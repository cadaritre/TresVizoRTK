"""Identidad de placa dentro de la imagen firmada, desde 0.8.0 (byte 320)."""
HARDWARE_ID = 'tresvizo-thingplus-s3-4m-v1'
# MeridianV con la placa principal v0.3 (entorno meridianv_v03, desde 0.9.0):
# firmware/esp32/include/board_profile_v03.h.
HARDWARE_ID_V03 = 'tresvizo-meridianv-v03-s3-16m-v1'
# Entorno de PlatformIO → identidad de placa que lleva su imagen.
HARDWARE_ID_BY_ENV = {'esp32s3_usb': HARDWARE_ID, 'meridianv_v03': HARDWARE_ID_V03}
IDENTITY_OFFSET = 288
HARDWARE_OFFSET = 320
HARDWARE_BYTES = 48


def image_hardware_id(image):
    if image[IDENTITY_OFFSET:IDENTITY_OFFSET + 8] != b'TVZFWID1':
        return None
    raw = image[HARDWARE_OFFSET:HARDWARE_OFFSET + HARDWARE_BYTES]
    if len(raw) != HARDWARE_BYTES or b'\0' not in raw:
        return None
    try:
        value = raw.split(b'\0', 1)[0].decode('ascii')
    except UnicodeDecodeError:
        return None
    return value if value.startswith('tresvizo-') else None
