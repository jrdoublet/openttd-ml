# Audit parallèle — renforts AIR et capital immobilisé

Date : 30 septembre 2026. **Diagnostic hors ligne, pas de qualification économique.**

## Conclusion

R1 rend un lot partiellement finançable ; il ne démontre pas la valeur marginale
du prochain avion. Les sources locales examinées permettent d'identifier des
renforts, mais **aucun n'a un avant/après annuel complet exploitable** dans le
journal détaillé retenu. Impossible de les déclarer rentables ou improductifs.

Les trois fichiers de ce lot étaient absents avant création :

- `sweeps/parallel_fleet_audit.py` : lecteur JSON/JSONL, sortie JSON sur stdout ;
- `sweeps/test_parallel_fleet_audit.py` : fixtures synthétiques ciblées ;
- `docs/parallel_fleet_audit.md` : présent rapport.

Aucune écriture sous `ai/`, aucun harnais, dépendance, réglage, suivi commun ou
artefact de résultat modifié. Aucun conteneur, partie, commit ou publication.
C115 protégé ; expériences cadence OFF dans le code, inchangées. L'artefact
cadence historique analysé avait, lui, ses options expérimentales activées : il
ne représente pas le défaut. Git absent du PATH et `.git` absent : ni statut/diff
Git ni SHA de code vérifiables ; pas d'installation tentée.

## 1. Code existant, restrictions et hypothèses

Sources de décision lues : `AGENTS.md`, `CLAUDE.md`, `ai/OpexAI/CLAUDE.md`, état
courant de `docs/taches.md`, R1/R2 de `docs/revue_code_2026-09-30.md`, journal du
13 septembre (C59/C61), archive du 9 septembre et journal du 30 septembre.
Pas d'`AGENTS.md` supplémentaire trouvé sous `docs/` ou `sweeps/`.

### Code relu, et non gains mesurés

| Source actuelle | Contrat constaté |
|---|---|
| `task_air.nut::_resizeAirFleets` | Gardes liquidation, reconstitution de crash, cadence, santé, profit, stock et plafond physique. Le stock maximal aux deux gares dimensionne un lot plafonné à quatre au défaut. Le stock est une quantité, pas un temps d'attente. |
| `projects_selection.nut::OpexProjectFitFleetToBudget` | Après réserve, retire **1 000 £ une fois par lot**, réduit `want`, clone le projet et l'entrée. Vérifie `baseVehicles`. Avant plancher et classement commun. |
| `projects_builders.nut::OpexProjectFromFleet` | Chemin courant : `lastProfit / have` si positif, sinon repli modèle ; multiplie par `want`. Ce profit moyen observé n'est pas un rendement marginal. `profitIsObserved` protège la provenance R2. |
| Même fonction, C84/C121 | Branches marginales distinctes, non adoptées. R1 recalcule la marge C84 pour la quantité réduite ; pas de proportionnalité imposée à sa courbe. |
| `task_projects.nut::_tryBuildFleetProject` | Revalidation d'inventaire avant achat ; boucle unitaire. `added` et `replaced` séparés. Le log simple expose `replaced`, **pas C50** ; `added=0` ne signifie donc pas aucun achat. |
| `air_fleet.nut::OpexAirAddPlane` | Dernier contrôle prix + réserve + 1 000 £ ; transaction réelle distincte de l'admission au portefeuille. |
| `task_report.nut`, collecte vers lignes 261–280 et 400–409 | `profit` = somme du profit véhicule de l'année précédente pour les véhicules vivants au rapport. `rev = profit + runCost`, où `runCost` est la somme de `GetRunningCost` au rapport. **Recettes reconstruites**, pas encaissements directement mesurés. |

**Hypothèse à éprouver :** le profit moyen peut surestimer l'avion supplémentaire
quand la demande résiduelle ou la capacité temporelle d'aéroport est épuisée.
Une file de passagers élevée ne suffit pas : elle peut refléter une rotation
lente, une congestion, un chargement asymétrique ou des ordres inadéquats.
L'inverse (petit renfort profitable grâce à la fréquence) reste également possible.

**Restrictions conservées :** C61 AIR exige rotations, attente, demande et
occupation avant changement de capacité. C59 exige corrélation attente /
chargement au départ / profit. Ne pas supprimer le garde W ni le plafond ; ne pas
répéter les bras C50b. C85 précède C84 ; C84 seulement après le diagnostic C85
franchissant +50 k£/an et la garde de valeur ; aucun 20×10 avant ces portes.
Les fiches `24_c84_air_target_fleet.md` et `25_c85_air_equipment_frontier.md`
sont du contexte historique, pas une autorisation de réactivation.

## 2. Contrat du lecteur livré

Imports réutilisés, sans copier leur implémentation :

- `sweeps.harness._LINE_RE`, `_OPEX_RE`, `parse_fields` : champs et enveloppe ;
- `sweeps.game_health.parse_script_errors` : erreurs attribuées/non attribuées.

Ces modules sont utilisables sans lanceur. Les agrégateurs C50 anciens ne sont
pas importés : certains diagnostics modifient `subprocess` à l'import, réduisent
les identités/dates ou remplacent les champs absents par zéro.

API : `analyse_file(path)` / `analyse_payload(payload)`. Interface module
`sweeps.parallel_fleet_audit`, argument(s) positionnel(s) JSON/JSONL ; aucune
option d'écriture. Exécuter avec `-B` évite aussi les caches Python. La sortie
contient chemin absolu, SHA-256 du fichier, pointeur JSON, métadonnées connues,
compagnie issue de l'enveloppe, date du jeu normalisée **et brute**, numéro de
ligne du log, événement original, couvertures et limites.

### Jointures et prudence

- Chaque champ stdout est une portée autonome. Aucun cumul inter-checkpoints,
  campagne, répétition ou phases Save/Load ; les journaux peuvent se chevaucher.
  L'alias nettoyé n'est pas relu quand son raw non vide est disponible.
- Pas d'identité compagnie déduite d'un numéro de script. Sans compagnie/ligne
  attestées, pas de jointure. `lineId` interne n'est ni une gare ni un véhicule.
- Seul C50 `fleet_built mode=air` compte comme enregistrement de renfort AIR.
  `project_built mode=fleet` n'est **pas un deuxième achat**. Les doublons de
  renfort du même jour restent visibles et bloquent l'attribution plutôt que
  d'être arbitrairement supprimés.
- Le prix de `FLEET_PROJECT action=grow` est raccordé uniquement si compagnie,
  date, ligne, `added` et `want` concordent et la jointure est unique.
  `prix × added` est un **capital estimé**, pas la dépense comptable réelle.
- `want` journalisé est **déjà ajusté** par R1. `added == want` ne réfute pas
  un passage initial 4→1 ; `added < want` ne prouve que l'exécution partielle
  d'un lot sélectionné. `original_want` et `r1_budget_fit_exposed` restent nuls.
- Pour un achat pendant Y, baseline Y−1 et première année complète post-achat
  Y+1 (rapport Y+2). Rapport de baseline antérieur à l'achat, `age >= 2`,
  exercices cohérents, inventaires compatibles, absence d'autre événement flotte
  détecté dans la fenêtre. L'année d'achat n'est pas annualisée.
- Rapports annuels identiques = une observation ; rapports contradictoires =
  comparaison bloquée. Les effectifs au rapport ne prouvent pas l'absence de
  ventes/remplacements/crashs entre observations.
- `None`, quantité sentinelle négative, NaN/infini ≠ zéro. Zéro et pertes sont
  conservés pour les montants. Montants NoAI en £, sans division par 256.
  Aucun mélange PASS/MAIL ; aucun `len(VEHS)` utilisé.
- Santé : scan des marqueurs réutilisé, pas certification d'horizon complet.
  Erreur moteur/non attribuée ou touchant la compagnie : signal bloqué.
  L'absence de marqueur fatal ne certifie pas la santé du banc.

Deux signaux descriptifs seulement si les fenêtres sont disponibles :
`positive_before_after_signal` si Δ profit et Δ recettes proxy sont positifs ;
sinon `capital_at_risk_signal`. Sans données : `insufficient_observations`.
**Aucun n'est un verdict causal** ; le verdict économique reste
`not_identified_no_counterfactual`. Aucun seuil de rendement « suffisant » n'est
inventé après observation. Chargement, rotations, attente temporelle, occupation
et demande résiduelle restent non renseignés par ce lecteur C50.

## 3. Mesures sur les artefacts existants

Source détaillée : `results/save_load_exp_cadence_20260930_r2.json`, graine 42,
départ 1970, phase A 2 ans, phase B 1 an depuis sauvegarde **1971-01-01**.
Le fichier annonce `status=OK` ; le scan partagé ne trouve aucun marqueur fatal.
Ce n'est ni un duel causal ni une validation spécifique de R1.

SHA-256 : `e4422488f1b6d9e737c177eb527c5d494b512b171f3ca4ccc3b7441f56fedc58`.

| Mesure dans chaque stdout, compagnie 0 | Phase A | Phase B |
|---|---:|---:|
| Enregistrements de renfort AIR C50 | 10 | 6 |
| Somme des `added` connus | 12 | 9 |
| Jointures de prix uniques | 10/10 | 6/6 |
| Somme prix estimé × quantité | 438 860 £ | 334 272 £ |
| Rapports AIR de profit disponibles | 7, exercice 1970 | 7, exercice 1970 |
| Avant/après annuel complet exploitable | **0/10** | **0/6** |
| Exécutions `added < want` observées | 0/10 | 0/6 |
| Tags C117 / C98 trouvés dans le stdout | 0 / 0 | 0 / 0 |

**Ne pas additionner les phases** : la phase B rejoue une période de la phase A.
Tous les achats observés sont pendant 1971 ; les profits 1970 sont de démarrage,
et les profits de l'exercice complet 1972 manquent. Aucun gain, délai de retour
sur investissement ou nombre d'achats improductifs n'est identifiable.

Exemples vérifiables (numéros de ligne **dans la chaîne stdout**, pas le JSON) :

- `$/phase_a/openttd_output_raw:L5928` : 1971-05-03, ligne 1,
  `added=1 total=2 want=1`, estimation 38 964 £ ;
- même portée `L5938` : 1971-05-03, ligne 5,
  `added=2 total=3 want=2`, estimation 69 726 £ ;
- `$/phase_b/openttd_output_raw:L2147` : 1971-05-08, ligne 5,
  `added=4 total=5 want=4`, estimation 139 452 £.

La présence de quatre achats sur la même ligne après reload ne dit pas qu'ils
sont excessifs : horizon et mesures de service insuffisants. La section
`phantom_company_confound` du fichier signale aussi une compagnie humaine
supplémentaire au chargement ; elle est conservée comme métadonnée. L'audit ne
réutilise pas ses compteurs globaux de véhicules/stations.

Autres entrées effectivement lues avec le lecteur :

| Fichier sous `results/` | SHA-256 | Couverture d'événements individuels |
|---|---|---|
| `diag_review_opex_5x6_20260930.json` | `62dc830d097abe1a080374ebef6c9fd92c8860cb51d0ed5ac5a62c275673e0ab` | Aucun stdout non vide pris en charge ; aucune conclusion sur les achats |
| `diag_review_opex_5x6_20260930.jsonl` | `148f71bb28f7a482e8510a488bb3c1943c3e982367c46f5cce852f74be4ced02` | Même limite ; checkpoints financiers ≠ attribution par renfort |
| `diag_c69_fleet_batch_solo_5x6.json` | `bb5ad8de78a069695af5f058b0acd3591dfcf2f979dd690b272a38bcc0fa00cc` | Agrégat sans stdout pris en charge ; aucune ancienne performance requalifiée |

Absence confirmée des chemins `results/lineprofit_default_5x6_20260926.json`,
de son `.jsonl`, et `results/diag_c117_air_throughput_5x6_20260927.json`.
Cette recherche bornée ne prouve pas l'absence de toutes les autres archives.

## 4. Validation exécutée

- Python venv existant 3.14.4, sans installation ni changement de dépendances.
- `sweeps.test_parallel_fleet_audit` : **26/26** fixtures réussies.
- `sweeps.test_r1_partial_fleet` : **8/8** contrats existants réussis.
- Exécution ciblée via `unittest`, `-B -X utf8`, **34/34** au total.
  La découverte intégrée de l'éditeur n'a trouvé aucun test ; exécution explicite
  de ces deux modules seulement. Aucun test général lancé.
- Analyse des quatre entrées ci-dessus en mémoire et affichage terminal seulement.
  Pas de nouveau JSON/JSONL de résultats ni extraction d'archive sur disque.
- Interface CLI exercée sur l'artefact Save/Load : sortie JSON décodable,
  SHA-256 et couvertures identiques à l'API. Aucun diagnostic éditeur signalé
  dans les trois fichiers ; contrôle des espaces finaux propre. Diff Git
  indisponible, vérification par relecture des fichiers créés.
- Les tests couvrent absences/zéros/pertes, unités, périodes partielles,
  provenance, santé, inventaires, jointures ambiguës, doublons, phases/repeats
  isolés, prix estimé, quantité ajustée R1 et remplacement non identifié.

**Ces tests Python ne compilent pas Squirrel**, ne réalisent aucun achat et ne
valident ni l'économie de R1 ni les plafonds de C61.

## 5. Prochaine intervention minimale — raccordement proposé, non effectué

Après clôture des éditions, centraliser une sonde passive symétrique, avant tout
changement comportemental. Ne pas commencer par relever un plafond.

1. **À `_resizeAirFleets` / `OpexProjectFitFleetToBudget` :** identifiant stable
   `decision_id` + révision, `lineId`, stations, moteurs/cargos, `have`,
   `want_original`, `want_fitted`, budget après réserve, tampon, prix, stock A/B,
   plafond/cadence et motifs de rejet. Le lot réduit doit conserver sa filiation.
   Pas d'`AILog` non contrôlé dans chaque itération : journaliser une décision
   bornée après calcul, en réutilisant les sondes/probes et leur coût mesuré.
2. **À `_tryBuildFleetProject`, autour de l'exécution :** même identifiant,
   quantité réussie, `added` **et** `replaced`, `vehicle_id`/moteur, date de mise
   en service, dépense réelle et produits de vente séparés. Réutiliser
   l'accounting C63, sans comptabilisation imbriquée qui doublerait les coûts.
   Ne pas inférer le coût d'achat de la seule baisse du cash.
3. **Au rapport et aux transitions de service existantes :** historique de
   composition, profit/coûts/recettes avec leurs périodes, dates de vente/crash,
   réconciliation ligne↔stations↔véhicules. Réutiliser la collecte C117 pour
   chargement au départ, trajets simples achevés, jours observés, transitions
   manquées, attente et débit PASS/MAIL séparés ; `diag_c117_air_throughput.enrich`
   est le calcul offline existant, non recopié ici. Sa période normalisée est
   30,4 jours, pas un mois civil ; les trajets simples ne sont pas des rotations
   aller-retour. L'occupation temporelle partagée de l'aéroport exige encore un
   raccordement explicite, pas une capacité statique ou vitesse instantanée C98.
4. **Qualification technique R1 centralisée :** besoin 4, budget prix+1 000 £
   après réserve pour un seul, puis juste sous le seuil ; vérifier classement,
   inventaire caduc, absence de double achat et Save/Load. C'est une preuve de
   mécanisme, pas de profit. Aucun banc lancé par ce lot.
5. **Puis seulement**, si les fenêtres sont complètes et la nouvelle hypothèse
   admissible, comparer des politiques isolées sur mêmes cartes/adversaire et
   sources figées. Pré-enregistrer seuil utile, horizon, garde de valeur et
   traitement des coûts avant résultats. Mesurer l'incrément de profit Opex
   et le capital réellement engagé, pas le profit moyen existant ni le seul
   ratio contre AAAHogEx. Ne pas contourner les interdictions C84/C85/C121.

Priorité immédiate : rendre observables **quantité initiale → quantité admise →
achat → service réalisé** sur la même identité. Aucun seuil ni nouveau réglage
de flotte n'est justifié par les données présentes.