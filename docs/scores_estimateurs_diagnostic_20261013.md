# Scores et estimateurs — diagnostic et propositions du 13/10/2026

Étude demandée par [le prompt](prompt_scores_estimateurs_20261013.md), sans modification de l'IA,
sans partie Docker, sans changement de défaut ni commit. **Mise à jour après pull `7c362e1` :
la clôture V165 retire P1 (attente courte) des suites actives.** Trois propositions restent à
évaluer, dans l'ordre P2 (a priori), P3 (marge dans le score seulement), P4 (cohortes C70).
Ce sont des hypothèses, pas des gains qualifiés ; aucun multiplicateur favorable au rail adopté.

## 1. Provenance et limites de cette étude

- Code relu : `origin/master` **caec5720105e52293e25ce87f3ffc8a298620d68**, extrait par
  `git archive` dans `results/scores_estimateurs_audit_20261013/source/`. Cette copie sépare
  l'étude des modifications locales préexistantes de `probes.nut`, des diagnostics P0 et des docs.
- Le pull direct depuis `c79bf0f` a d'abord été refusé par Git. Après autorisation utilisateur,
  sauvegarde vérifiée de 128 fichiers locaux, stash ciblé puis pull en avance rapide vers
  **`7c362e19f8724ee5f48c3a3e5aef10dd87863141`**, restauration et résolution des deux conflits
  d'insertions dans `docs/taches.md` en conservant les deux ensembles. Code local restauré sans
  conflit ; aucun commit/push. Le commit ajouté depuis l'étude ne change que V165 dans les docs.
  Sauvegarde : `results/scores_pull_preserve_20261013/` ; stash de secours conservé
  `e706bfc3293f1da5151d50264a7a587cd836ddd0`.
- Sources de mesures : [tâches, V149/V161/V165](taches.md),
  [estimé/réalisé](estime_realise_par_ligne_20261012.md),
  [capital](capital_quote_p0_20261009.md),
  [territoire d'abord](c121_territory_first_40x3_20261011.md).
  Les journaux V149/V165 du worktree VPS `wt-v149-rail-unblock` ne sont pas présents dans ce
  checkout ni ses worktrees Git listés. **Leurs statistiques sont reprises comme résultats
  documentés, non recalculées ni réauditées ici.** Aucun bundle V149 n'est déclaré qualifié par
  cette étude. Aucun code de l'adversaire n'a été copié.
- Les chiffres du rapport estimé/réalisé portent sur d'autres arbres et des cohortes sélectionnées.
  Les valeurs 0,463 AIR, 1,850 rail et 0,480 flotte ne sont pas des coefficients prêts à adopter.
  Notamment, ce rapport déclare l'appariement du renfort **non résolu au convoi** : son ratio de
  flotte ne démontre pas un rendement marginal causal.
- Contrôles réalisés : lecture des définitions, chargements et consommateurs ; calculs illustratifs
  explicitement distingués des mesures ; contrôle des liens locaux et du diff. Pas de compilation
  Squirrel, de nouveau diagnostic moteur ni de qualification économique.
  Le contrôle reproductible est conservé dans
  `results/scores_estimateurs_audit_20261013/check_document.py` et son résultat
  `document_check.json` : empreintes de l'archive/code, symboles, repères et calculs.
  Le prompt est maintenant présent localement après synchronisation.

**Décision courante V165 reçue avec le pull.** Les mêmes journaux documentent un chantier AIR
suivant 14–20 jours après l'achat hors AIR en médiane, et une estimation d'effet de 10–50 k£/an,
sous le seuil A d'environ 80 k£. Le fil des seuils est clos sans banc. Cette chronologie ne fournit
pas à elle seule un contrefactuel causal, mais la clôture du backlog doit être respectée : P1
n'est plus une recommandation active, aucun dépouillement ou banc supplémentaire proposé sur
l'attente. P3 ne reste distinct que parce qu'il conserve intégralement les seuils de cash ;
aucune variante de « marges cohérentes » qui modifie l'abordabilité n'est proposée.

## 2. Corrections nécessaires au cadrage

| Affirmation du prompt | Vérification au SHA étudié et conséquence |
|---|---|
| Le score est seulement `profitCalibré / max(K_dec, capitalDeFinancement)` | C'est le noyau numérique, mais `OpexProjectInsertDefensive` classe d'abord par **priorité C77**, puis score éventuellement corrigé par `AIR_EARLY_SLOT`, puis revenu et stabilité. Une meilleure prévision peut ne changer ni la tête ni l'achat. |
| Capital utilisé pour l'abordabilité et le score identique | `OpexProjectFromAir` distingue `budgetCapital` de `decisionFinanceCapital`. La sélection teste le premier, puis peut employer le second au dénominateur. Il faut tracer les deux ainsi que `economics` et `decisionEconomics`, avant de conclure à une marge excessive ou à un mélange de profondeurs. |
| Rail : 50 % de production et cadence cible de 7 jours | Les 50 % dimensionnent la rame initiale. Le revenu emploie **`OpexStationRatingForHeadway(effectiveHeadway)`**. Les 7 jours alimentent `trainsForHeadway` après le choix, sans imposer le nombre retenu par cette boucle. |
| Rail : convoi unique rigide ; seconde rame évaluée par le helper cité | `OpexLineEconomics` compare **1 et 2 rames** au ROI sous `ECONOMY_FIX`. `OpexRailSecondTrainMarginal` est défini, mais aucune invocation n'a été trouvée dans `ai/OpexAI`. L'expansion active passe par `_expandRailLines`, avec profit passé positif, backlog, cash, puis construction/upgrade. |
| Les estimateurs de transformés/subventions sont absents ou inconnus | Ils existent : `OpexGoodsChainCandidates` additionne les économies de deux segments ; `OpexGenerateSubsidyCandidates` lisse un bonus temporaire sur le temps de retour du capital et vérifie un délai de chantier. Leur précision récente reste inconnue. |
| Rail : 2 700 opcodes par itération | La constante active de `projects.nut` vaut **3 105** ; plusieurs commentaires gardent 2 700. Ne pas calibrer un coût sur un commentaire. |
| Paiement physique C121 rejeté donc OFF | Le verdict du 09/10 reste `fail_primary`, mais **`air_c121_physical_payment_days=1` aux quatre difficultés** dans `info.nut`. L'état courant et la preuve statistique sont deux faits distincts. Pas de nouvelle proposition sur ce levier. |
| « Nous divisons toujours par le capital » | C69 introduit déjà `F × τ`. C49 a aussi étudié un dénominateur variable ; le journal du 13/09 interdit sa reformulation immédiate. `simple_opcode` reste rejeté. Un nouveau ratio profit/opcode n'est pas retenu ici. |

Repères de code : `projects_models.nut:220,267`, `projects_selection.nut:1077,1228,1508,1527`,
`projects_builders.nut:337`, `economy.nut:159,469`, `task_rail.nut:729`, `projects.nut:33`,
`info.nut:690`. Numéros attachés au SHA ci-dessus.

## 3. Diagnostic par estimateur et par opération

### 3.1 Calibration, K_dec et financement commun

`OpexC70C82AccumulateLine` attend l'âge 2, puis calcule
`real = profitVehicules × trains0 / vehCount - predAmort`. Les ratios sont cumulés par ligne,
puis moyennés entre lignes avec une pseudo-ligne de ratio 1. Ce n'est ni le ratio des profits
totaux ni une mesure marginale. Le nombre présent au relevé n'est pas un nombre de véhicules-années.
Une flotte doublée en novembre peut donc diviser presque toute l'année passée par deux ; inversement,
la baisse d'une flotte peut gonfler le profit normalisé. Les effets de demande, partage et congestion
ne sont pas linéaires en N. **Mécanisme certain ; fréquence et amplitude de ce biais non mesurées ici.**

Un facteur commun conserve l'ordre au sein d'une famille à provenance identique, mais change
l'arbitrage entre modes et entre projets exemptés/non exemptés. Les exemptions R2, réalisation
directe C121 et V161 doivent être conservées : multiplier tout l'AIR par un deuxième facteur
produirait des doubles corrections. Le log `C121_REALIZATION factor=` ne publie pas directement
`C121_AIR_P0_DIRECT_FACTOR` ; pour établir le facteur effectif, lire aussi le nombre d'observations,
le bras et la branche active. Zéro ligne implique bien ici le repli à 1.

`OpexC69ComputeKDec` utilise un flux d'exploitation et une cadence de constructions endogènes.
Il ne mesure ni le prochain encaissement certain, ni le temps propre de chaque chantier. Si le flux
ou le nombre de constructions est nul, `K_dec=0`. Modifier un score peut modifier les constructions
puis K_dec : un rejeu à K_dec figé n'est qu'un diagnostic instantané.

`OpexProjectSelectAffordable` filtre le cash **avant** le tri. Un projet non finançable ne gagne
pas en augmentant son score. Les montants de marge sont du cash requis, pas des dépenses annuelles.
La réserve trimestrielle et les marges ne constituent pas nécessairement un doublon : elles couvrent
des besoins différents. Le portefeuille retient des alternatives testées sur le même budget ; ce
n'est pas une résolution globale de sac à dos. Les achats et revalidations réelles restent à suivre.

**Classement de 1971 :** les résultats documentés placent AIR vers 1 346–1 606, rail vers 283–325,
flotte vers 196–199. Illustration, pas rejeu : AIR ×0,37 donne 498–594 et rail ×0,87 donne 246–283.
Cette correction grossière peut donc laisser l'AIR devant, tout en laissant intact le problème
d'abordabilité. Cela ne prédit aucun gain et ne garantit pas l'ordre pour chaque projet individuel.

### 3.2 Rail neuf, voyageurs et fret

- **Revenu :** vitesse effective avec accélération, nombre de voyages chargés, note liée à la
  cadence, plafond de capacité et tarif API. Pour le fret, l'absence de la rame est approximée
  par `max(allerRetour - tempsChargement, 0)` pour la note. Ce n'est pas une simulation des
  files, du chargement, des pannes ou des livraisons. Pour les voyageurs, le traitement agrégé
  peut masquer l'asymétrie des deux bassins. Ce sont des limites de modèle ; la cause précise
  du faible réalisé voyageurs n'est **pas établie** par sept lignes.
- **Coût :** longueur de trajet × coût de voie, quais, matériel et dépôt conditionnel. Avant
  A*, la géométrie et les obstacles restent inconnus ; après A*, l'économie de trajet et le
  capital sont réconciliés. Le coût de la deuxième voie n'est pas représenté par une deuxième
  copie complète de l'infrastructure dans la boucle économique initiale. Cela peut favoriser
  une variante à deux rames ; l'exposition au défaut et l'écart total doivent être vérifiés
  dans les devis et constructions. Ne pas en déduire un facteur terrain uniforme.
- **Profit :** l'exploitation compte les locomotives, l'amortissement les véhicules. La pertinence
  du coût courant des wagons dépend du catalogue effectivement utilisé ; aucun surcoût positif
  n'est affirmé sans le lire. L'infrastructure n'est pas amortie au défaut.
- **Effet sur le rang :** une sous-estimation de coût peut favoriser longs trajets/doubles voies
  avant devis ; une sur-prévision de demande favorise voyageurs et petits bassins. À l'inverse,
  la disponibilité d'un cargo, d'un candidat ou du slot A* est un problème de génération/exécution
  que la précision du score ne résout pas.

Les ratios documentés du 13/10 (fret 0,87, voyageurs 0,17–0,26) sont annualisés sur exploitation
partielle. Ils ne se comparent pas directement au 1,850 rail du rapport antérieur, ni à une année
mûre : cohortes, durées, matériel et périmètres diffèrent. Une annualisation avec montée en charge
peut sous-estimer le régime établi ; ce n'est pas une borne basse mathématiquement garantie si la
demande baisse ou si la concurrence s'intensifie. Ventiler COAL/WOOD/IORE/GRAI/LVST/OIL par cargos
API, jamais par IDs supposés. **Justesse par cargo : INFO NON DISPONIBLE.**

### 3.3 Rail : wagon supplémentaire, seconde rame, doublement

`_expandRailLines` estime le gain d'un wagon par variation de capacité théorique recalée sur
`lastRevenue`, après rentabilité et saturation observées ; il retranche roulement/amortissement
du wagon. La demande future et l'allongement de cycle restent des hypothèses. Pour la seconde
rame, le chemin actif inspecté est une règle profit/backlog/cash, pas le helper marginal dormant.
Un bon score de ligne ne garantit donc pas un bon rendement de cette opération.

Il faut distinguer coût du wagon, locomotive complète et infrastructure additionnelle, ainsi que
revenu supplémentaire de la ligne et perte éventuelle des autres services partageant la gare.
**Gain marginal récent et classement contre un projet neuf : INFO NON DISPONIBLE.** V107bis a
déjà échoué à A40×3 ; son retour au portefeuille n'est pas proposé sous un autre nom.

### 3.4 AIR neuf : newpair, hubsite, hubhub

`OpexC121AirEconomics` possède déjà vol/manœuvres, rating dépendant de la cadence, partage,
capacité de piste, passagers/courrier séparés et cannibalisation. Le temps physique de paiement est
ON au SHA étudié. **« Ajouter congestion, rating ou concurrence » ne serait pas une idée neuve.**
Le débit de piste explicitement positif dans `OpexC121AirportRunwayServiceDays` est spécialisé
sur `AT_LARGE` ; il faut vérifier les types réellement exposés avant toute extrapolation.

Les ratios documentés indiquent une sur-prévision nette dans leurs cohortes, sans identifier seuls
si elle vient de capture, départs réalisés, remplissage, tarif ou pertes sur les voisines. Le
profit C121 soustrait la cannibalisation à son revenu ; le profit observé de **la seule nouvelle
ligne** ne contient pas cette externalité. Comparer ces deux grandeurs ne mesure donc pas toujours
le même objet. Séparer bénéfice propre et bénéfice net du réseau, ainsi que dépenses aéroportuaires
et profits des seuls véhicules.

Le modèle garde une cible max-profit et une profondeur décisionnelle max-P/C. Le portefeuille
consomme la seconde pour le profit, tout en ayant plusieurs champs de capital. Un avion réellement
acheté au lieu de deux prévus exige un nouvel estimé à N=1, pas une division arbitraire par deux.
Le biais d'un facteur AIR unique peut préserver le mauvais ordre newpair/hubsite/hubhub et ne
corrige jamais les choix déjà éliminés dans le catalogue. **Catalogue en refonte : lecture et
propositions seulement, aucun changement appliqué.**

### 3.5 AIR : renfort et remplacement

Le marginal C121 compare des profondeurs, puis peut utiliser des observations historiques. Sous
V161, `OpexV161PerPlaneProfit` retourne `min(modèle, 13 000 - 2 600 × voisines - amortissement)`
et refuse si le plafond est non positif. L'exemption C70 est levée pour une valeur restée au
modèle ; la source `prior` est traitée comme non recalibrable. V161=1 est une adoption utilisateur,
son +2,7 % historique n'est pas un passage du seuil +4 %.

La régression ayant motivé V161 ne prouve pas l'effet causal d'un achat en 1970–71 : la précision
précoce est insuffisante et les renforts sont endogènes. Une moyenne observée par avion n'est pas
le marginal du prochain avion. Un remplacement doit aussi séparer revenu conservé, économie de
roulement, prix neuf et produit de vente. Aucun nouvel estimateur de remplacement n'est proposé
faute de transactions appariées. **Contrainte maintenue : ne pas remonter les renforts devant
les projets rail.** Ne pas passer à profit/opcode : le renfort, peu coûteux en commandes, y serait
structurellement favorisé.

### 3.6 Route, eau, chaînes, multi-cargo et subventions

| Opération | Modèle effectivement présent, défaut ou incertitude | Effet possible sur l'ordre |
|---|---|---|
| Bus/camion neuf | `OpexRoadLineEconomics` applique efficacité de vitesse, trajet réel si plus long, arrêt voyageurs, offre à 50 %, capacité, éventuellement chevauchement PAX ; revenu = 12 × transporté × tarif de transit ; coûts = véhicules, voies, deux arrêts, dépôt, exploitation et amortissement. | Une route existante peut être surchiffrée au prix de route neuve ; capture surestimée agit en sens inverse. Le signe net et les cargos exposés sont inconnus. Le ratio 0,121 d'un ancien corpus ne justifie pas une règle actuelle. |
| Route d'appoint/transfert | Le revenu direct du véhicule ne valorise pas le gain net apporté à la destination, ni sa cannibalisation. | Ne pas créditer au bus le billet d'avion entier. V139, V139b et V139c ont échoué ; aucune réactivation de route autonome ou de feeder proposée. |
| Eau neuve | `OpexWaterEconomics` : vitesse/2, trajet navigable, distance tarifaire entre quais, un navire, note/capacité, deux docks+dépôt ; marge 50 k£. **`tripsPerMonth=max(30/oneWayDays,1)`** surévalue la capacité théorique quand l'aller dépasse 30 jours et que la capacité lie. À 60 jours : 1 au lieu de 0,5, soit capacité ×2, pas forcément revenu ×2. | Favorise potentiellement longues traversées lentes. Exposition inconnue ; aucun diagnostic maritime lancé. La réserve `maxShipPrice` du builder est distincte du navire choisi dans le score. |
| Chaîne de transformés V88 | `OpexGoodsChainCandidates` somme profit et capital des segments amont/aval ; le financement de la seule étape 1 est un réglage distinct. | Valeur aval non encore disponible, délai d'ouverture et débit de transformation peuvent rendre l'addition optimiste. Pas d'estimateur absent, mais disponibilité conjointe non démontrée. |
| Train multi-cargo V163 | Non livré dans le SHA étudié ; un cargo dans le candidat courant. | Partager locomotive/voie peut éviter de doubler les coûts, mais répartir les wagons réduit la capacité du premier cargo. Additionner deux profits de trains complets serait faux. Exposition/valeur inconnues, chantier séparé. |
| Subvention | `OpexGenerateSubsidyCandidates` existe : garde de délai, multiplicateur limité par durée/temps de retour du capital, coût d'exploitation non multiplié. | Lissage d'une prime temporaire ≠ profit de l'année terminale ; obtention et premier transport incertains. Décomposer base/bonus et vérifier l'activation avant toute conclusion. |

### 3.7 Opcodes : coût futur, coût passé et attente

`expectedOpcodes` rail borne les itérations par `HARD_ITERATION_CAP`, multiplie par 3 105 et ajoute
les transactions. AIR/eau utilisent essentiellement les transactions restantes ; la découverte
déjà payée est distincte. `opcodeScore` est construit sur **`revenueAnnual`**, pas systématiquement
sur le profit calibré de `fundScore`. On ne peut donc pas comparer directement leurs valeurs.
Le chemin d'admission peut utiliser ce second vivier sans qu'il soit le classement final.

Mesurer coût conditionnel au stade (candidat brut, tracé prêt, réparation), succès/échec et travail
restant ; ne pas refacturer la recherche déjà exécutée. `OpexOpsMeasureEnd` peut inclure des
suspensions de commande : opcodes VM, durée de construction et fenêtres de budget ne sont pas
interchangeables. Les totaux V149 ne calibrent pas à eux seuls chaque candidat.

## 4. Propositions et statut après synchronisation

Ordre initial **qualitatif de priorité d'investigation**, sans promesse de £/an. La clôture V165
retire désormais P1 ; l'ordre courant des trois propositions restantes est P2, P3, P4.
Tous les noms de réglages
ci-dessous sont **proposés, non implémentés**, booléens à défaut 0 aux quatre difficultés.
Chaque proposition serait testée isolément sur le même arbre, autres défauts conservés, dont V161.

### P1 — Attente courte : hypothèse initiale retirée après clôture V165

**Section conservée pour traçabilité ; aucun travail ni banc à poursuivre sur cette proposition.**

**Hypothèse falsifiable.** Une partie des achats de faible valeur de 1971 retarde un projet
nettement meilleur, proche du financement et encore réalisable ; la perte due à ce retard dépasse
le gain immédiat. La seule existence d'un meilleur AIR hors budget ne suffit pas.

**Calcul proposé.** Pour le meilleur achat `j` et une alternative `b` au-dessus de lui dans la
même classe de priorité, comparer deux séquences, « j puis b » et « attendre b ». Avec flux prudent
`F>0`, `w0=max(0,(C_b-B)/F)` et `w1≈max(0,(C_b-B+C_j)/F)` donnent un premier encadrement du retard.
Inclure dans la seconde étape le flux produit par j seulement après sa mise en service ; intégrer
délais, risque d'invalidation et coûts effectivement déboursés, sans compter les marges comme
des dépenses. Une évaluation à horizon roulant fixe, à déterminer puis geler sur le corpus de
développement, compare les profits nets des deux séquences. Le profit terminal du banc reste
le juge, pas cette intégrale interne.

**Code et flag.** Nouveau helper `OpexProjectWaitValue` appelé dans `OpexProjectSelectAffordable`
et recontrôlé dans `_tryBuildProjects`, sous `score_wait_value=0`. Candidats limités à ceux déjà
générés ; pas de recherche supplémentaire de sites. État transitoire avec échéance courte,
invalidé après cash dépensé, changement de devis/site ou remplacement du candidat. Spécifier la
reconstruction au Load si un état d'attente est retenu. F=0, données absentes, site non validé ou
délai hors borne : revenir au choix courant, jamais bloquer indéfiniment.

**Différence avec territoire d'abord.** Pas de caisse réservée au prochain aéroport, pas de priorité
de mode et pas de refus systématique des non-AIR. L'achat immédiat peut gagner ; un projet rail
peut être l'alternative attendue. Une variante qui reproduit les refus territoriaux sans preuve
de valeur temporelle serait écartée comme redite. Ne pas ajouter de `Sleep()` ; différer seulement
l'achat et laisser les tâches normales travailler.

**Mesure préalable.** V165/B6 + achats datés + cash avant/après + devis contemporains : nombres
d'épisodes distincts, manque de cash, délai observé sans nouvel achat, candidat survivant, et
valeur perdue sous bornes pessimistes. Pas de cumul des mêmes refus mensuels comme occasions
indépendantes. Les logs permettent de tester le signal et sa robustesse ; ils ne fournissent pas
le contrefactuel de construction. Si F ou les dates manquent, ne pas chiffrer l'attente.

**Banc pré-enregistrable.** Protocole commun §5, exposition requise : refus temporaires réellement
levés, absence de blocage et constructions ultérieures identifiées ; suivi des dates AIR/rail et
du cash immobilisé. **Complexité élevée**, potentiel prioritaire, risque principal : faire attendre
sur des opportunités qui disparaissent.

### P2 — Un a priori de démarrage par opération, remplacé par les observations éligibles

**Hypothèse falsifiable.** En 1970–71, des erreurs différentes par opération produisent des
inversions parmi des projets **simultanément finançables et de même priorité**. Un simple biais
de niveau commun, sans inversion d'achat, ne justifie pas ce chantier.

**Code et flag.** `score_cold_prior=0` : helper `OpexScoreColdPrior` dans `projects_models.nut`,
appelé par `OpexProjectFundProfit` uniquement en absence d'observation éligible. Familles proposées :
AIR newpair/hubsite/hubhub et rail voyageurs/fret, distinction cargo seulement si le support est
suffisant. Pas de nouvelle valeur route/eau sans échantillon. R2, réalisation C121 non neutre et
V161 gardent leur provenance et leur exemption ; aucun deuxième multiplicateur sur un profit
déjà corrigé. Ne pas toucher au catalogue ou à la flotte cible.

Les facteurs seraient appris **hors jeu**, par cohortes comparables, puis figés avant les bancs ;
pas de constantes 0,37/0,87 tirées telles quelles des agrégats. Le retour au facteur de partie
doit suivre une règle de support explicite, identique après Save/Load, sans saut opportuniste
choisi après résultats. Un prior externe persisté/versionné ne doit pas être confondu avec une
observation de la partie.

**Mesure préalable.** Appariement élection→profondeur livrée→année complète, coût/maintenance et
amortissement homogènes ; validation laissée de côté par **graines entières et bundle**, jamais
par lignes d'une même partie. Comparer erreur prédictive, inversions à priorité égale et fréquence
de changement du premier achat. Les logs Top5 seuls ne couvrent pas le vivier ; résultat incomplet
si les candidats concurrents manquent. Les ratios actuels ne suffisent pas.

**Banc pré-enregistrable.** §5, avec empreinte des coefficients et séparation développement/
validation. La gate finale doit rester hors entraînement ; si les données de développement ont
déjà utilisé les graines canoniques dans le même contexte, déclarer le risque de réutilisation et
fixer un échantillon tenu à l'écart avant lancement. Exposition : achats changés en 1970–71,
pas seulement scores changés. Vérifier **aucune promotion flotte devant rail** ; si la calibration
du rail provoque ces inversions, le candidat est non recevable et doit être revu avant gel, sans
bonus rail ad hoc. **Complexité moyenne à élevée**, gain incertain : l'AIR reste souvent premier.

**Différence avec les rejets.** Pas de bonus fret, pas de régression en jeu des revenus AIR par
époque de flotte, pas de changement de paiement/concurrence ou de capital appris. Il s'agit du
repli en absence d'information, au classement final, soumis à une preuve d'inversion nouvelle.

### P3 — Séparer le tampon AIR d'abordabilité du capital durable dans le score

**Hypothèse falsifiable.** À besoin de cash identique, le tampon récupérable de 30/12/2 k£ pénalise
trop certaines lignes AIR dans le classement, comme s'il restait engagé durablement. Si K_dec
domine ou si les projets ne sont pas finançables, l'effet est nul.

**Code et flag.** `score_air_buffer_separate=0`, helper `OpexProjectScoreCapital` consommé par
les deux branches de `OpexProjectSelectAffordable` : pour AIR seulement, retirer du dénominateur
la marge explicitement identifiée, conserver capital de la **même profondeur décisionnelle** et
immobilisation. Continuer à appliquer `max(K_dec, capitalScore)`. **Ne modifier ni
`OpexProjectFinanceCapital`, ni `budgetCapital`, ni `OpexAirRequiredMargin`, ni le garde constructeur.**
Les autres modes, le rail et V161 gardent exactement leurs scores ; aucun renfort n'est promu.
Tester également les consommateurs de `lastScore` du cache et la revalidation ; ne pas supposer
qu'une modification au tri est sans effet sur l'invalidation. Si la cohérence impose une édition
du catalogue en refonte, ce candidat attendra cette intégration.

**Mesure préalable.** Sur mêmes candidats finançables et même priorité, calculer l'effet exact.
Illustration : P=100 k£, capital décisionnel=100 k£, marge=30 k£, K_dec=60 k£ : score 769→1 000 ;
le cash requis reste 130 k£. À budget 110 k£, le projet reste refusé ; à K_dec=150 k£, score 667
dans les deux cas. Tracer permutations newpair/hubsite/hubhub, pas seulement AIR contre rail.
Les dépenses temporaires de chantier doivent confirmer qu'il s'agit bien d'un tampon libéré.

**Différence avec V126/capital_quote_learning.** Aucun devis nouveau, aucune baisse de marge requise,
aucun ratio devis/réel appris, aucun changement de financement ROAD. C'est un test du **prix de
la liquidité dans le score**, sans assouplissement d'accès au cash. Il ne résout pas V165 à lui seul.

**Banc pré-enregistrable.** §5, exposition : inversions d'achats à admission identique, toutes les
gardes de cash byte-identiques ; coûts d'échec, nouvelles gares et profit à suivre. **Complexité
moyenne**, potentiel moindre que P1/P2 ; risque de survaloriser encore l'AIR surestimé.

### P4 — Calibrer C70 sur des exercices à flotte stable plutôt que diviser par N au relevé

**Hypothèse falsifiable.** Les entrées C70 ayant changé de flotte pendant l'exercice présentent
une erreur de normalisation qui modifie les facteurs et les choix à partir de 1972.

**Code et flag.** `score_c70_stable_cohort=0` : `OpexC70C82AccumulateLine`,
`OpexC70PublishModeFactors`, `OpexC70RecomputeFactors` et sérialisation de `persist.nut`.
Première variante étroite : n'ajouter une observation que si flotte et modèle sont stables pendant
tout l'exercice complet ; garder l'agrégat antérieur si aucune observation comparable n'arrive.
Ne pas transformer les mois observés en graines ni reconstituer une année par extrapolation.
Pas de nouvel apprentissage du revenu C121 ni de modification de son modèle physique.

**Mesure préalable.** Réutiliser `FLEET_PROJECT`, constructions, ventes/crashes et télémétrie
physique par IDs pour qualifier l'exercice ; même effectif en janvier/décembre ne prouve pas
l'absence de remplacement. Comparer facteurs historiques et cohorte stable, par graines,
ainsi que leurs inversions d'achat. Mesurer aussi le biais de sélection des lignes stables et
la perte de couverture ; sinon cette sélection pourrait simplement retirer les mauvaises lignes.

**Banc pré-enregistrable.** §5 + roundtrip Save/Load, prédictions brutes toujours conservées,
exposition des nouvelles observations et choix à partir de 1972. Préserver les exemptions et
la contrainte flotte/rail ; une hausse indirecte des renforts via C70 rendrait la variante non
recevable sans correction de périmètre pré-enregistrée. **Complexité élevée**, priorité basse
à horizon 3 ans car ne traite pas directement 1970–71 ; intérêt diagnostique plus fort à dix ans.

## 5. Plan commun pré-enregistrable — aucune exécution autorisée par cette étude

Le protocole concerne seulement P2–P4 ; P1 est retirée. Les propositions restantes ne sont pas
encore prêtes à lancer : P2 attend des mesures/paramètres,
P3 une exposition des inversions, P4 une couverture d'exercices stables. Compléter ces éléments
et figer une seule variante avant le premier moteur ; ne pas sélectionner le meilleur horizon
ou les meilleurs coefficients après résultats.

1. **Contrats** : OFF équivalent au comportement courant ; valeurs absentes restent inconnues ;
   provenance du profit, capital réel/décisionnel, marges, priorités C77 et égalités ; aucune
   promotion des renforts devant rail. Tests de Save/Load si état ajouté, cohérence des caches.
2. **Smoke causal** : seed42 ×1 an, deux duels, même arbre/bundle/adversaire/configuration.
   `gain_short`, seuil relatif 4 %, required-seeds40/required-years3 ; santé et exposition seulement.
   Si exposition tardive absente à un an, la gate A attend une preuve dédiée pré-enregistrée.
3. **A** : 40 graines ×3 ans ×1 répétition, 80 duels. `profit_year` terminal Opex ON−OFF,
   `gain_short`, moyenne ≥4 % de la référence, Wilcoxon exact bilatéral p<0,05, borne basse
   bootstrap95 >0 ; garde ratio des moyennes `company_value` ≥0,95. Bootstrap20 000, seed0.
4. **B seulement si A complète/saine/pass** : 20 graines ×10 ans, 40 duels, `non_erosion`,
   borne haute bootstrap95 ≥0 et même garde de valeur. Seuil 4 % enregistré mais non bloquant sous B.
5. **Budget par candidat** : contrats + smoke2 duels/2 années simulées + A80/240 + B40/400
   conditionnelle, soit au maximum **122 duels / 642 années simulées** hors diagnostic
   d'exposition et roundtrip à budgéter séparément. Une seule campagne à la fois, sans répétition
   pour chercher un résultat favorable. PC10CPU/8g/10workers, VPS3CPU/2g/3workers, swap=RAM,
   cache `openttd-lab-home`, contexte/image/montage vérifiés au moment d'un futur lancement.

Pré-enregistrer SHA, diff, manifeste/bundle, coefficient/version, bras explicites
`OpexAI[<flag>=0]` / `OpexAI[<flag>=1]`, graines, fenêtres, budget et critères d'arrêt.
Diagnostic avec `decision_log=1` identique aux deux bras ; sondes OFF aux gates économiques sauf
besoin justifié et gelé avant mesure. Les quatre flags ne doivent pas être cumulés dans une gate
censée qualifier chacun. `comparison_complete`, `metric_coverage_complete`,
`adoption_sample_complete`, horizon et quatre trimestres valides sont obligatoires sous A/B.
Un 5×3 ou une baisse d'erreur de modèle ne remplace aucune gate. Aucun changement de défaut
après une simple évaluation, même si les deux gates passent.

## 6. Mesures manquantes et point d'arrêt

| Priorité | Mesure à obtenir | Décision qu'elle permet |
|---|---|---|
| Historique, clos | Bundle/manifeste/logs V149/V165 non présents localement | Limite de provenance conservée ; aucun nouveau dépouillement des seuils ni test de P1 après clôture V165 |
| 1 | Chaîne graine/bras/company/date/clé projet/lineId/StationID/cargo/moteur/N entre choix, achat et exercice complet | Comparer les mêmes objets ; distinguer sous-livraison, cannibalisation et défaut d'estimation |
| 1 | Classe C77, score appliqué, facteur/provenance, K_dec et deux capitaux au choix | Quantifier les inversions utiles à P2/P3, au lieu d'une amélioration de valeurs jamais choisies |
| 2 | Capital rail ventilé voie/quais/ponts/dépôt/rame/seconde voie, pre/test-mode/réel, succès et échecs | Localiser le biais sans réintroduire terrain170 ni apprentissage du capital rejeté |
| 2 | Rail PAX/fret par cargo, temps de charge/retour et revenu à flotte constante | Tester capture/cadence et rendre comparables 0,87 vs anciennes cohortes |
| 2 | AIR : départs, volumes transportés par sens/cargo, paiement, occupation de piste, pertes des voisines | Attribuer la sur-prévision à une composante ; transmettre au chantier catalogue, sans le modifier |
| 2 | Transactions rail d'expansion et exercices à flotte stable, crashes/remplacements compris | Évaluer les marges réelles et P4 sans réactiver V107 |
| 3 | Coût VM restant par stade et succès/échec, distinct des ticks d'attente | Juger l'intérêt d'un estimateur de coût ; aucune proposition `simple_opcode` |
| 3 | Exposition route/eau/chaînes/subventions aux défauts, puis coût et profit réseau | Éviter de calibrer des opérations absentes ; aucun nouveau diagnostic maritime sans décision |

Ne pas proposer de requalification automatique de V149, de bonus fret, de seuils PAX/fret,
de budget A*, de rail `simple_roi/simple_opcode`, de territoire d'abord, de V126 à marge réduite,
de capital appris ou de feeders. Le défaut V161 reste acquis par décision utilisateur.
**Étude livrée ; aucune proposition implémentée ni qualifiée.** P1 et le fil des seuils V165
restent clos. La prochaine preuve utile pour P2 est un appariement des estimés aux exercices
réalisés comparables, puis l'exposition d'inversions entre candidats simultanément finançables.
La refonte du catalogue AIR reste hors de cette intervention.
