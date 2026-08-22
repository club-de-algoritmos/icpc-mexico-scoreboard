import unittest
from unittest.mock import MagicMock, patch

from icpc_mexico_scoreboard.parser import parse_boca_scoreboard
from icpc_mexico_scoreboard.parser_types import NotAScoreboardError, ParsedBocaScoreboardProblem

_BOCA_SCOREBOARD_HTML = """
<table id="myscoretable">
<tr>
<td>Place</td><td>Site</td><td>Name</td><td>A</td><td>B</td><td>Total</td>
</tr>
<tr class="sitegroup1">
<td>2</td><td>site1</td><td>[UAS] Team B</td>
<td><font>0/-</font></td><td><font>1/80</font></td><td>1 (80)</td>
</tr>
<tr class="sitegroup1">
<td>1</td><td>site1</td><td>[ITSUR] Team A</td>
<td><font>2/50</font></td><td><font>0/-</font></td><td>1 (50)</td>
</tr>
<tr class="sitegroup1">
<td>1</td><td>site1</td><td>[ITSUR] Team A</td>
<td><font>2/50</font></td><td><font>0/-</font></td><td>1 (50)</td>
</tr>
</table>
"""

_NAQUADAH_SCOREBOARD_HTML = """
<a onclick="showSite(5)">Mexico</a>
<table id="myscoretable">
<tr>
<td>Place</td><td>Site</td><td>Name</td><td>A</td><td>Total</td>
</tr>
<tr class="sitegroup5">
<td>1</td><td>site5</td><td>[ITSUR] Team Mexico</td>
<td><font>1/10</font></td><td>1 (10)</td>
</tr>
<tr class="sitegroup9">
<td>1</td><td>site9</td><td>[Brasil] Team Other</td>
<td><font>1/10</font></td><td>1 (10)</td>
</tr>
</table>
"""

_NOT_A_SCOREBOARD_HTML = "<html><body>Contest has not started</body></html>"

_ANIMEITOR_SCOREBOARD_HTML = """
<div class="runstable">
  <div class="run">
    <div class="problema">A</div>
    <div class="problema">B</div>
  </div>
  <div class="run">
    <div class="run_prefix">
      <span class="nomeTime">[ITSUR] Team A</span>
      <span class="colocacao">1</span>
      <span class="cima">1</span>
      <span class="baixo">50</span>
    </div>
    <div class="cell"><span class="accept-text"><span>0</span><span>50</span></span></div>
    <div class="cell">X2</div>
  </div>
  <div class="run" style="display:none">
    <div class="run_prefix">
      <span class="nomeTime">Hidden Team</span>
      <span class="colocacao">2</span>
      <span class="cima">0</span>
      <span class="baixo">0</span>
    </div>
    <div class="cell">-</div>
    <div class="cell">-</div>
  </div>
</div>
"""


def _mock_response(html: str) -> MagicMock:
    response = MagicMock()
    response.content = html.encode("utf-8")
    return response


def _problem(name: str, tries: int, solved_at: int, is_solved: bool) -> ParsedBocaScoreboardProblem:
    return ParsedBocaScoreboardProblem(name=name, tries=tries, solved_at=solved_at, is_solved=is_solved)


class ParseBocaScoreboardTest(unittest.TestCase):
    @patch("icpc_mexico_scoreboard.parser.requests.get")
    def test_parses_teams_sorted_by_place_then_name(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response(_BOCA_SCOREBOARD_HTML)

        scoreboard = parse_boca_scoreboard("https://score.icpcmexico.org")

        self.assertEqual([team.name for team in scoreboard.teams], ["[ITSUR] Team A", "[UAS] Team B"])

    @patch("icpc_mexico_scoreboard.parser.requests.get")
    def test_parses_problem_results(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response(_BOCA_SCOREBOARD_HTML)

        scoreboard = parse_boca_scoreboard("https://score.icpcmexico.org")

        team_a = next(team for team in scoreboard.teams if team.name == "[ITSUR] Team A")
        self.assertEqual(team_a.place, 1)
        self.assertEqual(team_a.total_solved, 1)
        self.assertEqual(team_a.total_penalty, 50)
        self.assertEqual(
            team_a.problems,
            [
                _problem("A", tries=2, solved_at=50, is_solved=True),
                _problem("B", tries=0, solved_at=0, is_solved=False),
            ],
        )

    @patch("icpc_mexico_scoreboard.parser.requests.get")
    def test_duplicate_teams_are_only_parsed_once(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response(_BOCA_SCOREBOARD_HTML)

        scoreboard = parse_boca_scoreboard("https://score.icpcmexico.org")

        self.assertEqual(len(scoreboard.teams), 2)

    @patch("icpc_mexico_scoreboard.parser.requests.get")
    def test_no_scoreboard_table_raises(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response(_NOT_A_SCOREBOARD_HTML)

        with self.assertRaises(NotAScoreboardError):
            parse_boca_scoreboard("https://score.icpcmexico.org")

    @patch("icpc_mexico_scoreboard.parser.requests.get")
    def test_naquadah_url_only_includes_mexico_site(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response(_NAQUADAH_SCOREBOARD_HTML)

        scoreboard = parse_boca_scoreboard("https://naquadah.example.com/scoreboard")

        self.assertEqual([team.name for team in scoreboard.teams], ["[ITSUR] Team Mexico"])


class ParseAnimeitorScoreboardTest(unittest.TestCase):
    @patch("icpc_mexico_scoreboard.parser.time.sleep")
    @patch("icpc_mexico_scoreboard.parser._get_webdriver")
    def test_parses_visible_teams_only(self, mock_get_webdriver: MagicMock, mock_sleep: MagicMock) -> None:
        driver = MagicMock()
        driver.page_source = _ANIMEITOR_SCOREBOARD_HTML
        mock_get_webdriver.return_value = driver

        scoreboard = parse_boca_scoreboard("https://animeitor.example.com/scoreboard")

        self.assertEqual([team.name for team in scoreboard.teams], ["[ITSUR] Team A"])

    @patch("icpc_mexico_scoreboard.parser.time.sleep")
    @patch("icpc_mexico_scoreboard.parser._get_webdriver")
    def test_parses_solved_and_wrong_attempts(self, mock_get_webdriver: MagicMock, mock_sleep: MagicMock) -> None:
        driver = MagicMock()
        driver.page_source = _ANIMEITOR_SCOREBOARD_HTML
        mock_get_webdriver.return_value = driver

        scoreboard = parse_boca_scoreboard("https://animeitor.example.com/scoreboard")

        team = scoreboard.teams[0]
        self.assertEqual(team.place, 1)
        self.assertEqual(team.total_solved, 1)
        self.assertEqual(team.total_penalty, 50)
        self.assertEqual(
            team.problems,
            [
                _problem("A", tries=1, solved_at=50, is_solved=True),
                _problem("B", tries=2, solved_at=0, is_solved=False),
            ],
        )

    @patch("icpc_mexico_scoreboard.parser.time.sleep")
    @patch("icpc_mexico_scoreboard.parser._get_webdriver")
    def test_no_scoreboard_table_raises(self, mock_get_webdriver: MagicMock, mock_sleep: MagicMock) -> None:
        driver = MagicMock()
        driver.page_source = _NOT_A_SCOREBOARD_HTML
        mock_get_webdriver.return_value = driver

        with self.assertRaises(NotAScoreboardError):
            parse_boca_scoreboard("https://animeitor.example.com/scoreboard")
