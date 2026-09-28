"""Análisis de una sesión: el mismo código en vivo y al reproducir una grabación.

Consume `session.Event` y acumula: caudal por característica, huecos en la
secuencia de solución, intervalos máximos entre notificaciones, latencias de las
órdenes, anomalías del rearmado, cuentas de RTCM por etapa y el estado del
equipo antes y después. `render()` da el resumen en español.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import protocol as p
from .session import Event

# Qué contadores del equipo interesan, dónde viven en /api/status y cómo se
# llaman en el resumen. Rutas verificadas en el firmware: ble_transport.cpp:263,
# correction_router.cpp:68, instrument.cpp:727-738.
STATUS_COUNTERS = {
    "ble.rtcm_valid_frames": ("subsystems", "ble", "rtcm_valid_frames"),
    "ble.rtcm_crc_errors": ("subsystems", "ble", "rtcm_crc_errors"),
    "ble.rtcm_dropped_frames": ("subsystems", "ble", "rtcm_dropped_frames"),
    "ble.dropped_requests": ("subsystems", "ble", "dropped_requests"),
    "ble.response_frames_forced": ("subsystems", "ble", "response_frames_forced"),
    "corrections.accepted_frames": ("corrections", "accepted_frames"),
    "corrections.rejected_frames": ("corrections", "rejected_frames"),
    "gnss.correction_frames_sent": ("subsystems", "gnss", "correction_frames_sent"),
    "gnss.correction_frames_dropped": ("subsystems", "gnss", "correction_frames_dropped"),
    "gnss.accepted_gga": ("subsystems", "gnss", "accepted_gga"),
    "gnss.rejected_gga": ("subsystems", "gnss", "rejected_gga"),
    "gnss.native_frames_valid": ("subsystems", "gnss", "native_frames_valid"),
    "gnss.uart_errors": ("subsystems", "gnss", "uart_errors"),
    # Contrato v3 (0.7.11). En un firmware anterior no existen y quedan en None.
    "ble.telemetry_skipped": ("subsystems", "ble", "telemetry_skipped"),
    "gnss.correction_bytes_written": ("subsystems", "gnss", "correction_bytes_written"),
    "gnss.correction_frames_evicted": ("subsystems", "gnss", "correction_frames_evicted"),
    "gnss.correction_frames_expired": ("subsystems", "gnss", "correction_frames_expired"),
}
STATUS_FIELDS = {
    "firmware_version": ("firmware_version",),
    "uptime_ms": ("uptime_ms",),
    "free_heap_bytes": ("free_heap_bytes",),
    "min_free_heap_bytes": ("min_free_heap_bytes",),
    "ble.state": ("subsystems", "ble", "state"),
    "ble.att_mtu": ("subsystems", "ble", "att_mtu"),
    "ble.protocol_version": ("subsystems", "ble", "protocol_version"),
    "ble.rtcm_available": ("subsystems", "ble", "rtcm_available"),
    "corrections.active_source": ("corrections", "active_source"),
    "corrections.age_ms": ("corrections", "age_ms"),
    "gnss.state": ("subsystems", "gnss", "state"),
    "receiver_role": ("receiver_role",),
    "ble.rtcm_write_without_response": ("subsystems", "ble", "rtcm_write_without_response"),
    "ble.conn_interval_ms": ("subsystems", "ble", "conn_interval_ms"),
    "ble.health_period_ms": ("subsystems", "ble", "health_period_ms"),
    "ble.max_loop_gap_ms": ("subsystems", "ble", "max_loop_gap_ms"),
    "ble.max_request_dispatch_ms": ("subsystems", "ble", "max_request_dispatch_ms"),
    "gnss.correction_queue_bytes": ("subsystems", "gnss", "correction_queue_bytes"),
    "gnss.correction_queue_high_water_bytes": ("subsystems", "gnss", "correction_queue_high_water_bytes"),
    "gnss.correction_queue_capacity_bytes": ("subsystems", "gnss", "correction_queue_capacity_bytes"),
}
# Lo que el banco guarda de GET /api/ble (el mismo objeto que subsystems.ble).
BLE_STATUS_KEYS = ("state", "protocol_version", "att_mtu", "rtcm_write_without_response", "health_period_ms",
                   "conn_interval_ms", "rtcm_available", "response_frames_forced", "telemetry_skipped")
# La cola del ESP32 hacia la UART hasta 0.7.10: cuatro tramas (gnss_receiver.cpp:137).
# Lo que queda dentro al tomar la foto no es pérdida. Desde 0.7.11 la cola es por
# bytes y el estado dice cuántos hay dentro (`correction_queue_bytes`).
DEVICE_UART_QUEUE_FRAMES = 4
PERCENTILES = (50, 95)
RATE_SHORTFALL_RATIO = 0.95  # por debajo del 95 % del ritmo pedido se avisa
MAX_TRANSITIONS_SHOWN = 20   # el resumen enseña las primeras; el CSV las tiene todas


def GGA_NAME(quality: int) -> str:  # noqa: N802 - mismo nombre que la tabla del protocolo
    return p.GGA_QUALITIES.get(quality, f"desconocida ({quality})")


def extract_status(body: dict) -> dict:
    """Lo que el banco guarda de /api/status: contadores y estado, nada más."""
    def dig(path):
        value = body
        for key in path:
            if not isinstance(value, dict) or key not in value:
                return None
            value = value[key]
        return value
    snapshot = {name: dig(path) for name, path in {**STATUS_COUNTERS, **STATUS_FIELDS}.items()}
    snapshot["alerts"] = sorted(a.get("code", "?") for a in (body.get("alerts") or []) if isinstance(a, dict))
    return snapshot


def percentile(values: list[float], rank: float) -> float | None:
    """Percentil por el método del rango más cercano. None sin datos."""
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(rank / 100 * len(ordered)) - 1)
    return ordered[index]


@dataclass
class StreamStats:
    count: int = 0
    total_bytes: int = 0
    first_t: float | None = None
    last_t: float | None = None
    max_interval_s: float = 0.0
    max_interval_at_s: float | None = None
    intervals: list[float] = field(default_factory=list)
    connections: int = 1

    def add(self, t: float, size: int) -> None:
        if self.first_t is not None and self.last_t is None:
            self.connections += 1
        if self.last_t is not None:
            interval = t - self.last_t
            self.intervals.append(interval)
            if interval > self.max_interval_s:
                self.max_interval_s, self.max_interval_at_s = interval, t
        if self.first_t is None:
            self.first_t = t
        self.last_t = t
        self.count += 1
        self.total_bytes += size

    def break_continuity(self) -> None:
        """Tras conectar o desconectar: el hueco entre dos conexiones no es un intervalo."""
        self.last_t = None

    def rate_hz(self) -> float | None:
        """Ritmo medio dentro de las conexiones (sin contar los huecos entre ellas)."""
        if len(self.intervals) < 1:
            return None
        span = sum(self.intervals)
        return len(self.intervals) / span if span > 0 else None


class Analyzer:
    """Acumula una sesión evento a evento. Ver `render()` para el resumen."""

    def __init__(self) -> None:
        self.streams: dict[str, StreamStats] = {}
        self.reassembler = p.ResponseReassembler()
        self.solution_decode_errors = 0
        self.health_decode_errors = 0
        self.solution_missing = 0
        self.solution_anomalies = 0
        self.last_solution: p.SolutionPacket | None = None
        self.last_health: p.HealthPacket | None = None
        self.health_with_rtcm_counters = 0
        self.health_rtcm_discarded = 0     # suma de diferencias módulo 256 del byte 17
        self.health_rtcm_rejected = 0      # ídem byte 18
        self.health_queue_percent_max: int | None = None
        self._health_previous: p.HealthPacket | None = None
        self.gatt: dict[str, list[str]] = {}
        self.ble_status: dict = {}
        self.gatt_warnings: list[str] = []
        self.qualities: dict[str, int] = {}
        # Cambios de calidad (FLOTANTE → FIJO…) con su instante de llegada. No se
        # borra al reconectar: interesa la historia entera de la sesión.
        self.quality_transitions: list[tuple[float, str, str]] = []
        self._last_quality: int | None = None
        self.pending_requests: dict[int, tuple[float, str, str]] = {}
        self.latencies_s: list[float] = []
        self.latency_by_path: dict[str, list[float]] = {}
        self.responses_by_status: dict[int, int] = {}
        self.request_timeouts = 0
        self.requests_cancelled = 0
        self.uncorrelated_responses = 0
        self.invalid_json_responses = 0
        self.requests_sent = 0
        self.completed: list[tuple[float, dict]] = []
        self.rtcm_generated_frames = self.rtcm_generated_bytes = 0
        self.rtcm_sent_frames = self.rtcm_sent_bytes = 0
        self.rtcm_sent_invalid = 0      # corruptas a propósito: no cuentan como esperadas
        self.rtcm_sent_valid_bytes = 0
        self.rtcm_writes = 0
        self.rtcm_write_failures = 0
        self.rtcm_discarded_frames = 0
        self.rtcm_discarded_by_reason: dict[str, int] = {}
        self.rtcm_target_rates: list[float] = []
        self.rtcm_first_t: float | None = None
        self.rtcm_last_t: float | None = None
        self.rtcm_write_modes: set[str] = set()
        self.rtcm_frame_durations_s: list[float] = []
        self.command_write_failures = 0
        self.connects = 0
        self.disconnects_expected = 0
        self.disconnects_unexpected = 0
        self.connect_failures = 0
        self.ready_times_s: list[float] = []
        self.mtu_values: list[int] = []
        self.statuses: list[tuple[float, str, dict]] = []
        self.notes: list[str] = []
        self.first_t: float | None = None
        self.last_t: float | None = None

    # -- entrada ----------------------------------------------------------
    def consume(self, event: Event) -> list[dict]:
        """Procesa un evento. Devuelve las respuestas JSON completadas por él."""
        if self.first_t is None:
            self.first_t = event.t
        self.last_t = event.t
        handler = getattr(self, "_on_" + event.kind, None)
        if handler is None:
            return []
        return handler(event) or []

    def _on_notify(self, event: Event) -> list[dict]:
        name = event.characteristic or "?"
        data = event.data or b""
        self.streams.setdefault(name, StreamStats()).add(event.t, len(data))
        if name == "solution":
            self._solution(data, event.t)
        elif name == "health":
            self._health(data)
        elif name == "response":
            return self._response(event.t, data)
        return []

    def _solution(self, data: bytes, t: float = 0.0) -> None:
        try:
            packet = p.decode_solution(data)
        except p.ProtocolError:
            self.solution_decode_errors += 1
            return
        if self.last_solution is not None:
            gap = p.sequence_gap(self.last_solution.sequence, packet.sequence)
            if gap > 0:
                self.solution_missing += gap
            elif gap < 0:
                self.solution_anomalies += 1
        if self._last_quality is not None and packet.quality != self._last_quality:
            self.quality_transitions.append((t, GGA_NAME(self._last_quality), packet.quality_name))
        self._last_quality = packet.quality
        self.last_solution = packet
        self.qualities[packet.quality_name] = self.qualities.get(packet.quality_name, 0) + 1

    def _health(self, data: bytes) -> None:
        try:
            packet = p.decode_health(data)
        except p.ProtocolError:
            self.health_decode_errors += 1
            return
        previous, self._health_previous = self._health_previous, packet
        self.last_health = packet
        if not packet.has_rtcm_counters:
            return
        self.health_with_rtcm_counters += 1
        if packet.rtcm_queue_percent is not None:
            self.health_queue_percent_max = max(self.health_queue_percent_max or 0, packet.rtcm_queue_percent)
        if previous is not None and previous.has_rtcm_counters:
            self.health_rtcm_discarded += p.counter_delta_mod256(previous.rtcm_frames_discarded_mod256,
                                                                 packet.rtcm_frames_discarded_mod256)
            self.health_rtcm_rejected += p.counter_delta_mod256(previous.rtcm_frames_rejected_mod256,
                                                                packet.rtcm_frames_rejected_mod256)

    def _response(self, t: float, data: bytes) -> list[dict]:
        done = []
        for outcome in self.reassembler.feed(data, t):
            if outcome.kind != "completed":
                continue
            try:
                message = p.decode_response_json(outcome.message)
            except p.ProtocolError:
                self.invalid_json_responses += 1
                continue
            request_id = message.get("id")
            status = message.get("status")
            if isinstance(status, int):
                self.responses_by_status[status] = self.responses_by_status.get(status, 0) + 1
            pending = self.pending_requests.pop(request_id, None) if isinstance(request_id, int) else None
            if pending is None:
                self.uncorrelated_responses += 1
            else:
                latency = t - pending[0]
                self.latencies_s.append(latency)
                self.latency_by_path.setdefault(f"{pending[1]} {pending[2]}", []).append(latency)
            self.completed.append((t, message))
            done.append(message)
        return done

    def _on_request(self, event: Event) -> None:
        self.requests_sent += 1
        self.pending_requests[int(event.info["id"])] = (event.t, event.info.get("method", "?"),
                                                        event.info.get("path", "?"))

    def _on_request_timeout(self, event: Event) -> None:
        self.request_timeouts += 1
        self.pending_requests.pop(int(event.info["id"]), None)

    def _on_command_write_failed(self, event: Event) -> None:
        self.command_write_failures += 1

    def _on_rtcm_generated(self, event: Event) -> None:
        self.rtcm_generated_frames += int(event.info.get("frames", 1))
        self.rtcm_generated_bytes += int(event.info["bytes"])

    def _on_rtcm_write_failed(self, event: Event) -> None:
        self.rtcm_write_failures += 1
        self.rtcm_writes += int(event.info.get("chunks_written", 0)) + 1
        self.rtcm_write_modes.add(event.info.get("mode", "?"))

    def _on_rtcm_sent(self, event: Event) -> None:
        if self.rtcm_first_t is None:
            self.rtcm_first_t = event.t
        self.rtcm_last_t = event.t
        self.rtcm_sent_frames += 1
        self.rtcm_sent_bytes += int(event.info["bytes"])
        if event.info.get("valid") is False:
            self.rtcm_sent_invalid += 1
        else:
            self.rtcm_sent_valid_bytes += int(event.info["bytes"])
        self.rtcm_writes += int(event.info.get("writes", 1))
        self.rtcm_write_modes.add(event.info.get("mode", "?"))
        if "duration_s" in event.info:
            self.rtcm_frame_durations_s.append(float(event.info["duration_s"]))

    def _on_rtcm_discarded(self, event: Event) -> None:
        count = int(event.info.get("frames", 1))
        self.rtcm_discarded_frames += count
        reason = str(event.info.get("reason", "?"))
        self.rtcm_discarded_by_reason[reason] = self.rtcm_discarded_by_reason.get(reason, 0) + count

    def _on_rtcm_stream(self, event: Event) -> None:
        self.rtcm_target_rates.append(float(event.info.get("bytes_per_second", 0)))

    def _break_streams(self) -> None:
        for stats in self.streams.values():
            stats.break_continuity()
        self.last_solution = None       # la secuencia se cuenta por conexión
        self._health_previous = None    # los contadores de la salud, también

    def _on_connected(self, event: Event) -> None:
        self.connects += 1
        self.reassembler.reset()
        self._break_streams()
        if isinstance(event.info.get("gatt"), dict):
            self.gatt = event.info["gatt"]
            self._check_gatt()
        if "mtu" in event.info and event.info["mtu"] is not None:
            self.mtu_values.append(int(event.info["mtu"]))
        if "ready_s" in event.info:
            self.ready_times_s.append(float(event.info["ready_s"]))

    def _on_connect_failed(self, event: Event) -> None:
        self.connect_failures += 1

    def _on_disconnected(self, event: Event) -> None:
        if event.info.get("expected"):
            self.disconnects_expected += 1
        else:
            self.disconnects_unexpected += 1
        self.reassembler.reset()
        self._break_streams()
        # Una desconexión invalida lo pedido: no hay respuesta que esperar.
        self.requests_cancelled += len(self.pending_requests)
        self.pending_requests.clear()

    def _on_ble_status(self, event: Event) -> None:
        self.ble_status = dict(event.info.get("status") or {})
        self._check_gatt()

    def _check_gatt(self) -> None:
        """Tabla GATT en caché: el equipo dice v3 pero la pila ve la tabla vieja."""
        version = self.ble_status.get("protocol_version")
        if not self.gatt or not isinstance(version, int) or version < p.PROTOCOL_VERSION_WITH_HEARTBEAT:
            return
        warnings = []
        if not self.gatt.get("health"):
            warnings.append("falta la característica de salud a04c0006")
        if self.ble_status.get("rtcm_write_without_response") and \
                "write-without-response" not in self.gatt.get("correction", []):
            warnings.append("a04c0005 no anuncia escritura sin respuesta")
        for warning in warnings:
            text = (f"tabla GATT en caché: el equipo dice protocolo {version} pero {warning}. "
                    "No es un fallo del equipo: la pila de este lado recuerda la tabla de un firmware viejo")
            if text not in self.gatt_warnings:
                self.gatt_warnings.append(text)

    def _on_status(self, event: Event) -> None:
        self.statuses.append((event.t, event.info.get("label", ""), event.info.get("snapshot", {})))

    def _on_note(self, event: Event) -> None:
        self.notes.append(str(event.info.get("text", "")))

    # -- resultados -------------------------------------------------------
    def device_restarts(self) -> list[float]:
        """Instantes (de la foto siguiente) en que el `uptime_ms` del equipo volvió atrás."""
        restarts = []
        for (_, _, before), (t, _, after) in zip(self.statuses, self.statuses[1:]):
            a, b = before.get("uptime_ms"), after.get("uptime_ms")
            if isinstance(a, int) and isinstance(b, int) and b < a:
                restarts.append(t)
        return restarts

    def status_delta(self) -> dict[str, int | None]:
        """Diferencia de contadores entre la primera y la última foto del equipo.

        Si el equipo se reinició entre medias, sus contadores volvieron a cero: la
        diferencia se toma desde la primera foto posterior al último reinicio.
        """
        if len(self.statuses) < 2:
            return {}
        start = 0
        for index, ((_, _, before), (_, _, after)) in enumerate(zip(self.statuses, self.statuses[1:]), start=1):
            a, b = before.get("uptime_ms"), after.get("uptime_ms")
            if isinstance(a, int) and isinstance(b, int) and b < a:
                start = index
        if start == len(self.statuses) - 1:
            return {}
        first, last = self.statuses[start][2], self.statuses[-1][2]
        delta = {}
        for name in STATUS_COUNTERS:
            a, b = first.get(name), last.get(name)
            delta[name] = b - a if isinstance(a, int) and isinstance(b, int) else None
        return delta

    def receiver_silent(self) -> bool | None:
        """True si el ESP32 no ha recibido nada del UM980 (el cable RX de GPIO18)."""
        if not self.statuses:
            return None
        last = self.statuses[-1][2]
        gga, native = last.get("gnss.accepted_gga"), last.get("gnss.native_frames_valid")
        if gga is None and native is None:
            return None
        return not gga and not native

    def reconcile_rtcm(self) -> list[str]:
        """Cuadra las etapas del RTCM. Devuelve líneas en español con el veredicto."""
        lines = []
        if not self.rtcm_generated_frames and not self.rtcm_sent_frames:
            return lines
        lines.append(f"generadas {self.rtcm_generated_frames} tramas / {self.rtcm_generated_bytes} B → "
                     f"enviadas {self.rtcm_sent_frames} / {self.rtcm_sent_bytes} B "
                     f"(descartadas en la Mac sin enviar: {self.rtcm_discarded_frames}, "
                     f"escrituras fallidas: {self.rtcm_write_failures})")
        if self.rtcm_discarded_by_reason:
            lines.append("descartes de la Mac: " + "; ".join(f"{reason}: {count}"
                                                            for reason, count in self.rtcm_discarded_by_reason.items()))
        if self.device_restarts():
            lines.append("✘ el equipo se reinició durante la sesión: lo enviado por la Mac no se puede cuadrar "
                         "contra sus contadores, que volvieron a cero; ver «contadores del equipo» desde el reinicio")
            return lines
        delta = self.status_delta()
        valid = delta.get("ble.rtcm_valid_frames")
        if valid is None:
            lines.append("sin fotos del estado del equipo antes y después: no se puede cuadrar el lado del ESP32")
            return lines
        crc = delta.get("ble.rtcm_crc_errors") or 0
        dropped = delta.get("ble.rtcm_dropped_frames") or 0
        accepted = delta.get("corrections.accepted_frames")
        rejected = delta.get("corrections.rejected_frames")
        uart_sent = delta.get("gnss.correction_frames_sent")
        uart_dropped = delta.get("gnss.correction_frames_dropped")
        lines.append(f"ESP32 por BLE: válidas {valid}, CRC malos {crc}, no admitidas por el enrutador {dropped}")
        lines.append(f"enrutador: aceptadas {accepted}, rechazadas {rejected}; "
                     f"UART al UM980: escritas {uart_sent}, caducadas o sin sitio {uart_dropped}")
        if self.rtcm_sent_invalid:
            lines.append(f"de las enviadas, {self.rtcm_sent_invalid} iban corruptas a propósito: "
                         "se esperan como CRC malos o ruido, no como válidas")
        lost_in_link = self.rtcm_sent_frames - self.rtcm_sent_invalid - valid
        if lost_in_link == 0:
            lines.append("✔ enviadas = válidas en el ESP32: ninguna trama se perdió ni se partió por Bluetooth")
        elif lost_in_link > 0:
            lines.append(f"✘ {lost_in_link} tramas enviadas no llegaron válidas al ESP32 "
                         f"(CRC malos {crc}: trozos perdidos o reordenados)")
        else:
            lines.append(f"? el ESP32 contó {-lost_in_link} tramas válidas de más: otro cliente escribió RTCM a la vez")
        if dropped and valid and dropped >= valid:
            lines.append("✘ el enrutador no admitió ninguna: la fuente activa no es BLE "
                         "(PUT /api/corrections/source {\"source\":\"ble\"}) o el equipo trabaja como base")
        evicted = delta.get("gnss.correction_frames_evicted")
        expired = delta.get("gnss.correction_frames_expired")
        last = self.statuses[-1][2]
        if accepted and uart_sent is not None and evicted is not None and expired is not None:
            # Contrato v3: aceptadas = escritas + desalojadas + caducadas + en cola.
            in_queue = accepted - uart_sent - evicted - expired
            queue_bytes = last.get("gnss.correction_queue_bytes")
            lines.append(f"cola hacia el UM980: desalojadas {evicted}, caducadas {expired}, "
                         f"{queue_bytes} B dentro al final, máximo {last.get('gnss.correction_queue_high_water_bytes')} "
                         f"de {last.get('gnss.correction_queue_capacity_bytes')} B")
            if in_queue == 0 or (in_queue > 0 and queue_bytes):
                lines.append(f"✔ aceptadas = escritas al UM980 + desalojadas + caducadas + {in_queue} en cola")
            else:
                lines.append(f"✘ no cuadra el último salto: aceptadas {accepted}, escritas {uart_sent}, "
                             f"desalojadas {evicted}, caducadas {expired}, {queue_bytes} B en cola (diferencia {in_queue})")
            written = delta.get("gnss.correction_bytes_written")
            valid_bytes = self.rtcm_sent_valid_bytes
            if written is not None and not evicted and not expired and not queue_bytes:
                mark = "✔" if written == valid_bytes else "?"
                lines.append(f"{mark} bytes escritos a la UART {written} / bytes RTCM válidos enviados {valid_bytes}")
        elif accepted and uart_sent is not None and uart_dropped is not None:
            in_queue = accepted - uart_sent - uart_dropped
            if 0 <= in_queue <= DEVICE_UART_QUEUE_FRAMES:
                lines.append(f"✔ aceptadas = escritas al UM980 + descartadas + {in_queue} en cola")
            else:
                lines.append(f"✘ no cuadra el último salto: aceptadas {accepted}, escritas {uart_sent}, "
                             f"descartadas {uart_dropped} (diferencia {in_queue})")
        if self.health_with_rtcm_counters:
            lines.append(f"según la salud (v3): tiradas camino del UM980 +{self.health_rtcm_discarded}, "
                         f"rechazadas al llegar +{self.health_rtcm_rejected}, cola máx "
                         f"{'—' if self.health_queue_percent_max is None else str(self.health_queue_percent_max) + ' %'}")
        return lines

    def render(self, title: str = "Resumen") -> str:
        out = [f"== {title} =="]
        duration = (self.last_t - self.first_t) if self.first_t is not None and self.last_t is not None else 0.0
        out.append(f"duración: {duration:.1f} s")
        out.append(f"conexiones: {self.connects} (fallidas {self.connect_failures}); "
                   f"desconexiones pedidas {self.disconnects_expected}, inesperadas {self.disconnects_unexpected}")
        if self.mtu_values:
            out.append(f"MTU visto por la Mac: {sorted(set(self.mtu_values))}")
        if self.ready_times_s:
            out.append(f"tiempo hasta listo: p50 {percentile(self.ready_times_s, 50):.2f} s, "
                       f"máx {max(self.ready_times_s):.2f} s")
        out.append("notificaciones:")
        for name in ("solution", "health", "response"):
            stats = self.streams.get(name)
            if stats is None or stats.count == 0:
                out.append(f"  {name}: 0")
                continue
            if name == "response":
                # Las respuestas van a demanda: su intervalo no dice nada del enlace.
                out.append(f"  {name}: {stats.count} tramas ({stats.total_bytes} B)")
                continue
            rate = stats.rate_hz()
            out.append(f"  {name}: {stats.count} ({stats.total_bytes} B"
                       + (f", {rate:.2f} Hz" if rate else "")
                       + f"), máximo entre dos {stats.max_interval_s * 1000:.0f} ms"
                       + (f" (a los {stats.max_interval_at_s:.1f} s)" if stats.max_interval_at_s is not None else "")
                       + (f", p95 {percentile(stats.intervals, 95) * 1000:.0f} ms" if stats.intervals else ""))
        solution = self.streams.get("solution")
        health = self.streams.get("health")
        if solution is not None and solution.count:
            out.append(f"solución: {self.solution_missing} paquetes perdidos por secuencia, "
                       f"{self.solution_anomalies} saltos atrás o repetidos, {self.solution_decode_errors} ilegibles; "
                       f"calidades {self.qualities}")
        if self.quality_transitions:
            shown = ", ".join(f"{t:.1f} s {a}→{b}" for t, a, b in self.quality_transitions[:MAX_TRANSITIONS_SHOWN])
            more = len(self.quality_transitions) - MAX_TRANSITIONS_SHOWN
            out.append(f"cambios de calidad: {len(self.quality_transitions)} ({shown}"
                       + (f", y {more} más" if more > 0 else "") + ")")
        silent = self.receiver_silent()
        if silent:
            out.append("⚠ 0 bytes de telemetría del receptor: el ESP32 no ha aceptado ni una trama del UM980 "
                       "(GGA 0, binario nativo 0). **No es un fallo de Bluetooth**: revisar el cable "
                       "TTL_TXD2 → GPIO18. Sin solución el firmware tampoco manda salud (ble_transport.cpp:233).")
        elif (solution is None or not solution.count) and (health is None or not health.count) and duration > 3:
            out.append("⚠ ni solución ni salud: o el receptor no emite (ver /api/status → subsystems.gnss) "
                       "o no hay suscripción; la salud solo sale detrás de una solución nueva (ble_transport.cpp:255)")
        if health is not None and health.count and health.max_interval_s * 1000 > p.HEALTH_SILENCE_DEGRADED_MS \
                and (self.ble_status.get("protocol_version") or 0) >= p.PROTOCOL_VERSION_WITH_HEARTBEAT:
            out.append(f"✘ latido: {health.max_interval_s:.1f} s sin salud con el enlace arriba "
                       f"(el contrato v3 da la sesión por medio muerta a los {p.HEALTH_SILENCE_DEGRADED_MS / 1000:.0f} s)")
        out += [f"⚠ {warning}" for warning in self.gatt_warnings]
        if self.ble_status:
            out.append("estado BLE al conectar: " + ", ".join(f"{k} {v}" for k, v in self.ble_status.items()))
        if self.last_health is not None:
            h = self.last_health
            out.append(f"última salud: fuente {h.correction_source_name}, edad de corrección "
                       f"{'—' if h.correction_age_seconds is None else str(h.correction_age_seconds) + ' s'}, "
                       f"rastreados {'—' if h.satellites_tracked is None else h.satellites_tracked}, "
                       f"banderas 0x{h.flags:02x}"
                       + (f", cola RTCM {'—' if h.rtcm_queue_percent is None else str(h.rtcm_queue_percent) + ' %'}"
                          if h.has_rtcm_counters else ""))
        if self.requests_sent:
            p50, p95 = (percentile(self.latencies_s, rank) for rank in PERCENTILES)
            fmt = lambda v: "—" if v is None else f"{v * 1000:.0f} ms"  # noqa: E731
            out.append(f"órdenes: {self.requests_sent} enviadas, {len(self.latencies_s)} respondidas, "
                       f"{self.request_timeouts} vencidas, {self.requests_cancelled} cortadas por desconexión, "
                       f"{self.command_write_failures} escrituras fallidas, "
                       f"{self.uncorrelated_responses} respuestas sin petición, {self.invalid_json_responses} JSON ilegibles")
            out.append(f"latencia de órdenes: p50 {fmt(p50)}, p95 {fmt(p95)}, "
                       f"máx {fmt(max(self.latencies_s) if self.latencies_s else None)}; estados {self.responses_by_status}")
            for path, values in sorted(self.latency_by_path.items()):
                out.append(f"  {path}: n={len(values)} p50 {fmt(percentile(values, 50))} "
                           f"p95 {fmt(percentile(values, 95))} máx {fmt(max(values))}")
        anomalies = {k: v for k, v in self.reassembler.counts.items() if k not in ("pending", "completed") and v}
        if anomalies or self.reassembler.counts["completed"]:
            out.append(f"rearmado de respuestas: {self.reassembler.counts['completed']} completas; "
                       f"anomalías {anomalies or 'ninguna'}")
        if self.rtcm_sent_frames or self.rtcm_generated_frames:
            span = (self.rtcm_last_t - self.rtcm_first_t) if self.rtcm_first_t is not None else 0.0
            rate = self.rtcm_sent_bytes / span if span > 0 else None
            modes = ", ".join(sorted(self.rtcm_write_modes)) or "—"
            out.append(f"RTCM: modo de escritura {modes}; caudal {'—' if rate is None else f'{rate:.0f} B/s'}; "
                       f"{self.rtcm_writes} escrituras"
                       + (f"; tiempo por trama p95 {percentile(self.rtcm_frame_durations_s, 95) * 1000:.1f} ms, "
                          f"máx {max(self.rtcm_frame_durations_s) * 1000:.1f} ms"
                          if self.rtcm_frame_durations_s else ""))
            target = max(self.rtcm_target_rates) if self.rtcm_target_rates else None
            if target and rate is not None and rate < RATE_SHORTFALL_RATIO * target \
                    and not self.disconnects_expected + self.disconnects_unexpected > 1:
                out.append(f"  ⚠ caudal por debajo del pedido ({rate:.0f} de {target:.0f} B/s): el carril no da más "
                           f"en modo {modes}; lo que no cupo se tiró por viejo en la Mac, no se acumuló")
            out += ["  " + line for line in self.reconcile_rtcm()]
        restarts = self.device_restarts()
        if restarts:
            out.append(f"⚠ el equipo se reinició {len(restarts)} vez/veces (uptime_ms volvió atrás; foto a los "
                       + ", ".join(f"{t:.0f} s" for t in restarts) + ")")
        delta = self.status_delta()
        if delta:
            changed = {k: v for k, v in delta.items() if v}
            out.append(f"contadores del equipo que cambiaron: {changed or 'ninguno'}")
        if self.statuses:
            last = self.statuses[-1][2]
            out.append(f"equipo: firmware {last.get('firmware_version')}, BLE {last.get('ble.state')}, "
                       f"MTU {last.get('ble.att_mtu')}, tramas forzadas {last.get('ble.response_frames_forced')}, "
                       f"fuente {last.get('corrections.active_source')}, GNSS {last.get('gnss.state')}, "
                       f"heap libre {last.get('free_heap_bytes')} (mín {last.get('min_free_heap_bytes')}), "
                       f"alertas {last.get('alerts')}")
            if last.get("ble.conn_interval_ms") is not None or last.get("ble.max_loop_gap_ms") is not None:
                out.append(f"equipo (v3): intervalo de conexión {last.get('ble.conn_interval_ms')} ms, "
                           f"telemetría saltada por falta de hueco {last.get('ble.telemetry_skipped')}, "
                           f"bucle BLE máx {last.get('ble.max_loop_gap_ms')} ms, "
                           f"despacho de orden máx {last.get('ble.max_request_dispatch_ms')} ms")
        out += [f"nota: {note}" for note in self.notes]
        return "\n".join(out)


def analyze_events(events) -> Analyzer:
    analyzer = Analyzer()
    for event in events:
        analyzer.consume(event)
    return analyzer
