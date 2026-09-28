"""Meridian V simulado en proceso, para probar el banco sin radio.

Reproduce lo que hace `firmware/esp32/src/ble_transport.cpp` en lo que el banco
puede observar, **incluidos sus defectos conocidos**, para que los escenarios y
el resumen se ensayen hoy y mañana digan lo mismo contra el equipo:

- órdenes: rearmado por LF, cola de dos, caducidad de 5 s, una respuesta a la
  vez en tramas del MTU con 5 ms entre tramas (`:218`);
- solución a 5 Hz como máximo y salud a 1 Hz **solo detrás de una solución
  nueva** (`:233`, `:255`): con el receptor mudo no sale ninguna de las dos;
- RTCM: rearmado con CRC, admisión solo si la fuente activa es BLE, cola hacia
  la UART, caducidad de 2 s y los mismos contadores.

Por defecto imita el contrato v3 (firmware 0.7.11, BLE_CONTRACT.md): salud a
1 Hz siempre, con contadores de RTCM; `a04c0005` con escritura sin respuesta;
cola por bytes (8 KiB) que desaloja las tramas más viejas. Con
`protocol_version=2` vuelve a 0.7.10: salud solo detrás de una solución y cola
de cuatro tramas. `stale_gatt=True` imita una pila que recuerda la tabla GATT
de un firmware viejo (sin salud ni escritura sin respuesta).

No es el firmware: el tiempo de radio, el intervalo de conexión y la pila
Bluedroid no se simulan. Lo que pase aquí no demuestra nada del equipo real.
"""
from __future__ import annotations

import asyncio
import json
import random
from collections import deque
from dataclasses import dataclass

from . import protocol as p
from . import rtcm
from .link import Link, LinkError, NotifyCallback

# Mismos valores que el firmware; el motivo de cada uno está allí.
REQUEST_QUEUE_DEPTH = 2              # ble_transport.cpp:132
RESPONSE_FRAME_SPACING_S = 0.005     # ble_transport.cpp:218
TELEMETRY_TICK_S = 0.020             # ble_transport.cpp:229
UART_QUEUE_FRAMES = 4                # v2: gnss_receiver.cpp:137
UART_QUEUE_CAPACITY_BYTES = 8192     # v3: correction_queue_capacity_bytes
UART_QUEUE_RECORD_HEADER_BYTES = 10  # v3: rtcm_queue.h, kRecordHeaderBytes
CORRECTION_EXPIRY_S = 2.0            # gnss_receiver.cpp:94
PARSER_IDLE_RESET_S = 2.0            # ble_transport.cpp:115
UART_BYTES_PER_SECOND = 11520        # 115200 baudios, 8N1 (platformio.ini)
RECEIVER_EPOCH_S = 0.1               # el UM980 a 10 Hz; el firmware manda 1 de cada 2
# Tiempo que tarda una escritura con respuesta: un intervalo de conexión típico
# de iPhone/Mac. Solo para que el banco no escriba infinitamente rápido.
SIMULATED_ATT_ROUND_TRIP_S = 0.015


@dataclass
class SimulatorOptions:
    receiver_talking: bool = True
    write_without_response: bool = True
    mtu: int = 185
    response_frame_drop_probability: float = 0.0
    response_frame_duplicate_probability: float = 0.0
    seed: int = 7
    firmware_version: str = "simulador"
    protocol_version: int = 3
    stale_gatt: bool = False


class SimulatedMeridian:
    """El equipo: estado y contadores que sobreviven a las conexiones."""

    def __init__(self, options: SimulatorOptions | None = None):
        self.options = options or SimulatorOptions()
        self.rng = random.Random(self.options.seed)
        self.generation = 0
        self.connection: "SimulatedLink | None" = None
        self.selected_source = "none"
        self.source_generation = 0
        self.message_id = 0
        self.dropped_requests = 0
        self.forced_frames = 0
        self.ble_parser = rtcm.Rtcm3Parser()
        self.ble_dropped = 0
        self.router_accepted = 0
        self.router_rejected = 0
        self.uart_sent = 0
        self.uart_dropped = 0
        self.uart_evicted = 0
        self.uart_expired = 0
        self.uart_bytes_written = 0
        self.uart_queue_bytes = 0
        self.uart_queue_high_water = 0
        self.telemetry_skipped = 0
        self.uart_queue: deque = deque()
        self.uart_in_flight = None
        self.accepted_gga = 0
        self.sequence = 0

    # -- HTTP sobre BLE -----------------------------------------------------
    @property
    def v3(self) -> bool:
        return self.options.protocol_version >= 3

    def ble_status(self) -> dict:
        connected = self.connection is not None and self.connection.is_connected
        extra = {"rtcm_write_without_response": self.options.write_without_response, "health_period_ms": 1000,
                 "conn_interval_ms": 30.0 if connected else None, "telemetry_skipped": self.telemetry_skipped,
                 "max_loop_gap_ms": 5, "max_request_dispatch_ms": 3} if self.v3 else {}
        return {**extra, 
            "state": "connected" if connected else "advertising",
            "enabled": True, "pairing_required": False, "protocol_version": self.options.protocol_version,
            "dropped_requests": self.dropped_requests,
            "att_mtu": self.connection.negotiated_mtu if connected else p.MINIMUM_ATT_MTU,
            "response_frames_forced": self.forced_frames, "control_available": True,
            "rtcm_available": True, "rtcm_valid_frames": self.ble_parser.accepted,
            "rtcm_crc_errors": self.ble_parser.rejected, "rtcm_dropped_frames": self.ble_dropped,
            "file_download_available": False, "telemetry_hardware_validated": False,
        }

    def status_body(self) -> dict:
        silent = not self.options.receiver_talking
        return {
            "api_version": 1, "firmware_version": self.options.firmware_version,
            "uptime_ms": 0, "free_heap_bytes": 150000, "min_free_heap_bytes": 120000,
            "subsystems": {
                "ble": self.ble_status(),
                "gnss": {"state": "waiting_data" if silent else "receiving",
                         "accepted_gga": self.accepted_gga, "rejected_gga": 0, "line_overflows": 0,
                         "uart_errors": 0, "correction_frames_sent": self.uart_sent,
                         "correction_frames_dropped": self.uart_dropped,
                         "native_frames_valid": 0, "native_frames_invalid": 0,
                         **({"correction_bytes_written": self.uart_bytes_written,
                             "correction_frames_evicted": self.uart_evicted,
                             "correction_frames_expired": self.uart_expired,
                             "correction_queue_bytes": self.uart_queue_bytes,
                             "correction_queue_high_water_bytes": self.uart_queue_high_water,
                             "correction_queue_capacity_bytes": UART_QUEUE_CAPACITY_BYTES} if self.v3 else {})},
            },
            "corrections": {"active_source": self.selected_source, "chosen_source": self.selected_source,
                            "format": "rtcm3", "generation": self.source_generation,
                            "accepted_frames": self.router_accepted, "rejected_frames": self.router_rejected,
                            "age_ms": None},
            "receiver_role": "rover",
            "alerts": [{"code": "receiver_silent", "level": "error", "message": "…"}] if silent else [],
        }

    def handle(self, request: dict) -> tuple[int, dict]:
        method, path, body = request.get("method"), request.get("path"), request.get("body")
        if path == "/api/status" and method == "GET":
            return 200, self.status_body()
        if path == "/api/ble" and method == "GET":
            return 200, self.ble_status()
        if path == "/api/corrections/source":
            if method == "PUT":
                source = body.get("source") if isinstance(body, dict) else None
                if source not in ("none", "ble", "ntrip"):
                    return 400, {"error": "unsupported_source"}
                if source != self.selected_source:
                    self.selected_source = source
                    self.source_generation += 1
            return 200, {"active_source": self.selected_source, "generation": self.source_generation,
                         "accepted_frames": self.router_accepted, "rejected_frames": self.router_rejected}
        if path == "/api/gnss/sky" and method == "GET":
            # Unos 2.5 kB, como el cielo con cuarenta satélites.
            return 200, {"satellites": [{"id": f"G{i:02d}", "elevation_deg": i, "azimuth_deg": i * 7,
                                         "cn0_dbhz": 40, "used": i % 2 == 0} for i in range(40)]}
        return 404, {"error": "not_found"}

    # -- RTCM ---------------------------------------------------------------
    def health_inputs(self) -> p.HealthInputs:
        source = {"none": 0, "ble": 1, "ntrip": 2}.get(self.selected_source, 0)
        talking = self.options.receiver_talking
        inputs = p.HealthInputs(
            um980_raw_horizontal_sigma_mm=12 if talking else p.UNKNOWN_U16,
            um980_raw_vertical_sigma_mm=20 if talking else p.UNKNOWN_U16,
            meridian_display=p.meridian_display_precision(12 if talking else p.UNKNOWN_U16),
            correction_age_seconds=1 if source and self.router_accepted else p.UNKNOWN_U16, source=source,
            quality=4 if talking else 0, tracked=34 if talking else p.UNKNOWN_SATELLITES,
            visible=40 if talking else p.UNKNOWN_SATELLITES)
        if self.v3:
            inputs.has_rtcm_counters = True
            inputs.rtcm_frames_discarded = self.uart_dropped % 256
            inputs.rtcm_frames_rejected = (self.router_rejected + self.ble_parser.rejected) % 256
            inputs.rtcm_queue_percent = p.queue_percent(self.uart_queue_bytes, UART_QUEUE_CAPACITY_BYTES)
        return inputs

    def submit_correction(self, frame: bytes, now: float) -> None:
        if self.v3:
            self._submit_v3(frame, now)
            return
        if self.selected_source != "ble" or not rtcm.frame_is_valid(frame) or len(self.uart_queue) >= UART_QUEUE_FRAMES:
            if len(self.uart_queue) >= UART_QUEUE_FRAMES:
                self.uart_dropped += 1
            self.router_rejected += 1
            self.ble_dropped += 1
            return
        self.router_accepted += 1
        self.uart_queue.append((now, self.source_generation, len(frame)))

    def _submit_v3(self, frame: bytes, now: float) -> None:
        """Como 0.7.11: la cola por bytes nunca rechaza; desaloja las más viejas."""
        if self.selected_source != "ble" or not rtcm.frame_is_valid(frame):
            self.router_rejected += 1
            self.ble_dropped += 1
            return
        needed = UART_QUEUE_RECORD_HEADER_BYTES + len(frame)
        while UART_QUEUE_CAPACITY_BYTES - self.uart_queue_bytes < needed and self.uart_queue:
            _, _, length = self.uart_queue.popleft()
            self.uart_queue_bytes -= UART_QUEUE_RECORD_HEADER_BYTES + length
            self.uart_evicted += 1
            self.uart_dropped += 1
        self.router_accepted += 1
        self.uart_queue.append((now, self.source_generation, len(frame)))
        self.uart_queue_bytes += needed
        self.uart_queue_high_water = max(self.uart_queue_high_water, self.uart_queue_bytes)

    def drain_uart(self, now: float, elapsed_s: float) -> None:
        budget = UART_BYTES_PER_SECOND * elapsed_s
        while budget > 0:
            if self.uart_in_flight is None:
                if not self.uart_queue:
                    return
                self.uart_in_flight = list(self.uart_queue.popleft()) + [0]
                self.uart_queue_bytes = max(0, self.uart_queue_bytes - UART_QUEUE_RECORD_HEADER_BYTES
                                            - self.uart_in_flight[2])
            arrival, generation, length, sent = self.uart_in_flight
            if sent == 0 and (now - arrival > CORRECTION_EXPIRY_S or generation != self.source_generation):
                self.uart_dropped += 1
                self.uart_expired += 1
                self.uart_in_flight = None
                continue
            step = min(length - sent, budget)
            budget -= step
            self.uart_in_flight[3] = sent + step
            self.uart_bytes_written += step
            if self.uart_in_flight[3] >= length:
                self.uart_sent += 1
                self.uart_in_flight = None


class SimulatedLink(Link):
    """Una conexión al equipo simulado. Una nueva por cada intento, como con bleak."""

    def __init__(self, device: SimulatedMeridian):
        self.device = device
        self._connected = False
        self._callbacks: dict[str, NotifyCallback] = {}
        self._tasks: list[asyncio.Task] = []
        self._requests: deque = deque()
        self._command_buffer = bytearray()
        self._command_started = 0.0
        self._last_correction_byte = -1e9
        self._seen_source_generation = -1
        self.on_unexpected_disconnect = None

    @property
    def description(self) -> str:
        return "simulador en proceso (no es el equipo)"

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def negotiated_mtu(self) -> int | None:
        return self.device.options.mtu if self._connected else None

    def properties(self, characteristic_uuid: str) -> set[str]:
        options = self.device.options
        if characteristic_uuid == p.CORRECTION_UUID:
            announced = options.write_without_response and self.device.v3 and not options.stale_gatt
            return {"write", "write-without-response"} if announced else {"write"}
        if characteristic_uuid == p.COMMAND_UUID:
            return {"write"}
        if characteristic_uuid == p.HEALTH_UUID and options.stale_gatt:
            return set()
        return {"notify"}

    async def connect(self) -> None:
        if self.device.connection is not None and self.device.connection.is_connected:
            raise LinkError("el equipo simulado ya tiene un cliente conectado")
        self.device.connection = self
        self.device.generation += 1
        self.device.ble_parser.reset()
        self._connected = True
        loop = asyncio.get_running_loop()
        self._tasks = [loop.create_task(self._responses()), loop.create_task(self._telemetry()),
                       loop.create_task(self._uart())]

    async def _stop(self) -> None:
        if not self._connected:
            return
        self._connected = False
        self.device.generation += 1
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        self._callbacks.clear()

    async def disconnect(self) -> None:
        await self._stop()

    async def drop(self) -> None:
        """Pérdida del enlace que el banco no pidió (fuera de alcance, reinicio)."""
        await self._stop()
        if self.on_unexpected_disconnect:
            self.on_unexpected_disconnect()

    async def start_notify(self, characteristic_uuid: str, callback: NotifyCallback) -> None:
        if not self._connected:
            raise LinkError("sin conexión")
        self._callbacks[characteristic_uuid] = callback

    def _notify(self, uuid: str, data: bytes) -> None:
        callback = self._callbacks.get(uuid)
        if callback is not None and self._connected:
            callback(bytes(data))

    async def write(self, characteristic_uuid: str, data: bytes, with_response: bool) -> None:
        if not self._connected:
            raise LinkError("sin conexión")
        if not with_response and "write-without-response" not in self.properties(characteristic_uuid):
            raise LinkError("la característica no admite escritura sin respuesta")
        loop = asyncio.get_running_loop()
        now = loop.time()
        if characteristic_uuid == p.COMMAND_UUID:
            self._command(bytes(data), now)
        elif characteristic_uuid == p.CORRECTION_UUID:
            if now - self._last_correction_byte > PARSER_IDLE_RESET_S or \
                    self._seen_source_generation != self.device.source_generation:
                self.device.ble_parser.reset()
            self._seen_source_generation = self.device.source_generation
            self._last_correction_byte = now
            for frame in self.device.ble_parser.feed(bytes(data)):
                self.device.submit_correction(frame, now)
        else:
            raise LinkError(f"característica no escribible: {characteristic_uuid}")
        await asyncio.sleep(SIMULATED_ATT_ROUND_TRIP_S if with_response else 0)

    def _command(self, data: bytes, now: float) -> None:
        if self._command_buffer and now - self._command_started > p.REQUEST_EXPIRY_SECONDS:
            self._command_buffer.clear()
        for value in data:
            if not self._command_buffer:
                self._command_started = now
            if value == 0x0A:
                if len(self._requests) >= REQUEST_QUEUE_DEPTH or not self._command_buffer:
                    self.device.dropped_requests += 1
                else:
                    self._requests.append((now, bytes(self._command_buffer)))
                self._command_buffer.clear()
            elif value != 0x0D:
                self._command_buffer.append(value)

    async def _responses(self) -> None:
        loop = asyncio.get_running_loop()
        device = self.device
        while True:
            await asyncio.sleep(RESPONSE_FRAME_SPACING_S)
            if not self._requests:
                continue
            arrival, raw = self._requests.popleft()
            if loop.time() - arrival > p.REQUEST_EXPIRY_SECONDS:
                device.dropped_requests += 1
                continue
            try:
                request = json.loads(raw)
                if not isinstance(request, dict) or not isinstance(request.get("id"), int):
                    raise ValueError
                status, body = device.handle(request)
                output = {"id": request["id"], "status": status, "body": body}
            except ValueError:
                output = {"status": 400, "body": {"error": "invalid_request"}}
            text = json.dumps(output, separators=(",", ":")).encode()
            if len(text) > p.MAX_RESPONSE_BYTES:
                text = b'{"status":413,"body":{"error":"response_too_large"}}'
            device.message_id = (device.message_id + 1) & 0xFFFF
            for frame in p.encode_response_frames(device.message_id, text, self.negotiated_mtu or p.MINIMUM_ATT_MTU):
                if device.rng.random() >= device.options.response_frame_drop_probability:
                    self._notify(p.RESPONSE_UUID, frame)
                if device.rng.random() < device.options.response_frame_duplicate_probability:
                    self._notify(p.RESPONSE_UUID, frame)
                await asyncio.sleep(RESPONSE_FRAME_SPACING_S)

    async def _telemetry(self) -> None:
        loop = asyncio.get_running_loop()
        device = self.device
        last_solution = last_health = -1e9
        last_epoch = -1e9
        while True:
            await asyncio.sleep(TELEMETRY_TICK_S)
            now = loop.time()
            if device.v3 and now - last_health >= p.HEALTH_INTERVAL_MS / 1000:
                # v3: salud a 1 Hz siempre, haya solución o no (latido).
                last_health = now
                self._notify(p.HEALTH_UUID, p.encode_health(device.health_inputs()))
            if not device.options.receiver_talking:
                continue  # sin época nueva no sale solución (ni salud en v2)
            if now - last_epoch >= RECEIVER_EPOCH_S:
                last_epoch = now
                device.accepted_gga += 1
            if now - last_solution < p.MIN_SOLUTION_INTERVAL_MS / 1000:
                continue
            last_solution = now
            device.sequence = (device.sequence + 1) % p.SEQUENCE_MODULO
            utc_ms = int((now * 1000) % 86_400_000)
            self._notify(p.SOLUTION_UUID, p.encode_solution(device.sequence, 4, 28, utc_ms,
                                                            19.4326077, -99.1332080, 2240.5))
            if device.v3 or now - last_health < p.HEALTH_INTERVAL_MS / 1000:
                continue
            last_health = now  # v2: la salud solo sale detrás de una solución nueva
            self._notify(p.HEALTH_UUID, p.encode_health(device.health_inputs()))

    async def _uart(self) -> None:
        loop = asyncio.get_running_loop()
        last = loop.time()
        while True:
            await asyncio.sleep(0.01)
            now = loop.time()
            self.device.drain_uart(now, now - last)
            last = now
