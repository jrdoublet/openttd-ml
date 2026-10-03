"""Table de moteurs C121, mesuree hors ligne.

La sonde ``probe_c121_engine_table`` (defaut 0) journalise des choix deja
calcules. Ce module ne relance aucune partie. Il apprend des cellules
distance x demande x contexte sur toutes les graines sauf une, puis compare
la table aux decisions exactes de la graine tenue a l'ecart.

Quantite du portefeuille
------------------------
Le portefeuille classe un projet aerien C121 par ``fundScore``
(``projects_selection.nut`` : ``project.fundScore <- OpexProjectScore(...)``).

``OpexProjectScore(value, cost)`` vaut ``1000 * value / cost`` quand les deux
sont strictement positifs, sinon 0.

``value`` est ``OpexProjectFundProfit(project)`` :

* ``calibrated`` = profit C70/C82 si ``C70_PROFIT_CALIBRATED``, sinon
  ``profitAnnual``. ``OpexCalibratedProfit`` pointe vers ``OpexC70Profit``
  tant que ``c82_engine_calibration`` reste a 0. ``OpexC70Factor`` est un
  facteur de mode (la flotte est ramenee a l'air). Le meme facteur multiplie
  chaque nouveau projet AIR d'une passe : il ne change pas l'ordre entre ces
  projets et il est omis ici.
* si ``split`` et ``portfolioProfitAnnual`` existe, le profit de classement
  est le profit portfolio, multiplie par ``calibrated / profitAnnual`` quand
  C70 est actif et que le profit d'ouverture est positif ;
* sinon le profit de classement est ``calibrated``.

Sous les defauts courants (``c121_air_portfolio_split_economics=0``,
``c121_air_initial_project_economics=0``, ``c82_engine_calibration=0``,
``c121_air_decision_depth_economics=0``, ``c121_air_one_or_two_planes=1``),
``OpexProjectFromAir`` pose ``profitAnnual`` et le capital de decision sur
``decisionEconomics``. La marge de caisse depend du bras :
newpair 30000, hubsite 12000, hubhub 2000. ``immobilise`` s'ajoute s'il est
positif. Le denominateur est ``decisionFinanceCapital``, ou le ``K_dec`` de
la selection s'il est plus grand (``C69_DECISION_BOTTLENECK``, projet non
exempt). La selection recalcule ce ``K_dec`` une fois par
``OpexC69ComputeKDec()``. Le champ ``kdec`` de PLAN est le
``decisionKDec`` deja tamponne sur l'objet economique au moment de
l'evaluation : c'est la seule valeur disponible sans appel supplementaire.
Il peut differer du ``K_dec`` ulterieur de la selection. S'il vaut -1, le
proxy classe sur le seul capital de financement.

Reconstruction depuis les champs PLAN (facteur C70 omis) :

* ``init=1`` : profit, capital = ``P``, ``C`` (economie d'ouverture) ;
* sinon ``split=1`` et ``pfP`` connu : profit, capital = ``pfP``, ``pfC`` ;
* sinon profit, capital = ``dP``, ``dC``, avec repli sur ``P``, ``C`` si le
  champ de decision vaut -1.
* ``finance = capital + (imm si imm >= 0 sinon 0) + marge(bras)``
* ``denom = kdec`` si ``kdec > finance``, sinon ``finance`` (et ``finance``
  seule si ``kdec`` vaut -1)
* ``rankScore = 1000 * profit / denom`` si profit > 0 et denom > 0, sinon le
  plan est exclu du classement.

Le score de cellule qui pre-classe les plans est la mediane du score de
decision du vainqueur (``dScore``, repli ``score``), pas ``fundScore``.
Le rapport ``P_cellule / C_cellule`` est un second classement. La cible de
comparaison reste le proxy ``fundScore``.

Les lignes PLAN calculent l'apprentissage. Un HIT repete la derniere
observation exacte de la meme cle dans la partie : il entre dans le
classement, pas dans l'apprentissage (sinon les routes chaudes du cache
pesent plusieurs fois).

Jetons optionnels ``ge`` / ``ge_est`` (absents = 0 / -1) :

* ``ge=0`` scan normal, ``1`` raccourci (aucune ligne ENG : seul le
  vainqueur etabli est retenu, sans ``decisionOnly``), ``2`` controle,
  ``3`` repli.
* ``ge_est`` est le moteur etabli pour le type d'aeroport, ou ``-1``.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import random
import re
import statistics
import sys


ROOT = Path(__file__).resolve().parents[1]
NEEDLE = "probe_c121_engine_table=1"
STRING_FIELDS = {"date", "engines", "key", "arm"}
EVENT_RE = re.compile(
    r"(?:\[I\]\s+)?(C121_ENGTAB_(PASS|ENG|PLAN|HIT))\s+(\S.*?)\s*$"
)
MARGINS = {"newpair": 30000, "hubsite": 12000, "hubhub": 2000}
COARSE_BINS = {12: (8, 6, 4), 8: (6, 4), 6: (4,), 4: ()}
RANDOM_SEED_BASE = 20261002

PORTFOLIO_QUANTITY = (
    "fundScore = OpexProjectScore(OpexProjectFundProfit(project), denom). "
    "Proxy AIR : 1000 * profit / denom, facteur C70 omis car commun aux "
    "projets AIR d'une passe. profit/capital = P/C si init=1, pfP/pfC si "
    "split=1, sinon dP/dC (repli P/C). finance = capital + immobilise "
    "(si >= 0) + marge(newpair 30000, hubsite 12000, hubhub 2000). "
    "denom = kdec s'il depasse finance, sinon finance. kdec est le "
    "decisionKDec d'evaluation, pas le K_dec recalcule a la selection."
)


def parse_number(value):
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    try:
        return float(value)
    except ValueError:
        return value


def parse_line(raw):
    match = EVENT_RE.search(raw)
    if match is None:
        return None
    fields = {"kind": match.group(2)}
    for token in match.group(3).split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        fields[key] = value if key in STRING_FIELDS else parse_number(value)
    return fields


def parse_log_text(text):
    events = []
    for raw in text.splitlines():
        event = parse_line(raw)
        if event is not None:
            events.append(event)
    return events


def year_of(date_text):
    if not isinstance(date_text, str) or len(date_text) < 4:
        return None
    head = date_text[:4]
    return int(head) if head.isdigit() else None


def reconstruct(events, seed, game):
    """Attache ENG au PLAN suivant de meme cle et passe, et HIT a la derniere PLAN."""
    signatures = {}
    pass_dates = {}
    pending = defaultdict(list)
    last_plan = {}
    rows = []
    unresolved = 0
    seq = 0
    for event in events:
        kind = event["kind"]
        pid = event.get("pass")
        if kind == "PASS":
            signatures[pid] = event.get("engines", "none")
            if event.get("date"):
                pass_dates[pid] = event["date"]
            continue
        if kind == "ENG":
            pending[(pid, event.get("key"))].append(dict(event))
            continue
        if kind == "PLAN":
            row = dict(event)
            row["engines_rows"] = pending.pop((pid, event.get("key")), [])
            row["engine_set"] = signatures.get(pid, "unknown")
            row["hit"] = False
            row["row_id"] = seq
            row["seed"] = seed
            row["game"] = game
            row["year"] = year_of(row.get("date"))
            if "ge" not in row:
                row["ge"] = 0
            if "ge_est" not in row:
                row["ge_est"] = -1
            seq += 1
            rows.append(row)
            last_plan[event.get("key")] = row
            continue
        if kind == "HIT":
            source = last_plan.get(event.get("key"))
            if source is None:
                unresolved += 1
                continue
            row = dict(source)
            row["engines_rows"] = list(source.get("engines_rows") or [])
            row["hit"] = True
            row["pass"] = pid
            row["row_id"] = seq
            row["seed"] = seed
            row["game"] = game
            row["engine_set"] = signatures.get(pid, source.get("engine_set", "unknown"))
            if pid in pass_dates:
                row["date"] = pass_dates[pid]
                row["year"] = year_of(pass_dates[pid])
            seq += 1
            rows.append(row)
    return rows, unresolved


def known_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value != value or value == -1:
        return None
    return float(value)


def pax_sum(plan):
    left = known_number(plan.get("paxRawA"))
    right = known_number(plan.get("paxRawB"))
    if left is None or right is None or left < 0 or right < 0:
        return None
    return left + right


def asymmetry_class(pax_a, pax_b, high=0.75, low=0.4):
    """min/max : 0 si le ratio >= high ou si la demande manque, 1 si >= low, sinon 2."""
    left = known_number(pax_a)
    right = known_number(pax_b)
    if left is None or right is None or left < 0 or right < 0:
        return 0
    hi = max(left, right)
    if hi == 0:
        return 0
    ratio = min(left, right) / hi
    if ratio >= high:
        return 0
    if ratio >= low:
        return 1
    return 2


def quantile_edges(values, bins):
    vals = sorted(float(value) for value in values if known_number(value) is not None)
    if not vals:
        return [0.0, 1.0]
    if len(set(vals)) == 1:
        return [vals[0], vals[0]]
    count = len(vals)
    raw = []
    for index in range(bins + 1):
        pos = index * (count - 1) / bins
        lo = int(pos)
        hi = min(lo + 1, count - 1)
        frac = pos - lo
        raw.append(vals[lo] * (1.0 - frac) + vals[hi] * frac)
    edges = [raw[0]]
    for edge in raw[1:]:
        if edge > edges[-1]:
            edges.append(edge)
    if len(edges) == 1:
        edges.append(edges[0])
    return edges


def log_edges(values, bins):
    vals = sorted(float(value) for value in values if known_number(value) is not None and value > 0)
    if not vals:
        return [0.0, 1.0]
    lo = vals[0]
    hi = vals[-1]
    if hi <= lo:
        return [lo, lo]
    log_lo = math.log(lo)
    log_hi = math.log(hi)
    return [math.exp(log_lo + (log_hi - log_lo) * index / bins) for index in range(bins + 1)]


def bin_index(value, edges, nonpositive_bin0=False):
    if not edges or len(edges) < 2:
        return 0
    number = known_number(value)
    if number is None:
        return 0
    if nonpositive_bin0 and number <= 0:
        return 0
    if number <= edges[0]:
        return 0
    last = len(edges) - 2
    if number >= edges[-1]:
        return last
    for index in range(last + 1):
        if number < edges[index + 1]:
            return index
    return last


def decision_score(plan):
    scored = known_number(plan.get("dScore"))
    if scored is not None:
        return scored
    return known_number(plan.get("score"))


def winner_profit(plan):
    profit = known_number(plan.get("dP"))
    if profit is not None:
        return profit
    return known_number(plan.get("P"))


def winner_capital(plan):
    capital = known_number(plan.get("dC"))
    if capital is not None:
        return capital
    return known_number(plan.get("C"))


def portfolio_parts(plan):
    """profit, capital et proxy fundScore. None si le plan n'est pas classable."""
    init = plan.get("init", 0) == 1
    split = plan.get("split", 0) == 1
    if init:
        profit, capital = known_number(plan.get("P")), known_number(plan.get("C"))
    elif split and known_number(plan.get("pfP")) is not None:
        profit, capital = known_number(plan.get("pfP")), known_number(plan.get("pfC"))
    else:
        profit = known_number(plan.get("dP"))
        capital = known_number(plan.get("dC"))
        if profit is None:
            profit = known_number(plan.get("P"))
        if capital is None:
            capital = known_number(plan.get("C"))
    if profit is None or capital is None or profit <= 0:
        return None, None, None
    imm = known_number(plan.get("imm"))
    finance = capital + (imm if imm is not None and imm >= 0 else 0.0) + MARGINS.get(plan.get("arm"), 0)
    kdec = known_number(plan.get("kdec"))
    denom = kdec if kdec is not None and kdec > finance else finance
    if denom <= 0:
        return None, None, None
    return profit, capital, 1000.0 * profit / denom


def median(values):
    vals = [float(value) for value in values if value is not None]
    if not vals:
        return None
    return float(statistics.median(vals))


def argmax_engine(scores, profits, winners):
    best_key = None
    best_engine = None
    for engine, engine_scores in scores.items():
        if not engine_scores:
            continue
        med_p = statistics.median(profits[engine]) if profits.get(engine) else float("-inf")
        key = (statistics.median(engine_scores), med_p, -int(engine))
        if best_key is None or key > best_key:
            best_key = key
            best_engine = engine
    if best_engine is not None:
        return best_engine
    if not winners:
        return None
    counts = Counter(winners)
    top = max(counts.values())
    return min(engine for engine, count in counts.items() if count == top)


def build_cell(group):
    scores = defaultdict(list)
    profits = defaultdict(list)
    winners = []
    d_scores, d_profits, d_capitals = [], [], []
    n1_p, n1_c, n2_p, n2_c = [], [], [], []
    marginal_p, marginal_c = [], []
    for plan in group:
        for row in plan.get("engines_rows") or []:
            if row.get("eval") != 1:
                continue
            score = known_number(row.get("score"))
            if score is None:
                continue
            engine = row.get("eng")
            scores[engine].append(score)
            profit = known_number(row.get("P"))
            if profit is not None:
                profits[engine].append(profit)
        if plan.get("eng", -1) == -1:
            continue
        winners.append(plan["eng"])
        score = decision_score(plan)
        if score is not None:
            d_scores.append(score)
        profit = winner_profit(plan)
        capital = winner_capital(plan)
        if profit is not None:
            d_profits.append(profit)
        if capital is not None:
            d_capitals.append(capital)
        p1, c1 = known_number(plan.get("P_n1")), known_number(plan.get("C_n1"))
        p2, c2 = known_number(plan.get("P_n2")), known_number(plan.get("C_n2"))
        if p1 is not None:
            n1_p.append(p1)
        if c1 is not None:
            n1_c.append(c1)
        if p2 is not None:
            n2_p.append(p2)
        if c2 is not None:
            n2_c.append(c2)
        if p1 is not None and p2 is not None:
            marginal_p.append(p2 - p1)
        if c1 is not None and c2 is not None:
            marginal_c.append(c2 - c1)
    engine = argmax_engine(scores, profits, winners)
    score = median(d_scores)
    if engine is None or score is None:
        return None
    return {
        "engine": engine,
        "score": score,
        "p": median(d_profits),
        "c": median(d_capitals),
        "p_n1": median(n1_p),
        "c_n1": median(n1_c),
        "p_n2": median(n2_p),
        "c_n2": median(n2_c),
        "marginal_p": median(marginal_p),
        "marginal_c": median(marginal_c),
        "n": len(group),
    }


def spec_name(bins, asym, context, demand):
    if not demand:
        return "dist-%d" % bins
    name = "dxd-%d" % bins
    if asym:
        name += "-asym"
    if not context:
        name += "-nocontext"
    return name


def iter_specs(include_context):
    specs = []
    contexts = (True, False) if include_context else (False,)
    for bins in (4, 6, 8, 12):
        for asym in (False, True):
            for context in contexts:
                specs.append({
                    "bins": bins, "asym": asym, "context": context, "demand": True,
                    "name": spec_name(bins, asym, context, True),
                })
    for bins in (4, 6, 8, 12):
        specs.append({
            "bins": bins, "asym": False, "context": False, "demand": False,
            "name": spec_name(bins, False, False, False),
        })
    return specs


def coarser_names(spec):
    names = [
        spec_name(bins, spec["asym"], spec["context"], spec["demand"])
        for bins in COARSE_BINS[spec["bins"]]
    ]
    if spec["demand"]:
        names.append("dist-4")
    return names


def fit_edges(train, bins, demand, binning):
    distances = [plan.get("dist") for plan in train if known_number(plan.get("dist")) is not None]
    demands = [pax_sum(plan) for plan in train if pax_sum(plan) is not None]
    if binning == "log":
        return log_edges(distances, bins), log_edges(demands, bins) if demand else None
    return quantile_edges(distances, bins), quantile_edges(demands, bins) if demand else None


def locate(plan, table):
    log_mode = table["binning"] == "log"
    dist_bin = bin_index(plan.get("dist"), table["edges_dist"], log_mode)
    if table["spec"]["demand"]:
        demand_bin = bin_index(pax_sum(plan), table["edges_demand"], log_mode)
    else:
        demand_bin = 0
    if table["spec"]["asym"]:
        asym = asymmetry_class(
            plan.get("paxRawA"), plan.get("paxRawB"), table["asym_high"], table["asym_low"])
    else:
        asym = -1
    if table["spec"]["context"]:
        arm = plan.get("arm") or ""
        airport = plan.get("ap", -1)
    else:
        arm, airport = "", -1
    return (dist_bin, demand_bin, asym, arm, airport)


def fit_table(train, spec, binning, asym_high, asym_low):
    edges_dist, edges_demand = fit_edges(train, spec["bins"], spec["demand"], binning)
    table = {
        "spec": spec,
        "binning": binning,
        "asym_high": asym_high,
        "asym_low": asym_low,
        "edges_dist": edges_dist,
        "edges_demand": edges_demand,
        "cells": {},
        "global": build_cell(train),
    }
    groups = defaultdict(list)
    for plan in train:
        groups[locate(plan, table)].append(plan)
    for key, group in groups.items():
        cell = build_cell(group)
        if cell is not None:
            table["cells"][key] = cell
    return table


def nearest_cell(table, key, same_context):
    dist_bin, demand_bin, asym, arm, airport = key
    best = None
    found = None
    for cell_key, cell in table["cells"].items():
        other_dist, other_demand, other_asym, other_arm, other_airport = cell_key
        if other_asym != asym:
            continue
        if same_context and (other_arm != arm or other_airport != airport):
            continue
        distance = abs(other_dist - dist_bin)
        if table["spec"]["demand"]:
            distance += abs(other_demand - demand_bin)
        rank = (
            distance, abs(other_dist - dist_bin), abs(other_demand - demand_bin),
            other_dist, other_demand, str(other_arm), other_airport,
        )
        if best is None or rank < best:
            best = rank
            found = cell
    return found


def resolve_cell(plan, table, tables):
    key = locate(plan, table)
    if key in table["cells"]:
        return table["cells"][key], False
    found = nearest_cell(table, key, True)
    if found is not None:
        return found, True
    for name in coarser_names(table["spec"]):
        other = tables[name]
        other_key = locate(plan, other)
        if other_key in other["cells"]:
            return other["cells"][other_key], True
        found = nearest_cell(other, other_key, True)
        if found is not None:
            return found, True
    found = nearest_cell(table, key, False)
    if found is not None:
        return found, True
    if table["global"] is not None:
        return table["global"], True
    return None, True


def cell_ratio(cell):
    if cell is None or cell.get("p") is None or cell.get("c") in (None, 0):
        return None
    return cell["p"] / cell["c"]


def predict_table(test, table, tables):
    predictions = []
    for plan in test:
        cell, fallback = resolve_cell(plan, table, tables)
        pred = dict(plan)
        pred["table_engine"] = None if cell is None else cell["engine"]
        pred["cell_score"] = None if cell is None else cell["score"]
        pred["cell_p"] = None if cell is None else cell["p"]
        pred["cell_c"] = None if cell is None else cell["c"]
        pred["cell_ratio"] = cell_ratio(cell)
        pred["fallback"] = fallback
        predictions.append(pred)
    return predictions


def predict_random(train, test, seed):
    winners = sorted({plan["eng"] for plan in train if plan.get("eng", -1) != -1})
    drawn = random.Random(RANDOM_SEED_BASE + int(seed))
    engine = winners[drawn.randrange(len(winners))] if winners else None
    grouped = defaultdict(list)
    for plan in test:
        grouped[(plan["game"], plan["pass"])].append(plan)
    predictions = []
    for (game, pid), rows in grouped.items():
        shuffler = random.Random(RANDOM_SEED_BASE + int(seed) + int(pid) + int(game) * 100003)
        order = list(rows)
        shuffler.shuffle(order)
        scores = {row["row_id"]: float(len(order) - index) for index, row in enumerate(order)}
        for row in rows:
            pred = dict(row)
            pred["table_engine"] = engine
            pred["cell_score"] = scores[row["row_id"]]
            pred["cell_p"] = scores[row["row_id"]]
            pred["cell_c"] = 1.0
            pred["cell_ratio"] = scores[row["row_id"]]
            pred["fallback"] = False
            predictions.append(pred)
    return predictions


def engine_observed_score(plan, engine):
    for row in plan.get("engines_rows") or []:
        if row.get("eng") == engine and row.get("eval") == 1:
            return known_number(row.get("score"))
    return None


def relative_regret(plan):
    winner = plan.get("eng", -1)
    table_engine = plan.get("table_engine")
    if winner == -1 or table_engine is None:
        return None
    if table_engine == winner:
        return 0.0
    score = decision_score(plan)
    if score is None or score == 0:
        return None
    observed = engine_observed_score(plan, table_engine)
    if observed is None:
        return None
    return (score - observed) / abs(score)


def average_ranks(values):
    order = sorted(range(len(values)), key=lambda index: (values[index], index))
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(order):
        end = cursor
        while end + 1 < len(order) and values[order[end + 1]] == values[order[cursor]]:
            end += 1
        average = (cursor + end) / 2.0 + 1.0
        for index in range(cursor, end + 1):
            ranks[order[index]] = average
        cursor = end + 1
    return ranks


def pearson(xs, ys):
    count = len(xs)
    if count < 2:
        return None
    mean_x = sum(xs) / count
    mean_y = sum(ys) / count
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    dy = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def spearman(left, right):
    return pearson(average_ranks(left), average_ranks(right))


def percentile(values, fraction):
    if not values:
        return None
    vals = sorted(values)
    if len(vals) == 1:
        return vals[0]
    pos = (len(vals) - 1) * fraction
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(vals) - 1)
    weight = pos - lo
    return vals[lo] * (1.0 - weight) + vals[hi] * weight


def mean(values):
    vals = [value for value in values if value is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


def smallest_covering_k(ranks):
    if not ranks:
        return None
    need = 0.95 * len(ranks)
    limit = max(ranks)
    for k in range(1, limit + 1):
        if sum(rank <= k for rank in ranks) >= need:
            return k
    return limit


def _blank_metrics():
    return {
        "n_plans": 0, "n_winners": 0, "n_passes": 0,
        "agreement": None, "regret": None, "regret_unknown": None,
        "top1": None, "top3": None, "top5": None, "top10": None,
        "median_rank": None, "spearman": None, "k95": None, "top5_overlap": None,
        "pc_top1": None, "pc_top3": None, "pc_top5": None, "pc_top10": None,
        "pc_median_rank": None, "pc_spearman": None, "pc_k95": None, "pc_top5_overlap": None,
        "kept3": None, "avoid3": None, "kept5": None, "avoid5": None,
        "error_median": None, "error_p90": None, "fallback_rate": None,
    }


def _rank_block(usable, score_name):
    exact = sorted(
        usable,
        key=lambda row: (-row["proxy"], -row["tie_profit"], row["tie_capital"], row["key"], row["row_id"]),
    )
    ordered = sorted(
        usable,
        key=lambda row: (
            -(row[score_name] if row[score_name] is not None else float("-inf")),
            -(row["cell_p"] if row["cell_p"] is not None else float("-inf")),
            row["cell_c"] if row["cell_c"] is not None else float("inf"),
            row["key"], row["row_id"],
        ),
    )
    true_first = exact[0]["row_id"]
    rank = next(index for index, row in enumerate(ordered, 1) if row["row_id"] == true_first)
    overlap = len({row["row_id"] for row in exact[:5]} & {row["row_id"] for row in ordered[:5]}) / 5.0
    coefficient = spearman(
        [row["proxy"] for row in usable],
        [row[score_name] if row[score_name] is not None else float("-inf") for row in usable],
    )
    return rank, overlap, coefficient


def metrics_of(predictions, with_fallback=True):
    result = _blank_metrics()
    result["n_plans"] = len(predictions)
    winners = [row for row in predictions if row.get("eng", -1) != -1]
    result["n_winners"] = len(winners)
    if winners:
        result["agreement"] = (
            sum(1 for row in winners if row.get("table_engine") == row.get("eng")) / len(winners)
        )
        regrets = [relative_regret(row) for row in winners]
        known = [value for value in regrets if value is not None]
        result["regret"] = median(known)
        result["regret_unknown"] = (len(winners) - len(known)) / len(winners)
        if with_fallback:
            result["fallback_rate"] = sum(1 for row in winners if row.get("fallback")) / len(winners)
    errors = []
    for row in winners:
        score = decision_score(row)
        cell = row.get("cell_score")
        if score in (None, 0) or cell is None:
            continue
        errors.append(abs(cell - score) / abs(score))
    result["error_median"] = median(errors)
    result["error_p90"] = percentile(errors, 0.9)
    grouped = defaultdict(list)
    for row in predictions:
        grouped[(row.get("game"), row.get("pass"))].append(row)
    score_ranks, pc_ranks = [], []
    score_overlap, pc_overlap = [], []
    score_spearman, pc_spearman = [], []
    kept3, kept5 = [], []
    for rows in grouped.values():
        usable = []
        for row in rows:
            profit, capital, proxy = portfolio_parts(row)
            if proxy is None or proxy <= 0:
                continue
            item = dict(row)
            item["tie_profit"] = profit
            item["tie_capital"] = capital
            item["proxy"] = proxy
            usable.append(item)
        if len(usable) < 5:
            continue
        rank, overlap, coefficient = _rank_block(usable, "cell_score")
        score_ranks.append(rank)
        score_overlap.append(overlap)
        if coefficient is not None:
            score_spearman.append(coefficient)
        rank, overlap, coefficient = _rank_block(usable, "cell_ratio")
        pc_ranks.append(rank)
        pc_overlap.append(overlap)
        if coefficient is not None:
            pc_spearman.append(coefficient)
        computed = sum(1 for row in rows if not row.get("hit"))
        if computed > 0:
            kept3.append(min(3, computed) / computed)
            kept5.append(min(5, computed) / computed)
    result["n_passes"] = len(score_ranks)
    if score_ranks:
        result["top1"] = sum(rank <= 1 for rank in score_ranks) / len(score_ranks)
        result["top3"] = sum(rank <= 3 for rank in score_ranks) / len(score_ranks)
        result["top5"] = sum(rank <= 5 for rank in score_ranks) / len(score_ranks)
        result["top10"] = sum(rank <= 10 for rank in score_ranks) / len(score_ranks)
        result["median_rank"] = median(score_ranks)
        result["spearman"] = mean(score_spearman)
        result["k95"] = smallest_covering_k(score_ranks)
        result["top5_overlap"] = mean(score_overlap)
        result["pc_top1"] = sum(rank <= 1 for rank in pc_ranks) / len(pc_ranks)
        result["pc_top3"] = sum(rank <= 3 for rank in pc_ranks) / len(pc_ranks)
        result["pc_top5"] = sum(rank <= 5 for rank in pc_ranks) / len(pc_ranks)
        result["pc_top10"] = sum(rank <= 10 for rank in pc_ranks) / len(pc_ranks)
        result["pc_median_rank"] = median(pc_ranks)
        result["pc_spearman"] = mean(pc_spearman)
        result["pc_k95"] = smallest_covering_k(pc_ranks)
        result["pc_top5_overlap"] = mean(pc_overlap)
        result["kept3"] = mean(kept3)
        result["avoid3"] = None if result["kept3"] is None else 1.0 - result["kept3"]
        result["kept5"] = mean(kept5)
        result["avoid5"] = None if result["kept5"] is None else 1.0 - result["kept5"]
    return result


def _subset_metrics(predictions, key):
    grouped = defaultdict(list)
    for row in predictions:
        grouped[row.get(key)].append(row)
    return {
        "unknown" if label is None else str(label): metrics_of(rows)
        for label, rows in sorted(grouped.items(), key=lambda item: str(item[0]))
    }


def fit_fold(train, binning, asym_high, asym_low, include_context):
    learned = [plan for plan in train if not plan.get("hit")]
    tables = {
        spec["name"]: fit_table(learned, spec, binning, asym_high, asym_low)
        for spec in iter_specs(include_context)
    }
    return tables


def predict_fold(train, test, tables, seed, include_context):
    out = {}
    for spec in iter_specs(include_context):
        out[spec["name"]] = predict_table(test, tables[spec["name"]], tables)
    out["random"] = predict_random(train, test, seed)
    return out


def config_names(include_context):
    return [spec["name"] for spec in iter_specs(include_context)] + ["random"]


def _jsonable(value):
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def build_report(rows, games, unresolved, binning="quantile", asym_high=0.75, asym_low=0.4,
                 include_context=True):
    seeds = sorted({row["seed"] for row in rows})
    names = config_names(include_context)
    notes = [
        "Apprentissage sur les PLAN calculees seulement. Les HIT resolus repetent "
        "la derniere observation de leur cle et servent au classement.",
        "keptK = min(K, plans calcules) / plans calcules ; avoidK = 1 - keptK. "
        "Les deux sont des moyennes sur les passes d'au moins 5 plans classables.",
        "Le repli d'une cellule vide est la voisine de meme contexte, puis une "
        "grille plus grossiere, puis une cellule d'un autre bras, puis le global.",
        "Temoin aleatoire : un moteur uniforme parmi les vainqueurs d'apprentissage "
        "(Random(20261002 + graine)) et un melange par passe "
        "(Random(20261002 + graine + passe + partie * 100003)).",
        "P_n1/C_n1/P_n2/C_n2 valent -1 tant que le chemin un-ou-deux n'a pas "
        "calcule les deux flottes du vainqueur. pfScore/pfP/pfC valent -1 quand "
        "l'economie portfolio est absente.",
        "mean_cells_with_n1 est le nombre moyen, sur les plis, de cellules "
        "d'apprentissage dont la mediane P du vainqueur en N=1 est connue. "
        "Une valeur -1 ne remplit pas la cellule.",
        "ge=0 scan, 1 raccourci (pas de ligne ENG), 2 controle, 3 repli. "
        "ge_est est le moteur etabli ou -1. Jetons absents : 0 / -1.",
    ]
    if len(seeds) < 2:
        notes.append("Validation croisee indisponible : il faut au moins deux graines.")
    pooled = {name: [] for name in names}
    folds = {name: [] for name in names}
    cell_counts = defaultdict(list)
    n1_counts = defaultdict(list)
    available = len(seeds) >= 2
    if available:
        for held in seeds:
            train = [row for row in rows if row["seed"] != held]
            test = [row for row in rows if row["seed"] == held]
            tables = fit_fold(train, binning, asym_high, asym_low, include_context)
            predicted = predict_fold(
                [row for row in train if not row.get("hit")], test, tables, held, include_context)
            for name in names:
                fold_metrics = metrics_of(predicted[name], with_fallback=name != "random")
                folds[name].append({
                    "seed": held,
                    "n_train": sum(1 for row in train if not row.get("hit")),
                    "n_test": len(test),
                    "metrics": fold_metrics,
                })
                pooled[name].extend(predicted[name])
                if name in tables:
                    cells = tables[name]["cells"]
                    cell_counts[name].append(len(cells))
                    n1_counts[name].append(sum(
                        1 for cell in cells.values() if cell.get("p_n1") is not None))
    configs = {}
    for name in names:
        preds = pooled[name]
        measured = metrics_of(preds, with_fallback=name != "random") if available else _blank_metrics()
        configs[name] = {
            "metrics": measured,
            "by_arm": _subset_metrics(preds, "arm") if available else {},
            "by_year": _subset_metrics(preds, "year") if available else {},
            "by_engines": _subset_metrics(preds, "engine_set") if available else {},
            "folds": folds[name],
            "mean_train_cells": mean(cell_counts[name]) if cell_counts[name] else None,
            "mean_cells_with_n1": mean(n1_counts[name]) if n1_counts[name] else None,
        }
    report = {
        "schema": "c121-engine-table-v1",
        "binning": binning,
        "asym_high": asym_high,
        "asym_low": asym_low,
        "context_included": include_context,
        "portfolio_quantity": PORTFOLIO_QUANTITY,
        "cv": {"available": available, "seeds": seeds},
        "counts": {
            "games": games,
            "seeds": seeds,
            "plans": sum(1 for row in rows if not row.get("hit")),
            "hits": sum(1 for row in rows if row.get("hit")),
            "unresolved_hits": unresolved,
            "passes": len({(row["game"], row["pass"]) for row in rows}),
            "eng_rows": sum(len(row.get("engines_rows") or []) for row in rows if not row.get("hit")),
            "ge": dict(Counter(
                row.get("ge", 0) for row in rows if not row.get("hit"))),
        },
        "configs": configs,
        "notes": notes,
    }
    return _jsonable(report)


def analyse_texts(items, **opts):
    rows = []
    unresolved = 0
    for game, (seed, text) in enumerate(items):
        part, missing = reconstruct(parse_log_text(text), seed, game)
        rows.extend(part)
        unresolved += missing
    return build_report(rows, len(items), unresolved, **opts)


def resolve_log(raw, root=ROOT):
    text = str(raw)
    if text.startswith("/work/"):
        text = text[len("/work/"):]
    path = Path(text)
    if path.is_absolute():
        return path
    for base in (root, root.parent, Path.cwd()):
        candidate = base / path
        if candidate.is_file():
            return candidate
    return root / path


def game_blob(campaign, game):
    arm = str(game.get("arm") or "")
    chunks = [arm]
    arms = campaign.get("arms") or {}
    if isinstance(arms, dict) and arm in arms:
        spec = arms[arm]
        chunks.append(spec if isinstance(spec, str) else json.dumps(spec, sort_keys=True))
    resolved = campaign.get("resolved_arms") or {}
    if isinstance(resolved, dict):
        for key, spec in resolved.items():
            key_text = key if isinstance(key, str) else json.dumps(key, sort_keys=True)
            if key_text == arm or key_text in chunks:
                chunks.append(key_text)
                chunks.append(spec if isinstance(spec, str) else json.dumps(spec, sort_keys=True))
    return "\n".join(chunks)


def game_enabled(campaign, game):
    return NEEDLE in game_blob(campaign, game)


def game_log_path(game):
    for key in ("log_path", "engine_log_path"):
        if game.get(key):
            return game[key]
    health = game.get("health") or {}
    if isinstance(health, dict):
        for key in ("engine_log_path", "log_path"):
            if health.get(key):
                return health[key]
    return None


def seed_of_path(path, explicit, index):
    if explicit is not None and index < len(explicit):
        return int(explicit[index])
    match = re.search(r"(\d+)\D*$", Path(path).stem)
    if match:
        return int(match.group(1))
    return index


def load_campaign(campaign, root):
    items = []
    for game in campaign.get("games") or []:
        if not game_enabled(campaign, game):
            continue
        raw = game_log_path(game)
        if not raw:
            raise FileNotFoundError("partie sans journal : seed=%s" % game.get("seed"))
        path = resolve_log(raw, root)
        if not path.is_file():
            raise FileNotFoundError(path)
        items.append((game.get("seed", 0), path.read_text(encoding="utf-8", errors="replace")))
    return items


def load_inputs(paths, seeds=None, root=ROOT):
    items = []
    raw_index = 0
    for path in paths:
        text = Path(path).read_text(encoding="utf-8")
        stripped = text.lstrip()
        if stripped.startswith("{"):
            data = json.loads(text)
            if isinstance(data, dict) and "games" in data:
                items.extend(load_campaign(data, root))
                continue
        items.append((seed_of_path(path, seeds, raw_index), text))
        raw_index += 1
    return items


def analyse_paths(paths, seeds=None, root=ROOT, **opts):
    items = load_inputs(paths, seeds=seeds, root=root)
    if not items:
        report = build_report([], 0, 0, **opts)
        report["notes"].insert(0, "Aucune partie du bras probe_c121_engine_table=1.")
        return report
    return analyse_texts(items, **opts)


def _fmt(value):
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return "%.3f" % value
    return str(value)


def _markdown_table(headers, rows):
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_fmt(value) for value in row) + " |")
    return "\n".join(lines)


def format_markdown(report):
    counts = report["counts"]
    lines = [
        "# Table de moteurs C121",
        "",
        "Graines %s, parties %s, PLAN %s, HIT %s (non resolus %s), passes %s, lignes ENG %s."
        % (
            ", ".join(str(seed) for seed in counts["seeds"]) or "aucune",
            counts["games"], counts["plans"], counts["hits"], counts["unresolved_hits"],
            counts["passes"], counts["eng_rows"],
        ),
        "",
        "Quantite du portefeuille : %s" % report["portfolio_quantity"],
        "",
        "Binning %s, asymetrie %.2f / %.2f, contexte %s, validation croisee %s."
        % (
            report["binning"], report["asym_high"], report["asym_low"],
            "inclus" if report["context_included"] else "retire",
            "oui" if report["cv"]["available"] else "non",
        ),
        "",
    ]
    for note in report["notes"]:
        lines.append("- %s" % note)
    headers = [
        "config", "agree", "regret", "unk", "top1", "top3", "top5", "top10",
        "med_rank", "spearman", "k95", "ov5", "kept3", "avoid3", "kept5", "avoid5",
        "err_med", "err_p90", "fallback", "pc_top1", "pc_top5", "pc_spearman",
        "cells", "n1cells",
    ]
    body = []
    for name, config in report["configs"].items():
        metrics = config["metrics"]
        body.append([
            name, metrics["agreement"], metrics["regret"], metrics["regret_unknown"],
            metrics["top1"], metrics["top3"], metrics["top5"], metrics["top10"],
            metrics["median_rank"], metrics["spearman"], metrics["k95"], metrics["top5_overlap"],
            metrics["kept3"], metrics["avoid3"], metrics["kept5"], metrics["avoid5"],
            metrics["error_median"], metrics["error_p90"], metrics["fallback_rate"],
            metrics["pc_top1"], metrics["pc_top5"], metrics["pc_spearman"],
            config["mean_train_cells"], config["mean_cells_with_n1"],
        ])
    lines.extend(["", _markdown_table(headers, body), ""])
    for name in ("dxd-8", "dxd-8-asym"):
        config = report["configs"].get(name)
        if config is None:
            continue
        lines.append("## %s" % name)
        lines.append("")
        for title, key in (("bras", "by_arm"), ("annee", "by_year"), ("moteurs", "by_engines")):
            lines.append("### %s" % title)
            lines.append("")
            rows = []
            for label, metrics in config[key].items():
                rows.append([
                    label, metrics["n_winners"], metrics["agreement"], metrics["top1"],
                    metrics["top5"], metrics["spearman"], metrics["fallback_rate"],
                ])
            lines.append(_markdown_table(
                [title, "n", "agree", "top1", "top5", "spearman", "fallback"], rows))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=(
        "Mesure hors ligne si une table distance x demande x contexte retrouve "
        "le moteur C121 et le classement des plans."
    ))
    parser.add_argument("inputs", nargs="+", type=Path,
                        help="JSON de diagnostic ou journaux bruts")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--binning", choices=("quantile", "log"), default="quantile")
    parser.add_argument("--asym-high", type=float, default=0.75)
    parser.add_argument("--asym-low", type=float, default=0.4)
    parser.add_argument("--seeds", type=int, nargs="*")
    parser.add_argument("--no-context", action="store_true",
                        help="Ne pas evaluer les tables qui croisent bras et type d'aeroport")
    args = parser.parse_args(argv)
    report = analyse_paths(
        args.inputs,
        seeds=args.seeds,
        binning=args.binning,
        asym_high=args.asym_high,
        asym_low=args.asym_low,
        include_context=not args.no_context,
    )
    sys.stdout.write(format_markdown(report))
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
