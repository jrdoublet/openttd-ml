"""Compare a fused fleet scan to three ordinary evaluations on the same quote.

Only staged copies change. The ordinary results drive natural play; no cache
invalidation is removed. Rich target equality and the three consumed marginal
fields are checked in NoAI. Missing depths use the original fixed-N evaluator.
"""
from pathlib import Path

from .run_c121_visible_newsite_fixture import main
from .run_mechanism_fixtures import replace_once

ROOT = Path(__file__).resolve().parents[1]


def add_fused_model(target):
    source = target / "air_economics_c121.nut"
    text = source.read_text(encoding="utf8")
    start = text.index("function OpexC121AirEconomics(")
    end = text.index("\nfunction ", start + 1)
    fused = text[start:end].replace("function OpexC121AirEconomics(", "function FxVRFused(", 1)
    fused = replace_once(fused, "engineContext = null)", "engineContext = null, marginalOut = null)")
    fused = replace_once(fused, "    local profitAnnual = revenueAnnual - runningAnnual - amortAnnual;",
        "    local profitAnnual = revenueAnnual - runningAnnual - amortAnnual;\n"
        "    if (marginalOut != null && (planes == marginalOut.have || planes == marginalOut.have+1))\n"
        "      marginalOut.values.rawset(planes, { profitAnnual = profitAnnual,\n"
        "        revenueAnnual = revenueAnnual, realizationFactor = realizationFactor });")
    source.write_text(text + "\n" + fused + "\n", encoding="utf8")


def transform(target):
    add_fused_model(target)
    source = target / "air_fleet.nut"
    text = source.read_text(encoding="utf8")
    text = replace_once(text,
        "  local target = OpexC121AirEconomics(catalog, quote, plane, pax, mail, 0);\n"
        "  local before = OpexC121AirEconomics(catalog, quote, plane, pax, mail, have);\n"
        "  local after = OpexC121AirEconomics(catalog, quote, plane, pax, mail, have+1);",
        "  local compared = FxVRCompare(catalog, quote, plane, pax, mail, have);\n"
        "  local target = compared.target;\n  local before = compared.before;\n  local after = compared.after;")
    text = replace_once(text, "  local now = AIDate.GetCurrentDate();\n  if (!force && line.lineId in C121_VISIBLE_FLEET_CACHE)",
        "  local now = AIDate.GetCurrentDate();\n"
        "  FxVRReason(line, now, force);\n  if (!force && line.lineId in C121_VISIBLE_FLEET_CACHE)")
    source.write_text(text, encoding="utf8")


if __name__ == "__main__":
    main(fixture=ROOT / "tests/mechanisms/c121_visible_redundancy_vm.nut",
         marker="C121_VISIBLE_REDUNDANCY", stage_transform=transform)
