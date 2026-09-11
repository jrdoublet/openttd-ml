"""Diagnostic de qualite des gares OpexAI, portfolio_v2 actif ou inactif.

Ce diagnostic lit exclusivement le chunk STNN de la derniere sauvegarde de chaque partie.  Il
ne depend d'aucune sonde Squirrel ni des journaux OpenTTD.

Piege methodologique central : les deux bras n'ont pas le meme nombre de gares. Comparer des
parts ne dit donc pas si les gares ajoutees sont mauvaises. La question est : « les ~21 gares
supplementaires sont-elles concentrees dans le bas de la distribution ? ». Les effectifs par
tranche de note, et non seulement les pourcentages, y repondent. Si v2=1 a la meme forme avec
plus de tout, la dilution vient d'ailleurs.

Les notes STNN.goods.rating sont traitees sur l'echelle 0--255 : bench_v2.station_ratings()
la documente ainsi pour OpenTTD 15.3. Cette hypothese reste a confirmer au premier diagnostic
reel en controlant minimum et maximum observes.

ARCHIVE (2026-09-11) : le bras portfolio_v2=0 (chemin legacy) a ete supprime de l'arbre lors de la
cloture de C51 (docs/taches.md). Ce script ne peut plus configurer l'IA tel quel ; conserve pour
memoire de la question deja tranchee, pas pour etre relance sans le retoucher.
"""
import argparse
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (
    OPENGFX_VERSION, OPENTTD_VERSION, build_arms, enable_savegame_cleanup,
    experiments, script_failure_reason, write_json_atomically,
)

ARMS = ("OpexAI[portfolio_v2=1]", "OpexAI[portfolio_v2=0]")
SEEDS = (100, 12345, 42, 7, 999)
RATING_BIN_WIDTH = 25
METHODOLOGY_NOTE = (
    "Les bras n'ont pas le meme nombre de gares : comparer des parts ne dit pas si les gares "
    "supplementaires sont mauvaises. La question est si elles sont concentrees dans le bas de "
    "la distribution; les effectifs par tranche, pas seulement les pourcentages, y repondent."
)


def _first(value):
    """Le parseur STNN encode parfois une liste a un element."""
    return value[0] if isinstance(value, list) and value else value


def station_records(chunks, owner=0):
    """Retourne une ligne par gare du proprietaire, sans agreger entre gares."""
    records = []
    stations = chunks.get("STNN") or {}
    values = stations.values() if isinstance(stations, dict) else stations
    for station in values:
        body = _first(station.get("normal") if isinstance(station, dict) else None)
        if body is None and isinstance(station, dict):
            body = station
        if not isinstance(body, dict):
            continue
        base = _first(body.get("base"))
        if isinstance(base, dict) and base.get("owner", owner) != owner:
            continue
        ratings, max_waiting_total, n_cargo_with_backlog, n_cargo_packets = [], 0, 0, 0
        for good in body.get("goods") or []:
            if not isinstance(good, dict):
                continue
            # max_waiting_cargo est le maximum atteint depuis le dernier recalcul de note,
            # pas le stock instantane. OpenTTD l'utilise pour penaliser la note de gare.
            max_waiting = good.get("max_waiting_cargo") or 0
            max_waiting_total += max_waiting
            if max_waiting > 0:
                n_cargo_with_backlog += 1
            cargo_packets = good.get("cargo") or []
            n_cargo_packets += len(cargo_packets) if isinstance(cargo_packets, list) else 0
            if ((good.get("status") or 0) & 1
                    and good.get("time_since_pickup", 255) < 255
                    and good.get("rating") is not None):
                ratings.append(int(good["rating"]))
        records.append({
            "n_cargo_rated": len(ratings),
            "rating_min": min(ratings) if ratings else None,
            "rating_median": statistics.median(ratings) if ratings else None,
            "rating_max": max(ratings) if ratings else None,
            "max_waiting_total": max_waiting_total,
            "n_cargo_with_backlog": n_cargo_with_backlog,
            "n_cargo_packets": n_cargo_packets,
        })
    return records


def keep(row):
    """Capture les gares de ce checkpoint; aucun openttd_output ne traverse ici."""
    return ({
        "run": row["experiment"]["bench_run"],
        "date": str(row["date"]),
        "stations": station_records(row.get("chunks") or {}),
        "run_ok": script_failure_reason(row.get("output")) is None,
    },)


def final_rows(rows):
    """Un seul dernier checkpoint par partie, pour eviter tout double comptage."""
    by_run = {}
    for row in rows:
        by_run.setdefault(tuple(row["run"]), []).append(row)
    final = []
    for run, series in sorted(by_run.items(), key=lambda item: str(item[0])):
        latest = max(series, key=lambda row: row["date"])
        final.append({"arm": run[0], "seed": run[1], "last_date": latest["date"],
                      "stations": latest["stations"], "run_ok": latest["run_ok"]})
    return final


def quantile(values, fraction):
    """Quantile lineaire inclusif, defini aussi pour les petits echantillons."""
    values = sorted(values)
    if not values:
        return None
    position = (len(values) - 1) * fraction
    lower, upper = int(position), min(int(position) + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def deciles(values):
    return {str(percent): quantile(values, percent / 100) for percent in range(0, 101, 10)}


def rating_bins(stations):
    """Effectifs (jamais parts) dans les tranches 0-24 ... 250-255."""
    bins = [{"lower": lower, "upper": min(lower + RATING_BIN_WIDTH - 1, 255), "n_stations": 0}
            for lower in range(0, 256, RATING_BIN_WIDTH)]
    unrated = 0
    for station in stations:
        rating = station["rating_median"]
        if rating is None:
            unrated += 1
            continue
        index = min(int(rating) // RATING_BIN_WIDTH, len(bins) - 1)
        bins[index]["n_stations"] += 1
    return {"bins": bins, "n_unrated": unrated}


def thresholds(control_stations):
    """Seuils communs : Q1 des notes et Q3 du backlog, calcules sur v2=0 uniquement."""
    return {
        "rating_median_q1": quantile(
            [station["rating_median"] for station in control_stations
             if station["rating_median"] is not None], .25),
        "max_waiting_total_q3": quantile(
            [station["max_waiting_total"] for station in control_stations], .75),
    }


def congested_category_warning(common_thresholds):
    """Signale qu'un seuil nul rend la categorie engorgee non fiable."""
    zero_thresholds = [name for name, value in common_thresholds.items() if value == 0]
    if not zero_thresholds:
        return None
    return (
        "Categorie gare engorgee degeneree : au moins un seuil de quartile temoin vaut 0 "
        f"({', '.join(zero_thresholds)}); ce seuil nul rend la categorie non fiable. "
        "Cette categorie ne doit pas etre lue."
    )


def station_summary(stations, other_backlog_median, common_thresholds):
    ratings = [station["rating_median"] for station in stations if station["rating_median"] is not None]
    backlogs = [station["max_waiting_total"] for station in stations]
    dead = [station for station in stations
            if (station["n_cargo_rated"] == 0 and station["max_waiting_total"] == 0
                and station["n_cargo_packets"] == 0)]
    q1, q3 = common_thresholds["rating_median_q1"], common_thresholds["max_waiting_total_q3"]
    congested = [station for station in stations if q1 is not None and q3 is not None
                 and station["rating_median"] is not None
                 and station["rating_median"] <= q1 and station["max_waiting_total"] >= q3]
    above_other = (sum(backlog > other_backlog_median for backlog in backlogs)
                   if other_backlog_median is not None else None)
    return {
        "n_stations": len(stations),
        "rating_median_deciles": deciles(ratings),
        "rating_distribution": rating_bins(stations),
        "max_waiting_total_deciles": deciles(backlogs),
        "n_max_waiting_above_other_arm_median": above_other,
        "share_max_waiting_above_other_arm_median": (above_other / len(stations) if above_other is not None and stations else None),
        "other_arm_max_waiting_total_median": other_backlog_median,
        "dead_stations": {"n": len(dead), "share": len(dead) / len(stations) if stations else None},
        "congested_stations": {"n": len(congested), "share": len(congested) / len(stations) if stations else None},
    }


def analyse_grouped(records):
    """Agregats par graine et cumules; les effectifs sont toujours sommes, jamais moyens."""
    grouped = defaultdict(list)
    for record in records:
        if record["run_ok"]:
            grouped[record["arm"], record["seed"]].extend(record["stations"])
    result = {"per_seed": [], "cumulative": {}}
    for seed in sorted({seed for _, seed in grouped}):
        station_sets = {arm: grouped[arm, seed] for arm in ARMS}
        control_thresholds = thresholds(station_sets[ARMS[1]])
        result["per_seed"].append({
            "seed": seed, "engorged_thresholds_from_control_v2_0": control_thresholds,
            "congested_category_warning": congested_category_warning(control_thresholds),
            "arms": {arm: station_summary(
                station_sets[arm], quantile([s["max_waiting_total"] for s in station_sets[other]], .5),
                control_thresholds)
                     for arm, other in ((ARMS[0], ARMS[1]), (ARMS[1], ARMS[0]))},
        })
    cumulative_sets = {arm: [station for (name, _), stations in grouped.items() if name == arm
                             for station in stations] for arm in ARMS}
    control_thresholds = thresholds(cumulative_sets[ARMS[1]])
    result["cumulative"] = {
        "engorged_thresholds_from_control_v2_0": control_thresholds,
        "congested_category_warning": congested_category_warning(control_thresholds),
        "arms": {arm: station_summary(
            cumulative_sets[arm], quantile([s["max_waiting_total"] for s in cumulative_sets[other]], .5),
            control_thresholds)
                 for arm, other in ((ARMS[0], ARMS[1]), (ARMS[1], ARMS[0]))},
    }
    return result


def run_selftest():
    """Chunks factices conformes a STNN.goods pour morts, backlog et seuil nul."""
    def good(rating, max_waiting_cargo, cargo, status=1, time_since_pickup=1):
        """Toutes les cles observees d'un GoodsEntry sont presentes, sans cle inventee."""
        return {
            "status": status,
            "time_since_pickup": time_since_pickup,
            "rating": rating,
            "last_speed": 0,
            "last_age": 0,
            "amount_fract": 0,
            "cargo.reserved_count": 0,
            "link_graph": 0,
            "node": 0,
            "max_waiting_cargo": max_waiting_cargo,
            "flow": [],
            "cargo": cargo,
        }

    def chunks(specifications):
        return {"STNN": {str(index): {"normal": {"base": {"owner": 0}, "goods": goods}}
                         for index, goods in enumerate(specifications)}}

    # v2=0: 68 gares, dont une morte; les quartiles inclusifs attendus sont 35 et 32,5.
    packet = [{"first": 65535, "second": [170]}]
    dead_good = good(175, 0, [], status=0, time_since_pickup=255)
    control = ([[dead_good]] + [[good(10, 100, packet)] for _ in range(17)] +
               [[good(60, 10, packet)] for _ in range(25)] +
               [[good(130, 0, [])] for _ in range(25)])
    # v2=1: 89 gares, dont deux mortes, et davantage de gares dans la tranche basse.
    treatment = ([[dead_good]] * 2 + [[good(10, 20, packet)] for _ in range(30)] +
                 [[good(60, 0, [])] for _ in range(30)] +
                 [[good(130, 2, packet)] for _ in range(27)])
    records = [
        {"arm": ARMS[1], "seed": 1, "run_ok": True, "stations": station_records(chunks(control))},
        {"arm": ARMS[0], "seed": 1, "run_ok": True, "stations": station_records(chunks(treatment))},
    ]
    analysed = analyse_grouped(records)
    cumulative = analysed["cumulative"]
    baseline = cumulative["arms"][ARMS[1]]
    candidate = cumulative["arms"][ARMS[0]]
    assert baseline["n_stations"] == 68 and candidate["n_stations"] == 89
    assert baseline["dead_stations"]["n"] == 1 and candidate["dead_stations"]["n"] == 2
    assert cumulative["engorged_thresholds_from_control_v2_0"] == {"rating_median_q1": 35.0, "max_waiting_total_q3": 32.5}
    assert cumulative["congested_category_warning"] is None
    assert baseline["congested_stations"]["n"] == 17
    low_bin = baseline["rating_distribution"]["bins"][0]["n_stations"]
    assert low_bin == 17 and candidate["rating_distribution"]["bins"][0]["n_stations"] == 30
    weighted = (1 + 1 + 100) / 3
    unweighted_means = (statistics.mean([1, 1]) + statistics.mean([100])) / 2
    assert weighted != unweighted_means
    print("selftest passed: stations v2=1/v2=0 = 89/68; dead = 2/1")
    print("selftest passed: control thresholds q1_rating=35.0 q3_max_waiting=32.5; congested control=17")
    print("selftest passed: low rating-bin counts v2=1/v2=0 = 30/17")
    print("selftest passed: weighted mean=34.0 differs from mean of means=50.5")

    zero_control = station_records(chunks([[good(10, 0, [])], [good(20, 0, [])]]))
    zero_thresholds = thresholds(zero_control)
    warning = congested_category_warning(zero_thresholds)
    assert zero_thresholds["max_waiting_total_q3"] == 0
    assert warning == (
        "Categorie gare engorgee degeneree : au moins un seuil de quartile temoin vaut 0 "
        "(max_waiting_total_q3); ce seuil nul rend la categorie non fiable. "
        "Cette categorie ne doit pas etre lue."
    )
    print("selftest passed: zero control Q3 triggers explicit congested-category warning")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "diag_station_quality_10y_5seeds.json")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        run_selftest()
        return
    if args.years <= 0 or not args.seeds or args.max_workers not in (1, 2, 3):
        parser.error("--years et --seeds non vides ; --max-workers vaut 1, 2 ou 3")
    if len(set(args.seeds)) != len(args.seeds):
        parser.error("--seeds ne doit pas contenir de doublon")

    enable_savegame_cleanup()
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers, result_processor=keep,
        experiments=experiments(build_arms(ARMS), args.seeds, args.years, 1, 1970),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    final = final_rows(rows)
    failed = [{key: value for key, value in record.items() if key != "stations"}
              for record in final if not record["run_ok"]]
    payload = {
        "years": args.years, "seeds": args.seeds, "arms": list(ARMS),
        "rating_scale": {"minimum": 0, "maximum": 255, "bin_width": RATING_BIN_WIDTH,
                         "basis": "bench_v2.station_ratings documents STNN.goods.rating as 0-255"},
        "methodology_note": METHODOLOGY_NOTE,
        "max_waiting_total_definition": (
            "Somme de STNN.goods[].max_waiting_cargo par gare : maximum atteint depuis le "
            "dernier recalcul de note, pas un stock instantane. C'est la grandeur qu'OpenTTD "
            "utilise pour penaliser la note de gare."
        ),
        "n_cargo_with_backlog_definition": (
            "Nombre de cargos de la gare dont STNN.goods[].max_waiting_cargo est strictement "
            "superieur a 0."
        ),
        "n_cargo_packets_definition": (
            "Somme des longueurs de STNN.goods[].cargo par gare : indicateur brut que du fret "
            "est physiquement present, sans quantite."
        ),
        "waiting_quantity_extraction_note": (
            "La quantite exacte de fret en attente n'est pas extraite. Une jointure des paquets "
            "vers CAPA/CAPY est la piste si elle est voulue un jour, mais elle n'est pas tentee "
            "ici car les identifiants ne sont pas verifies."
        ),
        "dead_station_definition": (
            "n_cargo_rated == 0 and max_waiting_total == 0 and n_cargo_packets == 0"
        ),
        "congested_station_definition": (
            "rating_median <= control Q1 and max_waiting_total >= control Q3; les deux "
            "quartiles sont calcules sur OpexAI[portfolio_v2=0]"
        ),
        "congested_category_warning_definition": (
            "Si un seuil de quartile temoin vaut 0, congested_category_warning est explicite : "
            "la categorie est degeneree et ne doit pas etre lue."
        ),
        "final_runs": final,
        "analysis": analyse_grouped(final),
        "failed_runs": failed, "failed_run_count": len(failed),
    }
    write_json_atomically(args.out, payload)
    print("failed", len(failed), "out", args.out)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
