#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>

namespace verified_image {
// ¿Se puede volver por la API a la imagen de la otra partición?
//
// **Por qué hace falta (reauditoría de 0.7.13, R01).** La firma se comprueba en
// `finish`, pero la imagen se escribe en la partición durante `chunk`. Si la
// corriente se corta después de escribir el último byte y antes de comprobar la
// firma, queda en la otra partición una imagen completa que nadie autenticó, y
// tras reiniciar no queda rastro en RAM de que la transferencia no acabó. La
// marca de identidad (`signed_firmware.h`, TVZFWID1 + versión) dice lo que la
// imagen afirma ser, no quién la firmó.
//
// **La regla.** El equipo guarda, de forma persistente y por partición, el
// SHA-256 de la imagen **después** de verificar su firma. El registro de esa
// partición se borra **antes** de la primera escritura de una carga nueva. Un
// corte en cualquier punto deja la partición sin registro, o con uno que ya no
// coincide con lo que hay escrito: en los dos casos no se restaura. Una imagen
// cargada por USB no tiene registro: se vuelve a ella por USB.
constexpr size_t kDigestBytes = 32;

enum class Verdict {
    allowed,            // imagen presente, versión que exige firma y firma verificada aquí
    no_image,           // no hay imagen de aplicación válida en la otra partición
    unsigned_version,   // la imagen es de una versión que acepta firmware sin firma
    not_verified,       // sin registro, o el registro no coincide con lo escrito
};

inline Verdict rollback(bool imagePresent, bool versionRequiresSignature, bool recordPresent,
                        const uint8_t* recordedDigest, const uint8_t* partitionDigest) {
    if (!imagePresent) return Verdict::no_image;
    if (!versionRequiresSignature) return Verdict::unsigned_version;
    if (!recordPresent || !recordedDigest || !partitionDigest) return Verdict::not_verified;
    return std::memcmp(recordedDigest, partitionDigest, kDigestBytes) == 0 ? Verdict::allowed
                                                                           : Verdict::not_verified;
}
}  // namespace verified_image
