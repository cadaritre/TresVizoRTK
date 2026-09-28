"""Escenarios de la matriz de aceptación que se pueden correr desde la Mac.

Cada escenario recibe un `Bench` ya creado y unas `ScenarioOptions`, deja todo
registrado como eventos y no decide «pasa/falla» por su cuenta: eso lo hace el
operador con el resumen y los criterios de `docs/connectivity/ACCEPTANCE_PROCEDURES.md`.
"""
from __future__ import annotations

import asyncio
import itertools
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable, Iterator

from . import rtcm
from .protocol import COMMAND_UUID
from .runner import Bench

# Pausa tras el flujo para que el ESP32 vacíe su cola a la UART (4 tramas de
# ~300 B a 11.5 kB/s son 0.1 s; se deja margen para la caducidad de 2 s).
DRAIN_AFTER_STREAM_S = 3.0
PAUSE_BEFORE_RECONNECT_S = 1.0
LONG_SESSION_SLICE_S = 60.0
LONG_SESSION_SNAPSHOT_PERIOD_S = 300.0
# Escenario «malformados»: una trama de cada 7 con CRC roto y una de cada 11
# sustituida por ruido. Deterministas, para que el recuento se pueda repetir.
MALFORMED_CRC_EVERY = 7
MALFORMED_NOISE_EVERY = 11


@dataclass
class ScenarioOptions:
    duration_s: float = 60.0
    rate_bytes_per_second: float = 1000.0
    command_period_s: float = 2.0
    command_path: str = "/api/ble"
    burst_seconds: float = 0.0
    cycles: int = 20
    select_ble_source: bool = False
    msm_kind: int = 7
    inert: bool = False
    rtcm_file: Path | None = None
    seed: int = 1


def rtcm_source(options: ScenarioOptions, note: Callable[[str], None]) -> Iterator[bytes]:
    """Tramas de una captura real si se dio una; si no, del generador."""
    if options.rtcm_file is not None:
        frames, parser = rtcm.read_frames_from_file(options.rtcm_file)
        if not frames:
            raise ValueError(f"{options.rtcm_file}: ni una trama RTCM3 válida")
        note(f"RTCM de {options.rtcm_file}: {len(frames)} tramas válidas, {parser.rejected} con CRC malo; se repite en bucle")
        return itertools.cycle(frames)
    profile = rtcm.EpochProfile(msm_kind=options.msm_kind, inert_message_number=4095 if options.inert else None)
    generator = rtcm.RtcmGenerator(profile, seed=options.seed)
    note(f"RTCM generado: MSM{options.msm_kind} de 4 constelaciones + 1005/1033/1230, "
         f"~{generator.epoch_bytes()} B por época; contenido sintético, el UM980 no fijará con él")
    return (item.frame for item in generator.frames())


async def _open(bench: Bench, options: ScenarioOptions, rtcm_needed: bool) -> None:
    await bench.connect()
    bench.note(f"conectado: {bench.link.description}; MTU {bench.link.negotiated_mtu}; "
               f"RTCM se escribirá {bench.rtcm_mode}")
    await bench.snapshot("inicio")
    if rtcm_needed:
        await bench.ensure_ble_source(options.select_ble_source)


async def _close(bench: Bench) -> None:
    if bench.connected:
        await bench.snapshot("fin")
        await bench.disconnect()


async def telemetry_only(bench: Bench, options: ScenarioOptions) -> None:
    await _open(bench, options, rtcm_needed=False)
    await asyncio.sleep(options.duration_s)
    await _close(bench)


async def rtcm_stream(bench: Bench, options: ScenarioOptions) -> None:
    await _open(bench, options, rtcm_needed=True)
    await bench.stream_rtcm(rtcm_source(options, bench.note), options.rate_bytes_per_second,
                            options.duration_s, options.burst_seconds)
    await asyncio.sleep(DRAIN_AFTER_STREAM_S)
    await _close(bench)


async def rtcm_with_commands(bench: Bench, options: ScenarioOptions) -> None:
    await _open(bench, options, rtcm_needed=True)
    stop = asyncio.Event()
    commands = asyncio.create_task(bench.periodic_requests(options.command_path, options.command_period_s, stop))
    try:
        await bench.stream_rtcm(rtcm_source(options, bench.note), options.rate_bytes_per_second,
                                options.duration_s, options.burst_seconds)
    finally:
        stop.set()
        await commands
    await asyncio.sleep(DRAIN_AFTER_STREAM_S)
    await _close(bench)


async def bursts(bench: Bench, options: ScenarioOptions) -> None:
    if options.burst_seconds <= 0:
        options.burst_seconds = 5.0
    await rtcm_with_commands(bench, options)


async def disconnect_during_rtcm(bench: Bench, options: ScenarioOptions) -> None:
    await _open(bench, options, rtcm_needed=True)
    source = rtcm_source(options, bench.note)
    half = options.duration_s / 2
    stream = asyncio.create_task(bench.stream_rtcm(source, options.rate_bytes_per_second, options.duration_s))
    await asyncio.sleep(half)
    await bench.disconnect(reason="corte provocado a mitad de RTCM")
    await stream
    await asyncio.sleep(PAUSE_BEFORE_RECONNECT_S)
    await bench.connect()
    await bench.snapshot("tras reconectar")
    # Nada viejo: el generador sigue desde la época siguiente; la trama que se
    # cortó quedó registrada como fallida y no se reenvía.
    await bench.stream_rtcm(source, options.rate_bytes_per_second, half)
    await asyncio.sleep(DRAIN_AFTER_STREAM_S)
    await _close(bench)


async def disconnect_during_command(bench: Bench, options: ScenarioOptions) -> None:
    await _open(bench, options, rtcm_needed=False)
    for cycle in range(max(1, min(options.cycles, 10))):
        bench.arm_response_frame_watch()
        _, waiter = await bench.send_request("GET", "/api/gnss/sky")
        waiter.add_done_callback(lambda f: f.exception() if not f.cancelled() else None)
        if not await bench.wait_first_response_frame(5.0):
            bench.note(f"ciclo {cycle + 1}: la respuesta grande no empezó a llegar en 5 s")
        await bench.disconnect(reason="corte a mitad de una orden")
        await asyncio.sleep(PAUSE_BEFORE_RECONNECT_S)
        await bench.connect()
        try:
            answer = await bench.request("GET", "/api/ble")
            bench.note(f"ciclo {cycle + 1}: tras reconectar, GET /api/ble → {answer.get('status')}")
        except Exception as error:
            bench.note(f"ciclo {cycle + 1}: tras reconectar la orden falló: {type(error).__name__}: {error}")
    await _close(bench)


async def reconnect_cycles(bench: Bench, options: ScenarioOptions) -> None:
    ok = 0
    for cycle in range(options.cycles):
        try:
            await bench.connect()
            if cycle == 0:
                await bench.snapshot("inicio")
            answer = await bench.request("GET", "/api/ble")
            ok += answer.get("status") == 200
            if cycle == options.cycles - 1:
                await bench.snapshot("fin")
            await bench.disconnect(reason=f"ciclo {cycle + 1}")
        except Exception as error:
            bench.note(f"ciclo {cycle + 1}: {type(error).__name__}: {error}")
            if bench.connected:
                await bench.disconnect(reason="limpieza tras fallo")
        await asyncio.sleep(PAUSE_BEFORE_RECONNECT_S)
    bench.note(f"ciclos con conexión y respuesta: {ok} de {options.cycles}")


async def malformed_data(bench: Bench, options: ScenarioOptions) -> None:
    """RTCM con CRC roto, tramas cortadas y ruido; y una orden que no es JSON."""
    await _open(bench, options, rtcm_needed=True)
    rng = random.Random(options.seed)
    generator = rtcm.RtcmGenerator(rtcm.EpochProfile(msm_kind=options.msm_kind,
                                                     inert_message_number=4095 if options.inert else None),
                                   seed=options.seed)
    broken_crc = noise = 0

    def frames() -> Iterator[bytes]:
        nonlocal broken_crc, noise
        for index, item in enumerate(generator.frames()):
            if index % MALFORMED_CRC_EVERY == MALFORMED_CRC_EVERY - 1:
                broken_crc += 1
                frame = bytearray(item.frame)
                frame[-1] ^= 0x55
                yield bytes(frame)
            elif index % MALFORMED_NOISE_EVERY == MALFORMED_NOISE_EVERY - 1:
                noise += 1
                # Ruido que empieza por 0xD3 con una longitud imposible de cumplir
                # antes de la trama siguiente: obliga a resincronizar.
                yield bytes((0xD3, 0x00, 0x40)) + bytes(rng.getrandbits(8) for _ in range(rng.randint(5, 60)))
            else:
                yield item.frame
    await bench.stream_rtcm(frames(), options.rate_bytes_per_second, options.duration_s)
    bench.note(f"corruptas a propósito: {broken_crc} con CRC roto y {noise} de ruido; el ESP32 debe contarlas "
               "como CRC malos (el ruido puede arrastrar una trama buena) y seguir aceptando las demás")
    # Una orden que no es JSON: el firmware contesta 400 sin id, que el resumen
    # cuenta como «respuesta sin petición» (ble_transport.cpp:188-189).
    bench.note("se escribe una orden que no es JSON; se espera una respuesta 400 sin id")
    await bench.link.write(COMMAND_UUID, b"esto no es json\n", with_response=True)
    await asyncio.sleep(DRAIN_AFTER_STREAM_S)
    await _close(bench)


async def long_session(bench: Bench, options: ScenarioOptions) -> None:
    await _open(bench, options, rtcm_needed=True)
    loop = asyncio.get_running_loop()
    end = loop.time() + options.duration_s
    source = rtcm_source(options, bench.note)
    stop = asyncio.Event()
    commands = asyncio.create_task(bench.periodic_requests(options.command_path, options.command_period_s, stop))
    next_snapshot = loop.time() + LONG_SESSION_SNAPSHOT_PERIOD_S
    try:
        while loop.time() < end:
            if not bench.connected:
                bench.note("enlace perdido: reconectando con la escalera 1-2-4-8-16-30 s")
                if not await bench.reconnect_with_backoff():
                    bench.note("no volvió tras la escalera completa; fin de la sesión")
                    break
                await bench.snapshot("tras reconectar")  # delata un reinicio del equipo (uptime)
                await bench.ensure_ble_source(options.select_ble_source)
            await bench.stream_rtcm(source, options.rate_bytes_per_second,
                                    min(LONG_SESSION_SLICE_S, end - loop.time()))
            if loop.time() >= next_snapshot and bench.connected:
                await bench.snapshot("periódica")
                next_snapshot = loop.time() + LONG_SESSION_SNAPSHOT_PERIOD_S
            bench.recorder.flush()
    finally:
        stop.set()
        await commands
    await asyncio.sleep(DRAIN_AFTER_STREAM_S)
    await _close(bench)


@dataclass(frozen=True)
class Scenario:
    run: Callable[[Bench, ScenarioOptions], Awaitable[None]]
    description: str
    defaults: dict


SCENARIOS: dict[str, Scenario] = {
    "telemetria": Scenario(telemetry_only, "solo telemetría: suscribirse y escuchar", {"duration_s": 60}),
    "rtcm-1k": Scenario(rtcm_stream, "RTCM a 1 kB/s (MSM7 de 4 constelaciones a 1 Hz)",
                        {"rate_bytes_per_second": 1000, "duration_s": 120}),
    "rtcm-3k": Scenario(rtcm_stream, "RTCM a 3 kB/s", {"rate_bytes_per_second": 3000, "duration_s": 120}),
    "rtcm-6k": Scenario(rtcm_stream, "RTCM a 6 kB/s", {"rate_bytes_per_second": 6000, "duration_s": 120}),
    "rtcm-ordenes": Scenario(rtcm_with_commands, "RTCM + una orden de lectura periódica (latencia)",
                             {"rate_bytes_per_second": 3000, "duration_s": 120, "command_period_s": 2.0}),
    "rafagas": Scenario(bursts, "RTCM a golpes, como un caster por TCP, con órdenes",
                        {"rate_bytes_per_second": 3000, "duration_s": 120, "burst_seconds": 5.0}),
    "saturacion": Scenario(rtcm_with_commands, "RTCM por encima de lo que la UART puede sacar, con órdenes",
                           {"rate_bytes_per_second": 14000, "duration_s": 60, "command_period_s": 2.0}),
    "corte-rtcm": Scenario(disconnect_during_rtcm, "desconexión a mitad de RTCM y reconexión",
                           {"rate_bytes_per_second": 3000, "duration_s": 60}),
    "corte-orden": Scenario(disconnect_during_command, "desconexión a mitad de una respuesta grande",
                            {"cycles": 5}),
    "reconexiones": Scenario(reconnect_cycles, "conectar, preguntar y soltar, muchas veces", {"cycles": 20}),
    "malformados": Scenario(malformed_data, "RTCM corrupto y una orden que no es JSON",
                            {"rate_bytes_per_second": 1000, "duration_s": 30}),
    "sesion-larga": Scenario(long_session, "RTCM a 1 kB/s + órdenes cada 10 s durante 30-60 min",
                             {"rate_bytes_per_second": 1000, "duration_s": 1800, "command_period_s": 10.0}),
}
