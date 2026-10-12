# Revue 12/10 — étape 07 : synthèse

[Plan](../revue_code_2026-10-12_plan.md) · Rapport attendu : `docs/revue_code_2026-10-12.md`

## Objet

Consolider les rapports des étapes 01 à 06, classer les constats et préparer la suite. **Ne rien
corriger.**

## Entrées

`docs/revue/2026-10-12_rapport_0[1-6]_*.md`. S'il en manque, le dire en tête et travailler avec
ceux qui existent.

## À faire

1. Dédupliquer les constats ; quand deux étapes se contredisent, relire le code en cause
   (≤ 300 lignes au total) et trancher, ou laisser l'hypothèse ouverte.
2. Classer par gravité (P0 → P3), puis par coût de correction. Pour chaque P0 et P1 : correctif
   proposé, réglage derrière lequel le mettre (défaut 0, rollback), et validation selon AGENTS.md
   §4 — une optimisation d'opcodes demande un gain d'opcodes et un 20×10 neutre ; un changement de
   comportement demande la porte A (40×3 `gain_short`) puis la porte B (20×10 `non_erosion`).
3. Signaler tout constat qui touche une branche en attente de banc (V158, V160) : il doit être
   connu **avant** que son 20×10 soit lu.
4. Écrire `docs/revue_code_2026-10-12.md` : tableau des constats (id, gravité, `fichier:ligne`,
   résumé, statut, étape d'origine), puis les correctifs proposés.
5. Ajouter **une** ligne dans `docs/taches.md`, section « État courant », pointant vers la
   synthèse et listant les P0/P1. Ne rien modifier d'autre dans `taches.md`.
6. Commit de la synthèse et de `docs/taches.md` (exception à la règle « seul rapport »), message
   `docs(revue): 12/10 synthèse`, push sur master (règles de rejet ci-dessous).

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
