# Revue de code — réconciliation du 22 septembre 2026

Cette revue reprend le plan de 'docs/revue_code_2026-09-21_plan.md' et le rapport intégral
'docs/revue_code_2026-09-22_integrale.md', puis les confronte à l'état **courant** du dépôt.
Elle ne traite donc pas les findings du rapport intégral comme encore ouverts par défaut.

État lu pour cette passe :

- HEAD : 'a9f0f3c7469e0b157c68864c48f7fabafbeb6acf' ;
- working tree volontairement dirty, avec les intégrations C78/C83 et d'autres travaux concurrents ;
- revue en lecture seule sur le code, à l'exception du présent document ;
- aucun reset, nettoyage, commit ou lancement de campagne Docker.

Le but est double : réconcilier les findings déjà trouvés avec les correctifs du 22 septembre,
et vérifier que les changements C76/C77/C78/C80/C83 ainsi que leurs harnais n'introduisent pas
un nouveau défaut évident avant les prochaines mesures économiques.

## 1. Méthode — reprise des étapes proposées

Le plan du 21 septembre est suivi par familles, mais avec l'ordre de preuve actuel :

1. **chemin adopté au défaut** : portefeuille C69 bis/C70/C75, persistance, builders et cycle de vie ;
2. **sondes et chemins appelés depuis le défaut** : événements, diagnostics, erreurs et coûts cachés ;
3. **C80 / C76 / C77** : ordonnanceur, travailleurs reprenables, régénération et persistance ;
4. **harness de mesure** : contrat 'result_processor', corrélation C78, C83.2 et santé des lignes ;
5. **analyses** : cohérence des agrégats et absence de conclusion causale à partir d'un snapshot ambigu ;
6. **réconciliation** : état de chaque finding et ordre de traitement avant les prochains 20×10.

Le rapport intégral du matin reste l'inventaire exhaustif des lots lus. La présente passe relit
les zones modifiées depuis, les findings encore susceptibles d'être exposés, et les nouveaux
chemins C78/C83.

Résultat par étape : la persistance C69/C75 et le recalcul C70/C82 sont cohérents dans
'_reconcileAfterLoad' (les facteurs sont recalculés après 'this._lines = liveLines') ; les
findings du chemin adopté se concentrent désormais sur builders/cycle de vie. Les sondes gardent
les reliquats événements/sign ci-dessous. C80/C77 conserve deux problèmes de bornage, tandis que
le chemin AIR C78.4 est bien reprenable. Le harnais C78/C83 respecte le contrat d'itérable et
évite l'attribution causale intra-journée non observable.

## 2. Findings du rapport intégral maintenant corrigés

| Finding | État courant | Preuve relue |
|---|---|---|
| 'F-AIR-ORDER-01' | **corrigé** | 'builder_air.nut::OpexAirAddPlane' contrôle désormais 'AIOrder.ShareOrders', vend l'avion de repli si possible et retourne 'ORDER' avant tout démarrage. Le chemin multi-avions de 'OpexBuildAirRoute' ajoute aussi l'avion au rollback et retourne 'ORDFAIL' avant la boucle de démarrage. |
| 'F-AIR-ERR-01' | **corrigé** | 'OpexBuildAirRoute' mémorise l'erreur au moment du 'BuildAirport' et n'utilise ces champs que pour un aéroport réellement construit ; les branches 'HUB/HUBB' de réutilisation ne relisent plus un 'AIError' périmé. |
| 'F-RAIL-DEPOT-01' | **corrigé** | 'OpexBuildDepot' teste d'abord 'AIRail.BuildRailDepot' sous 'AITestMode' et 'AIAccounting', puis seulement démolit la tuile pour la construction réelle. |
| 'F-RAIL-ERR-01' | **corrigé** | 'OpexBuildTrains' contrôle chaque 'AppendOrder' immédiatement et capture l'erreur avant tout autre appel NoAI. |
| 'F-C77-CARGO-01' | **corrigé** | lors d'une régénération ciblée rail, le cargo fret de repli trouvé est copié dans 'projects.freightCargo' avant le mode route suivant. |
| 'F-DOC-DEPS-01' | **corrigé comme documentation historique** | l'en-tête de 'docs/architecture_opexai.md' indique explicitement que le schéma date du 13 septembre et que 'lib_water.nut', Queue et Lakes ont été retirés. Les graphes anciens restent présents, mais ne se présentent plus comme le runtime courant. |

Ces corrections sont couvertes par 'sweeps/test_review_residual_contracts.py'. La passe ciblée
du 22 septembre exécute également les tests C78/C83 : **38 tests sur 38 passent**.

Une limitation encore inscrite dans 'docs/taches.md' au début de la revue est également déjà
corrigée dans le code courant : sous C77 sans C76, un rebuild complet ne perd plus les candidats
de subvention. '_rebuildProjects' transmet 'this._activeSubsidies' à 'OpexBuildProjects' dès que
C77 est actif, et la génération complète rappelle 'OpexGenerateSubsidyCandidates'. Le contrat
'sweeps/test_c45_subsidy_persistence.py' vérifie cette transmission et la persistance :
**6 tests sur 6 passent**.

## 3. Findings encore ouverts

### 3.1 Haute priorité — atomicité et cycle de vie

#### 'F-ROAD-TXN-01' — rollback routier après démarrage partiel

**Sévérité : haute, chemin par défaut.**

'builder_road.nut::OpexRoadRollback' appelle 'AIVehicle.SellVehicle(v)' sur tous les véhicules,
puis retire dépôt, arrêts et routes sans vérifier le retour de la vente. Or
'OpexBuildRoadRoute' démarre les véhicules séquentiellement ; si un démarrage échoue après qu'un
véhicule précédent a démarré, le rollback peut tenter de vendre un véhicule qui n'est plus
vendable immédiatement puis démolir son infrastructure.

Le contrat transactionnel reste donc incomplet. La correction doit séparer les véhicules encore
vendables au dépôt des véhicules déjà partis, ou empêcher tout démarrage avant que la transaction
entière soit validée.

#### 'F-RAIL-START-01' — résultat de 'StartStopVehicle' ignoré

**Sévérité : haute, chemin par défaut.**

'OpexBuildTrains' démarre les trains par
'foreach (train in vehicles) AIVehicle.StartStopVehicle(train)' sans lire le booléen retourné.
Le chemin de construction initiale double voie fait la même chose après avoir construit les deux
consists. Une ligne peut donc être enregistrée comme construite alors qu'un train est resté arrêté.

#### 'F-RAIL-TXN-02' — second train : correction partielle seulement

**Sévérité : haute, chemin 'RAIL_REFLEET'.**

Le chemin de construction initiale à deux dépôts a été amélioré : si le deuxième
'OpexBuildTrains' échoue, ses 'rollbackVehicles' sont fusionnés avec ceux du premier avant
'OpexRollback'.

Le chemin postérieur 'OpexBuildSecondTrain', appelé depuis 'task_rail.nut::_expandRailLines',
reste différent : si 'OpexBuildTrains(..., startVehicles=true)' retourne 'failed', la fonction
retourne simplement 'TRAINFAIL' et perd la liste 'rollbackVehicles'. Un échec de wagon ou
d'ordre peut donc encore laisser du matériel dans 'depot2'.

#### 'F-LIFE-SCRAP-01' — une vente échouée est comptée comme réussie

**Sévérité : haute, chemin par défaut.**

Dans 'task_report.nut::_scrapDeadLines', un véhicule arrêté au dépôt est retiré de la liste
'remaining' juste après l'appel à 'AIVehicle.SellVehicle(v)', sans tester son retour. Si la
vente échoue, le véhicule disparaît du suivi et la ligne peut atteindre le critère 'all_sold'
alors qu'il existe encore.

### 3.2 Priorité moyenne — modèle et ordonnanceur

#### 'F-RAIL-ECON-01' — coût de dépôt absent du capital rail

**Sévérité : moyenne, chemin par défaut.**

'economy.nut::OpexLineEconomics' calcule encore :

~~~text
infraCost = travelDist * effectiveTrackCost + 2 * platformLength * catalog.costStation
~~~

Le coût du dépôt n'est pas inclus alors que le modèle route inclut explicitement
'catalog.costRoadDepot'. Le capital rail et son amortissement sont donc légèrement sous-estimés.
Ce finding ne justifie pas encore un changement de politique : il faut corriger le modèle puis
mesurer l'effet sur le classement.

#### 'F-C80-TOWN-01' — repli monolithique si le registre est occupé

**Sévérité : moyenne, conditionnelle à C80.**

Sous 'c80_worker_town=1', si '_activeWorker' contient un autre travailleur,
'_dispatchTownGrowth' retombe explicitement sur '_tryTownGrowth(year)'. Le pic d'opcodes que le
travailleur devait fractionner peut donc réapparaître précisément quand le registre est occupé.
Le contrat C80-4 reste de toute façon non atteint dans les mesures existantes.

#### 'F-C77-SLICE-01' — AIR est reprenable, rail/route restent monolithiques

**Sévérité : moyenne, conditionnelle à C77.**

C78.4 a corrigé une partie importante du finding : le mode AIR du travailleur
'regen_candidates' passe désormais par 'OpexRegenerateAirProjectsSlice', avec
'opsBudget', 'deadlineTick' et un curseur persistant entre tranches.

Les autres modes passent toujours par 'OpexRegenerateModeProjects' en un appel synchrone.
Un événement industrie ou moteur peut donc encore faire exécuter une régénération rail/route
monolithique dans le registre actif. La branche générique de '_runOrchestratorTick' retourne
ensuite sans faire avancer la file de fond pour ce tick.

Ce finding ne bloque pas le mécanisme C83.1 actuel, qui enfile uniquement le mode AIR, mais il
bloque une conclusion générale disant que C77 est entièrement borné par tranche.

### 3.3 Priorité basse à moyenne — robustesse et diagnostics

#### 'F-EVENT-BACKLOG-01' — la file d'événements est vidée sans quota

'events.nut::_processEvents' conserve un 'while (AIEventController.IsEventWaiting())' sans
budget local ni nombre maximal d'événements. Une rafale peut retarder l'ordonnanceur. Aucune
exposition pathologique n'est démontrée dans les bancs actuels ; le risque reste donc inférieur
aux findings transactionnels.

#### 'F-SIGN-01' — 'OpexSign' ne borne pas les noms à 31 caractères

'probes.nut::OpexSign' transmet encore 'name' directement à 'AISign.BuildSign'. Les formats
actuels sont généralement courts, mais le helper commun ne protège pas la limite NoAI de
31 caractères.

#### 'F-TEST-01' — dette de tests toujours réelle

Deux tests historiques échouent encore et leurs causes sont confirmées :

- 'test_b8_scrap_lifecycle.py::test_feeder_recovery_clears_old_scrap_timer' cherche
  'FEEDER_RECOVER', supprimé avec les feeders ;
- 'test_review_evidence.py::test_index_covers_every_cited_review_result' constate que
  'evidence/review/index.json' et la liste courante de résultats cités ont divergé.

Ils ne doivent pas être masqués dans une validation globale ; il faut soit retirer le contrat
obsolète feeder, soit le remplacer par le contrat de cycle de vie encore vivant, et régénérer
l'index de preuves avec le mécanisme prévu par 'package_review_evidence.py'.

## 4. Nouveaux chemins C78/C83 relus

### 4.1 Course défensive C83.1

'task_projects.nut::_c83WatchAirSlotTransitions' est placé au début de
'_tryBuildProjects', avant les dépenses ordinaires. Lorsqu'un passage de deux slots restants à
un seul est détecté et qu'aucun projet AIR déjà financé ne couvre la ville, il enfile une
régénération C77 ciblée sur cette seule ville puis rend la main. Le projet défensif déjà présent
peut être remonté en tête par 'OpexPromoteLiveDefensiveAir' ; un rail calculé mais pas encore
construit peut céder une passe.

Les gardes sont cohérentes avec le signal retenu : C77 doit être actif,
'economy.station_noise_level == 0' et le conseil municipal ne doit pas être dans le mode qui
lève la limite. Au défaut C77=0, le watcher n'est pas activé.

**Limite de couverture à mesurer, pas bug de correction :** 'OpexAirC83WatchTowns' ne surveille
que les 'AIR_EARLY_SLOT_TARGET_TOWNS' plus grandes villes admissibles, soit **6 villes au
réglage courant**. L'exposition C83 a été mesurée sur un ensemble plus large. Le 5×6 doit donc
publier combien de transitions concurrentes pertinentes tombent réellement dans ces six villes,
combien déclenchent la régénération, et combien aboutissent à un aéroport Opex avant fermeture du
slot. Il ne faut pas déduire de la correction seule qu'elle couvre les monopoles top-24.

### 4.2 Tranchage AIR C78.4

'OpexRegenerateAirProjectsSlice' conserve 'plans', 'airCursor' et le coût mesuré dans l'état
du worker. 'OpexAirPlans' reçoit le budget d'opcodes et l'échéance puis la fonction retourne
'running' tant que le curseur n'est pas terminé. Le contrat est cohérent avec la correction
C78.4 ; aucun retour au scan exhaustif AIR n'a été trouvé dans ce chemin.

### 4.3 Harnais C78/C83

La relecture de 'sweeps/diag_1v1_shared_monthly.py' ne montre pas de corruption du contrat
'result_processor' : 'keep()' retourne bien des **tuples**, deux lignes en partie partagée et
un tuple singleton en solo.

La corrélation C78 utilise les 'build_date' des stations AAAHogEx et refuse de présenter comme
réaction causale un log Opex du même jour, car le snapshot ne donne pas l'ordre intra-journée.
Elle prend le premier passage 'projects' strictement postérieur, puis corrèle candidats,
tentatives, outcomes et raisons d'arrêt par 'pass/cycle/tick'. Cette précaution évite le biais
principal qui avait été signalé pendant la tranche 2.

L'analyse C83.2 relie chaque mesure de droits au premier snapshot à la date ou après et filtre les
aéroports par leur date de construction. Aucun nouveau défaut bloquant n'a été trouvé dans les
portions modifiées du harnais.

## 5. Documentation/protocole : une incohérence nouvelle

### 'F-DOC-C81-01' — libellé C81 obsolète dans la fiche de commandes

**Sévérité : basse, mais susceptible de faire lancer le mauvais bras.**

'docs/20_nuit_2026-09-22.md' corrige explicitement la prémisse : AAAHogEx applique le plein
chargement aux **deux** extrémités en AIR, ce qui correspond à 'air_full_load=1'.
'docs/13_banc_c69_20x10_pc.md' §9 contient encore un libellé qui décrit
'air_full_load=2' comme « comme AAAHogEx ». Les commandes elles-mêmes exposent bien les deux
valeurs, mais ce commentaire ne doit plus guider le choix d'un banc.

De plus, C82 est déjà clos en échec au 20×10 du 22 septembre et ne doit pas être relancé, même si
la fiche de nuit historique le présente encore comme le candidat prioritaire. 'docs/taches.md'
et le journal du 22 font foi.

## 6. Validation exécutée pendant cette revue

~~~text
python -X utf8 -m unittest
  sweeps.test_review_residual_contracts
  sweeps.test_c78_air_candidate_hygiene
  sweeps.test_c78_slot_intercept_probe
  sweeps.test_c77_air_defensive_slot
  sweeps.test_c83_exclusive_rights_probe

38 tests, OK.
~~~

Contrat subventions C77 :

~~~text
python -X utf8 -m unittest sweeps.test_c45_subsidy_persistence

6 tests, OK.
~~~

Puis la dette connue :

~~~text
python -X utf8 -m unittest
  sweeps.test_b8_scrap_lifecycle
  sweeps.test_review_evidence

9 tests : 1 erreur + 1 échec.
- FEEDER_RECOVER absent du code courant ;
- index de preuves désynchronisé de package_review_evidence.cited_results().
~~~

Aucune partie OpenTTD n'a été lancée pour cette revue documentaire. Le smoke C77/C78 déjà
consigné dans 'docs/taches.md' reste la preuve moteur courante ; la prochaine preuve nécessaire
pour la course défensive est le 5×6 apparié.

## 7. Bancs 20×10 à envisager pendant une nuit

Le dépôt a déjà un 20×10 **C77 seul** et un 20×10 **C82** terminés le 22 septembre ; les relancer
à l'identique n'apporterait pas d'information. C80 est techniquement lançable, mais pas encore
propre pour un **banc d'adoption** : le worker town garde un fallback monolithique, sa tranche
dépasse encore largement la borne visée, et le coût des workers n'est pas encore complètement
attribué par la sonde. C78/C83.1 a ses paramètres 20×10 enregistrés ci-dessous, avec le 5×6
apparié conservé comme étape de qualification préalable. C67 n'est pas encore implémenté.

Les campagnes suivantes ont en revanche des hypothèses distinctes. Les seuils sont fixés avant
lecture : 'profit_year' primaire, au moins 15/20 signes positifs avec p bilatéral < 0,05,
delta moyen minimal +50 k£/an et garde de valeur d'entreprise à −5 %.

### N1 — pile C76 + mémo contre le défaut courant

**Priorité : la plus forte des 20×10 actuellement disponibles.**

Hypothèse : C76 évite les régénérations complètes inutiles et le mémo supprime les replanifications
géométriques répétées de 'town_growth' ; les deux économies d'opcodes portent sur des goulots
différents et peuvent augmenter le débit réel de projets.

~~~text
rtk proxy python -X utf8 sweeps/run_c66_reference.py --campaign c76_tgmemo_vs_default_10y_20seeds_20260922 --policy-id default --reference "OpexAI" --variant "OpexAI[c76_regen_targeted=1,town_growth_plan_memo=1]" --variant-policy-id c76_tgmemo --primary-metric profit_year --min-useful-primary-delta 50000 --value-guard-max-loss-pct 5 --years 10 --max-workers 3 --cpus 3 --memory 2g
~~~

Ce banc répond directement à la question économique de la pile finale, mais il n'attribue pas
seul le gain éventuel à C76 ou au mémo.

### N2 — contribution propre du mémo sur C76

**Priorité : forte si N1 est lancé.**

Hypothèse : à C76 identique des deux côtés, 'town_growth_plan_memo' réduit le coût répété sans
perdre des constructions devenues possibles. Cette comparaison isole le mémo.

~~~text
rtk proxy python -X utf8 sweeps/run_c66_reference.py --campaign tgmemo_on_c76_vs_c76_10y_20seeds_20260922 --policy-id c76 --reference "OpexAI[c76_regen_targeted=1]" --variant "OpexAI[c76_regen_targeted=1,town_growth_plan_memo=1]" --variant-policy-id c76_tgmemo --primary-metric profit_year --min-useful-primary-delta 50000 --value-guard-max-loss-pct 5 --years 10 --max-workers 3 --cpus 3 --memory 2g
~~~

### N3 — C76 seul contre le défaut courant

**Priorité : moyenne ; utile pour attribuer N1.**

Le 20×10 C77 seul existe, mais pas le même verdict d'autorité pour C76 seul sur la référence
courante. Ce banc mesure si l'économie de régénération de C76 se traduit à elle seule en économie
réelle face à AAAHogEx.

~~~text
rtk proxy python -X utf8 sweeps/run_c66_reference.py --campaign c76_vs_default_10y_20seeds_20260922 --policy-id default --reference "OpexAI" --variant "OpexAI[c76_regen_targeted=1]" --variant-policy-id c76 --primary-metric profit_year --min-useful-primary-delta 50000 --value-guard-max-loss-pct 5 --years 10 --max-workers 3 --cpus 3 --memory 2g
~~~

### N4 — C81 'air_full_load=1', seulement comme confirmation négative

**Priorité : basse.**

La mesure solo était très défavorable. Si une preuve de duel est néanmoins souhaitée, la variante
qui reproduit le comportement AIR observé chez AAAHogEx est 'air_full_load=1' (plein chargement
aux deux extrémités), pas le libellé obsolète associé à la valeur 2 dans la fiche de commandes.

~~~text
rtk proxy python -X utf8 sweeps/run_c66_reference.py --campaign c81_fullload1_vs_default_10y_20seeds_20260922 --policy-id default --reference "OpexAI" --variant "OpexAI[air_full_load=1]" --variant-policy-id c81_fl1 --primary-metric profit_year --min-useful-primary-delta 50000 --value-guard-max-loss-pct 5 --years 10 --max-workers 3 --cpus 3 --memory 2g
~~~

### N5 — C78/C83.1, course défensive au second slot

**Priorité : forte après le 5×6 apparié.**

Le bras fonctionnel est simplement 'c77_opportunistic_candidates=1'. Le chargement des réglages
fait alors automatiquement 'C80_DOUBLE_REGISTER = true', donc il ne faut pas ajouter
'c80_double_register=1' dans le bras. Sur le code courant, ce même réglage C77 porte désormais
la course défensive C78/C83.1 : surveillance du slot restant, régénération AIR ciblée et priorité
lexicographique avant les dépenses ordinaires. Ce 20×10 est donc **distinct** du vieux 20×10 C77
du 22 septembre, qui mesurait le code antérieur à cette course défensive.

Paramètres d'adoption : référence = défaut courant ; variante =
'OpexAI[c77_opportunistic_candidates=1]' ; métrique primaire = 'profit_year' ; seuil utile
+50 k£/an ; garde de valeur = −5 % ; 20 graines canoniques × 10 ans ; 3 workers / 3 CPU / 2 Go.
Les sondes C78 restent désactivées dans le banc d'adoption pour ne pas modifier la cadence.

~~~text
rtk proxy python -X utf8 sweeps/run_c66_reference.py --campaign c78_c83_slot_race_vs_default_10y_20seeds_20260922 --policy-id default --reference "OpexAI" --variant "OpexAI[c77_opportunistic_candidates=1]" --variant-policy-id c78_c83_slot_race --primary-metric profit_year --min-useful-primary-delta 50000 --value-guard-max-loss-pct 5 --years 10 --max-workers 3 --cpus 3 --memory 2g
~~~

### N6 — C80 exploratoire, pile ordonnanceur utile

**Priorité : moyenne ; diagnostic économique, pas verdict d'adoption.**

Bras exploratoire retenu : double registre + workers rail/ville + C76 + mémo de planification
urbaine + régénération par mode + index AIR hub. 'c80_air_choice_memo' est volontairement exclu :
le solo 3×10 l'a déjà montré défavorable et son choix d'avion peut devenir périmé.

La comparaison se fait contre le défaut courant pour répondre à une question simple : est-ce que
la pile C80 qui réduit réellement les gros coûts d'ordonnancement et de régénération améliore aussi
le résultat économique en duel ? Le résultat reste **exploratoire** tant que le fallback
'town_growth' monolithique, la borne par tranche et l'attribution des opcodes travailleurs ne sont
pas corrigés. Les mêmes seuils économiques sont calculés pour rendre le banc comparable aux autres
20×10, mais ils ne valent pas à eux seuls adoption de C80.

Paramètres : référence = défaut courant ; variante =
'OpexAI[c80_double_register=1,c80_worker_rail=1,c80_worker_town=1,c76_regen_targeted=1,town_growth_plan_memo=1,c80_mode_regen=1,c80_air_hub_index=1]' ;
20 graines canoniques × 10 ans ; 'profit_year' primaire ; seuil utile +50 k£/an ; garde de valeur
−5 % ; 3 workers / 3 CPU / 2 Go.

~~~text
rtk proxy python -X utf8 sweeps/run_c66_reference.py --campaign c80_exploratory_stack_vs_default_10y_20seeds_20260922 --policy-id default --reference "OpexAI" --variant "OpexAI[c80_double_register=1,c80_worker_rail=1,c80_worker_town=1,c76_regen_targeted=1,town_growth_plan_memo=1,c80_mode_regen=1,c80_air_hub_index=1]" --variant-policy-id c80_exploratory_stack --primary-metric profit_year --min-useful-primary-delta 50000 --value-guard-max-loss-pct 5 --years 10 --max-workers 3 --cpus 3 --memory 2g
~~~

Ces campagnes doivent être lancées **séquentiellement** sur le profil VPS actuel : la limite du
dépôt interdit plusieurs campagnes Docker simultanées, même si chaque conteneur est plafonné.

## 8. Bancs à ne pas lancer encore

- **C78/C83.1** : paramètres 20×10 consignés en N5, mais faire d'abord le 5×6 apparié déjà dû ;
  vérifier exposition du watcher top-6, déclenchements, constructions défensives, santé et effet
  économique avant de lire N5 comme un banc d'adoption.
- **C80 workers** : le 20×10 exploratoire est consigné en N6 et peut être lancé comme diagnostic ;
  traiter le fallback monolithique town-growth et mesurer les vrais opcodes du worker avant
  d'utiliser un 20×10 comme verdict d'adoption.
- **C77 seul** : 20×10 déjà terminé et non adopté.
- **C82** : 20×10 déjà terminé, verdict 'fail_primary'.
- **C67** : implémentation absente ; le protocole prévoit les étapes de diagnostic avant le 20×10.
- **C83.2 droits exclusifs** : mécanisme mesuré trop coûteux au début de partie et non retenu.

## 9. Ordre de correction conseillé après la revue

L'ordre technique reste dicté par les risques de corruption d'état, puis par la qualification des
expériences : 'F-ROAD-TXN-01', 'F-RAIL-START-01', 'F-RAIL-TXN-02',
'F-LIFE-SCRAP-01', puis 'F-RAIL-ECON-01'. Ensuite viennent
'F-C80-TOWN-01' et le reliquat 'F-C77-SLICE-01', qui conditionnent les conclusions
architecturales sur C80/C77. Les findings événements/sign/tests/docs peuvent être traités en lots
plus petits après les chemins transactionnels.

La course défensive C83.1 n'a pas besoin d'attendre ces corrections pour son **5×6** : son chemin
AIR ciblé est désormais tranché et ses tests passent. Son 20×10, lui, doit attendre le résultat
du 5×6 conformément au protocole du dépôt.
