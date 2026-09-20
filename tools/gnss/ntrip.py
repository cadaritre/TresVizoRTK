"""NTRIP de banco v1: cliente, publicador y caster de una fuente, con RTCM validado.

No expone credenciales en estado. TLS del cliente/publicador usa verificación del sistema.
"""
import base64
import hmac
import queue
import re
import socket
import socketserver
import ssl
import threading
import time
from .rtcm import Framer


def clean(value, label, pattern=r'[!-~]{1,128}'):
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise ValueError('Campo inválido: ' + label)
    return value


def credentials(user, password):
    clean(user, 'usuario', r'[^:\r\n\x00-\x1f]{1,64}')
    clean(password, 'contraseña', r'[^\r\n\x00-\x1f]{8,128}')
    return 'Basic ' + base64.b64encode((user + ':' + password).encode()).decode()


def read_header(connection):
    # Leer exactamente el encabezado, preservando el comienzo binario del flujo.
    data = bytearray()
    while len(data) < 8192:
        byte = connection.recv(1)
        if not byte: raise OSError('Conexión cerrada durante negociación')
        data.extend(byte)
        # NTRIP v1 ICY puede terminar en una sola línea.
        if data == b'ICY 200 OK\r\n' or data.endswith(b'\r\n\r\n'):
            return bytes(data)
    raise ValueError('Encabezado NTRIP demasiado grande')


class Transport:
    def __init__(self, consumer):
        self.consumer = consumer
        self.stop_event = threading.Event()
        self.worker = None
        self.connection = None
        self.output = queue.Queue(maxsize=64)
        self.state = {'state': 'stopped', 'bytes': 0, 'frames': 0, 'crc_errors': 0, 'dropped_frames': 0}
        self.lock = threading.Lock()

    def start(self, config):
        if not isinstance(config, dict) or set(config) - {'role','host','port','mountpoint','username','password','tls'}:
            raise ValueError('Configuración NTRIP inválida')
        role = config.get('role')
        if role not in ('input', 'publisher'):raise ValueError('Rol NTRIP inválido')
        host = clean(config.get('host'), 'host', r'[A-Za-z0-9.:-]{1,253}')
        mount = clean(config.get('mountpoint'), 'mountpoint', r'[A-Za-z0-9_.-]{1,64}')
        port = config.get('port')
        if type(port) is not int or not 1 <= port <= 65535:raise ValueError('Puerto inválido')
        if type(config.get('tls')) is not bool:raise ValueError('TLS debe ser booleano')
        auth = credentials(config.get('username'), config.get('password'))
        if role == 'publisher':clean(config['password'], 'contraseña fuente', r'[!-~]{8,128}')
        self.stop()
        self.stop_event.clear()
        self.output = queue.Queue(maxsize=64)
        self.worker = threading.Thread(target=self._run, args=(dict(config),auth), daemon=True)
        self.worker.start()
        return self.snapshot()

    def _run(self, config, auth):
        delay = 1
        while not self.stop_event.is_set():
            try:
                self.state['state'] = 'connecting'
                connection = socket.create_connection((config['host'], config['port']), timeout=3)
                self.connection = connection
                if config['tls']:
                    connection = ssl.create_default_context().wrap_socket(connection, server_hostname=config['host'])
                    self.connection = connection
                if config['role'] == 'input':
                    request = f"GET /{config['mountpoint']} HTTP/1.0\r\nUser-Agent: NTRIP TresVizoBench/1\r\nAuthorization: {auth}\r\n\r\n"
                else:
                    request = f"SOURCE {config['password']} /{config['mountpoint']}\r\nSource-Agent: NTRIP TresVizoBench/1\r\n\r\n"
                connection.sendall(request.encode())
                response = read_header(connection)
                first = response.split(b'\r\n')[0]
                if first not in (b'ICY 200 OK', b'HTTP/1.0 200 OK', b'HTTP/1.1 200 OK'):
                    raise ValueError('Autenticación o mountpoint rechazado')
                if b'transfer-encoding:' in response.lower():
                    raise ValueError('Este adaptador v1 no admite transferencia chunked')
                connection.settimeout(1)
                self.state.pop('error',None)
                self.state['state'] = 'streaming'
                delay = 1
                parser = Framer()
                last = time.monotonic()
                while not self.stop_event.is_set():
                    if config['role'] == 'input':
                        try: data = connection.recv(8192)
                        except socket.timeout:
                            if time.monotonic()-last > 10:raise OSError('Flujo sin datos')
                            continue
                        if not data:raise OSError('Fuente desconectada')
                        last = time.monotonic()
                        for frame in parser.feed(data):
                            self.consumer(frame)
                            self.state['frames'] += 1;self.state['bytes'] += len(frame)
                        self.state['crc_errors'] = parser.rejected
                    else:
                        try: stamp, frame = self.output.get(timeout=.5)
                        except queue.Empty:continue
                        if time.monotonic()-stamp > 2:
                            self.state['dropped_frames'] += 1;continue
                        connection.sendall(frame)
                        self.state['frames'] += 1;self.state['bytes'] += len(frame)
                    self.state['last_frame_monotonic_s'] = time.monotonic()
            except (OSError, ValueError):
                self.state['state'] = 'reconnecting'
                self.state['error'] = 'No se pudo mantener el flujo; revisa red, TLS, credenciales y mountpoint.'
            finally:
                if self.connection:
                    self.connection.close();self.connection = None
            if self.stop_event.wait(delay):break
            delay = min(delay*2,30)
        self.state['state'] = 'stopped'

    def publish(self, frame):
        if not self.worker or not self.worker.is_alive():return
        try:self.output.put_nowait((time.monotonic(),frame))
        except queue.Full:self.state['dropped_frames'] += 1

    def stop(self):
        self.stop_event.set()
        if self.connection:
            try:self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:pass
        if self.worker:
            self.worker.join(timeout=5)
            if self.worker.is_alive():raise TimeoutError('Transporte todavía está cerrando')
        self.state['state'] = 'stopped'

    def snapshot(self):
        return dict(self.state)


class LocalCaster:
    """Un mountpoint, una fuente externa y hasta dos rovers; colas por cliente."""
    def __init__(self, host, port, mountpoint, username, password, source_password, source="external"):
        if source not in ("external", "gps"): raise ValueError("Fuente del caster inválida")
        self.source_kind = source
        self.connections = set()
        self.mount = clean(mountpoint,'mountpoint',r'[A-Za-z0-9_.-]{1,64}')
        self.auth = credentials(username,password)
        self.source_password = clean(source_password,'clave fuente',r'[!-~]{8,128}')
        self.clients = set()
        self.lock = threading.Lock()
        self.source_active = False
        self.frames = self.dropped = 0
        owner = self
        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                q = None;source = False
                self.request.settimeout(3)
                with owner.lock: owner.connections.add(self.request)
                try:
                    header = read_header(self.request).decode('ascii')
                    lines=header.split('\r\n'); parts=lines[0].split(' ')
                    headers={line.split(':',1)[0].lower():line.split(':',1)[1].strip() for line in lines[1:] if ':' in line}
                    if len(parts)==3 and parts[0]=='SOURCE':
                        if owner.source_kind != 'external' or parts[2]!='/'+owner.mount or not hmac.compare_digest(parts[1],owner.source_password):
                            self.request.sendall(b'HTTP/1.0 401 Unauthorized\r\n\r\n');return
                        with owner.lock:
                            if owner.source_active:
                                self.request.sendall(b'HTTP/1.0 409 Conflict\r\n\r\n');return
                            owner.source_active=source=True
                        self.request.sendall(b'ICY 200 OK\r\n')
                        framer=Framer()
                        while True:
                            data=self.request.recv(8192)
                            if not data:break
                            for frame in framer.feed(data):owner.broadcast(frame)
                    elif len(parts)==3 and parts[0]=='GET':
                        if not hmac.compare_digest(headers.get('authorization',''),owner.auth):
                            self.request.sendall(b'HTTP/1.0 401 Unauthorized\r\n\r\n');return
                        if parts[1]=='/':
                            table=f'STR;{owner.mount};TresVizo;RTCM 3;;;;;0;0;0;0;;none;B;N;0;\r\nENDSOURCETABLE\r\n'.encode()
                            self.request.sendall(b'SOURCETABLE 200 OK\r\nContent-Type: gnss/sourcetable\r\nContent-Length: '+str(len(table)).encode()+b'\r\n\r\n'+table);return
                        if parts[1]!='/'+owner.mount:
                            self.request.sendall(b'HTTP/1.0 404 Not Found\r\n\r\n');return
                        with owner.lock:
                            if len(owner.clients)>=2:
                                self.request.sendall(b'HTTP/1.0 503 Busy\r\n\r\n');return
                            q=queue.Queue(maxsize=32);owner.clients.add(q)
                        self.request.sendall(b'ICY 200 OK\r\n')
                        while True:
                            try:stamp,frame=q.get(timeout=5)
                            except queue.Empty:break
                            if time.monotonic()-stamp>2:owner.dropped+=1;continue
                            self.request.sendall(frame)
                    else:self.request.sendall(b'HTTP/1.0 400 Bad Request\r\n\r\n')
                except (OSError, ValueError, UnicodeError):pass
                finally:
                    with owner.lock:
                        owner.connections.discard(self.request)
                        if q is not None:owner.clients.discard(q)
                        if source:owner.source_active=False
        class Server(socketserver.ThreadingTCPServer):
            allow_reuse_address=True
            daemon_threads=True
            slots=threading.BoundedSemaphore(16)
            def process_request(self, request, address):
                if not self.slots.acquire(False):
                    self.shutdown_request(request);return
                try:super().process_request(request,address)
                except Exception:self.slots.release();raise
            def process_request_thread(self, request, address):
                try:super().process_request_thread(request,address)
                finally:self.slots.release()
        self.server=Server((host,port),Handler)
        self.worker=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.worker.start()

    def broadcast(self,frame):
        with self.lock:
            self.frames+=1
            for q in self.clients:
                try:q.put_nowait((time.monotonic(),frame))
                except queue.Full:self.dropped+=1

    def close(self):
        self.server.shutdown()
        with self.lock:
            for connection in self.connections:
                try: connection.shutdown(socket.SHUT_RDWR)
                except OSError: pass
        self.server.server_close()

    def snapshot(self):
        with self.lock:return {'state':'listening','host':self.server.server_address[0],
                              'port':self.server.server_address[1], 'mountpoint':self.mount,
                              'source_kind':self.source_kind,'clients':len(self.clients),'source_connected':self.source_active,
                              'frames':self.frames,'dropped_frames':self.dropped}
