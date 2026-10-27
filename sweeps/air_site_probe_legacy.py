"""Exact startup additions projected OFF; historical hashes are never rebased.

Idempotent so nested historical projections can share it. A present marker with
modified bytes fails instead of silently erasing a changed guard.
"""
import json
from pathlib import Path

DELTAS = json.loads((Path(__file__).parent / "fixtures/air_site_probe_off_deltas.json").read_text())


def off_source(name, text):
    entry = DELTAS.get(name)
    if entry is None or entry["marker"] not in text:
        return text
    fragment = entry["fragment"]
    assert text.count(fragment) == 1, f"AIR probe {name}: reviewed OFF fragment changed"
    return text.replace(fragment, "", 1)
