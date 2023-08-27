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
    def clean_name(self) -> str:
        if self.name.startswith('['):
            end = self.name.index(']')
            return self.name[end+1:].strip()
        return self.name

    @property
    def school_name(self) -> str:
        if self.name.startswith('['):
            end = self.name.index(']')
            return self.name[1:end].strip()
        return ''

    @property
    def is_guest(self) -> bool:
        guest_school_name_suffixes = ['omi', 'cbtis', 'cetis']
        school_name = self.school_name.lower()
        for suffix in guest_school_name_suffixes:
            if suffix in school_name:
                return True
        return False


@dataclass(frozen=True)
class ParsedBocaScoreboard:
    teams: List[ParsedBocaScoreboardTeam]
