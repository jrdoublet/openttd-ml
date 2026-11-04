# RAIL-LONG v3 : modernisation transactionnelle, 4 novembre 2026

Mandat : correction des modernisations existantes uniquement. Aucun changement
de defaut, de multihead, de politique economique ni de publication Git.

## Etat initial et conservation

Arbre `exp/rail-sibling-20261102`, HEAD `99f29d9c`, nombreux changements locaux
preexistants. Copie des quatre fichiers cibles et empreintes des fichiers
proteges avant modification :
`results/rail_long_v3_upgrade_fix_20261104_145126/`.
Le module v2 contient deja les adaptations INVEST-STALL de l'utilisateur.

## Diagnostic et intervention

- `build_a`/`build_b_or_commit` : le helper v2 refuse aussi une rame proche,
  mais v3 transformait cette occupation transitoire en abandon immediat.
  V3 attend maintenant la vacance, sans supprimer la garde v2. La pose B et
  les refus de commit ont des causes distinctes. Les anciens journaux ne
  permettent pas d'attribuer chaque refus a une erreur moteur precise.
- Ancres, directions, pas, sortie/approche et identites des deux gares sont
  revalides physiquement avant commit/adoption. Reutilisation des plans et du
  constructeur v2, choix 7 puis 6 conserve, aucune demolition historique.
- `SendVehicleToDepot` cherche un depot et agit comme une bascule si un ordre
  depot est deja actif. L'ancien code marquait le detour avant son acceptation,
  puis rappelait cette commande au rollback meme apres un echec : un nouveau
  detour pouvait etre cree au lieu d'etre annule. Le nouveau chemin ajoute un
  troisieme ordre explicite vers le depot de la ligne, seulement a vide apres
  dechargement, avec controle d'entree et de compatibilite. Son acceptation ne
  prouve pas encore son accessibilite : seule l'arrivee physique au bon depot
  l'atteste, avec timeout sinon.
- Les deux ordres historiques restent en place ; l'ordre temporaire identifie
  est retire au depot ou au rollback. Chaque commande a une intention et une
  verification idempotente pour Save/Load. Migration de l'ancien detour : ne
  basculer que si un ordre depot est effectivement courant.
- L'ancienne rame reste jusqu'a certification, ordonnancement, demarrage et
  adoption de la nouvelle. Le snapshot de nettoyage couvre maintenant tous
  les vehicules preexistants, meme ceux arrivant ensuite au depot.
- Traces : phase avant rollback, cause, cote, tuile/ancre/direction/gare,
  depot, vehicules, charge/etat/localisation et derniere erreur NoAI capturee.

Contrat officiel verifie pour OpenTTD 15.3 :
[SendVehicleToDepot](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_vehicle.hpp),
[ordres depot](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_order.hpp).
La cause exacte des anciens refus de pathfinder reste non observable dans les
anciens logs ; on ne presente pas une orientation supposee comme un fait mesure.

## Diagnostic moteur pre-enregistre avant lancement

- Campagne `rail_long_v3_upgrade_diag_4x6_20261104_r2` : quatre parties contre
  AAAHogEx, graines **17, 512, 314, 8191**, annees **1970-1975**, carte 256x256.
- Un seul bras Opex : `mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1,rail_long=3`.
  AAAHogEx rail seul. Pas de comparaison economique ni de porte d'adoption.
- Probes 6, script-debug, line-telemetry, sauvegardes conservees. Image
  `sha256:0480a863e164856797412ff4a0782621464a52087abbb9c056dd3587d46cac31`,
  contexte `desktop-linux`, cache `openttd-lab-home`, montage racine du depot,
  10 CPU, 8 GiB RAM/swap, 10 workers maximum. Code fige par le lanceur courant.
- Critere : sante de toutes les parties ; au moins un `upgrade_done`, avec
  deux quais et rame reellement verifies. Sinon documenter la cause residuelle.
  Aucun 40x5/20x10. Une correction d'erreur technique exige un nouveau bundle
  et un identifiant neuf, jamais l'ecrasement du precedent.

## Validation

R1 refuse avant toute partie : `decision_log` n'est plus un reglage declare
dans cet arbre. `settings.nut` active deja DECISION_LOG avec `probes=6`.
R2 conserve donc le masque prevu, sans ajouter ce nom de reglage obsolete.

Les contrats Python sont des controles de source hors VM ; les validations
moteur et les reprises Save/Load ci-dessous apportent leur preuve separee.

### R2 et correction de l'ordonnancement

R2 : 4/4 parties completes et saines, bundle
`b5788000f55e58a6be6ee2e57cb16776f95c95686efccea633e6a6eed3cf2c94`.
Six selections, cinq `upgrade_done`. La sixieme (graine 17, ligne 20) attend
la vacance B le 22/09/1975. Le 25/09, `V284 action=pick line=4` precede
immediatement son `context_changed` : `_expandRailLines` continuait a lancer
des renforts pendant l'intention v3, alors que l'orchestrateur bloquait leur
execution. Une reservation a l'entree de `_expandRailLines` corrige ce conflit,
y compris apres desactivation au chargement. Les autres contextes ont maintenant
des motifs distincts (`v284_busy`, `vehicle_changed`, etc.).

R3 pre-enregistre : meme diagnostic 4x6, meme graines/bras/sondes/ressources,
identifiant `rail_long_v3_upgrade_diag_4x6_20261104_r3`, pour valider cette
correction demontree ; aucune selection de resultat economique. Les anciens
bundles restent immuables. Les projecteurs OFF retirent la nouvelle reservation
avant de comparer les hunks INVEST-STALL historiques ; aucune fixture modifiee.

Save/Load cible pre-enregistre : reprendre les saves R3 de la graine 512 au
01/07/1972 (`approach`) puis au 01/08/1972 (`depot`), et de 17 au 01/01/1975
(`depot`), 120 jours par reprise. Meme bundle R3 et adversaire, adaptateur
`save_load_roundtrip.make_patched_check_output` et processeur/extracteurs du
duel figes, copies dans un dossier neuf `rail_long_v3_upgrade_reload_20261104_r1`.
Ce controle ne genere aucune carte nouvelle et ne mesure aucun effet economique.

### R3 : modernisations certifiees et alerte 8191

Le bundle R3 `b33ee55ae8e3324e07efa3a23761f8b85cf9b6fdd472d1a1118f967b2ec0b734`
a produit **4/4 parties saines**, **4 `upgrade_done`** (17 : 8 wagons/240
unites ; 512 : 9/270 ; 314 : 8/240 puis 11/330). L'audit des sauvegardes
`results/rail_long_v3_upgrade_diag_4x6_20261104_r3_physical.json` confirme
pour chacune les deux quais exacts, la rame en service et les **deux ordres
historiques uniquement**, sans ordre depot residuel. Aucun echec NoAI releve.

La graine **8191** termine les six ans et ne montre pas d'erreur moteur :
`game_ok=true`, `horizon_complete=true`, mais
`stagnation_suspect: activity=declining_without_expansion`. Cette alerte de
performance reste a analyser separement ; elle ne contredit pas la sante
technique du chantier et ne constitue pas une preuve de gain economique.

### Reprises Save/Load : anomalie trouvee et corrigee

Le premier controle pre-enregistre `rail_long_v3_upgrade_reload_20261104_r1`
reprend les trois sauvegardes R3 mais finit dans les trois cas par
`upgrade_fail reason=line_unsafe`, puis rollback. Les parties sont saines :
il s'agit d'un **refus injustifie de reprise**, pas d'un plantage.
Les bundles de diagnostic R4/R5 etablissent que `OpexRailLongV2LineSafe=true`,
les gares et rames sont valides et le profit est conserve. Seule manque
`line.cargo in owner._catalog.wagonByCargo` : le catalogue natif n'est pas
sauvegarde, alors que le premier `OpexRailLongV3UpgradeStep` arrive avant
son premier rafraichissement apres `Load`.

Le correctif cible dans `rail_long_v3_upgrade.nut` :
1. reprogramme le rafraichissement du catalogue a la reconciliation d'une
   transaction v3 pending (`_lastCatalogMonth=-1` si non initialise) ;
2. attend ce catalogue avant de juger la securite de ligne, tout en gardant
   la `deadline` persistante et les revalidations physiques et economiques ;
3. conserve la garde de wagon au choix et au devis du depot.

Le nouveau bundle **R6** `be98d35222c11fb77ab859aa88ca7d28c44f305202ad964fe66ad8bdc3a64688`
(smoke 1×1 sain) reprend ces **trois memes sauvegardes** sur 120 jours dans
`results/rail_long_v3_upgrade_reload_fix_20261104_r4` :

| Save reprise | Evenement `upgrade_done` | Rame | Controle physique |
| --- | --- | --- | --- |
| 512, 01/07/1972, phase approach | 03/08/1972 | 9 wagons, 270 unites | 01/09/1972 |
| 512, 01/08/1972, phase depot | 14/08/1972 | 9 wagons, 270 unites | 01/09/1972 |
| 17, 01/01/1975, phase depot | 28/02/1975 | 8 wagons, 240 unites | 01/03/1975 |

**3/3 reprises saines, 3/3 transactions abouties, aucune erreur moteur.**
L'audit direct des sauvegardes
`results/rail_long_v3_upgrade_reload_fix_20261104_r4/physical_verified.json`
verifie chaque rame physique, capacite, les deux quais appartenant aux bonnes
stations et deux ordres de service (zero ordre depot), rame non stoppee.
Provenance : script
`results/rail_long_v3_upgrade_fix_20261104_145126/reload_diag.py`,
adaptateur Save/Load actuel et
`results/rail_long_v3_upgrade_fix_20261104_145126/verify_reload_physical.py`.
Les trois sauvegardes d'origine conservent leurs empreintes SHA256.

Validation finale hote : **21 contrats v3, 11 contrats v2**, projecteurs
OFF mono/multimodal et `git diff --check` OK. Ces tests hors VM ne sont pas
confondus avec les parties moteur. Le mecanisme v3 est **valide techniquement
dans les cas exposes** ; aucun nouveau duel 40×5/20×10, aucune adoption du
defaut et aucun gain statistique revendique. Les portes economiques anterieures
ne sont pas reinterpretees au titre de cette correction.
