import asyncio
import os
from typing import List

from telegram import Bot
from telegram.error import TelegramError
from telegram.constants import ParseMode


_bot = Bot(token=os.environ["ICPC_MX_TELEGRAM_BOT_TOKEN"])
# try:
#     _bot.getMe()
# except TelegramError:
#     print("Could not connect to Telegram")
#     raise Exception("Could not connect to Telegram, please check the Telegram API token is correct")


async def display_chat_id():
    updates = await _bot.get_updates()
    print(f'Chat ID: {updates[0].message.chat.id}')

# asyncio.run(display_chat_id())


def _get_chat_ids() -> List[str]:
    return os.environ["ICPC_MX_TELEGRAM_CHAT_IDS"].split(",")


async def send_message(text):
    for chat_id in _get_chat_ids():
        try:
            await _bot.send_message(chat_id, text=text, parse_mode=ParseMode.MARKDOWN_V2)
        except Exception as e:
            print("Could not send Telegram message ", e)
