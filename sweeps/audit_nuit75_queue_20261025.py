"""Independent audit for all completed campaigns in the N75 overnight queue.

No Docker, simulation, or code modification. Call repeatedly while the
sequential runner works. Each completed gate is audited once, with strict
pair/script checks, independently calculated Opex/AAA ratios and journal
entry. Existing audits are deduplicated by campaign id + bundle.
"""

import argparse
import json
from pathlib import Path
from datetime import datetime

from run_nuit75_newformat_queue_20261025 import (
    ROOT, JOURNAL, QUEUE, STATUS, ratios, report,
)
from verify_nuit75_gate_integrity_20261025 import verify

AUDITS = ROOT / "results/nuit75_newformat_gate_audits_20261025.jsonl"


def completed_ids():
    keys = set()
    if AUDITS.exists():
        for text in AUDITS.read_text(encoding="utf-8").splitlines():
            try:
                obj = json.loads(text)
            except json.JSONDecodeError:
                continue
            if obj.get("status") in ("ok", "invalid"):
                keys.add((obj.get("campaign"), obj.get("bundle")))
    return keys


def write_audit(item):
    AUDITS.parent.mkdir(parents=True, exist_ok=True)
    with AUDITS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False) + "\n")


def journal_audit(entry):
    gate = entry["gate"]
    campaign = entry["campaign"]
    audit = entry["audit"]
    pair_count = 40 if gate == "A" else 20
    ratios_by_arm = entry.get("ratios", {})
    lines = [
        f"**Audit indépendant {gate} — `{campaign}` : "
        f"{'VALIDE' if audit['ok'] else 'ÉCHEC TECHNIQUE'}**, "
        f"{audit['games']} duels, {audit['company_rows']} compagnies, "
        f"{audit['complete_pairs']}/{pair_count} paires, "
        f"{audit['script_error_count']} erreur script, "
        f"{audit['unhealthy_games']} partie invalide et "
        f"{audit['unhealthy_summaries']} bilan invalide. "
        f"Manifest SHA {'conforme' if audit['manifest_sha_ok'] else 'NON conforme'}, "
        f"{audit['engine_log_count']} fichiers moteur dont "
        f"{audit['nonempty_engine_logs']} non vides, "
        f"{len(audit['fatal_engine_messages'])} message fatal dans les logs. "
        f"SHA source `{audit['bundle']}` ; verdict économique "
        f"`{audit['verdict']}`. "
    ]
    if audit["engine_log_count"] and not audit["nonempty_engine_logs"]:
        lines.append("Les fichiers moteur sont vides : absence d'erreur script "
                     "établie par les bilans structurés, non par une trace textuelle. ")
    if audit["issues"]:
        lines.append("**ANOMALIES :** " + "; ".join(audit["issues"]) + ". ")
    for policy, fields in ratios_by_arm.items():
        lines.append(
            f"{policy} (fin {1979 if gate == 'B' else 1974}) : "
            f"{fields['n']} paires avec AAA positif, Opex moyen "
            f"{fields['opex_mean']:,.2f} £/an, AAA moyen "
            f"{fields['aaa_mean']:,.2f} £/an, ratio des moyennes "
            f"**{fields['ratio_of_means_pct']:.4f} %**, médiane "
            f"des ratios appariés **{fields['median_paired_ratios_pct']:.4f} %**. "
        )
    if gate == "A":
        lines.append(" Les ratios à 5 ans ne remplacent pas les mesures "
                     "à 10 ans ; B uniquement si l'A officielle passe.")
    with JOURNAL.open("a", encoding="utf-8") as handle:
        handle.write("\n" + "".join(lines) + "\n")


def audit_available():
    old = completed_ids()
    new = []
    for label, folder, setting, value, name_a, name_b in QUEUE:
        for gate, name, years, expected_seeds in (
            ("A", name_a, 5, 40), ("B", name_b, 10, 20)
        ):
            source = ROOT / ".worktrees" / folder / "results" / (name + ".json")
            if not source.exists():
                continue
            try:
                data, comparison, metrics = report(source)
                bundle = data["source_bundle_sha256"]
                if (name, bundle) in old:
                    continue
                integrity = verify(source, expected_seeds, years,
                                   setting=setting, value=value)
                try:
                    arm_ratios = ratios(data)
                except Exception as exc:
                    arm_ratios = {}
                    integrity["ok"] = False
                    integrity["issues"].append(f"ratio computation failed: {exc}")
                item = {
                    "at": datetime.now().isoformat(timespec="seconds"),
                    "campaign": name, "gate": gate, "label": label,
                    "status": "ok" if integrity["ok"] else "invalid",
                    "bundle": bundle, "audit": integrity,
                    "economics": metrics, "ratios": arm_ratios,
                }
                write_audit(item)
                journal_audit(item)
                old.add((name, bundle))
                new.append(item)
            except Exception as exc:
                # A partial/in-progress JSON should not be marked audited.
                new.append({"campaign": name, "status": "pending",
                            "error": str(exc)})
    return new


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-all", action="store_true")
    opts = parser.parse_args()
    new = audit_available()
    print(json.dumps(new, ensure_ascii=False, indent=2))
    if any(x["status"] == "invalid" for x in new):
        raise SystemExit(2)
    if opts.require_all:
        # An invalid earlier audit cannot count as a completed gate, even if
        # it was deduplicated and has no new entry on this invocation.
        history = [json.loads(line) for line in AUDITS.read_text("utf-8").splitlines()]
        by_campaign = {item["campaign"]: item for item in history}
        required = [name_a for *_, name_a, name_b in QUEUE]
        for *_, name_a, name_b in QUEUE:
            if by_campaign.get(name_a, {}).get("economics", {}).get("verdict") == "pass":
                required.append(name_b)
        missing = [name for name in required
                   if by_campaign.get(name, {}).get("status") != "ok"]
        events = [json.loads(line) for line in STATUS.read_text("utf-8").splitlines()]
        complete = any(event.get("event") == "queue_complete" for event in events)
        if missing or not complete:
            print("Missing technically valid required gates:", missing,
                  "; queue_complete:", complete)
            raise SystemExit(3)
