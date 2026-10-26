# MULTI-1 — localisation du décrochage 1975–1979 (analyse sans nouveau banc)

**Complément descriptif du 26 octobre 2026**, après trois pilotes non exposés.
La cible stratégique MULTI-1 est **≥75 %** du `profit_year` moyen d'AAAHogEx
sur 20 graines × 10 ans en partie multimodale. Cette analyse utilise **une
campagne déjà terminée**, sans relancer de simulation ni changer la politique.

## Source et limites d'attribution

`results/nuit75_master83e_baseline20x10_20261024.{json,jsonl,manifest.json}` :
20 duels 1970–1979, carte 256², source historique master `83e436cc` (et non
HEAD courant `2bfc118f`). Les **40 compagnies de `summary` terminent 1979** ;
les **4 800 snapshots** JSONL couvrent 120 dates mensuelles ×40 compagnies.
Chaque ligne du tableau retient exclusivement le **1er décembre de l'année**,
pour 20 OpexAI et 20 AAAHogEx, sans additionner les snapshots d'une même année.
`profit_year` assemble **3 trimestres valides en 1970** puis **4 trimestres
valides chaque année de 1971 à 1979** sur les 40 compagnies ; les
véhicules par mode sont les moteurs principaux dédupliqués. La **trésorerie est
un stock en décembre**, ni un financement contrefactuel ni un CAPEX cumulé.
Les logs `*_engine/*.log` de cette archive sont vides : aucune observation
fiable de `PROJECT_CHOSEN` ou `ROAD_BUILD` ne peut être ajoutée a posteriori.
Les deux IA jouent sur la même carte dans chaque duel, mais aucune comparaison
de modes n'isole l'effet causal d'un investissement donné.

## Chronologie des vingt mondes, même cohorte

| Décembre | Profit Opex moyen (£/an) | Profit AAA moyen (£/an) | Opex/AAA | Avions Opex/AAA | Trains Opex/AAA | Véhicules ROUTE Opex/AAA |
|---|---:|---:|---:|---:|---:|---:|
| 1970 | 351 307 | 315 663 | 111,29 % | 11,6 / 12,4 | 0,0 / 0,2 | 0,0 / 0,5 |
| 1971 | 1 411 184 | 1 476 261 | 95,59 % | 35,1 / 24,2 | 3,4 / 5,5 | 3,3 / 40,1 |
| 1972 | 2 104 034 | 2 049 717 | 102,65 % | 52,3 / 31,2 | 13,2 / 12,1 | 4,4 / 106,4 |
| 1973 | 2 406 725 | 2 545 797 | 94,54 % | 67,4 / 38,9 | 21,6 / 20,1 | 4,6 / 135,8 |
| 1974 | 2 699 696 | 3 087 412 | 87,44 % | 83,0 / 42,1 | 25,6 / 29,3 | 4,7 / 142,6 |
| 1975 | 2 995 362 | 4 021 534 | **74,48 %** | 91,7 / 42,5 | 27,6 / 36,0 | 4,7 / 150,7 |
| 1976 | 3 275 085 | 4 895 759 | 66,90 % | 100,5 / 45,0 | 28,5 / 45,4 | 4,8 / 153,5 |
| 1977 | 3 594 101 | 5 904 910 | 60,87 % | 105,0 / 49,5 | 29,3 / 51,6 | 4,8 / 159,3 |
| 1978 | 3 836 538 | 6 465 082 | 59,34 % | 110,7 / 52,1 | 29,8 / 54,6 | 4,8 / 162,5 |
| 1979 | **4 122 708** | **7 290 134** | **56,55 %** | **114,0 / 52,5** | **30,4 / 60,9** | **4,5 / 166,3** |

En **1975** — un an seulement après la porte A MULTI-1 fixée à fin 1974 —
le ratio passe sous la cible de 75 %, puis décroche jusqu'à **56,55 %**.
La médiane des ratios par graine en 1979 est **58,91 %** et **aucun des vingt
duels** n'a un profit final Opex supérieur à AAA. À adversaire inchangé, il
manquerait **≈1 344 893 £/an** de profit Opex en 1979 pour atteindre 75 %.

Fin 1979, Opex détient en moyenne **14,90 M£ de trésorerie** (contre 21,98 M£
chez AAA). Déjà en 1975, Opex détient 2,99 M£ et AAA 2,82 M£ : la simple
hypothèse « Opex n'a plus d'argent pour bâtir après 1974 » n'explique pas
l'ensemble du décrochage. Opex augmente fortement ses avions **114 contre 52,5**
chez AAA, tandis que les trains stagnent autour de 30 dès 1976 et que la flotte
routière demeure autour de 5. AAA continue à étendre train et ROUTE.

## Implications **non causales** pour le prochain essai

1. **H1 — captation précoce du capital par RAIL** : non confirmée en 1970
   (voir [analyse 40×5](multi1_analyse_20261026.md)) ; encore moins une
   explication suffisante de la stagnation à caisse élevée de 1975–1979.
   Vérifier flux d'investissement et projets effectivement financés avant un
   nouveau garde-capital, plutôt que couper arbitrairement RAIL.
2. **H2 — opcodes/ticks** : les panneaux montrent des coûts, pas l'ensemble
   de la ressource ni le délai causal vers une nouvelle construction. Les
   anciens essais V100 de simple réallocation du créneau RAIL ont montré une
   absorption du temps libéré par d'autres recherches échouées ; éviter de
   répéter cette famille sans preuve nouvelle.
3. **H3 — diversification AAA** : la flotte AAA, notamment ROUTE, croît
   beaucoup plus. Mais **166 véhicules ne valent pas 166 lignes rentables**.
   Le rabattement bus V139 a déjà échoué à sa porte A 40×5 (voir
   `docs/taches.md`, V139/V242) : ne pas en déduire qu'imiter les bus AAA
   rapportera le déficit de 1,34 M£/an. Mesurer la contribution marginale
   réelle par mode et le sort des candidats finançables avant un quatrième
   prototype économique.

Contrôle complémentaire sur les **journaux déjà disponibles** de la campagne
`multi1_roaddetour_exposure_5x5_20261026`, bras référence `probes=258` :
**12 `ROAD_BUILD`**, profit annuel **prédit** total **65 702 £ sur les cinq
mondes** (médiane par construction **4 056 £**) ; parmi les rejets ROAD
journalisés, 59 `plan_failed` dont 58 `detail=TRACEX`, 12
`town_already_bus_served`, 1 `abandoned_pair`, 1 `src_origin_served`.
Le nombre de tentatives n'est pas celui de candidats uniques ; les profits
prédits ne sont ni réalisés ni additifs sans chevauchement/cannibalisation.
Mais le volume d'opportunités observées ne justifie **pas** de supposer qu'un
simple assouplissement du plafond de lignes bus résoudra le manque de
1,34 M£/an. Le troisième pilote de détours n'a sauvé aucune construction.

**Contrainte de protocole :** la porte A MULTI-1 est pré-enregistrée à **5 ans**,
alors que l'écart sous 75 % apparaît en **année 6** sur cette cohorte. Un
levier qui n'agit qu'à partir de 1975 serait **non exposé à A**, même s'il
répondait exactement à la perte tardive ; son éventuelle étude exigerait un
nouveau pré-enregistrement explicitement distinct, sans maquiller A40×5 ni
rouvrir les trois `NO-GO_NON_EXPOSE`. Ne pas modifier P1/VPS, P6 ni
LATE-GAME-1 pour contourner cette tension.
