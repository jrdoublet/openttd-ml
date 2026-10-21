#!/usr/bin/env python3
"""V307 : lecture des sondes de longs traces (V307_ARM) et des autopsies d'ABND (V307_AUTOPSY).

Usage : python3 sweeps/diag_v307_long_paths.py results/<campagne>_engine [...] [--json out.json]

Pour chaque paire (graine, type, a, b) : bras base (recherche de production, budget 20k),
coarse (A* grossier par blocs) et guided (production guidee par le couloir grossier).
Tables par type x tranche : reussite, reussite au plafond actuel (cap_ok), iterations, opcodes,
jours ; precision du grossier (longueur predite / longueur reelle, correlation des couts) ;
guided contre base sur les memes paires. Les autopsies sont comptees par issue aller/inverse.
"""
import argparse
import gzip
import json
import math
import re
import statistics
import sys
from pathlib import Path

LINE = re.compile(r"\[0\] \[I\] OPEX (\d+)-(\d+)-(\d+) (V307_ARM|V307_AUTOPSY|V307_START) (.*)$")
BINS = ["120-179", "180-249", "250-349"]
SIDE = 8


def parse_fields(text):
    out = {}
    for tok in text.split():
        if "=" in tok:
            k, v = tok.split("=", 1)
            try:
                out[k] = int(v)
            except ValueError:
                out[k] = v
    return out


def read_log(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            m = LINE.search(raw)
            if m:
                f = parse_fields(m.group(5))
                f["year"] = int(m.group(1))
                yield m.group(4), f


def seed_of(path):
    m = re.search(r"seed(\d+)", path.name)
    return int(m.group(1)) if m else -1


def med(xs):
    return statistics.median(xs) if xs else None


def pearson(xs, ys):
    if len(xs) < 3:
        return None
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def collect(dirs):
    pairs, autopsies, starts = {}, [], []
    for d in dirs:
        camp = Path(d).name.replace("_engine", "")
        for path in sorted(Path(d).glob("*.log*")):
            seed = seed_of(path)
            for kind, f in read_log(path):
                if kind == "V307_START":
                    starts.append(dict(f, campaign=camp, seed=seed))
                    continue
                if kind == "V307_AUTOPSY":
                    autopsies.append(dict(f, campaign=camp, seed=seed))
                    continue
                key = (camp, seed, f.get("kind"), f.get("a"), f.get("b"))
                p = pairs.setdefault(key, {"campaign": camp, "seed": seed, "kind": f.get("kind"),
                                           "dist": f.get("dist"), "bin": f.get("bin"), "year": f["year"]})
                p[f["arm"]] = f
    return list(pairs.values()), autopsies, starts


def arm_table(pairs, arm):
    rows = []
    for kind in ("pax", "freight"):
        for b in range(3):
            sel = [p for p in pairs if p["kind"] == kind and p["bin"] == b and arm in p]
            if not sel:
                continue
            ok = [p[arm] for p in sel if p[arm]["outcome"] == "OK"]
            rows.append({
                "kind": kind, "bin": BINS[b], "n": len(sel), "ok": len(ok),
                "cap_ok": sum(1 for p in sel if p[arm].get("cap_ok") == 1),
                "iters_med": med([r["iters"] for r in ok]), "iters_max": max([r["iters"] for r in ok], default=None),
                "ops_med_k": med([r["ops"] / 1000 for r in ok]),
                "days_med": med([r["days"] for r in ok]), "days_max": max([r["days"] for r in ok], default=None),
                "len_over_dist": med([r["len"] / p["dist"] for p in sel for r in [p[arm]] if r["outcome"] == "OK" and p["dist"]]),
                "segments_max": max([p[arm].get("segments", 0) for p in sel], default=None),
            })
    return rows


def coarse_table(pairs):
    sel = [p for p in pairs if "base" in p and "coarse" in p and p["base"]["outcome"] == "OK" and p["coarse"]["outcome"] == "OK"]
    pred_len = [p["coarse"]["cost"] / 10 for p in sel]
    real_len = [p["base"]["len"] for p in sel]
    real_cost = [p["base"]["cost"] for p in sel]
    ratio = [r / pl for r, pl in zip(real_len, pred_len) if pl > 0]
    cost_per_tile = [p["base"]["cost"] / p["base"]["len"] for p in sel if p["base"]["len"] > 0]
    excess = [c - 100 * l for c, l in zip(real_cost, real_len)]
    coarse_excess = [p["coarse"]["cost"] / 10 - p["dist"] for p in sel]
    nopa = [p for p in pairs if "coarse" in p and p["coarse"]["outcome"] != "OK"]
    return {
        "n": len(sel), "coarse_nopa": len(nopa),
        "coarse_nopa_base_ok": sum(1 for p in nopa if "base" in p and p["base"]["outcome"] == "OK"),
        "real_len_over_coarse_len_med": med(ratio),
        "corr_coarse_cost_real_cost": pearson([p["coarse"]["cost"] for p in sel], real_cost),
        "corr_coarse_excess_real_excess": pearson(coarse_excess, excess),
        "real_cost_per_tile_med": med(cost_per_tile),
        "coarse_ops_med_k": med([p["coarse"]["ops"] / 1000 for p in pairs if "coarse" in p]),
    }


def guided_vs_base(pairs):
    sel = [p for p in pairs if "base" in p and "guided" in p]
    both = [p for p in sel if p["base"]["outcome"] == "OK" and p["guided"]["outcome"] == "OK"]
    return {
        "n": len(sel),
        "base_ok": sum(1 for p in sel if p["base"]["outcome"] == "OK"),
        "guided_ok": sum(1 for p in sel if p["guided"]["outcome"] == "OK"),
        "both_ok": len(both),
        "cost_ratio_med": med([p["guided"]["cost"] / p["base"]["cost"] for p in both if p["base"]["cost"] > 0]),
        "guided_cheaper": sum(1 for p in both if p["guided"]["cost"] < p["base"]["cost"]),
        "ops_ratio_med": med([p["guided"]["ops"] / p["base"]["ops"] for p in both if p["base"]["ops"] > 0]),
        "iters_ratio_med": med([p["guided"]["iters"] / p["base"]["iters"] for p in both if p["base"]["iters"] > 0]),
    }


def autopsy_table(autopsies):
    out = {}
    for a in autopsies:
        k = (a.get("dir"), a.get("out"), a.get("join"))
        out.setdefault(k, []).append(a)
    rows = []
    for (d, o, j), xs in sorted(out.items(), key=lambda kv: str(kv[0])):
        rows.append({"dir": d, "out": o, "join": j, "n": len(xs),
                     "iters_med": med([x["iters"] for x in xs]), "days_med": med([x["days"] for x in xs]),
                     "dist_med": med([x["dist"] for x in xs if isinstance(x.get("dist"), int)])})
    # Croisement aller x inverse par recherche (meme graine, src, dst, spent)
    joint = {}
    for a in autopsies:
        key = (a["campaign"], a["seed"], a.get("src"), a.get("dst"), a.get("spent"), a["year"])
        joint.setdefault(key, {})[a.get("dir")] = a.get("out")
    cross = {}
    for v in joint.values():
        k = (v.get("fwd"), v.get("rev"))
        cross[str(k)] = cross.get(str(k), 0) + 1
    return {"rows": rows, "fwd_x_rev": cross, "searches": len(joint)}


def fmt(v):
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--json")
    args = ap.parse_args()
    pairs, autopsies, starts = collect(args.dirs)
    report = {"starts": len(starts), "pairs": len(pairs),
              "base": arm_table(pairs, "base"), "guided": arm_table(pairs, "guided"),
              "coarse": coarse_table(pairs), "guided_vs_base": guided_vs_base(pairs),
              "noplan": sum(1 for p in pairs if "plans" in p),
              "autopsy": autopsy_table(autopsies) if autopsies else None}
    print(f"sondes={len(starts)} paires={len(pairs)} sans quai={report['noplan']}")
    for arm in ("base", "guided"):
        print(f"\n== {arm}")
        cols = ["kind", "bin", "n", "ok", "cap_ok", "iters_med", "iters_max", "ops_med_k", "days_med", "days_max", "len_over_dist", "segments_max"]
        print(" | ".join(cols))
        for r in report[arm]:
            print(" | ".join(fmt(r[c]) for c in cols))
    print("\n== coarse", json.dumps(report["coarse"], default=fmt))
    print("== guided_vs_base", json.dumps(report["guided_vs_base"], default=fmt))
    if report["autopsy"]:
        print("\n== autopsies", report["autopsy"]["searches"], "recherches ; aller x inverse :", report["autopsy"]["fwd_x_rev"])
        for r in report["autopsy"]["rows"]:
            print(" ", r)
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=1, default=str))


if __name__ == "__main__":
    sys.exit(main())
