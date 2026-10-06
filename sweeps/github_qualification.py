"""Bounded smoke -> diagnostic -> adoption; no dispatch loop, default edit or merge."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
from urllib.request import urlopen

from campaign_freeze import parse_ai_setting_specs
from github_bench import (AAAHOGEX_SHA256, AAAHOGEX_URL, ROOT, command_for,
                          install_opponent, make_plan, profit_ratios, summary_text)
from qualification import (ACCEPTED, INVALID, PROFILES, REJECTED, arm_settings, digest,
                           evaluate, load_evidence, read_json, require, validate_spec, write_json)


def location(env):
    run, attempt = env.get("GITHUB_RUN_ID", ""), env.get("GITHUB_RUN_ATTEMPT", "")
    require(re.fullmatch(r"\d+", run) and re.fullmatch(r"\d+", attempt), "Run/attempt requis")
    return ROOT / "results" / f"qualification-{run}-{attempt}"


def stage_plan(spec, stage, env):
    plan = make_plan(dict(env, BENCH_MODE="paired", BENCH_PROFILE=stage,
                          BENCH_REFERENCE=spec["reference"], BENCH_VARIANT=spec["variant"],
                          BENCH_YEARS="", BENCH_SEEDS="", BENCH_MIN_DELTA="50000",
                          BENCH_VALUE_GUARD="5", BENCH_LINE_TELEMETRY="false"))
    plan["campaign"] = f"qualification-{env['GITHUB_RUN_ID']}-{env['GITHUB_RUN_ATTEMPT']}-{stage}"
    plan["output"] = (location(env) / stage / "bench.json").relative_to(ROOT).as_posix()
    # Pin the actual seed list, rather than relying on a future harness default.
    plan["seeds"] = PROFILES[stage][1]
    return plan


def initialize(env):
    directory = location(env)
    directory.mkdir(parents=True, exist_ok=False)
    write_json(directory / "decision.json", dict(status=INVALID, reasons=["Préparation inachevée"], stages=[]))
    path = (ROOT / env["QUALIFICATION_PLAN"]).resolve()
    require(path.is_relative_to((ROOT / "qualifications").resolve()) and path.suffix == ".json",
            "Plan versionné qualifications/*.json requis")
    spec = validate_spec(read_json(path))
    sha = env["GITHUB_SHA"]
    require(re.fullmatch(r"[0-9a-f]{40}", sha), "SHA GitHub requis")
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == sha,
            "Checkout différent du run")
    require(not subprocess.check_output(["git", "status", "--porcelain=v1", "--untracked-files=all"],
                                        cwd=ROOT, text=True).strip(), "Checkout non propre")
    specs = parse_ai_setting_specs(ROOT / "ai/OpexAI/info.nut")
    for role in ("reference", "variant"):
        for name, value in arm_settings(spec[role]).items():
            require(name in specs, f"Réglage inconnu : {name}")
            setting = specs[name]
            minimum = 0 if setting["boolean"] else setting["min_value"]
            maximum = 1 if setting["boolean"] else setting["max_value"]
            require(minimum is not None and maximum is not None and minimum <= value <= maximum,
                    f"Réglage hors bornes : {name}")
            step = setting["step_size"]
            require(step is None or (step > 0 and (value - minimum) % step == 0),
                    f"Pas de réglage incorrect : {name}")
            if role == "reference":
                require(value == setting["default"], f"Ancien défaut non conservé : {name}")
    for name in spec["contract_tests"]:
        require((ROOT / "sweeps" / f"{name}.py").is_file(), f"Contrat absent : {name}")
    request = dict(schema_version=1, qualification_id=directory.name, sha=sha,
                   run_id=env["GITHUB_RUN_ID"], attempt=env["GITHUB_RUN_ATTEMPT"],
                   repository=env.get("GITHUB_REPOSITORY"), ref=env.get("GITHUB_REF"),
                   spec_path=path.relative_to(ROOT).as_posix(), spec_sha256=digest(path), spec=spec,
                   stages=[stage_plan(spec, stage, env) for stage in PROFILES])
    write_json(directory / "request.json", request)
    print(f"Plan figé : {directory.name} / {sha}", flush=True)


def request_at(directory):
    request = read_json(directory / "request.json")
    validate_spec(request["spec"])
    require(digest(ROOT / request["spec_path"]) == request["spec_sha256"] and
            read_json(ROOT / request["spec_path"]) == request["spec"], "Plan modifié après préparation")
    return request


def prepare(directory):
    request_at(directory)
    with urlopen(AAAHOGEX_URL, timeout=60) as response:
        data = response.read(2 * 1024 * 1024)
    install_opponent(data, ROOT / "ai/AAAHogEx-115")
    write_json(directory / "opponent.json", dict(url=AAAHOGEX_URL, sha256=AAAHOGEX_SHA256,
                                                version=115, license="GPL v3"))


def run_bounded(command, *, timeout, log, container):
    """Kill the named container AND its host launcher on timeout/cancellation."""
    require(timeout > 0, "Budget épuisé")
    with Path(log).open("w", encoding="utf-8") as handle:
        process = subprocess.Popen(command, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT,
                                   start_new_session=(os.name == "posix"))
        try:
            return process.wait(timeout=timeout)
        finally:
            if process.poll() is None:
                try:
                    subprocess.run(["docker", "rm", "--force", container], check=False,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
                finally:
                    if os.name == "posix":
                        os.killpg(process.pid, signal.SIGKILL)
                    else:
                        process.kill()
                    process.wait(timeout=30)


def contracts(directory):
    request = request_at(directory)
    container = directory.name + "-contracts"
    command = ["docker", "run", "--rm", "--name", container, "--cpus=3", "--memory=2g", "--memory-swap=2g",
               "-v", "openttd-lab-home:/home/lab", "-v", f"{ROOT}:/work", "-w", "/work/sweeps",
               "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "PYTHONPATH=/work:/work/sweeps",
               "openttd-lab:github", "python3", "-m", "unittest", "-v",
               *request["spec"]["contract_tests"]]
    code = run_bounded(command, timeout=600, log=directory / "contracts.log", container=container)
    require(code == 0, f"Contrats en échec : {code}")
    write_json(directory / "contracts.json", dict(request_sha256=digest(directory / "request.json"),
                                                 exit_code=code, modules=request["spec"]["contract_tests"]))


def run_sequence(directory, execute=run_bounded):
    request = request_at(directory)
    receipt = read_json(directory / "contracts.json")
    require(receipt["exit_code"] == 0 and receipt["request_sha256"] == digest(directory / "request.json"),
            "Contrats non validés pour ce plan")
    spec = request["spec"]
    decision = dict(qualification_id=request["qualification_id"], sha=request["sha"],
                    request_sha256=digest(directory / "request.json"), status=INVALID,
                    reasons=["Séquence inachevée"], stages=[])
    write_json(directory / "decision.json", decision)
    deadline = time.monotonic() + spec["budget_minutes"] * 60
    previous = None
    for plan in request["stages"]:
        stage = plan["profile"]
        output = ROOT / plan["output"]
        output.parent.mkdir(parents=True, exist_ok=False)
        write_json(output.parent / "request.json", plan)
        result = dict(stage=stage, status=INVALID, proceed=False, reasons=["Étape inachevée"])
        try:
            container = plan["campaign"]
            command = command_for(plan) + ["--container-name", container, "--repeats", "1"]
            code = execute(command, timeout=deadline - time.monotonic(),
                           log=output.parent / "console.log", container=container)
            require(code == 0, f"Exécution moteur en échec : {code}")
            report, manifest = load_evidence(output, spec)
            result = evaluate(spec, stage, report, manifest, expected_sha=request["sha"],
                              campaign=plan["campaign"], previous=previous)
            result["report_sha256"] = digest(output)
            result["manifest_sha256"] = digest(output.with_suffix(".manifest.json"))
            (output.parent / "summary.md").write_text(summary_text(plan, report), encoding="utf-8")
            write_json(output.parent / "profit-ratios.json", profit_ratios(plan, report))
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
            result.update(status=INVALID, proceed=False, reasons=[str(error)])
        write_json(output.parent / "decision.json", result)
        decision["stages"].append(result)
        decision["status"] = result["status"] if not result["proceed"] or stage == "adoption" else INVALID
        decision["reasons"] = result["reasons"] if decision["status"] != INVALID or not result["proceed"] else ["Séquence inachevée"]
        write_json(directory / "decision.json", decision)
        print(f"{stage}: {result['status']} — {'; '.join(result['reasons'])}", flush=True)
        if not result["proceed"]:
            break
        previous = result["identity"]
    return 0 if decision["status"] == ACCEPTED else 2 if decision["status"] == REJECTED else 1


def summarize(directory):
    path = directory / "decision.json"
    if not path.exists():
        directory.mkdir(parents=True, exist_ok=True)
        write_json(path, dict(status=INVALID, stages=[], reasons=["Initialisation/runner interrompu"]))
    decision = read_json(path)
    text = "## Qualification de défaut\n\n"
    text += f"**{decision['status']}** — {'; '.join(decision['reasons'])}\n\n"
    text += "| Étape | Décision | Verdict brut |\n|---|---|---|\n"
    for result in decision["stages"]:
        text += f"| {result['stage']} | {result['status']} | {result.get('raw_harness_verdict', 'n/d')} |\n"
    text += "\nAucun défaut modifié. Smoke/diagnostic ne sont pas une adoption. Voir decision.json et les artefacts complets.\n"
    (directory / "summary.md").write_text(text, encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
            handle.write(text)
    print(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("init", "prepare", "contracts", "run", "summary"))
    args = parser.parse_args()
    directory = location(os.environ)
    if args.action == "init":
        initialize(os.environ)
    elif args.action == "prepare":
        prepare(directory)
    elif args.action == "contracts":
        contracts(directory)
    elif args.action == "run":
        raise SystemExit(run_sequence(directory))
    else:
        summarize(directory)


if __name__ == "__main__":
    main()