#!/usr/bin/env python3
"""AIR orphan -> hub : appariement observationnel des stations physiques.

Les coûts A reclassés comme « productifs » restent des dépenses historiques :
aucun remboursement, revenu ni gain économique n'est imputé. Les horizons
inconnus ne deviennent jamais la date du dernier message AILog.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Optional

from parse_air_finance_margin import (
    RE_KV, clean_log_line, parse_kv_payload, parse_log_filename,
)


TOKEN = re.compile(r"\b(AIR_ORPHAN_RETAIN|AIR_HUB_REUSE)\b\s*(.*)$")
INT = re.compile(r"\d+\Z")
REQUIRED = {
    "AIR_ORPHAN_RETAIN": ("date", "anchor", "station", "town", "pair",
                          "reason", "cost_a", "cost_b", "total"),
    "AIR_HUB_REUSE": ("date", "line", "anchor", "station", "side",
                      "prior_line_refs", "src_town", "dst_town",
                      "reuse_a", "reuse_b"),
}
NUMERIC = {"date", "anchor", "station", "town", "line", "cost_a", "cost_b",
           "total", "prior_line_refs", "src_town", "dst_town",
           "reuse_a", "reuse_b"}


def _warn(warnings: list[dict], code: str, detail: str, line: Optional[int] = None):
    warnings.append({"code": code, "line": line, "detail": detail})


def _event(kind: str, raw: str, position: int, warnings: list[dict]) -> Optional[dict]:
    keys = [match.group(1) for match in RE_KV.finditer(raw)]
    if len(keys) != len(set(keys)):
        _warn(warnings, "duplicate_field", kind, position)
        return None
    kv = parse_kv_payload(raw)
    missing = [key for key in REQUIRED[kind] if key not in kv or kv[key] == ""]
    if missing:
        _warn(warnings, "missing_fields", f"{kind}: {','.join(missing)}", position)
        return None
    bad = [key for key in NUMERIC & kv.keys() if not INT.fullmatch(kv[key])]
    if bad:
        _warn(warnings, "invalid_numeric", f"{kind}: {','.join(sorted(bad))}", position)
        return None
    for key in NUMERIC & kv.keys():
        kv[key] = int(kv[key])
    if kv["station"] < 0 or kv["anchor"] < 0:
        _warn(warnings, "invalid_station", kind, position)
        return None
    if kind == "AIR_ORPHAN_RETAIN":
        if kv["reason"] not in ("BFAIL", "HUBB") or not kv["pair"]:
            _warn(warnings, "invalid_origin", kind, position)
            return None
        if "reuse_a" in kv and kv["reuse_a"] != 0:
            _warn(warnings, "not_new_airport_a", kind, position)
            return None
        if "reuse_b" in kv and kv["reuse_b"] not in (0, 1):
            _warn(warnings, "invalid_reuse_flag", kind, position)
            return None
    else:
        side = kv["side"]
        if (side not in ("A", "B") or kv["reuse_a"] not in (0, 1)
                or kv["reuse_b"] not in (0, 1)
                or kv["reuse_a" if side == "A" else "reuse_b"] != 1):
            _warn(warnings, "inconsistent_reuse_side", kind, position)
            return None
    return {"kind": kind, "position": position, **kv}


def parse_stream(lines: Iterable[str], filename: str,
                 end_date: Optional[int] = None) -> dict[str, Any]:
    """Une partie = un log. Jamais de jointure entre répétitions ou fichiers."""
    meta = parse_log_filename(filename)
    warnings: list[dict] = []
    if not meta["arm"] or re.search(r"seed[_-]?\d+", Path(filename).stem, re.I) is None:
        _warn(warnings, "unknown_run_metadata", f"arm/seed: {filename}")
        return {"file": filename, "arm": meta["arm"], "seed": None,
                "repeat": meta["repeat"], "end_date": None,
                "end_date_source": None, "orphans": [], "unmatched_reuses": [],
                "warnings": warnings, "summary": _summary([], [], warnings)}

    origins: list[dict] = []
    reuses: list[dict] = []
    dates: list[int] = []
    for position, text in enumerate(lines, 1):
        m = TOKEN.search(clean_log_line(text))
        if not m:
            continue
        event = _event(m.group(1), m.group(2), position, warnings)
        if event is None:
            continue
        dates.append(event["date"])
        (origins if event["kind"] == "AIR_ORPHAN_RETAIN" else reuses).append(event)

    # Les replays Save/Load peuvent remonter la date : interdire une jointure
    # quand l'ordre chronologique global du fichier n'est plus fiable.
    backwards = any(right < left for left, right in zip(dates, dates[1:]))
    if backwards:
        _warn(warnings, "date_regression", "ordre des dates non monotone")

    by_station: dict[int, list[dict]] = defaultdict(list)
    for event in origins + reuses:
        by_station[event["station"]].append(event)

    origin_dupes = Counter((o["date"], o["anchor"], o["station"]) for o in origins)
    reuse_dupes = Counter((r["date"], r["line"], r["anchor"],
                           r["station"], r["side"]) for r in reuses)
    consumed: set[int] = set()
    records: list[dict] = []
    for origin in origins:
        station_events = by_station[origin["station"]]
        station_origins = [e for e in station_events
                           if e["kind"] == "AIR_ORPHAN_RETAIN"]
        station_reuses = [e for e in station_events
                          if e["kind"] == "AIR_HUB_REUSE"]
        matching = [r for r in station_reuses
                    if r["anchor"] == origin["anchor"]
                    and r["position"] > origin["position"]
                    and r["date"] >= origin["date"]]
        matching.sort(key=lambda r: (r["date"], r["position"]))
        first = matching[0] if matching else None

        # Un second événement ORPHAN sur la station, ou un usage enregistré
        # avec une autre ancre, peut indiquer un recyclage de StationID.
        changed_anchor = any(e["anchor"] != origin["anchor"] for e in station_events)
        prior_usage = any(r["position"] < origin["position"]
                          for r in station_reuses)
        duplicate_origin = origin_dupes[(origin["date"], origin["anchor"],
                                         origin["station"])] > 1
        duplicate_reuse = first is not None and reuse_dupes[(
            first["date"], first["line"], first["anchor"], first["station"],
            first["side"])] > 1
        same_first_line = first is not None and sum(
            1 for r in matching if r["date"] == first["date"]
            and r["line"] == first["line"]) > 1
        if backwards:
            status = "ambiguous_chronology"
        elif duplicate_origin or duplicate_reuse or same_first_line:
            status = "ambiguous_duplicate"
        elif len(station_origins) != 1 or changed_anchor or prior_usage:
            status = "ambiguous_station_recycled"
        elif first is None:
            status = "censored"
        elif first["prior_line_refs"] != 0:
            status = "prior_service_unverified"
        else:
            status = "first_use_confirmed"

        valid_match = status == "first_use_confirmed"
        if valid_match:
            # Le premier service est unique ; les services ultérieurs ne sont
            # pas des réemplois « non appariés » et ne récupèrent pas deux fois A.
            consumed.update(r["position"] for r in matching)
        horizon_known = (end_date is not None
                         and end_date >= origin["date"]
                         and (not dates or end_date >= max(dates)))
        if end_date is not None and not horizon_known:
            _warn(warnings, "invalid_end_date",
                  f"end={end_date} earlier than observed date",
                  origin["position"])
        delay = (first["date"] - origin["date"]) if valid_match else None
        censor_days = (end_date - origin["date"]
                       if status == "censored" and horizon_known else None)
        records.append({
            "date": origin["date"], "anchor": origin["anchor"],
            "station": origin["station"], "town": origin["town"],
            "pair": origin["pair"], "reason": origin["reason"],
            "cost_a_gbp": origin["cost_a"], "cost_b_gbp": origin["cost_b"],
            "total_build_cost_gbp": origin["total"],
            "status": status, "first_reuse_date": first["date"] if valid_match else None,
            "first_reuse_line": first["line"] if valid_match else None,
            "first_reuse_side": first["side"] if valid_match else None,
            "first_reuse_prior_line_refs": first["prior_line_refs"] if valid_match else None,
            "later_reuse_count": len(matching) - 1 if valid_match else 0,
            "delay_days": delay,
            "productive_cost_a_gbp": origin["cost_a"] if valid_match else None,
            "immobilization_gbp_days": origin["cost_a"] * delay if valid_match else None,
            "censor_end_date": end_date if censor_days is not None else None,
            "censored_days": censor_days,
            "censored_immobilization_gbp_days": (
                origin["cost_a"] * censor_days if censor_days is not None else None),
            "log_line": origin["position"],
        })
    unmatched = [
        {"date": r["date"], "anchor": r["anchor"], "station": r["station"],
         "line": r["line"], "side": r["side"], "log_line": r["position"]}
        for r in reuses if r["position"] not in consumed
    ]
    return {
        "file": filename, "arm": meta["arm"], "seed": meta["seed"],
        "repeat": meta["repeat"], "end_date": end_date
        if end_date is not None and not backwards and (not dates or end_date >= max(dates))
        else None,
        "end_date_source": ("explicit_cli" if end_date is not None
                            and not backwards and (not dates or end_date >= max(dates))
                            else None),
        "orphans": records, "unmatched_reuses": unmatched,
        "warnings": warnings, "summary": _summary(records, unmatched, warnings),
    }


def _summary(records: list[dict], unmatched: list[dict],
             warnings: list[dict]) -> dict:
    statuses = Counter(record["status"] for record in records)
    confirmed = [r for r in records if r["status"] == "first_use_confirmed"]
    censored_known = [r for r in records
                      if r["censored_immobilization_gbp_days"] is not None]
    return {
        "orphan_count": len(records),
        "status_counts": dict(sorted(statuses.items())),
        "first_use_confirmed": len(confirmed),
        "later_reuse_count": sum(r["later_reuse_count"] for r in confirmed),
        "unmatched_reuse_count": len(unmatched),
        "warning_counts": dict(sorted(Counter(w["code"] for w in warnings).items())),
        "retained_cost_a_gbp_all_events": sum(r["cost_a_gbp"] for r in records),
        "productive_cost_a_gbp_confirmed": sum(r["cost_a_gbp"] for r in confirmed),
        "delay_days_confirmed": [r["delay_days"] for r in confirmed],
        "immobilization_gbp_days_confirmed": sum(
            r["immobilization_gbp_days"] for r in confirmed),
        "censored_immobilization_gbp_days_known": sum(
            r["censored_immobilization_gbp_days"] for r in censored_known),
        "censored_duration_known_count": len(censored_known),
        "censored_duration_unknown_count": sum(
            r["status"] == "censored" and r["censored_days"] is None
            for r in records),
    }


def analyse_files(paths: Iterable[Path], end_date: Optional[int] = None) -> dict:
    runs = []
    seen: set[tuple] = set()
    for path in sorted(set(Path(p) for p in paths)):
        with path.open(encoding="utf-8", errors="replace") as stream:
            result = parse_stream(stream, str(path), end_date=end_date)
        key = (result["arm"], result["seed"], result["repeat"])
        if result["seed"] is not None and key in seen:
            _warn(result["warnings"], "duplicate_run",
                  f"arm/seed/repeat already present: {key}")
            # Ne pas relier des observations issues de copies d'un même bras.
            for run in runs:
                if (run["arm"], run["seed"], run["repeat"]) == key:
                    _warn(run["warnings"], "duplicate_run", f"ambiguous run: {key}")
                    run["summary"] = _summary([], [], run["warnings"])
                    run["orphans"] = []
                    run["unmatched_reuses"] = []
            result["orphans"] = []
            result["unmatched_reuses"] = []
            result["summary"] = _summary([], [], result["warnings"])
        seen.add(key)
        runs.append(result)
    all_records = [r for run in runs for r in run["orphans"]]
    all_unmatched = [r for run in runs for r in run["unmatched_reuses"]]
    all_warnings = [w for run in runs for w in run["warnings"]]
    grouped: dict[str, list[dict]] = defaultdict(list)
    for run in runs:
        grouped[run["arm"]].append(run)
    by_arm = {}
    for arm, members in sorted(grouped.items()):
        by_arm[arm] = _summary(
            [r for run in members for r in run["orphans"]],
            [r for run in members for r in run["unmatched_reuses"]],
            [w for run in members for w in run["warnings"]],
        )
    return {"runs": runs, "summary": _summary(all_records, all_unmatched, all_warnings),
            "by_arm": by_arm, "limitations": [
        "appairage seulement sur (bras,graine,répétition,ancre,station) au sein du même fichier",
        "prior_line_refs=0 et construction réussie requis pour premier service confirmé",
        "cost_a productif est une attribution de capital historique, jamais un remboursement",
        "date de fin inconnue sans --end-date explicitement vérifiée ; pas d'inférence du dernier log",
        "doublons, station recyclée, recul de date et champs incomplets exclus des confirmations",
        "recyclage physique sans événement observable et disparition d'aéroport restent inconnus",
    ]}


def _inputs(items: Iterable[str]) -> list[Path]:
    paths: set[Path] = set()
    for item in items:
        p = Path(item)
        if p.is_dir():
            paths.update(p.rglob("*.log"))
        elif p.is_file():
            paths.add(p)
    return sorted(paths)


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("inputs", nargs="+", help="Fichiers .log ou dossiers")
    p.add_argument("--json", nargs="?", const="-", metavar="PATH",
                   help="Sortie JSON fichier ou stdout avec '-'")
    p.add_argument("--end-date", type=int, default=None,
                   help="Horizon moteur explicite (jour AIDate) pour les censures")
    opts = p.parse_args(argv)
    paths = _inputs(opts.inputs)
    if not paths:
        p.error("aucun fichier .log trouvé")
    report = analyse_files(paths, end_date=opts.end_date)
    if opts.json is not None:
        data = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if opts.json == "-":
            print(data, end="")
        else:
            output = Path(opts.json)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(data, encoding="utf-8")
    else:
        for run in report["runs"]:
            print(f"{run['file']}: {run['summary']['status_counts']} "
                  f"first_use={run['summary']['first_use_confirmed']} "
                  f"unmatched_reuse={run['summary']['unmatched_reuse_count']} "
                  f"warnings={run['summary']['warning_counts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
