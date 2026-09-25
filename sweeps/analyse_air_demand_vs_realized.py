"""Predit contre realise pour les lignes aeriennes OpexAI.

Lit les sorties JSON/JSONL des harnais existants : paires C78_AIRPAIR admises
(paxOld / paxNew si V93.1, P = profit predit), constructions C78_BUILD, traces
LINE_PROFIT si elles sont la, et lignes realisees des snapshots
diag_c78_lines_vs_aaa (companies[..].lines : towns, vehicles, profit_last_year).

Les identifiants de ville des sauvegardes valent l'identifiant API plus un.
Le harnais a deja soustrait 1 : ce script utilise `towns`, pas `towns_raw`,
et ne soustrait rien une seconde fois.

Deux modeles : le proxy de population (pas de paxNew) et la production V93.1
(paxNew present, P calcule avec ce chiffre). Le profit P d'une ligne admise
n'appartient qu'au modele qui l'a produit.
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from analyse_c78_etape2 import get_candidate_pair, get_line_pair, get_town_pool_info
from analyse_v86_cannibalisation import parse_c56_log_line
from diag_c78_lines_vs_aaa import parse_c78_logs

OPEX_COMPANY = "0"
BANDS = ("<600", "600-1500", ">1500", "inconnu")


def median(values):
    vals = sorted(v for v in values if v is not None)
    n = len(vals)
    if n == 0:
        return None
    mid = n // 2
    if n % 2:
        return vals[mid]
    return (vals[mid - 1] + vals[mid]) / 2.0


def mean(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    return sum(vals) / float(len(vals))


def as_number(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def pop_band(pop):
    if pop is None:
        return "inconnu"
    if pop < 600:
        return "<600"
    if pop <= 1500:
        return "600-1500"
    return ">1500"


def pair_population_band(pop_a, pop_b):
    if pop_a is None or pop_b is None:
        return "inconnu"
    return pop_band(min(pop_a, pop_b))


def empty_bundle():
    return {
        "snapshots": [],
        "admitted": [],
        "builds": [],
        "line_profits": [],
        "files": [],
        "missing_files": [],
        "parse_notes": [],
    }


def _seed_of(record, default=None):
    if not isinstance(record, dict):
        return default
    seed = record.get("seed", record.get("experiment_seed", default))
    if isinstance(seed, dict):
        seed = seed.get("seed", default)
    return seed


def _extend_parsed_logs(bundle, parsed, seed):
    for year, rows in (parsed.get("airpairs") or {}).items():
        for row in rows:
            if row.get("outcome") != "admitted":
                continue
            item = dict(row)
            item["year"] = item.get("year", year)
            item["seed"] = seed
            item["source"] = "log"
            bundle["admitted"].append(item)
    for year, rows in (parsed.get("builds") or {}).items():
        for row in rows:
            item = dict(row)
            item["year"] = item.get("year", year)
            item["seed"] = seed
            bundle["builds"].append(item)
    for year, pool in (parsed.get("airpool") or {}).items():
        bundle["snapshots"].append({
            "seed": seed,
            "year": year,
            "airpool": pool,
            "companies": {},
            "airpairs": [],
            "builds": [],
            "_pool_only": True,
        })


def _ingest_text(bundle, text, seed):
    if not text:
        return
    if "C78_" in text:
        _extend_parsed_logs(bundle, parse_c78_logs(text), seed)
    for line in text.splitlines():
        if "C56_TASK" not in line or "LINE_PROFIT" not in line:
            continue
        parsed = parse_c56_log_line(line)
        if not parsed or parsed.get("kind") != "LINE_PROFIT":
            continue
        fields = parsed.get("fields") or {}
        bundle["line_profits"].append({
            "seed": seed,
            "year": as_number(fields.get("year")),
            "profit": as_number(fields.get("profit")),
            "stA": as_number(fields.get("stA")),
            "stB": as_number(fields.get("stB")),
            "pax": as_number(fields.get("pax", fields.get("carried", fields.get("delivered")))),
            "line_id": fields.get("name", fields.get("line")),
        })


def _ingest_record(bundle, record, seed_hint=None):
    if isinstance(record, str):
        _ingest_text(bundle, record, seed_hint)
        return
    if not isinstance(record, dict):
        bundle["parse_notes"].append("enregistrement ignore (ni objet ni texte)")
        return
    seed = _seed_of(record, seed_hint)
    text = record.get("grep") or record.get("output") or record.get("log") or record.get("text") or record.get("_raw")
    if isinstance(text, str) and ("C78_" in text or "LINE_PROFIT" in text or "C56_TASK" in text):
        _ingest_text(bundle, text, seed)
    looks_like_snapshot = any(key in record for key in ("companies", "airpairs", "airpool", "builds"))
    if looks_like_snapshot and not record.get("_raw"):
        snap = dict(record)
        snap["seed"] = seed
        bundle["snapshots"].append(snap)
        for row in snap.get("airpairs") or []:
            if not isinstance(row, dict) or row.get("outcome") != "admitted":
                continue
            item = dict(row)
            item["seed"] = seed
            item["year"] = item.get("year", snap.get("year"))
            item["source"] = "snapshot"
            bundle["admitted"].append(item)
        for row in snap.get("builds") or []:
            if not isinstance(row, dict):
                continue
            item = dict(row)
            item["seed"] = seed
            item["year"] = item.get("year", snap.get("year"))
            bundle["builds"].append(item)


def iter_records(path):
    text = path.read_text(encoding="utf-8")
    stripped = text.lstrip()
    if not stripped:
        return
    if stripped[0] == "[":
        data = json.loads(text)
        if isinstance(data, list):
            for item in data:
                yield item
            return
    if stripped[0] == "{":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            rows = data.get("snapshots") or data.get("rows") or data.get("results")
            if isinstance(rows, list):
                for item in rows:
                    yield item
                return
            yield data
            return
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line[0] == "{":
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                yield line
        else:
            yield line


def load_paths(paths):
    bundle = empty_bundle()
    for raw in paths:
        path = Path(raw)
        bundle["files"].append(str(path))
        if not path.is_file():
            bundle["missing_files"].append(str(path))
            continue
        try:
            for record in iter_records(path):
                _ingest_record(bundle, record)
        except (OSError, json.JSONDecodeError) as exc:
            bundle["parse_notes"].append(f"{path.name}: {exc}")
    return bundle


def _dedupe_admitted(rows):
    seen = set()
    out = []
    for row in rows:
        pair = get_candidate_pair(row)
        if len(pair) != 2:
            continue
        key = (
            row.get("seed"), pair, row.get("year"), row.get("arm"),
            row.get("P"), row.get("paxOld"), row.get("paxNew"),
        )
        if key in seen:
            continue
        seen.add(key)
        item = dict(row)
        item["pair"] = pair
        out.append(item)
    return out


def _model_of(row):
    if "paxNew" in row and row.get("paxNew") is not None:
        return "production"
    return "old_proxy"


def _predicted_pax(row, model):
    if model == "production":
        return as_number(row.get("paxNew"))
    return as_number(row.get("paxOld"))


def _town_pop(airpools, town_id):
    for pool in airpools:
        info = get_town_pool_info(pool, town_id)
        if not info or len(info) < 2:
            continue
        pop = as_number(info[1])
        if pop is not None:
            return pop
    return None


def _line_station_ids(line):
    ids = []
    for key in ("station_ids", "stations"):
        raw = line.get(key)
        if isinstance(raw, list):
            for value in raw:
                num = as_number(value)
                if num is not None:
                    ids.append(int(num))
    return ids


def _line_pax(line):
    for key in ("passengers", "pax", "pax_last_year", "delivered", "delivered_pax", "carried"):
        num = as_number(line.get(key))
        if num is not None:
            return num
    return None


def _line_revenue(line):
    for key in ("revenue_last_year", "revenue", "income_last_year"):
        num = as_number(line.get(key))
        if num is not None:
            return num
    return None


def _predicted_revenue(row):
    for key in ("R", "rev", "revenue", "revenueAnnual"):
        num = as_number(row.get(key))
        if num is not None:
            return num
    return None


def _airport_degree(lines, line):
    """Degre max des aeroports de la ligne : tuiles de gare si elles existent, sinon villes."""
    tiles_ok = bool(line.get("tiles")) and all(other.get("tiles") for other in lines)
    if tiles_ok:
        counts = defaultdict(int)
        for other in lines:
            for tile in set(other.get("tiles") or []):
                if tile is not None:
                    counts[tile] += 1
        degrees = [counts[tile] for tile in set(line.get("tiles") or []) if tile in counts]
        if degrees:
            return max(degrees), "tuile"
    counts = defaultdict(int)
    for other in lines:
        pair = get_line_pair(other)
        if len(pair) != 2:
            continue
        for town in set(pair):
            counts[town] += 1
    pair = get_line_pair(line)
    if len(pair) != 2:
        return None, "ville"
    degrees = [counts[town] for town in set(pair) if town in counts]
    if not degrees:
        return None, "ville"
    return max(degrees), "ville"


def _choose_prediction(rows, first_year):
    if not rows:
        return None
    eligible = []
    if first_year is not None:
        eligible = [row for row in rows if as_number(row.get("year")) is not None
                    and as_number(row.get("year")) <= first_year]
    pool = eligible or rows
    def sort_key(row):
        year = as_number(row.get("year"))
        return (year if year is not None else -1, rows.index(row))
    return max(pool, key=sort_key)


def _snapshot_lines(snapshot):
    companies = snapshot.get("companies") or {}
    if isinstance(companies, list):
        companies = {str(i): item for i, item in enumerate(companies)}
    company = companies.get(OPEX_COMPANY) or companies.get(0) or {}
    if not isinstance(company, dict):
        return []
    return [line for line in (company.get("lines") or []) if isinstance(line, dict)]


def build_observations(bundle):
    admitted = _dedupe_admitted(bundle["admitted"])
    by_key = defaultdict(list)
    for row in admitted:
        by_key[(row.get("seed"), row["pair"], _model_of(row))].append(row)

    airpools = defaultdict(list)
    realized = defaultdict(list)
    degree_basis_counts = defaultdict(int)
    for snap in bundle["snapshots"]:
        if snap.get("_pool_only"):
            pool = snap.get("airpool") or {}
            if pool:
                airpools[snap.get("seed")].append(pool)
            continue
        seed = snap.get("seed")
        year = as_number(snap.get("year"))
        pool = snap.get("airpool") or {}
        if pool:
            airpools[seed].append(pool)
        air_lines = [line for line in _snapshot_lines(snap) if line.get("mode") == "air"]
        for line in air_lines:
            pair = get_line_pair(line)
            if len(pair) != 2:
                continue
            degree, basis = _airport_degree(air_lines, line)
            degree_basis_counts[basis] += 1
            realized[(seed, pair)].append({
                "year": year,
                "profit": as_number(line.get("profit_last_year")),
                "vehicles": line.get("vehicles"),
                "pax": _line_pax(line),
                "revenue": _line_revenue(line),
                "degree": degree,
                "degree_basis": basis,
                "station_ids": _line_station_ids(line),
            })

    line_profit_by_stations = defaultdict(list)
    for row in bundle["line_profits"]:
        sta, stb = row.get("stA"), row.get("stB")
        if sta is None or stb is None:
            continue
        key = (row.get("seed"), tuple(sorted((int(sta), int(stb)))))
        line_profit_by_stations[key].append(row)

    builds_by_pair = defaultdict(list)
    for row in bundle["builds"]:
        if row.get("mode") not in (None, "air"):
            continue
        if row.get("outcome") not in (None, "built"):
            continue
        pair = get_candidate_pair(row)
        if len(pair) != 2:
            continue
        builds_by_pair[(row.get("seed"), pair)].append(as_number(row.get("year")))

    observations = []
    matched_pairs = set()
    for (seed, pair), samples in realized.items():
        years = [sample["year"] for sample in samples if sample["year"] is not None]
        first_year = min(years) if years else None
        latest = max(samples, key=lambda sample: (sample["year"] is not None, sample["year"] or -1))
        profits = [sample["profit"] for sample in samples if sample["profit"] is not None]
        pax_values = [sample["pax"] for sample in samples if sample["pax"] is not None]
        revenues = [sample["revenue"] for sample in samples if sample["revenue"] is not None]
        station_key = None
        if latest["station_ids"] and len(latest["station_ids"]) >= 2:
            station_key = (seed, tuple(sorted(latest["station_ids"][:2])))
        joined_lp = line_profit_by_stations.get(station_key, []) if station_key else []
        lp_profits = [row["profit"] for row in joined_lp if row.get("profit") is not None]
        lp_pax = [row["pax"] for row in joined_lp if row.get("pax") is not None]
        pop_a = _town_pop(airpools.get(seed, []), pair[0])
        pop_b = _town_pop(airpools.get(seed, []), pair[1])
        build_years = [year for year in builds_by_pair.get((seed, pair), []) if year is not None]
        anchor_year = min(build_years) if build_years else first_year
        for model in ("old_proxy", "production"):
            preds = by_key.get((seed, pair, model)) or []
            if not preds:
                continue
            chosen = _choose_prediction(preds, anchor_year)
            predicted_profit = as_number(chosen.get("P"))
            predicted_pax = _predicted_pax(chosen, model)
            predicted_revenue = _predicted_revenue(chosen)
            realized_profit = median(profits) if profits else (median(lp_profits) if lp_profits else None)
            realized_pax = median(pax_values) if pax_values else (median(lp_pax) if lp_pax else None)
            realized_revenue = median(revenues) if revenues else None
            observations.append({
                "seed": seed,
                "pair": list(pair),
                "model": model,
                "population_band": pair_population_band(pop_a, pop_b),
                "pop_min": None if pop_a is None or pop_b is None else min(pop_a, pop_b),
                "airport_degree": latest["degree"],
                "degree_basis": latest["degree_basis"],
                "predicted_profit": predicted_profit,
                "predicted_pax": predicted_pax,
                "predicted_pax_old": as_number(chosen.get("paxOld")),
                "predicted_revenue": predicted_revenue,
                "realized_profit": realized_profit,
                "realized_pax": realized_pax,
                "realized_revenue": realized_revenue,
                "profit_ratio": _ratio(realized_profit, predicted_profit),
                "pax_ratio": _ratio(realized_pax, predicted_pax),
                "revenue_ratio": _ratio(realized_revenue, predicted_revenue),
                "profit_source": "snapshot" if profits else ("line_profit" if lp_profits else None),
                "line_profit_joined": bool(joined_lp),
                "admitted_year": chosen.get("year"),
                "vehicles": latest.get("vehicles"),
            })
            matched_pairs.add((seed, pair, model))

    unmatched_predictions = 0
    for key, rows in by_key.items():
        if key not in matched_pairs and rows:
            unmatched_predictions += len(rows)
    return {
        "observations": observations,
        "unmatched_predictions": unmatched_predictions,
        "degree_basis_counts": dict(degree_basis_counts),
        "admitted_n": len(admitted),
    }


def _ratio(realized, predicted):
    if realized is None or predicted is None or predicted == 0:
        return None
    return realized / float(predicted)


def _group_stats(rows):
    # Le facteur est la mediane des ratios a profit predit strictement positif.
    positive_profit = [row["profit_ratio"] for row in rows
                       if row["profit_ratio"] is not None and (row["predicted_profit"] or 0) > 0]
    positive_pax = [row["pax_ratio"] for row in rows
                    if row["pax_ratio"] is not None and (row["predicted_pax"] or 0) > 0]
    positive_revenue = [row["revenue_ratio"] for row in rows
                        if row["revenue_ratio"] is not None and (row["predicted_revenue"] or 0) > 0]
    by_band = {}
    for band in BANDS:
        subset = [row for row in rows if row["population_band"] == band]
        if not subset:
            continue
        by_band[band] = _compact(subset)
    by_degree = {}
    degrees = sorted({row["airport_degree"] for row in rows if row["airport_degree"] is not None})
    for degree in degrees:
        subset = [row for row in rows if row["airport_degree"] == degree]
        by_degree[str(int(degree))] = _compact(subset)
    return {
        "n": len(rows),
        "profit_ratio_median": median(positive_profit),
        "profit_ratio_mean": mean(positive_profit),
        "pax_ratio_median": median(positive_pax),
        "pax_ratio_mean": mean(positive_pax),
        "n_profit": len(positive_profit),
        "n_pax": len(positive_pax),
        "n_revenue": len(positive_revenue),
        "calibration_factor_profit": median(positive_profit),
        "calibration_factor_revenue": median(positive_revenue),
        "calibration_factor_pax": median(positive_pax),
        "by_population_band": by_band,
        "by_airport_degree": by_degree,
    }


def _compact(rows):
    ratios = [row["profit_ratio"] for row in rows
              if row["profit_ratio"] is not None and (row["predicted_profit"] or 0) > 0]
    pax = [row["pax_ratio"] for row in rows
           if row["pax_ratio"] is not None and (row["predicted_pax"] or 0) > 0]
    return {
        "n": len(rows),
        "n_profit": len(ratios),
        "profit_ratio_median": median(ratios),
        "profit_ratio_mean": mean(ratios),
        "n_pax": len(pax),
        "pax_ratio_median": median(pax),
        "pax_ratio_mean": mean(pax),
    }


def missing_inputs(bundle, built):
    missing = []
    if bundle["missing_files"]:
        missing.append("fichiers")
    if not bundle["files"]:
        missing.append("entrees")
    if built["admitted_n"] == 0:
        missing.append("C78_AIRPAIR admises")
    if not any(row.get("outcome") == "built" or row.get("mode") == "air" for row in bundle["builds"]):
        missing.append("C78_BUILD")
    if not bundle["line_profits"]:
        missing.append("LINE_PROFIT")
    real_snaps = [snap for snap in bundle["snapshots"] if not snap.get("_pool_only")]
    air_lines = 0
    for snap in real_snaps:
        air_lines += sum(1 for line in _snapshot_lines(snap) if line.get("mode") == "air")
    if air_lines == 0:
        missing.append("lignes realisees (companies)")
    pops = False
    for snap in bundle["snapshots"]:
        pool = snap.get("airpool") or {}
        towns = pool.get("towns") or {}
        if towns:
            pops = True
            break
    if not pops:
        missing.append("populations (C78_AIRPOOL)")
    has_pax_old = any("paxOld" in row and row.get("paxOld") is not None for row in bundle["admitted"])
    has_pax_new = any("paxNew" in row and row.get("paxNew") is not None for row in bundle["admitted"])
    if not has_pax_old and not has_pax_new:
        missing.append("pax predit (paxOld/paxNew)")
    elif not has_pax_new:
        missing.append("paxNew (modele production)")
    elif not has_pax_old:
        missing.append("paxOld")
    has_realized_pax = any(obs.get("realized_pax") is not None for obs in built["observations"])
    if not has_realized_pax:
        missing.append("passagers realises")
    has_revenue = any(obs.get("revenue_ratio") is not None for obs in built["observations"])
    if not has_revenue:
        missing.append("revenu (predit et realise)")
    joined = any(obs.get("line_profit_joined") for obs in built["observations"])
    if bundle["line_profits"] and not joined:
        missing.append("LINE_PROFIT relie aux villes (pas d'identifiant de gare commun)")
    return missing


def analyse_bundle(bundle):
    built = build_observations(bundle)
    models = {}
    for name in ("old_proxy", "production"):
        rows = [row for row in built["observations"] if row["model"] == name]
        models[name] = _group_stats(rows)
    report = {
        "files": list(bundle["files"]),
        "missing_files": list(bundle["missing_files"]),
        "parse_notes": list(bundle["parse_notes"]),
        "missing_inputs": missing_inputs(bundle, built),
        "counts": {
            "admitted": built["admitted_n"],
            "builds": len(bundle["builds"]),
            "snapshots": sum(1 for snap in bundle["snapshots"] if not snap.get("_pool_only")),
            "line_profit": len(bundle["line_profits"]),
            "observations": len(built["observations"]),
            "unmatched_predictions": built["unmatched_predictions"],
        },
        "town_ids": "api",
        "town_id_note": (
            "Les snapshots du harnais ont deja soustrait 1 "
            "(identifiant sauvegarde = identifiant API + 1). Pas de seconde correction."
        ),
        "opex_company": OPEX_COMPANY,
        "degree_basis_counts": built["degree_basis_counts"],
        "models": models,
        "observations": built["observations"],
        "calibration_note": (
            "calibration_factor_profit est la mediane realise/predit sur les profits "
            "predits strictement positifs : multiplier le profit predit par ce facteur "
            "rend la mediane du ratio egale a 1. calibration_factor_revenue est le meme "
            "calcul sur le revenu, et reste nul si les entrees n'ont ni revenu predit ni "
            "revenu realise. calibration_factor_pax est le facteur qui recentrerait un "
            "revenu proportionnel aux passagers, a tarif constant."
        ),
    }
    return report


def analyse_paths(paths):
    return analyse_bundle(load_paths(paths))


def _fmt(value):
    if value is None:
        return "n/d"
    return f"{value:.3f}"


def _fmt_group(title, stats):
    lines = [
        f"{title} : {stats['n']} ligne(s), ratios de profit n={stats['n_profit']} "
        f"médiane {_fmt(stats['profit_ratio_median'])} moyenne {_fmt(stats['profit_ratio_mean'])} ; "
        f"passagers n={stats['n_pax']} médiane {_fmt(stats['pax_ratio_median'])} "
        f"moyenne {_fmt(stats['pax_ratio_mean'])}."
    ]
    if stats["by_population_band"]:
        lines.append("  Bandes de population (plus petite ville de la paire) :")
        for band, group in stats["by_population_band"].items():
            lines.append(
                f"    {band} : n={group['n_profit']} médiane {_fmt(group['profit_ratio_median'])} "
                f"moyenne {_fmt(group['profit_ratio_mean'])}"
            )
    if stats["by_airport_degree"]:
        lines.append("  Degré d'aéroport (nombre de lignes OpexAI sur l'aéroport) :")
        for degree, group in stats["by_airport_degree"].items():
            lines.append(
                f"    degré {degree} : n={group['n_profit']} médiane {_fmt(group['profit_ratio_median'])} "
                f"moyenne {_fmt(group['profit_ratio_mean'])}"
            )
    lines.append(
        "  Facteur de calibration du profit : "
        f"{_fmt(stats['calibration_factor_profit'])}. "
        "Facteur de calibration du revenu : "
        f"{_fmt(stats['calibration_factor_revenue'])}. "
        "Facteur passagers : "
        f"{_fmt(stats['calibration_factor_pax'])}."
    )
    return lines


def french_summary(report):
    counts = report["counts"]
    lines = [
        "Demande aérienne : profit et passagers prédits contre réalisés.",
        (
            f"Lu : {len(report['files'])} fichier(s), "
            f"{counts['admitted']} paire(s) admise(s), {counts['builds']} construction(s), "
            f"{counts['snapshots']} snapshot(s), {counts['line_profit']} trace(s) LINE_PROFIT, "
            f"{counts['observations']} ligne(s) jointe(s)."
        ),
        "Compagnie OpexAI : clé " + str(report["opex_company"]) + " des snapshots du harnais.",
        report["town_id_note"],
    ]
    if report["missing_inputs"]:
        lines.append("Entrées manquantes : " + ", ".join(report["missing_inputs"]) + ".")
    else:
        lines.append("Entrées manquantes : aucune.")
    if report["missing_files"]:
        lines.append("Fichiers absents : " + ", ".join(report["missing_files"]) + ".")
    if report["parse_notes"]:
        lines.append("Notes de lecture : " + " ; ".join(report["parse_notes"]) + ".")
    lines.extend(_fmt_group("Modèle proxy de population (ancien)", report["models"]["old_proxy"]))
    lines.extend(_fmt_group("Modèle production (V93.1, paxNew)", report["models"]["production"]))
    lines.append(report["calibration_note"])
    if counts["unmatched_predictions"]:
        lines.append(
            f"Paires admises sans ligne réalisée jointe : {counts['unmatched_predictions']}."
        )
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="*", help="JSON ou JSONL de harnais (C78, snapshots, LINE_PROFIT)")
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "analyse_air_demand_vs_realized.json")
    args = parser.parse_args(argv)
    report = analyse_paths(args.inputs)
    text = french_summary(report)
    print(text)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"JSON : {args.out}")
    return report


if __name__ == "__main__":
    main()
