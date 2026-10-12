"""Identificadores (KIID) repetibles para los scripts que crean objetos en KiCad.

KiCad guarda el PCB ordenado por los identificadores de sus objetos, y los scripts recorren los
objetos en el orden en que los lee: con identificadores al azar, dos ejecuciones con la misma entrada
procesan las piezas en otro orden y el ruteo sale distinto. Cada script fija la semilla del generador
a partir de su nombre y del contenido de lo que lee (sin las líneas de fecha y ruta de origen que
escribe kicad-cli en la netlist), así que la misma entrada da los mismos identificadores, y dos pasos
distintos, o el mismo paso sobre otra entrada, no los repiten.
"""

import zlib

import pcbnew

VOLATILE = (b"(date ", b"(source ")


def seed(tag, *paths):
    h = zlib.crc32(tag.encode("utf-8"))
    for p in paths:
        with open(p, "rb") as f:
            for line in f:
                if not any(v in line for v in VOLATILE):
                    h = zlib.crc32(line, h)
    pcbnew.KIID.SeedGenerator(h & 0xFFFFFFFF)
