from typing import List


class ParsedBocaScoreboardProblem:
    name: str
    tries: int = 0
    solved_at: int = 0
    is_solved: bool = False

    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other):
        if not isinstance(other, ParsedBocaScoreboardProblem):
            return False
        return (
            self.name == other.name
            and self.tries == other.tries
            and self.solved_at == other.solved_at
            and self.is_solved == other.is_solved
        )

    def __str__(self):
        penalty_text = str(self.solved_at) if self.is_solved else "-"
        return f"{self.name} ({self.tries}/{penalty_text})"

    def __repr__(self):
        return self.__str__()


class ParsedBocaScoreboardTeam:
    name: str
    place: int
    user_site: str
    total_solved: int
    total_penalty: int
    problems: List[ParsedBocaScoreboardProblem]

    def __init__(self):
        self.problems = []


class ParsedBocaScoreboard:
    teams: List[ParsedBocaScoreboardTeam]

    def __init__(self):
        self.teams = []
