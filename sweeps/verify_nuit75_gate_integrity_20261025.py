"""Strict, read-only result and script-health audit for the N75 gate queue.

Checks pair completeness, both companies' health, identical source bundle,
absence of recorded Squirrel errors, and paired seed/policy coverage.
Does not launch Docker, change thresholds, or reinterpret V102 verdicts.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


FATAL_LOG = re.compile(
    r"(?im)^\s*\[E\]|\b(?:squirrel (?:error|exception)|script error|"
    r"unhandled exception|fatal error)\b"
)


def verify(path, expected_seeds, expected_years, *, setting=None, value=None):
    source = Path(path)
    data = json.loads(source.read_text(encoding="utf-8-sig"))
    campaigns = data["policies"]
    policy_ids = {p["id"] for p in campaigns}
    seeds = set(data["seeds"])
    issues = []
    if len(seeds) != expected_seeds or len(data["seeds"]) != expected_seeds:
        issues.append(f"expected {expected_seeds} distinct seeds, got {len(seeds)}")
    if data.get("years") != expected_years:
        issues.append(f"expected {expected_years} years, got {data.get('years')}")
    if data.get("repeats") != 1:
        issues.append("expected one repeat")
    if data.get("start_year") != 1970 or data.get("map_size") != 8:
        issues.append("expected starting year 1970 and 256x256 map")
    if len(policy_ids) != 2 or len(campaigns) != 2:
        issues.append("expected exactly two distinct policy arms")
    if data.get("failed_runs"):
        issues.append(f"failed_runs present: {len(data['failed_runs'])}")
    if len(data["games"]) != expected_seeds * 2:
        issues.append(f"games incomplete: {len(data['games'])}/{expected_seeds * 2}")
    if len(data["summary"]) != expected_seeds * 4:
        issues.append(f"company summary incomplete: {len(data['summary'])}/{expected_seeds * 4}")
    expected_terminal = 1970 + expected_years - 1
    if data.get("expected_last_year") != expected_terminal:
        issues.append("unexpected terminal year")
    rule = data.get("policy_comparison", {}).get("decision_rule", {})
    if (rule.get("rule") != ("gain_short" if expected_years == 5 else "non_erosion")
            or rule.get("min_useful_primary_delta_pct") != 4.0
            or rule.get("value_guard_max_loss_pct") != 5.0
            or rule.get("required_pairs") != expected_seeds):
        issues.append("decision rule, +4% gain or -5% value guard inconsistent")
    if setting is not None:
        configs = {p["role"]: dict(p.get("explicit_settings", [])) for p in campaigns}
        if (configs.get("reference", {}).get(setting) != 0
                or configs.get("variant", {}).get(setting) != value
                or any(v.get("probes") != 2 for v in configs.values())):
            issues.append("experimental OFF/ON intervention or symmetric probes=2 inconsistent")
    expected_keys = {(p, s, 0) for p in policy_ids for s in seeds}
    game_keys = [(g["policy_id"], g["seed"], g["repeat"]) for g in data["games"]]
    if set(game_keys) != expected_keys or any(n != 1 for n in Counter(game_keys).values()):
        issues.append("duplicate or missing policy×seed×repeat game")
    summary_keys = [(r["duel_policy_id"], r["seed"], r["repeat"], r["arm"])
                    for r in data["summary"]]
    expected_summary = {(p, s, 0, a) for p in policy_ids for s in seeds
                        for a in ("OpexAI", "AAAHogEx")}
    if set(summary_keys) != expected_summary or any(n != 1 for n in Counter(summary_keys).values()):
        issues.append("duplicate or missing company summary")
    bundle = data.get("source_bundle_sha256")
    if not bundle:
        issues.append("missing source bundle SHA")
    script_errors = []
    unhealthy_games = []
    for g in data["games"]:
        key = (g["policy_id"], g["seed"], g["repeat"])
        if g.get("source_bundle_sha256") != bundle:
            issues.append(f"different game source bundle: {key}")
        if not g.get("game_ok") or g.get("game_status") != "complete" or g.get("unattributed_errors"):
            unhealthy_games.append(key)
        for company, status in g.get("companies", {}).items():
            if (not status.get("run_ok") or status.get("status") != "complete"
                    or not status.get("horizon_complete") or status.get("failure_reason")):
                unhealthy_games.append((key, company))
        if set(g.get("companies", {})) != {"OpexAI", "AAAHogEx"}:
            unhealthy_games.append((key, "missing company"))
    bad_summaries = []
    for s in data["summary"]:
        key = (s["duel_policy_id"], s["seed"], s["repeat"], s["arm"])
        if s.get("script_errors") or s.get("unattributed_errors"):
            script_errors.append((key, s.get("script_errors"), s.get("unattributed_errors")))
        if (not s.get("run_ok") or not s.get("game_ok")
                or not s.get("horizon_complete") or not s.get("include_in_economic_stats")
                or s.get("failure_reason") or s.get("status") != "complete"
                or s.get("last_year") != expected_terminal
                or s.get("expected_last_year") != expected_terminal
                or s.get("source_bundle_sha256") != bundle):
            bad_summaries.append(key)
    if unhealthy_games:
        issues.append(f"unhealthy games: {unhealthy_games[:10]}")
    if bad_summaries:
        issues.append(f"unhealthy summaries: {bad_summaries[:10]}")
    if script_errors:
        issues.append(f"script errors: {script_errors[:10]}")
    # The game JSON often points at empty per-duel engine logs. Check their
    # presence and any nonempty content, but make that evidentiary limit clear.
    engine_dir = source.parent / (source.stem + "_engine")
    engine_logs = list(engine_dir.glob("*.log")) if engine_dir.is_dir() else []
    expected_logs = {Path(g["engine_log_path"]).name for g in data["games"]}
    if {p.name for p in engine_logs} != expected_logs:
        issues.append("engine log set missing, extra or duplicated")
    nonempty = 0
    fatal_hits = []
    for engine_log in engine_logs:
        if engine_log.stat().st_size:
            nonempty += 1
            with engine_log.open("r", encoding="utf-8", errors="replace") as handle:
                for number, line in enumerate(handle, 1):
                    if FATAL_LOG.search(line):
                        fatal_hits.append((engine_log.name, number, line.strip()[:160]))
                        if len(fatal_hits) >= 10:
                            break
    if fatal_hits:
        issues.append(f"fatal engine messages: {fatal_hits}")
    manifest = source.with_suffix(".manifest.json")
    manifest_ok = False
    if manifest.is_file():
        raw_manifest = manifest.read_bytes()
        manifest_ok = hashlib.sha256(raw_manifest).hexdigest() == data.get("manifest_sha256")
        content = json.loads(raw_manifest)
        config = content.get("configuration", {})
        comparison_config = content.get("comparison", {})
        if (not manifest_ok or content.get("source_bundle", {}).get("sha256") != bundle
                or config.get("seeds") != data.get("seeds")
                or config.get("years") != expected_years or config.get("map_size") != 8
                or config.get("repeats") != 1
                or comparison_config.get("decision_rule", {}).get("rule") != rule.get("rule")):
            issues.append("manifest SHA, bundle, seeds or benchmark rules inconsistent")
        if setting is not None and comparison_config.get("effective_differences") != {
                setting: {"reference": 0, "candidate": value}}:
            issues.append("manifest intervention not isolated to expected setting")
        if setting is not None:
            manifest_policies = {p["role"]: p for p in content.get("policies", [])}
            ref_settings = manifest_policies.get("reference", {}).get("settings", {})
            on_settings = manifest_policies.get("variant", {}).get("settings", {})
            ref_effective = ref_settings.get("effective", {})
            on_effective = on_settings.get("effective", {})
            differences = {key for key in set(ref_effective) | set(on_effective)
                           if ref_effective.get(key) != on_effective.get(key)}
            if (differences != {setting} or ref_effective.get(setting) != 0
                    or on_effective.get(setting) != value
                    or ref_settings.get("defaults", {}).get(setting) != 0
                    or on_settings.get("defaults", {}).get(setting) != 0):
                issues.append("manifest effective policy drift or experimental default changed")
        if content.get("execution", {}).get("options", {}).get("max_workers", 10) > 9:
            issues.append("more than 9 simulation workers requested")
    else:
        issues.append("missing frozen campaign manifest")
    comparison = data.get("policy_comparison", {})
    if comparison.get("complete_pairs") != expected_seeds:
        issues.append(f"complete policy pairs != {expected_seeds}")
    if not comparison.get("comparison_complete"):
        issues.append("policy comparison incomplete")
    if comparison.get("verdict") in ("pass", "fail_primary", "fail_value", "fail_non_erosion"):
        if data.get("expected_last_year") != data.get("start_year", 1970) + expected_years - 1:
            issues.append("wrong expected terminal year")
    return {
        "campaign": data.get("campaign_id"), "bundle": bundle,
        "years": data.get("years"), "seeds": len(seeds),
        "games": len(data["games"]), "company_rows": len(data["summary"]),
        "complete_pairs": comparison.get("complete_pairs"),
        "script_error_count": len(script_errors), "unhealthy_games": len(unhealthy_games),
        "unhealthy_summaries": len(bad_summaries),
        "engine_log_count": len(engine_logs), "nonempty_engine_logs": nonempty,
        "fatal_engine_messages": fatal_hits, "manifest_sha_ok": manifest_ok,
        "verdict": comparison.get("verdict"), "ok": not issues, "issues": issues
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("json_files", nargs="+", type=Path)
    parser.add_argument("--required-seeds", type=int, required=True)
    parser.add_argument("--required-years", type=int, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    reports = [verify(path, args.required_seeds, args.required_years)
               for path in args.json_files]
    encoded = json.dumps(reports, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0 if all(r["ok"] for r in reports) else 2


if __name__ == "__main__":
    raise SystemExit(main())
