import enum

from django.db import models


@enum.unique
class ScoreboardStatus(models.TextChoices):
    VISIBLE = "visible"
    FROZEN = "frozen"
    RELEASED = "released"


class Contest(models.Model):
    name = models.CharField(max_length=255)
    scoreboard_url = models.CharField(max_length=511)
    scoreboard_status = models.CharField(
        max_length=100, choices=ScoreboardStatus.choices, default=ScoreboardStatus.VISIBLE)
    starts_at = models.DateTimeField()
    freezes_at = models.DateTimeField()
    ends_at = models.DateTimeField()


class ScoreboardUser(models.Model):
    telegram_chat_id = models.IntegerField(unique=True)


class ScoreboardSubscription(models.Model):
    user = models.ForeignKey(ScoreboardUser, on_delete=models.PROTECT, related_name="+")
    subscription = models.CharField(max_length=100)
