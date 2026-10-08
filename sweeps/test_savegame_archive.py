import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from savegame_archive import archive_savegames


class ArchiveTests(unittest.TestCase):
    def test_preserves_nested_bytes_hashes_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            source = root / "run" / "0" / "save"
            source.mkdir(parents=True)
            (source / "0.sav").write_bytes(b"original snapshot")
            archive_savegames(source.parent, root / "archive", 0)
            saved = root / "archive" / "0" / "save" / "0.sav"
            self.assertEqual(saved.read_bytes(), b"original snapshot")
            manifest = json.loads((saved.parent.parent / "archive.json").read_text())
            self.assertEqual(manifest["savegames"][0]["sha256"],
                             hashlib.sha256(saved.read_bytes()).hexdigest())
            with self.assertRaises(FileExistsError):
                archive_savegames(source.parent, root / "archive", 0)
            self.assertEqual(saved.read_bytes(), b"original snapshot")

    def test_failed_engine_with_no_saves_is_explicit_empty(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            self.assertEqual(archive_savegames(root / "missing", root / "out", 8), [])
            self.assertEqual(json.loads((root / "out" / "8" / "archive.json").read_text())
                             ["savegames"], [])
