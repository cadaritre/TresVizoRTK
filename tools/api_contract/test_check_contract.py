#!/usr/bin/env python3
"""Pruebas del comprobador del contrato firmware ↔ apps.

    python3 -m unittest discover -s tools/api_contract -v
"""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import check_contract as cc  # noqa: E402

FIXTURE = HERE / "fixtures" / "device_0.8.0_from_source.json"
SCRIPT = HERE / "check_contract.py"


def load_fixture():
    with open(FIXTURE, encoding="utf-8") as handle:
        return json.load(handle)


class MutatedFirmware:
    """Copia temporal de `src`, `include` y `lib` con cambios de texto."""

    def __init__(self, edits):
        self.edits = edits

    def __enter__(self) -> Path:
        self.directory = tempfile.TemporaryDirectory(prefix="api_contract_")
        root = Path(self.directory.name) / "esp32"
        for folder in cc.SOURCE_DIRS:
            shutil.copytree(cc.DEFAULT_FIRMWARE / folder, root / folder)
        for relative, old, new in self.edits:
            path = root / relative
            text = path.read_text(encoding="utf-8")
            if old not in text:
                raise AssertionError(f"La prueba ya no aplica: no está «{old}» en {relative}.")
            path.write_text(text.replace(old, new), encoding="utf-8")
        return root

    def __exit__(self, *_):
        self.directory.cleanup()


class ScannerTests(unittest.TestCase):
    def test_comments_do_not_count_and_urls_survive(self):
        tokens = cc.scan_cpp('a["x"] = 1; // b["y"] = 2;\n/* c["z"] = 3; */ d = "http://h//p";')
        strings = [t.text for t in tokens if t.kind == "str"]
        self.assertEqual(strings, ["x", "http://h//p"])

    def test_escapes_and_char_literals(self):
        tokens = cc.scan_cpp('s = "a\\"b"; c = \'"\'; n = 1\'000; t = "k";')
        self.assertEqual([t.text for t in tokens if t.kind == "str"], ['a\\"b', "k"])

    def test_write_versus_read(self):
        with tempfile.TemporaryDirectory() as folder:
            src = Path(folder) / "src"
            src.mkdir()
            (src / "a.cpp").write_text(
                'void status(JsonObject out) {\n'
                '  out["written"] = 1;\n'
                '  out["parent"]["child"] = 2;\n'
                '  out["made"].to<JsonArray>();\n'
                '  helper(out["handed"].as<JsonObject>());\n'
                '  for (const char* k : {"listed", "too"}) out[k] = 0;\n'
                '}\n'
                'int request(JsonVariantConst body) {\n'
                '  if (body["read"] == 1 || body["other"] != 2) return 1;\n'
                '  int v = doc["defaulted"] | 0; bool b = body["typed"].is<int>();\n'
                '  status(out);\n'
                '  return 0;\n'
                '}\n', encoding="utf-8")
            index = cc.FirmwareIndex(Path(folder))
            for key in ("written", "parent", "child", "made", "handed", "listed", "too"):
                self.assertTrue(index.key_evidence(key, ["src/a.cpp"]), key)
            for key in ("read", "other", "defaulted", "typed"):
                self.assertFalse(index.key_evidence(key, ["src/a.cpp"]), key)
                self.assertTrue(index.literal_evidence(key, ["src/a.cpp"]), key)
            # Por función: la llamada `status(out);` no es una definición.
            self.assertEqual(len(index.resolve(["src/a.cpp#status"])), 1)
            self.assertTrue(index.key_evidence("written", ["src/a.cpp#status"]))
            self.assertFalse(index.key_evidence("written", ["src/a.cpp#request"]))
            self.assertFalse(index.has_source("src/a.cpp#missing"))

    def test_values_at(self):
        body = {"a": {"b": 1}, "n": None, "list": [{"k": 1}, {"j": 2}], "empty": []}
        self.assertEqual(cc.values_at(body, cc.parse_key_path("a.b")), [1])
        self.assertEqual(cc.values_at(body, cc.parse_key_path("a.c")), [cc._ABSENT])
        self.assertEqual(cc.values_at(body, cc.parse_key_path("n.x")), [])          # contenedor nulo
        self.assertEqual(cc.values_at(body, cc.parse_key_path("missing.x")), [])    # contenedor ausente
        self.assertEqual(cc.values_at(body, cc.parse_key_path("list[].k")), [1, cc._ABSENT])
        self.assertEqual(cc.values_at(body, cc.parse_key_path("empty[].k")), [])


class StaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = cc.load_contract(cc.DEFAULT_CONTRACT)
        cls.firmware = cc.FirmwareIndex(cc.DEFAULT_FIRMWARE)

    def check(self, firmware_root: Path) -> cc.Report:
        return cc.check_static(self.contract, cc.FirmwareIndex(firmware_root))

    def assertBroken(self, report: cc.Report, *needles):
        self.assertFalse(report.ok, "la comprobación debía fallar")
        text = "\n".join(report.errors)
        for needle in needles:
            self.assertIn(needle, text)

    def test_contract_is_well_formed(self):
        self.assertEqual(cc.validate_contract(self.contract), [])

    def test_contract_covers_both_apps(self):
        apps = {app for route in self.contract["routes"] for entry in route["response"] for app in entry["apps"]}
        self.assertEqual(apps, {"ios", "android"})
        names = {item["name"] for item in self.contract["identifiers"]}
        self.assertTrue({"hardware_id", "board", "firmware_version", "device_name", "ap_ssid"} <= names)

    def test_real_tree_passes(self):
        report = cc.check_static(self.contract, self.firmware)
        self.assertEqual(report.errors, [])
        self.assertGreater(report.checked, 500)

    def test_removed_hardware_id_fails_and_is_named(self):
        edit = ("src/firmware_update.cpp", 'out["hardware_id"] = hardware;', "")
        with MutatedFirmware([edit]) as root:
            report = self.check(root)
        self.assertBroken(report, "GET /api/update", "«hardware_id»", "src/firmware_update.cpp#status")
        # /api/status la sigue escribiendo en instrument.cpp; y la lectura de
        # `body["hardware_id"]` en begin no cuenta como escritura.
        self.assertFalse(any("GET /api/status" in line for line in report.errors))
        self.assertEqual(len(report.errors), 1)

    def test_commented_key_does_not_count(self):
        edit = ("src/firmware_update.cpp", 'out["hardware_id"] = hardware;', '/* out["hardware_id"] = hardware; */')
        with MutatedFirmware([edit]) as root:
            self.assertBroken(self.check(root), "«hardware_id»")

    def test_renamed_key_fails(self):
        edit = ("src/instrument.cpp", 'response["firmware_version"] = kVersion;', 'response["fw_version"] = kVersion;')
        with MutatedFirmware([edit]) as root:
            self.assertBroken(self.check(root), "GET /api/status", "«firmware_version»")

    def test_nested_key_in_other_module_fails(self):
        edit = ("src/ble_transport.cpp", 'out["protocol_version"] = 3;', 'out["ble_version"] = 3;')
        with MutatedFirmware([edit]) as root:
            report = self.check(root)
        self.assertBroken(report, "«subsystems.ble.protocol_version»", "POST /api/ble", "protocol_version de BLE")

    def test_removed_route_fails(self):
        edit = ("src/sd_recorder.cpp", '"/api/recording/sessions"', '"/api/recording/list"')
        with MutatedFirmware([edit]) as root:
            self.assertBroken(self.check(root), "GET /api/recording/sessions: la ruta ya no aparece")

    def test_moved_function_is_reported(self):
        edit = ("src/ntrip_input.cpp", "void profilesJson(JsonObject out){", "void profileList(JsonObject out){")
        with MutatedFirmware([edit]) as root:
            self.assertBroken(self.check(root), "GET /api/ntrip/profiles", "src/ntrip_input.cpp#profilesJson")

    def test_request_key_no_longer_read_fails(self):
        edit = ("src/firmware_update.cpp", '"sha256"', '"digest"')
        with MutatedFirmware([edit]) as root:
            self.assertBroken(self.check(root), "POST /api/update/begin", "«sha256»")

    def test_literal_of_wrong_type_fails(self):
        edits = [("src/ble_transport.cpp", 'out["protocol_version"] = 3;', 'out["protocol_version"] = "3";'),
                 ("src/firmware_update.cpp", 'out["signature_required"] = true;', 'out["signature_required"] = "yes";')]
        with MutatedFirmware(edits) as root:
            self.assertBroken(self.check(root),
                              "«subsystems.ble.protocol_version» se escribe como string",
                              "«signature_required» se escribe como string")

    def test_binary_layout_changes_fail(self):
        edits = [("lib/protocol/src/health_packet.h", "report[0] = 1;", "report[0] = 2;"),
                 ("src/ble_transport.cpp", 'out["protocol_version"] = 3;', 'out["protocol_version"] = 2;'),
                 ("src/telemetry_ws.cpp", "kHealth = 0x02;", "kHealth = 0x03;")]
        with MutatedFirmware(edits) as root:
            self.assertBroken(self.check(root), "Salud: versión 1 en byte 0", "por debajo de 3",
                              "WebSocket: tipo 0x02 = salud")


class DeviceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = cc.load_contract(cc.DEFAULT_CONTRACT)
        cls.recorded = load_fixture()

    def run_device(self, recorded, ble_size=False) -> cc.Report:
        # El tamaño por BLE se prueba aparte: con la fixture, /api/status no cabe.
        return cc.check_device(self.contract, cc.ReplayInstrument(recorded), ble_size=ble_size)

    def mutated(self, route, change):
        recorded = copy.deepcopy(self.recorded)
        change(recorded[route]["body"])
        return self.run_device(recorded)

    def test_fixture_covers_every_device_route(self):
        wanted = {cc.route_label(r) for r in cc.device_routes(self.contract)}
        self.assertEqual(wanted - set(self.recorded), set())

    def test_fixture_keys_and_types_pass(self):
        report = self.run_device(self.recorded)
        self.assertEqual(report.errors, [])
        self.assertEqual(report.warnings, [])

    def test_fixture_status_does_not_fit_ble(self):
        # Discrepancia anotada en el contrato: con todo lo que escribe 0.8.0,
        # /api/status pasa de 4096 bytes y por BLE el equipo contesta 413.
        report = self.run_device(self.recorded, ble_size=True)
        self.assertEqual(len(report.errors), 1, report.errors)
        self.assertIn("GET /api/status: por BLE la respuesta mediría", report.errors[0])

    def test_smaller_status_fits_ble(self):
        recorded = copy.deepcopy(self.recorded)
        body = recorded["GET /api/status"]["body"]
        for name in ("radio", "display", "power"):
            body["subsystems"].pop(name)
        body["memory"].pop("stack_free_min_bytes")
        body["alerts"] = []
        self.assertLess(cc.ble_message_bytes(200, body), 4096)
        report = self.run_device(recorded, ble_size=True)
        self.assertEqual(report.errors, [])

    def test_ble_size_ignores_secrets_like_the_firmware(self):
        body = {"ap_password": "x" * 5000, "wifi_password_saved": True, "nested": [{"cpass": "y" * 100}]}
        stripped = cc.strip_ble_secrets(body)
        self.assertEqual(stripped, {"wifi_password_saved": True, "nested": [{}]})
        self.assertLess(cc.ble_message_bytes(200, body), 200)

    def test_missing_required_key_fails(self):
        report = self.mutated("GET /api/status", lambda b: b.pop("firmware_version"))
        self.assertIn("falta «firmware_version»", "\n".join(report.errors))

    def test_missing_optional_key_is_fine(self):
        report = self.mutated("GET /api/status", lambda b: b["solution"].pop("satellites_used"))
        self.assertTrue(report.ok, report.errors)

    def test_wrong_type_fails(self):
        def change(body):
            body["satellites"][0]["el"] = 61.5
        report = self.mutated("GET /api/gnss/sky", change)
        self.assertIn("«satellites[].el» es number y el contrato dice integer", "\n".join(report.errors))

    def test_null_where_not_nullable_fails(self):
        report = self.mutated("GET /api/config", lambda b: b.update(revision=None))
        self.assertIn("«revision» llega null", "\n".join(report.errors))

    def test_array_element_without_required_key_fails(self):
        report = self.mutated("GET /api/wifi/scan", lambda b: b["networks"][1].pop("ssid"))
        self.assertIn("falta «networks[].ssid»", "\n".join(report.errors))

    def test_strict_enum_fails_and_tolerant_enum_warns(self):
        report = self.mutated("GET /api/status", lambda b: b.update(receiver_role="base_and_rover"))
        self.assertIn("«receiver_role»", "\n".join(report.errors))
        report = self.mutated("GET /api/status", lambda b: b["solution"].update(fix="rtk_super"))
        self.assertTrue(report.ok)
        self.assertIn("«solution.fix»", "\n".join(report.warnings))

    def test_status_codes(self):
        recorded = copy.deepcopy(self.recorded)
        recorded["GET /api/update"] = {"status": 404, "body": {"error": "not_found"}}
        recorded["GET /api/recording/sessions"] = {"status": 503, "body": {"message": "sin memoria"}}
        report = self.run_device(recorded)
        self.assertEqual(len(report.errors), 1)
        self.assertIn("GET /api/update: el equipo contesta 404", report.errors[0])
        self.assertIn("GET /api/recording/sessions: estado 503", "\n".join(report.warnings))

    def test_missing_answer_is_an_error(self):
        recorded = copy.deepcopy(self.recorded)
        del recorded["GET /api/gnss/sky"]
        self.assertIn("GET /api/gnss/sky: sin respuesta", "\n".join(self.run_device(recorded).errors))

    def test_wait_until_ready_retries_while_booting(self):
        class Booting:
            def __init__(self, silent):
                self.silent = silent
                self.calls = 0

            def request(self, method, path, body=None):
                self.calls += 1
                if self.calls <= self.silent:
                    raise TimeoutError("arrancando")
                return {"status": 200, "body": {}}

        device = Booting(silent=2)
        self.assertTrue(cc.wait_until_ready(device))
        self.assertEqual(device.calls, 3)
        self.assertFalse(cc.wait_until_ready(Booting(silent=99), attempts=3))

    def test_record_redacts_secrets(self):
        recorded = copy.deepcopy(self.recorded)
        recorded["GET /api/config"]["body"]["ap_password"] = "secreto-de-verdad"
        recorder = cc.RecordingInstrument(cc.ReplayInstrument(recorded))
        cc.check_device(self.contract, recorder)
        saved = recorder.recorded["GET /api/config"]["body"]
        self.assertEqual(saved["ap_password"], "redactado")
        self.assertEqual(saved["ap_ssid"], "MeridianV")


class CommandLineTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=120)

    def test_static_by_default(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("cumple", result.stdout)

    def test_static_broken_tree_exits_1(self):
        edit = ("src/firmware_update.cpp", 'out["hardware_id"] = hardware;', "")
        with MutatedFirmware([edit]) as root:
            result = self.run_cli("static", "--firmware-root", str(root))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("hardware_id", result.stdout)

    def test_bad_contract_exits_2(self):
        with tempfile.TemporaryDirectory() as folder:
            bad = Path(folder) / "bad.json"
            bad.write_text(json.dumps({"routes": [{"method": "GET", "path": "/api/x"}]}), encoding="utf-8")
            result = self.run_cli("--contract", str(bad))
        self.assertEqual(result.returncode, 2, result.stdout)

    def test_device_replay(self):
        # Tal cual, la fixture solo falla por el tamaño de /api/status por BLE.
        result = self.run_cli("device", "--replay", str(FIXTURE))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("GET /api/status: por BLE", result.stdout)
        self.assertEqual(result.stdout.count("ERROR"), 1, result.stdout)

        recorded = load_fixture()
        status = recorded["GET /api/status"]["body"]
        for name in ("radio", "display", "power"):
            status["subsystems"].pop(name)
        status["memory"].pop("stack_free_min_bytes")
        status["alerts"] = []
        with tempfile.TemporaryDirectory() as folder:
            fitting = Path(folder) / "fitting.json"
            fitting.write_text(json.dumps(recorded), encoding="utf-8")
            result = self.run_cli("device", "--replay", str(fitting))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            recorded["GET /api/config"]["body"].pop("revision")
            broken = Path(folder) / "broken.json"
            broken.write_text(json.dumps(recorded), encoding="utf-8")
            result = self.run_cli("device", "--replay", str(broken))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("falta «revision»", result.stdout)


if __name__ == "__main__":
    unittest.main()
