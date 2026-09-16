"""Analyse des événements passifs M3_EQUIP produits par equipment_roi_probe."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

PREFIX = "M3_EQUIP "

def _value(text):
    if text in ("true", "false"):
        return text == "true"
    try:
        return int(text)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return text

def parse_event(line):
    pos = line.find(PREFIX)
    if pos < 0:
        return None
    event = {}
    for token in line[pos + len(PREFIX):].strip().split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        event[key] = _value(value)
    return event if "mode" in event and "phase" in event else None

def collect_engine_events(engine_dir):
    events = []
    engine_dir = Path(engine_dir)
    if not engine_dir.exists():
        return events
    for path in sorted(engine_dir.glob("*.log")):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            event = parse_event(line)
            if event is not None:
                event["_log"] = path.name
                events.append(event)
    return events

def _mean(values):
    return sum(values) / len(values) if values else None

def analyse_events(events):
    by_mode = defaultdict(list)
    by_phase = Counter()
    for event in events:
        by_mode[str(event["mode"])].append(event)
        by_phase[f"{event['mode']}:{event['phase']}"] += 1
    modes = {}
    for mode, rows in sorted(by_mode.items()):
        comparison = [row for row in rows if "choices" in row]
        pre = [row for row in comparison if str(row.get("phase", "")).startswith("pre_admission")]
        post_refit = [row for row in rows if row.get("phase") == "post_refit"]
        diff_profit = [row for row in comparison if int(row.get("best_profit_id", -1)) >= 0 and int(row.get("selected", -1)) != int(row.get("best_profit_id", -1))]
        diff_roi = [row for row in comparison if int(row.get("best_roi_id", -1)) >= 0 and int(row.get("selected", -1)) != int(row.get("best_roi_id", -1))]
        profit_regrets = [
            float(row["best_profit"]) - float(row["selected_profit"])
            for row in comparison
            if float(row.get("selected_profit", -999999999)) > -900000000 and float(row.get("best_profit", -999999999)) > -900000000
        ]
        roi_regrets = [
            float(row["best_roi"]) - float(row["selected_roi"])
            for row in comparison
            if float(row.get("selected_roi", -1)) >= 0 and float(row.get("best_roi", -1)) >= 0
        ]
        cap_deltas = [int(row.get("capacity_delta", 0)) for row in post_refit]
        modes[mode] = {
            "events": len(rows),
            "comparison_events": len(comparison),
            "pre_admission_events": len(pre),
            "multi_choice_events": sum(int(row.get("choices", 0)) > 1 for row in comparison),
            "multi_viable_events": sum(int(row.get("viable", 0)) > 1 for row in comparison),
            "selected_differs_best_profit": len(diff_profit),
            "selected_differs_best_roi": len(diff_roi),
            "admission_flips": sum(int(row.get("admission_flip", 0)) for row in pre),
            "native_admission_flips": sum(int(row.get("native_admission_flip", 0)) for row in pre),
            "mean_profit_regret": _mean(profit_regrets),
            "max_profit_regret": max(profit_regrets) if profit_regrets else None,
            "mean_roi_regret": _mean(roi_regrets),
            "max_roi_regret": max(roi_regrets) if roi_regrets else None,
            "native_choices_total": sum(int(row.get("native_choices", 0)) for row in comparison),
            "refit_proxy_choices_total": sum(int(row.get("refit_proxy_choices", 0)) for row in comparison),
            "selected_refit_events": sum(int(row.get("selected_refit", 0)) for row in comparison),
            "post_refit_events": len(post_refit),
            "capacity_delta_nonzero": sum(delta != 0 for delta in cap_deltas),
            "capacity_delta_mean": _mean(cap_deltas),
            "capacity_delta_min": min(cap_deltas) if cap_deltas else None,
            "capacity_delta_max": max(cap_deltas) if cap_deltas else None,
        }
    return {
        "event_count": len(events),
        "by_phase": dict(sorted(by_phase.items())),
        "by_mode": modes,
        "vanilla_interpretation": (
            "Campagne courante sur le jeu de véhicules OpenTTD/OpenGFX gelé. "
            "Les deltas de capacité refit observés valent pour ce set seulement ; "
            "le risque NewGRF reste un risque de compatibilité, pas un effet mesuré extrapolable."
        ),
    }

def analyse(payload, engine_dir):
    analysis = analyse_events(collect_engine_events(engine_dir))
    analysis["health"] = payload.get("health")
    analysis["economics"] = {
        "statistics": payload.get("statistics"),
        "paired_comparisons": payload.get("paired_comparisons"),
    }
    return analysis

def selftest():
    sample = (
        "dbg: M3_EQUIP date=123 mode=road phase=pre_admission cargo=0 "
        "choices=3 viable=3 selected=4 selected_profit=-10 selected_roi=0 "
        "best_profit_id=5 best_profit=20 best_roi_id=5 best_roi=7 "
        "native_choices=2 refit_proxy_choices=1 selected_refit=0 admission_flip=1 "
        "native_admission_flip=1"
    )
    event = parse_event(sample)
    assert event["mode"] == "road"
    result = analyse_events([event])
    assert result["by_mode"]["road"]["admission_flips"] == 1
    assert result["by_mode"]["road"]["selected_differs_best_profit"] == 1
    print("diag_m3_equipment_roi selftest OK")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--payload", type=Path)
    parser.add_argument("--engine-dir", type=Path)
    args = parser.parse_args()
    if args.selftest:
        selftest()
        return
    payload = json.loads(args.payload.read_text(encoding="utf-8"))
    print(json.dumps(analyse(payload, args.engine_dir), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
