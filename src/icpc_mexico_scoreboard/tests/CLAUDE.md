# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with tests in this directory.

## Running tests

```shell
python -m pytest src               # run the suite (reuses the test DB schema between runs)
python -m pytest src --create-db   # same, but rebuilds the test DB schema first (needed after a new migration)
```

Run from the repository root, same as `python src/manage.py ...` (`pytest.ini` sets `pythonpath = src` and
`DJANGO_SETTINGS_MODULE = settings`).

Tests run against a real local MySQL database (`test_icpc_mexico_scoreboard`), not SQLite or a mocked DB —
this is deliberate, to keep tests close to production instead of diverging on engine-specific behavior.
Django's test runner auto-creates/drops `test_icpc_mexico_scoreboard` on the same MySQL server configured in
`src/.env`. If a DB-backed test fails with a MySQL error 1044 ("access denied ... to database
test_icpc_mexico_scoreboard"), the `scoreboard` DB user needs a one-time grant (run once, as MySQL root, per
machine):

```sql
GRANT ALL PRIVILEGES ON `test_icpc_mexico_scoreboard`.* TO 'scoreboard'@'localhost';
FLUSH PRIVILEGES;
```

There is no CI yet — tests are run locally only.

## Test style

- One `TestCase` class per function or behavior under test, not bare `def test_...()` functions and not
  pytest fixtures. Use `unittest.TestCase` for pure-logic tests that don't touch the DB (e.g.
  `parser_types.py`, `string_utils.py`, `time_utils.py`), and Django's `django.test.TestCase` for anything
  that does (`db/models.py`) — it wraps each test in a transaction and rolls it back.
- Only put data in `setUp()` if most of the class's test methods need it. If only one test needs something,
  create it inline in that test method instead. Do not introduce `conftest.py` fixtures for this project —
  data should be visible either in `setUp()` or in the test itself, not injected from elsewhere.
- Build model instances with the `factory_boy` factories in `factories.py` (e.g. `ContestFactory()`) instead
  of calling `Model.objects.create(...)` directly. Explicitly pass any field the test asserts on; leave the
  rest to the factory's defaults. Add a factory there the first time a model is needed in a test — don't
  pre-build factories for models nothing tests yet.
- Name classes after what they test, e.g. `class NormalizeTest(unittest.TestCase)` for `normalize`,
  `class ContestStrTest(TestCase)` for `Contest.__str__`. See the existing files in this directory for the
  pattern.
- Test public functions only, never `_`-prefixed private helpers directly — let them get exercised
  indirectly through the public function that calls them.
- `scoreboard_notifier.py` and `telegram_notifier.py` are almost entirely `async def`. Keep test methods
  themselves synchronous, then call the async function under test via `asgiref.sync.async_to_sync(fn)(...)`.
  Don't make the test method itself `async def`: Django's async-safety check raises
  `SynchronousOnlyOperation` the moment a sync ORM call runs inside a coroutine.
- `USE_TZ` is not set (so it defaults to `False`): this codebase works with naive `datetime`s throughout,
  always representing UTC by convention (e.g. `_get_last_contest`/`_get_next_contest` compare against
  `datetime.utcnow()`, and `Contest.starts_at` etc. are stored naive). Build test datetimes the same way
  (`datetime.utcnow()`, not `datetime.now(timezone.utc)`) — an aware datetime gets silently converted by
  Django before saving, which can shift the value and make time-window assertions flaky.
- For pure logic that only reads a model's fields (e.g. `ScoreboardNotifier._get_rank_update` reading
  `contest.starts_at`), build the instance with `ContestFactory.build(...)` instead of the default
  `ContestFactory(...)` — `.build()` skips the DB save, so the test can stay a `unittest.TestCase`.
- `_admin` (and anything else that calls `django.db.close_old_connections()`) really closes the DB
  connection. Inside a `TestCase`, that breaks the test's wrapping transaction. Mock it:
  `@patch("icpc_mexico_scoreboard.scoreboard_notifier.db.close_old_connections")`.

`pytest-django` (configured in the root `pytest.ini`) auto-detects and runs both `unittest.TestCase` and
`django.test.TestCase` subclasses correctly, so no special markers or config are needed beyond what's already
there.
