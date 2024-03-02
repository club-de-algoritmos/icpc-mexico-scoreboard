from datetime import datetime, timedelta

from icpc_mexico_scoreboard.db.models import Contest, ScoreboardStatus


def create_contest(
        name: str,
        starts_at: datetime,
        scoreboard_url: str = 'https://score.icpcmexico.org',
        scoreboard_status: ScoreboardStatus = ScoreboardStatus.INVISIBLE,
) -> Contest:
    unfrozen_duration = timedelta(hours=4)
    total_duration = timedelta(hours=5)
    if "masters" in name.lower():
        unfrozen_duration = timedelta(minutes=140)
        total_duration = timedelta(hours=3)
    freezes_at = starts_at + unfrozen_duration
    ends_at = starts_at + total_duration

    return Contest.objects.create(
        name=name,
        scoreboard_url=scoreboard_url,
        scoreboard_status=scoreboard_status,
        starts_at=starts_at,
        freezes_at=freezes_at,
        ends_at=ends_at,
    )


def shift_contest_time(contest: Contest, shift: timedelta) -> None:
    contest.starts_at += shift
    contest.freezes_at += shift
    contest.ends_at += shift
    contest.save()
