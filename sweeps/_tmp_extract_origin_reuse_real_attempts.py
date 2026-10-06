#!/usr/bin/env python3
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "results" / "rail_origin_reuse_costcal_20x5_20261005.jsonl"
ATTEMPT = re.compile(r"OPEX (\d{4}-\d+-\d+) RAIL_ATTEMPT\s+(.*)$")
BUILD = re.compile(r"OPEX (\d{4}-\d+-\d+) RAIL_BUILD\s+(.*)$")


def fields(rest):
    out = {}
    for token in rest.split():
        if "=" in token:
            k, v = token.split("=", 1)
            out[k] = v
    return out


seen = set()
rows = []
terminal_marker = "1974-12-01"
raw_reuse_lines = 0

with P.open(encoding="utf-8") as fh:
    for line in fh:
        if "reuse=1" in line:
            raw_reuse_lines += 1
            if raw_reuse_lines <= 3:
                pos = line.find("reuse=1")
                print("RAW_REUSE_SAMPLE", line[max(0, pos - 300):pos + 500])
        # The raw line can be many MB because openttd_output is embedded.  Avoid
        # JSON parsing for every monthly checkpoint.
        if terminal_marker not in line:
            continue
        obj = json.loads(line)
        run = obj.get("run") or []
        if not run or not str(run[0]).startswith("OpexAI["):
            continue
        seed = int(run[1])
        arm = str(run[0])
        if "rail_origin_reuse=0" in arm:
            continue
        for raw in str(obj.get("openttd_output") or "").splitlines():
            m = ATTEMPT.search(raw)
            if not m:
                continue
            date, rest = m.groups()
            f = fields(rest)
            if f.get("reuse") != "1":
                continue
            key = (seed, date, f.get("src"), f.get("dst"), f.get("cargo"), f.get("kind"))
            if key in seen:
                continue
            seen.add(key)
            rows.append({
                "seed": seed,
                "date": date,
                "kind": f.get("kind"),
                "cargo": f.get("cargo"),
                "src": f.get("src"),
                "dst": f.get("dst"),
                "join_end": f.get("join_end"),
                "ok": f.get("ok"),
                "reason": f.get("reason"),
                "pred_profit": f.get("pred_profit"),
                "pred_roi": f.get("pred_roi"),
                "pred_astar": f.get("pred_astar"),
                "iters": f.get("iters"),
                "ops": f.get("ops"),
                "actual": f.get("actual"),
            })

rows.sort(key=lambda r: (r["seed"], r["date"], r["kind"] or ""))
for r in rows:
    print(r)
print("TOTAL", len(rows))
print("RAW_LINES_WITH_REUSE1", raw_reuse_lines)
print("BY_KIND", {
    k: sum(r["kind"] == k for r in rows)
    for k in sorted({r["kind"] for r in rows})
})
print("OK_BY_KIND", {
    k: sum(r["kind"] == k and r["ok"] == "1" for r in rows)
    for k in sorted({r["kind"] for r in rows})
})
