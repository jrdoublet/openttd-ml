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
import sys

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

    print("Selftest passe avec succes (5 exposures, 1 summary, 2 discards valides).")


def main():
    parser = argparse.ArgumentParser(description="Analyse de l'exposition aux notes municipales (C60).")
    parser.add_argument("--selftest", action="store_true", help="Execute l'auto-test unitaire interne.")
    parser.add_argument("--file", type=str, help="Chemin vers un fichier JSON de diagnostic a analyser.")
    args = parser.parse_args()

    if args.selftest:
        run_selftest()
        return 0

    if args.file:
        res = analyze_historical_air_failures(args.file)
        print(json.dumps(res, indent=2))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
