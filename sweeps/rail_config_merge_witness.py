"""Strict composite SHA witnesses for the ROAD1Y + RAIL merge.

This does not project bytes and does not modify any historical fixture. The
existing exact OFF projector must run first; this verifier then enforces the
source/output SHA256 pair recorded for this merge, or retains the old frozen
SHA expectation on the standalone RAIL branch.
"""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads(
    (Path(__file__).parent / 'fixtures/rail_config_merge_sha_20261105.json')
    .read_text(encoding='utf-8')
)


def expected_off_sha(name, layer, original_sha, live):
    info = (ROOT / 'ai/OpexAI/info.nut').read_bytes()
    if b'name = "road1y_load_orders"' not in info:
        return original_sha
    source_sha = FIXTURE['source'].get(name)
    expected = FIXTURE[layer].get(name)
    if source_sha is None or expected is None:
        raise AssertionError(f'merged RAIL {layer} {name}: missing reviewed witness')
    if hashlib.sha256(live if isinstance(live, bytes) else live.encode('utf-8')).hexdigest() != source_sha:
        raise AssertionError(f'merged RAIL {layer} {name}: source SHA mismatch')
    return expected
