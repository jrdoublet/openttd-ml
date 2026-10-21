#!/usr/bin/env python3
"""V307 1.10: count destination stations receiving additional RAIL_BUILD lines.

The decision log has no station ID. A new non-shared destination build starts a
new station episode; only shared_dest=1 / join_end=B attaches to an existing one.
This prevents conflating two different stations serving the same industry tile.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import gzip
from pathlib import Path
import re
from statistics import median


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOGS = ROOT / "results/calibration_pc_20261021/results/calib_duel_40x10_pc_20261021_engine"
SEED_RE = re.compile(r"(?:reference|variant)_seed(\d+)_r\d+\.log(?:\.gz)?$")
BUILD_RE = re.compile(r"\bOPEX\s+(\d{4}-\d{1,2}-\d{1,2})\s+RAIL_BUILD\s+(.*)$")
ATTEMPT_RE = re.compile(r"\bOPEX\s+\d{4}-\d{1,2}-\d{1,2}\s+RAIL_ATTEMPT\s+(.*)$")
FIELDS_RE = re.compile(r"([a-zA-Z][a-zA-Z_0-9]*)=([^\s]+)")

# Cargos de base OpenTTD, categorie de DESTINATION (pas de production).
# Une ville apparaissant comme destination pax n'est pas necessairement son terminus.
CARGO_DEST = {
    "PASS": "Ville (voyageurs)", "MAIL": "Ville (courrier)",
    "GOOD": "Ville (marchandises)", "FOOD": "Ville (nourriture)",
    "COAL": "Centrale electrique", "IORE": "Acierie", "WOOD": "Scierie",
    "OIL_": "Raffinerie", "GRAI": "Usine", "LVST": "Usine",
    "STEL": "Usine", "VALU": "Banque", "DIAM": "Banque",
    "WATR": "Chateau d'eau",
}


def open_log(path: Path):
    return gzip.open(path, "rt", encoding="utf-8", errors="replace") if path.suffix == ".gz" else path.open(
        "rt", encoding="utf-8", errors="replace"
    )


def parse_lines(paths):
    """Return successful builds and telemetry counts; deduplicate repeated log lines."""
    builds, attempted, successes = [], 0, 0
    files = 0
    seen = set()
    for path in paths:
        m = SEED_RE.search(path.name)
        if m is None:
            continue
        files += 1
        seed = int(m.group(1))
        arm = path.name.split("_seed", 1)[0]
        with open_log(path) as stream:
            for line in stream:
                attempt = ATTEMPT_RE.search(line)
                if attempt:
                    fields = dict(FIELDS_RE.findall(attempt.group(1)))
                    attempted += 1
                    successes += fields.get("ok") == "1"
                hit = BUILD_RE.search(line)
                if not hit:
                    continue
                kv = dict(FIELDS_RE.findall(hit.group(2)))
                if not all(k in kv for k in ("line", "src", "dst", "cargo")):
                    raise ValueError(f"Champs RAIL_BUILD manquants: {path}: {line.strip()}")
                key = (arm, seed, int(kv["line"]))
                if key in seen:
                    continue
                seen.add(key)
                join = kv.get("join_end", "-")
                shared = kv.get("shared_dest", "0") == "1"
                if shared and join != "B":
                    raise ValueError(f"Jointure B incoherente: {path}: {line.strip()}")
                builds.append({
                    "arm": arm, "seed": seed, "line": int(kv["line"]),
                    "day": date(*map(int, hit.group(1).split("-"))), "src": int(kv["src"]),
                    "dst": int(kv["dst"]), "cargo": kv["cargo"],
                    "join_end": join, "shared_dest": shared,
                })
    if files == 0:
        raise ValueError("Aucun journal .log/.log.gz identifiable par son nom de graine")
    if not builds or attempted == 0:
        raise ValueError("RAIL_BUILD/RAIL_ATTEMPT absents : impossible de classer les puits")
    return builds, {"files": files, "attempts": attempted, "attempt_ok": successes, "builds": len(builds)}


def sinks_for_builds(builds):
    """Reconstruct destination station episodes, not merely distinct destination tiles.

    Without the station ID, an incoming shared build is assigned to the most
    recently created station for that destination. Ambiguities are disclosed.
    """
    sinks = []
    active = {}
    orphan_joins = 0
    duplicate_destinations = 0
    for b in sorted(builds, key=lambda x: (x["arm"], x["seed"], x["day"], x["line"])):
        key = (b["arm"], b["seed"], b["dst"])
        if b["shared_dest"] and key in active:
            sink = active[key]
        else:
            if b["shared_dest"]:
                orphan_joins += 1
            if key in active and not b["shared_dest"]:
                duplicate_destinations += 1
            sink = {"arm": b["arm"], "seed": b["seed"], "dst": b["dst"],
                    "lines": [], "cargos": set()}
            sinks.append(sink)
            active[key] = sink
        sink["lines"].append(b)
        sink["cargos"].add(b["cargo"])
    for sink in sinks:
        labels = {CARGO_DEST.get(c, "Cargo inconnu: " + c) for c in sink["cargos"]}
        sink["category"] = next(iter(labels)) if len(labels) == 1 else "Mixte: " + ", ".join(sorted(labels))
    return sinks, {"orphan_shared_joins": orphan_joins, "same_destination_new_stations": duplicate_destinations}


def summarize(sinks):
    rows = []
    by_cat = defaultdict(list)
    by_cat["TOTAL"] = list(sinks)
    for sink in sinks:
        by_cat[sink["category"]].append(sink)
    for cat, group in sorted(by_cat.items(), key=lambda x: (x[0] != "TOTAL", x[0])):
        counts = Counter(min(len(s["lines"]), 4) for s in group)
        delays = [(s["lines"][1]["day"] - s["lines"][0]["day"]).days
                  for s in group if len(s["lines"]) > 1]
        n = len(group)
        rows.append({"category": cat, "sinks": n, "one": counts[1], "two": counts[2],
                     "three": counts[3], "four_plus": counts[4],
                     "pct_one": 100 * counts[1] / n if n else 0,
                     "pct_two": 100 * counts[2] / n if n else 0,
                     "pct_three": 100 * counts[3] / n if n else 0,
                     "pct_four_plus": 100 * counts[4] / n if n else 0,
                     "median_second_days": median(delays) if delays else None})
    return rows


def markdown(rows):
    print("| Categorie de puits | Puits | 1 ligne | 2 lignes | 3 lignes | >=4 lignes | Delai median 1->2 (j) |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        delay = "—" if r["median_second_days"] is None else f'{r["median_second_days"]:g}'
        print(f'| {r["category"]} | {r["sinks"]} | {r["pct_one"]:.1f}% ({r["one"]}) | '
              f'{r["pct_two"]:.1f}% ({r["two"]}) | {r["pct_three"]:.1f}% ({r["three"]}) | '
              f'{r["pct_four_plus"]:.1f}% ({r["four_plus"]}) | {delay} |')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs", type=Path, default=DEFAULT_LOGS)
    parser.add_argument("--per-seed", action="store_true", help="Also print station counts for each seed")
    args = parser.parse_args()
    files = sorted(p for p in args.logs.iterdir() if p.name.endswith((".log", ".log.gz")))
    builds, metrics = parse_lines(files)
    sinks, issues = sinks_for_builds(builds)
    print(f"# Fichiers et evenements: {metrics}; reconstruction: {issues}")
    print(f"# Graines: {len(set((b['arm'], b['seed']) for b in builds))}")
    markdown(summarize(sinks))
    if args.per_seed:
        print("\n| Bras | Graine | Puits | 1 ligne | 2 lignes | 3 lignes | >=4 lignes |")
        print("|---|---:|---:|---:|---:|---:|---:|")
        for arm, seed in sorted(set((s["arm"], s["seed"]) for s in sinks)):
            subs = [s for s in sinks if (s["arm"], s["seed"]) == (arm, seed)]
            counts = Counter(min(len(s["lines"]), 4) for s in subs)
            print(f"| {arm} | {seed} | {len(subs)} | {counts[1]} | {counts[2]} | {counts[3]} | {counts[4]} |")


if __name__ == "__main__":
    main()
