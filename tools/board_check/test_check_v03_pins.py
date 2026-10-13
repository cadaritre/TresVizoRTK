"""Pruebas del comprobador de pines de la v0.3: python3 -m unittest discover -s tools/board_check

La placa del pedido (97000ef) y el perfil de firmware tienen que cumplir; cualquier
cambio de pin, polaridad o dirección en el perfil, o un cambio en la placa, tiene que
hacerlo fallar con un motivo legible.
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_v03_pins as cv  # noqa: E402


def committed_netlist():
    try:
        return cv.netlist_from_git(cv.JLC_COMMIT)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return (cv.ROOT / cv.NETLIST).read_text(encoding='utf-8')


NETLIST = committed_netlist()
PROFILE = cv.PROFILE.read_text(encoding='utf-8')


def check(profile=PROFILE, netlist=NETLIST):
    return cv.run_checks(cv.parse_netlist(netlist), cv.parse_profile(profile))


def with_constant(name, value, text=PROFILE):
    """El perfil con `name` cambiado (constexpr o #define)."""
    changed, count = re.subn(rf'(\b{name}\b(?:\[\])?\s*=\s*)[^,;]+', rf'\g<1>{value}', text, count=1)
    if not count:
        changed, count = re.subn(rf'(#define\s+{name}\s+)\S+', rf'\g<1>{value}', text, count=1)
    assert count, name
    return changed


class BoardCheckTests(unittest.TestCase):
    def test_board_sent_to_jlc_matches_profile(self):
        report = check()
        self.assertEqual(report.errors, [])
        self.assertGreater(report.checks, 150)
        self.assertTrue(all(row.ok for row in report.rows))
        gpio = {row.net: row.gpio for row in report.rows}
        self.assertEqual((gpio['GNSS_TX_MCU'], gpio['GNSS_TXD2_MCU'], gpio['GNSS_PWR_EN']), (8, 9, 45))
        self.assertEqual((gpio['I2C_SDA'], gpio['I2C_SCL'], gpio['SD_DET'], gpio['LED_STATUS']), (13, 14, 17, 48))

    def test_working_tree_netlist_is_the_one_sent_to_jlc(self):
        # hardware/ no se toca después del pedido: si alguien la cambia, que se note aquí.
        working = (cv.ROOT / cv.NETLIST).read_text(encoding='utf-8')
        self.assertEqual(cv.comparable(working), cv.comparable(NETLIST))

    def test_profile_parser_reads_every_form(self):
        profile = cv.parse_profile(PROFILE)
        self.assertEqual(profile['TRESVIZO_GNSS_RX'], 9)
        self.assertEqual((profile['kUsbDm'], profile['kUsbDp']), (19, 20))     # dos en una línea
        self.assertEqual(profile['kPowerPush'], 18)                            # alias
        self.assertEqual(profile['kChargerAddress'], 0x6B)
        self.assertIs(profile['kSdDetectActiveLow'], False)
        self.assertIsNone(profile['kIpRating'])
        self.assertEqual(profile['kImu'], 'BMI088')
        self.assertEqual(profile['kAutoShutdownVolts'], 3.45)

    def assertFails(self, report, fragment):
        self.assertTrue(any(fragment in e for e in report.errors), (fragment, report.errors))

    def test_swapped_uart_fails(self):
        profile = with_constant('TRESVIZO_GNSS_TX', 9, with_constant('TRESVIZO_GNSS_RX', 8))
        report = check(profile)
        self.assertFails(report, 'TRESVIZO_GNSS_TX = GPIO9')
        self.assertFails(report, 'TRESVIZO_GNSS_RX = GPIO8')

    def test_thing_plus_pins_fail(self):
        # Los de la Thing Plus en la v0.3: detección en 48 (ahí está el LED), I2C en 8/9.
        self.assertFails(check(with_constant('kSdDetect', 48)), 'kSdDetect = GPIO48')
        self.assertFails(check(with_constant('kSda', 8)), 'kSda = GPIO8')
        self.assertFails(check(with_constant('kPeripheralEnable', 45)), 'kPeripheralEnable')
        self.assertFails(check(with_constant('kPowerOff', 14)), 'kPowerOff')

    def test_polarities_and_addresses_fail(self):
        self.assertFails(check(with_constant('kSdDetectActiveLow', 'true')), 'kSdDetectActiveLow')
        self.assertFails(check(with_constant('kSdDetectInternalPull', 'true')), 'kSdDetectInternalPull')
        self.assertFails(check(with_constant('kImuAccelAddress', '0x19')), 'acelerómetro')
        self.assertFails(check(with_constant('kImuGyroAddress', '0x69')), 'giróscopo')
        self.assertFails(check(with_constant('kChargerAddress', '0x6A')), 'kChargerAddress')
        self.assertFails(check(with_constant('kChargeCurrentMa', 2000)), 'ICHG')
        self.assertFails(check(with_constant('kChargeVoltageMv', 4350)), 'PROG')
        self.assertFails(check(with_constant('kOledRotation', 0)), 'kOledRotation')

    def test_strapping_and_duplicates_fail(self):
        self.assertFails(check(with_constant('kStatusLed', 0)), 'pin de arranque')
        self.assertFails(check(with_constant('kGaugeAlert', 21)), 'ya lo usa')

    def move(self, netlist, ref, pin, to):
        """El nodo `ref.pin` pasa a la red `to` (sobre el netlist ya leído)."""
        for nodes in netlist.nets.values():
            for node in list(nodes):
                if node.ref == ref and node.pin == pin:
                    nodes.remove(node)
                    netlist.nets[to].append(node)
                    return netlist
        raise AssertionError(f'{ref}.{pin}')

    def test_board_changes_fail(self):
        profile = cv.parse_profile(PROFILE)
        # Sin el pull-down de la detección (R407 al aire), la lectura sin tarjeta flotaría.
        board = self.move(cv.parse_netlist(NETLIST), 'R407', '2', 'unconnected-(U201-IO38-Pad31)')
        self.assertFails(cv.run_checks(board, profile), 'SD_DET')
        # SDO1 a VDDIO: el acelerómetro pasaría a 0x19.
        board = self.move(cv.parse_netlist(NETLIST), 'U401', '15', '+3V3')
        self.assertFails(cv.run_checks(board, profile), 'acelerómetro')
        # La OLED con GND y VCC cruzados en el esquema.
        board = self.move(self.move(cv.parse_netlist(NETLIST), 'J403', '1', 'GND'), 'J403', '2', '+3V3')
        self.assertFails(cv.run_checks(board, profile), 'OLED J403')
        # Un GPIO nuevo con señal que el perfil no nombra.
        extra = NETLIST.replace('"unconnected-(U201-IO38-Pad31)"', '"NUEVA_SENAL"')
        self.assertFails(check(netlist=extra), 'GPIO38 lleva la red NUEVA_SENAL')
        # Símbolo del módulo con un pin mal numerado.
        wrong = NETLIST.replace('(pinfunction "IO8_12")', '(pinfunction "IO9_12")', 1)
        self.assertFails(check(netlist=wrong), 'U201 pin 12')

if __name__ == '__main__':
    unittest.main()
