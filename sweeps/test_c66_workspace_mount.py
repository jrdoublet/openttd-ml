import tempfile
from pathlib import Path
from unittest import TestCase, mock
from run_c66_reference import docker_workspace

class WorkspaceMountTests(TestCase):
    def test_same_root_keeps_original_workdir(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            with mock.patch("run_c66_reference.ROOT", root):
                self.assertEqual(docker_workspace(), (root, "/work"))

    def test_parent_mount_selects_actual_isolated_root(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp).resolve()
            with mock.patch("run_c66_reference.ROOT", parent / "results" / "isolated"):
                self.assertEqual(docker_workspace(parent), (parent, "/work/results/isolated"))

    def test_unrelated_mount_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp).resolve()
            with mock.patch("run_c66_reference.ROOT", parent / "isolated"):
                with self.assertRaises(ValueError):
                    docker_workspace(parent / "other")
