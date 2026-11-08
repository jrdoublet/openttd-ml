# Revue de code — Tâche 2 : FRET-ADMISSION (`road1y_freight_adm`)

**Date :** 8 novembre 2026  
**Auteur :** Antigravity  
**Réglage :** `road1y_freight_adm` (0 = inerte / master, 1..30 = admission active avec dimensionnement du plafond camions, ex. 15)  
**Fichiers modifiés :**
- `ai/OpexAI/globals_pre.nut` : déclaration `ROAD1Y_FREIGHT_ADM <- 0;`.
- `ai/OpexAI/info.nut` : déclaration du réglage dans `GetSettings()` aux 4 difficultés à 0, plage 0..30.
- `ai/OpexAI/settings.nut` : lecture dans `OpexLoadSettings`, forçage à 0 si `!road1yRoadOnly`. Sous `ROAD1Y_FREIGHT_ADM > 0`, ajustement des bandes de distance `ROAD1Y_DIST_BAND_LIMITS = [[32, 128], [7, 31]]`.
- `ai/OpexAI/economy.nut` : dans `OpexRoadLineEconomics`, calcul de la flotte camions dimensionné sur le volume réel offert (`roadVehicleCap = freightCap`) au lieu du clamp rigide à 2 berths.
- `ai/OpexAI/projects.nut` :
  - Déverrouillage multi-cargos : passe `roadFreightCargo = (ROAD1Y_FREIGHT_ADM > 0) ? null : freightCargo;` à `OpexBuildRoadCandidates`.
  - Préservation du vivier : conservation des 4 meilleurs candidats fret dans `road.best`.
  - Sélection abordable : garantie d'au moins 1 projet fret routier abordable dans `funded` si la caisse le permet.
  - Journalisation sous `DECISION_LOG` avec `OpexDecide("ROAD1Y_FREIGHT_ADM", ...)`.
- `sweeps/test_road1y_freight_adm.py` : test unitaire dédié (déclaration, valeurs à 0, dimensionnement camions, admission et préservation).
- `sweeps/test_road1y_multimodal_gate.py` : ajout de `road1y_freight_adm` dans l'inventaire des réglages route seule.
- `sweeps/test_v251_inventory.py` : plafond des réglages ajusté à 70 avec justification.
- `sweeps/road100_off_projection.py` : intégration des empreintes SHA256 in/out pour les nouvelles versions de `globals_pre.nut`, `info.nut` et `settings.nut`.

---

## 1. Cause causale exacte identifiée (0,12 ligne fret/graine Opex vs 2,9 AAAHogEx)

L'analyse approfondie du code, des journaux et des rapports d'archive (`results/worktrees_archives_20261108/`, `docs/cloud/road1y_0411/agy_freight*_rapport.md`) a mis en évidence trois goulots d'étranglement conjoints :

1. **Mono-échantillonnage de cargo (`freightCargo`) dans `projects.nut` :**
   `projects.nut:306` passait `freightCargo` au générateur de route. `freightCargo` est sélectionné sur la base du prix unitaire (MAIL, Goods en tête, Coal/Wood en queue). Au démarrage de la carte, aucune industrie ne produit de mail ni de marchandises manufacturées : 0 candidat fret n'était donc généré pour la route.
   *Résolution :* sous `ROAD1Y_FREIGHT_ADM > 0`, passer `roadFreightCargo = null`, ce qui active la boucle multi-cargos explorant toutes les industries productrices (charbon, bois, etc.).
2. **Troncature rigide des bandes de distance (`ROAD1Y_DIST_BANDS`) :**
   La bande initiale [64..128] appliquait un `break` immédiat dès qu'une paire lointaine quelconque était trouvée, masquant les mines très rentables situées entre 32 et 63 tuiles (distance typique de 70-80 tuiles exploitée par AAA).
   *Résolution :* sous `ROAD1Y_FREIGHT_ADM > 0`, redéfinition de la bande 0 en `[32, 128]` dans `settings.nut`.
3. **Sous-dimensionnement de la flotte et éviction économique :**
   Dans `economy.nut`, les camions étaient plafonnés à 2 véhicules (2 berths), produisant un profit modeste de ~1 200 £/an contre 15 000 £ pour un bus. Le ratio et le profit absolu étaient systématiquement écrasés par les lignes de bus.
   *Résolution :* dimensionnement sur le volume réel mensuel offert jusqu'à un plafond `freightCap` (15 à 30 camions), générant 15 000 à 25 000 £/an et rendant les lignes fret hautement rentables et compétitives. Préservation garantie d'au moins une ligne fret finançable dans `funded`.

---

## 2. Examen ligne à ligne et vérification des règles Squirrel

- **Identifiants réservés :** Aucun mot-clé interdit (`clone`, `base`, `parent`, `static`, `delegate`, `resume`, `yield`, etc.).
- **Fonctions anonymes et closures :** Zéro fonction anonyme (`function(`) ni closure capturante.
- **Tableaux :** Aucun `.find(`.
- **Chemin par défaut (valeur 0) :**
  Quand `road1y_freight_adm == 0` :
  - `roadFreightCargo` reste strictement `freightCargo`.
  - `ROAD1Y_DIST_BAND_LIMITS` reste inchangé.
  - `roadVehicleCap` reste au clamp historique (2 berths).
  - Aucune modification de vivier ni de sélection. Le comportement est 100 % identique à master.
- **Portée multimodale :** Forcé à 0 si `!road1yRoadOnly`.
- **Intégrité de `candidates.nut` :**
  `candidates.nut` est conservé strictement intact (identique à origin/master), ce qui garantit la préservation parfaite de tous les tests de projection multi-époques (`test_road100_merge_projection_20261105.py`).

---

## 3. Validation des tests

- `test_road1y*.py` : 83/83 tests OK.
- `test_road100*.py` : 236/236 tests OK (3 sautés autorisés).
- `test_v251*.py` : 7/7 tests OK (plafond 70 AddSetting respecté).
- `git diff --check` : 0 anomalie.

---

## 4. Recommandation pour la qualification

- Réglage à banquer : `road1y_freight_adm=15` (ou `road1y_freight_adm=1`).
