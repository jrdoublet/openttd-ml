# OpexAI vs AAAHogEx — comparaison ligne par ligne sur les mêmes marchés

**Date : 2026-09-15.**
**Statut : diagnostic terminé.**

Cette fiche part de la politique early_slot désormais adoptée. Elle répond à la question suivante :

> Quand OpexAI et AAAHogEx desservent réellement le même marché, l'écart économique vient-il surtout
> du nombre de marchés ouverts, du nombre de véhicules déployés sur chaque marché, ou du rendement
> des véhicules ?

Source :

- campagne passive : results/diag_early_slot_lines_20x10_v1.json ;
- analyse : results/diag_opex_vs_aaa_same_markets_20x10_v1.json ;
- vue AIR dédiée : results/diag_opex_vs_aaa_same_air_markets_20x10_v1.json ;
- analyseur : sweeps/analyse_opex_vs_aaa_same_markets.py.

La campagne contient 20 graines × 10 ans. Aucune nouvelle simulation n'a été nécessaire.

## 1. Matching

Une ligne n'est jamais appariée par group_id, station_id ou vehicle_id, qui sont locaux à une
compagnie/partie. Le matching se fait dans la même politique early_slot, la même seed et la même
année par mode + paire canonique de TownID.

La signature cargo est ensuite comparée. Pour la comparaison la plus stricte, on conserve seulement
les observations où les deux IA transportent les mêmes cargos sur ce même marché.

Les métriques disponibles viennent uniquement de la télémétrie passive :

- nombre de véhicules ;
- capacité par cargo ;
- profit_this_year ;
- profit_last_year.

profit_this_year et profit_last_year sont les sommes des valeurs VEHS /256 des véhicules encore
présents au checkpoint. Aucun revenue ni running_cost de ligne n'est inventé.

## 2. AIR : Opex ouvre beaucoup de marchés mais les densifie très peu

En 1979, moyennes par seed :

| Métrique | OpexAI | AAAHogEx |
|---|---:|---:|
| marchés AIR | 44,65 | 23,75 |
| véhicules par marché AIR | **1,02** | **3,00** |
| capacité par marché AIR | 356,9 | 670,0 |
| marchés AIR exactement communs | 1,70 | 1,70 |

Le faible recouvrement est lui-même informatif : les deux IA suivent des portefeuilles très
différents. OpexAI a presque deux fois plus de marchés AIR à dix ans, mais AAAHogEx concentre environ
trois fois plus d'avions sur chacun de ses marchés.

| Année | Marchés Opex | Marchés AAA | Marchés communs | Avions/marché Opex | Avions/marché AAA |
|---:|---:|---:|---:|---:|---:|
| 1971 | 9,15 | 13,00 | 0,95 | 1,07 | 2,11 |
| 1973 | 21,50 | 19,90 | 1,35 | 1,03 | 2,48 |
| 1975 | 33,00 | 22,05 | 1,50 | 1,02 | 2,63 |
| 1977 | 40,20 | 23,05 | 1,60 | 1,02 | 2,84 |
| 1979 | 44,65 | 23,75 | 1,70 | **1,02** | **3,00** |

À partir de 1973, OpexAI ouvre davantage de marchés AIR qu'AAAHogEx tout en restant pratiquement à
un avion par marché. La largeur du portefeuille n'est donc plus le manque visible ; le manque visible
est la profondeur de service.

## 3. AIR : sur les marchés strictement comparables, AAAHogEx domine aussi en rendement

En 1979, 34 observations AIR sont sur la même paire de villes ; 30/34 ont aussi exactement la même
signature cargo.

Sur ces 30 marchés même ville + même cargo :

| Métrique agrégée | OpexAI | AAAHogEx |
|---|---:|---:|
| véhicules | 30 | 105 |
| ratio véhicules AAA/Opex |  | **3,50×** |
| ratio capacité AAA/Opex |  | **2,47×** |
| profit courant observé | 1,206 M£ | 11,182 M£ |
| profit courant / véhicule | **40,2 k£** | **106,5 k£** |
| marchés où le profit est supérieur | 2/30 | **28/30** |

Sur l'ensemble des 34 marchés communs, cargos identiques ou non, OpexAI possède exactement 34 avions :
un avion par marché. AAAHogEx en possède 113.

Le profit courant par avion vaut alors environ 36,5 k£ chez OpexAI contre 100,7 k£ chez AAAHogEx.
Le profit_last_year reste aussi à l'avantage d'AAA : 1,174 M£ contre 6,160 M£ sur ces marchés, soit
environ 34,5 k£ contre 54,5 k£ par avion.

Le sous-dimensionnement de flotte n'explique donc pas tout : même après division par le nombre
d'appareils, AAAHogEx extrait davantage de profit des mêmes marchés.

## 4. L'âge des lignes n'explique pas l'écart

Parmi les 34 marchés communs de 1979 :

- OpexAI est arrivé plus tôt sur 4 ;
- les deux IA apparaissent la même année sur 9 ;
- AAAHogEx est arrivé plus tôt sur 21.

Sur les **9 marchés où les deux IA apparaissent la même année** :

- OpexAI : 9 avions ;
- AAAHogEx : 32 avions, soit **3,56× plus** ;
- capacité AAA/Opex : **2,86×** ;
- profit courant par avion : environ **40,5 k£ Opex** contre **117,3 k£ AAA** ;
- profit_last_year par avion : environ **44,9 k£ Opex** contre **57,3 k£ AAA**.

Même sur les **4 marchés où OpexAI est arrivé avant AAAHogEx**, AAA finit avec 20 avions contre 4,
soit **5× plus**. L'ancienneté de la ligne ne suffit donc pas à expliquer la profondeur de flotte.

## 5. Les autres modes ne donnent pas le même diagnostic

La comparaison 1979 par même marché + même cargo donne :

| Mode | observations strictement comparables | véhicules AAA/Opex | capacité AAA/Opex | profit Opex | profit AAA | victoires profit Opex / AAA |
|---|---:|---:|---:|---:|---:|---:|
| AIR | 30 | **3,50×** | **2,47×** | 1,206 M£ | 11,182 M£ | 2 / **28** |
| ROAD | 108 | 1,52× | 1,52× | **+44,9 k£** | -38,4 k£ | **93** / 15 |
| RAIL | 4 | 1,00× | 4,35× | 79,8 k£ | 218,0 k£ | 1 / 3 |
| WATER | 0 | — | — | — | — | — |

La route est donc l'inverse de l'air sur les marchés strictement comparables : OpexAI y gagne
largement plus souvent et le profit agrégé est meilleur. Ce n'est pas le chantier prioritaire de
rendement.

Le rail n'a que quatre observations réellement comparables en 1979 ; ce diagnostic ne justifie pas
un chantier général rail.

## 6. Lecture du code AIR actuel

OpexAI possède déjà une boucle de renforcement _resizeAirFleets dans task_air.nut. Elle peut
ajouter des avions et contient des gardes explicites pour :

- cadence (Y) ;
- absence d'avion vivant (V) ;
- ligne morte (D) ;
- profit négatif (L) ;
- capacité physique d'aéroport (C) ;
- plafond de demande (Q) ;
- santé de ligne (S) ;
- trésorerie insuffisante (M) ;
- échec d'achat (X) ;
- stock au sol insuffisant (W, lorsque air_fleet_buffer >= 0).

Les défauts actuels pertinents sont :

- fleet_before_new=0 : les nouvelles lignes AIR passent avant air_fleet ;
- air_fleet_cadence_days=7 ;
- air_fleet_buffer=0 ;
- air_cadence_cap=1 ;
- air_demand_cap=0 ;
- air_roi_order=1 ;
- marginal_fleet=0.

Le commentaire qui maintient fleet_before_new=0 cite des bancs du 2026-09-02. Selon la règle du
projet, les résultats antérieurs au 2026-09-09 ne font plus foi sur le code actuel. Ils ne peuvent
donc pas fermer le sujet face au diagnostic 20×10 du 2026-09-15.

## 7. Décision de priorité

Le prochain chantier prioritaire est **AIR fleet depth** : comprendre pourquoi le renforcement
existant laisse presque toutes les lignes à un seul avion.

Le prochain diagnostic doit mesurer les refus de _resizeAirFleets sur le défaut actuel early_slot,
en distinguant au minimum W, M, C, Y, L/S et les achats réellement effectués. Il doit relier chaque
refus à une ligne identifiée, son âge, son profit observé, son nombre d'avions, sa capacité et,
lorsque disponible sans inventer de comptabilité, le cargo en attente.

Le but n'est pas de passer arbitrairement fleet_before_new à 1 ni de supprimer un cap. Le fait à
expliquer est désormais précis :

> **OpexAI ouvre assez de marchés AIR, mais ne réinvestit presque jamais assez profondément dans ses
> lignes existantes ; AAAHogEx exploite les rares mêmes marchés avec environ trois fois plus d'avions
> et un meilleur profit par appareil.**

Une fois la garde dominante identifiée, un seul levier causal devra être testé sur 5×6 puis 20×10
avant toute modification de défaut.
