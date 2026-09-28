#!/usr/bin/env python3
"""Empaqueta el firmware firmado y su manifiesto OTA, sin datos privados del equipo.

Desde 0.7.13 el equipo solo acepta por OTA firmware-signed.bin (lo deja `pio run`
si está la clave del propietario; ver tools/firmware_signing/README.md). El
manifiesto lleva tamaño y SHA-256 del archivo firmado, que es el que se sube.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sign_firmware', ROOT / 'tools/firmware_signing/sign_firmware.py')
signer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(signer)
import argparse
parser = argparse.ArgumentParser(description=__doc__)
# esp32s3_usb es el MeridianV; meridian3 el receptor sencillo (lib/protocol/src/product.h).
parser.add_argument('--env', default='esp32s3_usb', choices=['esp32s3_usb', 'meridian3'])
args = parser.parse_args()
HARDWARE_IDS = {'esp32s3_usb': 'tresvizo-esp32s3-4m-v1', 'meridian3': 'tresvizo-meridian3-esp32s3-4m-v1'}
source = ROOT / f'firmware/esp32/.pio/build/{args.env}/firmware-signed.bin'
version = re.search(r'kVersion = "([^"]+)"', (ROOT / 'firmware/esp32/include/instrument.h').read_text())[1]
if not source.is_file():
    raise SystemExit(f'No existe {source}: compila con la clave de firma instalada (tools/firmware_signing/README.md).')
data = source.read_bytes()
valid, message = signer.verify(data)
if not valid:
    raise SystemExit(f'{source}: {message} No se empaqueta.')
if len(data) - signer.TRAILER_BYTES > 0x1e0000:
    raise ValueError('La imagen no cabe en la partición de 1920 KiB.')
folder = ROOT / 'data/local/releases' / version / args.env
folder.mkdir(parents=True,exist_ok=True)
shutil.copyfile(source,folder / 'firmware-signed.bin')
manifest = {'hardware_id':HARDWARE_IDS[args.env],'size':len(data),'sha256':hashlib.sha256(data).hexdigest(),
            'firmware_version':version,'api_version':1,'module_api_version':1,'image_authenticity':'owner_signed_ecdsa_p256'}
(folder / 'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(folder)
