import unittest
from unittest.mock import MagicMock

from icpc_mexico_scoreboard.telegram_notifier import TelegramUser, _get_command_args


class GetCommandArgsTest(unittest.TestCase):
    def test_no_args_returns_none(self) -> None:
        self.assertIsNone(_get_command_args("/seguir"))

    def test_only_whitespace_args_returns_none(self) -> None:
        self.assertIsNone(_get_command_args("/seguir   "))

    def test_returns_the_stripped_args(self) -> None:
        self.assertEqual(_get_command_args("/seguir itsur"), "itsur")

    def test_keeps_internal_whitespace(self) -> None:
        self.assertEqual(_get_command_args("/seguir  ITSUR Culiacan  "), "ITSUR Culiacan")


class TelegramUserFromUpdateTest(unittest.TestCase):
    def test_extracts_the_effective_chat_id(self) -> None:
        update = MagicMock()
        update.effective_chat.id = 12345

        self.assertEqual(TelegramUser.from_update(update), TelegramUser(chat_id=12345))
