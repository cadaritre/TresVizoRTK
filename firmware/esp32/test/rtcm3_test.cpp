#include "rtcm3.h"
#include <cassert>
#include <vector>
int main() {
    std::vector<uint8_t> packet{0xd3, 0, 4, 0x3e, 0xd0, 0, 0};
    const auto crc = gnss::crc24q(packet.data(), packet.size());
    packet.push_back(crc >> 16); packet.push_back(crc >> 8); packet.push_back(crc);
    gnss::Rtcm3Parser parser;
    unsigned count = 0;
    auto consume = [&](const uint8_t* data, size_t size) { assert(size == packet.size()); assert(data[0] == 0xd3); ++count; };
    for (const auto byte : packet) parser.feed(byte, consume);
    assert(count == 1);
    packet.back() ^= 1;
    for (const auto byte : packet) parser.feed(byte, consume);
    assert(count == 1 && parser.rejected == 1);
    packet.back() ^= 1;
    for (const auto byte : packet) parser.feed(byte, consume);
    assert(count == 2);
    for (int i = 0; i < 5000; ++i) parser.feed(0xff, consume);
    for (const auto byte : packet) parser.feed(byte, consume);
    assert(count == 3);

    // Resincronización: basura con 0xD3 intercalados no debe perder la trama
    // siguiente ni dejar el buffer bloqueado.
    gnss::Rtcm3Parser noisy;
    unsigned recovered = 0;
    auto collect = [&](const uint8_t*, size_t size) { assert(size == packet.size()); ++recovered; };
    for (int i = 0; i < 40; ++i) { noisy.feed(0xd3, collect); noisy.feed(0xff, collect); }
    for (const auto byte : packet) noisy.feed(byte, collect);
    assert(recovered == 1);

    // Cabecera con la longitud máxima y CRC inválido: ocupa el buffer entero y
    // el parser debe recuperarse para aceptar la trama siguiente.
    gnss::Rtcm3Parser flooded;
    unsigned after = 0;
    auto tally = [&](const uint8_t*, size_t) { ++after; };
    flooded.feed(0xd3, tally); flooded.feed(0x03, tally); flooded.feed(0xff, tally);
    for (int i = 0; i < 4000; ++i) flooded.feed(0x00, tally);
    for (const auto byte : packet) flooded.feed(byte, tally);
    assert(after == 1);

    // Regla 1 (0.9.0, como las apps): una cabecera falsa que declara 1029 bytes no
    // retiene la trama buena que viene detrás: sale al completarse, no 1029 bytes después.
    gnss::Rtcm3Parser greedy;
    unsigned early = 0;
    size_t fedWhenEmitted = 0, fed = 0;
    auto first = [&](const uint8_t* data, size_t size) {
        assert(size == packet.size() && data[0] == 0xd3); ++early; fedWhenEmitted = fed;
    };
    for (uint8_t b : {uint8_t(0xd3), uint8_t(0x03), uint8_t(0xff), uint8_t(0x12)}) { greedy.feed(b, first); ++fed; }
    for (const auto byte : packet) { ++fed; greedy.feed(byte, first); }
    assert(early == 1 && fedWhenEmitted == 4 + packet.size() && greedy.abandoned == 1);
    for (const auto byte : packet) greedy.feed(byte, first);       // y el flujo sigue normal
    assert(early == 2 && greedy.rejected == 0);

    // Regla 2: una trama a medias sin bytes nuevos durante 1 s se descarta al
    // llegar el siguiente byte, sin pasar por un CRC fallido.
    gnss::Rtcm3Parser timed, untimed;
    unsigned withClock = 0, withoutClock = 0;
    auto a = [&](const uint8_t*, size_t) { ++withClock; };
    auto b = [&](const uint8_t*, size_t) { ++withoutClock; };
    for (size_t i = 0; i < 4; ++i) { timed.feedAt(packet[i], 100, a); untimed.feed(packet[i], b); }
    for (const auto byte : packet) { timed.feedAt(byte, 1101, a); untimed.feed(byte, b); }
    assert(withClock == 1 && timed.expired == 1 && timed.rejected == 0);
    assert(withoutClock == 1 && untimed.rejected == 1);   // sin reloj: un CRC fallido de por medio
    // Un hueco de menos de 1 s no descarta nada.
    gnss::Rtcm3Parser patient;
    unsigned whole = 0;
    auto c = [&](const uint8_t*, size_t) { ++whole; };
    for (size_t i = 0; i < packet.size(); ++i) patient.feedAt(packet[i], i < 4 ? 0 : 999, c);
    assert(whole == 1 && patient.expired == 0);

    // Casos añadidos en main (placa v0.3 y Thing Plus, mismas reglas).
    // 0.9.0, trama rota tapada por una completa: a una trama de 206 bytes se le
    // pierde el final (una escritura BLE que no llegó) y detrás viene una buena.
    // La buena sale **en cuanto llega su último byte**, sin esperar a los 206.
    gnss::Rtcm3Parser cut;
    std::vector<size_t> sizes;
    auto sizesOf = [&](const uint8_t* data, size_t size) { assert(data[0] == 0xd3); sizes.push_back(size); };
    const std::vector<uint8_t> broken{0xd3, 0x00, 0xc8, 0x43, 0x50, 0x01, 0x02, 0x03, 0x04, 0x05};
    for (const auto byte : broken) cut.feedAt(byte, 0, sizesOf);
    for (size_t i = 0; i < packet.size(); ++i) {
        cut.feedAt(packet[i], 0, sizesOf);
        assert(sizes.size() == (i + 1 == packet.size() ? 1u : 0u));
    }
    assert(cut.abandoned == 1 && cut.accepted == 1 && cut.rejected == 0);
    // Y las siguientes siguen saliendo una a una.
    for (int k = 0; k < 3; ++k) for (const auto byte : packet) cut.feedAt(byte, 0, sizesOf);
    assert(sizes.size() == 4 && cut.accepted == 4);

    // Un 0xD3 con cabecera plausible dentro de una trama buena no la corta: su
    // «trama» no cuadra el CRC y la de fuera sale entera.
    std::vector<uint8_t> carrier{0xd3, 0x00, 0x0c, 0x3e, 0xd0, 0xd3, 0x00, 0x01, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77};
    const auto outer = gnss::crc24q(carrier.data(), carrier.size());
    carrier.push_back(outer >> 16); carrier.push_back(outer >> 8); carrier.push_back(outer);
    gnss::Rtcm3Parser intact;
    std::vector<size_t> got;
    for (const auto byte : carrier) intact.feedAt(byte, 0, [&](const uint8_t*, size_t size) { got.push_back(size); });
    assert(got.size() == 1 && got[0] == carrier.size() && intact.abandoned == 0);

    // Trama a medias sin bytes nuevos: se descarta pasado 1 s, no a los 2 s.
    gnss::Rtcm3Parser idle;
    unsigned fresh = 0;
    auto tick = [&](const uint8_t*, size_t) { ++fresh; };
    for (size_t i = 0; i < 5; ++i) idle.feedAt(packet[i], 100, tick);
    idle.feedAt(packet[5], 1099, tick);            // 999 ms: sigue esperando
    assert(idle.expired == 0);
    for (size_t i = 6; i < packet.size(); ++i) idle.feedAt(packet[i], 1099, tick);
    assert(fresh == 1);
    for (size_t i = 0; i < 5; ++i) idle.feedAt(packet[i], 2000, tick);
    for (const auto byte : packet) idle.feedAt(byte, 3001, tick);   // más de 1 s sin bytes: fuera la vieja
    assert(idle.expired == 1 && fresh == 2 && idle.rejected == 0);
    // El reloj que da la vuelta no la tira antes de tiempo.
    gnss::Rtcm3Parser wrap;
    for (size_t i = 0; i < 5; ++i) wrap.feedAt(packet[i], UINT32_MAX - 100, tick);
    for (size_t i = 5; i < packet.size(); ++i) wrap.feedAt(packet[i], 500, tick);
    assert(wrap.expired == 0 && fresh == 3);
}
