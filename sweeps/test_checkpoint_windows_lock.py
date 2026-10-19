"""Checkpoints survive transient Windows/Docker sharing failures, without a game."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import bench_v2
import bench_1v1_5y_20seeds as duel


class TestCheckpointWindowsLock(unittest.TestCase):
    def test_transient_denial_recovers_without_duplicate_records(self):
        original_open = os.open
        for module in (bench_v2, duel):
            with self.subTest(module=module.__name__), tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "checkpoints.jsonl"
                attempts = 0

                def sometimes_locked(*args):
                    nonlocal attempts
                    attempts += 1
                    if attempts <= 2:
                        raise PermissionError(13, "temporarily locked")
                    return original_open(*args)

                with mock.patch.object(module, "CHECKPOINT_PATH", path), \
                     mock.patch.object(bench_v2.os, "open", side_effect=sometimes_locked), \
                     mock.patch.object(bench_v2.time, "sleep") as sleep:
                    module.append_checkpoint({"run": ["test", 42, 0]})

                self.assertEqual(attempts, 3)
                self.assertEqual(sleep.call_args_list, [mock.call(0.25)] * 2)
                # os.open() uses text-mode newline conversion on native Windows.
                self.assertEqual(path.read_bytes().splitlines(), [b'{"run":["test",42,0]}'])

    def test_persistent_denial_fails_and_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "checkpoints.jsonl"
            path.write_bytes(b'existing\n')
            with mock.patch.object(bench_v2.os, "open", side_effect=PermissionError(13, "locked")) as opening, \
                 mock.patch.object(bench_v2.time, "sleep") as sleep:
                with self.assertRaises(PermissionError):
                    bench_v2.open_checkpoint_append(path)

            self.assertEqual(opening.call_count, 21)
            self.assertEqual(sleep.call_count, 20)
            self.assertEqual(path.read_bytes(), b'existing\n')

    def test_other_io_errors_are_not_retried(self):
        with mock.patch.object(bench_v2.os, "open", side_effect=OSError(28, "disk full")) as opening, \
             mock.patch.object(bench_v2.time, "sleep") as sleep:
            with self.assertRaises(OSError):
                bench_v2.open_checkpoint_append("ignored.jsonl")
            opening.assert_called_once()
            sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
