#include "firmware_update.h"
#include "instrument.h"
#include "correction_router.h"
#include <esp_ota_ops.h>
#include <esp_app_format.h>
#include <mbedtls/base64.h>
#include <mbedtls/sha256.h>

namespace firmware_update {
namespace {
constexpr char hardware[] = "tresvizo-esp32s3-4m-v1";
constexpr size_t chunkLimit = 576;
esp_ota_handle_t handle = 0;
const esp_partition_t* target = nullptr;
mbedtls_sha256_context hash;
uint32_t total = 0, received = 0, touched = 0, lastOffset = 0;
size_t lastLength = 0;
uint8_t previous[chunkLimit];
String expectedHash, session;
bool active = false, restart = false, bootChecked = false, targetTouched = false;
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
    if (active) { esp_ota_abort(handle); mbedtls_sha256_free(&hash); }
    invalidateTarget();
    active = false; state = reason;
}
bool matches(JsonVariantConst body) {
    return body["session"].is<const char*>() && session == body["session"].as<const char*>();
}
void status(JsonDocument& out) {
    const auto running = esp_ota_get_running_partition();
    const auto next = esp_ota_get_next_update_partition(nullptr);
    out["state"] = state; out["hardware_id"] = hardware;
    out["firmware_version"] = instrument::kVersion;
    out["active_slot"] = running ? running->label : "unknown";
    out["max_image_bytes"] = next ? next->size : 0;
    out["chunk_bytes"] = chunkLimit;
    out["received_bytes"] = received; out["total_bytes"] = total;
    out["transport"] = "wifi_or_usb";
    out["image_authenticity"] = "owner_supplied_unsigned";
#ifdef CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE
    out["automatic_boot_rollback"] = true;
#else
    out["automatic_boot_rollback"] = false;
#endif
    esp_ota_img_states_t imageState;
    out["boot_confirmed"] = running && esp_ota_get_state_partition(running, &imageState) == ESP_OK && imageState == ESP_OTA_IMG_VALID;
    esp_app_desc_t previousImage;
    out["previous_image_present"] = next && esp_ota_get_partition_description(next, &previousImage) == ESP_OK;
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
        const uint32_t size = body["size"];
        if (!target || size < 1024 || size > target->size) return fail(out,400,"Tamaño de imagen fuera de la partición OTA.");
        if (esp_ota_begin(target,OTA_WITH_SEQUENTIAL_WRITES,&handle) != ESP_OK) return fail(out,503,"No se pudo preparar la partición inactiva.");
        correction_router::select("none");
        mbedtls_sha256_init(&hash); mbedtls_sha256_starts_ret(&hash,0);
        char token[25]; snprintf(token,sizeof(token),"%08lx%08lx%08lx",(unsigned long)esp_random(),(unsigned long)esp_random(),(unsigned long)esp_random());
        targetTouched = false; session = token; expectedHash = digest; total = size; received = 0; lastLength = 0;
        touched = millis(); active = true; state = "receiving";
        status(out); out["session"] = session; return 200;
    }
    if (path == "/api/update/rollback") {
        if (busy()) return fail(out,409,"Actualización en curso.");
        const auto next = esp_ota_get_next_update_partition(nullptr);
        esp_app_desc_t descriptor;
        if (!next || esp_ota_get_partition_description(next,&descriptor) != ESP_OK || esp_ota_set_boot_partition(next) != ESP_OK)
            return fail(out,409,"No hay una imagen anterior válida para restaurar.");
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
        targetTouched = true;
        if (esp_ota_write(handle,decoded,count) != ESP_OK) { abortTransfer("write_failed"); return fail(out,503,"Falló la escritura de flash; se conserva el arranque actual."); }
        mbedtls_sha256_update_ret(&hash,decoded,count);
        lastOffset = offset; lastLength = count; memcpy(previous,decoded,count); received += count;
        out["received_bytes"] = received; return 200;
    }
    if (path == "/api/update/finish") {
        if (received != total) return fail(out,409,"La imagen está incompleta.");
        uint8_t digest[32]; char hex[65];
        mbedtls_sha256_finish_ret(&hash,digest);
        for (size_t i=0;i<32;++i) snprintf(hex+i*2,3,"%02x",digest[i]);
        if (expectedHash != hex) { abortTransfer("hash_mismatch"); return fail(out,400,"SHA-256 no coincide; no se cambiará el arranque."); }
        mbedtls_sha256_free(&hash);
        const esp_err_t validated = esp_ota_end(handle); active = false;
        if (validated != ESP_OK) { invalidateTarget(); state = "invalid_image"; return fail(out,400,"La imagen no pasó la validación de Espressif."); }
        if (esp_ota_set_boot_partition(target) != ESP_OK) { state = "activation_failed"; return fail(out,503,"No se pudo activar la imagen; se conserva el arranque actual."); }
        state = "restart_scheduled"; restart = true; restartAt = millis(); status(out); return 202;
    }
    return fail(out,404,"Operación de actualización desconocida.");
}
void tick(bool servicesReady) {
    if (active && millis() - touched > 30000) abortTransfer("timed_out");
    if (restart && millis() - restartAt > 1500) ESP.restart();
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
