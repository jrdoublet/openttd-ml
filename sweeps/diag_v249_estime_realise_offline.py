"""V249: audit of statue quotes and descriptive line-profit history in existing logs.

This is NOT an estimate of the realized marginal benefit of a statue. V249_STATUE
records one representative station/cargo and an ex-ante quote, while LINE_REVENUE
is an annual *whole-line* snapshot, without station/town or transported cargo
attribution. A nearby AIR_BUILD town permits a descriptive town-to-line join only.
The quoted gain must never be compared to this proxy as a calibration ratio.

Usage (no engine needed)::

    python sweeps/diag_v249_estime_realise_offline.py --log-dir results/.../_engine

Only OPEX company-0 entries are considered, and no input files are modified.
"""

import argparse
from collections import Counter, defaultdict
from datetime import date
import gzip
import hashlib
import json
from pathlib import Path
import re
from statistics import median


EVENT = re.compile(
    r"\[0\]\s+\[I\]\s+OPEX\s+"
    r"(?P<date>\d{4}-\d{1,2}-\d{1,2})\s+"
    r"(?P<tag>V249_STATUE|V249_SKIP|AIR_BUILD|LINE_REVENUE)\s+(?P<fields>.*)"
)
SEED = re.compile(r"(?:reference|variant|opex)_seed(\d+)_r(\d+)\.log$", re.I)


def fields_of(text):
    return dict(part.split("=", 1) for part in text.split() if "=" in part)


def integer(fields, key):
    try:
        return int(fields[key])
    except (KeyError, TypeError, ValueError):
        return None


def parse_log(path):
    """Read a log once, keeping only build, annual AIR profit and statue facts."""
    path = Path(path)
    stem = path.name[:-3] if path.name.endswith(".gz") else path.name
    match = SEED.search(stem)
    run_id = f"seed{match[1]}_r{match[2]}" if match else path.stem
    buildings = {}
    profits = defaultdict(dict)
    statues = []
    skipped = Counter()
    tags = Counter()

    opener = gzip.open if path.suffix == ".gz" else Path.open
    with opener(path, "rt", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            event = EVENT.search(line)
            if event is None:
                continue
            tag = event["tag"]
            tags[tag] += 1
            values = fields_of(event["fields"])
            try:
                when = date.fromisoformat("-".join(
                    str(int(n)).zfill(width) for n, width in
                    zip(event["date"].split("-"), (4, 2, 2))
                ))
            except ValueError:
                continue

            if tag == "V249_SKIP":
                skipped[values.get("reason", "missing")] += 1
            elif tag == "AIR_BUILD":
                line_id = integer(values, "line")
                src = integer(values, "src_town")
                dst = integer(values, "dst_town")
                if line_id is not None and src is not None and dst is not None:
                    buildings[line_id] = {"date": when, "towns": {src, dst}}
            elif tag == "LINE_REVENUE" and values.get("mode") == "air":
                line_id = integer(values, "line")
                report_year = integer(values, "year")
                real_profit = integer(values, "real_prof")
                if None not in (line_id, report_year, real_profit):
                    profits[line_id][report_year] = real_profit
            elif tag == "V249_STATUE":
                town = integer(values, "town")
                if town is None:
                    continue
                statues.append({
                    "run": run_id, "date": when, "town": town,
                    "station": integer(values, "station"),
                    "cargo": values.get("cargo"),
                    "rating_percent_at_quote": integer(values, "rating"),
                    "production_last_month_at_quote": integer(values, "prod"),
                    "quoted_gain_annual": integer(values, "gain"),
                    "quoted_cost": integer(values, "cost"),
                    "quoted_horizon_years": integer(values, "horizon"),
                    "cash_at_quote": integer(values, "cash"),
                    "budget_threshold_at_quote": integer(values, "threshold"),
                })

    # The annual report in year Y describes the previous year. After a statue
    # purchased in Y, year Y+2 is the earliest full-calendar-year post snapshot.
    for purchase in statues:
        purchase_year = purchase["date"].year
        gain = purchase["quoted_gain_annual"]
        cost = purchase["quoted_cost"]
        purchase["quoted_simple_payback_years"] = (
            cost / gain if gain is not None and gain > 0 and cost is not None else None
        )
        associated = [line_id for line_id, build in buildings.items()
                      if build["date"] <= purchase["date"]
                      and purchase["town"] in build["towns"]]
        comparable = [line_id for line_id in associated
                      if purchase_year in profits[line_id]
                      and purchase_year + 2 in profits[line_id]]
        purchase["air_lines_associated"] = len(associated)
        purchase["air_lines_with_two_snapshots"] = len(comparable)
        purchase["associated_air_profit_delta_descriptive"] = (
            sum(profits[line_id][purchase_year + 2] - profits[line_id][purchase_year]
                for line_id in comparable) if comparable else None
        )
        purchase["snapshot_prior_report_year"] = purchase_year
        purchase["snapshot_post_report_year"] = purchase_year + 2

    return {"run": run_id, "log": str(path), "tags": dict(tags),
            "skipped": dict(skipped), "purchases": [serialize_purchase(p) for p in statues]}


def serialize_purchase(purchase):
    result = dict(purchase)
    result["date"] = purchase["date"].isoformat()
    return result


def summarize(log_results):
    purchases = [p for log in log_results for p in log["purchases"]]
    gains = [p["quoted_gain_annual"] for p in purchases
             if p["quoted_gain_annual"] is not None]
    costs = [p["quoted_cost"] for p in purchases
             if p["quoted_cost"] is not None]
    proxies = [p["associated_air_profit_delta_descriptive"] for p in purchases
               if p["associated_air_profit_delta_descriptive"] is not None]
    paybacks = [p["quoted_simple_payback_years"] for p in purchases
                if p["quoted_simple_payback_years"] is not None]
    tags = Counter()
    skips = Counter()
    for log in log_results:
        tags.update(log["tags"])
        skips.update(log["skipped"])
    return {
        "interpretation": (
            "Descriptive only; associated AIR line-profit movements are NOT the "
            "realized marginal gain of a statue, not a cargo/station comparison, "
            "and not a causal estimate. LINE_REVENUE lacks station/town IDs, "
            "cargo-delivery splits and a counterfactual. Annual report Y covers Y-1; "
            "other investments, fleet changes and competing statues are uncontrolled."
            " Comparable lines are subject to survivorship bias."
        ),
        "log_count": len(log_results),
        "logs_with_purchases": sum(bool(log["purchases"]) for log in log_results),
        "tags": dict(tags),
        "skip_reasons": dict(skips),
        "purchase_count": len(purchases),
        "quoted_gain_median_annual": median(gains) if gains else None,
        "quoted_cost_median": median(costs) if costs else None,
        "quoted_simple_payback_years_median": median(paybacks) if paybacks else None,
        "purchases_by_cargo": dict(Counter(p["cargo"] or "missing" for p in purchases)),
        "purchases_by_year": dict(sorted(Counter(p["date"][:4] for p in purchases).items())),
        "with_associated_air_line": sum(p["air_lines_associated"] > 0 for p in purchases),
        "with_descriptive_air_profit_proxy": len(proxies),
        "descriptive_air_profit_delta_median": median(proxies) if proxies else None,
        "descriptive_proxy_positive": sum(x > 0 for x in proxies),
        "descriptive_proxy_negative": sum(x < 0 for x in proxies),
        "descriptive_proxy_zero": sum(x == 0 for x in proxies),
    }


def _event_signature(path):
    """Compare the exact Opex company-0 V249 inputs between duplicate copies."""
    digest = hashlib.sha256()
    opener = gzip.open if path.suffix == ".gz" else Path.open
    with opener(path, "rt", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            event = EVENT.search(line)
            if event:
                digest.update(event.group(0).encode("utf-8"))
                digest.update(b"\n")
    return digest.digest()


def reference_logs(directory):
    """Return unique reference games; conflicting gzip/text copies are invalid."""
    files = list(directory.glob("reference_seed*_r*.log"))
    files += list(directory.glob("reference_seed*_r*.log.gz"))
    chosen = {}
    canonical_names = {}
    for path in sorted(files):
        stem = path.name[:-3] if path.suffix == ".gz" else path.name
        match = SEED.search(stem)
        if match is None:
            continue
        # Two spellings such as seed1/seed01 or r0/r00 are one numeric
        # game identity, not independent evidence.  Only .log/.gz copies of
        # the SAME spelling may be reconciled by their event signatures.
        identity = (int(match[1]), int(match[2]))
        previous_name = canonical_names.setdefault(identity, stem)
        if previous_name != stem:
            raise ValueError(f"identite de partie V249 ambigue : "
                             f"{previous_name} et {stem} (seed={identity[0]}, r={identity[1]})")
        if stem in chosen:
            prior = chosen[stem]
            if _event_signature(prior) != _event_signature(path):
                raise ValueError(f"copies V249 contradictoires : {prior} et {path}")
            if path.suffix == ".log":
                chosen[stem] = path
        else:
            chosen[stem] = path
    return [chosen[name] for name in sorted(chosen)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-dir", type=Path, required=True,
                        help="Directory of existing engine logs (no recursion)")
    parser.add_argument("--out", type=Path, help="Optional JSON audit output")
    args = parser.parse_args(argv)
    logs = reference_logs(args.log_dir)
    if not logs:
        parser.error("no reference_seed*_r*.log or .log.gz found in --log-dir")
    details = [parse_log(path) for path in logs]
    payload = {"summary": summarize(details), "logs": details}
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
