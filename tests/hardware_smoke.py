#!/usr/bin/env python3
"""Pruebas explícitas en ESP32: cambia ajustes temporales y reinicia el equipo."""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from usb_console import Instrument, detect_port
from firmware_identity import HARDWARE_ID


def run(port, require_oled=False, require_sd=False):
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
        check(status.get("hardware_id") == HARDWARE_ID, "Firmware de Thing Plus identificado antes de modificar ajustes")
        check(status["flash_bytes"] == 4194304, "Flash de 4 MB detectada")
        check(status["wifi"]["ap_ready"], "Punto de acceso iniciado")
        check(status["solution"]["fix"] != "simulated" and (status["solution"]["fix"] not in (None,"invalid") or status["solution"]["latitude_deg"] is None), "Sin FIX simulado; sin coordenadas cuando no hay solución")
        subsystems = status["subsystems"]
        check(subsystems["imu"]["state"] == "not_integrated" and subsystems["gnss"]["state"] in ("waiting_data","receiving","stale") and subsystems["ntrip"]["available"], "UART/NTRIP disponibles; IMU pendiente explícita")
        check((subsystems["gnss"]["rx_gpio"], subsystems["gnss"]["tx_gpio"], subsystems["gnss"]["baud"]) == (44, 43, 115200), "UART configurada para Thing Plus")
        sd, oled = subsystems["microsd"], subsystems["display"]
        check(sd["interface"] == "sdmmc_4bit" and isinstance(sd["card_present"], bool) and isinstance(sd["closing"], bool), "microSD integrada informa detección y cierre")
        check(not sd["available"] or sd["card_present"], "No se anuncia microSD disponible sin tarjeta")
        check((oled["driver"], oled["width"], oled["height"], oled["sda_gpio"], oled["scl_gpio"]) == ("ssd1306", 128, 64, 8, 9), "OLED configurada para Thing Plus")
        if require_oled:
            check(oled["available"] and oled["state"] == "ready" and oled["i2c_address"] in (0x3c, 0x3d), "OLED responde por I2C; comprobar imagen a simple vista")
        if require_sd:
            check(sd["available"] and sd["card_present"] and not sd["active"] and not sd["closing"], "Tarjeta montada e inactiva antes del ensayo")
        check(status["subsystems"]["ble"]["control_available"], "Servicio de control BLE iniciado")
        original = get("/api/config")
        check("wifi_password" not in original, "Contraseña de red externa ausente de la configuración")
        # Desde 0.6.2 el panel no pide clave: no hay 401 que comprobar. La del
        # Wi-Fi propio sí se expone a propósito, para poder teclearla en un teléfono.
        check(bool(original.get("ap_password")), "Contraseña del Wi-Fi propio visible para el operador")
        check(original.get("device_name") == "MeridianV", "Nombre fijo del equipo")
        for body, label in [
            ({"ap_password": "corta"}, "Contraseña de AP demasiado corta rechazada"),
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
        changed = update({"revision": original["revision"], "refresh_ms": 5000})
        check(changed["status"] == 200 and changed["body"]["changed"], "Ajustes válidos guardados")
        new_config = get("/api/config")
        unchanged = update({"revision": new_config["revision"], "refresh_ms": 5000})
        check(unchanged["status"] == 200 and not unchanged["body"]["changed"], "Guardado sin cambios evita escribir de nuevo")
        conflict = update({"revision": original["revision"], "refresh_ms": 1000})
        check(conflict["status"] == 409, "Revisión obsoleta rechazada")
        after_restart = reboot()
        check(after_restart["device_name"] == "MeridianV" and after_restart["uptime_ms"] < 20000, "Reinicio y persistencia comprobados")
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
            result = update({"revision": current["revision"], "refresh_ms": original["refresh_ms"]})
            assert result["status"] == 200, "No se pudo restaurar la configuración original"
            restored = reboot()
            check(restored["refresh_ms"] == original["refresh_ms"], "Ajustes originales restaurados y reiniciados")
        device.close()
    print(f"Completadas {len(checks)} comprobaciones de hardware.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port")
    parser.add_argument("--require-oled", action="store_true", help="Exigir respuesta de la OLED conectada")
    parser.add_argument("--require-sd", action="store_true", help="Exigir tarjeta FAT32 insertada antes de arrancar")
    args = parser.parse_args()
    run(args.port or detect_port(), args.require_oled, args.require_sd)
