#!/usr/bin/env python3
"""Compara el perfil de firmware de la placa v0.3 con el netlist de la placa fabricada.

La fuente de verdad es el netlist del pedido a JLCPCB (commit 97000ef,
hardware/main-board/kicad/tresvizo-main.net, idéntico al que exporta kicad-cli del
esquema de ese commit). Falla si cualquier GPIO, polaridad, dirección I2C o periférico
de `firmware/esp32/include/board_profile_v03.h` no coincide con la placa.

    python3 tools/board_check/check_v03_pins.py                 # netlist de 97000ef (git)
    python3 tools/board_check/check_v03_pins.py --netlist X.net  # otro netlist
    python3 tools/board_check/check_v03_pins.py --kicad          # exporta el esquema de 97000ef
    python3 tools/board_check/check_v03_pins.py --markdown       # tabla para la documentación

No escribe nada dentro de hardware/: el esquema se exporta en una carpeta temporal.
Solo usa la biblioteca estándar de Python.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / 'firmware/esp32/include/board_profile_v03.h'
NETLIST = 'hardware/main-board/kicad/tresvizo-main.net'
SCHEMATIC_DIR = 'hardware/main-board/kicad'
JLC_COMMIT = '97000ef'
KICAD_CLI = Path('/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')

# Pines del ESP32-S3-WROOM-1 (Espressif, hoja del módulo v1.8, tabla 3-1). Se comparan
# con el símbolo de KiCad: si el símbolo numerara mal un pin, todo lo demás mentiría.
# Pin del módulo → GPIO (None: alimentación o EN) y los nombres que admite el símbolo
# (la hoja da a 13/14 y 36/37 su función: USB_D−/D+ y RXD0/TXD0).
WROOM1_PINS = {
    1: (None, {'GND'}), 2: (None, {'3V3'}), 3: (None, {'EN'}), 4: (4, set()), 5: (5, set()), 6: (6, set()),
    7: (7, set()), 8: (15, set()), 9: (16, set()), 10: (17, set()), 11: (18, set()), 12: (8, set()),
    13: (19, {'USB_D-'}), 14: (20, {'USB_D+'}), 15: (3, set()), 16: (46, set()), 17: (9, set()), 18: (10, set()),
    19: (11, set()), 20: (12, set()), 21: (13, set()), 22: (14, set()), 23: (21, set()), 24: (47, set()),
    25: (48, set()), 26: (45, set()), 27: (0, set()), 28: (35, set()), 29: (36, set()), 30: (37, set()),
    31: (38, set()), 32: (39, set()), 33: (40, set()), 34: (41, set()), 35: (42, set()), 36: (44, {'RXD0'}),
    37: (43, {'TXD0'}), 38: (2, set()), 39: (1, set()), 40: (None, {'GND'}), 41: (None, {'GND'}),
}
STRAPPING = {0, 3, 45, 46}          # hoja del ESP32-S3, §2.6 «Strapping Pins»
FLASH_PSRAM = set(range(26, 33))    # SPI de la flash y de la PSRAM quad (no salen en el WROOM-1)
OCTAL_PSRAM_ONLY = {33, 34, 35, 36, 37}

# Lo que tiene que cumplir cada constante del perfil: red de la placa y comprobaciones.
# `uso` es lo que hace el firmware con ese pin (para la tabla).
SIGNALS = [
    ('TRESVIZO_GNSS_TX', 'GNSS_TX_MCU', 'UART del UM980: TX → RXD2 de la carrier (COM2)'),
    ('TRESVIZO_GNSS_RX', 'GNSS_TXD2_MCU', 'UART del UM980: RX ← TXD2 de la carrier (COM2)'),
    ('kGnssPps', 'GNSS_PPS_MCU', 'PPS del UM980 (entrada; sin uso todavía)'),
    ('kGnssEvent', 'GNSS_EVENT_MCU', 'EVENT del UM980 (no se maneja; R308 lo deja en bajo)'),
    ('kGnssReset', 'GNSS_RESET_MCU', 'RESET_N del UM980 (entrada en alta impedancia; la BDLX no lo saca)'),
    ('kGnssPowerEnable', 'GNSS_PWR_EN', 'Enciende el 5 V de la carrier (TPS63070) antes de abrir la UART'),
    ('kSda', 'I2C_SDA', 'I2C: OLED, BQ25798 y MAX17048 (SDA)'),
    ('kScl', 'I2C_SCL', 'I2C: OLED, BQ25798 y MAX17048 (SCL)'),
    ('kSdClock', 'SD_CLK', 'microSD SD_MMC CLK'),
    ('kSdCommand', 'SD_CMD', 'microSD SD_MMC CMD'),
    ('kSdD0', 'SD_D0', 'microSD SD_MMC D0'),
    ('kSdD1', 'SD_D1', 'microSD SD_MMC D1'),
    ('kSdD2', 'SD_D2', 'microSD SD_MMC D2'),
    ('kSdD3', 'SD_D3', 'microSD SD_MMC D3'),
    ('kSdDetect', 'SD_DET', 'Detección de tarjeta: HIGH con tarjeta, sin pull interno'),
    ('kPowerButton', 'BTN_SENSE_N', 'Botón: activo bajo; 2 s = apagado (modo ship)'),
    ('kStatusLed', 'LED_STATUS', 'LED de estado: activo alto'),
    ('kChargerInt', 'CHG_INT_N', 'INT del BQ25798 (entrada; se lee por I2C cada segundo)'),
    ('kGaugeAlert', 'FG_ALRT_N', 'ALRT del MAX17048 (entrada; sin uso)'),
    ('kImuSda', 'IMU_SDA', 'Wire1 del BMI088 (SDA, 400 kHz)'),
    ('kImuScl', 'IMU_SCL', 'Wire1 del BMI088 (SCL)'),
    ('kImuInt1', 'IMU_INT1', 'INT1 del acelerómetro (entrada con pull-down interno)'),
    ('kImuInt3', 'IMU_INT3', 'INT3 del giróscopo (entrada con pull-down interno)'),
    ('kUsbDm', 'USB_DN', 'USB nativo D− (consola JSON y carga de firmware)'),
    ('kUsbDp', 'USB_DP', 'USB nativo D+'),
    ('kConsoleTx', 'ESP_TXD0', 'U0TXD: mensajes de la ROM (TP208)'),
    ('kConsoleRx', 'ESP_RXD0', 'U0RXD (TP209)'),
]
# Redes del módulo que el perfil no tiene por qué nombrar.
# EN y BOOT son de los pulsadores, GPIO3 solo lleva su resistencia de arranque y
# GPIO35-37 son puntos de prueba libres.
NOT_FIRMWARE = {'GND', '+3V3', 'ESP_EN', 'ESP_BOOT', 'ESP_IO3', 'ESP_IO35', 'ESP_IO36', 'ESP_IO37'}


# ---------------------------------------------------------------------------------------
# Netlist (formato KiCad s-expression, versión E)
# ---------------------------------------------------------------------------------------

@dataclass
class Node:
    ref: str
    pin: str
    function: str


@dataclass
class Netlist:
    nets: dict[str, list[Node]] = field(default_factory=dict)
    values: dict[str, str] = field(default_factory=dict)

    def short(self, name: str) -> str:
        """`/microSD, IMU…/SD_CD_N` → `SD_CD_N` (las redes locales llevan la hoja delante)."""
        return name.rsplit('/', 1)[-1]

    def net_of(self, ref: str, pin: str) -> str | None:
        for name, nodes in self.nets.items():
            if any(n.ref == ref and n.pin == pin for n in nodes):
                return self.short(name)
        return None

    def nodes(self, net: str) -> list[Node]:
        for name, nodes in self.nets.items():
            if self.short(name) == net:
                return nodes
        return []

    def pin_by_function(self, ref: str, prefix: str) -> tuple[str, str] | None:
        """(pin, red) del pin de `ref` cuya función empieza por `prefix`."""
        for name, nodes in self.nets.items():
            for n in nodes:
                if n.ref == ref and n.function.split('_')[0].lstrip('~{').rstrip('}') == prefix:
                    return n.pin, self.short(name)
        return None

    def other_side(self, ref: str, net: str) -> str | None:
        """Red del otro extremo de una pieza de dos patas (resistencia, diodo)."""
        pins = [n.pin for n in self.nodes(net) if n.ref == ref]
        if not pins:
            return None
        for pin in ('1', '2'):
            if pin not in pins:
                return self.net_of(ref, pin)
        return None

    def resistor_to(self, net: str, rail: str) -> list[str]:
        """Resistencias que unen `net` con `rail` (GND o +3V3)."""
        return [n.ref for n in self.nodes(net) if n.ref.startswith('R') and self.other_side(n.ref, net) == rail]


def tokenize(text: str) -> list[str]:
    return re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+', text)


def parse_netlist(text: str) -> Netlist:
    tokens = tokenize(text)
    stack: list[list] = [[]]
    for token in tokens:
        if token == '(':
            stack.append([])
        elif token == ')':
            done = stack.pop()
            stack[-1].append(done)
        else:
            stack[-1].append(token[1:-1].replace('\\"', '"') if token.startswith('"') else token)
    root = stack[0][0]

    def children(node, name):
        return [c for c in node if isinstance(c, list) and c and c[0] == name]

    def value(node, name):
        found = children(node, name)
        return found[0][1] if found and len(found[0]) > 1 else ''

    netlist = Netlist()
    for comp in children(children(root, 'components')[0], 'comp'):
        netlist.values[value(comp, 'ref')] = value(comp, 'value')
    for net in children(children(root, 'nets')[0], 'net'):
        netlist.nets[value(net, 'name')] = [Node(value(n, 'ref'), value(n, 'pin'), value(n, 'pinfunction'))
                                            for n in children(net, 'node')]
    return netlist


def netlist_from_git(commit: str) -> str:
    return subprocess.run(['git', '-C', str(ROOT), 'show', f'{commit}:{NETLIST}'], check=True,
                          capture_output=True, text=True).stdout


def netlist_from_kicad(commit: str) -> str:
    """Exporta el esquema de `commit` con kicad-cli en una carpeta temporal."""
    if not KICAD_CLI.is_file():
        raise SystemExit(f'No está kicad-cli en {KICAD_CLI}.')
    with tempfile.TemporaryDirectory(prefix='tresvizo-v03-') as folder:
        archive = subprocess.run(['git', '-C', str(ROOT), 'archive', commit, SCHEMATIC_DIR], check=True,
                                 capture_output=True).stdout
        subprocess.run(['tar', '-x', '-C', folder], input=archive, check=True)
        output = Path(folder) / 'export.net'
        subprocess.run([str(KICAD_CLI), 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', str(output),
                        str(Path(folder) / SCHEMATIC_DIR / 'tresvizo-main.kicad_sch')], check=True,
                       capture_output=True)
        return output.read_text(encoding='utf-8')


def comparable(text: str) -> str:
    """El netlist sin las líneas que cambian en cada exportación (fecha, ruta, herramienta)."""
    return '\n'.join(line for line in text.splitlines() if not re.match(r'\s*\((date|source|tool) ', line))


# ---------------------------------------------------------------------------------------
# Perfil de firmware
# ---------------------------------------------------------------------------------------

def parse_profile(text: str) -> dict[str, object]:
    code = re.sub(r'//[^\n]*', '', text)
    values: dict[str, object] = {}
    for name, raw in re.findall(r'#define\s+(TRESVIZO_\w+)\s+([^\s]+)', code):
        values[name] = raw.strip('"') if raw.startswith('"') else int(raw, 0)
    pairs = []
    for statement in re.findall(r'constexpr\s+([^;]+);', code):
        # `constexpr int kA = 1, kB = 2;`: un par por declarador.
        for name, raw in re.findall(r'\b(k\w+)(?:\[\])?\s*=\s*("[^"]*"|[^,]+)', statement):
            pairs.append((name, raw))
    for name, raw in pairs:
        raw = raw.strip()
        if raw in ('true', 'false'):
            values[name] = raw == 'true'
        elif raw == 'nullptr':
            values[name] = None
        elif raw.startswith('"'):
            values[name] = raw.strip('"')
        elif re.fullmatch(r'-?(0x[0-9a-fA-F]+|\d+)', raw):
            values[name] = int(raw, 0)
        elif re.fullmatch(r'-?\d+\.\d*f?', raw):
            values[name] = float(raw.rstrip('f'))
        elif raw in values:
            values[name] = values[raw]
        else:
            values[name] = raw
    return values


# ---------------------------------------------------------------------------------------
# Comprobaciones
# ---------------------------------------------------------------------------------------

@dataclass
class Row:
    net: str
    gpio: int | None
    use: str
    ok: bool
    note: str = ''


@dataclass
class Report:
    rows: list[Row] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    checks: int = 0

    def check(self, condition: bool, message: str) -> bool:
        self.checks += 1
        if not condition:
            self.errors.append(message)
        return condition


def module_map(netlist: Netlist, report: Report) -> dict[int, str]:
    """GPIO → red, comprobando el símbolo de U201 contra la tabla de Espressif."""
    gpio_net: dict[int, str] = {}
    seen = set()
    for name, nodes in netlist.nets.items():
        for n in nodes:
            if n.ref != 'U201':
                continue
            pin = int(n.pin)
            seen.add(pin)
            gpio, aliases = WROOM1_PINS.get(pin, (None, set()))
            function = n.function.rsplit('_', 1)[0]
            names = set(aliases) | ({f'IO{gpio}'} if gpio is not None else set())
            report.check(pin in WROOM1_PINS and function in names,
                         f'U201 pin {pin}: el símbolo dice «{function}» y la hoja del WROOM-1 «{"/".join(sorted(names))}».')
            if gpio is not None:
                gpio_net[gpio] = netlist.short(name)
    report.check(seen == set(WROOM1_PINS), f'U201: faltan pines en el netlist: {sorted(set(WROOM1_PINS) - seen)}.')
    return gpio_net


def pin_to(netlist: Netlist, ref: str, function: str) -> str | None:
    found = netlist.pin_by_function(ref, function)
    return found[1] if found else None


def run_checks(netlist: Netlist, profile: dict[str, object]) -> Report:
    report = Report()
    v = netlist.values
    # Piezas montadas que el firmware supone.
    for ref, part in (('U201', 'ESP32-S3-WROOM-1-N16R2'), ('U102', 'BQ25798'), ('U103', 'MAX17048'),
                      ('U401', 'BMI088'), ('U301', 'TPS63070'), ('Q401', 'AO3401A'), ('D402', '1N4148W'),
                      ('Q101', 'AO3400A')):
        report.check(part in v.get(ref, ''), f'{ref}: se esperaba {part} y el netlist dice «{v.get(ref)}».')

    gpio_net = module_map(netlist, report)
    used: dict[int, str] = {}
    for constant, net, use in SIGNALS:
        gpio = profile.get(constant)
        if not report.check(isinstance(gpio, int) and gpio >= 0, f'{constant}: falta en el perfil o vale -1.'):
            report.rows.append(Row(net, None, use, False, 'falta en el perfil'))
            continue
        actual = gpio_net.get(gpio)
        ok = report.check(actual == net, f'{constant} = GPIO{gpio}: en la placa ese GPIO es «{actual}», '
                                         f'y la señal {net} está en GPIO{next((g for g, n in gpio_net.items() if n == net), "?")}.')
        if gpio in used:
            ok = report.check(False, f'{constant}: GPIO{gpio} ya lo usa {used[gpio]}.') and ok
        used[gpio] = constant
        report.rows.append(Row(net, gpio, use, ok))
    # Lo que no debe tener la v0.3.
    report.check(profile.get('kPeripheralEnable') == -1, 'kPeripheralEnable: la v0.3 no tiene regulador de periféricos.')
    report.check(profile.get('kPowerOff') == -1, 'kPowerOff: la v0.3 no corta por GPIO (modo ship por I2C).')
    report.check(profile.get('kPowerPush') == profile.get('kPowerButton'), 'kPowerPush tiene que ser el botón.')
    report.check(profile.get('TRESVIZO_GNSS_BAUD') == 115200, 'UART del UM980: COM2 a 115200.')
    report.check(str(profile.get('TRESVIZO_HARDWARE_ID', '')).startswith('tresvizo-') and
                 len(str(profile.get('TRESVIZO_HARDWARE_ID', ''))) < 48, 'TRESVIZO_HARDWARE_ID: «tresvizo-…» y < 48 bytes.')

    # Toda señal del módulo que el firmware podría necesitar está en el perfil.
    named = {net for _, net, _ in SIGNALS}
    for gpio, net in sorted(gpio_net.items()):
        if net.startswith('unconnected') or net in NOT_FIRMWARE or net in named:
            continue
        report.check(False, f'GPIO{gpio} lleva la red {net} y el perfil no la nombra.')

    # Pines de arranque, flash y PSRAM.
    for constant, net, _ in SIGNALS:
        gpio = profile.get(constant)
        if not isinstance(gpio, int) or gpio < 0:
            continue
        report.check(gpio not in FLASH_PSRAM, f'{constant}: GPIO{gpio} es de la flash/PSRAM del módulo.')
        if gpio in STRAPPING:
            # El único admitido: GPIO45, salida con pull-down externo (VDD_SPI = 3.3 V en el reset).
            report.check(gpio == 45 and constant == 'kGnssPowerEnable' and netlist.resistor_to(net, 'GND'),
                         f'{constant}: GPIO{gpio} es pin de arranque y no tiene el pull-down que lo deja bajo en el reset.')
    report.check('N16R2' in v.get('U201', ''), 'U201: PSRAM octal (R8) ocuparía GPIO33-37.')
    report.check(netlist.resistor_to('ESP_IO3', 'GND') != [], 'GPIO3 (pin de arranque JTAG) sin su resistencia a GND.')
    report.check(netlist.resistor_to('ESP_BOOT', '+3V3') != [], 'GPIO0 (BOOT) sin pull-up: no arrancaría desde la flash.')

    # UART, PPS, EVENT y RESET del GNSS hasta J301 (resistencias en serie).
    for net, ref, j301_pin in (('GNSS_TX_MCU', 'R304', '3'), ('GNSS_TXD2_MCU', 'R305', '4'), ('GNSS_PPS_MCU', 'R306', '5'),
                               ('GNSS_EVENT_MCU', 'R307', '6'), ('GNSS_RESET_MCU', 'R309', '7')):
        far = netlist.other_side(ref, net)
        report.check(far is not None and far == netlist.net_of('J301', j301_pin),
                     f'{net}: no llega a J301.{j301_pin} por {ref}.')
    report.check(netlist.resistor_to('GNSS_EVENT_MCU', 'GND') != [], 'EVENT sin pull-down (R308).')
    report.check(pin_to(netlist, 'U301', 'EN') == 'GNSS_PWR_EN', 'GNSS_PWR_EN no llega al EN del TPS63070.')
    report.check(netlist.resistor_to('GNSS_PWR_EN', 'GND') != [], 'GNSS_PWR_EN sin pull-down: el GNSS no quedaría apagado en el reset.')

    # I2C principal: OLED, cargador y medidor; direcciones fijas de esos chips.
    for net, oled_pin in (('I2C_SDA', '4'), ('I2C_SCL', '3')):
        report.check(netlist.resistor_to(net, '+3V3') != [], f'{net} sin pull-up.')
        report.check(netlist.net_of('J403', oled_pin) == net, f'{net}: no llega a la OLED (J403.{oled_pin}).')
    report.check(pin_to(netlist, 'U102', 'SDA') == 'I2C_SDA' and pin_to(netlist, 'U102', 'SCL') == 'I2C_SCL',
                 'El BQ25798 no está en el I2C principal.')
    report.check(pin_to(netlist, 'U103', 'SDA') == 'I2C_SDA' and pin_to(netlist, 'U103', 'SCL') == 'I2C_SCL',
                 'El MAX17048 no está en el I2C principal.')
    report.check(profile.get('kChargerAddress') == 0x6B, 'kChargerAddress: el BQ25798 es 0x6B (SLUSDV2C §7.3.14.5).')
    report.check(profile.get('kGaugeAddress') == 0x36, 'kGaugeAddress: el MAX17048 es 0x36.')
    report.check(netlist.net_of('J403', '1') == '+3V3' and netlist.net_of('J403', '2') == 'GND',
                 'OLED J403: el esquema dice VCC, GND, SCL, SDA (pines 1-4).')

    # microSD: bus de 4 bits, pull-ups y detección invertida por Q401.
    for net, function in (('SD_CLK', 'CLK'), ('SD_CMD', 'CMD'), ('SD_D0', 'DAT0'), ('SD_D1', 'DAT1'),
                          ('SD_D2', 'DAT2'), ('SD_D3', 'DAT3')):
        report.check(pin_to(netlist, 'J401', function) == net, f'{net} no llega a {function} de J401.')
        if net != 'SD_CLK':
            report.check(netlist.resistor_to(net, '+3V3') != [], f'{net} sin pull-up de 10 kΩ.')
    cd = pin_to(netlist, 'J401', 'CD')
    gate, source, drain = (netlist.net_of('Q401', p) for p in ('1', '2', '3'))
    inverted = (cd is not None and gate == cd and source == '+3V3' and drain == 'SD_DET' and
                netlist.resistor_to(cd, '+3V3') != [] and netlist.resistor_to('SD_DET', 'GND') != [])
    report.check(inverted, 'SD_DET: se esperaba CD a GND con tarjeta, invertido por Q401 (canal P) con pull-down.')
    report.check(profile.get('kSdDetectActiveLow') is (not inverted),
                 'kSdDetectActiveLow no coincide con la placa (con Q401, HIGH = tarjeta).')
    report.check(profile.get('kSdDetectInternalPull') is False or not netlist.resistor_to('SD_DET', 'GND'),
                 'kSdDetectInternalPull: la placa ya tiene el pull-down (R407).')

    # Botón: activo bajo por D402 desde QON; LED activo alto.
    report.check(netlist.resistor_to('BTN_SENSE_N', '+3V3') != [], 'BTN_SENSE_N sin pull-up.')
    anode, cathode = netlist.net_of('D402', '2'), netlist.net_of('D402', '1')
    report.check(anode == 'BTN_SENSE_N' and cathode == 'BTN_N', 'D402: ánodo en GPIO18 y cátodo en BTN_N.')
    report.check(pin_to(netlist, 'U102', 'QON') == 'BTN_N', 'El botón no llega a QON del BQ25798.')
    report.check(netlist.net_of('SW401', '4') == 'GND' or netlist.net_of('SW401', '1') == 'GND',
                 'SW401 no cierra a GND: el botón no sería activo bajo.')
    led_resistor = [n.ref for n in netlist.nodes('LED_STATUS') if n.ref.startswith('R')]
    led_anode = netlist.other_side(led_resistor[0], 'LED_STATUS') if led_resistor else None
    report.check(led_anode is not None and netlist.net_of('D403', '2') == led_anode and netlist.net_of('D403', '1') == 'GND',
                 'LED_STATUS: se esperaba GPIO → resistencia → ánodo de D403, cátodo a GND (activo alto).')

    # Cargador: PROG (1S), FET de envío y /CE.
    prog = netlist.pin_by_function('U102', 'PROG')
    prog_r = [n.ref for n in netlist.nodes(prog[1]) if n.ref.startswith('R')] if prog else []
    report.check(bool(prog_r) and v.get(prog_r[0]) == '4.7k' and profile.get('kChargeVoltageMv') == 4200,
                 'PROG del BQ25798: 4.7 kΩ es 1S a 750 kHz (tabla 7-1), VREG 4.2 V; el perfil tiene que decir 4200 mV.')
    report.check(pin_to(netlist, 'U102', 'SDRV') is not None and
                 any(n.ref == 'Q101' for n in netlist.nodes(pin_to(netlist, 'U102', 'SDRV') or '')),
                 'SDRV del BQ25798 sin el FET de envío Q101: SFET_PRESENT no debería escribirse.')
    report.check(pin_to(netlist, 'U102', 'CE') == 'GND', '/CE del BQ25798 no está a GND.')
    report.check(isinstance(profile.get('kChargeCurrentMa'), int) and profile.get('kChargeCurrentMa') <= 1500
                 and profile.get('kChargeCurrentMaxMa') == 1500, 'ICHG: 1.5 A como mucho (J102, AWG #26).')
    report.check(pin_to(netlist, 'U102', 'INT') == 'CHG_INT_N' and netlist.resistor_to('CHG_INT_N', '+3V3') != [],
                 'INT del BQ25798 sin su pull-up.')
    report.check(pin_to(netlist, 'U103', 'ALRT') == 'FG_ALRT_N' and netlist.resistor_to('FG_ALRT_N', '+3V3') != [],
                 'ALRT del MAX17048 sin su pull-up.')

    # BMI088: I2C (PS y CSB1 a VDDIO), direcciones por SDO1/SDO2, interrupciones.
    report.check(pin_to(netlist, 'U401', 'PS') == '+3V3', 'BMI088: PS a VDDIO selecciona I2C (DS §6).')
    report.check(pin_to(netlist, 'U401', 'CSB1') == '+3V3', 'BMI088: CSB1 a VDDIO en I2C (DS tabla 14).')
    sdo1, sdo2 = pin_to(netlist, 'U401', 'SDO1'), pin_to(netlist, 'U401', 'SDO2')
    report.check(profile.get('kImuAccelAddress') == (0x18 if sdo1 == 'GND' else 0x19),
                 f'Dirección del acelerómetro: SDO1 en {sdo1} → {"0x18" if sdo1 == "GND" else "0x19"} (DS §6.2).')
    report.check(profile.get('kImuGyroAddress') == (0x68 if sdo2 == 'GND' else 0x69),
                 f'Dirección del giróscopo: SDO2 en {sdo2} → {"0x68" if sdo2 == "GND" else "0x69"} (DS §6.2).')
    report.check(pin_to(netlist, 'U401', 'SDI/SDA') == 'IMU_SDA' and pin_to(netlist, 'U401', 'SCK/SCL') == 'IMU_SCL',
                 'El BMI088 no está en IMU_SDA/IMU_SCL.')
    report.check(pin_to(netlist, 'U401', 'INT1') == 'IMU_INT1' and pin_to(netlist, 'U401', 'INT3') == 'IMU_INT3',
                 'INT1/INT3 del BMI088 no llegan a IMU_INT1/IMU_INT3.')
    for net in ('IMU_SDA', 'IMU_SCL'):
        report.check(netlist.resistor_to(net, '+3V3') != [], f'{net} sin pull-up.')
    report.check(profile.get('kImu') == 'BMI088', 'capabilities.imu: la placa lleva un BMI088.')

    # USB nativo hasta el conector.
    report.check(netlist.net_of('J101', 'A6') == 'USB_DP' and netlist.net_of('J101', 'A7') == 'USB_DN',
                 'USB: D+/D− no llegan a J101.')
    report.check(profile.get('kOledRotation') == 2, 'OLED girada 180° en la placa: kOledRotation = 2.')
    return report


def render(report: Report, markdown: bool) -> str:
    lines = []
    if markdown:
        lines += ['| Red de la placa | GPIO | Uso en el firmware | ✓/✗ |', '| --- | --- | --- | --- |']
        for r in report.rows:
            lines.append(f'| `{r.net}` | {r.gpio if r.gpio is not None else "—"} | {r.use} | {"✓" if r.ok else "✗"} |')
    else:
        for r in report.rows:
            lines.append(f'{"✓" if r.ok else "✗"} {r.net:<16} GPIO{r.gpio if r.gpio is not None else "—":<3} {r.use}')
    return '\n'.join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--netlist', type=Path, help='netlist KiCad (por omisión, el de 97000ef en git)')
    source.add_argument('--kicad', action='store_true', help='exportar el esquema de 97000ef con kicad-cli')
    parser.add_argument('--commit', default=JLC_COMMIT, help='commit del pedido (por omisión 97000ef)')
    parser.add_argument('--profile', type=Path, default=PROFILE)
    parser.add_argument('--markdown', action='store_true')
    args = parser.parse_args(argv)
    if args.netlist:
        text, origin = args.netlist.read_text(encoding='utf-8'), str(args.netlist)
    elif args.kicad:
        text, origin = netlist_from_kicad(args.commit), f'esquema de {args.commit} exportado con kicad-cli'
        committed = netlist_from_git(args.commit)
        if comparable(text) != comparable(committed):
            print(f'AVISO: el netlist guardado en {args.commit} no es el que exporta su esquema.')
    else:
        text, origin = netlist_from_git(args.commit), f'{args.commit}:{NETLIST}'
    report = run_checks(parse_netlist(text), parse_profile(args.profile.read_text(encoding='utf-8')))
    print(f'Netlist: {origin}\nPerfil:  {args.profile.relative_to(ROOT) if args.profile.is_relative_to(ROOT) else args.profile}\n')
    print(render(report, args.markdown))
    print()
    for error in report.errors:
        print(f'ERROR  {error}')
    print(f'{report.checks} comprobaciones, {"cumple" if not report.errors else f"{len(report.errors)} fallos"}.')
    return 0 if not report.errors else 1


if __name__ == '__main__':
    sys.exit(main())
