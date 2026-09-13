# OpexAI — contexte pour la revue de code

## Quoi
`OpexAI` est une IA de jeu OpenTTD (framework NoAI), multimodale (rail, route, air, eau).
Objectif du script (`info.nut`) : "meilleur ROI par origine/destination, puis revenu maximisé
sous contraintes de capital et d'opcodes."

## Le but : battre AAAHogEx
AAAHogEx est l'IA adverse utilisée comme arbitre externe de toute décision : en cas de désaccord
entre un raisonnement interne et le résultat d'un banc contre AAAHogEx, le banc gagne. Toute la
logique de scoring interne (profit/opcode, ROI) n'est qu'une heuristique d'allocation ; la
métrique qui compte est la comparaison directe (`company_value`, `profit_year`) sur carte
partagée.

État mesuré le plus récent (duel C42, 2026-09-11, carte partagée) : AAAHogEx gagne 20/20 —
37,79 M£ de valeur / 10,26 M£ de profit annuel et 1 077 véhicules, contre 5,67 M£ / 1,24 M£ et
158 véhicules pour OpexAI. Ne pas citer de chiffre antérieur au 2026-09-09 : ces résultats sont
archivés et ne font plus foi (voir `docs/taches.md`).

## Architecture : le budget d'opcodes est une ressource de flux, pas un stock
Chaque tick de jeu accorde un budget d'opcodes fixe avant suspension du script
(`script_max_opcode_till_suspend`, de l'ordre de 10 000). Ce budget ne se cumule pas d'un tick à
l'autre : tout calcul long doit donc pouvoir être découpé et repris plutôt qu'exécuté d'un bloc.
Deux implémentations concrètes de ce principe, déjà en production (pas un plan futur) :
- **Ordonnanceur de micro-tâches** (`main.nut`) : `_taskQueue` est une liste de tâches nommées
  (catalogue, rapport, mise à la casse, construction eau/route/rail/signalisation...) avec
  `dueCycle` et `enabled` ; `_taskCursor` fait tourner l'exécution en round-robin, persisté à la
  sauvegarde.
- **Recherche de chemin ferroviaire segmentée et reprenable** (`builder_rail.nut`) :
  `rail_search_resumable`, `rail_micro_deadline`, `rail_segmented_search` (tous à défaut 1,
  adoptés) découpent l'A* en tranches de `RAIL_SEARCH_SLICE` itérations avec un point de reprise
  explicite plutôt qu'un recalcul.

Le pipeline de décision (sélection des lignes à construire) : `candidates.nut` génère les
candidats → `economy.nut` les score en ROI → `projects.nut` sélectionne le portefeuille à
construire (`portfolio_v2`, seul chemin depuis le 2026-09-11 — le legacy knapsack a été
supprimé, pas de branche morte à unifier).

## Ce qui ressemble à un bug mais n'en est pas un
- La plupart des réglages de `info.nut` sont des **drapeaux d'expérience à défaut 0/false/off** :
  du code vivant mais volontairement inerte (hypothèse déjà banquée et rejetée, ou pas encore
  banquée). Vérifier la valeur par défaut avant de signaler "code mort" ou "flag jamais activé".
- `debug_signs=1` par défaut n'est pas un oubli de debug : c'est la seule source de mesure pour
  tous les bancs `sweeps/*.py`. Il ne doit être mis à 0 que pour une partie réelle avec des
  humains.
- Philosophie "armes égales" : ne jamais proposer de bridage ou de simplification qui
  handicaperait OpexAI par rapport à AAAHogEx (qui, lui, ne se bride jamais) — un déséquilibre
  involontaire invaliderait tout le banc.
- `GetAPIVersion()` déclare "15", aligné sur la plateforme de banc OpenTTD 15.3 (C62).


## Pour aller plus loin
L'historique complet des décisions, mesures et fiches techniques vit dans `docs/taches.md`
(journal continu) — un humain doit le consulter avant d'agir sur un finding, même si cet outil de
revue ne le lira pas automatiquement.
