"""Project reviewed opt-in V233L edits to OFF for immutable legacy contracts.

The fixture records both sides, anchored by surrounding source. A changed
guard must fail rather than silently get erased. This is a source-level
projection; execution timing and VM equivalence still require a real smoke.
"""
import json
from pathlib import Path

FIXTURE = json.loads((Path(__file__).parent / "fixtures/v233_long_good_off.json").read_text())


def off_source(name, code):
    from estim_unifie_legacy import estim_off
    code = estim_off(name, code)
    from air_site_probe_legacy import off_source as air_probe_off
    code = air_probe_off(name, code)
    entry = FIXTURE["files"].get(name)
    if entry is None:
        return code
    for edit in reversed(entry["edits"]):
        guarded = edit["guarded"]
        # The frozen V233L fixture predates permanent cash-reserve removal.
        # Its V233L dispatch is still exact once the obsolete argument is dropped.
        if (name == "builder_rail.nut" and guarded ==
                "  if (OpexV233LIs(candidate)) return OpexV190ExecuteRailPlan(catalog, budget, candidate, plan, cashReserve);\n"):
            guarded = "  if (OpexV233LIs(candidate)) return OpexV190ExecuteRailPlan(catalog, budget, candidate, plan);\n"
        assert code.count(guarded) == 1, f"V233L {name}: guarded hunk changed"
        code = code.replace(guarded, edit["off"], 1)
    return code


def off_bytes(name, code):
    return off_source(name, code.decode("utf-8")).encode("utf-8")
