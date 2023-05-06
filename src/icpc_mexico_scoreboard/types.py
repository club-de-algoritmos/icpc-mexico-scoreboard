from dataclasses import dataclass
from typing import List


@dataclass
class ParsedBocaScoreboardProblem:
    name: str
    tries: int
    solved_at: int
    is_solved: bool


@dataclass
class ParsedBocaScoreboardTeam:
    name: str
    place: int
    user_site: str
    total_solved: int
    total_penalty: int
    problems: List[ParsedBocaScoreboardProblem]


@dataclass
class ParsedBocaScoreboard:
    teams: List[ParsedBocaScoreboardTeam]

    def __init__(self):
        self.teams = []
