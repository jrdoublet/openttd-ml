"""analyze_diag_c63.py - Analyse automatisée et lecture rigoureuse du diagnostic C63/C58.

Applique strictement les seuils du protocole :
- Surcoût : actual_ok / planned_ok >= 1.30
- Déficit de revenu : médiane réelle/prédite < 0.50 dans une cohorte
- Cause dominante : plus de 50 % des jours de reliquat

Pour chaque table[] de chaque graine :
1. spend[mode] : prévu/réel, succès et échecs
2. cohort_revenue : ratio réel/prédit par mode et âge
3. opp et leftover_shares : répartition des causes des jours sans lancement
4. attribution : synthèse annuelle
5. Synthèse inter-graines et qualification du signal dominant.
"""
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics
import sys

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from diag_c63_c58 import (
    ABSENT_CAUSES,
    DOMINANT,
    LEFTOVER_KINDS,
    MODES,
    OVERCOST_RATIO,
    REVENUE_SHORTFALL,
    median_ratio,
    revenue_shortfall_by_cohort,
)


def analyze_diag(path: Path):
    with open(path) as f:
        data = json.load(f)

    print("=" * 80)
    print(f"ANALYSE DU DIAGNOSTIC : {path.name}")
    print(f"Arm: {data.get('arm')} | Graines: {data.get('seeds')} | Années: {data.get('years')}")
    print("=" * 80)

    by_seed = data.get("by_seed", {})
    cross_seed_signals = defaultdict(lambda: defaultdict(list))
    cross_seed_shortfalls = defaultdict(lambda: defaultdict(list))

    for seed, seed_data in sorted(by_seed.items(), key=lambda x: int(x[0])):
        print(f"\n########################################")
        print(f"GRAINE {seed} (Valeur: {seed_data.get('company_value'):,} £ | Stations: {seed_data.get('n_stations')})")
        print(f"########################################")
        table = seed_data.get("table", [])

        for row in table:
            year = row.get("year")
            print(f"\n--- Année {year} (Graine {seed}) ---")
            print(f"Attribution: {row.get('attribution')} | CPU idle: {row.get('cpu_from_idle_cash')} | Pièges: {row.get('traps')}")

            # 1. spend[mode]
            spend = row.get("spend", {})
            print("  [Dépenses]")
            has_spend = False
            for mode in MODES:
                m_spend = spend.get(mode, {})
                plan_ok = m_spend.get("planned_ok", 0)
                act_ok = m_spend.get("actual_ok", 0)
                plan_fail = m_spend.get("planned_fail", 0)
                act_fail = m_spend.get("actual_fail", 0)
                n_ok = m_spend.get("n_ok", 0)
                n_fail = m_spend.get("n_fail", 0)

                if n_ok > 0 or n_fail > 0:
                    has_spend = True
                    ratio_ok = (act_ok / plan_ok) if plan_ok > 0 else 0.0
                    overcost_flag = " [SURCOÛT >= 1.30]" if (ratio_ok >= OVERCOST_RATIO and plan_ok > 0) else ""
                    print(f"    - {mode:5s}: {n_ok} ok (prévu={plan_ok:,} £, réel={act_ok:,} £, ratio={ratio_ok:.2f}){overcost_flag} | {n_fail} fail (prévu={plan_fail:,} £, réel={act_fail:,} £)")
            if not has_spend:
                print("    (aucun lancement cette année)")

            # 2. cohort_revenue
            lines = row.get("lines", [])
            any_short, cohort_details = revenue_shortfall_by_cohort(lines)
            print("  [Cohortes de revenu]")
            if not cohort_details:
                print("    (aucune cohorte avec témoin positif)")
            for cd in cohort_details:
                m = cd["mode"]
                age = cd["age"]
                med = cd["median"]
                n = cd["n"]
                shortfall = cd["shortfall"]
                sf_flag = " [DÉFICIT DE REVENU < 0.50]" if shortfall else ""
                print(f"    - {m}|age={age}: n={n}, ratio_médian={med:.2f}{sf_flag}")
                cross_seed_shortfalls[year][f"{m}|age={age}"].append((med, n, shortfall))

            # 3. opp et leftover_shares
            opp = row.get("opp", {})
            leftover_days = row.get("leftover_days", 0)
            launched_days = row.get("launched_days", 0)
            shares = row.get("leftover_shares", {})
            
            dom_cause = None
            if shares and max(shares.values()) > DOMINANT:
                dom_cause = max(shares, key=shares.get)

            print(f"  [Occasions & Reliquat] Total jours = {leftover_days + launched_days} (lancés={launched_days}, reliquat={leftover_days})")
            days_by_kind = {}
            for k in LEFTOVER_KINDS:
                entry = opp.get(k, 0)
                days_by_kind[k] = entry.get("days", 0) if isinstance(entry, dict) else entry

            shares_str = ", ".join([f"{k}={shares.get(k, 0.0)*100:.1f}% ({days_by_kind.get(k, 0)}j)" for k in LEFTOVER_KINDS])
            print(f"    Shares: {shares_str}")
            absent_shares = row.get("absent_shares", {})
            if absent_shares:
                absent_causes = row.get("absent_causes", {})
                ac_str = ", ".join([f"{c}={absent_shares.get(c, 0.0)*100:.1f}% ({absent_causes.get(c, {}).get('days', 0)}j)" for c in ABSENT_CAUSES if absent_shares.get(c, 0) > 0])
                if ac_str:
                    print(f"    [Absent Breakdown]: {ac_str}")
            # Sonde légère empty_probe
            empty_probes = row.get("empty_probes", [])
            ep_sum = row.get("empty_probe_summary") or {}
            if empty_probes or ep_sum.get("n"):
                cause_counter = ep_sum.get("causes") or {}
                if not cause_counter:
                    for ep in empty_probes:
                        c = ep.get("cause", "?")
                        cause_counter[c] = cause_counter.get(c, 0) + 1
                ep_str = ", ".join(f"{c}×{n}" for c, n in sorted(cause_counter.items(), key=lambda x: -x[1]))
                n_ua = ep_sum.get("n_min_cap_gt_avail")
                if n_ua is None:
                    n_ua = sum(1 for ep in empty_probes if ep.get("min_cap", -1) > ep.get("avail_cap", 0) and ep.get("min_cap", -1) > 0)
                bits = [f"causes={ep_str}", f"min>avail={n_ua}"]
                for key, label in (("considered", "alt"), ("min_cap", "min_cap"), ("avail_cap", "avail")):
                    slot = ep_sum.get(key)
                    if isinstance(slot, dict) and slot.get("n"):
                        bits.append(f"{label}={slot['min']}-{slot['max']} (méd {slot['median']})")
                print(f"    [Empty Probes n={ep_sum.get('n', len(empty_probes))}]: " + " | ".join(bits))
            if dom_cause:
                print(f"    => CAUSE DOMINANTE (> 50%): {dom_cause.upper()} ({shares.get(dom_cause, 0.0)*100:.1f}%)")
            elif leftover_days > 0:
                max_k = max(LEFTOVER_KINDS, key=lambda k: shares.get(k, 0.0))
                print(f"    => Pluralité sans majorité absolue: {max_k} ({shares.get(max_k, 0.0)*100:.1f}%)")
            else:
                print("    => 0 jours de reliquat")

            cross_seed_signals[year]["attributions"].append(row.get("attribution"))
            cross_seed_signals[year]["dominant_leftovers"].append(dom_cause)
            for k in LEFTOVER_KINDS:
                cross_seed_signals[year][f"share_{k}"].append(shares.get(k, 0.0))
                cross_seed_signals[year][f"days_{k}"].append(days_by_kind.get(k, 0))
            for c in ABSENT_CAUSES:
                cross_seed_signals[year][f"absent_share_{c}"].append(absent_shares.get(c, 0.0))
                ac_entry = row.get("absent_causes", {}).get(c, {})
                cross_seed_signals[year][f"absent_days_{c}"].append(ac_entry.get("days", 0) if isinstance(ac_entry, dict) else 0)
            cross_seed_signals[year]["days_launched"].append(launched_days)

    # Synthèse inter-graines par année
    print("\n" + "=" * 80)
    print("SYNTHÈSE MULTI-GRAINES PAR ANNÉE (1970 - 1974)")
    print("=" * 80)

    for year in sorted(cross_seed_signals.keys()):
        stats = cross_seed_signals[year]
        n_seeds = len(stats["attributions"])
        print(f"\n>>> ANNÉE {year} ({n_seeds} graines observées) <<<")
        print(f"  Attributions: {dict(Counter(stats['attributions']))}")
        print(f"  Causes dominantes individuelles (>50%): {dict(Counter(stats['dominant_leftovers']))}")

        avg_shares = {k: statistics.mean(stats[f"share_{k}"]) for k in LEFTOVER_KINDS}
        tot_days = {k: sum(stats[f"days_{k}"]) for k in LEFTOVER_KINDS}
        tot_launched = sum(stats["days_launched"])

        print(f"  Jours cumulés: lancés={tot_launched} | " + " | ".join([f"{k}={tot_days[k]}j" for k in LEFTOVER_KINDS]))
        print("  Parts moyennes du reliquat:")
        for k in sorted(LEFTOVER_KINDS, key=lambda x: avg_shares[x], reverse=True):
            print(f"    - {k:15s}: {avg_shares[k]*100:5.1f}%")

        tot_absent = tot_days.get("absent", 0)
        if tot_absent > 0:
            print("  Ventilation multi-graines de ABSENT:")
            for c in ABSENT_CAUSES:
                c_days = sum(stats[f"absent_days_{c}"])
                c_pct = (c_days / tot_absent * 100) if tot_absent > 0 else 0.0
                print(f"    * {c:20s}: {c_days:4d}j ({c_pct:5.1f}%)")

        # Cohortes
        if year in cross_seed_shortfalls:
            print("  Cohortes multi-graines:")
            for c_name, vals in sorted(cross_seed_shortfalls[year].items()):
                meds = [v[0] for v in vals]
                ns = [v[1] for v in vals]
                sfs = [v[2] for v in vals]
                mean_med = statistics.mean(meds)
                sf_count = sum(1 for s in sfs if s)
                sf_flag = " [SHORTFALL REVENUE]" if sf_count > 0 else ""
                print(f"    * {c_name:12s}: moyenne méd={mean_med:.2f}, total_lignes={sum(ns)}, déficit_graines={sf_count}/{len(vals)}{sf_flag}")

        # Règle d'interprétation
        max_share_k = max(avg_shares, key=lambda k: avg_shares[k])
        if avg_shares[max_share_k] >= DOMINANT:
            print(f"  ==> SIGNAL MULTI-GRAINES COHÉRENT : {max_share_k.upper()} DOMINANT (moyenne {avg_shares[max_share_k]*100:.1f}%)")
        else:
            print(f"  ==> SIGNAL MIXTE / PLURALITÉ SANS MAJORITÉ : {max_share_k} en tête ({avg_shares[max_share_k]*100:.1f}%)")


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else (ROOT / "results" / "diag_c63_c58_6y_5seeds.json")
    analyze_diag(target)
