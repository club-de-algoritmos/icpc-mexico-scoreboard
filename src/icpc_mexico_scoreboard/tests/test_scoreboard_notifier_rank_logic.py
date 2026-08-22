import unittest
from datetime import datetime, timedelta
from typing import List

from icpc_mexico_scoreboard.parser_types import ParsedBocaScoreboard, ParsedBocaScoreboardProblem, \
    ParsedBocaScoreboardTeam
from icpc_mexico_scoreboard.scoreboard_notifier import ScoreboardNotifier
from icpc_mexico_scoreboard.tests.factories import ContestFactory


def _team(name: str, place: int = 1, total_solved: int = 1, total_penalty: int = 0) -> ParsedBocaScoreboardTeam:
    return ParsedBocaScoreboardTeam(
        name=name, place=place, user_site="site1", total_solved=total_solved, total_penalty=total_penalty,
        problems=[],
    )


def _team_with_problems(
        name: str, total_solved: int, solved: List[str], place: int = 1, total_penalty: int = 0,
) -> ParsedBocaScoreboardTeam:
    problems = [ParsedBocaScoreboardProblem(name=p, tries=1, solved_at=10, is_solved=True) for p in solved]
    return ParsedBocaScoreboardTeam(
        name=name, place=place, user_site="site1", total_solved=total_solved, total_penalty=total_penalty,
        problems=problems,
    )


class FilterTeamsTest(unittest.TestCase):
    def test_no_scoreboard_returns_empty(self) -> None:
        notifier = ScoreboardNotifier()
        self.assertEqual(notifier._filter_teams(None, {"itsur"}), [])

    def test_matches_substring_case_and_accent_insensitively(self) -> None:
        notifier = ScoreboardNotifier()
        scoreboard = ParsedBocaScoreboard(teams=[_team("[Culiacán Tech] Team A"), _team("[UAS] Team B")])

        result = notifier._filter_teams(scoreboard, {"culiacan"})

        self.assertEqual([t.name for t in result], ["[Culiacán Tech] Team A"])

    def test_matches_any_of_multiple_queries(self) -> None:
        notifier = ScoreboardNotifier()
        scoreboard = ParsedBocaScoreboard(teams=[_team("[ITSUR] Team A"), _team("[UAS] Team B")])

        result = notifier._filter_teams(scoreboard, {"itsur", "uas"})

        self.assertEqual(len(result), 2)


class GetTeamSummaryTest(unittest.TestCase):
    def test_formats_place_name_and_score(self) -> None:
        notifier = ScoreboardNotifier()
        team = _team("[ITSUR] Team A", place=3, total_solved=4, total_penalty=120)

        self.assertEqual(
            notifier._get_team_summary(team),
            "<b>#3</b> <code>[ITSUR] Team A</code>: 4 AC (120)",
        )


class GetCurrentRankTest(unittest.TestCase):
    def test_joins_team_summaries(self) -> None:
        notifier = ScoreboardNotifier()
        teams = [_team("[ITSUR] Team A", place=1), _team("[UAS] Team B", place=2)]

        result = notifier._get_current_rank(teams)

        self.assertEqual(
            result,
            "<b>#1</b> <code>[ITSUR] Team A</code>: 1 AC (0)\n<b>#2</b> <code>[UAS] Team B</code>: 1 AC (0)",
        )

    def test_truncates_and_warns_beyond_max_notification_team_count(self) -> None:
        notifier = ScoreboardNotifier()
        teams = [_team(f"Team {i}", place=i) for i in range(1, 32)]

        result = notifier._get_current_rank(teams)

        self.assertTrue(result.startswith("Solo se muestran los primeros 30 equipos de los 31 encontrados:\n\n"))
        self.assertEqual(result.count("<b>#"), 30)


class GetSolvedDiffSummaryTest(unittest.TestCase):
    def test_no_new_solves_is_empty(self) -> None:
        notifier = ScoreboardNotifier()
        old_team = _team_with_problems("A", total_solved=1, solved=["A"])
        new_team = _team_with_problems("A", total_solved=1, solved=["A"])

        self.assertEqual(notifier._get_solved_diff_summary(old_team, new_team), "")

    def test_single_new_solve(self) -> None:
        notifier = ScoreboardNotifier()
        old_team = _team_with_problems("A", total_solved=0, solved=[])
        new_team = _team_with_problems("A", total_solved=1, solved=["A"])

        self.assertEqual(
            notifier._get_solved_diff_summary(old_team, new_team),
            "el problema A, llegando a un total de <b>1</b> problemas resueltos",
        )

    def test_multiple_new_solves(self) -> None:
        notifier = ScoreboardNotifier()
        old_team = _team_with_problems("A", total_solved=0, solved=[])
        new_team = _team_with_problems("A", total_solved=2, solved=["A", "B"])

        self.assertEqual(
            notifier._get_solved_diff_summary(old_team, new_team),
            "2 problemas (A, B), llegando a un total de <b>2</b> problemas resueltos",
        )


class GetRankUpdateTest(unittest.TestCase):
    def test_new_team_is_reported_when_there_were_previous_teams(self) -> None:
        notifier = ScoreboardNotifier()
        contest = ContestFactory.build(starts_at=datetime.utcnow() - timedelta(hours=5))
        old_teams = [_team_with_problems("[ITSUR] Team A", total_solved=0, solved=[])]
        new_teams = old_teams + [_team_with_problems("[UAS] Team B", total_solved=0, solved=[])]

        result = notifier._get_rank_update(old_teams, new_teams, contest)

        self.assertEqual(result, "El equipo <code>[UAS] Team B</code> apareció en el scoreboard")

    def test_new_team_with_no_previous_teams_is_reported_right_after_contest_starts(self) -> None:
        notifier = ScoreboardNotifier()
        contest = ContestFactory.build(starts_at=datetime.utcnow() - timedelta(minutes=5))
        new_teams = [_team_with_problems("[ITSUR] Team A", total_solved=0, solved=[])]

        result = notifier._get_rank_update([], new_teams, contest)

        self.assertEqual(result, "El equipo <code>[ITSUR] Team A</code> apareció en el scoreboard")

    def test_new_team_with_no_previous_teams_is_ignored_long_after_contest_starts(self) -> None:
        notifier = ScoreboardNotifier()
        contest = ContestFactory.build(starts_at=datetime.utcnow() - timedelta(hours=1))
        new_teams = [_team_with_problems("[ITSUR] Team A", total_solved=0, solved=[])]

        result = notifier._get_rank_update([], new_teams, contest)

        self.assertEqual(result, "")

    def test_reports_newly_solved_problems_and_rank_change(self) -> None:
        notifier = ScoreboardNotifier()
        contest = ContestFactory.build(starts_at=datetime.utcnow() - timedelta(hours=1))
        old_team = _team_with_problems("[ITSUR] Team A", total_solved=1, solved=["A"], place=2, total_penalty=20)
        new_team = _team_with_problems("[ITSUR] Team A", total_solved=2, solved=["A", "B"], place=1,
                                        total_penalty=60)

        result = notifier._get_rank_update([old_team], [new_team], contest)

        self.assertEqual(result, "<code>[ITSUR] Team A</code> | B -> 2 AC (60) | #2 -> #1")

    def test_no_solve_change_is_not_reported(self) -> None:
        notifier = ScoreboardNotifier()
        contest = ContestFactory.build(starts_at=datetime.utcnow() - timedelta(hours=1))
        team = _team_with_problems("[ITSUR] Team A", total_solved=1, solved=["A"])

        result = notifier._get_rank_update([team], [team], contest)

        self.assertEqual(result, "")
