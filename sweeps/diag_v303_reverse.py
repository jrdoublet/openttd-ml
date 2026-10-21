#!/usr/bin/env python3
"""V303 decision logs; reuse the current rail attempt decoder and distance bins."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import re
import statistics

from diag_railech_abnd import get_slice, parse_opex_attempt


def summary(rows, fields):
    out = {"n": len(rows)}
    for key in fields:
        values = [int(r[key]) for r in rows if key in r and int(r[key]) >= 0]
        out[key] = ({"n": len(values), "sum": sum(values),
                     "mean": statistics.mean(values), "median": statistics.median(values),
                     "max": max(values)} if values else None)
    return out


def analyse(directory):
    arms = defaultdict(lambda: {"probes": [], "searches": [], "attempts": [], "errors": 0})
    files = sorted(Path(directory).glob("*.log")) or sorted(Path(directory).glob("*.log.gz"))
    for path in files:
        arm = "reference" if path.name.startswith("reference_") else "variant"
        seed_match = re.search(r"seed(\d+)", path.name)
        seed = int(seed_match[1]) if seed_match else None
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8", errors="replace") as stream:
            for line in stream:
                if "[0]" not in line:
                    continue
                if "Your script made an error" in line:
                    arms[arm]["errors"] += 1
                if "[script:4]" not in line:
                    continue
                row = dict(re.findall(r"(\w+)=([^\s]+)", line))
                if "V294F_PROBE" in line:
                    arms[arm]["probes"].append(row)
                elif "V303_SEARCH" in line:
                    arms[arm]["searches"].append(row)
                elif "RAIL_ATTEMPT" in line:
                    attempt = parse_opex_attempt(line, arm, seed, path.name)
                    if attempt:
                        arms[arm]["attempts"].append(attempt)
    out = {"files": [str(p) for p in files], "arms": {}}
    for arm, rows in arms.items():
        probes = rows["probes"]
        attempts = rows["attempts"]
        report = {"errors": rows["errors"],
                  "probes": summary(probes, ("iters", "ticks", "max_ticks", "ops")),
                  "probe_found": sum(int(p["ok"]) for p in probes),
                  "searches": summary(rows["searches"], ("iters", "elapsed", "ticks", "max_ticks", "ops")),
                  "winners": dict(Counter(p["winner"] for p in rows["searches"])),
                  "attempts": len(attempts), "reasons": dict(Counter(p["reason"] for p in attempts)),
                  "distance": {}}
        for band in ("<60", "60-100", "100-160", ">=160"):
            a = [p for p in attempts if p["slice"] == band]
            p = [p for p in probes if get_slice(int(p["manh"])) == band]
            report["distance"][band] = {
                "attempts": len(a), "ok": sum(x["ok"] for x in a),
                "abnd": sum(x["reason"] == "ABND" for x in a),
                "probes": len(p), "probe_found": sum(int(x["ok"]) for x in p),
                "search_cost": summary(a, ("iters", "search_ops")),
            }
        out["arms"][arm] = report
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    args = parser.parse_args()
    print(json.dumps(analyse(args.directory), indent=2, ensure_ascii=False))
