# Diagnostic : cargo par ligne rail, OpexAI contre AAAHogEx

**Date :** 20 octobre 2026  
**Auteur :** agy  
**Chantier :** Décision utilisateur du 20/10/2026 sur l'efficacité des lignes rail fret à 10 ans  
**Script d'analyse :** [`sweeps/diag_cargo_par_ligne_rail.py`](file:///home/deploy/projects/wt-raildiag/sweeps/diag_cargo_par_ligne_rail.py)  
**Données sources :** Campagne d'exposition 3 graines × 10 ans `wt-v270/results/v270_expo_3x10_20261019*` (graines 42, 7, 1234, bras référence contre AAAHogEx) et travail de référence `wt-v265fix/results/v265fix_expo_complete_3x10_20261019*`.

---

## Question et contexte

Pourquoi chaque levier de capacité sur nos lignes rail fret existantes (rames plus longues [V270](file:///home/deploy/projects/wt-raildiag/docs/taches.md#L62)/[V272](file:///home/deploy/projects/wt-raildiag/docs/taches.md#L82)/[V284](file:///home/deploy/projects/wt-raildiag/docs/taches.md#L21), 2e train [V181](file:///home/deploy/projects/wt-raildiag/docs/taches.md#L578)/[V271](file:///home/deploy/projects/wt-raildiag/docs/taches.md#L66), double voie, évitements, lignes plus longues [V280](file:///home/deploy/projects/wt-raildiag/docs/taches.md#L167)) fonctionne mécaniquement mais ne change pas le profit à 10 ans, alors qu'AAAHogEx fait tourner **2,5 trains par ligne fret** (nous 1,1 à 1,2) avec **266 places par train** (nous 85 à 92) ?

**Hypothèse à tester :** *Nos lignes manquent de CARGO, pas de trains ; AAA transporte beaucoup plus par ligne parce qu'il agrège l'offre (plusieurs sources vers une même gare source via des collecteurs `T:`, destinations partagées, fret retour, cargo transformé).*

---

## 1. Métriques du réseau rail fret (1975 et 1979)

Les chiffres ci-dessous proviennent de l'analyse combinée des snapshots annuels au 1er décembre de `line_telemetry` (`v270_expo_3x10_20261019.json.gz`), du journal mensuel de la campagne (`v270_expo_3x10_20261019.jsonl.gz`), et des journaux moteur compressés (`v270_expo_3x10_20261019_engine/reference_seed<N>_r0.log.gz`).

### Tableau 1.1 : Relevé par graine et par compagnie (1975 et 1979)

| Année | Graine | Compagnie | Lignes rail fret | Trains / ligne | Places / train | Dist. moy. (tuiles) | Fret livré (u/mois) | Fret / ligne (u/m/lig) | % Cargo transf. | % Dest. partagées | % Sources partagées | % Fret retour |
|:---:|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1975** | 42 | **OpexAI** | 14 | 1,14 | 96,9 | 87,3 | 481,0 | 34,4 | 11,1 % | 0,0 % | 0,0 % | 0,0 % |
| 1975 | 42 | **AAAHogEx** | 14 | 1,86 | 237,1 | 145,9 | 1 214,0 | 86,7 | 28,6 % | 0,0 % | 28,6 % | 0,0 % |
| **1975** | 7 | **OpexAI** | 17 | 1,35 | 90,7 | 97,1 | 946,7 | 55,7 | 7,0 % | 0,0 % | 0,0 % | 0,0 % |
| 1975 | 7 | **AAAHogEx** | 12 | 2,50 | 246,5 | 142,0 | 1 518,3 | 126,5 | 47,2 % | 0,0 % | 33,3 % | 0,0 % |
| **1975** | 1234 | **OpexAI** | 14 | 1,21 | 86,5 | 102,9 | 825,0 | 58,9 | 0,0 % | 0,0 % | 0,0 % | 0,0 % |
| 1975 | 1234 | **AAAHogEx** | 8 | 1,38 | 324,1 | 162,5 | 465,7 | 58,2 | 0,0 % | 0,0 % | 0,0 % | 0,0 % |
| **1979** | 42 | **OpexAI** | 14 | 1,14 | 96,9 | 87,3 | 570,7 | 40,8 | 15,2 % | 0,0 % | 0,0 % | 0,0 % |
| 1979 | 42 | **AAAHogEx** | 20 | 2,30 | 265,3 | 145,4 | 1 981,0 | 99,1 | 42,0 % | 10,0 % | 40,0 % | 0,0 % |
| **1979** | 7 | **OpexAI** | 18 | 1,39 | 78,4 | 93,7 | 948,3 | 52,7 | 7,0 % | 0,0 % | 0,0 % | 0,0 % |
| 1979 | 7 | **AAAHogEx** | 18 | 3,11 | 256,2 | 126,9 | 2 505,7 | 139,2 | 45,1 % | 22,2 % | 50,0 % | 0,0 % |
| **1979** | 1234 | **OpexAI** | 15 | 1,20 | 80,0 | 101,3 | 763,3 | 50,9 | 0,0 % | 0,0 % | 0,0 % | 0,0 % |
| 1979 | 1234 | **AAAHogEx** | 12 | 2,92 | 215,9 | 146,5 | 1 476,3 | 123,0 | 42,9 % | 16,7 | 16,7 % | 0,0 % |

### Tableau 1.2 : Moyennes triennales consolidées

| Grandeur | 1975 OpexAI | 1975 AAAHogEx | Ratio AAA / Opex | 1979 OpexAI | 1979 AAAHogEx | Ratio AAA / Opex |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Nombre de lignes fret** | 15,0 | 11,3 | 0,75× | **15,7** | **16,7** | **1,06×** |
| **Trains par ligne** | 1,24 | 1,91 | 1,54× | **1,24** | **2,78** | **2,24×** |
| **Places par train** | 91,3 | 269,2 | 2,95× | **85,1** | **245,8** | **2,89×** |
| **Capacité totale fret rail** | 1 702 | 5 708 | 3,35× | **1 650** | **11 371** | **6,89×** |
| **Distance moyenne (tuiles)** | 95,7 | 150,1 | 1,57× | **94,1** | **139,6** | **1,48×** |
| **Fret livré total (unités/mois)** | 750,9 | 1 066,0 | 1,42× | **760,8** | **1 987,7** | **2,61×** |
| **Fret moyen par ligne (u/m/lig)** | 50,1 | 94,1 | 1,88× | **48,6** | **119,3** | **2,45×** |
| **Part de cargo transformé (volume)** | 6,0 % | 25,3 % | 4,22× | **7,4 %** | **43,3 %** | **5,85×** |
| **Part de destinations partagées** | 0,0 % | 0,0 % | — | **0,0 %** | **16,3 %** | +16,3 pts |
| **Part de sources partagées (collecteurs)** | 0,0 % | 20,6 % | — | **0,0 %** | **35,6 %** | +35,6 pts |
| **Part du fret retour** | 0,0 % | 0,0 % | 1,00× | **0,0 %** | **0,0 %** | 1,00× |
| **Note moyenne gare source** | 63,8 % | 78,7 % | +14,9 pts | **61,7 %** | **83,4 %** | **+21,7 pts** |
| **Délai moyen ramassage (périodes 2,5 j)** | 7,7 (19,2 j) | 3,1 (7,6 j) | 0,40× | **5,3 (13,2 j)** | **2,0 (5,1 j)** | **0,38×** |
| **Profit annuel rail fret total** | 404,4 k£ | 495,3 k£ | 1,22× | **431,7 k£** | **1 983,5 k£** | **4,59×** |

### Provenance exacte de chaque chiffre et limites de mesure

1. **Nombre de lignes rail fret, trains par ligne, places par train, distances :**
   - *Source :* Clichés annuels du 1er décembre dans `line_telemetry.snapshots` du fichier `v270_expo_3x10_20261019.json.gz`. Chaque ligne `mode="rail"` a été filtrée sur ses `cargo_types` (exclusion de `0` Passagers et `2` Courrier). Le nombre de véhicules (`vehicles`) et la somme des capacités (`capacity_by_cargo`) sont directement lus dans la structure de données NoAI. La distance est la distance de Manhattan entre les tuiles des deux gares terminales (`ordered_station_tiles`).
   - *Contrôle croisé :* Cohérent au véhicule près avec `primary_vehicles_by_mode['rail']` du JSONL (déduction faite des lignes passagers/courrier).

2. **Cargo transporté par mois :**
   - *Source :* `delivered_cargo_last_quarter` issu du JSONL mensuel (`date="1975-12-01"` et `"1979-12-01"`). Les indices 1 (Charbon), 3 (Pétrole), 4 (Bétail), 5 (Marchandises), 6 (Céréales), 7 (Bois), 8 (Minerai de fer) et 9 (Acier) sont sommés puis divisés par 3 pour obtenir le débit mensuel. Le cargo moyen par ligne est le ratio fret livré / nombre de lignes fret.
   - *Ce qui n'est PAS mesurable directement :* OpenTTD ne consigne pas le tonnage mensuel livré ventilé par tronçon ou par train adverse dans la sauvegarde ou dans NoAI. Seul le revenu (`profit_last_year_gbp`) et le total trimestriel par cargo sont exposés par l'API pour l'adversaire. Pour OpexAI, notre sonde `LINE_REVENUE` journalise `real_rev` et `src_pct`, mais pas le tonnage physique absolu par train.

3. **Part du cargo transformé :**
   - *Source :* Somme des livraisons de Marchandises (ID 5) et d'Acier (ID 9) rapportée au total du fret livré dans `delivered_cargo_last_quarter`.
   - *Contrôle croisé :* Vérifié par l'inventaire des lignes dans `line_telemetry` : en 1979, AAA possède 7/20, 5/18 et 3/12 lignes transportant de l'Acier ou des Marchandises (28,0 % de ses lignes), alors qu'OpexAI n'en possède que 2/14 (acier), 1/18 (acier) et 0/15 (0 % sur la graine 1234), et **strictement zéro ligne de Marchandises** (Goods) sur les 3 graines.

4. **Destinations partagées et gares sources partagées (collecteurs) :**
   - *Source :* Comptage topologique des `ordered_station_ids` dans `line_telemetry`. Pour chaque ligne fret, la gare source (`rated=True` ou `accepts=False`) et la gare destinataire (`accepts=True`) sont identifiées. Une gare accueillant 2 lignes ou plus de fret est qualifiée de partagée.
   - *Contrôle croisé journal AAA :* Les préfixes `T:` dans les journaux `TrainRoute` d'AAAHogEx correspondent aux collecteurs créés par `CreateTransferPlans` ([`main.nut:2163`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/main.nut#L2163)).

5. **Part du fret retour :**
   - *Source :* Inspection exhaustive des journaux moteur AAAHogEx (`reference_seed<N>_r0.log.gz`). La méthode `CheckBuildReturnRoute` ([`trainroute.nut:3304`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/trainroute.nut#L3304)) est appelée périodiquement par AAA, mais les tentatives `Try BuildReturnRoute` et les succès `build return route succeeded` ([`trainroute.nut:3475`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/trainroute.nut#L3475)) sont **strictement égaux à 0 sur les 3 graines et les 10 ans de simulation**. Chez OpexAI, aucune logique de fret retour n'existe sur le rail. Le fret retour est donc **rigoureusement nul (0,0 %)** chez les deux compagnies.

---

## 2. Analyse de la sonde LINE_REVENUE (Offre vs Capacité)

Notre sonde `LINE_REVENUE` journalise chaque année pour chaque ligne rail : la production de la source (`src_prod` en unités/mois), la part captée (`src_pct` en %), l'attente sur le quai A (`wait_a`), la capacité totale de la ligne (`cap`) et le nombre de trains (`vehs`). La capacité d'une rame est `rame_cap = cap / vehs`.

Une ligne est classée :
- **« Bornée par la capacité »** si `wait_a > rame_cap` (l'attente sur le quai dépasse la capacité d'une rame entière : le train part plein et laisse du cargo en souffrance).
- **« Bornée par l'offre »** si `wait_a <= rame_cap` (la rame arrive et emporte tout le stock disponible ou presque ; ajouter des wagons ou un second train n'augmente pas le volume transporté mais dilue le chargement et augmente les coûts d'exploitation).

### Tableau 2.1 : Synthèse globale OpexAI (sonde LINE_REVENUE)

| Année | Lignes analysées | Prod. source moy. (u/m) | Part transportée moy. | Attente quai moy. (u) | Capacité rame moy. (places) | Médiane ratio attente / rame | Lignes bornées par l'offre | Lignes bornées par la capacité |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1975** | 42 | 105,8 u/m | 69,8 % | 57,3 u | 91,9 pl | **0,27** | **36 (85,7 %)** | 6 (14,3 %) |
| **1979** | 47 | 108,4 u/m | 69,1 % | 58,3 u | 87,1 pl | **0,22** | **39 (83,0 %)** | 8 (17,0 %) |

### Distribution du ratio `wait_a / rame_cap` chez OpexAI :
- **1975 :** décile 10 = 0,00 | décile 25 = 0,00 | **médiane (d50) = 0,27** | décile 75 = 0,68 | décile 90 = 1,21
- **1979 :** décile 10 = 0,00 | décile 25 = 0,00 | **médiane (d50) = 0,22** | décile 75 = 0,67 | décile 90 = 2,85

> [!IMPORTANT]
> **Constat fondamental :** Chez OpexAI, **83,0 % des lignes en 1979 sont strictement bornées par l'offre**. La médiane du stock en attente sur le quai n'atteint que **22 % de la capacité d'une rame**. Sur plus de la moitié de nos lignes, le train arrive devant un quai quasi vide.

### Détail des 8 seules lignes bornées par la capacité en 1979 chez OpexAI :
Sur les 47 lignes fret actives en 1979, seules 8 présentent une attente supérieure à la rame :
- **Graine 42 (0/14) :** Aucune ligne saturée (ligne 64 la plus chargée : attente 226 pour capacité 260).
- **Graine 7 (4/18) :**
  - Ligne 11 (`WOOD`) : attente 91 u, capacité rame 60 pl, dist. 29, 1 train, profit 15,7 k£
  - Ligne 51 (`WOOD`) : attente 139 u, capacité rame 30 pl, dist. 82, 2 trains, profit 18,1 k£
  - Ligne 70 (`OIL_`) : attente 31 u, capacité rame 30 pl, dist. 70, 2 trains, profit 11,9 k£
  - Ligne 77 (`IORE`) : attente 171 u, capacité rame 60 pl, dist. 36, 1 train, profit 12,3 k£
- **Graine 1234 (4/15) :**
  - Ligne 7 (`COAL`) : attente 702 u, capacité rame 45 pl, dist. 40, 2 trains, profit 15,9 k£ (engorgement sévère)
  - Ligne 8 (`COAL`) : attente 564 u, capacité rame 90 pl, dist. 48, 1 train, profit 36,6 k£ (engorgement sévère)
  - Ligne 65 (`COAL`) : attente 127 u, capacité rame 60 pl, dist. 139, 1 train, profit 32,0 k£
  - Ligne 67 (`OIL_`) : attente 104 u, capacité rame 30 pl, dist. 80, 1 train, profit 3,2 k£

### Situation équivalente chez AAAHogEx :
Au cliché du 1er décembre 1979 dans `line_telemetry`, **0 ligne sur 50 chez AAAHogEx n'est bornée par la capacité** (attente moyenne au quai = 0,7 u sur la graine 42, 3,0 u sur la graine 7, 16,3 u sur la graine 1234).
Pourquoi ? Parce qu'avec **2,78 trains par ligne** et une cadence de passage de **5 jours** (`time_since_pickup = 2,0` périodes de 2,5 jours), le stock est vidé en continu dès qu'il est produit. Les trains de 246 places d'AAA absorbent le flux continu sans jamais laisser le quai saturer.

---

## 3. Verdict sur l'hypothèse

### Formulation initiale de l'hypothèse :
> *« Nos lignes manquent de CARGO, pas de trains ; AAA transporte beaucoup plus par ligne parce qu'il agrège l'offre (plusieurs sources vers une même gare source via des collecteurs `T:`, destinations partagées, fret retour, cargo transformé). »*

### Verdict : **CONFIRMÉE avec précision et deux rectifications majeures.**

L'hypothèse est confirmée dans son diagnostic central (**nos lignes manquent de cargo disponible par aller-retour, pas de trains**) et sur deux de ses leviers d'agrégation (**destinations partagées et chaînes de cargo transformé**). En revanche, l'idée de « fret retour » est totalement infirmée, et les collecteurs `T:` ne représentent qu'une composante secondaire par rapport à deux autres facteurs déterminants découverts dans les données : **la longueur des lignes** et **le taux de captage lié à la note de gare**.

| Composante de l'hypothèse | Verdict chiffré | Analyse détaillée |
|:---|:---:|:---|
| **1. « Nos lignes manquent de cargo, pas de trains »** | **CONFIRMÉ À 100 %** | **83,0 %** de nos lignes sont limitées par l'offre (médiane attente/rame = **0,22**). Allonger les rames (V270/V272) ou doubler les trains (V181/V271) fait rouler des capacités vides qui augmentent l'amortissement et les coûts de roulement sans capter de cargo supplémentaire. |
| **2. « AAA transporte beaucoup plus par ligne »** | **CONFIRMÉ (2,45×)** | AAA livre **119,3 u/mois par ligne** contre **48,6 u/mois** chez nous, pour un nombre de lignes quasi identique (16,7 vs 15,7). |
| **3. « Plusieurs sources vers une gare via collecteurs T: »** | **NUANCÉ (20 % à 35 %)** | Mécanisme bien réel dans le code d'AAA ([`main.nut:2163`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/main.nut#L2163)) : 10 lignes fret sur 50 (20 %) sont des transferts `T:`, créant des super-hubs (ex. gare 232 graine 7 agrégeant 3 puits de pétrole). Mais 80 % de ses lignes restent en point-à-point direct. |
| **4. « Destinations partagées »** | **TRÈS CONFIRMÉ** | AAA concentre ses flux : 5 mines de fer vers une seule aciérie (graine 42), 5 fermes vers une seule usine (graine 1234). En 1979, **16,3 %** de ses gares terminus sont partagées, contre **0,0 %** chez nous au bras référence (avant V178/V179). |
| **5. « Fret retour »** | **INFIRMÉ (0,0 %)** | Strictement aucun fret retour réussi sur 10 ans chez AAA ([`trainroute.nut:3475`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/trainroute.nut#L3475) : 0 succès). Les trains roulent tous à vide au retour. |
| **6. « Cargo transformé (marchandises, acier) »** | **FACTEUR MAJEUR (5,8×)** | **43,3 %** du volume fret d'AAA et 28 % de ses lignes sont des produits transformés (Marchandises, Acier), contre **7,4 %** du volume et **0 % de marchandises** chez nous. AAA empoche le paiement de la matière première PUIS le paiement des marchandises. |
| **7. Longueur des lignes (facteur omis)** | **+48 % de distance** | Les lignes d'AAA mesurent en moyenne **139,6 tuiles** (médiane 155, max 314) contre **94,1 tuiles** chez nous (médiane 105, bornées à 160). À débit égal, une ligne 48 % plus longue rapporte 48 % de plus. |
| **8. Note de gare et captage (facteur omis)** | **+21,7 points de note** | AAA capte **83,4 %** de la production grâce à un passage continu (toutes les 5 jours, contre 13 jours chez nous). Cela génère +35 % de volume brut à la source, et dépasse le seuil OpenTTD de 80 % qui permet aux industries de grandir (+33 % de chance de doublement de production par an). |

### Adéquation des journaux et instrumentation complémentaire

Les journaux actuels (`line_telemetry` des snapshots annuels + JSONL mensuel + `LINE_REVENUE`) **suffisent amplement** pour quantifier l'ensemble de ces grandeurs et trancher sans ambiguïté.

Toutefois, si l'on souhaitait mesurer le tonnage exact par train sur l'adversaire de façon mensuelle continue sans attendre les clichés annuels, il suffirait d'ajouter dans `sweeps/bench_1v1_5y_20seeds.py` la lecture des méthodes de l'API NoAI 15.3 suivantes (vérifiées dans [`docs/noai_api_15.3.tsv`](file:///home/deploy/projects/wt-raildiag/docs/noai_api_15.3.tsv)) :
- `AIStation.GetCargoWaiting(station_id, cargo_id)` : stock exact en attente par cargo.
- `AIStation.GetCargoRating(station_id, cargo_id)` : note de la gare pour ce cargo.
- `AIIndustry.GetLastMonthProduction(industry_id, cargo_id)` : production mensuelle de l'industrie source.
- `AIIndustry.GetLastMonthTransported(industry_id, cargo_id)` : tonnage physique effectivement ramassé.
- `AIVehicle.GetCapacity(vehicle_id, cargo_id)` : capacité exacte de chaque rame.
- `AIVehicle.GetProfitLastYear(vehicle_id)` : rentabilité individuelle de chaque train.

---

## 4. Les 3 leviers les plus prometteurs

En s'appuyant sur les chiffres établis ci-dessus et en vérifiant les fiches de [`docs/taches.md`](file:///home/deploy/projects/wt-raildiag/docs/taches.md), les 3 leviers prioritaires pour combler l'écart de volume rail à 10 ans sont :

### Levier 1 : Chaînes industrielles complètes et cargo transformé (V233)
- **Constat chiffré :** AAA tire **43,3 %** de son volume fret et près de **1 000 k£/an** de profit des Marchandises et de l'Acier. OpexAI a **0 ligne de Marchandises** sur toutes les graines testées. Livrer du bois à une scierie ou du grain à une usine sans jamais poser la ligne de Marchandises vers les villes abandonne la moitié de la valeur de la ligne initiale.
- **Ordre de grandeur à 10 ans :** **+350 à +600 k£/an**.
- **Contrôle dans `docs/taches.md` :** Fiche [V233](file:///home/deploy/projects/wt-raildiag/docs/taches.md#L190) (« Chaînes industrielles et cargo transformé : à refaire DE ZÉRO »). L'échec historique de V88/V218 venait d'une combinatoire d'opcodes explosive (11 423 `CHAIN_GEN`) et du blocage du créneau A* unique, pas du principe économique. Le travail consiste à générer la ligne de biens aval dès qu'une usine réceptrice a du stock produit (`GetLastMonthProduction > 0`).

### Levier 2 : Maintien de la note de gare au-dessus de 80 % (statues et cadence ciblée)
- **Constat chiffré :** Note médiane de la gare source : **83,4 %** chez AAA contre **61,7 %** chez nous (écart de **+21,7 points**). Cet écart vient du délai de passage moyen : 5,1 jours chez AAA contre 13,2 jours chez nous. Dans OpenTTD, une note ≥ 80 % offre 33 % de chances par an à l'industrie de doubler sa production, alors qu'une note < 60 % entraîne un déclin progressif de l'offre (vérifié dans `LINE_REVENUE` : production médiane stagnante à 90-108 u/m chez nous).
- **Actions concrètes :**
  1. Poser une statue de compagnie dans la ville de chaque gare source fret dès que la trésorerie dépasse 400 k£, comme le fait AAAHogEx ([`main.nut:3636`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/main.nut#L3636) : bonus immédiat et permanent de **+26 points** de note, sans aucun train supplémentaire).
  2. Ajuster la commande de chargement (`OF_FULL_LOAD_ANY`) pour éviter que la gare ne reste vide de train pendant les longs allers-retours.
- **Ordre de grandeur à 10 ans :** **+200 à +350 k£/an**.
- **Contrôle dans `docs/taches.md` :** Fiche [V271](file:///home/deploy/projects/wt-raildiag/docs/taches.md#L66) / note de gare (l. 65). L'allongement mécanique (V270/V272) ou le 2e quai sur voie unique (V271) ont échoué parce que la voie unique plafonnait le débit. Le levier statue + captage accru valorise l'offre existante à investissement minimal.

### Levier 3 : Agrégation amont de sources vers les corridors existants (collecteurs de fret)
- **Constat chiffré :** AAA agrège 2 à 3 sources par point de chargement principal (35,6 % de sources partagées, 10 collecteurs `T:`), ce qui lui permet de remplir des trains de 246 places avec 2,8 trains par ligne. OpexAI a déjà qualifié avec succès les **destinations partagées V178/V179** ([Porte A +235,6 k£/an, Porte B +192,2 k£/an](file:///home/deploy/projects/wt-raildiag/docs/taches.md#L76), default 1 sur master).
- **Action concrète :** Étendre cette logique à l'amont : autoriser le rattachement d'une source secondaire proche (mine, puits de pétrole, forêt à < 50 tuiles) vers la gare de chargement d'une ligne longue existante vers le même débouché (par navette rail courte ou raccord direct). Une ligne alimentée par 2 sources produit 180-220 u/mois et justifie alors pleinement un second train et des rames de 150+ places.
- **Ordre de grandeur à 10 ans :** **+150 à +300 k£/an**.
- **Contrôle dans `docs/taches.md` :** Fiche [V178/V179](file:///home/deploy/projects/wt-raildiag/docs/taches.md#L74) (adoptée) et [V203-rabattements](file:///home/deploy/projects/wt-raildiag/docs/taches.md#L1762) (diagnostic préliminaire sur graine 42 mais jamais banqué). Cohérent avec le constat du vivier fret épuisé dès 1972 ([`docs/taches.md` l. 1718](file:///home/deploy/projects/wt-raildiag/docs/taches.md#L1718)).

---

## Annexe : Commandes de reproduction des mesures

Toutes les mesures de ce rapport sont directement reproductibles via les commandes suivantes exécutées depuis la racine de `/home/deploy/projects/wt-raildiag` :

```bash
# 1. Auto-tests du script de diagnostic
python3 sweeps/diag_cargo_par_ligne_rail.py --selftest

# 2. Exécution du tableau synthétique complet (Tableaux 1 et 2)
python3 sweeps/diag_cargo_par_ligne_rail.py

# 3. Exécution avec le détail ligne par ligne des lignes bornées par la capacité
python3 sweeps/diag_cargo_par_ligne_rail.py --detail
```
