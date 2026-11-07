# Spécification technique : EB-7 phase 2 (comptabilité fine des dépenses)

## 1. Objectif et critère de succès chiffré

### Objectif
Mettre en place un système de comptabilité transactionnelle fine et passive enregistrant les dépenses **réellement débitées** de la caisse (en cash), ventilées par objet et par mode de transport :
1. **Objets de dépense** :
   - Voies et voirie (construction, terrassement, nivellement, démolition).
   - Stations et arrêts (quais rail, arrêts bus, aéroports, quais de chargement).
   - Dépôts (dépôt rail, dépôt route, hangar aviation).
   - Signaux ferroviaires (PBS, cantons).
   - Véhicules : distinguer **achats bruts** et **ventes** (recettes nettes), par mode.
   - Dépenses municipales / autres : statues (V249), droits exclusifs (V250), campagnes de pub.
2. **Réconciliation financière** :
   - Rapprochement exact avec les postes officiels `AICompany.GetQuarterlyIncome` / `AIAccounting` et la trésorerie réelle `AICompany.GetBankBalance` + prêt `AICompany.GetLoanAmount`.
   - Zéro double comptage, isolation absolue des commandes simulées en `AITestMode`.

### Critères de succès chiffrés
- **Exactitude de réconciliation** : écart maximal entre $\Delta(\text{cash} - \text{prêt})$ et la somme algébrique des flux comptabilisés $\le 1\%$ (hors revenus opérationnels de transport de marchandises).
- **Zéro pollution AITestMode** : 100 % des devis ou sondages de nivellement/tracé exécutés en mode test doivent être isolés (coût comptabilisé = 0 £).
- **Consommation d'opcodes** : sonde passive, surcharge $< 0,5\%$ des opcodes globaux au défaut 0, et $< 2\%$ lorsque la sonde est activée.
- **Save/Load roundtrip** : persistance exacte des compteurs cumulés sans dérive après rechargement.

---

## 2. État du code existant (fichier:ligne vérifiés dans le worktree)

1. **Mécanisme OpenTTD NoAI `AIAccounting` et piège du bouclier `AITestMode`** :
   - [`ai/OpexAI/air_construction.nut:7-14`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/air_construction.nut#L7-L14) :
     `/* 1. AIAccounting compte AUSSI les commandes jouees en AITestMode -- Le bouclier est un AIAccounting IMBRIQUE : son destructeur RESTAURE le total du niveau superieur. */`
   - [`ai/OpexAI/builder_rail.nut:4514-4518`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/builder_rail.nut#L4514-L4518) :
     `/* Bouclier : AIAccounting compte le cout SIMULE des commandes jouees en AITestMode ... local shield = AIAccounting(); */`
   - [`ai/OpexAI/builder_road.nut:5161-5162`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/builder_road.nut#L5161-L5162) :
     `local costs = AIAccounting();` pour mesurer la dépense réelle de pose.

2. **Suivi existant de caisse et investissements** :
   - [`ai/OpexAI/ledgers.nut:1110-1135`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/ledgers.nut#L1110-L1135) : `OpexCashSnapshot()` relève cash, loan, max_loan et trésorerie disponible.
   - [`ai/OpexAI/task_projects.nut:289`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/task_projects.nut#L289) : sonde `C63_INVEST_PROBE ? AIAccounting() : null`.

---

## 3. Conception proposée

### 3.1 Réglage et intégration
- **Réglage** : `eb7_detailed_accounting` (0 = désactivé/défaut ; 1 = sonde comptable active avec journalisation mensuelle et réconciliation).
- **Constante** : `EB7_DETAILED_ACCOUNTING <- 0;` dans `globals_pre.nut`.
- Lecture dans les deux chargeurs de `settings.nut` :
  `EB7_DETAILED_ACCOUNTING = AIController.GetSetting("eb7_detailed_accounting") == 1 ? 1 : 0;`

### 3.2 Structure de données comptables (`OpexLedgerEB7`)
Créer une classe ou table légère dans `ledgers.nut` :
```squirrel
class OpexEB7Ledger {
  // Flux cumulés de dépenses réelles (en GBP)
  capexTrackRoad = 0;
  capexTrackRail = 0;
  capexStationRoad = 0;
  capexStationRail = 0;
  capexStationAir = 0;
  capexDepotRoad = 0;
  capexDepotRail = 0;
  capexDepotAir = 0;
  capexSignals = 0;
  
  // Flottes
  vehBuyRoad = 0;
  vehBuyRail = 0;
  vehBuyAir = 0;
  vehSellRoad = 0;
  vehSellRail = 0;
  vehSellAir = 0;
  
  // Divers
  civicStatues = 0;
  civicRights = 0;
  civicOther = 0;
  
  // Horodatage et point de contrôle
  lastCash = 0;
  lastLoan = 0;
}
```

### 3.3 Enregistrement sans double comptage
- **Chantiers de construction** :
  Encadrer chaque bloc d'exécution réelle (hors AITestMode) :
  ```squirrel
  local acc = EB7_DETAILED_ACCOUNTING ? AIAccounting() : null;
  // ... exécution des commandes réelles BuildTrack / BuildStation ...
  if (acc != null) {
    local spent = acc.GetCosts();
    this._eb7Ledger.capexTrackRail += spent;
  }
  ```
- **Achats et Ventes de véhicules** :
  Lors de `AIVehicle.BuildVehicle` : enregistrer le coût net réel (prix d'achat).
  Lors de `AIVehicle.SellVehicle` : enregistrer le produit de la vente dans `vehSell*`.

### 3.4 Persistance (Save/Load)
- Sérialiser la table `_eb7Ledger` dans `persist.nut` (méthodes `Save` et `Load`).
- Lors de `Load`, réconcilier `lastCash = AICompany.GetBankBalance(COMPANY_SELF)` et `lastLoan = AICompany.GetLoanAmount()`.

---

## 4. Pièges connus et historique

1. **Piège AITestMode / AITestMode leak** :
   Si un `AIAccounting()` est ouvert pendant qu'une méthode appelle une sous-fonction qui exécute `AITestMode` sans bouclier `local shield = AIAccounting()`, les coûts **fictifs** de test (ex: devis d'A* de 500 000 £) s'ajoutent au compteur et faussent complètement la comptabilité !
   *Contre-mesure* : s'assurer que l'objet `acc` n'est instancié qu'immédiatement autour des appels de construction réelle, après validation du plan.
2. **Piège des dépenses municipales "Autres" de PLYR** :
   Dans l'écran des finances OpenTTD, la ligne « Autres » regroupe statues, droits exclusifs, nivellement urbain, mais aussi certains frais de modification de voirie municipale. Ne pas assimiler « Autres » aux statues seules.
3. **Piège de l'inflation** :
   OpenTTD applique des multiplicateurs d'inflation au fil des années. La comptabilité doit relever les montants absolus débités à la date de l'opération, pas un prix catalogue nominal.

---

## 5. Plan de test

1. **Tests hôtes unitaires** :
   - `sweeps/test_eb7_detailed_accounting.py` :
     - Vérifier la neutralité à 0 : aucun objet alloué, 0 opcode additionnel.
     - Tester l'isolation d'un bloc `AITestMode` (coût enregistré = 0).
     - Tester la formule de balance : `Cash(T) - Cash(0) + Prêt(T) - Prêt(0) = Somme(Revenus) - Somme(Dépenses)`.
2. **Smoke 1×1 an** :
   - Exécution avec `eb7_detailed_accounting=1` sous graine 42 : vérifier l'émission du log mensuel `EB7_MONTHLY_REPORT` avec décomposition complète.

---

## 6. Estimation de difficulté et effet attendu

- **Difficulté** : Modérée (instrumentation minutieuse des points de commande réels dans `builder_rail.nut`, `builder_road.nut`, `air_construction.nut`, `task_v249.nut`).
- **Effet attendu** :
  - Outil de diagnostic analytique indispensable pour identifier où s'échappe l'argent entre 1970 et 1974 (AIR vs RAIL vs voirie).
  - Économie directe : 0 k£ (sonde pure), mais débloque l'arbitrage précoce EB-4.
- **Source** : `docs/taches.md` ligne 1203 et rapport EB-7 (`docs/journaux/journal_2026-10-30_transfert_taches.md` ligne 54).
