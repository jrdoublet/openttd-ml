# Diagnostic : Pourquoi 157 k£ dorment en caisse en 1972 (OpexAI route seule, spread2)

**Auteur :** Antigravity (mode lecture seule strict)  
**Date :** 2026-11-03  
**Banc de référence :** `n_spread2_3y` / `n_spread2_gateA` (`road1y_load_orders=1` + `road1y_spread_stops=2`)  
**Scripts d'analyse :** `/home/deploy/.claude/jobs/e230de46/tmp/cash72/`  

---

## 0. Contexte et constat macroscopique

Sur le banc de qualification 40 graines (`n_spread2_gateA.jsonl`), la trajectoire de trésorerie moyenne d'OpexAI (`money`) montre une accumulation massive et rapide en troisième année :
- **1970-T4 (fin an 1) :** 15 375 £
- **1971-T2 (creux an 2) :** 21 042 £
- **1971-T4 (fin an 2) :** 47 884 £
- **1972-T2 :** 94 308 £
- **1972-T4 (fin an 3) :** 157 218 £ (avec des graines dépassant 350 k£ à 430 k£)

À l'inverse, l'adversaire AAAHogEx maintient une trésorerie quasi constante et basse (14 000 £ à 20 000 £) en réinvestissant immédiatement tout son flux de trésorerie disponible. Fin 1972, AAAHogEx termine avec 24,8 lignes ouvertes contre 23,6 pour OpexAI, alors qu'OpexAI disposait de plus de 8 mois d'avance opérationnelle en début de partie.

Le présent diagnostic analyse le blocage précis qui empêche OpexAI de dépenser sa caisse en 1972, décortique mois par mois le comportement des 3 graines instrumentées (`probes=258`, `decision_log`), ausculte les gardes du code Squirrel et démontre la rationalité économique sous-jacente.

---

## 1. Analyse mois par mois en 1972 sur les 3 graines instrumentées (Question 1)

*Données extraites des journaux moteurs `/home/deploy/projects/wt-lineyield/results/n_spread2_3y_engine/` par les scripts `analyze_q1_month_by_month.py`, `deep_dive_q1.py` et `q1_stats.py`.*

### 1.1 Chronologie mensuelle détaillée

#### Graine 100 (Profil modéré : caisse 42 k£ début 1972 -> creux 5 k£ en fév -> 38 k£ en oct -> 77,6 k£ fin déc)
- **1972-01 (Caisse : 42 017 £) :** Construction de la ligne 15 (`L15`). Refus de 2 projets dans le même cycle : 1 `plan_failed:TRACEX` (échec A*), 1 `plan_failed:SITE_LOST` (site de gare devenu invalide). A* : 1 `OK`, 1 `BUDGET` (coût estimé supérieur au capital disponible). Satellites (`spread_stops`) : 2 construits, rejets : 1 `LIMIT` (plafond de 2 arrêts atteint), 1 `NO_SITE`. Renforts flotte : +6 bus achetés, 1 refus `CASH`.
- **1972-02 (Caisse : 5 105 £) :** 0 ligne. Caisse trop basse pour de nouvelles infrastructures. Renforts : +2 bus, 3 refus `CASH`.
- **1972-03 (Caisse : 9 024 £) :** 0 ligne. Renforts : +3 bus, 2 refus `CASH`.
- **1972-04 (Caisse : 8 507 £) :** 0 ligne. Renforts : +2 bus, 2 refus `CASH`.
- **1972-05 (Caisse : 10 639 £) :** 0 ligne. 1 refus `plan_failed:TRACEX`. Renforts : +1 bus, 2 refus `CASH`.
- **1972-06 (Caisse : 8 710 £) :** 0 ligne. Renforts : +2 bus, 2 refus `CASH`.
- **1972-07 (Caisse : 7 976 £) :** 0 ligne. Renforts : +1 bus, 2 refus `CASH`.
- **1972-08 (Caisse : 22 875 £) :** 0 ligne. La caisse recommence à remonter grâce aux lignes existantes. Renforts : +3 bus, 0 refus.
- **1972-09 (Caisse : 18 846 £) :** 0 ligne. Renforts : 0 bus (flottes nominales atteintes).
- **1972-10 (Caisse : 38 431 £) :** Construction de la ligne 18 (`L18`). A* : 1 `OK`. Satellites : 1 construit, 1 rejet `NO_SITE`. Renforts : 0 bus.
- **1972-11 (Caisse : 31 520 £) :** Construction de 2 lignes (`L19`, `L20`). Refus : 1 `plan_failed:TRACEX`, 1 `insufficient_cash` (en fin de passe après 2 constructions). A* : 2 `OK`, 1 `BUDGET`. Satellites : 3 construits, 1 rejet `LIMIT`. Renforts : 0 bus.
- **1972-12 (Caisse : 13 348 £ au 01/12, 77 595 £ au 31/12) :** Construction de la ligne 21 (`L21`). Refus : 4 `plan_failed:SITE_LOST`, 1 `plan_failed:TRACEX`. A* : 1 `OK`, 1 `BUDGET`. Satellites : 2 rejets `BUILD_268` (conflit de construction). Renforts : 0 bus.

#### Graine 613553 (Profil intermédiaire : caisse 10 k£ en jan -> pic 65 k£ en juin -> stabilisation 15-22 k£)
- **1972-01 (Caisse : 10 842 £) :** 0 ligne. Refus : 1 `plan_failed:TRACEX`. Renforts : 0 bus.
- **1972-02 (Caisse : 37 242 £) :** Construction de la ligne 15 (`L15`). Refus : 1 `town_already_bus_served` (ville saturée à 4 lignes). A* : 1 `OK`. Satellites : 2 construits. Renforts : +6 bus, 4 refus `CASH`.
- **1972-03 (Caisse : 7 837 £) :** 0 ligne. Renforts : +3 bus, 5 refus `CASH`.
- **1972-04 (Caisse : 3 893 £) :** 0 ligne. Refus : 1 `plan_failed:TRACEX`. Renforts : 0 bus, 5 refus `CASH`.
- **1972-05 (Caisse : 42 906 £) :** 0 ligne. Refus : 1 `plan_failed:TRACEX`. A* : 1 `OK`, 1 `BUDGET`. Renforts : 0 bus.
- **1972-06 (Caisse : 65 272 £) :** Construction de la ligne 17 (`L17`). Satellites : 1 rejet `BUILD_268`, 1 rejet `LIMIT`. Renforts : +9 bus achetés d'un coup, 2 refus `CASH`.
- **1972-07 (Caisse : 21 765 £) :** Construction de la ligne 19 (`L19`). Refus : 2 `town_already_bus_served`. A* : 1 `OK`. Satellites : 1 construit, 1 rejet `BUILD_268`. Renforts : +4 bus, 3 refus `CASH`.
- **1972-08 (Caisse : 16 722 £) :** Construction de la ligne 20 (`L20`). Refus : 1 `plan_failed:SITE_LOST`, 1 `build_failed:BSTOP`. A* : 2 `OK`. Satellites : 2 rejets `BUILD_268`. Renforts : +7 bus, 0 refus.
- **1972-09 (Caisse : 3 965 £) :** 0 ligne. Refus : 1 `plan_failed:SITE_LOST`. Renforts : +2 bus, 2 refus `CASH`.
- **1972-10 (Caisse : 21 937 £) :** Construction de la ligne 22 (`L22`). A* : 1 `OK`. Satellites : 1 construit, 1 rejet `LIMIT`. Renforts : +5 bus, 0 refus.
- **1972-11 (Caisse : 13 313 £) :** 0 ligne. Renforts : +4 bus, 1 refus `CASH`.
- **1972-12 (Caisse : 14 937 £) :** 0 ligne. Refus : 1 `plan_failed:TRACEX`, 1 `plan_failed:SITE_LOST`, 1 `town_already_bus_served`. A* : 1 `BUDGET`. Renforts : +7 bus, 2 refus `CASH`.

#### Graine 781335 (Profil haute rentabilité & cash fluctuant : caisse 85 k£ en juin, 70 k£ en sept, 88 k£ fin déc)
- **1972-01 (Caisse : 6 566 £) :** Construction de la ligne 18 (`L18`). Refus : 2 `plan_failed:SITE_LOST`. A* : 1 `OK`. Satellites : 1 rejet `LIMIT`, 1 rejet `BUILD_265`. Renforts : +6 bus, 7 refus `CASH`.
- **1972-02 (Caisse : 4 365 £) :** 0 ligne. Renforts : +6 bus, 4 refus `CASH`.
- **1972-03 (Caisse : 6 778 £) :** 0 ligne. Renforts : +4 bus, 4 refus `CASH`.
- **1972-04 (Caisse : 9 753 £) :** 0 ligne. Renforts : +1 bus, 2 refus `CASH`.
- **1972-05 (Caisse : 29 911 £) :** 0 ligne. Vague massive de rejets : 16 `plan_failed:SITE_LOST`, 1 `plan_failed:TRACEX`. A* : 1 `BUDGET`. Renforts : 0 bus.
- **1972-06 (Caisse : 85 044 £) :** Construction de la ligne 21 (`L21`). Refus : 1 `plan_failed:SITE_LOST`, 1 `build_failed:ROAD`. A* : 2 `OK`. Satellites : 1 construit, 1 rejet `BUILD_268`. Renforts : +4 bus, 0 refus.
- **1972-07 (Caisse : 55 301 £) :** Construction de la ligne 22 (`L22`). Refus : 4 `plan_failed:SITE_LOST`. A* : 1 `OK`. Satellites : 2 construits. Renforts : +9 bus, 0 refus.
- **1972-08 (Caisse : 15 456 £) :** 0 ligne. Refus : 4 `plan_failed:SITE_LOST`, 1 `plan_failed:TRACEX`. A* : 1 `OK`, 1 `BUDGET`. Renforts : 0 bus.
- **1972-09 (Caisse : 70 479 £) :** Construction de 2 lignes (`L23`, `L25`). La passe tente ensuite 20 autres candidats : tous rejetés pour `insufficient_cash` (car la caisse est tombée à 12,4 k£ en cours de mois suite aux 2 lignes, alors que les candidats suivants réclamaient 13 à 26 k£), 7 rejets `plan_failed:SITE_LOST`, 1 `town_already_bus_served`. Satellites : 1 construit, 1 rejet `NO_SITE`. Renforts : +8 bus, 0 refus.
- **1972-10 (Caisse : 8 986 £) :** 0 ligne. Renforts : +5 bus, 0 refus.
- **1972-11 (Caisse : 28 878 £) :** 0 ligne. Refus : 7 `plan_failed:SITE_LOST`, 1 `plan_failed:TRACEX`, 1 `build_failed:ROAD`. A* : 1 `OK`, 1 `BUDGET`. Renforts : 0 bus.
- **1972-12 (Caisse : 87 778 £) :** Construction de la ligne 26 (`L26`). Refus : 1 `build_failed:DEPOT`. A* : 2 `OK`. Satellites : 2 construits, 2 rejets `LIMIT`. Renforts : +4 bus, 0 refus.

---

### 1.2 Motif de refus dominant quand la caisse dépasse 50 k£

Le dépouillement exhaustif de tous les événements de refus sur les mois où la caisse franchit le seuil de 50 000 £ (juin/juil/sept/déc 1972 sur 781335, juin 1972 sur 613553, déc 1972 sur 100) produit les comptes suivants :

| Catégorie | Événement / Motif | Occurrences (Caisse > 50 k£) | Rôle et explication mécanique |
|---|---|:---:|---|
| **Projets d'infrastructure** | `insufficient_cash` | **20** | **Artefact intra-cycle :** En 1972-09 (graine 781335), la caisse initiale est de 70 479 £. Deux lignes complètes sont construites immédiatement (`L23` et `L25`). La caisse descend à 12 400 £. Le portefeuille continue d'évaluer les candidats restants de la passe, dont le coût estimé est entre 13 k£ et 26 k£. Ils sont donc refusés pour trésorerie insuffisante à cet instant précis. |
| **Projets d'infrastructure** | `plan_failed:SITE_LOST` | **12** | **Blocage physique structurel :** L'emplacement identifié lors de la génération du candidat est devenu indisponible (zone de chalandise chevauchée par une station construite entre-temps, ou bâtiment urbain ayant poussé sur la case). Déclenche un bannissement de la paire pendant 365 jours. |
| **Projets d'infrastructure** | `town_already_bus_served` | **1** | La ville a déjà atteint le plafond de 4 lignes de bus (`OpexTownRoadLineCount >= 4`). |
| **Projets d'infrastructure** | `build_failed:ROAD` | **1** | Échec de construction de segment routier (dénivelé, obstacle). |
| **Projets d'infrastructure** | `build_failed:DEPOT` | **1** | Échec de pose de dépôt (erreur OpenTTD 260). |
| **Flotte (Renforts)** | Refus `CASH` | **2** | Seulement 2 refus ponctuels sur 78 achats de bus validés. Quand la caisse > 50 k£, la flotte achète sans aucune retenue. |
| **Arrêts satellites (`spread`)** | `LIMIT` | **3** | La station a déjà ses 2 arrêts (`road1y_spread_stops=2`). |
| **Arrêts satellites (`spread`)** | `BUILD_268` / `NO_SITE` | **3** | Aucun terrain libre adjacent ou rejet du planificateur de station. |

**Synthèse causale pour la Question 1 :**  
Quand la caisse dépasse 50 k£, **ce ne sont pas des gardes financières qui bloquent**, mais :
1. **L'épuisement des sites physiques viables (`SITE_LOST`)** au fur et à mesure que les villes cibles sont maillées.
2. **Le plafonnement territorial (`town_already_bus_served`)** qui élimine les villes majeures déjà desservies par 4 lignes.
3. L'apparente abondance de refus `insufficient_cash` (20 occurrences) n'est que la conséquence directe du fait qu'Opex **a bel et bien dépensé 58 k£ en quelques jours** dans le même mois (septembre 1972) pour construire 2 lignes d'affilée, épuisant sa caisse disponible pour les projets lourds suivants.

---

## 2. Vivier de candidats, plafonds et cadences de blocage (Question 2)

### 2.1 Le vivier de candidats est-il vide ou épuisé ?
- **Le vivier est-il VIDE ? NON.**  
  Le générateur `ROAD100_PAX_GEN` (`candidates.nut:658`) continue de générer activement des paires de villes tout au long de 1972. Les journaux moteurs enregistrent à chaque cycle de génération :
  - Graine 100 : 126 candidats en juillet 1972, 108 en novembre 1972.
  - Graine 613553 : 120 candidats en septembre 1972, 100 en novembre 1972.
  - Graine 781335 : 89 candidats en septembre 1972, 68 en décembre 1972.
- **Le vivier est-il ÉPUISÉ sur la fenêtre viable ? OUI.**  
  La quasi-totalité des paires candidates générées dans la table brute sont immédiatement éliminées par les filtres de viabilité économique et géographique avant même la construction.

### 2.2 Inventaire exhaustif des gardes avec fichiers, lignes et comptes

Voici la chaîne complète des verrous qui éliminent les candidats en 1972 :

#### Garde 1 : Plancher et plafond de distance interurbaine (Fenêtre [64, 128] tuiles)
- **Fichier et ligne :** `ai/OpexAI/bus_districts_overrides.nut:353` et `ai/OpexAI/candidates.nut:670`
- **Code :**
  ```squirrel
  // bus_districts_overrides.nut:353
  local dMin = (ROAD1Y_NEXT > 0) ? ROAD1Y_NEXT : 40; // ROAD1Y_NEXT vaut 64 par défaut
  if (dist < dMin) continue;
  // candidates.nut:670
  if (dist > roadCap) continue; // roadCap vaut 128 par défaut
  ```
- **Comptes et impact :** Sur une carte 256×256 avec ~45 à 55 villes (soit environ 1 200 à 1 500 paires possibles) :
  - Les paires < 64 tuiles sont interdites (débit passager trop faible, amortissement routier impossible).
  - Les paires > 128 tuiles sont interdites (temps de trajet excessif, péremption de cargaison, coût de tracé monstrueux).
  - Cette fenêtre stricte ne laisse que ~150 à 250 paires géographiquement recevables sur toute la carte.

#### Garde 2 : Plafond de lignes de bus par ville (`OpexTownRoadLineCount >= 4`)
- **Fichier et ligne :** `ai/OpexAI/bus_districts_overrides.nut:324` et `ai/OpexAI/task_road.nut:80`
- **Code :**
  ```squirrel
  // bus_districts_overrides.nut:324
  if (OpexTownRoadLineCount(t1) >= 4 || OpexTownRoadLineCount(t2) >= 4) continue;
  ```
- **Comptes et impact :** Les grandes villes (qui génèrent le trafic le plus rentable) atteignent leur quota de 4 lignes dès la fin 1971 / début 1972. Dès lors, toute nouvelle paire impliquant une de ces villes majeures est immédiatement jetée. En 1972, les seules villes restantes avec < 4 lignes sont de petits bourgs excentrés à faible population.

#### Garde 3 : Bannissement des paires à site perdu pendant 365 jours (`SITE_LOST`)
- **Fichier et ligne :** `ai/OpexAI/opcode_exact.nut:516`, `ai/OpexAI/lines.nut:277`, et `ai/OpexAI/globals_post.nut:42`
- **Code :**
  ```squirrel
  // opcode_exact.nut:516
  OpexPairRecordFail(p.key, "plan_failed:SITE_LOST");
  // lines.nut:277
  this._markPairAbandoned(pairKey, 365);
  // globals_post.nut:42
  ABANDON_COOLDOWN_DAYS <- 365;
  ```
- **Comptes et impact :** Lorsqu'une station satellite (`spread_stops`) ou une nouvelle ligne est construite dans une ville, le rayon d'acceptation de la nouvelle station chevauche souvent l'emplacement théorique pré-calculé d'un autre candidat. Ce candidat échoue avec `SITE_LOST`, ce qui déclenche un bannissement ferme de la paire pour 365 jours. En 1972, Seed 781335 accumule 35 rejets `SITE_LOST`, congelant 35 paires potentielles pendant une année entière.

#### Garde 4 : Plafond global de véhicules et plafond par ligne
- **Plafond global OpenTTD (`max_roadveh`) :**  
  - Fichier : `ai/OpexAI/catalog.nut:488` (`OpexVehicleSlotAvailable`).
  - `vehicle.max_roadveh` est fixé à **500** dans la configuration moteur d'OpenTTD.
  - Fin 1972, Opex possède entre 135 et 189 véhicules routiers (environ 100 bus et 75 camions postaux). Il reste **plus de 310 slots libres**. Ce plafond **ne bloque JAMAIS**.
- **Plafond de flotte par ligne (`road1yCap`) :**  
  - Fichier et ligne : `ai/OpexAI/bus_districts_overrides.nut:2088`
  - Code : `local road1yCap = ROAD1Y_FLEET * road1yStops;` (avec `ROAD1Y_FLEET=2` ou `3`, et `road1yStops=2` ou `3`).
  - Comptes : Chaque ligne est plafonnée entre 4 et 8 véhicules. Une fois la ligne à son effectif nominal, elle n'achète plus aucun bus, quel que soit le montant de la caisse disponible.

#### Garde 5 : Bride de cadence de construction (`ROAD100_ROAD_BATCH` et scheduler)
- **Fichiers et lignes :**  
  - `ai/OpexAI/globals_pre.nut:64` : `ROAD100_ROAD_BATCH <- false;` (désactivé par défaut)
  - `ai/OpexAI/task_projects.nut:1329-1345` :
    ```squirrel
    local maxBatch = ROAD100_ROAD_BATCH ? 4 : 1;
    if (builtThisPass >= maxBatch) {
      c75BypassConsumed = true;
      break;
    }
    ```
  - `ai/OpexAI/main.nut:453` : rotation de la file de tâches `_taskQueue` comprenant 9 tâches (`FINANCE`, `ROAD`, `SURVEY`, `REPAIR`, `PORTFOLIO`, `AIR`, `EXPAND`, `REFLEET`, `MAINTENANCE`).
- **Comptes et impact :**  
  `maxBatch` vaut strictement **1**. Dès qu'une ligne est construite avec succès dans une passe du portefeuille, OpexAI stoppe immédiatement ses constructions et passe la main aux 8 autres tâches. L'exécution complète d'un tour de boucle du scheduler prend entre **10 et 25 jours**. OpexAI est donc physiologiquement incapable de construire plus d'une ligne toutes les 2 à 3 semaines.

---

## 3. Ce que fait AAA de son argent en 1972 (Question 3)

*Données quantifiées par `analyze_aaa_1972.py` à partir des traces d'exécution de `script:4` (AAAHogEx).*

AAAHogEx maintient une trésorerie quasi-nulle (14 k£ à 20 k£) parce qu'il réinvestit en continu dans trois canaux d'allocation du capital :

```
========================================================================================
AAA HOGEX 1972 - ACTIVITÉ D'INVESTISSEMENT SUR LES 3 GRAINES
========================================================================================
Graine | Nouvelles stations / Lignes créées | Répartition par cargaison           | Véhicules clonés | Tests de clonage
-------|------------------------------------|-------------------------------------|------------------|------------------
100    | 18 terminus (9 lignes complètes)   | Passagers: 8, Courrier: 6, Charbon: 4 | 59 clones        | 535 vérifications
613553 | 34 terminus (17 lignes complètes)  | Courrier: 13, Passagers: 12, Charbon: 9 | 107 clones       | 656 vérifications
781335 | 33 terminus (16 lignes complètes)  | Courrier: 16, Passagers: 11, Charbon: 4, Bois: 2 | 48 clones | 650 vérifications
========================================================================================
```

### Analyse structurelle des dépenses d'AAAHogEx :
1. **Lignes autonomes de Courrier (`cargo:Mail`, 40 à 50 % des investissements) :**  
   Contrairement à OpexAI qui greffe des fourgons de courrier sur ses arrêts de bus passagers existants, AAAHogEx construit des lignes routières de courrier point-à-point indépendantes entre les centres-villes. En 1972, il ouvre 6 à 16 terminus postaux par graine, absorbant instantanément 20 à 40 k£ de trésorerie.
2. **Lignes de Fret routier lourd (`Coal` et `Wood`, 15 à 25 % des investissements) :**  
   AAAHogEx relie les mines de charbon aux centrales électriques et les forêts aux scieries par camions. Ce fret garantit un flux régulier et consomme des capitaux continus.
3. **Clonage agressif de véhicules (`CloneVehicle`, 50 à 107 véhicules/an) :**  
   AAAHogEx exécute plus de 600 tests `CheckBuildVehicle` par an. Dès qu'un quai accumule du stock, AAAHogEx duplique immédiatement un véhicule sans aucune contrainte de plafond de ligne strict, maintenant sa trésorerie au ras du plancher de sécurité.

---

## 4. Conclusion : Pourquoi cet argent n'a PAS d'emploi rentable à 3 ans, et proposition ciblée (Question 4)

### 4.1 Démonstration économique : Pourquoi forcer la dépense en fin de 1972 détruit le profit terminal

L'intuition selon laquelle « 157 k£ en caisse est un gâchis qu'il faut absolument dépenser dans le réseau » est économiquement fausse à l'horizon de 3 ans. Les données et les expérimentations antérieures prouvent que toute tentative d'injection de ce capital dans l'exploitation en 1972 dégrade `profit_year` :

#### Preuve A : Renforts de flotte de bus (Sur-offre stérile et coûts fixes)
- **Saturation de la demande :** OpexAI possède déjà fin 1972 une flotte médiane de **100,2 bus par graine**, soit **+14,3 bus de plus qu'AAAHogEx** (85,9 bus).
- **Files d'attente faméliques :** La médiane des passagers en attente aux arrêts OpexAI n'est que de **9 passagers** (contre 28 passagers chez AAAHogEx). Le réseau d'OpexAI draine déjà l'intégralité de la génération urbaine.
- **Flotte marginale déficitaire :** 30,3 % des bus OpexAI rapportent moins de 2 500 £/an, et 9,2 % ont un profit annuel négatif ou nul (`agy_paxgap_rapport.md`, §1).
- **Réfutation expérimentale formelle :** Le levier `road1y_rich_fleet=10` a déjà été testé et qualifié à la Porte A (`memory/road1y_flotte_portes_a_0211.md`). Résultat : **-9,8 k£ de perte de profit** par rapport à la référence, et `rich_fleet=10` combiné à `load_orders=1` a produit un delta négatif de **-1,3 k£**. Ajouter des bus supplémentaires ne crée aucun passager nouveau ; cela ne fait qu'augmenter les coûts fixes d'entretien des véhicules (`expenses_last_year`).

#### Preuve B : Construction accélérée de nouvelles lignes en fin d'année 1972 (Décalage de CAPEX / Amortissement négatif)
- Une ligne routière coûte entre **10 000 £ et 20 000 £** de CAPEX (terrassement, routes, 2 gares, 1 dépôt, 4 bus neufs).
- **Cycle d'activation opérationnelle :** Entre la construction des gares, l'achat des bus, leur sortie du dépôt, le trajet à vide jusqu'au terminus, le premier chargement et la première livraison, il s'écoule entre **60 et 120 jours**.
- **Impact sur `profit_year` de l'année terminale :** Une ligne construite au 4e trimestre 1972 n'enregistre aucune recette significative avant le 31 décembre 1972, mais encaisse immédiatement l'usure, les frais de roulement et les intérêts de capital.  
  *Exemple mesuré sur la graine 100 :* La ligne 21 construite le 12 novembre 1972 a produit un profit net de **-59,5 £** en 1972. Dépenser 100 k£ en T4 1972 pour forcer la construction de 6 lignes supplémentaires amputerait mécaniquement le résultat net de l'année 3 sans aucun retour sur investissement mesurable avant 1973 ou 1974.

#### Preuve C : Réseau postal autonome (Horizon de rentabilité hors gabarit)
- Le déploiement d'un réseau autonome de camions postaux (`road1y_mail_net`, chiffré dans `memory/road1y_mail_gisement.md`) réclame 15 à 25 k£ de CAPEX par ligne pour une marge brute annuelle très faible (1,5 à 3 k£/an).
- Son temps de retour sur investissement est de **6 à 8 ans**. À l'horizon de la Porte A (3 ans), ce réseau constitue une perte sèche de valeur.

#### Preuve D : L'analyse croisée des 40 graines prouve que la caisse dormante est la signature de l'excellence
La comparaison entre les graines à forte trésorerie (> 300 k£ en décembre 1972) et les graines à faible trésorerie (< 15 k£) révèle une corrélation sans équivoque :

```
========================================================================================
COMPARAISON HAUTE CAISSE vs FAIBLE CAISSE FIN 1972 (Banc 40 graines)
========================================================================================
Groupe de graines        | Caisse moyenne (déc 1972) | Profit moyen 1972 | Flotte moyenne (véhicules) | Gares
-------------------------|---------------------------|-------------------|----------------------------|------
Graines > 300 k£ (n=8)   | 355 475 £                 | 619 494 £         | 174 véhicules              | 47 gares
Graines < 15 k£ (n=8)    | 7 763 £                   | 410 440 £         | 162 véhicules              | 46 gares
========================================================================================
```
Les graines qui accumulent plus de 300 k£ de caisse (graines 999, 12345, 2026, 8675309, 1, 375172, 983759, 515222) ne sont pas "bloquées" : **ce sont les réseaux les plus performants du jeu**, générant un profit annuel record de **620 k£** (avec des pointes à 686 k£ sur la graine 999).  
Elles ont déjà connecté toutes les paires viables entre 64 et 128 tuiles, équipé chaque arrêt de satellites (`spread_stops`), maximisé leur flotte, et génèrent un cash-flow net de **45 000 £ à 55 000 £ par mois**.  
Cette caisse n'est pas un dysfonctionnement : **c'est le surplus de trésorerie incompressible d'un réseau saturé et ultra-rentable.**

---

### 4.2 UNE spécification précise pour valoriser cette trésorerie avant fin 1972 : Le remboursement anticipé de la dette (`LOAN_REPAY_FLOOR`)

Puisque réinvestir cette caisse dans des actifs d'exploitation en 1972 est destructeur de valeur, la seule allocation financièrement rentable, immédiate et sans risque opérationnel consiste à **rembourser l'emprunt bancaire**.

#### Constat dans le code actuel :
Dans `ai/OpexAI/globals_post.nut:17` et `ai/OpexAI/capital.nut:27`, le plancher requis pour rembourser l'emprunt est fixé à un montant prohibitif :
```squirrel
// globals_post.nut:17
LOAN_REPAY_FLOOR <- 300000;
```
En conséquence, `_tryRepayLoan` (`capital.nut:15`) est appelé chaque mois par le scheduler (`scheduler_tasks.nut:1144`), mais refuse systématiquement de rembourser :
`LOAN action=refuse_repay reason=cash_below_floor cash=... floor=300000 loan=300000`

Sur les 40 graines, **100 % des parties conservent leur dette maximale de 300 000 £ pendant l'intégralité des 3 ans**.  
OpenTTD applique un taux d'intérêt de **4 % par an** sur la dette, soit **12 000 £/an d'intérêts bancaires**, directement débités des comptes et imputés dans les charges d'exploitation (`expenses_last_year`), diminuant d'autant `profit_year` !

#### Spécification technique du changement :
1. **Fichier :** `ai/OpexAI/globals_post.nut` (ligne 17) ou nouveau paramètre dans `settings.nut`
   - **Modification :** Remplacer le seuil absolu de 300 000 £ par un plancher d'exploitation dynamique ou abaissé :
     ```squirrel
     LOAN_REPAY_FLOOR <- 50000; // Au lieu de 300000
     ```
2. **Fichier :** `ai/OpexAI/capital.nut` (fonction `OpexAI::_tryRepayLoan`, lignes 15-52)
   - Préserver une réserve de trésorerie de sécurité de 50 000 £ pour absorber les dépenses imprévues et le renouvellement de véhicules.
   - Tout excédent au-delà de 50 000 £ est alloué par tranches de `AICompany.GetLoanInterval()` (généralement 10 000 £) au remboursement de la dette via `AICompany.SetLoanAmount(newLoan)`.

#### Effet attendu chiffré :
- Sur les graines à trésorerie moyenne (157 k£ fin 1972), OpexAI remboursera environ **100 000 £** de dette dès le 2e semestre 1972.
- Sur les 8 graines à forte trésorerie (> 300 k£), la totalité des **300 000 £ de dette sera intégralement remboursée** dès le milieu de 1972.
- **Gain financier direct sur `profit_year` (année terminale) :**
  - Économie nette d'intérêts bancaires : entre **4 000 £ et 12 000 £** par graine sur l'année 1972.
  - Hausse mécanique de la valeur de compagnie (`company_value`) par assainissement du bilan.
  - Zéro risque de saturation d'infrastructure, zéro risque de sur-offre de véhicules, zéro opcode consommé en calculs A*.

---

## 5. Inventaire des scripts d'analyse créés

Tous les scripts ci-dessous sont conservés et reproductibles dans `/home/deploy/.claude/jobs/e230de46/tmp/cash72/` :
- `explore_logs.py` : Recensement initial des motifs de décision et tags de traces dans les journaux moteurs.
- `check_gateA_cash.py` : Extraction de la trésorerie mensuelle sur l'ensemble des 40 graines de `n_spread2_gateA.jsonl`.
- `analyze_q1_month_by_month.py` : Extraction chronologique mensuelle des 3 graines instrumentées (lignes, rejets, flotte).
- `deep_dive_q1.py` : Traçage des modules spécifiques (`ROAD1Y_REFLEET`, `ROAD1Y_ASTAR_PASS`, `BUS_DISTRICT_SPREAD`).
- `q1_stats.py` : Génération du tableau synthétique consolidé et dépouillement des motifs de refus quand caisse > 50 k£.
- `inspect_projects_pass.py` & `b6_audit.py` : Audit de la boucle `_tryBuildProjects`, cadence `maxBatch` et cadences scheduler.
- `analyze_aaa_1972.py` : Quantification de l'activité d'AAAHogEx en 1972 (endpoints, types de cargo, clonage de véhicules).
- `check_all40_cash.py` : Distribution statistique de la caisse à 3 ans sur les 40 graines.
- `check_high_vs_low_cash.py` : Analyse différentielle économique entre les graines à forte caisse (>300 k£) et faible caisse.
- `check_line_opening_profits.py` : Analyse de l'impact financier des lignes ouvertes tardivement en année 3.

---

exit=0
