"""Empaqueta recursos locales en flash; no requiere microSD ni Internet."""
import gzip
from pathlib import Path

Import("env")
root = Path(env.subst("$PROJECT_DIR"))
assets = [
    ("/device.js", "device.js", "application/javascript; charset=utf-8"),
    ("/", "index.html", "text/html; charset=utf-8"),
    ("/app.css", "app.css", "text/css; charset=utf-8"),
    ("/update.js", "update.js", "application/javascript; charset=utf-8"),
    ("/bench.js", "bench.js", "application/javascript; charset=utf-8"),
    ("/app.js", "app.js", "application/javascript; charset=utf-8"),
    ("/assets/tresvizo-logo.png", "assets/tresvizo-logo.png", "image/png"),
]
lines = ["#pragma once", "#include <Arduino.h>", "namespace web_assets {"]
entries = []
for index, (url, filename, mime) in enumerate(assets):
    data = gzip.compress((root / "web" / filename).read_bytes(), mtime=0)
    name = f"asset_{index}"
    lines.append(f"static const uint8_t {name}[] PROGMEM = {{")
    for offset in range(0, len(data), 24):
        lines.append(",".join(str(n) for n in data[offset:offset + 24]) + ",")
    lines.append("};")
    entries.append(f'{{"{url}", "{mime}", {name}, sizeof({name})}}')
lines.append("struct Asset { const char* path; const char* mime; const uint8_t* data; size_t size; };")
lines.append("static const Asset all[] = {" + ",".join(entries) + "};")
lines.append("}")
destination = Path(env.subst("$BUILD_DIR")) / "generated"
destination.mkdir(parents=True, exist_ok=True)
header = destination / "web_assets.h"
text = "\n".join(lines) + "\n"
if not header.exists() or header.read_text() != text:
    header.write_text(text)
env.Append(CPPPATH=[str(destination)])
