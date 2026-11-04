# Pourquoi 30 k£ par véhicule au lieu de 50-60 — synthèse cloud du 4 novembre 2026 (Prompt 4)

Revue croisée de bout en bout d'une **ligne fret type** d'OpexAI et d'AAAHogEx‑115, du choix de la
route à la livraison. Ce document ne contient pas de code. Il s'appuie sur :
- `docs/point_9h_20261103.md` ;
- `docs/v190_eco_20261103.md` §4 et §6 ;
- `docs/cloud_pack_20261104/per_seed.csv` ;
- `docs/mecanique_jeu.md` §3 et §4, relus sur le source OpenTTD 15.3 ;
- `docs/rail_loop_bancs_20261104.md` (bancs PC du 04/11) ;
- les trois revues cloud du jour : `cloud_double-voie`, `cloud_capacite-rame`, `cloud_portefeuille`.

Les références au code d'AAA sont celles déjà relevées dans ces rapports : la source GPL n'est pas
dans le dépôt.

## 0. En une phrase

Opex construit **beaucoup de lignes à une rame courte**, dimensionnée pour la note de gare qu'il
suppose (50 %). Il obtient donc cette note. À ce niveau, la production de ses industries
**baisse** plus souvent qu'elle ne monte.

AAA construit **moins de lignes**, chacune avec plusieurs rames longues dont **une est toujours
en chargement**. Sa note tourne autour de 75 % ; au-delà de 60 % de fret transporté, la production
**monte** dans deux cas sur trois.

L'écart par véhicule (×1,5 à 5 ans) devient alors à 10 ans un écart de flotte et de production
(×2,25 sur le profit).

## 1. Ce que disent les chiffres agrégés (rail seul, duels appariés)

Moyennes OpexAI et AAAHogEx des bras de **référence** (calcul sur `per_seed.csv`). La note de gare
est la `median_station_rating` en /255.

| Indicateur | Opex 5 ans (40 graines) | AAA 5 ans | Opex 10 ans (20 graines) | AAA 10 ans |
|---|---:|---:|---:|---:|
| `profit_year` | 1,59 M£ | 1,88 M£ | 1,79 M£ | **4,02 M£** |
| Véhicules | **50,0** | 40,1 | 55,2 | **72,7** |
| Profit médian par véhicule | **31,5 k£** | 47,2 k£ | 31,8 k£ | **54,0 k£** |
| Gares | 75 | 40 | 81 | 51 |
| Note de gare médiane | **131 (51 %)** | 192 (75 %) | 134 (53 %) | 203 (80 %) |
| Caisse | 0,39 M£ | 0,67 M£ | 6,8 M£ | 14,2 M£ |

Sources : `rds_failclosed_A40x5_20261103`, bras de référence ; `rail_long_v3_gate_b_rail_20x10`,
bras de référence.

**Lecture.**
- **À 5 ans**, Opex a **25 % de véhicules en plus** qu'AAA et presque **deux fois plus de gares**.
  Tout le déficit vient du rendement par véhicule (×1,50).
- **À 10 ans**, l'écart de profit (×2,25) se décompose en rendement par véhicule ×1,70 (environ
  65 % de l'écart logarithmique) et flotte ×1,32 (environ 35 %).
- Opex n'a pas pris de retard en **nombre de projets**. Il a pris du retard en **trafic par
  ligne**.

**Fret seul** (télémétrie 40×5, décembre 1974, `docs/point_9h_20261103.md`) :

| Mesure | Opex | AAA |
|---|---:|---:|
| Trains par ligne | 1,00 | 1,89 |
| Unités par train | 90 | 240 |
| Note source (/255) | 151 | 212 |
| Profit par train | 10 k£ | 32 k£ |
| Distance médiane | 119 | 131 |

Fret livré au dernier trimestre (rail seul 1974, `docs/taches.md` MULTI-1) : **2 408 unités pour
Opex contre 4 266 pour AAA**, alors qu'Opex aligne plus de trains.

## 2. Une ligne fret type, étape par étape

| Étape | OpexAI (code courant) | AAAHogEx‑115 (lectures documentées) | Écart |
|---|---|---|---|
| **Choix de la route** | Classement `fundScore` ; une ligne par origine (`origin_served`) ; disque de 10 cases autour de chaque gare (`MIN_SEPARATION`, `main.nut:72`) | Compare simple et double sur la même route (`estimator.nut:1767-1811`) ; réutilise une source en **ajoutant des trains** (`trainroute.nut:970-1008`) ou une destination (`TrainRouteExtendBuilder`) | Opex multiplie les lignes ; AAA les remplit |
| **Cargo et distance** | Distance médiane 119 ; portefeuille riche en voyageurs et courrier (19 groupes contre 3,9 chez AAA) | Distance médiane 131 | Faible : environ 10 % de recette par unité |
| **Gare** | Un quai de 3-4 cases (médiane mesurée 4) ; une gare par extrémité et par ligne ; jonctions V178/sœurs ponctuelles | 2-3 quais × 7 cases à la source, 1-2 à la destination (`station.nut:1518-1558`, `1601-1642`) ; 15-17 % des gares servent 2 à 4 lignes à 10 ans | Le quai court plafonne la rame à 5-7 wagons |
| **Voie** | Voie unique, aucun PBS à sens unique ; seconde voie seulement au Cas 2 (voie isolée, une rame) ; RAIL-LOOP par défaut depuis `a8cfb1e` | Double voie orientée, PBS à sens unique environ toutes les 7 cases (391 à 807 par graine) | Plafond d'un train par voie chez Opex |
| **Dépôt** | Collé à la gare, sur la première case de voie (`OpexBuildDepot`, `builder_rail.nut:4340`) | Hors tracé, accès vérifiés (`BuildDepotForRail`) | Bloque les boucles : 46 rejets `depot_front_curve` |
| **Matériel** | Une locomotive ; wagons = offre calibrée / capacité par trajet, avec une **note supposée de 50 %** (`economy.nut:24`, `:267-274`) ; renouvellement V257 sur le fret **livré**, départage par le prix | 10 à 13 wagons, souvent 2-3 locomotives (`trainroute.nut:2957-2988`) | Capacité ×2,7 |
| **Ordres** | Chargement complet à A, non-stop, déchargement à B ; ordres partagés seulement sur les boucles RAIL-LOOP | Chargement complet, ordres partagés et clones ; transferts (`OF_TRANSFER`) dans son réseau | Comparable |
| **Cadence** | Une rame : la source reste vide pendant presque tout l'aller-retour | Plusieurs rames : une rame **toujours en chargement** à la source | **Bonus de ramassage : 10-20 % contre 51 %** (`mecanique_jeu.md` §3) |
| **Note de gare** | 51-53 % | 75-80 % | ×1,5 de fret capté à production égale |
| **Évolution de la production** | Fret transporté souvent ≤ 60 % : dans 67 % des changements, la production **baisse** (`mecanique_jeu.md` §4) | Au-delà de 60 % : 67 % de hausses ; au-delà de 80 % : 83 % | Effet composé sur 10 ans |
| **Profit par rame et par an** | Environ 6 k£ par wagon d'après ses propres doubles (§3.2) ; 10 k£ par rame fret en médiane | 32 k£ par rame fret ; jusqu'à 798 k£ pour 9 rames sur une ligne (graine 512) | ×3 en fret |

## 3. Classement des écarts par contribution au déficit de profit par véhicule

Chaque estimation vient de mesures existantes. Les ordres de grandeur sont signalés comme tels.

### Écart n°1 — La note de la gare source, et son effet sur la production (le plus important)

**Mécanisme.** Le fret capté est `production × note` (`mecanique_jeu.md` §3). Le plus gros terme
de la note est le **délai depuis le dernier chargement** : +51 % sous 6,8 jours, +10 % entre 27
et 47 jours.
- Une rame unique taillée pour la production arrive, charge ce qui attend et repart. La gare reste
  ensuite vide un aller-retour entier, souvent 30 à 50 jours.
- Une rame **en chargement complet** présente en permanence garde le bonus maximal.
- Opex dimensionne ses rames pour **50 %** de note (`STATION_RATING_PCT`) et obtient 51 %. Le
  modèle se valide lui-même.

**Effet composé.** Avec une note de 51 %, le fret transporté de l'industrie reste sous 60 %. Dans
le barème 15.3 (`mecanique_jeu.md` §4) :
- environ 4,5 % de chance de changement par mois, d'amplitude 4 à 23 % ;
- **67 % de baisses** sous 60 % transporté, contre **67 à 83 % de hausses** au-dessus.

En espérance, sur 10 ans (environ 5 changements de 13 % en moyenne), la production d'Opex tend
vers **environ ×0,8** et celle d'AAA vers **environ ×1,25 à 1,4**. Cela donne un facteur d'environ
**1,6** entre les deux.

C'est une **estimation par le barème, pas une mesure**. Elle explique pourtant les trois faits
observés :
- le ratio rail seul passe de 85 % à 5 ans à environ 45 % à 10 ans ;
- le profit d'Opex est quasi constant d'une carte à l'autre (1,1-1,9 M£) ;
- les graines perdantes sont celles où AAA monte à 50-70 véhicules.

**Contribution estimée** : la plus grande. Environ ×1,4-1,5 de fret capté à production égale, plus
un facteur 1,2-1,6 de production à 10 ans.

**Quels chantiers l'attaquaient, et pourquoi ils ont échoué.**
- **Aucun ne la visait directement.**
- RAIL-PAIR (second quai et second train sur voie unique) a fait monter la note source
  (45 → 53 %, 40 → 82 %), mais −120 k£ (a), parce qu'une voie unique ne porte pas deux trains.
- Le modèle de note par cadence (`OpexStationRatingForHeadway`, sous `estim_unifie & 8`) reste un
  opt-in de calibration, défaut 0.
- La note `mecanique_jeu.md` §4 interdit un « terme service composé » au classement sans banc :
  ce n'est pas une réfutation.

**Bonne implémentation dans OpexAI.**
- Viser une **rame toujours en chargement** à la source : N rames à ordres partagés sur une voie
  orientée (RAIL-LOOP), avec une taille calculée pour une note cible de 75-80 % (cible de
  RAIL-FILL, déjà codée).
- Puis réévaluer les lignes avec une demande **non censurée**, c'est-à-dire la production réelle
  de l'industrie, pas le fret livré.
- **KPI à suivre pour chaque ligne** : le % transporté de l'industrie source, objectif > 60 %,
  idéalement > 80 %.

### Écart n°2 — La capacité par rame (90 contre 240 unités)

**Mesure interne à Opex.** Sur les doubles V190 indépendantes (`v190_eco_20261103.md` §4), le
profit annuel par rame croît à peu près linéairement avec les wagons :

| Composition | Profit par rame |
|---|---:|
| 2 wagons | 8-20 k£ |
| 4 wagons | 26 k£ |
| 6-7 wagons | 31-42 k£ |
| 11 wagons (GOOD, 841478 #10) | **67 k£** |

Cela fait environ **6 k£ par wagon et par an**. C'est **confondu** avec la production : le
dimensionnement met plus de wagons là où il y a plus de fret.

**Pourquoi les rames sont courtes** (`docs/cloud_capacite-rame_20261104.md`) :
- note de 50 % supposée au dimensionnement initial ;
- V257 reprend comme demande le fret **déjà livré**, donc plafonné par la rame, et départage par
  le prix : il raccourcit ;
- quais de 3-4 cases.

La médiane en service reste à **3 wagons** pour un quai qui en porte **7**.

**Contribution estimée** : grande, mais seulement si la cargaison suit. Une rame longue en
chargement complet améliore aussi la note de l'écart n°1 par sa présence.

**Quels chantiers l'attaquaient, et pourquoi ils ont échoué.**

| Chantier | Ce qui s'est passé | Catégorie |
|---|---|---|
| RAIL-CONSIST | Capital doublé en 1970-72, quand la caisse est la contrainte | (b) mauvais moment |
| RAIL-LONG v1 | 2 rames longues, défaites ensuite par V257 | (b) et (c) |
| RAIL-LONG v2/v3 | Lignes neuves seulement, 11 modernisations sur 40 graines, multi-traction 1/1 209 ; le parc posé en 1970-72 reste court | (c) |
| INVEST-STALL | Garde `GetCapacity == 0` alors que l'API renvoie −1 : 0 achat | (b) bug |

**Bonne implémentation.**
- **RAIL-FILL** (`rail_fill=1`, codé, non mesuré) : remplir les quais **existants** quand la caisse
  dort, sur la production réelle, avec la transaction V284 éprouvée, et protéger la rame de V257.
- Ensuite seulement : quais de 7 cases et multi-traction pour les lignes neuves (RAIL-LONG v3).

### Écart n°3 — Le nombre de rames par ligne (1,0-1,14 contre 1,89)

**Mécanisme.** La voie unique d'Opex ne porte qu'un train. Chaque rame ajoutée sur une ligne
existante :
- augmente directement le fret transporté ;
- fait monter la note (écart n°1) ;
- est ce qui fait **croître la flotte** à 10 ans (55 contre 73 véhicules).

**Mesure causale.** C'est le **seul gain significatif de la campagne** : RAIL-LOOP en porte B rail
20×10 donne **+173 k£/an**, 16V/4D, p = 0,0014, IC95 [+86 ; +257] k£. Il vient de 33 boucles et
**119 rames ajoutées**, soit **environ +29 k£/an par rame ajoutée** sur une source déjà servie. La
porte A à 5 ans est neutre, car les boucles naissent en 1973-75.

**Contribution estimée** : moyenne sur le rendement par véhicule, mais **principale sur l'écart de
flotte à 10 ans** (environ 18 véhicules × 30 k£ ≈ 0,5 M£ des 2,2 M£ d'écart).

**Quels chantiers l'attaquaient, et pourquoi ils ont échoué** (`docs/cloud_double-voie_20261104.md`) :

| Chantier | Ce qui s'est passé | Catégorie |
|---|---|---|
| V190 | Deux voies isolées à une rame chacune, plus un écrasement du slot `_railSearch` | (b) |
| V190-FIX2 et DOUBLE-GROW | Aiguillages de gorge : virages à 90°, pas de quai parallèle ; bugs de caisse et de structures | (b) |
| RDS | 26 rames perdues sur les embranchements | (b) |
| RAIL-PAIR | Deux trains sur voie unique | (a) |
| RAIL-SEARCH-PRIO | A tué les doublements Cas 2 : −24 trains | (b) |
| Verrou V284 | `task_rail.nut:652` coupe le Cas 2 de toutes les lignes fret dès que V284 s'active | (b) |

**Bonne implémentation.**
- **RAIL-LOOP**, défaut depuis `a8cfb1e` : traverse les quais, sans gorge ni nouveau dépôt.
- **RAIL-KEEP** (`rail_expand_keep=1`, codé, non mesuré) : rouvre le Cas 2 après l'activation de
  V284.
- Lever les deux premiers rejets de RAIL-LOOP : `depot_front_curve` 46 et `back_lead` 30.

### Écarts secondaires

| Écart | Contribution estimée | Commentaire |
|---|---|---|
| Composition et vitesse (multi-traction) | Faible à 5 ans | Utile seulement au-delà de 7 wagons ; non mesuré : vitesses des locomotives en service des deux IA |
| Distance (119 contre 131) | Environ 10 % de recette par unité | Pas un levier prioritaire |
| Mix voyageurs (19 groupes contre 3,9) | Indéterminée | Les lignes voyageurs d'Opex sont rentables ; ne pas les sacrifier |
| Nombre de gares (75 contre 40) | Nulle en coûts | `infrastructure_maintenance = false` ; mais chaque gare interdit un disque de 10 cases (§2) |

## 4. Mesures manquantes, à faire avant de conclure sur l'écart n°1

Ces mesures sont peu coûteuses, sans changer le comportement de l'IA, et à faire sur les
sauvegardes d'un smoke existant (`--retain-savegames`) :

1. **% transporté et production mensuelle de chaque industrie source**, pour Opex et pour AAA.
   Bloc `INDY` des sauvegardes : `last_month_production`, `last_month_pct_transported`. On peut
   aussi utiliser l'IA elle-même sous sonde (`AIIndustry.GetLastMonthTransportedPercentage`,
   `GetLastMonthProduction`), comme le fait déjà `OpexInvestStallSourceGap`.

   Hypothèse à confirmer : sur 10 ans, la production des sources d'Opex baisse, celle d'AAA monte.
2. **Fraction du temps où une rame est en gare source**, par ligne et pour chaque IA. On la tire
   des positions mensuelles des véhicules (VEHS), en ajoutant `--line-telemetry-monthly` :
   présence de 0 à 1, à corréler avec la note.
3. **Trajets chargés par rame et par an**, et unités livrées par véhicule (`LINE_REVENUE`). Cela
   permet de séparer capacité et cadence dans l'écart n°2.

## 5. Feuille de route ordonnée

| Ordre | Action | Pourquoi maintenant | État |
|---:|---|---|---|
| 1 | **Mesures du §4** (production, % transporté, présence en gare), sur les sauvegardes RAIL-LOOP et RAIL-FILL | Confirme ou réfute le moteur principal de l'écart avant d'investir plus | Pas de code IA ; un lecteur de sauvegarde à écrire |
| 2 | **RAIL-FILL** : smoke 1×1, smoke 4×6, puis porte B 20×10 (A neutre attendue à 5 ans) | Capacité sur tout le parc existant, financée par la caisse oisive | Codé (`rail_fill`, défaut 0) |
| 3 | **RAIL-KEEP**, seul puis combiné à RAIL-FILL (4×10, puis B 20×10) | Rouvre le second train Cas 2 coupé par V284 | Codé (`rail_expand_keep`, défaut 0) |
| 4 | **Exposition de RAIL-LOOP** : dépôt non droit (poser le dépôt sur la voie 2), arrière de quai occupé (allonger le quai d'une case), admission plus précoce, ventilation des 56 échecs | Le seul levier significatif mesuré : plus de boucles, plus tôt | À coder |
| 5 | **Demande non censurée dans V257** (production × note prévue) et départage par la capacité ; correctif INVEST-STALL `<= 0` | Empêche de raccourcir les rames ; débloque les achats de wagons | À coder, opt-in |
| 6 | **Dimensionnement initial à note cible** (75-80 %) et production attendue dans l'évaluation des candidats, sous banc et opt-in | Choisir des sources où plus de 60 % transporté est atteignable | À coder après l'étape 1 |
| 7 | **Lignes neuves construites directement en boucle**, avec quais de 6-7 cases (RAIL-LONG v3 + RAIL-LOOP à la construction) | Évite la phase « une rame courte » de 1970-72, si la caisse le permet | Chantier |
| 8 | **Réseau en étoile avec transfert** (V226), sur des troncs RAIL-LOOP | La croissance de long terme d'AAA ; prérequis de troncs multi-rames désormais disponible | Chantier |

**À ne pas refaire sans fait nouveau** : relâcher `origin_served`, filtrer la proximité avant le
TOP_K, `MIN_SEPARATION`, multiplier les créneaux A\*, préempter les upgrades, ajouter des trains
sur voie unique (`docs/cloud_portefeuille_20261104.md` §1).

**Multimodal.** RAIL-LOOP n'y change rien de mesurable (porte B −64 k£, neutre). AAA y aligne
288 véhicules à 23 k£, contre 112 à 36 k£ pour Opex : l'écart y est **de flotte routière et
aérienne**, pas de rendement par véhicule. Il faut le traiter comme un chantier distinct.
