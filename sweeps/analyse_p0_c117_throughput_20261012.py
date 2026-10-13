"""Diagnostic descriptif des fenêtres C117 AIR, SANS comparaison événementielle OFF/ON.

Les fenêtres sont indexées par âge de ligne (~30 jours), pas par année civile.
`profit` est l'évolution observée du profit des véhicules, pas le profit_year
comptable. Les vols achevés proviennent du suivi approximatif des transitions
d'ordres toutes les 2 journées : `unobserved_transitions` et `invalid_order_samples`
sont conservés, jamais cachés par le parser.
"""

from __future__ import annotations

import argparse
from collections import defaultdict, Counter
import hashlib
import json
from pathlib import Path
import re


EVENT = re.compile(r"OPEX (?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2}) C117_AIR_THROUGHPUT ")
KEYS = re.compile(r"([a-z_]+)=([^\s]+)")
REQUIRED = (
    "line", "build_date", "age_bucket", "period_days", "samples", "live_avg", "live_last",
    "pax", "seat_legs", "trips", "profit", "load_factor", "rating_a", "rating_b",
    "wait_a", "wait_b", "invalid_order_samples", "unobserved_transitions",
)


def parse(line: str) -> dict | None:
    match = EVENT.search(line)
    if match is None:
        if "C117_AIR_THROUGHPUT " in line:
            raise ValueError(f"journal C117 mal forme : {line[:160]}")
        return None
    fields = dict(KEYS.findall(line[match.end():]))
    absent = set(REQUIRED) - fields.keys()
    if absent:
        raise ValueError(f"champs C117 absents : {sorted(absent)}")
    fields.update({key: int(match.group(key)) for key in ("year", "month", "day")})
    for name in ("line", "build_date", "age_bucket", "period_days", "samples", "live_last",
                 "pax", "seat_legs", "trips", "profit", "invalid_order_samples",
                 "unobserved_transitions"):
        fields[name] = int(fields[name])
    for name in ("live_avg", "load_factor", "rating_a", "rating_b", "wait_a", "wait_b"):
        fields[name] = float(fields[name])
    if fields["period_days"] < 1 or fields["samples"] < 1:
        raise ValueError("C117 fenetre de duree ou echantillonnage nul")
    if fields["pax"] < 0 or fields["seat_legs"] < 0 or fields["live_last"] < 0:
        raise ValueError("C117 compteur negatif")
    return fields


def year_line(rows: list[dict]) -> dict:
    """Sommes couvrant les fenêtres observées ; n'infère pas 365 jours."""
    rows = sorted(rows, key=lambda r: (r["year"], r["month"], r["day"], r["age_bucket"]))
    days = sum(r["period_days"] for r in rows)
    live_days = sum(r["live_avg"] * r["period_days"] for r in rows)
    pax = sum(r["pax"] for r in rows)
    seats = sum(r["seat_legs"] for r in rows)
    trips = sum(r["trips"] for r in rows)
    profit = sum(r["profit"] for r in rows)
    samples = sum(r["samples"] for r in rows)
    invalid = sum(r["invalid_order_samples"] for r in rows)
    return {
        "line": rows[0]["line"], "year": rows[0]["year"],
        "windows": len(rows), "period_days_total": days,
        "samples_total": samples,
        "last_fleet": rows[-1]["live_last"],
        "mean_fleet_exposure": live_days / days if days else None,
        "vehicle_profit_observed": profit,
        "vehicle_profit_per_aircraft_year_exposure": profit * 365.25 / live_days if live_days > 0 else None,
        "pax_observed": pax,
        "seat_legs_observed": seats,
        "completed_legs_observed": trips,
        "pax_per_30days_observed": pax * 30.4 / days if days else None,
        "seats_per_30days_observed": seats * 30.4 / days if days else None,
        "load_factor_observed": pax / seats if seats > 0 else None,
        "headway_days_observed": 2.0 * days / trips if trips > 0 else None,
        "rating_mean_observed": sum(
            (r["rating_a"] + r["rating_b"]) * 0.5 * r["period_days"]
            for r in rows if r["rating_a"] >= 0 and r["rating_b"] >= 0
        ) / sum(r["period_days"] for r in rows
                if r["rating_a"] >= 0 and r["rating_b"] >= 0)
        if any(r["rating_a"] >= 0 and r["rating_b"] >= 0 for r in rows) else None,
        "invalid_order_samples": invalid,
        # Compteur dans la boucle VEHICULES : le denominateur `samples` est
        # celui des appels par LIGNE ; ce ratio n'est PAS une probabilite.
        "invalid_order_events_per_line_step_sample": invalid / samples if samples > 0 else None,
        "unobserved_transitions": sum(r["unobserved_transitions"] for r in rows),
    }


def summarize(rows: list[dict], seed: int) -> dict:
    annual_rows = defaultdict(list)
    seen = set()
    build_by_line = {}
    for row in rows:
        if row["line"] in build_by_line and build_by_line[row["line"]] != row["build_date"]:
            raise ValueError(f"lineId recycle avec nouvelle date de pose : {row['line']}")
        build_by_line[row["line"]] = row["build_date"]
        k = (row["line"], row["year"], row["age_bucket"])
        if k in seen:
            raise ValueError(f"fenetre C117 dupliquee : {k}")
        seen.add(k)
        annual_rows[(row["line"], row["year"])].append(row)
    by_year = {key: year_line(value) for key, value in annual_rows.items()}
    fleet_categories = {"increase": [], "constant": [], "decrease": []}
    for line in sorted({key[0] for key in by_year}):
        p72 = by_year.get((line, 1972))
        p73 = by_year.get((line, 1973))
        if not p72 or not p73:
            continue
        group = ("increase" if p73["last_fleet"] > p72["last_fleet"] else
                 "decrease" if p73["last_fleet"] < p72["last_fleet"] else "constant")
        def delta(field):
            a, b = p72[field], p73[field]
            return b - a if a is not None and b is not None else None
        fleet_categories[group].append({
            "line": line, "fleet_1972": p72["last_fleet"], "fleet_1973": p73["last_fleet"],
            "days_1972": p72["period_days_total"], "days_1973": p73["period_days_total"],
            "windows_1972": p72["windows"], "windows_1973": p73["windows"],
            "profit_per_aircraft_year_1972": p72["vehicle_profit_per_aircraft_year_exposure"],
            "profit_per_aircraft_year_1973": p73["vehicle_profit_per_aircraft_year_exposure"],
            "delta_profit_per_aircraft_year": delta("vehicle_profit_per_aircraft_year_exposure"),
            "pax_per_30days_1972": p72["pax_per_30days_observed"],
            "pax_per_30days_1973": p73["pax_per_30days_observed"],
            "delta_pax_per_30days": delta("pax_per_30days_observed"),
            "load_factor_1972": p72["load_factor_observed"],
            "load_factor_1973": p73["load_factor_observed"],
            "delta_load_factor": delta("load_factor_observed"),
            "headway_days_1972": p72["headway_days_observed"],
            "headway_days_1973": p73["headway_days_observed"],
            "delta_headway_days": delta("headway_days_observed"),
            "delta_rating": delta("rating_mean_observed"),
            "invalid_order_samples": p72["invalid_order_samples"] + p73["invalid_order_samples"],
            "samples_total": p72["samples_total"] + p73["samples_total"],
            "unobserved_transitions": p72["unobserved_transitions"] + p73["unobserved_transitions"],
        })
    return {
        "seed": seed,
        "windows_total": len(rows),
        "year_windows": dict(sorted(Counter(r["year"] for r in rows).items())),
        "fleet_groups": {group: {"count": len(entries), "lines": entries}
                         for group, entries in fleet_categories.items()},
    }


def analyze(engine_dir: Path, result_path: Path, manifest_path: Path) -> dict:
    data = json.loads(result_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["comparison"]["effective_differences"] != {
        "c117_air_throughput_probe": {"candidate": 1, "reference": 0}
    }:
        raise ValueError("C117 n'est pas l'unique reglage ON/OFF")
    if len(data["games"]) != 2 * len(data["seeds"]) or data["failed_runs"]:
        raise ValueError("duels manquants ou en erreur")
    if not all(g["game_ok"] for g in data["games"]):
        raise ValueError("jeu malade")
    seen_hashes = {}
    summaries = []
    for seed in data["seeds"]:
        active = engine_dir / f"c117_throughput_shadow_seed{seed}_r0.log"
        passive = engine_dir / f"reference_seed{seed}_r0.log"
        if not active.is_file() or not passive.is_file():
            raise ValueError(f"logs C117 manquants seed {seed}")
        for path in (active, passive):
            seen_hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        if "C117_AIR_THROUGHPUT " in passive.read_text(encoding="utf-8", errors="replace"):
            raise ValueError(f"logs C117 erroneement actifs dans reference {seed}")
        rows = []
        for line in active.read_text(encoding="utf-8", errors="replace").splitlines():
            parsed = parse(line)
            if parsed is not None:
                rows.append(parsed)
        summaries.append(summarize(rows, seed))
    return {
        "status": "diagnostic_only_no_adoption_gate",
        "bundle_sha256": data["source_bundle_sha256"],
        "campaign": data["campaign_id"],
        "health": {"games": len(data["games"]), "failed": len(data["failed_runs"]),
                   "seeds": data["seeds"]},
        "sha256": {"result": hashlib.sha256(result_path.read_bytes()).hexdigest(),
                   "manifest": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                   **dict(sorted(seen_hashes.items()))},
        "seed_summaries": summaries,
        "limitations": [
            "Analyse dans la trajectoire ON uniquement : C117 peut deplacer les decisions.",
            "Age buckets de ~30 jours chevauchent les annees; sommes NON comptables et non necessairement 365 jours.",
            "Profit C117 = differences de profit YTD des vehicules observes, pas profit_year comptable.",
            "Legs et charge inferes de transitions d'ordres avec echantillonnage 2j, pas observabilite parfaite.",
            "Les cohortes par lineId ne sont pas les memes que les services regroupes par StationID de C66.",
            "Ni comparateur exogene de la demande, ni contrefactuel sur renfort de flotte, ni cout d'opportunite prouve.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    info = analyze(args.engine_dir, args.result, args.manifest)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(info, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for seed in info["seed_summaries"]:
        print(f"seed={seed['seed']} windows={seed['windows_total']} "
              + " ".join(f"{cat}={group['count']}" for cat, group in seed["fleet_groups"].items()))
    print(f"archive {args.out}")


if __name__ == "__main__":
    main()
