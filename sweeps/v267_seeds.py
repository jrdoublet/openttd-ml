#!/usr/bin/env python3
"""V267 : choisir 40 graines de banc complementaires (docs/taches.md, V267).

Trois sous-commandes, bibliotheque standard seule :

  generate  tire une population de graines, deterministe (meme LCG POSIX que SEEDS_EXTRA_20
            de bench_v2.py, initialise a une autre date), graine 73 exclue (AAAHogEx plante,
            route.nut:2056), les 39 graines historiques de SEEDS_40 incluses pour pouvoir juger
            la liste actuelle contre la population.
  command   ecrit la ou les commandes PC (run_c66_reference.py, profil PC du 18/10).
            Bras de reference = master au defaut ; bras variante = un effet deja qualifie
            (controle de detection, critere b de V267).
  select    lit les variables de carte (v267_maps.py) et/ou les JSONL de campagnes (annees 3, 6, 10).
            Remplit d'abord des quotas : quelques graines dans chacun des deux deciles extremes de
            chaque variable de couverture (COVERAGE : relief, mer, rivieres, ponts a franchir,
            industries, parts de mode...), puis complete par glouton MMD (noyau gaussien sur
            variables centrees reduites) pour rester representatif de la population.
            Rapport : moyenne et quantiles population / selection / liste historique, et effet
            du controle (variante - reference) par horizon.

Exemples (parcours complet : sweeps/run_v267_pc.sh) :
  python3 sweeps/v267_maps.py screen --count 3000 --out results/v267_maps_3000.jsonl   # dans Docker
  python3 sweeps/v267_seeds.py select --maps results/v267_maps_3000.jsonl --no-control --k 300 --seeds-out results/v267_pop_300.txt
  python3 sweeps/v267_seeds.py command --seeds-file results/v267_pop_300.txt --campaign v267_main_x10_pc_20261019 --no-control
  python3 sweeps/v267_seeds.py select results/v267_main_x10_pc_20261019*.jsonl --maps results/v267_maps_3000.jsonl --no-control --k 40
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _bench_v2_seeds_40() -> tuple[int, ...]:
    """SEEDS_40 lu dans bench_v2.py sans l'importer (il importe openttdlab, absent hors Docker)."""
    import ast
    tree = ast.parse((ROOT / "sweeps" / "bench_v2.py").read_text())
    values: dict[str, tuple[int, ...]] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in ("SEEDS", "SEEDS_EXTRA_20"):
                values[name] = tuple(ast.literal_eval(node.value))
    return values["SEEDS"] + values["SEEDS_EXTRA_20"]


SEEDS_40 = _bench_v2_seeds_40()

EXCLUDED = {73}  # AAAHogEx plante (route.nut:2056, memoire aaahogex_crash_graine73)
LCG_INIT = 20261019  # date de V267, comme 20260923 pour SEEDS_EXTRA_20
HORIZONS = (3, 6, 10)
START_YEAR = 1970
PC_PROFILE = ["--cpus", "10", "--memory", "8g", "--max-workers", "10", "--network", "host"]
# Controle de detection par defaut : V252 coupe contre V252 mode 2 (defaut), qualifie le 18/10
# (portes A et B ; remesure PC 10 ans : -354 k/an quand on le coupe).
CONTROL_REFERENCE = "OpexAI[v252_air_engine_refresh=2]"
CONTROL_VARIANT = "OpexAI[v252_air_engine_refresh=0]"


def lcg_seeds(count: int, init: int = LCG_INIT, exclude: set[int] | None = None) -> list[int]:
    """Graines nouvelles, hors SEEDS_40 et hors exclusions, meme procede que SEEDS_EXTRA_20."""
    exclude = set(exclude or ()) | set(SEEDS_40) | {0}
    out: list[int] = []
    x = init
    while len(out) < count:
        x = (1103515245 * x + 12345) % (2 ** 31)
        seed = x % 1_000_000
        if seed in exclude or seed in out:
            continue
        out.append(seed)
    return out


def cmd_generate(args: argparse.Namespace) -> None:
    historic = [s for s in SEEDS_40 if s not in EXCLUDED]
    fresh = lcg_seeds(args.count - len(historic), args.init, EXCLUDED)
    seeds = historic + fresh
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(str(s) for s in seeds) + "\n")
    print(f"{len(seeds)} graines ({len(historic)} historiques, {len(fresh)} nouvelles) -> {args.out}")


def read_seeds(path: str) -> list[int]:
    return [int(x) for x in Path(path).read_text().split() if x.strip()]


def cmd_command(args: argparse.Namespace) -> None:
    seeds = read_seeds(args.seeds_file)
    seeds = seeds[args.offset:]
    if args.limit:
        seeds = seeds[: args.limit]
    chunks = max(1, args.chunks)
    size = math.ceil(len(seeds) / chunks)
    for i in range(chunks):
        part = seeds[i * size:(i + 1) * size]
        if not part:
            continue
        campaign = args.campaign if chunks == 1 else f"{args.campaign}_c{i + 1}"
        cmd = [
            "python3", "sweeps/run_c66_reference.py", "--campaign", campaign,
            # Un bras sans --reference : OpexAI aux defauts de l'arbre (policy-id "reference").
            *(["--reference", args.reference or CONTROL_REFERENCE] if not args.no_control
              else (["--reference", args.reference] if args.reference else [])),
            *([] if args.no_control else ["--variant", args.variant, "--variant-policy-id", args.variant_policy_id]),
            # Un seul bras (C66.3) : le lanceur refuse les options de decision C66.4.
            *([] if args.no_control else [
                "--decision-rule", "non_erosion", "--primary-metric", "profit_year",
                "--min-useful-primary-delta-pct", "4", "--value-guard-max-loss-pct", "5"]),
            "--years", str(args.years), "--repeats", "1", "--seeds", *map(str, part),
            *PC_PROFILE,
        ]
        print(" ".join(f'"{c}"' if "[" in c else c for c in cmd))


def checkpoint(horizon: int) -> str:
    return f"{START_YEAR + horizon - 1}-12-01"


def load_rows(paths: list[str]) -> dict:
    """{(seed, policy, company): {date: row}} pour les dates de controle seulement."""
    wanted = {checkpoint(h) for h in HORIZONS}
    out: dict = {}
    for path in paths:
        with open(path) as fh:
            for line in fh:
                row = json.loads(line)
                if row.get("date") not in wanted:
                    continue
                company, seed, _rep = row["run"]
                key = (seed, row.get("duel_policy_id") or row.get("policy_id"), company)
                out.setdefault(key, {})[row["date"]] = row
    return out


def seed_features(rows: dict, reference: str, variant: str | None) -> dict[int, dict[str, float]]:
    feats: dict[int, dict[str, float]] = {}
    seeds = sorted({k[0] for k in rows})
    for seed in seeds:
        opex = rows.get((seed, reference, "OpexAI"), {})
        aaa = rows.get((seed, reference, "AAAHogEx"), {})
        f: dict[str, float] = {}
        ok = True
        for h in HORIZONS:
            d = checkpoint(h)
            o, a = opex.get(d), aaa.get(d)
            if o is None or a is None or o.get("profit_year") is None or a.get("profit_year") is None:
                ok = False
                break
            po, pa = float(o["profit_year"]), float(a["profit_year"])
            vo, va = float(o.get("company_value") or 0), float(a.get("company_value") or 0)
            f[f"opex_profit_y{h}"] = po
            f[f"aaa_profit_y{h}"] = pa
            f[f"profit_ratio_y{h}"] = po / pa if pa > 0 else 0.0
            f[f"value_ratio_y{h}"] = vo / va if va > 0 else 0.0
            if variant is not None:
                ov = rows.get((seed, variant, "OpexAI"), {}).get(d)
                if ov is None or ov.get("profit_year") is None:
                    ok = False
                    break
                f[f"control_delta_y{h}"] = float(ov["profit_year"]) - po
        if not ok:
            continue
        last = opex[checkpoint(HORIZONS[-1])]
        by_mode = last.get("primary_vehicles_by_mode") or {}
        total = sum(by_mode.values()) or 1
        for mode in ("air", "rail", "road", "water"):
            f[f"share_{mode}_y{HORIZONS[-1]}"] = by_mode.get(mode, 0) / total
        f[f"stations_y{HORIZONS[-1]}"] = float(last.get("n_stations") or 0)
        feats[seed] = f
    return feats


def standardize(feats: dict[int, dict[str, float]], names: list[str]) -> dict[int, list[float]]:
    cols = {n: [feats[s][n] for s in feats] for n in names}
    mu = {n: statistics.fmean(v) for n, v in cols.items()}
    sd = {n: (statistics.pstdev(v) or 1.0) for n, v in cols.items()}
    return {s: [(feats[s][n] - mu[n]) / sd[n] for n in names] for s in feats}


def greedy_mmd(z: dict[int, list[float]], k: int, initial: list[int] | None = None) -> list[int]:
    """Glouton : a chaque pas, la graine qui minimise la MMD^2 entre selection et population.

    initial : graines deja retenues (quotas de couverture), completees jusqu'a k.
    """
    seeds = list(z)
    n = len(seeds)
    index = {s: i for i, s in enumerate(seeds)}
    dim = len(next(iter(z.values())))
    gamma = 1.0 / (2.0 * dim)  # largeur de bande = dimension (variables centrees reduites)
    K = [[math.exp(-gamma * sum((a - b) ** 2 for a, b in zip(z[s], z[t]))) for t in seeds] for s in seeds]
    pop_mean = [sum(row) / n for row in K]  # moyenne du noyau de chaque graine vers la population
    chosen: list[int] = []
    sum_k = [0.0] * n  # somme des noyaux vers les graines deja choisies
    for seed in initial or []:
        best = index[seed]
        chosen.append(best)
        for j in range(n):
            sum_k[j] += K[j][best]
    for step in range(len(chosen), min(k, n)):
        m = step + 1
        best, best_val = None, None
        for i in range(n):
            if i in chosen:
                continue
            # MMD^2 = const - 2/m sum_j mean_pop(j) + 1/m^2 sum_jl K(j,l), restreinte aux termes variables
            self_term = (sum(sum_k[j] for j in chosen) + 2 * sum_k[i] + K[i][i]) / (m * m)
            cross = 2.0 * (sum(pop_mean[j] for j in chosen) + pop_mean[i]) / m
            val = self_term - cross
            if best_val is None or val < best_val:
                best, best_val = i, val
        chosen.append(best)
        for j in range(n):
            sum_k[j] += K[j][best]
    return [seeds[i] for i in chosen]


def tail_quotas(feats: dict[int, dict[str, float]], names: list[str], tail: float, per_tail: int) -> dict:
    """{(variable, 'haut'|'bas'): graines du decile extreme} pour chaque variable de couverture."""
    quotas = {}
    for n in names:
        ranked = sorted(feats, key=lambda s: (feats[s][n], s))
        size = max(per_tail, int(round(tail * len(ranked))))
        lo, hi = ranked[:size], ranked[-size:]
        if feats[lo[-1]][n] < feats[hi[0]][n]:  # variable non degeneree
            quotas[(n, "bas")] = set(lo)
            quotas[(n, "haut")] = set(hi)
    return quotas


def coverage_seeds(quotas: dict, per_tail: int, budget: int) -> tuple[list[int], list]:
    """Glouton de couverture : la graine qui remplit le plus de quotas encore ouverts."""
    need = {key: per_tail for key in quotas}
    chosen: list[int] = []
    candidates = sorted(set().union(*quotas.values())) if quotas else []
    while len(chosen) < budget:
        best, gain = None, 0
        for s in candidates:
            if s in chosen:
                continue
            g = sum(1 for key, members in quotas.items() if need[key] > 0 and s in members)
            if g > gain:
                best, gain = s, g
        if best is None:
            break
        chosen.append(best)
        for key, members in quotas.items():
            if best in members and need[key] > 0:
                need[key] -= 1
    return chosen, sorted(key for key, left in need.items() if left > 0)


def load_maps(paths: list[str]) -> dict[int, dict[str, float]]:
    out = {}
    for path in paths:
        for line in Path(path).read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                seed = row.pop("seed")
                out[seed] = {f"map_{k}": float(v) for k, v in row.items() if isinstance(v, (int, float))}
    return out


def quantile(values: list[float], q: float) -> float:
    v = sorted(values)
    if not v:
        return float("nan")
    pos = q * (len(v) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (pos - lo)


def bootstrap_ci(values: list[float], reps: int = 2000, seed: int = LCG_INIT) -> tuple[float, float]:
    rng = random.Random(seed)
    means = sorted(statistics.fmean(rng.choices(values, k=len(values))) for _ in range(reps))
    return means[int(0.025 * reps)], means[int(0.975 * reps) - 1]


def describe(label: str, feats: dict, seeds: list[int], names: list[str]) -> None:
    print(f"\n== {label} ({len(seeds)} graines)")
    for n in names:
        v = [feats[s][n] for s in seeds]
        print(f"  {n:24s} moy {statistics.fmean(v):>14.3f}  q10 {quantile(v, .1):>14.3f}"
              f"  q50 {quantile(v, .5):>14.3f}  q90 {quantile(v, .9):>14.3f}")


# Variables de couverture (quotas des deux deciles extremes) : la carte elle-meme, puis ce que
# l'IA y a fait quand des parties existent. Les variables absentes ou constantes sont ignorees.
COVERAGE = (
    "map_height_mean", "map_roughness", "map_sea_share", "map_river_share", "map_wide_water_share",
    "map_coastal_towns", "map_town_tiles_max", "map_industries_primary", "map_industries_secondary",
    "map_power_stations", "map_town_river_cross_share", "map_town_river_run_max",
    "map_town_sea_cross_share", "map_town_climb_p90", "map_coal_river_run_max",
    "share_water_y10", "share_rail_y10", "share_air_y10", "profit_ratio_y10",
)


def cmd_select(args: argparse.Namespace) -> None:
    variant = None if args.no_control else args.variant_policy_id
    feats: dict[int, dict[str, float]] = {}
    if args.jsonl:
        feats = seed_features(load_rows(args.jsonl), args.reference_policy_id, variant)
    if args.maps:
        maps = load_maps(args.maps)
        feats = {s: {**maps[s], **feats[s]} for s in feats if s in maps} if args.jsonl else maps
    for s in args.exclude:
        feats.pop(s, None)
    if len(feats) < args.k:
        sys.exit(f"{len(feats)} graines completes seulement, moins que k={args.k}")
    names = sorted(n for n in next(iter(feats.values()))
                   if len({feats[s][n] for s in feats}) > 1 and not n.endswith(("_tiles", "_pairs")))
    z = standardize(feats, names)
    per_tail = max(1, int(round(args.k * args.tail / 2)))
    cover = [n for n in COVERAGE if n in names]
    quotas = tail_quotas(feats, cover, args.tail, per_tail)
    first, _ = coverage_seeds(quotas, per_tail, int(args.k * args.coverage_share))
    chosen = greedy_mmd(z, args.k, initial=first)
    unmet = sorted(key for key, members in quotas.items()
                   if sum(1 for s in chosen if s in members) < per_tail)
    population = sorted(feats)
    historic = [s for s in SEEDS_40 if s in feats]
    describe("population", feats, population, names)
    describe("selection", feats, chosen, names)
    if historic:
        describe("liste historique SEEDS_40 presente", feats, historic, names)
    print(f"\n== couverture des deciles extremes ({per_tail} graine(s) par queue, "
          f"{len(first)} graines de quotas puis {args.k - len(first)} par MMD)")
    for key, members in sorted(quotas.items()):
        got = sum(1 for s in chosen if s in members)
        old = sum(1 for s in historic if s in members)
        print(f"  {key[0]:32s} {key[1]:4s} selection {got:2d}   historique {old:2d}")
    if unmet:
        print("  quotas non remplis : " + ", ".join(f"{a}/{b}" for a, b in unmet))
    if variant is not None and args.jsonl:
        print("\n== controle de detection (variante - reference, profit_year)")
        for h in HORIZONS:
            n = f"control_delta_y{h}"
            for label, group in (("population", population), ("selection", chosen), ("historique", historic)):
                if not group:
                    continue
                v = [feats[s][n] for s in group]
                lo, hi = bootstrap_ci(v)
                print(f"  annee {h:2d} {label:11s} moy {statistics.fmean(v):>12.0f}  IC95 [{lo:.0f} ; {hi:.0f}]")
    print("\nSELECTION " + " ".join(str(s) for s in chosen))
    if args.out:
        Path(args.out).write_text(json.dumps({
            "k": args.k, "seeds": chosen, "coverage_seeds": first, "features": names,
            "coverage": [list(k) for k in sorted(quotas)], "unmet": [list(k) for k in unmet],
            "population": population}, indent=2) + "\n")
        print(f"-> {args.out}")
    if args.seeds_out:
        Path(args.seeds_out).write_text("\n".join(str(s) for s in chosen) + "\n")
        print(f"-> {args.seeds_out}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--count", type=int, required=True, help="taille totale, historiques compris")
    g.add_argument("--init", type=int, default=LCG_INIT)
    g.add_argument("--out", required=True)
    g.set_defaults(func=cmd_generate)
    c = sub.add_parser("command")
    c.add_argument("--seeds-file", required=True)
    c.add_argument("--campaign", required=True)
    c.add_argument("--years", type=int, default=HORIZONS[-1])
    c.add_argument("--chunks", type=int, default=1)
    c.add_argument("--limit", type=int, default=0, help="pilote : premieres graines seulement")
    c.add_argument("--offset", type=int, default=0, help="campagne principale : sauter les graines du pilote")
    c.add_argument("--reference", default=None, help=f"defaut : {CONTROL_REFERENCE} avec controle, defauts sinon")
    c.add_argument("--variant", default=CONTROL_VARIANT)
    c.add_argument("--variant-policy-id", default="v267_control")
    c.add_argument("--no-control", action="store_true", help="un seul bras (C66.3), cout divise par deux")
    c.set_defaults(func=cmd_command)
    s = sub.add_parser("select")
    s.add_argument("jsonl", nargs="*", help="campagnes jouees ; vide = cartes seules (--maps)")
    s.add_argument("--maps", nargs="*", default=[], help="JSONL de v267_maps.py screen")
    s.add_argument("--tail", type=float, default=0.1, help="taille de chaque decile extreme")
    s.add_argument("--coverage-share", type=float, default=0.6,
                   help="part maximale de k donnee aux quotas, le reste par MMD")
    s.add_argument("--exclude", type=int, nargs="*", default=[])
    s.add_argument("--seeds-out", help="liste de graines, une par ligne (population a jouer)")
    s.add_argument("--k", type=int, default=40)
    s.add_argument("--reference-policy-id", default="reference")
    s.add_argument("--variant-policy-id", default="v267_control")
    s.add_argument("--no-control", action="store_true")
    s.add_argument("--out")
    s.set_defaults(func=cmd_select)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
