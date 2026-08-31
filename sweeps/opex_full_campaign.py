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
RE_OQ = re.compile(r"^OQ\|(\d+)\|(-?\d+)\|(\d+)(?:\|(\d+)\|(\d+))?$")
RE_OT = re.compile(r"^OT\|(\d+)\|(-?\d+)(?:\|(\d+)(?:\|(\d+)\|(\d+))?)?$")
RE_OL_TRACTION = re.compile(r"^OL\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")
RE_PL = re.compile(r"^PL\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")
RE_PT = re.compile(r"^PT\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")
RE_PG = re.compile(r"^PG\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")
RE_PD = re.compile(r"^PD\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)(?:\|(\d+))?$")
RE_PS = re.compile(r"^PS\|(\d{2})\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)(?:\|([PF]))?(?:\|([ABN]))?$")
RE_OY = re.compile(r"^OY\|(\d+)\|(\d+)\|(-?\d+)\|(-?\d+)$")
RE_RV = re.compile(r"^RV\|(\d{2})\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")  # yy, id, nMoving, med, pred, cat
RE_RY = re.compile(r"^RY\|(\d{2})\|(\d+)\|([PF])\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")  # yy, id, kind, nMoving, med, pred, cat
RE_OZ = re.compile(r"^OZ\|(\d+)\|(\d+)\|(-?\d+)$")
RE_OU = re.compile(r"^OU\|(\d+)\|(\d+)\|(\d+)\|(-?\d+)$")
RE_OO = re.compile(r"^OO\|(\d+)\|(\d+)\|(-?\d+)$")
RE_OR = re.compile(r"^OR\|(\d+)\|(\d+)\|(\d+)\|(\w+)$")  # historique avant mesure abandon
RE_OR_BUDGET = re.compile(r"^OR\|(\d{2})\|(\d+)\|(\d+)\|([ZFCN][SL][KADPLHMJSTERVXBCGFU])\|(\d+)\|(\d+)$")
RE_OB_ATTEMPT = re.compile(r"^OB\|A\|(\d{2})\|(\d+)\|(\d+)\|(\d+)(?:\|(\d+))?$")
RE_PK = re.compile(r"^PK\|(\d+)\|([PF])\|(\d+)$")
RE_PC = re.compile(r"^PC\|(\d+)\|(.+)$")
# Marqueur par LIGNE de la tranche jointure (2026-08-29) : extremite jointe ("A"/"B"/"N")
# et origine deja desservie (0/1). 4e champ optionnel : P = H2 place-first, T = v1 tooClose.
# Emis quand station_join = 1 ou join_place = 1.
RE_PJ = re.compile(r"^PJ\|(\d+)\|([ABN])\|([01])(?:\|([PT]))?$")
RE_PH = re.compile(r"^PH\|(\d{2})\|(\d+)\|(\d+)\|(\d+)$")  # yy, gen, ranked, built
RE_SG = re.compile(r"^SG\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")  # id, ok, fail, junc
RE_SJ = re.compile(r"^SJ\|(\d+)\|(\d+)\|(\d+)$")  # id, skip, nfailures
RE_JF = re.compile(r"^JF\|(\d+)\|([ABLR])\|(\d+)\|(-?\d+)\|(\d+)\|(\d+)\|(\d+)$")
RE_SC = re.compile(r"^SC\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")  # id, ok, fail, segments
RE_SF = re.compile(r"^SF\|(\d+)\|(\d+)\|(-?\d+)\|(\d+)\|(\d+)\|(\d+)$")
RE_RX = re.compile(r"^RX\|(\d{2})\|(\d+)\|(\d+)\|(\d+)$")  # yy, id, lost, total
RE_XC = re.compile(r"^XC\|(\d{2})\|(-?\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")
RE_DT = re.compile(r"^DT\|(\d+)\|([01])\|(\d+)\|(\d+)$")  # id, posed, trains, skip
RE_PM = re.compile(r"^PM\|(\d+)\|([AWR])\|(\d+)\|(.+)$")
RE_IA = re.compile(r"^IA\|(\d+)\|(\d+)\|(-?\d)\|(-?\d)\|(-?\d+)$")
RE_OX = re.compile(r"^OX\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")   # year, towns, industries, ranked.all
RE_TV = re.compile(r"^TV\|(\d{2})\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")  # yy, nServed, medS, nFree, medU
RE_OW = re.compile(r"^OW\|(\d+)\|(\d+)\|(\d+)$")          # year, buildOps, lines.len() (as of start of year)
RE_OS = re.compile(r"^OS\|(\d+)\|(\d+)\|(\d+)$")          # year, cand_rank opcodes, utilisationPerMille
RE_CG = re.compile(r"^CG\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")
RE_CR = re.compile(r"^CR\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")
RE_CD = re.compile(r"^CD\|(\d+)\|(\d+)\|(\d+)$")
RE_CE = re.compile(r"^CE\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")
RE_CK = re.compile(r"^CK\|(\d+)\|(\d+)\|(\d+)$")
RE_DC = re.compile(r"^DC\|(\d+)\|(\d+)\|(-?\d+)\|(\d+)\|(\d+)\|([01])$")
RE_GN = re.compile(r"^GN\|(\d+)\|(\d+)\|(\d+)$")
RE_GM = re.compile(r"^GM\|(\d+)\|(\d+)$")                 # candidats exclus par memoire ABND
RE_OB_JOIN = re.compile(r"^OB\|J\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")
# Refus de jointure AVANT tentative (2026-08-30) : multi / kind-cargo / role fret / autre.
RE_OB_REFUSE = re.compile(r"^OB\|R\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)(?:\|(\d+))?$")
# Tranche du 2026-08-29 : part du TOP_K qui n'existe QUE parce qu'une extremite deja servie
# peut etre reprise par un quai joint (annee, ces candidats, taille du classement).
RE_OB_SERVED = re.compile(r"^OB\|S\|(\d+)\|(\d+)\|(\d+)$")
# Devenir des paires a UNE seule extremite servie : irrecuperables / poursuivies.
RE_CJ = re.compile(r"^CJ\|(\d+)\|(\d+)\|(\d+)$")
RE_GC = re.compile(r"^GC\|(\d+)\|(-?\d+)\|(\d+)$")
RE_DL = re.compile(r"^DL\|(\d+)\|(\d+)\|(\d+)$")
RE_LR = re.compile(r"^LR\|(\d+)\|(\d+)\|(\d+)$")
RE_GL = re.compile(r"^GL\|(\d+)\|(\d+)\|(\d+)\|([01])$")  # reemprunt : year, drew, newLoan, covered
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
RE_RM_ROAD = re.compile(r"^RM\|(\d{2})\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")  # nStopsA / nStopsB / veh
RE_RA_ROAD = re.compile(r"^RA\|(\d{2})\|(\d+)\|(\d+)\|(\w+)\|(-?\d+)$")  # tentative echouee
RE_RI_ROAD = re.compile(r"^RI\|(\d{2})\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")  # SITE cargo/buildable/cmd
RE_RT_ROAD = re.compile(r"^RT\|(\d{2})\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")  # TRACEX trials/long/hit/unb
RE_RB_ROAD = re.compile(r"^RB\|(\d{2})\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")   # opcodes plan / construction
RE_RN_ROAD = re.compile(r"^RN\|(\d{2})\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")  # classes/tentatives/baties/opcodes
RE_RS_ROAD = re.compile(r"^RS\|(\d{2})\|(\d+)\|(\d+)\|(\d+)$")  # paires en bande / coupees / acceptees
RE_RF_ROAD = re.compile(r"^RF\|(\d+)\|(\d+)\|(\d+)\|(.+)$")  # year, id, added, after|reason
RE_EU_EXPAND = re.compile(r"^EU\|(\d{2})\|(\d+)\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")
RE_EG_EXPAND = re.compile(r"^EG\|(\d{2})\|(\d+)\|(\d+)\|(\d+)\|(-?\d+)$")
RE_ES_EXPAND = re.compile(r"^ES\|(\d{2})\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")
RE_EX_EXPAND = re.compile(r"^EX\|(\d{2})\|(\d+)\|([A-Z])\|(\d+)\|(-?\d+)$")
RE_YT = re.compile(r"^YT\|(\d{2})\|(\d+)\|(\d+)\|(\d+)\|(\d+)(C)?$")
# Item 7 : sondage des paires a profit predit <= 0. Absents si probe_negative = 0.
RE_PN = re.compile(r"^PN\|(\d{2})\|(\d+)\|(-?\d+)\|(\d+)\|([A-Z])\|(\d+)$")
RE_PX = re.compile(r"^PX\|(\d+)$")
RE_PQ = re.compile(r"^PQ\|(\d{2})\|(\d+)\|(\d+)\|(\d+)\|([01])$")
RE_NH = re.compile(r"^NH\|(\d{2})\|(\d+)\|(\d+)\|(\d+)\|(\d+)$")
RE_NM = re.compile(r"^NM\|(\d{2})\|(\d+)\|(\d+)\|(\d+)\|(-?\d+)$")
RE_PE = re.compile(r"^PE\|(\d{2})\|(\d+)\|(\d+)\|(\d+)$")
RE_PY = re.compile(r"^PY\|(\d+)$")

TOP_K = 20  # Doit rester synchronise avec ai/OpexAI/candidates.nut, pour decoder rang20.
REASON_CODES = {
    "K": "OK", "A": "ABND", "D": "DEAD", "P": "NOPA", "L": "NOPLAN",
    "B": "SITEA", "C": "SITEB", "G": "SITEAB", "F": "ECON",
    "H": "SHORT", "M": "NOMATCH", "J": "JOINPATH", "S": "STNFAIL", "T": "TRKFAIL",
    "E": "DEPFAIL", "U": "SIGFAIL", "R": "ORDFAIL", "V": "NOTRAIN", "X": "UNKNOWN",
}


def unpack_rank(packed):
    """Inverse rang * TOP_K + longueur, range 0..TOP_K-1 et longueur 1..TOP_K."""
    rank = (packed - 1) // TOP_K
    length = packed - rank * TOP_K
    if not (0 <= rank < TOP_K and 1 <= length <= TOP_K):
        raise ValueError(f"rang20 invalide: {packed}")
    return rank, length


# Doit rester aligne sur ai/OpexAI/candidates.nut. Sert a rapporter le ratio reel/modele
# des tentatives, y compris les echecs, des que OB|A porte la distance.
KNOT_DISTANCE = (23, 33, 48, 63, 81, 105, 150)
KNOT_ITERATIONS = (371, 673, 2188, 4066, 7745, 15308, 53951)
DISTANCE_BANDS = ((0, 35), (35, 50), (50, 70), (70, 105), (105, 201))


def opex_rail_iterations(distance):
    """Interpolation entiere de OpexRailIterations, pour le depouillement Python."""
    if distance <= KNOT_DISTANCE[0]:
        return KNOT_ITERATIONS[0]
    for i in range(1, len(KNOT_DISTANCE)):
        if distance <= KNOT_DISTANCE[i]:
            d0, d1 = KNOT_DISTANCE[i - 1], KNOT_DISTANCE[i]
            v0, v1 = KNOT_ITERATIONS[i - 1], KNOT_ITERATIONS[i]
            return v0 + ((v1 - v0) * (distance - d0)) // (d1 - d0)
    last = len(KNOT_DISTANCE) - 1
    slope = (KNOT_ITERATIONS[last] - KNOT_ITERATIONS[last - 1]) // (
        KNOT_DISTANCE[last] - KNOT_DISTANCE[last - 1])
    return KNOT_ITERATIONS[last] + slope * (distance - KNOT_DISTANCE[last])


def _median(values):
    values = sorted(values)
    if not values:
        return None
    mid = len(values) // 2
    if len(values) % 2:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2


def summarise_attempt_distance(attempts):
    """P(construite | distance) : le denominateur que les seules reussites ne donnent pas."""
    with_distance = [item for item in attempts if item.get("distance") is not None]
    bands = []
    for lo, hi in DISTANCE_BANDS:
        if lo == 0:
            in_band = [item for item in with_distance if item["distance"] <= hi]
        else:
            in_band = [item for item in with_distance if lo < item["distance"] <= hi]
        ok = [item for item in in_band if item["reason"] == "OK"]
        abnd = [item for item in in_band if item["reason"] == "ABND"]
        site = [item for item in in_band if item["reason"] in ("SITEA", "SITEB", "SITEAB", "ECON", "NOPLAN")]
        astar = [item for item in in_band if item["reason"] not in ("SITEA", "SITEB", "SITEAB", "ECON", "NOPLAN")]
        ratios_ok = []
        for item in ok:
            predicted = opex_rail_iterations(item["distance"])
            if predicted > 0:
                ratios_ok.append(item["iterations"] / predicted)
        iter_all = sum(item.get("iterations") or 0 for item in in_band)
        bands.append({
            "lo": lo, "hi": hi, "n": len(in_band), "n_ok": len(ok), "n_abnd": len(abnd),
            "n_site": len(site),
            "p_ok": round(len(ok) / len(in_band), 4) if in_band else None,
            "p_ok_astar": round(len(ok) / len(astar), 4) if astar else None,
            "median_iterations_ok": _median([item["iterations"] for item in ok]),
            "amort_iterations": (iter_all / len(ok)) if ok else None,
            "median_ratio_ok": _median(ratios_ok),
        })
    return {
        "n_attempts": len(attempts),
        "n_with_distance": len(with_distance),
        "n_ok": sum(1 for item in with_distance if item["reason"] == "OK"),
        "n_abnd": sum(1 for item in with_distance if item["reason"] == "ABND"),
        "bands": bands,
    }


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
    road_multi = {}
    join_marks = {}
    probe_built = {}
    probe_pn = {}

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
            if m.group(4) is not None:
                predicted[idx]["wagons"] = int(m.group(4))
                predicted[idx]["perTrain"] = int(m.group(5))
        elif m := RE_OT.match(sign):
            idx = int(m.group(1)); predicted.setdefault(idx, {})["oneWayDays"] = int(m.group(2))
            if m.group(3) is not None:
                predicted[idx]["distance"] = int(m.group(3))
            if m.group(4) is not None:
                predicted[idx]["platformLength"] = int(m.group(4))
                predicted[idx]["effectiveSpeed"] = int(m.group(5))
        elif m := RE_OL_TRACTION.match(sign):
            idx = int(m.group(1)); pred = predicted.setdefault(idx, {})
            pred["locoId"] = int(m.group(2)); pred["locoCatalogSpeed"] = int(m.group(3))
            pred["effectiveSpeed"] = int(m.group(4)); pred["locoPower"] = int(m.group(5))
            pred["locoTractiveEffort"] = int(m.group(6))
        elif m := RE_PL.match(sign):
            idx = int(m.group(1)); pred = predicted.setdefault(idx, {})
            pred["builtPlatformLength"] = int(m.group(2)); pred["builtWagons"] = int(m.group(3))
            pred["trainLength16"] = int(m.group(4))
            pred["locoLength16"] = int(m.group(5)); pred["wagonLength16"] = int(m.group(6))
        elif m := RE_PT.match(sign):
            idx = int(m.group(1)); pred = predicted.setdefault(idx, {})
            pred["offered"] = int(m.group(2)); pred["monthlyCapacity"] = int(m.group(3))
            pred["headwayDays"] = int(m.group(4)); pred["stationRating"] = int(m.group(5))
            pred["trainsForHeadway"] = int(m.group(6))
        elif m := RE_PG.match(sign):
            idx = int(m.group(1)); pred = predicted.setdefault(idx, {})
            pred["plansA12"] = int(m.group(2)); pred["plansA4"] = int(m.group(3))
            pred["plansB12"] = int(m.group(4)); pred["plansB4"] = int(m.group(5))
        elif m := RE_PD.match(sign):
            idx = int(m.group(1)); pred = predicted.setdefault(idx, {})
            pred["wantedPlatformLength"] = int(m.group(2))
            pred["builtPlatformLength"] = int(m.group(3))
            pred["plansA"] = int(m.group(4)); pred["plansB"] = int(m.group(5))
            if m.group(6) is not None:
                pred["slopeRelaxed"] = int(m.group(6))
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
                                           "origin_served": m.group(3) == "1",
                                           "place_join": m.group(4) == "P"}
        elif m := RE_SG.match(sign):
            idx = int(m.group(1))
            predicted.setdefault(idx, {})
            predicted[idx]["signals_ok"] = int(m.group(2))
            predicted[idx]["signals_fail"] = int(m.group(3))
            predicted[idx]["signal_junc"] = int(m.group(4))
        elif m := RE_SJ.match(sign):
            idx = int(m.group(1))
            predicted.setdefault(idx, {})
            predicted[idx]["signals_skip"] = int(m.group(2))
            predicted[idx]["signal_failure_count"] = int(m.group(3))
        elif m := RE_SC.match(sign):
            idx = int(m.group(1))
            predicted.setdefault(idx, {})
            predicted[idx]["capacity_signals_ok"] = int(m.group(2))
            predicted[idx]["capacity_signals_fail"] = int(m.group(3))
            predicted[idx]["capacity_signal_segments"] = int(m.group(4))
        elif m := RE_DT.match(sign):
            idx = int(m.group(1))
            predicted.setdefault(idx, {})
            predicted[idx]["double_track"] = int(m.group(2))
            predicted[idx]["double_trains"] = int(m.group(3))
            predicted[idx]["double_skip"] = int(m.group(4))
        elif m := RE_DC.match(sign):
            idx = int(m.group(1))
            predicted.setdefault(idx, {})["modelCapital"] = int(m.group(2))
            predicted[idx]["actualCost"] = int(m.group(3))
            predicted[idx]["predictedTrains"] = int(m.group(4))
            predicted[idx]["actualTrains"] = int(m.group(5))
            predicted[idx]["costDoubleTrack"] = int(m.group(6))
        elif m := RE_PC.match(sign):
            predicted.setdefault(int(m.group(1)), {})["cargo_label"] = m.group(2)
        elif m := RE_PX.match(sign):
            probe_built[int(m.group(1))] = True
        elif m := RE_PY.match(sign):
            predicted.setdefault(int(m.group(1)), {})["pax_near"] = True
        elif m := RE_PN.match(sign):
            # Un ABND reutilise _nextLineId : ne pas coller ce PN sur la ligne classee
            # qui reprendra le meme idx. Seulement PX (succes) autorise le merge.
            probe_pn[int(m.group(2))] = {
                "probe": True,
                "rankingProfit": int(m.group(3)),
                "rankingDistance": int(m.group(4)),
                "probeReason": m.group(5),
                "probeIterations": int(m.group(6)),
                "probeYear": 1900 + int(m.group(1)),
            }
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
        elif m := RE_RM_ROAD.match(sign):
            idx = int(m.group(2))
            road_multi[idx] = {"n_stops_a": int(m.group(4)), "n_stops_b": int(m.group(5)),
                               "vehicles": int(m.group(6))}

    for idx, fields in probe_pn.items():
        if idx in probe_built:
            predicted.setdefault(idx, {}).update(fields)

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
            "pax_near": bool(pred.get("pax_near")),
            "distance": built[idx].get("distance", pred.get("distance")),
            "iterations": built[idx]["iterations"],
            "reason": built[idx]["reason"],
            # None quand station_join = 0 : le panneau n'est pas emis, et l'absence ne doit pas
            # se lire comme "ligne non jointe, origine libre" -- c'est "non mesure".
            "joined_end": mark.get("joined_end"),
            "origin_served": mark.get("origin_served"),
            "place_join": mark.get("place_join"),
            "signals_ok": pred.get("signals_ok"),
            "signals_fail": pred.get("signals_fail"),
            "signals_skip": pred.get("signals_skip"),
            "signal_junc": pred.get("signal_junc"),
            "capacity_signals_ok": pred.get("capacity_signals_ok"),
            "capacity_signals_fail": pred.get("capacity_signals_fail"),
            "capacity_signal_segments": pred.get("capacity_signal_segments"),
            "double_track": pred.get("double_track"),
            "double_skip": pred.get("double_skip"),
            "predicted": pred,
            "actual_last_year": last_year,
            "actual": last,
            "actual_series": years,
        })
    for idx in sorted(probe_built):
        if idx in built:
            # Un probe ne pose pas OR : collision impossible avec une ligne classee.
            continue
        pred = dict(predicted.get(idx, {}))
        pred["profitAnnual"] = (pred.get("revenueAnnual", 0) - pred.get("runningAnnual", 0)
                                - pred.get("amortAnnual", 0))
        years = actual_series.get(idx, {})
        last_year = max(years) if years else None
        last = years.get(last_year, {}) if last_year is not None else {}
        lines.append({
            "line_index": idx,
            "mode": "rail",
            "probe": True,
            "distance": pred.get("rankingDistance") or pred.get("distance"),
            "iterations": pred.get("probeIterations"),
            "reason": REASON_CODES.get(pred.get("probeReason"), pred.get("probeReason")),
            "year_built": pred.get("probeYear"),
            "ranking_profit": pred.get("rankingProfit"),
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
        if idx in road_multi:
            entry["n_stops_a"] = road_multi[idx]["n_stops_a"]
            entry["n_stops_b"] = road_multi[idx]["n_stops_b"]
        lines.append(entry)
    return lines


def parse_probes(all_signs):
    """Toutes les tentatives PN, reussies ou non -- le denominateur de l'item 7."""
    attempts = []
    for sign in all_signs:
        if m := RE_PN.match(sign):
            attempts.append({
                "year": 1900 + int(m.group(1)),
                "idx": int(m.group(2)),
                "ranking_profit": int(m.group(3)),
                "distance": int(m.group(4)),
                "reason": REASON_CODES.get(m.group(5), m.group(5)),
                "iterations": int(m.group(6)),
            })
    return attempts


def summarise_probe_negative(runs):
    """Predit (rejet) vs reel (force-construit) : le biais de selection de l'etage 1."""
    yearly_rows = [row for run in runs for row in (run.get("yearly") or {}).values()]
    attempts = [item for run in runs for item in run.get("probe_attempts") or []]
    lines = []
    for run in runs:
        for line in run.get("lines") or []:
            if line.get("probe"):
                row = dict(line)
                row["_seed"] = run.get("seed")
                lines.append(row)
    funnels = [row for row in yearly_rows if "probe_tried" in row]
    bands = {
        "lt50": sum(row.get("neg_band50") or 0 for row in yearly_rows),
        "50_75": sum(row.get("neg_band75") or 0 for row in yearly_rows),
        "75_100": sum(row.get("neg_band100") or 0 for row in yearly_rows),
        "gt100": sum(row.get("neg_band200") or 0 for row in yearly_rows),
    }
    population = {
        "n_profit_non_positive": sum(row.get("candidate_profit_non_positive") or 0
                                     for row in yearly_rows),
        "n_pax": sum(row.get("neg_pax") or 0 for row in yearly_rows),
        "n_freight": sum(row.get("neg_freight") or 0 for row in yearly_rows),
        "n_near": sum(row.get("neg_near") or 0 for row in yearly_rows),
        "bands": bands,
        "mean_predicted": _median([row["neg_mean_profit"] for row in yearly_rows
                                   if row.get("neg_mean_profit") is not None]),
    }
    reasons = {}
    for item in attempts:
        reasons[item["reason"]] = reasons.get(item["reason"], 0) + 1
    actuals = []
    for line in lines:
        series = line.get("actual_series") or {}
        if not series:
            continue
        years = sorted(int(y) for y in series)
        first = series[years[0]] if years[0] in series else series[str(years[0])]
        second = None
        if len(years) >= 2:
            y2 = years[1]
            second = series[y2] if y2 in series else series[str(y2)]
        last_year = years[-1]
        last = series[last_year] if last_year in series else series[str(last_year)]
        pred = line.get("ranking_profit")
        if pred is None:
            pred = (line.get("predicted") or {}).get("rankingProfit")
        actuals.append({
            "seed": line.get("_seed"),
            "line_index": line["line_index"],
            "distance": line.get("distance"),
            "kind": (line.get("predicted") or {}).get("kind"),
            "cargo": (line.get("predicted") or {}).get("cargo_label"),
            "year_built": line.get("year_built"),
            "first_year": years[0],
            "predicted": pred,
            "actual_profit": first.get("profit"),
            "actual_revenue": first.get("revenue"),
            "actual_profit_second": None if second is None else second.get("profit"),
            "actual_profit_last": last.get("profit"),
            "vehicles": first.get("vehCount"),
            "rating_a": first.get("ratingA"),
            "rating_b": first.get("ratingB"),
        })
    def _pos(key):
        return [row for row in actuals if (row.get(key) or 0) > 0]
    ok_attempts = [item for item in attempts if item["reason"] == "OK"]
    abnd_attempts = [item for item in attempts if item["reason"] == "ABND"]
    attempt_bands = []
    for lo, hi in ((0, 50), (50, 75), (75, 100), (100, 201)):
        if lo == 0:
            in_band = [item for item in attempts if item["distance"] <= hi]
        else:
            in_band = [item for item in attempts if lo < item["distance"] <= hi]
        ok = [item for item in in_band if item["reason"] == "OK"]
        built = [row for row in actuals
                 if row.get("distance") is not None
                 and ((row["distance"] <= hi) if lo == 0 else lo < row["distance"] <= hi)]
        pos2 = [row for row in built if (row.get("actual_profit_second") or 0) > 0]
        pos_last = [row for row in built if (row.get("actual_profit_last") or 0) > 0]
        attempt_bands.append({
            "lo": lo, "hi": hi, "n": len(in_band), "n_ok": len(ok),
            "n_abnd": sum(1 for item in in_band if item["reason"] == "ABND"),
            "median_predicted": _median([item["ranking_profit"] for item in in_band]),
            "n_with_actual": len(built),
            "n_positive_second": len(pos2),
            "n_positive_last": len(pos_last),
            "median_actual_second": _median([row["actual_profit_second"] for row in built
                                             if row.get("actual_profit_second") is not None]),
            "median_actual_last": _median([row["actual_profit_last"] for row in built
                                           if row.get("actual_profit_last") is not None]),
        })
    return {
        "population": population,
        "n_funnel_years": len(funnels),
        "n_stash_offered": sum(row.get("probe_stash") or 0 for row in funnels),
        "n_skip_close": sum(row.get("probe_skip_close") or 0 for row in funnels),
        "n_skip_cash": sum(row.get("probe_skip_cash") or 0 for row in funnels),
        "n_tried": sum(row.get("probe_tried") or 0 for row in funnels),
        "n_attempts": len(attempts),
        "reasons": reasons,
        "n_ok": len(ok_attempts),
        "n_abnd": len(abnd_attempts),
        "median_ranking_profit_tried": _median([item["ranking_profit"] for item in attempts]),
        "median_distance_tried": _median([item["distance"] for item in attempts]),
        "median_distance_ok": _median([item["distance"] for item in ok_attempts]),
        "median_distance_abnd": _median([item["distance"] for item in abnd_attempts]),
        "n_lines_with_actual": len(actuals),
        "n_actual_profit_positive": len(_pos("actual_profit")),
        "n_actual_profit_positive_second": len(_pos("actual_profit_second")),
        "n_actual_profit_positive_last": len(_pos("actual_profit_last")),
        "p_actual_positive": (round(len(_pos("actual_profit")) / len(actuals), 4) if actuals else None),
        "p_actual_positive_second": (round(len(_pos("actual_profit_second")) / len(actuals), 4)
                                     if actuals else None),
        "median_actual_profit": _median([row["actual_profit"] for row in actuals
                                         if row.get("actual_profit") is not None]),
        "median_actual_profit_second": _median([row["actual_profit_second"] for row in actuals
                                                if row.get("actual_profit_second") is not None]),
        "median_actual_profit_last": _median([row["actual_profit_last"] for row in actuals
                                              if row.get("actual_profit_last") is not None]),
        "median_predicted_of_ok": _median([row["predicted"] for row in actuals
                                           if row.get("predicted") is not None]),
        "attempt_bands": attempt_bands,
        "lines": actuals,
    }


def parse_attempts(all_signs):
    """Toutes les tentatives OR (rail), y compris les echecs -- pour distinguer les rejets par
    tentative-echouee (TRKFAIL, NOPLAN, ...) des rejets INVISIBLES (_tooClose continue, argent
    break) qui ne generent aucun sign."""
    attempts = []
    opcodes = {}
    distances = {}
    site_stats = {}
    for sign in all_signs:
        if m := RE_OB_ATTEMPT.match(sign):
            key = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
            opcodes[key] = int(m.group(4))
            if m.group(5) is not None:
                distances[key] = int(m.group(5))
        elif m := RE_PS.match(sign):
            stats = {
                "n_clear": int(m.group(4)), "n_cargo": int(m.group(5)), "n_cmd": int(m.group(6)),
            }
            if m.group(7):
                stats["kind"] = "pax" if m.group(7) == "P" else "freight"
            if m.group(8):
                stats["join_end"] = m.group(8)
            site_stats[(int(m.group(1)), int(m.group(2)), int(m.group(3)))] = stats
    for sign in all_signs:
        if m := RE_OR_BUDGET.match(sign):
            packed = int(m.group(3))
            rank, ranked_len = unpack_rank(packed)
            mode = m.group(4)
            year_mod, idx = int(m.group(1)), int(m.group(2))
            key = (year_mod, idx, packed)
            item = {"year": 1900 + year_mod, "idx": idx,
                    "rank": rank, "ranked_len": ranked_len,
                    "budget_path": mode[0], "alternative_source": mode[1],
                    "reason": REASON_CODES[mode[2]], "iteration_budget": int(m.group(5)),
                    "iterations": int(m.group(6)),
                    "opcodes": opcodes.get(key),
                    "distance": distances.get(key)}
            stats = site_stats.get(key)
            if stats:
                item.update(stats)
            attempts.append(item)
        elif m := RE_OR.match(sign):
            attempts.append({"idx": int(m.group(1)), "distance": int(m.group(2)),
                              "iterations": int(m.group(3)), "reason": m.group(4)})
    return attempts


def parse_safety(all_signs):
    """Signaux de capacite/jointure et detecteurs de collision, y compris les rollbacks SIGFAIL."""
    capacity, capacity_failures = [], []
    join, join_skips, join_failures = [], [], []
    unexpected_losses, train_crashes = [], []
    double_tracks = []
    for sign in all_signs:
        if m := RE_SC.match(sign):
            capacity.append({"line_index": int(m.group(1)), "ok": int(m.group(2)),
                             "fail": int(m.group(3)), "segments": int(m.group(4))})
        elif m := RE_SF.match(sign):
            capacity_failures.append({
                "line_index": int(m.group(1)), "slot": int(m.group(2)),
                "error": int(m.group(3)), "tracks": int(m.group(4)),
                "x": int(m.group(5)), "y": int(m.group(6)),
            })
        elif m := RE_SG.match(sign):
            join.append({"line_index": int(m.group(1)), "ok": int(m.group(2)),
                         "fail": int(m.group(3)), "junc": int(m.group(4))})
        elif m := RE_SJ.match(sign):
            join_skips.append({"line_index": int(m.group(1)), "skip": int(m.group(2)),
                               "n_failures": int(m.group(3))})
        elif m := RE_JF.match(sign):
            join_failures.append({
                "line_index": int(m.group(1)), "kind": m.group(2), "slot": int(m.group(3)),
                "error": int(m.group(4)), "tracks": int(m.group(5)),
                "x": int(m.group(6)), "y": int(m.group(7)),
            })
        elif m := RE_RX.match(sign):
            unexpected_losses.append({
                "year": 1900 + int(m.group(1)), "line_index": int(m.group(2)),
                "lost": int(m.group(3)), "total": int(m.group(4)),
            })
        elif m := RE_XC.match(sign):
            train_crashes.append({
                "year": 1900 + int(m.group(1)), "line_index": int(m.group(2)),
                "vehicle": int(m.group(3)), "x": int(m.group(4)),
                "y": int(m.group(5)), "victims": int(m.group(6)),
            })
        elif m := RE_DT.match(sign):
            double_tracks.append({
                "line_index": int(m.group(1)), "posed": int(m.group(2)),
                "trains": int(m.group(3)), "skip": int(m.group(4)),
            })
    return {
        "capacity_signals": capacity,
        "capacity_signal_failures": capacity_failures,
        "join_signals": join,
        "join_signal_skips": join_skips,
        "join_signal_failures": join_failures,
        "unexpected_train_losses": unexpected_losses,
        "train_crashes": train_crashes,
        "n_capacity_signals_ok": sum(item["ok"] for item in capacity),
        "n_capacity_signals_fail": sum(item["fail"] for item in capacity),
        "n_capacity_signal_segments": sum(item["segments"] for item in capacity),
        "n_capacity_signal_failures": len(capacity_failures),
        "n_join_signals_ok": sum(item["ok"] for item in join),
        "n_join_signals_fail": sum(item["fail"] for item in join),
        "n_join_signal_junc": sum(item["junc"] for item in join),
        "n_join_signals_skip": sum(item["skip"] for item in join_skips),
        "n_join_signal_failures": len(join_failures),
        "n_rx_events": len(unexpected_losses),
        "n_unexpected_trains_lost": sum(item["lost"] for item in unexpected_losses),
        "n_train_crashes": len(train_crashes),
        "double_tracks": double_tracks,
        "n_double_track_ok": sum(item["posed"] for item in double_tracks),
        "n_double_track_tried": len(double_tracks),
        "n_double_track_trains": sum(item["trains"] for item in double_tracks if item["posed"]),
    }


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
        elif m := RE_TV.match(sign):
            y = 1900 + int(m.group(1))
            d = by_year.setdefault(y, {})
            d["pop_n_served"] = int(m.group(2))
            d["pop_served_median"] = int(m.group(3))
            d["pop_n_free"] = int(m.group(4))
            d["pop_free_median"] = int(m.group(5))
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
        elif m := RE_OB_REFUSE.match(sign):
            y = int(m.group(1)); d = by_year.setdefault(y, {})
            d["join_refuse_multi"] = int(m.group(2))
            d["join_refuse_kind"] = int(m.group(3))
            d["join_refuse_role"] = int(m.group(4))
            d["join_refuse_other"] = int(m.group(5))
            d["join_refuse_dist"] = int(m.group(6) or 0)
        elif m := RE_OB_SERVED.match(sign):
            y = int(m.group(1)); d = by_year.setdefault(y, {})
            d["ranked_origin_served"] = int(m.group(2))
            d["ranked_total"] = int(m.group(3))
        elif m := RE_PH.match(sign):
            y = 1900 + int(m.group(1)); d = by_year.setdefault(y, {})
            d["place_join_generated"] = int(m.group(2))
            d["place_join_ranked"] = int(m.group(3))
            d["place_join_built"] = int(m.group(4))
        elif m := RE_CJ.match(sign):
            y = int(m.group(1)); d = by_year.setdefault(y, {})
            d["candidate_pairs_join_impossible"] = int(m.group(2))
            d["candidate_pairs_one_served"] = int(m.group(3))
        elif m := RE_NH.match(sign):
            y = 1900 + int(m.group(1)); d = by_year.setdefault(y, {})
            d["neg_band50"] = int(m.group(2))
            d["neg_band75"] = int(m.group(3))
            d["neg_band100"] = int(m.group(4))
            d["neg_band200"] = int(m.group(5))
        elif m := RE_NM.match(sign):
            y = 1900 + int(m.group(1)); d = by_year.setdefault(y, {})
            d["neg_pax"] = int(m.group(2))
            d["neg_freight"] = int(m.group(3))
            d["neg_near"] = int(m.group(4))
            d["neg_mean_profit"] = int(m.group(5))
        elif m := RE_PQ.match(sign):
            y = 1900 + int(m.group(1)); d = by_year.setdefault(y, {})
            d["probe_stash"] = int(m.group(2))
            d["probe_skip_close"] = int(m.group(3))
            d["probe_skip_cash"] = int(m.group(4))
            d["probe_tried"] = int(m.group(5))
        elif m := RE_PE.match(sign):
            y = 1900 + int(m.group(1)); d = by_year.setdefault(y, {})
            d["pax_near_admitted"] = int(m.group(2))
            d["pax_near_tried"] = int(m.group(3))
            d["pax_near_ok"] = int(m.group(4))
    return dict(sorted(by_year.items()))


def summarise_town_growth(yearly):
    """Ratio  derniere/premiere annee des medianes TV (villes desservies vs libres)."""
    rows = []
    for year, row in yearly.items():
        if "pop_served_median" not in row:
            continue
        rows.append((int(year), row))
    if len(rows) < 2:
        return {}
    rows.sort()
    last_year, last = rows[-1]
    first_year, first = rows[0]
    for year, row in rows:
        if (row.get("pop_n_served") or 0) > 0:
            first_year, first = year, row
            break
    def ratio(a, b):
        if not a:
            return None
        return b / a
    return {
        "first_year": first_year,
        "last_year": last_year,
        "n_served_first": first.get("pop_n_served"),
        "n_served_last": last.get("pop_n_served"),
        "n_free_first": first.get("pop_n_free"),
        "n_free_last": last.get("pop_n_free"),
        "pop_served_first": first.get("pop_served_median"),
        "pop_served_last": last.get("pop_served_median"),
        "pop_free_first": first.get("pop_free_median"),
        "pop_free_last": last.get("pop_free_median"),
        "served_ratio": ratio(first.get("pop_served_median") or 0, last.get("pop_served_median") or 0),
        "free_ratio": ratio(first.get("pop_free_median") or 0, last.get("pop_free_median") or 0),
    }


def _speed_yield_from_samples(samples):
    """Mediane et rapports pour un jeu d'instantanes RV/RY."""
    moving = [s for s in samples if s["n_moving"] > 0 and s["catalog_speed"] > 0]
    def ratios(key):
        out = []
        for s in moving:
            denom = s[key]
            if denom > 0:
                out.append(s["median_speed"] / denom)
        return out
    vs_cat = ratios("catalog_speed")
    vs_pred = ratios("pred_speed")
    vs_cat.sort()
    vs_pred.sort()
    def mid(vals):
        return vals[len(vals) // 2] if vals else None
    return {
        "n_samples": len(samples),
        "n_moving": len(moving),
        "median_vs_catalog": mid(vs_cat),
        "median_vs_pred": mid(vs_pred),
        "p10_vs_catalog": vs_cat[len(vs_cat) // 10] if vs_cat else None,
        "p90_vs_catalog": vs_cat[(9 * len(vs_cat)) // 10] if vs_cat else None,
        "median_speed": mid(sorted(s["median_speed"] for s in moving)) if moving else None,
        "median_catalog": mid(sorted(s["catalog_speed"] for s in moving)) if moving else None,
        "median_pred": mid(sorted(s["pred_speed"] for s in moving)) if moving else None,
        "samples": samples,
    }


def parse_speed_yield(all_signs):
    """Instantanes RV : vitesse mediane des trains en marche vs traction et catalogue."""
    samples = []
    for sign in all_signs:
        if m := RE_RV.match(sign):
            n_moving, med, pred, cat = (int(m.group(3)), int(m.group(4)),
                                        int(m.group(5)), int(m.group(6)))
            samples.append({
                "year": 1900 + int(m.group(1)),
                "line_index": int(m.group(2)),
                "n_moving": n_moving,
                "median_speed": med,
                "pred_speed": pred,
                "catalog_speed": cat,
            })
    return _speed_yield_from_samples(samples)


def parse_road_speed_yield(all_signs):
    """Instantanes RY : vitesse mediane des vehicules routiers en marche vs 60 % et catalogue."""
    samples = []
    for sign in all_signs:
        if m := RE_RY.match(sign):
            samples.append({
                "year": 1900 + int(m.group(1)),
                "line_index": int(m.group(2)),
                "kind": "pax" if m.group(3) == "P" else "freight",
                "n_moving": int(m.group(4)),
                "median_speed": int(m.group(5)),
                "pred_speed": int(m.group(6)),
                "catalog_speed": int(m.group(7)),
            })
    out = _speed_yield_from_samples(samples)
    for kind in ("pax", "freight"):
        sub = _speed_yield_from_samples([s for s in samples if s["kind"] == kind])
        out[kind] = {k: v for k, v in sub.items() if k != "samples"}
    return out


def parse_events(all_signs):
    """Retient les evenements rares qui expliquent les variations de parc et d'emprunt."""
    cash_blocks, dead_lines, loan_repayments, loan_draws, road_refleets = [], [], [], [], []
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
        elif m := RE_GL.match(sign):
            loan_draws.append({"year": int(m.group(1)), "drew": int(m.group(2)),
                               "new_loan": int(m.group(3)), "covered": int(m.group(4))})
        elif m := RE_RF_ROAD.match(sign):
            added = int(m.group(3))
            tail = m.group(4)
            event = {"year": int(m.group(1)), "line_index": int(m.group(2)), "added": added}
            if added > 0:
                event["after"] = int(tail)
            else:
                event["reason"] = tail
            road_refleets.append(event)
        elif m := RE_LF.match(sign):
            seen_at_repay[int(m.group(1))] = {"cash": int(m.group(2)), "loan": int(m.group(3))}
        elif m := RE_LB.match(sign):
            seen_before_block[int(m.group(1))] = int(m.group(2))

    return (cash_blocks, dead_lines, loan_repayments, loan_draws, road_refleets,
            loan_view(seen_at_repay, seen_before_block))


def parse_rail_expansions(all_signs):
    """Funnel annuel, decisions et resultat atomique des ajouts de wagon."""
    funnels, decisions, results = [], {}, []
    saturation = {}
    for sign in all_signs:
        if m := RE_EU_EXPAND.match(sign):
            funnels.append({
                "year": 1900 + int(m.group(1)), "eligible": int(m.group(2)),
                "saturated": int(m.group(3)), "persistent": int(m.group(4)),
                "positive": int(m.group(5)), "decision_opcodes": int(m.group(6)),
            })
        elif m := RE_EG_EXPAND.match(sign):
            key = (int(m.group(1)), int(m.group(2)))
            decisions[key] = {
                "year": 1900 + key[0], "line_index": key[1],
                "old_wagons": int(m.group(3)), "new_wagons": int(m.group(4)),
                "expected_profit_annual": int(m.group(5)),
            }
        elif m := RE_ES_EXPAND.match(sign):
            saturation[(int(m.group(1)), int(m.group(2)))] = {
                "waiting": int(m.group(3)), "utilisation_permille": int(m.group(4)),
                "streak": int(m.group(5)),
            }
        elif m := RE_EX_EXPAND.match(sign):
            key = (int(m.group(1)), int(m.group(2)))
            results.append({
                "year": 1900 + key[0], "line_index": key[1], "reason": m.group(3),
                "transaction_opcodes": int(m.group(4)), "cost_or_error": int(m.group(5)),
            })
    for key, decision in decisions.items():
        decision.update(saturation.get(key, {}))
    for result in results:
        # Le trajet vers le depot peut franchir le 31 decembre : EX porte alors l'annee
        # d'arrivee, EG celle de la decision. Associer la derniere decision anterieure de la ligne.
        prior = [decision for decision in decisions.values()
                 if decision["line_index"] == result["line_index"]
                 and decision["year"] <= result["year"]]
        if prior:
            result.update(max(prior, key=lambda decision: decision["year"]))
    successful = [result for result in results if result["reason"] == "K"]
    total_ops = (sum(row["decision_opcodes"] for row in funnels)
                 + sum(row["transaction_opcodes"] for row in results))
    expected_profit = sum(row.get("expected_profit_annual", 0) for row in successful)
    return {
        "funnels": funnels, "decisions": list(decisions.values()), "results": results,
        "n_success": len(successful), "n_fail": len(results) - len(successful),
        "expected_profit_annual": expected_profit, "opcodes": total_ops,
        "expected_profit_per_mopcode": (
            expected_profit * 1_000_000 / total_ops if total_ops else None),
        "capital": sum(row["cost_or_error"] for row in successful),
    }


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
    road_site = {}
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
        elif m := RE_RI_ROAD.match(sign):
            road_site[(int(m.group(1)), int(m.group(2)), int(m.group(3)))] = {
                "n_cargo": int(m.group(4)), "n_buildable": int(m.group(5)),
                "n_cmd": int(m.group(6))}
        elif m := RE_RT_ROAD.match(sign):
            road_site[(int(m.group(1)), int(m.group(2)), int(m.group(3)))] = {
                "n_trials": int(m.group(4)), "n_long": int(m.group(5)),
                "n_hit": int(m.group(6)), "n_unb": int(m.group(7))}
        elif m := RE_RB_ROAD.match(sign):
            road_costs[(int(m.group(1)), int(m.group(2)), int(m.group(3)))] = {
                "plan_ops": int(m.group(4)), "build_ops": int(m.group(5))}
    for item in road:
        item.update(road_costs.get((item["year"] % 100, item["line_index"], item["attempt"]), {}))
        item.update(road_site.get((item["year"] % 100, item["line_index"], item["attempt"]), {}))
    # road_costs sort aussi de la fonction : les tentatives REUSSIES sont reconstituees plus tard
    # depuis PM/RC (parse_lines), et doivent pouvoir retrouver leur cout en opcodes par (annee, id).
    return air, water, road, road_costs


def make_run_payload(rows, seed, years):
    """Assemble une campagne sans melanger les panneaux de graines differentes."""
    rows.sort(key=lambda row: row["date"])
    final = rows[-1]

    lines = parse_lines(final["signs"])
    attempts = parse_attempts(final["signs"])
    safety = parse_safety(final["signs"])
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
        if "n_stops_a" in line:
            item["n_stops_a"] = line["n_stops_a"]
            item["n_stops_b"] = line["n_stops_b"]
        if year_built is not None:
            item.update(road_ops.get((year_built % 100, line["line_index"], item["attempt"]), {}))
        road.append(item)
    cash_blocks, dead_lines, loan_repayments, loan_draws, road_refleets, loan_view_rows = parse_events(
        final["signs"])
    probe_attempts = parse_probes(final["signs"])
    speed_yield = parse_speed_yield(final["signs"])
    road_speed_yield = parse_road_speed_yield(final["signs"])
    rail_expansion = parse_rail_expansions(final["signs"])

    n_rail_ok = sum(1 for line in lines
                    if line["mode"] == "rail" and line["reason"] == "OK" and not line.get("probe"))
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
        "n_rail_attempts_sitea": sum(1 for attempt in attempts if attempt["reason"] == "SITEA"),
        "n_rail_attempts_siteb": sum(1 for attempt in attempts if attempt["reason"] == "SITEB"),
        "n_rail_attempts_siteab": sum(1 for attempt in attempts if attempt["reason"] == "SITEAB"),
        "n_rail_attempts_econ": sum(1 for attempt in attempts if attempt["reason"] == "ECON"),
        "n_rail_attempts_noplan": sum(1 for attempt in attempts if attempt["reason"] == "NOPLAN"),
        "n_lines_slope_relaxed": sum(
            1 for line in lines if line.get("predicted", {}).get("slopeRelaxed")),
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
        "n_join_refuse_multi": sum(row.get("join_refuse_multi", 0) for row in yearly.values()),
        "n_join_refuse_kind": sum(row.get("join_refuse_kind", 0) for row in yearly.values()),
        "n_join_refuse_role": sum(row.get("join_refuse_role", 0) for row in yearly.values()),
        "n_join_refuse_other": sum(row.get("join_refuse_other", 0) for row in yearly.values()),
        "n_join_refuse_dist": sum(row.get("join_refuse_dist", 0) for row in yearly.values()),
        "n_rail_attempts_joinpath": sum(1 for attempt in attempts if attempt["reason"] == "JOINPATH"),
        "n_place_join_generated": sum(row.get("place_join_generated", 0) for row in yearly.values()),
        "n_place_join_ranked": sum(row.get("place_join_ranked", 0) for row in yearly.values()),
        "n_place_join_built": sum(row.get("place_join_built", 0) for row in yearly.values()),
        "n_place_join_lines": sum(1 for line in lines if line.get("place_join")),
        "n_rail_attempts_sigfail": sum(1 for attempt in attempts if attempt["reason"] == "SIGFAIL"),
        "n_join_signals_ok": safety["n_join_signals_ok"],
        "n_join_signals_fail": safety["n_join_signals_fail"],
        "n_join_signal_junc": safety["n_join_signal_junc"],
        "n_join_signals_skip": safety["n_join_signals_skip"],
        "n_join_signal_failures": safety["n_join_signal_failures"],
        "n_capacity_signals_ok": safety["n_capacity_signals_ok"],
        "n_capacity_signals_fail": safety["n_capacity_signals_fail"],
        "n_capacity_signal_segments": safety["n_capacity_signal_segments"],
        "n_capacity_signal_failures": safety["n_capacity_signal_failures"],
        "n_rx_events": safety["n_rx_events"],
        "n_unexpected_trains_lost": safety["n_unexpected_trains_lost"],
        "n_train_crashes": safety["n_train_crashes"],
        "n_double_track_ok": safety["n_double_track_ok"],
        "n_double_track_tried": safety["n_double_track_tried"],
        "n_double_track_trains": safety["n_double_track_trains"],
        "double_tracks": safety["double_tracks"],
        "join_signal_failures": safety["join_signal_failures"],
        "capacity_signal_failures": safety["capacity_signal_failures"],
        "unexpected_train_losses": safety["unexpected_train_losses"],
        "train_crashes": safety["train_crashes"],
        "n_road_lines_ok": sum(1 for line in lines if line["mode"] == "road"),
        "n_road_freight_lines_ok": sum(
            1 for line in lines
            if line["mode"] == "road" and line["predicted"].get("kind") == "freight"),
        "n_road_multistop_a": sum(
            1 for line in lines if line["mode"] == "road" and (line.get("n_stops_a") or 1) > 1),
        "n_road_multistop_b": sum(
            1 for line in lines if line["mode"] == "road" and (line.get("n_stops_b") or 1) > 1),
        "n_road_multistop_both": sum(
            1 for line in lines if line["mode"] == "road"
            and (line.get("n_stops_a") or 1) > 1 and (line.get("n_stops_b") or 1) > 1),
        "n_road_vehicles_gt2": sum(
            1 for line in lines if line["mode"] == "road" and (line.get("vehicles_built") or 0) > 2),
        "n_road_attempts": sum(row.get("road_attempts", 0) for row in yearly.values()),
        "n_road_attempts_failed": sum(1 for item in road if not item["ok"]),
        "road_plan_opcodes": sum(item.get("plan_ops", 0) for item in road),
        "road_build_opcodes": sum(item.get("build_ops", 0) for item in road),
        "attempt_distance": summarise_attempt_distance(attempts),
        "rail_attempts": attempts, "air_attempts": air, "water_attempts": water,
        "road_attempts": road, "cash_blocks": cash_blocks, "dead_line_events": dead_lines,
        "loan_repayments": loan_repayments, "loan_draws": loan_draws,
        "n_loan_draws": len(loan_draws),
        "n_loan_draws_covered": sum(1 for draw in loan_draws if draw["covered"]),
        "road_refleets": road_refleets,
        "n_road_refleets": sum(1 for event in road_refleets if event["added"] > 0),
        "n_road_refleet_vehicles": sum(event["added"] for event in road_refleets),
        "rail_expansion": rail_expansion,
        "probe_attempts": probe_attempts,
        "n_probe_attempts": len(probe_attempts),
        "n_probe_ok": sum(1 for item in probe_attempts if item["reason"] == "OK"),
        "n_probe_lines": sum(1 for line in lines if line.get("probe")),
        "n_pax_near_admitted": sum(row.get("pax_near_admitted") or 0 for row in yearly.values()),
        "n_pax_near_tried": sum(row.get("pax_near_tried") or 0 for row in yearly.values()),
        "n_pax_near_ok": sum(1 for line in lines if line.get("pax_near")),
        "loan_view": loan_view_rows,
        "speed_yield": {k: v for k, v in speed_yield.items() if k != "samples"},
        "speed_samples": speed_yield["samples"],
        "road_speed_yield": {k: v for k, v in road_speed_yield.items() if k != "samples"},
        "road_speed_samples": road_speed_yield["samples"],
        "town_growth": summarise_town_growth(yearly),
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
    parser.add_argument("--workers", type=int, default=3)
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
    all_attempts = [item for run in runs for item in run.get("rail_attempts") or []]
    payload = {
        "openttd_version": OPENTTD_VERSION, "opengfx_version": OPENGFX_VERSION,
        "years": args.years, "seeds": args.seeds, "openttd_config": CFG,
        "ai_settings": {key: value for key, value in args.ai_settings},
        "attempt_distance": summarise_attempt_distance(all_attempts),
        "probe_negative": summarise_probe_negative(runs),
        "instrumentation_added": ["CG", "CR", "CD", "CE", "CK", "PC", "PM", "OB|A", "GM", "OB|J",
                                  "CJ", "OB|S", "PJ", "OL traction", "PL longueur rame", "PT arbitrage",
                                  "PD quai voulu-vs-bati", "PD repli pente",
                                  "OR SITEA/SITEB/SITEAB/ECON", "PS site clear/cargo/cmd",
                                  "GL reemprunt", "RF reconstitution flotte route",
                                  "OB|A distance",
                                  "PN/PX/PQ/NH/NM sondage profit<=0",
                                  "PE/PY pax_near", "EU/EG/ES/EX expansion rail",
                                  "OB|R refus de jointure",
                                  "OB|R D join_max_distance",
                                  "PH join_place H2",
                                  "SG signaux PBS jointure",
                                  "PJ|P place-first",
                                  "PS join_end A/B/N",
                                  "RI SITE route cargo/buildable/cmd",
                                  "RT TRACEX trials/long/hit/unb",
                                  "RM multistop nStopsA/nStopsB/veh",
                                  "RV vitesse mediane trains en marche",
                                  "RY vitesse mediane bus/camions en marche",
                                  "TV pop mediane villes desservies/libres",
                                  "SC/SF blocs de capacite et echecs exacts",
                                  "SJ/JF approches de jointure et echecs exacts",
                                  "RX pertes inattendues de trains",
                                  "XC collisions CRASH_TRAIN",
                                  "DT double voie posee/trains/skip"],
        "runs": runs,
    }
    result_path.write_text(json.dumps(payload, indent=2))
    for run in runs:
        print(f"=== {args.years} ans, graine {run['seed']} ===")
        print(f"lignes rail OK: {run['n_rail_lines_ok']}  (tentatives totales: "
              f"{run['n_rail_attempts_total']}, echouees: {run['n_rail_attempts_failed']})")
        print(f"sites: SITEA={run['n_rail_attempts_sitea']} SITEB={run['n_rail_attempts_siteb']} "
              f"SITEAB={run['n_rail_attempts_siteab']} ECON={run['n_rail_attempts_econ']} "
              f"NOPLAN={run['n_rail_attempts_noplan']}  pente={run['n_lines_slope_relaxed']}")
        site = [a for a in run["rail_attempts"]
                if a["reason"] in ("SITEA", "SITEB", "SITEAB")]
        join_end = sum(1 for a in site
                       if a.get("join_end") in ("A", "B")
                       and ((a["reason"] == "SITEA" and a.get("join_end") == "A")
                            or (a["reason"] == "SITEB" and a.get("join_end") == "B")
                            or a["reason"] == "SITEAB"))
        clear0 = sum(1 for a in site if (a.get("n_clear") or 0) == 0)
        cmd = sum(1 for a in site if (a.get("n_cmd") or 0) > 0)
        print(f"  SITE n={len(site)} join_end_fail={join_end} clear0={clear0} "
              f"cmd>0={cmd} JOINPATH={run.get('n_rail_attempts_joinpath', 0)}")
        sy = run.get("speed_yield") or {}
        print(f"  vitesse n={sy.get('n_moving')}/{sy.get('n_samples')} "
              f"med={sy.get('median_speed')} pred={sy.get('median_pred')} "
              f"cat={sy.get('median_catalog')} "
              f"med/cat={sy.get('median_vs_catalog')} med/pred={sy.get('median_vs_pred')}")
        ry = run.get("road_speed_yield") or {}
        print(f"  route n={ry.get('n_moving')}/{ry.get('n_samples')} "
              f"med={ry.get('median_speed')} pred={ry.get('median_pred')} "
              f"cat={ry.get('median_catalog')} "
              f"med/cat={ry.get('median_vs_catalog')} med/pred={ry.get('median_vs_pred')}")
        for kind in ("pax", "freight"):
            sub = ry.get(kind) or {}
            if sub.get("n_moving"):
                print(f"    {kind} n={sub.get('n_moving')} "
                      f"med={sub.get('median_speed')} "
                      f"med/cat={sub.get('median_vs_catalog')} "
                      f"med/pred={sub.get('median_vs_pred')}")
        tg = run.get("town_growth") or {}
        if tg:
            print(f"  villes served {tg.get('n_served_first')}->{tg.get('n_served_last')} "
                  f"pop {tg.get('pop_served_first')}->{tg.get('pop_served_last')} "
                  f"x{tg.get('served_ratio')}  "
                  f"free {tg.get('n_free_first')}->{tg.get('n_free_last')} "
                  f"pop {tg.get('pop_free_first')}->{tg.get('pop_free_last')} "
                  f"x{tg.get('free_ratio')}")
        print(f"company_value final: {run['final_company_value']}  "
              f"performance_history: {run['final_performance_history']}")
        print(f"money: {run['final_money']}  current_loan: {run['final_current_loan']}")
        print(f"n_vehicles: {run['final_n_vehicles']}  n_stations: {run['final_n_stations']}")
        print(f"road_ok: {run['n_road_lines_ok']}  refleets: {run.get('n_road_refleets', 0)}"
              f" veh+={run.get('n_road_refleet_vehicles', 0)}")
        expansion = run.get("rail_expansion") or {}
        print(f"rail_expand: ok={expansion.get('n_success', 0)} "
              f"fail={expansion.get('n_fail', 0)} "
              f"gain_attendu={expansion.get('expected_profit_annual', 0)} "
              f"ops={expansion.get('opcodes', 0)} "
              f"profit/Mop={expansion.get('expected_profit_per_mopcode')}")
        road_ok = [a for a in (run.get("road_attempts") or []) if a.get("ok")]
        extra_a = sum(1 for a in road_ok if (a.get("n_stops_a") or 1) > 1)
        extra_b = sum(1 for a in road_ok if (a.get("n_stops_b") or 1) > 1)
        extra_both = sum(1 for a in road_ok
                         if (a.get("n_stops_a") or 1) > 1 and (a.get("n_stops_b") or 1) > 1)
        veh_gt2 = sum(1 for a in road_ok if (a.get("vehicles") or 0) > 2)
        print(f"  multistop extraA={extra_a} extraB={extra_b} both={extra_both} veh>2={veh_gt2}")
        road_fail = [a for a in (run.get("road_attempts") or []) if not a.get("ok")]
        site = [a for a in road_fail if a.get("reason") in ("SITEA", "SITEB")]
        print(f"  road SITE={len(site)}/{len(road_fail)} "
              f"SITEA={sum(1 for a in road_fail if a.get('reason')=='SITEA')} "
              f"SITEB={sum(1 for a in road_fail if a.get('reason')=='SITEB')} "
              f"TRACEX={sum(1 for a in road_fail if a.get('reason')=='TRACEX')} "
              f"DEPOTX={sum(1 for a in road_fail if a.get('reason')=='DEPOTX')}")
        tracex = [a for a in road_fail if a.get("reason") in ("TRACEX", "DEPOTX")]
        if tracex:
            print(f"  TRACEX trials={sum(a.get('n_trials') or 0 for a in tracex)} "
                  f"long={sum(a.get('n_long') or 0 for a in tracex)} "
                  f"hit={sum(a.get('n_hit') or 0 for a in tracex)} "
                  f"unb={sum(a.get('n_unb') or 0 for a in tracex)}")
        dist = run.get("attempt_distance") or {}
        print(f"sondages profit<=0: {run.get('n_probe_attempts', 0)}  "
              f"OK={run.get('n_probe_ok', 0)}  lignes={run.get('n_probe_lines', 0)}")
        print(f"pax_near: admis={run.get('n_pax_near_admitted', 0)}  "
              f"tries={run.get('n_pax_near_tried', 0)}  OK={run.get('n_pax_near_ok', 0)}")
        print(f"join: att={run.get('n_station_join_attempts', 0)}  "
              f"ok={run.get('n_station_join_built', 0)}  "
              f"fail={run.get('n_station_join_failed', 0)}  "
              f"JOINPATH={run.get('n_rail_attempts_joinpath', 0)}")
        print(f"join_place: gen={run.get('n_place_join_generated', 0)}  "
              f"rank={run.get('n_place_join_ranked', 0)}  "
              f"ok={run.get('n_place_join_built', 0)}  "
              f"lines={run.get('n_place_join_lines', 0)}")
        print(f"signaux: ok={run.get('n_join_signals_ok', 0)}  "
              f"fail={run.get('n_join_signals_fail', 0)}  "
              f"skip={run.get('n_join_signals_skip', 0)}  "
              f"junc={run.get('n_join_signal_junc', 0)}  "
              f"JF={run.get('n_join_signal_failures', 0)}")
        print(f"capacite: ok={run.get('n_capacity_signals_ok', 0)}  "
              f"fail={run.get('n_capacity_signals_fail', 0)}  "
              f"segments={run.get('n_capacity_signal_segments', 0)}  "
              f"SF={run.get('n_capacity_signal_failures', 0)}")
        print(f"crash: RX={run.get('n_rx_events', 0)}  "
              f"lost={run.get('n_unexpected_trains_lost', 0)}  "
              f"XC={run.get('n_train_crashes', 0)}  "
              f"SIGFAIL={run.get('n_rail_attempts_sigfail', 0)}")
        print(f"double voie: ok={run.get('n_double_track_ok', 0)}/"
              f"{run.get('n_double_track_tried', 0)}  "
              f"trains={run.get('n_double_track_trains', 0)}")
        print(f"join refuse: multi={run.get('n_join_refuse_multi', 0)}  "
              f"kind={run.get('n_join_refuse_kind', 0)}  "
              f"role={run.get('n_join_refuse_role', 0)}  "
              f"other={run.get('n_join_refuse_other', 0)}  "
              f"dist={run.get('n_join_refuse_dist', 0)}")
        print(f"tentatives avec distance: {dist.get('n_with_distance')}/"
              f"{dist.get('n_attempts')}  OK={dist.get('n_ok')} ABND={dist.get('n_abnd')}")
        for band in dist.get("bands") or []:
            print(f"  {band['lo']:3}-{band['hi']:<3} n={band['n']:3} p_ok={band['p_ok']} "
                  f"ABND={band['n_abnd']} ratio_ok={band['median_ratio_ok']}")
        print(f"annees franchies: {run['calendar_years_crossed']}  "
              f"non rattrapees: {run['skipped_years']}")
    dist = payload.get("attempt_distance") or {}
    print(f"=== join refuse toutes graines: "
          f"multi={sum(r.get('n_join_refuse_multi', 0) for r in runs)} "
          f"kind={sum(r.get('n_join_refuse_kind', 0) for r in runs)} "
          f"role={sum(r.get('n_join_refuse_role', 0) for r in runs)} "
          f"other={sum(r.get('n_join_refuse_other', 0) for r in runs)} "
          f"dist={sum(r.get('n_join_refuse_dist', 0) for r in runs)} "
          f"att={sum(r.get('n_station_join_attempts', 0) for r in runs)} "
          f"ok={sum(r.get('n_station_join_built', 0) for r in runs)} "
          f"JOINPATH={sum(r.get('n_rail_attempts_joinpath', 0) for r in runs)} "
          f"place_ok={sum(r.get('n_place_join_built', 0) for r in runs)} "
          f"sig_ok={sum(r.get('n_join_signals_ok', 0) for r in runs)} "
          f"sig_fail={sum(r.get('n_join_signals_fail', 0) for r in runs)} "
          f"sig_junc={sum(r.get('n_join_signal_junc', 0) for r in runs)} ===")
    print(f"=== securite toutes graines: "
          f"cap_ok={sum(r.get('n_capacity_signals_ok', 0) for r in runs)} "
          f"cap_fail={sum(r.get('n_capacity_signals_fail', 0) for r in runs)} "
          f"SF={sum(r.get('n_capacity_signal_failures', 0) for r in runs)} "
          f"join_ok={sum(r.get('n_join_signals_ok', 0) for r in runs)} "
          f"join_fail={sum(r.get('n_join_signals_fail', 0) for r in runs)} "
          f"skip={sum(r.get('n_join_signals_skip', 0) for r in runs)} "
          f"JF={sum(r.get('n_join_signal_failures', 0) for r in runs)} "
          f"RX={sum(r.get('n_rx_events', 0) for r in runs)} "
          f"XC={sum(r.get('n_train_crashes', 0) for r in runs)} "
          f"SIGFAIL={sum(r.get('n_rail_attempts_sigfail', 0) for r in runs)} "
          f"DT={sum(r.get('n_double_track_ok', 0) for r in runs)}/"
          f"{sum(r.get('n_double_track_tried', 0) for r in runs)} ===")
    print(f"=== distance toutes graines: {dist.get('n_with_distance')}/"
          f"{dist.get('n_attempts')}  OK={dist.get('n_ok')} ABND={dist.get('n_abnd')} ===")
    for band in dist.get("bands") or []:
        print(f"  {band['lo']:3}-{band['hi']:<3} n={band['n']:3} p_ok={band['p_ok']} "
              f"ABND={band['n_abnd']} ratio_ok={band['median_ratio_ok']}")
    probe = payload.get("probe_negative") or {}
    pop = probe.get("population") or {}
    print(f"=== sondage profit<=0 toutes graines: tries={probe.get('n_tried')} "
          f"OK={probe.get('n_ok')} ABND={probe.get('n_abnd')} "
          f"actuals={probe.get('n_lines_with_actual')} "
          f"profit>0 1re={probe.get('n_actual_profit_positive')} "
          f"2e={probe.get('n_actual_profit_positive_second')} "
          f"last={probe.get('n_actual_profit_positive_last')} ===")
    print(f"  population CE profit<=0: {pop.get('n_profit_non_positive')}  "
          f"pax={pop.get('n_pax')} frt={pop.get('n_freight')} near={pop.get('n_near')}")
    print(f"  bandes: {pop.get('bands')}  raisons: {probe.get('reasons')}")
    print(f"  median predit (tries): {probe.get('median_ranking_profit_tried')}  "
          f"median reel 2e: {probe.get('median_actual_profit_second')}  "
          f"median dist tries/ok/abnd: {probe.get('median_distance_tried')}/"
          f"{probe.get('median_distance_ok')}/{probe.get('median_distance_abnd')}")
    for band in probe.get("attempt_bands") or []:
        print(f"  {band['lo']:3}-{band['hi']:<3} n={band['n']:3} OK={band['n_ok']} "
              f"ABND={band['n_abnd']} actuals={band['n_with_actual']} "
              f">0 2e={band['n_positive_second']} last={band['n_positive_last']} "
              f"med_pred={band['median_predicted']} med_last={band['median_actual_last']}")
    print("ecrit", result_path)


if __name__ == "__main__":
    main()
