"""Audit hors ligne de latence. Aucun import de lanceur, aucune simulation.

Les distributions sont par flux/compagnie/session, jamais entre bras ou reloads.
Les opcodes sont les mesures conventionnelles Opex, PAS des instructions CPU.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import statistics

from analyse_sched_idle import _percentile, parse_fields, parse_sched_idle_output
from analyse_p5_preplan import parse_p5_output
from analyse_v86_cannibalisation import parse_c56_log_line, to_int

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "results" / "parallel_latency_audit"
ENVELOPE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) (\w+)\s*(.*)$")
OWNER = re.compile(r"\[script:\d+\]\s*\[(\d+)\]")
CATEGORIES = ("calcul_synchrone", "attente_financiere", "recherche_en_cours",
              "candidat_caduc", "cause_inconnue")
MEASURES = ("days", "ticks", "ops_proxy", "legacy_days_tick74")


def nonnegative(value):
    value = to_int(value)
    return value if value is not None and value >= 0 else None


def distribution(values):
    values = list(values)
    valid = sorted(v for v in values if v is not None)
    return {"eligible": len(values), "n": len(valid), "missing": len(values) - len(valid),
            "median": statistics.median(valid) if valid else None,
            "p95": _percentile(valid, .95), "max": max(valid) if valid else None}


def classify(fields):
    """Motif observé seulement : ne donne pas une durée causale au refus."""
    reasons = {fields.get(k) for k in ("phase", "r", "reason", "cause", "stop")}
    if reasons & {"refused_cash", "cash", "all_unaffordable"}:
        return "attente_financiere"
    if reasons & {"rail_search", "projects_rail_search_pending", "search_pending", "search_in_progress"}:
        return "recherche_en_cours"
    if reasons & {"batch_plan_dead", "projects_invalidated", "stale", "plan_dead"}:
        return "candidat_caduc"
    return "cause_inconnue"


def parse_log(text, source):
    events, issues = [], []
    sessions = defaultdict(int)
    last_date = {}
    for line_number, raw in enumerate(text.splitlines(), 1):
        match = ENVELOPE.search(raw)
        if not match:
            continue
        y, m, d, tag, rest = match.groups()
        try:
            stamp = date(int(y), int(m), int(d))
        except ValueError:
            issues.append({"line": line_number, "reason": "invalid_date", "raw": raw})
            continue
        owner_match = OWNER.search(raw)
        owner = owner_match.group(1) if owner_match else None
        if tag == "LOAD_RECONCILE" or (owner in last_date and stamp < last_date[owner]):
            sessions[owner] += 1
        last_date[owner] = stamp
        fields = parse_fields(rest)
        kind = tag
        if tag == "C56_TASK":
            parsed = parse_c56_log_line(raw)
            if parsed is None:
                issues.append({"line": line_number, "reason": "invalid_c56", "raw": raw})
                continue
            kind, fields = parsed["kind"], parsed["fields"]
        elif tag == "SCHED_IDLE":
            # Réutiliser le collecteur, mais masquer ses défauts zéro/-1 si absents.
            parsed = parse_sched_idle_output(raw)["events"][0]
            fields = {k: parsed.get(k, v) if to_int(v) is not None else v
                      for k, v in fields.items()}
        events.append({"source": source, "line": line_number, "company": owner,
                       "session": sessions[owner], "date": stamp.isoformat(),
                       "tag": tag, "kind": kind, "fields": fields, "raw": raw})
    return events, issues


def reference(event):
    return {k: event[k] for k in ("source", "line", "company", "session", "date", "kind")}


def difference(a, b):
    return b - a if a is not None and b is not None and b >= a else None


def interval(start, end, metric, category="cause_inconnue"):
    days = (date.fromisoformat(end["date"]) - date.fromisoformat(start["date"])).days
    return {"metric": metric, "category": category, "start": reference(start),
            "end": reference(end), "days": days if days >= 0 else None,
            "ticks": difference(nonnegative(start["fields"].get("tick")),
                                nonnegative(end["fields"].get("tick"))),
            "ops_proxy": None, "boundary": "paired_markers"}


def audit_stream(events):
    """Un flux = une source, compagnie et session. Pas d'imputation des silences."""
    intervals, observations, issues = [], [], []
    pending = {}
    previous = {}
    chosen = {}
    p2 = {}
    counts = Counter(e["kind"] for e in events)

    def observed(event, metric, category="cause_inconnue", **measures):
        rec = {"metric": metric, "category": category, "start": None,
               "end": reference(event), "days": None, "ticks": None,
               "ops_proxy": None, "boundary": "reported_measure", **measures}
        intervals.append(rec)

    def consecutive(event, metric):
        if metric in previous:
            intervals.append(interval(previous[metric], event, metric))
        previous[metric] = event

    for event in events:
        f, kind, tag = event["fields"], event["kind"], event["tag"]
        if tag == "C56_TASK" and re.fullmatch(r"(TASK|STAGE|INTENT|WORKER)_(ENTER|EXIT)", kind):
            family, edge = kind.split("_")
            key = (family, f.get("name"), f.get("cycle"))
            if f.get("name") is None or f.get("cycle") is None:
                issues.append({"event": reference(event), "reason": "missing_pair_key"})
            elif edge == "ENTER":
                if key in pending:
                    issues.append({"event": reference(event), "reason": "ambiguous_repeated_enter"})
                    pending[key] = None  # Ne pas choisir arbitrairement un début.
                else:
                    pending[key] = event
            else:
                start = pending.pop(key, None)
                if start is None:
                    issues.append({"event": reference(event), "reason": "unmatched_exit"})
                else:
                    category = "cause_inconnue"
                    if family == "STAGE" or (family == "TASK" and f.get("name") == "catalog"):
                        category = "calcul_synchrone"
                    if family == "WORKER" and f.get("name") == "rail_search":
                        category = "recherche_en_cours"
                    rec = interval(start, event, f"c56:{family}:{f.get('name')}", category)
                    # Worker spans include interleavings. Only step_ops measures its own steps.
                    rec["ops_proxy"] = (nonnegative(f.get("step_ops")) if family == "WORKER"
                                        else difference(to_int(start["fields"].get("opsclk")),
                                                        to_int(f.get("opsclk"))))
                    intervals.append(rec)
        if tag == "TASK":
            consecutive(event, "dispatch_gap")  # Not a task's execution duration!
        if tag == "SCHED_IDLE":
            observed(event, f"scheduler:{f.get('t')}:{f.get('r')}",
                     days=nonnegative(f.get("d")), ticks=nonnegative(f.get("tk")),
                     ops_proxy=nonnegative(f.get("op")))
            if f.get("t") == "projects" and nonnegative(f.get("gap_d")) is not None:
                observed(event, "projects_useful_gap", days=nonnegative(f.get("gap_d")),
                         ticks=nonnegative(f.get("gap_tk")))
        if tag == "AIR_PLAN_PERF":
            # air_planning.nut publie days = elapsedTicks / 74, PAS AIDate.
            # En mode sliced, ticks est la vie du scan, pas du calcul continu.
            observed(event, "air_plan_scan", legacy_days_tick74=nonnegative(f.get("days")),
                     ticks=nonnegative(f.get("ticks")), ops_proxy=nonnegative(f.get("total_ops")),
                     attribution="scan_cost_synchronous_or_sliced_context_required")
        if tag == "P5_RAIL_SEARCH":
            parsed = parse_p5_output(event["raw"])["rail_searches"]
            if parsed:
                search = parsed[0]
                slices = nonnegative(f.get("slices"))
                # Le ledger émet aussi des consommations répétées d'un résultat déjà prêt.
                # Les garder distinctes : pas de médiane biaisée par les répétitions zéro.
                scope = "active_slices" if slices is not None and slices > 0 else "no_measured_slices"
                observed(event, f"rail_search:{scope}", "recherche_en_cours",
                         **{unit: nonnegative(search[field]) if nonnegative(f.get(field)) is not None else None
                            for unit, field in (("days", "days"), ("ticks", "ticks"), ("ops_proxy", "ops"))},
                         identity={key: f.get(key) for key in ("id", "kind", "src", "dst", "outcome", "slices")},
                         attribution="elapsed_search_lifetime_includes_interleavings")
            else:
                issues.append({"event": reference(event), "reason": "invalid_search_id"})
        if tag in {"PROJECTS_COST", "CATALOG_COST", "CATALOG_COST_SLICE"}:
            for field, value in f.items():
                if field.endswith("_ops"):
                    observed(event, f"{tag}:{field}", ops_proxy=nonnegative(value))
        if tag == "B6_FRESH_EQ" and f.get("scope") == "all":
            observed(event, "rebuild_reported", "calcul_synchrone", days=nonnegative(f.get("rebuild_days")))
        if f.get("phase") == "c83_poll_summary":
            # Cumul mensuel : surtout PAS une distribution des intervalles de poll.
            observations.append({"event": reference(event), "type": "watcher_cumulative", "fields": f})
        if f.get("phase") == "c83_poll_state" and f.get("initial") == "0":
            observed(event, "watcher_change_detection_window",
                     days=difference(nonnegative(f.get("seen_before")), nonnegative(f.get("detected"))))
        if tag in {"C78_CAND", "C78_AIRPAIR", "PROJECT_CHOSEN", "PROJECT_DISCARD", "C78_BUILD"} or (
                tag == "C50_CHRONO" and f.get("phase") in {"project_built", "refused_cash"}):
            observations.append({"event": reference(event), "type": kind,
                                 "category": classify(f), "fields": f})
        if tag == "C50_CHRONO" and f.get("phase") == "project_built":
            consecutive(event, "construction_gap")
        if tag == "PROJECT_CHOSEN" and f.get("mode") == "air":
            key = (f.get("src"), f.get("dst"))
            if None not in key:
                chosen[key] = event if key not in chosen else None
        if tag == "AIR_BUILD":
            start = chosen.pop((f.get("src"), f.get("dst")), None)
            if start is not None:
                rec = interval(start, event, "chosen_to_air_build")
                rec["identity"] = {k: f.get(k) for k in ("src", "dst", "line")}
                intervals.append(rec)
            else:
                issues.append({"event": reference(event), "reason": "build_without_unique_choice"})
        if tag == "PROJECT_DISCARD":
            chosen.pop((f.get("src"), f.get("dst")), None)
        if tag == "P2_BUILD" and f.get("id") is not None:
            key = f["id"]
            if key in p2:
                issues.append({"event": reference(event), "reason": "duplicate_p2_id"})
                p2[key] = None
            else:
                p2[key] = event
        if tag == "P2_RESOLVE":
            start = p2.pop(f.get("id"), None)
            if start is not None and f.get("ret_reason") != "sim_end":
                rec = interval(start, event, "portfolio_empty_to_nonempty", classify(start["fields"]))
                rec.update(days=nonnegative(f.get("days")), ticks=nonnegative(f.get("ticks")),
                           identity={"episode_id": f.get("id")},
                           attribution="initial_cause_only_not_continuous_wait")
                intervals.append(rec)
            else:
                issues.append({"event": reference(event), "reason": "unresolved_or_censored_p2"})

    for mapping, reason in ((pending, "unclosed_enter"), (chosen, "choice_without_build"),
                            (p2, "unresolved_p2")):
        for key, value in mapping.items():
            issues.append({"key": key, "event": reference(value) if value else None, "reason": reason})
    groups = defaultdict(list)
    for rec in intervals:
        groups[rec["metric"]].append(rec)
    summaries = {metric: {"n_intervals": len(items),
                          **{unit: distribution(r.get(unit) for r in items) for unit in MEASURES},
                          "by_category": {category: {
                              unit: distribution(r.get(unit) for r in items if r["category"] == category)
                              for unit in MEASURES}
                              for category in sorted({r["category"] for r in items})},
                          "max_day_example": max((r for r in items if r["days"] is not None),
                                                 key=lambda r: r["days"], default=None)}
                 for metric, items in sorted(groups.items())}
    ranking = {category: sorted((r for r in intervals if r["category"] == category and r["days"] is not None),
                                key=lambda r: r["days"], reverse=True)[:10] for category in CATEGORIES}
    return {"coverage": {"events": len(events), "markers": dict(counts),
                         "first_date": events[0]["date"] if events else None,
                         "last_date": events[-1]["date"] if events else None,
                         "issues": len(issues)}, "summaries": summaries,
            "largest_intervals_by_category": ranking, "issues": issues,
            "intervals": intervals, "observations": observations}


def audit_text(text, source):
    events, issues = parse_log(text, source)
    groups = defaultdict(list)
    for event in events:
        groups[(event["company"], event["session"])].append(event)
    return {"source": source, "parse_issues": issues, "timeline": events,
            "streams": [{"company": company, "session": session, **audit_stream(items)}
                        for (company, session), items in groups.items()]}


def read_sources(path):
    """Schémas explicites : log brut ou phases Save/Load ; pas de double collecte JSONL."""
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix == ".log":
        return [(str(path), text)], None
    data = json.loads(text)
    streams = []
    for phase in ("phase_a", "phase_b"):
        raw = data.get(phase, {}).get("openttd_output_raw")
        if isinstance(raw, str):
            streams.append((f"{path}#$.{phase}.openttd_output_raw", raw))
    metadata = {k: data.get(k) for k in ("status", "seed", "years_a", "years_b", "starting_year",
                                        "config", "reloaded_savegame", "phantom_company_confound")}
    return streams, metadata


def run(paths, output):
    output = output.resolve()
    if not output.is_relative_to(OUTPUT_ROOT.resolve()):
        raise ValueError("Sortie autorisée seulement sous results/parallel_latency_audit/")
    paths = [p.resolve() for p in paths]
    if len(set(paths)) != len(paths):
        raise ValueError("Source dupliquée")
    if output.exists():
        raise FileExistsError(f"Préserver la sortie existante : {output}")
    payload = {"schema": 1, "scope": "offline_descriptive_not_causal",
               "units": {"days": "game_calendar_days", "ticks": "AIController_ticks_as_logged",
                         "ops_proxy": "Opex_opcode_convention_not_CPU_instructions",
                         "legacy_days_tick74": "AIR_PLAN_PERF_days_ticks_div_74_not_calendar_days"},
               "percentile": "linear_interpolation_(n-1)*p", "sources": [], "analyses": []}
    for path in paths:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        streams, metadata = read_sources(path)
        payload["sources"].append({"path": str(path), "sha256": digest, "metadata": metadata,
                                   "raw_streams": len(streams), "raw_missing": not streams})
        payload["analyses"].extend(audit_text(text, source) for source, text in streams)
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError(f"Source modifiée pendant lecture : {path}")
    for source in payload["sources"]:
        if hashlib.sha256(Path(source["path"]).read_bytes()).hexdigest() != source["sha256"]:
            raise RuntimeError(f"Source modifiée avant publication : {source['path']}")
    output.mkdir(parents=True)
    # Mode exclusif : aucune ancienne preuve écrasée.
    with (output / "audit.json").open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    compact = {k: v for k, v in payload.items() if k != "analyses"}
    compact["analyses"] = [
        {"source": a["source"], "parse_issues": a["parse_issues"],
         "streams": [{k: v for k, v in s.items() if k not in {"intervals", "observations"}}
                     for s in a["streams"]]}
        for a in payload["analyses"]]
    with (output / "summary.json").open("x", encoding="utf-8") as handle:
        json.dump(compact, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return payload


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path, help="Logs bruts ou JSON Save/Load explicites")
    parser.add_argument("--out", required=True, type=Path, help="Nouveau sous-dossier de résultats attribué")
    args = parser.parse_args(argv)
    payload = run(args.inputs, args.out)
    print(f"{len(payload['sources'])} sources, {len(payload['analyses'])} flux ; {args.out / 'audit.json'}")


if __name__ == "__main__":
    main()