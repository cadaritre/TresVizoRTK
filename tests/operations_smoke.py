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
        check(body["base"]["can_preview"] and not body["base"]["can_apply"])
        check(body["recording"]["sessions"] is None and not body["recording"]["can_start"])
        check(all(not value["can_start"] for value in body["corrections"].values()))
        plan = dict(method="known",station_id=1,datum="Test frame",coordinate_epoch=None,
                    latitude_deg=0,longitude_deg=0,ellipsoid_height_m=100,antenna_vertical_m=2,height_point="marker")
        r = preview(plan)
        check(r["status"] == 200 and not r["body"]["applied"] and not r["body"]["persisted"])
        check(r["body"]["plan"]["arp_ellipsoid_height_m"] == 102)
        r = preview({**plan,"height_point":"arp"})
        check(r["body"]["plan"]["arp_ellipsoid_height_m"] == 100)
        for patch in [dict(station_id=-1),dict(station_id=4096),dict(station_id=1.5),
                      dict(latitude_deg=91),dict(longitude_deg=-181),dict(latitude_deg="0"),
                      dict(latitude_deg=None),dict(antenna_vertical_m=-1),dict(ellipsoid_height_m=30000),
                      dict(height_point="inclined"),dict(datum=""),dict(datum="a\0b"),
                      dict(coordinate_epoch=3000),dict(command="MODE BASE")]:
            check(preview({**plan,**patch})["status"]==400)
        average=dict(method="average",station_id=4095,average_seconds=300,reuse_distance_m=0)
        check(preview(average)["status"]==200)
        check(preview({**average,"average_seconds":3601})["status"]==400)
        check(preview({**average,"reuse_distance_m":11})["status"]==400)
        check(device._exchange("POST","/api/base/plan",plan,key="wrong")["status"]==401)
        check(device.request("POST","/api/recording/start",{})["status"]==404)
        check(device.request("GET","/api/config")["body"]==before["body"])
        print(f"Operaciones: {count} comprobaciones; sin cambios persistentes ni comandos GNSS.")
    finally:
        device.close()
if __name__=="__main__": run()
