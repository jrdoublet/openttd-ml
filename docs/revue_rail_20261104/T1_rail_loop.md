# T1 — Revue RAIL-LOOP du 4 novembre 2026

RAIL-LOOP peut partager une ligne avec une transaction V284 en cours ; les journaux le prouvent.
Les champs `railLoop*` sont sauvegardés, mais les constructions et les clones interrompus ne le sont pas complètement.
L'armement repris n'est pas idempotent : des signaux existants sont ignorés et de nouveaux peuvent être posés trop près.
Les 56 échecs du 20×10 se décomposent notamment en 31 plafonds A*, 17 absences de chemin et 4 abandons après pose.
Revue et preuves livrées sans correction Squirrel, changement de défaut ni nouvelle partie ; les gains correctifs restent à mesurer.

## Périmètre et provenance

Référence revue : **`fbc0f100bbf87462b6231ce256b2f5e3ac27d84f`**, parent `a8cfb1e8`,
sur `ccr-6d627d08-tlnphk`. Livraison : `cloud/revue-rail-T1-20261104`.
Les numéros de ligne ci-dessous désignent cette référence, inchangée par la revue.
Le `master` local `99f29d9c` et ses modifications parallèles n'ont pas servi de référence.

Lecture complète de `rail_loop.nut:1-698`, puis lecture ciblée du câblage, de la
projection et réconciliation Save/Load, des helpers demandés, des sélecteurs et transactions
V284/V257/RAIL-LONG/INVEST-STALL, de C41 et du ferraillage. Les autres lots restent hors périmètre.
Les [consignes T1](../cloud_revue_rail_20261104.md) permettent, sans les imposer,
de petites corrections certaines. Les défauts retenus demandent ici des contrats
transactionnels et des essais de reprise/occupation ; aucun correctif n'a été appliqué.

Les CSV du `cloud_pack_20261104` de cette référence ne contiennent pas les événements
RLOOP. Dépouillement des **journaux moteur existants**, sans rejeu, dans
`.wt_rail_loop_20261104/results/` :

- `rail_loop_fix1_smoke_4x6_20261104_engine/rail_loop_*.log` : 4 fichiers ON ;
- `rail_loop_non_erosion_rail_20x10_20261104_engine/rail_loop_*.log` : 20 fichiers ON.

Les [preuves archivées](../../evidence/review/revue_rail_t1_20261104/index.json)
contiennent les manifestes, tous les événements RLOOP/V284 extraits avec fichier et
numéro de ligne, leurs empreintes, celles des 24 logs sources et les sorties de tests.
Un événement répété est compté comme une nouvelle tentative, pas comme une nouvelle ligne.
Les hashes des manifestes correspondent aux JSON finaux ; leurs hashes de bundle concordent.
Le module gelé est identique à celui relu après normalisation CRLF/LF,
SHA-256 brut `66a043a74f0b8f98ff97cbd861c568d120d58480251323bfb39cbfe9d17dbad2`.
Le bundle historique du 20×10 est `7af015bfd379f3a2ae945e0e0ecb7057ed935240ce18c982083603e023e696e6` :
SHA Git `07e2d389` **sale**, avec le correctif local de `rail_loop.nut`. Cela ne rend
pas les deux arbres entiers identiques, notamment leurs défauts.

## Constats, par bénéfice correctif attendu

Le classement est qualitatif : aucun gain monétaire causal n'a été mesuré pour ces corrections.
**(a)** certain dans le code/les traces ; **(b)** probable ; **(c)** à vérifier en moteur.

| ID | Classe / gravité | Emplacement principal | Défaut et correction proposée | Gain attendu |
|---|---|---|---|---|
| T1-01 | (a), robustesse / perte de profit | `task_rail.nut:631-640`, `rail_loop.nut:593-622`, `task_v284.nut:115-140` | Pas d'exclusion réciproque RAIL-LOOP/V284 ; réserver la ligne et respecter les transactions déjà engagées | Éviter remplacement, détournement ou seconde rame pendant conversion |
| T1-02 | (a), robustesse / perte de profit | `rail_loop.nut:395-424,580-583` | Voie 2 non journalisée avant dépense ; persister intention, trace et progression avant commandes | Reprendre/nettoyer un chantier après Load, sans rails oubliés |
| T1-03 | (a), robustesse / perte de profit | `rail_loop.nut:495-505`, `persist.nut:955-961` | Clone créé/démarré avant son inscription persistante ; journaliser l'achat et réconcilier le dépôt | Éviter rame orpheline, achats répétés et dépassement réel du plafond |
| T1-04 | (a), robustesse, blocage possible | `rail_loop.nut:463-481,571-576`, `v190_fix_directional.nut:189-190` | Reprise d'armement non idempotente ; reconnaître les PBS attendus et vérifier la topologie | Conserver espacement, compte des cantons et possibilité de reprise |
| T1-05 | (a) pour l'abandon ; (b) pour sa cause transitoire, perte de profit | `rail_loop.nut:280-288,679-691` | Après pose, un seul refus d'armement gèle l'investissement pour 100×365 jours ; conserver une reprise contrôlée | Récupérer des voies de retour déjà payées, 4 cas observés au 20×10 |
| T1-06 | (a) pour l'absence de contrôle ; conséquence physique (c), robustesse | `rail_loop.nut:313-324,411-415,670-671` | Démolition sans contrôle de réussite, puis `kept_track2=0` inconditionnel ; retrait journalisé avec résidus | Éviter orphelins non suivis et retrait partiel d'un raccord accessible |
| T1-07 | (c), blocage / perte de profit possible | `rail_loop.nut:154-155,465-475` | Le PBS facultatif ne démontre pas l'absence de contre-sens local dépôt→gare ; vérifier les itinéraires physiques | Sécuriser la croissance sans interblocage de gorge |

### T1-01 — Deux propriétaires de la même ligne

`OpexRailLoopSelect` lance `Begin` puis retourne **false** (`621-622`). La même
passe de `_expandRailLines` peut donc atteindre V284. Le sélecteur V284 rejette
les doubles voies et les rames multiples, mais pas `railLoop=1` ; la conversion
reste à `doubleTrack=0` et une rame. Réciproquement, l'admission RAIL-LOOP ne
teste ni `OpexV284Busy`, ni `_v257Pending`, ni la réservation propre à la ligne.

**Preuve directe**, 20×10, `rail_loop_seed160569_r0.log` :

| Ligne du log | Date jeu | Événement ligne 35 |
|---|---|---|
| 45064 | 1978-05-05 | `RLOOP phase=search`, une rame |
| 45232 | 1978-06-11 | `V284 action=pick kind=wagon` |
| 45237 | 1978-06-25 | `RLOOP phase=track2`, coût simulé 48 155 |
| 45240 | 1978-06-26 | `V284 action=done`, véhicule 197→894, capacité 50→75 |
| 45493 | 1978-07-06 | `RLOOP phase=commit`, deuxième rame 432 |

Trois `V284 pick` et deux `V284 done` apparaissent entre `search` et
`commit/fail` dans le 20×10 ; ce sont des événements, pas cinq conflits indépendants.
La graine 324874 montre également un `done` d'une transaction commencée auparavant.
Le chevauchement est certain ; ces traces ne prouvent pas qu'il cause une perte
de profit, et le premier exemple finit par réussir.

**Correction** : réservation par `lineId`, admission refusée si une autre
transaction possède cette ligne, vérification réciproque au choix et au commit.
Étendre le contrat à RAIL-LONG et INVEST-STALL : leurs gardes
`task_rail_long_v2.nut:121-176`, `rail_long_v3_upgrade.nut:136-144` et
`invest_stall_fleet.nut:142-154` ne reconnaissent pas RAIL-LOOP. Ils sont OFF au
défaut ; leur coactivation n'est pas une exposition prouvée ici.

**Évolution postérieure vérifiée** : `80df60e9`, après `71ea4c44`, ajoute
`if (RAIL_FILL && ... line.railLoop == 1) continue` dans V284. Cette garde
conditionnée par `rail_fill` ne traite ni le chemin historique, ni une
transaction déjà ouverte. Ne pas la présenter comme absente de la branche actuelle,
ni comme la résolution complète du problème.

### T1-02 — Save pendant la pose oublie les rails déjà posés

Scénario : sauvegarder après une commande de la boucle `395-401`, avant les
`rawset` de `421-423`, puis recharger. La carte conserve les rails, mais la ligne
n'a que `railLoop=1`, sans trace `railLoopTrack2` ; `_railLoopState` est transitoire.
La reprise `580-583` classe donc cette pose comme une **recherche perdue**,
programme un nouvel essai à 30 jours et ne connaît pas les objets à récupérer.
Si un raccord a déjà été posé, `back_lead` peut ensuite refuser cette ligne.

Ce scénario est permis par le contrat
[Save d'OpenTTD 15.3](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_controller.hpp#L59-L95) :
la sauvegarde est indépendante de l'activité du script et ne conserve que sa table retournée.
Le code V257 connaît déjà ce risque (`task_v257.nut:549-557`) et journalise
le dépôt avant ses commandes. Aucun Save/Load ciblé n'est exécuté dans cette revue.

**Correction** : persister avant la première dépense une transaction sérialisable
(plans, trace, ouvrages, type rail, phase, éléments possédés et progression).
À la reprise, vérifier chaque élément effectivement présent ; ne pas simplement
publier `railLoopTrack2` avant la pose, car le chargeur actuel le prendrait pour
une voie complète. Complexité élevée, coordination avec T6.

### T1-03 — Save pendant le clonage oublie une rame achetée

`CloneVehicle` (`495`) et `StartStopVehicle` (`497`) précèdent
`line.vehicles.append(train)` (`501`). Un Load entre ces commandes et l'adoption
retrouve une rame physique sans identifiant dans la ligne. La réconciliation
`persist.nut:955-961` filtre seulement les identifiants déjà connus ;
`lines.nut:105` continue ensuite à retourner cette liste pour le rail.

Conséquences selon l'instant : rame arrêtée payée et inutilisée, ou rame active
absente du compte qui limite la croissance. Le refroidissement `railLoopNextGrow`
est lui aussi posé après l'achat. **Correction** : intention d'achat persistante,
inventaire initial du dépôt, adoption/rollback idempotents et délai enregistré
avec l'adoption. Ne pas réconcilier toutes les rames d'un StationID partagé.

### T1-04 — Les PBS existants ne sont pas reconnus à la reprise

Scénario : Save pendant l'armement, après un ou plusieurs `BuildSignal`, avant
`Commit`. Au Load, `571-576` repart en `arm` avec seulement `railLoopPbs2`.
`OpexV190Fix2PlaceSignal` refuse toute tuile portant déjà un signal (`189-190`) ;
le balayage ne compte donc pas le PBS de la transaction précédente et cherche
la prochaine case libre.

Exemple déduit du code : espacement 7, premiers signaux posés aux indices
3 et 10 ; à la reprise, la fenêtre 3..9 saute 3 et peut poser en 4, puis la
fenêtre suivante commence à 11 et peut y poser un autre PBS. La contrainte de 7 ne porte que
sur les **nouveaux** signaux ; deux PBS peuvent être voisins. Si toutes les
positions utiles sont déjà occupées, `count1=0` produit au contraire
`signals_track1` et T1-05. Le nombre de cantons est calculé sur cette passe seule.

**Correction** : conserver ou reconstruire les signaux appartenant à la
transaction, reconnaître type et orientation corrects sans les recréer,
mesurer l'espacement par rapport à **tous** les signaux et vérifier les deux
routes avant certification. Le chargeur vérifie actuellement le dépôt et le
sens, pas la continuité et les PBS de `railLoopTrack2`.

### T1-05 — Une difficulté d'armement devient un abandon séculaire

Après `track2`, `depot_exit`, `signals_track1` ou `arm_timeout` appellent
`Fail(..., true)`. Celui-ci efface l'état de reprise et fixe un délai de
**36 500 jours**. Après ce délai, une réadmission ordinaire rencontrerait encore
l'arrière de quai déjà occupé. Il n'existe pas de chemin de reprise de
l'armement pour `railLoop=-1` avec une voie conservée.

Preuves 20×10 : **3 `depot_exit` + 1 `arm_timeout`**, tous `kept_track2=1`,
sur 37 voies 2 posées pour 33 commits. Exemple graine 714470, ligne 20 :
`track2` le 15/08/1974 (log 20399, 224 tuiles, devis 50 354), puis
`arm_timeout` le 19/02/1975 (22413). Le service peut continuer avec une rame ;
la croissance RAIL-LOOP est perdue. Le log ne donne ni erreur API de
`depot_exit`, ni position/ordre de la rame à chaque attente : **ne pas attribuer
ces trois refus à une occupation temporaire comme si elle était prouvée**.

`ArmSafe` peut rester faux avec une rame au chargement complet, en maintenance,
arrêtée ou sans trajet vers l'aval dans les 180 jours. L'attente est bornée,
mais son échec est traité comme définitif. **Correction** : état « voie posée,
armement à reprendre », échéance persistée et retries bornés classés par erreur,
avec revalidation physique. Ne pas forcer l'armement quand `ArmSafe` est faux.

### T1-06 — Le rollback ne prouve pas que la voie a disparu

`RollbackTrack2` appelle `DemolishTile` sans examiner le résultat ni conserver
une liste de résidus. `Step` transmet ensuite toujours `false` à `Fail`
quand `BuildTrack2` échoue. Un refus de démolition laisse donc le journal
annoncer `kept_track2=0`, sans ticket de récupération.

Le dernier chemin (`411-415`) peut aussi avoir raccordé le premier bout avant
l'échec du second ou de la vérification finale. L'affirmation « toujours
déconnectée pendant le retrait » n'est donc pas un invariant du code.
**Un `build_ends` est observé**, graine 107890, ligne 26, log 18601 ; la
présence effective de rails résiduels ou d'une rame sur ceux-ci reste à vérifier.
Le test actuel `test_failure_never_demolishes_a_connected_track` ne l'établit
pas : il vérifie surtout l'absence de rollback dans `Fail`, pas ce chemin.

**Correction** : journal des pièces réellement créées, déconnexion contrôlée,
contrôle d'occupation, résultat de chaque retrait et récupération persistante
des résidus. Ne pas remplacer cela par une démolition globale des tuiles de la trace.

### T1-07 — PBS facultatif : distinguer boucle et gorge de dépôt

Avec `k=1, flow=1`, la recherche du garde commence à 0 et vise 2 avec un pas
négatif : elle ne pose rien. La courbe dépôt→gare amont reste présente pour
l'entretien. Une rame dont le prochain ordre est cette gare peut donc la
rejoindre par cette courte branche **sans franchir le dos d'un PBS de voie 1** ;
celui-ci est après le dépôt. La boucle complète à l'envers, elle, rencontre
les PBS de la voie 2. L'argument du commentaire `154-155` ne suffit donc pas
à démontrer le sens unique local de la gorge.

Ce n'est **pas** une collision démontrée : réservations YAPF, ordre courant,
occupation du quai et rebroussement déterminent le résultat. Les traces donnent
4 `guard_skip` au smoke, 32 au 20×10 ; les succès observés empêchent de qualifier
ce cas de blocage systématique. **Correction éventuelle après essai** : maîtriser
l'ordre courant et l'insertion des clones ou préparer une gorge signalable ;
ne pas remettre un rejet global des dépôts proches de la gare.

## Réponses aux autres questions de T1

### Exposition et motifs de refus

| Motif | Smoke 4×6 | Rail 20×10 | Interprétation / variante à étudier |
|---|---:|---:|---|
| `reject:depot_front_curve` | 46 | 483 | Garde droite conservatrice : pas une preuve que toute courbe est impraticable. Tester les trackbits entrée/sortie et les deux raccords sous `forbid_90_deg`, ou déplacer le dépôt via une transaction. Supprimer seulement la garde serait dangereux. |
| `reject:back_lead_A/B` | 20 / 10 | 189 / 183 | Le motif agrège plan invalide, quai, voisinage, pente et occupation ; il ne prouve pas un lead d'une autre ligne. Garder l'exclusivité. À la création, réserver/préférer une sortie arrière dédiée ; ne pas reprendre le lead d'un voisin sans conception d'une jonction. |
| `defer:cash` | 20 | 80 | Devis d'admission = 1,5×longueur voie 1×prix rail + clone, report 60 jours. Heuristique, pas devis réel de la voie 2. Une simulation préparatoire hors réservation financière pourrait éviter certains faux refus, coût A* à mesurer. |
| `fail:astar_ABND` | 2 | 31 | Budget 8 000 épuisé, pas impossibilité géométrique. Reprendre un état borné au reliquat est une proposition distincte ; ne pas relever globalement le budget. |
| `fail:astar_NOPA` | 0 | 17 | File vide sous les contraintes présentes ; davantage d'itérations seules ne suffit pas. |
| `fail:not_dedicated` | 0 | 2 | Refus protecteur d'un rail existant ; localiser l'intersection et l'ajouter aux interdits, plutôt qu'autoriser son usage. |
| `fail:depot_exit` | 1 | 3 | Après pose : T1-05 ; erreur API manquante. |
| `fail:build_ends` | 0 | 1 | T1-06. |
| `fail:cash` | 0 | 1 | Après A*, contrairement au devis d'admission ; budget de signaux et sortie de dépôt absent du devis `382-389`. |
| `fail:arm_timeout` | 0 | 1 | T1-05. |

Le smoke a aussi **1 `reject:depot_exit`**, le 20×10 en a **25**.
Au 20×10 : 90 recherches, 56 échecs et 33 commits ; une recherche n'a pas encore
de terminaison dans le log terminal (graine 897560, ligne 5, ouverte le 10/12/1979). Ne pas la
transformer en échec ou en succès. Les 48 échecs A* sur 56 sont un poste
à diagnostiquer, pas une preuve que tous seraient récupérables.

### Sauvegarde par phase

| Point d'interruption | Lecture statique |
|---|---|
| Recherche seule | `railLoop=1` survit ; faute de `Track2`, passage à −1 et nouvel essai après 30 jours. Le pathfinder est volontairement perdu. |
| Pendant la pose | T1-02 : trace/progression absentes de la sauvegarde. |
| Après `track2`, avant armement | `Track2`, `Flow`, `Pbs2` survivent ; reprise en `arm`, avec `startDate=now`, donc nouvelle fenêtre de 180 jours. Validation physique insuffisante. |
| Pendant l'armement | T1-04 : les signaux déjà posés ne sont pas repris idempotemment. |
| Certifiée, hors achat | Les neuf champs écrits par le module (`railLoop`, `Retry`, `Track2`, `Flow`, `Pbs2`, `Blocks`, `Cap`, `Date`, `NextGrow`) sont compatibles avec la projection générique et ne sont pas dans `OPEX_SAVE_LINE_SKIP`. Pas d'oubli d'allowlist. |
| Pendant un clone | T1-03. |

Le cache de projection est invalidé aux transitions terminées. Il ne résout
pas les interruptions **avant** l'écriture de ces transitions. Les assertions
Python existantes ne réalisent aucun de ces parcours dans la VM NoAI.

### Croissance, rythme et cantons

`waiting >= capacity` est un déclencheur de stock, sans estimation de profit
marginal ni observation du temps d'attente en signal. `lastProfit>0` porte sur
la ligne existante. `cap = (pbs1 + pbs2 + 2) - 2`, borné à 8, garde en théorie
deux zones libres, **si** chaque zone est physiquement exploitable par les rames.
Le nombre seul ne certifie ni la gorge ni les longueurs disponibles.

L'espacement vaut `max(platformLength+2, 7)` ; conserver cette marge et vérifier
la longueur réelle après remplacement, puis la capacité des zones proches des
quais et du dépôt. Les 45 jours sont une borne minimale **par ligne**, pas une
cadence garantie : `_expandRailLines` a ses propres gardes et ne réussit qu'un
ajout par appel. Le premier clone du commit est distinct des événements `grow`.
**119 `grow` / 33 commits** ne prouve donc pas que 45 jours soit le facteur limitant.

Avant un essai d'accélération : attribuer les refus à capacité/plafond, stock,
caisse, modèle non achetable, slot véhicules et calendrier ; observer les trains
à l'arrêt et les livraisons. Tester ensuite un seul délai candidat, plafond et
topologie inchangés. Aucun nombre plus rapide n'est qualifié par cette revue.

### C41, remplacement, ferraillage et opcodes

- **C41** : les réparations de signaux et jonctions sont explicitement `false`
  (`settings.nut:493-494`) et leurs événements exigent `doubleTrack==1`
  (`event_handlers.nut:353,369`). RAIL-LOOP ne pose pas ce marqueur : elles
  ne réparent donc pas ses PBS au défaut. Ce n'est pas une collision active
  avec C41 ; ne pas réactiver ses anciennes réparations ni poser artificiellement
  `doubleTrack=1`, leur topologie est différente.
- **V257** : pas de garde de conversion ; détourner l'unique rame peut retarder
  `ArmSafe`. Hors conversion, le remplacement préserve le nombre de rames et
  recopie les ordres (`task_v257.nut:569-597`). Une revalidation de longueur et
  de topologie est nécessaire avant d'affirmer la compatibilité universelle.
- **Ferraillage** : `Step:635-638` annule une conversion marquée `scrapping` ;
  `Select:590` ne fait plus croître cette ligne. Le retrait des ouvrages n'est
  pas prévu par `_scrapDeadLines` (`task_report.nut:688-758`), pour les lignes
  ordinaires non plus. Ne pas présenter cette politique préexistante comme un
  bug spécifique de RAIL-LOOP ; le clone oublié T1-03 échappe en revanche au suivi.
- **Ordonnanceur** : le hook est dans `_runNextTask`, utilisé aussi sous sondes ;
  pas de second hook manquant dans la copie de boucle de `probes.nut`.
  L'A* est borné à 200 itérations par passe / 8 000 au total, deadline +250 ticks,
  sans prendre `_railSearch`. Cela n'en fait pas un travailleur au seul reliquat.
  Tests natifs, pose, signaux et rollback parcourent toute la trace dans le même
  appel ; la simulation continue pendant les suspensions moteur, mais la file
  des autres tâches de l'IA attend le retour. Les scans de croissance et reprise
  parcourent toutes les lignes ; seuls les candidats neufs sont plafonnés à 16.
  Coût non découpé, **pas boucle infinie démontrée**. Mesurer un span par phase
  avant de concevoir une pose reprenable, en commun avec T1-02.

## Validation exécutée et suites PC

Suite entière sur copie isolée, avant rédaction :
`python -X utf8 -m unittest discover -s sweeps -p 'test_*.py'`.
**3 387 tests, 4 failures, 12 errors, 10 skips, 2 expected failures** (73,849 s).
Tous les échecs appartiennent aux familles préexistantes annoncées : B6 (1),
projection RAIL-LONG v3 multi (2 sous-tests), V166 AAAHogEx (1 failure, 12 errors,
source adverse absente). Aucun téléchargement de l'adversaire, Docker ou moteur.
La suite après rédaction et les contrôles d'archives sont consignés au suivi
final ci-dessous. Squirrel non compilé, Save/Load non exercé, sécurité physique
et gains des corrections non qualifiés.

### Plan PC à préparer après correction — non lancé

1. **Contrats et reprise** : réservation réciproque avec transactions anciennes,
   idempotence des signaux ; interruptions après chaque commande de pose/raccord,
   armement et clone, avec au moins 64 lignes pour activer le cache Save.
   Vérifier rails, PBS, rames, ordres, compte physique, absence de double achat,
   reprise des retraits refusés. Inclure occupation temporaire, manque de caisse,
   remplacement V257, départ en ferraillage et réglages RAIL-LONG/INVEST-STALL ON.
2. **Diagnostic demandé 4×6 rail seul**, graines **17 512 314 8191**, carte
   identique, AAA rail seul. Référence exacte du prompt :
   `OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1]`
   (**rail_loop=1** au défaut de `fbc0f100`). Variante : même bras avec uniquement
   la correction isolée. Si aucun commutateur ne conserve le témoin, utiliser
   deux arbres figés via le harnais existant ; ne pas employer `rail_loop=0`
   comme témoin du correctif, cela mesurerait le mécanisme entier.
3. **Exposition** : `decision_log=1` dans les deux bras, capture `--script-debug`
   et télémétrie identique ; comptabiliser `search/track2/commit/grow/fail`,
   motif API précis, délais, opcodes, refus de financement et résidus réels.
   Le smoke six ans ne remplace pas les scénarios Save/Load injectés ni une porte économique.
4. **Critères techniques** : 8/8 parties saines à horizon complet, aucun clone
   non attribué, aucune concurrence sur la ligne réservée, zéro résidu non suivi,
   PBS de bon sens et espacement vérifié, parcours dépôt/quais et croissance
   sans rame perdue ni arrêt permanent. Conserver aussi tous les refus et faillites.
5. **Profil PC** : `--cpus 10 --memory 8g --max-workers 10`, cache et swap selon
   AGENTS ; vérifier Docker, montages et campagnes actives avant tout lancement.
   AAA : `disable_veh_roadveh=1`, `disable_veh_tram=1`, `disable_veh_ship=1`,
   `disable_veh_aircraft=1`. Durée 6, début 1970, `map_size=8`, une répétition.
   Pour enregistrer ce diagnostic avec le lanceur V102 : `--decision-rule gain_short
   --primary-metric profit_year --min-useful-primary-delta-pct 4
   --value-guard-max-loss-pct 5 --required-seeds 40 --required-years 6
   --years 6 --seeds 17 512 314 8191` ; échantillon volontairement insuffisant
   pour adoption, juger santé/exposition et conserver le verdict brut.

La garde de valeur historique 100 des bancs du 04/11 était une dérogation propre
à ces campagnes ; elle n'est pas reprise implicitement ici. Après diagnostics,
qualification économique à pré-enregistrer séparément ; **aucune porte B autorisée**
par cette revue. L'adoption historique de `rail_loop=1` reste une décision utilisateur,
sans réécriture des `fail_primary` des portes A.

## Suivi final

Revue T1 terminée ; correctifs T1-01 à T1-06 proposés, non implémentés.
T1-07 reste une vérification moteur, pas un défaut de circulation affirmé.
T2 à T9 et leur synthèse ne sont pas exécutés par cette session.

Suite **après rédaction : 3 387 tests en 65,988 s**, mêmes 4 failures et
12 errors, mêmes 10 skips et 2 expected failures. Les 16 signatures
d'échec/erreur sont identiques avant/après, aucune régression ajoutée.
Les 5 archives sont relues et vérifiées par hash brut/compressé ; les compteurs
sont recalculés depuis les **2 378 événements** du CSV archivé. Liens relatifs,
références de fichiers et `git diff --check` vérifiés. Seuls rapport, suivi
documentaire et preuves sont destinés au commit T1.
