# V166 P2/P4 — portefeuille H3 vide et banc Savefork retrouve (14-10-2026)

**Chantier suspendu à la demande utilisateur.** Pour le bilan global de toutes
les expériences et les références des résultats, lire
`docs/p2_p4_bilan_final_et_suspension_20261014.md`. Aucun nouveau banc prévu.

## Provenance et limites d'intervention

Worktree exclusivement cree depuis `7ecbabe8ff4154dfd62184a5d6d1e33db3bbccbf` :
`results/scores_p2_p4_empty_pool_causality_stage_20261014`.
Le script `sweeps/analyze_h3_empty_pool_20261014.py` et cinq tests hote
lisent les campagnes deja figees, sans lancer Docker, ecrire dans les
stages d'origine ou changer un seul octet de l'IA. Verdict **diagnostic_only**.
Sortie figée : `results/h3_empty_pool_fork_lineage_20261014.json`.

## Nouveauté 1 : 14 zero candidats a capital eleve, pas 14 refus d'investissement

Tous les dix vrais logs H3 5x5 ont ete parcourus pour les lignes
`[PORTFOLIO_CACHE] incremental: candidates=N od=M selected=K remaining=R`.
Seuil diagnostique impose par la demande : `N=0`, `K=0`, `R>=100000` GBP.

| Seed | C121 historique avec shadow H3 OFF | H3 credit signe ON |
|---|---:|---:|
|42|2|3|
|100|3|3|
|999|2|2|
|1234|2|2|
|5678|1|14|

Parcours source V166 :

* `ai/OpexAI/task_projects.nut:2021-2057` : mise a jour apres construction ou abandon ;
* `ai/OpexAI/projects_update.nut:95-173` : filtration du vivier, suppression des
  anciennes entrees flotte, abandon, validite, AIR touchant les villes d'un
  chantier ;
* `ai/OpexAI/projects_update.nut:192-213` : lorsque C121_CATALOG_INCREMENTAL
  est actif apres chantier AIR, **defer** la replannification AIR massive ;
* `ai/OpexAI/projects_update.nut:216-290` : mise en commun, filtrage, selection,
  stats et log ; `ai/OpexAI/projects_builders.nut:415-425` :
  `modeCandidates` compte les candidats effectivement MEMORISES dans ce vivier ;
* `ai/OpexAI/scheduler_tasks.nut:255-331` : slices du catalogue AIR et
  republication progressive quand de nouveaux plans sont produits ;
* `ai/OpexAI/projects_selection.nut:1077-1121,1149+` : le capital/floor
  n'agit qu'APRES production de projets.

Sur seed5678 ON, un des 14 evenements arrive au lancement en janvier 1970 ;
les **13 autres** sont entre le **16 fevrier et le 25 decembre 1972**.
Ils sont **tous** precedes, dans les 14 lignes de log, d'un succes physique
`C121_BUILD` ou `[FLEET_PROJECT]`, et **tous** suivis d'un nouveau succes
AIR/flotte en environ **2 a 67 jours** (mediane **24 jours** selon les dates
du dernier message moteur). Il ne s'agit donc pas d'un deadlock perpetuel.
Ces intervalles ne prouvent pas non plus qu'un projet marginal profitable
aurait pu etre construit plus tot.

Le troisieme snapshot incrémental apparie par **rang de log**, non par tick,
est OFF `candidates=47, remaining=39703` le **13 avril 1970**,
contre ON `candidates=36, remaining=86167` le **9 mars 1970**.
**Ces lignes ne sont pas deux decisions au meme instant**. Leur opposition
ne peut dater une premiere divergence causale H3 ; les trajectoires ne sont
deja pas alignees. Les rapports annuels `C121_HUB_SIGNED` ne donnent pas
les ticks de premiere cotation effectivement changee.

## Nouveauté 2 : comparaison a V166 pur

Le temoin `hub_shadow_historical` utilise le comportement C121 historique
V166 en presence de l'instrumentation H3 OFF ; il suffit a etablir que
ce type d'episode n'est pas propre a l'application du credit positif H3.
Il **ne constitue pas** une trace d'un executable V166 pur byte-identique.

Archives physiques V166
`scores_p2_p4_save_baseline_stage_20261013/results/scores_p2_p4_v166_physical_base2x5_r2_20261013.jsonl` :
60 checkpoints pour chacun des deux seeds 161803, 314159 et les deux
compagnies, soit 240 lignes. Les deux chemins de logs moteur V166 references
ne sont pas conserves dans le stage. Ces JSONL mensuels ne stockent ni
`candidateGroups`, ni le compteur de candidats post-filtre, ni les
contre-factuels de construction. **Existence en V166 pur : plausible par le
code, mais non verifiable exactement depuis ces deux archives.**

## Banc long 12:30–12:50 retrouve, ne PAS relancer

Dans `scores_p2_p4_net_revenue_stage_20261014/results/` :
`p2_net_savefork_314159_terminal49m_20261014/replays/aa0/replay.json`,
ecrit sur la machine a **12:46:03**. `engine.log` ecrit a 12:45:37.
Graine 314159. Save initial **1971-01-01** tick **28289**,
OpenTTD en serveur dedie, exactement deux compagnies, `LOAD_RECONCILE`
`saved=5 kept=5 dropped=0`; aucun script_failure, 49 checkpoints,
derniere date **1975-01-01**, terminal observe : OpexAI profit_year
**1 974 739 GBP**, company_value **5 543 810 GBP**, cash **961 669 GBP**,
107 vehicules (93 AIR, 11 RAIL, 3 ROAD), 69 gares.

Le `fork.json` PREVOIT `aa0,aa1,variant`, mais seul `aa0` est present.
`paired_comparison_possible=false`. Le manifeste declare aussi
`MONTHLY_CHECKPOINT_NOT_C77_TICK` et `frozen_source_matches.reference.exact=false`
(17 fichiers OpexAI ne correspondent pas au code historique fige). Ce long
replay est **valide comme continuation descriptive d'un bras**, mais **n'est
ni une A/A, ni une A/B, ni une preuve d'un effet H2, ni une raison de
relancer un long replay d'une variante H2 deja rejetee en 5x5**.

## Porte de decision

Aucune des 14 lignes `candidates=0` ne contient une alternative identifiee
ayant *a la fois* score net meilleur, admissibilite, financement au meme
tick, preflight vrai, constructeur abouti et profit marginal de reseau.
Le jeu de donnees ne porte pas ces variables : le programme ne fabrique
pas une politique `refresh_on_empty`, `disable_filter` ou un seuil cash.
Les interventions H1 (0 defers), H2 (5x5 final -16.9k/an) et H3
(5x5 -109.4k/an) restent non qualifiees. La conclusion est celle
d'un **cycle borne avec blocage de preuve causale**, non de l'optimalite
economique universelle d'OpexAI.

Un candidat comportemental nouveau exige un worldstate V166 avant la
decision, alternatives completes et A/A a horloge/VM compatible ; tester
un seul filtre et verifier immediatement `head->challenger->construction`
avec preuve physique, puis `profit_year` global a cinq ans. Sans ces donnees,
un autre 40x5 ou ajustement de coefficient recyclerait du bruit.
