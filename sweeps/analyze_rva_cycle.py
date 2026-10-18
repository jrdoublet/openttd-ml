#!/usr/bin/env python3
"""Read one company's engine log, in order. No game calls or inferred deliveries.

Durations use journal dates, never controller ticks. Calendar/model residuals
are only covered for calendar timekeeping. A sampled rotation cannot rule out
an entire unobserved rotation. Never merge different games/companies in one input.
"""
import argparse
import json
import re
from pathlib import Path
from rva_dry_cycle import from_snapshot

EVENT = re.compile(r"\b(RVA_[A-Z_]+)\s+(.*)")
FIELDS = re.compile(r"([\w.]+)=([^\s]+)")


def value(token):
    if token in ("na", "null"):
        return None
    try:
        return float(token) if "." in token else int(token)
    except ValueError:
        return token


def records(lines):
    for line in lines:
        match = EVENT.search(line)
        if match:
            yield match[1], {k: value(v) for k, v in FIELDS.findall(match[2])}


def duration(start, end):
    """Each transition lies between its last old and first new sample."""
    return [max(0, end[0] - start[1]), end[1] - start[0]]


def number(item):
    return isinstance(item, (int, float))


def analyze(lines):
    output = {"schema": 2, "coverage": "not_covered", "sessions": 0,
              "samples": 0, "lines_observed": [], "vehicles": [], "transitions": [],
              "missing": [], "cycles": [], "contexts": [], "cargo_scopes": [], "sweeps": [],
              "equipment": [],
              "cost": {"frames": [], "prefix_ops": [], "previous_total_ops": [],
                                                        "model_prefix_ops": []}}
    models, fleet = {}, {}
    context = {}
    session = 0
    sample_counts, last_sample_seq = {}, {}

    def missing(key, reason):
        output["missing"].append({"session": session, "line": key[0], "vehicle": key[1],
                                  "reason": reason, "coverage": "not_covered"})

    def close(reason):
        for key, track in fleet.items():
            if track["path"]:
                missing(key, reason)
            output["vehicles"].append({"session": session, "line": key[0], "vehicle": key[1],
                "composition": dict(track["parts"]), "parts": track["last"]["parts"],
                "max_sample_gap_ticks": track["max_gap"]})

    def cycle(key, track, sample):
        path = track["path"]
        edges = [edge["ticks"] for edge in path]
        total = duration(edges[0], edges[4])
        row = {"session": session, "line": key[0], "vehicle": key[1],
               "coverage": "sampled_complete", "exhaustive_coverage": "not_covered",
               "cycle_ticks": total, "outbound_ticks": duration(edges[0], edges[1]),
               "dwell_b_ticks": duration(edges[1], edges[2]),
               "return_ticks": duration(edges[2], edges[3]),
               "dwell_a_ticks": duration(edges[3], edges[4]),
               "dwell_cause": "unknown", "composition": dict(track["parts"]),
               "composition_coverage": "sampled_complete" if len(track["parts"]) == sample["parts"]
                   else "not_covered", "length_16tile": sample["length_16tile"],
               "max_sample_gap_ticks": track["max_gap"], "residual_coverage": "not_covered", "residuals": None}
        # Dates have one-day resolution. Include the whole final sample day;
        # old logs lack date_end, so an intra-sample rollover is not covered.
        dates = [edge["dates"] for edge in path]
        if all(d is not None for d in dates):
            for label, first, last in (("cycle", 0, 4), ("outbound", 0, 1),
                                       ("dwell_b", 1, 2), ("return", 2, 3), ("dwell_a", 3, 4)):
                row[label + "_days"] = duration(dates[first], dates[last])
        row["date_precision_days"] = 1
        row["sample_rollover_coverage"] = "covered" if all(e["date_end_known"] for e in path) else "not_covered"
        model = models.get(key[0])
        # A build snapshot is required; no reconstruction from rounded signs.
        valid = (model and number(model.get("trips_month")) and model["trips_month"] > 0
                 and number(model.get("one_way_days"))
                 and context.get("timekeeping") == 0 and row.get("cycle_days", [0])[0] > 0
                 and model.get("a") == sample.get("a") and model.get("b") == sample.get("b")
                 and context.get("model_days_month", 0) > 0)
        if valid:
            dm = context["model_days_month"]
            total_days = row["cycle_days"]
            predicted_cycle = 2 * dm / model["trips_month"]
            residual = {"coverage": "sampled", "model_cycle_days": predicted_cycle,
                        "model_dwell_per_leg_days": dm / model["trips_month"] - model["one_way_days"],
                        "model_headway_days": model.get("headway_days"),
                        "model_income_days": model.get("income_days"),
                        "cycle_delta_model_days": [d - predicted_cycle for d in total_days],
                        "outbound_delta_model_days": [d - model["one_way_days"] for d in row["outbound_days"]],
                        "return_delta_model_days": [d - model["one_way_days"] for d in row["return_days"]],
                        "cargo": []}
            for end in ("a", "b"):
                residual[f"dwell_{end}_delta_model_days"] = [
                    d - residual["model_dwell_per_leg_days"] for d in row[f"dwell_{end}_days"]]
            for suffix, pred in (("", "per_train"), ("2", "per_train2")):
                cap = sample.get("cap" + suffix)
                loads = [path[i]["load" + suffix] for i in (0, 2)]
                if cap is None:
                    continue
                capacity_rate = [2 * cap * dm / total_days[i] for i in (1, 0)]
                expected = model.get(pred)
                if model.get("cargo" + suffix) != sample.get("cargo" + suffix):
                    expected = None
                expected = expected * model["trips_month"] if expected is not None else None
                residual["cargo"].append({"cargo": sample.get("cargo" + suffix), "capacity": cap,
                    "unit": "cargo_units_per_model_30day_month_per_train",
                    "capacity_rate": capacity_rate, "model_capacity_rate": expected,
                    "capacity_delta": [r - expected for r in capacity_rate] if expected is not None else None,
                    "departing_payload_rate_proxy": [sum(loads) * dm / total_days[i] for i in (1, 0)]
                        if all(load is not None for load in loads) else None,
                    "delivered_rate": None})
            row["residuals"] = residual
            row["residual_coverage"] = "sampled"
            row["dry_cycle"] = from_snapshot(model)
        output["cycles"].append(row)

    for kind, row in records(lines):
        if kind == "RVA_BEGIN":
            close("session_reset")
            initial_models = models if session == 0 else {}
            session += 1
            output["sessions"] += 1
            fleet, models, context = {}, initial_models, row
            output["contexts"].append({"session": session, **row})
        elif kind == "RVA_MODEL":
            if row.get("line") is not None:
                models[row["line"]] = row
        elif kind == "RVA_CARGOS":
            output["cargo_scopes"].append({"session": session, **row})
        elif kind == "RVA_EQUIPMENT":
            output["equipment"].append({"session": session, **row})
        elif kind == "RVA_SWEEP":
            output["sweeps"].append({"session": session, **row})
        elif kind in ("RVA_COST", "RVA_MODEL_COST"):
            output["cost"]["frames"].append({"session": session, "event": kind, **row})
            field = "model_prefix_ops" if kind == "RVA_MODEL_COST" else "prefix_ops"
            if row.get("ops_prefix") is not None:
                output["cost"][field].append(row["ops_prefix"])
            if row.get("previous_total") is not None:
                output["cost"]["previous_total_ops"].append(row["previous_total"])
        elif kind in ("RVA_SAMPLE", "RVA_LOST"):
            key = row.get("line"), row.get("vehicle")
            if None in key:
                missing(key, "incomplete_identity")
                continue
            if kind == "RVA_LOST":
                missing(key, "vehicle_lost")
                fleet.pop(key, None)
                continue
            output["samples"] += 1
            sample_counts[session] = sample_counts.get(session, 0) + 1
            last_sample_seq[session] = row.get("seq")
            if row["line"] not in output["lines_observed"]:
                output["lines_observed"].append(row["line"])
            required = ("tick", "parts", "length_16tile", "engine", "cap", "load")
            if (any(not number(row.get(k)) for k in required)
                    or row.get("phase") not in ("A", "B", "R", "D", "X")
                    or not number(row.get("tick_end", row.get("tick")))
                    or row.get("tick_end", row.get("tick")) < row.get("tick", 0)):
                missing(key, "incomplete_sample")
                fleet.pop(key, None)
                continue
            signature = tuple(row.get(k) for k in
                              ("build_date", "engine", "parts", "length_16tile", "cargo", "cap", "cargo2", "cap2", "a", "b"))
            track = fleet.get(key)
            if track and (track["signature"] != signature or row["tick"] <= track["last"]["tick"]
                          or row.get("age_days", 0) < track["last"].get("age_days", 0)
                          or (number(row.get("date")) and number(track["last"].get("date"))
                              and row["date"] < track["last"]["date"])):
                missing(key, "identity_composition_or_clock_changed")
                track = None
            if track is None:
                missing(key, "initial_partial")
                track = {"signature": signature, "last": row, "path": [], "parts": {}, "max_gap": 0}
                fleet[key] = track
            part, engine = row.get("part"), row.get("part_engine")
            if part is not None and 0 <= part < row["parts"] and engine is not None:
                if part in track["parts"] and track["parts"][part] != engine:
                    missing(key, "part_engine_changed")
                    track["path"], track["parts"] = [], {}
                track["parts"][part] = engine
            old = track["last"]
            track["max_gap"] = max(track["max_gap"], row["tick"] - old["tick"])
            pair = old["phase"], row["phase"]
            if (pair == ("R", "R") and old.get("order_tile") is not None
                    and row.get("order_tile") is not None and old["order_tile"] != row["order_tile"]):
                missing(key, "order_changed_between_samples")
                track["path"] = []
            if pair[0] != pair[1]:
                edge = {"session": session, "line": key[0], "vehicle": key[1],
                        "from": pair[0], "to": pair[1], "ticks": [old["tick"], row.get("tick_end", row["tick"])],
                        "load": row.get("load"), "load2": row.get("load2")}
                date_end = row.get("date_end", row.get("date"))
                edge["dates"] = ([old["date"], date_end + 1]
                    if number(old.get("date")) and number(row.get("date")) and number(date_end)
                    and date_end >= row["date"] >= old["date"] else None)
                edge["date_end_known"] = "date_end" in row and edge["dates"] is not None
                output["transitions"].append(edge)
                expected = [("R", "B"), ("B", "R"), ("R", "A"), ("A", "R")]
                if track["path"]:
                    if pair == expected[len(track["path"]) - 1]:
                        track["path"].append(edge)
                        if len(track["path"]) == 5:
                            cycle(key, track, row)
                            track["path"] = []
                    else:
                        missing(key, "missing_transition_or_detour")
                        track["path"] = []
                elif pair not in (("A", "R"), ("R", "A"), ("R", "B"), ("B", "R")):
                    missing(key, "missing_transition_or_detour")
                if pair == ("A", "R"):
                    track["path"] = [edge]
            track["last"] = row
    close("end_of_log")
    if output["cycles"]:
        output["coverage"] = "sampled_complete"
    output["cost"]["coverage"] = "prefix_and_lagged_total_last_tail_not_covered"
    last_cost = {frame["session"]: frame for frame in output["cost"]["frames"] if frame["event"] == "RVA_COST"}
    output["cost"]["session_totals"] = []
    for sid, frame in last_cost.items():
        values = [frame.get(k) for k in ("completed_ops", "ops_prefix", "model_completed_ops")]
        total = sum(values) if all(number(v) for v in values) else None
        samples = sample_counts.get(sid, 0)
        covers_samples = (number(last_sample_seq.get(sid)) and number(frame.get("seq"))
                          and frame["seq"] >= last_sample_seq[sid])
        output["cost"]["session_totals"].append({"session": sid, "measured_prefix_ops": total,
            "ops_per_observation": total / samples if total is not None and samples and covers_samples else None,
            "samples": samples, "calls": frame.get("calls"), "skipped": frame.get("skipped"),
            "scope": "between_measurement_markers_final_tail_and_entry_return_not_covered"})
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="one game/company engine log")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    with args.log.open(encoding="utf-8", errors="replace") as source:
        result = analyze(source)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
