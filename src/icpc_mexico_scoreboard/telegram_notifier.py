import asyncio
import os
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable, List

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler


@dataclass(frozen=True)
class TelegramUser:
    chat_id: int

    @staticmethod
    def from_update(update: Update) -> 'TelegramUser':
        return TelegramUser(chat_id=update.effective_chat.id)


_GetScoreboardCallback = Callable[[TelegramUser, Optional[str]], Awaitable[None]]
_FollowCallback = Callable[[TelegramUser, str], Awaitable[None]]
_ShowFollowingCallback = Callable[[TelegramUser], Awaitable[None]]
_StopFollowingCallback = Callable[[TelegramUser, str], Awaitable[None]]


def _get_command_args(message: str) -> Optional[str]:
    separator = message.find(' ')
    if separator < 0:
        return None
    return message[separator:].strip() or None


class TelegramNotifier:
    _app: Optional[Application]
    _get_scoreboard_callback: Optional[_GetScoreboardCallback]
    _follow_callback: Optional[_FollowCallback]
    _show_following_callback: Optional[_ShowFollowingCallback]
    _stop_following_callback: Optional[_StopFollowingCallback]

    async def start_running(self,
                            get_scoreboard_callback: _GetScoreboardCallback,
                            follow_callback: _FollowCallback,
                            show_following_callback: _ShowFollowingCallback,
                            stop_following_callback: _StopFollowingCallback,
                            ) -> None:
        self._app = Application.builder().token(os.environ["ICPC_MX_TELEGRAM_BOT_TOKEN"]).build()
        self._app.add_handler(CommandHandler("scoreboard", self._get_scoreboard))
        self._app.add_handler(CommandHandler("seguir", self._follow))
        self._app.add_handler(CommandHandler("dejar", self._show_following))
        self._app.add_handler(CallbackQueryHandler(self._stop_following))
        # TODO: Top
        # TODO: Help

        self._get_scoreboard_callback = get_scoreboard_callback
        self._follow_callback = follow_callback
        self._show_following_callback = show_following_callback
        self._stop_following_callback = stop_following_callback

        await self._app.initialize()
        await self._app.updater.start_polling()
        await asyncio.ensure_future(self._app.start())

    async def stop_running(self) -> None:
        if self._app:
            await self._app.shutdown()

    async def _get_scoreboard(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        search_text = _get_command_args(update.message.text)
        await self._get_scoreboard_callback(TelegramUser.from_update(update), search_text)

    async def _follow(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        follow_text = _get_command_args(update.message.text)
        if not follow_text:
            await update.message.reply_html('Especifica una subcadena despues de <code>/seguir</code>')
            return
        await self._follow_callback(TelegramUser.from_update(update), follow_text)

    async def _show_following(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        await self._show_following_callback(TelegramUser.from_update(update))

    async def show_following(self, subscriptions: List[str], chat_id: int) -> None:
        keyboard = [[InlineKeyboardButton(subscription, callback_data=subscription)] for subscription in subscriptions]
        markup = InlineKeyboardMarkup(keyboard)
        try:
            await self._app.bot.send_message(
                chat_id=chat_id,
                text="Elige lo que deseas dejar de seguir:",
                reply_markup=markup,
            )
        except Exception as e:
            print("Could not send Telegram message ", e)

    async def _stop_following(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        unfollow_text = update.callback_query.data
        await self._stop_following_callback(TelegramUser.from_update(update), unfollow_text)

    async def send_message(self, text: str, chat_id: int) -> None:
        try:
            await self._app.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)
        except Exception as e:
            print("Could not send Telegram message ", e)
