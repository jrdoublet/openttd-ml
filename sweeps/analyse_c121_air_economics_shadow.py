#!/usr/bin/env python3
"""Compare C121 build-time shadow predictions with mature C117 observations."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from analyse_c117_aggregate import aggregate
from c121_airport_source import at_large_runway_profile


def ratio(actual, predicted):
    if not isinstance(actual, (int, float)) or not isinstance(predicted, (int, float)) or predicted <= 0:
        return None
    return float(actual) / float(predicted)


def stats(values):
    values = [float(v) for v in values if isinstance(v, (int, float)) and math.isfinite(float(v))]
    if not values:
        return {"n": 0, "mean": None, "median": None, "p25": None, "p75": None}
    ordered = sorted(values)

    def q(frac):
        pos = (len(ordered) - 1) * frac
        lo = int(math.floor(pos))
        hi = int(math.ceil(pos))
        if lo == hi:
            return ordered[lo]
        return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)

    return {
        "n": len(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "p25": q(0.25),
        "p75": q(0.75),
    }


def _pickup_rating_points(headway_days):
    if headway_days < 7.5:
        return 130
    if headway_days < 15.0:
        return 95
    if headway_days < 30.0:
        return 50
    if headway_days < 52.5:
        return 25
    return 0


def _stock_rating_points(waiting):
    points = -90
    if waiting <= 1500:
        points += 55
    if waiting <= 1000:
        points += 35
    if waiting <= 600:
        points += 10
    if waiting <= 300:
        points += 20
    if waiting <= 100:
        points += 10
    return points


STATION_RATING_INTERVAL_DAYS = 185.0 / 74.0
INITIAL_STATION_RATING = 175


def _source_pickup_rating_points(intervals_since_pickup):
    if intervals_since_pickup <= 3:
        return 130
    if intervals_since_pickup <= 6:
        return 95
    if intervals_since_pickup <= 12:
        return 50
    if intervals_since_pickup <= 21:
        return 25
    return 0


def _average_pickup_rating_points(headway_days):
    """Long-run mean of OpenTTD 15.3 pickup-rating buckets."""
    if not isinstance(headway_days, (int, float)) or headway_days <= 0:
        return 0.0
    interval = STATION_RATING_INTERVAL_DAYS
    edges = ((0.0, 3.0 * interval, 130.0),
             (3.0 * interval, 6.0 * interval, 95.0),
             (6.0 * interval, 12.0 * interval, 50.0),
             (12.0 * interval, 21.0 * interval, 25.0))
    area = 0.0
    h = float(headway_days)
    for start, stop, points in edges:
        area += max(0.0, min(h, stop) - start) * points
    return area / h


def _source_rating_replay(base_without_pickup, capturable_monthly, headway_days,
                           capacity_per_visit):
    """Replay deterministe du rating station+cargo OpenTTD 15.3."""
    values = (base_without_pickup, capturable_monthly, headway_days, capacity_per_visit)
    if not all(isinstance(value, (int, float)) for value in values):
        return None
    if headway_days <= 0 or capacity_per_visit <= 0 or capturable_monthly < 0:
        return None

    interval = STATION_RATING_INTERVAL_DAYS
    rating = float(INITIAL_STATION_RATING)
    waiting = 0.0
    max_waiting = 0.0
    intervals_since_pickup = 0
    now = 0.0
    next_rating = interval
    next_pickup = float(headway_days)
    mature_ratings = []

    # Le rating est un octet et bouge de 2 points/update au plus. 4*256
    # updates laissent plusieurs cycles apres relaxation; on mesure les 256 derniers.
    for update_index in range(4 * 256):
        while next_pickup <= next_rating + 1.0e-9:
            elapsed = max(0.0, next_pickup - now)
            waiting += float(capturable_monthly) * rating / 255.0 * elapsed / 30.4
            now = next_pickup
            waiting = max(0.0, waiting - float(capacity_per_visit))
            intervals_since_pickup = 0
            next_pickup += float(headway_days)

        elapsed = max(0.0, next_rating - now)
        waiting += float(capturable_monthly) * rating / 255.0 * elapsed / 30.4
        now = next_rating
        intervals_since_pickup = min(255, intervals_since_pickup + 1)
        target = (
            float(base_without_pickup)
            + _source_pickup_rating_points(intervals_since_pickup)
            + _stock_rating_points(max_waiting)
        )
        target = max(0.0, min(255.0, target))
        rating += max(-2.0, min(2.0, target - rating))
        rating = max(0.0, min(255.0, rating))
        # Le source note d'abord l'ancien max_waiting_cargo puis le remplace
        # par waiting_avg; en distribution manuelle waiting_avg = waiting / 2.
        max_waiting = waiting / 2.0
        next_rating += interval
        if update_index >= 3 * 256:
            mature_ratings.append(rating)

    return statistics.fmean(mature_ratings)


def _rating_target(base_without_pickup, capturable_monthly, headway_days, capacity_per_visit):
    base = float(base_without_pickup) + _pickup_rating_points(headway_days)
    rating = 175
    seen = set()
    while rating not in seen:
        seen.add(rating)
        offered = float(capturable_monthly) * rating / 255.0 if capturable_monthly > 0 else 0.0
        waiting_upper = offered * headway_days / 30.4
        stock = (
            _stock_rating_points(waiting_upper / 2.0)
            if capacity_per_visit > 0 and waiting_upper <= capacity_per_visit
            else -90
        )
        target = max(0, min(255, int(base + stock)))
        if target == rating:
            break
        if target in seen:
            if capturable_monthly > 0 and headway_days > 0 and capacity_per_visit > 0:
                rating = int(
                    capacity_per_visit * 30.4 * 255.0
                    / (float(capturable_monthly) * headway_days)
                )
                rating = max(0, min(255, rating))
            elif target < rating:
                rating = target
            break
        rating = target
    return rating


def _rating_target_average_pickup(base_without_pickup, capturable_monthly,
                                  headway_days, capacity_per_visit):
    base = float(base_without_pickup) + _average_pickup_rating_points(headway_days)
    rating = 175
    seen = set()
    while rating not in seen:
        seen.add(rating)
        offered = float(capturable_monthly) * rating / 255.0 if capturable_monthly > 0 else 0.0
        waiting_upper = offered * headway_days / 30.4
        stock = (
            _stock_rating_points(waiting_upper / 2.0)
            if capacity_per_visit > 0 and waiting_upper <= capacity_per_visit
            else -90
        )
        target = max(0, min(255, int(base + stock)))
        if target == rating:
            break
        if target in seen:
            if capturable_monthly > 0 and headway_days > 0 and capacity_per_visit > 0:
                rating = int(
                    capacity_per_visit * 30.4 * 255.0
                    / (float(capturable_monthly) * headway_days)
                )
                rating = max(0, min(255, rating))
            elif target < rating:
                rating = target
            break
        rating = target
    return rating


def _source_air_loading_dwell_days(pax_a, pax_b, mail_a, mail_b, departures):
    """OpenTTD 15.3 base-aircraft loading dwell for one airport visit.

    Original aircraft have EngineInfo.load_amount=20. With gradual_loading
    (default on), aircraft wait 20 ticks between slices; the secondary MAIL
    part uses ceil(load_amount/4)=5. PASS and MAIL parts are processed in
    parallel, while each part unloads before it can load again. PrepareUnload
    adds the initial one-tick delay. No empirical coefficient is used here.
    """
    if departures <= 0:
        return 0.0

    def slices(monthly, amount):
        per_visit = max(0.0, float(monthly)) / float(departures)
        if per_visit <= 0:
            return 0
        return int(math.ceil(per_visit / float(amount) - 1.0e-12))

    pax_rounds = slices(pax_a, 20) + slices(pax_b, 20)
    mail_rounds = slices(mail_a, 5) + slices(mail_b, 5)
    rounds = max(pax_rounds, mail_rounds)
    return (1.0 + 20.0 * rounds) / 74.0


def _source_city_runway_service_days():
    """AT_LARGE RunwayInOut service proxy from OpenTTD 15.3 source only.

    The city-airport FTA holds the shared RunwayInOut over takeoff positions
    9->10->11->12 and landing positions 13->14->15->17. AirportClearBlock
    reserves the next block before movement and releases the old block once the
    aircraft reaches the first position outside it. The occupied paths are
    8->9->10->11 on take-off and 13->14->15->17 on landing. Their movement-data
    coordinates yield 260 axial pixel steps plus 30 diagonal steps per complete
    visit (one takeoff + one landing). NoAI does not expose aircraft
    acceleration, so all occupied segments are conservatively advanced at the
    source taxi limit (50). UpdateAircraftSpeed runs twice per tick and the old
    movement code applies integer speed*3/4 on axial motion; OpenTTD uses 74
    ticks/day. This is a physical source approximation, not a fitted constant.
    """
    taxi_speed = 50
    ticks_per_day = 74.0
    progress_per_pixel = 256.0
    updates_per_tick = 2.0
    axial_progress = (taxi_speed * 3) // 4
    diagonal_progress = taxi_speed
    axial_pixels_per_day = (
        updates_per_tick * axial_progress * ticks_per_day / progress_per_pixel
    )
    diagonal_pixels_per_day = (
        updates_per_tick * diagonal_progress * ticks_per_day / progress_per_pixel
    )
    return 260.0 / axial_pixels_per_day + 30.0 / diagonal_pixels_per_day


def _manual_fifo_candidate_monthly(raw_monthly, rating_points,
                                   candidate_pickup, candidate_capacity,
                                   existing_pickup, existing_capacity_rate):
    """Part candidat sous distribution manuelle OpenTTD, sans fit empirique.

    Le cargo attend dans un stock commun. Tant qu'aucun groupe ne sature sa
    capacite par visite, chaque passage rencontre en moyenne la meme quantite
    de stock et le partage suit donc la frequence des visites. Si un groupe
    sature, son excedent reste disponible pour l'autre groupe. Cette
    conservation de flux donne un water-filling ferme a deux groupes.
    """
    demand_day = max(0.0, float(raw_monthly)) * float(rating_points) / 255.0 / 30.4
    rc = max(0.0, float(candidate_pickup))
    re = max(0.0, float(existing_pickup))
    cc = max(0.0, float(candidate_capacity))
    existing_rate = max(0.0, float(existing_capacity_rate))
    candidate_rate = rc * cc
    total_capacity = candidate_rate + existing_rate
    if rc <= 0.0 or demand_day <= 0.0 or total_capacity <= 0.0:
        return 0.0
    target = min(demand_day, total_capacity)
    if re <= 0.0 or existing_rate <= 0.0:
        return 30.4 * min(target, candidate_rate)
    ce = existing_rate / re
    common_rate = rc + re
    first_cap = min(cc, ce)
    if target <= common_rate * first_cap:
        return 30.4 * rc * target / common_rate
    if cc <= ce:
        candidate_day = candidate_rate
    else:
        candidate_day = min(candidate_rate, target - existing_rate)
    return 30.4 * max(0.0, candidate_day)


def replay_fleet(build, one_way_override=None, fleet_cap_override=None,
                 airport_slot_days=None, fixed_planes=None, source_loading=False,
                 source_rating=False, average_pickup_rating=False,
                 source_queue=False, manual_fifo_share=False,
                 candidate_pickup_override=None):
    """Replay hors jeu de la boucle de flotte C121 avec les champs C121_BUILD."""
    required = (
        "pax_raw_a", "pax_raw_b", "mail_raw_a", "mail_raw_b",
        "pax_cap", "mail_cap", "one_way_days",
        "existing_pickup_a", "existing_pickup_b",
        "existing_pax_rate_a", "existing_pax_rate_b",
        "existing_mail_rate_a", "existing_mail_rate_b",
        "rating_base_a", "rating_base_b",
        "pax_income", "mail_income", "fleet_scan_cap",
        "actual_n", "actual_vehicle_running", "actual_vehicle_amort",
        "actual_infra_running", "actual_infra_amort",
        "plane_price", "airport_capital",
    )
    if not all(isinstance(build.get(key), (int, float)) for key in required):
        return None
    actual_n = int(build["actual_n"])
    one_way = (
        float(one_way_override)
        if isinstance(one_way_override, (int, float)) and one_way_override > 0
        else float(build["one_way_days"])
    )
    round_trip = 2.0 * one_way
    fleet_cap = int(build["fleet_scan_cap"])
    if isinstance(fleet_cap_override, (int, float)) and fleet_cap_override > 0:
        fleet_cap = min(fleet_cap, int(fleet_cap_override))
    if actual_n <= 0 or round_trip <= 0 or fleet_cap <= 0:
        return None
    pax_cap = float(build["pax_cap"])
    mail_cap = float(build["mail_cap"])
    if pax_cap <= 0 or mail_cap < 0:
        return None
    plane_running = float(build["actual_vehicle_running"]) / actual_n
    plane_amort = float(build["actual_vehicle_amort"]) / actual_n
    infra_running = float(build["actual_infra_running"])
    infra_amort = float(build["actual_infra_amort"])
    plane_price = float(build["plane_price"])
    airport_capital = float(build["airport_capital"])
    kdec = build.get("model_kdec", build.get("decision_kdec", 0))
    kdec = max(0.0, float(kdec)) if isinstance(kdec, (int, float)) else 0.0
    runway_profile = (
        at_large_runway_profile(int(build["engine"]))
        if source_queue and isinstance(build.get("engine"), (int, float)) else None
    )

    def evaluate_once(planes, effective_round_trip):
        requested_pickup = (
            float(candidate_pickup_override)
            if isinstance(candidate_pickup_override, (int, float))
            and candidate_pickup_override > 0
            else float(planes) / effective_round_trip
        )
        existing_pickup_a = float(build["existing_pickup_a"])
        existing_pickup_b = float(build["existing_pickup_b"])
        requested_station_a = existing_pickup_a + requested_pickup
        requested_station_b = existing_pickup_b + requested_pickup
        scale_a = 1.0
        scale_b = 1.0
        if isinstance(airport_slot_days, (int, float)) and airport_slot_days > 0:
            slot_rate = 1.0 / float(airport_slot_days)
            if requested_station_a > slot_rate:
                scale_a = slot_rate / requested_station_a
            if requested_station_b > slot_rate:
                scale_b = slot_rate / requested_station_b
        candidate_pickup = requested_pickup * min(scale_a, scale_b)
        existing_effective_a = existing_pickup_a * scale_a
        existing_effective_b = existing_pickup_b * scale_b
        station_pickup_a = existing_effective_a + candidate_pickup
        station_pickup_b = existing_effective_b + candidate_pickup
        candidate_pax_rate = pax_cap * candidate_pickup
        candidate_mail_rate = mail_cap * candidate_pickup

        def share(candidate_rate, existing_rate):
            total = float(existing_rate) + candidate_rate
            return candidate_rate / total if total > 0 else 1.0

        pax_share_a = share(candidate_pax_rate, float(build["existing_pax_rate_a"]) * scale_a)
        pax_share_b = share(candidate_pax_rate, float(build["existing_pax_rate_b"]) * scale_b)
        mail_share_a = share(candidate_mail_rate, float(build["existing_mail_rate_a"]) * scale_a)
        mail_share_b = share(candidate_mail_rate, float(build["existing_mail_rate_b"]) * scale_b)
        headway = 1.0 / candidate_pickup if candidate_pickup > 0 else 1.0e9
        station_headway_a = 1.0 / station_pickup_a if station_pickup_a > 0 else headway
        station_headway_b = 1.0 / station_pickup_b if station_pickup_b > 0 else headway
        pax_visit_a = (
            (float(build["existing_pax_rate_a"]) * scale_a + candidate_pax_rate) / station_pickup_a
            if station_pickup_a > 0 else pax_cap
        )
        pax_visit_b = (
            (float(build["existing_pax_rate_b"]) * scale_b + candidate_pax_rate) / station_pickup_b
            if station_pickup_b > 0 else pax_cap
        )
        mail_visit_a = (
            (float(build["existing_mail_rate_a"]) * scale_a + candidate_mail_rate) / station_pickup_a
            if station_pickup_a > 0 else mail_cap
        )
        mail_visit_b = (
            (float(build["existing_mail_rate_b"]) * scale_b + candidate_mail_rate) / station_pickup_b
            if station_pickup_b > 0 else mail_cap
        )
        rating_fn = (
            _source_rating_replay if source_rating
            else (_rating_target_average_pickup if average_pickup_rating else _rating_target)
        )
        rp_a = rating_fn(build["rating_base_a"], build["pax_raw_a"], station_headway_a, pax_visit_a)
        rp_b = rating_fn(build["rating_base_b"], build["pax_raw_b"], station_headway_b, pax_visit_b)
        rm_a = rating_fn(build["rating_base_a"], build["mail_raw_a"], station_headway_a, mail_visit_a)
        rm_b = rating_fn(build["rating_base_b"], build["mail_raw_b"], station_headway_b, mail_visit_b)
        if None in (rp_a, rp_b, rm_a, rm_b):
            return None
        departures = 30.4 * candidate_pickup
        pax_dir = pax_cap * departures
        mail_dir = mail_cap * departures
        if manual_fifo_share:
            carried_pax_a = int(_manual_fifo_candidate_monthly(
                build["pax_raw_a"], rp_a, candidate_pickup, pax_cap,
                existing_effective_a, float(build["existing_pax_rate_a"]) * scale_a))
            carried_pax_b = int(_manual_fifo_candidate_monthly(
                build["pax_raw_b"], rp_b, candidate_pickup, pax_cap,
                existing_effective_b, float(build["existing_pax_rate_b"]) * scale_b))
            carried_mail_a = int(_manual_fifo_candidate_monthly(
                build["mail_raw_a"], rm_a, candidate_pickup, mail_cap,
                existing_effective_a, float(build["existing_mail_rate_a"]) * scale_a))
            carried_mail_b = int(_manual_fifo_candidate_monthly(
                build["mail_raw_b"], rm_b, candidate_pickup, mail_cap,
                existing_effective_b, float(build["existing_mail_rate_b"]) * scale_b))
        else:
            offered_pax_a = float(build["pax_raw_a"]) * rp_a / 255.0 * pax_share_a
            offered_pax_b = float(build["pax_raw_b"]) * rp_b / 255.0 * pax_share_b
            offered_mail_a = float(build["mail_raw_a"]) * rm_a / 255.0 * mail_share_a
            offered_mail_b = float(build["mail_raw_b"]) * rm_b / 255.0 * mail_share_b
            carried_pax_a = int(min(offered_pax_a, pax_dir))
            carried_pax_b = int(min(offered_pax_b, pax_dir))
            carried_mail_a = int(min(offered_mail_a, mail_dir))
            carried_mail_b = int(min(offered_mail_b, mail_dir))
        carried_pax = carried_pax_a + carried_pax_b
        carried_mail = carried_mail_a + carried_mail_b
        revenue = (
            int(12.0 * carried_pax * float(build["pax_income"]))
            + int(12.0 * carried_mail * float(build["mail_income"]))
        )
        running = planes * plane_running + infra_running
        amort = planes * plane_amort + infra_amort
        profit = revenue - running - amort
        capital = airport_capital + planes * plane_price
        denom = max(capital, kdec)
        kdec_score = profit * 1000.0 / denom if denom > 0 else 0.0
        roi_score = profit * 1000.0 / capital if capital > 0 else 0.0
        return {
            "planes": planes, "pax": carried_pax, "mail": carried_mail,
            "pax_a": carried_pax_a, "pax_b": carried_pax_b,
            "mail_a": carried_mail_a, "mail_b": carried_mail_b,
            "revenue": revenue, "profit": profit, "capital": capital,
            "score": roi_score, "roi_score": roi_score, "kdec_score": kdec_score,
            "rating": (rp_a + rp_b) * 50.0 / 255.0,
            "rating_pax_a": rp_a, "rating_pax_b": rp_b,
            "rating_mail_a": rm_a, "rating_mail_b": rm_b,
            "headway": headway, "slot_scale_a": scale_a, "slot_scale_b": scale_b,
            "departures": departures, "round_trip": effective_round_trip,
        }

    def evaluate(planes):
        effective_round_trip = round_trip
        row = None
        if source_queue:
            # Validation volontairement restreinte aux deux extremites sans
            # service AIR preexistant : sinon l'artefact C121 ne contient pas
            # le mix moteur necessaire pour reconstruire la charge de piste.
            if (runway_profile is None
                    or float(build["existing_pickup_a"]) > 1.0e-12
                    or float(build["existing_pickup_b"]) > 1.0e-12):
                return None

            takeoff = float(runway_profile["takeoff_days"])
            landing = float(runway_profile["landing_days"])
            service = takeoff + landing
            if service <= 0.0:
                return None

            # Une visite genere deux operations RunwayInOut, une arrivee et un
            # depart. En supposant leurs instants d'arrivee independants entre
            # lignes, Pollaczek-Khinchine pour une M/G/1 donne l'attente moyenne
            # par operation : r*(St^2+Sl^2)/(2*(1-r*(St+Sl))). Le round-trip
            # subit deux operations a chacun des deux aeroports. Aucun
            # coefficient n'est appris sur le banc.
            def residual(candidate_round_trip):
                visit_rate = float(planes) / candidate_round_trip
                rho = visit_rate * service
                if rho >= 1.0:
                    return -1.0e100
                queue_event = (
                    visit_rate * (takeoff * takeoff + landing * landing)
                    / (2.0 * (1.0 - rho))
                )
                predicted = round_trip + 4.0 * queue_event
                return candidate_round_trip - predicted

            lo = max(round_trip, float(planes) * service * (1.0 + 1.0e-9))
            hi = max(lo * 2.0, round_trip * 2.0)
            for _ in range(64):
                if residual(hi) > 0.0:
                    break
                hi *= 2.0
            for _ in range(80):
                mid = (lo + hi) / 2.0
                if residual(mid) > 0.0:
                    hi = mid
                else:
                    lo = mid
            effective_round_trip = (lo + hi) / 2.0
            row = evaluate_once(planes, effective_round_trip)
            visit_rate = float(planes) / effective_round_trip
            row["queue_wait_roundtrip_days"] = effective_round_trip - round_trip
            row["runway_rho"] = visit_rate * service
            row["runway_service_days"] = service
            row["runway_hold_retry_days"] = float(runway_profile["hold_retry_days"])
            row["loading_dwell_days"] = 0.0
            return row
        if source_loading:
            # Fixed point: dwell changes cadence; cadence changes cargo per visit.
            # Start from zero dwell and iterate the source-defined discrete loading
            # rounds. This is diagnostic only and never reads the 5x6 outcomes.
            seen = set()
            for _ in range(32):
                row = evaluate_once(planes, effective_round_trip)
                dwell = _source_air_loading_dwell_days(
                    row["pax_a"], row["pax_b"], row["mail_a"], row["mail_b"],
                    row["departures"],
                )
                next_round_trip = round_trip + 2.0 * dwell
                state = round(next_round_trip, 9)
                if abs(next_round_trip - effective_round_trip) < 1.0e-9:
                    effective_round_trip = next_round_trip
                    break
                if state in seen:
                    # A threshold can alternate by one loading slice. The slower
                    # state is the safe physical bound, not a fitted average.
                    effective_round_trip = max(effective_round_trip, next_round_trip)
                    break
                seen.add(state)
                effective_round_trip = next_round_trip
            row = evaluate_once(planes, effective_round_trip)
            row["loading_dwell_days"] = (effective_round_trip - round_trip) / 2.0
            return row
        row = evaluate_once(planes, effective_round_trip)
        row["loading_dwell_days"] = 0.0
        return row

    if isinstance(fixed_planes, (int, float)) and int(fixed_planes) > 0:
        choices = [evaluate(int(fixed_planes))]
    else:
        choices = [evaluate(planes) for planes in range(1, fleet_cap + 1)]
    choices = [row for row in choices if row is not None]
    if not choices:
        return None
    target = max(choices, key=lambda row: (row["profit"], row["roi_score"]))
    decision = max(choices, key=lambda row: (row["roi_score"], row["profit"]))
    kdec_decision = max(choices, key=lambda row: (row["kdec_score"], row["profit"]))
    roi = max(choices, key=lambda row: (row["roi_score"], row["profit"]))
    return {
        "target": target, "decision": decision, "roi": roi,
        "kdec_decision": kdec_decision, "kdec": kdec,
    }


def analyse(payload, min_age=6, max_age=None):
    builds = {}
    all_events = defaultdict(list)
    mature_events = defaultdict(list)
    timing_by_route = defaultdict(list)
    final_station_lines = defaultdict(set)
    hub_delay_updates = []
    for row in payload.get("rows", []):
        seed = row.get("seed")
        for build in row.get("c121_builds", []):
            line = build.get("line")
            if isinstance(seed, int) and isinstance(line, (int, float)):
                line_id = int(line)
                builds[(seed, line_id)] = build
                for station_key in ("station_id_a", "station_id_b"):
                    station_id = build.get(station_key)
                    if isinstance(station_id, (int, float)) and station_id >= 0:
                        final_station_lines[(seed, int(station_id))].add(line_id)
        for event in row.get("events", []):
            line = event.get("line")
            age = event.get("age_bucket")
            if not (isinstance(seed, int) and isinstance(line, (int, float))):
                continue
            item = dict(event)
            item["seed"] = seed
            event_key = (seed, int(line))
            all_events[event_key].append(item)
            if not (isinstance(age, (int, float)) and age >= min_age
                    and (max_age is None or age <= max_age)):
                continue
            mature_events[event_key].append(item)
        for timing in row.get("timing_measurements", []):
            src = timing.get("src_station")
            dst = timing.get("dst_station")
            engine = timing.get("engine")
            if not (isinstance(seed, int) and isinstance(src, (int, float))
                    and isinstance(dst, (int, float)) and isinstance(engine, (int, float))):
                continue
            a, b = sorted((int(src), int(dst)))
            timing_by_route[(seed, a, b, int(engine))].append(timing)
        for update in row.get("hub_delay_updates", []):
            if not isinstance(update, dict):
                continue
            item = dict(update)
            item["seed"] = seed
            hub_delay_updates.append(item)

    # Reconstituer hors-jeu le service final des hubs avec la derniere fenetre
    # C117 de chaque ligne. En distribution manuelle, le cargo d'une gare est
    # commun aux services qui la visitent : capacity/headway donne donc une
    # mesure mecanique de la capacite de prise en charge concurrente.
    final_line_service = {}
    final_station_pickup_rate = defaultdict(float)
    final_station_pax_rate = defaultdict(float)
    final_station_mail_rate = defaultdict(float)
    for event_key, events in all_events.items():
        build = builds.get(event_key)
        if build is None or not events:
            continue
        latest = max(
            events,
            key=lambda event: (
                event.get("age_bucket", -1) if isinstance(event.get("age_bucket"), (int, float)) else -1,
                event.get("age_days", -1) if isinstance(event.get("age_days"), (int, float)) else -1,
            ),
        )
        headway = latest.get("headway_days")
        pax_cap = build.get("pax_cap")
        mail_cap = build.get("mail_cap")
        if not (isinstance(headway, (int, float)) and headway > 0
                and isinstance(pax_cap, (int, float)) and pax_cap > 0
                and isinstance(mail_cap, (int, float)) and mail_cap >= 0):
            continue
        pickup_rate = 1.0 / float(headway)
        pax_rate = float(pax_cap) * pickup_rate
        mail_rate = float(mail_cap) * pickup_rate
        final_line_service[event_key] = {
            "pickup_rate": pickup_rate, "pax_rate": pax_rate, "mail_rate": mail_rate,
        }
        for station_key in ("station_id_a", "station_id_b"):
            station_id = build.get(station_key)
            if isinstance(station_id, (int, float)) and station_id >= 0:
                station_ref = (event_key[0], int(station_id))
                final_station_pickup_rate[station_ref] += pickup_rate
                final_station_pax_rate[station_ref] += pax_rate
                final_station_mail_rate[station_ref] += mail_rate

    rows = []
    for key, events in sorted(mature_events.items()):
        build = builds.get(key)
        if build is None:
            continue
        build = dict(build)
        replay = replay_fleet(build)
        roi_decision = replay["roi"] if replay is not None else None
        kdec_decision = replay["kdec_decision"] if replay is not None else None
        legacy_c16_replay = None
        legacy_c16_cap = None
        if all(isinstance(build.get(key), (int, float)) for key in (
            "one_way_days", "route_div_a", "route_div_b"
        )):
            # Diagnostic uniquement. Le 5x6 C121 utilise AT_LARGE aux deux bouts.
            # C16/AAAHogEx donne 10 jours par slot AT_LARGE et partage ce slot
            # entre les routes du hub. Cette valeur n'est PAS injectee dans C121.
            c16_span = 10.0 * max(float(build["route_div_a"]), float(build["route_div_b"]))
            if c16_span > 0:
                legacy_c16_cap = max(
                    1, int((2.0 * float(build["one_way_days"])) / c16_span) + 1
                )
                legacy_c16_replay = replay_fleet(
                    build, fleet_cap_override=legacy_c16_cap
                )
        if replay is not None:
            if not isinstance(build.get("target_n"), (int, float)) or build.get("target_n", -1) < 1:
                target = replay["target"]
                build.update({
                    "target_n": target["planes"],
                    "target_pax": target["pax"],
                    "target_mail": target["mail"],
                    "target_revenue": target["revenue"],
                    "target_profit": target["profit"],
                })
            if not isinstance(build.get("decision_n"), (int, float)) or build.get("decision_n", -1) < 1:
                decision = replay["decision"]
                build.update({
                    "decision_kdec": replay["kdec"],
                    "decision_n": decision["planes"],
                    "decision_score": decision["score"],
                    "decision_pax": decision["pax"],
                    "decision_mail": decision["mail"],
                    "decision_revenue": decision["revenue"],
                    "decision_profit": decision["profit"],
                    "decision_capital": decision["capital"],
                    "decision_rating": decision["rating"],
                    "decision_headway": decision["headway"],
                })
        observed = aggregate(events)
        adapted_pairs = [
            (float(event["c121_adapted_oneway_days"]), float(event.get("leg_days_n", 0)))
            for event in events
            if isinstance(event.get("c121_adapted_oneway_days"), (int, float))
            and event["c121_adapted_oneway_days"] > 0
            and isinstance(event.get("leg_days_n"), (int, float))
            and event["leg_days_n"] > 0
        ]
        adapted_weight = sum(weight for _, weight in adapted_pairs)
        live_adapted_oneway_days = (
            sum(value * weight for value, weight in adapted_pairs) / adapted_weight
            if adapted_weight > 0 else None
        )
        station_a = build.get("station_id_a")
        station_b = build.get("station_id_b")
        final_degree_a = (
            len(final_station_lines.get((key[0], int(station_a)), ()))
            if isinstance(station_a, (int, float)) and station_a >= 0 else None
        )
        final_degree_b = (
            len(final_station_lines.get((key[0], int(station_b)), ()))
            if isinstance(station_b, (int, float)) and station_b >= 0 else None
        )
        build_degree_a = build.get("route_div_a")
        build_degree_b = build.get("route_div_b")
        growth_a = (
            max(0, final_degree_a - int(build_degree_a))
            if isinstance(final_degree_a, int) and isinstance(build_degree_a, (int, float))
            else None
        )
        growth_b = (
            max(0, final_degree_b - int(build_degree_b))
            if isinstance(final_degree_b, int) and isinstance(build_degree_b, (int, float))
            else None
        )
        endpoint_growth = max(
            growth_a if isinstance(growth_a, int) else 0,
            growth_b if isinstance(growth_b, int) else 0,
        )
        growth_bucket = "0" if endpoint_growth == 0 else ("1" if endpoint_growth == 1 else "2+")
        timing_rows = []
        station_a = build.get("station_id_a")
        station_b = build.get("station_id_b")
        engine = build.get("engine")
        if (isinstance(station_a, (int, float)) and isinstance(station_b, (int, float))
                and isinstance(engine, (int, float))):
            ta, tb = sorted((int(station_a), int(station_b)))
            timing_rows = timing_by_route.get((key[0], ta, tb, int(engine)), [])
        timetable_travel_days = None
        timetable_wait_days = None
        timetable_cycle_days = None
        if timing_rows:
            travels = [float(t["observed_days"]) for t in timing_rows
                       if isinstance(t.get("observed_days"), (int, float))]
            waits = [float(t.get("wait_ticks", 0.0)) / 74.0 for t in timing_rows]
            cycles = [float(t["observed_days"]) + float(t.get("wait_ticks", 0.0)) / 74.0
                      for t in timing_rows if isinstance(t.get("observed_days"), (int, float))]
            if travels:
                timetable_travel_days = statistics.median(travels)
            if waits:
                timetable_wait_days = statistics.median(waits)
            if cycles:
                timetable_cycle_days = statistics.median(cycles)
        timetable_replay = (
            replay_fleet(build, timetable_cycle_days)
            if timetable_cycle_days is not None else None
        )
        timetable_decision = timetable_replay["decision"] if timetable_replay is not None else None
        timetable_fixed_replay = (
            replay_fleet(
                build,
                timetable_cycle_days,
                fixed_planes=build.get("actual_n"),
            )
            if timetable_cycle_days is not None else None
        )
        timetable_fixed = (
            timetable_fixed_replay["decision"] if timetable_fixed_replay is not None else None
        )
        source_loading_replay = replay_fleet(build, source_loading=True)
        source_loading_decision = (
            source_loading_replay["decision"] if source_loading_replay is not None else None
        )
        source_loading_fixed_replay = replay_fleet(
            build, fixed_planes=build.get("actual_n"), source_loading=True
        )
        source_loading_fixed = (
            source_loading_fixed_replay["decision"]
            if source_loading_fixed_replay is not None else None
        )
        source_rating_fixed_replay = replay_fleet(
            build, fixed_planes=build.get("actual_n"), source_rating=True
        )
        source_rating_fixed = (
            source_rating_fixed_replay["decision"]
            if source_rating_fixed_replay is not None else None
        )
        average_pickup_fixed_replay = replay_fleet(
            build, fixed_planes=build.get("actual_n"), average_pickup_rating=True
        )
        average_pickup_fixed = (
            average_pickup_fixed_replay["decision"]
            if average_pickup_fixed_replay is not None else None
        )
        source_rating_timetable_fixed_replay = (
            replay_fleet(
                build,
                timetable_cycle_days,
                fixed_planes=build.get("actual_n"),
                source_rating=True,
            )
            if timetable_cycle_days is not None else None
        )
        source_rating_timetable_fixed = (
            source_rating_timetable_fixed_replay["decision"]
            if source_rating_timetable_fixed_replay is not None else None
        )
        source_slot_days = None
        if timing_rows:
            airport_pairs = {
                (t.get("src_airport_type"), t.get("dst_airport_type"))
                for t in timing_rows
            }
            # OpenTTD 15.3 AT_LARGE: une seule ressource RunwayInOut est
            # partagee par arrivees/departs. Le temps de service ci-dessous est
            # derive directement de la FTA/movement data et de la vitesse taxi,
            # jamais de maneuverDays C100 ni des resultats du banc.
            if airport_pairs == {(1, 1)}:
                source_slot_days = _source_city_runway_service_days()
        source_slot_replay = (
            replay_fleet(build, airport_slot_days=source_slot_days)
            if source_slot_days is not None else None
        )
        source_slot_decision = (
            source_slot_replay["decision"] if source_slot_replay is not None else None
        )
        source_slot_fixed_replay = (
            replay_fleet(
                build,
                airport_slot_days=source_slot_days,
                fixed_planes=build.get("actual_n"),
            )
            if source_slot_days is not None else None
        )
        source_slot_fixed = (
            source_slot_fixed_replay["decision"]
            if source_slot_fixed_replay is not None else None
        )
        source_queue_replay = (
            replay_fleet(build, source_queue=True)
            if source_slot_days is not None else None
        )
        source_queue_decision = (
            source_queue_replay["decision"] if source_queue_replay is not None else None
        )
        source_queue_fixed_replay = (
            replay_fleet(
                build,
                fixed_planes=build.get("actual_n"),
                source_queue=True,
            )
            if source_slot_days is not None else None
        )
        source_queue_fixed = (
            source_queue_fixed_replay["decision"]
            if source_queue_fixed_replay is not None else None
        )
        average_pickup_slot_fixed_replay = (
            replay_fleet(
                build,
                airport_slot_days=source_slot_days,
                fixed_planes=build.get("actual_n"),
                average_pickup_rating=True,
            )
            if source_slot_days is not None else None
        )
        average_pickup_slot_fixed = (
            average_pickup_slot_fixed_replay["decision"]
            if average_pickup_slot_fixed_replay is not None else None
        )
        source_rating_slot_fixed_replay = (
            replay_fleet(
                build,
                airport_slot_days=source_slot_days,
                fixed_planes=build.get("actual_n"),
                source_rating=True,
            )
            if source_slot_days is not None else None
        )
        source_rating_slot_fixed = (
            source_rating_slot_fixed_replay["decision"]
            if source_rating_slot_fixed_replay is not None else None
        )
        manual_fifo_replay = (
            replay_fleet(
                build,
                airport_slot_days=source_slot_days,
                average_pickup_rating=True,
                manual_fifo_share=True,
            )
            if source_slot_days is not None else None
        )
        manual_fifo_decision = (
            manual_fifo_replay["decision"] if manual_fifo_replay is not None else None
        )
        manual_fifo_fixed_replay = (
            replay_fleet(
                build,
                airport_slot_days=source_slot_days,
                fixed_planes=build.get("actual_n"),
                average_pickup_rating=True,
                manual_fifo_share=True,
            )
            if source_slot_days is not None else None
        )
        manual_fifo_fixed = (
            manual_fifo_fixed_replay["decision"]
            if manual_fifo_fixed_replay is not None else None
        )
        mature_competition_fixed = None
        mature_competition_no_slot_fixed = None
        mature_competition_fifo_fixed = None
        mature_current_service_fixed = None
        mature_current_service_fifo_fixed = None
        own_final_service = final_line_service.get(key)
        if (own_final_service is not None
                and isinstance(station_a, (int, float)) and station_a >= 0
                and isinstance(station_b, (int, float)) and station_b >= 0):
            mature_build = dict(build)
            ref_a = (key[0], int(station_a))
            ref_b = (key[0], int(station_b))
            mature_build["existing_pickup_a"] = max(
                0.0, final_station_pickup_rate[ref_a] - own_final_service["pickup_rate"])
            mature_build["existing_pickup_b"] = max(
                0.0, final_station_pickup_rate[ref_b] - own_final_service["pickup_rate"])
            mature_build["existing_pax_rate_a"] = max(
                0.0, final_station_pax_rate[ref_a] - own_final_service["pax_rate"])
            mature_build["existing_pax_rate_b"] = max(
                0.0, final_station_pax_rate[ref_b] - own_final_service["pax_rate"])
            mature_build["existing_mail_rate_a"] = max(
                0.0, final_station_mail_rate[ref_a] - own_final_service["mail_rate"])
            mature_build["existing_mail_rate_b"] = max(
                0.0, final_station_mail_rate[ref_b] - own_final_service["mail_rate"])
            mature_competition_no_slot_replay = replay_fleet(
                mature_build,
                fixed_planes=build.get("actual_n"),
                average_pickup_rating=True,
            )
            if mature_competition_no_slot_replay is not None:
                mature_competition_no_slot_fixed = mature_competition_no_slot_replay["decision"]
            mature_current_service_replay = replay_fleet(
                mature_build,
                fixed_planes=build.get("actual_n"),
                average_pickup_rating=True,
                candidate_pickup_override=own_final_service["pickup_rate"],
            )
            if mature_current_service_replay is not None:
                mature_current_service_fixed = mature_current_service_replay["decision"]
            mature_current_service_fifo_replay = replay_fleet(
                mature_build,
                fixed_planes=build.get("actual_n"),
                average_pickup_rating=True,
                manual_fifo_share=True,
                candidate_pickup_override=own_final_service["pickup_rate"],
            )
            if mature_current_service_fifo_replay is not None:
                mature_current_service_fifo_fixed = mature_current_service_fifo_replay["decision"]
            if source_slot_days is not None:
                mature_competition_replay = replay_fleet(
                    mature_build,
                    airport_slot_days=source_slot_days,
                    fixed_planes=build.get("actual_n"),
                    average_pickup_rating=True,
                )
                if mature_competition_replay is not None:
                    mature_competition_fixed = mature_competition_replay["decision"]
                mature_competition_fifo_replay = replay_fleet(
                    mature_build,
                    airport_slot_days=source_slot_days,
                    fixed_planes=build.get("actual_n"),
                    average_pickup_rating=True,
                    manual_fifo_share=True,
                )
                if mature_competition_fifo_replay is not None:
                    mature_competition_fifo_fixed = mature_competition_fifo_replay["decision"]
        source_slot_roi = source_slot_replay["roi"] if source_slot_replay is not None else None
        legacy_c16_decision = (
            legacy_c16_replay["decision"] if legacy_c16_replay is not None else None
        )
        actual_total_pm = observed.get("pax_pm", 0.0) + observed.get("mail_pm", 0.0)
        pred_total = build.get("actual_pax", 0) + build.get("actual_mail", 0)
        target_total = build.get("target_pax", 0) + build.get("target_mail", 0)
        decision_total = build.get("decision_pax", 0) + build.get("decision_mail", 0)
        pred_yield = None
        if isinstance(build.get("actual_revenue"), (int, float)) and pred_total > 0:
            pred_yield = build["actual_revenue"] / 12.0 / pred_total
        actual_yield = ratio(observed.get("revenue_pm"), actual_total_pm)
        c121_revenue_at_actual_mix_y = None
        if (isinstance(build.get("pax_income"), (int, float))
                and isinstance(build.get("mail_income"), (int, float))):
            c121_revenue_at_actual_mix_y = 12.0 * (
                observed.get("pax_pm", 0.0) * build["pax_income"]
                + observed.get("mail_pm", 0.0) * build["mail_income"]
            )
        capacity_share = None
        required_share_fields = (
            "pax_raw_a", "pax_raw_b", "mail_raw_a", "mail_raw_b",
            "rating_pax_a", "rating_pax_b", "rating_mail_a", "rating_mail_b",
            "pax_dir_capacity", "mail_dir_capacity",
            "existing_pax_rate_a", "existing_pax_rate_b",
            "existing_mail_rate_a", "existing_mail_rate_b",
            "pax_income", "mail_income",
        )
        if all(isinstance(build.get(field), (int, float)) for field in required_share_fields):
            pax_rate = max(0.0, float(build["pax_dir_capacity"])) / 30.4
            mail_rate = max(0.0, float(build["mail_dir_capacity"])) / 30.4

            def service_share(candidate_rate, existing_rate):
                existing_rate = max(0.0, float(existing_rate))
                total = existing_rate + candidate_rate
                return candidate_rate / total if total > 0 else 1.0

            pax_share_a = service_share(pax_rate, build["existing_pax_rate_a"])
            pax_share_b = service_share(pax_rate, build["existing_pax_rate_b"])
            mail_share_a = service_share(mail_rate, build["existing_mail_rate_a"])
            mail_share_b = service_share(mail_rate, build["existing_mail_rate_b"])
            pax_offered_a = float(build["pax_raw_a"]) * float(build["rating_pax_a"]) / 255.0 * pax_share_a
            pax_offered_b = float(build["pax_raw_b"]) * float(build["rating_pax_b"]) / 255.0 * pax_share_b
            mail_offered_a = float(build["mail_raw_a"]) * float(build["rating_mail_a"]) / 255.0 * mail_share_a
            mail_offered_b = float(build["mail_raw_b"]) * float(build["rating_mail_b"]) / 255.0 * mail_share_b
            pax_cf = min(pax_offered_a, float(build["pax_dir_capacity"])) + min(
                pax_offered_b, float(build["pax_dir_capacity"])
            )
            mail_cf = min(mail_offered_a, float(build["mail_dir_capacity"])) + min(
                mail_offered_b, float(build["mail_dir_capacity"])
            )
            revenue_cf = 12.0 * (
                pax_cf * float(build["pax_income"]) + mail_cf * float(build["mail_income"])
            )
            capacity_share = {
                "pax": pax_cf, "mail": mail_cf, "total": pax_cf + mail_cf,
                "revenue": revenue_cf,
                "pax_share_a": pax_share_a, "pax_share_b": pax_share_b,
                "mail_share_a": mail_share_a, "mail_share_b": mail_share_b,
            }
        observed_vehicle_profit_y = (
            observed.get("profit_pm", 0.0) * 12.0
            if isinstance(observed.get("profit_pm"), (int, float)) else None
        )
        actual_model_like_profit_y = None
        if all(isinstance(build.get(key), (int, float)) for key in (
            "actual_running", "actual_vehicle_running", "actual_amort"
        )) and isinstance(observed_vehicle_profit_y, (int, float)):
            actual_model_like_profit_y = (
                observed_vehicle_profit_y
                - (build["actual_running"] - build["actual_vehicle_running"])
                - build["actual_amort"]
            )
        rows.append({
            "seed": key[0],
            "line": key[1],
            "arm": build.get("arm"),
            "engine": build.get("engine"),
            "period_days": observed.get("period_days"),
            "pred_pax_pm": build.get("actual_pax"),
            "actual_pax_pm": observed.get("pax_pm"),
            "actual_over_pred_pax": ratio(observed.get("pax_pm"), build.get("actual_pax")),
            "pred_mail_pm": build.get("actual_mail"),
            "actual_mail_pm": observed.get("mail_pm"),
            "actual_over_pred_mail": ratio(observed.get("mail_pm"), build.get("actual_mail")),
            "pred_total_pm": pred_total,
            "actual_total_pm": actual_total_pm,
            "actual_over_pred_total": ratio(actual_total_pm, pred_total),
            "source_loading_fixed_total_pm": (
                source_loading_fixed["pax"] + source_loading_fixed["mail"]
                if source_loading_fixed else None
            ),
            "actual_over_source_loading_fixed_total": ratio(
                actual_total_pm,
                (
                    source_loading_fixed["pax"] + source_loading_fixed["mail"]
                    if source_loading_fixed else None
                ),
            ),
            "actual_over_source_rating_fixed_total": ratio(
                actual_total_pm,
                (source_rating_fixed["pax"] + source_rating_fixed["mail"])
                if source_rating_fixed else None,
            ),
            "actual_over_average_pickup_fixed_total": ratio(
                actual_total_pm,
                (average_pickup_fixed["pax"] + average_pickup_fixed["mail"])
                if average_pickup_fixed else None,
            ),
            "actual_over_manual_fifo_fixed_total": ratio(
                actual_total_pm,
                (manual_fifo_fixed["pax"] + manual_fifo_fixed["mail"])
                if manual_fifo_fixed else None,
            ),
            "actual_over_mature_competition_fixed_total": ratio(
                actual_total_pm,
                (mature_competition_fixed["pax"] + mature_competition_fixed["mail"])
                if mature_competition_fixed else None,
            ),
            "actual_over_mature_competition_no_slot_fixed_total": ratio(
                actual_total_pm,
                (mature_competition_no_slot_fixed["pax"] + mature_competition_no_slot_fixed["mail"])
                if mature_competition_no_slot_fixed else None,
            ),
            "actual_over_mature_competition_fifo_fixed_total": ratio(
                actual_total_pm,
                (mature_competition_fifo_fixed["pax"] + mature_competition_fifo_fixed["mail"])
                if mature_competition_fifo_fixed else None,
            ),
            "actual_over_mature_current_service_fixed_total": ratio(
                actual_total_pm,
                (mature_current_service_fixed["pax"] + mature_current_service_fixed["mail"])
                if mature_current_service_fixed else None,
            ),
            "actual_over_mature_current_service_fifo_fixed_total": ratio(
                actual_total_pm,
                (mature_current_service_fifo_fixed["pax"] + mature_current_service_fifo_fixed["mail"])
                if mature_current_service_fifo_fixed else None,
            ),
            "actual_over_source_rating_timetable_fixed_total": ratio(
                actual_total_pm,
                (source_rating_timetable_fixed["pax"] + source_rating_timetable_fixed["mail"])
                if source_rating_timetable_fixed else None,
            ),
            "source_slot_fixed_total_pm": (
                source_slot_fixed["pax"] + source_slot_fixed["mail"]
                if source_slot_fixed else None
            ),
            "actual_over_source_slot_fixed_total": ratio(
                actual_total_pm,
                (
                    source_slot_fixed["pax"] + source_slot_fixed["mail"]
                    if source_slot_fixed else None
                ),
            ),
            "actual_over_source_queue_fixed_total": ratio(
                actual_total_pm,
                (
                    source_queue_fixed["pax"] + source_queue_fixed["mail"]
                    if source_queue_fixed else None
                ),
            ),
            "source_queue_fixed_wait_roundtrip_days": (
                source_queue_fixed.get("queue_wait_roundtrip_days")
                if source_queue_fixed else None
            ),
            "source_queue_fixed_runway_rho": (
                source_queue_fixed.get("runway_rho") if source_queue_fixed else None
            ),
            "source_queue_fixed_runway_service_days": (
                source_queue_fixed.get("runway_service_days") if source_queue_fixed else None
            ),
            "actual_over_average_pickup_slot_fixed_total": ratio(
                actual_total_pm,
                (
                    average_pickup_slot_fixed["pax"] + average_pickup_slot_fixed["mail"]
                    if average_pickup_slot_fixed else None
                ),
            ),
            "actual_over_source_rating_slot_fixed_total": ratio(
                actual_total_pm,
                (
                    source_rating_slot_fixed["pax"] + source_rating_slot_fixed["mail"]
                    if source_rating_slot_fixed else None
                ),
            ),
            "timetable_fixed_total_pm": (
                timetable_fixed["pax"] + timetable_fixed["mail"]
                if timetable_fixed else None
            ),
            "actual_over_timetable_fixed_total": ratio(
                actual_total_pm,
                (
                    timetable_fixed["pax"] + timetable_fixed["mail"]
                    if timetable_fixed else None
                ),
            ),
            "target_pax_pm": build.get("target_pax"),
            "actual_over_target_pax": ratio(observed.get("pax_pm"), build.get("target_pax")),
            "target_mail_pm": build.get("target_mail"),
            "actual_over_target_mail": ratio(observed.get("mail_pm"), build.get("target_mail")),
            "target_total_pm": target_total,
            "actual_over_target_total": ratio(actual_total_pm, target_total),
            "decision_pax_pm": build.get("decision_pax"),
            "actual_over_decision_pax": ratio(observed.get("pax_pm"), build.get("decision_pax")),
            "decision_mail_pm": build.get("decision_mail"),
            "actual_over_decision_mail": ratio(observed.get("mail_pm"), build.get("decision_mail")),
            "decision_total_pm": decision_total,
            "actual_over_decision_total": ratio(actual_total_pm, decision_total),
            "source_loading_decision_n": (
                source_loading_decision["planes"] if source_loading_decision else None
            ),
            "actual_over_source_loading_decision_fleet": ratio(
                observed.get("live_avg"),
                source_loading_decision["planes"] if source_loading_decision else None,
            ),
            "actual_over_source_loading_decision_total": ratio(
                actual_total_pm,
                (
                    source_loading_decision["pax"] + source_loading_decision["mail"]
                    if source_loading_decision else None
                ),
            ),
            "actual_over_source_loading_decision_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0,
                source_loading_decision["revenue"] if source_loading_decision else None,
            ),
            "source_loading_decision_dwell_days": (
                source_loading_decision.get("loading_dwell_days")
                if source_loading_decision else None
            ),
            "source_slot_days": source_slot_days,
            "source_slot_decision_n": source_slot_decision["planes"] if source_slot_decision else None,
            "actual_over_source_slot_decision_fleet": ratio(
                observed.get("live_avg"),
                source_slot_decision["planes"] if source_slot_decision else None,
            ),
            "source_slot_decision_total_pm": (
                source_slot_decision["pax"] + source_slot_decision["mail"]
                if source_slot_decision else None
            ),
            "actual_over_source_slot_decision_total": ratio(
                actual_total_pm,
                (
                    source_slot_decision["pax"] + source_slot_decision["mail"]
                    if source_slot_decision else None
                ),
            ),
            "source_slot_decision_revenue_y": (
                source_slot_decision["revenue"] if source_slot_decision else None
            ),
            "actual_over_source_slot_decision_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0,
                source_slot_decision["revenue"] if source_slot_decision else None,
            ),
            "manual_fifo_decision_n": (
                manual_fifo_decision["planes"] if manual_fifo_decision else None
            ),
            "actual_over_manual_fifo_decision_fleet": ratio(
                observed.get("live_avg"),
                manual_fifo_decision["planes"] if manual_fifo_decision else None,
            ),
            "actual_over_manual_fifo_decision_pax": ratio(
                observed.get("pax_pm"),
                manual_fifo_decision["pax"] if manual_fifo_decision else None,
            ),
            "actual_over_manual_fifo_decision_mail": ratio(
                observed.get("mail_pm"),
                manual_fifo_decision["mail"] if manual_fifo_decision else None,
            ),
            "actual_over_manual_fifo_decision_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0,
                manual_fifo_decision["revenue"] if manual_fifo_decision else None,
            ),
            "source_queue_decision_n": (
                source_queue_decision["planes"] if source_queue_decision else None
            ),
            "actual_over_source_queue_decision_fleet": ratio(
                observed.get("live_avg"),
                source_queue_decision["planes"] if source_queue_decision else None,
            ),
            "actual_over_source_queue_decision_total": ratio(
                actual_total_pm,
                (
                    source_queue_decision["pax"] + source_queue_decision["mail"]
                    if source_queue_decision else None
                ),
            ),
            "actual_over_source_queue_decision_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0,
                source_queue_decision["revenue"] if source_queue_decision else None,
            ),
            "source_queue_decision_wait_roundtrip_days": (
                source_queue_decision.get("queue_wait_roundtrip_days")
                if source_queue_decision else None
            ),
            "source_queue_decision_runway_rho": (
                source_queue_decision.get("runway_rho")
                if source_queue_decision else None
            ),
            "source_slot_scale_a": (
                source_slot_decision.get("slot_scale_a") if source_slot_decision else None
            ),
            "source_slot_scale_b": (
                source_slot_decision.get("slot_scale_b") if source_slot_decision else None
            ),
            "source_slot_roi_n": source_slot_roi["planes"] if source_slot_roi else None,
            "actual_over_source_slot_roi_fleet": ratio(
                observed.get("live_avg"), source_slot_roi["planes"] if source_slot_roi else None
            ),
            "actual_over_source_slot_roi_total": ratio(
                actual_total_pm,
                source_slot_roi["pax"] + source_slot_roi["mail"] if source_slot_roi else None,
            ),
            "actual_over_source_slot_roi_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0,
                source_slot_roi["revenue"] if source_slot_roi else None,
            ),
            "legacy_c16_cap": legacy_c16_cap,
            "legacy_c16_decision_total_pm": (
                legacy_c16_decision["pax"] + legacy_c16_decision["mail"]
                if legacy_c16_decision else None
            ),
            "actual_over_legacy_c16_decision_total": ratio(
                actual_total_pm,
                (
                    legacy_c16_decision["pax"] + legacy_c16_decision["mail"]
                    if legacy_c16_decision else None
                ),
            ),
            "timetable_decision_n": timetable_decision["planes"] if timetable_decision else None,
            "actual_over_timetable_decision_fleet": ratio(
                observed.get("live_avg"),
                timetable_decision["planes"] if timetable_decision else None,
            ),
            "timetable_decision_total_pm": (
                timetable_decision["pax"] + timetable_decision["mail"]
                if timetable_decision else None
            ),
            "actual_over_timetable_decision_total": ratio(
                actual_total_pm,
                timetable_decision["pax"] + timetable_decision["mail"]
                if timetable_decision else None,
            ),
            "timetable_decision_revenue_y": timetable_decision["revenue"] if timetable_decision else None,
            "actual_over_timetable_decision_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0,
                timetable_decision["revenue"] if timetable_decision else None,
            ),
            "pred_revenue_y": build.get("actual_revenue"),
            "actual_revenue_y": observed.get("revenue_pm", 0.0) * 12.0,
            "actual_over_pred_revenue": ratio(observed.get("revenue_pm", 0.0) * 12.0, build.get("actual_revenue")),
            "actual_over_source_loading_fixed_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0,
                source_loading_fixed["revenue"] if source_loading_fixed else None,
            ),
            "actual_over_source_rating_fixed_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0,
                source_rating_fixed["revenue"] if source_rating_fixed else None,
            ),
            "actual_over_manual_fifo_fixed_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0,
                manual_fifo_fixed["revenue"] if manual_fifo_fixed else None,
            ),
            "actual_over_mature_competition_fixed_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0,
                mature_competition_fixed["revenue"] if mature_competition_fixed else None,
            ),
            "actual_over_mature_competition_no_slot_fixed_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0,
                mature_competition_no_slot_fixed["revenue"] if mature_competition_no_slot_fixed else None,
            ),
            "actual_over_mature_competition_fifo_fixed_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0,
                mature_competition_fifo_fixed["revenue"] if mature_competition_fifo_fixed else None,
            ),
            "actual_over_mature_current_service_fixed_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0,
                mature_current_service_fixed["revenue"] if mature_current_service_fixed else None,
            ),
            "actual_over_mature_current_service_fifo_fixed_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0,
                mature_current_service_fifo_fixed["revenue"] if mature_current_service_fifo_fixed else None,
            ),
            "actual_over_manual_fifo_fixed_rating": ratio(
                observed.get("rating_mean"),
                manual_fifo_fixed["rating"] if manual_fifo_fixed else None,
            ),
            "actual_over_mature_competition_fixed_rating": ratio(
                observed.get("rating_mean"),
                mature_competition_fixed["rating"] if mature_competition_fixed else None,
            ),
            "actual_over_mature_competition_no_slot_fixed_rating": ratio(
                observed.get("rating_mean"),
                mature_competition_no_slot_fixed["rating"] if mature_competition_no_slot_fixed else None,
            ),
            "actual_over_mature_competition_fifo_fixed_rating": ratio(
                observed.get("rating_mean"),
                mature_competition_fifo_fixed["rating"] if mature_competition_fifo_fixed else None,
            ),
            "actual_over_mature_current_service_fixed_rating": ratio(
                observed.get("rating_mean"),
                mature_current_service_fixed["rating"] if mature_current_service_fixed else None,
            ),
            "actual_over_mature_current_service_fifo_fixed_rating": ratio(
                observed.get("rating_mean"),
                mature_current_service_fifo_fixed["rating"] if mature_current_service_fifo_fixed else None,
            ),
            "actual_over_average_pickup_fixed_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0,
                average_pickup_fixed["revenue"] if average_pickup_fixed else None,
            ),
            "actual_over_manual_fifo_fixed_pax": ratio(
                observed.get("pax_pm"),
                manual_fifo_fixed["pax"] if manual_fifo_fixed else None,
            ),
            "actual_over_manual_fifo_fixed_mail": ratio(
                observed.get("mail_pm"),
                manual_fifo_fixed["mail"] if manual_fifo_fixed else None,
            ),
            "actual_over_manual_fifo_fixed_total": ratio(
                actual_total_pm,
                (manual_fifo_fixed["pax"] + manual_fifo_fixed["mail"])
                if manual_fifo_fixed else None,
            ),
            "actual_over_manual_fifo_fixed_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0,
                manual_fifo_fixed["revenue"] if manual_fifo_fixed else None,
            ),
            "actual_over_mature_competition_fixed_pax": ratio(
                observed.get("pax_pm"),
                mature_competition_fixed["pax"] if mature_competition_fixed else None,
            ),
            "actual_over_mature_competition_fixed_mail": ratio(
                observed.get("mail_pm"),
                mature_competition_fixed["mail"] if mature_competition_fixed else None,
            ),
            "actual_over_mature_competition_fixed_total": ratio(
                actual_total_pm,
                (mature_competition_fixed["pax"] + mature_competition_fixed["mail"])
                if mature_competition_fixed else None,
            ),
            "actual_over_mature_competition_fixed_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0,
                mature_competition_fixed["revenue"] if mature_competition_fixed else None,
            ),
            "actual_over_source_rating_timetable_fixed_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0,
                source_rating_timetable_fixed["revenue"] if source_rating_timetable_fixed else None,
            ),
            "actual_over_source_rating_fixed_rating": ratio(
                observed.get("rating_mean"),
                source_rating_fixed["rating"] if source_rating_fixed else None,
            ),
            "actual_over_average_pickup_fixed_rating": ratio(
                observed.get("rating_mean"),
                average_pickup_fixed["rating"] if average_pickup_fixed else None,
            ),
            "source_loading_fixed_dwell_days": (
                source_loading_fixed.get("loading_dwell_days") if source_loading_fixed else None
            ),
            "actual_over_source_slot_fixed_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0,
                source_slot_fixed["revenue"] if source_slot_fixed else None,
            ),
            "actual_over_source_queue_fixed_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0,
                source_queue_fixed["revenue"] if source_queue_fixed else None,
            ),
            "actual_over_average_pickup_slot_fixed_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0,
                average_pickup_slot_fixed["revenue"] if average_pickup_slot_fixed else None,
            ),
            "actual_over_source_rating_slot_fixed_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0,
                source_rating_slot_fixed["revenue"] if source_rating_slot_fixed else None,
            ),
            "actual_over_average_pickup_slot_fixed_rating": ratio(
                observed.get("rating_mean"),
                average_pickup_slot_fixed["rating"] if average_pickup_slot_fixed else None,
            ),
            "actual_over_source_rating_slot_fixed_rating": ratio(
                observed.get("rating_mean"),
                source_rating_slot_fixed["rating"] if source_rating_slot_fixed else None,
            ),
            "actual_over_timetable_fixed_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0,
                timetable_fixed["revenue"] if timetable_fixed else None,
            ),
            "c121_revenue_at_actual_mix_y": c121_revenue_at_actual_mix_y,
            "actual_over_c121_payment_yield": ratio(
                observed.get("revenue_pm", 0.0) * 12.0, c121_revenue_at_actual_mix_y
            ),
            "capacity_share_pax_pm": capacity_share["pax"] if capacity_share else None,
            "capacity_share_mail_pm": capacity_share["mail"] if capacity_share else None,
            "capacity_share_total_pm": capacity_share["total"] if capacity_share else None,
            "actual_over_capacity_share_pax": ratio(
                observed.get("pax_pm"), capacity_share["pax"] if capacity_share else None
            ),
            "actual_over_capacity_share_mail": ratio(
                observed.get("mail_pm"), capacity_share["mail"] if capacity_share else None
            ),
            "actual_over_capacity_share_total": ratio(
                actual_total_pm, capacity_share["total"] if capacity_share else None
            ),
            "actual_over_capacity_share_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0,
                capacity_share["revenue"] if capacity_share else None,
            ),
            "capacity_share_pax_a": capacity_share["pax_share_a"] if capacity_share else None,
            "capacity_share_pax_b": capacity_share["pax_share_b"] if capacity_share else None,
            "capacity_share_mail_a": capacity_share["mail_share_a"] if capacity_share else None,
            "capacity_share_mail_b": capacity_share["mail_share_b"] if capacity_share else None,
            "target_revenue_y": build.get("target_revenue"),
            "actual_over_target_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0, build.get("target_revenue")
            ),
            "decision_revenue_y": build.get("decision_revenue"),
            "actual_over_decision_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0, build.get("decision_revenue")
            ),
            "kdec_decision_fleet": kdec_decision["planes"] if kdec_decision else None,
            "actual_over_kdec_decision_fleet": ratio(
                observed.get("live_avg"), kdec_decision["planes"] if kdec_decision else None
            ),
            "actual_over_kdec_decision_total": ratio(
                actual_total_pm,
                kdec_decision["pax"] + kdec_decision["mail"] if kdec_decision else None,
            ),
            "actual_over_kdec_decision_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0,
                kdec_decision["revenue"] if kdec_decision else None,
            ),
            "kdec_decision_capital_over_kdec": ratio(
                kdec_decision["capital"] if kdec_decision else None,
                replay["kdec"] if replay is not None else None,
            ),
            "roi_fleet": roi_decision["planes"] if roi_decision else None,
            "actual_over_roi_fleet": ratio(
                observed.get("live_avg"), roi_decision["planes"] if roi_decision else None
            ),
            "actual_over_roi_total": ratio(
                actual_total_pm,
                roi_decision["pax"] + roi_decision["mail"] if roi_decision else None,
            ),
            "actual_over_roi_revenue": ratio(
                observed.get("revenue_pm", 0.0) * 12.0,
                roi_decision["revenue"] if roi_decision else None,
            ),
            "pred_profit_y": build.get("actual_profit"),
            "actual_model_like_profit_y": actual_model_like_profit_y,
            "actual_over_pred_profit": ratio(actual_model_like_profit_y, build.get("actual_profit")),
            "built_fleet": build.get("actual_n"),
            "pred_fleet": build.get("target_n"),
            "actual_fleet": observed.get("live_avg"),
            "limit_class": observed.get("limit_class"),
            "actual_over_built_fleet": ratio(observed.get("live_avg"), build.get("actual_n")),
            "actual_over_pred_fleet": ratio(observed.get("live_avg"), build.get("target_n")),
            "decision_fleet": build.get("decision_n"),
            "actual_over_decision_fleet": ratio(observed.get("live_avg"), build.get("decision_n")),
            "legacy_c16_decision_fleet": (
                legacy_c16_decision["planes"] if legacy_c16_decision else None
            ),
            "actual_over_legacy_c16_decision_fleet": ratio(
                observed.get("live_avg"),
                legacy_c16_decision["planes"] if legacy_c16_decision else None,
            ),
            "decision_kdec": build.get("decision_kdec"),
            "decision_score": build.get("decision_score"),
            "decision_capital": build.get("decision_capital"),
            "decision_capital_over_kdec": ratio(
                build.get("decision_capital"), replay["kdec"] if replay is not None else None
            ),
            "pred_oneway_days": build.get("one_way_days"),
            "actual_leg_days": observed.get("actual_leg_days"),
            "actual_over_pred_leg_days": ratio(observed.get("actual_leg_days"), build.get("one_way_days")),
            "live_adapted_oneway_days": live_adapted_oneway_days,
            "actual_over_live_adapted_leg_days": ratio(
                observed.get("actual_leg_days"), live_adapted_oneway_days
            ),
            "timetable_samples": len(timing_rows),
            "timetable_travel_days": timetable_travel_days,
            "timetable_wait_days": timetable_wait_days,
            "timetable_cycle_days": timetable_cycle_days,
            "timetable_travel_over_pred_oneway": ratio(
                timetable_travel_days, build.get("one_way_days")
            ),
            "timetable_cycle_over_pred_oneway": ratio(timetable_cycle_days, build.get("one_way_days")),
            "timetable_travel_delay_days": (
                timetable_travel_days - build.get("flight_days")
                if isinstance(timetable_travel_days, (int, float))
                and isinstance(build.get("flight_days"), (int, float))
                else None
            ),
            "timetable_delay_over_pred_maneuver": ratio(
                (
                    timetable_travel_days - build.get("flight_days")
                    if isinstance(timetable_travel_days, (int, float))
                    and isinstance(build.get("flight_days"), (int, float))
                    else None
                ),
                build.get("maneuver_days"),
            ),
            "c117_leg_over_timetable_cycle": ratio(observed.get("actual_leg_days"), timetable_cycle_days),
            "pred_headway_days": build.get("headway_days"),
            "actual_headway_days": observed.get("headway_days"),
            "actual_over_pred_headway": ratio(observed.get("headway_days"), build.get("headway_days")),
            "pred_rating_pct": build.get("rating"),
            "actual_rating_pct": observed.get("rating_mean"),
            "actual_over_pred_rating": ratio(observed.get("rating_mean"), build.get("rating")),
            "pax_capacity": build.get("pax_cap"),
            "mail_capacity": build.get("mail_cap"),
            "pred_pax_dir_capacity": build.get("pax_dir_capacity"),
            "pred_mail_dir_capacity": build.get("mail_dir_capacity"),
            "pax_income": build.get("pax_income"),
            "mail_income": build.get("mail_income"),
            "pred_mixed_yield": pred_yield,
            "actual_mixed_yield": actual_yield,
            "actual_over_pred_mixed_yield": ratio(actual_yield, pred_yield),
            "flight_days": build.get("flight_days"),
            "maneuver_days": build.get("maneuver_days"),
            "fleet_scan_cap": build.get("fleet_scan_cap"),
            "route_div_a": build.get("route_div_a"),
            "route_div_b": build.get("route_div_b"),
            "final_degree_a": final_degree_a,
            "final_degree_b": final_degree_b,
            "route_growth_a": growth_a,
            "route_growth_b": growth_b,
            "route_growth_max": endpoint_growth,
            "route_growth_bucket": growth_bucket,
            "demand_ops": build.get("demand_ops"),
            "demand_ticks": build.get("demand_ticks"),
            "eval_ops": build.get("eval_ops"),
            "eval_ticks": build.get("eval_ticks"),
        })

    metrics = [
        "actual_over_pred_pax", "actual_over_pred_mail", "actual_over_pred_total",
        "actual_over_source_loading_fixed_total",
        "actual_over_source_rating_fixed_total",
        "actual_over_average_pickup_fixed_total",
        "actual_over_manual_fifo_fixed_total",
        "actual_over_mature_competition_fixed_total",
        "actual_over_mature_competition_no_slot_fixed_total",
        "actual_over_mature_competition_fifo_fixed_total",
        "actual_over_mature_current_service_fixed_total",
        "actual_over_mature_current_service_fifo_fixed_total",
        "actual_over_source_rating_timetable_fixed_total",
        "actual_over_source_slot_fixed_total",
        "actual_over_source_queue_fixed_total",
        "actual_over_average_pickup_slot_fixed_total",
        "actual_over_source_rating_slot_fixed_total",
        "actual_over_timetable_fixed_total",
        "actual_over_target_pax", "actual_over_target_mail", "actual_over_target_total",
        "actual_over_decision_pax", "actual_over_decision_mail", "actual_over_decision_total",
        "actual_over_source_loading_decision_total", "actual_over_source_loading_decision_revenue",
        "actual_over_source_slot_decision_total", "actual_over_source_slot_decision_revenue",
        "actual_over_source_queue_decision_total", "actual_over_source_queue_decision_revenue",
        "actual_over_source_slot_roi_total", "actual_over_source_slot_roi_revenue",
        "actual_over_legacy_c16_decision_total",
        "actual_over_timetable_decision_total", "actual_over_timetable_decision_revenue",
        "actual_over_pred_revenue", "actual_over_source_loading_fixed_revenue",
        "actual_over_source_rating_fixed_revenue",
        "actual_over_manual_fifo_fixed_revenue",
        "actual_over_mature_competition_fixed_revenue",
        "actual_over_mature_competition_no_slot_fixed_revenue",
        "actual_over_mature_competition_fifo_fixed_revenue",
        "actual_over_mature_current_service_fixed_revenue",
        "actual_over_mature_current_service_fifo_fixed_revenue",
        "actual_over_manual_fifo_fixed_rating",
        "actual_over_mature_competition_fixed_rating",
        "actual_over_mature_competition_no_slot_fixed_rating",
        "actual_over_mature_competition_fifo_fixed_rating",
        "actual_over_mature_current_service_fixed_rating",
        "actual_over_mature_current_service_fifo_fixed_rating",
        "actual_over_average_pickup_fixed_revenue",
        "actual_over_source_rating_timetable_fixed_revenue",
        "actual_over_source_rating_fixed_rating",
        "actual_over_average_pickup_fixed_rating",
        "actual_over_source_slot_fixed_revenue",
        "actual_over_source_queue_fixed_revenue",
        "actual_over_average_pickup_slot_fixed_revenue",
        "actual_over_source_rating_slot_fixed_revenue",
        "actual_over_average_pickup_slot_fixed_rating",
        "actual_over_source_rating_slot_fixed_rating",
        "actual_over_timetable_fixed_revenue",
        "actual_over_target_revenue", "actual_over_decision_revenue",
        "actual_over_roi_fleet", "actual_over_roi_total", "actual_over_roi_revenue",
        "actual_over_kdec_decision_fleet", "actual_over_kdec_decision_total",
        "actual_over_kdec_decision_revenue", "kdec_decision_capital_over_kdec",
        "decision_capital_over_kdec",
        "actual_over_c121_payment_yield",
        "actual_over_capacity_share_pax", "actual_over_capacity_share_mail",
        "actual_over_capacity_share_total", "actual_over_capacity_share_revenue",
        "actual_over_pred_profit", "actual_over_built_fleet", "actual_over_pred_fleet",
        "actual_over_decision_fleet", "actual_over_legacy_c16_decision_fleet",
        "actual_over_source_loading_decision_fleet",
        "actual_over_source_slot_decision_fleet",
        "actual_over_source_queue_decision_fleet",
        "actual_over_source_slot_roi_fleet",
        "actual_over_timetable_decision_fleet",
        "actual_over_pred_leg_days", "actual_over_live_adapted_leg_days",
        "actual_over_pred_headway", "actual_over_pred_rating",
        "timetable_travel_over_pred_oneway", "timetable_cycle_over_pred_oneway",
        "timetable_delay_over_pred_maneuver", "c117_leg_over_timetable_cycle",
        "actual_over_pred_mixed_yield",
        "source_queue_fixed_wait_roundtrip_days", "source_queue_fixed_runway_rho",
        "source_queue_fixed_runway_service_days",
        "source_queue_decision_wait_roundtrip_days", "source_queue_decision_runway_rho",
    ]
    overall = {metric: stats([row.get(metric) for row in rows]) for metric in metrics}
    by_seed = {}
    for seed in sorted({row["seed"] for row in rows}):
        seed_rows = [row for row in rows if row["seed"] == seed]
        by_seed[str(seed)] = {
            "line_count": len(seed_rows),
            **{metric: stats([row.get(metric) for row in seed_rows]) for metric in metrics},
        }
    by_arm = {}
    for arm in sorted({row["arm"] for row in rows if row.get("arm") is not None}):
        arm_rows = [row for row in rows if row.get("arm") == arm]
        by_arm[str(arm)] = {
            "line_count": len(arm_rows),
            **{metric: stats([row.get(metric) for row in arm_rows]) for metric in metrics},
        }
    by_route_growth = {}
    for growth in ("0", "1", "2+"):
        growth_rows = [row for row in rows if row.get("route_growth_bucket") == growth]
        if not growth_rows:
            continue
        by_route_growth[growth] = {
            "line_count": len(growth_rows),
            **{metric: stats([row.get(metric) for row in growth_rows]) for metric in metrics},
        }
    by_limit_class = {}
    for limit_class in sorted({row["limit_class"] for row in rows if row.get("limit_class") is not None}):
        limit_rows = [row for row in rows if row.get("limit_class") == limit_class]
        by_limit_class[str(limit_class)] = {
            "line_count": len(limit_rows),
            "decision_2plus_count": sum(
                1 for row in limit_rows
                if isinstance(row.get("decision_fleet"), (int, float)) and row["decision_fleet"] >= 2
            ),
            **{metric: stats([row.get(metric) for row in limit_rows]) for metric in metrics},
        }
    decision_fleet_counts = {
        str(int(planes)): sum(1 for row in rows if row.get("decision_fleet") == planes)
        for planes in sorted({
            row["decision_fleet"] for row in rows
            if isinstance(row.get("decision_fleet"), (int, float))
        })
    }
    source_queue_rows = [
        row for row in rows
        if isinstance(row.get("source_queue_fixed_runway_service_days"), (int, float))
    ]
    source_queue_subset = {
        "line_count": len(source_queue_rows),
        **{metric: stats([row.get(metric) for row in source_queue_rows]) for metric in metrics},
    }
    build_rows = list(builds.values())
    latest_hub_update_by_seed = {}
    for update in hub_delay_updates:
        seed = update.get("seed")
        last_update = update.get("last_update")
        if not isinstance(seed, int) or not isinstance(last_update, (int, float)):
            continue
        current = latest_hub_update_by_seed.get(seed)
        if current is None or last_update > current.get("last_update", -1):
            latest_hub_update_by_seed[seed] = update
    hub_total_ops = sum(
        float(update.get("update_ops_total", 0))
        for update in latest_hub_update_by_seed.values()
        if isinstance(update.get("update_ops_total"), (int, float))
    )
    hub_total_samples = sum(
        float(update.get("update_samples", 0))
        for update in latest_hub_update_by_seed.values()
        if isinstance(update.get("update_samples"), (int, float))
    )
    adapted_builds = [
        build for build in build_rows
        if (isinstance(build.get("hub_delay_window_obs_a"), (int, float))
            and build.get("hub_delay_window_obs_a", 0) > 0)
        or (isinstance(build.get("hub_delay_window_obs_b"), (int, float))
            and build.get("hub_delay_window_obs_b", 0) > 0)
    ]
    return {
        "source_campaign": payload.get("campaign_id"),
        "mature_definition": (
            f"C117 age_bucket >= {min_age}"
            + (f" and <= {max_age}" if max_age is not None else "")
            + "; grouped per seed/line"
        ),
        "matched_mature_lines": len(rows),
        "split_yield_measurable": False,
        "split_yield_note": (
            "NoAI vehicle profit does not expose realised revenue separately for PASS and MAIL; "
            "only mixed realised yield is reported."
        ),
        "overall": overall,
        "by_seed": by_seed,
        "by_arm": by_arm,
        "by_route_growth": by_route_growth,
        "by_limit_class": by_limit_class,
        "source_queue_subset": source_queue_subset,
        "decision_fleet_counts": decision_fleet_counts,
        "hub_delay_learning": {
            "published_update_count": len(hub_delay_updates),
            "station_count": len({
                (update.get("seed"), int(update["station"]))
                for update in hub_delay_updates
                if isinstance(update.get("seed"), int)
                and isinstance(update.get("station"), (int, float))
            }),
            "delay_days": stats([update.get("days") for update in hub_delay_updates]),
            "raw_delay_days": stats([update.get("raw_days") for update in hub_delay_updates]),
            "window_n": stats([update.get("window_n") for update in hub_delay_updates]),
            "variance": stats([update.get("variance") for update in hub_delay_updates]),
            "latest_measured_update_samples": hub_total_samples,
            "latest_measured_update_ops": hub_total_ops,
            "measured_ops_per_observation": (
                hub_total_ops / hub_total_samples if hub_total_samples > 0 else None
            ),
            "adapted_build_count": len(adapted_builds),
            "adapted_build_fraction": (
                len(adapted_builds) / len(build_rows) if build_rows else None
            ),
        },
        "opcode_overhead": {
            "build_count": len(build_rows),
            "demand_ops_same_tick": stats([
                b.get("demand_ops") for b in build_rows
                if isinstance(b.get("demand_ops"), (int, float)) and b.get("demand_ops") >= 0
            ]),
            "demand_ticks": stats([b.get("demand_ticks") for b in build_rows]),
            "eval_ops_same_tick": stats([
                b.get("eval_ops") for b in build_rows
                if isinstance(b.get("eval_ops"), (int, float)) and b.get("eval_ops") >= 0
            ]),
            "eval_ticks": stats([b.get("eval_ticks") for b in build_rows]),
            "demand_suspended_count": sum(
                1 for b in build_rows
                if isinstance(b.get("demand_ticks"), (int, float)) and b.get("demand_ticks") > 0
            ),
            "eval_suspended_count": sum(
                1 for b in build_rows
                if isinstance(b.get("eval_ticks"), (int, float)) and b.get("eval_ticks") > 0
            ),
            "b9_stage_ticks": {
                key: stats([b.get(key) for b in build_rows])
                for key in ("pax_ticks_a", "pax_ticks_b", "mail_ticks_a", "mail_ticks_b")
            },
            "b9_stage_suspended_count": {
                key: sum(
                    1 for b in build_rows
                    if isinstance(b.get(key), (int, float)) and b.get(key) > 0
                )
                for key in ("pax_ticks_a", "pax_ticks_b", "mail_ticks_a", "mail_ticks_b")
            },
            "b9_stage_ops_same_tick": {
                key: stats([
                    b.get(key) for b in build_rows
                    if isinstance(b.get(key), (int, float)) and b.get(key) >= 0
                ])
                for key in ("pax_ops_a", "pax_ops_b", "mail_ops_a", "mail_ops_b")
            },
            "b9_internal_ticks": {
                key: stats([b.get(key) for b in build_rows])
                for key in (
                    "pax_predict_ticks_a", "pax_predict_ticks_b",
                    "pax_coverage_ticks_a", "pax_coverage_ticks_b",
                    "pax_union_ticks_a", "pax_union_ticks_b",
                    "mail_union_ticks_a", "mail_union_ticks_b",
                )
            },
            "b9_internal_suspended_count": {
                key: sum(
                    1 for b in build_rows
                    if isinstance(b.get(key), (int, float)) and b.get(key) > 0
                )
                for key in (
                    "pax_predict_ticks_a", "pax_predict_ticks_b",
                    "pax_coverage_ticks_a", "pax_coverage_ticks_b",
                    "pax_union_ticks_a", "pax_union_ticks_b",
                    "mail_union_ticks_a", "mail_union_ticks_b",
                )
            },
        },
        "rows": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--min-age", type=int, default=6)
    parser.add_argument("--max-age", type=int)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = analyse(payload, min_age=args.min_age, max_age=args.max_age)
    out = args.out or args.input.with_name(args.input.stem + "_summary.json")
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "matched_mature_lines": result["matched_mature_lines"],
        "overall": result["overall"],
        "by_seed": result["by_seed"],
        "by_route_growth": result["by_route_growth"],
        "by_limit_class": result["by_limit_class"],
        "decision_fleet_counts": result["decision_fleet_counts"],
        "opcode_overhead": result["opcode_overhead"],
    }, indent=2))
    print(f"Sortie: {out}")


if __name__ == "__main__":
    main()
