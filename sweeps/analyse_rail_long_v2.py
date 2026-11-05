"""Analyse descriptive d'un duel RAIL-LONG figé (sans partie OpenTTD).

    python -X utf8 sweeps/analyse_rail_long_v2.py results/<campagne>.json
    python -X utf8 sweeps/analyse_rail_long_v2.py results/<campagne>.json --format json

Le JSON C66 fournit les profits appariés et les services/véhicules aux
checkpoints. Les journaux RAIL_BUILD donnent la composition *initiale* des
trains, RAIL_LONG event=build les créations initiales v1. Les événements
RAIL_LONG_V2 et INVEST_STALL sont décrits séparément : une opération achevée
dans le journal n'est pas un inventaire physique des gares en fin de partie.
La télémétrie v1 n'expose pas les wagons présents en fin de partie ni le
revenu par véhicule : ces mesures restent indisponibles, sauf si une future
version ajoute explicitement un champ de revenu aux vehicle_financials.
"""

import argparse
import json
import re
from collections import Counter, defaultdict, deque
from pathlib import Path
from statistics import median


DATE_EVENT = re.compile(
    r"\bOPEX\s+(\d{4}-\d{1,2}-\d{1,2})\s+"
    r"(RAIL_BUILD|RAIL_LONG_V2|RAIL_LONG|INVEST_STALL)\s+(.+)$"
)
FIELDS = re.compile(r"\b([a-zA-Z_][a-zA-Z_0-9]*)=([^\s]+)")
V2_DONE_LENGTH = re.compile(r"(?:^|\s)len=(\d+)(?=\s|$)")

# Compteurs d'EVENEMENTS dans les logs, jamais un inventaire final des quais.
EVENT_COUNT_FIELDS = (
    "v2_initial_build_count",
    "v2_initial_both_ends_over_threshold",
    "v2_extension_done_count",
    "v2_extension_to_threshold_count",
    "v2_fleet_done_count",
    "v2_failed_count",
    "v2_rolled_back_count",
    "v2_orphan_safe_count",
    "invest_new_line_build_ok_count",
    "invest_station_built_count",
    "invest_station_pair_matched_count",
    "invest_stations_confirmed_at_build_count",
    "invest_unmatched_station_built_count",
    "invest_unmatched_build_ok_count",
    "invest_fleet_done_count",
)


def number(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def observed_checkpoint(campaign, policy, seed, repeat):
    snapshots = (
        item for item in campaign.get("line_telemetry", {}).get("snapshots", [])
        if item.get("duel_policy_id") == policy and item.get("arm") == "OpexAI"
        and number(item.get("seed")) == seed and number(item.get("repeat")) == repeat
        and item.get("ok") is True
    )
    latest = max(snapshots, key=lambda item: item.get("date", ""), default=None)
    if latest is None:
        return None

    rail = [line for line in latest.get("lines", []) if line.get("mode") == "rail"]
    ids = set()
    profits = {}
    revenues = {}
    for line in rail:
        for vehicle in line.get("vehicle_ids", []):
            ids.add(str(vehicle))
        for financial in line.get("vehicle_financials", []):
            vid = financial.get("vehicle_id")
            if vid is None:
                continue
            vid = str(vid)
            if "profit_this_year_gbp" in financial and financial["profit_this_year_gbp"] is not None:
                profits[vid] = financial["profit_this_year_gbp"]
            # Explicit future telemetry field only: profit is NOT a revenue proxy.
            if "revenue_this_year_gbp" in financial and financial["revenue_this_year_gbp"] is not None:
                revenues[vid] = financial["revenue_this_year_gbp"]

    return {
        "date": latest.get("date"),
        "rail_services": len(rail),
        "rail_vehicles": len(ids),
        "max_vehicles_per_service": max((len(line.get("vehicle_ids", [])) for line in rail), default=0),
        "observed_profit_per_vehicle_gbp": (
            sum(profits.values()) / len(ids) if ids and len(profits) == len(ids) else None
        ),
        "observed_revenue_per_vehicle_gbp": (
            sum(revenues.values()) / len(ids) if ids and len(revenues) == len(ids) else None
        ),
        "vehicle_profit_coverage": len(profits),
        "vehicle_revenue_coverage": len(revenues),
    }


def parse_engine_log_lines(lines, long_min):
    """Événements observés, sans extrapoler les gares survivant au checkpoint."""
    all_wagons = []
    freight_wagons = []
    rail_builds = 0
    freight_builds = 0
    long_builds = []
    fallbacks = 0
    v2_initial_builds = []
    v2_extensions_done = []
    v2_fleet_done = []
    v2_failed = []
    v2_rolled_back = []
    v2_orphan_safe = []
    invest_new_line_build_ok = []
    invest_station_built = []
    invest_station_pairs_matched = []
    invest_fleet_done = []
    pending_station_pairs = defaultdict(deque)

    def station_key(values):
        fields = ("src", "dst", "parent", "new_a")
        if any(number(values.get(field)) is None for field in fields):
            return None
        return tuple(number(values[field]) for field in fields)

    for text in lines:
        match = DATE_EVENT.search(text)
        if match is None:
            continue
        date, source, payload = match.groups()
        values = dict(FIELDS.findall(payload))
        event = values.get("event")
        if source == "RAIL_BUILD":
            wagons = number(values.get("wagons"))
            if wagons is None:
                continue
            wagons += number(values.get("wagons2")) or 0
            # Composition INITIALE, non celle du checkpoint terminal.
            trains = max(1, number(values.get("trains")) or 1)
            all_wagons.extend([wagons] * trains)
            rail_builds += 1
            if values.get("cargo") not in ("PASS", "MAIL"):
                freight_wagons.extend([wagons] * trains)
                freight_builds += 1
        elif source == "RAIL_LONG":
            if event == "fallback":
                fallbacks += 1
            elif event == "build":
                length_a = number(values.get("len_a"))
                length_b = number(values.get("len_b"))
                long_builds.append({
                    "line": number(values.get("line")),
                    "date": date,
                    "length_a": length_a,
                    "length_b": length_b,
                    "initial_wagons": number(values.get("wagons")),
                    "trains": number(values.get("trains")),
                })
        elif source == "RAIL_LONG_V2":
            if event == "build":
                v2_initial_builds.append({
                    "date": date,
                    "line": number(values.get("line")),
                    "length_a": number(values.get("len_a")),
                    "length_b": number(values.get("len_b")),
                    "initial_wagons": number(values.get("wagons")),
                    "trains": number(values.get("trains")),
                })
            elif event == "done":
                # OpexRailLongV2Log émet reason=len=7 cost=..., pas len=7 seul.
                length_match = V2_DONE_LENGTH.search(values.get("reason", ""))
                v2_extensions_done.append({
                    "date": date,
                    "line": number(values.get("line")),
                    "target_length": int(length_match.group(1)) if length_match else None,
                    "cost": number(values.get("cost")),
                })
            elif event == "fleet_done":
                v2_fleet_done.append({
                    "date": date,
                    "line": number(values.get("line")),
                    "wagons_old": number(values.get("wagons_old")),
                    "wagons_new": number(values.get("wagons_new")),
                    "new_vehicle": number(values.get("new_vehicle")),
                    "capacity": number(values.get("capacity")),
                })
            elif event in ("fail", "rolled_back", "orphan_safe"):
                detail = {
                    "date": date,
                    "line": number(values.get("line")),
                    "reason": values.get("reason"),
                }
                {"fail": v2_failed, "rolled_back": v2_rolled_back,
                 "orphan_safe": v2_orphan_safe}[event].append(detail)
        elif source == "INVEST_STALL":
            if event == "station_built":
                detail = {
                    "date": date,
                    "src": number(values.get("src")),
                    "dst": number(values.get("dst")),
                    "parent": number(values.get("parent")),
                    "new_a": number(values.get("new_a")),
                    "new_b": number(values.get("new_b")),
                    "matched_build_ok": False,
                }
                invest_station_built.append(detail)
                key = station_key(values)
                if (key is not None and detail["new_b"] is not None
                        and detail["new_b"] >= 0 and detail["new_a"] >= 0
                        and detail["new_a"] != detail["new_b"]):
                    pending_station_pairs[key].append(detail)
            elif event == "build_ok":
                detail = {
                    "date": date,
                    "src": number(values.get("src")),
                    "dst": number(values.get("dst")),
                    "parent": number(values.get("parent")),
                    "new_a": number(values.get("new_a")),
                    "trains": number(values.get("trains")),
                    "cost": number(values.get("cost")),
                    "matched_station_pair": False,
                }
                invest_new_line_build_ok.append(detail)
                key = station_key(values)
                if key is not None and pending_station_pairs[key]:
                    station = pending_station_pairs[key].popleft()
                    station["matched_build_ok"] = True
                    detail["matched_station_pair"] = True
                    invest_station_pairs_matched.append({
                        "station_built_date": station["date"],
                        "build_ok_date": date,
                        "src": detail["src"],
                        "dst": detail["dst"],
                        "parent": detail["parent"],
                        "new_a": detail["new_a"],
                        "new_b": station["new_b"],
                    })
            elif event == "done" and values.get("route") == "fleet":
                invest_fleet_done.append({
                    "date": date,
                    "line": number(values.get("line")),
                    "kind": values.get("kind"),
                    "old_vehicle": number(values.get("old_vehicle")),
                    "new_vehicle": number(values.get("new_vehicle")),
                    "old_wagons": number(values.get("old_wagons")),
                    "wagons": number(values.get("wagons")),
                })

    return {
        "rail_build_events": rail_builds,
        "freight_build_events": freight_builds,
        "initial_all_train_wagons_median": median(all_wagons) if all_wagons else None,
        "initial_freight_train_wagons_median": median(freight_wagons) if freight_wagons else None,
        "initial_freight_train_wagons_count": len(freight_wagons),
        "initial_freight_train_wagons_histogram": dict(sorted(Counter(freight_wagons).items())),
        "long_station_builds": long_builds,
        "long_station_build_count": len(long_builds),
        "long_both_ends_over_threshold": sum(
            1 for item in long_builds
            if item["length_a"] is not None and item["length_b"] is not None
            and item["length_a"] >= long_min and item["length_b"] >= long_min
        ),
        "long_fallback_events": fallbacks,
        "v2_initial_builds": v2_initial_builds,
        "v2_initial_build_count": len(v2_initial_builds),
        "v2_initial_both_ends_over_threshold": sum(
            1 for item in v2_initial_builds
            if item["length_a"] is not None and item["length_b"] is not None
            and item["length_a"] >= long_min and item["length_b"] >= long_min
        ),
        "v2_extensions_done": v2_extensions_done,
        "v2_extension_done_count": len(v2_extensions_done),
        "v2_extension_to_threshold_count": sum(
            1 for item in v2_extensions_done
            if item["target_length"] is not None and item["target_length"] >= long_min
        ),
        "v2_fleet_done": v2_fleet_done,
        "v2_fleet_done_count": len(v2_fleet_done),
        "v2_failed": v2_failed,
        "v2_failed_count": len(v2_failed),
        "v2_rolled_back": v2_rolled_back,
        "v2_rolled_back_count": len(v2_rolled_back),
        "v2_orphan_safe": v2_orphan_safe,
        "v2_orphan_safe_count": len(v2_orphan_safe),
        "invest_new_line_build_ok": invest_new_line_build_ok,
        "invest_new_line_build_ok_count": len(invest_new_line_build_ok),
        "invest_station_built": invest_station_built,
        "invest_station_built_count": len(invest_station_built),
        "invest_station_pairs_matched": invest_station_pairs_matched,
        "invest_station_pair_matched_count": len(invest_station_pairs_matched),
        "invest_stations_confirmed_at_build_count": 2 * len(invest_station_pairs_matched),
        "invest_unmatched_station_built_count": sum(
            not item["matched_build_ok"] for item in invest_station_built
        ),
        "invest_unmatched_build_ok_count": sum(
            not item["matched_station_pair"] for item in invest_new_line_build_ok
        ),
        "invest_fleet_done": invest_fleet_done,
        "invest_fleet_done_count": len(invest_fleet_done),
    }


def engine_log(engine_dir, policy, seed, repeat, long_min):
    path = engine_dir / f"{policy}_seed{seed}_r{repeat}.log"
    if not path.is_file():
        return None, str(path)
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return parse_engine_log_lines(handle, long_min), None


def analyze(path, engine_dir=None, long_min=6):
    campaign = json.loads(path.read_text(encoding="utf-8"))
    comparison = campaign.get("policy_comparison")
    if not comparison or not comparison.get("per_pair"):
        raise ValueError("un JSON de duel C66 avec policy_comparison.per_pair est requis")
    reference = comparison["reference_policy_id"]
    variant = comparison["variant_policy_id"]
    if engine_dir is None:
        engine_dir = path.with_suffix("").with_name(path.stem + "_engine")

    rows = []
    errors = []
    for pair in comparison["per_pair"]:
        if not pair.get("complete"):
            errors.append(f"paire incomplete : seed={pair.get('seed')} repeat={pair.get('repeat')}")
            continue
        seed, repeat = number(pair.get("seed")), number(pair.get("repeat"))
        metrics = pair["metrics"]["profit_year"]
        row = {
            "seed": seed, "repeat": repeat,
            "reference_profit_year_gbp": metrics["reference_opex"],
            "variant_profit_year_gbp": metrics["variant_opex"],
            "policy_delta_profit_year_gbp": metrics["policy_delta"],
        }
        for name, policy in (("reference", reference), ("variant", variant)):
            row[name + "_checkpoint"] = observed_checkpoint(campaign, policy, seed, repeat)
            if row[name + "_checkpoint"] is None:
                errors.append(f"télémétrie manquante : {policy} seed={seed} repeat={repeat}")
            row[name + "_builds"], missing = engine_log(engine_dir, policy, seed, repeat, long_min)
            if missing:
                errors.append("journal manquant : " + missing)
        rows.append(row)

    delta = comparison.get("aggregates", {}).get("profit_year", {}).get("policy_delta", {})
    aggregate = {}
    for name in ("reference", "variant"):
        checks = [row[name + "_checkpoint"] for row in rows]
        builds = [row[name + "_builds"] for row in rows]
        wagon_hist = Counter()
        for build in builds:
            if build:
                wagon_hist.update({int(k): v for k, v in build["initial_freight_train_wagons_histogram"].items()})
        pooled_wagons = [wagon for wagon, count in wagon_hist.items() for _ in range(count)]
        valid_checks = [s for s in checks if s is not None]
        vehicles = sum(s["rail_vehicles"] for s in valid_checks)
        profit_observed = all(s["vehicle_profit_coverage"] == s["rail_vehicles"] for s in valid_checks)
        revenue_observed = all(s["vehicle_revenue_coverage"] == s["rail_vehicles"] for s in valid_checks)
        all_checks = len(valid_checks) == len(rows)
        aggregate[name] = {
            "final_rail_services": sum(s["rail_services"] for s in valid_checks) if all_checks else None,
            "final_rail_vehicles": vehicles if all_checks else None,
            "initial_freight_train_wagons_median_pooled": median(pooled_wagons) if pooled_wagons else None,
            "initial_freight_train_wagons_count": len(pooled_wagons),
            "long_station_build_count": sum(b["long_station_build_count"] for b in builds if b) if all(builds) else None,
            "long_both_ends_over_threshold": sum(b["long_both_ends_over_threshold"] for b in builds if b) if all(builds) else None,
            "observed_profit_per_vehicle_gbp": (
                sum(s["observed_profit_per_vehicle_gbp"] * s["rail_vehicles"] for s in valid_checks) / vehicles
                if all_checks and profit_observed and vehicles > 0 else None
            ),
            "observed_revenue_per_vehicle_gbp": (
                sum(s["observed_revenue_per_vehicle_gbp"] * s["rail_vehicles"] for s in valid_checks) / vehicles
                if all_checks and revenue_observed and vehicles > 0 else None
            ),
        }
        # Sommes des journaux par politique : jamais des gares encore présentes.
        for metric in EVENT_COUNT_FIELDS:
            aggregate[name][metric] = (
                sum(b[metric] for b in builds) if all(builds) else None
            )
    return {
        "source": str(path),
        "source_bundle_sha256": campaign.get("source_bundle_sha256"),
        "reference_policy_id": reference,
        "variant_policy_id": variant,
        "expected_last_checkpoint": campaign.get("expected_last_checkpoint"),
        "mean_profit_year_delta_gbp": delta.get("mean"),
        "wins": delta.get("wins"), "losses": delta.get("losses"), "ties": delta.get("ties"),
        "wilcoxon_p": delta.get("wilcoxon_p"),
        "bootstrap_95pct_ci_gbp": delta.get("mean_bootstrap_95pct_ci"),
        "verdict": comparison.get("verdict"),
        "minimum_long_platform_tiles": long_min,
        "aggregate": aggregate,
        "rows": rows,
        "missing_evidence": errors,
        "notes": [
            "Wagons : médiane des compositions initiales RAIL_BUILD, pas parc final ; PASS/MAIL exclus du fret.",
            "Créations longues v1 : seules les poses RAIL_LONG event=build sont comptées ; chaque quai doit satisfaire le seuil.",
            "Profit/véhicule : résultat observé au checkpoint, année inachevée si décembre 1.",
            "Revenu/véhicule : indisponible en télémétrie v1 ; jamais déduit du profit ni d'une prévision.",
            "Comparaison REF/ON strictement au sein du même bundle figé.",
        ],
    }


def display(result):
    def n(value, decimals=0):
        if value is None:
            return "n/d"
        return f"{value:,.{decimals}f}".replace(",", " ")

    print(f"# {Path(result['source']).stem}")
    print(f"Bundle : {result['source_bundle_sha256']}; verdict : {result['verdict']}.")
    print(f"Δ moyen Opex ON−REF : {n(result['mean_profit_year_delta_gbp'])} £/an ; "
          f"V/D/E : {result['wins']}/{result['losses']}/{result['ties']}; "
          f"Wilcoxon : {result['wilcoxon_p']}.")
    a, b = result["aggregate"]["reference"], result["aggregate"]["variant"]
    print(f"Agrégat REF/ON : wagons fret initiaux médians "
          f"{n(a['initial_freight_train_wagons_median_pooled'], 1)}/{n(b['initial_freight_train_wagons_median_pooled'], 1)} ; "
          f"créations longues v1 ≥{result['minimum_long_platform_tiles']} tuiles aux deux bouts "
          f"{n(a['long_both_ends_over_threshold'])}/{n(b['long_both_ends_over_threshold'])} ; "
          f"véhicules finaux {n(a['final_rail_vehicles'])}/{n(b['final_rail_vehicles'])}.")
    print("| Graine | Δ profit/an | Trains fin REF/ON | Wagons fret initiaux médians REF/ON | Créations longues v1 REF/ON | Profit checkpoint/véhicule REF/ON | Revenu checkpoint/véhicule REF/ON |")
    print("|---:|---:|---:|---:|---:|---:|---:|")
    for row in result["rows"]:
        a, b = row["reference_checkpoint"], row["variant_checkpoint"]
        ab, bb = row["reference_builds"], row["variant_builds"]
        pair = lambda x, y, dp=0: f"{n(x, dp)}/{n(y, dp)}"
        print(f"| {row['seed']} | {n(row['policy_delta_profit_year_gbp'])} | "
              f"{pair(a['rail_vehicles'] if a else None, b['rail_vehicles'] if b else None)} | "
              f"{pair(ab['initial_freight_train_wagons_median'] if ab else None, bb['initial_freight_train_wagons_median'] if bb else None, 1)} | "
              f"{pair(ab['long_both_ends_over_threshold'] if ab else None, bb['long_both_ends_over_threshold'] if bb else None)} | "
              f"{pair(a['observed_profit_per_vehicle_gbp'] if a else None, b['observed_profit_per_vehicle_gbp'] if b else None, 1)} | "
              f"{pair(a['observed_revenue_per_vehicle_gbp'] if a else None, b['observed_revenue_per_vehicle_gbp'] if b else None, 1)} |")
    # Préserver intégralement le tableau v1 historique. Afficher les nouveaux
    # compteurs dans une section distincte, uniquement si des événements v2 /
    # INVEST_STALL ont effectivement été trouvés.
    if any(
        build and any(build[metric] for metric in EVENT_COUNT_FIELDS)
        for row in result["rows"]
        for build in (row["reference_builds"], row["variant_builds"])
    ):
        ref, var = result["aggregate"]["reference"], result["aggregate"]["variant"]
        paired = lambda metric: f"{n(ref[metric])}/{n(var[metric])}"
        print("\n## Événements v2 / INVEST_STALL (journaux, PAS inventaire final)")
        print("La colonne historique « créations longues v1 » ci-dessus ne compte que les créations RAIL_LONG v1.")
        print(f"Créations initiales longues v2 ≥{result['minimum_long_platform_tiles']} : "
              f"{paired('v2_initial_both_ends_over_threshold')} ; "
              f"extensions v2 terminées : {paired('v2_extension_done_count')} "
              f"(cible ≥{result['minimum_long_platform_tiles']} : "
              f"{paired('v2_extension_to_threshold_count')}) ; "
              f"rames v2 modifiées : {paired('v2_fleet_done_count')}.")
        print(f"INVEST_STALL nouvelles lignes build_ok : {paired('invest_new_line_build_ok_count')} ; "
              f"chantiers station_built : {paired('invest_station_built_count')} ; "
              f"paires appariées à build_ok : {paired('invest_station_pair_matched_count')} ; "
              f"stations identifiées au build_ok : "
              f"{paired('invest_stations_confirmed_at_build_count')} ; "
              f"rames modifiées : {paired('invest_fleet_done_count')}.")
        print(f"Stations bâties sans build_ok correspondant : "
              f"{paired('invest_unmatched_station_built_count')} ; "
              f"build_ok sans paire station_built : "
              f"{paired('invest_unmatched_build_ok_count')}.")
        print(f"V2 échecs : {paired('v2_failed_count')} ; "
              f"rollbacks terminés : {paired('v2_rolled_back_count')} ; "
              f"orphan_safe : {paired('v2_orphan_safe_count')}.")
        print("| Graine | Créations v2 longues REF/ON | Extensions v2 REF/ON | Rames v2 REF/ON | "
              "Lignes INVEST REF/ON | Paires stations confirmées REF/ON | Rames INVEST REF/ON | "
              "Rollbacks v2 REF/ON |")
        print("|---:|---:|---:|---:|---:|---:|---:|---:|")
        for row in result["rows"]:
            ab, bb = row["reference_builds"], row["variant_builds"]
            pair = lambda metric: f"{n(ab[metric] if ab else None)}/{n(bb[metric] if bb else None)}"
            print(f"| {row['seed']} | {pair('v2_initial_both_ends_over_threshold')} | "
                  f"{pair('v2_extension_done_count')} | {pair('v2_fleet_done_count')} | "
                  f"{pair('invest_new_line_build_ok_count')} | "
                  f"{pair('invest_station_pair_matched_count')} | "
                  f"{pair('invest_fleet_done_count')} | {pair('v2_rolled_back_count')} |")
        print("Les appariements station_built/build_ok attestent un chantier réussi, pas la présence "
              "de ces gares dans une sauvegarde finale. pick/fail/fleet_pick ne sont jamais des succès.")
    print("\n" + "\n".join(result["notes"]))
    if result["missing_evidence"]:
        print("\nDonnées manquantes (ne pas interpréter comme zéro) :")
        for item in result["missing_evidence"]:
            print("- " + item)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path, help="JSON C66 du duel figé")
    parser.add_argument("--engine-dir", type=Path, help="Répertoire des logs moteur, sinon <campagne>_engine")
    parser.add_argument("--long-platform-min", type=int, default=6, help="Longueur minimale réelle de chaque quai (défaut : 6)")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    if args.long_platform_min < 1:
        parser.error("--long-platform-min doit être positif")
    try:
        output = analyze(args.campaign, args.engine_dir, args.long_platform_min)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    if args.format == "json":
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        display(output)
    raise SystemExit(2 if output["missing_evidence"] else 0)
