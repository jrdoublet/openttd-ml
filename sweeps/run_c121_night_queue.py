"""Sequential, bounded C121 retests using the unchanged frozen C66 launcher.

The plan distinguishes qualification attempts from exploratory comparisons.
Exploratory statistical passes never authorize B or adoption.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from datetime import datetime, timezone


def save(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    # Windows readers or antivirus can briefly lock the destination.
    for attempt in range(21):
        try:
            tmp.replace(path)
            return
        except PermissionError:
            if attempt == 20:
                raise
            time.sleep(0.25)


def resource_args(plan):
    cpus = int(plan.get("cpus", 3))
    workers = int(plan.get("max_workers", 3))
    memory = plan.get("memory", "2g")
    if cpus <= 0 or workers <= 0 or workers > cpus:
        raise ValueError("Require positive resources and workers <= allocated CPUs")
    if not isinstance(memory, str) or not re.fullmatch(r"[1-9][0-9]*[mg]", memory):
        raise ValueError("Memory must be a positive Docker size in m or g")
    return ["--cpus", str(cpus), "--memory", memory, "--max-workers", str(workers)]


def healthy(data, pairs):
    games = data.get("games", [])
    comp = data.get("policy_comparison", {})
    return (data.get("failed_runs") == [] and len(games) == pairs * 2
            and all(g.get("game_ok") is True and not g.get("unattributed_errors")
                    and set(g.get("companies", {})) == {"OpexAI", "AAAHogEx"}
                    and all(c.get("horizon_complete") is True and c.get("run_ok") is True
                            for c in g["companies"].values()) for g in games)
            and comp.get("comparison_complete") is True
            and comp.get("complete_pairs") == pairs)


def gate_pass(data, rule, pairs):
    c = data.get("policy_comparison", {})
    return (healthy(data, pairs) and c.get("adoption_sample_complete") is True
            and c.get("metric_coverage_complete") is True
            and c.get("decision_rule", {}).get("rule") == rule
            and c.get("verdict") == "pass"
            and c.get("primary_pass") is True and c.get("value_guard_pass") is True)


def snapshot(root):
    paths = list((root / "ai").rglob("*"))
    paths += list((root / "sweeps").glob("*.py"))
    paths += [root / "requirements.txt"]
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths if p.is_file() and "__pycache__" not in p.parts}


def exposed(data, root, kind):
    hits = []
    for g in data["games"]:
        if kind in ("n1", "hubcap", "priority", "marginal") and g["policy_id"] == "reference":
            continue
        if kind == "kpass" and g["policy_id"] == "reference":
            continue
        if kind == "kdec" and g["policy_id"] != "reference":
            continue
        log = root / g["engine_log_path"].removeprefix("/work/")
        text = log.read_text(encoding="utf-8", errors="replace")
        patterns = {
            "kpass": r"C121_KPASS_AIR_CONTINUE fleet_rank=",
            "kdec": r"C121_KDEC_COLD_SHADOW state=cold[^\n]*affected=1",
            "n1": r"QUAL_EXPOSURE mechanism=n1 applied=1",
            "hubcap": r"QUAL_EXPOSURE mechanism=hubcap rejected=1",
            "priority": r"C121_FIRST_LIVE_PRIORITY_DEFER line=",
            "marginal": r"QUAL_EXPOSURE mechanism=marginal rejected=1",
        }
        count = len(re.findall(r"\[script:\d+\]\s*\[0\].*?" + patterns[kind], text))
        if count:
            hits.append({"seed": g["seed"], "events": count, "log": str(log)})
    return hits


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--plan", type=Path, required=True)
    args = p.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    resources = resource_args(plan)
    root = Path(plan["worktree"])
    mount = Path(plan.get("mount_root", str(root)))
    out = args.plan.parent
    status_path = out / "status.json"
    with (out / "started.lock").open("x", encoding="utf-8") as lock:
        lock.write(str(os.getpid()))
    initial = snapshot(root)
    diagnostic_root = Path(plan.get("exposure_worktree", str(root)))
    diagnostic_initial = snapshot(diagnostic_root)
    deadline = time.monotonic() + plan["budget_seconds"]
    state = {"started_utc": datetime.now(timezone.utc).isoformat(),
             "deadline_utc": datetime.fromtimestamp(time.time() + plan["budget_seconds"],
                                                  timezone.utc).isoformat(),
             "pid": os.getpid(), "state": "running", "results": []}
    save(status_path, state)
    env = os.environ.copy()
    env["PATH"] = plan["docker_dir"] + os.pathsep + env.get("PATH", "")
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONUTF8"] = "1"

    def run(entry, step, *, years, pairs, seeds=None, probe=False):
        run_root = diagnostic_root if probe and entry.get("exposure") in ("n1", "hubcap", "priority", "marginal") else root
        running = subprocess.check_output(["docker", "ps", "-q"], env=env, text=True).strip()
        if running:
            raise RuntimeError("Another Docker container is running; queue stopped.")
        if snapshot(root) != initial:
            raise RuntimeError("Frozen worktree sources changed; queue stopped.")
        if snapshot(diagnostic_root) != diagnostic_initial:
            raise RuntimeError("Frozen exposure sources changed; queue stopped.")
        if time.monotonic() >= deadline:
            raise TimeoutError("Eight-hour budget exhausted before next stage.")
        other = dict(entry.get("common", {}))
        if probe:
            other.update(entry.get("exposure_common", {}))
        if probe and entry["exposure"] == "kdec":
            other["c121_kdec_cold_shadow"] = 1
        def arm(value):
            settings = {"c121_air_economics": 1, "c121_catalog_incremental": 1,
                        **other, entry["setting"]: value}
            return "OpexAI[" + ",".join(f"{k}={v}" for k, v in settings.items()) + "]"
        cid = f'{plan["id"]}_{entry["id"]}_{step}'
        container = cid.lower().replace("_", "-")
        result = run_root / "results" / (cid + ".json")
        if result.exists() or result.with_suffix(".jsonl").exists():
            raise RuntimeError("Campaign already exists; never overwrite or repeat.")
        rule = "non_erosion" if step == "B" else "gain_short"
        cmd = [sys.executable, "-X", "utf8", str(run_root / "sweeps/run_c66_reference.py"),
               "--mount-root", str(mount),
               "--campaign", cid, "--container-name", container,
               "--image", plan["image"], "--reference", arm(entry["old"]),
               "--variant", arm(entry["new"]), "--variant-policy-id", entry["id"],
               "--primary-metric", "profit_year", "--value-guard-max-loss-pct", "5",
               "--min-useful-primary-delta-pct", "4", "--decision-rule", rule,
               "--years", str(years), "--repeats", "1", *resources, "--script-debug"]
        if step != "B":
            cmd += ["--required-seeds", "40", "--required-years", str(entry["years"])]
        if seeds:
            cmd += ["--seeds", *map(str, seeds)]
        state["current"] = {"campaign": cid, "step": step, "container": container,
                            "result": str(result), "command": cmd}
        save(status_path, state)
        with (out / (cid + ".launcher.log")).open("x", encoding="utf-8") as log:
            proc = subprocess.Popen(cmd, cwd=run_root, env=env, stdout=log,
                                    stderr=subprocess.STDOUT)
            try:
                rc = proc.wait(timeout=max(1, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                subprocess.run(["docker", "stop", "--time", "20", container],
                               env=env, timeout=35, check=False, stdout=log, stderr=log)
                proc.terminate()
                proc.wait(timeout=15)
                raise TimeoutError("Eight-hour deadline; current gate interrupted, not validated.")
        if rc != 0 or not result.is_file():
            raise RuntimeError(f"{cid}: technical failure, exit={rc}; inspect launcher log.")
        data = json.loads(result.read_text(encoding="utf-8"))
        manifest = mount / data["manifest_path"].removeprefix("/work/")
        if hashlib.sha256(manifest.read_bytes()).hexdigest() != data["manifest_sha256"]:
            raise RuntimeError("Manifest hash mismatch.")
        if not healthy(data, pairs):
            raise RuntimeError(f"{cid}: incomplete or unhealthy; no automatic retry.")
        if pairs >= 20 and not data["policy_comparison"].get("metric_coverage_complete"):
            raise RuntimeError(f"{cid}: incomplete terminal metric coverage.")
        summary = {"campaign": cid, "result": str(result),
                   "raw_verdict": data["policy_comparison"]["verdict"],
                   "kind": entry["kind"], "step": step,
                   "source_bundle_sha256": data["source_bundle_sha256"],
                   "manifest_sha256": data["manifest_sha256"],
                   "qualification_complete": False}
        state["results"].append(summary)
        save(status_path, state)
        return data, summary

    try:
        for entry in plan["entries"]:
            if entry["kind"] == "opcode":
                receipt_path = Path(entry["opcode_receipt"])
                if (entry.get("opcode_receipt_sha256")
                        and hashlib.sha256(receipt_path.read_bytes()).hexdigest() != entry["opcode_receipt_sha256"]):
                    raise RuntimeError("Opcode prerequisite receipt changed; queue stopped.")
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                if not receipt.get("opcode_gain_measured"):
                    state["results"].append({"kind": "opcode", "setting": entry["setting"],
                        "qualification_complete": False, "stop_reason": "matched_opcode_gain_absent",
                        "opcode_receipt": str(receipt_path)})
                    save(status_path, state)
                    continue
                run(entry, "smoke", years=1, pairs=1, seeds=[42])
                data, summary = run(entry, "B", years=10, pairs=20)
                from run_c121_winner_economic_validation import neutral_gate
                summary["opcode_neutrality"] = neutral_gate(data, 20, adoption=True)
                summary["opcode_receipt"] = str(receipt_path)
                summary["qualification_complete"] = summary["opcode_neutrality"]["pass"]
                save(status_path, state)
                continue
            if entry["kind"] == "user_requested_B":
                if plan.get("user_authorized_direct_B") is not True:
                    raise ValueError("Direct B requires explicit recorded user authorization")
                data, summary = run(entry, "B", years=10, pairs=20)
                summary["B_pass"] = gate_pass(data, "non_erosion", 20)
                summary["qualification_complete"] = False
                summary["stop_reason"] = "explicit B after failed A; no adoption qualification"
                save(status_path, state)
                continue
            run(entry, "smoke", years=1, pairs=1, seeds=[42])
            if entry["kind"] == "qualification":
                data, summary = run(entry, "exposure", years=entry.get("exposure_years", 3), pairs=5,
                                    seeds=[42, 100, 999, 1234, 5678], probe=True)
                hits = exposed(data, mount, entry["exposure"])
                summary["exposure"] = hits
                save(status_path, state)
                if not hits:
                    summary["stop_reason"] = "exposure_missing; A and B not launched"
                    save(status_path, state)
                    continue
                data, summary = run(entry, "A", years=entry["years"], pairs=40)
                if gate_pass(data, "gain_short", 40) and entry["allow_B"]:
                    data, summary = run(entry, "B", years=10, pairs=20)
                    summary["qualification_complete"] = gate_pass(data, "non_erosion", 20)
                    save(status_path, state)
                else:
                    summary["stop_reason"] = ("A_failed_or_incomplete" if
                                             not gate_pass(data, "gain_short", 40) else
                                             "B_prohibited_by_current_task")
                    save(status_path, state)
            else:
                # Full comparative exploration requested for the night. This is not
                # a qualification A: missing mechanism-specific exposure remains explicit.
                _, summary = run(entry, "exploration", years=entry["years"], pairs=40)
                summary["stop_reason"] = "exposure_and_qualification_require_review; no B"
                save(status_path, state)
        state["state"] = "completed"
    except TimeoutError as exc:
        state["state"] = "budget_exhausted"
        state["reason"] = str(exc)
    except Exception as exc:
        state["state"] = "stopped_technical"
        state["reason"] = str(exc)
    finally:
        state["finished_utc"] = datetime.now(timezone.utc).isoformat()
        save(status_path, state)
    return 1 if state["state"] == "stopped_technical" else 0


if __name__ == "__main__":
    raise SystemExit(main())
