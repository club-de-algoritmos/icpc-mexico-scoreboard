# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Retired -- superseded by wkoach

This repo's functionality (scoreboard scraping/parsing and the Telegram subscriber bot) has been merged
into the sibling `wkoach` repo (`wkoach/services/scoreboard/` for parsing/persistence,
`wkoach/services/telegram/` for the bot) and is no longer developed here. wkoach's version is authoritative
and ahead of this one (bug fixes, an extra scoreboard-source parser, persisted history this repo never had,
per-contest-scoped subscriptions instead of a single implicit "current contest"). Treat this repo as
historical/archival -- a future change to this functionality belongs in wkoach, not here, and shouldn't be
expected to affect production once wkoach's Telegram bot deploy replaces this one (see wkoach's CLAUDE.md,
"ICPC Mexico rich scoreboard" section, and its git history for the merge).

## What this is

A Telegram bot that scrapes BOCA-based ICPC Mexico contest scoreboards and notifies subscribed users of rank/score changes. It is not a web app: Django is used only for its ORM/settings machinery (MySQL) against a single `db` app; there are no views, templates, or URLs.

## Commands

All commands are run from the repository root (not `src/`); `manage.py` adds `src/` to `sys.path` itself.

- Install dependencies: `pip install -r requirements.txt` (Python version pinned in `.tool-versions`, managed via `asdf`)
- One-time env setup: `cp src/dev.env src/.env` and customize; create the MySQL database as described in `README.md`
- Apply migrations: `python src/manage.py migrate`
- Make a new migration after changing `src/icpc_mexico_scoreboard/db/models.py`: `python src/manage.py makemigrations`
- Run the bot (also installs deps and applies migrations first): `bin/run.sh` — kills any already-running `run_scoreboard` process, then runs `python src/run_scoreboard.py` in the background, logging to `scoreboard.log`
- Run the bot directly in the foreground: `python src/run_scoreboard.py`
- Django/IPython shell with project models pre-imported: `bin/django_shell.sh` (imports come from `bin/django_shell_imports.py`)
- Run tests: `python -m pytest src` — see `src/icpc_mexico_scoreboard/tests/CLAUDE.md` for the local MySQL test DB setup and test-style conventions

There is no configured linter in this repo.

## Architecture

`src/run_scoreboard.py` is the entry point: it loads env vars, boots Django (`DJANGO_SETTINGS_MODULE=settings`), optionally wires up Google Cloud Logging, then runs `icpc_mexico_scoreboard.app.start()`, which constructs and starts a `ScoreboardNotifier`.

Everything revolves around `ScoreboardNotifier` (`scoreboard_notifier.py`):
- On startup it creates a `TelegramNotifier` and registers itself as the callback target for every bot command (`/estado`, `/top`, `/scoreboard`, `/seguir`, `/seguirtop`, `/dejar`, `/dejartop`, `/alto`, `/admin`, ...).
- It then runs an infinite loop (`_start_parsing_scoreboards`), polling every 60 seconds to find the "current" contest (`_get_current_contest`, based on `Contest.starts_at`/`freezes_at`/`ends_at`) and parse its scoreboard.
- Contest lifecycle is tracked via `Contest.scoreboard_status` (`ScoreboardStatus` in `db/models.py`): `invisible -> visible -> frozen -> waiting_to_be_released -> released -> archived`. Status transitions trigger broadcast notifications to all subscribed users.
- Scoreboard parsing itself (`parser.py`) runs in a `ProcessPoolExecutor` since it can block on network/Selenium calls. It fetches the scoreboard page (plain `requests` for most sources; Selenium/headless Chrome for sources needing JS, like `redprogramacioncompetitiva` (RPC) or `animeitor`) and parses the HTML table into `ParsedBocaScoreboard`/`ParsedBocaScoreboardTeam`/`ParsedBocaScoreboardProblem` (`parser_types.py`). Two distinct HTML shapes are handled: the standard BOCA table (`_parse_boca_scoreboard`) and the Brazilian "animeitor" widget (`_parse_animeitor_scoreboard`).
- After each parse, the new scoreboard is diffed against the previous in-memory one to compute per-user rank/solve updates (`_notify_rank_updates`) and top-N changes, and messages are pushed via Telegram. Scoreboards are kept only in memory (`_previous_scoreboard`/`_scoreboard`), not persisted to the DB (see the `TODO: Store scoreboard in DB` note).
- `ParsedBocaScoreboardTeam.name` encodes the school in brackets, e.g. `[ITSUR] Team Name`; `clean_name`/`school_name`/`is_guest` parse that convention and are used to compute which teams are eligible to "advance" (`_get_advancing_rank`), including special-casing repechaje contests against `db/repechaje_teams.txt`.

`telegram_notifier.py` (`TelegramNotifier`) wraps `python-telegram-bot`: it owns the `Application`, registers command handlers, and exposes a set of async callbacks (injected by `ScoreboardNotifier.start_running`) rather than embedding any business logic itself. User-facing text is Spanish HTML (`ParseMode.HTML`).

`db/models.py` defines the only persisted state: `Contest`, `ScoreboardUser` (keyed by Telegram chat ID), and `ScoreboardSubscription` (a user following either a team-name substring or a "top N"). `db/queries.py` and `db/util.py` hold small standalone DB helpers. `admin/contests.py` has helpers for creating/shifting contests, meant to be used from the Django shell (`bin/django_shell.sh`) rather than imported into the app.

The in-bot `/admin` command (`ScoreboardNotifier._admin`, restricted to `TELEGRAM_DEVELOPER_CHAT_ID`) is the primary way contests get created/edited at runtime (`add`, `name`, `scoreboard`, `time`, `status`, `max-teams`), as an alternative to the Django shell helpers in `admin/contests.py`.
