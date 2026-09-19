#!/usr/bin/env python3
"""Pruebas explícitas en ESP32: cambia ajustes temporales y reinicia el equipo."""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from usb_console import Instrument, detect_port


def run(port):
    device = Instrument(port)
    checks = []
    original = None

    def check(condition, label):
        if not condition:
            raise AssertionError(label)
        checks.append(label)
        print(f"OK: {label}", flush=True)

    def get(path):
        result = device.request("GET", path)
        assert result["status"] == 200, result["status"]
        return result["body"]

    def update(body):
        return device.request("PUT", "/api/config", body)

    def reboot():
        result = device.request("POST", "/api/restart", {})
        assert result["status"] == 202
        device.close()
        time.sleep(2)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                return get("/api/status")
            except (OSError, TimeoutError):
                time.sleep(0.5)
        raise AssertionError("No se recuperó el enlace tras reiniciar")

    try:
        status = get("/api/status")
        check(status["flash_bytes"] == 4194304, "Flash de 4 MB detectada")
        check(status["wifi"]["ap_ready"], "Punto de acceso iniciado")
        check(status["solution"]["fix"] is None and status["solution"]["latitude_deg"] is None, "Sin posición ni FIX simulados")
        check(all(value["state"] == "not_integrated" for value in status["subsystems"].values()), "Sensores no integrados explícitos")
        original = get("/api/config")
        check("wifi_password" not in original and "access_key" not in status, "Secretos ausentes de estado y configuración")
        invalid = device._exchange("GET", "/api/status", key="incorrecta")
        check(invalid["status"] == 401, "Acceso sin clave válida rechazado")
        for body, label in [
            ({"device_name": "<script>"}, "Nombre con contenido HTML rechazado"),
            ({"device_name": "x" * 33}, "Nombre mayor a 32 bytes rechazado"),
            ({"device_name": None}, "Valor nulo rechazado"),
            ({"device_name": "prueba\u0000oculta"}, "NUL incrustado rechazado"),
            ({"refresh_ms": 0}, "Intervalo cero rechazado"),
            ({"refresh_ms": "1000"}, "Tipo de intervalo inválido rechazado"),
            ({"wifi_ssid": "é" * 17}, "Límite SSID aplicado en bytes UTF-8"),
            ({"wifi_ssid": "red-de-prueba", "wifi_password": "corta"}, "Contraseña corta rechazada"),
            ({"wifi_ssid": "red-de-prueba", "wifi_password": ""}, "Nueva red sin contraseña rechazada"),
            ({"forget_wifi": "true"}, "Tipo booleano inválido rechazado"),
            ({"gnss_mode": "base"}, "Ajuste de hardware no implementado rechazado"),
        ]:
            result = update({"revision": original["revision"], **body})
            check(result["status"] == 400, label)
        check(get("/api/config") == original, "Solicitudes inválidas no alteran la configuración")
        changed = update({"revision": original["revision"], "device_name": "TresVizo prueba USB", "refresh_ms": 5000})
        check(changed["status"] == 200 and changed["body"]["changed"], "Ajustes válidos guardados")
        new_config = get("/api/config")
        unchanged = update({"revision": new_config["revision"], "device_name": new_config["device_name"]})
        check(unchanged["status"] == 200 and not unchanged["body"]["changed"], "Guardado sin cambios evita escribir de nuevo")
        conflict = update({"revision": original["revision"], "device_name": "Conflicto"})
        check(conflict["status"] == 409, "Revisión obsoleta rechazada")
        after_restart = reboot()
        check(after_restart["device_name"] == "TresVizo prueba USB" and after_restart["uptime_ms"] < 20000, "Reinicio y persistencia comprobados")
        check(get("/api/config")["refresh_ms"] == 5000, "Intervalo persiste tras reiniciar")
        # El parser debe recuperarse tras una línea más grande que su buffer.
        device.connection.write(b"x" * 1200 + b"\n")
        line = device.connection.read_until(b"\n", 2048)
        check(json.loads(line)["status"] == 413, "Línea USB sobredimensionada rechazada")
        check(get("/api/status")["api_version"] == 1, "Parser USB recuperado después del desbordamiento")
        device.connection.write(b'{"id":999,"method":\n')
        line = device.connection.read_until(b"\n", 2048)
        check(json.loads(line)["status"] == 400, "JSON incompleto rechazado")
        samples = [get("/api/status") for _ in range(20)]
        check(min(s["free_heap_bytes"] for s in samples) > 100000, "20 consultas consecutivas con memoria disponible")
    finally:
        if original is not None:
            current = get("/api/config")
            result = update({"revision": current["revision"], "device_name": original["device_name"], "refresh_ms": original["refresh_ms"]})
            assert result["status"] == 200, "No se pudo restaurar la configuración original"
            restored = reboot()
            check(restored["device_name"] == original["device_name"], "Ajustes originales restaurados y reiniciados")
        device.close()
    print(f"Completadas {len(checks)} comprobaciones de hardware.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port")
    args = parser.parse_args()
    run(args.port or detect_port())
