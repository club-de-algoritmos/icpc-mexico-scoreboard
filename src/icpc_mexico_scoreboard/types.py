from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional


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


@dataclass(frozen=True)
class Contest:
    name: str
    scoreboard_url: str
    starts_at: datetime
    freezes_at: datetime
    ends_at: datetime


@dataclass(frozen=True)
class ScoreboardUser:
    telegram_chat_id: int
    team_query_subscription: Optional[str]
