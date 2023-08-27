from dataclasses import dataclass
from functools import cache
from typing import List


@dataclass(frozen=True)
class RepechajeTeam:
    name: str


@cache
def get_repechaje_teams_that_have_advanced() -> List[RepechajeTeam]:
    teams: List[RepechajeTeam] = []
    with open("src/icpc_mexico_scoreboard/db/repechaje_teams.txt", "r") as f:
        for line in f.readlines():
            name = line.strip()
            if name:
                teams.append(RepechajeTeam(name))
    return teams
