"""Diagnostic OFF/ON P0 RAIL : exposition au slot A* (aucun contrefactuel).

Les lignes P0_RAIL_BLOCK sont emises une fois par cle OD/cargo/kind et par
objet _railSearch, sous la SONDE ON. Une OD dont la caisse depasse le budget
PREVU n'est ni revalidee ni certifiee constructible. Les trajectoires OFF et
ON ne doivent jamais etre appariees evenement par evenement.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


LOG_NAME = re.compile(r"^p0_rail_block_exposure_shadow_seed(?P<seed>\d+)_r(?P<repeat>\d+)\.log$")
DATE = re.compile(r"\bOPEX (?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2}) P0_RAIL_BLOCK ")
KV = re.compile(r"([a-z_]+)=([^\s]+)")
INTEGER = (
    "self_revisit", "rank", "requested_cargo", "requested_src", "requested_dst",
    "pred_profit", "pred_budget_capital", "pred_construction_capital",
    "cash_available", "blocker_src", "blocker_dst", "blocker_start_date",
    "blocker_age_days", "blocker_start_tick", "blocker_spent", "blocker_budget",
)
REQUIRED = set(INTEGER) | {
    "branch", "result", "dedup", "physical", "requested_kind", "blocker_kind", "blocker_phase"
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decode(line: str, *, seed: int, repeat: int) -> dict | None:
    match = DATE.search(line)
    if not match:
        if "P0_RAIL_BLOCK " in line:
            raise ValueError(f"ligne sonde mal formee : {line[:200]}")
        return None
    fields = dict(KV.findall(line[match.end():]))
    missing = REQUIRED - fields.keys()
    if missing:
        raise ValueError(f"champs absents {sorted(missing)} : {line[:200]}")
    for field in INTEGER:
        fields[field] = int(fields[field])
    for field in ("year", "month", "day"):
        fields[field] = int(match.group(field))
    if fields["result"] != "search_in_progress" or fields["dedup"] != "first":
        raise ValueError("la sonde ne capture pas un refus deduplique")
    if fields["physical"] != "unknown":
        raise ValueError("la sonde n'a pas de garantie de constructibilite")
    if fields["self_revisit"] not in (0, 1):
        raise ValueError("self_revisit inattendu")
    fields["seed"] = seed
    fields["repeat"] = repeat
    return fields


def od(event: dict) -> tuple:
    """Une OD PAX est non orientee ; le fret conserve sa direction."""
    src, dst = event["requested_src"], event["requested_dst"]
    if event["requested_kind"] == "pax":
        src, dst = sorted((src, dst))
    return event["requested_kind"], event["requested_cargo"], src, dst


def quoted_cash_positive(event: dict) -> bool:
    return (event["pred_profit"] > 0
            and event["pred_budget_capital"] > 0
            and event["cash_available"] >= event["pred_budget_capital"])


def annual(events: list[dict], year: int, seed: int) -> dict:
    observations = [e for e in events if e["year"] == year]
    competitors = [e for e in observations if e["self_revisit"] == 0]
    estimated = [e for e in competitors if quoted_cash_positive(e)]
    unique = sorted({od(e) for e in competitors})
    possible = sorted({od(e) for e in estimated})
    per_od_visits = Counter(od(e) for e in competitors)
    return {
        "seed": seed,
        "year": year,
        "dedup_episode_observations": len(observations),
        "self_revisits": len(observations) - len(competitors),
        "distinct_competitor_observations": len(competitors),
        "unique_competitor_od_cargo_kind": len(unique),
        "unique_od_details": [list(x) for x in unique],
        "quote_cash_positive_observations": len(estimated),
        "quote_cash_positive_unique_od": len(possible),
        "quote_cash_positive_od_details": [list(x) for x in possible],
        "quote_cash_positive_rank0_observations": sum(x["rank"] == 0 for x in estimated),
        "competitor_rank0_observations": sum(x["rank"] == 0 for x in competitors),
        "competing_events_repeated_across_episodes": len(competitors) - len(unique),
        "max_visits_for_same_od": max(per_od_visits.values(), default=0),
        "occupants_all": dict(sorted(Counter(
            f"{e['blocker_kind']}/{e['blocker_phase']}" for e in observations).items())),
        "occupants_competing": dict(sorted(Counter(
            f"{e['blocker_kind']}/{e['blocker_phase']}" for e in competitors).items())),
        "branches": dict(sorted(Counter(e["branch"] for e in observations).items())),
        "max_occupant_age_days_when_known": max(
            (e["blocker_age_days"] for e in competitors if e["blocker_age_days"] >= 0),
            default=None),
        "total_cash_above_quote_not_builder_proof": True,
        "geometric_constructibility": "unknown",
        "counterfactual_rail_lines": "not_measured",
    }


def analyze(engine_dir: Path, result_path: Path, manifest_path: Path) -> dict:
    data = json.loads(result_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["comparison"]["effective_differences"]["p0_rail_block_exposure_shadow"] != {
        "candidate": 1, "reference": 0
    }:
        raise ValueError("le seul switch OFF/ON attendu n'est pas present")
    games = data["games"]
    if any(not g["game_ok"] for g in games) or data["failed_runs"]:
        raise ValueError("campagne incomplete/malade")
    seeds = data["seeds"]
    if len(games) != 2 * len(seeds):
        raise ValueError("il manque des parties OFF ou ON")

    file_hashes = {}
    events_by_seed = {}
    for seed in seeds:
        log_path = engine_dir / f"p0_rail_block_exposure_shadow_seed{seed}_r0.log"
        control_path = engine_dir / f"reference_seed{seed}_r0.log"
        for path in (log_path, control_path):
            if not path.is_file():
                raise ValueError(f"journal manque : {path}")
            file_hashes[path.name] = sha256(path)
        if "P0_RAIL_BLOCK " in control_path.read_text(encoding="utf-8", errors="replace"):
            raise ValueError(f"sonde erroneement active en OFF seed {seed}")
        events = []
        for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
            event = decode(line, seed=seed, repeat=0)
            if event:
                events.append(event)
        events_by_seed[seed] = events

    last_year = manifest["configuration"]["starting_year"] + manifest["configuration"]["years"] - 1
    start_year = manifest["configuration"]["starting_year"]
    summaries = [annual(events_by_seed[seed], year, seed) for seed in seeds
                 for year in range(start_year, last_year + 1)]
    differences = {}
    for pair in data["policy_comparison"]["per_pair"]:
        differences[str(pair["seed"])] = {
            str(row["year"]): {
                "probe_on_minus_off_profit_year": row["policy_delta"],
                "off_profit_year": row["reference_opex"],
                "on_profit_year": row["variant_opex"],
            } for row in pair["annual_trajectory"] if row["year"] in (1972, 1973, 1974)
        }

    return {
        "status": "diagnostic_only_not_a_policy_gate",
        "campaign_id": data["campaign_id"],
        "bundle_sha256": data["source_bundle_sha256"],
        "health": {"games_complete": len(games), "failed_runs": len(data["failed_runs"]),
                   "seeds": seeds},
        "source_files_sha256": {"result": sha256(result_path), "manifest": sha256(manifest_path),
                                **dict(sorted(file_hashes.items()))},
        "probe_on_minus_off_annual_accounting_profit_noncausal": differences,
        "annual": summaries,
        "limits": [
            "Sonde ON intrusive: les evenements ON ne s'apparient pas a ceux du bras OFF.",
            "Dedup par cle OD/cargo/kind ET _railSearch transitoire ; plusieurs episodes peuvent compter la meme OD.",
            "self_revisit signale le projet deja dans A* : pas un chantier alternatif perdu.",
            "OpexAvailableCapital >= budgetCapital ne garantit ni cout reel, ni ressources, ni geometrie.",
            "Les controles constructibilite et recherche A* du projet demande n'ont pas ete executes.",
            "Upgrade: origines indicatives sans candidat attache; dates de debut/age souvent indisponibles.",
            "P5_BUILD_LINE mesure seulement les accroissements nets; la telemetrie ne mesure que des services actifs.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    data = analyze(args.engine_dir, args.result, args.manifest)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for row in data["annual"]:
        if row["year"] == 1973:
            print(f"seed={row['seed']} 1973 hits={row['dedup_episode_observations']} "
                  f"other={row['distinct_competitor_observations']} "
                  f"unique={row['unique_competitor_od_cargo_kind']} "
                  f"quoted={row['quote_cash_positive_unique_od']} "
                  f"self={row['self_revisits']}")
    print(f"sauve: {args.out}")


if __name__ == "__main__":
    main()
