"""Sonde A6 : la contrainte dominante VARIE-T-ELLE au cours d'une partie ?

C'est la seule question que cette sonde pose, et elle doit y repondre AVANT qu'une ligne
d'arbitrage soit ecrite. Si la dominante est l'argent 100 % du temps, le modele de tension se
reduit a ce que le classement fait deja -- ROI capital -- et il n'y a rien a coder. Precedents
qui imposent ce controle : portfolio_max_batch, rejete avec 11 graines sur 20 en NULS EXACTS
(le mecanisme ne se declenchait jamais), et le plafond maxRoutes, mesure a 0 refus sur 32.

Second livrable, aussi important que le premier : l'ECART RELATIF entre la premiere et la
deuxieme tension. Un ecart faible signifie qu'un argmax basculerait sur du bruit d'estimation,
donc qu'une bascule discrete (a la AAAHogEx, _IsRich) serait instable et qu'il faut le
denominateur PONDERE. Un ecart large signifie l'inverse, et la bascule suffirait.

`tension_probe=1` ne change AUCUNE decision : classement, selection et construction sont
identiques. La sonde ne fait que journaliser.
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import enable_savegame_cleanup, make_cfg  # noqa: E402

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(a).startswith("-vnull") for a in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

OPEX_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) (TENSION|TENSION_COST) (.*)$")
FAIL_RE = re.compile(r"Your script made an error|The script died unexpectedly")


def keep(row):
    return ({"seed": row["experiment"]["seed"], "date": str(row["date"]),
             "output": row.get("output")},)


def parse(output):
    tensions, costs, errors = [], [], []
    for line in (output or "").splitlines():
        if FAIL_RE.search(line):
            errors.append(line.strip()[:200])
            continue
        m = OPEX_RE.search(line)
        if not m:
            continue
        year, month, _day, kind, rest = m.groups()
        fields = {}
        for token in rest.split():
            if "=" in token:
                key, _, value = token.partition("=")
                fields[key] = value
        fields["year"] = int(year)
        fields["month"] = int(month)
        (tensions if kind == "TENSION" else costs).append(fields)
    return tensions, costs, errors


def report(seed, tensions, costs):
    doms = Counter(t.get("dominant", "?") for t in tensions)
    by_year = defaultdict(Counter)
    for t in tensions:
        by_year[t["year"]][t.get("dominant", "?")] += 1

    gaps = []
    for t in tensions:
        try:
            gaps.append(float(t.get("gap", "nan")))
        except ValueError:
            pass
    gaps = [g for g in gaps if g == g]
    gaps.sort()
    ops = []
    for c in costs:
        try:
            ops.append(int(c.get("probe_ops", 0)))
        except ValueError:
            pass

    print(f"\n=== graine {seed} : {len(tensions)} evaluations, {len(costs)} cycles ===")
    total = sum(doms.values()) or 1
    print("  dominante globale : " + ", ".join(
        f"{k} {v} ({100 * v / total:.0f} %)" for k, v in doms.most_common()))
    if gaps:
        med = gaps[len(gaps) // 2]
        tight = sum(1 for g in gaps if g < 0.10)
        print(f"  ecart 1re/2e : median {med:.3f} | < 0,10 sur {tight}/{len(gaps)} "
              f"({100 * tight / len(gaps):.0f} %) -> un argmax y basculerait sur du bruit")
    if ops:
        ops.sort()
        print(f"  cout sonde : median {ops[len(ops) // 2]} opcodes/cycle, max {ops[-1]}")
    print("  par annee :")
    for year in sorted(by_year):
        row = by_year[year]
        n = sum(row.values())
        print(f"    {year} : " + ", ".join(f"{k} {100 * v / n:.0f} %" for k, v in row.most_common()))
    return {"dominant": dict(doms), "by_year": {y: dict(c) for y, c in by_year.items()},
            "gaps": gaps, "probe_ops": ops}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 999, 12345])
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "diag_tension.json")
    args = parser.parse_args()

    enable_savegame_cleanup()
    ai = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI",
                      (("decision_log", 1), ("tension_probe", 1)))
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        max_workers=args.workers, result_processor=keep,
        experiments=[{"seed": seed, "days": 365 * args.years,
                      "openttd_config": make_cfg(1970), "ais": (ai,)}
                     for seed in args.seeds],
        ai_libraries=(bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                      bananas_ai_library("5046524c", "Pathfinder.Rail"))))

    per_seed, all_errors = {}, {}
    for seed in args.seeds:
        output = ""
        for r in rows:
            if r["seed"] == seed and r.get("output"):
                output = r["output"]
                break
        tensions, costs, errors = parse(output)
        if errors:
            all_errors[seed] = errors
            print(f"\n🔴 graine {seed} : {len(errors)} erreurs de script")
            for e in errors[:5]:
                print("   ", e)
        per_seed[seed] = report(seed, tensions, costs)

    merged = Counter()
    all_gaps = []
    for data in per_seed.values():
        merged.update(data["dominant"])
        all_gaps.extend(data["gaps"])
    total = sum(merged.values()) or 1
    print("\n=== TOUTES GRAINES ===")
    print("  dominante : " + ", ".join(
        f"{k} {v} ({100 * v / total:.0f} %)" for k, v in merged.most_common()))
    if all_gaps:
        all_gaps.sort()
        tight = sum(1 for g in all_gaps if g < 0.10)
        print(f"  ecart 1re/2e : median {all_gaps[len(all_gaps) // 2]:.3f} | "
              f"< 0,10 sur {100 * tight / len(all_gaps):.0f} % des evaluations")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "years": args.years, "seeds": args.seeds,
        "per_seed": {str(k): v for k, v in per_seed.items()},
        "script_errors": {str(k): v for k, v in all_errors.items()},
    }, indent=1))
    print("\necrit", args.out)


if __name__ == "__main__":
    main()
