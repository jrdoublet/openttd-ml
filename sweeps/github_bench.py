"""GitHub Actions orchestration only; game collection stays in the existing harnesses.

Uses only the standard library on the host. Docker/OpenTTDLab run on GitHub, not
on the workstation used to dispatch the workflow. No shell evaluation of inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
AAAHOGEX_URL = (
    "https://bananas-cdn.openttd.org/ai/484f4745/"
    "db5fd180cdf633c1a3310c4a367052e9/484f4745-AAAHogEx-115.tar.gz"
)
AAAHOGEX_SHA256 = "a67f6722b73d9b3179277e45d091747d94148fd8676d13d6bac98c9124c57e0e"
ARM_RE = re.compile(r"OpexAI(?:\[[A-Za-z_][A-Za-z_0-9]*=-?\d+(?:,[A-Za-z_][A-Za-z_0-9]*=-?\d+)*\])?")


def make_plan(env):
    if env.get("BENCH_MIN_DELTA", ""):
        raise ValueError("Seuil absolu historique refusé ; utiliser BENCH_MIN_DELTA_PCT")
    mode = env.get("BENCH_MODE", "solo")
    profile = env.get("BENCH_PROFILE", "smoke")
    if mode not in ("solo", "duel", "paired"):
        raise ValueError("Mode inconnu")
    reference = env.get("BENCH_REFERENCE", "").strip() or "OpexAI"
    variant = env.get("BENCH_VARIANT", "").strip()
    if not ARM_RE.fullmatch(reference) or (variant and not ARM_RE.fullmatch(variant)):
        raise ValueError("Bras attendu : OpexAI ou OpexAI[reglage=entier,...]")
    if mode == "paired" and (not variant or reference == variant):
        raise ValueError("Le mode paired exige une variante distincte de la reference")
    if mode != "paired" and variant:
        raise ValueError("Une variante exige le mode paired")
    custom_years = env.get("BENCH_YEARS", "").strip()
    custom_seeds = env.get("BENCH_SEEDS", "").strip()
    if profile != "custom" and (custom_years or custom_seeds):
        raise ValueError("years et seeds doivent rester vides hors profil custom")
    if profile == "smoke":
        years, seeds = 1, [42]
    elif profile == "diagnostic":
        years, seeds = 6, [42, 100, 999, 1234, 5678]
    elif profile in ("gain_short", "non_erosion"):
        if mode != "paired":
            raise ValueError("Les portes V102 exigent paired")
        years, seeds = (3 if profile == "gain_short" else 10), None
    elif profile == "custom":
        years = int(custom_years)
        seeds = [int(value) for value in custom_seeds.replace(",", " ").split()]
        if not 1 <= years <= 10 or not 1 <= len(seeds) <= 40:
            raise ValueError("custom : 1..10 ans et 1..40 graines")
        if len(set(seeds)) != len(seeds) or any(not 0 <= s < 2**32 for s in seeds):
            raise ValueError("Graines uniques, entiers non signes sur 32 bits")
    else:
        raise ValueError("Profil inconnu")
    minimum = float(env.get("BENCH_MIN_DELTA_PCT", "4"))
    guard = float(env.get("BENCH_VALUE_GUARD", "5"))
    if not math.isfinite(minimum) or minimum < 0:
        raise ValueError("Effet utile : nombre fini >= 0")
    if not math.isfinite(guard) or not 0 <= guard <= 100:
        raise ValueError("Garde de valeur : pourcentage fini entre 0 et 100")
    telemetry = env.get("BENCH_LINE_TELEMETRY", "false")
    if telemetry not in ("true", "false") or (mode == "solo" and telemetry == "true"):
        raise ValueError("line_telemetry est un booleen reserve aux duels")
    run_id, attempt = env.get("GITHUB_RUN_ID", ""), env.get("GITHUB_RUN_ATTEMPT", "")
    if not re.fullmatch(r"\d+", run_id) or not re.fullmatch(r"\d+", attempt):
        raise ValueError("Identifiants GitHub run/attempt requis")
    campaign = f"gha-{run_id}-{attempt}"
    return dict(mode=mode, profile=profile, reference=reference, variant=variant,
                years=years, seeds=seeds, minimum=minimum, guard=guard,
                telemetry=telemetry == "true", campaign=campaign,
                output=f"results/{campaign}/bench.json",
                expected_games=(len(seeds) if seeds is not None else
                                40 if profile == "gain_short" else 20) * (2 if mode == "paired" else 1))


def command_for(plan, root=ROOT):
    common = ["--years", str(plan["years"]), "--max-workers", "2", "--out", plan["output"]]
    if plan["seeds"] is not None:
        common += ["--seeds", *map(str, plan["seeds"])]
    if plan["mode"] == "solo":
        return ["docker", "run", "--rm", "--cpus=3", "--memory=2g", "--memory-swap=2g",
                "-v", "openttd-lab-home:/home/lab", "-v", f"{root}:/work", "-w", "/work",
                "openttd-lab:github", "python3", "sweeps/smoke_test.py",
                "--arm", plan["reference"], *common]
    command = [sys.executable, "sweeps/run_c66_reference.py", "--image", "openttd-lab:github",
               "--campaign", plan["campaign"], "--cpus", "3", "--memory", "2g",
               "--engine-timeout", "1800", "--decision-rule",
               "non_erosion" if plan["profile"] == "non_erosion" else "gain_short", *common]
    if plan["reference"] != "OpexAI":
        command += ["--reference", plan["reference"]]
    if plan["mode"] == "paired":
        # The harness expects explicit settings, even when the variant is the default.
        if plan["variant"] == "OpexAI":
            raise ValueError("La variante doit expliciter ses reglages ; utiliser OpexAI comme reference")
        command += ["--variant", plan["variant"], "--variant-policy-id", "variant",
                    "--primary-metric", "profit_year", "--min-useful-primary-delta-pct", str(plan["minimum"]),
                    "--value-guard-max-loss-pct", str(plan["guard"])]
        if plan["profile"] != "non_erosion":
            command += ["--required-seeds", "40", "--required-years", "3"]
    if plan["telemetry"]:
        command += ["--line-telemetry"]
    return command


def install_opponent(data, destination):
    """Verify the immutable upstream archive, preserve all sources and licenses."""
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(f"Refus de remplacer {destination}")
    if hashlib.sha256(data).hexdigest() != AAAHOGEX_SHA256:
        raise ValueError("SHA-256 AAAHogEx 115 incorrect")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            members = archive.getmembers()
            for member in members:
                path = PurePosixPath(member.name)
                if (path.is_absolute() or ".." in path.parts or "\\" in member.name
                        or not (member.isfile() or member.isdir())):
                    raise ValueError(f"Entree d'archive refusee : {member.name}")
            archive.extractall(temporary, members=members, filter="data")
        infos = list(Path(temporary).rglob("info.nut"))
        if len(infos) != 1:
            raise ValueError("Archive AAAHogEx ambigue")
        folder = infos[0].parent
        info = infos[0].read_text(encoding="utf-8-sig")
        if not re.search(r"GetVersion\s*\(\s*\)\s*\{\s*return\s+115\s*;", info):
            raise ValueError("Version AAAHogEx differente de 115")
        if not (folder / "main.nut").is_file() or not (folder / "license.txt").is_file():
            raise ValueError("Source ou licence AAAHogEx manquante")
        shutil.copytree(folder, destination)


def profit_ratios(plan, report):
    """Read final harness metrics only; never re-decode or sum monthly snapshots.

    Ratios require healthy paired companies, four closed quarters and positive
    AAA profit. Do not publish an overall percentage for a selected subset.
    Reference/variant duels have different opponents and must remain separate.
    """
    def number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

    seeds = plan["seeds"] if plan["seeds"] is not None else report.get("seeds", [])
    expected = plan["expected_games"] // (2 if plan["mode"] == "paired" else 1)
    policies = [report.get("policy_id", "reference")]
    if plan["mode"] == "paired":
        policies.append("variant")
    index = {}
    for record in report.get("summary", []):
        key = (record.get("duel_policy_id"), record.get("seed"),
               record.get("repeat", 0), record.get("arm"))
        index.setdefault(key, []).append(record)
    results = []
    for policy in policies:
        rows = []
        for seed in seeds:
            records = [index.get((policy, seed, 0, arm), []) for arm in ("OpexAI", "AAAHogEx")]
            row = dict(seed=seed, opex_profit_year=None, aaa_profit_year=None,
                       opex_over_aaa_pct=None, reason=None)
            if any(len(items) != 1 for items in records):
                row["reason"] = "compagnie absente ou doublon"
            else:
                opex, aaa = (items[0] for items in records)
                op, ap = opex.get("profit_year"), aaa.get("profit_year")
                row["opex_profit_year"] = op if number(op) else None
                row["aaa_profit_year"] = ap if number(ap) else None
                if any(r.get("run_ok") is not True or r.get("game_ok") is not True for r in (opex, aaa)):
                    row["reason"] = "santé ou horizon invalide"
                elif any(r.get("profit_year_coverage") != "complete" for r in (opex, aaa)):
                    row["reason"] = "quatre trimestres valides non confirmés"
                elif not number(op) or not number(ap):
                    row["reason"] = "profit absent ou invalide"
                elif ap <= 0:
                    row["reason"] = "profit AAAHogEx nul ou négatif"
                else:
                    ratio = (op / ap) * 100
                    if math.isfinite(ratio):
                        row["opex_over_aaa_pct"] = ratio
                    else:
                        row["reason"] = "ratio non fini"
            rows.append(row)
        valid = [row for row in rows if row["opex_over_aaa_pct"] is not None]
        complete = (len(rows) == expected and len(set(seeds)) == expected
                    and len(valid) == expected and not report.get("failed_runs"))
        mean_opex = mean_aaa = overall = None
        if complete:
            mean_opex = math.fsum(row["opex_profit_year"] / expected for row in valid)
            mean_aaa = math.fsum(row["aaa_profit_year"] / expected for row in valid)
            overall = (mean_opex / mean_aaa) * 100
        results.append(dict(policy=policy, expected_games=expected, valid_ratios=len(valid),
                            complete=complete, mean_opex_profit_year=mean_opex,
                            mean_aaa_profit_year=mean_aaa, opex_over_aaa_pct=overall,
                            per_seed=rows))
    return results


def profit_summary_lines(plan, report):
    def fmt(value):
        return "n/d" if value is None else f"{value:,.1f}"

    lines = ["", "### Profits OpexAI / AAAHogEx",
             "Profit annuel au dernier checkpoint (quatre trimestres clos), pas le cumul du banc.",
             "100 % = égalité ; 80 % = OpexAI réalise 80 % du profit AAAHogEx."]
    for result in profit_ratios(plan, report):
        lines += ["", f"#### Politique `{result['policy']}`",
                  f"Ratios exploitables : {result['valid_ratios']}/{result['expected_games']}.",
                  "", "| Graine | OpexAI (£/an) | AAAHogEx (£/an) | Opex / AAA (%) | Réserve |",
                  "|---|---:|---:|---:|---|"]
        for row in result["per_seed"]:
            lines.append(f"| {row['seed']} | {fmt(row['opex_profit_year'])} | "
                         f"{fmt(row['aaa_profit_year'])} | {fmt(row['opex_over_aaa_pct'])} | "
                         f"{row['reason'] or '—'} |")
        if result["complete"]:
            lines += ["", f"**Ratio global : {fmt(result['opex_over_aaa_pct'])} %**",
                      f"Profits moyens : OpexAI {fmt(result['mean_opex_profit_year'])} £/an ; "
                      f"AAAHogEx {fmt(result['mean_aaa_profit_year'])} £/an.",
                      "Global = 100 × somme des profits OpexAI / somme des profits AAAHogEx "
                      "(pas la moyenne des pourcentages)."]
        else:
            lines += ["", "**Ratio global : n/d** — couverture incomplète, santé invalide "
                      "ou dénominateur non positif ; pas d'agrégation du seul sous-ensemble favorable."]
    return lines


def summary_text(plan, report):
    lines = ["## Banc OpenTTD", f"- Campagne : `{plan['campaign']}`",
             f"- Mode / profil : `{plan['mode']}` / `{plan['profile']}`",
             f"- Horizon : {plan['years']} ans ; parties attendues : {plan['expected_games']}"]
    if report is None:
        lines += ["- **Rapport final absent : campagne non validée.** Consulter les logs et artefacts partiels."]
    elif plan["mode"] == "solo":
        lines += [f"- Smoke : `{report.get('smoke_test_status', 'UNKNOWN')}`"]
    else:
        lines += [f"- Parties rapportées : {len(report.get('games', []))}",
                  f"- Échecs de santé : {len(report.get('failed_runs', []))}"]
        comparison = report.get("policy_comparison")
        if comparison:
            lines += [f"- Paires complètes : {comparison['complete_pairs']}/{comparison['planned_pairs']}",
                      f"- Verdict économique du harnais : **`{comparison['verdict']}`**"]
        lines += profit_summary_lines(plan, report)
    lines += ["", "Un job vert indique une exécution valide, pas une adoption économique.",
              "Les portes manuelles sont isolées : vérifier A et B comparables avant toute adoption.",
              "Télécharger les artefacts (JSON, JSONL, logs et, pour les duels, manifeste et bundle).", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "prepare", "run", "summary"))
    args = parser.parse_args()
    plan = make_plan(os.environ)
    command = command_for(plan)
    output = ROOT / plan["output"]
    directory = output.parent
    if args.action == "plan":
        directory.mkdir(parents=True, exist_ok=False)
        (directory / "request.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(plan, indent=2), flush=True)
    elif args.action == "prepare" and plan["mode"] != "solo":
        with urlopen(AAAHOGEX_URL, timeout=60) as response:
            data = response.read(2 * 1024 * 1024)
        install_opponent(data, ROOT / "ai" / "AAAHogEx-115")
        (directory / "opponent.json").write_text(json.dumps({
            "url": AAAHOGEX_URL, "sha256": AAAHOGEX_SHA256, "version": 115,
            "license": "GPL v3", "source": "Official BaNaNaS archive; not a local VPS copy",
        }, indent=2) + "\n", encoding="utf-8")
    elif args.action == "run":
        print("Arguments:", json.dumps(command), flush=True)
        raise SystemExit(subprocess.run(command, cwd=ROOT, check=False).returncode)
    elif args.action == "summary":
        report = json.loads(output.read_text(encoding="utf-8")) if output.is_file() else None
        text = summary_text(plan, report)
        directory.mkdir(parents=True, exist_ok=True)
        if report is not None and plan["mode"] != "solo":
            (directory / "profit-ratios.json").write_text(json.dumps({
                "metric": "profit_year", "period": "last_four_closed_quarters_at_final_checkpoint",
                "formula": "100 * sum(opex_profit_year) / sum(aaa_profit_year)",
                "policies": profit_ratios(plan, report),
            }, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
        (directory / "summary.md").write_text(text, encoding="utf-8")
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
                handle.write(text)
        print(text)
        if report is None:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
