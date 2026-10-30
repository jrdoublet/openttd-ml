"""A default must not be elected until all three healthy 20x10 are complete."""
import unittest

from sweeps.estim31_default_release_20261030 import make_default_info, prepare


class DefaultRelease(unittest.TestCase):
    def test_rewrite_only_three_existing_defaults(self):
        blocks = []
        for name in ('estim_unifie', 'eb14_progressive', 'probes'):
            default = 'default_value = 0, ' if name != 'probes' else ''
            blocks.append(f'AddSetting({{ name = "{name}", description="0 none (default)", '
                          'min_value=0, max_value=31, easy_value=0, '
                          'medium_value=0, hard_value=0, custom_value=0, '
                          f'{default} flags = 0 }});')
        original = '\n'.join(blocks) + '\nother_constant <- 33;'
        new = make_default_info(original)
        for number in (31, 3, 2):
            self.assertIn(f'easy_value={number}', new)
        self.assertIn('other_constant <- 33', new)
        self.assertEqual(original.count('AddSetting'), new.count('AddSetting'))
        with self.assertRaises(ValueError):
            make_default_info('AddSetting({ name = "probes", easy_value=0 });')

    def test_refuse_unqualified_economic_data(self):
        from pathlib import Path
        with self.assertRaisesRegex(ValueError, 'before three healthy'):
            prepare(Path('/missing'), {'winner': {'suite': 'v161'}}, Path('/unused'))


if __name__ == '__main__':
    unittest.main()
