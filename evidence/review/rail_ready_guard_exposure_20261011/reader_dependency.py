"""Agrégation descriptive de la sonde RAIL_READY_ADMISSION.

Aucune comparaison politique : le rang d'un autre projet est insuffisant
pour prouver qu'il aurait pu être construit à cette date.

Utilisation: python -X utf8 sweeps/analyse_rail_ready_admission.py
  results/CAMPAGNE_engine --out results/CAMPAGNE.ready.json
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re


PATTERN = re.compile(r"RAIL_READY_(ADMISSION|UPGRADE)\s+(.+)")
GAME = re.compile(r"^(?P<policy>.+)_seed(?P<seed>\d+)_r(?P<repeat>\d+)\.log$")
FIELD = re.compile(r"([a-z][a-z_0-9]*)=([^\s]+)")


def _as_int(fields: dict, key: str, default: int = -1) -> int:
    try:
        return int(fields.get(key, default))
    except (ValueError, TypeError):
        return default


def read_logs(directory: Path) -> dict:
    if not directory.is_dir():
        raise FileNotFoundError(directory)
    files = sorted(directory.glob("*.log"))
    games = set()
    ready = {}
    upgrades = []
    events = Counter()
    warnings = []
    for path in files:
        game = GAME.match(path.name)
        if game is None:
            warnings.append(f"unrecognized_game:{path.name}")
            continue
        namespace = (game["policy"], int(game["seed"]), int(game["repeat"]))
        games.add(namespace)
        with path.open(encoding="utf-8", errors="replace") as lines:
            for line in lines:
                match = PATTERN.search(line)
                if match is None:
                    continue
                event, payload = match.groups()
                fields = dict(FIELD.findall(payload))
                phase = fields.get("phase", "unknown")
                events[(event, phase)] += 1
                if event == "UPGRADE":
                    upgrades.append({"namespace": namespace, **fields})
                    continue
                search_tick = _as_int(fields, "search_tick")
                if search_tick < 0:
                    warnings.append(f"missing_search_tick:{path.name}")
                    continue
                key = (*namespace, search_tick)
                row = ready.setdefault(key, {
                    "namespace": namespace,
                    "search_tick": search_tick,
                    "first_before": None,
                    "visits": 0,
                    "deferred_visits": 0,
                    "built": None,
                    "after_events": 0,
                })
                if phase == "before":
                    row["visits"] += 1
                    if _as_int(fields, "c77_defer") == 1:
                        row["deferred_visits"] += 1
                    if row["first_before"] is None:
                        row["first_before"] = fields
                elif phase == "after":
                    row["after_events"] += 1
                    row["built"] = _as_int(fields, "built") == 1
                else:
                    warnings.append(f"unknown_phase:{phase}:{path.name}")
    distribution = Counter()
    unique_rows = []
    for row in ready.values():
        fields = row["first_before"]
        if fields is None:
            warnings.append(f"after_without_before:{row['namespace']}:{row['search_tick']}")
            continue
        rank = _as_int(fields, "rank")
        first_rank = _as_int(fields, "first_rank")
        first_mode = fields.get("first_mode", "none")
        better_eligible = first_rank >= 0 and (rank < 0 or first_rank < rank)
        class_name = (
            "missing_from_portfolio" if rank < 0
            else "higher_rank_eligible" if better_eligible
            else "no_higher_rank_eligible"
        )
        distribution[class_name] += 1
        if better_eligible:
            distribution[f"ahead_{first_mode}"] += 1
        if row["built"] is True:
            distribution["built_rail"] += 1
            if better_eligible:
                distribution["built_over_higher_rank"] += 1
                distribution[f"built_over_{first_mode}"] += 1
        elif row["built"] is False:
            distribution["attempted_not_built"] += 1
        else:
            distribution["no_build_result_observed"] += 1
        if row["deferred_visits"] > 0:
            distribution["c77_deferred"] += 1
        unique_rows.append({
            "policy": row["namespace"][0], "seed": row["namespace"][1],
            "repeat": row["namespace"][2], "search_tick": row["search_tick"],
            "src": _as_int(fields, "src"), "dst": _as_int(fields, "dst"),
            "cargo": _as_int(fields, "cargo"), "kind": fields.get("kind", "unknown"),
            "age_days": _as_int(fields, "age_days"),
            "iters": _as_int(fields, "iters"),
            "rank": rank, "first_rank": first_rank, "first_mode": first_mode,
            "first_tier": _as_int(fields, "first_tier"),
            "available": _as_int(fields, "available"),
            "finance": _as_int(fields, "finance"),
            "visits": row["visits"], "c77_deferred_visits": row["deferred_visits"],
            "class": class_name, "built": row["built"],
        })
    unique_rows.sort(key=lambda x: (x["policy"], x["seed"], x["repeat"], x["search_tick"]))
    return {
        "scope": "descriptive shadow only; higher portfolio rank is NOT proof of physical buildability",
        "games_with_log": len(games), "log_files": len(files),
        "raw_events": {f"{name}.{phase}": n for (name, phase), n in sorted(events.items())},
        "unique_ready": len(unique_rows),
        "upgrade_starts": sum(x.get("phase") == "start" for x in upgrades),
        "upgrade_ends": sum(x.get("phase") == "end" for x in upgrades),
        "upgrade_outcomes": dict(Counter(
            x.get("reason", "unknown") for x in upgrades if x.get("phase") == "end")),
        "summary": dict(sorted(distribution.items())),
        "ready": unique_rows,
        "upgrades": upgrades,
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("engine_log_dir", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    options = parser.parse_args()
    result = read_logs(options.engine_log_dir)
    options.out.parent.mkdir(parents=True, exist_ok=True)
    options.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("ready", "upgrades")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
