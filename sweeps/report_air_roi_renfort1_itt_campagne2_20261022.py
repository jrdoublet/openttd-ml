"""Rapport daté de l'ITT AIR-ROI-RENFORT-1, campagne 2 (amendement §8).

N'accepte que 40 parties et 20 paires saines. Ne requalifie pas le 20x6.
Sorties : JSON analysable et docs/air_roi_renfort1_etape2b_itt_campagne2_20261022.md.

Attention : cette commande réécrit le Markdown désigné par ``--doc`` et le
JSON ``<campaign>_itt_report.json`` dans ``--results-dir``. La valeur par
défaut de ``--doc`` désigne un document historique versionné. Toujours
fournir ``--doc`` et ``--results-dir`` vers des sorties contrôlées si l'on
rejoue le post-traitement, afin de préserver le rapport historique.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from report_air_roi_renfort1_itt_20261022 import analyze_campaign


def fmt(value, digits=0):
    if value is None:
        return "indisponible"
    return f"{value:,.{digits}f}".replace(",", " ").replace(".", ",")


def estimate(row, unit="£/an"):
    ci = row.get("ci95_seed_cluster") or row.get("mean_bootstrap_95pct_ci")
    bounds = f"[{fmt(ci[0])} ; {fmt(ci[1])}]" if ci else "indisponible"
    return f"{fmt(row.get('mean'))} {unit}, IC95 {bounds}"


def render(report):
    a12, a24 = (report["itt_operating_" + str(n) + "m"] for n in (12, 24))
    fs = report["first_stage_ITT_aircraft_added"]
    cp = (report["company_profit_year"] or {}).get("policy_delta") or {}
    value = report["company_value"]
    value_change = (value.get("policy_ratio") or {}).get("ratio_of_means_percent_change")
    source = report["v161_model_versus_observation"]
    lines = [
        "# AIR-ROI-RENFORT-1 — étape 2b, campagne ITT 2 (22/10/2026)",
        "",
        f"**Verdict : `{report['scientific_verdict']}`** selon l'amendement prospectif",
        "§8 du protocole (signé avant toute collecte de cette campagne).",
        "La politique p50 contre p0 est un diagnostic et ne constitue aucune porte V102.",
        "",
        "## Identité, qualité et indépendance",
        "",
        f"- Campagne : `{report['campaign']}`, {report['years']} ans, "
        f"{report['games_completed']}/{report['games_total']} parties, "
        f"{report['pairs_complete']}/{report['pairs_total']} paires.",
        f"- Bundle SHA256 : `{report['sha256_bundle']}` ; manifeste SHA256 : `{report['sha256_manifest']}`.",
        "- Deux bras : `OpexAI[air_roi_renfort1_itt=1]` (p0) et "
        "`OpexAI[air_roi_renfort1_itt=2]` (p50), mêmes graines, AAAHogEx, "
        "quatre workers maximum ; conservation des logs moteur et de la télémétrie mensuelle.",
        "- 20 graines indépendantes, une répétition : aucune pseudo-réplication des "
        "assignations ou des observations mensuelles. IC95 percentile sur 20 000 "
        "rééchantillonnages par grappe de graine, RNG 0.",
        "",
        "## Effets estimés",
        "",
        "| Mesure | Assignations évaluables (traitées / différées) | Graines avec deux affectations | Effet et IC95 par graine |",
        "|---|---:|---:|---|",
        f"| Profit d'exploitation flotte ligne, mois 1–12 annualisés | "
        f"{a12['assigned_treatment_observed']} / {a12['assigned_deferred_observed']} | "
        f"{a12['seeds_with_both_arms']} | {estimate(a12)} |",
        f"| Profit d'exploitation flotte ligne, mois 13–24 annualisés | "
        f"{a24['assigned_treatment_observed']} / {a24['assigned_deferred_observed']} | "
        f"{a24['seeds_with_both_arms']} | {estimate(a24)} |",
        f"| Premier étage : avions déclarés ajoutés/assignation | "
        f"{fs['assigned_treatment_observed']} / {fs['assigned_deferred_observed']} | "
        f"{fs['seeds_with_both_arms']} | {fmt(fs['mean'], 3)} avions/assignation, "
        f"IC95 [{fmt((fs['ci95_seed_cluster'] or [None, None])[0], 3)} ; "
        f"{fmt((fs['ci95_seed_cluster'] or [None, None])[1], 3)}] |",
        f"| Compagnie p50−p0, `profit_year` terminal | {report['pairs_complete']} paires | "
        f"{report['pairs_complete']} | {estimate(cp)} |",
        "",
        f"Valeur compagnie : ratio des moyennes "
        f"{fmt((value.get('policy_ratio') or {}).get('ratio_of_means'), 6)} "
        f"(variation {fmt(value_change, 3)} % ; "
        f"garde descriptive de −5 % {'tenue' if value_change is not None and value_change >= -5 else 'non validée'}). "
        "L'ITT local porte sur **tous les avions de la ligne** et exclut "
        "infrastructure, valeur résiduelle et coût physique des remplacements. "
        "Un coefficient de ROI marginal net de l'appareil ne peut en être tiré.",
        "",
        "**Attention à la sélection de suivi :** les estimations d'exploitation à 12 et 24 "
        "mois portent sur les épisodes observables, et leurs IC95 sont descriptifs "
        "de cette sous-population. Ils ne constituent pas une preuve d'ITT causal "
        "sur toutes les assignations, car le suivi est largement incomplet. "
        "Les assignations sans endpoint n'ont reçu ni zéro fictif ni profit imputé.",
        "",
        "## Attrition et couverture préenregistrée",
        "",
        "| Horizon, bras | Assignées | Éligibles avant fin de partie | Censurées administrativement | "
        "Évaluables | Suivi parmi éligibles | Suivi brut |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for h in ("12", "24"):
        for arm in ("treatment", "deferred"):
            c = report["followup_windows"][h]["arms"].get(arm, {})
            lines.append(f"| {h} mois, {arm} | {c.get('assigned', 0)} | "
                         f"{c.get('administratively_eligible', 0)} | "
                         f"{c.get('administratively_censored', 0)} | "
                         f"{c.get('valid', 0)} | "
                         f"{fmt(100*c['retention_eligible'], 1) + '%' if c.get('retention_eligible') is not None else 'indisponible'} | "
                         f"{fmt(100*c['retention_all_assignments'], 1) + '%' if c.get('retention_all_assignments') is not None else 'indisponible'} |")
    lines.extend([""])
    for h in ("12", "24"):
        window = report["followup_windows"][h]
        lines.append(f"À {h} mois : écart absolu des taux de suivi "
                     f"{fmt(window['retention_gap_absolute']*100, 2) + ' points' if window['retention_gap_absolute'] is not None else 'indisponible'} ; "
                     f"seuil préenregistré {'satisfait' if window['information_threshold_met'] else 'non satisfait'}. "
                     f"Ruptures parmi les épisodes administrativement éligibles : "
                     f"`{json.dumps(window['missing_reasons_among_eligible'], ensure_ascii=False)}`.")
    duration = report.get("failed_24m_interval_duration_by_first_bad_checkpoint") or {}
    lines.extend(["",
        "**Détail des durées en échec à 24 mois :** parmi les premiers intervalles "
        "invalides des épisodes administrativement éligibles, "
        f"{duration.get('greater_than_42_days', 0)} durent plus de 42 jours et "
        f"{duration.get('less_than_18_days', 0)} moins de 18 jours "
        f"(non classés : {duration.get('unclassified', 0)}). "
        "Les intervalles longs indiquent une cadence effective de relevé trop "
        "espacée ; les intervalles courts apparaissent lors du rattrapage. "
        "Le seuil de durée est conservé conformément au préenregistrement : "
        "aucune requalification a posteriori de ces épisodes.",
        ""])
    lines.extend(["", "Par graine, assignations / éligibles / valides (12 et 24 mois) :",
                  "", "| Graine | Bras | Assignées | 12 mois (éligibles / valides) | 24 mois (éligibles / valides) |",
                  "|---|---|---:|---:|---:|"])
    for seed in sorted(report["followup_by_seed"], key=int):
        for arm in ("treatment", "deferred"):
            c = report["followup_by_seed"][seed].get(arm, {})
            lines.append(f"| {seed} | {arm} | {c.get('assigned', 0)} | "
                         f"{c.get('eligible_12', 0)} / {c.get('valid_12', 0)} | "
                         f"{c.get('eligible_24', 0)} / {c.get('valid_24', 0)} |")
    lines += ["", "## Cohortes au moment de l'assignation", "",
              "| Classe | Cohorte | Affectations (T/D) | ITT 12 mois ; graines avec deux bras | "
              "ITT 24 mois ; graines avec deux bras |",
              "|---|---|---:|---|---|"]
    for dimension, groups in report["cohorts_12m_24m"].items():
        for name, c in groups.items():
            t12, t24 = c["12m"], c["24m"]
            lines.append(f"| {dimension} | {name} | "
                         f"{c['assigned'].get('treatment', 0)} / {c['assigned'].get('deferred', 0)} | "
                         f"{estimate(t12)} ; n={t12['seeds_with_both_arms']} | "
                         f"{estimate(t24)} ; n={t24['seeds_with_both_arms']} |")
    lines += ["", "## Confrontation avec les prévisions V161/C70 (diagnostic)", "",
              "| Source V161 | Affectations | Médiane de profit prédit par avion (£/an) | "
              "Médiane ROI brut de sélection (unités du score) | Relevés 24 mois T/D |",
              "|---|---:|---:|---:|---:|"]
    for name, s in source.items():
        lines.append(f"| {name} | {s['assignments']} | "
                     f"{fmt(s['modeled_per_aircraft_profit_gbp_per_year']['median'])} | "
                     f"{fmt(s['roi_selection_heuristic']['median'], 2)} | "
                     f"{s['observed_24m_treatment']} / {s['observed_24m_deferred']} |")
    lines += ["",
              "Le ROI brut de sélection, le profit annuel prédit V161 et le résultat "
              "d'exploitation de toute la ligne ont des périmètres distincts. "
              "Ils ne permettent pas de comparer un rendement net marginal mesuré "
              "à un coût physique unitaire fiable.",
              "",
              "## Intégrité de la récupération des données",
              "",
              "Les simulations 40/40 ont produit leurs checkpoints et journaux moteur. "
              "Le post-traitement du harnais a ensuite été arrêté par Docker pour "
              "dépassement mémoire (OOM, code hôte 247), avant le JSON récapitulatif. "
              "La récupération a relu en streaming le JSONL original et les quarante "
              "journaux moteur, en réutilisant les fonctions du banc pour les contrôles "
              "de santé et la comparaison économique. Aucun moteur ni graine n'a été "
              "relancé. Les fichiers de télémétrie bruts sont conservés ; le résumé "
              "récupéré omet le volumineux proxy descriptif C66 des gares, qui ne "
              "sert pas aux endpoints ITT.",
              "",
              "## Décision",
              "",
              ("Les seuils de couverture à 24 mois sont satisfaits ; l'intervalle, "
               "la sensibilité à l'attrition et les limites de comptabilité sont "
               "examinés avant toute étape 3." if report['scientific_verdict'] == 'followup_information_met'
               else "L'information ITT à 24 mois ne satisfait pas les seuils "
                    "préenregistrés : aucune étape 3, politique nouvelle ou porte A/B n'est ouverte."),
              "Aucun défaut d'IA, coefficient V161/C70, score ni priorité n'est modifié.",
              "Les anciennes observations 20×6 restent figées ; toute évolution "
              "d'estimand dans cette campagne est documentée au §8.",
              ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", default="airr1_itt_month_20x10_20261022_b")
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    parser.add_argument("--doc", type=Path, default=Path(
        "docs/air_roi_renfort1_etape2b_itt_campagne2_20261022.md"))
    opts = parser.parse_args()
    result = analyze_campaign(opts.campaign, opts.results_dir, followup_v2=True)
    if result["games_completed"] != result["games_total"] or result["games_total"] != 40 \
            or result["pairs_complete"] != 20 or not result["comparison_complete"]:
        raise ValueError("Campagne incomplète ou comparaison invalide : pas de rapport final")
    out = opts.results_dir / (opts.campaign + "_itt_report.json")
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    opts.doc.write_text(render(result), encoding="utf-8")
    print(f"Rapport JSON : {out}")
    print(f"Rapport Markdown : {opts.doc}")
    print(f"Verdict : {result['scientific_verdict']}")


if __name__ == "__main__":
    main()
