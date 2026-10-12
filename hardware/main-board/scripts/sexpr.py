"""Lectura y escritura mínima de expresiones S en el formato de KiCad.

Los átomos sin comillas se conservan como `str`; las cadenas entre comillas
como `QStr`. Los números generados por los scripts pueden ser `int` o `float`.
"""

import re

__all__ = ["QStr", "loads", "dumps", "find", "findall", "value"]


class QStr(str):
    """Cadena que se escribe entre comillas."""

    __slots__ = ()


_TOKEN = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))', re.S)


def _unescape(s):
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            n = s[i + 1]
            out.append({"n": "\n", "t": "\t"}.get(n, n))
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _escape(s):
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def loads(text):
    """Convierte texto en listas anidadas."""
    stack = [[]]
    pos = 0
    n = len(text)
    while pos < n:
        m = _TOKEN.match(text, pos)
        if not m:
            if text[pos:].strip():
                raise ValueError("sintaxis inválida cerca de %d: %r" % (pos, text[pos:pos + 40]))
            break
        pos = m.end()
        lp, rp, qs, atom = m.groups()
        if lp:
            stack.append([])
        elif rp:
            node = stack.pop()
            stack[-1].append(node)
        elif qs is not None:
            stack[-1].append(QStr(_unescape(qs)))
        else:
            stack[-1].append(atom)
    if len(stack) != 1:
        raise ValueError("paréntesis sin cerrar")
    return stack[0][0] if len(stack[0]) == 1 else stack[0]


def _num(v):
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, int):
        return str(v)
    s = "%.4f" % v
    s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _atom(a):
    if isinstance(a, QStr):
        return '"%s"' % _escape(a)
    if isinstance(a, (int, float)):
        return _num(a)
    return str(a)


def dumps(node, indent=0):
    """Escribe listas anidadas con sangría de tabuladores, como KiCad."""
    if not isinstance(node, list):
        return _atom(node)
    if not any(isinstance(c, list) for c in node):
        return "(" + " ".join(_atom(c) for c in node) + ")"
    head = []
    i = 0
    while i < len(node) and not isinstance(node[i], list):
        head.append(_atom(node[i]))
        i += 1
    tab = "\t" * (indent + 1)
    lines = ["(" + " ".join(head)]
    rest = node[i:]
    # Las listas de puntos (pts (xy ..)...) se escriben en una línea.
    if head and head[0] == "pts":
        return "(pts " + " ".join(dumps(c) for c in rest) + ")"
    for c in rest:
        lines.append(tab + dumps(c, indent + 1))
    lines.append("\t" * indent + ")")
    return "\n".join(lines)


def find(node, head):
    """Primer hijo de `node` cuya cabeza sea `head`."""
    for c in node:
        if isinstance(c, list) and c and c[0] == head:
            return c
    return None


def findall(node, head):
    return [c for c in node if isinstance(c, list) and c and c[0] == head]


def value(node, head, default=None):
    c = find(node, head)
    return c[1] if c is not None and len(c) > 1 else default
