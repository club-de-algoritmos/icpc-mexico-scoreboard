import asyncio
import os
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes


@dataclass(frozen=True)
class TelegramUser:
    chat_id: int


_GetRankCallback = Callable[[TelegramUser], Awaitable[None]]


class TelegramNotifier:
    _app: Optional[Application]
    _get_rank_callback: Optional[_GetRankCallback]

    async def start_running(self, get_rank_callback: _GetRankCallback) -> None:
        self._app = Application.builder().token(os.environ["ICPC_MX_TELEGRAM_BOT_TOKEN"]).build()
        self._app.add_handler(CommandHandler("rank", self._get_rank))

        self._get_rank_callback = get_rank_callback

        await self._app.initialize()
        await self._app.updater.start_polling()
        await asyncio.ensure_future(self._app.start())

    async def stop_running(self) -> None:
        if self._app:
            await self._app.shutdown()

    async def _get_rank(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._get_rank_callback(TelegramUser(chat_id=update.effective_chat.id))

    async def send_message(self, text: str, chat_id: int) -> None:
        try:
            await self._app.bot.send_message(chat_id, text=text, parse_mode=ParseMode.HTML)
        except Exception as e:
            print("Could not send Telegram message ", e)
