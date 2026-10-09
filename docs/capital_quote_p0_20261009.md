# P0 Capital — devis physiques, risque de financement et apprentissage (09/10/2026)

## Décision et périmètre

Variante expérimentale `capital_quote_learning=0` aux quatre difficultés,
activable à `1` pour apprendre par construction. Aucun réglage historique
n'est adopté à cause d'un diagnostic de devis seul. Le code physique AIR C121,
le filtrage des candidats RAIL et les priorités du scheduler n'ont pas été
modifiés. **Le commit de traçabilité du chantier est autorisé le 09/10 ;
aucun push demandé.**

Le mot **devis** désigne ici le capital des composants construits. Le
**capital de financement** est le devis corrigé **plus** les tampons de
trésorerie, les fonds immobilisés en transit et éventuelles provisions
explicitement distinctes. Le **débit effectivement constaté** est
`AIAccounting.GetCosts()`; un échec peut conserver une infrastructure,
donner lieu à remboursement ou nécessiter une liquidation différée.

## Inventaire effectif et composants du devis

| Mode | Devis avant chantier / exclusions physiques | Politique de financement active/OFF | Réel observable |
|---|---|---|---|
| AIR | Aéroports neufs × prix du catalogue + nombre d'avions × prix moteur; C121 sous `air_site_cost_quote=1` ajouterait coût de nivellement simulé et provision des arrêts joints. Ce réglage V126 est **OFF** au défaut. | `OpexAirRequiredMargin`: 30 000 £ pour deux aéroports, 12 000 £ pour un, 2 000 £ pour aucun; s'ajoute à `OpexCashReserve` et à l'immobilisation en transit. La marge est **du cash disponible requis, pas une dépense**; sous V126 valide, 2 000 £ + % site, défaut % = 0. `AIR_MARGIN` actif via `policy_air=1`. | `air_construction.nut` : `AIAccounting` des terrassements, aéroports, avions, arrêts; tests d'arrêts joints protégés du coût simulé lorsque la variante est ON. Pertes différées R19 et actif BFAIL retenu restent à suivre. |
| RAIL | `economy.nut`: distance × prix voie/tile × `RAIL_TERRAIN_FACTOR/100`, 2 quais × longueur × coût station, véhicules (locomotives et wagons), dépôt si réglage. `OpexPrepareRailRoute` remplace cette estimation par un `AITestMode` de sites, voies, relief, ponts/tunnels, plus véhicules/dépôt forfaitaires; la seconde voie et certains dépôts restent imparfaitement prévus. | Initialiseur **100** aligné sur `rail_terrain_factor=100` chargé à toutes difficultés (ancien initialiseur 170 écrasé). `rail_finance_bias_pct=100`. `rail_depot_cost=0` au défaut; garde `OpexCashReserve()`. | `builder_rail.nut`: devis AITestMode puis `AIAccounting` vrai incluant deuxième voie/véhicules/échecs; résultat reconcilié à l'économie après succès. Avant A*, `preCapital` et nombre initial de rames sauvegardés pour les observations comparables. |
| ROAD | Distance route estimée × prix route par tuile, 2 arrêts au tarif bus/truck, dépôt, coût de N véhicules. La géométrie exacte et le capital sont recalculés juste avant construction. | `CAPITAL_CALIBRATION` activé par `policy_portfolio=1` applique historiquement **121 %** au seul filtre de financement (pas au coût physique). `ROAD_CAPITAL_MARGIN=1 000 £` et réserve de trésorerie restent séparés. Sous variante ON le facteur correctif initial est 1; seconde garde cash après nouveau plan. | `builder_road.nut`: `AIAccounting` voies, raccords, arrêts, dépôt, véhicules/clones. Certains échecs sont enregistrés avant rollback, d'autres après. |
| WATER | Deux docks + dépôt maritime + navire élu par l'économie. | Le garde de trésorerie utilise **maxShipPrice** par prudence face à un navire de repli, et `WATER_CAPITAL_MARGIN=50 000 £` indépendant du coût prédit; pas de remplacement de cette réserve par 1. | `builder_water.nut` : `AIAccounting` activé pour la variante ou sonde C63; pose docks, dépôt, navire et remboursements; choix réel du navire vérifié avant d'accepter l'observation comme comparable. |

`OpexProjectFinanceCapital` devient sous variante le devis de construction
réévalué plus `budgetCapital-capital` inchangé. Si le devis physique RAIL a
déjà remplacé le modèle, il prend priorité sur tout facteur appris. Les
conditions C118 et les deux branches normales/fallback du score AIR appliquent
également la correction de la composante construction, en préservant la marge
et les immobilisations de l'économie concernée.

## Apprentissage et précautions de sélection

Fichier `ai/OpexAI/capital_quote_learning.nut`, à `0` par défaut. Le
facteur `f=1.0` tant qu'il n'existe aucune construction achevée comparable,
ou si la longueur sort de la plage observée pour la famille. Ensuite
`f=somme_débit_réel_des_succès / somme_devis_avant_chantier_des_succès`.
Familles : AIR par 0/1/2 aéroports et nombre prévu d'avions; RAIL et ROAD
par passagers/fret et nombre prévu de véhicules; WATER par construction
maritime. Les devis/dépenses doivent être positifs et leur distance connue.
Si le nombre de véhicules livré diffère du devis, ou si le navire élu change,
le chantier achevé est **exclu** du calibrage. Un facteur appris ne convertit
pas une réserve de trésorerie en dépense.

La distance sert d'intervalle de validité, **pas d'affirmation que les terrains
sont homogènes**. Les premiers succès peuvent être sélectionnés parmi les
terrains les plus simples, les échecs les plus coûteux ne donnant aucun ratio
de ligne terminée. Pour mesurer ce biais, la variante garde à part le nombre
d'échecs et le coût comptabilisé à leur retour, et peut émettre des panneaux
`CQ|` avec `probe_cost=1`. Ces coûts échoués sont *comptabilisés à l'instant*
et ne sont pas des pertes définitives. La prochaine itération devra étudier
cohortes terrain/longueur et états R19 de liquidation si la porte échoue ou
si des échantillons sont trop peu comparables.

Sauvegarde `capitalQuoteLearning` dans les deux variantes de `Save()`, et
`Load()` rétablit l'agrégat sans toucher au comportement si l'option est OFF.
Seuls des compteurs/nombres sérialisables y figurent. Pas de mutation du
calibrage après un seul échec.

## Données antérieures utilisables comme contexte, sans revendication de gain

Les campagnes AIR V126 isolées, *avec d'autres bundles et d'autres réglages*,
restent du diagnostic, à ne pas mélanger à l'A/B P0. Référence :
[`air_devis_marge_orthogonal_20261009.md`](air_devis_marge_orthogonal_20261009.md).
Sur 6 graines × 3 ans, le devis ajouté à marge ancienne a produit
**−164 538 £/an**, valeur **−8,88 %**; isoler la marge à devis constant
donne **−156 413 £/an**, valeur **−11,37 %**. Sur un échantillon naturel
de 70 échecs AIR, 370 199 £ étaient comptabilisés à l'instant, dont
203 320 £ pour neuf échecs avec aéroport A encore conservé. Dans un essai
R19 START *forcé*, 118 505 £ payées initialement et 75 136 £ remboursées
plus tard ont donné **43 369 £ de coût net**; la valeur des actifs conservés
ailleurs n'est pas connue. Le diagnostic de devis AIR frais
[`air_devis_fraicheur_shadow_20261009.md`](air_devis_fraicheur_shadow_20261009.md)
montre 111 devis différents sur 313 gardes cash, mais un seul renversement
de la décision d'abordabilité. Ce n'est pas une mesure d'erreur de devis
par mode en cours de partie.

## Protocole d'évaluation de la nouvelle variante

Comparaison `OpexAI[capital_quote_learning=0]` / `=1`, arbre de code
identique, toutes autres options au défaut. Catégorie **comportement** :
smoke 1×1 sain, diagnostic d'exposition devis/réel, puis porte A V102
40 graines × 3 ans, `gain_short`, Wilcoxon exact bilatéral p<0,05,
borne basse bootstrap IC95 >0, delta moyen `profit_year` ≥4 % du
profit moyen référence, garde de `company_value` −5 %. Porte B seulement
si A passe, 20×10 `non_erosion`, IC95 borne haute ≥0 et garde valeur.
Une seule campagne Docker simultanée. PC Windows `desktop-linux` / image
`openttd-lab` / 10 CPU, 8 GiB, 10 workers maximum.

### Validation et campagnes exécutées

Contrats ciblés nouveaux `test_capital_quote_learning.py` : **8/8 verts**.
V126 `test_v126_air_site_cost_quote.py` : **34/34 verts** ; WATER B7
**2/2**. `test_r23_rail_quote_failure.py` : **1 échec/6**
(`test_cash_failure_retains_retry_contract`, ordre des gardes) sur le code
RAIL déjà modifié simultanément, provenance de l'échec encore à isoler.
Les tests P0 du décodeur (3/3) et de l'agrégateur (2/2) passent également,
soit **49/49** contrôles ciblés verts hors R23.
Smoke 1×1 `p0_capital_quote_smoke_20261009_r1` :
**2/2 duels complets et sains**, bundle
`be1dc07cfe7b2561d4f76982ad6ca26262d82c7a817a75edc4bc388e536fd6dd`;
variante − référence `profit_year` **+32 040 £/an**,
valeur **+6,52 %**, verdict `diagnostic_only`, échantillon insuffisant.
Ce seul résultat ne valide ni un gain ni l'exposition par mode.

### Porte A — verdict économique final

`p0_capital_quote_A40x3_20261009_r1`, bundle figé
`6421111a5edd0076f1e3a244a94001e4f56633e1d66747fdbd7071245fa917bf`.
**40/40 paires, 80/80 parties saines**, graines canoniques V102,
bras identiques sauf `capital_quote_learning`.
Variante−référence, `profit_year` terminal :
**moyenne −106 788,325 £/an**, **médiane −46 838,5 £/an**,
**V/D/E=14/26/0**, **Wilcoxon exact p=0,01527**,
**IC95 bootstrap [−179 143,175 ; −36 512,3] £/an**,
seuil de gain requis **+79 256,63 £/an**.
Ratio des moyennes `company_value` **−2,2345 %**, garde −5 % tenue.
Verdict brut **`fail_primary`**. La porte B 20×10 n'est pas lancée.
**Rejet de la variante**, aucun défaut modifié.

La porte A teste ensemble le retrait du correctif ROAD 121 %
au profit de 1,0 initial, la correction de devis et leur apprentissage.
La part de perte propre à chaque mécanisme demeure non identifiée.

### Sondes et extraction

Le diagnostic `p0_capital_quote_costprobe_20261009_r1`
(1 graine × 3 ans, `probe_cost=1` sur les deux bras) a terminé
**2/2 duels sains**, variante−référence
`profit_year` **−132 583 £/an**, valeur **−4,07 %** ;
`diagnostic_only`, et la sonde peut influer sur la trajectoire.
`sweeps/bench_1v1_5y_20seeds.py::capital_quote_sign_metrics`
extrait les panneaux `CQ|mode|devis|actual|ok|n` dans les checkpoints;
`sweeps/analyse_capital_quote_p0.py` conserve seulement le dernier
checkpoint par partie avant d'agréger les coûts par mode. Les débits
d'échec à leur retour ne donnent ni leur perte finale après récupération
ni le capital encore immobilisé. Les refus de financement qui auraient
permis une construction restent contrefactuels et non observables
directement par cette sonde.

Diagnostic moteur complémentaire **avec décodage effectif des signes CQ**
`p0_capital_quote_costprobe_decode_20261009_r2`, même graine 42,
3 ans, 2/2 duels complets/sains, `probe_cost=1` dans les deux bras.
Les profits Opex sont identiques au premier diagnostic instrumenté
à cette graine (−132 583 £/an variante−référence). Rapport extracteur :
`results/p0_capital_quote_costprobe_decode_20261009_r2_analysis.json`.
Les seules mesures de devis CQ ci-dessous proviennent du bras **ON**.

| Mode | Succès observés | Devis avant chantier | Débit au retour des succès | Écart réel−devis | Échecs et débit au retour |
|---|---:|---:|---:|---:|---:|
| AIR | 49 | 2 641 728 £ | 2 864 118 £ | +8,42 % | 5 / 30 825 £ |
| RAIL | 3 | 124 191 £ | 131 737 £ | +6,08 % | 0 |
| ROAD | 1 | 11 095 £ | 13 983 £ | +26,03 % | 0 |
| WATER | 0 observé | inconnu | inconnu | inconnu | 0 observé |

Le plus grand compteur de succès compatibles observable en fin de partie
pour **une famille** vaut 22 en AIR, 3 en RAIL, 1 en ROAD. Il ne s'agit pas
du total des succès compatibles toutes familles confondues. Le volume WATER
et la segmentation du terrain ne permettent pas d'en tirer une calibration
généralisable. Les échecs AIR 30 825 £ sont des **débits au retour**,
avec valeur conservée/recouvrement final inconnus. Les projets refusés par
le financement, le coût d'opportunité du cash immobilisé et la cause
de la perte A exigeraient un diagnostic causal séparé.

Tests de collecte après instrumentation : 3/3 pour
`test_capital_quote_sign_metrics.py` et 2/2 pour
`test_analyse_capital_quote_p0.py`. Extraction non utilisée
dans la porte A (sonde OFF).

### Save/Load réel

`sweeps/run_capital_quote_roundtrip.py` réemploie le banc existant
`save_load_roundtrip.py` avec des répertoires temporaires propres au P0,
afin de conserver les archives Save/Load d'autres chantiers.
`OpexAI[capital_quote_learning=1]`, seed42, phase A deux ans puis reprise
de la sauvegarde du **1971-01-01** pendant un an :
**25 sauvegardes phase A, 13 phase B**, compagnie active après reprise.
Le signal **`LOAD_RECONCILE`** confirme le chargement, et aucun
marqueur d'échec OpenTTD/NoAI n'a été relevé. Rapport
`results/p0_capital_quote_roundtrip_20261009_r1.json`.
Une compagnie humaine fantôme sans activité apparaît au rechargement,
un biais déjà documenté dans ce harnais. Ce test établit une reprise
fonctionnelle; la **valeur numérique exacte des agrégats appris
n'est pas relue indépendamment** du savegame.

La variante reste **rejetée** à la porte A, indépendamment du succès
technique de ce round-trip.

## Piste suivante — devis par composants et apprentissage du résiduel

La porte A négative ne démontre ni que le 121 % ROAD est nécessaire, ni que
les coûts physiques suffisent, puisque plusieurs décisions ont changé à la
fois. Pour éviter d'inventer un nouveau 115 %, 130 % ou facteur de prudence,
la solution suivante doit **reconstituer le coût de chaque commande** puis
isoler ce qui reste inexpliqué :

1. **ROAD** : après choix des arrêts et du trajet, chiffrer les segments de
   route, raccords, arrêts, dépôt et véhicules du plan réellement construit.
   Utiliser des tests de coût de commande quand ils sont fiables ; une
   simulation `AITestMode` de plusieurs commandes dépendantes doit être
   vérifiée face au chantier réel. Contrôler la caisse après replanification.
2. **RAIL** : réutiliser le devis physique déjà produit pour les gares,
   terrassements, ponts/tunnels et voies. Ajouter les commandes non devisées
   (deuxième voie, raccord au dépôt, équipements) plutôt que multiplier la
   distance Manhattan par 170 %. Conserver le devis initial et le devis
   révisé pour ne pas comparer des géométries différentes.
3. **AIR** : construire le devis avec les aéroports exacts (0/1/2 neufs),
   le nivellement réalisable, les arrêts joints et les avions *effectivement*
   prévus. Rafraîchir les éléments susceptibles de changer avant le garde
   cash, puis comparer au débit réel en excluant coûts de tests simulés et
   bâtiments conservés après échec jusqu'à leur réconciliation.
4. **WATER** : séparer coût du bateau prévu, docks et dépôt de la liquidité
   exigée pour un éventuel bateau de repli. Une substitution de moteur ne
   sert pas d'observation compatible avec le devis initial.

Sur chaque chantier compatible, enregistrer **devis physique par poste,
débit effectif par poste et résiduel**
 = `coût réalisé − somme des composants devisés`.
L'estimateur démarre sur les tarifs physiques, donc correction multiplicative
**1,0** et résiduel **0 £** tant qu'aucune réalisation comparable n'existe.
Après observation, l'estimateur peut apprendre **le poste manquant** en
fonction de la longueur construite, du relief et du nombre d'équipements ;
il ne doit pas agréger des projets dont la géométrie, la flotte ou la
stratégie de chantier ont changé. Le coût final des échecs demeure une
variable censurée tant que les ventes/remboursements et actifs conservés ne
sont pas rapprochés.

Le **tampon de liquidité** reste un objet distinct du devis et s'évalue
sur les pics de trésorerie observés avant/pendant/après chantier, incluant
les échecs. Ne pas déduire de la réussite d'un devis juste que le tampon
forfaitaire peut disparaître ; choisir une nouvelle politique de risque
exige une mesure séparée des financements refusés à tort et des chantiers
échoués par manque d'argent.

**Qualification isolée** : (A) retrait du seul biais de financement ROAD
121 %, (B) enrichissement des devis physiques seuls avec corrections
initiales 1,0, (C) apprentissage des résiduels sur les seuls postes
exposés. Pour chaque bras, figer une référence identique, mesurer l'erreur
de devis et l'augmentation des projets finançables *avant* un duel apparié
V102. Une perte à la porte A arrête l'adoption de ce sous-mécanisme ; ne
pas requalifier la variante monolithique rejetée après coup.
