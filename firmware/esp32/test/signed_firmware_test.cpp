// Firmware firmado: trailer, frontera de bloques, versiones e identidad
// (lib/protocol/src/signed_firmware.h).
//
// La comprobacion ECDSA real es de mbedtls y solo existe en el equipo; aqui se
// sustituye por una de prueba. Lo que se prueba es lo que la rodea: que a la
// flash vaya exactamente la imagen, que el trailer se reconstruya aunque llegue
// partido, y que la falta de firma o una firma alterada no se den por buenas.
// Que la firma del script verifique con la clave embebida lo prueba
// `tools/firmware_signing/sign_firmware.py --verify`.
#include "firmware_signing_key.h"
#include "signed_firmware.h"
#include <algorithm>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <vector>

using namespace signed_firmware;
typedef std::vector<uint8_t> Bytes;

// Resumen de prueba de 32 bytes (FNV-1a con cuatro semillas). No es SHA-256:
// basta con que cambie si cambia un byte.
static void fakeDigest(const Bytes& data, uint8_t out[kDigestBytes]) {
    for (int lane = 0; lane < 4; ++lane) {
        uint64_t h = 1469598103934665603ULL ^ uint64_t(lane + 1) * 0x9e3779b97f4a7c15ULL;
        for (uint8_t b : data) { h ^= b; h *= 1099511628211ULL; }
        for (int i = 0; i < 8; ++i) out[lane * 8 + i] = uint8_t(h >> (8 * i));
    }
}
// «Firma» de prueba: el resumen y su complemento. Solo la da quien conoce la
// regla, igual que solo el propietario tiene la clave privada.
static void fakeSign(const uint8_t digest[kDigestBytes], uint8_t signature[kSignatureBytes]) {
    for (size_t i = 0; i < kDigestBytes; ++i) { signature[i] = digest[i]; signature[32 + i] = uint8_t(~digest[i]); }
}
static bool fakeVerify(const uint8_t* digest, const uint8_t* signature) {
    uint8_t expected[kSignatureBytes];
    fakeSign(digest, expected);
    return std::memcmp(expected, signature, kSignatureBytes) == 0;
}

static Bytes image(size_t size, uint8_t seed) {
    Bytes out(size);
    uint32_t x = 0x12345678u + seed;
    for (size_t i = 0; i < size; ++i) { x = x * 1664525u + 1013904223u; out[i] = uint8_t(x >> 24); }
    return out;
}
static Bytes signedFile(const Bytes& img) {
    uint8_t digest[kDigestBytes], signature[kSignatureBytes];
    fakeDigest(img, digest);
    fakeSign(digest, signature);
    Bytes file(img);
    file.insert(file.end(), kTrailerMagic, kTrailerMagic + kMagicBytes);
    file.insert(file.end(), signature, signature + kSignatureBytes);
    return file;
}

struct Result {
    Bytes flashed;
    Verdict verdict;
};
// Lo que hace firmware_update.cpp: bloques en orden, a la flash solo la parte
// de imagen, y al final el veredicto con el resumen de lo escrito.
static Result upload(const Bytes& file, size_t chunk) {
    Splitter splitter;
    assert(splitter.begin(uint32_t(file.size())));
    Result result;
    for (size_t offset = 0; offset < file.size(); offset += chunk) {
        const size_t count = std::min(chunk, file.size() - offset);
        size_t imagePart = 99999;
        assert(splitter.accept(file.data() + offset, count, imagePart));
        assert(imagePart <= count);
        result.flashed.insert(result.flashed.end(), file.begin() + long(offset), file.begin() + long(offset + imagePart));
    }
    uint8_t digest[kDigestBytes];
    fakeDigest(result.flashed, digest);
    result.verdict = check(splitter, digest, fakeVerify);
    return result;
}

int main() {
    static_assert(kTrailerBytes == 72, "trailer de 72 bytes");
    static_assert(kMinFileBytes == 1024 + 72, "imagen minima mas trailer");

    // Clave embebida: punto P-256 sin comprimir.
    static_assert(sizeof(firmware_signing::kPublicKey) == 65, "65 bytes");
    assert(firmware_signing::kPublicKey[0] == 0x04);

    // Tamano: por debajo de imagen minima + trailer, no se empieza.
    {
        Splitter s;
        assert(!s.begin(0));
        assert(!s.begin(kMinFileBytes - 1));
        assert(s.begin(kMinFileBytes));
        assert(s.imageBytes() == kMinImageBytes);
    }

    // Todas las fronteras: la imagen llega entera a la flash, el trailer se
    // reconstruye y la firma vale, sea cual sea el corte de los bloques
    // (bloque de 1 byte, que cae justo en la frontera, que la cruza, 576...).
    const size_t sizes[] = {kMinImageBytes, kMinImageBytes + 1, 1100, 2 * 576 - 72, 2 * 576 - 71, 2 * 576 + 1};
    for (size_t imageSize : sizes) {
        const Bytes img = image(imageSize, uint8_t(imageSize));
        const Bytes file = signedFile(img);
        for (size_t chunk = 1; chunk <= 600; ++chunk) {
            const Result r = upload(file, chunk);
            assert(r.flashed == img);
            assert(r.verdict == Verdict::valid);
        }
    }

    // Trailer ausente: se sube firmware.bin sin firmar. Sus ultimos 72 bytes
    // hacen de trailer y no empiezan por la marca.
    {
        const Bytes unsignedImage = image(1500, 7);
        assert(upload(unsignedImage, 576).verdict == Verdict::missing_signature);
    }
    // Marca de otra version del formato: tampoco.
    {
        Bytes file = signedFile(image(1500, 8));
        file[1500 + 7] = '2';  // TVZSIG02
        assert(upload(file, 576).verdict == Verdict::missing_signature);
    }
    // Firma alterada: un bit de r, un bit de s.
    for (size_t at : {size_t(8), size_t(8 + 32), size_t(71)}) {
        Bytes file = signedFile(image(1500, 9));
        file[1500 + at] ^= 0x01;
        assert(upload(file, 576).verdict == Verdict::invalid_signature);
    }
    // Imagen alterada con la firma de la original.
    {
        Bytes file = signedFile(image(1500, 10));
        file[700] ^= 0x80;
        assert(upload(file, 576).verdict == Verdict::invalid_signature);
    }
    // Firma de otra imagen pegada a esta.
    {
        const Bytes a = signedFile(image(1500, 11)), b = signedFile(image(1500, 12));
        Bytes mixed(a.begin(), a.begin() + 1500);
        mixed.insert(mixed.end(), b.begin() + 1500, b.end());
        assert(upload(mixed, 576).verdict == Verdict::invalid_signature);
    }
    // Incompleto: no hay veredicto de firma.
    {
        const Bytes file = signedFile(image(1500, 13));
        Splitter s;
        assert(s.begin(uint32_t(file.size())));
        size_t part = 0;
        assert(s.accept(file.data(), file.size() - 1, part));
        assert(!s.complete());
        uint8_t digest[kDigestBytes] = {};
        assert(check(s, digest, fakeVerify) == Verdict::incomplete);
        // Un bloque que se sale del archivo se rechaza sin tocar nada.
        assert(!s.accept(file.data(), 2, part));
        assert(part == 0 && s.receivedBytes() == file.size() - 1);
        assert(s.accept(file.data() + file.size() - 1, 1, part) && part == 0 && s.complete());
    }
    // Sin begin(): nada entra.
    {
        Splitter s;
        size_t part = 1;
        const uint8_t byte = 0;
        assert(!s.accept(&byte, 1, part) && part == 0 && !s.complete());
    }

    // Versiones.
    assert(versionAtLeast("0.7.13", "0.7.13"));
    assert(versionAtLeast("0.7.14", "0.7.13"));
    assert(versionAtLeast("0.8.0", "0.7.13"));
    assert(versionAtLeast("0.10.0", "0.7.13"));
    assert(versionAtLeast("1.0.0", "0.7.13"));
    assert(versionAtLeast("0.7.13-dev", "0.7.13"));
    assert(!versionAtLeast("0.7.12", "0.7.13"));
    assert(!versionAtLeast("0.7.9", "0.7.13"));  // numerico, no alfabetico
    assert(!versionAtLeast("0.6.99", "0.7.13"));
    assert(!versionAtLeast("esp-idf: v4.4.7 38eeba213a", "0.7.13"));
    assert(!versionAtLeast("", "0.7.13"));
    assert(!versionAtLeast(nullptr, "0.7.13"));
    assert(!versionAtLeast("0.7", "0.7.13"));
    assert(!versionAtLeast("0.7.13x", "0.7.13"));
    assert(!versionAtLeast("v0.7.13", "0.7.13"));
    assert(!versionAtLeast("0.7.1234567890", "0.7.13"));
    assert(!versionAtLeast("0.7.13", "basura"));

    // Identidad: se construye en compilacion y se lee en la otra particion.
    static_assert(fitsIdentity("0.7.13"), "cabe");
    static_assert(fitsIdentity("12345678901234567890123"), "23 + NUL caben");
    static_assert(!fitsIdentity("123456789012345678901234"), "24 + NUL no caben");
    constexpr FirmwareIdentity built = makeIdentity("0.7.13");
    static_assert(built.magic[0] == 'T' && built.magic[7] == '1', "marca");
    static_assert(built.version[5] == '3' && built.version[6] == '\0' && built.version[23] == '\0', "version");
    {
        uint8_t raw[sizeof(FirmwareIdentity)];
        std::memcpy(raw, &built, sizeof(raw));
        assert(std::memcmp(raw, "TVZFWID10.7.13", 14) == 0);
        assert(requiresSignature(raw, sizeof(raw)));
        assert(!requiresSignature(raw, sizeof(raw) - 1));
        assert(!requiresSignature(nullptr, sizeof(raw)));

        const FirmwareIdentity later = makeIdentity("0.8.2");
        std::memcpy(raw, &later, sizeof(raw));
        assert(requiresSignature(raw, sizeof(raw)));

        // Una imagen de esta rama compilada aun como 0.7.12: no se vuelve a ella.
        const FirmwareIdentity older = makeIdentity("0.7.12");
        std::memcpy(raw, &older, sizeof(raw));
        assert(!requiresSignature(raw, sizeof(raw)));

        // Imagen anterior a la identidad: en el byte 288 hay otra cosa
        // (en 0.7.12, «wifi ipc: failed to post wifi task»).
        const char before[] = "wifi ipc: failed to post wifi task\0failed";
        std::memcpy(raw, before, sizeof(raw));
        assert(!requiresSignature(raw, sizeof(raw)));

        // Marca buena pero version sin NUL: no se da por buena.
        std::memcpy(raw, &built, sizeof(raw));
        std::memset(raw + kIdentityMagicBytes, '9', kIdentityVersionBytes);
        assert(!requiresSignature(raw, sizeof(raw)));
    }

    std::puts("signed_firmware: OK");
    return 0;
}
