#!/usr/bin/env python3
"""Experience naturelle : effet de l'arrivee d'un aeroport AAAHogEx dans la ville
d'un de nos aeroports sur le rendement de nos lignes AIR (reanalyse RVA, 19/10).

Lecture seule des cliches annuels `line_telemetry` (1er decembre). Unite : une
ligne AIR OpexAI identifiee par ses deux StationID dans une partie. Traitee en t
si AAA n'a aucun aeroport dans ses deux villes au cliche t-1 et en a un dans au
moins une au cliche t. Temoins de la meme partie et de la meme annee : aucune
presence AAA (aeroport) dans leurs villes de t-1 a t+1.

Effet = (delta traite) - (moyenne des deltas temoins de la meme partie-annee),
delta1 = ppv(t) - ppv(t-1), delta2 = ppv(t+1) - ppv(t-1), ppv = profit de l'annee
en cours au cliche / avions. IC95 bootstrap par partie (grappes).
Le profit au cliche de l'annee t melange les mois avant et apres l'arrivee :
delta2 est la mesure d'exposition complete.
"""
import argparse
import collections
import gzip
import json
import random
import statistics


def open_any(path):
    return gzip.open(path, "rt") if path.endswith(".gz") else open(path)


def cargo0(stat):
    c = (stat.get("cargo") or {}).get("0")
    return c if c and c.get("rated") else None


AIRPORT_CATCHMENT = {0: 4, 1: 5, 2: 4, 3: 6, 4: 8, 5: 4, 6: 4, 7: 10, 8: 4}  # table/airport_defaults.h
MAP_W = 256


def catchment_rect(st):
    ap = st.get("airport")
    if ap:
        x, y = ap["tile"] % MAP_W, ap["tile"] // MAP_W
        r = AIRPORT_CATCHMENT.get(ap.get("type"), 4)
        return (x - r, y - r, x + ap["width"] - 1 + r, y + ap["height"] - 1 + r)
    t = st.get("tile")
    if t is None:
        return None
    x, y = t % MAP_W, t // MAP_W
    return (x - 3, y - 3, x + 3, y + 3)  # tuile unique connue : borne basse (arret de bus)


def overlap_frac(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0]) + 1
    h = min(a[3], b[3]) - max(a[1], b[1]) + 1
    if w <= 0 or h <= 0:
        return 0.0
    return w * h / ((a[2] - a[0] + 1) * (a[3] - a[1] + 1))


def load(paths, aaa_scope):
    """games[gid] = {"opex": {year: {key: line}}, "aaa_air": {year: {town: maxrating}},
    "aaa_any": {year: set(town)}}"""
    games = collections.defaultdict(lambda: {"opex": collections.defaultdict(dict),
                                             "aaa_air": collections.defaultdict(dict),
                                             "aaa_any": collections.defaultdict(set),
                                             "aaa_rects": collections.defaultdict(dict)})
    for path in paths:
        with open_any(path) as f:
            for raw in f:
                if '"line_key_local"' not in raw:
                    continue
                d = json.loads(raw)
                lt = d.get("line_telemetry") or {}
                lines = lt.get("lines") or []
                if not lines:
                    continue
                gid = d["campaign_id"] + "|" + d["game_id"]
                year = int(d["date"][:4])
                g = games[gid]
                if d["company_slot"] == 1:
                    for ln in lines:
                        for st in ln.get("endpoint_cargo_stats") or []:
                            town = st.get("town_id")
                            c0 = cargo0(st)
                            if town is None or c0 is None:
                                continue
                            g["aaa_any"][year].add(town)
                            rect = catchment_rect(st)
                            if rect and (aaa_scope == "any" or st.get("airport")):
                                g["aaa_rects"][year][st["station_id"]] = rect
                            if st.get("airport"):
                                prev = g["aaa_air"][year].get(town, -1)
                                g["aaa_air"][year][town] = max(prev, c0["rating"])
                else:
                    for ln in lines:
                        if ln.get("mode") != "air" or not ln.get("vehicles"):
                            continue
                        key = tuple(sorted(ln["station_ids"]))
                        stats = {st["station_id"]: st for st in ln.get("endpoint_cargo_stats") or []}
                        g["opex"][year][key] = {
                            "towns": tuple(ln.get("endpoint_towns") or ln.get("town_ids") or []),
                            "veh": ln["vehicles"],
                            "profit": ln["profit_this_year_gbp"],
                            "rating": {stats[s]["town_id"]: (cargo0(stats[s]) or {}).get("rating")
                                       for s in stats if "town_id" in stats[s]},
                            "rects": {stats[s]["town_id"]: catchment_rect(stats[s])
                                      for s in stats if "town_id" in stats[s]},
                        }
    return games


def presence(g, year, aaa_scope):
    return set(g["aaa_air"][year]) if aaa_scope == "air" else g["aaa_any"][year]


def events(games, aaa_scope, min_year, require_prior, rows=None, placebo=0):
    out = []
    for gid, g in games.items():
        years = sorted(g["opex"])
        for t in years:
            if t - 1 < min_year or (t - 1) not in g["opex"]:
                continue
            p_prev, p_t = presence(g, t - 1, aaa_scope), presence(g, t, aaa_scope)
            p_next = presence(g, t + 1, aaa_scope) if (t + 1) in g["opex"] else None
            if placebo:
                # Placebo : periode t-1 -> t+1 encore NON exposee ; arrivee reelle en t+placebo.
                lead = t + placebo
                if lead not in g["opex"] or p_next is None:
                    continue
                p_lead = presence(g, lead, aaa_scope)
                quiet = p_prev | p_t | p_next
                p_t = {tw for tw in p_lead if tw not in quiet}
                p_next = p_next | presence(g, lead, aaa_scope)
                p_prev = p_prev | presence(g, t, aaa_scope) | presence(g, t + 1, aaa_scope)
            treated, controls = [], []
            for key, cur in g["opex"][t].items():
                prev = g["opex"][t - 1].get(key)
                if prev is None:
                    continue
                if require_prior and key not in g["opex"].get(t - 2, {}):
                    continue
                towns = cur["towns"]
                nxt = g["opex"].get(t + 1, {}).get(key)
                ppv = lambda x: x["profit"] / x["veh"]
                rec = {"key": key, "d1": ppv(cur) - ppv(prev),
                       "d2": (ppv(nxt) - ppv(prev)) if nxt else None,
                       "base": ppv(prev), "dveh1": cur["veh"] - prev["veh"],
                       "dveh2": (nxt["veh"] - prev["veh"]) if nxt else None}
                if any(tw in p_prev for tw in towns):
                    continue
                hit = [tw for tw in towns if tw in p_t]
                if hit:
                    tw = hit[0]
                    rec["town"] = tw
                    ro = cur["rating"].get(tw)
                    ra = g["aaa_air"][t].get(tw)
                    rec["r_opex"], rec["r_aaa"] = ro, ra
                    if ro is not None and ra is not None and ra >= 0:
                        rec["share_pred"] = (ro + 1) / (ro + ra + 2)
                    mine = cur["rects"].get(tw)
                    ya = t + 1 if (t + 1) in g["aaa_rects"] else t
                    rec["ovl"] = max([overlap_frac(mine, r) for r in g["aaa_rects"][ya].values()] or [0.0]) if mine else None
                    treated.append(rec)
                elif p_next is not None and not any(tw in p_t or tw in p_next for tw in towns):
                    controls.append(rec)
                else:
                    continue
                if rows is not None:
                    rows.append({"game": gid, "year": t, "treated": 1 if hit else 0,
                                 "ovl": rec.get("ovl") or 0.0,
                                 "pred": (rec.get("ovl") or 0.0) * (1 - rec.get("share_pred", 1.0)),
                                 "base": rec["base"], "d1": rec["d1"], "d2": rec["d2"],
                                 "dveh2": rec["dveh2"]})
            if not treated or len(controls) < 2:
                continue
            for k in ("d1", "d2"):
                cvals = [c[k] for c in controls if c[k] is not None]
                cbase = [c["base"] for c in controls]
                for tr in treated:
                    if tr[k] is None or len(cvals) < 2:
                        tr["eff_" + k] = None
                    else:
                        tr["eff_" + k] = tr[k] - statistics.mean(cvals)
                        tr["ctl_" + k] = statistics.mean(cvals)
            for tr in treated:
                tr["ctl_base"] = statistics.mean(cbase)
                tr["game"], tr["year"], tr["n_ctl"] = gid, t, len(controls)
                out.append(tr)
    return out


def solve(a, b):
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(m[r][c]))
        m[c], m[piv] = m[piv], m[c]
        if abs(m[c][c]) < 1e-12:
            return None
        for r in range(n):
            if r != c:
                f = m[r][c] / m[c][c]
                m[r] = [x - f * y for x, y in zip(m[r], m[c])]
    return [m[i][n] / m[i][i] for i in range(n)]


SPECS = {
    "treated": lambda r: [float(r["treated"])],
    "split": lambda r: [float(r["treated"] and r["ovl"] > 0), float(r["treated"] and r["ovl"] == 0)],
    "pred": lambda r: [float(r["treated"]), r["pred"]],
    "dose": lambda r: [float(r["treated"]), float(r["treated"]) * r["ovl"]],
}


def ols_treated(rows, field, years=None, spec="treated", which=0):
    """field ~ 1 + base + traitement(spec) + effets annee ; renvoie le coefficient `which`."""
    years = sorted({r["year"] for r in rows if r[field] is not None})
    xs, ys = [], []
    for r in rows:
        if r[field] is None:
            continue
        x = [1.0, r["base"] / 1000.0] + SPECS[spec](r)
        x += [1.0 if r["year"] == y else 0.0 for y in years[1:]]
        xs.append(x); ys.append(r[field])
    k = len(xs[0])
    xtx = [[sum(x[i] * x[j] for x in xs) for j in range(k)] for i in range(k)]
    xty = [sum(x[i] * y for x, y in zip(xs, ys)) for i in range(k)]
    beta = solve(xtx, xty)
    return None if beta is None else beta[2 + which]


def boot_ols(rows, field, n=1000, seed=2, spec="treated", which=0):
    years = sorted({r["year"] for r in rows})
    by = collections.defaultdict(list)
    for r in rows:
        by[r["game"]].append(r)
    gids = list(by)
    point = ols_treated(rows, field, years, spec, which)
    rnd = random.Random(seed)
    est = []
    for _ in range(n):
        s = [r for g in (rnd.choice(gids) for _ in gids) for r in by[g]]
        if not any(r["treated"] and r[field] is not None for r in s):
            continue
        b = ols_treated(s, field, years, spec, which)
        if b is not None:
            est.append(b)
    est.sort()
    if point is None or len(est) < 20:
        return None
    return {"coef_treated": point, "ci95": [est[int(0.025 * len(est))], est[int(0.975 * len(est))]],
            "n_rows": sum(r[field] is not None for r in rows),
            "n_treated": sum(r["treated"] and r[field] is not None for r in rows)}


def boot(evts, field, n=4000, seed=1):
    by = collections.defaultdict(list)
    for e in evts:
        if e.get(field) is not None:
            by[e["game"]].append(e[field])
    gids = list(by)
    if not gids:
        return None
    allv = [v for g in gids for v in by[g]]
    rnd = random.Random(seed)
    means = []
    for _ in range(n):
        s = [v for g in (rnd.choice(gids) for _ in gids) for v in by[g]]
        means.append(statistics.mean(s))
    means.sort()
    return {"n": len(allv), "games": len(gids), "mean": statistics.mean(allv),
            "median": statistics.median(allv),
            "ci95": [means[int(0.025 * n)], means[int(0.975 * n)]],
            "neg": sum(v < 0 for v in allv)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl", nargs="+")
    ap.add_argument("--aaa-scope", choices=["air", "any"], default="air")
    ap.add_argument("--min-year", type=int, default=1971)
    ap.add_argument("--require-prior", action="store_true")
    ap.add_argument("--dump")
    ap.add_argument("--placebo", type=int, default=0, help="arrivee reelle en t+N, N>=2")
    a = ap.parse_args()
    games = load(a.jsonl, a.aaa_scope)
    rows = []
    ev = events(games, a.aaa_scope, a.min_year, a.require_prior, rows, a.placebo)
    res = {"games_loaded": len(games), "events": len(ev)}
    res["ols_d1"] = boot_ols(rows, "d1")
    res["ols_d2"] = boot_ols(rows, "d2")
    res["ols_dveh2"] = boot_ols(rows, "dveh2")
    res["ols_d2_overlap"] = boot_ols(rows, "d2", spec="split", which=0)
    res["ols_d2_no_overlap"] = boot_ols(rows, "d2", spec="split", which=1)
    res["ols_d2_dose_slope"] = boot_ols(rows, "d2", spec="dose", which=1)
    res["ols_d2_pred_slope"] = boot_ols(rows, "d2", spec="pred", which=1)
    res["ols_d2_pred_intercept"] = boot_ols(rows, "d2", spec="pred", which=0)
    tr = [r for r in rows if r["treated"]]
    res["pred_loss_frac_median"] = statistics.median([r["pred"] for r in tr]) if tr else None
    res["treated_overlap_share"] = sum(r["ovl"] > 0 for r in tr) / len(tr) if tr else None
    res["treated_overlap_mean_if_pos"] = statistics.mean([r["ovl"] for r in tr if r["ovl"] > 0] or [0])
    res["ctl_base_all"] = statistics.mean(r["base"] for r in rows if not r["treated"])
    for f in ("eff_d1", "eff_d2", "d1", "d2", "base", "ctl_base", "dveh1", "dveh2"):
        res[f] = boot(ev, f)
    rel = [e["eff_d2"] / e["ctl_base"] for e in ev
           if e.get("eff_d2") is not None and e["ctl_base"] > 0]
    res["eff_d2_rel_ctl_base_median"] = statistics.median(rel) if rel else None
    sp = [e["share_pred"] for e in ev if "share_pred" in e]
    res["share_pred_median"] = statistics.median(sp) if sp else None
    res["by_year"] = {y: boot([e for e in ev if e["year"] == y], "eff_d2", n=500)
                      for y in sorted({e["year"] for e in ev})}
    print(json.dumps(res, indent=1))
    if a.dump:
        with open(a.dump, "w") as f:
            json.dump(ev, f, default=list)


if __name__ == "__main__":
    main()
