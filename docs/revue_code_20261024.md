# Revue de code OpexAI — 24 octobre 2026

## Périmètre et méthode

Référence : **/openttd-ml, master/origin/master, commit c03fce93afc16cf86d2e36bb43d9f6dba8b4667d**, contenant les nettoyages et les optimisations AIList L3 à L6. Le comptage actuel de ai/OpexAI/info.nut est **58 AddSetting**. Le WIP antérieur (41031a7f) est archivé dans backup/local-wip-20261024 et n'a pas servi de base aux constats.

Audit **statique et en lecture seule** du code Squirrel : recherche des déclarations, appels et lecteurs avec rg sur ai/OpexAI, revue de la chaîne de chargement, de Save/Load, des réglages et sondes, des deux boucles principales et des listes natives. Aucun .nut modifié, aucun test, banc ou Docker lancé, aucun commit. Les conséquences probables sont distinguées des reproductions expérimentales absentes.

**Bilan : 12 constats, dont 1 critique, 2 majeurs et 9 mineurs.**

## Critique

### R01 — Omission de la projection avant Save dans la boucle profilée

**Fichiers/lignes :** ai/OpexAI/main.nut:778,793-804 ; ai/OpexAI/probes.nut:2695-2725 ; ai/OpexAI/persist.nut:564-585,650-674 ; ai/OpexAI/settings.nut:197-199.

**Preuve :** lorsque PROBE_LOOP_OPS est armé (bit dédié 2048 ou groupe 8), Start appelle OpexAI::_mainLoopProfiled. La boucle normale appelle OpexAI::_refreshSaveProjection après les événements dès 64 lignes (main.nut:798-802). La boucle profilée passe directement des événements à OpexC117AirThroughputStep (probes.nut:2713-2725). Recherche vérifiée : **rg -n '_refreshSaveProjection|SAVE_PROJECTION_MIN_LINES|_mainLoopProfiled' ai/OpexAI -g '*.nut'** ; il n'existe qu'un appel à la projection, main.nut:800.

**Impact :** Save complet projette à la volée toutes les lignes faute de cache (persist.nut:656-674). Le commentaire de persist.nut:564-567 rapporte une précédente mort du script vers 150 lignes par dépassement de la limite fixe de 100 000 opcodes de Save. Une campagne instrumentée avec flotte importante peut donc perdre la capacité de sauvegarder, et son coût diffère de la boucle courante. Le défaut ordinaire probes=2 ne bascule pas vers cette boucle.

**Correction proposée :** reproduire le bloc de projection/annulation dans _mainLoopProfiled exactement entre événements et C117, et mesurer son coût dans une rubrique propre. Vérifier par contrat la parité des deux boucles, puis Save/Load sur grande flotte lors d'une phase autorisant les exécutions.

## Majeur

### R02 — Le cache V276 des cargos reste périmé après modification des industries

**Fichiers/lignes :** ai/OpexAI/candidates_v276.nut:23-47,74-103 ; ai/OpexAI/candidates.nut:37-39 ; ai/OpexAI/catalog.nut:939-979 ; ai/OpexAI/event_handlers.nut:388-408 ; ai/OpexAI/orchestrator.nut:892-921 ; ai/OpexAI/settings.nut:446-450.

**Preuve :** OpexV276CargoOrder valide le cache seulement par l'année et ne réécrit V276_CARGO_YEAR/V276_CARGO_ORDER qu'à son calcul (candidates_v276.nut:25-47). OpexV276AddUnits, OpexV276Start et OpexFreightCargoOrder le lisent. Le catalogue reconstruit ses producteurs à l'ouverture d'une industrie (event_handlers.nut:407) et au rafraîchissement rail/route (orchestrator.nut:911,921), sans invalider ces variables. Recherche vérifiée : **rg -n 'V276_CARGO_ORDER|V276_CARGO_YEAR|OpexV276CargoOrder|_refreshIndustries' ai/OpexAI -g '*.nut'** ; seules les écritures de candidates_v276.nut et l'initialisation settings.nut:449-450 apparaissent.

**Impact :** une catégorie de cargo introduite pendant l'année peut être exclue des nouvelles unités V276 jusqu'à janvier ; le classement calculé sur la production mensuelle en mode 2 reste lui aussi figé. V276=2 est actif automatiquement sur les cartes d'au moins 1024×1024 cases (settings.nut:446-447 et réglage v276_cand_slices dans info.nut).

**Correction proposée :** invalider à chaque reconstruction des industries, ou utiliser une révision du catalogue dans la clé du cache ; pour la composante de volume mensuel, définir une actualisation mensuelle. Préserver l'ordre déterministe et le coût borné.

### R03 — Une invalidation du cache de sauvegarde est ignorée jusqu'au mois suivant

**Fichiers/lignes :** ai/OpexAI/persist.nut:571-585,656-674 ; ai/OpexAI/task_v257.nut:538,622 ; ai/OpexAI/task_v284.nut:357,490 ; ai/OpexAI/main.nut:798-802.

**Preuve :** _refreshSaveProjection retourne immédiatement si le mois courant correspond à _saveProjectionMonth (persist.nut:579), même lorsque _saveProjection vaut null. Or les transactions de flotte V257 et V284 invalident explicitement _saveProjection (quatre sites ci-dessus) mais ne réinitialisent jamais le mois. Recherche vérifiée : **rg -n '_saveProjection\s*=|_saveProjectionMonth\s*=' ai/OpexAI -g '*.nut'** ; les seules écritures du mois sont l'initialisation à -1 (main.nut:139) et le changement de mois (persist.nut:580).

**Impact :** même dans la boucle normale, une mutation après le premier rafraîchissement du mois laisse le cache nul jusqu'au changement de mois. Save projette alors toutes les lignes dans son budget fixe de 100 000 opcodes (persist.nut:661-674), avec risque de dépassement pour les grandes flottes. Le problème existe indépendamment de R01 ; rétablir la projection dans la boucle profilée ne suffit pas.

**Correction proposée :** remplacer la garde par une condition vérifiant aussi la présence du cache (même mois **et** _saveProjection non nul), ou invalider simultanément _saveProjectionMonth à chacun des quatre sites. Conserver la sémantique d'actualisation mensuelle des champs scalaires et vérifier le scénario mutation → Save au cours du même mois quand les tests seront autorisés.

## Mineurs

### R04 — Cache de surveillance C83 jamais élagué quand une ville quitte le top K

**Fichiers/lignes :** ai/OpexAI/air_towns.nut:168-190 ; ai/OpexAI/task_projects.nut:605-632,634-691 ; ai/OpexAI/main.nut:365,387.

**Preuve :** OpexAirC83WatchTowns recalcule les six villes surveillées ; _c83WatchAirSlotTransitions fait un rawset par ville mais ne retire aucune ville sortie du classement. Recherche : **rg -n '_c83SlotWatch|OpexAirC83WatchTowns' ai/OpexAI -g '*.nut'** ; aucune suppression de clé après initialisation.

**Impact :** le champ previous d'une ville réadmise peut dater d'une observation ancienne ; certaines transitions intermédiaires ou fins d'observation C122 ne sont plus traçables correctement. Cas de permutation de la cohorte, non reproduit.

**Correction proposée :** élaguer les villes sorties après avoir clos leurs observations de menace, et initialiser explicitement l'état des nouvelles entrées. Vérifier sur un changement contrôlé d'ordre des populations.

### R05 — Tri natif V276 effectué sur toutes les paires avant le plafond de 500

**Fichiers/lignes :** ai/OpexAI/candidates_v276.nut:10-11,237-277,338-355.

**Preuve :** OpexV276Enumerate accumule les paires avec s.pairs.AddItem (:277), puis appelle s.pairs.Sort (:250). V276_EVAL_CAP=500 est utilisé seulement pendant la phase evaluate (:339,354). Recherche : **rg -n 'V276_EVAL_CAP|s\.pairs\.(AddItem|Sort|Count)' ai/OpexAI/candidates_v276.nut**.

**Impact :** mémoire et coût du tri liés à toutes les paires admissibles, potentiellement nombreuses sur 1024², alors que seules 500 paires sont évaluées. La boucle d'énumération est budgétée ; le tri final natif reste global. **Risque de budget d'opcodes non mesuré**, pas un dépassement prouvé.

**Correction proposée :** mesurer la taille maximale de la liste et le coût du tri ; envisager une présélection bornée des 500 premiers rangs en conservant la priorité et le départage exacts.

### R06 — Canal V309 seul : coût de la sonde sans journal

**Fichiers/lignes :** ai/OpexAI/settings.nut:58,92-93 ; ai/OpexAI/main.nut:779-780,851-853 ; ai/OpexAI/probes.nut:2452-2454,2532-2550.

**Preuve :** le bit 26 arme V309_IDLE_PROBE, mais DECISION_LOG ne dépend que du masque 508. OpexV309IdleBegin/Tick travaillent, puis OpexV309IdleFlush retourne immédiatement si DECISION_LOG est faux. Recherche : **rg -n 'V309_IDLE_PROBE|OpexV309Idle(Flush|Begin|Tick)|DECISION_LOG = ' ai/OpexAI -g '*.nut'**.

**Impact :** probes=67108864 instrumente sans produire de rapport ; il faut également le bit 256 ou un groupe historique. Le commentaire probes.nut:2453 le précise déjà ; problème d'ergonomie/contrat plutôt que collision de bits.

**Correction proposée :** documenter clairement la double exigence dans info.nut, ou permettre à V309 d'émettre son seul bilan sous son bit dédié.

### R07 — Chemins de compatibilité toujours morts et cinq affectations identiques

**Fichiers/lignes :** ai/OpexAI/globals_pre.nut:198,211 ; ai/OpexAI/settings.nut:253-255,455-456 ; lecteurs dans ai/OpexAI/builder_water.nut:78,129,434,535, ai/OpexAI/candidates.nut:721,749 et ai/OpexAI/rail_prep_c121.nut:53,66.

**Preuve :** OPEX_ECONOMY_OPCODE_COMPAT_FALSE est exclusivement initialisé à false ; WATER_OPCODE_COMPAT_FALSE est réassigné false à cinq endroits, sans écriture true. Recherches : **rg -n 'OPEX_ECONOMY_OPCODE_COMPAT_FALSE|WATER_OPCODE_COMPAT_FALSE' ai/OpexAI -g '*.nut'** et **rg -n '(OPEX_ECONOMY_OPCODE_COMPAT_FALSE|WATER_OPCODE_COMPAT_FALSE)\s*(<-|=)' ai/OpexAI -g '*.nut'**.

**Impact :** branches alternatives, tests vides et redondances sans lecteur actif possible.

**Correction proposée :** dédupliquer d'abord les affectations ; supprimer les branches gelées au terme d'un lot de nettoyage avec adaptation des contrats éventuellement attachés.

### R08 — Générateur PO01C de cargos non appelé

**Fichier/lignes :** ai/OpexAI/po01c_generators.nut:671-683.

**Preuve :** **rg -n '\bOpexPO01CCargos\b' ai/OpexAI -g '*.nut'** ne renvoie que la définition. Les régénérations effectives passent par d'autres générateurs du module et par po01c_regen.nut.

**Impact :** fonction de maintenance inutilisée qui réplique la découverte des cargos.

**Correction proposée :** supprimer après vérification des fixtures externes ou intégrer explicitement un helper partagé tout en conservant les checkpoints de PO01C.

### R09 — Trois helpers du runtime ne sont jamais appelés

**Fichiers/lignes :** ai/OpexAI/air_towns.nut:151-159 (OpexAirV95CompetitorSecondSlotOpen), ai/OpexAI/builder_road.nut:580 (OpexRoadTryJoinStop), ai/OpexAI/task_rail.nut:2311-2314 (OpexV131KeepStructures).

**Preuve :** **rg -n 'OpexAirV95CompetitorSecondSlotOpen|OpexRoadTryJoinStop|OpexV131KeepStructures' ai/OpexAI -g '*.nut'** ne renvoie que les définitions. Le chemin V131 effectif invoque directement OpexV131RebuildStructures (task_rail.nut:2588). Certains helpers sont référencés par des tests ou des documents historiques.

**Impact :** surface de code et API de tests potentiellement trompeuses, aucun coût runtime établi.

**Correction proposée :** qualifier les interfaces volontairement maintenues par tests ; éliminer les autres après mise à jour explicite de ces contrats.

### R10 — Constantes sans lecteur et prototype de méthode sans réalisation

**Fichiers/lignes :** ai/OpexAI/main.nut:33-34 (RAIL_EXPAND_STREAK, RAIL_EXPAND_UTIL_PERMILLE), :41 (CASH_RESERVE_STATIC), :503 (_logC48IncrementalLedger).

**Preuve :** **rg -n 'RAIL_EXPAND_STREAK|RAIL_EXPAND_UTIL_PERMILLE|CASH_RESERVE_STATIC|_logC48IncrementalLedger' ai/OpexAI -g '*.nut'** ne retourne que ces déclarations : aucun appel à la méthode ni lecteur des constantes.

**Impact :** contrats supposés mais inactifs, risque de confusion lors d'une future modification.

**Correction proposée :** retirer ou annoter explicitement comme interfaces historiques, sans changer les paramètres opérationnels voisins.

### R11 — Neuf duplications du tri des types de ponts

**Fichiers/lignes :** ai/OpexAI/builder_rail.nut:2033-2034,2889-2890,3617-3618,3659-3660,3812-3813,4579-4580,4631-4632 ; ai/OpexAI/task_rail.nut:1703-1704 ; ai/OpexAI/task_v259.nut:241-242.

**Preuve :** **rg -n 'bridges\.Valuate\(AIBridge.GetMaxSpeed\)|bridges\.Sort\(AIList.SORT_BY_VALUE' ai/OpexAI -g '*.nut'** donne neuf paires Valuate(GetMaxSpeed) puis Sort(VALUE, descending).

**Impact :** maintenance en neuf lieux du même prétri ; les listes de types de ponts sont petites et aucun coût problématique n'a été mesuré.

**Correction proposée :** unifier uniquement si un helper conserve les gardes locales de constructibilité, le prix, la vitesse et les égalités ; une règle documentée commune peut suffire.

### R12 — L3 et PO01C conservent deux sélections du rail maximal

**Fichiers/lignes :** ai/OpexAI/catalog.nut:403-414 (tri natif L3), ai/OpexAI/po01c_generators.nut:639-652 (scan par ID et yield), ai/OpexAI/probe_v307.nut:403-411 (scan diagnostic).

**Preuve :** **rg -n 'AIRailTypeList|AIRail.IsRailTypeAvailable|SORT_BY_ITEM|chosen = -1' ai/OpexAI/catalog.nut ai/OpexAI/po01c_generators.nut ai/OpexAI/probe_v307.nut** montre trois implémentations qui prennent le plus grand ID disponible ; PO01C possède un checkpoint par type.

**Impact :** duplication d'une règle sensible à l'ordre des AIList. Aucun défaut de décision L3 prouvé ; remplacer automatiquement PO01C par un tri pourrait casser sa granularité de reprise.

**Correction proposée :** documenter la règle commune et conserver les checkpoints de PO01C lors d'une éventuelle mutualisation.

## Résultats négatifs et limites

- Aucune référence active identifiée aux états supprimés _v233*, _v294Deferred/_v294Ready, _c83Preempt* ; aucune collision entre bits dédiés de sondes démontrée. Le mode V309 de R06 est une dépendance de journal, pas une collision. Les 58 réglages déclarés dans info.nut correspondent aux 58 noms distincts consultés par GetSetting dans settings.nut.
- Le seul module .nut non inclus dans la chaîne de chargement runtime est terrain_valuate.nut, utilisé intentionnellement dans des fixtures de terrain : **aucun require manquant confirmé**.
- Lecture statique des conversions AIList : L3 catalog.nut:403-414 ; L4 task_v257.nut:201-219 ; L5 catalog.nut:609-615 ; L6 task_v284.nut:36-53. Leurs filtres métier, comparateurs et choix semblent préservés ; **aucun bogue propre à L3–L6 confirmé**. Le journal docs/opcode_ailist_lots_20261023.md contient les validations antérieures, sans preuve universelle sur tous les NewGRF.
- R04 à R06 représentent des conséquences conditionnelles ou risques à valider, sans incident reproduit. R01 et R03 présentent un risque de dépassement du budget Save démontré structurellement, sans nouvelle reproduction expérimentale. Aucune nouvelle mesure n'a été faite au cours de cet audit.

**Ordre de correction conseillé : R01 et R03 (persistance), puis R02 (génération des cargos).** Les autres constats relèvent d'un lot de maintenance séparé, avec conservation des contrats de sélection, de reprise et des tests.
