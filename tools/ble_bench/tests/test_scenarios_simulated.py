"""Los escenarios del banco corren contra el simulador y el resumen dice lo esperado.

No prueba el equipo: prueba que el banco mide bien, para que mañana lo que
diga contra el Meridian V sea creíble.
"""
import asyncio
import tempfile
import unittest
from pathlib import Path

from bench import protocol as p
from bench.link import LinkError
from bench.runner import Bench
from bench.scenarios import SCENARIOS, ScenarioOptions
from bench.session import Recorder, read_session
from bench.analysis import analyze_events
from bench.simulator import SimulatedLink, SimulatedMeridian, SimulatorOptions
from bench import scenarios


def setUpModule():
    # Pausas cortas: el simulador vacía su cola al instante y no hay radio que esperar.
    scenarios.DRAIN_AFTER_STREAM_S = 0.3
    scenarios.PAUSE_BEFORE_RECONNECT_S = 0.1


def run(scenario: str, sim: SimulatorOptions | None = None, **options) -> tuple[Bench, Path, tempfile.TemporaryDirectory]:
    tmp = tempfile.TemporaryDirectory()
    device = SimulatedMeridian(sim or SimulatorOptions())
    recorder = Recorder(Path(tmp.name) / "s.jsonl", Path(tmp.name) / "e.csv", metadata={"scenario": scenario})
    bench = Bench(lambda: SimulatedLink(device), recorder, allow_mutations=options.get("select_ble_source", False))
    values = dict(SCENARIOS[scenario].defaults)
    values.update(options)
    asyncio.run(SCENARIOS[scenario].run(bench, ScenarioOptions(**values)))
    recorder.close()
    bench.device = device
    return bench, Path(tmp.name) / "s.jsonl", tmp


class Scenarios(unittest.TestCase):
    def test_telemetry_only_rates(self):
        bench, _, tmp = run("telemetria", duration_s=2.2)
        a = bench.analyzer
        self.assertLessEqual(a.streams["solution"].rate_hz(), p.MAX_SOLUTION_RATE_HZ + 0.3)
        self.assertGreaterEqual(a.streams["health"].count, 1)
        self.assertEqual(a.solution_missing, 0)
        tmp.cleanup()

    def test_silent_receiver_is_not_blamed_on_bluetooth(self):
        # Contrato v3: la salud sigue llegando (latido) aunque el UM980 esté mudo.
        bench, _, tmp = run("telemetria", SimulatorOptions(receiver_talking=False), duration_s=2.2)
        a = bench.analyzer
        self.assertNotIn("solution", a.streams)
        self.assertGreaterEqual(a.streams["health"].count, 2)
        self.assertIsNone(a.last_health.satellites_tracked)
        self.assertTrue(a.receiver_silent())
        self.assertIn("No es un fallo de Bluetooth", a.render())
        tmp.cleanup()

    def test_silent_receiver_with_firmware_v2_sends_nothing(self):
        # Hasta 0.7.10 la salud solo salía detrás de una solución (ble_transport.cpp:233).
        bench, _, tmp = run("telemetria", SimulatorOptions(receiver_talking=False, protocol_version=2),
                            duration_s=1.5)
        a = bench.analyzer
        self.assertNotIn("solution", a.streams)
        self.assertNotIn("health", a.streams)
        self.assertIn("No es un fallo de Bluetooth", a.render())
        tmp.cleanup()

    def test_stale_gatt_table_is_named(self):
        bench, _, tmp = run("telemetria", SimulatorOptions(stale_gatt=True), duration_s=1.2)
        a = bench.analyzer
        self.assertNotIn("health", a.streams)
        self.assertEqual(bench.rtcm_mode, "con respuesta")
        text = a.render()
        self.assertIn("tabla GATT en caché", text)
        self.assertIn("a04c0006", text)
        self.assertIn("escritura sin respuesta", text)
        tmp.cleanup()

    def test_rtcm_uses_write_without_response_when_announced(self):
        bench, _, tmp = run("rtcm-3k", duration_s=1.5, select_ble_source=True)
        a = bench.analyzer
        self.assertEqual(a.rtcm_write_modes, {"sin respuesta"})
        self.assertIn("✔ enviadas = válidas", "\n".join(a.reconcile_rtcm()))
        self.assertEqual(a.status_delta()["ble.rtcm_valid_frames"], a.rtcm_sent_frames)
        tmp.cleanup()

    def test_rtcm_falls_back_to_write_with_response(self):
        bench, _, tmp = run("rtcm-1k", SimulatorOptions(write_without_response=False), duration_s=1.5,
                            select_ble_source=True)
        self.assertEqual(bench.analyzer.rtcm_write_modes, {"con respuesta"})
        self.assertGreater(bench.analyzer.rtcm_sent_frames, 0)
        tmp.cleanup()

    def test_without_ble_source_every_frame_is_refused_and_said(self):
        bench, _, tmp = run("rtcm-1k", duration_s=1.2)
        lines = "\n".join(bench.analyzer.reconcile_rtcm())
        self.assertIn("la fuente activa no es BLE", lines)
        self.assertIn("--select-ble-source", "\n".join(bench.analyzer.notes))
        tmp.cleanup()

    def test_mutation_needs_explicit_permission(self):
        async def attempt():
            device = SimulatedMeridian()
            with tempfile.TemporaryDirectory() as tmp:
                recorder = Recorder(Path(tmp) / "s.jsonl")
                bench = Bench(lambda: SimulatedLink(device), recorder)
                await bench.connect()
                with self.assertRaises(PermissionError):
                    await bench.request("PUT", "/api/corrections/source", {"source": "ble"})
                with self.assertRaises(PermissionError):
                    await bench.request("POST", "/api/restart")
                await bench.disconnect()
                recorder.close()
        asyncio.run(attempt())

    def test_commands_during_rtcm_have_latencies(self):
        bench, _, tmp = run("rtcm-ordenes", duration_s=2.5, command_period_s=0.4, rate_bytes_per_second=6000,
                            select_ble_source=True)
        a = bench.analyzer
        self.assertGreaterEqual(len(a.latency_by_path["GET /api/ble"]), 4)
        self.assertEqual(a.request_timeouts, 0)
        self.assertEqual(a.uncorrelated_responses, 0)
        tmp.cleanup()

    def test_saturation_is_counted_not_hidden(self):
        # Más de lo que saca la UART (11.5 kB/s) durante más de lo que cabe en 8 KiB.
        bench, _, tmp = run("saturacion", duration_s=2.0, rate_bytes_per_second=25000, command_period_s=0.5,
                            select_ble_source=True)
        a = bench.analyzer
        delta = a.status_delta()
        self.assertGreater(delta["gnss.correction_frames_evicted"], 0)
        self.assertEqual(delta["ble.rtcm_valid_frames"], a.rtcm_sent_frames)
        self.assertEqual(a.request_timeouts, 0)
        lines = "\n".join(a.reconcile_rtcm())
        self.assertIn("✔ aceptadas = escritas al UM980 + desalojadas + caducadas", lines)
        self.assertGreater(a.health_rtcm_discarded, 0)
        tmp.cleanup()

    def test_saturation_with_firmware_v2(self):
        bench, _, tmp = run("saturacion", SimulatorOptions(protocol_version=2), duration_s=1.5,
                            command_period_s=0.5, select_ble_source=True)
        # v2: sin escritura sin respuesta y cuadre con la fórmula de antes (cola de 4 tramas).
        self.assertEqual(bench.analyzer.rtcm_write_modes, {"con respuesta"})
        self.assertIsNone(bench.analyzer.status_delta()["gnss.correction_frames_evicted"])
        self.assertIn("+ descartadas +", "\n".join(bench.analyzer.reconcile_rtcm()))
        tmp.cleanup()

    def test_disconnect_during_rtcm_resends_nothing_old(self):
        bench, _, tmp = run("corte-rtcm", duration_s=2.0, select_ble_source=True)
        a = bench.analyzer
        self.assertEqual(a.connects, 2)
        self.assertEqual(a.disconnects_expected, 2)
        self.assertLessEqual(a.status_delta()["ble.rtcm_crc_errors"], 1)
        tmp.cleanup()

    def test_disconnect_during_command(self):
        bench, _, tmp = run("corte-orden", cycles=2)
        a = bench.analyzer
        self.assertEqual(a.requests_cancelled, 2)
        # Una GET /api/ble por conexión (como las apps) y otra tras cada corte.
        self.assertEqual(len(a.latency_by_path["GET /api/ble"]), a.connects + 2)
        self.assertEqual(a.reassembler.counts["orphan"], 0)
        tmp.cleanup()

    def test_reconnect_cycles(self):
        bench, _, tmp = run("reconexiones", cycles=3)
        a = bench.analyzer
        self.assertEqual(a.connects, 3)
        self.assertEqual(len(a.latency_by_path["GET /api/ble"]), 2 * 3)
        tmp.cleanup()

    def test_malformed_rtcm_and_command(self):
        bench, _, tmp = run("malformados", duration_s=2.0, rate_bytes_per_second=3000, select_ble_source=True)
        a = bench.analyzer
        delta = a.status_delta()
        self.assertGreater(delta["ble.rtcm_crc_errors"], 0)
        self.assertGreater(delta["corrections.accepted_frames"], 0)
        self.assertEqual(a.uncorrelated_responses, 1)
        self.assertEqual(a.responses_by_status.get(400), 1)
        tmp.cleanup()

    def test_response_frame_loss_is_reported_as_gap(self):
        bench, _, tmp = run("rtcm-ordenes", SimulatorOptions(response_frame_drop_probability=0.3, seed=3),
                            duration_s=2.5, command_period_s=0.3, rate_bytes_per_second=1000)
        a = bench.analyzer
        lost = a.reassembler.counts["gap"] + a.reassembler.counts["orphan"] + a.reassembler.counts["expired"]
        self.assertGreater(lost + a.request_timeouts, 0)
        tmp.cleanup()

    def test_unexpected_drop_is_distinguished(self):
        async def scenario():
            device = SimulatedMeridian()
            with tempfile.TemporaryDirectory() as tmp:
                recorder = Recorder(Path(tmp) / "s.jsonl")
                bench = Bench(lambda: SimulatedLink(device), recorder)
                await bench.connect()
                await bench.link.drop()
                with self.assertRaises(LinkError):
                    await bench.request("GET", "/api/ble")
                recorder.close()
                return bench
        bench = asyncio.run(scenario())
        self.assertEqual(bench.analyzer.disconnects_unexpected, 1)
        self.assertEqual(bench.analyzer.disconnects_expected, 0)

    def test_replay_of_a_simulated_run_matches_live(self):
        bench, path, tmp = run("rtcm-ordenes", duration_s=1.5, command_period_s=0.5, select_ble_source=True)
        _, events = read_session(path)
        self.assertEqual(analyze_events(events).render(), bench.analyzer.render())
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
