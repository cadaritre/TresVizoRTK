#include "verified_image.h"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <map>
#include <string>

using verified_image::Verdict;

// Simula lo que hace firmware_update.cpp con la NVS y la partición: el registro
// se borra antes de escribir y se guarda solo tras verificar la firma.
namespace {
struct Device {
    std::map<std::string, std::string> nvs;   // etiqueta de partición → SHA-256
    std::string partitionImage;               // lo escrito en la otra partición
    bool imagePresent = false;

    static std::string digestOf(const std::string& image) {
        std::string digest(verified_image::kDigestBytes, '\0');
        for (size_t i = 0; i < image.size(); ++i) digest[i % digest.size()] ^= image[i];
        digest[0] ^= static_cast<char>(image.size());
        return digest;
    }
    void begin() { nvs.erase("app1"); }
    void writeAll(const std::string& image) { partitionImage = image; imagePresent = true; }
    void finishVerified() { nvs["app1"] = digestOf(partitionImage); }
    Verdict rollback(bool versionRequiresSignature) const {
        const auto record = nvs.find("app1");
        const std::string current = digestOf(partitionImage);
        return verified_image::rollback(
            imagePresent, versionRequiresSignature, record != nvs.end(),
            record != nvs.end() ? reinterpret_cast<const uint8_t*>(record->second.data()) : nullptr,
            reinterpret_cast<const uint8_t*>(current.data()));
    }
};
}  // namespace

int main() {
    // Carga completa y verificada: se puede volver a ella.
    Device ok;
    ok.begin(); ok.writeAll("imagen firmada A"); ok.finishVerified();
    assert(ok.rollback(true) == Verdict::allowed);

    // Corte tras escribir toda la imagen y antes de verificar (el caso de R01).
    Device cut;
    cut.begin(); cut.writeAll("imagen sin firma, completa");
    assert(cut.rollback(true) == Verdict::not_verified);

    // Una carga nueva interrumpida sobre una partición que antes estaba verificada:
    // el registro viejo se borró antes de escribir, así que tampoco se restaura.
    Device again = ok;
    again.begin(); again.writeAll("imagen B a medias");
    assert(again.rollback(true) == Verdict::not_verified);

    // Aunque el registro sobreviviera, si lo escrito cambió no coincide.
    Device stale = ok;
    stale.partitionImage = "otra cosa escrita por USB";
    assert(stale.rollback(true) == Verdict::not_verified);

    // Versión anterior a la firma y partición vacía.
    assert(ok.rollback(false) == Verdict::unsigned_version);
    Device empty;
    assert(empty.rollback(true) == Verdict::no_image);

    std::puts("verified_image_test: OK");
    return 0;
}
