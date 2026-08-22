from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from asgiref.sync import async_to_sync
from django.test import TestCase

from icpc_mexico_scoreboard.db.models import Contest, ScoreboardStatus
from icpc_mexico_scoreboard.scoreboard_notifier import ScoreboardNotifier
from icpc_mexico_scoreboard.tests.factories import ContestFactory


def _make_notifier() -> ScoreboardNotifier:
    notifier = ScoreboardNotifier()
    notifier._telegram = AsyncMock()
    return notifier


# `_admin` calls `db.close_old_connections()`, which really closes the DB connection and would
# break the TestCase's wrapping transaction, so it's mocked out in every test here.
@patch("icpc_mexico_scoreboard.scoreboard_notifier.db.close_old_connections")
class AdminInvalidCommandTest(TestCase):
    def test_unknown_command_reports_the_valid_options(self, mock_close: AsyncMock) -> None:
        notifier = _make_notifier()

        async_to_sync(notifier._admin)("bogus")

        message = notifier._telegram.send_developer_message.await_args.args[0]
        self.assertIn("Invalid command", message)
        self.assertEqual(Contest.objects.count(), 0)


@patch("icpc_mexico_scoreboard.scoreboard_notifier.db.close_old_connections")
class AdminAddTest(TestCase):
    def test_creates_a_contest(self, mock_close: AsyncMock) -> None:
        notifier = _make_notifier()

        async_to_sync(notifier._admin)(
            "add https://score.icpcmexico.org 2026-03-01T08:00:00 ICPC Mexico Regional"
        )

        contest = Contest.objects.get()
        self.assertEqual(contest.name, "ICPC Mexico Regional")
        self.assertEqual(contest.scoreboard_url, "https://score.icpcmexico.org")
        self.assertEqual(contest.starts_at, datetime(2026, 3, 1, 8, 0, 0))
        self.assertEqual(contest.freezes_at, datetime(2026, 3, 1, 12, 0, 0))
        self.assertEqual(contest.ends_at, datetime(2026, 3, 1, 13, 0, 0))
        self.assertEqual(contest.scoreboard_status, ScoreboardStatus.INVISIBLE)
        self.assertEqual(notifier._telegram.send_developer_message.await_args.args[0], "Contest created!")

    def test_too_few_params_does_not_create_a_contest(self, mock_close: AsyncMock) -> None:
        notifier = _make_notifier()

        async_to_sync(notifier._admin)("add https://score.icpcmexico.org")

        self.assertEqual(Contest.objects.count(), 0)
        message = notifier._telegram.send_developer_message.await_args.args[0]
        self.assertIn("Not enough parameters", message)


@patch("icpc_mexico_scoreboard.scoreboard_notifier.db.close_old_connections")
class AdminNoContestTest(TestCase):
    def test_reports_when_no_contest_exists(self, mock_close: AsyncMock) -> None:
        notifier = _make_notifier()

        async_to_sync(notifier._admin)("name NuevoNombre")

        message = notifier._telegram.send_developer_message.await_args.args[0]
        self.assertEqual(message, "No contest is running")


def _next_contest(**kwargs) -> Contest:
    kwargs.setdefault("starts_at", datetime.utcnow() + timedelta(days=1))
    return ContestFactory(**kwargs)


@patch("icpc_mexico_scoreboard.scoreboard_notifier.db.close_old_connections")
class AdminEditContestTest(TestCase):
    def test_name_replaces_the_contest_name(self, mock_close: AsyncMock) -> None:
        contest = _next_contest(name="Old Name")
        notifier = _make_notifier()

        async_to_sync(notifier._admin)("name NuevoNombre")

        contest.refresh_from_db()
        self.assertEqual(contest.name, "NuevoNombre")
        self.assertEqual(notifier._telegram.send_developer_message.await_args.args[0], "Done!")

    def test_scoreboard_replaces_the_scoreboard_url(self, mock_close: AsyncMock) -> None:
        contest = _next_contest()
        notifier = _make_notifier()

        async_to_sync(notifier._admin)("scoreboard https://score.icpcmexico.org/new")

        contest.refresh_from_db()
        self.assertEqual(contest.scoreboard_url, "https://score.icpcmexico.org/new")

    def test_time_shifts_all_three_timestamps(self, mock_close: AsyncMock) -> None:
        contest = _next_contest(
            starts_at=datetime(2026, 3, 1, 8, 0, 0),
            freezes_at=datetime(2026, 3, 1, 12, 0, 0),
            ends_at=datetime(2026, 3, 1, 13, 0, 0),
        )
        notifier = _make_notifier()

        async_to_sync(notifier._admin)("time 2 hours")

        contest.refresh_from_db()
        self.assertEqual(contest.starts_at, datetime(2026, 3, 1, 10, 0, 0))
        self.assertEqual(contest.freezes_at, datetime(2026, 3, 1, 14, 0, 0))
        self.assertEqual(contest.ends_at, datetime(2026, 3, 1, 15, 0, 0))

    def test_status_updates_the_scoreboard_status(self, mock_close: AsyncMock) -> None:
        contest = _next_contest(scoreboard_status=ScoreboardStatus.INVISIBLE)
        notifier = _make_notifier()

        async_to_sync(notifier._admin)("status visible")

        contest.refresh_from_db()
        self.assertEqual(contest.scoreboard_status, ScoreboardStatus.VISIBLE)

    def test_status_without_a_value_reports_the_valid_options(self, mock_close: AsyncMock) -> None:
        contest = _next_contest(scoreboard_status=ScoreboardStatus.INVISIBLE)
        notifier = _make_notifier()

        async_to_sync(notifier._admin)("status")

        contest.refresh_from_db()
        self.assertEqual(contest.scoreboard_status, ScoreboardStatus.INVISIBLE)
        message = notifier._telegram.send_developer_message.await_args.args[0]
        self.assertIn("Specify the status", message)

    def test_max_teams_replaces_the_max_teams_to_advance(self, mock_close: AsyncMock) -> None:
        contest = _next_contest(max_teams_to_advance=None)
        notifier = _make_notifier()

        async_to_sync(notifier._admin)("max-teams 8")

        contest.refresh_from_db()
        self.assertEqual(contest.max_teams_to_advance, 8)
