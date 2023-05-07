import asyncio
import logging
import os
from datetime import datetime
from typing import List, Dict, Set, Optional

from icpc_mexico_scoreboard.parser import parse_boca_scoreboard, NotAScoreboardError
from icpc_mexico_scoreboard.telegram_notifier import TelegramNotifier, TelegramUser
from icpc_mexico_scoreboard.types import ParsedBocaScoreboard, ParsedBocaScoreboardTeam, Contest, ScoreboardUser

logger = logging.getLogger(__name__)


_DEVELOPER_CHAT_ID = int(os.environ["ICPC_MX_TELEGRAM_DEVELOPER_CHAT_ID"])


def escape(value):
    chars = ["_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"]
    escaped = str(value)
    for char in chars:
        escaped = escaped.replace(char, f"\\{char}")
    return escaped


class ScoreboardNotifier:
    _telegram: Optional[TelegramNotifier] = None
    # TODO: Use a lock to write/read scoreboards
    _previous_scoreboard: Optional[ParsedBocaScoreboard] = None
    _scoreboard: Optional[ParsedBocaScoreboard] = None

    async def start_running(self) -> None:
        logger.debug('Starting up')
        self._telegram = TelegramNotifier()
        await self._telegram.start_running(get_rank_callback=self._get_rank)
        await self._start_parsing_scoreboards()

    async def _start_parsing_scoreboards(self) -> None:
        logger.debug('Starting to parse scoreboards')
        previous_contest = None
        while True:
            contest = self._get_current_contest(actively_running_only=True)
            if not contest:
                logger.debug('No contest identified')
                if previous_contest:
                    await self._notify_contest_has_ended(previous_contest)
                    previous_contest = None

                await asyncio.sleep(60)
                continue

            logger.debug(f'Parsing the scoreboard of contest {contest.name}')
            try:
                scoreboard = parse_boca_scoreboard(contest.scoreboard_url)
                self._previous_scoreboard = self._scoreboard
                self._scoreboard = scoreboard
                await self._notify_rank_updates()
            except NotAScoreboardError:
                logger.info(f"El concurso {contest.name} no ha iniciado")
            except Exception as e:
                logging.exception('Unexpected error')
                await self._notify_error(str(e))

            previous_contest = contest
            await asyncio.sleep(60)

    async def stop_running(self) -> None:
        await self._telegram.stop_running()

    def _get_current_contest(self, actively_running_only: bool) -> Optional[Contest]:
        # TODO: Implement actively_running_only
        # TODO: Get from DB
        return Contest(name='ICPC Mexico 2022 - TEST',
                       scoreboard_url="https://score.icpcmexico.org",
                       starts_at=datetime(2022, 1, 1, 0, 0, 0),
                       freezes_at=datetime(2024, 1, 1, 0, 0, 0),
                       ends_at=datetime(2024, 1, 1, 0, 0, 0))

    def _get_users_with_subscriptions(self) -> List[ScoreboardUser]:
        return [ScoreboardUser(telegram_chat_id=_DEVELOPER_CHAT_ID,
                               team_query_subscription="IT Culiacan, UASinaloa, FIMAZ")]

    def _get_user_by_telegram_chat_id(self, telegram_chat_id: int) -> Optional[ScoreboardUser]:
        return next(user for user in self._get_users_with_subscriptions() if user.telegram_chat_id == telegram_chat_id)

    async def _get_rank(self, telegram_user: TelegramUser) -> None:
        contest = self._get_current_contest(actively_running_only=False)
        if not contest:
            await self._telegram.send_message('No hay concurso actual', telegram_user.chat_id)
            return

        if not self._scoreboard:
            await self._telegram.send_message(f'Todavía no tenemos el scoreboard del concurso <i>{contest.name}</i>, '
                                              f'reintenta de nuevo más tarde',
                                              telegram_user.chat_id)
            return

        user = self._get_user_by_telegram_chat_id(telegram_user.chat_id)
        if not user or not user.team_query_subscription:
            await self._telegram.send_message('No sigues ningún equipo, ejecuta el commando '
                                              '<code>/seguir <subcadena1>, <subcadena2>, ...</code> '
                                              'para seguir los equipos que quieres',
                                              telegram_user.chat_id)
            return

        watched_teams = self._filter_teams(self._scoreboard, user.team_query_subscription)
        current_rank = self._get_current_rank(watched_teams)
        await self._telegram.send_message(current_rank or 'Ningún equipo que sigues fué encontrado',
                                          telegram_user.chat_id)

    async def _notify_error(self, error: str) -> None:
        await self._telegram.send_message(f"Got unexpected error: <code>{error}</code>", _DEVELOPER_CHAT_ID)

    async def _notify_info(self, info: str) -> None:
        logger.info(info)
        await self._telegram.send_message(info, _DEVELOPER_CHAT_ID)

    def _filter_teams(self, scoreboard: Optional[ParsedBocaScoreboard], team_query: str
                      ) -> List[ParsedBocaScoreboardTeam]:
        if not scoreboard:
            return []

        def matches_team(team: ParsedBocaScoreboardTeam) -> bool:
            for subquery in team_query.lower().split(','):
                if subquery.strip() in team.name.lower():
                    return True
            return False

        return list(filter(matches_team, scoreboard.teams))

    def _get_solved_names(self, team: ParsedBocaScoreboardTeam) -> Set[str]:
        return set(map(lambda p: p.name, filter(lambda p: p.is_solved, team.problems)))

    def _solved_as_str(self, solved: Set[str]) -> str:
        return "(" + ", ".join(sorted(solved)) + ")"

    def _get_solved_summary(self, team: ParsedBocaScoreboardTeam) -> str:
        if not team.total_solved:
            return "0 problemas"

        solved_names = self._solved_as_str(self._get_solved_names(team))
        if team.total_solved == 1:
            return f"1 problema {solved_names}"
        return f"{team.total_solved} problemas {solved_names}"

    def _get_current_rank(self, teams: List[ParsedBocaScoreboardTeam]) -> str:
        def get_rank(team: ParsedBocaScoreboardTeam) -> str:
            solved_summary = self._get_solved_summary(team)
            return f"<b>#{team.place}</b> <code>{team.name}</code> " \
                   f"resolvió {solved_summary} en {team.total_penalty} minutos"

        sorted_teams = sorted(teams, key=lambda t: (t.place, t.name.lower()))
        return "\n".join(map(get_rank, sorted_teams))

    def _get_solved_diff_summary(self, old_team: ParsedBocaScoreboardTeam, new_team: ParsedBocaScoreboardTeam) -> str:
        solved = new_team.total_solved - old_team.total_solved
        if not solved:
            return ""

        solved_names = self._solved_as_str(self._get_solved_names(new_team).difference(self._get_solved_names(old_team)))
        if solved == 1:
            return f"1 problema {solved_names}"
        return f"{solved} problemas {solved_names}"

    def _get_rank_update(self, old_teams: List[ParsedBocaScoreboardTeam], new_teams: List[ParsedBocaScoreboardTeam]
                         ) -> str:
        teams: Dict[str, ParsedBocaScoreboardTeam] = {t.name: t for t in old_teams}
        updates = []
        for new_team in new_teams:
            if new_team.name not in teams:
                # TODO: Re-work to account for server restarts
                updates.append(f"El equipo <code>{new_team.name}</code> apareció en el scoreboard")
                continue

            old_team = teams[new_team.name]
            solved_diff_summary = self._get_solved_diff_summary(old_team, new_team)
            if solved_diff_summary:
                update = f"El equipo <code>{new_team.name}</code> resolvió {solved_diff_summary}, "
                if old_team.place == new_team.place:
                    update += f"quedándose en el mismo lugar {old_team.place}"
                else:
                    update += f"cambiando del lugar {old_team.place} al {new_team.place}"
                updates.append(update)

        return "\n".join(updates)

    async def _notify_rank_updates(self) -> None:
        for user in self._get_users_with_subscriptions():
            previous_teams = self._filter_teams(self._previous_scoreboard, user.team_query_subscription)
            teams = self._filter_teams(self._scoreboard, user.team_query_subscription)
            rank_update = self._get_rank_update(previous_teams, teams)
            if rank_update:
                await self._telegram.send_message(rank_update, user.telegram_chat_id)

    async def _notify_contest_has_ended(self, contest: Contest) -> None:
        for user in self._get_users_with_subscriptions():
            await self._telegram.send_message(f'El concurso <i>{contest.name}</i> terminó', user.telegram_chat_id)
