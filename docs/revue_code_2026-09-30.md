# Revue de code OpexAI — 2026-09-30

> Mise à jour après la revue : R1/R2/R3/R4/R5/R18/R19/R20/R21/R22/R23/R24/R25/R26
> sont implémentés localement, **sans validation par exécution** ;
> les autres constats ne sont pas réputés corrigés. Voir les sections finales et le
> [journal du 30 septembre](journaux/journal_2026-09-30.md).
> Les constats et numéros de ligne des revues ci-dessous décrivent l'état inspecté
> avant ces modifications ; ils sont conservés comme historique, pas comme état résolu.

## Objectif et portée

Améliorer le profit, la vitesse de construction et les décisions d'OpexAI en duel
contre AAAHogEx sur carte partagée.

Revue statique du checkout local téléchargé depuis la branche `c121-catalog`,
centrée sur AIR, le portefeuille, l'ordonnancement et la persistance. Ce n'est
pas un audit exhaustif des modes rail, route et eau. Le checkout provient d'une
archive ZIP, sans historique Git local ; aucun SHA exact n'a été établi pendant
cette revue. Les numéros de ligne ci-dessous sont ceux du code inspecté.

- Aucun code modifié et aucun test ou benchmark exécuté pendant la revue.
- Le code source d'AAAHogEx est absent de ce checkout : pas de comparaison
  directe des deux implémentations.
- Les effets économiques décrits sont des conséquences attendues des mécanismes,
  pas des gains mesurés ni une preuve de victoire contre AAAHogEx.
- Les défauts et décisions ont été confrontés à `info.nut`, `settings.nut` et
  à l'état courant de [taches.md](taches.md).
- **Conserver C115 inchangé**, conformément à la décision courante.
- Ce rapport n'adopte aucun traitement et ne remplace pas `docs/taches.md`, seule
  liste autoritaire du travail restant.

## Synthèse

| Référence locale | Priorité | Constat | Exposition |
|---|---|---|---|
| R1 | P2 | Renfort de flotte financé tout ou rien malgré un achat unitaire possible | Défaut |
| R2 | P2 | Calibration du modèle appliquée à nouveau au profit de flotte observé | Défaut, dès que le facteur C70 diffère de 1 |
| R3 | P2 | Plan AIR caduc consommant l'unique dépassement de `K_pass` | Défaut, après un premier chantier dans la passe |
| R4 | P2 | Continuation du catalogue C121 inaccessible au budget documenté | Expérimental, défaut désactivé |
| R5 | P2 | Autotests de démarrage effaçant le travail restauré | Défaut, au rechargement |

Les identifiants R1–R5 sont propres à ce rapport et n'allouent aucun numéro de
chantier C/V. P2 indique un correctif à planifier, pas un blocage universel.

## R1 — Financement tout ou rien des renforts AIR

### Références

- [`task_air.nut:930–954`](../ai/OpexAI/task_air.nut#L930-L954) : stock en attente,
  plafond du lot et création d'une seule entrée `want`.
- [`projects.nut:1041–1050`](../ai/OpexAI/projects.nut#L1041-L1050) : capital égal
  à `entry.planePrice * entry.want`.
- [`projects.nut:2032`](../ai/OpexAI/projects.nut#L2032) : exclusion du projet si
  son capital de financement dépasse le budget.
- [`task_projects.nut:171–205`](../ai/OpexAI/task_projects.nut#L171-L205) :
  exécution avion par avion.
- [`builder_air.nut:4602–4611`](../ai/OpexAI/builder_air.nut#L4602-L4611) :
  contrôle de trésorerie et clonage d'un seul avion.

### Mécanisme et impact

La demande en attente produit une proposition unique pouvant porter jusqu'à
quatre avions au défaut. Le portefeuille exige de financer tout ce lot, alors
que l'exécuteur sait en acheter moins.

Exemple illustratif, non issu d'une partie : quatre avions à 40 k£ représentent
160 k£. Avec 90 k£ de capital mobilisable, le lot est rejeté alors qu'un renfort
unitaire reste possible, sous réserve des marges d'exécution.

Une hausse de stock peut ainsi faire disparaître un renfort précédemment
finançable. La capacité et ses recettes potentielles sont retardées.

`policy_air=1` active l'arbitrage de flotte ; `c69_fleet_demand_batch=0` conserve
le plafond de quatre avions, et non un lot unitaire. Les branches C84/C121,
désactivées par défaut, ne protègent pas ce chemin legacy.

### Correctif proposé et validation

Présenter des quantités finançables au portefeuille, ou sélectionner un avion
marginal puis réévaluer le reliquat. Préserver réserve de caisse, plafonds
physiques et concurrence avec les nouveaux projets ; ne pas contourner le
classement économique par un achat direct systématique.

Tester un stock justifiant quatre avions avec un budget permettant un seul
avion, puis un budget inférieur au coût unitaire. Vérifier qu'aucune variante
de lot ne permet de financer plusieurs fois le même besoin.

## R2 — Double correction du profit de flotte observé

### Références

- [`task_report.nut:88–93`](../ai/OpexAI/task_report.nut#L88-L93) et
  [`task_report.nut:260`](../ai/OpexAI/task_report.nut#L260) : collecte du profit
  réel et stockage dans `line.lastProfit`.
- [`projects.nut:1025–1033`](../ai/OpexAI/projects.nut#L1025-L1033) : profit par
  avion issu de `lastProfit / have` quand le profit observé est positif.
- [`projects.nut:297–301`](../ai/OpexAI/projects.nut#L297-L301) et
  [`projects.nut:358–367`](../ai/OpexAI/projects.nut#L358-L367) : rattachement de
  `fleet` au facteur AIR et multiplication par C70.
- [`projects.nut:2064–2065`](../ai/OpexAI/projects.nut#L2064-L2065) : emploi du
  profit calibré dans `fundScore`.
- [`task_report.nut:287–307`](../ai/OpexAI/task_report.nut#L287-L307) : facteur
  appris sur le rapport réalisé/prédit.

### Mécanisme et impact

Le profit utilisé par le projet de flotte peut déjà provenir de l'observation
des véhicules. Il reçoit pourtant le facteur de correction du **modèle**,
comme un nouveau projet fondé sur une prédiction.

Exemple illustratif : un facteur AIR de 1,5 transforme 30 k£ observés par avion
en 45 k£ pour le classement. Un facteur inférieur à 1 produit la distorsion
inverse. Cela modifie l'allocation entre flotte existante et nouvelles lignes.

Exposition au défaut : `c70_mode_calibration=1`, `c82_engine_calibration=0`.
L'exemption existante pour les marges C121 ne protège pas la flotte legacy.

### Correctif proposé et validation

Distinguer explicitement un estimateur issu d'observations d'un estimateur issu
du modèle. Appliquer la calibration du modèle uniquement au second, y compris
au repli prédictif utilisé en l'absence de profit observé positif.

Cette correction ne résout pas à elle seule l'estimation marginale : le profit
moyen des avions existants n'est pas nécessairement celui du prochain avion.

Tester les facteurs 0,5, 1 et 1,5 avec une source observée et une source prédite.
Le facteur du modèle doit modifier la seconde, pas recalibrer la première.

## R3 — Plan AIR caduc consommant le dépassement de `K_pass`

### Références

- [`task_projects.nut:1252–1295`](../ai/OpexAI/task_projects.nut#L1252-L1295) :
  consommation de `c75BypassConsumed` avant la tentative AIR.
- [`task_air.nut:310–330`](../ai/OpexAI/task_air.nut#L310-L330) : rejet ultérieur
  par `OpexAirBatchPlanStillLive`.
- [`info.nut:686–699`](../ai/OpexAI/info.nut#L686-L699) : multi-build et bypass
  activés par défaut.

### Mécanisme et impact

Après un premier chantier, un plan AIR encore nominalement finançable peut
consommer l'unique bypass avant d'être reconnu caduc.

Séquence de reproduction :

1. Construire A–B.
2. Examiner un ancien plan A–C, qui prévoyait un nouvel aéroport à A et dont le
   coût atteint `K_pass` ; il consomme le bypass.
3. Rejeter A–C, car A est désormais desservie.
4. Rencontrer D–E, indépendant et finançable, mais atteignant aussi `K_pass` :
   le bypass est épuisé et la passe s'arrête.

Le garde anticipé existe pour C121 première année, pas pour le chemin par
défaut. La revalidation empêche correctement la construction invalide, mais
arrive trop tard pour préserver l'allocation de la passe.

### Correctif proposé et validation

Écarter les plans caducs avant la consommation du bypass. Ne pas augmenter le
nombre de dépassements réussis autorisés ni supprimer `K_pass`.

Tester la séquence ci-dessus : le plan caduc ne doit pas consommer le bypass,
et le projet indépendant doit encore pouvoir en bénéficier.

## R4 — Continuation C121 inaccessible au budget documenté

### Références

- [`main.nut:709–754`](../ai/OpexAI/main.nut#L709-L754) : deux boucles de
  continuation exigeant `AIController.GetOpsTillSuspend() > 10000`.
- [`budget.nut:3–14`](../ai/OpexAI/budget.nut#L3-L14) : reste du tick et budget
  documenté de 10 000 opcodes pour OpenTTD 15.3.
- [`test_c121_catalog_incremental.py:53–64`](../sweeps/test_c121_catalog_incremental.py#L53-L64) :
  test statique exigeant textuellement cette condition.

### Mécanisme et impact

Avec un budget total de 10 000 opcodes, le reste du tick ne peut pas dépasser
10 000. La continuation directe prévue pour enchaîner les tranches ne s'exécute
donc jamais dans cette configuration. Le catalogue avance toujours par les
passages ordinaires de l'ordonnanceur : ce n'est pas un gel total.

Exposition expérimentale seulement : `c121_catalog_incremental` dépend de
`c121_air_economics` et reste désactivé par défaut. Le runtime local n'a pas été
exécuté ou inspecté ; un budget externe supérieur modifierait cette exposition.

### Correctif proposé et validation

Choisir un seuil compatible avec le budget effectif et le coût minimal d'une
tranche, en conservant les exclusions worker/rail et l'alternance des tâches.

Remplacer l'assertion de présence textuelle par une vérification comportementale :
catalogue en attente avec 9 000 opcodes disponibles, budget insuffisant et worker
actif. Mesurer ensuite l'enchaînement réel des tranches et la latence des autres
tâches avant de conclure à un gain de débit.

## R5 — Autotests détruisant le travail restauré

### Références

- [`persist.nut:729–738`](../ai/OpexAI/persist.nut#L729-L738) : restauration de la
  file réactive et du worker.
- [`persist.nut:869–871`](../ai/OpexAI/persist.nut#L869-L871) : reconnexion du
  worker `regen_candidates` à l'instance.
- [`main.nut:641–687`](../ai/OpexAI/main.nut#L641-L687) : réconciliation, puis
  appels aux autotests C80/C76.
- [`orchestrator.nut:838–875`](../ai/OpexAI/orchestrator.nut#L838-L875) : test C80
  sur les structures vivantes, effacement sur échec et remplacement du worker.
- [`orchestrator.nut:1036–1037`](../ai/OpexAI/orchestrator.nut#L1036-L1037) :
  sauvegarde de l'état initial trop tardive, après les premiers sous-tests.
- [`orchestrator.nut:1898–1918`](../ai/OpexAI/orchestrator.nut#L1898-L1918) :
  effacement indépendant de la file par l'autotest C76.

### Mécanisme et impact

Après restauration, C80 ajoute son entrée de test puis attend une file de
longueur un. Une intention préexistante fait échouer ce contrôle, qui vide la
file et annule le worker. Même avec une file vide, un worker restauré peut être
remplacé par le worker de test. C76 vide aussi la file sans en préserver le contenu.

Une régénération ultérieure peut reconstruire des candidats, mais ne préserve
pas les intentions ciblées, la progression du worker ou sa continuation
`buildAfter`. Les duels démarrés sans rechargement n'exposent pas ce défaut.

### Correctif proposé et validation

Exécuter les autotests sur un état isolé ou les éviter au rechargement. Traiter
les deux autotests, pas seulement C80.

Valider le chemin complet `Load → Start` avec une intention `c77_build` en
attente, puis avec un worker `regen_candidates` actif. Un test des seuls helpers
de sérialisation ne couvre pas la destruction ultérieure dans `Start`.

## Ordre recommandé et protocole

1. R1 et R3 : admission des quantités de flotte et conservation du bypass face
   aux plans caducs, dans deux interventions séparées.
2. R2 : distinguer observation et prédiction dans la calibration.
3. R4 : réparer et mesurer l'enchaînement avant de réinterpréter les expériences
   de vitesse du catalogue C121.
4. R5 : correctif et régression Save/Load indépendants.

Pour chaque changement Squirrel : tests ciblés et smoke 1 graine × 1 an pour
compilation/exécution. Pour chaque changement de comportement : diagnostic
apparié 5 graines × 6 ans, puis banc officiel apparié 20 graines × 10 ans avant
adoption, selon `AGENTS.md`. Ajouter la validation de rechargement pour R5.

Figer le code et les réglages, conserver C115, isoler les traitements et fixer
les métriques avant les parties. Suivre le profit et la valeur propres d'OpexAI,
l'écart avec AAAHogEx, la croissance de flotte, les dates d'acquisition des
aéroports et la trésorerie inutilisée malgré des projets finançables. Une baisse
du seul adversaire, un meilleur score interne ou une suite de tests statiques
verte ne démontre pas un gain économique.

**État de validation de ce rapport : lecture statique uniquement. Aucun des
correctifs proposés n'a été implémenté, testé en partie ou adopté par cette revue.**

## Complément — code mort, paramètres inutiles et regroupement

### Périmètre et méthode

Complément de revue statique du 30 septembre 2026. L'inventaire textuel des
déclarations `AddSetting` et des lectures `GetSetting` dans `ai/OpexAI/` trouve
**146 paramètres déclarés et 145 clés distinctes lues**. Les usages des globales,
les appels et alias, les branches conditionnelles et les consommateurs dans les
tests/harnais ont ensuite été examinés. Un faible nombre d'occurrences est un
indice à vérifier, pas une preuve suffisante de code mort.

Les références correspondent au checkout local inspecté. Git et ses métadonnées
étaient absents ; aucun diff Git n'a pu être inspecté. Aucune modification du code
IA ni exécution de tests ou de parties n'a été effectuée pour ce complément.

Distinctions retenues :

- **Réglage sans effet fonctionnel identifié** : sa valeur n'atteint aucun
  consommateur métier, ou n'est jamais lue.
- **Expérience désactivée** : un défaut 0 n'implique pas du code mort.
- **Branche inaccessible** : une valeur interne verrouillée empêche son exécution.
- **Compatibilité d'opcodes** : des conditions sans effet métier restent
  volontairement exécutées pour préserver la cadence de décision.

**Contrainte utilisateur : C115 et tous les paramètres C121/C122 doivent rester
accessibles.** Leur retrait, renommage, fusion destructrice ou activation forcée
ne fait pas partie des propositions de nettoyage.

Les identifiants R6–R10 prolongent uniquement les références locales du rapport ;
ils ne créent pas de nouveaux chantiers C/V dans `docs/taches.md`.

### R6 [P2] — Quatre paramètres exposés sans effet fonctionnel identifié

| Paramètre | Constat | Références |
|---|---|---|
| `c80_double_register` | Jamais lu ; `C80_DOUBLE_REGISTER` est forcé à `true` alors que l'interface annonce un interrupteur à défaut 0. | [`info.nut:1033–1037`](../ai/OpexAI/info.nut#L1033-L1037), [`settings.nut:472`](../ai/OpexAI/settings.nut#L472) |
| `c102_air_station_rating_probe` | Lu et stocké ; aucune lecture de la globale après affectation. | [`settings.nut:249`](../ai/OpexAI/settings.nut#L249), [`globals_pre.nut:334`](../ai/OpexAI/globals_pre.nut#L334) |
| `v95_air_targeted_second` | Lu et stocké ; aucun traitement ne consomme sa valeur. | [`settings.nut:242`](../ai/OpexAI/settings.nut#L242), [`info.nut:247–251`](../ai/OpexAI/info.nut#L247-L251) |
| `v95_air_post73_targeted` | Même absence de consommateur. | [`settings.nut:243`](../ai/OpexAI/settings.nut#L243), [`info.nut:255–259`](../ai/OpexAI/info.nut#L255-L259) |

**Impact :** l'interface laisse croire qu'un changement de valeur active une
variante ou une sonde. Un A/B sur ces clés ne teste pas la fonctionnalité annoncée.

**Proposition :** retirer l'interrupteur C80 devenu obsolète ; pour C102 et les
deux V95, décider explicitement entre retrait et implémentation. Ce sont des
propositions, pas des suppressions autorisées ou effectuées par la revue.

Le retrait doit traiter les contrats de configuration :
[`test_campaign_freeze.py:180–198`](../sweeps/test_campaign_freeze.py#L180-L198)
exige encore les clés C80 et C102 avec leur défaut 0. Les variantes historiques
et les parseurs génériques doivent également être pris en compte.

**Ne pas retirer toute la famille V95 : `v95_air_post73_probe` est effectivement
utilisé**, notamment dans `builder_air.nut`. Les paramètres conditionnels ou
expérimentaux ne sont pas assimilés aux quatre cas ci-dessus.

### R7 [P2] — Effet de plancher C121 neutralisé, paramètre à conserver

`c121_air_defensive_floor` reste accessible, mais ne peut pas actuellement
assouplir un plancher positif :

1. [`settings.nut:465`](../ai/OpexAI/settings.nut#L465) force
   `PORTFOLIO_FLOOR_PCT = 0`.
2. [`projects.nut:1994–2002`](../ai/OpexAI/projects.nut#L1994-L2002) laisse donc
   `floorProfit = 0`.
3. [`projects.nut:2045–2046`](../ai/OpexAI/projects.nut#L2045-L2046) calcule 50 %
   ou 75 % de ce zéro pour les projets défensifs.

La branche reste accessible et peut modifier les calculs exécutés et leur
cadence : ce constat ne garantit pas une identité parfaite des trajectoires.
Le filtre contre les profits négatifs reste, lui, opérant.

**Proposition : conserver le paramètre et documenter sa dépendance neutralisée.**
Définir le contrat économique attendu avant un éventuel correctif séparé. Ne pas
réactiver silencieusement le plancher global ni supprimer la branche C121 pendant
un nettoyage de code mort.

Validation proposée : vérifier les valeurs effectives du plancher et le résultat
du filtre pour les différentes classes défensives, puis mesurer séparément tout
traitement qui réintroduirait un plancher positif.

### R8 [P3] — Fonctions sans appel et globales sans lecteur

Aucun appel, alias ou enregistrement comme callback n'a été trouvé pour les
fonctions suivantes dans l'arbre examiné :

| Fonction | Emplacement |
|---|---|
| `OpexPlaceCapacitySignals` | [`builder_rail.nut:1410`](../ai/OpexAI/builder_rail.nut#L1410) ; commentaire « plus appelé » juste au-dessus |
| `OpexRoadFindOrBuildTruckStop` | [`builder_road.nut:856`](../ai/OpexAI/builder_road.nut#L856) |
| `OpexCloneCandidateGroups` | [`projects.nut:3762`](../ai/OpexAI/projects.nut#L3762) |
| `OpexC102WaitingRatingPoints`, `OpexC102AgeRatingPoints`, `OpexC102SpeedRatingPoints` | [`task_report.nut:4–36`](../ai/OpexAI/task_report.nut#L4-L36) |

Ces corps sont des candidats de retrait ciblé. Leurs helpers doivent être
vérifiés individuellement : certains restent utilisés par du code vivant.

Deux globales n'ont également aucun lecteur identifié :

- `JOIN_MAX_DISTANCE` : initialisation dans `globals_post.nut:53`, affectation
  dans [`settings.nut:487`](../ai/OpexAI/settings.nut#L487).
- `C39_ENGINE_REFRESH` : initialisation dans `globals_pre.nut:103`, affectation
  dans [`settings.nut:509`](../ai/OpexAI/settings.nut#L509).

**Validation proposée :** recherche complète des références et contrats de tests
avant retrait, puis smoke de chargement/exécution Squirrel. Ne pas étendre le
nettoyage à toute une famille sur la seule base du préfixe des fonctions.

### R9 [P3] — Branches verrouillées et compatibilité d'opcodes

#### Reliquat `BASIN_SHARE`

`BASIN_SHARE` est initialisé puis forcé à `false` dans
[`settings.nut:488`](../ai/OpexAI/settings.nut#L488), sans réglage public courant.
Les branches dans `candidates.nut:1170–1171`, `1327–1328` et `projects.nut:3422`
sont donc inaccessibles. Les helpers
[`OpexShareBasin` et `OpexStationCargoLineCount`](../ai/OpexAI/candidates.nut#L1034-L1052)
ne servent qu'à ces branches.

Candidat à un nettoyage isolé, sans restaurer la politique abandonnée. Retirer
les tests de branche modifie néanmoins les opcodes exécutés ; aucune neutralité
de cadence n'a été mesurée ici.

#### Gardes volontairement conservées

`OPEX_ECONOMY_OPCODE_COMPAT_FALSE` et `WATER_OPCODE_COMPAT_FALSE` sont explicitement
documentées dans [`globals_pre.nut:91–108`](../ai/OpexAI/globals_pre.nut#L91-L108).
Leurs branches alternatives sont mortes, mais les évaluations des conditions
restent exécutées. Leur rôle historique est confirmé dans le
[journal du 22 septembre](journaux/journal_2026-09-22.md).

Les supprimer peut changer la date des décisions et donc la compétition.
Des contrats textuels conservent encore certaines formes, notamment
`sweeps/test_b3_road_fleet_targets.py` et `sweeps/test_c84_air_target_fleet.py`.

Séparer trois interventions : retrait de fonctions jamais appelées, simplification
de conditions exécutées, puis optimisation mesurée de cadence. Ne pas supprimer
les wrappers eau en bloc : leurs chemins de connectivité vivants restent requis.

### R10 [P2] — Paramètres masqués et traitements partiellement actifs

Les réglages AIR ne sont pas tous composables. Exemples vérifiés :

- `c72_plane_choice != 0` ferme la branche de choix C115 dans
  [`builder_air.nut:6549`](../ai/OpexAI/builder_air.nut#L6549).
- Avec C72 non nul et C105 actif, le chooser C105 est exclu par
  [`builder_air.nut:6486`](../ai/OpexAI/builder_air.nut#L6486), mais C105 active
  encore le timing physique dans
  [`builder_air.nut:1293–1296`](../ai/OpexAI/builder_air.nut#L1293-L1296).
- La sonde `c104_air_c100_compare_probe` figure dans les exclusions des branches
  C109/C111/C112 dans
  [`builder_air.nut:6519–6547`](../ai/OpexAI/builder_air.nut#L6519-L6547).
  Activer une sonde peut donc empêcher une branche de traitement.

Il s'agit de **composition de configuration**, pas de code mort. Une clé présente
et une valeur lue ne prouvent pas que le traitement est effectivement actif.

**Proposition :** établir une matrice « valeur demandée → prérequis → exclusions
→ comportement effectif ». Ajouter des tests de combinaisons et, si nécessaire,
un diagnostic de configuration hors des boucles coûteuses. Ne pas convertir
immédiatement ces booléens en une enum : cela supprimerait des combinaisons
accessibles et pourrait modifier les expériences.

La correction d'une sonde qui masque un traitement doit être isolée d'un simple
réagencement des réglages et validée comme changement de comportement.

### Plan de regroupement non destructif

Regrouper la présentation des `AddSetting` et organiser les blocs de chargement,
**sans fusionner les leviers causaux**, modifier leurs défauts ou changer l'ordre
de résolution de leurs dépendances.

| Groupe proposé | Contenu |
|---|---|
| Système | Sauvegarde, logs, panneaux, temporisation |
| Politiques générales | `policy_*`, capital, sélection du portefeuille |
| Rail / Route / Eau | Paramètres physiques, construction et exploitation par mode |
| Ordonnancement | C76, workers C80, stock A*, V89–V91 |
| AIR historique | Choix moteur, flotte, hubs, C115 explicitement visible |
| C121 — économie | Modèle, réalisation moteur/projet, adaptation, économie initiale |
| C121 — développement | Catalogue, première année, renforts, territoire, configuration AAA, plancher défensif |
| C121 — observation | Shadow économique, pression, replay moteur |
| C122 — traitements | Priorité de régime, retry de menace |
| C122 — observation | Shadow de régime, sonde de menace |
| Autres diagnostics | Sondes par domaine, séparées des traitements |

#### Contrat de protection : 19 clés publiques

Conserver les noms exacts, déclarations, lectures, défauts et possibilités de
configuration dans les combinaisons autorisées. Tous ces paramètres sont des
booléens dans le checkout inspecté.

**C115 — 1 paramètre, défaut 1 :**

- `c115_air_c100_capital_replay`

**C121 — 14 paramètres, défaut 0 :**

- `c121_air_economics_shadow`
- `c121_air_economics`
- `c121_catalog_incremental`
- `c121_catalog_air_first_year`
- `c121_aaa_line`
- `c121_territory_first`
- `c121_fleet_stock_growth`
- `c121_air_engine_realization`
- `c121_air_project_realization`
- `c121_air_project_realization_adaptive`
- `c121_air_pressure_probe`
- `c121_air_defensive_floor`
- `c121_air_initial_project_economics`
- `c121_air_engine_replay_shadow`

**C122 — 4 paramètres, défaut 0 :**

- `c122_air_regime_priority`
- `c122_air_regime_shadow`
- `c122_air_threat_probe`
- `c122_air_threat_retry`

Préserver les dépendances de chargement :

- `c121_catalog_incremental` dépend de `c121_air_economics` ;
  `c121_catalog_air_first_year` dépend du catalogue incrémental.
- `c121_fleet_stock_growth`, `c121_territory_first` et `c121_aaa_line` sont
  conditionnés par C121 actif.
- `c121_aaa_line` impose `AIR_FULL_LOAD = 1`.
- `c122_air_threat_retry` implique la sonde de menace, tout en conservant la
  possibilité d'activer la sonde seule.

La protection s'étend aux dépendances non homonymes :

- C115 appelle `OpexC104BestAirEngine` dans
  [`builder_air.nut:6108,6123`](../ai/OpexAI/builder_air.nut#L6108-L6123).
- C121 utilise `OpexC119AirIncomeDays` dans
  [`builder_air.nut:2803`](../ai/OpexAI/builder_air.nut#L2803).

Supprimer « tout C104 » ou « tout C119 » casserait donc les fonctionnalités
protégées. Une expérience rejetée ne rend pas ses helpers partagés supprimables.
Préserver également les données de persistance nécessaires et la lisibilité des
déclarations par `sweeps/campaign_freeze.py`.

### Ordre et validation du nettoyage proposé

1. Clarifier les quatre interrupteurs sans effet de R6 et leurs contrats de tests.
2. Retirer isolément les fonctions sans appel et globales sans lecteur de R8.
3. Réorganiser les réglages sans changer leurs identifiants, défauts ou dépendances.
4. Vérifier par tests la présence et le chargement des 19 paramètres protégés,
   leurs implications et leur disponibilité dans le harnais.
5. Traiter séparément les conflits AIR, le plancher C121 neutralisé et toute
   simplification de conditions qui modifie le coût en opcodes.

Les règles de validation d'`AGENTS.md` restent applicables : tests de contrat et
smoke pour les modifications Squirrel, validation Save/Load si la persistance
est touchée, mesure d'opcodes et banc de non-régression adapté pour les
optimisations de cadence. Les changements de comportement ne sont pas des
nettoyages purement structurels et nécessitent leur propre qualification.

**Conclusion du complément :** priorité à une interface fidèle au comportement
réel et à un retrait ciblé des reliquats. Aucun gain économique n'est démontré ;
aucune suppression, fusion ou modification des paramètres n'a été effectuée.

## Complément — fichiers et fonctions trop volumineux

### Périmètre, méthode et limites

Revue structurelle statique du 30 septembre 2026. Le problème recherché est la
concentration des responsabilités, pas le seul dépassement d'un seuil de lignes.
L'inventaire récursif porte sur les fichiers `.nut` de `ai/OpexAI/`, y compris
`pathfinder_v90/`. Les principaux blocs métier ont ensuite fait l'objet de
lectures ciblées ; ce n'est pas une analyse exhaustive de toutes les fonctions.

Les mesures ont été exécutées en arrière-plan par un script PowerShell en lecture
seule : comptage des lignes physiques, masquage des commentaires et chaînes, puis
repérage des fonctions nommées et équilibrage des accolades. Le scan est terminé ;
aucun agent délégué ni travail autonome restant n'est associé à cette revue.

- Les lignes comprennent commentaires et blancs ; le découpage sur les sauts de
  ligne peut compter le segment vide final.
- Les fonctions anonymes et les constructeurs ne sont pas comptés séparément.
- Cet inventaire textuel n'est ni un parseur Squirrel complet, ni une mesure de
  complexité cyclomatique, de coût en opcodes ou de temps d'exécution.
- Aucun code IA modifié, aucun test ni partie exécuté pour ce complément.
- Les propositions ne constituent pas une adoption et ne modifient pas le backlog
  autoritaire `docs/taches.md`. R11–R17 sont des références locales au rapport.

### Inventaire de taille

**39 fichiers, 45 374 lignes physiques, 1 027 fonctions nommées ; 31 fonctions
dépassent 200 lignes, dont 5 dépassent 500 lignes.** `builder_air.nut` représente
environ 21 % des lignes ; avec `projects.nut`, environ 30 %.

| Fichier | Lignes | Lecture structurelle |
|---|---:|---|
| `builder_air.nut` | 9 479 | Nombreuses responsabilités indépendantes |
| `projects.nut` | 4 263 | Modèles, sélection, génération et diagnostics |
| `candidates.nut` | 2 466 | À examiner par familles de génération |
| `probes.nut` | 2 309 | Instrumentation volumineuse |
| `builder_rail.nut` | 2 151 | Préserver les transactions de construction |
| `task_rail.nut` | 1 992 | Exécution et exploitation rail |
| `task_projects.nut` | 1 930 | Orchestration centrale concentrée |
| `orchestrator.nut` | 1 928 | Production et autotests mélangés |
| `ledgers.nut` | 1 552 | Comptabilité et diagnostics |
| `task_report.nut` | 1 509 | Reporting et mutations métier |
| `builder_road.nut` | 1 304 | Construction route |
| `info.nut` | 1 241 | Principalement déclaratif |

| Fonction | Référence | Lignes |
|---|---|---:|
| `GetSettings` | [`info.nut:14–1237`](../ai/OpexAI/info.nut#L14-L1237) | 1 224 |
| `OpexAI::_tryBuildProjects` | [`task_projects.nut:944–1815`](../ai/OpexAI/task_projects.nut#L944-L1815) | 872 |
| `OpexAI::_reportLines` | [`task_report.nut:41–688`](../ai/OpexAI/task_report.nut#L41-L688) | 648 |
| `OpexAI::_c80RunSelfTest` | [`orchestrator.nut:838–1378`](../ai/OpexAI/orchestrator.nut#L838-L1378) | 541 |
| `OpexLoadSettings` | [`settings.nut:4–518`](../ai/OpexAI/settings.nut#L4-L518) | 515 |
| `OpexAI::_schedIdlePostDispatch` | [`ledgers.nut:565–1058`](../ai/OpexAI/ledgers.nut#L565-L1058) | 494 |
| `OpexBuildProjects` | [`projects.nut:3819–4262`](../ai/OpexAI/projects.nut#L3819-L4262) | 444 |
| `OpexAI::_dispatchCatalog` | [`scheduler_tasks.nut:176–606`](../ai/OpexAI/scheduler_tasks.nut#L176-L606) | 431 |
| `OpexC121AirEconomics` | [`builder_air.nut:2787–3193`](../ai/OpexAI/builder_air.nut#L2787-L3193) | 407 |

### R11 [P2] — Plusieurs modules métier dans `builder_air.nut`

Le fichier réunit couverture et demande, sites, temps de trajet, économie,
sélection des avions, catalogue incrémental, flottes, planification, construction
physique et instrumentation. Repères particulièrement significatifs :

- Sites : [`1439–2245`](../ai/OpexAI/builder_air.nut#L1439-L2245).
- Économie C121, catalogue incrémental et mesures associées :
  [`2787–3953`](../ai/OpexAI/builder_air.nut#L2787-L3953).
- Choix moteur, politiques et sondes :
  [`4683–6818`](../ai/OpexAI/builder_air.nut#L4683-L6818).
- Planification puis construction :
  [`6819–9320`](../ai/OpexAI/builder_air.nut#L6819-L9320).

**Impact :** une modification locale exige de naviguer dans un périmètre trop
large ; les dépendances entre familles deviennent difficiles à identifier.

**Proposition :** déplacer d'abord des fonctions entières, sans modifier leur
corps ni leur nom public, vers des modules cohérents : sites, économie, choix
moteur, planification, flotte et construction. La planification dispose déjà de
plusieurs fonctions : il ne s'agit pas d'une unique fonction de 2 000 lignes.

Éviter un découpage uniquement par numéro d'expérience ou un fichier fourre-tout
« expériences ». C115 dépend de C104 et C121 de C119 ; ces liens doivent survivre
au déplacement. Vérifier aussi les affectations et alias au niveau module, pas
seulement les appels de fonctions.

### R12 [P2] — `_tryBuildProjects` cumule orchestration, décisions et comptabilité

**Référence :** [`task_projects.nut:944–1815`](../ai/OpexAI/task_projects.nut#L944-L1815),
872 lignes.

La fonction prépare la passe et ses budgets, arbitre avec le rail reprenable,
admet et tente les projets par mode, enregistre les constructions, alimente les
sondes et régénère le portefeuille. Les branches AIR, ROAD, RAIL et WATER répètent
des traitements après succès : journaux C39/C50, compteurs, suivi C69/C75 et arrêt
du batch, notamment dans
[`1460–1640`](../ai/OpexAI/task_projects.nut#L1460-L1640).

**Impact :** une nouvelle sortie peut oublier une mise à jour ou contourner une
finalisation. Le résultat rail `pending` illustre le risque : selon les
constructions déjà réalisées, il provoque un `break` ou un retour anticipé avec
sa propre comptabilité. Ce constat structurel n'établit pas un nouveau défaut
fonctionnel sur tous ces chemins.

**Proposition :** garder un orchestrateur lisible et isoler progressivement la
préparation, les traitements communs après succès, la finalisation des diagnostics
et le rafraîchissement du portefeuille. Définir explicitement les résultats
« continuer », « arrêter la passe » et « suspendre/reprendre » ; ne pas remplacer
mécaniquement les `break`/`continue` par des retours de helpers.

Préserver budgets de passe, invalidations, villes AIR touchées, reprises rail et
différences intentionnelles entre modes. Ne pas transformer tous les locaux en
un vaste état partagé pour simplement raccourcir la signature des helpers.

### R13 [P2] — `_reportLines` n'est pas une simple fonction de reporting

**Référence :** [`task_report.nut:41–688`](../ai/OpexAI/task_report.nut#L41-L688),
648 lignes ; mutations et finalisation notamment dans
[`480–688`](../ai/OpexAI/task_report.nut#L480-L688).

Observations, santé des lignes, compteurs de pertes, abandons, calibration et
publication des diagnostics se trouvent dans un même bloc.

**Impact :** une modification présentée comme cosmétique peut changer les
décisions économiques ou l'état persistant. Le nom de la fonction ne rend pas
ces effets métier suffisamment visibles.

**Proposition :** distinguer collecte des observations, mise à jour de la santé,
accumulation de calibration, publication des facteurs et émission des rapports.
Conserver l'ordre et la période des observations : publier un facteur avant la
fin de la collecte changerait le comportement. Préserver les contrats Save/Load
des états concernés. Transformer ce traitement en worker reprenable constituerait
un changement d'ordonnancement séparé, pas une simple modularisation.

### R14 [P2] — `projects.nut` mélange les étapes de fabrication du portefeuille

**Références :** [`projects.nut`](../ai/OpexAI/projects.nut), 4 263 lignes ;
[`OpexBuildProjects:3819–4262`](../ai/OpexAI/projects.nut#L3819-L4262),
444 lignes et 12 paramètres.

Le fichier combine modèles économiques, politiques de classement, contraintes
financières, génération, validation, cache incrémental et diagnostics.
`OpexBuildProjects` prépare les modes, génère et fusionne les candidats, assemble
les alternatives, sélectionne les projets finançables et construit le résultat
instrumenté.

**Impact :** modifier une étape impose de suivre simultanément les hypothèses
des modèles, le cycle des caches et la forme des données retournées.

**Proposition :** séparer les modèles de projets, les politiques de sélection,
la génération/mise à jour et les diagnostics spécialisés. Pour la fonction,
extraire des étapes substantielles plutôt qu'une multitude de petits helpers.
Un contexte de génération explicite pourrait réduire les paramètres, sans devenir
un conteneur global mutable.

Préserver la durée de vie des caches d'une génération, les candidats hérités,
les subventions actives, les étapes de bootstrap et la séquence de sélection.
Les modifications d'interface et de logique doivent rester distinctes des simples
déplacements de fonctions.

### R15 [P3] — Deux grands résultats presque identiques dans `OpexC121AirEconomics`

**Référence :** [`builder_air.nut:2787–3193`](../ai/OpexAI/builder_air.nut#L2787-L3193),
407 lignes.

La fonction combine calcul physique, partage du trafic, congestion,
cannibalisation, coûts, recherche de flotte et construction de résultats détaillés.
Deux grands snapshots sont maintenus : meilleur score et meilleur profit.

**Risque :** l'ajout d'un champ ou une correction dans un seul snapshot peut
introduire une divergence difficile à détecter.

**Proposition :** formaliser le schéma commun et tester la cohérence des deux
résultats avant de mutualiser leur construction. Les critères d'optimisation et
leurs départages doivent rester distincts ; leurs gagnants peuvent être différents.

Ne pas découper aveuglément la boucle chaude : le chemin `decisionOnly` évite
volontairement de grosses allocations. Des appels ou tables intermédiaires
supplémentaires peuvent augmenter le coût en opcodes. Préserver le chemin compact,
les bornes d'élagage, les arrondis et les champs consommés par C121 et ses sondes.
Tout gain d'opcodes doit être mesuré, pas déduit du nombre de lignes supprimées.

### R16 [P3] — Les autotests alourdissent l'orchestrateur de production

**Référence :** [`orchestrator.nut:838–1378`](../ai/OpexAI/orchestrator.nut#L838-L1378),
`_c80RunSelfTest`, 541 lignes, environ 28 % du fichier.

Cette fonction rassemble plusieurs scénarios, des états temporaires et de
nombreuses restaurations manuelles avant retour.

**Proposition :** déplacer les autotests dans un module dédié chargé après la
déclaration de `OpexAI`, puis séparer les scénarios avec un contrat explicite de
sauvegarde/restauration. Conserver initialement les points d'appel et l'ordre
d'exécution ; leur modification est une intervention distincte.

**Déplacer le code ne corrige pas R5.** Le défaut de restauration déjà identifié
et le découpage structurel doivent être traités et validés séparément.

### R17 [P3] — Les tests textuels dépendent de l'organisation physique actuelle

**Références :**
[`test_c115_air_c100_capital_replay.py:6–54`](../sweeps/test_c115_air_c100_capital_replay.py#L6-L54)
et [`test_c121_air_economics.py`](../sweeps/test_c121_air_economics.py).

Ces tests lisent directement `builder_air.nut`. Certains délimitent un bloc entre
deux fonctions nommées dans ce même fichier.

**Impact :** déplacer une fonction sans changer son comportement peut casser
les tests. Le découpage implique donc aussi une migration des contrats textuels.

**Proposition :** adapter leur lecture aux nouveaux modules tout en conservant
les assertions métier et la vérification de leur chargement. Ne pas supprimer
les assertions pour faire passer le découpage. Les tests Python ne remplacent
pas la compilation et l'exécution Squirrel.

### Gros blocs à ne pas prioriser sur la seule taille

- `GetSettings` (1 224 lignes) est principalement déclaratif : préférer
  regroupement et cohérence des métadonnées à une fragmentation arbitraire.
- `OpexLoadSettings` (515 lignes) exige de préserver l'ordre des dépendances et
  surcharges ; sa taille ne justifie pas une réorganisation automatique.
- `_schedIdlePostDispatch` (494 lignes) peut être organisé par familles de
  diagnostics, mais son entrée est protégée par `V95_SCHED_IDLE_LEDGER`. Le coût
  actif n'a pas été mesuré ; la fonction entière n'a pas été relue pour ce complément.
- Les constructeurs de routes doivent conserver des engagements de ressources
  et chemins de rollback lisibles. Raccourcir un bloc au prix de la dispersion
  d'une transaction n'est pas un progrès.

### Ordre de traitement et garde-fous

1. Déplacer les familles de fonctions AIR et les autotests sans modifier leur logique.
2. Adapter les tests structurels et vérifier l'ordre de chargement dans la même
   intervention, avant de considérer chaque déplacement comme terminé.
3. Réduire `_tryBuildProjects` et `_reportLines`, une responsabilité à la fois.
4. Séparer les responsabilités du portefeuille.
5. Traiter l'économie C121 seulement avec contrôle du coût en opcodes.

Conserver les **19 clés protégées C115/C121/C122** listées dans le complément
précédent, leurs défauts, leurs dépendances et leurs combinaisons utiles. Un
découpage n'autorise ni suppression d'expérience ni changement de configuration.

Vérifier les chargements de [`main.nut:44–60`](../ai/OpexAI/main.nut#L44-L60)
et [`581–599`](../ai/OpexAI/main.nut#L581-L599), les dépendances de
`globals_pre.nut`/`globals_post.nut`, les constantes et les alias. Les méthodes
`OpexAI::...` doivent rester chargées après la déclaration de classe. Ne pas
supposer qu'une nouvelle fonction imbriquée capture les locaux englobants.

Séparer déplacement de fonctions, extraction de helpers et optimisation : des
appels supplémentaires changent le coût en opcodes, donc potentiellement la
cadence en jeu. Préserver persistance, reprise des tâches, invalidation, nettoyage
des constructions partielles et formats des journaux/panneaux.

Pour une mise en œuvre ultérieure : tests de contrat pertinents et smoke 1×1
pour tout changement Squirrel ; validation Save/Load pour les états concernés ;
diagnostic apparié 5×6 si le comportement change, puis qualification d'adoption
20×10 selon `AGENTS.md`. Une optimisation d'opcodes suit le protocole de gain
mesuré et de non-régression économique, pas une preuve fondée sur la taille source.

**Conclusion du complément :** priorité à la séparation des responsabilités AIR,
de l'orchestration des constructions et des mutations cachées dans le reporting.
Un découpage de fichiers améliore la maintenabilité ; il ne démontre aucun gain
de vitesse ni de profit. Aucun des découpages proposés n'a été implémenté ou adopté.

## Complément — consolidation de huit revues parallèles

### Mandat et niveau de preuve

À la demande de l'utilisateur, huit agents spécialisés ont été lancés en parallèle
sur les axes ci-dessous. Trois appels ont échoué sur une erreur réseau ; une
seconde vague a permis d'obtenir leurs rapports. Les huit axes ont finalement
fourni une conclusion. Il ne reste pas de revue autonome en arrière-plan.

Tous les agents ont travaillé en lecture seule, avec consultation des instructions,
de l'état courant de `docs/taches.md` et des constats R1–R17. La consolidation a
recoupé les mécanismes décisifs dans les sources, leurs appelants et leurs réglages.
Les propositions déjà connues ont été séparées des nouvelles observations.

**Bilan : neuf nouveaux constats statiques R18–R26, dont six dans l'IA et trois
dans le banc.** Ce ne sont pas neuf incidents reproduits : les scénarios d'échec,
leur fréquence et leurs conséquences économiques restent à tester. P2 désigne
une correction à planifier, pas une exposition universelle ni une adoption.

- Lectures ciblées par axe, pas huit audits exhaustifs. Route et eau ont notamment
  été seulement survolées ; l'absence de nouveau constat ne vaut pas certification.
- Aucun test, installation, compilation Squirrel ou lancement de partie exécuté.
- Seul ce rapport est modifié par la consolidation ; aucun correctif IA/harnais.
- Git, `.git` et RTK restent absents lors de la vérification locale : pas de SHA
  établi, ni de `git diff --check` disponible.
- Les **19 clés C115/C121/C122** et leurs dépendances restent protégées. Les
  conclusions expérimentales n'autorisent aucune activation par défaut.
- Aucun résultat historique cité dans le backlog n'est présenté comme une nouvelle
  mesure de cette revue. Le source d'AAAHogEx demeure absent du checkout.

### Couverture des huit axes

| Axe | Périmètre principal effectivement lu | Résultat consolidé |
|---|---|---|
| 1. Constructions et échecs | Construction AIR, nivellement, rollback, abandon ; `builder_air.nut`, `task_air.nut`, `lines.nut` | R18–R19 |
| 2. État, caches, sauvegardes | `persist.nut`, démarrage, événements, révisions C76 et classification C121/C122 | R20 ; R5 non recompté |
| 3. Opcodes et ordonnancement | Rotation du fond, registre réactif, repli C77 synchrone ; `scheduler.nut`, `orchestrator.nut` | Aucun nouveau défaut suffisamment démontré ; risques à mesurer |
| 4. Modèles économiques | Unités rail/route, legacy AIR, congestion C121, cash-flow C69/C75, renfort marginal | Aucun nouveau défaut suffisamment démontré ; R1/R2 non recomptés |
| 5. Cycle de vie | Santé du fret, événements véhicules, retraites et délais de récupération | R21–R22 |
| 6. Rail, route, eau | Rail devis/construction approfondi ; raccordement route et disponibilité/connectivité eau survolés | R23 ; pas de conclusion exhaustive route/eau |
| 7. Tests et banc | Lanceur courant, gel, collecte économique, santé, comparaison appariée et tests associés | R24–R26 |
| 8. Concurrence AAAHogEx | Surveillance C83, priorités C77/C122, classifieur et reprise après site rejeté | Fragilité C122 déjà documentée ; pas de nouveau R |

### Synthèse des nouveaux constats

| Réf. | Priorité | Constat | Exposition |
|---|---|---|---|
| R18 | P2 | Cause du nivellement AIR perdue, abandon potentiellement injustifié | Chemin par défaut ; échec de terrassement requis |
| R19 | P2 | Rollback AIR non sûr après démarrage partiel d'un lot | Plusieurs avions initiaux, notamment C121 AAA ; défaut OFF |
| R20 | P2 | Régime C121/C122 verrouillé non restauré | Reload sous options adaptatives/de priorité ; défaut OFF |
| R21 | P2 | Perte du destinataire industriel absente du critère de retrait | Fret au défaut, source encore productive et débouché perdu |
| R22 | P2 | Relance de retraite pouvant annuler l'envoi au dépôt | `policy_vehicle_events=1` ou ticket déjà sauvegardé |
| R23 | P2 | Devis rail partiellement échoué accepté comme capital physique | Devis actif au défaut ; tracé devenu impossible |
| R24 | P2 | Éligibilité d'adoption fondée sur le nombre de paires, pas le protocole | Répétitions ou horizon court dans le banc |
| R25 | P2 | Trimestre invalide silencieusement retiré du profit annuel | Donnée économique partiellement indécodable |
| R26 | P2 | Harnais archivé mais non imposé comme source d'exécution | Modification concurrente du dépôt pendant la préparation/import |

### R18 [P2] — La cause d'un échec de nivellement AIR est perdue

**Références :**
[`builder_air.nut:1510–1525`](../ai/OpexAI/builder_air.nut#L1510-L1525),
[`9080–9094`](../ai/OpexAI/builder_air.nut#L9080-L9094),
[`9117–9131`](../ai/OpexAI/builder_air.nut#L9117-L9131),
[`lines.nut:36–42`](../ai/OpexAI/lines.nut#L36-L42),
[`task_air.nut:513–520`](../ai/OpexAI/task_air.nut#L513-L520).

`OpexAirLevelFootprint` peut retourner `false`. Ses deux appelants ignorent ce
retour et exécutent `BuildAirport`. L'erreur conservée est alors celle de la
construction d'aéroport, pas nécessairement celle du terrassement.

**Scénario à reproduire :** les précontrôles passent, puis les dépenses du chantier
A réduisent la caisse ; le nivellement B échoue faute d'argent et laisse une
emprise non plane. Si `BuildAirport` renvoie ensuite une erreur de terrain, le
garde financier ne reconnaît plus l'erreur temporaire initiale et la paire peut
être mémorisée comme abandonnée. Le retour ignoré est établi ; cette succession
d'erreurs moteur n'a pas été reproduite pendant la revue.

**Exposition :** `policy_air=1`, `policy_abandon=1` au défaut
([`info.nut:760–773`](../ai/OpexAI/info.nut#L760-L773)). Le premier délai d'abandon
est de 365 jours, puis augmente avec les récidives
([`info.nut:814–821`](../ai/OpexAI/info.nut#L814-L821),
[`lines.nut:262–300`](../ai/OpexAI/lines.nut#L262-L300)). Contrôles financiers et
présondages réduisent le risque sans réserver atomiquement tout le chantier.

**Proposition :** remonter un résultat explicite de nivellement, conserver sa cause
et arrêter avant `BuildAirport` en cas d'échec. Distinguer état partiellement
modifié et impossibilité durable ; nettoyer uniquement les ressources nouvelles.

**Validation future :** échec financier injecté au nivellement A puis B, absence
d'appel de construction ultérieur, erreur conservée et aucun abandon durable ;
contre-test d'un obstacle réellement durable. Ne pas supprimer la mémoire d'abandon
pour contourner la perte d'information.

### R19 [P2] — Le rollback AIR suppose tous les avions encore arrêtés

**Références :**
[`builder_air.nut:8898–8909`](../ai/OpexAI/builder_air.nut#L8898-L8909),
[`9195–9230`](../ai/OpexAI/builder_air.nut#L9195-L9230),
[`task_air.nut:513–570`](../ai/OpexAI/task_air.nut#L513-L570).

Après constitution du lot, les avions sont démarrés successivement. Si un démarrage
ultérieur échoue, tout le lot est transmis à `OpexAirRollback`. Celui-ci suppose
les avions encore arrêtés au hangar, ignore les résultats de vente et de suppression
des aéroports, puis l'appelant rejette le projet sans enregistrer une ligne.

**Scénario conditionnel :** deux avions achetés, premier démarré, second démarrage
refusé. Le premier n'est plus nécessairement vendable et peut empêcher le nettoyage.
Un survivant n'est pas transmis comme état de récupération suivi. Le défaut de
contrat est établi ; aucun déclencheur naturel de ce second refus ni fréquence
d'occurrence n'a été démontré.

**Exposition :** pas le chantier initial ordinaire limité à un avion. Le cas
`c121_air_economics=1` et `c121_aaa_line=1` prévoit un lot initial de deux appareils ;
les options restent OFF par défaut et liées dans
[`settings.nut:283–284`](../ai/OpexAI/settings.nut#L283-L284).

**Proposition :** suivre séparément les avions achetés, démarrés et liquidés.
Enregistrer un service partiellement opérationnel ou maintenir un état de
récupération jusqu'à vente confirmée. Ne pas déduire le succès du nettoyage de
la seule émission des commandes ; préserver les hubs réutilisés.

**Validation future :** refus au premier puis au second démarrage, refus de vente,
aéroport occupé ; chaque survivant doit rester suivi et un retry ne doit pas
dupliquer le service. Ajouter Save/Load si un état de récupération est introduit.

### R20 [P2] — Le rechargement efface le régime stratégique verrouillé

**Références :**
[`globals_pre.nut:426–431`](../ai/OpexAI/globals_pre.nut#L426-L431),
[`projects.nut:1351–1372`](../ai/OpexAI/projects.nut#L1351-L1372),
[`persist.nut:536–747`](../ai/OpexAI/persist.nut#L536-L747),
[`settings.nut:303–312`](../ai/OpexAI/settings.nut#L303-L312).

Le compteur d'années observées et le régime sont initialisés à 0 et −1. Après
deux clôtures annuelles, le classifieur verrouille `race` ou `efficiency` pour
éviter que la politique ne modifie ensuite son propre signal. Ni ce verrou ni
son historique d'observation ne sont sauvegardés/restaurés ; le chargement des
réglages remet aussi les accumulateurs de pression à `null`.

**Scénario :** sauvegarder un régime verrouillé puis recharger avec les mêmes
réglages. Même avec `save_full_state=1`, le régime repart en observation ; il peut
ensuite être reclassé sur un monde déjà modifié par la politique antérieure.

**Impact et exposition :** sous C121 adaptatif, la perte d'`efficiency` ramène le
facteur à 1 au lieu du soft25 applicable
([`projects.nut:208–221`](../ai/OpexAI/projects.nut#L208-L221)). Sous
`c122_air_regime_priority`, perdre `race` désactive temporairement le départage
stratégique ([`projects.nut:1661–1673`](../ai/OpexAI/projects.nut#L1661-L1673),
[`2223–2228`](../ai/OpexAI/projects.nut#L2223-L2228)). Ces traitements sont OFF au
défaut ; le shadow seul ne réordonne pas les projets. Défaut distinct de R5.

**Proposition :** persister un petit état versionné contenant le régime, la
progression et les observations requises. Le restaurer après les remises à zéro
des réglages, sans reclassifier un régime déjà verrouillé. Définir la migration
des sauvegardes anciennes et respecter les types sérialisables NoAI.

**Validation future :** parcours complet `Save → Load → Start` avant classification,
puis après verrou `race` et `efficiency` ; vérifier facteur, ordre des candidats
et stabilité du verrou. Tester une ancienne sauvegarde sans ces champs.

### R21 [P2] — La disparition du destinataire fret ne déclenche pas le retrait

**Références :**
[`task_report.nut:512–537`](../ai/OpexAI/task_report.nut#L512-L537),
[`745–755`](../ai/OpexAI/task_report.nut#L745-L755),
[`event_handlers.nut:305–325`](../ai/OpexAI/event_handlers.nut#L305-L325).

Le reporting lit `dstAlive` mais ne l'utilise que pour le diagnostic. Le critère
`collapsed` exige une source fermée ou sans production, puis l'absence de revenu
implicite. Si la source continue à produire, `deadStreak` revient à zéro même si
la ligne n'a plus aucun débouché.

**Scénario :** usine destinataire fermée, aucun autre établissement n'acceptant le
cargo à destination, source toujours productive, plusieurs exercices sans recettes.
La flotte continue à coûter sans atteindre le critère annuel de rebut.

**Exposition :** fret au défaut. L'événement de fermeture invalide les candidats
mais ne ferme/réaffecte pas les lignes existantes. Le filet des véhicules
déficitaires est conditionné par `policy_vehicle_events`, défaut 0
([`info.nut:784–789`](../ai/OpexAI/info.nut#L784-L789),
[`event_handlers.nut:201–274`](../ai/OpexAI/event_handlers.nut#L201-L274)). Le timeout
de rebut ne protège pas une ligne qui n'entre jamais dans ce processus.

**Proposition :** intégrer la perte effective du débouché, avec contrôle de
l'acceptation du cargo et hystérésis sur l'absence de recettes. Ne pas fermer
automatiquement sur le seul IndustryID disparu : une industrie voisine ou une
destination urbaine peut rester valide.

**Validation future :** source productive, destinataire fermé et plus aucune
acceptation pendant deux exercices ; contre-tests avec acceptation voisine ou
destination urbaine. Vérifier le chemin annuel jusqu'au retrait, pas seulement
la formule locale de `deadStreak`.

### R22 [P2] — La relance d'une retraite peut annuler l'envoi au dépôt

**Références :**
[`event_handlers.nut:230–235`](../ai/OpexAI/event_handlers.nut#L230-L235),
[`task_report.nut:859–907`](../ai/OpexAI/task_report.nut#L859-L907),
[`builder_air.nut:4305–4318`](../ai/OpexAI/builder_air.nut#L4305-L4318).

Un ticket mémorise l'envoi au dépôt. Après 90 jours, `_scrapRetiredVehicles`
réémet `SendVehicleToDepot` sans vérifier si la diversion est toujours active.
Le caractère basculant de cette commande est déjà explicitement traité ailleurs
dans le code : un deuxième appel peut annuler le premier.

**Scénario :** une approche dure plus de 90 jours, par distance ou congestion.
La relance annule l'approche, mais son succès met à jour `lastSendDate` et
incrémente `attempts`. Les passages suivants peuvent alterner renvoi et annulation.
La vente réussit normalement si le véhicule arrive avant la relance.

**Exposition :** tickets créés sous `policy_vehicle_events=1`, défaut 0. Un ticket
déjà présent est néanmoins traité indépendamment de ce réglage et persiste dans
[`persist.nut:657,703`](../ai/OpexAI/persist.nut#L657-L703). Le timeout de deux ans
annule la retraite et restaure l'inventaire ; il ne rend pas la relance correcte.

**Proposition :** rendre la relance idempotente et suivre la diversion possédée
par le retrait. Ne réémettre que si elle a réellement disparu ; ne pas supposer
qu'une diversion manuelle appartient à la liste ordinaire des ordres.

**Validation future :** approche encore active à J+91, diversion effectivement
perdue, arrivée au dépôt, puis Save/Load. Vérifier absence d'annulation intempestive
et vente unique. La sémantique moteur et ces scénarios restent à exercer en test.

### R23 [P2] — Un devis rail partiellement échoué devient du capital physique

**Références :**
[`builder_rail.nut:1637–1694`](../ai/OpexAI/builder_rail.nut#L1637-L1694),
[`1733–1782`](../ai/OpexAI/builder_rail.nut#L1733-L1782),
[`economy.nut:468–483`](../ai/OpexAI/economy.nut#L468-L483),
[`task_rail.nut:1256–1291`](../ai/OpexAI/task_rail.nut#L1256-L1291).

`OpexSimulateRailInfraCost` ignore les retours des commandes simulées de gares,
voie, ponts et tunnels. `OpexQuoteRailCapital` accepte toute somme d'infrastructure
positive ; elle remplace ensuite le capital et reçoit `capitalIsActual=true`.
Un coût partiel peut ainsi être pris pour un devis physique valide.

**Scénario :** entre la recherche A* et sa consommation, un concurrent occupe
une tuile intérieure. Les gares et d'autres segments passent le devis, l'obstacle
échoue, mais le total reste positif. Les gares peuvent être réellement engagées
avant l'échec de la voie. Le contrôle des slots train et celui de caisse ne
détectent pas cet obstacle.

**Exposition :** `policy_rail=1` active les devis au défaut. Les contrôles de stock
A* optionnels ne sont pas une garde générale. Le constructeur réel détecte
l'échec et appelle le rollback : ce constat ne démontre ni ruine persistante ni
blocage permanent, mais des dépenses évitables et un marquage économique trompeur.

**Proposition :** distinguer coût, validité et premier motif d'échec ; ne pas
publier un coût partiel comme physique. Examiner la réutilisation de
[`OpexTestRailTrack`](../ai/OpexAI/builder_rail.nut#L1088-L1125), sans rejeter une
voie déjà compatible ni confondre impossibilité réelle et dépendance à une étape
que `AITestMode` ne matérialise pas. Un test de connectivité après pose seulement
simulée ne serait pas une correction valide.

**Validation future :** obstacle ajouté après A*, total simulé partiel positif,
aucune gare réellement engagée et absence de `capitalIsActual` invalide.
Contre-tests : tracé libre, voie compatible existante, pont/tunnel et manque de
trésorerie. Ne pas mélanger cette correction avec une optimisation du pathfinder.

### R24 [P2] — Le verdict d'adoption ne garantit pas le protocole d'adoption

**Références :**
[`bench_1v1_5y_20seeds.py:1262–1263`](../sweeps/bench_1v1_5y_20seeds.py#L1262-L1263),
[`1398–1500`](../sweeps/bench_1v1_5y_20seeds.py#L1398-L1500),
[`test_campaign_freeze.py:466–559`](../sweeps/test_campaign_freeze.py#L466-L559).

Chaque couple graine/répétition devient une observation. L'éligibilité utilise
`planned == 20` (ou 40), sans exiger autant de graines distinctes ni l'horizon
d'adoption. Le lanceur transmet librement les répétitions et la durée
([`run_c66_reference.py:63–68`](../sweeps/run_c66_reference.py#L63-L68)).

**Scénarios synthétiques, non exécutés :** une graine répétée vingt fois avec des
deltas favorables peut recevoir `pass` ; vingt paires d'un an également. Le test
existant construit justement un cas `years=1` et exige `pass`. Il valide le calcul
statistique, pas sa conformité au protocole 20 graines × 10 ans.

**Impact :** risque de traiter des répétitions d'une même carte comme des preuves
indépendantes de robustesse et de confondre résultat diagnostique et adoption.
Cela ne prouve pas qu'une campagne passée a effectivement été adoptée à tort.

**Proposition :** séparer verdict statistique et éligibilité au protocole ; vérifier
horizon et graines distinctes. Agréger les répétitions par graine ou employer une
inférence explicitement regroupée. Garder une voie diagnostique pour les bancs
courts et respecter la règle d'adoption réellement choisie, notamment pour les
optimisations d'opcodes ; ne pas durcir arbitrairement tous les seuils.

**Validation future :** fixtures 1 graine ×20 répétitions, 5×4, 20 graines ×1 an,
puis 20 graines distinctes ×10 ans. Les trois premiers cas doivent rester
inéligibles à l'adoption même si leur résultat statistique est favorable.

### R25 [P2] — Un trimestre invalide disparaît du profit annuel

**Références :**
[`bench_v2.py:370–390`](../sweeps/bench_v2.py#L370-L390),
[`bench_1v1_5y_20seeds.py:844–881`](../sweeps/bench_1v1_5y_20seeds.py#L844-L881),
[`1285–1291`](../sweeps/bench_1v1_5y_20seeds.py#L1285-L1291),
[`game_health.py:535–600`](../sweeps/game_health.py#L535-L600).

`quarter_profit` retourne `None` si un champ manque. `year_profit` retire ensuite
ces valeurs et additionne les autres. La comparaison vérifie que la métrique est
non nulle, sans connaître le nombre de trimestres valides. La complétude des
checkpoints mensuels ne contrôle pas cette couverture économique interne.

**Scénario :** une compagnie mature a quatre entrées trimestrielles ; une entrée
présente ne possède pas `expenses`. Le total des trois autres devient un
`profit_year` numérique admissible si les autres contrôles passent. Si l'entrée
omise était déficitaire, ce total est artificiellement augmenté ; l'erreur peut
aussi agir dans l'autre sens et inverser le delta.

**Distinction nécessaire :** ce n'est pas l'historique légitimement court du début
de partie. Une entrée présente mais invalide ne doit pas être assimilée à une
période encore inexistante. Aucune occurrence réelle de décodage partiel n'a été
mesurée dans cette revue.

**Proposition :** publier nombre de trimestres disponibles/valides et statut de
couverture. Rendre une fenêtre avec entrée invalide non admissible, sans imputer
zéro ; préserver la distinction entre démarrage et donnée corrompue.

**Validation future :** quatre trimestres valides, historique initial court, puis
champ absent dans chacune des quatre positions, y compris un trimestre déficitaire.
Vérifier la propagation jusqu'au verdict `incomplete`, pas seulement le helper.

### R26 [P2] — Le harnais figé n'est pas imposé à l'exécution

**Références :**
[`campaign_freeze.py:408–411`](../sweeps/campaign_freeze.py#L408-L411),
[`bench_1v1_5y_20seeds.py:1725–1740`](../sweeps/bench_1v1_5y_20seeds.py#L1725-L1740),
[`run_c66_reference.py:59–60`](../sweeps/run_c66_reference.py#L59-L60),
[`105–109`](../sweeps/run_c66_reference.py#L105-L109).

Le gel copie et empreinte les fichiers du harnais dans le bundle. Le lanceur
exécute pourtant le script du dépôt monté. Lorsqu'il est lancé comme script,
celui-ci réimporte après le gel `bench_1v1_5y_20seeds` par son nom pour fournir
`result_processor`, sans imposer le chemin du bundle.

**Scénario de concurrence :** une modification du collecteur survient après sa
copie et avant ce réimport. Le nouveau code peut être exécuté alors que les
métadonnées identifient le bundle précédent. Comparer ces métadonnées ne prouve
pas la provenance du module chargé.

**Limite :** le défaut est une garantie de reproductibilité incomplète ; sans
modification concurrente, cette divergence précise n'est pas démontrée. Les deux
IA utilisent bien leurs copies figées : ne pas généraliser ce constat à un gel
entièrement absent.

**Proposition :** séparer préparation et exécution, puis lancer le harnais figé
avec imports et racines de ressources maîtrisés. Une simple copie supplémentaire
ou un contrôle d'empreinte des IA ne suffit pas.

**Validation future :** figer un collecteur A dans une fixture temporaire,
remplacer uniquement l'original par B, puis vérifier que A est utilisé et que
ses dépendances viennent des sources prévues. Cette régression de provenance ne
nécessite pas de partie ; l'intégration réelle du harnais doit ensuite être validée.

### Axes sans nouveau défaut retenu et protections observées

#### Ordonnancement/opcodes : exposition à mesurer avant correction

La rotation de fond avance le curseur et les échéances
([`scheduler.nut:183–230`](../ai/OpexAI/scheduler.nut#L183-L230)). Cela garantit
une progression logique, pas une borne de latence en jours. Les intentions
réactives et workers peuvent retarder le fond
([`orchestrator.nut:726–743`](../ai/OpexAI/orchestrator.nut#L726-L743),
[`803–828`](../ai/OpexAI/orchestrator.nut#L803-L828)), mais l'absence de quota
anti-famine est déjà une décision explicite. Aucun flux durablement saturant
nouveau n'a été établi.

Le repli C77 synchrone lorsque certains workers occupent le registre est connu
([`orchestrator.nut:537–550`](../ai/OpexAI/orchestrator.nut#L537-L550)) et concerne
des options désactivées par défaut. Ne pas ajouter de quota ou de sommeil arbitraire.
Mesurer durée des replis, passages sans service du fond et délai entre financement
possible et tentative. R4 reste le défaut déjà identifié, non une découverte répétée.

#### Économie : pas de nouvelle contradiction suffisante

Les blocs lus distinguent rotations passagers bidirectionnelles et fret, coûts
annuels et revenus mensuels ; le cash-flow C69/C75 utilise les dépenses signées
des trimestres clos. C121 emploie la cadence réellement admise pour borner la
capacité et retranche la cannibalisation
([`builder_air.nut:2878–3006`](../ai/OpexAI/builder_air.nut#L2878-L3006)).

Les conventions 30/30,4 jours ne constituent pas à elles seules une preuve de bug.
Profit moyen versus marginal est déjà signalé dans R2. L'exactitude prédictive
des modèles, des sources de demande et des observations de hubs reste à mesurer ;
leur présence ne prouve pas leur calibration.

#### Modes et récupération : gardes réelles à conserver

- AIR : revalidation avant engagement, ordres vérifiés avant démarrage et hubs
  réutilisés exclus du rollback. La conservation de A après échec B sans frais
  de maintenance est intentionnelle et dispose d'une redécouverte d'orphelins ;
  elle n'est pas retenue comme défaut.
- Persistance : contrôle des endpoints et véhicules, abandon explicite d'un A*
  non sérialisé et réarmement du catalogue. Ces gardes ne compensent pas R5/R20.
- Rail : slot train contrôlé avant dépenses, raccordement du dépôt et longueur
  des convois vérifiés. Signalisation et blocages non audités exhaustivement.
- Route : chemins voirie/repli borné et revalidation du raccordement des arrêts
  observés ; pas de verdict global sur coûts, moteurs ou exploitation.
- Eau : le mode courant n'est pas globalement désarmé. Catalogue de navires et
  BFS borné existent ; Lakes est retiré. Un échec du BFS borné n'est pas une preuve
  universelle d'inaccessibilité et ne justifie pas de restaurer Lakes.
- Banc : appariement, propriétaires des données, copies des IA, refus d'écraser
  une campagne et contrôles de santé existent. R24–R26 complètent ces protections,
  ils ne signifient pas qu'aucune validation n'est faite.

#### Concurrence : fragilité connue, pas nouveau chantier adopté

Le watcher C83 peut considérer une menace comme déjà traitée lorsqu'un projet est
finançable, puis ne pas réagir à sa persistance après rejet du site. Cela établit
une absence de reprise par ce watcher, pas un gel de toute régénération.

Ce scénario et le prototype de retry C122 sont déjà documentés dans
la [fiche C122](44_c122_air_regime_priority_20260929.md). Il n'est ni recompté comme nouveau R,
ni utilisé pour lever l'arrêt au smoke ou activer C122. C77 traite déjà certaines
prises périssables ; C122 ne remplace pas universellement l'ordre économique.

Trois pistes de mesure, sans lancement ni adoption :

1. Chaîne passive menace → candidat → financement → tentative → acquisition/perte,
   avec motifs de rejet et délais ; instrumentation symétrique des deux bras.
2. Observation de la valeur de l'attente : projet non finançable, manque de capital,
   flux et menace locale, avant toute politique d'attente.
3. Exposition des inversions territoriales réellement disponibles entre projets
   finançables, puis effets sur flotte et modes évincés ; ne pas confondre annotation
   et décision effectivement modifiée.

### Priorisation et validation proposées

1. **Sécuriser la preuve avant tout verdict d'adoption : R24–R26**, par fixtures
   du harnais, couverture trimestrielle et provenance du collecteur.
2. **Traiter séparément les défauts exposés au défaut : R18, R21 et R23**, avec
   injection d'échecs et contre-tests des récupérations existantes.
3. **Qualifier les chemins optionnels : R19, R20 et R22**, sans activer leurs
   réglages au défaut et avec Save/Load lorsque l'état suivi change.
4. Poursuivre les mesures de latence, justesse prédictive et concurrence seulement
   avec une hypothèse bornée. Les correctifs R1–R5 restent à qualifier en parallèle
   de cette priorisation documentaire ; aucun n'est implicitement résolu.

Tests ciblés et smoke 1×1 pour les changements Squirrel ; diagnostic apparié 5×6
si comportement modifié ; banc 20×10 complet et sain avant adoption selon les
règles du dépôt. Ne pas prétendre qu'une suite Python compile Squirrel, ni qu'un
test de mécanisme démontre un gain économique. Le protocole des optimisations
d'opcodes reste distinct du seuil d'effet utile des changements de politique.

**État final : huit axes examinés, neuf nouveaux constats consignés, aucune
correction implémentée ni validée en partie. Le rapport contient désormais
R1–R26 ; `docs/taches.md` demeure la seule liste autoritaire des travaux adoptés.**

## Début d'implémentation — R24/R25, validation en attente

Sur demande utilisateur, deux lots ont été commencés après la consolidation.
Le lancement d'agents délégués n'étant plus disponible dans cette session,
**aucun nouvel agent d'implémentation n'a été lancé** : éditions réalisées
séquentiellement, avec intégration finale du collecteur partagé.

| Lot | Modifications locales | Statut |
|---|---|---|
| R24 | `policy_adoption_eligibility`, motifs d'inéligibilité publiés dans `adoption_protocol` ; 20/40 graines distinctes ×10 ans, une répétition ; fixtures d'adoption existantes corrigées et régressions ajoutées | Implémenté, tests non exécutés |
| R25 | `year_profit_metrics`, aucune omission de trimestre invalide ; couverture `missing`/`partial`/`invalid`/`complete` et compteurs ; propagation aux collecteurs solo/duel et au résumé | Implémenté, tests non exécutés |
| R26 | Non commencé ; même fichier duel que R24 et intégration R25 | À traiter séparément après validation |

Les bancs courts ou répétés restent calculables à titre diagnostique : pas de
remplacement des statistiques par une inférence regroupée improvisée. Un historique
court valide conserve sa somme partielle, sans multiplication ni imputation à zéro.
La couverture ne permet pas à elle seule de déduire l'âge d'une compagnie.

**Validation effective :** relecture ciblée et diagnostics éditeur sans erreur
signalée. Configuration Python impossible (`No base python found`) ; seuls des
alias Windows Store ont été trouvés. L'exécuteur de tests de l'éditeur n'a découvert
aucun test. **Ni les nouveaux tests, ni les tests existants, ni le selftest ne sont
annoncés réussis.** Aucune installation de runtime ou partie effectuée.

Les cas ajoutés couvrent notamment cartes répétées, graines dupliquées, horizons
non conformes, règles `signs20`/`mean40`, chaque champ trimestriel manquant, déficit
omis, historique court, valeurs invalides et propagation jusqu'au verdict incomplet.
Le détail et la suite sont dans le [journal](journaux/journal_2026-09-30.md) et
`docs/taches.md`. Aucun fichier `ai/OpexAI/` ni paramètre protégé n'a été modifié.

## Suite d'implémentation — R26 et workflow ciblé

Après accord utilisateur pour reporter les tests à GitHub Actions, R26 est
implémenté localement, sans attendre une validation locale indisponible :

- `sweeps/frozen_harness.py` lance un interpréteur isolé depuis le bundle et vérifie
  les empreintes avant import ; aucun module projet déjà chargé dans le processus
  vivant n'est réutilisé. Le collecteur et ses dépendances locales sont recherchés
  dans le harnais figé ; la production de bytecode y est désactivée.
- Le manifeste 1.2.0 conserve les options d'exécution. Le banc restaure les
  politiques, bibliothèques et chemins de campagne, utilise la configuration figée
  et refuse les incohérences de protocole. L'intégrité est revérifiée avant le
  rapport final ; résultats/checkpoints/logs existants ne sont pas réutilisés.
- Dix tests de provenance et deux tests de contrat supplémentaires sont ajoutés,
  notamment modification du code vivant après gel, worker `spawn`, altération du
  bundle et chemin réel du collecteur jusqu'à une frontière moteur simulée.
- `.github/workflows/benchmark-regressions.yml` prévoit des fixtures Windows/Linux,
  puis un job avec OpenTTDLab 0.0.75 et le selftest, **sans parties**. Le workflow
  `ci.yml` existant reste inchangé.

**Statut actuel R24–R26 : implémentés localement, non validés par exécution.**
Le statut antérieur de R26 dans la section précédente est historique. Aucun
workflow publié ou exécuté ici, aucun test annoncé réussi. La qualification
nécessite encore les fixtures puis un smoke moteur 1×1 ; les anciens bundles et
diagnostics autonomes ne reçoivent pas rétroactivement cette garantie de provenance.
Détails, limites et suite dans le [journal](journaux/journal_2026-09-30.md).
Tous les réglages C115/C121/C122 sont préservés ; aucun code Squirrel modifié.

## Suite Squirrel — R18/R21/R23, périmètres disjoints

Nouvelle demande utilisateur : poursuivre d'autres items sans collisions de fichiers.
Lectures parallèles et éditions séquentielles ici, faute de délégation disponible.

| Lot | Fichier métier | Correction locale | Validation |
|---|---|---|---|
| R18 | `builder_air.nut` | Résultat de nivellement explicite ; construction court-circuitée à l'échec, cause conservée jusqu'au garde financier d'abandon | 6 contrats source ajoutés, non exécutés |
| R21 | `task_report.nut` | Acceptation réelle de la gare destinataire contrôlée sans recettes ; débouché voisin/urbain préservé, hystérésis et retrait existants | 5 contrats source ajoutés, non exécutés |
| R23 | `builder_rail.nut` | Premier échec simulé rend le devis invalide ; aucune promotion du coût partiel ni dépense réelle ; retry financier conservé | 6 contrats source ajoutés, non exécutés |

Un fichier de tests distinct par lot ; documents et workflow consolidés par un seul
rédacteur. `ai-review-contracts.yml` prévoit six jobs parallèles Windows/Linux,
sans partie. R19 et R22 restent ouverts : ils partageraient les fichiers de R18/R21.

**Implémenté localement, pas qualifié.** Les tests source ne compilent pas Squirrel
et ne reproduisent pas les erreurs moteur. Restent injections ciblées, smoke 1×1,
diagnostics causaux séparés et protocole d'adoption applicable. Pas de rollback du
relief AIR, pas d'observation continue de l'acceptation fret, pas de transaction
atomique du devis rail. Détails dans le [journal](journaux/journal_2026-09-30.md).
Réglages C115/C121/C122 inchangés ; aucun gain économique ni exécution CI revendiqué.

## Groupe suivant — R2/R3/R22

Suite autorisée, après inspection des consommateurs et des contrats existants.
Fichiers disjoints au sein du groupe ; R22 intervient après R21 et le conserve.
Lectures parallèles, éditions séquentielles, consolidation unique des documents et
du workflow ; aucun agent délégué lancé.

| Lot | Fichier métier | Correction locale | Validation préparée |
|---|---|---|---|
| R2 | `projects.nut` | Provenance `profitIsObserved` fixée lors de la construction du projet ; C70/C82 ne multiplient plus le profit legacy observé. Repli prédictif, modèle C84 et exemption C121 conservés | 6 contrats source |
| R3 | `task_projects.nut` | Garde `OpexAirBatchPlanStillLive` avant le bypass pour tout projet AIR ; même quota de bypass, financement, raisons de rejet et garde final de l'exécuteur | 6 contrats source |
| R22 | `task_report.nut` | Lecture directe de `ORDER_CURRENT` et de `OF_STOP_IN_DEPOT` avant relance ; arrêt actif préservé, entretien convertible, mise à jour du ticket seulement après succès | 6 contrats source |

Le workflow `ai-review-contracts.yml` est étendu à **12 jobs** (six lots × deux OS).
Les 18 nouveaux tests sont structurels : aucune exécution Squirrel ni simulation
du moteur. Diagnostics éditeur sans erreur, ownership sans chevauchement et
présence/chargement des 19 réglages protégés vérifiés. Git absent ; pas de diff Git.

**Statut : R2/R3/R22 implémentés localement, non validés par exécution.** Aucun
test Python, lint actionlint, smoke ou workflow exécuté dans ce groupe. R22 n'est
donc plus « à implémenter » comme dans la section historique précédente, mais
reste à qualifier. R19 et R20 ne sont pas corrigés ici.

Limites : R2 conserve l'approximation profit moyen → renfort marginal ; R3 ne
prévalide pas tous les échecs physiques ni ne réserve atomiquement les sites ;
R22 ne réécrit pas l'envoi initial, le timeout ou la reprise de trajet après
timeout. Aucune nouvelle garantie de récupération globale du cycle de retraite.
Cas moteur à exercer, persistance et protocole économique dans le
[journal du 30](journaux/journal_2026-09-30.md). Réglages C115/C121/C122 intacts.

## Groupe suivant — R4/R5/R20

Suite demandée avec parallélisation maximale. Aucun outil de délégation d'agents
de fond n'est disponible : inspections indépendantes parallèles, éditions locales
séquentielles sur périmètres disjoints, puis consolidation unique.

| Lot | Fichiers métier exclusifs | Correction locale |
|---|---|---|
| R4 | `main.nut`, `scheduler_tasks.nut` | Prédicat d'admission C121 accessible à 9 000 opcodes, refus à ≤2 000, exclusions worker/rail et borne de tick ; alternance des tâches conservée |
| R5 | `orchestrator.nut` | Sortie des deux autotests C80/C76 dès l'entrée si partie rechargée, avant enfilage, effacement ou remplacement d'état |
| R20 | `persist.nut` | État stratégique versionné : régime, années observées, accumulateur de pression et année close ; tampon Load puis restauration après réglages |

R4 ajoute six tests (dont évaluation de l'expression réelle extraite, pas une VM
Squirrel), R5 six contrats et R20 huit contrats. Le test C121 qui exigeait `>10000`
est corrigé ; `ai-review-contracts.yml` sélectionne dix suites sur deux OS, soit
20 jobs. Les 19 réglages protégés restent déclarés/chargés et leurs fichiers
inchangés par cette intervention. Corrections précédentes conservées.

**Implémenté localement, non validé par exécution.** Le seuil R4 n'est pas une
mesure de coût minimal ni une borne dure de tranche. R5 évite les tests au reload,
il ne les réécrit pas sur une instance isolée. R20 accepte les options séparément,
ne persiste pas les caches, reprend un verrou valide sans reclassifier ; une
sauvegarde antérieure ou un bloc incompatible repart explicitement en observation.
Les parcours moteur, Save/Load et effets économiques restent à vérifier. Candidat
non publié et absence d'accès GitHub exploitable : aucun workflow déclenché.
R20 rejoint les items implémentés, contrairement aux statuts historiques ci-dessus ;
R1/R19 restent ouverts. Voir le journal pour le plan de validation et ses limites.

## Groupe suivant — R1/R19 : clôture locale

**Implémentés localement, non validés par exécution.** La pause a été suivie
d'une demande de terminer ce groupe seulement. Les statuts R1/R19 « ouverts »
ci-dessus décrivent les étapes antérieures ; leur validation reste due.

- **R1** : tranche AIR finançable calculée avant plancher et classement, sans
  muter le vivier ni ajouter plusieurs variantes cumulables. Réserve conservée,
  tampon d'exécution de 1 000 £ intégré au financement ; économie du lot réduit
  cohérente, C84 recalculé avec son modèle marginal, provenance R2 préservée.
  Snapshot d'effectif revalidé avant sélection et achat pour refuser une demande
  devenue caduque. Pas d'achat de flotte prioritaire hors portefeuille.
- **R19** : ticket persistant enregistré avant nettoyage, vente confirmée avant
  démolition, rappel des avions partis sans inverser un ordre halt, protection
  des hubs et installations utilisées. Reprise bornée à un ticket par tâche,
  espacement de 30 jours, rotation sans disparition temporaire de la file.
  Paire bloquée pendant liquidation, Save/Load court et complet, validation de
  format puis réconciliation après réglages. La solution choisie liquide le
  chantier rejeté ; elle ne transforme pas son service partiel en ligne réussie.

18 nouveaux tests préparés (8 R1, 10 R19), deux contrats AIR historiques adaptés.
Workflow courant : **12 suites × 2 OS = 24 jobs**, complété par C84/B6 et les
deux méthodes AIR ciblées. Contrôles source/lexicaux et diagnostics éditeur
uniquement ; aucun test Python, compilation, partie ou Save/Load exécuté.
Les 19 réglages protégés restent déclarés/chargés, sans modification de leurs
fichiers. Aucun push, installation ou workflow lancé.

Limites : pas de recherche exhaustive de tailles de flotte, approximation
marginale legacy inchangée ; une liquidation durablement impossible reste
suivie et peut bloquer la paire. Pas de réparation de tous les chemins AIR,
de transaction atomique avec le monde ou de réattribution complète des dépenses
différées. Les assertions moteur et la qualification restent à produire sur
des versions isolées. Détails, périmètres partagés et plan dans le
[journal de clôture](journaux/journal_2026-09-30.md#clôture-du-groupe-r1r19).

**14 findings implémentés localement ; R6–R17 restent à implémenter/décider.**
Le [backlog](taches.md) reste la seule liste autoritaire des actions ouvertes.