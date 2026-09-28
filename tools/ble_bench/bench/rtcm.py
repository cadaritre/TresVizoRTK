"""RTCM3: CRC-24Q, rearmado como el del ESP32 y generador de tramas de banco.

`Rtcm3Parser` es copia fiel de `firmware/esp32/lib/gnss/src/rtcm3.h`, byte a
byte, con los mismos contadores (`accepted`, `rejected`, `overflow`): lo que
diga aquí sobre un flujo es lo que diría el equipo.

El generador arma tramas **válidas en la capa de transporte** (cabecera, longitud
y CRC-24Q) con los tamaños de un flujo real: MSM4 o MSM7 de cuatro
constelaciones, 1005, 1033 y 1230. El contenido de las observaciones es
sintético: **no es una base de verdad** y el UM980 no puede fijar con él. Sirve
para medir el transporte, no el RTK. Para FLOTANTE → FIJO hace falta un caster.
"""
from __future__ import annotations

import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

PREAMBLE = 0xD3
HEADER_BYTES = 3
CRC_BYTES = 3
MAX_PAYLOAD_BYTES = 1023
MAX_FRAME_BYTES = MAX_PAYLOAD_BYTES + HEADER_BYTES + CRC_BYTES  # 1029, rtcm3.h y correction_router.cpp:46
CRC24Q_POLYNOMIAL = 0x1864CFB


def _crc_table() -> list[int]:
    table = []
    for byte in range(256):
        crc = byte << 16
        for _ in range(8):
            crc <<= 1
            if crc & 0x1000000:
                crc ^= CRC24Q_POLYNOMIAL
        table.append(crc & 0xFFFFFF)
    return table


_CRC_TABLE = _crc_table()


def crc24q(data: bytes) -> int:
    """CRC-24Q de RTCM3. Mismo resultado que gnss::crc24q (por tabla, más rápido)."""
    crc = 0
    for value in data:
        crc = ((crc << 8) & 0xFFFFFF) ^ _CRC_TABLE[((crc >> 16) ^ value) & 0xFF]
    return crc


def crc24q_bitwise(data: bytes) -> int:
    """El mismo algoritmo que rtcm3.h, bit a bit. Solo para comprobar la tabla."""
    crc = 0
    for value in data:
        crc ^= value << 16
        for _ in range(8):
            crc <<= 1
            if crc & 0x1000000:
                crc ^= CRC24Q_POLYNOMIAL
    return crc & 0xFFFFFF


def build_frame(payload: bytes) -> bytes:
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError(f"carga RTCM3 de {len(payload)} bytes; el máximo es {MAX_PAYLOAD_BYTES}")
    head = bytes((PREAMBLE, (len(payload) >> 8) & 0x03, len(payload) & 0xFF)) + payload
    return head + crc24q(head).to_bytes(CRC_BYTES, "big")


def message_number(frame: bytes) -> int | None:
    """Los 12 primeros bits de la carga. None si la trama no llega a tenerlos."""
    if len(frame) < HEADER_BYTES + 2:
        return None
    return (frame[3] << 4) | (frame[4] >> 4)


def frame_is_valid(frame: bytes) -> bool:
    """Las mismas comprobaciones que correction_router::submit (correction_router.cpp:46-51)."""
    if len(frame) < HEADER_BYTES + CRC_BYTES or len(frame) > MAX_FRAME_BYTES:
        return False
    if frame[0] != PREAMBLE or frame[1] & 0xFC:
        return False
    if (((frame[1] & 3) << 8) | frame[2]) + HEADER_BYTES + CRC_BYTES != len(frame):
        return False
    return crc24q(frame[:-CRC_BYTES]) == int.from_bytes(frame[-CRC_BYTES:], "big")


class Rtcm3Parser:
    """Copia de gnss::Rtcm3Parser (rtcm3.h), byte a byte y con sus contadores."""

    def __init__(self) -> None:
        self._bytes = bytearray()
        self.accepted = 0
        self.rejected = 0
        self.overflow = 0

    def reset(self) -> None:
        self._bytes.clear()

    def _resync(self) -> None:
        # Descarta el primer byte y salta al siguiente 0xD3.
        following = self._bytes.find(PREAMBLE, 1)
        if following < 0:
            self._bytes.clear()
        else:
            del self._bytes[:following]

    def feed(self, data: bytes) -> list[bytes]:
        frames = []
        for value in data:
            if len(self._bytes) == MAX_FRAME_BYTES:
                self.overflow += 1
                self._resync()
            self._bytes.append(value)
            while self._bytes:
                buffer = self._bytes
                if buffer[0] != PREAMBLE or (len(buffer) >= 2 and buffer[1] & 0xFC):
                    self._resync()
                    continue
                if len(buffer) < HEADER_BYTES:
                    break
                total = (((buffer[1] & 3) << 8) | buffer[2]) + HEADER_BYTES + CRC_BYTES
                if len(buffer) < total:
                    break
                actual = int.from_bytes(buffer[total - CRC_BYTES:total], "big")
                if crc24q(buffer[:total - CRC_BYTES]) == actual:
                    self.accepted += 1
                    frames.append(bytes(buffer[:total]))
                    del buffer[:total]
                else:
                    self.rejected += 1
                    self._resync()
        return frames

    @property
    def buffered_bytes(self) -> int:
        return len(self._bytes)


# ---------------------------------------------------------------------------
# Generador

class BitWriter:
    def __init__(self) -> None:
        self._value = 0
        self._bits = 0

    def put(self, value: int, bits: int) -> None:
        self._value = (self._value << bits) | (value & ((1 << bits) - 1))
        self._bits += bits

    @property
    def bit_length(self) -> int:
        return self._bits

    def to_bytes(self) -> bytes:
        padding = (-self._bits) % 8
        return (self._value << padding).to_bytes((self._bits + padding) // 8, "big")


# Tamaños por satélite y por celda de RTCM 10403.3, tabla 3.5-78 y siguientes.
MSM_HEADER_FIXED_BITS = 169       # hasta la máscara de señales inclusive (sin celdas)
MSM_BITS = {
    4: {"satellite": 18, "cell": 48},   # rango entero + módulo; fino, fase, bloqueo, medio ciclo, CNR
    7: {"satellite": 36, "cell": 80},   # + info extendida y tasa de fase; campos finos extendidos
}
# Primer número de mensaje MSM de cada constelación (MSM1). MSMn = base + n − 1.
MSM_BASE_NUMBER = {"GPS": 1071, "GLONASS": 1081, "Galileo": 1091, "BeiDou": 1121}
DEFAULT_CONSTELLATIONS = (("GPS", 10, 2), ("GLONASS", 7, 2), ("Galileo", 8, 2), ("BeiDou", 12, 2))
# Estación de referencia de banco. No es ninguna base real.
BENCH_STATION_ID = 4095
# Cada cuánto van los mensajes de estación (1005, 1033, 1230) en un flujo típico.
STATION_MESSAGE_PERIOD_EPOCHS = 10


def _random_bits(writer: BitWriter, bits: int, rng: random.Random) -> None:
    while bits > 0:
        step = min(bits, 32)
        writer.put(rng.getrandbits(step), step)
        bits -= step


def msm_payload(number: int, station_id: int, epoch_ms: int, satellites: int, signals: int,
                msm_kind: int, multiple_message: bool, rng: random.Random) -> bytes:
    """Carga MSM4 o MSM7 con cabecera coherente y observaciones sintéticas."""
    if satellites > 64 or signals > 32 or satellites * signals > 64:
        raise ValueError("MSM: como máximo 64 satélites, 32 señales y 64 celdas")
    bits = MSM_BITS[msm_kind]
    writer = BitWriter()
    writer.put(number, 12)
    writer.put(station_id, 12)
    writer.put(epoch_ms % (7 * 86400000) if number < 1081 or number > 1087 else epoch_ms % 86400000, 30)
    writer.put(1 if multiple_message else 0, 1)
    writer.put(0, 3)       # IODS
    writer.put(0, 7)       # reservado
    writer.put(0, 2)       # dirección del reloj
    writer.put(0, 2)       # reloj externo
    writer.put(0, 1)       # suavizado
    writer.put(0, 3)       # intervalo de suavizado
    satellite_mask = sum(1 << (63 - index) for index in range(satellites))
    signal_mask = sum(1 << (31 - index) for index in (1, 8, 14, 21)[:signals]) if signals <= 4 \
        else sum(1 << (31 - index) for index in range(signals))
    writer.put(satellite_mask, 64)
    writer.put(signal_mask, 32)
    writer.put((1 << (satellites * signals)) - 1, satellites * signals)
    _random_bits(writer, satellites * bits["satellite"], rng)
    _random_bits(writer, satellites * signals * bits["cell"], rng)
    return writer.to_bytes()


def station_1005_payload(station_id: int) -> bytes:
    """1005: 152 bits. Coordenadas ECEF a cero: no es una base real."""
    writer = BitWriter()
    writer.put(1005, 12)
    writer.put(station_id, 12)
    writer.put(0, 6)       # ITRF
    writer.put(0b1111, 4)  # GPS, GLONASS, Galileo, indicador de referencia
    writer.put(0, 38)      # X
    writer.put(0, 1)       # oscilador
    writer.put(0, 1)       # reservado
    writer.put(0, 38)      # Y
    writer.put(0, 2)       # cuarto de ciclo
    writer.put(0, 38)      # Z
    return writer.to_bytes()


def descriptor_1033_payload(station_id: int, antenna: str = "HA-901A NONE",
                            receiver: str = "UNICORE UM980", firmware: str = "BANCO",
                            serial: str = "") -> bytes:
    """1033: descriptores de antena y receptor, de tamaño variable."""
    writer = BitWriter()
    writer.put(1033, 12)
    writer.put(station_id, 12)
    for text, with_setup in ((antenna, True), ("", False), (receiver, False), (firmware, False), (serial, False)):
        encoded = text.encode("ascii")
        writer.put(len(encoded), 8)
        for value in encoded:
            writer.put(value, 8)
        if with_setup:
            writer.put(0, 8)  # identificador de montaje de antena
    return writer.to_bytes()


def glonass_biases_1230_payload(station_id: int) -> bytes:
    """1230: sesgos código-fase de GLONASS con las cuatro señales."""
    writer = BitWriter()
    writer.put(1230, 12)
    writer.put(station_id, 12)
    writer.put(0, 1)       # indicador de alineación
    writer.put(0, 3)       # reservado
    writer.put(0b1111, 4)  # máscara de señales L1 C/A, L1 P, L2 C/A, L2 P
    for _ in range(4):
        writer.put(0, 16)
    return writer.to_bytes()


@dataclass
class EpochProfile:
    """Qué manda una base por época. Por defecto, MSM7 de cuatro constelaciones."""
    msm_kind: int = 7
    constellations: tuple[tuple[str, int, int], ...] = DEFAULT_CONSTELLATIONS
    station_id: int = BENCH_STATION_ID
    station_message_period_epochs: int = STATION_MESSAGE_PERIOD_EPOCHS
    # Número de mensaje de reemplazo para no alimentar al receptor con MSM
    # falsos (modo «inerte»). None = los números reales.
    inert_message_number: int | None = None


@dataclass
class GeneratedFrame:
    frame: bytes
    number: int
    epoch_index: int


class RtcmGenerator:
    """Genera épocas completas, trama a trama, con semilla fija para repetir pruebas."""

    def __init__(self, profile: EpochProfile | None = None, seed: int = 1) -> None:
        self.profile = profile or EpochProfile()
        self._rng = random.Random(seed)
        self.frames_generated = 0
        self.bytes_generated = 0

    def epoch(self, epoch_index: int, epoch_ms: int) -> list[GeneratedFrame]:
        profile = self.profile
        payloads: list[bytes] = []
        if epoch_index % profile.station_message_period_epochs == 0:
            payloads += [station_1005_payload(profile.station_id), descriptor_1033_payload(profile.station_id),
                         glonass_biases_1230_payload(profile.station_id)]
        count = len(profile.constellations)
        for position, (name, satellites, signals) in enumerate(profile.constellations):
            number = MSM_BASE_NUMBER[name] + profile.msm_kind - 1
            payloads.append(msm_payload(number, profile.station_id, epoch_ms, satellites, signals,
                                        profile.msm_kind, position < count - 1, self._rng))
        result = []
        for payload in payloads:
            if profile.inert_message_number is not None:
                payload = bytes(((profile.inert_message_number >> 4) & 0xFF,
                                 ((profile.inert_message_number & 0x0F) << 4) | (payload[1] & 0x0F))) + payload[2:]
            frame = build_frame(payload)
            self.frames_generated += 1
            self.bytes_generated += len(frame)
            result.append(GeneratedFrame(frame, message_number(frame) or 0, epoch_index))
        return result

    def epoch_bytes(self) -> int:
        """Tamaño de una época sin mensajes de estación (para calcular ritmos)."""
        probe = RtcmGenerator(self.profile, seed=0)
        return sum(len(item.frame) for item in probe.epoch(1, 0))

    def frames(self, epoch_interval_ms: int = 1000) -> Iterator[GeneratedFrame]:
        index = 0
        while True:
            yield from self.epoch(index, index * epoch_interval_ms)
            index += 1


def read_frames_from_file(path: Path) -> tuple[list[bytes], Rtcm3Parser]:
    """Tramas válidas de una captura RTCM3 cruda, con el mismo rearmado que el ESP32."""
    parser = Rtcm3Parser()
    frames = parser.feed(Path(path).read_bytes())
    return frames, parser


def find_capture_files(root: Path) -> list[Path]:
    """Capturas RTCM que haya en el repositorio (captures/, data/, tests/)."""
    found = []
    for folder in ("captures", "data", "tests"):
        base = Path(root) / folder
        if not base.is_dir():
            continue
        for current, _, names in os.walk(base):
            for name in names:
                if name.lower().endswith((".rtcm", ".rtcm3", ".rtc")):
                    found.append(Path(current) / name)
    return sorted(found)


@dataclass
class Pacer:
    """Reparte tramas enteras a un ritmo de bytes por segundo (cubeta de fichas).

    `burst_seconds` > 0 imita a un caster que entrega por TCP a golpes: junta
    ese tiempo de tramas y las suelta de una vez.
    """
    bytes_per_second: float
    burst_seconds: float = 0.0
    _credit: float = field(default=0.0, init=False)
    _last: float | None = field(default=None, init=False)

    def due_bytes(self, now: float) -> float:
        if self._last is None:
            self._last = now
            self._credit = self.bytes_per_second * max(self.burst_seconds, 0.0)
            return self._credit
        elapsed = now - self._last
        if self.burst_seconds > 0 and elapsed < self.burst_seconds:
            return self._credit
        self._last = now
        self._credit += elapsed * self.bytes_per_second
        # Sin acumular más de un segundo (o una ráfaga) de atraso: la política
        # de datos viejos del encargo; lo que no salió a tiempo no se amontona.
        # Nunca por debajo de una trama máxima, o una de 1029 bytes no saldría jamás.
        cap = max(self.bytes_per_second * max(1.0, self.burst_seconds), MAX_FRAME_BYTES)
        self._credit = min(self._credit, cap)
        return self._credit

    def spend(self, amount: int) -> None:
        self._credit -= amount
