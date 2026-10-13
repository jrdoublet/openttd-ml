"""Lien chronologique non causal entre achats AIR et fenêtres C117 déjà archivées.

Les logs [FLEET_PROJECT] ne portent pas de date du jeu. Les messages datés
précédent/suivant, émis dans la MEME partie shared-map, bornent la date réelle.
Pas d'inférence depuis l'horloge murale du Docker (timestamps 2026).
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import re
import statistics

from analyse_p0_c117_throughput_20261012 import parse


DATE = re.compile(r"\b(197\d)-(\d{1,2})-(\d{1,2})\b")
PURCHASE = re.compile(r"\[FLEET_PROJECT\] line=(\d+) added=(\d+) replaced=(\d+)")
DIRECT_PURCHASE = re.compile(r"\[AIR_FLEET\] line=(\d+) added=(\d+) total=(\d+)")


def event_date_bounds(lines: list[str]) -> tuple[list[date | None], list[date | None]]:
    """Encadre tout log par les deux dates connues les plus proches."""
    dates: list[date | None] = []
    for line in lines:
        match = DATE.search(line)
        if match is None:
            dates.append(None)
        else:
            try:
                dates.append(date(*map(int, match.groups())))
            except ValueError:
                raise ValueError(f"date non valide: {line[:150]}")
    prev = []
    current = None
    for item in dates:
        if item is not None:
            if current is not None and item < current:
                raise ValueError(f"dates de jeu non monotones : {item} < {current}")
            current = item
        prev.append(current)
    next_ = [None] * len(lines)
    current = None
    for index in range(len(lines) - 1, -1, -1):
        if dates[index] is not None:
            current = dates[index]
        next_[index] = current
    return prev, next_


def extract(log: Path, *, seed: int) -> dict:
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    left, right = event_date_bounds(lines)
    buys = []
    windows = defaultdict(list)
    for index, line in enumerate(lines):
        candidate = PURCHASE.search(line)
        direct = DIRECT_PURCHASE.search(line)
        if candidate or direct:
            kind = "fleet_project" if candidate else "direct_air_fleet"
            match = candidate if candidate is not None else direct
            assert match is not None
            start, stop = left[index], right[index]
            gap = (stop - start).days if start is not None and stop is not None else None
            buys.append({
                "kind": kind, "line": int(match.group(1)), "added": int(match.group(2)),
                "replaced": int(match.group(3)) if candidate else None,
                "date_lower_bound": str(start) if start else None,
                "date_upper_bound": str(stop) if stop else None,
                "date_uncertainty_days": gap,
                "log_line_index": index,
            })
        item = parse(line)
        if item is not None:
            end = date(item["year"], item["month"], item["day"])
            start = end - timedelta(days=item["period_days"])
            windows[item["line"]].append({"start": start, "end": end, "data": item})

    eligible = []
    for event in buys:
        if event["added"] != 1 or event["replaced"] not in (None, 0):
            continue
        if event["date_uncertainty_days"] is None:
            continue
        low, high = date.fromisoformat(event["date_lower_bound"]), date.fromisoformat(event["date_upper_bound"])
        observations = windows.get(event["line"], [])
        before = [w for w in observations if w["end"] <= low
                  and (low - w["end"]).days <= 90 and w["data"]["seat_legs"] > 0]
        after = [w for w in observations if w["start"] >= high
                 and (w["start"] - high).days <= 90 and w["data"]["seat_legs"] > 0]
        if not before or not after:
            continue
        older = max(before, key=lambda w: w["end"])
        newer = min(after, key=lambda w: w["start"])
        if older["data"]["live_last"] >= newer["data"]["live_last"]:
            continue
        # Do not attribute a before/after pair across ANOTHER intervening
        # purchase of exactly this line: isolated +1 acquisitions only.
        other = [b for b in buys if b is not event and b["line"] == event["line"]
                 and b["added"] > 0 and b["date_lower_bound"] is not None
                 and b["date_upper_bound"] is not None
                 and date.fromisoformat(b["date_upper_bound"]) >= older["end"]
                 and date.fromisoformat(b["date_lower_bound"]) <= newer["start"]]
        if other:
            continue
        p, q = older["data"], newer["data"]
        if p["build_date"] != q["build_date"]:
            continue
        def window_field_delta(name: str):
            return q[name] - p[name]
        eligible.append({
            "seed": seed, **event,
            "pre_window_end": older["end"].isoformat(),
            "post_window_start": newer["start"].isoformat(),
            "pre_fleet": p["live_last"], "post_fleet": q["live_last"],
            "pre_load_factor": p["load_factor"], "post_load_factor": q["load_factor"],
            "delta_load_factor": window_field_delta("load_factor"),
            "pre_pax_per_30days": p["pax"] * 30.4 / p["period_days"],
            "post_pax_per_30days": q["pax"] * 30.4 / q["period_days"],
            "pre_seats_per_30days": p["seat_legs"] * 30.4 / p["period_days"],
            "post_seats_per_30days": q["seat_legs"] * 30.4 / q["period_days"],
            "pre_profit_per_aircraft_30days": p["profit"] * 30.4 / (p["period_days"] * p["live_avg"]) if p["live_avg"] > 0 else None,
            "post_profit_per_aircraft_30days": q["profit"] * 30.4 / (q["period_days"] * q["live_avg"]) if q["live_avg"] > 0 else None,
            "pre_invalid_order_samples": p["invalid_order_samples"],
            "post_invalid_order_samples": q["invalid_order_samples"],
        })

    gaps = [b["date_uncertainty_days"] for b in buys if b["date_uncertainty_days"] is not None]
    year1973 = [r for r in eligible if r["date_lower_bound"].startswith("1973")
                and r["date_upper_bound"].startswith("1973")]
    load = [r for r in year1973 if r["pre_load_factor"] >= 0 and r["post_load_factor"] >= 0]
    profit = [r for r in year1973 if r["pre_profit_per_aircraft_30days"] is not None
              and r["post_profit_per_aircraft_30days"] is not None]
    d_pax = [r["post_pax_per_30days"] - r["pre_pax_per_30days"] for r in load]
    d_seats = [r["post_seats_per_30days"] - r["pre_seats_per_30days"] for r in load]
    d_profit = [r["post_profit_per_aircraft_30days"] - r["pre_profit_per_aircraft_30days"]
                for r in profit]
    return {
        "seed": seed,
        "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
        "purchases_total": len(buys),
        "purchases_by_kind": dict(Counter(b["kind"] for b in buys)),
        "purchase_date_gap_max_days": max(gaps, default=None),
        "purchase_date_gap_0_to_2_days": sum(gap <= 2 for gap in gaps),
        "purchase_date_bounds_missing": sum(b["date_uncertainty_days"] is None for b in buys),
        "purchases": buys,
        "event_study_1973": {
            "isolated_added_one_purchases_with_pre_post_windows": len(year1973),
            "with_observable_load": len(load),
            "load_factor_falls": sum(r["delta_load_factor"] < 0 for r in load),
            "mean_delta_load_factor": statistics.mean(r["delta_load_factor"] for r in load) if load else None,
            "pax_per_30days_increases": sum(v > 0 for v in d_pax),
            "mean_delta_pax_per_30days": statistics.mean(d_pax) if d_pax else None,
            "seats_per_30days_increases": sum(v > 0 for v in d_seats),
            "mean_delta_seats_per_30days": statistics.mean(d_seats) if d_seats else None,
            "with_observable_profit": len(profit),
            "profit_per_aircraft_30days_falls": sum(v < 0 for v in d_profit),
            "mean_delta_profit_per_aircraft_30days": statistics.mean(d_profit) if d_profit else None,
        },
        "single_purchases_with_complete_pre_post_windows": eligible,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--seeds", nargs="+", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = {
        "status": "observational_event_study_not_causal",
        "per_seed": [extract(args.engine_dir / f"c117_throughput_shadow_seed{seed}_r0.log", seed=seed)
                     for seed in args.seeds],
        "limits": [
            "Dates d'achat encadrees par deux messages dates du moteur; jamais date exacte sans borne 0.",
            "C117 est une sonde intrusive; impossible d'apparier a reference OFF/N19.",
            "Fenêtres pre et post hors achat, mais potentiellement affectées par demande, saison et rivaux.",
            "La mesure de load_factor repose sur des transitions d'ordres observees toutes les 2j.",
            "Aucun controle du cout d'opportunite / aucune ligne contre-factuelle.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for data in result["per_seed"]:
        print("seed", data["seed"], "purchases", data["purchases_total"],
              "bracket<=2days", data["purchase_date_gap_0_to_2_days"],
              "paired isolated", len(data["single_purchases_with_complete_pre_post_windows"]),
              "1973", data["event_study_1973"])


if __name__ == "__main__":
    main()
