#include "gnss_control.h"
#include "base_survey.h"
#include "ntrip_input.h"
#include "firmware_update.h"
#include "board_profile.h"
#include "instrument.h"
#include "local_display.h"
#include "correction_router.h"
#include "firmware_signing_key.h"
#include "signed_firmware.h"
#include "verified_image.h"
#include <Preferences.h>
#include <esp_partition.h>
#include <esp_ota_ops.h>
#include <esp_app_format.h>
#include <esp_image_format.h>
#include <mbedtls/base64.h>
#include <mbedtls/sha256.h>
#include <mbedtls/ecdsa.h>
#include <atomic>

namespace firmware_update {
namespace {
constexpr char hardware[] = TRESVIZO_HARDWARE_ID;
constexpr size_t chunkLimit = 576;

// Identidad de esta imagen, en la seccion que ESP-IDF deja justo detras del
// descriptor de aplicacion (byte 288 de la imagen). Asi, la version que corra
// despues puede leer la de esta particion y decidir si se puede volver a ella
// (`/api/update/rollback`). Motivo y formato en `signed_firmware.h`.
static_assert(signed_firmware::fitsIdentity(instrument::kVersion), "kVersion no cabe en la identidad de la imagen");
static_assert(sizeof(esp_image_header_t) + sizeof(esp_image_segment_header_t) + sizeof(esp_app_desc_t) ==
              signed_firmware::kIdentityImageOffset, "la identidad va justo detras de esp_app_desc_t");
// Referenciada desde status(): si nadie la usa, el enlazador la descarta.
static_assert(sizeof(hardware)<=signed_firmware::kHardwareIdBytes,"hardware_id no cabe en la imagen");
const signed_firmware::BoardFirmwareIdentity identity __attribute__((section(".rodata_custom_desc"), used)) =
    {signed_firmware::makeIdentity(instrument::kVersion),TRESVIZO_HARDWARE_ID};

esp_ota_handle_t handle = 0;
const esp_partition_t* target = nullptr;
// Dos resumenes: el del archivo completo (integridad del transporte, contra el
// `sha256` del manifiesto) y el de la imagen sola, que es lo firmado.
mbedtls_sha256_context fileHash, imageHash;
signed_firmware::Splitter splitter;
uint32_t total = 0, received = 0, touched = 0, lastOffset = 0;
size_t lastLength = 0;
uint8_t previous[chunkLimit];
String expectedHash, session;
// busy() se consulta también desde las tareas NTRIP y GNSS.
std::atomic<bool> active{false}, restart{false};
bool bootChecked = false, targetTouched = false;
uint32_t restartAt = 0;
const char* state = "idle";
int fail(JsonDocument& out, int code, const char* message) {
    out["error"] = "update_error"; out["message"] = message; return code;
}
void invalidateTarget() {
    if (targetTouched && target && target != esp_ota_get_running_partition()) esp_partition_erase_range(target,0,4096);
    targetTouched = false;
}
void abortTransfer(const char* reason) {
    if (active) { esp_ota_abort(handle); mbedtls_sha256_free(&fileHash); mbedtls_sha256_free(&imageHash); }
    invalidateTarget();
    active = false; state = reason;
}
bool matches(JsonVariantConst body) {
    return body["session"].is<const char*>() && session == body["session"].as<const char*>();
}
// Firma ECDSA P-256 `r||s` sobre `digest` (SHA-256 de la imagen), con la clave
// publica embebida. Cualquier fallo de mbedtls cuenta como firma no valida.
bool signatureValid(const uint8_t* digest, const uint8_t* signature) {
    constexpr size_t half = signed_firmware::kSignatureBytes / 2;
    mbedtls_ecp_group group; mbedtls_ecp_point key; mbedtls_mpi r, s;
    mbedtls_ecp_group_init(&group); mbedtls_ecp_point_init(&key);
    mbedtls_mpi_init(&r); mbedtls_mpi_init(&s);
    const bool valid =
        mbedtls_ecp_group_load(&group, MBEDTLS_ECP_DP_SECP256R1) == 0 &&
        mbedtls_ecp_point_read_binary(&group, &key, firmware_signing::kPublicKey, sizeof(firmware_signing::kPublicKey)) == 0 &&
        mbedtls_ecp_check_pubkey(&group, &key) == 0 &&
        mbedtls_mpi_read_binary(&r, signature, half) == 0 &&
        mbedtls_mpi_read_binary(&s, signature + half, half) == 0 &&
        mbedtls_ecdsa_verify(&group, digest, signed_firmware::kDigestBytes, &key, &r, &s) == 0;
    mbedtls_mpi_free(&s); mbedtls_mpi_free(&r);
    mbedtls_ecp_point_free(&key); mbedtls_ecp_group_free(&group);
    return valid;
}
// Registro persistente de las imágenes cuya firma se verificó en este equipo
// (verified_image.h, reauditoría R01): SHA-256 de la partición, por etiqueta.
constexpr const char* kVerifiedNamespace = "ota_verified";
bool partitionDigest(const esp_partition_t* partition, uint8_t* digest) {
    return partition && esp_partition_get_sha256(partition, digest) == ESP_OK;
}
// Antes de la primera escritura: si no se puede borrar, no se escribe.
bool forgetVerified(const esp_partition_t* partition) {
    Preferences store;
    if (!partition || !store.begin(kVerifiedNamespace, false)) return false;
    const bool ok = !store.isKey(partition->label) || store.remove(partition->label);
    store.end();
    return ok;
}
// Tras verificar la firma y validar la imagen. Si falla, solo se pierde poder
// volver a ella por la API: el arranque nuevo no depende de esto.
bool rememberVerified(const esp_partition_t* partition) {
    uint8_t digest[verified_image::kDigestBytes];
    Preferences store;
    if (!partitionDigest(partition, digest) || !store.begin(kVerifiedNamespace, false)) return false;
    const bool ok = store.putBytes(partition->label, digest, sizeof(digest)) == sizeof(digest);
    store.end();
    return ok;
}
bool requiresSignature(const esp_partition_t* partition);
bool matchesBoard(const esp_partition_t* partition) {
    uint8_t raw[signed_firmware::kHardwareIdBytes];
    return partition && esp_partition_read(partition,signed_firmware::kHardwareImageOffset,raw,sizeof(raw))==ESP_OK &&
           signed_firmware::matchesHardware(raw,sizeof(raw),hardware);
}
verified_image::Verdict rollbackVerdict(const esp_partition_t* partition) {
    esp_app_desc_t descriptor;
    const bool present = partition && esp_ota_get_partition_description(partition, &descriptor) == ESP_OK;
    uint8_t recorded[verified_image::kDigestBytes], current[verified_image::kDigestBytes];
    bool recordPresent = false;
    Preferences store;
    if (present && store.begin(kVerifiedNamespace, true)) {
        recordPresent = store.getBytesLength(partition->label) == sizeof(recorded) &&
                        store.getBytes(partition->label, recorded, sizeof(recorded)) == sizeof(recorded);
        store.end();
    }
    const bool digestOk = present && partitionDigest(partition, current);
    return verified_image::rollback(present, present && requiresSignature(partition), recordPresent && digestOk,
                                    recorded, current);
}
// La imagen debe exigir firma y pertenecer a esta placa. La autenticidad se
// comprueba además mediante el registro persistente de rollbackVerdict().
bool requiresSignature(const esp_partition_t* partition) {
    uint8_t raw[sizeof(signed_firmware::FirmwareIdentity)];
    return matchesBoard(partition) && esp_partition_read(partition, signed_firmware::kIdentityImageOffset, raw, sizeof(raw)) == ESP_OK &&
           signed_firmware::requiresSignature(raw, sizeof(raw));
}
void status(JsonDocument& out) {
    const auto running = esp_ota_get_running_partition();
    const auto next = esp_ota_get_next_update_partition(nullptr);
    out["state"] = state; out["hardware_id"] = hardware;
    out["firmware_version"] = static_cast<const char*>(identity.firmware.version);
    out["active_slot"] = running ? running->label : "unknown";
    out["max_image_bytes"] = next ? next->size : 0;
    out["chunk_bytes"] = chunkLimit;
    out["received_bytes"] = received; out["total_bytes"] = total;
    out["transport"] = "wifi_or_usb";
    out["image_authenticity"] = "owner_signed_ecdsa_p256";
    out["signature_required"] = true;
#ifdef CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE
    out["automatic_boot_rollback"] = true;
#else
    out["automatic_boot_rollback"] = false;
#endif
    esp_ota_img_states_t imageState;
    out["boot_confirmed"] = running && esp_ota_get_state_partition(running, &imageState) == ESP_OK && imageState == ESP_OTA_IMG_VALID;
    esp_app_desc_t previousImage;
    const bool previousPresent = next && esp_ota_get_partition_description(next, &previousImage) == ESP_OK;
    out["previous_image_present"] = previousPresent;
    // Si es falso, `/api/update/rollback` contesta 409: el panel apaga el botón.
    // Desde 0.7.14 exige además que este equipo haya verificado su firma (R01).
    out["previous_image_signature_required"] = previousPresent && rollbackVerdict(next) == verified_image::Verdict::allowed;
}
}
bool busy() { return active || restart; }
int request(const String& method, const String& path, JsonVariantConst body, JsonDocument& out) {
    if (method == "GET" && path == "/api/update") { status(out); return 200; }
    if (method != "POST") return fail(out,400,"Método de actualización no válido.");
    if (path == "/api/update/begin") {
        if (busy()) return fail(out,409,"Ya hay una actualización o reinicio en curso.");
        if (!body.is<JsonObjectConst>() || body.size() != 3 || body["hardware_id"] != hardware ||
            !body["size"].is<uint32_t>() || !body["sha256"].is<const char*>())
            return fail(out,400,"Manifiesto incompatible con este equipo.");
        const String digest = body["sha256"].as<const char*>();
        if (body["sha256"].as<JsonString>().size() != 64 || digest.length() != 64) return fail(out,400,"SHA-256 inválido.");
        for (char c : digest) if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return fail(out,400,"SHA-256 inválido.");
        target = esp_ota_get_next_update_partition(nullptr);
        // `size` es el del archivo firmado: imagen más los 72 bytes de la firma.
        const uint32_t size = body["size"];
        if (size < signed_firmware::kMinFileBytes) return fail(out,400,"El archivo es demasiado pequeño para ser un firmware firmado. Usa el archivo firmware-signed.bin.");
        if (!target || size - signed_firmware::kTrailerBytes > target->size) return fail(out,400,"Tamaño de imagen fuera de la partición OTA.");
        // Antes de tocar la partición: que deje de contar como verificada (R01).
        if (!forgetVerified(target)) return fail(out,503,"No se pudo preparar la partición inactiva.");
        base_survey::cancel("Cancelado por actualización.");gnss_control::cancel();ntrip_input::stopForUser();
        if (esp_ota_begin(target,OTA_WITH_SEQUENTIAL_WRITES,&handle) != ESP_OK) return fail(out,503,"No se pudo preparar la partición inactiva.");
        correction_router::select("none");
        mbedtls_sha256_init(&fileHash); mbedtls_sha256_starts_ret(&fileHash,0);
        mbedtls_sha256_init(&imageHash); mbedtls_sha256_starts_ret(&imageHash,0);
        splitter.begin(size);
        char token[25]; snprintf(token,sizeof(token),"%08lx%08lx%08lx",(unsigned long)esp_random(),(unsigned long)esp_random(),(unsigned long)esp_random());
        targetTouched = false; session = token; expectedHash = digest; total = size; received = 0; lastLength = 0;
        touched = millis(); active = true; state = "receiving";
        status(out); out["session"] = session; return 200;
    }
    if (path == "/api/update/rollback") {
        if (busy()) return fail(out,409,"Actualización en curso.");
        const auto next = esp_ota_get_next_update_partition(nullptr);
        switch (rollbackVerdict(next)) {
            case verified_image::Verdict::allowed: break;
            case verified_image::Verdict::no_image:
                return fail(out,409,"No hay una imagen anterior válida para restaurar.");
            case verified_image::Verdict::unsigned_version:
                return fail(out,409,"La imagen anterior no exige firma o corresponde a otra placa; no se restaura por la API.");
            default:
                return fail(out,409,"Este equipo no verificó la firma de la imagen anterior (se cargó por cable o su carga no terminó); no se restaura por la API. Usa el cable USB.");
        }
        if (esp_ota_set_boot_partition(next) != ESP_OK)
            return fail(out,409,"No hay una imagen anterior válida para restaurar.");
        base_survey::cancel("Cancelado por actualización.");gnss_control::cancel();ntrip_input::stopForUser();
        state = "rollback_scheduled"; restart = true; restartAt = millis(); status(out); return 202;
    }
    if (!active || !matches(body)) return fail(out,409,"Sesión de actualización inválida o vencida.");
    touched = millis();
    if (path == "/api/update/abort") { abortTransfer("aborted"); status(out); return 200; }
    if (path == "/api/update/chunk") {
        if (!body["offset"].is<uint32_t>() || !body["data"].is<const char*>() || body.size() != 3)
            return fail(out,400,"Bloque de actualización inválido.");
        uint8_t decoded[chunkLimit]; size_t count = 0;
        const JsonString encoded = body["data"].as<JsonString>();
        if (!encoded.size() || encoded.size() > 768 || mbedtls_base64_decode(decoded,sizeof(decoded),&count,
            reinterpret_cast<const uint8_t*>(encoded.c_str()),encoded.size()) != 0 || !count)
            return fail(out,400,"Bloque base64 inválido.");
        const uint32_t offset = body["offset"];
        if (lastLength && offset == lastOffset && count == lastLength && !memcmp(decoded,previous,count)) {
            out["received_bytes"] = received; out["duplicate"] = true; return 200;
        }
        if (offset != received || count > total - received) return fail(out,409,"Offset inesperado. Consulta el progreso antes de continuar.");
        // Cabecera ESP32-S3, seguida de descriptor de aplicación; no aceptar imágenes de bootloader/flash completa.
        if (!received && (count < 288 || decoded[0] != 0xe9 || decoded[12] != 9 || decoded[13] != 0 ||
            decoded[32] != 0x32 || decoded[33] != 0x54 || decoded[34] != 0xcd || decoded[35] != 0xab)) {
            abortTransfer("invalid_image"); return fail(out,400,"Se requiere firmware.bin de aplicación ESP32-S3.");
        }
        // A la flash solo va la imagen; los bytes del trailer (la firma) se
        // quedan en memoria. Un bloque puede cruzar la frontera.
        size_t imagePart = 0;
        if (!splitter.accept(decoded,count,imagePart)) return fail(out,409,"Offset inesperado. Consulta el progreso antes de continuar.");
        targetTouched = true;
        if (imagePart && esp_ota_write(handle,decoded,imagePart) != ESP_OK) { abortTransfer("write_failed"); return fail(out,503,"Falló la escritura de flash; se conserva el arranque actual."); }
        mbedtls_sha256_update_ret(&fileHash,decoded,count);
        if (imagePart) mbedtls_sha256_update_ret(&imageHash,decoded,imagePart);
        lastOffset = offset; lastLength = count; memcpy(previous,decoded,count); received += count;
        out["received_bytes"] = received; return 200;
    }
    if (path == "/api/update/finish") {
        if (received != total) return fail(out,409,"La imagen está incompleta.");
        uint8_t digest[32]; char hex[65];
        mbedtls_sha256_finish_ret(&fileHash,digest);
        for (size_t i=0;i<32;++i) snprintf(hex+i*2,3,"%02x",digest[i]);
        if (expectedHash != hex) { abortTransfer("hash_mismatch"); return fail(out,400,"SHA-256 no coincide; no se cambiará el arranque."); }
        // La firma se comprueba antes de validar la imagen y de tocar el arranque.
        uint8_t imageDigest[signed_firmware::kDigestBytes];
        mbedtls_sha256_finish_ret(&imageHash,imageDigest);
        switch (signed_firmware::check(splitter,imageDigest,signatureValid)) {
            case signed_firmware::Verdict::valid: break;
            case signed_firmware::Verdict::missing_signature:
                abortTransfer("signature_missing");
                return fail(out,400,"El firmware no trae la firma del propietario. Usa el archivo firmware-signed.bin.");
            case signed_firmware::Verdict::invalid_signature:
                abortTransfer("signature_invalid");
                return fail(out,400,"La firma del firmware no es válida; no se instala.");
            default:
                abortTransfer("incomplete");
                return fail(out,409,"La imagen está incompleta.");
        }
        // Cambiar solo el manifiesto no convierte un firmware de Tiny en uno
        // de Thing Plus. La placa forma parte de la imagen cuya firma se comprobó.
        if (!matchesBoard(target)) {
            abortTransfer("hardware_mismatch");
            return fail(out,400,"La imagen firmada es para otra placa. Se requiere firmware de Thing Plus ESP32-S3.");
        }
        mbedtls_sha256_free(&fileHash); mbedtls_sha256_free(&imageHash);
        const esp_err_t validated = esp_ota_end(handle);
        if (validated != ESP_OK) { invalidateTarget(); active = false; state = "invalid_image"; return fail(out,400,"La imagen no pasó la validación de Espressif."); }
        // Firma verificada e imagen válida: desde ahora se puede volver a ella.
        rememberVerified(target);
        if (esp_ota_set_boot_partition(target) != ESP_OK) { active = false; state = "activation_failed"; return fail(out,503,"No se pudo activar la imagen; se conserva el arranque actual."); }
        // busy() permanece cierto entre recibir y programar el reinicio:
        // NTRIP/GNSS no deben arrancar durante la activación de la imagen.
        state = "restart_scheduled"; restart = true; active = false; restartAt = millis(); status(out); return 202;
    }
    return fail(out,404,"Operación de actualización desconocida.");
}
void tick(bool servicesReady) {
    if (active && millis() - touched > 30000) abortTransfer("timed_out");
    if (restart && millis() - restartAt > 1500 && local_display::prepareRestart()) ESP.restart();
    if (!bootChecked && servicesReady && millis() > 5000) {
        esp_ota_img_states_t imageState;
        const auto running = esp_ota_get_running_partition();
        if (running && esp_ota_get_state_partition(running,&imageState) == ESP_OK && imageState == ESP_OTA_IMG_PENDING_VERIFY) {
            if (esp_ota_mark_app_valid_cancel_rollback() != ESP_OK) return;
        }
        bootChecked = true;
    }
}
}
