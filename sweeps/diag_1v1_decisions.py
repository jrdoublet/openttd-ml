"""Diagnostic 1v1 mois par mois : les DECISIONS des deux IA, et leurs RAISONS.

Ce que ce harnais ajoute a diag_1v1_monthly.py : il ne compte plus seulement ce que les deux IA
POSSEDENT (vehicules, gares, tresorerie, tire des chunks de sauvegarde), il lit ce qu'elles
DECIDENT et pourquoi.

Le verrou leve (2026-09-03) : le code affirmait a trois endroits que AILog n'est pas capture par
OpenTTDLab. C'est vrai PAR DEFAUT seulement. OpenTTDLab n'expose aucun crochet pour les arguments
de ligne de commande d'OpenTTD, mais il lance le binaire par subprocess.check_output et
parallelise par multiprocessing.Pool ; sous Linux le demarrage est `fork`, donc un patch pose ici
AVANT l'appel est herite par les workers. On patche donc openttdlab.subprocess.check_output pour
injecter `-d script=4`, sans jamais toucher au paquet installe.

  script=3 ne rend que les [W] ; les [I] arrivent a 4. Verifie.

Les deux journaux :
  - AAAHogEx journalise deja ~2 077 lignes/an via son helper HgLog (ai/AAAHogEx-115/utils.nut:543),
    chacune prefixee par la date de jeu et portant souvent le nom de la fonction appelante entre
    parentheses : "1970-7-8 Not enough money (TrainInfoDictionary.CreateTrainInfo) ... price:12890".
  - OpexAI journalise sous le reglage `decision_log` (defaut 0), au format impose
    "OPEX <a>-<m>-<j> <KIND> <cle=valeur> ...".

⚠️ `decision_log` DOIT rester a 0 hors diagnostic : le comportement de l'IA depend du nombre
d'opcodes consommes, donc journaliser change les parties. Ce harnais l'allume volontairement ; ses
chiffres de valeur ne sont donc PAS comparables a ceux des bancs.

Parties ISOLEES, comme sweeps/bench.py et diag_1v1_monthly.py : chaque IA joue seule sur la meme
graine. Un duel en partie partagee est une autre experience, plus spectaculaire mais confondue.
"""
import argparse
import json
import re
import statistics
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work")
OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
AAAHOGEX_DIR = "AAAHogEx-115"
SCRIPT_DEBUG_LEVEL = "4"

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    """Injecte -d script=N sur le SEUL lancement de partie (repere par -vnull).

    Le second lancement eventuel (screenshot) ne porte pas -vnull et ne doit pas etre touche.
    """
    args = tuple(args)
    if any(str(a).startswith("-vnull") for a in args):
        args = args[:1] + ("-d", f"script={SCRIPT_DEBUG_LEVEL}") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

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

VEHICLE_MODES = ("train", "roadveh", "ship", "aircraft")
TYPE_TO_MODE = {"0": "train", "1": "roadveh", "2": "ship", "3": "aircraft"}

# [script:4] [<compagnie>] [<niveau>] <texte>
LINE_RE = re.compile(r"\[script:\d+\] \[(\d+)\] \[(\w)\] (.*)")
# Notre grammaire : OPEX <a>-<m>-<j> <KIND> <cle=valeur> ...
OPEX_RE = re.compile(r"^OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")
# AAAHogEx : <a>-<m>-<j> <texte>, avec parfois (NomDeFonction) dans le texte.
HOGEX_RE = re.compile(r"^(\d+)-(\d+)-(\d+) (.*)$")
HOGEX_FUNC_RE = re.compile(r"\(([A-Za-z_][A-Za-z0-9_.]*)\)")


def _first(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def parse_decisions(output, arm):
    """Rend une liste d'evenements {mois, kind, reason, fields, raw} pour UNE partie.

    Les deux IA sont journalisees differemment : la notre en cle=valeur imposees, la sienne en
    prose. On normalise sur (mois, kind), le `kind` etant le KIND explicite chez nous et le
    debut de phrase chez elle -- c'est ce qui rend les deux colonnes comparables.
    """
    events = []
    for line in (output or "").splitlines():
        m = LINE_RE.search(line)
        if not m:
            continue
        _company, level, text = m.groups()
        text = text.strip()

        if arm == "OpexAI":
            m2 = OPEX_RE.match(text)
            if not m2:
                continue
            year, month, day, kind, rest = m2.groups()
            fields = {}
            for token in rest.split():
                if "=" in token:
                    key, _, value = token.partition("=")
                    fields[key] = value
            events.append({
                "month": f"{int(year):04d}-{int(month):02d}",
                "day": int(day), "level": level, "kind": kind,
                "reason": fields.get("reason") or fields.get("why"),
                "fields": fields, "raw": text,
            })
            continue

        m2 = HOGEX_RE.match(text)
        if not m2:
            continue
        year, month, day, body = m2.groups()
        func = HOGEX_FUNC_RE.search(body)
        # Le "kind" d'AAAHogEx est le debut de phrase avant la parenthese de fonction : c'est la
        # partie stable ("Not enough money", "Build railroute"), le reste etant les parametres.
        head = body.split("(")[0].strip()
        head = re.sub(r"[0-9]+", "#", head)[:60].strip()
        events.append({
            "month": f"{int(year):04d}-{int(month):02d}",
            "day": int(day), "level": level, "kind": head or "?",
            "reason": None, "fields": {"func": func.group(1)} if func else {},
            "raw": body,
        })
    return events


def vehicle_breakdown(chunks, owner=0):
    """VEHS est un enregistrement A VARIANTES : toutes les cles de mode sont presentes quel que
    soit le type reel. C'est le champ `type` (une CHAINE) qui tranche, jamais la presence d'une cle.
    """
    by_mode = dict.fromkeys(VEHICLE_MODES, 0)
    profit_by_mode = dict.fromkeys(VEHICLE_MODES, 0)
    capital = 0
    profits = []
    for record in (chunks.get("VEHS") or {}).values():
        record = _first(record)
        if not record or record.get("owner") != owner:
            continue
        mode = TYPE_TO_MODE.get(str(record.get("type")))
        if mode is None:
            continue
        by_mode[mode] += 1
        profit = record.get("profit_this_year") or 0
        profit_by_mode[mode] += profit
        profits.append(profit)
        capital += record.get("value") or 0
    return {
        "by_mode": by_mode, "profit_by_mode": profit_by_mode,
        "n_vehicles": sum(by_mode.values()), "rolling_capital": capital,
        "profit_per_vehicle": (sum(profits) / len(profits)) if profits else None,
    }


def station_detail(chunks, owner=0):
    ratings, waiting, n = [], 0, 0
    for record in (chunks.get("STNN") or {}).values():
        record = _first(record)
        if not record or record.get("owner") != owner:
            continue
        n += 1
        for goods in record.get("goods") or []:
            goods = _first(goods) or {}
            rating = goods.get("rating")
            if rating is not None and (goods.get("cargo_count") or 0) > 0:
                ratings.append(rating)
            waiting += goods.get("cargo_count") or 0
    return {
        "n_stations": n, "waiting_cargo": waiting,
        "median_rating": statistics.median(ratings) if ratings else None,
        "n_rated": len(ratings),
    }


def keep(row):
    chunks = row["chunks"]
    player = (chunks.get("PLYR") or {}).get(0) or (chunks.get("PLYR") or {}).get("0") or {}
    closed = player.get("old_economy") or []
    last = closed[0] if closed else {}
    return ({
        "arm": row["experiment"]["diag_arm"],
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        "money": player.get("money"),
        "current_loan": player.get("current_loan"),
        "company_value": last.get("company_value"),
        "delivered_cargo": last.get("delivered_cargo"),
        "performance_history": last.get("performance_history"),
        "vehicles": vehicle_breakdown(chunks),
        "stations": station_detail(chunks),
        "signs": [s["name"] for s in chunks.get("SIGN", {}).values()],
        # Identique sur toutes les lignes d'une meme partie : dedoublonne dans le parent.
        "output": row.get("output"),
    },)


def build_experiments(seeds, years, decision_log):
    arms = {
        "OpexAI": local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI",
                               (("air_fleet_probe", 1), ("decision_log", 1 if decision_log else 0))),
        "AAAHogEx": local_folder(str(ROOT / "ai" / AAAHOGEX_DIR), "AAAHogEx", ()),
    }
    return [
        {"seed": seed, "days": 365 * years, "openttd_config": CFG,
         "ais": (arms[arm],), "diag_arm": arm}
        for seed in seeds for arm in arms
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=2)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 7])
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "diag_1v1_decisions.json")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--no-decision-log", action="store_true",
                        help="laisse decision_log a 0 (mesure la richesse du seul journal adverse)")
    args = parser.parse_args()

    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        experiments=build_experiments(args.seeds, args.years, not args.no_decision_log),
        max_workers=args.workers, result_processor=keep,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    # Le journal complet est attache a CHAQUE sauvegarde mensuelle de la meme partie : on ne le
    # parse qu'une fois par (bras, graine), puis on le retire des lignes avant d'ecrire le JSON.
    logs, decisions = {}, []
    for record in rows:
        key = (record["arm"], record["seed"])
        if key not in logs and record.get("output"):
            logs[key] = record["output"]
    for (arm, seed), output in logs.items():
        for event in parse_decisions(output, arm):
            event["arm"], event["seed"] = arm, seed
            decisions.append(event)
    for record in rows:
        record.pop("output", None)

    months = sorted({r["date"][:7] for r in rows})
    per_month = defaultdict(list)
    for r in rows:
        per_month[(r["arm"], r["date"][:7])].append(r)
    dec_month = defaultdict(list)
    for e in decisions:
        dec_month[(e["arm"], e["month"])].append(e)

    print(f"\njournaux captures : {len(logs)} parties, {len(decisions)} decisions\n")
    header = (f"{'mois':<8} | {'OpexAI tr/rt/bt/av':>19} {'gares':>5} {'valeur':>10} {'decis':>6}"
              f" | {'AAAHogEx tr/rt/bt/av':>20} {'gares':>5} {'valeur':>10} {'decis':>6}")
    print(header)
    print("-" * len(header))
    for month in months:
        line = f"{month:<8} |"
        for arm in ("OpexAI", "AAAHogEx"):
            month_rows = per_month[(arm, month)]
            if not month_rows:
                line += f" {'-':>19} {'-':>5} {'-':>10} {'-':>6} |"
                continue
            mix = "/".join(
                f"{statistics.mean([r['vehicles']['by_mode'][m] for r in month_rows]):.0f}"
                for m in VEHICLE_MODES)
            st = statistics.mean([r["stations"]["n_stations"] for r in month_rows])
            cv = [r["company_value"] for r in month_rows if r["company_value"] is not None]
            nd = len(dec_month[(arm, month)])
            line += (f" {mix:>19} {st:>5.1f} {statistics.mean(cv) if cv else 0:>10,.0f}"
                     f" {nd:>6} |")
        print(line)

    print("\n--- vocabulaire de decision, 15 premiers par IA ---")
    for arm in ("OpexAI", "AAAHogEx"):
        counts = Counter(e["kind"] for e in decisions if e["arm"] == arm)
        print(f"\n{arm} : {sum(counts.values())} decisions, {len(counts)} types")
        for kind, count in counts.most_common(15):
            print(f"   {count:6d}  {kind}")

    args.out.write_text(json.dumps({
        "openttd_version": OPENTTD_VERSION, "years": args.years, "seeds": args.seeds,
        "openttd_config": CFG, "script_debug_level": SCRIPT_DEBUG_LEVEL,
        "decision_log": not args.no_decision_log,
        "rows": rows, "decisions": decisions,
    }, indent=1))
    print(f"\necrit {args.out}")


if __name__ == "__main__":
    main()
