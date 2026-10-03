# AIR efficiency preflight — 20x10 du 02/10/2026

Qualification canonique de `air_efficiency_preflight` seul : 20 graines, 10 ans,
40 parties complètes, référence `air_efficiency_preflight=0` contre variante `=1`.
`probe_events=1` était identique dans les deux bras.

Résultat variante − référence sur `profit_year` : **−89 294 £/an** en moyenne,
médiane **−51 962 £/an**, **4 victoires / 14 défaites / 2 égalités**, test des
signes `p=0,030884`, IC95 **[−141 180 ; −37 408]**. Le ratio des moyennes de
`company_value` baisse de **−2,282652 %** : la garde −5 % passe, mais le verdict
C66.4 est `fail_primary`.

La télémétrie opcode n'est pas exploitable dans ce run : les champs
`observed_opcodes_*` et `selection_kopcodes_*` du JSON sont `null` et les logs
engine sont vides. Aucun gain opcode n'est donc revendiqué.

Décision : le critère demandé « neutralité économique ET gain opcode » échoue sur
la neutralité économique. `air_efficiency_preflight` reste **OFF par défaut**.
Le résultat brut local est `results/air_eff_preflight_20x10_20261002.json`
(répertoire `results/` ignoré par Git).
