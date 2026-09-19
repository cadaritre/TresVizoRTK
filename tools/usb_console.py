#!/usr/bin/env python3
"""Consola y puente local USB para TresVizo RTK; no simula el instrumento."""
import argparse
import json
import mimetypes
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import serial
from serial.tools import list_ports

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
        self.key = None
        self.sequence = 0
        self.lock = threading.Lock()

    def close(self):
        if self.connection:
            self.connection.close()
        self.connection = None
        self.key = None

    def _open(self):
        if self.connection and self.connection.is_open:
            return
        connection = serial.Serial(baudrate=115200, timeout=0.25, write_timeout=2, exclusive=True)
        connection.dtr = False
        connection.rts = False
        connection.port = self.port
        connection.open()
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
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            line = self.connection.read_until(b"\n", 8192)
            if not line.startswith(b"{"):
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
                if path == "/api/access":
                    return self._exchange(method, path, body)
                if self.key is None:
                    access = self._exchange("GET", "/api/access")
                    if access.get("status") != 200:
                        return access
                    self.key = access["body"]["access_key"]
                return self._exchange(method, path, body, self.key)
            except (serial.SerialException, OSError, TimeoutError):
                self.close()
                raise


def serve(device, port):
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    allowed_origins = {f"http://{host}" for host in allowed_hosts}
    assets = {"/": WEB / "index.html", "/app.css": WEB / "app.css", "/app.js": WEB / "app.js", "/assets/tresvizo-logo.png": WEB / "assets" / "tresvizo-logo.png"}

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
            if self.path not in {"/api/status", "/api/config", "/api/restart"}:
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
    finally:
        server.server_close()
        device.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="Puerto USB del ESP32; se detecta si hay uno solo.")
    parser.add_argument("command", choices=["access", "status", "config", "serve"])
    parser.add_argument("--http-port", type=int, default=8765)
    args = parser.parse_args()
    device = Instrument(args.port or detect_port())
    try:
        if args.command == "serve":
            serve(device, args.http_port)
        else:
            result = device.request("GET", f"/api/{args.command}")
            print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        device.close()


if __name__ == "__main__":
    main()
