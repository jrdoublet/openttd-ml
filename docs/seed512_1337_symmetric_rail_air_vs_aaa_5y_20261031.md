# Duel strict : OpexAI vs AAAHogEx-115 — AIR/AIR et RAIL/RAIL, 512 et 1337

## Correction du protocole, 31 octobre 2026

L'expérience précédente avait comparé OpexAI monomodal à **AAAHogEx
multimodal**. Cela ne répondait pas à la demande. Sa documentation est
désormais explicitement marquée **asymétrique, à ne pas utiliser** pour
ce diagnostic. Le présent banc est une **nouvelle exécution indépendante**.

Les deux compagnies jouent **ensemble sur la même carte** :

- **RAIL/RAIL** : OpexAI `mode_rail=1`, `mode_air=0`,
  `mode_road=0`, `mode_water=0`. AAAHogEx-115 :
  `disable_veh_train=0`, `disable_veh_roadveh=1`,
  `disable_veh_tram=1`, `disable_veh_ship=1`,
  `disable_veh_aircraft=1`.
- **AIR/AIR** : OpexAI `mode_air=1`, `mode_rail=0`,
  `mode_road=0`, `mode_water=0`. AAAHogEx :
  `disable_veh_train=1`, `disable_veh_roadveh=1`,
  `disable_veh_tram=1`, `disable_veh_ship=1`,
  `disable_veh_aircraft=0`.

Pour les deux graines **512 et 1337**, simulation complète **1970–1974**
avec OpenTTD **15.3**, OpenGFX **7.1**, carte **256²**, inflation OFF,
densité des villes 3, industries 4, croissance urbaine 2.
Un seul conteneur, 4 workers, 1 répétition. Pas de changement du
défaut OpexAI ESTIM-31 ; code source figé à `1ed675a95b3767e960cab9aec2985601dafdfcda`.
Même AAAHogEx-115 local et bibliothèques NoAI gelées vérifiées SHA256.

**Contrôle strict des deux IA :** 4 jeux × 60 mois, **480 enregistrements
de compagnie**, 8/8 séries complètes, compagnies et chunks physiques
`VEHS` et `STNN` valides sur **tous** les relevés, zéro erreur script.
Sur **480/480 relevés**, le nombre de véhicules des modes interdits
(`rail`, `road`, `air`, `water`) est strictement **zéro** pour
OpexAI **et** AAAHogEx. Chacune possède en fin de jeu des véhicules
du mode autorisé. Les arrêts de bus/truck éventuellement joints
à des stations ne sont **pas** des véhicules routiers.

## Résultats au 1er décembre 1974

La mesure `profit_year` est la somme des quatre derniers trimestres
clos. Chaque ratio utilise les deux sociétés **du même duel**, sans
combiner AAAHogEx d'une autre exécution.

| Graine | Comparaison | Profit OpexAI (£/an) | Profit AAA (£/an) | Ratio Opex/AAA | Écart Opex−AAA (£/an) |
|---|---|---:|---:|---:|---:|
| **512** | **RAIL/RAIL** | **897 756** | **2 812 304** | **31,9224 %** | −1 914 548 |
| **512** | **AIR/AIR** | **1 894 990** | **1 116 654** | **169,7025 %** | +778 336 |
| **1337** | **RAIL/RAIL** | **1 053 661** | **2 294 598** | **45,9192 %** | −1 240 937 |
| **1337** | **AIR/AIR** | **1 988 125** | **2 185 660** | **90,9622 %** | −197 535 |

Ainsi **OpexAI dépasse nettement AAAHogEx en AIR sur 512**,
et manque de peu l'égalité en AIR sur 1337. Dans le rail, OpexAI
ne produit que **32 % et 46 %** environ du profit d'AAAHogEx,
respectivement. Les deux graines présentent donc un handicap
ferroviaire beaucoup plus marqué qu'aérien, au même mode.

### Réseaux monomodaux réellement mesurés

| Graine / mode | Véhicules Opex / AAA | Gares RAIL ou aéroports Opex / AAA | Valeur Opex / AAA (£) |
|---|---:|---:|---:|
| 512 RAIL/RAIL | **39 / 52 trains** | 61 / 47 gares ferroviaires | 1 629 122 / 3 168 083 |
| 512 AIR/AIR | **77 / 52 avions** | 28 / 40 aéroports | 3 622 379 / 3 483 682 |
| 1337 RAIL/RAIL | **53 / 58 trains** | 78 / 52 gares ferroviaires | 1 875 520 / 2 360 317 |
| 1337 AIR/AIR | **70 / 62 avions** | 26 / 54 aéroports | 4 521 493 / 6 162 316 |

Le rail d'OpexAI construit **davantage de gares mais moins de trains**
qu'AAAHogEx sur ces deux cartes, avec beaucoup moins de profit.
Cela suggère d'étudier le capital immobilisé, le nombre de trains
actifs par liaison et les possibilités de réemploi des gares. Ce
n'est pas encore une preuve de mauvaise construction ou d'une
cause unique.

### Trajectoire annuelle du ratio OpexAI / AAAHogEx

| Année | 512 RAIL/RAIL | 512 AIR/AIR | 1337 RAIL/RAIL | 1337 AIR/AIR |
|---|---:|---:|---:|---:|
| 1970 | 129,89 % | 116,21 % | 95,10 % | 91,15 % |
| 1971 | 74,23 % | 95,60 % | 89,77 % | 56,07 % |
| 1972 | 44,52 % | 125,02 % | 51,71 % | 60,89 % |
| 1973 | 35,50 % | 143,04 % | 51,21 % | 76,97 % |
| 1974 | **31,92 %** | **169,70 %** | **45,92 %** | **90,96 %** |

Sur 512, le retard ferroviaire apparaît dès 1971 et s'amplifie
entre 1972 et 1974. Le réseau aérien dépasse l'adversaire
à partir de 1972. Sur 1337, le rail reste très en dessous
à partir de 1972 ; l'air se rapproche d'AAAHogEx en 1974.

## Portée et traçabilité

Ces **deux graines sont sélectionnées après le résultat du banc
multimodal à 10 ans**. Les quatre duels monomodaux sont des
diagnostics descriptifs, **pas une porte A** ni une démonstration
généralisable de gains à 40 graines. Le concurrent s'adapte
à la compétition ; chaque ratio est propre à sa partie.
Aucun réglage par défaut n'est modifié.

- Code reproductible : `sweeps/diag_seeds512_1337_symmetric_modes_vs_aaa_5y_20261031.py`.
- Jeu JSON local : `results/seeds512_1337_symmetric_rail_air_vs_aaa_5y_20261031.json`,
  SHA256 **`a4842ac015e21a9f4a4cd781dca4ea8783b4d9625a8fd47aeee9b2d2b996cbbc`**.
- Relevés mensuels JSONL locaux : même préfixe `.jsonl`,
  SHA256 **`622f34dfc7b20d048d5488f30524c9f7e7596f5415bab1723f4093ad54c3a46e`**.
- [Résumé et contrôle physique versionnés](seed512_1337_symmetric_rail_air_vs_aaa_5y_20261031_results.json).
- AAAHogEx-115 est monté en lecture seule sur `/opponent` dans
  Docker et passé au lanceur via
  `OPEX_AAAHOGEX_DIR=/opponent`. L'exécution utilise le même
  source OpexAI et les mêmes deux dépendances NoAI figées que
  le banc précédent ; les paramètres de désactivation par mode
  ne sont appliqués qu'à **AAAHogEx**.
