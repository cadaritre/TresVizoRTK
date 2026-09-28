"""Grabación de sesiones: cada evento con su marca de tiempo monotónica.

Una sesión es un archivo JSON Lines. La primera línea es una cabecera; cada una
de las siguientes, un evento. El mismo evento va a la vez a un CSV plano para
abrirlo en una hoja de cálculo.

La marca `t` son **segundos del reloj monotónico de la Mac desde el inicio de la
sesión**: el instante de llegada a este lado, no el de medición en el receptor.
Nunca se mezcla con la hora UTC del paquete de solución ni con el reloj del ESP32.

**Nunca se graban credenciales.** El banco solo consulta rutas de estado y
`redact()` borra cualquier clave con pinta de secreto antes de escribir JSON.
"""
from __future__ import annotations

import csv
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator

FORMAT_NAME = "meridian-ble-bench"
FORMAT_VERSION = 1
CSV_COLUMNS = ("t_monotonic_s", "kind", "characteristic", "bytes", "detail")

# Claves que no se escriben nunca, en ningún nivel del JSON.
SECRET_KEY_FRAGMENTS = ("password", "passwd", "pass", "secret", "token", "key", "psk", "credential")


def redact(value: object) -> object:
    """Copia del JSON con las claves sensibles sustituidas por «[oculto]»."""
    if isinstance(value, dict):
        clean = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(fragment in lowered for fragment in SECRET_KEY_FRAGMENTS) and not lowered.endswith("_persisted"):
                clean[key] = "[oculto]"
            else:
                clean[key] = redact(item)
        return clean
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


@dataclass
class Event:
    """Un evento del banco. `t` en segundos monotónicos desde el inicio."""
    t: float
    kind: str
    characteristic: str | None = None
    data: bytes | None = None
    info: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        row: dict[str, object] = {"t": round(self.t, 6), "kind": self.kind}
        if self.characteristic:
            row["char"] = self.characteristic
        if self.data is not None:
            row["hex"] = self.data.hex()
        if self.info:
            row["info"] = redact(self.info)
        return row

    @classmethod
    def from_json(cls, row: dict) -> "Event":
        return cls(t=float(row["t"]), kind=row["kind"], characteristic=row.get("char"),
                   data=bytes.fromhex(row["hex"]) if "hex" in row else None, info=row.get("info", {}))

    def csv_row(self) -> list[object]:
        detail = json.dumps(redact(self.info), ensure_ascii=False, separators=(",", ":")) if self.info else ""
        return [f"{self.t:.6f}", self.kind, self.characteristic or "",
                "" if self.data is None else len(self.data), detail]


class Recorder:
    """Escribe eventos a JSON Lines y a CSV a la vez. Sin archivos, solo reparte."""

    def __init__(self, jsonl_path: Path | None = None, csv_path: Path | None = None,
                 clock: Callable[[], float] = time.monotonic, metadata: dict | None = None):
        self._clock = clock
        self._start = clock()
        self._listeners: list[Callable[[Event], None]] = []
        self._jsonl = open(jsonl_path, "w", encoding="utf-8") if jsonl_path else None
        self._csv_file = open(csv_path, "w", encoding="utf-8", newline="") if csv_path else None
        self._csv = csv.writer(self._csv_file) if self._csv_file else None
        if self._jsonl:
            header = {"format": FORMAT_NAME, "version": FORMAT_VERSION,
                      "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      "clock": "monotónico de la Mac, segundos desde el inicio",
                      "metadata": redact(metadata or {})}
            self._jsonl.write(json.dumps(header, ensure_ascii=False) + "\n")
        if self._csv:
            self._csv.writerow(CSV_COLUMNS)

    def now(self) -> float:
        return self._clock() - self._start

    def subscribe(self, listener: Callable[[Event], None]) -> None:
        self._listeners.append(listener)

    def record(self, kind: str, characteristic: str | None = None, data: bytes | None = None,
               t: float | None = None, **info) -> Event:
        # Redondeado como se escribe, para que la reproducción vea los mismos números.
        event = Event(round(self.now() if t is None else t, 6), kind, characteristic,
                      None if data is None else bytes(data), info)
        self.emit(event)
        return event

    def emit(self, event: Event) -> None:
        if self._jsonl:
            self._jsonl.write(json.dumps(event.to_json(), ensure_ascii=False) + "\n")
        if self._csv:
            self._csv.writerow(event.csv_row())
        for listener in self._listeners:
            listener(event)

    def flush(self) -> None:
        for handle in (self._jsonl, self._csv_file):
            if handle:
                handle.flush()

    def close(self) -> None:
        for handle in (self._jsonl, self._csv_file):
            if handle:
                handle.close()
        self._jsonl = self._csv_file = None
        self._csv = None


class SessionFormatError(ValueError):
    pass


def read_session(path: Path) -> tuple[dict, Iterator[Event]]:
    """Cabecera y eventos de una sesión grabada, en orden."""
    handle = open(path, encoding="utf-8")
    first = handle.readline()
    try:
        header = json.loads(first)
    except ValueError as error:
        handle.close()
        raise SessionFormatError(f"{path}: la primera línea no es JSON") from error
    if header.get("format") != FORMAT_NAME:
        handle.close()
        raise SessionFormatError(f"{path}: no es una sesión del banco ({header.get('format')!r})")
    if header.get("version") != FORMAT_VERSION:
        handle.close()
        raise SessionFormatError(f"{path}: versión {header.get('version')} no soportada")

    def events() -> Iterator[Event]:
        with handle:
            for number, line in enumerate(handle, start=2):
                if not line.strip():
                    continue
                try:
                    yield Event.from_json(json.loads(line))
                except (ValueError, KeyError) as error:
                    raise SessionFormatError(f"{path}:{number}: evento ilegible ({error})") from error
    return header, events()


# ---------------------------------------------------------------------------
# Anonimizar una sesión antes de versionarla (tests/fixtures/ solo admite datos
# anonimizados, docs/development.md). Las respuestas de /api/status traen el
# nombre de las redes Wi-Fi y direcciones IP. Se sustituyen **por el mismo número
# de bytes**, así que el troceo, los desplazamientos y las anomalías del rearmado
# quedan idénticos y la reproducción da el mismo resumen salvo esos textos.
ANONYMIZED_KEYS = ("ssid", "device_name", "ap_ip", "station_ip", "ip", "mac", "bssid", "hostname")
IPV4_PATTERN = re.compile(rb"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
# La comilla de apertura de la clave es opcional: en un mensaje con hueco la
# clave puede llegar cortada («p_ssid": "…»).
_STRING_VALUE = re.compile(rb'"?([A-Za-z0-9_]+)"\s*:\s*"((?:[^"\\]|\\.)*)"')
MIN_SECRET_BYTES = 3  # valores más cortos no se buscan sueltos: taparían medio JSON
ANONYMIZED_LINK = "Meridian V (anonimizado)"
RESPONSE_HEADER_BYTES = 5  # id uint16 + offset uint16 + banderas (protocol.RESPONSE_HEADER_BYTES)


def _sensitive_values(buffer: bytes) -> set[bytes]:
    values = set()
    for match in _STRING_VALUE.finditer(buffer):
        key = match.group(1).decode("ascii", "replace").lower()
        if any(fragment in key for fragment in ANONYMIZED_KEYS) and len(match.group(2)) >= MIN_SECRET_BYTES:
            values.add(match.group(2))
    return values


def _mask_sensitive(buffer: bytearray, secrets: set[bytes]) -> None:
    for match in _STRING_VALUE.finditer(bytes(buffer)):
        key = match.group(1).decode("ascii", "replace").lower()
        if any(fragment in key for fragment in ANONYMIZED_KEYS):
            start, end = match.span(2)
            buffer[start:end] = b"x" * (end - start)
    # Lo que se vio como red o IP en cualquier mensaje se tapa en todos, aunque
    # aquí haya llegado sin su clave (mensaje con hueco).
    for secret in secrets:
        start = buffer.find(secret)
        while start >= 0:
            buffer[start:start + len(secret)] = b"x" * len(secret)
            start = buffer.find(secret, start + len(secret))
    for match in IPV4_PATTERN.finditer(bytes(buffer)):
        start, end = match.span()
        buffer[start:end] = re.sub(rb"\d", b"0", buffer[start:end])


def anonymize_events(events: list[Event]) -> list[Event]:
    """Copia de los eventos con redes e IP tapadas en las respuestas, byte a byte."""
    groups: dict[tuple[int, int], list[int]] = {}
    current: dict[int, int] = {}
    for index, event in enumerate(events):
        if event.kind != "notify" or event.characteristic != "response" or not event.data \
                or len(event.data) < RESPONSE_HEADER_BYTES:
            continue
        message_id = int.from_bytes(event.data[0:2], "little")
        if event.data[4] & 0x01 or message_id not in current:
            current[message_id] = index
        groups.setdefault((message_id, current[message_id]), []).append(index)
    result = list(events)
    buffers = {}
    for key, indices in groups.items():
        size = max(int.from_bytes(events[i].data[2:4], "little") + len(events[i].data) - RESPONSE_HEADER_BYTES
                   for i in indices)
        buffer = bytearray(size)
        for i in indices:
            offset = int.from_bytes(events[i].data[2:4], "little")
            payload = events[i].data[RESPONSE_HEADER_BYTES:]
            buffer[offset:offset + len(payload)] = payload
        buffers[key] = buffer
    secrets: set[bytes] = set()
    for buffer in buffers.values():
        secrets |= _sensitive_values(bytes(buffer))
    for key, indices in groups.items():
        buffer = buffers[key]
        _mask_sensitive(buffer, secrets)
        for i in indices:
            original = events[i]
            offset = int.from_bytes(original.data[2:4], "little")
            length = len(original.data) - RESPONSE_HEADER_BYTES
            data = original.data[:RESPONSE_HEADER_BYTES] + bytes(buffer[offset:offset + length])
            result[i] = Event(original.t, original.kind, original.characteristic, data, original.info)
    # El nombre y la dirección del equipo (en macOS, el UUID de CoreBluetooth)
    # van en la descripción del enlace y en las notas.
    links = {str(e.info["link"]) for e in result if e.kind == "connected" and e.info.get("link")}
    for index, event in enumerate(result):
        if not event.info:
            continue
        info = dict(event.info)
        if "link" in info:
            info["link"] = ANONYMIZED_LINK
        if isinstance(info.get("text"), str):
            for link in links:
                info["text"] = info["text"].replace(link, ANONYMIZED_LINK)
        if info != event.info:
            result[index] = Event(event.t, event.kind, event.characteristic, event.data, info)
    return result


def anonymize_session(source: Path, target: Path) -> int:
    """Escribe `target` anonimizado. Devuelve cuántas notificaciones cambiaron."""
    header, events = read_session(source)
    events = list(events)
    clean = anonymize_events(events)
    header = dict(header)
    header["anonymized"] = True
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(header, ensure_ascii=False) + "\n")
        for event in clean:
            handle.write(json.dumps(event.to_json(), ensure_ascii=False) + "\n")
    return sum(1 for a, b in zip(events, clean) if a.data != b.data)
