from django.db import models


class Contest(models.Model):
    name = models.CharField(max_length=255)
    scoreboard_url = models.CharField(max_length=511)
    starts_at = models.DateTimeField()
    freezes_at = models.DateTimeField()
    ends_at = models.DateTimeField()


class ScoreboardUser(models.Model):
    telegram_chat_id = models.IntegerField(db_index=True)


class ScoreboardSubscription(models.Model):
    user = models.ForeignKey(ScoreboardUser, on_delete=models.PROTECT, related_name="+")
    subscription = models.CharField(max_length=100)
