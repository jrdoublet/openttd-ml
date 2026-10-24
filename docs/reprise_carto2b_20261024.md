# Prompt de reprise — CARTO-2b (en attente depuis le 24/10/2026)

Projet /openttd-ml, worktree `.worktrees/carto1` (HEAD détaché, non commité, base `eec5db81`).
Rapport : `.worktrees/carto1/docs/carto2_preparation_rail_20261024.md`, section « CARTO-2b ».
Docs voisins : `docs/carto1_couloirs_rail_20261024.md`, `docs/brief_idle1_20261024.md` (IDLE-1, non lancé).

## État
- CARTO-2b implémenté (bits 24+25+26) : tours V309 entiers pour le shadow, ligne de blocs Bresenham,
  quantum 9 000/10 000 opcodes, A* en pause/reprise au lieu d'annulation, file CARTO-1 coupée.
- Verdict : **NON QUALIFIÉ**.
- Dernière campagne `carto2b_budget9000_equal_log1024_3x5_20261024` contre le témoin OFF
  `carto2b_budget9000_off258_witness1024_3x5_20261024` :
  - écart de profit annuel ON − OFF : +3,17 / +4,64 / +0,78 M£/an (graines 42/100/999) ;
  - valeur ON 35,6 M£ contre 19,1 M£ (+86 %) ; Wilcoxon p = 0,25, diagnostic seulement.
- Ce gain n'est **pas attribuable** à la cartographie :
  - 0 tour CARTO-2b sur les graines 42 et 999 ;
  - graine 100 : 141 tours et au moins 398 k opcodes ;
  - le témoin OFF paraît faible ;
  - le témoin OFF n'est pas strictement reproductible : 6 checkpoints sur 360 diffèrent (graine 999, fin 1974).
- Mesures manquantes :
  - 0 paire A* libre/guidé arrivée au bout ; la recherche libre de la graine 100 a fait au moins 115 itérations ;
  - plans prêts fin 1974 inconnus ;
  - borne du coût d'un `FindPath(1)` impossible à découper non démontrée ; la première version avait dépassé un tick.

## À faire
1. Comprendre pourquoi les tours d'attente CARTO-2b ne se déclenchent pas sur les graines 42 et 999
   (conditions d'entrée V309 `unfunded_snapshot`, revalidations).
2. Faire aboutir au moins une paire A* libre/guidé, OK des deux côtés, sur les 3 graines. Mesurer itérations,
   opcodes et longueur. Journaliser l'état final : plans prêts au 31/12/1974.
3. Étalonner le coût d'expansion de `FindPath(1)` et garantir 0 tick dépassé.
4. Rendre le témoin OFF reproductible, ou expliquer l'écart de la graine 999.
5. Seulement ensuite : porte A `gain_short` 40×3, puis porte B `non_erosion` 20×10 (AGENTS.md §4.1).

Notes :
- master a avancé (`origin/master` = `d6b9b09f`, v8 et bit 4 de V275 retiré) : rebaser le worktree avant les bancs.
- Interdits : changer un défaut, commiter, pousser.
- Un seul Docker à la fois ; ne rien lancer si l'utilisateur utilise Docker.
