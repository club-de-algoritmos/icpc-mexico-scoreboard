from datetime import datetime, timedelta

from asgiref.sync import async_to_sync
from django.test import TestCase

from icpc_mexico_scoreboard.db.models import ScoreboardStatus
from icpc_mexico_scoreboard.scoreboard_notifier import _delete_user, _get_current_contest, _get_last_contest, \
    _get_next_contest, _get_or_create_user, _get_team_subscriptions, _get_top_subscription, _get_user, \
    _get_users_with_subscriptions
from icpc_mexico_scoreboard.tests.factories import ContestFactory, ScoreboardSubscriptionFactory, \
    ScoreboardUserFactory


class GetOrCreateUserTest(TestCase):
    def test_creates_a_new_user(self) -> None:
        user = async_to_sync(_get_or_create_user)(12345)
        self.assertEqual(user.telegram_chat_id, 12345)

    def test_returns_the_existing_user(self) -> None:
        existing = ScoreboardUserFactory(telegram_chat_id=12345)
        user = async_to_sync(_get_or_create_user)(12345)
        self.assertEqual(user.pk, existing.pk)


class GetUserTest(TestCase):
    def test_returns_none_when_missing(self) -> None:
        self.assertIsNone(async_to_sync(_get_user)(12345))

    def test_returns_the_user(self) -> None:
        existing = ScoreboardUserFactory(telegram_chat_id=12345)
        user = async_to_sync(_get_user)(12345)
        self.assertEqual(user.pk, existing.pk)


class DeleteUserTest(TestCase):
    def test_deletes_the_user_and_their_subscriptions(self) -> None:
        user = ScoreboardUserFactory()
        ScoreboardSubscriptionFactory(user=user, subscription="itsur")

        async_to_sync(_delete_user)(user)

        self.assertIsNone(async_to_sync(_get_user)(user.telegram_chat_id))


class GetTeamSubscriptionsTest(TestCase):
    def test_returns_subscriptions_sorted(self) -> None:
        user = ScoreboardUserFactory()
        ScoreboardSubscriptionFactory(user=user, subscription="uas")
        ScoreboardSubscriptionFactory(user=user, subscription="itsur")

        self.assertEqual(async_to_sync(_get_team_subscriptions)(user), ["itsur", "uas"])

    def test_excludes_top_subscriptions(self) -> None:
        user = ScoreboardUserFactory()
        ScoreboardSubscriptionFactory(user=user, top=5)

        self.assertEqual(async_to_sync(_get_team_subscriptions)(user), [])


class GetTopSubscriptionTest(TestCase):
    def test_returns_none_when_not_subscribed(self) -> None:
        user = ScoreboardUserFactory()
        self.assertIsNone(async_to_sync(_get_top_subscription)(user))

    def test_returns_the_subscribed_top(self) -> None:
        user = ScoreboardUserFactory()
        ScoreboardSubscriptionFactory(user=user, top=5)

        self.assertEqual(async_to_sync(_get_top_subscription)(user), 5)

    def test_caps_at_the_max_notification_team_count(self) -> None:
        user = ScoreboardUserFactory()
        ScoreboardSubscriptionFactory(user=user, top=1000)

        self.assertEqual(async_to_sync(_get_top_subscription)(user), 30)


class GetUsersWithSubscriptionsTest(TestCase):
    def test_only_includes_users_with_a_subscription(self) -> None:
        subscribed_user = ScoreboardUserFactory()
        ScoreboardSubscriptionFactory(user=subscribed_user, subscription="itsur")
        ScoreboardUserFactory()  # No subscriptions

        users = async_to_sync(_get_users_with_subscriptions)()

        self.assertEqual([u.pk for u in users], [subscribed_user.pk])


class GetLastAndNextContestTest(TestCase):
    def test_last_contest_is_the_most_recently_started_one(self) -> None:
        now = datetime.utcnow()
        ContestFactory(starts_at=now - timedelta(days=2))
        recent = ContestFactory(starts_at=now - timedelta(days=1))

        contest = async_to_sync(_get_last_contest)()

        self.assertEqual(contest.pk, recent.pk)

    def test_last_contest_ignores_future_contests(self) -> None:
        now = datetime.utcnow()
        ContestFactory(starts_at=now + timedelta(days=1))

        self.assertIsNone(async_to_sync(_get_last_contest)())

    def test_next_contest_is_the_soonest_upcoming_one(self) -> None:
        now = datetime.utcnow()
        ContestFactory(starts_at=now + timedelta(days=2))
        soonest = ContestFactory(starts_at=now + timedelta(days=1))

        contest = async_to_sync(_get_next_contest)()

        self.assertEqual(contest.pk, soonest.pk)

    def test_next_contest_ignores_started_contests(self) -> None:
        now = datetime.utcnow()
        ContestFactory(starts_at=now - timedelta(days=1))

        self.assertIsNone(async_to_sync(_get_next_contest)())


class GetCurrentContestTest(TestCase):
    def test_no_contests_at_all_returns_none(self) -> None:
        self.assertIsNone(async_to_sync(_get_current_contest)())

    def test_only_a_future_contest_returns_it(self) -> None:
        now = datetime.utcnow()
        next_contest = ContestFactory(starts_at=now + timedelta(days=1))

        contest = async_to_sync(_get_current_contest)()

        self.assertEqual(contest.pk, next_contest.pk)

    def test_unfinished_last_contest_takes_priority_over_next(self) -> None:
        now = datetime.utcnow()
        last_contest = ContestFactory(starts_at=now - timedelta(hours=1), scoreboard_status=ScoreboardStatus.VISIBLE)
        ContestFactory(starts_at=now + timedelta(minutes=30))

        contest = async_to_sync(_get_current_contest)()

        self.assertEqual(contest.pk, last_contest.pk)

    def test_finished_last_contest_with_imminent_next_returns_next(self) -> None:
        now = datetime.utcnow()
        ContestFactory(starts_at=now - timedelta(days=1), scoreboard_status=ScoreboardStatus.RELEASED)
        next_contest = ContestFactory(starts_at=now + timedelta(hours=1))

        contest = async_to_sync(_get_current_contest)()

        self.assertEqual(contest.pk, next_contest.pk)

    def test_finished_last_contest_with_distant_next_returns_last(self) -> None:
        now = datetime.utcnow()
        last_contest = ContestFactory(
            starts_at=now - timedelta(days=1), scoreboard_status=ScoreboardStatus.RELEASED
        )
        ContestFactory(starts_at=now + timedelta(days=5))

        contest = async_to_sync(_get_current_contest)()

        self.assertEqual(contest.pk, last_contest.pk)

    def test_archived_last_contest_returns_next_even_if_distant(self) -> None:
        now = datetime.utcnow()
        ContestFactory(starts_at=now - timedelta(days=10), scoreboard_status=ScoreboardStatus.ARCHIVED)
        next_contest = ContestFactory(starts_at=now + timedelta(days=5))

        contest = async_to_sync(_get_current_contest)()

        self.assertEqual(contest.pk, next_contest.pk)

    def test_archived_last_contest_with_no_next_returns_none(self) -> None:
        now = datetime.utcnow()
        ContestFactory(starts_at=now - timedelta(days=10), scoreboard_status=ScoreboardStatus.ARCHIVED)

        self.assertIsNone(async_to_sync(_get_current_contest)())
