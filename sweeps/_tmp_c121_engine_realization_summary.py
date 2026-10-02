#!/usr/bin/env python3
import re
import statistics
from collections import defaultdict

path = "results/c121_engine_realization_seed42_4y_r2_20260929_engine/c121_engine_shadow_seed42_r0.log"
pat = re.compile(r"C121_ENGINE_REALIZATION .*?year=(\d+) engine=(\d+) arm=(\w+).*?ratio_pm=(-?\d+)")
rows = []
with open(path, encoding="utf-8", errors="replace") as f:
    for line in f:
        m = pat.search(line)
        if m:
            rows.append((int(m.group(1)), int(m.group(2)), m.group(3), int(m.group(4))))

def show(label, vals):
    vals = list(vals)
    if not vals:
        return
    print(label, "n", len(vals), "mean_pm", round(statistics.mean(vals), 1),
          "median_pm", statistics.median(vals), "min", min(vals), "max", max(vals))

show("all", [r[3] for r in rows])
by_engine = defaultdict(list)
by_arm = defaultdict(list)
by_year = defaultdict(list)
for year, engine, arm, ratio in rows:
    by_engine[engine].append(ratio)
    by_arm[arm].append(ratio)
    by_year[year].append(ratio)
for k in sorted(by_engine): show("engine=" + str(k), by_engine[k])
for k in sorted(by_arm): show("arm=" + k, by_arm[k])
for k in sorted(by_year): show("year=" + str(k), by_year[k])
