import asyncio
import html
import logging
import math
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional, Iterable

from django.db.models import QuerySet

from icpc_mexico_scoreboard.db.models import ScoreboardUser, ScoreboardSubscription, Contest, ScoreboardStatus
from icpc_mexico_scoreboard.db.queries import get_repechaje_teams_that_have_advanced
from icpc_mexico_scoreboard.parser import parse_boca_scoreboard
from icpc_mexico_scoreboard.parser_types import ParsedBocaScoreboard, ParsedBocaScoreboardTeam, NotAScoreboardError
from icpc_mexico_scoreboard.telegram_notifier import TelegramNotifier, TelegramUser

logger = logging.getLogger(__name__)

_SCOREBOARD_RELEASE_TIMEOUT = timedelta(days=5)

_SCOREBOARD_PRE_START_TIME = timedelta(hours=2)

_MAX_NOTIFICATION_TEAM_COUNT = 30


def _format_code(code: str) -> str:
    return f"<code>{html.escape(code)}</code>"


def _concat_paragraphs(a: Optional[str], b: Optional[str]) -> str:
    if a and b:
        return f'{a}\n\n{b}'
    return a or b or ''


def _get_time_delta_as_human(before: datetime, after: datetime) -> str:
    if before >= after:
        return "0 minutos"

    seconds_from_now = (after - before).total_seconds()
    minutes = math.ceil(seconds_from_now / 60)
    if minutes < 60:
        if minutes == 1:
            return "1 minuto"
        return f"{minutes} minutos"

    hours = round(minutes / 60)
    if hours < 24:
        if hours == 1:
            return "1 hora"
        return f"{hours} horas"

    days = round(hours / 24)
    if days < 30:
        if days == 1:
            return "1 día"
        return f"{days} días"

    months = round(days / 30)
    if months < 12:
        if months == 1:
            return "1 mes"
        return f"{months} meses"

    years = round(months / 12)
    if years == 1:
        return "1 año"
    return f"{years} años"


async def _query_to_list(queryset: QuerySet) -> List:
    return [e async for e in queryset]


async def _get_or_create_user(telegram_chat_id: int) -> ScoreboardUser:
    user, _ = await ScoreboardUser.objects.aget_or_create(telegram_chat_id=telegram_chat_id)
    return user


async def _get_user(telegram_chat_id: int) -> Optional[ScoreboardUser]:
    return await ScoreboardUser.objects.filter(telegram_chat_id=telegram_chat_id).afirst()


async def _delete_user(user: ScoreboardUser) -> None:
    deleted_subscriptions, _ = await ScoreboardSubscription.objects.filter(user=user).adelete()
    logger.debug(f"Deleted {deleted_subscriptions} subscriptions of user {user.pk}")
    await user.adelete()
    logger.debug(f"Deleted user with chat ID {user.telegram_chat_id}")


async def _get_user_subscriptions(user: ScoreboardUser) -> List[str]:
    return sorted(
        await _query_to_list(
            ScoreboardSubscription.objects.filter(user=user).values_list("subscription", flat=True)))


async def _get_users_with_subscriptions() -> List[ScoreboardUser]:
    user_ids = await _query_to_list(
        ScoreboardSubscription.objects.filter().values_list("user_id", flat=True).distinct())
    return await _query_to_list(ScoreboardUser.objects.filter(pk__in=user_ids))


async def _get_last_contest() -> Optional[Contest]:
    return await Contest.objects.filter(starts_at__lte=datetime.utcnow()).order_by("starts_at").alast()


async def _get_next_contest() -> Optional[Contest]:
    return await Contest.objects.filter(starts_at__gt=datetime.utcnow()).order_by("starts_at").afirst()


async def _get_current_contest() -> Optional[Contest]:
    last_contest = await _get_last_contest()
    next_contest = await _get_next_contest()
    if last_contest:
        if not ScoreboardStatus.is_finished(last_contest):
            return last_contest
        if next_contest and next_contest.starts_at < datetime.utcnow() + _SCOREBOARD_PRE_START_TIME:
            # Last contest has finished (whatever state) and the next one is about to start, so use that instead
            return next_contest
        if last_contest.scoreboard_status == ScoreboardStatus.ARCHIVED:
            # Makes no sense to return an archived context, so return whatever is next, even is there is none
            return next_contest
        # The last contest is finished, but we may still need to release it, or users may want to query it
        return last_contest

    # Just return what's next as there is nothing behind us
    return next_contest


class ScoreboardNotifier:
    _telegram: Optional[TelegramNotifier] = None
    # TODO: Get from DB
    _previous_scoreboard: Optional[ParsedBocaScoreboard] = None
    _scoreboard: Optional[ParsedBocaScoreboard] = None

    async def start_running(self) -> None:
        logger.debug("Starting up")
        self._telegram = TelegramNotifier()
        await self._telegram.start_running(
            _get_status_callback=self._get_status,
            get_top_callback=self._get_top,
            get_scoreboard_callback=self._get_scoreboard,
            follow_callback=self._follow,
            show_following_callback=self._show_following,
            stop_following_callback=self._stop_following,
            stop_all_callback=self._stop_all,
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
            logger.info("No contest is actively running or soon to run")
            return

        if contest.scoreboard_status == ScoreboardStatus.RELEASED:
            # Makes no sense to parse the scoreboard because it cannot change after its release
            # TODO: Return here when the scoreboard can be obtained from the DB
            pass

        now = datetime.utcnow()
        if contest.starts_at > now:
            # The contest has not started, do nothing yet
            pass
        elif contest.freezes_at > now:
            # Not yet frozen
            if contest.scoreboard_status != ScoreboardStatus.VISIBLE:
                contest.scoreboard_status = ScoreboardStatus.VISIBLE
                await contest.asave()
                await self._notify_all_subscribed_users(f"El concurso <i>{contest.name}</i> ha iniciado")
        elif contest.ends_at > now:
            # Not yet finished
            if contest.scoreboard_status != ScoreboardStatus.FROZEN:
                contest.scoreboard_status = ScoreboardStatus.FROZEN
                await contest.asave()
                await self._notify_all_subscribed_users(
                    f"El concurso <i>{contest.name}</i> se ha congelado, "
                    f"pero algunos envíos pueden estar pendientes de evaluarse")
        elif contest.ends_at + _SCOREBOARD_RELEASE_TIMEOUT < now:
            # Expire the contest if it ended a long time ago as it was never released
            if contest.scoreboard_status != ScoreboardStatus.RELEASED:
                contest.scoreboard_status = ScoreboardStatus.RELEASED
                await contest.asave()
                await self._telegram.send_developer_message(
                    f"El concurso <i>{contest.name}</i> terminó hace más de 5 días "
                    f"y su scoreboard no ha sido liberado, por lo que ha expirado y ya no será leído")
        elif not ScoreboardStatus.is_finished(contest.scoreboard_status):
            # The contest finished, but it hasn't expired, so wait for it to be released
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
                and self._previous_scoreboard
                and self._previous_scoreboard != self._scoreboard):
            # A scoreboard change means it was released
            contest.scoreboard_status = ScoreboardStatus.RELEASED
            await contest.asave()
            await self._notify_all_subscribed_users(
                f"Los resultados finales del concurso <i>{contest.name}</i> han sido liberados")
            await self._notify_scoreboard_to_all_users()
            return

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

    async def _get_status(self, telegram_user: TelegramUser) -> None:
        agenda = await self._compute_status()
        await self._telegram.send_message(agenda, chat_id=telegram_user.chat_id)

    async def _compute_status(self) -> str:
        last_contest = await _get_last_contest()
        now = datetime.utcnow()
        next_contest = await _get_next_contest()
        if (next_contest and (
                next_contest.starts_at < datetime.utcnow() + _SCOREBOARD_PRE_START_TIME
                or (last_contest and last_contest.scoreboard_status == ScoreboardStatus.ARCHIVED)
        )):
            time_to_start = _get_time_delta_as_human(now, next_contest.starts_at)
            return (f"El concurso <i>{next_contest.name}</i> iniciará en {time_to_start}.\n"
                    f"Podrás ver su scoreboard completo <a href='{next_contest.scoreboard_url}'>aquí</a>, "
                    f"o usando este bot (mira <a href='/ayuda'>/ayuda</a> para saber cómo).")

        last_contest_desc = None
        next_contest_desc = None
        if last_contest:
            time_to_freeze = _get_time_delta_as_human(now, last_contest.freezes_at)
            time_to_end = _get_time_delta_as_human(now, last_contest.ends_at)
            time_after_end = _get_time_delta_as_human(last_contest.ends_at, now)

            last_contest_desc = f"El concurso <i>{last_contest.name}</i> "
            if last_contest.scoreboard_status == ScoreboardStatus.VISIBLE:
                last_contest_desc += (f"está corriendo, su scoreboard se congelará en {time_to_freeze} y "
                                      f"terminará en {time_to_end}")
            elif last_contest.scoreboard_status == ScoreboardStatus.FROZEN:
                last_contest_desc += f"está congelado y terminará en {time_to_end}"
            elif last_contest.scoreboard_status == ScoreboardStatus.WAITING_TO_BE_RELEASED:
                last_contest_desc += f"terminó hace {time_after_end} pero parece que sus resultados no son finales"
            elif last_contest.scoreboard_status in [ScoreboardStatus.RELEASED, ScoreboardStatus.ARCHIVED]:
                last_contest_desc += f"terminó hace {time_after_end} y sus resultados son finales"
                if next_contest:
                    time_to_start = _get_time_delta_as_human(now, next_contest.starts_at)
                    starts_at_date = next_contest.starts_at.strftime("%Y-%m-%d")
                    next_contest_desc = (f"El siguiente concurso <i>{next_contest.name}</i> "
                                         f"iniciará en {time_to_start} ({starts_at_date}).")
            else:
                last_contest_desc = None
                logger.error(f"Contest {last_contest.name} has an unexpected status {last_contest.scoreboard_status}")

        if not last_contest_desc:
            return "¡No hay concursos agendados!"

        last_contest_desc = (
            f"{last_contest_desc}.\n"
            f"Puedes ver su scoreboard completo <a href='{last_contest.scoreboard_url}'>aquí</a>, "
            f"o usando este bot (mira <a href='/ayuda'>/ayuda</a> para saber cómo)."
        )

        return _concat_paragraphs(last_contest_desc, next_contest_desc)

    async def _get_top(self, telegram_user: TelegramUser, top_n: Optional[int]) -> None:
        if await self._notify_if_no_scoreboard(telegram_user):
            return

        if top_n is None or top_n <= 0:
            top_n = 10
        top_n = min(top_n, _MAX_NOTIFICATION_TEAM_COUNT)

        top_teams = self._scoreboard.teams[:top_n]
        top_rank = self._get_current_rank(top_teams)
        advancing_rank = await self._get_advancing_rank()
        message = _concat_paragraphs(top_rank, advancing_rank)

        await self._telegram.send_message(message or "El scoreboard está vacío",
                                          telegram_user.chat_id)

    async def _get_scoreboard(self, telegram_user: TelegramUser, search_text: Optional[str]) -> None:
        if await self._notify_if_no_scoreboard(telegram_user):
            return

        if search_text:
            await self._notify_scoreboard(telegram_user.chat_id, {search_text})
            return

        user = await _get_or_create_user(telegram_user.chat_id)
        subscriptions = await _get_user_subscriptions(user)
        if not subscriptions:
            await self._telegram.send_message("No sigues ningún equipo, ejecuta el commando "
                                              f"{_format_code('/seguir subcadena')}"
                                              "para seguir los equipos que quieras",
                                              telegram_user.chat_id)
            return

        await self._notify_scoreboard(telegram_user.chat_id, subscriptions)

    async def _follow(self, telegram_user: TelegramUser, follow_text: str) -> None:
        user = await _get_or_create_user(telegram_user.chat_id)
        await ScoreboardSubscription.objects.aget_or_create(user=user, subscription=follow_text)

        if await self._notify_if_no_scoreboard(telegram_user):
            return

        # Notify of scoreboard, only for the new subscription
        await self._notify_scoreboard(telegram_user.chat_id, {follow_text})

    async def _notify_scoreboard_to_all_users(self) -> None:
        # TODO: Improve performance
        for user in await _get_users_with_subscriptions():
            subscriptions = await _get_user_subscriptions(user)
            await self._notify_scoreboard(user.telegram_chat_id, subscriptions)

    async def _notify_scoreboard(self, telegram_user_chat_id: int, team_query_subscriptions: Iterable[str]) -> None:
        watched_teams = self._filter_teams(self._scoreboard, team_query_subscriptions)
        current_rank = self._get_current_rank(watched_teams) or "Ningún equipo que sigues fué encontrado"
        advancing_rank = await self._get_advancing_rank()
        message = _concat_paragraphs(current_rank, advancing_rank)
        await self._telegram.send_message(message, telegram_user_chat_id)

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

    def _get_team_summary(self, team: ParsedBocaScoreboardTeam) -> str:
        solved_summary = self._get_solved_summary(team)
        return f"<b>#{team.place}</b> {_format_code(team.name)} " \
               f"resolvió {solved_summary} en {team.total_penalty} minutos"

    def _get_current_rank(self, teams: List[ParsedBocaScoreboardTeam]) -> str:
        sorted_teams = sorted(teams, key=lambda t: (t.place, t.name.lower()))

        warning = ""
        if len(sorted_teams) > _MAX_NOTIFICATION_TEAM_COUNT:
            warning = (f"Solo se muestran los primeros {_MAX_NOTIFICATION_TEAM_COUNT}"
                       f" equipos de los {len(sorted_teams)} encontrados:\n\n")
            sorted_teams = sorted_teams[:_MAX_NOTIFICATION_TEAM_COUNT]

        team_rank = "\n".join(map(self._get_team_summary, sorted_teams))
        return f"{warning}{team_rank}"

    async def _get_advancing_rank(self) -> str:
        contest = await _get_current_contest()
        max_to_advance = contest.max_teams_to_advance
        if not max_to_advance:
            return ''

        max_by_school = contest.max_teams_per_school_to_advance or 1
        if 'repechaje' in contest.name.lower():
            teams_to_ignore = {team.name.lower() for team in get_repechaje_teams_that_have_advanced()}
        else:
            teams_to_ignore = []
        teams = []
        school_team_count = defaultdict(int)
        for team in self._scoreboard.teams:
            if team.clean_name.lower() in teams_to_ignore or team.is_guest:
                continue

            school_team_count[team.school_name] += 1
            if school_team_count[team.school_name] <= max_by_school:
                teams.append(team)
                if len(teams) == max_to_advance:
                    break

        team_summaries = "\n".join(map(self._get_team_summary, teams))
        return f'Los siguientes {len(teams)} equipos se espera que avancen a la siguiente etapa:\n{team_summaries}'

    def _get_solved_diff_summary(self, old_team: ParsedBocaScoreboardTeam, new_team: ParsedBocaScoreboardTeam) -> str:
        solved_problems = self._get_solved_names(new_team).difference(self._get_solved_names(old_team))
        solved_names = self._solved_as_str(solved_problems)
        if not solved_problems:
            return ''

        if len(solved_problems) == 1:
            (problem,) = solved_problems
            desc = f"el problema {problem}"
        else:
            desc = f"{len(solved_problems)} problemas {solved_names}"
        return f"{desc}, llegando a un total de <b>{new_team.total_solved}</b> problemas resueltos"

    def _get_rank_update(
            self,
            old_teams: List[ParsedBocaScoreboardTeam],
            new_teams: List[ParsedBocaScoreboardTeam],
            contest: Contest,
    ) -> str:
        teams: Dict[str, ParsedBocaScoreboardTeam] = {t.name: t for t in old_teams}
        updates = []
        now = datetime.utcnow()
        for new_team in new_teams:
            if new_team.name not in teams:
                if old_teams or contest.starts_at >= now - timedelta(minutes=15):
                    # Only notify of appearance when there were previous parsings (old_teams) or the contest just begun
                    updates.append(f"El equipo {_format_code(new_team.name)} apareció en el scoreboard")
                continue

            old_team = teams[new_team.name]
            solved_diff_summary = self._get_solved_diff_summary(old_team, new_team)
            if solved_diff_summary:
                update = f"El equipo {_format_code(new_team.name)} resolvió {solved_diff_summary}, y "
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

    async def _stop_all(self, telegram_user: TelegramUser) -> None:
        logger.debug(f'Stopping all notifications to user with chat ID {telegram_user.chat_id}')
        user = await _get_user(telegram_user.chat_id)
        if user:
            await _delete_user(user)
