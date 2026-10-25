"""Analyse C66.4 de deux campagnes C66.3 source-identitees.

Pour une modification Squirrel sans nouveau reglage, C66.4 ne peut pas
selectionner deux sources dans un seul dossier OpexAI. Jouer deux campagnes
separees du MEME harnais, apparier les memes 20 graines, puis appliquer la
fonction officielle build_policy_comparison. La verification refuse toute
autre divergence de source IA ou de harnais et tout jeu incomplet.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from bench_1v1_5y_20seeds import build_policy_comparison

SEEDS = [42, 100, 7, 999, 2026, 1, 17, 373684, 314, 512, 1024, 1337,
         4096, 8191, 12345, 54321, 65537, 123456, 424242, 8675309]


def _hashes(root: Path) -> dict[str, str]:
    return {
        file.relative_to(root).as_posix(): hashlib.sha256(file.read_bytes()).hexdigest()
        for file in root.rglob("*") if file.is_file()
    }


def _read_report(path: Path, policy: str):
    if not path.is_file():
        raise FileNotFoundError(f"rapport manquant : {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    assert value["seeds"] == SEEDS and value["years"] == 10 and value["repeats"] == 1, (
        "plan 20x10 non conforme", path)
    assert value["start_year"] == 1970 and value["map_size"] == 8, ("configuration", path)
    assert value["policy_id"] == policy, ("policy_id", path)
    assert not value.get("failed_runs"), ("echecs C66.3", path, value.get("failed_runs"))
    assert len(value["games"]) == 20 and all(game["game_ok"] for game in value["games"]), (
        "jeux invalides", path)
    assert len(value["summary"]) == 40 and all(
        row["run_ok"] and row["game_ok"] for row in value["summary"]), ("summary", path)
    jsonl = path.with_suffix(".jsonl")
    rows = [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines() if line]
    assert rows and all(row.get("duel_policy_id") == policy for row in rows), ("checkpoint", path)
    bundle = path.with_name(path.stem + "_bundle")
    assert bundle.is_dir(), ("bundle absent", bundle)
    return value, rows, bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--variant", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("ne pas ecraser un verdict existant")
    ref, ref_rows, ref_bundle = _read_report(args.reference, "reference")
    var, var_rows, var_bundle = _read_report(args.variant, "probe_gates")
    assert ref["openttd_version"] == var["openttd_version"]
    assert ref["opengfx_version"] == var["opengfx_version"]
    assert ref["aaahogex_settings"] == var["aaahogex_settings"]
    assert _hashes(ref_bundle / "ai" / "AAAHogEx-115") == _hashes(var_bundle / "ai" / "AAAHogEx-115"), "AAAHogEx modifie"
    ref_harness = _hashes(ref_bundle / "harness")
    var_harness = _hashes(var_bundle / "harness")
    assert ref_harness.keys() == var_harness.keys(), "inventaire harnais distinct"
    harness_newline_only = []
    for rel in sorted(ref_harness):
        if ref_harness[rel] == var_harness[rel]:
            continue
        before = (ref_bundle / "harness" / rel).read_bytes()
        after = (var_bundle / "harness" / rel).read_bytes()
        # Worktrees Windows peuvent convertir LF <-> CRLF pour un module
        # suivi, sans toucher au code; tracer toute exception bit-a-bit.
        assert before.replace(b"\r\n", b"\n") == after.replace(b"\r\n", b"\n"), (
            "code du harnais divergent", rel)
        harness_newline_only.append(rel)
    ref_opex = _hashes(ref_bundle / "ai" / "OpexAI")
    var_opex = _hashes(var_bundle / "ai" / "OpexAI")
    assert ref_opex.keys() == var_opex.keys(), "inventaire des fichiers OpexAI divergent"
    changed = sorted(name for name in ref_opex if ref_opex[name] != var_opex[name])
    assert changed == ["task_report.nut"], ("sources OpexAI divergentes", changed)

    for path in (args.reference, args.variant):
        manifest = json.loads(path.with_suffix(".manifest.json").read_text(encoding="utf-8"))
        policy = manifest["policies"][0]
        assert policy["settings"]["effective"]["probes"] == 0, "probes=0 obligatoire"
    comparison = build_policy_comparison(
        ref["summary"] + var["summary"], ref_rows + var_rows,
        seeds=SEEDS, repeats=1, reference_policy_id="reference",
        variant_policy_id="probe_gates", primary_metric="profit_year",
        min_useful_primary_delta=None, min_useful_primary_delta_pct=4,
        value_guard_max_loss_pct=5, starting_year=1970, years=10,
        decision_rule="non_erosion",
    )
    assert comparison["comparison_complete"] and comparison["complete_pairs"] == 20, (
        "20 paires non completes", comparison["incomplete_pairs"])
    pairs = comparison["per_pair"]
    ratios = {}
    for prefix in ("reference", "variant"):
        opex = sum(pair["metrics"]["profit_year"][f"{prefix}_opex"] for pair in pairs)
        aaa = sum(pair["metrics"]["profit_year"][f"{prefix}_aaahogex"] for pair in pairs)
        ratios[prefix] = {"opex_mean_gbp": opex / 20, "aaa_mean_gbp": aaa / 20,
                          "ratio_means_pct": opex / aaa * 100 if aaa else None}
    duration_s = {
        "reference": args.reference.stat().st_mtime - args.reference.with_suffix(".manifest.json").stat().st_mtime,
        "variant": args.variant.stat().st_mtime - args.variant.with_suffix(".manifest.json").stat().st_mtime,
    }
    payload = {
        "purpose": "20x10 non_erosion opcodes; same harness, separate immutable source bundles",
        "reference_source": {"git_commit": "2be46925", "bundle_sha256": ref["source_bundle_sha256"],
                             "manifest_sha256": ref["manifest_sha256"]},
        "variant_source": {"git_commit": "2be46925+task_report.nut guards",
                           "bundle_sha256": var["source_bundle_sha256"],
                           "manifest_sha256": var["manifest_sha256"]},
        "changed_ai_files": changed,
        "harness_newline_only_differences": harness_newline_only,
        "effective_probes": 0,
        "workers_per_campaign": 9,
        "ratios": ratios,
        "duration_s": duration_s,
        "comparison": comparison,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    stats = comparison["aggregates"]["profit_year"]["policy_delta"]
    print(json.dumps({
        "verdict": comparison["verdict"],
        "complete_pairs": comparison["complete_pairs"],
        "mean_delta": stats["mean"],
        "V_D_E": [stats["wins"], stats["losses"], stats["ties"]],
        "wilcoxon_p": stats.get("wilcoxon_p"),
        "ci95": stats.get("mean_bootstrap_95pct_ci"),
        "company_value_guard_pct": comparison["aggregates"]["company_value"]["policy_ratio"]["ratio_of_means_percent_change"],
        "ratios": ratios,
        "duration_s": duration_s,
        "output": str(args.out),
    }, indent=2))


if __name__ == "__main__":
    main()
