from datetime import datetime

import factory
from factory.django import DjangoModelFactory

from icpc_mexico_scoreboard.db.models import Contest, ScoreboardStatus, ScoreboardSubscription, ScoreboardUser

# USE_TZ is not set (defaults to False), so this codebase works with naive datetimes throughout,
# always representing UTC by convention (e.g. `_get_last_contest`/`_get_next_contest` compare
# against `datetime.utcnow()`) — factories must stick to naive datetimes too, not aware ones.
_DEFAULT_CONTEST_TIME = datetime(2026, 1, 1)


class ContestFactory(DjangoModelFactory):
    class Meta:
        model = Contest

    name = factory.Sequence(lambda n: f"Contest {n}")
    scoreboard_url = "https://score.icpcmexico.org"
    scoreboard_status = ScoreboardStatus.INVISIBLE
    starts_at = _DEFAULT_CONTEST_TIME
    freezes_at = _DEFAULT_CONTEST_TIME
    ends_at = _DEFAULT_CONTEST_TIME


class ScoreboardUserFactory(DjangoModelFactory):
    class Meta:
        model = ScoreboardUser

    telegram_chat_id = factory.Sequence(lambda n: n)


class ScoreboardSubscriptionFactory(DjangoModelFactory):
    class Meta:
        model = ScoreboardSubscription

    user = factory.SubFactory(ScoreboardUserFactory)
