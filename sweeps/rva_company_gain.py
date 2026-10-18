"""RVA-09: passive ledger and comparability gate, never a portfolio score.

Economic identity from RVA-02 / plan section 1. The caller supplies predictions
with provenance, not a before/after difference labelled as a causal measurement.
No conversion of physical demand to incremental demand, or capital to expense.
"""
from rva_dry_cycle import known


def service_externality(*, demand_before_month, allocation_delta_month,
                        capacity_month, waiting, horizon_months,
                        observed_delivered_month, final_receipts_annual,
                        avoidable_cost_delta_annual=0):
    """Marginal receipts, with fixed fleet costs unchanged by lost passengers.

    Stock can sustain a saturated service over the common horizon. Vehicle
    transfer credits are NOT final receipts. Values must be same cargo/price
    context; aggregate each station's routes before allocating to vehicles.
    """
    nonnegative = (demand_before_month, capacity_month, waiting,
                   observed_delivered_month, final_receipts_annual)
    if (any(not known(v) or v < 0 for v in nonnegative)
            or not known(allocation_delta_month) or not known(horizon_months)
            or horizon_months <= 0 or not known(avoidable_cost_delta_annual)
            or observed_delivered_month <= 0):
        return {'status': 'not_covered', 'revenue_delta_annual': None}
    before = min(capacity_month, demand_before_month + waiting / horizon_months)
    after = min(capacity_month, max(0, demand_before_month + allocation_delta_month)
                + waiting / horizon_months)
    # Empirical receipts per delivered unit, not profit per unit (fixed costs).
    delta = (after - before) / observed_delivered_month * final_receipts_annual
    return {'status': 'estimated_constant_marginal_receipts',
            'revenue_delta_annual': delta,
            'avoidable_cost_delta_annual': avoidable_cost_delta_annual,
            'profit_delta_annual': delta - avoidable_cost_delta_annual,
            'served_delta_month': after - before}


def company_gain(line, affected_services, *, affected_inventory_complete):
    """All cashflows are per the same explicit economic year/context/horizon.

    service deltas are after minus before. Only avoidable cost variations enter
    the externality. A retained aircraft's fixed costs therefore cancel, rather
    than being credited as savings for each displaced passenger.
    """
    context = line["context"]
    if set(context) != {"fingerprint", "horizon", "currency", "annual_clock"} or any(
            not context[k] for k in context):
        raise ValueError("Explicit context/horizon/currency/clock required")
    if line["revenue_basis"] != "final_company_receipts":
        raise ValueError("Transfer credits and vehicle accounting profit are not final receipts")
    if line["demand_basis"] != "physical_line_demand":
        raise ValueError("Do not charge externalities on V216a net-scaled physical demand")
    corrections = line["corrections"]
    if not isinstance(corrections, dict):
        raise ValueError("Corrections must identify each corrected field")
    for field, stages in corrections.items():
        if (not isinstance(stages, list) or len(stages) != len(set(stages))
                or len(stages) > 1):
            raise ValueError(f"Multiple corrections to {field} need an explicit separate model")
    terms = [line.get(k) for k in ("revenue_annual", "running_annual", "amort_annual")]
    line_profit = terms[0] - terms[1] - terms[2] if all(
        known(v) and v >= 0 for v in terms) else None
    missing, effects, seen = [], [], set()
    for service in affected_services:
        identity = service["service_id"]
        if identity in seen:
            raise ValueError("Duplicate affected service: aggregate cargo/directions once")
        seen.add(identity)
        if service["context"] != context:
            raise ValueError("Affected service has a different economic context")
        revenue, costs = service.get("revenue_delta_annual"), service.get("avoidable_cost_delta_annual")
        effect = revenue - costs if known(revenue) and known(costs) and service.get("source") else None
        if effect is None:
            missing.append(identity)
        effects.append({"service_id": identity, "profit_delta_annual": effect,
                        "source": service.get("source"), "status": "input_prediction"})
    network = sum(s["profit_delta_annual"] for s in effects) if (
        affected_inventory_complete is True and not missing) else None
    gain = line_profit + network if line_profit is not None and network is not None else None
    capital = line.get("capital_required")
    return {"context": dict(context), "profit_line_annual": line_profit,
            "network_delta_annual": network, "gain_company_annual": gain,
            "capital_required": capital if known(capital) and capital >= 0 else None,
            "line_demand": line.get("line_demand"), "affected_services": effects,
            "missing_service_effects": missing, "corrections": corrections,
            "gain_status": "input_prediction" if gain is not None else "not_covered",
            "causal_measurement": False}


def comparable_alternatives(alternatives):
    """Require net contributions for *every* mode before a hypothetical ranking.

    This gate neither replaces OpexC70Profit/C69 nor makes the absolute profit
    admission floor or a changed rank into a replay of an actual purchase.
    """
    if not alternatives:
        return {"comparable": False, "reasons": ["no_alternatives"]}
    expected = alternatives[0]["context"]
    reasons, seen = [], set()
    for row in alternatives:
        identity = row["project_id"]
        if identity in seen:
            raise ValueError("Duplicate alternative identity")
        seen.add(identity)
        if row["context"] != expected:
            reasons.append(f"{identity}:context_mismatch")
        if row["profit_basis"] != "net_company_contribution":
            reasons.append(f"{identity}:profit_basis_mismatch")
        if not known(row.get("gain_company_annual")):
            reasons.append(f"{identity}:unknown_gain")
    return {"comparable": not reasons, "reasons": reasons}
