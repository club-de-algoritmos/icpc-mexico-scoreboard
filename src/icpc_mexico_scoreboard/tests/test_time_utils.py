import unittest
from datetime import datetime, timezone

from icpc_mexico_scoreboard.time_utils import format_as_local_time


class FormatAsLocalTimeTest(unittest.TestCase):
    def test_converts_utc_to_cdmx(self) -> None:
        # Mexico City has used a fixed UTC-6 offset year-round since DST was abolished in 2022.
        utc_time = datetime(2026, 1, 1, 18, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(format_as_local_time(utc_time), "2026-01-01 12:00:00 CDMX")

    def test_naive_datetime_is_treated_as_utc(self) -> None:
        naive_time = datetime(2026, 1, 1, 18, 0, 0)
        self.assertEqual(format_as_local_time(naive_time), "2026-01-01 12:00:00 CDMX")
