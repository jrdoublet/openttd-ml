"""MULTI-1: reproduce annual modal diagnostics from existing C66 checkpoints.

No engine or simulator access. Never infer real construction CAPEX from vehicle
book value or project finance quotes. Default multi source is the OFF arm of
the 2026-10-26 P6 experiment (40 seeds x 5y), explicitly a different bundle.
"""
import collections
import json
import pathlib
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent / "results"
CAMPAIGNS = {
    "rail": ("modal_rail_defaults_master85c88_40x5_20261025", None),
    "air": ("modal_air_defaults_master85c88_40x5_20261025", None),
    "multi": ("p6_win_porteA_40x5_20261026", "reference"),
}
ARMS = ("OpexAI", "AAAHogEx")
MODES = ("rail", "road", "air", "water")
OPCODES = ("selection", "rail_attempt", "road_planning", "road_build", "air_planning", "water_planning")


def mean(values):
    data = [x for x in values if isinstance(x, (int, float))]
    return round(statistics.mean(data), 2) if data else None


def describe(prefix, selected_policy):
    path = ROOT / (prefix + ".json")
    metadata = json.loads(path.read_text(encoding="utf-8"))
    wanted = {(r["arm"], int(r["seed"])): r for r in metadata["summary"]
              if selected_policy is None or r.get("duel_policy_id") == selected_policy}
    if len(wanted) != len(metadata["seeds"]) * len(ARMS):
        raise ValueError(f"Nonunique or missing summaries in {prefix}: {len(wanted)}")
    december = {}
    first_air = {}
    first_rail = {}
    first_line = {}
    with (ROOT / (prefix + ".jsonl")).open(encoding="utf-8") as handle:
        for line in handle:
            r = json.loads(line)
            arm, seed, repeat = r["run"]
            if repeat != 0 or (arm, int(seed)) not in wanted:
                continue
            if selected_policy is not None and r.get("duel_policy_id") != selected_policy:
                continue
            date = r["date"]
            identity = (arm, int(seed))
            fleet = r.get("primary_vehicles_by_mode") or {}
            if fleet.get("air", 0) > 0:
                first_air.setdefault(identity, date)
            if fleet.get("rail", 0) > 0:
                first_rail.setdefault(identity, date)
            lt = r.get("line_telemetry") or {}
            if lt.get("ok") and lt.get("lines"):
                first_line.setdefault(identity, date)
            if date.endswith("-12-01"):
                key = (arm, int(seed), int(date[:4]))
                if key in december:
                    raise ValueError(f"Duplicate December snapshot: {prefix} {key}")
                december[key] = r
    if len(december) != len(wanted) * 5:
        raise ValueError(f"Incomplete December coverage {prefix}: {len(december)}/{len(wanted)*5}")
    output = {"campaign": prefix, "bundle": metadata["source_bundle_sha256"],
              "policy": selected_policy, "n_games": len(wanted) // 2,
              "failed_runs": len(metadata["failed_runs"]), "annual": {},
              "first_air_vehicle": {}, "first_rail_vehicle": {}, "first_active_line_any_mode": {}}
    for arm in ARMS:
        keys = [(a, s) for a, s in wanted if a == arm]
        output["first_air_vehicle"][arm] = dict(collections.Counter(first_air.get(k, "unknown") for k in keys))
        output["first_rail_vehicle"][arm] = dict(collections.Counter(first_rail.get(k, "unknown") for k in keys))
        output["first_active_line_any_mode"][arm] = dict(collections.Counter(first_line.get(k, "unknown") for k in keys))
        output["annual"][arm] = {}
        for year in range(1970, 1975):
            rows = [december[(arm, k[1], year)] for k in keys]
            by_mode = {mode: mean((r.get("primary_vehicles_by_mode") or {}).get(mode) for r in rows)
                       for mode in MODES}
            # Book value of live aircraft is available separately, not historical spend.
            # In monomodal campaigns line telemetry also reports live rail book value.
            book = {}
            for mode in ("air", "rail"):
                vals = []
                for r in rows:
                    if mode == "air":
                        vals.append(r.get("air_vehicle_book_value"))
                    else:
                        lt = r.get("line_telemetry") or {}
                        if lt.get("ok"):
                            vals.append(sum(float(l.get("vehicle_value") or 0)
                                            for l in lt.get("lines", []) if l.get("mode") == "rail"))
                book[mode] = mean(vals)
            sample = {mode: {"samples": mean((r.get("observed_opcode_components") or {}).get(mode, {}).get("samples") for r in rows),
                             "opcodes": mean((r.get("observed_opcode_components") or {}).get(mode, {}).get("opcodes") for r in rows)}
                      for mode in OPCODES} if arm == "OpexAI" else None
            output["annual"][arm][str(year)] = {
                "profit_year": mean(r.get("profit_year") for r in rows),
                "vehicles": by_mode, "air_vehicle_book_value": book["air"],
                "rail_live_line_vehicle_book_value": book["rail"],
                "cash": mean(r.get("money") for r in rows),
                "loan": mean(r.get("current_loan") for r in rows),
                "opcode_signs": sample,
            }
    return output


def main():
    report = {label: describe(*spec) for label, spec in CAMPAIGNS.items()}
    data = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if len(sys.argv) == 3 and sys.argv[1] == "--out":
        with pathlib.Path(sys.argv[2]).open("x", encoding="utf-8") as f:
            f.write(data)
    elif len(sys.argv) == 1:
        print(data, end="")
    else:
        raise SystemExit("Usage: analyse_multi1_existing.py [--out NEWFILE.json]")


if __name__ == "__main__":
    main()
