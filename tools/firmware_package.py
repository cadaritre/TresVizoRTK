#!/usr/bin/env python3
"""Empaqueta firmware de aplicación y manifiesto OTA, sin datos privados del equipo."""
import hashlib
import json
from pathlib import Path
import re
import shutil
ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'firmware/esp32/.pio/build/esp32s3_usb/firmware.bin'
version = re.search(r'kVersion = "([^"]+)"', (ROOT / 'firmware/esp32/include/instrument.h').read_text())[1]
data = source.read_bytes()
if data[0] != 0xe9 or int.from_bytes(data[12:14],'little') != 9 or not 1024 <= len(data) <= 0x1e0000:
    raise ValueError('No es una imagen de aplicación compatible con ESP32-S3 / partición de 1920 KiB.')
folder = ROOT / 'data/local/releases' / version
folder.mkdir(parents=True,exist_ok=True)
shutil.copyfile(source,folder / 'firmware.bin')
manifest = {'hardware_id':'tresvizo-esp32s3-4m-v1','size':len(data),'sha256':hashlib.sha256(data).hexdigest(),
            'firmware_version':version,'api_version':1,'module_api_version':1,'image_authenticity':'owner_supplied_unsigned'}
(folder / 'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(folder)
