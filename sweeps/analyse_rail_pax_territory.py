"""Passive rail-pax territoriality analysis from frozen-harness line telemetry.

The benchmark reconstructs each company's operated lines from monthly savegames.
This analyser never reads NoAI internals and never changes gameplay.  A town is
considered served by rail passengers once a live rail line with passenger capacity
(cargo id 0 in the temperate OpenTTD 15.3 fixture) has that town as an endpoint.

For each seed, compare reference vs pax-only origin-reuse policy and report:
  * first Opex rail-pax service date by TownID;
  * first AAAHogEx rail-pax service date by TownID;
  * Opex claims advanced/created by the variant;
  * whether the newly claimed town was reached from another endpoint already served
    by Opex in the previous monthly snapshot (physical extension signature);
  * whether AAA's first claim is delayed or disappears in the variant game.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
import json
from pathlib import Path


PASSENGER_CARGO_ID = "0"


def _ordinal(value: str | None) -> int | None:
    if not value:
        return None
    y, m, d = (int(part) for part in str(value).split("-")[:3])
    return date(y, m, d).toordinal()


def _rail_pax_lines(snapshot: dict) -> list[dict]:
    out = []
    for line in snapshot.get("lines") or []:
        if line.get("mode") != "rail":
            continue
        capacity = line.get("capacity_by_cargo") or {}
        if int(capacity.get(PASSENGER_CARGO_ID, 0) or 0) <= 0:
            continue
        towns = [int(t) for t in (line.get("town_ids") or []) if t is not None]
        if towns:
            out.append({**line, "town_ids": towns})
    return out


def _company_snapshots(report: dict) -> dict[tuple[str, int, str], list[dict]]:
    grouped = defaultdict(list)
    telemetry = report.get("line_telemetry") or {}
    for snap in telemetry.get("snapshots") or []:
        arm = snap.get("arm")
        if arm not in ("OpexAI", "AAAHogEx"):
            continue
        policy = str(snap.get("duel_policy_id"))
        seed = int(snap.get("seed"))
        grouped[(policy, seed, arm)].append(snap)
    for rows in grouped.values():
        rows.sort(key=lambda row: _ordinal(row.get("date")) or -1)
    return grouped


def _first_claims(rows: list[dict]) -> tuple[dict[int, str], dict[int, dict]]:
    first: dict[int, str] = {}
    context: dict[int, dict] = {}
    previously_served: set[int] = set()
    for snap in rows:
        current: set[int] = set()
        lines = _rail_pax_lines(snap)
        for line in lines:
            current.update(line["town_ids"])
        new_towns = current - set(first)
        for town in sorted(new_towns):
            first[town] = str(snap.get("date"))
            related = [line for line in lines if town in line["town_ids"]]
            prior_endpoints = sorted({
                other
                for line in related
                for other in line["town_ids"]
                if other != town and other in previously_served
            })
            context[town] = {
                "date": str(snap.get("date")),
                "extension_from_previously_served": bool(prior_endpoints),
                "prior_endpoint_towns": prior_endpoints,
                "line_markets": sorted({str(line.get("market_key")) for line in related}),
            }
        previously_served = current
    return first, context


def _date_relation(ref: str | None, var: str | None) -> dict:
    ref_ord, var_ord = _ordinal(ref), _ordinal(var)
    if ref_ord is None and var_ord is None:
        return {"kind": "absent_both", "days": None}
    if ref_ord is None:
        return {"kind": "variant_only", "days": None}
    if var_ord is None:
        return {"kind": "reference_only", "days": None}
    days = var_ord - ref_ord
    return {"kind": "later" if days > 0 else "earlier" if days < 0 else "same", "days": days}


def analyse(report: dict, reference_policy: str, variant_policy: str) -> dict:
    grouped = _company_snapshots(report)
    comparison = report.get("policy_comparison") or {}
    paired = {int(row["seed"]): row for row in (comparison.get("per_pair") or []) if "seed" in row}
    seeds = sorted({seed for policy, seed, _ in grouped if policy in (reference_policy, variant_policy)})
    seed_reports = []
    totals = defaultdict(int)
    aaa_delay_days = []

    for seed in seeds:
        claims = {}
        contexts = {}
        for policy in (reference_policy, variant_policy):
            for arm in ("OpexAI", "AAAHogEx"):
                rows = grouped.get((policy, seed, arm), [])
                first, context = _first_claims(rows)
                claims[(policy, arm)] = first
                contexts[(policy, arm)] = context

        ref_opex = claims[(reference_policy, "OpexAI")]
        var_opex = claims[(variant_policy, "OpexAI")]
        ref_aaa = claims[(reference_policy, "AAAHogEx")]
        var_aaa = claims[(variant_policy, "AAAHogEx")]
        all_towns = sorted(set(ref_opex) | set(var_opex) | set(ref_aaa) | set(var_aaa))
        events = []
        regressions = []
        for town in all_towns:
            opex_rel = _date_relation(ref_opex.get(town), var_opex.get(town))
            # "advanced" means the variant serves first or serves where reference never did.
            advanced = opex_rel["kind"] in ("variant_only", "earlier")
            if advanced:
                aaa_rel = _date_relation(ref_aaa.get(town), var_aaa.get(town))
                aaa_delayed_or_lost = aaa_rel["kind"] in ("later", "reference_only")
                if aaa_rel["kind"] == "later" and aaa_rel["days"] is not None:
                    aaa_delay_days.append(int(aaa_rel["days"]))
                ctx = contexts[(variant_policy, "OpexAI")].get(town, {})
                event = {
                    "town_id": town,
                    "opex_reference_first": ref_opex.get(town),
                    "opex_variant_first": var_opex.get(town),
                    "opex_relation": opex_rel,
                    "physical_extension_signature": bool(ctx.get("extension_from_previously_served")),
                    "prior_endpoint_towns": ctx.get("prior_endpoint_towns", []),
                    "line_markets": ctx.get("line_markets", []),
                    "aaa_reference_first": ref_aaa.get(town),
                    "aaa_variant_first": var_aaa.get(town),
                    "aaa_relation": aaa_rel,
                    "aaa_delayed_or_lost": aaa_delayed_or_lost,
                }
                events.append(event)
                totals["opex_advanced_towns"] += 1
                if event["physical_extension_signature"]:
                    totals["opex_advanced_with_extension_signature"] += 1
                if aaa_delayed_or_lost:
                    totals["advanced_towns_with_aaa_delay_or_loss"] += 1
                    if event["physical_extension_signature"]:
                        totals["extension_signature_with_aaa_delay_or_loss"] += 1

            regressed = opex_rel["kind"] in ("reference_only", "later")
            if regressed:
                aaa_rel = _date_relation(ref_aaa.get(town), var_aaa.get(town))
                regressions.append({
                    "town_id": town,
                    "opex_reference_first": ref_opex.get(town),
                    "opex_variant_first": var_opex.get(town),
                    "opex_relation": opex_rel,
                    "aaa_reference_first": ref_aaa.get(town),
                    "aaa_variant_first": var_aaa.get(town),
                    "aaa_relation": aaa_rel,
                })
                totals["opex_delayed_or_lost_towns"] += 1

        pair = paired.get(seed, {})
        profit_metric = ((pair.get("metrics") or {}).get("profit_year") or {})
        value_metric = ((pair.get("metrics") or {}).get("company_value") or {})

        seed_reports.append({
            "seed": seed,
            "terminal": {
                "profit_year_policy_delta": profit_metric.get("policy_delta"),
                "profit_year_duel_gap_evolution": profit_metric.get("duel_gap_evolution"),
                "company_value_policy_delta": value_metric.get("policy_delta"),
                "company_value_duel_gap_evolution": value_metric.get("duel_gap_evolution"),
            },
            "reference_opex_towns": len(ref_opex),
            "variant_opex_towns": len(var_opex),
            "reference_aaa_towns": len(ref_aaa),
            "variant_aaa_towns": len(var_aaa),
            "advanced_events": events,
            "regressed_events": regressions,
        })

    n_adv = totals["opex_advanced_towns"]
    n_ext = totals["opex_advanced_with_extension_signature"]
    return {
        "schema_version": 1,
        "source": "monthly savegame line telemetry; passive post-processing",
        "passenger_cargo_id": PASSENGER_CARGO_ID,
        "reference_policy": reference_policy,
        "variant_policy": variant_policy,
        "seeds": seeds,
        "totals": dict(totals),
        "ratios": {
            "extension_share_of_advanced": (n_ext / n_adv) if n_adv else None,
            "aaa_delay_or_loss_share_of_advanced": (
                totals["advanced_towns_with_aaa_delay_or_loss"] / n_adv if n_adv else None
            ),
            "aaa_delay_or_loss_share_of_extension_signature": (
                totals["extension_signature_with_aaa_delay_or_loss"] / n_ext if n_ext else None
            ),
        },
        "aaa_delay_days": {
            "count": len(aaa_delay_days),
            "mean": (sum(aaa_delay_days) / len(aaa_delay_days)) if aaa_delay_days else None,
            "max": max(aaa_delay_days) if aaa_delay_days else None,
            "values": aaa_delay_days,
        },
        "per_seed": seed_reports,
    }


def _selftest() -> None:
    def snap(policy, seed, arm, d, lines):
        return {"duel_policy_id": policy, "seed": seed, "arm": arm, "date": d,
                "ok": True, "lines": lines}
    def rail(*towns):
        return {"mode": "rail", "town_ids": list(towns), "market_key": "rail|" + ",".join(map(str, towns)),
                "capacity_by_cargo": {"0": 100}}
    report = {"line_telemetry": {"snapshots": [
        snap("ref", 42, "OpexAI", "1970-01-01", [rail(1, 2)]),
        snap("ref", 42, "OpexAI", "1970-02-01", [rail(1, 2)]),
        snap("var", 42, "OpexAI", "1970-01-01", [rail(1, 2)]),
        snap("var", 42, "OpexAI", "1970-02-01", [rail(1, 2), rail(2, 3)]),
        snap("ref", 42, "AAAHogEx", "1970-02-01", [rail(3, 4)]),
        snap("var", 42, "AAAHogEx", "1970-02-01", []),
        snap("var", 42, "AAAHogEx", "1970-03-01", [rail(3, 4)]),
    ]}}
    out = analyse(report, "ref", "var")
    assert out["totals"]["opex_advanced_towns"] == 1
    event = out["per_seed"][0]["advanced_events"][0]
    assert event["town_id"] == 3
    assert event["physical_extension_signature"] is True
    assert event["prior_endpoint_towns"] == [2]
    assert event["aaa_delayed_or_lost"] is True
    assert event["aaa_relation"]["days"] == 28


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, nargs="?")
    parser.add_argument("--reference-policy", default="reference")
    parser.add_argument("--variant-policy", default="origin_reuse_pax_only")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        _selftest()
        print("analyse_rail_pax_territory selftest: OK")
        return
    if args.input is None:
        parser.error("input JSON requis sans --selftest")
    report = json.loads(args.input.read_text(encoding="utf-8"))
    result = analyse(report, args.reference_policy, args.variant_policy)
    encoded = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        args.out.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)


if __name__ == "__main__":
    main()
