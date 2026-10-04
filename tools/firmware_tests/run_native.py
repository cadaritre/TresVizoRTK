#!/usr/bin/env python3
"""Compila y ejecuta las suites C++ del firmware, con UBSan y warnings como errores."""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
FW = ROOT / "firmware/esp32"
with tempfile.TemporaryDirectory(prefix="tresvizo-native-") as folder:
    tests = sorted((FW / "test").glob("*_test.cpp"))
    for source in tests:
        binary = Path(folder) / source.stem
        args = [os.environ.get("CXX", "clang++"), "-std=c++17", "-Wall", "-Wextra", "-Werror",
                "-fsanitize=undefined", "-fno-sanitize-recover=all"]
        if source.stem.endswith("_integration_test"):
            args += ["-I" + str(FW / "test/host")]
        for include in ["include", "lib/gnss/src", "lib/protocol/src", ".pio/libdeps/esp32s3_usb/ArduinoJson/src"]:
            args += ["-I" + str(FW / include)]
        subprocess.run(args + [str(source), "-o", str(binary)], cwd=ROOT, check=True)
        subprocess.run([str(binary)], cwd=FW if source.stem == "json_allowlist_test" else ROOT, check=True)
        print(f"OK {source.stem}", flush=True)
    print(f"{len(tests)} suites C++ superadas.")
