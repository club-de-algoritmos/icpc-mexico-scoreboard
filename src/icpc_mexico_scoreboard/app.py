from icpc_mexico_scoreboard.rank_notifier import notify_rank_updates_until_finished


async def start() -> None:
    await notify_rank_updates_until_finished("https://score.icpcmexico.org", "IT Culiacan|UASinaloa|FIMAZ")
