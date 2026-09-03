"""L'ENTONNOIR DE DECISION : pourquoi 30 projets sont-ils ecartes pour un elu ?

Mesure du 2026-09-03 (S0 quintrigesies) : sur dix ans, l'IA classe 109 a 141 fois, ecarte 71 a
134 projets et n'en elit que 2 a 5. Elle n'est ni empechee (aucune tension ne mord dans 97 % des
cas) ni endormie (elle evalue 86-89 % des mois) : elle REJETTE. Ce script agrege les motifs.

Trois etages, du plus large au plus etroit :
  1. VIVIER_GEN     : paires produites -> candidats retenus ;
  2. VIVIER_REJECT  : pourquoi une paire ne devient pas candidat (motifs cumules) ;
  3. PROJECT_DISCARD: pourquoi un projet classe n'est pas elu -- l'etage decisif, celui ou le
     ratio 30:1 se joue.
"""
import argparse, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import enable_savegame_cleanup, make_cfg  # noqa: E402

_real = openttdlab.subprocess.check_output


def _hook(args, *rest, **kw):
    args = tuple(args)
    if any(str(a).startswith("-vnull") for a in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real(args, *rest, **kw)


openttdlab.subprocess.check_output = _hook
OPEX_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")


def keep(row):
    return ({"seed": row["experiment"]["seed"], "date": str(row["date"]),
             "output": row.get("output")},)


def analyse(output):
    discard = Counter()
    discard_by_mode = defaultdict(Counter)
    vivier = Counter()
    produced = kept = chosen = 0
    builds = Counter()
    for line in (output or "").splitlines():
        m = OPEX_RE.search(line)
        if not m:
            continue
        _y, _mo, _d, kind, rest = m.groups()
        f = dict(t.split("=", 1) for t in rest.split() if "=" in t)
        if kind == "PROJECT_DISCARD":
            reason = f.get("reason", "?")
            discard[reason] += 1
            discard_by_mode[f.get("mode", "?")][reason] += 1
        elif kind == "VIVIER_REJECT":
            try:
                vivier[f.get("reason", "?")] += int(f.get("n", 0))
            except ValueError:
                pass
        elif kind == "VIVIER_GEN":
            try:
                produced += int(f.get("produced", 0))
                kept += int(f.get("kept", 0))
            except ValueError:
                pass
        elif kind == "PROJECT_CHOSEN":
            chosen += 1
        elif kind.endswith("_BUILD"):
            builds[kind] += 1
    return {"discard": discard, "discard_by_mode": discard_by_mode, "vivier": vivier,
            "produced": produced, "kept": kept, "chosen": chosen, "builds": builds}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 999, 7])
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "diag_discards.json")
    args = parser.parse_args()

    enable_savegame_cleanup()
    ai = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", (("decision_log", 1),))
    rows = list(run_experiments(
        openttd_version="15.3", opengfx_version="7.1", max_workers=args.workers,
        result_processor=keep,
        experiments=[{"seed": s, "days": 365 * args.years,
                      "openttd_config": make_cfg(1970), "ais": (ai,)} for s in args.seeds],
        ai_libraries=(bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                      bananas_ai_library("5046524c", "Pathfinder.Rail"))))

    merged_d, merged_v, merged_b = Counter(), Counter(), Counter()
    per_seed = {}
    for seed in args.seeds:
        output = next((r["output"] for r in rows if r["seed"] == seed and r.get("output")), "")
        a = analyse(output)
        per_seed[seed] = a
        merged_d.update(a["discard"])
        merged_v.update(a["vivier"])
        merged_b.update(a["builds"])
        print(f"\n=== graine {seed} : {a['produced']} paires produites -> {a['kept']} candidats "
              f"-> {sum(a['discard'].values())} ecartes -> {a['chosen']} elus "
              f"-> {sum(a['builds'].values())} constructions")
        for reason, n in a["discard"].most_common(8):
            print(f"    PROJECT_DISCARD  {reason:28} {n:>5}")

    total = sum(merged_d.values()) or 1
    print(f"\n=== MOTIFS DE REJET AU PORTEFEUILLE, toutes graines ({total}) ===")
    for reason, n in merged_d.most_common():
        print(f"  {reason:32} {n:>5}  ({100 * n / total:.0f} %)")
    print("\n=== par mode ===")
    for seed in args.seeds:
        for mode, counter in per_seed[seed]["discard_by_mode"].items():
            top = ", ".join(f"{r} {n}" for r, n in counter.most_common(3))
            print(f"  g{seed} {mode:6} : {top}")
    tv = sum(merged_v.values()) or 1
    print(f"\n=== rejets du VIVIER, toutes graines ({tv}) ===")
    for reason, n in merged_v.most_common(8):
        print(f"  {reason:32} {n:>7}  ({100 * n / tv:.0f} %)")
    print("\nconstructions :", dict(merged_b))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "years": args.years, "seeds": args.seeds,
        "per_seed": {str(s): {"discard": dict(a["discard"]), "vivier": dict(a["vivier"]),
                              "produced": a["produced"], "kept": a["kept"],
                              "chosen": a["chosen"], "builds": dict(a["builds"])}
                     for s, a in per_seed.items()}}, indent=1))
    print("\necrit", args.out)


if __name__ == "__main__":
    main()
