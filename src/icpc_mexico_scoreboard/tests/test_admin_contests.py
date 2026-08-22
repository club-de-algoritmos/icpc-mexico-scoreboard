from datetime import datetime, timedelta

from django.test import TestCase

from icpc_mexico_scoreboard.admin.contests import create_contest, shift_contest_time
from icpc_mexico_scoreboard.db.models import ScoreboardStatus
from icpc_mexico_scoreboard.tests.factories import ContestFactory


class CreateContestTest(TestCase):
    def test_defaults_to_four_hour_freeze_and_five_hour_duration(self) -> None:
        starts_at = datetime(2026, 3, 1, 8, 0, 0)

        contest = create_contest("ICPC Mexico Regional", starts_at)

        self.assertEqual(contest.freezes_at, starts_at + timedelta(hours=4))
        self.assertEqual(contest.ends_at, starts_at + timedelta(hours=5))

    def test_masters_contest_uses_a_shorter_duration(self) -> None:
        starts_at = datetime(2026, 3, 1, 8, 0, 0)

        contest = create_contest("ICPC Masters Sinaloa", starts_at)

        self.assertEqual(contest.freezes_at, starts_at + timedelta(minutes=140))
        self.assertEqual(contest.ends_at, starts_at + timedelta(hours=3))

    def test_masters_match_is_case_insensitive(self) -> None:
        starts_at = datetime(2026, 3, 1, 8, 0, 0)

        contest = create_contest("MASTERS Culiacan", starts_at)

        self.assertEqual(contest.ends_at, starts_at + timedelta(hours=3))

    def test_defaults_url_and_status_when_not_given(self) -> None:
        contest = create_contest("ICPC Mexico Regional", datetime(2026, 3, 1, 8, 0, 0))

        self.assertEqual(contest.scoreboard_url, "https://score.icpcmexico.org")
        self.assertEqual(contest.scoreboard_status, ScoreboardStatus.INVISIBLE)

    def test_honors_a_custom_url_and_status(self) -> None:
        contest = create_contest(
            "ICPC Mexico Regional",
            datetime(2026, 3, 1, 8, 0, 0),
            scoreboard_url="https://redprogramacioncompetitiva.com/scoreboard",
            scoreboard_status=ScoreboardStatus.VISIBLE,
        )

        self.assertEqual(contest.scoreboard_url, "https://redprogramacioncompetitiva.com/scoreboard")
        self.assertEqual(contest.scoreboard_status, ScoreboardStatus.VISIBLE)


class ShiftContestTimeTest(TestCase):
    def test_shifts_all_three_timestamps_and_persists(self) -> None:
        contest = ContestFactory(
            starts_at=datetime(2026, 3, 1, 8, 0, 0),
            freezes_at=datetime(2026, 3, 1, 12, 0, 0),
            ends_at=datetime(2026, 3, 1, 13, 0, 0),
        )

        shift_contest_time(contest, timedelta(days=1))

        contest.refresh_from_db()
        self.assertEqual(contest.starts_at, datetime(2026, 3, 2, 8, 0, 0))
        self.assertEqual(contest.freezes_at, datetime(2026, 3, 2, 12, 0, 0))
        self.assertEqual(contest.ends_at, datetime(2026, 3, 2, 13, 0, 0))
