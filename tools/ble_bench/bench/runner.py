"""El banco: conexión, suscripciones, órdenes con correlación y flujo de RTCM.

Todo lo que pasa se registra como evento (`session.Recorder`) y el `Analyzer`
lo consume en el mismo instante: el resumen en vivo y el de una reproducción
salen del mismo código.
"""
from __future__ import annotations

import asyncio
from typing import Callable, Iterator

from . import protocol as p
from .analysis import BLE_STATUS_KEYS, Analyzer, extract_status
from .link import Link, LinkError
from .rtcm import Pacer, frame_is_valid, message_number
from .session import Event, Recorder

# Lo único que el banco pide al equipo. Todo es de lectura salvo elegir la
# fuente de correcciones, que el operador activa a propósito (--select-ble-source).
# Nunca rutas que devuelvan credenciales, ni /api/restart, ni actualizaciones.
READ_ONLY_REQUESTS = {
    ("GET", "/api/status"),
    ("GET", "/api/ble"),
    ("GET", "/api/corrections/source"),
    ("GET", "/api/gnss/sky"),
    ("GET", "/api/gnss/control"),
}
MUTATING_REQUESTS = {("PUT", "/api/corrections/source")}
DEFAULT_REQUEST_TIMEOUT_S = 5.0   # lo mismo que tarda el firmware en caducar una orden
STREAM_TICK_S = 0.005             # cada cuánto mira el ritmo el emisor de RTCM
REQUEST_ID_MODULO = 1 << 31       # el firmware exige un uint32 en "id"


class RequestFailed(RuntimeError):
    pass


class Bench:
    def __init__(self, link_factory: Callable[[], Link], recorder: Recorder,
                 request_timeout_s: float = DEFAULT_REQUEST_TIMEOUT_S, allow_mutations: bool = False,
                 command_priority: bool = True):
        self.link_factory = link_factory
        self.recorder = recorder
        self.analyzer = Analyzer()
        self.request_timeout_s = request_timeout_s
        self.allow_mutations = allow_mutations
        self.link: Link | None = None
        self.rtcm_with_response = True
        self._waiters: dict[int, asyncio.Future] = {}
        self._next_id = 1
        self._command_lock = asyncio.Lock()
        self._first_response_frame = asyncio.Event()
        # Contrato v3, regla 2: si hay una orden escribiéndose, el siguiente hueco
        # del carril ATT es suyo y el RTCM espera. Se puede apagar para medir
        # la diferencia (--no-command-priority).
        self.command_priority = command_priority
        self._lane_free = asyncio.Event()
        self._lane_free.set()
        recorder.subscribe(self._on_event)

    # -- eventos ------------------------------------------------------------
    def record(self, kind: str, **info) -> Event:
        return self.recorder.record(kind, **info)

    def note(self, text: str) -> None:
        self.recorder.record("note", text=text)
        print(text, flush=True)

    def _on_event(self, event: Event) -> None:
        for message in self.analyzer.consume(event):
            waiter = self._waiters.get(message.get("id"))
            if waiter is not None and not waiter.done():
                waiter.set_result(message)
        if event.kind == "notify" and event.characteristic == "response":
            self._first_response_frame.set()

    def _notify_handler(self, name: str):
        def handler(data: bytes) -> None:
            self.recorder.record("notify", name, data)
        return handler

    # -- conexión -----------------------------------------------------------
    @property
    def connected(self) -> bool:
        return self.link is not None and self.link.is_connected

    async def connect(self) -> None:
        started = self.recorder.now()
        link = self.link_factory()
        link.on_unexpected_disconnect = self._lost
        try:
            await link.connect()
            gatt = {name: sorted(link.properties(uuid)) for uuid, name in p.CHARACTERISTIC_NAMES.items()}
            if not gatt["command"] or not gatt["response"]:
                raise LinkError("faltan las características de órdenes o respuestas: no es un Meridian V utilizable")
            # Respuestas primero: sin esa suscripción una orden no tiene vuelta.
            # La salud puede faltar si la pila recuerda una tabla GATT vieja
            # (hallazgo del líder con la Mac): se sigue sin ella y se dice.
            for uuid in (p.RESPONSE_UUID, p.SOLUTION_UUID, p.HEALTH_UUID):
                name = p.CHARACTERISTIC_NAMES[uuid]
                if not gatt[name]:
                    self.record("note", text=f"la tabla GATT descubierta no trae «{name}» ({uuid}); sin suscripción")
                    continue
                await link.start_notify(uuid, self._notify_handler(name))
        except Exception as error:
            self.record("connect_failed", error=f"{type(error).__name__}: {error}")
            try:
                await link.disconnect()
            except Exception:
                pass
            raise
        self.link = link
        properties = link.properties(p.CORRECTION_UUID)
        # Sin respuesta solo si el firmware lo anuncia (hallazgo del líder,
        # 22:12 del canal); si no, con respuesta, como hasta ahora.
        self.rtcm_with_response = "write-without-response" not in properties
        self.record("connected", mtu=link.negotiated_mtu, ready_s=round(self.recorder.now() - started, 4),
                    link=link.description, gatt=gatt, rtcm_write_mode=self.rtcm_mode)
        # Como las apps (contrato v3, regla 3): tras conectar, el estado BLE.
        try:
            answer = await self.request("GET", "/api/ble")
            body = answer.get("body") if isinstance(answer.get("body"), dict) else {}
            self.record("ble_status", status={key: body.get(key) for key in BLE_STATUS_KEYS if key in body})
        except Exception as error:
            self.note(f"tras conectar, GET /api/ble no contestó: {type(error).__name__}: {error}")

    @property
    def rtcm_mode(self) -> str:
        return "con respuesta" if self.rtcm_with_response else "sin respuesta"

    def _lost(self) -> None:
        self.record("disconnected", expected=False)
        self._fail_waiters("enlace perdido")

    def _fail_waiters(self, reason: str) -> None:
        for waiter in self._waiters.values():
            if not waiter.done():
                waiter.set_exception(RequestFailed(reason))

    async def disconnect(self, reason: str = "pedida") -> None:
        link, self.link = self.link, None
        if link is None:
            return
        try:
            await link.disconnect()
        finally:
            self.record("disconnected", expected=True, reason=reason)
            self._fail_waiters("desconexión pedida")

    async def reconnect_with_backoff(self, delays_s=(1, 2, 4, 8, 16, 30), attempts: int = 8) -> bool:
        """Escalera acotada, como la de las apps. Devuelve si volvió."""
        for attempt in range(attempts):
            try:
                await self.connect()
                return True
            except Exception as error:
                delay = delays_s[min(attempt, len(delays_s) - 1)]
                self.note(f"reconexión {attempt + 1} fallida ({error}); siguiente en {delay} s")
                await asyncio.sleep(delay)
        return False

    # -- órdenes ------------------------------------------------------------
    def _check_allowed(self, method: str, path: str) -> None:
        if (method, path) in READ_ONLY_REQUESTS:
            return
        if (method, path) in MUTATING_REQUESTS and self.allow_mutations:
            return
        raise PermissionError(f"el banco no manda {method} {path}")

    def _allocate_id(self) -> int:
        request_id = self._next_id
        self._next_id = self._next_id % (REQUEST_ID_MODULO - 1) + 1
        return request_id

    async def send_request(self, method: str, path: str, body: object | None = None) -> tuple[int, asyncio.Future]:
        """Escribe la orden y devuelve (id, futuro de la respuesta) sin esperarla."""
        self._check_allowed(method, path)
        if not self.connected:
            raise LinkError("sin conexión")
        request_id = self._allocate_id()
        line = p.encode_request(request_id, method, path, body)
        waiter = asyncio.get_running_loop().create_future()
        self._waiters[request_id] = waiter
        self.record("request", id=request_id, method=method, path=path, bytes=len(line))
        if self.command_priority:
            self._lane_free.clear()
        try:
            # Las órdenes siempre con respuesta ATT (a04c0002 solo anuncia WRITE).
            for chunk in p.chunk_for_write(line, self.link.negotiated_mtu or p.MINIMUM_ATT_MTU):
                await self.link.write(p.COMMAND_UUID, chunk, with_response=True)
        except Exception as error:
            self._waiters.pop(request_id, None)
            self.record("command_write_failed", id=request_id, path=path, error=f"{type(error).__name__}: {error}")
            raise
        finally:
            self._lane_free.set()
        return request_id, waiter

    async def request(self, method: str, path: str, body: object | None = None,
                      timeout_s: float | None = None) -> dict:
        """Una orden y su respuesta, de una en una, como la app. Nunca reintenta."""
        async with self._command_lock:
            request_id, waiter = await self.send_request(method, path, body)
            try:
                return await asyncio.wait_for(waiter, timeout_s or self.request_timeout_s)
            except asyncio.TimeoutError:
                self.record("request_timeout", id=request_id, path=path)
                raise
            finally:
                self._waiters.pop(request_id, None)

    async def snapshot(self, label: str) -> dict | None:
        """Foto de los contadores del equipo (GET /api/status). None si no contestó."""
        try:
            answer = await self.request("GET", "/api/status")
        except Exception as error:
            self.note(f"sin foto del estado «{label}»: {type(error).__name__}: {error}")
            return None
        if answer.get("status") != 200 or not isinstance(answer.get("body"), dict):
            self.note(f"/api/status respondió {answer.get('status')} en «{label}»")
            return None
        snapshot = extract_status(answer["body"])
        self.record("status", label=label, snapshot=snapshot)
        return snapshot

    async def ensure_ble_source(self, select: bool) -> None:
        """Comprueba que el ESP32 admitirá el RTCM por BLE y, si se pidió, lo elige."""
        try:
            answer = await self.request("GET", "/api/corrections/source")
        except Exception as error:
            self.note(f"no se pudo leer la fuente de correcciones: {error}")
            return
        active = (answer.get("body") or {}).get("active_source")
        if active == "ble":
            return
        if not select:
            self.note(f"⚠ la fuente activa es «{active}»: el ESP32 rechazará todas las tramas "
                      "(se contarán en rtcm_dropped_frames). Repetir con --select-ble-source para elegir BLE.")
            return
        answer = await self.request("PUT", "/api/corrections/source", {"source": "ble"})
        self.note(f"fuente de correcciones → ble: respuesta {answer.get('status')} "
                  f"{(answer.get('body') or {}).get('error', '')}".rstrip())

    # -- RTCM ---------------------------------------------------------------
    async def write_rtcm_frame(self, frame: bytes) -> bool:
        """Una trama entera, en trozos de MTU − 3. True si todos los trozos salieron."""
        loop = asyncio.get_running_loop()
        started = loop.time()
        chunks = p.chunk_for_write(frame, self.link.negotiated_mtu or p.MINIMUM_ATT_MTU)
        written = 0
        try:
            for chunk in chunks:
                await self._lane_free.wait()
                await self.link.write(p.CORRECTION_UUID, chunk, with_response=self.rtcm_with_response)
                written += 1
        except Exception as error:
            self.record("rtcm_write_failed", bytes=len(frame), chunks_written=written, chunks=len(chunks),
                        mode=self.rtcm_mode, error=f"{type(error).__name__}: {error}")
            return False
        # Las tramas corruptas a propósito (escenario «malformados») se marcan para
        # que el cuadre no las espere como válidas en el ESP32.
        self.record("rtcm_sent", bytes=len(frame), number=message_number(frame), writes=len(chunks),
                    mode=self.rtcm_mode, duration_s=round(loop.time() - started, 6),
                    valid=frame_is_valid(frame))
        return True

    async def stream_rtcm(self, frames: Iterator[bytes], bytes_per_second: float, duration_s: float,
                          burst_seconds: float = 0.0, stop: asyncio.Event | None = None) -> None:
        """Manda tramas enteras al ritmo pedido hasta agotar el tiempo o perder el enlace.

        No se reenvía nada: una trama que no salió se cuenta como descartada y
        la siguiente es nueva (política de datos viejos del encargo).
        """
        loop = asyncio.get_running_loop()
        pacer = Pacer(bytes_per_second, burst_seconds)
        end = loop.time() + duration_s
        pending: bytes | None = None
        while loop.time() < end and self.connected and not (stop and stop.is_set()):
            due = pacer.due_bytes(loop.time())
            while self.connected:
                if pending is None:
                    try:
                        pending = next(frames)
                    except StopIteration:
                        return
                    self.record("rtcm_generated", bytes=len(pending), number=message_number(pending))
                if len(pending) > due:
                    break
                ok = await self.write_rtcm_frame(pending)
                pacer.spend(len(pending))
                due -= len(pending)
                pending = None
                if not ok:
                    break
            await asyncio.sleep(STREAM_TICK_S)
        if pending is not None:
            self.record("rtcm_discarded", frames=1, bytes=len(pending), reason="fin del flujo o enlace perdido")

    async def periodic_requests(self, path: str, period_s: float, stop: asyncio.Event) -> None:
        """Una orden de lectura cada `period_s` hasta que se pida parar. Mide latencias."""
        while not stop.is_set():
            if self.connected:
                try:
                    await self.request("GET", path)
                except Exception:
                    pass  # vencida o enlace perdido: ya quedó registrado
            try:
                await asyncio.wait_for(stop.wait(), period_s)
            except asyncio.TimeoutError:
                pass

    def arm_response_frame_watch(self) -> None:
        """Antes de mandar la orden: luego `wait_first_response_frame` no se pierde la trama."""
        self._first_response_frame.clear()

    async def wait_first_response_frame(self, timeout_s: float) -> bool:
        try:
            await asyncio.wait_for(self._first_response_frame.wait(), timeout_s)
            return True
        except asyncio.TimeoutError:
            return False
