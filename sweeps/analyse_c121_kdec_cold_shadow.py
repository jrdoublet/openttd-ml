"""Decode C121 cold K_dec logs referenced by a frozen duel campaign.

Counts are candidate/pass occurrences, never independent economic samples.
Identical messages on successive selections must not be deduplicated. The
engine timestamp is wall time: only explicit in-game year/month/day are used.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import statistics
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVENT = re.compile(r"\[0\]\s+\[I\]\s+(C121_KDEC_COLD_(?:SHADOW|SUMMARY|FUNDED))\s+(.*)$")
COUNTS = ("cold", "warm", "affected", "rank_up", "entered", "head_flip")


def parse_event(raw):
    match = EVENT.search(raw)
    if not match:
        return None
    fields = {}
    for token in match[2].split():
        key, value = token.split("=", 1)
        try:
            fields[key] = int(value)
        except ValueError:
            try:
                fields[key] = float(value)
            except ValueError:
                fields[key] = value
    fields["kind"] = match[1].removeprefix("C121_KDEC_COLD_")
    # Never infer the game date from a neighbouring event or PC timestamp.
    fields["date"] = date(fields["year"], fields["month"], fields["day"]).isoformat()
    return fields


def distribution(values):
    values = sorted(values)
    if not values:
        return {"n": 0, "mean": None, "median": None, "min": None, "max": None,
                "p25": None, "p75": None}
    quartiles = statistics.quantiles(values, n=4, method="inclusive") if len(values) > 1 else values * 3
    return {"n": len(values), "mean": statistics.mean(values), "median": statistics.median(values),
            "min": values[0], "max": values[-1], "p25": quartiles[0], "p75": quartiles[2]}


def counts(rows):
    out = {key: 0 for key in COUNTS}
    for row in rows:
        cold = row["samples"] <= 0
        if row["state"] != ("cold" if cold else "warm"):
            raise ValueError("state/samples mismatch")
        changed = cold and row["cold_denom"] != row["denom"]
        up = changed and row["cold_rank"] >= 0 and (row["rank"] < 0 or row["cold_rank"] < row["rank"])
        entered = changed and row["rank"] < 0 <= row["cold_rank"]
        flip = changed and row["rank"] != 0 and row["cold_rank"] == 0
        if row["affected"] != int(changed) or row["head_flip"] != int(flip):
            raise ValueError("candidate flag/denominator/rank mismatch")
        for key, value in zip(COUNTS, (cold, not cold, changed, up, entered, flip)):
            out[key] += int(value)
    return out


def decode_log(path):
    pending, passes, candidates, funded = [], [], [], []
    with path.open(encoding="utf-8", errors="strict") as stream:
        for number, raw in enumerate(stream, 1):
            try:
                event = parse_event(raw)
                if event is None:
                    continue
                event["log_line"] = number
                if event["kind"] == "SHADOW":
                    pending.append(event)
                elif event["kind"] == "FUNDED":
                    if event["added"] <= 0:
                        raise ValueError("funded without addition")
                    funded.append(event)
                else:
                    measured = counts(pending)
                    if any(event[key] != measured[key] for key in COUNTS):
                        raise ValueError("summary/candidates mismatch")
                    if any(row["date"] != event["date"] for row in pending):
                        raise ValueError("selection dates mismatch")
                    index = len(passes)
                    for row in pending:
                        row["selection"] = index
                    candidates.extend(pending)
                    passes.append(event)
                    pending = []
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"{path}:{number}: {exc}") from exc
    if pending:
        raise ValueError(f"{path}: unfinished selection")
    return passes, candidates, funded


def group_report(passes, candidates):
    result = {"selections": len(passes), **{key: sum(row[key] for row in passes) for key in COUNTS}}
    result["cold_lines"] = len({row["line"] for row in candidates if row["samples"] <= 0})
    result["warm_lines"] = len({row["line"] for row in candidates if row["samples"] > 0})
    result["score_ratio"] = distribution(row["cold_score"] / row["score"] for row in candidates
        if row["affected"] and row["score"] != 0)
    result["affected_zero_score"] = sum(row["affected"] and row["score"] == 0 for row in candidates)
    # Original head mode, for selections where a cold candidate displaces it.
    result["head_mode"] = dict(Counter(row["head_mode"] for row in passes if row["head_flip"] > 0))
    result["head_flip_selections"] = sum(row["head_flip"] > 0 for row in passes)
    return result


def resolve_log(raw, root):
    if raw.startswith("/work/"):
        return root / raw.removeprefix("/work/")
    path = Path(raw)
    return path if path.is_absolute() else root / path


def analyse_campaign(campaign_path, policy_id=None, root=ROOT):
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    policy_id = policy_id or (campaign.get("policy_comparison") or {}).get("variant_policy_id") or campaign["policy_id"]
    games = [game for game in campaign["games"] if game["policy_id"] == policy_id]
    expected_games = len(campaign["seeds"]) * campaign["repeats"]
    by_game, by_year, by_line, provenance = [], [], [], []
    all_passes, all_candidates = [], []
    seen = set()
    for game in games:
        identity = (game["seed"], game["repeat"])
        if identity in seen:
            raise ValueError(f"duplicate game {identity}")
        seen.add(identity)
        path = resolve_log(game["engine_log_path"], root)
        passes, candidates, funded = decode_log(path)
        if not passes:
            raise ValueError(f"{path}: no shadow summaries (setting/debug not exposed)")
        label = {"seed": game["seed"], "repeat": game["repeat"]}
        by_game.append({**label, **group_report(passes, candidates)})
        last_year = campaign["expected_last_year"]
        for year in range(last_year - campaign["years"] + 1, last_year + 1):
            by_year.append({**label, "year": year, **group_report(
                [row for row in passes if row["year"] == year],
                [row for row in candidates if row["year"] == year])})
        for line_id in sorted({row["line"] for row in candidates}):
            rows = [row for row in candidates if row["line"] == line_id]
            additions = [row for row in funded if row["line"] == line_id]
            by_line.append({**label, "line": line_id,
                "cold_passes": len({row["selection"] for row in rows if row["samples"] <= 0}),
                "affected_passes": len({row["selection"] for row in rows if row["affected"]}),
                "first_seen": rows[0]["date"], "last_seen": rows[-1]["date"],
                "first_funded_date": min((row["date"] for row in additions), default=None),
                "funded_additions": sum(row["added"] for row in additions)})
        all_passes.extend(passes)
        all_candidates.extend(candidates)
        with path.open("rb") as stream:
            log_hash = hashlib.file_digest(stream, "sha256").hexdigest()
        provenance.append({**label, "path": game["engine_log_path"], "bytes": path.stat().st_size,
                           "sha256": log_hash})
    summary = group_report(all_passes, all_candidates)
    # Unique line IDs are scoped to each game, not to the whole campaign.
    for key in ("cold_lines", "warm_lines"):
        summary[key] = sum(row[key] for row in by_game)
    years = expected_games * campaign["years"]
    healthy = len(games) == expected_games and all(game.get("game_ok") is True for game in games)
    complete = healthy and len(seen) == expected_games and {seed for seed, _ in seen} == set(campaign["seeds"])
    head_seeds = sorted({row["seed"] for row in by_game if row["head_flip"] > 0})
    gate = "non_validated"
    diagnostic = len(campaign["seeds"]) == 5 and campaign["years"] == 6 and campaign["repeats"] == 1
    if complete and not diagnostic:
        gate = "short_sample"
    elif complete:
        if summary["head_flip"] == 0 and summary["entered"] <= 2:
            gate = "negligible"
        elif len(head_seeds) >= 3 or summary["entered"] >= years:
            gate = "material"
        else:
            gate = "intermediate"
    return {"schema": "c121-kdec-cold-shadow-v1", "campaign": campaign["campaign_id"],
            "campaign_sha256": hashlib.sha256(campaign_path.read_bytes()).hexdigest(),
            "bundle_sha256": campaign["source_bundle_sha256"], "policy_id": policy_id,
            "coverage": {"games_expected": expected_games, "games_obtained": len(games),
                         "party_years_expected": years, "complete_healthy": complete},
            "exposure_gate": gate, "head_flip_seeds": head_seeds,
            "entered_per_party_year": summary["entered"] / years,
            "summary": summary, "by_seed": by_game, "by_seed_year": by_year,
            "by_line": by_line, "engine_logs": provenance,
            "economic_interpretation": "Opcode-perturbed shadow; economic delta is not causal."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path, nargs="?")
    parser.add_argument("--policy-id")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        suite = unittest.defaultTestLoader.discover(str(ROOT / "sweeps"), pattern="test_analyse_c121_kdec_cold_shadow.py")
        raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
    if args.campaign is None:
        parser.error("campaign is required")
    result = analyse_campaign(args.campaign, args.policy_id)
    output = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        if args.out.exists():
            raise FileExistsError(args.out)
        args.out.write_text(output, encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("coverage", "exposure_gate", "summary")}, indent=2))


if __name__ == "__main__":
    main()
