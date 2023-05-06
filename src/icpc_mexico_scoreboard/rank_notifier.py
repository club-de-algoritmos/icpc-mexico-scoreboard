import logging
import time
from typing import List, Dict, Set

from icpc_mexico_scoreboard.parser import parse_boca_scoreboard, NotAScoreboardError
from icpc_mexico_scoreboard.telegram_notifier import send_message
from icpc_mexico_scoreboard.types import ParsedBocaScoreboard, ParsedBocaScoreboardTeam


logger = logging.getLogger(__name__)


def escape(value):
    chars = ["_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"]
    escaped = str(value)
    for char in chars:
        escaped = escaped.replace(char, f"\\{char}")
    return escaped


def _notify_error(error: str) -> None:
    print("Got unexpected error: ", error)
    print()
    send_message(escape("Got unexpected error: " + error))


def _notify_info(info: str) -> None:
    print(info)
    print()
    send_message(info)


def _notify_current_rank(current_rank: str) -> None:
    print("Current rank:")
    print(current_rank)
    print()
    send_message(current_rank)


def _notify_rank_update(rank_update: str) -> None:
    print("Rank update:")
    print(rank_update)
    print()
    send_message(rank_update)


def _wait_until_contest_starts(scoreboard_url: str) -> ParsedBocaScoreboard:
    while True:
        try:
            return parse_boca_scoreboard(scoreboard_url)
        except NotAScoreboardError as e:
            print(e)
            _notify_info("El concurso no ha iniciado")
        except Exception as e:
            _notify_error(str(e))
        time.sleep(60)  # Wait a minute


def _filter_teams(scoreboard: ParsedBocaScoreboard, team_query: str) -> List[ParsedBocaScoreboardTeam]:
    def matches_team(team: ParsedBocaScoreboardTeam) -> bool:
        # return bool(re.search(team_query.lower(), team.name.lower()))
        # return team_query.lower() in team.name.lower()
        for subquery in team_query.lower().split('|'):
            if subquery in team.name.lower():
                return True
        return False

    return list(filter(matches_team, scoreboard.teams))


def _get_solved_names(team: ParsedBocaScoreboardTeam) -> Set[str]:
    return set(map(lambda p: p.name, filter(lambda p: p.is_solved, team.problems)))


def _solved_as_str(solved: Set[str]) -> str:
    return "\\(" + ", ".join(sorted(solved)) + "\\)"


def _get_solved_summary(team: ParsedBocaScoreboardTeam) -> str:
    if not team.total_solved:
        return "0 problemas"

    solved_names = _solved_as_str(_get_solved_names(team))
    if team.total_solved == 1:
        return f"1 problema {solved_names}"
    return f"{team.total_solved} problemas {solved_names}"


def _get_current_rank(teams: List[ParsedBocaScoreboardTeam]) -> str:
    def get_rank(team: ParsedBocaScoreboardTeam) -> str:
        solved_summary = _get_solved_summary(team)
        return f"\\#{team.place} _{escape(team.name)}_ resolvió {solved_summary} en {team.total_penalty} minutos"

    sorted_teams = sorted(teams, key=lambda t: t.place)
    return "\n".join(map(get_rank, sorted_teams))


def _get_solved_diff_summary(old_team: ParsedBocaScoreboardTeam, new_team: ParsedBocaScoreboardTeam) -> str:
    solved = new_team.total_solved - old_team.total_solved
    if not solved:
        return ""

    solved_names = _solved_as_str(_get_solved_names(new_team).difference(_get_solved_names(old_team)))
    if solved == 1:
        return f"1 problema {solved_names}"
    return f"{solved} problemas {solved_names}"


def _get_rank_update(old_teams: List[ParsedBocaScoreboardTeam], new_teams: List[ParsedBocaScoreboardTeam]) -> str:
    teams: Dict[str, ParsedBocaScoreboardTeam] = {t.name: t for t in old_teams}
    updates = []
    for new_team in new_teams:
        if new_team.name not in teams:
            updates.append(f"El equipo _{escape(new_team.name)}_ apareció en el scoreboard")
            continue

        old_team = teams[new_team.name]
        solved_diff_summary = _get_solved_diff_summary(old_team, new_team)
        if solved_diff_summary:
            update = f"El equipo _{escape(new_team.name)} resolvió {solved_diff_summary}, "
            if old_team.place == new_team.place:
                update += f"quedándose en el mismo lugar {old_team.place}"
            else:
                update += f"cambiando del lugar {old_team.place} al {new_team.place}"
            updates.append(update)

    return "\n".join(updates)


def notify_current_rank(scoreboard_url: str, team_query: str) -> None:
    scoreboard = parse_boca_scoreboard(scoreboard_url)
    watched_teams = _filter_teams(scoreboard, team_query)
    current_rank = _get_current_rank(watched_teams)
    _notify_current_rank(current_rank)


def notify_rank_updates(scoreboard_url: str, team_query: str) -> None:
    scoreboard = _wait_until_contest_starts(scoreboard_url)
    watched_teams = _filter_teams(scoreboard, team_query)
    current_rank = _get_current_rank(watched_teams)
    _notify_current_rank(current_rank)

    next_notify_rank = 5
    while True:
        time.sleep(60)  # Notify updates every minute

        new_scoreboard = parse_boca_scoreboard(scoreboard_url)
        new_watched_teams = _filter_teams(new_scoreboard, team_query)
        rank_update = _get_rank_update(watched_teams, new_watched_teams)
        if rank_update:
            _notify_rank_update(rank_update)
        scoreboard = new_scoreboard
        watched_teams = new_watched_teams

        next_notify_rank -= 1
        if next_notify_rank == 0:
            next_notify_rank = 5
            watched_teams = _filter_teams(scoreboard, team_query)
            current_rank = _get_current_rank(watched_teams)
            _notify_current_rank(current_rank)


def notify_rank_updates_until_finished(scoreboard_url: str, team_query: str) -> None:
    while True:
        try:
            notify_rank_updates(scoreboard_url, team_query)
        except NotAScoreboardError:
            _notify_info("El concurso terminó")
            return
        except Exception as e:
            logging.exception('Unexpected error')
            _notify_error(str(e))
