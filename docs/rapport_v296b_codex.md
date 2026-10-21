# V296b — A* rail natif

21 octobre 2026. Worktree `/home/deploy/projects/wt-v296b`, branche `v296b`,
base `40a4d8fa`. Réglage livré **à 0 aux quatre difficultés**. Aucun banc,
conteneur Docker ni push exécuté. Aucun résultat économique ou gain d'opcodes mesuré.

Ce rapport est conservé dans le worktree : le chemin demandé
`/home/deploy/.claude/jobs/e230de46/tmp/rapport_v296b_codex.md` est extérieur au
périmètre que la même demande interdit de modifier.

## Implémentation

- `ai/OpexAI/pathfinder_v90/v296.nut` : classe dérivée de V129, AIList triée par
  valeur croissante, identifiants entiers croissants départageant les ex æquo.
  Tuile, direction, coût, parent et Bloom sont cinq tableaux parallèles.
  Les objets `OpexAyStarV129.Path` sont matérialisés pour le résultat et la frontière.
  Les sources `[lead, previous]` sont insérées à leur coût g comme dans V129 ;
  les sources Path importent toute leur parenté et reconstruisent le Bloom.
- La boucle fusionne génération, coût et heuristique sans callback de recherche
  ni tableau de voisins. Les helpers de terrain, de pente et de direction sont
  hérités, avec leurs caches. Toutes les expressions de coût V129 sont conservées,
  y compris les arrondis entiers, V214, V294d, `_guideTiles`, `_outwardSide`,
  les surcoûts longs des ouvrages et l'élagage sur g. Les doublons de voisins
  à la sortie des ouvrages sont conservés. Les buts distincts sont dédoublonnés
  pour l'heuristique seulement ; un but distinct bénéficie d'un chemin direct.
- `info.nut`, `settings.nut`, `globals_pre.nut`, `main.nut` : déclaration,
  chargement et ordre des fichiers pour `v296_astar_native` (0/1/2).
- `pathfinder_v90/v129.nut` : **seule la fabrique change**, avec deux branches
  d'activation. À 0 elle rend toujours V129 ; son A*, son tas et ses coûts
  restent inchangés.
- `builder_rail.nut` : frontière native via `Begin/Next/IsEnd`, dédoublonnage
  tuile/direction, matérialisation des K meilleures alternatives distinctes.
  Aucun retrait dans l'AIList lors de cette lecture. La fabrique commune couvre
  recherche continue, segmentation, sonde inverse V294f, réparation V131 et reprise.
- Le mode 2 hérite de V296, copie tous les paramètres de coût vers une instance
  V129 distincte et exécute les deux sous AITestMode. Mesures par appel avec
  `OpexOpsMeasureBegin/End`, cumulées par recherche. Journal `V296_CHECK` sous
  `DECISION_LOG` : itérations, coûts, opcodes, chemins trouvés, état de complétude,
  poids, V295 de référence et égalité des coûts. `-1` signifie coût indisponible.
  V129 conserve le réglage V295 choisi : utiliser `v295_astar_fast=1` pour mesurer
  contre V129 rapide. V296 emploie toujours le Bloom et les buts dédoublonnés.
- Si V129 termine d'abord, son résultat est conservé. Si V296 termine d'abord,
  le contrôleur achève V129 avant de rendre le résultat V296. `LastConsumed`
  reste le nombre d'itérations V296 ; le travail supplémentaire de contrôle
  peut donc dépasser le budget de tranche apparent. Chaque tranche est journalisée
  pour que les sondes bornées et segments abandonnés ne disparaissent pas du diagnostic.
- Aucun précalcul Valuate : pas de mesure disponible pour en justifier le coût.

## Sauvegarde

Audit de `persist.nut` : `Save()` conserve `railSearchPending`, pas `_railSearch`.
`OpexSaveActiveWorker` projette les travailleurs `rail_search` et `rail_stock`
en état vide. La réconciliation abandonne la recherche vivante au chargement.
`OpexSaveRailExpansion` est une projection explicite sans pathfinder.
**Aucun AIList ni objet V296 ajouté au format de sauvegarde.** Aucun changement
de persistance n'a été nécessaire ; aucun roundtrip en jeu exécuté.

## Validation exécutée

- 17 contrats ajoutés dans `sweeps/test_v296b_astar_native.py` : réglage,
  fabrique, chargement, interface, AIList, boucle sans callbacks/Path,
  parenté/Bloom, sources importées, frontière, diagnostic et persistance.
  Un contrat compare **tout le bloc de coût** à celui de V129, après les seules
  substitutions champs → locaux et parenté → indices. Un autre vérifie l'ordre
  des longueurs de pont puis tunnel, y compris quand aucune longueur de pont
  n'est autorisée. Ce sont des contrôles statiques, pas une exécution de Squirrel.
- Compteurs AddSetting portés de 85 à 86 : tests V246, V251, V259 et V284.
- Suite demandée : `python3 -X utf8 -m unittest discover -s sweeps -p 'test_*.py'`
  : **2 249 tests, OK, 3 ignorés, 3 échecs attendus**, 23,538 secondes.
  Le premier passage des 2 232 anciens tests échouait parce qu'AAAHogEx était
  absent. Copie locale de `/home/deploy/projects/wt-v295/ai/AAAHogEx-115` vers
  `ai/AAAHogEx-115`, ignorée par Git, sans modification de la source ni copie
  de son code dans OpexAI ; second passage complet vert.
- `delim.py` attend un **répertoire**, pas un fichier : exécuté avec `ai/OpexAI`,
  aucune erreur de délimiteur. `undecl.py ai/OpexAI` ne signale que
  `AICONFIG_BOOLEAN` et `CONFIG_BOOLEAN`, constantes API déjà utilisées dans
  `info.nut`, aucune nouvelle globale non déclarée.
- `git diff --check` sans erreur. Aucun compilateur Squirrel disponible ni
  smoke autorisé : **compilation/exécution moteur non validées**.

## Estimation d'opcodes, non mesurée

Comptage indicatif à la lecture : un chargement/comparaison/arithmetic/jump vaut
approximativement une instruction VM ; appel natif avec préparation des arguments
environ 4–8. Sans bytecode compilé, ce ne sont pas des comptes exacts. Les fréquences
dynamiques viennent du profil fourni ; les ex æquo peuvent les modifier.

| Poste | Profil fourni / itération | V296 plausible / itération | Lecture du code |
|---|---:|---:|---|
| Coût | 384 | 300–350 | Appel callback supprimé, constantes locales ; mêmes requêtes/cache/pente, aucune suppression de pénalité |
| Dépilement | 287 | 15–25 | Deux appels natifs, affectation de l'identifiant, compteur ; plus de boucle de descente |
| Voisins | 214 | 200–260 | Plus de tableaux imbriqués ni callback ; le sélecteur de candidats ajoute des branches |
| Parenté | 209 | 150–210 | Deux lectures indexées, comparaison et saut par ancêtre ; Bloom évite certains scans mais peut saturer |
| Insertion | 197 | 95–135 | Cinq append, calcul du Bloom, identifiant et AddItem : environ 50–70 instructions par voisin, sans remontée de tas |
| Heuristique | 128 | 70–110 | Cache conservé, coordonnées locales, pas de boucle avec un seul but distinct |
| Fermé/but/autres | ~30 | 40–70 | Gestion des indices et constantes amorties par tranche ; coût plus sensible avec FindPath(1) |
| Non ventilé dans les chiffres fournis | 56 | 56 conservés | Les postes cités totalisent 1 449 et non 1 505 |
| **Total** | **1 505** | **926–1 216** | **Hypothèse : environ −20 à −40 %**, point central voisin de 1 050 |

Le gain attendu est surtout celui du tas natif. Il ne faut pas ajouter à nouveau
un gain V295 intégral : ce filtre aide surtout les longues recherches et sature
sur les longues parentés. Coût de matérialisation final et coût initial non inclus
dans cette estimation par itération. Les cinq tableaux retiennent tous les nœuds
créés jusqu'à la fin de la recherche, puis sont libérés : surveiller la mémoire.

## Vérifications nécessaires au banc ultérieur

1. Compilation et exécution des trois modes ; mêmes paramètres de coût, mêmes
   sources, buts, exclusions et carte. Tester plusieurs appels FindPath(n),
   absence de chemin, frontière puis reprise, ouvrages et plusieurs buts.
2. En mode 2 avec V295=1 et poids 100 : exiger l'égalité des coûts lorsque les
   deux chemins existent ; diagnostiquer tout écart avant validation. À poids
   supérieur, rapporter les écarts sans imposer le même chemin ni les mêmes
   itérations. Les journaux partiels ne sont pas des comparaisons finales.
3. Le poids 100 n'est pas à lui seul une preuve générale d'optimalité : le guide
   peut réduire les coûts sous l'heuristique et la clé du fermé ne contient pas
   toute la parenté dont dépendent les virages. Ce sont des propriétés héritées
   de V129 ; ne pas modifier ces politiques dans ce chantier pour masquer un écart.
4. Mesurer séparément opcodes/itération, coût total et nombre d'itérations,
   initialisation, matérialisation et frontière. Le mode 2 ajoute du travail
   susceptible de laisser évoluer le monde entre les deux explorations : préférer
   des fixtures stables pour les comparaisons exactes et un diagnostic sans journal
   pour l'effet global. Vérifier la mémoire sur les longues recherches.
5. Tester Save/Load avec recherche active. Le contrat reste abandon/reconstruction,
   jamais sérialisation de l'AIList. Aucun passage par défaut sur la seule base
   des tests Python ou de cette estimation.
