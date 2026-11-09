# Spécification Technique — LATE-GAME-1 / V249 / V251 (Excédent de Caisse Tardif)

## 1. Objectif et critère de succès chiffré

- **Constat économique :** En 1979 (année terminale 10), OpexAI accumule couramment **~14,74 M£ de trésorerie oisive**, avec un emprunt intégralement remboursé (`AICompany.GetLoanAmount() == 0`). Cette caisse dormante ne contribue ni au profit annuel, ni à l'accélération de la valeur de compagnie une fois le catalogue de projets initiaux saturé.
- **Objectif :** Réinvestir intelligemment cette trésorerie excédentaire tardive dans des leviers productifs ciblés lorsque tous les projets primaires de transport sont construits, sans cannibaliser le renouvellement de flotte V252 ni dégrader la valeur de compagnie.
- **Critère de succès chiffré :**
  - **Delta profit terminal (Année 10) :** $\ge +50\text{ k£/an}$ par rapport au défaut de référence.
  - **Garde de valeur :** Ratio de valeur de compagnie OpexAI variante / référence $\ge 0{,}95$ (perte maximale autorisée $\le -5\%$).
  - **Prérequis documentaire strict (Décision du 26/10, `docs/journaux/journal_2026-10-30_transfert_taches.md:710`) :** Le déverrouillage de tout code d'achat ou d'action tardive exige au préalable la documentation de la parité OpexAI $\ge 100\%$ du profit d'AAAHogEx à 5 ans sur les 48 cellules de la matrice (4 dates $\times$ 4 modes $\times$ 3 tailles de carte).

---

## 2. État du code vérifié dans le worktree

- **`ai/OpexAI/globals_pre.nut:245-256` :**
  - Ligne 246 : `V249_STATUE <- 2;` (Défaut actif en mode 2 V249a+b+c depuis le 21/10).
  - Ligne 249 : `V249_CASH_STOP <- true;` (Drapeau d'arrêt sur caisse insuffisante).
- **`ai/OpexAI/task_v249.nut` :**
  - Ligne 235 : `function OpexV249DispatchMode2(ai, ym, year)` — calcul du gain marginal annuel capturable sur les stations desservies ayant une capacité résiduelle (`spareCapacity > 0`).
  - Lignes 441-451 :
    ```squirrel
    local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    local bestProjCap = OpexV249BestAdmissibleCapital(ai._projects, ai._lines, cash);
    local v252Cost = OpexV249GetPendingV252Cost(ai);
    local threshold = bestProjCap + v252Cost;
    if ((ESTIM_UNIFIE & 2) != 0) threshold = 0;
    if (cost <= 0 || cash - cost < threshold) { ... return true; }
    ```
  - Lignes 463-485 : `OpexAI::_dispatchV249Statue(task, year)` :
    - Vérifie `if (!V249_STATUE) return false;`
    - Vérifie `loan > 0` $\implies$ skip (`reason=loan`).
    - Vérifie `cashStop` $\implies$ skip (`reason=cash_stop`).
    - Exécute `OpexV249DispatchMode2(this, ym, year);`.
- **`ai/OpexAI/probes.nut:213-255` :**
  - `OpexV251LogIndustryTypes()` : inventaire en lecture seule des types d'industries finançables via `AIIndustryType.CanBuildIndustry(type)` et `AIIndustryType.CanProspectIndustry(type)` avec `AIIndustryType.GetConstructionCost(type)`.
- **`ai/OpexAI/scheduler.nut:404` :**
  - `ranTask = this._dispatchV249Statue(task, year);` (Appelé mensuellement dans la boucle d'ordonnancement).
- **`ai/OpexAI/task_projects.nut:1067` :**
  - `if (V249_STATUE && c75StopReason == "cash") ::V249_CASH_STOP = true;`

---

## 3. Conception proposée

### Architecture du module `task_late_game.nut`
Créer un sous-module ou étendre `task_v249.nut` derrière un réglage paramétrable :
- **Réglage :** `late_game_policy` dans `info.nut` (4 niveaux de difficulté à 0, défaut 0).
  - `0` : OFF (comportement master actuel, V249 statue seul).
  - `1` : Réinvestissement urbain étendu (campagnes publicitaires ciblées AITown sur villes desservies à forte marge + gares secondaires si saturation station > 80%).
  - `2` : Prospection d'industrie V251 ciblée (financement d'industries productrices dont la marchandise est acceptée par une industrie/ville reliée par une ligne existante avec capacité libre).

### Conditions de déclenchement strictes
Pour éviter d'évincer les investissements normaux :
1. `year >= 1976` (phase tardive avérée).
2. `AICompany.GetLoanAmount() == 0` (aucun emprunt actif).
3. `ai._projects == null || ai._projects.best == null` (aucun projet du vivier principal finançable et admissible en attente).
4. `cash > (v252Cost * 2 + 5000000)` (trésorerie supérieure au double du renouvellement de flotte + réserve incompressible de 5 M£).

### Interaction avec Save / Load
- État volatile de cadence : mémoriser `_lateGameLastMonth` dans l'instance AI (non critique pour la persistance, réinitialisé à -1 au `Load`).

---

## 4. Pièges connus et historique

- **Échec V240 (Croissance urbaine) :** Classé `NO-GO` dans son ancien périmètre (`docs/taches.md:1215`, `docs/journaux/journal_2026-10-30_transfert_taches.md:710`). Financer des actions de ville sans transport immédiat génère des coûts "Autres" massifs sans hausse de chiffre d'affaires, détruisant la valeur de compagnie.
- **Piège C121 N1/N2 :** Mesuré perdant sur 10 ans dans le top 3.
- **Piège des dépenses "Autres" PLYR :** Les achats d'actions municipales ou d'industries sont comptabilisés en dépenses immédiates ; si le fret produit n'est pas immédiatement enlevé et transporté à profit, la perte nette fait chuter le ratio de garde de valeur sous les 95%.
- **Vérification OpenTTD NoAI :** `AIIndustryType.ProspectIndustry` crée une industrie à un emplacement aléatoire de la carte, ce qui est risqué si elle apparaît hors de portée d'une ligne existante. Préférer `AIIndustryType.BuildIndustry` à proximité immédiate d'une station existante disposant de trains/véhicules excédentaires.

---

## 5. Plan de test

1. **Tests unitaires et de contrat hôte (`sweeps/test_late_game.py`) :**
   - Vérifier qu'à `late_game_policy=0`, aucun appel d'achat tardif n'est émis.
   - Vérifier que la présence d'un emprunt (`loan > 0`) bloque tout investissement tardif.
   - Vérifier que si `cash < 5 M£`, aucun déclenchement n'a lieu.
   - Vérifier que le renouvellement de flotte V252 est strictement sanctuarisé dans le calcul du seuil.
2. **Smoke test local :** 1 graine $\times$ 1 an en mode normal (vérification de compilation et santé).
3. **Qualification V102 (Porte B directe ou horizon tardif) :**
   - Comme le mécanisme n'est actif qu'après 1975, la porte A 40 $\times$ 3 ans serait inerte.
   - Profil ad hoc conforme AGENTS.md : **Porte A custom 40 graines $\times$ 10 ans** puis Porte B 20 graines $\times$ 10 ans.
   - Critère : $\Delta \text{profit\_year} \ge +4\%$ en 1979 et ratio valeur de compagnie $\ge 0{,}95$.

---

## 6. Estimation de difficulté et d'effet attendu

- **Difficulté :** **Très élevée** (4/5). Dépendance envers le diagnostic IDLE-1 pour détecter l'absence réelle de projets, et exigence préalable de conformité sur la matrice 48 cellules.
- **Effet attendu :** **$+50$ à $+150\text{ k£/an}$** en fin de partie (années 8 à 10) en convertissant une fraction des 14,7 M£ oisifs en trafic additionnel haute marge sur des lignes amorties.
- **Source des données :** Audit de trésorerie master 1979 (`docs/taches.md:1213`), bilan V249 mode 2 (`ai/OpexAI/task_v249.nut`), inventaire V251 (`ai/OpexAI/probes.nut:213`).
