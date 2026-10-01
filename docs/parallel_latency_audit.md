# Audit de latence — 30 septembre 2026

## Conclusion et statut

**Priorité proposée : rendre reprenable le parcours des paires passagers rail de
`OpexPaxCandidates`, pas accélérer les seuls no-op du scheduler.** C'est une
**hypothèse d'intervention bornée**, pas un goulot dominant démontré : les traces
actuelles prouvent des reconstructions synchrones de portefeuille de **24–29 jours**,
mais ne ventilent pas ces journées entre paires rail, fret, route, AIR et sélection.
La prochaine intervention minimale est donc le raccord de mesure décrit au §6,
avant de décider ce découpage. Aucun changement comportemental dans ce lot.

Un intervalle entre constructions ne devient jamais une durée de calcul par défaut.
L'attente financière et la vie d'une recherche peuvent durer plus longtemps que
le calcul et se recouvrir. **Aucun gain économique ni construction avancée démontré.**
C115 protégé ; cadence, stock A* et C121 non réactivés.

## 1. Livrables, sources et reproductibilité

- `sweeps/parallel_latency_audit.py` : lecteur hors ligne, aucun import de lanceur.
- `sweeps/test_parallel_latency_audit.py` : 24 tests ciblés.
- Preuve finale : `results/parallel_latency_audit/audit_20260930_r3/audit.json`.
  Chronologie dans l'ordre source, champs bruts, compagnie, session, références
  de lignes, observations, intervalles, distributions et cas non appariés.
- Lecture courte : même dossier, `summary.json` : couvertures, médianes, p95,
  maxima, catégories et exemples. Empreintes SHA-256 des **27 fichiers lus**,
  contrôlées avant/après lecture et avant publication.
- Les dossiers `audit_20260930_r1` et `audit_20260930_r2` sont des sorties
  intermédiaires conservées, **non autoritaires** : r3 corrige notamment l'unité
  historique `AIR_PLAN_PERF.days`. Aucun nettoyage demandé/effectué.

Entrées exactes de cette exécution : les quatre `.log` de
`results/diag_cadence_exposure_20260930_r1.artifacts/`, les vingt `.log` de
`results/diag_cadence_5x6_20260930_r1.artifacts/`, puis
`save_load_r4_probes_20260930.json`, `save_load_exp_cadence_20260930_r2.json` et
`diag_c50_chronology_probe_6y_5seeds.json`, sous `results/`.
Interface : entrées positionnelles et `--out`, obligatoirement un **nouveau**
sous-dossier de `results/parallel_latency_audit/`. Écrasement et doublons refusés.

| Source | Couverture exploitable / limite |
|---|---|
| Exposition cadence | 4 duels, graine 42 ; 4 233 / 4 382 / 4 601 / 4 343 événements OPEX respectivement hubs / référence / scheduler / watcher. Début 01/01/1970 ; dernière trace 27/01/1971 pour hubs, 01/02/1971 pour les autres. Pas une comparaison économique qualifiée. |
| Diagnostic cadence 5×6 | Les **20/20 logs ont zéro marqueur OPEX daté** exploitable ici. Cela signifie couverture chronologique absente, pas inactivité ni zéro construction. Les résultats économiques restent ceux de `cadence_parallel_20260930.md`, non recalculés. |
| Save/Load R4 | Deux flux bruts, phases A 1970–1971 et B 1971 ; scénario expérimental distinct du défaut. 733 `SCHED_IDLE`, 167 `CATALOG_COST_SLICE`, 52 `PROJECTS_COST`, 26 couples P2. Pas d'activation de cette expérience par l'audit. |
| Save/Load cadence | Deux flux A/B séparés, trois options combinées : contrôle technique seulement, pas témoin économique. Tous les résultats restent séparés dans les JSON. |
| Ancienne chronologie C50 | JSON agrégé seulement : aucune sortie brute datée reconnue. Exclu des statistiques temporelles ; aucune performance actuelle déduite de cette ancienne campagne. |

Total : **28 flux lus, 56 736 événements OPEX**, zéro anomalie de parsing ou
d'appariement signalée sur ces entrées. Il n'y a **aucune paire C56 ENTER/EXIT**
dans ces flux : leur parseur est testé par fixtures, pas exposé par ces parties.
Zéro anomalie n'établit ni complétude des marqueurs ni santé du moteur.
Le statut de santé des campagnes n'est pas requalifié par cet audit.

Instructions consultées : `AGENTS.md`, `CLAUDE.md`, `ai/OpexAI/CLAUDE.md`, état
courant de `docs/taches.md`, fiche cadence ; historique du 13 septembre, archive
des tâches et journal du 30 pour les pistes abandonnées. Git absent dans cette
copie : pas de diff Git, SHA du code exécuté ou bundle immuable revendiqué.

## 2. Contrats de lecture et d'unités

Réutilisation par import de `analyse_sched_idle.parse_fields`,
`parse_sched_idle_output`, `_percentile`, de
`analyse_v86_cannibalisation.parse_c56_log_line` / `to_int` et de
`analyse_p5_preplan.parse_p5_output`. Les défauts zéro des anciens collecteurs
sont masqués si le champ brut est absent/invalide. `diag_sched_idle.py` a été lu,
**pas importé ni exécuté** ; idem pour le lanceur C50 à monkey-patch global.

- `days` : différences calendaires réelles ou mesure AIDate explicitement publiée.
- `ticks` : ticks **AIController**, conservés sans conversion automatique.
- `ops_proxy` : convention `OpexOpsMeasureEnd` (`budget.nut:14–30`), 10 000 par
  tick franchi plus restes. Ce n'est pas un compteur d'instructions CPU pur ;
  commandes suspendues/intercalations peuvent gonfler une mesure englobante.
- **Piège découvert** : `air_planning.nut:1879–1899` publie
  `AIR_PLAN_PERF.days = elapsedTicks / 74`. Ce champ n'est pas une différence
  AIDate. Il devient `legacy_days_tick74`, jamais fusionné avec les jours
  calendaires. En mode découpé, les ticks couvrent la vie du scan, pas seulement
  ses tranches. **Ne pas lire “days=4” comme quatre jours de blocage.**
- Worker C56 : seuls `step_ops` mesurent ses étapes ; ENTER→EXIT couvre sa vie
  avec intercalations. Parents et sous-étapes ne sont jamais additionnés.

Médiane usuelle ; p95 interpolé linéairement à `(n−1)×0,95`. Chaque distribution
donne `eligible`, `n`, `missing` ; absence → `null`, zéro observé → zéro.
Petits effectifs, répétitions au sein d'une partie : pas d'IC ni de preuve causale.
Séparation stricte par fichier/phase, compagnie, rechargement ou retour de date.

`TASK` est un début sans fin : son intervalle avec le `TASK` suivant reste
**inconnu**, même si le premier s'appelle `catalog`. `C78_CAND` est une observation
de candidat publiée, pas la date de son calcul initial. Aucun raccord forcé
évaluation→construction sur le seul rang ; les rangs changent et les variantes
partagent des paires. Seul choix AIR→AIR_BUILD avec mêmes `src/dst`, sans choix
concurrent ambigu ni rejet intermédiaire, est apparié ; cela ne mesure pas la
première recette ni toute l'attente antérieure.

## 3. Mesures contemporaines : où le temps est visible

Dans cette section, chemins abrégés = dossier d'exposition cadence ci-dessus.
Tous les exemples contiennent compagnie **0**, graine **42**.

### 3.1 Reconstruction complète : calcul synchrone confirmé, sous-bloc inconnu

`B6_FRESH_EQ scope=all rebuild_days` est émis après le rebuild normal, pas après
un second rebuild de sonde. Vérification : `task_projects.nut:1897–1973` prend
`b6StaleDate`, appelle `OpexBuildProjects`, puis
`OpexB6LogFreshEquivalence`; `projects_diagnostics.nut:181–251` prend
`now−snapshotDate`. Les autres scopes répètent cette durée : **seul `all` compte**.
Cela inclut la préparation normale, la génération, la sélection et le début
du diagnostic B6 ; pas un temps exclusif des paires rail.

| Bras | n mesures / médiane / p95 / max (jours calendaires) |
|---|---:|
| Référence | 2 / 27 / 28,80 / **29** |
| Scheduler | 2 / 25,50 / 25,95 / 26 |
| Hubs | 2 / 25,50 / 25,95 / 26 |
| Watcher | 1 / 24 / 24 / 24 |

Exemple : `reference_42.log:5901`, **12/01/1971**, `rebuild_days=29` ;
`watch_daily_42.log:3250`, **12/07/1970**, `rebuild_days=24`.
Ticks et opcodes de **ces mêmes fenêtres** absents (0/2 en référence), pas zéro.
Ces sept mesures ne couvrent ni tous les rebuilds, ni les vingt parties longues.

### 3.2 AIR : coût mesuré, pas quatre jours calendaires

Référence, 10 `AIR_PLAN_PERF` : ticks médiane **332,5**, p95 **384,15**, max **399** ;
opcodes conventionnels médiane **3 320 818**, p95 **3 835 966,75**, max **3 980 590**.
Couverture 10/10 pour ces deux unités ; jours calendaires **0/10**.
Le champ historique donne médiane 4, p95 4,55, max 5, mais utilise `/74`.
Exemple maximum : `reference_42.log:2744`, 07/05/1970, scan AIR.
Ne pas soustraire ces « 5 » des 29 jours du rebuild : unité et fenêtre différentes.

### 3.3 Construction : l'attente est surtout avant le choix visible, cause non isolée

`construction_gap` = intervalle entre événements C50 `project_built`, **flotte
comprise**, pas entre toutes les nouvelles lignes. `chosen_to_air_build` est
plus étroit et couvre seulement les choix/builds AIR raccordables.

| Bras | Intervalles C50 (n) | médiane / p95 / max, jours | Choix AIR→build (n), max |
|---|---:|---:|---:|
| Référence | 7 | 52 / 68,60 / **74** | 8, 0 jour |
| Scheduler | 8 | 45 / 69,45 / 74 | 8, 0 jour |
| Hubs | 9 | 43 / 67,60 / 70 | 9, 0 jour |
| Watcher | 9 | 50 / 74,40 / **76** | 9, 0 jour |

Couverture calendaire n/n ; ticks et opcodes absents pour tous ces intervalles.
Les médianes et p95 choix→build sont également zéro : **même journée**, pas
gratuité ni instantanéité. Tous les premiers AIR_BUILD ont lieu le 05/02/1970.
Les options scheduler/watcher n'avancent donc pas ce premier build dans ces logs.

Exemples inconnus : référence `:3087→3993`, 16/05→29/07/1970 (**74 j**) ;
watcher `:2973→3699`, 18/05→02/08 (**76 j**, fin sur événement flotte).
Ces fenêtres ne sont attribuées ni à rail, ni à catalogue, ni à finance.
Les écarts `TASK→TASK` atteignent 32 j en référence, 40 j dans le watcher :
ce ne sont **pas** des durées d'exécution des tâches.

### 3.4 Watcher : contrôles espacés, détection censurée

`watch_daily_42.log:6008`, 12/01/1971 : 33 polls, 198 observations de ville,
15 changements, **0 enqueue**, 98 419 opcodes cumulés, `max_gap_days=38`.
Treize résumés mensuels ne sont pas treize polls : **médiane/p95 des 32 gaps de
poll inconnus**, seul leur maximum cumulé est fourni.

Neuf changements non initiaux fournissent `detected−seen_before` : médiane
**19 j**, p95 **26,20 j**, max **31 j** (`:2642`, 06/05/1970).
C'est la largeur d'une fenêtre d'observation, pas le retard exact depuis la
construction adverse. Six premiers états sont exclus, leur passé est inconnu.
Sans enqueue, aucun délai détection→action de régénération n'est mesurable.

## 4. Classement des délais, avec limites causales

Les catégories se recouvrent temporellement : **ne pas sommer leurs durées**.

| Catégorie | Preuve et ampleur | Ce qui reste inconnu |
|---|---|---|
| Calcul synchrone | Rebuild complet 24–29 j dans l'exposition cadence (§3.1). | Part exclusive du rail pax, du fret, de la route, d'AIR et du classement. |
| Attente financière | R4 A : 8 retours P2 après `all_unaffordable`, médiane **22,5 j**, p95 **47,25**, max **49** ; ticks **415 / 883,65 / 919**. R4 B : 2 épisodes, **14 / 18,5 / 19 j**. | Cause **initiale** seulement : le retour peut venir d'une génération ciblée/refleet ; pas 49 jours de trésorerie continuellement insuffisante prouvés. |
| Recherche en cours | R4 A : 11 fins de recherche avec `slices>0`, médiane **4 j**, p95 **50**, max **59** ; ticks **76 / 920 / 1088**. R4 B : 16, **7 / 27,25 / 46 j**. | Vie de recherche avec intercalations, pas 59 jours d'A* continu ni preuve que plus de stock ferait construire plus tôt. |
| Candidat caduc | `batch_plan_dead` : référence **2** lignes de log, hubs **20**, watcher **33** ; identités/raisons conservées dans la chronologie. | Pas de naissance/expiration appariée : durée médiane/p95/max **inconnue**. Ni taux d'échec unique ni nombre de marchés perdus déduit de ces compteurs. |
| Cause inconnue | Intervalles C50 jusqu'à 76 j en exposition, **94 j** en R4 B. | Impossible de répartir ces silences entre les catégories précédentes. |

R4 finance maximum : `save_load_r4_probes_20260930.json`, texte
`$.phase_a.openttd_output_raw`, lignes **10793→13548**, épisode P2 **13**,
24/04→12/06/1971. P5 précise `ret_reason=refleet`, pas uniquement reconstitution
de trésorerie. Des épisodes P2 se chevauchent : ce ne sont pas des observations
indépendantes. Les 18 P2 A incluent 10 retours immédiats ; la distribution
financière est celle des **8/18 classés**, pas une sélection de durées longues.

R4 recherche maximum : même texte, **ligne 322**, 12/03/1970, `id=1`,
`src=9815 dst=13978`, 14 tranches, 59 j, 1088 ticks, **2 221 779 opcodes**.
49 autres publications A et 55 B ont zéro tranche mesurée ; elles incluent des
relectures de résultat prêt. Elles sont conservées dans un groupe distinct,
jamais ajoutées comme recherches rapides pour abaisser la médiane.

R4 `PROJECTS_COST`, phase A : 39 mesures, `regen_ops` médiane **125 050**,
p95 **1 907 780,40**, max **8 162 732**, contre `build_ops` **70 679 /
1 485 741,30 / 2 393 430**. Cela prouve qu'un coût de `projects` peut être du
rebuild après tentative, pas uniquement de la construction. Aucun jour/tick
de sous-phase disponible (0/39). Ce scénario ne qualifie pas le défaut courant.

## 5. Code existant et unique découpage proposé

**Code vérifié, lecture seule :** `main.nut:699–758` traite les événements puis
l'orchestrateur ; la VM qui suspend un calcul reprend ce calcul, pas cette
boucle. Le dispatcher ne rend la main qu'au retour du sous-programme.
`orchestrator.nut:734–840` possède déjà des workers ; le worker générique retourne
avant la file de fond. Un worker de plus n'assurerait donc pas automatiquement
la progression des constructions. Le rapport annuel a aussi des mutations,
ce n'est pas une simple impression que l'on pourrait morceler sans contrat.

**Seul bloc proposé :** `candidates.nut:1067–1140`, préparation et parcours
des paires dans `OpexPaxCandidates`. Il calcule production/service, construit une
grille, parcourt sources/voisins, filtre et appelle `OpexMakeCandidate` sans
checkpoint. Aucune infrastructure n'est construite dans ce bloc. L'ancienne
domination rail relatée dans l'archive est antérieure à des caches adoptés :
elle explique le choix à profiler, **ne prouve pas sa domination actuelle**.

Contrat envisagé, **non implémenté** :

- **État minimal :** phase préparation/grille/paires/terminé ; index ville puis
  source/voisin, liste des voisins courants ; contexte cargo/bornes/bande/cible ;
  productions, services, grille, compteurs, résultats privés, caches locaux,
  versions des dépendances et identifiant de génération. Préserver l'ordre exact
  des voisins/égalités et tous les filtres, aucun nouvel TopK anticipé.
- **Suspensions :** après chaque ville préparée et chaque paire terminée,
  y compris les branches de rejet ; fermer la mesure de tranche puis retourner
  effectivement jusqu'à la boucle principale. Pas de `Sleep` au milieu du helper,
  ni de boucle appelante vidant immédiatement toutes les tranches. Construction
  de grille, liste de voisins et **une paire** restent à mesurer : aucune garantie
  « au plus un tick » avant cette mesure.
- **Raccord appelant :** propager `pending` depuis `OpexBuildCandidates` vers
  génération complète/par mode et dispatcher, sans publier un portefeuille
  partiel. Garder le dernier portefeuille utilisable, mais revalider ses projets
  avant construction. Ne pas installer un worker qui affame la file de fond.
- **Invalidation :** révisions villes, moteurs rail, lignes, contexte catalogue,
  production/période, facteurs économiques et abandons. Si un changement arrive
  pendant la génération, ne pas l'acquitter avec la version de fin ; abandonner
  ou reprendre sur un nouveau contexte cohérent. `OpexSitableCache`, aujourd'hui
  global/réinitialisé par `OpexBuildCandidates`, doit être attaché à cette
  génération ou explicitement invalidé. Ne pas laisser un budget ouvert entre
  tranches, sinon les travaux intercalés seraient imputés au rail pax.
- **Save/Load :** brouillon dérivé jetable, pas de sérialisation de grille,
  objets API/candidats flottants. Après réconciliation, réarmer la génération
  sale depuis les révisions conservées, sans publication/acquittement partiel
  ni deuxième achat. Tester reload pendant préparation, paire, avant publication,
  formats court/complet, et changement de ligne pendant suspension. Le format
  courant conserve les échéances des tâches, pas un curseur arbitraire nouveau.

Découper diminue potentiellement le temps sans contrôle, **pas nécessairement
le temps avant publication**. Si le profil actuel innocente ce bloc, ne pas le
modifier sur la foi des anciens résultats ; aucune deuxième proposition ici.

## 6. Prochaine intervention minimale et critère « construire plus tôt »

Raccord à préparer par le lot autorisé à modifier `ai/`, **pas réalisé ici** :

1. Réutiliser `OpexC56TaskLog` / les mesures locales pour borner le rebuild normal
   et **ce seul parcours rail pax** ; ajouter un identifiant d'invocation/génération
   commun et les révisions d'entrée. Début/fin de tranche : AIDate, GetTick,
   restes/opcodes, raison du retour. Conserver séparément durée de vie et somme
   des tranches. Le profil `C41_RAIL_PAX_PROFILE` peut ventiler préparation,
   paires et `OpexMakeCandidate` ; il manque ici.
2. Relier, avec identité stable de projet/variante et génération : demande de
   régénération → première évaluation → publication/éligibilité finançable →
   élection → tentative → succès du builder → **mise en service du premier
   véhicule**. Journaliser aussi invalidation, refus financier et abandon.
   Un rang ou une paire de villes seul n'est pas un identifiant suffisant.
3. Instrumenter les retours effectifs à la boucle, pas seulement les polls ayant
   changé d'état. Mesurer le coût de la sonde symétriquement et employer une vraie
   différence AIDate au lieu du champ AIR `/74`.

**Mesure principale proposée avant banc centralisé :** temps calendaire entre
le déclencheur de régénération/opportunité identifié et la première mise en
service réussie, par épisode, puis delta apparié variante−référence. Publier
médiane, p95, maximum et couverture, dates absolues des services, nombre de
services à horizons fixes et épisodes non aboutis/censurés. Ne pas exclure les
échecs, invalidations ou occasions devenues non finançables. La mesure
publication→service est secondaire : prise seule, elle masquerait une publication
retardée par le nouveau découpage. Diminution des opcodes ou du gap des polls
sans avance des mises en service = **objectif non démontré**.

Aucun gain économique ne sera conclu sans comparaison valide ; les contrôles
profit/valeur et le protocole d'adoption restent distincts. Les futurs bancs sont
centralisés après éditions, plafond global 12 CPU/12 workers ; **aucun n'a été
lancé par cet audit**.

## 7. Validation réalisée et limites finales

- Exécution ciblée `unittest discover`, dossier `sweeps`, motif
  `test_parallel_latency_audit.py` : **24/24 OK**, Python 3.14.4, option `-B`
  (pas de bytecode écrit dans les harnais partagés). L'interface de tests VS Code
  n'avait pas découvert cette suite ; exécution directe unittest réussie.
- Cas : logs incomplets/nombres tronqués, absence contre zéro, entreprises
  intercalées, worker et tâches intercalés, mauvais cycle, double ENTER,
  changement d'année/bissextile, retour d'horloge/reload, choix ambigu/rejeté,
  P2 censuré, répétitions de recherche prête, unités AIR et p95.
- Analyse r3 terminée : 27 sources, 28 flux ; aucune partie, aucun conteneur,
  aucune installation, modification de défaut, de `ai/`, des harnais, du suivi
  commun ou de VS Code. Pas de commit/push/nettoyage.
- Ces tests Python ne compilent pas Squirrel. Les sorties d'exposition sont
  instrumentées, sur une seule graine ; les logs économiques longs n'exposent
  pas la chronologie demandée. La persistance du **nouveau** découpage reste
  entièrement à valider après autorisation et implémentation.