# INVEST-STALL : autopsie des obstacles et pistes de résolution — 04/11/2026

## Périmètre

Analyse de **la révision de quais du 04/11**, sur `exp/rail-sibling-20261102`,
arbre local non commité, paramètre `invest_stall=0` conservé. Les deux duels
appariés et leurs empreintes sont consignés dans
[`invest_stall_platform_qualification_20261104.md`](invest_stall_platform_qualification_20261104.md).
Cette note est une **analyse de traces et de source**, sans nouveau banc,
mutation de comportement ou verdict d'adoption.

Les agrégats ont été extraits avec `sweeps/analyse_invest_stall_v2.py`,
politique `invest_stall_platform`, depuis les dossiers `_engine` des
campagnes `invest_stall_platform_exposure_4x6_20261104_a` et
`invest_stall_platform_exposure_2x8_20261104_a`. Résultats de dépouillement :
`results/invest_stall_platform_obstacles_{4x6,2x8}_20261104.{json,csv}`.
Le 2×8 prolonge deux graines du 4×6 : ses comptes sont **cumulatifs et non
indépendants**. Les compteurs sont des événements/réexamens, non des industries
distinctes, ni des profits prouvés.

## 1. Principal goulet : 37 renforcements choisis, aucun terminé

| Événement INVEST-STALL | 4×6, quatre graines | 2×8, graines 17 et 65537 |
| --- | ---: | ---: |
| `pick route=fleet kind=wagon` | 24 | **37** |
| `skip reason=invest_stall_recheck` | 16 | **30** |
| `skip reason=approach_timeout` | 5 | **6** |
| `done route=fleet` | **0** | **0** |
| `skip reason=nonpositive_margin_or_traction` | 152 | 254 |
| `kind=platform reason=unsafe_or_busy` | 12 | 24 |

Dans le 2×8, les 37 sélections se concentrent sur **10 lignes distinctes** :
graine 17, 20 sélections sur 5 lignes (notamment ligne 22 : 8 fois) ;
graine 65537, 17 sélections sur 5 lignes (ligne 2 : 7 fois).
On ne peut pas associer exactement chaque refus à un achat sans identifiant
unique de transaction, mais il n'existe **aucun DONE** physique. La sélection
répétée consomme du temps de simulation, des inspections et des détours vers
le dépôt, sans nouvelle capacité attestée.

**Source :** `invest_stall_fleet.nut:179-307` crée une intention
`pending.phase="approach"` après un calcul de marge positive, puis
`task_v284.nut:515-615` doit approcher le dépôt et refaire la mesure.
La revalidation (`task_v284.nut:575-595`) réexige notamment :
production/rating/capacité de l'origine (`OpexInvestStallSourceGap`),
marge nette positive, caisse, locomotive/wagons identiques et homogènes,
aucune autre transaction, aucune recherche/extension concurrente,
une seule rame inchangée et pas de nouveau train.

**Ce qui est prouvé :** 30 sorties portent le motif **groupé**
`invest_stall_recheck` ; certaines interviennent dès le lendemain du
`pick` (ex. graine 17, ligne 6, du 26 au 27/06/1977).
**Ce qui manque :** le détail de la clause refusée. Il serait abusif
d'affirmer que les 30 échecs viennent de la marge, de la caisse ou d'une
concurrence de tâches : la trace agrège toutes ces causes.

**Action P0, sans modification de comportement :** journaliser à la
revalidation de V284, uniquement sous INVEST_STALL + DECISION_LOG :
`reason_code` exclusif avec priorité stable et une table diagnostique des
booléens pour les refus multiples (`gap.reason`, `margin_null`,
`source_capacity`, `rated_offer`, `monthly_extra`, `profit`,
`capital`, `pending_*_conflict`, `line_vehicle_changed`,
`wagon_count_changed`, `engine_rail_incompatible`, `cash_recheck`).
Attribuer `transaction_id` (ligne, date, véhicule) aux `pick`,
`approach`, `depot`, `cancel`, `done` et `rollback`.
Comparer le devis initial à la même ligne juste avant annulation.

**Action P1 suivant la cause vérifiée :** si les échecs viennent d'un
travailleur lancé entre sélection et passage au dépôt, réserver
explicitement un créneau exclusif **pendant la courte phase d'achat**.
Si la variation de production mensuelle ou de note provoque des
annulations de marge, conserver la revalidation avant achat, puis
tester un estimateur sur une offre lissée et une règle de persistance
bornée ; jamais acheter quand le gain marginal actualisé est négatif.
Si un véhicule change entre-temps, abandonner la transaction et
réévaluer le véhicule réel ; ne pas ignorer le changement.

## 2. Délai d'approche : six expirations sans achat

`task_v284.nut:515-529` exige d'abord une rame **vide** à huit tuiles
au plus du dépôt (`RAIL_EXPAND_APPROACH_TILES=8`, `main.nut:37`) avant
d'émettre `SendVehicleToDepot`. Le budget de sélection est calculé
par distance/vitesse, puis borné à 120–730 jours
(`invest_stall_fleet.nut:290-301`).
Une rame qui passe près du dépôt encore chargée, ou une rotation longue,
peut donc être choisie plusieurs fois sans jamais y entrer à temps.

**Piste P1 :** journaliser jours depuis choix, distance minimale au
dépôt, passages vides dans son voisinage, statut des ordres et dernier
déchargement. Si l'absence de fenêtre vide est confirmée, planifier
un retour dépôt à la **première occasion après déchargement**, sans
détour chargé, avec borne de durée dérivée du cycle observé ;
réconcilier l'ordre temporaire après Save/Load et vérifier l'absence
de rames perdues. Un délai simplement augmenté masquerait le blocage.

## 3. Quais : refus générique et deux incompatibilités démontrables

`OpexInvestStallPlatformPlan` (`invest_stall_fleet.nut:91-130`)
emploie un premier `if` qui renvoie **un seul**
`unsafe_or_busy` pour les causes suivantes : transaction concurrente
(`OpexInvestStallPlatformSlotFree`), ligne non sûre
(`OpexRailLongV2LineSafe`), et plans A/B incohérents avec
`line.platformLength`. Ce refus est émis **avant** la boucle des
longueurs et la construction de devis.

Les deux lignes responsables des **24 événements** du 2×8 :

| Graine, ligne | État observé dans `RAIL_BUILD` et `LINE_REVENUE` | Obstacle |
| --- | --- | --- |
| 17, ligne 27, WOOD | `reuse=1 join_end=B shared_dest=1` (02/11/1972), 5 wagons, quai de 3 tuiles jusqu'en 1977 ; 10 refus | `OpexRailLongV2LineSafe` refuse toute gare partagée avec une autre ligne (`task_rail_long_v2.nut:157-168`). Le partage à la création est confirmé, sa persistance lors de chaque refus reste à contrôler |
| 65537, ligne 18, GOOD | `reuse=0` (28/09/1971), 13 wagons, quai de **8 tuiles** jusqu'en 1977 ; 14 refus | Le planificateur limite `target` à **7**, puis 6, et impose `target > line.platformLength` : même si la garde initiale passait, il n'existerait **aucun** candidat d'extension pour un quai de 8 |

Important : le quai de 8 tuiles **ne peut pas être la cause directe du
message `unsafe_or_busy`**, puisque le test de taille vient plus tard.
Les 14 refus de la ligne 18 cachent donc une autre condition échouée,
indépendante de l'impossibilité de son extension. Même distinction
pour la ligne 27 : son partage est un motif **plausible**, pas un
diagnostic de garde confirmé à chaque date.

**Action P0 :** remplacer le motif regroupé par un journal de refus
sans effet sur la décision : `slot_active_worker`,
`rail_search_busy`, `v284_pending`, `po01c_pending`,
`other_transaction`, `station_shared_A/B`, `line_shape`,
`platform_plan_mismatch`, `at_or_above_game_length`,
`at_or_above_target`. Journaliser ancien quai, cible calculée,
longueur réelle de rame, limite de longueur du jeu, nombre
de wagons, nombre de gares utilisatrices, tuiles candidates.

**Piste P1 géométrique :** distinguer la **place supplémentaire réellement
nécessaire** (souvent une seule tuile pour un wagon vanilla) de l'objectif
de taille 7/6. Tester des longueurs à partir du minimum capable de
contenir la nouvelle rame, jusqu'au plafond autorisé ; contrôler
séparément A et B, ainsi que les obstacles de chaque tuile, avant devis.
Pour les quais déjà ≥ maximum du jeu, la réponse est `no_extension_needed`
ou `length_cap` selon la longueur réelle, puis explorer un autre
mode de capacité ; ne jamais tenter un « agrandissement » 8→7.

**Piste P2 gares partagées :** examiner une extension seulement sur
un quai dont les **tuiles ajoutées** peuvent être certifiées
sans train voisin, sans chevauchement de voies, ni changement des
interfaces existantes et de leurs ordres. Adapter la certification
à un ensemble de quais physiques plutôt qu'au seul StationID
global. Si la séparation ne peut être prouvée, refuser. Ne jamais
retirer la garde de partage sans preuve topologique et test de trafic.

**Piste P2 planification :** `OpexRailLongV2ExtendPlan`
(`task_rail_long_v2.nut:20-60`) rallonge uniquement le côté opposé
à la voie de sortie, avec tuiles plates et constructibles. Les
obstacles de terrain, pente, bâtiment ou voisinage sont refusés ;
un contournement ponctuel ou un terrassement ne serait envisageable
qu'après identification des tiles bloquantes et tests de propriété
sans destruction d'infrastructure. La vérification de proximité
des véhicules est bornée à 256 entrées
(`task_rail_long_v2.nut:95-112`) : le plafond doit être instrumenté
avant d'être changé.

## 4. Seconde gare : le mécanisme passe parfois, mais très rarement

Dans le 2×8, on voit **117 `origin_candidate`**, **4 `site_ok`**,
**3 `site_reject reason=no_independent_station`**, **1
`station_built` et 1 `build_ok`**. Dans le 4×6,
34 candidatures, 3 `site_ok`, 2 `build_ok`.
Ce ne sont pas des ratios de conversion : les candidatures peuvent
être régénérées et ne sont pas toutes sélectionnées ou construites.

`candidates.nut:1597-1674` réclame une origine industriellement valide,
non encore doublée, une autre destination et une capacité résiduelle.
Le filtre donne priorité à un wagon réellement constructible et rentable
sur la gare mère ; si ce dernier est jugé possible il bloque la
deuxième gare (`fleet_headroom`). **156 réexamens** de ce motif
sur 2×8, alors que **zéro achat INVEST-STALL** n'aboutit.
Cela révèle un **décalage potentiel** : « wagon économiquement
possible à la sélection » ne signifie pas « wagon exécuté ».
La note de gare insuffisante donne aussi **147 événements**
`origin_fleet_blocked reason=rating_supply`.

**Piste P1 :** laisser sa priorité à la flotte, mais après un
échec physique daté et catégorisé (`approach_timeout`,
`recheck`, traction indisponible...), autoriser une
réévaluation de la seconde gare avec cooldown borné et devis
réel. Ne pas traiter chaque refus comme une permission automatique
de construire : vérifier le captage, la distance, le coût, la
rentabilité nette et l'absence d'interférence. Ajouter une mémoire
de tentative par **source + cargo + station mère**, persistée
si elle influence la décision.

**Piste P2 :** `OpexInvestStallSecondStationPlans`
(`builder_rail.nut:1692-1732`) prend jusqu'à 48 propositions
au départ, conserve 12 plans A indépendants et exige aussi
un site B. Décomposer les `no_independent_station` en
absence de source indépendante, de destination, de terrain
plat, ou rejet de jonction. Ne rechercher plus large qu'en cas
d'opportunité économiquement admissible ; pas de balayage
global supplémentaire.

## 5. Autres filtres économiques et sécurité des transactions

- **254 refus `nonpositive_margin_or_traction`** dans le 2×8 :
  ce motif confond impossibilité d'engin, marge incrémentale
  nulle/négative, offre captée insuffisante et caisse. La marge
  `invest_stall_fleet.nut:18-55` soustrait le remplacement
  complet et son amortissement, avec vitesse non dégradée.
  Séparer les sous-causes avant de toucher aux seuils.
- **Modèle de débit volatile :** `OpexInvestStallSourceGap`
  (`invest_stall.nut:73-129`) utilise la production du
  dernier mois, le pourcentage transporté tous opérateurs et
  une note de gare instantanée. Dans la graine 65537,
  ligne 18 GOOD, la production consignée varie de 93 à
  918 unités selon les mois de 1977 ; des candidatures
  nouvelles sont ensuite émises avec des offres allant de
  200 à 799 unités/mois. Tester moyenne/quantile de production
  sur plusieurs mois et plafonnement par cargo réellement
  disponible ; comparer prédictions et livraisons avant
  un changement de formule.
- **Deuxième rame interdite :** `OpexInvestStallFleetTrainCertified`
  (`invest_stall_fleet.nut:62-65`) renvoie toujours false.
  C'est un verrou de sûreté explicite, pas une panne.
  Une extension de capacité sur quai saturé exige une
  certification effective de double voie/PBS, dépôt, ordres
  et rotations, et un test moteur d'absence de train perdu.
- **Transaction de quai non exercée :** la persistance
  `_railLongV2Pending` et le moteur de rollback existent
  (`task_rail_long_v2.nut:204-220,411-597`). Le Save/Load
  du 01/02/1975 a prouvé la reprise de l'IA, **pas**
  le traitement d'une transaction interrompue. Tester les
  phases `intent_a`, `intent_b`, `commit` et `rollback`
  sur un véritable jeu rechargé, en contrôlant
  StationID, propriété et tuiles avant/après, y compris
  `orphan_safe`. Ne pas fabriquer de succès à partir de
  tests statiques ou d'un appel `Load()` générique.

## Priorités et protocole proposé

1. **P0 diagnostic passif, sans effet OFF :** décomposer les refus
   au dépôt et `unsafe_or_busy` avec identifiants de transaction ;
   vérifier par contrat que les événements contiennent des motifs
   exclusifs, et par smoke NoAI que la sonde est active.
   Le premier objectif mesurable est d'expliquer au moins 90 %
   des 30 `invest_stall_recheck` et des 24 `unsafe_or_busy`
   de cette famille, sans modifier les décisions.
2. **P1 libérer l'achat existant :** corriger seulement la cause
   dominante prouvée des rechecks ou des expirations. Smoke ciblé
   sur graines 17 et 65537 avec **`done` physique attesté**,
   ligne encore mobile, capacité effectivement accrue,
   ancien train repris/supprimé proprement, ordre valide et
   aucun échec NoAI. Contrôler que le gain vient du débit
   et du profit de la ligne, pas seulement du nombre de
   `pick`.
3. **P2 traiter les quais :** cibler d'abord une ligne à
   source réellement saturée, station exclusive,
   longueur inférieure au plafond et géométrie vérifiée.
   Essayer la longueur minimale puis les alternatives
   économiques, journaliser chaque tile refusée. Tester
   des gares partagées uniquement avec nouveau certificat
   physique ; ne pas libérer globalement les contrôles.
4. **P3 Save/Load et rollback physiques :** sur une
   transaction de quai effectivement engagée, capturer
   les sauvegardes aux frontières d'intention/pose,
   provoquer un échec réversible et contrôler les
   tuiles, les rames, les ordres et les stations.
5. **P4 économie appariée :** après exposition saine et
   version figée, comparer ON/OFF du **même code** face
   à AAAHogEx rail seul, profit propre `profit_year`,
   garde de valeur selon protocole d'adoption, santé,
   nombre de trains, cargaisons livrées, vraies
   extensions et caisse. Une sélection de graines
   favorables ne suffit pas. Les 40×5 v2-r2 historiques
   étaient `fail_primary` et n'accordent aucun PASS
   à cette révision.

**Décision actuelle :** diagnostics concluants sur les goulots,
mais causalité interne des rechecks et de la garde
`unsafe_or_busy` encore non démontrée. L'adoption reste **NO-GO**,
`invest_stall=0` demeure la valeur par défaut. Aucun nouveau
smoke ou banc économique n'est lancé par cette note.
