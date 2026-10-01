# C76 — Routeur d'événements et régénération ciblée du vivier

**Lecture au 30 septembre : contrat initial puis résultats historiques.** C76 ciblé
et C77 sont depuis intégrés ; voir [tâches](taches.md) et [synthèse](journaux/synthese_decisions_2026-09-30.md).
Les numéros de ligne sont ceux de la branche étudiée ; les liens ouvrent les modules
courants sans prétendre retrouver ces anciennes lignes. Le « futur » ci-dessous
appartient à la conception du 21 septembre.

**Contrat initial du 2026-09-21, suivi des résultats de l'étape 1.**
Les références de code visent historiquement la branche `c69-goulot-decision`.

---

## 0. Statut et mandat

| Axe | Statut | Mandat / Décision |
|---|---|---|
| **Origine** | Mesures C73-C74 (`docs/16_bilan_volume.md` §6-§7) | Un tour de file dure **45 à 120 jours** à partir de 1975 ; l'IA ne réalise que **4 à 9 chantiers par an** alors que sa trésorerie atteint 11 M£. |
| **Goulot identifié** | Régénération répétée du vivier | `catalog` (31 % du temps, ~2,8 Mop) et `projects` (23 %, ~2,2 Mop) régénèrent chacun le vivier à chaque tour. |
| **Mandat C76** | Étape 1 : Contrat + sonde passive | Établir le contrat d'invalidation ciblée et mesurer via une sonde passive si les régénérations successives apportent de nouveaux candidats ou rejouent un calcul identique. |
| **Règle absolue** | Neutralité à l'étape 1 | **Aucune décision de jeu ne change.** Tout le nouveau code est inerte par défaut et gardé sous `C39_INVALIDATION_PROBE` (`probe_catalogue`). |

---

## 1. État du code (vérifié fichier et ligne)

L'inspection exhaustive du code au 2026-09-21 établit l'état suivant :

| Composant | Fichier et lignes | Comportement actuel constaté |
|---|---|---|
| **Cadence catalogue** | [`scheduler_tasks.nut:35-66`](../ai/OpexAI/scheduler_tasks.nut#L35-L66) | `_dispatchCatalog` ne saute que dans le même mois (`_lastCatalogMonth == ym`). Dès qu'un tour de file prend plus de 30 jours, `catalog.refresh` et `_rebuildProjects` s'exécutent **systématiquement**. |
| **Catalogue global** | [`catalog.nut:932-986`](../ai/OpexAI/catalog.nut#L932-L986) | `OpexCatalog::refresh` appelle en bloc `_refreshCargos`, `_refreshRail`, `_refreshTowns`, `_refreshIndustries`, `_refreshRoad`, `_refreshAirport`, `_refreshWater`. Aucun sous-catalogue n'est rafraîchi isolément. |
| **Génération vivier (complet)** | [`projects.nut:2088-2589`](../ai/OpexAI/projects.nut#L2088-L2589) | `OpexBuildProjects` scanne l'ensemble des modes (`rail`, `road`, `air`, `water`, `fleet`), génère tous les candidats, exécute le knapsack/sélection et assemble `candidateGroups` et `best`. Coût : ~2,8 M opcodes par passe. |
| **Rebuild appelant** | [`task_projects.nut:1038-1075`](../ai/OpexAI/task_projects.nut#L1038-L1075) | `_rebuildProjects(fleetPlan)` recalcule l'ordre des frets et appelle `OpexBuildProjects`. |
| **Mise à jour post-chantier** | [`task_projects.nut:980-998`](../ai/OpexAI/task_projects.nut#L980-L998) | Après un chantier réussi, `OpexIncrementalUpdateProjects` filtre les candidats en mémoire (< 1 tick, < 500 opcodes), mais replie sur `_rebuildProjects` complet si le cache est désarmé ou au bootstrap. |
| **Réception d'événements** | [`events.nut:280-357`](../ai/OpexAI/events.nut#L280-L357) | `_processEvents` dépile la boucle d'événements NoAI 15.3 (`AIEventController.GetNextEvent`) et route vers les handlers. |
| **Marquage d'invalidation** | [`events.nut:40-142`](../ai/OpexAI/events.nut#L40-L142) | `_markDirty` est purement passif sous `C39_INVALIDATION_PROBE`. Il incrémente des révisions de diagnostic sous `C41_REVISION_PROBE`, mais **aucun état n'est consommé par les générateurs**. |
| **Handlers d'événements** | [`event_handlers.nut:690-785`](../ai/OpexAI/event_handlers.nut#L690-L785) | `_onIndustryOpen`, `_onIndustryClose`, `_onTownFounded`, `_onEngineAvailable` appellent `_markDirty`. Le seul impact réel est `_portfolioInvalidated = true`, qui **avance** une régénération complète au lieu d'en éviter une. |
| **Garde de sonde** | [`settings.nut:184-188`](../ai/OpexAI/settings.nut#L184-L188) | Le réglage `probe_catalogue` (défaut 0) contrôle `C39_INVALIDATION_PROBE` et `C41_REVISION_PROBE`. Au défaut, le routeur passif ne fait aucun travail. |

---

## 2. Architecture cible (C76 étape 2)

L'architecture cible formalise la séparation stricte entre notification légère, invalidation d'état par couche, et rafraîchissement à la demande.

```text
AIEventController (moteur C++)
       │
       ▼
_processEvents() (routeur NoAI léger, aucun travail lourd)
       │
       ▼
_markDirty(couche, entitéId)
       ├── catalog.<couche>.revision++
       └── dirtySince.<couche> = date
              │
              ▼
Ordonnanceur / Tâches de génération
       │
       ├── Dépendance inchangée (revision == ackRevision) ?
       │      └── SAUTER la régénération du mode (gain : opcodes + jours)
       │
       ├── Dépendance changée (revision > ackRevision) ?
       │      └── Régénération CIBLÉE du mode concerné
       │      └── ackRevision = revision
       │
       └── Filet périodique (reconciliation net)
              └── Actualisation pop/prod mensuelle/annuelle sans recalcul spatial
```

### 2.1 Découpage en sous-catalogues et révisions

Chaque couche conserve deux entiers : `revision` (incrémenté à chaque modification du monde) et `acknowledgedRevision` (mis à jour quand le consommateur a recalculé).

| Couche sous-catalogue | Entités couvertes | Déclencheurs NoAI | Dépendances modales |
|---|---|---|---|
| `catalog.cargos` | Types de fret disponibles, libellés, classes | Début de partie / NewGRF | Tous modes |
| `catalog.towns` | Villes, population, maisons, acceptations | `TownFounded`, croissance urbaine (filet) | `air`, `road_pax`, `rail_pax` |
| `catalog.industries` | Industries productrices et réceptrices | `IndustryOpen`, `IndustryClose` | `rail_freight`, `road_freight`, `water` |
| `catalog.rail` | Types de voies, locomotives, wagons, signaux | `EngineAvailable` (type rail) | `rail` |
| `catalog.road` | Types de route, camions, bus, dépôts | `EngineAvailable` (type route) | `road` |
| `catalog.air` | Types d'avions, caractéristiques aéroports | `EngineAvailable` (type air) | `air` |
| `catalog.water` | Navires, capacités, docks | `EngineAvailable` (type water) | `water` |

### 2.2 Matrice des dépendances modales

Un générateur de candidats ne doit être invoqué que si au moins une de ses couches sources présente `revision > acknowledgedRevision` :

| Famille de candidats | Dépendances strictes (catalogue + réseau) | Déclencheur typique |
|---|---|---|
| `candidates.air` | `catalog.cargos`, `catalog.towns`, `catalog.air`, `lines` | Nouvel avion, ville franchissant seuil aéroport, ligne saturée |
| `candidates.rail_pax` | `catalog.cargos`, `catalog.towns`, `catalog.rail`, `lines` | Nouvelle motrice, fermeture de liaison concurrente |
| `candidates.rail_freight` | `catalog.cargos`, `catalog.industries`, `catalog.rail`, `lines` | Ouverture/fermeture industrie, nouvelle locomotive fret |
| `candidates.road_pax` | `catalog.cargos`, `catalog.towns`, `catalog.road`, `lines` | Nouveau bus, saturation urbaine |
| `candidates.road_freight` | `catalog.cargos`, `catalog.industries`, `catalog.road`, `lines` | Nouvelle industrie courte distance, nouveau camion |
| `candidates.water` | `catalog.cargos`, `catalog.industries`, `catalog.water`, `lines` | Nouveau navire, nouvelle industrie côtière |
| `candidates.fleet` | Lignes existantes (`lines`), matériel du mode concerné | Allongement de file d'attente, avion supplémentaire amortissable |

### 2.3 Filet périodique de réconciliation (obligatoire)

OpenTTD ne génère **aucun événement** pour :
1. L'évolution mensuelle de la population des villes (croissance naturelle ou induite) ;
2. La variation mensuelle de production des industries primaires ;
3. Le vieillissement des convois en service ;
4. Le chargement d'une sauvegarde (la file d'événements est vide à la reprise).

La doctrine architecturale est donc impérativement : **event-driven + periodic reconciliation**, jamais « événements seuls ».
Le filet périodique (ex. annuel ou semestriel) met à jour les grandeurs volumétriques (`pop`, `production`) et réévalue économiquement les candidats existants en mémoire, sans relancer les coûteuses recherches spatiales ou pathfindings d'origine.

---

## 3. Plan d'exécution par étapes

| Étape | Contenu | Type d'évaluation | Règle de décision |
|---|---|---|---|
| **Étape 1** | **Sonde passive C76** (la régénération sert-elle ?) | Journalisation passive sous `probe_catalogue=1` | Mesurer la part de régénérations sans modification de dépendance et la stabilité des candidats. Aucun code de décision modifié. |
| **Étape 2** | **Levier de régénération ciblée** sous réglage (défaut 0) | Régénération conditionnelle par mode + filet | Exécuter `OpexBuildCandidates` seulement si dépendance sale. Vérifier la stricte équivalence économique sous les mêmes événements. |
| **Étape 3** | **Smoke test 2×3** (2 graines, 3 ans) | Validation technique locale | Absence de plantage, conformité opcodes/RAM, intégrité des invariants de file. |
| **Étape 4** | **Banc officiel 20×10 duel** contre AAAHogEx | Décision d'adoption finale | Mesure de valeur de compagnie et de profit en concurrence réelle. |

⚠️ **Rappel méthodologique fondamental :** Le 5×6 solo **ne prédit pas le duel**.
Les retours d'expérience C49 (scarcity), C69 (goulot de décision) et C72 (choix d'avion) ont prouvé que des gains de +100 k£ à +290 k£ en solo s'annulent ou deviennent négatifs en duel : en solo, les aéroports libres et le capital abondent ; en duel, AAAHogEx sature les bassins de ville et capte le profit si la cadence de construction n'est pas coordonnée. Seul le banc 20×10 duel fait foi pour l'adoption.

---

## 4. Critères de passage écrits d'avance pour l'étape 1

L'étape 1 est concluante et autorise le développement de l'étape 2 (levier) si les critères suivants sont satisfaits sur la trace instrumentée (10 ans, graines standard) :

| Identifiant | Métrique | Seuil de validation | Interprétation causale |
|---|---|---|---|
| **C76-C1** | Part des régénérations à dépendances inchangées | **$\ge 50\ \%$** des passes | Plus de la moitié des passes de régénération s'exécutent sans qu'aucun changement structurel (industrie, moteur, ville, ligne) n'ait eu lieu. |
| **C76-C2** | Stabilité des clés de candidats par mode | **$\ge 90\ \%$** de clés identiques | La quasi-totalité des opportunités générées à la passe $N$ étaient déjà présentes à la passe $N-1$. |
| **C76-C3** | Stabilité du premier projet (`best_same_top1`) | **$\ge 75\ \%$** identique | Le projet prioritaire élu par le portefeuille reste inchangé d'une passe à l'autre en l'absence d'événement majeur. |
| **C76-C4** | Jours de jeu récupérables | **$\ge 40$ jours / an** | Le temps passé à reconstruire le catalogue et le vivier représente un gisement exploitable pour accélérer le tour de file. |

Si C76-C1 < 30 % ou C76-C2 < 60 %, le vivier se renouvelle rapidement par la seule dérive économique naturelle ; dans ce cas, sauter la régénération risquerait d'appauvrir le choix de l'IA et la fiche serait close sans levier.

---

## 5. Risques identifiés et ce que le contrat ne fait pas

### 5.1 Risques identifiés

1. **Stagflation par omission** : Si un événement est manqué ou si le filtre NoAI est trop restrictif, un mode peut rester bloqué dans un sous-catalogue obsolète jusqu'au filet périodique.
2. **Fuite mémoire d'objets abandonnés** : Un candidat dont l'industrie source ferme doit être invalidé immédiatement et purgé du vivier en mémoire, sans attendre un rebuild complet.
3. **Désynchronisation multimodale** : Le portefeuille arbitre entre modes (`rail`, `road`, `air`, `water`). Si un seul mode est régénéré avec des coûts actuels pendant que les autres gardent des coûts anciens, le classement peut subir un biais d'âge.

### 5.2 Ce que le contrat ne fait pas

- **Aucune modification du classement** : Le score `P / max(C, F·τ)` ou le ratio `P/C` reste strictement identique.
- **Aucune modification des pathfinders** : AYSTAR rail/road ne reçoit aucun changement d'heuristique ni de profil.
- **Aucune création d'entités en mode test** : La sonde n'appelle aucune primitive modifiant l'état du monde.
- **Aucun contournement du budget NoAI** : Tout calcul de signature reste sous strict plafond d'opcodes.

---

## 6. Synergie avec C77 (candidats opportunistes)

Le chantier **C77** (« déclenchement des candidats opportunistes ») réutilisera directement les briques posées par C76 :
1. **Sous-catalogues indépendants** : Dès réception d'un événement (ex. `IndustryOpen` ou `EngineAvailable`), C77 n'attendra plus le prochain tour de file (~45 jours) ;
2. **Générateurs ciblés** : C77 appellera le générateur ciblé sur l'entité concernée (lignes de l'industrie ouverte, nouveau modèle d'avion) ;
3. **Injection au vivier existant** : Les nouveaux candidats seront insérés directement dans `candidateGroups` et réévalués face au capital disponible pour une construction immédiate.

---

## 6. Résultats de l'étape 1 (2026-09-21)

Sonde passive (agy, relue : tout est gardé par `probe_catalogue` ; la branche de retour ajoutée
dans `OpexBuildProjects` est déjà celle du défaut, `policy_caches=1`). 3 graines × 10 ans, solo,
0 échec : `results/diag_c76_regen_10y_3seeds.json`, analyse `sweeps/analyse_c76_regen.py`
(516 lignes brutes, non versionnées).

**Volume et coût** (3 graines) : 34 à 77 régénérations par an (moitié complètes, moitié
incrémentales), **81 à 100 M opcodes par an**, soit 27 à 33 M par partie. Au taux de C39.6
(~186 k opcodes par jour de jeu), c'est **~145 à 180 jours de jeu par an et par partie** passés
à régénérer le vivier (estimation : le champ jours de la sonde n'a pas été renseigné).

| critère | seuil | mesure | verdict |
|---|---|---|---|
| C76-C1 régénérations sans changement de dépendance | ≥ 50 % | **53 à 76 %** selon l'année | ✅ |
| C76-C2 clés de candidats identiques | ≥ 90 % | air **99,5 à 100 %** ; rail 86 à 96 % (sous 90 % en 1973-1975) | ✅ air, ❌ rail en partie |
| C76-C3 meilleur projet identique | ≥ 75 % | **5 à 35 %** (régénérations complètes seules : 16 à 43 %) | ❌ |
| C76-C4 jours récupérables | ≥ 40 j/an | non mesuré directement ; estimation ~90 à 110 j/an/partie (60 % de ~160 j) | ⚠️ estimé |

**Lecture.**

- Les candidats sont presque toujours les mêmes (air 99,5-100 % des clés), la liste classée aussi
  (88 à 96 % identique à partir de 1972), et la majorité des régénérations ne suit aucun changement
  de ville, d'industrie, de moteur ou de ligne.
- **Mais le meilleur projet change 65 à 95 % du temps**, même sans changement de dépendance. La
  dérive continue suffit : économie aérienne identique à 1 % près pour 70 à 84 % des candidats
  seulement (population, demande, budget). La tête du classement est sensible à des écarts faibles.
  Sauter une régénération changerait donc le projet construit ; on ne sait pas si ce changement
  vaut le temps qu'il coûte.

**Verdict, à la lettre : C3 échoue, l'étape 2 n'est pas autorisée par ce contrat.** C1 et C2 (air)
passent nettement ; C4 est probablement largement atteint mais n'est qu'estimé. Décision
utilisateur requise : fermer, ou réviser C3 (par exemple mesurer si le projet élu après une
régénération « sans changement » rapporte plus que celui qu'on aurait gardé).

**Décision utilisateur du 2026-09-21 : C76 est validé tel quel.** L'étape 2 est autorisée malgré
l'échec de C3 à la lettre. La stabilité du meilleur projet n'est pas un préalable ; l'effet se
jugera au 20×10 en duel.
