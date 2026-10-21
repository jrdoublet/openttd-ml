#!/usr/bin/env python3
"""V307R : exposition et criteres structurels sur les bancs deja executes.

Usage : python sweeps/diag_v307r_exposition.py [--root DIR] [--campaign NAME]
        [--abnd] [--json OUT]

Par defaut, chaque campagne V307R du checkout propre est analysee separement.
Les seuils pre-enregistres (+50 % de reussite des jonctions, -40 % de
SITEAB+ABND, aucune baisse des lignes neuves) ne sont evaluables que sur deux
bras complets et exposes ; les smokes restent descriptifs. Les events V307R_SITE
ne sont pas des constructions. Les profits de RAIL_BUILD sont *predits*, seuls
les profits finaux de la synthese du banc sont presentes comme realises.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import re
import statistics


ROOT = Path(__file__).resolve().parents[1] / "results/v307r_bench_clean_20261021/results"
LOG_RE = re.compile(r"^(?P<arm>.+)_seed(?P<seed>\d+)_r(?P<repeat>\d+)\.log(?:\.gz)?$")
EVENT_RE = re.compile(r"\bOPEX\s+(?P<date>\d{4}-\d{1,2}-\d{1,2})\s+"
                      r"(?P<tag>V307R_SITE|V307R_DROP|RAIL_ATTEMPT|RAIL_BUILD|RAIL_BUILD_FAIL)\s+(?P<fields>.*)$")
FIELD_RE = re.compile(r"\b([a-zA-Z_][a-zA-Z_0-9]*)=([^\s]+)")
ERROR_RE = re.compile(r"\[0\]\s+\[S\]\s+Your script made an error")
EXPECTED_REASONS = ("OK", "SITEAB", "SITEA", "SITEB", "ABND")


def integer(record, key, default=None):
    try:
        return int(record[key])
    except (KeyError, TypeError, ValueError):
        return default


def percentile(values, percent):
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * percent / 100
    lo = int(index)
    hi = min(lo + 1, len(ordered) - 1)
    return round(ordered[lo] + (ordered[hi] - ordered[lo]) * (index - lo), 1)


def ratio_change(current, reference):
    """A zero reference is not an infinite % uplift: the ratio is undefined."""
    return round(100.0 * (current / reference - 1), 2) if reference > 0 else None


def parse_log(path):
    """An OpexAI script log only; preserve each event, including repeated attempts."""
    matcher = LOG_RE.match(path.name)
    if matcher is None:
        raise ValueError(f"Nom de journal inattendu: {path}")
    arm, seed, repeat = matcher.group("arm"), int(matcher.group("seed")), int(matcher.group("repeat"))
    events = defaultdict(list)
    fatal = 0
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, 1):
            if ERROR_RE.search(line):
                fatal += 1
            match = EVENT_RE.search(line)
            if not match:
                continue
            fields = dict(FIELD_RE.findall(match.group("fields")))
            fields.update(date=match.group("date"), arm=arm, seed=seed, repeat=repeat)
            # Les dates du jeu ont une resolution d'un jour : le numero de ligne
            # distingue plusieurs sites/tentatives sur la meme paire ce jour-la.
            fields["_log_line"] = line_number
            events[match.group("tag")].append(fields)
    return {"arm": arm, "seed": seed, "repeat": repeat,
            "events": events, "fatal_errors": fatal, "source": str(path)}


def log_files(directory):
    if not directory.is_dir():
        return []
    found = sorted(p for p in directory.iterdir()
                   if p.is_file() and LOG_RE.match(p.name))
    duplicates = Counter(LOG_RE.match(path.name).groups() for path in found)
    if any(n > 1 for n in duplicates.values()):
        raise ValueError(f"Journaux .log et .log.gz dupliques: {directory}")
    return found


def arm_events(records):
    """Sum events and keep arm and seed ownership for paired comparisons."""
    attempts = [x for p in records for x in p["events"].get("RAIL_ATTEMPT", [])]
    builds = [x for p in records for x in p["events"].get("RAIL_BUILD", [])]
    sites = [x for p in records for x in p["events"].get("V307R_SITE", [])]
    drops = [x for p in records for x in p["events"].get("V307R_DROP", [])]
    reason = Counter(x.get("reason", "MISSING") for x in attempts)
    attempt_shared = [x for x in attempts if integer(x, "shared_dest") == 1]
    build_shared = [x for x in builds if integer(x, "shared_dest") == 1]
    attempt_join = [x for x in attempts if integer(x, "shared_dest") == 1 and x.get("join_end") == "B"]
    build_join = [x for x in builds if integer(x, "shared_dest") == 1 and x.get("join_end") == "B"]
    filtered = [x for x in sites if integer(x, "before") is not None and integer(x, "after") is not None]
    ops = [integer(x, "ops") for x in sites if integer(x, "ops") is not None]
    fallback = sum(integer(x, "fallback") == 1 for x in sites)
    reduced = sum(integer(x, "after") < integer(x, "before") for x in filtered)
    unchanged = sum(integer(x, "after") == integer(x, "before") for x in filtered)
    invalid = len(sites) - len(filtered) + sum(integer(x, "after") > integer(x, "before") for x in filtered)
    attempts_missing = sum("ok" not in a or "reason" not in a for a in attempts)
    attempts_inconsistent = sum((a.get("ok") == "1") != (a.get("reason") in ("OK", "-", ""))
                                for a in attempts if a.get("ok") in ("0", "1") and "reason" in a)
    return {
        "logs": len(records), "script_errors": sum(p["fatal_errors"] for p in records),
        "site_calls": len(sites), "room_drops": len(drops),
        "site_before_sum": sum(integer(s, "before", 0) for s in filtered),
        "site_after_sum": sum(integer(s, "after", 0) for s in filtered),
        "site_before_median": percentile([integer(s, "before") for s in filtered], 50),
        "site_after_median": percentile([integer(s, "after") for s in filtered], 50),
        "site_reduced": reduced, "site_unchanged": unchanged,
        "site_fallback": fallback, "site_invalid": invalid,
        "site_bits": dict(Counter(integer(s, "bit", -1) for s in sites)),
        "site_ops_total": sum(ops), "site_ops_median": percentile(ops, 50),
        "site_ops_p90": percentile(ops, 90),
        "attempts": len(attempts), "attempts_ok": sum(a.get("ok") == "1" for a in attempts),
        "attempts_shared": len(attempt_shared),
        "attempts_shared_ok": sum(a.get("ok") == "1" for a in attempt_shared),
        "attempts_join_B": len(attempt_join),
        "attempts_join_B_ok": sum(a.get("ok") == "1" for a in attempt_join),
        "attempt_missing_fields": attempts_missing,
        "attempt_inconsistent_ok_reason": attempts_inconsistent,
        "reasons": dict(reason), "shared_reasons": dict(Counter(a.get("reason", "MISSING") for a in attempt_shared)),
        "abnd_siteab": reason["ABND"] + reason["SITEAB"],
        "abnd_siteab_per_attempt": (reason["ABND"] + reason["SITEAB"]) / len(attempts) if attempts else None,
        "builds": len(builds),
        "new_lines": len(builds) - len(build_shared),
        "shared_lines": len(build_shared), "joins_B": len(build_join),
        "build_fail": sum(len(p["events"].get("RAIL_BUILD_FAIL", [])) for p in records),
        "predicted_profit_annual_sum": sum(integer(b, "pred_profit", 0) for b in builds),
        "built_line_ids": len({(b["seed"], b["repeat"], b.get("line")) for b in builds}),
    }


def summarize_results(report):
    """Read the *OpexAI* final checkpoint from each duel, never AAAHogEx."""
    if report is None:
        return {}, "json_missing"
    metrics = {}
    for row in report.get("summary", []):
        if row.get("arm") != "OpexAI" or row.get("company_slot") != 0:
            continue
        policy = row.get("duel_policy_id", row.get("policy_id"))
        key = (policy, row.get("seed"), row.get("repeat"))
        if key in metrics:
            raise ValueError(f"Duplicata OpexAI dans le JSON: {key}")
        metrics[key] = {"profit_year": row.get("profit_year"),
                        "company_value": row.get("company_value"),
                        "profit_year_coverage": row.get("profit_year_coverage"),
                        "status": row.get("status"),
                        "horizon_complete": row.get("horizon_complete"),
                        "game_ok": row.get("game_ok")}
    return metrics, "ok" if metrics else "opex_summary_missing"


def paired_metrics(metrics, refs, variants):
    pairs = []
    for seed, repeat in sorted(set(refs) & set(variants)):
        a = metrics.get((refs[(seed, repeat)]["arm"], seed, repeat))
        b = metrics.get((variants[(seed, repeat)]["arm"], seed, repeat))
        if a is None or b is None:
            pairs.append({"seed": seed, "repeat": repeat, "profit_year_delta": None,
                          "company_value_delta": None, "complete_profit_year": False})
            continue
        good = all(m["game_ok"] and m["horizon_complete"] and m["status"] == "complete"
                   and m["profit_year_coverage"] == "complete" and m["profit_year"] is not None
                   for m in (a, b))
        pairs.append({"seed": seed, "repeat": repeat,
                      "profit_year_delta": b["profit_year"] - a["profit_year"] if good else None,
                      "company_value_delta": b["company_value"] - a["company_value"]
                      if a["company_value"] is not None and b["company_value"] is not None else None,
                      "complete_profit_year": good, "reference": a, "variant": b})
    deltas = [p["profit_year_delta"] for p in pairs if p["profit_year_delta"] is not None]
    values = [p["company_value_delta"] for p in pairs if p["company_value_delta"] is not None]
    return {"pairs": pairs, "profit_year_n": len(deltas),
            "profit_year_delta_mean": statistics.mean(deltas) if deltas else None,
            "profit_year_delta_median": statistics.median(deltas) if deltas else None,
            "company_value_delta_mean": statistics.mean(values) if values else None}


def evaluate(ref, var, expected_pairs, actual_pairs, complete, long_horizon):
    """Three *pre-registered* structural criteria, without posthoc replacement."""
    # Un appel avec fallback=1 n'a conserve que les plans historiques, donc il
    # ne constitue pas une exposition du nouveau choix. Un candidat filtre mais
    # qui conserve les 12 plans reste expose : les plans portent la reservation.
    exposed = var["site_calls"] > var.get("site_fallback", 0)
    both_valid = (complete and long_horizon and actual_pairs == expected_pairs and expected_pairs > 0
                  and ref["logs"] == var["logs"] == expected_pairs
                  and not ref["script_errors"] and not var["script_errors"]
                  and not ref["attempt_missing_fields"] and not var["attempt_missing_fields"]
                  and not ref["attempt_inconsistent_ok_reason"] and not var["attempt_inconsistent_ok_reason"])
    junction_rate_ref = ref["attempts_join_B_ok"] / ref["attempts_join_B"] if ref["attempts_join_B"] else None
    junction_rate_var = var["attempts_join_B_ok"] / var["attempts_join_B"] if var["attempts_join_B"] else None
    junction_count_delta_pct = ratio_change(var["joins_B"], ref["joins_B"])
    failure_delta_pct = ratio_change(var["abnd_siteab"], ref["abnd_siteab"])
    failure_rate_delta_pct = ratio_change(var["abnd_siteab_per_attempt"], ref["abnd_siteab_per_attempt"]) if (ref["abnd_siteab_per_attempt"] is not None and var["abnd_siteab_per_attempt"] is not None) else None
    junction_rate_delta_pct = ratio_change(junction_rate_var, junction_rate_ref) if (junction_rate_ref is not None and junction_rate_var is not None) else None
    def criterion(can_evaluate, ok):
        if not both_valid or not exposed or not can_evaluate:
            return "not_evaluable"
        return "pass" if ok else "fail"
    criteria = {
        "join_success_plus_50pct": criterion(junction_rate_delta_pct is not None,
                                               junction_rate_delta_pct is not None and junction_rate_delta_pct >= 50),
        "siteab_abnd_minus_40pct": criterion(failure_delta_pct is not None,
                                              failure_delta_pct is not None and failure_delta_pct <= -40),
        "new_lines_no_loss": criterion(ref["attempts"] > 0 and var["attempts"] > 0,
                                       var["new_lines"] >= ref["new_lines"]),
    }
    return {
        "complete_for_structural_criteria": both_valid,
        "exposed": exposed, "site_filter_effective": var["site_reduced"] > 0,
        "site_opportunities": var["site_calls"],
        "site_effective_calls": var["site_calls"] - var.get("site_fallback", 0),
        "join_success_rate_reference": junction_rate_ref,
        "join_success_rate_variant": junction_rate_var,
        "join_success_rate_delta_pct": junction_rate_delta_pct,
        "join_success_count_delta_pct": junction_count_delta_pct,
        "siteab_abnd_count_delta_pct": failure_delta_pct,
        "siteab_abnd_rate_delta_pct": failure_rate_delta_pct,
        "new_lines_delta": var["new_lines"] - ref["new_lines"],
        "criteria": criteria,
        "verdict": ("all_pass" if all(c == "pass" for c in criteria.values())
                    else "not_evaluable" if "not_evaluable" in criteria.values() else "fail"),
        "limits": (["no_V307R_SITE" if not var["site_calls"] else "only_fallback_sites"]
                   if not exposed else [])
                  + ([] if both_valid else ["incomplete_or_smoke_or_script_error"])
                  + (["no_baseline_successful_join"] if junction_rate_ref in (None, 0) else [])
                  + (["no_baseline_SITEAB_ABND"] if ref["abnd_siteab"] == 0 else []),
    }


def abnd_autopsy(refs, variants):
    """Associe chaque ABND au dernier SITE de sa paire *avant* la tentative.

    L'appariement ne traverse jamais une graine, repetition, bras ou campagne.
    Une meme paire peut etre retentee : ne pas dedupliquer ses evenements ABND.
    """
    details = []
    reference_abnd_pairs = set()
    variant_abnd_pairs = set()
    reference_abnd_events = 0
    reference_details = []
    by_seed = defaultdict(Counter)

    for seed, repeat in sorted(refs.keys() & variants.keys()):
        reference_attempts = defaultdict(list)
        variant_attempts = defaultdict(list)
        for attempt in variants[(seed, repeat)]["events"].get("RAIL_ATTEMPT", []):
            variant_attempts[(attempt.get("src"), attempt.get("dst"))].append(attempt)
        for attempt in refs[(seed, repeat)]["events"].get("RAIL_ATTEMPT", []):
            pair = (attempt.get("src"), attempt.get("dst"))
            reference_attempts[pair].append(attempt)
            if attempt.get("reason") == "ABND":
                reference_abnd_events += 1
                reference_abnd_pairs.add((seed, repeat, *pair))
                counterpart = Counter(a.get("reason", "MISSING") for a in variant_attempts.get(pair, []))
                reference_details.append({
                    "seed": seed, "repeat": repeat, "date": attempt.get("date"),
                    "src": pair[0], "dst": pair[1],
                    "variant_reasons_same_pair": dict(sorted(counterpart.items())),
                })

        events = variants[(seed, repeat)]["events"]
        stream = ([(site["_log_line"], "site", site) for site in events.get("V307R_SITE", [])]
                  + [(attempt["_log_line"], "attempt", attempt)
                     for attempt in events.get("RAIL_ATTEMPT", [])])
        stream.sort(key=lambda item: item[0])
        preceding_site = {}
        attempts_after_site = Counter()
        for _, tag, event in stream:
            pair = (event.get("src"), event.get("dst"))
            if tag == "site":
                if None not in pair:
                    preceding_site[pair] = event
                    attempts_after_site[pair] = 0
                continue

            site = preceding_site.get(pair) if None not in pair else None
            if event.get("reason") == "ABND":
                before = integer(site, "before") if site is not None else None
                after = integer(site, "after") if site is not None else None
                fallback = integer(site, "fallback") if site is not None else None
                if site is None:
                    category = "no_site"
                elif fallback == 0 and before is not None and after is not None and after < before:
                    category = "filtered"
                elif fallback == 1 or (before is not None and after == before):
                    category = "unfiltered"
                else:
                    # Format anormal ou champ manque : aucune cause imputee.
                    category = "invalid_site"

                same_reference = reference_attempts.get(pair, [])
                reasons = Counter(a.get("reason", "MISSING") for a in same_reference)
                detail = {
                    "seed": seed, "repeat": repeat, "date": event.get("date"),
                    "src": pair[0], "dst": pair[1], "attempt_log_line": event["_log_line"],
                    "kind": event.get("kind"), "shared_dest": integer(event, "shared_dest"),
                    "join_end": event.get("join_end"), "iters": integer(event, "iters"),
                    "classification": category,
                    "site_date": site.get("date") if site is not None else None,
                    "site_log_line": site["_log_line"] if site is not None else None,
                    "before": before, "after": after, "fallback": fallback,
                    "bit": integer(site, "bit") if site is not None else None,
                    "intervening_same_pair_attempts": attempts_after_site[pair] if site is not None else None,
                    "reference_attempts_same_pair": len(same_reference),
                    "reference_reasons_same_pair": dict(sorted(reasons.items())),
                    "reference_abnd_same_pair": reasons["ABND"],
                }
                details.append(detail)
                variant_abnd_pairs.add((seed, repeat, *pair))
                by_seed[(seed, repeat)][category] += 1
            if site is not None:
                attempts_after_site[pair] += 1

    classification = Counter(d["classification"] for d in details)
    types = Counter((d["classification"], d["kind"], d["shared_dest"]) for d in details)
    shared_abnd_pairs = reference_abnd_pairs & variant_abnd_pairs
    return {
        "scope": "paired_seed_repeat_only",
        "reference_abnd_events": reference_abnd_events,
        "reference_distinct_abnd_pairs": len(reference_abnd_pairs),
        "variant_abnd_events": len(details),
        "variant_distinct_abnd_pairs": len(variant_abnd_pairs),
        "classification": {k: classification[k] for k in ("filtered", "unfiltered", "no_site", "invalid_site")},
        "class_by_kind_shared": [{"classification": category, "kind": kind,
                                  "shared_dest": shared, "count": count}
                                 for (category, kind, shared), count in sorted(
                                     types.items(), key=lambda item: tuple(str(x) for x in item[0]))],
        "per_seed": [{"seed": seed, "repeat": repeat, "counts": dict(counts)}
                     for (seed, repeat), counts in sorted(by_seed.items())],
        "reference_abnd_same_pairs": len(shared_abnd_pairs),
        "reference_abnd_events_on_variant_pairs": sum(
            1 for seed, repeat in sorted(refs.keys() & variants.keys())
            for a in refs[(seed, repeat)]["events"].get("RAIL_ATTEMPT", [])
            if a.get("reason") == "ABND" and (seed, repeat, a.get("src"), a.get("dst")) in variant_abnd_pairs),
        "variant_events_with_reference_abnd": sum(d["reference_abnd_same_pair"] > 0 for d in details),
        "variant_events_with_reference_attempt": sum(d["reference_attempts_same_pair"] > 0 for d in details),
        "variant_events_reusing_site": sum((d["intervening_same_pair_attempts"] or 0) > 0 for d in details),
        "shared_abnd_pair_keys": [{"seed": seed, "repeat": repeat, "src": src, "dst": dst}
                                  for seed, repeat, src, dst in sorted(
                                      shared_abnd_pairs, key=lambda key: tuple(str(x) for x in key))],
        "conclusion": "indeterminate" if details else "not_applicable_no_abnd",
        "causal_limit": ("'filtered' rend (a) possible sans exclure (b); 'unfiltered' "
                         "ecarte (a) direct pour ce candidat; 'no_site' ne documente "
                         "aucune intervention V307R directe (notamment pax et shared_dest=1). "
                         "Une variation de trajectoire peut aussi expliquer les ecarts "
                         "et aucun site ne prouve a lui seul un blocage A*."),
        "reference_details": reference_details,
        "details": details,
    }


def analyze_campaign(directory, campaign, *, results_dir=None, abnd=False):
    results_dir = results_dir or directory.parent
    paths = log_files(directory)
    files = {p: parse_log(p) for p in paths}
    report_path = results_dir / f"{campaign}.json"
    manifest_path = results_dir / f"{campaign}.manifest.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else None
    policies = report.get("policies", []) if report else []
    ref_ids = [p["id"] for p in policies if p.get("role") == "reference"]
    var_ids = [p["id"] for p in policies if p.get("role") == "variant"]
    if not ref_ids or not var_ids:
        comparison = (manifest or {}).get("comparison", {})
        observed_arms = {entry["arm"] for entry in files.values()}
        ref_ids = ref_ids or [comparison.get("reference_policy_id") or "reference"]
        other_arms = sorted(observed_arms - set(ref_ids))
        var_ids = var_ids or [comparison.get("variant_policy_id")
                              or (other_arms[0] if len(other_arms) == 1 else "variant")]
    ref_id, var_id = ref_ids[0], var_ids[0]
    refs = {(p["seed"], p["repeat"]): p for p in files.values() if p["arm"] == ref_id}
    variants = {(p["seed"], p["repeat"]): p for p in files.values() if p["arm"] == var_id}
    expected_pairs = ((report or {}).get("seeds", []) or (manifest or {}).get("configuration", {}).get("seeds", []))
    expected_repeats = (report or {}).get("repeats", (manifest or {}).get("configuration", {}).get("repeats", 0))
    expected = len(expected_pairs) * expected_repeats
    actual = len(refs.keys() & variants.keys())
    metrics, status = summarize_results(report)
    pairing = paired_metrics(metrics, refs, variants)
    games = (report or {}).get("games", [])
    games_complete = bool(games) and len(games) == expected * 2 and all(
        g.get("game_ok") and g.get("game_status") == "complete" for g in games)
    protocol = (report or {}).get("policy_comparison", {})
    # Le 3x10 est une porte *structurelle* autonome : le protocole economique
    # de 40 paires doit rester diagnostic_only sans rendre ce 3x10 incomplet.
    comparison_complete = all(protocol.get(k, True)
                              for k in ("comparison_complete", "metric_coverage_complete"))
    diffs = (manifest or {}).get("comparison", {}).get("effective_differences")
    config_valid = (diffs is None or (set(diffs) == {"v307_sink_room"}
                    and diffs["v307_sink_room"].get("reference") == 0
                    and diffs["v307_sink_room"].get("candidate") in range(1, 16)))
    bundle_matches = not (report and manifest) or (
        report.get("source_bundle_sha256") == manifest.get("source_bundle", {}).get("sha256"))
    years = (report or {}).get("years") or (manifest or {}).get("configuration", {}).get("years", 0)
    complete = (bool(report) and games_complete and actual == expected and expected > 0
                and len(metrics) == expected * 2 and config_valid and bundle_matches and comparison_complete)
    paired_keys = sorted(refs.keys() & variants.keys())
    # Pendant un 3x10 inacheve, le premier bras d'une nouvelle graine peut deja
    # exister sans son temoin. Ne jamais calculer un delta de volumes sur 2 vs 1.
    reference = arm_events([refs[k] for k in paired_keys])
    variant = arm_events([variants[k] for k in paired_keys])
    reference_observed = arm_events(list(refs.values()))
    variant_observed = arm_events(list(variants.values()))
    result = {
        "campaign": campaign, "manifest": str(manifest_path) if manifest_path.is_file() else None,
        "source_bundle_sha256": (report or {}).get("source_bundle_sha256")
                                or (manifest or {}).get("source_bundle", {}).get("sha256"),
        "git_sha": (manifest or {}).get("git", {}).get("sha"),
        "git_dirty": (manifest or {}).get("git", {}).get("dirty"),
        "policies": {"reference": ref_id, "variant": var_id},
        "settings": (manifest or {}).get("comparison", {}).get("effective_differences", {}),
        "years": years, "expected_pairs": expected, "actual_pairs": actual,
        "logs_found": len(files), "complete": complete, "json_status": status,
        "reference": reference, "variant": variant,
        "unpaired_observed": {"reference": reference_observed, "variant": variant_observed},
        "counts_scope": "paired_seed_repeat_only",
        "economics": pairing,
        "health": {"games_complete": games_complete, "comparison_complete": comparison_complete,
                   "config_valid": config_valid, "bundle_matches": bundle_matches,
                   "missing_reference_logs": sorted(set(variants) - set(refs)),
                   "missing_variant_logs": sorted(set(refs) - set(variants))},
    }
    comparison = (report or {}).get("policy_comparison", {})
    aggregate = comparison.get("aggregates", {})
    result["economics"]["policy_verdict"] = comparison.get("verdict")
    for metric in ("profit_year", "company_value"):
        published = aggregate.get(metric, {}).get("policy_delta", {})
        result["economics"][metric + "_bootstrap_95pct_ci"] = published.get("mean_bootstrap_95pct_ci")
        result["economics"][metric + "_wilcoxon_p"] = published.get("wilcoxon_p")
    result["evaluation"] = evaluate(reference, variant, expected, actual, complete, years >= 10)
    if abnd:
        result["abnd"] = abnd_autopsy(refs, variants)
    return result


def discover(root, campaign=None):
    if campaign:
        return [(campaign, root / (campaign + "_engine"))]
    dirs = sorted(p for p in root.iterdir() if p.is_dir() and p.name.startswith("v307r_")
                  and p.name.endswith("_engine")) if root.is_dir() else []
    return [(p.name[:-7], p) for p in dirs]


def display(row, *, show_abnd=False):
    r, v, e = row["reference"], row["variant"], row["evaluation"]
    print(f"\n# {row['campaign']} ({row['years']} an(s), {row['actual_pairs']}/{row['expected_pairs']} "
          f"paires, complete={row['complete']}, git={row['git_sha']}, bundle={row['source_bundle_sha256']})")
    print("Comptages sur les graines/repetitions avec deux logs apparis seulement; "
          "les journaux d'une graine encore en cours sont exclus des deltas.")
    print("| Bras | Logs appariees | V307R_SITE | V307R_DROP | before/after | reduced/fallback | ops med/p90 | "
          "RAIL_ATTEMPT | OK | SITEAB | ABND | join B OK/essais | RAIL_BUILD | neuves | jonctions B |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for name, a in (("reference", r), ("variant", v)):
        print(f"| {name} | {a['logs']} | {a['site_calls']} | {a['room_drops']} | "
              f"{a['site_before_sum']}/{a['site_after_sum']} "
              f"| {a['site_reduced']}/{a['site_fallback']} | {a['site_ops_median']}/{a['site_ops_p90']} "
              f"| {a['attempts']} | {a['attempts_ok']} | {a['reasons'].get('SITEAB', 0)} "
              f"| {a['reasons'].get('ABND', 0)} | {a['attempts_join_B_ok']}/{a['attempts_join_B']} "
              f"| {a['builds']} | {a['new_lines']} | {a['joins_B']} |")
    for name, a in (("reference", r), ("variant", v)):
        shared = a["shared_reasons"]
        print(f"  {name} shared_dest=1: RAIL_ATTEMPT={a['attempts_shared']}, "
              f"OK={a['attempts_shared_ok']}, SITEAB={shared.get('SITEAB', 0)}, "
              f"ABND={shared.get('ABND', 0)}; script_errors={a['script_errors']}, "
              f"site_ops_total={a['site_ops_total']}")
    pending_ref = row["unpaired_observed"]["reference"]["logs"] - r["logs"]
    pending_var = row["unpaired_observed"]["variant"]["logs"] - v["logs"]
    if pending_ref or pending_var:
        print(f"  Logs encore non appariees: reference={pending_ref}, variante={pending_var}")
    print(f"  Exposition effective={e['exposed']} ({e['site_effective_calls']} appels "
          f"avec plans reserves; filtre reduit={e['site_filter_effective']}), "
          f"jonctions reussies {e['join_success_rate_delta_pct']}%, "
          f"SITEAB+ABND comptes {e['siteab_abnd_count_delta_pct']}%, "
          f"taux {e['siteab_abnd_rate_delta_pct']}%, lignes neuves delta={e['new_lines_delta']}")
    print(f"  Criteres: {e['criteria']} => {e['verdict']}; limites={e['limits']}")
    eco = row["economics"]
    print(f"  profit_year delta moyenne sur {eco['profit_year_n']} paires a 4 trimestres: "
          f"{eco['profit_year_delta_mean']}; bootstrap IC95={eco['profit_year_bootstrap_95pct_ci']}; "
          f"company_value delta moyenne={eco['company_value_delta_mean']}; "
          f"bootstrap IC95={eco['company_value_bootstrap_95pct_ci']}; "
          f"banc_economique={eco['policy_verdict']}")
    if show_abnd:
        a = row["abnd"]
        print(f"  ABND: temoin={a['reference_abnd_events']} sur {a['reference_distinct_abnd_pairs']} "
              f"paires, variante={a['variant_abnd_events']} sur {a['variant_distinct_abnd_pairs']} "
              f"paires ; classes={a['classification']}")
        print(f"  Meme paire ABND dans les deux bras: {a['reference_abnd_same_pairs']} paires; "
              f"ABND variante avec ABND temoin={a['variant_events_with_reference_abnd']}, "
              f"avec une tentative temoin quelconque={a['variant_events_with_reference_attempt']}; "
              f"V307R_SITE reutilise apres une autre tentative={a['variant_events_reusing_site']}")
        print(f"  ABND par classe, type, destination partagee: {a['class_by_kind_shared']}")
        print("  ABND du temoin par paire (et autres essais de la variante sur cette paire):")
        for d in a["reference_details"]:
            print(f"    seed={d['seed']} date={d['date']} src={d['src']} dst={d['dst']} "
                  f"variante={d['variant_reasons_same_pair'] or 'aucune tentative'}")
        print("| Graine | Date ABND | src/dst | classe | V307R_SITE precedent | before -> after | "
              "fallback | essais intermediaires | raisons temoin (meme paire) |")
        print("|---:|---|---|---|---|---|---:|---:|---|")
        for d in a["details"]:
            before_after = f"{d['before']} -> {d['after']}" if d["before"] is not None else "-"
            reason = ", ".join(f"{k}:{n}" for k, n in d["reference_reasons_same_pair"].items()) or "aucune"
            print(f"| {d['seed']} | {d['date']} | {d['src']}/{d['dst']} | {d['classification']} "
                  f"| {d['site_date'] or '-'} | {before_after} | "
                  f"{d['fallback'] if d['fallback'] is not None else '-'} | "
                  f"{d['intervening_same_pair_attempts'] if d['site_date'] else '-'} | {reason} |")
        print(f"  Conclusion causale: {a['conclusion']}. {a['causal_limit']}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT, help="Dossier results/ des campagnes V307R")
    p.add_argument("--campaign", help="ID d'une seule campagne (avec _engine)")
    p.add_argument("--abnd", action="store_true",
                   help="Autopsie ABND des variantes : dernier V307R_SITE precedent et appariement temoin")
    p.add_argument("--json", type=Path, help="Sauver l'analyse complete en JSON")
    args = p.parse_args()
    campaigns = discover(args.root, args.campaign)
    if not campaigns:
        print(f"Aucune campagne V307R avec journaux moteur dans {args.root}")
        return 2
    output = []
    for campaign, folder in campaigns:
        row = analyze_campaign(folder, campaign, results_dir=args.root, abnd=args.abnd)
        display(row, show_abnd=args.abnd)
        output.append(row)
    if args.json:
        args.json.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
