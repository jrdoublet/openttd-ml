# Rapport de Diagnostic EB-5 : Débouchés GOOD Précoces et Chaîne Industrielle

Date : 2026-11-12  
Branche : `agy12-nov12`  
Dépôt : `/home/deploy/projects/wt-agy12`  
Statut : **DIAGNOSTIC SEULEMENT (aucune modification de code dans `ai/`)**  

---

## 1. Contexte et Problématique

La tâche **EB-5** (inscrite dans `docs/taches.md`) vise à comprendre le blocage complet de la chaîne industrielle secondaire Intrant $\to$ Usine $\to$ Marchandises (`GOOD`) dans OpexAI, et à analyser pourquoi **aucun départ ferroviaire de marchandises n'est construit en début de partie (1970–1973)**.

Dans les parties standards 10 ans d'OpexAI contre AAAHogEx :
1. De nombreuses lignes de fret primaire apportent des intrants bruts (`WOOD`, `GRAI`, `LVST`, `OIL_`, `STEL`) aux usines de transformation (Scieries, Usines, Raffineries, Aciéries).
2. Malgré l'arrivée de ces matières premières et la transformation effective en `GOOD`, **0 ligne de sortie de marchandises** n'est construite au défaut en début de partie.
3. L'échec des essais antérieurs (notamment `good_source_rail_join` à −40,7 k£/an) reposait sur une illusion statistique quant au nombre de villes acceptatrices.

Ce rapport fournit une analyse causale et chiffrée, rigoureusement adossée aux résultats et journaux mesurés existants.

---

## 2. Données Sources et Requêtes d'Analyse

Les chiffres et constats présentés dans ce document proviennent directement des artefacts et campagnes archivés :

1. **Campagne 5×10 multimodal (horizon 10 ans) :**
   - Répertoire : `/home/deploy/projects/openttd-ml/.worktrees/v233-devis/results/v233_long_expo_5x10_20261025_engine/`
   - Journaux de parties : `reference_seed42_r0.log`, `reference_seed100_r0.log`, `reference_seed2026_r0.log`, `reference_seed7_r0.log`, `reference_seed999_r0.log`
   - Archive compressée associée : `/home/deploy/projects/openttd-ml/results/v233_long_expo_5x10_20261025.jsonl.gz`
2. **Rapport d'audit préliminaire et script de diagnostic :**
   - `/home/deploy/agy_runs/early/rapport_goodinputs.md` (audit par Antigravity, 27 octobre 2026)
   - `/home/deploy/projects/wt-agy12/results/nuit75_good_capacity_1979_offline.json` (télémétrie des lignes `GOOD` matures)

### Requêtes de reproduction :
- **Audit des sources actives et production mensuelle de `GOOD` :**
  ```bash
  grep "V233_SOURCE" /home/deploy/projects/openttd-ml/.worktrees/v233-devis/results/v233_long_expo_5x10_20261025_engine/reference_seed42_r0.log \
    | grep -E "input_cargo=(WOOD|GRAI|LVST|OIL_|STEL)" \
    | head -n 10
  ```
- **Identification des usines secondaires alimentées par monde :**
  ```bash
  grep "V233_SOURCE" <log_file> | grep -E "input_cargo=(WOOD|GRAI|LVST|OIL_|STEL)" \
    | grep -o "source=[0-9]*" | sort -u
  ```
- **Vérification des lignes ferroviaires de départ `GOOD` construites :**
  ```bash
  grep "RAIL_BUILD" <log_file> | grep "cargo=GOOD"
  # Résultat : 0 occurrence sur l'ensemble des 5 mondes avant 1974.
  ```

---

## 3. Analyse des Sources Actives et Chronologie d'Alimentation

Sur les 5 mondes de la campagne 5×10 de référence, **41 usines secondaires** sont effectivement raccordées et alimentées par les lignes de fret primaire d'OpexAI :

### Répartition par monde des 41 usines alimentées :
- **Graine 100 :** 8 usines (Raffineries 4, 25, 39, 42 ; Usines 5, 17 ; Scieries 2, 43)
- **Graine 2026 :** 11 usines (Scieries 2, 15, 27, 49, 54 ; Usines 5, 41, 47 ; Raffineries 4, 22, 43)
- **Graine 42 :** 6 usines (Scieries 2, 16, 37 ; Usines 5, 28 ; Raffinerie 10)
- **Graine 7 :** 8 usines (Scieries 2, 11, 50 ; Aciérie 37 ; Usines 5, 39 ; Raffineries 4, 18)
- **Graine 999 :** 8 usines (Scieries 45, 46, 50, 52 ; Usines 5, 11, 43 ; Raffineries 33, 40)

### Chronologie d'apparition de la production de `GOOD` :
La production de marchandises à l'usine n'est pas instantanée : elle exige la pose de la voie, l'achat du train, son trajet aller, le chargement à la mine/forêt, le trajet retour, et enfin la conversion mensuelle par le moteur OpenTTD.

| Horizon temporel | Nombre d'usines produisant `GOOD` | % du total (41 usines) | Détail par graine |
|---|:---:|:---:|---|
| **Avant 1972** | **1** | **2,4 %** | Graine 100 uniquement (Raffinerie 4 le 1971-04-19) |
| **Avant 1973** | **4** | **9,8 %** | Graine 100 (1), Graine 2026 (1), Graine 7 (2) |
| **Avant 1974** | **15** | **36,6 %** | 100 (3), 2026 (5), 42 (3), 7 (4), 999 (0) |
| **1974 et après** | **26** | **63,4 %** | Démarrage très tardif (1974, 1975, 1976) |

### Facteurs causaux du retard d'alimentation :
1. **Éviction financière par l'Aérien (1970–1971) :** En mode multimodal, l'aérien capte l'intégralité du capital disponible grâce à ses ROI initiaux écrasants (1 000 à 1 600 contre 300 à 500 pour les intrants ferroviaires). Le rail ne reçoit ses premiers financements d'intrants qu'au printemps/été 1972.
2. **Priorité au Charbon et aux Passagers dans le vivier :** Les lignes de charbon (`COAL`, ROI 800–1 500) et les lignes de passagers denses relèguent les projets d'intrants (`WOOD`, `GRAI`, `LVST`) aux rangs 3 à 6 du portefeuille.
3. **Conflits de site d'implantation (`too_close_no_join`) :** Des sources majeures (ex. Forêt 21920 en graine 42, ROI 1 046) sont rejetées 3 fois consécutives en raison d'interférences de quais avec les stations ou aéroports voisins, obligeant l'IA à se rabattre sur des sources secondaires posées tardivement.

---

## 4. La Réalité Moteur : Seulement 2 à 5 Villes Acceptatrices par Carte

### 4.1 La fausse prémisse de l'analyse initiale
Dans les premières études (notamment `rapport_p5.md`), un décompte naïf du champ `towns=` de `V233_SOURCE` concluait à l'existence de **33 à 41 villes acceptatrices par carte** et de **614 liaisons exploitables**.  
Cette affirmation était fausse : le champ `towns=` listait aveuglément les villes inscrites dans `catalog.townAcceptors[GOOD]`, sans vérifier leur acceptation réelle au sol.

### 4.2 La règle moteur OpenTTD (Climat Tempéré standard)
Dans OpenTTD 15.3, les marchandises (`GOOD`) ne sont acceptées que par les bâtiments commerciaux et industriels denses (immeubles de bureaux, grands magasins). Les maisons résidentielles courantes ont une acceptation nulle ($0/8$). Pour qu'une gare puisse accepter `GOOD`, la somme de captage sur son rayon de desserte doit atteindre **au moins $8/8$ (1 unité pleine)**.

### 4.3 Recensement terrain exact par monde :
Les mesures physiques réelles (relevés moteurs et gares adverses AAAHogEx) établissent les chiffres exacts suivants :

| Graine | Villes Totales | Villes Naïves `towns=` | Villes Acceptant Réellement `GOOD` | Proportion Réelle | Villes Acceptatrices Identifiées |
|:---:|:---:|:---:|:---:|:---:|---|
| **100** | 37 | 34 | **5** | 13,5 % | Sefingbridge, Flonfingley Market, Town_11, Town_13, Town_36 |
| **2026** | 49 | 39 | **3** | 6,1 % | Nunningstone, Sedtown, Sarfingfield |
| **42** | 41 | 33 | **5** | 12,2 % | Danville, Bruston, Linnwell, Nenningville, Safingburg Springs |
| **7** | 46 | 41 | **3** | 6,5 % | Binnway, Fort Betbourne, Saningville |
| **999** | 45 | 40 | **2** | 4,4 % | Satborough Market, Nadborough Bay |
| **TOTAL** | **218** | **187** | **18** | **8,2 %** | **Moyenne : 3,6 villes acceptatrices par carte** |

### 4.4 Débouchés réels dans la plage ferroviaire standard [30, 200] tuiles :
En croisant la position des 41 usines alimentées avec les seules villes acceptant réellement `GOOD` à distance légale :
- **Moyenne :** **1,8 débouché réel par usine** (au lieu de 15 à 25 supposés).
- **Usines orphelines (0 débouché constructible) :**
  - Graine 7 : Scierie 50 (tuile 58909) $\to$ **0 ville acceptatrice à portée**.
  - Graine 999 : Scierie 46, Scierie 45, Raffinerie 33, Raffinerie 40 $\to$ **4 usines sur 10 n'ont aucun débouché**.
  - Alimenter ces usines en intrants ne peut jamais déboucher sur une ligne de sortie de marchandises.

---

## 5. Le Verrou Algorithmique `origin_served`

Même lorsqu'une usine alimentée produit des marchandises et dispose d'une ville acceptatrice réelle à distance optimale, **aucune ligne de sortie n'est jamais construite**.

La cause réside dans le générateur de candidats ferroviaires :
- Dans `ai/OpexAI/candidates.nut` (lignes 1897–1902) :
  ```squirrel
  if ((ss != null && longGood == null) || st != null) {
    if (longGood != null && DECISION_LOG) OpexV233LLog("REJECT", "industry=" + source.id + " town=" + town.id + " reason=destination_served");
    stats.pairsOriginServed++;
    if (townGuardMark != null) { profile.freightTownGuardsOps += OpexOpsMeasureEnd(townGuardMark); profile.freightTownGuardsCalls++; }
    continue;
  }
  ```
- Dans le générateur reprenable `ai/OpexAI/po01c_generators.nut` (lignes 340–345) :
  ```squirrel
  if ((ss != null && longGood == null) || st != null) {
    if (longGood != null && DECISION_LOG) OpexV233LLog("REJECT", "industry=" + source.id + " town=" + town.id + " reason=destination_served");
    stats.pairsOriginServed++;
    if (townGuardMark != null) { profile.freightTownGuardsOps += OpexOpsMeasureEnd(townGuardMark); profile.freightTownGuardsCalls++; }
    continue;
  }
  ```

### Mécanisme du blocage :
1. Pour qu'une usine produise du `GOOD`, une ligne de fret primaire doit y avoir été construite $\implies$ la gare de l'usine existe déjà.
2. `OpexOriginService(lines, source.tile)` renvoie donc un service non nul (`ss != null`).
3. Au réglage par défaut (`longGood == null`, car `V233_LONG_GOOD` est désactivé à 0), la condition `(ss != null && longGood == null)` s'évalue **systématiquement à VRAI**.
4. Le candidat Usine $\to$ Ville est incrémenté dans `stats.pairsOriginServed` et **abandonné immédiatement**.
5. Contrairement à la branche industrie $\to$ industrie (qui bénéficie de l'exception `v179Keep` pour faire converger plusieurs intrants vers une usine), la branche industrie $\to$ ville acceptatrice ne dispose d'**aucune exception** pour autoriser le départ d'un produit transformé depuis une gare existante.

---

## 6. Distinction Capitale : Analyse Dédupliquée EB-8 vs Bug de Production EB-10

Il est indispensable de ne pas confondre le correctif d'analyse statistique **EB-8** et le défaut de logique de jeu **EB-10** :

### 6.1 EB-8 : Correction d'une illusion statistique *offline* (script Python)
- **Contexte :** Lors de la première étude P5, le script d'analyse analysait la chaîne de diagnostic `towns=` et rapportait 614 liaisons exploitables vers 33–41 villes par carte.
- **Intervention EB-8 (commit `f7cff8b3`) :** Le script d'analyse hors-ligne `p5_good_dedup.py` a été corrigé pour croiser les villes listées avec leur acceptation réelle ($A \ge 8$).
- **Résultat :** Révélation que le gisement réel ne comportait que **56 liaisons avant 1974** (réduction de 91 % par rapport aux 614 annoncées), avec seulement 2 à 5 villes acceptatrices par carte.
- **Portée :** EB-8 est un outil de mesure et d'analyse. Il n'a modifié aucun fichier dans `ai/OpexAI/` et n'a eu aucun impact sur le comportement de l'IA en partie.

### 6.2 EB-10 : Véritable défaut de production *in-game* (code Squirrel)
- **Contexte :** Problèmes structurels actifs dans le moteur de décision d'OpexAI :
  1. `ai/OpexAI/catalog.nut:872` :
     ```squirrel
     local acceptance = AITile.GetCargoAcceptance(tile, cargo, 2, 2, this.railCoverage > 0 ? this.railCoverage : 4);
     if (acceptance >= 8 || (pop >= 300 && AICargo.HasCargoClass(cargo, AICargo.CC_EXPRESS))) {
       this.townAcceptors[cargo].append(townObj);
     }
     ```
     Dans OpenTTD, `GOOD` possède la classe `CC_EXPRESS`. La clause `pop >= 300 && HasCargoClass` court-circuitait le test `acceptance >= 8` pour toutes les villes $\ge 300$ habitants. OpexAI tentait donc d'évaluer des débouchés vers des villes qui refusaient physiquement les marchandises !
  2. `ai/OpexAI/lines.nut:254` (`OpexAbandonedPairKey`) :
     La sentinelle `INVALID_INDUSTRY = 65535` renvoyée par OpenTTD pour une ville était comparée par `>= 0`, la traitant à tort comme une industrie valide et corrompant les clés d'abandon de paires.
- **Statut :** EB-10 a été implémenté sous le réglage opt-in `eb10_guards` (défaut 0, commit `e66c523b`).

---

## 7. Proposition de Levier Chiffrée (Sans modification dans `ai/`)

Pour débloquer la filière `GOOD` sans dégrader la rentabilité d'OpexAI, le levier doit agir de manière coordonnée sur le déverrouillage algorithmique et la rentabilité d'insertion :

### 7.1 Levier proposé : `eb5_good_chain_early` (Défaut 0)

1. **Déverrouillage conditionnel de `origin_served` (Sortie GOOD) :**
   Dans `candidates.nut` et `po01c_generators.nut`, autoriser l'émission du candidat si :
   - `cargo == catalog.goodsCargo` (Marchandises) ;
   - La source est une usine secondaire disposant d'une gare existante (`ss != null`) ;
   - La production mensuelle observée est strictement positive (`monthly >= 40 t/mois`) ;
   - La destination est une ville acceptatrice réelle (`acceptance >= 8`, condition garantie par `EB10_GUARDS`) et non encore desservie par le rail (`st == null`).

2. **Bonus d'intrant orienté débouché (`outlet_bonus`) :**
   Lors de l'évaluation d'un projet d'intrant primaire (`WOOD`, `GRAI`, `LVST`, `OIL_`, `STEL`) vers une usine secondaire :
   - Si l'usine dispose d'au moins une ville acceptatrice réelle dans la fenêtre [40, 160] tuiles, appliquer un bonus de rang de **+25 % à +35 %** au projet d'intrant dans `PORTFOLIO_RANK`.
   - Si l'usine n'a aucun débouché réel (cas de 6 usines sur 41), ne pas bonifier le projet.

### 7.2 Chiffrage économique prévisionnel :
- **Capital moyen par ligne de sortie `GOOD` :** ~70 000 £ à 85 000 £ (quai neuf en ville + quai joint ou extension en usine + 1 rame).
- **Recette brute annuelle par ligne mature (distance ~100 tuiles, 60 t/mois) :** ~35 000 £ à 50 000 £/an.
- **Coût d'exploitation annuel d'un train de marchandises :** ~4 500 £/an.
- **Profit net annuel attendu par ligne :** **+30 000 £ à +45 000 £/an** dès la 2e année de mise en service.
- **Gain global attendu à l'horizon 3 ans :** +60 000 £ à +100 000 £/an de `profit_year` par monde (1 à 2 lignes construites dès 1972–1973 au lieu de 0).

### 7.3 Protocole de qualification V102 préenregistré :
- Réglage : `eb5_good_chain_early` (plage 0..1, défaut 0).
- Métrique primaire : `profit_year` OpexAI variante − référence à l'année terminale.
- **Porte A (`gain_short`) :** 40 graines × 3 ans, seuil relatif $\ge 4$ %, Wilcoxon $p < 0{,}05$, IC95 bootstrap borne basse $> 0$, garde de valeur $-5$ %.
- **Porte B (`non_erosion`) :** 20 graines × 10 ans, borne haute IC95 bootstrap $\ge 0$, garde de valeur $-5$ %.
