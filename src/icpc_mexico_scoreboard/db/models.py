from django.db import models


class ScoreboardUser(models.Model):
    telegram_chat_id = models.IntegerField(db_index=True)


class ScoreboardSubscription(models.Model):
    user = models.ForeignKey(ScoreboardUser, on_delete=models.PROTECT, related_name="+")
    subscription = models.CharField(max_length=100)
