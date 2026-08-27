"""Tests unitaires du nettoyage d'autosaves v3, sans lancer OpenTTD."""
import importlib.util
import multiprocessing
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest


SCRIPT = Path(__file__).parents[1] / "sweeps" / "phase2_hurdle_dataset_v3.py"
MODULE_NAME = "phase2_hurdle_dataset_v3_cleanup_test_subject"
MISSING = object()


class SavegameCleanupTest(unittest.TestCase):
    def setUp(self):
        self.previous_openttdlab = sys.modules.get("openttdlab", MISSING)
        self.openttdlab = types.ModuleType("openttdlab")
        self.openttdlab._run_experiment = lambda *args, **kwargs: None
        self.openttdlab.bananas_ai_library = lambda *args, **kwargs: None
        self.openttdlab.local_folder = lambda *args, **kwargs: None
        self.openttdlab.run_experiments = lambda *args, **kwargs: None
        sys.modules["openttdlab"] = self.openttdlab
        spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT)
        self.subject = importlib.util.module_from_spec(spec)
        sys.modules[MODULE_NAME] = self.subject
        spec.loader.exec_module(self.subject)

    def tearDown(self):
        sys.modules.pop(MODULE_NAME, None)
        if self.previous_openttdlab is MISSING:
            sys.modules.pop("openttdlab", None)
        else:
            sys.modules["openttdlab"] = self.previous_openttdlab

    def install(self, original):
        self.openttdlab._run_experiment = original
        self.subject.enable_savegame_cleanup()
        return self.openttdlab._run_experiment

    def test_cleanup_after_return_binds_run_dir_and_i_by_name(self):
        seen = []

        def original(*, final_screenshot_directory=None, i, run_dir):
            seen.append((run_dir, i, os.path.isdir(os.path.join(run_dir, str(i)))))
            return "parsed-and-checkpointed"

        wrapper = self.install(original)
        with tempfile.TemporaryDirectory() as run_dir:
            attempt_dir = os.path.join(run_dir, "73")
            os.mkdir(attempt_dir)
            self.assertEqual(
                wrapper(run_dir=run_dir, i=73, final_screenshot_directory=None),
                "parsed-and-checkpointed",
            )
            self.assertEqual(seen, [(run_dir, 73, True)])
            self.assertFalse(os.path.exists(attempt_dir))

    def test_rmtree_error_cannot_fail_an_attempt(self):
        def original(*, final_screenshot_directory=None, i, run_dir):
            return "checkpoint-written"

        wrapper = self.install(original)
        real_rmtree = self.subject.shutil.rmtree

        def failing_rmtree(*args, **kwargs):
            self.assertTrue(kwargs["ignore_errors"])
            raise OSError("simulated cleanup failure")

        self.subject.shutil.rmtree = failing_rmtree
        try:
            self.assertEqual(
                wrapper(run_dir="/unused", i=1, final_screenshot_directory=None),
                "checkpoint-written",
            )
        finally:
            self.subject.shutil.rmtree = real_rmtree

    def test_final_screenshot_directory_is_refused(self):
        called = False

        def original(*, final_screenshot_directory=None, i, run_dir):
            nonlocal called
            called = True

        wrapper = self.install(original)
        with self.assertRaisesRegex(AssertionError, "final_screenshot_directory"):
            wrapper(run_dir="/unused", i=1, final_screenshot_directory="screenshots")
        self.assertFalse(called)

    @unittest.skipUnless("fork" in multiprocessing.get_all_start_methods(), "requires Linux fork")
    def test_wrapper_survives_apply_async_pickle_as_main_reference(self):
        def original(*, final_screenshot_directory=None, i, run_dir):
            return (run_dir, i)

        wrapper = self.install(original)
        main = sys.modules["__main__"]
        old_module = wrapper.__module__
        old_main_value = getattr(main, wrapper.__name__, MISSING)
        wrapper.__module__ = "__main__"
        setattr(main, wrapper.__name__, wrapper)
        try:
            with tempfile.TemporaryDirectory() as run_dir:
                attempt_dir = os.path.join(run_dir, "19")
                os.mkdir(attempt_dir)
                with multiprocessing.get_context("fork").Pool(1) as pool:
                    result = pool.apply_async(
                        wrapper,
                        kwds={"run_dir": run_dir, "i": 19, "final_screenshot_directory": None},
                    ).get(timeout=10)
                self.assertEqual(result, (run_dir, 19))
                self.assertFalse(os.path.exists(attempt_dir))
        finally:
            wrapper.__module__ = old_module
            if old_main_value is MISSING:
                delattr(main, wrapper.__name__)
            else:
                setattr(main, wrapper.__name__, old_main_value)


if __name__ == "__main__":
    unittest.main()
