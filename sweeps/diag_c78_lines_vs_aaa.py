"""C78 : Diagnostic ligne par ligne OpexAI contre AAAHogEx.

Duel OpexAI[probe_portfolio=1] contre AAAHogEx avec capture passive des candidats C78_CAND
et releve des lignes exploitees (mode, villes, vehicules, profit_last_year, aeroports) a
chaque sauvegarde de decembre pour les compagnies 0 et 1.
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

DEFAULT_SEEDS = [42, 100, 7]
DEFAULT_YEARS = 6

try:
    import openttdlab
    from openttdlab import bananas_ai_library, local_folder, run_experiments
    from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, enable_savegame_cleanup, make_cfg
    from bench_1v1_5y_20seeds import extract_line_telemetry

    _real_check_output = openttdlab.subprocess.check_output

    def _check_output_with_script_debug(args, *rest, **kwargs):
        args = tuple(args)
        if any(str(arg).startswith("-vnull") for arg in args):
            args = args[:1] + ("-d", "script=4") + args[1:]
        return _real_check_output(args, *rest, **kwargs)

    openttdlab.subprocess.check_output = _check_output_with_script_debug
except ImportError:
    pass


C78_RE = re.compile(r"OPEX (\d+)-\d+-\d+ C78_CAND\s*(.*)")


def parse_fields(fields_str):
    res = {}
    for token in fields_str.split():
        if "=" in token:
            k, v = token.split("=", 1)
            try:
                res[k] = int(v)
            except ValueError:
                try:
                    res[k] = float(v)
                except ValueError:
                    res[k] = v
    return res


def parse_c78_candidates(output):
    by_year = defaultdict(list)
    for date_year, fields_str in C78_RE.findall(output or ""):
        parsed = parse_fields(fields_str)
        y = parsed.get("year", int(date_year))
        by_year[y].append(parsed)
    return by_year


def keep(row):
    date_str = str(row.get("date", ""))
    if not re.match(r"^\d{4}-12-", date_str):
        return ()
    chunks = row.get("chunks", {})
    year_match = re.match(r"^(\d{4})-", date_str)
    year = int(year_match.group(1)) if year_match else None
    seed = row.get("experiment", {}).get("seed")
    output = row.get("output", "")

    candidates_by_year = parse_c78_candidates(output)
    cand_list = candidates_by_year.get(year, [])

    companies_data = {}
    for owner in (0, 1):
        telemetry = extract_line_telemetry(chunks, owner)
        lines_summary = []
        for l in telemetry.get("lines", []):
            endpoint_airports = [
                ep.get("airport")
                for ep in l.get("endpoint_cargo_stats", [])
                if ep.get("airport") is not None
            ]
            airport_types = [
                ep["airport"]["type"]
                for ep in l.get("endpoint_cargo_stats", [])
                if ep.get("airport") and ep["airport"].get("type") is not None
            ]
            lines_summary.append({
                "mode": l.get("mode"),
                "towns": l.get("town_ids", []),
                "vehicles": l.get("vehicles", 0),
                "profit_last_year": l.get("profit_last_year_gbp", 0.0),
                "airports": endpoint_airports,
                "airport_types": airport_types,
            })
        companies_data[str(owner)] = {
            "lines": lines_summary,
        }

    return ({
        "seed": seed,
        "year": year,
        "date": date_str,
        "candidates": cand_list,
        "companies": companies_data,
    },)


def run_selftest():
    sample_output = (
        "OPEX 1971-1-1 C78_CAND year=1971 mode=air townA=10 townB=20 indA=-1 indB=-1 P=120000 C=45000 rank=0 affordable=1\n"
        "OPEX 1971-1-1 C78_CAND year=1971 mode=road townA=10 townB=20 indA=-1 indB=-1 P=35000 C=12000 rank=1 affordable=1\n"
        "OPEX 1973-1-1 C78_CAND year=1973 mode=air townA=15 townB=30 indA=-1 indB=-1 P=250000 C=50000 rank=-1 affordable=0\n"
    )
    by_year = parse_c78_candidates(sample_output)
    assert len(by_year[1971]) == 2, f"Expected 2 candidates in 1971, got {len(by_year[1971])}"
    assert len(by_year[1973]) == 1, f"Expected 1 candidate in 1973, got {len(by_year[1973])}"
    c = by_year[1971][0]
    assert c["mode"] == "air"
    assert c["townA"] == 10
    assert c["townB"] == 20
    assert c["P"] == 120000
    assert c["C"] == 45000
    assert c["rank"] == 0
    assert c["affordable"] == 1
    print("diag_c78_lines_vs_aaa selftest passed: parsing C78_CAND ok.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=DEFAULT_YEARS)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "diag_c78_lines_vs_aaa.json")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        run_selftest()
        return

    enable_savegame_cleanup()
    # local_folder avec les SEULS reglages explicites (la ligne ai_players est lue sur ~1024 caracteres)
    opex = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", (("probe_portfolio", 1),))
    aaahogex = local_folder(str(ROOT / "ai" / "AAAHogEx-115"), "AAAHogEx", ())
    cfg = make_cfg(1970)

    experiments = []
    for seed in args.seeds:
        experiments.append({
            "bench_context": "duel",
            "bench_arm": "OpexAI[probe_portfolio=1]",
            "seed": seed,
            "days": 365 * args.years,
            "openttd_config": cfg,
            "ais": (opex, aaahogex),
        })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        experiments=experiments,
        max_workers=args.max_workers,
        result_processor=keep,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    rows.sort(key=lambda r: (r.get("seed", 0), r.get("year", 0)))
    args.out.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    print(f"Snapshots captures: {len(rows)}, sortie: {args.out}")


if __name__ == "__main__":
    main()
