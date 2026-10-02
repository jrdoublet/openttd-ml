#!/usr/bin/env python3
"""Locate the first semantic log divergence across identical seed5678 repeats."""

from pathlib import Path
import re


ROOT = Path("results/c121_first_live_variance_seed5678_6y_20261001_r1_engine")
PREFIX = "c121_first_live_growth_bal90_fallback_seed5678_r"
STAMP = re.compile(r"^\[[0-9-]+ [0-9:]+\] ")


def semantic_lines(path):
    return [STAMP.sub("", line.rstrip("\n")) for line in path.open(encoding="utf-8", errors="replace")]


base = semantic_lines(ROOT / f"{PREFIX}0.log")
for repeat in range(1, 6):
    other = semantic_lines(ROOT / f"{PREFIX}{repeat}.log")
    limit = min(len(base), len(other))
    first = next((i for i in range(limit) if base[i] != other[i]), None)
    if first is None and len(base) == len(other):
        print("r0 vs r%d: identical semantic log" % repeat)
        continue
    if first is None:
        print("r0 vs r%d: common prefix %d, lengths %d/%d" % (repeat, limit, len(base), len(other)))
        continue
    lo = max(0, first - 2)
    hi = min(limit, first + 3)
    print("r0 vs r%d: first divergence line %d" % (repeat, first + 1))
    for i in range(lo, hi):
        mark = ">" if i == first else " "
        print(mark, "r0", i + 1, base[i])
        print(mark, "r%d" % repeat, i + 1, other[i])
