#!/usr/bin/env python3
"""Reinicios físicos de OLED: no cambia ajustes ni inicia grabaciones.

Ejecutar sólo con el equipo disponible para pruebas. La API confirma estado y
tiempos, no permite leer la imagen física de la OLED: comprobarla a simple vista.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from usb_console import Instrument, detect_port


def run(port, cycles, output):
    device = Instrument(port)
    records = []

    def get():
        response = device.request("GET", "/api/status")
        assert response["status"] == 200
        body = response["body"]
        # Conservar sólo diagnóstico, sin redes, credenciales ni coordenadas.
        return {
            "firmware": body["firmware_version"],
            "uptime_ms": body["uptime_ms"],
            "display": body["subsystems"]["display"],
            "recording": body["subsystems"]["microsd"]["active"],
            "closing": body["subsystems"]["microsd"]["closing"],
        }

    try:
        before = get()
        assert before["firmware"] == "0.8.1", "Primero cargar 0.8.1"
        assert not before["recording"] and not before["closing"], "Hay una grabación abierta"
        detection_deadline = time.monotonic() + 4
        while not before["display"]["available"] and time.monotonic() < detection_deadline:
            time.sleep(0.2)
            before = get()
        assert before["display"]["available"], f"OLED no detectada: {before['display']['state']}"
        for cycle in range(cycles):
            restart_deadline = time.monotonic() + 25
            while True:
                response = device.request("POST", "/api/restart", {})
                if response["status"] == 202:
                    break
                assert response["status"] == 409 and time.monotonic() < restart_deadline, response
                time.sleep(0.25) # La reconciliación inicial del GPS puede estar ocupada.
                before = get()
            assert response["status"] == 202
            # Dos pulsaciones de la app deben ser idempotentes.
            assert device.request("POST", "/api/restart", {})["status"] == 202
            # Ruta inexistente para comprobar el bloqueo de escrituras sin
            # iniciar ninguna operación real, incluso si falla esa protección.
            blocked = device.request("POST", "/api/display-bench-noop", {})
            assert blocked["status"] == 409 and blocked["body"]["error"] == "restarting"
            deadline = time.monotonic() + 22
            rebooted = False
            first_logo = last_logo = first_main = None
            samples = []
            previous_uptime = before["uptime_ms"]
            while time.monotonic() < deadline:
                try:
                    sample = get()
                except (OSError, TimeoutError):
                    time.sleep(0.15)
                    continue
                uptime = sample["uptime_ms"]
                if uptime < previous_uptime:
                    assert not rebooted, "Se produjo otro reinicio inesperado durante el logo"
                    rebooted = True
                previous_uptime = uptime
                if rebooted:
                    samples.append(sample)
                    state = sample["display"]["screen"]
                    if state == "logo":
                        assert first_main is None, "El logo reapareció después de la pantalla principal"
                        if first_logo is None:
                            first_logo = uptime
                        last_logo = uptime
                    elif state == "main":
                        if first_main is None:
                            first_main = uptime
                        assert sample["display"]["state"] == "ready"
                        if uptime >= first_main + 1200:
                            before = sample
                            break
                time.sleep(0.05)
            assert rebooted, "No se observó el reinicio"
            assert first_logo is not None, "No se observó el logo"
            assert first_main is not None, "No apareció la pantalla principal"
            # El plazo comienza dentro de setup. Margen para arranque del SDK y
            # muestreo USB; no es una medición óptica de exposición del panel.
            assert 9500 <= first_main <= 11500, f"Transición fuera de plazo: {first_main} ms"
            assert last_logo <= 11200, f"Logo retenido: {last_logo} ms"
            record = {"cycle": cycle+1, "first_logo_ms": first_logo,
                      "last_logo_ms": last_logo, "first_main_ms": first_main,
                      "samples": samples}
            records.append(record)
            print(json.dumps({k:v for k,v in record.items() if k != "samples"}), flush=True)
    finally:
        device.close()
        if output:
            Path(output).write_text(json.dumps(records, indent=2) + "\n")
    print(f"OK: {cycles} reinicios; imagen física pendiente de comprobación visual.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port")
    parser.add_argument("--cycles", type=int, default=3)
    parser.add_argument("--output")
    args = parser.parse_args()
    if not 1 <= args.cycles <= 10:
        parser.error("--cycles debe ser de 1 a 10")
    run(args.port or detect_port(), args.cycles, args.output)
