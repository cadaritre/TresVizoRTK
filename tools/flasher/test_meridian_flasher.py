"""Pruebas del cargador sin ventana: python3 -m unittest tools/flasher/test_meridian_flasher.py"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import meridian_flasher as mf  # noqa: E402

MERIDIANV, MERIDIAN3 = mf.MODELS


def fake_app(hardware_id=b'', version=b'0.7.14', size=4096):
    """Imagen mínima con la forma de una de ESP32-S3: cabecera, descriptor e identidad."""
    data = bytearray(size)
    data[0] = mf.ESP_IMAGE_MAGIC
    data[12:14] = mf.ESP32S3_CHIP_ID.to_bytes(2, 'little')
    data[32:36] = mf.APP_DESC_MAGIC
    identity = mf.IDENTITY_MAGIC + version.ljust(mf.IDENTITY_VERSION_BYTES, b'\0')
    data[mf.IDENTITY_OFFSET:mf.IDENTITY_OFFSET + len(identity)] = identity
    data[2000:2000 + len(hardware_id)] = hardware_id
    return bytes(data)


class FakeSigner:
    def __init__(self, valid):
        self.valid = valid

    def verify(self, data):
        return (True, 'Firma válida.') if self.valid else (False, 'La firma no es válida con esa clave pública.')


class ImageTests(unittest.TestCase):
    def write(self, data):
        handle = tempfile.NamedTemporaryFile(suffix='.bin', delete=False)
        handle.write(data)
        handle.close()
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return Path(handle.name)

    def test_models_by_hardware_id(self):
        self.assertEqual(mf.model_by_hardware_id(fake_app(MERIDIANV.hardware_id.encode())), MERIDIANV)
        self.assertEqual(mf.model_by_hardware_id(fake_app(MERIDIAN3.hardware_id.encode())), MERIDIAN3)
        self.assertIsNone(mf.model_by_hardware_id(fake_app(b'otra-cosa')))

    def test_unsigned_image(self):
        info = mf.inspect_image(self.write(fake_app(MERIDIAN3.hardware_id.encode())))
        self.assertEqual(info.model, MERIDIAN3)
        self.assertEqual(info.version, '0.7.14')
        self.assertFalse(info.signed)
        self.assertEqual(len(info.app), 4096)

    def test_signed_image_strips_trailer(self):
        app = fake_app(MERIDIANV.hardware_id.encode())
        signed = app + mf.SIGNATURE_MAGIC + bytes(64)
        info = mf.inspect_image(self.write(signed), signer=FakeSigner(True))
        self.assertTrue(info.signed)
        self.assertTrue(info.signature_ok)
        self.assertEqual(info.app, app)  # a la flash va la imagen sin los 72 bytes
        bad = mf.inspect_image(self.write(signed), signer=FakeSigner(False))
        self.assertFalse(bad.signature_ok)
        self.assertIn('FIRMA NO VÁLIDA', bad.describe())

    def test_rejects_non_app_images(self):
        with self.assertRaises(mf.FlasherError):
            mf.inspect_image(self.write(b'\x00' * 4096))
        wrong_chip = bytearray(fake_app())
        wrong_chip[12:14] = (2).to_bytes(2, 'little')
        with self.assertRaises(mf.FlasherError):
            mf.inspect_image(self.write(bytes(wrong_chip)))
        no_desc = bytearray(fake_app())
        no_desc[32:36] = b'\0\0\0\0'
        with self.assertRaises(mf.FlasherError):
            mf.inspect_image(self.write(bytes(no_desc)))

    def test_old_image_without_identity(self):
        data = bytearray(fake_app(MERIDIANV.hardware_id.encode()))
        data[mf.IDENTITY_OFFSET:mf.IDENTITY_OFFSET + 8] = b'\0' * 8
        info = mf.inspect_image(self.write(bytes(data)))
        self.assertIsNone(info.version)
        self.assertIn('versión desconocida', info.describe())


class CommandTests(unittest.TestCase):
    def test_update_matches_platformio_addresses(self):
        command = mf.flash_command(['esptool.py'], '/dev/cu.x', 'app.bin', 'boot_app0.bin', full=False)
        self.assertEqual(command[:3], ['esptool.py', '--chip', 'esp32s3'])
        self.assertIn('write_flash', command)
        tail = command[command.index('4MB') + 1:]
        self.assertEqual(tail, ['0xe000', 'boot_app0.bin', '0x10000', 'app.bin'])

    def test_full_install_adds_bootloader_and_partitions(self):
        command = mf.flash_command(['esptool.py'], 'COM3', 'app.bin', 'boot.bin', True, 'bl.bin', 'pt.bin')
        tail = command[command.index('4MB') + 1:]
        self.assertEqual(tail, ['0x0', 'bl.bin', '0x8000', 'pt.bin', '0xe000', 'boot.bin', '0x10000', 'app.bin'])
        with self.assertRaises(mf.FlasherError):
            mf.flash_command(['esptool.py'], 'COM3', 'app.bin', 'boot.bin', True)

    def test_progress(self):
        self.assertEqual(mf.parse_progress('Writing at 0x0001c000... (12 %)'), 12)
        self.assertEqual(mf.parse_progress('Writing at 0x0001c000... (100%)'), 100)
        self.assertIsNone(mf.parse_progress('Hash of data verified.'))

    def test_status_model(self):
        self.assertEqual(mf.status_model({}), MERIDIANV)  # firmware viejo: MeridianV
        self.assertEqual(mf.status_model({'product': 'meridian3'}), MERIDIAN3)
        self.assertIsNone(mf.status_model({'product': 'otro'}))


@unittest.skipUnless((mf.BUILD / 'meridian3' / 'firmware-signed.bin').is_file()
                     and (mf.BUILD / 'esp32s3_usb' / 'firmware-signed.bin').is_file(),
                     'faltan las compilaciones: pio run -e esp32s3_usb y -e meridian3')
class RealBuildTests(unittest.TestCase):
    """Con las imágenes que deja `pio run`: cada una se reconoce como su modelo."""

    def test_real_images(self):
        for model in mf.MODELS:
            for name in ('firmware.bin', 'firmware-signed.bin'):
                info = mf.inspect_image(mf.BUILD / model.env / name)
                self.assertEqual(info.model, model, f'{model.env}/{name}')
                self.assertIsNotNone(info.version)
            signed = mf.inspect_image(mf.BUILD / model.env / 'firmware-signed.bin')
            self.assertTrue(signed.signed)
            self.assertEqual(signed.app, (mf.BUILD / model.env / 'firmware.bin').read_bytes())
            # Con openssl en la Mac, la firma se comprueba de verdad.
            self.assertIn(signed.signature_ok, (True, None), signed.signature_message)


if __name__ == '__main__':
    unittest.main()
