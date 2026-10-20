"""Verify the self-contained V277+V279 result archive."""

import gzip
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREFIX = "v277v279_porteB_20x10_pc_20261020"


def main():
    index = json.loads((ROOT / "index.json").read_text(encoding="utf-8"))
    assert index["execution_git_sha"] == "fb6b9ebeffff5b99f7aa4d9796e2ba8686082f77"
    assert len(index["artifacts"]) == 4
    documents = {}
    for entry in index["artifacts"]:
        archive = ROOT / entry["evidence"]
        packed = archive.read_bytes()
        raw = gzip.decompress(packed)
        assert len(raw) == entry["raw_bytes"]
        assert len(packed) == entry["gzip_bytes"]
        assert hashlib.sha256(raw).hexdigest() == entry["raw_sha256"]
        assert hashlib.sha256(packed).hexdigest() == entry["gzip_sha256"]
        documents[Path(entry["source"]).name] = json.loads(raw)

    result = documents[PREFIX + ".json"]
    smoke = documents[PREFIX + "_smoke.json"]
    assert result["source_bundle_sha256"] == index["source_bundle_sha256"]
    assert result["manifest_sha256"] == index["manifest_sha256"]
    assert result["years"] == 10 and len(result["games"]) == 40
    assert not result["failed_runs"]
    comparison = result["policy_comparison"]
    assert comparison["complete_pairs"] == comparison["planned_pairs"] == 20
    assert comparison["comparison_complete"] is True
    assert comparison["adoption_sample_complete"] is True
    assert comparison["metric_coverage_complete"] is True
    assert comparison["decision_rule"]["rule"] == "non_erosion"
    assert comparison["verdict"] == "pass"
    assert comparison["ci_pass"] is True and comparison["value_guard_pass"] is True
    delta = comparison["aggregates"]["profit_year"]["policy_delta"]
    assert delta["n"] == 20 and (delta["wins"], delta["losses"], delta["ties"]) == (6, 14, 0)
    assert delta["mean"] == -195078.2
    assert delta["mean_bootstrap_95pct_ci"] == [-386320.8, 7582.55]
    assert comparison["aggregates"]["company_value"]["policy_ratio"]["ratio_of_means_percent_change"] == -3.534663
    assert smoke["years"] == 1 and len(smoke["games"]) == 2
    assert not smoke["failed_runs"]
    assert smoke["policy_comparison"]["verdict"] == "diagnostic_only"
    print("OK: 4 archives, smoke 2/2, banc 40/40, 20/20 paires, verdict pass")


if __name__ == "__main__":
    main()
