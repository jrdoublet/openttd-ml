"""Offline candidate: conserved station arrivals and calibrated capture.

No AI behavior change. Callers must count pickups by ALL services at the
station, separate PASS from MAIL, and identify losses and transfers.
Unknown loss produces a lower bound, never an exact demand observation.
"""
from math import isfinite
from statistics import median


def station_arrivals(*, days, pickups, queue_start, queue_end, losses=None,
                     complete=True, external_deliveries=0):
    values = (days, pickups, queue_start, queue_end, external_deliveries)
    if (not complete or any(not isinstance(x, (int, float)) or not isfinite(x) for x in values)
            or days <= 0 or min(pickups, queue_start, queue_end, external_deliveries) < 0):
        return {"status": "unknown", "monthly": None, "lower_bound_monthly": None}
    # Q_end = Q_start + locally captured arrivals + external deliveries
    #         - all pickups - losses.
    net = pickups + queue_end - queue_start - external_deliveries
    lower = max(0, net) * 30.4 / days
    if losses is None:
        return {"status": "lower_bound", "monthly": None, "lower_bound_monthly": lower}
    if not isinstance(losses, (int, float)) or not isfinite(losses) or losses < 0 or net + losses < 0:
        return {"status": "inconsistent", "monthly": None, "lower_bound_monthly": None}
    monthly = (net + losses) * 30.4 / days
    return {"status": "measured", "monthly": monthly, "lower_bound_monthly": monthly}


def calibrated_station_forecast(current_reference_monthly, history):
    """Learn capture residual locally from exact observations, not revenue.

    Reference is the SAME station model evaluated at each observation date,
    including that date's production and rating. No fitted global discount.
    A measured year is an eligibility condition, not a claim of stationarity.
    """
    eligible = [h for h in history if h.get("status") == "measured"
                and not h.get("capacity_censored", True)
                and isinstance(h.get("reference_monthly"), (int, float))
                and isfinite(h["reference_monthly"]) and h["reference_monthly"] > 0
                and isinstance(h.get("monthly"), (int, float)) and isfinite(h["monthly"])
                and h["monthly"] >= 0 and isinstance(h.get("days"), (int, float))
                and isfinite(h["days"]) and h["days"] > 0]
    if (not isinstance(current_reference_monthly, (int, float))
            or not isfinite(current_reference_monthly) or current_reference_monthly < 0
            or sum(h["days"] for h in eligible) < 330):
        return {"status": "insufficient_observation", "monthly": None, "capture_factor": None}
    # Equal-duration, non-overlapping monthly observations are the input contract.
    factor = median(h["monthly"] / h["reference_monthly"] for h in eligible)
    return {"status": "candidate", "monthly": current_reference_monthly * factor,
            "capture_factor": factor}


def allocate_station_forecast(monthly, route_weights):
    """Conserve the station total; increasing the number of routes creates no flow."""
    if (not isinstance(monthly, (int, float)) or not isfinite(monthly) or monthly < 0
            or not route_weights or any(not isinstance(w, (int, float)) or not isfinite(w) or w < 0
                                      for w in route_weights.values())
            or sum(route_weights.values()) <= 0):
        return None
    total = sum(route_weights.values())
    return {route: monthly * weight / total for route, weight in route_weights.items()}
