"""Reviewed default-OFF additions; do not rebase historical hashes."""
import json
from pathlib import Path
from eb2_legacy import off_source as eb2_off

DELTAS = json.loads((Path(__file__).parent / "fixtures/air_site_ranked_off_deltas.json").read_text())


def off_source(name, text):
    text = eb2_off(name, text)
    entry = DELTAS.get(name)
    if entry is None or entry["marker"] not in text:
        return text
    assert text.count(entry["fragment"]) == 1, f"Ranked funnel {name}: OFF fragment changed"
    return text.replace(entry["fragment"], "", 1)
