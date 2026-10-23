"""AIR-ROI-RENFORT-1: auditeur de randomisation prospective par épisode.

Le réglage ``air_roi_renfort1_itt=2`` (p=50) randomise les occasions AIR
``treatment`` / ``deferred`` dans chaque partie. L'unité expérimentale est
l'épisode, mais la grappe statistique indépendante est la graine. Les échecs
de constructeur restent dans le dénominateur d'intention de traiter (ITT).

Les logs ``AIRR1_ITT_ASSIGN / AIRR1_ITT_OUTCOME`` donnent seulement exposition
et réalisation : ils ne donnent aucun rendement marginal. Un endpoint à 24
mois est calculé UNIQUEMENT si 24 observations mensuelles nettes comparables
par épisode sont fournies comme ``AIRR1_ITT_MONTH`` dans les logs ou comme
JSONL (``record_type=airr1_itt_month``, ``episode_id``, ``seed``, ``line``,
``month_offset`` 1..24, ``net_profit_gbp``, ``complete=true``). L'endpoint est
le profit net *de la ligne entière* des mois 13..24, jamais celui d'un avion.

Le JSONL C66 de ``--line-telemetry --line-telemetry-monthly`` est également
inspecté : appariement seulement par deux tuiles de stations prétraitement
et unicité de ligne AIR. Ses ``profit_this_year_gbp`` sont des profits des
véhicules ; en l'absence de comptabilité d'infrastructure et de coupe
exacte à t0+24 mois ils restent une série descriptive, pas l'endpoint net ITT.

Usage : python -X utf8 sweeps/audit_air_roi_renfort1_itt.py
            'results/..._seed*_r0.log' --telemetry 'results/...jsonl'
            --format markdown
"""

from __future__ import annotations

import argparse
import calendar
from collections import Counter, defaultdict
from datetime import date
import glob
import gzip
import json
import math
from pathlib import Path
import random
import re
from statistics import mean, median


LOG = re.compile(r"\bOPEX\s+(\d{4}-\d{1,2}-\d{1,2})\s+(AIRR1_ITT_ASSIGN|AIRR1_ITT_OUTCOME|AIRR1_ITT_MONTH|AIRR1_ITT_CENSOR)\s+(.*)$")
FIELDS = re.compile(r"([A-Za-z_][A-Za-z_0-9]*)=([^\s]+)")
SEED_RE = re.compile(r"(?:^|[_-])seed[_-]?(\d+)(?=[_.-]|$)", re.I)
REPEAT_RE = re.compile(r"(?:^|[_-])r(\d+)(?=[_.-]|$)", re.I)
ARMS = {"treatment": "treatment", "reinforce": "treatment", "renfort": "treatment",
        "deferred": "deferred", "defer": "deferred", "sans_renfort": "deferred"}
MISSING = {"", "na", "none", "null", "unknown", "missing", "-"}
FLEETS = ("1", "2", "3-4", ">=5", "unknown")
SATURATION = ("saturated", "unsaturated", "unknown")
KINDS = ("newpair", "hubsite", "hubhub", "other", "unknown")


def first(row, *keys):
    for k in keys:
        value = row.get(k)
        if value is not None and str(value).strip().lower() not in MISSING:
            return value
    return None


def number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (ValueError, TypeError):
        return None


def integer(value):
    value = number(value)
    return int(value) if value is not None and value.is_integer() else None


def yes(value):
    return value is True or value == 1 or (isinstance(value, str) and
           value.lower() in ("true", "1", "yes", "ok"))


def paths_from_globs(patterns):
    return sorted({Path(name) for pattern in patterns for name in glob.glob(str(pattern))
                   if Path(name).is_file()})


def read_lines(path):
    opener = gzip.open if str(path).lower().endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        yield from handle


def jsonl_rows(paths):
    for path in paths:
        for position, raw in enumerate(read_lines(path), 1):
            if not raw.strip():
                continue
            try:
                item = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{position}: invalid JSONL: {exc}") from exc
            if not isinstance(item, dict):
                raise ValueError(f"{path}:{position}: expected JSON object")
            yield item


def game_date(value):
    try:
        y, m, d = (int(v) for v in str(value).split("-"))
        return date(y, m, d)
    except (ValueError, TypeError):
        return None


def add_months(d, count):
    m = d.year * 12 + d.month - 1 + count
    year, m0 = divmod(m, 12)
    month = m0 + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def log_records(path):
    for lineno, raw in enumerate(read_lines(path), 1):
        match = LOG.search(raw)
        if match:
            date_str, kind, payload = match.groups()
            row = dict(FIELDS.findall(payload))
            row["log_date"] = date_str
            yield kind, row, lineno
        elif raw.lstrip().startswith("{"):
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            kind = first(row, "record_type", "event", "tag", "type")
            if kind and str(kind).lower() in ("airr1_itt_assign", "airr1_itt_outcome", "airr1_itt_month"):
                yield str(kind).upper(), row, lineno


def filename_seed(path):
    match = SEED_RE.search(Path(path).name)
    return match.group(1) if match else None


def filename_repeat(path):
    match = REPEAT_RE.search(Path(path).name)
    return int(match.group(1)) if match else 0


def arm(row):
    return ARMS.get(str(first(row, "arm", "assignment") or "").lower())


def episode_id(row):
    value = first(row, "episode_id", "episode", "id")
    return str(value) if value is not None else None


def fleet_class(count):
    count = integer(count)
    if count is None or count < 1:
        return "unknown"
    return "1" if count == 1 else "2" if count == 2 else "3-4" if count <= 4 else ">=5"


def saturation_class(row):
    # Ici saturation = cible atteinte à l'instant du choix, PAS taux de charge.
    flag = first(row, "saturation")
    if str(flag).lower() in ("1", "true", "saturated"):
        return "saturated"
    if str(flag).lower() in ("0", "false", "unsaturated"):
        return "unsaturated"
    want = integer(first(row, "target"))
    have = integer(first(row, "vehicles_before", "baseline"))
    if want is not None and have is not None and have >= 1:
        return "saturated" if want <= have else "unsaturated"
    return "unknown"


def kind_class(row):
    k = str(first(row, "kind", "c121_arm", "c121Arm") or "unknown").lower()
    return k if k in KINDS else "other"


def _assignment(path, row, outcomes, issue):
    seed = first(row, "seed") or filename_seed(path)
    eid = episode_id(row)
    line = first(row, "line", "lineId")
    assignment = arm(row)
    out_rows = outcomes
    outcome = out_rows[0] if len(out_rows) == 1 else {}
    bad = list(issue)
    if len(out_rows) != 1:
        bad.append("missing_outcome" if not out_rows else "duplicate_outcome")
    if assignment is None:
        bad.append("invalid_arm")
    if seed is None:
        bad.append("missing_seed")
    if line is None:
        bad.append("missing_line")
    if integer(first(row, "p")) not in (0, 50):
        bad.append("unknown_assignment_probability")
    if out_rows and first(outcome, "line", "lineId") not in (None, line):
        bad.append("line_mismatch")
    if out_rows and arm(outcome) not in (None, assignment):
        bad.append("arm_mismatch")
    if out_rows and first(outcome, "seed") not in (None, seed, str(seed)):
        bad.append("seed_mismatch")
    if out_rows and first(outcome, "id", "episode_id", "episode") not in (None, eid):
        bad.append("episode_mismatch")
    assigned_tick = integer(first(row, "tick_pre", "tick", "execution_tick"))
    outcome_tick = integer(first(outcome, "tick_after"))
    # Le saut de tick est conservé, sa valeur 0 n'est pas imposée par le devis.
    baseline = integer(first(row, "vehicles_before", "baseline", "have_actual"))
    added = integer(first(outcome, "added"))
    replaced = integer(first(outcome, "replaced"))
    delivered_reported = assignment == "treatment" and added == 1 and replaced == 0
    station_a = integer(first(row, "station_a", "stationA"))
    station_b = integer(first(row, "station_b", "stationB"))
    if station_a == station_b:
        station_a = station_b = None
    return {"file": str(path), "seed": str(seed) if seed is not None else None,
            "repeat": filename_repeat(path), "episode_id": eid, "line": str(line) if line is not None else None,
            "date": first(row, "log_date", "date_pre", "date"), "tick_pre": assigned_tick,
            "tick_after": outcome_tick, "p": integer(first(row, "p")), "hash": first(row, "hash"),
            "seq": integer(first(row, "seq")), "until_date": first(row, "until_date"),
            "arm": assignment, "baseline": baseline, "fleet_class": fleet_class(baseline),
            "saturation": saturation_class(row), "kind": kind_class(row),
            "station_tiles": tuple(sorted((station_a, station_b))) if station_a is not None and station_b is not None else None,
            "v161_model": number(first(row, "v161_model")), "v161_source": first(row, "v161_source", "v161_src"),
            "v161_cohort": ("cold_start" if integer(first(row, "marginal_samples")) == 0
                              else "sampled" if (integer(first(row, "marginal_samples")) or 0) > 0 else "unknown"),
            "roi_estimated": number(first(row, "roi")), "quote": number(first(row, "quote")),
            "added": added, "replaced": replaced, "reason": first(outcome, "reason") or "missing",
            "reported_delivered": delivered_reported, "verified_vehicle_id": first(outcome, "VehicleID", "vehicle"),
            "transaction_accounting_cost": number(first(outcome, "actual_cost")),
            "issue": sorted(set(bad)), "line_profit_last_12m": None,
            "line_vehicle_operating_profit_last_12m": None,
            "line_vehicle_operating_profit_first_12m": None,
            "vehicle_running_cost_est_last_12m": None,
            "vehicle_revenue_est_last_12m": None,
            "aircraft_24m": None,
            "line_fleet_profit_12m_proxy": None, "line_telemetry_status": "not_supplied"}


def read_assignments(paths):
    result, month_rows, global_issues = [], [], Counter()
    for path in paths:
        slots = defaultdict(lambda: {"assign": [], "outcome": []})
        for kind, row, lineno in log_records(path):
            if kind in ("AIRR1_ITT_MONTH", "AIRR1_ITT_CENSOR"):
                if kind == "AIRR1_ITT_CENSOR":
                    row = {**row, "record_type": "airr1_itt_censor"}
                month_rows.append({**row, "_source_file": str(path)})
                continue
            eid = episode_id(row)
            if eid is None:
                global_issues["event_without_id"] += 1
                continue
            role = "assign" if kind == "AIRR1_ITT_ASSIGN" else "outcome"
            slots[eid][role].append(row)
        for eid, record in slots.items():
            assignments = record["assign"]
            if not assignments:
                global_issues["outcome_without_assignment"] += len(record["outcome"])
                continue
            # L'ITT n'efface aucune affectation double et refuse son endpoint.
            issue = ["duplicate_assignment"] if len(assignments) > 1 else []
            item = _assignment(path, assignments[0], record["outcome"], issue)
            result.append(item)
            global_issues.update(item["issue"])
    return result, month_rows, dict(sorted(global_issues.items()))


def _episode_key(row):
    if row.get("seed") is None or row.get("episode_id") is None:
        return None
    return (str(row["seed"]), int(row.get("repeat") or 0), str(row["episode_id"]))


def observe_explicit_months(episodes, months):
    """Exige 24 mois uniques; garde les frais de flotte séparés de l'infrastructure."""
    index = defaultdict(list)
    for row in months:
        eid = episode_id(row)
        if eid is None:
            continue
        seed = first(row, "seed") or filename_seed(row.get("_source_file", ""))
        repeat = integer(first(row, "repeat"))
        if repeat is None:
            repeat = filename_repeat(row.get("_source_file", ""))
        index[(str(seed), repeat, eid)].append(row)
    status = Counter()
    for episode in episodes:
        key = _episode_key(episode)
        series = index.get(key, [])
        if not series:
            status["no_explicit_months"] += 1
            continue
        by_month = defaultdict(list)
        for r in series:
            if str(first(r, "line", "lineId")) != episode["line"]:
                continue
            offset = integer(first(r, "month_offset"))
            if offset is not None and 1 <= offset <= 24:
                by_month[offset].append(r)
        if any(len(by_month[n]) != 1 for n in range(1, 25)):
            status["incomplete_or_duplicated_24_months"] += 1
            continue
        values = []
        operating = []
        running = []
        revenues = []
        valid = True
        operating_valid = True
        for n in range(1, 25):
            current = by_month[n][0]
            amount = number(first(current, "net_profit_gbp", "line_net_profit_month_gbp"))
            if not yes(current.get("complete")):
                valid = False
                break
            if amount is None:
                valid = False
            else:
                values.append(amount)
            op = number(first(current, "vehicle_net_profit_gbp"))
            cost = number(first(current, "running_cost_est_gbp"))
            revenue = number(first(current, "revenue_est_gbp"))
            if op is None or cost is None or revenue is None or \
                    abs((op + cost) - revenue) > max(.01, abs(revenue) * 1e-7) or \
                    first(current, "scope") != "vehicle_operating_no_infrastructure":
                operating_valid = False
            else:
                operating.append(op)
                running.append(cost)
                revenues.append(revenue)
        if operating_valid and len(operating) == 24:
            episode["line_vehicle_operating_profit_last_12m"] = sum(operating[12:])
            episode["vehicle_running_cost_est_last_12m"] = sum(running[12:])
            episode["vehicle_revenue_est_last_12m"] = sum(revenues[12:])
            episode["aircraft_24m"] = integer(first(by_month[24][0], "aircraft"))
            status["complete_24_months_vehicle_operating"] += 1
        if not valid:
            if operating_valid and len(operating) == 24:
                status["vehicle_operating_only_not_full_line_net"] += 1
            else:
                status["incomplete_or_nonnet_month"] += 1
            continue
        # Effet ITT du choix sur le profit de la ligne, tout le parc inclus.
        episode["line_profit_last_12m"] = sum(values[12:])
        status["complete_24_months"] += 1
    return dict(status)


def observe_prospective_windows(episodes, months):
    """Amendement §8 : fenêtres 1-12 et 13-24 autonomes, durée réelle observée.

    Refuse les épisodes ambiguës et les lacunes; n'invente pas de bénéfice net
    d'infrastructure. Les 24 mois historiques conservent leur ancien auditeur.
    """
    index = defaultdict(list)
    for row in months:
        eid = episode_id(row)
        if eid is None:
            continue
        seed = first(row, "seed") or filename_seed(row.get("_source_file", ""))
        repeat = integer(first(row, "repeat"))
        if repeat is None:
            repeat = filename_repeat(row.get("_source_file", ""))
        index[(str(seed), repeat, eid)].append(row)

    status = Counter()
    for ep in episodes:
        rows = index.get(_episode_key(ep), [])
        censored = [r for r in rows if r.get("record_type") == "airr1_itt_censor"]
        ep["followup_censor_reason"] = first(censored[0], "reason") if censored else None
        by_month = defaultdict(list)
        for row in rows:
            if str(first(row, "line", "lineId")) == ep["line"]:
                offset = integer(first(row, "month_offset"))
                if row.get("record_type") != "airr1_itt_censor" and offset is not None:
                    by_month[offset].append(row)
        for endpoint, start, end in (("12m", 1, 12), ("24m", 13, 24)):
            values, costs, revenues, days_total = [], [], [], 0
            reason = None
            for month in range(start, end + 1):
                events = by_month[month]
                if len(events) != 1:
                    reason = "missing_or_duplicate_month"
                    break
                event = events[0]
                if not yes(event.get("complete")):
                    reason = first(event, "fail_reason") or "invalid_interval"
                    break
                days = integer(first(event, "days"))
                due, actual = integer(first(event, "date_due")), integer(first(event, "date_actual"))
                if days is None or not 18 <= days <= 42 or due is None or actual is None \
                        or not 0 <= actual - due <= 14:
                    reason = "invalid_interval_clock"
                    break
                op = number(first(event, "vehicle_net_profit_gbp"))
                cost = number(first(event, "running_cost_est_gbp"))
                revenue = number(first(event, "revenue_est_gbp"))
                if op is None or cost is None or revenue is None or \
                        abs(op + cost - revenue) > max(.01, abs(revenue) * 1e-7) or \
                        first(event, "scope") != "vehicle_operating_no_infrastructure":
                    reason = "invalid_vehicle_accounting"
                    break
                values.append(op)
                costs.append(cost)
                revenues.append(revenue)
                days_total += days
            if reason is None and not 337 <= days_total <= 393:
                reason = "invalid_annual_duration"
            ep["followup_" + endpoint + "_status"] = reason or "valid"
            status[endpoint + "_" + (reason or "valid")] += 1
            if reason is not None:
                continue
            factor = 365.25 / days_total
            if endpoint == "12m":
                ep["line_vehicle_operating_profit_first_12m"] = sum(values) * factor
                ep["vehicle_running_cost_est_first_12m"] = sum(costs) * factor
                ep["vehicle_revenue_est_first_12m"] = sum(revenues) * factor
            else:
                ep["line_vehicle_operating_profit_last_12m"] = sum(values) * factor
                ep["vehicle_running_cost_est_last_12m"] = sum(costs) * factor
                ep["vehicle_revenue_est_last_12m"] = sum(revenues) * factor
                ep["aircraft_24m"] = integer(first(by_month[24][0], "aircraft"))
        if censored:
            status["line_censor_" + (ep["followup_censor_reason"] or "unknown")] += 1
    return dict(status)


def _telemetry_seed(row):
    run = row.get("run") or []
    if len(run) < 2 or str(run[0]) != "OpexAI":
        return None
    return str(run[1]), integer(run[2]) if len(run) > 2 else 0


def read_telemetry(paths, policy_id=None):
    """Indexe les snapshots VEHS, sans prétendre connaître leur lineId NoAI."""
    observations = defaultdict(list)
    defects = Counter()
    for row in jsonl_rows(paths):
        if policy_id is not None and row.get("duel_policy_id") != policy_id:
            continue
        identity = _telemetry_seed(row)
        telemetry = row.get("line_telemetry") or {}
        if identity is None or not telemetry:
            continue
        when = game_date(row.get("date"))
        if when is None or not yes(telemetry.get("ok")):
            defects["invalid_telemetry_checkpoint"] += 1
            continue
        observations[identity].append((when, telemetry.get("lines") or []))
    return observations, dict(defects)


def _find_vehs_line(lines, station_tiles):
    matches = []
    for line in lines:
        if line.get("mode") != "air":
            continue
        raw = line.get("ordered_station_tiles") or []
        try:
            tiles = tuple(sorted(int(tile) for tile in raw))
        except (TypeError, ValueError):
            continue
        if tiles == station_tiles:
            matches.append(line)
    return matches[0] if len(matches) == 1 else None


def attach_telemetry(episodes, telemetry):
    """Trace l'applicabilité du proxy VEHS; jamais un profit net AIR isolé."""
    issues = Counter()
    for episode in episodes:
        key = (episode["seed"], episode["repeat"])
        stations = episode["station_tiles"]
        if stations is None:
            episode["line_telemetry_status"] = "no_pretrade_station_tiles"
            continue
        dates = telemetry.get(key, [])
        if not dates:
            episode["line_telemetry_status"] = "no_telemetry_seed"
            continue
        assigned = game_date(episode["date"])
        if assigned is None:
            episode["line_telemetry_status"] = "bad_assignment_date"
            continue
        # Aucune interpolation : exactement une mesure au 1er du mois attendu.
        # Les 25 points ci-dessous forment 24 *mois civils entiers* après t0.
        first_day = add_months(date(assigned.year, assigned.month, 1), 1)
        checkpoint_dates = [add_months(first_day, m) for m in range(25)]
        index = defaultdict(list)
        for day, lines in dates:
            index[day].append(lines)
        series = []
        for day in checkpoint_dates:
            if len(index[day]) != 1:
                break
            line = _find_vehs_line(index[day][0], stations)
            if line is None:
                break
            this = number(line.get("profit_this_year_gbp"))
            last = number(line.get("profit_last_year_gbp"))
            if this is None:
                break
            series.append((day, this, last))
        if len(series) != 25:
            episode["line_telemetry_status"] = "incomplete_or_unmatched_vehicle_months"
            issues[episode["line_telemetry_status"]] += 1
            continue
        increments = []
        valid = True
        for (previous_day, prev_ytd, _), (day, ytd, last_year) in zip(series[:-1], series[1:]):
            if day.year == previous_day.year:
                increments.append(ytd - prev_ytd)
            elif day.month == 1 and last_year is not None:
                increments.append(last_year - prev_ytd + ytd)
            else:
                valid = False
                break
        if not valid:
            episode["line_telemetry_status"] = "missing_year_rollover_profit"
            issues[episode["line_telemetry_status"]] += 1
            continue
        episode["line_fleet_profit_12m_proxy"] = sum(increments[12:])
        episode["line_telemetry_status"] = "vehicle_profit_24_full_calendar_months_proxy"
        issues["vehicle_profit_24_full_calendar_months_proxy"] += 1
    return dict(sorted(issues.items()))


def cluster_itt(episodes, endpoint="line_profit_last_12m", replays=20000, bootstrap_seed=0):
    """Δ des moyennes d'épisodes ; rééchantillonne des graines ENTIERES.

    Ne conditionne ni sur la livraison ni sur la présence des deux bras dans
    chaque graine. Chaque assignation randomisée observée conserve son poids.
    """
    grouped = defaultdict(lambda: defaultdict(list))
    invalid_assignment = {"duplicate_assignment", "invalid_arm", "missing_seed", "missing_line",
                          "unknown_assignment_probability", "line_mismatch", "arm_mismatch",
                          "seed_mismatch", "episode_mismatch"}
    for row in episodes:
        outcome = number(row.get(endpoint))
        # Les échecs ou absences d'OUTCOME n'excluent jamais un épisode assigné
        # si sa mesure longitudinale peut être récupérée indépendamment.
        if not invalid_assignment.intersection(row["issue"]) and row["seed"] is not None \
                and outcome is not None and row["arm"] in ARMS.values():
            grouped[row["seed"]][row["arm"]].append(outcome)
    paired = [(seed, mean(arms["treatment"]) - mean(arms["deferred"]))
              for seed, arms in sorted(grouped.items()) if arms["treatment"] and arms["deferred"]]
    deltas = [x for _, x in paired]
    count_t = sum(len(arms["treatment"]) for arms in grouped.values())
    count_d = sum(len(arms["deferred"]) for arms in grouped.values())
    seed_t = sum(bool(arms["treatment"]) for arms in grouped.values())
    seed_d = sum(bool(arms["deferred"]) for arms in grouped.values())
    all_t = [v for arms in grouped.values() for v in arms["treatment"]]
    all_d = [v for arms in grouped.values() for v in arms["deferred"]]
    observed = mean(all_t) - mean(all_d) if all_t and all_d else None
    result = {"endpoint": endpoint, "definition": "episode_mean_treatment_minus_deferred_clustered_by_seed",
              "assigned_treatment_observed": count_t, "assigned_deferred_observed": count_d,
              "treatment_seeds": seed_t, "deferred_seeds": seed_d,
              "seeds_with_both_arms": len(deltas), "seed_deltas": dict(paired),
              "mean": observed,
              "median_seed_delta": median(deltas) if deltas else None,
              "seed_wins_losses_ties": {"wins": sum(v > 0 for v in deltas),
                                        "losses": sum(v < 0 for v in deltas),
                                        "ties": sum(v == 0 for v in deltas)},
              "ci95_seed_cluster": None, "bootstrap_replays": replays,
              "bootstrap_valid_replays": 0, "bootstrap_seed": bootstrap_seed}
    if seed_t < 2 or seed_d < 2 or replays < 1:
        return result
    rng = random.Random(bootstrap_seed)
    buckets = list(grouped.values())
    n = len(buckets)
    simulations = []
    for _ in range(replays):
        sample = [buckets[rng.randrange(n)] for _ in range(n)]
        t = [v for group in sample for v in group["treatment"]]
        d = [v for group in sample for v in group["deferred"]]
        if t and d:
            simulations.append(mean(t) - mean(d))
    result["bootstrap_valid_replays"] = len(simulations)
    if len(simulations) < int(replays * .9):
        return result
    simulations.sort()
    def quantile(q):
        p = (len(simulations) - 1) * q
        lo, hi = math.floor(p), math.ceil(p)
        return simulations[lo] + (simulations[hi] - simulations[lo]) * (p - lo)
    result["ci95_seed_cluster"] = [quantile(.025), quantile(.975)]
    return result


def _strata(rows, key, labels, replays, seed):
    return {v: cluster_itt([r for r in rows if r.get(key) == v], replays=replays,
                           bootstrap_seed=seed) for v in labels}


def analyze(log_paths, telemetry_paths=(), month_paths=(), *, replays=20000,
            bootstrap_seed=0, include_episodes=False, telemetry_policy_id=None,
            followup_v2=False):
    episodes, months, issues = read_assignments(log_paths)
    months.extend(row for row in jsonl_rows(month_paths)
                  if str(first(row, "record_type", "event", "type") or "").lower()
                  in ("airr1_itt_month", "month"))
    subjects = [r for r in episodes if r["p"] == 50]
    direct_status = (observe_prospective_windows(subjects, months) if followup_v2
                     else observe_explicit_months(subjects, months))
    telemetry, telemetry_input_issues = read_telemetry(telemetry_paths, policy_id=telemetry_policy_id)
    attached_status = attach_telemetry(subjects, telemetry) if telemetry_paths else {}
    randomized_count = Counter(r["arm"] for r in subjects)
    exposure = {"episodes": len(episodes), "randomized_p50": len(subjects),
                "nonrandomized_p0": sum(r["p"] == 0 for r in episodes),
                "seeds": len({r["seed"] for r in subjects if r["seed"] is not None}),
                "distinct_seed_lines": len({(r["seed"], r["line"]) for r in subjects if r["line"] is not None}),
                "assigned": dict(randomized_count),
                "reported_deliveries_treatment": sum(r["reported_delivered"] for r in subjects),
                "verified_deliveries_with_vehicle_id": sum(r["reported_delivered"] and
                     r["verified_vehicle_id"] is not None for r in subjects),
                "treatment_missing_outcome": sum(r["arm"] == "treatment" and r["added"] is None for r in subjects),
                "issues": issues,
                "fleet": {k: sum(r["fleet_class"] == k for r in subjects) for k in FLEETS},
                "saturation": {k: sum(r["saturation"] == k for r in subjects) for k in SATURATION},
                "kind": {k: sum(r["kind"] == k for r in subjects) for k in KINDS},
                "v161_source": dict(Counter(r["v161_source"] or "unknown" for r in subjects)),
                "v161_cohort": dict(Counter(r["v161_cohort"] for r in subjects))}
    result = {"design": "prospective_episode_randomization_p50_within_game",
              "scope": "ITT of one assignment; never a per-aircraft physical ROI",
              "files": {"logs": len(log_paths), "telemetry": len(telemetry_paths),
                        "telemetry_policy_id": telemetry_policy_id, "month_exports": len(month_paths)},
              "exposure": exposure,
              "monthly_net_observation": direct_status,
              "line_telemetry": {"ingest_issues": telemetry_input_issues, "matching": attached_status,
                                 "scope": "VEHS fleet profit only, 24 full calendar months; not net infrastructure or exact t0+24"},
              "itt_line_net_profit_last_12m": cluster_itt(subjects, replays=replays, bootstrap_seed=bootstrap_seed),
              "itt_line_vehicle_operating_profit_last_12m": cluster_itt(
                  subjects, endpoint="line_vehicle_operating_profit_last_12m",
                  replays=replays, bootstrap_seed=bootstrap_seed),
              "itt_line_vehicle_operating_profit_first_12m": cluster_itt(
                  subjects, endpoint="line_vehicle_operating_profit_first_12m",
                  replays=replays, bootstrap_seed=bootstrap_seed),
              "itt_vehicle_running_cost_est_last_12m": cluster_itt(
                  subjects, endpoint="vehicle_running_cost_est_last_12m",
                  replays=replays, bootstrap_seed=bootstrap_seed),
              "itt_vehicle_revenue_est_last_12m": cluster_itt(
                  subjects, endpoint="vehicle_revenue_est_last_12m",
                  replays=replays, bootstrap_seed=bootstrap_seed),
              "descriptive_fleet_profit_proxy_last_12m": cluster_itt(subjects,
                     endpoint="line_fleet_profit_12m_proxy", replays=replays, bootstrap_seed=bootstrap_seed),
              "strata_vehicle_operating": {
                  "fleet": {v: cluster_itt([r for r in subjects if r["fleet_class"] == v],
                                endpoint="line_vehicle_operating_profit_last_12m",
                                replays=replays, bootstrap_seed=bootstrap_seed) for v in FLEETS},
                  "saturation": {v: cluster_itt([r for r in subjects if r["saturation"] == v],
                                     endpoint="line_vehicle_operating_profit_last_12m",
                                     replays=replays, bootstrap_seed=bootstrap_seed) for v in SATURATION},
                  "kind": {v: cluster_itt([r for r in subjects if r["kind"] == v],
                               endpoint="line_vehicle_operating_profit_last_12m",
                               replays=replays, bootstrap_seed=bootstrap_seed) for v in KINDS}},
              "strata": {"fleet": _strata(subjects, "fleet_class", FLEETS, replays, bootstrap_seed),
                         "saturation": _strata(subjects, "saturation", SATURATION, replays, bootstrap_seed),
                         "kind": _strata(subjects, "kind", KINDS, replays, bootstrap_seed),
                         "v161_cohort": _strata(subjects, "v161_cohort", ("cold_start", "sampled", "unknown"),
                                                replays, bootstrap_seed)},
              "p50_minus_p0_company_profit_year": None,
              "displaced_investments_verified": None,
              "marginal_physical_roi": None,
              "limits": ["The randomized experiment compares whole-line profits, not physical profit of one airplane.",
                         "Randomization allows arms across seeds; bootstrap resamples complete seed clusters, not episodes.",
                         "Missing outcomes may induce attrition bias; exposure and missingness remain visible.",
                         "NoAI vehicle operating profit excludes infrastructure and replacement depreciation; running costs are prorated estimates, maintenance cannot be split out.",
                         "C66 monthly VEHS profits exclude infrastructure costs and cannot be a net ROI.",
                         "No inferable RAIL displacement without executed-project causal proof.",
                         "p=0 reference requires independent matched company-level records; no cross-run line IDs.",
                         "No V161/C70 coefficient or policy qualifies from this diagnostic."]}
    if include_episodes:
        result["episodes"] = episodes
    return result


def markdown(result):
    expo = result["exposure"]
    primary = result["itt_line_net_profit_last_12m"]
    operating = result["itt_line_vehicle_operating_profit_last_12m"]
    proxy = result["descriptive_fleet_profit_proxy_last_12m"]
    lines = ["# AIR-ROI-RENFORT-1 — randomisation ITT", "",
             f"Affectations p=50 : {expo['randomized_p50']} ({expo['seeds']} graines), "
             f"treatment={expo['assigned'].get('treatment', 0)}, "
             f"deferred={expo['assigned'].get('deferred', 0)} ; "
             f"livraisons déclarées={expo['reported_deliveries_treatment']}.", "",
             "| Mesure | Δ treatment − deferred | IC95 grappes de graines | Graines appariées |",
             "|---|---:|---|---:|",
             f"| Profit net ligne, mois 13–24 | {primary['mean'] if primary['mean'] is not None else 'null'} | "
             f"{primary['ci95_seed_cluster']} | {primary['seeds_with_both_arms']} |",
             f"| Profit d'exploitation des avions de la ligne (sans infrastructure) | {operating['mean'] if operating['mean'] is not None else 'null'} | "
             f"{operating['ci95_seed_cluster']} | {operating['seeds_with_both_arms']} |",
             f"| Profit flotte VEHS (proxy) | {proxy['mean'] if proxy['mean'] is not None else 'null'} | "
             f"{proxy['ci95_seed_cluster']} | {proxy['seeds_with_both_arms']} |", "",
             "Le proxy VEHS exclut l'infrastructure et porte sur des mois civils complets ; "
             "il ne constitue pas le ROI net ni une mesure exacte à t0 + 24 mois.", "",
             "Motifs d'observation mensuelle : " + json.dumps(result["monthly_net_observation"], ensure_ascii=False),
             "Anomalies d'exposition : " + json.dumps(expo["issues"], ensure_ascii=False)]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs", nargs="+", help="logs avec AIRR1_ITT_ASSIGN / OUTCOME")
    parser.add_argument("--telemetry", nargs="*", default=[], help="JSONL C66 --line-telemetry-monthly")
    parser.add_argument("--telemetry-policy-id", help="policy_id du bras p50 dans la télémétrie C66")
    parser.add_argument("--months", nargs="*", default=[], help="JSONL net par épisode/mois, prouvé")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--include-episodes", action="store_true")
    parser.add_argument("--bootstrap-replays", type=int, default=20000)
    parser.add_argument("--bootstrap-seed", type=int, default=0)
    opts = parser.parse_args()
    if opts.bootstrap_replays < 0:
        parser.error("bootstrap-replays must be >= 0")
    logs = paths_from_globs(opts.logs)
    if not logs:
        parser.error("no logs match")
    report = analyze(logs, paths_from_globs(opts.telemetry), paths_from_globs(opts.months),
                     replays=opts.bootstrap_replays, bootstrap_seed=opts.bootstrap_seed,
                     include_episodes=opts.include_episodes,
                     telemetry_policy_id=opts.telemetry_policy_id)
    print(markdown(report) if opts.format == "markdown" else json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
