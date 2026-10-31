import unittest

from sweeps.estim31_promote_default_20261030 import (
    edit_setting, promote, mirror_verified_files, verify_exact_simulated_source)
from sweeps.campaign_freeze import fingerprint_tree


class PromotionSafety(unittest.TestCase):
    def test_executed_source_is_byte_identical_to_deployable_bundle(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            base = Path(directory)
            campaign = 'ten'
            frozen = base / 'results' / (campaign + '_bundle')
            for prefix in ('ai/OpexAI', 'ai_libraries'):
                (base / prefix).mkdir(parents=True)
                (frozen / prefix).mkdir(parents=True)
                (base / prefix / 'one.nut').write_bytes(b'tested')
                (frozen / prefix / 'one.nut').write_bytes(b'tested')
            fingerprint = fingerprint_tree(frozen)['sha256']
            self.assertEqual(
                verify_exact_simulated_source(base, campaign, fingerprint),
                {'ai/OpexAI': 1, 'ai_libraries': 1})
            (base / 'ai/OpexAI/one.nut').write_bytes(b'drift')
            with self.assertRaisesRegex(ValueError, 'differs from executed'):
                verify_exact_simulated_source(base, campaign, fingerprint)
            (frozen / 'ai/OpexAI/one.nut').write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError, 'fingerprint'):
                verify_exact_simulated_source(base, campaign, fingerprint)

    def test_noai_libraries_are_mirrored_and_verified(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source, target = root / 'bundle_ai_libraries', root / 'installed_ai_libraries'
            source.mkdir()
            (source / 'Graph.tar').write_bytes(b'original')
            self.assertEqual(mirror_verified_files(source, target), (['Graph.tar'], 1))
            self.assertFalse(target.exists())
            self.assertEqual(mirror_verified_files(source, target, apply=True), (['Graph.tar'], 1))
            self.assertEqual((target / 'Graph.tar').read_bytes(), b'original')
            self.assertEqual(mirror_verified_files(source, target), ([], 1))
            (target / 'alien.tar').write_bytes(b'not from tested bundle')
            with self.assertRaisesRegex(ValueError, 'Unmapped production-only'):
                mirror_verified_files(source, target, apply=True)

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

    def test_probes_signs_default_without_explicit_default_value(self):
        source = ('AddSetting({ name = "probes", description = "0 none (default)", '
                  'min_value = 0, max_value = 2147483647, '
                  'easy_value = 0, medium_value = 0, hard_value = 0, '
                  'custom_value = 0, flags = 0 });')
        actual = edit_setting(source, 'probes', 2)
        self.assertIn('easy_value = 2, medium_value = 2', actual)
        self.assertIn('custom_value = 2', actual)
        self.assertNotIn('default_value', actual)

    def test_refuses_incomplete_ten_year_default_election(self):
        from pathlib import Path
        with self.assertRaisesRegex(ValueError, 'qualified'):
            promote(Path('/none'), Path('/none'),
                    {'winner': {'health': '40/40 complete'},
                     'ranked_healthy_20x10': []}, apply=False)


if __name__ == '__main__':
    unittest.main()
