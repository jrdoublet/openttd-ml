# Diagnostic 5 ans : graines 512 et 1337, RAIL seul et AIR seul contre AAAHogEx

**31 octobre 2026 — 4 duels partagés OpenTTD 15.3, OpenGFX 7.1, 256²,
1970–1974.** Demandes : rejouer la pire graine relative à dix ans (512)
en RAIL seul puis AIR seul ; étendre le même protocole à la pire graine
en déficit absolu (1337).

## Protocole

Chaque expérience est une **partie partagée**, avec OpexAI (compagnie 0)
et AAAHogEx-115 (compagnie 1) jouant ensemble sur la même carte :

- Graines **512 et 1337**, chacune avec deux parties séparées.
- **RAIL seul** : `mode_air=0, mode_road=0, mode_water=0, mode_rail=1`.
- **AIR seul** : `mode_air=1, mode_road=0, mode_water=0, mode_rail=0`.
- Tous les autres paramètres OpexAI restent **aux défauts publiés**
  d'ESTIM-31 à la révision `545affe3168d8a73bcd4111af4473425bef3b99a`
  de `origin/master` ; aucune réparation opt-in activée.
- Adversaire **AAAHogEx-115**, version locale inchangée, identique
  dans les quatre parties. NoAI `Queue.FibonacciHeap` et
  `Pathfinder.Rail` proviennent du bundle local figé, dont chaque
  fichier est vérifié SHA256 avant exécution.
- OpenTTD 15.3 / OpenGFX 7.1 ; densité des villes 3, industries 4,
  croissance des villes 2, inflation OFF, 1 répétition. Quatre workers
  au maximum dans un conteneur unique.
- `profit_year` correspond à la somme des quatre trimestres clos ;
  lecture décisive au snapshot du **1er décembre 1974**. Les ratios
  Opex/AAA sont calculés **dans le même duel** (ne pas importer
  l'adversaire d'une autre partie).

**Santé :** quatre jeux de 60 mois, **480 lignes de compagnie** (2 sociétés
par mois), aucun mois manquant, 8/8 séries avec compagnies présentes,
`VEHS`/`STNN` valides et zéro erreur de script ; 8/8 `profit_year`
finaux à couverture complète.

## Résultats 1974

| Graine | Mode OpexAI | Profit OpexAI (£/an) | Profit AAAHogEx (£/an) | Opex/AAA | Retard OpexAI (£/an) |
|---|---|---:|---:|---:|---:|
| **512** | **RAIL seul** | 1 051 209 | 2 232 180 | **47,0934 %** | −1 180 971 |
| **512** | **AIR seul** | 2 381 660 | 2 949 351 | **80,7520 %** | −567 691 |
| **1337** | **RAIL seul** | 902 190 | 3 333 683 | **27,0629 %** | −2 431 493 |
| **1337** | **AIR seul** | 2 033 991 | 3 146 793 | **64,6369 %** | −1 112 802 |

En profit OpexAI **absolu**, le changement RAIL→AIR améliore
les résultats de **+1 330 451 £/an** pour 512 et
**+1 131 801 £/an** pour 1337. Les écarts relatifs
Opex/AAA progressent respectivement de **+33,66** et
**+37,57 points**. Cette observation n'est **pas** un effet
causal isolé, car AAAHogEx adapte son activité à chaque adversaire.

### Trajectoire annuelle du rapport de profit OpexAI / AAAHogEx

| Année | 512 RAIL seul | 512 AIR seul | 1337 RAIL seul | 1337 AIR seul |
|---|---:|---:|---:|---:|
| 1970 | 81,20 % | 178,20 % | 17,10 % | 97,07 % |
| 1971 | 72,04 % | 270,14 % | 32,60 % | 76,00 % |
| 1972 | 64,43 % | 224,38 % | 28,81 % | 81,34 % |
| 1973 | 59,81 % | 100,68 % | 30,00 % | 77,11 % |
| 1974 | **47,09 %** | **80,75 %** | **27,06 %** | **64,64 %** |

Les deux parties AIR seul décrochent par rapport au profit de
l'adversaire en fin de période, mais elles conservent une avance
marquée sur RAIL seul. La graine 1337 est particulièrement difficile
pour le chemin ferroviaire dès 1970.

### Réseaux OpexAI au 1er décembre 1974

| Graine / mode | Flotte OpexAI | Infrastructures | Valeur de société (£) |
|---|---|---|---:|
| 512 RAIL | 38 trains, 0 avion | 65 gares ferroviaires | 1 594 995 |
| 512 AIR | 85 avions, 0 train | 33 aéroports | 4 521 428 |
| 1337 RAIL | 36 trains, 0 avion | 60 gares ferroviaires | 1 593 792 |
| 1337 AIR | 83 avions, 0 train | 40 aéroports | 5 299 748 |

Le décodeur STNN signale également des quais ou arrêts de bus joints
aux gares ou aéroports, mais le décodeur VEHS confirme **0 véhicule
routier OpexAI** dans les quatre parties. Le nombre
`stations_by_facility` n'est pas une somme additive de gares uniques.

### Réaction du concurrent

À la graine **1337**, AAAHogEx utilise **194 véhicules routiers**
et 26 trains face à OpexAI RAIL seul, contre **122 véhicules
routiers** et 38 trains face à AIR seul ; sa flotte aérienne
passe respectivement de 56 à 36 appareils. À la graine **512**,
AAAHogEx utilise **112 véhicules routiers, 16 trains, 45 avions**
face au RAIL seul, contre **68 routiers, 42 trains, 26 avions**
face à AIR seul. Les profits AAAHogEx diffèrent entre les deux
duels d'une même graine : ce sont deux **marchés concurrentiels
endogènes** et non un seul adversaire immobile.

## Limites et suite

Ce **diagnostic ciblé sur deux graines** donne un indice utile :
le rail seul sous-performe nettement l'air seul, particulièrement
sur 1337. Il ne constitue pas une qualification sur 40 graines,
ne mesure pas une synergie AIR+RAIL, et ne dit pas quelle
branche de l'estimation `estim_unifie=31` cause cet écart.
Les ratios de ce **banc 1974** ne sont pas à comparer directement
au classement multimodal **1979** qui a sélectionné 512 et 1337.

**Archives :**
- Source JSON complète, sous `results/` (ignorée par Git) :
  `seeds512_1337_rail_air_only_vs_aaa_5y_20261031.json`,
  SHA256 `1a4d3899929fd81c6e1a2a6814f580333cabaf0e3f8bad55f55a7632c42fcad8`.
- Checkpoints bruts 480 lignes : même préfixe, `.jsonl` ; SHA256
  `201f1644542cab7a8c8bbfa4f81f2c81d6acc953a190b25b3f456b1660611dff`.
- [Résumé structuré et trajectoires](seed512_1337_rail_air_vs_aaa_5y_20261031_results.json)
  archivé dans `docs/`.
- Reproduction : `sweeps/diag_seeds512_1337_modes_vs_aaa_5y_20261031.py`,
  un volume monté sur `/work` plus
  AAAHogEx-115 local monté en lecture seule sur `/opponent` avec
  `OPEX_AAAHOGEX_DIR=/opponent`.
