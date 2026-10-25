#!/usr/bin/env python3
"""Pre-registered CARTO-1 long-corridor shadow analysis (no game launched).

Usage:
    python sweeps/analyze_carto1_long.py results/carto1_long_engine --format markdown
    python sweeps/analyze_carto1_long.py results/carto1_long_engine --require-complete \
        --format json --out results/carto1_long_analysis.json
    python sweeps/analyze_carto1_long.py results/carto1_long_8y_engine \
        --years 8 --require-complete --format json

Protocol: exactly three independent 1024x1024, >=3-year, r0 games, with
30 deterministic reservoir samples (indices 0..29) per game and >=20 actual
A* failures among the eligible observations. A sampled episode needs SAMPLE, COST,
and terminal ASTAR events with matching sample index and candidate key.
The preregistered horizon is --years N (default 3). Seed IDs remain 42/100/999
and sample sizes remain 30 per seed, INCLUDING at 8 or 10 years. Since seed 42
had only 16 CARTO1_LONG_COST after one year in the smoke, an incomplete 3-year
campaign should be reported as incomplete. To study a longer horizon, start
a fresh campaign with --years 8 or --years 10, and require the matching N-year
JSON/manifest and healthy completed games; do not extrapolate partial samples.
SUMMARY can precede the game's final year and is never proof of the horizon.
Risk score is FIXED before seeing outcomes: route / route_blocks, higher
means more likely to fail. Failure means ABND, DEAD or NOPA; OK is success.
ASTAR started=0 outcome=NOPA site=missing_virtual_endpoint/no_pathfinder is a separate site failure,
excluded from real A* prediction and savings. Actual A* needs started=1.

Train a threshold maximizing Youden's J on the OTHER TWO SEEDS, then score
the held-out seed. Ties select the highest (most conservative) threshold.
Neither predictors nor thresholds are selected on the held-out seed.
One-class AUC/sensitivity/specificity are null, never invented.

Opcode savings are counterfactual *upper bounds*: only correctly predicted
failed A* searches are counted as potentially avoidable. Neither false
positives nor probe timing are assigned a fictional economic value.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
from fractions import Fraction
import gzip
import json
import math
from pathlib import Path
import re


LOG_NAME = re.compile(
    r"^(?P<policy>.+)_seed(?P<seed>\d+)_r(?P<repeat>\d+)\.log(?:\.gz)?$", re.I
)
EVENT = re.compile(
    r"\bOPEX\s+(\d{4}-\d{1,2}-\d{1,2})\s+"
    r"(CARTO1_LONG_(?:SAMPLE|COST|ASTAR|SUMMARY|SAFETY)|RLW04B_ENUM)"
    r"(?:\s+(.*))?$"
)
FIELD = re.compile(r"(?<!\S)([A-Za-z_][A-Za-z0-9_]*)=([^\s]+)")
TAGS = ("CARTO1_LONG_SAMPLE", "CARTO1_LONG_COST", "CARTO1_LONG_ASTAR",
        "CARTO1_LONG_SUMMARY", "CARTO1_LONG_SAFETY", "RLW04B_ENUM")
FAILURES = frozenset(("ABND", "DEAD", "NOPA"))
OUTCOMES = FAILURES | {"OK"}
DEFAULT_SEEDS = (42, 100, 999)
SAMPLES_PER_SEED = 30
MIN_FAILURES = 20


def validate_years(years):
    """Validate a horizon selected before measuring any candidate scores."""
    if type(years) is not int or years < 3:
        raise ValueError("Horizon --years attendu : entier N >= 3")
    return years


def decode_line(line):
    """Accept decorated engine lines, excluding malformed dates and alien tags."""
    match = EVENT.search(line.rstrip())
    if not match:
        return None
    try:
        when = date.fromisoformat("-".join(
            [f"{int(part):0{4 if index == 0 else 2}d}"
             for index, part in enumerate(match[1].split("-"))]
        ))
    except ValueError:
        return None
    return when, match[2], dict(FIELD.findall(match[3] or ""))


def nonnegative(value):
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    return result if result >= 0 else None


def identity(path):
    match = LOG_NAME.fullmatch(Path(path).name)
    if not match:
        raise ValueError(f"Nom de fichier attendu <policy>_seed<N>_r<K>.log[.gz]: {path}")
    return match["policy"], int(match["seed"]), int(match["repeat"])


def _summary_checks(summary, observed_failures, samples, errors):
    if summary is None:
        errors.append("CARTO1_LONG_SUMMARY absent")
        return None
    expected = {"phase": "done", "samples": SAMPLES_PER_SEED,
                "completed": samples, "failures": observed_failures,
                "mapx": 1024, "mapy": 1024}
    for field, value in expected.items():
        actual = summary.get(field) if isinstance(value, str) else nonnegative(summary.get(field))
        if actual != value:
            errors.append(f"SUMMARY {field} attendu {value}, reçu {summary.get(field)!r}")
    map_ops = nonnegative(summary.get("map_ops"))
    if summary.get("map_ops") is not None and map_ops is None:
        errors.append("SUMMARY map_ops invalide")
    if nonnegative(summary.get("search_ops")) is None:
        errors.append("SUMMARY search_ops absent ou invalide")
    overruns = nonnegative(summary.get("overruns"))
    if overruns is None:
        errors.append("SUMMARY overruns absent ou invalide")
    elif overruns:
        errors.append(f"SUMMARY franchissements de tick = {overruns} (exige 0)")
    return map_ops


def parse_game(source, lines):
    """Read one log without joining distinct episodes on src/dst alone."""
    policy, seed, repeat = identity(source)
    counts = Counter()
    events = {}
    summary = None
    enum_done = False
    reservoir_seed = None
    enum_overruns = 0
    enum_ticks = 0
    seen_samples = set()
    seen_costs = set()
    started_astar = False
    first_date = last_date = None
    errors = []
    for line_no, line in enumerate(lines, 1):
        parsed = decode_line(line)
        if parsed is None:
            # An OPEX line naming our tag but malformed is a collection error.
            if any(tag in line for tag in TAGS) and "OPEX " in line:
                errors.append(f"ligne {line_no}: événement CARTO-1/RLW04b illisible")
            continue
        when, tag, fields = parsed
        counts[tag] += 1
        first_date = when if first_date is None else min(first_date, when)
        last_date = when if last_date is None else max(last_date, when)
        if tag == "RLW04B_ENUM":
            if fields.get("phase") == "done":
                enum_done = True
                reservoir_seed = nonnegative(fields.get("sample_seed"))
                enum_overruns = nonnegative(fields.get("overruns"))
                enum_ticks = nonnegative(fields.get("ticks"))
                if enum_overruns is None or enum_ticks is None:
                    errors.append("RLW04B_ENUM phase=done sans compteurs de sécurité")
                elif enum_overruns or enum_ticks:
                    errors.append(
                        f"RLW04B_ENUM tick crossing overruns={enum_overruns} ticks={enum_ticks}"
                    )
            continue
        if tag == "CARTO1_LONG_SUMMARY":
            summary = fields  # The latest snapshot wins.
            continue
        if tag == "CARTO1_LONG_SAFETY":
            errors.append(
                f"ligne {line_no}: arrêt de sécurité shadow : "
                f"{fields.get('reason', 'non_renseignée')}"
            )
            continue
        sample = nonnegative(fields.get("sample"))
        if sample is None or sample >= SAMPLES_PER_SEED:
            errors.append(f"ligne {line_no}: {tag} sample attendu dans 0..29")
            continue
        row = events.setdefault(sample, {})
        if tag == "CARTO1_LONG_SAMPLE":
            if started_astar:
                errors.append(f"ligne {line_no}: SAMPLE postérieur au premier A*")
            seen_samples.add(sample)
        elif tag == "CARTO1_LONG_COST":
            if started_astar:
                errors.append(f"ligne {line_no}: COST postérieur au premier A*")
            seen_costs.add(sample)
        elif tag == "CARTO1_LONG_ASTAR":
            if not started_astar:
                started_astar = True
                if len(seen_samples) != SAMPLES_PER_SEED or len(seen_costs) != SAMPLES_PER_SEED:
                    errors.append(
                        f"ligne {line_no}: A* avant pré-enregistrement complet : "
                        f"SAMPLE={len(seen_samples)} COST={len(seen_costs)} "
                        f"(attendu 30/30)"
                    )
        if tag == "CARTO1_LONG_ASTAR" and fields.get("phase") == "start":
            continue
        if tag == "CARTO1_LONG_ASTAR" and fields.get("phase") != "end":
            errors.append(f"ligne {line_no}: ASTAR sans phase=end/start")
            continue
        slot = tag.removeprefix("CARTO1_LONG_").lower()
        if slot in row:
            errors.append(f"ligne {line_no}: doublon {tag} sample={sample}")
            continue
        row[slot] = fields
    if not enum_done:
        errors.append("RLW04B_ENUM phase=done absent")
    elif reservoir_seed is None:
        errors.append("RLW04B_ENUM phase=done sans sample_seed de réservoir")
    if repeat != 0:
        errors.append(f"répétition r{repeat} inattendue (protocole r0)")
    rows = []
    observed_astar_overruns = 0
    observed_map_ticks = 0
    for sample in range(SAMPLES_PER_SEED):
        parts = events.get(sample, {})
        absent = [name for name in ("sample", "cost", "astar") if name not in parts]
        if absent:
            errors.append(f"sample={sample}: événements absents {','.join(absent)}")
            continue
        base, cost, astar = (parts[name] for name in ("sample", "cost", "astar"))
        key = base.get("key")
        if not key or key.count(":") != 3 or any(
                other.get("key") != key for other in (cost, astar)):
            errors.append(f"sample={sample}: clé absente ou discordante")
            continue
        route = nonnegative(cost.get("route"))
        blocks = nonnegative(cost.get("route_blocks"))
        cost_ops = nonnegative(cost.get("ops"))
        started = astar.get("started")
        site_fail = (started == "0" and astar.get("outcome") == "NOPA"
                     and astar.get("site") in ("missing_virtual_endpoint", "no_pathfinder"))
        search_ops = nonnegative(astar.get("search_ops"))
        iters = nonnegative(astar.get("iters"))
        astar_overruns = nonnegative(astar.get("overruns"))
        map_ticks = nonnegative(cost.get("ticks"))
        outcome = astar.get("outcome")
        distance = nonnegative(base.get("distance"))
        if (cost.get("valid") != "1" or route is None or not blocks
                or cost_ops is None or search_ops is None or iters is None
                or astar_overruns is None or map_ticks is None
                or distance is None or not 224 <= distance <= 288
                or outcome not in OUTCOMES or (started != "1" and not site_fail)):
            errors.append(f"sample={sample}: COST/ASTAR incomplet ou invalide")
            continue
        if site_fail and (search_ops != 0 or iters != 0):
            errors.append(f"sample={sample}: échec de site avec A* ops/iters non nuls")
            continue
        if not site_fail and (search_ops <= 0 or iters <= 0):
            errors.append(f"sample={sample}: A* prétendu réel sans FindPath consommé")
            continue
        observed_astar_overruns += astar_overruns
        observed_map_ticks += map_ticks
        if astar_overruns or map_ticks:
            errors.append(
                f"sample={sample}: franchissement de tick "
                f"astar={astar_overruns} carto={map_ticks}"
            )
        rows.append({
            "sample": sample, "key": key,
            "score": route / blocks, "route": route, "route_blocks": blocks,
            "map_ops": cost_ops, "astar_ops": search_ops, "iters": iters,
            "outcome": outcome, "failed": int(outcome in FAILURES and not site_fail),
            "site_fail": site_fail, "astar_started": not site_fail,
            "astar_overruns": astar_overruns, "map_ticks": map_ticks,
        })
    failures = sum(row["failed"] for row in rows)
    site_failures = sum(row["site_fail"] for row in rows)
    map_ops = _summary_checks(summary, failures + site_failures, len(rows), errors)
    sampled_map_ops = sum(row["map_ops"] for row in rows)
    observed_search_ops = sum(row["astar_ops"] for row in rows)
    if summary:
        if nonnegative(summary.get("costs")) != SAMPLES_PER_SEED:
            errors.append("SUMMARY costs différent des 30 épisodes attendus")
        if nonnegative(summary.get("cap")) != 5000:
            errors.append("SUMMARY cap différent du budget A* pré-enregistré 5000")
        if map_ops is not None and len(rows) == SAMPLES_PER_SEED and map_ops != sampled_map_ops:
            errors.append("SUMMARY map_ops discordant avec les COST individuels")
        if (len(rows) == SAMPLES_PER_SEED
                and nonnegative(summary.get("search_ops")) != observed_search_ops):
            errors.append("SUMMARY search_ops discordant avec les ASTAR individuels")
    if (summary and summary.get("sample_seed") is not None
            and nonnegative(summary.get("sample_seed")) != reservoir_seed):
        errors.append("SUMMARY sample_seed différent de RLW04B_ENUM")
    if len(rows) != SAMPLES_PER_SEED:
        errors.append(f"échantillons valides {len(rows)}/{SAMPLES_PER_SEED}")
    return {
        "source": str(source), "policy": policy, "seed": seed, "repeat": repeat,
        "events": {tag: counts[tag] for tag in TAGS},
        "first_event_date": first_date.isoformat() if first_date else None,
        "last_event_date": last_date.isoformat() if last_date else None,
        "summary": summary, "enum_done": enum_done, "reservoir_seed": reservoir_seed,
        "samples": len(rows), "failures": failures,
        "successes": sum(not row["failed"] for row in rows if row["astar_started"]),
        "site_failures": site_failures,
        "astar_overruns": observed_astar_overruns,
        "map_ticks": observed_map_ticks,
        "enum_overruns": enum_overruns,
        "enum_ticks": enum_ticks,
        "map_ops": map_ops if map_ops is not None else sampled_map_ops,
        "map_ops_scope": "all_probe" if map_ops is not None else "sample_only",
        "sample_map_ops": sampled_map_ops,
        "astar_ops": observed_search_ops,
        "rows": rows, "errors": errors,
        "complete": not errors,
    }


def confusion(rows, threshold):
    """Binary decision score >= threshold; undefined rates stay null."""
    tp = fp = tn = fn = 0
    for row in rows:
        predicted = row["score"] >= threshold
        if row["failed"]:
            tp += bool(predicted)
            fn += not predicted
        else:
            fp += bool(predicted)
            tn += not predicted
    positives, negatives = tp + fn, tn + fp
    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "sensitivity": tp / positives if positives else None,
        "specificity": tn / negatives if negatives else None,
    }


def auc(rows):
    """Tie-corrected pairwise ROC AUC; undefined for either absent class."""
    pos = [row["score"] for row in rows if row["failed"]]
    neg = [row["score"] for row in rows if not row["failed"]]
    if not pos or not neg:
        return None
    correct = sum(2 * (p > n) + (p == n) for p in pos for n in neg)
    return correct / (2 * len(pos) * len(neg))


def train_threshold(rows):
    """All unique thresholds plus predict-none, max Youden J, tie: highest."""
    positives = sum(row["failed"] for row in rows)
    negatives = len(rows) - positives
    if not positives or not negatives:
        return None
    scores = sorted(set(row["score"] for row in rows), reverse=True)
    thresholds = [math.nextafter(scores[0], math.inf), *scores]
    winner = None
    best = None
    for threshold in thresholds:
        result = confusion(rows, threshold)
        j = Fraction(result["tp"], positives) - Fraction(result["fp"], negatives)
        if best is None or j > best:
            best = j
            winner = threshold
    return winner


def _fold(seed, train, test, map_ops):
    threshold = train_threshold(train)
    result = {
        "test_seed": seed, "train_seeds": sorted({row["seed"] for row in train}),
        "train_n": len(train), "test_n": len(test),
        "train_failures": sum(row["failed"] for row in train),
        "test_failures": sum(row["failed"] for row in test),
        "threshold": threshold, "auc": auc(test),
        "confusion": confusion(test, threshold) if threshold is not None else None,
        "cartography_ops": map_ops,
        "potential_astar_ops_saved": None, "potential_net_ops": None,
    }
    if threshold is not None and map_ops is not None:
        saved = sum(row["astar_ops"] for row in test
                    if row["failed"] and row["score"] >= threshold)
        result["potential_astar_ops_saved"] = saved
        result["potential_net_ops"] = saved - map_ops
    return result


def analyze_sources(sources, *, seeds=DEFAULT_SEEDS, years=3):
    """Analyze (filename, lines) streams, preserving policy and seed boundaries."""
    years = validate_years(years)
    seeds = tuple(seeds)
    if seeds != DEFAULT_SEEDS:
        raise ValueError("Graines pré-enregistrées obligatoires : 42 100 999")
    games = {}
    for source, lines in sources:
        game = parse_game(source, lines)
        key = game["policy"], game["seed"]
        if key in games:
            # Never silently pick a replay or merge samples from two games.
            games[key]["errors"].append(f"fichier dupliqué pour policy/seed: {source}")
            games[key]["complete"] = False
        else:
            games[key] = game
    result = {"protocol": {
        "seeds": list(seeds), "years": years, "map": "1024x1024",
        "samples_per_seed": SAMPLES_PER_SEED, "min_failures_pooled": MIN_FAILURES,
        "predictor": "route / route_blocks", "positive_outcomes": sorted(FAILURES),
        "threshold": "maximum train-only Youden J; ties choose highest cutoff; score >= cutoff",
        "horizon_verified_from_logs": False,
        "horizon_caveat": (
            "CARTO1_LONG_SUMMARY can be emitted before the end of the game. "
            "Confirm the requested N-year horizon and 1024 map in the harness manifest/game results; "
            "the log independently verifies map dimensions only."
        ),
    }, "policies": {}}
    for policy in sorted({name for name, _ in games}):
        selected = [games.get((policy, seed)) for seed in seeds]
        found = [game for game in selected if game is not None]
        errors = [f"graine {seed} absente" for seed, game in zip(seeds, selected) if game is None]
        extras = sorted(seed for name, seed in games if name == policy and seed not in seeds)
        if extras:
            errors.append(f"graines hors protocole: {extras}")
        for game in found:
            errors.extend(f"graine {game['seed']}: {error}" for error in game["errors"])
        sampled_rows = [
            {**row, "seed": game["seed"]} for game in found for row in game["rows"]
        ]
        valid_rows = [row for row in sampled_rows if row["astar_started"]]
        failures = sum(row["failed"] for row in valid_rows)
        if failures < MIN_FAILURES:
            errors.append(f"échecs réels {failures}/{MIN_FAILURES} minimum")
        data_complete = not errors and len(sampled_rows) == len(seeds) * SAMPLES_PER_SEED
        folds = []
        if data_complete:
            for seed, game in zip(seeds, selected):
                train = [row for row in valid_rows if row["seed"] != seed]
                test = [row for row in valid_rows if row["seed"] == seed]
                folds.append(_fold(seed, train, test, game["map_ops"]))
        protocol_complete = data_complete and all(
            fold["threshold"] is not None for fold in folds
        )
        if data_complete and not protocol_complete:
            errors.append("Au moins un entraînement à deux graines n'a qu'une classe")
        pooled_confusion = None
        potential_saved = potential_net = None
        if protocol_complete:
            pooled_confusion = {
                name: sum(fold["confusion"][name] for fold in folds)
                for name in ("tp", "fp", "tn", "fn")
            }
            positives = pooled_confusion["tp"] + pooled_confusion["fn"]
            negatives = pooled_confusion["tn"] + pooled_confusion["fp"]
            pooled_confusion["sensitivity"] = (
                pooled_confusion["tp"] / positives if positives else None
            )
            pooled_confusion["specificity"] = (
                pooled_confusion["tn"] / negatives if negatives else None
            )
            potential_saved = sum(fold["potential_astar_ops_saved"] for fold in folds)
            potential_net = sum(fold["potential_net_ops"] for fold in folds)
        # Completude du protocole != preuve de prediction tenue a l'ecart.
        # Refuser aussi un fold sans les deux classes et un gain d'opcodes
        # theorique non positif (carte prise integralement en compte).
        scope_is_full = all(game["map_ops_scope"] == "all_probe" for game in found)
        predictive_validated = bool(
            protocol_complete and scope_is_full and potential_net is not None
            and potential_net > 0 and pooled_confusion is not None
            and pooled_confusion["tp"] > 0 and pooled_confusion["tn"] > 0
            and all(fold["auc"] is not None and fold["auc"] > 0.5 for fold in folds)
        )
        result["policies"][policy] = {
            "complete": bool(protocol_complete), "data_complete": data_complete,
            "predictive_validated": predictive_validated,
            "campaign_verified": False,
            "errors": errors,
            "games": found, "samples": len(sampled_rows),
            "real_astar": len(valid_rows),
            "site_failures": len(sampled_rows) - len(valid_rows),
            "failures": failures, "successes": len(valid_rows) - failures,
            "pooled_auc": auc(valid_rows) if data_complete else None,
            "folds": folds, "out_of_fold_confusion": pooled_confusion,
            "cartography_ops": (sum(game["map_ops"] for game in found)
                                if data_complete else None),
            "cartography_ops_scope": (
                "all_probe" if data_complete and all(
                    game["map_ops_scope"] == "all_probe" for game in found)
                else "sample_only_or_missing"
            ),
            "potential_astar_ops_saved": potential_saved,
            "potential_net_ops": potential_net,
            "opcode_interpretation": (
                "Hypothetical upper bound: summed real A* search_ops on correctly "
                "flagged failures minus observed cartography map_ops. In absence of "
                "SUMMARY map_ops, the latter covers sampled COST only; full probe "
                "overhead is unknown. Site failures (started=0) are excluded. "
                "False positives and perturbation of game timing have no assigned economic value."
            ),
        }
    if not result["policies"]:
        raise ValueError("Aucune politique dans les journaux")
    return result


def validate_campaign(report, result_json, manifest_json):
    """Check runtime game scope using the harness, never invent years from SUMMARY.

    This is separate from statistical completeness so synthetic log fixtures can
    test the estimator on their own. Production --require-complete requires both.
    """
    config = manifest_json.get("configuration", {})
    execution = manifest_json.get("execution", {})
    options = execution.get("options", {})
    games = result_json.get("games", [])
    years = validate_years(report["protocol"]["years"])
    errors = []
    if options.get("reference") != "OpexAI[probes=50331650]":
        errors.append("politique/probes du manifeste ≠ OpexAI[probes=50331650]")
    if options.get("script_debug") is not True:
        errors.append("script_debug absent du manifeste")
    if not options.get("docker_image_id"):
        errors.append("empreinte image Docker absente du manifeste")
    if not manifest_json.get("git", {}).get("sha"):
        errors.append("SHA Git absent du manifeste")
    if result_json.get("campaign_id") != manifest_json.get("campaign_id"):
        errors.append("campaign_id JSON/manifeste divergent")
    if result_json.get("years") != years or config.get("years") != years:
        errors.append(f"horizon harnais ≠ {years} ans pré-enregistrés")
    if result_json.get("map_size") != 10 or config.get("map_size") != 10:
        errors.append("map_size harnais ≠ 10 (1024²)")
    if result_json.get("repeats") != 1 or config.get("repeats") != 1:
        errors.append("repeats harnais ≠ 1")
    if result_json.get("seeds") != report["protocol"]["seeds"] or (
            config.get("seeds") != report["protocol"]["seeds"]):
        errors.append("graines JSON/manifeste ≠ graines pré-enregistrées")
    start = result_json.get("start_year")
    if type(start) is not int or result_json.get("expected_last_year") != start + years - 1:
        errors.append("année de fin attendue du résultat incohérente")
    if config.get("starting_year") != start:
        errors.append("année de début JSON/manifeste divergente")
    for name, policy in report["policies"].items():
        issues = list(errors)
        by_seed = {}
        for game in games:
            if game.get("policy_id") != name:
                continue
            key = (game.get("seed"), game.get("repeat"))
            if key in by_seed:
                issues.append(f"partie dupliquée dans JSON : {key}")
            by_seed[key] = game
        if len(by_seed) != 3:
            issues.append(f"parties de la politique {name} : {len(by_seed)}/3")
        for parsed in policy["games"]:
            seed = parsed["seed"]
            game = by_seed.get((seed, 0))
            if game is None:
                issues.append(f"JSON sans partie {name}/seed{seed}/r0")
                continue
            if (game.get("game_status") != "complete" or game.get("game_ok") is not True
                    or game.get("unattributed_errors")
                    or not game.get("companies", {}).get("OpexAI", {}).get("horizon_complete")):
                issues.append(f"partie {seed} non saine/à horizon incomplet")
            if (Path(game.get("engine_log_path") or "").name
                    != Path(parsed["source"]).name.removesuffix(".gz")):
                issues.append(f"journal déclaré du jeu {seed} discordant")
            if type(start) is int:
                for field in ("first_event_date", "last_event_date"):
                    stamp = parsed[field]
                    if stamp and not start <= int(stamp[:4]) <= start + years - 1:
                        issues.append(f"événement {field} hors des {years} ans pour {seed}")
        manifest_games = {
            (game.get("policy_id"), game.get("seed"), game.get("repeat"))
            for game in manifest_json.get("games", [])
        }
        for seed in report["protocol"]["seeds"]:
            if (name, seed, 0) not in manifest_games:
                issues.append(f"manifeste sans jeu {name}/seed{seed}/r0")
        policy["campaign_verified"] = not issues
        policy["campaign_errors"] = issues
        policy["complete"] = policy["complete"] and not issues
        policy["predictive_validated"] = policy["predictive_validated"] and not issues
    report["protocol"]["horizon_verified_from_logs"] = False
    report["protocol"]["campaign_scope_evidence"] = {
        "result_campaign_id": result_json.get("campaign_id"),
        "manifest_campaign_id": manifest_json.get("campaign_id"),
        "expected_years": years, "result_years": result_json.get("years"),
        "manifest_years": config.get("years"),
        "expected_last_year": start + years - 1 if type(start) is int else None,
        "result_expected_last_year": result_json.get("expected_last_year"),
        "map_size_log2": result_json.get("map_size"),
        "starting_year": start,
    }
    return report


def _open_log(path):
    if path.name.endswith(".log.gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("rt", encoding="utf-8", errors="replace")


def find_logs(inputs, policy=None):
    matches = {}
    for raw in inputs:
        path = Path(raw)
        if not path.exists():
            raise FileNotFoundError(path)
        candidates = path.iterdir() if path.is_dir() else (path,)
        for candidate in candidates:
            if not candidate.is_file() or not LOG_NAME.fullmatch(candidate.name):
                continue
            if policy is not None and identity(candidate)[0] != policy:
                continue
            matches[str(candidate.resolve())] = candidate
    if not matches:
        raise ValueError("Aucun journal <policy>_seed<N>_r<K>.log[.gz] trouvé")
    return [matches[key] for key in sorted(matches)]


def analyze_paths(inputs, *, policy=None, seeds=DEFAULT_SEEDS, years=3,
                  result_json=None, manifest_json=None):
    def sources():
        for path in find_logs(inputs, policy):
            with _open_log(path) as log:
                yield path, log
    report = analyze_sources(sources(), seeds=seeds, years=years)
    inputs = [Path(path) for path in inputs]
    if len(inputs) == 1 and inputs[0].is_dir() and inputs[0].name.endswith("_engine"):
        base = inputs[0].parent / inputs[0].name[:-len("_engine")]
        if result_json is None:
            result_json = base.with_suffix(".json")
        if manifest_json is None:
            manifest_json = base.with_suffix(".manifest.json")
    if result_json is not None and manifest_json is not None and (
            Path(result_json).is_file() and Path(manifest_json).is_file()):
        result = json.loads(Path(result_json).read_text(encoding="utf-8"))
        manifest = json.loads(Path(manifest_json).read_text(encoding="utf-8"))
        validate_campaign(report, result, manifest)
    return report


def _number(value):
    return "indéfini" if value is None else f"{value:.4f}" if isinstance(value, float) else str(value)


def render_markdown(report):
    lines = ["# CARTO-1 LONG — qualification prédictive hors graine", "",
             f"Horizon pré-enregistré : {report['protocol']['years']} ans ; "
             "30 échantillons par graine 42/100/999, au moins 20 échecs A* réels.",
             "Score fixé : coût route / nombre de blocs ; score élevé = risque d'échec.",
             "Seuil Youden ajusté uniquement sur les deux autres graines.", ""]
    for name, policy in report["policies"].items():
        lines += [f"## {name}", "",
                  f"**Complet :** {policy['complete']} ; "
                  f"**prédiction hors graine qualifiée :** {policy['predictive_validated']} ; échantillons "
                  f"{policy['samples']}/90 ; A* réels {policy['real_astar']} ; "
                  f"échecs de site exclus {policy['site_failures']} ; "
                  f"échecs A* {policy['failures']} "
                  f"(minimum 20). Vérification campagne : "
                  f"{policy['campaign_verified']}.", "",
                  "| Graine test | Entraînement | Seuil | AUC test | TP | FP | TN | FN | Sensibilité | Spécificité | Carte ops | A* évitables ops |",
                  "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for fold in policy["folds"]:
            c = fold["confusion"] or {}
            lines.append(
                f"| {fold['test_seed']} | {','.join(map(str, fold['train_seeds']))} | "
                f"{_number(fold['threshold'])} | {_number(fold['auc'])} | "
                + " | ".join(_number(c.get(field)) for field in (
                    "tp", "fp", "tn", "fn", "sensitivity", "specificity"))
                + f" | {_number(fold['cartography_ops'])} | "
                  f"{_number(fold['potential_astar_ops_saved'])} |"
            )
        lines += ["", f"AUC poolée descriptive : {_number(policy['pooled_auc'])}. "
                  f"Confusion hors graine : {policy['out_of_fold_confusion'] or 'indéfinie'}.",
                  f"Carte ({policy['cartography_ops_scope']}) : "
                  f"{_number(policy['cartography_ops'])} ops ; A* potentiellement "
                  f"évitables : {_number(policy['potential_astar_ops_saved'])} ops ; "
                  f"solde théorique : {_number(policy['potential_net_ops'])} ops.",
                  policy["opcode_interpretation"], ""]
        if policy["errors"]:
            lines += ["**Incomplétude :**", *[f"- {error}" for error in policy["errors"]], ""]
        if policy.get("campaign_errors"):
            lines += ["**Écarts du harnais :**",
                      *[f"- {error}" for error in policy["campaign_errors"]], ""]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path, help="Journaux .log/.log.gz ou dossiers")
    parser.add_argument("--policy", help="Restreindre à une politique")
    parser.add_argument("--result-json", type=Path,
                        help="Résultat JSON du harnais; automatique depuis dossier *_engine")
    parser.add_argument("--manifest", type=Path,
                        help="Manifeste JSON du harnais; automatique depuis dossier *_engine")
    parser.add_argument("--seeds", nargs=3, type=int, default=DEFAULT_SEEDS,
                        metavar=("SEED_A", "SEED_B", "SEED_C"),
                        help="Graines pré-enregistrées : 42 100 999 (non modifiables)")
    parser.add_argument("--years", type=int, default=3, metavar="N",
                        help="Horizon pré-enregistré N >= 3 (défaut 3 ; extension possible 8/10)")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--out", type=Path, help="Chemin de rapport (défaut stdout)")
    parser.add_argument("--require-complete", action="store_true",
                        help="Code de sortie 1 si protocole incomplet")
    args = parser.parse_args(argv)
    try:
        report = analyze_paths(args.inputs, policy=args.policy, seeds=args.seeds,
                               years=args.years,
                               result_json=args.result_json, manifest_json=args.manifest)
    except (ValueError, FileNotFoundError, OSError) as exc:
        parser.error(str(exc))
    output = (json.dumps(report, ensure_ascii=False, indent=2) + "\n"
              if args.format == "json" else render_markdown(report))
    if args.out:
        args.out.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    if args.require_complete and not all(
            policy["complete"] and policy["campaign_verified"]
            for policy in report["policies"].values()):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
