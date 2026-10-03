#!/usr/bin/env python3
"""Cargador de firmware por USB para los equipos TresVizo (hoy, el receptor MeridianV).

Ventana con tkinter: se elige el modelo, la imagen (firmware.bin o firmware-signed.bin) y
el puerto, y se carga con el mismo esptool y las mismas direcciones que usa
`pio run -t upload`. Antes de cargar comprueba que la imagen sea del modelo elegido
(por su hardware_id, el de firmware/esp32/src/firmware_update.cpp) y, si puede leer el
equipo conectado, avisa si es de otro modelo. Después lee el equipo y confirma
modelo y versión.

Se abre con el Python de python.org (trae tkinter):
    python3 tools/flasher/meridian_flasher.py
El esptool y pyserial los pone PlatformIO (~/.platformio); si no está, sirve un Python
con `pip install esptool pyserial`. Ver tools/flasher/README.md.
"""
from __future__ import annotations

import importlib.util
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / 'firmware' / 'esp32' / '.pio' / 'build'
PLATFORMIO = Path(os.environ.get('PLATFORMIO_CORE_DIR', Path.home() / '.platformio'))


@dataclass(frozen=True)
class Model:
    name: str          # lo que se muestra y lo que anuncia el equipo
    key: str           # `product` de /api/status
    env: str           # entorno de PlatformIO
    hardware_id: str   # identidad de la imagen (la que exige la OTA)


# Los equipos que se pueden cargar. El hardware_id es el de firmware_update.cpp; un
# equipo nuevo (p. ej. el módulo de radio con su propio ESP32) se añade aquí con el suyo.
MODELS = (
    Model('MeridianV', 'meridianv', 'esp32s3_usb', 'tresvizo-esp32s3-4m-v1'),
)

# Formato de la imagen (firmware/esp32/lib/protocol/src/signed_firmware.h).
SIGNATURE_MAGIC = b'TVZSIG01'
SIGNATURE_TRAILER_BYTES = 72
IDENTITY_MAGIC = b'TVZFWID1'
IDENTITY_OFFSET = 24 + 8 + 256
IDENTITY_VERSION_BYTES = 24
ESP_IMAGE_MAGIC = 0xE9
ESP32S3_CHIP_ID = 9
APP_DESC_MAGIC = bytes((0x32, 0x54, 0xCD, 0xAB))
MIN_IMAGE_BYTES = 1024

# Direcciones de la tabla de particiones del proyecto (partitions.csv) y de
# `pio run -t upload`. boot_app0 reinicia la elección de partición: sin él, un equipo
# que se actualizó por OTA seguiría arrancando la otra partición y la carga no se vería.
BOOTLOADER_ADDRESS = 0x0000
PARTITIONS_ADDRESS = 0x8000
BOOT_APP0_ADDRESS = 0xE000
APP_ADDRESS = 0x10000
FLASH_ARGS = ['--flash_mode', 'dio', '--flash_freq', '80m', '--flash_size', '4MB']
UPLOAD_BAUD = 460800

# Tras cargar, el equipo arranca y levanta la consola USB; antes no contesta.
BOOT_WAIT_SECONDS = 8


class FlasherError(Exception):
    pass


@dataclass
class ImageInfo:
    path: Path
    model: Model | None
    version: str | None
    signed: bool
    signature_ok: bool | None           # None: no se pudo comprobar
    signature_message: str
    app: bytes = field(repr=False)      # la imagen sin el trailer de firma: lo que va a la flash

    def describe(self):
        model = self.model.name if self.model else 'modelo desconocido'
        version = self.version or 'versión desconocida'
        if not self.signed:
            firma = 'sin firma (por USB se puede cargar igual)'
        elif self.signature_ok:
            firma = 'firmada por el propietario'
        elif self.signature_ok is None:
            firma = f'firmada, sin comprobar: {self.signature_message}'
        else:
            firma = f'FIRMA NO VÁLIDA: {self.signature_message}'
        return f'{model} · {version} · {firma}'


def model_by_hardware_id(data):
    # El más largo primero: si un hardware_id contuviera a otro, ganaría el exacto.
    for model in sorted(MODELS, key=lambda m: -len(m.hardware_id)):
        if model.hardware_id.encode() in data:
            return model
    return None


def identity_version(app):
    raw = app[IDENTITY_OFFSET:IDENTITY_OFFSET + len(IDENTITY_MAGIC) + IDENTITY_VERSION_BYTES]
    if not raw.startswith(IDENTITY_MAGIC):
        return None
    text = raw[len(IDENTITY_MAGIC):].split(b'\0', 1)[0]
    try:
        return text.decode('ascii') or None
    except UnicodeDecodeError:
        return None


def check_app_image(app):
    """Que sea una imagen de aplicación de ESP32-S3, no un volcado completo ni un bootloader."""
    if len(app) < MIN_IMAGE_BYTES:
        raise FlasherError('El archivo es demasiado pequeño para ser un firmware.')
    if app[0] != ESP_IMAGE_MAGIC:
        raise FlasherError('No es una imagen de firmware de ESP32 (falta la cabecera 0xE9). Elige firmware.bin o firmware-signed.bin.')
    if int.from_bytes(app[12:14], 'little') != ESP32S3_CHIP_ID:
        raise FlasherError('La imagen no es para ESP32-S3.')
    if app[32:36] != APP_DESC_MAGIC:
        raise FlasherError('No es una imagen de aplicación (¿un bootloader o un volcado completo?). Elige firmware.bin o firmware-signed.bin.')


def load_signer():
    path = ROOT / 'tools' / 'firmware_signing' / 'sign_firmware.py'
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location('sign_firmware', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inspect_image(path, signer=None):
    path = Path(path)
    data = path.read_bytes()
    signed = len(data) > SIGNATURE_TRAILER_BYTES and data[-SIGNATURE_TRAILER_BYTES:-SIGNATURE_TRAILER_BYTES + len(SIGNATURE_MAGIC)] == SIGNATURE_MAGIC
    app = data[:-SIGNATURE_TRAILER_BYTES] if signed else data
    check_app_image(app)
    signature_ok, message = None, ''
    if signed:
        try:
            signer = signer or load_signer()
            if signer is None:
                message = 'no está la herramienta de firma'
            else:
                signature_ok, message = signer.verify(data)
        except Exception as error:  # openssl ausente u otra cosa: se dice, no se inventa
            signature_ok, message = None, str(error)
    return ImageInfo(path, model_by_hardware_id(app), identity_version(app), signed, signature_ok, message, app)


def companion(name, image_path, model):
    """bootloader.bin o partitions.bin: junto a la imagen, o en la compilación de ese modelo."""
    for folder in (Path(image_path).parent, BUILD / model.env):
        candidate = folder / name
        if candidate.is_file():
            return candidate
    return None


def boot_app0():
    candidate = PLATFORMIO / 'packages' / 'framework-arduinoespressif32' / 'tools' / 'partitions' / 'boot_app0.bin'
    if candidate.is_file():
        return candidate
    local = Path(__file__).with_name('boot_app0.bin')
    return local if local.is_file() else None


def esptool_command():
    """Cómo lanzar esptool: el de PlatformIO, o el del Python que abre esta ventana."""
    python = PLATFORMIO / 'penv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    script = PLATFORMIO / 'packages' / 'tool-esptoolpy' / 'esptool.py'
    if python.is_file() and script.is_file():
        return [str(python), str(script)], str(python)
    if importlib.util.find_spec('esptool') and importlib.util.find_spec('serial'):
        return [sys.executable, '-m', 'esptool'], sys.executable
    raise FlasherError('No encuentro esptool. Instala PlatformIO (el firmware ya lo usa) o ejecuta: python3 -m pip install esptool pyserial')


def flash_command(esptool, port, app_file, boot_app0_file, full, bootloader=None, partitions=None):
    command = list(esptool) + ['--chip', 'esp32s3', '--port', port, '--baud', str(UPLOAD_BAUD),
                               '--before', 'default_reset', '--after', 'hard_reset', 'write_flash', '-z'] + FLASH_ARGS
    if full:
        if not bootloader or not partitions:
            raise FlasherError('Para la instalación completa faltan bootloader.bin o partitions.bin.')
        command += [hex(BOOTLOADER_ADDRESS), str(bootloader), hex(PARTITIONS_ADDRESS), str(partitions)]
    command += [hex(BOOT_APP0_ADDRESS), str(boot_app0_file), hex(APP_ADDRESS), str(app_file)]
    return command


PROGRESS = re.compile(r'\((\d{1,3}) ?%\)')


def parse_progress(line):
    match = PROGRESS.search(line)
    return int(match.group(1)) if match else None


# Lo que corre dentro del Python de PlatformIO (tiene pyserial): puertos y estado del equipo.
LIST_PORTS_SCRIPT = r'''
import json
from serial.tools import list_ports
print(json.dumps([{"device": p.device, "description": p.description or "", "esp32": p.vid == 0x303A}
                  for p in list_ports.comports() if p.vid is not None]))
'''
READ_STATUS_SCRIPT = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from usb_console import Instrument
device = Instrument(sys.argv[2])
try:
    result = device.request("GET", "/api/status")
    print(json.dumps(result.get("body") or {}))
finally:
    device.close()
'''


def list_ports(python):
    result = subprocess.run([python, '-c', LIST_PORTS_SCRIPT], capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        raise FlasherError('No pude listar los puertos: ' + (result.stderr.strip().splitlines() or ['sin detalle'])[-1])
    ports = json.loads(result.stdout or '[]')
    # Solo puertos USB (no el de Bluetooth ni la consola de depuración del sistema);
    # primero los ESP32 (USB nativo de Espressif, 303A), luego adaptadores serie.
    return sorted(ports, key=lambda p: (not p['esp32'], p['device']))


def read_status(python, port, timeout=12):
    result = subprocess.run([python, '-c', READ_STATUS_SCRIPT, str(ROOT / 'tools'), port],
                            capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise FlasherError((result.stderr.strip().splitlines() or ['El equipo no respondió.'])[-1])
    return json.loads(result.stdout or '{}')


def status_model(status):
    """El modelo que dice el equipo; un firmware sin `product` es un MeridianV."""
    key = status.get('product') or 'meridianv'
    return next((m for m in MODELS if m.key == key), None)


# ---------------------------------------------------------------------------------------
# Ventana
# ---------------------------------------------------------------------------------------

def run_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    try:
        esptool, tool_python = esptool_command()
        tool_error = None
    except FlasherError as error:
        esptool, tool_python, tool_error = None, None, str(error)

    root = tk.Tk()
    root.title('Cargar firmware · TresVizo')
    root.minsize(640, 520)
    events = queue.Queue()
    state = {'image': None, 'busy': False}

    frame = ttk.Frame(root, padding=16)
    frame.pack(fill='both', expand=True)
    frame.columnconfigure(1, weight=1)

    # 1. Modelo
    ttk.Label(frame, text='1. Modelo de receptor', font=('', 13, 'bold')).grid(row=0, column=0, columnspan=3, sticky='w')
    model_var = tk.StringVar(value=MODELS[0].name)
    models_row = ttk.Frame(frame)
    models_row.grid(row=1, column=0, columnspan=3, sticky='w', pady=(4, 12))
    for model in MODELS:
        ttk.Radiobutton(models_row, text=model.name, value=model.name, variable=model_var,
                        command=lambda: refresh_state()).pack(side='left', padx=(0, 16))

    # 2. Imagen
    ttk.Label(frame, text='2. Imagen de firmware', font=('', 13, 'bold')).grid(row=2, column=0, columnspan=3, sticky='w')
    image_var = tk.StringVar(value='Ninguna elegida')
    ttk.Label(frame, textvariable=image_var, wraplength=460).grid(row=3, column=0, columnspan=2, sticky='w', pady=4)
    image_info_var = tk.StringVar(value='')
    ttk.Label(frame, textvariable=image_info_var, wraplength=560, foreground='#1f5fa8').grid(row=4, column=0, columnspan=3, sticky='w')

    def choose_image():
        model = current_model()
        start = BUILD / model.env
        path = filedialog.askopenfilename(title=f'Imagen para {model.name}', initialdir=str(start if start.is_dir() else ROOT),
                                          filetypes=[('Firmware', '*.bin'), ('Todos', '*.*')])
        if not path:
            return
        try:
            info = inspect_image(path)
        except (OSError, FlasherError) as error:
            state['image'] = None
            image_var.set(Path(path).name)
            image_info_var.set(f'No sirve: {error}')
        else:
            state['image'] = info
            image_var.set(str(info.path))
            image_info_var.set(info.describe())
        refresh_state()

    ttk.Button(frame, text='Elegir imagen…', command=choose_image).grid(row=3, column=2, sticky='e')

    # 3. Puerto
    ttk.Label(frame, text='3. Puerto USB del equipo', font=('', 13, 'bold')).grid(row=5, column=0, columnspan=3, sticky='w', pady=(12, 0))
    port_var = tk.StringVar()
    port_box = ttk.Combobox(frame, textvariable=port_var, state='readonly')
    port_box.grid(row=6, column=0, columnspan=2, sticky='ew', pady=4)

    def refresh_ports():
        if not tool_python:
            return
        try:
            ports = list_ports(tool_python)
        except (FlasherError, subprocess.SubprocessError, ValueError) as error:
            log(f'Puertos: {error}')
            ports = []
        port_box['values'] = [p['device'] for p in ports]
        if ports and port_var.get() not in port_box['values']:
            port_var.set(ports[0]['device'])
        if not ports:
            port_var.set('')
            log('No veo ningún equipo por USB. Conéctalo con un cable de datos y pulsa «Buscar».')
        refresh_state()

    ttk.Button(frame, text='Buscar', command=refresh_ports).grid(row=6, column=2, sticky='e')

    # 4. Tipo de carga
    full_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(frame, text='Instalación completa (placa nueva: también bootloader y tabla de particiones)',
                    variable=full_var).grid(row=7, column=0, columnspan=3, sticky='w', pady=(12, 0))
    ttk.Label(frame, text='Ninguna de las dos borra los ajustes guardados del equipo (red Wi-Fi, perfiles NTRIP).',
              foreground='#666').grid(row=8, column=0, columnspan=3, sticky='w')

    # Progreso y registro
    flash_button = ttk.Button(frame, text='Cargar firmware')
    flash_button.grid(row=9, column=0, columnspan=3, sticky='ew', pady=(16, 6))
    progress = ttk.Progressbar(frame, maximum=100)
    progress.grid(row=10, column=0, columnspan=3, sticky='ew')
    status_var = tk.StringVar(value='')
    ttk.Label(frame, textvariable=status_var, font=('', 12, 'bold')).grid(row=11, column=0, columnspan=3, sticky='w', pady=6)
    log_box = tk.Text(frame, height=12, wrap='word', state='disabled', font=('Menlo', 10))
    log_box.grid(row=12, column=0, columnspan=3, sticky='nsew')
    frame.rowconfigure(12, weight=1)

    def log(text):
        log_box.configure(state='normal')
        log_box.insert('end', text.rstrip() + '\n')
        log_box.see('end')
        log_box.configure(state='disabled')

    def current_model():
        return next(m for m in MODELS if m.name == model_var.get())

    def mismatch():
        info = state['image']
        if not info:
            return 'Elige una imagen.'
        if info.model is None:
            return 'No sé de qué modelo es esta imagen (no trae ningún hardware_id conocido).'
        if info.model != current_model():
            return f'Esta imagen es de un {info.model.name} y elegiste {current_model().name}.'
        if info.signed and info.signature_ok is False:
            return 'La firma de la imagen no es válida: no es un firmware del propietario.'
        return None

    def refresh_state():
        problem = tool_error or mismatch() or ('' if port_var.get() else 'Elige el puerto del equipo.')
        flash_button.configure(state='disabled' if problem or state['busy'] else 'normal')
        if not state['busy']:
            status_var.set(problem or f'Listo para cargar {current_model().name}.')

    def worker(info, model, port, full):
        temporary = None
        try:
            events.put(('status', 'Leyendo el equipo conectado…'))
            try:
                before = read_status(tool_python, port)
                events.put(('before', before))
                reply = queue.Queue()
                events.put(('confirm', (before, reply)))
                if not reply.get():
                    events.put(('done', (False, 'Cancelado: no se cargó nada.')))
                    return
            except (FlasherError, subprocess.SubprocessError, ValueError) as error:
                events.put(('log', f'No pude leer el equipo antes de cargar ({error}). Puede ser una placa nueva; sigo.'))
            boot = boot_app0()
            if not boot:
                raise FlasherError('No encuentro boot_app0.bin (viene con PlatformIO).')
            bootloader = companion('bootloader.bin', info.path, model) if full else None
            partitions = companion('partitions.bin', info.path, model) if full else None
            # A la flash va la imagen sin los 72 bytes de la firma, como en una OTA.
            handle, temporary = tempfile.mkstemp(suffix='.bin', prefix='tresvizo-app-')
            with os.fdopen(handle, 'wb') as out:
                out.write(info.app)
            command = flash_command(esptool, port, temporary, boot, full, bootloader, partitions)
            events.put(('log', '$ ' + ' '.join(command)))
            events.put(('status', f'Cargando {model.name}… no desconectes el cable.'))
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            buffer = b''
            while True:
                chunk = process.stdout.read(64)
                if not chunk:
                    break
                buffer += chunk
                parts = re.split(rb'[\r\n]', buffer)
                buffer = parts.pop()
                for part in parts:
                    line = part.decode(errors='replace').strip()
                    if not line:
                        continue
                    percent = parse_progress(line)
                    if percent is not None:
                        events.put(('progress', percent))
                    else:
                        events.put(('log', line))
            if process.wait() != 0:
                raise FlasherError('esptool no terminó bien: mira el registro. Revisa el cable y que ningún otro programa tenga el puerto abierto.')
            events.put(('progress', 100))
            events.put(('status', 'Cargado. Esperando a que el equipo arranque…'))
            time.sleep(BOOT_WAIT_SECONDS)
            try:
                after = read_status(tool_python, port)
            except (FlasherError, subprocess.SubprocessError, ValueError) as error:
                events.put(('done', (None, f'Cargado, pero no pude leer el equipo después ({error}). Desconéctalo, vuelve a conectarlo y compruébalo desde la app.')))
                return
            name = after.get('product_name') or 'MeridianV'
            version = after.get('firmware_version') or '—'
            same_model = status_model(after) == model
            same_version = info.version is None or version == info.version
            if same_model and same_version:
                events.put(('done', (True, f'Listo: el equipo es un {name} con firmware {version}.')))
            else:
                events.put(('done', (False, f'El equipo contesta como {name} {version}; se esperaba {model.name} {info.version or ""}. Revisa la imagen.')))
        except FlasherError as error:
            events.put(('done', (False, str(error))))
        except Exception as error:  # nada se queda colgado sin decirlo
            events.put(('done', (False, f'Error inesperado: {error}')))
        finally:
            if temporary:
                try:
                    os.remove(temporary)
                except OSError:
                    pass

    def start_flash():
        info, model, port, full = state['image'], current_model(), port_var.get(), full_var.get()
        if mismatch() or not port:
            return
        detail = 'instalación completa' if full else 'actualización'
        if not messagebox.askokcancel('Cargar firmware', f'Vas a cargar {model.name} {info.version or ""} en {port} ({detail}).\n\n¿Seguir?'):
            return
        state['busy'] = True
        progress['value'] = 0
        refresh_state()
        threading.Thread(target=worker, args=(info, model, port, full), daemon=True).start()

    flash_button.configure(command=start_flash)

    def pump():
        try:
            while True:
                kind, value = events.get_nowait()
                if kind == 'log':
                    log(value)
                elif kind == 'status':
                    status_var.set(value)
                    log(value)
                elif kind == 'progress':
                    progress['value'] = value
                elif kind == 'before':
                    log(f'Equipo conectado: {value.get("product_name") or "MeridianV"} con firmware {value.get("firmware_version") or "—"}.')
                elif kind == 'confirm':
                    before, reply = value
                    was = status_model(before)
                    target = current_model()
                    if was and was != target:
                        reply.put(messagebox.askyesno(
                            'Otro modelo',
                            f'El equipo conectado es un {was.name} y vas a cargarle firmware de {target.name}.\n\n'
                            'Los ajustes guardados se conservan. ¿Cargarlo igual?'))
                    else:
                        reply.put(True)
                elif kind == 'done':
                    ok, message = value
                    state['busy'] = False
                    status_var.set(message)
                    log(message)
                    refresh_state()
                    status_var.set(message)
                    if ok is True:
                        messagebox.showinfo('Firmware cargado', message)
                    elif ok is False:
                        messagebox.showerror('No se completó', message)
                    else:
                        messagebox.showwarning('Firmware cargado', message)
        except queue.Empty:
            pass
        root.after(100, pump)

    if tool_error:
        log(tool_error)
    refresh_ports()
    refresh_state()
    pump()
    root.mainloop()


if __name__ == '__main__':
    run_gui()
