from dataclasses import dataclass
from datetime import datetime
from typing import List, Set


@dataclass(frozen=True)
class ParsedBocaScoreboardProblem:
    name: str
    tries: int
    solved_at: int
    is_solved: bool


@dataclass(frozen=True)
class ParsedBocaScoreboardTeam:
    name: str
    place: int
    user_site: str
    total_solved: int
    total_penalty: int
    problems: List[ParsedBocaScoreboardProblem]


@dataclass(frozen=True)
class ParsedBocaScoreboard:
    teams: List[ParsedBocaScoreboardTeam]
