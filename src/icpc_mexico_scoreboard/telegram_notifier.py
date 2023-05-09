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

    @staticmethod
    def from_update(update: Update) -> 'TelegramUser':
        return TelegramUser(chat_id=update.effective_chat.id)


_GetScoreboardCallback = Callable[[TelegramUser], Awaitable[None]]

_FollowCallback = Callable[[TelegramUser, str], Awaitable[None]]


class TelegramNotifier:
    _app: Optional[Application]
    _get_scoreboard_callback: Optional[_GetScoreboardCallback]
    _follow_callback: Optional[_FollowCallback]

    async def start_running(self,
                            get_scoreboard_callback: _GetScoreboardCallback,
                            follow_callback: _FollowCallback,
                            ) -> None:
        self._app = Application.builder().token(os.environ["ICPC_MX_TELEGRAM_BOT_TOKEN"]).build()
        self._app.add_handler(CommandHandler("scoreboard", self._get_scoreboard))
        self._app.add_handler(CommandHandler("seguir", self._follow))

        self._get_scoreboard_callback = get_scoreboard_callback
        self._follow_callback = follow_callback

        await self._app.initialize()
        await self._app.updater.start_polling()
        await asyncio.ensure_future(self._app.start())

    async def stop_running(self) -> None:
        if self._app:
            await self._app.shutdown()

    async def _get_scoreboard(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        await self._get_scoreboard_callback(TelegramUser.from_update(update))

    async def _follow(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        follow_text = update.message.text
        separator = follow_text.find(' ')
        follow_text = follow_text[separator:].strip()
        if separator < 0 or not follow_text:
            await update.message.reply_html('Especifica una subcadena despues de <code>/seguir</code>')
            return
        await self._follow_callback(TelegramUser.from_update(update), follow_text)

    async def send_message(self, text: str, chat_id: int) -> None:
        try:
            await self._app.bot.send_message(chat_id, text=text, parse_mode=ParseMode.HTML)
        except Exception as e:
            print("Could not send Telegram message ", e)
