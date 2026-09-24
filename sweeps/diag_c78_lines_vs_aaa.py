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


C78_TAG_RE = re.compile(r"OPEX (\d+)-\d+-\d+ (C78_[A-Z]+)\s*(.*)")


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


def parse_c78_logs(output):
    candidates_by_year = defaultdict(list)
    airpool_by_year = {}
    airtowns_by_year = defaultdict(list)
    airpairs_by_year = defaultdict(list)
    builds_by_year = defaultdict(list)

    for date_year, tag, fields_str in C78_TAG_RE.findall(output or ""):
        parsed = parse_fields(fields_str)
        y = parsed.get("year", int(date_year))

        if tag == "C78_CAND":
            candidates_by_year[y].append(parsed)
        elif tag == "C78_AIRPOOL":
            pool = parsed.get("pool", 24)
            towns_str = parsed.get("towns", "")
            towns_dict = {}
            if isinstance(towns_str, str) and towns_str:
                for idx, item in enumerate(towns_str.split(",")):
                    parts = item.split(":")
                    if len(parts) >= 2:
                        try:
                            # [rang, population, tuile] ; tuile absente dans l'ancien format
                            tile = int(parts[2]) if len(parts) >= 3 else None
                            towns_dict[int(parts[0])] = [idx, int(parts[1]), tile]
                        except ValueError:
                            pass
            bounds = {key: parsed[key] for key in ("airMin", "airMax", "railMin", "railMax", "overlap")
                      if key in parsed}
            # Codes d'erreur de l'API publies par l'IA elle-meme (nom -> valeur)
            errors = {key[2:]: parsed[key] for key in parsed if key.startswith("e_")}
            airpool_by_year[y] = {"pool": pool, "towns": towns_dict,
                                  "mapx": parsed.get("mapx"), "bounds": bounds, "errors": errors}
        elif tag == "C78_AIRTOWN":
            airtowns_by_year[y].append(parsed)
        elif tag == "C78_AIRPAIR":
            airpairs_by_year[y].append(parsed)
        elif tag == "C78_BUILD":
            builds_by_year[y].append(parsed)

    return {
        "candidates": candidates_by_year,
        "airpool": airpool_by_year,
        "airtowns": airtowns_by_year,
        "airpairs": airpairs_by_year,
        "builds": builds_by_year,
    }


def parse_c78_candidates(output):
    logs = parse_c78_logs(output)
    return logs["candidates"]


def keep(row):
    date_str = str(row.get("date", ""))
    if not re.match(r"^\d{4}-12-", date_str):
        return ()
    chunks = row.get("chunks", {})
    year_match = re.match(r"^(\d{4})-", date_str)
    year = int(year_match.group(1)) if year_match else None
    seed = row.get("experiment", {}).get("seed")
    output = row.get("output", "")

    c78_data = parse_c78_logs(output)
    cand_list = c78_data["candidates"].get(year, [])
    airpool_data = c78_data["airpool"].get(year, {})
    airtowns_list = c78_data["airtowns"].get(year, [])
    airpairs_list = c78_data["airpairs"].get(year, [])
    builds_list = c78_data["builds"].get(year, [])

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
            # La sauvegarde stocke la ville d'une gare comme reference d'objet : identifiant + 1
            # (0 = aucune). Les sondes C78 journalisent les identifiants de l'API. Sans ce -1,
            # l'appariement decalait toutes les paires d'une ville (mesure 2026-09-22 : decalage
            # +1 dans 11 416 cas, ~170 pour tout autre ecart ; diag_b9 le corrige de son cote).
            lines_summary.append({
                "mode": l.get("mode"),
                "towns": [t - 1 for t in (l.get("town_ids") or []) if isinstance(t, int) and t > 0],
                "towns_raw": l.get("town_ids", []),
                "vehicles": l.get("vehicles", 0),
                "profit_last_year": l.get("profit_last_year_gbp", 0.0),
                "airports": endpoint_airports,
                "airport_types": airport_types,
                "tiles": l.get("ordered_station_tiles", []),
                "cargo": l.get("cargo_types", []),
            })
        companies_data[str(owner)] = {
            "lines": lines_summary,
        }

    return ({
        "seed": seed,
        "year": year,
        "date": date_str,
        "candidates": cand_list,
        "airpool": airpool_data,
        "airtowns": airtowns_list,
        "airpairs": airpairs_list,
        "builds": builds_list,
        "companies": companies_data,
    },)


def run_selftest():
    sample_output = (
        "OPEX 1971-1-1 C78_CAND year=1971 mode=air townA=10 townB=20 indA=-1 indB=-1 P=120000 C=45000 rank=0 affordable=1\n"
        "OPEX 1971-1-1 C78_CAND year=1971 mode=road townA=10 townB=20 indA=-1 indB=-1 P=35000 C=12000 rank=1 affordable=1\n"
        "OPEX 1973-1-1 C78_CAND year=1973 mode=air townA=15 townB=30 indA=-1 indB=-1 P=250000 C=50000 rank=-1 affordable=0\n"
        "OPEX 1971-1-1 C78_AIRPOOL year=1971 pool=24 mapx=256 airMin=90 airMax=400 railMin=20 railMax=160 overlap=90 towns=10:1500:2570,20:1200,30:900:5000\n"
        "OPEX 1971-1-1 C78_AIRTOWN year=1971 combo=0:12 town=10 rank=0 outcome=site\n"
        "OPEX 1971-1-1 C78_AIRPAIR year=1971 arm=newpair combo=0:12 townA=10 townB=20 dist=45 outcome=admitted P=120000 C=45000\n"
        "OPEX 1971-1-1 C78_BUILD year=1971 rank=0 mode=air townA=10 townB=20 indA=-1 indB=-1 P=120000 C=45000 outcome=built reason=-\n"
    )
    c78_data = parse_c78_logs(sample_output)
    by_year = c78_data["candidates"]
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

    # Selftest des nouveaux types C78 etape 2
    airpool = c78_data["airpool"].get(1971)
    assert airpool is not None, "Expected airpool in 1971"
    assert airpool["pool"] == 24
    assert airpool["towns"][10] == [0, 1500, 2570]
    assert airpool["towns"][20] == [1, 1200, None]  # ancien format sans tuile
    assert airpool["towns"][30] == [2, 900, 5000]
    assert airpool["mapx"] == 256
    assert airpool["bounds"] == {"airMin": 90, "airMax": 400, "railMin": 20, "railMax": 160, "overlap": 90}

    airtowns = c78_data["airtowns"].get(1971)
    assert len(airtowns) == 1, f"Expected 1 airtown in 1971, got {len(airtowns)}"
    assert airtowns[0]["town"] == 10
    assert airtowns[0]["outcome"] == "site"
    assert airtowns[0]["combo"] == "0:12"

    airpairs = c78_data["airpairs"].get(1971)
    assert len(airpairs) == 1, f"Expected 1 airpair in 1971, got {len(airpairs)}"
    assert airpairs[0]["arm"] == "newpair"
    assert airpairs[0]["townA"] == 10
    assert airpairs[0]["townB"] == 20
    assert airpairs[0]["dist"] == 45
    assert airpairs[0]["outcome"] == "admitted"
    assert airpairs[0]["P"] == 120000
    assert airpairs[0]["C"] == 45000

    builds = c78_data["builds"].get(1971)
    assert len(builds) == 1, f"Expected 1 build in 1971, got {len(builds)}"
    assert builds[0]["mode"] == "air"
    assert builds[0]["townA"] == 10
    assert builds[0]["townB"] == 20
    assert builds[0]["outcome"] == "built"
    assert builds[0]["reason"] == "-"

    extra = parse_c78_logs(
        "OPEX 1971-1-1 C78_AIRTOWN year=1971 combo=0:12 town=11 rank=1 outcome=no_site\n"
        "OPEX 1971-1-1 C78_AIRTOWN year=1971 combo=0:12 town=12 rank=2 outcome=no_site_slot\n"
        "OPEX 1971-1-1 C78_AIRTOWN year=1971 combo=0:12 town=13 rank=3 outcome=no_site_budget\n"
        "OPEX 1971-1-1 C78_AIRTOWN year=1971 combo=0:12 town=14 rank=4 outcome=no_site_terrain\n"
    )
    outs = {row["town"]: row["outcome"] for row in extra["airtowns"][1971]}
    assert outs == {
        11: "no_site",
        12: "no_site_slot",
        13: "no_site_budget",
        14: "no_site_terrain",
    }

    print("diag_c78_lines_vs_aaa selftest passed: parsing C78_CAND, AIRPOOL, AIRTOWN, AIRPAIR, BUILD ok.")


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
