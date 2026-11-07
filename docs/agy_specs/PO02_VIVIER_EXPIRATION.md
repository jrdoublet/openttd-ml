# Spécification Technique — PO-02 (Échéance de Publication Propre à Chaque Vivier)

## 1. Objectif et critère de succès chiffré

- **Constat d'architecture :** Depuis la livraison de PO-01c (découpage coopératif de la régénération réactive), la reconstruction complète s'exécute par tranches. Cependant, les viviers de projets (`air`, `rail`, `road`, `water`) partagent encore une logique d'invalidation globale couplée aux révisions C76.
- **Problème de l'expiration globale :** Un événement mineur sur le réseau routier peut déclencher une reconstruction lourde de tous les modes, ou inversement, des candidats d'un mode dont le réseau a peu évolué peuvent stagner ou être régénérés inutilement alors qu'ils sont encore frais.
- **Objectif :**
  1. Donner à chaque vivier modal son propre cycle de fraîcheur (TTL) et d'échéance de publication indépendante.
  2. Maintenir la validité des candidats en cours pendant le recalcul (pas de "trou de vivier" où un mode se retrouve vide).
  3. Coalescer les demandes de régénération pour éviter la redondance d'opcodes.
- **Critère de succès chiffré :**
  - **Opcodes :** Réduction de **$10$ à $25\text{ M opcodes/an}$** sur les postes `select.reselect` (actuellement 12,04 M/an) et `catalog.rebuild` (10,81 M/an) selon l'inventaire PCAL-03.
  - **Neutralité V102 (Règle d'opcodes du 24/09) :** Banc apparié 20 graines $\times$ 10 ans sans perte de profit, IC95 Student non négatif, test des signes $p \ge 0{,}05$, garde de valeur $\ge 0{,}95$.

---

## 2. État du code vérifié dans le worktree

- **`ai/OpexAI/po01c_regen.nut:740-775` :**
  - `OpexPO01CStart(owner)` : inspecte les modes "sales" (`dirty`) en comparant les instantanés de révision de couche (`OpexAC06SnapshotLayer`) avec les révisions acquittées (`OpexPO01CConsumed`).
- **`ai/OpexAI/po01c_regen.nut:776-805` :**
  - `OpexPO01CAcknowledge(owner, s)` : met à jour `owner._c76ModeConsumed` pour chaque mode publié.
- **`ai/OpexAI/po01c_regen.nut:823-866` :**
  - `OpexPO01CPublish(owner, s)` : fusionne atomiquement les projets générés d'un mode (`OpexPO01CMerge`) dans `owner._projects` puis réexécute la sélection finale `OpexReselectProjects`.
  - Lignes 826-831 : protection du scan AIR asynchrone si `OpexPO01CAirPending(owner)`.
- **`ai/OpexAI/orchestrator.nut:618-622` :**
  - `if (PO01C_REGEN_SPLIT && this._projects != null) this._po01cPending = true;`
- **`ai/OpexAI/main.nut:816` :**
  - Exécution par tranches : `if (PO01C_REGEN_SPLIT && (this._po01cPending || this._po01cJob != null)) OpexPO01CStep(this);`

---

## 3. Conception proposée

### Durées de vie indépendantes par mode (TTL)
- **Réglage :** `po02_independent_expiry` dans `info.nut` (défaut 0, 4 niveaux à 0).
- **Cadence de fraîcheur nominale :**
  - `ROAD` : 30 jours (réseau très fluide, adaptation rapide aux extensions urbaines).
  - `RAIL` : 30 jours (gestion des opportunités fret/pax).
  - `WATER` : 90 jours (infrastructure maritime très stable, scans côtiers coûteux).
  - `AIR` : Cadence pilotée par le scan C78 reprenable avec isolation des verrous.

### Horodatage et Coalescence
- Ajouter sur l'instance OpexAI une table `_po02LastPublishDate = { air = 0, rail = 0, road = 0, water = 0 }`.
- Un mode n'est éligible à un rafraîchissement d'échéance que si `currentDate - _po02LastPublishDate[mode] >= TTL[mode]`.
- **Coalescence :** Si une invalidation C76 intervient alors qu'une expiration temporelle est proche (< 5 jours), regrouper les travaux dans le même lot PO-01c.
- **Continuité d'offre :** Les projets du vivier existant restent éligibles au financement jusqu'à ce que `OpexPO01CPublish` écrase et remplace le mode concerné.

### Interaction avec Save / Load
- Sauvegarder la table `_po02LastPublishDate` dans le bloc de persistance PO-01c/C76 (`persist.nut`). Si absente (chargement d'une ancienne sauvegarde), initialiser avec la date courante pour éviter une tempête de recalcul immédiate.

---

## 4. Pièges connus et historique

- **Échec historique V143 (`docs/taches.md:1210`, `docs/journaux/journal_2026-10-30_transfert_taches.md:961`) :** Le rafraîchissement annuel rail/route en plein vol d'un scan AIR avait détruit les résultats économiques (-252 k£/an au smoke 2×5) en corrompant les contextes d'itérateurs. Le scan AIR C78 doit conserver son étanchéité absolue (`OpexPO01CAirPending`).
- **Échec V142 :** Les modifications apportées directement au tri et au plancher de sélection avaient dégradé la rentabilité. PO-02 doit se contenter d'alimenter les listes de candidats sans modifier la fonction de sélection finale `OpexReselectProjects`.
- **Risque de famine (Starvation) :** Si les expirations rail et route se répètent trop fréquemment, le générateur AIR ou les tâches d'infrastructure peuvent manquer de tranches d'opcodes. Un quota de tranches d'opcodes équitable doit être maintenu dans `OpexPO01CStep`.

---

## 5. Plan de test

1. **Tests unitaires et de contrat (`sweeps/test_po02_expiry.py`) :**
   - Vérifier qu'à `po02_independent_expiry=0`, la logique de déclenchement PO-01c historique est inchangée.
   - Vérifier le calcul d'éligibilité pour chaque mode selon son TTL (30j, 90j).
   - Vérifier la coalescence de deux requêtes rapprochées.
   - Vérifier la préservation des projets en cours durant le calcul de tranche.
2. **Smoke test local :** 1 graine $\times$ 1 an avec vérification des traces `PO01C_BATCH`.
3. **Qualification au banc (Règle d'opcodes du 24/09) :**
   - 20 graines $\times$ 10 ans apparié contre la référence master.
   - Métrique primaire : profit annuel non dégradé, absence de perte au test des signes, garde de valeur $\ge 0{,}95$.
   - Métrique secondaire : réduction mesurée des opcodes des postes `select.reselect` et `catalog.rebuild`.

---

## 6. Estimation de difficulté et d'effet attendu

- **Difficulté :** **Élevée** (3.5/5). S'appuie sur la structure existante de PO-01c, mais exige de gérer finement l'indépendance des dates et les collisions avec les révisions C76.
- **Effet attendu :** Économie de **$10$ à $25\text{ M opcodes/an}$**, suppression des à-coups réactifs et meilleure réactivité du réseau routier/ferroviaire.
- **Source des données :** Inventaire PCAL-03 (`docs/pcal03_inventaire_20261021.md`), bilan PO-01c du 23/10 (`docs/po01c_regen_split_20261021.md`).
