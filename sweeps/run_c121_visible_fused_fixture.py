"""Experimental fused refresh on staged copies; full-body cost or Save/Load."""
import argparse
from pathlib import Path
from .run_c121_visible_redundancy_fixture import add_fused_model
from .run_mechanism_fixtures import replace_once

ROOT = Path(__file__).resolve().parents[1]


def transform(target):
    add_fused_model(target)
    (target / "c121_visible_flux_vm.nut").write_bytes((ROOT / "tests/mechanisms/c121_visible_flux_vm.nut").read_bytes())
    source = target / "air_fleet.nut"
    text = source.read_text(encoding="utf8")
    start = text.index("function OpexC121RefreshVisibleFleet(")
    end = text.index("\nfunction ", start+1)
    body = text[start:end]
    body = replace_once(body, "  OpexC121PrepareEngineStatic(catalog, quote);",
                        "  OpexC121PrepareEngineStatic(catalog, quote);\n  FxVFInput(quote, pax, mail, have);")
    candidate = body.replace("function OpexC121RefreshVisibleFleet(", "function FxVFCandidate(", 1)
    candidate = replace_once(candidate,
        "  local target = OpexC121AirEconomics(catalog, quote, plane, pax, mail, 0);\n"
        "  local before = OpexC121AirEconomics(catalog, quote, plane, pax, mail, have);\n"
        "  local after = OpexC121AirEconomics(catalog, quote, plane, pax, mail, have+1);",
        "  local captured = { have = have, values = {} };\n"
        "  local target = FxVRFused(catalog, quote, plane, pax, mail, 0, false, null, null, null, captured);\n"
        "  foreach (n in [have, have+1]) if (!(n in captured.values))\n"
        "    captured.values.rawset(n, OpexC121AirEconomics(catalog, quote, plane, pax, mail, n));\n"
        "  local before = captured.values[have];\n  local after = captured.values[have+1];")
    text = text[:start]+body.replace("function OpexC121RefreshVisibleFleet(", "function FxVFOriginal(", 1)+text[end:]
    source.write_text(text+"\n"+candidate+"\n", encoding="utf8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--reload", action="store_true")
    args, rest = parser.parse_known_args()
    if args.reload:
        from .run_c121_target_limit_fixtures import main
        main(rest, settings=(("c121_air_visible_competition", 1), ("decision_log", 1)),
             fixture=ROOT / "tests/mechanisms/c121_visible_fused_reload_vm.nut",
             marker="C121_VISIBLE", stage_transform=transform)
    else:
        from .run_c121_visible_newsite_fixture import main
        main(rest, settings=(("c121_air_visible_competition", 1), ("decision_log", 1)),
             fixture=ROOT / "tests/mechanisms/c121_visible_fused_cost_vm.nut",
             marker="C121_VISIBLE_FUSED", stage_transform=transform)
