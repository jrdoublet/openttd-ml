"""Audit offline AIR-LOAD: refus de flotte et reliquat du vivier existant.

Réutilise le décodeur des journaux de décision; ne lance jamais de partie.
Les sommes de remaining sont des livres-clichés, pas des dépenses ni des
livres uniques. TASK est paresseux et PROJECT_DISCARD partiellement journalisé:
un bloc de rejets observable n'est pas un recensement de toutes les passes.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

from analyse_rail_freight_dlog import decode_line
from campaign_freeze import fingerprint_tree, sha256_file as digest
from parse_air_finance_margin import parse_log_filename


OWNER = re.compile(r"\[script:\d+\]\s+\[(\d+)\]")
PERIODS = ("1970", "1971", "1972", "1972-12")
CATEGORIES = ("pool_sum_covers_budget", "no_candidate",
              "unaffordable_candidate", "no_extra_candidate", "other_unresolved")
FROZEN_FILES = ("task_projects.nut", "scheduler_tasks.nut", "projects_update.nut",
                "projects_selection.nut", "projects_rank_log.nut", "probes.nut",
                "task_air.nut", "settings.nut", "globals_pre.nut", "persist.nut")
COUNT_TAGS = {"VIVIER", "FLEET_PROJECT", "AIR_FLEET", "PROJECT_DISCARD",
              "PROJECT_CHOSEN", "AIR_BUILD", "RAIL_BUILD", "ROAD_BUILD",
              "PORTFOLIO_RANK", "V217_RAIL_REFILL", "V217_RAIL_SKIP", "V269"}


def classify_vivier(fields):
    """Partition du reliquat observé, sans interpréter selected comme engagé.

    Le classement contient des projets individuellement finançables. Leur
    capital total peut dépasser le budget: remaining=0 ne prouve aucun achat.
    next_capital=-1 seul ne prouve pas que tous les candidats sont sélectionnés.
    """
    row = {key: int(fields[key]) for key in (
        "budget", "selection_pool_capital", "remaining", "next_capital",
        "considered", "selected", "rejected")}
    if (min(row[k] for k in ("budget", "selection_pool_capital", "remaining",
                            "considered", "selected", "rejected")) < 0
            or row["selected"] + row["rejected"] != row["considered"]
            or row["remaining"] != max(0, row["budget"] - row["selection_pool_capital"])):
        raise ValueError(f"VIVIER incohérent: {fields}")
    if row["remaining"] == 0:
        category = "pool_sum_covers_budget"
    elif row["considered"] == 0:
        category = "no_candidate"
    elif row["next_capital"] > row["budget"]:
        category = "unaffordable_candidate"
    elif row["selected"] == row["considered"]:
        category = "no_extra_candidate"
    else:
        category = "other_unresolved"
    return dict(row, category=category)


def summarise_vivier(rows):
    categories = {}
    for category in CATEGORIES:
        subset = [r for r in rows if r["category"] == category]
        categories[category] = {
            "snapshots": len(subset),
            "remaining_pound_snapshots": sum(r["remaining"] for r in subset),
        }
    total = sum(r["remaining"] for r in rows)
    assert total == sum(r["remaining_pound_snapshots"] for r in categories.values())
    return {
        "snapshots": len(rows),
        "positive_remaining_snapshots": sum(r["remaining"] > 0 for r in rows),
        "budget_mean": sum(r["budget"] for r in rows) / len(rows) if rows else None,
        "remaining_mean": total / len(rows) if rows else None,
        "remaining_pound_snapshots": total,
        "top64_snapshots": sum(r["selected"] == 64 for r in rows),
        "all_candidates_selected_snapshots": sum(r["rejected"] == 0 for r in rows),
        "positive_remaining_with_fleet": (sum(r["remaining"] > 0 and r["modes"]["fleet"] > 0
            for r in rows) if all("modes" in r for r in rows) else None),
        "categories": categories,
    }


def analyse_log(lines, source):
    meta = parse_log_filename(source)
    counts, reasons, chosen = Counter(), Counter(), Counter()
    vivier, fleet_blocks, december_events = [], [], []
    block = []

    def flush_block():
        if any(r["fields"].get("mode") == "fleet" for r in block):
            fleet_blocks.append(list(block))
        block.clear()

    for number, line in enumerate(lines, 1):
        owner = OWNER.search(line)
        if owner and owner[1] != "0":
            continue
        decoded = decode_line(line)
        if decoded is None:
            continue
        year, month, day, tag, fields = decoded
        if year not in (1970, 1971, 1972):
            continue
        date = f"{year:04}-{month:02}-{day:02}"
        event = {"source": source, "log_line": number, "date": date,
                 "tag": tag, "fields": fields}
        if tag in COUNT_TAGS:
            counts[f"{year}/{tag}"] += 1
        if tag in ("PROJECT_DISCARD", "AIR_FLEET", "FLEET_PROJECT"):
            reasons[f"{year}/{tag}/{fields.get('mode', '-')}/"
                    f"{fields.get('reason', '-')}/{fields.get('action', '-')}"] += 1
        if tag == "PROJECT_CHOSEN":
            chosen[fields["mode"]] += 1
        if tag == "PROJECT_DISCARD":
            # TASK, y compris deux TASK le même jour, sépare les blocs.
            block.append(event)
        else:
            flush_block()
        if tag == "VIVIER":
            row = classify_vivier(fields)
            row.update(source=source, log_line=number, date=date, path=fields["path"])
            vivier.append(row)
        if tag == "VIVIER_MIX":
            modes = {k: int(fields[k]) for k in ("rail", "road", "air", "water", "total")}
            modes["fleet"] = modes["total"] - sum(modes[k] for k in ("rail", "road", "air", "water"))
            # MIX porte candidateGroups brut, considered les alternatives filtrées.
            # L'API peut aussi franchir minuit entre ces deux journaux.
            if (not vivier or "modes" in vivier[-1]
                    or min(modes.values()) < 0):
                raise ValueError(f"VIVIER_MIX sans sélection concordante: {event}")
            vivier[-1]["modes"] = modes
        if year == 1972 and month == 12 and tag in (
                "V217_RAIL", "V217_RAIL_SKIP", "V217_RAIL_REFILL", "PROJECT_CHOSEN",
                "RAIL_BUILD", "AIR_BUILD", "ROAD_BUILD", "PROJECT_DISCARD"):
            december_events.append(event)
    flush_block()
    fleet_events = [r for b in fleet_blocks for r in b if r["fields"].get("mode") == "fleet"]
    return {
        **meta, "event_counts": dict(sorted(counts.items())),
        "refusal_counts": dict(sorted(reasons.items())), "chosen_attempts": dict(chosen),
        "fleet_discard_events": len(fleet_events),
        "observed_low_load_discard_events": sum(
            r["fields"].get("reason") == "low_load_factor" for r in fleet_events),
        "observed_low_load_fleet_project_refusals": sum(n for k, n in reasons.items()
            if "/FLEET_PROJECT/" in k and k.endswith("/low_load_factor/refuse")),
        "fleet_discard_blocks": len(fleet_blocks),
        "fleet_head_discard_blocks": sum(any(r["fields"].get("mode") == "fleet"
            and r["fields"].get("rank") == "0" for r in b) for b in fleet_blocks),
        "blocks_with_later_higher_rank_discard": sum(any(
            r["log_line"] > f["log_line"] and int(r["fields"]["rank"]) > int(f["fields"]["rank"])
            for f in b if f["fields"].get("mode") == "fleet" for r in b) for b in fleet_blocks),
        "fleet_discard_blocks_detail": fleet_blocks,
        "december_events": december_events,
        "vivier": vivier,
    }


def verify_frozen_files(bundle, manifest):
    expected = {r["path"]: r["sha256"] for r in manifest["sources"]["OpexAI"]["files"]}
    checked = {}
    for name in FROZEN_FILES:
        actual = digest(bundle / "ai" / "OpexAI" / name)
        if actual != expected[name]:
            raise ValueError(f"Bundle différent du manifeste: {name}")
        checked[name] = actual
    return checked


def audit(results):
    campaign = "airload_cash_5x3_20261024"
    manifest_path = results / f"{campaign}.manifest.json"
    result_path = results / f"{campaign}.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result["manifest_sha256"] != digest(manifest_path):
        raise ValueError("Manifeste différent de celui enregistré dans le résultat")
    if result["source_bundle_sha256"] != manifest["source_bundle"]["sha256"]:
        raise ValueError("Résultat et manifeste désignent des bundles différents")
    bundle = results / f"{campaign}_bundle"
    actual_bundle = fingerprint_tree(bundle)
    if (actual_bundle["sha256"] != manifest["source_bundle"]["sha256"]
            or actual_bundle["file_count"] != manifest["source_bundle"]["file_count"]):
        raise ValueError("Bundle incomplet ou différent du manifeste")
    checked = verify_frozen_files(bundle, manifest)
    games = result["games"]
    planned = {(arm, seed, 0) for arm in ("reference", "airload50log")
               for seed in (42, 100, 7, 999, 2026)}
    obtained = {(g["policy_id"], g["seed"], g["repeat"]) for g in games}
    if obtained != planned or len(games) != len(planned) or not all(
            g["game_ok"] and g["game_status"] == "complete" for g in games):
        raise ValueError("Les dix duels attendus ne sont pas tous complets et sains")
    comparisons = result["policy_comparison"]
    if not comparisons["comparison_complete"] or not comparisons["metric_coverage_complete"]:
        raise ValueError("Comparaison ou couverture économique incomplète")
    records, files = [], []
    for arm, seed, repeat in sorted(planned):
        path = results / f"{campaign}_engine" / f"{arm}_seed{seed}_r{repeat}.log"
        with path.open(encoding="utf-8") as stream:
            record = analyse_log(stream, path.name)
        if any("modes" not in r for r in record["vivier"]):
            raise ValueError(f"VIVIER_MIX absent dans {path.name}")
        files.append({"path": str(path), "sha256": digest(path), "bytes": path.stat().st_size})
        records.append(record)
    aggregates = {}
    for arm in ("reference", "airload50log"):
        subset = [r for r in records if r["arm"] == arm]
        rows = [v for r in subset for v in r["vivier"]]
        counts, reasons = Counter(), Counter()
        for r in subset:
            counts.update(r["event_counts"])
            reasons.update(r["refusal_counts"])
        aggregates[arm] = {
            "periods": {p: summarise_vivier([v for v in rows if v["date"].startswith(p)])
                        for p in PERIODS},
            "event_counts": dict(sorted(counts.items())),
            "refusal_counts": dict(sorted(reasons.items())),
            **{key: sum(r[key] for r in subset) for key in (
                "fleet_discard_events", "fleet_discard_blocks", "fleet_head_discard_blocks",
                "blocks_with_later_higher_rank_discard", "observed_low_load_discard_events",
                "observed_low_load_fleet_project_refusals")},
        }
    for r in records:
        r["periods"] = {p: summarise_vivier([v for v in r["vivier"] if v["date"].startswith(p)])
                        for p in PERIODS}
        r["december_vivier"] = [v for v in r.pop("vivier") if v["date"].startswith("1972-12")]
    return {
        "schema": 1, "campaign": campaign,
        "limits": ["Descriptive diagnostic, not an adoption sample or causal cash ledger",
                   "TASK is lazy; discard blocks do not enumerate all portfolio passes",
                   "PROJECT_DISCARD is censored; AIR_FLEET refusals are deduplicated by line/month",
                   "Sum of remaining is in pound-snapshots, not distinct pounds or committed capital",
                   "No per-pass counter proves zero unlogged low-load attempts; queue cause is not decoded"],
        "provenance": {
            "result": {"path": str(result_path), "sha256": digest(result_path)},
            "manifest": {"path": str(manifest_path), "sha256": digest(manifest_path)},
            "git": manifest["git"], "bundle_sha256": result["source_bundle_sha256"],
            "verified_bundle_file_count": actual_bundle["file_count"],
            "verified_frozen_files": checked, "logs": files,
            "policies": {p["id"]: p["settings"]["explicit"] for p in manifest["policies"]},
            "games_complete": len(games), "comparison_complete": comparisons["comparison_complete"],
            "metric_coverage_complete": comparisons["metric_coverage_complete"],
            "adoption_sample_complete": comparisons["adoption_sample_complete"],
        },
        "aggregates": aggregates, "logs": records,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path, help="Dossier parent des artefacts existants, lecture seule")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    # Aucune sortie partielle si les entrées ne satisfont pas les contrôles.
    result = audit(args.results)
    with args.out.open("x", encoding="utf-8") as output:
        json.dump(result, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print(json.dumps(result["aggregates"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
