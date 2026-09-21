"""C70 etape 1 : M1-M4 par mode a partir des lignes `phase=line_calib` (docs/12_calibration_par_mode.md §3-§4).

Usage : python3 sweeps/analyse_c70_calibration.py results/c70_calib_raw_10y_20seeds.jsonl
        python3 sweeps/analyse_c70_calibration.py --selftest
"""
import json
import statistics
import sys

MIN_LINES = 20
MAX_SPREAD = 1.5


def quartiles(values):
    if len(values) < 2:
        return None
    q = statistics.quantiles(values, n=4)
    return q[2] - q[0]


def analyse(rows):
    """Une mediane par ligne (graine, mode, id) sur ses annees pleines, puis mediane entre lignes."""
    per_line = {}
    for r in rows:
        if r.get("phase") != "line_calib" or int(r["age"]) < 2:
            continue
        pred, n0, vehs = float(r["pred_p"]), int(r["trains0"]), int(r["vehs"])
        if pred <= 0 or n0 <= 0 or vehs <= 0:
            continue
        # GetProfitLastYear n'amortit rien ; profitAnnual retire l'amortissement predit. On retire
        # donc cet amortissement (par convoi initial) du realise avant de comparer.
        amort = float(r.get("pred_amort", 0))
        ratio = (float(r["real_p"]) * n0 / vehs - amort) / pred
        key = (r["seed"], r["mode"], r["line"])
        slot = per_line.setdefault(key, {"m1": [], "m2": []})
        slot["m1"].append(ratio)
        if vehs == n0:
            slot["m2"].append(ratio)
    modes = {}
    for (seed, mode, line), slot in per_line.items():
        entry = modes.setdefault(mode, {"m1": [], "m2": [], "line_years": 0, "seeds": set()})
        entry["m1"].append(statistics.median(slot["m1"]))
        if slot["m2"]:
            entry["m2"].append(statistics.median(slot["m2"]))
        entry["line_years"] += len(slot["m1"])
        entry["seeds"].add(seed)
    out = {}
    for mode, e in sorted(modes.items()):
        out[mode] = {
            "lines": len(e["m1"]), "lines_m2": len(e["m2"]), "line_years": e["line_years"],
            "seeds": len(e["seeds"]),
            "M1": statistics.median(e["m1"]), "M2": statistics.median(e["m2"]) if e["m2"] else None,
            "M4_iqr_m1": quartiles(e["m1"]),
        }
    return out


def verdict(out):
    thin = [m for m, v in out.items() if v["lines"] < MIN_LINES]
    if thin:
        return "C", "echantillon insuffisant : " + ", ".join(f"{m}={out[m]['lines']}" for m in thin)
    use_m2 = all(v["lines_m2"] >= MIN_LINES for v in out.values())
    key = "M2" if use_m2 else "M1"
    values = [v[key] for v in out.values() if v[key] and v[key] > 0]
    spread = max(values) / min(values)
    return ("A" if spread <= MAX_SPREAD else "B"), f"{key} max/min = {spread:.2f}"


def selftest():
    rows = []
    for i in range(25):
        rows.append({"phase": "line_calib", "seed": 1, "mode": "air", "line": str(i), "age": "2",
                     "pred_p": "100", "real_p": "140", "pred_amort": "20", "trains0": "1", "vehs": "1"})
        rows.append({"phase": "line_calib", "seed": 1, "mode": "road", "line": str(i), "age": "3",
                     "pred_p": "100", "real_p": "200", "trains0": "1", "vehs": "2"})
    rows.append({"phase": "line_calib", "seed": 1, "mode": "air", "line": "x", "age": "1",
                 "pred_p": "100", "real_p": "900", "trains0": "1", "vehs": "1"})
    out = analyse(rows)
    assert out["air"]["lines"] == 25 and abs(out["air"]["M1"] - 1.2) < 1e-9
    assert out["road"]["M1"] == 1.0 and out["road"]["M2"] is None
    assert verdict(out)[0] == "A", verdict(out)
    print("selftest passed: age>=2, par convoi, M2 flotte inchangee, verdict A")


def main():
    if sys.argv[1:] == ["--selftest"]:
        selftest()
        return
    rows = [json.loads(line) for line in open(sys.argv[1])]
    out = analyse(rows)
    for mode, v in out.items():
        print(mode, {k: (round(x, 3) if isinstance(x, float) else x) for k, x in v.items()})
    print("verdict", *verdict(out))


if __name__ == "__main__":
    main()
