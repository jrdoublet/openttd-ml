"""RVA-07, calcul passif. Aucun score, commande de jeu ou coefficient ajusté.

Le trajet est une entrée C41 (snapshot du candidat), pas distance/vitesse max.
Chaque cargo porte sa capacité par rame et son séjour par extrémité. Le profil
parallèle prend le maximum des séjours des cargos, jamais leur somme. Attente
de production et chargement mécanique sont des entrées distinctes.
"""
import math


def known(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def dry_cycle(one_way_days, trains, cargos, *, waiting_a_days, waiting_b_days,
              rating_anchor_pct, parallel_loading):
    """Deux directions chargées ; monthly = demande totale des deux extrémités.

    Les capacités de cargos distincts ne sont jamais additionnées. La note est
    le proxy Opex existant, pas une note moteur mesurée. Sans demande, l'offre
    et le débit restent inconnus ; sans physique couverte, aucune durée inventée.
    """
    result = {"coverage": "not_covered", "cycle_days": None, "cargos": [],
              "travel_source": "C41_candidate_snapshot", "rating_source": "Opex_headway_proxy",
              "delivered_rate": None}
    if (not known(one_way_days) or one_way_days <= 0 or not known(trains) or trains < 1
            or int(trains) != trains or not cargos or parallel_loading is not True
            or not known(rating_anchor_pct) or not 0 <= rating_anchor_pct <= 100
            or any(not known(v) or v < 0 for v in (waiting_a_days, waiting_b_days))):
        return result
    if len({c.get("cargo") for c in cargos}) != len(cargos):
        raise ValueError("Un cargo doit agréger ses éléments avant le calcul du cycle")
    for cargo in cargos:
        if (cargo.get("cargo") is None or any(not known(cargo.get(k)) or cargo[k] < 0
                for k in ("capacity", "dwell_a_days", "dwell_b_days"))):
            return result
    dwell_a = max(c["dwell_a_days"] for c in cargos)
    dwell_b = max(c["dwell_b_days"] for c in cargos)
    cycle = 2 * one_way_days + dwell_a + dwell_b + waiting_a_days + waiting_b_days
    headway = cycle / trains
    pickup = next((p for threshold, p in ((7.5, 130), (15, 95), (30, 50), (52.5, 25))
                   if headway < threshold), 0)
    rating = max(0, min(100, 100 * (rating_anchor_pct * 255 / 100 - 95 + pickup) / 255))
    departures = 2 * 30 / cycle  # Existing model month: 30 days, two loaded legs.
    result.update(coverage="estimated", cycle_days=cycle, one_way_days=one_way_days,
                  dwell_a_days=dwell_a, dwell_b_days=dwell_b, headway_days=headway,
                  rating_pct=rating, loaded_legs_per_train_month=departures)
    for cargo in cargos:
        demand = cargo.get("monthly")
        offer = demand * rating / 100 if known(demand) and demand >= 0 else None
        capacity = trains * cargo["capacity"] * departures
        result["cargos"].append({"cargo": cargo["cargo"], "capacity_month": capacity,
            "offered_month": offer, "carried_month": min(offer, capacity) if offer is not None else None,
            "unit": "cargo_units_per_model_30day_month"})
    return result


def from_snapshot(model):
    """Rejeu des anciens clichés : séjour commun hérité, explicitement estimé.

    Ne prétend pas reconstituer le chargement propre du courrier, absent des
    anciens logs. Les nouvelles entrées par cargo peuvent appeler dry_cycle.
    """
    trips, travel = model.get("trips_month"), model.get("one_way_days")
    if not known(trips) or trips <= 0 or not known(travel):
        return {"coverage": "not_covered"}
    dwell = 30 / trips - travel
    cargos = []
    for suffix in ("", "2"):
        cap = model.get("per_train" + suffix)
        if known(cap) and cap > 0:
            cargos.append({"cargo": model.get("cargo" + suffix), "capacity": cap,
                "monthly": model.get("monthly" + suffix), "dwell_a_days": dwell, "dwell_b_days": dwell})
    result = dry_cycle(travel, model.get("trains"), cargos, waiting_a_days=0,
        waiting_b_days=0, rating_anchor_pct=50, parallel_loading=True)
    result["dwell_source"] = "legacy_primary_shared_assumption"
    result["mixed_loading_coverage"] = "not_covered" if len(cargos) > 1 else "estimated"
    result["waiting_source"] = "pax_orders_without_full_load_assumption"
    return result
