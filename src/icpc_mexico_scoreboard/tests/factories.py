from datetime import datetime, timezone

import factory
from factory.django import DjangoModelFactory

from icpc_mexico_scoreboard.db.models import Contest, ScoreboardStatus


class ContestFactory(DjangoModelFactory):
    class Meta:
        model = Contest

    name = factory.Sequence(lambda n: f"Contest {n}")
    scoreboard_url = "https://score.icpcmexico.org"
    scoreboard_status = ScoreboardStatus.INVISIBLE
    starts_at = factory.LazyFunction(lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))
    freezes_at = factory.LazyFunction(lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))
    ends_at = factory.LazyFunction(lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))
