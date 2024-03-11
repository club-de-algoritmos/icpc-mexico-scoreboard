import enum

from django.db import models


@enum.unique
class ScoreboardStatus(models.TextChoices):
    INVISIBLE = "invisible"
    VISIBLE = "visible"
    FROZEN = "frozen"
    WAITING_TO_BE_RELEASED = "waiting_to_be_released"
    RELEASED = "released"
    ARCHIVED = "archived"

    @staticmethod
    def is_finished(status: "ScoreboardStatus") -> bool:
        return status in [ScoreboardStatus.WAITING_TO_BE_RELEASED, ScoreboardStatus.RELEASED, ScoreboardStatus.ARCHIVED]


class Contest(models.Model):
    name = models.CharField(max_length=255)
    scoreboard_url = models.CharField(max_length=511)
    scoreboard_status = models.CharField(
        max_length=100, choices=ScoreboardStatus.choices, default=ScoreboardStatus.INVISIBLE)
    starts_at = models.DateTimeField()
    freezes_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    max_teams_to_advance = models.IntegerField(null=True)
    max_teams_per_school_to_advance = models.IntegerField(null=True)

    @property
    def is_official(self) -> bool:
        return "redprogramacioncompetitiva" not in self.scoreboard_url


class ScoreboardUser(models.Model):
    telegram_chat_id = models.IntegerField(unique=True)


class ScoreboardSubscription(models.Model):
    user = models.ForeignKey(ScoreboardUser, on_delete=models.PROTECT, related_name="+")
    subscription = models.CharField(max_length=100, null=True)
    top = models.IntegerField(null=True)


# TODO: Add Scoreboard and Team models
