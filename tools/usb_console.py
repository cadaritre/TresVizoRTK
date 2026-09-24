#!/usr/bin/env python3
"""Consola y puente local USB para TresVizo RTK; no simula el instrumento."""
import argparse
from collections import deque
import json
import mimetypes
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from gnss.receiver import Receiver

import serial
from serial.tools import list_ports

# TIOCEXCL solo existe en POSIX. En Windows el puerto ya se abre en exclusiva y
# pyserial rechaza una segunda apertura, así que no hace falta refuerzo.
try:
    import fcntl
    import termios
except ImportError:  # Windows
    fcntl = termios = None

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "firmware" / "esp32" / "web"
MAX_REQUEST = 1024


def detect_port():
    ports = [p.device for p in list_ports.comports() if p.vid == 0x303A and p.pid == 0x1001]
    if len(ports) != 1:
        raise RuntimeError("Especifica --port: debe haber exactamente un ESP32 USB conectado.")
    return ports[0]


class Instrument:
    def __init__(self, port):
        self.port = port
        self.connection = None
        self.sequence = 0
        self.lock = threading.Lock()
        self.boot_diagnostics = deque(maxlen=12)

    def close(self):
        if self.connection:
            self.connection.close()
        self.connection = None

    def _open(self):
        if self.connection and self.connection.is_open:
            return
        connection = serial.Serial(baudrate=115200, timeout=0.25, write_timeout=2, exclusive=True)
        connection.dtr = False
        connection.rts = False
        connection.port = self.port
        connection.open()
        if fcntl is not None:
            try:
                # flock de pyserial es consultivo; impedir también nuevas aperturas
                # del monitor serie que podrían cambiar DTR/RTS durante una OTA.
                fcntl.ioctl(connection.fileno(), termios.TIOCEXCL)
            except OSError:
                connection.close()
                raise
        self.connection = connection

    def _exchange(self, method, path, body=None, key=None):
        self._open()
        self.sequence += 1
        payload = {"id": self.sequence, "method": method, "path": path}
        if key is not None:
            payload["key"] = key
        if body is not None:
            payload["body"] = body
        encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode()
        if len(encoded) > MAX_REQUEST:
            return {"status": 413, "body": {"error": "request_too_large", "message": "La solicitud USB supera 1024 bytes."}}
        self.connection.write(encoded + b"\n")
        deadline = time.monotonic() + (15 if path.startswith("/api/update/") else 4)
        while time.monotonic() < deadline:
            line = self.connection.read_until(b"\n", 8192)
            if not line.startswith(b"{"):
                if any(marker in line for marker in (b"Guru",b"panic",b"rst:",b"assert",b"watchdog",b"Backtrace",b"TresVizo RTK")):
                    self.boot_diagnostics.append(line.decode(errors="replace").strip()[:256])
                continue
            try:
                response = json.loads(line)
            except (ValueError, UnicodeError):
                continue
            if response.get("id") == self.sequence:
                return response
        raise TimeoutError("El ESP32 no respondió. Verifica el cable y cierra otros monitores serie.")

    def request(self, method, path, body=None):
        with self.lock:
            try:
                # El instrumento ya no exige clave de panel: la única credencial
                # es la del Wi-Fi propio, y por USB no hace falta ni esa.
                return self._exchange(method, path, body)
            except (serial.SerialException, OSError, TimeoutError):
                self.close()
                raise


def serve(device, port, gps=None):
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    allowed_origins = {f"http://{host}" for host in allowed_hosts}
    assets = {"/device.js": WEB / "device.js", "/update.js": WEB / "update.js", "/bench.js": WEB / "bench.js", "/": WEB / "index.html", "/app.css": WEB / "app.css", "/app.js": WEB / "app.js", "/assets/tresvizo-logo.png": WEB / "assets" / "tresvizo-logo.png"}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass  # no registrar solicitudes que puedan contener ajustes privados

        def respond(self, code, body, mime="application/json; charset=utf-8"):
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(data)

        def handle_request(self):
            if self.headers.get("Host") not in allowed_hosts:
                return self.respond(403, {"error": "invalid_host"})
            origin = self.headers.get("Origin")
            if origin and origin not in allowed_origins:
                return self.respond(403, {"error": "invalid_origin"})
            if self.command == "GET" and self.path in assets:
                path = assets[self.path]
                mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
                return self.respond(200, path.read_bytes(), mime)
            path = urlsplit(self.path).path
            if path.startswith("/api/bench/"):
                if gps is None:
                    return self.respond(404, {"error": "bench_not_enabled"})
                if path.startswith("/api/bench/file/") and self.command == "GET":
                    if self.headers.get("Sec-Fetch-Site") != "same-origin" and self.headers.get("X-TresVizo-Client") != "portal":
                        return self.respond(403, {"error": "same_origin_required"})
                    try:
                        _, _, _, _, identity, artifact = path.split("/")
                        file = gps.sessions.export(identity, artifact)
                        size = file.stat().st_size
                        start, end = 0, size - 1
                        partial = self.headers.get("Range")
                        if partial:
                            import re
                            match = re.fullmatch(r"bytes=(\d+)-(\d*)", partial)
                            if not match: return self.respond(416, {"error": "invalid_range"})
                            start = int(match[1]); end = min(int(match[2]), end) if match[2] else end
                            if not 0 <= start <= end < size: return self.respond(416, {"error": "invalid_range"})
                        self.send_response(206 if partial else 200)
                        self.send_header("Content-Type", "application/octet-stream")
                        self.send_header("Content-Disposition", f'attachment; filename="{identity}-{artifact}"')
                        self.send_header("Content-Length", str(max(0, end-start+1)))
                        self.send_header("Accept-Ranges", "bytes")
                        self.send_header("Cache-Control", "no-store")
                        if partial: self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                        self.end_headers()
                        with file.open("rb") as source:
                            source.seek(start)
                            remaining = end-start+1
                            while remaining > 0:
                                chunk = source.read(min(65536, remaining))
                                if not chunk: break
                                self.wfile.write(chunk); remaining -= len(chunk)
                        return
                    except (ValueError, OSError):
                        return self.respond(404, {"error": "file_unavailable"})
                if self.headers.get("X-TresVizo-Client") != "portal":
                    return self.respond(403, {"error": "client_header_required"})
                try:
                    if path == "/api/bench/gnss" and self.command == "GET":
                        since = int(parse_qs(urlsplit(self.path).query).get("since", ["0"])[0])
                        return self.respond(200, gps.snapshot(max(0, since)))
                    if path == "/api/bench/sessions" and self.command == "GET":
                        return self.respond(200, gps.sessions.catalog())
                    if path in ("/api/bench/action", "/api/bench/base") and self.command == "POST":
                        length = int(self.headers.get("Content-Length", "0"))
                        if self.headers.get("Transfer-Encoding") or not 0 < length <= MAX_REQUEST:
                            return self.respond(413, {"error": "invalid_length"})
                        self.connection.settimeout(5)
                        body = json.loads(self.rfile.read(length))
                        if path == "/api/bench/base":
                            preview = device.request("POST", "/api/base/plan", body)
                            if preview["status"] != 200: return self.respond(preview["status"],preview["body"])
                            return self.respond(200,gps.apply_base(preview["body"]["plan"]))
                        return self.respond(200, gps.action(body))
                except (ValueError, UnicodeError) as error:
                    return self.respond(400, {"message": str(error)})
                except (serial.SerialException, OSError, TimeoutError) as error:
                    return self.respond(503, {"message": str(error)})
                return self.respond(404, {"error": "not_found"})
            if self.path not in {"/api/recording", "/api/recording/start", "/api/recording/stop", "/api/recording/read", "/api/recording/sessions", "/api/gnss/control", "/api/base/apply", "/api/ntrip/input", "/api/status", "/api/config", "/api/restart", "/api/operations", "/api/base/plan", "/api/update", "/api/update/begin", "/api/update/chunk", "/api/update/finish", "/api/update/abort", "/api/update/rollback", "/api/corrections/source", "/api/wifi/networks", "/api/wifi/scan", "/api/ble", "/api/gnss/profile", "/api/ntrip/profiles", "/api/ntrip/sourcetable", "/api/ntrip/server", "/api/ntrip/caster", "/api/base/survey"}:
                return self.respond(404, {"error": "not_found"})
            if self.headers.get("X-TresVizo-Client") != "portal":
                return self.respond(403, {"error": "client_header_required"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                return self.respond(400, {"error": "invalid_length"})
            if length < 0 or length > MAX_REQUEST:
                return self.respond(413, {"error": "request_too_large"})
            if self.headers.get("Transfer-Encoding"):
                return self.respond(400, {"error": "unsupported_encoding"})
            try:
                self.connection.settimeout(5)
                raw = self.rfile.read(length)
                body = json.loads(raw) if length else None
                result = device.request(self.command, self.path, body)
                self.respond(result["status"], result["body"])
            except (ValueError, UnicodeError):
                self.respond(400, {"error": "invalid_json", "message": "La solicitud no es JSON válido."})
            except (serial.SerialException, OSError, TimeoutError):
                self.respond(503, {"error": "device_unavailable", "message": "No hay comunicación USB con el ESP32."})

        do_GET = handle_request
        do_PUT = handle_request
        do_POST = handle_request

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Panel USB real: http://127.0.0.1:{port}", flush=True)
    print("Solo accesible desde esta Mac. Ctrl+C para detener. Sin datos simulados.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Puente USB detenido.", flush=True)
    finally:
        server.server_close()
        device.close()
        if gps: gps.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="Puerto USB del ESP32; se detecta si hay uno solo.")
    parser.add_argument("command", choices=["access", "status", "config", "serve"])
    parser.add_argument("--http-port", type=int, default=8765)
    parser.add_argument("--gnss-port", help="Activa banco GNSS USB independiente; nunca se presenta como UART del ESP32.")
    args = parser.parse_args()
    device = Instrument(args.port or detect_port())
    try:
        if args.command == "serve":
            gps = Receiver(args.gnss_port, ROOT / "captures" / "local" / "sessions") if args.gnss_port else None
            serve(device, args.http_port, gps)
        elif args.command == "access":
            result = device.request("GET", "/api/access")
            body = result.get("body", {})
            # La contraseña del Wi-Fi propio es la única credencial del
            # equipo. Se cambia desde Configuración, no desde aquí.
            print(f'Red Wi-Fi                : {body.get("ap_ssid")}')
            print(f'Contraseña Wi-Fi         : {body.get("ap_password")}')
            print(f'Panel por su red propia  : {body.get("ap_url")}')
            station = body.get("station_url")
            if station:
                print(f'Panel en {body.get("station_ssid"):<15}: {station}')
            else:
                print('Panel en red externa     : sin conexion')
            print(f'Por nombre               : {body.get("mdns_url")}')
            print("\nSalida privada: no la subas al repositorio ni la compartas.")
        else:
            result = device.request("GET", f"/api/{args.command}")
            print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        device.close()


if __name__ == "__main__":
    main()
