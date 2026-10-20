# V278 — sites AIR paresseux, 20 octobre 2026

Prototype sur `v278`, base `9b9e3b3002e7ba2b37b47571ce821d09cfaed021`.
Réglage entier `v278_air_lazy_sites`, bornes 0..1, **défaut 0 aux quatre difficultés**.
Demande utilisateur : implémentation, contrats, contrôles statiques et commit ;
**aucun moteur, banc, Docker ou push**. Aucune qualification ni économie d'opcodes
mesurée sur ce prototype. Le master local a avancé documentairement pendant le
travail ; ses trois modules AIR concernés sont identiques à la base.

## Constat fourni

Profil par spans, graine 42, un an, `probes=2,probe_span_trace=1` :

| Carte | `air.sites` | `air.prepare` | Paires et autres coûts |
|---|---:|---:|---|
| 1024² | 9,6 M, 428 tranches | 2,2 M | 2,25 M pour 70 paires évaluées |
| 256² | 2,0 M | non fourni | `air.hub_site` 2,4 M ; `air.new_pairs` 7,3 M, dont `air.pair` 4,9 M |

Il s'agit des mesures transmises dans la demande, sans artefact audité dans cette
tâche. `OpexAirTownPoolLimit` fournit 256 villes à 1024² et 64 à 256².
Le pipeline historique cherche tous leurs sites, puis revalide leur rang avant
la première paire. En reprise, `NewPairs` revalide encore ses extrémités.

## Conception

`air_lazy_sites.nut` est chargé après `air_planning.nut`. À 1, seuls les scans
reprenables non ciblés empruntent la nouvelle frontière. Les courses/réparations
C83, les scans ciblés et les appels synchrones gardent leur parcours de paires.
Le cache de préparation et la déduplication au tick s'appliquent également aux
appels qui passent dans les fonctions communes lorsque le réglage vaut 1.

Le vivier reste exactement celui choisi par Prepare et sa limite spatiale.
Dans chaque combo, on copie les villes retenues et leurs populations, puis on les
ordonne par population décroissante, avec égalités stables. Le potentiel choisi
est **popA × popB**, calculé en flottant avant multiplication. La population est
l'heuristique demandée, disponible sans géométrie ; ce produit donne un ordre
monotone de partenaires par ligne de la matrice triangulaire. La distance reste
un filtre et une entrée de l'économie réelle. Le produit n'est ni une borne du
profit ni une promesse de meilleure paire économique. Nous ne revendiquons pas
un ordre `popA × popB × √d`.

Un tas maximal fusionne les lignes `(a, b>a)`. Il contient au plus n−1 entrées,
contre n(n−1)/2 si toutes les paires étaient matérialisées. Après dépilement de
`(a,b)`, seul `(a,b+1)` est inséré : toutes les paires restent accessibles, une
seule fois, dans l'ordre décroissant du potentiel, avec départage par indices.
L'initialisation et l'ordonnancement ne demandent aucun site.

On cherche d'abord les sites des huit premières villes. Avant de dépiler une
paire dont une extrémité est hors lot, le lot est étendu jusqu'au multiple de huit
qui inclut cette extrémité. **Aucune paire de moindre potentiel ne devance ce
sommet pendant une extension.** Un site absent élimine seulement les paires qui
l'utilisent. À la fin, toutes les villes sont visitées, même sans paire, afin de
fournir les sites aux bras hub→site. Il n'y a aucun plafond nouveau de villes ou
de paires. Les combos et leur règle d'arrêt historique restent inchangés.

Chaque extension appelle le vrai `OpexAirPlansFindSites`, avec `scanEnd` réduit et
la limite complète conservée. Les filtres C83/V133/V134, les couronnes C96, les
budgets et le classement physique restent communs. **Le même objet de sondage
est conservé pour tout le combo** : son crédit n'est pas réinitialisé par lot,
et `townsLeft = limit - i` conserve le partage global historique. Chaque paire
disposant de deux sites valides appelle le vrai `OpexAirPlansNewPairs` sur ces
deux sites. Les panneaux AX/AY/AV de première paire sont désarmés sur ces appels
atomiques pour éviter de les reconstruire à chaque paire.

## Validité : preuve au tick, pas au mois

Le mémo V278 est distinct d'AIR0310. Sa clé inclut type d'aéroport, ancre, ville
commerciale et slot C83 requis. Il ne couvre que les sites neufs ; la validité
des hubs réutilisés conserve son chemin existant.

Une recherche `FindSite` réussie prouve déjà nearest-town, footprint et le test
BuildAirport ou son repli de terrassement. Après ajout des métadonnées C83, on
complète les gardes de recovery et de slot. Cette preuve permet d'éviter une
revalidation de rang **si la recherche entière reste dans le même tick**.
Sinon `StillBuildable` est rejoué. La revalidation de paire partage ce même mémo.
Une réponse de `StillBuildable` n'est mémorisée que si le tick initial est encore
courant à la fin ; un prédicat qui suspend automatiquement n'empoisonne pas le
mémo du tick suivant. Les villes au plafond restent filtrées avant le mémo.

`OpexAir0310InvalidateSiteValidity` invalide aussi V278 : les crochets existants
des constructions/démolitions AIR, rail, route, eau, recovery et suppressions de
lignes sont donc conservés. `OpexAirResetSiteCache`, **même avec false**, et
`OpexAirInvalidateCachedSite` invalident V278 également. Le mémo est global,
transitoire, et ne conserve aucune preuve au-delà de son tick. Les concurrents
peuvent changer la carte entre ticks : on ne réutilise alors pas leur ancienne
géométrie. Aucun changement de cache n'est exécuté lorsque V278 vaut 0.

V157 avait trouvé **66 écarts sur 35 004** avec le cache mensuel AIR0310, puis
encore **26 sur 39 471** avec une validité limitée à un appel pouvant durer
environ 40 ticks (`docs/taches.md`, section V157). Ni le mois ni l'appel ni le
scan ne sont donc une durée de preuve acceptable ici. V278 évite ces deux
durées ; son exactitude moteur reste à vérifier, notamment aux suspensions.

## Préparation et entrées vivantes

Prepare possède un cache dans `resumeState.v278Prepare`. Les villes, combos,
limite, signal C83, diagnostic servi et génération annuelle étaient déjà figés
par le scan historique. Le cache évite leur réaffectation et les multiples tests
d'initialisation à chaque tranche. Il relit les compteurs, `bestPlan`, le combo
courant et les pointeurs de mémos C121 depuis le vrai curseur.

Les lignes **peuvent changer** entre tranches, car C78 publie progressivement et
des chantiers peuvent démarrer. L'index hub n'est donc pas figé aveuglément : une
signature exacte de toutes les extrémités AIR, l'époque d'invalidation et le tick
gardent sa réutilisation. Il est reconstruit à un nouveau tick, même à signature
inchangée, pour reconsulter les StationID et leur validité. Ce coût reste à
mesurer ; la totalité des 2,2 M n'est pas promise comme économisée.

Le réglage moteur de maintenance est relu. Le renouvellement mensuel des mémos
de prix/économie reste **avant** le retour rapide de Prepare. Un catalogue
différent force la préparation commune ; aucune entrée économique mensuelle
n'est gelée pendant tout le scan.

## Reprise, publication et sauvegarde

`resumeState.v278Lazy` conserve tas, sites accumulés, correspondance ville→site,
lot couvert, lot demandé, sondage global et sous-curseur `scanIndex/rankIndex`.
Un yield de recherche ne dépile pas la paire en attente. Une paire dépilée est
traitée atomiquement, comme la garantie historique d'au moins une paire par
appel ; la tranche suivante poursuit le tas. La phase hub ne commence qu'une
fois toutes les paires terminées ; `pairsDone` empêche leur rejeu après un yield
de hub. La fin de combo libère l'état paresseux, la fin de scan libère Prepare.

`scheduler_tasks.nut` continue de publier le même tableau `s.plans`, via
`partialPending` au passage suivant. Ni `projects_update.nut`, ni la boucle
principale, ni son double profilé ne changent. La publication progressive verra
des plans plus tôt et dans un autre ordre.

Le curseur C78 n'est pas sérialisé par `persist.nut` : seules les échéances des
tâches le sont. V278 ne change pas ce contrat. Au Load, le scan et les mémos sont
recréés, et `_c76ForceReloadRegen = true` force la reconstruction habituelle.
Pas de nouvelle clé Save/Load, ni de référence de contexte persistée. Les
simulations Python de reprise ne remplacent pas un roundtrip moteur.

## Équivalence et changements de trajectoire

À **0**, mêmes fonctions historiques, filtres, économie, reprise et publication
qu'à la base ; aucune recherche paresseuse ni mémo V278 n'est appelé. Les tests
figent l'intégralité du driver et de NewPairs (hors garde de panneaux V278).
L'ajout des gardes et du chargement du réglage consomme néanmoins des opcodes :
ce n'est pas une identité de trajectoire au bit près face à un autre binaire.

À **1**, l'ensemble théorique des paires du vivier et l'évaluation C121 sont
conservés sur des entrées immuables, mais **pas leur ordre ni leur calendrier**.
La copie des populations, le tri après sélection du vivier, le partage du budget
de sondage dans ce nouvel ordre, les sites pris ou perdus pendant un scan et les
publications/constructions anticipées peuvent modifier les sites et décisions.
Il n'y a donc pas de preuve de neutralité économique sans moteur.

## Validation et mesures restantes

- Base : **2 090 tests**, 3 ignorés, 3 échecs attendus, aucun échec inattendu.
- V278 : **16 contrats/simulations** (tas jusqu'à 256 villes, égalités, grandes
  populations, sites absents, extension prioritaire et reprise entre opérations).
- Suite complète : **2 106 tests**, 3 ignorés et 3 échecs attendus, aucun nouvel
  échec inattendu (base : 2 090 tests, mêmes ignorés et échecs attendus).
- `undecl.py` : diagnostics préexistants `AICONFIG_BOOLEAN`, `CONFIG_BOOLEAN` ;
  aucun ajout. `delim.py` : aucun diagnostic. `git diff --check` requis.
- Aucun test Python ne compile Squirrel ; compilation, Save/Load et performances
  ne sont pas validés dans cette tâche, conformément à la demande sans moteur.

Mesures à faire ultérieurement, **sans lancement dans cette tâche** : deux
comparaisons 0/1, graine 42, un an, départ 1970, mêmes paramètres et runtime,
cartes **1024² et 256²**, `probes=2,probe_span_trace=1` identiques dans les deux
bras, arbres et sorties figés sous noms neufs. Relever coût total AIR et coût
par tranche, `air.sites`, `air.prepare`, `air.new_pairs`, `air.pair`, `air.hub_site`,
nombre de paires réellement évaluées, date de première paire et publication,
santé et horizon. Les extensions émettent `air.sites` sous `air.new_pairs` :
spans inclusifs, **ne pas additionner ces coûts**. Le premier lot n'émet qu'un
span sites, sans double comptage imbriqué de ce même nom.

Comparer aussi les potentiels et raisons de rejet des paires, la qualité C121
des plans admis et les compteurs globaux, pour distinguer économie de géométrie,
surcoût de la frontière et simple déplacement du travail. Tester une sauvegarde
pendant une extension puis pendant la phase hub. Le smoke de compilation et ces
profils restent préalables à toute qualification économique ou adoption ; le
défaut reste 0.

## V278b — correctif des états de reprise

Base du correctif : `e2c00592f4c1fcc53671f7eb3e2e0f4780778c2b`, branche
`v278`, arbre initial propre. L'utilisateur rapporte un plantage moteur
`bestPlan` absent lors du checkpoint de FindSites le 17/01/1970, graine 42,
cartes 1024² et 256², `probes=2,probe_span_trace=1,v278_air_lazy_sites=1`.
Cette mesure est fournie ; aucune partie n'est exécutée ici.

Audit par recherche des accès `resumeState.<clé>` et des affectations `=` :

- FindSites utilise `combo`, `scanIndex`, `scanSites`, `scanProbes`, `rankIndex`,
  `rankSites`, `sites`, `a`, `b`, `bestPlan`, `stationLimitedTowns`,
  `perfOpsSites`, `perfOpsEval`, `perfProbesCount`, `perfCheapSkip`,
  `perfSitesFound`, `totalOps` (ce dernier en `+=`). Toutes ces clés sont
  maintenant initialisées dans `lazy.scan`, y compris les sept manquantes.
  `bestPlan`, la table des villes limitées et les compteurs reprennent le
  contexte courant : null/table vide/zéros au départ comme Prepare, résultats
  cumulés pour les lots étendus. Les curseurs restent propres au lot et le
  sondage est partagé pour tout le combo.
- NewPairs utilise un sous-ensemble des mêmes clés. Son appel V278 est atomique,
  `sliced=false`, `resumingCombo=false`, `resumeState=null` : toutes les lectures
  et écritures de ce dernier sont court-circuitées. Aucun autre état de travail
  n'est passé à Prepare ; l'état extérieur est initialisé par Prepare avant
  création de `v278Prepare`/`v278Lazy` et avant les checkpoints V278.
- Prepare initialise également `done`, `startTick`, `towns`, `combos`,
  `townLimit`, `c83TopTownIds`, les deux mémos C121 ; `c78Year` et `c78Gen`
  sont créés ensemble, `servedDiag` est gardé par `in`. Les marqueurs de cache
  sont créés avec `<-`. Le retour rapide `v278Prepare` lit donc un état déjà
  préparé, jamais `lazy.scan`.
- Tous les champs de contexte lus directement par FindSites/NewPairs sont
  déclarés dans le contexte du driver, puis copiés par `rawset`. `v278ScanEnd`
  est ajouté avant FindSites et lu sous garde. Les tableaux/tables partagés
  (notamment `projects`, `stationLimitedTowns`, `servedDiag`) gardent leurs
  mutations ; `sites` est fusionné dans `lazy.sites`, jamais remplacé par les
  deux extrémités atomiques. `bestPlan` et les cinq compteurs sont explicitement
  recopiés après les deux appels, avant un éventuel retour false. Le helper
  V133 peut créer `v133Skip` : cette table est aussi remontée sous garde.
  Le chemin C83 Repair est exclu par LazyEnabled et absent de `lazy.scan`.
- Chaque champ `lazy.*` est créé par LazyState, `scan` est testé contre null
  avant création/réemploi, puis libéré uniquement à la fin du lot.
  `v278ExtendingPairs` est créé avec `<-` et testé avec `in` ; `v278Lazy`
  est créé avant LazyPairs et supprimé à la fin du combo. `v278Prepare` est
  créé après préparation complète ; ses champs de mémo sont initialisés
  ensemble et vérifiés avant restauration. Aucun nouvel état Save/Load.

Trois contrats supplémentaires vérifient tous les accès du sous-curseur,
les entrées/sorties des copies de contexte, puis rejouent les affectations des
deux checkpoints réels avec refus d'écrire une clé absente. La simulation
conserve un gagnant antérieur à l'extension et le même objet de sondage entre
les suspensions de scan et de classement. Elle ne compile pas Squirrel et ne
simule pas la géométrie moteur. Les 19 tests V278 passent ; suite complète :
2 109 tests, 3 ignorés, 3 échecs attendus, aucun échec inattendu. `undecl.py` :
seulement les diagnostics préexistants `AICONFIG_BOOLEAN`, `CONFIG_BOOLEAN` ;
`delim.py` et `git diff --check` sans diagnostic. Défaut toujours 0.
