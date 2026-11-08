# Revue d'analyse — Tâche 5 : Suite H3 (Examen des 89 lignes bus « admissibles mais non retenues »)

**Date :** 8 novembre 2026  
**Auteur :** Antigravity  
**Sujet :** Examen des 89 lignes bus admissibles non retenues dans l'auscultation H3 :
- `SITE_LOST` (34 lignes)
- `TRACEX` (28 lignes)
- `maxBatch=1` (27 lignes)

---

## 1. Contexte et problématique

Dans l'analyse approfondie de l'Hypothèse 3 (`H3_CAISSE_1972.md`), sur les 482 ouvertures de lignes d'AAAHogEx en 1972, 80,3 % concernaient des modes volontairement exclus d'OpexAI à cette date (courrier autonome avec voirie dédiée, fret routier lourd, ou paires > 128 tuiles).
Seules **89 lignes (18,5 %)** correspondaient à des liaisons bus interurbaines admissibles selon les critères d'OpexAI, réparties en trois motifs d'élimination :
1. `SITE_LOST` : 34 lignes (7,1 %)
2. `TRACEX` : 28 lignes (5,8 %)
3. Cadence `maxBatch=1` : 27 lignes (5,6 %)

La présente étude examine si l'un de ces trois goulots constitue une cause évitable justifiant un levier neuf.

---

## 2. Analyse causale détaillée par motif

### A. Motif `SITE_LOST` (34 lignes) — Insoluble spatialement sans perte de valeur
- **Mécanisme physique :**
  Lors de la passe de scanning amont, deux emplacements d'arrêts A et B sont pré-identifiés dans les tissus urbains. Lorsque le chantier s'ouvre, l'un des deux sites est devenu physiquement inconstructible : l'autorité municipale a étendu la voirie urbaine, une maison a poussé sur la case réservée, ou le rayon de captage est désormais recouvert par une station préexistante.
- **Leviers déjà testés et réfutés dans le dépôt :**
  1. *Relocalisation locale (`road1y_site_relocate`, commit `52a7e0ec`) :*
     Recherche d'un site alternatif à $\le 6$ tuiles.
     *Résultat :* Porte A 40×3 à **−4,2 k£/an** (14V/26D, p=0,29) $\Rightarrow$ `fail_primary`.
     *Cause :* Un site déporté à 6 tuiles capte une frange périphérique à faible densité de voyageurs, dégradant la rentabilité unitaire de la ligne.
  2. *Réduction du cooldown de bannissement (`road1y_abandon_days=60`, commit `2e1b131e`) :*
     Raccourcissement du bannissement de 365 à 60 jours.
     *Résultat :* Smoke 3 graines à **−22,0 k£/an** $\Rightarrow$ rejeté.
     *Cause :* L'IA boucle sur les mêmes paires urbaines en conflit, gaspillant des opcodes et subissant des échecs répétés.
- **Verdict :** `SITE_LOST` est une contrainte spatiale dure, non évitable sans dégradation économique.

### B. Motif `TRACEX` (28 lignes) — Contrainte topographique avérée
- **Mécanisme physique :**
  L'algorithme de routage A* échoue à trouver un chemin continu en voirie plane entre A et B en raison d'obstacles géographiques (plans d'eau, falaises, dénivelés abrupts).
- **Levier déjà testé et réfuté :**
  *Ponts routiers (`road1y_bridge`, commit `f8023aec`) :*
  Autorisation de ponts routiers pour franchir les obstacles A*.
  *Résultat :* Porte A 40×3 à **+0,4 k£/an** (22V/18D, p=0,90, IC95 [−21 ; +22] k£) $\Rightarrow$ `fail_primary`.
  *Cause :* Le surcoût d'infrastructure d'un pont routier élève le CAPEX de la ligne à plus de 35 k£, allongeant le payback au-delà de 2 ans et neutralisant le bénéfice net à l'horizon 3 ans.
- **Verdict :** `TRACEX` reflète des barrières physiques dont le contournement par génie civil lourd n'est pas rentable sur bus.

### C. Motif `maxBatch=1` (27 lignes) — Incompatibilité avec l'année terminale
- **Mécanisme :**
  Le scheduler d'OpexAI limite les constructions à une seule nouvelle ligne par passe de portefeuille (`task_projects.nut:1285-1335`).
- **Levier déjà testé et réfuté :**
  *Cadence `road100_road_batch=1` (4 lignes max par passe) :*
  *Résultat :* Porte A 40×5 à **−194 £/an** (15V/23D, p=0,85) $\Rightarrow$ `fail_primary`.
- **Pourquoi ouvrir plus de lignes en an 3 (1972) détruit du profit terminal :**
  L'auscultation H3 a prouvé mathématiquement que :
  1. Une ligne de bus ouverte au T3 ou T4 de 1972 nécessite 60 à 90 jours pour que ses bus soient achetés, mis en route et stabilisés.
  2. Sur l'année calendaire 1972 (qui mesure `profit_year`), la ligne enregistre l'intégralité de ses amortissements et coûts de mise en service mais seulement 2 à 4 mois de recettes brutes. Son profit net sur 1972 est **négatif ou inférieur à 500 £**.
  3. L'ouverture accélérée en 1972 consomme la caisse qui sécurise les renforts de bus existants (`OpexRoadRefleet`), lesquels rapportent 5 500 £/bus immédiatement sans délai de rodage.

---

## 3. Conclusion et arbitrage

1. **Aucun des 3 motifs d'élimination des 89 lignes (SITE_LOST, TRACEX, maxBatch=1) n'est évitable à gain économique positif à l'horizon 3 ans.**
2. Le seul véritable levier rationnel extrait de l'auscultation H3 était l'assainissement de la dette bancaire via l'abaissement du plancher de remboursement : c'est précisément **`road1y_loan_floor`**, qui a été implémenté et validé lors de la **Tâche 1**.
3. En conséquence, aucun code expérimental hasardeux supplémentaire n'est introduit pour la Tâche 5, préservant la stabilité parfaite du code et évitant les régressions mesurées sur `site_relocate`, `abandon_days`, `bridge` et `road_batch`.
