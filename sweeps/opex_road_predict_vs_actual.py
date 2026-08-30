"""Predit vs reel des lignes ROUTIERES deja construites.

Item 1 bis.1 : le plancher ROAD_MIN_PROFIT_ANNUAL = 1000 coupait, sur n = 1, une ligne
pax predite a ~1000 et payee 7-11 k. Ce script ne relance pas OpenTTD : il lit les
campagnes qui ont pose OF/OZ, pour sortir de n = 1 sans recalibrer.

Sources : docs/opex_join_factor_20y_10seeds.json (10 graines, n pax le plus large)
et docs/opex_road_20y_42.json (premiere campagne route, deux pax dont une morte).
Le fret est le temoin : meme ROAD_SPEED_EFFICIENCY_PCT, pas de TOWN_CATCHMENT.
"""
import json
from pathlib import Path

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
SOURCES = (
    ROOT / "docs" / "opex_join_factor_20y_10seeds.json",
    ROOT / "docs" / "opex_road_20y_42.json",
)
FLOOR_SOURCE = ROOT / "docs" / "opex_join_parallel_20y_5seeds.json"
RESULT = ROOT / "docs" / "opex_road_predict_vs_actual.json"


def median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def full_years(series):
    if not isinstance(series, dict) or not series:
        return []
    years = sorted(series, key=int)
    return [series[y] for y in years[1:]]  # saute l'annee partielle de mise en service


def collect_lines(path):
    data = json.loads(path.read_text())
    rows = []
    for run in data.get("runs") or []:
        for line in run.get("lines") or []:
            if line.get("mode") != "road":
                continue
            pred = line.get("predicted") or {}
            full = full_years(line.get("actual_series") or {})
            profits = [row["profit"] for row in full if row.get("profit") is not None]
            revenues = [row["revenue"] for row in full if row.get("revenue") is not None]
            pred_profit = pred.get("profitAnnual")
            pred_rev = pred.get("revenueAnnual")
            med_profit = median(profits)
            med_rev = median(revenues)
            rows.append({
                "source": path.name,
                "seed": run.get("seed"),
                "line_index": line.get("line_index"),
                "year_built": line.get("year_built"),
                "kind": pred.get("kind"),
                "distance": line.get("distance") or pred.get("distance"),
                "monthly": pred.get("monthly"),
                "pred_profit": pred_profit,
                "pred_revenue": pred_rev,
                "med_profit": med_profit,
                "med_revenue": med_rev,
                "n_full_years": len(profits),
                "profit_ratio": (med_profit / pred_profit) if pred_profit and med_profit is not None else None,
                "revenue_ratio": (med_rev / pred_rev) if pred_rev and med_rev else None,
            })
    return rows


def summarise(rows, kind):
    xs = [row for row in rows
          if row["kind"] == kind and row["n_full_years"] >= 2 and row["profit_ratio"] is not None]
    ratios_p = [row["profit_ratio"] for row in xs]
    ratios_r = [row["revenue_ratio"] for row in xs if row["revenue_ratio"] is not None]
    return {
        "n": len(xs),
        "median_profit_ratio": median(ratios_p),
        "min_profit_ratio": min(ratios_p) if ratios_p else None,
        "max_profit_ratio": max(ratios_p) if ratios_p else None,
        "median_revenue_ratio": median(ratios_r),
        "lines": xs,
    }


def floor_cut(path):
    data = json.loads(path.read_text())
    seeds = []
    tot_too = tot_band = 0
    for run in data.get("runs") or []:
        too = sum((row.get("road_pairs_profit_too_low") or 0) for row in run["yearly"].values())
        band = sum((row.get("road_pairs_in_band") or 0) for row in run["yearly"].values())
        acc = sum((row.get("road_candidates_accepted") or 0) for row in run["yearly"].values())
        tot_too += too
        tot_band += band
        seeds.append({
            "seed": run["seed"], "profit_too_low": too, "pairs_in_band": band,
            "accepted": acc, "road_ok": run.get("n_road_lines_ok"),
            "cut_rate": (too / band) if band else None,
        })
    return {
        "source": path.name,
        "seeds": seeds,
        "cut_rate": (tot_too / tot_band) if tot_band else None,
        "profit_too_low": tot_too,
        "pairs_in_band": tot_band,
    }


def main():
    rows = []
    seen = set()
    for path in SOURCES:
        for row in collect_lines(path):
            key = (row["seed"], row["line_index"], row["year_built"])
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
    payload = {
        "sources": [path.name for path in SOURCES],
        "note": ("Annee partielle de mise en service exclue. Le pax idx 15 graine 42 "
                 "(opex_road_20y_42) meurt ensuite a 0 vehicule : pre-refleet, ratio 1.33. "
                 "Le fret temoigne : meme ROAD_SPEED_EFFICIENCY_PCT, pas de bassin ville."),
        "pax": summarise(rows, "pax"),
        "freight": summarise(rows, "freight"),
        "current_tree_floor": floor_cut(FLOOR_SOURCE),
        "verdict": {
            "n_pax_was": 1,
            "n_pax": None,
            "median_pax_profit_ratio": None,
            "median_freight_profit_ratio": None,
            "retune": False,
            "reason": ("Le pax routier rapporte ~4x le predit (revenu ~2.3x). Le fret est "
                       "calibre (~1.2x). Ce n'est pas la vitesse. TOWN_CATCHMENT_SHARE_PCT = 22 "
                       "est un calibrage rail. Ne pas baisser ROAD_MIN_PROFIT_ANNUAL ni monter "
                       "le 22 sans constante route propre et banc apparie : le 22 est aussi le rail."),
        },
    }
    payload["verdict"]["n_pax"] = payload["pax"]["n"]
    payload["verdict"]["median_pax_profit_ratio"] = payload["pax"]["median_profit_ratio"]
    payload["verdict"]["median_pax_revenue_ratio"] = payload["pax"]["median_revenue_ratio"]
    payload["verdict"]["median_freight_profit_ratio"] = payload["freight"]["median_profit_ratio"]
    RESULT.write_text(json.dumps(payload, indent=2))
    pax, frt = payload["pax"], payload["freight"]
    print(f"pax n={pax['n']} med P/p={pax['median_profit_ratio']:.2f} "
          f"R/r={pax['median_revenue_ratio']:.2f} "
          f"range {pax['min_profit_ratio']:.2f}-{pax['max_profit_ratio']:.2f}")
    print(f"frt n={frt['n']} med P/p={frt['median_profit_ratio']:.2f} "
          f"R/r={frt['median_revenue_ratio']:.2f}")
    cut = payload["current_tree_floor"]
    print(f"floor cut current tree: {cut['cut_rate']:.1%} "
          f"({cut['profit_too_low']}/{cut['pairs_in_band']})")
    print("ecrit", RESULT)


if __name__ == "__main__":
    main()
