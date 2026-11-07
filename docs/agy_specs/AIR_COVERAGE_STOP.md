# Spécification technique : AIR-COVERAGE-STOP / EB-1

## 1. Objectif et critère de succès chiffré

### Objectif
Arrêter définitivement les recherches répétées et infructueuses de nouvelles villes et de nouveaux sites aéroportuaires lorsque le vivier de villes équipables est saturé / épuisé.
Le périmètre est strictement encadré par décision utilisateur (voir `docs/taches.md` ligne 1189) :
1. Une énumération initiale des villes équipables lors du démarrage ou du premier cycle.
2. Une fois le vivier épuisé (toutes les villes candidates testées sans nouveau site constructible ou admissible), **mise en veille complète** de la recherche de nouvelles villes et de nouveaux sites aéroportuaires.
3. Aucune réactivation cyclique par TTL, croissance démographique, niveau de trésorerie, disponibilité de nouveaux moteurs ou simple écoulement du temps.
4. **Seul `AIEvent.ET_TOWN_FOUNDED`** réveille la recherche de nouvelles villes (ciblant la nouvelle ville créée ou une mise à jour incrémentale du vivier).
5. Les projets aériens déjà calculés en portefeuille, ainsi que les opérations sur les lignes existantes (renfort de flotte V161/V284, maintenance des aéroports existants, renouvellement V252) continuent de s'exécuter normalement sans perturbation.

### Critères de succès chiffrés
- **Opcodes épargnés** : réduction mesurable de **9 à 15 M opcodes/an** sur les cartes 256² et 1024² après saturation du réseau aérien (vers 1973-1975), où le poste `air.sites` et les passes « zéro candidat » consomment actuellement 25 % à 45 % du CPU pour 0 nouveau projet (cf. audit PCAL-03, `docs/pcal03_inventaire_20261021.md`).
- **Passes de recherche** : 0 passe de scan de villes/sites après saturation, tant qu'aucun événement `ET_TOWN_FOUNDED` ne survient.
- **Réactivité** : lors de la création d'une nouvelle ville (`ET_TOWN_FOUNDED`), réveil en 1 seul cycle et traitement de la nouvelle ville sans boucle ni famine.
- **Règle d'adoption** : Règle opcodes (§4 AGENTS.md) : gain d'opcodes démontré sur le poste visé, puis porte 20×10 appariée saine sans érosion (`profit_year` delta IC95 non négatif, test des signes p >= 0,05, garde de valeur -5% respectée).

---

## 2. État du code existant (fichier:ligne vérifiés dans le worktree)

1. **Déclenchement du scan des villes et sites AIR** :
   - [`ai/OpexAI/air_planning.nut:511`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/air_planning.nut#L511) : `function OpexAirPlansFindSites(ctx, comboIndex, combo, airport, plane, resumingCombo)` : itère sur toutes les villes du catalogue pour tester les sites potentiels (`AIR_MAX_SITE_PROBES`).
   - [`ai/OpexAI/air_planning.nut:716`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/air_planning.nut#L716) : `function OpexAirPlansNewPairs(ctx, comboIndex, combo, airport, plane, minDist, resumingCombo)` : itère sur les paires de sites trouvés pour former de nouvelles liaisons.
   - [`ai/OpexAI/air_planning.nut:1825`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/air_planning.nut#L1825) : `function OpexAirPlansStepFindSites` : phase par étapes du générateur.
   - [`ai/OpexAI/air_planning.nut:1948`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/air_planning.nut#L1948) : `function OpexAirPlans(...)` : point d'entrée principal de la génération aérienne.

2. **Événement `ET_TOWN_FOUNDED`** :
   - [`ai/OpexAI/events.nut:18`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/events.nut#L18) : comptabilisation de `entry.town_founded++`.
   - [`ai/OpexAI/events.nut:357-358`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/events.nut#L357-L358) : `else if (eventType == AIEvent.ET_TOWN_FOUNDED) { this._onTownFounded(event); }`.
   - [`ai/OpexAI/event_handlers.nut:414-439`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/event_handlers.nut#L414-L439) : `function OpexAI::_onTownFounded(event)` :
     - ligne 418 : `this._markDirty("town_founded", ["towns"], ["rail", "road", "air", "water"], true, true, "town", probeEvt.GetTownID());`
     - ligne 433 : `if (this._catalog != null) this._catalog._refreshTowns();`

3. **Ordonnancement et boucle de portefeuille** :
   - [`ai/OpexAI/orchestrator.nut:187-205`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/orchestrator.nut#L187-L205) : reprise asynchrone des générateurs et réactivation des intentions.

---

## 3. Conception proposée

### 3.1 Mécanisme et réglage
- **Réglage** : `air_coverage_stop` dans `info.nut` (0 = ancien comportement avec scans cycliques récurrents ; 1 = mise en veille du vivier de villes après saturation jusqu'à `ET_TOWN_FOUNDED`).
- **Constante / Globale** : `AIR_COVERAGE_STOP <- 0;` dans `globals_pre.nut`.
- Lecture dans les deux blocs chargeurs de `settings.nut` :
  `AIR_COVERAGE_STOP = AIController.GetSetting("air_coverage_stop") == 1 ? 1 : 0;`

### 3.2 Machine à états du vivier de prospection AIR
- Ajouter dans `OpexAI` (dans `main.nut` et `air_planning.nut`) :
  - `_airTownSearchExhausted` (booléen, défaut `false`) : devient `true` lorsqu'un balayage complet des villes de `catalog.towns` ne trouve plus aucun nouveau site aéroportuaire ou aucune nouvelle liaison admissible.
  - `_airNewTownQueue` (tableau de town IDs, défaut `[]`) : empile les `townId` reçus via `_onTownFounded`.
- **Logique de court-circuit dans `OpexAirPlans`** :
  ```squirrel
  if (AIR_COVERAGE_STOP && this._airTownSearchExhausted && this._airNewTownQueue.len() == 0) {
    if (DECISION_LOG) OpexDecide("AIR_STOP", "status=sleeping reason=pool_exhausted");
    return []; // Ne lance aucun scan d'aéroports ni de sites
  }
  ```
- **Réveil sur événement** :
  Dans `event_handlers.nut::_onTownFounded(event)` :
  ```squirrel
  if (AIR_COVERAGE_STOP) {
    this._airNewTownQueue.append(townId);
    this._airTownSearchExhausted = false;
  }
  ```
  Lors de la prochaine passe, l'énumérateur AIR ne teste que la ou les villes présentes dans `_airNewTownQueue` contre les aéroports et hubs existants (`OpexAirPlansFindSites` ciblée sur `targetTownId`), évitant ainsi le scan combinatoire $O(N^2)$ sur toute la carte.

### 3.3 Sauvegarde et Rechargement (Save/Load)
- Ajouter `_airTownSearchExhausted` et `_airNewTownQueue` dans `persist.nut` (`Save` et `Load`).
- Lors de `Load`, si `_airTownSearchExhausted` n'est pas présent dans la sauvegarde (ancienne partie), initialiser à `false` pour déclencher une passe d'inventaire initiale sécurisée.

---

## 4. Pièges connus et historique

1. **Piège du faux positif de saturation précoce** :
   En tout début de partie (1970), le capital est limité par le prêt initial. Si la recherche est mise en veille parce qu'aucun aéroport n'est finançable immédiatement (cause budget), l'IA ne chercherait plus jamais de ville une fois riche !
   *Contre-mesure* : la saturation ne doit être prononcée QUE lorsque l'absence de site est **physique** ou **géographique** (toutes les villes ont déjà un aéroport, ou aucune ville restante n'a de terrain plat de dimensions 3×4 ou 4×4 constructible), et **non** pour cause de trésorerie momentanée.
2. **Piège V142/V143 (banc négatif du 12/10, -252 k£/an)** :
   Mélanger le rafraîchissement d'autres modes (rail/route) au milieu d'une coroutine AIR en cours désynchronise le catalogue (`docs/journaux/journal_2026-10-30_transfert_taches.md` ligne 961).
   *Contre-mesure* : la mise en veille ne touche que l'étape de génération des nouvelles paires AIR ; elle ne modifie aucun autre mode.
3. **Piège du nivellement en test-mode (OpenTTD 15.3)** :
   `LevelTiles` en mode test renvoie vrai dès qu'un coin bouge. Les sites testés doivent utiliser le validateur existant éprouvé `air_site_ranked`.

---

## 5. Plan de test

1. **Tests unitaires et de contrat (hôte)** :
   - `sweeps/test_air_coverage_stop.py` :
     - Vérifier la déclaration du réglage, défaut 0, lecture dans les deux chargeurs.
     - Simuler un épuisement du vivier : vérifier que `OpexAirPlans` retourne immédiatement sans consommer d'opcodes.
     - Simuler un événement `ET_TOWN_FOUNDED` : vérifier le réveil et la restriction du scan à la nouvelle ville.
     - Test de roundtrip Save/Load sur l'état `_airTownSearchExhausted`.
2. **Smoke test moteur** :
   - 1 graine × 1 an en mode duel contre AAAHogEx avec `air_coverage_stop=1`.
   - Vérifier 0 crash, présence du journal `AIR_STOP` et conservation du réseau aérien standard.
3. **Campagne de qualification** :
   - Selon règle opcodes §4 AGENTS.md :
     1. Mesure du profil d'opcodes sur graine 42 à 5 ans : gain attendu > 5 M opcodes/an sur `loop.c121_catalog_resume` / `air.sites`.
     2. Porte B 20×10 appariée : non-érosion du `profit_year`, ratio de valeur >= 95%.

---

## 6. Estimation de difficulté et effet attendu

- **Difficulté** : Moyenne (nécessite une isolation propre du flag d'épuisement physique distinct du cash, et persistance Save/Load).
- **Effet attendu** :
  - **Opcodes** : gain massif de **10 à 25 M opcodes/an** à partir de 1974 (libère le budget CPU pour les autres chantiers comme le rail et la sélection).
  - **Économie** : neutre à court terme (+0 k£), mais permet de supprimer les freezes CPU et de financer les projets ferroviaires plus rapidement.
- **Source** : Audit PCAL-03 (`docs/pcal03_inventaire_20261021.md`) et diagnostic EB-7 (`docs/journaux/journal_2026-10-30_transfert_taches.md` ligne 55).
