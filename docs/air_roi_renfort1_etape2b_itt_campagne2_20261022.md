# AIR-ROI-RENFORT-1 — étape 2b, campagne ITT 2 (22/10/2026)

> **ARCHIVE HISTORIQUE — ÉTUDE SUR ARBRE WIP LOCAL NON INTÉGRÉ (22/10/2026).** Ce rapport décrit une expérience menée sur le `master` local au HEAD `41031a7f`, avec des modifications non commitées. Le dispositif `air_roi_renfort1_itt` et son code expérimental ne sont **ni intégrés ni adoptés** dans la branche qui archive ce document. Malgré les **40 parties complètes**, la couverture des épisodes à 24 mois reste très inférieure au seuil préenregistré : les résultats conditionnels observés **ne qualifient ni un effet causal ITT ni un ROI marginal**, et aucune qualification économique V102 ou politique nouvelle n'en découle. Les journaux moteur, manifestes, télémétries et fichiers sous `results/` cités plus bas sont **locaux au WIP d'origine et non archivés ici**. Les chiffres et chemins ci-dessous sont conservés à titre de provenance historique.

**Verdict : `inconclusive`** selon l'amendement prospectif
§8 du protocole (signé avant toute collecte de cette campagne).
La politique p50 contre p0 est un diagnostic et ne constitue aucune porte V102.

## Identité, qualité et indépendance

- Campagne : `airr1_itt_month_20x10_20261022_b`, 10 ans, 40/40 parties, 20/20 paires.
- Bundle SHA256 : `169c1ee258383b306e2dfc9f7f2520a7a188553db77e70d822a62374abde1cdf` ; manifeste SHA256 : `3c96c0956e8d1c935ee29dee696a0afb78eedd6a3a4b79be0f1c24606f8d7c80`.
- Deux bras : `OpexAI[air_roi_renfort1_itt=1]` (p0) et `OpexAI[air_roi_renfort1_itt=2]` (p50), mêmes graines, AAAHogEx, quatre workers maximum ; conservation des logs moteur et de la télémétrie mensuelle.
- 20 graines indépendantes, une répétition : aucune pseudo-réplication des assignations ou des observations mensuelles. IC95 percentile sur 20 000 rééchantillonnages par grappe de graine, RNG 0.

## Effets estimés

| Mesure | Assignations évaluables (traitées / différées) | Graines avec deux affectations | Effet et IC95 par graine |
|---|---:|---:|---|
| Profit d'exploitation flotte ligne, mois 1–12 annualisés | 247 / 217 | 20 | 11 328 £/an, IC95 [4 998 ; 18 281] |
| Profit d'exploitation flotte ligne, mois 13–24 annualisés | 156 / 140 | 19 | 15 780 £/an, IC95 [8 055 ; 23 704] |
| Premier étage : avions déclarés ajoutés/assignation | 1117 / 873 | 20 | 0,927 avions/assignation, IC95 [0,908 ; 0,942] |
| Compagnie p50−p0, `profit_year` terminal | 20 paires | 20 | 30 286 £/an, IC95 [-175 120 ; 231 449] |

Valeur compagnie : ratio des moyennes 1,003430 (variation 0,343 % ; garde descriptive de −5 % tenue). L'ITT local porte sur **tous les avions de la ligne** et exclut infrastructure, valeur résiduelle et coût physique des remplacements. Un coefficient de ROI marginal net de l'appareil ne peut en être tiré.

**Attention à la sélection de suivi :** les estimations d'exploitation à 12 et 24 mois portent sur les épisodes observables, et leurs IC95 sont descriptifs de cette sous-population. Ils ne constituent pas une preuve d'ITT causal sur toutes les assignations, car le suivi est largement incomplet. Les assignations sans endpoint n'ont reçu ni zéro fictif ni profit imputé.

## Attrition et couverture préenregistrée

| Horizon, bras | Assignées | Éligibles avant fin de partie | Censurées administrativement | Évaluables | Suivi parmi éligibles | Suivi brut |
|---|---:|---:|---:|---:|---:|---:|
| 12 mois, treatment | 1117 | 999 | 118 | 247 | 24,7% | 22,1% |
| 12 mois, deferred | 873 | 786 | 87 | 217 | 27,6% | 24,9% |
| 24 mois, treatment | 1117 | 908 | 209 | 156 | 17,2% | 14,0% |
| 24 mois, deferred | 873 | 724 | 149 | 140 | 19,3% | 16,0% |

À 12 mois : écart absolu des taux de suivi 2,88 points ; seuil préenregistré non satisfait. Ruptures parmi les épisodes administrativement éligibles : `{"vehicle_sold_or_lost": 178, "interval_days_out_of_range": 1123, "checkpoint_lag_over_14_days": 20}`.
À 24 mois : écart absolu des taux de suivi 2,16 points ; seuil préenregistré non satisfait. Ruptures parmi les épisodes administrativement éligibles : `{"interval_days_out_of_range": 1102, "vehicle_sold_or_lost": 218, "checkpoint_lag_over_14_days": 16}`.

**Détail des durées en échec à 24 mois :** parmi les premiers intervalles invalides des épisodes administrativement éligibles, 955 durent plus de 42 jours et 147 moins de 18 jours (non classés : 0). Les intervalles longs indiquent une cadence effective de relevé trop espacée ; les intervalles courts apparaissent lors du rattrapage. Le seuil de durée est conservé conformément au préenregistrement : aucune requalification a posteriori de ces épisodes.


Par graine, assignations / éligibles / valides (12 et 24 mois) :

| Graine | Bras | Assignées | 12 mois (éligibles / valides) | 24 mois (éligibles / valides) |
|---|---|---:|---:|---:|
| 42 | treatment | 59 | 50 / 20 | 47 / 20 |
| 42 | deferred | 47 | 45 / 19 | 39 / 12 |
| 100 | treatment | 39 | 34 / 10 | 31 / 9 |
| 100 | deferred | 21 | 19 / 6 | 19 / 2 |
| 111 | treatment | 54 | 49 / 6 | 45 / 8 |
| 111 | deferred | 47 | 44 / 9 | 37 / 8 |
| 222 | treatment | 66 | 61 / 12 | 57 / 2 |
| 222 | deferred | 51 | 46 / 20 | 44 / 5 |
| 333 | treatment | 68 | 57 / 13 | 54 / 8 |
| 333 | deferred | 55 | 49 / 20 | 46 / 15 |
| 444 | treatment | 44 | 41 / 4 | 38 / 4 |
| 444 | deferred | 46 | 40 / 11 | 38 / 5 |
| 555 | treatment | 50 | 45 / 22 | 38 / 11 |
| 555 | deferred | 40 | 37 / 11 | 35 / 13 |
| 666 | treatment | 54 | 49 / 13 | 45 / 9 |
| 666 | deferred | 36 | 34 / 13 | 31 / 5 |
| 777 | treatment | 62 | 50 / 7 | 45 / 3 |
| 777 | deferred | 54 | 51 / 5 | 48 / 5 |
| 999 | treatment | 63 | 61 / 15 | 56 / 6 |
| 999 | deferred | 49 | 44 / 8 | 36 / 5 |
| 1024 | treatment | 49 | 47 / 15 | 41 / 8 |
| 1024 | deferred | 35 | 34 / 14 | 32 / 7 |
| 1234 | treatment | 50 | 43 / 8 | 40 / 8 |
| 1234 | deferred | 42 | 36 / 6 | 33 / 10 |
| 1337 | treatment | 61 | 58 / 12 | 48 / 6 |
| 1337 | deferred | 54 | 44 / 9 | 41 / 8 |
| 2026 | treatment | 73 | 61 / 14 | 54 / 1 |
| 2026 | deferred | 49 | 46 / 11 | 42 / 0 |
| 5678 | treatment | 55 | 51 / 19 | 49 / 8 |
| 5678 | deferred | 52 | 45 / 16 | 41 / 8 |
| 123457 | treatment | 48 | 48 / 17 | 41 / 9 |
| 123457 | deferred | 37 | 32 / 8 | 31 / 6 |
| 161803 | treatment | 34 | 33 / 6 | 31 / 11 |
| 161803 | deferred | 23 | 21 / 4 | 18 / 1 |
| 271828 | treatment | 62 | 53 / 13 | 48 / 13 |
| 271828 | deferred | 45 | 41 / 6 | 39 / 10 |
| 314159 | treatment | 57 | 51 / 16 | 47 / 9 |
| 314159 | deferred | 36 | 31 / 13 | 29 / 8 |
| 987653 | treatment | 69 | 57 / 5 | 53 / 3 |
| 987653 | deferred | 54 | 47 / 8 | 45 / 7 |

## Cohortes au moment de l'assignation

| Classe | Cohorte | Affectations (T/D) | ITT 12 mois ; graines avec deux bras | ITT 24 mois ; graines avec deux bras |
|---|---|---:|---|---|
| fleet_class | 1 | 875 / 555 | 14 097 £/an, IC95 [6 553 ; 22 739] ; n=20 | 19 154 £/an, IC95 [12 456 ; 25 016] ; n=19 |
| fleet_class | 2 | 128 / 163 | 53 300 £/an, IC95 [18 190 ; 82 390] ; n=8 | 52 906 £/an, IC95 [7 522 ; 95 581] ; n=7 |
| fleet_class | 3-4 | 114 / 155 | -11 124 £/an, IC95 [-78 598 ; 57 922] ; n=4 | 59 384 £/an, IC95 [7 535 ; 118 681] ; n=3 |
| saturation | saturated | 0 / 1 | indisponible £/an, IC95 indisponible ; n=0 | indisponible £/an, IC95 indisponible ; n=0 |
| saturation | unsaturated | 1117 / 872 | 11 328 £/an, IC95 [4 998 ; 18 281] ; n=20 | 15 780 £/an, IC95 [8 055 ; 23 704] ; n=19 |
| kind | hubhub | 369 / 279 | 12 737 £/an, IC95 [2 998 ; 22 881] ; n=15 | 10 959 £/an, IC95 [-876 ; 20 668] ; n=12 |
| kind | hubsite | 630 / 473 | 13 916 £/an, IC95 [2 161 ; 24 679] ; n=20 | 20 325 £/an, IC95 [8 648 ; 32 109] ; n=17 |
| kind | newpair | 118 / 121 | 29 102 £/an, IC95 [918 ; 55 432] ; n=15 | 14 912 £/an, IC95 [-6 554 ; 38 245] ; n=10 |
| v161_source | model | 79 / 52 | 885 £/an, IC95 [-17 743 ; 21 408] ; n=3 | 385 £/an, IC95 [-17 784 ; 22 981] ; n=2 |
| v161_source | prior | 1038 / 821 | 11 458 £/an, IC95 [4 796 ; 18 672] ; n=20 | 17 575 £/an, IC95 [9 687 ; 26 135] ; n=19 |
| v161_cohort | unknown | 1117 / 873 | 11 328 £/an, IC95 [4 998 ; 18 281] ; n=20 | 15 780 £/an, IC95 [8 055 ; 23 704] ; n=19 |

## Confrontation avec les prévisions V161/C70 (diagnostic)

| Source V161 | Affectations | Médiane de profit prédit par avion (£/an) | Médiane ROI brut de sélection (unités du score) | Relevés 24 mois T/D |
|---|---:|---:|---:|---:|
| model | 131 | 1 787 | 48,00 | 10 / 4 |
| prior | 1859 | 21 562 | 19,00 | 146 / 136 |

Le ROI brut de sélection, le profit annuel prédit V161 et le résultat d'exploitation de toute la ligne ont des périmètres distincts. Ils ne permettent pas de comparer un rendement net marginal mesuré à un coût physique unitaire fiable.

## Intégrité de la récupération des données

Les simulations 40/40 ont produit leurs checkpoints et journaux moteur. Le post-traitement du harnais a ensuite été arrêté par Docker pour dépassement mémoire (OOM, code hôte 247), avant le JSON récapitulatif. La récupération a relu en streaming le JSONL original et les quarante journaux moteur, en réutilisant les fonctions du banc pour les contrôles de santé et la comparaison économique. Aucun moteur ni graine n'a été relancé. Les fichiers de télémétrie bruts sont conservés ; le résumé récupéré omet le volumineux proxy descriptif C66 des gares, qui ne sert pas aux endpoints ITT.

## Décision

L'information ITT à 24 mois ne satisfait pas les seuils préenregistrés : aucune étape 3, politique nouvelle ou porte A/B n'est ouverte.
Aucun défaut d'IA, coefficient V161/C70, score ni priorité n'est modifié.
Les anciennes observations 20×6 restent figées ; toute évolution d'estimand dans cette campagne est documentée au §8.
