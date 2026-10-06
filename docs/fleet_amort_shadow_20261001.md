# Renfort AIR legacy — amortissement parallèle, 1er octobre 2026

> **Suite intégrée le 01/10 :** sonde OFF `fleet_amort_shadow_probe=0/1/2`,
> capture complète à l'élection et adaptateur moteur raccordés. Exposition :
> 48 élections complètes, 369 inversions de paires, zéro changement de tête.
> [Bilan central et limites](three_lots_integration_20261001.md). Le texte
> ci-dessous décrit la livraison initiale, qui n'avait pas encore d'appelant.

## Verdict et périmètre livré

**Écart comptable confirmé ; importance au classement encore non mesurable.**
Le numérateur legacy ne déduit pas l'amortissement des avions ajoutés. La nouvelle
liaison AIR le déduit déjà, ainsi que celui des aéroports neufs. Le helper livré
permet d'observer la différence sans changer le profit du sélecteur.

**Aucun appel du helper dans le chemin courant.** L'activation, l'identité et
l'émission à l'élection restent un raccord du lot sélection/intégrateur (§4).
Il n'y a ni référence à un nouveau global non déclaré, ni réglage ajouté, ni
cache shadow dans les projets. Aucun défaut modifié ; C115 protégé, cadence OFF,
C84/C85/C121/C122 non réactivés. Pas de partie, conteneur, installation, commit,
push, nettoyage, ni écriture dans les harnais ou le suivi commun.

Fichiers de ce lot seulement :

- [projects_builders.nut](../ai/OpexAI/projects_builders.nut) : ajout isolé de
  `OpexFleetAmortShadow`, aucune modification des fonctions préexistantes ;
- [parallel_fleet_amort_shadow.py](../sweeps/parallel_fleet_amort_shadow.py) :
  contrat arithmétique Python et lecteur passif ;
- [test_parallel_fleet_amort_shadow.py](../sweeps/test_parallel_fleet_amort_shadow.py) ;
- ce rapport ;
- [validation_20261001.json](../results/fleet_amort_shadow/validation_20261001.json) :
  résumé des contrôles exécutés et empreintes (pas un résultat moteur).

Contexte relu : `AGENTS.md`, les deux `CLAUDE.md`, état courant de `taches.md`,
[intégration](parallel_integration_20261001.md),
[audit sélection §7](parallel_selection_audit.md#7-une-seule-correction-candidate-à-examiner-ensuite),
[audit flotte](parallel_fleet_audit.md), revue et contrats R1/R2. Les anciennes
revues sont historiques : R1/R2 sont déjà implémentés, pas à recoder ici.

## 1. Conventions reconfirmées dans les sources

### Nouvelle liaison

`air_route_economics.nut::OpexAirEconomics` calcule :

- revenu annuel converti en entier ;
- fonctionnement = nombre d'avions × coût nominal annuel + maintenance des
  seuls aéroports neufs si l'infrastructure maintenance est active ;
- amortissement avions = **nombre × prix / durée**, division entière après
  multiplication ; aéroports = `(newAirportCount * price * INFRA_AMORT_PCT / 100) / 30` ;
- profit = revenu − fonctionnement − amortissement.

La durée AIR legacy est **20 ans**, pas systématiquement la durée API du moteur.
Seulement sous `V92_AIR_SERVICE_CHOICE`, `plane.ageYears > 1` la remplace.
Les vues catalogue renseignent `ageYears = AIEngine.GetMaxAge(engine) / 365`.
Ne pas introduire cette durée au défaut où V92 est OFF. C115 sélectionne son
équipement/économie dans les chemins existants ; ce lot n'y intervient pas.

### Renfort legacy

`OpexProjectFromFleet` utilise, pour les entrées qu'il accepte :

1. `have = vehCount > 0`, sinon longueur de `vehicles` ;
2. si `lastProfit > 0`, `perPlaneProfit = lastProfit / have` et
   `profitIsObserved = true` ;
3. sinon, si `predRevenue > 0`,
   `perPlaneProfit = (predRevenue - running) / planes`, avec les replis historiques
   `running = predRunning` sinon 0, `planes = predTrains > 0` sinon `have` ;
4. refus si le profit unitaire est non positif ; sinon multiplication par `want`.

Ces replis **déjà présents dans le code décisionnel** ne sont pas une permission
pour le lecteur de transformer des données absentes en zéro. Le lecteur exige
le profit et sa provenance effectivement figés. Il ne relit pas `lastProfit`
actuel pour réinventer le calcul à l'élection.

Le réalisé provient des profits véhicules de l'exercice précédent, après leurs
coûts de fonctionnement mais sans amortissement économique des achats ni charges
compagnie complètes. Dans le repli, le fonctionnement prédit est déjà soustrait.
**Ne soustraire une seconde fois ni `predRunning`, ni `predAmort`** (qui inclut
une référence d'infrastructure). Les champs de recettes legacy ne sont pas un
journal d'encaissements ; ils ne changent pas dans le shadow.

`_resizeAirFleets` fournit `entry.planePrice`, généralement le prix du moteur du
premier avion vivant sous `AIR_FLEET_LINE_PRICE`. Ce prix est celui du projet,
pas la preuve de la dépense future ; conserver sa date et sa provenance lors du
raccord, sans requoter les candidats ou refaire le choix C115.

### R1 / R2 et branches hors périmètre

- R1 clone projet/entrée, réduit `want` après réserve et tampon unique de
  1 000 £, puis recalcule profit/revenu/capital. `baseVehicles` détecte un
  inventaire caduc. Quantité demandée, admise et achetée restent distinctes.
- R2 : C70/C82 retournent immédiatement le profit marqué observé. Le repli
  prédictif reste calibrable. **C82 remplace le chemin C70 selon les réglages,
  ce n'est pas le produit de deux facteurs.**
- C84 et C121 ont leurs marges propres. Le helper refuse toute activation de
  C84 ou C121, même pour une ligne hors cible : exclusion volontairement plus
  large que la branche marginale, jamais seconde charge sur ces marges.

## 2. Estimation alternative exacte

Pour le projet **déjà ajusté par R1**, quantité $q$, prix projet $p$, durée AIR
$L$, profit legacy figé $G$ :

$$A_{ajout}=\left\lfloor\frac{q p}{L}\right\rfloor,\qquad N=G-A_{ajout}.$$

Les entrées prix/quantité sont des entiers positifs ; aucun arrondi par avion
avant multiplication. Aucun amortissement d'aéroport, tampon ou réserve n'entre
dans $A_{ajout}$. Le net peut être **nul ou négatif** : aucune borne à zéro dans
le helper. Seul le score commun `OpexProjectScore` borne un profit non positif.

Le helper reçoit `project, enabled=false, plane=null`. Il retourne `null` si
inactif/hors périmètre/incomplet, sinon une nouvelle table :
`quantity`, `planePrice`, `lifeYears`, `profitSource`, `profitIsObserved`,
`grossProfitAnnual`, `addedAmortAnnual`, `netProfitAnnual`,
`calibratedProfitAnnual`. Sous V92, l'appelant doit fournir la vue modèle du
moteur ajouté, sans choix moteur nouveau ; une vue absente donne `null`.

La calibration réutilise **`OpexCalibratedProfit` sur un clone local** où seul
`profitAnnual` vaut $N$. Le marqueur R2 reste copié. Donc observation → $N$ ;
repli prédictif avec calibration effective $k$ → $kN$, pas $kG-A$.
Le prix/durée de vie est la même convention comptable ; $kA$ est la différence
des numérateurs calibrés du repli, **pas un autre amortissement comptable**.

Exemple synthétique, sans partie : $p=30\,019$, $L=20$, profit unitaire 2 000 £.

| Lot admis | Brut | Amortissement ajouté | Net shadow |
|---|---:|---:|---:|
| 1 | 2 000 | 1 500 | 500 |
| 4 | 8 000 | 6 003 | 1 997 |
| 4→1, recalcul après R1 | 2 000 | 1 500 | 500 |

Diviser 1 997 par quatre donnerait 499 et serait erroné. Pas de résultat shadow
stocké sur le lot initial : chaque appel lit la quantité de son projet ajusté.
Un achat réel inférieur à cette quantité exige une observation d'exécution
distincte ; ne pas réécrire rétroactivement l'instantané d'élection.

**Ce calcul ne résout pas « profit moyen ≠ profit marginal ».** Il ne mesure ni
demande résiduelle, ni congestion, ni revenu incrémental, ni profit compagnie.

## 3. Lecteur livré et preuves existantes

`estimate_shadow` est un **contrat arithmétique Python**, pas une traduction
exécutable du sélecteur Squirrel. `analyse_file` lit JSON/JSONL/log, conserve
chemin et SHA-256 ; CLI module `sweeps.parallel_fleet_amort_shadow`, chemins
positionnels, stdout JSON seulement. Aucun lanceur ni écriture automatique.

Les anciens formats passent par `parallel_fleet_audit.analyse_payload` : mêmes
collecteurs, marqueurs, propriétaires, pointeurs et phases, sans duplication.
Le lecteur ne tente ni une jointure C50→élection, ni un classement des seuls
survivants, ni une conversion de `C69_LAST_AFFORDABLE` en ensemble complet.

Lectures effectivement exécutées, empreintes dans le fichier de validation :

| Source sous `results/` | Couverture réutilisée | Inversions |
|---|---|---|
| `save_load_exp_cadence_20260930_r2.json`, phase A | 10 événements AIR, 12 ajouts connus | non mesurables |
| même source, phase B | 6 événements AIR, 9 ajouts connus | non mesurables |
| `diag_parallel_integration_20261001_r2.artifacts/profile_42.log` | 0 événement AIR C50, quantités inconnues | non mesurables |
| même dossier, `reference_42.log` | 0 événement AIR C50, quantités inconnues | non mesurables |

Phases Save/Load **non additionnées**, profil et témoin non fusionnés. Aucun
avant/après annuel complet dans ces portées. Zéro événement collecté n'est ni
zéro renfort réel, ni zéro inversion. Aucune estimation de l'écart comptable
historique n'est fabriquée à partir d'un prix d'exécution et d'un profit partiel.

### Contrat futur des instantanés

Entrée normalisée : objet `schema="fleet_amort_elections_v1"`, tableau `elections`.
La fixture `snapshot()` du test est un exemple **synthétique** complet, pas une
trace moteur. Chaque élection exige :

- `campaign, arm, seed, repeat, company, phase, decision_id, revision, date` ;
- `complete=true`, `candidate_count`, `all_admitted_before_limit=true`,
  `order_source="selector"`, `comparison_scope="fixed_admission"` ;
- `settings` avec booléens `c84,c85,c121,c122,v92,calibrated,cadence_off`,
  les quatre premiers faux, cadence_off vrai et `c115=1` ;
- `candidates` et les permutations **complètes** `baseline_order`,
  `alternative_order`, calculées en VM par le sélecteur, avant limite/compaction.

Chaque candidat contient `id` (action + révision, attribué par le sélecteur),
`mode`, `category` (`fleet_legacy`, `new_link` ou `other_unchanged`), `baseline`
et `alternative`. Chaque vue contient `profitAnnual, calibratedProfitAnnual,
score, context`. Le `score` est le score de comparaison **après bonus early-slot**.
`context` doit être identique dans les deux vues, avec :
`budget, finance_capital, denominator, calibration_factor, priority,
early_slot_bonus_pct, revenue_annual, admitted, stable_index, quantity`.

`calibration_factor` est le facteur **effectivement appliqué**, donc 1 pour R2
ou calibration désactivée. `priority` est la classe lexicographique effective
C77 + éventuelle priorité V88 ; `early_slot_bonus_pct` est le bonus effectif
(0 s'il ne s'applique pas). `stable_index` garde l'ordre d'insertion avant tri.
Le budget est celui après réserve de cette même passe, commun à tous.
Le dénominateur est celui de `fundScore`, **pas le `c69Score` de sonde** : conserver
l'exemption flotte C69 et la finance propres à chaque candidat.

Pour `fleet_legacy`, ajouter `project` contenant au minimum `mode="fleet"`,
`profitAnnual`, `profitIsObserved`, `payload.want`, `payload.planePrice`,
`payload.line.mode="air"`. Il s'agit d'une **copie scalaire figée**, pas de la
ligne vivante ; sous V92 ajouter `plane` avec la vue du modèle (`ageYears`).
L'intégrateur conservera en plus la quantité initiale et l'identité moteur/prix
dans son snapshot commun, sans les déduire de la quantité ajustée.

Le lecteur contrôle la complétude, les identités uniques, les contextes égaux,
les budgets, R1/R2, la calibration et l'arithmétique du score. Il exige les deux
ordres, **ne les reconstruit jamais**. Une tolérance de 1e-6 sert uniquement à
vérifier les nombres issus des floats/logs, jamais à trancher les égalités.
Les inversions sont les paires dont l'ordre est renversé dans les permutations
émises ; le sous-ensemble `fleet_vs_new_link_inversions` isole la question métier.
`winner_changed` désigne la **tête avant compaction**, pas l'achat finalement
exécuté. Ni le lecteur ni ces instantanés ne simulent une autre politique.

Un ensemble vide explicitement complet est mesurable sans inversion ; un
ensemble absent/tronqué, un ID doublonné ou un champ manquant donne null et un
motif, pas zéro. Deux élections identiques dans le même payload sont bloquées.
Les records JSONL restent séparés : aucune somme multi-checkpoint, aucune
déduplication inter-fichiers prétendant identifier des observations indépendantes.
La santé du jeu et les hashes de sources restent à contrôler par le harnais ;
un snapshot cohérent n'est pas une certification de santé/horizon.

## 4. Raccordements nécessaires — non réalisés dans ce lot

1. **Activation par l'intégrateur** : proposer `fleet_amort_shadow_probe`, booléen
   0/1, quatre défauts 0 dans `info.nut`, global `FLEET_AMORT_SHADOW_PROBE <- false`
   déclaré dans `globals_pre.nut`, chargement dans `OpexLoadSettings` à la manière
   des sondes existantes. Ce nom est une proposition **non déclarée actuellement** :
   ne pas le passer à un harnais avant raccord. Aucun `GetSetting` dans une boucle.
   Le helper ne lit pas ce futur global : l'appelant passe explicitement `true`.
2. **Sélecteur, réservé au lot 3** : après `OpexProjectFitFleetToBudget` et les
   filtres d'admission **inchangés**, capturer chaque candidat admis **avant**
   `OpexProjectInsertDefensive(..., limit, ...)`. Couvrir aussi la branche de
   secours `affordable.len()==0 && floorProfit>0`, sous une passe identifiée,
   sans doubler la même élection. Ne pas partir de la liste finale bornée.
3. Appeler `OpexFleetAmortShadow(project, true)` pour la flotte legacy ajustée,
   jamais le projet du vivier avant R1. Sous V92, passer explicitement la vue
   modèle du matériel ajouté ; pour le protocole ci-dessous V92 reste OFF.
   Copier ses scalaires immédiatement dans le snapshot commun. L'absence de
   résultat bloque la mesure de l'élection si un candidat fleet est concerné.
4. Sur des **copies diagnostiques uniquement**, garder budget, admission/plancher,
   recettes de départage, capital, quantité, dénominateur, calibration, classe C77,
   bonus early-slot et ordre stable. Calculer le score alternatif avec
   `OpexProjectScore(shadow.calibratedProfitAnnual, denom_effectif)` ; réutiliser
   `OpexProjectInsertDefensive`/`OpexProjectSelectionScore` sur les copies, limite
   = nombre total des admis, flags de politiques identiques et interdits OFF.
   Rien ne revient dans `affordable`, le vivier ou les caches de décisions.
   Les copies sans amortissement doivent reproduire exactement l'ordre témoin.
   Ne pas appliquer à nouveau C70/C82 sur `calibratedProfitAnnual`.
5. Ce test maintient **l'admission actuelle figée**, même si le net shadow devient
   négatif. Ne pas recalculer le plancher relatif sur les nets : ce serait une
   seconde intervention. Capturer les ordres **avant** réserve/compaction AIR et
   autres réordonnancements aval ; ne pas appeler les finaliseurs décisionnels
   une seconde fois. Leur éventuelle influence sur l'achat réel est hors mesure.
6. **Émission/collecte, intégrateur** : identité et révision viennent du snapshot
   commun du sélecteur. Réutiliser `OpexDecide`, les enveloppes et stdout bruts du
   harnais courant, pas des panneaux limités à 31 caractères. Vérifier la garde
   `decision_log` (ou raccorder la nouvelle sonde au mécanisme commun) : activer
   un flag sans canal effectif n'est pas une collecte. Émettre ouverture, candidats,
   clôture/compte et deux ordres ; l'adaptateur doit refuser les blocs incomplets,
   convertir vers le schéma §3 et conserver localisateurs/provenance. **Cet
   adaptateur d'événements futurs n'est pas implémenté ici** : ne pas présenter le
   lecteur de JSON normalisé comme déjà raccordé au moteur. Aucun scan de carte,
   appel API de profit ni rechoix C115 nécessaire au helper.

L'état shadow est transitoire, pas à sauvegarder dans les lignes. Au reload,
reconstruire une nouvelle élection depuis R1 et distinguer la phase/époque de
session pour éviter une collision d'IDs. Les événements d'achats continuent de
distinguer `added`/`replaced` et quantité initiale/admissible/livrée.

## 5. Protocole moteur pré-enregistré — À EXÉCUTER PAR L'INTÉGRATEUR

**Pas de lancement pendant les éditions parallèles.** Prérequis : lots stabilisés,
raccord §4 testé, sources réellement exécutées figées avec `campaign_freeze`,
hashes avant/après, réglages et bibliothèques/adversaire/runtime vérifiés.
OpenTTD 15.3 / NoAI 15 / OpenGFX 7.1 / OpenTTDLab 0.0.75. Aucune publication
implicite pour satisfaire ces prérequis.

### Porte A — compilation et fixtures techniques

- Smoke **graine 42, un an depuis 1970**, via harnais existant, puis fixture
  moteur ciblée sur des tables projet (même VM/helper) : prix 30 019, durée 20,
  quantités 1 et 4 ; budget après réserve **31 019 £** donne 4→1, **31 018 £**
  refuse ; inventaire caduc refusé. Vérifier qu'aucun double achat n'est introduit.
- Profits 2 000, 1 500 et 10, observation puis repli prédictif ; C70 et C82 testés
  séparément aux facteurs 0,5 / 1 / 1,5 **sur la fixture**, sans changement des
  réglages protégés dans une campagne. R2 attend le même net observé pour tous.
- C84/C121 restent OFF en partie ; tests statiques des branches préexistantes,
  pas activation économique pour exercer le refus du helper. V92 durée 25 et
  durée <=1 : fixture pure en VM, pas réouverture de la politique de remplacement.
- Save/Load via `save_load_roundtrip.py` : mêmes données recalculées après R1,
  nouvelle identité de phase ; pas de valeur shadow périmée stockée à restaurer.

### Porte B — exposition légère et coût, pas banc économique

Plan borné fixé avant résultats : **graine 42, départ 1970, deux ans**, fin
exigée **1972-02-01**, trois duels techniques distincts contre AAAHogEx-115 :

1. témoin : sonde OFF, autres paramètres courants ;
2. calcul seul : helper + copies/classement diagnostic ON, émission détaillée
   OFF, bilan agrégé de coût à la clôture ;
3. calcul + instantanés complets ON.

Les modes calcul/émission sont à prévoir dans le raccord commun (ou deux gardes
diagnostiques séparées), **pas des bras déjà disponibles**. Même debug script et
canal de logs de base dans les trois bras. Éviter les sept sondes larges du r2
qui ont perturbé fortement la trajectoire ; ne pas les activer pour ce lot.
Toutes politiques, dont C115=1, restent identiques ; cadence/C84/C85/C121/C122 OFF.

Ressources : lancement centralisé seulement, **plafond global 12 CPU / 12 workers**,
pas 12 par agent. Choix conservateur pour ce protocole : un conteneur, 3 CPU,
2 Go sans swap, cache `openttd-lab-home`, au plus 3 workers, aucun autre banc
concurrent. Si profil VPS, ces limites locales restent impératives.

Réutiliser les collecteurs/santé/compteurs physiques existants et une sortie
neuve sous `results/fleet_amort_shadow/engine_<identifiant>/` ; ne pas écraser
les preuves d'audit. Le bilan doit comporter :

- nombre d'élections, nombre complètes/incomplètes et raisons ;
- élections complètes avec au moins un fleet legacy et une nouvelle liaison,
  par provenance observée/prédictive, quantité, classe de priorité et mode ;
- distributions $A$, $G$, $N$, ratio $A/G$ pour $G>0$, score avant/après,
  rangs VM, inversions fleet↔nouvelles liaisons et changements de tête ;
- réductions R1 4→1 avec identités/quantités originales et ajustées ; aucune
  sélection des seuls cas inversés ni reconstruction des candidats manquants ;
- coût helper, copie/tri, sérialisation/émission **séparément**, médiane/p95/max
  et somme sur la couverture mesurée. Utiliser `OpexOpsMeasureBegin/End`, marques
  locales de `budget.nut`, pas un `OpexBudget.begin` imbriqué partagé. Garder une
  mesure enveloppante de sélection et ne pas sommer parent + sous-étapes ;
- contrôle à vide des marques ; nombre/octets d'émissions, ticks et dates
  calendaires, éventuelles suspensions. **Opcode conventionnel ≠ temps CPU**.
  Les coûts d'émission différés peuvent être consignés au bilan suivant ; une
  dernière fenêtre non close reste censurée, pas un coût nul ;
- santé/horizon, réglages effectifs, hashes et différences de trajectoire des
  trois bras. Les profits/valeurs servent de contrôle de perturbation, **pas**
  d'estimateur causal du coût de la sonde ou du bénéfice d'amortir la flotte.

Critères fixés : compilation/contrats/Save-Load OK ; aucun champ décisionnel
modifié par la mesure ; ordre témoin diagnostique exactement égal au sélecteur
sur son périmètre ; au moins une élection complète avec fleet et nouvelle liaison
pour déclarer le mécanisme exposé. Sinon **non exposé/non mesurable**, pas zéro
effet. Une inversion n'est pas nécessaire au succès technique et n'est pas un
gain économique. Pas de seuil d'adoption ni de seuil de neutralité inventé sur
une graine. **Arrêt après ce protocole**, même sans inversion ou réduction R1
naturelle ; aucun 5×6/20×10, aucun changement de défaut automatique.

## 6. Validation exécutée et limites

- Python 3.14.4 du venv existant, `-B -X utf8`, aucun package installé.
- Découverte de tests de l'éditeur : aucun test trouvé ; runner `unittest`
  explicite avec `sweeps` ajouté au chemin pour les contrats existants.
- **67/67 réussis** : 27 shadow, 8 R1, 6 R2, 26 lecteur flotte ; exécution
  0,094 s. Pas de suite générale ou partie lancée.
- Contrôle d'intégrité : le fichier builder, une fois le seul bloc ajouté
  retiré, a exactement son SHA-256 texte UTF-8/LF initial
  `399ee1dc158c20331af11d232d4d38429b47deaff0d91d30fefcc2fa80672cb0`.
  Cela inclut les branches C84/C121 et les constructeurs de nouvelles liaisons.
  Empreintes modèle AIR, calibration, choix moteur C115 et tests R1/R2 inchangées.
- Aucun diagnostic éditeur sur les trois sources du lot. **Ni ces contrôles ni
  les tests Python ne compilent Squirrel.** Compilation, coût, exposition et
  influence effective sur le classement restent à mesurer après raccord.
- Git/rtk absents du PATH et copie sans `.git` : pas de statut/diff Git ni de
  SHA de dépôt attestable. Préservation contrôlée par empreinte du builder et
  relecture ; ne pas attribuer à ce lot les modifications concurrentes hors
  de son périmètre.

Conclusion : une définition comptable précise et un dispositif de mesure sont
livrés, **pas une correction de classement adoptée**. L'amortissement homogène
ne démontre ni la rentabilité du prochain avion ni celle d'une autre politique.