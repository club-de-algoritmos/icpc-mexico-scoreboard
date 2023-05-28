from datetime import datetime, timedelta

from icpc_mexico_scoreboard.db.models import Contest, ScoreboardStatus


def create_contest(
        name: str,
        starts_at: datetime,
        scoreboard_url: str = 'https://score.icpcmexico.org',
        scoreboard_status: ScoreboardStatus = ScoreboardStatus.INVISIBLE,
) -> Contest:
    freezes_at = starts_at + timedelta(hours=4)
    ends_at = starts_at + timedelta(hours=5)

    return Contest.objects.create(
        name=name,
        scoreboard_url=scoreboard_url,
        scoreboard_status=scoreboard_status,
        starts_at=starts_at,
        freezes_at=freezes_at,
        ends_at=ends_at,
    )
