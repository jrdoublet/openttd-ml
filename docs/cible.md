# Architecture cible d'OpexAI — version corrigée

Origine : schéma d'orchestrateur proposé par Gemini le 2026-09-03, à la suite du modèle de tension
de Liebig (`docs/taches.md` §3 terdecies). **L'idée générale est retenue.** Ce document sépare ce
qui est juste, ce qui est faux, et ce qui contredit nos propres mesures.

> **Comment lire.** ✅ = vérifié dans du code qui tourne. ❌ = faux, vérification à l'appui.
> ⚠️ = contredit une mesure de ce projet. ❓ = non vérifié, à traiter comme une hypothèse.

---

## 1. ❌ Ce qui est halluciné : l'API des opcodes

Le bloc de code de l'étape 8 est faux sur **deux** points indépendants.

```squirrel
// PROPOSÉ — ne compile pas, et ne ferait pas ce qui est annoncé
if (AIController.GetOpsLimit() - AIController.GetOps() < 2500) {
    AIController.Break(1);
}
```

**Vérification** — comptage d'occurrences sur trois IA réelles (AAAHogEx 37 531 lignes, AdmiralAI,
OpexAI) :

| symbole | AAAHogEx | AdmiralAI | OpexAI | verdict |
|---|---:|---:|---:|---|
| `GetOpsLimit()` | 0 | 0 | 0 | ❌ **n'existe pas** |
| `GetOps()` | 0 | 0 | 0 | ❌ **n'existe pas** (les 20/5 apparents ne sont que des sous-chaînes de `GetOpsTillSuspend`) |
| `GetOpsTillSuspend()` | 20 | 0 | 5 | ✅ c'est la seule primitive réelle |
| `AIController.Break(...)` | 2, **toutes commentées** | 0 | 0 | ❌ c'est un **point d'arrêt de débogueur**, pas un `yield` ; prend une chaîne, pas un entier |
| `AIController.Sleep(n)` | 18 | 8 | 3 | ✅ c'est le vrai rendu de main |
| coroutines Squirrel (`suspend`/`resume`) | 0 | 0 | 0 | ❓ jamais employées par aucune IA du lot |

**Forme correcte** :

```squirrel
// Le budget est un DEBIT, pas un stock : OPS_PER_TICK opcodes par tick, non reportables.
// GetOpsTillSuspend() rend le RESTE du tick courant.
if (AIController.GetOpsTillSuspend() < seuilDerivé) {
    AIController.Sleep(1);   // rend la main au moteur jusqu'au tick suivant
    return;
}
```

⚠️ Et le seuil ne doit pas être `2500` en dur : il se dérive du coût mesuré de la prochaine
micro-étape, que `budget.nut` sait déjà mesurer par catégorie.

---

## 2. ⚠️ Ce qui contredit nos propres mesures

### 2.1 🔴 L'exécuteur reprenable (étape 8) a été mesuré **deux fois**, et rejeté deux fois

C'est la correction la plus importante du document. Le « curseur sauvegardé, reprise au tick
suivant » est exactement le réglage `rail_search_resumable` :

| banc | écart | signes |
|---|---:|---:|
| 1er (socle ordinaire) | **−23,1 %** de valeur, 16/20 graines perdantes | $p = 0{,}0118$ |
| 2e (socle segmenté) | **−13,3 %** de valeur, 5/20 — et **−27,5 % de gares** ($t = -4{,}46$) | $p = 0{,}0414$ |

**Mécanisme identifié** : `safetyDeadline` est une échéance en **ticks**, posée une fois. En mode
reprenable, la fenêtre est partagée avec le reste de la file, et la recherche **meurt avant
d'aboutir**. Le découpage n'a pas redistribué le travail : **il l'a amputé**.

➡️ Conséquence pour la cible : un exécuteur incrémental n'est acceptable que si **chaque
micro-étape porte sa propre échéance**, jamais une échéance globale posée à l'entrée. Sinon on
rejoue une régression déjà payée deux fois.

### 2.2 ❌ Le « rollback » ne récupère pas de capital — il en coûte

« Revente des segments posés pour récupérer une partie du capital » : dans OpenTTD, **démolir
coûte**. Mesure maison : ne plus raser l'aéroport orphelin économise **~25 000 £ par échec de
chantier** (tâche C5, adoptée). Un rollback n'est donc pas une opération neutre de trésorerie,
c'est **une seconde dépense après un échec**.

➡️ La bonne politique, déjà adoptée ici : **abandonner en place** plutôt que nettoyer, et se
souvenir de l'échec (`air_abandon`, adopté) pour ne pas le refaire. Le « plan de rollback » de
l'étape 7 doit devenir un **plan d'abandon** : libérer la réserve, marquer la paire, ne rien
démolir.

### 2.3 ⚠️ L'ordre étape 4 → étape 5 est le mauvais sens

Estimer l'impact de chaque intention **puis** filtrer la faisabilité fait payer le calcul cher sur
des actions qui seront rejetées. Nos deux mesures sur ce point :

- **C4, filtre de platitude éliminatoire** (rejet à ≥ 2 niveaux d'écart, à la AAAHogEx) : adopté,
  il écarte 7 échecs sur 8 **avant** toute dépense.
- **`air_presite`** (niveler puis tester, donc estimer avant d'éliminer) : mesuré à 10 ans,
  **non adopté** — le gaspillage supprimé ne se convertit pas.

➡️ **Les filtres éliminatoires bon marché passent AVANT l'estimateur d'impact**, pas après.

### 2.4 ⚠️ Le « dry run » par intention attaque le vrai goulot

Le goulot mesuré d'OpexAI n'est ni la trésorerie ni le pathfinder — **c'est le débit du
contrôleur** : avec ≥ 300 k£ en caisse, l'IA ne construit rien dans **61,2 %** des transitions
mensuelles, contre 2,8 % chez AAAHogEx. Et les trois voies du pathfinder sont fermées : relever
❌, redistribuer ❌ (−23 %), abaisser 🟡 nul.

➡️ Une simulation à blanc **par intention** multiplie précisément la dépense qui nous manque.
Elle n'est justifiée que sur les **quelques** candidats déjà classés en tête, jamais sur le vivier.

### 2.5 ⚠️ Le Town Rating n'est pas un score continu

`AITown.GetRating` rend un **enum 0-8**, pas une note fine — un garde de ce projet comparait un
enum à 700 et était donc mort. « Calcul strict du nombre d'arbres à abattre pour vérifier que la
réputation ne descendra pas sous le seuil » n'est **pas calculable** par l'API : on ne peut ni
prédire le delta, ni le lire finement. Et notre seul levier dessus, `tree_planting`, est **rejeté
deux fois** (−22,1 % puis, garde réparé, −13,4 % de `profit_year`).

➡️ Le Town Rating est une ressource à **lire** (et à respecter quand elle bloque), pas une
ressource qu'on sait piloter.

### 2.6 ❓ Le « délai d'attente aux signaux » n'est pas une télémétrie disponible

Il n'existe pas d'état « en attente à un signal » dans l'API : `AIVehicle.GetState()` rend
`VS_RUNNING`, `VS_STOPPED`, `VS_IN_DEPOT`, `VS_AT_STATION`, `VS_BROKEN`, `VS_CRASHED`. AAAHogEx
n'utilise que `VS_RUNNING` et `VS_AT_STATION`. La saturation ne peut donc être qu'**inférée**
(temps de rotation observé contre temps théorique), pas relevée.

➡️ Et de toute façon **sans objet dans notre topologie actuelle** : point-à-point, voie unique,
1 à 2 convois par ligne.

---

## 3. ⚠️ Le schéma réintroduit une dizaine de nombres magiques

La consigne était « éviter à tout prix les constantes en dur ». Le schéma en contient au moins
huit : `K_r > 0,85`, `< 2500` opcodes, fenêtre de `60 jours`, rétroaction à `90 jours`,
subventions à `180 jours`, `490/500` slots, l'exposant `²` du score, et un `Poids(r)` par
ressource.

Trois d'entre eux méritent un traitement particulier :

- **L'exposant 2 et les poids** sont **deux paramètres libres par ressource**. C'est exactement ce
  qu'on voulait supprimer.
- **`490/500`** : le plafond de véhicules n'est **pas global**, il est **par type**
  (`vehicle.max_trains`, `max_roadveh`, `max_aircraft`, `max_ships`) et **lisible au runtime** —
  donc à lire, jamais à écrire.
- **`180 jours` pour les subventions** est le seul qui soit défendable : ce n'est pas un réglage
  de confort mais un **garde-fou empirique écrit par une IA qui exploite réellement les
  subventions** (AdmiralAI, `road/buslinemanager.nut:232-235`, commentaire à l'appui). À reprendre
  comme repli, mais dérivable : la vraie quantité est *le temps de chantier estimé*.

---

## 4. 🔴 Le défaut de modélisation du score

```
Score(A) = ROI(A) × Multiplicateur_Urgence / ( 1 + Σ_r Poids(r) × Tension(A,r)² )
```

Trois problèmes, dont le premier est disqualifiant.

1. **L'argent est compté deux fois.** `ROI(A) = profit / capital` porte déjà le capital au
   dénominateur, et `Tension(A, argent)` l'y remet. Une action chère est pénalisée deux fois, avec
   un exposant différent à chaque fois.
2. **Deux définitions de tension incompatibles cohabitent.** L'étape 2 définit
   `K_r = Consommation_moyenne / Marge_sécurité(r)`, indépendante de l'action ; l'étape 6 utilise
   `Tension(A, r)`, dépendante de l'action. Le schéma ne les réconcilie jamais.
3. **`Multiplicateur_Urgence` est un troisième paramètre libre**, non défini.

**Forme retenue** (§3 terdecies), qui n'a aucun paramètre libre :

```
tension(r, a) = cout_r(a) / ( disponible_r - engagements_r + flux_r × tau(a) )
denominateur(a) = Σ_r  tension(r, a) × cout_r(a)
score(a) = profit_attendu(a) / denominateur(a)
```

- `tau(a)` est **endogène** : l'horizon d'amortissement de l'action, `capital / profitAnnual`.
- `engagements_r` est **mesuré** : les obligations déjà prises et non payées.
- Le flux reste **signé** — une ressource qui se vide est la plus contraignante ; `max(0, flux)`
  supprimerait précisément le Time-to-Exhaustion qu'on cherche.
- **L'argent n'apparaît qu'une fois**, comme une ressource parmi d'autres.
- Aucun `argmax`, donc **aucune oscillation** et aucune hystérésis à régler ; quand une ressource
  domine, la somme dégénère d'elle-même vers l'aiguillage d'AAAHogEx.
- L'existant en est un **cas particulier** : `tension(argent) = 1`, tout le reste à 0. Le passage
  est donc mesurable en continu, et non comme un remplacement en bloc — ce qui compte, car
  `portfolio_v2`, la dernière refonte du classement livrée d'un coup, **détruisait la valeur**.

---

## 5. ✅ Ce qui est juste et qu'on garde

- **La séparation télémétrie / diagnostic / génération / sélection / exécution.** C'est déjà
  grossièrement notre structure (`catalog` → `candidates` → `projects` → `builder_*`), et la
  nommer aide.
- **La dérivée première plutôt que l'état instantané.** Le flux est le terme qui manque
  aujourd'hui à toutes nos décisions ; la fenêtre glissante est la bonne idée, sa longueur doit
  juste être dérivée du bruit mesuré, pas fixée à 60 jours.
- **Deux canaux de travail, régulier et événementiel.** Le second sert à entretenir une couche
  réellement périmée, avec une tâche coalescée et repriseable. La famille « tension relative /
  prix d'ombre » a été fermée stratégiquement : elle ne pilote plus le déclenchement de C41.
- **La simulation à blanc existe vraiment** : `AITestMode`, et AAAHogEx s'en sert comme d'un
  outil. ⚠️ **Piège vérifié chez nous** : `AIAccounting` compte le coût **simulé** d'un
  `AITestMode` ; le bouclier est un `AIAccounting` imbriqué.
- **La boucle de rétroaction (étape 9)** est bonne, et déjà amorcée : nous avons mesuré que le
  rail coûte **×1,70** son prix modèle. ⚠️ Mais notre suite a été meilleure que « apprendre un
  coefficient » : **demander un devis réel** par `AITestMode` + `AIAccounting` (C7, adopté). Quand
  l'API sait répondre exactement, **mesurer bat apprendre**.
- **Les subventions comme opportunité datée** : leur grandeur limitante est un temps avant
  fermeture, et c'est un bon test du modèle de tension.

---

## 6. La cible corrigée

```
┌─ 0. TÉLÉMÉTRIE ────────────────────────────────────────────────────────────────┐
│  Stocks   : cash + marge d'emprunt · slots PAR TYPE (AIGameSettings) ·          │
│             sites admissibles restants (vivier survivant à la séparation)       │
│  Flux     : cashflow net/jour · opcodes = DÉBIT (OPS_PER_TICK, pas un stock) ·  │
│             production des villes/industries                                    │
│  Registres: Town Rating (enum 0-8, LECTURE seule) · subventions non attribuées  │
│             et leur date d'expiration                                           │
│  ⚠️ pas de « temps d'attente aux signaux » : l'API ne l'expose pas              │
└───────────────────────────────┬────────────────────────────────────────────────┘
                                ▼
┌─ 2. GÉNÉRATION D'INTENTIONS ───────────────────────────────────────────────────┐
│  régulier : fret · interurbain pax · densification de l'existant                │
│  opportuniste : subventions non attribuées, si temps restant > chantier estimé  │
│  maintenance C41 : couche stale coalescée, coût borné, échéance propre          │
└───────────────────────────────┬────────────────────────────────────────────────┘
                                ▼
┌─ 3. FILTRES ÉLIMINATOIRES BON MARCHÉ  ◀── DÉPLACÉ AVANT L'ESTIMATION ──────────┐
│  platitude du site · distance hors bornes · paire déjà servie · échec mémorisé  │
│  Motif mesuré : le filtre de platitude écarte 7 échecs sur 8 pour presque rien ;│
│  « niveler puis tester » (air_presite) a été mesuré et NON adopté.              │
└───────────────────────────────┬────────────────────────────────────────────────┘
                                ▼
┌─ 4. ESTIMATION D'IMPACT — sur les SEULS candidats de tête ─────────────────────┐
│  Δ(a) = [Δcash, Δslots, Δopcodes, Δsites]  + devis RÉEL via AITestMode          │
│  ⚠️ AIAccounting compte le coût SIMULÉ d'AITestMode : bouclier = accounting     │
│     imbriqué                                                                    │
│  ⚠️ le goulot mesuré est le DÉBIT DU CONTRÔLEUR : ne jamais simuler le vivier   │
└───────────────────────────────┬────────────────────────────────────────────────┘
                                ▼
┌─ 5. SÉLECTION ─────────────────────────────────────────────────────────────────┐
│  score(a) = profit_attendu(a) / Σ_r [ tension(r,a) × cout_r(a) ]                │
│  Aucun poids, aucun exposant, aucun multiplicateur d'urgence : zéro paramètre   │
│  libre. L'argent n'est compté qu'UNE fois. Dégénère vers le ROI capital actuel. │
└───────────────────────────────┬────────────────────────────────────────────────┘
                                ▼
┌─ 6. EXÉCUTION INCRÉMENTALE ────────────────────────────────────────────────────┐
│  while (GetOpsTillSuspend() > coût de la micro-étape suivante) { avancer }      │
│  sinon AIController.Sleep(1)        ← PAS Break(), qui est un débogueur         │
│  🔴 CHAQUE micro-étape porte sa PROPRE échéance. Une échéance globale posée à   │
│     l'entrée a été mesurée DEUX FOIS : −23,1 % puis −13,3 % et −27,5 % de gares.│
│  En cas d'échec : ABANDON EN PLACE + mémorisation. Pas de rollback : démolir    │
│  COÛTE (~25 000 £ mesurés par chantier avorté).                                 │
└───────────────────────────────┬────────────────────────────────────────────────┘
                                ▼
┌─ 7. RÉTROACTION ───────────────────────────────────────────────────────────────┐
│  réel vs estimé sur coût, opcodes et débit                                      │
│  ⚠️ Quand l'API sait répondre exactement, MESURER BAT APPRENDRE : le devis      │
│     AITestMode a remplacé le facteur correctif ×1,70 appris.                    │
│  L'apprentissage reste utile là où aucun devis n'existe : les OPCODES.          │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Ordre de construction

| # | étape | état |
|---|---|---|
| 1 | **Vecteur de tension, instrumentation seule** | 🔄 **en cours** — la contrainte dominante varie-t-elle ? Si c'est l'argent 100 % du temps, tout le reste tombe |
| 2 | Filtres éliminatoires **avant** estimation | 🟡 partiellement fait (platitude, distance, mémoire d'échec) — reste à ordonner explicitement |
| 3 | Sonde subventions, lecture seule (C17) | ⬜ à faire, pas cher, tranche seul |
| 4 | Micro-étapes à échéance **propre** (C15 et la leçon d'A4) | ⬜ à faire, et c'est le prérequis de toute exécution incrémentale |
| 5 | Dénominateur composé | ⬜ **conditionné au résultat de l'étape 1** |
| 6 | Apprentissage de l'estimateur d'opcodes (B3) | ⬜ seul endroit où apprendre bat mesurer |

**Règle qui domine toute cette liste** : rien ne s'arme sans avoir montré que le mécanisme
**mord**. `portfolio_max_batch` a été rejeté avec 11 graines sur 20 en nuls exacts, et le plafond
`maxRoutes` mesuré à 0 refus sur 32. Un beau schéma qui ne se déclenche jamais coûte des opcodes
et ne rend rien.

---

## 8. Vérification contre la source OpenTTD 15.3 (2026-09-03)

Second lot de conseils, **vérifié dans le source du moteur** (`github.com/OpenTTD/OpenTTD`, tag
`15.3`), et non dans d'autres IA. Fichiers lus : `src/script/api/*.hpp`, `script_list.cpp`,
`src/table/settings/*.ini`.

### 8.1 Verdicts, un par affirmation

| affirmation | verdict | source |
|---|---|---|
| `AIList.Valuate`, `KeepTop`, `KeepAboveValue`, `KeepBottom`, `KeepList` | ✅ existent | `script_list.hpp:318,343,349` |
| `AIList.Filter()` | ❌ **n'existe pas** — la liste complète est `Clear HasItem Begin Next IsEmpty IsEnd Count GetValue SetValue Sort AddList SwapList Remove* Keep* Valuate` | `script_list.hpp` |
| `AIList.KeepBelowList()` | ❌ **n'existe pas** (il y a `KeepList` et `KeepBelowValue`) | idem |
| 🔴 « `Valuate` est exécuté 100 % en C++, coût CPU quasi nul » | ❌ **FAUX** — la boucle de `Valuate` appelle `Squirrel::DecreaseOps(vm, 5)` **par élément**, plus le coût du valuateur lui-même | `script_list.cpp:910` |
| `AIController.GetOpsLimit()` / `GetOps()` | ❌ **n'existent pas** : la classe expose `GetTick`, `GetOpsTillSuspend`, `GetSetting`, `GetVersion`, `SetCommandDelay`, `Sleep`, `Break`, `Print`, `Import` | `script_controller.hpp:111-204` |
| `AIController.Break(1)` comme `yield` | ❌ signature `Break(const std::string &message)`, et la doc dit **« when script developer tools are active »** — c'est un point d'arrêt de débogueur | `script_controller.hpp:175-184` |
| `AIController.Sleep(ticks)` | ✅ c'est le vrai rendu de main | `script_controller.hpp:172` |
| `AIEventVehicleLost`, `AIEventVehicleUnprofitable`, `AIEventIndustryClose`, `AIEventTownFounded` | ✅ **tous les quatre existent** | `script_event_types.hpp:573,639,705,879` |
| `AIEventTownStyleAnnounce` | ❌ **n'existe pas** dans les 34 classes d'événements de 15.3 | `script_event_types.hpp` |
| 🟢 **non cité, et directement utile** : `AIEventSubsidyOffer`, `SubsidyOfferExpired`, `SubsidyAwarded`, `SubsidyExpired` | ✅ existent | idem |
| `AIEventEnginePreview`, `AIEventEngineAvailable`, événements `Company*`, `AIEventExclusiveTransportRights`, `AIEventRoadReconstruction` | ✅ existent | `script_event.hpp`, `script_event_types.hpp` |
| `AIEventStationFirstWait` | ❌ n'existe pas ; le type réel est `AIEventStationFirstVehicle`, première visite par un véhicule | `script_event.hpp:41`, `script_event_types.hpp:713-751` |
| `AIEventScript` / `ET_SCRIPT` | ❌ n'existent pas dans l'API standard 15.3 | liste exhaustive de `ScriptEventType`, `script_event.hpp:21-57` |
| `AIEventController.HasEvents()` | ❌ n'existe pas ; utiliser `IsEventWaiting()` puis `GetNextEvent()` | `script_event.hpp:86-97` |
| `AISignal.SIGNALTYPE_PBS` | ❌ **il n'y a pas de classe `AISignal`** ; c'est `AIRail.SIGNALTYPE_PBS` | `script_rail.hpp:74`, liste des classes de l'API |
| `AICompany.BuyLandArea` (« acheter du terrain pour verrouiller un corridor ») | ❌ **n'existe pas** — aucune méthode d'achat de terrain dans `AITile` (`IsBuildable … PlantTree, DemolishTile, LevelTiles, GetBuildCost`) ni dans `AICompany` | `script_tile.hpp`, `script_company.hpp` |
| « interroger la demande via le graphe interne (LinkGraph) » | ❌ **aucun `script_linkgraph.hpp`** dans l'API. Le plus proche existant est `AICargoMonitor` (cargo ramassé/livré par compagnie) | liste des classes de l'API 15.3 |
| `AITown.TOWN_RATING_MEDIOCRE` | ✅ existe — enum `NONE, APPALLING, VERY_POOR, POOR, MEDIOCRE, GOOD, VERY_GOOD, EXCELLENT, OUTSTANDING`, `INVALID = -1`. **Confirme notre mesure : c'est un enum, pas un score continu** | `script_town.hpp:84-93` |
| `AIOrder.OF_TRANSFER`, `OF_NO_LOAD` | ✅ existent | `script_order.hpp:56,57` |
| ⚠️ **`OF_TRANSFER` et `OF_UNLOAD` sont mutuellement exclusifs** | ✅ confirmé par la source : « Cannot be set when `OF_TRANSFER` or `OF_NO_UNLOAD` is set ». Déjà corrigé dans `builder_road.nut:742-748` le 2026-09-02 ; **la ligne de `taches.md` qui écrit `OF_TRANSFER \| OF_UNLOAD` est périmée** | `script_order.hpp:53-56` |
| « une case de gare = deux caisses » | 🟡 vrai pour le jeu de base, mais la longueur est une **propriété par engin** (`AIVehicle.GetLength`), qu'un NewGRF peut changer | — |
| « PBS divise par trois les blocages » | ❓ **invérifiable**, aucune source ; à traiter comme une intuition |
| `AIMain.Save()` / `Load()` | 🟡 le mécanisme existe bien (méthodes `Save`/`Load` sur la classe principale de l'IA), mais **il n'y a pas de classe `AIMain`** — c'est la classe déclarée par l'IA elle-même |

### 8.2 🔑 Deux vérifications qui changent une conclusion

**1. CargoDist est DÉSACTIVÉ par défaut, et notre config ne l'active pas.**

```ini
linkgraph.distribution_pax       def = DT_MANUAL
linkgraph.distribution_mail      def = DT_MANUAL
linkgraph.distribution_armoured  def = DT_MANUAL
```
(`src/table/settings/linkgraph_settings.ini`)

➡️ **Toute la section 4 du conseil est sans objet chez nous.** Les passagers n'ont pas de
destination, il n'y a pas d'accumulation de correspondances en gare B, et le « piège classique »
décrit ne peut pas se produire dans notre configuration gelée. À rouvrir **seulement** si on
décide un jour d'activer CargoDist — et ce serait alors un changement de règle du jeu, pas une
optimisation.

**2. `OPS_PER_TICK = 10000` est confirmé au niveau du moteur.**

```ini
script.script_max_opcode_till_suspend   def = 10000   max = 250000
```
(`src/table/settings/script_settings.ini`)

➡️ Confirme la constante de `budget.nut`, qui n'était jusqu'ici vérifiée que « dans le binaire ».

### 8.3 Ce qu'il faut retenir des conseils, une fois corrigés

- ✅ **Le pipeline `AIList` reste le bon réflexe**, mais pour la bonne raison : il ne coûte pas
  « zéro », il coûte **5 opcodes par élément** plus le valuateur, là où une boucle `foreach`
  Squirrel paie l'intégralité de son corps à chaque tour. C'est un facteur, pas une exonération.
  ⚠️ Corollaire direct pour A6 : un calcul de tension écrit en `Valuate` sur 500 villes coûte au
  minimum 2 500 opcodes — soit un quart d'un tick entier. **À mesurer**, pas à supposer gratuit.
- 🟢 **L'architecture par événements est le vrai gain**, et elle est mieux fournie que le conseil
  ne le dit : les quatre événements cités existent, **plus les quatre événements de subvention**.
  ➡️ **C17 n'a donc pas besoin de scruter `AISubsidyList` en boucle** : `AIEventSubsidyOffer`
  prévient à la publication de l'offre. Une opportunité datée est signalée, pas sondée.
- ⚠️ **Le HPA\* hiérarchique est une bonne idée qui répond à un problème que nous n'avons pas.**
  Les trois voies du pathfinder sont mesurées et fermées : relever ❌, redistribuer ❌ (−23 %),
  abaisser 🟡 nul ; et le pathfinder segmenté (A5) donne **+12,9 % de gares pour une valeur
  neutre**. Le découpage macro/micro serait un quatrième essai sur un goulot qui n'en est pas un.
- ❌ **Le « verrouillage foncier préemptif » est impossible** : l'API n'expose aucun achat de
  terrain. La seule façon de réserver un corridor est d'y **poser du rail**, ce qui en paie le
  coût complet. L'idée tombe.
- ✅ **La résilience Save/Load par états plats est juste**, et rejoint la leçon d'A4 : ce qui ne
  se sérialise pas (curseurs, échéances globales, objets complexes) est précisément ce qui nous a
  déjà coûté deux bancs.

### 8.4 C39 — bus d'invalidation événementiel et réconciliation périodique (2026-09-08)

Cette section est normative pour l'architecture future. Le moteur publie les événements dans la
file propre à l'instance du script. OpexAI la consomme déjà correctement avec
`AIEventController.IsEventWaiting()`, `GetNextEvent()`, `GetEventType()` puis la méthode statique
`.Convert(event)` de la classe spécialisée (`main.nut:4609-4874`).

**Séparer impérativement notification et exécution.** `_processEvents()` doit rester un routeur
léger : convertir l'événement, extraire ses identifiants, fusionner l'invalidation dans un état
plat et armer une tâche. Il ne doit ni reconstruire un catalogue complet, ni générer des milliers
de candidats, ni lancer un pathfinder. Ces travaux appartiennent à la file C41, qui peut les
prioriser, les découper et les reprendre.

```text
AIEventController
    -> routeur d'événements (aucun travail lourd)
        -> invalidations coalescées + objets concernés
            -> tâches urgentes de maintenance
            -> sous-catalogues sales
                -> candidats sales par mode / origine
                    -> portefeuille sale
                        -> sélection sale
```

**Grandes catégories et effets :**

- **monde** (`IndustryOpen/Close`, `TownFounded`) : actualiser uniquement les entités touchées,
  puis les familles de candidats qui en dépendent ;
- **matériel** (`EnginePreview/Available`) : évaluer le prototype ou rafraîchir uniquement rail,
  route, air ou eau selon le type du moteur ;
- **véhicules** (`Crashed`, `Lost`, `WaitingInDepot`, `Unprofitable`, `AutoReplaced`) : alimenter
  les tâches de réparation, retrait, renouvellement et mise à jour d'identifiants ;
- **concurrence/infrastructure** (`Company*`, `ExclusiveTransportRights`, `RoadReconstruction`) :
  invalider les plans physiques ou les villes réellement concernés ;
- **subventions** (`Subsidy*`) : maintenir un registre d'opportunités datées et produire un
  candidat ciblé, sans balayage régulier de `AISubsidyList`.

**Révisions minimales :** `catalogRevision` par sous-catalogue (`cargos`, `towns`, `industries`,
`rail`, `road`, `air`, `water`), `candidateRevision` par mode, `portfolioRevision`, puis
`selectionRevision`. Une tâche mémorise les révisions consommées ; elle ne repart que si une
dépendance a changé. Plusieurs événements avant son exécution sont coalescés en une seule passe,
avec un ensemble d'IDs affectés quand une mise à jour locale est possible.

**Filet périodique obligatoire.** Aucun événement 15.3 ne couvre l'évolution mensuelle de la
production/population, la disponibilité des ponts, tout changement de carte concurrent, l'âge des
véhicules ou l'expiration interne de la mémoire d'abandon. Une resynchronisation rare couvre aussi
le chargement d'une sauvegarde, car les événements en attente ne constituent pas un état durable.
La doctrine est donc *event-driven + reconciliation*, jamais « événements seulement ».

Cette couche C39 dit **quoi est devenu périmé**. C41 dira **quand et avec quelle tranche d'opcodes
le recalculer**. Les futures tâches de renouvellement de véhicules, audit des ponts, exploitation
des subventions et devis rail fractionné doivent toutes entrer par cette même interface ; ne pas
ajouter une nouvelle boucle périodique autonome pour chacune.

**État de livraison (C39.0, 2026-09-08).** La première tranche est une sonde passive, activable
seulement par `c39_invalidation_probe=1` (défaut `0`). Elle met en oeuvre cet état plat sous
`_staleness` et le point unique `_markDirty()`, puis consigne directement `C39_DIRTY` et le résumé
coalescé `C39_REFRESH` dans `AILog` (sans dépendre de `decision_log`). `IndustryOpen/Close`, `TownFounded` et
`EngineAvailable` y sont raccordés. L'état n'est encore consommé par aucune tâche : aucune
invalidation ne déclenche de calcul et la cadence mensuelle historique est conservée. C'est le
contrat de base pour étendre le routeur sans créer d'effets de bord avant C41.

La trace C39.1 (5 graines × 6 ans, `results/diag_c39_events_6y_5seeds.json`) a reçu 43
notifications sans erreur : 32 moteurs, 6 fermetures et 5 ouvertures d'industrie. 28 refreshes
en ont absorbé au moins une, jusqu'à trois dans une même passe. Elle valide donc le format de
coalescence et désigne `EngineAvailable` comme premier consommateur actif à mesurer ; aucune ville
n'a été fondée dans cet échantillon, donc ce cas doit rester passif jusqu'à une trace appropriée.

**C39.3 (2026-09-08) précise le seuil de propagation, sans changer le jeu.** Sous
`c39_decision_delta_probe=1` et la sonde C39.0, l'IA retient la signature du meilleur projet avant
la première notification d'une rafale. Après le rebuild mensuel historique, elle écrit la signature
après, son changement éventuel, et pour chaque `EngineAvailable` si le moteur est retenu par le
sous-catalogue de son mode. La trace dédiée 5 graines × 6 ans
(`results/diag_c39_decision_delta_6y_5seeds.json`) compte 23 rétentions sur 32 moteurs : rail 5/5,
route 13/13, eau 5/9, air 0/5. Ainsi, la future tâche ciblée pourra éliminer les moteurs filtrés
avant de propager l'invalidation. Les 18 changements de premier projet sur 29 rafales sont un
signal de sensibilité du portefeuille, **pas** une attribution causale à un moteur : une rafale peut
inclure d'autres événements et le monde change pendant le cycle mensuel. C39.3 reste par conséquent
une instrumentation, pas une autorisation de réactiver le rebuild complet C39.2.

### 8.5 C41.0 — registre de révisions et acquittements (contrat avant exécution ciblée)

La première tranche C41 ne doit ni avancer un pathfinder, ni tenter un « rebuild ciblé » fictif :
le catalogue ne propose aujourd'hui que `refresh()`, qui appelle toutes ses sous-régénérations.
Elle établit donc le contrat qui rendra une telle exécution vérifiable : pour chaque couche
catalogue (`cargos`, `towns`, `industries`, `rail`, `road`, `air`, `water`) et candidat
(`rail`, `road`, `air`, `water`), plus portefeuille et sélection, conserver deux entiers primitifs
et sérialisables : `revision` et `acknowledgedRevision`.

- Au premier événement qui salit une couche encore propre, incrémenter sa révision ; les autres
  événements de la rafale n'ajoutent pas de travail.
- Une tâche ne peut acquitter que les révisions de ses dépendances réellement reconstruites. Elle
  ne touche jamais aux révisions d'une autre couche.
- Le rebuild complet historique constitue l'unique exception transitoire : il acquitte toutes les
  couches connues, parce qu'il les a effectivement recalculées. Cette compatibilité disparaîtra au
  fur et à mesure que les sous-régénérations publiques existeront.
- Après chargement de sauvegarde, l'absence de file d'événements impose une réconciliation qui
  produit de nouvelles révisions ; ne pas supposer qu'un acquittement antérieur décrit encore le
  monde courant.

C41.0 sera instrumenté et désactivé par défaut. Aucun `dueCycle`, aucune priorité et aucune
décision de construction ne doivent dépendre du registre tant que sa trace n'a pas confirmé
coalescence et acquittement. C41.1 pourra ensuite rendre publique une unique sous-régénération de
matériel — `rail`, `road`, `air` ou `water` — et comparer ce chemin au rebuild complet ; les mondes
(villes/industries) et le pathfinding restent hors de cette première mesure.

**État de livraison C41.0 (2026-09-08).** `c41_revision_probe=0` ajoute le registre passif à
`_staleness`, sans modifier la file. La trace 5 graines × 6 ans
(`results/diag_c41_revision_6y_5seeds.json`) est saine : 47 notifications font progresser 42
révisions de couche, puis les 30 rebuilds qui absorbent une rafale produisent exactement 30
acquittements. L'écart 42/30 est attendu : une même rafale peut rendre plusieurs couches sales,
mais une couche ne progresse qu'une fois avant son acquittement. C41.1 doit maintenant exposer et
mesurer un seul sous-catalogue de matériel ; il ne doit pas encore toucher villes, industries,
candidats, portefeuille ou pathfinding.

**Contrat C41.1 — eau.** Une nouvelle disponibilité de navire arme une seule micro-tâche
`catalog.water`. Elle appelle seulement la sous-régénération eau, enregistre son coût d'opcodes,
puis acquitte **uniquement** `catalog.water` et le remet propre. `candidates.water`, portefeuille
et sélection restent volontairement sales : `OpexWaterPlans` peut être régénéré isolément, mais
son insertion dans le vivier multimodal et son classement demandent une opération de fusion qui
n'existe pas encore. Le rebuild historique les traitera donc comme avant. Cette tranche ne doit ni
construire, ni reclasser, ni modifier le budget ; son réglage reste à `0` et son intérêt est le
coût/ordonnancement réel du sous-catalogue, pas une performance de jeu.

**État de livraison C41.1 (2026-09-08).** `c41_water_refresh=0` arme la micro-tâche seulement
après `EngineAvailable` eau, mesure `cat_water_targeted`, puis acquitte et nettoie seulement
`catalog.water`. La trace 5 graines × 6 ans (`results/diag_c41_water_6y_5seeds.json`) est saine : les
9 notifications eau ont produit 9 sous-régénérations, pour 2 923 opcodes au total, soit 315 à 337
par passe. Aucun candidat ni portefeuille n'est réélu. La tâche s'exécute encore pour les 9
annonces, parce que la rétention du moteur n'est connue qu'après lecture du sous-catalogue ; C41.2
devra rendre ce filtre local et éviter les 4/9 rafraîchissements qui avaient ensuite été rejetés
dans la trace C39.3.

**C41.2 (implémenté, non exécuté à la demande, 2026-09-08).**
`c41_water_precheck=0` garde C41.1 comme contrôle. À `1`, le routeur conserve la trace C39 de
tout `EngineAvailable`, mais n'incrémente ni n'arme la branche C41 eau si le moteur n'est pas à la
fois valide, constructible, de type eau et refittable passagers. Ce prédicat reprend exactement
les critères de `_refreshWater()`, sans énumérer le catalogue. Les événements filtrés ne sont donc
pas acquittés fictivement : ils ne produisent pas de révision C41. Aucun test ou diagnostic C41.2
n'a été lancé dans cette tranche ; il faudra comparer C41.1 et C41.2 sur la même trace avant toute
extension vers les candidats.

**Mesure C41.2 (2026-09-08, 5 graines × 6 ans).** Le contrôle C41.1
(`results/diag_c41_water_precheck_baseline_6y_5seeds.json`) exécute 9 rafraîchissements eau pour
2 923 opcodes. Le préfiltre C41.2
(`results/diag_c41_water_precheck_treatment_6y_5seeds.json`) en exécute 5 pour 1 576 opcodes : les
4 moteurs rejetés sont bien évités, soit −44,4 % de passes et **−46,1 % d'opcodes**, sans erreur.
Les deux traces observent les mêmes 9 annonces eau, 5 retenues / 4 filtrées. C'est une validation
de coût et de routage, pas un banc de valeur ; l'étape suivante reste la sonde passive de
`OpexWaterPlans` avant toute fusion dans le portefeuille.

**Contrat C41.3 — plans eau passifs.** Après le sous-catalogue C41.1/C41.2, la même micro-tâche
peut appeler `OpexWaterPlans()` dans un tableau temporaire, mesurer `project_water_targeted_probe`
et consigner le nombre de plans. Ses tests de construction sont sous `AITestMode`, donc aucun dock
ni véhicule ne doit être créé. La sonde ne touche ni `this._projects`, ni les acquittements
`candidates.water`/portefeuille/sélection. Elle doit rester limitée au préfiltre C41.2 et fournir
le coût réel avant que C41.4 puisse concevoir une fusion de vivier.

**Mesure C41.3 (2026-09-08, 5 graines × 6 ans) : ne pas propager.** La trace
`results/diag_c41_water_plans_6y_5seeds.json` est saine mais éliminatoire : les 5 moteurs eau
retenus déclenchent 5 sondes, **0 plan**, et consomment 593 273 opcodes (113 896 à 122 419 par
sonde). Le coût est environ 380 fois celui du sous-catalogue ciblé, pour aucun candidat. C41.3
reste donc à 0 et C41.4 doit d'abord ventiler `OpexWaterPlans` (sites, paires, BFS, économie) afin
d'établir si l'absence de plans est structurelle ou si une étape précise peut être réduite ; aucune
fusion ou micro-tâche active de candidats eau n'est autorisée avant ce diagnostic.

**Mise à jour C41.11–C41.15 (2026-09-08) — ce que les mesures changent.** Les ledgers
passifs C41.11/C41.12 ont mesuré 28,1 % d'opcodes initiaux non utilisés et des couches stale
jusqu'à 61 jours. Mais C41.13/C41.14 ont ensuite tranché le point crucial : ce slack n'est pas
disponible dans le *même tick* que les 56 fenêtres où une micro-tâche ciblée devrait être admise.
Il ne faut donc pas bâtir C41 sur « utiliser le reliquat ». Une micro-tâche utile doit disposer de
sa propre tranche normale de scheduler, entre deux tâches existantes, et ne jamais interrompre un
calcul en cours.

`catalog.water` puis `catalog.road` ont servi de pilotes de contrat, non de priorités produit.
Le second isole bien `EngineAvailable` route et acquitte seulement sa révision de catalogue ;
cependant le comparatif apparié C41.15 5×6 est défavorable (OFF +1,00 % de valeur sur 5/5 graines,
OFF +16,7 % de profit trimestriel sur 4/5). C'est cohérent avec le modèle : tant que le rebuild
historique régénère plus tard candidats, portefeuille et sélection, le sous-catalogue ciblé ajoute
un coût sans offrir de consommateur aval immédiatement frais. `c41_road_refresh` reste donc à 0
et aucun banc officiel n'est justifié.

**Priorité d'architecture C41.** Le gain attendu n'est pas dans les sous-catalogues eux-mêmes,
mais dans une chaîne dont chaque frontière peut être reprise et acquittée séparément :

```text
candidats par mode/origine → pricing/scoring → portefeuille (fusion) →
sélection sous capital (« sac à dos ») → devis et trajet incrémentaux
```

La prochaine sonde doit profiler cette chaîne, en commençant par les candidats route, pour isoler
les sous-étapes et leurs dépendances. Une tranche future ne sera active que si elle (1) possède un
checkpoint sérialisable, (2) porte sa propre échéance, (3) ne réexécute pas au rebuild le travail
déjà acquitté et (4) passe un diagnostic apparié 5×6 avant le banc officiel 20×10. Le pathfinding
reste particulièrement sensible : les tentatives à échéance globale ont déjà été rejetées ; seul
un état local repris par micro-étape est recevable.

**Premier profil de la chaîne (C41.16, 5×6).** `OpexBuildRoadCandidates` a été ventilé sans
modifier sa sortie : fret 83,7 % des 29,31 M opcodes, feeders 16,2 %, `TopK` 0,05 % ; la branche
passagers n'était pas active (`road_pax_build=0`). Le prochain découpage doit donc conserver la
frontière de génération et isoler d'abord les boucles fret, non le tri ni le sac à dos.

**Sous-profil fret (C41.17, sonde).** `OpexRoadFreightCandidates` expose trois tranches passives :
préparation des états déjà desservis, puits industriels, puis puits urbains avec acceptation
mémorisée. Le diagnostic 5×6 (`results/diag_c41_17_road_freight_profile_6y_5seeds.json`) mesure
25,13 M opcodes dans ces tranches : préparation 66,6 %, villes 29,2 %, industries 4,2 %. La
première frontière candidate est donc l'index d'origines servies, et non le cache d'acceptation ni
les puits industriels. Cette découpe conserve l'ordre de production actuel ; elle sert à
dimensionner un état reprenable et ne reporte encore aucun travail du scheduler.

**Index fret (C41.18, apparié 5×6).** L'index spatial d'origines rail+route déjà servies conserve
la predicate historique (`DistanceManhattan < ORIGIN_SEPARATION`) mais évite son scan par
ville/industrie. Il divise par 5,5 la tranche de préparation et par 1,86 la génération route
totale, sans échec sur 10 parties. La valeur et le profit annuel sont compatibles avec un effet
neutre à favorable. Le banc officiel 20×10 (40/40) confirme −47,8 % d'opcodes de génération route,
sans signal économique négatif ; l'index fret est donc livré à ON par défaut.

**Puits urbains fret (C41.19, 5×6).** Seulement 2,0 % des couples producteur×ville passent les
filtres de distance/abandon jusqu'à l'acceptation, et aucun ne devient candidat durant la fenêtre.
La prochaine frontière est donc un index des villes acceptantes par cargo ; il doit rester local à
une génération et reproduire les compteurs de rejet de la boucle historique.

**C39.4 — cause des avions non retenus (2026-09-08).** La sonde
`c39_air_reason_probe=0` sépare les filtres éliminatoires de la sélection finale des combos. Sa
trace 5 graines × 6 ans (`results/diag_c39_air_reason_6y_5seeds.json`) est saine : les cinq annonces
concernent le même moteur 233, un gros avion passagers de capacité 260 (`plane_type=3`), et les
cinq motifs sont `dominated`. Il est donc valide, constructible et refittable, mais perd contre un
avion déjà meilleur selon la règle gros avion → capacité → vitesse. Ne pas implémenter un
préfiltre air « moteur invalide » : une future optimisation devra comparer ce moteur aux gagnants
du catalogue avant d'armer une régénération.

**C41.4 — contrat de départ `VehicleLost`.** Avant toute stratégie de renouvellement ou de
réparation, `c41_vehicle_lost_probe=0` observe séparément de l'ancien A7.4 l'événement
`AIEventVehicleLost`. Son seul effet est une ligne `C41_VEHICLE_LOST` avec l'identifiant, la
validité, l'attribution persistée à une ligne, le mode et le booléen `orphan`. Elle ne doit pas
incrémenter de compteur, poser de signe, salir une couche, modifier une révision ou programmer une
micro-tâche. Cette première mesure distingue une réparation future faisable (ligne/mode connus)
d'un problème d'observabilité (orphelin) sans introduire de recherche globale de stations.

**Mesure C41.4 (2026-09-08, 5 graines × 6 ans).** Le smoke 3 × 2 ans est sain (un événement,
ligne rail attribuée). La trace `results/diag_c41_vehicle_lost_6y_5seeds.json` est également saine :
**29 `VehicleLost`**, 29 véhicules encore valides, **29/29 lignes attribuées**, tous en mode rail,
et aucun orphelin ni erreur. Cette couverture rend une future maintenance rail ciblée possible,
mais ne renseigne pas encore sa cause. La prochaine tranche doit mesurer, pour chaque événement,
l'ordre courant, la position, un éventuel dépôt et l'état du chemin ; ne pas armer de réparation,
de refleet ou de régénération de catalogue avant ce diagnostic.

**C41.5 — faits rail avant toute inférence.** Le réglage `c41_rail_lost_probe=0` ajoute au
diagnostic C41.4 l'état numérique du véhicule, son ordre courant, la destination, la position et
la validité du dépôt. La trace 5 × 6 (`results/diag_c41_rail_lost_6y_5seeds.json`) est saine : les
29 notifications viennent de seulement **4 couples ligne-véhicule**, récurrents ; chacune porte
deux ordres valides, dont la destination appartient à la ligne, et un dépôt rail valide. Écarter
donc ordre hors-ligne et dépôt manquant, mais ne pas conclure à un signal bloqué : l'API ne le
rend pas observable. La suite est une corrélation passive avec la topologie persistée de ces
lignes (double voie, second dépôt, longueur de quai et signaux).

**C41.6 — concentration topologique (2026-09-08).** La sonde
`c41_rail_lost_topology_probe=0` ne relit que l'état persisté d'une ligne. La trace 5 × 6
(`results/diag_c41_rail_lost_topology_6y_5seeds.json`) est saine : les 29 événements, et les quatre
couples ligne-véhicule qui les répètent, sont tous sur des lignes **fret à double voie**, deux
rames, deux véhicules persistés et second dépôt valide (quais 3–4, 2–3 wagons). La défaillance
est donc concentrée dans la géométrie ou l'exploitation de la double voie, non dans les ordres,
un dépôt absent ou une voie simple. C41.7 devra lire seulement les tuiles déjà référencées par ces
lignes (sorties de quais, fronts de dépôts et jonctions) pour vérifier connexion et signalisation ;
aucun scan global ni geste correctif n'est encore autorisé.

**C41.7 — cause locale observable (2026-09-08).** La sonde
`c41_rail_lost_physical_probe=0` vérifie sans pathfinding les approches déjà persistées des quais
et les fronts des dépôts. La trace 5 × 6
(`results/diag_c41_rail_lost_physical_6y_5seeds.json`) est saine : les 29 occurrences gardent les
quatre approches rail et les deux fronts de dépôt valides. Mais les quatre appels
`AIRail.GetSignalType(lead, station_exit)` rendent tous `SIGNALTYPE_NONE` (255). Le code confirme
la cause structurelle : la pose de signaux est conditionnée à `join != null`, alors que la double
voie ordinaire reçoit deux rames et aucun signal d'approche. Une future C41.8 pourra seulement
réparer de façon idempotente les approches d'une ligne double ayant effectivement émis `Lost`,
derrière un réglage expérimental et une mesure appariée ; aucune régénération de catalogue ou
réparation globale n'est autorisée.

**C41.8 — contrat de réparation PBS, non exécuté.** `c41_rail_lost_signal_repair=0` transforme
seulement l'événement d'une ligne double attribuée en entrée coalescée de `c41_rail_signals`.
Cette micro-tâche pose un `AIRail.SIGNALTYPE_PBS` uniquement sur les approches à une branche et
orienté vers le quai ; elle reconnaît un PBS existant et refuse de remplacer un signal non-PBS.
Les approches à deux branches restent intactes, car leur sortie sûre n'est pas établie. Aucun
chemin n'est recherché et aucune couche C39/C41, flotte, véhicule ou portefeuille ne change.
Implémenté le 2026-09-08 sans smoke ni mesure à la demande : son activation exige d'abord un
smoke, puis une trace appariée avant toute décision de défaut.

**Verdict C41.8 (2026-09-08) : PBS d'approche rejeté.** Le smoke est sain, mais le diagnostic
apparié 5 × 6 oppose 29 `VehicleLost` sur 4 couples ligne-véhicule dans le contrôle à **45 sur
10** avec la réparation PBS (les trois graines actives se dégradent). Les 10 PBS sont bien posés
et les reprises suivantes les reconnaissent, donc ce n'est pas un défaut d'idempotence. Le réglage
reste à 0 : l'hypothèse « signal d'approche manquant » est insuffisante, voire perturbatrice. Ne
pas lancer le banc officiel ni étendre la réparation ; isoler plutôt la géométrie et le choix de
branche de la double voie avant toute nouvelle commande.

**C41.9 — premier défaut géométrique prouvé (2026-09-08).** La sonde
`c41_rail_lost_connectivity_probe=0` appelle seulement `AIRail.AreTilesConnected` entre les
voisins immédiats des approches et dépôts. Trace 5 × 6 saine : parmi 28 pertes, quatre répétitions
du couple graine 7 / ligne 18 / véhicule 115 ont `a_links=0` — la tuile d'approche A existe mais
ne mène à aucune branche reconnue hors du quai. Toutes les autres approches et dépôts vus dans les
24 autres pertes ont au moins un lien sortant. C41.10 pourra donc réparer **uniquement** ce
raccord local, d'abord dans `AITestMode`, puis par une commande identique si le test réussit.
Cette piste ne couvre pas encore les 24 autres cas et ne doit pas déclencher de réparation globale.
