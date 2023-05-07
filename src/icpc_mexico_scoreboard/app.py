from icpc_mexico_scoreboard.rank_notifier import ScoreboardNotifier


async def start() -> None:
    scoreboard = ScoreboardNotifier()
    await scoreboard.start_running()
