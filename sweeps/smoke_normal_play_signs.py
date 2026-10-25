"""Smoke moteur du profil normal sans panneaux, independant du socle de banc.

Contrairement aux bancs economiques, ce diagnostic ne passe PAS par
benchmark_opex_settings : leur injection probes=2 est intentionnelle et doit
rester inchangee. Le bras normal emploie les defauts publies (probes=0), et
le temoin impose seulement probes=2 sur le meme code. Aucun verdict economique.

Docker PC (apres verification qu'aucun autre banc ne tourne) :
  docker run --rm --cpus=10 --memory=8g --memory-swap=8g \
    -v openttd-lab-home:/home/lab -v "${PWD}:/work" -w /work \
    openttd-lab:latest python3 sweeps/smoke_normal_play_signs.py \
    --out results/smoke_normal_play_signs_20261025.json
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_FAILURE_MARKERS = ("Your script made an error", "The script died unexpectedly")


def sign_records(chunks):
    signs = (chunks or {}).get("SIGN") or {}
    records = signs.values() if isinstance(signs, dict) else signs
    return [record for record in records if isinstance(record, dict)]


def capture_snapshot(row):
    name, seed, repetition = row["experiment"]["bench_run"]
    output = row.get("output") or ""
    chunks = row.get("chunks") or {}
    players = chunks.get("PLYR") or {}
    company = (players.get(0) or players.get("0")) if isinstance(players, dict) else None
    signs = sign_records(chunks)
    sign_types = Counter(str(sign.get("name", "")).split("|", 1)[0] for sign in signs)
    return ({
        "arm": name, "seed": seed, "repetition": repetition, "date": str(row.get("date")),
        "sign_count": len(signs),
        "sign_types": dict(sign_types),
        "sign_names": [str(record.get("name", "")) for record in signs][:10],
        "opex_company_present": isinstance(company, dict),
        "script_error": next((m for m in SCRIPT_FAILURE_MARKERS if m in output), None),
    },)


def summarize(rows, *, final_year=1970, years=1, require_freight=False):
    summary = {}
    for arm in ("normal_default", "benchmark_panels"):
        snapshots = sorted((r for r in rows if r["arm"] == arm), key=lambda r: r["date"])
        final = snapshots[-1] if snapshots else None
        summary[arm] = {
            "snapshot_count": len(snapshots),
            "last_date": final["date"] if final else None,
            "final_sign_count": final["sign_count"] if final else None,
            "max_sign_count": max((r["sign_count"] for r in snapshots), default=None),
            "final_sign_names": final["sign_names"] if final else [],
            "final_sign_types": final["sign_types"] if final else {},
            "company_present": bool(final and final["opex_company_present"]),
            "script_errors": sorted({r["script_error"] for r in snapshots if r["script_error"]}),
        }
    normal, control = summary["normal_default"], summary["benchmark_panels"]
    for item in (normal, control):
        # OpenTTDLab peut exposer le dernier snapshot au 01/01 suivant (1 an)
        # ou le 01/12 de l'annee finale (3 ans, 36 autosaves). Exiger tous les
        # mois attendus et un snapshot au moins au debut de decembre final.
        item["complete"] = bool(item["snapshot_count"] >= 12 * years
                                and item["company_present"] and item["last_date"]
                                and f"{final_year}-12-01" <= item["last_date"]
                                <= f"{final_year + 1}-01-31"
                                and not item["script_errors"])
    verdict = (normal["complete"] and control["complete"]
               and normal["max_sign_count"] == 0 and control["max_sign_count"] > 0)
    if require_freight:
        # Prove that VS/VL have actually been exercised in the diagnostic arm,
        # not merely that both arms completed with no freight vehicles.
        freight_types = control["final_sign_types"]
        verdict = verdict and freight_types.get("VS", 0) > 0 and freight_types.get("VL", 0) > 0
    return summary, bool(verdict)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--years", type=int, default=1)
    parser.add_argument("--require-freight", action="store_true")
    args = parser.parse_args()
    if args.years <= 0:
        parser.error("--years must be positive")

    # Imports seulement dans le runtime OpenTTDLab, pas dans les tests hote.
    from openttdlab import bananas_ai_library, local_folder, run_experiments
    from bench_v2 import OPENTTD_VERSION, OPENGFX_VERSION, make_cfg
    arms = {
        "normal_default": local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", ()),
        "benchmark_panels": local_folder(str(ROOT / "ai" / "OpexAI"), "OpexAI", (("probes", 2),)),
    }
    experiments = [
        {"seed": args.seed, "days": 365 * args.years, "openttd_config": make_cfg(1970, 8),
         "ais": (ai,), "bench_run": [arm, args.seed, 0]}
        for arm, ai in arms.items()
    ]
    rows = list(run_experiments(
        openttd_version=OPENTTD_VERSION,
        opengfx_version=OPENGFX_VERSION,
        max_workers=1,
        result_processor=capture_snapshot,
        experiments=experiments,
        ai_libraries=(
            bananas_ai_library("51554648", "Queue.FibonacciHeap"),
            bananas_ai_library("5046524c", "Pathfinder.Rail"),
        ),
    ))
    summary, passed = summarize(rows, final_year=1970 + args.years - 1, years=args.years,
                                require_freight=args.require_freight)
    payload = {
        "purpose": "diagnostic_only; not an economic A/B",
        "seed": args.seed, "years": args.years, "starting_year": 1970,
        "requires_freight_panel_exposure": args.require_freight,
        "map_size": 256, "settings": {"normal_default": "published defaults (probes=0)",
                                   "benchmark_panels": "probes=2"},
        "arms": summary, "pass": passed,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
