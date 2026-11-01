# ROAD100 — préenregistrement GRAPH-BRIDGE (28 octobre 2026)

**Statut : hypothèse technique préenregistrée, non qualifiée.** Parités H1..H5 prouvées : **0/5**. Ne pas assimiler la réussite d'un tracé ou un gain ON−OFF à une parité.

## Cause et mécanisme unique

V21 construit quelques lignes et laisse de la caisse, mais son générateur site-first ne couvre que les centres à distance 12..42 ; 181/205 préplans ont échoué physiquement, avec ~2,7–3,1 millions d'opcodes/an sur la graine 42. V29 observe 43..80 sans publier de projet ; V35 a constaté les rejets `BAND_1_EDGE_OCCUPIED` et `BAND_10_GAP_TURN`, et aucune ligne LONG. Ces mesures ne justifient pas un assouplissement général de C75 ni un classement fictif par `waiting` AAA après construction.

**Un seul réglage** `road100_pax_graph_bridge=1`, défaut 0 sur les quatre difficultés et limité au duel ROUTE seule, active une chaîne complète : préqualification de couples de villes d43..170 sur les vrais arrêts traversants, choix des sites par captation physique, traceur GRAPH-BRIDGE fondé sur tronçons de voirie existante et petits raccordements locaux bornés, devis des arêtes manquantes et des deux quais/dépôt/flotte, admission normale au portefeuille et revalidation stricte des sites, ordres, hash du trajet, coût et StationIDs lors du chantier. Pas de construction de satellite, pas de station fantôme, pas de double comptage de trafic, pas de copie d'AAAHogEx.

La conversion ex ante est `OpexRoad100PaxSiteMonthly` (producteurs vers PASS/mois de ville) et non la valeur brute `AITile.GetCargoProduction`. Ne pas utiliser `route.profit` AAA, ses attentes après construction ou un revenu de retour non desservi comme oracle. Les entrées à plusieurs lignes sont générées par régénérations annuelles, au maximum deux couples LONG physiques examinés par année ; le générateur existant PO01C doit partager exactement le même chemin que le synchrone.

## Bornes, sécurité et critères de décision

- Corridor physique 43..190 arêtes ; recherche locale sans A* LONG monolithique ; ≤42 000 opcodes par tentative de trace, ≤180 000 par paire (scan sites, trace, qualification et économie), ≤400 000 pour les couples LONG par an, deux couples au maximum. À dépassement : refus explicite, jamais admission présumée.
- Revalidation `OpexRoad100LongVerifyTrace` des arêtes (connexion réelle dans les deux sens pour les arêtes préexistantes ; AITest de construction pour les autres), contrôle de pente/virages, quais et dépôt, puis `OpexBuildRoadRoute` avec rollback des seules constructions propres. Les contrôles de station, slots, refit et commandes existants restent obligatoires.
- Quote : coût routier manquant ×3, deux arrêts, dépôt et raccord, flotte effective, marge 25 %, réserve de caisse 50 000 £ ; profit ex ante strictement positif et ROI conservateur ; les filtres financiers C75/C78 et le ranking existant continuent à s'appliquer, sans leur bypass.
- Hypothèse vérifiable : au moins un corridor GRAPH-BRIDGE complet et un service PASS avec StationIDs distincts, véhicules circulants et PASS réellement livrés sur la graine 42, sans dégradation de la compagnie OFF. Si aucun corridor ou aucune livraison : verdict **NO-EXPOSURE/NO-GO**, pas de 5×5 ni Gate A.
- Smoke strict apparié 1970 256² seed 42, même bundle figé et seule différence `road100_pax_graph_bridge: 0→1` ; options Opex `mode_air=0, mode_rail=0, mode_road=1, mode_water=0` et AAA `disable_veh_train=1, disable_veh_tram=1, disable_veh_ship=1, disable_veh_aircraft=1` sur les deux bras. Enregistrer `ROAD100_GRAPH`, `ROAD100_LONG_PLAN`, `ROAD100_LONG_BUILD`, `ROAD_BUILD`, StationIDs, véhicules, livraisons PASS, opcodes, caisse payée et `profit_year` société.
- Si exposition rentable et signal économique ON−OFF positif au smoke, diagnostic apparié **5 graines 42/100/7/999/2026 × 5 ans**. Exiger rentabilité et non-érosion H1..H5 avant de considérer la Gate A.
- Gate A uniquement après ces prérequis : **40 graines × 5 ans** appariées, Δ moyen de `profit_year` Opex H5 ≥+4 % de la référence, Wilcoxon exact bilatéral p<0,05, garde de valeur ≥−5 % et absence d'érosion sur H1–H4. Le critère supérieur demeure Opex `profit_year` réel ≥ AAA `profit_year` réel à chacun H1..H5. Aucun changement de défaut sans validations complémentaires.

## Portes techniques préalables

Tests ciblés ; projection OFF byte-exact ; fixture historique `sweeps/fixtures/v262_valuate_inventory.json` inchangée ; suite `python -X utf8 -m unittest discover -s sweeps -p "test_*.py"` ; `git diff --check` ; smoke OpenTTD de compilation Squirrel et de transport physique. Conserver bundles et résultats ; ni commit, ni push, ni merge, ni reset, ni clean. Un échec est archivé NO-GO puis le travail structurel se poursuit.

## Premier verdict moteur, avant correction du graphe

Campagne `road100_v36_graph_bridge_roadonly_seed42_1x1_20261028` ; bundle
`2ad6cc3310e0bfe3adc07e1a87f0fc2e30aeec78283f50ec6226ff9642b13be4` ;
deux duels `complete/complete`, une seule option effective différente.
Six traces GRAPH tentées, zéro candidate complète, zéro projet LONG admis ;
`ROAD_BUILD` huit contre huit. Rejets observés : `GAP_LOCAL_NODE_CAP`,
`GAP_OPCAP`, `COUPLE_OPCAP`. H1 Opex OFF 20 797 £/an, ON 19 106 £/an,
AAAHogEx référence 94 472 £/an, AAA dans la partie ON 93 008 £/an.
Le delta ON−OFF vaut **−1 691 £/an**.
**NO-EXPOSURE / NO-GO** pour le traceur initial ; **0/5 parités**.

### Correction de l'hypothèse technique, avant nouveau smoke

L'exploration de seulement 7 nœuds a consommé 17 638 opcodes sur un
couple ; un autre a épuisé son budget à 19 nœuds et 29 921 opcodes.
Avant toute nouvelle mesure, conserver *strictement* le même réglage et
les caps 42k/180k/400k, mais réduire les appels natifs redondants dans
`OpexRoad100GBGap`, préserver la direction et l'état réel de l'arête dans
les revisites, traiter un recouvrement de manchons physiquement connectés
comme possible jonction au lieu d'un rejet automatique, et rendre le log
final cohérent avec le plafond d'opcodes. Aucun AITest ni construction
dans le traceur. Les seuils de preuve restent inchangés : une trace
*spéculative* ne vaut ni raccordement moteur, ni flotte, ni bénéfice.

## Deuxième verdict et hypothèse géométrique suivante

La correction par cache/état directionnel a passé **3 253 tests** (5
ignorés, 2 échecs attendus), projection OFF et contrats V262. Le nouveau
bundle `43347b47fb0aa2ea1b3b9cc031940b41269fec5641c2cf6e9add3ae34aed9d3b`
de `road100_v36_graph_bridge_gapcache_roadonly_seed42_1x1_20261028`
a deux parties `complete` et une seule option effective différente. Aucun
des six essais GRAPH n'a retourné de trace candidate, aucun LONG n'a été
admis, sept constructions ordinaires sur le bras ON. H1 Opex OFF
**20 797 £/an**, ON **19 072 £/an** (delta **−1 725 £/an**), AAA ON
**98 965 £/an**. **NO-EXPOSURE/NO-GO**, toujours **0/5**.

**Nouvelle hypothèse technique fixée avant un nouveau smoke :** le coût
des nœuds du graphe (par exemple 27 532 opcodes pour 7 expansions) est
incompatible avec plusieurs gaps successifs dans 42k opcodes. Dans la
*même* famille opt-in V36 et sans changer classement ou économie, tenter
une proposition directe de liaison géométrique **sleeve-to-sleeve**, à
couloirs orthogonaux déterministes (pas de balayage A*), bornée à une
petite fraction du budget de tentative. Il ne s'agit que de candidates :
chaque arête, arrêt, virage, dépôt, coût et connexion doit impérativement
passer le même préflight `OpexRoad100LongVerifyTrace` puis la construction
transactionnelle ; une hypothèse géométrique n'autorise aucun profit.
Ne pas fabriquer de cycle, de connexion routière implicite ni de gain
de `waiting` adverse. Une trace refusée par le moteur reste un échec et
donne un point de blocage mesurable. En l'absence d'exposition et de
livraisons, ne pas lancer de diagnostic 5×5. Les caps 42k/180k/400k
et la seule option 0→1 restent strictement identiques.

## Troisième verdict moteur et économie du préfiltre FAST

Campagne `road100_v36_fastbridge_roadonly_seed42_1x1_20261028`, bundle
`6c0bb06556c6b2178311a38cf7fa11499c48b077c23bf39ef8520f8e79729e52`,
suite **3 254 tests OK**, deux parties moteur `complete`. La troisième
conception n'a pas produit de trace : cinq tentatives GRAPH dont
`fast_reason=FAST_OPCAP` sur les deux premiers couples, après seulement
deux ou trois variantes géométriques. H1 Opex ON **19 072 £/an**,
OFF **20 797 £/an**, AAA ON **98 965 £/an**, delta **−1 725 £/an**.
**NO-EXPOSURE/NO-GO** ; toujours **0/5**, sans 5×5 ni Gate A.

**Hypothèse technique supplémentaire préenregistrée avant nouvel essai :**
le préfiltre FAST revient à réitérer sur chacune des 43..190 tuiles des
tests natifs d'occupation, puis les répète à la matérialisation de sa
trace ; c'est exactement ce qui le fait dépasser 6k avant publication.
Déplacer l'autorité des contrôles d'occupation *pour chaque arête*
vers `OpexRoad100LongVerifyTrace`, qui les exécute déjà systématiquement
avant le devis ou l'admission et refuse les stations/dépôts tiers, ainsi
que les arêtes impossibles. Le FAST reste strictement **non vérifié** :
il ne doit annoncer qu'une candidate géométriquement contiguë, avec
absence de cycles, axes de quai corrects, virages géométriques plausibles
et couloirs dans les limites carte/longueur. Il peut conserver les tests
de station/dépôt aux seuls coudes/points de liaison pour une élimination
bon marché. Aucune arête spéculative ne peut être créditée comme vraie
liaison : `LongVerifyTrace` puis chantier transactionnel restent
obligatoires ; les mêmes limites 8k FAST, 42k tentative, 180k couple,
400k année et une seule option ON−OFF sont maintenues. Si le vérificateur
rejette la candidate, enregistrer son stade, l'arête et le code d'erreur.

## Quatrième verdict moteur et diagnostic des variantes

Campagne `road100_v36_fastbridge_lowops_roadonly_seed42_1x1_20261028`,
bundle figé `f2b03291e4a3665f8b04c961b26b0b901b9e5398e4e142ba2647a81826b456f9`.
Les deux parties OpenTTD sont `complete` ; les 3 254 tests ont terminé
`OK` (5 ignorés, 2 échecs attendus). La suppression des sondes natives
d'occupation par tuile FAST n'a toujours pas produit de corridor :
`fast_reason=FAST_OPCAP`, `fast_ops=6346` en 3 variantes sur le
premier marché et `6103` en 2 variantes sur le second ; fallback
`GAP_OPCAP`. Aucune trace, aucun LONG admis. H1 : Opex OFF 20 797 £/an,
Opex ON 19 072 £/an, AAA OFF 94 472 £/an et AAA ON 98 965 £/an.
Δ Opex ON−OFF = −1 725 £/an, NO-EXPOSURE/NO-GO, **0/5 parités**.

**Prédiagnostic avant le prochain smoke :** les rejets de chaque variante
FAST sont masqués par le motif terminal `FAST_OPCAP`. Instrumenter les
motifs précoces par variante, réduire la fréquence des mesures d'opcodes
dans la boucle géométrique (de chaque 5 à chaque 16 tuiles), sans relever
les caps FAST 8k / Graph 42k / paire 180k et sans alléger
`OpexRoad100LongVerifyTrace`. Ce smoke diagnostique ne qualifie aucune
route spéculative : si un candidat apparaît, recueillir obligatoirement
le blocage précis du vérificateur avant toute admission ou chantier.

## Cinquième verdict et préfiltre de cycles, hypothèse suivante

Campagne `road100_v36_fastbridge_variant_diag_roadonly_seed42_1x1_20261028`,
bundle `39b87b2e101b8389f2c29eeecbb8a97c2f09fe1cdd6ed88d1ae5c77bea987998`,
tests intégraux **3 255 OK** (5 ignorés, 2 attendus), deux parties
OpenTTD `complete`. Aucune trace : premier couple (town18→2)
`fast_rejections=3:FAST_REJECT_CYCLE;1:FAST_REJECT_CYCLE;2:FAST_OPCAP`,
6 338 opcodes FAST ; second (town26→23)
`3:FAST_REJECT_TURN;1:FAST_OPCAP`, 6 149 opcodes FAST. Les
replis sont `GAP_OPCAP`, puis `SLEEVE_*_OPCAP` et `COUPLE_OPCAP`.
Profit H1 inchangé : Opex OFF 20 797, ON 19 072, AAA OFF 94 472,
ON 98 965 £/an, soit −1 725 £/an ON−OFF ; **NO-GO, 0/5**.

**Hypothèse préenregistrée avant un sixième smoke :** les premiers
couloirs orthogonaux perdent l'essentiel des 8k opcodes à détecter
*après parcours* que la polyligne recoupe une tuile d'un sleeve A/B
réservé (ou un quai). Vérifier ces intersections **par formule
géométrique, avant la génération par case**, avec les coordonnées
obtenues des indices existants, puis ne parcourir que les variantes
qui ne recoupent pas les sleeves. Ne créer aucun faux lien entre
routes ni crédit de connexion ; conserver le test de cycles exhaustif
pendant la matérialisation, les gardes de virage, le contrôle
`LongVerifyTrace`, la construction transactionnelle et tous les caps
8k/42k/180k/400k. Mesurer les candidats, la raison exacte de rejet
`phase=verify` et les profits réels. Aucun diagnostic 5×5 si NO-GO.

## Septième verdict : double matérialisation de la même route

Campagne `road100_v36_fastbridge_monotone_roadonly_seed42_1x1_20261028`,
bundle `a410bc6752c2059d5f8fbc13372f22fc1a2c521f85c7f9aa940abfcd72c08791` ;
3 256 tests OK et deux parties `complete`. Le corridor monotone
du premier couple atteint la fin de son parcours, mais `fast_ops=8588`
dépasse la borne 8k et annule la candidate ; autres variantes refusées
pour `SLEEVE_CROSS`. Le second couple revient à `FAST_OPCAP`
(6 259 opcodes) après 3 rejets géométriques. Aucune trace, aucun
`phase=verify`, aucune construction LONG. Profits H1 inchangés :
Opex OFF/ON 20 797/19 072 et AAA OFF/ON 94 472/98 965 £/an ;
**NO-GO, 0/5**.

**Hypothèse d'optimisation avant prochain smoke :** la version actuelle
alloue une liste de tuiles `path` de 43..190 éléments puis la parcourt
une deuxième fois pour allouer chaque arête `{from,to}` dans `trace`.
Produire les arêtes une seule fois, en flux contigu depuis le vrai
sleeve A vers le vrai sleeve B (sans allocation de `path`). Garder
un suivi du précédent et du courant pour les virages, l'unicité
des sleeves physiques, la monotonie du pont et le contrôle des axes
des arrêts. Aucun test moteur contourné, aucune réduction des réserves
ni hausse des caps FAST 8k / Graph 42k / paire 180k. Si la trace passe
FAST, le véritable `OpexRoad100LongVerifyTrace` doit encore produire
un verdict par arête avant toute admission, devis ou chantier.

## Sixième verdict et suppression des doublons de parcours

Campagne `road100_v36_fastbridge_prefilter_roadonly_seed42_1x1_20261028`,
bundle `6111b49632f5727b1653556bab657fa033eac6f9cad08620670ecfccc1bea069`,
suite **3 256 tests OK**, deux parties `complete`. Les cycles des
variantes 3 et 1 sont désormais rejetés avant la matérialisation :
`3:SLEEVE_CROSS;1:SLEEVE_CROSS;2:FAST_OPCAP` sur le premier couple ;
`3:FAST_REJECT_TURN;1:SLEEVE_CROSS;2:SLEEVE_CROSS;0:FAST_OPCAP`
sur le second. Les FAST consomment encore 6 392/6 975 opcodes,
aucune trace n'atteint `phase=verify` et aucune ligne LONG n'est bâtie.
Opex OFF/ON H1 20 797/19 072, AAA OFF/ON 94 472/98 965 £/an,
Δ Opex −1 725 £/an : **NO-EXPOSURE/NO-GO, 0/5**.

**Hypothèse causale fixée avant tout nouveau banc :** chaque tracé
retenu est monotone en X/Y quand sa longueur de pont est exactement
la distance Manhattan des pointes ; un tel tracé ne peut physiquement
repasser deux fois sur la même tuile. L'absence de croisement avec les
deux sleeves est désormais prouvée analytiquement par le préfiltre
`FastOnSegment`. Éviter donc les recherches `next in seen` et
`seen.rawset` **pour chaque tuile intermédiaire**, et déplacer la
validation des virages au début de chaque segment orthogonal, plutôt
que sur chaque pas. Garder les contrôles de cycles des véritables
sleeves et de leur suffixe, le test de monotonie, les axes des deux
quais et `LongVerifyTrace` sur TOUTES les arêtes. La validation reste
spéculative avant le chantier réel ; caps intacts (FAST ≤8k, Graph
≤42k, couple ≤180k, annuel ≤400k). Tester le moteur OFF/ON avant
tout diagnostic pluriannuel ; un résultat sans construction est NO-GO.

## Huitième verdict : première trace FAST, première arête moteur impossible

Campagne `road100_v36_fastbridge_singlepass_roadonly_seed42_1x1_20261028`,
bundle `4978f8b99392233a4e0dfd627fd3156efe2c4b47dee7e5b18dde0de3d10483d7`,
3 256 tests OK ; 2 parties moteur `complete`. La matérialisation unique
fait apparaître la **première trace complète** : 154 arêtes,
`FAST_CANDIDATE candidate=1 verified=0`, FAST 6 534 opcodes,
38k/42k non dépassés. Le vérificateur physique rejette aussitôt
la première arête nouvelle : `phase=verify ok=0`,
`stage=AITEST_BUILD_ROAD index=1 from=32674 to=32673 error=260`,
soit (162,127) vers (161,127). Le code 260 est
`ERR_AREA_NOT_CLEAR` dans la nomenclature de ce dépôt. Le couple
suivant échoue encore `FAST_OPCAP`. Aucun LONG admis ou construit.
H1 Opex OFF/ON 20 797/19 072, AAA OFF/ON 94 472/98 965 £/an,
Δ Opex −1 725 £/an ; **NO-GO, 0/5**.

**Hypothèse préenregistrée avant le prochain moteur :** l'arête fautive
est à l'index 1, immédiatement après la façade du vrai quai :
les doglegs historiques n'acceptent que les échecs d'index supérieur
à 1 et seulement les formes non Graph. Adapter la même logique
de détour **exclusivement au dispatch V36**, en gardant sa fenêtre
rectiligne, un détour latéral borné à 1..3 tuiles, au plus 6 alternatives
et le préflight `OpexRoad100LongVerifyTrace` de chaque corridor complet.
Ne jamais poser de route sous `AITestMode` ou annoncer une validation
sur le seul calcul géométrique. Garder trace simple, axes, deux StationIDs,
virages plats, coûts, budget annuel et financier, rollback et seuils
8k FAST / 42k Graph / 180k paire. Journaliser le premier rejet initial,
chaque échec de détour et l'éventuel premier corridor vérifié. Si la
construction physique, les bus et les livraisons restent absents :
**NO-EXPOSURE / NO-GO**, aucun 5×5 ou Gate A.

## Neuvième verdict et correction locale préenregistrée

Campagne `road100_v36_graph_frontdogleg_roadonly_seed42_1x1_20261028`,
bundle `22f5e6440de0d2eb9215723a425b7534cf17d917e161d21a3083dc206986ba07`,
3 257 tests OK, `git diff --check` OK et deux parties `complete`.
Une trace FAST de 154 arêtes reste spéculative ; vérification physique
initiale `index=1 from=32674 to=32673 error=260`. Deux détours testés
par le vérificateur complet échouent aussi, le dernier `index=3 error=260`.
Le compteur total atteint 130 536 opcodes, proche de la réserve
`limitOps - 50000`. Aucune ligne LONG admise/construite ni PASS nouveau.
H1 Opex OFF/ON 20 797/19 106 £/an, AAA OFF/ON 94 472/93 008 £/an :
delta Opex −1 691 £/an, **NO-EXPOSURE / NO-GO, 0/5**.
Le second couple villes 26→23, centre d63, n'émet aucune trace complète.

**Hypothèse avant le dixième smoke :** les deux premiers détours à faible
écart latéral se heurtent rapidement à la même zone de terrain refusée ;
pour ne pas épuiser la réserve sur eux, tester les largeurs `3,2,1` au lieu
de `1,2,3` (deux côtés pour chacune, six au maximum) et journaliser
chaque échec exact `(width, side, index, from, to, error, ops)`.
Le changement reste strictement dans le dispatch Graph-only, garde les
caps 8k FAST / 42k Graph / 180k paire / 400k annuel et la réserve 50k.
Chaque éventuel détour continue de passer le même
`OpexRoad100LongVerifyTrace` complet ; aucun A* LONG, aucune modification
du dogleg historique, aucune admission spéculative, aucun effet OFF.
Critères : au moins un chemin complet validé physiquement, puis devis,
quais, dépôt, bus, livraisons et `profit_year` réel ; sinon NO-GO et
pas de 5×5 ni Gate A.

## Dixième verdict moteur : les trois premières bandes sont bloquées

Campagne `road100_v36_graph_frontdogleg_widefirst_roadonly_seed42_1x1_20261028`,
bundle `327fa2b932bede175f655c89df0ed4e3f99e2cbb735a515d815da9a7081e3b78`.
3 257 tests OK (5 skipped, 2 expected failures), projection OFF byte-exact,
fixture V262 SHA-256 `2FF9C310854E98EBC53EA64D75ADE74948995AF70DF2C847374824463137C4E4`,
`git diff --check` OK ; parties OFF/ON `complete/complete`, même bundle,
option `road100_pax_graph_bridge=0→1` seule modifiée.

La trace FAST reste de 154 arêtes, 6 534 opcodes, `verified=0`.
Le premier refus est inchangé (`32674→32673`, index1, error260).
Le détour largeur3 côté sud échoue physiquement index4
`33442→33441 error260` à 119 097 opcodes ; largeur2 côté sud échoue
index3 `33186→33185 error260` à 131 100 opcodes.
Aucun LONG validé/admis/construit, ni PASS LONG livré. Deuxième couple
town26→23 d63 : trois tentatives, `GRAPH_NO_TRACE`.
`profit_year` H1 Opex OFF/ON 20 797/19 106 £/an ; AAA OFF/ON
94 472/93 008 £/an, Δ Opex −1 691 £/an.
**NO-EXPOSURE / NO-GO, ROAD100 0/5.**

La priorité width3 n'est pas une solution ; ne pas relancer ce bundle.
Prochain problème structurel identifié : sélectionner des sites disposant
d'une véritable sortie routière et éviter de consacrer ~131k opcodes
au premier de trois couples de sites d158, puis traiter la trace manquante
à d63, sans faux lien routier, ni A* LONG, ni relèvement des caps.
La prochaine hypothèse doit être préenregistrée et validée OFF/V262/moteur
avant tout diagnostic 5×5 et Gate A.

## Hypothèse structurelle V36 suivante — accès réel avant géométrie

Les deux derniers smokes isolent deux coûts injustifiés : le couple
town18→2 d158 consomme ~132k opcodes (dont ~77k de scanner sites) puis
rencontre plusieurs obstacles 260 tout près de sa façade ; town26→23
d63 est évalué après lui, avec 213 PASS/mois estimés sur ses racines,
contre 258 sur d158, mais sans trace complète. Le sélecteur actuel
privilégie le proxy de production, la distance servant de départage.

**Avant le prochain smoke**, modifier exclusivement le chemin V36 pour :
(1) prioriser les marchés d43..80 dans les deux créneaux annuels
indépendants, en conservant les marchés longs dans le pool et un
second couple disjoint ; proxy de production uniquement comme critère
de pré-recherche, jamais comme revenu ou ROI ;
(2) parmi les trois couples de vrais sites retenus par le scanner,
prioriser ceux ayant au moins une arête de sortie bidirectionnelle
physiquement connectée ou, à défaut, dont une arête de sortie directe
vers l'autre ville passe réellement `AIRoad.BuildRoad` sous `AITestMode`.
Au plus une arête de sortie par extrémité de couple, avec cache borné,
opcodes supplémentaires ≤6k et réserve 50k inchangée. Cette sonde ne
pose rien et **ne supprime aucun couple** : score nul ou mesure censurée
conserve le candidat en repli, l'ordre de production départage les
égalités. Journaliser marché/score sortie/ops pour rendre visible le
changement de rang et d'exposition.

Validation : projection OFF byte-exact, V262 intacte, suite intégrale,
diff-check, bundle OFF/ON commun sur seed42 H1, vérification complète
des arêtes, deux StationIDs, depot/fleet/ordres/livraisons/cash et
`profit_year` société. Aucune recherche A* LONG, aucune hausse des
caps 8k/42k/180k/400k, aucune dérogation C75/C78, aucun effet AIR/RAIL/WATER.
Sans construction rentable et gain ON−OFF, NO-GO et pas de 5×5/Gate A.

## Onzième smoke : marchés d63 et d68, obstacles physiques plus loin

`road100_v36_access_priority_roadonly_seed42_1x1_20261028`, source figée
`515d788d497f5b5c2be3716ad7f6c0e23452dc87bcf3c7b5784796c9de24d71a`,
deux parties `complete`, suite intégrale 3 258 OK, projection OFF
exacte, V262 inchangée et `git diff --check` OK. L'ordonnancement
GRAPH-first choisit désormais towns26→23 d63 puis towns18→31 d68.
Score de sortie du premier site de chaque paire = 4 (deux raccords
réels bidirectionnels), sonde ~1 050–1 250 opcodes par marché.
Le traceur FAST fournit respectivement 77 arêtes (FAST 3 620 opcodes)
et 71 arêtes (FAST 4 032 opcodes), jamais certifiées par la géométrie.
`OpexRoad100LongVerifyTrace` rejette la première à l'index8
`59976→59720 error=260`, la seconde à l'index18
`38564→38820 error=1281` (signification exacte non déterminée ; le
vrai code `AIRoad.ERR_ROAD_CANNOT_BUILD_ON_TOWN_ROAD` est 2307).
Aucun LONG admis/construit et aucune livraison
LONG prouvée. H1 `profit_year` Opex OFF/ON 20 797/19 103 £/an,
AAA OFF/ON 94 472/97 693 £/an, delta Opex −1 694 £/an :
**NO-EXPOSURE / NO-GO, ROAD100 0/5**.

**Préenregistrement avant prochain moteur :** le nouveau marché plus
court rend possible une recherche de détour local autour d'un refus
index8 (260) ou index18 (1281) ; le helper Graph-only actuel ne traite
que 260 aux indices1..3. Étendre sa fenêtre d'intervention à 1..20,
uniquement pour `ERR_AREA_NOT_CLEAR` ou
`AIRoad.ERR_ROAD_CANNOT_BUILD_ON_TOWN_ROAD`, sans modifier le dogleg
historique, et conserver au plus six détours rectilignes de largeur
1..3 sur les deux côtés. Aucune destruction de route municipale,
aucune route posée pendant une sonde, toujours la revalidation intégrale
`OpexRoad100LongVerifyTrace` de chaque variante, axes de stations,
virages plats, cycles refusés, devis/finance/chantier inchangés.
Les caps FAST 8k, Graph 42k, paire 180k, annuel 400k et réserve 50k
sont inchangés. Journaliser type/position du premier refus, largeur,
côté, succès de revalidation, index/erreur du prochain obstacle, opcodes
restants. Ne pas confondre réparations spéculatives et route bâtie.
Verdict NO-GO si aucun LONG admissible : pas de 5×5 ni Gate A.

## Douzième smoke — fenêtre de détour étendue, zéro variante géométrique

`road100_v36_midtrace_dogleg_roadonly_seed42_1x1_20261028`, source figée
`859768f99ffc1c813fd696c649f53f685a7ea6e0cda2ce7c32762a256d1f55b0`,
deux parties `complete`, même bundle et seul Graph=0→1 modifié. Suite
intégrale 3 258 OK (5 ignorés, 2 expected), OFF exact et V262 intacte.
Les traces FAST d63/d68 réapparaissent (77 et 71 arêtes, 3 620/4 007
opcodes FAST), mais `phase=verify` refuse encore index8
`59976→59720 error260` et index18 `38564→38820 error1281`.
**Aucun détour géométrique n'est émis** (`detours=0` aux deux endroits),
malgré la nouvelle fenêtre 1..20. Aucun projet LONG admis ou construit.
H1 Opex OFF/ON **20 797/19 106 £/an**, AAA OFF/ON
**94 472/93 008 £/an**, Δ Opex **−1 691 £/an**.
**NO-EXPOSURE / NO-GO, ROAD100 0/5**.

**Préenregistrement diagnostic suivant, sans nouvelle hypothèse de gain :**
tracer dans le seul helper Graph-only `OpexRoad100GBFrontDoglegTrace`
la première cause précise de retour `null` pour chaque largeur/côté :
fenêtre rectiligne trop courte, différence d'axes, sortie carte, pente,
cycle, virage, ou longueur 43..190. Retourner ces explications au caller
via un petit objet facultatif ; aucun changement de route, aucune
construction, aucun AITest additionnel, aucun relèvement de budget ni
changement de comportement OFF. Refaire tests ciblés, projection OFF,
V262, suite entière, puis smoke moteur 1×1 distinct seulement pour
établir si le rejet est physique ou géométrique. Tout NO-GO est conservé.

## Treizième verdict : toutes les largeurs échouent aux ancres

`road100_v36_dogleg_geometry_reason_roadonly_seed42_1x1_20261028`,
bundle `fc4f3a4532496bb6b18c4a798f6c764647ca52f9fe6182efc89c25489d8e9b8d`,
suite 3 258 OK et deux duels complets. Les six combinaisons de largeur
1..3 et côtés ±1 du marché d63 renvoient **NONFLAT_ANCHOR** sans détour
constructible ; ni le vrai test de la route alternative ni le devis ne
sont donc atteints. La route initiale reste refusée index8 error260.
Le marché d68 reste refusé index18 error1281, sans événement de détour
géométrique : il faut contrôler la condition de déclenchement du code
municipal, plutôt que présumer sa correspondance numérique.
Opex H1 OFF/ON 20 797/19 106 £/an ; AAA OFF/ON 94 472/93 008 £/an,
delta Opex −1 691 £/an, **NO-GO ROAD100 0/5**.

**Micro-diagnostic préenregistré avant nouveau smoke :** distinguer
sans nouvelle famille de sondes les quatre ancres `first`, `last`,
`bypassA`, `bypassB` dans `NONFLAT_ANCHOR` et journaliser le code
numérique réel de `AIRoad.ERR_ROAD_CANNOT_BUILD_ON_TOWN_ROAD` avec
le premier refus et la réserve d'opcodes. Aucun changement de chemin,
aucune construction en test, aucun cap augmenté, aucune hypothèse de
gain : les valeurs mesureront si un déplacement borné d'ancre est
physiquement envisageable. Aucun 5×5/Gate A sans exposition rentable.

## Quatorzième smoke : ancre de départ non plane, code 1281 distingué

`road100_v36_anchor_reason_roadonly_seed42_1x1_20261028`, bundle
`ccce484adf2c60fe046d3c811e5a59a257ea6b51736551b28d46993d5331159d`,
suite 3 258 OK, deux parties complètes, Graph seul 0→1. Sur les six
détours du marché d63, même motif : **NONFLAT_FIRST**, avant tout test
de la route alternative. L'erreur du marché d68 est 1281, **pas** le
code municipal 2307 confirmé par la constante OpenTTD 15.3.
`profit_year` H1 Opex OFF/ON 20 797/19 106 £/an, AAA OFF/ON
94 472/93 008 £/an ; aucun LONG. **NO-GO 0/5**.

**Hypothèse préenregistrée avant nouveau moteur :** pour le d63,
reculer au maximum **quatre arêtes supplémentaires** sur le même axe
rectiligne pour chercher une ancre de départ plane, sans dépasser
l'indice1 (façade), franchir un virage, modifier les arrêts, ou
inventer des liaisons. Vérifier ensuite à nouveau axes des arrêts,
virages, collisions, route entière via `OpexRoad100LongVerifyTrace`,
devis et construction réels. Caps et réserve 50k inchangés. Si aucune
ancre plane n'existe, refuser la variante. L'erreur1281 reste
hors traitement municipal non prouvé. Pas d'A* LONG ni Gate A.

## Quinzième smoke : nouveau détour physique, mais sortie urbaine inaccessible

`road100_v36_flat_anchor_backoff_roadonly_seed42_1x1_20261028`, bundle
`e7cb66636924180e547bc134e87b3b9d348ff91f5ca2cb8758c9f8696d603cbf`,
3 258 tests OK (5 skipped, 2 expected), source OFF exacte,
V262 SHA inchangée, 2/2 jeux `complete`, seul Graph 0→1 modifié.
Le recul rectiligne d'ancre produit **cinq véritables variantes de
géométrie** d79..83 sur le d63 (contre 0) ; le vérificateur physique
les refuse toutes dès l'index4, depuis la même ancre `(72,238)`
`61000` vers 61001/60999, erreur260. Les variantes consomment au total
~132k opcodes ; la réserve de 50k stoppe le sixième essai.
Le d68 garde index18/error1281 de type exact non déterminé, distinct
de 2307 municipal. Aucun LONG admis ou construit, aucune nouvelle
livraison PASS prouvée. H1 Opex OFF/ON **20 797/19 103 £/an**,
AAA OFF/ON **94 472/97 693 £/an**, Δ Opex −1 694 £/an.
**NO-EXPOSURE / NO-GO, ROAD100 0/5**.

Ne pas relancer le même sixième détour ni augmenter les caps. Le
goulot structural n'est plus une ancre non plane : le premier segment
latéral issu de l'ancre réellement plane est lui-même non constructible
de chaque côté (260). Reprendre la sélection de *vrais corridors*
existants ou de nouvelles paires de sites accessibles, avec budget
physique et financier complet, plutôt que dépenser la paire180k sur
une unique vallée urbaine irréalisable. Toute future hypothèse doit
rester opt-in, OFF exact, test moteur/économique réel avant Gate A.

## Hypothèse V36 suivante — classements des accès physiques avant Top-3

Nouvelle demande utilisateur du 28/10 : réutiliser les principes de la
recherche RAIL et des sites AIR/RAIL récemment poussés sur `origin`, et
examiner les principes routiers AAAHogEx/AAAHogNet sans copier de code.
Provenance étudiée : `origin/master` `12e4d39f` (repli EB-2 gare neuve),
`air_site_ranked.nut` (présélection native puis admission physique) et
`task_rail.nut::_startRailSearch` (sources et destinations multiples avec
heuristique de coût). Ces changements distants ne sont **pas fusionnés**
dans l'arbre ROAD100 dirty.

Hypothèse **avant moteur** : `OpexRoad100LongConstructPlan` réduit actuellement
jusqu'à seize couples de quatre sites à trois *avant* de contrôler leur
sortie physique. Un quai à forte production mais sa façade menant à une
impasse peut ainsi évincer un site réellement connecté. Sous **le seul
opt-in V36** `road100_pax_graph_bridge=1`, comparer les seize couples
avec un micro-score de 1–2 arêtes de route **déjà connectées dans les
deux sens** et orientées vers le site opposé, cache partagé, temps borné
à 4 000 opcodes, sans aucune construction ou `AITest` supplémentaire.
Utiliser ce score comme premier départage *avant* le Top-3, la production
native et la distance conservées pour les égalités ou données censurées.
Un zéro ou une mesure censurée **n'exclut jamais** les sites du pool ;
seules les trois paires réellement exécutées changent éventuellement.

La stratégie est un **classement de sites**, pas une preuve de route.
Les bords non connectés restent hypothétiques et passent par
`OpexRoad100LongVerifyTrace`, devis, deux StationIDs, dépôt, vrai chantier
transactionnel, bus, ordres, PASS livrés. Pas de nouvel A* LONG, pas de
copie de code AAA, ni modification AIR/RAIL/WATER. Conserver les caps
8k FAST, 42k GRAPH, 180k paire, 400k annuel et réserve 50k.
Journaliser le score pré-Top-3, scores des 3 paires, dépenses et verdicts
physiques ; comparer OFF/ON sur bundle unique seed42 H1. **NO-GO** si
aucun nouveau LONG construit ni gain économique ; ne pas lancer 5x5
ou Gate A avant preuve d'exposition rentable.

### Seizième smoke : coût du classement avant Top-3 non amorti

`road100_v36_railair_site_rank_roadonly_seed42_1x1_20261028`, bundle
`a0187cd9f024593f07ba8b4baba6eab1df7975299bc2c7c82d2265c4c2bd245f`,
deux parties complètes, 3 259 tests complets OK (5 skipped, 2 expected),
source OFF exacte et V262 inchangée. Le classement a examiné 6 puis
8 paires de sites, mais la sonde tous-axes 2 pas a consommé
6 482–7 016 opcodes avec **tous les `pre_top3_road=-1` censurés** :
aucune amélioration de l'ordre des couples. Le d63 reste refusé
`index8 error260` (5 détours, tous échoués) et le d68 `index18 error1281`.
Aucun LONG nouveau. H1 Opex OFF/ON 20 797/19 103 £/an, AAA
94 472/97 693 £/an ; delta Opex −1 694 £/an : **NO-GO, 0/5**.

**Hypothèse fixée avant le smoke suivant :** le classement native-cheap
doit remplacer les tests de quatre voisins avec quatre seconds voisins
par **seulement les deux directions cardinales menant au partenaire**, puis
au plus un prolongement rectiligne sur l'arête réellement connectée.
Le lien station→front est déjà testé par le scanner des sites et n'est
pas refait ; 4 000 opcodes restent le plafond de classement et la limite
par paire 180k/année400k, réserve50k ne changent pas. Retour `-1` si
censuré, aucun site rejeté pour cette seule mesure. Le bon signe mécanique
est un ou plusieurs scores 0..8 au lieu de tout `-1`, et un nouvel ordre
Top-3 explicite. Le bon signe économique nécessite toujours chantier,
vrais bus et PASS livrés, plus `profit_year` Opex/AAA H1 ; sinon NO-GO.

### Dix-septième smoke : l'accès mesuré change les sites, pas le tracé

`road100_v36_railair_site_rank_axis_roadonly_seed42_1x1_20261028`, bundle
`bebee153bfbe68066be40589039c5e877aeabfdcc7d95d90f5bcf7f6c34bf143`,
3 259 tests OK (5 ignorés, 2 attendus), OFF exacte et deux parties
complètes, même source, Graph seul 0→1. Les scores pré-Top3 deviennent
`8,4,-1` pour d63, `8,8,-1` pour d68 : **la présélection fonctionne** et
change effectivement les sites d63. Les traces d63 66/64 arêtes sont
rejetées `index21 error260` puis `index5 error260` ; la d68 71 arêtes
reste rejetée `index18 error1281` (non identifié). Aucun LONG admis,
construit ou livré. H1 Opex OFF/ON 20 797/19 103 £/an, AAA
94 472/97 693 £/an : delta Opex −1 694 £/an, **NO-GO, 0/5**.

**Hypothèse suivante avant moteur — réparation A* locale inspirée du rail :**
Le nouveau meilleur site atteint l'index21 avant 260, donc son accès
physique est moins fragile qu'auparavant. Plutôt que retenter six doglegs
orthogonaux ou un A* LONG, lorsqu'une trace GRAPH a un premier refus
physique `ERR_AREA_NOT_CLEAR` 260, tenter **un seul chemin local alternatif**
de part et d'autre de cette arête. Recherche best-first bornée à
24 expansions et 96 états, rayon local Manhattan≤11, profondeur≤18,
coût moindre pour arêtes vraiment connectées et pour virages limités ;
les tuiles de stations/dépôts tiers, cycles, fausses adjacences et virages
non plats sont exclus. La géométrie n'utilise **aucun** BuildRoad ni
AITestMode ; l'arête initialement refusée n'est jamais créditée. Route
43..190, axes des deux quais conservés, aucun nouveau site implicite.
Toute proposition est entièrement revérifiée par
`OpexRoad100LongVerifyTrace` avant devis/finance/chantier transactionnel,
et aucune admission sans revalidation réussie. Un seul essai avec plafond
local 18k opcodes et la réserve partagée `limitOps-50000`, sans modifier
les plafonds FAST8k/GRAPH42k/paire180k/année400k. Journaliser le premier
rejet, expansions, opcodes, réussite/rejet de la réparation et nouveau
code d'erreur. En cas de NO-GO, conserver les preuves, ne pas faire de
5×5/Gate A sans chantier et rentabilité.

### Premier moteur de réparation locale : erreur de compilation isolée

`road100_v36_rail_local_repair_roadonly_seed42_1x1_20261028`, bundle
`316a29ae34840ab2213677a9a94675e2f23642e603c0b0beeff1512591f69edd` :
le banc est **invalide**, les deux IA OpexAI échouent au chargement,
`road100_graph_bridge.nut:175/40 expected IDENTIFIER`. La clé de table
Squirrel `parent` est réservée (`AGENTS.md` §2). Le correctif purement
syntaxique préenregistré consiste à remplacer cette clé et ses accès par
`parentIndex`, sans modifier la recherche, les budgets, les tests physiques
ni la stratégie. Réexécuter ciblés, OFF, V262, suite entière puis un smoke
avec **nouveau bundle**, sans réécrire cette campagne invalide. Aucun
résultat `profit_year` de ce moteur n'est admissible comme diagnostic.

### Dix-huitième moteur corrigé — recherche locale trop chère

`road100_v36_rail_local_repair_syntaxfix_roadonly_seed42_1x1_20261028`,
bundle `8b6fa6bf995e4b843ea42cfe16efb686d78409c21f758985756e954823352d79` :
3 260 tests complets OK (5 ignored, 2 expected failures), OFF source
exacte, 2/2 parties complètes. Sur d63, la réparation A* locale
autour de l'arête21 refusée 260 explore seulement **10 nœuds / 31 états**
en **18 263 opcodes**, dépasse son propre cap18k, ne produit pas
d'alternative et ne revalide donc aucun nouveau corridor. d68 reste
refusé index18/error1281 (non interprété). Aucune ligne LONG nouvelle.
`profit_year` H1 Opex OFF/ON **20 797/19 103 £/an**, AAA OFF/ON
**94 472/97 693 £/an** ; delta Opex −1 694 £/an,
**NO-EXPOSURE / NO-GO, ROAD100 0/5**. Ne pas relancer ce bundle.

**Prochaine hypothèse avant moteur :** les requêtes natives dans chaque
successeur A* (route, connexité, déblaiement, platitude) rendent les
24 expansions théoriques inatteignables en 18k. Séparer recherche rapide
et vérification : garder la topologie directionnelle, occupation des
stations tierces, cycles et terrain de virage, mais ne **jamais créditer**
une route spéculative comme connexion réelle ni appeler
`AIRoad.AreRoadTilesConnected` sur chaque successeur. Un voisin inconnu
coûte le prix majoré d'une **nouvelle** arête ; même si elle existe, le
modèle ne bénéficie pas artificiellement du bonus « route existante ».
La route complète reste filtrée par `OpexRoad100LongVerifyTrace` et la
construction réelle. Le budget local18k, les 24 expansions, 96 états,
pair180k et réserve50k restent stricts. Journaliser expansion, premier
refus de chaque retest et coûts, et conserver NO-GO sans travaux réels.

### Dix-neuvième smoke — staging natif encore insuffisant

`road100_v36_rail_local_repair_staged_roadonly_seed42_1x1_20261028`,
bundle `610230930c780b90a08d7ec1ba723fe6043f9c0c6d0c5267c405ff75a92cfb54`,
3 260 tests OK, OFF inchangé et deux moteurs `complete`. Les appels
natifs déplacés du successeur vers le nœud exploré donnent seulement
**14 expansions / 33 états / 18 261 opcodes** avant `REPAIR_OPCAP`,
aucune trace locale vérifiable. Le d68 refuse encore `index18 error1281`.
Aucun LONG, H1 Opex OFF/ON 20 797/19 106 £/an, AAA OFF/ON
94 472/93 008 £/an : ΔOpex −1 691 £/an, **NO-GO 0/5**.

**Prérégistration d'un seul dernier test de faisabilité de recherche locale :**
le prochain pathfinder ne fera que de la **géométrie arithmétique** dans
sa petite fenêtre (coordonnées X/Y de nœud, longueur Manhattan entière),
en interdisant l'arête exacte rejetée, sans présumer que la tuile entière
est interdite. Aucun `AIRoad.AreRoadTilesConnected`, aucun `AITestMode`,
aucune vérification de station/dépôt par successeur ou expansion ; la
géométrie reste clairement **spéculative**, chaque tuile/arête conservée
étant vérifiée par le vérificateur commun (occupation, liaison réelle,
AITest BuildRoad, coût). L'absence de filtre natif dans la **proposition**
n'est pas un assouplissement d'admission. Gardes de carte exactes sur
X/Y, protection des extrémités, cycle/virages, et caps 24 expansions,
96 états, 18k local, 180k paire, 400k annuel, réserve 50k inchangés.
Critère technique : produire un candidat sous les limites et observer
le `retest` physique avec sa première erreur ; si celui-ci échoue,
**NO-GO**, ne pas itérer d'autres heuristiques locales sans un nouveau
fait terrain. L'exposition rentable, et non le seul retest, reste le
prérequis des diagnostics H1–H5 et Gate A.

### Vingtième smoke — géométrie A* arithmétique sans exposition

`road100_v36_rail_local_repair_arith_roadonly_seed42_1x1_20261028`,
bundle `cf675df6682af97d0d663550e42c8c28c5668703b59dd16e2879c5b9c2b21bc7`,
3 260 tests intégralement OK (5 skipped, 2 expected), projection OFF
exacte, fixture V262 inchangée, 2/2 duels complets sur bundle commun,
Graph 0→1 seul réglage variable. Même en supprimant tous les appels
natifs de **l'expansion de géométrie**, seulement **14 expansions / 36
états / 18 209 opcodes** : `REPAIR_OPCAP`, zéro trace locale livrée
au vérificateur. Les arêtes initiales refusées sont inchangées : d63
index21 `error260`, d68 index18 `error1281` non identifié. Aucun LONG
admis/construit, aucun nouveau PASS LONG livré. H1 `profit_year`
Opex OFF/ON **20 797/19 106 £/an**, AAA OFF/ON
**94 472/93 008 £/an** ; Δ Opex **−1 691 £/an**,
**NO-EXPOSURE / NO-GO, ROAD100 0/5**.

Le dernier test de faisabilité locale ne passe pas sa propre porte :
**ne pas augmenter 18k ou recommencer des micros variantes Squirrel**
de cette boucle. La prochaine architecture à instruire, avec un
préenregistrement distinct et mesures d'opcodes, est un constructeur
routier **reprenable en tranches comme `_startRailSearch`**, retenant
son état de recherche entre passages PO01C et l'invalidant sur
modification de sites/carte/save-load. Il devra privilégier les vrais
tronçons connectés, intégrer les sites alternatifs AIR/RAIL comme
sélection avant recherche, et proposer plusieurs marchés d43..80/d80..160.
Ce n'est pas une permission d'emprunter le code AAA : seulement les
principes de coût, admissibilité et itération. Le devis réel, les deux
StationIDs, le dépôt, les bus, les ordres, les PASS livrés et le
`profit_year` de société restent les conditions de succès ; aucun
5×5/40×5 avant exposition rentable.
