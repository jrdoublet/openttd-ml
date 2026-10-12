# Audit des reconstructions complètes du catalogue et du portefeuille (OpexAI)

**Date d'audit :** 12 octobre 2026  
**Dépôt :** `wt-regen-audit` (base `master` OpenTTD-ML, IA OpexAI dans `ai/OpexAI/`)  
**Profil par défaut audité :**
- `c121_air_economics = 1` ([info.nut:361](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/info.nut#L361), [settings.nut:361](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/settings.nut#L361))
- `c121_catalog_incremental = 1` ([info.nut:370](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/info.nut#L370), [settings.nut:370](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/settings.nut#L370))
- `c76_regen_targeted = 1` ([info.nut:1604-1609](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/info.nut#L1604-L1609), [settings.nut:587](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/settings.nut#L587))
- `c80_mode_regen = 1` ([info.nut:1644-1649](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/info.nut#L1644-L1649), [settings.nut:604](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/settings.nut#L604))
- `air0310_incremental_publish = 1` ([info.nut:1832-1839](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/info.nut#L1832-L1839), [settings.nut:615](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/settings.nut#L615))
- `v147_air_catalog_tasks = 1` ([info.nut:1912-1919](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/info.nut#L1912-L1919), [settings.nut:593](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/settings.nut#L593))
- `air_efficiency_reselect = 0` ([info.nut:1809](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/info.nut#L1809), [settings.nut:169](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/settings.nut#L169))
- `c76_lean_invalidation = 0` ([info.nut:1612-1617](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/info.nut#L1612-L1617), [settings.nut:602](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/settings.nut#L602))
- `c76_freight_rotation = 0` ([info.nut:1620-1625](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/info.nut#L1620-L1625), [settings.nut:603](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/settings.nut#L603))
- `staged_bootstrap = 1` ([settings.nut:78](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/settings.nut#L78))
- `c121_flat_bootstrap = 0` ([settings.nut:376-378](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/settings.nut#L376-L378))

---

## 1. Tableau exhaustif des chemins vers une reconstruction complète

Une « reconstruction complète » désigne soit la reconstruction synchrone de tous les projets de tous les modes via `this._rebuildProjects(...)` ([task_projects.nut:2171-2291](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/task_projects.nut#L2171-L2291)), soit la reconstruction découpée en tranches C78/V147 du catalogue aérien (`OpexC78StartCatalogAirRebuild` dans [scheduler_tasks.nut:15-74](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/scheduler_tasks.nut#L15-L74)) qui se termine à l'application par un appel complet à `this._rebuildProjects(fleetPlan, airOverride)` ([scheduler_tasks.nut:232](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/scheduler_tasks.nut#L232)).

| Chemin / Déclencheur | Condition exacte dans le code | Motif journalisé (`c76Reason` / `reason`) | Fréquence attendue au défaut | Voie incrémentale existante pour cas voisin |
|---|---|---|---|---|
| **1. Bootstrap initial** (génération initiale du portefeuille) | [scheduler_tasks.nut:484-485](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/scheduler_tasks.nut#L484-L485) : `if (this._projects == null) c76NeedFullRegen = true;` | `c76Reason = "bootstrap"` ([scheduler_tasks.nut:499](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/scheduler_tasks.nut#L499)) ou `"initial"` | Exactement 1 fois en début de partie (année 0) | Non applicable (initialisation à froid requise). |
| **2. Post-construction en bootstrap étagé** (`STAGED_BOOTSTRAP=1`) | [task_projects.nut:2068-2077](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/task_projects.nut#L2068-L2077) : `if (STAGED_BOOTSTRAP && this._generationStage < OPEX_STAGE_COMPLETE)` après succès ou abandon de construction | `reason = "staged"` ([task_projects.nut:2076](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/task_projects.nut#L2076)) | Après chaque ligne construite pendant les stades 0, 1 et 2 (jusqu'à `OPEX_STAGE_COMPLETE`, ~3 à 6 premières lignes) | Pour le stade complet, la voie incrémentale existe (`_tryIncrementalAfterBuild`, [task_projects.nut:2088-2108](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/task_projects.nut#L2088-L2108)), mais elle est court-circuitée en bootstrap étagé. |
| **3. Filet de sécurité périodique annuel** | [scheduler_tasks.nut:408](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/scheduler_tasks.nut#L408) : `c76PeriodicDue = (this._c76LastRegenQuarter < 0 \|\| c76CurQuarter > this._c76LastRegenQuarter);` avec `c76CurQuarter = year` ([L407](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/scheduler_tasks.nut#L407)) ; déclenché dans `_dispatchCatalog` car [L488](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/scheduler_tasks.nut#L488) interdit le mode regen si `c76PeriodicDue == true` | `c76Reason = "periodic"` ([scheduler_tasks.nut:505](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/scheduler_tasks.nut#L505)) | Exactement **1 fois par an**, au 1er dispatch catalogue de chaque nouvelle année civile | C80 mode regen existe pour rafraîchir les modes modifiés, mais `c76PeriodicDue` force un full annuel sans tenir compte de C80. |
| **4. Rechargement de sauvegarde** | [persist.nut:1128](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/persist.nut#L1128) : `this._c76ForceReloadRegen = true;` qui donne [scheduler_tasks.nut:409](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/scheduler_tasks.nut#L409) : `c76ReloadDue = this._c76ForceReloadRegen;` entraînant [L485](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/scheduler_tasks.nut#L485) `c76NeedFullRegen = true;` | `c76Reason = "reload"` ([scheduler_tasks.nut:501](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/scheduler_tasks.nut#L501)) | 1 fois à chaque chargement de sauvegarde | Les catalogues pourraient être persistés, mais la politique de sécurité actuelle force une régénération totale. |
| **5. Invalidation externe du portefeuille** (`_portfolioInvalidated`) | [scheduler_tasks.nut:485](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/scheduler_tasks.nut#L485) : `if (this._portfolioInvalidated) c76NeedFullRegen = true;` | `c76Reason = "invalidated"` ([scheduler_tasks.nut:500](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/scheduler_tasks.nut#L500)) | Rare/événementiel (fermeture d'industrie si C76 désactivé, ou reprise après échec rail/drop) | Sous C76, les événements NoAI incrémentent des couches plutôt que `_portfolioInvalidated`, sauf en cas de reprise de batchs rail abandonnés ([persist.nut:892, 1025](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/persist.nut#L892-L1025)). |
| **6. Changement de couche non filtrable par C80** (`towns`, `lines`, `engines.air`) | [scheduler_tasks.nut:489-491](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/scheduler_tasks.nut#L489-L491) : `c76LayerChanged == true` et `_c80ModeRegenModes()` retourne `null` ([orchestrator.nut:1376-1388](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/orchestrator.nut#L1376-L1388)) | `c76Reason = "layers"` ([scheduler_tasks.nut:502](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/scheduler_tasks.nut#L502)) | Dès qu'une ville apparaît (`towns`), qu'un avion est débloqué (`engines.air`), ou qu'une ligne est abandonnée/construite avec impact non acquitté (`lines`) | C80 cible `industries` et `engines.rail/road/water`, mais `towns`, `lines` et `engines.air` renvoient `null` dans `_c80ModeRegenModes`, forçant une régénération complète. |
| **7. Dérive de trésorerie / Budget Stale** | [scheduler_tasks.nut:380-400](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/scheduler_tasks.nut#L380-L400) : `budgetNow > budgetThen + 50000 && budgetNow > budgetThen * 2`, et [L483](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/scheduler_tasks.nut#L483) : `budgetStale = stale && !AIR_EFFICIENCY_RESELECT && !C76_LEAN_INVALIDATION;` | `c76Reason = "budget"` ([scheduler_tasks.nut:504](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/scheduler_tasks.nut#L504)) | Chaque fois que la trésorerie double avec +50 k£ de delta (fréquent en phase de forte croissance) | `AIR_EFFICIENCY_RESELECT=1` permet une simple resélection sans recalcul complet du catalogue ([scheduler_tasks.nut:474-477](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/scheduler_tasks.nut#L474-L477)), mais ce réglage est à **0 par défaut**. |
| **8. Échec ou non-application de l'incrémental post-construction** | [task_projects.nut:2104-2119](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/task_projects.nut#L2104-L2119) : si `c121Incremental` n'a pas traité toutes les villes ou si `_c76AcknowledgeAllLayers()` est contourné car `airTouchedTowns` est non vide sans republish total | `reason = "post_build"` ([task_projects.nut:2117](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/task_projects.nut#L2117)) ou reporté sur le dispatch suivant en motif `"layers"` | Après construction d'une ligne si le catalogue aérien ne s'acquitte pas de la couche `lines` | `_c121IncrementalPublishTouched` et `_tryIncrementalAfterBuild` existent, mais un reliquat non acquitté sur `lines` fait retomber le planificateur sur un full. |

---

## 2. Déclencheurs d'événements NoAI

Deux mécanismes transmettent les perturbations extérieures vers le planificateur :
1. L'invalidation globale `this._portfolioInvalidated = true` (mécanisme historique pré-C76).
2. L'incrémentation des révisions de couches C76 via `this._c76BumpLayer(layerName, notify)` ([orchestrator.nut:1069-1093](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/orchestrator.nut#L1069-L1093)).

### A. Événements affectant `_portfolioInvalidated`

Dans [event_handlers.nut:310-323](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/event_handlers.nut#L310-L323) :
- `ET_INDUSTRY_CLOSE` ([events.nut:53-54](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/events.nut#L53-L54)) :
  - **Sous C76 (défaut `c76_regen_targeted=1`)** : ne met **pas** `_portfolioInvalidated = true`. Il appelle `this._c76BumpLayer("industries", true)` ([event_handlers.nut:316](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/event_handlers.nut#L316)).
  - **Hors C76 (`c76_regen_targeted=0`)** : positionne `this._portfolioInvalidated = true` ([event_handlers.nut:318](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/event_handlers.nut#L318)).
- `_reconcileAfterLoad` ([persist.nut:892, 1025](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/persist.nut#L892-L1025)) :
  - Si un lot dynamique de construction rail ou une recherche de rail a été abandonné au rechargement, `this._portfolioInvalidated = true` est positionné manuellement pour forcer la remise à plat.

### B. Événements NoAI incrémentant une révision de couche C76 (`_c76BumpLayer`)

Les événements sont dépilés dans `_processEvents` ([events.nut:313-380](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/events.nut#L313-L380)) puis dispatchés vers `_markDirty` ([events.nut:40-147](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/events.nut#L40-L147)) ou traités dans [event_handlers.nut](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/event_handlers.nut) :

1. **Couche `towns`** :
   - Événement `AIEvent.ET_TOWN_FOUNDED` ([event_handlers.nut:585](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/event_handlers.nut#L585), [events.nut:47-48](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/events.nut#L47-L48)).
   - Appel : `this._c76BumpLayer("towns", true)`.
   - **Impact au défaut :** `_c80ModeRegenModes()` inspecte `towns` ([orchestrator.nut:1377-1378](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/orchestrator.nut#L1377-L1378)) ; comme `towns` n'est pas restreint à un seul mode, il renvoie `null`, ce qui déclenche **immédiatement une reconstruction complète** (`c76Reason = "layers"`).

2. **Couche `industries`** :
   - Événement `AIEvent.ET_INDUSTRY_OPEN` ([event_handlers.nut:300-307](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/event_handlers.nut#L300-L307), [events.nut:51-52](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/events.nut#L51-L52)).
   - Événement `AIEvent.ET_INDUSTRY_CLOSE` ([event_handlers.nut:310-323](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/event_handlers.nut#L310-L323), [events.nut:53-54](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/events.nut#L53-L54)).
   - Appel : `this._c76BumpLayer("industries", true)`.
   - **Impact au défaut :** Grâce à `c80_mode_regen=1`, `industries` ne déclenche **pas** de reconstruction complète : il déclenche un `_c80DoModeRegen` ciblé sur `[MODE_RAIL, MODE_ROAD, MODE_WATER]` ([orchestrator.nut:1384-1386](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/orchestrator.nut#L1384-L1386)), sauf si combiné avec le filet annuel `c76PeriodicDue`.

3. **Couche `engines.air`** :
   - Événement `AIEvent.ET_ENGINE_AVAILABLE` pour un véhicule dont le type est `AIVehicle.VT_AIR` ([event_handlers.nut:624](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/event_handlers.nut#L624), [events.nut:49-50](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/events.nut#L49-L50)).
   - Appel : `this._c76BumpLayer("engines.air", true)`.
   - **Impact au défaut :** [orchestrator.nut:1381](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/orchestrator.nut#L1381) stipule : `if (eng.air > ack.engines.air) return null;`. `_c80ModeRegenModes()` retourne `null` ! Cet événement NoAI déclenche donc **une reconstruction complète** (`c76Reason = "layers"`).

4. **Couches `engines.rail` / `engines.road` / `engines.water`** :
   - Événement `AIEvent.ET_ENGINE_AVAILABLE` pour les autres types de transport ([event_handlers.nut:627-632](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/event_handlers.nut#L627-L632)).
   - Appels : `this._c76BumpLayer("engines.rail", true)`, etc.
   - **Impact au défaut :** Géré de façon incrémentale par mode via C80 ([orchestrator.nut:1385](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/orchestrator.nut#L1385)).

5. **Couche `lines`** (déclenchement interne/réseau) :
   - Événement d'abandon de paire : `_markPairAbandoned` ([lines.nut:293](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/lines.nut#L293)). Comme `c76_lean_invalidation = 0` par défaut, tout abandon de ligne appelle `this._c76BumpLayer("lines", true)`.
   - Événement de fin de construction : `_tryIncrementalAfterBuild` ([task_projects.nut:2091](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/task_projects.nut#L2091)) appelle `this._c76BumpLayer("lines", true)`.
   - **Impact au défaut :** Dans [orchestrator.nut:1379-1380](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/orchestrator.nut#L1379-L1380), `if (lines > ack.lines) return null;`. Si la couche `lines` n'est pas acquittée immédiatement, elle force une régénération complète (`c76Reason = "layers"`).

---

## 3. Sondes existantes et attribution des opcodes au motif

### A. Sondes existantes

Il existe trois sondes instrumentées dans le code source :

#### 1. `probe_catalogue` contrôlant `C39_INVALIDATION_PROBE`
- **Réglage :** `probe_catalogue` ([info.nut:261](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/info.nut#L261), [settings.nut:261](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/settings.nut#L261)), valeur par défaut : **0**.
- **Liaison :** `C39_INVALIDATION_PROBE = (val != 0);` ([settings.nut:262](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/settings.nut#L262)).
- **Lieu d'émission :** [task_report.nut:1480](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/task_report.nut#L1480) via `OpexC76Log(...)` ([probes.nut:2412-2418](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/probes.nut#L2412-L2418)).
- **Sites d'appel enregistrant la régénération (`_c76RecordRegen`) :**
  1. [scheduler_tasks.nut:238](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/scheduler_tasks.nut#L238) (reconstruction C78 par tranches terminée à l'application) :
     `this._c76RecordRegen("full", s.regenOps, c76Days, year, reason);`
     Ici `s.regenOps` cumule la totalité des opcodes consommés par l'ensemble des tranches de calcul C78/V147 ([scheduler_tasks.nut:292](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/scheduler_tasks.nut#L292)), et `reason` contient exactement le motif (`"periodic"`, `"layers"`, `"budget"`, `"reload"`, `"invalidated"`, etc.).
  2. [scheduler_tasks.nut:520](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/scheduler_tasks.nut#L520) (reconstruction complète synchrone dans `_dispatchCatalog`) :
     `this._c76RecordRegen("full", ops, days, year, c76Reason);`
  3. [task_projects.nut:2076](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/task_projects.nut#L2076) (reconstruction post-build en staged bootstrap) :
     `this._c76RecordRegen("full", ops, days, year, "staged");`
  4. [task_projects.nut:2117](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/task_projects.nut#L2117) (fallback complet post-build) :
     `this._c76RecordRegen("full", ops, days, year, "post_build");`
  5. [orchestrator.nut:1277](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/orchestrator.nut#L1277) (`_c76DoFullRegen`) :
     `this._c76RecordRegen("full", totalOps, totalDays, year, reason);`
- **Format exact de la ligne produite dans le journal moteur OpenTTD (`-d script=4`) :**
  ```text
  dbg: [script] [OpexAI] [C76] C76_REGEN phase=regen kind=<kind> reason=<reason> ops=<ops> days=<days> y=<year>
  ```
  *(Note : Selon les versions ou l'environnement, le préfixe peut être `dbg: [script] [C76]` ou `dbg: [script] [OpexAI] [C76]`).*
- **Champs disponibles :**
  - `phase` : `"regen"`
  - `kind` : `"full"` (ou `"mode"` / `"reselect"`)
  - `reason` : `"periodic"`, `"layers"`, `"budget"`, `"staged"`, `"post_build"`, `"reload"`, `"invalidated"`, `"bootstrap"`, `"initial"`
  - `ops` : nombre entier d'opcodes Squirrel consommés (cumulé sur toutes les tranches dans le cas C78)
  - `days` : nombre de jours de jeu écoulés pour le calcul
  - `modes` : présent seulement pour `kind=mode`
  - `y` : année calendaire OpenTTD (`year`)

#### 2. `catalog_cost_probe` contrôlant `CATALOG_COST_PROBE`
- **Réglage :** `catalog_cost_probe` ([info.nut:191-196](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/info.nut#L191-L196), [settings.nut:194](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/settings.nut#L194)), valeur par défaut : **0**.
- **Lieu d'émission :** [probes.nut:824-865](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/probes.nut#L824-L865) (`OpexCatalogCostLog`).
- **Format de ligne :**
  ```text
  dbg: [script] [OpexAI] CATALOG_COST reason=<reason> total_ops=<total_ops> path=<path> ...
  ```
- **Limitation majeure :** Pour une reconstruction découpée C78 en tâche de fond, `CATALOG_COST_ACTIVE` est réinitialisé à `null` lors de l'extension de la file ([scheduler_tasks.nut:509](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/scheduler_tasks.nut#L509)) et les tranches individuelles sont loguées en `CATALOG_SLICE` sans le motif global d'invalidation. De plus, les reconstructions post-build en staged bootstrap ([task_projects.nut:2076](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/task_projects.nut#L2076)) n'émettent pas `CATALOG_COST` mais `PROJECTS_COST`.

#### 3. `probe_span_trace` contrôlant `PROBE_SPAN_TRACE`
- **Réglage :** `probe_span_trace` ([info.nut:127-132](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/info.nut#L127-L132), [settings.nut:196](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/settings.nut#L196)), valeur par défaut : **0**.
- **Format :** Émet des balises `SPAN` chronométrées (`catalog.rebuild`, `air_catalog.slice`), mais **n'attribue pas** le motif C76 de haut niveau dans la balise.

### B. Conclusion sur la sonde existante retenue

**La sonde `probe_catalogue=1` (`C39_INVALIDATION_PROBE`) est exactement la sonde idoine déjà présente dans le code.**  
Elle intercepte tous les chemins (synchrones ou asynchrones C78 découpés, bootstrap étagé, filet annuel, dérive budget, couches) au moment de l'enregistrement du bilan via `_c76RecordRegen`, avec les opcodes réels cumulés (`ops`), l'année (`y`), le type (`kind=full`) et le motif exact (`reason`).

Aucune nouvelle sonde n'est nécessaire pour mesurer ces coûts.

---

## 4. Plan de mesure du diagnostic

Ce plan de diagnostic à un seul bras a pour but de quantifier le coût opcode réel de chaque motif de reconstruction complète sur une durée représentative.

- **Objectif :** Mesurer le volume d'opcodes et la fréquence de chaque motif de reconstruction complète (`kind=full`) sous le profil par défaut, sans modifier le comportement de l'IA.
- **Bras unique :**  
  `OpexAI[probe_catalogue=1]`  
  *(Tous les autres paramètres restent aux valeurs par défaut : `c121_air_economics=1`, `c121_catalog_incremental=1`, `c76_regen_targeted=1`, `c80_mode_regen=1`, `air0310_incremental_publish=1`, `v147_air_catalog_tasks=1`, `staged_bootstrap=1`).*
- **Horizon :** **5 ans** (permet de capturer le bootstrap stades 0/1/2, 5 filets annuels périodiques, les doublements de budget de début de partie, et les premières ouvertures de lignes).
- **Échantillon :** **5 graines représentatives** : `42, 100, 999, 1234, 5678`.
- **Exécution :** Exécution avec OpenTTDLab en capturant la sortie script (`-d script=4`), par exemple via le harnais solo `sweeps/bench_v2.py`.
- **Sorties attendues de l'analyseur (`sweeps/analyse_full_regen_cost.py`) :**
  1. Tableau récapitulatif par motif (`reason`) :
     - Nombre d'occurrences totales sur la campagne.
     - Opcodes totaux consommés par motif.
     - Médiane et maximum d'opcodes par événement de ce motif.
     - Part relative (%) dans le budget total des reconstructions complètes.
  2. Ventilation par année (Années 0 à 4) montrant l'évolution temporelle :
     - Année 0 : prédominance attendue de `staged` et `bootstrap`.
     - Années 1 à 4 : part de `periodic` vs `budget` vs `layers`.
  3. Fichier JSON structuré pour exploitation automatisée.

---

## 5. Limites de l'audit

1. **Agrégation C78 dans `regenOps` :** Pour les reconstructions asynchrones C78, `ops` représente la somme des opcodes de toutes les tranches exécutées jusqu'à l'application finale ([scheduler_tasks.nut:292](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/scheduler_tasks.nut#L292)). Si une tranche a été interrompue ou si un nouveau rebuild a écrasé l'état en cours avant l'application finale, les opcodes de la tâche avortée ne sont pas comptabilisés dans le message final `C76_REGEN`.
2. **Conflit de motifs simultanés :** Dans `_dispatchCatalog` ([scheduler_tasks.nut:488-505](file:///home/deploy/projects/wt-regen-audit/ai/OpexAI/scheduler_tasks.nut#L488-L505)), les drapeaux d'invalidation sont évalués avec une priorité fixe : `bootstrap` > `invalidated` > `reload` > `layers` > `budget` > `periodic`. Si un changement de couche et le filet périodique annuel surviennent en même temps, le motif enregistré est `"layers"`. Le motif journalisé reflète donc la priorité d'attribution du planificateur et non une décomposition causale exclusive.
3. **Absence d'imputation aux sous-modes dans les reconstructions complètes :** Le message `C76_REGEN` pour `kind=full` n'émet pas le champ `modes=...`. Pour connaître la part respective du catalogue aérien vs rail/route/eau au sein d'un rebuild complet synchrone, il faudrait inspecter les sondes fines internes (`CATALOG_COST`), qui ne sont pas actives au défaut.
4. **Validité statistique :** L'échantillon de 5 graines × 5 ans est calibré pour un diagnostic de coût et d'ordre de grandeur (opcodes/an), et ne constitue pas une porte de qualification comparative V102 (qui exigerait 40×3 ou 20×10 apparié).


---

## Note de relecture (Claude, 12/10) — corrections et mesure

### Corrections de l'audit d'agy
- **Chemin manquant, le plus coûteux :** l'intention réactive `regen`
  (`_c76BumpLayer(..., notify=true)` → `_enqueueReactive("regen")`,
  `orchestrator.nut:1089-1091`) est traitée par `_dispatchReactiveIntention`
  (`orchestrator.nut:674-686`) : si `_c80ModeRegenModes()` rend `null`, elle
  lance `_c76DoFullRegen("reactive")` (`orchestrator.nut:681`, puis 1242-1277),
  **reconstruction complète synchrone d'un seul bloc**, hors du découpage C78.
  Motif journalisé `reactive` (et `reactive_<modes>` pour la voie C80).
  Le tableau du §1 attribue à tort les changements de couche au seul
  `_dispatchCatalog` (« layers ») : au défaut, c'est l'orchestrateur qui les
  consomme en premier.
- Le motif `bootstrap` n'existe pas (premier passage : `initial`) ;
  `c76TotalOps` n'existe pas (compteur réel : `s.regenOps`, corrigé ci-dessus).
- Format réel de la sonde (`task_report.nut:1450`, `OpexC76Log`
  `probes.nut:2412`) : `OPEX <date> C76_REGEN phase=regen kind=… reason=…
  year=… days=… days_since_prev=… ops=… …`. L'analyseur d'agy cherchait un
  ordre de champs et un `y=` inventés : réécrit en lecture clé=valeur,
  tests passés au format réel.

### Mesure 5×5 (`results/regen_cost_5x5_20261012*`, graines 42/100/999/1234/5678, `probe_catalogue=1`, duel, V147 ON/OFF)

| Bras | Reconstructions complètes | Opcodes | `reactive` | `periodic` | `budget` |
|---|---:|---:|---:|---:|---:|
| V147=1 (défaut) | 12 | 105,9 M | 11 (72 %) | 1 | 0 |
| V147=0 | 11 | 90,2 M | 9 (65 %) | 1 | 1 |

- Chaque `reactive` coûte **5 à 12 M d'opcodes d'un bloc** ; elles se
  concentrent en **janvier–mars 1972 et 1973** (couches villes/lignes/moteurs
  AIR non filtrables par C80). Ordre de grandeur : ≈ 12,6 M/graine en 1972,
  soit ~20 % des ~64 M d'opcodes exécutés par OpexAI cette année-là
  (référence LOOP_OPS du banc V147 40×4, autres graines : estimation).
- **Aucune reconstruction complète enregistrée en 1970–1971.** Sonde
  complémentaire 1×3 graine 42 avec `catalog_cost_probe=1`
  (`results/regen_c78_apply_1x3_20261012*`) : le **rebuild AIR C78 initial
  dure 27 mois** (janvier 1970 → 1er avril 1972, ~1 150 tranches, 25,6 M
  d'opcodes, 616 plans évalués, ~25 plans/mois publiés au fil de l'eau) ; dans
  le bras V147=0 il n'est **pas terminé au bout de 3 ans**. Le rebuild suivant
  (mai 1972) ne compte que quelques plans.

### Conséquences pour la suite
1. La cible « rendre incrémentale une reconstruction » est d'abord
   `_c76DoFullRegen("reactive")` : identifier quelle couche la déclenche
   (towns, lines ou engines.air) avant de choisir. Sonde passive minimale :
   journaliser la couche fautive au moment où `_c80ModeRegenModes()` rend
   `null`.
2. Question nouvelle, plus importante économiquement : **le scan AIR initial
   met 2 ans à parcourir son vivier**. Les meilleurs plans ne sont pas
   forcément trouvés tôt. Mesurer ce qui borne son débit (tranches par tour,
   continuation bloquée par worker/recherche rail, budget de tranche) avant
   toute variante.
Aucun correctif proposé avant ces mesures.
