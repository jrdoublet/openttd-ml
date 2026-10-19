# PO-01 — instrumentation et dépendances (19 octobre 2026)

Analyse du code de la branche `po01`, base `535b5bd`. Les mesures 5–12 M et
72 % viennent du diagnostic du 12/10, pas d’une nouvelle mesure. Aucune partie
n’est lancée pour cette mission. PO-02 reste distinct, sans expiration ajoutée.

## Déclenchement et invalidation

`orchestrator.nut::_dispatchReactiveIntention` consomme l’intention coalescée
`regen`. `_c80ModeRegenModes` rend `null` si les révisions C76 ou leurs
acquittements manquent, ou si `towns`, `lines`, `engines.air` dépassent
l’acquittement. Sans portefeuille, le dispatch prend aussi le chemin complet.
Les industries et moteurs terrestres/eau seuls donnent une liste C80.

| Couche | Générateurs concernés selon `_c76GetModeDeps` | Précision |
|---|---|---|
| towns | AIR, rail, route, eau | rail/route regroupent pax et fret ; l’acceptation urbaine du fret lit aussi les villes |
| lines | AIR, rail, route, eau, flotte | exclusions des origines, gares, dessertes et opportunités de flotte |
| engines.air | AIR, flotte | aucune dépendance rail/route/eau ; le commentaire C80 « tous les modes » est trop large |
| industries | rail, route | l’eau ne transporte ici que des voyageurs |
| engines.rail/road/water | mode correspondant et flotte | flotte C76 conservatrice ; les opportunités actuelles sont aériennes |

Les sous-modes C76 sont une matrice déclarative ; les unités réellement
régénérables par `OpexRegenerateModeProjects` sont `rail/road/air/water`.
La flotte s’injecte via `OpexInjectFleetProjects`, elle ne passe pas par ce générateur.
`ET_TOWN_FOUNDED` et `ET_ENGINE_AVAILABLE` passent par `_markDirty`, qui
incrémente les révisions. Attention à l’audit du 12/10 : dans cette base,
`_markPairAbandoned` incrémente `lines` avec `false`, donc sans enfiler lui-même
une intention ; cette révision peut être coalescée avec une intention ultérieure.

## Sonde livrée

`probes=8` (groupe opcodes/catalogue), `probes=4` (journal), ou tout groupe
activant `DECISION_LOG` : `PO01_REACTIVE cause=... modes=...` décrit toutes
les couches en retard et leur union de modes, sans choisir artificiellement
une cause unique. `PO01_COST phase=layer unit=... ops=...` mesure les sept
rafraîchissements du catalogue ; `phase=mode` mesure rail, route, AIR, eau et
l’assemblage/sélection/flotte/subventions. Les intervalles sont disjoints dans
chaque famille, mais les niveaux imbriqués ne doivent pas être additionnés.
Le coût des lignes est surtout porté par les générateurs : il n’existe pas de
rafraîchissement de catalogue `lines` à chronométrer séparément. Une couche qui
invalide plusieurs modes n’a pas de coût causal exclusif : aucune division
arbitraire des opcodes n’est faite entre causes simultanées.

Hors sonde : aucune mesure, allocation de diagnostic ou émission nouvelle.
Les gardes de branche ont néanmoins un coût VM ; « coût nul » désigne ici
l’absence de travail de sonde, pas une identité opcode bit à bit.

## Références vérifiées (code livré, chemins relatifs à `ai/OpexAI/`)

| Chemin | Point vérifié |
|---|---|
| `orchestrator.nut:595` | dispatch réactif, branche OFF historique conservée |
| `orchestrator.nut:1041` | incréments de couches et intention coalescée |
| `orchestrator.nut:1080` | matrice `_c76GetModeDeps` |
| `orchestrator.nut:1292` | conditions exactes du retour `null` C80 |
| `orchestrator.nut:1214` | reconstruction complète et mesure flotte |
| `events.nut:40` | passage événements → révisions C76 |
| `event_handlers.nut:414` et `event_handlers.nut:440` | fondation de ville / disponibilité moteur |
| `lines.nut:277` | abandon : révision `lines`, notification `false` |
| `catalog.nut:987` | intervalles par couche du refresh complet |
| `projects.nut:118` | drapeaux réellement exécutés `PO01_EXEC`, coût des modes et assemblage |
| `po01_reactive.nut:2` | diagnostic par union des dépendances |
| `projects_generation.nut:120` | remplacement d’un seul mode, conservation des autres candidats et des projets spéciaux |

Les numéros sont ceux de la livraison PO-01, pas ceux de l’ancien audit du 12/10.

## Prototype OFF livré

`info.nut:16`, `settings.nut:59` : `po01_reactive_split=0`, booléen,
quatre difficultés à 0. **80 AddSetting**, plafond courant **100** : aucun
relèvement nécessaire (`sweeps/test_v246_fixed_policies.py:27` et
`sweeps/test_v251_inventory.py:46`). Le chemin à 0 conserve les appels complets
et C80 existants ; les seules mesures nouvelles sont gardées par les sondes.
Il ne s’agit pas d’une promesse d’identité bit à bit des trajectoires : les
nouvelles gardes ajoutent des opcodes et les deux bras doivent partager le code.

À 1, le dispatch pose un booléen coalescé. Une entrée ajoutée **après toutes les
entrées existantes** (`main.nut:715`, `scheduler.nut:249`) porte le calcul de fond.
`po01_reactive.nut:195` attend un portefeuille, la fin du bootstrap, la fin des
phases C78 **scan/publish/apply**, et l’absence de worker actif. Aucun rafraîchissement
annuel rail/route n’est ajouté pendant AIR : V143 n’est pas réintroduit. Le scan
AIR C78 peut absorber les révisions avant le départ du lot ; dans ce cas, la
demande devient inutile et est retirée sans nouvelle reconstruction.

Le snapshot précède tous les refreshs. Un catalogue privé et une copie des lignes
et des abandons alimentent le calcul. Les modes sont l’union des dépendances C76,
avec masquage des modes coupés. Les générateurs Squirrel de
`po01_generators.nut` conservent leurs locales entre reprises ; les quatre corps
proviennent mécaniquement des producteurs synchrones, avec ajout de `yield` aux
boucles. Le contrat Python vérifie leur identité après retrait des checkpoints.
Le moteur AIR réutilise `OpexRegenerateAirProjectsSlice`, sans nouveau modèle
physique, sans modification de C115. Les demandes tardives restent pendantes.

`po01_reactive.nut:162` publie le lot seulement après tous les modes :
`OpexRegenerateModeProjects` accepte le résultat déjà calculé, remplace les modes
concernés sur une copie du **portefeuille courant**, garde les autres alternatives,
projets spéciaux et stock rail, injecte la flotte actuelle, puis resélectionne sur
`OpexAvailableCapital()`. Aucun portefeuille partiel PO-01 n’est exposé.
`orchestrator.nut:1182` acquitte les nombres capturés par
`orchestrator.nut:1154` ; les révisions arrivées ensuite ne sont pas acquittées.
L’invalidation de sûreté abandonne le lot et libère la tâche catalogue.

`persist.nut:758` détruit les états transitoires au Load, avant même le test des
données nulles. Aucune locale de générateur n’entre dans Save ; le filet complet
Load C76 (`persist.nut:1073`) est maintenu. Cela établit un contrat statique,
**pas un roundtrip exécuté**.

Le journal du prototype porte `batch`, causes, modes, snapshot, `PO01_SLICE`
(coût réel de chaque reprise), `PO01_BATCH` (sommes par couche/mode/publication)
et `PO01_PUBLISH_MODE` (détails imbriqués de publication, dont flotte).
Ne pas additionner les détails de publication à leur total parent.

## Limites et validation restante

**La borne stricte d’opcodes par tick demandée n’est pas entièrement livrée.**
La boucle de reprise des générateurs est limitée à 4 000 opcodes, avec marge de
2 000, et ne continue pas sur un budget neuf après changement de tick. Elle
n’admet qu’un passage PO-01 par tick. Cependant, une reprise peut dépasser la
borne dans un appel atomique : économie d’une paire, recherche de site/BFS eau,
refresh d’une couche, préparation/copie et publication/sélection. L’AIR conserve
également la granularité atomique de C78. `PO01_SLICE ticks/ops` expose ces
dépassements, sans les masquer. Un bornage dur exigerait de découper aussi ces
appels et la publication ; ce prototype ne doit pas être présenté comme tel.

Les API du monde restent vivantes pendant le calcul ; le snapshot couvre les
**révisions acquittées**, pas une copie figée du monde OpenTTD. La durée d’un lot,
le retard des demandes coalescées, la starvation et le coût mémoire des
générateurs/copies restent à mesurer. Aucune équivalence économique n’est prouvée.

Validation exécutée : **19 contrats PO-01 verts** ; suite complète : **2 101 tests,
2 082 succès ordinaires, 3 ignorés, 3 échecs attendus, 12 erreurs et 1 échec**.
Les 13 anomalies sont les mêmes que sur `master` (2 082 tests) et proviennent de
l’absence de `ai/AAAHogEx-115/info.nut` dans ce worktree. Les tests ne sont pas
retouchés pour cacher ce prérequis. `undecl.py` : mêmes deux symboles externes
NoAI que master (`AICONFIG_BOOLEAN`, `CONFIG_BOOLEAN`), aucun nouvel indéclaré.
`delim.py` : aucun diagnostic des deux côtés. `git diff --check` : propre.

Aucun Docker, banc ou moteur lancé. À exécuter par l’utilisateur : smoke causal
42 × 1 an, `po01_reactive_split=0` contre `1` sur ce même arbre ; le défaut reste 0.
Le smoke d’un an ne suffira probablement pas à exposer PO-01, qui attend la fin
du scan AIR initial (27 mois sur une graine historique). Prévoir ensuite les
vrais événements villes/lignes/moteurs AIR, un Save/Load en cours de lot et les
mesures d’opcodes par reprise, avant toute qualification économique.
