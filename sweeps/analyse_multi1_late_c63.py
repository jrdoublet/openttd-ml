"""MULTI-1: bilan descriptif C63 des années tardives sur des logs moteur figés.

Réutilise le décodeur C63/C58, vérifie chaque vidange annuelle et ne cherche
aucun effet causal de la sonde sur la référence. Ne lance aucune simulation.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

try:
    from sweeps.diag_c63_c58 import C63_RE, C50_RE, MODES, OPP_KINDS, parse_c63_invest
    from sweeps.harness import parse_fields
except ImportError:
    from diag_c63_c58 import C63_RE, C50_RE, MODES, OPP_KINDS, parse_c63_invest
    from harness import parse_fields

SCRIPT_FATAL = re.compile(r"script error|squirrel.*error|ai script.*crash", re.IGNORECASE)


def analyse_log(contents: str, first_year: int, last_year: int) -> dict:
    """Les années sont celles du ledger, vidangées le 1er janvier suivant."""
    parsed = parse_c63_invest(contents)
    emitted = defaultdict(Counter)
    cash_by_year = defaultdict(dict)
    for line in contents.splitlines():
        match = C63_RE.search(line)
        if match:
            fields = parse_fields(match.group(4))
            year = int(fields.get("year", match.group(1)))
            phase = fields.get("phase", "")
            if phase == "spend":
                emitted[year]["spend:" + str(fields.get("mode", "?"))] += 1
            elif phase in ("opp", "opp_absent"):
                emitted[year][phase] += 1
            continue
        match = C50_RE.search(line)
        if match:
            fields = parse_fields(match.group(4))
            if fields.get("phase") == "treasury_monthly":
                year = int(fields.get("year", match.group(1)))
                month = int(fields.get("month", 0))
                if month == 12:
                    cash_by_year[year] = {
                        "cash": int(fields.get("cash", 0)),
                        "loan": int(fields.get("loan", 0)),
                        "available": int(fields.get("available", 0)),
                    }

    warnings = []
    if SCRIPT_FATAL.search(contents):
        warnings.append("possible_script_error_inspect_engine_log")
    years = {}
    for year in range(first_year, last_year + 1):
        bucket = parsed.get(year)
        if bucket is None:
            warnings.append(f"missing_ledger:{year}")
            continue
        counts = emitted[year]
        if counts["opp"] != 1 or counts["opp_absent"] != 1:
            warnings.append(f"ledger_flush_count:{year}:opp={counts['opp']}:absent={counts['opp_absent']}")
        for mode in MODES:
            if counts["spend:" + mode] != 1:
                warnings.append(f"spend_flush_count:{year}:{mode}={counts['spend:' + mode]}")
        all_lines = bucket["lines"]
        identities = [(item["mode"], item["line"]) for item in all_lines]
        if len(identities) != len(set(identities)):
            warnings.append(f"duplicate_line_report:{year}")
        mature = [item for item in all_lines if item["age"] >= 2]
        modes = {}
        for mode in MODES:
            slot = bucket["spend"][mode]
            lines = [item for item in mature if item["mode"] == mode]
            modes[mode] = {
                "planned_ok": slot["planned_ok"],
                "actual_ok": slot["actual_ok"],
                "n_ok": slot["n_ok"],
                "planned_fail": slot["planned_fail"],
                "actual_fail": slot["actual_fail"],
                "n_fail": slot["n_fail"],
                "mature_n": len(lines),
                "mature_pred_profit": sum(item["pred_p"] for item in lines),
                "mature_real_profit": sum(item["real_p"] for item in lines),
                "mature_pred_revenue": sum(item["pred_r"] for item in lines),
                "mature_real_revenue": sum(item["real_r"] for item in lines),
                "mature_losing_n": sum(item["real_p"] < 0 for item in lines),
            }
        opp = bucket["opp"]
        opp_days = {kind: opp[kind]["days"] for kind in OPP_KINDS}
        annual_days = sum(opp_days.values())
        # Les sondes sont exclusives par passe ; une différence avec 365/366
        # n'est pas une preuve de double comptage (jours sans passe possibles).
        if annual_days > 366:
            warnings.append(f"opportunity_days_exceed_year:{year}:{annual_days}")
        if sum(item["days"] for item in bucket["absent_causes"].values()) != opp_days["absent"]:
            warnings.append(f"absent_subcauses_inconsistent:{year}")
        if year not in cash_by_year:
            warnings.append(f"missing_december_cash:{year}")
        years[str(year)] = {
            "modes": modes,
            "opp_days": opp_days,
            "opp_n": {kind: opp[kind]["n"] for kind in OPP_KINDS},
            "opp_annual_total_days": annual_days,
            "absent_causes_days": {
                key: value["days"] for key, value in bucket["absent_causes"].items()
            },
            "empty_probe_n": len(bucket["empty_probes"]),
            "empty_probe_causes": dict(Counter(
                item["cause"] for item in bucket["empty_probes"]
            )),
            "all_lines_n": len(all_lines),
            "mature_lines_n": len(mature),
            "cash_december": cash_by_year.get(year),
        }
    return {"years": years, "warnings": warnings}


def aggregate(by_seed: dict, first_year: int, last_year: int) -> dict:
    # Le protocole interdit les moyennes construites sur une vidange incomplète,
    # même lorsque les cinq clés d'années sont techniquement présentes.
    if any(item["warnings"] for item in by_seed.values()):
        return {}
    summary = {}
    n = len(by_seed)
    for year in range(first_year, last_year + 1):
        year_key = str(year)
        rows = [data["years"][year_key] for data in by_seed.values()
                if year_key in data["years"]]
        if len(rows) != n:
            continue
        modes = {}
        for mode in MODES:
            columns = rows[0]["modes"][mode].keys()
            modes[mode] = {
                key: sum(row["modes"][mode][key] for row in rows) / n
                for key in columns
            }
        summary[year_key] = {
            "n_seeds": n,
            "avg_modes": modes,
            "avg_opp_days": {
                kind: sum(row["opp_days"][kind] for row in rows) / n
                for kind in OPP_KINDS
            },
            "avg_cash_december": (
                sum(row["cash_december"]["cash"] for row in rows) / n
                if all(row["cash_december"] is not None for row in rows) else None
            ),
        }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", required=True, type=Path)
    parser.add_argument("--prefix", default="multi1_c63_probe_only")
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 7, 999, 2026])
    parser.add_argument("--first-year", type=int, default=1975)
    parser.add_argument("--last-year", type=int, default=1979)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        parser.error(f"fichier de sortie déjà présent : {args.out}")
    by_seed = {}
    for seed in args.seeds:
        path = args.engine_dir / f"{args.prefix}_seed{seed}_r0.log"
        if not path.is_file():
            parser.error(f"journal moteur absent : {path}")
        by_seed[str(seed)] = analyse_log(
            path.read_text(encoding="utf-8", errors="replace"),
            args.first_year, args.last_year,
        )
    result = {
        "scope": "diagnostic_only_not_causal",
        "engine_dir": str(args.engine_dir),
        "seeds": args.seeds,
        "years": [args.first_year, args.last_year],
        "by_seed": by_seed,
        "annual_mean": aggregate(by_seed, args.first_year, args.last_year),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("analysis:", args.out)
    print("years complete:", len(result["annual_mean"]), "/", args.last_year - args.first_year + 1)
    print("warnings:", {seed: item["warnings"] for seed, item in by_seed.items() if item["warnings"]})
    if any(item["warnings"] for item in by_seed.values()):
        raise SystemExit("ABORT: statistiques non qualifiées — vérifier les avertissements")


if __name__ == "__main__":
    main()
