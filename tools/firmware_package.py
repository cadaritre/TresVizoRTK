#!/usr/bin/env python3
"""Empaqueta el firmware firmado y su manifiesto OTA, sin datos privados del equipo.

Desde 0.7.13 el equipo solo acepta por OTA firmware-signed.bin (lo deja `pio run`
si está la clave del propietario; ver tools/firmware_signing/README.md). El
manifiesto lleva tamaño y SHA-256 del archivo firmado, que es el que se sube.

Uso: `python3 tools/firmware_package.py [entorno]`. Sin entorno, la Thing Plus
(`esp32s3_usb`); `meridianv_v03` empaqueta la de la placa v0.3, en su propia carpeta.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sign_firmware', ROOT / 'tools/firmware_signing/sign_firmware.py')
signer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(signer)
from firmware_identity import HARDWARE_ID_BY_ENV, image_hardware_id
ENV = sys.argv[1] if len(sys.argv) > 1 else 'esp32s3_usb'
if ENV not in HARDWARE_ID_BY_ENV:
    raise SystemExit(f'Entorno desconocido: {ENV}. Conocidos: {", ".join(HARDWARE_ID_BY_ENV)}.')
HARDWARE_ID = HARDWARE_ID_BY_ENV[ENV]
source = ROOT / f'firmware/esp32/.pio/build/{ENV}/firmware-signed.bin'
version = re.search(r'kVersion = "([^"]+)"', (ROOT / 'firmware/esp32/include/instrument.h').read_text())[1]
if not source.is_file():
    raise SystemExit(f'No existe {source}: compila con la clave de firma instalada (tools/firmware_signing/README.md).')
data = source.read_bytes()
valid, message = signer.verify(data)
if not valid:
    raise SystemExit(f'{source}: {message} No se empaqueta.')
if image_hardware_id(data) != HARDWARE_ID:
    raise SystemExit(f'La compilación no corresponde a {HARDWARE_ID}. No se empaqueta.')
# 1920 KiB: la ranura OTA de la Thing Plus y, en la v0.3 (ranuras de 4 MB), lo que
# todavía comparan las apps en vez de leer `max_image_bytes`.
if len(data) - signer.TRAILER_BYTES > 0x1e0000:
    raise ValueError('La imagen no cabe en 1920 KiB.')
folder = ROOT / 'data/local/releases' / version
if ENV != 'esp32s3_usb':
    folder = folder / ENV
folder.mkdir(parents=True,exist_ok=True)
shutil.copyfile(source,folder / 'firmware-signed.bin')
manifest = {'hardware_id':HARDWARE_ID,'size':len(data),'sha256':hashlib.sha256(data).hexdigest(),
            'firmware_version':version,'api_version':1,'module_api_version':1,'image_authenticity':'owner_signed_ecdsa_p256'}
(folder / 'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(folder)
