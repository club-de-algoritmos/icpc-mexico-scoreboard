from datetime import datetime, timedelta
from typing import List

from asgiref.sync import async_to_sync
from django.test import TestCase

from icpc_mexico_scoreboard.db.models import ScoreboardStatus
from icpc_mexico_scoreboard.db.queries import get_repechaje_teams_that_have_advanced
from icpc_mexico_scoreboard.parser_types import ParsedBocaScoreboard, ParsedBocaScoreboardTeam
from icpc_mexico_scoreboard.scoreboard_notifier import ScoreboardNotifier
from icpc_mexico_scoreboard.tests.factories import ContestFactory


def _team(name: str, place: int = 1, total_solved: int = 1) -> ParsedBocaScoreboardTeam:
    return ParsedBocaScoreboardTeam(
        name=name, place=place, user_site="site1", total_solved=total_solved, total_penalty=0, problems=[],
    )


def _make_notifier(teams: List[ParsedBocaScoreboardTeam]) -> ScoreboardNotifier:
    notifier = ScoreboardNotifier()
    notifier._scoreboard = ParsedBocaScoreboard(teams=teams)
    return notifier


def _current_contest(**kwargs):
    kwargs.setdefault("starts_at", datetime.utcnow() - timedelta(hours=1))
    kwargs.setdefault("scoreboard_status", ScoreboardStatus.VISIBLE)
    return ContestFactory(**kwargs)


class GetAdvancingRankTest(TestCase):
    def test_no_max_to_advance_returns_empty(self) -> None:
        _current_contest(max_teams_to_advance=None)
        notifier = _make_notifier([_team("[ITSUR] Team A")])

        result = async_to_sync(notifier._get_advancing_rank)()

        self.assertEqual(result, "")

    def test_caps_teams_per_school(self) -> None:
        _current_contest(max_teams_to_advance=5, max_teams_per_school_to_advance=1)
        teams = [_team("[ITSUR] Team A"), _team("[ITSUR] Team B"), _team("[UAS] Team C")]
        notifier = _make_notifier(teams)

        result = async_to_sync(notifier._get_advancing_rank)()

        self.assertIn("Team A", result)
        self.assertNotIn("Team B", result)
        self.assertIn("Team C", result)

    def test_excludes_guest_teams(self) -> None:
        _current_contest(max_teams_to_advance=5)
        teams = [_team("[OMI Sinaloa] Team A"), _team("[ITSUR] Team B")]
        notifier = _make_notifier(teams)

        result = async_to_sync(notifier._get_advancing_rank)()

        self.assertNotIn("Team A", result)
        self.assertIn("Team B", result)

    def test_stops_at_max_teams_to_advance(self) -> None:
        _current_contest(max_teams_to_advance=1, max_teams_per_school_to_advance=5)
        teams = [_team("[ITSUR] Team A"), _team("[UAS] Team B")]
        notifier = _make_notifier(teams)

        result = async_to_sync(notifier._get_advancing_rank)()

        self.assertIn("Team A", result)
        self.assertNotIn("Team B", result)

    def test_repechaje_contest_ignores_teams_that_already_advanced(self) -> None:
        _current_contest(name="Repechaje 2026", max_teams_to_advance=5)
        already_advanced = get_repechaje_teams_that_have_advanced()[0].name
        teams = [_team(f"[ITSUR] {already_advanced}"), _team("[UAS] New Team")]
        notifier = _make_notifier(teams)

        result = async_to_sync(notifier._get_advancing_rank)()

        self.assertNotIn(already_advanced, result)
        self.assertIn("New Team", result)
