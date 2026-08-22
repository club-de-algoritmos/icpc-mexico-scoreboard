import unittest

from icpc_mexico_scoreboard.db.queries import get_repechaje_teams_that_have_advanced

_REPECHAJE_TEAMS_PATH = "src/icpc_mexico_scoreboard/db/repechaje_teams.txt"


class GetRepechajeTeamsThatHaveAdvancedTest(unittest.TestCase):
    def test_matches_the_non_blank_lines_of_the_teams_file(self) -> None:
        with open(_REPECHAJE_TEAMS_PATH, "r") as f:
            expected_names = [line.strip() for line in f.readlines() if line.strip()]

        teams = get_repechaje_teams_that_have_advanced()

        self.assertEqual([team.name for team in teams], expected_names)

    def test_names_have_no_surrounding_whitespace(self) -> None:
        teams = get_repechaje_teams_that_have_advanced()

        self.assertTrue(teams)
        for team in teams:
            self.assertEqual(team.name, team.name.strip())
            self.assertNotEqual(team.name, "")
