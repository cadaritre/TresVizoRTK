#!/usr/bin/env python3
"""Firma el firmware del Meridian V para la OTA, o comprueba un archivo firmado.

Formato (contrato con el equipo, firmware/esp32/lib/protocol/src/signed_firmware.h):

    firmware-signed.bin = firmware.bin + b"TVZSIG01" + r (32 bytes) + s (32 bytes)

con (r, s) la firma ECDSA P-256 sobre SHA-256 de firmware.bin, en big-endian.

Uso:
    sign_firmware.py firmware.bin firmware-signed.bin [--key RUTA] [--pubkey RUTA]
    sign_firmware.py --verify firmware-signed.bin [--pubkey RUTA]

La clave privada por defecto es ~/.tresvizo/firmware-signing/private.pem, o la
que diga TRESVIZO_SIGNING_KEY. Este script nunca la lee ni la copia: le pasa la
ruta a `openssl` (OpenSSL o LibreSSL del sistema; otro con OPENSSL=RUTA). Sin
dependencias fuera de la biblioteca estándar.

Al firmar, el resultado se comprueba enseguida; si no verifica, no se deja.
Tanto eso como --verify usan por defecto la clave pública embebida en el
firmware (firmware/esp32/include/firmware_signing_key.h): lo mismo que
comprobará el equipo. Con --pubkey, la de un PEM (p. ej. una clave de prueba).
"""
import argparse
import base64
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[2]
KEY_HEADER = REPO / 'firmware/esp32/include/firmware_signing_key.h'
DEFAULT_KEY = Path('~/.tresvizo/firmware-signing/private.pem')
KEY_ENVIRONMENT = 'TRESVIZO_SIGNING_KEY'

MAGIC = b'TVZSIG01'
SIGNATURE_BYTES = 64
TRAILER_BYTES = len(MAGIC) + SIGNATURE_BYTES  # 72
HALF = SIGNATURE_BYTES // 2
# Lo mismo que exige el equipo (signed_firmware.h, kMinImageBytes).
MIN_IMAGE_BYTES = 1024
# Cabecera de imagen de aplicación ESP-IDF: byte mágico y chip ESP32-S3.
IMAGE_MAGIC = 0xE9
ESP32S3_CHIP_ID = 9
# SubjectPublicKeyInfo de una clave P-256 hasta el punto sin comprimir
# (SEQUENCE { SEQUENCE { id-ecPublicKey, prime256v1 }, BIT STRING }).
P256_SPKI_PREFIX = bytes.fromhex('3059301306072a8648ce3d020106082a8648ce3d030107034200')


class SigningError(Exception):
    """Fallo con un mensaje en español listo para enseñar."""


def default_key_path():
    return Path(os.environ.get(KEY_ENVIRONMENT) or DEFAULT_KEY).expanduser()


def openssl():
    binary = os.environ.get('OPENSSL') or shutil.which('openssl')
    if not binary:
        raise SigningError('No se encontró openssl. Instálalo o indica su ruta con OPENSSL=RUTA.')
    return binary


def check_image(image):
    """Imagen de aplicación ESP32-S3, sin firmar."""
    if len(image) < MIN_IMAGE_BYTES:
        raise SigningError(f'La imagen tiene {len(image)} bytes; el mínimo es {MIN_IMAGE_BYTES}.')
    if image[0] != IMAGE_MAGIC or int.from_bytes(image[12:14], 'little') != ESP32S3_CHIP_ID:
        raise SigningError('No es una imagen de aplicación ESP32-S3 (firmware.bin).')
    if image[-TRAILER_BYTES:-SIGNATURE_BYTES] == MAGIC:
        raise SigningError('Este archivo ya está firmado. Firma firmware.bin, no firmware-signed.bin.')


def der_to_raw(der):
    """Firma DER (SEQUENCE de dos INTEGER) a r||s de 32 + 32 bytes."""
    def integer(data, at):
        if at + 2 > len(data) or data[at] != 0x02:
            raise SigningError('openssl devolvió una firma DER inesperada.')
        length = data[at + 1]
        value = data[at + 2:at + 2 + length]
        if length == 0 or length >= 0x80 or len(value) != length:
            raise SigningError('openssl devolvió una firma DER inesperada.')
        value = value.lstrip(b'\0')
        if len(value) > HALF:
            raise SigningError('openssl devolvió una firma que no es de P-256.')
        return value.rjust(HALF, b'\0'), at + 2 + length

    if len(der) < 8 or der[0] != 0x30 or der[1] >= 0x80 or der[1] != len(der) - 2:
        raise SigningError('openssl devolvió una firma DER inesperada.')
    r, at = integer(der, 2)
    s, at = integer(der, at)
    if at != len(der):
        raise SigningError('openssl devolvió una firma DER inesperada.')
    return r + s


def raw_to_der(raw):
    """r||s a firma DER, para que openssl la compruebe."""
    def integer(value):
        value = value.lstrip(b'\0') or b'\0'
        if value[0] & 0x80:
            value = b'\0' + value
        return bytes([0x02, len(value)]) + value

    body = integer(raw[:HALF]) + integer(raw[HALF:])
    return bytes([0x30, len(body)]) + body


def embedded_public_key_pem():
    """PEM de la clave pública que lleva el firmware, leída de su cabecera."""
    text = KEY_HEADER.read_text()
    match = re.search(r'kPublicKey\[65\]\s*=\s*\{([^}]*)\}', text)
    if not match:
        raise SigningError(f'No se encontró kPublicKey en {KEY_HEADER}.')
    point = bytes(int(byte, 16) for byte in re.findall(r'0x([0-9a-fA-F]{2})', match[1]))
    if len(point) != 65 or point[0] != 0x04:
        raise SigningError(f'La clave de {KEY_HEADER} no es un punto P-256 sin comprimir.')
    encoded = base64.b64encode(P256_SPKI_PREFIX + point).decode()
    lines = [encoded[i:i + 64] for i in range(0, len(encoded), 64)]
    return '-----BEGIN PUBLIC KEY-----\n' + '\n'.join(lines) + '\n-----END PUBLIC KEY-----\n'


def sign(image, key):
    """Archivo firmado a partir de la imagen. La clave solo la abre openssl."""
    check_image(image)
    if not key.is_file():
        raise SigningError(f'No existe la clave privada {key}.')
    result = subprocess.run([openssl(), 'dgst', '-sha256', '-sign', str(key)],
                            input=image, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        detail = result.stderr.decode(errors='replace').strip()
        raise SigningError(f'openssl no pudo firmar con {key}: {detail}')
    return image + MAGIC + der_to_raw(result.stdout)


def verify(signed, pubkey=None):
    """(válida, mensaje) de un archivo firmado, con la clave embebida o un PEM."""
    if len(signed) < MIN_IMAGE_BYTES + TRAILER_BYTES:
        return False, 'El archivo es demasiado pequeño para ser un firmware firmado.'
    image, trailer = signed[:-TRAILER_BYTES], signed[-TRAILER_BYTES:]
    if trailer[:len(MAGIC)] != MAGIC:
        return False, 'El archivo no trae la firma del propietario (falta TVZSIG01 al final).'
    try:
        check_image(image)
    except SigningError as error:
        return False, str(error)
    with tempfile.TemporaryDirectory() as folder:
        signature = Path(folder) / 'signature.der'
        signature.write_bytes(raw_to_der(trailer[len(MAGIC):]))
        if pubkey is None:
            pubkey = Path(folder) / 'embedded-public.pem'
            pubkey.write_text(embedded_public_key_pem())
        result = subprocess.run([openssl(), 'dgst', '-sha256', '-verify', str(pubkey), '-signature', str(signature)],
                                input=image, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode == 0 and b'Verified OK' in result.stdout:
        return True, 'Firma válida.'
    return False, 'La firma no es válida con esa clave pública.'


def sign_file(source, destination, key):
    """Firma `source` en `destination` sin dejar un archivo a medias."""
    signed = sign(Path(source).read_bytes(), Path(key))
    destination = Path(destination)
    partial = destination.with_name(destination.name + '.partial')
    partial.write_bytes(signed)
    os.replace(partial, destination)
    return signed


def describe(signed):
    return (f'{len(signed)} bytes (imagen {len(signed) - TRAILER_BYTES} + {TRAILER_BYTES} de firma), '
            f'SHA-256 {hashlib.sha256(signed).hexdigest()}')


def main():
    parser = argparse.ArgumentParser(description='Firma firmware.bin para la OTA del Meridian V, o comprueba un archivo firmado.')
    parser.add_argument('files', nargs='+', type=Path, metavar='ARCHIVO',
                        help='firmware.bin y la salida firmada; con --verify, el archivo firmado')
    parser.add_argument('--key', type=Path, help=f'clave privada (por defecto {KEY_ENVIRONMENT} o {DEFAULT_KEY})')
    parser.add_argument('--verify', action='store_true', help='comprobar un archivo firmado en vez de firmar')
    parser.add_argument('--pubkey', type=Path, help='clave pública PEM con la que comprobar (por defecto, la embebida en el firmware)')
    args = parser.parse_args()
    try:
        if args.verify:
            if len(args.files) != 1 or args.key:
                parser.error('--verify recibe un solo archivo y no usa --key')
            signed = args.files[0].read_bytes()
            ok, message = verify(signed, args.pubkey)
            source = f'la clave de {args.pubkey}' if args.pubkey else 'la clave embebida en el firmware'
            print(f'{args.files[0]}: {message} Comprobado con {source}.')
            if ok:
                print(describe(signed))
            return 0 if ok else 1
        if len(args.files) != 2:
            parser.error('para firmar: firmware.bin y la salida firmada')
        source, destination = args.files
        if source.resolve() == destination.resolve():
            parser.error('la salida no puede ser el mismo archivo que la entrada')
        signed = sign_file(source, destination, args.key or default_key_path())
        # Recién firmado se comprueba con la clave que usará el equipo: si la
        # privada no es la suya, el archivo no serviría y es mejor no dejarlo.
        ok, message = verify(signed, args.pubkey)
        if not ok:
            destination.unlink()
            if args.pubkey:
                raise SigningError(f'La firma no verifica con {args.pubkey}. No se deja archivo firmado.')
            raise SigningError('La firma no verifica con la clave pública embebida en el firmware: '
                               'la clave privada no es la del equipo. No se deja archivo firmado.')
        source = f'la clave de {args.pubkey}' if args.pubkey else 'la clave embebida en el firmware'
        print(f'{destination}: {describe(signed)}. Verificada con {source}.')
        return 0
    except (SigningError, OSError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
