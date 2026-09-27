#!/usr/bin/env python3
"""Prueba preparación de base en ESP32, sin aplicar comandos ni grabar."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from usb_console import Instrument, detect_port

def run():
    device = Instrument(detect_port())
    count = 0
    def check(value):
        nonlocal count
        assert value
        count += 1
    def preview(plan):
        return device.request("POST", "/api/base/plan", plan)
    try:
        before = device.request("GET", "/api/config")
        caps = device.request("GET", "/api/operations")
        check(caps["status"] == 200)
        body = caps["body"]
        check(body["base"]["can_preview"] and body["base"]["can_apply"])
        check(body["recording"]["sessions"] is None and not body["recording"]["can_start"])
        check(body["corrections"]["input"]["can_start"] and all(not body["corrections"][role]["can_start"] for role in ("publisher","local_caster")))
        plan = dict(method="known",station_id=1,
                    latitude_deg=0,longitude_deg=0,ellipsoid_height_m=100,antenna_vertical_m=2)
        r = preview(plan)
        check(r["status"] == 200 and not r["body"]["applied"] and not r["body"]["persisted"])
        # Altura declarada = punto + antena + los 10 cm de case que suma el equipo.
        check(abs(r["body"]["plan"]["arp_ellipsoid_height_m"] - 102.10) < 1e-6)
        check(abs(r["body"]["plan"]["case_offset_m"] - 0.10) < 1e-9)
        check(r["body"]["plan"]["datum"] == "WGS84")
        for patch in [dict(station_id=-1),dict(station_id=4096),dict(station_id=1.5),
                      dict(latitude_deg=91),dict(longitude_deg=-181),dict(latitude_deg="0"),
                      dict(latitude_deg=None),dict(antenna_vertical_m=-1),dict(ellipsoid_height_m=30000),
                      dict(command="MODE BASE"),
                      # Retirados en 0.6.2: enviarlos ahora debe rechazarse.
                      dict(datum="Test frame"),dict(coordinate_epoch=2020.5),
                      dict(height_point="marker")]:
            check(preview({**plan,**patch})["status"]==400)
        average=dict(method="average",station_id=4095,average_seconds=300,reuse_distance_m=0)
        check(preview(average)["status"]==200)
        check(preview({**average,"average_seconds":3601})["status"]==400)
        check(preview({**average,"reuse_distance_m":11})["status"]==400)
        # La clave de panel se retiró en 0.6.2: ya no hay respuesta 401 que probar.
        check(device.request("POST","/api/recording/start",{})["status"]==503)
        check(device.request("GET","/api/config")["body"]==before["body"])
        print(f"Operaciones: {count} comprobaciones; sin cambios persistentes ni comandos GNSS.")
    finally:
        device.close()
if __name__=="__main__": run()
