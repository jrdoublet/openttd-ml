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
- **Deux canaux de génération, régulier et de délestage.** Utile — à condition que le déclencheur
  soit une tension comparée aux autres, jamais un seuil absolu.
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
┌─ 1. VECTEUR DE TENSION ────────────────────────────────────────────────────────┐
│  tension(r,a) = cout_r(a) / (dispo_r − engagements_r + flux_r × tau(a))         │
│  tau(a) endogène · flux SIGNÉ · dénominateur ≤ 0 ⇒ ∞ (sentinelle)              │
│  ⚠️ ÉTAPE EN COURS : instrumentation seule, aucune décision touchée.            │
│     Question à trancher : la contrainte dominante VARIE-T-ELLE ?                │
└───────────────────────────────┬────────────────────────────────────────────────┘
                                ▼
┌─ 2. GÉNÉRATION D'INTENTIONS ───────────────────────────────────────────────────┐
│  régulier : fret · interurbain pax · densification de l'existant                │
│  opportuniste : subventions non attribuées, si temps restant > chantier estimé  │
│  délestage : armé par une tension RELATIVE, jamais par un seuil absolu          │
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
