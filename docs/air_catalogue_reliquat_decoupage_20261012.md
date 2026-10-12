# AIR catalogue — reliquat de découpage après le commit 978d098

État vérifié le **12 octobre 2026** dans `master` après le commit
`978d098`. Ce document constitue un **plan de travail**, pas une
qualification ni un changement de production.

## Ce qui est clos

- Huit audits AC-01 à AC-08 documentés, fonctions de génération AIR
  spécialisées et curseurs reprenables contrôlés ; ne pas recommencer
  les audits ni les campagnes concluantes.
- AC04-B (déduplication par ancre et non par ville), AC05 (pré-calcul
  marginal V86 inutilisé sous C121) et **AC06 v2** (acquittement C76
  plafonné à sept révisions photographiées) adoptés avec réglages à 1
  et retour à 0 possible. AC06 v2 a été **accepté explicitement malgré
  un surcoût initial de +32 opcodes** sur les dix paires mesurées.
- Cumul AC04-B+AC05 : B20×10 économie, 10×4 opcodes ; interaction
  AC06 v2 additionnelle : 10×4, 20/20 parties saines, profit annuel
  +6 190 £, IC95 [−12 662 ; +33 747], opcodes exécutés 1970–1972
  −150 863 en moyenne, IC95 [−474 394 ; +21 766], **mais 9/10
  paires avec une hausse d'opcodes**. Save/Load AC06 v2 réel OK.
  Aucune équivalence stricte ni exposition VM d'un événement late-ack
  ne sont établies.
- AC04-A v1/v2 (hub saturé classé orphelin) rejetées pour opcodes ;
  AC06 v1/v3 rejetées ; V142 (coalescence des publications) et V143
  (conservation des curseurs hub / refresh hors AIR en cours de scan)
  rejetées. V141 et les choix économiques existants sont conservés.

## Dette de découpage : différence entre fonction et tâche exécutable

Le code possède déjà les fonctions
`OpexAirPlansPrepare`, `FindSites`, `NewPairs`,
`DiscoverHubs`, `HubToSite`, `HubToHub` et `Finalize`
dans `air_planning.nut`. **Elles ne sont pas sept tâches
autonomes** : `OpexAirPlans` les enchaîne dans sa boucle de combos
(`air_planning.nut`, vers 2341–2558).

`OpexC78ContinueCatalogAirRebuild` gère encore la publication
partielle, le balayage et l'application finale dans un même objet
`task.c78AirRebuild` (`scheduler_tasks.nut`, vers 15–247).
`main.nut` conserve une seule entrée `catalog` à l'index 0 de
`_taskQueue`, y compris pour la boucle d'avancement C121 du même
tick. Les entrées/indices de cette file servent aussi à la
compatibilité des sauvegardes. Par conséquent, **aucune conversion
à huit entrées de file n'est acquise ou automatiquement autorisée**.

## Lots restant à traiter — chacun peut être clos séparément

### CD-00 — Contrat de machine à états et référence de parité

**Statut : à faire, préalable, lecture seule.**
Inventorier les transitions exactes `primary → fallback → apply`,
le saut de combo V93, les raisons `sites_yield / pairs_yield /
hub_site_yield / hub_hub_yield`, les champs de `resumeState`,
les états `air0310HubSnap`, C83 et les dépendances aux événements.
Définir le propriétaire de chaque champ, l'ordre d'exécution et
les bornes d'opcodes. Figurer les contrats de publications V141,
le `bestPlan`, les conditions d'arrêt et le déclencheur de
`_c76AcknowledgeAllLayers` / snapshot AC06 v2.

**Sortie attendue :** graphe d'états et matrice
« entrée → phase → curseur/snapshot → sortie »,
fixtures de trace déterministes sur le comportement du HEAD,
plus un diagnostic clair sur la possibilité de tâches internes
autonomes sans changer `_taskQueue`. Aucun patch comportemental.

### CD-01 — Isoler la préparation et la recherche de sites

**Statut : à faire après CD-00.**
Faire de `Prepare` et `FindSites` des étapes explicites avec
entrée/sortie, en préservant l'ordre des combos, les validations
C83, le balayage/reclassement, le `scanIndex`, `rankIndex`
et les reprises à budget épuisé. Ne pas refaire un scan de sites
après reprise si le contexte/snapshot historique ne l'exige pas ;
ne pas mettre en cache ce que V143 a montré devoir être revérifié.

**Sortie :** test de parité sites/ordre/curseur et de reprise
au milieu du premier et du dernier combo.

### CD-02 — Détacher la génération des paires neuves

**Statut : à faire après CD-01.**
Isoler `NewPairs` de la recherche de sites via un contrat de
snapshot temporaire, et préserver les indices `a/b`, la clé OD,
les filtres d'échec `abandoned`, l'ordre économique et les
exceptions V93/C83 déjà adoptées.

**Sortie :** mêmes projets produits (y compris doublons historiques
justifiés), ordre et décisions avec tranches coupées avant/après
chaque paire ; après Save/Load, abandon puis régénération du scan
comme historiquement, sans feindre une persistance des curseurs.

### CD-03 — Détacher la découverte des hubs

**Statut : à faire après CD-02.**
Isoler `DiscoverHubs` et ses interfaces `hubs/sites/hubIndex`
sans changer `air0310HubSnap`, C80, les limites de routes ou
la déduplication **AC04-B** par ancre. Ne pas intégrer AC04-A
rejetée ni forcer la conservation des anciens hubs façon V143.

**Sortie :** mêmes hubs, sites, slots C83, ordre et frontières
de réutilisation ; pas de nouvel acquis sur AC04-A.

### CD-04 — Détacher les projets hub-vers-site

**Statut : à faire après CD-03.**
Donner à `HubToSite` sa continuation dédiée `hubSiteI/J`
et `hubPhase`, en respectant le filtrage, la validité des sites,
la rentabilité et les sites distincts C83. Ne pas modifier les
formules C121 ou la priorité du portefeuille.

**Sortie :** invariants de parcours sans omission/double visite et
parité des projets retenus lors de suspensions arbitraires.

### CD-05 — Détacher hub-vers-hub, fin de combo et finalisation

**Statut : à faire après CD-04.**
Séparer `HubToHub` de `HubToSite` avec `hubHubI/J`,
préserver le calcul AC05 adopté, l'ordre strict `i<j`,
les exemptions V93, l'avancement du combo et le nettoyage des
snapshots entre combos. Distinguer `Finalize` du passage au
combo suivant **sans** réintroduire le maintien de curseur V143.

**Sortie :** mêmes candidats, meilleur plan, fermeture du dernier
combo et passage à `done` sur tous les cas dirigés.

### CD-06 — Extraire publication et acquittement de la génération

**Statut : à faire après CD-05.**
Isoler la transaction de publication `partialPending` /
`OpexAir0310PublishIncremental` (V141), le dernier
`_rebuildProjects` et la transition finale `apply`, tout
en conservant **la publication au passage suivant** après
épuisement du budget et la republication par nouveau lot.
En final, appliquer **AC06 v2** sans acquitter de révision plus
récente que la photographie initiale. Save/Load abandonne le
curseur transitoire et régénère selon les règles actuelles.

**Sortie :** préfixes et non-AIR inchangés, ordre de sélection,
exactement une finalisation, aucun acquittement tardif sur fixture
injectant un événement entre `refresh` et `apply`. Ne pas
réutiliser V142 ni le refresh intermédiaire V143 rejetés.

### CD-07 — Décider *séparément* d'une vraie autonomie dans la file

**Statut : décision conditionnelle, non autorisée par les audits AC.**
Après CD-00 à CD-06, comparer deux architectures :
(A) sous-tâches explicites **dans la même entrée** `catalog`,
préservant l'ordonnancement ; (B) plusieurs entrées
`_taskQueue`. Pour (B), établir d'abord une migration sûre des
indices persistés `_taskCursor`, des `dueCycle`, du bootstrap
index 0, de `OpexC121CatalogCanContinue`, du partage d'opcodes
et des workers. Sans preuve que ces règles demeurent inchangées,
**conserver (A)** : « tâches indépendantes » ne signifie pas
nécessairement « huit entrées de la file globale ».

**Sortie :** décision motivée, sans implémenter (B) par défaut.

## Qualifier les étapes et préserver les décisions

Chaque CD débute avec les tests source et fixtures existants,
une référence gelée du HEAD et un patch **structurel isolé** :
pas de changement de politique déguisé sous un déplacement.
Vérifier le parcours, les sorties, les curseurs et les sauvegardes
avant/après Load ; smoke Docker réel puis A/B apparié selon
`AGENTS.md` avec **profit annuel, valeur de compagnie et opcodes
globaux `LOOP_OPS`**, pas les seuls compteurs partiels H5.
Une étape n'hérite pas de la validation de la précédente :
si les résultats diffèrent, faire une autopsie causale et
rejeter ou corriger le lot concerné. Un seul banc à la fois,
au maximum 10 CPU/10 workers sur le PC local. Ne pas relancer
les expériences V141–V143, AC04-A ou les formules de score
RAIL déjà closes sans **nouvelle hypothèse distincte**.

## Reliquats annexes, sans bloquer CD-00 à CD-07

- **AC04-A : bug de hub saturé toujours présent.** L'anomalie est
  documentée, mais ses deux corrections ont dégradé les opcodes.
  Conserver en reliquat causal ; aucune variante v3 ni A/B
  automatique sans nouvelle explication vérifiable.
- **AC06 v2 : preuve moteur de la course tardive absente.**
  Le modèle et Save/Load sont testés ; une fixture moteur à
  événement forcé pourrait démontrer la correction réellement
  exercée, séparément d'une campagne économique.
- **AC07 : coût absolu résiduel de `pub.filter` inconnu** ;
  instrumentation ciblée seulement si elle aide CD-06.
- **AC08 : `_refreshAir` matériel à faible fréquence**,
  pas de refactoring/optimisation justifié actuellement.
- **Publication Git :** le commit `978d098` est local (un commit
  d'avance sur `origin/master` au 12/10). **Pas de push demandé**
  dans ce chantier de planification. Les deux worktrees de preuves
  restent à conserver jusqu'à décision d'archivage distincte.

Voir aussi [les audits AC-01 à AC-08](air_catalogue_microtasks_20261011.md),
[les qualifications](air_catalogue_validation_finale_20261011.md) et
[l'adoption AC06 v2](ac06_v2_adoption_20261012.md).
