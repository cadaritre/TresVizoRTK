"""Grabación, reproducción y resumen: sin radio y sin simulador."""
import json
import tempfile
import unittest
from pathlib import Path

from bench import protocol as p
from bench.analysis import Analyzer, analyze_events, extract_status, percentile
from bench.session import Event, Recorder, SessionFormatError, read_session, redact


class FakeClock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


class Redaction(unittest.TestCase):
    def test_secrets_never_written(self):
        value = {"ssid": "Obra", "password": "hunter2", "ntrip": {"mountpoint": "X", "pass": "abc",
                                                                   "credentials_persisted": False},
                 "list": [{"api_key": "k"}]}
        clean = redact(value)
        self.assertEqual(clean["password"], "[oculto]")
        self.assertEqual(clean["ntrip"]["pass"], "[oculto]")
        self.assertEqual(clean["list"][0]["api_key"], "[oculto]")
        self.assertIs(clean["ntrip"]["credentials_persisted"], False)
        self.assertEqual(clean["ssid"], "Obra")

    def test_recorder_redacts_on_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            recorder = Recorder(Path(tmp) / "s.jsonl", Path(tmp) / "e.csv", metadata={"token": "zzz"})
            recorder.record("status", snapshot={"password": "secreta"})
            recorder.close()
            text = (Path(tmp) / "s.jsonl").read_text() + (Path(tmp) / "e.csv").read_text()
            self.assertNotIn("secreta", text)
            self.assertNotIn("zzz", text)


class RecordAndReplay(unittest.TestCase):
    def test_replay_gives_the_same_summary(self):
        clock = FakeClock()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.jsonl"
            recorder = Recorder(path, Path(tmp) / "e.csv", clock=clock, metadata={"scenario": "prueba"})
            live = Analyzer()
            recorder.subscribe(live.consume)
            recorder.record("connected", mtu=185, ready_s=0.8)
            for sequence in (1, 2, 3, 6, 7):
                clock.t += 0.2
                recorder.record("notify", "solution", p.encode_solution(sequence, 5, 20, 1000, 19.4, -99.1, 2240.0))
            recorder.record("request", id=1, method="GET", path="/api/ble")
            clock.t += 0.05
            body = json.dumps({"id": 1, "status": 200, "body": {}}).encode()
            for frame in p.encode_response_frames(4, body, 185):
                recorder.record("notify", "response", frame)
            recorder.record("disconnected", expected=True)
            recorder.close()
            header, events = read_session(path)
            self.assertEqual(header["metadata"]["scenario"], "prueba")
            replayed = analyze_events(events)
            self.assertEqual(replayed.render(), live.render())
            self.assertEqual(replayed.solution_missing, 2)
            self.assertEqual(len(replayed.latencies_s), 1)
            self.assertAlmostEqual(replayed.latencies_s[0], 0.05, places=5)
            csv_lines = (Path(tmp) / "e.csv").read_text().splitlines()
            self.assertEqual(csv_lines[0], "t_monotonic_s,kind,characteristic,bytes,detail")
            self.assertEqual(len(csv_lines), 1 + 1 + 5 + 1 + 1 + 1)

    def test_rejects_foreign_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "otro.jsonl"
            path.write_text('{"format": "otra-cosa", "version": 1}\n')
            with self.assertRaises(SessionFormatError):
                read_session(path)


class Anonymize(unittest.TestCase):
    def test_networks_and_ips_are_masked_without_changing_framing(self):
        from bench.session import anonymize_events
        body = json.dumps({"id": 3, "status": 200, "body": {"wifi": {"ap_ssid": "TresVizo-C81D",
                          "station_ssid": "Casa de Carlos", "station_ip": "192.168.1.44"}, "firmware_version": "0.7.11"}})
        frames = p.encode_response_frames(9, body.encode(), 23)
        link = "TresVizo-C81D [6F1B-UUID] por Bluetooth"
        events = [Event(0.0, "connected", info={"link": link, "mtu": 247}),
                  Event(0.0, "note", info={"text": f"conectado: {link}; MTU 247"}),
                  Event(0.0, "request", info={"id": 3, "method": "GET", "path": "/api/status"})]
        events += [Event(0.1 + i * 0.01, "notify", "response", f) for i, f in enumerate(frames)]
        # Un mensaje con hueco también se tapa: se trabaja por desplazamiento.
        broken = p.encode_response_frames(10, body.encode(), 23)
        events += [Event(1.0 + i * 0.01, "notify", "response", f) for i, f in enumerate(broken) if i != 2]
        clean = anonymize_events(events)
        joined = b"".join(e.data[5:] for e in clean if e.data)
        for secret in (b"Casa", b"Carlos", b"C81D", b"192.168.1.44"):
            self.assertNotIn(secret, joined)
        self.assertEqual([len(e.data or b"") for e in clean], [len(e.data or b"") for e in events])
        # Mismo resumen salvo las notas, que llevan el nombre del equipo tapado.
        without_notes = lambda text: [l for l in text.splitlines() if not l.startswith("nota:")]  # noqa: E731,E741
        self.assertEqual(without_notes(analyze_events(clean).render()), without_notes(analyze_events(events).render()))
        self.assertIn(b"0.7.11", joined)
        self.assertNotIn("C81D", json.dumps([e.info for e in clean]))


class AnalyzerFacts(unittest.TestCase):
    def feed(self, analyzer, *events):
        for event in events:
            analyzer.consume(event)

    def test_percentiles(self):
        self.assertIsNone(percentile([], 50))
        self.assertEqual(percentile([3, 1, 2], 50), 2)
        self.assertEqual(percentile(list(range(1, 101)), 95), 95)

    def test_sequence_gap_resets_on_reconnect(self):
        a = Analyzer()
        solution = lambda s: p.encode_solution(s, 4, 20, 0, 1.0, 1.0, 1.0)  # noqa: E731
        self.feed(a, Event(0, "connected", info={}), Event(0.2, "notify", "solution", solution(10)),
                  Event(0.4, "notify", "solution", solution(12)), Event(0.5, "disconnected", info={"expected": False}),
                  Event(2.0, "connected", info={}), Event(2.2, "notify", "solution", solution(500)))
        self.assertEqual(a.solution_missing, 1)
        self.assertEqual(a.solution_anomalies, 0)
        self.assertEqual(a.disconnects_unexpected, 1)

    def test_quality_transitions(self):
        a = Analyzer()
        for t, quality in ((0.2, 1), (0.4, 5), (0.6, 5), (0.8, 4), (1.0, 5)):
            a.consume(Event(t, "notify", "solution", p.encode_solution(int(t * 5), quality, 20, 0, 1.0, 1.0, 1.0)))
        self.assertEqual([(a_, b) for _, a_, b in a.quality_transitions],
                         [("autónoma", "FLOTANTE"), ("FLOTANTE", "FIJO"), ("FIJO", "FLOTANTE")])
        self.assertIn("cambios de calidad: 3", a.render())

    def test_receiver_silent_is_said_plainly(self):
        a = Analyzer()
        silent = extract_status({"subsystems": {"gnss": {"accepted_gga": 0, "native_frames_valid": 0,
                                                         "state": "waiting_data"}, "ble": {}},
                                 "alerts": [{"code": "receiver_silent"}]})
        self.feed(a, Event(0, "status", info={"label": "inicio", "snapshot": silent}),
                  Event(10, "status", info={"label": "fin", "snapshot": silent}))
        self.assertTrue(a.receiver_silent())
        text = a.render()
        self.assertIn("0 bytes de telemetría del receptor", text)
        self.assertIn("No es un fallo de Bluetooth", text)

    def test_rtcm_ledger_balances(self):
        a = Analyzer()
        before = {"ble.rtcm_valid_frames": 10, "ble.rtcm_crc_errors": 0, "ble.rtcm_dropped_frames": 0,
                  "corrections.accepted_frames": 10, "corrections.rejected_frames": 0,
                  "gnss.correction_frames_sent": 10, "gnss.correction_frames_dropped": 0}
        after = dict(before, **{"ble.rtcm_valid_frames": 30, "corrections.accepted_frames": 30,
                                "gnss.correction_frames_sent": 27, "gnss.correction_frames_dropped": 1})
        self.feed(a, Event(0, "status", info={"snapshot": before}))
        for i in range(20):
            self.feed(a, Event(1 + i * 0.1, "rtcm_generated", info={"bytes": 300}),
                      Event(1 + i * 0.1, "rtcm_sent", info={"bytes": 300, "writes": 2, "mode": "sin respuesta"}))
        self.feed(a, Event(9, "status", info={"snapshot": after}))
        lines = "\n".join(a.reconcile_rtcm())
        self.assertIn("✔ enviadas = válidas", lines)
        self.assertIn("2 en cola", lines)

    def test_rtcm_loss_in_link_is_flagged(self):
        a = Analyzer()
        zero = {k: 0 for k in ("ble.rtcm_valid_frames", "ble.rtcm_crc_errors", "ble.rtcm_dropped_frames",
                               "corrections.accepted_frames", "corrections.rejected_frames",
                               "gnss.correction_frames_sent", "gnss.correction_frames_dropped")}
        self.feed(a, Event(0, "status", info={"snapshot": zero}))
        for i in range(5):
            self.feed(a, Event(1, "rtcm_sent", info={"bytes": 100}))
        self.feed(a, Event(2, "status", info={"snapshot": dict(zero, **{"ble.rtcm_valid_frames": 3,
                                                                       "ble.rtcm_crc_errors": 2})}))
        self.assertIn("✘ 2 tramas enviadas no llegaron válidas", "\n".join(a.reconcile_rtcm()))

    def test_device_restart_splits_the_counters(self):
        a = Analyzer()
        snap = lambda up, valid: {"uptime_ms": up, "ble.rtcm_valid_frames": valid}  # noqa: E731
        self.feed(a, Event(0, "status", info={"snapshot": snap(50_000, 100)}),
                  Event(60, "status", info={"snapshot": snap(3_000, 5)}),
                  Event(120, "status", info={"snapshot": snap(63_000, 65)}),
                  Event(61, "rtcm_sent", info={"bytes": 100}))
        self.assertEqual(a.device_restarts(), [60])
        self.assertEqual(a.status_delta()["ble.rtcm_valid_frames"], 60)
        self.assertIn("se reinició", "\n".join(a.reconcile_rtcm()))
        self.assertIn("⚠ el equipo se reinició 1", a.render())

    def test_uncorrelated_and_timeouts(self):
        a = Analyzer()
        body = json.dumps({"status": 400, "body": {"error": "invalid_request"}}).encode()
        self.feed(a, Event(0, "request", info={"id": 5, "method": "GET", "path": "/api/ble"}),
                  Event(5, "request_timeout", info={"id": 5}))
        for frame in p.encode_response_frames(1, body, 23):
            self.feed(a, Event(6, "notify", "response", frame))
        self.assertEqual(a.request_timeouts, 1)
        self.assertEqual(a.uncorrelated_responses, 1)
        self.assertEqual(a.responses_by_status, {400: 1})


if __name__ == "__main__":
    unittest.main()
