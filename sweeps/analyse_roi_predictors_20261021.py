#!/usr/bin/env python3
"""Predictors of mature line ROI, using only historical calibration engine logs."""
import argparse
import hashlib
import json
import math
import os
import statistics
from collections import Counter, defaultdict
from glob import glob

import numpy as np
from analyse_calibration_projets import KV_RE, LINE_RE, SEED_RE, open_text


def num(s):
    try:
        v = float(s)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def med(a):
    return statistics.median(a) if a else None


_ROI_EVENTS = {"PROJECT_CHOSEN", "AIR_BUILD", "RAIL_BUILD", "ROAD_BUILD", "LINE_REVENUE"}


def _relevant_digest(path):
    """Digest only ROI source events; reject divergent .log/.log.gz copies."""
    checksum = hashlib.sha256()
    with open_text(path) as stream:
        for raw in stream:
            matched = LINE_RE.search(raw)
            if matched is not None and matched.group(4) in _ROI_EVENTS:
                checksum.update(matched.group(0).encode("utf-8"))
                checksum.update(b"\n")
    return checksum.digest()


def _unique_game_logs(folder):
    """Keep one representation per seed/repetition, per campaign directory."""
    selected = {}
    canonical_names = {}
    for path in sorted(glob(os.path.join(folder, "*.log")) + glob(os.path.join(folder, "*.log.gz"))):
        basename = os.path.basename(path)
        stem = basename[:-3] if basename.endswith(".gz") else basename
        match = SEED_RE.search(stem)
        if match is None:
            continue
        # Numeric spelling is not part of a game's identity. Without this
        # guard, seed1/seed01 or r0/r00 become independent ROI observations.
        identity = (stem[:match.start()], int(match.group(1)), int(match.group(2)))
        previous = canonical_names.setdefault(identity, stem)
        if previous != stem:
            raise ValueError(f"identite de partie ROI ambigue : {previous} et {stem}")
        if stem in selected:
            current = selected[stem]
            if _relevant_digest(current) != _relevant_digest(path):
                raise ValueError(f"copies de journal ROI contradictoires : {current} et {path}")
            if path.endswith(".log"):
                selected[stem] = path
        else:
            selected[stem] = path
    return [selected[key] for key in sorted(selected)]


def parse(folder, arm):
    items = []
    ct = Counter()
    for file in _unique_game_logs(folder):
        match = SEED_RE.search(os.path.basename(file).replace(".gz", ""))
        if match is None:
            continue
        seed = int(match.group(1))
        chosen, builds, observed = {}, {}, defaultdict(list)
        ct["games"] += 1
        with open_text(file) as log:
            for raw in log:
                m = LINE_RE.search(raw)
                if m is None:
                    continue
                tag, year = m.group(4), int(m.group(1))
                if tag not in ("PROJECT_CHOSEN", "AIR_BUILD", "RAIL_BUILD", "ROAD_BUILD", "LINE_REVENUE"):
                    continue
                kv = dict(KV_RE.findall(m.group(5)))
                if tag == "PROJECT_CHOSEN":
                    chosen[(kv.get("mode"), kv.get("src"), kv.get("dst"))] = kv
                elif tag.endswith("_BUILD"):
                    mode = tag.split("_")[0].lower()
                    ct["built_" + mode] += 1
                    p = chosen.get((mode, kv.get("src"), kv.get("dst")))
                    if not p:
                        ct["unmatched_choice_" + mode] += 1
                        continue
                    cost, pred_profit, physical, dist = (num(p.get("cost")), num(p.get("profit")),
                                                         num(kv.get("cost")), num(kv.get("dist")))
                    if (cost is None or cost <= 0 or pred_profit is None or pred_profit <= 0
                            or dist is None):
                        ct["invalid_prediction"] += 1
                        continue
                    denominator = cost if mode == "air" else physical
                    if denominator is None or denominator <= 0:
                        ct["invalid_physical_cost"] += 1
                        continue
                    n0 = num(kv.get("planes") or kv.get("trains") or kv.get("vehicles")) or 1.
                    builds[kv["line"]] = {
                        "seed": seed, "arm": arm, "line": kv["line"], "mode": mode,
                        "cargo": kv.get("cargo", "PASS"), "year": year,
                        "src_tile": num(p.get("src")),
                        "dst_tile": num(p.get("dst")),
                        "dist": dist, "capital": cost, "pred_profit": pred_profit,
                        "real_capital": denominator, "n0": n0,
                        "rank": num(p.get("rank")) or 0.,
                        "project_score": num(p.get("roi")) or 0.,
                        "subtype": kv.get("arm", p.get("kind", "unknown")),
                        "reuse": kv.get("reuse", "0"),
                    }
                    ct["matched_" + mode] += 1
                else:
                    if (num(kv.get("age")) or 0.) < 2.:
                        continue
                    b = builds.get(kv.get("line"))
                    if b is None:
                        continue
                    rv, nv = num(kv.get("real_prof")), num(kv.get("vehs"))
                    if rv is not None and nv is not None and nv > 0:
                        observed[kv["line"]].append(rv * b["n0"] / nv)
        for line, b in builds.items():
            if not observed[line]:
                ct["no_mature"] += 1
                continue
            b["n_years"] = len(observed[line])
            b["real_profit"] = med(observed[line])
            b["roi_pred"] = b["pred_profit"] / b["capital"] * 100.
            b["roi_real"] = b["real_profit"] / b["real_capital"] * 100.
            b["profit_ratio"] = b["real_profit"] / b["pred_profit"]
            items.append(b)
            ct["mature_" + b["mode"]] += 1
    return items, dict(ct)


def quartiles(rows, field):
    a = sorted(rows, key=lambda r: r[field])
    result = []
    for k in range(4):
        sub = a[k*len(a)//4:(k+1)*len(a)//4]
        result.append({
            "quartile": k+1, "n": len(sub),
            "roi_pred_pct": round(med([r["roi_pred"] for r in sub]), 2),
            "roi_real_pct": round(med([r["roi_real"] for r in sub]), 2),
            "profit_real_over_pred": round(med([r["profit_ratio"] for r in sub]), 3),
            "distance": round(med([r["dist"] for r in sub]), 1),
        })
    return result


FEATURE_SETS = {
    "affine_roi": ("roi",),
    "roi_quadratic": ("roi", "roi2"),
    "plus_distance": ("roi", "roi2", "dist", "roi_dist"),
    "plus_cargo": ("roi", "roi2", "cargo", "roi_cargo"),
    "plus_capital": ("roi", "roi2", "capital", "roi_capital"),
    "plus_year": ("roi", "roi2", "year", "roi_year"),
    "plus_rank": ("roi", "roi2", "rank", "roi_rank"),
    "plus_subtype": ("roi", "roi2", "subtype", "roi_subtype", "reuse"),
    "all_available": ("roi", "roi2", "dist", "roi_dist", "cargo", "roi_cargo",
                      "capital", "roi_capital", "year", "roi_year", "rank",
                      "subtype", "roi_subtype", "reuse"),
}


def basic(r):
    roi = r["roi_pred"]
    return {
        "roi": roi,
        "roi2": roi ** 2,
        "dist": r["dist"],
        "roi_dist": roi * r["dist"],
        "capital": math.log(max(r["capital"], 1)),
        "roi_capital": roi * math.log(max(r["capital"], 1)),
        "year": r["year"] - 1970,
        "roi_year": roi * (r["year"] - 1970),
        "rank": min(r["rank"], 12),
        "roi_rank": roi * min(r["rank"], 12),
    }


def matrix(train, test, spec):
    data = train + test
    n = len(train)
    baseline = [basic(r) for r in data]
    arrays = [np.ones(len(data))]
    for f in spec:
        if f in baseline[0]:
            vec = np.array([x[f] for x in baseline])
            if vec[:n].std() > 1e-7:
                arrays.append((vec - vec[:n].mean()) / vec[:n].std())
        else:
            interaction = f.startswith("roi_")
            col = f[4:] if interaction else f
            levels = Counter(str(r[col]) for r in train)
            baseline_level = sorted(levels)[0]
            for level, count in sorted(levels.items()):
                if level == baseline_level or count < 12:
                    continue
                vec = np.array([float(str(r[col]) == level) for r in data])
                if interaction:
                    vec *= np.array([r["roi_pred"] for r in data])
                if vec[:n].std() > 1e-7:
                    arrays.append((vec - vec[:n].mean()) / vec[:n].std())
    return np.array(arrays).T


def predict(train, test, spec):
    m = matrix(train, test, spec)
    n = len(train)
    y = np.array([r["roi_real"] for r in train])
    reg = np.eye(m.shape[1]) * (n * .05)
    reg[0, 0] = 0.
    beta = np.linalg.solve(m[:n].T @ m[:n] + reg, m[:n].T @ y)
    return m[n:] @ beta


def run_cv(data):
    out = {}
    for mode in sorted(set(r["mode"] for r in data)):
        rows = [r for r in data if r["mode"] == mode and r["arm"] == "duel"]
        if len(rows) < 30:
            continue
        names = ("raw", "factor") + tuple(FEATURE_SETS)
        forecasts = {name: {} for name in names}
        seeds = sorted(set(r["seed"] for r in rows))
        for fold in range(5):
            held = set(seeds[fold::5])
            train = [r for r in rows if r["seed"] not in held]
            test = [r for r in rows if r["seed"] in held]
            scale = med([r["roi_real"] / r["roi_pred"] for r in train])
            for r in test:
                key = (r["seed"], r["line"])
                forecasts["raw"][key] = r["roi_pred"]
                forecasts["factor"][key] = r["roi_pred"] * scale
            for name, spec in FEATURE_SETS.items():
                estimates = predict(train, test, spec)
                for r, v in zip(test, estimates):
                    forecasts[name][(r["seed"], r["line"])] = float(v)
        errors = {}
        for name, predictions in forecasts.items():
            residual = np.array([predictions[(r["seed"], r["line"])]-r["roi_real"]
                                 for r in rows])
            per_seed_rho = []
            for seed in seeds:
                one = [r for r in rows if r["seed"] == seed]
                if len(one) < 4:
                    continue
                a = np.array([r["roi_real"] for r in one])
                b = np.array([predictions[(r["seed"], r["line"])] for r in one])
                if a.std() > 1.e-7 and b.std() > 1.e-7:
                    # Spearman ranks for within-game selected-line prioritization.
                    ra = np.argsort(np.argsort(a))
                    rb = np.argsort(np.argsort(b))
                    per_seed_rho.append(float(np.corrcoef(ra, rb)[0, 1]))
            errors[name] = {
                "mae_roi_points": round(float(np.mean(abs(residual))), 2),
                "median_abs_roi_points": round(float(np.median(abs(residual))), 2),
                "median_bias_points": round(float(np.median(residual)), 2),
                "median_within_seed_rank_rho": round(med(per_seed_rho), 3) if per_seed_rho else None,
            }
        # Cluster-bootstrap of improvement versus a nonlinear ROI-only model.
        rng = np.random.default_rng(20261021)
        gains = {}
        ref = forecasts["roi_quadratic"]
        for name, predictions in forecasts.items():
            if name == "roi_quadratic":
                continue
            per_seed_delta = {}
            for seed in seeds:
                selected = [r for r in rows if r["seed"] == seed]
                per_seed_delta[seed] = np.mean([
                    abs(ref[(r["seed"], r["line"])] - r["roi_real"]) -
                    abs(predictions[(r["seed"], r["line"])] - r["roi_real"])
                    for r in selected
                ])
            means = np.array([per_seed_delta[s] for s in seeds])
            samps = rng.integers(0, len(means), size=(1500, len(means)))
            samples = np.mean(means[samps], axis=1)
            gains[name] = {
                "mean_gain_roi_points_per_seed": round(float(np.mean(means)), 2),
                "ci95": [round(float(x), 2) for x in np.percentile(samples, [2.5, 97.5])],
                "positive_seeds": int((means > 0).sum()),
                "seeds": len(seeds),
            }
        bytype = {}
        for feature in ("cargo", "subtype", "reuse"):
            vals = defaultdict(list)
            for r in rows:
                vals[str(r[feature])].append(r)
            bytype[feature] = {
                key: {"n": len(part),
                      "roi_pred_pct": round(med([r["roi_pred"] for r in part]), 1),
                      "roi_real_pct": round(med([r["roi_real"] for r in part]), 1),
                      "profit_ratio": round(med([r["profit_ratio"] for r in part]), 3)}
                for key, part in vals.items() if len(part) >= 12
            }
        out[mode] = {
            "lines": len(rows), "seeds": len(seeds),
            "cv": errors,
            "gains_vs_roi_quadratic": gains,
            "by_predicted_roi_quartile": quartiles(rows, "roi_pred"),
            "by_realized_roi_quartile": quartiles(rows, "roi_real"),
            "by_type": bytype,
        }
    return out


def format_report(out, stats):
    lines = [
        "# Variables predictives du ROI annuel, calibration PC 40x10",
        "",
        "Methode : une observation par ligne, profit median des annees age >=2,",
        "normalise a la flotte initiale, divise par capital physique RAIL/ROAD",
        "ou par le devis AIR (aucun cout physique AIR dans les journaux).",
        "Prediction de depart : profit prevu / capital prevu, en pourcentage annuel.",
        "Evaluation supervisee : 5 plis par graines disjointes, bras duel uniquement.",
        "Modeles ridge fixes, sans optimisation de l'hyperparametre sur le test.",
        "Les variables subtype/reuse viennent du plan journalise a la construction ;",
        "leur disponibilite au choix doit etre verifiee dans le constructeur.",
        "",
        "Attention : correction ne vaut que pour les lignes construites, avec suivi",
        "jusqu'a age 2. Quartiler sur le ROI reel amplifie la regression vers",
        "la moyenne par construction. Aucune causalite n'est demontree ici.",
    ]
    for mode, x in out.items():
        lines += ["", "## " + mode.upper() + " : " + str(x["lines"]) + " lignes en duel",
                  "", "| Modele | MAE ROI (points) | Median abs. (points) | Biais median (points) | Rang intra-graine rho |",
                  "|---|---:|---:|---:|---:|"]
        for name, val in x["cv"].items():
            lines.append("| {} | {} | {} | {} | {} |".format(name, val["mae_roi_points"],
                         val["median_abs_roi_points"], val["median_bias_points"],
                         val["median_within_seed_rank_rho"]))
        lines += ["", "### Effets additionnels vs ROI seul quadratique (graines bootstrappees)", "",
                  "| Ajout | Gain MAE moyen par graine (points, positif=mieux) | IC95 | Graines favorables |",
                  "|---|---:|---:|---:|"]
        for name, val in x["gains_vs_roi_quadratic"].items():
            lines.append("| {} | {} | {} a {} | {}/{} |".format(
                name, val["mean_gain_roi_points_per_seed"], *val["ci95"],
                val["positive_seeds"], val["seeds"]))
        for typ in ("by_predicted_roi_quartile", "by_realized_roi_quartile"):
            lines += ["", "### " + typ, "",
                      "| Quartile | N lignes | ROI prevu % | ROI reel % | Profit reel/predit | Distance med. |",
                      "|---|---:|---:|---:|---:|---:|"]
            for r in x[typ]:
                lines.append("| Q{} | {} | {} | {} | {} | {} |".format(
                    r["quartile"], r["n"], r["roi_pred_pct"], r["roi_real_pct"],
                    r["profit_real_over_pred"], r["distance"]))
        lines += ["", "### Sous-groupes descriptifs", ""]
        for field, vals in x["by_type"].items():
            if len(vals)>1:
                lines += ["- " + field + " : " + "; ".join("{}: {}".format(k, v)
                          for k, v in sorted(vals.items())), ""]
    lines += ["", "## Couverture et limites", "", json.dumps(stats, indent=2),
              "", "La validation par graines isole les parties, mais ne corrige pas",
              "le biais de selection du catalogue. Les conditions de production,",
              "saturation, demande concurrente, stations, vitesse et utilisation",
              "ne sont pas journalisees au moment du choix dans ces traces."]
    return "\n".join(lines) + "\n"


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--campaign", action="append", required=True)
    ap.add_argument("--out-prefix", required=True)
    opts=ap.parse_args()
    rows=[]; stats={}
    for spec in opts.campaign:
        arm, folder = spec.split("=", 1)
        data, counts = parse(folder, arm)
        rows.extend(data)
        stats[arm] = counts
        print(arm, len(data), counts)
    out=run_cv(rows)
    result={"stats": stats, "by_mode": out}
    os.makedirs(os.path.dirname(opts.out_prefix) or ".", exist_ok=True)
    with open(opts.out_prefix+".json","w",encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
    with open(opts.out_prefix+".md","w",encoding="utf-8") as fh:
        fh.write(format_report(out, stats))
    for mode, x in out.items():
        print(mode, x["cv"])
        print(mode, "by ROI:", x["by_predicted_roi_quartile"])


if __name__=="__main__":
    main()
