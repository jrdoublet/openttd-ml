#!/usr/bin/env python3
from pathlib import Path
import re
import statistics


LOG = Path("results/c122_3_exposure_probe_seed42_1x3_20260929_r2_engine/c122_3_exposure_probe_seed42_r0.log")
EXPOSURE = re.compile(
    r"C122_EXPOSURE date=(\d+) air=(\d+) new=(\d+) potential_inversions=(\d+) "
    r"top_air_global_rank=(-?\d+) top_air_score=([^ ]+) best_new_global_rank=(-?\d+) "
    r"best_new_air_rank=(-?\d+) best_new_claims=(\d+) best_new_score=([^ ]+) "
    r"best_new_tier=(-?\d+) same_tier_blockers=(\d+)"
)
PRESSURE = re.compile(r"C121_PRESSURE year=(\d+)")


rows = []
pending = None
for line in LOG.read_text(encoding="utf-8", errors="replace").splitlines():
    match = EXPOSURE.search(line)
    if match:
        pending = {
            "date": int(match.group(1)),
            "air": int(match.group(2)),
            "new": int(match.group(3)),
            "inv": int(match.group(4)),
            "global_rank": int(match.group(7)),
            "air_rank": int(match.group(8)),
            "claims": int(match.group(9)),
            "tier": int(match.group(11)),
            "blockers": int(match.group(12)),
        }
        rows.append(pending)
        continue
    match = PRESSURE.search(line)
    if match and pending is not None and "year" not in pending:
        pending["year"] = int(match.group(1))
        pending = None

with_new = [row for row in rows if row["new"] > 0]
print("snapshots", len(rows))
print("with_new", len(with_new))
print("new_candidates_sum", sum(row["new"] for row in rows))
print("with_potential", sum(row["inv"] > 0 for row in rows))
print("potential_candidates_sum", sum(row["inv"] for row in rows))
if with_new:
    air_ranks = [row["air_rank"] for row in with_new]
    global_ranks = [row["global_rank"] for row in with_new]
    print("best_new_air_rank_min_med_max", min(air_ranks), statistics.median(air_ranks), max(air_ranks))
    print("best_new_global_rank_min_med_max", min(global_ranks), statistics.median(global_ranks), max(global_ranks))
    blockers = sorted({row["blockers"] for row in with_new})
    print("blockers_hist", {value: sum(row["blockers"] == value for row in with_new) for value in blockers})

years = sorted({row["year"] for row in rows if "year" in row})
for year in years:
    subset = [row for row in rows if row.get("year") == year]
    subset_new = [row for row in subset if row["new"] > 0]
    print(
        "year", year,
        "snapshots", len(subset),
        "with_new", len(subset_new),
        "new_sum", sum(row["new"] for row in subset),
        "with_potential", sum(row["inv"] > 0 for row in subset),
        "inv_sum", sum(row["inv"] for row in subset),
        "air_ranks", [row["air_rank"] for row in subset_new],
        "blockers", [row["blockers"] for row in subset_new],
    )
