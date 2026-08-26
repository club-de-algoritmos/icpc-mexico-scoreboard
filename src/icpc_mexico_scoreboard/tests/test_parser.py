import unittest
from unittest.mock import MagicMock, patch

from selenium.common import TimeoutException

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


def _moj_cell(name: str, tries: int, solved_at) -> str:
    if tries == 0:
        return f'<td class="cell" title="{name}"><span class="pv"></span></td>'
    penalty_text = str(solved_at) if solved_at is not None else "-"
    cls = "cell ok" if solved_at is not None else "cell c-try prob-wait-cell"
    return (
        f'<td class="{cls}" title="{name}: {tries} attempts">'
        f'<span class="pv">{tries}/{penalty_text}</span></td>'
    )


def _moj_row(place: int, name: str, total_solved: int, total_penalty: int, *cells: str) -> str:
    return (
        f'<tr id="tr-team-{name.lower()}"><td class="cl-place">{place}</td><td></td>'
        f'<td class="team" title="{name.lower()}">{name}</td>'
        f"{''.join(cells)}"
        f'<td class="cell tot">{total_solved}</td>'
        f'<td class="cell pen"><span class="pv">{total_penalty}</span></td></tr>'
    )


def _moj_table(problem_letters: list, *rows: str) -> str:
    header_cells = "".join(f"<th>{letter}</th>" for letter in problem_letters)
    return f"""
    <table class="score m-icpc">
      <thead>
        <tr><th>#</th><th></th><th>Team</th>{header_cells}<th>Total</th><th>Pen.</th></tr>
      </thead>
      <tbody>{"".join(rows)}</tbody>
    </table>
    """


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


class ParseMojScoreboardTest(unittest.TestCase):
    _URL = "https://ensaio-times-2026.moj.naquadah.com.br/contest/score/?c=ensaio-times-2026"

    def _run(self, html: str):
        driver = MagicMock()
        driver.page_source = html
        with (
            patch("icpc_mexico_scoreboard.parser._get_webdriver", return_value=driver),
            patch("icpc_mexico_scoreboard.parser.WebDriverWait"),
        ):
            return parse_boca_scoreboard(self._URL)

    def test_parses_teams_ranks_and_problem_results(self) -> None:
        html = _moj_table(
            ["A", "B", "C"],
            _moj_row(
                1,
                "Aviators",
                2,
                190,
                _moj_cell("A", 1, 10),
                _moj_cell("B", 2, 180),
                _moj_cell("C", 0, None),
            ),
            _moj_row(
                2,
                "Falcons",
                1,
                60,
                _moj_cell("A", 3, None),
                _moj_cell("B", 0, None),
                _moj_cell("C", 1, 60),
            ),
        )

        scoreboard = self._run(html)

        self.assertEqual([team.name for team in scoreboard.teams], ["Aviators", "Falcons"])

        aviators = scoreboard.teams[0]
        self.assertEqual(aviators.place, 1)
        self.assertEqual(aviators.total_solved, 2)
        self.assertEqual(aviators.total_penalty, 190)
        self.assertEqual(
            aviators.problems,
            [
                _problem("A", tries=1, solved_at=10, is_solved=True),
                _problem("B", tries=2, solved_at=180, is_solved=True),
                _problem("C", tries=0, solved_at=0, is_solved=False),
            ],
        )

        falcons = scoreboard.teams[1]
        self.assertEqual(
            falcons.problems,
            [
                _problem("A", tries=3, solved_at=0, is_solved=False),
                _problem("B", tries=0, solved_at=0, is_solved=False),
                _problem("C", tries=1, solved_at=60, is_solved=True),
            ],
        )

    def test_raises_when_the_scoreboard_table_never_loads(self) -> None:
        driver = MagicMock()
        with (
            patch("icpc_mexico_scoreboard.parser._get_webdriver", return_value=driver),
            patch(
                "icpc_mexico_scoreboard.parser.WebDriverWait.until",
                side_effect=TimeoutException(),
            ),
        ):
            with self.assertRaises(NotAScoreboardError):
                parse_boca_scoreboard(self._URL)
