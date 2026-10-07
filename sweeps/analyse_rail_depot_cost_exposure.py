#!/usr/bin/env python3
"""Passive comparison of decision logs for ``rail_depot_cost`` exposure.

This decoder never participates in the simulation.  It compares two already
captured engine logs seed by seed and reports the first place where the paper
rail economics, portfolio order, vivier summary, or chosen rail project differ.
The useful causal observation is a *same date, same rail candidate* economics
delta; terminal economic metrics are deliberately outside this script.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


OPEX_RE = re.compile(r"\bOPEX\s+(\d{4}-\d{1,2}-\d{1,2})\s+(\S+)(?:\s+(.*))?$")
PAIR_RE = re.compile(r"_seed(\d+)_r(\d+)\.log$")


def _fields(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for token in text.split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        out[key] = value
    return out


def _candidate_key(row: dict[str, object]) -> tuple[str, ...]:
    f = row["fields"]
    assert isinstance(f, dict)
    return tuple(str(f.get(k, "")) for k in ("mode", "kind", "cargo", "src", "dst"))


def _parse(path: Path) -> dict[str, list[dict[str, object]]]:
    events: dict[str, list[dict[str, object]]] = defaultdict(list)
    for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        match = OPEX_RE.search(line)
        if not match:
            continue
        date, event, tail = match.groups()
        events[event].append(
            {
                "date": date,
                "line": line_no,
                "fields": _fields(tail or ""),
                "raw": (tail or "").strip(),
            }
        )
    return events


def _numeric_delta(reference: str | None, variant: str | None) -> float | None:
    if reference is None or variant is None:
        return None
    try:
        return float(variant) - float(reference)
    except ValueError:
        return None


def _first_common_rail_delta(ref_events, var_events):
    watched = ("cost", "finance_capital", "profit", "roi", "rank_score", "rank_score_raw", "budget_score")
    ref_by_key = {}
    for row in ref_events.get("PORTFOLIO_RANK", []):
        f = row["fields"]
        if f.get("mode") != "rail":
            continue
        ref_by_key[(row["date"], _candidate_key(row))] = row
    for row in var_events.get("PORTFOLIO_RANK", []):
        f = row["fields"]
        if f.get("mode") != "rail":
            continue
        key = (row["date"], _candidate_key(row))
        prior = ref_by_key.get(key)
        if prior is None:
            continue
        rf = prior["fields"]
        vf = row["fields"]
        changed = [name for name in watched if rf.get(name) != vf.get(name)]
        if not changed:
            continue
        return {
            "date": row["date"],
            "candidate": list(key[1]),
            "changed_fields": changed,
            "reference": {name: rf.get(name) for name in watched},
            "variant": {name: vf.get(name) for name in watched},
            "delta": {name: _numeric_delta(rf.get(name), vf.get(name)) for name in watched},
            "reference_rank": rf.get("rank"),
            "variant_rank": vf.get("rank"),
            "reference_line": prior["line"],
            "variant_line": row["line"],
        }
    return None


def _rank_by_date(events):
    out = defaultdict(list)
    for row in events.get("PORTFOLIO_RANK", []):
        out[row["date"]].append((_candidate_key(row), row["fields"].get("rank")))
    return out


def _first_same_order_rail_delta(ref_events, var_events):
    """Find the strongest direct signature before the visible TOP-5 order moves.

    A later same-candidate delta is not necessarily causal: once the two games have
    diverged, demand, cash and calibration can differ.  Here we only compare dates
    where both arms publish the exact same ordered candidate keys, then look for a
    rail row whose economics fields differ.
    """
    watched = ("cost", "finance_capital", "profit", "roi", "rank_score", "rank_score_raw", "budget_score")
    ref_rows = defaultdict(list)
    var_rows = defaultdict(list)
    for row in ref_events.get("PORTFOLIO_RANK", []):
        ref_rows[row["date"]].append(row)
    for row in var_events.get("PORTFOLIO_RANK", []):
        var_rows[row["date"]].append(row)
    for date in sorted(set(ref_rows) & set(var_rows)):
        rr = ref_rows[date]
        vr = var_rows[date]
        if [_candidate_key(row) for row in rr] != [_candidate_key(row) for row in vr]:
            continue
        for reference, variant in zip(rr, vr):
            rf = reference["fields"]
            vf = variant["fields"]
            if rf.get("mode") != "rail":
                continue
            changed = [name for name in watched if rf.get(name) != vf.get(name)]
            if not changed:
                continue
            return {
                "date": date,
                "candidate": list(_candidate_key(reference)),
                "changed_fields": changed,
                "reference": {name: rf.get(name) for name in watched},
                "variant": {name: vf.get(name) for name in watched},
                "delta": {name: _numeric_delta(rf.get(name), vf.get(name)) for name in watched},
                "rank": rf.get("rank"),
                "reference_line": reference["line"],
                "variant_line": variant["line"],
            }
    return None


def _first_rank_delta(ref_events, var_events):
    ref = _rank_by_date(ref_events)
    var = _rank_by_date(var_events)
    for date in sorted(set(ref) & set(var)):
        ref_keys = [key for key, _rank in ref[date]]
        var_keys = [key for key, _rank in var[date]]
        if ref_keys != var_keys:
            return {
                "date": date,
                "reference": [list(key) for key in ref_keys],
                "variant": [list(key) for key in var_keys],
            }
    return None


def _first_raw_delta(ref_events, var_events, event):
    ref = defaultdict(list)
    var = defaultdict(list)
    for row in ref_events.get(event, []):
        ref[row["date"]].append(row["raw"])
    for row in var_events.get(event, []):
        var[row["date"]].append(row["raw"])
    for date in sorted(set(ref) | set(var)):
        if ref.get(date, []) != var.get(date, []):
            return {"date": date, "reference": ref.get(date, []), "variant": var.get(date, [])}
    return None


def _project_choice_key(row):
    f = row["fields"]
    return tuple(str(f.get(k, "")) for k in ("mode", "cargo", "src", "dst"))


def _choice_sequence_delta(ref_events, var_events):
    """Separate cadence drift from an actual project identity change.

    Comparing raw PROJECT_CHOSEN lines conflates harmless numeric field changes with
    different actions.  This view walks the chosen-project sequences by ordinal:
    same key / different date is a timing drift; different key is a semantic choice
    divergence.  Both are useful, but only the latter supports a ranking-choice
    mechanism.
    """
    ref = ref_events.get("PROJECT_CHOSEN", [])
    var = var_events.get("PROJECT_CHOSEN", [])
    first_timing = None
    first_identity = None
    for index in range(min(len(ref), len(var))):
        rk = _project_choice_key(ref[index])
        vk = _project_choice_key(var[index])
        if rk == vk:
            if first_timing is None and ref[index]["date"] != var[index]["date"]:
                first_timing = {
                    "index": index,
                    "candidate": list(rk),
                    "reference_date": ref[index]["date"],
                    "variant_date": var[index]["date"],
                    "reference_line": ref[index]["line"],
                    "variant_line": var[index]["line"],
                }
            continue
        first_identity = {
            "index": index,
            "reference_date": ref[index]["date"],
            "variant_date": var[index]["date"],
            "reference_candidate": list(rk),
            "variant_candidate": list(vk),
            "reference_line": ref[index]["line"],
            "variant_line": var[index]["line"],
        }
        break
    if first_identity is None and len(ref) != len(var):
        first_identity = {
            "index": min(len(ref), len(var)),
            "reference_date": ref[min(len(ref), len(var))]["date"] if len(ref) > len(var) else None,
            "variant_date": var[min(len(ref), len(var))]["date"] if len(var) > len(ref) else None,
            "reference_candidate": list(_project_choice_key(ref[min(len(ref), len(var))])) if len(ref) > len(var) else None,
            "variant_candidate": list(_project_choice_key(var[min(len(ref), len(var))])) if len(var) > len(ref) else None,
            "reference_line": ref[min(len(ref), len(var))]["line"] if len(ref) > len(var) else None,
            "variant_line": var[min(len(ref), len(var))]["line"] if len(var) > len(ref) else None,
        }
    return {"first_timing_delta": first_timing, "first_identity_delta": first_identity}


def _attempt_key(row):
    f = row["fields"]
    return tuple(str(f.get(k, "")) for k in ("kind", "src", "dst"))


def _first_same_attempt_model_delta(ref_events, var_events):
    """Compare the pre-quote model on an otherwise same physical rail attempt.

    The strongest signature is ``pre/model`` different while the AITestMode
    ``quote`` is equal: the setting changed paper economics, not the physical
    route price.  Matching is deliberately restricted to same date/key.
    """
    ref = defaultdict(list)
    for row in ref_events.get("RAIL_ATTEMPT", []):
        ref[(row["date"], _attempt_key(row))].append(row)
    for row in var_events.get("RAIL_ATTEMPT", []):
        key = (row["date"], _attempt_key(row))
        candidates = ref.get(key, [])
        if not candidates:
            continue
        variant = row["fields"]
        for reference_row in candidates:
            reference = reference_row["fields"]
            pre_changed = reference.get("pre") != variant.get("pre")
            model_changed = reference.get("model") != variant.get("model")
            if not (pre_changed or model_changed):
                continue
            return {
                "date": row["date"],
                "candidate": list(key[1]),
                "reference": {name: reference.get(name) for name in ("pred_profit", "pred_roi", "pre", "model", "quote", "actual", "ok", "reason")},
                "variant": {name: variant.get(name) for name in ("pred_profit", "pred_roi", "pre", "model", "quote", "actual", "ok", "reason")},
                "delta": {name: _numeric_delta(reference.get(name), variant.get(name)) for name in ("pred_profit", "pred_roi", "pre", "model", "quote", "actual")},
                "same_quote": reference.get("quote") == variant.get("quote"),
                "same_outcome": reference.get("ok") == variant.get("ok") and reference.get("reason") == variant.get("reason"),
                "reference_line": reference_row["line"],
                "variant_line": row["line"],
            }
    return None


def _discover(engine_dir: Path, prefix: str) -> dict[tuple[int, int], Path]:
    found = {}
    for path in engine_dir.glob(f"{prefix}_seed*_r*.log"):
        match = PAIR_RE.search(path.name)
        if match:
            found[(int(match.group(1)), int(match.group(2)))] = path
    return found


def analyse(engine_dir: Path, reference_prefix: str, variant_prefix: str):
    reference = _discover(engine_dir, reference_prefix)
    variant = _discover(engine_dir, variant_prefix)
    pairs = sorted(set(reference) & set(variant))
    result = {
        "engine_dir": str(engine_dir),
        "reference_prefix": reference_prefix,
        "variant_prefix": variant_prefix,
        "paired_logs": len(pairs),
        "missing_reference": [list(key) for key in sorted(set(variant) - set(reference))],
        "missing_variant": [list(key) for key in sorted(set(reference) - set(variant))],
        "seeds": [],
    }
    for seed, repeat in pairs:
        ref_events = _parse(reference[(seed, repeat)])
        var_events = _parse(variant[(seed, repeat)])
        choice_sequence = _choice_sequence_delta(ref_events, var_events)
        result["seeds"].append(
            {
                "seed": seed,
                "repeat": repeat,
                "reference_log": str(reference[(seed, repeat)]),
                "variant_log": str(variant[(seed, repeat)]),
                "portfolio_rank_rows": {
                    "reference": len(ref_events.get("PORTFOLIO_RANK", [])),
                    "variant": len(var_events.get("PORTFOLIO_RANK", [])),
                },
                "first_same_order_rail_economics_delta": _first_same_order_rail_delta(ref_events, var_events),
                "first_same_rail_candidate_economics_delta": _first_common_rail_delta(ref_events, var_events),
                "first_same_attempt_model_delta": _first_same_attempt_model_delta(ref_events, var_events),
                "first_portfolio_order_delta": _first_rank_delta(ref_events, var_events),
                "first_vivier_delta": _first_raw_delta(ref_events, var_events, "VIVIER"),
                "first_project_chosen_delta": _first_raw_delta(ref_events, var_events, "PROJECT_CHOSEN"),
                "first_project_chosen_timing_delta": choice_sequence["first_timing_delta"],
                "first_project_chosen_identity_delta": choice_sequence["first_identity_delta"],
            }
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--reference-prefix", default="rail_depot_off")
    parser.add_argument("--variant-prefix", default="rail_depot_on")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = analyse(args.engine_dir, args.reference_prefix, args.variant_prefix)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["paired_logs"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
