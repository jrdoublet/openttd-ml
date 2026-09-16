# AIR — qualité de service et demande captée OpexAI vs AAAHogEx

**Date : 2026-09-15.**
**Statut : diagnostic passif 5×6 terminé.**

Cette analyse prolonge la comparaison ligne par ligne de
08_opex_vs_aaahogex_same_markets.md. Le constat précédent était :

- OpexAI ouvre davantage de marchés AIR ;
- OpexAI reste presque toujours à un avion par marché ;
- AAAHogEx obtient beaucoup plus de profit par véhicule et par unité de capacité.

L'hypothèse testée ici était une boucle auto-entretenue :

> peu d'avions → faible fréquence → mauvais rating → peu de cargo capté →
> faible stock en attente → refus W → toujours peu d'avions.

## 1. Extension passive

Le harness C66 lit désormais, pour chaque endpoint et chaque cargo réellement
transporté par une ligne :

- rating ;
- time_since_pickup ;
- max_waiting_cargo ;
- le statut rated ;
- la tuile de la station.

La source est exclusivement STNN.goods, reliée aux lignes reconstruites via
ORDL/ORDR + STNN + VEHS.

Précisions :

- rating n'est retenu que si le cargo a déjà été ramassé (status & 1) et si
  time_since_pickup < 255 ;
- max_waiting_cargo est le **maximum atteint depuis le dernier recalcul de
  note**, pas le stock instantané ;
- aucun revenu ni running cost de ligne n'est reconstruit ;
- le profit est toujours le profit VEHS des véhicules présents au checkpoint.

Fichiers :

- campagne : results/diag_air_service_quality_5x6_v1.json ;
- analyse : results/diag_air_service_quality_analysis_5x6_v1.json ;
- analyseur : sweeps/analyse_air_service_quality.py.

Le smoke seed 42 × 3 ans reproduit exactement le niveau économique de référence
early_slot : 1 563 115 £ de company value et 753 646 £/an en 1972.

## 2. Résultat global 1975

| Métrique AIR | OpexAI | AAAHogEx |
|---|---:|---:|
| lignes observées | 168 | 116 |
| véhicules / ligne | **1,01** | **2,36** |
| distance octile moyenne | 166,9 | 184,6 |
| rating moyen | 144,5 | 151,8 |
| time_since_pickup moyen | **4,6** | 10,1 |
| max_waiting_cargo moyen | **7,2** | **64,6** |
| profit / capacité | **60,5 £** | **322,6 £** |

Le résultat réfute l'explication simple « Opex a un mauvais rating parce qu'il
passe moins souvent » :

- le pickup observé est au contraire **plus récent chez Opex** ;
- le rating n'est que légèrement inférieur en 1975, et il est supérieur à celui
  d'AAA plusieurs années auparavant ;
- malgré cela, AAA obtient environ **5,3× plus de profit par unité de capacité**.

Le signal dominant est max_waiting_cargo : AAA voit beaucoup plus de cargo
passer par ses stations.

## 3. Contrôle par distance

En 1975, le profit par capacité d'Opex reste presque plat et faible quelle que
soit la longueur de ligne :

| Distance octile | Opex profit/capacité | AAA profit/capacité |
|---|---:|---:|
| 96–128 | 49,5 £ | 205,3 £ |
| 128–160 | 60,2 £ | 346,9 £ |
| 160–192 | 67,0 £ | 310,7 £ |
| 192+ | 59,3 £ | 336,8 £ |

La différence de distance moyenne — AAA vole un peu plus loin — ne peut donc pas
expliquer l'écart de rendement.

## 4. Contrôle à un seul avion

Pour éliminer la profondeur de flotte elle-même, seules les lignes à **un avion**
sont comparées en 1975.

Globalement :

- OpexAI : 166 lignes, 60,8 £ de profit/capacité,
  max_waiting/capacité = 0,083 ;
- AAAHogEx : 20 lignes, 208,9 £ de profit/capacité,
  max_waiting/capacité = 0,705.

Par bandes de distance :

| Distance | Opex profit/cap | AAA profit/cap | Opex wait/cap | AAA wait/cap |
|---|---:|---:|---:|---:|
| 96–128 | 49,5 | 205,0 | 0,082 | 0,438 |
| 128–160 | 61,0 | 115,7 | 0,089 | 1,067 |
| 160–192 | 67,0 | 179,9 | 0,082 | 0,561 |
| 192+ | 59,3 | 285,4 | 0,076 | 0,916 |

Même à flotte et distance comparables, AAA reçoit donc beaucoup plus de cargo
par unité de capacité.

Ce contrôle est important : le différentiel n'est pas créé seulement par le
fait qu'AAA a déjà trois avions là où Opex n'en a qu'un.

## 5. Marchés strictement communs

En 1975, sept marchés sont strictement comparables dans le 5×6 :

- même seed ;
- même année ;
- même paire de TownID ;
- mêmes cargos ;
- une seule ligne locale AIR par IA.

Résultats moyens :

| Métrique | OpexAI | AAAHogEx |
|---|---:|---:|
| avions | 1,00 | 3,14 |
| capacité | 350 | 877 |
| rating moyen | 157,9 | 169,0 |
| time_since_pickup | **2,8** | 6,8 |
| max_waiting moyen | **7,4** | **113,9** |
| max_waiting / capacité | **0,085** | **0,523** |
| profit / capacité | **87,1 £** | **432,3 £** |

Pairwise :

- AAA a plus de profit/capacité sur **7/7** marchés ;
- AAA a plus de max_waiting/capacité sur **7/7** marchés ;
- AAA n'a le meilleur rating que sur **3/7** marchés ;
- Opex a le meilleur rating sur **4/7** ;
- AAA a un time_since_pickup plus long sur **5/7**.

Le rating et la fréquence ne sont donc pas la cause principale du différentiel.

## 6. Conclusion causale

La boucle supposée :

1 avion → fréquence faible → rating faible → peu de cargo → W

est **réfutée comme explication principale**.

La nouvelle chaîne compatible avec les données est plutôt :

station/marché AIR → faible demande réellement captée → peu de cargo observé
à la station → faible profit/capacité → garde W presque toujours active.

Le point critique se situe donc **en amont de W**.

Comme le signal persiste sur les mêmes TownID, la seule sélection de villes ne
suffit pas à l'expliquer. Les prochains suspects sont :

1. type d'aéroport et rayon de captage ;
2. placement de l'aéroport dans la ville / proximité de la zone productive ;
3. différence de catchment réel des stations ;
4. éventuellement différence de modèle d'avion/vitesse, mais le rating seul
   n'explique déjà pas l'écart.

La prochaine priorité doit être un diagnostic passif du **catchment AIR** :
type/taille d'aéroport, position de la station relativement à la ville et, si
accessible sans instrumentation intrusive, production de passagers/courrier
dans la zone captée.

## 7. Réserve méthodologique

Une campagne géométrique antérieure et cette campagne ont des bundles OpexAI
bit-à-bit identiques mais deux seeds (999, 1234) n'ont pas reproduit exactement
les mêmes résultats économiques entre reruns.

Pour cette raison, toutes les conclusions ci-dessus sont faites
**intra-campagne**, entre OpexAI et AAAHogEx du même run, même seed et même
checkpoint. Aucun delta économique entre deux reruns n'est utilisé comme preuve.
