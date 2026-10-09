#!/usr/bin/env python3
"""Profit comptable VEHS des premiers réemplois physiques AIR (observationnel).

La comptabilité d'un groupe air|StationID,StationID ne prouve ni revenu brut,
ni profit net du capital, ni bénéfice après le dernier checkpoint.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import json
import math
from pathlib import Path
import sys

import analyse_air_orphan_reuse as orphan
from parse_air_finance_margin import clean_log_line, parse_kv_payload


def aidate(d):
    # Corrélation exacte AIDate / date de jeu confirmée dans les logs du banc.
    return d.toordinal() + 365


def iso(day):
    return date.fromordinal(day - 365).isoformat()


def parse_date(raw):
    if not isinstance(raw, str):
        return None
    try:
        d = date.fromisoformat(raw)
        return d if d.isoformat() == raw else None
    except ValueError:
        return None


def integer(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return None


def amount(value):
    return float(value) if (isinstance(value, (int, float)) and
                            not isinstance(value, bool) and math.isfinite(value)) else None


def pair(values):
    if not isinstance(values, list) or len(values) != 2:
        return None
    a, b = [integer(v) for v in values]
    return tuple(sorted((a, b))) if a is not None and b is not None else None


def physical(line):
    if not isinstance(line, dict) or line.get("mode") != "air":
        return None
    stations = pair(line.get("station_ids"))
    if stations is None or stations[0] == stations[1]:
        return None
    key = f"air|{stations[0]},{stations[1]}"
    return key if line.get("line_key_local") == key else None


def load_snapshots(path):
    warnings = []
    if path.suffix.lower() == ".jsonl":
        snapshots = []
        with path.open(encoding="utf-8") as fh:
            for i, raw in enumerate(fh, 1):
                if not raw.strip():
                    continue
                record = json.loads(raw)
                if not isinstance(record, dict) or not isinstance(record.get("line_telemetry"), dict):
                    continue
                run = record.get("run")
                if not isinstance(run, list) or len(run) < 2:
                    warnings.append(f"invalid_jsonl_run:{i}")
                    continue
                tel = record["line_telemetry"]
                snapshots.append(dict(
                    duel_policy_id=record.get("duel_policy_id"), arm=run[0],
                    seed=run[1], repeat=run[2] if len(run) > 2 else 0,
                    date=record.get("date"), ok=tel.get("ok"),
                    lines=tel.get("lines"), unresolved_vehicles=tel.get("unresolved_vehicles", [])))
        return snapshots, {"source": "jsonl"}, warnings
    root = json.loads(path.read_text(encoding="utf-8"))
    tel = root.get("line_telemetry")
    if not isinstance(tel, dict) or not isinstance(tel.get("snapshots"), list):
        raise ValueError("line_telemetry.snapshots absent du JSON")
    return tel["snapshots"], {
        "source": "final_json", "campaign": root.get("campaign_id"),
        "scope": tel.get("scope"), "schema": tel.get("schema_version"),
        "bundle": root.get("source_bundle_sha256")}, warnings


def index_snapshots(snapshots, company, warnings):
    by_run = defaultdict(dict)
    for pos, s in enumerate(snapshots):
        if not isinstance(s, dict) or s.get("arm") != company:
            continue
        p = s.get("duel_policy_id")
        seed, repeat = s.get("seed"), s.get("repeat")
        d = parse_date(s.get("date"))
        if (not isinstance(p, str) or not p or integer(seed) is None
                or integer(repeat) is None or d is None
                or s.get("year", d.year) != d.year):
            warnings.append(f"invalid_snapshot_identity:{pos}")
            continue
        key = (p, seed, repeat)
        day = d.isoformat()
        if day in by_run[key]:
            by_run[key][day]["_duplicate"] = True
            warnings.append(f"duplicate_snapshot:{key}:{day}")
        else:
            by_run[key][day] = {**s, "_date": d}
    return {k: sorted(v.values(), key=lambda s: s["_date"]) for k, v in by_run.items()}


def read_events(path):
    reuses, builds, build_tries = [], [], []
    with path.open(encoding="utf-8", errors="replace") as fh:
        for n, raw in enumerate(fh, 1):
            line = clean_log_line(raw)
            match = orphan.TOKEN.search(line)
            if match and match.group(1) == "AIR_HUB_REUSE":
                event = orphan._event(match.group(1), match.group(2), n, [])
                if event is not None:
                    reuses.append(event)
            if "C121_BUILD line=" in line:
                fields = parse_kv_payload(line.split("C121_BUILD ", 1)[1])
                try:
                    builds.append(dict(line=int(fields["line"]),
                                       stations=tuple(sorted((int(fields["station_id_a"]),
                                                              int(fields["station_id_b"])))),
                                       town_a=int(fields["town_a"]),
                                       town_b=int(fields["town_b"])))
                except (ValueError, KeyError):
                    pass  # Sonde C121 facultative, la jointure AIR demeure stricte.
            if "AIR_FINANCE_TRY " in line:
                raw_fields = line.split("AIR_FINANCE_TRY ", 1)[1]
                fields = parse_kv_payload(raw_fields)
                # Conserver aussi les lignes de succès incomplètes ; il ne
                # faut jamais promouvoir un champ absent en dépense nulle.
                if fields.get("outcome") == "built" and fields.get("reason") == "OK":
                    build_tries.append({
                        "fields": fields, "position": n,
                        "duplicate_fields": len([
                            m.group(1) for m in orphan.RE_KV.finditer(raw_fields)
                        ]) != len(set(m.group(1) for m in orphan.RE_KV.finditer(raw_fields))),
                    })
    return reuses, builds, build_tries


def strict_event(record, reuses):
    found = [e for e in reuses
             if (e["line"], e["date"], e["station"], e["anchor"], e["side"],
                 e["prior_line_refs"]) ==
             (record["first_reuse_line"], record["first_reuse_date"],
              record["station"], record["anchor"], record["first_reuse_side"], 0)]
    return found[0] if len(found) == 1 else None


def actual_build_spend(event, build_tries):
    """Coût vraiment débité au chantier : succès unique, mêmes identifiants.

    Ni C121_BUILD.actual_* (modèle), ni un échec portant le même lineId,
    ni une construction d'un autre run ne servent de coût.
    """
    selected = []
    for trial in build_tries:
        raw_line = trial["fields"].get("line")
        if raw_line is not None and raw_line.isdecimal() and int(raw_line) == event["line"]:
            selected.append(trial)
    if not selected:
        return None, "missing_built_try"
    if len(selected) != 1 or selected[0]["duplicate_fields"]:
        return None, "ambiguous_built_try"
    fields = selected[0]["fields"]
    day = parse_date(fields.get("date"))
    src = integer(fields.get("src_town"))
    dst = integer(fields.get("dst_town"))
    if (day is None or aidate(day) != event["date"]
            or (src, dst) != (event["src_town"], event["dst_town"])):
        return None, "ambiguous_build_metadata"
    amount_raw = fields.get("actual")
    if amount_raw is None or not amount_raw.isdecimal():
        return None, "missing_or_invalid_actual"
    return int(amount_raw), "matched_real_build"


def town_endpoint_ok(group, event):
    if pair(group.get("town_ids")) != tuple(sorted((event["src_town"], event["dst_town"]))):
        return False
    stations, towns = group.get("ordered_station_ids"), group.get("ordered_town_ids")
    if stations is None or towns is None:
        return True
    if not isinstance(stations, list) or not isinstance(towns, list) or len(stations) != 2 or len(towns) != 2:
        return False
    expected = event["src_town"] if event["side"] == "A" else event["dst_town"]
    return any(integer(s) == event["station"] and integer(t) == expected
               for s, t in zip(stations, towns))


def choose_group(snapshots, event, builds):
    c121 = [b for b in builds if b["line"] == event["line"]]
    if len(c121) > 1:
        return None, "ambiguous_duplicate_c121_build"
    if c121:
        # NoAI logue les deux StationID et les deux TownID au succès, avant
        # tout service. STNN.base.town est un label sérialisé différent (+1
        # constaté en r2) : ne pas le transformer par hypothèse de codec.
        origin = c121[0]
        stations = origin["stations"]
        if (event["station"] not in stations or
                (origin["town_a"], origin["town_b"]) !=
                (event["src_town"], event["dst_town"])):
            return None, "ambiguous_c121_endpoint_conflict"
        if len({b["line"] for b in builds if b["stations"] == stations}) > 1:
            return None, "ambiguous_shared_station_pair"
        key = f"air|{stations[0]},{stations[1]}"
        earliest = False
        later = False
        for snap in snapshots:
            if snap.get("ok") is not True or snap.get("_duplicate") or not isinstance(snap.get("lines"), list):
                continue
            for line in snap["lines"]:
                if physical(line) != key:
                    continue
                if aidate(snap["_date"]) < event["date"]:
                    earliest = True
                else:
                    later = True
        if earliest:
            return None, "ambiguous_preexisting_group"
        if not later:
            return None, ("no_postbuild_snapshot" if not any(
                aidate(s["_date"]) >= event["date"] for s in snapshots) else "unmatched_group")
        return key, "matched_c121_physical"

    # Repli sûr en absence de C121_BUILD : la seule station orpheline ne
    # détermine pas l'autre gare. Exiger deux TownID compatibles, sans
    # convertir les IDs STNN par un décalage supposé.
    keys = set()
    preexisting = False
    for snap in snapshots:
        if snap.get("ok") is not True or snap.get("_duplicate") or not isinstance(snap.get("lines"), list):
            continue
        for line in snap["lines"]:
            key = physical(line)
            if key is None or event["station"] not in pair(line["station_ids"]):
                continue
            correct = town_endpoint_ok(line, event)
            if aidate(snap["_date"]) < event["date"]:
                preexisting |= correct
            elif correct:
                keys.add(key)
    if preexisting:
        return None, "ambiguous_preexisting_group"
    if len(keys) > 1:
        return None, "ambiguous_multiple_groups"
    if not keys:
        return None, ("no_postbuild_snapshot" if not any(
            aidate(s["_date"]) >= event["date"] for s in snapshots) else "unmatched_group")
    key = next(iter(keys))
    station_pair = tuple(map(int, key.split("|", 1)[1].split(",")))
    users = {x["line"] for x in builds if x["stations"] == station_pair}
    if len(users) > 1:
        return None, "ambiguous_shared_station_pair"
    if users and event["line"] not in users:
        return None, "ambiguous_build_identity"
    return key, "matched"


def vehicle_financials(group):
    rows = group.get("vehicle_financials")
    if not isinstance(rows, list) or not rows:
        return None, "missing_vehicle_details"
    vehicles = {}
    unitnumbers = group.get("unitnumbers")
    for position, v in enumerate(rows):
        if not isinstance(v, dict):
            return None, "invalid_vehicle_details"
        vid = integer(v.get("vehicle_id"))
        if vid is None or vid in vehicles:
            return None, "ambiguous_vehicle_id"
        vehicles[vid] = {
            "vehicle_id": vid,
            "profit_ytd_gbp": amount(v.get("profit_this_year_gbp")),
            "profit_previous_year_gbp": amount(v.get("profit_last_year_gbp")),
            "vehicle_book_value_raw": v.get("vehicle_value"),
            "unitnumber": (unitnumbers[position] if isinstance(unitnumbers, list)
                           and position < len(unitnumbers) else None),
        }
    if group.get("vehicles") != len(vehicles):
        return None, "vehicle_count_mismatch"
    return vehicles, None


def interval(previous, current):
    if previous is None:
        return {"status": "baseline_unknown", "full_group_delta_gbp": None}
    month0 = previous["_date"].year * 12 + previous["_date"].month
    month1 = current["_date"].year * 12 + current["_date"].month
    if month1 - month0 != 1:
        return {"status": "nonconsecutive_months", "full_group_delta_gbp": None}
    if previous["status"] != "observed" or current["status"] != "observed":
        return {"status": "missing_or_invalid_group", "full_group_delta_gbp": None}
    old, new = previous["_by_vehicle"], current["_by_vehicle"]
    shared = set(old) & set(new)
    entered, removed = sorted(set(new) - set(old)), sorted(set(old) - set(new))
    # Les checkpoints du 1er janvier peuvent précéder la bascule interne du
    # moteur. R2 : solde 1971 encore en YTD au 1972-01-01, puis report de
    # profit_last_year seulement au 1972-02-01. Ne JAMAIS déclencher la
    # bascule sur le seul changement d'année civile du nom du checkpoint.
    flips = []
    for vid in shared:
        last_before = old[vid]["profit_previous_year_gbp"]
        last_after = new[vid]["profit_previous_year_gbp"]
        flips.append(None if last_before is None or last_after is None
                     else abs(last_after - last_before) > 0.000001)
    mixed_rollover = (None in flips or (True in flips and False in flips))
    reset = bool(flips) and all(flag is True for flag in flips)
    boundary = previous["_date"].year != current["_date"].year
    if reset and current["_date"].month not in (1, 2):
        # Changement du solde last_year hors bascule annuelle attendue.
        mixed_rollover = True
        reset = False
    if boundary and not reset and not mixed_rollover:
        # Même avec profit_last_year=0, un YTD qui baisse au changement
        # d'année peut cacher une bascule sans signal distinctif.
        mixed_rollover = any(
            old[vid]["profit_ytd_gbp"] is not None
            and new[vid]["profit_ytd_gbp"] is not None
            and new[vid]["profit_ytd_gbp"] < old[vid]["profit_ytd_gbp"] - 0.000001
            for vid in shared)
    details = []
    for vid in sorted(shared):
        before, after = old[vid], new[vid]
        a, b = before["profit_ytd_gbp"], after["profit_ytd_gbp"]
        closed = after["profit_previous_year_gbp"]
        delta = None
        if a is not None and b is not None and not mixed_rollover:
            if reset and closed is not None:
                delta = round(closed - a + b, 6)
            elif not reset:
                delta = round(b - a, 6)
        details.append({"vehicle_id": vid, "profit_delta_gbp": delta})
    deltas = [d["profit_delta_gbp"] for d in details if d["profit_delta_gbp"] is not None]
    qualified = (not mixed_rollover and not entered and not removed
                 and len(details) == len(new)
                 and len(deltas) == len(details)
                 and previous["unresolved_air_vehicles"] == 0
                 and current["unresolved_air_vehicles"] == 0)
    return {
        "status": "complete" if qualified else "partial",
        "from": previous["date"], "to": current["date"],
        "calendar_reset": reset,
        "calendar_year_boundary": boundary,
        "mixed_or_unverifiable_rollover": mixed_rollover,
        "method": "last_year_bridge" if reset else "ytd_difference",
        "new_vehicle_ids": entered, "removed_vehicle_ids": removed,
        "vehicle_profit_deltas": details,
        "known_continuing_vehicle_delta_gbp": round(sum(deltas), 6) if deltas else None,
        "full_group_delta_gbp": round(sum(deltas), 6) if qualified else None,
    }


def line_observations(snapshots, event, group_key):
    observations, closed_years = [], []
    previous = None
    for snap in snapshots:
        if aidate(snap["_date"]) < event["date"]:
            continue
        d = snap["_date"]
        item = {
            "date": d.isoformat(), "_date": d, "status": "group_absent",
            "vehicle_count": None, "vehicles": [],
            "line_profit_ytd_gbp": None,
            "line_profit_previous_year_gbp": None,
            "unresolved_air_vehicles": None,
        }
        if snap.get("_duplicate") or snap.get("ok") is not True or not isinstance(snap.get("lines"), list):
            item["status"] = "invalid_checkpoint"
        else:
            groups = [g for g in snap["lines"] if physical(g) == group_key]
            if len(groups) > 1:
                item["status"] = "ambiguous_duplicate_group"
            elif groups:
                mapping, problem = vehicle_financials(groups[0])
                if problem:
                    item["status"] = problem
                else:
                    item["status"] = "observed"
                    item["_by_vehicle"] = mapping
                    item["vehicles"] = [mapping[v] for v in sorted(mapping)]
                    item["vehicle_count"] = len(mapping)
                    ytd = [v["profit_ytd_gbp"] for v in mapping.values()]
                    last = [v["profit_previous_year_gbp"] for v in mapping.values()]
                    item["line_profit_ytd_gbp"] = (round(sum(ytd), 6)
                                                    if all(v is not None for v in ytd) else None)
                    item["line_profit_previous_year_gbp"] = (round(sum(last), 6)
                                                              if all(v is not None for v in last) else None)
                    missing = snap.get("unresolved_vehicles")
                    item["unresolved_air_vehicles"] = (
                        sum(isinstance(v, dict) and v.get("mode") == "air" for v in missing)
                        if isinstance(missing, list) else None)
        item["period"] = interval(previous, item)
        if (item["status"] == "observed"
                and item["period"].get("calendar_reset") is True):
            closed_years.append({
                "closed_calendar_year": d.year - 1,
                "checkpoint": item["date"],
                "surviving_vehicle_profit_last_year_gbp":
                    item["line_profit_previous_year_gbp"],
                "vehicles_still_present": item["vehicle_count"],
                "complete_year_profit_proven": False,
                "qualification": "solde des véhicules survivants, retraits antérieurs inconnus",
            })
        observations.append(item)
        previous = item
    for item in observations:
        item.pop("_date", None)
        item.pop("_by_vehicle", None)
    return observations, closed_years


def analyze(results_path, logs, company="OpexAI"):
    snaps, provenance, warnings = load_snapshots(Path(results_path))
    indexed = index_snapshots(snaps, company, warnings)
    roots = orphan.analyse_files(logs)
    table = []
    for run in roots["runs"]:
        key = (run["arm"], run["seed"], run["repeat"])
        events, builds, build_tries = read_events(Path(run["file"]))
        snapshots = indexed.get(key, [])
        if not snapshots:
            warnings.append(f"no_snapshots_for_run:{key}")
        for old in run["orphans"]:
            record = {
                "arm": run["arm"], "seed": run["seed"], "repeat": run["repeat"],
                "orphan_station": old["station"], "orphan_anchor": old["anchor"],
                "orphan_date": iso(old["date"]),
                "historical_orphan_cost_a_gbp": old["cost_a_gbp"],
                "new_build_actual_cost_gbp": None,
                "new_build_cost_status": "not_applicable_no_confirmed_first_use",
                "combined_historical_spend_gbp": None,
                "first_use_line": old["first_reuse_line"],
                "build_date": iso(old["first_reuse_date"]) if old["first_reuse_date"] else None,
                "side": old["first_reuse_side"],
                "source_town": None, "destination_town": None,
                "match_status": "orphan_" + old["status"],
                "physical_group": None,
                "eligible_checkpoints": 0, "observed_checkpoints": 0,
                "complete_monthly_intervals": 0, "partial_monthly_intervals": 0,
                "sum_complete_intervals_gbp": None,
                "first_observed": None, "last_observed": None,
                "snapshots": [], "annual_closures": [],
            }
            if old["status"] == "first_use_confirmed":
                event = strict_event(old, events)
                if event is None:
                    record["match_status"] = "ambiguous_or_missing_reuse_event"
                    record["new_build_cost_status"] = "missing_or_ambiguous_reuse_event"
                else:
                    record["source_town"], record["destination_town"] = (
                        event["src_town"], event["dst_town"])
                    spend, spend_status = actual_build_spend(event, build_tries)
                    record["new_build_actual_cost_gbp"] = spend
                    record["new_build_cost_status"] = spend_status
                    if spend is not None:
                        record["combined_historical_spend_gbp"] = (
                            old["cost_a_gbp"] + spend)
                    group, status = choose_group(snapshots, event, builds)
                    record["match_status"] = status
                    if group:
                        record["physical_group"] = group
                        observations, annual = line_observations(snapshots, event, group)
                        found = [v for v in observations if v["status"] == "observed"]
                        complete = [v["period"]["full_group_delta_gbp"] for v in observations
                                    if v["period"]["status"] == "complete"]
                        record.update({
                            "eligible_checkpoints": len(observations),
                            "observed_checkpoints": len(found),
                            "complete_monthly_intervals": len(complete),
                            "partial_monthly_intervals": sum(
                                v["period"]["status"] == "partial" for v in observations),
                            "sum_complete_intervals_gbp": round(sum(complete), 6) if complete else None,
                            "first_observed": found[0]["date"] if found else None,
                            "last_observed": found[-1]["date"] if found else None,
                            "snapshots": observations, "annual_closures": annual,
                        })
            table.append(record)
        warnings.extend("orphan_parser_" + w["code"] + ":" + run["file"]
                        for w in run["warnings"])
    statuses = Counter(v["match_status"] for v in table)
    return {
        "source": str(results_path), "telemetry": provenance, "company": company,
        "summary": {
            "orphans": len(table),
            "first_reuses": sum(v["first_use_line"] is not None for v in table),
            "physical_groups_matched": sum(v["physical_group"] is not None for v in table),
            "match_statuses": dict(sorted(statuses.items())),
            "eligible_checkpoints": sum(v["eligible_checkpoints"] for v in table),
            "observed_checkpoints": sum(v["observed_checkpoints"] for v in table),
            "complete_monthly_intervals": sum(v["complete_monthly_intervals"] for v in table),
            "partial_monthly_intervals": sum(v["partial_monthly_intervals"] for v in table),
            "closed_year_observations": sum(len(v["annual_closures"]) for v in table),
            "new_build_cost_statuses": dict(sorted(Counter(
                v["new_build_cost_status"] for v in table).items())),
            "confirmed_first_uses_with_real_build_cost": sum(
                v["new_build_cost_status"] == "matched_real_build" for v in table),
        },
        "lines": table, "warnings": warnings,
        "limitations": [
            "Station-pair VEHS != lineId NoAI; l'agrégation est exclue en présence de plusieurs builds détectés.",
            "YTD est un solde par année civile, pas le profit depuis la construction.",
            "Premiers soldes, nouveaux/anciens avions, lacunes et disparitions n'ont pas de delta complet.",
            "Profit comptable VEHS sans décomposition revenu / running, ni cash net du capital.",
            "Somme dépenses = coût A orphelin historique + chantier ultérieur réel, sans valeur de ROI.",
            "Ne jamais prolonger les profits au-delà du dernier checkpoint observé.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True,
                        help="JSON final line_telemetry.snapshots ; JSONL accepté pour diagnostics")
    parser.add_argument("--logs", type=Path, required=True)
    parser.add_argument("--company", default="OpexAI")
    parser.add_argument("--json", nargs="?", const="-", default="-",
                        help="Fichier JSON, ou '-' pour stdout")
    args = parser.parse_args(argv)
    if not args.logs.is_dir():
        parser.error("--logs doit être un dossier")
    logs = sorted(args.logs.glob("*.log"))
    if not logs:
        parser.error("aucun log trouvé")
    try:
        report = analyze(args.results, logs, company=args.company)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        parser.error(str(error))
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.json == "-":
        print(output, end="")
    else:
        Path(args.json).write_text(output, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
