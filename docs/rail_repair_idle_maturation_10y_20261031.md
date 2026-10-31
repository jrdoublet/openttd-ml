# RAIL-REPAIR-IDLE — maturation à 10 ans des 5 lignes SITE sauvées

## Préenregistrement, 31 octobre 2026, avant toute simulation

Demande utilisateur : poursuivre les cinq lignes effectivement construites
avec `RAIL_BUILD site_repair=1` jusqu'en **1979**, et « enchaîner sur une
porte B si c'est prometteur ».

### Origine des lignes et limites de sélection

Dans le replay diagnostique **40×5**, `probes=258` / `-d script=4`,
cinq lignes SITE se sont construites sur cinq graines :

| Graine | OD des événements SITE / BUILD | Cargo | Date en 1974 |
|---|---|---|---|
| 100 | 46958→29140 | COAL | 18 août |
| 512 | 31408→39017 | IORE | 16 décembre |
| 12345 | 46126→50747 | GRAI | 13 novembre |
| 54321 | 12108→23443 | GRAI | 17 octobre |
| 65537 | 42142→29270 | GRAI | 18 février |

Les cinq graines sont **sélectionnées après exposition positive** : leur
résultat ne peut pas être projeté sur les 40 graines ni considéré comme
une nouvelle porte A. Le 40×5 économique initial demeure **NO-GO**
(+0,113 %, p=0,824, intervalle englobant 0).

### Étape 1 — cinq duels à 10 ans (diagnostic, pas porte A)

- Source IA sans modification, `origin/master=b4bbc4a3`.
- Même OpenTTD 15.3, OpenGFX 7.1, carte 256², inflation OFF,
  `1970–1979`, **5 graines** pré-sélectionnées, 1 répétition.
- RAIL seul ; témoin `mode_air=0,mode_road=0,mode_water=0,mode_rail=1`,
  quatre réparateurs OFF ; variante : mêmes modes, avec SITE, V131,
  A* et POSE `=1`, conditionnés aux six mois sans nouvelle ligne.
  `v233l_constructibilite=0` dans les deux bras.
- Pour maximiser la comparabilité **intra-duel instrumenté**, le témoin
  et la variante utilisent tous deux `probes=258`, journal moteur
  `script=4`. Conserver tous les `RAIL_BUILD`, `RAIL_SITE_REPAIR`,
  `RAIL_REPAIR_IDLE` et les erreurs. Le code de l'IA n'est pas édité.
  L'instrumentation change les opcodes par rapport au 40×5 économique.
- Parcourir les sauvegardes mensuelles ; lors de chaque décembre
  (1974–1979), lire les véhicules `VEHS`, les ordres `ORDL/ORDR`
  et les gares `STNN` via le décodeur existant
  `extract_line_telemetry`. Les profits de flotte
  `profit_this_year/256` sont **observés**, sans les convertir en
  profit net après CAPEX, gare, station ou dette. La mesure d'année
  entière à décembre reflète les mois écoulés et doit être distinguée
  du `profit_last_year` historique de flotte.
- Association **sans attribution forcée** des OD loguées aux services
  de gares et trains (carte 256², stations/cargo/ordres) ; éliminer
  les associations ambiguës. Documenter chaque ligne sauvée :
  existe-t-elle de nouveau en replay 10 ans avant fin 1974 ?
  Dispose-t-elle de trains attribuables univoquement en 1975–1979 ?
  Le profit de flotte à maturité est-il positif ? Distinguer prévision,
  profit d'exploitation réel, capital et profit causal.
- Vérifier **10/10 parties saines**, tous les clichés 1970–1979 et
  trajectoires appariées `profit_year` et `company_value` ;
  des lignes de même OD construites dans le témoin interdisent de
  prétendre à un effet causal exclusif.

**Règle préalable d'escalade vers la B**, seulement un *signal
exploratoire*, choisie avant calcul :

1. Au moins **3/5 OD** reproduites en `RAIL_BUILD site_repair=1`
   avant la fin 1974 dans le nouveau replay et associées sans
   ambiguïté à un service physique.
2. Au moins **3/5 lignes** avec un profit de flotte réalisé **>0**
   sur au moins un cliché mature 1976–1979, et aucune erreur de
   qualification dans les dix parties.
3. Delta moyen apparié `profit_year` terminal 1979 **>0**,
   ratio des valeurs moyennes **≥0,95** sur les cinq duels.

Si l'un de ces points est manquant/ambigu/négatif : **pas de B**,
rapport du blocage, aucune activation des défauts. Ce criblage
sur cinq graines sélectionnées est volontairement faible :
une B ne pourra jamais effacer un échec A préexistant.

### Étape 2 — B conditionnelle, 20 graines × 10 ans

Si les trois conditions précédentes passent, lancer **sans demander
une nouvelle autorisation** un duel RAIL seul `OFF` contre
`SITE/V131/A*/POSE=1`, les **20 graines initiales canoniques**
`bench_v2.SEEDS`, 1970–1979, 256², un seul worker pool
8 workers maximum, aucune concurrence Docker.

La B sera **une étude de non-érosion distincte**, car la vraie A 40×5
est déjà NO-GO : ne pas en déduire une adoption.
Contrairement au suivi diagnostic, la B est sans journal moteur et
`probes=2`, identique à l'instrumentation de l'A échouée.
Critères **préenregistrés** : 20/20 paires saines, delta
`profit_year` 1979 (ON−OFF), borne supérieure de l'IC95
bootstrap apparié **≥0**, ratio de moyennes
`company_value` **≥0,95**. Reporter aussi Wilcoxon, ratio de profit,
victoires/défaites et dispersion. Si B échoue, conclure NO-GO
non-érosion. Si B passe, documenter « B exploration non-érosion »
sans changer les défauts tant qu'une nouvelle A complète n'a pas
qualifié les réparations.

### Exécution et intégrité

Lanceur : `sweeps/run_rail_repair_idle_maturation_10y_20261031.py`,
analyseur : `sweeps/analyse_rail_repair_idle_maturation_10y_20261031.py`.
Sources NoAI tar SHA256 **figées** depuis le 30 octobre.
Les fichiers de résultats moteur restent dans `results/` (ignorés
par Git). Les conclusions et les agrégats individuels seront publiés
dans ce rapport et dans un petit JSON de preuve versionné.

**Aucun réglage IA par défaut n'est modifié.**

## Résultats de maturation — 5 graines × 10 ans, diagnostic

**10/10 parties saines**, 120 clichés mensuels par partie, tous jusqu'au
1er décembre 1979. Le préenregistrement a été fixé avant le calcul au
commit `ba680b44`. Résultat brut de la campagne diagnostique :
`results/rail_repair_idle_pilot_10y_20261031.json`, SHA256
`258f48e624fa61b5ecd1d908d5c2ab8bcffb2597822a46b6abd23d3f9699bddf`.
Les chiffres par année et l'identification physique des services figurent
dans [les preuves détaillées](rail_repair_idle_pilot_10y_20261031_evidence.json).

**Les cinq constructions SITE de 1974 ont été reproduites** à la même
OD/cargo. La lecture VEHS/ORDL/STNN a permis d'attribuer à chacune un
service RAIL sans ambiguïté (cargo correspondant, proximité des deux
gares, pas de concurrent proche). Les profits ci-dessous proviennent
des véhicules réellement présents aux clichés de décembre, en livres,
et **ne déduisent pas l'investissement en voies, gare, dépôt et véhicules**.

| Graine | Profit prédit au BUILD | Devis BUILD | Profit VEHS observé 1975* | Profit VEHS observé 1979* |
|---|---:|---:|---:|---:|
| 100 | +36 330 | 80 279 | +52 420 | +28 030 |
| 512 | +6 704 | 57 195 | +12 819 | +8 190 |
| 12345 | +4 738 | 47 445 | +5 132 | +6 102 |
| 54321 | +5 458 | 81 370 | +10 786 | +23 198 |
| 65537 | +20 064 | 82 606 | +26 280 | +27 429 |

\* `profit_this_year/256`, cumul d'année civile partielle à la
date de sauvegarde (1er décembre, environ onze mois). La présence
de trains et un profit VEHS positif à maturité ne garantissent pas
le remboursement du capital initial. En particulier, la ligne de
graine 100 a connu une année 1977 légèrement négative à la date de
snapshot, et un train renouvelé peut avoir son profit annuel
`profit_last_year` remis à zéro : ne pas extrapoler le profit par
véhicule à tous les trains historiques.

### Effet sur les sociétés à la fin de 1979

| Graine | `profit_year` variante − témoin |
|---|---:|
| 100 | +263 390 £/an |
| 512 | −11 522 £/an |
| 12345 | −6 524 £/an |
| 54321 | +97 718 £/an |
| 65537 | +181 795 £/an |

- Gain moyen apparié **+104 971,4 £/an, +5,4634 %** de la moyenne témoin ;
  **3 victoires / 2 défaites**, Wilcoxon bilatéral exact **p=0,3125**.
- IC95 bootstrap apparié [**+12 325,2 ; +197 617,6**] £/an, sur seulement
  cinq graines sélectionnées : aucun statut de confirmation indépendante.
- Ratio des valeurs moyennes : **109,7933 %**.
- Le service utilisant la même OD est aussi présent dans le témoin à la
  fin 1979 dans **quatre des cinq graines** ; on ne peut pas créditer
  automatiquement la totalité de la différence de profits aux seules
  lignes « sauvées ». Le diagnostic prouve la **construction effective**,
  l'**exploitation** et un **profit VEHS positif**, pas l'impact causal
  marginal exact après CAPEX.

Les **trois conditions préenregistrées** de promotion sont vraies :
5/5 constructions et associations non ambiguës, 5/5 lignes avec
profit VEHS mature positif, delta moyen décennal positif et
garde de valeur tenue. **La B exploratoire 20×10 a donc été lancée**,
sans nouvelle activation de réglage par défaut.

## Résultats de la B exploratoire 20×10 — non-érosion PASS, pas d'adoption

**40/40 parties** saines et complètes (20 graines appariées, 2 bras,
1970–1979, cartes 256², sans `script-debug`, `probes=2` par défaut).
Toutes les données jusqu'au 1er décembre 1979, 120 clichés mensuels
par partie, aucune erreur de script ni anomalie VEHS/STNN. Source brute :
`results/rail_repair_idle_b_10y_20261031.json`,
SHA256 **`be6c7c5eb15edf810050cb581ec45c99be6166f4e75660b3d4e96e7516632ebc`**.
Les 20 deltas et la décision calculée sont archivés dans
[le JSON des preuves de B](rail_repair_idle_b_10y_20261031_evidence.json).

| Mesure terminale, décembre 1979 | Référence OFF | Réparations ON |
|---|---:|---:|
| `profit_year` moyen | 2 102 608,05 £/an | 2 092 141,65 £/an |
| `company_value` moyen | 7 284 487,60 £ | 7 256 727,85 £ |

- Différence moyenne appariée : **−10 466,4 £/an**, soit **−0,49778 %**
  du témoin ; médiane **−11 158,5 £/an**.
- **8 victoires / 12 défaites, 0 égalité**, Wilcoxon bilatéral exact
  **p=0,57060** : aucun gain statistiquement confirmé.
- IC95 bootstrap de la moyenne appariée (20 000 tirages, seed 0) :
  **[−53 505,5 ; +34 582,25] £/an**. La borne haute est positive :
  critère de non-érosion à la B **réussi**, sans prouver que la moyenne
  du traitement est non négative.
- Ratio des valeurs moyennes **99,6189 %** : garde de valeur ≥95 %
  **réussie**.

**Verdict de B : `B_EXPLORATORY_NON_EROSION_PASS`** ; la porte
exploratoire **ne rejette pas** la non-érosion selon son protocole
unilatéral. Le gain moyen reste négatif ; elle ne démontre ni une
amélioration, ni un bénéfice global des réparations.

**Cohérence entre les expériences :** la maturation 5×10 est réalisée
sur cinq graines *sélectionnées parce que SITE avait construit* et
utilise `probes=258` (avec trace `-d script=4`), tandis que la B
utilise `probes=2` et 20 graines canoniques. La différence est réelle
et peut fortement modifier le parcours des parties : par exemple, la
graine 65537 donne **+181 795 £/an** dans le pilote instrumenté,
mais **−149 496 £/an** dans la B sans instrumentation. Ce ne sont
**pas** deux mesures interchangeables d'un même effet causal.

### Décision de mise en production

La porte A RAIL seul 40×5 est **NO-GO** (+0,113 %, p≈0,824),
et la B n'est qu'une non-érosion exploratoire expressément autorisée
après maturation. Le critère d'adoption (gain robuste sur A) n'a jamais
été franchi. **Tous les opt-ins demeurent à 0 par défaut, pas de
promotion**.

La prochaine hypothèse expérimentale devrait **isoler SITE**
(les cinq récupérations réelles) et chercher à augmenter sa
**sélectivité économique** après six mois d'inactivité ; les
secondes chances A* ont échoué dans le replay 40×5 et POSE/V131
n'y ont pas été observés. Toute nouvelle adoption exige une nouvelle
porte A indépendante et explicite, sans réinterpréter ce NO-GO.
