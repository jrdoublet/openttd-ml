import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sweeps.estim31_default_install_worktree_20261030 import install


class GuardedInstallation(unittest.TestCase):
    def test_never_install_on_master(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            release = root / 'release'
            target = root / 'isolated'
            release.mkdir()
            target.mkdir()
            (release / 'release_manifest.json').write_text(
                json.dumps({'deployable_source_ready': True,
                            'production_ai_updated': False}), 'utf8')
            with patch('sweeps.estim31_default_install_worktree_20261030.git',
                       side_effect=[str(target), 'master']):
                with self.assertRaisesRegex(ValueError, 'shared master'):
                    install(release, target)

    def test_modified_target_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            release, target = root / 'release', root / 'isolated'
            release.mkdir()
            target.mkdir()
            (release / 'release_manifest.json').write_text(
                json.dumps({'deployable_source_ready': True,
                            'production_ai_updated': False}), 'utf8')
            with patch('sweeps.estim31_default_install_worktree_20261030.git',
                       side_effect=[str(target), 'experiments/default', ' M test.txt']):
                with self.assertRaisesRegex(ValueError, 'fully clean'):
                    install(release, target)


if __name__ == '__main__':
    unittest.main()
