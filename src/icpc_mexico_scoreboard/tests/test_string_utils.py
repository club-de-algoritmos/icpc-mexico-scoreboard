import unittest

from icpc_mexico_scoreboard.string_utils import normalize


class NormalizeTest(unittest.TestCase):
    def test_strips_accents(self) -> None:
        self.assertEqual(normalize("Culiacán"), "culiacan")
        self.assertEqual(normalize("Ñu"), "nu")

    def test_lowercases(self) -> None:
        self.assertEqual(normalize("ITSUR"), "itsur")

    def test_strips_surrounding_whitespace(self) -> None:
        self.assertEqual(normalize("  Equipo  "), "equipo")
