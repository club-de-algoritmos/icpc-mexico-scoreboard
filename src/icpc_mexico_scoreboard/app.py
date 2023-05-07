import logging

from icpc_mexico_scoreboard.rank_notifier import ScoreboardNotifier


async def start() -> None:
    logging.basicConfig(level=logging.DEBUG)
    scoreboard = ScoreboardNotifier()
    await scoreboard.start_running()
