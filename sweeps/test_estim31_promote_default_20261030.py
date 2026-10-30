import unittest

from sweeps.estim31_promote_default_20261030 import edit_setting, promote


class PromotionSafety(unittest.TestCase):
    def test_replace_existing_values_only(self):
        sample = ('AddSetting({ name = "estim_unifie", min_value = 0, max_value = 31, '
                  'easy_value = 0, medium_value = 0, hard_value = 0, '
                  'custom_value = 0, default_value = 0, step_size = 1 });')
        edited = edit_setting(sample, 'estim_unifie', 31)
        self.assertIn('min_value = 0, max_value = 31', edited)
        for key in ('easy_value', 'medium_value', 'hard_value',
                    'custom_value', 'default_value'):
            self.assertIn(f'{key} = 31', edited)
        with self.assertRaises(ValueError):
            edit_setting(sample, 'missing_setting', 3)

    def test_refuses_incomplete_ten_year_default_election(self):
        from pathlib import Path
        with self.assertRaisesRegex(ValueError, 'qualified'):
            promote(Path('/none'), Path('/none'),
                    {'winner': {'health': '40/40 complete'},
                     'ranked_healthy_20x10': []}, apply=False)


if __name__ == '__main__':
    unittest.main()
