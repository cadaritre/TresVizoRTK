#!/usr/bin/env python3
"""Comprueba que el firmware del MeridianV sigue cumpliendo el contrato con sus apps.

El contrato (`docs/api-contract/app-contract.json`) enumera lo que las apps iOS y
Android leen de cada respuesta y lo que mandan en cada cuerpo. Este programa lo
contrasta con el firmware de dos maneras:

- `static` (por omisión, sin equipo): lee el código C++ de `firmware/esp32`
  (`src`, `include`, `lib`), sin comentarios, y exige que cada ruta siga
  despachándose, que cada clave del contrato se siga ESCRIBIENDO como literal
  `["clave"]` en la función que arma esa respuesta (con el tipo del contrato si
  se escribe un literal), y que se sigan leyendo las claves que mandan las
  apps. También comprueba la disposición de los paquetes binarios de BLE,
  WebSocket e imagen firmada.
- `device --port /dev/cu.usbmodemXXXX`: pide por la consola USB cada ruta de
  lectura y valida presencia, tipo, nulos, enumerados estrictos y que la
  respuesta quepa por BLE (4096 bytes). `--replay` hace lo mismo con respuestas
  grabadas, sin equipo; `--record` las graba sin contraseñas.

Solo usa la biblioteca estándar. El modo `device` necesita además pyserial,
porque reutiliza `tools/usb_console.py`.

Sale con 0 si todo cumple, 1 si algo del contrato se rompió y 2 si el propio
contrato está mal formado o no se pudo ejecutar la comprobación.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DEFAULT_CONTRACT = REPO / "docs" / "api-contract" / "app-contract.json"
DEFAULT_FIRMWARE = REPO / "firmware" / "esp32"
SOURCE_DIRS = ("src", "include", "lib")
SOURCE_SUFFIXES = {".cpp", ".cc", ".c", ".h", ".hpp"}

JSON_TYPES = {"string", "number", "integer", "boolean", "object", "array"}
APPS = {"ios", "android"}
METHODS = {"GET", "POST", "PUT"}
CHANNELS = {"http", "ble", "usb"}

# Códigos de salida.
EXIT_OK = 0
EXIT_BROKEN = 1
EXIT_UNUSABLE = 2

# Claves cuyo valor nunca se imprime ni se graba tal cual (`--record`).
SECRET_KEY = re.compile(r"(pass|password|secret|token|key)$", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Lectura del C++ sin comentarios
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Token:
    kind: str        # "str", "word" o "punct"
    text: str        # el contenido del literal, la palabra o el signo
    line: int
    enclosing: str   # "(", "[", "{" o "" según el paréntesis que lo contiene


RAW_PREFIXES = {"R", "u8R", "uR", "UR", "LR"}
OPENERS = {"(": ")", "[": "]", "{": "}"}
CLOSERS = {")": "(", "]": "[", "}": "{"}


def scan_cpp(text: str) -> list[Token]:
    """Tokeniza C++ lo justo para distinguir literales de cadena del resto.

    Descarta comentarios `//` y `/* */` (una clave comentada no cuenta como
    escrita), respeta los escapes de las cadenas y de los caracteres, y anota
    para cada token qué paréntesis lo contiene. No pretende ser un compilador.
    """
    tokens: list[Token] = []
    stack: list[str] = []
    i, line, n = 0, 1, len(text)
    word_start = -1

    def flush_word(end: int) -> None:
        nonlocal word_start
        if word_start >= 0:
            tokens.append(Token("word", text[word_start:end], line, stack[-1] if stack else ""))
            word_start = -1

    while i < n:
        c = text[i]
        # Comentarios.
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            flush_word(i)
            end = text.find("\n", i)
            i = n if end < 0 else end
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            flush_word(i)
            end = text.find("*/", i + 2)
            end = n if end < 0 else end + 2
            line += text.count("\n", i, end)
            i = end
            continue
        # Literales de cadena, también crudos (R"delim(...)delim").
        if c == '"':
            prefix = text[word_start:i] if word_start >= 0 else ""
            if prefix in RAW_PREFIXES:
                word_start = -1
                close = text.find("(", i + 1)
                delimiter = text[i + 1:close]
                end = text.find(")" + delimiter + '"', close + 1)
                end = n if end < 0 else end
                tokens.append(Token("str", text[close + 1:end], line, stack[-1] if stack else ""))
                stop = min(n, end + len(delimiter) + 2)
                line += text.count("\n", i, stop)
                i = stop
                continue
            word_start = -1  # u8"", L"": el prefijo no es una palabra aparte
            start_line = line
            j = i + 1
            chunk = []
            while j < n and text[j] != '"':
                if text[j] == "\\" and j + 1 < n:
                    chunk.append(text[j:j + 2])
                    if text[j + 1] == "\n":
                        line += 1
                    j += 2
                    continue
                if text[j] == "\n":  # cadena sin cerrar: no arrastrar el resto del archivo
                    break
                chunk.append(text[j])
                j += 1
            tokens.append(Token("str", "".join(chunk), start_line, stack[-1] if stack else ""))
            i = j + 1
            continue
        # Literales de carácter, salvo el separador de dígitos de C++14 (1'000).
        if c == "'":
            if word_start >= 0 and text[word_start].isdigit():
                i += 1
                continue
            flush_word(i)
            j = i + 1
            while j < n and text[j] != "'" and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            i = j + 1
            continue
        if c.isalnum() or c == "_":
            if word_start < 0:
                word_start = i
            i += 1
            continue
        flush_word(i)
        if c == "\n":
            line += 1
        elif not c.isspace():
            enclosing = stack[-1] if stack else ""
            if c in CLOSERS and stack and stack[-1] == CLOSERS[c]:
                stack.pop()
                enclosing = stack[-1] if stack else ""
            tokens.append(Token("punct", c, line, enclosing))
            if c in OPENERS:
                stack.append(c)
        i += 1
    flush_word(n)
    return tokens


def _is_punct(token: Token | None, chars: str) -> bool:
    return token is not None and token.kind == "punct" and token.text in chars


class FirmwareIndex:
    """Los literales de cadena del firmware, por archivo, sin comentarios."""

    def __init__(self, root: Path):
        self.root = Path(root)
        if not self.root.is_dir():
            raise FileNotFoundError(f"No existe la carpeta del firmware: {self.root}")
        self.files: dict[str, list[Token]] = {}
        self.code: dict[str, str] = {}
        for folder in SOURCE_DIRS:
            base = self.root / folder
            if not base.is_dir():
                continue
            for path in sorted(base.rglob("*")):
                if path.suffix in SOURCE_SUFFIXES and path.is_file():
                    relative = path.relative_to(self.root).as_posix()
                    text = path.read_text(encoding="utf-8", errors="replace")
                    self.files[relative] = scan_cpp(text)
                    self.code[relative] = strip_comments(text)
        if not self.files:
            raise FileNotFoundError(f"No hay fuentes C++ en {self.root} ({', '.join(SOURCE_DIRS)}).")

    def has_source(self, spec: str) -> bool:
        """`spec` es «archivo» o «archivo#función»; existe si el archivo existe
        y, con función, si la define."""
        name, _, function = spec.partition("#")
        if name not in self.files:
            return False
        return not function or bool(self._bodies(name, function))

    def _bodies(self, name: str, function: str) -> list[tuple[int, int]]:
        """Rangos de tokens del cuerpo de cada definición de `function` en el
        archivo: `function ( … ) [const…] { … }`. Una llamada no tiene `{`."""
        tokens = self.files[name]
        bodies = []
        for index, token in enumerate(tokens):
            if token.kind != "word" or token.text != function:
                continue
            if not _is_punct(tokens[index + 1] if index + 1 < len(tokens) else None, "("):
                continue
            close = _matching(tokens, index + 1, "(", ")")
            if close is None:
                continue
            after = close + 1
            while after < len(tokens) and tokens[after].kind == "word":  # const, override, noexcept
                after += 1
            if not _is_punct(tokens[after] if after < len(tokens) else None, "{"):
                continue
            end = _matching(tokens, after, "{", "}")
            if end is not None:
                bodies.append((after, end))
        return bodies

    def resolve(self, specs: list[str] | None) -> list[tuple[str, int, int]]:
        """(archivo, inicio, fin) de cada fuente pedida; todo el firmware si no
        se pide ninguna. «archivo#función» se limita al cuerpo de la función."""
        if not specs:
            return [(name, 0, len(tokens)) for name, tokens in self.files.items()]
        ranges = []
        for spec in specs:
            name, _, function = spec.partition("#")
            if name not in self.files:
                continue
            if function:
                ranges.extend((name, start, end) for start, end in self._bodies(name, function))
            else:
                ranges.append((name, 0, len(self.files[name])))
        return ranges

    def key_evidence(self, key: str, specs: list[str] | None) -> list[str]:
        """Dónde se ESCRIBE `key` como clave JSON.

        Cuenta `x["key"] = …`, `x["key"]["otra"] = …`, `x["key"].to<…>()`,
        `x["key"].add<…>()` y `x["key"].as<JsonObject|JsonArray>()` (un
        contenedor que se pasa a quien lo rellena), y las listas `{"a", "key"}`
        que recorre un `for` para escribir claves. No cuenta lecturas como
        `body["key"]`, `doc["key"] | 0` ni `x["key"] == y`."""
        found = []
        for name, start, end in self.resolve(specs):
            tokens = self.files[name]
            for index in range(start, end):
                token = tokens[index]
                if token.kind != "str" or token.text != key:
                    continue
                before = tokens[index - 1] if index else None
                after = tokens[index + 1] if index + 1 < len(tokens) else None
                listed = token.enclosing == "{" and _is_punct(before, "{,") and _is_punct(after, ",}")
                written = _is_punct(before, "[") and _is_punct(after, "]") and _is_write(tokens, index + 2)
                if listed or written:
                    found.append(f"{name}:{token.line}")
        return found

    def literal_writes(self, key: str, specs: list[str] | None) -> list[tuple[str, str]]:
        """Las escrituras `x["key"] = <literal>;` y el tipo JSON del literal.
        Solo las sencillas (cadena, entero, true/false, nullptr): con una
        expresión no se sabe el tipo y no se juzga."""
        found = []
        for name, start, end in self.resolve(specs):
            tokens = self.files[name]
            for index in range(start + 1, min(end, len(tokens) - 4)):
                token = tokens[index]
                if token.kind != "str" or token.text != key:
                    continue
                if not (_is_punct(tokens[index - 1], "[") and _is_punct(tokens[index + 1], "]")
                        and _is_punct(tokens[index + 2], "=") and _is_punct(tokens[index + 4], ";")):
                    continue
                literal = _literal_type(tokens[index + 3])
                if literal:
                    found.append((f"{name}:{token.line}", literal))
        return found

    def literal_evidence(self, literal: str, specs: list[str] | None) -> list[str]:
        """Dónde aparece la cadena `literal` en el código (no en comentarios)."""
        found = []
        for name, start, end in self.resolve(specs):
            tokens = self.files[name]
            found.extend(f"{name}:{tokens[i].line}" for i in range(start, end)
                         if tokens[i].kind == "str" and tokens[i].text == literal)
        return found


def _matching(tokens: list[Token], opener: int, open_char: str, close_char: str) -> int | None:
    depth = 0
    for index in range(opener, len(tokens)):
        token = tokens[index]
        if token.kind != "punct":
            continue
        if token.text == open_char:
            depth += 1
        elif token.text == close_char:
            depth -= 1
            if depth == 0:
                return index
    return None


INTEGER_LITERAL = re.compile(r"^(0[xX][0-9a-fA-F]+|\d+)[uUlL]*$")


def _literal_type(token: Token) -> str | None:
    if token.kind == "str":
        return "string"
    if token.kind == "word":
        if token.text in ("true", "false"):
            return "boolean"
        if token.text in ("nullptr", "NULL"):
            return "null"
        if INTEGER_LITERAL.match(token.text):
            return "integer"
    return None


def _literal_fits(literal: str, expected: str) -> bool:
    if expected == "number":
        return literal in ("integer", "number")
    return literal == expected


def _is_write(tokens: list[Token], index: int) -> bool:
    """¿Lo que sigue a un `[…]` es una escritura? `index` apunta detrás del `]`."""
    while _is_punct(tokens[index] if index < len(tokens) else None, "["):
        close = _matching(tokens, index, "[", "]")
        if close is None:
            return False
        index = close + 1
    if index + 1 >= len(tokens):
        return False
    first, second = tokens[index], tokens[index + 1]
    if _is_punct(first, "="):
        return not _is_punct(second, "=")
    if _is_punct(first, ".") and second.kind == "word":
        if second.text in ("to", "add"):
            return True
        if second.text == "as" and index + 3 < len(tokens):
            return tokens[index + 3].kind == "word" and tokens[index + 3].text in ("JsonObject", "JsonArray")
    return False


def strip_comments(text: str) -> str:
    """El código sin comentarios, con las cadenas intactas y las líneas en su sitio."""
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            end = text.find("\n", i)
            i = n if end < 0 else end
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            end = text.find("*/", i + 2)
            end = n if end < 0 else end + 2
            out.append("\n" * text.count("\n", i, end))
            i = end
            continue
        if c in "\"'":
            if c == "'" and i and (text[i - 1].isalnum()) and text[i - 1].isdigit():
                out.append(c)
                i += 1
                continue
            j = i + 1
            while j < n and text[j] != c and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1])
            i = j + 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


# ---------------------------------------------------------------------------
# Rutas de claves: "subsystems.ble.protocol_version", "networks[].ssid"
# ---------------------------------------------------------------------------

KEY_SEGMENT = re.compile(r"^[A-Za-z0-9_]+(\[\])?$")


def parse_key_path(path: str) -> list[tuple[str, bool]]:
    """`a.b[].c` → [("a", False), ("b", True), ("c", False)]; True = arreglo."""
    if not path:
        raise ValueError("ruta de clave vacía")
    segments = []
    for raw in path.split("."):
        if not KEY_SEGMENT.match(raw):
            raise ValueError(f"segmento no válido «{raw}» en «{path}»")
        array = raw.endswith("[]")
        segments.append((raw[:-2] if array else raw, array))
    return segments


def canonical(path: str) -> str:
    return path.replace("[]", "")


def writers_for(container: str, writers: dict[str, list[str]]) -> list[str] | None:
    """Los archivos que escriben los miembros del objeto `container`: los del
    prefijo más largo declarado en `writers`. None si no hay ninguno (todos)."""
    parts = canonical(container).split(".") if container else []
    for size in range(len(parts), -1, -1):
        candidate = ".".join(parts[:size])
        if candidate in writers:
            return writers[candidate]
    return None


# ---------------------------------------------------------------------------
# El contrato
# ---------------------------------------------------------------------------

def load_contract(path: Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def route_label(route: dict) -> str:
    return f"{route['method']} {route['path']}"


def validate_contract(contract: dict) -> list[str]:
    """Errores de forma del propio contrato. Vacío si está bien."""
    problems = []
    routes = contract.get("routes")
    if not isinstance(routes, list) or not routes:
        return ["El contrato no tiene `routes`."]
    seen = set()
    for route in routes:
        if not isinstance(route, dict) or "method" not in route or "path" not in route:
            problems.append(f"Ruta sin `method` o `path`: {route!r}"[:200])
            continue
        label = route_label(route)
        if label in seen:
            problems.append(f"{label}: repetida.")
        seen.add(label)
        if route["method"] not in METHODS:
            problems.append(f"{label}: método desconocido.")
        if not str(route["path"]).startswith("/api/"):
            problems.append(f"{label}: la ruta debe empezar por /api/.")
        if not set(route.get("channels", [])) <= CHANNELS or not route.get("channels"):
            problems.append(f"{label}: `channels` vacío o con valores fuera de {sorted(CHANNELS)}.")
        if not route.get("apps") or not set(route["apps"]) <= APPS:
            problems.append(f"{label}: `apps` vacío o con valores fuera de {sorted(APPS)}.")
        fw = route.get("firmware", {})
        if not fw.get("dispatch"):
            problems.append(f"{label}: falta `firmware.dispatch` (dónde se despacha la ruta).")
        for section in ("response", "request"):
            paths = set()
            for entry in route.get(section, []):
                where = f"{label} [{section}] {entry.get('path')!r}"
                try:
                    parse_key_path(entry.get("path", ""))
                except ValueError as error:
                    problems.append(f"{where}: {error}.")
                    continue
                if entry["path"] in paths:
                    problems.append(f"{where}: repetida.")
                paths.add(entry["path"])
                if entry.get("type") not in JSON_TYPES:
                    problems.append(f"{where}: tipo «{entry.get('type')}» fuera de {sorted(JSON_TYPES)}.")
                if not entry.get("apps") or not set(entry["apps"]) <= APPS:
                    problems.append(f"{where}: `apps` vacío o desconocido.")
                elif not set(entry["apps"]) <= set(route.get("apps", [])):
                    problems.append(f"{where}: la usa una app que no figura en la ruta.")
                for flag in ("nullable", "optional"):
                    if section == "response" and not isinstance(entry.get(flag), bool):
                        problems.append(f"{where}: falta `{flag}` (true/false).")
            # Los contenedores de una clave declarada también tienen que estar declarados
            # («networks[].ssid» cuelga de «networks», que es un arreglo).
            declared = {canonical(e["path"]): e.get("type") for e in route.get(section, []) if e.get("path") in paths}
            for entry in route.get(section, []):
                segments = entry["path"].split(".")
                for size in range(1, len(segments)):
                    parent = ".".join(segments[:size])
                    if canonical(parent) not in declared:
                        problems.append(f"{label} [{section}]: «{entry['path']}» cuelga de «{parent}», que no está declarada.")
                        break
                    wanted = "array" if parent.endswith("[]") else "object"
                    if declared[canonical(parent)] != wanted:
                        problems.append(f"{label} [{section}]: «{canonical(parent)}» tiene hijos como {wanted} pero se declara {declared[canonical(parent)]}.")
                        break
    known = {(route_label(r), e["path"]) for r in routes if isinstance(r, dict) and "method" in r
             for e in r.get("response", []) if "path" in e}
    for item in contract.get("identifiers", []):
        if not item.get("name") or not item.get("why"):
            problems.append(f"Identificador sin `name` o `why`: {item!r}"[:200])
        for source in item.get("exposed_in", []):
            if (source.get("route"), source.get("path")) not in known:
                problems.append(f"Identificador «{item.get('name')}»: {source.get('route')} → {source.get('path')} no está en el contrato.")
    if not contract.get("identifiers"):
        problems.append("El contrato no tiene `identifiers`.")
    for item in contract.get("binary", {}).get("firmware_evidence", []):
        if "file" not in item or "pattern" not in item or "what" not in item:
            problems.append(f"Evidencia binaria incompleta: {item!r}"[:200])
            continue
        try:
            re.compile(item["pattern"])
        except re.error as error:
            problems.append(f"Evidencia binaria «{item['what']}»: patrón no válido ({error}).")
    return problems


# ---------------------------------------------------------------------------
# Comprobación estática
# ---------------------------------------------------------------------------

@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    checked: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def check_static(contract: dict, firmware: FirmwareIndex) -> Report:
    report = Report()
    for route in contract["routes"]:
        label = route_label(route)
        fw = route["firmware"]
        writers = fw.get("writers", {})
        dispatch = fw["dispatch"]

        sources = list(dispatch) + [s for specs in writers.values() for s in specs] + list(fw.get("readers", []))
        missing = sorted({s for s in sources if not firmware.has_source(s)})
        if missing:
            report.errors.append(
                f"{label}: no existe en el firmware: {', '.join(missing)}. Si el código se movió o la función "
                "cambió de nombre, actualiza `firmware` de esta ruta en el contrato.")
            continue

        report.checked += 1
        if not firmware.literal_evidence(route["path"], dispatch):
            report.errors.append(
                f"{label}: la ruta ya no aparece en {', '.join(dispatch)}. "
                "Si se movió, actualiza `firmware.dispatch` en el contrato; si se quitó, rompe las apps.")

        for entry in route.get("response", []):
            report.checked += 1
            segments = parse_key_path(entry["path"])
            container = ""
            for name, array in segments:
                files = writers_for(container, writers)
                if not firmware.key_evidence(name, files):
                    where = ", ".join(files) if files else "ningún archivo del firmware"
                    report.errors.append(
                        f"{label}: la clave «{entry['path']}» (que lee {'+'.join(entry['apps'])}) "
                        f"ya no se escribe: falta «{name}» en {where}.")
                    break
                container = f"{container}.{name}" if container else name
                if array:
                    container += "[]"
            else:
                # La clave sigue ahí: que no se escriba con un literal de otro tipo.
                leaf = segments[-1][0]
                files = writers_for(container.rsplit(".", 1)[0] if "." in container else "", writers)
                for where, literal in firmware.literal_writes(leaf, files):
                    if literal == "null":
                        if not entry["nullable"]:
                            report.errors.append(
                                f"{label}: «{entry['path']}» se escribe nula en {where} y "
                                f"{'+'.join(entry['apps'])} no admite null.")
                    elif not _literal_fits(literal, entry["type"]):
                        report.errors.append(
                            f"{label}: «{entry['path']}» se escribe como {literal} en {where} y el contrato "
                            f"dice {entry['type']}.")

        # Lo que llega se lee de muchas maneras (`body["x"]`, `boolField(body,"x",…)`,
        # `key != "x"` al recorrer el objeto): basta con el literal en el manejador.
        readers = fw.get("readers") or dispatch
        for entry in route.get("request", []):
            report.checked += 1
            name = parse_key_path(entry["path"])[-1][0]
            if not firmware.literal_evidence(name, readers):
                report.errors.append(
                    f"{label}: el firmware ya no lee «{entry['path']}» del cuerpo, que manda "
                    f"{'+'.join(entry['apps'])} (buscado en {', '.join(readers)}).")

    envelope = contract.get("command_envelope")
    if envelope:
        files = envelope["firmware"]["files"]
        for section, finder in (("request", firmware.literal_evidence), ("response", firmware.key_evidence)):
            for entry in envelope.get(section, []):
                report.checked += 1
                if not finder(entry["path"], files):
                    report.errors.append(
                        f"Envoltura BLE [{section}]: «{entry['path']}» ya no aparece en {', '.join(files)}.")

    errors = contract.get("error_response")
    if errors:
        for entry in errors.get("response", []):
            report.checked += 1
            if not firmware.key_evidence(entry["path"], None):
                report.errors.append(f"Respuestas de error: ningún archivo escribe ya «{entry['path']}».")
        for item in errors.get("codes_used_by_apps", []):
            report.checked += 1
            if not firmware.literal_evidence(item["code"], None):
                report.errors.append(
                    f"Respuestas de error: el código «{item['code']}», que distinguen {'+'.join(item['apps'])}, ya no existe.")

    for item in contract.get("binary", {}).get("firmware_evidence", []):
        report.checked += 1
        code = firmware.code.get(item["file"])
        if code is None:
            report.errors.append(f"Binario: no existe {item['file']} ({item['what']}).")
            continue
        match = re.search(item["pattern"], code, re.MULTILINE)
        if not match:
            report.errors.append(f"Binario: {item['what']} — ya no se encuentra en {item['file']}.")
            continue
        if "min" in item and int(match.group(1), 0) < item["min"]:
            report.errors.append(f"Binario: {item['what']} — vale {match.group(1)}, por debajo de {item['min']}.")

    if contract.get("discrepancies"):
        report.notes.append(f"{len(contract['discrepancies'])} discrepancia(s) conocida(s) anotada(s) en el contrato "
                            "(`discrepancies`); no las comprueba este modo.")
    return report


# ---------------------------------------------------------------------------
# Validación de respuestas reales (modo device y fixtures)
# ---------------------------------------------------------------------------

def json_type_ok(value, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    return False


def json_type_name(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    return "object"


_ABSENT = object()


def values_at(body, segments: list[tuple[str, bool]]):
    """Los valores en esa ruta de claves, `_ABSENT` donde falta la clave.

    Un arreglo se recorre entero; uno vacío no da nada que comprobar. Si falta
    un contenedor, o es nulo, sus hijos no se miran: eso lo juzga la entrada del
    propio contenedor, que el contrato obliga a declarar."""
    current = [body]
    for index, (name, array) in enumerate(segments):
        last = index == len(segments) - 1
        following = []
        for item in current:
            if not isinstance(item, dict):
                following.append(_ABSENT)  # se esperaba un objeto: la clave no puede estar
                continue
            if name not in item:
                if last:
                    following.append(_ABSENT)
                continue
            value = item[name]
            if last:
                following.append(value)
            elif value is None:
                continue
            elif array:
                if isinstance(value, list):
                    following.extend(value)
            else:
                following.append(value)
        current = following
    return current


def ble_secret_key(name: str) -> bool:
    """La misma regla que `protocol::isSecretKeyName` (lib/protocol/src/secret_redaction.h)."""
    return name in ("password", "pass", "cpass", "psk", "secret") or \
        name.endswith(("_password", "_pass", "_psk", "_secret"))


def strip_ble_secrets(value):
    """Lo que hace `protocol::stripSecrets` antes de responder por BLE."""
    if isinstance(value, dict):
        return {k: strip_ble_secrets(v) for k, v in value.items()
                if not (ble_secret_key(k) and not isinstance(v, bool))}
    if isinstance(value, list):
        return [strip_ble_secrets(v) for v in value]
    return value


def ble_message_bytes(status: int, body) -> int:
    """Bytes del JSON que el equipo mandaría por BLE: `{"id":…,"status":…,"body":…}`
    compacto, con el `id` más largo posible y sin secretos."""
    message = {"id": 4294967295, "status": status, "body": strip_ble_secrets(body)}
    return len(json.dumps(message, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def validate_body(route: dict, status: int, body, ble_limit: int | None = None) -> tuple[list[str], list[str]]:
    """Errores y avisos de una respuesta frente al contrato de su ruta.

    Con `ble_limit`, además, que la misma respuesta quepa por BLE si la ruta se
    usa por ese canal: si no cabe, el equipo contesta 413 por BLE."""
    label = route_label(route)
    expected = route.get("device", {}).get("expect_status", [200])
    if status not in expected:
        if status == 404:
            return [f"{label}: el equipo contesta 404; la ruta no existe en este firmware."], []
        return [], [f"{label}: estado {status} (se esperaba {expected}); no se pudo validar."]
    errors, warnings = [], []
    if ble_limit and "ble" in route["channels"]:
        size = ble_message_bytes(status, body)
        if size > ble_limit:
            errors.append(f"{label}: por BLE la respuesta mediría {size} bytes y el máximo es {ble_limit}: "
                          "el equipo contestaría 413 (response_too_large) y las apps se quedan sin esta ruta "
                          "cuando no hay Wi-Fi.")
    for entry in route.get("response", []):
        path = entry["path"]
        for value in values_at(body, parse_key_path(path)):
            if value is _ABSENT:
                if not entry["optional"]:
                    errors.append(f"{label}: falta «{path}», que {'+'.join(entry['apps'])} exige.")
                break
            if value is None:
                if not entry["nullable"]:
                    errors.append(f"{label}: «{path}» llega null y {'+'.join(entry['apps'])} no lo admite.")
                continue
            if not json_type_ok(value, entry["type"]):
                errors.append(f"{label}: «{path}» es {json_type_name(value)} y el contrato dice {entry['type']}.")
                break
            allowed = entry.get("values")
            if allowed and value not in allowed:
                shown = repr(value)[:40]
                if entry.get("unknown_values_ok", True):
                    warnings.append(f"{label}: «{path}» = {shown}, que las apps no conocen; lo toleran.")
                else:
                    errors.append(f"{label}: «{path}» = {shown}, fuera de {allowed}: al menos una app lo "
                                  "decodifica en estricto y falla la respuesta entera.")
    return errors, warnings


def device_routes(contract: dict) -> list[dict]:
    """Las rutas que se pueden pedir a un equipo sin cambiar nada: GET y por USB."""
    return [r for r in contract["routes"]
            if r["method"] == "GET" and "usb" in r["channels"] and r.get("device", {}).get("check", True)]


def check_device(contract: dict, instrument, ble_size: bool = True) -> Report:
    report = Report()
    limit = contract.get("binary", {}).get("ble", {}).get("response_frame", {}).get("max_message_bytes")
    limit = limit if ble_size else None
    for route in device_routes(contract):
        report.checked += 1 + len(route.get("response", []))
        try:
            reply = instrument.request("GET", route["path"])
        except Exception as error:  # el cable, el puerto o un tiempo vencido
            report.errors.append(f"{route_label(route)}: sin respuesta ({error}).")
            continue
        errors, warnings = validate_body(route, reply.get("status"), reply.get("body"), limit)
        report.errors.extend(errors)
        report.warnings.extend(warnings)
    return report


class ReplayInstrument:
    """Contesta con respuestas grabadas: {"GET /api/status": {"status":200,"body":{...}}}."""

    def __init__(self, recorded: dict):
        self.recorded = recorded

    @classmethod
    def from_file(cls, path: Path) -> "ReplayInstrument":
        with open(path, encoding="utf-8") as handle:
            return cls(json.load(handle))

    def request(self, method, path, body=None):
        key = f"{method} {path}"
        if key not in self.recorded:
            raise TimeoutError(f"no hay respuesta grabada para {key}")
        return self.recorded[key]


class RecordingInstrument:
    """Envuelve un instrumento real y guarda lo que contesta, sin secretos."""

    def __init__(self, inner):
        self.inner = inner
        self.recorded: dict = {}

    def request(self, method, path, body=None):
        reply = self.inner.request(method, path, body)
        self.recorded[f"{method} {path}"] = {"status": reply.get("status"), "body": redact(reply.get("body"))}
        return reply


def redact(value, key: str = ""):
    if isinstance(value, dict):
        return {k: redact(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, key) for v in value]
    if isinstance(value, str) and SECRET_KEY.search(key) and value:
        return "redactado"
    return value


def usb_instrument(port: str):
    """El `Instrument` de `tools/usb_console.py`, sin cerrar el puerto cuando una
    respuesta tarda: abrirlo reinicia el ESP32, y cerrarlo y reabrirlo en cada
    vencimiento lo tendría reiniciándose mientras arranca."""
    sys.path.insert(0, str(REPO / "tools"))
    from usb_console import Instrument  # necesita pyserial

    class SteadyInstrument(Instrument):
        def request(self, method, path, body=None):
            with self.lock:
                try:
                    return self._exchange(method, path, body)
                except TimeoutError:
                    raise
                except OSError:  # pyserial: SerialException; el puerto ya no sirve
                    self.close()
                    raise

    return SteadyInstrument(port)


def wait_until_ready(instrument, attempts: int = 6) -> bool:
    """Reintenta `GET /api/status` mientras el equipo arranca (cada intento
    espera lo que `usb_console` da a una respuesta: 4 s)."""
    for _ in range(attempts):
        try:
            if instrument.request("GET", "/api/status").get("status") == 200:
                return True
        except TimeoutError:
            continue
        except OSError:
            return False
    return False


# ---------------------------------------------------------------------------
# Línea de órdenes
# ---------------------------------------------------------------------------

def print_report(title: str, report: Report, verbose: bool) -> None:
    for line in report.errors:
        print(f"ERROR  {line}")
    for line in report.warnings:
        print(f"AVISO  {line}")
    for line in report.notes:
        print(f"NOTA   {line}")
    if verbose:
        print(f"(revisadas {report.checked} rutas, claves y evidencias)")
    verdict = "cumple" if report.ok else f"ROTO: {len(report.errors)} problema(s)"
    print(f"{title}: {report.checked} comprobaciones, {verdict}.")


def summary(contract: dict) -> str:
    routes = contract["routes"]
    keys = sum(len(r.get("response", [])) for r in routes)
    sent = sum(len(r.get("request", [])) for r in routes)
    return f"{len(routes)} rutas, {keys} claves de respuesta y {sent} de petición"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT, help="contrato JSON")
    sub = parser.add_subparsers(dest="mode")
    static = sub.add_parser("static", help="contra el código del firmware, sin equipo (por omisión)")
    static.add_argument("--firmware-root", type=Path, default=DEFAULT_FIRMWARE,
                        help="carpeta firmware/esp32 (por omisión, la de este repositorio)")
    static.add_argument("-v", "--verbose", action="store_true")
    device = sub.add_parser("device", help="contra un equipo por la consola USB")
    source = device.add_mutually_exclusive_group(required=True)
    source.add_argument("--port", help="puerto serie, p. ej. /dev/cu.usbmodem1101")
    source.add_argument("--replay", type=Path, help="respuestas grabadas en JSON, sin equipo")
    device.add_argument("--record", type=Path, help="guarda lo que contesta el equipo (sin contraseñas)")
    device.add_argument("-v", "--verbose", action="store_true")
    parser.set_defaults(firmware_root=DEFAULT_FIRMWARE, verbose=False)
    args = parser.parse_args(argv)
    mode = args.mode or "static"

    try:
        contract = load_contract(args.contract)
    except (OSError, ValueError) as error:
        print(f"ERROR  No se pudo leer el contrato {args.contract}: {error}")
        return EXIT_UNUSABLE

    if mode == "static":
        try:
            firmware = FirmwareIndex(args.firmware_root)
        except FileNotFoundError as error:
            print(f"ERROR  {error}")
            return EXIT_UNUSABLE
        problems = validate_contract(contract)
        if problems:
            for line in problems:
                print(f"CONTRATO  {line}")
            print(f"El contrato está mal formado: {len(problems)} problema(s).")
            return EXIT_UNUSABLE
        print(f"Contrato: {summary(contract)}.")
        report = check_static(contract, firmware)
        print_report("Estático", report, getattr(args, "verbose", False))
        return EXIT_OK if report.ok else EXIT_BROKEN

    problems = validate_contract(contract)
    if problems:
        for line in problems:
            print(f"CONTRATO  {line}")
        return EXIT_UNUSABLE
    if args.replay:
        instrument = ReplayInstrument.from_file(args.replay)
    else:
        try:
            instrument = usb_instrument(args.port)
        except ImportError as error:
            print(f"ERROR  El modo device necesita pyserial ({error}). Usa el Python de PlatformIO "
                  "(~/.platformio/penv/bin/python) o instala pyserial.")
            return EXIT_UNUSABLE
        print("Abriendo el puerto: el ESP32 se reinicia al abrirlo. Esperando a que conteste…", flush=True)
        if not wait_until_ready(instrument):
            instrument.close()
            print(f"ERROR  El equipo no contesta por {args.port}. Cierra otros monitores serie y revisa el cable.")
            return EXIT_UNUSABLE
    recorder = RecordingInstrument(instrument) if args.record else None
    try:
        report = check_device(contract, recorder or instrument)
    finally:
        if hasattr(instrument, "close"):
            instrument.close()
    if recorder:
        args.record.write_text(json.dumps(recorder.recorded, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Respuestas guardadas en {args.record} (contraseñas sustituidas).")
    print_report("Equipo", report, args.verbose)
    return EXIT_OK if report.ok else EXIT_BROKEN


if __name__ == "__main__":
    sys.exit(main())
