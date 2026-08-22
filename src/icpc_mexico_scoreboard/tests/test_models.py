import unittest
from datetime import datetime, timezone

from django.test import TestCase

from icpc_mexico_scoreboard.db.models import Contest, ScoreboardStatus


def _make_contest(scoreboard_url: str) -> Contest:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return Contest.objects.create(
        name="ICPC Mexico Regional",
        scoreboard_url=scoreboard_url,
        starts_at=now,
        freezes_at=now,
        ends_at=now,
    )


class ContestStrTest(TestCase):
    def setUp(self) -> None:
        self.contest = _make_contest("https://score.icpcmexico.org")

    def test_includes_name(self) -> None:
        self.assertEqual(str(self.contest), "Contest ICPC Mexico Regional")


class ContestIsOfficialTest(TestCase):
    def test_official_scoreboard_is_official(self) -> None:
        contest = _make_contest("https://score.icpcmexico.org")
        self.assertTrue(contest.is_official)

    def test_rpc_scoreboard_is_not_official(self) -> None:
        contest = _make_contest("https://redprogramacioncompetitiva.com/scoreboard")
        self.assertFalse(contest.is_official)


class ScoreboardStatusIsFinishedTest(unittest.TestCase):
    def test_waiting_to_be_released_is_finished(self) -> None:
        self.assertTrue(ScoreboardStatus.is_finished(ScoreboardStatus.WAITING_TO_BE_RELEASED))

    def test_released_is_finished(self) -> None:
        self.assertTrue(ScoreboardStatus.is_finished(ScoreboardStatus.RELEASED))

    def test_archived_is_finished(self) -> None:
        self.assertTrue(ScoreboardStatus.is_finished(ScoreboardStatus.ARCHIVED))

    def test_visible_is_not_finished(self) -> None:
        self.assertFalse(ScoreboardStatus.is_finished(ScoreboardStatus.VISIBLE))

    def test_frozen_is_not_finished(self) -> None:
        self.assertFalse(ScoreboardStatus.is_finished(ScoreboardStatus.FROZEN))
