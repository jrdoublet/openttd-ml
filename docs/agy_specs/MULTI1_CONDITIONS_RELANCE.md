# Spécification technique : MULTI-1 — Conditions de Relance du Multimodal

## 1. Objectif et critère de succès chiffré

### Contexte et problème
En mode multimodal (AIR + RAIL + ROUTE actifs), OpexAI enregistre un excellent niveau de performance sur les premières années, mais subit un décrochage sévère face à AAAHogEx sur l'horizon de 10 ans :
1. **À 5 ans (fin 1974)** : OpexAI affiche **2 867 118 £/an contre 3 094 032 £/an pour AAAHogEx, soit 92,67 %** (référence 40×5 `p6_win_porteA_40x5_20261026`, voir `docs/multi1_analyse_20261026.md`). OpexAI démarre systématiquement en mode AIR (février 1970 sur 40/40 graines) avant d'engager son premier train en 1971.
2. **À 10 ans (1979)** : OpexAI décroche à **56,55 %** dans les anciennes campagnes 20×10 et à **66,56 %** sous ESTIM-31, restant sous la cible stratégique fixée à **≥ 75 %** du profit annuel moyen d'AAAHogEx (`docs/taches.md` ligne 1211).
3. **Autopsie du décrochage tardif (1975–1979)** :
   - Le diagnostic C63 (campagne 5×11 `multi1_late_c63_5x11_20261026`, commit `340545cc`) démontre que le décrochage n'est **pas causé par un manque d'argent** : la trésorerie moyenne d'OpexAI s'élève à **16,27 M£ fin 1979 avec 0 jour d'impossibilité financière (`unaffordable = 0`)** !
   - Le système subit une **starvation de chantiers neufs** : sur les 5 années 1975–1979 cumulées, OpexAI ne construit en moyenne par monde que **1,2 nouvel aéroport, 4,2 lignes rail et 0,2 ligne route** (totalisant seulement 345,5 k£ d'investissements neufs, contre 2,310 M£ consacrés à 39,6 interventions de renfort de flotte).
   - Pendant ce temps, le planificateur passe en moyenne **172 jours par an (836 jours sur 5 ans) en état résiduel `invalid`** : les viviers de sites principaux sont épuisés ou bloqués par la concurrence, et l'IA n'ouvre aucun front d'investissement secondaire.
   - AAAHogEx continue quant à elle de saturer la carte avec **147 véhicules routiers contre 4 pour OpexAI** et réinvestit continuellement sa trésorerie.

### Tentatives antérieures et suspension
Le 26 octobre 2026, quatre leviers précoces ont été mesurés et rejetés (tous clos sous verdict NO-GO non exposé) :
- *Levier 1 (priorité route)* : zéro projet routier exposé en début de partie.
- *Levier 2 (AIR avant RAIL)* : déjà réalisé par construction dès février 1970 (H1 réfutée).
- *Levier 3 (détour géométrique route TRACEX)* : non exposé.
- *Levier 4 (SHADOW fret routier alternatif)* : 12 déclenchements, 14 couples examinés, mais 0/4 plans physiques validés sur 0/5 mondes (coût jusqu'à 473 213 opcodes par atome de trace).
Face à ces constats, MULTI-1 a été **officiellement suspendu le 26/10** dans l'attente d'une étude de constructibilité et de conditions strictes de réouverture.

### Critères de succès chiffrés
1. **Condition de levée de la suspension (Trigger)** :
   - Année de jeu ≥ 1975 (horizon tardif exclusivement, aucun changement sur 1970–1974).
   - Trésorerie nette disponible `cash >= 2 000 000 £` sans dette résiduelle.
   - Starvation avérée : aucun chantier neuf validé dans les 180 derniers jours OU vivier primaire de sélection vide (`this._projects.best.len() == 0`).
2. **Performance économique attendue** :
   - Réinvestissement productif de 2 à 4 M£ de trésorerie oisive sur 1975–1979.
   - Gain net terminal : **+50 000 £ à +120 000 £/an** de `profit_year` à 10 ans.
   - Atteinte du seuil cible : ratio moyen OpexAI / AAAHogEx porté de **66,56 % à ≥ 75,0 % en 20×10**.
3. **Gardes de non-régression** :
   - Préservation stricte de la trajectoire 1970–1974 (zéro altération des 5 premières années).
   - Zéro starvation d'opcodes sur le service de flotte (`_resizeAirFleets` et `_resizeRoadFleets`).
   - Respect de la garde de valeur −5 % aux deux portes.

---

## 2. État du code existant (fichier:ligne vérifiés dans le worktree)

### 2.1 Déclaration des modes et politique d'ordonnancement initial
- [`ai/OpexAI/globals_pre.nut:9-12`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/globals_pre.nut#L9-L12) :
  ```squirrel
  MODE_AIR <- true;
  MODE_RAIL <- true;
  MODE_ROAD <- true;
  MODE_WATER <- true;
  ```
  Les interrupteurs modaux V166 activent les trois modes par défaut en partie normale.
- [`ai/OpexAI/projects_selection.nut:1686-1695`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/projects_selection.nut#L1686-L1695) :
  ```squirrel
  /* EB-14 : en debut de partie, sous MODE_AIR, on preserve le capital pour la
   * premiere liaison AIR : publier un RAIL ne lui donne pas le droit de
   * consommer sa tresorerie avant la premiere construction AIR. */
  if (EB14_PROGRESSIVE && MODE_AIR && C121_CATALOG_FIRST_YEAR_ACTIVE) {
    local airFirst = [];
    foreach (project in alternatives)
      if (project.mode == "air") airFirst.append(project);
    alternatives = airFirst;
  }
  ```
  Le filtrage précoce garantit la priorité absolue à la première ligne AIR, ce qui explique le départ sain en 1970.

### 2.2 Viviers de candidats et critères de sélection
- [`ai/OpexAI/candidates.nut:40-73`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/candidates.nut#L40-L73) : `OpexFilterRankCargos` : classe les marchandises par tarif, mais élimine les opportunités routières dès lors qu'aucun véhicule ou qu'aucune industrie active n'est immédiatement détectée.
- [`ai/OpexAI/candidates.nut:335-375`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/candidates.nut#L335-L375) : `state.servedCount < AIR_EARLY_SLOT_TARGET_TOWNS` : limite la recherche de sites aériens aux villes cibles majeures. En fin de partie, une fois ces villes desservies, le générateur n'explore plus les paires de villes moyennes.
- [`ai/OpexAI/projects_selection.nut:1057-1070`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/projects_selection.nut#L1057-L1070) : calcul du score de financement `fundScore`. En phase tardive, `kDec` impose un seuil de sévérité élevé qui rejette les projets routiers ou ferroviaires secondaires même si la caisse est pléthorique.

### 2.3 Boucle principale et diagnostic de starvation
- [`ai/OpexAI/orchestrator.nut:230-270`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/orchestrator.nut#L230-L270) : gestion du travailleur `rail_search` et cadence des tâches. Les recherches ferroviaires infructueuses continuent de consommer des tranches de calcul sans déboucher sur des plans physiques.
- [`ai/OpexAI/task_projects.nut:120-159`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/task_projects.nut#L120-L159) : funnel mensuel `OpexMonthlyFunnelLog` consignant les rejets de construction (`AFAIL`, `BFAIL`, `town_limit`).

---

## 3. Conception technique proposée

### 3.1 Nouveau réglage comportemental
- **Nom** : `multi1_relance`
- **Déclaration** : dans `ai/OpexAI/info.nut` (4 difficultés : easy, medium, hard, custom = 0).
- **Plage** : `min_value = 0, max_value = 2`
  - `0` : OFF (comportement courant, suspendu, baseline rigoureusement identique).
  - `1` : SHADOW / Télémétrie passive (détecte et logue les conditions de relance sans altérer les choix).
  - `2` : ON conditionnel (active les viviers secondaires en cas de starvation tardive avérée).
- **Globale** : `MULTI1_RELANCE <- 0;` dans `globals_pre.nut`, lue dans les deux chargeurs de `settings.nut`.

### 3.2 Prédicat d'activation tardive (`OpexMulti1TriggerActive`)
Dans `ai/OpexAI/projects_selection.nut` :
```squirrel
function OpexMulti1TriggerActive(ai, state)
{
  if (MULTI1_RELANCE == 0) return false;
  // Garde temporelle absolue : jamais avant 1975
  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  if (year < 1975) return false;

  // Garde de trésorerie : caisse abondante sans emprunt
  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local loan = AICompany.GetLoanAmount();
  if (cash < 2000000 || loan > 0) return false;

  // Détection de starvation de chantiers neufs
  local daysSinceBuild = ("lastNewBuildDate" in state && state.lastNewBuildDate > 0)
      ? (AIDate.GetCurrentDate() - state.lastNewBuildDate) : 999;
  local portfolioEmpty = (ai._projects == null || !("best" in ai._projects)
                          || ai._projects.best == null || ai._projects.best.len() == 0);

  return (daysSinceBuild >= 180 || portfolioEmpty);
}
```

### 3.3 Viviers secondaires mobilisés sous relance
Lorsque `OpexMulti1TriggerActive` est vrai :
1. **Ouverture du vivier ROUTE Express/Feeder** :
   - Autoriser la liaison routière entre villes de population 600..2000 situées dans le bassin de rabattement d'un aéroport ou d'une gare existante (`feeder` passagers/courrier).
   - Seuil de distance modéré (20 à 50 tuiles) évitant les A* routiers prohibitifs.
2. **Ouverture des aéroports de taille intermédiaire** :
   - Autoriser `OpexAirPlansNewPairs` à évaluer les aérodromes de type `AIRPORT_COMMUTER` ou `AIRPORT_CITY` pour les paires de villes non desservies de distance 60..150 tuiles.
3. **Plafond d'allocation sécurisé** :
   - Ne jamais allouer plus de 25 % de la trésorerie totale disponible à un projet secondaire.
   - Réserver en permanence un plancher de caisse de 1 000 000 £ pour les renouvellements et renforts de flotte mûre.

### 3.4 Interaction avec Save/Load
- Dans `ai/OpexAI/persist.nut` :
  - Ajouter `lastNewBuildDate` dans la table de sérialisation `OpexSaveState`.
  - À la reprise d'une sauvegarde antérieure, réinitialiser `lastNewBuildDate = AIDate.GetCurrentDate()` pour accorder un délai de grâce de 180 jours avant tout déclenchement secondaire.

---

## 4. Pièges connus et leçons du backlog

1. **Piège du lancement précoce (1970–1974)** :
   Les campagnes 40×5 du 26/10 prouvent qu'OpexAI est déjà à **92,67 %** d'AAAHogEx à 5 ans. Tenter de favoriser la route ou de modifier l'ordre des chantiers avant 1975 dégrade l'amorçage AIR qui est la force majeure d'OpexAI. La porte d'entrée de MULTI-1 doit rester **strictement verrouillée avant 1975**.
2. **Piège du fret routier fantôme (Levier 4 du 26/10)** :
   Vouloir trouver du fret routier alternatif sur de longues distances a coûté jusqu'à **473 213 opcodes par atome de trace** pour 0 gisement physique exploitable. Le multimodal secondaire doit se limiter aux passagers/courrier où la demande urbaine est garantie.
3. **Piège de la mauvaise interprétation du ledger C63 `invalid`** :
   Le diagnostic du 26/10 a relevé 836 jours en état `invalid`. Cela signifie que les paires favorites de l'algorithme échouent en boucle, **non qu'il n'existe aucune autre ville raccordable sur la carte**.
4. **Piège de l'érosion de la valeur compagnie** :
   Construire des projets à bas rendement pour le seul plaisir de dépenser la caisse ferait échouer la porte de garde de valeur (−5 %). Le critère de sélection doit exiger une rentabilité marginale positive et un délai de retour sur investissement inférieur à 4 ans.

---

## 5. Plan de test et protocole de validation

### 5.1 Tests unitaires hôte (sans partie)
- `sweeps/test_multi1_restart_conditions.py` :
  - Vérifier que `multi1_relance` est déclaré à 0 sur les 4 difficultés dans `info.nut`.
  - Vérifier que `OpexMulti1TriggerActive` renvoie `false` pour toute date antérieure au 01/01/1975, quelle que soit la trésorerie.
  - Vérifier qu'avec `cash < 2 000 000 £` ou dette > 0, le trigger renvoie `false`.
  - Vérifier la détection exacte de starvation lorsque `daysSinceBuild >= 180`.
  - Vérifier la préservation byte-à-byte du comportement OFF (`multi1_relance = 0`).

### 5.2 Smoke et qualification causale
- **Smoke hôte** : 1 graine × 1 an (2 duels appariés contre AAAHogEx) pour valider la non-régression et la compilation Squirrel.
- **Diagnostic d'exposition** : 5 graines × 10 ans (`probes=2`) pour vérifier que le trigger s'active bien entre 1975 et 1979 et débloque 2 à 5 chantiers secondaires sans encombrement d'opcodes.
- **Porte A (`gain_short`)** :
  - Comme le mécanisme est par conception **inerte avant 1975**, la porte A doit utiliser l'horizon adapté : **40 graines × 10 ans** (`profile=custom` sur GitHub Actions, conformément au protocole V102 §4 pour les mécanismes tardifs).
  - Seuil de succès : gain moyen `profit_year` terminal **≥ +4 %**, Wilcoxon bilatéral exact **p < 0,05**, borne basse de l'IC95 bootstrap **> 0**, garde de valeur de compagnie **−5 %**.
- **Porte B (`non_erosion`)** :
  - **20 graines × 10 ans** : borne haute de l'IC95 bootstrap **≥ 0**, garde de valeur **−5 %**.

---

## 6. Estimation de difficulté et effet attendu

| Dimension | Estimation | Justification / Source |
|---|---|---|
| **Difficulté technique** | **Moyenne** (3 / 5) | Le prédicat de déclenchement est isolé et simple ; la difficulté réside dans le filtrage propre des paires secondaires sans surcoût d'opcodes A*. |
| **Effet attendu sur profit_year** | **+50 000 à +120 000 £/an** à 10 ans | Réactivation de 3 à 6 lignes rentables sur les 5 dernières années, injectant ~2 à 4 M£ de trésorerie oisive. |
| **Effet sur le ratio Opex / AAA** | **Passage de ~66 % à ≥ 75 %** | Comblement de la moitié de l'écart historique de 1979 constaté lors du bilan C63. |
| **Impact sur les opcodes** | Négligeable (< +2 % ticks) | Déclenché uniquement lorsque le vivier principal est vide (pendant les tours de boucle oisifs `sleep_slack`). |
