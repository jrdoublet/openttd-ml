# OpexAI P2/P4 — bilan expérimental final et mise en pause

**Date : 14 octobre 2026. Statut : CHANTIER SUSPENDU à la demande de l'utilisateur.**

Ce document centralise les résultats importants des essais économiques V166,
les contrôles causaux et les pistes testées ou non qualifiables. Il **n'annonce
ni amélioration adoptée, ni preuve d'optimalité générale**. La décision de
suspension remplace toute intention précédente de poursuivre les expériences.
**Ne pas relancer de campagne, d'audit, de sonde ou de variante dans ce cycle.**

## 1. Reproductibilité, intégrité et état au gel

- Base V166 immuable : `7ecbabe8ff4154dfd62184a5d6d1e33db3bbccbf`.
- Checkout principal : `b56d190bab9f9483c533b296ac9a3e29bc0beb56`, **sale avant
  cette recherche et préservé**. Master, origin, P1/V165, C121/R2/V161,
  financement, branches et worktrees antérieurs non modifiés pour cette clôture.
- Tous les prototypes sont des **worktrees détachés**, sans commit, merge,
  reset, push ou adoption. Les réglages expérimentaux restent OFF dans
  `easy`, `medium`, `hard` et `custom`. Les résultats ignorés par Git sous
  `results/` font partie des preuves à conserver, même non suivies par Git.
- Image des campagnes réalisées : `openttd-lab:latest`, SHA256
  `f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659` ;
  OpenTTD 15.3, OpenGFX 7.1, openttdlab 0.0.75. Une campagne Docker à la fois,
  jusqu'à 10 CPU et 10 workers. **Aucun banc nouveau pour cette documentation.**
- Synthèse indépendante H1/H2/H3 :
  `results/scores_p2_p4_causal_closure_stage_20261014/` avec
  `sweeps/qualify_p2_p4_evidence_20261014.py`, son test 4/4 PASS,
  `results/p2_p4_causal_closure_20261014.json` et
  `docs/p2_p4_causal_closure_and_open_mechanisms_20261014.md`.
- Dernière autopsie lecture seule :
  `results/scores_p2_p4_empty_pool_causality_stage_20261014/`,
  `sweeps/analyze_h3_empty_pool_20261014.py`, 5/5 tests hôte PASS,
  `results/h3_empty_pool_fork_lineage_20261014.json` et
  `docs/p2_p4_empty_pool_and_recovered_fork_20261014.md`.

**Convention** : tous les écarts financiers ci-dessous sont `variante − témoin`
sur le **`profit_year` terminal à cinq ans**, en livres par an, sauf indication
contraire. Les IC95 portent sur la moyenne appariée selon le protocole
indiqué. Un IC recouvrant zéro n'autorise pas à annoncer un gain robuste.
Les résultats « diagnostic_only » et différences sans intervention ne sont
**pas** des effets causaux.

## 2. Trois nouveaux prototypes P2/P4 : code, moteur, verdicts

| Hypothèse et worktree | Validation moteur / exposition | Δ profit_year ; IC95 bootstrap | Valeur et verdict |
|---|---|---|---|
| **H1**, différer une dépense de flotte AIR devant une nouvelle AIR plus rentable/ROI à tier égal ; `scores_p2_p4_fleet_opportunity_stage_20261014` | Smoke 2×3, puis **3×5** (6/6 parties), 4+52 tests hôte ; **0** marque `P2_FLEET_AIR_DEFER` sur les trois variantes | **+49 418,3** ; **[−72 204 ; +124 295]** ; 2V/1D | Valeur +0,3275 % apparente ; **aucune intervention effective**, aucun gain attribuable, stop |
| **H2**, apprendre `k_revenue` et maintenir séparés les coûts prédits de la nouvelle AIR ; `scores_p2_p4_net_revenue_stage_20261014` | Smoke 2×3, précontrôle A/A 2×2 identique hors timestamps, finale **5×5** (10/10), 69 tests hôte | **−16 912,6** ; **[−94 875 ; +63 108,6]** ; 2V/3D | Valeur +1,3819 %, seed999 opcodes adverses divergents avant facteur non neutre ; **non qualifié** |
| **H3**, tenir compte du gain externe positif des hubs AIR dans C121 sans supprimer les pertes de cannibalisation ; `scores_p2_p4_signed_hub_stage_20261014` | Smoke 2×3 négatif, **5×5** (10/10), 56 tests hôte ; **9 475 cotations positives / 18 148 évaluations** témoin | **−109 432,8** ; **[−405 956 ; +177 481,4]** ; 3V/2D | Valeur −4,0901 % ; fortes pertes sur graines 1234/5678 ; **non qualifié** |

Les prototypes H1/H2/H3 n'introduisent **aucun nouveau coefficient C70/P2/P4**
et n'ont **jamais été promus**. Aucun n'a satisfait la porte 40×5.

**H1** — flag `p2_fleet_air_displacement=0` par défaut, code principalement
`ai/OpexAI/task_projects.nut`, SHA bundle
`a01921034d6aacadee242cc131a3bc3894617ec67ac831fec0d50644168aef5e`.
Les deltas par graine 42/100/999 sont +96 164, −72 204 et +124 295.
La condition stricte n'a été exécutée dans **aucune** réalisation : il
serait invalide de présenter la moyenne positive comme une amélioration.
Sources : `docs/p2_p4_fleet_air_displacement_20261014.md` et
`results/p2_p4_fleet_displace_exposure3x5_20261014.json` dans ce stage.

**H2** — flags `p2_air_net_revenue=0`, `p2_air_revenue_shadow=0`, modifications
isolées dans `projects_models.nut`, `task_report.nut`, `persist.nut` et réglages.
Évolution des portes : brut 5×5 +86 069 £/an **non causal propre** (opcodes
asymétriques), symétrique 5×5 +61 503 £/an encore non paritaire, puis final
parity5×5 **−16 913 £/an** avec bundle
`aa11fd16691fd3b05ed1d1c89f87f562b9a631abc6f8a2e8fabc63d4eb275d86`.
Deltas finals (42/100/999/1234/5678) : −136 613, −60 743, +81 621,
−70 203, +101 375. Le precheck seeds42/100 a 4 850/3 362 lignes de logs
strictement égales OFF/ON après retrait de l'horodatage, **pas** un certificat
de parité universelle. Voir `docs/p2_p4_net_revenue_experiment_20261014.md`
et `results/p2_p4_net_revenue_parity5x5_20261014.json`.

**H3** — flags `c121_hub_signed_externality=0`, `c121_hub_signed_shadow=0`,
correction double chemin dans `air_economics_c121.nut`, bundle
`de9a48fbb1255cc930dac545cb64914f88a69f31b73b5237240415cc617e9ca5`.
Deltas finals (42/100/999/1234/5678) : +138 224, +98 613, +256 173,
**−563 915**, **−476 259**. Les 9 475 mesures positives sont des **cotations
de projets**, pas 9 475 constructions ni des profits réellement perçus.
Source : `docs/p2_p4_signed_hub_externality_20261014.md` et
`results/p2_p4_signed_hub_dev5x5_20261014.json`.

## 3. Autopsies terminales : mécanismes observés, causalité non acquise

Sur H3, la graine 1234 passe de 61 à 55 constructions AIR, 45 à 35
renforcements de flotte, 105 à 84 avions et 42 à 37 aéroports. Sur 5678,
62 à 61 constructions AIR, 66 à 46 renforts, 126 à 106 avions et 16 à
8 trains ; seulement 10 projets en 1973 contre 48. Pourtant, sur cette
dernière graine, la variante détient **plus** de cash fin 1973
(3,303 M£ contre 1,924 M£) et fin 1974 (4,561 M£ contre 3,711 M£).
Le mauvais résultat H3 n'est donc pas un simple manque de trésorerie ;
les changements d'ordonnancement, de vivier et de réseau demeurent des
causes possibles **non identifiées au même état**. Runways saturées :
`runway_scale<1` sur seulement **4/278** constructions témoins et **6/286**
variantes. **Aucun** `[FLEET_PROJECT] replaced>0` dans dix journaux.

Le signal `PORTFOLIO_CACHE incremental candidates=0 selected=0 remaining>=100000`
apparaît sur les cinq graines du H3, avec comptes témoin/variant :

| Graine | Témoin H3 shadow | H3 signé |
|---|---:|---:|
| 42 | 2 | 3 |
| 100 | 3 | 3 |
| 999 | 2 | 2 |
| 1234 | 2 | 2 |
| 5678 | **1** | **14** |

Sur **5678**, 13 des 14 épisodes variants ont lieu du 16 février au
25 décembre **1972**, après un succès AIR ou fleet récent ; chacun est suivi
d'un autre succès physique sous **2 à 67 jours**, médiane **24 jours**.
Ce n'est **pas** un deadlock. La troisième ligne de cache appariée *par
rang*, déjà différente en mars/avril 1970, n'est **pas** une comparaison
same-tick ; aucune alternative simultanément constructible et meilleure
n'a été isolée. Le compteur `candidates` compte le vivier **post-filtre**
(`projects_update.nut:95–173,192–290`), non toutes les routes possibles.
L'AIR est régénéré par catalogue incrémental différé et ses publications
partielles (`scheduler_tasks.nut:255–331`). Les relevés mensuels V166 pur
sur **deux graines × 60 mois** ne gardent pas les logs moteur et ne permettent
pas de calculer la fréquence exacte de ces épisodes en V166 pur.

Autopsie séparée des dépenses et de la constructibilité dans V166 :
95 services AIR, 18 RAIL, 5 ROAD sur le témoin physique à deux graines,
avec 50 hausses de flotte AIR et **3 RAIL hors portefeuille** ; les mouvements
de cash correspondants sont des **différences mensuelles composites**, pas
les factures marginales des trains. Plusieurs échecs constructeur et A*
existent, mais la boucle essaie déjà des alternatives après des vetos.
Le panel C77 instrumenté a **103** épisodes par répétition A/A sur seed314159,
**75 dispatch**, **57 constructeurs** et **44 constructions** ; les traces
ne contiennent pas le profit du projet non construit. Le vivier vide, un
devis théorique ou un `LINE_REVENUE` YTD ne suffisent pas à qualifier une
nouvelle politique économique.

Sources :
`scores_p2_p4_causal_closure_stage_20261014/docs/p2_p4_causal_closure_and_open_mechanisms_20261014.md`,
`scores_p2_p4_empty_pool_causality_stage_20261014/docs/p2_p4_empty_pool_and_recovered_fork_20261014.md`,
`scores_p2_p4_integrated_probe_stage_20261013/docs/scores_p2_p4_experimental_verdict_20261013.md`.

## 4. C77, P3/P4 antérieurs et autres portes économiques déjà closes

| Variante/porte antérieure | Banc | Δ profit_year à 5 ans et verdict |
|---|---|---|
| **C77** RAIL→RAIL de même tier, rang 2 | **5×5**, 3/5 substitutions construites | **−4 229,4 £/an**, 2V/2D/1E, IC95 **[−131 479 ; +123 020]**, valeur −2,04 %, rejet |
| P3 score | **40×5** | **−58 916 £/an**, rejet |
| P4 stable-cohort | **40×5** | **−43 730 £/an**, rejet |
| P4 vehicle-year | deux **5×5** (clean/matched) | **+19 040 / −19 231 £/an**, non qualifié |
| P4 fresh_equal | **5×5** | **−24 050 £/an**, non qualifié |
| P4 partial | **5×5** | **+476 £/an**, non qualifié |
| P4 garde uplift AIR | dev **5×5** puis holdout **40×5** | **+68 192** puis **−52 352 £/an** ; IC95 holdout **[−96 110 ; −15 267]**, rejet indépendant |
| P4 crash-only | deux lots totalisant **5×5** | **−5 292 £/an**, 1V/4D ; exposé mais non gagnant |
| Quote capital / devis physiques `capital_quote_learning` | porte **40×3** | **−106 788 £/an**, IC95 négatif, rejet |
| AIR site quote et marge 15 % | **40×3** | **−92 700 £/an**, non gagnant |
| AIR reselect efficiency | **5×6** | environ **−94 800 £/an**, rejet |

La politique C77 avait deux forks de sauvegarde à +181 618/+173 456 £/an
qui ajoutaient une **compagnie fantôme** (`-vnull`) : **diagnostic seulement**.
Une validation C77 en serveur dédié sans compagnie fantôme a montré A/A
4/4 et une alternative RAIL physiquement construite (+4 véhicules,
+3 gares, coût cash 81 247 £), **sans preuve de gain terminal à cinq ans**.
Dans le 5×5 C77, seed5678 **ne force aucun remplacement** (`head_mismatch`)
mais affiche pourtant −135 264 £/an entre bras : divergence AAA antérieure,
non attribuable à C77. Voir
`results/scores_c77_rank2_policy_stage_20261014/docs/c77_rank2_policy_experiment_20261014.md`.

Autres familles vérifiées/rejetées ou non reproductibles : P2 froid LOSO
(3 flips admissibles sur 202 décisions, **0 construction alternative**),
P4 stable vs survivants/partiels, réglages C80/V105 flotte, capital V104,
réserves V165, correctifs rail-origin/A*/sites, réemploi AIR, Save/Load
80 lignes et autres bancs antérieurs explicitement clos. **Ne pas relancer**
ces essais sans nouvelle demande après la suspension.

Les métriques de `LINE_REVENUE` de 1974 reflètent généralement l'année
1973 ; 132/140 lignes comparables ont un profit différent malgré OD,
jour de construction et compte de véhicules égaux au rapport. Ce n'est
ni l'identité du réseau au tick ni le rendement marginal d'une ligne.
Les sondes OFF/ON elles-mêmes peuvent changer la trajectoire : sur deux
graines, −108 623 £/an apparent entre mondes sondés/non sondés, alors que
les 60/60 checkpoints du A/A avec sondes identiques sur une graine
étaient égaux. **Une différence sans intervention ou avant intervention
est un risque de comparabilité, pas un bénéfice causal.**

## 5. Banc long retrouvé le 14 octobre entre 12 h 30 et 12 h 50

Chemin exact :
`results/scores_p2_p4_net_revenue_stage_20261014/results/p2_net_savefork_314159_terminal49m_20261014/`.

Seul le bras **`replays/aa0`** a achevé un replay depuis checkpoint
mensuel **1971-01-01**, seed314159, tick initial 28289 : `engine.log` daté
12:45:37, `replay.json` daté **12:46:03** CET, 49 checkpoints jusqu'au
**1975-01-01**. Serveur dédié, deux compagnies (OpexAI et AAAHogEx),
`LOAD_RECONCILE saved=5 kept=5 dropped=0`, aucune erreur de script et
terminal OpexAI : **profit_year 1 974 739 £/an**,
**company_value 5 543 810 £**, **cash 961 669 £**, **107 véhicules**
(93 AIR, 11 RAIL, 3 ROAD), 69 stations.

**Important :** `fork.json` prévoit **`aa0`, `aa1`, `variant`**, mais seul
`aa0` est effectivement présent/terminé. Le manifeste indique
`MONTHLY_CHECKPOINT_NOT_C77_TICK`, `frozen_source_matches.reference.exact=false`
et 17 divergences de fichiers vis-à-vis de la source gelée. Ce banc est
une **continuation descriptive terminée d'un seul bras**, **pas** un A/A,
pas un A/B, pas une preuve de gain H2 et pas un ordre de compléter les
deux branches manquantes. Il est conservé intégralement.

## 6. Conclusion, travaux mis en pause, conditions éventuelles de reprise

**Verdict factuel :** aucune des politiques P2/P4 récentes n'a montré un
gain robuste et reproductible de `profit_year` terminal à cinq ans avec
IC95 entièrement positif et effet physique réellement attribuable.
H1 n'a pas été exercée ; H2 et H3 ont été négatives en moyenne et dispersées ;
C77 et les principaux prédécesseurs ont été rejetés ou non qualifiés.

**Épuisement borné :** les hypothèses alors économiquement justifiées et
testables avec les archives et leurs filtres existants ont été examinées.
La question générale de la rentabilité marginale du réseau, des hubs et
des alternatives non construites **reste ouverte en théorie**, sans
contre-factuel same-tick, décision alternative physiquement réussie et
profit net global attribuable. Cette incertitude n'est **pas** la preuve
qu'OpexAI ne peut plus être amélioré.

**Décision utilisateur : ARRÊT DU TRAVAIL SUR CE SUJET POUR L'INSTANT.**
Aucune tâche en arrière-plan, aucun nouveau banc, aucune modification de
comportement, aucun cherry-pick/commit/merge/reset/push, aucune adoption des
flags prototypes. Les sources, JSON/JSONL, logs et saves dans tous les
worktrees restent en place afin de pouvoir retrouver les conclusions sans
recommencer les audits. Toute reprise nécessitera une **nouvelle demande**.
