"""Sequential 2026-10-25 A40x5 multimodal / B20x10 queue, never two Dockers.

Launch manually from /openttd-ml with:
  python -X utf8 sweeps/run_nuit75_newformat_queue_20261025.py

This is an explicit one-shot execution of the user's authorised campaign
queue, not a daemon or a changed default. No force-stopping containers.
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parents[1]
JOURNAL = ROOT / "docs/journaux/journal_2026-10-24_nuit_75pct.md"
RESULTS = ROOT / "results"
STATUS = RESULTS / "nuit75_newformat_queue_20261025.jsonl"
LOG = RESULTS / "nuit75_newformat_queue_20261025.log"

# Keep the current N75-CAP gate, which was already underway at queue creation.
QUEUE = [
    ("N75-CAP", "nuit75-freight-capacity-variant", "n75_freight_capacity", 1,
     "nuit75_freightcap_porteA_40x5_20261025", "nuit75_freightcap_porteB_20x10_20261025"),
    ("GOOD", "nuit75-good-source-variant", "good_source_rail_join", 1,
     "nuit75_goodsource_porteA_40x5_newformat_20261025", "nuit75_goodsource_porteB_20x10_newformat_20261025"),
    ("AIR-GROW corrigé", "nuit75-air-grow-corrected", "air_grow_marginal", 2,
     "nuit75_airgrowfix_porteA_40x5_20261025", "nuit75_airgrowfix_porteB_20x10_20261025"),
    ("N75-C75-REFUND", "nuit75-early-c75-refund", "n75_c75_refund", 2,
     "nuit75_c75refund_porteA_40x5_20261025", "nuit75_c75refund_porteB_20x10_20261025"),
    ("N75 AIR quote", "nuit75-early-value-v1", "n75_air_true_quote", 2,
     "nuit75_truequote_porteA_40x5_20261025", "nuit75_truequote_porteB_20x10_20261025"),
    ("N75 multi-cargo", "nuit75-early-multicargo-v1", "n75_multi_cargo", 2,
     "nuit75_multicargo_porteA_40x5_20261025", "nuit75_multicargo_porteB_20x10_20261025"),
]


def event(kind, **fields):
    entry = {"at": datetime.now().isoformat(timespec="seconds"), "event": kind, **fields}
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    with STATUS.open("a", encoding="utf-8") as output:
        output.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(json.dumps(entry, ensure_ascii=False), flush=True)


def journal(message):
    with JOURNAL.open("a", encoding="utf-8") as output:
        output.write("\n" + message.strip() + "\n")


def docker_ids():
    check = subprocess.run(["docker", "ps", "--format", "{{.ID}}"],
                           cwd=ROOT, text=True, capture_output=True)
    if check.returncode:
        raise RuntimeError("Impossible de vérifier docker ps : " + check.stderr.strip())
    return [item for item in check.stdout.splitlines() if item.strip()]


def wait_docker_empty():
    reported = False
    while True:
        ids = docker_ids()
        if not ids:
            return
        if not reported:
            event("docker_occupied_wait", container_ids=ids)
            reported = True
        time.sleep(20)


def report(path):
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    p = data["policy_comparison"]
    metric = p["aggregates"]["profit_year"]["policy_delta"]
    value = p["aggregates"]["company_value"]["policy_ratio"]
    rule = p.get("decision_rule") or {}
    return data, p, {
        "verdict": p["verdict"], "complete_pairs": p["complete_pairs"],
        "mean_delta": metric["mean"], "median_delta": metric["median"],
        "wins": metric["wins"], "losses": metric["losses"], "ties": metric["ties"],
        "wilcoxon_p": metric["wilcoxon_p"],
        "ci95": metric["mean_bootstrap_95pct_ci"],
        "required_delta": rule.get("min_useful_primary_delta"),
        "company_value_percent_change": value["ratio_of_means_percent_change"],
        "bundle": data["source_bundle_sha256"],
        "last_year": data["expected_last_year"],
        "year_count": data["years"],
    }


def ratios(data):
    paired = {}
    for row in data["summary"]:
        policy = row.get("duel_policy_id")
        if policy is None or row.get("arm") not in ("OpexAI", "AAAHogEx"):
            continue
        pair = paired.setdefault((policy, row["seed"], row.get("repeat", 0)), {})
        if row["arm"] in pair:
            raise AssertionError("duplicated summary company")
        pair[row["arm"]] = row
    out = {}
    for policy in [p["id"] for p in data["policies"]]:
        relevant = [a for k, a in paired.items() if k[0] == policy]
        valid = []
        for arms in relevant:
            if set(arms) != {"OpexAI", "AAAHogEx"}:
                continue
            o, a = arms["OpexAI"], arms["AAAHogEx"]
            if not all(x.get("run_ok") and x.get("game_ok")
                       and x.get("horizon_complete") and x.get("include_in_economic_stats")
                       for x in (o, a)):
                continue
            if o.get("profit_year") is None or a.get("profit_year") is None or a["profit_year"] <= 0:
                continue
            valid.append((o["profit_year"], a["profit_year"]))
        if len(valid) != len(relevant):
            raise AssertionError(f"ratio data incomplete {policy}: {len(valid)}/{len(relevant)}")
        if not valid:
            raise AssertionError("no valid pairs")
        out[policy] = {
            "n": len(valid),
            "opex_mean": mean(o for o, _ in valid),
            "aaa_mean": mean(a for _, a in valid),
            "ratio_of_means_pct": 100*sum(o for o, _ in valid)/sum(a for _, a in valid),
            "median_paired_ratios_pct": 100*median(o/a for o, a in valid),
        }
    return out


def summary_to_journal(label, gate, campaign, metrics, ratio):
    prefix = "A40×5 multimodal" if gate == "A" else "B20×10 non_erosion"
    parts = [f"**25/10 — {label}, {prefix} `{campaign}` :** "
             f"verdict **`{metrics['verdict']}`**, {metrics['complete_pairs']} paires, "
             f"Δ `profit_year` moyen **{metrics['mean_delta']:+,.2f} £/an**, "
             f"médiane {metrics['median_delta']:+,.2f}, "
             f"V/D/E={metrics['wins']}/{metrics['losses']}/{metrics['ties']}, "
             f"Wilcoxon p={metrics['wilcoxon_p']}, "
             f"IC95 bootstrap [{metrics['ci95'][0]:+,.2f}; {metrics['ci95'][1]:+,.2f}], "
             f"garde valeur {metrics['company_value_percent_change']:+.3f} %, "
             f"bundle `{metrics['bundle']}`. "
             f"Seuil indicatif 4 % = {metrics['required_delta']} £/an."]
    if ratio:
        parts.append(" Ratios Opex/AAAHogEx en décembre 1979 (chaque AAA du duel propre au bras) : ")
        for arm, item in ratio.items():
            parts.append(f"**{arm}** : {item['n']} paires, Opex moyen {item['opex_mean']:,.2f} £/an, "
                         f"AAA moyen {item['aaa_mean']:,.2f} £/an, "
                         f"ratio des moyennes **{item['ratio_of_means_pct']:.4f} %**, "
                         f"médiane des ratios appariés **{item['median_paired_ratios_pct']:.4f} %**. ")
    elif gate == "A":
        parts.append(" B20×10 déclenchée seulement si A passe ; un résultat A40×5 "
                     "n'autorise pas à déclarer un ratio de profit à dix ans.")
    journal("".join(parts))


def run_campaign(worktree, campaign, setting, value, gate):
    destination = worktree / "results" / (campaign + ".json")
    if destination.exists():
        data, cmp, metrics = report(destination)
        assert data["years"] == (5 if gate == "A" else 10)
        assert len(data["seeds"]) == (40 if gate == "A" else 20)
        event("existing_report_used", name=campaign, **metrics)
        return data, cmp, metrics
    wait_docker_empty()
    cmd = [sys.executable, "-X", "utf8", "sweeps/run_c66_reference.py",
           "--campaign", campaign, "--reference", f"OpexAI[{setting}=0]",
           "--variant", f"OpexAI[{setting}={value}]",
           "--variant-policy-id", setting.replace("_", "")[:28],
           "--decision-rule", "gain_short" if gate == "A" else "non_erosion",
           "--min-useful-primary-delta-pct", "4",
           "--primary-metric", "profit_year",
           "--value-guard-max-loss-pct", "5",
           "--years", "5" if gate == "A" else "10",
           "--repeats", "1", "--probes", "2",
           "--max-workers", "9", "--cpus", "10", "--memory", "8g",
           "--map-size", "8"]
    if gate == "A":
        cmd += ["--required-seeds", "40", "--required-years", "5"]
    event("campaign_start", name=campaign, gate=gate, worktree=str(worktree), cmd=cmd)
    with LOG.open("a", encoding="utf-8") as output:
        output.write("\n==== " + datetime.now().isoformat() + " " + campaign + " ====\n")
        output.flush()
        code = subprocess.call(cmd, cwd=worktree, stdout=output, stderr=subprocess.STDOUT)
    if code != 0 or not destination.exists():
        event("campaign_error", name=campaign, exit_code=code,
              json_exists=destination.exists())
        journal(f"**25/10 — {campaign} : ERREUR TECHNIQUE**, code={code}; "
                "aucun verdict économique, ne pas relancer sans diagnostic.")
        return None, None, None
    data, cmp, metrics = report(destination)
    event("campaign_finish", name=campaign, **metrics)
    return data, cmp, metrics


def main():
    event("queue_begin", count=len(QUEUE))
    for label, folder, setting, value, name_a, name_b in QUEUE:
        worktree = ROOT / ".worktrees" / folder
        if not (worktree / "ai" / "AAAHogEx-115").is_dir():
            event("queue_abort", issue="AAAHogEx missing", worktree=str(worktree))
            return 2
        if name_a == "nuit75_freightcap_porteA_40x5_20261025":
            # This Docker process was started BEFORE this queue. Do not kill it.
            event("wait_existing_gate", name=name_a)
            while not (worktree / "results" / (name_a + ".json")).exists():
                ids = docker_ids()
                if not ids:
                    event("queue_abort", issue="existing first gate ended without final JSON",
                          name=name_a)
                    return 3
                time.sleep(20)
        data_a, cmp_a, metrics_a = run_campaign(worktree, name_a, setting, value, "A")
        if data_a is None:
            event("queue_abort", issue="gate A technical error", name=name_a)
            return 4
        if data_a["years"] != 5 or len(data_a["seeds"]) != 40 or cmp_a["complete_pairs"] != 40:
            event("queue_abort", issue="incomplete A report", name=name_a)
            return 5
        summary_to_journal(label, "A", name_a, metrics_a, None)
        if metrics_a["verdict"] != "pass":
            event("B_skipped_A_failed", name=name_a, verdict=metrics_a["verdict"])
            continue
        # Only A complete, with official V102 'pass', authorises B.
        data_b, cmp_b, metrics_b = run_campaign(worktree, name_b, setting, value, "B")
        if data_b is None:
            event("queue_abort", issue="gate B technical error", name=name_b)
            return 6
        if data_b["years"] != 10 or len(data_b["seeds"]) != 20 or cmp_b["complete_pairs"] != 20:
            event("queue_abort", issue="incomplete B report", name=name_b)
            return 7
        ratio = ratios(data_b)
        (worktree / "results" / (name_b + "_ratios.json")).write_text(
            json.dumps({"campaign": name_b, "bundle_sha256": data_b["source_bundle_sha256"],
                        "arms": ratio}, indent=2, ensure_ascii=False), encoding="utf-8")
        summary_to_journal(label, "B", name_b, metrics_b, ratio)
        event("B_finished", name=name_b, verdict=metrics_b["verdict"],
              ratios=ratio)
    event("queue_complete", count=len(QUEUE))
    journal("**25/10 — File nouvelle formule terminée :** les six portes A40×5 "
            "ont reçu un verdict ; les B20×10 ont été effectuées seulement "
            "pour les portes A officiellement `pass`. Aucun défaut/commit/push/merge.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
