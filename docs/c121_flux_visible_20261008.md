# C121 — candidat NoAI et raccordement des trois usages

Pré-enregistrement avant parties : `c121_air_visible_competition=0` témoin,
`=1` candidat, défaut0 aux quatre difficultés. Même arbre courant modifié,
HEAD36fa8c79a740a54632d34ce86aecd2f5639e9493 ; autres réglages inchangés sauf
decision_log1 dans les deux bras pour l'exposition. Aucune adoption autorisée
par le diagnostic, aucun commit/publication implicite.

NoAI voit IsAirportTile/GetOwner sur les tuiles adverses, mais GetAirportType
et GetCargoRating rejettent leurs stations. Candidat : rayon du petit aéroport
exposé par NoAI, compagnies dédupliquées par producteur, prior de ratings égaux,
division du flux local par1+nombre de compagnies adverses couvrant la source.
Les installations non-AIR, services inactifs et ratings inconnus restent des
limites explicites. MAIL conserve l'ancien modèle.

Analyse externe avant implémentation : mêmes978 intervalles de42x6, reproduction
B9 par comptage des maisons porteuses PASS, production LAST_MONTH et ratings
propres ; erreur45,46 %→22,83 %, biais+41,78 %→+14,65 %. Source
`results/c121_source_map_20261008/diag42_6y/source_analysis_noai.json`.
Les ratings propres sont les octets exacts de sauvegarde, contre pourcentage
quantifié NoAI ; pas une identité bit à bit du modèle de l'IA. Une seule graine,
prévision mensuelle seulement, aucune conclusion de flux annuel futur.

Raccordements implémentés :

- Nouveaux aéroports et hubs : buckets de capture partagés par les choix moteur,
  flux/revenus, meilleur nombre d'avions et marges post-build. Répartition des
  routes existante conservée ; aucune multiplication du total de gare.
- Renforts : actualisation mensuelle des gares existantes et du moteur réellement
  exploité, calcul C121 du total de flotte et marge prévisionnelle N+1−N.
  Exclusion de la ligne recalculée des services de hub pour éviter le double
  comptage. Cible actualisée avant les gardes et vérifiée au site d'achat.
  Les marges réellement observées ne sont jamais remplacées par ce devis ;
  dernier marginal négatif et gardes temporelles restent applicables.
- Save/Load : aucun nouvel état durable. Les cibles et marges froides existantes
  utilisent leur persistance habituelle ; les nouveaux caches sont reconstruits,
  effacés au chargement des réglages. Cache mensuel, invalidation véhicules et
  epoch de géométrie pour le devis de flotte. Pas de vente de flotte existante.

Validation pré-enregistrée : contrats Python, VM réelle avec matrice de capture
et assertion de préservation des marges observées avant/après Save/Load, puis
smoke causal42x1 (deux duels), règle explicite gain_short/4 %/garde5 %, hors
échantillon d'adoption. Ressources locales réduites à2CPU/2g/2workers pour ce
contrôle car d'autres diagnostics utilisateurs tournent ; volume cache courant.
Campagnes neuves : fixtures `results/c121_target_limit/visible_vm_20261008_r1`,
smoke `c121_visible_flux_smoke42_20261008_r1`, sortie
`results/c121_visible_flux_20261008/smoke42_r1/bench.json`.

Budget actuel : VM deux phases un an, smoke deux duels un an ; si sains et
exposition hubs insuffisante, un diagnostic candidat42x3 maximum avant bilan.
Pas de gateA ni adoption avant validation temporelle du flux annuel et couverture
des trois usages. Conserver tout échec technique ; aucun rerun favorable.

VM r1 :26 sauvegardes, matrice et devis live validés avant/après Load,
réconciliation saine et marges observées préservées. Smoke causal r1 : référence
saine, variante noai_error (appel inexistant AICompany.IsValidCompany au premier
aéroport adverse), verdict brut incomplete. Aucune conclusion économique.
API corrigée par ResolveCompanyID et COMPANY_INVALID, vérifiée dans le code
primaire15.3 ; nouvelle campagne r2 même protocole/graines/horizon/budget,
`c121_visible_flux_smoke42_20261008_r2`, sortie `smoke42_r2/bench.json`.
Le recalcul de flotte est aussi déplacé avant le plafond target_limit optionnel,
pour ne pas refuser sur une ancienne cible avant de lire le nouveau devis.

Smoke r2 sain : deux duels complets, verdict diagnostic_only. Variante :2 newpair,
10 hubsite,4 hubhub avec visible_flux1 et156 devis de flotte live ; référence
visible_flux0, aucun devis live. Bundle
d0e1b702cdac570fe2879d58fb116f154184c61be7b5e8688e13a2a130d6d674,
manifeste bf435184566d6fc9ea4edf2dd1d8eb9dd9429a2433a3b089adb94a83a52f6e2d.
La garde temporelle des renforts exige normalement deux ans : compléter le budget
diagnostique pré-enregistré par42x3 candidat seul pour vérifier les achats de
renfort et l'exposition de la demande courante, pas pour une conclusion de gain.
Campagne `c121_visible_flux_exposure42_3y_20261008`, sortie
`results/c121_visible_flux_20261008/exposure42_3y/bench.json`, même bundle attendu.

Diagnostic42x3 terminé sain :3 newpair,18 hubsite,11 hubhub ;13 hubsite et9 hubhub
avec producteurs potentiellement adverses.992 devis live et23 achats réels de
renfort, chacun un avion, sur23 lignes. Les3 newpair ont bien utilisé le chemin
commun mais ne rencontraient pas d'aéroport adverse à leur construction : le
cas newpair avec réduction non nulle reste couvert par matrice/contrats, pas
exposé naturellement sur cette graine. Manifeste
ed6d2f2c7562322e56b23d05566e7e7c2f9107a8dd1b8f679f9119ba2f8db975.

Dernière garde d'intégration : charger le candidat uniquement si C121 causal1,
pour le rendre inerte quand C1210. Revalidation technique sur code final,
VM `visible_vm_20261008_r2` et smoke `c121_visible_flux_smoke42_20261008_r3`,
même protocole. Aucun nouvel essai économique, aucune sélection favorable.

Audit des achats : `exposure42_3y/visible_exposure_audit.json`, empreinte du log
et ligne de chaque achat/devis précédent ;23/23 ont un devis live antérieur.
VM r2 : tous les contrôles avant/après reload passent sur code final.
96 contrats ciblés verts (visible3, C12173, target5, C84six, probe4, carte5),
diff-check vert. Le développement actuel ne satisfait pas encore une validation
annuelle hors période ni sur graines réservées ; aucune porte économique lancée.

Smoke final r3 sain : deux duels complets, verdict diagnostic_only, mêmes
trajectoires et métriques que r2 dans les deux bras. Bundle
4dd7c4bd867ff8c3850160da3cd2f40f8c0ba7e4d1740110b041d2ea72548d50,
manifeste16bcdbce6d61205a22fc552aa25cc12a5055f2a5a23a7183eb25ad5b8dc3fa77.
Défaut toujours0. Le résultat42x3 est un diagnostic d'exposition au bundle r2 ;
la différence finale de chargement ne concerne que C1210, le smoke final confirme
les trajectoires C1211. Ne pas transformer ces contrôles en qualification de gain.

### Validation réservée — pré-enregistrement du 08/10 avant lancement

Campagne `c121_visible_flux_reserved_3x6_20261008` : trois duels de six ans,
graines réservées73/314/512, une répétition, référence
`OpexAI[c121_air_visible_competition=0,decision_log=1]` contre AAAHogEx figée.
HEAD36fa8c7, arbre local modifié conservé ; image locale f4b2b9b3b739,
10CPU/8g RAM et swap/3workers, cache openttd-lab-home, aucun conteneur actif
avant lancement. Sauvegardes brutes retenues, station-supply et lignes mensuelles,
script-debug. Sortie `results/c121_visible_flux_20261008/reserved_3x6/bench.json`.
Budget :18 années de duel, une seule collecte ; pas de sélection favorable.

Comparaison hors ligne du seul estimateur de capture B9 propre/B9 visible,
sans réestimer ses paramètres et sans informations adverses cachées dans le
candidat. Ratings propres de sauvegarde : approximation de leur quantification
NoAI, donc pas une reproduction bit à bit du devis C121 complet. Le label reste
le cargo nouveau reçu par station, pas le revenu ni les embarquements d'une ligne.
Prévisions figées à l'ancre : douze intervalles mensuels futurs contigus,
365 ou366 jours, tous exacts ; aucune imputation des compressions/graphes modifiés.
Ancres fixes tous les douze checkpoints à partir du checkpoint12 (période future,
hors première année). Exclusions et couverture publiées, même lot pour les modèles.
WAPE/biais globaux et par graine ; station et snapshots ne sont pas des graines.
Conditions pour poursuivre : cas annuels stricts sur chacune des trois graines,
WAPE visible inférieur au témoin globalement et par graine. Ce contrôle de précision
ne remplace pas les portes économiques. Strates d'âge/construction documentées ;
une station partagée ne permet pas d'attribuer son flux à un achat de renfort.

Exposition neuve dirigée séparée : copie de l'IA et fixture sur un duel42x1,
devis de site neuf libre dans le bassin d'un aéroport adverse réel déjà installé.
Aucun achat imposé ni changement de la production ; établir stationId=-1,
rivalWeight>0 et baisse de capture au rating fixé. Ce test qualifie le devis
d'un nouvel aéroport, pas une construction naturelle rentable.

Extension diagnostique pré-enregistrée après constat de zéro année exacte,
avant calcul des bornes : réutiliser uniquement ces sauvegardes. Les compressions
OpenTTD15.3 divisent supply par deux ; une compression isolée donne une borne
de flux, pas un label exact. Autoriser seulement graphe/membres/identité stables,
date de compression compatible, âge bornant à une compression maximum sur le
mois. Année retenue seulement si les douze intervalles sont exacts ou bornés,
aucune fusion imputée. Publier la largeur des bornes, les bornes du biais et
de l'erreur absolue ; comparer les deux prévisions sur tout flux admissible.
Ce résultat secondaire ne remplace pas la condition annuelle exacte précédente
et ne déclenche aucune porte A/B. Source primaire :
[compression](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/linkgraph/linkgraph.cpp),
[déclenchement](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/station_cmd.cpp#L3908).

### Résultats réservés et exposition dirigée

Collecte réservée terminée :3/3 duels complets/sains,216 sauvegardes, bundle
4dd7c4bd867ff8c3850160da3cd2f40f8c0ba7e4d1740110b041d2ea72548d50,
manifeste c0d7f1cf505f7d4e599d0c24f36a148492b6c4d887d41b46e54f1e1796cfbe70.
Les archives sont associées par ordre des expériences du manifeste (73/314/512),
pas par ordre des jeux dans le bilan (314/512/73). Lecteur généralisé à un index
explicite ; manifestes/bundles/bruts vérifiés avant décodage.

| Graine | Intervalles mensuels exacts | WAPE B9 propre | WAPE B9 visible | Biais propre | Biais visible |
|---|---:|---:|---:|---:|---:|
|73|1057|45,43 %|24,05 %|+41,08 %|+16,18 %|
|314|913|37,68 %|28,03 %|+24,39 %|+3,39 %|
|512|398|57,61 %|29,08 %|+57,31 %|+21,71 %|
|Ensemble|2368|44,04 %|26,41 %|+36,62 %|+11,75 %|

63 stations ; amélioration mensuelle répliquée sur les trois graines, sans fit
supplémentaire. Sources `reserved_3x6/sources_0.json`, `_1.json`, `_2.json`.
La réplication ne prouve pas encore une cible de flotte rentable.

Prévision annuelle exacte `reserved_3x6/future_year.json` :0 cas ;191 ancres
rejetées pour au moins un intervalle futur non exact,62 sans horizon terminal
suffisant. **Condition de précision annuelle non validée**, pas rejet du candidat.
L'extension secondaire finale `future_year_bounds_r2.json` conserve54 années de station,
31 stations :48 cas sur73,6 sur512,aucun sur314. Graphe/membres/identité stables
obligatoires ; toutes les compressions ambiguës/fusions restent exclues.
Flux reçu annuel total entre39852 et47017 passagers. WAPE propre bornée
32,997–56,210 %, visible13,722–33,042 % ; biais propre+25,551–+48,124 %,
visible+1,490–+19,737 %. L'erreur absolue visible est inférieure pour tout choix
de labels dans ces bornes, globalement et sur les deux graines couvertes.
Pas d'estimation centrale inventée, pas de qualification sur trois graines.
La r2 borne explicitement l'âge après la première compression pour exclure
une seconde compression possible ; tests d'ambiguïté renforcés,54 cas et tous
les chiffres identiques à la première analyse, conservée séparément.
Ces ancres concernent des gares exploitées ; elles ne donnent pas le marginal
d'un renfort ni la capture future au rating projeté d'une gare neuve.

Fixture dirigée `results/c121_target_limit/visible_newsite_20261008_r3/report.json`
saine : site libre56137, construction autorisée en AITestMode, stationId=-1,
reuse0, rival réel station5/owner1. Endpoint complet avec arrêts joints prédits,
5 producteurs partagés sur13, flux brut106/mois. À rating127 fixe : capture
38,923386→30,490654/mois (−21,66 %). Aucun aéroport imposé dans la carte.
Mesure ponctuelle de buckets sur mêmes producteurs :3709 opcodes OFF,
10405 ON cache froid,3812 ON cache chaud. Ce cas montre le coût du scan initial,
pas le coût agrégé du recalcul de toutes les flottes ni un gain d'opcodes.

Fixtures r1/r2 conservées : parties saines mais exposition absente, aucune
conclusion. Le rectangle de recherche employait des coins invalides de carte,
donc AddRectangle rejetait toute la liste. Correction de la fixture et du même
cas limite dans le scan candidat (coins1 et largeur/hauteur−2). Type du site
neuf pris dans le catalogue courant au lieu d'imposer AT_SMALL.

Revalidation du code final :103 tests ciblés verts, VM Save/Load
`visible_border_vm_20261008` verte (26 sauvegardes), smoke causal
`c121_visible_flux_border_smoke42_20261008` complet/sain, diagnostic_only,
bundle dc6db460a1f5c705f1c08fd9cb6278c3a760924258ed58f3b0918e802758467d,
manifeste41fd362c6d3c6f0a26944654272516c5502d770dba014efddd5d6fd2cda248a2.
Les métriques du smoke restent identiques au smoke précédent ; aucun verdict
de gain économique. Défaut0, aucune porte A/B lancée, aucun commit/publication.

Suite nécessaire : obtenir une mesure annuelle suffisamment couverte sur314
en auditant la continuité des nœuds survivants lors des ajouts/fusions, ou un
collecteur de flux annuel informatif sans modifier le jeu. Valider séparément
le rating projeté/capture des sites neufs et le coût de l'ensemble des devis
de flotte. Ne pas transformer le gain mensuel ou les54 années bornées en passage
de la condition annuelle pré-enregistrée. Ensuite seulement A40x3, puis B20x10
si A passe.

### Audit des nœuds survivants — plan avant nouvelle analyse

Reprise demandée par l'utilisateur. Source15.3 `LinkGraph::Merge` : seuls les
nœuds importés changent d'échelle ; les nœuds déjà présents dans le graphe
survivant conservent leur compteur. `AddNode` ajoute une entrée sans modifier
les anciennes. Extension du décodeur diagnostique explicitement optionnelle :
accepter la croissance de membership seulement si graphe inchangé, ensemble
ancien intégralement conservé avec coordonnées identiques, identité de station
inchangée et compteur/date cohérents. Graphes transférés, retraits, déplacements,
resets et compressions ambiguës restent inconnus. Ancien décodeur et résultats
conservés ; nouvelle analyse des mêmes216 sauvegardes, sans relance ni fit.
Comparer les prévisions figées aux bornes annuelles sur tout label admissible,
publier séparément chaque graine et la couverture obtenue. Cette réanalyse
n'est pas un passage de la condition annuelle exacte initiale ; aucune A/B
automatique fondée sur ce changement de méthode.

Coût global pré-enregistré : copie instrumentée du corps de
OpexC121RefreshVisibleFleet, compteur existant GetTick/GetOpsTillSuspend et
OPS_PER_TICK. Duels diagnostiques42×3 sous OFF et ON, même instrumentation,
10CPU/8g/1worker/cache courant ; pas comparaison de profit ni gate. Mesurer
nombre d'appels, recalculs complets, cache/no-op, opcodes et ticks dépensés,
distribution par mois. Les trajectoires peuvent diverger ; coût naturel des
usages réels, pas assertion d'identité des entrées ni optimisation d'opcodes.
Pas de modification de l'IA de production ni de Sleep ajouté.

### Résultats de l'audit de continuité et coût global

Analyse `reserved_3x6/future_year_surviving_growth.json`, mêmes empreintes de
sauvegardes/manifestes/bundle que ci-dessus, hashes des décodeurs enregistrés.
173 fenêtres annuelles complètes bornées,56 stations,176 intervalles de croissance
du graphe conservés selon l'audit.1582/2076 intervalles exacts,494 compressions
bornées ; aucune fusion transférant le nœud ni fenêtre partielle imputée.
Les18 ancres restantes d'horizon suffisant demeurent inexploitables (11/4/3
par graine).62 sans horizon suffisant restent exclues.

| Graine | Fenêtres annuelles | Stations | Biais propre borné | Biais visible borné | Correction meilleure pour tout label admissible |
|---|---:|---:|---:|---:|---|
|73|75|25|+25,16 à +48,87 %|+2,38 à +21,77 %|oui|
|314|72|23|+11,19 à +33,72 %|−8,20 à +10,39 %|oui|
|512|26|8|+26,76 à +53,32 %|−3,57 à +16,64 %|oui|
|Ensemble|173|56|+19,33 à +42,94 %|−3,03 à +16,16 %|oui|

WAPE propre bornée28,25–52,95 %, visible15,00–36,79 %. Les bornes de WAPE
se chevauchent ; la comparaison appariée des erreurs, elle, conserve un delta
négatif pour tout jeu de labels admissibles :−25745,53 à−16127,57 passagers.
Ce sont173 fenêtres de stations sur trois graines, pas173 expériences
indépendantes. Résultat annuel informatif répliqué, condition annuelle exacte
historique inchangée/non validée. Le rating reste celui observé à l'ancre,
donc validation du partage de capture, pas du rating futur projeté par C121.
Une fusion du graphe survivant ne recalibre pas ses nœuds déjà présents ; les
nœuds importés sont exclus si leur graphe change. L'analyse suppose une partie
ordinaire sans mutation cachée des sauvegardes/cheats, comme le collecteur exact.

Duels de coût copiés OFF/ON42x3 complets/sains, sources copiées inchangées,
résultats `results/c121_target_limit/visible_cost_off_20261008` et `_on_20261008`.
Collecteur/configuration/bibliothèques/santé du diagnostic existant réutilisés.
Le champ kind du plan initial conserve le nom du driver de site neuf ; les
hashes de fixture/copies et marqueurs identifient bien le compteur passif de
flotte, pas une exposition de site neuf. Métadonnée corrigée pour les futurs
lancements, aucun artefact ancien réécrit.

Analyse des36 périodes closes1970–1972 :

| Mesure | OFF | ON |
|---|---:|---:|
|Appels au corps de refresh|9513|6806|
|Devis complets|0|1051|
|Opcodes devis complets|0|53779348|
|Appels cache/no-op|9513|5755|
|Opcodes cache/no-op|172250|453520|
|Coût moyen d'un cache/no-op|18,11|78,80|
|Coût moyen d'un devis complet|sans objet|51169,69|
|Médiane / P95 devis complet|sans objet|45441 /82522|
|Ticks traversés pendant devis complets|0|5382|

Source finale `results/c121_visible_flux_20261008/visible_cost_analysis_r2.json`, log et
plan hashés ; chaque nombre et coût de devis réconcilié avec sa période.
Première analyse conservée, chiffres identiques ; hash du décodeur final après
retrait d'une variable Python inutilisée enregistré dans la r2.
Les périodes suivent le mois à l'entrée du scheduler ; pas une mesure du temps
mural ni du coût total de l'IA. Wrapper/logging exclus du corps mesuré. Trajectoires
différentes, donc pas preuve à entrées identiques ni gain d'opcodes. Maximum
mensuel ON4932627 opcodes,97 devis au mois23657 : invalidations de géométrie
peuvent provoquer plusieurs recalculs d'une ligne pendant le même mois.

Suite prioritaire avant qualification : réduire les évaluations redondantes
du devis live sans affaiblir les invalidations (notamment N/N+1 quand leurs
marges observées sont déjà disponibles), puis comparer à entrées figées avec
la VM existante ; confirmer le rating projeté des sites neufs. Le gain annuel
de précision ne suffit pas à adopter ce coût ni à déclencher A/B. Aucun défaut
modifié dans cette reprise.

### Exploration des redondances — plan avant mesure

Le log ON précédent contient1051 devis, tous `observed_samples=0`. La suppression
de N/N+1 pour les marges déjà observées n'y aurait donc aucune exposition.
58 devis seulement ont `target=have+1`, aucun `target=have` : réutiliser le
seul résultat gagnant évite peu de calculs. Chaque scan complet parcourt déjà
les profondeurs de flotte ; conserver les trois scalaires effectivement consommés
pour N et N+1 pourrait éviter les deux évaluations supplémentaires, même lorsque
ces profondeurs ne sont pas gagnantes. Une profondeur hors du scan utilise
l'évaluation fixe originale. Aucun changement de cap ni d'arrondi.

Diagnostic pré-enregistré42×3, un duel partagé,10CPU/8g/1worker, sortie neuve
`results/c121_target_limit/visible_redundancy_20261008`. Copies figées/hachées
par le driver existant. Même devis : trois appels originaux puis un scan copié
augmenté d'une capture minimale ; les résultats originaux pilotent la partie.
Comparer exactement le snapshot cible entier et profit/revenu/réalisation de
N/N+1. Les cas franchissant une date sont signalés et exclus de la mesure
à entrées temporelles identiques. Erreur sur toute différence à date stable.
Mesurer les trois appels et le scan fusionné, y compris ses captures et replis.
Compter séparément misses froids, âge, véhicules et epoch (causes cumulables).
L'instrumentation peut déplacer la trajectoire ; pas de verdict économique.

Audit du code : `OpexC121CatalogChoice` incrémente l'epoch globale pour tout
miss `age` ou `input`, puis les flottes comparent cette epoch. Une expiration
économique locale peut donc provoquer plusieurs devis d'autres lignes dans
le mois. Les invalidations restent intégralement actives dans ce diagnostic.
Une réutilisation future devra distinguer changements physiques, productions,
ratings, services et apprentissages ; supprimer simplement l'epoch ne prouve
pas l'équivalence. L'ancien contexte moteur générique rejeté reste OFF.

Diagnostic42×3 terminé, complet/sain, sans assertion, copies inchangées.
HEAD36fa8c79a740a54632d34ce86aecd2f5639e9493, arbre local modifié, contexte
Dockerdesktop-linux, imagef4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659.
Les copies effectivement jouées sont décrites par leurs hashes dans `plan.json`.
Source finale `results/c121_visible_flux_20261008/visible_redundancy_analysis.json` :
log5347a2a2f3a10d2ee03602ffe66b61fd2b9c523804d6503a83447026f51db71e,
plan4b5f20aa47cc0847a0ccb13621346dfbfdb83962dd75a01be75519a8414b3f79.

932 devis naturels instrumentés ;684 à date stable, tous exactement égaux
sur la cible complète et les trois champs consommés de chaque marge.
248 franchissent une date et sont exclus du gain apparié. Aucun repli hors
scan exposé dans ce lot : ce chemin reste à couvrir dans une matrice dirigée.

|Évaluations économiques des684 devis comparables|Opcodes|
|---|---:|
|Scan cible original|14427114|
|N original|2158568|
|N+1 original|2143295|
|Total original|18728977|
|Scan fusionné, captures et replis compris|14566103|
|Économie|4162874, soit22,23 %|

Les captures ne coûtent que138989 opcodes de plus que le scan cible original
sur ce lot. Ce gain concerne les évaluations économiques, exclut préparation
de la demande/géométrie ; pas22,23 % de toute l'IA ni du devis complet.
Le prototype est uniquement dans les copies du diagnostic : aucun changement
du modèle économique livré, aucun défaut/adoption ni banc économique.

|Cause de reconstruction,932 devis|Nombre|
|---|---:|
|Premier devis|30|
|Âge seul|448|
|Epoch seule, cache de moins de30 jours et taille de flotte identique|428|
|Âge et epoch|6|
|Véhicules seuls|17|
|Véhicules et epoch|2|
|Âge et véhicules|1|

428/932=45,92 % proviennent de l'epoch seule. Une epoch changée peut aussi
signaler une modification physique/service réelle : ce compte ne prouve pas
que ces428 devis sont tous supprimables, ni leur attribution exclusive aux
misses `age/input` du catalogue. La prochaine mesure doit distinguer ces
émetteurs et comparer un devis frais à la réutilisation proposée.

Audit des redondances restantes : PASS et MAIL partagent déjà les stops et la
géométrie de catchment ; le scan `airportOnly` est déjà réservé à la sonde B9.
La géométrie des gares propres est déjà mémorisée par station, mais effacée
par l'epoch globale. Piste prioritaire : conserver cette topologie séparément
des productions/ratings/services dynamiques, avec invalidation physique
explicite et contrôle par recalcul frais. Le cache de rivaux visibles a déjà
une durée30 jours ; ne pas l'allonger sans contrôler les constructions adverses.
7 tests ciblés verts (allocation visible3, coûts2, redondances2), VM réelle
compilée/exécutée dans le duel sain. Qualification économique toujours absente.

### Topologie conservée — plan avant mesure

Diagnostic copié42×3,10CPU/8g/1worker, sortie neuve
`results/c121_target_limit/visible_topology_20261008`. Le cache original et
ses invalidations continuent à piloter la partie. Cache parallèle de seule
topologie des gares Opex : conserver lors des misses catalogue `age/input`,
vider lors de toutes les autres invalidations (site_reset, coverage_reset,
station_lines et autres). Epoch globale, demande, ratings, services et
concurrence sont toujours rafraîchis selon le code original.

À chaque appel comparer géométrie originale, parallèle et reconstruction
fraîche via AITileList_StationCoverage. Toute différence arrête le diagnostic.
Mesurer original/parallèle séparément ; oracle et logs exclus. Enregistrer
chaque émetteur d'invalidation avec nombre d'entrées conservées/vidées.
Il s'agit de matérialisation du catchment, pas de réutilisation des devis
entiers ni des productions/ratings. La trajectoire instrumentée n'est pas une
mesure économique. Profondeurs dirigées `N=cap` et `N=cap+1` pour exposer un
et deux replis hors scan, comparaison cible et marges exacte à date stable ;
ces cas sont exclus des coûts naturels du cache.

Premier diagnostic complet/sain :666 appels de géométrie, tous identiques à
l'oracle frais ; aucun miss age/input exposé. Invalidationother1, site_reset1,
coverage_reset4, station_lines32. Hits460 des deux côtés, aucune matérialisation
évitée ;304427→315098 opcodes (+3,51 %, pas un gain). Piste age/input seule
non exposée sur cette trajectoire, aucun résultat économique/adoption.
Les deux cas dirigés hors scan passent : N=cap11/repli1 et N=cap12+1/replis2.
Analyse `results/c121_visible_flux_20261008/visible_topology_analysis.json`.

Nouvelle intervention pré-enregistrée avant mesure : cache parallèle à
révision par station, conserver sur station_lines mais vérifier à chaque
lookup C121_CATALOG_STATION_REV ; reconstruire les stations dont la révision
a changé. La fonction existante augmente déjà les révisions des endpoints
dont la signature de lignes a changé, y compris les stations retirées.
Toutes les autres invalidations physiques restent globales. Epoch/demande
originales restent inchangées. Oracle frais systématique, erreur si géométrie
différente ; les résultats originaux jouent. Diagnostic42×3, même budget,
sortie neuve `results/c121_target_limit/visible_topology_scoped_20261008`.
Cela change la granularité physique contrôlée, pas une relance à intervention
identique ni une qualification de la première piste non exposée.

Diagnostic à révisions locales terminé, complet/sain/exposé, copies inchangées.
700 appels, géométries originales/parallèles identiques à l'oracle frais,
aucune assertion. Deux cas hors scan dirigés à date stable passent à nouveau
(un/deux replis). Résultats appariés à l'intérieur de cette seule partie :

|Topologie des gares,700 appels|Original|Cache à révision locale|
|---|---:|---:|
|Hits|573|654|
|Matérialisations|127|46|
|Opcodes|193265|81693|

81 matérialisations évitées, économie111572 opcodes/57,73 % du composant
topologie. Révisions contrôlées et misses inclus dans son coût ; oracle frais
et logs exclus. Économie modeste en valeur absolue, pas57,73 % du devis/IA.
Les deux pourcentages (scan économique22,23 % et topologie57,73 %) concernent
des composants et trajectoires distincts : ne pas les additionner.
Invalidationsother1, site_reset1, coverage_reset4, station_lines25 ;23
invalidations conservées avec cache non vide. Aucun age/input naturel ici
non plus : cette branche demeure non exposée dans les deux diagnostics.

Source finale `results/c121_visible_flux_20261008/visible_topology_scoped_analysis_r2.json`.
Logf70d3fc463d96445d8b2218cd1629e4e8fdb3496f2a5247ab3f8d5db80bc27f5,
planb1227f27a708747100521f1a8a41f1fd3a429df1f12f12608f314d25ae598af1.
Première analyse conservée ; r2 renomme le compteur d'invalidations gardées,
car station_lines n'est pas une expiration économique. Chiffres inchangés.
HEAD/image/profil du premier diagnostic inchangés ; copies effectivement
jouées hachées dans chaque plan, trajectoires différentes par instrumentation.
8 tests ciblés verts (topologie3, redondances2, allocation visible3).

Priorité restante : intégrer expérimentalement la capture N/N+1 dans le modèle
commun, mesurer le corps entier du devis et vérifier Save/Load/marges observées.
Le cache physique local est une seconde optimisation plus petite ; son contrôle
de révision doit être validé sur constructions, extensions et démolitions
réelles avant utilisation sans oracle. Aucune production modifiée dans cette
reprise, défaut visible0, aucun verdict économique ni adoption.

### Scan fusionné dans le refresh complet — plan avant mesure

Intégration expérimentale sur copies uniquement, sans cache physique local :
même corps de refresh sauf cible/N/N+1 calculés par le scan fusionné et
replis fixes hors scan. Aucun défaut ou modèle commun modifié. Diagnostic42×3,
10CPU/8g/1worker, sortie `results/c121_target_limit/visible_fused_body_20261008`.
Sur chaque miss : original puis candidat, mêmes ligne et lignes voisines,
restauration des champs de ligne et des quatre caches reconstructibles entre
les deux corps (fleet, endpoint, geometry, rival). Les valeurs des caches sont
des snapshots/arrays non modifiés par ces corps ; restauration des tables
externes suffit. Candidate utilisée pour jouer. Mesure du corps entier,
restauration/logs de comparaison exclus ; logs internes inclus symétriquement.
Date stable requise, cible et champs de marges exactement égaux sinon erreur.
Les dates franchies restent recensées, exclues du gain à entrées comparables.
Ce test couvre le coût de construction du devis, pas le coût de toute l'IA.

Validation distincte via le driver Save/Load existant, sortie neuve
`results/c121_target_limit/visible_fused_reload_20261008` : un an puis reload
ordinaire après1970-07, matrice d'allocation et préservation des marges
observées avant/après Load. Les caches restent reconstructibles, aucun nouvel
état durable. Runtime/image/profil local inchangés et contrôlés avant lancement.

Premier diagnostic de corps entier arrêté par assertion après70 devis : cible
6→7 sur une même date. Résultat conservé/non validé, aucune conclusion économique.
Le contrôle par date seule ne fige pas les API live pendant les suspensions.
Correction pré-enregistrée du diagnostic : comparer aussi les snapshots préparés
(demande hors télémétrie ops/ticks, services, invariants moteur, avion/capacités,
trip et réalisation) ; restaurer le cache K_dec date/valeur entre les corps.
Toute sortie différente à date ET inputs égaux reste une erreur. Un input différent
est exclu du gain, même à date stable. Capture symétrique de snapshots incluse
dans les deux coûts ; coûts de comparaison/restauration exclus.
Sortie neuve `results/c121_target_limit/visible_fused_body_20261008_r2`, même42×3
et budget ; aucune réutilisation du verdict du premier diagnostic défaillant.

Diagnosticr2 complet/sain/exposé, copies inchangées.813 devis comparés,
301 à date ET entrées préparées identiques, sorties exactement égales ;447
franchissements de date et65 changements d'inputs à date stable exclus.
Ces exclusions confirment que la date seule n'est pas une garantie d'entrées
live constantes ; elles ne démontrent pas une erreur du scan fusionné.

|Corps entier sur301 devis comparables|Original|Fusionné|
|---|---:|---:|
|Opcodes|14180572|12351448|
|Moyenne par devis|47111,53|41034,71|

Économie1829124 opcodes/12,90 % sur ce sous-ensemble. Préparation de demande,
géométrie, services et mise à jour de la ligne incluses ; capture d'inputs
et logs internes symétriques inclus, restauration/comparaison externes exclues.
Pas une économie12,90 % de l'IA ni de tous les devis longs exclus ; candidats
utilisés pour jouer mais trajectoire instrumentée, pas qualification économique.
Samplesobservés0 sur les301 cas naturels ; leur préservation est testée séparément.
Source `results/c121_visible_flux_20261008/visible_fused_body_analysis.json`,
log0653384d4bda626ffc762223b0cbdd42614765ce57ccd2dd363a9b6dd1273a09,
plan959bedba5046a51b7bacc770df60d3ed6bcf49e4305c9d3f49256de377405c91.

Save/Load fusionné terminé :13 sauvegardes par phase,26 au total, intervalles
mensuels exacts, aucune erreur script, toutes les checks du rapport vertes.
Reload1970-07-01, saved6/kept6/dropped0, matrice5 assertions et contrôle
live8 assertions avant/après Load. Cible recalculée et marges observées
12345/23456 préservées lors du refresh forcé, puis état de fixture restauré.
Source `results/c121_target_limit/visible_fused_reload_20261008/report.json`.
7 tests ciblés verts (décodeur corps entier2, redondances2, allocation3),
VM fusionnée compilée/exécutée et reload sain. Aucun état durable ajouté.

L'intégration est toujours dans les copies expérimentales du harnais. Restant :
porter proprement la capture dans le module métier partagé sans dupliquer le
modèle, garder un chemin témoin, refaire contrats/smoke du code livré ;
contrôler le coût du chemin OFF avant qualification et rating projeté des
sites neufs. Pas de défaut modifié, pas d'adoption ni commit/publication.

### Portage métier — plan avant mesure

Portage dans `air_economics_c121.nut` : paramètre optionnel de capture minimale
dans l'unique OpexC121AirEconomics, helper de cible/N/N+1 et replis fixes.
`c121_air_visible_fused=0` aux quatre difficultés, chargé seulement si le
flux visible est actif ; sélection locale dans le refresh. Ni duplication du
modèle ni nouvelle persistance. Le chemin OFF conserve les trois évaluations.
Le test nullable ajouté au scan partagé a un coût à mesurer même à OFF.

Contrats puis diagnostics copiés42×3,10CPU/8g/1worker :
`visible_port_off_20261008` compare corps pré-portage (copie figée du r2
précédent) et corps courant OFF ; `visible_port_on_20261008` compare courant
OFF/ON, mêmes entrées préparées, dates, caches et champs, oracle de sortie.
Les copies du modèle ancien restent seulement dans le diagnostic OFF.
Date/inputs différents exclus, toute divergence comparable arrête le test.
Save/Load sur code réellement livré et flag1 : `visible_port_reload_20261008`.
Smoke causal1×1 sur arbre commun visible1/fused0 contre visible1/fused1,
règle gain_short enregistrée pour compatibilité, sans verdict d'adoption.
Image/runtime/cache/contexte/containeurs contrôlés avant lancements.
Ces validations ne qualifient pas le flux visible par défaut et n'autorisent
aucune adoption du nouveau réglage ; aucun20×10 économique dans cette étape.

Premières copies portées saines : coût OFF+0,133 %/218 paires, ON−13,22 %/
329 paires. Les branches des corps de comparaison étaient forcées par booléen
littéral dans le harnais. Contrôle final du coût du portage : conserver le
test réel de réglage dans les corps et basculer seulement le réglage global
pour la référence, hors des compteurs. Sorties nouvelles
`visible_port_off_20261008_r2` et `visible_port_on_20261008_r2`, mêmes protocoles.
Mesures précédentes conservées ; comparaison finale fondée sur les branches
réellement livrées, sans changement du code IA ni du bundle du smoke lancé.

Contrôles finaux complets/sains, copies inchangées :

|Comparaison du corps complet|Cas comparables|Référence ops|Courant ops|Delta|
|---|---:|---:|---:|---:|
|Pré-portage→courant fused0|219|10612266|10626345|+14079 /+0,133 %|
|Courant fused0→fused1|339|15634562|13552351|−2082211 /−13,318 %|

OFF :659 devis,395 dates franchies/45 inputs différents exclus ; ON :878
devis,475 dates franchies/64 inputs différents exclus. Sorties identiques
sur tous les cas comparables. MoyenneON46119,65→39977,44opcodes. Capture
symétrique/logs inclus, restauration et comparaison exclues ; économies
sur sous-ensembles comparables, pas coût total de l'IA. Coût OFF mesuré avec
visible1, pas une mesure globale du profil livré visible0. Aucun cas naturel
à marge observée ; contrôle dirigé Save/Load ci-dessous.

Sources finales `results/c121_visible_flux_20261008/visible_port_off_analysis_r2.json`
et `visible_port_on_analysis_r2.json`. Logs18b3063edf8ce571f49fbd7693cd55beef799caabc2efd5783a7883cfd57b523
et6bd37bd269272b0a1e6f546848bcf14d319ee0b96d6f3fd10b3c33cca60bad22 ;
plans6ec91cd5ee1996b592faa0a9102086bbfb0753d46b21817d35371867f67c2140
et7b98a2f23d7ada39ee5d54b968c7ae722b9bae87e12a9ac1ab51cd0dcd301154.
Référence pré-portage vérifiée contre les hashes de sa copie figée originale.

Code livré Save/Load :26 sauvegardes, toutes checks vertes,18 assertions live
avant/après Load, réglage1 chargé, null-contract et deux profondeurs hors scan
comparées au modèle complet. Marges observées préservées, reload1970-07-01
saved5/kept5/dropped0. `results/c121_target_limit/visible_port_reload_20261008`.

Smoke causal `c121_visible_fused_port_smoke42_20261008` :deux duels sains,
game_oktrue, comparison_completetrue, verdictdiagnostic_only attendu,
adoption_sample_completefalse. Bundleddb2e194c13565be0a02d1fa96c1c53c0bd41b99796264dd0ea930b49426dc50,
manifest7417d78eb30987667455a9354698d7f6955fd62169b96773e06563d6f3dfd5b3.
91 tests ciblés verts, diff-check. Une campagne utilisateur concurrente a
été préservée ; diagnostics1worker sur le PC local, aucun conteneur tiers arrêté.

Portage expérimental livré localement, sans duplication du modèle ; nouveau
réglage0 et flux visible0 aux quatre difficultés. Géométrie locale reste un
prototype distinct non porté. Pas d'adoption ni qualification économique,
aucun commit/push. Prochaine étape du chantier flux : rating projeté des sites
neufs, puis qualification comportementale du flux ; qualification opcodes
distincte nécessaire pour adopter la fusion, sur un contrôle causal isolé.

### 40×6 — pré-enregistrement utilisateur avant lancement

Demande explicite du08/10 : lancer40×6 si Docker disponible. Disponible,
desktop-linux, imagef4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659,
cacheopenttd-lab-home, aucune campagne active au contrôle initial. Arbre local
modifié deHEAD36fa8c79a740a54632d34ce86aecd2f5639e9493, code réellement
exécuté figé par le lanceur courant avant chaque campagne. Aucun commit/push.

Intervention comportementale isolée :
référence `OpexAI[c121_air_visible_competition=0,c121_air_visible_fused=0]`,
variante `OpexAI[c121_air_visible_competition=1,c121_air_visible_fused=0]`.
Même arbre et AAAHogEx figés, autres réglages aux défauts courants,C1151.
La fusion n'est pas évaluée ici. Les changements locaux communs sont inclus
dans la provenance ; le verdict mesure le levier visible sur cet arbre,
pas une qualification économique de leur cumul ni une adoption automatique.

PorteA à horizon6ans explicitement autorisé avant mesure :40 graines canoniques
SEEDS_40, une répétition,80 duels, primaireprofit_year Opex variante−référence
à l'année terminale. gain_short/required-seeds40/required-years6/years6,
seuil relatif4 %, Wilcoxon exact bilatéralp<0,05, borne basseIC95 bootstrap
de la moyenne>0, gardecompany_value5 %, bootstrap20000/seed0 du harnais.
Profil local10CPU/8g/8gswap/10workers, montage dépôt et volume cache.
Budget82 parties :smoke causal42×1 (2), puis80 si smoke sain.
Télémétrie supplémentaire OFF. Exposition antérieure :allocation commune
nouveau site/hubs/renforts, diagnostic live et fixture de rival neuf documentés.
Rating projeté du site neuf reste à valider séparément ; lancement utilisateur
ne transforme pas cette hypothèse en preuve d'exactitude.

Campagnes neuves `c121_visible_flux_smoke_40x6_20261008` puis
`c121_visible_flux_porteA_40x6_20261008`. Résultats, manifeste et bundle gardés
dansresults. Aucune adoption ni relance favorable ; résultats bruts conservés,
20×10 uniquement après porteA complète/saine/pass et contrôle de comparabilité.

Smoke terminé :deux games complets/game_oktrue, verdictdiagnostic_only.
Manifest046c69684c15eb10c7e299f63de3d2a50b3efd6b62aa0826a1400680eee56fdb.
40×6 effectivement lancé :80 parties/40 graines/10workers, sortie
`results/c121_visible_flux_porteA_40x6_20261008.json`.
Bundle communddb2e194c13565be0a02d1fa96c1c53c0bd41b99796264dd0ea930b49426dc50,
manifestbd17d9dc742102aeeaebca1d83163c859010fed42fe119f4978a35c12421c88e.
Début d'exécution confirmé par le lanceur ; résultat final attendu, pas encore
de verdict. Defaults0 conservés. Session de lanceur80581 (identifiant transitoire).


### Clôture du 40×6 : gain non démontré

Campagne `c121_visible_flux_porteA_40x6_20261008` terminée : **80/80 parties saines, 40/40 paires**, comparaison et couverture complètes ; quatre trimestres valides pour chaque ligne terminale Opex. Aucun `failed_run`. Résultat brut : `results/c121_visible_flux_porteA_40x6_20261008.json`. Bundle et manifeste identiques au lancement. Une synthèse versionnée est conservée dans `evidence/review/c121_visible_flux_40x6_20261008_summary.json` : critères, résultats par graine, compteurs physiques terminaux et hashes des sources. Les JSONL, journaux moteur et bundle complets restent locaux dans `results/` ; cette synthèse dérivée ne les remplace pas.

| Mesure terminale Opex | Référence | Nouvel estimateur |
|---|---:|---:|
| Profit annuel moyen | 1 735 605 £ | 1 720 107 £ |
| Avions moyens | 84,2 | 81,7 |
| Aéroports moyens | 23,675 | 23,8 |

Delta de profit : **−15 498,55 £ (−0,892977 %)** ; médiane +11 727 £ ; V/D/E 21/19/0 ; Wilcoxon p=0,8471556244 ; IC95 bootstrap [−88 842,525 ; +55 407,95] £ (20 000 rééchantillonnages, graine 0). Valeur de compagnie : ratio des moyennes **+1,775847 %**, garde de −5 % tenue.

Verdict brut **`fail_primary`** : le gain requis n'est pas démontré ; aucune perte significative n'est démontrée non plus. La baisse du nombre d'avions ne suffit pas à établir leur meilleure rentabilité. Porte B non lancée, candidat maintenu à 0, aucune adoption. La comparaison reste conditionnelle au code commun figé ; elle ne qualifie pas les autres changements communs aux deux bras. Suite : analyser les bifurcations et le rating projeté des nouveaux aéroports/hubs ; aucune relance favorable.
