from asgiref.sync import sync_to_async
from django import db


@sync_to_async
def close_connection() -> None:
    db.connections["default"].close()
