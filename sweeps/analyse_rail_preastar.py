#!/usr/bin/env python3
"""Analyse passive des recherches A* rail journalisees par RID.

Contrat attendu (une ligne OPEX datee par evenement) :
  RAIL_PREASTAR_START rid=<tick+identite> mode=primary|upgrade|stock
    kind=pax|freight|- cargo=<label|-> src=<tile|-1> dst=<tile|-1>
    line=<id|-1> budget=<n> length=<n> na=<n> nb=<n>
    amin=<n> amax=<n> azero=<n> awater=<n>
    bmin=<n> bmax=<n> bzero=<n> bwater=<n>
    aps=<lead:exit:free:water:rail,...> bps=<idem> probe_ops=<n>
    [feature=value ...]
  RAIL_PREASTAR_FRONTIER rid=<meme_id> segment=<n> iters=<n> used=<n>
    open=<n> sampled=<n> viable=<n> backtracks=<n> prefix=<n>
  RAIL_PREASTAR_END rid=<meme_id> stop=OK|ABND|NOPA|DEAD|TIMEOUT|SUPERSEDE|CANCEL
    iters=<n> budget=<n> [segments=<n> backtracks=<n> choices=<n>
    alternatives=<n> prefix=<n> active_open=<-1|n> segment_used=<n>]
  RAIL_PREASTAR_BUILD rid=<meme_id> reason=<issue> ok=0|1
    status=built|failed|ready|cash|expired|dropped

Une recherche est identifiee par (bras, graine, repetition, rid), dont le
token comprend le tick de depart ET l'identite metier. END/BUILD n'ont pas
de mode : on ne le devine qu'a partir d'un START unique valide.
Un champ manquant, un conflit ou une recherche incomplete restent observables,
mais n'entrent jamais dans une matrice de confusion. Les resultats proviennent
de parties sondees : ils ne justifient aucun filtre ni gain economique.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import json
from pathlib import Path
import re

LOG_NAME = re.compile(r"(?P<arm>.+)_seed(?P<seed>\d+)_r(?P<repeat>\d+)\.log$")
EVENT = re.compile(
    r"\bOPEX\s+(?P<day>\d{4}-\d{1,2}-\d{1,2})\s+"
    r"(?P<tag>RAIL_PREASTAR_(?:START|END|BUILD|FRONTIER))\s+(?P<fields>.*)$"
)
FIELD_NAME = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
THRESHOLD = re.compile(
    r"(?P<field>[A-Za-z_][A-Za-z_0-9]*)(?P<op>>=|<=|==|>|<)"
    r"(?P<value>-?(?:\d+(?:\.\d*)?|\.\d+))$"
)
MODES = {"primary", "upgrade", "stock"}
STOPS = {"OK", "ABND", "NOPA", "DEAD", "TIMEOUT", "SUPERSEDE", "CANCEL"}
BUILD_STATUSES = {"built", "failed", "ready", "cash", "expired", "dropped"}
TERMINAL_BUILD_STATUSES = {"built", "failed", "expired", "dropped"}
START_REQUIRED = ("mode", "kind", "cargo", "src", "dst", "line", "budget", "length",
                  "na", "nb", "amin", "amax", "azero", "awater", "bmin", "bmax",
                  "bzero", "bwater", "aps", "bps", "probe_ops")
FRONTIER_REQUIRED = ("segment", "iters", "used", "open", "sampled", "viable",
                     "backtracks", "prefix")
END_SEGMENTED = ("segments", "backtracks", "choices", "alternatives",
                 "prefix", "active_open", "segment_used")
INTEGER_FIELDS = {"src", "dst", "line", "budget", "length", "na", "nb", "amin",
                  "amax", "azero", "awater", "bmin", "bmax", "bzero", "bwater",
                  "probe_ops", "iters", "segment", "used", "open", "sampled",
                  "viable", "backtracks", "prefix", "segments", "choices",
                  "alternatives", "active_open", "segment_used"}
SIGNED_FIELDS = {"src", "dst", "line", "length", "amin", "bmin", "active_open"}
CORE_FIELDS = {"rid", "mode", "kind", "cargo", "src", "dst", "line", "budget",
               "stop", "iters", "reason", "ok", "status"}


def _warning(warnings, source, line, code, detail=""):
    warnings.append({"source": str(source), "line": line, "code": code, "detail": detail})


def _fields(raw):
    fields = {}
    for token in raw.split():
        if "=" not in token:
            raise ValueError("token_without_equal:" + token)
        key, value = token.split("=", 1)
        if not FIELD_NAME.fullmatch(key) or not value:
            raise ValueError("invalid_field:" + token)
        if key in fields:
            raise ValueError("duplicate_field:" + key)
        fields[key] = value
    return fields


def _integer(value, *, signed=False, allow_zero=True):
    if not re.fullmatch(r"-?\d+" if signed else r"\d+", value):
        raise ValueError("invalid_integer:" + str(value))
    number = int(value)
    if not allow_zero and number == 0:
        raise ValueError("zero_not_allowed")
    return number


def _plan_signatures(raw):
    """Decompose les plans sans confondre leurs cinq attributs avec des tuiles OD."""
    if raw == "-":
        return []
    parsed = []
    for item in raw.split(","):
        parts = item.split(":")
        if len(parts) != 5:
            raise ValueError("plan_signature_not_five_fields")
        parsed.append(dict(zip(("lead", "exit", "free", "water", "rail"),
                               (_integer(p, signed=True) for p in parts))))
    return parsed


def _parse_event(line, source, line_no, warnings):
    if "RAIL_PREASTAR" not in line:
        return None
    match = EVENT.search(line.rstrip("\r\n"))
    if match is None:
        _warning(warnings, source, line_no, "invalid_event_header")
        return {"tag": "INVALID", "key": None}
    phase = match["tag"].rsplit("_", 1)[-1]
    try:
        event_date = date(*map(int, match["day"].split("-"))).isoformat()
    except ValueError:
        event_date = None
    try:
        fields = _fields(match["fields"])
    except ValueError as exc:
        _warning(warnings, source, line_no, "invalid_event_fields", str(exc))
        # Si RID est unique et intact, son message invalide contamine sa
        # recherche ; sinon aucun rapprochement n'est possible.
        ids = re.findall(r"(?:^|\s)rid=([^\s]+)", match["fields"])
        key = ids[0] if len(ids) == 1 and ids[0] != "-" else None
        return {"tag": phase, "key": key, "date": event_date, "fields": {},
                "valid": False, "source": str(source), "line": line_no}
    problems = []
    if event_date is None:
        problems.append("invalid_date")
    rid = fields.get("rid")
    if rid is None or rid == "-":
        problems.append("missing_or_invalid_rid")
    key = rid if rid and rid != "-" else None
    required = (START_REQUIRED if phase == "START" else
                ("stop", "iters", "budget") if phase == "END" else
                FRONTIER_REQUIRED if phase == "FRONTIER" else
                ("reason", "ok", "status"))
    missing = [name for name in required if name not in fields]
    if missing:
        problems.append("missing_fields:" + ",".join(missing))
    if phase == "START" and fields.get("mode") not in MODES:
        problems.append("invalid_mode:" + str(fields.get("mode")))
    for name in INTEGER_FIELDS & fields.keys():
        try:
            _integer(fields[name], signed=name in SIGNED_FIELDS,
                     allow_zero=name != "budget")
        except ValueError:
            problems.append("invalid_integer:" + name)
    if phase == "START" and fields.get("kind") not in {"pax", "freight", "-"}:
        problems.append("invalid_kind")
    if phase == "START" and fields.get("cargo") in ("", None):
        problems.append("invalid_cargo")
    if phase == "START":
        for name in ("aps", "bps"):
            if name in fields:
                try:
                    _plan_signatures(fields[name])
                except ValueError:
                    problems.append("invalid_plan_signatures:" + name)
    if phase == "END" and fields.get("stop") not in STOPS:
        problems.append("invalid_stop:" + str(fields.get("stop")))
    if phase == "END" and any(field in fields for field in END_SEGMENTED):
        missing_summary = [field for field in END_SEGMENTED if field not in fields]
        if missing_summary:
            problems.append("partial_segmented_summary:" + ",".join(missing_summary))
    if phase == "FRONTIER" and all(name in fields for name in FRONTIER_REQUIRED):
        try:
            segment, opened, sampled, viable = (int(fields[name]) for name in
                                                 ("segment", "open", "sampled", "viable"))
            if segment <= 0 or not (0 <= viable <= sampled <= opened):
                problems.append("invalid_frontier_counts")
        except ValueError:
            problems.append("invalid_frontier_counts")
    if phase == "BUILD" and fields.get("ok") not in {"0", "1"}:
        problems.append("invalid_build_ok")
    if phase == "BUILD" and fields.get("reason") in ("", "-", None):
        problems.append("invalid_build_reason")
    if phase == "BUILD" and fields.get("status") in ("", "-", None):
        problems.append("invalid_build_status")
    if phase == "BUILD" and fields.get("status") not in BUILD_STATUSES:
        problems.append("unknown_build_status")
    if problems:
        _warning(warnings, source, line_no, "invalid_event", ";".join(problems))
    return {"tag": phase, "date": event_date, "fields": fields, "key": key,
            "valid": not problems, "source": str(source), "line": line_no}


def _parse_run(path):
    match = LOG_NAME.fullmatch(path.name)
    if match is None:
        return None
    return {"arm": match["arm"], "seed": int(match["seed"]),
            "repeat": int(match["repeat"]), "file": str(path)}


def parse_lines(lines, *, source="reference_seed42_r0.log"):
    """Rapport d'une seule partie. Les evenements malformes ne sont pas inventes."""
    warnings = []
    run = _parse_run(Path(source))
    if run is None:
        _warning(warnings, source, 0, "invalid_log_name")
        return {"run": None, "attempts": [], "warnings": warnings, "duplicates": 0,
                "unidentified_events": 0}
    groups = defaultdict(lambda: {"START": [], "END": [], "BUILD": [], "FRONTIER": []})
    unidentified = 0
    for line_no, line in enumerate(lines, 1):
        event = _parse_event(line, source, line_no, warnings)
        if event is None:
            continue
        if event["key"] is None:
            unidentified += 1
            continue
        groups[event["key"]][event["tag"]].append(event)

    attempts = []
    duplicates = 0
    for rid, phases in sorted(groups.items()):
        chosen = {}
        issues = []
        build_events = []
        frontier_events = []
        for phase in ("START", "END", "BUILD", "FRONTIER"):
            events = phases[phase]
            if not events:
                continue
            unique = {}
            for event in events:
                signature = (event["date"], tuple(sorted(event["fields"].items())))
                unique.setdefault(signature, event)
            duplicates += len(events) - len(unique)
            if phase == "FRONTIER":
                frontier_events = sorted(unique.values(), key=lambda e: e["line"])
                if any(not event["valid"] for event in frontier_events):
                    issues.append("invalid_frontier")
                cutoffs = [event["fields"].get("segment") for event in frontier_events]
                if len(set(cutoffs)) != len(cutoffs):
                    issues.append("conflicting_frontier_segment")
                    _warning(warnings, source, events[0]["line"],
                             "conflicting_frontier_segment", f"rid={rid}")
                continue
            if phase == "BUILD":
                build_events = sorted(unique.values(), key=lambda e: e["line"])
                if any(not event["valid"] for event in build_events):
                    issues.append("invalid_build")
                terminals = [event for event in build_events
                             if event["fields"].get("status") in TERMINAL_BUILD_STATUSES]
                if len(terminals) > 1:
                    issues.append("conflicting_build_terminal")
                    _warning(warnings, source, events[0]["line"], "conflicting_build_terminal",
                             f"rid={rid} count={len(terminals)}")
                if terminals and build_events[-1] is not terminals[-1]:
                    issues.append("build_after_terminal")
                    _warning(warnings, source, events[-1]["line"], "build_after_terminal", f"rid={rid}")
                chosen[phase] = build_events[-1]
                continue
            if len(unique) != 1:
                issues.append("conflicting_" + phase.lower())
                _warning(warnings, source, events[0]["line"], "conflicting_" + phase.lower(),
                         f"rid={rid} occurrences={len(unique)}")
            chosen[phase] = next(iter(unique.values()))
            if any(not event["valid"] for event in unique.values()):
                issues.append("invalid_" + phase.lower())
        if "START" not in chosen:
            issues.append("missing_start")
            _warning(warnings, source, 0, "missing_start", f"rid={rid}")
        if "END" not in chosen:
            issues.append("missing_end")
            _warning(warnings, source, 0, "missing_end", f"rid={rid}")
        start = chosen.get("START")
        end = chosen.get("END")
        build = chosen.get("BUILD")
        if start and end and start["fields"].get("budget") != end["fields"].get("budget"):
            issues.append("budget_mismatch")
            _warning(warnings, source, end["line"], "budget_mismatch", f"rid={rid}")
        if start and end and end["date"] and start["date"] and end["date"] < start["date"]:
            issues.append("end_precedes_start")
            _warning(warnings, source, end["line"], "end_precedes_start", f"rid={rid}")
        if build_events and end and build_events[0]["date"] and end["date"] and build_events[0]["date"] < end["date"]:
            issues.append("build_precedes_end")
            _warning(warnings, source, build_events[0]["line"], "build_precedes_end", f"rid={rid}")
        if frontier_events and start and end and start["date"] and end["date"] and any(
                ev["date"] is None or ev["date"] < start["date"] or ev["date"] > end["date"]
                for ev in frontier_events):
            issues.append("frontier_outside_search")
            _warning(warnings, source, frontier_events[0]["line"],
                     "frontier_outside_search", f"rid={rid}")

        status = "paired" if not issues else "censored" if set(issues) <= {"missing_start", "missing_end"} else "non_pairable"
        values = start["fields"] if start else {}
        completion = end["fields"] if end else {}
        build_values = build["fields"] if build else {}
        mode = values.get("mode", "unknown")
        budget = int(values["budget"]) if status == "paired" else None
        iters = int(completion["iters"]) if status == "paired" else None
        stop = completion.get("stop") if status == "paired" else None
        search_class = ("cap_abnd" if stop == "ABND" and iters == budget
                        else "other_abnd" if stop == "ABND" else "ok" if stop == "OK"
                        else "censored" if stop in {"TIMEOUT", "SUPERSEDE", "CANCEL"}
                        else stop.lower() if stop else "unknown")
        if status != "paired":
            search_class = "unknown"
        attempt = {**run, "mode": mode, "rid": rid, "status": status,
                   "issues": sorted(set(issues)), "start_date": start["date"] if start else None,
                   "end_date": end["date"] if end else None,
                   "build_date": build["date"] if build else None,
                   "kind": values.get("kind"), "cargo": values.get("cargo"),
                   "src": int(values["src"]) if status == "paired" else None,
                   "dst": int(values["dst"]) if status == "paired" else None,
                   "line": int(values["line"]) if status == "paired" else None,
                   "budget": budget, "na": int(values["na"]) if status == "paired" else None,
                   "nb": int(values["nb"]) if status == "paired" else None,
                   "plans": {"A": _plan_signatures(values["aps"]),
                             "B": _plan_signatures(values["bps"])} if status == "paired" else None,
                   "features": {k: v for k, v in values.items() if k not in CORE_FIELDS},
                   "stop": stop, "iters": iters, "search_class": search_class,
                   "segmented": ({name: int(completion[name]) for name in END_SEGMENTED}
                                 if status == "paired" and all(name in completion for name in END_SEGMENTED)
                                 else None),
                   "frontier_history": [
                       {"date": ev["date"], **{name: int(ev["fields"][name])
                         for name in FRONTIER_REQUIRED}}
                       for ev in frontier_events if ev["valid"]
                   ],
                   "build_history": [{"date": ev["date"], "reason": ev["fields"].get("reason"),
                                      "ok": int(ev["fields"]["ok"]) if ev["valid"] else None,
                                      "status": ev["fields"].get("status")}
                                     for ev in build_events],
                   "build_reason": build_values.get("reason") if status == "paired" else None,
                   "build_status": build_values.get("status") if status == "paired" else None,
                   "build_ok": int(build_values["ok"]) if status == "paired" and "ok" in build_values else None}
        attempts.append(attempt)
    return {"run": run, "attempts": attempts, "warnings": warnings,
            "duplicates": duplicates, "unidentified_events": unidentified}


def parse_threshold(text):
    match = THRESHOLD.fullmatch(text)
    if match is None:
        raise ValueError("Seuil invalide : " + text + " (exemple rough>=10)")
    return match["field"], match["op"], float(match["value"])


def _rejects(value, op, limit):
    return {">=": lambda: value >= limit, "<=": lambda: value <= limit,
            ">": lambda: value > limit, "<": lambda: value < limit,
            "==": lambda: value == limit}[op]()


def evaluate_threshold(attempts, expression, *, target="cap10000"):
    """Positif=ABND ayant atteint le plafond, negatif=A* OK.

    Le comparateur `cap10000` prend UNIQUEMENT des budgets 10000.
    Un A* OK dont le chantier echoue reste un faux positif du prefiltre.
    """
    if target not in {"cap10000", "cap_any"}:
        raise ValueError("target inconnu: " + str(target))
    field, op, limit = parse_threshold(expression)
    counts = Counter()
    by_mode = defaultdict(Counter)
    by_arm = defaultdict(Counter)
    false_positives = []
    for attempt in attempts:
        if attempt["status"] != "paired":
            counts["excluded_unpaired"] += 1
            continue
        if target == "cap10000" and attempt["budget"] != 10000:
            counts["excluded_other_budget"] += 1
            continue
        if attempt["search_class"] not in {"cap_abnd", "ok"}:
            counts["excluded_other_outcome"] += 1
            continue
        raw = attempt.get(field)
        if raw is None:
            raw = attempt["features"].get(field)
        try:
            numeric = float(raw) if raw is not None else None
            if numeric is None or not (float("-inf") < numeric < float("inf")):
                raise ValueError("missing/nonfinite")
        except (TypeError, ValueError):
            counts["excluded_missing_feature"] += 1
            continue
        predicted = _rejects(numeric, op, limit)
        positive = attempt["search_class"] == "cap_abnd"
        category = "tp" if predicted and positive else "fp" if predicted else "fn" if positive else "tn"
        counts[category] += 1
        by_mode[attempt["mode"]][category] += 1
        by_arm[attempt["arm"]][category] += 1
        if category == "fp":
            false_positives.append({key: attempt[key] for key in
                                    ("arm", "seed", "repeat", "mode", "rid", "start_date",
                                     "kind", "cargo", "src", "dst", "build_reason", "build_status", "build_ok")})
            is_built = attempt["build_status"] == "built" and attempt["build_ok"] == 1
            is_failure = attempt["build_status"] in {"failed", "expired", "dropped"}
            counts["fp_build_ok"] += int(is_built)
            counts["fp_build_failed"] += int(is_failure)
            counts["fp_build_unknown"] += int(not is_built and not is_failure)
    tp, fp, fn, tn = (counts[k] for k in ("tp", "fp", "fn", "tn"))
    return {"expression": expression, "target": target, "positive": "A* ABND at budget",
            "negative": "A* OK (regardless of build outcome)",
            "counts": {k: counts[k] for k in ("tp", "fp", "fn", "tn", "fp_build_ok",
                                                "fp_build_failed", "fp_build_unknown", "excluded_unpaired",
                                                "excluded_other_budget", "excluded_other_outcome",
                                                "excluded_missing_feature")},
            "recall": tp / (tp + fn) if tp + fn else None,
            "false_positive_rate": fp / (fp + tn) if fp + tn else None,
            "precision": tp / (tp + fp) if tp + fp else None,
            "by_mode": {k: {c: v[c] for c in ("tp", "fp", "fn", "tn")}
                        for k, v in sorted(by_mode.items())},
            "by_arm": {k: {c: v[c] for c in ("tp", "fp", "fn", "tn")}
                       for k, v in sorted(by_arm.items())},
            "false_positives": false_positives}


def analyse(path, *, thresholds=(), target="cap10000"):
    """Lit un repertoire de logs de campagne ou un log individuel."""
    root = Path(path)
    files = [root] if root.is_file() else sorted(root.glob("*.log"))
    if not root.exists():
        raise FileNotFoundError(root)
    runs, warnings = [], []
    for file in files:
        with file.open(encoding="utf-8", errors="replace") as handle:
            row = parse_lines(handle, source=str(file))
        runs.append(row)
        warnings.extend(row["warnings"])
    attempts = [item for run in runs for item in run["attempts"]]
    classes = Counter(item["search_class"] for item in attempts)
    statuses = Counter(item["status"] for item in attempts)
    by_mode = defaultdict(Counter)
    by_arm = defaultdict(Counter)
    by_year = defaultdict(Counter)
    for item in attempts:
        by_mode[item["mode"]][item["search_class"]] += 1
        by_arm[item["arm"]][item["search_class"]] += 1
        if item["start_date"]:
            by_year[item["start_date"][:4]][item["search_class"]] += 1
    return {"schema_version": 1,
            "scope": "passive traced paths only; absence of log is not absence of search",
            "source": str(root), "logs_seen": len(files),
            "summary": {"unique_rids": len(attempts), "classes": dict(classes),
                        "statuses": dict(statuses), "duplicates": sum(r["duplicates"] for r in runs),
                        "unidentified_events": sum(r["unidentified_events"] for r in runs),
                        "warnings": len(warnings),
                        "by_mode": {k: dict(v) for k, v in sorted(by_mode.items())},
                        "by_arm": {k: dict(v) for k, v in sorted(by_arm.items())},
                        "by_start_year": {k: dict(v) for k, v in sorted(by_year.items())}},
            "attempts": attempts, "warnings": warnings,
            "thresholds": [evaluate_threshold(attempts, expression, target=target)
                           for expression in thresholds]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs", type=Path, help="Dossier contenant *_seedN_rR.log ou log individuel")
    parser.add_argument("--out", type=Path, help="JSON de sortie (sinon stdout)")
    parser.add_argument("--threshold", action="append", default=[],
                        help="Predicat qui rejetterait une recherche, p.ex. rough>=10")
    parser.add_argument("--target", choices=("cap10000", "cap_any"), default="cap10000")
    args = parser.parse_args(argv)
    report = analyse(args.logs, thresholds=args.threshold, target=args.target)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
