import os

import environ


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load env vars here (rather than relying solely on manage.py/run_scoreboard.py doing it) so this
# settings module also works when imported directly, e.g. by pytest-django.
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))
env = environ.Env()

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "HOST": env("DATABASE_HOST"),
        "PORT": env("DATABASE_PORT"),
        "NAME": env("DATABASE_NAME"),
        "USER": env("DATABASE_USER"),
        "PASSWORD": env("DATABASE_PASSWORD"),
    }
}

CONN_MAX_AGE = 10*60  # 10 minutes

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = (
    "icpc_mexico_scoreboard.db",
)

SECRET_KEY = env("SECRET_KEY")
