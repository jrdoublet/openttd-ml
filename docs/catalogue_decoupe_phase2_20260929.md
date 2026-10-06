# Catalogue découpé C121 — phases 2 et 3 (2026-09-29)

## État au 2026-09-30 — revue documentaire statique

Prototype non adopté ; réglages expérimentaux à **défaut 0**. La branche active
exige `c121_air_economics=1`. La matrice suivante réconcilie les jalons avec les
mesures VPS ajoutées plus bas ; elle ne constitue pas une nouvelle exécution ni
une revalidation locale des résultats. Les anciens « non exécuté » décrivent
leur date de rédaction, pas le statut final du fichier.

| Phase / contrôle | État rapporté au 30 septembre | Limite conservée |
|---|---|---|
| Phase 2 brute | Diagnostic solo 1970 exécuté, graines 42/100/999 ; aucun scan complet | Goulots de publication/invalidation et de reprise observés |
| Phase 2 corrigée + AIR première année | Second diagnostic solo exécuté : 11/11/12 aéroports | Faible réutilisation du cache ; pas de qualification économique |
| Phase 3 + replanification différée | Mesurée ensuite en solo 2 ans et duels 5×3 ; cadence/trésorerie améliorées, décrochage en 1972 | Mesures postérieures aux mentions historiques « non exécuté » ; ne prouvent pas un batching intra-tick correct |
| Renforts au stock / territoire d'abord / ligne AAA | Variantes mesurées le 30 en duels 5×3 | Aucune ne rattrape la référence C115 ; défauts 0 |
| Identité au défaut | Contrôle rapporté non exact | Décalage d'opcodes invoqué dans le compte rendu, pas identité binaire démontrée |
| Save/Load | **Non vérifié** | Aucun aller-retour validé ne découle des mesures solo/duel |
| Qualification | Diagnostics 5×3 seulement pour ces variantes | Aucun 5×6/20×10 qualifiant rapporté ici ; non adoptable |

**Budget / batching :** l'ancien test de continuation `reliquat > 10 000` a été
remplacé localement par R4 (`> 2 000`, garde de tick inchangé). Ce correctif et
son seuil ne sont **pas validés par exécution** ; le budget demandé de 150 k par
tranche ne prouve pas le respect du quota moteur. Le coût fixe et une paire peuvent
franchir un tick. Les gains de cadence antérieurs ne valident pas R4 : il faut des traces
moteur de ticks/reliquats et de `same_tick_slices`. **Save/Load reste non vérifié.**
Suivi R4/R5 : [journal du 30](journaux/journal_2026-09-30.md) et [tâches](taches.md).
Décision utilisateur du 2026-09-30 : **ne pas toucher à C115**.

## Phase 3 — cache et trésorerie (29 septembre, historique de conception)

**Historique avant mesures VPS :** les attentes et mentions « non mesuré » de
cette section sont conservées comme état intermédiaire. Pour les exécutions
ultérieures, lire la matrice en tête et les sections de mesures du 29/30.

Le second diagnostic solo 1970 (`results/catalog_incr2_c121_1970_20260929.jsonl`
et `results/catalog_incr2_air1y_c121_1970_20260929.jsonl`, graines
42/100/999) a conduit l'utilisateur à retenir la direction AIR pendant la
première année. Le bras AIR ouvre 11/11/12 aéroports ; cette observation solo
ne qualifie ni le profit ni un gain causal face à AAAHogEx.

Dans le bras AIR, 19 des 47 tranches de la graine 42 ont au moins un hit ; les
recalculs de fin de scan sont majoritairement `dirty_town` (16 sur 17, puis
21 sur 24). La production PASS/MAIL mensuelle ne salit désormais une ville
qu'après **10 unités et 20 %** depuis le dernier volume ayant déclenché une
invalidation. Le seuil est un proxy de matérialité pour la demande utilisée par
`OpexC121PrepareDemandShadow` : cette demande intègre aussi la géométrie du
bassin et la desserte, donc le volume urbain brut ne suffit pas à déterminer
une économie exacte. Les petits écarts s'accumulent contre la même référence ;
les révisions de population, station, moteur, apprentissage et le filet de
365 jours restent actifs. `CATALOG_COST_SLICE` publie `reuse_pct` =
`100*hits/(hits+recalculated)` sur la passe et `chained_slices` avec
`same_tick_slices`. **À ce jalon historique**, le taux après correction restait
à mesurer en jeu ; aucune validation détaillée du batching n'est déduite des
mesures économiques ultérieures.

Le précédent enchaînement vérifiait un reliquat supérieur à **50 k opcodes**
après chaque dispatch, puis laissait le catalogue attendre son prochain tour
de file. Toutes les tranches observées affichaient `same_tick_slices=1`.
La continuation appelle maintenant le catalogue actif dans le tour courant
si plus de 10 k opcodes restent, puis laisse le scheduler servir une tâche due
avant la continuation suivante. Le calcul d'une paire et le coût fixe de
reprise peuvent malgré tout franchir la limite du tick ; seule une trace moteur
peut confirmer le nombre de tranches effectivement enchaînées.

La graine 42 a une passe `projects` le 9–12 novembre puis une autre le
20–21 décembre. `SCHED_IDLE t=projects` attribue **7,47 M opcodes et 40 jours**
à la passe qui se termine le 10 décembre ; le tour contient ensuite
`expand`, `refleet`, `town_growth`, `repay`, `catalog`, `report`, `scrap` et
`air_fleet`. Le catalogue n'explique donc pas à lui seul l'intervalle.
Le 12 novembre et le 21 décembre, `K_pass` vaut respectivement 6 007 et
6 828 £, mais l'AIR suivant coûte 101 364 £ avec 123 110 et 157 522 £
disponibles. C75 bis ne permet qu'un dépassement par passe ; une tentative
AIR rejetée `batch_plan_dead` peut déjà l'avoir consommé. Sous
`c121_catalog_air_first_year=1`, pendant cette seule année, un plan AIR vivant
et finançable peut donc franchir `K_pass` après une première construction
sans consommer le quota C75 bis. Les autres modes et années gardent C75.
Le test de validité d'un plan AIR est exécuté avant `K_pass` dans ce cas,
afin d'écarter tôt un site déjà pris ; le garde existant avant construction
reste en place. `C121_AIR_CHAIN_PASS` indique `built_air`, `chained_air`
(constructions réellement réussies par cette exception), `dead_skipped`,
`total_built` et le motif d'arrêt sous `catalog_cost_probe=1`.

Ces corrections sont derrière les deux réglages expérimentaux à défaut 0.
Les tests Python contrôlent les gardes et les champs, mais ne compilent pas
Squirrel. **Historique au jalon de rédaction :** le nombre de hits, le débit,
les chantiers et la trésorerie après correction étaient non mesurés, conformément
à l'interdiction de lancer une partie pendant cette phase. Les mesures VPS
ultérieures, conservées plus bas, remplacent ce statut pour les éléments mesurés,
pas pour Save/Load ni pour la preuve de batching intra-tick.

Le cache global transitoire associe une identité physique (bras, type d'aéroport,
TownID, ancre, StationID et réutilisation de chaque extrémité) au choix de moteur,
à l'économie initiale/de décision, à la cible de flotte et aux invariants C121 du
plan. L'admission et le score de financement sont refaits à chaque portefeuille.
Les entrées sont absentes de `Save()` ; `OpexLoadSettings()` les vide après Load.
Le mois de démarrage de la première année est l'état `_generationStageMonth` déjà
persisté ; l'option AIR seule désarme le fret rail normalement produit par
`OPEX_STAGE_AIR_ONLY`, ainsi que les nouveaux candidats rail passagers, route et
eau. Gestion des lignes et flottes existantes inchangée.

| Entrée | Invalidation | Périmé au maximum |
|---|---|---|
| Moteurs et prix | comparaison des choix et prix/coûts par type d'aéroport lors du refresh ; les événements réveillent le refresh | jusqu'au prochain refresh mensuel |
| Ville | `TownFounded`, population ≥20 habitants et ≥5 %, production PASS/MAIL ≥10 unités et ≥20 % depuis la dernière invalidation | au plus `ceil(villes/8)` jours de jeu avec passage catalogue avant détection |
| Station/ligne | empreinte des lignes AIR par StationID comparée lors du bump C76 `lines`, et nombre de routes du hub | jusqu'au prochain événement C76 |
| Apprentissage | révision par station pour le délai, par type d'aéroport contenant le moteur pour la soute MAIL, par bras pour le facteur de réalisation ; le régime adaptatif relève de l'admission recalculée | jusqu'au prochain portefeuille publié |
| Âge | 365 jours de jeu, vérifié quand le plan est revisité | aucune économie périmée de plus de 365 jours n'est relue dans un nouveau plan |

Les révisions globales de lignes, moteurs et apprentissages ont été retirées.
Une production sous
seuil, une variation de population sous seuil, ou un changement d'entrées non
couvert par ces révisions peut laisser l'économie périmée jusqu'au filet de 365
jours après revisite du plan. Le balayage de fond qui forcerait une revisite de
chaque ancienne entrée n'est pas encore présent. Si l'inflation modifie le paiement des cargos sans modifier le prix ou le
coût des moteurs observés, elle peut également rester périmée jusqu'à ce filet.

C78 reprend la génération AIR par curseur. Chaque tranche reçoit au plus 150 k
opcodes de budget demandé. Le tour suivant publie le lot de plans nouvellement
évalués ; une publication est refaite à chaque croissance du lot, sans attendre
la fin du scan. La boucle principale sert les tâches dues et continue le
catalogue tant qu'un scan reste actif et que le reliquat du tick dépasse
10 k opcodes. Un worker ou une recherche rail active suspend cet enchaînement.
Le lot de production de huit
villes passe au plus une fois par jour et ne marque plus
`_portfolioInvalidated` ; une publication partielle
déverrouille aussi `projects` après une invalidation C76 pendant le scan.
Le travail fixe de reprise et une dernière paire peuvent dépasser ce budget :
`CATALOG_COST_SLICE` est émis à chaque tranche avec taille du cache, hits,
recalculs, motifs de salissure, tranches dans le même tick et publication
partielle. `CATALOG_COST` garde son bilan de passe complète. Les villes qui
touchent un plan sale sont placées d'abord, selon le dernier `fundScore` connu
du plan ; le classement par population départage les autres. **Cette priorité
reste une approximation par ville : elle ne garantit pas l'ordre exact des
paires sales avant toutes les nouvelles paires.** La bande
`PAX_BAND_AIR_ONLY` reste la première unité de travail du bootstrap.

### Causes confirmées dans le journal brut

`results/catalog_incr_c121_1970_20260929.jsonl` contient 3 253 lignes
`SCHED_IDLE` pour la graine 42 (2 871 pour 100, 2 898 pour 999), aucune
`CATALOG_COST` sur les trois parties, 982 `projects_invalidated` au total et
1 057 `catalog_c78_slice_incomplete`. Le portefeuille partiel était publié
seulement une fois ; après un chantier, C76 remettait
`_portfolioInvalidated`, ce qui bloquait `projects` durant le reste du scan.
`SCHED_IDLE` décrit le résultat du dispatch ; le ledger C41 de reliquat est
observatoire. Le `Sleep(1)` de `main.nut` suivait chaque dispatch, même après
une tranche incomplète qui avait encore du travail.
Les révisions globales salissaient chaque entrée de cache après un changement
local. La part respective de ces causes dans la perte économique n'est pas
mesurable à partir de ce seul diagnostic.

## Validation disponible au jalon initial — historique

`python3 -m unittest discover -s sweeps -p 'test_*.py'` : 617 tests OK,
2 ignorés. `git diff --check` : OK. Les tests statiques ne compilent pas Squirrel. La
validation moteur, Save/Load et le 5×6 restaient à faire par l'orchestrateur
**à ce jalon**. Les exécutions ultérieures sont décrites plus bas ; Save/Load
reste non vérifié et les duels 5×3 ne valent pas qualification 5×6/20×10.
Ces comptes de tests sont rapportés, non réexécutés dans la revue du 30.

## Commandes de mesure prévues après revue — protocole historique

**Historique, pas file de lancements courante.** Ces commandes sont conservées
pour la traçabilité du protocole ; elles ne remplacent pas les campagnes
effectivement mesurées plus bas et aucune n'est exécutée par cette revue.

Sous Bash, depuis la racine, après contrôle du contexte Docker, de l'image,
du volume et du montage réel. Chaque sortie doit recevoir un nom neuf.

Identité au défaut (contrôle de bras équivalents dans le code courant ; pour une
identité historique stricte, utiliser deux bundles figés avant/après) :

```bash
rtk proxy docker run --rm --cpus=3 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab -v "$PWD":/work -w /work openttd-lab python3 sweeps/bench_v2.py --arms 'OpexAI[c121_air_economics=1,c121_air_project_realization_adaptive=1,c121_air_pressure_probe=1]' 'OpexAI[c121_air_economics=1,c121_air_project_realization_adaptive=1,c121_air_pressure_probe=1,c121_catalog_incremental=0]' --seeds 42 --years 1 --max-workers 3 --out results/c121_catalog_default_identity_42_1y.json
```

Diagnostic 1970, trois graines, probes identiques dans les deux bras :

```bash
rtk proxy docker run --rm --cpus=3 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab -v "$PWD":/work -w /work openttd-lab python3 sweeps/bench_v2.py --arms 'OpexAI[c121_air_economics=1,c121_air_project_realization_adaptive=1,c121_air_pressure_probe=1,catalog_cost_probe=1,probe_scheduler=1,probe_portfolio=1]' 'OpexAI[c121_air_economics=1,c121_air_project_realization_adaptive=1,c121_air_pressure_probe=1,c121_catalog_incremental=1,catalog_cost_probe=1,probe_scheduler=1,probe_portfolio=1]' --seeds 42 100 999 --starting-year 1970 --years 1 --max-workers 3 --out results/c121_catalog_diag_1970_3seeds.json
```

Rerun prioritaire du bras incrémental corrigé, avec sortie neuve :

```bash
rtk proxy docker run --rm --cpus=3 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab -v "$PWD":/work -w /work openttd-lab python3 sweeps/bench_v2.py --arms 'OpexAI[c121_air_economics=1,c121_air_project_realization_adaptive=1,c121_air_pressure_probe=1,c121_catalog_incremental=1,c121_catalog_air_first_year=1,probe_scheduler=1,catalog_cost_probe=1,probe_portfolio=1]' --seeds 42 100 999 --starting-year 1970 --years 1 --max-workers 3 --out results/c121_catalog_phase3_air1y_1970_3seeds_20260929.json
```

Save/Load : `save_load_roundtrip.py` accepte `--arm` et réutilise les helpers de
`bench_v2.py`. La phase A doit durer assez longtemps pour remplir le cache :

```bash
rtk proxy docker run --rm --cpus=3 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab -v "$PWD":/work -w /work openttd-lab python3 sweeps/save_load_roundtrip.py --arm 'OpexAI[c121_air_economics=1,c121_air_project_realization_adaptive=1,c121_air_pressure_probe=1,c121_catalog_incremental=1]' --seed 42 --starting-year 1970 --years-a 2 --years-b 1 --out results/c121_catalog_save_load_42.json
```

Ces commandes ne constituent pas un verdict d'adoption. Une qualification
économique demanderait ensuite un 5×6 apparié et, avant défaut 1, un 20×10
complet et sain selon `AGENTS.md`.

## Mesures en jeu et correction « replanification différée » (VPS, 2026-09-29/30)

Toutes en solo avec `probe_scheduler=1,catalog_cost_probe=1,probe_portfolio=1`, bras
C121 adaptatif + `c121_catalog_incremental=1` (+ `c121_catalog_air_first_year=1`).

- Phase 2 brute : aucun passage catalogue terminé en 1970, premier chantier d'avril à
  août (tranches non enchaînées, `SCHED_IDLE`, invalidations globales).
- Phase 2 corrigée + AIR première année : 11/11/12 aéroports ouverts en 1970 (défaut C115 :
  10/7/7) ; cache peu réutilisé (`dirty_town`).
- Phase 3 : trésorerie de fin 1970 mieux investie (graine 42 : 56 k£ au lieu de 254 k£).
- Sonde `PROJECTS_COST` (ajoutée ici) : en 1971 la passe `projects` dépensait 38 à 56 M
  opcodes dans la régénération post-chantier (`OpexIncrementalUpdateProjects` rejetait
  tous les plans AIR puis rappelait `OpexAirPlans` en bloc). Correction sous
  `c121_catalog_incremental=1` : seuls les plans touchant les villes du chantier sont
  retirés, pas de `OpexAirPlans` synchrone, couche C76 `lines` non acquittée pour que le
  catalogue découpé ajoute les nouvelles paires. 1971 : 25 à 81 passes (5 à 9 avant),
  trésorerie de fin d'année 42 à 365 k£ (381 à 891 k£ avant).
- Duels 5×3 contre AAAHogEx (`..._5x3_20260929d`, puis `..._deferred_..._5x3_20260929`) :
  plus d'aéroports que le défaut fin 1970 et 1971, décrochage en 1972 (flottes de 26 à 37
  avions contre 26 à 76 pour la référence). Prochain goulot : renforts de flotte C121.
- Correctif Squirrel : le champ `static` (mot réservé) renommé `engineStatic`.
- Identité au défaut : non exacte (graine 42 : 297 254 contre 293 746 sur `master`) ; logique
  identique, décalage d'opcodes seulement.
- Non vérifié : aller-retour sauvegarde/chargement ; amorçage par étapes qui régénère encore
  tout le portefeuille à chaque chantier en 1970 (18 à 30 M opcodes).

## Renforts au stock et territoire d'abord (VPS, 2026-09-30)

- Cause des flottes C121 figées : sous sa cible, une ligne C121 n'était renforcée qu'à deux
  ans d'âge puis tous les deux ans ; en 1970, 97 à 98 % des lignes examinées étaient
  refusées (`c121_no_full_year_observation`), aucun renfort en deux ans.
- `c121_fleet_stock_growth` (défaut 0) : renfort sur stock en gare comme AAAHogEx
  (`route.nut:2904-2915`), délai de 60 jours, jusqu'à 4 par passe sous la cible. Solo 42 fin
  1971 : 42 avions (21 sans), profit 2,19 M£ (1,32 M£). Duel 5×3
  `c121_catalog_fleetstock_vs_default_5x3_20260930` : 12,8 aéroports fin 1972 en moyenne
  (référence 20,4), monopoles AAA 2-0 plus nombreux, écart O−A −1 712 k£/an (réf. −822).
- `c121_territory_first` (défaut 0) : un projet non territorial doit laisser de quoi financer
  le prochain AIR qui ouvre une ville sans aéroport Opex. Solo : sans effet (21 aéroports,
  trésorerie inutilisée ; l'argent ne limite plus). Duel 5×3
  `c121_territory_first_vs_default_5x3_20260930` : 16,6 aéroports, écart −1 443 k£/an.
- Bilan des 4 duels 5×3 : aucune variante C121 ne rattrape la référence C115 sur le
  territoire ni sur l'écart avec AAAHogEx (diagnostics 5 paires, duels non déterministes).

## Ligne à la AAAHogEx sous C121 et essais hors C121 (VPS, 2026-09-30)

- `c121_aaa_line` (défaut 0, C121 seulement) : 2 avions à l'ouverture (le second au hangar B,
  départ par l'ordre retour), économie C121 du projet calculée à 2 avions, chargement complet
  aux deux bouts (`AIR_FULL_LOAD = 1` pour tout le bras). Choix moteur C121 inchangé : il
  prend déjà 223/220/228 (la référence C115 prend surtout le 217).
  Duel 5×3 `c121_aaa_line_vs_default_5x3_20260930` (pile C121 complète) : **effondrement**,
  4 à 13 aéroports fin 1972 (référence 9 à 25), profit Opex 279 k£ (1 280 k£), écart O−A
  −2 446 k£/an (réf. −822), 0/5. En solo le même bras atteignait 20 aéroports : en duel,
  le chargement complet sur des villes partagées avec AAAHogEx fait attendre les avions.
- Hors C121, même protocole (depuis `master`) : `v93_airport_no_pop_floor=1` −1 917 k£/an ;
  `air_hub_max_routes=1` −1 481 k£/an (flottes figées ~2 avions par ligne) ;
  `air_hub_max_routes=1` + `air_full_load=1` −1 806 k£/an, 0/5.
- Référence avec télémétrie par ligne (`lineprofit_ref_5x3_20260930`) : profit médian par
  aéroport identique (~38 k£) chez OpexAI et AAAHogEx en 1971-1972 ; AAAHogEx a 50 à 60 %
  d'aéroports en plus ; stock en gare bas chez les deux en début de partie. L'écart tient au
  nombre d'aéroports.
- Non isolé : 2 avions à l'ouverture **sans** chargement complet.
