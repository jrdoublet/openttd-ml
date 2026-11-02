"""Agrège les paires référence/variante de plusieurs JSONL du harnais C66.

Usage : python3 sweeps/aggregate_paired_gates.py VARIANT_POLICY_ID a.jsonl [b.jsonl ...]

Sert au rebanc « proche du seuil » (AGENTS.md §4.1, 02/11) : 40 graines canoniques
plus 40 graines disjointes, une paire par graine, dernière valeur de profit_year et de
company_value de chaque bras. Rapporte delta moyen (et % de la référence), V/D,
Wilcoxon exact, IC95 bootstrap et écart de valeur (ratio des moyennes).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paired_statistics import bootstrap_mean_ci, exact_wilcoxon_signed_rank_p


def load(files):
    profit, value = {}, {}
    for name in files:
        with open(name, encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                run = record.get("run", [])
                if not run or run[0] != "OpexAI":
                    continue
                key = (record.get("policy_id"), run[1])
                if record.get("profit_year") is not None:
                    profit[key] = record["profit_year"]
                if record.get("company_value") is not None:
                    value[key] = record["company_value"]
    return profit, value


def main(argv):
    if len(argv) < 3:
        sys.exit(__doc__)
    variant, files = argv[1], argv[2:]
    profit, value = load(files)
    seeds = sorted({s for (p, s) in profit if p == variant}
                   & {s for (p, s) in profit if p == "reference"})
    if not seeds:
        sys.exit("aucune paire complète")
    deltas = [profit[(variant, s)] - profit[("reference", s)] for s in seeds]
    mean = sum(deltas) / len(deltas)
    ref = sum(profit[("reference", s)] for s in seeds) / len(seeds)
    wins = sum(d > 0 for d in deltas)
    losses = sum(d < 0 for d in deltas)
    ratio = (sum(value[(variant, s)] for s in seeds)
             / sum(value[("reference", s)] for s in seeds))
    low, high = bootstrap_mean_ci(deltas)
    print(f"n={len(seeds)} delta={mean:.0f} ({100 * mean / ref:.2f} % de {ref:.0f}) "
          f"V/D={wins}/{losses} p={exact_wilcoxon_signed_rank_p(deltas):.4f} "
          f"IC95=[{low:.0f} ; {high:.0f}] valeur={100 * (ratio - 1):+.2f} %")


if __name__ == "__main__":
    main(sys.argv)
