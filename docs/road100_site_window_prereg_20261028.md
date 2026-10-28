# ROAD100-11 — fenêtre de préplans voyageurs diversifiée

Préréservation du 28 octobre 2026, avant banc économique. Réglage opt-in
`road100_site_window=1`, défaut **0** aux quatre difficultés ; actif uniquement
avec `road100_site_first=1`, donc en ROUTE seule. Aucun changement du chemin OFF.

## Fait causal préalable

Dans `road100_waitfleet_v1_expo_5x5_20261028_engine`, le producteur
`ROAD100_SITE_FIRST` répète souvent des préplans `TRACEX` déjà échoués :
187 préplans en 35 générations, dont 164 refus `plan`, pour environ
94,3 millions d'opcodes de préflight. Plusieurs couples apparaissent aux
premières positions de multiples générations. Le tri constant par profit
urbain proxy empêche d'examiner des alternatives de rang inférieur avant le
plafond de 2,5 millions d'opcodes, même si leur voirie serait faisable.

## Intervention isolée

Conserver **la paire de rang 0** en première tentative ; diversifier les
rangs suivants avec une fenêtre déterministe et circulaire, calculée avant
le premier appel au planiteur. Pour une liste de taille `n > 1` :
`offset = ((année % 10) * 5 + ((mois - 1) / 3)) % (n-1)` ;
au rang de tentative `k>0`, visiter
`1 + ((offset+k-1) % (n-1))`. En janvier 1970 la fenêtre reproduit
exactement l'ordre historique, mais elle avance aux années suivantes.
Cette formule n'est pas optimisée sur les résultats à venir.

On ne change **ni** les limites actuelles `plans<6` et `ops<2500000`,
**ni** les critères de rendement, caisse, site, exclusion de ville ou
connexion, **ni** le chemin de construction. La fenêtre peut améliorer
l'exploration sans économiser les opcodes : elle réinvestit le budget dans
d'autres paires ; ne pas présenter les 94,3 M comme un gain d'opcodes prédit.
Nouvelle télémétrie : indice testé et fenêtre pour prouver l'exposition.

## Qualification pré-définie

1. Projection OFF exacte + tests de contrat et smoke compilant graine 42,
   1 an, apparié ; 1970 peut rester identique.
2. Diagnostic apparié 5 graines `42,100,7,999,2026` × 5 ans, même bundle.
   Lire préplans, admissions, constructions, `profit_year` Opex, profits AAA,
   les cinq horizons, caisse, valeur, bus, gares et opcodes.
3. Si exposition effective, moyenne terminale favorable, garde de valeur
   respectée et absence d'érosion forte sur un horizon antérieur, envisager
   la porte A 40×5 préenregistrée (`gain_short`, ≥4 % de profit moyen,
   Wilcoxon p<0,05, IC95 bootstrap inférieur >0 et valeur ≥−5 %).
   Sinon conserver défaut 0 et ne pas qualifier.

Les échecs de construction ne deviennent jamais des projets admis. La
fenêtre peut être nocive si les rangs secondaires sont moins rentables ;
seules les recettes et profits réalisés tranchent.
