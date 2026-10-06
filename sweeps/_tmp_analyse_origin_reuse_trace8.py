#!/usr/bin/env python3
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEM = sys.argv[1] if len(sys.argv) > 1 else "rail_origin_reuse_mechanism_trace_8x5_20261005"
VAR = sys.argv[2] if len(sys.argv) > 2 else "origin_reuse_freight_onepass_trace"
ENG = ROOT / "results" / f"{STEM}_engine"
SEEDS = (17, 100, 12345, 4096, 65537, 54321, 512, 1024)
EVENT = re.compile(r"OPEX (\d{4}-\d+-\d+) ([A-Z0-9_]+)\s*(.*)$")


def fields(rest):
    return dict(t.split("=", 1) for t in rest.split() if "=" in t)


def events(path):
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = EVENT.search(line)
        if m:
            out.append(m.groups())
    return out


def chosen(ev):
    return [e for e in ev if e[1] == "PROJECT_CHOSEN"]


def sig(e):
    f = fields(e[2])
    return tuple(f.get(k) for k in ("mode", "kind", "cargo", "src", "dst"))


for seed in SEEDS:
    ref = events(ENG / f"reference_seed{seed}_r0.log")
    var = events(ENG / f"{VAR}_seed{seed}_r0.log")
    rc, vc = chosen(ref), chosen(var)
    div = None
    for i in range(min(len(rc), len(vc))):
        if sig(rc[i]) != sig(vc[i]):
            div = (i, rc[i], vc[i])
            break
    if div is None and len(rc) != len(vc):
        i = min(len(rc), len(vc))
        div = (i, rc[i] if i < len(rc) else None, vc[i] if i < len(vc) else None)

    reuse_events = [e for e in var if e[1].startswith("RAIL_ORIGIN_REUSE")]
    attempts = [e for e in var if e[1] == "RAIL_ATTEMPT" and fields(e[2]).get("reuse") == "1"]
    builds = [e for e in var if e[1] == "RAIL_BUILD" and fields(e[2]).get("reuse") == "1"]
    active = []
    for e in reuse_events:
        f = fields(e[2])
        if any(f.get(k) not in (None, "0") for k in ("queued", "reuse_total", "admitted")):
            active.append(e)

    print(f"SEED {seed}")
    print(" first_project_divergence", div)
    print(" reuse_events", len(reuse_events), "active", len(active), "first_active", active[0] if active else None)
    print(" reuse_attempts", len(attempts))
    for e in attempts:
        print("  ATTEMPT", e)
    print(" reuse_builds", len(builds))
    for e in builds:
        print("  BUILD", e)
    if active:
        print(" active_events")
        for e in active[:12]:
            print("  ", e)
    print()
