# Revue 12/10 — étape 04 : revalidation incrémentale indexée (V156)

[Plan](../revue_code_2026-10-12_plan.md) · Rapport attendu : `docs/revue/2026-10-12_rapport_04_revalidation_v156.md`

## Objet

V156 (`incr_revalidate_index`, défaut 1 depuis le 12/10) remplace, dans `select.incremental`,
les parcours O(lignes) de `OpexCandidateStillValid` par des index construits une fois par appel :
paires bâties, index losange d'`OpexOriginServed` (avec et sans route), cache de validité des
sites air. Elle est annoncée strictement équivalente. Le mode 2 (les deux chemins, l'historique
fait foi, écarts journalisés) a trouvé **66 écarts air** (cause : cache mensuel AIR0310, corrigé
par `4b78b41`, cache limité à l'appel), puis **26 écarts résiduels sur 39 471** revalidations, tous
air, tous `hist=0 idx=1` (l'index dit valide, l'historique dit invalide), graine 1234, juin 1972.
Hypothèse non vérifiée : un site devient inconstructible pendant l'appel et le cache garde la
première réponse.

## Périmètre

- `projects_generation.nut` : `OpexIncrementalCandidateStillValid` (~505),
  `OpexIncrRevalidateIndexContext` (~514), `OpexCandidateStillValidIndexed` (~627),
  `OpexFilterAirAlternativesStillValid` (~773), le chemin historique `OpexCandidateStillValid`, et
  l'appelant `select.incremental`.
- `task_air.nut` : `OpexAirSiteStillBuildableIndexed` (~638), `OpexAirBatchPlanStillLiveIndexed`
  (~652), `OpexAirBatchHubHasCapacityIndexed`, `OpexAirTownServedIndexed`, et leurs pendants
  historiques (`OpexAirBatchSiteStillBuildable`, `OpexAirSiteStillBuildable`).
- Tests : `sweeps/test_v156_origin_index.py`.

## Questions

1. **Prédicat par prédicat**, comparer l'indexé à l'historique : doublon exact, `OpexOriginServed`
   rail, parcours route, sites air, hubs, villes servies. Relever tout cas où ils divergent, y
   compris l'ordre d'évaluation et les courts-circuits.
2. **Les 26 écarts.** Chercher une cause dans le code, pas seulement dans le temps : la clé
   `(R|N)|airport.type|plane.planeType|site.anchor` omet-elle un paramètre que l'historique lit
   (ville, plafond de gares, bruit, note de la ville, argent, emprise, `reuse`) ? Deux candidats
   différents peuvent-ils partager une clé et recevoir la réponse de l'autre ? Le sens unique
   `hist=0 idx=1` est-il compatible avec l'hypothèse du site qui devient inconstructible ?
   Conclure par une cause démontrée, ou par la liste des hypothèses classées.
3. **Code mort.** `OpexIncrRevalidateIndexContext` construit encore `ctx.airValidityState` via
   `OpexAir0310SiteValidityBegin` (~531) alors que la validation de site indexée ne le lit plus :
   confirmer, et vérifier qu'aucun effet de bord de cet appel n'est nécessaire (remise à zéro de
   l'état mensuel).
4. **Coût.** Les index sont-ils bien construits une seule fois par appel, et paresseusement ?

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
