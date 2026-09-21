"""Borne le biais C49 sans conclure sur la valeur de jeu.

`portfolio_max_batch=4` a ete REFUTE au banc (-3,8 % de valeur, -7,9 % de gares). Il est
employe ici uniquement comme instrument de diagnostic pour tenter des rangs suivants ; ce script
ne propose pas son adoption et ne conclut rien sur la valeur de jeu. --selftest est pur Python.
"""
import argparse
import re
import sys
from pathlib import Path

import openttdlab
from openttdlab import bananas_ai_library, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_v2 import (
    OPENGFX_VERSION, OPENTTD_VERSION, build_arms, enable_savegame_cleanup,
    experiments, keep, summarise, write_json_atomically,
)
import bench_v2


_real_check_output = openttdlab.subprocess.check_output


def _check_output_with_script_debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(arg).startswith("-vnull") for arg in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)


openttdlab.subprocess.check_output = _check_output_with_script_debug

CONTROL_ARM = "OpexAI[c49_scarcity_ledger=1]"
TREATMENT_ARM = "OpexAI[c49_scarcity_ledger=1,portfolio_max_batch=4]"
ARMS = (CONTROL_ARM, TREATMENT_ARM)
SEEDS = (100, 12345, 42, 7, 999)
EVENT_RE = re.compile(r"OPEX \d+-\d+-\d+ C49_SCARCITY\s*(.*)")
RAW_RESOURCES = ("cash", "vehicles", "site", "decision_attempted", "decision_unattempted")
SHARE_RESOURCES = ("cash", "vehicles", "site", "decision")
WARNINGS = (
    "Les deux bras n'ont pas la meme trajectoire : portfolio_max_batch change le comportement ; p_map est un taux conditionnel transpose, pas une mesure du temoin.",
    "Dans le bras traitement, les rangs tentes sont plus profonds que la cible typique du temoin : p_map peut etre surestime si les rangs profonds echouent plus souvent.",
    "La correction est une borne indicative, pas une mesure : elle dit de combien decision pourrait au plus etre gonfle.",
)


def parse_fields(fields):
    return dict(token.split("=", 1) for token in fields.split() if "=" in token)


def parse_events(output):
    return [parse_fields(fields) for fields in EVENT_RE.findall(output or "")]


def empty_counts():
    return {resource: 0 for resource in RAW_RESOURCES}


def event_counts(event):
    return {resource: int(event.get(resource, 0)) for resource in RAW_RESOURCES}


def add_counts(total, counts):
    for resource in RAW_RESOURCES:
        total[resource] += counts[resource]


def public_counts(counts):
    return {**counts, "decision": counts["decision_attempted"] + counts["decision_unattempted"]}


def corrected_public_counts(counts):
    """Les composantes attempted/unattempted ne decrivent plus un fait apres correction."""
    return {resource: public_counts(counts)[resource] for resource in SHARE_RESOURCES}


def shares(counts):
    counts = public_counts(counts)
    denominator = sum(counts[resource] for resource in SHARE_RESOURCES)
    return {resource: (counts[resource] / denominator if denominator else None)
            for resource in SHARE_RESOURCES}


def aggregate_events(events):
    """Agrege les lignes annuelles deja extraites d'une UNIQUE capture stdout de partie."""
    annual = {}
    for event in events:
        if event.get("phase") != "annual" or "year" not in event:
            continue
        year = int(event["year"])
        entry = annual.setdefault(year, {"passes": 0, "none": 0, "counts": empty_counts()})
        entry["passes"] += int(event.get("passes", 0))
        entry["none"] += int(event.get("none", 0))
        add_counts(entry["counts"], event_counts(event))
    return annual


def sum_entries(entries):
    total = {"passes": 0, "none": 0, "counts": empty_counts()}
    for entry in entries:
        total["passes"] += entry["passes"]
        total["none"] += entry["none"]
        add_counts(total["counts"], entry["counts"])
    return total


def raw_entry(entry):
    return {"passes": entry["passes"], "none": entry["none"],
            "counts": public_counts(entry["counts"]), "shares": shares(entry["counts"])}


def p_map(treatment_counts):
    denominator = treatment_counts["site"] + treatment_counts["decision_attempted"]
    return treatment_counts["site"] / denominator if denominator else None


def corrected_counts(control_counts, map_rate):
    if map_rate is None:
        return None
    corrected = dict(control_counts)
    reservoir = control_counts["decision_unattempted"]
    corrected["decision_attempted"] += reservoir * (1 - map_rate)
    corrected["site"] += reservoir * map_rate
    corrected["decision_unattempted"] = 0
    return corrected


def bound_entry(control, treatment):
    """Expose les comptes bruts, p_map, puis les parts temoin brutes/corrigees et leur ecart."""
    rate = p_map(treatment["counts"])
    corrected = corrected_counts(control["counts"], rate)
    raw_shares = shares(control["counts"])
    corrected_shares = shares(corrected) if corrected is not None else {
        resource: None for resource in SHARE_RESOURCES
    }
    return {
        "control_raw": raw_entry(control),
        "treatment_raw": raw_entry(treatment),
        "p_map": rate,
        "control_corrected_counts": corrected_public_counts(corrected) if corrected is not None else None,
        "control_raw_shares": raw_shares,
        "control_corrected_shares": corrected_shares,
        "corrected_minus_raw_shares": {
            resource: (corrected_shares[resource] - raw_shares[resource]
                       if corrected_shares[resource] is not None else None)
            for resource in SHARE_RESOURCES
        },
    }


def paired_bound(control_annual, treatment_annual):
    years = sorted(set(control_annual) | set(treatment_annual))
    by_year = []
    for year in years:
        control = control_annual.get(year, {"passes": 0, "none": 0, "counts": empty_counts()})
        treatment = treatment_annual.get(year, {"passes": 0, "none": 0, "counts": empty_counts()})
        by_year.append({"year": year, **bound_entry(control, treatment)})
    return {
        "by_year": by_year,
        "cumulative": bound_entry(sum_entries(control_annual.values()), sum_entries(treatment_annual.values())),
    }


def run_selftest():
    """Deux bras, deux annees desequilibrees : pondération, correction et denominateur nul."""
    control = aggregate_events(parse_events("\n".join((
        "OPEX 1971-1-1 C49_SCARCITY phase=annual year=1971 passes=20 cash=10 vehicles=0 site=1 decision_attempted=1 decision_unattempted=8 none=0 regime=cash",
        "OPEX 1972-1-1 C49_SCARCITY phase=annual year=1972 passes=10 cash=1 vehicles=0 site=0 decision_attempted=1 decision_unattempted=8 none=0 regime=decision",
    ))))
    treatment = aggregate_events(parse_events("\n".join((
        "OPEX 1971-1-1 C49_SCARCITY phase=annual year=1971 passes=20 cash=0 vehicles=0 site=1 decision_attempted=1 decision_unattempted=0 none=18 regime=site",
        "OPEX 1972-1-1 C49_SCARCITY phase=annual year=1972 passes=100 cash=0 vehicles=0 site=1 decision_attempted=99 decision_unattempted=0 none=0 regime=decision",
    ))))
    result = paired_bound(control, treatment)
    first, second = result["by_year"]
    assert first["p_map"] == 0.5
    assert first["control_corrected_counts"]["decision"] == 5.0
    assert first["control_corrected_counts"]["site"] == 5.0
    assert result["cumulative"]["p_map"] == 2 / 102
    assert result["cumulative"]["p_map"] != (first["p_map"] + second["p_map"]) / 2

    null_treatment = aggregate_events(parse_events(
        "OPEX 1971-1-1 C49_SCARCITY phase=annual year=1971 passes=1 cash=1 vehicles=0 site=0 decision_attempted=0 decision_unattempted=0 none=0 regime=cash"
    ))
    null_result = paired_bound({1971: control[1971]}, null_treatment)["by_year"][0]
    assert null_result["p_map"] is None
    assert null_result["control_corrected_counts"] is None
    print("selftest passed: p_map_y1=0.5; corrected_y1 decision=5.0 site=5.0; p_map_cumulative=0.0196078431372549; unweighted_year_mean=0.255; null_denominator=null")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        run_selftest()
        return
    if args.years <= 0 or not args.seeds or args.max_workers not in (1, 2, 3):
        parser.error("--years et --seeds non vides ; --max-workers vaut 1, 2 ou 3")
    if len(set(args.seeds)) != len(args.seeds):
        parser.error("--seeds ne doit pas contenir de doublon")

    out = args.out or ROOT / "results" / "diag_c49_bias_bound_6y_5seeds.json"
    bench_v2.CHECKPOINT_PATH = out.with_suffix(".jsonl")
    enable_savegame_cleanup()
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION, opengfx_version=OPENGFX_VERSION,
        max_workers=args.max_workers, result_processor=keep,
        experiments=experiments(build_arms(ARMS), args.seeds, args.years, 1, 1970),
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    summary = summarise(rows)
    by_arm_seed = {}
    for record in summary:
        # openttd_output est la capture complete repetee aux checkpoints : une seule lecture ici.
        by_arm_seed[record["arm"], record["seed"]] = aggregate_events(
            parse_events(record.get("openttd_output", ""))
        )

    per_seed = []
    all_control, all_treatment = {}, {}
    for seed in args.seeds:
        control = by_arm_seed.get((CONTROL_ARM, seed), {})
        treatment = by_arm_seed.get((TREATMENT_ARM, seed), {})
        per_seed.append({"seed": seed, **paired_bound(control, treatment)})
        for year, entry in control.items():
            all_control.setdefault(year, {"passes": 0, "none": 0, "counts": empty_counts()})
            all_control[year]["passes"] += entry["passes"]
            all_control[year]["none"] += entry["none"]
            add_counts(all_control[year]["counts"], entry["counts"])
        for year, entry in treatment.items():
            all_treatment.setdefault(year, {"passes": 0, "none": 0, "counts": empty_counts()})
            all_treatment[year]["passes"] += entry["passes"]
            all_treatment[year]["none"] += entry["none"]
            add_counts(all_treatment[year]["counts"], entry["counts"])

    failed = [{key: value for key, value in record.items() if key != "openttd_output"}
              for record in summary if not record["run_ok"]]
    payload = {
        "years": args.years, "seeds": args.seeds,
        "arms": {"control": CONTROL_ARM, "treatment": TREATMENT_ARM},
        "instrument_notice": "portfolio_max_batch=4 est refute au banc (-3,8 % valeur, -7,9 % gares) ; instrument diagnostique seulement, sans conclusion sur la valeur de jeu.",
        "warnings": list(WARNINGS),
        "per_seed": per_seed,
        "all_seeds": paired_bound(all_control, all_treatment),
        "failed_runs": failed, "failed_run_count": len(failed),
    }
    write_json_atomically(out, payload)
    print("failed", len(failed), "out", out)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
