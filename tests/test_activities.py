import unittest

from coach.activities import format_activity


class FormatActivityAchievementTests(unittest.TestCase):
    def test_preserves_compact_achievement_for_weekly_review(self):
        raw = {
            "id": "i123",
            "start_date_local": "2026-07-22T07:06:09",
            "type": "Run",
            "name": "Long Run",
            "distance": 22013.08,
            "moving_time": 7424,
            "icu_achievements": [
                {
                    "id": "pa0_107",
                    "type": "BEST_PACE",
                    "secs": 7072,
                    "distance": 21097.5,
                    "pace": 2.9832437,
                    "point": {"start_index": 4, "end_index": 7077},
                }
            ],
        }

        formatted, _ = format_activity(raw)

        self.assertEqual(
            formatted["achievements"],
            [
                {
                    "type": "BEST_PACE",
                    "distance_m": 21097.5,
                    "duration_s": 7072,
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
