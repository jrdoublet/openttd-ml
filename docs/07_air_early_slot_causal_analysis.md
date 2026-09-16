# Air early-slot — décision adoptée et mécanisme causal

**Date : 2026-09-15.**
**Statut : adopté.** `air_early_slot` fait partie de la politique retenue ; cette fiche n'a pas pour
objet de rouvrir la décision d'adoption, mais d'expliquer **pourquoi** le levier fonctionne face à
AAAHogEx.

## 1. Contexte : l'erreur 771 est une concurrence pour des slots aéroportuaires

Le diagnostic préalable sur `AIStation.ERR_STATION_TOO_MANY_STATIONS_IN_TOWN` (771) a montré que,
sur la graine 42, les échecs observés arrivent dans des villes où OpexAI possède **0 aéroport**.
Dans le duel courant, avec `station_noise_level=false`, cela signifie que les deux slots locaux ont
déjà été pris par AAAHogEx. Nettoyer des stations OpexAI ou utiliser un distant join ne crée donc pas
de troisième slot.

La réponse retenue n'est pas de construire des aéroports vides. `air_early_slot` **biaise le
classement de projets air déjà rentables** afin de sécuriser plus tôt les premiers slots de grandes
villes. Le modèle économique prédit toujours la rentabilité ; le bonus ne remplace pas le filtre
économique.

Réglages associés au mécanisme étudié :

- `air_early_slot=1` ;
- `air_early_slot_target_towns=6` ;
- `air_early_slot_min_pop=1000` ;
- `air_early_slot_bonus_pct=50`.

## 2. Décision économique déjà prise

Le banc officiel d'adoption est :

`results/bench_early_slot_20x10_w6.json`

Il compare `current` à `early_slot` sur **20 graines × 10 ans**, en duel OpexAI slot 0 contre le
même AAAHogEx slot 1. Les 20 paires vont de 1970 à 1979.

Sur la dernière année, la moyenne de `profit_year` OpexAI passe d'environ **1 330 712 £/an** à
**1 485 068 £/an**, soit **+154 356 £/an, +11,6 %**. Cette campagne est la preuve économique ayant
servi à l'adoption.

Le diagnostic décrit ci-dessous est séparé de cette décision : il ajoute une télémétrie passive et
sert à comprendre le mécanisme, pas à refaire le verdict d'adoption.

## 3. Question causale

Le simple nombre final d'aéroports ou de monopoles ne suffisait pas à expliquer le gain. L'hypothèse
à tester était plus précise :

> En prenant plus tôt un endpoint stratégique, OpexAI empêche AAAHogEx de suivre certains de ses
> marchés aériens les plus profitables. AAAHogEx se redéploie ensuite sur d'autres marchés, de sorte
> que le nombre total de lignes peut converger alors que la trajectoire économique a déjà divergé.

Cette hypothèse prédit quatre signatures :

1. un effet fort sur l'**identité** des marchés AAA, même si leur nombre total converge ;
2. une part croissante des marchés AAA disparus qui touchent une ville occupée par OpexAI sous
   early-slot ;
3. des marchés déplacés disproportionnellement profitables ;
4. une compensation ultérieure d'AAAHogEx par de nouveaux marchés, donc pas nécessairement une
   baisse permanente de son profit aérien total.

## 4. Télémétrie passive ligne par ligne

Campagne causale :

`results/diag_early_slot_lines_20x10_v1.json`

Analyse dérivée :

`results/diag_early_slot_lines_20x10_v1_analysis.json`

La campagne contient **40/40 parties complètes**, **20/20 paires**, `failed_runs=[]`, 10 années par
graine et les deux politiques `current` / `early_slot`.

### 4.1. Construction des lignes

La reconstruction est hors comportement décisionnel de l'IA : elle lit les chunks de sauvegarde.

- `VEHS` : véhicules primaires, capacité par cargo, `profit_this_year`, `profit_last_year` ;
- `ORDL` : source canonique des ordres sous OpenTTD 15.3 (`VEHS.common.orders` est un pointeur
  1-based, donc clé `orders - 1`) ;
- `ORDR` : fallback seulement ;
- `STNN` : stations, propriétaire et TownID.

AAAHogEx crée un `AIGroup` par `Route` et place les véhicules de la route dans ce groupe. Pour une
partie donnée, `VEHS.common.group_id` est donc un très bon **identifiant local de ligne** :

`line_key_local = group:<id>`

Cet ID n'est toutefois pas une identité inter-parties : il peut différer entre policies, seeds et
peut théoriquement être recyclé. Le matching `current` ↔ `early_slot` utilise donc une signature
canonique :

`market_key = <mode>|<TownID trié>,<TownID trié>`

et, lorsque le cargo doit être distingué :

`service_key = market_key|cargo=<cargo(s)>`

L'analyse principale agrège par `market_key`, car la question est celle de la concurrence pour les
endpoints/slots, pas l'identité interne du groupe AAA.

### 4.2. Ce que signifie le profit de ligne

Le champ utilisé est la somme de `VEHS.profit_this_year / 256` des véhicules **encore présents au
checkpoint de décembre**.

Il ne faut pas l'appeler revenu brut ni comptabilité exhaustive de ligne :

- un véhicule vendu ou remplacé avant le checkpoint disparaît du calcul ;
- le `removedYearProfit` privé d'AAAHogEx n'est pas lu ;
- aucun `revenue` historique fiable par ligne n'est exposé ;
- aucun `running_cost` historique réel par ligne n'est exposé.

Ces champs ne doivent donc pas être inventés ou reconstruits par ventilation de la comptabilité de
compagnie.

## 5. Résultat principal : même nombre de marchés, portefeuille différent

Moyennes sur les 20 graines :

| Année | Marchés AAA current | Marchés AAA early | Marchés current-only | Dont touchant ≥1 ville Opex early | Profit current-only | Part de ce profit touchant Opex | Δ profit air AAA early-current | Δ `profit_year` Opex |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1970 | 6,20 | 6,10 | 0,90 | 0,15 | 10,7 k£ | 51,6 % | -7,3 k£ | +6,2 k£ |
| 1971 | 13,10 | 13,00 | 3,05 | 1,05 | 169,2 k£ | 40,3 % | -44,0 k£ | +0,6 k£ |
| 1972 | 16,75 | 17,10 | 6,00 | 2,85 | 343,8 k£ | **62,3 %** | -14,8 k£ | +47,4 k£ |
| 1973 | 19,40 | 19,90 | 8,00 | 4,20 | 698,9 k£ | **64,2 %** | -81,9 k£ | +70,1 k£ |
| 1974 | 20,85 | 20,80 | 9,25 | 5,50 | 873,7 k£ | **67,4 %** | -11,8 k£ | +62,9 k£ |
| 1975 | 22,05 | 22,05 | 10,20 | 6,65 | 1 002,0 k£ | **68,5 %** | +105,8 k£ | +117,6 k£ |
| 1976 | 22,80 | 22,95 | 10,80 | 7,30 | 1 128,5 k£ | **73,3 %** | +45,8 k£ | +188,9 k£ |
| 1977 | 23,25 | 23,05 | 11,25 | 7,85 | 1 590,3 k£ | **76,4 %** | -93,2 k£ | +178,4 k£ |
| 1978 | 23,75 | 23,45 | 11,65 | 8,00 | 1 898,0 k£ | **76,3 %** | -6,5 k£ | +148,1 k£ |
| 1979 | 24,20 | 23,75 | 12,00 | 8,10 | 1 999,7 k£ | **74,0 %** | -291,1 k£ | +134,9 k£ |

Le point central est visible en 1979 : le nombre de marchés AAA est presque identique
(**24,20 vs 23,75**), mais seulement **12,20 marchés** sont communs en moyenne. Environ la moitié du
portefeuille aérien d'AAAHogEx n'est donc plus le même.

Early-slot ne « supprime » pas AAAHogEx. Il modifie durablement **où** AAAHogEx investit.

## 6. Les marchés déplacés sont liés aux villes prises par OpexAI

La part des marchés `current-only` qui touchent au moins une ville possédant un marché air OpexAI
dans la variante augmente avec la maturité :

- 1972 : 2,85 / 6,00 marchés, soit **47,5 %** ;
- 1974 : 5,50 / 9,25, soit **59,5 %** ;
- 1976 : 7,30 / 10,80, soit **67,6 %** ;
- 1979 : 8,10 / 12,00, soit **67,5 %**.

Surtout, ces marchés pèsent plus lourd en profit que leur nombre :

- 1972 : **214,0 k£ sur 343,8 k£**, 62,3 % ;
- 1974 : **588,8 k£ sur 873,7 k£**, 67,4 % ;
- 1976 : **827,6 k£ sur 1 128,5 k£**, 73,3 % ;
- 1979 : **1 479,3 k£ sur 1 999,7 k£**, 74,0 %.

La signature attendue est donc présente : les marchés déplacés autour des villes sécurisées par
OpexAI sont **disproportionnellement rentables**.

Un endpoint suffit souvent. En 1979, 8,1 marchés current-only par seed touchent au moins une ville
OpexAI, mais seulement 2,6 ont leurs deux villes couvertes. Cela cadre avec une concurrence de slots :
prendre un endpoint stratégique peut suffire à détourner toute la liaison AAA.

## 7. Exemples de lignes très profitables déplacées

Les exemples ci-dessous sont des marchés **dans une graine donnée**. Les TownID ne doivent jamais
être agrégés entre graines comme s'il s'agissait de la même ville.

- seed 73, 1972, `air|10,45` : **~369,4 k£/an observés**, 6 avions ; OpexAI occupe les deux villes
  dans la variante ;
- seed 2026, 1979, `air|14,22` : **~951,1 k£/an**, 6 avions ; une des deux villes est occupée par
  OpexAI dans la variante ;
- seed 73, 1978, `air|10,45` : **~845,2 k£/an**, 9 avions ; les deux villes sont occupées par OpexAI ;
- seed 8191, 1978, `air|5,27` : **~795,2 k£/an**, 6 avions ; une des deux villes est occupée par
  OpexAI.

Ce sont précisément des marchés que le simple compteur final d'aéroports ne permet pas de voir.

## 8. AAAHogEx compense : le mécanisme est une réallocation, pas une destruction fixe de profit

Le profit aérien total observé d'AAAHogEx n'est pas inférieur chaque année sous early-slot.

- 1975 : **+105,8 k£** early-current ;
- 1976 : **+45,8 k£** ;
- 1977 : -93,2 k£ ;
- 1978 : -6,5 k£ ;
- 1979 : -291,1 k£.

En 1979, les marchés `current-only` valent environ **2,00 M£/an**, mais les marchés
`variant-only` valent déjà environ **1,80 M£/an**. AAAHogEx remplace donc une grande partie des
marchés perdus par d'autres marchés.

Il est faux de résumer le mécanisme par « Opex prend X £ à AAA ». Le résultat observé est plutôt :

1. OpexAI prend certains slots/endpoints plus tôt ;
2. certaines routes AAA très intéressantes n'apparaissent plus ;
3. AAAHogEx réinvestit sur d'autres marchés ;
4. les deux compagnies accumulent ensuite capital, véhicules et réseau selon des trajectoires
   différentes.

C'est un mécanisme de **path dependence / avantage de premier entrant**.

## 9. Cohérence inter-graines

Les corrélations de Pearson entre le gain annuel OpexAI et le profit des marchés AAA current-only
qui touchent une ville OpexAI sont positives sur les dix années. Elles valent notamment :

- 1971 : +0,49 ;
- 1972 : +0,31 ;
- 1973 : +0,37 ;
- 1976 : +0,36 ;
- 1979 : +0,42.

Lorsque le profit aérien AAA diminue davantage, le gain OpexAI est également parfois plus élevé :
la corrélation `gain Opex` / `Δ profit air AAA` vaut -0,51 en 1972 et -0,47 en 1979.

Ces corrélations sont **descriptives seulement**. Les deux variables sont des conséquences du même
traitement, avec `n=20` par année ; elles ne constituent pas une identification causale indépendante.

## 10. Limites d'interprétation

1. **Profit de survivants.** Les profits de ligne sont ceux des véhicules encore présents en
   décembre ; les véhicules vendus/remplacés ne sont pas reconstitués.
2. **Pas de revenu/coût de ligne exhaustif.** Ne jamais inventer `revenue` ou `running_cost` à partir
   de la comptabilité compagnie.
3. **`group_id` local seulement.** Le matching inter-arm utilise `market_key`, jamais l'égalité des
   IDs de groupe.
4. **TownID comparable uniquement dans une même seed.** Un TownID numérique identique dans deux
   graines n'identifie pas la même ville.
5. **Marché ≠ route interne unique.** Plusieurs groupes/services peuvent desservir la même paire de
   villes ; `market_key` les agrège volontairement. `service_key` est disponible pour distinguer le
   cargo.
6. **Orientation non causale.** Pour les boucles bidirectionnelles, les deux TownID sont des
   endpoints ; `origin`/`destination` ne doivent pas être surinterprétés.
7. **Portfolio displacement, pas blocage contrefactuel un-à-un.** Les deux arms sont deux parties
   séparées contre le même AAAHogEx gelé. Une route `current-only` montre une divergence de
   portefeuille provoquée par la politique ; cela ne prouve pas que la même route exacte aurait été
   construite puis physiquement bloquée à l'identique dans l'autre partie.
8. **Diagnostic ≠ banc d'adoption.** `diag_early_slot_lines_20x10_v1` explique le mécanisme ;
   `bench_early_slot_20x10_w6` porte la décision économique.

La couverture AAA utilisée dans l'analyse est très élevée : 200 pair-years et seulement **9
véhicules AAA non résolus** dans les snapshots comparés (6 côté current, 3 côté early-slot), sans
impact visible sur l'intégrité du matching aérien.

## 11. Conclusion

Le mécanisme retenu est désormais documenté ainsi :

> **Early-slot ne gagne pas principalement parce qu'il laisse AAAHogEx avec beaucoup moins de
> marchés à dix ans. Il gagne parce qu'il change tôt l'identité des marchés accessibles à AAAHogEx,
> en sécurisant pour OpexAI des endpoints qui appartiennent souvent aux routes AAA les plus
> profitables. AAAHogEx se redéploie ensuite et récupère une partie de son profit sur d'autres
> marchés, mais l'avantage initial d'OpexAI a déjà modifié l'accumulation de capital et le chemin de
> développement.**

Cette explication réconcilie les deux observations auparavant difficiles à faire tenir ensemble :

- le gain économique OpexAI adopté, **+11,6 % de `profit_year` à 10 ans** sur le banc officiel ;
- la faible différence finale de nombre de marchés/monopoles AAA.

La bonne métrique causale n'est donc pas seulement « combien d'aéroports AAA restent ? », mais
**quels marchés très rentables chaque IA a pu sécuriser, et à quel moment de sa trajectoire**.
