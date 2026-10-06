# Phase 0 et TrainLineAI — synthèse de l'ancien README

**Archive condensée le 30 septembre 2026, pas copie intégrale ni guide courant.**
[Index](../README.md) · [Archives](README.md) · [Méthode détaillée](../methode.md)

Les campagnes ci-dessous précèdent le seuil de preuve du 9 septembre : elles
expliquent la méthode et ses ruptures, **pas la performance actuelle d'OpexAI**.
Les commandes, checklists « à faire » et vieux prérequis ont été retirés du README
actif ; leur reprise exige une tâche explicite. Aucun ancien résultat n'est recalculé.

## Périmètre initial et ruptures

- Cible initiale : prédire le profit d'une ligne à partir de ses caractéristiques,
  avec modèle hurdle (constructibilité puis profit conditionnel).
- Runtime initial OpenTTD **13.4**, OpenGFX 7.1, Python 3.12, OpenTTDLab 0.0.75 ;
  ce choix historique ne remplace pas la cible courante **15.3 / API 15**.
- Calibration trAIns 2.1, BaNaNaS `54524149`, MD5
  `c4c069dc797674e545411b59867ad0c2` ; pas l'adversaire OpexAI courant.
- Passage 1950→1970 et densité modifiée : catalogue et rangs moteurs différents,
  donc campagnes non mélangeables. Électrique observé dès 1967, INTERNATIONAL en
  1990, monorail en 2000 (`results/catalogue_churn_1950_2000.json`).
- Paramètres initiaux : inflation désactivée, croissance urbaine 2, carte 256²,
  départ 1970, `number_towns=3` (densité, pas trois villes), industrie 4.

## Calibration et métriques

VPS, batch fixe 24 graines × 10 ans : 1/2/3/4 workers donnent respectivement
884,1/448,2/306,2/319,6 s, soit 36,8/18,7/12,8/13,3 s par partie.
Trois workers optimaux **sur ce banc ancien**, pas débit garanti d'OpexAI.
La première mesure « N parties pour N workers » ne mesurait pas le vrai scaling.
Source : `results/phase0_vps.json`, `sweeps/phase0_timing.py`.

`money` seul est trompeur : 289 299 £ avec 300 000 £ de prêt donne −10 701 £ nets.
Le graphique utilise `old_economy.company_value` ; la cible de modélisation reste
le profit. Déduplication par date réelle, jamais longueur d'`old_economy` plafonnée.
Graphiques conservés dans `docs/phase0_company_value_vs_date.html` et CSV associé ;
ancien graphique `phase0_money_vs_date.html` conservé comme témoin.

## ParameterisedAI et TrainLineAI

ParameterisedAI (`74662403e0764329112dc78e5b279d7f1b5fd510`) :
`maximum_buses=1/8`, graine 42 × 2 ans, trajectoires différentes dès avril 1950 ;
argent final 83 911 / 69 076. Cela vérifiait la transmission des réglages, pas une
politique optimale (`results/phase0_parameterised_ai_check.json`).

TrainLineAI construit une ligne isolée et signale statut, coût et coût véhicules
par panneaux `TRLN|` (limite 31 caractères). Schéma dans `src/trainlineai_schema.py` :
rangs villes, moteur, nombre de trains/wagons, `line_index`. Le prêt maximal initial
neutralisait le financement pour étudier la constructibilité. Détails complets,
pièges de portée et chronologie dans [methode.md](../methode.md).

Défauts successifs diagnostiqués : quai trop court ; dépôt mal raccordé ; coût
pollué par les sondages du pathfinder ; chargement nul puis navigation bloquée.
`OF_FULL_LOAD_ANY` corrigeait le chargement, pas à lui seul la navigation.
Le récit initial « navigation encore bloquée » ne constitue pas une tâche OpexAI.
La campagne 12 tentatives/6 ans comptait six constructions et six échecs
(quatre pathfinding, deux gares), aucune tentative pendante.

Le profit ligne utilisait les véhicules de tête (`profit_last_year`), puis
amortissement séparé véhicules (`max_age`) et infrastructure (30 ans, hypothèse).
L'agrégat compagnie ne remplace pas cette mesure ; `GetBankBalance` avant/après
est pollué par les intérêts. Sources : `results/phase2_profit_ligne.json`,
`results/phase2_trainline_run.json` et [schéma de données](../phase2_hurdle_dataset.md).

## Concurrence et timing

Même ligne avec 1/5/15 compagnies : profit −154 257/−278 673/−690 833 £.
Après villes disjointes : −247 186 £ à une compagnie, −49 298 £ à quinze.
La comparaison avant/après à N=1 restait elle-même inexpliquée : ne pas qualifier
un gain causal avec cette seule table. Le mécanisme limite aussi les lignes possibles.

Le décalage de construction changeait le profit d'environ un million malgré
les mêmes caractéristiques. Augmenter les villes n'éliminait pas ce bruit.
Barrière au tick absolu 11 000 après preflight (maximum observé 9 916 ticks),
plus `stagger_slot × 6000` en multi-compagnies : sept délais donnent une amplitude
nulle sur les trois lignes testées. C'est une **rupture de campagne**, pas une
insensibilité générale de la simulation au timing. Panneaux `M` respecté / `O` dépassé.

`results/phase2_baseline_v3.json` : 100 lignes isolées, 75 construites normalisées,
25 échecs (19 PATHLIM, 6 TRKFAIL), aucun dépassement de barrière. Taux par buckets
0–24/25–49/50–74/75–120 : 88/88/68/56 %. Construction « en pause » impossible,
la pause suspend aussi l'IA : [diagnostic](../pause_feasibility_findings.md).

## Anciennes suites, non actives

Checklist Phase 0, navigation TrainLineAI, sharding portable et Netdata ne sont
pas un second backlog. Netdata et confondant matériel/date avaient été explicitement
sortis du périmètre. Les modèles et jeux de données sont documentés dans
[Phase 3 ML](../phase3_ml.md) ; leur présence ne prouve pas leur adoption dans OpexAI.
Pour tout nouveau lancement, utiliser les consignes et harnais courants.