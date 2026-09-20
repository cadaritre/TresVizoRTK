"""Sesiones de banco en disco local: cola acotada, cierre durable y recuperación."""
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import shutil
import threading
import time
import uuid
import subprocess


class Sessions:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock = threading.RLock()
        self.active = None
        self.jobs = queue.Queue(maxsize=256)
        self.worker = None
        self.error = None
        self.conversions = set()
        # Los archivos .part se conservan: nunca se anuncian como sesiones cerradas.

    def _save(self, record):
        folder = self.root / record['id']
        temp = folder / 'manifest.tmp'
        with open(temp, 'w') as file:
            os.chmod(temp, 0o600)
            json.dump(record, file, ensure_ascii=False, allow_nan=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp, folder / 'manifest.json')
        fd = os.open(folder, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def start(self, name, metadata):
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 64 or any(ord(c) < 32 for c in name):
            raise ValueError('Nombre de sesión inválido (1–64 caracteres).')
        with self.lock:
            if self.active:
                raise ValueError('Ya hay una sesión abierta. Detén y cierra primero.')
            if shutil.disk_usage(self.root).free < 64 * 1024 * 1024:
                raise ValueError('Menos de 64 MB libres en la Mac.')
            identity = uuid.uuid4().hex
            folder = self.root / identity
            folder.mkdir(mode=0o700)
            self.error = None
            self.active = {'id': identity, 'name': name.strip(), 'state': 'recording',
                           'storage': 'mac_disk', 'format': 'receiver_stream', 'rinex_validated': False,
                           'started_unix_s': time.time(), 'bytes': 0, 'dropped_bytes': 0,
                           'metadata': metadata}
            self._save(self.active)
            self.jobs = queue.Queue(maxsize=256)
            self.worker = threading.Thread(target=self._write, args=(folder,), daemon=True)
            self.worker.start()
            return dict(self.active)

    def append(self, data):
        with self.lock:
            if not self.active or self.active['state'] != 'recording':
                return
            try:
                self.jobs.put_nowait(bytes(data))
            except queue.Full:
                self.active['dropped_bytes'] += len(data)

    def _write(self, folder):
        digest = hashlib.sha256()
        try:
            fd = os.open(folder / 'stream.part', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'wb') as file:
                synced = time.monotonic()
                while True:
                    data = self.jobs.get()
                    if data is None:
                        break
                    file.write(data)
                    digest.update(data)
                    with self.lock:
                        self.active['bytes'] += len(data)
                    if time.monotonic() - synced >= 2:
                        file.flush()
                        os.fsync(file.fileno())
                        synced = time.monotonic()
                file.flush()
                os.fsync(file.fileno())
            with self.lock:
                self.active['sha256'] = digest.hexdigest()
        except OSError as error:
            with self.lock:
                self.error = type(error).__name__
                self.active['state'] = 'error'

    def stop(self):
        with self.lock:
            if not self.active:
                return {'state': 'idle', 'storage': 'mac_disk'}
            self.active['state'] = 'closing'
            worker = self.worker
        while worker.is_alive():
            try:
                self.jobs.put(None, timeout=.2)
                break
            except queue.Full:
                pass
        worker.join(timeout=10)
        with self.lock:
            if worker.is_alive():
                raise TimeoutError('El disco todavía está cerrando la sesión.')
            record = dict(self.active)
            record['ended_unix_s'] = time.time()
            record['state'] = 'partial' if self.error or record['dropped_bytes'] else 'closed'
            record['error'] = self.error
            folder = self.root / record['id']
            if not self.error:
                os.replace(folder / 'stream.part', folder / 'stream.bin')
            self._save(record)
            self.active = None
            return record

    def catalog(self):
        rows = []
        with self.lock:
            for path in sorted(self.root.glob('*/manifest.json'), reverse=True)[:200]:
                try:
                    record = json.loads(path.read_text())
                    if self.active and record['id'] == self.active['id']:
                        record = dict(self.active)
                    elif record['state'] in ('recording', 'closing', 'error'):
                        record['state'] = 'interrupted'
                        record['bytes'] = (path.parent / 'stream.part').stat().st_size if (path.parent / 'stream.part').exists() else 0
                    if record.get('conversion_state') == 'running' and record['id'] not in self.conversions:
                        record['conversion_state'] = 'interrupted'
                    rows.append(record)
                except (ValueError, KeyError, OSError):
                    continue
        return {'storage': 'mac_disk', 'sessions': rows, 'active': dict(self.active) if self.active else None}

    def export(self, identity, artifact):
        if not re.fullmatch(r'[0-9a-f]{32}', identity) or artifact not in ('manifest.json', 'stream.bin', 'stream.part', 'observations.obs', 'navigation.nav'):
            raise ValueError('Archivo inválido.')
        with self.lock:
            if self.active and self.active['id'] == identity:
                raise ValueError('Detén y cierra la sesión antes de descargar.')
            folder = self.root / identity
            manifest = json.loads((folder / 'manifest.json').read_text())
            if artifact == 'stream.bin' and manifest.get('state') not in ('closed', 'partial'):
                raise ValueError('Sesión sin cierre confirmado.')
            if artifact in ('observations.obs', 'navigation.nav') and not manifest.get('rinex_available'):
                raise ValueError('Conversión no disponible.')
            return folder / artifact

    def convert(self, identity, executable):
        with self.lock:
            source = self.export(identity, 'stream.bin')
            folder = source.parent
            manifest = json.loads((folder / 'manifest.json').read_text())
            if identity in self.conversions or manifest.get('rinex_available'):
                return {'state': manifest.get('conversion_state', 'complete')}
            if not Path(executable).is_file():
                raise ValueError('Instala el conversor RTKLIB documentado en .cache/rtklib/convbin.')
            if self.conversions: raise ValueError('Ya hay una conversión en curso. Espera a que termine.')
            self.conversions.add(identity)
            manifest['conversion_state'] = 'running'
            self._save(manifest)
            threading.Thread(target=self._convert, args=(folder, str(executable)), daemon=True).start()
            return {'state': 'running'}

    def _convert(self, folder, executable):
        workspace = folder / ('conversion-' + uuid.uuid4().hex)
        workspace.mkdir(mode=0o700)
        manifest = json.loads((folder / 'manifest.json').read_text())
        try:
            obs, nav = workspace / 'observations.obs', workspace / 'navigation.nav'
            command = [executable, '-r', 'unicore', '-v', '3.04', '-o', str(obs), '-n', str(nav), str(folder / 'stream.bin')]
            with (workspace / 'conversion.log').open('wb') as log:
                subprocess.run(command, stdout=log, stderr=log, check=True, timeout=120)
            def inspect(path):
                header = False; epochs = records = 0; systems = set()
                with path.open() as file:
                    for line in file:
                        if 'RINEX VERSION / TYPE' in line and not line.startswith('     3.04'):
                            raise ValueError('Versión RINEX inesperada')
                        if 'END OF HEADER' in line: header = True; continue
                        if header and line.startswith('>'): epochs += 1
                        elif header and line[:1] in 'GRECJSI' and line[1:3].isdigit():
                            records += 1; systems.add(line[0])
                return header, epochs, records, sorted(systems)
            oh, epochs, _, systems = inspect(obs)
            nh, _, nav_records, nav_systems = inspect(nav)
            if not oh or not nh or epochs == 0 or nav_records == 0:
                raise ValueError('Sin observaciones o efemérides suficientes en esta captura')
            os.chmod(obs,0o600);os.chmod(nav,0o600)
            os.replace(obs,folder / 'observations.obs');os.replace(nav,folder / 'navigation.nav')
            manifest.update(conversion_state='complete',rinex_available=True,
                conversion={'rinex_version':'3.04','observation_epochs':epochs,'navigation_records':nav_records,
                            'observation_systems':systems,'navigation_systems':nav_systems,
                            'ppk_accuracy_validated':False,
                            'warning':'Metadatos de antena/altura sin confirmar. La conversión no valida exactitud ni cobertura de todas las señales.'})
            build = Path(executable).parent / 'build.json'
            if build.exists(): manifest['conversion']['converter_build'] = json.loads(build.read_text())
        except (OSError, ValueError, subprocess.SubprocessError):
            manifest.update(conversion_state='failed',rinex_available=False,
                            conversion_error='Conversión fallida o sin observaciones/efemérides. Se conserva el original.')
        with self.lock:
            self._save(manifest)
            self.conversions.discard(manifest['id'])
