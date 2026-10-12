# Revue 12/10 — étape 02 : catalogue AIR et V147

[Plan](../revue_code_2026-10-12_plan.md) · Rapport attendu : `docs/revue/2026-10-12_rapport_02_catalogue_air_v147.md`

## Objet

Le catalogue AIR a été découpé (CD01–CD06), complété (AC04-B, AC05, AC06) puis réparti en trois
entrées autonomes de la file de tâches (V147, `air_cat_scan/publish/apply`, défaut 1). Vérifier
que l'état reste cohérent quand les phases sont interrompues, réordonnées ou relancées.

## Périmètre (fonctions, pas fichiers entiers)

- `scheduler_tasks.nut` : `OpexV147ExtendQueue` (~90), `OpexV147PhaseTask` (~133),
  `OpexAI::_dispatchAirCatalogPhase` (~145), `OpexC78PublishPartialAir` (~164),
  `OpexC78ContinueCatalogAirRebuild` (~255), `OpexV147ArmPhases`, `OpexV147CurrentPhase`, `OpexC78ApplyAir`.
- `air_planning.nut` : `OpexAC04ValidateHubsAtUsage` (~1071), `OpexAC04ExtraSiteAlreadyKnown`,
  `OpexAirPlansStepNewPairs` (~2395), `OpexAirPlansHubDiscoveryPhase` (~2464),
  `OpexAirPlansHubToSitePhase`, `OpexAirPlansStepFindSites`, `OpexAirPlansStepPrepare`,
  `OpexAirPlansCompleteCombo`.
- `orchestrator.nut` : `OpexAC06SnapshotLayer` (~1198), `OpexAC06CaptureRevisionNumbers`,
  `OpexAC06AcknowledgeSnapshot`.
- `scheduler.nut`, `main.nut` : les seules lignes modifiées le 12/10 (`git diff 978d098^ master`).
- Tests : `sweeps/test_v147_air_catalog_tasks.py`, `sweeps/test_ac07_air_partial_publish.py`, et
  ceux trouvés par `grep -l "AC04\|AC06\|V147" sweeps/test_*.py`.

## Questions

1. **File de tâches.** Une phase peut-elle être insérée deux fois dans `_taskQueue`, ou jamais
   réarmée ? Que se passe-t-il si un rafraîchissement complet du catalogue (nouvel avion, nouvel
   aéroport, régénération) arrive entre `scan` et `apply` ?
2. **Publication partielle.** `OpexC78PublishPartialAir` et l'application finale peuvent-elles
   publier deux fois la même paire, ou en perdre une ? Une paire publiée partiellement puis
   invalidée par AC04 est-elle retirée ?
3. **AC06.** Les numéros de révision des instantanés sont-ils monotones ? Un accusé de réception
   peut-il viser un instantané déjà remplacé ?
4. **Sauvegarde.** Une partie sauvée au milieu d'une phase se recharge-t-elle sans état incohérent
   (phase courante, curseurs, instantanés) ?
5. **Équivalence annoncée.** V147 a été qualifié comme ne changeant que l'ordonnancement : relever
   toute différence de décision entre le chemin V147=1 et le chemin historique V147=0.

## Règles communes

- **Revue seulement.** Aucun correctif de code, aucun banc, aucune partie OpenTTD, aucun Docker,
  aucun changement de défaut, aucun agent délégué. Le seul fichier écrit est le rapport.
- **Préparer :** `git checkout master && git pull --ff-only && git fetch origin`. Noter en tête du
  rapport le SHA de master revu. Pour une branche : `git diff master...origin/<branche> -- ai/OpexAI`,
  `git show origin/<branche>:ai/OpexAI/<fichier>`, ou un worktree jetable
  (`git worktree add ../revue-<branche> origin/<branche>`, retiré en fin d'étape avec
  `git worktree remove ../revue-<branche>`).
- **Lire d'abord** `ai/OpexAI/CLAUDE.md`. Ne pas lire `docs/taches.md` en entier (chercher la
  ligne utile), ni `results/`, ni les journaux de partie.
- **Plafond de lecture : ~1 500 lignes de source.** Lire les fonctions utiles en entier et leurs
  appelants directs, pas les fichiers entiers. Si le périmètre déborde, couvrir l'essentiel et
  lister ce qui n'a pas été lu.
- **Vérifier à la main**, pas par grep seul. Vérifier le défaut d'un réglage avant de parler de
  code mort. Pièges connus : mots réservés Squirrel `clone`, `base`, `parent` ; une closure ne
  capture pas les locales ; `const` n'accepte qu'un littéral ; `<-` crée un champ, `=` sur un champ
  absent lève une erreur ; `line.stationA/B` sont des **tuiles**, pas des StationID ;
  `AIController.GetSetting` d'un nom inconnu renvoie **-1**, que `!= 0` transforme en vrai.
- **Tests :** `PYTHONPATH=sweeps python3 -m unittest sweeps/<test>.py` (ajouter le site-packages
  utilisateur au PYTHONPATH si un module manque). Les lancer et en donner le résultat. Ils ne
  prouvent pas que le Squirrel compile.
- **Constat :** ancre `fichier:ligne` ; gravité **P0** (plantage, ou décision fausse au défaut),
  **P1** (décision fausse sous un réglage en cours de banc, ou équivalence annoncée fausse),
  **P2** (coût d'opcodes, robustesse), **P3** (lisibilité, dette) ; scénario concret de défaillance ;
  statut **démontré** ou **hypothèse**. Pas plus de 5 lignes de code citées par constat.
- **Rapport :** `docs/revue/2026-10-12_rapport_NN_<sujet>.md` (NN et sujet de l'étape), avec : SHA
  revu, couverture (fonctions lues), constats, tests lancés, limites et non-lus. Court.
- **Commit :** ajouter le seul rapport, message `docs(revue): 12/10 étape NN — <sujet>`, puis
  `git push origin master`. Si le push est rejeté : `git pull --rebase` une fois, puis repousser.
  En cas de nouvel échec, laisser le fichier et le signaler.
