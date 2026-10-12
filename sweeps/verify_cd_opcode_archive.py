"""Verify CD C40x4 LOOP_OPS from compact paired annual engine counters.

Needs only the evidence archive, not OpenTTD, Docker, or the old worktrees.
"""
import json
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/review/air_catalogue_cd_20261012"


def verify(raw_path=EVIDENCE / "cd_combined_C40x4_20261012_opcode_annual_raw.json",
           comparison_path=EVIDENCE / "cd_combined_C40x4_20261012_comparison.json"):
    raw = json.loads(Path(raw_path).read_text(encoding="utf-8"))
    comparison = json.loads(Path(comparison_path).read_text(encoding="utf-8"))
    assert raw["complete_years"] == ["1970", "1971", "1972"]
    assert comparison["valid"] and comparison["n"] == 40
    paired = raw["paired"]
    assert len(paired) == 40
    assert set(paired) == {str(seed) for seed in comparison["seeds"]}
    windows = {
        "1970-1971": ("1970", "1971"),
        "1970-1972": ("1970", "1971", "1972"),
    }
    result = {}
    for window, years in windows.items():
        row = comparison["opcode"][window]
        deltas = []
        refs = []
        for seed, record in sorted(paired.items(), key=lambda item: int(item[0])):
            assert set(record) == set(raw["complete_years"])
            delta, reference = 0, 0
            for year in years:
                yr = record[year]
                assert set(yr) == {"reference", "variant"}
                for arm in ("reference", "variant"):
                    data = yr[arm]
                    assert data["loop_executed_ops"] > 0 and data["loop_posts"]
                    counted = sum(post["ops"] for key, post in data["loop_posts"].items()
                                  if key not in ("sleep_left", "_year"))
                    assert counted == data["loop_executed_ops"], (seed, year, arm)
                    assert data["sleep_left_ops"] == data["loop_posts"].get("sleep_left", {}).get("ops", 0)
                reference += yr["reference"]["loop_executed_ops"]
                delta += (yr["variant"]["loop_executed_ops"]
                          - yr["reference"]["loop_executed_ops"])
            assert delta == row["by_seed_delta"][seed], (window, seed)
            deltas.append(delta)
            refs.append(reference)
        assert abs(mean(deltas) - row["mean_delta"]) < 1e-8
        assert abs(mean(refs) - row["mean_reference"]) < 1e-8
        assert abs(mean(deltas) / mean(refs) - row["ratio_of_means"]) < 1e-12
        inc = row.get("increases", row.get("wins_or_increases"))
        dec = row.get("decreases", row.get("losses_or_decreases"))
        assert sum(v > 0 for v in deltas) == inc
        assert sum(v < 0 for v in deltas) == dec
        result[window] = {"mean_delta": mean(deltas),
                          "relative_delta": mean(deltas) / mean(refs),
                          "increases": inc,
                          "decreases": dec}
    return result


if __name__ == "__main__":
    print(json.dumps({"valid": True, "n": 40, "windows": verify()}, indent=2))
