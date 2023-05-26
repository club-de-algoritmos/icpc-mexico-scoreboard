import asyncio
import html
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional, Iterable

from django.db.models import QuerySet

from icpc_mexico_scoreboard.db.models import ScoreboardUser, ScoreboardSubscription, Contest, ScoreboardStatus
from icpc_mexico_scoreboard.parser import parse_boca_scoreboard
from icpc_mexico_scoreboard.parser_types import ParsedBocaScoreboard, ParsedBocaScoreboardTeam, NotAScoreboardError
from icpc_mexico_scoreboard.telegram_notifier import TelegramNotifier, TelegramUser

logger = logging.getLogger(__name__)

_SCOREBOARD_RELEASE_TIMEOUT = timedelta(days=5)


def _format_code(code: str) -> str:
    return f"<code>{html.escape(code)}</code>"


async def _query_to_list(queryset: QuerySet) -> List:
    return [e async for e in queryset]


async def _get_or_create_user(telegram_chat_id: int) -> ScoreboardUser:
    user, _ = await ScoreboardUser.objects.aget_or_create(telegram_chat_id=telegram_chat_id)
    return user


async def _get_user_subscriptions(user: ScoreboardUser) -> List[str]:
    return sorted(
        await _query_to_list(
            ScoreboardSubscription.objects.filter(user=user).values_list("subscription", flat=True)))


async def _get_users_with_subscriptions() -> List[ScoreboardUser]:
    user_ids = await _query_to_list(
        ScoreboardSubscription.objects.filter().values_list("user_id", flat=True).distinct())
    return await _query_to_list(ScoreboardUser.objects.filter(pk__in=user_ids))


async def _get_current_contest() -> Optional[Contest]:
    return await Contest.objects.filter(starts_at__lte=datetime.utcnow()).order_by("starts_at").alast()


class ScoreboardNotifier:
    _telegram: Optional[TelegramNotifier] = None
    # TODO: Get from DB
    _previous_scoreboard: Optional[ParsedBocaScoreboard] = None
    _scoreboard: Optional[ParsedBocaScoreboard] = None

    async def start_running(self) -> None:
        logger.debug("Starting up")
        self._telegram = TelegramNotifier()
        await self._telegram.start_running(
            get_top_callback=self._get_top,
            get_scoreboard_callback=self._get_scoreboard,
            follow_callback=self._follow,
            show_following_callback=self._show_following,
            stop_following_callback=self._stop_following,
        )
        await self._start_parsing_scoreboards()

    async def _start_parsing_scoreboards(self) -> None:
        logger.debug("Starting to parse scoreboards")
        while True:
            try:
                await self._parse_current_scoreboard()
            except RuntimeError as e:
                logging.exception("Unexpected error")
                await self._notify_error(str(e))

            await asyncio.sleep(60)

    async def _parse_current_scoreboard(self) -> None:
        contest = await _get_current_contest()
        if not contest:
            logger.info("No contest is actively running")
            return

        if contest.scoreboard_status == ScoreboardStatus.ARCHIVED:
            # Nothing to do because it was archived
            return

        if contest.scoreboard_status == ScoreboardStatus.RELEASED:
            # Makes no sense to parse the scoreboard because it cannot change after its release
            # TODO: Return here when the scoreboard can be obtained from the DB
            pass

        # The contest is either running or finished, but it hasn't been released
        now = datetime.utcnow()

        # Expire the contest if it ended a long time ago as it was never released
        if contest.ends_at + _SCOREBOARD_RELEASE_TIMEOUT < now:
            if contest.scoreboard_status != ScoreboardStatus.RELEASED:
                contest.scoreboard_status = ScoreboardStatus.RELEASED
                await contest.asave()
                await self._telegram.send_developer_message(
                    f"El concurso <i>{contest.name}</i> terminó hace más de 5 días "
                    f"y su scoreboard no ha sido liberado, por lo que ha expirado y ya no será leído")
        elif contest.freezes_at > now:  # Not yet frozen
            if contest.scoreboard_status != ScoreboardStatus.VISIBLE:
                contest.scoreboard_status = ScoreboardStatus.VISIBLE
                await contest.asave()
                await self._notify_all_subscribed_users(f"El concurso <i>{contest.name}</i> ha iniciado")
        elif contest.ends_at > now:  # Not yet finished
            if contest.scoreboard_status != ScoreboardStatus.FROZEN:
                contest.scoreboard_status = ScoreboardStatus.FROZEN
                await contest.asave()
                await self._notify_all_subscribed_users(
                    f"El concurso <i>{contest.name}</i> se ha congelado, "
                    f"pero algunos envíos pueden estar pendientes de evaluarse")
        elif not ScoreboardStatus.is_finished(contest.scoreboard_status):
            contest.scoreboard_status = ScoreboardStatus.WAITING_TO_BE_RELEASED
            await contest.asave()
            await self._notify_all_subscribed_users(
                f"El concurso <i>{contest.name}</i> ha terminado y, "
                f"cuando los resultados finales se liberen, serás notificado del scoreboard final")

        logger.debug(f"Parsing the scoreboard of contest {contest.name}")
        try:
            scoreboard = parse_boca_scoreboard(contest.scoreboard_url)
        except NotAScoreboardError:
            logger.info(f"El concurso {contest.name} no ha iniciado")
            scoreboard = None

        if not scoreboard:
            self._previous_scoreboard = None
            self._scoreboard = None
            if ScoreboardStatus.is_finished(contest.scoreboard_status):
                # There is no scoreboard so it must have been archived
                contest.scoreboard_status = ScoreboardStatus.ARCHIVED
                await contest.asave()
            return

        # TODO: Store scoreboard in DB
        self._previous_scoreboard = self._scoreboard
        self._scoreboard = scoreboard
        if (contest.scoreboard_status == ScoreboardStatus.WAITING_TO_BE_RELEASED
                and self._previous_scoreboard != self._scoreboard):
            # A scoreboard change means it was released
            contest.scoreboard_status = ScoreboardStatus.RELEASED
            await contest.asave()

        await self._notify_rank_updates(contest)

    async def stop_running(self) -> None:
        await self._telegram.stop_running()

    async def _notify_if_no_scoreboard(self, telegram_user: TelegramUser) -> bool:
        contest = await _get_current_contest()
        if not contest:
            await self._telegram.send_message("No hay concurso actual", telegram_user.chat_id)
            return True

        if not self._scoreboard:
            await self._telegram.send_message(f"Todavía no tenemos el scoreboard del concurso <i>{contest.name}</i>, "
                                              f"reintenta de nuevo más tarde",
                                              telegram_user.chat_id)
            return True

        return False

    async def _get_top(self, telegram_user: TelegramUser, top_n: Optional[int]) -> None:
        if await self._notify_if_no_scoreboard(telegram_user):
            return

        n = 10 if top_n is None or top_n <= 0 else top_n
        top_teams = self._scoreboard.teams[:n]
        top_rank = self._get_current_rank(top_teams)
        await self._telegram.send_message(top_rank or "El scoreboard está vacío",
                                          telegram_user.chat_id)

    async def _get_scoreboard(self, telegram_user: TelegramUser, search_text: Optional[str]) -> None:
        if await self._notify_if_no_scoreboard(telegram_user):
            return

        if search_text:
            await self._notify_scoreboard(telegram_user, {search_text})
            return

        user = await _get_or_create_user(telegram_user.chat_id)
        subscriptions = await _get_user_subscriptions(user)
        if not subscriptions:
            await self._telegram.send_message("No sigues ningún equipo, ejecuta el commando "
                                              f"{_format_code('/seguir subcadena')}"
                                              "para seguir los equipos que quieras",
                                              telegram_user.chat_id)
            return

        await self._notify_scoreboard(telegram_user, subscriptions)

    async def _follow(self, telegram_user: TelegramUser, follow_text: str) -> None:
        user = await _get_or_create_user(telegram_user.chat_id)
        await ScoreboardSubscription.objects.aget_or_create(user=user, subscription=follow_text)

        if await self._notify_if_no_scoreboard(telegram_user):
            return

        # Notify of scoreboard, only for the new subscription
        await self._notify_scoreboard(telegram_user, {follow_text})

    async def _notify_scoreboard(self, telegram_user: TelegramUser, team_query_subscriptions: Iterable[str]) -> None:
        watched_teams = self._filter_teams(self._scoreboard, team_query_subscriptions)
        current_rank = self._get_current_rank(watched_teams)
        await self._telegram.send_message(current_rank or "Ningún equipo que sigues fué encontrado",
                                          telegram_user.chat_id)

    async def _show_following(self, telegram_user: TelegramUser) -> None:
        user = await _get_or_create_user(telegram_user.chat_id)
        subscriptions = await _get_user_subscriptions(user)
        if not subscriptions:
            await self._telegram.send_message("No sigues a ningún equipo", user.telegram_chat_id)
            return

        await self._telegram.show_following(subscriptions, user.telegram_chat_id)

    async def _stop_following(self, telegram_user: TelegramUser, unfollow_text: str) -> None:
        user = await _get_or_create_user(telegram_user.chat_id)
        await ScoreboardSubscription.objects.filter(user=user, subscription=unfollow_text).adelete()
        await self._telegram.send_message(f"Ya no sigues {_format_code(unfollow_text)}", telegram_user.chat_id)

    async def _notify_error(self, error: str) -> None:
        await self._telegram.send_developer_message(f"Got unexpected error: {_format_code(error)}")

    def _filter_teams(
            self,
            scoreboard: Optional[ParsedBocaScoreboard],
            queries: Iterable[str],
    ) -> List[ParsedBocaScoreboardTeam]:
        if not scoreboard:
            return []

        def matches_team(team: ParsedBocaScoreboardTeam) -> bool:
            for query in queries:
                if query.lower().strip() in team.name.lower():
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
            return f"<b>#{team.place}</b> {_format_code(team.name)} " \
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

    def _get_rank_update(
            self,
            old_teams: List[ParsedBocaScoreboardTeam],
            new_teams: List[ParsedBocaScoreboardTeam],
            contest: Contest,
    ) -> str:
        teams: Dict[str, ParsedBocaScoreboardTeam] = {t.name: t for t in old_teams}
        updates = []
        for new_team in new_teams:
            if new_team.name not in teams:
                if contest.scoreboard_status not in [
                        ScoreboardStatus.WAITING_TO_BE_RELEASED, ScoreboardStatus.RELEASED]:
                    updates.append(f"El equipo {_format_code(new_team.name)} apareció en el scoreboard")
                continue

            old_team = teams[new_team.name]
            solved_diff_summary = self._get_solved_diff_summary(old_team, new_team)
            if solved_diff_summary:
                update = f"El equipo {_format_code(new_team.name)} resolvió {solved_diff_summary}, "
                if old_team.place == new_team.place:
                    update += f"quedándose en el mismo lugar <b>#{old_team.place}</b>"
                else:
                    update += f"cambiando del lugar #{old_team.place} al <b>#{new_team.place}</b>"
                updates.append(update)

        return "\n".join(updates)

    async def _notify_rank_updates(self, contest: Contest) -> None:
        # TODO: Improve performance
        for user in await _get_users_with_subscriptions():
            subscriptions = await _get_user_subscriptions(user)
            previous_teams = self._filter_teams(self._previous_scoreboard, subscriptions)
            teams = self._filter_teams(self._scoreboard, subscriptions)
            rank_update = self._get_rank_update(previous_teams, teams, contest)
            if rank_update:
                await self._telegram.send_message(rank_update, user.telegram_chat_id)

    async def _notify_all_subscribed_users(self, message: str) -> None:
        for user in await _get_users_with_subscriptions():
            await self._telegram.send_message(message, user.telegram_chat_id)
