import os

import environ


env = environ.Env()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = (
    "icpc_mexico_scoreboard.db",
)

SECRET_KEY = env("SECRET_KEY")
