# Mesure légère AIR / sélection — lot 1, 1er octobre 2026

> **Suite intégrée le 01/10 :** raccord des trois chemins de sélection, smokes,
> deux répétitions 5×6 et Save/Load exécutés. Le filtre de perturbation passe,
> sans neutralité prouvée. Voir le [bilan central](three_lots_integration_20261001.md).
> Le rapport ci-dessous conserve l'état de livraison initial, avant intégration.

## Décision et périmètre

**Dispositif livré, non validé en moteur.** Seul réglage supplémentaire retenu :
`catalog_cost_probe=1`. Ni `decision_log`, ni `probe_portfolio`, ni `probe_events`,
ni profil rail ne sont nécessaires. La variante n'est pas encore attestée légère
en pratique : c'est précisément l'objet du futur contrôle de perturbation.

Les 63,74 % AIR et 15,77 % sélection de
[l'intégration r2](parallel_integration_20261001.md) décrivent les cinq bilans
du **profil large**, pas le défaut. La baisse économique de ce profil ne chiffre
pas le coût direct des sondes. Le [lecteur de latence](parallel_latency_audit.md)
avait aussi établi que `AIR_PLAN_PERF.days` est un quotient de ticks.

Écritures de ce lot uniquement :

- `ai/OpexAI/air_planning.nut` : marques aux frontières des phases ;
- `sweeps/diag_air_selection_light.py` : lecteur hors ligne et `--plan` ;
- `sweeps/test_air_selection_light.py` : fixtures et contrats source ;
- cette fiche ; `results/air_selection_light/` : preuves locales.

**C115 conservé ; cadence OFF ; C84/C85/C121/C122 non réactivés.** Aucun calcul
économique supplémentaire, sondage physique, tri, filtre, seuil ou changement
d'ordre métier. Aucun fichier de sélection, harnais, réglage, dépendance, suivi
ou journal commun édité. Aucun lancement de partie/conteneur, installation,
commit, push ni nettoyage. Les appels de mesure et branches ajoutés consomment
néanmoins des opcodes, y compris quelques gardes au défaut : pas d'identité
bit-à-bit revendiquée avec l'ancien arbre.

## 1. Inventaire statique avant choix

Les symboles sont plus stables que les numéros de ligne pendant les éditions
parallèles. Sources : `air_planning.nut`, `probes.nut`, `budget.nut`,
`catalog.nut`, `projects.nut`, `projects_update.nut`, `projects_selection.nut`,
`projects_generation.nut`, `scheduler_tasks.nut`, `settings.nut`, `info.nut`.

| Mesure / site | Gate, fréquence, émission | Coût et limite |
|---|---|---|
| `OpexAirCalcDeltaOps`, `perfOpsSites`, `perfOpsEval` | Calculs déjà présents même sans sonde ; marques de scan de sites, de paires, hubs, reprises ; agrégation par scan | Lectures tick/restes et compteurs. Sites et évaluation inclus dans le total, pas à ajouter à celui-ci. Pas de ventilation nouveaux couples / hubs. |
| `OpexAirPlansFinalize`, `AIR_PLAN_PERF:` | `AILog.Info` **sans gate**, une ligne par finalisation réelle ; `script=4` pour récupérer les Info. Panneau `AP|` sous `DEBUG_SIGNS` | Concaténation existante, panneau tronqué à 31 caractères ; pas d'identité dans la ligne non OPEX. Aucun calendrier réel. Retour anticipé sans moteur et résultat déjà prêt non finalisés. |
| `AIR_PLAN_PERF` structuré / `AIR_PLAN_INPUT` | `DECISION_LOG`, `scan=AIR_PLAN_DIAG_SEQ` ; résumé par scan | Active aussi les diagnostics de villes desservies, vivier/B6 et nombreux logs hors AIR. `days=ticks/74` ; en découpé, ticks = vie du scan, opcodes = tranches cumulées. Ne pas activer pour acquérir seulement un identifiant. |
| `C56_TASK STAGE_*` | `C56_TASK_TRACE`, chargé par **`probe_events`** ; ENTER/EXIT de chaque phase et combo | Beaucoup de lignes, autres sondes d'événements/fleet/catchment concomitantes. `cycle=-` n'identifie pas la génération AIR ; sorties précoces hubs pas toutes closes. Écart `opsclk` englobant ≠ coût CPU. |
| `CATALOG_COST` | `CATALOG_COST_PROBE` ; record créé dans le scheduler puis une émission à la fin de la passe catalogue | Marques de grandes phases, compteurs AIR aux paires, sans second modèle économique. Hors scheduler, `CATALOG_COST_ACTIVE` peut être nul : pas de couverture de tous les rebuilds/régénérations. Aucun identifiant unique publié. |
| `PROJECTS_COST` | Même `catalog_cost_probe` ; ligne de fin de passe `projects` quand cette fin est atteinte | Coûts construction/flotte/régénération existants, hors objectif mais indissociables de ce gate. Certains retours anticipés ne publient pas. Ce gate n'est donc pas un flag AIR pur. |
| `CATALOG_COST_SLICE` | `catalog_cost_probe` **et** C121 incrémental | Non disponible au protocole retenu ; ne pas réactiver C121 pour obtenir une mesure de tranche. |
| `C121_AIR_PLAN_PERF` | `C121_AIR_ECONOMICS` ; marque des appels internes au modèle C121 | Change le modèle utilisé ; exclu. Les zéros C121 imprimés au défaut ne prouvent pas une évaluation gratuite de ces sous-blocs. |
| C69/C78 AIR, V95/B9 et autres sondes physiques | Gates spécialisés, parfois par candidat / ville | Trop larges ou second calcul/sondage ; exclus. `probe_catalogue` active C39 et d'autres familles ; pas nécessaire à `CATALOG_COST`. |
| `stats.selectionOpcodes` | **Mesure existante sans gate** dans `OpexBuildProjects`, `OpexIncrementalUpdateProjects`, `OpexReselectProjects` | Aplatissement + fusion éventuelle + filtre AIR + `OpexProjectSelectAffordable` + quelques stats selon appelant. Pas uniquement le tri. Marques `OpexOpsMeasureBegin/End` locales. |
| `CATALOG_COST.selection_ops` | Même sonde catalogue, **path=full** | Réutilise `stats.selectionOpcodes`. Pour `path=mode/reselect`, le zéro initial ne signifie pas sélection gratuite : `mode_regen_ops/reselect_ops` sont des enveloppes plus larges. Le lecteur masque ce faux zéro de couverture. |
| `IG|` / `portfolio_selection_opcode_stats` | Panneaux existants `debug_signs=1`, collecteur de `bench_v2.py` | Milliers d'opcodes tronqués, instantanés pouvant republier la dernière sélection ; pas un cumul d'invocations. Pas de conversion/raccord depuis les checkpoints vers le log ici. |
| `C41_RAIL_PORTFOLIO_PROFILE`, B6, vivier | `probe_candidates_rail` puis gate de sortie `OpexC39Log` via `probe_catalogue`, ou `DECISION_LOG` pour B6 | Trop large pour ce besoin ; reprendre ces dépendances reproduirait le piège r1/r2. |

**Combinaison existante évaluée d'abord :** `catalog_cost_probe` seul, plus le
`AIR_PLAN_PERF:` déjà émis. Suffisant pour un coût global et une sélection
partielle ; insuffisant pour les dates réelles, les identités et la séparation
des sous-blocs AIR. C'est la seule justification de l'ajout Squirrel ci-dessous.

Attention au périmètre : la grande enveloppe `CATALOG_COST.air_ops` de
`OpexBuildProjects` inclut aussi la branche de secours `BOOTSTRAP_PAX_FALLBACK`
qui peut générer du rail pax. Elle n'est pas strictement identique à la somme des
appels `OpexAirPlans`, même avec des identités disponibles. Aucun ratio de ces
deux populations n'est présenté comme une partition exacte.

## 2. Ajout AIR minimal et couverture attendue

`OpexAirPlans` garde les mêmes appels métier, dans le même ordre, une fois chacun.
Autour de leurs frontières : `prepare`, `sites`, `new_pairs`, `hub_discover`,
`hub_site`, `hub_hub`, `finalize`. Pas de marque dans les boucles de candidats.
Les mesures des combos sont additionnées **localement par phase et invocation**.
Il n'y a pas de phase parente `hubs` en plus de ses enfants.

- Gate existant `CATALOG_COST_PROBE`, déclaré false, chargé une fois par settings,
  défaut 0 dans les quatre difficultés. Aucune dépendance au record catalogue actif.
  Donc couverture aussi des appels AIR ciblés C77 et des rebuilds hors scheduler.
- **Deux lignes `AIR_LIGHT v=1` au plus par invocation active** : ENTER puis EXIT,
  au plus sept agrégats sur EXIT. Pas de ligne par candidat, moteur ou combo.
- `OPEX_AIR_LIGHT_SEQ` est déclaré **dans le module attribué**, déjà chargé par
  `builder_air.nut`. Pas de symbole global non déclaré ni de raccord main/settings.
- `inv` identifie chaque appel actif ; `gen` identifie le scan AIR ; `slice` croît
  dans `resumeState.airLight`. Ce dernier ne contient que trois scalaires
  (`gen`, `slice`, `origin`), sans état économique. Il suit le curseur dérivé,
  abandonné au reload, pas un nouveau format de sauvegarde.
- Un résultat `resumeState.done` déjà prêt n'est pas remesuré comme génération.
  `prepare_return` couvre notamment l'absence de combo ; tous les retours de
  tranche sont clos. Une interruption moteur laisse ENTER ouvert.
- Si un curseur possède déjà `startTick` sans état de mesure, `origin=0` interdit
  de prétendre avoir le début du scan. Un nouvel appel AIR de fallback possède
  sa propre génération, même dans une seule reconstruction de portefeuille.

**Unités et bornes :**

1. `day` vient d'`AIDate.GetCurrentDate`, `tick` d'`AIController.GetTick` ;
   jours = différence des marques AIDate, jamais `/74` ni opcodes divisés par un débit.
   Les dates de l'enveloppe de log sont distinctes : concaténer/émettre peut suspendre.
2. `ops` réutilise `OpexOpsMeasureBegin/End`, convention 10 000 par tick traversé.
   Les suspensions/commandes peuvent gonfler ce proxy ; aucune durée CPU déduite.
3. Invocation = tranche active ; génération AIR complète = première ENTER à
   dernière EXIT terminale, avec toutes les tranches 1..N. La vie inclut les
   intercalations ; `slice_days_sum`, `slice_ticks_sum`, `slice_ops_sum` les excluent.
   Il n'y a volontairement **aucune mesure d'opcodes ouverte entre tranches**.
4. Les phases sont enfants du coût de tranche. On ne les ajoute ni à `ops`, ni
   à `CATALOG_COST.air_ops`, ni au total catalogue. Préparation/maintenance des
   marques et espaces entre phases restent dans l'enveloppe, pas répartis fictivement.
5. La marque de tranche est après allocation initiale de télémétrie ; elle inclut
   ENTER et agrégations, mais exclut la construction/émission EXIT. Les phases
   incluent leurs diagnostics préexistants internes ; `finalize` inclut les logs
   AIR historiques. Ces fenêtres ne mesurent **pas le surcoût net de la sonde**.

Sur carte où le scan est synchrone, N=1. Le chemin repris C78/C77 est supporté sans
activer C121 ; son exposition naturelle n'est pas garantie dans le smoke. Aucun
nouveau découpage comportemental ni délai de retour n'est promis. La durée d'une
génération **de portefeuille entière** reste non identifiée par ce lot.

## 3. Lecteur : contrats et raccord sélection réservé

Réutilise `parallel_latency_audit.parse_log`, `read_sources`, `distribution`,
`reference`, `difference`, `nonnegative` et les parseurs transitifs de champs.
Entrées : logs bruts `.log` ou JSON Save/Load aux chemins explicites
`phase_a/phase_b.openttd_output_raw`. Un JSON sans brut donne `raw_missing=true`,
pas zéro activité. Pas de suivi automatique d'un `log_path`, ni double ingestion
des checkpoints cumulatifs. Ne pas fournir plusieurs copies du même flux comme
des parties indépendantes ; les chemins identiques sont refusés.

- Identité complète = **source/phase + compagnie + session + gen + inv + slice**.
  LOAD_RECONCILE et retour de date séparent les sessions. Sans marqueur reload,
  fournir impérativement deux sources/phases distinctes ; pas de reload inféré
  à partir d'un rang ou d'une identité répétée. Collisions contradictoires rejetées.
- Copies exactes d'une publication identifiée dédupliquées ; collision différente,
  mauvais gen/target/band, tranches manquantes, non closes ou chevauchées :
  génération censurée. Régression de tick dans une invocation = fenêtre invalide.
- Absence/invalide → `null`, zéro publié → 0. Une génération structurellement
  complète peut encore manquer une unité ; lire les couvertures par unité.
  Une phase non visitée n'est pas imputée à zéro par le lecteur.
- Anciennes lignes AIR structurées et non structurées conservées séparément ;
  **jamais additionnées**, sans identités vérifiées. `legacy_days_tick74` conserve
  l'ancien champ sans lui donner un sens calendaire.
- Les bilans catalogue sont des **publications**, jamais joints à la génération
  AIR la plus proche ni présentés comme un dénombrement de sélections uniques.
  `path=full` fournit la mesure existante de sélection ; jours/ticks inconnus.

### Raccord exact à proposer au lot 3 / intégrateur — non effectué

**Aucun raccord indispensable pour compiler le lot AIR ou lancer le profil réduit.**
Pour une mesure unique de *toutes* les sélections avec calendrier/ticks, il faut
compléter les points suivants, dans un amendement stabilisé avant tout banc :

1. Dans `projects_selection.nut::OpexReselectProjects`, ajouter un identifiant
   transitoire local à la VM et deux marques AIDate/GetTick aux **mêmes bornes**
   que `opsMark` / l'affectation `projects.stats.selectionOpcodes`. Émettre une
   ligne agrégée sous `CATALOG_COST_PROBE`, directement via AILog.Info,
   **après** l'affectation, avant B6. Réutiliser la valeur calculée, ne pas rappeler
   le sélecteur, ne pas ajouter un second `OpexOpsMeasureEnd` au même intervalle.
2. Contrat proposé `SELECTION_LIGHT v=1 inv=<id> path=reselect start_day=…
   end_day=… start_tick=… end_tick=… ops=<selectionOpcodes> considered=… selected=…`.
   Déclarer le compteur dans le module qui le possède, pas une globale fantôme.
   Identité sourcée/sessionnée comme AIR ; aucune association à `AIR_LIGHT.gen`
   sans lien explicite fourni par le producteur. Ce lecteur ne prétend pas déjà
   accepter ce futur format : test et raccord de lecture avant amendement moteur.
3. Pour la couverture **full et incremental**, même raccord autour des marques
   existantes de `projects.nut::OpexBuildProjects` et
   `projects_update.nut::OpexIncrementalUpdateProjects`. Ces deux fichiers aussi
   sont hors de ce lot : l'intégrateur doit attribuer explicitement ces écritures.
4. Une ventilation interne tri/filtre n'existe pas ici : ne pas remplacer le
   périmètre de `selectionOpcodes` par une autre mesure sans changer le contrat.
   Ne pas ajouter une dépendance au lot 3 dans le défaut livré par ce lot.

Sans ce raccord, la conclusion sélection restera limitée aux publications
catalogue full ; aucun total de toutes les sélections ni ratio AIR/sélection
joint par génération ne sera produit.

## 4. Protocole moteur pré-enregistré — à exécuter par l'intégrateur seulement

`--plan` affiche le plan sans import de lanceur ni partie. L'intégrateur réutilise
**`diag_cadence_duel.main`**, avec `arm_specs=ARMS` et les `harness_kwargs` de
`PROTOCOL`. Conserver ses collecteurs, `assess_game`, décodages physiques,
couverture annuelle, alignement final et empreintes avant/après. Aucun nouveau
lanceur/collecteur copié dans ce lot. `--probe` est **interdit** : il armerait
decision/portfolio symétriquement et changerait l'expérience.

Le harnais conserve sa métadonnée générique `primary=mean_per_seed_annual_ratio_pct`
et son seuil utile 50 k£ ; ils ne deviennent pas les critères de cette expérience.
Archiver aussi cette fiche et `PROTOCOL` avec le plan natif, conserver le verdict
brut du harnais et appliquer séparément les critères de perturbation ci-dessous.
Aucune neutralité ni qualification ne découle du seul `complete=true`.

### Prérequis de lancement

- Attendre la fin de **toutes** les éditions parallèles et résoudre les contrats
  en échec. Même arbre stabilisé dans les deux bras, adversaire AAAHogEx-115,
  mêmes configurations/opcodes/debug et versions 15.3 / NoAI15 / OpenGFX7.1 /
  OpenTTDLab0.0.75. Figer manifeste/hashes ; ne pas appeler un bundle « exécuté »
  si le harnais utilise encore l'arbre monté mutable. SHA Git absent actuellement.
- Bras `reference=OpexAI` ; `light=OpexAI[catalog_cost_probe=1]`.
  Résolution effective : **une seule différence**, ce flag. C115=1, expériences
  cadence=0, C84/C85/C121/C122 OFF. Vérifier aussi tout drapeau test-only des autres
  lots OFF. Script debug **4 dans les deux bras**, panneaux par défaut conservés.
- Plafond global **12 CPU / 12 workers**, toutes campagnes confondues, piloté par
  l'intégrateur. Préférer un seul conteneur de partie : 3 CPU, 2 Go sans swap,
  cache `openttd-lab-home`, 2 workers smoke puis 3 workers diagnostic. Ne jamais
  multiplier les conteneurs sous prétexte que chacun respecte son plafond.
- Sorties **neuves** sous `results/air_selection_light/`, préfixes suggérés
  `engine_smoke_20261001_r1`, puis `engine_perturbation_20261001_rep1/rep2`.
  Conserver aussi plan du harnais, logs et checkpoints `.artifacts`. Aucun écrasement.

### Portes et budget fixé avant résultats

1. **Smoke apparié : 42 × 1 an × deux bras**, 1970 → checkpoint 1971-02-01.
   Santé complète, aucune erreur script/fatal, sources inchangées. Témoin : zéro
   `AIR_LIGHT`, ancienne ligne AIR attendue mais pas imposée comme activité.
   Variante : au moins une génération AIR complètement identifiée et une phase
   non nulle ; au moins un bilan catalogue `path=full` avec `selection_ops` valide.
   Toutes les fenêtres closes hors éventuelle dernière invocation censurée à
   l'horizon ; aucun conflit d'identité. Publier couverture et log-volume.
   Sinon arrêt **non validé**, pas élargissement spontané des sondes.
2. **Perturbation seulement après smoke sain/exposé :** graines
   42, 100, 999, 1234, 5678 × 6 ans × deux bras × **deux répétitions**, soit
   20 parties, réalisées en deux campagnes séparées du même protocole, arrêt
   1976-02-01. Ne pas relancer les graines perdantes. Les répétitions précisent
   le bruit du duel ; elles ne font pas dix graines indépendantes. Moyenne des
   deux répétitions par graine, puis statistiques appariées sur les cinq graines.
3. Primaire : delta du `profit_year` Opex de la dernière année complète (1975),
  moyenne/médiane, deltas par graine et IC95 Student à quatre degrés de liberté,
  via `bench_1v1_5y_20seeds.delta_statistics`, champ
  `mean_student_t_95pct_ci`, appliqué aux cinq deltas moyens par graine.
  Vérifier 5/5 valeurs avant cet appel (ce helper filtre les valeurs absentes) ;
  petit effectif, hypothèse de Student et test des signes à publier sans
  sélection après résultat. Secondaires : trajectoire annuelle, valeur,
   appareils/aéroports, date de première apparition aux checkpoints. Les dates
   exactes de construction absentes restent inconnues ; pas de `decision_log`
   ajouté pour les récupérer. Ratio Opex/AAA et profit AAA descriptifs seulement.
4. **Filtre pratique, pas preuve de neutralité :** moyenne des profits Opex au
   moins 95 % de celle du témoin, garde de valeur −5 % et au moins 3/5 deltas moyens
   par graine non négatifs. Si profit de référence non positif, données absentes,
   santé incomplète ou échec : arrêt/indécis, aucune neutralité. Même si le filtre
   passe, ne pas dire « neutre » sur ce petit effectif ; toute qualification
   ultérieure exige un protocole plus puissant séparé, sans 20×10 automatique ici.
5. Save/Load technique à prévoir avec `save_load_roundtrip.py` existant : sonde ON,
   reprise d'une sauvegarde avec scan C78/C77 en cours **si ce chemin est exposé
   naturellement sans activer C121**. A/B bruts distincts ; ancien scan censuré,
   nouveau gen VM autorisé, jamais fusionné. Si pas de tranche active obtenue,
   publier « exposition de reprise absente », pas une validation inventée.

Les écarts de duel comprennent perturbation des opcodes, changement de calendrier,
concurrence et divergence des trajectoires ; **ils ne sont pas tous le coût direct
de la sonde**. Un scan instrumenté n'est pas une mesure du scan sans instrumentation.

### Critère de prochaine optimisation, fixé avant mesure

Après portes précédentes, avec au moins cinq générations AIR closes par graine
et ≥90 % des invocations appariées (publier aussi abandons et fins censurées) :
calculer pour chaque graine les parts `somme phase.ops / somme slice.ops` sur les
seules mêmes invocations couvertes, puis la médiane inter-graines. Retenir un
bloc AIR seulement s'il est le premier poste et représente ≥20 % de l'enveloppe
AIR dans **au moins 4/5 graines**, sans mélange de scopes target/band/sliced.
Publier jours/ticks p95 et maxima en parallèle, sans les convertir en opcodes.
Une faible couverture ou un résidu non instrumenté dominant appelle une nouvelle
mesure ciblée, pas une optimisation arbitraire.

La sélection peut devenir prioritaire si sa part dans les **bilans full** reste
≥20 % dans 4/5 graines ; cela justifie d'abord le raccord d'identité/périmètre du
§3. Ce n'est ni un classement global sur toutes les sélections, ni la preuve que
le tri seul domine. Aucune optimisation comportementale n'est livrée dans ce lot.

## 5. Tests, preuves et limites finales

- VS Code n'a découvert aucun test ; exécution explicite par `unittest`, Python
  **3.14.4**, `-B -X utf8`, sans bytecode ni installation.
- **34/34** nouveaux tests réussis : absence/zéro, unités, phases non additionnées,
  tranches manquantes, dates/ticks invalides, répétitions, collisions, reload,
  compagnies, sources, garde de sortie, gate et ordre des appels métier.
- Suite ciblée élargie : **106 exécutés, 105 réussis, 1 échec**, 0 erreur/skip.
  Détail dans [test_execution_20261001.json](../results/air_selection_light/test_execution_20261001.json).
  Échec `test_c121_catalog_incremental.…test_new_squirrel_identifiers_avoid_keywords` :
  la regex de mot-clé trouve **`base=` dans une chaîne de log R1/R3** de fichiers
  édités concurremment, hors de ce lot. Ne prouve pas un identifiant Squirrel
  interdit. Ni le contrat ni ces fichiers n'ont été corrigés/masqués par ce lot.
- Contrats catalogue 2/2, préfiltre AIR 13/13, C115 5/5, R4 6/6, hygiène C78
  10/10, V93 5/5, lecteur de latence 24/24 ; 6/7 contrats C121 passent.
- Analyse statique Python et diagnostics d'éditeur : aucune erreur dans les
  fichiers du lot. **Ces tests ne compilent pas Squirrel.** Smoke/reload et
  perturbation de la nouvelle sonde restent entièrement non exécutés.
- [Fixture synthétique](../results/air_selection_light/fixture_20261001.log),
  [lecture](../results/air_selection_light/synthetic_20261001_r1/audit.json) :
  génération 11 jours / 1 020 ticks ; tranches 2 jours / 30 ticks / 300 opcodes.
  Un scan censuré avant reload ; nouveau scan nul après reload, identité séparée.
  **Chiffres de fixture, pas de performance moteur.**
- [Lecture des logs r2 existants](../results/air_selection_light/legacy_20261001_r1/audit.json) :
  témoin 12 lignes AIR brutes, profil 10 brutes + 10 structurées, cinq bilans
  catalogue. Aucune nouvelle génération `AIR_LIGHT`, zéro anomalie de parsing :
  couverture de la nouvelle sonde **absente**, pas son coût nul. Les deux copies
  AIR du profil ne sont pas additionnées. Empreintes des entrées inchangées.
- [Empreintes initiales](../results/air_selection_light/baseline_20261001.json) :
  pas de Git ni `.git`, donc pas de diff/SHA historique revendiqué. Dans les dix
  fichiers échantillonnés, `air_planning.nut` change pour ce lot et
  `projects_selection.nut` a changé concurremment ; les huit autres sont inchangés
  au contrôle. Cela ne certifie pas l'immuabilité globale du dépôt parallèle.
- Contrôle inverse **en mémoire**, sans réécrire le fichier : retirer les seuls
  ajouts de ce lot et rétablir les deux formes de retour originales reproduit
  exactement le SHA-256 initial d'`air_planning.nut` (LF). Les trois sources
  testées concordent encore avec les empreintes publiées ; liens locaux valides,
  aucun espace final dans les fichiers du lot. Aucun changement antérieur AIR
  n'a été effacé par le patch.

**Conclusion :** profil réduit autonome, dates et identités AIR couvertes par le
contrat, sélection full réutilisée avec ses limites. Aucun gain, neutralité,
couverture moteur nouvelle ou découpage comportemental n'est encore démontré.