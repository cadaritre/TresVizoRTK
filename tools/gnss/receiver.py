"""Dueño único del USB GNSS; lectura independiente y comandos con ACK asociado."""
from collections import deque
import copy
import threading
import time
import serial
from .nmea import Parser, checked
from .sessions import Sessions
from .stream import Stream
from .ntrip import Transport, LocalCaster

PROFILE = ['GPGGA COM3 0.1', 'GPGST COM3 0.1', 'GPRMC COM3 0.1', 'GPGSV COM3 1']
RAW_PROFILE = ['OBSVMB COM3 1', 'GPSEPHB COM3 30', 'GLOEPHB COM3 30',
               'GALEPHB COM3 30', 'BDSEPHB COM3 30', 'BD3EPHB COM3 30']


class Receiver:
    def __init__(self, port, root):
        self.port = port
        self.parser = Parser()
        self.sessions = Sessions(root)
        self.lock = threading.RLock()
        self.operation = threading.Lock()
        self.condition = threading.Condition(self.lock)
        self.serial = None
        self.stop_event = threading.Event()
        self.generation = 0
        self.responses = deque(maxlen=100)
        self.error = None
        self.mode = None
        self.last_operation = None
        self.bytes = 0
        self.stream = Stream()
        self.rtcm_frames = 0
        self.ntrip = Transport(self.write_rtcm)
        self.caster = None
        self.height_reference = "receiver_msl"
        self.raw_profile = False
        self.worker = threading.Thread(target=self._read, daemon=True)
        self.worker.start()

    def _read(self):
        while not self.stop_event.is_set():
            try:
                if self.serial is None:
                    connection = serial.Serial(baudrate=115200, timeout=.05, write_timeout=.5, exclusive=True)
                    connection.dtr = connection.rts = False
                    connection.port = self.port
                    connection.open()
                    with self.lock:
                        self.serial = connection
                        self.error = None
                        self.parser = Parser()
                        self.mode = None
                        self.raw_profile = False
                        self.generation += 1
                    self.stream = Stream()
                data = self.serial.read(4096)
                if not data:
                    continue
                self.sessions.append(data)
                with self.lock:
                    self.bytes += len(data)
                    for kind, line in self.stream.feed(data):
                        if kind == 'rtcm':
                            self.rtcm_frames += 1
                            self.ntrip.publish(line)
                            if self.caster and self.caster.source_kind == "gps": self.caster.broadcast(line)
                            continue
                        if line.startswith((b'$command,', b'$CONFIG,', b'#MODE,')):
                            try:
                                # MODE y ACK incluyen el carácter inicial; NMEA lo excluye.
                                if line.startswith(b'#'):
                                    body, crc = line[1:].rsplit(b'*', 1)
                                    value = ord('#')
                                    for b in body: value ^= b
                                    if len(crc) != 2 or value != int(crc, 16):
                                        raise ValueError('checksum')
                                    message = body.decode('ascii')
                                else:
                                    message = checked(line, include_start=True)
                                self.responses.append((time.monotonic(), message))
                                self.condition.notify_all()
                                if message.startswith('MODE,'):
                                    self.mode = message.split(';', 1)[1].rstrip(',')
                            except (ValueError, UnicodeError, IndexError):
                                pass
                        elif line.startswith(b'$'):
                            self.parser.feed(line)
            except (serial.SerialException, OSError):
                with self.lock:
                    if self.serial:
                        self.serial.close()
                    self.serial = None
                    self.error = 'GPS USB desconectado o puerto ocupado por otro programa.'
                    self.mode = None
                    self.condition.notify_all()
                self.stop_event.wait(1)

    def _command(self, command, query_prefix=None):
        with self.condition:
            if not self.serial:
                raise ValueError('GPS USB no disponible.')
            generation = self.generation
            started = time.monotonic()
            self.serial.write((command + '\r\n').encode('ascii'))
            deadline = started + 3
            ack = None
            lines = []
            while time.monotonic() < deadline:
                if generation != self.generation or not self.serial:
                    raise ValueError('GPS desconectado durante el comando.')
                recent = [message for stamp, message in self.responses if stamp >= started]
                matches = [m for m in recent if m.startswith('command,' + command + ',response: ')]
                if matches:
                    ack = matches[-1].split(',response: ', 1)[1]
                    if ack != 'OK':
                        raise ValueError('Receptor rechazó ' + command.split()[0] + ': ' + ack)
                lines = [m for m in recent if query_prefix and m.startswith(query_prefix)]
                if ack and (not query_prefix or lines):
                    return {'command': command, 'ack': True, 'readback': lines}
                self.condition.wait(.05)
            raise TimeoutError('Sin confirmación del receptor para ' + command.split()[0] + '. Estado incierto; consulta antes de repetir.')

    def action(self, body):
        if not isinstance(body, dict) or set(body) - {'action', 'name', 'config', 'session_id'}:
            raise ValueError('Operación inválida.')
        if 'config' in body and not isinstance(body['config'],dict):
            raise ValueError('La configuración debe ser un objeto.')
        action = body.get('action')
        with self.operation:
            if action == 'ntrip_stop':
                self.ntrip.stop()
                return self.ntrip.snapshot()
            if action == 'caster_stop':
                if self.caster: self.caster.close(); self.caster = None
                return {'state': 'stopped'}
            if action == 'ntrip_start':
                config = body.get('config', {})
                if config.get('role') == 'publisher' and (not self.mode or not self.mode.startswith('MODE BASE')):
                    raise ValueError('Consulta y configura modo base antes de publicar RTCM.')
                if config.get('role') == 'input' and self.mode != 'MODE ROVER SURVEY':
                    raise ValueError('Consulta modo rover antes de enviar correcciones al GPS.')
                return self.ntrip.start(config)
            if action == 'caster_start':
                config = body.get('config', {})
                if set(config) != {'host','port','mountpoint','username','password','source_password','source'}:
                    raise ValueError('Configuración del caster incompleta.')
                if config['host'] not in ('127.0.0.1','0.0.0.0') or type(config['port']) is not int or not 1024 <= config['port'] <= 65535:
                    raise ValueError('Dirección o puerto del caster inválido.')
                if config['source'] == 'gps' and (not self.mode or not self.mode.startswith('MODE BASE')):
                    raise ValueError('Configura el GPS como base antes de usarlo como fuente del caster.')
                if self.caster: raise ValueError('Detén el caster antes de reconfigurarlo.')
                self.caster = LocalCaster(**config)
                return self.caster.snapshot()
            if action == 'convert':
                executable = self.sessions.root.parents[2] / '.cache' / 'rtklib' / 'convbin'
                return self.sessions.convert(body.get('session_id',''), executable)
            if action == 'record_stop':
                return self.sessions.stop()
            if action == 'record_start':
                snapshot = self.snapshot()
                if snapshot['state'] != 'receiving':
                    raise ValueError('No llegan datos GNSS vigentes.')
                return self.sessions.start(body.get('name', ''), {'source': 'mac_usb', 'port': self.port,
                    'raw_profile_acknowledged': self.raw_profile, 'mode': self.mode,
                    'initial_solution': snapshot['solution'], 'antenna_model': 'Helix sin calibración confirmada',
                    'ppk_ready': False})
            if self.sessions.active and action != 'query_mode':
                raise ValueError('Cierra la grabación antes de cambiar el receptor.')
            if action == 'query_mode':
                commands = [('MODE', 'MODE,')]
            elif action == 'telemetry':
                commands = [(c, None) for c in PROFILE]
            elif action == 'rover':
                if self.ntrip.snapshot()['state'] != 'stopped' or self.caster:
                    raise ValueError('Detén los transportes de correcciones antes de cambiar el modo.')
                commands = [('MODE ROVER SURVEY', None), ('CONFIG UNDULATION AUTO', None), ('MODE', 'MODE,')]
            elif action == 'rtcm_profile':
                if not self.mode or not self.mode.startswith('MODE BASE'):
                    raise ValueError('RTCM de salida requiere modo base leído del receptor.')
                commands = [(f'RTCM{identity} COM3 {period}', None) for identity,period in [(1005,10),(1033,10),(1074,1),(1084,1),(1094,1),(1114,1),(1124,1)]]
            elif action == 'raw_profile':
                commands = [(c, None) for c in RAW_PROFILE]
            else:
                raise ValueError('Acción no admitida.')
            results = []
            try:
                for command, prefix in commands:
                    results.append(self._command(command, prefix))
                if action == 'rover' and self.mode != 'MODE ROVER SURVEY':
                    raise ValueError('La lectura de modo no coincide con rover topográfico.')
                if action == 'rover': self.height_reference = 'receiver_msl'
                if action == 'raw_profile':
                    self.raw_profile = True
                self.last_operation = {'action': action, 'state': 'confirmed', 'results': results, 'saved': False}
            except (ValueError, TimeoutError, serial.SerialException, OSError):
                self.last_operation = {'action': action, 'state': 'partial_or_unknown', 'results': results, 'saved': False}
                raise
            return copy.deepcopy(self.last_operation)

    def apply_base(self, plan):
        # Plan normalizado previamente por el validador del firmware; no aceptar comandos libres.
        import math
        with self.operation:
            if self.sessions.active:
                raise ValueError('Cierra la sesión antes de cambiar la base.')
            if self.ntrip.snapshot()['state'] != 'stopped' or self.caster:
                raise ValueError('Detén los transportes de correcciones antes de cambiar el modo.')
            identity = plan['station_id']
            if type(identity) is not int or not 0 <= identity <= 4095:
                raise ValueError('ID de base inválido')
            results = []
            try:
                if plan['method'] == 'known':
                    if plan['datum'].upper().replace(' ','') not in ('WGS84','WGS-84'):
                        raise ValueError('El adaptador inicial exige WGS84; no transforma otros marcos.')
                    lat, lon, height = plan['latitude_deg'], plan['longitude_deg'], plan['arp_ellipsoid_height_m']
                    if not all(type(x) in (int,float) and math.isfinite(x) for x in (lat,lon,height)) or not (-90 <= lat <= 90 and -180 <= lon <= 180 and -30000 <= height <= 30000):
                        raise ValueError('Coordenadas de base inválidas')
                    results.append(self._command('CONFIG UNDULATION 0.0000'))
                    self.height_reference = 'ellipsoidal_user_configured'
                    command = f'MODE BASE {identity} {lat:.11f} {lon:.11f} {height:.4f}'
                elif plan['method'] == 'average':
                    seconds, reuse = plan['average_seconds'], plan['reuse_distance_m']
                    if type(seconds) is not int or not 1 <= seconds <= 3600 or type(reuse) not in (int,float) or not math.isfinite(reuse) or not 0 <= reuse <= 10:
                        raise ValueError('Parámetros de promedio inválidos')
                    command = f'MODE BASE {identity} TIME {seconds} {reuse:.4f}'
                else: raise ValueError('Método de base inválido')
                results.append(self._command(command))
                results.append(self._command('MODE','MODE,'))
                if not self.mode or not self.mode.startswith('MODE BASE'):
                    raise ValueError('Modo base no confirmado por lectura')
                coordinate_readback = False
                if plan['method'] == 'known':
                    deadline = time.monotonic() + 3
                    while time.monotonic() < deadline:
                        current = self.snapshot()['solution']
                        if current.get('latitude_deg') is not None and abs(current['latitude_deg']-lat)<1e-8 and abs(current['longitude_deg']-lon)<1e-8 and current.get('height_m') is not None and abs(current['height_m']-height)<.002:
                            coordinate_readback = True; break
                        time.sleep(.05)
                    if not coordinate_readback: raise ValueError('Comando aceptado, pero coordenadas no verificadas en GGA. No publiques la base todavía.')
                self.last_operation = {'action':'apply_base','state':'confirmed' if coordinate_readback else 'averaging',
                    'results':results,'coordinate_readback':coordinate_readback,'plan':plan,
                    'saveconfig_sent':False,'receiver_may_persist_average':plan['method']=='average'}
            except (ValueError,TimeoutError,OSError):
                self.last_operation = {'action':'apply_base','state':'partial_or_unknown','results':results}
                raise
            return copy.deepcopy(self.last_operation)

    def write_rtcm(self, data):
        with self.lock:
            if not self.serial:
                raise OSError('GPS no disponible')
            self.serial.write(data)

    def snapshot(self, since=0):
        with self.lock:
            result = self.parser.snapshot(since=since)
            if self.serial is None:
                result.update(state='disconnected', solution={}, signals=[], epochs=[])
            if result['solution']: result['solution']['height_reference'] = self.height_reference
            result.update(ntrip=self.ntrip.snapshot(), caster=self.caster.snapshot() if self.caster else {'state':'stopped'}, rtcm_frames=self.rtcm_frames, native_messages=dict(self.stream.native_counts), native_crc_errors=self.stream.native_errors, port=self.port, error=self.error, mode=self.mode, bytes_received=self.bytes,
                          raw_profile_acknowledged=self.raw_profile, last_operation=self.last_operation)
            return result

    def close(self):
        self.ntrip.stop()
        if self.caster: self.caster.close()
        self.stop_event.set()
        self.worker.join(timeout=2)
        self.sessions.stop()
        if self.serial:
            self.serial.close()
