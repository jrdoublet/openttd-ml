"""R3: offline evidence audit, not a planner, game launcher or causal A/B.

Only the output directory assigned to this audit can be written, exclusively.
Raw line counts are not event totals. PROJECT_DISCARD can be emitted late.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import re

from analyse_v86_cannibalisation import parse_kv_fields, to_int
from game_health import SCRIPT_LINE_RE, parse_script_errors

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "results" / "parallel_bypass_audit"
ENVELOPE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")
TAGS = {"C78_SLOT", "PROJECT_DISCARD", "AIR_BUILD", "C78_BUILD", "MONTHLY_FUNNEL"}
SLOT_PHASES = {"projects_pass", "projects_exit", "air_attempt", "air_outcome", "pass_stop"}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def parse_log(text, source):
    """Preserve publication order/date, owner and pass occurrence, never infer owner 0."""
    events, issues, active, serial = [], [], {}, Counter()
    for line_number, raw in enumerate(text.splitlines(), 1):
        owner = SCRIPT_LINE_RE.search(raw)
        company = int(owner.group(2)) if owner else None
        script = int(owner.group(1)) if owner else None
        match = ENVELOPE.search(raw)
        stamp = None
        if match:
            y, m, d, tag, rest = match.groups()
            try:
                stamp = date(int(y), int(m), int(d)).isoformat()
            except ValueError:
                issues.append({"line": line_number, "reason": "invalid_date"})
                active.pop(company, None)
                continue
            if tag == "LOAD_RECONCILE":
                active.pop(company, None)
                continue
            if tag not in TAGS:
                continue
        elif "C75_BYPASS " in raw:
            tag, rest = "C75_BYPASS", raw.split("C75_BYPASS ", 1)[1]
        else:
            continue
        fields = parse_kv_fields(rest)
        phase = fields.get("phase")
        if tag == "C78_SLOT" and phase not in SLOT_PHASES:
            continue  # catalog inventory is NOT a candidate examined by the build loop
        if tag == "C78_SLOT" and phase == "projects_pass":
            serial[company] += 1
            active[company] = (serial[company], fields.get("pass"), fields.get("cycle"))
        context = active.get(company)
        if tag == "C78_SLOT" and context and (
            fields.get("pass"), fields.get("cycle")
        ) != context[1:]:
            issues.append({"line": line_number, "reason": "pass_context_mismatch"})
            active.pop(company, None)
            context = None
        event = {"source": source, "line": line_number, "company": company,
                 "script": script, "date": stamp, "tag": tag, "fields": fields,
                 "pass_instance": context[0] if context else None,
                 "pass": context[1] if context else fields.get("pass"),
                 "cycle": context[2] if context else fields.get("cycle"), "raw": raw}
        events.append(event)
        if tag == "C78_SLOT" and phase == "projects_exit":
            active.pop(company, None)
    return events, issues


def candidate_key(event):
    f = event["fields"]
    values = tuple(to_int(f.get(k)) for k in ("rank", "src", "dst"))
    return values if all(v is not None and v >= 0 for v in values) else None


def analyse_pass(events):
    """Correlate explicit attempts/outcomes. No counterfactual construction is counted."""
    attempts, outcomes, rejects, successes = [], [], [], []
    for e in events:
        f = e["fields"]
        if e["tag"] == "C78_SLOT" and f.get("phase") == "air_attempt":
            attempts.append(e)
        elif e["tag"] == "C78_SLOT" and f.get("phase") == "air_outcome":
            outcomes.append(e)
        elif e["tag"] == "PROJECT_DISCARD" and f.get("mode") == "air":
            rejects.append(e)
        elif e["tag"] == "AIR_BUILD":
            successes.append(e)
    bypasses = [e for e in events if e["tag"] == "C75_BYPASS"
                and e["fields"].get("phase") == "consumed"]
    candidates = []
    keys = {candidate_key(e) for e in attempts + outcomes + rejects} - {None}
    for key in sorted(keys):
        a = [e for e in attempts if candidate_key(e) == key]
        o = [e for e in outcomes if candidate_key(e) == key]
        r = [e for e in rejects if candidate_key(e) == key]
        # Bypass has no candidate identity: require a unique next AIR attempt,
        # same finance and built_before, no intervening attempt (even a repeat).
        matched = []
        if len(a) == 1:
            for b in bypasses:
                following = [x for x in attempts if x["line"] > b["line"]]
                bf, af = b["fields"], a[0]["fields"]
                if (following and following[0] is a[0] and bf.get("mode") == "air"
                        and to_int(bf.get("capital")) is not None
                        and to_int(bf.get("built_before")) is not None
                        and to_int(bf.get("capital")) == to_int(af.get("finance"))
                        and to_int(bf.get("built_before")) == to_int(af.get("built_before"))):
                    matched.append(b)
        ordered = len(a) == len(o) == 1 and a[0]["line"] < o[0]["line"]
        corroboration = []
        if ordered and o[0]["fields"].get("outcome") == "built":
            corroboration = [s for s in successes
                             if a[0]["line"] < s["line"] < o[0]["line"]
                             and (to_int(s["fields"].get("src")),
                                  to_int(s["fields"].get("dst"))) == key[1:]]
        candidates.append({
            "rank": key[0], "src_tile": key[1], "dst_tile": key[2],
            "examined": True, "examined_basis": "executor_or_discard_trace",
            "executor_attempted": True if a else None,
            "physical_builder_attempted": True if corroboration or any(
                x["fields"].get("reason") == "build_failed" for x in o + r) else None,
            "rejected": True if r or any(x["fields"].get("outcome") == "rejected" for x in o) else None,
            "reasons": sorted({x["fields"].get("reason") for x in o + r
                               if x["fields"].get("reason")}),
            "construction_succeeded": (o[0]["fields"].get("outcome") == "built") if ordered else None,
            "bypass_consumed": True if len(matched) == 1 else None,
            "bypass_link": "inferred_next_attempt_finance_built_before" if len(matched) == 1 else None,
            "attempt_lines": [x["line"] for x in a], "outcome_lines": [x["line"] for x in o],
            "discard_lines": [x["line"] for x in r],
            "bypass_lines": [x["line"] for x in matched],
            "air_build_lines": [x["line"] for x in corroboration],
            "ambiguous": len(a) > 1 or len(o) > 1 or len(matched) > 1 or len(corroboration) > 1,
        })
    gate_candidates = []
    for e in events:
        f = e["fields"]
        if (e["tag"] == "C78_SLOT" and f.get("phase") == "pass_stop"
                and f.get("next_mode") == "air"):
            gate_candidates.append({
                "rank": to_int(f.get("next_rank")), "src_tile": None, "dst_tile": None,
                "examined": True, "examined_basis": "finance_gate",
                "executor_attempted": None, "construction_succeeded": None,
                "bypass_consumed": None, "pass_stopped": True, "reason": f.get("reason"),
                "finance_gbp": to_int(f.get("finance")), "available_gbp": to_int(f.get("available")),
                "threshold_gbp": to_int(f.get("threshold")), "line": e["line"],
                "note": "Gate stop, not a builder rejection; price increase itself is not observed."})
    sequences = []
    built = [c for c in candidates if c["construction_succeeded"] and c["air_build_lines"]
             and not c["ambiguous"]]
    for first, following in zip(built, built[1:]):
        dead = [c for c in candidates if first["rank"] < c["rank"] < following["rank"]
                and "batch_plan_dead" in c["reasons"] and not c["attempt_lines"]
                and c["discard_lines"]
                and all(first["outcome_lines"][0] < n < following["outcome_lines"][0]
                        for n in c["discard_lines"])]
        if dead and first["outcome_lines"][0] < following["attempt_lines"][0]:
            sequences.append({"first_rank": first["rank"], "dead_ranks": [c["rank"] for c in dead],
                              "following_rank": following["rank"],
                              "following_bypass_linked": following["bypass_consumed"],
                              "first_build_lines": first["air_build_lines"],
                              "dead_publication_lines": [n for c in dead for n in c["discard_lines"]],
                              "following_build_lines": following["air_build_lines"],
                              "interpretation": "observed_continuation_delayed_rejections",
                              "causal_advancement_proven": False})
    first_event = events[0]
    return {"company": first_event["company"], "pass": first_event["pass"],
            "cycle": first_event["cycle"], "pass_instance": first_event["pass_instance"],
            "complete_boundary": any(e["fields"].get("phase") == "projects_exit" for e in events),
            "candidates": candidates, "gate_candidates": gate_candidates, "sequences": sequences,
            "stops": [e for e in events if e["fields"].get("phase") == "pass_stop"]}


def analyse_text(text, source, evidence_kind="engine_log"):
    events, issues = parse_log(text, source)
    groups = {}
    for e in events:
        if e["company"] is not None and e["pass_instance"] is not None:
            groups.setdefault((e["company"], e["pass_instance"]), []).append(e)
    passes = [analyse_pass(es) for es in groups.values()]
    counts = Counter(e["tag"] for e in events)
    return {"source": source, "evidence_kind": evidence_kind,
            "coverage": {"log_present": True, "lines": len(text.splitlines()),
                         "retained_trace_lines": len(events), "tag_lines": dict(counts),
                         "unattributed_trace_lines": sum(e["company"] is None for e in events),
                         "unscoped_trace_lines": sum(e["pass_instance"] is None for e in events),
                         "candidate_scan_total": None, "bypass_preserved_total": None,
                         "additional_airports": None,
                         "note": "Trace counts only; missing probes and delayed discards prevent exhaustive totals."},
            "script_errors": parse_script_errors(text), "issues": issues,
            "passes": passes, "events": events, "causal_advancement_proven": False}


def read_artifact(path):
    """Explicit Save/Load phases stay separate; no flattening snapshot windows."""
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig")
        if path.suffix.lower() == ".log":
            streams = [(str(path), text)]
        elif path.suffix.lower() == ".json":
            data = json.loads(text)
            streams = []
            if isinstance(data, dict):
                for phase in ("phase_a", "phase_b"):
                    node = data.get(phase)
                    if isinstance(node, dict) and isinstance(node.get("openttd_output_raw"), str):
                        streams.append((f"{path}#{phase}.openttd_output_raw", node["openttd_output_raw"]))
                if isinstance(data.get("openttd_output_raw"), str):
                    streams.append((f"{path}#openttd_output_raw", data["openttd_output_raw"]))
        else:
            streams = []
        return {"path": str(path), "sha256": sha256(raw), "bytes": len(raw),
                "status": "read" if streams else "no_supported_log_stream",
                "streams": [analyse_text(text, name) for name, text in streams]}
    except (OSError, UnicodeError, ValueError) as exc:
        return {"path": str(path), "status": "unreadable", "error": str(exc), "streams": []}


def read_manifest(path):
    """Keep supplied provenance and compare key sources, without importing a launcher."""
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8-sig"))
    hashes = data.get("source_hashes_before", {})
    checked = {}
    for name in ("ai/OpexAI/task_projects.nut", "ai/OpexAI/task_air.nut",
                 "ai/OpexAI/settings.nut", "ai/OpexAI/info.nut"):
        current = sha256((ROOT / name).read_bytes())
        checked[name] = {"current_sha256": current, "recorded_sha256": hashes.get(name),
                         "matches": current == hashes[name] if name in hashes else None}
    return {"path": str(path), "sha256": sha256(raw), "source_checks": checked,
            **{k: data.get(k) for k in ("protocol", "git_sha", "source_frozen", "sources_unchanged",
                                      "docker_image_id", "years", "seeds", "workers", "arms", "complete")},
            "games": [{k: g.get(k) for k in ("arm", "seed", "valid", "date", "log_path", "health")}
                      for g in data.get("games", [])],
            "resolved_arms": data.get("resolved_arms")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--manifest", action="append", default=[], type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    destination = args.out.resolve()
    if not destination.is_relative_to(OUTPUT_ROOT.resolve()):
        parser.error("output must be under results/parallel_bypass_audit/")
    if destination.exists():
        parser.error("refusing to overwrite existing evidence")
    artifacts = [read_artifact(p.resolve()) for p in dict.fromkeys(args.inputs)]
    report = {"schema": "parallel_bypass_audit/1", "mode": "existing_artifacts_only",
              "units": {"capital": "GBP", "finance": "GBP", "k_pass": "GBP",
                        "available": "GBP", "tick": "OpenTTD_tick", "src_dst": "town_tile",
                        "date": "game_calendar_publication_date"},
              "artifacts": artifacts, "manifests": [read_manifest(p.resolve()) for p in args.manifest],
              "causal_advancement_proven": False, "economic_gain_measured": False}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"{len(artifacts)} artifacts analysed -> {destination}")


if __name__ == "__main__":
    main()