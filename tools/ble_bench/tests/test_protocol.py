"""El decodificador dice lo mismo que el firmware.

Los vectores son los de `firmware/esp32/test/ble_frames_test.cpp` y
`firmware/esp32/test/health_packet_test.cpp`: si una de las dos pruebas cambia,
la otra tiene que cambiar igual.
"""
from __future__ import annotations

import json
import math
import struct
import unittest

from bench import protocol as p


def round_trip(data: bytes, mtu: int, message_id: int) -> tuple[bytes, int]:
    """Trocea como ble_transport.cpp y rearma como la app (ble_frames_test.cpp:9)."""
    reassembler = p.ResponseReassembler(negotiated_mtu=mtu)
    frames = p.encode_response_frames(message_id, data, mtu)
    rebuilt = None
    for index, frame in enumerate(frames):
        assert len(frame) <= max(mtu, p.MINIMUM_ATT_MTU) - p.ATT_HEADER_BYTES
        assert len(frame) <= p.MAX_NOTIFICATION_BYTES
        parsed = p.parse_response_frame(frame)
        assert parsed.is_first == (index == 0)
        assert parsed.is_last == (index == len(frames) - 1)
        outcome = reassembler.feed(frame)[-1]
        if outcome.kind == "completed":
            rebuilt = outcome.message
    return rebuilt, len(frames)


class ResponseFramesMatchFirmware(unittest.TestCase):
    def test_payload_bytes_per_mtu(self):
        self.assertEqual(p.response_payload_bytes(23), 15)
        self.assertEqual(p.response_payload_bytes(0), 15)
        self.assertEqual(p.response_payload_bytes(185), 177)
        self.assertEqual(p.response_payload_bytes(247), 239)
        self.assertEqual(p.response_payload_bytes(517), 239)

    def test_byte_compatible_20_byte_frame(self):
        short = b'{"id":7,"status":200,"body":{}}'
        frame = p.encode_response_frame(0x0102, 15, short, 15)
        self.assertEqual(len(frame), 20)
        self.assertEqual(frame[:5], bytes((0x02, 0x01, 15, 0, 0)))
        self.assertEqual(frame[5:], short[15:30])

    def test_all_sizes_all_mtus(self):
        for size in (1, 15, 16, 239, 240, 2048, 2500, 4096):
            data = bytes(ord("a") + i % 26 for i in range(size))
            for mtu in (23, 185, 247, 517):
                rebuilt, frames = round_trip(data, mtu, 42)
                self.assertEqual(rebuilt, data, (size, mtu))
                per = p.response_payload_bytes(mtu)
                self.assertEqual(frames, (size + per - 1) // per)

    def test_2k_goes_from_134_to_9_frames(self):
        self.assertEqual(round_trip(b"x" * 2000, 23, 1)[1], 134)
        self.assertEqual(round_trip(b"x" * 2000, 247, 1)[1], 9)


class ReassemblerAnomalies(unittest.TestCase):
    def setUp(self):
        self.data = json.dumps({"id": 9, "status": 200, "body": {"x": "y" * 80}}).encode()
        self.frames = p.encode_response_frames(7, self.data, 23)
        self.assertGreater(len(self.frames), 4)

    def feed_all(self, reassembler, frames, now=0.0):
        kinds = []
        for frame in frames:
            kinds += [o.kind for o in reassembler.feed(frame, now)]
        return kinds

    def test_gap_discards_message(self):
        r = p.ResponseReassembler()
        kinds = self.feed_all(r, self.frames[:2] + self.frames[3:])
        self.assertIn("gap", kinds)
        self.assertNotIn("completed", kinds)
        self.assertEqual(r.counts["gap"], 1)

    def test_duplicate_is_classified_and_message_survives(self):
        r = p.ResponseReassembler()
        frames = self.frames[:3] + [self.frames[2]] + self.frames[3:]
        kinds = self.feed_all(r, frames)
        self.assertEqual(r.counts["duplicate"], 1)
        self.assertEqual(kinds[-1], "completed")

    def test_duplicate_after_completion(self):
        r = p.ResponseReassembler()
        self.feed_all(r, self.frames)
        kinds = self.feed_all(r, [self.frames[-1], self.frames[0]])
        self.assertEqual(kinds, ["duplicate", "duplicate"])
        self.assertEqual(r.counts["completed"], 1)

    def test_single_frame_message_repeated_is_not_completed_twice(self):
        r = p.ResponseReassembler()
        frame = p.encode_response_frames(3, b'{"id":1}', 247)
        self.assertEqual(len(frame), 1)
        kinds = self.feed_all(r, frame + frame)
        self.assertEqual(kinds, ["completed", "duplicate"])

    def test_swapped_frames_are_out_of_order_not_loss(self):
        r = p.ResponseReassembler()
        frames = self.frames[:2] + [self.frames[3], self.frames[2]] + self.frames[4:]
        kinds = self.feed_all(r, frames)
        self.assertEqual(r.counts["gap"], 1)
        self.assertEqual(r.counts["out_of_order"], 1)
        self.assertNotIn("completed", kinds)

    def test_orphan_without_first_frame(self):
        r = p.ResponseReassembler()
        kinds = self.feed_all(r, self.frames[1:2])
        self.assertEqual(kinds, ["orphan"])

    def test_invalid_lengths(self):
        r = p.ResponseReassembler(negotiated_mtu=23)
        self.assertEqual(r.feed(b"\x01\x00\x00")[0].kind, "invalid_length")
        too_long = p.encode_response_frames(5, b"z" * 300, 247)[0]
        self.assertEqual(r.feed(too_long)[0].kind, "invalid_length")
        first_with_offset = struct.pack("<HHB", 6, 10, p.FIRST_FRAME_FLAG) + b"abc"
        self.assertEqual(r.feed(first_with_offset)[0].kind, "invalid_length")

    def test_too_large(self):
        r = p.ResponseReassembler()
        frames = p.encode_response_frames(8, b"q" * 5000, 247)
        kinds = self.feed_all(r, frames)
        self.assertIn("too_large", kinds)
        self.assertNotIn("completed", kinds)

    def test_restart_and_expiry(self):
        r = p.ResponseReassembler()
        self.feed_all(r, self.frames[:2], now=0.0)
        other = p.encode_response_frames(7, b'{"otra":1}', 23)
        kinds = self.feed_all(r, other, now=1.0)
        self.assertEqual(r.counts["restarted"], 1)
        self.assertEqual(kinds[-1], "completed")
        self.feed_all(r, self.frames[:1], now=2.0)
        kinds = [o.kind for o in r.feed(p.encode_response_frames(9, b"{}", 23)[0], now=8.0)]
        self.assertEqual(kinds[0], "expired")

    def test_reset_forgets_everything(self):
        r = p.ResponseReassembler()
        self.feed_all(r, self.frames[:2])
        r.reset()
        self.assertEqual(r.pending_messages, 0)
        self.assertEqual(self.feed_all(r, self.frames[2:3]), ["orphan"])


class SolutionPacket(unittest.TestCase):
    def test_round_trip_and_unknowns(self):
        raw = p.encode_solution(65535, 4, 23, 43_200_123, 19.4326077, -99.1332080, 2240.512)
        s = p.decode_solution(raw)
        self.assertEqual((s.sequence, s.quality, s.satellites_used, s.utc_time_of_day_ms), (65535, 4, 23, 43_200_123))
        self.assertAlmostEqual(s.latitude_degrees, 19.4326077, places=7)
        self.assertAlmostEqual(s.longitude_degrees, -99.1332080, places=7)
        self.assertAlmostEqual(s.height_msl_meters, 2240.512, places=3)
        self.assertEqual(s.quality_name, "FIJO")
        unknown = p.decode_solution(p.encode_solution(1, 0, None, 0, None, None, None))
        self.assertIsNone(unknown.satellites_used)
        self.assertIsNone(unknown.latitude_degrees)
        self.assertIsNone(unknown.height_msl_meters)

    def test_wrong_length_is_rejected(self):
        with self.assertRaises(p.ProtocolError):
            p.decode_solution(b"\x00" * 19)

    def test_sequence_gap_with_wraparound(self):
        self.assertEqual(p.sequence_gap(10, 11), 0)
        self.assertEqual(p.sequence_gap(10, 14), 3)
        self.assertEqual(p.sequence_gap(65535, 0), 0)
        self.assertEqual(p.sequence_gap(65534, 1), 2)
        self.assertLess(p.sequence_gap(10, 10), 0)
        self.assertLess(p.sequence_gap(500, 3), 0)  # el equipo se reinició


class HealthMatchesFirmware(unittest.TestCase):
    """Vectores de health_packet_test.cpp."""

    def test_display_rule(self):
        for raw, h, v in ((0, 10, 15), (10, 10, 15), (30, 10, 15), (35, 10, 15), (36, 11, 16), (39, 14, 19),
                          (50, 25, 30), (80, 55, 60), (100, 75, 80), (0xFFFF, 0xFFFF, 0xFFFF),
                          (65534, 65509, 65514)):
            self.assertEqual(p.meridian_display_precision(raw), (h, v), raw)

    def test_sigma_to_mm(self):
        self.assertEqual(p.sigma_to_mm(0.028), 28)
        self.assertEqual(p.sigma_to_mm(0.0355), 36)
        self.assertEqual(p.sigma_to_mm(-1), p.UNKNOWN_U16)
        self.assertEqual(p.sigma_to_mm(70.0), p.UNKNOWN_U16)

    def test_worst_axis(self):
        self.assertEqual(p.worst_axis_horizontal_sigma_meters(0.011, 0.010, 0.015), 0.011)
        self.assertEqual(p.worst_axis_horizontal_sigma_meters(math.nan, 0.010, 0.015), 0.015)

    def test_encode_decode_like_firmware(self):
        inputs = p.HealthInputs(um980_raw_horizontal_sigma_mm=12, um980_raw_vertical_sigma_mm=39,
                                meridian_display=p.meridian_display_precision(12), correction_age_seconds=1,
                                source=2, quality=4, tracked=31, visible=39)
        report = p.encode_health(inputs)
        self.assertEqual(len(report), 20)
        self.assertEqual(report[0], 1)
        self.assertEqual(struct.unpack_from("<HH", report, 1), (10, 15))
        self.assertEqual(struct.unpack_from("<HH", report, 12), (12, 39))
        self.assertEqual(report[9], 0)
        self.assertEqual(report[11], 39)
        self.assertEqual(report[16], p.HEALTH_FLAG_DISPLAY_PRECISION | p.HEALTH_FLAG_RAW_PRECISION)
        self.assertEqual(report[17:20], b"\x00\x00\x00")
        h = p.decode_health(report)
        self.assertEqual((h.display_horizontal_precision_mm, h.display_vertical_precision_mm), (10, 15))
        self.assertEqual((h.raw_horizontal_sigma_mm, h.raw_vertical_sigma_mm), (12, 39))
        self.assertEqual((h.correction_age_seconds, h.correction_source_name, h.quality), (1, "NTRIP", 4))
        self.assertEqual((h.satellites_tracked, h.satellites_visible), (31, 39))
        self.assertTrue(h.bytes_1_to_4_are_display_precision and h.has_raw_precision)
        self.assertFalse(h.has_rtcm_counters)
        self.assertIsNone(h.rtcm_queue_percent)

    def test_unknowns_are_none_not_zero(self):
        h = p.decode_health(p.encode_health(p.HealthInputs()))
        self.assertIsNone(h.satellites_visible)
        self.assertIsNone(h.display_horizontal_precision_mm)
        self.assertIsNone(h.raw_horizontal_sigma_mm)
        self.assertIsNone(h.correction_age_seconds)

    def test_rtcm_counters_v3(self):
        # Vectores de health_packet_test.cpp en 0.7.11 (contrato v3).
        report = p.encode_health(p.HealthInputs(has_rtcm_counters=True, rtcm_frames_discarded=300,
                                                rtcm_frames_rejected=3,
                                                rtcm_queue_percent=p.queue_percent(4100, 8192)))
        self.assertEqual(report[16], p.HEALTH_FLAG_DISPLAY_PRECISION | p.HEALTH_FLAG_RAW_PRECISION
                         | p.HEALTH_FLAG_RTCM_COUNTERS)
        self.assertEqual(tuple(report[17:20]), (44, 3, 51))
        h = p.decode_health(report)
        self.assertTrue(h.has_rtcm_counters)
        self.assertEqual((h.rtcm_frames_discarded_mod256, h.rtcm_frames_rejected_mod256, h.rtcm_queue_percent),
                         (44, 3, 51))
        self.assertEqual(p.queue_percent(0, 8192), 0)
        self.assertEqual(p.queue_percent(1, 8192), 1)
        self.assertEqual(p.queue_percent(8192, 8192), 100)
        self.assertEqual(p.queue_percent(10, 0), p.UNKNOWN_PERCENT)
        unknown = p.decode_health(p.encode_health(p.HealthInputs(has_rtcm_counters=True)))
        self.assertIsNone(unknown.rtcm_queue_percent)
        self.assertEqual(p.counter_delta_mod256(250, 4), 10)
        self.assertEqual(p.counter_delta_mod256(7, 7), 0)

    def test_bytes_17_19_ignored_without_flag(self):
        report = bytearray(p.encode_health(p.HealthInputs()))
        report[17:20] = b"\x01\x02\x03"
        h = p.decode_health(bytes(report))
        self.assertFalse(h.has_rtcm_counters)
        self.assertIsNone(h.rtcm_frames_discarded_mod256)
        self.assertEqual(h.extension_bytes, b"\x01\x02\x03")

    def test_bad_version_and_length(self):
        with self.assertRaises(p.ProtocolError):
            p.decode_health(b"\x02" + b"\x00" * 19)
        with self.assertRaises(p.ProtocolError):
            p.decode_health(b"\x01" * 21)


class Requests(unittest.TestCase):
    def test_request_line_and_chunks(self):
        line = p.encode_request(5, "GET", "/api/ble")
        self.assertTrue(line.endswith(b"\n"))
        self.assertEqual(json.loads(line), {"id": 5, "method": "GET", "path": "/api/ble"})
        chunks = p.chunk_for_write(line, 23)
        self.assertTrue(all(len(c) <= 20 for c in chunks))
        self.assertEqual(b"".join(chunks), line)
        self.assertEqual(len(p.chunk_for_write(line, 247)), 1)

    def test_request_too_long(self):
        with self.assertRaises(p.ProtocolError):
            p.encode_request(1, "PUT", "/api/config", {"x": "y" * 1100})


if __name__ == "__main__":
    unittest.main()
