# RAIL-REPAIR-ASTAR / RAIL-REPAIR-POSE — intervention isolee du 30/10/2026

**Point de depart :** branche `feat/rail-repair-astar-pose-20261030`,
`729eafb8` (ESTIM31, EB14=3). **Verdict : prototypes prequalificatifs,
aucun GO** : tests de contrats hotes uniquement, Docker interdit au worker.
Deux reglages publics independants a 0 sur les quatre difficultes :
`rail_repair_astar_pair=1`, `rail_repair_pose_order=1`.

## ASTAR : une paire de quais differente, et un seul nouveau A*

L'ancienne recherche primaire segmentee/multisource est conservee. Sur un
premier resultat `ABND` ou `NOPA`, et seulement si le profit annuel prevu
est positif, une selection bornée parcourt jusqu'a **8 plans par extremite**
issus du prefiltre actuel `OpexRailPlatformPlans`. Elle refuse la paire
initiale, les ports sans vraie tuile, les approches qui ne changent pas de
2 tuiles ou s'ecartent de plus de 12, et les distances superieures a
`distance(initiale) + 12`.

Une seule nouvelle recherche avec **une source et un but directionnels** est
creee, budget `min(900, budget primaire / 4)` iterations (refus si <250),
fenetre de ticks `RAIL_SEARCH_SAFETY_TICKS` et reprise par les tranches C80.
On ne relance ni les anciennes recherches V307 inverse/guidees, ni le meme
grand ensemble de quais avec un simple budget augmente. Le pathfinder
secondaire conserve le cargo, le sens de transport, les tuiles ignorees et
la configuration locomotive ; le plan final est examine et revalorise par
`OpexCompleteRailRouteAfterSearch` comme tout chemin classique.

`astarRepairTried` est limite au travail `_railSearch` en cours : **un
seul essai** apres un echec primaire. Le resultat final additionne les
iterations de l'A* primaire et du second, et les opcodes de chaque tranche
sont imputes au budget `build_search` existant. `RAIL_ASTAR_REPAIR`
trace `start/end`, l'OD, les ancres, le motif initial, le resultat et
le cout de recherche complementaire. `RAIL_BUILD`/`RAIL_ATTEMPT`
recevront `astar_repair=1` seulement si le second A* a produit une route.

L'etat `_railSearch` (pathfinder C++ non serialisable) n'est deja jamais
sauvegarde : `persist.nut` signale `railSearchPending`, annule le worker
et invalide le portefeuille lors du Load. Le nouvel essai partage ce
contrat. Un echec final `ABND/NOPA` invoque deja `_markPairAbandoned` via
`_recordRailAttempt` ; la table `_abandonedPairs` est sauvegardee et soumise
au cooldown OD existant. Ainsi la meme OD n'est pas essayee en boucle dans
la meme fenetre ou apres Load. Tester Save/Load *pendant le second A-star*
au moteur.

**Limites :** sur un vrai NOPA d'un A* complet qui a epuise toutes les
possibilites physiques, restreindre les quais ne peut pas creer une voie.
Sur ABND, une recherche plus focalisee peut trouver un trajet avant la
limite d'iterations, mais aucun cas de construction nouvelle n'a ete mesure.
Les échecs `SITEA/B/AB`, les nouvelles emprises et les chemins sans sites
alternatifs sont hors de ce contrat (item RAIL-REPAIR-SITE distinct).

## POSE : inversion de deux commandes consecutives sous garde d'emprise

`OpexRailRepairPoseVirgin` verifie **avant toute pose de gare** que chaque
tuile interieure du trajet est valide, unique, sans rail/gare/depot deja
construit, et sans pont ou tunnel existant. Les chantiers utilisant une voie
double et les variantes V233L sont exclus. Le repli intervient uniquement
sur un `AIRail.BuildRail` ordinaire refuse au milieu d'une pose neuve,
une seule fois et jamais avec `V199_ROBUST_BUILD`.

Si `prev,cur,next,after` sont quatre cases contigues, que `cur` et `next`
sont vierges/constructibles, le constructeur tente `BuildRail(cur,next,after)`
avant `BuildRail(prev,cur,next)` et verifie les connexions. Un succes saute
uniquement la commande `i+1` deja posée. Un refus arrete immediatement la
construction : la routine appelante appelle son `OpexRollback` habituel
sur les stations et **toutes** les tuiles du trajet, dont celle posée
en avance. Aucun train n'est achete avant validation des voies et du depot ;
les comptages C63 `actualCost` continuent de reposer sur `AIAccounting`
sans pretendre qu'une depense annulee est nulle.

L'inversion vise **un defaut d'ordre de pose**, et non un obstacle qui
requerrait terrassement, demolition concurrente, pont, tunnel ou aiguillage
sur une voie active. Elle s'arrete sans tentatives ulterieures si la premiere
inversion ne marche pas. Le log `RAIL_POSE_REPAIR idx tile first_err ok`
identifie la commande et la tuile. `RAIL_BUILD`/`RAIL_ATTEMPT`
ajoutent `pose_repair=1` pour les lignes passées par cette alternative.

**STNFAIL** : les nouveaux quais ne sont pas poses par cette variante.
Un retour `STNFAIL` en phase de construction utilise le diagnostic
`RAIL_STN_FAIL` et le rollback historiques. Reprendre une jonction doit
selectionner et tester une nouvelle paire gare+voie **avant tout paiement**,
avec preuve de conservation du StationID sur les quais partages ; c'est
le mecanisme distinct SITE. Ne pas tenter une pose sur un StationID invalide.

**LOOPFAIL** : la boucle et le depot d'une seconde voie sont controles
apres une construction a plusieurs phases et avant engagement des trains.
On n'inverse aucune commande au milieu de ce processus car le rollback
peut aussi toucher les quais de la voie principale et les vehicules deja
achetes. Tache technique explicite : un journal de transaction par objet
(rail / pont / tunnel / quai / depot / vehicule avec ownership initial),
reconciliation apres Save/Load, et un test physique de conservation de la
premiere voie apres echec `LOOPFAIL` ; ensuite seulement une reprise locale.

## Protocole à exécuter au moteur par le prime

1. Avec les nouveaux settings OFF : smoke 1×1, aucune erreur de compilation ;
   examiner les logs par comparaison au temoin et la santé du jeu. Puis ON
   separement et en cumul, avec `probes=2` et instrumentation decision.
2. Cibler des mondes où il y a `ABND`, `NOPA` et `TRKFAIL` : pour ASTAR,
   comparer les OD `(seed,kind,cargo,src,dst)` avant/après et verifier
   `RAIL_ASTAR_REPAIR action=end result=OK` suivi d'un vrai `RAIL_BUILD` ;
   pour POSE, exiger `RAIL_POSE_REPAIR ok=1`, `RAIL_BUILD`, profit positif,
   absence de quai/depot/voie/train orphelin et caisse correcte. Inclure
   un Save/Load pendant un A* secondaire et pendant un chantier inacheve
   si le moteur peut effectuer ce checkpoint.
3. Exposition appariée 5 graines × 5 ans ; arret **NO_GO_NON_EXPOSE** si
   aucune OD supplementaire rentable ou si le rollback n'est pas sur.
   Sinon, pre-enregistrer les graines/seuils et lancer la porte A 40×5
   multimodale, puis B 20×10 seulement si A passe. Aucun default change
   sans qualification economique. Garder intacts les anciens verdicts
   V307 inverse/V303/V304, V199, V233L et V131c.

## Verification statique hôte

`sweeps/test_rail_repair_astar_pose_20261030.py` teste les deux settings,
les bornes A*, la contabilite cumulee, la tentative de pose unique, le
prefiltre de tuiles vierges, le rollback et la reconciliation Save/Load.
Tests V131 et geometrie rail sont egalement executables sans moteur.
Les vieux `test_v233_long_good` etaient deja incompatibles avec la base
`729eafb8` : ils attendent 83 reglages alors que `git show HEAD:info.nut`
en compte deja 85, et des empreintes de projection historiques.

**Non realises :** compilation Squirrel, essai moteur reel, Save/Load reel,
preuve d'OD reprise rentable, verification des debrits en carte et portes
economiques. Les deux items restent **ouverts**.

**Mise à jour de l'intégration :** un premier smoke a découvert une
erreur de slot `astarRepairTried` absent dans le chemin stock C121.
Après correctif et test de ses deux initialisations, le smoke moteur,
la comparaison OFF/ON 1×1 et le Save/Load réel passent. Le 5×5 combiné
est sain mais non significatif. Les preuves par OD, l'absence de débris
sur cartes exposées et les réparations `STNFAIL/LOOPFAIL` restent en suspens.
Voir [rapport commun](rail_repairs_integration_validation_20261030.md).
