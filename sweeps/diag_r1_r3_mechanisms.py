"""R1/R3: preparation and conservative trace reader; no game on import/prepare.

Only `smoke --centralized --sources-stable` runs a game, after parallel edits.
This is natural exposure, NOT a deterministic fixture or an economic A/B.
The exact boundary, world mutation and mid-decision reload fixtures require the
integration hooks specified in docs/r1_r3_mechanisms_20261001.md.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

try:
    from .harness import parse_fields
    from .game_health import SCRIPT_LINE_RE, parse_script_errors
except ImportError:
    from harness import parse_fields
    from game_health import SCRIPT_LINE_RE, parse_script_errors

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "results/r1_r3_mechanisms"
GATE = "const R1_R3_TEST_ONLY = 0;"
ARM = "OpexAI[decision_log=1]"
SCENARIOS = {
    "r1_exact": "Besoin 4, budget reel apres reserve = prix + 1000, achat reel 1.",
    "r1_below": "Meme besoin, budget reel = prix + 999, aucune admission/commande.",
    "r1_stale": "Inventaire reel modifie entre selection et execution; rejet fleet_stale.",
    "r1_repeat": "Reexecution du meme snapshot apres achat; aucun second achat.",
    "r1_reload": "Save/Load au point selection/achat; reconciliation puis aucun double achat.",
    "r3_dead": "A-B construit, A-C caduc naturellement, D-E consomme le bypass et construit.",
    "r3_cash": "Candidat vivant devenu non financable apres A-B; arret cash actuel.",
    "r3_failure": "Refus API reel apres consommation; suivant finance bloque par k_pass.",
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_hashes(root=ROOT):
    """All local AI/runtime helpers, not a claim about downloaded libraries."""
    paths = []
    for folder in ("ai/OpexAI", "ai/AAAHogEx-115", "ai/library", "sweeps"):
        paths.extend(p for p in (root / folder).rglob("*")
                     if p.is_file() and p.suffix in (".nut", ".py"))
    for name in ("requirements.txt", "requirements-ml.txt", "Dockerfile"):
        if (root / name).is_file():
            paths.append(root / name)
    return {p.relative_to(root).as_posix(): sha256(p) for p in sorted(paths)}


def new_directory(path, allowed=OUTPUT_ROOT):
    path, allowed = Path(path).resolve(), Path(allowed).resolve()
    if not path.is_relative_to(allowed) or path == allowed:
        raise ValueError(f"Output must be a new child of {allowed}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.mkdir()  # exclusive, including empty directories; never clean a run
    return path


def write_new(path, payload):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")


def protocol(root=ROOT):
    return {
        "schema": "r1_r3_mechanisms_v1", "date": "2026-10-01",
        "engine_executed": False, "economic_verdict": "not_evaluated",
        "git_sha": None, "source_hashes": source_hashes(root),
        "test_only": True, "source_gate": GATE, "arm": ARM,
        "seed": 42, "starting_year": 1970, "years": 1, "workers": 1,
        "global_cpu_worker_ceiling": 12, "script_debug": 4,
        "runtime": {"openttd": "15.3", "noai": "15", "opengfx": "7.1",
                    "openttdlab": "0.0.75"},
        "policy": "C115 protected; cadence/C84/C85/C121/C122 OFF; no quota/batch/priority change",
        "scenarios": {key: {"criterion": value, "status": "not_executed"}
                      for key, value in SCENARIOS.items()},
        "sequence": ["freeze_sources", "default_compile_smoke_1x1",
                     "test_only_exposure_smoke_1x1", "targeted_world_fixtures",
                     "sequential_exact_checkpoint_save_load", "physical_reconciliation"],
        "integration_required": [
            "real bank-balance/world fixture, not a substituted budget/API return",
            "initial liveness proof for A-B/A-C/D-E, normal final ranking recorded",
            "builder refusal after physical checks via a real world mutation",
            "exact selection/execute checkpoint and post-load identity mapping",
            "company-filtered physical inventories and line/order reconciliation",
        ],
        "save_load": {"harness": "sweeps/save_load_roundtrip.py",
                      "sequential_only": True, "shared_scratch": ".scratch_saveload",
                      "mid_fraction_is_not_mechanism_checkpoint": True,
                      "raw_vehicle_counts_not_accepted": True},
        "stop": "No 5x6/20x10, no retry for favourable economics; non-exposure stays non-exposed",
    }


def integer(fields, name):
    value = fields.get(name)
    return int(value) if isinstance(value, str) and re.fullmatch(r"-?\d+", value) else None


def vehicle_ids(fields):
    value = fields.get("vehicles")
    if value == "none":
        return set() if integer(fields, "inventory") == 0 else None
    if not isinstance(value, str) or not re.fullmatch(r"\d+(,\d+)*", value):
        return None
    ids = value.split(",")
    if len(set(ids)) != len(ids) or len(ids) != integer(fields, "inventory"):
        return None
    return set(ids)


def finding(scenario, status, events, reason):
    return {"scenario": scenario, "trace_status": status, "reason": reason,
            "source_lines": [e["source_line"] for e in events]}


def r1_findings(events):
    """Check observed returns, never simulate the fit/purchase implementation."""
    groups = defaultdict(list)
    for event in events:
        f = event["fields"]
        if f.get("mechanism") == "R1" and f.get("id") not in (None, "unknown"):
            groups[event["company"], f["id"]].append(event)
    found = []
    for group in groups.values():
        fits = [e for e in group if e["fields"].get("phase") == "fit"]
        if len(fits) != 1:
            found.append(finding("r1_exact", "incomplete", group, "ambiguous_fit_identity"))
            continue
        fit = fits[0]["fields"]
        if any(e["fields"].get("line") != fit.get("line")
               for e in group if "line" in e["fields"]):
            found.append(finding("r1_exact", "incomplete", group, "conflicting_line_identity"))
            continue
        original, price, budget = (integer(fit, k) for k in ("original", "price", "budget"))
        reserve, cash = integer(fit, "reserve"), integer(fit, "cash")
        eligible = (original == 4 and price is not None and price > 0
                    and integer(fit, "buffer") == 1000
                    and integer(fit, "scrapping") == 0
                    and integer(fit, "base") is not None
                    and integer(fit, "base") == integer(fit, "have")
                    and reserve is not None and cash is not None and budget == cash - reserve)
        if not eligible:
            continue
        ranks = [e for e in group if e["fields"].get("phase") == "rank"]
        executes = [e for e in group if e["fields"].get("phase") == "execute"]
        results = [e for e in group if e["fields"].get("phase") == "result"]
        apis = [e for e in group if e["fields"].get("phase") == "api_result"]
        if budget == price + 999:
            status = "pass" if integer(fit, "admitted") == 0 and not executes and not apis else "fail"
            found.append(finding("r1_below", status, group, "boundary_fit_only_no_global_inventory_proof"))
        if budget != price + 1000:
            continue
        if integer(fit, "fitted") != 1 or integer(fit, "admitted") != 1:
            found.append(finding("r1_exact", "fail", group, "expected_four_to_one"))
            continue
        if len(ranks) != 1 or integer(ranks[0]["fields"], "rank") is None or integer(ranks[0]["fields"], "rank") < 0:
            found.append(finding("r1_exact", "incomplete", group, "fit_is_not_final_admission"))
            continue
        if not executes or not results:
            found.append(finding("r1_exact", "incomplete", group, "fit_without_purchase_is_not_success"))
            continue
        first, result = executes[0], results[0]
        ef, rf = first["fields"], result["fields"]
        before, after = vehicle_ids(ef), vehicle_ids(rf)
        ordered = (fits[0]["source_line"] < ranks[0]["source_line"] < first["source_line"]
                   < result["source_line"])
        if not ordered or before is None or after is None:
            found.append(finding("r1_exact", "incomplete", group, "missing_or_unordered_inventory"))
            continue
        calls = [e for e in apis if first["source_line"] < e["source_line"] < result["source_line"]]
        if rf.get("reason") == "fleet_stale" and integer(ef, "cached") != integer(ef, "base"):
            status = "pass" if not calls and before == after and integer(rf, "added") == 0 else "fail"
            found.append(finding("r1_stale", status, [first, result], "stale_guard_actual_return"))
        else:
            ok = (len(calls) == 1 and integer(calls[0]["fields"], "added") == 1
                  and rf.get("reason") == "built" and integer(rf, "added") == 1
                  and integer(rf, "replaced") == 0 and before < after and len(after - before) == 1
                  and integer(rf, "cached") == len(after)
                  and integer(ef, "rank") == integer(ranks[0]["fields"], "rank"))
            found.append(finding("r1_exact", "pass" if ok else "fail", group,
                                 "real_helper_return_and_primary_line_inventory"))
        if len(executes) == 2 and len(results) == 2:
            second, second_result = executes[1], results[1]
            sf, sr = second["fields"], second_result["fields"]
            calls2 = [e for e in apis if second["source_line"] < e["source_line"] < second_result["source_line"]]
            ok = (result["source_line"] < second["source_line"] < second_result["source_line"]
                  and rf.get("reason") == "built" and sr.get("reason") == "fleet_stale"
                  and integer(sf, "pass") is not None and integer(ef, "pass") is not None
                  and integer(sf, "pass") > integer(ef, "pass")
                  and not calls2 and integer(sr, "added") == 0 and integer(sr, "replaced") == 0
                  and vehicle_ids(sf) == after == vehicle_ids(sr))
            found.append(finding("r1_repeat", "pass" if ok else "fail", group, "same_snapshot_second_pass"))
        elif len(executes) > 1 or len(results) > 1:
            found.append(finding("r1_repeat", "incomplete", group, "ambiguous_execution_pairing"))
    return found


def r3_findings(events):
    passes = defaultdict(list)
    for event in events:
        f = event["fields"]
        if f.get("mechanism") == "R3" and all(integer(f, k) is not None for k in ("pass", "cycle", "rank")):
            passes[event["company"], f["pass"], f["cycle"]].append(event)
    found = []
    for group in passes.values():
        keys = [(e["fields"].get("phase"), e["fields"].get("rank")) for e in group]
        if len(keys) != len(set(keys)):
            found.append(finding("r3_dead", "incomplete", group, "duplicate_pass_or_rank"))
            continue
        for index, event in enumerate(group):
            f = event["fields"]
            before, after = integer(f, "bypass_before"), integer(f, "bypass_after")
            finance, available, threshold = (integer(f, k) for k in ("finance", "available", "threshold"))
            if None in (before, after, finance, available, threshold):
                continue
            prior = group[:index]
            later = group[index + 1:]
            built = [e for e in prior if e["fields"].get("phase") == "result"
                     and e["fields"].get("outcome") == "built"]
            same = lambda e: (e["fields"].get("id"), e["fields"].get("rank")) == (f.get("id"), f.get("rank"))
            if f.get("phase") == "reject" and f.get("reason") == "batch_plan_dead":
                if before != after:
                    found.append(finding("r3_dead", "fail", [event], "dead_candidate_consumed_bypass"))
                    continue
                consumed = [e for e in later if e["fields"].get("phase") == "consume"]
                if not built or not consumed or before != 0 or not threshold <= finance <= available:
                    continue
                first, next_event = built[-1]["fields"], consumed[0]
                nf = next_event["fields"]
                shared = {first.get("src"), first.get("dst")} & {f.get("src"), f.get("dst")}
                independent = not ({nf.get("src"), nf.get("dst")} & {first.get("src"), first.get("dst"), f.get("src"), f.get("dst")})
                outcomes = [e for e in later if e["fields"].get("phase") == "result"
                            and e["fields"].get("id") == nf.get("id")
                            and e["fields"].get("rank") == nf.get("rank")]
                if not shared or None in shared or not independent or len(outcomes) != 1:
                    continue
                out = outcomes[0]["fields"]
                nf_cap, nf_avail, nf_threshold = (integer(nf, k) for k in ("finance", "available", "threshold"))
                if None in (nf_cap, nf_avail, nf_threshold):
                    continue
                ok = (not any(same(e) and e["fields"].get("phase") in ("consume", "attempt") for e in later)
                      and integer(nf, "bypass_before") == 0 and integer(nf, "bypass_after") == 1
                      and nf_threshold <= nf_cap <= nf_avail
                      and next_event["source_line"] < outcomes[0]["source_line"]
                      and out.get("outcome") == "built"
                      and integer(out, "lines_before") is not None
                      and integer(out, "lines_after") == integer(out, "lines_before") + 1)
                found.append(finding("r3_dead", "pass" if ok else "fail", [built[-1], event, next_event, outcomes[0]],
                                     "natural_overlap_continuation_initial_liveness_still_required"))
            if f.get("phase") == "stop" and f.get("reason") == "cash" and built and finance >= threshold and finance > available:
                ok = before == after and not any(e["fields"].get("phase") in ("attempt", "consume") for e in later)
                found.append(finding("r3_cash", "pass" if ok else "fail", [built[-1], event] + later,
                                     "financial_stop_not_builder_failure"))
            if f.get("phase") == "result" and f.get("reason") == "build_failed":
                consumption = [e for e in prior if same(e) and e["fields"].get("phase") == "consume"]
                attempts = [e for e in prior if same(e) and e["fields"].get("phase") == "attempt"]
                stops = [e for e in later if e["fields"].get("phase") == "stop"
                         and e["fields"].get("reason") == "k_pass"]
                error = integer(f, "error")
                if not consumption or not attempts or not stops or error is None or error <= 0:
                    continue
                if f.get("detail") not in ("AFAIL", "BFAIL", "PLANE", "ORDFAIL", "START"):
                    continue
                stop = stops[0]["fields"]
                sf, sa, st = (integer(stop, k) for k in ("finance", "available", "threshold"))
                if None in (sf, sa, st) or not st <= sf <= sa:
                    continue
                cf = consumption[-1]["fields"]
                ok = (before == after == 1 and integer(stop, "bypass_before") == integer(stop, "bypass_after") == 1
                      and integer(cf, "bypass_before") == 0 and integer(cf, "bypass_after") == 1
                      and consumption[-1]["source_line"] < attempts[-1]["source_line"] < event["source_line"]
                      and f.get("outcome") == "rejected"
                      and integer(f, "lines_before") is not None
                      and integer(f, "lines_before") == integer(f, "lines_after")
                      and not any(e["fields"].get("phase") in ("attempt", "consume") for e in later))
                found.append(finding("r3_failure", "pass" if ok else "fail", [consumption[-1], event, stops[0]],
                                     "real_error_no_refund_line_count_only_not_rollback_proof"))
    return found


def analyse_text(text, scope="log", evidence_kind="unverified_log"):
    if evidence_kind not in ("synthetic_fixture", "unverified_log", "engine_log"):
        raise ValueError("Unknown evidence kind")
    events, malformed = [], []
    for number, raw in enumerate(text.splitlines(), 1):
        if "R1R3 " not in raw:
            continue
        match = SCRIPT_LINE_RE.search(raw)
        if not match or not match.group(4).startswith("R1R3 "):
            malformed.append(number)
            continue
        fields = parse_fields(match.group(4)[len("R1R3 "):])
        tokens = match.group(4)[len("R1R3 "):].split()
        keys = [token.partition("=")[0] for token in tokens if "=" in token]
        if (len(keys) != len(set(keys)) or fields.get("test_only") != "1"
            or fields.get("mechanism") not in ("R1", "R3")
            or not fields.get("phase") or fields.get("id") in (None, "unknown")
            or integer(fields, "date") is None or integer(fields, "tick") is None):
            malformed.append(number)
            continue
        events.append({"company": int(match.group(2)), "script": int(match.group(1)),
                       "source_line": number, "fields": fields, "raw": raw})
    errors = parse_script_errors(text)
    findings = r1_findings(events) + r3_findings(events)
    unhealthy = bool(errors["attributed"] or errors["unattributed"] or errors["engine_marker"])
    # No fatal marker is not horizon/collection certification. Never infer a
    # complete engine fixture from a matching trace, including synthetic fixtures.
    summaries = {}
    for scenario in SCENARIOS:
        statuses = [f["trace_status"] for f in findings if f["scenario"] == scenario]
        status = ("fail" if "fail" in statuses else "incomplete" if "incomplete" in statuses
                  else "pass" if "pass" in statuses else "non_expose")
        summaries[scenario] = "invalid" if unhealthy or malformed else status
    return {"scope": scope, "evidence_kind": evidence_kind, "engine_validated": False,
            "economic_verdict": "not_evaluated", "events": events, "findings": findings,
            "trace_summary": summaries, "malformed_lines": malformed, "script_errors": errors,
            "complete_scenario_verdict": "pending_fixture_and_physical_reconciliation",
            "limits": ["No cross-stream/Save-Load identity inference", "Absence is not zero",
                       "Primary vehicles attached to line are not a global ghost-vehicle audit",
                       "No CPU or economic effect is measured", "Trace pass is not engine fixture pass"]}


def analyse_file(path):
    path = Path(path)
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".log":
        streams = [analyse_text(text, "$log")]
    else:
        payload = json.loads(text)
        streams = []
        if isinstance(payload, dict):
            for phase in ("phase_a", "phase_b"):
                value = payload.get(phase)
                raw = value.get("openttd_output_raw") if isinstance(value, dict) else None
                if isinstance(raw, str):
                    streams.append(analyse_text(raw, f"$/{phase}/openttd_output_raw"))
    return {"source": str(path.resolve()), "sha256": sha256(path), "streams": streams,
            "coverage": "supported_streams" if streams else "no_supported_log_stream"}


def stage_ai(directory, root=ROOT):
    """Only copy the AI; never rewrite main/globals/settings, even in the copy."""
    target = directory / "test_only_ai/OpexAI"
    shutil.copytree(root / "ai/OpexAI", target)
    source = target / "projects_selection.nut"
    text = source.read_text(encoding="utf-8")
    if text.count(GATE) != 1:
        raise ValueError("Expected exactly one OFF test gate")
    source.write_text(text.replace(GATE, GATE.replace("= 0", "= 1")), encoding="utf-8")
    return target


def run_smoke(directory):
    """Called only by the explicit centralized CLI, not by unit tests/prepare."""
    # Import existing runtime lazily. No installation, subprocess CLI, setting
    # replacement or wrapper import with a launch side effect during analysis.
    sys.path.insert(0, str(ROOT / "sweeps"))
    import openttdlab
    import bench_v2
    import diag_cadence_duel as shared
    from game_health import assess_game, enable_engine_failure_capture

    plan = protocol()
    resolved = bench_v2.resolved_arm_settings([ARM])[ARM]
    effective = resolved["settings"]["effective"]
    required = {"c115_air_c100_capital_replay": 1, "c84_air_target_fleet": 0,
                "c85_air_equipment_frontier": 0,
                "exp_scheduler_skip_not_due": 0, "exp_air_hub_pair_prefilter": 0,
                "c121_air_economics": 0, "c122_air_regime_priority": 0,
                "c121_catalog_incremental": 0, "c121_catalog_air_first_year": 0,
                "c121_territory_first": 0,
                "r19_fault_inject": 0}
    if any(effective.get(k) != v for k, v in required.items()):
        raise ValueError("Protected defaults changed; refuse runtime")
    if set(resolved["explicit_nondefault"]) - {"decision_log"}:
        raise ValueError("Unexpected intervention")
    target = stage_ai(directory)
    plan.update({"resolved_arm": resolved, "configuration": bench_v2.make_cfg(1970),
                 "ai_copy": str(target), "copied_ai_hashes": {
                     p.relative_to(target).as_posix(): sha256(p) for p in sorted(target.rglob("*")) if p.is_file()},
                 "experiment_kind": "natural_exposure_not_targeted_fixture"})
    write_new(directory / "plan.json", plan)
    params = tuple(resolved["explicit_nondefault"].items())
    ai = openttdlab.local_folder(str(target), "OpexAI", params)
    opponent = bench_v2.build_arms(["AAAHogEx"])["AAAHogEx"]
    original_check = openttdlab.subprocess.check_output
    try:
        bench_v2.enable_savegame_cleanup()
        shared.enable_script_debug()
        enable_engine_failure_capture()
        rows = list(openttdlab.run_experiments(
            openttd_version=bench_v2.OPENTTD_VERSION, opengfx_version=bench_v2.OPENGFX_VERSION,
            max_workers=1, result_processor=shared.collect,
            experiments=[{"arm": "test_only", "seed": 42, "years": 1,
                          "days": (date(1971, 1, 1) - date(1970, 1, 1)).days + 32,
                          "openttd_config": plan["configuration"], "ais": (ai, opponent),
                          "log_path": str(directory / "engine.log"),
                          "checkpoint_path": str(directory / "checkpoints.jsonl")}],
            ai_libraries=(openttdlab.bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                          openttdlab.bananas_ai_library("5046524c", "Pathfinder.Rail"))))
    finally:
        openttdlab.subprocess.check_output = original_check
    log_path = directory / "engine.log"
    text = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    health = assess_game([rec for row in rows for rec in row["records"]],
                         starting_year=1970, years=1, engine_log=text, engine_log_path=str(log_path))
    hashes_after = source_hashes()
    unchanged = plan["source_hashes"] == hashes_after
    copy_unchanged = plan["copied_ai_hashes"] == {
        p.relative_to(target).as_posix(): sha256(p) for p in sorted(target.rglob("*")) if p.is_file()}
    report = {"engine_executed": True, "health": health, "sources_unchanged": unchanged,
              "copied_ai_unchanged": copy_unchanged,
              "source_hashes_after": hashes_after,
              "log_sha256": sha256(log_path) if log_path.exists() else None,
              "trace": analyse_text(text, "engine.log", "engine_log"),
              "economic_verdict": "not_evaluated", "targeted_fixtures_executed": False}
    write_new(directory / "report.json", report)
    if not (health["game_ok"] and unchanged and copy_unchanged):
        raise RuntimeError("Unhealthy/truncated game or source drift; retain artifacts, do not qualify")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "analyse", "smoke"))
    parser.add_argument("--out", required=True, type=Path, help="New run directory under results/r1_r3_mechanisms")
    parser.add_argument("--input", type=Path, nargs="+")
    parser.add_argument("--centralized", action="store_true")
    parser.add_argument("--sources-stable", action="store_true")
    args = parser.parse_args(argv)
    if args.action == "smoke" and not (args.centralized and args.sources_stable):
        parser.error("No game during parallel edits: centralized stable-source confirmation required")
    if args.action == "analyse" and not args.input:
        parser.error("analyse requires explicit inputs")
    directory = new_directory(args.out)
    if args.action == "prepare":
        write_new(directory / "plan.json", protocol())
    elif args.action == "analyse":
        write_new(directory / "analysis.json", [analyse_file(p) for p in args.input])
    else:
        run_smoke(directory)
    print(str(directory))


if __name__ == "__main__":
    main()