#!/usr/bin/env python3
"""ROAD100 PAX: observational train/heldout calibration on the V24 ON logs.

Only OpexAI LINE_REVENUE mode=road kind=pax is used. Observations are
unique by (seed, line, age), and only age >= 2 contributes to calibration.
The median realized/predicted factor is fitted on seeds 7, 42, 100, then
evaluated without refitting on heldout seeds 999, 2026. MALE is the mean
absolute natural-log error; pairs with nonpositive values are excluded and
counted rather than being assigned an artificial positive pseudocount.

WARNING: existing and surviving lines are selected by the original policy.
The result is not a counterfactual, a calibrated runtime setting, a company
profit forecast, nor economic validation of new PAX neighborhood routes.

Usage (default: print Markdown only; do not create files):
  python -X utf8 sweeps/diag_road100_pax_heldout_20261028.py
  python -X utf8 sweeps/diag_road100_pax_heldout_20261028.py --format json
  python -X utf8 sweeps/diag_road100_pax_heldout_20261028.py --out report.md
  python -X utf8 sweeps/diag_road100_pax_heldout_20261028.py --out report.json
"""

import argparse
from collections import defaultdict
import gzip
import json
import math
from pathlib import Path
import re
from statistics import mean, median


TRAIN_SEEDS = (7, 42, 100)
HELDOUT_SEEDS = (999, 2026)
SEEDS = frozenset(TRAIN_SEEDS + HELDOUT_SEEDS)
POLICY = "road100_v24_freight_berths"
DEFAULT_LOGS = (Path(__file__).resolve().parent.parent / "results" /
                "road100_v24_freight_physical_berths_roadonly_5x5_20261028_engine")
LOG_NAME = re.compile(r"^road100_v24_freight_berths_seed(\d+)_r(\d+)\.log(?:\.gz)?$")
FIELD = re.compile(r"([A-Za-z_][A-Za-z_0-9]*)=(\S+)")
RECORD = " LINE_REVENUE "
MEASURES = {"revenue": ("pred_rev", "real_rev"),
            "profit": ("pred_prof", "real_prof")}
WARNING = (
    "Biais de selection/survie : seules les lignes PAX deja construites et "
    "encore observees figurent ici. Les lignes/ages d'une meme graine ne sont "
    "pas des observations independantes. Le split heldout ne valide ni "
    "un nouveau quartier, ni un profit incremental ou de societe, ni "
    "une politique ON/OFF. Pas d'ajustement runtime, de causalite ou "
    "de verdict economique V102."
)


def discover_logs(locations=None):
    """Select the one frozen ON policy; reject missing/duplicated/other arms."""
    sources = [DEFAULT_LOGS] if locations is None else [Path(p) for p in locations]
    paths = []
    for source in sources:
        if source.is_dir():
            paths.extend(sorted(source.glob(f"{POLICY}_seed*_r*.log")))
            paths.extend(sorted(source.glob(f"{POLICY}_seed*_r*.log.gz")))
        elif source.is_file():
            paths.append(source)
        else:
            raise ValueError(f"missing --logs path: {source}")
    by_seed = {}
    for path in paths:
        match = LOG_NAME.fullmatch(path.name)
        if match is None:
            raise ValueError(f"not a V24 ON policy engine log: {path}")
        seed, repeat = int(match[1]), int(match[2])
        if seed not in SEEDS or repeat != 0:
            raise ValueError(f"unexpected seed/repetition in V24 5x5 ON: {path}")
        if seed in by_seed:
            raise ValueError(f"duplicate ON policy log for seed {seed}: {path}")
        by_seed[seed] = path
    missing = sorted(SEEDS - by_seed.keys())
    if missing:
        raise ValueError(f"missing V24 ON logs for seeds: {missing}")
    return dict(sorted(by_seed.items()))


def _int_field(fields, name, context, minimum=0):
    token = fields.get(name)
    if token is None or re.fullmatch(r"-?\d+", token) is None:
        raise ValueError(f"{context}: missing/invalid {name}: {token!r}")
    number = int(token)
    if number < minimum:
        raise ValueError(f"{context}: {name} below {minimum}")
    return number


def _numeric_field(fields, name, context):
    token = fields.get(name)
    try:
        number = float(token)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{context}: missing/invalid {name}: {token!r}") from exc
    if not math.isfinite(number):
        raise ValueError(f"{context}: non-finite {name}: {token!r}")
    return number


def parse_log(path, seed):
    """Parse ONLY the named event, mode and kind; enforce identity uniqueness."""
    opening = gzip.open if str(path).endswith(".gz") else open
    rows = []
    identities = set()
    ignored_immature = 0
    with opening(path, "rt", encoding="utf-8", errors="replace") as stream:
        for line_no, raw in enumerate(stream, 1):
            if RECORD not in raw:
                continue
            payload = raw.split(RECORD, 1)[1].strip()
            context = f"{path}:{line_no}"
            tokens = [FIELD.fullmatch(token) for token in payload.split()]
            if any(token is None for token in tokens):
                raise ValueError(f"{context}: malformed LINE_REVENUE")
            fields = {}
            for token in tokens:
                key, value = token.groups()
                if key in fields:
                    raise ValueError(f"{context}: duplicate field {key}")
                fields[key] = value
            if fields.get("mode") != "road" or fields.get("kind") != "pax":
                continue
            line = _int_field(fields, "line", context)
            age = _int_field(fields, "age", context)
            year = _int_field(fields, "year", context, minimum=1)
            identity = (seed, line, age)
            if identity in identities:
                raise ValueError(f"{context}: duplicate (seed,line,age)={identity}")
            identities.add(identity)
            if age < 2:
                ignored_immature += 1
                continue
            entry = {"seed": seed, "line": line, "age": age, "year": year,
                     "vehicles": _int_field(fields, "vehs", context)}
            for field in ("pred_rev", "real_rev", "pred_prof", "real_prof"):
                entry[field] = _numeric_field(fields, field, context)
            rows.append(entry)
    return rows, {"pax_events": len(identities),
                  "immature_age_lt_2": ignored_immature,
                  "mature_events": len(rows)}


def _round(value):
    return None if value is None else round(value, 6)


def _positive_ratio(row, predicted, realized):
    p, r = row[predicted], row[realized]
    if p <= 0 or r <= 0:
        return None
    ratio = r / p
    return ratio if math.isfinite(ratio) and ratio > 0 else None


def _coverage(rows):
    """A line's most recent mature age is a proxy, not a fleet snapshot."""
    latest = {}
    for row in rows:
        key = (row["seed"], row["line"])
        if key not in latest or row["age"] > latest[key]["age"]:
            latest[key] = row
    return {
        "mature_line_age_rows": len(rows),
        "distinct_mature_lines": len(latest),
        "vehicle_sum_latest_mature_age_per_line_proxy": sum(
            row["vehicles"] for row in latest.values()),
        "vehicle_count_note": (
            "Une seule observation, age mature le plus recent par ligne; "
            "les annees different, ce n'est ni une flotte simultanee ni "
            "le parc de la societe."
        ),
    }


def _errors(rows, measure, factor):
    predicted, realized = MEASURES[measure]
    errors_raw, errors_cal = [], []
    invalid = 0
    for row in rows:
        ratio = _positive_ratio(row, predicted, realized)
        if ratio is None:
            invalid += 1
            continue
        log_ratio = math.log(ratio)
        errors_raw.append(abs(log_ratio))
        if factor is not None:
            errors_cal.append(abs(log_ratio - math.log(factor)))
    return {
        "maLE_raw": _round(mean(errors_raw)) if errors_raw else None,
        "maLE_calibrated": _round(mean(errors_cal)) if errors_cal else None,
        "n_positive_real_pred": len(errors_raw),
        "n_excluded_nonpositive_or_unusable": invalid,
    }


def analyze(locations=None):
    """Single-policy descriptive report with genuinely disjoint heldout seeds."""
    files = discover_logs(locations)
    by_seed = {}
    counts = {}
    for seed, path in files.items():
        by_seed[seed], counts[seed] = parse_log(path, seed)
    train = [row for seed in TRAIN_SEEDS for row in by_seed[seed]]
    heldout = [row for seed in HELDOUT_SEEDS for row in by_seed[seed]]
    factors, train_support, scores = {}, {}, {}
    for measure, (predicted, realized) in MEASURES.items():
        ratios = [ratio for row in train
                  if (ratio := _positive_ratio(row, predicted, realized)) is not None]
        factor = median(ratios) if ratios else None
        factors[measure] = _round(factor)
        train_support[measure] = {
            "n_positive_real_pred": len(ratios),
            "n_excluded_nonpositive_or_unusable": len(train) - len(ratios),
        }
        seed_scores = {str(seed): _errors(by_seed[seed], measure, factor)
                       for seed in HELDOUT_SEEDS}
        valid_raw = [entry["maLE_raw"] for entry in seed_scores.values()
                     if entry["maLE_raw"] is not None]
        valid_cal = [entry["maLE_calibrated"] for entry in seed_scores.values()
                     if entry["maLE_calibrated"] is not None]
        scores[measure] = {
            **_errors(heldout, measure, factor),
            "by_seed": seed_scores,
            "seed_balanced_mean_maLE_raw": _round(mean(valid_raw)) if valid_raw else None,
            "seed_balanced_mean_maLE_calibrated": _round(mean(valid_cal)) if valid_cal else None,
            "n_heldout_seeds_with_valid_pairs": len(valid_raw),
        }
    return {
        "diagnostic": "ROAD100-PAX-V24-ON train/heldout observational",
        "policy": POLICY,
        "training_seeds": list(TRAIN_SEEDS),
        "heldout_seeds": list(HELDOUT_SEEDS),
        "age_minimum": 2,
        "maLE_definition": "mean(abs(ln(real / (factor * pred)))) on strictly positive pairs; raw factor=1",
        "factors_train_median_real_over_pred": factors,
        "train_ratio_support": train_support,
        "heldout": scores,
        "train_coverage": _coverage(train),
        "heldout_coverage": _coverage(heldout),
        "by_seed": {
            str(seed): {
                "log": str(files[seed]),
                "split": "train" if seed in TRAIN_SEEDS else "heldout",
                **counts[seed], **_coverage(by_seed[seed]),
            } for seed in sorted(files)
        },
        "warning": WARNING,
    }


def render_markdown(report):
    result = ["# ROAD100 PAX V24 ON — calibration descriptive heldout", "",
              f"Politique unique : `{report['policy']}` ; age ≥ {report['age_minimum']} ; "
              f"train {report['training_seeds']} ; heldout {report['heldout_seeds']}.", "",
              "La MALE est la moyenne des erreurs logarithmiques absolues "
              "(logarithme naturel) sur les seules paires strictement positives. "
              "Chaque ligne-age compte une fois ; les erreurs par graine sont affichees "
              "a part pour exposer la pseudo-replication.", "",
              "| Cible | Mediane train reel/predit | Train paires positives | "
              "Heldout paires positives | MALE brute | MALE calibree | "
              "MALE moyenne par graine brute / calibree |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    def fmt(value):
        return "ND" if value is None else f"{value:.6f}"
    for measure in ("revenue", "profit"):
        score = report["heldout"][measure]
        result.append(
            f"| {measure} | {fmt(report['factors_train_median_real_over_pred'][measure])} | "
            f"{report['train_ratio_support'][measure]['n_positive_real_pred']} | "
            f"{score['n_positive_real_pred']} | {fmt(score['maLE_raw'])} | "
            f"{fmt(score['maLE_calibrated'])} | "
            f"{fmt(score['seed_balanced_mean_maLE_raw'])} / "
            f"{fmt(score['seed_balanced_mean_maLE_calibrated'])} |"
        )
    result.extend(["", "| Graine | Split | PAX observes | Ages < 2 | "
                   "Observations matures | Lignes matures | "
                   "Somme vehicules dernier age mature (proxy) |",
                   "|---:|---|---:|---:|---:|---:|---:|"])
    for seed, entry in report["by_seed"].items():
        result.append(
            f"| {seed} | {entry['split']} | {entry['pax_events']} | "
            f"{entry['immature_age_lt_2']} | {entry['mature_events']} | "
            f"{entry['distinct_mature_lines']} | "
            f"{entry['vehicle_sum_latest_mature_age_per_line_proxy']} |"
        )
    for split in ("train", "heldout"):
        entry = report[f"{split}_coverage"]
        result.append(
            f"| **{split}** | — | — | — | {entry['mature_line_age_rows']} | "
            f"{entry['distinct_mature_lines']} | "
            f"{entry['vehicle_sum_latest_mature_age_per_line_proxy']} |"
        )
    result += ["", "## Exclusions et MALE par graine heldout", ""]
    for measure in ("revenue", "profit"):
        score = report["heldout"][measure]
        result.append(
            f"- {measure} : {score['n_excluded_nonpositive_or_unusable']} "
            "paires non positives/inutilisables exclues de la MALE ; "
            + ", ".join(
                f"seed {seed}: n={value['n_positive_real_pred']} "
                f"brut={fmt(value['maLE_raw'])} calibre={fmt(value['maLE_calibrated'])}"
                for seed, value in score["by_seed"].items()
            )
        )
    result += ["", "**Avertissement.** " + report["warning"], "",
               "La somme des vehicules est un **proxy de lignes**, pas un nombre "
               "de vehicules simultanement exploites ni un profit de societe.", ""]
    return "\n".join(result)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs", nargs="+", type=Path, default=None,
                        help="V24 ON engine-log directory or five explicit ON log files")
    parser.add_argument("--out", type=Path, default=None,
                        help="Optional new .json or .md file; no file by default")
    parser.add_argument("--format", choices=("json", "md"), default=None,
                        help="Console format (default md, or infer from --out)")
    args = parser.parse_args(argv)
    if args.out is not None and args.out.suffix.lower() not in (".json", ".md"):
        parser.error("--out must end in .json or .md")
    selected = args.format or (
        args.out.suffix.lower()[1:] if args.out is not None else "md"
    )
    if args.out is not None and args.out.suffix.lower() != f".{selected}":
        parser.error("--format and --out extension must match")
    try:
        report = analyze(args.logs)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    output = (json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
              if selected == "json" else render_markdown(report)) + "\n"
    if args.out is not None:
        # Exclusive creation: do not modify preexisting user artifacts.
        try:
            with args.out.open("x", encoding="utf-8") as stream:
                stream.write(output)
        except OSError as exc:
            parser.error(str(exc))
    print(output, end="")
    return report


if __name__ == "__main__":
    main()
