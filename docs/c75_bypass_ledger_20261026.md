# C75 bis — isolement expérimental du diagnostic de bypass K_pass (26/10/2026)

Le registre `C75_KPASS_BYPASS_LEDGER` recueillait toujours ses compteurs,
ses lignes `C75_BYPASS` et ses panneaux `C7C/C7Y/C7S` en jeu normal.
Ses champs ne sont lus que par `OpexC75BypassFlushYear` et ses émetteurs,
jamais par la décision de franchir `K_pass`. Cette dernière utilise
`OpexC75KPassBypassIsNewLine`, `OpexC75ComputeKPass` et le booléen
local `c75BypassConsumed` dans `task_projects.nut`.

L'option **`c75_bypass_ledger_skip`**, à **0 dans les quatre difficultés**,
permet d'examiner le coût de ce registre indépendamment de l'expérience
`c75_year_ledger_skip`. À **1**, lorsque **`DEBUG_SIGNS=0` et
`DECISION_LOG=0`**, `OpexC75BypassResetYearLedger` laisse le registre
à `null` et l'année à `-1`; `EnsureYear`, `RecordEligible` et
`RecordConsumed` retournent sans produire leur télémétrie. `RecordStop`
et `FlushYear` possédaient déjà une garde sur `null`. À réglage 0 et
avec les sondes/panneaux activés, le parcours historique est conservé.
`C75_PASS_DATES`, son Save/Load, la logique K_pass et le bypass réel
restent actifs. L'état diagnostique lui-même est transitoire.

## Vérification

- Contrats hôte étendus dans `test_c75_kpass_bypass.py`, plus inventaire
  historique strict `n75_mc_legacy.py` ; suite complète :
  **2 919 tests OK, 5 ignorés, 2 échecs attendus**, diff check sain.
- Smoke `probes=0`, graine 42 × 1 an, 2/2 parties saines et
  identiques : `results/c75bypass_skip_smoke_42x1_20261026.json`.
- Contrôle de préservation `probes=2`, graine 42 × 2 ans :
  2/2 parties saines, **un `C75_BYPASS` par bras**, même profit et même
  valeur : `results/c75bypass_skip_bench_42x2_20261026.json`.
- Exposition `probes=0`, graine 42 × 3 ans :
  **41 lignes `C75_BYPASS` sous option 0, zéro sous option 1** ;
  2/2 parties saines, `profit_year` variante−référence
  **−72 712 £/an**, valeur **+1,95 %**, `diagnostic_only` :
  `results/c75bypass_skip_exposure_42x3_20261026.json`.
  Bundle figé commun aux trois essais : `ae7bee9e2a80c94fdfe31420a2cc55102fc7a5a4abc7e1621442e02cd793deb9`.

L'identité à un et deux ans ne vaut pas neutralité économique :
à trois ans une seule graine diverge sous l'effet possible des opcodes.
L'économie d'opcodes de ce poste n'est **pas mesurée**, et il manque
un banc de neutralité apparié **B20×10** avant toute éventuelle adoption
en jeu normal. **Aucun défaut changé ; tâche générale « sondes » ouverte.**
Les seules émissions `C121_FLEET_MARGINAL` et `[FLEET_PROJECT]`
restent à classifier ou garder selon un contrat indépendant.
