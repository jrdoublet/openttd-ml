# RAIL-LOOP — bancs PC du 4 novembre 2026

Code : branche cloud `ccr-6d627d08-tlnphk` (07e2d389), plus un correctif local non commité
dans `ai/OpexAI/rail_loop.nut`. Le défaut reste `rail_loop=0`. La garde de valeur est
neutralisée (`--value-guard-max-loss-pct 100`), à la demande de l'utilisateur.

## Correctif `depot_flow`

Premier smoke 4×6 : **0 boucle**. Toutes les lignes étaient rejetées `depot_flow`, car :
- `OpexRailLoopDepotFlow` ne cherchait l'avant du dépôt qu'aux indices 4 à n−4 ;
- or `OpexBuildDepot` pose le dépôt primaire sur la première case de rail après la gare
  (indice 1 ou 2).

Corrections :
- recherche sur toute la voie (indices 1 à n−2) ;
- PBS de garde gare amont → dépôt **facultatif** quand aucune case n'est libre (journal
  `RLOOP phase=guard_skip`).

Contrats : 20/20.

## Smoke 4×6 rail seul (graines 17 512 314 8191)

- 1 boucle par graine ; lignes 16 et 20 montées à **8 et 7 rames** ;
- 0 rame Opex perdue ;
- Δ profit = +2 k (2V/2D) ;
- motifs de rejet restants : `depot_front_curve` 46, `back_lead_A/B` 30, `cash` 20.

## Portes

Graines neuves, disjointes de SEEDS_40, générées par LCG avec la graine 20261104 :
- 40 graines pour les portes A ;
- 20 autres pour les portes B.

| Banc | Δ profit/an | V/D | p | IC95 | Valeur | Verdict |
|---|---:|---:|---:|---|---:|---|
| A rail seul 40×5 | +11 k | 17/23 | 0,99 | [−47 k ; +71 k] | +0,4 % | fail_primary (neutre) |
| A multimodal 40×5 | −33 k | 18/22 | 0,33 | [−106 k ; +41 k] | −1,7 % | fail_primary (neutre) |
| **B rail seul 20×10** | **+173 k** | **16/4** | **0,0014** | **[+86 k ; +257 k]** | **+10,3 %** | **pass, significatif** |
| B multimodal 20×10 | −64 k | 9/11 | 0,67 | [−248 k ; +113 k] | +1,1 % | pass (neutre) |

### Exposition (bras ON)

| Banc | Boucles | Rames ajoutées | Graines sans boucle |
|---|---:|---:|---:|
| A rail 40×5 | 50 | 73 | 10/40 |
| A multimodal 40×5 | 56 | 65 | 8/40 |
| B rail 20×10 | 33 | 119 | 3/20 |
| B multimodal 20×10 | 39 | 89 | 2/20 |

- 0 rame Opex perdue sur les 10 ans.
- Échecs `RLOOP phase=fail` : 56 en rail seul, 27 en multimodal (motifs non encore ventilés).

## Lecture

- Le mécanisme est physiquement validé : double voie à sens unique, croissance de flotte
  jusqu'à 8 rames, aucune rame perdue.
- **En rail seul à 10 ans**, c'est le **premier gain significatif** de la série double voie :
  +173 k£/an, environ +10 %. Le ratio Opex/AAA reste toutefois à 46 %.
- **À 5 ans**, la porte est neutre. Les boucles sont créées en 1973-1975 et grossissent
  ensuite : l'effet arrive trop tard pour un horizon de 5 ans.
- **En multimodal**, rien de mesurable : les boucles pèsent peu à côté de la route et de l'air.
- **Prochains leviers d'exposition** :
  - `depot_front_curve` (première cause de rejet) ;
  - arrières de quai non libres (`back_lead_A/B`) ;
  - admission plus précoce ;
  - ventilation des 56 échecs.

## Décision de défaut (4 novembre 2026, utilisateur)

`rail_loop` passe à **1 par défaut** sur décision explicite de l'utilisateur. C'est une
**dérogation au protocole V102** : la porte A `gain_short` n'est passée ni en rail seul ni en
multimodal (verdict neutre).

Changements associés :
- la projection OFF (`sweeps/rail_loop_off.py`) et le contrat de défaut ont été alignés ;
- pour désactiver la boucle, passer `OpexAI[rail_loop=0]`.

Suite complète : 3 387 tests, 3 échecs, tous préexistants et identiques à ceux d'avant le
changement :
- `test_b6_portfolio_causality` ;
- deux `test_rail_long_v3_multi`.

Traces des bancs : `docs/rail_loop_bancs_20261104/` (sorties console, script de chaîne).
