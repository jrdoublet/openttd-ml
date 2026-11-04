# Rapport cloud road1y (04/11/2026) : pourquoi les paires bus d'AAA rapportent plus

Branche `cloud/road1y-paxmin`, créée depuis `cloud/road1y-pack-0411` (6f00ea48 = master 558f5bd8 + données).
Données : `n_spread2_gateA.jsonl.gz` (bras `spread2` = config master actuelle, 40 graines,
instantané 1972-12-01, profit par ligne = 11 mois de 1972) et les journaux moteur des graines
100, 613553 et 781335. Carte 256×256 (distance = Manhattan entre les deux gares de la ligne).
Scripts d'analyse : hors dépôt (scratchpad de session), formules reprises ci-dessous.

## 1. Comment AAA choisit, classe et dimensionne ses lignes bus

**Choix des villes.** En début de partie AAA est en `roiBase` (`main.nut:781-787`, pas riche).
Les lieux de départ sont triés par `score = maxValue*1000 + production` (`main.nut:1500-1501`) :
à `maxValue` égal pour toutes les villes, c'est la **production de la ville** qui ordonne. Le
journal le confirme : la 1re ligne de la graine 613553 relie les deux premières villes de la liste
(Tindham 327 ↔ Gunpool 291).

**Estimation d'une paire bidirectionnelle (le point clé).** Pour un bus ou un avion,
`production = min(orgPlaceProduction, placeProduction)` (`main.nut:1757-1758`) ; une paire dont
le min est < 27 est rejetée (`main.nut:1766-1769`). L'estimateur double ensuite le revenu pour le
retour (`estimator.nut:436`, `incomePerOneTimeReturn`). Une paire grosse ville + village vaut donc
le village ×2, pas la somme. Le ROI estimé culmine vers 80-130 tuiles pour le PAX (journal :
`Estimate d:80 roi:850`, `d:130 roi:848`, `d:210 roi:513`).

**Ordres.** Chargement complet aux deux bouts pour les routes bidirectionnelles
(`road.nut:250` `isDestFullLoadOrder = true`, `route.nut:2137` et `:2163`).

**Flotte.**
- Ajout (`route.nut:2720-2724`, `:2838-2921`) : attente = `min(attente A, attente B)` ; achat si
  elle dépasse 30 (`roiBase`, < 10 véhicules), `buildNum = (attente − min(50, capacité)) / capacité`,
  au plus 4, et **rien si ≥ 2 bus sont arrêtés** (`ExistsWaiting`, `route.nut:3012-3026`).
  Le plafond `maxVehicles` monte de `max/12` quand la gare déborde (`route.nut:2799-2808`), borné
  par un plafond proportionnel au temps de trajet (`EstimateMaxVehicles`, `route.nut:2374-2380`).
- Retrait (`route.nut:2553-2619`, 25 % des passages) : si `min(attente A, B) < min(50, capacité)`
  et plus de 3 bus, les bus à l'arrêt au-delà des 3 premiers repartent au dépôt et sont vendus
  (12-26 événements « station busy » par graine sur 3 ans). Bus déficitaires de plus de 800 jours
  retirés d'octobre à décembre (`route.nut:2480-2498`).

## 2. Ce que fait OpexAI

- **Génération** (`bus_districts_overrides.nut:309-418`, `OpexRoad100SoloPaxCandidates`) : sites de
  quartier triés par captage, 40 premiers, 12 partenaires plus petits chacun, distance ≥ 64
  (`road1y_next`). **Demande de la paire = somme des deux captages**
  (`bus_districts_overrides.nut:387-389`), puis `OpexMakeRoadCandidate` → `fundScore` (ROI).
  Aucune pénalité de déséquilibre : 300 + 30 vaut 165 + 165.
- **Ordres** : chargement complet à la source A seulement (`builder_road.nut:5463-5468`,
  `road1y_load_orders=1`).
- **Renfort** (`OpexRoad1yRefleetSaved`, `bus_districts_overrides.nut:2062-2094`) : avec
  `road1y_pax_refleet=0` (défaut), plafond `ROAD1Y_FLEET(4) × min(nStopsA, nStopsB)` = 8 ou 12 bus,
  achat de ≤ 2 bus/mois dès que `(attente A + attente B) ≥ capacité`. La spécification
  `road1y_spread_cap` du rapport agy (somme des arrêts) visait la branche `paxRefleet`, **inactive
  au défaut** : sa prémisse ne s'applique pas. Retrait : seulement `road1y_weak` (bus < 1,5 k£).

## 3. Confrontation aux données (40 graines, an 3)

**Écart PAX −94 k£/graine = lignes mûres −56 k + lignes ouvertes en 1972 −38 k.**

| Lignes PAX (fin 1972) | Opex | AAA |
|---|---|---|
| Mûres (présentes fin 1971) : lignes/graine, bus/ligne, profit/ligne | 9,75 · 8,41 · 36,0 k | 8,65 · 7,04 · 47,1 k |
| Ouvertes en 1972 : lignes/graine, bus/ligne, profit/ligne | 4,5 · 4,07 · 6,2 k | 5,1 · 4,87 · 12,9 k |

À distance égale, AAA gagne plus par ligne avec moins de bus (lignes mûres) :

| Distance | Opex lignes · bus · profit | AAA lignes · bus · profit |
|---|---|---|
| 64-80 | 99 · 8,6 · 29,8 k | 47 · 5,6 · 34,2 k |
| 80-96 | 50 · 7,7 · 28,7 k | 54 · 6,2 · 41,1 k |
| 96-112 | 143 · 8,8 · 40,7 k | 105 · 6,9 · 45,2 k |
| 112-128 | 83 · 8,6 · 43,3 k | 69 · 7,9 · 55,9 k |
| ≥ 128 | 3 · 5,0 · 25 k | 39 · 10,5 · 75 k |

**D'où viennent nos 7-8 bus/ligne ?** Distribution bimodale : 212 lignes mûres à 7-8 bus et 98 à
11-12, soit exactement les plafonds `4 × min(arrêts)` (2 ou 3 arrêts par bout). La flotte est
**bornée par le plafond, pas par la demande** : elle ne dépend pas de la distance (8,6 bus à
64-80 comme à 112-128), alors que celle d'AAA croît de 4,6 (< 48 tuiles) à 13,6 (≥ 160). Pas
« jamais de retrait » au sens strict (`weak` retire), mais aucun retrait sur file d'attente.
Les renforts « sans demande » existent : la règle somme ≥ 35 se déclenche dès qu'un bout a du
stock. Ces leviers de flotte (bilat, rich_fleet, berth_fleet, fleet_unlock…) sont déjà réfutés.

**La vraie différence : l'offre de passagers par ligne.** Classement des lignes (≥ 3 bus) selon le
stock maximal en attente à chaque bout (`max_waiting_cargo`) :

| Profil | Opex part · bus · profit/ligne | AAA part · bus · profit/ligne |
|---|---|---|
| Vidée aux deux bouts (< 35 / < 35) | **49 %** (6,3/graine) · 6,7 · **23,3 k** | 13 % (1,5/graine) · 7,2 · 37,3 k |
| A vidé, B déborde (≥ 100) | 10 % · 9,2 · 27,4 k | 33 % · 7,0 · 44,3 k |
| B vidé, A déborde | 17 % · 9,1 · 44,4 k | 25 % · 6,7 · 42,5 k |
| Stock aux deux bouts | 10 % · 8,3 · 44,8 k | 9 % · 9,3 · 36,1 k |

La moitié de nos lignes **manque de passagers** : nos bus emportent tout ce qui se présente et
rapportent 23 k£/ligne ; AAA laisse presque toujours un stock quelque part. Ce n'est pas la taille
moyenne des villes (min de production médian des extrémités comparable : 151/125/108 chez nous,
165/114/113 chez AAA sur les 3 graines), c'est **l'équilibre des paires** :

- ratio `min/max` de production des deux villes : **médiane 0,49 chez nous** (31 lignes PAX des
  3 graines, 52 % < 0,6 et 39 % < 0,4), **≈ 0,87 chez AAA** (19 premières paires avec production
  connue) ;
- sur nos lignes à profit d'année pleine, la corrélation profit/ligne ~ min(prod) vaut 0,75 contre
  0,69 pour la somme (profit/bus : 0,63 contre 0,47) ;
- à somme égale (300-450) : paires équilibrées (ratio ≥ 0,6) **37,9 k£/ligne avec 6,7 bus**,
  déséquilibrées **29,5 k£ avec 7,6 bus** (n = 6 et 5 : petit échantillon, tendance cohérente
  avec 30,2 k/5,1 bus d'AAA contre 25,1 k/7,3 bus chez nous sur les paires non partagées).

Mécanisme : un bus bidirectionnel fait A→B plein puis B→A avec ce que produit B. Paire
déséquilibrée = retours presque vides ; il faut autant de bus pour la même somme, et le bout
faible est « vidé » à chaque passage. Notre estimateur (somme) ne voit pas la différence ; celui
d'AAA (min ×2) la voit.

Constat secondaire : au bout B (sans chargement complet) le temps depuis le dernier chargement est
médian 4 (p90 16) chez nous contre 1 (p90 8) chez AAA, d'où une note B de 153 contre 168 : sur
les lignes vidées, la fréquence à B est bornée par le remplissage à A.

Écarté : gel des renforts après une année < −200 £ (`bus_districts_overrides.nut:1675`), visible
sur une ligne de la graine 613553 mais 0,05 ligne/graine sur 40 graines ; plafond de 4 lignes par
ville et caisse 1972 (déjà traités par agy cash72).

## 4. Leviers nouveaux proposés

### Levier 1 (codé) : `road1y_pax_min` — estimer une paire bus comme AAA (min des deux bouts)

`monthly = (somme × (100 − N) + 2 × min(captage A, captage B) × N) / 100`, avant
`OpexMakeRoadCandidate`, seulement pour les paires bus-quartier en route seule. N = 0 : somme
historique inchangée ; N = 100 : règle d'AAA. Une paire équilibrée garde sa valeur, une paire
déséquilibrée perd la part inutile de son gros bout et recule dans le classement (et sort du
vivier si son estimation devient non rentable, comme le filtre min < 27 d'AAA).

**Effet attendu à 3 ans** : environ 7 lignes déséquilibrées par graine (52 % de 14,2). Si la moitié
est remplacée par des paires équilibrées (+8,4 k£/ligne à somme égale, −0,9 bus), gain brut
≈ +31 k£/an ; en tenant compte d'une somme moyenne plus faible des paires de remplacement et de la
concurrence d'AAA sur les grosses villes : **+15 à +30 k£/an, estimation centrale +20 k£/an**,
au niveau du seuil utile (+21 k£/an). Effet secondaire : moins de bus par ligne (capital libéré).
Risque : vivier PAX plus court (l'expérience `next2` montre qu'un classement mal calé peut
coûter cher) ; le smoke doit vérifier que les ouvertures ne s'effondrent pas.
**Valeur à banquer : `road1y_pax_min=100`** (règle AAA pure) ; 50 en second bras si 100 échoue
sur le volume d'ouvertures.

### Levier 2 (non codé) : `road1y_alt_load` — une part des bus chargent à plein à B

Donner à environ un tiers des bus d'une ligne l'ordre inverse (chargement complet à B, aucun à A),
en liste d'ordres séparée. Chaque bout a alors souvent un bus en charge : temps depuis le dernier
chargement à B de 4 → ≈ 1, note B de 153 → ≈ 175 (niveau de A), soit ≈ +15 % de voyageurs
générés à B. Différent de `dest_full` (tous les bus chargent à plein aux deux bouts, réfuté au
smoke) : aucun bus n'attend deux fois. Effet attendu ≈ +7 % de revenu des lignes PAX, **+10 à
+25 k£/an**. Plus risqué à coder (deuxième liste d'ordres, identification des véhicules de ligne,
`weak` et `spread` qui manipulent la flotte) : à tenter après le levier 1.

## 5. Smoke GitHub (phase 3)

Run [41850440520](https://github.com/jrdoublet/openttd-ml/actions/runs/41850440520), commit
ac4a78b2, `mode=paired`, `profile=custom`, 3 ans, graines 613553 781335 100,
`aaahogex_settings=road_only`, `line_telemetry=true`. Référence
`OpexAI[mode_air=0,mode_rail=0,mode_road=1,mode_water=0,probes=258]`, variante identique plus
`road1y_pax_min=100`. Écart à la commande du PROMPT : `probes=258` ajouté **aux deux bras**
(le défaut du workflow, probes=2, ne journalise pas `OpexDecide`) pour voir les compteurs.

**Santé** : 6/6 parties `complete`, OpexAI et AAAHogEx `horizon_complete` jusqu'au 1972-12-01,
aucune erreur non attribuée, 0 ligne `[E]`/`[S]` de script, 0 faillite.

**Mécanisme exercé** (variante seulement ; aucune ligne `ROAD1Y_PAX_MIN` côté référence) :
35 générations PAX journalisées (12 + 14 + 9, une par `ROAD100_PAX_GEN`), 7 496 paires notées,
7 411 pénalisées (99 %), 216 562 voyageurs/mois retirés au total des estimations, 7 409 paires
restent rentables. Le réglage **réordonne** le vivier ; il n'en retire presque rien.

**profit_year 1972** (pas de conclusion économique : bruit ≈ ±18 % à 3 graines) :

| Graine | Réf. Opex | Réf. AAA | Var. Opex | Var. AAA | Var − Réf (Opex) |
|---|---|---|---|---|---|
| 100 | 318 045 | 472 323 | 371 647 | 515 636 | +53 602 |
| 613553 | 473 694 | 769 999 | 624 953 | 716 090 | +151 259 |
| 781335 | 534 106 | 619 554 | 388 247 | 525 666 | −145 859 |
| Moyenne | 441 948 | 620 625 | 461 616 | 585 797 | +19 668 |

Opex/AAA (rapport des sommes) : 71,2 % référence, 78,8 % variante. Véhicules Opex en fin de
partie : 118/166/186 (réf.) contre 158/221/151 (var.) : les ouvertures ne s'effondrent pas.
La graine 781335 recule fortement : à examiner sur le banc complet (lignes par profil de
déséquilibre) avant toute conclusion.

**Suite** : porte A `gain_short` 40×3 avec `road1y_pax_min=100` (sur VPS, par l'utilisateur),
puis porte B 20×10 si elle passe. Aucun défaut modifié.
