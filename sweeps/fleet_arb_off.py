"""Strict outermost FLEET-ARB projection; never rebase historical witnesses.

Each reviewed substitution is reversed literally and the resulting UTF-8 source
must match the pre-feature SHA256. A partial edit fails closed. New standalone
modules are absent OFF; existing files are restored byte for byte (LF Git blobs).
"""
from pathlib import Path
import hashlib
import json

FIXTURE = Path(__file__).with_name("fixtures") / "fleet_arb_off_20261105.json"
MANIFEST = json.loads(FIXTURE.read_text(encoding="utf-8"))
NEW_MODULES = {"fleet_arb.nut", "fleet_arb_quotes.nut"}


def off_source(name, source):
    name = Path(name).name
    if name in NEW_MODULES:
        return ""
    if not any(token in source for token in ("FLEET_ARB", "FLEET-ARB", "OpexFleet", "fleet_arb")):
        return source
    if name not in MANIFEST["files"]:
        raise AssertionError(f"FLEET-ARB {name}: unregistered wiring")
    entry = MANIFEST["files"][name]
    for edit in reversed(entry["edits"]):
        if source.count(edit["after"]) != 1:
            raise AssertionError(f"FLEET-ARB {name}: partial or modified wiring")
        source = source.replace(edit["after"], edit["before"], 1)
    if hashlib.sha256(source.encode("utf-8")).hexdigest() != entry["sha256"]:
        raise AssertionError(f"FLEET-ARB {name}: historical source changed")
    return source


def off_bytes(name, source):
    return off_source(name, source.decode("utf-8")).encode("utf-8")


def historical_read_text(path, *args, **kwargs):
    """Explicit reader for pre-FLEET-ARB contracts; never patches pathlib."""
    source = path.read_text(*args, **kwargs)
    return off_source(path.name, source) if path.parent.name == "OpexAI" and path.suffix == ".nut" else source


def historical_read_bytes(path):
    source = path.read_bytes()
    return off_bytes(path.name, source) if path.parent.name == "OpexAI" and path.suffix == ".nut" else source
