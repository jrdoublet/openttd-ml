# Intégration AIR/sélection, amortissement shadow et R1/R3 — 01/10/2026

## Périmètre et protocole central (avant moteur)

Demande : les trois lots terminés, intégrer et lancer les tests. Rapports reçus :
[AIR](air_selection_light_20261001.md), [shadow](fleet_amort_shadow_20261001.md),
[R1/R3](r1_r3_mechanisms_20261001.md). Les états de jeu dirigés R1/R3 ne sont
**pas livrés** : huit protocoles et un lanceur d'exposition naturelle, pas huit
fixtures moteur. Ne pas fabriquer leurs préconditions ou leurs succès.

Intégration :

- Mesure `SELECTION_LIGHT` sur les trois chemins full/incremental/reselect,
  sous le gate existant `catalog_cost_probe`, valeur d'opcodes existante réutilisée.
  Dates/ticks légèrement englobants, avant/après la mesure existante ; émission
  exclue. Identités locales à la VM, séparées par source/compagnie/session.
- Nouveau module `selection_diagnostics.nut`, chargé par le sélecteur. Sonde
  `fleet_amort_shadow_probe=0/1/2` : OFF/calcul/calcul+instantanés. Défaut **0**.
  Admission figée après R1 et filtres, ensemble complet avant limite, copies
  diagnostiques triées par le comparateur existant. Le préfixe témoin doit égaler
  le sélecteur réel avant compaction. Aucune mutation des champs décisionnels.
  Helper, copie/tri et émission détaillée séparés ; enveloppe incluant le travail
  vivant non assimilée au coût propre de la sonde ; émission du bilan exclue.
- Instantanés scalaires par élection, filiation quantité initiale/ajustée et
  ordres VM transmis au lecteur livré via un adaptateur strict. Pas de classement
  reconstruit à partir des scores arrondis ni de total des seuls survivants.
  V92 et politiques C84/C85/C118/C120/C121/C122 hors périmètre de cette collecte.
  Le helper V92 reste testable indépendamment mais le profil intégré le refuse.
- R1/R3 : conserver la constante OFF en production ; le lanceur livré active
  uniquement sa copie dédiée, sans nouveau réglage métier.
- Contrat lexical Squirrel corrigé pour masquer chaînes/commentaires avant de
  rechercher les identifiants interdits ; contre-test conservant `local base`.
  Ancien contrat « aucun appel shadow » remplacé par « un seul appel diagnostic
  derrière gate OFF ». Aucun test historique Git contourné.

### Validation et ressources pré-enregistrées

Sources stabilisées avant chaque campagne, aucune édition pendant le moteur.
Copie sans `.git`/Git : hashes avant/après, **pas** de qualification ni de bundle
Git immuable. L'image historique existe par son digest mais le tag `openttd-lab`
n'existe plus : employer
`sha256:69d7e57aad5d3036f16655e8af23f36aa9fbb7c82c61ea325192c56b50e48e47`.
Docker Desktop local, 16 CPU/4 Go ; un seul conteneur, 3 CPU/2 Go sans swap,
cache `openttd-lab-home`, au plus 3 workers (R1/R3 : 1). Plafond autorisé global
12 CPU/12 workers non nécessaire ici. Aucun téléchargement/install implicite.

1. Contrats ciblés puis régression complète. État avant moteur : **137/137**
   ciblés ; **1112 réussis / 1 erreur Git absent / 1 skip sur 1114** au global.
   [Reçu](../results/three_lots_integration/tests_before_engine_20261001_r1.json).
2. AIR léger : smoke apparié 42×1 an, témoin puis sonde, debug4 commun,
   `diag_three_lots_integration --lot light`. Critères du lot AIR inchangés :
   santé/horizon 1971-02-01, une génération close, phase non nulle, sélection
   full, pas de conflit ; une dernière invocation à l'horizon peut être censurée.
   Raccord sélection ajouté avant mesure, sans deuxième calcul économique.
   Si passage : deux répétitions séparées 5×6 conformément au plan du lot ; filtre
   pratique −5 % profit/valeur et ≥3/5 deltas moyens par graine non négatifs,
   jamais une preuve de neutralité. Aucun 20×10.
3. Shadow : smoke 42×1 an, trois bras OFF/1/2, séparé du lot AIR. Si sain,
   exposition bornée 42×2 ans, trois bras, fin 1972-02-01. Amendement explicite
   au prérequis Git du rapport : diagnostic live-tree haché seulement, pas banc
   qualifiant. Les fixtures Python ne remplacent pas la fixture arithmétique VM
   ni les seuils de budget moteur. Au moins une élection complète fleet+nouvelle
   liaison nécessaire à l'exposition comparative ; absence = non-exposé.
4. R1/R3 : smoke naturel livré 42×1 an, copie dédiée, un worker. Santé et hashes
   obligatoires ; `trace_status=pass` n'est pas validation d'une fixture dirigée.
5. Save/Load technique séparé des frontières exactes : sonde(s) dans des profils
   distincts, répertoire de scratch neuf/isolé, phases séquentielles. Ne pas
   qualifier R1 reload ni scan suspendu si frontière non exposée.

Sorties neuves sous `results/air_selection_light/`, `results/fleet_amort_shadow/`,
`results/r1_r3_mechanisms/` et reçu central `results/three_lots_integration/`.
Tous les échecs sont conservés ; pas de relance pour résultat favorable.
**C115 protégé, cadence OFF, aucun amortissement utilisé pour acheter/classer,
aucun commit/push et aucun changement de politique par défaut.**

## Résultats moteur

### Amendement technique r2

Smoke AIR r1 conservé : échec des deux bras à la compilation, `projects_selection`
ligne 6, `scalar expected : integer,float or string`. La constante livrée
`const R1_R3_TEST_ONLY = false` n'est pas acceptée par cette VM. Remplacement
par **`const R1_R3_TEST_ONLY = 0`**, copie test-only activée à **1** ; contrats
adaptés. Aucun changement économique ni relance de résultat défavorable.
Relance technique prévue `engine_smoke_20261001_r2.json`, même protocole.

AIR r2 sain (2/2), 11 générations closes et dernière invocation censurée à
l'horizon ; 35 sélections valides, huit bilans catalogue. Shadow r1 : témoin et
calcul seul sains, émission échoue car NoAI n'expose pas `format()`. Artefact
conservé. Sérialisation remplacée par mantisse entière neuf chiffres + exposant,
sans changement d'ordre ni arrondi utilisé par le sélecteur. Contrat ajouté.
Relance shadow r2 ; reconfirmation AIR r3 sur cet arbre final avant répétitions.

### Save/Load : paramètres de l'exécution technique

Trois profils **séparés et séquentiels** : `catalog_cost_probe=1`,
`fleet_amort_shadow_probe=2`, puis copie R1/R3 `decision_log=1`. Graine 42,
phase A deux ans, checkpoint calendaire exact **1971-01-01**, phase B un an.
Sortie neuve `results/three_lots_integration/save_load_20261001_r1/` ; aucune
utilisation/suppression de `.scratch_saveload`. Driver de campagne archivé
[ici](../results/three_lots_integration/save_load_driver_20261001.py), réutilisant
les fonctions de phase existantes, cache moteur existant et décodeurs physiques
par propriétaire. Hash du checkpoint effectivement chargé et des saves conservé.
Ce choix exact de **date** n'atteste pas la frontière exacte d'un mécanisme.

## Bilan final

### Tests et intégrité

- Suite finale : **1115 tests, 1113 réussis, zéro failure, une erreur historique
  Git absent (`test_c80_rail_stock_worker`, `git show 6895781:…`), un skip Git**.
  [Reçu final](../results/three_lots_integration/tests_final_20261001_r1.json).
  22 nouveaux tests de raccord ; les contrats des trois lots sont conservés,
  sauf adaptations explicitement décrites ci-dessus.
- Compilations/exécutions moteur réussies sur l'arbre final. Les **622 hashes**
  du second 5×6 concordent encore après tous les runs et la régression finale.
  La copie R1/R3 ne diffère que par sa constante test-only ; copie et sources
  contrôlées avant/après par son harnais. Aucun Git/SHA inventé.
- Tous les runs finaux sortent 0, sans OOM. Les deux échecs techniques antérieurs
  sont conservés. Aucun conteneur de simulation laissé actif après validation.

### AIR et sélection : filtre de perturbation passé, pas neutralité prouvée

Arbre final :
[smoke r3](../results/air_selection_light/engine_smoke_20261001_r3.json),
[répétition 1](../results/air_selection_light/engine_perturbation_20261001_rep1.json),
[répétition 2](../results/air_selection_light/engine_perturbation_20261001_rep2.json),
[synthèse appariée](../results/air_selection_light/integrated_perturbation_summary_20261001.json).
20/20 parties 5×6 complètes, fin 1976-02-01, sources inchangées. La moyenne des
deux répétitions est calculée **par graine**, puis sur les cinq graines :

| Graine | Δ profit Opex 1975, moyenne des deux répétitions |
|---|---:|
| 42 | −65 128 £ |
| 100 | +35 813 £ |
| 999 | +230 276 £ |
| 1234 | +296 808 £ |
| 5678 | −114 837,5 £ |

Moyenne **+76 586,3 £**, médiane **+35 813 £**, IC95 Student (4 ddl)
**[−147 693,6 ; +300 866,2] £**, 3/5 deltas non négatifs, p signes **1,0**.
Ratio des moyennes de profit **+5,12 %**, valeur **+2,14 %** : filtre pratique
pré-enregistré satisfait. Pas de gain économique causal revendiqué pour une
sonde, ni de neutralité statistique, ni de qualification par défaut.

Lectures détaillées : [rep1](../results/air_selection_light/perturbation_analysis_rep1/audit.json),
[rep2](../results/air_selection_light/perturbation_analysis_rep2/audit.json).
**939/942 invocations appariées (99,68 %), 1564 sélections identifiées valides**.
Trois dernières invocations sont censurées aux horizons ; pas de conflit ni de
fenêtre reconstruite. Les générations ciblées reprises existent dans le 5×6 ;
ne pas mélanger leur durée de vie et leur coût actif avec les scans synchrones.

Sur le périmètre commun `target=-1, band=0, sliced=0`, pondération par opcodes
sur les mêmes invocations entièrement couvertes des deux répétitions :

| Graine | hub→site | hub→hub | Premier poste |
|---|---:|---:|---|
| 42 | 33,95 % | 40,61 % | hub→hub |
| 100 | 48,13 % | 20,54 % | hub→site |
| 999 | 37,61 % | 30,02 % | hub→site |
| 1234 | 32,34 % | 39,50 % | hub→hub |
| 5678 | 32,61 % | 34,37 % | hub→hub |

**Aucun bloc unique premier sur ≥4/5 graines** : la porte pré-enregistrée pour
choisir automatiquement une optimisation n'est pas franchie. Les bandes de
bootstrap 1/2 ont seulement deux observations chacune par graine sur les deux
répétitions : pas de généralisation. Dans les seules publications catalogue
`path=full`, sélection ≈10,84–17,36 % selon graine/répétition, pas ≥20 % sur 4/5.
Les parts sont des opcodes conventionnels, pas CPU ; pas d'addition parent/enfants
ni de jointure implicite AIR↔sélection.

### Amortissement : exposition au classement, pas bénéfice d'achat

[Smoke r2](../results/fleet_amort_shadow/engine_smoke_20261001_r2.json) : 3/3 sains,
37 élections complètes. [Exposition deux ans](../results/fleet_amort_shadow/engine_exposure_20261001_r1.json) :
3/3 sains, fin 1972-02-01, sources inchangées.
[Synthèse](../results/fleet_amort_shadow/integrated_exposure_summary_20261001.json),
[instantanés décodés](../results/fleet_amort_shadow/integrated_exposure_snapshot_20261001.json).

- 48/48 élections mesurables, 20 avec fleet+nouvelle liaison, 61 occurrences de
  candidats flotte : 43 prédictives, 18 observées. Ordre témoin conforme partout.
- **369 inversions fleet↔nouvelle liaison, zéro changement de tête** avant
  compaction. Occurrences répétées d'élections, pas 369 décisions indépendantes
  ni 369 achats différents. Pas de gain marginal ou réalisé identifié.
- Amortissement ajouté médian **1640 £/an**, ratio amort/brut médian **7,47 %**,
  maximum **50,15 %**. Deux captures de réduction **4→1** (élections 27/28),
  mais pas la preuve d'un achat +1 au seuil exact avec inventaires/ordres vérifiés.
- Le shadow est perturbateur : calcul seul Δprofit1971 **−96 953 £**, valeur
  **−10,95 %** ; instantanés **−241 651 £**, valeur **−20,89 %**. Une graine ne
  sépare pas coût direct et trajectoire. Aucun A/B économique de l'amortissement.
- Copie/tri diagnostic p95 ≈3,98 M /4,07 M opcodes (calcul/instantanés), bien
  plus que le helper p95 ≈21 k. Le classement exhaustif diagnostique est donc
  coûteux : sonde OFF, ne pas la déployer comme instrumentation permanente.
  Coût de sérialisation/émission détaillée p95 ≈135 k, hors émission du bilan.

### R1/R3 et rechargement

[Smoke R1/R3](../results/r1_r3_mechanisms/engine_smoke_20261001_r1/report.json) :
un duel sain, 318 événements sans ligne mal formée, sources et copie inchangées.
`r3_dead` et `r3_cash` passent les conditions de **trace naturelle** ; les cas R1
exacts, inventaire, répétition, reload et R3 refus API réel restent non exposés.
Le harnais conserve `engine_validated=false` pour les huit scénarios dirigés.

Save/Load : [light](../results/three_lots_integration/save_load_20261001_r1/light/report.json),
[shadow](../results/three_lots_integration/save_load_20261001_r1/shadow/report.json),
[R1/R3](../results/three_lots_integration/save_load_20261001_r1/r1r3/report.json),
[lectures isolées](../results/three_lots_integration/save_load_analysis_20261001.json).
Les trois profils : **25 saves A +13 B**, santé officielle valide, checkpoint
chargé haché, `LOAD_RECONCILE` respectivement **10/10, 8/8, 14/14 lignes gardées**,
aucune ligne abandonnée. Compagnie humaine supplémentaire au reload conservée
dans les métadonnées ; compteurs physiques officiels limités à Opex.

AIR : 17 générations closes /55 sélections avant, 7/18 après ; **pas de scan
suspendu à la frontière de reload**, validation de cette reprise non acquise.
Shadow : 20 élections complètes avant, cinq après ; sixième bloc après reload
interrompu à l'horizon, explicitement rejeté/censuré, aucune fusion d'identités.
R1/R3 : traces naturelles saines, pas de frontière sélection/achat sauvegardée.

## Restant, sans nouvelle campagne automatique

- Fixtures dirigées dans le monde réel : R1 prix+tampon exact, juste dessous,
  mutation d'inventaire par API, deuxième soumission et checkpoint de mécanisme ;
  R3 construction réellement refusée après consommation du bypass. Le contrôle
  du monde, les barrières exactes et leur persistance ne sont pas livrés.
- Fixture VM des calculs shadow C70/C82/V92 et seuils R1 : Python + exposition
  naturelle ne valident pas toute cette matrice. Aucun réglage protégé activé
  pour simuler artificiellement une réussite.
- Réduire le coût du **diagnostic** exhaustif avant d'envisager sa réutilisation
  à grande échelle ; aucune correction de score économique adoptée.
- Profil AIR utile pour la suite, mais choix d'une intervention isolée encore
  à décider : pas de gagnant unique selon la porte 4/5, pas de retour automatique
  au préfiltre hubs/cadence/C121 rejetés.

**Intégration logicielle et tests réalisables terminés ; fixtures dirigées
incomplètes, qualification économique absente. Tous les nouveaux diagnostics
restent OFF au défaut, C115 inchangé, aucune publication.**