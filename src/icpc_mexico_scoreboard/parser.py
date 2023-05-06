import time

import requests
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

from icpc_mexico_scoreboard.types import ParsedBocaScoreboard, ParsedBocaScoreboardTeam, ParsedBocaScoreboardProblem


class NotAScoreboardError(Exception):
    pass


def _setup_webdriver() -> webdriver.Chrome:
    return webdriver.Chrome(ChromeDriverManager().install())


def parse_boca_scoreboard(scoreboard_url: str) -> ParsedBocaScoreboard:
    """Parses the scoreboard of a BOCA contest."""
    if 'animeitor' in scoreboard_url:
        return _parse_animeitor_scoreboard(scoreboard_url)
    return _parse_boca_scoreboard(scoreboard_url)


def _parse_boca_scoreboard(scoreboard_url: str) -> ParsedBocaScoreboard:
    if "icpcmexico.org" in scoreboard_url:
        response = requests.get(scoreboard_url)
        scoreboard_html = response.content
    else:
        driver = _setup_webdriver()
        driver.get(scoreboard_url)
        # TODO: Wait properly
        time.sleep(5)
        # Multi-sites like Brazil use an iframe, switch to it if found
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if iframes:
            driver.switch_to.frame(iframes[0])
        scoreboard_html = driver.page_source
        driver.quit()

    html = BeautifulSoup(scoreboard_html, "html.parser")
    table = html.find(id="myscoretable")
    if not table:
        raise NotAScoreboardError("Scoreboard table not found")

    table_rows = table.find_all("tr")
    if not table_rows:
        raise NotAScoreboardError("Scoreboard header not found")
    table_header = table_rows[0]

    problem_names = [cell.text.strip() for cell in table_header.find_all("td")[3:-1]]
    teams_elements = table_rows[1:]
    scoreboard = ParsedBocaScoreboard()
    for teams_element in teams_elements:
        cell_elements = teams_element.find_all("td")

        name = cell_elements[2].text.strip()
        # Multi-sites have duplicate teams, only parse the first one
        if scoreboard.teams and scoreboard.teams[-1].name == name:
            continue

        place = int(cell_elements[0].text.strip())
        user_site = cell_elements[1].text.strip()
        total_text_parts = cell_elements[-1].text.strip().split()
        total_solved = int(total_text_parts[0])
        total_penalty = int(total_text_parts[1][1:-1])
        problems = []
        for idx, problem_element in enumerate(cell_elements[3:-1]):
            tries = 0
            solved_at = 0
            is_solved = False
            result_element = problem_element.find("font")
            if result_element:
                result_text_parts = result_element.text.strip().split("/")
                tries = int(result_text_parts[0])
                penalty_text = result_text_parts[1]
                if penalty_text != "-":
                    solved_at = int(penalty_text)
                    is_solved = True

            problem_result = ParsedBocaScoreboardProblem(
                name=problem_names[idx], tries=tries, solved_at=solved_at, is_solved=is_solved)
            problems.append(problem_result)

        team = ParsedBocaScoreboardTeam(
            name=name, place=place, user_site=user_site, total_solved=total_solved, total_penalty=total_penalty,
            problems=problems)
        scoreboard.teams.append(team)

    return scoreboard


def _parse_animeitor_scoreboard(scoreboard_url: str) -> ParsedBocaScoreboard:
    driver = _setup_webdriver()
    driver.get(scoreboard_url)
    # TODO: Wait properly
    time.sleep(15)
    html = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    tables = html.find_all(class_="runstable")
    if not tables:
        raise NotAScoreboardError("Scoreboard table not found")

    table = tables[-1]
    table_rows = table.find_all(class_="run")
    if not table_rows:
        raise NotAScoreboardError("Scoreboard header not found")
    table_header = table_rows[0]

    problem_names = [cell.text.strip() for cell in table_header.find_all(class_="problema")]
    teams_elements = table_rows[1:]
    scoreboard = ParsedBocaScoreboard()
    for teams_element in teams_elements:
        if 'display:none' in teams_element.get('style', ''):
            continue

        team_prefix = teams_element.find(class_="run_prefix")
        name = team_prefix.find(class_="nomeTime").text.strip()
        # Multi-sites have duplicate teams, only parse the first one
        if scoreboard.teams and scoreboard.teams[-1].name == name:
            continue

        place = int(team_prefix.find_all(class_="colocacao")[1].text.strip())
        total_solved = int(team_prefix.find(class_="cima").text.strip())
        total_penalty = int(team_prefix.find(class_="baixo").text.strip())

        problem_elements = teams_element.find_all(class_="cell", recursive=False)
        problems = []
        for idx, problem_element in enumerate(problem_elements):
            tries = 0
            solved_at = 0
            is_solved = False
            result_text = problem_element.text.strip()
            if result_text != "-":
                if result_text.startswith("X"):
                    tries = int(result_text[2:-1])
                else:
                    accepted_element = problem_element.find(class_="accept-text")
                    if not accepted_element:
                        # TODO: Get tries
                        continue
                    tries_text = accepted_element.contents[0].text.strip()
                    tries = 1 + int((tries_text[1:] or "0"))
                    solved_at = int(accepted_element.contents[2].text.strip())
                    is_solved = True

            problem_result = ParsedBocaScoreboardProblem(
                name=problem_names[idx], tries=tries, solved_at=solved_at, is_solved=is_solved)
            problems.append(problem_result)

        team = ParsedBocaScoreboardTeam(
            name=name, place=place, user_site='', total_solved=total_solved, total_penalty=total_penalty,
            problems=problems)
        scoreboard.teams.append(team)

    return scoreboard
