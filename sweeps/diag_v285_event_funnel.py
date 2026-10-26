#!/usr/bin/env python3
"""Read-only V285 event funnel from existing OpenTTD engine logs.

Usage: python -B -X utf8 sweeps/diag_v285_event_funnel.py results/v285m6_exposure_5x3_pc_20261020_engine

Only actual V285_RESULT action=moved supports an observed wagon move.
V285 action=wagon is an intention, V285_GATE is a gating decision, and
action=completed is a separate completion notification, NOT another move.
Neither this diagnostic nor an event count estimates causal revenue/ROI.
"""

import argparse
from collections import Counter, defaultdict
from datetime import date
import gzip
import json
from pathlib import Path
import re


LOG_NAME = re.compile(r"^(?P<arm>.+)_seed(?P<seed>\d+)_r(?P<repeat>\d+)\.log(?:\.gz)?$")
OPEX_COMPANY = re.compile(r"\[(?P<company>\d+)\]\s+\[[A-Z]\]\s+OPEX\b")
EVENT = re.compile(
    r"\[0\]\s+\[I\]\s+OPEX\s+(?P<day>\d{4}-\d{1,2}-\d{1,2})\s+"
    r"(?P<tag>V285_GATE|V285_RESULT|V285)\b(?P<rest>[^\r\n]*)"
)
OPEX_DAY = re.compile(r"\[0\]\s+\[I\]\s+OPEX\s+(\d{4}-\d{1,2}-\d{1,2})\b")
KEY_VALUES = re.compile(r"\b([A-Za-z_][A-Za-z_0-9]*)=(\S+)")
FIELDS = {
    "gate": ("line", "reason", "trains", "wagons", "platform"),
    "wagon_intent": ("line", "kind", "old_wagons", "new_wagons", "platform",
                     "waiting", "train_cap", "speed", "new_speed"),
    "result": ("line", "action", "reason", "date", "old_wagons", "new_wagons", "cost"),
}
INTEGER_FIELDS = {"line", "trains", "wagons", "platform", "old_wagons", "new_wagons",
                  "waiting", "train_cap", "speed", "new_speed", "date", "cost"}


def read_one(path):
    """Parse one file; identical event lines on the same date count once."""
    path = Path(path)
    opener = gzip.open if path.name.endswith(".gz") else open
    unique = {}
    raw_events = 0
    unparsed_markers = 0
    last_opex_day = None
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            observed_day = OPEX_DAY.search(raw)
            if observed_day:
                candidate_day = tuple(int(part) for part in observed_day[1].split("-"))
                if last_opex_day is None or candidate_day > last_opex_day:
                    last_opex_day = candidate_day
            # The same engine log can include messages from the rival company.
            # Only company [0] belongs to OpexAI in this campaign format.
            emitter = OPEX_COMPANY.search(raw)
            if emitter is not None and int(emitter["company"]) != 0:
                continue
            # Other V285 actions are out of scope, but a malformed selected
            # marker must not disappear without an explicit coverage warning.
            selected = ("V285_GATE" in raw or "V285_RESULT" in raw
                        or "V285 action=wagon" in raw)
            if not selected:
                continue
            found = EVENT.search(raw)
            if not found:
                unparsed_markers += 1
                continue
            tag = found.group("tag")
            kv = dict(KEY_VALUES.findall(found.group("rest")))
            if tag == "V285" and kv.get("action") != "wagon":
                unparsed_markers += 1
                continue
            kind = ("gate" if tag == "V285_GATE" else
                    "result" if tag == "V285_RESULT" else "wagon_intent")
            values = {}
            for field in FIELDS[kind]:
                raw_value = kv.get(field)
                if field in INTEGER_FIELDS:
                    try:
                        values[field] = int(raw_value) if raw_value is not None else None
                    except ValueError:
                        values[field] = None
                else:
                    values[field] = raw_value
            # `kind=pax` is a cargo field of the wagon intent, distinct from
            # the event family; do not let it replace the parser's event type.
            event = {"day": found.group("day"), "event_type": kind, **values}
            # Include all raw key/value pairs in the identity, so distinct
            # observations cannot collapse just because selected fields match.
            signature = (event["day"], kind, tuple(sorted(kv.items())))
            raw_events += 1
            unique.setdefault(signature, event)
    return {
        "events": list(unique.values()),
        "signatures": frozenset(unique),
        "raw_events": raw_events,
        "identical_event_lines_ignored": raw_events - len(unique),
        "unparsed_marker_lines": unparsed_markers,
        "last_opex_day": (
            f"{last_opex_day[0]:04d}-{last_opex_day[1]:02d}-{last_opex_day[2]:02d}"
            if last_opex_day is not None else None
        ),
    }


def summarize(events, last_opex_day=None):
    """A moved+completed pair identifies ONE result operation, never two."""
    counters = Counter()
    gates = Counter()
    gate_lines = defaultdict(set)
    missing = {kind: Counter() for kind in FIELDS}
    per_line = defaultdict(lambda: {
        "gates": Counter(), "wagon_intentions": 0,
        "moved_results": 0, "completed_results": 0,
        "other_results": 0, "confirmed_move_operations": 0,
    })
    operations = defaultdict(set)
    intention_lines, moved_lines, completed_lines = set(), set(), set()
    intent_signatures = Counter()
    intent_dates = defaultdict(list)
    result_details = defaultdict(list)
    for event in events:
        kind, line = event["event_type"], event["line"]
        counters[kind + "_events"] += 1
        for field in FIELDS[kind]:
            if event[field] is None:
                missing[kind][field] += 1
        detail = per_line[line] if line is not None else None
        if kind == "gate":
            reason = event["reason"] if event["reason"] is not None else "<missing>"
            gates[reason] += 1
            if line is not None:
                gate_lines[reason].add(line)
                detail["gates"][reason] += 1
        elif kind == "wagon_intent":
            if line is not None:
                intention_lines.add(line)
                detail["wagon_intentions"] += 1
            signature = (line, event["old_wagons"], event["new_wagons"])
            if all(value is not None for value in signature):
                intent_signatures[signature] += 1
                intent_dates[signature].append(event["day"])
            else:
                counters["intent_events_missing_pair_identity"] += 1
        else:
            action = event["action"]
            pair_signature = (line, event["old_wagons"], event["new_wagons"])
            if all(part is not None for part in pair_signature):
                result_details[pair_signature].append({
                    "day": event["day"], "action": action, "reason": event["reason"],
                })
            if action == "moved":
                counters["moved_result_events"] += 1
                if line is not None:
                    moved_lines.add(line)
                    detail["moved_results"] += 1
            elif action == "completed":
                counters["completed_result_events"] += 1
                if line is not None:
                    completed_lines.add(line)
                    detail["completed_results"] += 1
            else:
                counters["other_result_events"] += 1
                if detail is not None:
                    detail["other_results"] += 1
            # Internal 'date' is the source's operation token. Without a full
            # token, the notification remains visible but is not claimed as a
            # unique, confirmed wagon move.
            identity = (event["line"], event["date"],
                        event["old_wagons"], event["new_wagons"])
            if action in ("moved", "completed"):
                if all(value is not None for value in identity):
                    operations[identity].add(action)
                else:
                    counters["result_events_missing_operation_identity"] += 1

    confirmed = {key for key, actions in operations.items() if "moved" in actions}
    moved_signatures = Counter((line, before, after)
                               for line, _, before, after in confirmed)
    # Calendar dates differ between intent and eventual completion. Pairing
    # line+old/new is only a descriptive signature overlap, not a guarantee
    # that a particular intention caused a particular move.
    signature_overlap = sum(min(count, moved_signatures[key])
                            for key, count in intent_signatures.items())
    counters["intent_move_signature_overlap"] = signature_overlap
    counters["intent_events_without_move_signature_match"] = (
        sum(intent_signatures.values()) - signature_overlap)
    counters["moves_without_intent_signature_match"] = (
        len(confirmed) - signature_overlap)
    unmatched_intentions = []
    for signature, total in sorted(intent_signatures.items()):
        moved_count = moved_signatures[signature]
        unmatched = max(0, total - moved_count)
        if unmatched == 0:
            continue
        dates = sorted(intent_dates[signature],
                       key=lambda value: tuple(int(part) for part in value.split("-")))
        outcomes = sorted(result_details[signature], key=lambda row: (
            tuple(int(part) for part in row["day"].split("-")), row["action"] or "",
        ))
        non_move = [row for row in outcomes if row["action"] not in ("moved", "completed")]
        completion_only = (
            any(row["action"] == "completed" for row in outcomes) and moved_count == 0
        )
        latest = date(*map(int, dates[-1].split("-")))
        last = date(*map(int, last_opex_day.split("-"))) if last_opex_day else None
        unmatched_intentions.append({
            "line": signature[0],
            "old_wagons": signature[1],
            "new_wagons": signature[2],
            "intention_count": total,
            "confirmed_move_count_same_signature": moved_count,
            "unmatched_signature_count": unmatched,
            "intention_days": dates,
            "other_result_events_same_signature": non_move,
            "classification": (
                "non_move_result_logged" if non_move else
                "completion_without_confirmed_move" if completion_only else
                "pending_or_unobserved"
            ),
            "days_from_latest_intention_to_last_opex_log": (
                (last - latest).days if last is not None else None
            ),
        })
    for line, _, _, _ in confirmed:
        per_line[line]["confirmed_move_operations"] += 1
    counters["confirmed_move_operations"] = len(confirmed)
    counters["completed_operation_notifications"] = sum(
        "completed" in actions for actions in operations.values())
    counters["moved_and_completed_same_operation"] = sum(
        actions == {"moved", "completed"} for actions in operations.values())
    counters["completed_without_moved_operation"] = sum(
        actions == {"completed"} for actions in operations.values())
    counters["moved_without_completed_notification"] = sum(
        actions == {"moved"} for actions in operations.values())

    def detail_dict(value):
        return {**value, "gates": dict(sorted(value["gates"].items()))}

    names = ("gate_events", "wagon_intent_events", "result_events",
             "moved_result_events", "completed_result_events", "other_result_events",
             "confirmed_move_operations", "completed_operation_notifications",
             "moved_and_completed_same_operation", "completed_without_moved_operation",
             "moved_without_completed_notification",
             "result_events_missing_operation_identity",
             "intent_events_missing_pair_identity", "intent_move_signature_overlap",
             "intent_events_without_move_signature_match",
             "moves_without_intent_signature_match")
    return {
        "counts": {name: counters[name] for name in names},
        "gate_events_by_reason": dict(sorted(gates.items())),
        "distinct_gate_lines_by_reason": {
            reason: len(lines) for reason, lines in sorted(gate_lines.items())},
        "distinct_line_counts": {
            "gate": len(set().union(*gate_lines.values())) if gate_lines else 0,
            "wagon_intent": len(intention_lines),
            "moved_result": len(moved_lines),
            "completed_result": len(completed_lines),
            "intention_without_observed_move": len(intention_lines - moved_lines),
            "move_without_logged_intention": len(moved_lines - intention_lines),
        },
        "missing_fields_by_kind": {
            kind: {name: missing[kind][name] for name in fields}
            for kind, fields in FIELDS.items()},
        "per_line": {str(k): detail_dict(v) for k, v in sorted(per_line.items())},
        "unmatched_intention_signatures": unmatched_intentions,
    }


def _paths(inputs):
    selected = {}
    for source in inputs:
        path = Path(source)
        if path.is_dir():
            files = sorted(p for p in path.iterdir() if p.is_file() and LOG_NAME.fullmatch(p.name))
        elif path.is_file() and LOG_NAME.fullmatch(path.name):
            files = [path]
        else:
            raise ValueError(f"dossier ou journal V285 absent/invalide : {path}")
        for file in files:
            selected[str(file.resolve())] = file.resolve()
    if not selected:
        raise ValueError("aucun journal *_seedN_rR.log[.gz] trouve")
    return sorted(selected.values())


def analyze(inputs):
    """Analyze existing campaign logs; never launch games or write any file."""
    groups = defaultdict(list)
    for path in _paths(inputs):
        name = path.name[:-3] if path.name.endswith(".gz") else path.name
        match = LOG_NAME.fullmatch(name)
        logical_key = (str(path.parent), match["arm"],
                       int(match["seed"]), int(match["repeat"]))
        groups[logical_key].append(path)
    runs = []
    gzip_copies_collapsed = 0
    numeric_aliases_collapsed = 0
    # Preserve the previous filename-lexicographic run order for consumers,
    # while detecting aliases using numeric game identities.
    ordered_groups = sorted(groups.items(), key=lambda item: (
        item[0][0], min(path.name for path in item[1])))
    for (_, arm, seed, repeat), files in ordered_groups:
        parsed = [(file, read_one(file)) for file in files]
        first_file, first = parsed[0]
        for file, alternative in parsed[1:]:
            if (first["signatures"] != alternative["signatures"]
                    or first["unparsed_marker_lines"] != alternative["unparsed_marker_lines"]
                    or first["last_opex_day"] != alternative["last_opex_day"]):
                first_base = (first_file.name[:-3] if first_file.name.endswith(".gz")
                              else first_file.name)
                other_base = (file.name[:-3] if file.name.endswith(".gz")
                              else file.name)
                kind = "log/gzip" if first_base == other_base else "alias numerique"
                raise ValueError(f"copies {kind} contradictoires : {first_file} / {file}")
        basenames = [file.name[:-3] if file.name.endswith(".gz") else file.name
                     for file in files]
        gzip_copies_collapsed += len(files) - len(set(basenames))
        numeric_aliases_collapsed += len(set(basenames)) - 1
        summary = summarize(first["events"], last_opex_day=first["last_opex_day"])
        runs.append({
            "arm": arm, "seed": seed, "repeat": repeat,
            "source_files": [str(file) for file in files],
            "observed_unique_events": len(first["events"]),
            "raw_event_lines": first["raw_events"],
            "identical_event_lines_ignored": first["identical_event_lines_ignored"],
            "unparsed_marker_lines": first["unparsed_marker_lines"],
            "last_logged_opex_day": first["last_opex_day"],
            **summary,
        })
    by_arm = defaultdict(lambda: Counter())
    for run in runs:
        counts = by_arm[run["arm"]]
        counts["logical_games"] += 1
        for key, value in run["counts"].items():
            counts[key] += value
        counts["unparsed_marker_lines"] += run["unparsed_marker_lines"]
    return {
        "scope": "observed V285 log events only; no build inference from intention or causal ROI",
        "source_files": sum(len(group) for group in groups.values()),
        "log_gzip_copies_collapsed": gzip_copies_collapsed,
        "numeric_name_aliases_collapsed": numeric_aliases_collapsed,
        "logical_games": len(runs),
        "by_arm": {arm: dict(sorted(values.items())) for arm, values in sorted(by_arm.items())},
        "runs": runs,
        "limits": [
            "V285_GATE repeats by line over time; gates are not unique candidate projects.",
            "V285 action=wagon is an intent, not evidence of a constructed wagon.",
            "Only V285_RESULT action=moved with complete operation identity counts as a confirmed move.",
            "V285_RESULT action=completed is a notification, not a second move.",
            "Intent/move signature overlap uses line+old/new counts only; no causal or chronological matching is asserted.",
            "Unmatched signatures do not identify a failed attempt: delayed moves or end-of-log censoring remain possible.",
            "Days since latest intention end at the last logged Opex date, not a verified completion horizon.",
            "Events may be absent when the diagnostic is disabled or logs are truncated.",
            "No causal profit, counterfactual build, or station-platform cost estimate.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path, help="journaux .log/.log.gz ou dossiers existants")
    args = parser.parse_args()
    try:
        result = analyze(args.inputs)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
