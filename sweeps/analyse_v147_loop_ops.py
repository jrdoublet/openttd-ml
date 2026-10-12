"""LOOP_OPS apparies d'une campagne C66.4 a deux bras (meme source, reglage different).

Usage : python3 -m sweeps.analyse_v147_loop_ops results/<campagne>.json --out <json>
Lit les journaux moteur `<campagne>_engine/<policy>_seed<N>_r0.log` et compare les
opcodes executes par annee civile close (la derniere annee est censuree : les
compteurs C121 se vident au nouvel an suivant).
"""

import argparse
import json
from pathlib import Path
from statistics import mean

from sweeps.analyse_ac_loop_opcode import logfile_stats
from sweeps.compare_cd_cross_tree_c66 import ci


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("result", type=Path)
    parser.add_argument("--reference", default="v147_off")
    parser.add_argument("--variant", default="v147_on")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.result.read_text(encoding="utf-8"))
    engine = args.result.with_name(args.result.stem + "_engine")
    years = [str(1970 + i) for i in range(int(data["years"]) - 1)]
    seeds = sorted({g["seed"] for g in data["games"]})
    stats = {}
    for seed in seeds:
        pair = {}
        for policy in (args.reference, args.variant):
            log = engine / f"{policy}_seed{seed}_r0.log"
            assert log.is_file() and log.stat().st_size > 0, log
            pair[policy] = logfile_stats(log)
            for y in years:
                assert pair[policy].get(y) and pair[policy][y]["loop_executed_ops"] > 0, (log, y)
        stats[seed] = pair
    out = {"campaign": data.get("campaign_id", args.result.stem), "n": len(seeds),
           "seeds": seeds, "complete_years": years, "windows": {}}
    for window in ([years[0], years[1]], years):
        name = f"{window[0]}-{window[-1]}"
        diffs = [sum(stats[s][args.variant][y]["loop_executed_ops"]
                     - stats[s][args.reference][y]["loop_executed_ops"] for y in window)
                 for s in seeds]
        refs = [sum(stats[s][args.reference][y]["loop_executed_ops"] for y in window)
                for s in seeds]
        out["windows"][name] = {
            "mean_delta": mean(diffs),
            "mean_reference": mean(refs),
            "ratio_of_means": mean(diffs) / mean(refs),
            "bootstrap_95_ci": ci(diffs),
            "increases": sum(d > 0 for d in diffs),
            "decreases": sum(d < 0 for d in diffs),
            "ties": sum(d == 0 for d in diffs),
            "by_seed_delta": {str(s): d for s, d in zip(seeds, diffs)},
        }
    args.out.write_text(json.dumps(out, indent=2), encoding="utf-8")
    for name, w in out["windows"].items():
        print(f"{name}: delta moyen {w['mean_delta']:+.0f} ({100 * w['ratio_of_means']:+.4f} %) "
              f"IC95 [{w['bootstrap_95_ci'][0]:+.0f} ; {w['bootstrap_95_ci'][1]:+.0f}] "
              f"hausses/baisses/egalites {w['increases']}/{w['decreases']}/{w['ties']}")


if __name__ == "__main__":
    main()
