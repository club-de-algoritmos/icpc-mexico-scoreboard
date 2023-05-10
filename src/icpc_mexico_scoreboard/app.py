import logging

from icpc_mexico_scoreboard.scoreboard_notifier import ScoreboardNotifier


async def start() -> None:
    logging.basicConfig(level=logging.DEBUG)
    scoreboard = ScoreboardNotifier()
    await scoreboard.start_running()
