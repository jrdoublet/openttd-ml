#!/usr/bin/env python3
"""Join first frozen C121 build prediction to passive monthly line outcomes."""

from __future__ import annotations

import argparse
import calendar
from datetime import date
import json
from pathlib import Path


def month_add(text: str, months: int) -> str:
    y, m, d = map(int, text.split("-"))
    pos = y * 12 + m - 1 + months
    y2, m0 = divmod(pos, 12)
    m2 = m0 + 1
    return date(y2, m2, min(d, calendar.monthrange(y2, m2)[1])).isoformat()


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def line_profit_cumulative(history: list[tuple[str, dict]], start: str, end: str) -> float | None:
    rows = [(d, line) for d, line in history if start <= d <= end]
    if not rows:
        return None
    years: dict[int, list[tuple[str, float]]] = {}
    for d, line in rows:
        value = line.get("profit_this_year_gbp")
        if not isinstance(value, (int, float)):
            continue
        years.setdefault(int(d[:4]), []).append((d, float(value)))
    if not years:
        return None
    total = 0.0
    start_year = int(start[:4])
    for year, values in sorted(years.items()):
        values.sort()
        if year == start_year:
            total += values[-1][1] - values[0][1]
        else:
            total += values[-1][1]
    return total


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline", type=Path)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    trace = json.loads(args.trace.read_text(encoding="utf-8"))
    rows = load_jsonl(args.baseline.with_suffix(".jsonl"))
    output = []
    for trace_row in trace.get("rows", []):
        if trace_row.get("policy_id") != "c121_current":
            continue
        seed = trace_row.get("seed")
        builds = trace_row.get("c121_builds") or []
        if not builds:
            continue
        build = builds[0]
        station_ids = tuple(sorted((int(build.get("station_id_a")), int(build.get("station_id_b")))))
        history = []
        for row in rows:
            run = row.get("run") or []
            if len(run) < 2 or run[0] != "OpexAI" or int(run[1]) != int(seed):
                continue
            if row.get("duel_policy_id") != "c121_current":
                continue
            for line in (row.get("line_telemetry") or {}).get("lines", []):
                if line.get("mode") != "air":
                    continue
                ids = tuple(sorted(int(x) for x in (line.get("station_ids") or [])))
                if ids == station_ids:
                    history.append((row.get("date"), line))
        history.sort(key=lambda item: item[0])
        first_seen = history[0][0] if history else None
        horizons = {}
        cumulative = {}
        if first_seen:
            for months in (6, 12, 24):
                target = month_add(first_seen, months)
                cumulative[months] = line_profit_cumulative(history, first_seen, target)
                line = next((line for d, line in history if d == target), None)
                horizons[months] = {
                    "target_date": target,
                    "present": line is not None,
                    "vehicles": line.get("vehicles") if line else None,
                    "profit_this_year_gbp": line.get("profit_this_year_gbp") if line else None,
                    "profit_last_year_gbp": line.get("profit_last_year_gbp") if line else None,
                }
        actual_6m_annualized = cumulative.get(6) * 2 if cumulative.get(6) is not None else None
        actual_year1 = cumulative.get(12)
        actual_year2 = None
        if cumulative.get(24) is not None and cumulative.get(12) is not None:
            actual_year2 = cumulative[24] - cumulative[12]
        prediction = {
            key: build.get(key) for key in (
                "line", "arm", "station_id_a", "station_id_b", "pax_a", "pax_b",
                "mail_a", "mail_b", "target_n", "target_profit", "target_revenue",
                "decision_n", "decision_profit", "decision_revenue", "decision_capital",
                "actual_n", "actual_profit", "actual_revenue", "actual_running",
                "plane_price", "airport_capital", "new_airports", "payment_distance",
            )
        }
        pred_one = build.get("actual_profit")
        ratios = {
            "annualized_6m_over_pred_one": actual_6m_annualized / pred_one if actual_6m_annualized is not None and pred_one else None,
            "year1_over_pred_one": actual_year1 / pred_one if actual_year1 is not None and pred_one else None,
            "year2_over_pred_one": actual_year2 / pred_one if actual_year2 is not None and pred_one else None,
        }
        output.append({
            "seed": seed,
            "station_ids": station_ids,
            "first_seen": first_seen,
            "prediction": prediction,
            "actual_profit": {
                "annualized_6m": actual_6m_annualized,
                "year1": actual_year1,
                "year2": actual_year2,
            },
            "ratios": ratios,
            "horizons": horizons,
        })

    payload = {"baseline": str(args.baseline), "trace": str(args.trace), "rows": output}
    text = json.dumps(payload, indent=2) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    for row in output:
        print("SEED", row["seed"], "stations", row["station_ids"], "first", row["first_seen"])
        print(" PRED", row["prediction"])
        print(" REAL", row["actual_profit"], "RATIO", row["ratios"])


if __name__ == "__main__":
    main()
