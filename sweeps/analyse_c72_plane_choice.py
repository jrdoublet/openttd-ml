"""Analyse C72 : sonde passive du choix d'avion par route (C69 etape 1).

Lit le jsonl brut produit par `diag_c69_bottleneck_probe.py --raw <fichier.jsonl>` et publie :
- E1 par annee : calls, differ_roi, differ_c69 (depuis plane_choice_count)
- E2 sur les lignes plane_choice : mediane de p_C / r_C et de p_C / c_C ; part des cas ou p_C > avail ;
  les 10 couples (p_name -> r_name) les plus frequents
- E3 depuis line_calib (mode air, age >= 2, trains0 > 0, vehs == trains0, pred_p > 0) :
  par plane : nombre de lignes distinctes et mediane de (real_p - pred_amort)/pred_p,
  en reutilisant la logique de sweeps/analyse_c70_calibration.py (mediane par ligne puis entre lignes).

Usage :
  python3 sweeps/analyse_c72_plane_choice.py results/c69_raw_6y_5seeds.jsonl
  python3 sweeps/analyse_c72_plane_choice.py --selftest
"""
import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path


def to_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def to_int(val, default=0):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def median_or_none(values):
    cleaned = [v for v in values if v is not None]
    return statistics.median(cleaned) if cleaned else None


def analyse_e1(rows):
    """E1 par annee : calls, differ_roi, differ_c69 (depuis plane_choice_count)."""
    by_year = {}
    for r in rows:
        if r.get("phase") != "plane_choice_count":
            continue
        year = to_int(r.get("year"))
        if year not in by_year:
            by_year[year] = {"calls": 0, "differ_roi": 0, "differ_c69": 0}
        by_year[year]["calls"] += to_int(r.get("calls"))
        by_year[year]["differ_roi"] += to_int(r.get("differ_roi"))
        by_year[year]["differ_c69"] += to_int(r.get("differ_c69"))
    return {y: by_year[y] for y in sorted(by_year)}


def analyse_e2(rows):
    """E2 sur les lignes plane_choice : mediane de p_C / r_C et de p_C / c_C ;
    part des cas ou p_C > avail ; les 10 couples (p_name -> r_name) les plus frequents."""
    ratios_p_r = []
    ratios_p_c = []
    count_p_gt_avail = 0
    pair_counter = Counter()
    n_choices = 0

    for r in rows:
        if r.get("phase") != "plane_choice":
            continue
        n_choices += 1
        p_c = to_float(r.get("p_C"))
        r_c = to_float(r.get("r_C"))
        c_c = to_float(r.get("c_C"))
        avail = to_float(r.get("avail"))
        p_name = r.get("p_name", "")
        r_name = r.get("r_name", "")

        if r_c > 0:
            ratios_p_r.append(p_c / r_c)
        if c_c > 0:
            ratios_p_c.append(p_c / c_c)
        if p_c > avail:
            count_p_gt_avail += 1

        if p_name or r_name:
            pair_key = f"{p_name} -> {r_name}"
            pair_counter[pair_key] += 1

    share_p_gt_avail = (count_p_gt_avail / n_choices) if n_choices > 0 else None
    top_pairs = pair_counter.most_common(10)

    return {
        "n_choices": n_choices,
        "med_p_over_r_C": median_or_none(ratios_p_r),
        "med_p_over_c_C": median_or_none(ratios_p_c),
        "share_p_C_gt_avail": share_p_gt_avail,
        "top_pairs": top_pairs,
    }


def analyse_e3(rows):
    """E3 depuis line_calib (mode air, age >= 2, trains0 > 0, vehs == trains0, pred_p > 0) :
    par plane : nombre de lignes distinctes et mediane de (real_p - pred_amort)/pred_p,
    en reutilisant la logique de sweeps/analyse_c70_calibration.py (mediane par ligne puis entre lignes)."""
    per_line = {}
    for r in rows:
        if r.get("phase") != "line_calib":
            continue
        if r.get("mode") != "air":
            continue
        age = to_int(r.get("age"))
        if age < 2:
            continue
        trains0 = to_int(r.get("trains0"))
        vehs = to_int(r.get("vehs"))
        if trains0 <= 0 or vehs != trains0:
            continue
        pred_p = to_float(r.get("pred_p"))
        if pred_p <= 0:
            continue
        plane = r.get("plane")
        if plane is None or plane == "" or str(plane) == "-1":
            continue

        real_p = to_float(r.get("real_p"))
        pred_amort = to_float(r.get("pred_amort", 0))
        ratio = (real_p - pred_amort) / pred_p

        seed = r.get("seed")
        line_id = r.get("line")
        key = (seed, str(plane), line_id)
        per_line.setdefault(key, []).append(ratio)

    per_plane = {}
    for (seed, plane, line_id), ratios in per_line.items():
        line_med = statistics.median(ratios)
        per_plane.setdefault(plane, []).append(line_med)

    out = {}
    for plane, line_medians in sorted(per_plane.items(), key=lambda x: to_int(x[0])):
        out[plane] = {
            "distinct_lines": len(line_medians),
            "median_ratio": statistics.median(line_medians),
        }
    return out


def analyse_all(rows):
    return {
        "E1": analyse_e1(rows),
        "E2": analyse_e2(rows),
        "E3": analyse_e3(rows),
    }


def print_report(results):
    print("=== E1 : Compteurs de choix d'avion par annee ===")
    e1 = results["E1"]
    if not e1:
        print("  Aucune donnee plane_choice_count trouvee.")
    else:
        for year, counts in e1.items():
            print(f"  Annee {year}: calls={counts['calls']} differ_roi={counts['differ_roi']} differ_c69={counts['differ_c69']}")

    print("\n=== E2 : Desaccords de choix d'avion (plane_choice) ===")
    e2 = results["E2"]
    if e2["n_choices"] == 0:
        print("  Aucune donnee plane_choice trouvee.")
    else:
        print(f"  Nombre total de desaccords : {e2['n_choices']}")
        med_pr = f"{e2['med_p_over_r_C']:.3f}" if e2['med_p_over_r_C'] is not None else "N/A"
        med_pc = f"{e2['med_p_over_c_C']:.3f}" if e2['med_p_over_c_C'] is not None else "N/A"
        share = f"{e2['share_p_C_gt_avail'] * 100:.1f}% ({e2['share_p_C_gt_avail']:.3f})" if e2['share_p_C_gt_avail'] is not None else "N/A"
        print(f"  Mediane p_C / r_C : {med_pr}")
        print(f"  Mediane p_C / c_C : {med_pc}")
        print(f"  Part p_C > avail  : {share}")
        print("  Top couples (p_name -> r_name) :")
        for rank, (pair, cnt) in enumerate(e2["top_pairs"], 1):
            print(f"    {rank}. {pair} : {cnt}")

    print("\n=== E3 : Calibration par type d'avion (line_calib) ===")
    e3 = results["E3"]
    if not e3:
        print("  Aucune ligne d'avion mure eligible trouvee.")
    else:
        for plane, data in e3.items():
            print(f"  Plane {plane}: lignes={data['distinct_lines']} mediane_ratio={data['median_ratio']:.3f}")


def run_selftest():
    sample_rows = [
        # E1 rows
        {"phase": "plane_choice_count", "seed": 100, "year": "1971", "calls": "10", "differ_roi": "4", "differ_c69": "2"},
        {"phase": "plane_choice_count", "seed": 100, "year": "1972", "calls": "20", "differ_roi": "6", "differ_c69": "3"},
        {"phase": "plane_choice_count", "seed": 42, "year": "1971", "calls": "5", "differ_roi": "1", "differ_c69": "1"},

        # E2 rows
        {"phase": "plane_choice", "p_name": "PlaneA", "r_name": "PlaneB", "c_name": "PlaneB", "p_C": "200", "r_C": "100", "c_C": "100", "avail": "150"},
        {"phase": "plane_choice", "p_name": "PlaneA", "r_name": "PlaneB", "c_name": "PlaneA", "p_C": "300", "r_C": "100", "c_C": "300", "avail": "400"},
        {"phase": "plane_choice", "p_name": "PlaneC", "r_name": "PlaneD", "c_name": "PlaneD", "p_C": "100", "r_C": "100", "c_C": "100", "avail": "50"},

        # E3 rows
        # Plane 10, line 1 (two mature years)
        {"phase": "line_calib", "seed": 1, "mode": "air", "plane": "10", "line": "1", "age": "2", "trains0": "1", "vehs": "1", "pred_p": "100", "real_p": "150", "pred_amort": "20"},
        {"phase": "line_calib", "seed": 1, "mode": "air", "plane": "10", "line": "1", "age": "3", "trains0": "1", "vehs": "1", "pred_p": "100", "real_p": "170", "pred_amort": "20"},
        # Plane 10, line 2 (one mature year)
        {"phase": "line_calib", "seed": 1, "mode": "air", "plane": "10", "line": "2", "age": "2", "trains0": "2", "vehs": "2", "pred_p": "100", "real_p": "130", "pred_amort": "10"},
        # Ignored rows for E3:
        {"phase": "line_calib", "seed": 1, "mode": "air", "plane": "10", "line": "3", "age": "1", "trains0": "1", "vehs": "1", "pred_p": "100", "real_p": "900"}, # age < 2
        {"phase": "line_calib", "seed": 1, "mode": "air", "plane": "10", "line": "4", "age": "2", "trains0": "1", "vehs": "2", "pred_p": "100", "real_p": "200"}, # vehs != trains0
        {"phase": "line_calib", "seed": 1, "mode": "road", "plane": "10", "line": "5", "age": "2", "trains0": "1", "vehs": "1", "pred_p": "100", "real_p": "200"}, # mode != air
        {"phase": "line_calib", "seed": 1, "mode": "air", "plane": "-1", "line": "6", "age": "2", "trains0": "1", "vehs": "1", "pred_p": "100", "real_p": "200"}, # plane == -1
    ]

    res = analyse_all(sample_rows)
    e1 = res["E1"]
    assert e1[1971]["calls"] == 15
    assert e1[1971]["differ_roi"] == 5
    assert e1[1971]["differ_c69"] == 3
    assert e1[1972]["calls"] == 20
    assert e1[1972]["differ_roi"] == 6
    assert e1[1972]["differ_c69"] == 3

    e2 = res["E2"]
    assert e2["n_choices"] == 3
    assert abs(e2["med_p_over_r_C"] - 2.0) < 1e-9
    assert abs(e2["med_p_over_c_C"] - 1.0) < 1e-9
    assert abs(e2["share_p_C_gt_avail"] - (2.0 / 3.0)) < 1e-9
    assert e2["top_pairs"][0] == ("PlaneA -> PlaneB", 2)
    assert e2["top_pairs"][1] == ("PlaneC -> PlaneD", 1)

    e3 = res["E3"]
    assert "10" in e3
    assert e3["10"]["distinct_lines"] == 2
    # line 1: ratios = [ (150-20)/100 = 1.3, (170-20)/100 = 1.5 ] -> median = 1.4
    # line 2: ratios = [ (130-10)/100 = 1.2 ] -> median = 1.2
    # plane 10 median = median([1.4, 1.2]) = 1.3
    assert abs(e3["10"]["median_ratio"] - 1.3) < 1e-9

    print("selftest passed: E1, E2, E3 assertions verified successfully.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, help="Fichier jsonl brut (--raw)")
    parser.add_argument("--json", action="store_true", help="Format de sortie JSON")
    parser.add_argument("--selftest", action="store_true", help="Lance les tests unitaires internes")
    args = parser.parse_args()

    if args.selftest:
        run_selftest()
        return

    if not args.input:
        parser.error("Fichier d'entree jsonl requis (ou --selftest)")

    if not args.input.exists():
        parser.error(f"Fichier introuvable : {args.input}")

    rows = []
    with open(args.input, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    results = analyse_all(rows)
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_report(results)


if __name__ == "__main__":
    main()
