"""Ported shared-model full-body costs and ordinary Save/Load; staged probes only."""
import argparse
import hashlib
import json
from pathlib import Path
from .run_mechanism_fixtures import replace_once

ROOT = Path(__file__).resolve().parents[1]
PREPORT = ROOT / "results/c121_target_limit/visible_fused_body_20261008_r2/ai/OpexAI"


def reload_transform(target):
    (target / "c121_visible_flux_vm.nut").write_bytes((ROOT / "tests/mechanisms/c121_visible_flux_vm.nut").read_bytes())
    source = target / "air_fleet.nut"
    text = replace_once(source.read_text(encoding="utf8"), "  OpexC121PrepareEngineStatic(catalog, quote);",
        "  OpexC121PrepareEngineStatic(catalog, quote);\n  FxVPMatrix(catalog, quote, plane, pax, mail, have);")
    source.write_text(text, encoding="utf8")


def transform(target, *, off=False):
    source = target / "air_fleet.nut"
    text = source.read_text(encoding="utf8")
    start = text.index("function OpexC121RefreshVisibleFleet(")
    end = text.index("\nfunction ", start+1)
    current = text[start:end]
    if off:
        plan = json.loads((PREPORT.parents[1] / "plan.json").read_text(encoding="utf8"))
        for name in ("air_fleet.nut", "air_economics_c121.nut"):
            if hashlib.sha256((PREPORT / name).read_bytes()).hexdigest() != plan["copied_hashes"]["opex"][name]:
                raise ValueError("pre-port reference changed")
        old = (PREPORT / "air_fleet.nut").read_text(encoding="utf8")
        first = old.index("function FxVFOriginal(")
        last = old.index("\nfunction ", first+1)
        original = old[first:last].replace("OpexC121AirEconomics(", "FxVPPrePortEconomics(")
        econ = target / "air_economics_c121.nut"
        old_econ = (PREPORT / "air_economics_c121.nut").read_text(encoding="utf8")
        first = old_econ.index("function OpexC121AirEconomics(")
        last = old_econ.index("\nfunction ", first+1)
        reference = old_econ[first:last].replace("function OpexC121AirEconomics(", "function FxVPPrePortEconomics(", 1)
        econ.write_text(econ.read_text(encoding="utf8")+"\n"+reference+"\n", encoding="utf8")
    else:
        original = current.replace("function OpexC121RefreshVisibleFleet(", "function FxVFOriginal(", 1)
        original = replace_once(original, "  OpexC121PrepareEngineStatic(catalog, quote);",
            "  OpexC121PrepareEngineStatic(catalog, quote);\n  FxVFInput(quote, pax, mail, have);")
    candidate = current.replace("function OpexC121RefreshVisibleFleet(", "function FxVFCandidate(", 1)
    candidate = replace_once(candidate, "  OpexC121PrepareEngineStatic(catalog, quote);",
        "  OpexC121PrepareEngineStatic(catalog, quote);\n  FxVFInput(quote, pax, mail, have);")
    source.write_text(text[:start]+original+text[end:]+"\n"+candidate+"\n", encoding="utf8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--off", action="store_true")
    parser.add_argument("--reload", action="store_true")
    args, rest = parser.parse_known_args()
    settings = (("c121_air_visible_competition", 1), ("c121_air_visible_fused", 0 if args.off else 1), ("decision_log", 1))
    if args.reload:
        from .run_c121_target_limit_fixtures import main
        main(rest, settings=settings, fixture=ROOT / "tests/mechanisms/c121_visible_port_reload_vm.nut",
             marker="C121_VISIBLE", stage_transform=reload_transform)
    else:
        from .run_c121_visible_newsite_fixture import main
        main(rest, settings=settings, fixture=ROOT / "tests/mechanisms/c121_visible_fused_cost_vm.nut",
             marker="C121_VISIBLE_FUSED", stage_transform=lambda target: transform(target, off=args.off))
