# Spécification Technique — EB-4 (Arbitrage de Caisse 1970–1972, Volet AIR / ROUTE)

## 1. Objectif et critère de succès chiffré

- **Constat économique :** Durant les 24 à 36 premiers mois de jeu (1970–1972), OpexAI emprunte le plafond maximal de 300 k£ (`main.nut:799`). Malgré cet apport, l'IA passe **60% à 95% de ses cycles en attente de caisse** (`c75StopReason == "cash"`), faute de pouvoir financer le prochain projet retenu :
  - Un premier aéroport + avion coûte typiquement **60 à 85 k£**.
  - Une ligne routière rentable (bus ou camion) coûte entre **3 et 12 k£**.
- **Problème d'éviction bidirectionnelle :**
  1. *Éviction cheap-first :* Des petites lignes routières marginales consomment les derniers 15 k£ nécessaires au lancement d'un aéroport majeur, retardant de plusieurs mois une ligne rapportant 100 k£/an.
  2. *Éviction par thésaurisation stérile :* Lorsque la caisse résiduelle est de 25 k£ et que le prochain aéroport exige 75 k£, la caisse reste inactive pendant 6 à 12 mois sans générer le moindre cash-flow additionnel, alors qu'une ligne routière à retour sur investissement ultra-rapide (< 6 mois) accélérerait l'atteinte des 75 k£.
- **Périmètre strict :** Conforme aux consignes de mission, ce chantier est **strictement limité aux modes AIR et ROUTE**, à l'exclusion formelle de tout investissement ou arbitrage ferroviaire.
- **Critère de succès chiffré :**
  - **Porte A (40 graines $\times$ 3 ans) :** $\Delta\text{profit\_year} \ge +4\%$ (gain short-term V102), test de Wilcoxon exact $p < 0{,}05$, borne basse IC95 bootstrap $> 0$, garde de valeur $\ge 0{,}95$.
  - Réduction mesurée de la dette en fin d'année 1972.

---

## 2. État du code vérifié dans le worktree

- **`ai/OpexAI/main.nut:798-804` :**
  ```squirrel
  local spLoan = PROBE_SPAN_TRACE ? OpexSpanBegin("start.loan") : null;
  AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount());
  if (DECISION_LOG) {
    OpexDecide("LOAN", "action=initial_borrow amount=" + AICompany.GetLoanAmount() + " max_loan=" + AICompany.GetMaxLoanAmount());
  }
  ```
- **`ai/OpexAI/projects_selection.nut:895-932` :**
  - `OpexProjectSelectAffordable(alternatives, capitalBudget, limit, realSelection = true, abandonedPairs = null)`
  - Lignes 918-931 : documentation historique du plancher de profit relatif destiné à contrer l'effet pervers du tri au ratio profit/capital pur mesuré au banc du 2026-09-02 (-24,4% de valeur, -30,7% de profit).
- **`ai/OpexAI/projects_selection.nut:966-971` :**
  ```squirrel
  if (financeCapital > capitalBudget) {
    if (PROBE_SELECT_REJECT && project.mode == "air") {
      OpexSelectRejectLog(project, "cash", affordable, scoreKey, kDec);
    }
    continue;
  }
  ```
- **`ai/OpexAI/task_projects.nut:1067-1070` :**
  - Positionnement de `::V249_CASH_STOP = true` et `::V252_CASH_STOP = true` dès que `c75StopReason == "cash"`.
- **`ai/OpexAI/task_projects.nut:1086-1089` :**
  - `if (P6_AIR_FIRSTLINE_WINDOW != 0 && OpexP6FirstlineWindowHold(this))` : fenêtre d'attente avant dépense.

---

## 3. Conception proposée

### Nouveau réglage et logique d'arbitrage
- **Réglage :** `eb4_air_road_arbitrage` dans `info.nut` (défaut 0, 4 niveaux de difficulté à 0).
  - `0` : Comportement historique inchangé (sélection selon plancher relatif standard).
  - `1` : **Arbitrage dynamique de caisse résiduelle :**
    - Si le projet n°1 non finançable est de mode `air` avec un besoin résiduel $\Delta C = C_\text{air} - \text{caisse}$ :
      - *Zone de protection (proche du but) :* Si $\Delta C \le \text{revenu mensuel estimé} \times 2$, **interdire** toute dépense routière pour sanctuariser l'ouverture imminente de l'aéroport.
      - *Zone d'opportunité (attente longue) :* Si $\Delta C > \text{revenu mensuel estimé} \times 3$, autoriser un projet routier exceptionnel si et seulement si :
        1. Son coût de construction $C_\text{route} \le 0{,}25 \times \text{caisse vivante}$.
        2. Son payback estimé $\le 6\text{ mois}$ ($P_\text{annuel} \ge 2 \times C_\text{route}$).
        3. Il n'appartient pas à une ville couverte par une réservation d'aéroport en cours.

### Interaction avec Save / Load
- L'arbitrage s'effectue à la volée dans `OpexProjectSelectAffordable` à chaque passe de réévaluation de caisse. Aucune variable persistante d'état n'est requise dans le flux de sauvegarde.

---

## 4. Pièges connus et historique

- **Le piège « Cheap-First » (`projects_selection.nut:918-927`) :** Un simple tri par ROI favoriserait systématiquement une cascade de camions à 3 k£ au détriment des lignes aériennes à fort volume. L'arbitrage EB-4 ne doit JAMAIS rétrograder un projet AIR éligible au profit d'un projet ROUTE ; il n'intervient QUE lorsque le projet AIR est strictement infinançable à court terme.
- **Incompatibilité avec les feeders d'aéroports (`PAX_AIR_FIRST_FEEDER_ONLY`) :** Vérifier que les lignes routières sélectionnées ne court-circuitent pas le module d'apport d'aéroport (`airport_feeder_dispatch.nut:29`).
- **Garde de valeur à 3 ans :** Construire des véhicules routiers faiblement amortis peut dégrader la valeur de compagnie si leur taux d'utilisation est insuffisant. Le critère de payback $\le 6\text{ mois}$ est un garde-fou impératif.

---

## 5. Plan de test

1. **Tests hôtes (`sweeps/test_eb4_arbitrage.py`) :**
   - Vérifier qu'à `eb4_air_road_arbitrage=0`, la sélection de projets reproduit à l'identique l'ordre historique.
   - Vérifier le blocage d'un projet route lorsque le projet air manque de moins de 2 mois de cash.
   - Vérifier le déblocage d'un projet route ultra-rentable lorsque le projet air manque de 6 mois de cash.
2. **Smoke test causale :** 1 graine $\times$ 1 an (graine 42, horizon 1970-1971), validation de l'absence de crash et journalisation `DECISION_LOG` des arbitrages.
3. **Qualification V102 complète :**
   - **Porte A :** 40 graines $\times$ 3 ans, profil `gain_short`, critère $\ge +4\%$ de delta profit annuel terminal.
   - **Porte B :** 20 graines $\times$ 10 ans, profil `non_erosion`, garde de valeur $\ge 0{,}95$.

---

## 6. Estimation de difficulté et d'effet attendu

- **Difficulté :** **Élevée** (3.5/5). La sélection de projets est le carrefour décisionnel d'OpexAI. Un dérèglement subtil peut déséquilibrer tout le portefeuille.
- **Effet attendu :** **$+30$ à $+80\text{ k£/an}$** en début de partie (années 1 à 3), accélération du remboursement de la dette et réduction de l'oisiveté de trésorerie de 15 à 25%.
- **Source des données :** Audit de trésorerie 1970-1972 (`docs/taches.md:1191`), analyse des rejets de sélection (`probes.nut:OpexSelectRejectLog`).
