"""Diagnostic C81 / C82 en solo pur (chargement complet et calibration par moteur).

Bras :
* ``base`` : OpexAI au défaut (air_full_load=0, c82_engine_calibration=0) ;
* ``fl1``  : air_full_load=1 (plein chargement aux deux aéroports) ;
* ``fl2``  : air_full_load=2 (plein chargement au premier aéroport seulement, défaut AAAHogEx) ;
* ``c82``  : c82_engine_calibration=1 (calibration du profit prédit par moteur d'avion).

Option --probe : ajoute probe_portfolio=1 à tous les bras.
Paires : chaque bras contre base (fl1-base, fl2-base, c82-base).
Métriques primaires et secondaires :
* profit annuel OpexAI (profit_year, PLYR) ;
* valeur d'entreprise (company_value, PLYR) ;
* véhicules pilotables (vehicles, VEHS) ;
* profit aérien (air_profit, télémesure des lignes) ;
* profit aérien par place (air_profit_per_seat) ;
* avions par ligne (air_planes_per_line).
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import statistics
import sys
import types

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

try:
    import openttdlab
    from openttdlab import bananas_ai_library, local_folder, run_experiments
    _HAS_OPENTTDLAB = True
except ImportError:
    _HAS_OPENTTDLAB = False
    class _Dummy(types.ModuleType):
        def __getattr__(self, item):
            return _Dummy(item)
        def __call__(self, *args, **kwargs):
            return _Dummy("sub")
    _m = _Dummy("openttdlab")
    _m.subprocess = _Dummy("subprocess")
    sys.modules["openttdlab"] = _m
    sys.modules["openttdlab.subprocess"] = _m.subprocess
    import openttdlab
    bananas_ai_library = None
    local_folder = None
    run_experiments = None

if _HAS_OPENTTDLAB:
    _real_check_output = openttdlab.subprocess.check_output

    def _check_output_with_script_debug(args, *rest, **kwargs):
        args = tuple(args)
        if any(str(arg).startswith("-vnull") for arg in args):
            args = args[:1] + ("-d", "script=4") + args[1:]
        return _real_check_output(args, *rest, **kwargs)

    openttdlab.subprocess.check_output = _check_output_with_script_debug

from bench_v2 import (  # noqa: E402
    OPENGFX_VERSION,
    OPENTTD_VERSION,
    enable_savegame_cleanup,
    make_cfg,
    year_profit,
)
from physical_counters import decode_vehicles  # noqa: E402
from bench_1v1_5y_20seeds import extract_line_telemetry  # noqa: E402


STARTING_YEAR = 1970
DEFAULT_YEARS = 6
DEFAULT_SEEDS = (100, 42, 12345)
DEFAULT_WORKERS = 3

ARM_SPECS = {
    "base": (),
    "fl1": (("air_full_load", 1),),
    "fl2": (("air_full_load", 2),),
    "c82": (("c82_engine_calibration", 1),),
}
DEFAULT_ARMS = ("base", "fl1", "fl2", "c82")

VEHICLE_VARIANT_BY_MODE = {
    "rail": "train",
    "road": "roadveh",
    "water": "ship",
    "air": "aircraft",
}


def _first(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _raw_vehicle_common(chunks, vehicle_index, mode):
    """Retrouve le common brut correspondant a un vehicule primaire qualifie."""
    vehs = (chunks or {}).get("VEHS") or {}
    record = None
    if isinstance(vehs, dict):
        record = vehs.get(vehicle_index)
        if record is None:
            record = vehs.get(str(vehicle_index))
    elif isinstance(vehs, list) and 0 <= vehicle_index < len(vehs):
        record = vehs[vehicle_index]
    if not isinstance(record, dict):
        return None
    variant = VEHICLE_VARIANT_BY_MODE.get(mode)
    body = _first(record.get(variant)) if variant else None
    common = _first(body.get("common")) if isinstance(body, dict) else None
    return common if isinstance(common, dict) else None


def _air_engine_counts(chunks, owner=0):
    """Compte les avions de la compagnie par type de moteur."""
    vehs = (chunks or {}).get("VEHS")
    if not vehs:
        return {}
    dec = decode_vehicles(vehs, target_owner=owner)
    if not dec.get("chunk_valid"):
        return {}
    counts = defaultdict(int)
    for detail in dec.get("primary_vehicles_detail") or []:
        if detail.get("mode") != "air":
            continue
        vehicle_index = detail.get("index")
        common = _raw_vehicle_common(chunks, vehicle_index, "air")
        if isinstance(common, dict):
            engine_type = common.get("engine_type")
            if engine_type is not None:
                counts[int(engine_type)] += 1
    return dict(sorted(counts.items()))


def _player(chunks, owner):
    players = chunks.get("PLYR") or {}
    return players.get(owner) or players.get(str(owner)) or {}


def _profit_year(chunks, owner):
    player = _player(chunks, owner)
    closed = player.get("old_economy") or []
    value = year_profit(closed) if closed else 0
    return value if value is not None else 0


def _company_value(chunks, owner):
    player = _player(chunks, owner)
    closed = player.get("old_economy") or []
    last_closed = closed[0] if closed else {}
    value = last_closed.get("company_value")
    return value if value is not None else 0


def _vehicle_count(chunks, owner):
    vehs = chunks.get("VEHS")
    if not vehs:
        return None
    dec = decode_vehicles(vehs, target_owner=owner)
    return dec["primary_vehicles_count"] if dec.get("chunk_valid") else None


def _extract_month(date_val):
    if hasattr(date_val, "month"):
        return int(date_val.month)
    if isinstance(date_val, str):
        parts = date_val.split("-")
        if len(parts) >= 2:
            try:
                return int(parts[1])
            except ValueError:
                pass
    return None


def _extract_air_metrics_from_lines(lines, month):
    air_lines = [l for l in lines if l.get("mode") == "air"]
    n_lines = len(air_lines)
    n_planes = sum(int(l.get("vehicles", 0)) for l in air_lines)
    n_seats = sum(
        sum(int(cap) for cap in l.get("capacity_by_cargo", {}).values())
        for l in air_lines
    )

    use_this_year = (month == 12)
    profit_source = "this_year" if use_this_year else "last_year"
    if use_this_year:
        air_profit = sum(float(l.get("profit_this_year_gbp", 0.0)) for l in air_lines)
    else:
        air_profit = sum(float(l.get("profit_last_year_gbp", 0.0)) for l in air_lines)

    profit_per_seat = (air_profit / n_seats) if n_seats > 0 else 0.0
    planes_per_line = (float(n_planes) / n_lines) if n_lines > 0 else 0.0

    return {
        "air_lines": n_lines,
        "air_planes": n_planes,
        "air_seats": n_seats,
        "air_profit": air_profit,
        "air_profit_source": profit_source,
        "air_profit_per_seat": profit_per_seat,
        "air_planes_per_line": planes_per_line,
    }


def compute_air_line_metrics(chunks, save_date):
    telemetry = extract_line_telemetry(chunks, 0)
    month = _extract_month(save_date)
    return _extract_air_metrics_from_lines(telemetry.get("lines", []), month)


def parse_c82_probe(output):
    """Extrait la telemetrie de sonde C82 sans conserver la sortie terminale complete."""
    factors = {}
    calls_sum = 0
    differ_sum = 0
    choice_samples = []

    if not output:
        return {
            "factors": factors,
            "calls_sum": calls_sum,
            "differ_sum": differ_sum,
            "choice_samples": choice_samples,
        }

    for line in output.splitlines():
        if "C69_BOTTLENECK" not in line or "phase=c82_" not in line:
            continue
        fields = {}
        for token in line.split():
            if "=" in token:
                k, v = token.split("=", 1)
                fields[k] = v
        phase = fields.get("phase")
        if phase == "c82_factor":
            try:
                engine = int(fields.get("engine"))
                factors[engine] = {
                    "engine": engine,
                    "name": fields.get("name", "unknown"),
                    "lines": int(fields.get("lines", 0)),
                    "k": float(fields.get("k", 1.0)),
                    "year": int(fields.get("year", 0)),
                }
            except (ValueError, TypeError):
                pass
        elif phase == "c82_choice_summary":
            try:
                calls_sum += int(fields.get("calls", 0))
                differ_sum += int(fields.get("differ", 0))
            except (ValueError, TypeError):
                pass
        elif phase == "c82_choice":
            if len(choice_samples) < 20:
                choice_samples.append(line.strip())

    return {
        "factors": factors,
        "calls_sum": calls_sum,
        "differ_sum": differ_sum,
        "choice_samples": choice_samples,
    }


def keep(row):
    """Conserver uniquement les metriques necessaires, SANS sortie terminale."""
    chunks = row.get("chunks", {})
    context = row["experiment"]["bench_context"]
    arm = row["experiment"]["bench_arm"]
    seed = row["experiment"]["seed"]
    date_val = row.get("date")
    date_str = str(date_val or "")

    opex_profit = _profit_year(chunks, 0)
    opex_company_value = _company_value(chunks, 0)
    opex_vehicles = _vehicle_count(chunks, 0)
    opex_air_engines = _air_engine_counts(chunks, 0)
    air_metrics = compute_air_line_metrics(chunks, date_val)
    probe_info = parse_c82_probe(row.get("output")) if row.get("output") else None

    rec = {
        "context": context,
        "arm": arm,
        "seed": seed,
        "date": date_str,
        "opex_profit_year": opex_profit,
        "opex_company_value": opex_company_value,
        "opex_vehicles": opex_vehicles,
        "opex_air_engines": opex_air_engines,
        **air_metrics,
    }
    if probe_info is not None:
        rec["c82_probe"] = probe_info
    return (rec,)


def _latest_by_run(rows):
    latest = {}
    for row in rows:
        key = (row["context"], row["arm"], row["seed"])
        previous = latest.get(key)
        if previous is None or row["date"] > previous["date"]:
            latest[key] = row
    return latest


def _mean(values):
    values = [value for value in values if value is not None]
    return statistics.mean(values) if values else None


def _median(values):
    values = [value for value in values if value is not None]
    return statistics.median(values) if values else None


def _paired_outcome(differences):
    return {
        "wins": sum(1 for value in differences if value > 0),
        "ties": sum(1 for value in differences if value == 0),
        "losses": sum(1 for value in differences if value < 0),
    }


def summarize(latest, seeds, arm_names, probe=False):
    metric_fields = {
        "profit_year": "opex_profit_year",
        "company_value": "opex_company_value",
        "vehicles": "opex_vehicles",
        "air_profit": "air_profit",
        "air_profit_per_seat": "air_profit_per_seat",
        "air_planes_per_line": "air_planes_per_line",
    }
    by_metric = {}
    for label, field in metric_fields.items():
        per_arm = {}
        for arm in arm_names:
            values = [latest[("solo", arm, seed)][field] for seed in seeds]
            per_arm[f"solo:{arm}"] = {
                "mean": _mean(values),
                "median": _median(values),
                "per_seed": dict(zip(seeds, values)),
            }
        pairs = {}
        if "base" in arm_names:
            ctrl = "base"
            for treat in arm_names:
                if treat == ctrl:
                    continue
                deltas = []
                for seed in seeds:
                    t = latest[("solo", treat, seed)][field]
                    c = latest[("solo", ctrl, seed)][field]
                    deltas.append(None if t is None or c is None else t - c)
                clean = [d for d in deltas if d is not None]
                pairs[f"solo:{treat}-{ctrl}"] = {
                    "deltas": dict(zip(seeds, deltas)),
                    "delta_mean": _mean(clean),
                    "delta_median": _median(clean),
                    "paired_outcome": _paired_outcome(clean),
                }
        by_metric[label] = {"per_arm": per_arm, "pairs": pairs}

    air_engines = {}
    for arm in arm_names:
        per_seed = {
            seed: latest[("solo", arm, seed)].get("opex_air_engines", {})
            for seed in seeds
        }
        total = defaultdict(int)
        for counts in per_seed.values():
            for eng, cnt in counts.items():
                total[eng] += cnt
        air_engines[f"solo:{arm}"] = {
            "per_seed": per_seed,
            "total": dict(sorted(total.items())),
        }

    c82_probe_summary = {}
    if probe:
        for arm in arm_names:
            arm_factors = {}
            total_calls = 0
            total_differ = 0
            all_samples = []
            factors_by_seed = {}
            for seed in seeds:
                p_info = latest[("solo", arm, seed)].get("c82_probe") or {}
                factors = p_info.get("factors", {})
                factors_by_seed[seed] = factors
                for eng, f_data in factors.items():
                    arm_factors[eng] = f_data
                total_calls += p_info.get("calls_sum", 0)
                total_differ += p_info.get("differ_sum", 0)
                samples = p_info.get("choice_samples", [])
                if len(all_samples) < 20:
                    needed = 20 - len(all_samples)
                    all_samples.extend(samples[:needed])
            c82_probe_summary[f"solo:{arm}"] = {
                "calls_sum": total_calls,
                "differ_sum": total_differ,
                "factors_by_seed": factors_by_seed,
                "latest_factors": arm_factors,
                "choice_samples_20": all_samples,
            }

    res = {
        "by_metric": by_metric,
        "air_engines": air_engines,
    }
    if probe:
        res["c82_probes"] = c82_probe_summary
    return res


def _print_summary(summary, seeds, arm_names, probe=False):
    metric_labels = [
        ("profit_year", "profit annuel OpexAI (£/an)", "{:,.0f}"),
        ("company_value", "valeur d'entreprise OpexAI (£)", "{:,.0f}"),
        ("vehicles", "vehicules pilotables OpexAI", "{:.0f}"),
        ("air_profit", "profit aerien OpexAI (£/an)", "{:,.0f}"),
        ("air_profit_per_seat", "profit aerien par place (£/place)", "{:.2f}"),
        ("air_planes_per_line", "avions par ligne aerienne", "{:.2f}"),
    ]
    for m_key, title, fmt in metric_labels:
        data = summary["by_metric"][m_key]
        print(f"\n=== SOLO : {title} ===")
        print("seed | " + " | ".join(arm for arm in arm_names))
        for seed in seeds:
            cells = []
            for arm in arm_names:
                value = data["per_arm"][f"solo:{arm}"]["per_seed"][seed]
                if value is None:
                    cells.append("n/a")
                elif "{:," in fmt:
                    cells.append(f"{value:,.0f}")
                elif "{:.2f}" in fmt:
                    cells.append(f"{value:.2f}")
                else:
                    cells.append(f"{value:.1f}")
            print(f"{seed} | " + " | ".join(cells))
        for pair_key, pair in data["pairs"].items():
            pair_name = pair_key.replace("solo:", "")
            o = pair["paired_outcome"]
            dm = pair["delta_mean"]
            dm_str = "n/a" if dm is None else f"{dm:+.2f}"
            print(f"{pair_name}: delta moyen {dm_str} | W/T/L {o['wins']}/{o['ties']}/{o['losses']}")

    print("\n=== SOLO : Repartition des avions par moteur (compagnie 0) ===")
    for arm in arm_names:
        data = summary["air_engines"][f"solo:{arm}"]
        print(f"\nBras {arm} :")
        for seed in seeds:
            counts = data["per_seed"][seed]
            counts_str = ", ".join(f"moteur {k}: {v}" for k, v in sorted(counts.items())) if counts else "aucun"
            print(f"  Graine {seed}: {counts_str}")
        totals = data["total"]
        totals_str = ", ".join(f"moteur {k}: {v}" for k, v in sorted(totals.items())) if totals else "aucun"
        print(f"  Total {arm}: {totals_str}")

    if probe and "c82_probes" in summary:
        print("\n=== SONDE C82 : Facteurs k par moteur et arbitrage de choix ===")
        for arm in arm_names:
            p_data = summary["c82_probes"].get(f"solo:{arm}", {})
            print(f"\nBras {arm} :")
            print(f"  calls={p_data.get('calls_sum', 0)} differ={p_data.get('differ_sum', 0)}")
            factors = p_data.get("latest_factors", {})
            if factors:
                for eng in sorted(factors):
                    info = factors[eng]
                    print(f"  moteur {eng} ({info.get('name')}): k={info.get('k'):.3f} (sur {info.get('lines')} lignes)")
            else:
                print("  aucun facteur enregistre")


def run_selftest():
    """Test pur Python (sans OpenTTD) des fonctions de synthese et telemesure."""
    print("Execution du selftest...")

    # 1. Test du choix this_year/last_year selon le mois
    fake_lines = [
        {
            "mode": "air",
            "vehicles": 2,
            "capacity_by_cargo": {"0": 30, "2": 5},  # 35 places
            "profit_this_year_gbp": 12000.0,
            "profit_last_year_gbp": 8000.0,
        },
        {
            "mode": "air",
            "vehicles": 3,
            "capacity_by_cargo": {"0": 65},          # 65 places
            "profit_this_year_gbp": 18000.0,
            "profit_last_year_gbp": 14000.0,
        },
        {
            "mode": "road",                          # non-aerien, doit etre ignore
            "vehicles": 5,
            "capacity_by_cargo": {"0": 100},
            "profit_this_year_gbp": 5000.0,
            "profit_last_year_gbp": 4000.0,
        }
    ]

    # Mois 12 -> this_year
    res_dec = _extract_air_metrics_from_lines(fake_lines, 12)
    assert res_dec["air_lines"] == 2, f"Expected 2 lines, got {res_dec['air_lines']}"
    assert res_dec["air_planes"] == 5, f"Expected 5 planes, got {res_dec['air_planes']}"
    assert res_dec["air_seats"] == 100, f"Expected 100 seats, got {res_dec['air_seats']}"
    assert res_dec["air_profit"] == 30000.0, f"Expected 30000.0, got {res_dec['air_profit']}"
    assert res_dec["air_profit_source"] == "this_year"
    assert res_dec["air_profit_per_seat"] == 300.0, f"Expected 300.0, got {res_dec['air_profit_per_seat']}"
    assert res_dec["air_planes_per_line"] == 2.5, f"Expected 2.5, got {res_dec['air_planes_per_line']}"

    # Mois 6 -> last_year
    res_jun = _extract_air_metrics_from_lines(fake_lines, 6)
    assert res_jun["air_profit"] == 22000.0, f"Expected 22000.0, got {res_jun['air_profit']}"
    assert res_jun["air_profit_source"] == "last_year"
    assert res_jun["air_profit_per_seat"] == 220.0, f"Expected 220.0, got {res_jun['air_profit_per_seat']}"

    # 2. Test du comptage victoires / ex aequo / defaites
    diffs = [10.5, 0.0, -5.2, 3.0, 0.0]
    outcomes = _paired_outcome(diffs)
    assert outcomes["wins"] == 2, f"Expected 2 wins, got {outcomes['wins']}"
    assert outcomes["ties"] == 2, f"Expected 2 ties, got {outcomes['ties']}"
    assert outcomes["losses"] == 1, f"Expected 1 loss, got {outcomes['losses']}"

    # 3. Test de parsing de la sonde C82
    fake_log = (
        "dbg: [script] [0] OPEX 1972-1-1 C69_BOTTLENECK phase=c82_factor year=1972 engine=30 name=Bakewell_Luckett_LB-8 lines=2 k=1.8500\n"
        "dbg: [script] [0] OPEX 1973-1-1 C69_BOTTLENECK phase=c82_factor year=1973 engine=30 name=Bakewell_Luckett_LB-8 lines=3 k=1.9200\n"
        "dbg: [script] [0] OPEX 1973-1-1 C69_BOTTLENECK phase=c82_factor year=1973 engine=32 name=Darwin_300 lines=1 k=1.1500\n"
        "dbg: [script] [0] OPEX 1972-1-1 C69_BOTTLENECK phase=c82_choice_summary year=1972 calls=12 differ=4\n"
        "dbg: [script] [0] OPEX 1973-1-1 C69_BOTTLENECK phase=c82_choice_summary year=1973 calls=8 differ=2\n"
        "dbg: [script] [0] OPEX 1972-3-15 C69_BOTTLENECK phase=c82_choice raw=32 cal=30 k_raw=1.0000 k_cal=1.8500 c72=0\n"
    )
    probe = parse_c82_probe(fake_log)
    assert 30 in probe["factors"] and probe["factors"][30]["k"] == 1.9200, "Expected engine 30 k=1.9200"
    assert 32 in probe["factors"] and probe["factors"][32]["k"] == 1.1500, "Expected engine 32 k=1.1500"
    assert probe["calls_sum"] == 20, f"Expected calls_sum=20, got {probe['calls_sum']}"
    assert probe["differ_sum"] == 6, f"Expected differ_sum=6, got {probe['differ_sum']}"
    assert len(probe["choice_samples"]) == 1

    # 4. Test synthese
    seeds = [100, 42]
    arms = ["base", "fl1"]
    fake_latest = {
        ("solo", "base", 100): {
            "opex_profit_year": 10000, "opex_company_value": 50000, "opex_vehicles": 10,
            "air_profit": 5000, "air_profit_per_seat": 50.0, "air_planes_per_line": 1.5,
            "opex_air_engines": {30: 2},
        },
        ("solo", "base", 42): {
            "opex_profit_year": 12000, "opex_company_value": 60000, "opex_vehicles": 12,
            "air_profit": 6000, "air_profit_per_seat": 60.0, "air_planes_per_line": 2.0,
            "opex_air_engines": {30: 3},
        },
        ("solo", "fl1", 100): {
            "opex_profit_year": 11000, "opex_company_value": 55000, "opex_vehicles": 10,
            "air_profit": 5500, "air_profit_per_seat": 55.0, "air_planes_per_line": 1.5,
            "opex_air_engines": {30: 2},
        },
        ("solo", "fl1", 42): {
            "opex_profit_year": 11500, "opex_company_value": 58000, "opex_vehicles": 14,
            "air_profit": 5800, "air_profit_per_seat": 58.0, "air_planes_per_line": 2.2,
            "opex_air_engines": {30: 4},
        },
    }
    summary = summarize(fake_latest, seeds, arms)
    pair = summary["by_metric"]["profit_year"]["pairs"]["solo:fl1-base"]
    assert pair["deltas"][100] == 1000
    assert pair["deltas"][42] == -500
    assert pair["paired_outcome"] == {"wins": 1, "ties": 0, "losses": 1}

    print("Selftest REUSSI avec succes !")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=DEFAULT_YEARS)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(DEFAULT_SEEDS))
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "diag_nuit_air_solo.json")
    parser.add_argument("--arms", nargs="+", choices=list(ARM_SPECS.keys()), default=list(DEFAULT_ARMS))
    parser.add_argument("--probe", action="store_true", help="Active probe_portfolio sur tous les bras")
    parser.add_argument("--selftest", action="store_true", help="Execute le test unitaire interne pur Python")
    args = parser.parse_args()

    if args.selftest:
        run_selftest()
        return

    if not _HAS_OPENTTDLAB:
        sys.exit("openttdlab n'est pas installe sur l'hote. Lancez dans l'environnement docker.")

    active_arms = {}
    for arm in args.arms:
        base_settings = list(ARM_SPECS[arm])
        if args.probe:
            base_settings.append(("probe_portfolio", 1))
        active_arms[arm] = tuple(base_settings)

    enable_savegame_cleanup()
    cfg = make_cfg(STARTING_YEAR)
    days = 365 * args.years
    experiments = []
    for arm, settings in active_arms.items():
        opex = local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", settings)
        for seed in args.seeds:
            experiments.append({
                "bench_context": "solo",
                "bench_arm": arm,
                "seed": seed,
                "days": days,
                "openttd_config": cfg,
                "ais": (opex,),
            })

    print(f"=== DIAG NUIT AIR : {len(args.seeds)} graines x {args.years} ans, {len(active_arms)} bras, SOLO SEULEMENT ===")
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        experiments=experiments, max_workers=args.workers, result_processor=keep,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    latest = _latest_by_run(rows)
    expected = len(active_arms) * len(args.seeds)
    if len(latest) != expected:
        raise RuntimeError(f"runs finaux incomplets: {len(latest)}/{expected}")

    summary = summarize(latest, args.seeds, list(active_arms.keys()), probe=args.probe)
    payload = {
        "openttd_version": OPENTTD_VERSION,
        "starting_year": STARTING_YEAR,
        "years": args.years,
        "seeds": args.seeds,
        "arms": {arm: dict(settings) for arm, settings in active_arms.items()},
        "probe": args.probe,
        "summary": summary,
        "final_runs": [latest[key] for key in sorted(latest)],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with args.out.with_suffix(".jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")
    _print_summary(summary, args.seeds, list(active_arms.keys()), probe=args.probe)
    print(f"\nJSON:  {args.out}")


if __name__ == "__main__":
    main()
