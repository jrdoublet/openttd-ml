# OpexAI : croissance et rentabilité

Session du 2026-08-28, après la mise en place de l'étage 3 (construction) et du multimodal
(`docs/opexai_multimodal.md`). Point de départ : sur une campagne graine 42, `ai/OpexAI/`
s'arrêtait à 3 lignes ferroviaires, ne remboursait jamais son emprunt de 300 000 et terminait avec
`company_value = 1`. Six correctifs successifs, chacun mesuré en jeu avant et après, ont porté la
même campagne à 17 lignes et une valeur de compagnie de 2 716 098 (§6). Ce document décrit ce qui a
été changé, comment chaque changement a été vérifié, et — à la demande explicite du suivi de
projet — les pistes qui ont été envisagées puis écartées, avec la mesure qui a tranché.

## 1. Le modèle économique passagers surestimait le profit d'un facteur ~8

`economy.nut::OpexLineEconomics` prédit un profit annuel avant construction. Mesuré sur 9 lignes
pax réelles (2 campagnes de 10 ans, graine 42) : convois et coût de fonctionnement prédits
correspondaient exactement au réel — tout l'écart était dans le revenu. Décomposé en isolant
chaque facteur séparément :

- `STATION_RATING_PCT` supposait 75, mesuré ~53 (`AIStation.GetCargoRating` en régime établi) :
  facteur **~1,4x** seulement.
- **Dominant** : `AITown.GetLastMonthProduction` compte la production de la ville ENTIÈRE, alors
  qu'une gare n'en capte qu'un rayon local. Résidu mesuré 8-37 % (moyenne 22 %) : facteur **~4,5x**.

Corrigé par `STATION_RATING_PCT = 50` et un nouveau `TOWN_CATCHMENT_SHARE_PCT = 22` dans
`candidates.nut`, appliqué uniquement aux paires de villes (`OpexPaxCandidates`) — pas au fret, une
industrie produisant depuis une seule tuile sans cette dilution géométrique. Vérifié in-sample sur
les 9 lignes : ratio prédit/réel resserré de ~8x à ~1,18x. Commit `b09f23e`.

## 2. Le fret restait bloqué à plein chargement au puits

Le run de vérification du correctif pax n'a construit que du fret (le pax est désormais
correctement déclassé). Les 3 lignes fret ont vu leur note de gare tomber à -1 en 1 à 3 ans.

Diagnostic sur l'état réel des convois (`AIVehicle.GetState`, `AIOrder.ResolveOrderPosition`,
`AIVehicle.GetCargoLoad`) : `OpexFreightCandidates` n'apparie qu'un producteur à un accepteur du
MÊME cargo — la ligne fret est structurellement à sens unique. Mais `OpexBuildTrains` posait
`AIOrder.OF_FULL_LOAD_ANY` aux deux arrêts pour toute ligne, hérité du pax bidirectionnel. Un
convoi arrivant au puits attendait un plein chargement de retour qui n'existe jamais, restait
bloqué en `VS_AT_STATION`, et bouchait la gare à une seule voie pour les convois suivants.

Corrigé : le puits fret reçoit `AIOrder.OF_NONE`, la source garde `OF_FULL_LOAD_ANY`, le pax n'est
pas touché. Vérifié graine 42/10 ans : 3→8 lignes fret construites, note stable 58-84 sur 9 ans
(avant : -1 dès l'an 2), revenu ~18-28k/an soutenu (avant : 0). Commit `abd641b`.

**Correction du 2026-08-28 (après-coup) : le correctif ci-dessus suffisait aussi à fermer l'écart
prédit/réel.** §9 affirmait un écart fret résiduel de « ~4-6x » non identifié. Cette affirmation
n'était appuyée par aucune mesure citée dans ce document — en la creusant, la mesure existait déjà
mais n'avait jamais été exploitée : `sweeps/opex_freight_postfix.py` avait tourné (graine 42,
10 ans, code complet post-tous-correctifs) et écrit
`docs/opex_predict_vs_actual_postfix_freight_v2.json`, commis dans `abd641b` en même temps que le
correctif lui-même — la donnée était disponible dès ce commit, simplement jamais recroisée avec
l'affirmation « ~4-6x » écrite ensuite dans `9c5e39f`.

Sur les 8 lignes fret de cette mesure, 5 ont ≥3 ans de données stables (ratingA sain, industrie
source vivante) ; les 3 autres n'ont qu'1-2 ans (ligne neuve ou industrie sur le point de fermer —
bruit de bord de fenêtre, pas un biais de modèle). En moyennant le revenu réel par ligne sur toutes
ses années observées :

| ligne | années | revenu prédit | revenu réel moyen | ratio prédit/réel |
|---|---|---|---|---|
| 1 | 9 | 20 400 | 23 037 | 0,89 |
| 2 | 8 | 21 600 | 25 135 | 0,86 |
| 3 | 7 | 18 144 | 22 877 | 0,79 |
| 4 | 5 | 66 552 | 51 229 | 1,30 |
| 5 | 3 | 45 900 | 43 882 | 1,05 |

**Ratio sur les lignes stables : moyenne 0,98, médiane 0,89, géométrique 0,96 — pas 4-6x, ~1x.** Les
deux lignes à 1 an de données (ratios 2,39 et 1,82) sont un effet de fenêtre courte, pas un facteur
manquant : une ligne neuve ou en fin de vie n'a pas eu le temps de stabiliser sa note ni sa
production source. **`STATION_RATING_PCT = 50` (calibré sur le pax) tient donc aussi pour le fret**,
sans facteur correctif propre — la piste « facteur fret non identifié » de §9 est écartée, pas
juste non trouvée. Donnée source : `docs/opex_predict_vs_actual_postfix_freight_v2.json`, déjà
présente dans le dépôt depuis `abd641b`.

## 3. `MIN_SEPARATION` bloquait la croissance sur de faux positifs

Une fois pax et fret rentables, une campagne complète (`sweeps/opex_full_campaign.py`) a montré
l'IA passer de 3 à 8 (10 ans) puis 12 (20 ans) lignes — le capital n'était plus le mur — mais avec
des stalles de plusieurs années malgré une trésorerie très supérieure au capital de n'importe quel
candidat. Direct measurement (signs `GT`/`GC`/`GN`, pas de déduction par élimination) a montré deux
verrous distincts et séquentiels :

- **1970-1977 : trésorerie.** Un rejet cash par an, `break` confirmé sur manque de capital réel.
- **1980-1989 : `_tooClose`.** La trésorerie n'est plus jamais la raison (`nCashBlocked=0` chaque
  année), mais `_tooClose` rejette les 20/20 meilleurs candidats sur 6 des 10 années. **84 % de ces
  rejets sont à distance <5 de la MÊME origine déjà servie**, pas une ville voisine différente.

Cause : `_tooClose` comparait l'origine du candidat à la **gare bâtie** d'une ligne existante — un
proxy bruité par `STATION_SEARCH_RADIUS=30` (la gare peut finir loin de la ville qu'elle sert).
Corrigé en deux tests distincts : `ORIGIN_SEPARATION=3` sur la tuile catalogue stable (identité
réelle, précis) et `MIN_SEPARATION` abaissé 15→10 comme filet physique entre deux gares bâties
différentes. Vérifié graine 42/20 ans, reproduit deux fois à l'identique : 11→12 lignes, valeur
1 139 315→2 245 285, aucun échec de construction introduit. Commit `5433518`.

## 4. L'emprunt n'était jamais remboursé

Un seul appel de prêt existait dans tout le code : `AICompany.SetLoanAmount(GetMaxLoanAmount())`
au démarrage. Aucune logique de remboursement. Ajouté `OpexAI::_tryRepayLoan`, appelé une fois par
an après les tentatives de construction (elles ont priorité sur le cash de l'année) : au-dessus de
`LOAN_REPAY_FLOOR = 1 000 000` de trésorerie, rembourse le maximum qui laisse ce plancher, arrondi
vers le HAUT au palier `AICompany.GetLoanInterval()` (arrondir vers le bas rembourserait plus que
permis). Vérifié graine 42/20 ans : emprunt 300 000→0 (atteint en 1987, jamais repris), lignes
12→13 (le remboursement, placé après les constructions, ne les a jamais privées de cash).
Commit `44e0b14`.

## 5. Les lignes fret mortes n'étaient ni détectées ni remplacées

Certaines lignes fret meurent quand leur industrie source ferme — un événement de jeu normal. Sans
détection, leurs convois continuent de rouler à vide, payant leur coût de fonctionnement pour un
revenu nul, indéfiniment.

Détection : `srcAlive=0` (`AIIndustry.IsValidIndustry`) seul ne suffit PAS — une gare peut rester
alimentée par une industrie voisine du même cargo après la fermeture de celle d'origine et rester
pleinement rentable (voir §7, piste écartée). Le diagnostic exige donc la preuve réelle mesurée
chaque année (note de gare ≤0 ET revenu implicite `profit + coût de fonctionnement` ≤0) en plus de
la source défaillante, confirmée **2 années consécutives** (`DEAD_STREAK_THRESHOLD=2`) pour écarter
un accroc transitoire.

Remédiation étalée sur plusieurs années car `AIVehicle.SellVehicle` exige un convoi arrêté en
dépôt : l'année du seuil, chaque convoi est envoyé au dépôt (`AIVehicle.SendVehicleToDepot`) et ses
IDs figés sur la ligne ; les années suivantes, les convois arrivés sont vendus un par un. La ligne
quitte le suivi (`_lines`) une fois tous vendus — ce qui la libère du filet `_tooClose` sans
démolir gares ni voies (inutile une fois hors de `_lines`, et risque de note d'autorité locale pour
un gain nul).

Bug de diagnostic trouvé et corrigé au passage : `Array.remove()` décale tous les indices suivants,
donc l'indice de boucle n'était plus un identifiant stable dès qu'une ligne pouvait être retirée —
deux lignes différentes recevaient parfois le même numéro d'une année sur l'autre. Ajouté
`_nextLineId` (monotone, jamais réutilisé) ; tous les signs de diagnostic utilisent désormais
`line.lineId`. Vérifié sans effet sur la partie elle-même (résultat identique avant/après ce
correctif de diagnostic seul). Commit `e884358`.

## 6. `TOP_K` saturé par des origines déjà servies

Item 3 du backlog (`docs/taches.md` §2), traité le 2026-08-28. Baseline préservée dans
`docs/opex_full_campaign_20y_before_topk_fix.json` (avant tout correctif de cette section) ;
`docs/opex_full_campaign_20y.json` reflète l'état final (exclusion d'origine + `MIN_RATIO`).
Sur la campagne graine 42/20 ans,
les stalles de croissance (12 lignes bloquées 3 ans, 1984-1986) étaient mesurées comme 20/20
candidats du `TOP_K` rejetés par `_tooClose` pour la MÊME raison — une origine déjà desservie,
jamais une proximité physique. Le classement n'avait alors aucune chance de contenir un candidat
constructible : `TOP_K` entier gaspillé sur des origines mortes, sans qu'aucune place ne soit
jamais réévaluée.

**Premier correctif, insuffisant seul.** Exclure les origines déjà servies à la génération plutôt
qu'au filtrage (`OpexOriginServed` dans `candidates.nut`, appliqué dans `OpexPaxCandidates` et
`OpexFreightCandidates` avant même de calculer l'économie d'un candidat) fait bien son travail :
14 lignes dès 1985 contre 12 avant, la fenêtre de stalle raccourcie. Mais vérifié seul (même
graine/durée) : `company_value` **2 067 089** contre **2 413 587** avant (-14 %), emprunt **non
remboursé**. En creusant : une fois les bonnes origines épuisées, l'IA descend vers des candidats
à profit prédit quasi nul (685, 3 149) au lieu de laisser le `TOP_K` vide — dont une tentative à
70 tuiles **abandonnée après 60 000 itérations gaspillées** pour un profit prédit de seulement
3 149. L'ancien engorgement du `TOP_K` protégeait donc *accidentellement* contre ces candidats
marginaux, sans que ce soit une protection voulue.

**Second correctif : plancher de ratio.** `MIN_RATIO = 500` dans `OpexMakeCandidate` (profit
annuel par millier d'itérations), sous lequel un candidat est rejeté même s'il est techniquement
profitable. Choisi pour couper les trois candidats manifestement pathologiques de la mesure
ci-dessus (ratios 15, 218, 275) sans toucher au plancher empirique de la campagne AVANT tout
correctif (1278, jamais franchi à la baisse quand le classement avait assez de bons candidats).
Vérifié, même graine/durée : **17 lignes** (contre 15 avant tout correctif), `company_value`
**2 716 098** (+12,5 % vs avant), emprunt remboursé, `performance_history` 503 contre 424. Les 2
échecs de construction restants sont des `STNFAIL` bon marché (3 600 et 4 200 itérations), pas une
nouvelle dérive coûteuse.

**Politique d'abandon, trou du dernier rang corrigé (2026-08-28).** La politique en cours de
recherche avait bien sa forme fermée dans `OpexIterationBudget`, mais le dernier candidat recevait
`alternativeRatio = 0`, donc systématiquement `HARD_ITERATION_CAP = 60 000`. Une instrumentation
compacte du panneau `OR` (sans panneau supplémentaire) a tranché sur la campagne figée
graine 42/20 ans : ce chemin `Z` a concerné **5 tentatives**, pour **15 500 itérations réellement
consommées**, mais **0 ABND / 0 itération abandonnée**. Le plafond atteint via un suivant réel
(`C`) a concerné 3 tentatives, 57 700 itérations, et lui aussi 0 ABND. La campagne de référence
ne permet donc d'attribuer le vieux cas ABND à 60 000 ni à `Z` ni à `C` : il a été mesuré avant
cette instrumentation. Le dernier candidat compare désormais son rendement à `MIN_RATIO`, déjà le
plus petit rapport accepté par la génération, soit le coût d'opportunité d'attendre le classement
annuel suivant ; aucun seuil d'arrêt nouveau n'est introduit. Après correction, `Z` tombe à 0,
les cinq derniers rangs gardent les mêmes résultats et les agrégats restent 17 lignes,
`company_value` 2 716 098, emprunt 0, `performance_history` 503.

**Hypothèse du plafond de panneaux réfutée ; vrai défaut du cycle annuel (2026-08-28).** Il
n'existe pas de limite par tuile : `CmdPlaceSign` n'utilise la tuile que pour les coordonnées. Ses
deux échecs sont le nom de 32 caractères ou plus et le pool global épuisé ; ce dernier vaut 64 000,
très au-dessus des 1 400 à 2 149 signs de ces campagnes. Surtout, le trou est au milieu : 1984 est
absent mais 1985-1989 sont présents dans les trois mesures conservées. Un plafond de pool serait
monotone. L'ancienne explication « seule l'observabilité est perdue » est donc fausse.

La sonde `YT` remplace le panneau annuel `GT` (pas de commande de panneau supplémentaire) et donne
la preuve directe. En baseline, le bloc étiqueté 1983 commence au tick **88 142**, finit à
**104 707**, dure **16 565 ticks** et ne dépasse donc pas 27 010 (il lui manque 10 445). Mais les
ticks de `AIController` ne suivent pas l'arithmétique 365 × 74 supposée ici : ce bloc franchit
bien le calendrier jusqu'en 1985. `_tryBuild` en consomme **16 356 ticks (98,7 %)**, contre 209
pour le reste. Le bloc suivant porte `YT|85|...|1` : une année civile, **1984**, a été franchie
sans être exécutée. Dans l'ancien code, aucun rapport de ligne, rebut, remboursement, catalogue
ni classement annuels ne s'exécutait pour elle ; seul le `_tryBuild` du cycle 1983 pouvait encore
continuer pendant ce temps, sans nouveau cycle de construction propre à 1984.

Le correctif rattrape, à l'entrée du cycle 1985, les opérations encore valides sur l'état réel
présent : rapport des lignes, traitement des lignes mortes et remboursement. Il ne rejoue pas une
construction ni un classement historiques, dont les candidats, l'argent et le monde ont déjà
changé ; le catalogue est rafraîchi une fois pour l'année courante. Le marqueur `YT|85|...|1C`
prouve ce rattrapage : 1984 reste une année calendaire franchie, mais il n'y a plus d'année
**non traitée**. Même campagne : 16 lignes, `company_value` **2 787 970**, emprunt 0,
`performance_history` 521.

## 7. Pistes écartées

Hypothèses testées puis rejetées par la mesure, ou décisions de conception prises et non retenues,
consignées ici pour ne pas les reproposer sans nouvelle donnée.

- **Borner A* à la frontière calendaire pour empêcher tout franchissement.** Testé graine 42/20
  ans : plus aucune année franchie, mais 14 lignes, `company_value` **2 413 212** (-11,2 %),
  emprunt 0 et `performance_history` 433. Cela coupe des recherches rentables plutôt que de
  traiter le travail annuel retardé ; écarté au profit du rattrapage sans reconstruction passée.

- **La fermeture d'industrie source comme cause SEULE de l'effondrement fret initial (§2).** Avant
  diagnostic sur l'état réel des convois, c'était l'hypothèse la plus probable (le catalogue perd
  des industries au fil du temps). Écartée : les deux industries des 3 lignes concernées restaient
  valides et productives tout du long (`IA|...|1|1|prod>0`) — la vraie cause était le train coincé
  par `OF_FULL_LOAD_ANY`.
- **`srcAlive=0` comme critère unique de ligne fret morte (§5).** Testé implicitement en
  envisageant de scrapper dès la fermeture de l'industrie source ; écarté avant implémentation
  grâce à la donnée de la campagne 20 ans : une ligne (dist. 83) avait `srcAlive=0` en continu de
  1978 à 1989 tout en restant rentable (note 55-75, profit réel 18-52k/an) — une industrie voisine
  du même cargo, dans le rayon de couverture de la gare, avait pris le relais. Un critère basé sur
  `srcAlive` seul aurait vendu une ligne saine.
- **La trésorerie comme cause des stalles 1980-1989 (§3).** L'hypothèse de départ ("`MIN_SEPARATION`
  peut être responsable de l'arrêt à 3 lignes autant que la trésorerie") laissait la question
  ouverte entre les deux causes. Tranchée par mesure directe : `nCashBlocked=0` chaque année de
  cette période, donc la trésorerie n'y jouait aucun rôle — tout le blocage venait de `_tooClose`.
- **Abaisser `MIN_SEPARATION` seul, sans distinguer identité d'origine et proximité physique
  (§3).** Le diagnostic (84 % des rejets à distance <5, donc de la même origine, contre 16 % à
  distance 5-14, donc une ville réellement différente) montrait qu'un seuil unique plus bas aurait
  réduit les faux positifs à distance 5-14 mais serait resté vulnérable au bruit de
  `STATION_SEARCH_RADIUS=30` sur l'identité d'origine. Remplacé par deux tests séparés plutôt qu'un
  seul seuil recalibré.
- **`TOWN_CATCHMENT_SHARE_PCT` appliqué au fret (§1).** Envisagé pour cohérence avec le pax, écarté
  par construction : une industrie produit depuis une seule tuile, sans la dilution géométrique
  d'une ville entière captée par une seule gare. Non mesuré côté fret — voir limites ci-dessous.
- **Démolir gares et voies des lignes fret mortes (§5).** Envisagé comme remédiation plus complète
  que la simple vente des convois. Écarté par raisonnement plutôt que par mesure : une fois la
  ligne retirée de `_lines`, elle ne bloque plus rien (`_tooClose` n'itère que sur `_lines`) ; la
  démolition ajoute un risque (note d'autorité locale, infrastructure partagée) pour un gain nul.

## 8. Validation reproductible

Configuration commune à toutes les mesures de ce document : OpenTTD 15.3, OpenGFX 7.1, carte
256×256, graine 42, année 1970, inflation désactivée. Harnais : `sweeps/opex_full_campaign.py`
(mesures agrégées, financières et de construction) et les harnais spécifiques à chaque correctif
(`sweeps/opex_predict_vs_actual.py`, `sweeps/opex_freight_diag.py`, `sweeps/opex_freight_postfix.py`).

| Étape | Lignes rail | `company_value` | Emprunt final |
|---|---|---|---|
| Avant (documenté, 10 ans) | 3 (bloqué) | 1 | 300 000 (jamais remboursé) |
| Après §1-§2, 20 ans | 12 | 2 245 285 | 300 000 |
| Après §3 (`MIN_SEPARATION`), 20 ans | 12 | 2 245 285 | 300 000 |
| Après §4 (emprunt), 20 ans | 13 | 2 233 591 | **0** |
| Après §5 (lignes mortes), 20 ans | 15 | 2 413 587 | 0 |
| Après §6, exclusion d'origine SEULE, 20 ans | 15 | 2 067 089 (régression) | 300 000 |
| Après §6, + `MIN_RATIO`, 20 ans | **17** | **2 716 098** | 0 |

## 10. Ranking composite ROI / Rotation rapide et compatibilité Aéroports (2026-08-31)

### 10.1 Diagnostic financier
Le classement historique reposait uniquement sur `(profitAnnual * 1000) / iterations`. Bien qu'optimal pour économiser les opcodes de calcul A*, ce ratio ignorait le capital requis et le délai de récupération. En début de jeu (emprunt plafonné à 300 000 £), une ligne longue consommait 200 000 £ à 250 000 £ de capital et mettait 4 à 6 ans à amortir son investissement, bloquant l'expansion par manque de liquidités.

### 10.2 Principes inspirés d'AAAHogEx (Clean-room design)
Inspiré de l'arbitrage multi-critères d'AAAHogEx (`docs/aaahogex_evaluation.md` §5quinquies) :
- **Intégration du ROI** : $\text{ROI} = \frac{\text{profitAnnual} \times 1000}{\text{capital}}$
- **Facteur de rotation rapide** : bonus d'accélération pour les lignes courtes/rapides ($\text{oneWayDays} \le 12$ j : +30 %, $\le 25$ j : +15 %, $> 45$ j : -25 %).
- **Score composite** : $\text{Score} = \text{Ratio}_{\text{Opcode}} + (\text{ROI}_{\text{ajusté}} \times 0{,}15)$. Le rendement par opcode (`profitAnnual / iterations >= MIN_RATIO`) reste le plancher éliminatoire et le terme dominant.

### 10.3 Familles d'Aéroports et Avions
- **Grands Aéroports** (`AT_INTERNATIONAL`, `AT_METROPOLITAN`, `AT_LARGE`) : compatibles avec les gros avions (`PT_BIG_PLANE`) et petits avions.
- **Petits Aéroports** (`AT_COMMUTER`, `AT_SMALL`) : réservés **STRICTEMENT aux petits avions** (`PT_SMALL_PLANE`), excluant tout gros appareil.
- **Économie de l'Avion** : calcul du revenu annuel (vitesse réelle divisée par 4 selon OpenTTD `plane_speed`), de la maintenance et du ROI pour arbitrage immédiat.

### 10.4 Résultats (5 graines x 5 ans)
Trésorerie moyenne à l'an 5 : **~454 400 £** (contre < 100 000 £ précédemment), Valeur moyenne de compagnie : **~434 400 £**, et 7,2 lignes/partie construites avec 100 % de rentabilité.
