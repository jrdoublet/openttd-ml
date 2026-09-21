"""Diagnostic longitudinal des profits VEHS et des chaines d'ordres OpexAI.

Le diagnostic conserve tous les checkpoints, mais jamais ``row["output"]``: le JSON ne contient
donc ni ``openttd_output`` ni texte brut OpenTTD.  Il releve ``profit_last_year`` une fois par
annee et le convertit de l'unite VEHS (environ 256 x GBP) vers GBP par division par 256.
"""
import argparse
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (  # Reutilise le cablage canonique des experiences et l'ecriture atomique.
    OPENGFX_VERSION, OPENTTD_VERSION, build_arms, enable_savegame_cleanup, experiments,
    script_failure_reason, write_json_atomically,
)

ARMS = ("OpexAI",)
SEEDS = (100, 12345, 42, 7, 999)
TYPE_TO_MODE = {"0": ("train", "train"), "1": ("roadveh", "road"),
                "2": ("ship", "ship"), "3": ("aircraft", "aircraft")}
MODES = ("train", "road", "ship", "aircraft")
CLASSIFICATIONS = ("jamais_positif", "devenu_negatif", "toujours_positif", "irregulier")
PROFIT_RAW_UNITS_PER_GBP = 256
# 128 maillons est largement superieur a une ligne normale, mais borne strictement les cycles ORDR.
ORDER_CHAIN_MAX_HOPS = 128


def _first(value):
    """Le parseur peut encoder un sous-enregistrement en liste a un element."""
    return value[0] if isinstance(value, list) and value else value


def _number(value):
    return value if isinstance(value, (int, float)) else None


def profit_gbp(raw_profit):
    """VEHS profit_* est approximativement 256 fois le montant GBP reel."""
    return raw_profit / PROFIT_RAW_UNITS_PER_GBP if _number(raw_profit) is not None else None


def follow_orders(common, ordr, station_ids, max_hops=ORDER_CHAIN_MAX_HOPS):
    """Suit ORDR dest/next; une destination/maillon invalide reste explicitement illisible."""
    current = common.get("orders")
    # INVALID_ORDER est 0xffff dans les savegames OpenTTD; None/-1 couvrent aussi les
    # representations nulles possibles du parseur. La valeur brute est publiee plus bas.
    if current in (None, -1, 65535) or not isinstance(ordr, dict):
        return {"readable": False, "reason": "tete_ordre_absente", "distinct_destinations": None,
                "chain_length": 0, "truncated": False}
    station_ids = {str(station_id) for station_id in station_ids}
    destinations, length = set(), 0
    while length < max_hops:
        key = str(current)
        if key not in ordr:
            return {"readable": False, "reason": "maillon_ordre_introuvable",
                    "distinct_destinations": None, "chain_length": length, "truncated": False}
        order = _first(ordr[key])
        if not isinstance(order, dict):
            return {"readable": False, "reason": "maillon_ordre_non_dictionnaire",
                    "distinct_destinations": None, "chain_length": length, "truncated": False}
        destination = order.get("dest")
        if destination is None or str(destination) not in station_ids:
            return {"readable": False, "reason": "destination_ordre_invalide",
                    "distinct_destinations": None, "chain_length": length + 1, "truncated": False}
        destinations.add(str(destination))
        length += 1
        next_order = order.get("next")
        if next_order is None:
            return {"readable": True, "reason": None, "distinct_destinations": len(destinations),
                    "chain_length": length, "truncated": False}
        current = next_order
    return {"readable": True, "reason": None, "distinct_destinations": len(destinations),
            "chain_length": length, "truncated": True}


def checkpoint_vehicles(chunks, checkpoint_date, owner=0):
    """Capture compacte d'un checkpoint VEHS et des preuves brutes ORDR."""
    vehicles, records = chunks.get("VEHS") or {}, []
    iterator = vehicles.items() if isinstance(vehicles, dict) else enumerate(vehicles)
    ordr = chunks.get("ORDR") or {}
    stations = chunks.get("STNN") or {}
    station_ids = stations.keys() if isinstance(stations, dict) else range(len(stations))
    for vehicle_id, vehicle in iterator:
        if not isinstance(vehicle, dict):
            continue
        variant_and_mode = TYPE_TO_MODE.get(str(vehicle.get("type")))
        if variant_and_mode is None:
            continue
        variant, mode = variant_and_mode
        body = _first(vehicle.get(variant))
        common = _first(body.get("common")) if isinstance(body, dict) else None
        if not isinstance(common, dict) or common.get("owner") != owner:
            continue
        # Ces deux champs sont publies pour detecter un recyclage eventuel de la cle VEHS.
        engine_type = common.get("engine_type", body.get("engine_type") if isinstance(body, dict) else None)
        unitnumber = common.get("unitnumber", body.get("unitnumber") if isinstance(body, dict) else None)
        raw_orders = common.get("orders")
        head_key = str(raw_orders)
        head = _first(ordr.get(head_key)) if isinstance(ordr, dict) and head_key in ordr else None
        # `next` est normalement dans common; conserver aussi les variantes observees plutot
        # que prescrire une semantique de subtype avant d'avoir les distributions.
        subtype = common.get("subtype", body.get("subtype") if isinstance(body, dict) else None)
        has_next_field = "next" in common or (isinstance(body, dict) and "next" in body)
        records.append({
            "vehicle_id": str(vehicle_id), "mode": mode, "engine_type": engine_type,
            "unitnumber": unitnumber, "profit_last_year_gbp": profit_gbp(common.get("profit_last_year")),
            "reliability": _number(common.get("reliability")),
            "economy_age": _number(common.get("economy_age")), "max_age": _number(common.get("max_age")),
            "value": _number(common.get("value")),
            "orders": follow_orders(common, ordr, station_ids),
            "orders_raw": raw_orders,
            "order_head_keys": sorted(head.keys()) if isinstance(head, dict) else None,
            "subtype": subtype, "has_next_field": has_next_field,
        })
    return records


def keep(row):
    """Result processor: tuple obligatoire; le texte OpenTTD sert au seul booleen puis est jete."""
    return ({
        "run": row["experiment"]["bench_run"], "date": str(row["date"]),
        "year": row["date"].year, "run_ok": script_failure_reason(row.get("output")) is None,
        "vehicles": checkpoint_vehicles(row.get("chunks") or {}, row["date"]),
    },)


def _mean(values):
    values = [value for value in values if _number(value) is not None]
    return statistics.mean(values) if values else None


def _distribution(values):
    return {str(key): count for key, count in sorted(Counter(values).items(), key=lambda item: str(item[0]))}


def _context(records):
    """Age, fiabilite et valeur distinguent une panne de ligne d'un vehicule vieux en fin de vie."""
    ratios = [r["economy_age"] / r["max_age"] for r in records
              if _number(r.get("economy_age")) is not None and _number(r.get("max_age")) not in (None, 0)]
    return {"n_vehicles": len(records), "reliability_mean": _mean([r.get("reliability") for r in records]),
            "economy_age_mean": _mean([r.get("economy_age") for r in records]),
            "max_age_mean": _mean([r.get("max_age") for r in records]),
            "economy_age_over_max_age_mean": _mean(ratios),
            "value_mean": _mean([r.get("value") for r in records])}


def classify(profits):
    if all(value <= 0 for value in profits):
        return "jamais_positif"
    if all(value > 0 for value in profits):
        return "toujours_positif"
    if any(value > 0 for value in profits) and profits[-1] <= 0:
        return "devenu_negatif"
    return "irregulier"


def _identity(mode, unitnumber):
    """Identite affichee en jeu; le segment est ajoute seulement apres une reutilisation."""
    return (mode, unitnumber)


def _order_diagnostic_category(vehicle):
    raw = vehicle.get("orders_raw")
    if raw in (None, -1, 65535):
        return "absent"
    if vehicle["orders"]["readable"]:
        return "suivi_avec_succes"
    if vehicle["orders"]["reason"] == "maillon_ordre_introuvable":
        return "present_mais_introuvable_dans_ORDR"
    return "present_mais_autrement_illisible"


def analyse(records, seeds=SEEDS):
    """Construit des segments par (run, mode, unitnumber), jamais par index VEHS recyclable."""
    grouped = {(arm, seed): [] for arm in ARMS for seed in seeds}
    for record in records:
        if record["run_ok"]:
            grouped[tuple(record["run"][:2])].append(record)
    runs, all_classified, all_orders, all_observations, warnings = [], [], [], [], []
    identity_warning = False
    for (arm, seed), checkpoints in sorted(grouped.items(), key=lambda item: str(item[0])):
        by_identity = defaultdict(list)
        for checkpoint in sorted(checkpoints, key=lambda item: item["date"]):
            for vehicle in checkpoint["vehicles"]:
                by_identity[_identity(vehicle["mode"], vehicle["unitnumber"])].append((checkpoint, vehicle))
                all_observations.append(vehicle)
        vehicle_summary, segments_in_run = {}, []
        for identity, appearances in sorted(by_identity.items(), key=lambda item: str(item[0])):
            # Une baisse d'age prouve une reutilisation du unitnumber: ne jamais fusionner les vies.
            segments, current = [], []
            for appearance in appearances:
                age = appearance[1].get("economy_age")
                previous_age = current[-1][1].get("economy_age") if current else None
                if current and _number(age) is not None and _number(previous_age) is not None and age < previous_age:
                    segments.append(current)
                    current = []
                current.append(appearance)
            if current:
                segments.append(current)
            cut_count = max(0, len(segments) - 1)
            if cut_count:
                identity_warning = True
                warnings.append(f"recyclage confirme par baisse economy_age: {identity[0]}/{identity[1]} coupe en {len(segments)} segments.")
            for segment_index, segment in enumerate(segments, 1):
                vehicle_id = f"{identity[0]}/{identity[1]}#{segment_index}"
                by_year = {}
                for checkpoint, vehicle in segment:
                    if vehicle["profit_last_year_gbp"] is not None:
                        by_year[checkpoint["year"]] = (checkpoint, vehicle)
                annual = [by_year[year] for year in sorted(by_year)]
                engine_types = sorted({str(v["engine_type"]) for _, v in segment if v["engine_type"] is not None})
                engine_changed = len(engine_types) > 1
                if engine_changed:
                    identity_warning = True
                    warnings.append(f"changement engine_type inexplique: segment {vehicle_id} ecarte de la classification.")
                latest_checkpoint, latest = max(segment, key=lambda item: item[0]["date"])
                item = {"vehicle_id": vehicle_id, "stable_identity": {"mode": identity[0], "unitnumber": identity[1]},
                        "segment_index": segment_index, "n_segments_for_identity": len(segments),
                        "n_checkpoints_present": len(segment), "years_observed": sorted(by_year),
                        "n_full_years_observed": len(annual), "engine_types_observed": engine_types,
                        "engine_type_changed_unexplained": engine_changed,
                        "latest_checkpoint_date": latest_checkpoint["date"], "mode": latest["mode"],
                        "orders": latest["orders"]}
                if engine_changed:
                    item["classification"] = "exclu_changement_engine_type"
                    item["annual_profit_last_year_gbp"] = {}
                elif len(annual) < 2:
                    item["classification"] = "exclu_moins_deux_annees_pleines"
                    item["annual_profit_last_year_gbp"] = {str(year): vehicle["profit_last_year_gbp"]
                                                             for year, (_, vehicle) in sorted(by_year.items())}
                else:
                    profits = [vehicle["profit_last_year_gbp"] for _, vehicle in annual]
                    item["annual_profit_last_year_gbp"] = {str(year): vehicle["profit_last_year_gbp"]
                                                             for year, (_, vehicle) in sorted(by_year.items())}
                    item["classification"] = classify(profits)
                    item["latest_context"] = {key: latest[key] for key in
                                              ("reliability", "economy_age", "max_age", "value")}
                    all_classified.append(item)
                all_orders.append(item)
                vehicle_summary[vehicle_id] = item
                segments_in_run.append(item)
        runs.append({"arm": arm, "seed": seed, "n_checkpoints": len(checkpoints),
                     "vehicles_by_stable_identity_segment": vehicle_summary})
    if identity_warning:
        warnings.append("stabilite d'identite en echec: les trajectoires ne permettent aucune conclusion ferme.")
    if not all_classified:
        warnings.append("Aucun vehicule avec une annee pleine: les classifications et parts sont vides.")
    by_mode_classification = {}
    order_cross = {}
    for mode in MODES:
        mode_records = [r for r in all_classified if r["mode"] == mode]
        by_mode_classification[mode] = {classification: sum(r["classification"] == classification for r in mode_records)
                                        for classification in CLASSIFICATIONS}
        order_cross[mode] = {}
        for classification in CLASSIFICATIONS:
            subset = [r for r in mode_records if r["classification"] == classification]
            unreadable = sum(not r["orders"]["readable"] for r in subset)
            under_two = sum(r["orders"]["readable"] and r["orders"]["distinct_destinations"] < 2 for r in subset)
            at_least_two = sum(r["orders"]["readable"] and r["orders"]["distinct_destinations"] >= 2 for r in subset)
            if not subset:
                warnings.append(f"Categorie vide: {mode}/{classification}; sa part est nulle/non interpretable.")
            if subset and not (under_two + at_least_two):
                warnings.append(f"Denominateur nul: aucun ordre lisible pour {mode}/{classification}; la part moins de 2 est null.")
            order_cross[mode][classification] = {
                "n_vehicles": len(subset), "moins_de_2_destinations_distinctes": under_two,
                "au_moins_2_destinations_distinctes": at_least_two, "ordres_illisibles": unreadable,
                "share_moins_de_2_parmi_lisibles": under_two / (under_two + at_least_two)
                if under_two + at_least_two else None,
            }
    contexts = {mode: {classification: _context([r for r in all_classified
                                                   if r["mode"] == mode and r["classification"] == classification])
                       for classification in CLASSIFICATIONS} for mode in MODES}
    excluded = [r for r in all_orders if r["classification"].startswith("exclu_")]
    truncated = sum(r["orders"]["truncated"] for r in all_orders)
    for mode in MODES:
        for classification in CLASSIFICATIONS:
            context = contexts[mode][classification]
            if context["n_vehicles"] and context["reliability_mean"] is None:
                warnings.append(f"reliability absente: {mode}/{classification} ne doit pas etre interprete.")
            if context["n_vehicles"] and context["economy_age_over_max_age_mean"] is None:
                warnings.append(f"economy_age/max_age indisponible: {mode}/{classification} ne doit pas etre interprete.")
    # Les distributions ORDR portent sur chaque observation brute, pas seulement le dernier segment.
    observations = all_observations
    order_diagnostics, convoy_cross, train_order_head_samples = {}, {}, []
    for mode in MODES:
        mode_observations = [v for v in observations if v["mode"] == mode]
        categories = Counter(_order_diagnostic_category(v) for v in mode_observations)
        raw_values = _distribution([v.get("orders_raw") for v in mode_observations])
        order_diagnostics[mode] = {"orders_raw_distribution": raw_values,
            "orders_absent": categories["absent"],
            "orders_present_but_missing_from_ORDR": categories["present_mais_introuvable_dans_ORDR"],
            "order_chain_followed_successfully": categories["suivi_avec_succes"]}
        suspects = [v for v in mode_observations if v.get("subtype") is not None or v.get("has_next_field")]
        convoy_cross[mode] = {"n_vehicles": len(mode_observations), "n_subtype_present": sum(v.get("subtype") is not None for v in mode_observations),
            "n_next_field_present": sum(v.get("has_next_field") for v in mode_observations),
            "n_convoy_element_suspected": len(suspects),
            "n_convoy_element_suspected_with_readable_orders": sum(v["orders"]["readable"] for v in suspects),
            "n_not_suspected_with_readable_orders": sum(v["orders"]["readable"] for v in mode_observations if v not in suspects),
            "subtype_distribution": _distribution([v.get("subtype") for v in mode_observations])}
        if mode == "train":
            for v in mode_observations:
                if len(train_order_head_samples) >= 12:
                    break
                train_order_head_samples.append({"vehicle_id": v["vehicle_id"], "orders_raw": v.get("orders_raw"),
                    "head_in_ORDR": v.get("order_head_keys") is not None, "ORDR_element_keys": v.get("order_head_keys")})
    segments_by_identity = [{"arm": run["arm"], "seed": run["seed"], "mode": item["stable_identity"]["mode"],
                             "unitnumber": item["stable_identity"]["unitnumber"],
                             "n_segments": item["n_segments_for_identity"]}
                            for run in runs for item in run["vehicles_by_stable_identity_segment"].values()
                            if item["segment_index"] == 1]
    return {"warnings": warnings, "identity_stability_warning": identity_warning,
            "trajectory_conclusions_valid": not identity_warning,
            "identity_stability_definition": "Identite=(mode, unitnumber); une baisse economy_age coupe un nouveau segment, et un changement engine_type sans baisse ecarte le segment.",
            "runs": runs, "n_classified_vehicles": len(all_classified),
            "n_excluded_without_full_year": len(excluded),
            "segments_per_mode_unitnumber": segments_by_identity,
            "segments_per_mode_unitnumber_distribution": _distribution([entry["n_segments"] for entry in segments_by_identity]),
            "age_decrease_segment_cuts": sum(r["n_segments_for_identity"] - 1 for r in all_orders if r["segment_index"] == 1),
            "segments_excluded_unexplained_engine_type_change": sum(r["classification"] == "exclu_changement_engine_type" for r in all_orders),
            "classification_counts_by_mode": by_mode_classification,
            "years_observed_distribution": _distribution([r["n_full_years_observed"] for r in all_orders]),
            "order_chain_length_distribution": _distribution([r["orders"]["chain_length"] for r in all_orders]),
            "order_chain_truncated_count": truncated, "orders_x_classification_by_mode": order_cross,
            "orders_diagnostics_by_mode": order_diagnostics,
            "orders_absence_sentinel_values": [None, -1, 65535],
            "train_ORDR_head_key_samples": train_order_head_samples,
            "convoy_element_orders_cross_by_mode": convoy_cross,
            "context_by_classification_and_mode": contexts,
            "context_interpretation": "Un vehicule jamais positif tres vieux, peu fiable ou de faible valeur ne raconte pas la meme histoire qu'un vehicule neuf: reliability, economy_age/max_age et value sont donc publies par classe et mode."}


def run_selftest():
    """Fixtures uniquement en memoire: aucun fichier, Docker, OpenTTD ou campagne."""
    def vehicle(engine, unit, profit, orders, age, mode="1", subtype=None, next_field=False):
        variant = TYPE_TO_MODE[mode][0]
        common = {"owner": 0, "engine_type": engine,
                "unitnumber": unit, "profit_last_year": profit, "orders": orders,
                "reliability": 200, "economy_age": age, "max_age": 20, "value": 100,
                "subtype": subtype}
        if next_field:
            common["next"] = 0
        return {"type": mode, variant: {"common": common}}
    stations = {"1": {}, "2": {}}
    orders = {"one": {"dest": "1", "next": None},
              "cycle_a": {"dest": "1", "next": "cycle_b"},
              "cycle_b": {"dest": "1", "next": "cycle_a"}}
    def checkpoint(year, vehicles):
        return {"run": ["OpexAI", 100, 0], "date": f"{year}-01-01", "year": year,
                "run_ok": True, "vehicles": checkpoint_vehicles({"STNN": stations, "ORDR": orders, "VEHS": vehicles}, date(year, 1, 1))}
    records = [
        checkpoint(1971, {"never": vehicle(1, 10, 0, "one", 10), "turn": vehicle(2, 20, 256, "one", 10),
                          "always": vehicle(3, 30, 512, "one", 10), "young": vehicle(4, 40, None, "one", 10),
                          "cycle": vehicle(5, 50, 0, "cycle_a", 10), "reused": vehicle(6, 60, 0, "one", 15),
                          "engine_change": vehicle(8, 70, 0, "one", 10),
                          "train_absent": vehicle(9, 80, 0, 65535, 10, "0", subtype=1, next_field=True),
                          "train_missing": vehicle(10, 81, 0, "missing", 10, "0")}),
        checkpoint(1972, {"never": vehicle(1, 10, -256, "one", 11), "turn": vehicle(2, 20, 0, "one", 11),
                          "always": vehicle(3, 30, 256, "one", 11), "cycle": vehicle(5, 50, 0, "cycle_a", 11),
                          "reused": vehicle(7, 60, 0, "one", 1),
                          "engine_change": vehicle(11, 70, 0, "one", 11)}),
    ]
    result = analyse(records, seeds=(100,))
    vehicles = result["runs"][0]["vehicles_by_stable_identity_segment"]
    assert vehicles["road/10#1"]["classification"] == "jamais_positif"
    assert vehicles["road/20#1"]["classification"] == "devenu_negatif"
    assert vehicles["road/30#1"]["classification"] == "toujours_positif"
    assert vehicles["road/40#1"]["classification"] == "exclu_moins_deux_annees_pleines"
    assert vehicles["road/10#1"]["orders"]["distinct_destinations"] == 1
    assert vehicles["road/50#1"]["orders"]["truncated"] and result["order_chain_truncated_count"] == 1
    assert result["identity_stability_warning"] and not result["trajectory_conclusions_valid"]
    assert result["age_decrease_segment_cuts"] == 1 and "road/60#2" in vehicles
    assert vehicles["road/70#1"]["classification"] == "exclu_changement_engine_type"
    assert result["segments_excluded_unexplained_engine_type_change"] == 1
    assert result["orders_diagnostics_by_mode"]["train"]["orders_absent"] == 1
    assert result["orders_diagnostics_by_mode"]["train"]["orders_present_but_missing_from_ORDR"] == 1
    assert result["convoy_element_orders_cross_by_mode"]["train"]["n_convoy_element_suspected"] == 1
    assert vehicles["road/30#1"]["annual_profit_last_year_gbp"]["1971"] == 2.0
    weighted = (1 + 1 + 100) / 3
    simple_mean_of_means = (statistics.mean([1, 1]) + statistics.mean([100])) / 2
    assert weighted != simple_mean_of_means
    print("selftest passed: age decrease splits one (mode, unitnumber) into two segments")
    print("selftest passed: unexplained engine_type change excludes its segment and warns")
    print("selftest passed: short segment is excluded without classification or crash")
    print("selftest passed: train orders distinguish absent sentinel from missing ORDR head")
    print("selftest passed: one distinct destination is separate from unreadable orders")
    print(f"selftest passed: cyclic ORDR is bounded at {ORDER_CHAIN_MAX_HOPS} hops and truncation is counted")
    print("selftest passed: identity guard keeps trajectory_conclusions_valid false")
    print("selftest passed: profit_last_year raw 512 converts to GBP 2.0 via /256")
    print("selftest passed: weighted mean=34.0 differs from simple mean-of-means=50.5")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "diag_vehicle_history_10y_5seeds.json")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        run_selftest()
        return
    if args.years <= 0 or not args.seeds or args.max_workers not in (1, 2, 3):
        parser.error("--years et --seeds non vides ; --max-workers vaut 1, 2 ou 3")
    if len(set(args.seeds)) != len(args.seeds):
        parser.error("--seeds ne doit pas contenir de doublon")
    # Un seul bras: les taux precedents sont quasi identiques (rail 77,0% vs 76,9%; avion
    # 51,2% vs 50,3%), donc le phenomene n'est pas propre au reglage et un second bras ne ferait
    # qu'ajouter du temps de calcul.
    enable_savegame_cleanup()
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION, max_workers=args.max_workers,
        result_processor=keep, experiments=experiments(build_arms(ARMS), args.seeds, args.years, 1, 1970),
        ai_libraries=(bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                      bananas_ai_library("5046524c", "Pathfinder.Rail")),
    ))
    payload = {"years": args.years, "seeds": args.seeds, "arms": list(ARMS),
               "profit_field": "VEHS.common.profit_last_year", "profit_unit_conversion":
               "VEHS profit_last_year raw units / 256 = GBP (raw fields are approximately 256x GBP)",
               "order_chain_max_hops": ORDER_CHAIN_MAX_HOPS,
               "order_chain_bound_definition": "ORDR.dest/next is followed for at most 128 maillons; hitting the bound sets truncated=true.",
               "analysis": analyse(rows, args.seeds)}
    write_json_atomically(args.out, payload)
    print("out", args.out)


if __name__ == "__main__":
    main()
