# Revue de code — road1y_mail_p2p (Courrier point à point autonome)

**Date :** 9 novembre 2026  
**Branche :** `road1y-night`  
**Auteur :** Antigravity  
**Statut :** Validé et conforme  

---

## 1. Contexte et Objectif

- **Objectif :** Capter le vivier économique des lignes de courrier point à point interurbaines exploité massivement par AAAHogEx (36 % de ses ouvertures 1972, ~195 k£/an de profit courrier à 3 ans), sans subir les échecs historiques de `mail_net` (−38 k£/an), `mail_min` (−45 k£/an) et `mail_pick` (−27 k£/an).
- **Principe :** Déploiement de lignes de fourgons postaux autonomes (`kind == "mail_p2p"`) sur des paires de villes distantes de 24 à 128 tuiles, n'ayant aucune desserte bus ou courrier existante, sans investissement de voirie lourde (`missing <= 14` tuiles), exclusivement à partir de 1971 (`year > 1970`), avec 2 fourgons initiaux et refleeting progressif.
- **Réglage :** `road1y_mail_p2p` (plage 0..20, défaut 0 à toutes les difficultés, forcé à 0 hors route seule).

---

## 2. Décomposition du diff et vérification ligne à ligne

### A. Déclaration et configuration
- **`ai/OpexAI/globals_pre.nut` :**
  - Ajout de `ROAD1Y_MAIL_P2P <- 0;` et `ROAD1Y_MAIL_P2P_TRY_YM <- -1;`.
  - Pas d'identifiant réservé Squirrel.
- **`ai/OpexAI/info.nut` :**
  - `AddSetting` avec `name = "road1y_mail_p2p"`, `min_value = 0`, `max_value = 20`, 4 difficultés à `0`, `flags = 0`.
  - Plafond d'`AddSetting` ajusté à 72 dans `sweeps/test_v251_inventory.py`.
- **`ai/OpexAI/settings.nut` :**
  - Lecture dans `OpexLoadSettings()` avec borne `[0, 20]` et forçage `if (!road1yRoadOnly) ROAD1Y_MAIL_P2P = 0;`.
  - Inscription dans `test_road1y_multimodal_gate.py` (`ROAD1Y_OFF`, `SETTING_TO_GLOBAL`, `LOAD_SETTINGS_KEYS`).
- **`sweeps/road100_off_projection.py`, `sweeps/rail_open_legacy.py`, `sweeps/rail_sibling_legacy.py` :**
  - SHAs intermédiaires de stripping B2 et rail mis à jour pour préserver l'exactitude des projections historiques.

### B. Moteur métier (`ai/OpexAI/bus_districts.nut`)
- **`OpexRoad1yMailP2PLog(fields)` :**
  - Wrapper conditionnel `if (DECISION_LOG) OpexDecide("ROAD1Y_MAIL_P2P", fields);`. Aucune surcharge d'opcodes si le log de décision est désactivé.
- **`OpexRoad1yFindMailP2PSite(ai, catalog, townId, mailCargo)` :**
  - Recherche d'un arrêt DT camion dans la ville cible sans empiéter sur nos arrêts existants (`OpexRoad1yOurTruckTiles`), avec acceptation $\ge 8$ et production $> 0$.
  - Préflight en `AITestMode()` via `AIRoad.BuildDriveThroughRoadStation`.
- **`OpexRoad1yMailP2PActivePairs(ai)` :**
  - Indexe toutes les paires de villes déjà reliées par une ligne routière (pax, mail_pax, mail_p2p). Interdit formellement toute cannibalisation ou concurrence interne avec les bus prioritaires.
- **`OpexRoad1yBuildMailP2P(ai, catalog, ta, tb, siteA, siteB, trace, depot, cashReserve)` :**
  - Vérification de réserve de caisse (25 000 £ + infra + véhicules).
  - Construction des deux arrêts DT, raccordement routier si nécessaire, construction/réutilisation du dépôt.
  - Achat et refit du premier véhicule, ordres `OF_NON_STOP_INTERMEDIATE`, clonage immédiat du 2e véhicule si slot disponible.
  - Nettoyage / rollback immédiat en cas d'échec intermédiaire.
- **`OpexRoad1yMailP2PStep(ai, year)` :**
  - Garde stricte `if (year <= 1970) return;` : aucun capex courrier en 1970, préservant 100 % du capital de démarrage pour les bus.
  - Garde de réglage `if (ROAD1Y_MAIL_P2P <= 0) return;` : neutralité absolue au défaut 0.
  - Débounce mensuel `ROAD1Y_MAIL_P2P_TRY_YM == ym`.
  - Budget d'opcodes plafonné : au maximum 4 paires testées par mois (`attempts > 4`).
  - Garde anti-surcoût voirie `missing <= 14` : interdiction formelle des autoroutes dédiées à 20 k£ ; seules les paires sur voirie municipale existante ou avec raccord très court sont retenues.
- **`OpexRoad1yRefleetMailP2PLine(ai, line, year)` :**
  - Refleeting des lignes `mail_p2p` en service lorsque le stock en attente dépasse la capacité des véhicules, jusqu'au plafond `ROAD1Y_MAIL_P2P` (ou 4 par défaut), sous réserve de 25 000 £ de caisse.

### C. Câblage de refleet (`ai/OpexAI/bus_districts_overrides.nut` et fixture)
- Prise en charge des lignes `mail_p2p` dans `OpexRoad1yRefleetSaved` pour appeler `OpexRoad1yRefleetMailP2PLine`.
- Appel de `OpexRoad1yMailP2PStep(this, year)` à la fin de la passe de refleet routier.
- Fixture `sweeps/fixtures/road100_bus_districts_overrides.json` synchronisée pour garantir la conformité des 236 tests de régression B2.

---

## 3. Conformité aux règles et invariants

- **Mots réservés Squirrel :** Aucun mot interdit (`clone`, `base`, `parent`, `static`, etc.) utilisé comme identifiant.
- **Closures & lambdas :** Aucune closure capturant des variables locales englobantes. Aucune fonction anonyme.
- **Méthodes tableaux :** Aucun appel à `.find(`.
- **Inertie à 0 :** À `road1y_mail_p2p = 0`, aucune fonction de création ni de refleet p2p n'est exécutée ; le chemin d'exécution est strictement inchangé par rapport à `origin/master`.
- **Sauvegarde / Persistance :** Le champ `kind = "mail_p2p"` est automatiquement préservé par `persist.nut`. Aucun champ spéculatif non persistant.

---

## 4. Résultats des tests unitaires hôte

- `sweeps/test_road1y_mail_p2p.py` : **8/8 OK**
- `sweeps/test_road1y*.py` : **96/96 OK**
- `sweeps/test_road100*.py` : **236/236 OK** (3 skipped historiques)
- `sweeps/test_v251*.py` : **7/7 OK**
- `sweeps/test_v26*.py` : **107/107 OK** (2 expected failures historiques)
- `git diff --check` : **0 erreur** (aucun espace de fin, aucun conflit)
