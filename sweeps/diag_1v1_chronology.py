"""Chronologie annuelle symetrique d'un duel partage OpexAI contre AAAHogEx.

Les volumes viennent exclusivement des chunks de sauvegarde, par difference entre les
etats de fin d'annee. Le journal AAAHogEx ne sert qu'a compter ses tentatives de
construction. ``--selftest`` n'importe ni openttdlab ni OpenTTD.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re


ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
AAAHOGEX_DIR = "AAAHogEx-115"
STARTING_YEAR = 1970
CFG = """[difficulty]
number_towns = 3
industry_density = 4
[economy]
inflation = false
town_growth_rate = 2
[game_creation]
starting_year = 1970
map_x = 8
map_y = 8
"""

SCRIPT_RE = re.compile(r"\[script:(\d+)\] \[\d+\] \[\w\] (.*)")
HOG_DATE_RE = re.compile(r"^(\d+)-(\d+)-(\d+) (.*)$")
HOG_EVENTS = {
    "# RouteBuilder Start": "start",
    "# RouteBuilder Succeeded": "succeeded",
    "# RouteBuilder Failed": "failed",
}


def game_state_counts(chunks, owner):
    """Retourne les totaux de fin de checkpoint via les decodeurs mensuels existants."""
    # Import differe : --selftest reste un programme Python standard-library pur.
    from diag_1v1_monthly import station_detail, vehicle_breakdown

    return {
        "stations": station_detail(chunks, owner)["n_stations"],
        "vehicles": vehicle_breakdown(chunks, owner)["n_units"],
    }


def yearly_states(rows, starting_year=STARTING_YEAR, ending_year=None):
    """Garde le dernier chunk de chaque annee, puis calcule les deltas depuis zero."""
    last_by_year = {}
    for row in rows:
        year = int(str(row["date"])[:4])
        if year >= starting_year and (ending_year is None or year <= ending_year):
            last_by_year[year] = row

    result = []
    previous = {0: {"stations": 0, "vehicles": 0}, 1: {"stations": 0, "vehicles": 0}}
    for year in sorted(last_by_year):
        row = last_by_year[year]
        companies = {}
        for owner, arm in ((0, "OpexAI"), (1, "AAAHogEx")):
            if "counts" in row:
                current = row["counts"][owner]
            else:
                chunks = row.get("chunks", {})
                current = game_state_counts(chunks, owner)
            companies[arm] = {
                "owner": owner,
                "stations_end": current["stations"],
                "vehicles_end": current["vehicles"],
                "stations_delta": current["stations"] - previous[owner]["stations"],
                "vehicles_delta": current["vehicles"] - previous[owner]["vehicles"],
            }
            previous[owner] = current
        result.append({"year": year, "companies": companies})
    return result


def parse_hogex_trace(output, starting_year=STARTING_YEAR):
    """Parse une seule capture complete de sous-processus, jamais chaque checkpoint."""
    counts = defaultdict(lambda: {"start": 0, "succeeded": 0, "failed": 0})
    for line in (output or "").splitlines():
        script = SCRIPT_RE.search(line)
        if not script or int(script.group(1)) != 1:
            continue
        dated = HOG_DATE_RE.match(script.group(2).strip())
        if not dated:
            continue
        year, _month, _day, detail = dated.groups()
        for marker, kind in HOG_EVENTS.items():
            if marker in detail:
                counts[int(year)][kind] += 1
                break
    return {year: dict(values) for year, values in counts.items() if year >= starting_year}


def attach_derived_metrics(years, hog_trace):
    """Ajoute ratios Opex/AAAHogEx et la trace AAAHogEx a chaque annee."""
    for record in years:
        opex = record["companies"]["OpexAI"]
        hog = record["companies"]["AAAHogEx"]
        record["delta_ratio_opex_over_hogex"] = {
            "stations": (opex["stations_delta"] / hog["stations_delta"]
                         if hog["stations_delta"] else None),
            "vehicles": (opex["vehicles_delta"] / hog["vehicles_delta"]
                         if hog["vehicles_delta"] else None),
        }
        trace = hog_trace.get(record["year"], {"start": 0, "succeeded": 0, "failed": 0})
        record["hogex_trace"] = {
            **trace,
            "success_rate": (trace["succeeded"] / trace["start"] if trace["start"] else None),
        }


def coherence(years):
    """Controle somme des variations = etat final moins etat initial (zero)."""
    result = {}
    for arm in ("OpexAI", "AAAHogEx"):
        station_sum = sum(y["companies"][arm]["stations_delta"] for y in years)
        vehicle_sum = sum(y["companies"][arm]["vehicles_delta"] for y in years)
        final = years[-1]["companies"][arm] if years else {"stations_end": 0, "vehicles_end": 0}
        result[arm] = {
            "stations_delta_sum": station_sum,
            "stations_final_minus_initial": final["stations_end"],
            "stations_match": station_sum == final["stations_end"],
            "vehicles_delta_sum": vehicle_sum,
            "vehicles_final_minus_initial": final["vehicles_end"],
            "vehicles_match": vehicle_sum == final["vehicles_end"],
        }
    return result


def cumulative(by_seed):
    """Agrege les numerateurs et denominateurs avant de former tout ratio/taux."""
    per_year = {}
    for seed_data in by_seed.values():
        for source in seed_data["years"]:
            year = source["year"]
            target = per_year.setdefault(year, {
                "year": year,
                "companies": {arm: {"owner": owner, "stations_end": 0, "vehicles_end": 0,
                                     "stations_delta": 0, "vehicles_delta": 0}
                              for arm, owner in (("OpexAI", 0), ("AAAHogEx", 1))},
                "hogex_trace": {"start": 0, "succeeded": 0, "failed": 0},
            })
            for arm in target["companies"]:
                for key in ("stations_end", "vehicles_end", "stations_delta", "vehicles_delta"):
                    target["companies"][arm][key] += source["companies"][arm][key]
            for key in ("start", "succeeded", "failed"):
                target["hogex_trace"][key] += source["hogex_trace"][key]
    years = [per_year[year] for year in sorted(per_year)]
    for record in years:
        opex, hog = record["companies"]["OpexAI"], record["companies"]["AAAHogEx"]
        record["delta_ratio_opex_over_hogex"] = {
            "stations": opex["stations_delta"] / hog["stations_delta"] if hog["stations_delta"] else None,
            "vehicles": opex["vehicles_delta"] / hog["vehicles_delta"] if hog["vehicles_delta"] else None,
        }
        trace = record["hogex_trace"]
        trace["success_rate"] = trace["succeeded"] / trace["start"] if trace["start"] else None
    return {"years": years, "coherence": coherence(years)}


def keep(row):
    """Extrait compteurs et trace HogEx en vol ; ne conserve ni chunks bruts ni logs complets."""
    chunks = row.get("chunks", {})
    output = row.get("output", "")
    counts = {
        0: game_state_counts(chunks, 0),
        1: game_state_counts(chunks, 1),
    }
    trace = parse_hogex_trace(output)
    return ({
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        "counts": counts,
        "hogex_trace": trace,
    },)


def run_campaign(args):
    # Ces imports sont volontairement ici : --selftest ne charge pas openttdlab.
    import openttdlab
    from openttdlab import bananas_ai_library, local_folder, run_experiments

    real_check_output = openttdlab.subprocess.check_output

    def check_output_with_script_debug(command, *rest, **kwargs):
        command = tuple(command)
        if any(str(item).startswith("-vnull") for item in command):
            command = command[:1] + ("-d", "script=4") + command[1:]
        return real_check_output(command, *rest, **kwargs)

    openttdlab.subprocess.check_output = check_output_with_script_debug
    import sys
    sys.path.insert(0, str(ROOT / "sweeps"))
    from bench_v2 import enable_savegame_cleanup
    enable_savegame_cleanup()

    opex = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", (("decision_log", 0),))
    hogex = local_folder(str(ROOT / "ai" / AAAHOGEX_DIR), "AAAHogEx", ())
    return list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        experiments=tuple({"seed": seed, "days": 365 * args.years, "openttd_config": CFG,
                           "ais": (opex, hogex)} for seed in args.seeds),
        max_workers=args.max_workers, result_processor=keep,
        ai_libraries=(bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                      bananas_ai_library("5046524c", "Pathfinder.Rail")),
    ))


def selftest_counts(chunks, owner):
    return {"stations": sum(1 for station in chunks["stations"] if station == owner),
            "vehicles": sum(1 for vehicle in chunks["vehicles"] if vehicle == owner)}


def selftest():
    global game_state_counts
    original = game_state_counts
    game_state_counts = selftest_counts
    try:
        rows = [
            {"date": "1970-06-01", "chunks": {"stations": [0, 1], "vehicles": [0, 1, 1]}},
            {"date": "1970-12-31", "chunks": {"stations": [0, 0, 1], "vehicles": [0, 0, 1, 1]}},
            {"date": "1971-12-31", "chunks": {"stations": [0, 0, 0, 1, 1], "vehicles": [0, 0, 0, 1, 1, 1]}},
        ]
        years = yearly_states(rows)
    finally:
        game_state_counts = original
    log = "\n".join((
        "[script:1] [1] [I] 1970-02-01 # RouteBuilder Start x",
        "[script:1] [1] [I] 1970-02-02 # RouteBuilder Succeeded x",
        "[script:1] [1] [I] 1971-03-01 # RouteBuilder Start y",
        "[script:1] [1] [I] 1971-03-02 # RouteBuilder Failed y",
        "[script:0] [1] [I] 1971-03-02 # RouteBuilder Succeeded ignored",
    ))
    attach_derived_metrics(years, parse_hogex_trace(log))
    assert [(y["companies"]["OpexAI"]["stations_delta"], y["companies"]["AAAHogEx"]["stations_delta"])
            for y in years] == [(2, 1), (1, 1)]
    assert [(y["companies"]["OpexAI"]["vehicles_delta"], y["companies"]["AAAHogEx"]["vehicles_delta"])
            for y in years] == [(2, 2), (1, 1)]
    assert years[1]["hogex_trace"] == {"start": 1, "succeeded": 0, "failed": 1, "success_rate": 0.0}
    assert all(all(values[key] for key in values if key.endswith("_match")) for values in coherence(years).values())
    print("selftest: OK")
    print("deltas stations OpexAI/AAAHogEx: 1970=2/1, 1971=1/1")
    print("deltas vehicles OpexAI/AAAHogEx: 1970=2/2, 1971=1/1")
    print("trace AAAHogEx 1971: start=1 succeeded=0 failed=1 success_rate=0.0")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=[100, 12345, 42, 7, 999])
    parser.add_argument("--max-workers", type=int, choices=range(1, 4), default=2)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "diag_1v1_chronology_6y_5seeds.json")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        selftest()
        return
    rows = run_campaign(args)
    by_seed = {}
    for seed in args.seeds:
        seed_rows = sorted((row for row in rows if row["seed"] == seed), key=lambda row: row["date"])
        years = yearly_states(seed_rows, ending_year=STARTING_YEAR + args.years - 1)
        # Une seule capture complete par graine : celle du dernier checkpoint.
        trace = (seed_rows[-1]["hogex_trace"] if seed_rows and "hogex_trace" in seed_rows[-1]
                 else parse_hogex_trace(seed_rows[-1].get("output", "")) if seed_rows else {})
        attach_derived_metrics(years, trace)
        by_seed[str(seed)] = {"years": years, "coherence": coherence(years)}
    payload = {"openttd_version": OPENTTD_VERSION, "years_requested": args.years,
               "seeds": args.seeds, "shared_game": True, "opex_decision_log": 0,
               "openttd_config": CFG, "by_seed": by_seed, "cumulative": cumulative(by_seed)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2))
    print(f"ecrit {args.out}")


if __name__ == "__main__":
    main()
