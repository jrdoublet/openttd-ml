# Prompt — V294c adaptatif : poids A* fort d'abord, abaissé seulement sur le segment qui bloque

Dépôt `openttd-ml`, IA OpenTTD `ai/OpexAI/` (Squirrel/NoAI). Lis d'abord `AGENTS.md` (§4, protocole V102), `ai/OpexAI/CLAUDE.md` (pièges Squirrel : pas de capture de closure, `const` littéral seulement, `clone`/`base` réservés) et l'entrée **V294** de `docs/taches.md` (sous-items V294a-k, paramètres A* d'AAAHogEx).

Crée un worktree depuis `master` : `git worktree add -b v294c-adapt ../wt-v294c-adapt master`. Travaille seulement là. Ne change aucun défaut, ne fusionne rien, ne lance pas de banc moteur (le smoke est fait ensuite par Claude).

## Contexte vérifié (20/10)
- Le poids A* est fixé une fois par recherche : `OpexRailAstarWeight(dist)` (`builder_rail.nut:828`) renvoie 120 % sous 100 tuiles et 200 % au-delà (V172). AAAHogEx utilise 200 % partout (`ai/AAAHogEx-115/pathfinder.nut`, `_estimate_rate = 2`).
- La recherche segmentée (`OpexAdvanceSegmentedSearch`, `builder_rail.nut:1218`) crée un nouveau pathfinder à chaque segment (`state.pathfinder == null`, ~l. 1226-1250) et applique `state.weight` à `pathfinder.cost.astar_weight_pct`. Un segment dure `SEGMENTED_SEGMENT_ITERS` (2 000) itérations, puis on retient le meilleur nœud de la frontière (`OpexFrontierAlternatives`) et on repart. Un retour arrière (`OpexTrySegmentedBacktrack`, l. 1142) donne 10 000 itérations au segment suivant. Le budget total est de 5 000 itérations.
- Une autre branche (`v294cd`, agy) ajoute un réglage simple `v294_rail_weight_pct` (poids fixe à toutes les distances). Ton travail est indépendant : ne t'appuie pas dessus.

## Demande de l'utilisateur
« On peut commencer avec une tentative tout droit, puis élargir uniquement sur les segments difficiles. »

## À faire
1. Nouveau réglage `v294_rail_weight_adapt` (défaut 0 = master inchangé, sinon N = poids initial en %, bornes 100..400). Déclaration dans `info.nut` (les quatre `*_value` égaux à 0), une seule lecture dans `settings.nut::OpexLoadSettings()`, globale `V294C_RAIL_WEIGHT_ADAPT <- 0;` dans `globals_pre.nut`.
2. Si le réglage est actif, la recherche segmentée part avec `weight = N`. À chaque fin de segment, mesure la progression : la distance de Manhattan du meilleur nœud de frontière à la cible la plus proche, comparée à celle du début du segment. Si la progression est inférieure à un seuil (par exemple moins de 10 % de la distance restante, ou un retour arrière, ou NOPA), le segment suivant passe au poids historique (`OpexRailAstarWeight(dist)`), puis à 100 % si ça bloque encore. Dès qu'un segment progresse normalement, le poids remonte à N. Garde l'état dans la table `state` (ex. `state.v294cWeight`, `state.v294cLastDist`), en créant les clés avec `<-`.
3. Le même mécanisme doit fonctionner dans les trois appelants (`task_rail.nut` : `_startRailSearch` ~790, `_startRailUpgradeSearch` ~1324, `_startRailStockSearch` ~1469) sans changer leur code autant que possible : idéalement tout se passe dans `OpexAdvanceSegmentedSearch`.
4. Sous `DECISION_LOG`, journalise via `OpexDecide("V294C", "event=weight from=.. to=.. seg=.. remaining=..")`. Aucun coût au défaut 0 : chaque branche nouvelle est gardée par `V294C_RAIL_WEIGHT_ADAPT > 0`.
5. Tests : `sweeps/test_v294c_weight_adapt.py` (réglage à 0 par défaut, une seule lecture, garde sur chaque branche, aucune globale non déclarée, aucune closure). Relève de 1 les plafonds `AddSetting(` dans `sweeps/test_v246_fixed_policies.py`, `test_v251_inventory.py`, `test_v259_bridge_renew.py` et `test_v284_rail_growth.py`, avec un commentaire « +1 V294c ». `python3 -m unittest discover -s sweeps -p 'test_*.py'` doit être entièrement vert.
6. Commit sur `v294c-adapt` (message « V294c: poids A* adaptatif par segment, defaut 0 »), sans `ai/AAAHogEx-115` et sans résultats. Rapport court : fichiers et lignes, ce qui est vérifié, ce qui ne l'est pas, et la valeur de N proposée pour le smoke (200 ou 300).

## Critère de réussite au banc (pour information)
Smoke rail seul 42×3 avec `decision_log=1` : moins d'ABND et des itérations médianes plus basses que la référence, à longueur de tracé comparable (un poids fort trouve plus vite mais plus long). Ensuite, porte A 40×3 `gain_short`.
