#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>

namespace signed_firmware {
// Firmware firmado por el propietario para la carga OTA (desde 0.7.13).
//
// **Formato del archivo** (contrato con `tools/firmware_signing/sign_firmware.py`
// y con las apps, que suben el archivo tal cual):
//
//   [ imagen de aplicacion ESP32-S3 (firmware.bin) ][ trailer de 72 bytes ]
//   trailer = "TVZSIG01" (8 bytes ASCII) + firma ECDSA P-256 en bruto r||s
//             (32 + 32 bytes, big-endian) sobre SHA-256 de todos los bytes de
//             la imagen, sin el trailer.
//
// `POST /api/update/begin` no cambia de forma: `size` y `sha256` son los del
// archivo completo (el SHA sigue siendo integridad del transporte). A la flash
// solo va la imagen; el trailer se guarda aparte y se comprueba en `finish`,
// antes de `esp_ota_end` y de cambiar el arranque.
//
// Todo esto es C++11: el firmware compila con gnu++11.

constexpr char kTrailerMagic[] = "TVZSIG01";
constexpr size_t kMagicBytes = 8;
constexpr size_t kSignatureBytes = 64;  // r || s, 32 + 32
constexpr size_t kTrailerBytes = kMagicBytes + kSignatureBytes;
constexpr size_t kDigestBytes = 32;     // SHA-256
static_assert(sizeof(kTrailerMagic) == kMagicBytes + 1, "la marca son 8 bytes ASCII");
static_assert(kTrailerBytes == 72, "el trailer es contrato con el script de firma");

// Imagen minima que se acepta. Es el limite que ya aplicaba el equipo antes de
// la firma: una imagen real ronda 1.6 MB y la cabecera ESP32-S3 mas el
// descriptor de aplicacion ya ocupan 288 bytes. Solo rechaza lo absurdo.
constexpr uint32_t kMinImageBytes = 1024;
constexpr uint32_t kMinFileBytes = kMinImageBytes + kTrailerBytes;

// Separa el archivo que llega por bloques en la imagen (a flash) y el trailer
// (a memoria). Un bloque puede caer entero en la imagen, entero en el trailer o
// cruzar la frontera.
class Splitter {
public:
    // Falso si el archivo no llega a trailer mas imagen minima.
    bool begin(uint32_t fileBytes) {
        file_ = image_ = received_ = 0;
        std::memset(trailer_, 0, sizeof(trailer_));
        if (fileBytes < kMinFileBytes) return false;
        file_ = fileBytes;
        image_ = fileBytes - uint32_t(kTrailerBytes);
        return true;
    }
    // Siguiente bloque, en orden. `imagePart` dice cuantos bytes del principio
    // del bloque son imagen (van a flash y al SHA de la imagen); el resto se
    // guarda como trailer. Falso, sin tocar nada, si el bloque se sale del
    // archivo.
    bool accept(const uint8_t* data, size_t count, size_t& imagePart) {
        imagePart = 0;
        if (count > file_ - received_) return false;
        if (received_ < image_) {
            const uint32_t left = image_ - received_;
            imagePart = count < left ? count : size_t(left);
        }
        const size_t rest = count - imagePart;
        if (rest) std::memcpy(trailer_ + (received_ + imagePart - image_), data + imagePart, rest);
        received_ += uint32_t(count);
        return true;
    }
    uint32_t imageBytes() const { return image_; }
    uint32_t receivedBytes() const { return received_; }
    bool complete() const { return file_ && received_ == file_; }
    bool hasMagic() const { return std::memcmp(trailer_, kTrailerMagic, kMagicBytes) == 0; }
    const uint8_t* signature() const { return trailer_ + kMagicBytes; }

private:
    uint32_t file_ = 0, image_ = 0, received_ = 0;
    uint8_t trailer_[kTrailerBytes] = {};
};

enum class Verdict : uint8_t { valid, incomplete, missing_signature, invalid_signature };

// Veredicto sobre un archivo completo. `verify(digest, signature)` es la
// comprobacion ECDSA: mbedtls en el equipo, sustituible en las pruebas.
template <typename Verify>
Verdict check(const Splitter& splitter, const uint8_t imageDigest[kDigestBytes], Verify verify) {
    if (!splitter.complete()) return Verdict::incomplete;
    if (!splitter.hasMagic()) return Verdict::missing_signature;
    return verify(imageDigest, splitter.signature()) ? Verdict::valid : Verdict::invalid_signature;
}

// ---------------------------------------------------------------------------
// Versiones: la restauracion de la imagen anterior (`/api/update/rollback`) solo
// se admite si esa imagen tambien exige firma. Si no, quien no puede cargar un
// firmware ajeno volveria a una version que lo acepta y lo cargaria despues.

// Primera version que exige firma en la OTA.
constexpr char kFirstSignedVersion[] = "0.7.13";

struct Version {
    uint32_t major, minor, patch;
};

// Tope de cifras por campo, para no desbordar un uint32_t.
constexpr int kMaxVersionDigits = 9;

namespace detail {
inline const char* readNumber(const char* text, uint32_t& value) {
    if (*text < '0' || *text > '9') return nullptr;
    value = 0;
    int digits = 0;
    while (*text >= '0' && *text <= '9') {
        if (++digits > kMaxVersionDigits) return nullptr;
        value = value * 10 + uint32_t(*text - '0');
        ++text;
    }
    return text;
}
}  // namespace detail

// «MAYOR.MENOR.PARCHE», con un sufijo opcional tras «-» o «+» que no cuenta.
// Falso con cualquier otra cosa, incluida la version de ESP-IDF que Arduino
// deja en `esp_app_desc_t` («esp-idf: v4.4.7 38eeba213a»).
inline bool parseVersion(const char* text, Version& out) {
    if (!text) return false;
    const char* cursor = detail::readNumber(text, out.major);
    if (!cursor || *cursor != '.') return false;
    cursor = detail::readNumber(cursor + 1, out.minor);
    if (!cursor || *cursor != '.') return false;
    cursor = detail::readNumber(cursor + 1, out.patch);
    if (!cursor) return false;
    return *cursor == '\0' || *cursor == '-' || *cursor == '+';
}

// Falso tambien si alguna de las dos no se entiende: ante la duda, no se
// restaura.
inline bool versionAtLeast(const char* candidate, const char* minimum) {
    Version a, b;
    if (!parseVersion(candidate, a) || !parseVersion(minimum, b)) return false;
    if (a.major != b.major) return a.major > b.major;
    if (a.minor != b.minor) return a.minor > b.minor;
    return a.patch >= b.patch;
}

// ---------------------------------------------------------------------------
// Identidad de la imagen, para saber la version de la **otra** particion.
//
// **Por que no `esp_app_desc_t.version`.** Arduino-ESP32 2.0.17 trae el
// descriptor ya compilado en sus bibliotecas: en toda imagen dice
// «esp-idf: v4.4.7 38eeba213a» y «arduino-lib-builder» (comprobado en el
// `firmware.bin` de 0.7.12, bytes 32-287). La version del firmware esta en
// algun sitio de `.rodata`, sin posicion fija.
//
// **Como.** El enlazador de ESP-IDF reserva `.rodata_custom_desc` justo detras
// del descriptor (`sections.ld`: «Should be the second. Custom app version
// info»). La identidad va ahi, asi que en la imagen empieza en el byte 288:
// cabecera (24) + cabecera de segmento (8) + `esp_app_desc_t` (256).
// Una imagen anterior a 0.7.13 no la tiene: en ese sitio hay otra cosa y la
// marca no coincide.
constexpr char kIdentityMagic[] = "TVZFWID1";
constexpr size_t kIdentityMagicBytes = 8;
constexpr size_t kIdentityVersionBytes = 24;
constexpr uint32_t kIdentityImageOffset = 24 + 8 + 256;
static_assert(sizeof(kIdentityMagic) == kIdentityMagicBytes + 1, "la marca son 8 bytes ASCII");

struct FirmwareIdentity {
    char magic[kIdentityMagicBytes];      // "TVZFWID1", sin NUL
    char version[kIdentityVersionBytes];  // kVersion, terminada en NUL
};
static_assert(sizeof(FirmwareIdentity) == 32, "la identidad ocupa 32 bytes en la imagen");

namespace detail {
template <size_t... I> struct Indices {};
template <size_t N, size_t... I> struct BuildIndices : BuildIndices<N - 1, N - 1, I...> {};
template <size_t... I> struct BuildIndices<0, I...> { typedef Indices<I...> type; };

// Caracter `index` de `text`, o NUL pasado el final. Recursivo porque en C++11
// una funcion constexpr no admite bucles.
constexpr char charAt(const char* text, size_t index) {
    return *text == '\0' ? '\0' : index == 0 ? *text : charAt(text + 1, index - 1);
}
constexpr size_t textLength(const char* text) {
    return *text == '\0' ? 0 : 1 + textLength(text + 1);
}
template <size_t... M, size_t... V>
constexpr FirmwareIdentity buildIdentity(const char* version, Indices<M...>, Indices<V...>) {
    return FirmwareIdentity{{charAt(kIdentityMagic, M)...},
                            {(V + 1 < kIdentityVersionBytes ? charAt(version, V) : '\0')...}};
}
}  // namespace detail

// Cabe con su NUL en la identidad.
constexpr bool fitsIdentity(const char* version) {
    return detail::textLength(version) < kIdentityVersionBytes;
}

// Identidad en tiempo de compilacion, para dejarla en flash.
constexpr FirmwareIdentity makeIdentity(const char* version) {
    return detail::buildIdentity(version, detail::BuildIndices<kIdentityMagicBytes>::type(),
                                 detail::BuildIndices<kIdentityVersionBytes>::type());
}

// Los 32 bytes leidos en el byte 288 de otra particion: ¿es una imagen que
// exige firma? Falso si no hay marca, si la version no termina en NUL o si es
// anterior a la primera firmada.
inline bool requiresSignature(const uint8_t* raw, size_t length) {
    if (!raw || length < sizeof(FirmwareIdentity)) return false;
    if (std::memcmp(raw, kIdentityMagic, kIdentityMagicBytes) != 0) return false;
    char version[kIdentityVersionBytes];
    std::memcpy(version, raw + kIdentityMagicBytes, sizeof(version));
    if (!std::memchr(version, '\0', sizeof(version))) return false;
    return versionAtLeast(version, kFirstSignedVersion);
}
}  // namespace signed_firmware
