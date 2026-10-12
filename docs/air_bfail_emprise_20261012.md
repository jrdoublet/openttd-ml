# Autopsie : Échecs de pose d'aéroports « error=2 invalid airport footprint » (graine 5678, 1971) et « error=263 »

**Dépôt :** `/home/deploy/projects/openttd-ml` (lecture seule, code figé au commit `9144dc5`).  
**Corpus analysé :** Journaux bruts du 5×6 frais `results/astar_pending_expo_5x6_20261011_engine/reference_seed{42,100,999,1234,5678}_r0.log`.  
**Auteur :** Antigravity (agy). Date : 12/10/2026.

---

## 1. Analyse détaillée des 32 échecs « error=2 » de la graine 5678

### 1.1 Inventaire complet des 32 échecs
Les 32 échecs `error=2 error_text=invalid airport footprint` de la graine 5678 se répartissent en :
- **1 en 1970** (11 août 1970, `BFAIL`, `newpair`)
- **29 en 1971** :
  - **4 `AFAIL`** en février–avril 1971 (`newpair`, où la ville 11 est `src` et échoue immédiatement sans rien dépenser)
  - **25 `BFAIL`** d'avril à juillet 1971 (tous `hubsite`, reliant un hub existant à la ville 11)
- **1 en 1972** (18 mars 1972, `BFAIL`, `hubsite`)
- **1 en 1973** (22 juillet 1973, `BFAIL`, `hubsite`)

**Constat majeur :** Les **32 échecs** concernent **la même ville commerciale (Town ID 11, tuile centre 46323)** et **la même ancre d'aéroport (tuile 44793)** pour l'aéroport 6×6 (`AT_LARGE`, type=1).

| Date | Ligne log | Rang | Issue | Arm | Ville A (tuile) | Ville B (tuile) | Ancre B | Statut A avant pose |
|---|---:|---:|:---:|:---:|---|---|:---:|---|
| **1970-08-11** | 3578 | 0 | `BFAIL` | `newpair` | Town 5 (31600) | Town 11 (46323) | 44793 | Neuf (posé et payé -> **orphelin**) |
| **1971-02-23** | 6373 | 0 | `AFAIL` | `newpair` | Town 11 (46323) | Town 42 (28242) | — | Ancre A = 44793 (échec immédiat, 0 £) |
| **1971-02-24** | 6375 | 1 | `AFAIL` | `newpair` | Town 11 (46323) | Town 15 (38422) | — | Ancre A = 44793 (échec immédiat, 0 £) |
| **1971-04-04** | 7309 | 0 | `AFAIL` | `newpair` | Town 11 (46323) | Town 28 (23835) | — | Ancre A = 44793 (échec immédiat, 0 £) |
| **1971-04-04** | 7322 | 1 | `AFAIL` | `newpair` | Town 11 (46323) | Town 2 (24953) | — | Ancre A = 44793 (échec immédiat, 0 £) |
| **1971-04-09** | 7397 | 0 | `BFAIL` | `hubsite` | Town 41 (19002) | Town 11 (46323) | 44793 | Hub existant (`reuseA=true`, 0 £) |
| **1971-05-19** | 8116 | 0 | `BFAIL` | `hubsite` | Town 29 (11047) | Town 11 (46323) | 44793 | Hub existant (`reuseA=true`, 0 £) |
| **1971-05-26** | 8268 | 0 | `BFAIL` | `hubsite` | Town 0 (57904) | Town 11 (46323) | 44793 | Hub existant (`reuseA=true`, 0 £) |
| **1971-05-31** | 8370 | 0 | `BFAIL` | `hubsite` | Town 7 (13619) | Town 11 (46323) | 44793 | Hub existant (`reuseA=true`, 0 £) |
| **1971-07-05** | 9407 | 0 | `BFAIL` | `hubsite` | Town 21 (25913) | Town 11 (46323) | 44793 | Hub existant (`reuseA=true`, 0 £) |
| **1971-07-05** | 9412 | 1 | `BFAIL` | `hubsite` | Town 43 (35143) | Town 11 (46323) | 44793 | Hub existant (`reuseA=true`, 0 £) |
| **1971-07-05** | 9414 | 2 | `BFAIL` | `hubsite` | Town 27 (6476) | Town 11 (46323) | 44793 | Hub existant (`reuseA=true`, 0 £) |
| **1971-07-05** | 9416 | 3 | `BFAIL` | `hubsite` | Town 20 (59710) | Town 11 (46323) | 44793 | Hub existant (`reuseA=true`, 0 £) |
| **1971-07-05** | 9418 | 4 | `BFAIL` | `hubsite` | Town 35 (49434) | Town 11 (46323) | 44793 | Hub existant (`reuseA=true`, 0 £) |
| **1971-07-05** | 9421 | 5 | `BFAIL` | `hubsite` | Town 1 (16545) | Town 11 (46323) | 44793 | Hub existant (`reuseA=true`, 0 £) |
| **1971-07-06** | 9423 | 6 | `BFAIL` | `hubsite` | Town 14 (57113) | Town 11 (46323) | 44793 | Hub existant (`reuseA=true`, 0 £) |
| **1971-07-06** | 9425 | 7 | `BFAIL` | `hubsite` | Town 8 (7837) | Town 11 (46323) | 44793 | Hub existant (`reuseA=true`, 0 £) |
| **1971-07-06** | 9427 | 8 | `BFAIL` | `hubsite` | Town 18 (61457) | Town 11 (46323) | 44793 | Hub existant (`reuseA=true`, 0 £) |
| **1971-07-06** | 9429 | 9 | `BFAIL` | `hubsite` | Town 10 (29582) | Town 11 (46323) | 44793 | Hub existant (`reuseA=true`, 0 £) |
| **1971-07-06** | 9431 | 10 | `BFAIL` | `hubsite` | Town 34 (56953) | Town 11 (46323) | 44793 | Hub existant (`reuseA=true`, 0 £) |
| **1971-07-06** | 9433 | 11 | `BFAIL` | `hubsite` | Town 24 (51546) | Town 11 (46323) | 44793 | Hub existant (`reuseA=true`, 0 £) |
| **1971-07-10** | 9529 | 0 | `BFAIL` | `hubsite` | Town 39 (44386) | Town 11 (46323) | 44793 | Hub existant (`reuseA=true`, 0 £) |
| **1971-07-11** | 9531 | 1 | `BFAIL` | `hubsite` | Town 32 (22221) | Town 11 (46323) | 44793 | Hub existant (`reuseA=true`, 0 £) |
| **1971-07-11** | 9536 | 2 | `BFAIL` | `hubsite` | Town 23 (23271) | Town 11 (46323) | 44793 | Hub existant (`reuseA=true`, 0 £) |
| **1971-07-12** | 9567 | 0 | `BFAIL` | `hubsite` | Town 44 (4715) | Town 11 (46323) | 44793 | Hub existant (`reuseA=true`, 0 £) |
| **1971-07-12** | 9569 | 1 | `BFAIL` | `hubsite` | Town 4 (57419) | Town 11 (46323) | 44793 | Hub existant (`reuseA=true`, 0 £) |
| **1971-07-14** | 9595 | 0 | `BFAIL` | `hubsite` | Town 16 (38262) | Town 11 (46323) | 44793 | Hub existant (`reuseA=true`, 0 £) |
| **1971-07-15** | 9624 | 0 | `BFAIL` | `hubsite` | Town 6 (38207) | Town 11 (46323) | 44793 | Hub existant (`reuseA=true`, 0 £) |
| **1971-07-15** | 9626 | 1 | `BFAIL` | `hubsite` | Town 30 (28341) | Town 11 (46323) | 44793 | Hub existant (`reuseA=true`, 0 £) |
| **1971-07-16** | 9650 | 0 | `BFAIL` | `hubsite` | Town 9 (36956) | Town 11 (46323) | 44793 | Hub existant (`reuseA=true`, 0 £) |
| **1972-03-18** | 15840 | 0 | `BFAIL` | `hubsite` | Town 5 (31600) | Town 11 (46323) | 44793 | Hub existant (`reuseA=true`, 0 £) |
| **1973-07-22** | 23474 | 0 | `BFAIL` | `hubsite` | Town 25 (20146) | Town 11 (46323) | 44793 | Hub existant (`reuseA=true`, 0 £) |

### 1.2 Date de validation vs date de pose
- **Date d'élection / cotation initiale :** **1970-01-05** (`reference_seed5678_r0.log:189`) :  
  `C96_SITE town=11 pop=1047 type=1 first=44793 first_score=15 best=44793 best_score=15 gain=0 first_dist=7 best_dist=7 valid=3 first_ring=6 best_ring=6 probes=3`.
- **Dates de pose :** Les chantiers sont tentés de **7 mois plus tard** (11/08/1970) jusqu'à **3 ans et demi plus tard** (22/07/1973).

### 1.3 Ce qui rend l'emprise invalide : une pure anomalie géométrique de bord de carte
Contrairement à l'hypothèse d'expansion urbaine (maison ou route apparue entre-temps) :
1. **Le terrain est parfaitement vierge et plat :**  
   L'autopsie géométrique sous sonde (`docs/air_bfail_precheck_shadow_20261009.md §4`) a mesuré sur cette ancre exacte 44793 :  
   `mismatch = 0`, `slopes = 0`, terrain 100 % plat au niveau Z=2. Aucune maison ni route n'est apparue.
2. **Coordonnées de l'ancre et de l'emprise :**  
   Sur une carte 256×256 (`map_x = 256, map_y = 256`), l'ancre 44793 correspond à :  
   `ax = 44793 % 256 = 249`, `ay = 44793 // 256 = 174`.  
   L'aéroport 6×6 occupe en X les tuiles `249, 250, 251, 252, 253, 254`.  
   Ces 36 tuiles sont **strictement à l'intérieur de la carte** (`ax + w - 1 = 254 <= 255`).
3. **Le coin de terrassement dans `OpexAirFootprintEnd` :**  
   `OpexAirFootprintEnd` (`air_sites.nut:39`) calcule le coin terminal de terrassement :  
   `end = anchor + AIMap.GetTileIndex(airport.width, airport.height) = 44793 + (6×256 + 6) = 46335`.  
   Les coordonnées de `end` sont `end_x = 255`, `end_y = 180`.  
   Dans OpenTTD, la colonne `x = 255` (bordure de carte) est **inconstructible et invalide** (`AIMap.IsValidTile(46335) == false`).
4. **L'inversion de garde dans `OpexAirLevelFootprint` :**  
   `OpexAirLevelFootprint` (`air_sites.nut:133-139`) teste :
   ```squirrel
   local end = OpexAirFootprintEnd(anchor, airport);
   if (!AIMap.IsValidTile(end)) {
     return { ok = false, error = AIError.ERR_PRECONDITION_FAILED,
              errorText = "invalid airport footprint" };
   }
   if (OpexAirFootprintIsFlat(anchor, airport)) return { ok = true, ... };
   ```
   **Le code teste si le coin `end` est valide AVANT de vérifier si le terrain est déjà plat !**  
   Puisque le terrain était déjà 100 % plat, aucun terrassement (`LevelTiles`) n'était nécessaire. Mais la vérification prématurée de `end` a immédiatement rejeté le chantier avec `error=2` (`ERR_PRECONDITION_FAILED`).

---

## 2. Aéroports A orphelins résultants et leur devenir

Sur les 32 échecs `error=2` de la graine 5678 :
- **4 échecs sont des `AFAIL`** (février–avril 1971) : l'aéroport A était prévu sur la ville 11 (ancre 44793) ; il échoue immédiatement au début du chantier avant toute dépense. **0 orphelin.**
- **27 échecs sont des `BFAIL` sur l'arm `hubsite`** (avril 1971 à juillet 1973) : l'extrémité A était un **hub existant déjà en service** (`reuseA = true`). Aucun aéroport A n'a été construit ni payé lors de ces tentatives (`air_construction.nut:355` court-circuite la pose de A ; `air_construction.nut:468` ne roll back pas un hub réutilisé). **0 orphelin.**
- **Exactement 1 seul aéroport A orphelin** résulte de ces 32 échecs :  
  Le premier échec du **11 août 1970** (`src=31600 dst=46323`), arm `newpair`.  
  L'aéroport A a été construit à Town 5 (tuile 31600), coûtant ~28,4 k£ (catalogue 16,2 k£ + terrassement). Puis B a échoué à Town 11.

### Devenir de cet aéroport A orphelin (Town 5, tuile 31600)
- Avec `economy.infrastructure_maintenance = 0`, l'aéroport orphelin est conservé sans frais récurrents.
- Dès avril 1971 (`AIR_PLAN_SETS` ligne 7371), Town 5 (`5:31600`) apparaît dans le vivier des **hubs disponibles**.
- **Il est rentabilisé et réutilisé 3 ans plus tard :**
  1. **1973-08-20 (`reference_seed5678_r0.log:23652`) :** ligne 56 construite (`AIR_BUILD arm=hubsite line=56 src=31600 dst=59038 dist=133 profit=42260 cost=57219 planes=1 engine=223`).
  2. **1974-11-22 (`reference_seed5678_r0.log:24810`) :** ligne 61 construite (`AIR_BUILD arm=hubhub line=61 src=31600 dst=20146 dist=86 profit=10726 cost=38964 planes=1 engine=223`).
- L'aéroport A n'a donc pas été perdu : il est devenu un hub opérationnel, mais ses capitaux ont été immobilisés pendant 36 mois sans générer de recettes.

---

## 3. Chemin de code de validation et défaillance de la mémoire d'échec

### 3.1 Pourquoi la validation ne voit pas l'invalidité avant la pose
Trois niveaux de validation successifs testent le site avant la pose physique :
1. **Élection du site (`OpexAirFindSiteCatchmentListed`, `air_sites.nut:505`) :**  
   Appelle `AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW)` en `AITestMode()`.  
   Le moteur OpenTTD répond **`true`** car les 36 tuiles de l'emprise réelle sont plates et sur la carte. `LevelTiles` n'étant pas appelé, le coin `end` n'est jamais évalué.
2. **Revalidation en portefeuille (`OpexAirSiteStillBuildable`, `air_sites.nut:890`) :**  
   Rejoue également `AIAirport.BuildAirport(...)` en `AITestMode()`, qui répond encore **`true`**.
3. **Préflight de chantier (`OpexAirPreflightEndpoint`, `air_construction.nut:68`) :**  
   Appelle `OpexAirProbeSite`, qui teste `BuildAirport` en `AITestMode()`, répondant `err = 0` (succès).
4. **Pose physique réelle (`OpexBuildAirRoute`, `air_construction.nut:422`) :**  
   Appelle **`OpexAirLevelFootprint(plan.siteB.anchor, ...)`** avant de poser.  
   C'est là, et **uniquement là**, que la ligne 133 évalue `!AIMap.IsValidTile(end)` et échoue !

### 3.2 Pourquoi la mémoire d'échec n'empêche pas de retenter 32 fois la même tuile
1. **Invalidation de cache inefficace (`air_coverage.nut:94`) :**  
   Lors de l'échec, `OpexAirInvalidateCachedSite` exécute `delete AIR_SITE_CACHE[key]`. Cela supprime l'entrée en cache, mais **n'enregistre aucune interdiction**. Au scan suivant, `OpexAirFindSite` refait la recherche, retrouve l'ancre 44793 (la plus rentable en catchment) et la remet en cache !
2. **`OPEX_AIR_SITE_PAD` est désactivé au défaut (`globals_post.nut:114`, `settings.nut:665`) :**  
   `OPEX_AIR_SITE_PAD = false`. Donc dans `task_air.nut:17`, la mémorisation d'abandon de site est court-circuitée. De plus, `_padAirFailedSites` ne filtre que les erreurs de terrain 263/etc., ignorant `error=2` (`ERR_PRECONDITION_FAILED`).
3. **Seule la paire OD est abandonnée (`task_air.nut:854`) :**  
   `_markPairAbandoned` enregistre `air|townA|townB`. La ville 11 n'est bloquée qu'envers l'autre ville testée.  
   Dès lors, toutes les autres villes du réseau (Towns 0, 1, 4, 6, 7, 8, 9, 10, 14, 16, 18, 20, 21, 23, 24, 27, 30, 32, 34, 35, 39, 41, 43, 44) génèrent à leur tour un projet vers Town 11, reprennent l'ancre 44793 et échouent tour à tour en juillet 1971 (12 échecs en 24h les 5–6 juillet 1971 !).
4. **Réexpiration du cooldown (365 jours) :**  
   Le projet `31600 <-> 46323` échoué le 11/08/1970 est retenté le 18/03/1972 après expiration du délai d'abandon de 365 jours, échouant exactement de la même manière.

---

## 4. Analyse comparative : « error=263 » (footprint non plat) toutes graines

Sur les 5 graines du banc 5×6 frais, **20 échecs** sont attribués à `error=263 error_text=airport footprint remains non-flat` (4 `AFAIL`, 16 `BFAIL`) :
- Graine 42 : 4 (1 AFAIL, 3 BFAIL sur la même ville 28041 en 1971, 1972, 1973)
- Graine 100 : 4 (1 AFAIL, 3 BFAIL dont 2 sur la ville 15598 en 1972 et 1973)
- Graine 999 : 4 (1 AFAIL, 3 BFAIL)
- Graine 1234 : 5 (1 AFAIL, 4 BFAIL)
- Graine 5678 : 3 (1 AFAIL, 2 BFAIL sur la ville 20146 en janvier et avril 1970)

### Cause mécanique de « error=263 »
1. **L'erreur 263 est synthétique :** Elle est générée par le contrôle final d'OpexAI (`air_sites.nut:169`) :
   ```squirrel
   if (!OpexAirFootprintIsFlat(anchor, airport)) {
     return { ok = false, error = AIError.ERR_FLAT_LAND_REQUIRED,
              errorText = "airport footprint remains non-flat" };
   }
   ```
2. **Le piège d'API de `LevelTiles` en `AITestMode` :**  
   À l'élection (`OpexAirCanLevelFootprint`), `AITile.LevelTiles(anchor, end)` en `AITestMode` retourne `true` (la commande est autorisée).  
   Mais en exécution réelle (`AIExecMode`), `LevelTiles` s'arrête en cours de route dès qu'un dénivelé extérieur ou une pente maximale empêche d'aplanir les tuiles de bordure (pentes résiduelles sur les rangées 0 ou 5).
3. **Même absence de mémoire de site :**  
   Tout comme pour l'erreur 2, `OPEX_AIR_SITE_PAD=false` empêche de mémoriser l'échec de l'ancre. Les mêmes sites non nivelables sont retentés à plusieurs mois ou années d'intervalle (ex: ville 28041 sur graine 42 tentée 3 fois : 1971-05-08, 1972-11-19, 1973-07-17).

---

## 5. Synthèse causale, correctifs minimaux envisageables et validation

### 5.1 Synthèse causale
1. **Pour `error=2` :** Faux négatif purement interne créé par l'évaluation prématurée de `!AIMap.IsValidTile(end)` sur un terrain déjà plat en bord de carte (colonne 249 à 254).
2. **Pour `error=263` :** Limite de l'API `LevelTiles` d'OpenTTD qui valide en test des terrassements partiels non achevables en mode réel.
3. **Pour la répétition (32 et 20 fois) :** Absence totale de mémoire persistante sur les ancres d'aéroports ayant physiquement échoué (`OPEX_AIR_SITE_PAD=false`).

### 5.2 Correctifs minimaux envisageables (sans modification du code)

| Piste de correctif | Mécanisme | Ce qu'il résout | Limites / Risques | Coût en opcodes estimé |
|---|---|---|---|---|
| **Piste 1 : Inversion du garde de platitude dans `OpexAirLevelFootprint`** | Inverser l'ordre des lignes 133 et 139 dans `air_sites.nut` : tester `OpexAirFootprintIsFlat(anchor, airport)` **avant** `!AIMap.IsValidTile(end)`. | Résout **100 % des 32 erreurs `error=2`**. L'aéroport sur 44793 est directement posé sans terrassement. | Ne résout pas `error=263`. Si `BuildAirport` échouait malgré tout, l'erreur réelle du moteur serait enfin visible. | **0 opcode additionnel.** |
| **Piste 2 : Mémoire d'ancre en échec (`AIR_FAILED_ANCHORS`)** | Enregistrer l'ancre dans une table de quarantaine lors de tout `AFAIL`/`BFAIL` (`error=2`, `263`, `258`), ignorée par `FindSite` pendant N années. | Évite **31 récidives sur 32 pour `error=2`** et **les récidives multiples de `error=263`**. Libère les projets pour d'autres villes. | Le premier échec de chaque site survient quand même. Nécessite une table en mémoire (ou persistance Save/Load si multi-sessions). | **Négligeable** (< 50 opcodes par scan, test d'appartenance `in`). |
| **Piste 3 : Poser B avant A (`B-first`) sur `newpair`** | Tenter le terrassement et la pose de B avant de payer A quand A et B sont tous deux neufs. | Évite d'avoir un aéroport A orphelin lors des `BFAIL` sur `newpair`. | Ne prévient pas l'échec lui-même ; sans effet sur les 27 `hubsite` où A est déjà construit. Déplace l'orphelin vers B si A échoue ensuite. | **0 opcode.** |
| **Piste 4 : Revalidation `OpexAirLevelFootprint` en préflight** | Vérifier `!OpexAirFootprintIsFlat && !IsValidTile(end)` dans `OpexAirPreflightEndpoint`. | Prévient les `BFAIL` `error=2` avant de poser A sur `newpair`. | Ne permet pas de construire l'aéroport à Town 11 ; n'évite pas les 27 rejets `hubsite`. | **Négligeable** (~10 opcodes). |

### 5.3 Recommandation d'intervention et protocole de validation
- **Recommandation technique minimale :**  
  Combiner la **Piste 1** (inversion de garde `already_flat` avant `invalid_end`, correction géométrique pure) et la **Piste 2** (mise en quarantaine de l'ancre en cas d'échec réel au chantier, correctness).
- **Protocole de validation proportionné (selon AGENTS.md §4) :**
  1. Contrats unitaires ciblés (`sweeps/test_r18_air_level_failure.py` adapté).
  2. Smoke apparié **seed 5678 × 1 an** pour vérifier que la ville 11 est bien posée ou mise en quarantaine proprement sans crash ni divergence non désirée.
  3. Porte A **40×3** (`gain_short`), puis Porte B **20×10** (`non_erosion`) si une modification comportementale globale est proposée.

---

## Note de relecture (Claude, 12/10)

Vérifié dans `air_sites.nut` : `OpexAirLevelFootprint` teste `AIMap.IsValidTile(end)`
(coin de terrassement à +(w,h)) **avant** `OpexAirFootprintIsFlat`. Un site déjà plat
collé au bord est donc refusé à tort. Piste 1 (inverser les deux gardes, hors
FindSite/catalogue) confiée à agy sous V145, réglage `v145_air_flat_edge_guard`
défaut 0. La piste 2 (quarantaine d'ancres) touche FindSite : laissée au chantier
catalogue de l'utilisateur.
