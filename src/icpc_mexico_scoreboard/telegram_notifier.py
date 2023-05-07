import asyncio
import os
from typing import List

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes


def _get_chat_ids() -> List[str]:
    return os.environ["ICPC_MX_TELEGRAM_CHAT_IDS"].split(",")


class TelegramNotifier:
    _app: Application

    async def start_running(self) -> None:
        self._app = Application.builder().token(os.environ["ICPC_MX_TELEGRAM_BOT_TOKEN"]).build()
        self._app.add_handler(CommandHandler("start", self._start))
        await self._app.initialize()
        await self._app.updater.start_polling()
        await asyncio.ensure_future(self._app.start())

    async def stop_running(self) -> None:
        await self._app.shutdown()

    async def _start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Displays info on how to trigger an error."""
        await update.effective_message.reply_html(
            f"Your chat id is <code>{update.effective_chat.id}</code>."
        )

    async def send_message(self, text: str) -> None:
        for chat_id in _get_chat_ids():
            try:
                await self._app.bot.send_message(chat_id, text=text, parse_mode=ParseMode.MARKDOWN_V2)
            except Exception as e:
                print("Could not send Telegram message ", e)
