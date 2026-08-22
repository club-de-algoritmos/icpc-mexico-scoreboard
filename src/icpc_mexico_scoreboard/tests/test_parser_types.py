import unittest

from icpc_mexico_scoreboard.parser_types import ParsedBocaScoreboardTeam


def _make_team(name: str) -> ParsedBocaScoreboardTeam:
    return ParsedBocaScoreboardTeam(
        name=name, place=1, user_site="site1", total_solved=0, total_penalty=0, problems=[]
    )


class CleanNameTest(unittest.TestCase):
    def test_strips_school_prefix(self) -> None:
        team = _make_team("[ITSUR] Los Compiladores")
        self.assertEqual(team.clean_name, "Los Compiladores")

    def test_no_school_prefix_returns_full_name(self) -> None:
        team = _make_team("Los Compiladores")
        self.assertEqual(team.clean_name, "Los Compiladores")


class SchoolNameTest(unittest.TestCase):
    def test_extracts_school_from_brackets(self) -> None:
        team = _make_team("[ITSUR] Los Compiladores")
        self.assertEqual(team.school_name, "ITSUR")

    def test_no_school_prefix_is_empty(self) -> None:
        team = _make_team("Los Compiladores")
        self.assertEqual(team.school_name, "")


class IsGuestTest(unittest.TestCase):
    def test_omi_school_is_guest(self) -> None:
        team = _make_team("[OMI Sinaloa] Los Compiladores")
        self.assertTrue(team.is_guest)

    def test_cbtis_school_is_guest(self) -> None:
        team = _make_team("[CBTIS 100] Los Compiladores")
        self.assertTrue(team.is_guest)

    def test_regular_school_is_not_guest(self) -> None:
        team = _make_team("[ITSUR] Los Compiladores")
        self.assertFalse(team.is_guest)
