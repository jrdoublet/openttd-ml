"""Reproduce the ESTIM31 three-finalist detailed 20x10 report from archived JSON.

Read-only except for the single Markdown output. No simulator, Docker, or OpexAI edits.
Run: python -X utf8 sweeps/estim31_document_three_finalists_20261030.py
Check: python -X utf8 sweeps/estim31_document_three_finalists_20261030.py --check
"""

import argparse
import json
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "docs"
OUTPUT = DOCS / "estim31_trois_variantes_20x10_detail_20261030.md"
ACCOUNT_FILES = {
    "v161": "estim31_ten_v161_accounts_1979_20261030.json",
    "v161coeff": "estim31_ten_v161a250_accounts_1979_20261030.json",
    "v161cap": "estim31_ten_motorcap_accounts_1979_20261030.json",
}
TITLES = {
    "v161": "V161 AIR 2,00 / RAIL 0,75 — **variante élue**",
    "v161coeff": "V161 AIR 2,50 / RAIL 0,75 — coefficient AIR augmenté",
    "v161cap": "V161 AIR 2,00 / RAIL 0,75 × C121 N1/N2 — choix moteur étendu",
}
PYLR_ITEMS = (
    ("Recettes AIR", "aircraft_revenue", True),
    ("Recettes RAIL", "train_revenue", True),
    ("Recettes ROUTE", "road_vehicle_revenue", True),
    ("Recettes NAVAL", "ship_revenue", True),
    ("Exploitation AIR", "aircraft_running", False),
    ("Exploitation RAIL", "train_running", False),
    ("Exploitation ROUTE", "road_running", False),
    ("Exploitation NAVAL", "ship_running", False),
    ("Construction tous modes", "construction_all_modes", False),
    ("Véhicules neufs moins ventes, tous modes", "new_vehicles_net_all_modes", False),
    ("Autres (y compris actions municipales)", "other_including_town_actions", False),
    ("Intérêts d'emprunt", "loan_interest", False),
)


def load(name):
    return json.loads((DOCS / name).read_text(encoding="utf-8"))


def money(n):
    return f"{n:,.2f}".replace(",", " ").replace(".", ",")


def count(n):
    return f"{n:,.2f}".replace(",", " ").replace(".", ",")


def percentage(n, digits=2):
    return f"{n:.{digits}f}".replace(".", ",") + " %"


def line(*cells):
    return "| " + " | ".join(map(str, cells)) + " |"


def build_report():
    data = load("estim31_top3_20x10_20261030.json")
    trajectory = load("estim31_top3_decade_trajectory_20261030.json")
    frozen = load("estim31_top3_frozen_20261030.json")
    ranked = data["ranked_healthy_20x10"]
    names = [(r["suite"], r["name"]) for r in ranked]
    assert len(ranked) == 3 and len(set(names)) == 3
    assert [r["suite"] for r in ranked] == ["v161", "v161coeff", "v161cap"]
    source_paths = ["estim31_top3_20x10_20261030.json",
                    "estim31_top3_decade_trajectory_20261030.json",
                    "estim31_top3_frozen_20261030.json"]
    seeds = data["same_seed_set"]
    assert len(seeds) == 20 and len(set(seeds)) == 20
    by_trajectory = {(c["suite"], c["name"]): c
                     for c in trajectory["qualified_candidates"]}
    by_frozen = {(c["suite"], c["name"]): c
                 for c in frozen["locked_40x5_ranking"]}
    assert set(by_trajectory) == set(by_frozen) == set(names)

    out = [
        "# ESTIM-31 — résultats documentés des trois finalistes 20 graines × 10 ans",
        "",
        "**Date de qualification : 30 octobre 2026 — 1970–1979, OpenTTD 15.3,",
        "AAAHogEx-115, carte 256², huit workers, un seul Docker.** Ce rapport",
        "est reconstruit de manière déterministe depuis les archives JSON déjà",
        "publiées ; **aucune nouvelle partie n'a été lancée**.",
        "",
        "## 1. Protocole et paramètres figés",
        "",
        "- Chaque candidat est qualifié séparément, avec son propre témoin",
        "  `OpexAI[probes=2]` (ancien comportement OFF), contre AAAHogEx.",
        "  **20 graines identiques**, 40/40 parties saines par candidat,",
        "  **dix points annuels** au 1er décembre de 1970 à 1979 pour les",
        "  deux compagnies de chaque bras (`off` et `variant`). Les comptes PLYR",
        "  de 1979 proviennent des sauvegardes finales contrôlées.",
        "- Chaque variante a `estim_unifie=31`, `eb14_progressive=3`,",
        "  `probes=2`, V161 rendement marginal, poids d'a priori **15**,",
        "  profil RAIL **incliné**, `v249_statue=2`, `eb2_fallback=0`,",
        "  `air_load_min_pct=0`, coefficient RAIL **0,75**.",
        "  Seuls le coefficient AIR et/ou le sélecteur moteur C121 changent",
        "  dans ce trio. L'option C121 N1/N2 du troisième n'est **pas** le",
        "  choix moteur exhaustif N1 du gagnant publié.",
        "- **Critère de sélection exclusif** :",
        "  `100 × moyenne20(profit_year OpexAI au 1979-12-01) /",
        "  moyenne20(profit_year AAAHogEx au 1979-12-01)` **dans le même duel**.",
        "  Ne pas prendre la moyenne des 20 ratios individuels ; les ratios",
        "  par graine ci-dessous sont purement descriptifs. Aucun veto",
        "  Wilcoxon/IC95/valeur de société n'entre dans cette élection.",
        "- Le top3 a été **figé après les 40×5**, puis testé sur une",
        "  cohorte **20×10**. Une différence entre variantes",
        "  observée dans deux duels autonomes n'est pas une mesure",
        "  causale directe à adversaire identique : les profits AAA peuvent",
        "  varier d'une campagne à l'autre.",
        "",
        "### Configurations individuelles (sources gelées)",
        "",
        line("Rang 10 ans", "Suite", "Coefficient AIR", "Coefficient RAIL", "Poids",
             "Profil RAIL", "Moteur C121", "Rang 40×5"),
        line("---:", "---", "---:", "---:", "---:", "---", "---", "---:"),
    ]
    for i, r in enumerate(ranked, 1):
        cfg = by_frozen[(r["suite"], r["name"])]["configuration"]
        assert cfg["eb14"] == 3 and cfg["v249_statue"] == 2
        assert cfg["eb2_fallback"] == 0 and cfg["air_load_min_pct"] == 0
        assert not cfg["flat_rail"] and cfg["rail"] == .75 and cfg["weight"] == 15
        assert r["source_bundle_sha256"] == by_frozen[(r["suite"], r["name"])]["source_bundle_sha256"]
        assert abs(r["ratio_40x5_pct"] - by_frozen[(r["suite"], r["name"])]["ratio_40x5_pct"]) < 1e-10
        out.append(line(i, "`" + r["suite"] + "/" + r["name"] + "`",
                        count(cfg["air"]), count(cfg["rail"]), count(cfg["weight"]),
                        "incliné", "**N1/N2**" if r["suite"] == "v161cap" else "**N1 complet**",
                        {"v161": 3, "v161coeff": 2, "v161cap": 1}[r["suite"]]))

    out.extend(["", "## 2. Classement économique — 1979 et changement de rang", "",
                line("Rang à 10 ans", "Variante", "40×5 / 1974", "20×10 / 1979",
                     "Profit Opex 1979 (£/an)", "Profit AAA 1979 (£/an)",
                     "Écart Opex−AAA (£/an)", "Victoires / 20"),
                line("---:", "---", "---:", "---:", "---:", "---:", "---:", "---:"),
                ])
    for i, r in enumerate(ranked, 1):
        assert r["health"] == "40/40 complete"
        assert r["source_provenance"] == "40x5 frozen SHA matches 20x10 and all annual checkpoints"
        assert len(r["pairs"]) == 20 and set(map(int, r["pairs"])) == set(seeds)
        ratio = 100 * r["opex_profit_mean"] / r["aaa_profit_mean"]
        assert abs(ratio - r["ratio_pct"]) < 1e-8
        assert abs(r["opex_profit_mean"] - r["aaa_profit_mean"] - r["paired_profit_difference_mean"]) < 1e-6
        assert sum(p["opex"] > p["aaa"] for p in r["pairs"].values()) == r["opex_wins"]
        out.append(line(i, TITLES[r["suite"]], percentage(r["ratio_40x5_pct"], 9),
                        "**" + percentage(r["ratio_pct"], 9) + "**" if i == 1 else percentage(r["ratio_pct"], 9),
                        money(r["opex_profit_mean"]), money(r["aaa_profit_mean"]),
                        money(r["paired_profit_difference_mean"]), r["opex_wins"]))
    out.extend(["", "**Changement de classement :** N1/N2 passe de **1er**",
                "sur 40×5 à **3e** sur 20×10 ; le V161 N1 AIR2,00 passe de",
                "**3e** à **1er**. Les résultats décennaux montrent un",
                "décrochage partagé à partir de 1975. Le classement est",
                "celui **effectivement observé**, pas une preuve que",
                "le remplacement N1 par N1/N2 cause à lui seul ce décrochage.",
                "", "### Témoins OFF propres aux trois duels à 10 ans", "",
                line("Variante", "Ratio OFF (20×10)", "Ratio ON (20×10)", "Écart descriptif (points)",
                     "Profit Opex OFF", "Profit AAA OFF"),
                line("---", "---:", "---:", "---:", "---:", "---:"),
                ])
    for r in ranked:
        off = r["own_off"]
        out.append(line("`" + r["suite"] + "`", percentage(off["ratio_pct"], 6),
                        percentage(r["ratio_pct"], 6),
                        f"{r['ratio_pct'] - off['ratio_pct']:+.6f}".replace(".", ","),
                        money(off["opex_profit_mean"]), money(off["aaa_profit_mean"])))
    out.extend(["", "Le bras OFF permet de situer chaque politique par rapport",
                "à la référence historique du **propre essai**. Ses données",
                "ne doivent pas être combinées avec un bras d'une autre",
                "campagne comme un essai causal strictement synchronisé.",
                "", "## 3. Résultats complets, variante par variante", ""])

    for i, r in enumerate(ranked, 1):
        suite, name = r["suite"], r["name"]
        cand = by_trajectory[(suite, name)]
        assert cand["campaign"] == r["campaign"]
        assert cand["source_bundle_sha256"] == r["source_bundle_sha256"]
        years = cand["years"]
        assert len(years) == 10 and [y["date"] for y in years] == [f"{yr}-12-01" for yr in range(1970, 1980)]
        last = years[-1]["variant"]
        assert abs(last["ratio_of_means_pct"] - r["ratio_pct"]) < 1e-9
        assert abs(last["opex"]["profit_year"] - r["opex_profit_mean"]) < 1e-6
        assert abs(last["aaa"]["profit_year"] - r["aaa_profit_mean"]) < 1e-6
        acc_name = ACCOUNT_FILES[suite]
        accounts = load(acc_name)
        source_paths.append(acc_name)
        assert accounts["source_bundle_sha256"] == r["source_bundle_sha256"]
        assert accounts["healthy_games"] == 40
        assert accounts["paired_seeds"] == len(seeds)
        pay = accounts["mean_1979_ytd_net_postings"]
        o = pay[r["policy_id"] + ":OpexAI"]
        a = pay[r["policy_id"] + ":AAAHogEx"]

        out.extend([
            f"### {i}. {TITLES[suite]}", "",
            f"**Identité :** `{suite}/{name}` ; campagne",
            f"`{r['campaign']}` ; **source SHA-256** :",
            f"`{r['source_bundle_sha256']}`. Les états Opex/AAA sont tous",
            "issus de cette campagne, pas d'un adversaire emprunté à",
            "l'une des deux autres.", "",
            f"**Bilan final :** {percentage(r['ratio_pct'], 9)} AAAHogEx ;",
            f"Opex **{money(r['opex_profit_mean'])} £/an**, AAA",
            f"**{money(r['aaa_profit_mean'])} £/an** ; différence",
            f"**{money(r['paired_profit_difference_mean'])} £/an** ;",
            f"**{r['opex_wins']}/20** graines où Opex gagne.", "",
            "#### Trajectoire annuelle (1er décembre, moyennes sur 20 graines)", "",
            line("Année", "Opex (£/an)", "AAA (£/an)", "Opex/AAA", "OFF/AAA",
                 "Avions Opex/AAA", "Trains Opex/AAA", "Aéroports Opex/AAA", "Caisse Opex (£)"),
            line("---:", "---:", "---:", "---:", "---:", "---:", "---:", "---:", "---:"),
        ])
        for y in years:
            v = y["variant"]
            off = y["off"]
            out.append(line(y["date"][:4], money(v["opex"]["profit_year"]),
                            money(v["aaa"]["profit_year"]), percentage(v["ratio_of_means_pct"]),
                            percentage(off["ratio_of_means_pct"]),
                            f"{count(v['opex']['aircraft_stock'])}/{count(v['aaa']['aircraft_stock'])}",
                            f"{count(v['opex']['train_stock'])}/{count(v['aaa']['train_stock'])}",
                            f"{count(v['opex']['airport_count'])}/{count(v['aaa']['airport_count'])}",
                            money(v["opex"]["cash"])))

        out.extend(["", "#### Parc, couverture et trésorerie au 01/12/1979", "",
                    line("Indicateur", "OpexAI", "AAAHogEx"),
                    line("---", "---:", "---:"),
                    ])
        for label, key, unit in (("Avions (stock)", "aircraft_stock", "count"),
                                 ("Trains (stock)", "train_stock", "count"),
                                 ("Aéroports", "airport_count", "count"),
                                 ("Villes avec aéroport", "airport_towns", "count"),
                                 ("Caisse (£)", "cash", "money"),
                                 ("Prêt en cours (£)", "current_loan", "money"),
                                 ("Moteur AIR 223 (stock survivant)", "air_engine_stock_223", "count"),
                                 ("Moteur AIR 228 (stock survivant)", "air_engine_stock_228", "count"),
                                 ("Moteur AIR 220 (stock survivant)", "air_engine_stock_220", "count")):
            fmt = money if unit == "money" else count
            out.append(line(label, fmt(last["opex"][key]), fmt(last["aaa"][key])))

        out.extend(["", "#### Écritures PLYR réellement enregistrées — 1979 YTD au 1er décembre", "",
                    f"Source : [`{acc_name}`]({acc_name}).",
                    "Les recettes sont présentées en valeur positive (le",
                    "fichier PLYR stocke les recettes avec un signe négatif) ;",
                    "les dépenses sont des écritures **nettes**.", "",
                    line("Poste moyen (£/monde)", "OpexAI", "AAAHogEx"),
                    line("---", "---:", "---:"),
                    ])
        for label, key, is_income in PYLR_ITEMS:
            sign = -1 if is_income else 1
            out.append(line(label, money(sign * o[key]), money(sign * a[key])))

        out.extend(["", "#### Les vingt paires de graines — profit annuel 1979", "",
                    "La colonne « ratio individuel » est **descriptive** et",
                    "n'est **pas** la métrique de classement, laquelle",
                    "repose sur le ratio **des deux moyennes**.", "",
                    line("Graine", "OpexAI (£/an)", "AAAHogEx (£/an)",
                         "Écart Opex−AAA (£/an)", "Ratio individuel"),
                    line("---:", "---:", "---:", "---:", "---:"),
                    ])
        for seed in seeds:
            pair = r["pairs"][str(seed)]
            out.append(line(seed, money(pair["opex"]), money(pair["aaa"]),
                            money(pair["opex"] - pair["aaa"]),
                            percentage(100 * pair["opex"] / pair["aaa"])))
        out.extend(["", "**Limites de l'interprétation de cette variante :**",
                    "les stocks de moteurs sont **survivants à une date** et",
                    "non des achats ; les achats de véhicules PLYR sont",
                    "**nets des ventes** et **tous modes confondus** ;",
                    "« Autres » comprend les actions municipales sans",
                    "les attribuer uniquement aux statues. Les opcodes",
                    "observés dans ces qualifications sont **partiels**",
                    "(`opcodes_complete_all=false`), non une mesure du CPU",
                    "global. Aucune ventilation des revenus par ligne",
                    "ou du profit marginal d'un avion/train n'est prouvée",
                    "par ces tableaux.", ""])

    out.extend(["## 4. Conclusions documentaires et suites", "",
                "1. Le **défaut élu est bien le rang 1 à dix ans** :",
                "   `v161/mix_a200_r075_w15_slope`, AIR2,00, RAIL0,75,",
                "   poids15, pente RAIL, V161 same-engine, C121 scan",
                "   **N1 exhaustif**, `estim_unifie=31`, EB14=3 et `probes=2`.",
                "   La variante AIR2,50 et la variante N1/N2 sont",
                "   **mesurées mais non adoptées**, et leurs verdicts",
                "   ne doivent pas être rouverts en tant que simple",
                "   nouveau candidat sans nouvelle hypothèse.",
                "2. Les trois trajectoires passent de plus de **100 %**",
                "   à moins de **100 %** entre le 1er décembre 1974 et",
                "   celui de 1975, et convergent vers **65–67 %** en",
                "   1979. Le phénomène est **commun** aux trois variantes,",
                "   pas un incident propre au sélecteur C121 N1/N2.",
                "3. Les stocks ferroviaires croissent peu chez Opex",
                "   relativement à AAA, alors qu'Opex conserve une",
                "   trésorerie importante. En AIR, plus d'avions ne",
                "   signifie pas plus de recettes. Ce sont des",
                "   **symptômes**, non la preuve qu'une extension ou",
                "   réduction de flotte supplémentaire serait rentable.",
                "4. La priorité de diagnostic reste **POST-1974-ENTONNOIR**",
                "   puis **RAIL-RENDEMENT-TARDIF** et **AIR-PRODUCTIVITÉ**.",
                "   Un nouveau `1×10` loggé ne sera envisagé que si les",
                "   artefacts déjà conservés ne permettent pas de",
                "   distinguer les motifs exacts de rejet tardif.", "",
                "Références de travail : [liste active](taches.md),",
                "[analyse des priorités](estim31_priorites_20x10_20261030.md),",
                "[protocole et promotion](estim31_phase_combinatoire_20261030.md),",
                "[validation du défaut](estim31_default_validation_20261030.md).",
                "", "## 5. Sources immuables et reproduction", "",
                "Sources **déjà archivées**, aucune campagne redémarrée :", ""])
    for name in dict.fromkeys(source_paths):
        out.append(f"- [`{name}`]({name})")
    out.extend(["", "Le rapport est généré par",
                "[`sweeps/estim31_document_three_finalists_20261030.py`](../sweeps/estim31_document_three_finalists_20261030.py).",
                "Pour le reproduire :", "", "```powershell",
                "python -X utf8 sweeps/estim31_document_three_finalists_20261030.py",
                "python -X utf8 sweeps/estim31_document_three_finalists_20261030.py --check",
                "```", ""])
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Verify the report without writing")
    args = parser.parse_args()
    expected = build_report()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != expected:
            parser.exit(1, "Report missing/stale; regenerate it.\n")
        print("ESTIM31 3×20×10 report matches all JSON sources")
    else:
        OUTPUT.write_text(expected, encoding="utf-8", newline="\n")
        print(f"Wrote {OUTPUT.relative_to(DOCS.parent)} ({len(expected.splitlines())} lines)")


if __name__ == "__main__":
    main()
