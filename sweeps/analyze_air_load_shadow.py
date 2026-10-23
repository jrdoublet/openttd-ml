#!/usr/bin/env python3
"""Analyse passive hebdomadaire des journaux AIR_LOAD7 d'OpexAI.

Contrat moteur (champs ASCII `cle=valeur`, un cliché par ligne et semaine) :

    AIR_LOAD7 date=722000 line=12 fleet=3 dist=150 neighbors=2 target=4
    last_profit=26000 running=2 station_a=40 station_b=41
    airport_a=small airport_b=large a_pass_rating=80 a_pass_wait=120
    b_pass_rating=66 b_pass_wait=40 a_mail_rating=70 a_mail_wait=12
    b_mail_rating=62 b_mail_wait=0
    flights=a:70:100:100:24;b:90:100:300:24;?:20:50:70:30

`flights=-` signifie aucun avion en vol. a/b désigne la gare de destination ;
? est une destination inconnue. Un tuple donne destination:charge:capacite:
age_en_jours:modele. Ratings -1 : indisponible ; stock -1 : indisponible.
`reinforce=<date_en_jours>` est facultatif ; une hausse de `fleet` suffit pour
repérer un renfort probable. Les fichiers/campagnes restent indépendants.

Exemples :
    python sweeps/analyze_air_load_shadow.py "results/**/*.log"
    python sweeps/analyze_air_load_shadow.py results/air.log --format markdown

Il s'agit de corrélations et de diagnostics descriptifs ; ni les sondes, ni les
renforts observés ne prouvent un effet économique causal.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import glob
import json
import math
from pathlib import Path
import re
import statistics


TAG = re.compile(r"(?<![\w])AIR_LOAD7\b")
FIELD = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*)=([^\s]+)")
STATIONS = ("a", "b")
CARGOS = ("pass", "mail")
DIRECTIONS = ("a", "b", "?")
BANDS = ("0-24%", "25-49%", "50-74%", "75-89%", "90-100%", ">100%")


def number(value, *, integer=False, nonnegative=False):
    """Convertir les sentinelles négatives en None sans accepter NaN ou inf."""
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    if not math.isfinite(result) or (nonnegative and result < 0):
        return None
    if integer:
        return int(result) if result.is_integer() else None
    return result


def _quantile(values, fraction):
    ordered = sorted(values)
    if not ordered:
        return None
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _average(values):
    values = [v for v in values if v is not None]
    return statistics.mean(values) if values else None


def _diff(before, after):
    return after - before if before is not None and after is not None else None


def parse_flights(encoded):
    """Décodage du format compact, avec anomalies locales récupérables."""
    if encoded == "-":
        return [], []
    flights = []
    errors = []
    for item in encoded.split(";"):
        parts = item.split(":")
        if len(parts) != 5 or parts[0] not in DIRECTIONS:
            errors.append(f"invalid_flight:{item}")
            continue
        direction, raw_load, raw_cap, raw_age, model = parts
        load = number(raw_load, integer=True, nonnegative=True)
        cap = number(raw_cap, integer=True, nonnegative=True)
        age = number(raw_age, integer=True, nonnegative=True)
        if load is None or cap is None or cap <= 0 or load > cap:
            errors.append(f"invalid_load_capacity:{item}")
            continue
        flights.append({
            "direction": direction,
            "load": load,
            "capacity": cap,
            "occupancy": load / cap,
            "age_days": age,
            "model": model if model != "-1" else None,
        })
    return flights, errors


def parse_log(lines, source="<stream>"):
    """Retourne (clichés, compteurs, erreurs) à partir de vraies lignes AILog.

    Une duplication exacte date×ligne n'est comptée qu'une fois ; deux clichés
    incompatibles avec les mêmes clés sont tous deux exclus de l'analyse.
    """
    snapshots = {}
    conflicts = set()
    counts = Counter()
    issues = []

    def flag(line_number, reason):
        counts["parse_issues"] += 1
        counts[reason.split(":", 1)[0]] += 1
        if len(issues) < 30:
            issues.append({"source": source, "log_line": line_number, "reason": reason})

    for log_line, text in enumerate(lines, 1):
        found = TAG.search(text)
        if not found:
            continue
        counts["tagged_records"] += 1
        tokens = FIELD.findall(text[found.end():])
        fields = dict(tokens)
        if len(tokens) != len(fields):
            flag(log_line, "duplicate_field")
            continue
        day = number(fields.get("date"), integer=True, nonnegative=True)
        line = fields.get("line")
        fleet = number(fields.get("fleet"), integer=True, nonnegative=True)
        if day is None or not line or fleet is None or "flights" not in fields:
            flag(log_line, "missing_or_invalid_required_field")
            continue
        flights, errors = parse_flights(fields["flights"])
        for error in errors:
            flag(log_line, error)
        if errors:
            # Une liste tronquée/partiellement corrompue biaiserait la charge
            # hebdomadaire : conserver le cliché de station, exclure ses vols.
            counts["snapshots_with_bad_flights"] += 1
            flights = []
        stations = {}
        for station in STATIONS:
            stations[station] = {
                "id": fields.get("station_" + station),
                "airport": fields.get("airport_" + station),
            }
            for cargo in CARGOS:
                key = station + "_" + cargo
                rating = number(fields.get(key + "_rating"), integer=True,
                                nonnegative=True)
                stations[station][cargo] = {
                    "rating": rating if rating is not None and rating <= 100 else None,
                    "stock": number(fields.get(key + "_wait"), integer=True,
                                    nonnegative=True),
                }
        row = {
            "source": source,
            "date": day,
            "line": line,
            "fleet": fleet,
            "dist": number(fields.get("dist"), integer=True, nonnegative=True),
            "neighbors": number(fields.get("neighbors"), integer=True, nonnegative=True),
            "target": number(fields.get("target"), integer=True, nonnegative=True),
            "running": number(fields.get("running"), integer=True, nonnegative=True),
            "observed": number(fields.get("observed"), integer=True, nonnegative=True),
            "last_profit": (number(fields.get("last_profit"))
                            if fields.get("last_profit") != "-1" else None),
            "reinforce": number(fields.get("reinforce"), integer=True, nonnegative=True),
            "stations": stations,
            "flights": flights,
            "flight_data_complete": not errors,
        }
        key = (line, day)
        if key in conflicts:
            counts["conflicting_duplicates"] += 1
            continue
        if key in snapshots:
            if snapshots[key] == row:
                counts["identical_duplicates"] += 1
            else:
                counts["conflicting_duplicates"] += 1
                flag(log_line, "conflicting_duplicate_line_date")
                conflicts.add(key)
                del snapshots[key]
            continue
        snapshots[key] = row
    rows = sorted(snapshots.values(), key=lambda x: (x["line"], x["date"]))
    counts["valid_snapshots"] = len(rows)
    counts["flights_decoded"] = sum(len(row["flights"]) for row in rows)
    return rows, dict(counts), issues


def occupancy_band(ratio):
    if ratio < 0.25:
        return BANDS[0]
    if ratio < 0.50:
        return BANDS[1]
    if ratio < 0.75:
        return BANDS[2]
    if ratio < 0.90:
        return BANDS[3]
    if ratio <= 1:
        return BANDS[4]
    return BANDS[5]


def occupancy_stats(flights):
    flights = list(flights)
    ratios = [f["occupancy"] for f in flights]
    capacity = sum(f["capacity"] for f in flights)
    return {
        "flights": len(flights),
        "load_total": sum(f["load"] for f in flights),
        "capacity_total": capacity,
        "mean": _average(ratios),
        "capacity_weighted": sum(f["load"] for f in flights) / capacity if capacity else None,
        "p10": _quantile(ratios, .10),
        "p25": _quantile(ratios, .25),
        "median": _quantile(ratios, .50),
        "p75": _quantile(ratios, .75),
        "p90": _quantile(ratios, .90),
        "min": min(ratios) if ratios else None,
        "max": max(ratios) if ratios else None,
        "histogram": {band: sum(occupancy_band(r) == band for r in ratios)
                      for band in BANDS},
        "age_days_mean": _average([f["age_days"] for f in flights]),
        "models": dict(sorted(Counter(str(f["model"]) for f in flights
                                      if f["model"] is not None).items())),
    }


def pearson(xs, ys):
    """Corrélation descriptive ; minimum trois couples et variance non nulle."""
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    n = len(pairs)
    if n < 3:
        return {"n": n, "r": None}
    xavg = statistics.mean(x for x, _ in pairs)
    yavg = statistics.mean(y for _, y in pairs)
    xx = sum((x - xavg) ** 2 for x, _ in pairs)
    yy = sum((y - yavg) ** 2 for _, y in pairs)
    if xx == 0 or yy == 0:
        return {"n": n, "r": None}
    return {"n": n, "r": sum((x - xavg) * (y - yavg) for x, y in pairs)
            / math.sqrt(xx * yy)}


def stock_slope_per_week(points):
    """Pente OLS (unités de stock par 7 jours de jeu)."""
    points = [(day, stock) for day, stock in points if stock is not None]
    if len(points) < 3 or max(day for day, _ in points) - min(day for day, _ in points) < 14:
        return None
    day_mean = statistics.mean(day for day, _ in points)
    stock_mean = statistics.mean(stock for _, stock in points)
    variance = sum((day - day_mean) ** 2 for day, _ in points)
    return (7 * sum((day - day_mean) * (stock - stock_mean)
                    for day, stock in points) / variance) if variance else None


def _direction_flights(row, direction):
    return [flight for flight in row["flights"] if flight["direction"] == direction]


def _weekly_rate(row, direction=None):
    flights = row["flights"] if direction is None else _direction_flights(row, direction)
    cap = sum(f["capacity"] for f in flights)
    return sum(f["load"] for f in flights) / cap if cap else None


def station_diagnostics(rows, *, high_load=.85, low_load=.35,
                        min_pressure_samples=3, stock_rise_week=0):
    """Corrélations et pression par destination, sur couples semaine×ligne."""
    result = {}
    for dest in STATIONS:
        for cargo in CARGOS:
            key = dest + "_" + cargo
            # Une semaine sans avion observé vers la gare reste utilisable pour
            # rating/stock, mais jamais comme zéro de taux de remplissage.
            samples = [
                {"date": row["date"], "load": _weekly_rate(row, dest),
                 "loaded": sum(f["load"] for f in _direction_flights(row, dest)),
                 "capacity": sum(f["capacity"] for f in _direction_flights(row, dest)),
                 "rating": row["stations"][dest][cargo]["rating"],
                 "stock": row["stations"][dest][cargo]["stock"]}
                for row in rows
            ]
            linked = [s for s in samples if s["load"] is not None and s["stock"] is not None]
            slope = stock_slope_per_week([(s["date"], s["stock"]) for s in samples
                                          if s["stock"] is not None])
            mean_rate = _average(s["load"] for s in linked)
            weighted_rate = (sum(s["loaded"] for s in linked)
                             / sum(s["capacity"] for s in linked)) if linked else None
            status = "insufficient_data"
            # Les avions sont sondes pour le cargo principal de la ligne (PASS),
            # jamais pour le MAIL: les correlations MAIL restent un contexte
            # descriptif, aucun verdict de sur/sous-service MAIL n'est permis.
            if cargo == "mail":
                status = "pass_load_proxy_only"
            elif len(linked) >= min_pressure_samples and slope is not None:
                status = "indeterminate"
                if weighted_rate >= high_load and slope > stock_rise_week:
                    status = "underserved_suspected"
                elif weighted_rate <= low_load and slope <= 0:
                    status = "overserved_suspected"
            result[key] = {
                "destination": dest, "cargo": cargo,
                "linked_weeks": len(linked),
                "stock_weeks": sum(s["stock"] is not None for s in samples),
                "mean_load_ratio": mean_rate,
                "weighted_load_ratio": weighted_rate,
                "mean_stock": _average(s["stock"] for s in samples),
                "stock_slope_per_week": slope,
                "status": status,
                "correlation": {
                    "load_rating": pearson([s["load"] for s in samples],
                                           [s["rating"] for s in samples]),
                    "load_stock": pearson([s["load"] for s in samples],
                                          [s["stock"] for s in samples]),
                    "rating_stock": pearson([s["rating"] for s in samples],
                                            [s["stock"] for s in samples]),
                },
            }
    return result


def _window_metrics(rows):
    """Chaque cliché hebdomadaire pèse une fois, sans multiplier par les vols."""
    result = {
        "snapshots": len(rows),
        "fleet": _average(r["fleet"] for r in rows),
        "occupancy": _average(_weekly_rate(r) for r in rows),
        "last_profit": _average(r["last_profit"] for r in rows),
    }
    for dest in STATIONS:
        result["load_" + dest] = _average(_weekly_rate(r, dest) for r in rows)
        for cargo in CARGOS:
            for metric in ("stock", "rating"):
                result[f"{dest}_{cargo}_{metric}"] = _average(
                    r["stations"][dest][cargo][metric] for r in rows)
    return result


def reinforcement_events(rows, *, before_days=28, after_days=28,
                         min_window_samples=2):
    """Fenêtres locales non chevauchantes autour de hausses de flotte.

    Une date explicite `reinforce` est possible, mais seulement si l'événement
    appartient bien à l'intervalle entre deux clichés successifs.
    """
    events = []
    for previous, current in zip(rows, rows[1:]):
        raised = current["fleet"] > previous["fleet"]
        explicit = current["reinforce"]
        stamped = explicit is not None and previous["date"] < explicit <= current["date"]
        if not raised and not stamped:
            continue
        date = explicit if stamped else current["date"]
        events.append({"date": date, "detected_date": current["date"],
                       "fleet_before": previous["fleet"], "fleet_after": current["fleet"],
                       "added": current["fleet"] - previous["fleet"],
                       "evidence": "explicit_timestamp" if stamped else "fleet_increase"})
    # Deux événements peuvent arriver dans la même semaine : garde-fou.
    by_date = {}
    for event in events:
        by_date[event["date"]] = event
    events = [by_date[date] for date in sorted(by_date)]
    for i, event in enumerate(events):
        date = event["date"]
        previous_event = events[i - 1]["date"] if i else -math.inf
        next_event = events[i + 1]["date"] if i + 1 < len(events) else math.inf
        before = [r for r in rows if max(date - before_days, previous_event) <= r["date"] < date]
        after = [r for r in rows if date <= r["date"] <= date + after_days
                 and r["date"] < next_event]
        before_metrics = _window_metrics(before)
        after_metrics = _window_metrics(after)
        event["before"] = before_metrics
        event["after"] = after_metrics
        event["delta"] = {key: _diff(before_metrics[key], after_metrics[key])
                          for key in before_metrics if key != "snapshots"}
        event["adequate_windows"] = (len(before) >= min_window_samples
                                     and len(after) >= min_window_samples)
    return events


def summarize_line(rows, *, high_load, low_load, min_pressure_samples,
                   stock_rise_week, before_days, after_days, min_window_samples):
    all_flights = [flight for row in rows for flight in row["flights"]]
    return {
        "source": rows[0]["source"],
        "line": rows[0]["line"],
        "snapshots": len(rows),
        "first_day": rows[0]["date"],
        "last_day": rows[-1]["date"],
        "stations": {station: rows[-1]["stations"][station]["id"] for station in STATIONS},
        "airport_types": {station: rows[-1]["stations"][station]["airport"]
                          for station in STATIONS},
        "fleet_sizes": dict(sorted(Counter(str(row["fleet"]) for row in rows).items(),
                                  key=lambda item: int(item[0]))),
        "latest_fleet": rows[-1]["fleet"],
        "dist": rows[-1]["dist"],
        "neighbors": rows[-1]["neighbors"],
        "target": rows[-1]["target"],
        "last_profit": rows[-1]["last_profit"],
        "occupancy": occupancy_stats(all_flights),
        "by_direction": {
            direction: occupancy_stats(f for f in all_flights if f["direction"] == direction)
            for direction in DIRECTIONS
        },
        "by_fleet": {
            str(fleet): occupancy_stats(f for row in rows if row["fleet"] == fleet
                                        for f in row["flights"])
            for fleet in sorted({row["fleet"] for row in rows})
        },
        "station_pressure": station_diagnostics(
            rows, high_load=high_load, low_load=low_load,
            min_pressure_samples=min_pressure_samples,
            stock_rise_week=stock_rise_week),
        "reinforcements": reinforcement_events(
            rows, before_days=before_days, after_days=after_days,
            min_window_samples=min_window_samples),
    }


def analyze(paths, *, high_load=.85, low_load=.35, min_pressure_samples=3,
            stock_rise_week=0, before_days=28, after_days=28,
            min_window_samples=2):
    counters = Counter()
    issues = []
    all_rows = []
    file_stats = []
    for path in paths:
        with open(path, encoding="utf-8", errors="replace") as stream:
            rows, counts, errors = parse_log(stream, source=str(path))
        all_rows.extend(rows)
        counters.update(counts)
        issues.extend(errors[:max(0, 30 - len(issues))])
        file_stats.append({"path": str(path), "counts": counts})
    groups = defaultdict(list)
    for row in all_rows:
        groups[(row["source"], row["line"])].append(row)
    lines = [summarize_line(sorted(group, key=lambda row: row["date"]),
                            high_load=high_load, low_load=low_load,
                            min_pressure_samples=min_pressure_samples,
                            stock_rise_week=stock_rise_week,
                            before_days=before_days, after_days=after_days,
                            min_window_samples=min_window_samples)
             for _, group in sorted(groups.items())]
    all_flights = [flight for row in all_rows for flight in row["flights"]]
    pressures = [dict(source=line["source"], line=line["line"], **pressure)
                 for line in lines for pressure in line["station_pressure"].values()
                 if pressure["status"] in ("underserved_suspected", "overserved_suspected")]
    reinforcements = [dict(source=line["source"], line=line["line"], **event)
                      for line in lines for event in line["reinforcements"]]
    return {
        "kind": "AIR_LOAD7_passive_observation",
        "caveat": ("Observational only. Weekly in-flight loads may miss grounded planes. "
                   "Cargo is not identified per flight; PASS/MAIL station relationships "
                   "are proxies. Reinforcement deltas cannot establish causality. "
                   "Pooled readings across different lines may be confounded. "
                   "Malformed flight strings are excluded from occupancy statistics."),
        "thresholds": {"high_load": high_load, "low_load": low_load,
                       "stock_rise_per_week": stock_rise_week,
                       "min_pressure_samples": min_pressure_samples,
                       "before_days": before_days, "after_days": after_days,
                       "min_window_samples": min_window_samples},
        "files": file_stats,
        "counts": {**dict(counters), "files": len(file_stats), "lines": len(lines),
                   "reinforcements": len(reinforcements),
                   "reinforcements_adequate_windows": sum(e["adequate_windows"]
                                                           for e in reinforcements)},
        "occupancy": occupancy_stats(all_flights),
        "by_direction": {direction: occupancy_stats(
            f for f in all_flights if f["direction"] == direction)
            for direction in DIRECTIONS},
        "by_fleet": {str(fleet): occupancy_stats(
            f for row in all_rows if row["fleet"] == fleet for f in row["flights"])
            for fleet in sorted({row["fleet"] for row in all_rows})},
        "lines": lines,
        "pressure_alerts": pressures,
        "reinforcements": reinforcements,
        "parse_issues": issues,
    }


def _pretty(value, *, pct=False):
    if value is None:
        return "n/a"
    return f"{100 * value:.1f}%" if pct else f"{value:.2f}"


def _corr_cell(item):
    return f"{_pretty(item['r'])} ({item['n']})"


def _md(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(result):
    """Résumé lisible, avec données détaillées accessibles en JSON."""
    counts = result["counts"]
    out = ["# AIR_LOAD7 — mesures passives", "",
           f"{counts['files']} fichier(s), {counts['lines']} ligne(s), "
           f"{counts.get('valid_snapshots', 0)} clichés, "
           f"{result['occupancy']['flights']} vols en cours observés.", "",
           f"Occupation moyenne par avion : {_pretty(result['occupancy']['mean'], pct=True)} ; "
           f"pondérée par capacité : {_pretty(result['occupancy']['capacity_weighted'], pct=True)}. "
           f"Médiane : {_pretty(result['occupancy']['median'], pct=True)} ; "
           f"p90 : {_pretty(result['occupancy']['p90'], pct=True)}.", "",
           "## Par ligne", "",
           "| Fichier | Ligne | Semaines | Flotte | Distance | Voisins | Cible | "
           "Profit récent | Vols | Charge moyenne | Charge pondérée | p90 |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|" ]
    for line in result["lines"]:
        occ = line["occupancy"]
        out.append(f"| {_md(line['source'])} | {_md(line['line'])} | "
                   f"{line['snapshots']} | {line['latest_fleet']} | "
                   f"{_md(line['dist'])} | {_md(line['neighbors'])} | "
                   f"{_md(line['target'])} | {_md(line['last_profit'])} | "
                   f"{occ['flights']} | "
                   f"{_pretty(occ['mean'], pct=True)} | "
                   f"{_pretty(occ['capacity_weighted'], pct=True)} | "
                   f"{_pretty(occ['p90'], pct=True)} |")
    out.extend(["", "## Par direction (destination)", "",
                "| Vers | Vols | Charge moyenne | p10 | Médiane | p90 |",
                "|---|---:|---:|---:|---:|---:|"])
    for direction, metrics in result["by_direction"].items():
        out.append(f"| {direction} | {metrics['flights']} | "
                   f"{_pretty(metrics['mean'], pct=True)} | {_pretty(metrics['p10'], pct=True)} | "
                   f"{_pretty(metrics['median'], pct=True)} | {_pretty(metrics['p90'], pct=True)} |")
    out.extend(["", "## Par taille de flotte", "",
                "| Avions dans la ligne | Vols | Charge moyenne | Charge pondérée | p10 | p90 |",
                "|---:|---:|---:|---:|---:|---:|"])
    for fleet, metrics in result["by_fleet"].items():
        out.append(f"| {fleet} | {metrics['flights']} | "
                   f"{_pretty(metrics['mean'], pct=True)} | "
                   f"{_pretty(metrics['capacity_weighted'], pct=True)} | "
                   f"{_pretty(metrics['p10'], pct=True)} | {_pretty(metrics['p90'], pct=True)} |")
    out.extend(["", "## Distribution des charges", "",
                "| Charge des vols | Nombre |", "|---|---:|"])
    for band, count in result["occupancy"]["histogram"].items():
        out.append(f"| {band} | {count} |")
    out.extend(["", "## Corrélations par ligne, sens et station", "",
                "| Fichier | Ligne | Destination | Station cargo | Charge/note (n) | "
                "Charge/stock (n) | Note/stock (n) |",
                "|---|---:|---|---|---:|---:|---:|"])
    for line in result["lines"]:
        for pressure in line["station_pressure"].values():
            corr = pressure["correlation"]
            out.append(f"| {_md(line['source'])} | {_md(line['line'])} | "
                       f"{pressure['destination']} | {pressure['cargo']} | "
                       f"{_corr_cell(corr['load_rating'])} | "
                       f"{_corr_cell(corr['load_stock'])} | "
                       f"{_corr_cell(corr['rating_stock'])} |")
    out.extend(["", "## Pressions de desserte (heuristiques)", "",
                "| Fichier | Ligne | Destination | Fret station | Semaines jointes | "
                "Charge moyenne | Stock / semaine | Diagnostic |",
                "|---|---:|---|---|---:|---:|---:|---|"])
    for p in result["pressure_alerts"]:
        out.append(f"| {_md(p['source'])} | {_md(p['line'])} | {p['destination']} | "
                   f"{p['cargo']} | {p['linked_weeks']} | "
                   f"{_pretty(p['mean_load_ratio'], pct=True)} | "
                   f"{_pretty(p['stock_slope_per_week'])} | {p['status']} |")
    if not result["pressure_alerts"]:
        out.append("Aucun signal avec couverture suffisante.")
    out.extend(["", "## Renforts observés", "",
                "| Fichier | Ligne | Jour | Évolution flotte | Semaines avant/après | "
                "Delta charge | Delta profit observé | Couverture |",
                "|---|---:|---:|---:|---:|---:|---:|---|"])
    for event in result["reinforcements"]:
        out.append(f"| {_md(event['source'])} | {_md(event['line'])} | {event['date']} | "
                   f"{event['fleet_before']}→{event['fleet_after']} | "
                   f"{event['before']['snapshots']}/{event['after']['snapshots']} | "
                   f"{_pretty(event['delta']['occupancy'], pct=True)} | "
                   f"{_pretty(event['delta']['last_profit'])} | "
                   f"{'ok' if event['adequate_windows'] else 'insuffisante'} |")
    if not result["reinforcements"]:
        out.append("Aucune hausse de flotte observée.")
    out.extend(["", "## Qualité et limites", "",
                f"Anomalies de décodage : {counts.get('parse_issues', 0)} ; "
                f"doublons identiques : {counts.get('identical_duplicates', 0)} ; "
                f"conflits : {counts.get('conflicting_duplicates', 0)}.", "",
                result["caveat"], "",
                "Les corrélations charge/note/stock par ligne et direction, les quantiles "
                "et les fenêtres complètes de renfort figurent dans le rapport JSON."])
    return "\n".join(out) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("patterns", nargs="+", help="fichiers ou motifs de logs AIR_LOAD7")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", type=Path, help="sortie vers ce fichier (défaut : stdout)")
    parser.add_argument("--high-load", type=float, default=.85,
                        help="seuil d'occupation haute (défaut : 0.85)")
    parser.add_argument("--low-load", type=float, default=.35,
                        help="seuil d'occupation basse (défaut : 0.35)")
    parser.add_argument("--stock-rise-week", type=float, default=0,
                        help="pente stock/semaine > seuil pour alerte sous-desservie")
    parser.add_argument("--min-pressure-samples", type=int, default=3)
    parser.add_argument("--before-days", type=int, default=28)
    parser.add_argument("--after-days", type=int, default=28)
    parser.add_argument("--min-window-samples", type=int, default=2)
    args = parser.parse_args(argv)
    if not 0 <= args.low_load < args.high_load <= 1:
        parser.error("0 <= --low-load < --high-load <= 1 required")
    if args.min_pressure_samples < 3 or args.min_window_samples < 1:
        parser.error("minimum samples must be >=3 for pressure, >=1 for events")
    if args.before_days < 1 or args.after_days < 1 or args.stock_rise_week < 0:
        parser.error("window days must be positive and stock-rise-week nonnegative")
    files = sorted({Path(match) for pattern in args.patterns
                    for match in glob.glob(pattern, recursive=True) if Path(match).is_file()})
    if not files:
        parser.error("no matching log files")
    result = analyze(files, high_load=args.high_load, low_load=args.low_load,
                     min_pressure_samples=args.min_pressure_samples,
                     stock_rise_week=args.stock_rise_week, before_days=args.before_days,
                     after_days=args.after_days, min_window_samples=args.min_window_samples)
    payload = (json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
               if args.format == "json" else render_markdown(result))
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return result


if __name__ == "__main__":
    main()
