#!/usr/bin/env python3
"""Banco real de lectura: USB + BLE, fragmentación y reconexión.

No guarda respuestas, coordenadas ni credenciales. Requiere pyserial y bleak.
--stall prueba además la recuperación de una respuesta sin suscripción (corta
el enlace BLE de este banco a los 4.5 s). No cambia ajustes persistentes.
"""
import argparse
import asyncio
import hashlib
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from usb_console import Instrument, detect_port
from bleak import BleakClient, BleakScanner

SUFFIX = "-8f24-4adb-a350-77ef6339c320"
SERVICE, COMMAND, RESPONSE, SOLUTION, HEALTH = [
    "a04c000" + str(n) + SUFFIX for n in (1, 2, 3, 4, 6)
]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


async def main(args):
    usb = Instrument(args.port or detect_port())
    summary = {"cycles": [], "responses": 0, "frame_errors": 0, "fragment_bytes": args.fragment_bytes}
    original = None
    try:
        original = digest(usb.request("GET", "/api/config")["body"])
        status = usb.request("GET", "/api/status")["body"]
        summary["firmware"] = status["firmware_version"]
        latencies = []
        identity = 0
        for cycle in range(args.cycles):
            device = await BleakScanner.find_device_by_filter(
                lambda d, a: SERVICE in a.service_uuids, timeout=15)
            if not device:
                raise RuntimeError("No se encontró el servicio BLE disponible")
            queue = asyncio.Queue()
            buffer = bytearray()
            message_id = None
            health_times = []
            frame_sizes = set()

            def notify(_, data):
                nonlocal buffer, message_id
                try:
                    assert len(data) >= 5
                    frame_sizes.add(len(data))
                    mid = int.from_bytes(data[:2], "little")
                    offset = int.from_bytes(data[2:4], "little")
                    flags = data[4]
                    if flags & 1:
                        assert offset == 0
                        buffer = bytearray()
                        message_id = mid
                    assert mid == message_id and offset == len(buffer)
                    buffer.extend(data[5:])
                    assert len(buffer) <= 4096
                    if flags & 2:
                        queue.put_nowait(json.loads(buffer))
                        buffer = bytearray()
                        message_id = None
                except (AssertionError, ValueError, UnicodeError):
                    summary["frame_errors"] += 1

            def health(_, data):
                if len(data) != 20:
                    summary["frame_errors"] += 1
                health_times.append(time.monotonic())

            async with BleakClient(device, timeout=20) as client:
                await client.start_notify(RESPONSE, notify)
                await client.start_notify(HEALTH, health)
                async def send(raw):
                    # Alternar trozos pequeños y MTU negociado: no suponer
                    # límites de paquetes iguales a límites de JSON.
                    step = args.fragment_bytes if args.fragment_bytes and identity % 2 else min(client.mtu_size - 3, 244)
                    for offset in range(0, len(raw), step):
                        await client.write_gatt_char(COMMAND, raw[offset:offset+step], response=True)

                async def call(path):
                    nonlocal identity
                    identity += 1
                    request = json.dumps({"id": identity, "method": "GET", "path": path}, separators=(",", ":")).encode()+b"\n"
                    started = time.monotonic()
                    await send(request)
                    reply = await asyncio.wait_for(queue.get(), 8)
                    assert reply.get("id") == identity, "Respuesta de otra petición"
                    assert reply.get("status") == 200, (path, reply.get("status"))
                    latencies.append((time.monotonic() - started) * 1000)
                    summary["responses"] += 1
                    return reply["body"]

                for n in range(args.requests):
                    body = await call(("/api/status", "/api/ble", "/api/config")[n % 3])
                    if n % 3 == 2:
                        assert "ap_password" not in body
                # Entradas truncadas/invalidas no contaminan la siguiente orden.
                await send(b"x" * 1025 + b"\n")
                await send(b'{"id":0,"method":"GET","path":"/api/ble"}\0\n')
                await call("/api/ble")
                await asyncio.sleep(2.1)
                assert len(health_times) >= 2, "No llega el latido"
                gaps = [b-a for a, b in zip(health_times, health_times[1:])]
                summary["cycles"].append({"mtu": client.mtu_size, "max_frame_bytes": max(frame_sizes),
                    "health_packets": len(health_times), "max_health_gap_ms": round(max(gaps)*1000, 1)})
                if args.stall and cycle == 0:
                    await client.stop_notify(RESPONSE)
                    await send(b'{"id":999999,"method":"GET","path":"/api/ble"}\n')
                    started = time.monotonic()
                    while client.is_connected and time.monotonic()-started < 6:
                        await asyncio.sleep(.05)
                    assert not client.is_connected, "El envío bloqueado no cerró el enlace"
                    summary["stall_recovery_ms"] = round((time.monotonic()-started)*1000, 1)
                else:
                    # Una orden a medias no debe sobrevivir al cambio de sesión.
                    await send(b'{"id":123,"method":"GET","path":')
            print(json.dumps({"cycle": cycle+1, **summary["cycles"][-1]}), flush=True)
            await asyncio.sleep(.3)
        assert summary["frame_errors"] == 0
        summary["latency_ms"] = {"median": round(statistics.median(latencies), 1),
            "p95": round(sorted(latencies)[int((len(latencies)-1)*.95)], 1), "max": round(max(latencies), 1)}
        summary["ble"] = usb.request("GET", "/api/ble")["body"]
        assert summary["ble"]["response_frames_forced"] == 0
        assert summary["ble"]["notification_failures"] == 0
        assert summary["ble"]["response_timeouts"] == int(args.stall)
    finally:
        if original is not None:
            summary["config_unchanged"] = original == digest(usb.request("GET", "/api/config")["body"])
        usb.close()
        if args.out:
            Path(args.out).write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n")
    assert summary["config_unchanged"]
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port")
    parser.add_argument("--cycles", type=int, default=3)
    parser.add_argument("--requests", type=int, default=40)
    parser.add_argument("--fragment-bytes", type=int, default=7, help="0 usa siempre MTU negociado")
    parser.add_argument("--stall", action="store_true")
    parser.add_argument("--out")
    args = parser.parse_args()
    if args.cycles < 2 or args.requests < 1 or not 0 <= args.fragment_bytes <= 244:
        parser.error("cycles >= 2, requests >= 1, fragment-bytes entre 0 y 244")
    asyncio.run(main(args))
