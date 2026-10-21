# V308 — cartographie par blocs : échantillonnage V307 et quinconce à 6 points

21 octobre 2026. Proposition de l'utilisateur, analyse Claude. Aucun code IA modifié.

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

## 3. Résultats — préparation du 21 octobre (mesure moteur à effectuer)

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

| Motif | Blocs analysés | Rivières traversantes manquées | Autres classes manquées | Opcodes médiane / p90 |
|---|---:|---:|---:|---:|
| `v307` (5 points) | À mesurer | À mesurer | À mesurer | À mesurer |
| `full6` (6 points toujours) | À mesurer | À mesurer | À mesurer | À mesurer |
| `short6` (saut après quatre points décisifs) | À mesurer | À mesurer | À mesurer | À mesurer |
| `parity6` (décalage des blocs impairs) | À mesurer | À mesurer | À mesurer | À mesurer |
| `flatdry6` (centres seulement si plat et sec) | À mesurer | À mesurer | À mesurer | À mesurer |

Les 16 tests géométriques, de contrat et de lecture des journaux de
`sweeps/test_v308_quinconce.py` passent ;
les 19 tests ciblés V307/V309 passent également. Aucun runtime OpenTTD, smoke ni
banc comparatif n'a été exécuté à cette étape. La comparaison réelle des motifs
reste donc **non mesurée**, et il serait prématuré de retenir un motif pour une carte
partagée. Après coordination des bancs : smoke 1×1 puis graines 42, 7 et 100 avec
`v307_probe_year=0` et `=6`, et traitement des journaux avec
`python sweeps/diag_v308_carto.py <dossier> --json <sortie.json>`.
