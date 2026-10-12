# V151c — où partent les ~66 M opcodes annuels (spans exclusifs, 12/10)

Campagne `v151c_spans_3x5_20261012` (worktree `wt-v148-rail-diag`, code `d694cc4`, duel,
graines 42/100/999, 5 ans, `probe_span_trace=1`, `probe_loop_ops=1` ; bras B inerte).
Analyse : `sweeps/analyse_span_exclusive_by_year.py` (opcodes exclusifs = span − enfants directs).
La sonde ajoute ses propres opcodes ; les parts relatives sont fiables, les absolus approchés.

## Postes exclusifs par année (moyenne par graine, budget ≈ 66 M)

| Poste | 1970 | 1971 | 1972 | 1973 | 1974 |
|---|---:|---:|---:|---:|---:|
| Sélection (`select.full` + `select.incremental` + `projects.pass`) | 15,5 M | 21,8 M | 27,0 M | 27,5 M | 18,2 M |
| Publication AIR (`pub.filter`, `pub.select.filter`, `pub.select.stats`, `pub.partition`, `pub.insert`) | 18,0 M | 11,4 M | ~2 M | ~0,6 M | ~0,1 M |
| Scan AIR (`air.new_pairs`, `air.sites`, `air.hub_site`, `air.hub_hub`, `air.plans`, `air.prepare`) | ~13 M | ~9,5 M | ~6,7 M | ~3,6 M | ~3,7 M |
| `loop.orch` exclusif (≈ tranches A* rail `astar.slice`) | 3,0 M | 2,2 M | 14,4 M | 11,7 M | 10,9 M |
| `fleet.resize` | ~0,2 M | 1,4 M | 1,9 M | 5,8 M | 16,6 M |
| Non utilisé (`loop.sleep`) | 5,3 M | 4,7 M | 3,3 M | 1,6 M | 2,4 M |

## Fréquence × coût unitaire (par graine)

| Span | 1970 | 1971 | 1972 | 1973 | 1974 | Appelant principal |
|---|---|---|---|---|---|---|
| `select.full` | 291 × 31 k | 266 × 31 k | 100 × 96 k | 53 × 245 k | 115 × 77 k | `pub.select.score` (chaque publication AIR) |
| `select.incremental` | 11 × 435 k | 22 × 340 k | 22 × 510 k | 18 × 763 k | 22 × 352 k | `projects.post_regen.incremental` |
| `projects.pass` | 148 × 55 k | 204 × 78 k | 106 × 219 k | 41 × 588 k | 84 × 221 k | `task.projects` |
| `pub.filter` | 269 × 22 k | 228 × 20 k | 58 × 15 k | 12 × 3 k | 7 × 4 k | `catalog.rebuild` |
| `pub.select.filter` | 279 × 26 k | 243 × 22 k | 76 × 20 k | 34 × 17 k | 93 × 3 k | `select.reselect` |
| `fleet.resize` | 161 × 1 k | 226 × 6 k | 129 × 14 k | 61 × 95 k | 106 × 155 k | `task.air_fleet` |
| `loop.orch` | 1 503 × 15 k | 1 696 × 14 k | 913 × 58 k | 361 × 162 k | 757 × 73 k | boucle |

## Lecture

- **La sélection est le premier poste chaque année.** En 1970–71, chaque publication
  incrémentale AIR (~270 par an) relance filtre, sélection complète et statistiques, soit
  environ 90 k par publication et 24 M par an.
- **`fleet.resize` passe de 1 k à 155 k par appel** entre 1970 et 1974 : son coût croît avec la
  flotte. C'est le premier poste en 1974 (25 %).
- **`loop.orch` exclusif (11–14 M/an dès 1972) est en fait l'A* rail.** Les agrégats `SPAN_AGG` ne sont pas soustraits du parent : les tranches `astar.slice` (13,7 / 11,5 / 10,3 M par graine en 1972 / 1973 / 1974) tombent dans l'exclusif de `loop.orch` (17,8 M pour la graine 42 en 1972, contre 17,5 M d'`astar.slice`). **Correction de la première version de cette fiche, qui annonçait l'A* à 1–2 M/an** : `astar.build` ne couvre que la phase de construction. Avec V148, environ la moitié de ces opcodes A* part dans des tentatives qui échouent.
