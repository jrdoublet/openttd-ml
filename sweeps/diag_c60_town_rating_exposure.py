"""Diagnostic et chiffrage d'exposition C60 : Notes municipales et refus de gare.

Analyse l'exposition de l'IA aux refus d'autorite locale (ERR_LOCAL_AUTHORITY_REFUSES /
TOWN_RATING_VERY_POOR / TOWN_RATING_APPALLING) a partir des traces d'evenements
et des fichiers de resultats.

Usage :
    python sweeps/diag_c60_town_rating_exposure.py --selftest
    python sweeps/diag_c60_town_rating_exposure.py --file results/diag_air_afail_rect_end_6y_5seeds.json
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
import bench_v2
from bench_v2 import (
    OPENGFX_VERSION,
    OPENTTD_VERSION,
    build_arms,
    enable_savegame_cleanup,
    experiments,
    keep,
    paired_comparisons,
    resolve_opex_arm_settings,
    summarise,
    write_json_atomically,
)

_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

LIVE_ARM = "OpexAI[probe_portfolio=1]"
CONTROL_ARM = "C60_CONTROL"
FILTER_ARM = "C60_FILTER"

EVENT_EXPOSURE_RE = re.compile(
    r"OPEX (\d+-\d+-\d+) TOWN_RATING_EXPOSURE\s+mode=(\w+)\s+phase=(\w+)\s+town=(\d+)\s+rating=(\d+)\s+rating_name=(\w+)\s+allow=(\d+)"
)

SUMMARY_RE = re.compile(
    r"OPEX (\d+-\d+-\d+) C60_TOWN_RATING_SUMMARY\s+year=(\d+)\s+checks=(\d+)\s+none=(\d+)\s+ok=(\d+)\s+very_poor=(\d+)\s+appalling=(\d+)\s+road_checks=(\d+)\s+road_refused=(\d+)\s+rail_checks=(\d+)\s+rail_refused=(\d+)\s+air_checks=(\d+)\s+air_refused=(\d+)"
)

DISCARD_REFUSAL_RE = re.compile(
    r"OPEX (\d+-\d+-\d+) PROJECT_DISCARD\s+rank=(\d+)\s+mode=(\w+)\s+src=(\d+)\s+dst=(\d+)\s+reason=(town_rating_refusal|town_rating_appalling)"
)


def parse_town_rating_events(text):
    """Extrait les evenements d'exposition et de rejet municipal d'une trace stdout."""
    exposures = []
    summaries = []
    discards = []

    for line in (text or "").splitlines():
        m_exp = EVENT_EXPOSURE_RE.search(line)
        if m_exp:
            exposures.append({
                "date": m_exp.group(1),
                "mode": m_exp.group(2),
                "phase": m_exp.group(3),
                "town": int(m_exp.group(4)),
                "rating": int(m_exp.group(5)),
                "rating_name": m_exp.group(6),
                "allow": int(m_exp.group(7)) == 1,
            })
            continue

        m_sum = SUMMARY_RE.search(line)
        if m_sum:
            summaries.append({
                "date": m_sum.group(1),
                "year": int(m_sum.group(2)),
                "checks": int(m_sum.group(3)),
                "none": int(m_sum.group(4)),
                "ok": int(m_sum.group(5)),
                "very_poor": int(m_sum.group(6)),
                "appalling": int(m_sum.group(7)),
                "road_checks": int(m_sum.group(8)),
                "road_refused": int(m_sum.group(9)),
                "rail_checks": int(m_sum.group(10)),
                "rail_refused": int(m_sum.group(11)),
                "air_checks": int(m_sum.group(12)),
                "air_refused": int(m_sum.group(13)),
            })
            continue

        m_disc = DISCARD_REFUSAL_RE.search(line)
        if m_disc:
            discards.append({
                "date": m_disc.group(1),
                "rank": int(m_disc.group(2)),
                "mode": m_disc.group(3),
                "src": int(m_disc.group(4)),
                "dst": int(m_disc.group(5)),
                "reason": m_disc.group(6),
            })

    return {
        "exposures": exposures,
        "summaries": summaries,
        "discards": discards,
    }


def live_exposure_metrics(text):
    """Resume une trace courante C60.

    Le ledger C60 n'est pas remis a zero apres le rapport annuel : les lignes
    C60_TOWN_RATING_SUMMARY sont cumulatives. On conserve donc la derniere.
    Les lignes TOWN_RATING_EXPOSURE sont emises sans decision_log uniquement
    pour les refus, ce qui permet de ventiler les refus par phase.
    """
    parsed = parse_town_rating_events(text)
    final_summary = parsed["summaries"][-1] if parsed["summaries"] else {
        "checks": 0,
        "none": 0,
        "ok": 0,
        "very_poor": 0,
        "appalling": 0,
        "road_checks": 0,
        "road_refused": 0,
        "rail_checks": 0,
        "rail_refused": 0,
        "air_checks": 0,
        "air_refused": 0,
    }
    refused_by_mode_phase = Counter(
        (event["mode"], event["phase"])
        for event in parsed["exposures"]
        if not event["allow"]
    )
    return {
        "final_summary": final_summary,
        "refused_by_mode_phase": {
            f"{mode}:{phase}": count
            for (mode, phase), count in sorted(refused_by_mode_phase.items())
        },
        "refused_event_count": sum(refused_by_mode_phase.values()),
        "discard_count": len(parsed["discards"]),
    }


def run_live_exposure(years, seeds, out, max_workers):
    bench_v2.CHECKPOINT_PATH = out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_savegame_cleanup()
    built = build_arms([LIVE_ARM])
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=max_workers,
        result_processor=keep,
        experiments=experiments(built, seeds, years, 1, 1970),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    summary = summarise(rows, expected_last_year=1970 + years - 1)
    per_seed = []
    totals = {
        "checks": 0,
        "road_checks": 0,
        "road_refused": 0,
        "rail_checks": 0,
        "rail_refused": 0,
        "air_checks": 0,
        "air_refused": 0,
    }
    phases = Counter()
    for record in summary:
        output = record.pop("openttd_output", "") or ""
        metrics = live_exposure_metrics(output)
        final = metrics["final_summary"]
        for key in totals:
            totals[key] += int(final.get(key, 0))
        phases.update(metrics["refused_by_mode_phase"])
        per_seed.append({
            "seed": record["seed"],
            "run_ok": record["run_ok"],
            "failure_reason": record.get("failure_reason"),
            "last_date": record.get("last_date"),
            "company_value": record.get("company_value"),
            "profit_year": record.get("profit_year"),
            "exposure": metrics,
        })
    failed = [entry for entry in per_seed if not entry["run_ok"]]
    payload = {
        "arm": LIVE_ARM,
        "years": years,
        "seeds": list(seeds),
        "failed_run_count": len(failed),
        "totals": totals,
        "refused_by_mode_phase": dict(sorted(phases.items())),
        "per_seed": per_seed,
    }
    write_json_atomically(out, payload)
    print("failed", len(failed), "out", out)
    print("checks", totals["checks"])
    for mode in ("road", "rail", "air"):
        checks = totals[f"{mode}_checks"]
        refused = totals[f"{mode}_refused"]
        rate = (100.0 * refused / checks) if checks else 0.0
        print(f"{mode:4s} checks={checks:8d} refused={refused:6d} rate={rate:8.4f}%")
    if phases:
        print("refused phases")
        for key, count in sorted(phases.items()):
            print(f"  {key:32s} {count:6d}")
    if failed:
        raise SystemExit(f"diagnostic C60 invalide: {len(failed)} run(s) en echec")
    return payload


def _filter_variant_descriptor(temp_root):
    """Copie l'IA et force uniquement C60_TOWN_RATING_FILTER pour un banc A/B."""
    temp_ai = Path(temp_root) / "OpexAI-C60-filter"
    shutil.copytree(ROOT / "ai" / "OpexAI", temp_ai)
    settings_path = temp_ai / "settings.nut"
    text = settings_path.read_text(encoding="utf-8")
    needle = "  C60_TOWN_RATING_FILTER = false;"
    replacement = "  C60_TOWN_RATING_FILTER = true;"
    if text.count(needle) != 1:
        raise RuntimeError(
            "C60: impossible de construire le bras filtre, "
            f"occurrences attendues=1 observees={text.count(needle)}"
        )
    settings_path.write_text(text.replace(needle, replacement, 1), encoding="utf-8")
    settings = resolve_opex_arm_settings(LIVE_ARM)
    return local_folder(
        str(temp_ai),
        "OpexAI",
        tuple(settings["effective"].items()),
    )


def _aggregate_exposure_from_summary(summary):
    by_arm = {}
    for record in summary:
        arm = record["arm"]
        output = record.get("openttd_output", "") or ""
        metrics = live_exposure_metrics(output)
        entry = by_arm.setdefault(arm, {
            "reported_checks": Counter(),
            "refused_by_mode_phase": Counter(),
            "refused_event_count": 0,
        })
        final = metrics["final_summary"]
        for key in (
            "checks", "road_checks", "road_refused",
            "rail_checks", "rail_refused", "air_checks", "air_refused",
        ):
            entry["reported_checks"][key] += int(final.get(key, 0))
        entry["refused_by_mode_phase"].update(metrics["refused_by_mode_phase"])
        entry["refused_event_count"] += metrics["refused_event_count"]
    serializable = {}
    for arm, entry in by_arm.items():
        serializable[arm] = {
            "reported_checks": dict(entry["reported_checks"]),
            "refused_by_mode_phase": dict(sorted(entry["refused_by_mode_phase"].items())),
            "refused_event_count": entry["refused_event_count"],
        }
    return serializable


def run_filter_comparison(years, seeds, out, max_workers):
    """Compare le code livre au meme code avec uniquement le filtre C60 force a 1."""
    bench_v2.CHECKPOINT_PATH = out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists():
        bench_v2.CHECKPOINT_PATH.unlink()
    enable_savegame_cleanup()
    control = build_arms([LIVE_ARM])[LIVE_ARM]
    with tempfile.TemporaryDirectory(prefix="openttd-ml-c60-") as temp_root:
        filtered = _filter_variant_descriptor(temp_root)
        arms = {FILTER_ARM: filtered, CONTROL_ARM: control}
        rows = list(run_experiments(
            openttd_version=OPENTTD_VERSION,
            opengfx_version=OPENGFX_VERSION,
            max_workers=max_workers,
            result_processor=keep,
            experiments=experiments(arms, seeds, years, 1, 1970),
            ai_libraries=(
                bananas_ai_library("51554648", "Queue.FibonacciHeap"),
                bananas_ai_library("5046524c", "Pathfinder.Rail"),
            ),
        ))
    summary = summarise(rows, expected_last_year=1970 + years - 1)
    failed = [record for record in summary if not record["run_ok"]]
    exposure = _aggregate_exposure_from_summary(summary)
    metrics = (
        "company_value",
        "profit_year",
        "n_vehicles",
        "n_stations",
        "observed_opcodes_total",
    )
    paired = paired_comparisons(summary, [FILTER_ARM, CONTROL_ARM], metrics)
    clean_summary = []
    for record in summary:
        clean = dict(record)
        clean.pop("openttd_output", None)
        clean_summary.append(clean)
    payload = {
        "design": (
            "A/B temporaire: meme source et memes reglages probe_portfolio=1; "
            "le bras C60_FILTER ne differe que par "
            "C60_TOWN_RATING_FILTER=false -> true dans une copie /tmp."
        ),
        "years": years,
        "seeds": list(seeds),
        "arms": [FILTER_ARM, CONTROL_ARM],
        "failed_run_count": len(failed),
        "exposure": exposure,
        "summary": clean_summary,
        "paired_comparisons": paired,
    }
    write_json_atomically(out, payload)
    print("failed", len(failed), "out", out)
    if paired:
        result = paired[0]["metrics"]
        for metric in metrics:
            item = result[metric]
            print(
                f"{metric:24s} delta={item['mean_difference']} "
                f"wins={item['arm_a_beats_arm_b']} losses={item['arm_a_loses_to_arm_b']} "
                f"ties={item['ties']} sign_p={item['sign_test_p']}"
            )
    for arm in (FILTER_ARM, CONTROL_ARM):
        entry = exposure.get(arm, {})
        print(
            arm,
            "refused_events=", entry.get("refused_event_count", 0),
            "phases=", entry.get("refused_by_mode_phase", {}),
        )
    if failed:
        raise SystemExit(f"diagnostic filtre C60 invalide: {len(failed)} run(s) en echec")
    return payload


def analyze_historical_air_failures(json_path):
    """Quantifie les echecs ERR_LOCAL_AUTHORITY_REFUSES dans les diagnostics d'echecs.

    Attention : en OpenTTD, ERR_LOCAL_AUTHORITY_REFUSES a la construction d'un aeroport
    couvre a la fois le refus par note municipale (<= -200) ET le depassement du plafond
    de bruit aeroportuaire (station_noise_level). Ces comptages mesurent donc l'ensemble
    des refus municipaux (bruit + note) et ne permettent pas d'etablir a eux seuls
    une note APPALLING ni de justifier un filtre fonde exclusivement sur la note.
    """
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {json_path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    summary = data.get("summary", {})
    attempts = summary.get("attempts", 0)
    failures = summary.get("failures", 0)
    errors = summary.get("errors", {})
    refuses = errors.get("ERR_LOCAL_AUTHORITY_REFUSES", 0)

    # Analyse des runs individuels
    runs = data.get("runs", [])
    refusal_details = []
    attempts_per_seed = Counter()
    refuses_per_seed = Counter()
    consecutive_repeats = Counter()

    for run in runs:
        seed = run.get("seed")
        last_line_index = None
        for att in run.get("attempts", []):
            attempts_per_seed[seed] += 1
            err_name = att.get("error_name")
            line_idx = att.get("line_index")
            if err_name == "ERR_LOCAL_AUTHORITY_REFUSES":
                refuses_per_seed[seed] += 1
                refusal_details.append({
                    "seed": seed,
                    "year": att.get("year"),
                    "reason": att.get("reason"),
                    "line_index": line_idx,
                    "actual_cost": att.get("actual_cost", 0),
                })
                if last_line_index == line_idx:
                    consecutive_repeats[(seed, line_idx)] += 1
            last_line_index = line_idx

    refusal_rate_attempts = (refuses / attempts * 100) if attempts else 0.0
    refusal_rate_failures = (refuses / failures * 100) if failures else 0.0

    spikes_str_keys = {f"seed_{k[0]}_line_{k[1]}": v for k, v in consecutive_repeats.items()}

    return {
        "source": str(path),
        "total_attempts": attempts,
        "total_failures": failures,
        "refusal_count": refuses,
        "refusal_pct_attempts": refusal_rate_attempts,
        "refusal_pct_failures": refusal_rate_failures,
        "refuses_per_seed": dict(refuses_per_seed),
        "attempts_per_seed": dict(attempts_per_seed),
        "consecutive_repeat_spikes": spikes_str_keys,
        "sample_failures": refusal_details[:5],
        "caveat": (
            "ERR_LOCAL_AUTHORITY_REFUSES regroupe note municipale et plafond de bruit ; "
            "ce comptage n'etablit pas a lui seul une note APPALLING ni ne justifie un filtre note seul."
        ),
    }


def run_selftest():
    """Auto-test validant les expressions regulieres, le parsing et le calcul de metriques."""
    sample_log = """
OPEX 1970-02-01 TOWN_RATING_EXPOSURE mode=road phase=candidate_gen town=5 rating=0 rating_name=none allow=1
OPEX 1970-02-01 TOWN_RATING_EXPOSURE mode=road phase=candidate_gen town=8 rating=4 rating_name=mediocre allow=1
OPEX 1970-03-15 TOWN_RATING_EXPOSURE mode=road phase=build_precheck town=12 rating=1 rating_name=appalling allow=0
OPEX 1970-03-15 PROJECT_DISCARD rank=0 mode=road src=5 dst=12 reason=town_rating_refusal
OPEX 1970-04-10 TOWN_RATING_EXPOSURE mode=air phase=find_site town=20 rating=2 rating_name=very_poor allow=0
OPEX 1970-04-10 TOWN_RATING_EXPOSURE mode=air phase=find_site town=21 rating=1 rating_name=appalling allow=0
OPEX 1970-04-10 PROJECT_DISCARD rank=1 mode=air src=100 dst=200 reason=town_rating_appalling
OPEX 1971-01-01 C60_TOWN_RATING_SUMMARY year=1970 checks=150 none=130 ok=15 very_poor=3 appalling=2 road_checks=100 road_refused=2 rail_checks=20 rail_refused=0 air_checks=30 air_refused=3
"""
    parsed = parse_town_rating_events(sample_log)
    assert len(parsed["exposures"]) == 5, f"Expected 5 exposures, got {len(parsed['exposures'])}"
    assert len(parsed["summaries"]) == 1, f"Expected 1 summary, got {len(parsed['summaries'])}"
    assert len(parsed["discards"]) == 2, f"Expected 2 discards, got {len(parsed['discards'])}"

    exp0 = parsed["exposures"][0]
    assert exp0["town"] == 5 and exp0["allow"] is True and exp0["rating_name"] == "none"

    exp2 = parsed["exposures"][2]
    assert exp2["town"] == 12 and exp2["allow"] is False and exp2["rating_name"] == "appalling"

    s0 = parsed["summaries"][0]
    assert s0["checks"] == 150
    assert s0["very_poor"] == 3
    assert s0["appalling"] == 2
    assert s0["road_refused"] == 2
    assert s0["air_refused"] == 3

    live = live_exposure_metrics(sample_log)
    assert live["final_summary"]["road_refused"] == 2
    assert live["refused_by_mode_phase"]["road:build_precheck"] == 1
    assert live["refused_by_mode_phase"]["air:find_site"] == 2
    assert live["refused_event_count"] == 3

    candidates = (ROOT / "ai" / "OpexAI" / "candidates.nut").read_text(encoding="utf-8")
    probe_start = candidates.index("function OpexC60ObserveTownRating")
    probe_end = candidates.index("\nfunction ", probe_start)
    probe = candidates[probe_start:probe_end]
    assert "local allowed = OpexTownRatingAllowStation(townId);" in probe
    assert (
        "local allowed = (rating == AITown.TOWN_RATING_NONE || "
        "rating > AITown.TOWN_RATING_VERY_POOR);" not in probe
    )

    print("Selftest passe avec succes (5 exposures, 1 summary, 2 discards valides).")


def main():
    parser = argparse.ArgumentParser(description="Analyse de l'exposition aux notes municipales (C60).")
    parser.add_argument("--selftest", action="store_true", help="Execute l'auto-test unitaire interne.")
    parser.add_argument("--file", type=str, help="Chemin vers un fichier JSON de diagnostic a analyser.")
    parser.add_argument("--live", action="store_true", help="Mesure l'exposition C60 sur l'arbre courant.")
    parser.add_argument(
        "--compare-filter",
        action="store_true",
        help="Compare le code livre a une copie temporaire avec uniquement le filtre C60 force a 1.",
    )
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 999, 1234, 5678])
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "diag_c60_current_exposure_6y_5seeds.json")
    args = parser.parse_args()

    if args.selftest:
        run_selftest()
        return 0

    if args.file:
        res = analyze_historical_air_failures(args.file)
        print(json.dumps(res, indent=2))
        return 0

    if args.live:
        run_live_exposure(args.years, args.seeds, args.out, args.max_workers)
        return 0

    if args.compare_filter:
        run_filter_comparison(args.years, args.seeds, args.out, args.max_workers)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
