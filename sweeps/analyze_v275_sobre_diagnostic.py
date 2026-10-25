"""Read-only V275 paired decision-log diagnostic (never an adoption gate)."""

from collections import Counter
import json
from pathlib import Path
import re
import sys


EVENT_RE = re.compile(r"\bOPEX\s+(\d{4}-\d+-\d+)\s+([A-Z][A-Z0-9_]+)\s+(.*)$")
SEED_RE = re.compile(r"seed(\d+)_r0\.log$")
EVENTS = (
    "PROJECT_CHOSEN", "AIR_BUILD", "RAIL_ATTEMPT", "RAIL_BUILD",
    "RAIL_BUILD_FAIL", "VIVIER_GEN", "VIVIER_REJECT", "AIR_PLAN_INPUT",
)


def read_events(path):
    events = []
    for line in path.open(encoding="utf-8", errors="replace"):
        match = EVENT_RE.search(line)
        if match is None:
            continue
        date, kind, raw = match.groups()
        if kind not in EVENTS:
            continue
        fields = dict(item.split("=", 1) for item in raw.split(" ") if "=" in item)
        events.append({"date": date, "kind": kind, "fields": fields, "raw": raw})
    return events


def main():
    campaign = sys.argv[1] if len(sys.argv) > 1 else "v275_sobre_diag_4x3_log_20261020_b"
    root = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else Path(__file__).resolve().parents[1]
    engine = root / "results" / (campaign + "_engine")
    files = sorted(engine.glob("*.log"))
    by_seed = {}
    for path in files:
        match = SEED_RE.search(path.name)
        if match is None:
            continue
        seed = int(match.group(1))
        arm = "OFF" if path.name.startswith("reference_") else "ON"
        by_seed.setdefault(seed, {})[arm] = read_events(path)

    result = json.loads((root / "results" / (campaign + ".json")).read_text(encoding="utf-8"))
    comparison = result.get("policy_comparison", {})
    print("RESULT", json.dumps({"campaign": campaign, "keys": list(result),
                                "comparison_keys": list(comparison),
                                "verdict": comparison.get("verdict"),
                                "pairs": comparison.get("comparison_complete")}, ensure_ascii=False))
    for seed in sorted(by_seed):
        arms = by_seed[seed]
        if len(arms) != 2:
            continue
        print("SEED", seed)
        for arm in ("OFF", "ON"):
            ev = arms[arm]
            chosen = [e for e in ev if e["kind"] == "PROJECT_CHOSEN"]
            pax_attempt = [e for e in ev if e["kind"] == "RAIL_ATTEMPT" and e["fields"].get("kind") == "pax"]
            pax_build = [e for e in ev if e["kind"] == "RAIL_BUILD" and e["fields"].get("cargo") == "PASS"]
            rail_build = [e for e in ev if e["kind"] == "RAIL_BUILD"]
            air_build = [e for e in ev if e["kind"] == "AIR_BUILD"]
            by_year = {year: {"air": sum(e["date"].startswith(year) for e in air_build),
                              "rail": sum(e["date"].startswith(year) for e in rail_build),
                              "pax_attempt": sum(e["date"].startswith(year) for e in pax_attempt)}
                       for year in ("1970", "1971", "1972")}
            print(" ", arm, "events", dict(Counter(e["kind"] for e in ev)),
                  "chosen", len(chosen), "pax_attempt", len(pax_attempt),
                  "pax_success", sum(e["fields"].get("ok") == "1" for e in pax_attempt),
                  "pax_build", len(pax_build), "years", by_year)
            print("   pax_attempt_detail", [f'{e["date"]} {e["fields"].get("src")}->{e["fields"].get("dst")} ok={e["fields"].get("ok")} reason={e["fields"].get("reason")}' for e in pax_attempt[:15]])
        a = [e for e in arms["OFF"] if e["kind"] == "PROJECT_CHOSEN"]
        b = [e for e in arms["ON"] if e["kind"] == "PROJECT_CHOSEN"]
        first = next((i for i in range(min(len(a), len(b))) if a[i]["date"] != b[i]["date"] or a[i]["raw"] != b[i]["raw"]), None)
        if first is not None:
            print(" first_project_divergence index", first,
                  "OFF", a[first]["date"], a[first]["raw"],
                  "ON", b[first]["date"], b[first]["raw"])
        else:
            print(" first_project_divergence", "none at common prefix", len(a), len(b))
    for pair in comparison.get("per_pair", []):
        met = pair.get("metrics", {})
        struct = pair.get("air_structural_metrics", {})
        annual = [(row.get("year"), row.get("policy_delta")) for row in pair.get("annual_trajectory", [])]
        print("ECON", pair.get("seed"), "complete", pair.get("complete"),
              "profit_delta", met.get("profit_year", {}).get("policy_delta"),
              "planes_primary_vehicles_delta", met.get("primary_vehicles", {}).get("policy_delta"),
              "airport_delta", struct.get("airport_slots_opex", {}).get("policy_delta"),
              "yearly", annual)


if __name__ == "__main__":
    main()
