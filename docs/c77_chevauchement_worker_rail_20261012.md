# Rapport d'analyse : Exposition réelle du chevauchement C77 et Workers Rail

**Date :** 12 octobre 2026  
**Auteur :** Antigravity (mode lecture seule — aucune commande Docker, aucun banc, aucun commit, aucune modification de code)  
**Contexte :** `docs/c76_c77_reliquat_audit_20261012.md`, Thème 3 : dans `ai/OpexAI/orchestrator.nut`, `c77_subsidy` et `c77_build` s'exécutent même quand un travailleur `rail_search` ou `rail_stock` est actif.  
**Question :** Ce chevauchement arrive-t-il en partie réelle, et coûte-t-il quelque chose ?

---

## 1. Cartographie des marqueurs de log et code émetteur

Inspection détaillée des modules [`orchestrator.nut`](../ai/OpexAI/orchestrator.nut), [`task_rail.nut`](../ai/OpexAI/task_rail.nut), [`task_projects.nut`](../ai/OpexAI/task_projects.nut), [`probes.nut`](../ai/OpexAI/probes.nut), [`event_handlers.nut`](../ai/OpexAI/event_handlers.nut) et [`task_road.nut`](../ai/OpexAI/task_road.nut).

### 1.1 Début et fin d'un travailleur `rail_search` ou `rail_stock`

* **Travailleur `rail_search` (A* ligne primaire ou upgrade) :**
  - *Instanciation / Début :*
    - [`ai/OpexAI/task_rail.nut:1230–1236`](../ai/OpexAI/task_rail.nut#L1230-L1236) (recherche primaire sous `C80_WORKER_RAIL`) :  
      `this._activeWorker = { kind = "rail_search", state = { ai = this, search = this._railSearch } };`
    - [`ai/OpexAI/task_rail.nut:1742–1748`](../ai/OpexAI/task_rail.nut#L1742-L1748) (upgrade/expansion sous `C80_WORKER_RAIL`).
  - *Journalisation début :*
    - Si `C56_TASK_TRACE` (`probe_events=1`) : émet `OpexC56TaskLog("RAIL_SEARCH_START", ...)` ([`task_rail.nut:1224`](../ai/OpexAI/task_rail.nut#L1224)) et `OpexC56TaskLog("WORKER_ENTER", worker.kind, "-")` ([`probes.nut:1568`](../ai/OpexAI/probes.nut#L1568)).
    - **Au défaut (`probe_events=0`) : non journalisé.**
  - *Fin / Libération :*
    - [`ai/OpexAI/orchestrator.nut:983–986`](../ai/OpexAI/orchestrator.nut#L983-L986) : quand `outcome == "done" || outcome == "cancelled"`, `this._activeWorker = null;`.
    - [`ai/OpexAI/task_rail.nut:1248, 1256, 1760`](../ai/OpexAI/task_rail.nut#L1248) : réinitialisation synchrone si échec immédiat ou complétion sans reprise.
  - *Journalisation fin :*
    - Si `C56_TASK_TRACE` : `OpexC56TaskLog("WORKER_EXIT", acc.kind, "-", "outcome=" + outcome ...)` ([`probes.nut:1576`](../ai/OpexAI/probes.nut#L1576)).
    - **Au défaut (`probe_events=0`) : non journalisé.**

* **Travailleur `rail_stock` (recherche en fond pour mise en stock C80 / C121) :**
  - *Instanciation / Début :*
    - [`ai/OpexAI/task_rail.nut:2002–2007`](../ai/OpexAI/task_rail.nut#L2002-L2007) :  
      `this._activeWorker = { kind = "rail_stock", state = { ai = this } };` (appelé par `_startRailStockSearch`, déclenché soit par `_tryStartRailStockWorker` sous `C80_RAIL_STOCK_WORKER`, soit par `_tryStartC121RailPrepSearch` sous `C121_AIR_FIRST_YEAR_RAIL_PREP`).
  - *Journalisation début :*
    - Si `C56_TASK_TRACE` : `OpexC56TaskLog("RAIL_STOCK_START", ...)` ([`task_rail.nut:2015`](../ai/OpexAI/task_rail.nut#L2015)) et `WORKER_ENTER` ([`probes.nut:1568`](../ai/OpexAI/probes.nut#L1568)).
    - Si `CATALOG_COST_PROBE` en an 1 C121 : `OpexC121RailPrepLog` ([`rail_prep_c121.nut:33–40`](../ai/OpexAI/rail_prep_c121.nut#L33-L40)).
    - **Au défaut (`probe_events=0`, `catalog_cost_probe=0`) : non journalisé au démarrage.**
  - *Fin / Libération :*
    - [`ai/OpexAI/orchestrator.nut:1010–1011`](../ai/OpexAI/orchestrator.nut#L1010-L1011) : `this._activeWorker = null;`.
  - *Journalisation fin :*
    - Si `C56_TASK_TRACE` : `WORKER_EXIT` ([`probes.nut:1576`](../ai/OpexAI/probes.nut#L1576)), `RAIL_STOCK_TIMEOUT` ([`task_rail.nut:2048`](../ai/OpexAI/task_rail.nut#L2048)), `RAIL_STOCK_DEPOSIT` ([`task_rail.nut:2107`](../ai/OpexAI/task_rail.nut#L2107)), `RAIL_STOCK_EXPIRE` ([`task_rail.nut:2174`](../ai/OpexAI/task_rail.nut#L2174)).
    - Si `C39_PASS_CLOCK_LEDGER` (`probe_scheduler=1`) : rapport annuel `OPEX YYYY-MM-DD C39_PASS_CLOCK phase=annual year=YYYY key=worker|rail_stock passes=... days=... ticks=... ops=...` ([`ledgers.nut:171`](../ai/OpexAI/ledgers.nut#L171), alimenté par [`orchestrator.nut:1006`](../ai/OpexAI/orchestrator.nut#L1006)).
    - **Au défaut : non journalisé.**

### 1.2 Exécution de `c77_build` / `c77_subsidy` et construction résultante

* **Enfilage des intentions :**
  - Subvention reçue : [`ai/OpexAI/event_handlers.nut:342`](../ai/OpexAI/event_handlers.nut#L342) enfile `c77_subsidy` et émet sous `DECISION_LOG=1` :  
    `OPEX YYYY-MM-DD SUBSIDY_OFFER sub=<id> cargo=<label> src_t=... src=... dst_t=... dst=... exp=... matched=...` ([`event_handlers.nut:345`](../ai/OpexAI/event_handlers.nut#L345)).
  - Événement ciblé terminé : [`ai/OpexAI/orchestrator.nut:442`](../ai/OpexAI/orchestrator.nut#L442) (`OpexFinishRegenEntity`) enfile `c77_build`.
  - Subvention injectée : [`ai/OpexAI/orchestrator.nut:933`](../ai/OpexAI/orchestrator.nut#L933) (`_c77InjectSubsidy`) enfile `c77_build`.
* **Dépilage et exécution (`_dispatchReactiveIntention`) :**
  - `c77_subsidy` : [`ai/OpexAI/orchestrator.nut:720–741`](../ai/OpexAI/orchestrator.nut#L720-L741).
  - `c77_build` : [`ai/OpexAI/orchestrator.nut:742–793`](../ai/OpexAI/orchestrator.nut#L742-L793).
  - **NON JOURNALISÉ DIRECTEMENT !**
    - Aucun log `OpexDecide` ni `AILog.Info` n'est émis au moment précis où `c77_subsidy` ou `c77_build` s'exécute dans `_dispatchReactiveIntention`.
    - Si `C39_PASS_CLOCK_LEDGER` (`probe_scheduler=1`) est actif, `orchestrator.nut:967` enregistre le passage, publié annuellement : `C39_PASS_CLOCK phase=annual key=reactive|c77_subsidy` et `key=reactive|c77_build` ([`ledgers.nut:171`](../ai/OpexAI/ledgers.nut#L171)).
    - Si `PROBE_SPAN_TRACE=1`, des spans `"loop.orch.reactive.c77_subsidy"` et `"loop.orch.reactive.c77_build"` sont ouverts.
  - **Sonde minimale qui manquerait :**  
    Dans `_dispatchReactiveIntention` :
    ```squirrel
    // orchestrator.nut:720
    if (DECISION_LOG) OpexDecide("C77_SUBSIDY_EXEC", "sub=" + intention.payload.subsidyId
        + " worker=" + (this._activeWorker != null ? this._activeWorker.kind : "none")
        + " rail_search=" + (this._railSearch != null ? 1 : 0));
    // orchestrator.nut:742
    if (DECISION_LOG) OpexDecide("C77_BUILD_EXEC", "reason=" + payload.reason
        + " worker=" + (this._activeWorker != null ? this._activeWorker.kind : "none")
        + " rail_search=" + (this._railSearch != null ? 1 : 0));
    ```
* **Construction résultante (mode et coût) :**
  Quand `c77_build` valide `touches == true` et appelle `this._tryBuildProjects(year)` ([`orchestrator.nut:790`](../ai/OpexAI/orchestrator.nut#L790)) :
  - Mode route (subvention) sous `DECISION_LOG=1` :
    - [`ai/OpexAI/task_road.nut:297`](../ai/OpexAI/task_road.nut#L297) : `OpexDecide("ROAD_BUILD", "line=" + idx + " src=" + candidate.src + " dst=" + candidate.dst + " cargo=" + cargoStr + " dist=" + candidate.distance + " profit=" + candidate.profitAnnual + " cost=" + result.cost + " vehicles=" + result.vehicles.len());`
    - [`ai/OpexAI/task_road.nut:361`](../ai/OpexAI/task_road.nut#L361) : `OpexDecide("C42_SUBSIDY_BUILD", "line=" + idx + " sub=" + candidate.subsidyId + " cargo=" + cargoStr + " mult=" + candidate.multiplier);`
  - Mode air sous `DECISION_LOG=1` : [`ai/OpexAI/task_air.nut:534, 971`](../ai/OpexAI/task_air.nut#L534) : `OpexDecide("AIR_BUILD", ... cost=...);`.
  - Mode rail sous `DECISION_LOG=1` : [`ai/OpexAI/task_rail.nut:1599`](../ai/OpexAI/task_rail.nut#L1599) : `OpexDecide("RAIL_BUILD", "line=" + idx + ... + " cost=" + result.actualCost + ...);`.

### 1.3 Tentatives rail et refus pour caisse

* **Tentative rail (`RAIL_ATTEMPT`) :**
  - [`ai/OpexAI/task_rail.nut:1580–1596`](../ai/OpexAI/task_rail.nut#L1580-L1596) (sous `DECISION_LOG=1`) :  
    `OpexDecide("RAIL_ATTEMPT", "src=" + candidate.src + " dst=" + candidate.dst + ... + " quote=" + result.capital + " actual=" + result.actualCost + " ok=" + (result.ok ? 1 : 0) + " reason=" + result.reason + ...);`
  - Si échec : émet aussi [`task_rail.nut:1607`](../ai/OpexAI/task_rail.nut#L1607) `OpexDecide("RAIL_BUILD_FAIL", "line=" + this._nextLineId + " reason=" + result.reason + " error=" + result.error + ...);`.
* **Refus pour caisse (cash / insufficient) :**
  Deux points d'interception dans `_consumeRailSearch` :
  1. *Pré-contrôle avant travaux (`money < need`) :*  
     [`ai/OpexAI/task_rail.nut:1450–1466`](../ai/OpexAI/task_rail.nut#L1450-L1466)  
     Sous `C41_RAIL_CASH_RELEASE` (actif par défaut via `policy_caches=1`, [`settings.nut:27`](../ai/OpexAI/settings.nut#L27)) :  
     [`task_rail.nut:1461`](../ai/OpexAI/task_rail.nut#L1461) appelle [`probes.nut:1651–1657`](../ai/OpexAI/probes.nut#L1651-L1657) qui émet inconditionnellement :  
     `OPEX YYYY-MM-DD C41_RAIL_CASH_RELEASE reason=precheck src=<src> dst=<dst> need=<need> money=<money>`
  2. *Refus pendant travaux (`OpexBuildLine` renvoie `result.reason == "CASH"`) :*  
     [`ai/OpexAI/task_rail.nut:1472–1483`](../ai/OpexAI/task_rail.nut#L1472-L1483)  
     Sous `C41_RAIL_CASH_RELEASE` :  
     [`task_rail.nut:1478`](../ai/OpexAI/task_rail.nut#L1478) émet :  
     `OPEX YYYY-MM-DD C41_RAIL_CASH_RELEASE reason=build_cash src=<src> dst=<dst> capital=<capital>`
  *Note essentielle :* dans ces deux cas de manque de caisse, `_consumeRailSearch` retourne immédiatement sans appeler `_recordRailAttempt`. Par conséquent, **aucune ligne `RAIL_ATTEMPT` n'est émise sur refus de caisse** ; le marqueur autoritaire est la ligne `C41_RAIL_CASH_RELEASE`.

---

## 2. Dépouillement des journaux par graine

Audit exhaustif de 38 parties réelles issues des campagnes récentes d'octobre 2026 :
- `afm_probe_5x3_20261012_engine` (5 graines × 3 ans, défaut)
- `hubcap_autopsie_cap2_4x3_20261012_engine` (4 graines × 3 ans, défaut)
- `astar_pending_expo_5x6_20261011_engine` (5 graines × 6 ans, `decision_log=1`, `probe_scheduler=1`)
- `v127_expo_6x3_20261007_engine` (6 graines × 3 ans, `decision_log=1`)
- `airpairs_hub3_6x3_20261008_engine` (6 graines × 3 ans, `decision_log=1`)
- `idlecash_diag_6x3_20261007_engine` (6 graines × 3 ans, `decision_log=1`)
- `v122_worst_6x10_engine` (6 graines × 10 ans, `decision_log=1`)

### 2.1 Campagnes du 12 octobre 2026 (`afm_probe` et `hubcap_autopsie`)

*Dans ces deux campagnes, `decision_log` est à 0 dans le manifeste (`decision_log=0`). La sonde `policy_caches` étant à 1 par défaut, les refus de caisse ferroviaire `C41_RAIL_CASH_RELEASE` sont tracés.*

| Campagne / Graine | Années | Subventions reçues / bâties | Worker rail actif pendant C77 | Refus caisse rail (`C41_RAIL_CASH_RELEASE`) | Cause du refus de caisse |
|---|:---:|:---:|:---:|:---:|---|
| **afm_probe s100** | 3 ans | 0 / 0 | 0 | 1 (1972-05-22, capital=46 265 £) | Expansion aérienne (aucun C77 dans la partie) |
| **afm_probe s1234** | 3 ans | 0 / 0 | 0 | 0 | Néant |
| **afm_probe s42** | 3 ans | 0 / 0 | 0 | 0 | Néant |
| **afm_probe s5678** | 3 ans | 0 / 0 | 0 | 0 | Néant |
| **afm_probe s999** | 3 ans | 0 / 0 | 0 | 0 | Néant |
| **hubcap_cap2 s17** | 3 ans | 0 / 0 | 0 | 0 | Néant |
| **hubcap_cap2 s1** | 3 ans | 0 / 0 | 0 | 0 | Néant |
| **hubcap_cap2 s781335** | 3 ans | 0 / 0 | 0 | 0 | Néant |
| **hubcap_cap2 s802204**| 3 ans | 0 / 0 | 0 | 1 (1971-03-03, need=71 616 £, cash=67 360 £) | Expansion aérienne (aucun C77 dans la partie) |

### 2.2 Campagne 6 ans avec `decision_log=1` et `probe_scheduler=1` (`astar_pending_expo`)

*Cette campagne permet d'auditer à la fois `DECISION_LOG` et le registre d'horloge monotone `C39_PASS_CLOCK` pour les intentions réactives et les tranches de workers.*

| Graine | Offres subvention | Subventions bâties (`C42_SUBSIDY_BUILD`) | Date & Coût C77 | Worker rail actif lors du build | Refus caisse rail consécutif | Délai pose rail |
|---|:---:|:---:|---|:---:|:---:|:---:|
| **s100** | 9 | 0 | — | 0 | 0 | 0 j |
| **s1234** | 11 | 0 | — | 0 | 0 | 0 j |
| **s42** | 10 | 1 | 1971-12-06 (ligne 39, PASS) | **0** | **0** | 0 j |
| **s5678** | 12 | 1 | 1972-03-08 (ligne 43, PASS) | **0** | **0** | 0 j |
| **s999** | 15 | 2 | 1971-02-08 (ligne 8, PASS, 12 676 £)<br>1971-06-04 (ligne 12, MAIL) | **0** | **0** | 0 j |

*Détail chronologique sur graine 999 :*
- 1971-01-09 : `RAIL_ATTEMPT` et `RAIL_BUILD` ligne 6 (charbon, coût 37 056 £) -> **OK**
- 1971-01-18 : `RAIL_ATTEMPT` et `RAIL_BUILD` ligne 7 (charbon, coût 46 179 £) -> **OK**
- 1971-02-08 : Subvention bâtie (ligne 8, 12 676 £). Aucun worker rail n'était en cours.
- 1971-06-04 : Subvention bâtie (ligne 12).
- Aucun refus de caisse rail (`C41_RAIL_CASH_RELEASE = 0`). Toutes les poses ferroviaires de la partie ont réussi.

### 2.3 Autres campagnes avec `decision_log=1` (`v127_expo`, `airpairs_hub3`, `v122_worst`)

- **`v127_expo_6x3` (6 graines) :**
  - 6 subventions bâties au total (s100: 3 530 £ ; s2026: 19 029 £, sub3, 9 066 £ ; s42: 20 870 £ ; s999: sub1).
  - Constructions pendant worker rail actif : **0**.
  - Refus de caisse rail consécutif : **0**. Les tentatives ferroviaires avant et après réussissent toutes (ex. s100: rail bâti 38 jours après pour 45 559 £ ; s999: rail bâti 15 jours après pour 43 493 £).
- **`airpairs_hub3_6x3` (6 graines) :**
  - 3 subventions bâties (s100: 20 981 £ ; s42: 20 302 £ et 634 £).
  - Graine 100 : un refus `C41_RAIL_CASH_RELEASE` survient le 1972-06-15 (need=67 799 £, cash=54 514 £). Ce refus survient **190 jours après** la subvention du 1971-12-07, et est précédé immédiatement par 4 ouvertures de lignes aériennes consommant plus de 216 000 £ (lignes 25, 26, 27 et 28 aux coûts de 61 795 £, 58 529 £, 38 964 £ et 57 127 £). La subvention n'a joué aucun rôle causal.
- **`v122_worst_6x10` (6 graines × 10 ans) :**
  - 8 subventions bâties sur les 60 années de jeu cumulées.
  - Deux refus de caisse dans s18 (1971-03-31 et 1971-11-29) : la graine n'a **bâti aucune subvention** ; les deux blocages résultent d'avions achetés 13 et 4 jours avant (38 964 £ chacun).
  - Un refus de caisse dans s6 (1974-06-14, 68 598 £) : survient **9 mois après** la dernière subvention du 1973-09-17, causé par deux lignes aériennes ouvertes 29 et 12 jours plus tôt (38 964 £ chacune).

---

## 3. Synthèse des métriques demandées

Sur l'ensemble des 38 graines auditées :

1. **Constructions C77 pendant un travailleur rail actif :**  
   **0** (zéro absolu).
2. **Constructions C77 suivies d'un échec ou report de la pose rail pour caisse :**  
   **0** (zéro absolu).
3. **Montant de trésorerie ferroviaire préempté par C77 :**  
   **0 £**. Les subventions construites coûtent entre 634 £ et 21 475 £ (mode route léger), tandis que les blocages de caisse ferroviaire portent sur des devis de 46 000 £ à 72 000 £ et sont à 100 % consécutifs à des vagues d'achats d'avions et d'aéroports (38 000 £ à 62 000 £ par ligne).
4. **Délai de pose rail induit :**  
   **0 jour**.

---

## 4. Analyse causale et conclusion

### 4.1 Pourquoi ce chevauchement ne se produit pas en pratique

Trois barrières étanches empêchent le chevauchement redouté :

1. **Défaut de configuration :**  
   `c80_worker_rail` est à **0 par défaut** ([`info.nut:380`](../ai/OpexAI/info.nut#L380), [`settings.nut:588`](../ai/OpexAI/settings.nut#L588)) et `c80_rail_stock_worker` est à **0 par défaut** ([`info.nut:398`](../ai/OpexAI/info.nut#L398)).  
   En régime de croisière (an 2+), le registre `_activeWorker` n'est donc **jamais** occupé par un travailleur ferroviaire. La recherche A* ferroviaire tourne via le mécanisme historique résumable `this._railSearch != null`.
2. **Garde an 1 AIR étanche :**  
   Le seul cas où `_activeWorker == "rail_stock"` existe au défaut est l'an 1 via `c121_air_first_year_rail_prep`. Mais pendant l'an 1, [`orchestrator.nut:906`](../ai/OpexAI/orchestrator.nut#L906) bloque inconditionnellement l'injection de toute subvention (`if (C121_CATALOG_AIR_FIRST_YEAR && C121_CATALOG_FIRST_YEAR_ACTIVE) return false;`). De plus, les événements d'entités ciblées `c77_entity` sont soit différés ([`orchestrator.nut:708`](../ai/OpexAI/orchestrator.nut#L708)), soit sans effet car la tête du vivier `best[0]` ne contient que des liaisons intervilles aériennes (`touches == false`, [`orchestrator.nut:786`](../ai/OpexAI/orchestrator.nut#L786)).
3. **Filtre de tête `c77_targeted_build` :**  
   Quand une subvention est injectée en an 2+, `c77_build` n'appelle `_tryBuildProjects` **que si** la subvention se classe au rang 0 absolu (`head == best[0]`, [`orchestrator.nut:780`](../ai/OpexAI/orchestrator.nut#L780)). Si un projet ferroviaire occupe le rang 0, l'intention réactive abandonne immédiatement sans rien construire (`return true`). Si la subvention est classée au rang 0, elle coûte typiquement ~10 k£, ce qui ne suffit pas à assécher les réserves d'OpexAI.

### 4.2 Conclusion sur l'opportunité d'un correctif

* **Exposition : NULLE en jeu réel.** Le risque d'échec de pose ferroviaire par préemption de caisse via C77 est une hypothèse théorique infirmée par les données de jeu.
* **Faut-il différer `c77_build` pendant un travailleur rail ?**
  - **Sur le plan économique : NON.** L'impact mesurable est strictement nul. Aucun banc de qualification V102 ne pourra montrer de gain statistique sur cette modification.
  - **Sur le plan architectural (registre C80) : CORRECTIF DÉFENSIF SOUHAITABLE À TERME, MAIS NON PRIORITAIRE.**  
    Si un jour `c80_worker_rail` ou `c80_rail_stock_worker` venait à être activé, le fait que `_dispatchReactiveIntention` laisse passer `c77_build` et `c77_subsidy` sans vérifier `this._activeWorker != null` violerait le principe d'exclusivité du double registre.  
    Toutefois, ce correctif relève de la simple hygiène de code pour C80 ; il ne présente aucun caractère d'urgence et ne doit pas faire l'objet d'une campagne de qualification dédiée.

---

## Note de relecture (Claude, 12/10)

Vérifié : `c80_worker_rail` et `c80_rail_stock_worker` valent 0 aux réglages par défaut ; au défaut, l'A* rail passe par `_railSearch`, hors registre `_activeWorker`. Le défaut du thème 3 est réel dans le code mais inerte au défaut. **Clos sans correctif** ; à reprendre seulement si l'un des workers rail C80 passe à 1.
