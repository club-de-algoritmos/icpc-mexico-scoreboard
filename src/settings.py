import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "icpc_mexico_scoreboard",
        "USER": "scoreboard",
        "PASSWORD": "let-me-in",
        "HOST": "localhost",
        "PORT": "5432",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = (
    "icpc_mexico_scoreboard.db",
)

SECRET_KEY = "c4c4&6aw+(5&cg^_!05r(&7_#dghg_pdgopq(yk)xa^bog7j)^*j"
