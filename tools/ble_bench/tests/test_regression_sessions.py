"""Regresión: cada sesión grabada de `tests/fixtures/` da el mismo resumen que se guardó.

Para añadir una sesión real: **anonimizarla** (las respuestas de /api/status traen
nombres de red e IP; tests/fixtures/ solo admite datos anonimizados) y dejarla
aquí con un nombre que diga qué es:

    python3 tools/ble_bench anonymize …/sesion.jsonl tools/ble_bench/tests/fixtures/X.jsonl
    python3 tools/ble_bench replay tools/ble_bench/tests/fixtures/X.jsonl   # revisar a mano

La primera vez el test escribe el .resumen.txt que falte y falla, para que se revise.

Si un cambio del decodificador o del análisis cambia un resumen, esta prueba falla
y el cambio tiene que ser a propósito: se regenera el .resumen.txt y se dice por qué.
La sesión que hay hoy salió del **simulador**, no del equipo.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from bench.analysis import analyze_events
from bench.session import read_session

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class RecordedSessions(unittest.TestCase):
    def test_every_session_matches_its_summary(self):
        sessions = sorted(FIXTURES.glob("*.jsonl"))
        self.assertTrue(sessions, "no hay sesiones grabadas en tests/fixtures")
        for session in sessions:
            with self.subTest(session=session.name):
                _, events = read_session(session)
                summary = analyze_events(events).render("Reproducción") + "\n"
                golden = session.with_suffix(".resumen.txt")
                if not golden.exists():
                    golden.write_text(summary, encoding="utf-8")
                    self.fail(f"{golden.name} no existía: se escribió; revisarlo y volver a correr")
                self.assertEqual(summary, golden.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
