"""Protocolo BLE v1 del Meridian V, del lado del cliente. Sin radio.

Espejo en Python de lo que codifica el firmware, para decodificar lo que llega
por Bluetooth y comparar con las pruebas de C++:

- `firmware/esp32/lib/protocol/src/ble_frames.h` (tramas de respuesta),
- `firmware/esp32/lib/protocol/src/health_packet.h` (paquete de salud),
- `firmware/esp32/src/ble_transport.cpp` (paquete de solución, UUID, límites).

Si el firmware cambia un offset o un límite, se cambia aquí en un solo sitio.
"""
from __future__ import annotations

import json
import struct
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# UUID (ble_transport.cpp:20-25). Todos comparten sufijo.
UUID_SUFFIX = "-8f24-4adb-a350-77ef6339c320"
SERVICE_UUID = "a04c0001" + UUID_SUFFIX
COMMAND_UUID = "a04c0002" + UUID_SUFFIX
RESPONSE_UUID = "a04c0003" + UUID_SUFFIX
SOLUTION_UUID = "a04c0004" + UUID_SUFFIX
CORRECTION_UUID = "a04c0005" + UUID_SUFFIX
HEALTH_UUID = "a04c0006" + UUID_SUFFIX

# Nombre corto de cada característica, para registros y grabaciones.
CHARACTERISTIC_NAMES = {
    COMMAND_UUID: "command",
    RESPONSE_UUID: "response",
    SOLUTION_UUID: "solution",
    CORRECTION_UUID: "correction",
    HEALTH_UUID: "health",
}
CHARACTERISTIC_UUIDS = {name: uuid for uuid, name in CHARACTERISTIC_NAMES.items()}

# ---------------------------------------------------------------------------
# Límites (ble_frames.h y ble_transport.cpp). Son contrato con el firmware.
RESPONSE_HEADER_BYTES = 5          # id uint16 + offset uint16 + banderas uint8
ATT_HEADER_BYTES = 3               # opcode + handle de ATT
MINIMUM_ATT_MTU = 23               # el que rige hasta que el teléfono negocia
PREFERRED_ATT_MTU = 247            # el que ofrece el equipo (BLEDevice::setMTU)
MAX_NOTIFICATION_BYTES = PREFERRED_ATT_MTU - ATT_HEADER_BYTES
MAX_RESPONSE_BYTES = 4096          # ble_transport.cpp:206, se sustituye por un 413
MAX_REQUEST_BYTES = 1024           # ble_transport.cpp:99, sin contar el LF
REQUEST_EXPIRY_SECONDS = 5.0       # ble_transport.cpp:84 y :184
PARTIAL_RESPONSE_EXPIRY_SECONDS = 5.0  # igual que BLEResponseReassembler.swift
FIRST_FRAME_FLAG = 0x01
LAST_FRAME_FLAG = 0x02
MIN_SOLUTION_INTERVAL_MS = 190     # protocol::kMinSolutionIntervalMs (5 Hz como máximo)
MAX_SOLUTION_RATE_HZ = 5
HEALTH_INTERVAL_MS = 1000          # ble_transport.cpp:255

SOLUTION_PACKET_BYTES = 20
HEALTH_PACKET_BYTES = 20
INT32_MIN = -(2 ** 31)
UNKNOWN_U16 = 0xFFFF
UNKNOWN_SATELLITES = 255
SEQUENCE_MODULO = 1 << 16

# Byte 16 de la salud (health_packet.h).
HEALTH_FLAG_DISPLAY_PRECISION = 0x01  # bytes 1-4 = precisión mostrada por Meridian V
HEALTH_FLAG_RAW_PRECISION = 0x02      # bytes 12-15 = sigma cruda del UM980
# Bit 2: reservado para contadores de RTCM en los bytes 17-19, **pendiente del
# contrato** (docs/connectivity/BLE_CONTRACT.md). Mientras no esté fijado, el
# decodificador expone esos bytes crudos y no los interpreta.
HEALTH_FLAG_EXTENSION = 0x04

# Regla de la precisión mostrada (health_packet.h), en milímetros.
DISPLAY_THRESHOLD_MM = 35
DISPLAY_BASE_HORIZONTAL_MM = 10
DISPLAY_BASE_VERTICAL_MM = 15
DISPLAY_SATURATION_MM = 65534       # para no confundirse con 0xFFFF
SIGMA_MAX_METERS = 65.0             # sigmaToMm: más que esto es «desconocido»

CORRECTION_SOURCES = {0: "ninguna", 1: "BLE", 2: "NTRIP", 3: "radio"}
GGA_QUALITIES = {
    0: "inválida", 1: "autónoma", 2: "diferencial", 3: "PPS", 4: "FIJO",
    5: "FLOTANTE", 6: "estima", 7: "manual", 8: "simulada",
}


class ProtocolError(ValueError):
    """Un paquete que no respeta el protocolo (longitud, versión, campos)."""


# ---------------------------------------------------------------------------
# Tramas de respuesta (a04c0003)

def response_payload_bytes(negotiated_mtu: int) -> int:
    """Bytes de JSON por trama con ese MTU; igual que protocol::responsePayloadBytes."""
    mtu = min(max(negotiated_mtu, MINIMUM_ATT_MTU), PREFERRED_ATT_MTU)
    return mtu - ATT_HEADER_BYTES - RESPONSE_HEADER_BYTES


def encode_response_frame(message_id: int, offset: int, data: bytes, payload_bytes: int) -> bytes:
    """Espejo de protocol::encodeResponseFrame. Para el simulador y las pruebas."""
    total = len(data)
    count = min(payload_bytes, total - offset) if offset < total else 0
    flags = (FIRST_FRAME_FLAG if offset == 0 else 0) | (LAST_FRAME_FLAG if offset + count == total else 0)
    header = struct.pack("<HHB", message_id & 0xFFFF, offset & 0xFFFF, flags)
    return header + data[offset:offset + count]


def encode_response_frames(message_id: int, data: bytes, negotiated_mtu: int) -> list[bytes]:
    """Todas las tramas de un mensaje, como las manda ble_transport.cpp:223."""
    per_frame = response_payload_bytes(negotiated_mtu)
    frames, offset = [], 0
    while True:
        frame = encode_response_frame(message_id, offset, data, per_frame)
        frames.append(frame)
        offset += len(frame) - RESPONSE_HEADER_BYTES
        if frame[4] & LAST_FRAME_FLAG:
            return frames


@dataclass(frozen=True)
class ResponseFrame:
    message_id: int
    offset: int
    flags: int
    payload: bytes

    @property
    def is_first(self) -> bool:
        return bool(self.flags & FIRST_FRAME_FLAG)

    @property
    def is_last(self) -> bool:
        return bool(self.flags & LAST_FRAME_FLAG)


def parse_response_frame(data: bytes) -> ResponseFrame:
    if len(data) < RESPONSE_HEADER_BYTES:
        raise ProtocolError(f"trama de respuesta de {len(data)} bytes, menos que la cabecera de {RESPONSE_HEADER_BYTES}")
    message_id, offset, flags = struct.unpack_from("<HHB", data)
    return ResponseFrame(message_id, offset, flags, bytes(data[RESPONSE_HEADER_BYTES:]))


@dataclass(frozen=True)
class ReassemblyOutcome:
    """Qué pasó al alimentar una trama. `kind` es una de REASSEMBLY_KINDS."""
    kind: str
    message_id: int | None = None
    message: bytes | None = None
    detail: str = ""


# Clasificación de cada trama. Las que no son «pending»/«completed» son anomalías
# que el resumen cuenta; la app, ante cualquiera, descarta el mensaje entero.
REASSEMBLY_KINDS = (
    "pending",        # entró y el mensaje sigue incompleto
    "completed",      # mensaje entero
    "gap",            # falta al menos una trama: offset mayor que el esperado
    "duplicate",      # trama repetida: ya se había recibido ese tramo con el mismo contenido
    "out_of_order",   # llega la trama que faltaba después de haber declarado el hueco
    "orphan",         # continuación de un mensaje del que no se vio la primera trama
    "restarted",      # llega otra primera trama del mismo id con el mensaje a medias
    "invalid_length", # cabecera corta, trama más larga que el MTU, inicio con offset ≠ 0
    "too_large",      # el mensaje pasa de 4096 bytes
    "expired",        # mensaje a medias sin trama nueva en 5 s
)


@dataclass
class _Partial:
    buffer: bytearray
    last_frame_at: float


class ResponseReassembler:
    """Rearma respuestas por desplazamiento, como BLEResponseReassembler.swift.

    Detecta, además de lo que detecta la app, los duplicados y el desorden, para
    saber **por qué** se perdió una respuesta. El comportamiento ante una anomalía
    es el de la app: el mensaje se descarta entero.

    `negotiated_mtu`, si se conoce, sirve para marcar tramas más largas de lo que
    el MTU permite (serían un defecto del firmware o de la pila).
    """

    def __init__(self, negotiated_mtu: int | None = None,
                 partial_expiry_seconds: float = PARTIAL_RESPONSE_EXPIRY_SECONDS):
        self.negotiated_mtu = negotiated_mtu
        self.partial_expiry_seconds = partial_expiry_seconds
        self._partials: dict[int, _Partial] = {}
        # Último hueco por id: si luego llega la trama que faltaba, fue desorden.
        self._gaps: dict[int, int] = {}
        # Último mensaje terminado o descartado por id, para reconocer duplicados.
        self._recent: dict[int, bytes] = {}
        self.counts: dict[str, int] = {kind: 0 for kind in REASSEMBLY_KINDS}

    @property
    def pending_messages(self) -> int:
        return len(self._partials)

    def reset(self) -> None:
        """Se llama al desconectar: el firmware invalida lo encolado (ble_transport.cpp:180)."""
        self._partials.clear()
        self._gaps.clear()
        self._recent.clear()

    def _count(self, outcome: ReassemblyOutcome) -> ReassemblyOutcome:
        self.counts[outcome.kind] += 1
        return outcome

    def _expire(self, now: float) -> list[ReassemblyOutcome]:
        expired = []
        for message_id, partial in list(self._partials.items()):
            if now - partial.last_frame_at >= self.partial_expiry_seconds:
                del self._partials[message_id]
                expired.append(self._count(ReassemblyOutcome("expired", message_id,
                                                             detail=f"{len(partial.buffer)} bytes a medias")))
        return expired

    def feed(self, data: bytes, now: float = 0.0) -> list[ReassemblyOutcome]:
        """Alimenta una notificación. Devuelve lo que pasó (caducados primero)."""
        outcomes = self._expire(now)
        if len(data) < RESPONSE_HEADER_BYTES:
            outcomes.append(self._count(ReassemblyOutcome("invalid_length", None,
                                                          detail=f"{len(data)} bytes, sin cabecera")))
            return outcomes
        frame = parse_response_frame(data)
        if self.negotiated_mtu is not None and len(data) > max(self.negotiated_mtu, MINIMUM_ATT_MTU) - ATT_HEADER_BYTES:
            outcomes.append(self._count(ReassemblyOutcome(
                "invalid_length", frame.message_id,
                detail=f"trama de {len(data)} bytes con MTU {self.negotiated_mtu}")))
            return outcomes
        if frame.is_first and frame.offset != 0:
            outcomes.append(self._count(ReassemblyOutcome("invalid_length", frame.message_id,
                                                          detail=f"trama inicial con offset {frame.offset}")))
            return outcomes
        outcomes.append(self._accept(frame, now))
        return outcomes

    def _accept(self, frame: ResponseFrame, now: float) -> ReassemblyOutcome:
        message_id = frame.message_id
        partial = self._partials.get(message_id)
        if frame.is_first:
            if partial is not None and len(partial.buffer) > 0:
                if bytes(partial.buffer[:len(frame.payload)]) == frame.payload:
                    # La misma primera trama otra vez: duplicado, el mensaje sigue.
                    partial.last_frame_at = now
                    return self._count(ReassemblyOutcome("duplicate", message_id, detail="primera trama repetida"))
                # Otra primera trama con el mensaje a medias: el anterior se perdió.
                self.counts["restarted"] += 1
                partial = _Partial(bytearray(), now)
                self._partials[message_id] = partial
            else:
                # El firmware numera cada respuesta (ble_transport.cpp:207): el
                # mismo id con el mismo contenido es una notificación repetida.
                recent = self._recent.get(message_id)
                repeated = recent is not None and (recent == frame.payload if frame.is_last
                                                   else recent[:len(frame.payload)] == frame.payload)
                if repeated:
                    return self._count(ReassemblyOutcome("duplicate", message_id,
                                                         detail="primera trama de un mensaje ya cerrado"))
                partial = _Partial(bytearray(), now)
                self._partials[message_id] = partial
                self._gaps.pop(message_id, None)
        if partial is None:
            missing = self._gaps.get(message_id)
            if missing is not None and frame.offset == missing:
                del self._gaps[message_id]
                return self._count(ReassemblyOutcome("out_of_order", message_id,
                                                     detail=f"llegó el offset {frame.offset} después del hueco"))
            recent = self._recent.get(message_id)
            if recent is not None and recent[frame.offset:frame.offset + len(frame.payload)] == frame.payload:
                return self._count(ReassemblyOutcome("duplicate", message_id,
                                                     detail=f"offset {frame.offset} de un mensaje ya cerrado"))
            return self._count(ReassemblyOutcome("orphan", message_id, detail=f"offset {frame.offset} sin trama inicial"))
        expected = len(partial.buffer)
        if frame.offset < expected:
            if bytes(partial.buffer[frame.offset:frame.offset + len(frame.payload)]) == frame.payload:
                partial.last_frame_at = now
                return self._count(ReassemblyOutcome("duplicate", message_id, detail=f"offset {frame.offset} repetido"))
            del self._partials[message_id]
            self._recent[message_id] = bytes(partial.buffer)
            return self._count(ReassemblyOutcome("out_of_order", message_id,
                                                 detail=f"offset {frame.offset} por detrás de {expected} con otro contenido"))
        if frame.offset > expected:
            del self._partials[message_id]
            self._gaps[message_id] = expected
            self._recent[message_id] = bytes(partial.buffer)
            return self._count(ReassemblyOutcome("gap", message_id,
                                                 detail=f"esperaba offset {expected}, llegó {frame.offset}"))
        partial.buffer.extend(frame.payload)
        partial.last_frame_at = now
        if len(partial.buffer) > MAX_RESPONSE_BYTES:
            del self._partials[message_id]
            return self._count(ReassemblyOutcome("too_large", message_id, detail=f"{len(partial.buffer)} bytes"))
        if frame.is_last:
            del self._partials[message_id]
            message = bytes(partial.buffer)
            self._recent[message_id] = message
            return self._count(ReassemblyOutcome("completed", message_id, message=message))
        return self._count(ReassemblyOutcome("pending", message_id))


# ---------------------------------------------------------------------------
# Paquete de solución (a04c0004), ble_transport.cpp:239-252

@dataclass(frozen=True)
class SolutionPacket:
    sequence: int
    quality: int
    satellites_used: int | None          # None = 255, desconocido
    utc_time_of_day_ms: int              # hora UTC del día, sin fecha
    latitude_degrees: float | None       # None = INT32_MIN
    longitude_degrees: float | None
    height_msl_meters: float | None      # altura sobre el nivel medio del mar (MSL)

    @property
    def quality_name(self) -> str:
        return GGA_QUALITIES.get(self.quality, f"desconocida ({self.quality})")


def decode_solution(data: bytes) -> SolutionPacket:
    if len(data) != SOLUTION_PACKET_BYTES:
        raise ProtocolError(f"solución de {len(data)} bytes; el protocolo v1 manda {SOLUTION_PACKET_BYTES}")
    sequence, quality, satellites, utc_ms, lat, lon, height = struct.unpack("<HBBIiii", data)
    return SolutionPacket(
        sequence=sequence,
        quality=quality,
        satellites_used=None if satellites == UNKNOWN_SATELLITES else satellites,
        utc_time_of_day_ms=utc_ms,
        latitude_degrees=None if lat == INT32_MIN else lat / 1e7,
        longitude_degrees=None if lon == INT32_MIN else lon / 1e7,
        height_msl_meters=None if height == INT32_MIN else height / 1000.0,
    )


def encode_solution(sequence: int, quality: int, satellites_used: int | None, utc_time_of_day_ms: int,
                    latitude_degrees: float | None, longitude_degrees: float | None,
                    height_msl_meters: float | None) -> bytes:
    """Como ble_transport.cpp:239-251. Para el simulador y las pruebas."""
    def scaled(value: float | None, factor: float) -> int:
        return INT32_MIN if value is None else int(round(value * factor))
    return struct.pack("<HBBIiii", sequence % SEQUENCE_MODULO, quality,
                       UNKNOWN_SATELLITES if satellites_used is None else min(satellites_used, 254),
                       utc_time_of_day_ms & 0xFFFFFFFF, scaled(latitude_degrees, 1e7),
                       scaled(longitude_degrees, 1e7), scaled(height_msl_meters, 1000))


def sequence_gap(previous: int, current: int) -> int:
    """Paquetes perdidos entre dos secuencias de solución, con vuelta a 0 tras 65535.

    0 = consecutivos. Una secuencia repetida o hacia atrás no es un hueco: la
    devuelve negativa para que quien llama la cuente como anomalía (p. ej. el
    equipo se reinició y la secuencia volvió a empezar).
    """
    delta = (current - previous) % SEQUENCE_MODULO
    if delta == 0:
        return -1
    if delta > SEQUENCE_MODULO // 2:
        return -(SEQUENCE_MODULO - delta)
    return delta - 1


# ---------------------------------------------------------------------------
# Paquete de salud (a04c0006), health_packet.h

def meridian_display_precision(um980_precision_mm: int) -> tuple[int, int]:
    """Espejo de protocol::meridianDisplayPrecision: (horizontal, vertical) en mm."""
    if um980_precision_mm == UNKNOWN_U16:
        return UNKNOWN_U16, UNKNOWN_U16
    excess = max(0, um980_precision_mm - DISPLAY_THRESHOLD_MM)
    clamp = lambda mm: min(mm, DISPLAY_SATURATION_MM)  # noqa: E731
    return clamp(DISPLAY_BASE_HORIZONTAL_MM + excess), clamp(DISPLAY_BASE_VERTICAL_MM + excess)


def sigma_to_mm(meters: float) -> int:
    """Espejo de protocol::sigmaToMm (redondeo como std::lround: mitades hacia fuera)."""
    import math
    if not math.isfinite(meters) or meters < 0 or meters > SIGMA_MAX_METERS:
        return UNKNOWN_U16
    return int(math.floor(meters * 1000 + 0.5))


def worst_axis_horizontal_sigma_meters(north: float, east: float, combined: float) -> float:
    import math
    return max(north, east) if math.isfinite(north) and math.isfinite(east) else combined


@dataclass(frozen=True)
class HealthPacket:
    version: int
    display_horizontal_precision_mm: int | None   # bytes 1-2; None = 0xFFFF
    display_vertical_precision_mm: int | None     # bytes 3-4
    correction_age_seconds: int | None            # bytes 5-6; None = sin fuente
    correction_source: int                        # byte 7
    quality: int                                  # byte 8
    imu_reserved: int                             # byte 9
    satellites_tracked: int | None                # byte 10; None = 255
    satellites_visible: int | None                # byte 11; None = 255
    raw_horizontal_sigma_mm: int | None           # bytes 12-13
    raw_vertical_sigma_mm: int | None             # bytes 14-15
    flags: int                                    # byte 16
    extension_bytes: bytes = field(default=b"\x00\x00\x00")  # 17-19, crudos

    @property
    def bytes_1_to_4_are_display_precision(self) -> bool:
        return bool(self.flags & HEALTH_FLAG_DISPLAY_PRECISION)

    @property
    def has_raw_precision(self) -> bool:
        return bool(self.flags & HEALTH_FLAG_RAW_PRECISION)

    @property
    def has_extension(self) -> bool:
        return bool(self.flags & HEALTH_FLAG_EXTENSION)

    @property
    def correction_source_name(self) -> str:
        return CORRECTION_SOURCES.get(self.correction_source, f"desconocida ({self.correction_source})")


def decode_health(data: bytes) -> HealthPacket:
    if len(data) != HEALTH_PACKET_BYTES:
        raise ProtocolError(f"salud de {len(data)} bytes; el protocolo v1 manda {HEALTH_PACKET_BYTES}")
    if data[0] != 1:
        raise ProtocolError(f"versión de salud {data[0]} no soportada (se espera 1)")
    (version, display_h, display_v, age, source, quality, imu, tracked, visible,
     raw_h, raw_v, flags) = struct.unpack_from("<BHHHBBBBBHHB", data)
    unknown16 = lambda value: None if value == UNKNOWN_U16 else value  # noqa: E731
    unknown8 = lambda value: None if value == UNKNOWN_SATELLITES else value  # noqa: E731
    return HealthPacket(
        version=version,
        display_horizontal_precision_mm=unknown16(display_h),
        display_vertical_precision_mm=unknown16(display_v),
        correction_age_seconds=unknown16(age),
        correction_source=source,
        quality=quality,
        imu_reserved=imu,
        satellites_tracked=unknown8(tracked),
        satellites_visible=unknown8(visible),
        raw_horizontal_sigma_mm=unknown16(raw_h),
        raw_vertical_sigma_mm=unknown16(raw_v),
        flags=flags,
        extension_bytes=bytes(data[17:20]),
    )


@dataclass
class HealthInputs:
    """Espejo de protocol::HealthInputs, con los mismos valores por defecto."""
    um980_raw_horizontal_sigma_mm: int = UNKNOWN_U16
    um980_raw_vertical_sigma_mm: int = UNKNOWN_U16
    meridian_display: tuple[int, int] = (UNKNOWN_U16, UNKNOWN_U16)
    correction_age_seconds: int = UNKNOWN_U16
    source: int = 0
    quality: int = 0
    tracked: int = UNKNOWN_SATELLITES
    visible: int = UNKNOWN_SATELLITES


def encode_health(inputs: HealthInputs) -> bytes:
    """Espejo de protocol::encodeHealth (versión 1, bytes 17-19 a cero)."""
    return struct.pack("<BHHHBBBBBHHB3x", 1, inputs.meridian_display[0], inputs.meridian_display[1],
                       inputs.correction_age_seconds, inputs.source, inputs.quality, 0,
                       inputs.tracked, inputs.visible, inputs.um980_raw_horizontal_sigma_mm,
                       inputs.um980_raw_vertical_sigma_mm,
                       HEALTH_FLAG_DISPLAY_PRECISION | HEALTH_FLAG_RAW_PRECISION)


# ---------------------------------------------------------------------------
# Solicitudes (a04c0002)

def encode_request(request_id: int, method: str, path: str, body: object | None = None) -> bytes:
    """Una línea JSON terminada en LF, como la consola USB (`{id, method, path, body}`)."""
    payload: dict[str, object] = {"id": request_id, "method": method, "path": path}
    if body is not None:
        payload["body"] = body
    line = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(line) > MAX_REQUEST_BYTES:
        raise ProtocolError(f"solicitud de {len(line)} bytes; el firmware admite {MAX_REQUEST_BYTES}")
    return line + b"\n"


def chunk_for_write(data: bytes, negotiated_mtu: int) -> list[bytes]:
    """Trozos de MTU − 3, como BLERequestChunker.swift. El firmware rearma por bytes."""
    size = max(1, max(negotiated_mtu, MINIMUM_ATT_MTU) - ATT_HEADER_BYTES)
    return [data[offset:offset + size] for offset in range(0, len(data), size)]


def decode_response_json(message: bytes) -> dict:
    """El JSON de una respuesta rearmada. ProtocolError si no es un objeto JSON."""
    try:
        value = json.loads(message.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise ProtocolError(f"respuesta que no es JSON: {error}") from error
    if not isinstance(value, dict):
        raise ProtocolError("respuesta JSON que no es un objeto")
    return value
