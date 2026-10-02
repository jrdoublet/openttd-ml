"""Isolated C121 winner-fusion economic validation using the current C66 harness.

The ordinary default qualifier cannot expose C121 while its economics gate is OFF.
This records a scoped, predeclared opcode-neutral comparison in the C121 profile.
It never changes defaults and retains the ordinary signs20 verdict separately.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
AI_SOURCE = ROOT / "results/c121_winner_integration/20261001_measure_on42_r1/ai/OpexAI"
IMAGE = "sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659"
COMMON = "c121_air_economics=1,catalog_cost_probe=0,"
REFERENCE = "OpexAI[" + COMMON + "c121_air_winner_fusion=0]"
VARIANT = "OpexAI[" + COMMON + "c121_air_winner_fusion=1]"


def intervention_arms(intervention):
    if intervention == "fusion":
        return REFERENCE, VARIANT
    if intervention == "context":
        common = COMMON + "c121_air_winner_fusion=1,"
        return ("OpexAI[" + common + "c121_air_engine_context=0]",
                "OpexAI[" + common + "c121_air_engine_context=1]")
    raise ValueError("Unknown opcode intervention")


def write(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def neutral_gate(report, pairs, adoption=False):
    c = report.get("policy_comparison") or {}
    checks = {
        "healthy": report.get("failed_runs") == [],
        "complete": c.get("comparison_complete") is True,
        "coverage": c.get("metric_coverage_complete") is True,
        "pairs": c.get("complete_pairs") == pairs == c.get("planned_pairs"),
        "adoption_sample": not adoption or c.get("adoption_sample_complete") is True,
    }
    delta = c.get("aggregates", {}).get("profit_year", {}).get("policy_delta", {})
    ci = delta.get("mean_student_t_95pct_ci")
    p = delta.get("sign_test_p")
    wins, losses = delta.get("wins"), delta.get("losses")
    # The exact sign test has no trials for all ties: p=1 by definition here.
    if wins == losses == 0 and delta.get("ties") == pairs:
        p = 1.0
    checks["profit_ci_not_entirely_negative"] = (
        isinstance(ci, list) and len(ci) == 2
        and all(isinstance(x, (int, float)) and math.isfinite(x) for x in ci)
        and ci[1] >= 0
    )
    checks["no_significant_defeat"] = (
        isinstance(p, (int, float)) and math.isfinite(p)
        and (p >= .05 or (isinstance(wins, int) and isinstance(losses, int) and wins > losses))
    )
    checks["value_guard"] = c.get("value_guard_pass") is True
    return {"pass": all(checks.values()), "checks": checks,
            "raw_verdict": c.get("verdict"), "profit_delta": delta,
            "value": c.get("aggregates", {}).get("company_value"), "sign_p": p}


BRIDGE = '''import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "sweeps"))
import campaign_freeze
import bench_1v1_5y_20seeds as bench
import json, hashlib, shutil, inspect
import openttdlab
root = Path(__file__).resolve().parent
groups = json.loads((root / "library_manifest.json").read_text())["libraries"]
cache = Path(inspect.signature(openttdlab.run_experiments).parameters["get_cache_dir"].default())
def freeze_cached(specs, destination):
    if {(s["name"], s["unique_id"]) for s in specs} != {(g["requested_name"], g["requested_unique_id"]) for g in groups}:
        raise ValueError("Cached library requests differ from the current harness")
    destination.mkdir()
    for g in groups:
        for e in g["resolved"]:
            name = e["filename"]
            if Path(name).name != name:
                raise ValueError("Unsafe library filename")
            src = cache / "bananas" / name
            if hashlib.sha256(src.read_bytes()).hexdigest() != e["sha256"]:
                raise ValueError("Cached library fingerprint mismatch")
            shutil.copy2(src, destination / name)
    return tuple(campaign_freeze._frozen_library_descriptor(g["requested_name"], g["resolved"], destination) for g in groups), groups
# Only the pre-game library resolver is adapted. The verified child executes the
# unchanged stock harness and frozen descriptors; no engine/extractor patching.
campaign_freeze.freeze_bananas_libraries = freeze_cached
bench.main()
'''


def prepare(folder, intervention="fusion", ai_source=None, opcode_evidence=None, evaluate_economics=False):
    import bench_1v1_5y_20seeds as bench
    from campaign_freeze import fingerprint_tree
    reference, variant = intervention_arms(intervention)
    if intervention == "context":
        if ai_source is None or opcode_evidence is None:
            raise ValueError("Context requires its measured source and confirmed opcode evidence")
        evidence = json.loads(Path(opcode_evidence).read_text(encoding="utf-8"))
        if evidence.get("pass") is not True or (evidence.get("opcode_gain_confirmed") is not True and not evaluate_economics):
            raise ValueError("Context opcode gain has not passed its evidence gate")
        if evidence.get("ai_fingerprint") != fingerprint_tree(Path(ai_source)):
            raise ValueError("Economic source differs from measured context source")
    folder.mkdir(parents=True, exist_ok=False)
    inputs = folder / "inputs"
    inputs.mkdir()
    shutil.copytree(ai_source or AI_SOURCE, inputs / "ai/OpexAI")
    shutil.copytree(ROOT / "ai/AAAHogEx-115", inputs / "ai/AAAHogEx-115")
    files = set(bench.CAMPAIGN_HARNESS_FILES) | {"sweeps/run_c121_winner_economic_validation.py"}
    for name in files:
        target = inputs / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    shutil.copy2(ROOT / "results/_tmp_smoke_test.manifest.json", inputs / "library_manifest.json")
    (inputs / "run_cached.py").write_text(BRIDGE, encoding="utf-8")
    # The startup receipt is kept in both arms; the expensive catalogue probe is OFF.
    plan = {
        "category": "opcodes", "scope": intervention + " only, C121 experimental profile",
        "intervention": intervention,
        "economic_evaluation_requested": evaluate_economics,
        "opcode_gain_confirmed": evidence.get("opcode_gain_confirmed") if intervention == "context" else True,
        "authorization": "2026-10-02: vérifie le gain en opcode et la neutralité éco" if intervention == "context"
                         else "2026-10-01: lance la validation économique dès que possible",
        "reference": reference, "variant": variant,
        "primary_metric": "profit_year", "value_guard_max_loss_pct": 5,
        "neutrality": "Student CI95 upper >=0; sign p>=.05 OR wins>losses; value guard -5%",
        "raw_signs20_min_delta": 50000,
        "sequence": {"smoke": [1, [42]], "diagnostic": [6, [42, 100, 999, 1234, 5678]],
                     "adoption": [10, list(bench.SEEDS)]},
        "limits": {"cpus": 3, "memory": "2g", "memory_swap": "2g", "workers": 3},
        "image_id": IMAGE, "inputs": fingerprint_tree(inputs),
        "opcode_evidence": str(opcode_evidence) if opcode_evidence else "results/c121_winner_integration/20261001_summary_r2/report.json",
        "limitation": "Does not qualify C121 economics or enable its default; frozen C121 profile",
    }
    write(folder / "plan.json", plan)
    if opcode_evidence:
        shutil.copy2(opcode_evidence, folder / "opcode_evidence.json")
    return inputs, plan


def run(folder, resume=False, local_fast=False, intervention="fusion", ai_source=None, opcode_evidence=None, evaluate_economics=False):
    if local_fast:
        context = subprocess.check_output(["docker", "context", "show"], text=True).strip()
        if context != "desktop-linux":
            raise ValueError("10 CPU/10 workers authorized only on this local desktop context")
    if resume:
        inputs = folder / "inputs"
        plan = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
        if plan.get("intervention", "fusion") != intervention:
            raise ValueError("Cannot resume a different intervention")
    else:
        inputs, plan = prepare(folder, intervention, ai_source, opcode_evidence, evaluate_economics)
    cpus = workers = 10 if local_fast else 3
    if local_fast:
        write(folder / "local_resource_amendment.json", {
            "authorization": "2026-10-02: tu peux utiliser 10 cpu 10 workers sur ce pc",
            "docker_context": "desktop-linux", "cpus": cpus, "workers": workers,
            "memory": "2g", "memory_swap": "2g", "resume": resume,
            "economic_rules_unchanged": True, "completed_stages_not_replayed": True})
    sys.path.insert(0, str(inputs / "sweeps"))
    import run_c66_reference as launcher
    launcher.ROOT = inputs
    # Reuse the host launcher's exact metadata capture and Docker resource limits.
    # Substitute only the entry point that serves already fingerprinted libraries.
    original_run = launcher.subprocess.run
    def launch(command, **kwargs):
        if isinstance(command, list) and command[:2] == ["docker", "run"]:
            command = ["run_cached.py" if x == "sweeps/bench_1v1_5y_20seeds.py" else x for x in command]
        return original_run(command, **kwargs)
    launcher.subprocess.run = launch
    stages = []
    try:
        for stage, (years, seeds) in plan["sequence"].items():
            existing = folder / (stage + "_gate.json")
            if resume and existing.exists():
                completed = json.loads(existing.read_text(encoding="utf-8"))
                if not completed["neutrality"]["pass"]:
                    raise ValueError("Cannot resume past a failed validation gate")
                stages.append(completed)
                print("RETAIN " + stage + ": completed gate, no rerun", flush=True)
                continue
            while subprocess.check_output(["docker", "ps", "-q"], text=True).strip():
                print("WAIT_DOCKER: other container active; no campaign launched", flush=True)
                time.sleep(30)
            name = folder.name + "_" + stage
            print("LAUNCH " + name, flush=True)
            sys.argv = [__file__, "--campaign", name, "--image", IMAGE,
                        "--container-name", name.replace("_", "-"),
                        "--reference", plan["reference"], "--variant", plan["variant"],
                        "--policy-id", intervention + "_off", "--variant-policy-id", intervention + "_on",
                        "--primary-metric", "profit_year", "--min-useful-primary-delta", "50000",
                        "--value-guard-max-loss-pct", "5", "--years", str(years),
                        "--seeds", *map(str, seeds), "--max-workers", str(workers),
                        "--cpus", str(cpus)]
            try:
                launcher.main()
            except SystemExit as error:
                if error.code not in (None, 0):
                    raise
            report = json.loads((inputs / "results" / (name + ".json")).read_text(encoding="utf-8"))
            if stage == "smoke":
                c = report["policy_comparison"]
                verdict = {"pass": report["failed_runs"] == [] and c["comparison_complete"]
                           and c["metric_coverage_complete"] and c["complete_pairs"] == 1,
                           "raw_verdict": c["verdict"], "economic_verdict": "not_evaluated"}
            else:
                verdict = neutral_gate(report, len(seeds), stage == "adoption")
            stages.append({"stage": stage, "report": str(inputs / "results" / (name + ".json")),
                           "neutrality": verdict})
            write(folder / (stage + "_gate.json"), stages[-1])
            print("GATE " + stage + " " + json.dumps(verdict), flush=True)
            if not verdict["pass"]:
                break
        write(folder / "outcome.json", {"stages": stages, "defaults_changed": False,
              "economic_neutrality_pass": len(stages) == 3 and stages[-1]["neutrality"]["pass"],
              "accepted": len(stages) == 3 and stages[-1]["neutrality"]["pass"]
                          and plan.get("opcode_gain_confirmed", True) is True})
    finally:
        launcher.subprocess.run = original_run


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--resume", action="store_true", help="Retain successful completed gates")
    parser.add_argument("--local-fast", action="store_true", help="User-authorized local PC: 10 CPU/10 workers")
    parser.add_argument("--intervention", choices=("fusion", "context"), default="fusion")
    parser.add_argument("--ai-source", type=Path)
    parser.add_argument("--opcode-evidence", type=Path)
    parser.add_argument("--evaluate-economics", action="store_true", help="Explicit economic evaluation even without opcode gain; cannot qualify adoption")
    args = parser.parse_args()
    run(args.out.resolve(), args.resume, args.local_fast, args.intervention, args.ai_source, args.opcode_evidence, args.evaluate_economics)
