# Rapport d'analyse causale : Décrochage de la graine 100 face aux graines 999, 1234 et 5678 (Chantier C116 / AC04-A)

**Date :** 12 octobre 2026  
**Auteur :** Antigravity (d'après les données d'exécution de référence 3 ans, duel AAAHogEx)  
**Cible d'analyse :** ligne historique « C116 graine 100 » de l'[ancien registre archivé](journaux/journal_2026-10-30_transfert_taches.md) (ligne originale 774) : *« Chronologie cash/projets face à 999/1234/5678 dans C116.2 ; aucune nouvelle règle ni 20×10 sous les formulations rejetées. »*
**Fichiers analysés :**
- `results/afm_probe_5x3_20261012_engine/reference_seed{100,999,1234,5678}_r0.log` (logs moteur OpenTTD avec `--script-debug` et `probe_air_finance_margin=1`)
- `results/afm_probe_5x3_20261012.jsonl` (36 checkpoints mensuels complets par graine, compteurs physiques et financiers)
- `results/afm_probe_5x3_20261012.json` et `results/afm_probe_5x3_20261012.launcher.out` (synthèse appariée et bilans consolidés)

---

## 1. Contexte, définition de C116 / C116.2 et ce qui a été rejeté

### 1.1 Définition de C116 et ses formulations successives
Le chantier **C116** visait initialement à introduire un régulariseur de capital lors du choix du moteur d'avion (`AIR`), inspiré de l'hypothèse selon laquelle le gain accidentel de C100 provenait d'une pénalisation des surcoûts d'équipement marginaux peu rentables ([`docs/archives/c116_extraits_originaux_non_autoritaires_2026-09-30.md:27`](../docs/archives/c116_extraits_originaux_non_autoritaires_2026-09-30.md#L27)). Quatre formulations ont été explorées :

1. **C116.1 (Marginal hurdle / gate) :** Évaluation du surcoût marginal d'un moteur par rapport à un taux de rendement interne ou coût d'opportunité direct C69.  
   *Résultat :* Rejeté (**−176,5 k£/an** en 5×6 ; score C69 direct : **−234,4 k£/an**, [`docs/journaux/synthese_decisions_2026-09-30.md:49`](../docs/journaux/synthese_decisions_2026-09-30.md#L49)).
2. **C116.2 (Projet débloquable via frontière de portefeuille) :** Règle choisissant un moteur moins capitalistique si l'économie de capital $\Delta C$ permettait de combler le besoin de financement (`gap`) du meilleur projet AIR actuellement non finançable dans le snapshot du portefeuille (`OpexC116UnlockedProjectOpportunity`, [`ai/OpexAI/air_engine_choice.nut:1498-1512`](../ai/OpexAI/air_engine_choice.nut#L1498-L1512), [`ai/OpexAI/projects_selection.nut:810-874`](../ai/OpexAI/projects_selection.nut#L810-L874)).  
   *Résultat :* Rejeté avec une perte moyenne de **−330 k£/an** en 5×6, mais avec une **anomalie spectaculaire sur la graine 100 : +623,7 k£/an** ([`docs/journaux/synthese_decisions_2026-09-30.md:50`](../docs/journaux/synthese_decisions_2026-09-30.md#L50)).
3. **C116.3 (Gap exact du meilleur projet AIR en attente) :** Règle minimale $\Delta C \ge gap$ puis argmax de profit.  
   *Résultat :* Rejeté (**−283,0 k£/an** en 5×6 causal, 1 victoire / 4 défaites, ratio de valeur −18,05 % ; graine 100 retombée à seulement +4,4 k£/an, graine 5678 à −707,7 k£/an ; [`docs/archives/c116_extraits_originaux_non_autoritaires_2026-09-30.md:15`](../docs/archives/c116_extraits_originaux_non_autoritaires_2026-09-30.md#L15)).
4. **C116.4 (Découplage complet admission / équipement) :** Le portefeuille conserve le classement C68 strict ; `OpexC116ChooseBuildPlan` clone le plan au moment de l'achat pour sélectionner un moteur moins cher si $\Delta C \ge gap$ du projet en attente ([`ai/OpexAI/air_engine_choice.nut:1539-1623`](../ai/OpexAI/air_engine_choice.nut#L1539-L1623)).  
   *Résultat :* Rejeté contre C115 courant (**−166,6 k£/an**, valeur −11,55 %, garde de valeur échouée dans `smoke_c116_decoupled_1x3_20260927_r1`).

### 1.2 Décisions arrêtées et limites méthodologiques
- **Décision ferme à la date du 12/10 :** `C116 = 0` par défaut ; **aucun 20×10 sous les formulations rejetées** ([ancien registre, lignes 774 et 792](journaux/journal_2026-10-30_transfert_taches.md)).
- **Interdiction formelle :** Ne proposer aucune nouvelle règle de cap ou de marge déjà rejetée ; ne pas modifier le catalogue AIR.
- **Rôle de l'autopsie graine 100 et d'AC04-A v3 :** L'autopsie du 12/10 ([`docs/autopsie_air_graine100_20261012.md`](../docs/autopsie_air_graine100_20261012.md)) a démontré que la graine 100 subit en partie un blocage AIR structurel lié au reclassement erroné de hubs saturés en orphelins à `routes=0`. Ce bug a été corrigé et adopté le 12/10 sous **AC04-A v3** (`ac04_hub_usage_gate=1`, [`docs/ac04a_v3_adoption_20261012.md`](../docs/ac04a_v3_adoption_20261012.md)).

---

## 2. Données analysées et ce qui n'est pas mesurable

### 2.1 Périmètre des données
Les données proviennent de la campagne `afm_probe_5x3_20261012` exécutée sur la version de référence (commit `29dac01`, défauts **AVANT** AC04-A v3, 3 ans de jeu 1970–1972 en duel contre AAAHogEx) :
- Les checkpoints mensuels complets (36 par graine, du 1er janvier 1970 au 1er décembre 1972) sont enregistrés dans `afm_probe_5x3_20261012.jsonl`.
- La sonde d'exposition `probe_air_finance_margin=1` a émis dans les logs moteur `reference_seed{100,999,1234,5678}_r0.log` les événements `AIR_FINANCE_SELECT`, `AIR_FINANCE_TRY`, `AIR_FINANCE_FIRST_REVENUE` et `AIR_FINANCE_PENDING`.
- Les constructions AIR et de flotte sont tracées par `C121_BUILD` et `[FLEET_PROJECT]`.

### 2.2 Ce qui N'EST PAS mesurable dans ce jeu de données
1. **Marqueurs de décision générale absents (`decision_log=0`) :** Bien que la consigne mentionne `decision_log=1`, l'audit de la configuration réelle dans `results/afm_probe_5x3_20261012.json` (`explicit_settings: [['probe_air_finance_margin', 1]]`) confirme que `decision_log` est resté à sa valeur par défaut **0** ([`ai/OpexAI/info.nut:30`](../ai/OpexAI/info.nut#L30)). En conséquence, la garde `if (!DECISION_LOG && !C56_TASK_TRACE) return;` ([`ai/OpexAI/probes.nut:45`](../ai/OpexAI/probes.nut#L45)) a court-circuité `OpexDecide`. Les lignes textuelles directes telles que `PROJECT_CHOSEN`, `PROJECT_DISCARD reason=batch_plan_dead`, `RAIL_ATTEMPT`, `RAIL_BUILD`, `LOAN` et `REPORT` **ne sont pas imprimées dans les logs moteur**.
2. **Mesure indirecte des rejets de vivier :** Les rejets `batch_plan_dead` ne peuvent pas être lus mot à mot dans ces logs 3 ans (contrairement au run 5×6 de l'autopsie où `decision_log=1` était actif), mais leurs conséquences physiques (stagnation des aéroports, caisse dormante, blocage du vivier aux passages) sont rigoureusement documentées par les checkpoints mensuels.
3. **Consommation d'opcodes par fonction :** Les opcodes CPU totaux sont disponibles par an (`h5.observed-v1`), mais la décomposition détaillée par tâche ou par calcul de tracé A* rail n'est pas mesurable sans les sondes `probe_span_trace` ou `probe_portfolio`.

---

## 3. Chronologies mensuelles 1970–1972 : Graine 100 face à 999, 1234 et 5678

Les données ci-dessous proviennent des checkpoints synchrones au 1er de chaque mois (`afm_probe_5x3_20261012.jsonl`), croisées avec les événements de construction du log moteur.

### 3.1 Graine 100 (La graine en décrochage)
- **Bilan terminal à 3 ans :** Valeur 2 271 359 £ | Profit annuel 1 113 392 £ | Caisse 38 201 £ | Emprunt 300 000 £ (non remboursé) | Véhicules 56 (49 avions, 7 trains) | Stations 41 (29 aéroports, 6 gares rail).

| Mois | Trésorerie (£) | Emprunt (£) | Profit ann. (£/an) | Profit cum. (£) | Lignes AIR bâties | Avions flotte ajoutés | Aéroports cum. | Avions cum. | Trains | Refus AIR (Marge/Cap/Fail) | Top_mode du portefeuille |
|:---|---:|---:|---:|---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **1970-01** | 100 000 | 100 000 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 / 0 / 1 (AFAIL) | air:9 / none:8 |
| **1970-02** | 61 231 | 300 000 | 0 | 0 | 0 | 0 | 6 | 3 | 0 | 0 / 0 / 0 | none:28 |
| **1970-03** | 59 464 | 300 000 | 0 | 0 | 0 | 0 | 6 | 3 | 0 | 0 / 0 / 0 | none:17 |
| **1970-04** | 57 563 | 300 000 | 0 | 0 | 1 | 0 | 6 | 3 | 0 | 0 / 0 / 0 | air:2 / none:33 |
| **1970-05** | 18 554 | 300 000 | −4 150 | −4 150 | 0 | 1 | 7 | 4 | 0 | 0 / 0 / 0 | fleet:2 / none:17 |
| **1970-06** | 42 157 | 300 000 | −4 150 | −4 150 | 1 | 1 | 7 | 5 | 0 | 0 / 0 / 0 | air:3 / fleet:1 / none:22 |
| **1970-07** | 44 382 | 300 000 | −4 150 | −4 150 | 0 | 1 | 8 | 7 | 0 | 0 / 0 / 0 | fleet:2 / none:28 |
| **1970-08** | 40 481 | 300 000 | 172 935 | 177 085 | 1 | 0 | 8 | 8 | 0 | 0 / 0 / 0 | air:3 / none:24 |
| **1970-09** | 38 250 | 300 000 | 172 935 | 177 085 | 0 | 0 | 9 | 9 | 0 | 0 / 0 / 0 | air:1 / none:24 |
| **1970-10** | 49 742 | 300 000 | 172 935 | 177 085 | 2 | 0 | 11 | 10 | 0 | 0 / 0 / 0 | air:1 / none:18 |
| **1970-11** | 40 724 | 300 000 | 353 760 | 180 825 | 1 | 0 | 13 | 11 | 0 | 0 / 0 / 0 | air:1 / none:28 |
| **1970-12** | 59 158 | 300 000 | 353 760 | 180 825 | 1 | 1 | 14 | 12 | 0 | 0 / 0 / 0 | air:1 / fleet:2 / none:26 |
| **1971-01** | 33 744 | 300 000 | 353 760 | 180 825 | 0 | 0 | 15 | 14 | 0 | 0 / 0 / 0 | none:17 / rail:3 |
| **1971-02** | 48 342 | 300 000 | 571 651 | 217 891 | 0 | 0 | 15 | 14 | 1 | 0 / 0 / 0 | none:11 / rail:4 |
| **1971-03** | 53 118 | 300 000 | 571 651 | 217 891 | 2 | 0 | 15 | 14 | 3 | 0 / 0 / 0 | air:3 / none:20 |
| **1971-04** | 39 704 | 300 000 | 571 651 | 217 891 | 0 | 1 | 17 | 16 | 3 | 0 / 0 / 0 | air:1 / fleet:2 / none:30 |
| **1971-05** | 100 277 | 300 000 | 828 218 | 252 417 | 1 | 1 | 17 | 17 | 3 | 0 / 0 / 0 | air:2 / fleet:1 / none:15 / road:1 |
| **1971-06** | 63 432 | 300 000 | 828 218 | 252 417 | 1 | 0 | 18 | 19 | 3 | 0 / 0 / 0 | air:1 / none:29 |
| **1971-07** | 87 129 | 300 000 | 828 218 | 252 417 | 2 | 0 | 19 | 19 | 3 | 0 / 0 / 0 | air:2 / none:25 |
| **1971-08** | 62 054 | 300 000 | 933 463 | 282 330 | 2 | 0 | **20** | 20 | 3 | 0 / 0 / 0 | air:2 / none:23 |
| **1971-09** | 56 870 | 300 000 | 933 463 | 282 330 | 3 | 0 | **20** | 22 | 3 | 0 / 0 / 0 | air:4 / none:18 |
| **1971-10** | 40 689 | 300 000 | 933 463 | 282 330 | 2 | 0 | **20** | 25 | 3 | 0 / 0 / 0 | air:3 / none:32 |
| **1971-11** | 50 239 | 300 000 | 998 822 | 246 184 | 2 | 0 | **20** | 27 | 3 | 0 / 0 / 0 | air:2 / none:29 |
| **1971-12** | 65 448 | 300 000 | 998 822 | 246 184 | 3 | 0 | **20** | 29 | 3 | 0 / 0 / 0 | air:4 / none:22 |
| **1972-01** | 58 763 | 300 000 | 998 822 | 246 184 | 0 | 0 | **20** | 32 | 3 | 0 / 0 / 0 | *(aucun scan AIR)* |
| **1972-02** | 157 276 | 300 000 | 1 071 828 | 290 897 | 0 | 0 | **20** | 32 | 3 | 0 / 0 / 0 | rail:2 / road:1 |
| **1972-03** | 217 439 | 300 000 | 1 071 828 | 290 897 | 1 | 0 | **20** | 32 | 3 | 0 / 0 / 1 (BFAIL) | air:1 / rail:1 |
| **1972-04** | 221 187 | 300 000 | 1 071 828 | 290 897 | 0 | 5 | 21 | 33 | 3 | 0 / 0 / 0 | fleet:10 / rail:1 |
| **1972-05** | 122 304 | 300 000 | 1 082 584 | 263 173 | 1 | 2 | 21 | 38 | 3 | 0 / 0 / 0 | none:9 / rail:4 / road:2 |
| **1972-06** | 53 599 | 300 000 | 1 082 584 | 263 173 | 0 | 0 | 22 | 41 | 4 | 0 / 0 / 0 | none:3 / rail:6 |
| **1972-07** | 149 512 | 300 000 | 1 082 584 | 263 173 | 1 | 0 | 22 | 41 | 4 | 0 / 0 / 0 | rail:2 |
| **1972-08** | 171 748 | 300 000 | 1 105 191 | 304 937 | 1 | 0 | 24 | 42 | 4 | 0 / 0 / 2 (BFAIL) | none:8 / rail:4 |
| **1972-09** | 77 829 | 300 000 | 1 105 191 | 304 937 | 0 | 0 | 26 | 43 | 5 | 0 / 0 / 0 | none:10 / rail:6 |
| **1972-10** | 92 505 | 300 000 | 1 105 191 | 304 937 | 3 | 0 | 26 | 43 | 7 | 0 / 0 / 1 (BFAIL) | none:6 / rail:17 |
| **1972-11** | 34 532 | 300 000 | 1 113 392 | 254 385 | 3 | 0 | 29 | 46 | 7 | 0 / 0 / 0 | none:15 / rail:15 |
| **1972-12** | 38 201 | 300 000 | 1 113 392 | 254 385 | 2 | 0 | 29 | 49 | 7 | 0 / 0 / 0 | air:1 / none:19 / rail:6 |

---

### 3.2 Graine 999 (Réseau compact, haute rentabilité)
- **Bilan terminal à 3 ans :** Valeur 3 101 787 £ | Profit annuel 1 659 857 £ | Caisse 285 241 £ | Emprunt **0 £ (intégralement remboursé)** | Véhicules 40 (37 avions, 3 trains) | Stations 36 (32 aéroports, 4 gares rail).
- **Profil clé :** Seulement 30 lignes AIR construites (contre 40 pour la 100), mais profit moyen par ligne **156 347 £/an** (presque le double de la graine 100). Dès le printemps 1972, la caisse dépasse 300 000 £ : l'emprunt est remboursé progressivement (170 k£ en mai, 50 k£ en juin, 30 k£ en juillet, 0 £ en août 1972, [`ai/OpexAI/capital.nut:81`](../ai/OpexAI/capital.nut#L81)).

| Mois | Trésorerie (£) | Emprunt (£) | Profit ann. (£/an) | Profit cum. (£) | Lignes AIR bâties | Avions flotte ajoutés | Aéroports cum. | Avions cum. | Trains | Top_mode du portefeuille |
|:---|---:|---:|---:|---:|:---:|:---:|:---:|:---:|:---:|:---|
| **1970-12** | 71 527 | 300 000 | 284 133 | 139 191 | 1 | 1 | 8 | 8 | 0 | air:2 / fleet:1 / none:24 |
| **1971-06** | 132 872 | 300 000 | 785 644 | 333 042 | 2 | 0 | 15 | 13 | 2 | air:5 / none:18 / rail:6 |
| **1971-12** | 63 936 | 300 000 | 1 226 029 | 331 214 | 2 | 0 | 25 | 24 | 2 | air:2 / none:42 |
| **1972-03** | 343 158 | 300 000 | 1 475 022 | 466 495 | 1 | 0 | 25 | 25 | 2 | none:1 |
| **1972-05** | 321 561 | **170 000** | 1 527 846 | 385 866 | 0 | 0 | 26 | 27 | 2 | air:1 / none:1 |
| **1972-08** | 352 865 | **0** | 1 605 207 | 421 632 | 1 | 0 | 27 | 30 | 3 | air:1 / none:1 / rail:2 |
| **1972-12** | 285 241 | **0** | 1 659 857 | 385 864 | 2 | 0 | 32 | 37 | 3 | air:3 / none:26 |

---

### 3.3 Graine 1234 (Croissance soutenue de flotte)
- **Bilan terminal à 3 ans :** Valeur 2 457 523 £ | Profit annuel 1 560 083 £ | Caisse 51 861 £ | Emprunt 300 000 £ | Véhicules 64 (60 avions, 4 trains) | Stations 37 (33 aéroports, 5 gares rail).
- **Profil clé :** 44 lignes AIR bâties et 20 avions ajoutés par la flotte. Forte expansion en 1972 : le profit passe de 748 k£ fin 1971 à 1 560 k£ fin 1972 (+812 k£/an en 1972).

| Mois | Trésorerie (£) | Emprunt (£) | Profit ann. (£/an) | Profit cum. (£) | Lignes AIR bâties | Avions flotte ajoutés | Aéroports cum. | Avions cum. | Trains | Top_mode du portefeuille |
|:---|---:|---:|---:|---:|:---:|:---:|:---:|:---:|:---:|:---|
| **1970-12** | 36 295 | 300 000 | 432 607 | 185 873 | 1 | 0 | 10 | 10 | 0 | air:1 / none:31 |
| **1971-06** | 84 197 | 300 000 | 517 820 | 136 565 | 1 | 1 | 14 | 12 | 2 | air:2 / fleet:4 |
| **1971-12** | 84 830 | 300 000 | 748 137 | 281 698 | 1 | 2 | 22 | 21 | 2 | air:2 / fleet:5 / none:17 |
| **1972-04** | 151 401 | 300 000 | 930 410 | 304 316 | 2 | 1 | 24 | 30 | 4 | air:5 / fleet:1 / road:2 |
| **1972-08** | 46 520 | 300 000 | 1 403 974 | 399 265 | 4 | 0 | 33 | 42 | 4 | air:4 / none:17 |
| **1972-12** | 51 861 | 300 000 | 1 560 083 | 437 807 | 3 | 1 | 33 | 60 | 4 | air:5 / fleet:1 / none:17 |

---

### 3.4 Graine 5678 (L'expansion dominante)
- **Bilan terminal à 3 ans :** Valeur 4 146 679 £ | Profit annuel 2 355 462 £ | Caisse 1 192 692 £ | Emprunt **0 £ (intégralement remboursé)** | Véhicules 66 (61 avions, 3 trains, 2 camions) | Stations 48 (42 aéroports, 4 gares rail, 2 arrêts route).
- **Profil clé :** Accélération massive dès 1971 (36 aéroports fin 1971). Dès mai 1972, l'emprunt est ramené à 0 £ et la trésorerie dépasse le million de livres.

| Mois | Trésorerie (£) | Emprunt (£) | Profit ann. (£/an) | Profit cum. (£) | Lignes AIR bâties | Avions flotte ajoutés | Aéroports cum. | Avions cum. | Trains | Top_mode du portefeuille |
|:---|---:|---:|---:|---:|:---:|:---:|:---:|:---:|:---:|:---|
| **1970-12** | 93 838 | 300 000 | 402 797 | 256 837 | 2 | 0 | 14 | 11 | 0 | air:3 / none:23 |
| **1971-06** | 138 705 | 300 000 | 1 090 252 | 367 804 | 2 | 1 | 28 | 21 | 2 | air:3 / fleet:1 / none:10 / rail:6 |
| **1971-12** | 73 579 | 300 000 | 1 674 359 | 545 604 | 3 | 1 | 36 | 45 | 2 | air:14 / none:29 |
| **1972-04** | 709 804 | 300 000 | 1 912 643 | 553 575 | 1 | 0 | 36 | 50 | 2 | air:2 |
| **1972-05** | 503 407 | **0** | 2 207 289 | 662 450 | 1 | 0 | 37 | 51 | 2 | air:1 |
| **1972-08** | 909 700 | **0** | 2 314 279 | 552 650 | 1 | 2 | 38 | 54 | 3 | rail:2 |
| **1972-12** | 1 192 692 | **0** | 2 355 462 | 586 787 | 3 | 0 | 42 | 61 | 3 | rail:2 |

---

## 4. Où et pourquoi la graine 100 décroche (Date et Mécanismes)

### 4.1 Chronologie du décrochage
1. **1970 (Phase normale) :** En 1970, la graine 100 rivalise parfaitement avec les autres. Elle termine 1970 avec 10 lignes AIR, 14 aéroports et **353 760 £/an** de profit, soit **devant la graine 999** (284 k£) et proche de la graine 5678 (402 k£).
2. **Août à Décembre 1971 (Divergence structurelle) :**
   - Dès août 1971, le nombre d'aéroports de la graine 100 **se bloque à 20**.
   - Alors que les graines 5678 et 1234 continuent d'ouvrir agressivement des aéroports neufs (atteignant respectivement 36 et 22 aéroports fin 1971), la graine 100 construit **10 liaisons consécutives exclusivement en Hub-to-Hub** (`arm=hubhub`, `new_airports=0`).
   - Fin 1971, la graine 100 a empilé 28 lignes sur seulement 20 aéroports. Chaque petit aéroport communal étant borné à **3 routes maximum** (`OpexAirAirportMaxRoutes`, [`ai/OpexAI/task_air.nut:566`](../ai/OpexAI/task_air.nut#L566)), les 20 aéroports atteignent quasi tous leur **plafond physique de saturation**.
3. **Janvier à Mai 1972 (Décrochage économique franc) :**
   - Au 1er janvier 1972, le profit annualisé de la 100 est de 998 k£. Au 1er décembre 1972, il n'est que de 1 113 k£, soit **un gain dérisoire de +114 570 £/an sur TOUTE l'année 1972** !
   - Sur la même année 1972 :
     - Graine 999 : **+433 828 £/an**
     - Graine 5678 : **+681 103 £/an**
     - Graine 1234 : **+725 917 £/an**
   - La trésorerie de la graine 100 s'accumule sans s'investir : 157 k£ en février, 217 k£ en mars, 221 k£ en avril 1972. L'IA reste paralysée, incapable de déployer ce capital dans l'expansion aérienne.

---

## 5. Décomposition causale : Part expliquée par AC04-A vs Part restante

### 5.1 La part expliquée par l'anomalie AC04-A (Désormais corrigée par AC04-A v3)
L'anomalie AC04-A ([`docs/autopsie_air_graine100_20261012.md`](../docs/autopsie_air_graine100_20261012.md)) explique précisément la **paralysie d'expansion du premier semestre 1972** :

1. **Le mécanisme amont :** Dans `air_planning.nut:1364-1398` ([commit `9144dc5`](../docs/autopsie_air_graine100_20261012.md#L86-L103)), un hub saturé ($routeCount \ge 3$) subissait `if (routeCount >= maxRoutes) continue;` **avant** d'être inséré dans `seenStations`. La boucle 2 des aéroports orphelins (`orphanList`, ligne 1381) parcourait toutes les stations de la carte, ne trouvait pas ce hub saturé dans `seenStations`, et le reclassait comme un aéroport « orphelin » avec **`routes = 0`**.
2. **L'illusion au portefeuille :** Le générateur Hub-Hub appariait deux hubs saturés marqués à 0 route. Sans coût d'aéroport (`newAirports = 0`), le capital requis n'était que de **40 964 £** (l'appareil Bakewell LB-10 + 2 000 £ de marge). Ce plan Hub-Hub fantôme affichait un ROI et un `fundScore` artificiellement très élevés et s'installait en tête du portefeuille (`rank = 0`).
3. **Le blocage aval :** À l'exécution dans `_tryBuildProjects` ([`ai/OpexAI/task_projects.nut:1669-1683`](../ai/OpexAI/task_projects.nut#L1669-L1683)), la garde vivante `OpexAirBatchPlanStillLive` ([`ai/OpexAI/task_air.nut:571-604`](../ai/OpexAI/task_air.nut#L571-L604)) appelait `OpexAirBatchHubHasCapacity` ([`ai/OpexAI/task_air.nut:551-568`](../ai/OpexAI/task_air.nut#L551-L568)). Elle constatait la saturation réelle ($routes = 3 < 3$ faux) et rejetait le plan (`batch_plan_dead`).
4. **L'absence de purge :** Ligne 1682, `task_projects.nut` exécutait simplement `continue;` **sans retirer le plan de `this._projects.best`**. Entre deux passes, `OpexReselectProjects` reprenait le même vivier en cache et remettait le plan fantôme en tête. Le portefeuille était incapable d'accéder aux candidats inférieurs viables tant que le vivier n'était pas régénéré.
5. **Résolution par AC04-A v3 :** Le correctif adopté le 12/10 (`ac04_hub_usage_gate=1`, [`ai/OpexAI/air_planning.nut:1071-1085, 1464, 1755, 2486`](../ai/OpexAI/air_planning.nut#L1071-L1085)) contrôle les routes réelles au point d'usage via `OpexAir0310CountStationRoutes` et pose `ac04Blocked = true` sur les hubs saturés avant l'appariement. Ce blocage fantôme est donc **désormais éliminé**.

---

### 5.2 La part structurelle restante (Non expliquée par AC04-A)
La correction d'AC04-A n'efface pas tous les handicaps de la graine 100. Une part majeure du retard économique provient de facteurs environnementaux et architecturaux distincts :

#### 1. Démographie et topologie ultra-rurales de la graine 100
L'inspection des populations issues de `C96_SITE` dans les logs révèle une anomalie géographique massive :
- **Graine 100 :** Seulement **36 villes sur toute la carte**, population totale = **26 377 habitants**. Les 5 plus grandes villes cumulent seulement **7 471 habitants** (max 1 842 hab).
- **Graine 999 :** 45 villes, population totale = **44 608 habitants** (+69 %), top 5 = **15 303 habitants** (plus du double !).
- **Graine 5678 :** 46 villes, population totale = **49 282 habitants** (+87 %), top 5 = **15 683 habitants** (plus du double !).

#### 2. Épuisement précoce du gisement aérien rentable
Dès août 1971, OpexAI avait construit 20 aéroports sur la graine 100, soit **plus de 55 % de toutes les villes de la carte**. Les 16 villes restantes sont des villages minuscules (< 500 habitants) où le terrassement d'un aéroport communal (coûtant entre 30 000 £ et 85 000 £) ne produit pas assez de passagers pour rentabiliser l'infrastructure. C'est cet épuisement précoce qui a précipité l'IA dans l'empilement excessif de liaisons Hub-to-Hub dès 1971.

#### 3. Faible rendement unitaire des lignes et des véhicules
- Le profit annuel prédit moyen d'une ligne AIR sur la graine 100 n'est que de **82 279 £** (contre **156 347 £** sur la graine 999).
- Le profit réalisé par véhicule à 3 ans n'est que de **19 882 £/véhicule** sur la graine 100, contre **41 496 £/véhicule** sur la 999 et **35 688 £/véhicule** sur la 5678. Les lignes de la graine 100 transportent beaucoup moins de passagers et génèrent moitié moins de cash flow.

#### 4. Piège d'allocation : Re-flotte stérile et détour ferroviaire (V100)
- En avril 1972, face au blocage des ouvertures de lignes, OpexAI a injecté son capital dormant dans **5 avions de flotte supplémentaires** (`[FLEET_PROJECT]`). Sur des petites villes à faible génération de passagers, ces avions supplémentaires n'ont fait que diviser les flux sans augmenter le profit.
- De mai à novembre 1972, l'IA s'est tournée vers le rail (`top_mode=rail`, projet à 22 934 £ de profit prédit, score 606). Sous la contrainte du créneau de recherche ferroviaire sériel unique (V100, [ancien registre, ligne 795](journaux/journal_2026-10-30_transfert_taches.md)), l'IA a construit 4 trains supplémentaires (atteignant 7 trains fin 1972). Ces 7 trains ont absorbé du capital sans rien rapporter : entre août et décembre 1972, le profit annualisé n'a progressé que de **+8 201 £/an** !

#### 5. Impossibilité d'éteindre la dette
Le seuil de remboursement de l'emprunt est fixé par `LOAN_REPAY_FLOOR = 300 000 £` ([`ai/OpexAI/capital.nut:62`](../ai/OpexAI/capital.nut#L62)). Comme le cash flow de la 100 est faible, la trésorerie au 31 décembre de chaque année n'a jamais dépassé 65 000 £. L'emprunt de 300 000 £ est resté intact pendant les 3 ans, grevant les résultats financiers des intérêts d'emprunt. À l'inverse, les graines 999 et 5678 ont remboursé l'intégralité de leurs 300 000 £ de dette dès l'été 1972.

---

## 6. Pourquoi C116.2 semblait miraculeuse sur la graine 100 (+623 k£)

La compréhension de cette double cause éclaire parfaitement pourquoi **C116.2** avait obtenu un gain isolé de **+623,7 k£/an** sur la seule graine 100 :
1. Sur les graines à démographie normale (999, 1234, 5678), les lignes ont un fort potentiel de trafic. Remplacer un moteur standard performant par un moteur bas de gamme pour libérer du capital sacrifiait la capacité et le profit annuel, causant la défaite moyenne de **−330 k£/an**.
2. Sur la graine 100, les passagers sont si rares que les avions standards (Bakewell LB-10) volaient à moitié vides. Le moteur standard représentait un surinvestissement stérile. Dégrader le moteur libérait immédiatement 10 à 20 k£ de trésorerie (`ΔC`), ce qui débloquait le financement de chantiers alternatifs plus tôt dans une économie où le cash était constamment asphyxié.
3. **Néanmoins, C116.2 reste une fausse solution :** Elle reposait sur une heuristique de dégradation opportuniste qui détruisait l'économie de réseau partout ailleurs. La règle est rejetée, et la consigne de ne pas la réactiver reste rigoureusement respectée.

---

## 7. Synthèse des marqueurs et références de code vérifiées

| Élément | Rôle / Phénomène | Fichier et Lignes vérifiés |
|---|---|---|
| **AC04-A Bug amont** | Saut de `seenStations` avant `rawset` sur hub saturé | [`ai/OpexAI/air_planning.nut:1364-1398`](../ai/OpexAI/air_planning.nut#L1364-L1398) |
| **AC04-A v3 Correctif** | Validation au point d'usage via `OpexAC04ValidateHubsAtUsage` | [`ai/OpexAI/air_planning.nut:1071-1085, 1464, 1755, 2486`](../ai/OpexAI/air_planning.nut#L1071-L1085) |
| **Plafond routes Hub** | Capacité physique des aéroports communaux (3 routes max) | [`ai/OpexAI/task_air.nut:551-568`](../ai/OpexAI/task_air.nut#L551-L568) |
| **Garde vivante AIR** | Détection de saturation au moment de bâtir (`batch_plan_dead`) | [`ai/OpexAI/task_air.nut:571-604`](../ai/OpexAI/task_air.nut#L571-L604) |
| **Blocage du vivier** | Rejet silencieux sans purge du candidat dans le portefeuille | [`ai/OpexAI/task_projects.nut:1669-1683`](../ai/OpexAI/task_projects.nut#L1669-L1683) |
| **Sonde marge/capital** | Émission de `AIR_FINANCE_SELECT` (`blocked_margin`/`blocked_capital`) | [`ai/OpexAI/projects_selection.nut:2118-2145`](../ai/OpexAI/projects_selection.nut#L2118-L2145) |
| **Sonde tentative AIR** | Émission de `AIR_FINANCE_TRY` (`cash`, `need`, `outcome`) | [`ai/OpexAI/task_air.nut:755-775`](../ai/OpexAI/task_air.nut#L755-L775) |
| **Formule d'emprunt** | Plancher de remboursement (`LOAN_REPAY_FLOOR = 300 000 £`) | [`ai/OpexAI/capital.nut:50-87`](../ai/OpexAI/capital.nut#L50-L87) |
| **Goulot rail V100** | Créneau sériel unique de recherche ferroviaire (`_railSearch`) | [`ai/OpexAI/task_rail.nut:181-221`](../ai/OpexAI/task_rail.nut#L181-L221) |
| **Formule C116.2** | Opportunité de déblocage par économie d'équipement moteur | [`ai/OpexAI/air_engine_choice.nut:1498-1512`](../ai/OpexAI/air_engine_choice.nut#L1498-L1512) |

---

## Note de relecture (Claude, 12/10)

- Journaux antérieurs à AC04 v3 : la part « AC04-A » (paralysie du 1er semestre 1972) est attribuée par mécanisme, pas re-mesurée sous `ac04_hub_usage_gate=1`.
- Le reste est structurel : carte pauvre (26 k hab. contre 45-49 k), gisement aérien épuisé dès 1971, rendement par véhicule moitié moindre. Il n'appelle pas de règle propre à la graine 100 ; il confirme le constat général « flotte marginale stérile » ([[boucle flotte sur réseau statique]]) et le fil rail clos.
- **C116 clos** : aucune nouvelle règle ; une re-mesure de la graine 100 sous AC04 v3 viendra de tout banc ultérieur incluant cette graine.
