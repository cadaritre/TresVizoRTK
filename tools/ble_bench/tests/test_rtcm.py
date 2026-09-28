"""El rearmado RTCM3 de Python cuenta lo mismo que el del ESP32.

Vectores de `firmware/esp32/test/rtcm3_test.cpp`.
"""
from __future__ import annotations

import random
import unittest

from bench import rtcm


def smallest_packet() -> bytes:
    # rtcm3_test.cpp:5 — {0xd3, 0, 4, 0x3e, 0xd0, 0, 0} + CRC
    head = bytes((0xD3, 0, 4, 0x3E, 0xD0, 0, 0))
    return head + rtcm.crc24q_bitwise(head).to_bytes(3, "big")


class Crc(unittest.TestCase):
    def test_table_matches_bitwise(self):
        rng = random.Random(3)
        for size in (0, 1, 7, 100, 1026):
            data = bytes(rng.getrandbits(8) for _ in range(size))
            self.assertEqual(rtcm.crc24q(data), rtcm.crc24q_bitwise(data))

    def test_known_vector(self):
        # 1005 de 19 bytes publicado en ejemplos de RTCM (CRC conocido).
        self.assertEqual(rtcm.crc24q(b""), 0)
        self.assertEqual(rtcm.crc24q(b"123456789"), 0xCDE703)


class ParserMatchesFirmware(unittest.TestCase):
    def test_firmware_vectors(self):
        packet = bytearray(smallest_packet())
        parser = rtcm.Rtcm3Parser()
        self.assertEqual(len(parser.feed(packet)), 1)
        packet[-1] ^= 1
        self.assertEqual(parser.feed(packet), [])
        self.assertEqual(parser.rejected, 1)
        packet[-1] ^= 1
        self.assertEqual(len(parser.feed(packet)), 1)
        self.assertEqual(parser.feed(b"\xff" * 5000), [])
        self.assertEqual(len(parser.feed(packet)), 1)
        self.assertEqual(parser.accepted, 3)

    def test_resync_on_noise_with_preambles(self):
        noisy = rtcm.Rtcm3Parser()
        noisy.feed(b"\xd3\xff" * 40)
        self.assertEqual(len(noisy.feed(smallest_packet())), 1)

    def test_flooded_max_length_bad_crc(self):
        flooded = rtcm.Rtcm3Parser()
        flooded.feed(b"\xd3\x03\xff" + b"\x00" * 4000)
        self.assertEqual(len(flooded.feed(smallest_packet())), 1)
        self.assertGreaterEqual(flooded.overflow + flooded.rejected, 1)

    def test_split_anywhere(self):
        generator = rtcm.RtcmGenerator(seed=5)
        stream = b"".join(item.frame for item in generator.epoch(0, 0))
        for cut in (1, 2, 3, 19, 20, 181, 244):
            parser = rtcm.Rtcm3Parser()
            out = []
            for offset in range(0, len(stream), cut):
                out += parser.feed(stream[offset:offset + cut])
            self.assertEqual(b"".join(out), stream, cut)
            self.assertEqual(parser.rejected, 0)


class Generator(unittest.TestCase):
    def test_frames_are_valid_with_realistic_sizes(self):
        generator = rtcm.RtcmGenerator(seed=1)
        epoch = generator.epoch(0, 123_000)
        numbers = [item.number for item in epoch]
        self.assertEqual(numbers, [1005, 1033, 1230, 1077, 1087, 1097, 1127])
        for item in epoch:
            self.assertTrue(rtcm.frame_is_valid(item.frame), item.number)
        sizes = {item.number: len(item.frame) for item in epoch}
        self.assertEqual(sizes[1005], 25)          # 19 bytes de carga + 6
        self.assertTrue(200 < sizes[1077] < 400)    # 10 satélites × 2 señales, MSM7
        self.assertTrue(200 < sizes[1127] < 400)
        # Sin mensajes de estación la época ronda 1 kB: un flujo MSM7 real a 1 Hz.
        self.assertTrue(900 < generator.epoch_bytes() < 1300, generator.epoch_bytes())

    def test_msm4_is_smaller(self):
        msm4 = rtcm.RtcmGenerator(rtcm.EpochProfile(msm_kind=4)).epoch_bytes()
        msm7 = rtcm.RtcmGenerator(rtcm.EpochProfile(msm_kind=7)).epoch_bytes()
        self.assertLess(msm4, msm7)
        numbers = [item.number for item in rtcm.RtcmGenerator(rtcm.EpochProfile(msm_kind=4)).epoch(1, 0)]
        self.assertEqual(numbers, [1074, 1084, 1094, 1124])

    def test_same_seed_same_stream(self):
        a = [i.frame for i in rtcm.RtcmGenerator(seed=9).epoch(2, 0)]
        b = [i.frame for i in rtcm.RtcmGenerator(seed=9).epoch(2, 0)]
        self.assertEqual(a, b)

    def test_inert_message_number(self):
        generator = rtcm.RtcmGenerator(rtcm.EpochProfile(inert_message_number=4095))
        for item in generator.epoch(0, 0):
            self.assertEqual(item.number, 4095)
            self.assertTrue(rtcm.frame_is_valid(item.frame))

    def test_counters(self):
        generator = rtcm.RtcmGenerator()
        epoch = generator.epoch(0, 0)
        self.assertEqual(generator.frames_generated, len(epoch))
        self.assertEqual(generator.bytes_generated, sum(len(i.frame) for i in epoch))


class PacerRate(unittest.TestCase):
    def test_steady_rate(self):
        pacer = rtcm.Pacer(bytes_per_second=3000)
        sent = 0
        now = 0.0
        pacer.due_bytes(now)
        while now < 10.0:
            now += 0.01
            while pacer.due_bytes(now) >= 300:
                pacer.spend(300)
                sent += 300
        self.assertAlmostEqual(sent / 10.0, 3000, delta=150)

    def test_burst_holds_then_releases(self):
        pacer = rtcm.Pacer(bytes_per_second=1000, burst_seconds=2.0)
        self.assertAlmostEqual(pacer.due_bytes(0.0), 2000)
        pacer.spend(2000)
        self.assertEqual(pacer.due_bytes(1.0), 0)
        self.assertAlmostEqual(pacer.due_bytes(2.0), 2000)


if __name__ == "__main__":
    unittest.main()
