#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


path = Path(sys.argv[1])
rows = {}
with path.open(encoding="utf-8") as fh:
    for raw in fh:
        row = json.loads(raw)
        run = row.get("run") or []
        if not run:
            continue
        key = run[0]
        if key not in rows or str(row.get("date", "")) >= str(rows[key].get("date", "")):
            rows[key] = row

event_re = re.compile(r"OPEX (\d{4}-\d+-\d+) ([A-Z0-9_]+)\s*(.*)$")
interesting = {
    "RAIL_ORIGIN_REUSE_FALLBACK",
    "RAIL_ORIGIN_REUSE_FINALIZE",
    "FREIGHT_CARGO_FALLBACK",
    "PROJECT_CHOSEN",
    "RAIL_ATTEMPT",
    "RAIL_BUILD",
}

def events(row):
    out = []
    for line in (row.get("openttd_output") or "").splitlines():
        m = event_re.search(line)
        if not m:
            continue
        date, kind, rest = m.groups()
        if kind not in interesting:
            continue
        if kind == "PROJECT_CHOSEN" and "mode=rail" not in rest and "mode=air" not in rest:
            continue
        out.append((date, kind, rest))
    return out

keys = list(rows)
for key in keys:
    ev = events(rows[key])
    print("\nARM", key, "final", rows[key].get("date"))
    for item in ev[:120]:
        print(*item)

if len(keys) == 2:
    a = [e for e in events(rows[keys[0]]) if e[1] == "PROJECT_CHOSEN"]
    b = [e for e in events(rows[keys[1]]) if e[1] == "PROJECT_CHOSEN"]
    n = min(len(a), len(b))
    first = None
    for i in range(n):
        sig_a = re.sub(r"rank=\d+ ", "", a[i][2])
        sig_b = re.sub(r"rank=\d+ ", "", b[i][2])
        if sig_a != sig_b:
            first = (i, a[i], b[i])
            break
    if first is None and len(a) != len(b):
        first = (n, a[n] if n < len(a) else None, b[n] if n < len(b) else None)
    print("\nFIRST_PROJECT_DIVERGENCE", first)
