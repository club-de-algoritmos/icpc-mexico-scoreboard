import asyncio
import os

from django.core.wsgi import get_wsgi_application


if __name__ == "__main__":
    # Start up Django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    get_wsgi_application()

    # Delay import so Django is set up first
    from icpc_mexico_scoreboard.app import start
    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        pass
