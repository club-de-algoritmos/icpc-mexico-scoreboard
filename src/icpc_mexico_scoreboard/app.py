import logging

from icpc_mexico_scoreboard.scoreboard_notifier import ScoreboardNotifier


async def start() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('icpc_mexico_scoreboard').setLevel(logging.DEBUG)
    scoreboard = ScoreboardNotifier()
    await scoreboard.start_running()
