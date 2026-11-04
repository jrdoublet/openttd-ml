# Mission cloud n°5 : choix des paires bus — où perdons-nous les paires d'AAAHogEx ? (route seule, 3 ans)

Dépôt `jrdoublet/openttd-ml`, branche de départ `cloud/road1y-pack3-0411`. Réponds en français. Lis d'abord `AGENTS.md` §4/§4.1, `ai/OpexAI/CLAUDE.md`, `docs/cloud/road1y_0411/PROMPT.md` (contexte, règles du dépôt, données, sources AAA, commande de smoke), puis `BILAN_MISSIONS.md`, `RAPPORT_CLOUD.md`, `agy_paxgap_rapport.md` et `agy_new72_rapport.md`.

## Constat
- Bus PAX : −94 k£/an sur l'écart de −188 k. Sur les 48 paires de villes communes, profit par ligne IDENTIQUE (39,4 k contre 39,7 k). **Tout l'écart bus est sur les paires que nous ne partageons pas** : AAA 30,2 k£/ligne, nous 25,1 k ; paires AAA plus longues (médiane 107-112 tuiles contre 98), plus équilibrées (min/max médian 0,87 contre 0,49), villes de même taille.
- Les leviers de flotte sont épuisés (5 échecs, dont le portage complet de la flotte d'AAA, −22,7 k). Le rendement d'une même paire est déjà égal : il reste **le choix des paires**.

## Déjà essayé sur le choix des paires — ne pas refaire
`road1y_next=64` (adopté : plancher interurbain 64 tuiles), `road1y_next3=56` (adopté : crédit de voirie 96-127 tuiles), `road1y_far` (> 128 tuiles, neutre), `road1y_next2` (bonus fundScore aux longues, −300 k), `road1y_astar` (adopté), `road1y_bridge` (neutre), `road1y_pax_min` (estimation à 2×min(A,B) : −11,6 k à 100, −2,9 k à 50), `road1y_abandon_days`, `road1y_site_relocate`, `road1y_retry`, bus de quartiers (`spread_stops` adopté). Changer encore un poids de score n'est pas la mission.

## À faire
### Phase 1 — trace des paires d'AAA (≤ 2 h)
Données : `n_spread2_3y.jsonl.gz` + `engine_seed*.log.gz` (3 graines, journaux complets des deux IA, probes=258), `n_spread2_gateA.jsonl.gz` (40 graines, télémétrie par ligne). Pour chaque ligne bus d'AAA dont la paire de villes n'est pas desservie par Opex :
1. La paire figurait-elle dans nos candidats (`OpexRoad100SoloPaxCandidates`, `bus_districts*.nut`, `candidates.nut`) ? Sinon, quel filtre l'a écartée (bande de distance, taille de ville, site, plafond de 4 lignes par ville, `SITE_LOST`, autre) ? Si oui, son rang, son fundScore, et pourquoi elle n'a pas été construite (troncature `PROJECT_TOP_K = 64`, caisse, échec A* `TRACEX`/`BUDGET`, paire bannie 365 j, AAA arrivé avant) ? Cite fichier:ligne pour chaque filtre.
2. Symétriquement, nos lignes sur des paires qu'AAA n'a pas prises : profit/ligne, distance, déséquilibre, rang à la sélection.
3. Comparer à AAA : comment il énumère et classe les paires de villes pour bus (`route.nut`, `estimator.nut`, `main.nut` ; dénominateur profit/coût ou profit/temps de chantier, filtre min < 27, distance, villes déjà desservies). Cite fichier:ligne.
4. Écrire `docs/cloud/road1y_0411/RAPPORT_CLOUD5.md` : tableau des causes de perte des paires d'AAA (en nombre de paires et en k£/an), cause dominante chiffrée, effet attendu d'un levier (seuil utile de la porte A ≈ +21 k£/an). Si aucune cause ne dépasse le bruit, le dire avec les chiffres et s'arrêter là (c'est un résultat utile).

### Phase 2 — coder le levier visant la cause dominante (un seul)
- Il doit agir sur l'ensemble de candidats ou sur leur filtrage/ordre d'exécution, pas sur la flotte ni sur un simple poids de score déjà essayé.
- Règles du dépôt de `PROMPT.md` (info.nut 4 valeurs à 0, globale `globals_pre.nut`, lecture + forçage à 0 hors route seule dans LES DEUX chargeurs de `settings.nut`, pas de closure capturant une locale, `clone`/`base` réservés, `OpexDecide` sous `DECISION_LOG`, `sweeps/test_road1y_<nom>.py`, `test_road1y_multimodal_gate.py`, fixtures `road100_*.json`, `test_v251_inventory.py` ; depuis la racine `test_road1y*`, `test_road100*`, `test_v251*` verts). À 0 : code exécuté strictement identique.
- Branche `cloud/road1y-<nom>` depuis `cloud/road1y-pack3-0411`, push de cette branche seulement. Jamais master, aucun défaut changé.

### Phase 3 — smoke GitHub
Commande de `PROMPT.md` avec `probes=258` aux deux bras et la variante du levier. Suivi par `gh run view` toutes les 10 min. Si `gh workflow run` répond 403 ou que le jeton manque, arrête-toi après le push et dis-le (je lancerai le smoke sur le VPS). Vérifie : parties complètes, 0 erreur, mécanisme exercé (paires d'AAA désormais prises par Opex, compteurs `OpexDecide`), profit_year par graine. Pas de conclusion économique sur 3 graines, pas de porte A/B.

## Livrables
`RAPPORT_CLOUD5.md`, branche `cloud/road1y-<nom>` poussée, et en fin de session : branche, commit, réglage et valeur à banquer, lien du run.
