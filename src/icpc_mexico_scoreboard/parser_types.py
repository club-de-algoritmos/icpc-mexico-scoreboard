from dataclasses import dataclass
from typing import List


class NotAScoreboardError(Exception):
    pass


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

    @property
    def school_name(self) -> str:
        if self.name.startswith('['):
            end = self.name.index(']')
            return self.name[1:end]
        return ''


@dataclass(frozen=True)
class ParsedBocaScoreboard:
    teams: List[ParsedBocaScoreboardTeam]
