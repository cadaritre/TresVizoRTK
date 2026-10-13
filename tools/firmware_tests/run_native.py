#!/usr/bin/env python3
"""Compila y ejecuta las suites C++ del firmware, con UBSan y warnings como errores.

Las del MeridianV (firmware/esp32/test) y las del radio LoRa externo (firmware/radio/test),
que usa además el protocolo y el parser RTCM3 del MeridianV.
"""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
FW = ROOT / "firmware/esp32"
RADIO = ROOT / "firmware/radio"
SUITES = [
    (FW, [FW / include for include in ["include", "lib/gnss/src", "lib/protocol/src",
                                       ".pio/libdeps/esp32s3_usb/ArduinoJson/src"]]),
    (RADIO, [RADIO / "src", FW / "lib/gnss/src", FW / "lib/protocol/src"]),
]
with tempfile.TemporaryDirectory(prefix="tresvizo-native-") as folder:
    count = 0
    for project, includes in SUITES:
        for source in sorted((project / "test").glob("*_test.cpp")):
            binary = Path(folder) / f"{project.name}-{source.stem}"
            args = [os.environ.get("CXX", "clang++"), "-std=c++17", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=undefined", "-fno-sanitize-recover=all"]
            if source.stem.endswith("_integration_test"):
                args += ["-I" + str(project / "test/host")]
            args += ["-I" + str(include) for include in includes]
            subprocess.run(args + [str(source), "-o", str(binary)], cwd=ROOT, check=True)
            subprocess.run([str(binary)], cwd=FW if source.stem == "json_allowlist_test" else ROOT, check=True)
            print(f"OK {project.name}/{source.stem}", flush=True)
            count += 1
    print(f"{count} suites C++ superadas.")
