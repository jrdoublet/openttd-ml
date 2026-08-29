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
carte 256x256, depart 1970. YEARS et les graines sont des parametres CLI (defauts 10 et 42).
"""
import argparse
import json
import re
from pathlib import Path

from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work")

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
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
RE_OR_BUDGET = re.compile(r"^OR\|(\d{2})\|(\d+)\|(\d+)\|([ZFCN][SL][KADPLHMJSTERVX])\|(\d+)\|(\d+)$")
RE_OB_ATTEMPT = re.compile(r"^OB\|A\|(\d{2})\|(\d+)\|(\d+)\|(\d+)$")
RE_PK = re.compile(r"^PK\|(\d+)\|([PF])\|(\d+)$")
RE_PC = re.compile(r"^PC\|(\d+)\|(.+)$")
# Marqueur par LIGNE de la tranche jointure (2026-08-29) : extremite jointe ("A"/"B"/"N")
# et origine deja desservie (0/1). Emis seulement quand station_join = 1.
RE_PJ = re.compile(r"^PJ\|(\d+)\|([ABN])\|([01])$")
RE_PM = re.compile(r"^PM\|(\d+)\|([AWR])\|(\d+)\|(.+)$")
RE_IA = re.compile(r"^IA\|(\d+)\|(\d+)\|(-?\d)\|(-?\d)\|(-?\d+)$")
RE_OX = re.compile(r"^OX\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")   # year, towns, industries, ranked.all
RE_OW = re.compile(r"^OW\|(\d+)\|(\d+)\|(\d+)$")          # year, buildOps, lines.len() (as of start of year)
RE_OS = re.compile(r"^OS\|(\d+)\|(\d+)\|(\d+)$")          # year, cand_rank opcodes, utilisationPerMille
RE_CG = re.compile(r"^CG\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")
RE_CR = re.compile(r"^CR\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")
RE_CD = re.compile(r"^CD\|(\d+)\|(\d+)\|(\d+)$")
RE_CE = re.compile(r"^CE\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")
RE_CK = re.compile(r"^CK\|(\d+)\|(\d+)\|(\d+)$")
RE_GN = re.compile(r"^GN\|(\d+)\|(\d+)\|(\d+)$")
RE_GM = re.compile(r"^GM\|(\d+)\|(\d+)$")                 # candidats exclus par memoire ABND
RE_OB_JOIN = re.compile(r"^OB\|J\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")
# Tranche du 2026-08-29 : part du TOP_K qui n'existe QUE parce qu'une extremite deja servie
# peut etre reprise par un quai joint (annee, ces candidats, taille du classement).
RE_OB_SERVED = re.compile(r"^OB\|S\|(\d+)\|(\d+)\|(\d+)$")
# Devenir des paires a UNE seule extremite servie : irrecuperables / poursuivies.
RE_CJ = re.compile(r"^CJ\|(\d+)\|(\d+)\|(\d+)$")
RE_GC = re.compile(r"^GC\|(\d+)\|(-?\d+)\|(\d+)$")
RE_DL = re.compile(r"^DL\|(\d+)\|(\d+)\|(\d+)$")
RE_LR = re.compile(r"^LR\|(\d+)\|(\d+)\|(\d+)$")
RE_LF = re.compile(r"^LF\|(\d{2})\|(-?\d+)\|(\d+)$")   # ce que _tryRepayLoan VOIT (creux annuel)
RE_LB = re.compile(r"^LB\|(\d{2})\|(-?\d+)$")            # tresorerie au SOMMET, avant depense

# Doit suivre LOAN_REPAY_FLOOR dans ai/OpexAI/main.nut : sert uniquement a etiqueter les annees
# ou le sommet de tresorerie passait le plancher mais pas le creux.
LOAN_REPAY_FLOOR = 1000000
RE_OA = re.compile(r"^OA\|(\d+)\|(\d+)\|(\d+)\|(\w+)$")   # air attempt: year, distance, planOps, reason
RE_OM = re.compile(r"^OM\|W\|(\d+)\|(\d+)\|(\d+)$")       # water success: year, distance, planOps
RE_ON = re.compile(r"^ON\|W\|(\w+)\|(-?\d+)$")            # water failure: reason, error
# Phase routiere multi-lignes (2026-08-29). Les panneaux de la liaison bus unique (OM|R, OC|R,
# OV|R, OE|R, et tout le diagnostic RT/RS/RD/RY/RW/RP/RQ/RE/RI/RL/RV/RX) ont ete retires de l'IA
# en meme temps que ce diagnostic : une ligne routiere rejoint maintenant _lines, donc elle est
# decrite par les MEMES panneaux que le rail (OF/OJ/OK/OQ/OT/PK/PC predits, OY/OZ/OU/OO reels) et
# n'a plus besoin que d'un marqueur de mode.
RE_RC_ROAD = re.compile(r"^RC\|(\d{2})\|(\d+)\|(\d+)\|(-?\d+)\|(\d+)$")   # annee, id, essai, cout, vehicules
RE_RA_ROAD = re.compile(r"^RA\|(\d{2})\|(\d+)\|(\d+)\|(\w+)\|(-?\d+)$")  # tentative echouee
RE_RB_ROAD = re.compile(r"^RB\|(\d{2})\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")   # opcodes plan / construction
RE_RN_ROAD = re.compile(r"^RN\|(\d{2})\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")  # classes/tentatives/baties/opcodes
RE_RS_ROAD = re.compile(r"^RS\|(\d{2})\|(\d+)\|(\d+)\|(\d+)$")  # paires en bande / coupees / acceptees
RE_YT = re.compile(r"^YT\|(\d{2})\|(\d+)\|(\d+)\|(\d+)\|(\d+)(C)?$")

TOP_K = 20  # Doit rester synchronise avec ai/OpexAI/candidates.nut, pour decoder rang20.
REASON_CODES = {
    "K": "OK", "A": "ABND", "D": "DEAD", "P": "NOPA", "L": "NOPLAN",
    "H": "SHORT", "M": "NOMATCH", "J": "JOINPATH", "S": "STNFAIL", "T": "TRKFAIL",
    "E": "DEPFAIL", "R": "ORDFAIL", "V": "NOTRAIN", "X": "UNKNOWN",
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
        "seed": row["experiment"]["opex_seed"],
        "date": str(row["date"]),
        "signs": signs,
        "company_value": last_closed.get("company_value"),
        "performance_history": last_closed.get("performance_history"),
        "income_last_year": last_closed.get("income"),
        "money": (player or {}).get("money"),
        "current_loan": (player or {}).get("current_loan"),
        "months_of_bankruptcy": (player or {}).get("months_of_bankruptcy"),
        "n_vehicles": len(chunks.get("VEHS", {})),
        "n_stations": len(chunks.get("STNN", {})),
        "openttd_output": row.get("output"),
    },)


def parse_lines(all_signs):
    predicted = {}
    actual_series = {}
    built = {}
    multimodal_built = {}
    road_cost = {}
    join_marks = {}

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
            if m.group(4) == "OK":
                idx = int(m.group(1))
                built[idx] = {"distance": int(m.group(2)), "iterations": int(m.group(3)),
                              "reason": m.group(4)}
        elif m := RE_OR_BUDGET.match(sign):
            idx = int(m.group(2))
            reason = REASON_CODES[m.group(4)[2]]
            if reason == "OK":
                built[idx] = {"iterations": int(m.group(6)), "reason": reason}
        elif m := RE_PK.match(sign):
            idx = int(m.group(1))
            predicted.setdefault(idx, {})["kind"] = "pax" if m.group(2) == "P" else "freight"
            predicted[idx]["monthly"] = int(m.group(3))
        elif m := RE_PJ.match(sign):
            join_marks[int(m.group(1))] = {"joined_end": None if m.group(2) == "N" else m.group(2),
                                           "origin_served": m.group(3) == "1"}
        elif m := RE_PC.match(sign):
            predicted.setdefault(int(m.group(1)), {})["cargo_label"] = m.group(2)
        elif m := RE_PM.match(sign):
            idx = int(m.group(1))
            multimodal_built[idx] = {
                "mode": {"A": "air", "W": "water", "R": "road"}[m.group(2)],
                "distance": int(m.group(3)), "cargo_label": m.group(4),
            }
        elif m := RE_RC_ROAD.match(sign):
            idx = int(m.group(2))
            road_cost[idx] = {"year": 1900 + int(m.group(1)), "attempt": int(m.group(3)),
                              "cost": int(m.group(4)), "vehicles": int(m.group(5))}

    lines = []
    for idx in sorted(built):
        pred = predicted.get(idx, {})
        pred["profitAnnual"] = pred.get("revenueAnnual", 0) - pred.get("runningAnnual", 0) - pred.get("amortAnnual", 0)
        years = actual_series.get(idx, {})
        last_year = max(years) if years else None
        last = years.get(last_year, {}) if last_year is not None else {}
        mark = join_marks.get(idx, {})
        lines.append({
            "line_index": idx,
            "mode": "rail",
            "distance": built[idx].get("distance", pred.get("distance")),
            "iterations": built[idx]["iterations"],
            "reason": built[idx]["reason"],
            # None quand station_join = 0 : le panneau n'est pas emis, et l'absence ne doit pas
            # se lire comme "ligne non jointe, origine libre" -- c'est "non mesure".
            "joined_end": mark.get("joined_end"),
            "origin_served": mark.get("origin_served"),
            "predicted": pred,
            "actual_last_year": last_year,
            "actual": last,
            "actual_series": years,
        })
    for idx in sorted(multimodal_built):
        years = actual_series.get(idx, {})
        last_year = max(years) if years else None
        last = years.get(last_year, {}) if last_year is not None else {}
        item = multimodal_built[idx]
        # Une ligne routiere porte le meme bloc predit qu'une ligne rail (PK/PC/OF/OJ/OK/OQ/OT) ;
        # l'avion et le bateau, eux, n'en emettent aucun -- d'ou le repli sur ce que PM contient.
        pred = predicted.get(idx)
        if pred is None:
            pred = {"kind": "pax", "cargo_label": item["cargo_label"]}
        else:
            pred = dict(pred)
            pred["profitAnnual"] = (pred.get("revenueAnnual", 0) - pred.get("runningAnnual", 0)
                                    - pred.get("amortAnnual", 0))
        entry = {
            "line_index": idx,
            "mode": item["mode"],
            "distance": item["distance"],
            "iterations": 0,
            "reason": "OK",
            "predicted": pred,
            "actual_last_year": last_year,
            "actual": last,
            "actual_series": years,
        }
        if idx in road_cost:
            entry["year_built"] = road_cost[idx]["year"]
            entry["attempt"] = road_cost[idx]["attempt"]
            entry["cost"] = road_cost[idx]["cost"]
            entry["vehicles_built"] = road_cost[idx]["vehicles"]
        lines.append(entry)
    return lines


def parse_attempts(all_signs):
    """Toutes les tentatives OR (rail), y compris les echecs -- pour distinguer les rejets par
    tentative-echouee (TRKFAIL, NOPLAN, ...) des rejets INVISIBLES (_tooClose continue, argent
    break) qui ne generent aucun sign."""
    attempts = []
    opcodes = {}
    for sign in all_signs:
        if m := RE_OB_ATTEMPT.match(sign):
            opcodes[(int(m.group(1)), int(m.group(2)), int(m.group(3)))] = int(m.group(4))
    for sign in all_signs:
        if m := RE_OR_BUDGET.match(sign):
            packed = int(m.group(3))
            rank, ranked_len = unpack_rank(packed)
            mode = m.group(4)
            attempts.append({"year": 1900 + int(m.group(1)), "idx": int(m.group(2)),
                             "rank": rank, "ranked_len": ranked_len,
                             "budget_path": mode[0], "alternative_source": mode[1],
                             "reason": REASON_CODES[mode[2]], "iteration_budget": int(m.group(5)),
                             "iterations": int(m.group(6)),
                             "opcodes": opcodes.get((int(m.group(1)), int(m.group(2)), packed))})
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
        elif m := RE_CG.match(sign):
            y = int(m.group(1)); d = by_year.setdefault(y, {})
            d["towns_served"] = int(m.group(2)); d["towns_unserved"] = int(m.group(3))
            d["industries_served"] = int(m.group(4)); d["industries_unserved"] = int(m.group(5))
        elif m := RE_CR.match(sign):
            y = int(m.group(1)); d = by_year.setdefault(y, {})
            d["candidate_pairs_total"] = int(m.group(2))
            d["candidate_pairs_origin_served"] = int(m.group(3))
            d["candidate_no_monthly"] = int(m.group(4))
        elif m := RE_CD.match(sign):
            y = int(m.group(1)); d = by_year.setdefault(y, {})
            d["candidate_distance_short"] = int(m.group(2))
            d["candidate_distance_long"] = int(m.group(3))
        elif m := RE_CE.match(sign):
            y = int(m.group(1)); d = by_year.setdefault(y, {})
            d["candidate_economics_unavailable"] = int(m.group(2))
            d["candidate_profit_non_positive"] = int(m.group(3))
            d["candidate_ratio_too_low"] = int(m.group(4))
        elif m := RE_CK.match(sign):
            y = int(m.group(1)); d = by_year.setdefault(y, {})
            d["candidates_accepted"] = int(m.group(2))
            d["candidates_omitted_by_top_k"] = int(m.group(3))
        elif m := RE_GN.match(sign):
            y = int(m.group(1)); d = by_year.setdefault(y, {})
            d["too_close_near"] = int(m.group(2)); d["too_close_far"] = int(m.group(3))
        elif m := RE_GM.match(sign):
            y = int(m.group(1)); d = by_year.setdefault(y, {})
            d["candidates_skipped_abandon_memory"] = int(m.group(2))
        elif m := RE_RN_ROAD.match(sign):
            y = 1900 + int(m.group(1)); d = by_year.setdefault(y, {})
            d["road_candidates_ranked"] = int(m.group(2))
            d["road_attempts"] = int(m.group(3))
            d["road_lines_built"] = int(m.group(4))
            d["road_candidate_opcodes"] = int(m.group(5))
        elif m := RE_RS_ROAD.match(sign):
            y = 1900 + int(m.group(1)); d = by_year.setdefault(y, {})
            d["road_pairs_in_band"] = int(m.group(2))
            d["road_pairs_profit_too_low"] = int(m.group(3))
            d["road_candidates_accepted"] = int(m.group(4))
        elif m := RE_OB_JOIN.match(sign):
            y = int(m.group(1)); d = by_year.setdefault(y, {})
            d["station_join_attempts"] = int(m.group(2))
            d["station_join_built"] = int(m.group(3))
            d["station_join_failed"] = int(m.group(4))
        elif m := RE_OB_SERVED.match(sign):
            y = int(m.group(1)); d = by_year.setdefault(y, {})
            d["ranked_origin_served"] = int(m.group(2))
            d["ranked_total"] = int(m.group(3))
        elif m := RE_CJ.match(sign):
            y = int(m.group(1)); d = by_year.setdefault(y, {})
            d["candidate_pairs_join_impossible"] = int(m.group(2))
            d["candidate_pairs_one_served"] = int(m.group(3))
    return dict(sorted(by_year.items()))


def parse_events(all_signs):
    """Retient les evenements rares qui expliquent les variations de parc et d'emprunt."""
    cash_blocks, dead_lines, loan_repayments = [], [], []
    seen_at_repay, seen_before_block = {}, {}
    for sign in all_signs:
        if m := RE_GC.match(sign):
            cash_blocks.append({"year": int(m.group(1)), "cash": int(m.group(2)),
                                "capital": int(m.group(3))})
        elif m := RE_DL.match(sign):
            dead_lines.append({"year": int(m.group(1)), "line_index": int(m.group(2)),
                               "stage": int(m.group(3))})
        elif m := RE_LR.match(sign):
            loan_repayments.append({"year": int(m.group(1)), "repaid": int(m.group(2)),
                                    "new_loan": int(m.group(3))})
        elif m := RE_LF.match(sign):
            seen_at_repay[int(m.group(1))] = {"cash": int(m.group(2)), "loan": int(m.group(3))}
        elif m := RE_LB.match(sign):
            seen_before_block[int(m.group(1))] = int(m.group(2))

    return cash_blocks, dead_lines, loan_repayments, loan_view(seen_at_repay, seen_before_block)


def loan_view(seen_at_repay, seen_before_block):
    """Croise le sommet annuel de tresorerie (LB) et ce que _tryRepayLoan voit (LF).

    _tryRepayLoan est appele APRES _tryBuild : `drained` mesure donc exactement ce que la
    construction de l'annee retire au remboursement, et `blocked_by_floor_only` isole les annees
    ou le sommet aurait suffi mais pas le creux.
    """
    view = []
    for year_mod in sorted(set(seen_at_repay) | set(seen_before_block)):
        at = seen_at_repay.get(year_mod)
        before = seen_before_block.get(year_mod)
        row = {
            "year": 1900 + year_mod if year_mod >= 70 else 2000 + year_mod,
            "cash_before_block": before,
            "cash_at_repay": at["cash"] if at else None,
            "loan_at_repay": at["loan"] if at else None,
        }
        if before is not None and at is not None:
            row["drained_by_build"] = before - at["cash"]
            row["blocked_by_floor_only"] = bool(
                at["loan"] > 0
                and before > LOAN_REPAY_FLOOR
                and at["cash"] <= LOAN_REPAY_FLOOR
            )
        view.append(row)
    return view


def parse_annual_blocks(all_signs):
    """Mesure YT posee apres chaque bloc annuel termine.

    Le code AI encode l'annee sur deux chiffres (la campagne commence en 1970) pour respecter
    les 31 caracteres. skipped_years_before est explicite, et non infere de l'absence d'un sign.
    """
    blocks = []
    for sign in all_signs:
        if m := RE_YT.match(sign):
            year = 1900 + int(m.group(1))
            start_tick, end_tick, try_build_ticks, skipped = map(int, m.groups()[1:5])
            caught_up = skipped if m.group(6) == "C" else 0
            duration = end_tick - start_tick
            blocks.append({
                "year": year,
                "start_tick": start_tick,
                "end_tick": end_tick,
                "duration_ticks": duration,
                "try_build_ticks": try_build_ticks,
                "other_ticks": duration - try_build_ticks,
                "calendar_years_crossed_before": skipped,
                "caught_up_years": caught_up,
                "skipped_years_before": skipped - caught_up,
            })
    return blocks


def parse_multimodal(all_signs):
    air, water, road = [], [], []
    road_costs = {}
    for sign in all_signs:
        if m := RE_OA.match(sign):
            air.append({"year": int(m.group(1)), "distance": int(m.group(2)),
                        "planOps": int(m.group(3)), "reason": m.group(4)})
        elif m := RE_OM.match(sign):
            water.append({"ok": True, "year": int(m.group(1)), "distance": int(m.group(2)),
                          "planOps": int(m.group(3))})
        elif m := RE_ON.match(sign):
            water.append({"ok": False, "reason": m.group(1), "error": int(m.group(2))})
        elif m := RE_RA_ROAD.match(sign):
            # Une tentative routiere echouee. RA porte l'identifiant que la ligne AURAIT eu :
            # _nextLineId n'avance que sur un succes, donc plusieurs echecs peuvent partager un
            # meme numero, et le succes suivant le reutilise. C'est une trace de tentative, pas
            # une cle -- ne pas s'en servir pour indexer une ligne.
            road.append({"ok": False, "year": 1900 + int(m.group(1)),
                         "line_index": int(m.group(2)), "attempt": int(m.group(3)),
                         "reason": m.group(4), "error": int(m.group(5))})
        elif m := RE_RB_ROAD.match(sign):
            road_costs[(int(m.group(1)), int(m.group(2)), int(m.group(3)))] = {
                "plan_ops": int(m.group(4)), "build_ops": int(m.group(5))}
    for item in road:
        item.update(road_costs.get((item["year"] % 100, item["line_index"], item["attempt"]), {}))
    # road_costs sort aussi de la fonction : les tentatives REUSSIES sont reconstituees plus tard
    # depuis PM/RC (parse_lines), et doivent pouvoir retrouver leur cout en opcodes par (annee, id).
    return air, water, road, road_costs


def make_run_payload(rows, seed, years):
    """Assemble une campagne sans melanger les panneaux de graines differentes."""
    rows.sort(key=lambda row: row["date"])
    final = rows[-1]

    lines = parse_lines(final["signs"])
    attempts = parse_attempts(final["signs"])
    yearly = parse_yearly(final["signs"])
    annual_blocks = parse_annual_blocks(final["signs"])
    calendar_years_crossed = [missed for block in annual_blocks for missed in
                              range(block["year"] - block["calendar_years_crossed_before"], block["year"])]
    skipped_years = [missed for block in annual_blocks for missed in
                     range(block["year"] - block["skipped_years_before"], block["year"])]
    air, water, road, road_ops = parse_multimodal(final["signs"])
    # Les succes routiers sont decrits par PM/RC dans parse_lines ; on les reinjecte dans
    # road_attempts pour que la liste raconte l'annee entiere, echecs ET reussites.
    for line in lines:
        if line["mode"] != "road":
            continue
        year_built = line.get("year_built")
        item = {"ok": True, "year": year_built, "line_index": line["line_index"],
                "attempt": line.get("attempt"),
                "distance": line["distance"], "cost": line.get("cost"),
                "vehicles": line.get("vehicles_built"),
                "kind": line["predicted"].get("kind"),
                "cargo_label": line["predicted"].get("cargo_label")}
        if year_built is not None:
            item.update(road_ops.get((year_built % 100, line["line_index"], item["attempt"]), {}))
        road.append(item)
    cash_blocks, dead_lines, loan_repayments, loan_view_rows = parse_events(final["signs"])

    n_rail_ok = sum(1 for line in lines if line["mode"] == "rail" and line["reason"] == "OK")
    n_rail_failed_attempts = sum(1 for attempt in attempts if attempt["reason"] != "OK")
    abandoned = [attempt for attempt in attempts if attempt["reason"] == "ABND"]
    abandoned_no_alternative = [attempt for attempt in abandoned if attempt.get("budget_path") == "Z"]
    abandoned_hard_cap = [attempt for attempt in abandoned if attempt.get("budget_path") == "C"]

    financial_series = [{
        "date": row["date"], "company_value": row["company_value"],
        "income_last_year": row["income_last_year"], "money": row["money"],
        "current_loan": row["current_loan"], "n_vehicles": row["n_vehicles"],
        "n_stations": row["n_stations"], "openttd_output": row["openttd_output"],
    } for row in rows]

    return {
        "seed": seed, "years": years, "n_savegames": len(rows), "final_date": final["date"],
        "final_company_value": final["company_value"],
        "final_performance_history": final["performance_history"],
        "final_money": final["money"], "final_current_loan": final["current_loan"],
        "final_n_vehicles": final["n_vehicles"], "final_n_stations": final["n_stations"],
        "n_rail_lines_ok": n_rail_ok, "n_rail_attempts_total": len(attempts),
        "n_rail_attempts_failed": n_rail_failed_attempts,
        "n_rail_attempts_last_ranked": sum(
            1 for attempt in attempts if attempt.get("alternative_source") == "L"),
        "n_rail_attempts_zero_alternative": sum(
            1 for attempt in attempts if attempt.get("budget_path") == "Z"),
        "n_rail_attempts_abandoned": len(abandoned),
        "abandoned_iterations": sum(attempt["iterations"] for attempt in abandoned),
        "n_rail_attempts_abandoned_zero_alternative": len(abandoned_no_alternative),
        "abandoned_iterations_zero_alternative": sum(
            attempt["iterations"] for attempt in abandoned_no_alternative),
        "n_rail_attempts_abandoned_hard_cap": len(abandoned_hard_cap),
        "abandoned_iterations_hard_cap": sum(
            attempt["iterations"] for attempt in abandoned_hard_cap),
        "n_rail_candidates_skipped_abandon_memory": sum(
            row.get("candidates_skipped_abandon_memory", 0) for row in yearly.values()),
        "n_station_join_attempts": sum(row.get("station_join_attempts", 0) for row in yearly.values()),
        "n_station_join_built": sum(row.get("station_join_built", 0) for row in yearly.values()),
        "n_station_join_failed": sum(row.get("station_join_failed", 0) for row in yearly.values()),
        "n_road_lines_ok": sum(1 for line in lines if line["mode"] == "road"),
        "n_road_freight_lines_ok": sum(
            1 for line in lines
            if line["mode"] == "road" and line["predicted"].get("kind") == "freight"),
        "n_road_attempts": sum(row.get("road_attempts", 0) for row in yearly.values()),
        "n_road_attempts_failed": sum(1 for item in road if not item["ok"]),
        "road_plan_opcodes": sum(item.get("plan_ops", 0) for item in road),
        "road_build_opcodes": sum(item.get("build_ops", 0) for item in road),
        "rail_attempts": attempts, "air_attempts": air, "water_attempts": water,
        "road_attempts": road, "cash_blocks": cash_blocks, "dead_line_events": dead_lines,
        "loan_repayments": loan_repayments, "loan_view": loan_view_rows,
        "lines": lines, "yearly": yearly,
        "annual_blocks": annual_blocks, "calendar_years_crossed": calendar_years_crossed,
        "skipped_years": skipped_years, "financial_series": financial_series,
        "raw_signs_final": final["signs"],
    }


def parse_args():
    """Expose les graines afin de mesurer un mecanisme sur plusieurs cartes."""
    parser = argparse.ArgumentParser()
    parser.add_argument("years", type=int, nargs="?", default=10)
    parser.add_argument("seeds", type=int, nargs="*", default=[42])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workers", type=int, default=1)
    # Un reglage OpexAI par occurrence, "cle=valeur". Sert a mesurer un mecanisme que le DEFAUT
    # desactive -- station_join est passe a 0 le 2026-08-29 apres le verdict du banc, mais il faut
    # encore pouvoir l'allumer pour chiffrer la sur-estimation des lignes jointes.
    parser.add_argument("--setting", action="append", default=[], metavar="CLE=VALEUR")
    args = parser.parse_args()
    settings = []
    for item in args.setting:
        if "=" not in item:
            parser.error(f"--setting attend CLE=VALEUR, recu: {item}")
        key, _, value = item.partition("=")
        try:
            settings.append((key.strip(), int(value)))
        except ValueError:
            parser.error(f"--setting attend un entier, recu: {item}")
    args.ai_settings = tuple(settings)
    if args.years <= 0:
        parser.error("years doit etre positif")
    if not args.seeds:
        parser.error("au moins une graine est requise")
    if args.workers <= 0:
        parser.error("workers doit etre positif")
    return args


def result_path_for(args):
    """Conserve les sorties de mesure dans docs sans ecraser une campagne precedente."""
    if args.output is not None:
        return args.output if args.output.is_absolute() else ROOT / args.output
    suffix = "_".join(str(seed) for seed in args.seeds)
    return ROOT / "docs" / f"opex_full_campaign_{args.years}y_{suffix}.json"


def main():
    args = parse_args()
    result_path = result_path_for(args)
    experiments = [{
        "seed": seed, "days": 365 * args.years, "openttd_config": CFG,
        "ais": (local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", args.ai_settings),),
        "opex_seed": seed,
    } for seed in args.seeds]
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        max_workers=min(args.workers, len(args.seeds)), result_processor=keep,
        experiments=experiments,
        ai_libraries=(bananas_ai_library("5046524c", "Pathfinder.Rail"),),
    ))
    rows_by_seed = {seed: [] for seed in args.seeds}
    for row in rows:
        rows_by_seed[row["seed"]].append(row)
    missing = [seed for seed, series in rows_by_seed.items() if not series]
    if missing:
        raise RuntimeError(f"aucune sauvegarde pour les graines: {missing}")

    runs = [make_run_payload(rows_by_seed[seed], seed, args.years) for seed in args.seeds]
    payload = {
        "openttd_version": OPENTTD_VERSION, "opengfx_version": OPENGFX_VERSION,
        "years": args.years, "seeds": args.seeds, "openttd_config": CFG,
        "ai_settings": {key: value for key, value in args.ai_settings},
        "instrumentation_added": ["CG", "CR", "CD", "CE", "CK", "PC", "PM", "OB|A", "GM", "OB|J",
                                  "CJ", "OB|S", "PJ"],
        "runs": runs,
    }
    result_path.write_text(json.dumps(payload, indent=2))
    for run in runs:
        print(f"=== {args.years} ans, graine {run['seed']} ===")
        print(f"lignes rail OK: {run['n_rail_lines_ok']}  (tentatives totales: "
              f"{run['n_rail_attempts_total']}, echouees: {run['n_rail_attempts_failed']})")
        print(f"company_value final: {run['final_company_value']}  "
              f"performance_history: {run['final_performance_history']}")
        print(f"money: {run['final_money']}  current_loan: {run['final_current_loan']}")
        print(f"n_vehicles: {run['final_n_vehicles']}  n_stations: {run['final_n_stations']}")
        print(f"annees franchies: {run['calendar_years_crossed']}  "
              f"non rattrapees: {run['skipped_years']}")
    print("ecrit", result_path)


if __name__ == "__main__":
    main()
