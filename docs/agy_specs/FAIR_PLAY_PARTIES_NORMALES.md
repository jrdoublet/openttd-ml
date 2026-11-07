# Spécification Technique — FAIR-PLAY / JOURNAUX-NORMAL (Parties Humaines et Courtoisie)

Date : 2026-11-07  
Branche de travail : `agy-easy` (base `origin/master 7e5ad9d4`)  
Contexte : Prise en compte de la directive du backlog `docs/taches.md:1216` :
> *« Fair-play / parties humaines et sondes normales. Audit V261/V262 et niveaux de difficulté déjà livrés ; définir explicitement une option de courtoisie testée, réduire journaux/panneaux inutiles en partie normale sans changer furtivement probes=2 du défaut compétitif validé. »*

---

## 1. Objectif et critères de succès chiffrés

### 1.1 Constat et problématique
OpexAI a été optimisée de manière intensive pour le banc compétitif headless contre AAAHogEx (cartes carrées générées sans joueur humain). Dans cet environnement, l'instrumentation diagnostic pose des panneaux physiques sur la carte (`AISign.BuildSign`), active des sondes de profiling (`probes=2`, masques de bits dans `settings.nut`), et génère un flux continu d'annonces de décisions (`OpexDecide`).

Lorsqu'un joueur humain charge OpexAI dans une partie normale (solo ou multijoueur OpenTTD) :
1. **Pollution visuelle de la carte :** Des panneaux de diagnostic comme le tableau de budget mensuel sur la tuile `(20, 1)` (`task_report.nut:950-962`), ou les étiquettes de prospection d'aéroports (`probes.nut:40`), polluent l'interface du joueur et consomment la table globale des panneaux OpenTTD (plafonnée à 65 535 signes pour l'ensemble de la carte).
2. **Pollution de la console et des journaux :** Les traces de décisions internes (`DECISION_LOG`, traces de tranches de vivier) saturent les logs sans intérêt pour une partie ludique.
3. **Comportement agressif / anticoncurrentiel :** Bien que le module central `difficulty.nut` ait été introduit pour brider les gestes agressifs selon le niveau de difficulté choisi par l'utilisateur, toutes les options de courtoisie ne sont pas encore reliées à un commutateur explicite pour les parties normales.

### 1.2 Objectif
Définir une option de courtoisie propre et testée (`fair_play_courtesy`, défaut 0), qui, lorsqu'elle est activée (valeur 1) :
- Supprime intégralement la création de panneaux parasites sur la carte (`AISign.BuildSign`).
- Coupe les journaux de diagnostic inutiles en partie normale.
- Active l'ensemble des règles de courtoisie et de fair-play (respect de l'emprise des villes et des gares concurrentes).
- **Préserve strictement le défaut compétitif à 0** : en mode 0 (défaut sur tous les niveaux de difficulté), aucun comportement de banc, aucune sonde `probes=2` ni aucune trace d'arbitrage compétitif n'est altérée.

### 1.3 Critères de succès chiffrés
1. **Nombre de panneaux créés :** Sous `fair_play_courtesy = 1`, `AISign.GetSignCount()` créé par OpexAI $= 0$ (hors éventuel nom d'entreprise ou marqueur de siège social).
2. **Économie d'opcodes :** Suppression des concaténations de chaînes de caractères pour les panneaux et logs $\implies$ gain estimé de **30 000 à 60 000 opcodes par an**.
3. **Invariance stricte du mode compétitif :** Sous `fair_play_courtesy = 0`, identité stricte bit-à-bit du code exécuté et des décisions prises lors des duels contre AAAHogEx.

---

## 2. État du code vérifié dans le worktree

### 2.1 Table centrale des capacités : `ai/OpexAI/difficulty.nut`
- **Lignes 1–17 :**
  ```squirrel
  OPEX_DIFFICULTY <- 2;
  OPEX_LEVEL_LIMITS <- false;
  ```
  Le niveau par défaut est 2 (difficile / hard). Le niveau 3 (custom) est sans bridage. Les niveaux 0 (easy) et 1 (medium) appliquent des limitations.
- **Lignes 26–44 :** Table des fonctionnalités autorisées :
  ```squirrel
  OPEX_DIFFICULTY_MIN_LEVEL <- {
    v250_rights = 3,
    anticompetitive = 3,
    air_joined_road_stops = 2,
    water_depot_dock_front = 3,
    secondary_graft_rival_served = 3,
    preempt_last_airport_slot = 2,
    airport_rival_town = 1,
    compete_primary_industry = 2,
    encroach_rival_catchment = 1
  };
  ```
- **Lignes 47–53 :**
  ```squirrel
  function OpexLevelAllows(feature)
  {
    if (OPEX_DIFFICULTY >= 3) return true;
    if (feature in OPEX_DIFFICULTY_MIN_LEVEL) {
      return OPEX_DIFFICULTY >= OPEX_DIFFICULTY_MIN_LEVEL[feature];
    }
    return true;
  }
  ```

### 2.2 Panneaux de budget sur la carte : `ai/OpexAI/task_report.nut`
- **Lignes 945–964 :**
  ```squirrel
  if (_budgetSignIds == null) _budgetSignIds = {};
  local btText = "OPEX Y" + year + " " + (tot / 1000) + "k";
  if (!("tot" in _budgetSignIds) || !AISign.IsValidSign(_budgetSignIds["tot"])) {
    _budgetSignIds["tot"] <- AISign.BuildSign(AIMap.GetTileIndex(20, 1), btText);
  } else {
    AISign.SetName(_budgetSignIds["tot"], btText);
  }
  local catY = 2;
  foreach (cat, cBudget in _budgets) {
    local bcText = cat + " " + (cBudget.spent / 1000) + "/" + (cBudget.limit / 1000) + "k";
    if (!(cat in _budgetSignIds) || !AISign.IsValidSign(_budgetSignIds[cat])) {
      _budgetSignIds[cat] <- AISign.BuildSign(AIMap.GetTileIndex(20, catY), bcText);
    } else {
      AISign.SetName(_budgetSignIds[cat], bcText);
    }
    catY++;
  }
  ```
  Ce bloc pose jusqu'à 8 à 10 panneaux permanents sur les tuiles `(20, 1)` à `(20, 10)`, visibles en haut à gauche de la carte.

### 2.3 Panneaux de prospection : `ai/OpexAI/probes.nut`
- **Lignes 36–42 :**
  ```squirrel
  function OpexProbeSign(anchor, name)
  {
    if (!PROBES) return;
    AISign.BuildSign(anchor, name);
  }
  ```
  Appelé lors de diagnostics de terrain pour marquer les ancres d'aéroports.

### 2.4 Réglage `probes` et logs : `ai/OpexAI/settings.nut`
- **Lignes 39–72 :**
  `local probes = AIController.GetSetting("probes"); if (probes < 0) probes = 2; PROBES = probes;`  
  `DECISION_LOG = (probes & 508) != 0;`  
  Le masque par défaut `probes=2` est nécessaire au banc compétitif, mais en partie humaine, il active des sondes internes qui n'ont aucune utilité pour le joueur.

---

## 3. Conception proposée

### 3.1 Déclaration du réglage
- **Dans `globals_pre.nut` :**
  ```squirrel
  FAIR_PLAY_COURTESY <- false; // Mode courtoisie pour parties normales/humaines (défaut OFF).
  ```
- **Dans `info.nut` :**
  Ajout du réglage aux quatre difficultés à 0 :
  ```squirrel
  AddSetting({
    name = "fair_play_courtesy",
    description = "Mode courtoisie parties normales : supprime panneaux carte et modere journaux",
    min_value = 0,
    max_value = 1,
    easy_value = 0,
    medium_value = 0,
    hard_value = 0,
    custom_value = 0,
    flags = 0
  });
  ```
- **Dans `settings.nut` (dans les deux chargeurs `OpexLoadSettings` et `OpexLoadSettingsProfiled`) :**
  ```squirrel
  FAIR_PLAY_COURTESY = AIController.GetSetting("fair_play_courtesy") == 1;
  ```

### 3.2 Garde universelle des panneaux sur la carte
Dans `difficulty.nut` (ou helper dédié), définir la fonction d'autorisation :
```squirrel
function OpexSignAllowed(kind)
{
  if (FAIR_PLAY_COURTESY) return false;
  return OpexLevelAllows("debug_signs");
}
```
Dans `task_report.nut:948` :
```squirrel
if (!OpexSignAllowed("budget")) return;
```
Et si `_budgetSignIds` contenait des panneaux précédemment construits (par exemple avant bascule de réglage ou rechargement), les détruire proprement via `AISign.DemolishSign(id)` pour libérer les ressources.

### 3.3 Intégration dans la table `OPEX_DIFFICULTY_MIN_LEVEL`
Ajouter les clés de courtoisie dans `difficulty.nut` :
```squirrel
debug_signs = 2,           // Panneaux sur la carte reserves au mode diagnostic (interdits en facile/moyen)
budget_sign_overlay = 2,   // Panneaux de budget sur (20, 1)
```

### 3.4 Impact sur Save / Load
- `FAIR_PLAY_COURTESY` est un drapeau de configuration relu à chaque démarrage (`OpexLoadSettings`). Il n'a pas besoin d'être persisté dans la sauvegarde de jeu Squirrel.
- Lors du rechargement d'une sauvegarde (`Load`), si `FAIR_PLAY_COURTESY == true`, nettoyer les anciens identifiants de `_budgetSignIds` pour éviter les panneaux orphelins.

---

## 4. Pièges connus et leçons historiques

1. **Ne JAMAIS toucher au défaut de `probes` :**
   La décision utilisateur du 2026-09-30 et du 2026-10-07 a promu `probes=2` comme standard de test compétitif. Toute tentative d'abaisser `probes` par défaut pour "faire propre" ferait échouer les contrats de régression et fausserait la mesure d'arbitrage. `fair_play_courtesy` est un opt-in strictement à 0.
2. **Limite de 31 caractères de l'API NoAI :**
   `AISign.BuildSign(tile, text)` lève une exception fatale ou tronque silencieusement si la chaîne dépasse 31 caractères. En mode compétitif, préserver strictement les décodeurs de signes existants.
3. **Plafond d'AddSetting :**
   L'ajout du réglage `fair_play_courtesy` dans `info.nut` incrémentera le plafond vérifié par `sweeps/test_v251_inventory.py` (de 68 à 69). Le test doit être mis à jour avec justification dans son commentaire.
4. **Pas de `Sleep()` par courtoisie (AGENTS.md §2) :**
   Le guide du dépôt interdit formellement d'ajouter des `Sleep()` "par politesse" envers un joueur humain. Le rythme de jeu d'OpexAI est déjà borné par l'allocation d'opcodes par tick de NoAI. La courtoisie concerne l'espace physique (panneaux, gares, villes) et la propreté des journaux, pas un ralentissement artificiel du CPU.

---

## 5. Plan de test complet

### 5.1 Tests unitaires et de contrat (Hôte Python)
Créer `sweeps/test_fair_play_courtesy.py` :
1. **Contrat des 4 zéros :** Vérifier que `fair_play_courtesy` est déclaré avec `easy_value = 0`, `medium_value = 0`, `hard_value = 0`, `custom_value = 0` dans `info.nut`.
2. **Lecture symétrique des deux chargeurs :** Vérifier que `FAIR_PLAY_COURTESY` est lu à la fois dans `settings.nut` et dans `probes.nut:OpexLoadSettingsProfiled`.
3. **Garde de panneaux :** Tester que les blocs de `task_report.nut` et `probes.nut` sont protégés par la garde.

### 5.2 Smoke test moteur (1 graine × 1 an)
- Lancer un smoke 1×1 avec `fair_play_courtesy=1`.
- Vérifier dans le journal moteur et les métriques de fin d'année que `signs_count == 0`.

### 5.3 Qualification économique
Ce levier étant un opt-in de courtoisie utilisateur (défaut 0), aucune qualification V102 de gain n'est requise pour le modifier tant qu'il reste à 0. S'il devait un jour être proposé pour adoption par défaut, il relèverait de la règle d'optimisation d'opcodes (gain d'opcodes prouvé + non-régression économique 20×10).

---

## 6. Estimation de difficulté et ratio effet / difficulté

| Métrique | Valeur estimée | Justification |
|---|:---:|---|
| **Difficulté de mise en œuvre** | **1.5 / 5** | Modifications isolées dans `task_report.nut`, `settings.nut` et `difficulty.nut`. Aucun calcul mathématique complexe. |
| **Effet opcodes** | $+30\text{ k}$ à $+60\text{ k opcodes/an}$ | Suppression des allocations de chaînes et des appels de signes NoAI mensuels. |
| **Effet confort utilisateur** | **Majeur** | Carte propre pour les parties humaines, suppression des panneaux cryptiques sur la tuile (20, 1). |
| **Ratio Effet / Difficulté** | **Très élevé** | Chantier rapide, sûr, sans risque de régression sur le comportement compétitif. |
