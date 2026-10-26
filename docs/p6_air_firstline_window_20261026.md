# P6 — fenêtre du premier catalogue AIR (pré-enregistrement)

État : **porte A terminée `fail_primary` ; P6 OFF, porte B non lancée**. Base d'étude : `master` à partir de
`8a7cded9` (26/10/2026). Le commit et l'empreinte du bundle exécuté seront
reportés sur chaque campagne avant son lancement. Aucun défaut n'est adopté.

## Intervention isolée

- Réglage `p6_air_firstline_window`, témoin `0` et candidat `1`, **défaut 0**
  dans les quatre difficultés. Même code, mêmes autres réglages de `master`.
- Agir seulement au premier chantier AIR, après publication partielle du
  catalogue C78/C121 ; utiliser les projets déjà calculés, réellement valides
  et finançables. Réserver une courte fenêtre bornée de publication du scan
  déjà engagé, puis relancer la sélection normale. Aucun scan géométrique
  supplémentaire ni modification de la frontière des paires.
- Critères d'exposition : première ligne potentiellement différée, durée et
  opcodes consommés avant l'exécution, nouvelles publications, meilleur projet
  retenu, construction effective. Signaler aussi les cas sans fenêtre utile.
  L'exposition instrumentée reste **descriptive** ; le banc économique retire
  le journal de décisions.

## Séquence figée avant le premier moteur

1. Tests ciblés sur option OFF, sélection ON, bornage de l'attente, cas
   non-finançable, et reprise Save/Load court et complet ; suite Python complète,
   puis `git diff --check`.
2. Smoke **1 graine × 1 an**, graine `42`, deux duels appariés, carte `256²`,
   année initiale `1970`, mêmes réglages hors P6, santé et absence d'erreur Squirrel.
3. Exposition mécaniste d'au moins **5 graines prédéfinies** :
   `42 100 7 999 2026`, sans choix après lecture des résultats ; mesurer
   effectivement les fenêtres, constructions et coût par graine. Le journal
   éventuel est identique dans les bras et absent de la porte économique.
4. Porte **A 40 graines canoniques × 5 ans**, multimodale, `1970–1974`,
   `gain_short`, une répétition, 80 parties, `profit_year` Opex candidat moins
   Opex témoin à l'année terminale. Conditions **conjointes** : delta moyen
   ≥ `4 %` du profit moyen témoin, Wilcoxon exact bilatéral `p < 0,05`,
   borne basse de l'IC95 bootstrap de la moyenne `> 0` (20 000 tirages,
   graine bootstrap `0`), ratio des moyennes de valeur de compagnie `≥ 0,95`
   et parties saines. Horizon déclaré **5 ans avant lancement** ; ne pas
   sélectionner a posteriori un horizon ou un sous-groupe plus favorable.
5. **Uniquement si A passe** : porte **B 20 graines canoniques × 10 ans**,
   multimodale, `1970–1979`, `non_erosion`, une répétition, 40 parties ;
   borne haute de l'IC95 bootstrap ≥ 0, garde de valeur 5 %, santé complète.
   B ne prouve pas à elle seule un gain de long terme.

Le lanceur hôte est `sweeps/run_c66_reference.py` ; un seul conteneur Docker
à la fois, sur le PC `desktop-linux`, `--cpus 10 --memory 8g` et jusqu'à
`--max-workers 10` (9 si une autre charge est active). Préciser explicitement
`--required-seeds 40 --required-years 5 --years 5` sous `gain_short`.
Les noms de campagnes seront uniques, la publication et le verdict ajoutés
ici après vérification des archives complètes. Un échec de porte laisse le
réglage OFF et arrête la séquence P6.

## Objectif externe

Se rapprocher de **75 % des profits d'AAAHogEx à dix ans** (ratio des profits
moyens ou médiane des ratios de parties appariées, valeurs toutes rapportées
séparément). Ce ratio est descriptif ; le critère primaire des portes reste
le delta de `profit_year` d'OpexAI entre ON et OFF.

## Résultats mesurés et clôture — 26/10/2026

**Code et provenance figés :** `98c8568daa20c8c98d73dfde567d9a11c1bdfd51`
(`git dirty=0`) ; bundle
`094e7d1545ea2ec92bc7fd14aef8631975ddbeb32e3df8ef15f410101ea43c17` ;
image `openttd-lab:latest` SHA256
`f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
Les deux bras comparent le même code, `p6_air_firstline_window=0` vs `1`,
sur une carte 256² à partir de 1970. Aucun défaut modifié.

- **Tests/smoke :** 2 863 tests Python réussis (5 ignorés, 2 échecs attendus),
  `git diff --check` conforme. Smoke 1×1 sur graine 42 terminé/sain ;
  `results/p6_win_smoke_42x1_20261026.json`. Le premier départ AIR
  2→30 a été décalé d'un jour mais la paire reste identique.
- **Exposition 5 graines × 3 ans** (diagnostic uniquement) :
  `results/p6_win_expo_5x3_20261026.json`, 5/5 paires saines.
  Fenêtre ouverte sur **3/5 graines** : 42 (18 ticks, 95 941 opcodes de scan,
  1 publication supplémentaire), 100 (17, 97 715, 1) et 7 (21, 131 443, 2).
  Aucune fenêtre sur 999/2026 ; **5/5 premières paires construites identiques**
  ON/OFF malgré un jour de décalage sur les trois expositions. Δ `profit_year`
  diagnostique à trois ans **+59 580,6 £/an**, 4V/1D, p=0,3125,
  IC95 [−30 751 ; +132 236,8] £/an, non qualifiant.
- **Save/Load réel court et complet** avec `p6_air_firstline_window=1` :
  `results/p6_win_saveload_{short,full}_42_20261026.json` ; deux séquences
  d'une année puis rechargement du 01/07/1970 et poursuite d'une année.
  `LOAD_RECONCILE` observé, 13 sauvegardes produites à chaque phase,
  aucun marqueur d'erreur script. Le harnais de rechargement crée une compagnie
  fantôme connue : ces runs valident la reprise, pas un delta économique.

**Porte A : `p6_win_porteA_40x5_20261026`**, manifeste SHA256
`b310ae630d75da1468f7f78f6909b29bc664e2e754b9167ee394b9fcdcdefb17`,
40 graines canoniques, 1970–1974, 80 parties, 10 workers, un Docker,
`probes=2` symétrique, pas de `DECISION_LOG`. Archives
`results/p6_win_porteA_40x5_20261026.{json,jsonl,manifest.json}` et répertoire
`_engine`. Contrôles du rapport : `comparison_complete=true`,
`adoption_sample_complete=true`, `metric_coverage_complete=true`, 40/40
paires, aucun `failed_runs` ni erreur Squirrel, code retour 0.

| Critère A (`profit_year` terminal ON−OFF) | Observation | Exigence |
|---|---:|---:|
| Delta moyen | **−2 164,275 £/an** | ≥ +114 684,704 £/an (4 % du témoin) |
| Delta médian, V/D/E | +2 724,5 £/an ; 20/19/1 | descriptif |
| Wilcoxon exact bilatéral | **p=0,928548** | p<0,05 |
| IC95 bootstrap, 20 000 tirages, graine 0 | **[−100 482,125 ; +96 235,05] £/an** | borne basse >0 |
| Ratio des moyennes de valeur de compagnie | **0,997016** (−0,2984 %) | ≥0,95 : passe |

**Verdict `fail_primary`**, faute de gain positif au seuil, de significativité
et de borne basse IC positive ; seule la garde de valeur passe. Les cinq
premiers marchés AIR restent inchangés dans l'exposition et l'attente consomme
des ticks : constats descriptifs, sans interprétation causale générale.
**P6 reste à défaut `0` ; aucune porte B 20×10 P6 et aucune adoption.**
Poursuivre P3 `air_fleet_yield_rightsize` selon la file approuvée.
