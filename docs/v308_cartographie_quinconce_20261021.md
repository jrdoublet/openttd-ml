# V308 — cartographie par blocs : échantillonnage V307 et quinconce à 6 points

21 octobre 2026. Proposition de l'utilisateur, analyse et sonde de mesure V308.

## 1. L'échantillonnage V307 actuel (sonde `v307_long_probe`, défaut 0)

Code : `ai/OpexAI/probe_v307.nut` (`OpexV307Block`, `OpexV307StepCost`, `OpexV307Coarse`, `OpexV307Guide`).

- **Blocs** de 8×8 tuiles (`V307_SIDE = 8`) : 1 024 blocs sur 256².
- **5 points par bloc** : centre (4,4) et quarts (2,2), (6,2), (2,6), (6,6). Sur chacun :
  `AITile.GetMaxHeight`, `AITile.IsWaterTile`, obstacle = `!IsBuildable && !AIRoad.IsRoadTile`.
  Résumé `{n, h, water, obst}`, mémorisé **le temps d'une recherche** seulement.
- **Coût d'un pas** (dixièmes de tuile) : 80 droit, 112 diagonal ; + longueur × (3·eau + 2·obstacles)/5 ;
  + 40 par niveau d'écart d'altitude moyenne. Bloc sans point valide : infranchissable.
- **A\*** 8 voisins, file `AIList` triée, heuristique octile admissible.
- **Mesures** (sondes 1973/1976, 202 recherches grossières) : opcodes ≈ 433 × blocs échantillonnés
  + 452 × nœuds développés ; à 180-220 tuiles, 266 blocs échantillonnés, 182 développés, trajet de
  17 blocs, **≈ 0,2 M opcodes, ≈ 20 ticks, ≈ 1 jour**. Corrélation coût grossier / coût réel 0,85 ;
  longueur réelle / prédite 0,87. Guidage par le couloir (×0,5 dedans, ×2 dehors) : tracé ×1,14 à
  ×1,23, pas un bon défaut.
- **Angle mort** : points sur les lignes et colonnes 2, 4, 6 seulement. Une rivière droite d'une tuile
  sur les lignes ou colonnes 0, 1, 3, 5 ou 7 traverse le bloc sans être vue. Pas de distinction
  rivière / lac / mer, ni ville / autre obstacle.

### Conversion opcodes → temps
≈ 10 000 opcodes par tick consacré (banc C67 du 23/09 : 672 k opcodes en 68 ticks) ; ≈ 18,5 ticks de
contrôleur par jour de jeu, soit ≈ 185 k opcodes par jour au plus.

| Méthode | Opcodes / bloc | Couloir de 200 tuiles |
|---|---:|---|
| V307, 5 points | ≈ 430 | 25 blocs (8 de large) ≈ 11 k ; 75 blocs (24 de large) ≈ 32 k ; A\* complet mesuré ≈ 0,2 M (≈ 1 jour) |
| C67 exhaustif 5×5 | ≈ 10 k | 120 blocs (15 de large) ≈ 1,2 M (≈ 6,5 jours) |
| C67 exhaustif 10×10 | ≈ 35 k | 40 blocs (20 de large) ≈ 1,4 M (≈ 7,6 jours) |
| C67 dans le seul reliquat | 85-760 blocs/an mesurés | 120 blocs : 2 mois à 1,4 an |

## 2. La proposition : quinconce tourné de 6 points sur le cœur 6×6

1. Cibler le cœur 6×6 (décalages 1 à 6) avec 6 points, **exactement un par ligne et par colonne
   intérieures** (quinconce tourné).
2. Sonder d'abord les 4 points périphériques (un par quadrant) et classer par court-circuit
   mer, côte, ville, montagne.
3. Ne tester les 2 points centraux que sur terrain plat et sec, pour détecter une rivière traversante.
4. Compresser le résultat dans un seul entier, en temps masqué (`AIController.GetOpsTillSuspend()`).

### Un placement qui réalise les quatre contraintes
Lignes 1 à 6 → colonnes 3, 6, 2, 5, 1, 4, soit (x, y) :

```
     x: 0 1 2 3 4 5 6 7
y=0     . . . . . . . .
y=1     . . . P . . . .      P = périphérique (quadrant)
y=2     . . . . . . P .      C = central
y=3     . . C . . . . .
y=4     . . . . . C . .
y=5     . P . . . . . .
y=6     . . . . P . . .
y=7     . . . . . . . .
```

Périphériques (3,1) haut-gauche, (6,2) haut-droite, (1,5) bas-gauche, (4,6) bas-droite ;
centraux (2,3) et (5,4). Une ligne et une colonne intérieures chacune.

### Mon avis : bonne méthode, meilleure que V307, avec trois corrections

**✅ Validé par l'utilisateur le 21/10 au soir** : méthode retenue avec les trois corrections ci-dessous (centraux lus aussi en relief, court-circuit limité aux classes décisives, décalage de parité à tester). Prochaine étape : la sonde de validation.

**Ce qui est juste**
- **Garantie de détection** : toute rivière droite d'une tuile, horizontale ou verticale, qui
  traverse le cœur 6×6 touche exactement un point. Les 5 points V307 n'en voient que la moitié
  (lignes et colonnes 2, 4, 6).
- **L'API sait classer un point en un appel** : `AITile.IsSeaTile`, `AITile.IsRiverTile`,
  `AITile.IsCoastTile`, `AITile.IsHouseTile` et `AITile.GetTownAuthority` existent en 15.3
  (`docs/noai_api_15.3.tsv`). La carte peut donc distinguer une **rivière** (franchissable par un
  pont court) d'un **lac ou de la mer** (contournement), ce que V307 confond aujourd'hui. Pour le
  rail, c'est le gain le plus utile : la rivière doit coûter un pont, pas un détour.
- **Un entier par bloc** : 1 024 entiers sur 256², 4 096 sur 512². La carte peut enfin être
  **partagée** entre candidats (tâche V307 3.3) et sauvegardée à coût faible
  (cf. coût de `Save()`, mémoire « Save : cache de projection »).
- **Temps masqué** : conforme à la règle « le reliquat nourrit des workers ». Un bloc coûte
  ≈ 250-450 opcodes contre ≈ 10 k pour C67 : avec les crochets mesurés en partie (90-780 par an),
  on lirait ≈ 10 blocs par crochet, soit environ 900 à 7 800 blocs par an. Une carte 256² serait
  couverte en 1,5 mois à 1 an selon la graine, une 512² en 6 mois à 4 ans.

**Ce que je corrigerais**
1. **Ne pas réserver les 2 points centraux au plat sec.** Les rivières d'OpenTTD descendent les
   pentes : elles sont plus fréquentes dans les blocs en relief. Sans les points centraux, les
   lignes 3-4 et les colonnes 2-5 ne sont plus couvertes, et la garantie tombe justement là.
   Court-circuiter seulement sur les classes **décisives** pour le routage : mer ou lac (≥ 2
   points d'eau non fluviale), ville (≥ 2 maisons ou autorité de ville sur ≥ 3 points), montagne
   (écart d'altitude ≥ seuil sur les 4 périphériques). Tout le reste reçoit les 6 points.
2. **Bords non vus.** Les lignes et colonnes 0 et 7 ne sont sondées par aucun bloc : une bande de
   2 tuiles entre deux blocs voisins reste aveugle, et une rivière qui la longe passe. Variante à
   tester : décaler le motif d'une tuile un bloc sur deux (parité de `bx + by`), sans coût
   supplémentaire.
3. **Le court-circuit économise peu d'opcodes au total.** Dans l'A\* grossier, la tenue de la file
   coûte autant que la lecture (≈ 450 par nœud contre ≈ 430 par bloc). Le court-circuit ne
   touche que la lecture des blocs non plats : de l'ordre de 10-15 % du total. Le vrai gain
   vient de la carte partagée, payée une fois au lieu d'une fois par candidat (0,2 M).

**Format d'entier proposé** (31 bits, sûr en Squirrel 32 bits)

| Bits | Champ |
|---|---|
| 0-2 | points valides (0-6) |
| 3-5 | points d'eau mer/lac |
| 6-8 | points de rivière |
| 9-11 | points de ville (maison ou autorité) |
| 12-14 | autres obstacles |
| 15-19 | altitude moyenne (0-31) |
| 20-24 | écart d'altitude max − min (0-31) |
| 25 | côte vue |
| 26-29 | génération (invalidation après construction ou croissance de ville) |
| 30 | bloc complet (6 points lus) ou court-circuité |

### Validation proposée (V308, tâche simple-moyenne, sans changer l'IA)
Sonde passive qui lit, pour un échantillon de blocs, les 64 tuiles **et** les deux motifs (5 points
V307, quinconce 6 points, avec et sans court-circuit, avec et sans décalage de parité). On mesure,
contre la vérité des 64 tuiles :
- le taux de rivière, lac, mer, ville et montagne **manqués** ;
- les opcodes par bloc de chaque motif ;
- l'erreur sur le coût d'un tracé grossier, rejouée hors ligne sur les paires V307.

On ne branche la carte dans une décision (devis 3.1, guidage 2.2) que si le quinconce manque
nettement moins que les 5 points pour un coût comparable. Prompt :
[`docs/prompts/v308_cartographie_quinconce_20261021.md`](prompts/v308_cartographie_quinconce_20261021.md).

## 3. Résultats moteur — smoke et campagne indépendante 3×7

La sonde `ai/OpexAI/probe_v308.nut` est branchée dans les deux boucles sous
`v308_carto_probe=1`, **désactivée par défaut aux quatre difficultés**. Elle se déclenche une
seule fois au début de l'année `OPEX_START_YEAR + v307_probe_year`, sauf après Load.
Chaque échantillon tire avec remise un bloc 8×8 intérieur, compare les 64 tuiles aux
cinq motifs, et écrit exactement une ligne `V308_BLOCK` contenant la vérité, le témoin
`t_river_cross` (connexité à quatre voisins et bords opposés), les classes détectées et
les opcodes mesurés par motif. La sonde est bloquante et n'intervient pas dans
les choix de transport. Activée, elle consomme cependant du temps de jeu et des
tirages aléatoires, ce qui peut indirectement modifier la trajectoire d'une partie.

Le script `sweeps/diag_v308_carto.py` calcule par motif le taux de classes manquées,
les faux positifs et la médiane / p90 des opcodes. Une rivière vue par un point
est un **indice** pour `river_cross`, non une preuve qu'elle traverse tout le bloc ;
la vérité complète suit les composantes connexes des 64 tuiles. Les classes de ville
incluent la règle de sélection : deux maisons vues ou autorité valide sur trois points.

**Méthode de lecture.** Les valeurs `t_*` proviennent des 64 tuiles. `river_cross`
est une composante fluviale qui touche deux bords opposés du même bloc : les
échantillonneurs ne connaissent pas la connexité de la rivière, et le diagnostic
compte `motif_river>0` comme *signal de présence* (donc faux positifs possibles).
`mountain` correspond à un relief `max−min >= 4` dans les points lus ; ce n'est
pas une classification officielle des montagnes. `city` est une règle de seuil
(≥2 maisons ou ≥3 points avec autorité de ville) ; une autorité administrative
valide ne prouve pas la présence de bâti. Le motif V307 testé relit les mêmes
champs `IsSeaTile` / `IsRiverTile` / etc. que les autres motifs, contrairement
au noyau simplifié de `OpexV307Block` décrit en §1 : **les opcodes ne sont pas
ceux de l'algorithme V307 de production**. Les 400 blocs sont tirés *avec remise* :
les taux sont descriptifs, sans prétendre à 400 blocs distincts.

### Smoke 1×1 — 1970, graine 42, résultat complet

Campagne `v308_smoke_fix1_1x1_20261021`, bundle du worktree propre
`results/v308_bench_clean_20261021`. Le bras `reference` a la sonde OFF,
aucun `V308_BLOCK` ; le bras `v308` possède exactement **400 `V308_BLOCK`**,
400 indices `i` distincts (0..399), `t_n=64` sur chaque ligne, un `V308_START`
et un `V308_END`, **aucune erreur Squirrel**. Toutes les valeurs suivantes
proviennent donc du **bras variant sondé**, et comparent les cinq motifs *sur les
mêmes 400 blocs*. Aucun écart économique entre parties ne peut être attribué à
un motif : la sonde est bloquante et avance le générateur aléatoire.

| Motif | Traversées fluviales manquées (sur 18) | Faux signaux de traversée (sur 382 négatifs) | Rivière présente manquée (sur 46) | Mer manquée (sur 93) | Ville (seuil) manquée (sur 248) | Relief ≥4 manqué (sur 24) | Opcode méd. / p90 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `v307` | 6 (33,3 %) | 18 (4,7 %) | 16 (34,8 %) | 15 (16,1 %) | 64 (25,8 %) | 20 (83,3 %) | 944 / 949 |
| `full6` | **3 (16,7 %)** | 19 (5,0 %) | **12 (26,1 %)** | 16 (17,2 %) | 46 (18,5 %) | 19 (79,2 %) | 1 154 / 1 160 |
| `short6` | **3 (16,7 %)** | 19 (5,0 %) | **12 (26,1 %)** | 16 (17,2 %) | 52 (21,0 %) | 20 (83,3 %) | 815 / 1 176 |
| `parity6` | 4 (22,2 %) | 17 (4,5 %) | 15 (32,6 %) | **14 (15,1 %)** | **42 (16,9 %)** | 20 (83,3 %) | 1 161 / 1 166 |
| `flatdry6` | 4 (22,2 %) | 17 (4,5 %) | 15 (32,6 %) | 16 (17,2 %) | 71 (28,6 %) | 21 (87,5 %) | **802 / 1 168** |

Dans cette mesure, `full6` coûte +22,2 % d'opcodes médians par rapport aux cinq
points V307 et divise par deux les omissions des traversées (6 → 3).
`short6` conserve les trois traversées manquées et passe à 815 opcodes médians
(−13,7 %), mais son p90 de 1 176 traduit le coût du test et du branchement
quand les deux centres sont finalement lus. Les centres sont sautés dans
216/400 blocs pour `short6`, 308/400 pour `flatdry6`.

**Autres classes du smoke**, omissions exprimées en nombre de blocs réellement
positifs : côte (68) : `v307/full6/short6/parity6/flatdry6` =
33/33/38/33/38 ; maisons (60) = 37/26/30/30/29 ; autorité de ville (260) =
30/32/32/30/32 ; obstacles (52) = 33/33/35/36/37.
Le lac n'est présent dans **aucun** des 400 blocs ; un taux de manque pour le
lac n'est donc **pas estimable**. Les autres classes ordinaires n'ont aucun faux
positif dans ce smoke (chaque point lu appartient aux 64 tuiles du bloc).

Lecture immédiate : le quinconce six points est un candidat pour une *détection
rapide* des rivières et villes, surtout en version court-circuitée. **Il ne
reconstruit pas les traversées fluviales**, conserve des angles morts importants
sur la montagne, et le gain statistique du smoke repose sur seulement 18
traversées vraies. Pas de promotion en carte partagée à ce stade.

Commande :

```powershell
python -X utf8 sweeps/diag_v308_carto.py results/v308_bench_clean_20261021/results/v308_smoke_fix1_1x1_20261021_engine/v308_seed42_r0.log
```

### Campagne 3×7 — V308 année 0 contre année 6

Campagne `v308_carto_3x7_20261021`, même worktree propre, graines 42/7/100,
référence `OpexAI[v308_carto_probe=1]` (année 0), variante
`OpexAI[v308_carto_probe=1,v307_probe_year=6]` (année 6), horizon 7 ans.
Le JSON final atteste **6/6 parties terminées et saines**, 3/3 paires,
`comparison_complete=true`, `adoption_sample_complete=true`,
`metric_coverage_complete=true`. Les six journaux ont chacun un
`V308_START`, 400 `V308_BLOCK` complets et uniques, un `V308_END`, et
**zéro erreur Squirrel**. Le manifeste confirme le commit propre
`ccd2e9311ced40b9929fbe5240355eb775d00721`, bundle
`e30f3cb34aa54a5fc27d7aec29d9c3237ec96a68afd0fb29ceaa719d88acad5d`,
et le seul paramètre différent `v307_probe_year: 0 → 6`.

**Dates observées et censure temporelle :** les trois `reference` déclenchent
la sonde le **1er janvier 1970** et la terminent le **11 février 1970**.
À l'année 6, les démarrages/terminaisons sont **1er janvier → 10 février 1976**
(graine 100), **5 janvier → 15 février** (42), et **2 février → 14 mars** (7).
Une exécution de la sonde exhaustive 64 tuiles + cinq motifs occupe donc
environ **40–41 jours de simulation**, pas un seul tour ni une mesure masquée.
La condition d'année est un seuil minimal : l'IA peut atteindre ce seuil
plusieurs semaines après le 1er janvier. Les cinq motifs sont évalués
séquentiellement dans chaque bloc, mais les deux campagnes correspondent à
des états du monde et périodes différentes : les taux restent séparés.
Toutes les observations se déroulent en **hiver (janvier à mars)** ; aucune
autre saison n'est mesurée ici.

#### Bras `reference` : année 0, 3 × 400 = 1 200 blocs

La vérité contient **66 blocs avec rivière traversante**, 145 avec rivière,
241 avec mer, 753 selon le seuil de ville, 68 avec relief ≥4, et aucun lac.

| Motif | Traversées manquées / 66 | Faux signaux / 1 134 négatifs | Rivière présente manquée / 145 | Mer manquée / 241 | Ville manquée / 753 | Montagne manquée / 68 | Opcodes méd. / p90 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `v307` | 15 (22,7 %) | 32 (2,8 %) | 62 (42,8 %) | 44 (18,3 %) | 210 (27,9 %) | 45 (66,2 %) | 944 / 949 |
| `full6` | **8 (12,1 %)** | 37 (3,3 %) | **50 (34,5 %)** | 44 (18,3 %) | 173 (23,0 %) | 51 (75,0 %) | 1 154 / 1 160 |
| `short6` | 10 (15,2 %) | 34 (3,0 %) | 55 (37,9 %) | 44 (18,3 %) | 183 (24,3 %) | 53 (77,9 %) | 818 / 1 176 |
| `parity6` | 11 (16,7 %) | 35 (3,1 %) | 55 (37,9 %) | **40 (16,6 %)** | **164 (21,8 %)** | 48 (70,6 %) | 1 161 / 1 166 |
| `flatdry6` | 11 (16,7 %) | 30 (2,6 %) | 60 (41,4 %) | 46 (19,1 %) | 235 (31,2 %) | 54 (79,4 %) | **802 / 1 168** |

Autres classes, omissions par motif dans l'ordre `v307/full6/short6/parity6/flatdry6` :
côte (200) **88/69/88/78/90** ; maisons (182) **111/95/110/105/105** ;
autorité de ville (792) **91/95/95/102/96** ; obstacles (142)
**91/85/88/89/94**. Aucun faux positif ordinaire ; aucun lac à comparer.

#### Bras `y6` : année 6, 3 × 400 = 1 200 blocs

La vérité contient **67 blocs avec rivière traversante**, 153 avec rivière,
234 avec mer, 748 selon le seuil de ville, 66 avec relief ≥4, et aucun lac.

| Motif | Traversées manquées / 67 | Faux signaux / 1 133 négatifs | Rivière présente manquée / 153 | Mer manquée / 234 | Ville manquée / 748 | Montagne manquée / 66 | Opcodes méd. / p90 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `v307` | 12 (17,9 %) | 34 (3,0 %) | 64 (41,8 %) | 43 (18,4 %) | 207 (27,7 %) | 38 (57,6 %) | 944 / 949 |
| `full6` | **6 (9,0 %)** | 44 (3,9 %) | **48 (31,4 %)** | 44 (18,8 %) | 172 (23,0 %) | 47 (71,2 %) | 1 154 / 1 160 |
| `short6` | 7 (10,4 %) | 39 (3,4 %) | 54 (35,3 %) | 44 (18,8 %) | 181 (24,2 %) | 49 (74,2 %) | 821,5 / 1 176 |
| `parity6` | 11 (16,4 %) | 41 (3,6 %) | 56 (36,6 %) | 43 (18,4 %) | **162 (21,7 %)** | **42 (63,6 %)** | 1 161 / 1 166 |
| `flatdry6` | 9 (13,4 %) | 35 (3,1 %) | 60 (39,2 %) | 45 (19,2 %) | 234 (31,3 %) | 51 (77,3 %) | **802 / 1 167** |

Autres classes, omissions dans le même ordre : côte (196)
**99/72/91/83/95** ; maisons (230) **149/130/153/131/144** ;
autorité de ville (785) **93/96/96/104/97** ; obstacles (742)
**222/163/189/168/213**. Aucun faux positif ordinaire ; aucun lac à comparer.
Les différences du volume d'obstacles reflètent aussi l'évolution du monde
entre 1970 et 1976 : ces deux bras ne mesurent pas une variation causale de la
qualité du motif à géographie constante.

#### Robustesse par graine et décision

Les omis `river_cross` par graine 42/7/100 sont respectivement :

| Motif | Année 0 (18 / 30 / 18 traversées) | Année 6 (18 / 31 / 18 traversées) |
|---|---|---|
| `v307` | 6 / 3 / 6 | 6 / 2 / 4 |
| `full6` | **3 / 2 / 3** | **3 / 1 / 2** |
| `short6` | 3 / 2 / 5 | 3 / 1 / 3 |
| `parity6` | 4 / 3 / 4 | 4 / 4 / 3 |
| `flatdry6` | 4 / 3 / 4 | 4 / 2 / 3 |

Le motif **`full6`** atteint le plus faible nombre d'omissions de traversées
à chaque époque, avec un coût médian de **1 154 opcodes** (+22,2 % contre
les 944 du motif V307 relu avec les mêmes API). Il reste cependant 8/66
et 6/67 traversées manquées, ainsi que des faux signaux. Le **`short6`** est
le meilleur candidat *coût/couverture pour un futur cache partagé* :
10/66 et 7/67 traversées manquées avec 818/821,5 opcodes médians
(−13,3 %/−13,0 % contre V307), mais il manque davantage de côtes, maisons,
obstacles et reliefs que `full6`, et son p90 remonte à 1 176.
Sur la graine 7, le `short6` coûte 1 171 / 1 172 opcodes médians aux années
0 / 6 : l'économie de court-circuit n'est pas uniforme entre les graines.
**La médiane masque le coût réel du court-circuit** : sur les 1 200 blocs de
l'année 0, `short6` totalise **1 184 714 opcodes** contre **1 131 594**
pour `v307` (+4,7 %) ; à l'année 6, **1 188 402** contre **1 131 647**
(+5,0 %). Les centres sont sautés sur 611/1 200 puis 601/1 200 blocs.
Sur le smoke de 400 blocs, les cinq motifs représentent à eux seuls
**2 055 027 opcodes mesurés** (dont 390 041 pour `short6` et 376 975
pour `v307`), hors balayage exhaustif, connexité, logs et pilotage de la
sonde. Les **40–41 jours** observés ne doivent donc pas être imputés à un
seul motif. `short6` reste moins cher que `full6`, mais **ne constitue
pas une économie moyenne d'opcodes face au V307 mesuré**.
Le `parity6` n'améliore pas systématiquement les rivières et n'est pas retenu
en priorité.
Le `flatdry6` est économique à la médiane mais perd nettement en classification
des villes et des montagnes. **Aucun motif n'est implanté dans une politique
de routage à l'issue de cette simple mesure passive.**

Le résultat économique du duel *année 6 − année 0* est Δ `profit_year`
**+16 778,3 £/an** en moyenne, IC95 bootstrap **[−885 975 ; +722 245]**,
2 victoires / 1 défaite, verdict `fail_primary` du harnais. Ce chiffre reflète
le calendrier et les effets de la sonde (40–41 jours bloquants, tirages RNG,
réseau et concurrence divergents), **et ne compare pas l'adoption des cinq
motifs**. La valeur de compagnie est également sensible à ces trajectoires.
L'effet d'un cache cartographique partagé sur le coût par projet, les délais
d'A*, les ponts, la rentabilité et le résultat contre AAAHogEx reste à vérifier
séparément avant tout changement de comportement ou de réglage par défaut.

Reproduction sans nouveau banc :

```powershell
$engine = 'results/v308_bench_clean_20261021/results/v308_carto_3x7_20261021_engine'
python -X utf8 sweeps/diag_v308_carto.py "$engine/reference_seed42_r0.log" "$engine/reference_seed7_r0.log" "$engine/reference_seed100_r0.log"
python -X utf8 sweeps/diag_v308_carto.py "$engine/y6_seed42_r0.log" "$engine/y6_seed7_r0.log" "$engine/y6_seed100_r0.log"
python -X utf8 -m unittest sweeps.test_v308_quinconce -q
```

Les **18 tests V308** passent et le diagnostic est fondé sur les journaux du
bundle gelé, sans lancement supplémentaire de Docker. Le rapport est complet
pour cette mesure V308 3×7 et prêt à être publié, avec les limites ci-dessus.
