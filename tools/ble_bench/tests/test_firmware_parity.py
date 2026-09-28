"""Python y C++ dicen lo mismo, con las cabeceras del firmware compiladas de verdad.

Compila `tests/firmware_parity.cpp` contra `firmware/esp32/lib/*/src` y compara
su salida con el decodificador. Se salta solo si no hay compilador de C++.
"""
import os
import random
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from bench import protocol as p
from bench import rtcm

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
# Otra copia del firmware (p. ej. la rama del líder) con MERIDIAN_FIRMWARE_LIB=<…/firmware/esp32/lib>.
FIRMWARE_LIB = Path(os.environ.get("MERIDIAN_FIRMWARE_LIB", REPO / "firmware" / "esp32" / "lib"))
COMPILER = shutil.which("c++") or shutil.which("g++") or shutil.which("clang++")


def mixed_stream() -> bytes:
    """Tramas buenas, CRC roto, ruido con 0xD3, una cabecera inflada y cortes."""
    rng = random.Random(11)
    generator = rtcm.RtcmGenerator(seed=4)
    parts = []
    for index in range(4):
        for item in generator.epoch(index, index * 1000):
            frame = bytearray(item.frame)
            roll = rng.random()
            if roll < 0.15:
                frame[-1] ^= 0x40                       # CRC roto
            elif roll < 0.25:
                frame = frame[: len(frame) // 2]        # trama cortada
            parts.append(bytes(frame))
            if rng.random() < 0.2:
                parts.append(bytes(rng.choice((0xD3, 0x00, 0xFF, 0x3E)) for _ in range(rng.randint(1, 60))))
    parts.append(b"\xd3\x03\xff" + bytes(1500))           # longitud máxima con basura
    parts.append(generator.epoch(9, 9000)[0].frame)
    return b"".join(parts)


@unittest.skipIf(COMPILER is None, "no hay compilador de C++")
class FirmwareParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = dict(os.environ)
        if Path("/Applications/Xcode.app/Contents/Developer").is_dir():
            env.setdefault("DEVELOPER_DIR", "/Applications/Xcode.app/Contents/Developer")
        cls.tmp = tempfile.TemporaryDirectory()
        binary = Path(cls.tmp.name) / "parity"
        subprocess.run([COMPILER, "-std=c++17", "-O1", "-I", str(FIRMWARE_LIB / "protocol" / "src"),
                        "-I", str(FIRMWARE_LIB / "gnss" / "src"), "-o", str(binary),
                        str(HERE / "firmware_parity.cpp")], check=True, env=env, capture_output=True)
        cls.stream = mixed_stream()
        result = subprocess.run([str(binary)], input=cls.stream, capture_output=True, check=True)
        cls.lines = result.stdout.decode().splitlines()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def rows(self, tag):
        return [line.split(" ")[1:] for line in self.lines if line.startswith(tag + " ")]

    def test_response_frames(self):
        rows = self.rows("frames")
        self.assertEqual(len(rows), 20)
        for size, mtu, frames in rows:
            data = bytes(ord("a") + i % 26 for i in range(int(size)))
            ours = [f.hex() for f in p.encode_response_frames(0x1234, data, int(mtu))]
            self.assertEqual(ours, frames.rstrip(",").split(","), (size, mtu))

    def test_display_precision(self):
        rows = self.rows("display")
        self.assertGreater(len(rows), 300)
        for raw, h, v in rows:
            self.assertEqual(p.meridian_display_precision(int(raw)), (int(h), int(v)), raw)

    def test_sigma_to_mm(self):
        for meters, mm in self.rows("sigma"):
            self.assertEqual(p.sigma_to_mm(float(meters)), int(mm), meters)

    def test_health_packets(self):
        rows = self.rows("health")
        self.assertEqual(len(rows), 4)
        for h, v, age, source, quality, tracked, visible, packet in rows:
            inputs = p.HealthInputs(um980_raw_horizontal_sigma_mm=int(h), um980_raw_vertical_sigma_mm=int(v),
                                    meridian_display=p.meridian_display_precision(int(h)),
                                    correction_age_seconds=int(age), source=int(source), quality=int(quality),
                                    tracked=int(tracked), visible=int(visible))
            self.assertEqual(p.encode_health(inputs).hex(), packet)
            decoded = p.decode_health(bytes.fromhex(packet))
            self.assertEqual(decoded.quality, int(quality))

    def test_health_rtcm_counters(self):
        rows = self.rows("health_rtcm")
        self.assertEqual(len(rows), 3)
        for supported, discarded, rejected, percent, packet in rows:
            inputs = p.HealthInputs(has_rtcm_counters=supported == "1", rtcm_frames_discarded=int(discarded),
                                    rtcm_frames_rejected=int(rejected), rtcm_queue_percent=int(percent))
            self.assertEqual(p.encode_health(inputs).hex(), packet)
            if supported == "0":
                # Cabeceras anteriores al contrato v3: no hay nada que comparar.
                continue
            decoded = p.decode_health(bytes.fromhex(packet))
            self.assertEqual(decoded.rtcm_frames_discarded_mod256, int(discarded))

    def test_rtcm_parser_counts_the_same(self):
        (row,) = self.rows("rtcm")
        accepted, rejected, overflow, *lengths = (int(x) for x in row)
        parser = rtcm.Rtcm3Parser()
        frames = parser.feed(self.stream)
        self.assertEqual((parser.accepted, parser.rejected, parser.overflow), (accepted, rejected, overflow))
        self.assertEqual([len(f) for f in frames], lengths)
        self.assertGreater(rejected, 0)
        # `overflow` no sube nunca: una cabecera válida pide como mucho 1029
        # bytes, justo el tamaño del búfer, así que se resuelve antes de llenarlo
        # (rtcm3.h:25). Se compara igual, por si eso cambia.
        self.assertEqual(overflow, 0)


if __name__ == "__main__":
    unittest.main()
