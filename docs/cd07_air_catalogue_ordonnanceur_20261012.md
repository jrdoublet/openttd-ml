# CD-07 — décision sur l'autonomie du catalogue AIR

**Décision architecturale du 12 octobre 2026 : conserver une seule entrée
`catalog` à l'index 0 de `_taskQueue`.** Le découpage à poursuivre
est **interne** à cette entrée : sous-étapes de génération et transactions
de publication explicites, chacune testable, sans créer de nouvelles
entrées globales. Cette décision clôt la *question d'architecture*
CD-07 ; elle ne constitue ni une qualification économique de CD01–06
ni un changement du code de production.

## Pourquoi une file globale par phase serait un changement de politique

- `main.nut` construit `_taskQueue` avec `catalog` en première
  position. L'indice numérique `_taskCursor` est conservé par les
  sauvegardes complètes, tandis que les `dueCycle` sont restaurés par
  nom. Ajouter ou intercaler des tâches déplacerait donc les indices
  historiques et exigerait une migration Save/Load explicite.
- `OpexC78RequeueInitialCatalogSlice` ramène délibérément le curseur
  global à **0** pendant le bootstrap sans portefeuille. Les sous-phases
  AIR ne sont pas de simples tâches ordinaires à faire tourner au
  même niveau que report, air_fleet, projects et rail.
- La continuation C121 dans le *même tick* cherche explicitement
  une tâche appelée `catalog` possédant `c78AirRebuild`, et
  peut reprendre sous garde de budget/opcodes et d'absence de
  worker/rail. Plusieurs tâches perturberaient les reprises et
  la fenêtre des événements, même si les corps Squirrel étaient
  copiés mot pour mot.
- La publication V141, la transition `primary → fallback → apply`
  et l'ACK AC06 v2 doivent observer un seul curseur et conserver
  l'ordre des décisions. V142/V143 ont déjà montré qu'un changement
  de cadence/placement peut être nuisible économiquement.

## Architecture retenue

La tâche `catalog` reste l'ordonnanceur unique, propriétaire de
`task.c78AirRebuild`, de `s.cursor`, du budget d'une tranche et
de la transition publication/apply. Les sous-étapes
`Prepare`, `FindSites`, `NewPairs`, `DiscoverHubs`,
`HubToSite`, `HubToHub`, `CompleteCombo`, `Finalize`
et les transactions `PublishPartial`/`Apply` ont des interfaces
isolables, **sans nouveau `dueCycle` ni `_taskCursor`**.
Une reprise interrompue doit continuer avec les checkpoints
actuels ; un Save/Load abandonne la transaction transitoire et
la régénère selon l'historique.

## Statut de validation

- Le [contrat CD00](cd00_air_catalogue_contract_20261012.md)
  et son étalon de transitions documentent les invariants.
- Les lots CD01–CD06 doivent individuellement démontrer
  compilation Squirrel, parité des états/snapshots, santé,
  non-érosion économique et budget/opcodes. **Rien n'est
  autorisé à contourner ces portes** au prétexte que CD07
  choisit un seul ordonnanceur.
- Toute future conversion à plusieurs entrées de `_taskQueue`
  constituerait une **nouvelle expérimentation comportementale**
  avec migration de sauvegarde et A/B propres, explicitement
  hors du découpage demandé ici.

**Verdict : architecture A retenue, B non justifiée et non implémentée.**

**État postérieur au plan (12/10) :** les sous-étapes CD01–CD06 de
l'architecture A ont depuis été intégrées dans `master` et qualifiées
par C40×4/B20×10, tests et Save/Load moteur. Voir
[`cd_air_catalogue_validation_20261012.md`](cd_air_catalogue_validation_20261012.md).
Ce résultat ne transforme pas l'architecture B en option validée.
