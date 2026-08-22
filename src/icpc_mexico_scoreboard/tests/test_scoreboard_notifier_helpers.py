import unittest
from datetime import datetime

from icpc_mexico_scoreboard.parser_types import ParsedBocaScoreboard, ParsedBocaScoreboardTeam
from icpc_mexico_scoreboard.scoreboard_notifier import _concat_paragraphs, _format_code, _get_time_delta_as_human, \
    _get_top_teams


class FormatCodeTest(unittest.TestCase):
    def test_wraps_in_code_tag(self) -> None:
        self.assertEqual(_format_code("itsur"), "<code>itsur</code>")

    def test_escapes_html(self) -> None:
        self.assertEqual(_format_code("<b>"), "<code>&lt;b&gt;</code>")


class ConcatParagraphsTest(unittest.TestCase):
    def test_both_present_are_joined_with_blank_line(self) -> None:
        self.assertEqual(_concat_paragraphs("a", "b"), "a\n\nb")

    def test_only_first_present(self) -> None:
        self.assertEqual(_concat_paragraphs("a", None), "a")
        self.assertEqual(_concat_paragraphs("a", ""), "a")

    def test_only_second_present(self) -> None:
        self.assertEqual(_concat_paragraphs(None, "b"), "b")
        self.assertEqual(_concat_paragraphs("", "b"), "b")

    def test_both_absent(self) -> None:
        self.assertEqual(_concat_paragraphs(None, None), "")


class GetTimeDeltaAsHumanTest(unittest.TestCase):
    def test_after_before_or_equal_before_is_zero_minutes(self) -> None:
        now = datetime(2026, 1, 1, 12, 0, 0)
        self.assertEqual(_get_time_delta_as_human(now, now), "0 minutos")
        self.assertEqual(_get_time_delta_as_human(now, datetime(2025, 12, 31)), "0 minutos")

    def test_singular_minute(self) -> None:
        before = datetime(2026, 1, 1, 12, 0, 0)
        after = datetime(2026, 1, 1, 12, 0, 30)
        self.assertEqual(_get_time_delta_as_human(before, after), "1 minuto")

    def test_plural_minutes(self) -> None:
        before = datetime(2026, 1, 1, 12, 0, 0)
        after = datetime(2026, 1, 1, 12, 5, 0)
        self.assertEqual(_get_time_delta_as_human(before, after), "5 minutos")

    def test_singular_hour(self) -> None:
        before = datetime(2026, 1, 1, 12, 0, 0)
        after = datetime(2026, 1, 1, 13, 0, 0)
        self.assertEqual(_get_time_delta_as_human(before, after), "1 hora")

    def test_plural_hours(self) -> None:
        before = datetime(2026, 1, 1, 12, 0, 0)
        after = datetime(2026, 1, 1, 15, 0, 0)
        self.assertEqual(_get_time_delta_as_human(before, after), "3 horas")

    def test_singular_day(self) -> None:
        before = datetime(2026, 1, 1, 12, 0, 0)
        after = datetime(2026, 1, 2, 12, 0, 0)
        self.assertEqual(_get_time_delta_as_human(before, after), "1 día")

    def test_plural_days(self) -> None:
        before = datetime(2026, 1, 1, 12, 0, 0)
        after = datetime(2026, 1, 4, 12, 0, 0)
        self.assertEqual(_get_time_delta_as_human(before, after), "3 días")

    def test_singular_month(self) -> None:
        before = datetime(2026, 1, 1, 12, 0, 0)
        after = datetime(2026, 1, 31, 12, 0, 0)
        self.assertEqual(_get_time_delta_as_human(before, after), "1 mes")

    def test_plural_months(self) -> None:
        before = datetime(2026, 1, 1, 12, 0, 0)
        after = datetime(2026, 4, 1, 12, 0, 0)
        self.assertEqual(_get_time_delta_as_human(before, after), "3 meses")

    def test_singular_year(self) -> None:
        before = datetime(2026, 1, 1, 12, 0, 0)
        after = datetime(2027, 1, 1, 12, 0, 0)
        self.assertEqual(_get_time_delta_as_human(before, after), "1 año")

    def test_plural_years(self) -> None:
        before = datetime(2026, 1, 1, 12, 0, 0)
        after = datetime(2029, 1, 1, 12, 0, 0)
        self.assertEqual(_get_time_delta_as_human(before, after), "3 años")


def _team(name: str, total_solved: int) -> ParsedBocaScoreboardTeam:
    return ParsedBocaScoreboardTeam(
        name=name, place=1, user_site="site1", total_solved=total_solved, total_penalty=0, problems=[]
    )


class GetTopTeamsTest(unittest.TestCase):
    def test_no_scoreboard_returns_empty(self) -> None:
        self.assertEqual(_get_top_teams(None, 10), [])

    def test_limits_to_top_n(self) -> None:
        scoreboard = ParsedBocaScoreboard(
            teams=[_team("A", 1), _team("B", 1), _team("C", 1)]
        )
        self.assertEqual([t.name for t in _get_top_teams(scoreboard, 2)], ["A", "B"])

    def test_excludes_teams_with_zero_solved(self) -> None:
        scoreboard = ParsedBocaScoreboard(teams=[_team("A", 0), _team("B", 1)])
        self.assertEqual([t.name for t in _get_top_teams(scoreboard, 10)], ["B"])
