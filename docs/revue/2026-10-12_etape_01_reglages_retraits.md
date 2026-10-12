# Revue 12/10 — étape 01 : réglages et retraits

[Plan](../revue_code_2026-10-12_plan.md) · Rapport attendu : `docs/revue/2026-10-12_rapport_01_reglages_retraits.md`

## Objet

Le 12/10 a ajouté, changé de défaut ou retiré une vingtaine de réglages. Vérifier que chaque
réglage est cohérent de bout en bout, et qu'aucun réglage retiré n'a laissé de lecteur.

## Périmètre

- `git diff 978d098^ master -- ai/OpexAI/info.nut ai/OpexAI/globals_pre.nut ai/OpexAI/settings.nut ai/OpexAI/persist.nut`
- Les mêmes fichiers sur `origin/v158-lazy-select` et `origin/v160-fleet-routes-index`
  (`git diff master...origin/<branche>`).
- Les tests qui affirment un défaut : `grep -l "_value" sweeps/test_v15*.py sweeps/test_v147*.py sweeps/test_ac0*.py`.

## Questions

1. **Ajouts.** Pour chaque réglage ajouté ou modifié : `AddSetting` dans `info.nut` (bornes, quatre
   `*_value` identiques, `flags`), globale initialisée dans `globals_pre.nut`, lecture dans
   `settings.nut` (forme `!= 0` pour un booléen, `>= 0` ou bornage pour un entier), au moins un
   lecteur dans le code. Défauts attendus au 12/10 : V147 (`v147_air_catalog_tasks`), V153
   (`rail_end_jump_connect`), V154 (`select_bisect_insert`), V156 (`incr_revalidate_index`) à 1 ;
   V155 (`air_fleet_c121_preguard`), V158 (`air_publish_lazy_select`), V160 (`air_fleet_routes_index`)
   à 0. Signaler toute description qui contredit le défaut réel.
2. **Retraits** (commits `5e6fe47`, `d508c46`, et les retraits C121/C122 du jour : réglages de
   cadence et de réalisation C121, réalisation moteur, priorité par régime C122, paramètres de
   classement AIR). Pour chaque nom retiré et sa globale : plus aucun `GetSetting`, plus aucun
   lecteur, plus aucun test qui les attend. Un `GetSetting` restant sur un nom retiré renvoie -1 :
   c'est **P0** s'il est lu avec `!= 0`.
3. **Fusions des branches.** Les conflits de `info.nut`, `globals_pre.nut` et `settings.nut` ont été
   résolus à la main le 12/10 (V158 `3d19c55`, V160 `9830fc6`) : vérifier que chaque bloc
   `AddSetting({ ... })` est bien fermé, qu'aucun réglage n'est dupliqué ni perdu.
4. **Persistance.** `persist.nut` a changé : un champ ajouté au jour (`selectionStale`, état des
   phases V147, instantanés AC06…) est-il sauvé, ou reconstruit sans risque au chargement ?
5. Lancer les tests qui affirment des défauts et dire lesquels échouent.

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
