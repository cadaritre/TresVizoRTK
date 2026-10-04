#!/usr/bin/env python3
"""Banco USB de sustitución: solo consultas GNSS, validación y un reinicio.

No aplica coordenadas, tasas, máscaras ni perfiles NTRIP. Comprueba que las
órdenes aceptadas no exigen esperar al trabajo anterior y que un cuerpo inválido
no altera el trabajo vigente. No imprime credenciales ni coordenadas.
"""
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from usb_console import Instrument, detect_port

u = Instrument(detect_port())
latencies = []
def call(method, path, body=None, expected=200):
    started = time.monotonic()
    response = u.request(method, path, body)
    elapsed = (time.monotonic() - started) * 1000
    assert response["status"] == expected, (path, response["status"], response.get("body", {}).get("error"))
    return response["body"], elapsed

try:
    original, _ = call("GET", "/api/config")
    initial, _ = call("GET", "/api/status")
    source, _ = call("GET", "/api/corrections/source")
    previous = 0
    for action in ["query", "config_query", "query", "config_query", "query"]:
        accepted, elapsed = call("POST", "/api/gnss/control", {"action": action}, 202)
        assert accepted["job_id"] > previous
        previous = accepted["job_id"]
        latencies.append(elapsed)
    call("POST", "/api/gnss/control", {"action": "rover", "invalid": True}, 400)
    control, _ = call("GET", "/api/gnss/control")
    assert control["job_id"] == previous
    current_source, _ = call("GET", "/api/corrections/source")
    assert current_source["chosen_source"] == source["chosen_source"]
    assert current_source["active_source"] == source["active_source"]
    call("PUT", "/api/corrections/source", {"source": "invalid"}, 400)
    current_source, _ = call("GET", "/api/corrections/source")
    assert current_source["active_source"] == source["active_source"]
    # Reinicio válido durante consulta: respuesta inmediata, sin esperar timeout UART.
    call("POST", "/api/gnss/control", {"action": "query"}, 202)
    restart, restart_ms = call("POST", "/api/restart", {}, 202)
    assert restart["restarting"]
    u.close()
    time.sleep(3)
    after = None
    for _ in range(10):
        try:
            candidate, _ = call("GET", "/api/status")
            if candidate["uptime_ms"] < 15000:
                after = candidate
                break
        except (OSError, TimeoutError):
            pass
        time.sleep(.5)
    assert after is not None, "No volvió tras reinicio"
    current, _ = call("GET", "/api/config")
    assert current == original, "Cambió la configuración durante el banco"
    digest = hashlib.sha256(json.dumps(current, sort_keys=True).encode()).hexdigest()
    baseline = Path("/tmp/tresvizo-priority-config.sha256")
    if baseline.exists():
        assert digest == baseline.read_text().strip(), "Cambió configuración frente a imagen anterior"
    print(json.dumps({
        "firmware": after["firmware_version"], "accepted_queries": len(latencies),
        "median_response_ms": round(statistics.median(latencies), 1),
        "max_response_ms": round(max(latencies), 1), "restart_response_ms": round(restart_ms, 1),
        "invalid_request_preserved_job": True, "config_unchanged": True,
        "wifi_station_state": after["wifi"]["station_state"],
        "display_state": after["subsystems"]["display"]["state"],
    }, indent=2))
finally:
    u.close()
