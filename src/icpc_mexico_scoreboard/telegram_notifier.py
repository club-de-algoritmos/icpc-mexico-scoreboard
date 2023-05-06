import os
from typing import List

from telegram import Bot
from telegram.error import TelegramError
from telegram.constants import ParseMode


_bot = Bot(token=os.environ["TELEGRAM_BOT_TOKEN"])
try:
    _bot.get_me()
except TelegramError:
    print("Could not connect to Telegram")
    raise Exception("Could not connect to Telegram, please check the Telegram API token is correct")

# chat_id = _bot.getUpdates()[0].message.chat.id
# print(f'Chat ID: {chat_id}')


def _get_chat_ids() -> List[str]:
    return os.environ["TELEGRAM_CHAT_IDS"].split(",")


def send_message(text):
    for chat_id in _get_chat_ids():
        try:
            _send_message(text, chat_id)
        except Exception as e:
            print("Could not send Telegram message ", e)


def _send_message(text, chat_id):
    _bot.send_message(chat_id, text=_escape(text), parse_mode=ParseMode.MARKDOWN_V2)


def _escape(value):
    chars = ["_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"]
    escaped = str(value)
    for char in chars:
        escaped = escaped.replace(char, f"\\{char}")
    return escaped
