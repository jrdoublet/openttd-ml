#!/usr/bin/env python3
"""Regroupe les lignes FRONT_PAX2 des logs OpenTTD, sans nouveau scan en jeu.

Usage:
  python -X utf8 sweeps/analyse_front_pax2.py results/campagne/*.log \
      --strict --out-json results/front_pax2.json --out-md results/front_pax2.md

Une occurrence représente une visite de couple dans une combinaison moteur/site,
pas une paire unique, un chantier constructible ni un candidat bénéficiaire.
"""

import argparse
from collections import defaultdict
import glob
import json
from pathlib import Path
import re


BINS = ("20-63", "64-77", "78-199", "200+")
ARMS = ("newpair", "hubsite", "hubhub")
FIELDS = (
    "seen", "short", "below_min", "blocked_min", "below_airmax",
    "below_plane", "below_config", "below_within", "other_band",
    "airmax", "band_pass",
)
PARTITION = ("short", "blocked_min", "other_band", "airmax", "band_pass")
TAG = re.compile(r"\bFRONT_PAX2\s+(.*)$")
START = re.compile(r"\bAIR_PLAN_INPUT\s+scan=(\d+)")
OPEX_YEAR = re.compile(r"\bOPEX\s+(\d{4})-")
KV = re.compile(r"([a-z_][a-z0-9_]*)=([^\s]+)")


def parse_line(line, path, lineno):
    match = TAG.search(line)
    if not match:
        return None
    values = dict(KV.findall(match.group(1)))
    required = ("scan", "year", "arm", "pax_band", "air_min", "air_max", "under20") + FIELDS
    absent = [key for key in required if key not in values]
    if absent:
        raise ValueError(f"{path}:{lineno}: champs manquants: {','.join(absent)}")
    emission = OPEX_YEAR.search(line)
    if not emission:
        raise ValueError(f"{path}:{lineno}: FRONT_PAX2 sans annee d'emission OPEX")
    record = {"file": str(path), "line": lineno,
              "scan_year": int(values["year"]), "emitted_year": int(emission.group(1))}
    for key in ("scan", "pax_band", "air_min", "air_max", "under20"):
        record[key] = int(values[key])
    record["arm"] = values["arm"]
    if record["arm"] not in ARMS:
        raise ValueError(f"{path}:{lineno}: bras inconnu {record['arm']!r}")
    for key in FIELDS:
        bins = tuple(int(x) for x in values[key].split(","))
        if len(bins) != 4 or any(x < 0 for x in bins):
            raise ValueError(f"{path}:{lineno}: {key} doit contenir quatre entiers >= 0")
        record[key] = bins
    if record["under20"] < 0:
        raise ValueError(f"{path}:{lineno}: under20 negatif")
    for i in range(4):
        if record["seen"][i] != sum(record[k][i] for k in PARTITION):
            raise ValueError(f"{path}:{lineno}: seen non partitionne, tranche {BINS[i]}")
        if record["below_min"][i] < record["blocked_min"][i]:
            raise ValueError(f"{path}:{lineno}: blocked_min > below_min")
        for key in ("below_airmax", "below_plane", "below_config", "below_within"):
            if record[key][i] > record["below_min"][i]:
                raise ValueError(f"{path}:{lineno}: {key} > below_min")
        if record["below_min"][i] > record["seen"][i] - record["short"][i]:
            raise ValueError(f"{path}:{lineno}: below_min > seen - short")
    return record


def aggregate(rows):
    result = {"arm_records": len(rows), "under20": 0}
    for key in FIELDS:
        result[key] = [0, 0, 0, 0]
    for row in rows:
        result["under20"] += row["under20"]
        for key in FIELDS:
            for i in range(4):
                result[key][i] += row[key][i]
    return result


def analyze(paths):
    rows, problems, starts = [], [], {}
    for path in paths:
        try:
            with open(path, encoding="utf-8", errors="replace") as file:
                for lineno, line in enumerate(file, 1):
                    start = START.search(line)
                    if start:
                        year_match = OPEX_YEAR.search(line)
                        if year_match:
                            key = (str(path), int(start.group(1)))
                            if key in starts:
                                problems.append(f"{path}:{lineno}: AIR_PLAN_INPUT scan={key[1]} duplique")
                            starts[key] = int(year_match.group(1))
                        else:
                            problems.append(f"{path}:{lineno}: AIR_PLAN_INPUT sans annee OPEX")
                    try:
                        row = parse_line(line, path, lineno)
                        if row is not None:
                            rows.append(row)
                    except (ValueError, TypeError) as error:
                        problems.append(str(error))
        except OSError as error:
            problems.append(f"{path}: {error}")

    scans = defaultdict(list)
    for row in rows:
        scans[(row["file"], row["scan"])].append(row)
    complete_keys = set()
    for (path, scan), group in scans.items():
        names = [record["arm"] for record in group]
        if sorted(names) != sorted(ARMS):
            problems.append(f"{path}: scan={scan}: attendu 3 bras, recu {names}")
        elif all(len({record[key] for record in group}) == 1
                 for key in ("scan_year", "emitted_year", "pax_band", "air_min", "air_max")):
            complete_keys.add((path, scan))
        for key in ("scan_year", "emitted_year", "pax_band", "air_min", "air_max"):
            if len({record[key] for record in group}) != 1:
                problems.append(f"{path}: scan={scan}: {key} incoherent entre bras")

    # Un AIR_PLAN_INPUT sans FRONT_PAX2 indique un scan censure (yield/abandon),
    # pas une erreur et surtout pas trois lignes de compteurs a zero.
    for key in complete_keys:
        if key not in starts:
            problems.append(f"{key[0]}: scan={key[1]}: FRONT_PAX2 sans AIR_PLAN_INPUT dans ce log")

    # Refuser toute valeur agrégée issue d'un scan partiel ou incohérent.
    rows = [row for row in rows if (row["file"], row["scan"]) in complete_keys]
    coverage = []
    file_years = {(path, year) for (path, _), year in starts.items()}
    file_years.update((row["file"], row["scan_year"]) for row in rows
                      if (row["file"], row["scan"]) not in starts)
    for path, year in sorted(file_years):
        scan_keys = {key for key, y in starts.items() if key[0] == path and y == year}
        completed = scan_keys & complete_keys
        orphan_completed = {key for key in complete_keys - set(starts)
                            if key[0] == path and scans[key][0]["scan_year"] == year}
        group = aggregate([row for row in rows if (row["file"], row["scan"])
                           in (completed | orphan_completed)])
        coverage.append({"file": path, "year": year, "started": len(scan_keys),
                         "completed": len(completed), "censored": len(scan_keys - completed),
                         "completed_without_start": len(orphan_completed),
                         "below_min": group["below_min"],
                         "blocked_min": group["blocked_min"],
                         "below_within": group["below_within"]})

    by_arm, by_scan_year, by_emitted_year, by_band, by_scan_year_arm_band = {}, {}, {}, {}, {}
    for arm in ARMS:
        by_arm[arm] = aggregate([row for row in rows if row["arm"] == arm])
    for year in sorted({r["scan_year"] for r in rows}):
        by_scan_year[str(year)] = aggregate([r for r in rows if r["scan_year"] == year])
    for year in sorted({r["emitted_year"] for r in rows}):
        by_emitted_year[str(year)] = aggregate([r for r in rows if r["emitted_year"] == year])
    for band in sorted({r["pax_band"] for r in rows}):
        by_band[str(band)] = aggregate([r for r in rows if r["pax_band"] == band])
    for year in sorted({r["scan_year"] for r in rows}):
        by_scan_year_arm_band[str(year)] = {}
        for band in sorted({r["pax_band"] for r in rows if r["scan_year"] == year}):
            by_scan_year_arm_band[str(year)][str(band)] = {
                arm: aggregate([r for r in rows if r["scan_year"] == year
                                and r["pax_band"] == band and r["arm"] == arm])
                for arm in ARMS
            }

    return {"bins": BINS, "log_files": list(map(str, paths)),
            "records": len(rows), "complete_scans": len(complete_keys),
            "started_scans": len(starts), "censored_scans": len(set(starts) - complete_keys),
            "coverage_by_file_year": coverage, "scans_with_fp2": len(scans),
            "problems": problems,
            "all": aggregate(rows), "by_arm": by_arm,
            "by_scan_year": by_scan_year, "by_emitted_year": by_emitted_year,
            "by_band": by_band,
            "by_scan_year_arm_band": by_scan_year_arm_band}


def render_md(report):
    out = ["# FRONT-PAX-2 — paires examinées",
           "", f"Logs : {len(report['log_files'])} ; lignes : {report['records']} ; "
           f"cycles complets : {report['complete_scans']}/{report['started_scans']} "
           f"(censurés : {report['censored_scans']}).",
           "", "Les colonnes sont des évaluations de couples, non des projets rentables.",
           "Le champ `below_min` est contrefactuel sous les bandes split ; "
           "`blocked_min` mesure les rejets réels par `airMin`.",
           "Les scans commencés sans bilan complet sont exclus de tous les totaux.",
           "", "## Couverture par log et année de début", "",
           "| Log | Année | Démarrés | Complets | Censurés | Sous 200 (20–63 / 64–77 / 78–199 / 200+) |",
           "| --- | ---: | ---: | ---: | ---: | --- |"]
    for coverage in report["coverage_by_file_year"]:
        out.append("| " + " | ".join(str(coverage[key]) for key in (
            "file", "year", "started", "completed", "censored"))
                   + " | " + "/".join(map(str, coverage["below_min"])) + " |")
    out.extend(["", "## Comptes complets par bras", "",
           "", "| Bras | Mesure | 20–63 | 64–77 | 78–199 | 200+ |",
           "| --- | --- | ---: | ---: | ---: | ---: |"]) 
    for arm in ARMS:
        group = report["by_arm"][arm]
        for field in ("seen", "short", "below_min", "blocked_min", "below_within",
                      "below_plane", "below_airmax", "below_config", "other_band", "band_pass"):
            out.append(f"| {arm} | {field} | " + " | ".join(map(str, group[field])) + " |")
    if report["problems"]:
        out.extend(["", "## Alertes", ""])
        out.extend(f"- {problem}" for problem in report["problems"])
    out.extend(["", "## Par année de début et bande", ""])
    for year, by_band in report["by_scan_year_arm_band"].items():
        for band, by_arm in by_band.items():
            for arm, group in by_arm.items():
                out.append(f"- année={year}, bande={band}, bras={arm} : "
                           f"below_min={group['below_min']} ; "
                           f"blocked_min={group['blocked_min']} ; "
                           f"below_within={group['below_within']}")
    out.extend(["", "## Provenance de l'année", "",
                "`scan_year` provient du `bounds.year` gelé au début du scan ; "
                "`emitted_year` vient de la date OPEX de fin. Un scan commencé "
                "une année peut finir la suivante."])
    for year, group in report["by_emitted_year"].items():
        out.append(f"- année d'émission={year} : below_min={group['below_min']}, "
                   f"blocked_min={group['blocked_min']}, "
                   f"below_within={group['below_within']}")
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs", nargs="+", type=Path, help="Logs OpenTTD déjà produits")
    parser.add_argument("--out-json", type=Path)
    parser.add_argument("--out-md", type=Path)
    parser.add_argument("--strict", action="store_true", help="Erreur si FP2 partiel/incoherent ou format invalide ; censure signalee sans echec")
    args = parser.parse_args()
    log_paths = []
    for arg in args.logs:
        text_path = str(arg)
        matched = glob.glob(text_path) if any(c in text_path for c in "*?[") else [text_path]
        if not matched:
            parser.error(f"aucun log pour le motif : {text_path}")
        log_paths.extend(Path(path) for path in sorted(matched))
    report = analyze(list(dict.fromkeys(log_paths)))
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out_json:
        args.out_json.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    if args.out_md:
        args.out_md.write_text(render_md(report), encoding="utf-8")
    if args.strict and report["problems"]:
        parser.exit(1, f"FRONT_PAX2 : {len(report['problems'])} anomalie(s)\n")


if __name__ == "__main__":
    main()
