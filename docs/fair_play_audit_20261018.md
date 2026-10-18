# Audit d'exhaustivité des comportements OpexAI pour le mode `fair_play`

**Date :** 18 octobre 2026  
**Branche :** `fairplay` (dépôt `/home/deploy/projects/wt-fairplay`)  
**Statut :** Étape 1 de la tâche « Mode `fair_play` explicite » — Audit exhaustif et proposition de spécification (aucun code modifié dans `ai/`).

---

## 1. Contexte et principes directeurs

### 1.1 Objectif
L'objectif du mode `fair_play` est de permettre à un joueur humain de partager agréablement une carte avec OpexAI, sans subir de comportements toxiques, agressifs, déloyaux ou « exploits » moteur (parasitage de gares, pillage de créneaux d'aéroports, arrêts de bus fantômes pour siphonner les passagers, droits exclusifs paralysant le réseau adverse, pollution de la carte par des panneaux de diagnostic, démolitions urbaines massives, etc.).

Le mode `fair_play` ne doit toutefois **pas neutraliser arbitrairement toute concurrence économique saine** : OpexAI doit continuer à gérer son capital, construire des lignes rentables, renouveler sa flotte et concourir loyalement au développement des transports.

### 1.2 Limite NoAI fondamentale : Absence de distinction Humain / IA (C88)
L'audit préalable C88 (`docs/c88_compagnies_humaines_ia_20261008.md`) a formellement démontré sur le tag OpenTTD 15.3 :
- L'API NoAI n'expose aucune fonction du type `IsAICompany`, `IsHumanCompany` ou `CompanyProperties::is_ai`.
- `AICompany.IsMine(company)` distingue uniquement notre propre compagnie des tiers.
- `AITile.GetOwner(tile)` et `AIStation.GetOwner(station)` renvoient un identifiant de compagnie propriétaire, sans renseigner sur sa nature humaine ou artificielle.
- Même côté moteur interne C++, un humain peut rejoindre une compagnie IA ; le champ interne `is_ai` n'est donc pas une preuve d'exclusivité humaine.

**Conséquence architecturale inviolable :**
Le mode `fair_play` ne doit **jamais** tenter d'identifier si une compagnie adverse est un humain ou une IA. Les règles de courtoisie et de fair-play définies ci-dessous s'appliquent de manière **uniforme et causale envers toute autre compagnie tierce** présente sur la carte (`owner != me`).

### 1.3 Articulation avec les niveaux de difficulté (`opex_difficulty`)
Le 18 octobre 2026, la gestion de difficulté à 4 niveaux a été unifiée dans `ai/OpexAI/difficulty.nut` (`OPEX_DIFFICULTY`, défaut 2 = difficile) :
- **Niveau 0 (facile)** : brides sur captage gares (`encroach_rival_catchment`), villes aéroport rivales (`airport_rival_town`), etc.
- **Niveau 1 (moyen)** : autorise les villes rivales mais bride le dernier créneau d'aéroport (`preempt_last_airport_slot`) et les industries primaires rivales (`compete_primary_industry`).
- **Niveau 2 (difficile - DÉFAUT ACTUEL)** : autorise tous les comportements concurrentiels ordinaires, mais coupe les gestes anticoncurrentiels hostiles (`v250_rights = 3`, `anticompetitive = 3`).
- **Niveau 3 (custom)** : autorise l'ensemble des comportements, y compris les droits exclusifs V250 si configurés.

Le mode `fair_play` doit pouvoir être activé de manière orthogonale (ou comme sur-bride stricte) pour garantir un jeu civilisé, même face à un joueur choisissant une difficulté difficile ou sur mesure.

---

## 2. Audit exhaustif des comportements par catégorie

---

### Catégorie 1 : Implantation concurrentielle et captage

#### 1.1 Gares ferroviaires en captage partagé / chevauchement (Station catchment encroachment)
- **Fichier et lignes :** [`ai/OpexAI/builder_rail.nut:337-344`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/builder_rail.nut#L337-L344) et [`ai/OpexAI/spatial.nut:117-147`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/spatial.nut#L117-L147) (`OpexStationEncroachesRival`).
- **Réglage :** `encroach_rival_catchment` dans [`ai/OpexAI/difficulty.nut:38`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/difficulty.nut#L38) (`min_level = 1`).
- **Défaut actuel et effet par niveau :**
  - Au défaut actuel (`opex_difficulty = 2`), ce comportement est **AUTORISÉ** (`OPEX_LEVEL_LIMITS` est faux).
  - Au niveau 0 : interdit (aucune gare ne peut chevaucher le captage d'une gare adverse).
  - Aux niveaux 1, 2 et 3 : autorisé. OpexAI peut poser une gare ferroviaire dont le rayon de captage (4 cases de rayon standard) englobe des tuiles déjà couvertes par la gare d'un joueur, lui siphonnant une partie de ses passagers/fret selon les notes respectives.
- **Garde-fous existants :** `OpexStationEncroachesRival` vérifie si une tuile `AITile.IsStationTile` appartenant à un tiers se trouve dans la zone de captage étendue. Mais cette garde est désarmée aux niveaux 1, 2 et 3.
- **Proposition en mode `fair_play` :** **COUPÉ**.
  - *Justification :* Le parasitage direct d'une gare existante d'un humain (« station poaching ») est l'une des sources majeures de frustration. En mode `fair_play`, `encroach_rival_catchment` doit être coupé (interdiction de chevauchement de captage, exactement comme au niveau 0).

#### 1.2 Arrêts routiers (bus et camions) en chevauchement de captage
- **Fichier et lignes :** [`ai/OpexAI/builder_road.nut:161-174`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/builder_road.nut#L161-L174) et [`ai/OpexAI/builder_road.nut:423`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/builder_road.nut#L423).
- **Réglage :** `encroach_rival_catchment` dans [`ai/OpexAI/difficulty.nut:38`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/difficulty.nut#L38).
- **Défaut actuel et effet par niveau :**
  - Au niveau 0 : filtré via `OpexStationEncroachesRival`.
  - Au niveau 2 (défaut) et 1/3 : **AUTORISÉ**. Les arrêts de bus ou zones de chargement de camions peuvent recouvrir le captage d'arrêts ou gares existants d'un tiers.
- **Garde-fous existants :** Filtrage `OpexRoadSitesGated` sous garde `OPEX_LEVEL_LIMITS`.
- **Proposition en mode `fair_play` :** **COUPÉ**.
  - *Justification :* Même règle que pour le ferroviaire.

#### 1.3 Gares maritimes (quais / docks) en captage partagé
- **Fichier et lignes :** [`ai/OpexAI/builder_water.nut:145-165`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/builder_water.nut#L145-L165) (`OpexWaterFindDockSite`) et [`ai/OpexAI/builder_water.nut:530-550`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/builder_water.nut#L530-L550).
- **Réglage :** Aucun réglage propre (hors `mode_water` et `v220_water_enable`).
- **Défaut actuel et effet par niveau :**
  - **TOTALEMENT ABSENT DE TOUTE GARDE DE NIVEAU** à ce jour ! `builder_water.nut` n'appelle jamais `OpexStationEncroachesRival`.
  - OpexAI peut poser un quai directement à côté du quai ou de la gare d'un autre joueur, à n'importe quel niveau de difficulté.
- **Garde-fous existants :** Seule la faisabilité technique (`AITestMode() AIMarine.BuildDock`) est vérifiée.
- **Proposition en mode `fair_play` :** **COUPÉ / BORNÉ**.
  - *Justification :* Soumettre la sélection de site de quai maritime à `OpexStationEncroachesRival` en mode `fair_play`.

#### 1.4 Arrêts routiers joints aux aéroports ("Station-spread exploit / arrêts fantômes")
- **Fichier et lignes :** [`ai/OpexAI/air_construction.nut:55-155`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/air_construction.nut#L55-L155) (`OpexAirBuildJoinedStops`), [`ai/OpexAI/air_construction.nut:447, 456`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/air_construction.nut#L447) et [`ai/OpexAI/globals_pre.nut:144`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/globals_pre.nut#L144).
- **Réglage :** Constante hardcodée `AIR_JOINED_STOP_LIMIT <- 2`. Aucun réglage utilisateur dans `info.nut` ni `settings.nut` !
- **Défaut actuel et effet par niveau :**
  - **ACTIF PAR DÉFAUT à TOUS LES NIVEAUX** (0, 1, 2, 3) dès que `MODE_ROAD` et `MODE_AIR` sont actifs !
  - **Mécanisme :** Construit 1 à 2 arrêts de bus traversants sur la voirie urbaine, jusqu'à 12 tuiles (`station_spread`) de l'aéroport, joints à la même station. **AUCUN BUS NE DESSERT CES ARRÊTS.** Ce sont des extensions artificielles de captage qui siphonnent les passagers du cœur de ville directement dans l'aéroport sans frais de transport routier.
  - De plus, à la ligne 143 : si la mairie refuse l'arrêt (`ERR_LOCAL_AUTHORITY_REFUSES`), OpexAI appelle `OpexBoostTownRating` pour planter 40 arbres et forcer la pose de l'arrêt !
- **Garde-fous existants :** Limité à 2 arrêts, vérification de distance Manhattan minimale entre arrêts.
- **Proposition en mode `fair_play` :** **STRICTEMENT COUPÉ** (`AIR_JOINED_STOP_LIMIT = 0`).
  - *Justification :* C'est l'un des comportements les plus flagrants de « triche légale » / exploit de moteur. Pour un joueur humain, voir une IA planter des arrêts de bus fantômes sur les routes municipales pour aspirer tous les passagers vers un aéroport en périphérie est ressenti comme un abus inacceptable.

#### 1.5 Arrêts routiers joints aux gares ferroviaires
- **Fichier et lignes :** [`ai/OpexAI/task_rail.nut:1149-1158`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/task_rail.nut#L1149-L1158), [`ai/OpexAI/settings.nut:116-117`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/settings.nut#L116-L117) et [`ai/OpexAI/globals_pre.nut:43`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/globals_pre.nut#L43).
- **Réglage :** `v207_rail_pax_joined_stops` (entier 0..4).
- **Défaut actuel et effet par niveau :** Défaut 0 (inactif). Identique à tous les niveaux.
- **Garde-fous existants :** Contrôlé par le réglage.
- **Proposition en mode `fair_play` :** **MAINTENIR STRICTEMENT COUPÉ** (valeur forcée à 0).

#### 1.6 Aéroports dans une ville déjà pourvue d'un aéroport rival
- **Fichier et lignes :** [`ai/OpexAI/air_towns.nut:618-639`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/air_towns.nut#L618-L639) (`OpexTownAirportAllowedByLevel`), [`ai/OpexAI/air_planning.nut:369, 1108`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/air_planning.nut#L369) et [`ai/OpexAI/difficulty.nut:34`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/difficulty.nut#L34).
- **Réglage :** `airport_rival_town` dans `difficulty.nut` (`min_level = 1`).
- **Défaut actuel et effet par niveau :**
  - Au niveau 0 : interdit (aucun aéroport si un rival est déjà présent).
  - Aux niveaux 1, 2 (défaut) et 3 : **AUTORISÉ**. OpexAI peut poser un aéroport dans la même ville qu'un concurrent.
- **Garde-fous existants :** `OpexTownRivalAirports` compte les aéroports rivaux existants.
- **Proposition en mode `fair_play` :** **BORNÉ**.
  - *Justification :* « Ce n'est que de la concurrence économique normale » qu'une grande métropole puisse accueillir deux aéroports concurrents, TANT QUE l'IA ne sature pas la ville en prenant le dernier créneau disponible (voir 2.1 ci-dessous). En fair-play : autorisé uniquement si la ville a encore au moins 2 créneaux de bruit disponibles, ou interdite si l'utilisateur choisit un profil fair-play strict.

---

### Catégorie 2 : Occupation de sites rares

#### 2.1 Préemption du dernier créneau d'aéroport municipal
- **Fichier et lignes :** [`ai/OpexAI/air_towns.nut:642-664`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/air_towns.nut#L642-L664) et [`ai/OpexAI/difficulty.nut:33`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/difficulty.nut#L33).
- **Réglage :** `preempt_last_airport_slot` dans `difficulty.nut` (`min_level = 2`).
- **Défaut actuel et effet par niveau :**
  - Au niveau 2 (défaut) et au niveau 3 : **AUTORISÉ**. OpexAI s'autorise à poser le second aéroport dans une ville où un joueur est seul avec 1 aéroport (`GetAllowedNoise == 1`), prenant le dernier créneau disponible et interdisant définitivement au joueur d'agrandir son installation ou d'en poser un second.
  - Aux niveaux 0 et 1 : interdit (sauf si la ville est dans le quart supérieur de population `topPopThreshold`).
- **Garde-fous existants :** Vérification `own == 0 && rivals == 1 && isLastSlot`.
- **Proposition en mode `fair_play` :** **STRICTEMENT COUPÉ**.
  - *Justification :* Bloquer le dernier créneau d'aéroport d'une ville déjà occupée par un humain est une agression territoriale directe. En `fair_play`, OpexAI ne doit jamais prendre le dernier créneau d'une ville où un concurrent est déjà implanté.

#### 2.2 Course agressive aux créneaux en début de partie (Early slot rush)
- **Fichier et lignes :** [`ai/OpexAI/projects_selection.nut:349-390`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/projects_selection.nut#L349-L390) et [`ai/OpexAI/globals_pre.nut:147-149`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/globals_pre.nut#L147-L149).
- **Réglage :** Constantes `AIR_EARLY_SLOT_TARGET_TOWNS = 6`, `AIR_EARLY_SLOT_BONUS_PCT = 50`, `AIR_EARLY_SLOT_MIN_POP = 1000`. Pas de réglage dans `info.nut`.
- **Défaut actuel et effet par niveau :**
  - **ACTIF PAR DÉFAUT à TOUS LES NIVEAUX** (0..3).
  - Donne artificiellement un bonus de score de +50 % aux projets reliant les 6 premières grandes villes pour verrouiller les créneaux d'aéroport avant quiconque.
- **Garde-fous existants :** S'arrête dès que 6 villes sont desservies.
- **Proposition en mode `fair_play` :** **INCHANGÉ AVEC JUSTIFICATION ou BORNÉ**.
  - *Justification :* « Ce n'est que de la concurrence économique normale » de chercher à relier les plus grandes villes dès le début. Tant que les règles 2.1 (pas de vol du dernier créneau) et 2.3 (pas de double aéroport) s'appliquent, l'humain n'est pas bloqué. Alternativement, le bonus artificiel de +50 % peut être ramené à 0 pour laisser les liaisons se sélectionner sur leur pur mérite économique sans politique de ruée agressive.

#### 2.3 Verrouillage de monopole d'aéroport dans une même ville (Double slot capture)
- **Fichier et lignes :** [`ai/OpexAI/projects_selection.nut:416-417, 434-438, 461-465`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/projects_selection.nut#L416) (`ownSecondA`, `ownSecondB`).
- **Réglage :** Logique interne C83 (projet aérien avec second aéroport propre).
- **Défaut actuel et effet par niveau :**
  - Permet à OpexAI de construire un deuxième aéroport dans une ville où elle en possède déjà un, si `slotsRemaining == 1`, monopolisant ainsi 100 % des créneaux de la ville (2 sur 2) et empêchant tout autre joueur d'y voler.
- **Garde-fous existants :** Filtre de population et de rentabilité.
- **Proposition en mode `fair_play` :** **STRICTEMENT COUPÉ**.
  - *Justification :* Une compagnie ne doit pas confisquer les deux seuls créneaux d'une ville. Plafonner OpexAI à un seul aéroport par ville en fair-play.

#### 2.4 Gares sur industries primaires déjà desservies par un concurrent
- **Fichier et lignes :** [`ai/OpexAI/spatial.nut:88-112`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/spatial.nut#L88-L112) (`OpexIndustryPrimaryRivalServed`), [`ai/OpexAI/builder_rail.nut:299-302`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/builder_rail.nut#L299-L302), [`ai/OpexAI/builder_road.nut:154-159`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/builder_road.nut#L154-L159), [`ai/OpexAI/candidates.nut:1083, 1584, 1962`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/candidates.nut#L1083) et [`ai/OpexAI/difficulty.nut:37`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/difficulty.nut#L37).
- **Réglage :** `compete_primary_industry` dans `difficulty.nut` (`min_level = 2`).
- **Défaut actuel et effet par niveau :**
  - Au niveau 2 (défaut) et 3 : **AUTORISÉ**. OpexAI peut poser une gare ou station de chargement directement sur une mine de charbon, mine de fer, forêt ou ferme qu'un joueur humain exploite déjà, divisant la production de la ressource.
  - Aux niveaux 0 et 1 : interdit (`OpexIndustryPrimaryRivalServed` rejette la ressource si une gare rivale capte la production).
- **Garde-fous existants :** Détection via `AITileList_IndustryProducing` et `AITile.GetOwner`.
- **Proposition en mode `fair_play` :** **STRICTEMENT COUPÉ**.
  - *Justification :* Les industries primaires (mines, forêts, fermes) ont une production limitée. Venir se brancher sur une mine découverte et raccordée par un humain est considéré comme un pillage hostile très irritant. En fair-play, respecter la priorité du premier arrivé sur les industries extractives.

#### 2.5 Dessertes d'industries transformatrices secondaires (usines, aciéries, scieries - V233)
- **Fichier et lignes :** [`ai/OpexAI/goods_v233.nut:1-460`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/goods_v233.nut#L1-L460) et [`ai/OpexAI/candidates.nut:1450-1600`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/candidates.nut#L1450-L1600).
- **Réglage :** `v233_goods_graft` (défaut 0 dans `info.nut:645`).
- **Défaut actuel et effet par niveau :** Défaut 0 (inactif sur master).
- **Garde-fous existants :** Seuil de production mensuelle minimale V233.
- **Proposition en mode `fair_play` :** **INCHANGÉ AVEC JUSTIFICATION**.
  - *Justification :* « Ce n'est que de la concurrence économique normale » : les industries secondaires acceptent des cargaisons illimitées sans pénaliser les autres transporteurs (au contraire, apporter du minerai enrichit la production de l'usine pour tous). Transporter des marchandises depuis une usine partagée est un jeu économique sain.

---

### Catégorie 3 : Constructions gênantes, voirie, démolitions et terrain

#### 3.1 Démolition de maisons urbaines et de voirie lors de la pose ferroviaire (V199)
- **Fichier et lignes :** [`ai/OpexAI/builder_rail.nut:2037-2047`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/builder_rail.nut#L2037-L2047) (`OpexV199CanDemolishTile`) et [`ai/OpexAI/builder_rail.nut:2317-2335`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/builder_rail.nut#L2317-L2335).
- **Réglage :** `v199_robust_build` (booléen, défaut 0 dans `info.nut:601`).
- **Défaut actuel et effet par niveau :**
  - Défaut 0 (inactif).
  - Si activé : lorsqu'une tuile est bloquée (`ERR_AREA_NOT_CLEAR`), OpexAI tente de la démolir via `AITile.DemolishTile(cur)`. Cela peut détruire des bâtiments municipaux (maisons) ou des tronçons de route municipale.
- **Garde-fous existants :** Ne démolit pas le rail adverse ni les stations/dépôts, ne démolit pas l'eau.
- **Proposition en mode `fair_play` :** **STRICTEMENT COUPÉ** (forcé à 0).
  - *Justification :* Couper des routes de ville (qui cassent les lignes de bus humaines) ou raser des maisons (qui fait chuter la note municipale de tous les joueurs et défigure la ville) est inadmissible en jeu convivial.

#### 3.2 Nivellement d'emprise et terraformage étendu
- **Fichier et lignes :**
  - Aéroports : [`ai/OpexAI/air_sites.nut:143-159`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/air_sites.nut#L143-L159) (`OpexAirLevelFootprint`).
  - Voie ferrée : [`ai/OpexAI/builder_rail.nut:2200-2225`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/builder_rail.nut#L2200-L2225) (`AITile.LevelTiles`, `AITile.LowerTile`, `AITile.RaiseTile`), budget `v199_level_budget_k` (défaut 20).
  - Templates de gares : [`ai/OpexAI/rail_templates.nut:194, 200`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/rail_templates.nut#L194).
- **Réglage :** Actif en dur pour les aéroports et templates de gares ; contrôlé par `v199_robust_build` pour les voies doubles.
- **Défaut actuel et effet par niveau :**
  - Pour les aéroports, LevelTiles nivelle des rectangles entiers jusqu'à 6×6 cases. En modifiant les hauteurs des coins, le terraformage impacte les tuiles immédiatement voisines, pouvant briser des voies ou routes d'un joueur adjacent par création de falaises abruptes.
- **Garde-fous existants :** Vérifications de budget et de constructibilité.
- **Proposition en mode `fair_play` :** **BORNÉ**.
  - *Justification :* En fair-play, interdire formellement tout `LevelTiles` ou terraformage (`RaiseTile`/`LowerTile`) si le périmètre direct touche une infrastructure appartenant à une autre compagnie (`AITile.GetOwner != me`).

#### 3.3 Plantation massive d'arbres pour forcer l'accord municipal ("Tree spamming")
- **Fichier et lignes :** [`ai/OpexAI/candidates.nut:1802-1844`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/candidates.nut#L1802-L1844) (`OpexBoostTownRating`), appelé dans :
  - [`ai/OpexAI/air_sites.nut:148`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/air_sites.nut#L148)
  - [`ai/OpexAI/air_construction.nut:143, 239, 298`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/air_construction.nut#L143)
  - [`ai/OpexAI/builder_rail.nut:5075`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/builder_rail.nut#L5075)
- **Réglage :** AUCUN réglage dans `info.nut` ni `settings.nut` ! (L'ancien réglage `tree_planting` est obsolète ; l'appel réactif suite à `ERR_LOCAL_AUTHORITY_REFUSES` est inconditionnel).
- **Défaut actuel et effet par niveau :**
  - **ACTIF PAR DÉFAUT à TOUS LES NIVEAUX**.
  - Dès qu'une municipalité refuse des travaux (nivellement d'aéroport, arrêt de bus joint ou gare ferroviaire), OpexAI plante instantanément jusqu'à 40 arbres (`radius = 7`) sur toutes les cases libres de la ville pour contourner le veto municipal (+7 points de réputation par arbre).
- **Garde-fous existants :** Arrêt si `rating > MEDIOCRE`, plafond à 40 arbres.
- **Proposition en mode `fair_play` :** **STRICTEMENT COUPÉ ou FORTEMENT BORNÉ**.
  - *Justification :* Ce "tree spam" est un exploit classique d'IA qui sature la ville d'arbres et contourne artificiellement le mécanisme de réputation. Si la ville refuse, l'IA doit accepter le refus et chercher un autre site ou attendre, comme un joueur humain.

#### 3.4 Passages à niveau sur voirie (Level crossings)
- **Fichier et lignes :** [`ai/OpexAI/pathfinder_v90/rail.nut:515`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/pathfinder_v90/rail.nut#L515) et [`ai/OpexAI/builder_rail.nut:2300-2345`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/builder_rail.nut#L2300-L2345).
- **Réglage :** Inhérent au pathfinder rail A*.
- **Défaut actuel et effet par niveau :**
  - Actif à tous les niveaux. OpexAI peut poser une voie ferrée qui coupe une route existante (route municipale ou route d'un autre joueur), créant un passage à niveau.
  - Conséquence pour un humain : Les passages à niveau ferment les barrières au passage des trains (bloquant les bus/camions) et peuvent écraser les véhicules routiers de l'humain en cas de collision, les détruisant définitivement.
- **Garde-fous existants :** Pénalité de coût dans l'A*, mais aucune interdiction stricte sur route rivale.
- **Proposition en mode `fair_play` :** **STRICTEMENT BORNÉ**.
  - *Justification :* En fair-play, interdire formellement la pose de rails à niveau sur toute route appartenant à une autre compagnie (`AIRoad.IsRoadTile(t) && AITile.GetOwner(t) != me`). Obligation d'utiliser un pont ou un tunnel.

#### 3.5 Barrières ferroviaires continues / Voies doubles coupant la carte
- **Fichier et lignes :** [`ai/OpexAI/builder_rail.nut:1500-1800`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/builder_rail.nut#L1500-L1800) et [`ai/OpexAI/settings.nut:105-107`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/settings.nut#L105-L107) (`v190_rail_double_build`, `v197_guided_double`, etc.).
- **Réglage :** `v190_rail_double_build` (défaut 0), `v197_guided_double` (défaut 0).
- **Défaut actuel :** 0 (voie unique par défaut).
- **Proposition en mode `fair_play` :** **INCHANGÉ AVEC JUSTIFICATION**.
  - *Justification :* « Ce n'est que de la concurrence économique normale » : poser des voies ferrées fait partie du jeu, tant que des ponts ou tunnels permettent de les franchir.

---

### Catégorie 4 : Actions de ville (`AITown.PerformTownAction`)

#### 4.1 Achat de droits de transport exclusifs (`TOWN_ACTION_BUY_RIGHTS` - V250)
- **Fichier et lignes :** [`ai/OpexAI/task_v250.nut:1-297`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/task_v250.nut#L1-L297), [`ai/OpexAI/task_v250.nut:49`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/task_v250.nut#L49) et [`ai/OpexAI/settings.nut:128-132`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/settings.nut#L128-L132).
- **Réglage :** `v250_rights` (0..4) et `opex_difficulty`.
- **Défaut actuel et effet par niveau :**
  - Défaut actuel : `v250_rights = 0` et `opex_difficulty = 2`.
  - Niveaux 0, 1, 2 : **STRICTEMENT COUPÉ** (`difficulty.nut:29` réserve V250 au niveau 3 ; `settings.nut:131` force `rights = 0`).
  - Niveau 3 (custom) : Si `v250_rights > 0`, OpexAI achète des droits exclusifs dans les villes (mode 1 : villes disputées ; mode 4 : monopoles rivaux et grandes métropoles).
  - Conséquence pour un humain : Pendant 1 an (12 mois économiques), AUCUNE autre compagnie ne peut charger de passagers ou de marchandises dans la ville. Les gares du joueur humain sont totalement paralysées, ses trains repartent à vide et ses notes s'effondrent.
- **Garde-fous existants :** Verrou de niveau 3, conditions de trésorerie nette et de caisse disponible.
- **Proposition en mode `fair_play` :** **STRICTEMENT INTERDIT** (`v250_rights` forcé à 0).
  - *Justification :* C'est l'action la plus hostile et anti-jeu d'OpenTTD. Elle doit être bannie de toute partie conviviale.

#### 4.2 Construction de statues de l'entreprise (`TOWN_ACTION_BUILD_STATUE` - V249)
- **Fichier et lignes :** [`ai/OpexAI/task_v249.nut:1-142`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/task_v249.nut#L1-L142) et [`ai/OpexAI/settings.nut:125`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/settings.nut#L125).
- **Réglage :** `v249_statue` (booléen, défaut 0 dans `info.nut:667`).
- **Défaut actuel et effet par niveau :**
  - Défaut actuel : 0 (inactif).
  - Non conditionné par `difficulty.nut`. Si activé (`v249_statue = 1`), OpexAI construit une statue par mois dès qu'elle est "riche" (emprunt remboursé et trésorerie couvrant réserve + plus grand projet).
  - Conséquence pour un humain : Une ville ne peut comporter qu'**UNE SEULE statue dans toute la partie** (`AITown.HasStatue`). Une fois la statue posée par OpexAI, le joueur humain ne pourra PLUS JAMAIS construire sa propre statue dans cette ville, et OpexAI bénéficie d'un bonus permanent de +26 points de réputation de gare dans cette ville.
- **Garde-fous existants :** Condition de richesse stricte, 1 statue max par mois, priorité aux villes où l'IA réalise du profit.
- **Proposition en mode `fair_play` :** **BORNÉ ou COUPÉ**.
  - *Option coupée :* `v249_statue` forcé à 0 en fair-play.
  - *Option bornée :* Autoriser la statue UNIQUEMENT dans les villes où OpexAI est l'unique compagnie présente (aucun rival n'y a de gare ni de rating), évitant de priver l'humain de la statue de son propre fief.

#### 4.3 Campagnes publicitaires (`TOWN_ACTION_ADVERTISING_SMALL / MEDIUM / LARGE`)
- **Fichier et lignes :** Aucun appel dans tout `ai/OpexAI/`.
- **Réglage :** Aucun.
- **Défaut actuel :** Non implémenté.
- **Proposition en mode `fair_play` :** **INCHANGÉ AVEC JUSTIFICATION**.
  - *Justification :* « Ce n'est que de la concurrence économique normale » : la publicité stimule temporairement la note de la compagnie sans bloquer les autres joueurs. Si implémenté un jour, ce comportement est fair-play.

#### 4.4 Corruption / Pots-de-vin (`TOWN_ACTION_BRIBE`)
- **Fichier et lignes :** Aucun appel dans tout `ai/OpexAI/`.
- **Réglage :** Aucun.
- **Défaut actuel :** Non implémenté.
- **Proposition en mode `fair_play` :** **MAINTENIR INTERDIT**.
  - *Justification :* Anti-jeu risquant une suspension municipale de 6 mois.

#### 4.5 Financement de réfection de voirie ou de bâtiments (`TOWN_ACTION_ROAD_REBUILD`, `TOWN_ACTION_FUND_BUILDINGS`)
- **Fichier et lignes :** Aucun appel dans tout `ai/OpexAI/`.
- **Réglage :** Aucun.
- **Défaut actuel :** Non implémenté.
- **Proposition en mode `fair_play` :** **MAINTENIR INTERDIT pour les routes**.
  - *Justification :* Financer la réfection des routes (`TOWN_ACTION_ROAD_REBUILD`) paralyse la circulation routière pendant 6 mois dans la ville, ce qui bloquerait violemment les véhicules du joueur humain. Financer des bâtiments (`TOWN_ACTION_FUND_BUILDINGS`) serait en revanche inoffensif (stimule la croissance).

---

### Catégorie 5 : Panneaux (`AISign`)

#### 5.1 Panneaux de budget et catégories (BT et BC)
- **Fichier et lignes :** [`ai/OpexAI/task_report.nut:908-927`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/task_report.nut#L908-L927).
- **Réglage :** Normalement associé à `debug_signs`, mais **NON PROTÉGÉ** !
- **Défaut actuel et effet par niveau :**
  - **ANOMALIE DU CODE ACTUEL :** Ces lignes appellent directement `AISign.BuildSign` et `AISign.SetName` sur les tuiles `(20, 1)`, `(20, 2)`, etc., **SANS VÉRIFIER `DEBUG_SIGNS`** !
  - Elles s'exécutent donc même si `debug_signs = 0` !
- **Garde-fous existants :** Aucun dans le bloc 908-927.
- **Proposition en mode `fair_play` :** **STRICTEMENT COUPÉ**.
  - *Justification :* En fair-play, ajouter impérativement la garde `if (!DEBUG_SIGNS) return;` ou `if (FAIR_PLAY) return;`.

#### 5.2 Panneaux généraux de diagnostic et métriques (`OpexSign`)
- **Fichier et lignes :** [`ai/OpexAI/probes.nut:36-41`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/probes.nut#L36-L41) (`OpexSign`), présent sur des dizaines de sites (rapports, lignes, gares, aéroports, ports, ordonnanceur).
- **Réglage :** `probes` (défaut 2 = bit 2 panneaux) et `debug_signs` (défaut 1).
- **Défaut actuel et effet par niveau :**
  - Par défaut, `probes & 2 != 0 && debug_signs != 0` est **VRAI**.
  - OpexAI pose en permanence des dizaines de panneaux sur la carte (`OW|...`, `TV|...`, `IG|...`, `C7C|...`, `AP|...`, `AC|...`).
  - Conséquence pour un humain : La carte est couverte de panneaux cryptiques qui encombrent l'écran et perturbent la vue.
- **Garde-fous existants :** `if (!DEBUG_SIGNS) return;`.
- **Proposition en mode `fair_play` :** **STRICTEMENT COUPÉ**.
  - *Justification :* En mode fair-play, forcer l'extinction complète de tous les panneaux (`DEBUG_SIGNS = false`). Aucun panneau d'IA ne doit apparaître sur la carte du joueur.

---

### Catégorie 6 : Rachat et fusion de compagnies (`AICompany.BuyCompanyShare`, `BuyCompany`)
- **Fichier et lignes :** Recherche exhaustive sur tout le dossier `ai/OpexAI/` : **ZÉRO appel** à `BuyCompanyShare` ni `BuyCompany`.
- **Réglage :** Aucun.
- **Défaut actuel :** Non implémenté. OpexAI ne possède aucune logique de participation capitalistique, d'OPA ou de rachat d'autres entreprises.
- **Proposition en mode `fair_play` :** **INCHANGÉ AVEC JUSTIFICATION**.
  - *Justification :* L'IA ne menaçant pas le capital des autres joueurs, aucune bride supplémentaire n'est nécessaire.

---

### Catégorie 7 : Gestion des emprunts (`AICompany.SetLoanAmount`)
- **Fichier et lignes :**
  - Emprunt initial : [`ai/OpexAI/main.nut:751`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/main.nut#L751) (`AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount())`).
  - Remboursement : [`ai/OpexAI/capital.nut:44-81`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/capital.nut#L44-L81) (`_tryRepayLoan`).
- **Réglage :** `loan_repay_floor` (défaut 20 000 £ dans [`ai/OpexAI/settings.nut:157`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/settings.nut#L157)).
- **Défaut actuel et effet par niveau :**
  - Au démarrage (janvier 1970), OpexAI emprunte immédiatement le montant maximal permis par le jeu (typiquement 300 000 £). Elle rembourse ensuite au fil des années lorsque sa caisse dépasse le plancher.
  - La proposition d'agy de brider l'emprunt aux niveaux 0 et 1 a été expressément écartée par l'utilisateur le 18/10 (`docs/taches.md:197`).
- **Garde-fous existants :** Remboursement annuel automatique.
- **Proposition en mode `fair_play` :** **INCHANGÉ AVEC JUSTIFICATION**.
  - *Justification :* « Ce n'est que de la concurrence économique normale » : dans OpenTTD, la capacité d'emprunt est strictement individuelle et indépendante par joueur. Qu'OpexAI utilise son crédit n'ampute en rien celui du joueur humain. Cela fait partie intégrante de la saine gestion d'une entreprise de transport.

---

### Catégorie 8 : Autres interactions NoAI (`AICompany`, `AITile`, `AIIndustry`)

#### 8.1 Observation des concurrents (V211)
- **Fichier et lignes :** [`ai/OpexAI/rivals_v211.nut:1-105`](file:///home/deploy/projects/wt-fairplay/ai/OpexAI/rivals_v211.nut#L1-L105).
- **Réglage :** `v211_rivals_log` (défaut 0).
- **Défaut actuel :** Relevé passif trimestriel des valeurs, profits et nombres de véhicules des rivaux sous `DECISION_LOG`.
- **Proposition en mode `fair_play` :** **INCHANGÉ AVEC JUSTIFICATION**.
  - *Justification :* Pure lecture d'informations publiques du jeu, aucun impact sur le monde.

#### 8.2 Création et prospection d'industries (`AIIndustry.BuildIndustry`)
- **Fichier et lignes :** Aucun appel dans le code courant (tâche V251 en conception).
- **Proposition en mode `fair_play` :** Si la création d'industries est implémentée dans le futur, elle devra veiller à ne pas implanter d'industrie directement sur des réserves foncières ou corridors réservés par un autre joueur.

---

## 3. Synthèse récapitulative des comportements audités

| # | Comportement audité | Emplacement code | Contrôle / Réglage | État au défaut N2 | Recommandation Fair Play |
|---|---|---|---|---|---|
| **1.1** | Gares rail en captage partagé | `builder_rail.nut:337` | `encroach_rival_catchment` | Autorisé | **Coupé** (pas de captage partagé) |
| **1.2** | Arrêts route en captage partagé | `builder_road.nut:162` | `encroach_rival_catchment` | Autorisé | **Coupé** (pas de captage partagé) |
| **1.3** | Docks maritimes en captage partagé | `builder_water.nut:150` | Aucun (hors mode) | Autorisé | **Coupé** (soumis à `OpexStationEncroachesRival`) |
| **1.4** | Arrêts bus joints fantômes aux aéroports | `air_construction.nut:55` | Constante `LIMIT=2` | **ACTIF** | **Strictement coupé** (`LIMIT=0`) |
| **1.5** | Arrêts bus joints aux gares rail | `task_rail.nut:1149` | `v207_rail_pax_joined_stops` | Coupé (0) | **Maintenir coupé** (0) |
| **1.6** | Aéroport dans une ville rivale | `air_towns.nut:625` | `airport_rival_town` | Autorisé | **Borné** (autorisé seulement si ≥2 créneaux libres) |
| **2.1** | Préemption dernier créneau aéroport | `air_towns.nut:650` | `preempt_last_airport_slot` | **Autorisé** | **Strictement coupé** (ne jamais prendre le dernier créneau) |
| **2.2** | Early slot rush (bonus +50 % 6 villes) | `projects_selection.nut:349` | Constante interne | Actif | **Inchangé** (concurrence normale) ou bonus à 0 |
| **2.3** | Double aéroport propre dans une ville | `projects_selection.nut:416` | Logique C83 | Autorisé | **Strictement coupé** (max 1 aéroport par ville) |
| **2.4** | Gares sur industries primaires rivales | `spatial.nut:91` | `compete_primary_industry` | **Autorisé** | **Strictement coupé** (respect du premier arrivé) |
| **2.5** | Desserte industries secondaires (V233) | `goods_v233.nut:1` | `v233_goods_graft` | Coupé (0) | **Inchangé** (concurrence économique normale) |
| **3.1** | Démolition maisons / voirie (V199) | `builder_rail.nut:2037` | `v199_robust_build` | Coupé (0) | **Strictement coupé** (forcé à 0) |
| **3.2** | Terraformage / nivellement d'emprise | `air_sites.nut:143` | Hardcodé / `v199_level` | Actif | **Borné** (interdit si adjacent à infra rivale) |
| **3.3** | Tree spamming réactif aux refus | `candidates.nut:1802` | Aucun (inconditionnel) | **ACTIF** | **Strictement coupé** (respect des refus municipaux) |
| **3.4** | Passages à niveau sur routes rivales | `pathfinder_v90/rail.nut:515` | Pathfinder A* | Possible | **Strictement borné** (pont/tunnel obligatoire) |
| **3.5** | Voies doubles / barrières continues | `builder_rail.nut:1500` | `v190_rail_double_build` | Coupé (0) | **Inchangé** (concurrence économique normale) |
| **4.1** | Droits exclusifs V250 (`BUY_RIGHTS`) | `task_v250.nut:49` | `v250_rights` + niveau | Coupé (0) | **Strictement interdit** (forcé à 0) |
| **4.2** | Statues de ville V249 (`BUILD_STATUE`) | `task_v249.nut:134` | `v249_statue` | Coupé (0) | **Coupé ou borné** (villes à monopole propre) |
| **4.3** | Campagnes publicitaires | Non présent | — | Inexistant | **Inchangé** (concurrence économique normale) |
| **4.4** | Pots-de-vin (`BRIBE`) | Non présent | — | Inexistant | **Maintenir interdit** |
| **4.5** | Réfection routes / bâtiments | Non présent | — | Inexistant | **Maintenir interdit pour les routes** |
| **5.1** | Panneaux budget BT / BC | `task_report.nut:908` | `debug_signs` (non gardé) | **ACTIF** | **Strictement coupé** (aucun panneau) |
| **5.2** | Panneaux diagnostic `OpexSign` | `probes.nut:36` | `probes=2`, `debug_signs=1` | **ACTIF** | **Strictement coupé** (aucun panneau) |
| **6.1** | Rachat / actions de compagnies | Non présent | — | Inexistant | **Inchangé** (inexistant dans l'API OpexAI) |
| **7.1** | Emprunt initial au plafond | `main.nut:751` | Hardcodé | Actif | **Inchangé** (concurrence économique normale) |

---

## 4. Proposition de spécification du réglage `fair_play`

Pour répondre fidèlement à la demande utilisateur et préparer l'implémentation future (étape suivante), nous soumettons la spécification suivante.

### 4.1 Déclaration du réglage
- **Nom du paramètre :** `fair_play` (ou `opex_fair_play`)
- **Fichier de déclaration :** `ai/OpexAI/info.nut`
- **Fichier de chargement :** `ai/OpexAI/settings.nut`
- **Type :** Entier (0 ou 1, ou extension par paliers 0..2)
  - `easy_value = 1`
  - `medium_value = 1`
  - `hard_value = 0` (afin que les bancs de performance contre AAAHogEx continuent à tourner à leur profil compétitif maximal historique)
  - `custom_value = 0`

### 4.2 Définition des valeurs
- **Valeur `0` : Compétitif / Bancs (Défaut pour les bancs et le niveau Difficile)**
  - Comportement actuel préservé au bit près.
  - Tous les leviers concurrentiels de niveau 2 (captage, dernier créneau, industries primaires, arrêts joints d'aéroport, panneaux, etc.) restent actifs.
- **Valeur `1` : Fair-play standard (Recommandé pour jeu normal avec des humains)**
  - **Désactivation totale des panneaux :** `DEBUG_SIGNS = false`, et ajout d'un garde sur les panneaux BT/BC.
  - **Suppression des arrêts de bus fantômes d'aéroports :** `AIR_JOINED_STOP_LIMIT = 0`.
  - **Suppression du tree-spamming réactif :** En cas d'échec `ERR_LOCAL_AUTHORITY_REFUSES`, l'IA ne plante aucun arbre et abandonne le chantier.
  - **Protection des créneaux d'aéroports :** Interdiction de prendre le dernier créneau d'une ville rivale (`preempt_last_airport_slot` forcé à faux) ; interdiction du double aéroport propre dans la même ville.
  - **Protection des industries primaires :** Interdiction d'exploiter une mine/forêt/ferme déjà raccordée par un tiers (`compete_primary_industry` forcé à faux).
  - **Protection contre le captage hostile :** `encroach_rival_catchment` forcé à faux pour le rail, la route et l'eau.
  - **Interdiction absolue des droits exclusifs :** `v250_rights = 0`.
  - **Interdiction des passages à niveau sur routes rivales :** obligation de pont/tunnel.

### 4.3 Questions ouvertes soumises à l'arbitrage de l'utilisateur
1. **Périmètre du profil par défaut :** Souhaitez-vous que le réglage `fair_play` soit activé par défaut sur les difficultés Facile et Moyen (`easy_value = 1`, `medium_value = 1`) tout en restant à 0 sur Difficile/Personnalisé pour préserver les bancs C66 ?
2. **Statues V249 :** Préférez-vous interdire totalement les statues en fair-play (`v249_statue = 0`), ou autoriser l'IA à en poser uniquement dans les villes où elle est la seule compagnie établie ?
3. **Implantation en ville rivale :** En mode fair-play, préférez-vous interdire totalement à OpexAI de construire un aéroport dans une ville où un joueur est déjà présent, ou autoriser l'implantation tant qu'il reste au moins 2 créneaux de bruit libres ?

## 5. Comportements remontés par la communauté (tt-forums, 18/10)

### 5.1 Périmètre et méthode V261

Complément du 18/10, branche `v261` (fusion fairplay + master). L'extrait fourni
`/home/deploy/.claude/jobs/e230de46/tmp/forum_extract_v261.md` est une **liste
d'allégations à examiner**, pas une transcription authentifiée : le
[fil indiqué](https://www.tt-forums.net/viewtopic.php?t=90674) reste bloqué par
Anubis. Aucun propos ni chiffre ci-dessous n'est attribué à un auteur du forum.
Les preuves `ai/OpexAI/fichier:ligne` désignent l'arbre V261 ; les références
`script/...` désignent le source en lecture seule sous
`/home/deploy/.claude/jobs/e230de46/tmp/ottd15/src/src/`.

« Conforme » qualifie le contrat statique précisé, pas toutes les trajectoires
possibles. « Non conforme » désigne une garde de courtoisie absente, sans jugement
sur sa légalité dans le jeu. « Partiel » signifie qu'une protection existe mais
ne couvre pas toute l'allégation. Les contrôles dynamiques restent **non exécutés**.
Tests : `sweeps/test_v261_forum_behaviours.py`, préfixes `test_1_…` à `test_4_…`
correspondant aux identifiants F ci-dessous. L'audit initial ne modifiait pas
l'IA ; la suite V261b applique les décisions utilisateur du 18/10 ci-dessous.
Aucun réglage public ajouté, aucune famille protégée ni harnais modifié.

`fair_play` reste une proposition, sans réglage implémenté. La table effective
est `ai/OpexAI/difficulty.nut:26` : droits exclusifs/anticompetitive au niveau 3,
dernier créneau et concurrence primaire dès 2, ville rivale et chevauchement dès 1.
**Décisions utilisateur V261b, 18/10 :** les trois nouvelles clés passent par
`OpexLevelAllows`, sans ajouter le réglage `fair_play` proposé aux §2–4.
Ces propositions historiques ne constituent pas la spécification adoptée.

| Capacité (`difficulty.nut`) | 0 facile | 1 moyen | 2 difficile (défaut) | 3 personnalisé (« niveau 4 ») |
|---|---|---|---|---|
| `air_joined_road_stops` | Interdit | Interdit | Autorisé | Autorisé |
| `water_depot_dock_front` | Interdit | Interdit | Interdit | Autorisé |
| `secondary_graft_rival_served` | Interdit | Interdit | Interdit | Autorisé |

Les panneaux restent actifs au défaut des bancs : `probes=2` et `debug_signs=1`
inchangés. Tous les appels directs de pose sont désormais sous `DEBUG_SIGNS`
(BT/BC compris). `probes=0` ou `debug_signs=0` empêche toute nouvelle pose ;
cela ne supprime pas les panneaux déjà présents dans une partie rechargée.
F2.1a (`forbid_90_deg`) reste ignoré sur décision utilisateur ; F2.1c
(types de véhicules désactivés) attend une explication, sans modification.

### 5.2 (a) Interactions avec les autres joueurs

| Point de l'extrait | État OpexAI et preuve fichier:ligne | Mesure / contrat machine |
|---|---|---|
| **F1.1 — Spam d'arrêts municipaux traversants** | **Partiel**, garde AIR corrigée V261b. `ai/OpexAI/builder_road.nut:679` conserve l'espacement propre. `ai/OpexAI/air_construction.nut:58` refuse les arrêts joints avant recherche/pose si `air_joined_road_stops` est interdit (0–1), les autorise à 2–3. | Tests espacement et garde AIR verts, sans expectedFailure. Congestion et desserte effective restent non mesurées ; présence d'un traversant seule ≠ blocage. |
| **F1.2 — Colonisation maritime / côtes bloquées** | **Partiel**. `ai/OpexAI/builder_water.nut:1` ne construit ni canal, écluse, bouée, ni terraformage ; sondes et BFS bornés. `:134` choisit les quais sans `OpexStationEncroachesRival`. Le nombre global d'installations et l'accès des tiers ne sont pas garantis par ces bornes par recherche. | Étendre la garde de captage aux quais et préserver les passages navigables en fair_play, à tous niveaux ; pas d'interdiction générale du transport maritime. Test absence de constructions agressives vert. Futur contrôle topologique et journaux d'échec d'accès par compagnie. L'issue #10490 ne prouve pas une colonisation intentionnelle (voir §5.4). |
| **F1.3 — Dépôt sur l'accès immédiat du quai** | **Garde A/B corrigée V261b**. `ai/OpexAI/builder_water.nut:239` exclut `siteA.waterTiles` et `siteB.waterTiles` des deux tuiles candidates du dépôt aux niveaux 0–2 (`water_depot_dock_front` réservé à 3). Les fronts restent traversables par le BFS pour chercher ailleurs ; aucun dépôt existant n'est démoli. | Test vert : deux fronts, deux cases du dépôt, poursuite du BFS et retour null si aucun candidat. La protection porte sur les deux quais de la liaison ; pas d'inventaire supplémentaire de tous les quais tiers. Aucun test moteur de Full Load, de pose alternative ou de topologie dynamique effectué. |
| **F1.4 — Étouffement urbain par plusieurs aéroports** | **Partiel**. `ai/OpexAI/air_towns.nut:623` consulte les deux capacités de niveau, avec exceptions ; `projects_selection.nut:416`, `:434`, `:461` autorise le second aéroport propre C83. Pas de preuve d'une politique systématique « 2 à 3 par ville ». | Fair_play : empêcher la capture des deux sites propres et la prise du dernier créneau rival ; conserver les niveaux existants hors fair_play. Test des capacités vert, sans prétendre tester un plafond fair_play inexistant. Vérifier futurs comptes d'aéroports/bruit et refus des tiers. |
| **F1.5 — Droits exclusifs** | **Conforme** au niveau 2 par défaut : `ai/OpexAI/task_v250.nut:287` refuse si `OpexLevelAllows("v250_rights")` faux ; `difficulty.nut:29` réserve à 3. | Maintenir le veto absolu fair_play même au niveau 3 ; test vert de la garde existante. L'exemple LudAIAfterFix n'a pas été vérifié et n'est pas une preuve sur OpexAI. |
| **F1.6 — Captation de production secondaire financée par un tiers** | **Garde corrigée V261b si V233 activé** (défaut V233 inchangé). `ai/OpexAI/goods_v233.nut:181` détecte une desserte rivale de la secondaire ; `OpexV233JoinContextValid` applique le veto à 0–2, court-circuité à 3 par `secondary_graft_rival_served`. La même validation est appelée à l'éligibilité puis juste avant dépense. | Test vert des API, propriétaires, veto et revalidation. Définition opérationnelle : une tuile de gare rail, arrêt routier (route/tram) ou quai appartenant à une autre compagnie valide est dans `AITileList_IndustryAccepting(factory, rayon API du type)`. Arrêts bus inclus par précaution (rayon max bus/camion). Cela prouve une couverture d'acceptation, pas un intrant livré : gare inactive ou collectrice et bus peuvent être des faux positifs. Aucun historique de livraison par compagnie n'est utilisé. Aéroports seuls et desserte amont sans gare près de la secondaire ne sont pas détectés. Aucun cache ni état sauvegardé ajouté ; les observations et plans V233 existants sont revalidés par le chemin commun. |
| **F1.7 — Destruction massive de maisons / arbres** | **Partiel**. `ai/OpexAI/builder_rail.nut:2037` protège rail tiers et stations/dépôts rail, pas tous les bâtiments municipaux ; V199 reste optionnel (`info.nut:551`). `air_sites.nut:143` nivelle les emprises AIR. Ni destruction « massive » ni note sous Poor ne se déduisent du source. | Fair_play : revoir démolition municipale et terraformage au voisinage tiers ; aucun changement de la famille protégée V199. Test protection rail vert. Mesurer à l'avenir les commandes réellement exécutées et notes avant/après par compagnie. Une chute de notre note ne prouve pas celle de tous les joueurs ; corrige la formulation du §3.1. Le moteur contrôle la légalité du terrain, le §3.2 ne prouve pas une destruction de voie tierce par nivellement. |
| **F1.8 — Infrastructures fantômes après échec / abandon recommandé** | **Partiel**. `ai/OpexAI/builder_road.nut:549`, `builder_rail.nut:2556`, `builder_water.nut:489` ont des rollbacks. `air_recovery.nut:34` attend vente réelle des avions, protège les aéroports réutilisés/occupés et conserve des tickets persistés (`persist.nut:630`). | Ne pas appliquer l'abandon systématique de l'extrait : conserver nettoyage des actifs neufs sûrs, tickets de reprise et mémoire des échecs. Fair_play doit traiter les obstacles orphelins aux tiers sans démolir un service actif. Tests présence des rollbacks verts ; journaux AIR_ROLLBACK et inventaire des actifs après chaque échec à contrôler. « ~25 000 £ » n'est ni un prix garanti ni un seuil retenu. |
| **F1.9 — Pollution du journal / verbosité** | **Panneaux corrigés V261b**. `ai/OpexAI/settings.nut:70` combine le bit panneaux de probes et debug_signs. `ai/OpexAI/probes.nut:38` garde OpexSign ; `ai/OpexAI/task_report.nut:909` garde pose et renommage BT/BC. Défauts conservés pour les bancs. Journal ordinaire inchangé, aucun log_level ajouté. | Test BT/BC vert et inventaire exhaustif des appels directs `AISign.BuildSign` gardés. Aucune nouvelle pose avec probes=0 ou debug_signs=0 ; les panneaux préexistants ne sont pas effacés. Pas de preuve d'un rythme « toutes les trois secondes » ; débit des messages et comportement en jeu non mesurés. |
| **F1.10 — Délaissement du fret** | **Sans objet** comme comportement déloyal : choisir les voyageurs n'agresse pas en soi un tiers. Fret présent dans `ai/OpexAI/candidates.nut:1060`, `:1200`, `:1528`. Aucune garantie de diversité sur chaque carte. | Tests génération fret verts ; si objectif de variété, le traiter dans les profils de stratégie, sans règle punitive fair_play. Futur journal de portefeuille : candidats/rejets/constructions par cargo, réglages et disponibilité du matériel. |

### 5.3 (b) Robustesse, CPU et RAM — pas des règles de fair-play

Les points F2–F4 s'appliquent à tous les niveaux de difficulté. Ils ne justifient
ni bridage économique ni ajout de Sleep arbitraire ; une correction éventuelle
reste une autre tâche, après décision utilisateur.

| Point (y compris les sous-puces de l'extrait) | État OpexAI et preuve fichier:ligne | Mesure / contrat machine |
|---|---|---|
| **F2.1a — forbid_90_deg** | **Partiel**. `ai/OpexAI/builder_rail.nut:1242` compte la géométrie serrée ; `pathfinder_v90/rail.nut:23` implémente le pathfinder, mais aucune lecture de `vehicle.forbid_90_deg` dans l'arbre. Cela ne démontre pas une boucle infinie : un tracé peut être légal par construction. | Test d'absence de garde explicite **expectedFailure**, sans affirmer qu'une lecture serait la seule solution correcte. Futur contrôle géométrique des tracés, aiguillages et itinéraires réellement parcourus sous interdiction activée, journal LOST/erreurs et horizon complet. |
| **F2.1b — max_trains=0** | **Conforme** au contrat local : `ai/OpexAI/builder_rail.nut:3282` compare effectif et plafond, `:3411`, `:3966` revérifie à la transaction, `task_rail.nut:254` avant recherche. | Test vert des gardes, conserver aussi la revérification après suspension. |
| **F2.1c — Véhicules désactivés, tous modes** | **Partiel**. `ai/OpexAI/settings.nut:84` charge nos mode_* ; ce ne sont pas les options du jeu. Aucun appel `AIGameSettings.IsDisabledVehicleType`. `tension.nut:68` nomme les quatre plafonds mais sonde ≠ garde, `ledgers.nut:1048` ne fait que compter un rejet hypothétique. | Test consultation de désactivation **expectedFailure**. Vérifier futurs journaux par type désactivé : pas d'infrastructure engagée inutilement, ni boucle de tentatives. Les préconditions moteur limitent les constructions mais ne prouvent pas l'adaptation de l'IA. |
| **F2.2a — IDs cargo/rail/route numériques, NewGRF** | **Conforme** aux motifs numériques inspectés : `ai/OpexAI/catalog.nut:834` énumère les cargos/classes, `:403` les railtypes. `:766` utilise l'enum API ROADTYPE_ROAD, pas le littéral 0. **Partiel** pour le support de tous les NewGRF : pas de sélection générale AIRoadTypeList. | Test recherche de littéraux dans affectations et appels cargo/types vert, sentinelles -1 admises ; ce n'est pas une analyse de flux/alias exhaustive. Ne pas confondre enum API et ID cargo arbitraire. Tester à l'avenir disponibilité/refit et choix des types avec sets réels. |
| **F2.2b — Compatibilité des routes municipales tuile par tuile** | **Partiel**. `ai/OpexAI/builder_road.nut:397` vérifie chaque arête BFS et `IsRoadTile(nxt)` ; `:689` fixe le type courant, `:827` contrôle le moteur. `script/api/script_road.cpp:107` : AreRoadTilesConnected lit les roadbits route/tram, pas à lui seul la compatibilité de chaque RoadType ; `IsRoadTile` (`:45`) filtre le type présent. | Test vert du chemin protégé, sans prétendre couvrir tous les chemins L/réutilisations. Auditer ces autres chemins et tester futurs journaux NewGRF, type sur chaque tuile et trajet réel. Pas de remplacement par un simple test de connectivité. |
| **F2.3 — Remaniement de voies sous trafic / deadlocks** | **Non vérifiable statiquement** quant à l'absence de blocage. `ai/OpexAI/builder_rail.nut:3771` préserve et vérifie la voie primaire après rollback (`:3860`), ce qui ne prouve pas la vivacité du trafic. | Test de contrat rollback/intégrité vert. Contrôle futur : positions/vitesses, signaux orientés, ordres, événements LOST, durée sans progression avant/après extension et après Load ; un train au Full Load n'est pas automatiquement un deadlock. |
| **F2.4a — Longueur train/quai** | **Conforme** au contrat de construction inspecté : `ai/OpexAI/builder_rail.nut:2632` limite en 1/16 de tuile ; `:2681`, `:2687`, `:2693` mesure les véhicules réels et refuse le débordement avant attelage. | Test vert ; futur contrôle longueur réelle et longueur des deux quais, y compris refleet/extension et matériels NewGRF. |
| **F2.4b — Traction / relief** | **Partiel**. `ai/OpexAI/catalog.nut:468` lit effort de traction, `:136` calcule vitesse effective ; `economy.nut:247` l'emploie. Ce n'est pas une preuve de vitesse minimale sur les côtes de chaque tracé. | Test présence du modèle vert ; contrôler profils de pente et vitesses réelles à charge dans les futurs relevés. Ni vitesse « 15 km/h » ni pénalité « massive » quantifiée ici. |
| **F3.1 — Exécution coopérative, gestion bloquée pendant des mois** | **Partiel**. `ai/OpexAI/main.nut:828` cède la main ; `builder_rail.nut:646` limite chaque tranche par itérations, slice et deadline ; `scheduler.nut:442` réemploie le budget restant. Une boucle peut traverser des ticks et retarder d'autres tâches même si le moteur suspend automatiquement la VM. | Test garde de tranche + Sleep vert ; futur journal TASK/LOOP, dates des événements/remboursements et durée par tâche. Pas de garantie 60 IPS ni d'affirmation globale « tout OpenTTD mono-threadé » déduite de ces fichiers. |
| **F3.2 — Valuate Squirrel / excessive CPU usage** | **Conforme** à l'évitement des callbacks Squirrel : tous les appels recensés §5.5 passent des méthodes natives API. `script/api/script_list.cpp:842` accepte pourtant les closures Squirrel **et** natives ; `:852` limite l'opération. | Test inventaire exhaustif des premiers arguments vert, vérifié contre TSV API. Liste blanche de petites closures **vide** car aucun besoin actuel. Une future exception nécessiterait taille bornée et coût prouvé ; « exclusivement C++ » n'est pas une règle de validité API. L'affirmation « première cause de crash » n'est pas étayée. |
| **F3.3a — GetOpsTillSuspend, GetOpsLimit/GetOps** | **Conforme**. `ai/OpexAI/budget.nut:21`, `scheduler.nut:442` emploient la primitive réelle. `docs/noai_api_15.3.tsv:722` et `script/api/script_controller.hpp:121` exposent GetOpsTillSuspend, pas les deux autres. | Test absence des faux appels + présence primitive réelle vert. Aucun budget ne se cumule par simple attente. |
| **F3.3b — Sleep versus Break** | **Conforme** à l'absence de Break (scan récursif `.nut`), Sleep présent `ai/OpexAI/main.nut:828`. `script/api/script_controller.cpp:34`, `:48` distingue suspension et débogage. | Test vert. Break ne remplace pas Sleep ; nuance de l'extrait au §5.4. |
| **F3.3c — Tick budgeting / seuils 2 500–3 000 / 10 000** | **Partiel**. `ai/OpexAI/task_terrain.nut:100` refuse de travailler sous C67_SLACK_MIN ; `terrain_map.nut:252` a budget/deadline et `:256` garde 3 000. Rail utilise surtout slices et deadlines. | Test gardes existantes vert. Aucun seuil nouveau : profilage par tâche et mesure des IPS côté client nécessaires ; les seuils de l'extrait ne garantissent pas 60 IPS. Ne pas ajouter Sleep dans chaque boucle. |
| **F3.4a — Débit VM mensuel ~10^6 / demande rail ~3·10^7** | **Non vérifiable statiquement** comme mesure actuelle. `ai/OpexAI/tension.nut:39` mesure le débit selon dates/ticks ; `builder_rail.nut:646` exécute les tranches. | Contrôler futurs spans/opcodes et dates comparables, sans convertir une estimation en consommation mesurée. Pas de test d'un chiffre non qualifié. |
| **F3.4b — A* 50–150 ops / cap 100 000 / 204–206 tuiles** | **Partiel** pour la protection ; chiffres **non validés**. `ai/OpexAI/globals_pre.nut:586` fixe le cap courant à **5 000**, `builder_rail.nut:104` l'applique ; `candidates.nut:109` garde une table empirique historique, pas un plafond moteur universel. | Test du plafond courant et de sa consultation vert. Retirer l'inférence distance maximale universelle ; mesurer recherche réelle, succès/ABND/DEAD et coût par protocole avant tout changement. |
| **F3.4c — Lecture exhaustive de carte / coût 20–30 ops** | **Partiel**. `ai/OpexAI/terrain_map.nut:252` travaille par étapes, budget/deadline ; cache borné (`:74`). Ne prouve pas le coût 20–30 ni l'absence de tout autre scan. | Test structure bornée/reprenable vert ; futurs spans de lecture et nombre de tuiles effectivement lues. Aucun nouveau consommateur C67 ni modification de sa famille protégée. |
| **F3.4d — Explosion O(n²), 731 villes / 266 815 paires / 16,74 M** | **Conforme** à l'indexation sur le chemin voyageurs inspecté : `ai/OpexAI/candidates.nut:995` construit OpexSpatialGrid, `:999` demande les voisins. Le pire cas dense peut rester quadratique. | Test indexation vert ; mesurer candidats visités/coût par génération, sans promettre une complexité linéaire. Les chiffres sont historiques internes (§5.4). |
| **F3.4e — AITestMode/ROI avant filtres rapides** | **Partiel**. `ai/OpexAI/builder_water.nut:153` filtre la distance avant `:160` AITestMode. Ce cas ne prouve pas l'ordre optimal de tous les constructeurs ; AITestMode et AIAccounting imbriqués peuvent être nécessaires. | Test ordre local vert ; futur profil spans devis/filtres, taux de rejet et coûts. Pas de suppression automatique des simulations. |
| **F4.1 — RAM « normale 5–10 Mo », « critique >50 Mo »** | **Non vérifiable statiquement**. `ai/OpexAI/terrain_map.nut:74` borne un cache, `persist.nut:602` construit le graphe sauvé ; aucune mesure mémoire VM globale n'en découle. | Pas de seuil RAM inventé. Test capacité du cache couvre seulement un invariant structurel. Sur futurs relevés mémoire distinguer VM/compagnie, processus moteur et RSS du worker ; corréler croissance à taille de carte/flotte et temps de GC. |
| **F4.2 — Table par tuile 40–60 Mo / macro-blocs / null** | **Partiel**. `ai/OpexAI/terrain_map.nut:106` indexe des blocs, `:233` borne le cache, `:90` Clear, `:318` Cancel ; `:265` libère un accumulateur. Les tailles en Mo et l'obligation de blocs 32×32 ne sont pas établies. | Test bornes/Clear/libération vert ; suivre mémoire avant/après fin et annulation de chantier. Les objets encore référencés ne sont pas libérés par un simple null ailleurs. Ne pas changer C67 sur cette base. |
| **F4.3 — Valuate suivi de for = allocation redondante** | **Sans objet** comme interdiction générale. `ai/OpexAI/capital.nut:8`, `:10` et `tension.nut:84`, `:86` consomment les valeurs natives via GetValue sans rappeler GetRunningCost. `script/api/script_list.cpp:905` affecte une valeur à chaque entrée. | Test non-recalcul vert. Un parcours après Valuate est souvent précisément l'utilisation prévue de la liste ; profiler une redondance réelle avant refonte. L'allocation d'une seconde table n'est pas démontrée par ce seul motif. |
| **F4.4a — Trop de données Save / assertion #12133** | **Non vérifiable statiquement** quant au crash. `ai/OpexAI/persist.nut:602` a un format court ; `:585` prépare la projection mensuelle des lignes pour limiter le travail dans Save. L'issue citée décrit une ancienne assertion, pas un plafond d'octets V261. | Test structure/projection vert. Futur contrôle Save/Load : erreurs serializer, durée/opcodes Save, volume, urgence et horizon après recharge sur grosse flotte. Aucun lancement ici. |
| **F4.4b — Objets/coroutines et « dictionnaire plat » Save/Load** | **Partiel**. `ai/OpexAI/persist.nut:557` filtre les champs directs des lignes (convertit floats, écarte autres types), Save renvoie shortSave/saveObj tables (`:635`, `:717`). La copie est superficielle : les types des éléments imbriqués et des tables mutables ne sont pas prouvables par cette inspection. | Test projection/type direct et exclusion de l'objet pathfinder vert. **Pas une preuve de typage récursif** : vérifier en VM le graphe effectivement retourné et les deux modes Save/Load, y compris fonctions/générateurs/instances imbriqués, cycles, profondeur et chaînes. Aucun expectedFailure inventé en l'absence d'objet invalide réellement identifié. L'API accepte des structures imbriquées et certaines instances (§5.4), pas seulement un dictionnaire plat. |

### 5.4 Vérification des affirmations et provenance

- **API opcodes : confirmé.** GetOpsTillSuspend existe ; GetOpsLimit et GetOps
  n'existent pas dans l'API NoAI 15.3 inventoriée. `GetTick` mesure des ticks,
  pas le reliquat d'opcodes.
- **Break : formulation incomplète.** `script/api/script_controller.cpp:50`
  retourne sans effet en serveur dédié ou sans outils développeur. Sinon il
  suspend l'instance et demande une pause du jeu ; ce n'est jamais une primitive
  de coopération. Sleep (`:36`) est interdit dans constructeur, Save, Load et
  valuators. La VM peut aussi être suspendue automatiquement sur quota et les
  commandes de jeu peuvent suspendre le script : « seule primitive » ne doit pas
  être interprété comme « seul mécanisme qui rend la main ».
- **Valuate : risque réel, explication trop absolue.**
  `script/api/script_list.hpp:17` fixe MAX_VALUATE_OPS à **1 000 000** ;
  `script_list.cpp:852` pose SQOpsLimiter sur **l'opération entière**, pas une
  limite exprimée en nombre d'éléments. Les callbacks Squirrel sont acceptés
  (`:842`) ; une petite closure bornée n'est pas illégale. La chaîne exacte
  « excessive CPU usage in valuator function » n'a **pas été retrouvée** dans le
  source fourni (la définition de SQOpsLimiter n'y est pas présente). Ne pas
  prétendre avoir établi le message fatal exact ni un classement des crashes.
- **Sérialisation : deux affirmations fausses pour 15.3.**
  `script/script_instance.cpp:370` sérialise récursivement tables et tableaux,
  avec profondeur maximale **25** ; `:480` accepte des instances ScriptObject
  dont SaveObject réussit, notamment ScriptList (`script/api/script_list.cpp:333`)
  et ScriptTileList. Les instances Squirrel quelconques, fonctions et générateurs
  ne bénéficient pas de ce contrat. Le dictionnaire plat n'est pas imposé ;
  « primitifs » ne doit pas inclure les floats (pas de cas OT_FLOAT), et les
  chaînes ont une limite dans ce code (`:402`) : le message annonce 254 caractères,
  mais la condition `view.size() + 1 >= 255` refuse dès 254 octets UTF-8
  (donc 253 octets utiles au maximum dans cette implémentation).
  Un type non supporté produit une erreur et pas de données sauvées ; une
  corruption systématique du fichier n'est pas établie. OpexAI conserve sa
  politique plus restrictive sans instances, sans prétendre la prouver
  récursivement par regex.
- **Issues effectivement consultées le 18/10 :**
  [#10490](https://github.com/OpenTTD/OpenTTD/issues/10490) décrit sous OpenTTD
  **13.0** un navire au Full Load sur la sortie d'un dépôt bloquant d'autres
  navires. Le corps accessible ne nomme pas AAAHogEx et ne démontre pas un
  accaparement du rivage ; aucun statut de reproduction sous 15.3 n'est inféré.
  [#12133](https://github.com/OpenTTD/OpenTTD/issues/12133) décrit sous **14.0 RC1**
  une assertion de sauvegarde et joint AAAHogEx et une partie. Le corps accessible
  ne démontre ni cause « volume trop important », ni seuil RAM/Save, ni persistance
  du défaut sous 15.3. Les commentaires non rendus n'ont pas été inventés.
- **Chiffres recopiés de notre historique :**
  `docs/archives/taches_archive_2026-09-09.md:2226` contient 731 villes / 266 815
  paires ; `:1260` contient 16,74 M pour une préparation mesurée, pas une loi du
  coût de DistanceManhattan. `docs/journaux/journal_2026-08-30.md:9` et
  `ai/OpexAI/candidates.nut:109` contiennent 53 951 itérations pour le nœud de
  distance 150 d'une ancienne table empirique. Le cap actuel 5 000 réfute le
  « HARD_ITERATION_CAP fixé à 100 000 » appliqué à V261. Ces chiffres ne sont
  **ni une preuve communautaire indépendante ni une qualification actuelle**.
  Le compte combinatoire 731×730/2 = 266 815 est exact ; il ne prouve pas que le
  code actuel visite toutes ces paires.
- **Non établis :** coûts universels par voisin/tuile, borne 204–206 tuiles,
  garantie 60 IPS, RAM VM normale/critique, coût mémoire universel d'une table,
  prix fixe d'une démolition, comportement des IA nommées dans l'extrait. Aucun
  de ces nombres n'est ajouté comme seuil de test ou défaut.

### 5.5 Inventaire des appels AIList.Valuate

Le test `test_3_2_valuate_callbacks_are_native_inventory` examine récursivement
tous les `.nut`, hors commentaires, et exige que chaque premier argument soit
dans l'ensemble natif recensé et dans `docs/noai_api_15.3.tsv`. Aucun callback
Squirrel actuel, donc **aucune liste blanche de petites listes**. Un callback
natif ne prouve pas un coût nul ou une liste petite : l'absence de crash et le
coût global restent à surveiller dans les journaux.

| Fichier | Callbacks natifs et lignes |
|---|---|
| `ai/OpexAI/air_coverage.nut` | `AIRoad.IsRoadTile` (L208); `AIRoad.IsRoadStationTile` (L210); `AIRoad.IsRoadDepotTile` (L212); `AITile.IsStationTile` (L214); `AITile.GetCargoProduction` (L216); `AITile.GetClosestTown` (L222); `AITile.GetCargoProduction` (L484); `AITile.GetClosestTown` (L492) |
| `ai/OpexAI/air_sites.nut` | `AITile.IsWaterTile` (L232); `AITile.IsCoastTile` (L234); `AITile.GetClosestTown` (L237); `AIAirport.GetNearestTown` (L240); `AIMap.GetTileX` (L244) |
| `ai/OpexAI/air_towns.nut` | `AITile.IsStationTile` (L599) |
| `ai/OpexAI/builder_rail.nut` | `AIBridge.GetMaxSpeed` (L863); `AIBridge.GetMaxSpeed` (L1622); `AIBridge.GetMaxSpeed` (L2281); `AIBridge.GetMaxSpeed` (L2323); `AIBridge.GetMaxSpeed` (L2473); `AIBridge.GetMaxSpeed` (L3190); `AIBridge.GetMaxSpeed` (L3242) |
| `ai/OpexAI/candidates.nut` | `AIEngine.IsBuildable` (L161); `AIEngine.IsWagon` (L165); `AIEngine.HasPowerOnRail` (L168); `AIEngine.CanRefitCargo` (L173); `AIEngine.GetMaxSpeed` (L190) |
| `ai/OpexAI/capital.nut` | `AIVehicle.GetRunningCost` (L8) |
| `ai/OpexAI/catalog.nut` | `AIRail.IsRailTypeAvailable` (L404); `AIEngine.IsBuildable` (L426); `AIEngine.IsBuildable` (L610); `AIEngine.IsBuildable` (L726); `AIEngine.IsBuildable` (L781); `AIEngine.IsArticulated` (L783) |
| `ai/OpexAI/opcode_exact.nut` | `AITile.GetCargoProduction` (L535); `AIRoad.IsRoadTile` (L558); `AIRoad.IsRoadStationTile` (L560); `AIRoad.IsRoadDepotTile` (L562); `AITile.IsStationTile` (L564); `AITile.GetCargoProduction` (L566) |
| `ai/OpexAI/probe_v216.nut` | `AITile.IsStationTile` (L371) |
| `ai/OpexAI/spatial.nut` | `AITile.IsStationTile` (L102); `AITile.IsStationTile` (L133) |
| `ai/OpexAI/task_air.nut` | `AIStation.GetNearestTown` (L285) |
| `ai/OpexAI/task_rail.nut` | `AIBridge.GetMaxSpeed` (L1624) |
| `ai/OpexAI/tension.nut` | `AIVehicle.GetRunningCost` (L84) |
| `ai/OpexAI/terrain_valuate.nut` | `AITile.IsWaterTile` (L121); `AITile.IsCoastTile` (L127); `AITile.IsBuildable` (L133); `AITile.GetSlope` (L139); `AITile.GetMinHeight` (L145); `AITile.GetMaxHeight` (L155); `AITile.IsWaterTile` (L280); `AITile.IsCoastTile` (L297); `AITile.IsBuildable` (L314); `AITile.GetSlope` (L331); `AITile.GetMinHeight` (L348); `AITile.GetMaxHeight` (L376) |

Validation initiale V261 (`95d8a98`) : `PYTHONPATH=sweeps python3 -m unittest discover -s sweeps -p "test_*.py"`
— **1 953 tests, OK, 3 skipped, 6 expectedFailure** ; 31 nouveaux tests V261.
Les trois skips proviennent des tests existants. Aucun banc, Docker ou moteur lancé.
Extrait examiné : SHA-256 `9674d6723e43f42399f4b0572c1d4154da3c8a8372e2a1922992bacaacdb64d4`.

Validation V261b (18/10) : même commande, **1 957 tests, OK, 3 skipped,
2 expectedFailure**, 25,573 s. Module V261 : 35 tests, quatre expectedFailure
retirés (F1.1/F1.3/F1.6/F1.9), trois tests de table par niveau et un inventaire
exhaustif des appels directs de pose ajoutés. `git diff --check` vert.
Les deux expectedFailure F2.1a/F2.1c sont conservés sans modification.
Aucun banc, Docker, partie, compilation Squirrel ni test Save/Load moteur,
conformément à la demande utilisateur ; aucune qualification économique.
Les messages smoke/gain_short/non_erosion de la suite viennent de fixtures Python.

## 6. tipsyfox / t=90674 (V262)

### 6.1 Périmètre, provenance et lecture des statuts

Audit statique du 18/10/2026 sur `v261`, base `d83de3d` (master fusionné,
V261/V261b conservés). Aucun changement dans `ai/`, aucune famille protégée
modifiée, aucun moteur, banc, Docker ou push. Les correctifs ci-dessous sont
**des propositions à décider**, pas des travaux autorisés ni des gains mesurés.

Source de la liste : extrait utilisateur
`/home/deploy/.claude/jobs/e230de46/tmp/tipsyfox_extract_v262.md`.
Le [site Tipsy Fox](https://tipsyfox.net/ottd/) est accessible et annonce une
mise à jour juin 2026. Le [fil t=90674](https://www.tt-forums.net/viewtopic.php?t=90674)
renvoie une page de blocage « Oh noes! » au lecteur web : ses détails restent
attribués à l'extrait fourni, pas à une vérification indépendante des messages.
Les noms d'IA de l'extrait servent à identifier les symptômes, jamais à prouver
un défaut d'OpexAI. Une erreur fatale peut arrêter l'IA ; un redémarrage
automatique universel avec perte totale de progression n'est pas établi ici.

**« Concerné » qualifie le symptôme nuisible**, pas la simple présence de l'API.
« Oui » = mécanisme visible ; « non » = mécanisme précis exclu par le code ;
« partiellement » = protections présentes mais couverture incomplète ;
« non vérifiable statiquement » = résultat dynamique sans preuve suffisante.
Un « non » local n'est jamais une garantie universelle d'absence de crash.
Les chemins `ai/OpexAI/` sont abrégés dans les tableaux. Les lignes désignent
l'arbre audité, inchangé par V262.

Tests : `sweeps/test_v262_tipsyfox_behaviours.py` (préfixes `test_` omis
ci-dessous), inventaire figé `sweeps/fixtures/v262_valuate_inventory.json`.
Les contrats V261 cités restent actifs dans `test_v261_forum_behaviours.py`.
Un expectedFailure décrit une exigence absente ou insuffisante ; il ne constitue
ni une reproduction en VM ni une permission de corriger.

### 6.2 Valuate, tailles et calcul du budget

Le source fourni est réellement sous
`/home/deploy/.claude/jobs/e230de46/tmp/ottd15/src/src/` (noté **moteur/**).
`moteur/script/api/script_list.hpp:17` fixe `MAX_VALUATE_OPS=1000000` ;
`script_list.cpp:842` accepte les closures natives et Squirrel ; `:852` installe
le limiteur **sur tout le Valuate**, `:866` appelle chaque callback et `:910`
débite **5 opcodes par élément**, même pour une API native. Aucun découpage
implicite au milieu de cette boucle C++.

Complément au §5.4 : la distribution fournie omet `src/3rdparty/`. Les fichiers
manquants ont été lus depuis le **tag officiel 15.3**, sans modifier ce source
ni le dépôt : [sqapi.cpp](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/3rdparty/squirrel/squirrel/sqapi.cpp#L1300)
`:1300-1312` fixe le seuil au compteur d'entrée moins le budget ;
[sqvm.h](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/3rdparty/squirrel/squirrel/sqvm.h#L180)
`:180-187` teste strictement `< seuil` ; `sqapi.cpp:980-983` vérifie après l'appel
natif et émet **« excessive CPU usage in valuator function »**.
`sqvm.cpp:742-745` débite/vérifie les instructions Squirrel.
Le message est donc désormais retrouvé, contrairement à V261.

Pour les 57 sites actuels : callbacks API natifs, sans réentrée Squirrel ni
DoCommand, wrappers `moteur/script/squirrel_helper.hpp:316-333` ; coût imputé
**dans la boucle = 5N**. Avec une future closure, ajouter la somme de ses
opcodes par item : `5N + Σ callback_ops`. Ce n'est **pas un coût CPU réel** :
recherche de ville, calcul de production, coût d'un convoi et mise à jour des
arbres C++ ne sont pas proportionnellement débités. Le temps natif peut croître
sans déclencher l'erreur. Une API erronée peut échouer pour une autre raison.
Nuance de bord : après 200 001 items natifs, le dernier débit dépasse le budget
mais le contrôle n'arrive qu'au callback suivant ; 200 002 items provoquent
donc l'erreur dans ce cas simple. Ne pas utiliser cette marge comme seuil métier.

| Sites (inventaire exhaustif détaillé en 6.7) | N maximal par appel / débit 5N ; croissance | Risque du message CPU dans l'arbre actuel / proposition |
|---|---|---|
| `capital.nut:8`, `tension.nut:84` | `V` = véhicules propres primaires **+ rames de wagons libres** ; `5V`. Croît avec flotte/état des dépôts. | Théoriquement possible si V dépasse le budget ; aucune mesure d'exposition. Les plafonds ordinaires ne suffisent pas pour les wagons libres. Proposer une somme/scan reprenable, tous niveaux, si exposition confirmée. |
| `catalog.nut:426,610,726,781,783`, `candidates.nut:161,165,168,173,190` | Au plus E moteurs disponibles (diminue après filtres). `EngineID` limité à 64 000 (`moteur/engine_type.h:26`) ⇒ au plus **320 000** par appel. Croît avec NewGRF/époque, pas la surface de carte seule. | Ce budget seul ne peut dépasser 1 M avec ces callbacks. Temps CPU natif non mesuré ; ne pas remplacer systématiquement par Slow Valuate. |
| `task_air.nut:285` | A aéroports propres ≤ 64 000 stations (`moteur/station_type.h:16`) ⇒ **320 000** par appel. | Pas de dépassement 1 M par cardinalité seule. |
| `catalog.nut:404`, ponts `builder_rail.nut:863…3242`, `task_rail.nut:1624` | `5R` railtypes / `5B` types de pont compatibles avec la portée ; matériel, pas flotte ni carte. | Pas d'indice de dépassement ; petits ensembles de types moteur. |
| `air_sites.nut:232…244` | Anneau après retrait intérieur, ≤ `8r`, r ≤ `AIR_SITE_RADIUS=25` (`builder_air.nut:14`) ⇒ **1 000** par appel ; la création du rectangle temporaire est plus grande que l'anneau. | Pas de dépassement du budget Valuate avec ces bornes. |
| `air_towns.nut:599` | Carré rayon `STATION_SEARCH_RADIUS=30` (`builder_rail.nut:22`) ⇒ N ≤ 61², **18 605**. | Pas de dépassement de ce Valuate. |
| `air_coverage.nut:208…222`, `opcode_exact.nut:558…566` | Rectangle autorisé par `station_spread=S`, largeur ≤ `2S-w`, hauteur ≤ `2S-h` ; sous-listes filtrées ≤ ce rectangle. Débit ≤ `5(2S-w)(2S-h)`. | Fenêtre locale, pas liste de carte entière ; S ≤ 64 en 15.3 (`moteur/table/settings/game_settings.ini`, entrée station_spread). Même majoration grossière `5(2S)² = 81 920` reste sous 1 M. |
| `air_coverage.nut:484,492`, `opcode_exact.nut:535` | N = union des tuiles de captage, pas nombre de stations × carte ; ≤ rectangle d'emprise étendu du rayon C : `5 min(carte,(S+2C)²)`. | Pas de Valuate de carte entière démontré. Vérifier les dimensions effectives si extension du modèle / NewGRF ; coût natif par tuile non constant. |
| `spatial.nut:102,133` | N = emprise industrie étendue de coverage, ou rectangle gare étendu (`sMinX…sMaxY`). Débit `5 min(carte, largeur×hauteur)`. | Pas de borne métier universelle de toutes emprises NewGRF démontrée ici ; pas de dépassement établi. Garde de taille/découpage si les dimensions exposent le seuil, tous niveaux. |
| `probe_v216.nut:371` | Carré de côté `2(radius+V216_ADV_MAX_RADIUS)+1`, bord carte ; débit 5×aire. `V216_ADV_MAX_RADIUS=5` (`:297`). | Fenêtre paramétrée, pas carte entière ; vérifier les rayons transmis pour une configuration exotique. |
| `terrain_valuate.nut:121…155,280…376` | Bloc de côté side : N ≤ side², débit ≤ 5side² par appel. Consommateur courant `C67_SIDE=5` (`task_terrain.nut:9`) ⇒ **125** ; six passes distinctes. | Pas de dépassement avec side courant. La méthode publique n'impose pas cette taille à un futur consommateur. C67 reste sans consommateur économique. |

`AIVehicleList` inclut les wagons libres :
`moteur/script/api/script_vehiclelist.cpp:23-36`. Les quatre plafonds usuels sont
au plus 5 000 chacun (`moteur/table/settings/game_settings.ini:245-291`) :
20 000 primaires donneraient 100 000 opcodes, **pas 1 M**. En revanche la réserve
globale de VehicleID va jusqu'à `0xFF000` (`moteur/vehicle_type.h:17`) : la borne
brute de pool donnerait 5 222 400, largement au-dessus. Ce scénario théorique
demande énormément de wagons libres propres ; OpexAI suit normalement leurs
rollbacks (`builder_rail.nut:2621,2684`). Aucun crash CPU actuel n'est prouvé.
Les constructeurs sans filtre ne partagent pas le limiteur de filtre optionnel
(`script_list.hpp:94-99`) ; une grande construction de liste peut aussi coûter du
temps sans erreur Valuate.

**Boucles longues hors Valuate** : coût Squirrel généralement suspendable,
donc latence/starvation possible sans message de valuator. Aucun total exact
d'opcodes par appel ne se déduit d'un nombre de lignes ; les bornes ci-dessous
sont des estimations de complexité, pas des mesures ni un prix fixe par tuile.

| Famille / preuves | Pire croissance structurelle par invocation ; protection actuelle |
|---|---|
| Catalogue `catalog.nut:842-874,937-976`, choix matériel `:514-582,799-815` | O(T×C + I×C + E×C + E×longueurs×cargos), villes/industries/matériel ; pas de plafond d'opcodes global par méthode. Les lots production ville ont une tranche explicite (`:894-910`). |
| Candidats `candidates.nut:964-1059,1069-1182,1528-1691` | Paires villes O(T²) au pire si toutes dans les cellules voisines ; fret O(I²) / O(I×T), plus scans de lignes L. L'index spatial réduit le cas usuel, ne prouve pas une borne indépendante de carte. |
| Captage AIR `air_coverage.nut:360-425,482-495`, listes d'aéroports `air_planning.nut:839,1198`, `air_towns.nut:175,197,562` | Stations × tuiles de captage / villes / choix de paires ; cache et filtrage géométrique, sans preuve d'un coût absolu fixe. |
| Inventaire par ligne `lines.nut:78-193`, `task_report.nut:209-622`, `task_road.nut:294-428`, `task_rail.nut:380-563`, `task_air.nut:461` | O(L×V) possible avec scans `AIVehicleList_Station` répétés, puis ordres/convois ; flotte croissante. Le rapport annuel peut retarder la construction sans crash VM. |
| Arrêts existants `builder_road.nut:351-371`, recovery `air_recovery.nut:34-83` | O(stations+tuiles bus), puis tests de proximité O(arrêts) par site ; tickets×lignes et scans de véhicules par gare. |
| Route `builder_road.nut:77-112,376-414`, eau `builder_water.nut:206-232,237-287`, rail `builder_rail.nut:4513`, A* | Traces O(distance), reconstruction route par `insert(0)` jusqu'à O(chemin²) ; BFS route ≤ maxNodes (retour null), eau ≤ WATER_BFS_MAX_NODES, A* par itérations/deadline, parcours rail borné steps/limit. Un budget d'itérations n'est pas une borne du temps C++ d'une itération. |
| Terrain `terrain_map.nut` Step, `terrain_valuate.nut:88-155` | O(surface carte / side²) au total, repris par Step ; O(side²) local, cache de capacité bornée. |
| Sondes `probe_v216.nut:182,199,209,336-375`, `probes.nut:1730,2341`, `ledgers.nut:1383`, `rivals_v211.nut:71-90` | Villes, industries, stations, flotte ou moteurs ; distinguer sondes OFF et diagnostics activés. Coût sous sonde ne qualifie pas le défaut. |
| V250 `task_v250.nut:124-144,187,216`, V233 `goods_v233.nut:390-405,417-444` | Stations/captages/villes et plans×chemins ; V250 soumis au niveau 3, V233 expérimental. Ne pas désarmer une garde pour l'audit. |
| Conversion boucle `builder_rail.nut:4909-4911` | **Boucle sans progrès garanti** : RemoveOrder ignoré ; si échec permanent avec ordre restant, boucle indéfinie (suspensions possibles). Proposition tous niveaux : tester retour/progrès et abandonner proprement. Contrat `order_removal_loop_checks_progress` expectedFailure. |

Pas de parallélisation interne proposée : les scripts utilisent leur VM/budget ;
le nombre de workers du banc ne change pas le budget d'un Valuate.

### 6.3 Save/Load : volume, profondeur et limites réelles

**Deux coûts distincts.** `moteur/script/script_info.hpp:19` :
`MAX_SL_OPS=100000`. `script_instance.cpp:537` l'applique à **l'exécution de
Save()**, `:558-562` émet « This script took too long to Save. », sauve vide et
marque le script en crash. Load a aussi un budget/diagnostic (`:236`, `:801`).
Ce n'est ni une limite en millisecondes ni une limite d'octets du graphe retourné.
Après retour, SaveObject parcourt le graphe une fois pour validation puis pour
écriture (`:565-568`), en C++, **hors de ce budget de Save()**.
Temps de sérialisation O(nombre d'entrées/occurrences + octets chaînes), sans
borne temporelle fixe identifiée ; un partage de table est retraversé par occurrence.

Format (`script_instance.cpp:370-500`, `script_instance.hpp:22`) : profondeur
25, pas de float, chaîne utile au plus 253 octets UTF-8 (condition `len>=255`,
len incluant NUL). Entier : 1 octet tag + 8 valeur ; bool : tag + 1 ; null : tag ;
chaîne : tag + longueur sur 1 octet + NUL + octets ; conteneur : tag + contenu
+ marqueur fin ; table sérialise clés et valeurs, tableau ses valeurs.
Pas de plafond global de taille identifié dans ce chemin. Un cycle ou une
profondeur excessive est rejeté au plafond récursif ; pas de preuve de corruption
du fichier de partie entier. Ces règles viennent du moteur, aucun seuil ajouté.

`persist.nut:602-717` : défaut `save_full_state=1` (`info.nut:58-63`), payload
complet = lignes L et leurs champs F, vecteurs de véhicules V, historique des
abandons A et compteurs distincts H, tâches, dates C69/C75, queues réactives,
expansion rail, tickets de retrait/rollback, états optionnels C83/V250/V233.
Le format court évite les lignes mais garde abandons et tickets : pas une borne
globale de taille. Les pathfinders et caches terrain ne sont pas exportés.
Préparation complète estimée O(A + tâches + L + U×F + états auxiliaires), où U
désigne les lignes absentes du cache mensuel. La projection (`:585-599`) déplace
une grande partie du travail hors Save, mais le parcours L, la copie A et les
auxiliaires restent dans le budget. Un gros lot de nouvelles lignes peut encore
dépasser 100k ; on ne dispose pas du bytecode/exposition pour donner un L critique.
Le commentaire `:578-583` rapporte un ancien dépassement, pas une nouvelle mesure V262.

Croissance : L/V avec l'activité ; A est purgé après cooldown
(`lines.nut:292-310`), **H `_abandonCounts` n'est pas purgé avec A** ; les clés
distinctes accumulent donc l'historique de la partie. Tickets de récupération
peuvent rester si la démolition échoue. Une table de ligne est projetée seulement
en surface (`persist.nut:557-575`) ; les arrays/tables sont partagés. Aucune
validation récursive globale de floats, cycles, instances ou profondeur n'est
présente. Les structures ordinaires sont peu profondes (racine→lignes→ligne→
vehicles→ID), mais **la profondeur maximale de tous les états optionnels n'est
pas prouvée par cet audit**. Charge binaire, temps et opcodes maximaux demandent
une capture tardive et Save/Load en VM. Proposition tous niveaux : construire
un payload validé hors Save, contrôler récursivement le schéma et tester les
états tardifs ; ne pas jeter un état décisionnel pour respecter le budget.

Load filtre tuiles/stations/propriétaires/véhicules (`persist.nut:855-901`),
relance les tâches et reconstruit les caches (`:918-979`). Les scalaires de ligne
projetés mensuellement peuvent être anciens ; les tables imbriquées restent
partagées. Le test `loaded_line_type_checked_before_field_membership` relève
que **un élément non-table de `data.lines`** atteindrait `"stationA" in line`
sans validation de type (`:857`) : robustesse incomplète face à un payload
incompatible, pas un crash de sauvegarde normale démontré.

### 6.4 Chaque symptôme de l'extrait : statut, preuves et propositions

Tous les correctifs de **robustesse** proposés s'appliqueraient aux **0–3**.
Les mesures de **courtoisie** proposées sont explicitées par niveau ; aucune
nouvelle valeur numérique ni modification des familles protégées n'est proposée.

| ID / point de l'extrait | Concerné | Preuve fichier:ligne / contrat machine | Proposition de correctif et niveaux |
|---|---|---|---|
| T01 CPU excessif dans Valuate (PAXLink, AIAI, DictatorAI, FastPTPAI, MailAI, Denver & Rio Grande, TracAI) | Partiellement : taille variable, crash non observé | 6.2 ; `capital.nut:8`, `tension.nut:84` ; `cpu_each_valuate_site_is_reviewed`, `cpu_fleet_valuators_are_native_and_single_pass`, V261 `3_2` | Scan reprenable seulement si exposition, 0–3 ; pas de Slow Valuate universel sans mesure. |
| T02 CPU immédiat après rechargement (PAXLink) | Non vérifiable statiquement | `persist.nut:808-979`, `main.nut:668` ; `load_reconciles_objects_and_discards_missing_vehicles` | Stress reload tardif, distinguer Load plafonné et première reconstruction, 0–3. |
| T03 Pathfinding trop long, aucune construction (RoadAI) | Partiellement | `builder_road.nut:376-414`, `builder_water.nut:216`, rail `OpexAdvanceRailPathfinder` ; `pathfinding_has_failure_bounds_not_busy_wait`, V261 `3_1,3_4` | Diagnostiquer latence/horizon puis découper le poste exposé, 0–3 ; les budgets peuvent aussi refuser une ligne valide. |
| T04 Too long to save / save error (PathZilla, NoCAB) | Partiellement, garantie de budget absente | `persist.nut:578-717`, moteur `script_instance.cpp:537,559` ; `save_projection_is_outside_save_and_reused`, **xfail** `save_payload_preparation_has_no_state_sized_loop` | Payload préparé hors Save et schéma récursif, 0–3 ; taille/temps à mesurer. |
| T05 Renvoi soudain de tous les véhicules au dépôt (NoCAB) | Non vérifiable statiquement ; pas de renvoi global inconditionnel identifié | `task_report.nut:625-658,733-838`, `air_recovery.nut:34-54` ; `depot_orders_are_not_repeatedly_toggled` | Vérifier causes de retrait et reprise sur lignes réelles, 0–3. Une mauvaise rentabilité collective peut déclencher plusieurs retraits légitimes. |
| T06 Crash reload GetLocation inexistant (Mungo) | Non pour la méthode d'instance perdue ; reload global non garanti | Appels qualifiés API, `lines.nut:173-182`, `persist.nut:557-575` ; `missing_getlocation_method_is_not_a_persisted_instance_call` | Conserver appels API et reconstruction des instances, 0–3 ; Save/Load moteur reste nécessaire. |
| T07 Objet disparu : ville/industrie/véhicule, GetLocation invalide | Partiellement | `event_handlers.nut:151-159,265-276,414-437`, `candidates.nut:1936-1950`, `persist.nut:855-899`, `lines.nut:173-182` ; tests `industry_closed…`, `getlocation_spatial…`, `load_reconciles…` | Auditer les références mises en cache après suspensions/commandes ; scénarios industrie fermée et vente, 0–3. Les gardes locales ne prouvent pas tous les appels. |
| T08 Clonage infini / saturation ferroviaire (AdmiralAI, TrAIns) | Non pour clonage illimité ; saturation non vérifiable | `task_rail.nut:481-540`, `globals_pre.nut:79` (cap V190), attente source et slots ; `rail_cloning_has_line_cap_and_global_slot_check` | Conserver bornes ; congestion effective à tester, 0–3. Pas de bride économique arbitraire. |
| T09 Essaims de bus courts déficitaires (PAXLink) | Partiellement : pertes possibles, essaim illimité exclu par ligne | `economy.nut:666-671`, `candidates.nut:1415-1423`, `task_road.nut:360-399`, `builder_road.nut:700-708` ; `road_reinforcement_is_capped_even_when_profitable`, V261 `1_1` | Mesurer profit/congestion agrégés et santé ; robustesse 0–3 ; éventuelle courtoisie de voirie 0–1 à décider. |
| T10 Gares jamais utilisées / non détruites après abandon (BorkAI, EpicTrans, TrAIns) | Oui pour conservation après retrait ; jamais utilisées non garanti | `task_report.nut:660-727` retire `_lines`, sans démolir gares/rails/routes ; **xfail** `retired_lines_schedule_physical_infrastructure_cleanup` | Nettoyage différé avec propriété, partage et usage réel vérifiés, 0–3 ; ne pas démolir une station encore utilisée. |
| T11 Aéroports jamais utilisés (TransAI) | Partiellement | Échec de chantier : tickets `air_construction.nut:32-49`, démolition retry `air_recovery.nut:34-83` ; retrait normal T10 ; `air_build_failure_retains_retryable_cleanup_ticket` | Étendre le suivi aux abandons normaux, 0–3 ; délai « jamais » à mesurer. |
| T12 Infrastructures construites sans slots (LuDiAI) | Partiellement : rail protégé, précontrôle local absent route/air/eau | Rail `builder_rail.nut::OpexRailVehicleSlotAvailable`, V261 `2_1_train_zero_limit…` ; route `builder_road.nut:714,819`, air `air_construction.nut:231,358`, eau `builder_water.nut:524-630` ; trois **xfail** `*_vehicle_limit_rechecked_before_infrastructure` | Généraliser contrôle transactionnel du plafond du mode, 0–3. Les limites lues par `tension.nut:133-136` ne prouvent pas un refus physique avant dépenses. |
| T13 Gares/dépôts à côté mais non raccordés ; implantation incohérente (CluelessPlus) | Partiellement | Route : raccord et contrôle réel `builder_road.nut:791-808`, BFS `:376-414` ; V261 `2_3` et tests `road_depot_connectivity…`, `road_passenger_reuse…` | Contrôles après construction et graphe praticable jusqu'aux deux stations, 0–3 ; cohérence esthétique dynamique. |
| T14 Trop de dépôts routiers (Snake) | Partiellement | Un dépôt par construction `builder_road.nut:794`, conservé au retrait T10 ; `road_construction_builds_one_depot_not_one_per_path_tile` | Réutilisation sûre/collecte des dépôts orphelins, 0–3 ; « trop » demande une mesure, pas un seuil inventé. |
| T15 Restes routes/rails après démolition (Snake) | Oui après retrait normal ; rollback partiel présent | `builder_road.nut:549-574`, `builder_rail.nut::OpexRollback`, mais `task_report.nut:721-727` ; `road_partial_rollback…`, xfail T10, V261 `1_8` | Journal d'ouvrages ajoutés, démontage différé sans toucher tiers/partages, 0–3. Les retours d'échec de suppression ne sont pas tous repris. |
| T16 Arrêts de bus hors réseau urbain (AIAI, NotPerfectAI) | Partiellement | Voirie voyageurs réutilisée : `builder_road.nut:420-540` et BFS connecté ; autres plans tracent des routes `opcode_exact.nut:404-456` ; `road_passenger_reuse_traverses_connected_existing_roads` | Distinguer desserte fret légitime et arrêt voyageurs isolé ; robustesse connectivité 0–3, restriction de courtoisie éventuelle 0–1. |
| T17 Bouées excessives (HeliFerry) | Non | Aucun `AIMarine.BuildBuoy` dans tous les `.nut` ; `buoys_canals_and_locks_are_not_built`, V261 `1_2` | Aucun correctif. |
| T18 Navigation suit aveuglément littoral / détour estuaire (HeliFerry) | Non pour algorithme côtier imposé ; détour effectif non vérifiable | `builder_water.nut:206-232` BFS eau, puis économie distance navigable `:291-338` ; `pathfinding_has_failure_bounds_not_busy_wait` | Scénario estuaire sur eau ouverte, 0–3 si défaut ; ne pas réintroduire Lakes ni fabriquer un nouvel itinéraire. |
| T19 Joining adjacent stations OFF ⇒ labyrinthe routier (MogulAI) | Partiellement : option non lue, pas de labyrinthe prouvé | `builder_road.nut:580-652` tente deux côtés, teste commande, rollback ; `air_construction.nut:55-155` explicite StationID ; `adjacent_join_attempt_has_rollback_on_failure` | Scénario avec `station.adjacent_stations` OFF ; corriger les retries/joins incompatibles si exposés, 0–3. Absence de lecture ≠ crash. |
| T20 Tracés ferrés absurdes / wild track building (ChooChoo, AAAHogEx) | Non vérifiable statiquement | A* borné et seconde voie parallèle `builder_rail.nut:1573`, appels `FindPath(PATH_CHUNK)` ; V261 `3_1,3_4` | Inspection du tracé/détour/congestion en partie avant proposition, 0–3 ; esthétique seule éventuellement courtoisie 0–1. |
| T21 Routes/ponts défectueux sur marshland (KrakenAI) | Non vérifiable statiquement | `builder_road.nut:115-147` AITestMode + construction réelle, `:791-808` connexion ; `terrain_is_tested_by_commands_not_a_marshland_enum` | Carte/version/terrain exposant ce symptôme puis test connexion, 0–3 ; ne pas inventer un enum marshland NoAI. |
| T22 Droits exclusifs irritants (LuDiAI AfterFix) | Oui en custom configuré ; non en 0–2 | `difficulty.nut:29`, `task_v250.nut::_dispatchV250Rights` ; V261 `1_5` | Règle déjà livrée : interdits 0–2, autorisés 3 si configurés ; aucun nouveau correctif. |
| T23 Spam panneaux / debug non coupé (MailAI, CPU) | Oui au défaut pour instrumentation ; désactivable | `settings.nut` debug_signs, `probes.nut::OpexSign`, `task_report.nut` ; V261 `1_9` inventaire de tous BuildSign | Courtoisie : proposer profil sans panneaux 0–1 ou tous niveaux en partie humaine, décision requise ; garder les besoins du banc distincts. Aucun seuil nouveau. |
| T24 Arrêts sur voirie retardant les tiers (AAAHogEx 2023, PAXLink) | Oui possible ; gêne non mesurée | `builder_road.nut:420-540`, `air_construction.nut:55-155`, V261 `1_1` | Gardes AIR jointes **déjà interdites 0–1**, autorisées 2–3 ; ne pas confondre avec interdiction de tous les bus. Autre courtoisie voirie 0–1 seulement après exposition. |
| T25 Saturation rapide du plafond global (AroAI) | Non vérifiable statiquement | Caps par ligne `task_road.nut:391`, `task_rail.nut:483`, tension `tension.nut:133-182` ; `road_reinforcement…`, `rail_cloning…` | Distinguer utilisation rentable des slots et gaspillage ; pas de réserve arbitraire proposée. Voir T12, robustesse 0–3. |
| T26 Double tête / max_train_length ⇒ boucle infinie (OtviAI) | Non pour boucle d'ajout ; partiellement pour longueur admissible | `builder_rail.nut:2642-2712` nombre fini de wagons, longueur réelle convoi, retour sur échec MoveWagon ; `catalog.nut:395`, `economy.nut:208-211` clamp seulement pax V207 ; `double_head_cannot_create_an_unbounded_wagon_retry`, **xfail** `max_train_length_clamp_is_not_limited_to_v207_pax` | Borner tous convois à la longueur autorisée et mesurer double tête, 0–3 ; pas d'ajout séparé de motrice arrière en boucle identifié. |
| T27 Joueur fonde une ville ⇒ crash (AdmiralAI) | Non pour catalogue figé sans handler ; crash global non vérifiable | `events.nut:360`, `event_handlers.nut:414-437` validation/dirty/refresh ; `town_founded_refreshes_catalog_with_validity_guard` | Scénario fondation pendant travail en cours, 0–3 si défaut. |
| T28 forbid 90 degree turns mal géré (Denver & Rio Grande, MailAI) | Partiellement | Pas de lecture explicite `vehicle.forbid_90_deg` ; V261 **xfail** `2_1_forbid_90_setting_is_consulted` ; A* ne prouve pas tous les raccords | Vérifier routes complètes sous option ON, corriger raccords exposés, 0–3 ; lecture seule du réglage ne suffirait pas à prouver conformité. |
| T29 Plafond avions à 0 / mode désactivé / IA monomodale inutile | Partiellement : multimodale, switches internes mais pas API globale | `settings.nut` charge les quatre mode_*, `tension.nut:70-73,133-136`, T12 ; V261 **xfail** `2_1_disabled_vehicle_types_are_read`, nouveau `all_mode_switches_are_loaded` | Combiner capacité/type autorisé et slots dès sélection, revalider avant construction, 0–3. Distinguer `mode_air=0`, max_aircraft=0 et type interdit dans paramètres IA ; autres modes peuvent fonctionner. |
| T30 Index absent / pptile / null / invalid location (LuDiAI, MpAI, Rythorn, TracAI, RoadRunner, CivilAI, TeshiNet) | Partiellement ; pas de crash courant reproduit | Champs optionnels testés dans `persist.nut:735-755`, validations T07 ; **absence de contrôle type ligne** `:857` ; `optional_loaded_keys_have_membership_guards`, **xfail** `loaded_line_type_checked_before_field_membership` | Valider schéma à Load et frontières de tâches, 0–3. Ces tests ne constituent pas une analyse de flot Squirrel globale ; API invalide peut retourner sentinelle plutôt que crasher. |

Compléments V261b à préserver : `difficulty.nut:33-35` autorise les arrêts
joints AIR seulement en **2–3**, le dépôt naval devant quai et la greffe sur
secondaire tierce seulement en **3**. Les tests V261
`air_joined_road_stops_levels`, `water_depot_dock_front_levels`,
`secondary_graft_rival_served_levels` vérifient les quatre niveaux.
Les propositions V262 ne rouvrent pas cette décision ni les pistes économiques
abandonnées ; robustesse et courtoisie ne sont pas interchangeables.

### 6.5 Cinq risques prioritaires (ordre d'audit, pas fréquence mesurée)

1. **Save/Load tardif** : budget 100k encore dépendant de l'état, schéma récursif
   non garanti ; conséquence possible = arrêt de l'IA / état absent. T04/T30.
2. **Boucle RemoveOrder sans progrès** (`builder_rail.nut:4909`) : si l'échec
   persiste, l'IA ne sort pas de la conversion. Risque de blocage, pas un
   dépassement Valuate. Scénario d'échec commande nécessaire.
3. **Infrastructures orphelines après retrait** : mécanisme confirmé T10/T15 ;
   perte économique/occupation de carte, disparition du suivi après timeout.
4. **Slots/modes interdits hors rail** : dépenses avant échec de véhicule T12/T29,
   même avec rollback ultérieur ; exposition max=0 à vérifier.
5. **Longueur de train / géométrie sous paramètres non standard** : boucle Otvi
   exclue, mais clamp incomplet T26 et raccords forbid_90 T28 à éprouver.

Le dépassement Valuate sur flotte extrême demeure un risque théorique surveillé,
**pas un crash courant établi** justifiant de le classer devant ces lacunes.

### 6.6 Validation et questions qui demandent un moteur

Contrats statiques : inventaire exact des 57 sites, assertions locales positives,
huit nouveaux expectedFailure documentés (Save indépendant de taille, nettoyage
infrastructures, trois contrôles slots, clamp longueur, type ligne chargé,
progrès suppression d'ordres). Deux expectedFailure V261 conservés (forbid_90,
véhicules désactivés). Les tests verts ne compilent pas Squirrel et ne prouvent
ni santé longue durée, ni profit, ni absence universelle de crash.

Restent à trancher **sans lancement dans ce lot** : Save/Load tardif et payload
optionnel maximal (opcodes, profondeur, octets, durée), reprise après fondation
ville/fermeture industrie/vente entre tranches, échec permanent de RemoveOrder,
plafonds 0 et types désactivés dans chaque mode, NewGRF double tête et longueur
réduite, joining adjacent OFF, forbid_90 ON, connexion physique des deux gares,
marshland dans un runtime identifié, congestion/profit des bus, durée de vie des
orphelins, détour des navires dans un estuaire, CPU réel sur grande carte/flotte.
Un scénario de robustesse ciblé suffit d'abord ; des portes économiques ne
seraient pertinentes qu'après décision d'un changement comportemental.

Validation V262 : `PYTHONPATH=sweeps python3 -m unittest discover -s sweeps -p "test_*.py"`
— **1 991 tests en 24,596 s, OK (3 skipped, 10 expectedFailure)** ; 32 nouveaux
tests V262, dont 8 expectedFailure. `git diff --check` vert. Les trois skips
préexistaient ; les messages de campagne de la suite proviennent de fixtures
Python. Aucun lancement OpenTTD/Docker/banc ni validation Save/Load en VM.


### 6.7 Registre des 57 sites Valuate audités

Chaque ligne est un appel distinct, y compris répétitions de callbacks. Les
variables N, V, E, A, B, R et les bornes sont définies en 6.2 ; les sous-listes
filtrées ne peuvent excéder leur liste initiale. Le fixture JSON fige fichier,
récepteur et arguments (hors espaces), sans dépendance au source moteur local.

| Site `ai/OpexAI/` | Récepteur / callback (arguments conservés dans le fixture) | Majoration par appel |
|---|---|---|
| `air_coverage.nut:208` | `tiles` / `AIRoad.IsRoadTile` | rectangle spread / union captage ; 5N |
| `air_coverage.nut:210` | `tiles` / `AIRoad.IsRoadStationTile` | rectangle spread / union captage ; 5N |
| `air_coverage.nut:212` | `tiles` / `AIRoad.IsRoadDepotTile` | rectangle spread / union captage ; 5N |
| `air_coverage.nut:214` | `tiles` / `AITile.IsStationTile` | rectangle spread / union captage ; 5N |
| `air_coverage.nut:216` | `tiles` / `AITile.GetCargoProduction` | rectangle spread / union captage ; 5N |
| `air_coverage.nut:222` | `townRoad` / `AITile.GetClosestTown` | rectangle spread / union captage ; 5N |
| `air_coverage.nut:484` | `cargoTiles` / `AITile.GetCargoProduction` | rectangle spread / union captage ; 5N |
| `air_coverage.nut:492` | `townOwned` / `AITile.GetClosestTown` | rectangle spread / union captage ; 5N |
| `air_sites.nut:232` | `tiles` / `AITile.IsWaterTile` | anneau ≤ 8r ; ≤ 40r |
| `air_sites.nut:234` | `tiles` / `AITile.IsCoastTile` | anneau ≤ 8r ; ≤ 40r |
| `air_sites.nut:237` | `tiles` / `AITile.GetClosestTown` | anneau ≤ 8r ; ≤ 40r |
| `air_sites.nut:240` | `tiles` / `AIAirport.GetNearestTown` | anneau ≤ 8r ; ≤ 40r |
| `air_sites.nut:244` | `tiles` / `AIMap.GetTileX` | anneau ≤ 8r ; ≤ 40r |
| `air_towns.nut:599` | `tiles` / `AITile.IsStationTile` | carré rayon 30 ; ≤ 18 605 |
| `builder_rail.nut:863` | `bridges` / `AIBridge.GetMaxSpeed` | B types de ponts ; 5B |
| `builder_rail.nut:1622` | `bridges` / `AIBridge.GetMaxSpeed` | B types de ponts ; 5B |
| `builder_rail.nut:2281` | `bridges` / `AIBridge.GetMaxSpeed` | B types de ponts ; 5B |
| `builder_rail.nut:2323` | `bridges` / `AIBridge.GetMaxSpeed` | B types de ponts ; 5B |
| `builder_rail.nut:2473` | `bridges` / `AIBridge.GetMaxSpeed` | B types de ponts ; 5B |
| `builder_rail.nut:3190` | `bridges` / `AIBridge.GetMaxSpeed` | B types de ponts ; 5B |
| `builder_rail.nut:3242` | `bridges` / `AIBridge.GetMaxSpeed` | B types de ponts ; 5B |
| `candidates.nut:161` | `list` / `AIEngine.IsBuildable` | E moteurs ; 5E |
| `candidates.nut:165` | `list` / `AIEngine.IsWagon` | E moteurs ; 5E |
| `candidates.nut:168` | `list` / `AIEngine.HasPowerOnRail` | E moteurs ; 5E |
| `candidates.nut:173` | `list` / `AIEngine.CanRefitCargo` | E moteurs ; 5E |
| `candidates.nut:190` | `list` / `AIEngine.GetMaxSpeed` | E moteurs ; 5E |
| `capital.nut:8` | `vehicles` / `AIVehicle.GetRunningCost` | V ; 5V (primaires + wagons libres) |
| `catalog.nut:404` | `types` / `AIRail.IsRailTypeAvailable` | R railtypes / E moteurs ; 5R / 5E |
| `catalog.nut:426` | `engines` / `AIEngine.IsBuildable` | R railtypes / E moteurs ; 5R / 5E |
| `catalog.nut:610` | `engines` / `AIEngine.IsBuildable` | R railtypes / E moteurs ; 5R / 5E |
| `catalog.nut:726` | `engines` / `AIEngine.IsBuildable` | R railtypes / E moteurs ; 5R / 5E |
| `catalog.nut:781` | `engines` / `AIEngine.IsBuildable` | R railtypes / E moteurs ; 5R / 5E |
| `catalog.nut:783` | `engines` / `AIEngine.IsArticulated` | R railtypes / E moteurs ; 5R / 5E |
| `opcode_exact.nut:535` | `coverageTiles` / `AITile.GetCargoProduction` | union captage / rectangle spread ; 5N |
| `opcode_exact.nut:558` | `tiles` / `AIRoad.IsRoadTile` | union captage / rectangle spread ; 5N |
| `opcode_exact.nut:560` | `tiles` / `AIRoad.IsRoadStationTile` | union captage / rectangle spread ; 5N |
| `opcode_exact.nut:562` | `tiles` / `AIRoad.IsRoadDepotTile` | union captage / rectangle spread ; 5N |
| `opcode_exact.nut:564` | `tiles` / `AITile.IsStationTile` | union captage / rectangle spread ; 5N |
| `opcode_exact.nut:566` | `tiles` / `AITile.GetCargoProduction` | union captage / rectangle spread ; 5N |
| `probe_v216.nut:371` | `tiles` / `AITile.IsStationTile` | carré rayon étendu ; 5N |
| `spatial.nut:102` | `tiles` / `AITile.IsStationTile` | emprise étendue industrie / gare ; 5N |
| `spatial.nut:133` | `tiles` / `AITile.IsStationTile` | emprise étendue industrie / gare ; 5N |
| `task_air.nut:285` | `ownAirports` / `AIStation.GetNearestTown` | A aéroports propres ; 5A |
| `task_rail.nut:1624` | `bridges` / `AIBridge.GetMaxSpeed` | B types de ponts ; 5B |
| `tension.nut:84` | `vehicles` / `AIVehicle.GetRunningCost` | V ; 5V (primaires + wagons libres) |
| `terrain_valuate.nut:121` | `work` / `AITile.IsWaterTile` | bloc side² ; ≤ 5side² |
| `terrain_valuate.nut:127` | `work` / `AITile.IsCoastTile` | bloc side² ; ≤ 5side² |
| `terrain_valuate.nut:133` | `work` / `AITile.IsBuildable` | bloc side² ; ≤ 5side² |
| `terrain_valuate.nut:139` | `work` / `AITile.GetSlope` | bloc side² ; ≤ 5side² |
| `terrain_valuate.nut:145` | `work` / `AITile.GetMinHeight` | bloc side² ; ≤ 5side² |
| `terrain_valuate.nut:155` | `work` / `AITile.GetMaxHeight` | bloc side² ; ≤ 5side² |
| `terrain_valuate.nut:280` | `work` / `AITile.IsWaterTile` | bloc side² ; ≤ 5side² |
| `terrain_valuate.nut:297` | `work` / `AITile.IsCoastTile` | bloc side² ; ≤ 5side² |
| `terrain_valuate.nut:314` | `work` / `AITile.IsBuildable` | bloc side² ; ≤ 5side² |
| `terrain_valuate.nut:331` | `work` / `AITile.GetSlope` | bloc side² ; ≤ 5side² |
| `terrain_valuate.nut:348` | `work` / `AITile.GetMinHeight` | bloc side² ; ≤ 5side² |
| `terrain_valuate.nut:376` | `work` / `AITile.GetMaxHeight` | bloc side² ; ≤ 5side² |

Traçabilité de lecture (SHA-256 ; sources externes non requises par les tests) :

- `tipsyfox_extract_v262.md` : `af135e4feb65ce77e9b6ce007b220f2a13edeaf3f6e00884ab45026729d058c4`.
- `script_list.cpp` : `c265df3005f36ad2029c1c1dd3d0cd452d07ccb40f2231420e5ec75e3a93a138`.
- `script_list.hpp` : `fa1faaf736743e127f601db61b73b4066d05e037b572df0d3eca5697cbc32a09`.
- `script_instance.cpp` : `077e4f9a5dcd5e70ce44e7c4c01ef0014cb3b3379ed3dd0b2e0c0b026b03fe1d`.
- `script_info.hpp` : `1094fd15cd608ce54dc7aa98fc29d0cd7a722d9df72d3fcad74d02e799526fd9`.
- `v262_sqapi.cpp` : `b6caeba4e033bce8443d817aff828fa18d42409417041739bb66e4f53b1de71b`.
- `v262_sqvm.cpp` : `3ba7d708ddd80805505543f7f078a38c452624d77c90c9d9734e98d7bd0c414d`.
- `v262_sqvm.h` : `8abca78ab52e8d1049c4a5fa2571c57aa8a3af5ce45871fd720ed57b5a62df7e`.
- `v262_squirrel.h` : `a453931bd22120b91a621177c2dad75ca1bd081723cb8b249466f06891ac6647`.
