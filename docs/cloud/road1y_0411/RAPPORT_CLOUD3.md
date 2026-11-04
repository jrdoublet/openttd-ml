# Rapport cloud n°3 (04/11/2026) : `road1y_aaa_fleet`, la flotte bus d'AAAHogEx portée d'un bloc

Branche `cloud/road1y-aaafleet`, créée depuis `cloud/road1y-pack2-0411` (6b10cdb9). Code : commit
813f5c2a. Réglage `road1y_aaa_fleet` (0/1, défaut 0, forcé à 0 hors route seule). Smoke GitHub :
run [41874293544](https://github.com/jrdoublet/openttd-ml/actions/runs/41874293544).

## 1. Lecture

**AAA** (`ai/AAAHogEx-115/route.nut`, mode `roiBase` pendant les 3 ans) :
- plafond `maxVehicles` : à la première construction, `EstimateMaxVehicles` (`:2374-2380`,
  `:2107`) = `min(2 × jours_aller + 1, 2 × (distance + 4)) + 2`, avec
  `jours_aller = distance × 664 / vitesse / 24` ; pour un bus de 1970 à 56 km/h sur 100 tuiles,
  101 bus. Ce plafond ne lie presque jamais : il est abaissé à `flotte − retirés` à chaque retrait
  (`:2613-2616`) et relevé de `max(1, estimation/12)` quand la source déborde (note < 40 ou plus
  de 1 000 en attente, `:2799-2808`, `:492-503`) ;
- ajout (`:2838-2921`) : attente = `min(attente A, attente B)` pour une ligne bus
  bidirectionnelle (`:2720-2724`) ; seuil 30 sous 10 bus, 100 au-delà ;
  `(attente − min(50, capacité)) / capacité` bus, au plus 4 ; **rien si au moins 2 bus sont à
  l'arrêt** (`ExistsWaiting`, `:3012-3026`) ;
- retrait (`:2553-2619`, 25 % des passages) : plus de 3 bus, `min(attente) < min(50, capacité)`,
  plus de 3 bus à l'arrêt : ceux au-delà des 3 premiers vont au dépôt et sont vendus ;
- bus déficitaires depuis plus de 800 jours retirés d'octobre à décembre (`:2480-2498`).

**OpexAI** (`ai/OpexAI/bus_districts_overrides.nut`, `OpexRoad1yRefleetSaved`) :
- `target` part de `predTrains`, borné par `OpexRoadPhysicalVehicleCap` (`:1844`) ;
- trois règles historiques (`:1934-1946`) : somme des attentes ≥ capacité et aucun bus arrêté →
  jusqu'à 3 bus ; note < 65 → 1 bus ; ligne rentable (> 1 000 £) et caisse > 60 k → 1 bus.
  Les deux dernières ajoutent **sans demande** ;
- bloc `ROAD1Y_FLEET` (`:2085-2117`) : plafond `4 × min(nStopsA, nStopsB)`, 2 bus/mois dès que
  `somme ≥ capacité`. Le commentaire est explicite : un bus arrêté qui charge ne bloque pas l'achat ;
- gel si l'année précédente est < −200 £ (`:1698`) ;
- retrait : seulement `road1y_weak` (`bus_districts.nut:811`, `OpexRoad1yWeakStep`), qui déplace
  un bus d'une ligne faible (< 1,5 k£/bus, attente ≤ 20) vers une ligne forte de moins de 8 bus.
  Aucun retrait sur file d'attente.

## 2. Mesures (`n_spread2_3y.jsonl.gz`, 3 graines, instantanés mensuels)

| | Opex | AAA |
|---|---|---|
| Bus PAX ajoutés en 3 ans (hausses mensuelles de flotte) | 224 | 188 |
| … avec `min(attente A, B) ≤ 30` le mois précédent | **160 (71 %)** | 65 (35 %) |
| … avec `somme < 35` (aucune demande visible) | **69 (31 %)** | 7 (4 %) |
| Bus retirés (baisses mensuelles) | **0** | 54 |
| Bus par ligne à 1, 6, 12, 24 mois | 2,3 · 4,8 · 6,3 · **9,1** | 2,6 · 6,4 · 7,1 · **6,5** |

L'instantané mensuel ne coïncide pas avec l'instant où chaque IA décide : les 35 % d'AAA
mesurent ce bruit. Au-delà, **environ 36 % de nos ajouts se font sans demande au bout faible**
selon le critère d'AAA, et 31 % sans aucune demande visible. Notre flotte croît encore à 24 mois,
alors que celle d'AAA plafonne puis baisse.

Bus arrêtés en charge : la télémétrie de ligne ne donne pas l'état des véhicules et les journaux
moteur du pack n'ont pas de journal de flotte. La mesure vient donc du bras variante du smoke
(§4) : en moyenne 0,6 bus arrêté par ligne, dont 0,4 à la source, avec des flottes de 4-5 bus.

## 3. Le portage et ce qui le distingue des leviers réfutés

Pour les lignes `kind == "pax"`, un seul appel gardé, placé après les règles historiques et
juste avant `if (have >= target)`, remplace la cible :
`OpexRoad1yAaaFleetTarget` (`ai/OpexAI/road1y_aaa_fleet.nut`). Une fois par mois et par ligne :
1. plafond = `EstimateMaxVehicles` (distance Manhattan des terminus, vitesse du modèle corrigée
   de la fiabilité si les pannes sont actives) ; abaissé à `flotte − 1` à chaque retrait ;
   relevé de `max(1, estimation/12)` si la source A a une note < 40 ou plus de 1 000 voyageurs ;
2. retrait : plus de 3 bus, `min(attente) < min(50, capacité)` et plus de 3 bus à l'arrêt →
   le dernier bus arrêté va au dépôt ; il est vendu dès qu'il y est arrêté (vérifié à chaque
   passage), au plus un par mois et par ligne ;
3. ajout : `min(attente) > 30` (100 à partir de 10 bus) et moins de 2 bus arrêtés en charge à
   la gare source → `(min − min(50, capacité)) / capacité`, au plus 4, dans la limite du plafond
   et des emplacements de véhicules.

`road1y_weak`, `spread_stops` et `load_orders` sont inchangés. À 0 : aucun appel, chemin
historique identique (contrat `test_off_path_is_the_historical_refleet`).

| Levier réfuté | Ce qu'il changeait | Différence avec `aaa_fleet` |
|---|---|---|
| `road1y_fleet` | la valeur du plafond par quai (4) | le plafond par quai disparaît : la flotte suit la demande au bout faible, et elle peut descendre |
| `rich_fleet` | renfort quand la caisse dépasse 100 k£ | aucun critère de caisse ; ajoute moins (min au lieu de somme) et retire |
| `berth_fleet` | arrêt sans réserve de 50 k£ + renfort de style AAA | ce levier ne gérait que l'ajout, sous le plafond par quai ; ici, plafond, ajout et retrait changent ensemble |
| `fleet_unlock` | bits qui relevaient les plafonds (somme des arrêts, 6/quai) ou baissaient la réserve | sens inverse : aucun relèvement par quai ; la seule hausse du plafond vient du débordement de la source |
| `pax_bilat` | renfort sur `min(A, B) × 2` | même critère d'ajout, mais `pax_bilat` gardait le plafond fixe, sans garde « 2 bus arrêtés » ni retrait : sa flotte ne redescendait jamais |
| `weak` (adopté) | déplace un bus d'une ligne faible vers une forte | conservé tel quel ; il agit entre lignes, `aaa_fleet` agit dans chaque ligne |
| `dest_full` | chargement complet aux deux bouts | non touché : chargement complet à la source seule (`load_orders`) |

Chacun de ces essais ne changeait qu'une règle. Ici, les quatre règles d'AAA (plafond par temps
de trajet, ajout sur le bout faible, garde « bus arrêtés », retrait) changent ensemble, et c'est
la première fois qu'une flotte de ligne bus peut redescendre.

## 4. Smoke GitHub (phase de contrôle, aucune conclusion économique)

Run [41874293544](https://github.com/jrdoublet/openttd-ml/actions/runs/41874293544), `paired`,
`custom`, 3 ans, graines 613553 781335 100, `aaahogex_settings=road_only`,
`line_telemetry=true`, `probes=258` aux deux bras (pour journaliser `OpexDecide`), variante
`road1y_aaa_fleet=1`.

**Santé** : 6/6 parties `complete`, OpexAI et AAAHogEx `horizon_complete` jusqu'au 1972-12-01,
aucune erreur non attribuée, 0 ligne `[E]`/`[S]` de script.

**Mécanisme exercé** (variante seulement) : 157 décisions d'ajout, 11 envois au dépôt, 9 ventes,
0 relèvement de plafond, 480 mois-ligne sans action. Pourquoi aucun ajout, sur 637 échantillons
mois-ligne : `min(attente) ≤ seuil` 369 fois (58 %), dont **267 où l'autre bout dépassait le
seuil** (paire déséquilibrée) ; 2 bus arrêtés à la source 54 fois (8 %) ; plafond atteint
23 fois (4 %). Le plafond par temps de trajet ne lie pas (estimation 50 à 82 bus selon la
distance) : **c'est la règle du bout faible qui borne la flotte**, comme chez AAA. Cela rejoint
le constat du rapport n°1 : nos paires déséquilibrées ont un bout vidé. Les retraits se
concentrent sur la graine 613553 (10 sur 11), sur des lignes à 8-17 bus dont la source A était
vidée pendant que B accumulait 500 à 1 000 voyageurs.

**Bus par ligne selon la distance** (lignes PAX Opex, fin 1972, profit des 11 mois de 1972) :

| Distance | Référence : lignes · bus · profit | Variante : lignes · bus · profit |
|---|---|---|
| 64-80 | 13 · 7,4 · 18,7 k | 14 · 4,6 · 17,6 k |
| 80-96 | 5 · 7,4 · 25,2 k | 8 · 4,4 · 22,0 k |
| 96-112 | 13 · 7,0 · 30,2 k | 11 · 4,1 · 21,7 k |
| 112-128 | 7 · 8,3 · 32,5 k | 7 · **7,6** · **42,4 k** |
| Total (toutes distances) | 38 · 7,4 · 26,1 k | 43 · **4,7** · 22,5 k |

La flotte n'est plus collée au plafond de quais (7-8 bus partout). Elle ne croît pourtant
nettement avec la distance qu'au-delà de 112 tuiles (4,1-4,6 bus de 64 à 112, 7,6 de 112 à 128),
où le profit par ligne monte à 42,4 k£. AAA, dans le même smoke : 5,6 bus/ligne et 30,1 k£/ligne.

**profit_year 1972** (bruit ≈ ±18 % à 3 graines) :

| Graine | Réf. Opex | Réf. AAA | Var. Opex | Var. AAA | Var − Réf (Opex) |
|---|---|---|---|---|---|
| 100 | 366 332 | 478 899 | 313 314 | 506 204 | −53 018 |
| 613553 | 473 694 | 769 999 | 539 242 | 782 989 | +65 548 |
| 781335 | 534 106 | 619 554 | 550 575 | 635 883 | +16 469 |
| Moyenne | 458 044 | 622 817 | 467 710 | 641 692 | +9 666 |

Véhicules Opex en fin de partie : 146/166/186 (réf.) contre 123/141/199 (var.). Opex/AAA :
73,5 % (réf.) et 72,9 % (var.).

## 5. Suite

- Valeur à banquer : **`road1y_aaa_fleet=1`**, porte A `gain_short` 40×3 contre la configuration
  route seule actuelle (sur VPS, par l'utilisateur), puis porte B 20×10 si elle passe.
- Avec `road1y_pax_min=100` (mission n°1), les deux leviers visent la même cause, l'équilibre des
  paires : `pax_min` choisit des paires équilibrées, `aaa_fleet` cesse de renforcer celles qui ne
  le sont pas. Selon la règle des portes par lot, à tester seuls puis ensemble.
- Non porté : le retrait des bus déficitaires depuis 800 jours d'AAA (`route.nut:2480-2498`) ;
  `weak` joue ce rôle chez nous. Le gel « année < −200 £ » s'applique avant l'appel : une vente en
  attente sur une ligne gelée attend la fin du gel (bus arrêté au dépôt, sans frais de roulement).
