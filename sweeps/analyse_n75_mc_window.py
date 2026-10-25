"""N75-MC: direct 1972 cargo/date-window physical build attribution *candidates*.

This is an observational proxy, not a causal estimate: a matching cargo built
after N75 need not have come from that regeneration. Predictions are NOT
realised net profits. A comparison source may be constructed at another date.

Example:
  python -X utf8 sweeps/analyse_n75_mc_window.py nuit75_mc_expo_5x3_20261025
"""
import argparse
from datetime import date
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / "results"
LINE = re.compile(r'OPEX\s+(1972-\d+-\d+)\s+(N75_MC|RAIL_BUILD)\s+(.*)')
FIELD = re.compile(r'([a-z_]+)=([^ ]+)')


def read(path):
    events = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = LINE.search(raw)
        if not match:
            continue
        ds, event, rest = match.groups()
        fields = dict(FIELD.findall(rest))
        day = date(*map(int, ds.split("-")))
        events.append((day, event, fields))
    return events


def run(campaign, days=45):
    engine = ROOT / (campaign + "_engine")
    seeds = sorted(int(m.group(1)) for p in engine.glob("n75_mc_seed*_r0.log")
                   if (m := re.match(r'n75_mc_seed(\d+)_r0\.log$', p.name)))
    rows = []
    for seed in seeds:
        off = read(engine / f"reference_seed{seed}_r0.log")
        on = read(engine / f"n75_mc_seed{seed}_r0.log")
        for day, event, fields in on:
            if (event != "N75_MC" or fields.get("phase") != "refill"
                    or fields.get("budget_eligible") != "1"):
                continue
            cargo = fields["cargo"]
            new_lines = [(d, f) for d, e, f in on if e == "RAIL_BUILD"
                         and f.get("cargo") == cargo and 0 < (d - day).days <= days]
            sources = {f["src"] for _, f in new_lines}
            old_lines = [(d, f) for d, e, f in off if e == "RAIL_BUILD"
                         and f.get("cargo") == cargo and f.get("src") in sources]
            def annotated(entries):
                return [{"day": str(d), "src": f["src"], "dst": f["dst"],
                         "pred_profit": int(f["pred_profit"]), "cost": int(f["cost"])}
                        for d, f in entries]
            new = annotated(new_lines)
            old = annotated(old_lines)
            rows.append({
                "seed": seed, "event_date": str(day), "cargo": cargo,
                "on_build_count": len(new), "on_builds": new,
                "reference_same_source_count": len(old), "reference_builds": old,
                "on_predicted_profit_sum": sum(x["pred_profit"] for x in new),
                "reference_same_source_predicted_sum": sum(x["pred_profit"] for x in old),
                "nominal_predicted_difference":
                    sum(x["pred_profit"] for x in new)-sum(x["pred_profit"] for x in old)
            })
    return {"campaign": campaign, "year": 1972, "window_days": days,
            "method": "ON same cargo physical rail builds within N days after each N75 eligible refill; subtract any same cargo+source reference builds in 1972 even at other dates; predictive accounting proxy only",
            "rows": rows,
            "summary": {"event_count": len(rows),
                        "window_on_builds": sum(r["on_build_count"] for r in rows),
                        "reference_same_source_builds": sum(r["reference_same_source_count"] for r in rows),
                        "nominal_predicted_difference_total":
                            sum(r["nominal_predicted_difference"] for r in rows),
                        "nominal_predicted_difference_mean_over_5_seeds":
                            sum(r["nominal_predicted_difference"] for r in rows)/5}}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("campaign")
    p.add_argument("--days", type=int, default=45)
    a = p.parse_args()
    print(json.dumps(run(a.campaign, a.days), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
