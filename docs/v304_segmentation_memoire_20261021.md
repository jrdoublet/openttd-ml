# V304 — mesure et mémoire de segmentation, 21 octobre 2026

## Pré-enregistrement

Dépôt `/home/deploy/projects/wt-v304`, branche `v304`, base
`4eb307d0e51384952c14462f8974baca304b5929`, arbre initial propre.
Pas de changement de défaut, de push ou de banc GitHub. V303 secondaire.

Première étape : instrumentation seule sous `DECISION_LOG`, sur le moteur natif
V296 actif par défaut. Compter les expansions acceptées après le filtre closed,
les expansions de tuiles et de couples tuile/direction déjà vus dans un segment
antérieur, les segments, retours arrière et itérations totales par recherche.
Les doublons dépilés mais rejetés par le closed local ne sont pas des expansions.
Stockage plafonné à 50 000 tuiles et 50 000 états ; tout dépassement est signalé.
`native_segments` doit égaler `segments` pour une couverture complète.
Ces compteurs portent sur la recherche aller segmentée, pas sur la sonde inverse.

Diagnostic initial `v304_before_3x10_20261021` : référence
`OpexAI[decision_log=1]`, graines 42/7/100, 10 ans, une répétition,
carte 256×256, script-debug, CPU 3 / RAM 2g / swap 2g / workers 3,
réseau host, cache `openttd-lab-home`. Image locale
`sha256:a0e0a0727f5003532764eeaeee6b83e9ab96a7470df3c76208c6446d10b88c8c`.
Docker contexte `default`, aucun conteneur OpenTTD actif au contrôle initial.
Une référence seule : aucune qualification économique ni verdict A/B.
Budget : trois duels pour la mesure initiale, puis six duels pour le mécanisme
0 contre 1 si un mécanisme cohérent est livré. Aucun lancement de porte A/B.

## Point de correction à résoudre avant l'élagage

Le nouveau segment repart de `[front, previous]` avec g local réinitialisé.
`OpexSegmentIgnoredTiles` ajoute le préfixe aux interdictions ; les contextes de
recherche changent donc entre les segments. Les coûts de virage utilisent aussi
plusieurs ancêtres. Enfin, supprimer un nœud parce qu'il avait été développé
avant la destruction de sa frontière ne conserve pas ses successeurs.
Une table globale tuile/direction → g seule ne constitue donc pas une relation
de dominance sûre. La mesure précède le choix d'une reprise qui conserve le
travail exploitable sans supprimer les continuations nécessaires.

## Mesure initiale

Campagne terminée : 3/3 parties complètes et saines jusqu'au 01/12/1979,
aucune erreur Squirrel OpexAI, aucune saturation de la sonde, couverture native
complète. Bundle `35156850f41b9e7541291cee160c3813afedf80043fc864bd81fb2844830d6fa`.
95 recherches, dont 27 à plusieurs segments. `OK` signifie tracé trouvé,
pas nécessairement ligne construite. Les autres issues sont ici des `ABND`.

| Distance | Issue | n | Itérations moyennes | Segments moyens | Réexpansions tuiles (total) | Réexpansions états (total) |
|---|---|---:|---:|---:|---:|---:|
| <100 | OK | 29 | 402,2 | 1,07 | 470 | 303 |
| <100 | ABND | 4 | 5 000 | 3,25 | 6 646 | 5 055 |
| 100–159 | OK | 19 | 473,9 | 1,11 | 1 518 | 1 301 |
| 100–159 | ABND | 4 | 5 000 | 3,00 | 7 449 | 5 612 |
| ≥160 | OK | 26 | 791,2 | 1,12 | 2 068 | 1 356 |
| ≥160 | ABND | 13 | 5 000 | 3,23 | 23 879 | 17 508 |

Extraction : `sweeps/diag_v304_segments.py`, à partir des journaux de
`results/v304_before_3x10_20261021_engine/`. Les données absentes ne sont pas
converties en zéro. Cette première campagne précède le mécanisme et ne constitue
pas son bras témoin : celui-ci sera remesuré sur le même arbre que la variante.

## Mécanisme expérimental et écart au schéma initial

`v304_segment_memory=1` (défaut 0 aux quatre niveaux) conserve une table g,
les tableaux d'ancêtres et les files ouvertes AIList du moteur natif V296.
Le premier segment conserve le filtre closed historique. À la coupure, le
meilleur nœud de frontière amorce une branche dédiée ; les autres nœuds sont
conservés dans une file suspendue. Une branche épuisée restaure cette file,
dans la limite historique de quatre retours arrière. Le coût g reste relatif
aux sources originales ; les améliorations de g rouvrent un état et g ≥ connu
est élagué. Les changements de poids recalculent les priorités des files vivantes.

Ceci n'est pas le simple transfert d'une table dans des A* réinitialisés : cette
version change l'ordonnancement des frontières. Les sauts locaux de structures
du segmenter historique sont remplacés par les successeurs pont/tunnel du moteur
natif. Les sources ne sont pas déplacées, les chemins gardent leur ascendance
complète. Il reste une recherche segmentée à branches suspendues, distincte de
V294b qui utilise une seule file sans focalisation de branche.

Limites explicites : moteur `v296_astar_native=1` requis (autres modes : chemin
historique), maximum 50 000 états g et 50 000 nœuds dans les cinq tableaux natifs.
Une saturation donne ABND avec `capped=1`, jamais une suppression silencieuse.
Les files contiennent des identifiants des mêmes nœuds, pas des copies d'ancêtres.
La mémoire est transitoire, libérée avec la recherche ; la sauvegarde ne sérialise
déjà pas `_railSearch` et la réconciliation l'abandonne explicitement.
La dominance tuile/direction hérite de l'approximation d'état du moteur existant ;
elle ne prouve pas l'optimalité avec les contraintes dépendant des ancêtres.
La non-dégradation des tracés reste à mesurer, pas à supposer.

Pré-enregistrement de validation : contrats, suite complète, délimiteurs, puis
smoke causal `v304_compile_1x1_20261021` (42 × 1 an, deux duels), puis diagnostic
`v304_mech_3x10_20261021` (42/7/100 × 10 ans, six duels), mêmes limites Docker.
Bras `OpexAI[decision_log=1]` et `OpexAI[v304_segment_memory=1,decision_log=1]`,
policy-id `v304`, règle explicite `gain_short`, métrique `profit_year`, seuil 4 %,
garde valeur 5 %, carte 8, répétition 1, script-debug. Trois graines restent un
diagnostic, même si les moyennes sont favorables. Budget supplémentaire du smoke
de compilation : deux duels d'un an. Pas de porte A/B ni d'adoption.

Le second arbre mesure aussi les opcodes par recherche et recalcule le coût de
la totalité des tuiles trouvées via la fonction de coût commune (pas le seul g
du dernier segment). `V304_PATH` conserve les tuiles pour la comparaison exacte.

## Références vérifiées dans le code livré

- Interdictions dépendant du préfixe : `ai/OpexAI/builder_rail.nut:1108`.
- Journal terminal : `ai/OpexAI/builder_rail.nut:1253`.
- Création et activation optionnelle : `ai/OpexAI/builder_rail.nut:1380`.
- Comptage des réexpansions : `ai/OpexAI/builder_rail.nut:1456`.
- Dispatcher historique : `ai/OpexAI/builder_rail.nut:1478`.
- Coût du tracé complet : `ai/OpexAI/builder_rail.nut:1702`.
- Repondération des frontières : `ai/OpexAI/builder_rail.nut:1716`.
- Contrôleur des branches conservées : `ai/OpexAI/builder_rail.nut:1737`.
- Dominance g : `ai/OpexAI/pathfinder_v90/v296.nut:237`.
- Plafond de nœuds : `ai/OpexAI/pathfinder_v90/v296.nut:492`.
- Réglage : `ai/OpexAI/info.nut:772`, lecture `ai/OpexAI/settings.nut:204`.
- Réconciliation des recherches transitoires : `ai/OpexAI/persist.nut:1032`.

## Validation technique

Suite complète finale : **2 289 tests**, OK (3 ignorés, 2 échecs attendus).
Neuf contrats V304, dont lecture/agrégation des journaux et comparaison des
premières tentatives sans sélectionner la meilleure répétition. Compteurs
AddSetting 89 → 90 dans les quatre tests demandés. Le script de délimiteurs
fourni ne produit aucune ligne. `git diff --check` passe.

Smoke `v304_compile_1x1_20261021` : **2/2 parties saines**, zéro erreur OpexAI,
verdict brut `diagnostic_only`. Trois recherches segmentées par bras, toutes
dans un seul segment : itérations 29/47/90 et coûts 5 751/3 776/14 602 identiques.
Ce smoke compile le chemin optionnel mais ne démontre pas le transfert à la
coupure. Écart économique −38 874 £/an sur une graine : diagnostic uniquement.

La campagne 3×10 utilise le bundle
`b1cc6b7d031bac5463e13d3e70b18b0eaa2e5d85022961d8c3101744b6969fdf`, manifeste
`c2045f41607a5b6a05239ec8d0776d7900321ecef193406c96e2280e3d1bb6a2`.
Les 81 fichiers Squirrel du worktree ont été comparés octet par octet avec ce
bundle : aucun écart. Mémoire du conteneur échantillonnée pendant le banc :
483,5 MiB sur 2 GiB (mesure globale, pas la mémoire du cache ni un pic certifié).

Résultats du mécanisme et décision à compléter après exécution.
