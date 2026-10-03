#!/usr/bin/env python3
"""Genera firmware/esp32/lib/protocol/src/ble_status_keys.h desde el contrato.

Por Bluetooth, `GET /api/status` lleva solo lo que leen las apps (las claves de
respuesta de esa ruta en docs/api-contract/app-contract.json): así cabe en los 4096
bytes de una respuesta BLE aunque el estado completo crezca. Se vuelve a generar
cada vez que cambia el contrato; `check_contract.py static` falla si se olvida.

    python3 tools/api_contract/generate_ble_status_keys.py          # escribe la cabecera
    python3 tools/api_contract/generate_ble_status_keys.py --check  # solo comprueba
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / 'docs' / 'api-contract' / 'app-contract.json'
HEADER = ROOT / 'firmware' / 'esp32' / 'lib' / 'protocol' / 'src' / 'ble_status_keys.h'


def status_paths(contract):
    for route in contract['routes']:
        if route.get('path') == '/api/status' and route.get('method', 'GET') == 'GET':
            return sorted({entry['path'] for entry in route.get('response', [])})
    raise SystemExit('El contrato no tiene GET /api/status.')


def render(paths):
    lines = [
        '#pragma once',
        '#include <cstddef>',
        '',
        '// GENERADO por tools/api_contract/generate_ble_status_keys.py desde',
        '// docs/api-contract/app-contract.json. No editar a mano: regenerar.',
        '//',
        '// Lo que las apps leen de GET /api/status. Por Bluetooth la respuesta se recorta',
        '// a esto (json_allowlist.h) para que quepa en 4096 bytes.',
        'namespace protocol {',
        'constexpr const char* kBleStatusKeys[] = {',
    ]
    lines += [f'    "{path}",' for path in paths]
    lines += [
        '};',
        'constexpr size_t kBleStatusKeyCount = sizeof(kBleStatusKeys) / sizeof(kBleStatusKeys[0]);',
        '}  // namespace protocol',
        '',
    ]
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true', help='no escribe; falla si la cabecera no está al día')
    args = parser.parse_args()
    expected = render(status_paths(json.loads(CONTRACT.read_text(encoding='utf-8'))))
    if args.check:
        current = HEADER.read_text(encoding='utf-8') if HEADER.is_file() else ''
        if current != expected:
            print(f'{HEADER.relative_to(ROOT)} no está al día con el contrato: '
                  'corre tools/api_contract/generate_ble_status_keys.py', file=sys.stderr)
            return 1
        print('ble_status_keys.h al día con el contrato.')
        return 0
    HEADER.write_text(expected, encoding='utf-8')
    print(f'Escrito {HEADER.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
