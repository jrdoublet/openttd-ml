"""Mesure de campagne complete post-correctifs (2026-08-28), pour la tache "OpexAI a-t-il
depasse 3 lignes et rembourse son emprunt ?".

Combine ce que deux scripts existants faisaient separement :
  - sweeps/opex_freight_postfix.py : parse tous les signs d'instrumentation (OF/OJ/OK/OQ/OT
    predits, OY/OZ/OU/OO reels, OR par tentative avec la raison d'echec, PK, IA, VS/VL fret,
    OX/OC/OP/OS/OW annuels) ;
  - sweeps/bench.py : extrait le chunk PLYR (company_value, current_loan, money) de chaque
    sauvegarde mensuelle, PAS present dans opex_freight_postfix.py.

Ni l'un ni l'autre ne donnait a la fois "combien de lignes et pourquoi" ET "valeur d'entreprise /
emprunt / tresorerie" dans la meme execution -- necessaire pour repondre a la question du backlog
(doc/taches.md S2 point 1&5) sans relancer deux fois la meme graine.

Meme config gelee que sweeps/bench.py et opex_predict_vs_actual*.py : OpenTTD 15.3, OpenGFX 7.1,
carte 256x256, depart 1970, graine 42. YEARS est un parametre CLI (defaut 10).
"""
import json
import re
import sys
from pathlib import Path

from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work")

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
SEED = 42

CFG = """[difficulty]
number_towns = 3
industry_density = 4
[economy]
inflation = false
town_growth_rate = 2
[game_creation]
starting_year = 1970
map_x = 8
map_y = 8
"""

RE_OF = re.compile(r"^OF\|(\d+)\|(-?\d+)$")
RE_OJ = re.compile(r"^OJ\|(\d+)\|(-?\d+)$")
RE_OK = re.compile(r"^OK\|(\d+)\|(-?\d+)$")
RE_OQ = re.compile(r"^OQ\|(\d+)\|(-?\d+)\|(\d+)$")
RE_OT = re.compile(r"^OT\|(\d+)\|(-?\d+)(?:\|(\d+))?$")
RE_OY = re.compile(r"^OY\|(\d+)\|(\d+)\|(-?\d+)\|(-?\d+)$")
RE_OZ = re.compile(r"^OZ\|(\d+)\|(\d+)\|(-?\d+)$")
RE_OU = re.compile(r"^OU\|(\d+)\|(\d+)\|(\d+)\|(-?\d+)$")
RE_OO = re.compile(r"^OO\|(\d+)\|(\d+)\|(-?\d+)$")
RE_OR = re.compile(r"^OR\|(\d+)\|(\d+)\|(\d+)\|(\w+)$")  # historique avant mesure abandon
RE_OR_BUDGET = re.compile(r"^OR\|(\d{2})\|(\d+)\|(\d+)\|([ZFCN][SL][KADPLHMSTERVXY])\|(\d+)\|(\d+)$")
RE_PK = re.compile(r"^PK\|(\d+)\|([PF])\|(\d+)$")
RE_IA = re.compile(r"^IA\|(\d+)\|(\d+)\|(-?\d)\|(-?\d)\|(-?\d+)$")
RE_OX = re.compile(r"^OX\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")   # year, towns, industries, ranked.all
RE_OW = re.compile(r"^OW\|(\d+)\|(\d+)\|(\d+)$")          # year, buildOps, lines.len() (as of start of year)
RE_OS = re.compile(r"^OS\|(\d+)\|(\d+)\|(\d+)$")          # year, cand_rank opcodes, utilisationPerMille
RE_OA = re.compile(r"^OA\|(\d+)\|(\d+)\|(\d+)\|(\w+)$")   # air attempt: year, distance, planOps, reason
RE_OM = re.compile(r"^OM\|W\|(\d+)\|(\d+)\|(\d+)$")       # water success: year, distance, planOps
RE_ON = re.compile(r"^ON\|W\|(\w+)\|(-?\d+)$")            # water failure: reason, error
RE_YT = re.compile(r"^YT\|(\d{2})\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")

TOP_K = 20  # Doit rester synchronise avec ai/OpexAI/candidates.nut, pour decoder rang20.
REASON_CODES = {
    "K": "OK", "A": "ABND", "D": "DEAD", "P": "NOPA", "L": "NOPLAN",
    "H": "SHORT", "M": "NOMATCH", "S": "STNFAIL", "T": "TRKFAIL",
    "E": "DEPFAIL", "R": "ORDFAIL", "V": "NOTRAIN", "Y": "YEAR", "X": "UNKNOWN",
}


def unpack_rank(packed):
    """Inverse rang * TOP_K + longueur, range 0..TOP_K-1 et longueur 1..TOP_K."""
    rank = (packed - 1) // TOP_K
    length = packed - rank * TOP_K
    if not (0 <= rank < TOP_K and 1 <= length <= TOP_K):
        raise ValueError(f"rang20 invalide: {packed}")
    return rank, length


def keep(row):
    chunks = row["chunks"]
    signs = [s["name"] for s in chunks.get("SIGN", {}).values()]
    player = chunks.get("PLYR", {}).get(0) or chunks.get("PLYR", {}).get("0")
    closed = (player or {}).get("old_economy") or []
    last_closed = closed[0] if closed else {}
    return ({
        "date": str(row["date"]),
        "signs": signs,
        "company_value": last_closed.get("company_value"),
        "performance_history": last_closed.get("performance_history"),
        "money": (player or {}).get("money"),
        "current_loan": (player or {}).get("current_loan"),
        "months_of_bankruptcy": (player or {}).get("months_of_bankruptcy"),
        "n_vehicles": len(chunks.get("VEHS", {})),
        "n_stations": len(chunks.get("STNN", {})),
    },)


def parse_lines(all_signs):
    predicted = {}
    actual_series = {}
    built = {}

    for sign in all_signs:
        if m := RE_OF.match(sign):
            idx = int(m.group(1)); predicted.setdefault(idx, {})["revenueAnnual"] = int(m.group(2))
        elif m := RE_OJ.match(sign):
            idx = int(m.group(1)); predicted.setdefault(idx, {})["runningAnnual"] = int(m.group(2))
        elif m := RE_OK.match(sign):
            idx = int(m.group(1)); predicted.setdefault(idx, {})["amortAnnual"] = int(m.group(2))
        elif m := RE_OQ.match(sign):
            idx = int(m.group(1))
            predicted.setdefault(idx, {})["carried"] = int(m.group(2))
            predicted[idx]["trains"] = int(m.group(3))
        elif m := RE_OT.match(sign):
            idx = int(m.group(1)); predicted.setdefault(idx, {})["oneWayDays"] = int(m.group(2))
            if m.group(3) is not None:
                predicted[idx]["distance"] = int(m.group(3))
        elif m := RE_OY.match(sign):
            idx, year = int(m.group(1)), int(m.group(2))
            actual_series.setdefault(idx, {}).setdefault(year, {})["ratingA"] = int(m.group(3))
            actual_series[idx][year]["ratingB"] = int(m.group(4))
        elif m := RE_OZ.match(sign):
            idx, year = int(m.group(1)), int(m.group(2))
            actual_series.setdefault(idx, {}).setdefault(year, {})["profit"] = int(m.group(3))
        elif m := RE_OU.match(sign):
            idx, year = int(m.group(1)), int(m.group(2))
            actual_series.setdefault(idx, {}).setdefault(year, {})["vehCount"] = int(m.group(3))
            actual_series[idx][year]["runCost"] = int(m.group(4))
        elif m := RE_OO.match(sign):
            idx, year = int(m.group(1)), int(m.group(2))
            actual_series.setdefault(idx, {}).setdefault(year, {})["revenue"] = int(m.group(3))
        elif m := RE_IA.match(sign):
            idx, year = int(m.group(1)), int(m.group(2))
            d = actual_series.setdefault(idx, {}).setdefault(year, {})
            d["srcAlive"] = int(m.group(3)); d["dstAlive"] = int(m.group(4)); d["srcProd"] = int(m.group(5))
        elif m := RE_OR.match(sign):
            idx = int(m.group(1))
            built.setdefault(idx, {"distance": int(m.group(2)), "iterations": int(m.group(3)),
                                    "reason": m.group(4)})
        elif m := RE_OR_BUDGET.match(sign):
            idx = int(m.group(2))
            built.setdefault(idx, {"iterations": int(m.group(6)), "reason": REASON_CODES[m.group(4)[2]]})
        elif m := RE_PK.match(sign):
            idx = int(m.group(1))
            predicted.setdefault(idx, {})["kind"] = "pax" if m.group(2) == "P" else "freight"
            predicted[idx]["monthly"] = int(m.group(3))

    lines = []
    for idx in sorted(built):
        pred = predicted.get(idx, {})
        pred["profitAnnual"] = pred.get("revenueAnnual", 0) - pred.get("runningAnnual", 0) - pred.get("amortAnnual", 0)
        years = actual_series.get(idx, {})
        last_year = max(years) if years else None
        last = years.get(last_year, {}) if last_year is not None else {}
        lines.append({
            "line_index": idx,
            "distance": built[idx].get("distance", pred.get("distance")),
            "iterations": built[idx]["iterations"],
            "reason": built[idx]["reason"],
            "predicted": pred,
            "actual_last_year": last_year,
            "actual": last,
            "actual_series": years,
        })
    return lines


def parse_attempts(all_signs):
    """Toutes les tentatives OR (rail), y compris les echecs -- pour distinguer les rejets par
    tentative-echouee (TRKFAIL, NOPLAN, ...) des rejets INVISIBLES (_tooClose continue, argent
    break) qui ne generent aucun sign."""
    attempts = []
    for sign in all_signs:
        if m := RE_OR_BUDGET.match(sign):
            rank, ranked_len = unpack_rank(int(m.group(3)))
            mode = m.group(4)
            attempts.append({"year": 1900 + int(m.group(1)), "idx": int(m.group(2)),
                             "rank": rank, "ranked_len": ranked_len,
                             "budget_path": mode[0], "alternative_source": mode[1],
                             "reason": REASON_CODES[mode[2]], "iteration_budget": int(m.group(5)),
                             "iterations": int(m.group(6))})
        elif m := RE_OR.match(sign):
            attempts.append({"idx": int(m.group(1)), "distance": int(m.group(2)),
                              "iterations": int(m.group(3)), "reason": m.group(4)})
    return attempts


def parse_yearly(all_signs):
    """Series annuelles : candidats totaux (OX), lignes construites a date (OW), utilisation du
    budget d'opcodes en pour mille (OS)."""
    by_year = {}
    for sign in all_signs:
        if m := RE_OX.match(sign):
            y = int(m.group(1))
            by_year.setdefault(y, {})["towns"] = int(m.group(2))
            by_year[y]["industries"] = int(m.group(3))
            by_year[y]["ranked_all"] = int(m.group(4))
        elif m := RE_OW.match(sign):
            y = int(m.group(1))
            by_year.setdefault(y, {})["buildOps"] = int(m.group(2))
            by_year[y]["lines_len_start_of_year"] = int(m.group(3))
        elif m := RE_OS.match(sign):
            y = int(m.group(1))
            by_year.setdefault(y, {})["cand_rank_ops"] = int(m.group(2))
            by_year[y]["utilisation_permille"] = int(m.group(3))
    return dict(sorted(by_year.items()))


def parse_annual_blocks(all_signs):
    """Mesure YT posee apres chaque bloc annuel termine.

    Le code AI encode l'annee sur deux chiffres (la campagne commence en 1970) pour respecter
    les 31 caracteres. skipped_years_before est explicite, et non infere de l'absence d'un sign.
    """
    blocks = []
    for sign in all_signs:
        if m := RE_YT.match(sign):
            year = 1900 + int(m.group(1))
            start_tick, end_tick, try_build_ticks, skipped = map(int, m.groups()[1:])
            duration = end_tick - start_tick
            blocks.append({
                "year": year,
                "start_tick": start_tick,
                "end_tick": end_tick,
                "duration_ticks": duration,
                "try_build_ticks": try_build_ticks,
                "other_ticks": duration - try_build_ticks,
                "skipped_years_before": skipped,
            })
    return blocks


def parse_air_water(all_signs):
    air, water = [], []
    for sign in all_signs:
        if m := RE_OA.match(sign):
            air.append({"year": int(m.group(1)), "distance": int(m.group(2)),
                        "planOps": int(m.group(3)), "reason": m.group(4)})
        elif m := RE_OM.match(sign):
            water.append({"ok": True, "year": int(m.group(1)), "distance": int(m.group(2)),
                          "planOps": int(m.group(3))})
        elif m := RE_ON.match(sign):
            water.append({"ok": False, "reason": m.group(1), "error": int(m.group(2))})
    return air, water


def main():
    years = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    result_path = ROOT / "docs" / f"opex_full_campaign_{years}y.json"

    experiments = [{
        "seed": SEED, "days": 365 * years, "openttd_config": CFG,
        "ais": (local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", ()),),
    }]
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION, max_workers=1,
        result_processor=keep, experiments=experiments,
        ai_libraries=(bananas_ai_library("5046524c", "Pathfinder.Rail"),),
    ))
    rows.sort(key=lambda r: r["date"])
    final = rows[-1]

    lines = parse_lines(final["signs"])
    attempts = parse_attempts(final["signs"])
    yearly = parse_yearly(final["signs"])
    annual_blocks = parse_annual_blocks(final["signs"])
    skipped_years = [missed for block in annual_blocks for missed in
                     range(block["year"] - block["skipped_years_before"], block["year"])]
    air, water = parse_air_water(final["signs"])

    n_rail_ok = sum(1 for l in lines if l["reason"] == "OK")
    n_rail_failed_attempts = sum(1 for a in attempts if a["reason"] != "OK")
    abandoned = [a for a in attempts if a["reason"] == "ABND"]
    abandoned_no_alternative = [a for a in abandoned if a.get("budget_path") == "Z"]
    abandoned_hard_cap = [a for a in abandoned if a.get("budget_path") == "C"]

    # Serie temporelle courte (une ligne par sauvegarde) pour la trajectoire company_value/loan.
    financial_series = [{
        "date": r["date"], "company_value": r["company_value"], "money": r["money"],
        "current_loan": r["current_loan"], "n_vehicles": r["n_vehicles"], "n_stations": r["n_stations"],
    } for r in rows]

    payload = {
        "openttd_version": OPENTTD_VERSION, "opengfx_version": OPENGFX_VERSION,
        "seed": SEED, "years": years, "openttd_config": CFG,
        "n_savegames": len(rows), "final_date": final["date"],
        "final_company_value": final["company_value"],
        "final_performance_history": final["performance_history"],
        "final_money": final["money"],
        "final_current_loan": final["current_loan"],
        "final_n_vehicles": final["n_vehicles"],
        "final_n_stations": final["n_stations"],
        "n_rail_lines_ok": n_rail_ok,
        "n_rail_attempts_total": len(attempts),
        "n_rail_attempts_failed": n_rail_failed_attempts,
        "n_rail_attempts_last_ranked": sum(1 for a in attempts if a.get("alternative_source") == "L"),
        "n_rail_attempts_zero_alternative": sum(1 for a in attempts if a.get("budget_path") == "Z"),
        "n_rail_attempts_abandoned": len(abandoned),
        "abandoned_iterations": sum(a["iterations"] for a in abandoned),
        "n_rail_attempts_abandoned_zero_alternative": len(abandoned_no_alternative),
        "abandoned_iterations_zero_alternative": sum(a["iterations"] for a in abandoned_no_alternative),
        "n_rail_attempts_abandoned_hard_cap": len(abandoned_hard_cap),
        "abandoned_iterations_hard_cap": sum(a["iterations"] for a in abandoned_hard_cap),
        "rail_attempts": attempts,
        "air_attempts": air,
        "water_attempts": water,
        "lines": lines,
        "yearly": yearly,
        "annual_blocks": annual_blocks,
        "skipped_years": skipped_years,
        "financial_series": financial_series,
        "raw_signs_final": final["signs"],
    }
    result_path.write_text(json.dumps(payload, indent=2))
    print(f"=== {years} ans, graine {SEED} ===")
    print(f"lignes rail OK: {n_rail_ok}  (tentatives totales: {len(attempts)}, echouees: {n_rail_failed_attempts})")
    print(f"avion: {len(air)} tentative(s) {air}")
    print(f"bateau: {len(water)} tentative(s) {water}")
    print(f"company_value final: {final['company_value']}  performance_history: {final['performance_history']}")
    print(f"money: {final['money']}  current_loan: {final['current_loan']}")
    print(f"n_vehicles: {final['n_vehicles']}  n_stations: {final['n_stations']}")
    print(f"annees sautees: {skipped_years}")
    print("ecrit", result_path)


if __name__ == "__main__":
    main()
