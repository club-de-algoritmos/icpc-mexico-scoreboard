import asyncio
import html
import json
import logging
import os
import traceback
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable, List, Any

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TelegramUser:
    chat_id: int

    @staticmethod
    def from_update(update: Update) -> 'TelegramUser':
        return TelegramUser(chat_id=update.effective_chat.id)


_GetTopCallback = Callable[[TelegramUser, Optional[int]], Awaitable[None]]
_GetScoreboardCallback = Callable[[TelegramUser, Optional[str]], Awaitable[None]]
_FollowCallback = Callable[[TelegramUser, str], Awaitable[None]]
_ShowFollowingCallback = Callable[[TelegramUser], Awaitable[None]]
_StopFollowingCallback = Callable[[TelegramUser, str], Awaitable[None]]


_DEVELOPER_CHAT_ID = int(os.environ["ICPC_MX_TELEGRAM_DEVELOPER_CHAT_ID"])
_MESSAGE_SIZE_LIMIT = 4096


def _get_command_args(message: str) -> Optional[str]:
    separator = message.find(' ')
    if separator < 0:
        return None
    return message[separator:].strip() or None


class TelegramNotifier:
    _app: Optional[Application]
    _get_top_callback: Optional[_GetTopCallback]
    _get_scoreboard_callback: Optional[_GetScoreboardCallback]
    _follow_callback: Optional[_FollowCallback]
    _show_following_callback: Optional[_ShowFollowingCallback]
    _stop_following_callback: Optional[_StopFollowingCallback]

    async def start_running(self,
                            get_top_callback: _GetTopCallback,
                            get_scoreboard_callback: _GetScoreboardCallback,
                            follow_callback: _FollowCallback,
                            show_following_callback: _ShowFollowingCallback,
                            stop_following_callback: _StopFollowingCallback,
                            ) -> None:

        token = os.environ["ICPC_MX_TELEGRAM_BOT_TOKEN"]
        self._app = Application.builder().token(token).build()

        self._app.add_handler(CommandHandler("top", self._get_top))
        self._app.add_handler(CommandHandler("scoreboard", self._get_scoreboard))
        self._app.add_handler(CommandHandler("seguir", self._follow))
        self._app.add_handler(CommandHandler("dejar", self._show_following))
        self._app.add_handler(CallbackQueryHandler(self._stop_following))
        self._app.add_handler(CommandHandler("ayuda", self._help))
        self._app.add_error_handler(self._handle_error)

        self._get_top_callback = get_top_callback
        self._get_scoreboard_callback = get_scoreboard_callback
        self._follow_callback = follow_callback
        self._show_following_callback = show_following_callback
        self._stop_following_callback = stop_following_callback

        await self._app.initialize()
        commands = [
            BotCommand("top", "Entérate del top del scoreboard"),
            BotCommand("scoreboard", "Entérate del scoreboard de tus equipos"),
            BotCommand("seguir", "Comienza a seguir equipos"),
            BotCommand("dejar", "Deja de seguir equipos"),
            BotCommand("ayuda", "Muestra la ayuda sobre los comandos"),
        ]
        await self._app.bot.set_my_commands(commands)

        await self._app.updater.start_polling()
        # Start it up async
        await asyncio.ensure_future(self._app.start())

    async def stop_running(self) -> None:
        if self._app:
            await self._app.shutdown()

    async def _get_top(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        top_n_text = _get_command_args(update.message.text)
        top_n = None
        if top_n_text:
            try:
                top_n = int(top_n_text)
            except ValueError:
                pass

        await self._get_top_callback(TelegramUser.from_update(update), top_n)

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

    async def _help(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_html(
'''¡Yo puedo ayudarte a mantenerte informado sobre el scoreboard del ICPC México!

<a href="/top">/top</a> - Entérate del top 10 del scoreboard, agrega un entero para especificar cuántos equipos quieres ver. Por ejemplo, <code>/top 5</code>.
<a href="/scoreboard">/scoreboard</a> - Entérate del scoreboard filtrado por los equipos que estás siguiendo. Especifica una subcdena si quieres saber sobre algunos equipos solamente, y no los que sigues, por ejemplo, <code>/scoreboard itsur</code>.
<a href="/seguir">/seguir</a> - Comienza a seguir equipos cuyo nombre tengan la subcadena que especifiques, te notificaremos cuando estos equipos resuelvan un problema. Por ejemplo, <code>/seguir Culiacan</code>.
<a href="/dejar">/dejar</a> - Úsalo cuando quieras dejar de seguir a algunos equipos, sólo da click en la subcadena que quieras dejar de seguir.
'''
        )

    async def send_developer_message(self, text: str) -> None:
        await self.send_message(text, _DEVELOPER_CHAT_ID)

    async def send_message(self, text: str, chat_id: int) -> None:
        try:
            await self._app.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)
        except Exception as e:
            print("Could not send Telegram message ", e)

    async def _handle_error(self, update: Any, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log the error and send a telegram message to notify the developer."""
        # Log the error before we do anything else, so we can see it even if something breaks.
        logger.error("Exception while handling an update:", exc_info=context.error)

        tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
        tb_string = "".join(tb_list)

        # Build the message with some markup and additional information about what happened
        update_str = update.to_dict() if isinstance(update, Update) else str(update)
        message = (
            f"An exception was raised while handling an update\n"
            f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
            "</pre>\n\n"
            f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
            f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
            f"<pre>{html.escape(tb_string)}</pre>"
        )
        if len(message) > _MESSAGE_SIZE_LIMIT:
            message = message[:_MESSAGE_SIZE_LIMIT-3] + "..."

        await self.send_developer_message(message)
