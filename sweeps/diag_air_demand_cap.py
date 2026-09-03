"""Sonde du plafond aerien derive de la demande (air_demand_cap / air_demand_plan).

Deux questions, AVANT de depenser un banc apparie :

  1. `air_demand_cap` MORD-il ? Le plafond physique (4/16 avions) a deja ete mesure a 0 refus
     sur 32 (docs/taches.md S0 quinvicies) : un plafond qui ne se declenche jamais n'a rien a
     mesurer. On compte donc les refus de code `Q` (`demand_cap_reached`) et, quand le plafond
     ne mord pas, la MARGE entre flotte et plafond -- un plafond jamais atteint de peu et un
     plafond jamais atteint de loin ne demandent pas le meme travail.
  2. `air_demand_plan` AFFAME-t-il le bras aerien ? Il ne remplace pas qu'un plafond : il change
     l'ASSIETTE de la demande, de `pop x 22 %` (population) vers
     `GetLastMonthProduction x 22 %` (production reelle). Les 22 % ont ete calibres le 2026-08-28
     comme le rapport production-atteignant-la-gare / GetLastMonthProduction (candidates.nut:492) :
     les appliquer a une POPULATION n'avait pas de sens, mais la correction fait chuter l'assiette,
     donc `revenueAnnual`, donc le nombre de plans qui passent `profitAnnual > 0`.

Quatre bras factoriels sur les memes graines, lecture appairee par graine. Sortie : histogramme
des motifs de refus de croissance, journal AIR_DEMAND_CAP (plafond, demande, capacite, marge),
constructions aeriennes reussies, et les metriques de fin de partie pour reperer un effondrement.

⚠️ Ce n'est PAS un banc : 3 graines ne tranchent rien (docs/taches.md, banc mono-graine). La
sortie sert a decider s'il y a quelque chose a mesurer, pas a conclure.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import enable_savegame_cleanup, make_cfg, quarter_profit, year_profit  # noqa: E402

OPENTTD_VERSION, OPENGFX_VERSION = "15.3", "7.1"
SCRIPT_DEBUG_LEVEL = "4"
CFG = make_cfg(1970)

# Les deux reglages sont INDEPENDANTS par construction : un bras chacun, plus la combinaison.
ARMS = (
    ("base", 0, 0),
    ("cap", 1, 0),
    ("plan", 0, 1),
    ("cap+plan", 1, 1),
)

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    """`-d script=4` rend le journal de decision (AILog EST capturable, docs/taches.md)."""
    args = tuple(args)
    if any(str(a).startswith("-vnull") for a in args):
        args = args[:1] + ("-d", f"script={SCRIPT_DEBUG_LEVEL}") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

LINE_RE = re.compile(r"\[script:\d+\] \[(\d+)\] \[(\w)\] (.*)")
OPEX_RE = re.compile(r"^OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")


def parse_opex_decisions(output):
    events = []
    for line in (output or "").splitlines():
        m = LINE_RE.search(line)
        if not m:
            continue
        m2 = OPEX_RE.match(m.group(3).strip())
        if not m2:
            continue
        year, month, day, kind, rest = m2.groups()
        fields = {}
        for token in rest.split():
            if "=" in token:
                key, _, value = token.partition("=")
                fields[key] = value
        events.append({"date": f"{int(year):04d}-{int(month):02d}-{int(day):02d}",
                       "kind": kind, "fields": fields})
    return events


def n_aircraft(chunks, owner=0):
    count = 0
    for vehicle in (chunks.get("VEHS") or {}).values():
        if not isinstance(vehicle, dict) or str(vehicle.get("type")) != "3":
            continue
        body = vehicle.get("aircraft")
        body = body[0] if isinstance(body, list) and body else body
        common = (body or {}).get("common") if isinstance(body, dict) else None
        common = common[0] if isinstance(common, list) and common else common
        if isinstance(common, dict) and common.get("owner") == owner:
            count += 1
    return count


def keep(row):
    chunks = row["chunks"]
    player = chunks.get("PLYR", {}).get(0) or chunks.get("PLYR", {}).get("0")
    closed = (player or {}).get("old_economy") or []
    last_closed = closed[0] if closed else {}
    return ({
        "arm": row["experiment"]["diag_arm"],
        "seed": row["experiment"]["seed"],
        "date": str(row["date"]),
        # L'ordre des objectifs met le PROFIT avant la valeur : la premiere version de cette
        # sonde ne relevait que company_value, et son tableau a donc flatte un reglage que le
        # banc a ensuite rejete a -51,5 % de profit_year (S3 undecies bis).
        "profit": quarter_profit(last_closed),
        "profit_year": year_profit(closed),
        "company_value": last_closed.get("company_value"),
        "performance_history": last_closed.get("performance_history"),
        "n_vehicles": len(chunks.get("VEHS", {})),
        "n_aircraft": n_aircraft(chunks),
        "n_stations": len(chunks.get("STNN", {})),
        "output": row.get("output"),
    },)


def summarise(events):
    """Ce que la sonde doit repondre, et rien de plus."""
    refusals = Counter()
    caps = []
    builds = 0
    for e in events:
        if e["kind"] == "AIR_FLEET":
            f = e["fields"]
            if f.get("action") == "refuse":
                refusals[f.get("reason", "?")] += 1
        elif e["kind"] == "AIR_DEMAND_CAP":
            f = e["fields"]
            try:
                cap, planes = int(f.get("cap", 0)), int(f.get("planes", 0))
            except ValueError:
                continue
            caps.append({
                "date": e["date"], "line": f.get("line"), "cap": cap, "planes": planes,
                "marge": cap - planes,
                "monthly_demand": f.get("monthly_demand"),
                "capacity_per_plane": f.get("capacity_per_plane"),
                "physical_cap": f.get("physical_cap"),
                "applied_cap": f.get("applied_cap"),
                "routes_a": f.get("routes_a"), "routes_b": f.get("routes_b"),
            })
        elif e["kind"] == "AIR_BUILD":
            builds += 1
    binding = [c for c in caps if c["planes"] >= c["cap"]]
    marges = sorted(c["marge"] for c in caps)
    return {
        "refusals": dict(refusals),
        "q_refusals": refusals.get("demand_cap_reached", 0),
        "c_refusals": refusals.get("airport_capacity_reached", 0),
        "air_builds": builds,
        "cap_evaluations": len(caps),
        "cap_binding": len(binding),
        "marge_min": marges[0] if marges else None,
        "marge_mediane": marges[len(marges) // 2] if marges else None,
        "cap_samples": caps[:40],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=3)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 999, 12345])
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "diag_air_demand_cap.json")
    args = parser.parse_args()

    enable_savegame_cleanup()

    experiments = []
    for name, cap, plan in ARMS:
        for seed in args.seeds:
            ai = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", (
                ("decision_log", 1),
                ("air_demand_cap", cap),
                ("air_demand_plan", plan),
            ))
            experiments.append({
                "seed": seed, "days": 365 * args.years, "openttd_config": CFG,
                "ais": (ai,), "diag_arm": name,
            })

    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        experiments=experiments, max_workers=args.workers, result_processor=keep,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))

    finals, summaries = {}, {}
    for r in sorted(rows, key=lambda r: r["date"]):
        key = f"{r['arm']}|{r['seed']}"
        if r.get("output"):
            summaries[key] = summarise(parse_opex_decisions(r["output"]))
        finals[key] = {k: v for k, v in r.items() if k != "output"}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "years": args.years, "seeds": args.seeds,
        "arms": [{"name": n, "air_demand_cap": c, "air_demand_plan": p} for n, c, p in ARMS],
        "finals": finals, "summaries": summaries,
    }, indent=1))

    print(f"\n{'bras':10} {'graine':>7} {'profit_an':>11} {'valeur':>10} {'avions':>7} "
          f"{'lignes air':>11} {'refus Q':>8} {'refus C':>8} {'marge med':>10}")
    for name, _c, _p in ARMS:
        for seed in args.seeds:
            key = f"{name}|{seed}"
            f, s = finals.get(key, {}), summaries.get(key, {})
            print(f"{name:10} {seed:>7} {str(f.get('profit_year')):>11} "
                  f"{str(f.get('company_value')):>10} "
                  f"{str(f.get('n_aircraft')):>7} {str(s.get('air_builds')):>11} "
                  f"{str(s.get('q_refusals')):>8} {str(s.get('c_refusals')):>8} "
                  f"{str(s.get('marge_mediane')):>10}")
    print("\necrit", args.out)


if __name__ == "__main__":
    main()
