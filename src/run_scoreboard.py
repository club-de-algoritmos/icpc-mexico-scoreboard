#!/usr/bin/env python

import asyncio
import os

import environ
from django.core.wsgi import get_wsgi_application
import google.cloud.logging


if __name__ == "__main__":
    environ.Env.read_env()
    env = environ.Env()
    if env.bool("USE_CLOUD_LOGGING"):
        client = google.cloud.logging.Client()
        client.setup_logging()

    # Start up Django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    get_wsgi_application()

    # Delay import so Django is set up first
    from icpc_mexico_scoreboard.app import start
    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        pass
