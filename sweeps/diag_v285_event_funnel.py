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
import gzip
import json
from pathlib import Path
import re


LOG_NAME = re.compile(r"^(?P<arm>.+)_seed(?P<seed>\d+)_r(?P<repeat>\d+)\.log(?:\.gz)?$")
EVENT = re.compile(
    r"\bOPEX\s+(?P<day>\d{4}-\d{1,2}-\d{1,2})\s+"
    r"(?P<tag>V285_GATE|V285_RESULT|V285)\b(?P<rest>[^\r\n]*)"
)
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
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
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
    }


def summarize(events):
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
            else:
                counters["intent_events_missing_pair_identity"] += 1
        else:
            action = event["action"]
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
        groups[(str(path.parent), name)].append(path)
    runs = []
    duplicates_collapsed = 0
    for (_, name), files in sorted(groups.items()):
        identity = LOG_NAME.fullmatch(name)
        parsed = [(file, read_one(file)) for file in files]
        first_file, first = parsed[0]
        for file, alternative in parsed[1:]:
            if (first["signatures"] != alternative["signatures"]
                    or first["unparsed_marker_lines"] != alternative["unparsed_marker_lines"]):
                raise ValueError(f"copies log/gzip contradictoires : {first_file} / {file}")
        duplicates_collapsed += len(files) - 1
        summary = summarize(first["events"])
        runs.append({
            "arm": identity["arm"], "seed": int(identity["seed"]),
            "repeat": int(identity["repeat"]),
            "source_files": [str(file) for file in files],
            "observed_unique_events": len(first["events"]),
            "raw_event_lines": first["raw_events"],
            "identical_event_lines_ignored": first["identical_event_lines_ignored"],
            "unparsed_marker_lines": first["unparsed_marker_lines"],
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
        "log_gzip_copies_collapsed": duplicates_collapsed,
        "logical_games": len(runs),
        "by_arm": {arm: dict(sorted(values.items())) for arm, values in sorted(by_arm.items())},
        "runs": runs,
        "limits": [
            "V285_GATE repeats by line over time; gates are not unique candidate projects.",
            "V285 action=wagon is an intent, not evidence of a constructed wagon.",
            "Only V285_RESULT action=moved with complete operation identity counts as a confirmed move.",
            "V285_RESULT action=completed is a notification, not a second move.",
            "Intent/move signature overlap uses line+old/new counts only; no causal or chronological matching is asserted.",
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
