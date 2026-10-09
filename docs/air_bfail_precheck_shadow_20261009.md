# AIR — avant BFAIL : prétest B passif et limite de LevelTiles (09/10/2026)

## Question et garde de comportement

L'expérience précédente garder/démolir A a prouvé qu'une démolition après
échec **ne restitue pas le coût de construction de A** (+792 £ pour le
premier BFAIL sur chacune des trois graines). Question distincte : le
préflight du site B peut-il détecter de façon fiable l'échec **avant**
toute dépense A ?

La politique existante `air_efficiency_preflight=1` a **échoué** au 20×10
canonique du 02/10 (delta de `profit_year` −89 294 £/an en moyenne,
4V/14D/2E, IC95 [−141 180 ; −37 408]). Elle reste OFF. Il serait abusif
de réactiver ce filtre en prétendant qu'il prévient les BFAIL.

Nouvelle sonde `air_bfail_precheck_shadow=1`, **OFF=0 sur les quatre
difficultés**. Dans `OpexBuildAirRoute`, lorsque `!reuseA && !reuseB`, avant
`AIAccounting` et avant tout terrassement : elle appelle le helper existant
`OpexAirPreflightEndpoint` sur B et mémorise localement le résultat. Elle
ne rejette **jamais**, n'invalide aucun cache et ne change ni le projet ni
l'ordre réel des travaux. L'ancien `AIR_EFFICIENCY_PREFLIGHT` reste le seul
flag autorisant les rejets `PREA/PREB`. Aucun état ajouté à Save/Load.
`OpexAirV126RecoveryFields` attache dans le **même** `AIR_FINANCE_TRY`
`pre_b_ok`, `pre_b_err`, `pre_b_verdict`, `pre_b_anchor`, `real_b_err` ;
une seconde version inclut `real_b_stage` pour savoir si B a échoué à la
phase `level`, `airport`, ou a été `built` (ou `not_attempted` si A échoue).
Ce rattachement intra-appel évite toute jointure ambiguë entre chantiers.

## Résultats moteur initiaux

Smoke apparié `air_bfail_precheck_shadow_5678x1_20261009_r1` :
**2/2 parties complètes/saines** (1970), variante sonde ON contre OFF,
delta final `profit_year` **0 £/an**, ratio de valeur **0 %**, source figée
`5920d982c4b5bc875b2cb2cc13922c192638ed0dce5e0fb8d6440c6a9f6d1d95`.
Dans la variante, 11 chantiers à deux aéroports neufs, 8 atteignant B avec
succès, 1 échouant dès A, **2 BFAIL** (A historique 43 385 £) ; les deux
BFAIL avaient `pre_b_ok=1` / `defer_level`. Zéro prérejet utile.
L'identité de métriques d'un smoke ne prouve pas une neutralité générale
du coût en opcodes.

Collecte mono-bras ON `air_bfail_precheck_shadow_6x3_20261009_r1` :
**6/6 parties complètes/saines**, graines 42/100/999/1234/5678/2026,
1970–72, même bundle. Analyseur strict
`sweeps/analyse_air_bfail_precheck_shadow.py` :
`results/air_bfail_precheck_shadow_6x3_20261009_r1_analysis.json`.

| Issue réelle du chantier à deux nouveaux sites | Pré-B accept | Pré-B defer_level | Total |
|---|---:|---:|---:|
| B construit (chantier abouti ou échec ultérieur) | 23 | 29 | **52** |
| A échoue avant B (`AFAIL`) | 17 | 19 | **36** |
| B échoue après A (`BFAIL`) | 2 | 6 | **8** |
| **Total** | **42** | **54** | **96** |

**Aucun des 96 prétests n'a émis `reject`.** Donc aucun des **8 BFAIL**
n'aurait été prévenu par la politique existante, et le coût A historique
exposé de **168 532 £** n'aurait pas été évité. Les erreurs finales B sont
5× code `263` (`ERR_FLAT_LAND_REQUIRED`), 2× code `2`, 1× code `258` ;
ces deux derniers codes restent bruts tant que leur nom n'est pas confirmé
au runtime. On ne doit pas conclure que les huit erreurs proviennent d'une
seule cause. Les données sont **strictement observationnelles** et non un
test économique de nouvelle politique ; les 96 tentatives ne sont pas des
graines indépendantes.

L'API `AITile.LevelTiles` documente expressément qu'un appel peut retourner
`true` en `AITestMode` même si la même opération échoue en `AIExecMode` ;
une exécution réelle peut modifier **une partie seulement** du rectangle
avant l'échec. Documentation :
https://docs.openttd.org/ai-api/classAITile .
Le code OpexAI `OpexAirCanLevelFootprint` (`air_sites.nut:62-74`) accepte
justement `AITile.LevelTiles` en `AITestMode`, sans poser réellement le
terrain. C'est une **limite d'API démontrée**, pas la preuve que ce mode
explique chacune des huit erreurs. Le helper `OpexAirFootprintIsFlat`
compare les maxima d'altitude, alors que le moteur considère aussi les
pentes et la configuration `construction.build_on_slopes`; l'hypothèse
géométrique doit être confirmée avant tout changement.

## Résultat affiné : échec au nivellement ou à la pose ?

Pour distinguer l'échec de nivellement réel d'un échec de BuildAirport
après nivellement, la mesure passive `real_b_stage` a été ajoutée sous
**le même setting**. Elle n'existait pas dans le bundle r1, d'où les
avertissements explicites de l'analyseur lors d'une relecture des vieux logs.

La campagne **`air_bfail_precheck_stage_6x3_20261009_r2`**, lancée **après**
libération du Docker occupé par RAIL, est **6/6 complète et saine**, nouveau
bundle SHA256
`293d8e65b4a3036c3c5fff0fde437f4d889e80c8e6ed1eee79420732c44c518d`,
manifest SHA256
`ced807e0788c86a878301b6cdd542e37b1a4fb009e2ece729a8be4e00947652d`.
La sortie `results/air_bfail_precheck_stage_6x3_20261009_r2_analysis.json`
compte **96/96 tentatives appariées, 0 warning, exactement les mêmes 8 BFAIL
et les mêmes métriques économiques par graine qu'en r1**. Aucun signal de
régression de la trajectoire sur cette série ; la sonde change néanmoins
le profil d'opcodes, donc ce n'est pas une garantie globale.

| Stade de l'échec réel B | Nombre de BFAIL | Capital A historique exposé | Détail |
|---|---:|---:|---|
| **`level`** (`OpexAirLevelFootprint` non OK) | **7** | **142 972 £** | cinq erreurs B code 263, deux code 2 |
| **`airport`** (niveau OK, BuildAirport refusé) | **1** | **25 560 £** | code B 258 |
| **Total** | **8** | **168 532 £** | Tous les prétests B sont `ok=1` |

Parmi les 52 chantiers dont B a été construit, **29** avaient précisément
la classification préalable `defer_level` : rejeter ce cas en bloc
produirait une perte certaine de bonnes constructions. Le stade réel
`level` révèle un mécanisme plus précis que le libellé général `BFAIL` ;
il ne garantit pas qu'une exécution alternative aurait pu prévoir l'échec
sans dépenser. Les valeurs 2 et 258 restent des codes de diagnostic, non
des erreurs nommées inventées.

## Verdict et prochaine intervention justifiable

**Rejeter la piste “activer le préflight actuel pour sauver A” :** il ne
prédit aucun des huit échecs et a déjà fait perdre au 20×10.
**Ne pas transformer `defer_level` en hard reject :** 29 B construits
réussissent après cet état. **Aucun changement comportemental, aucun
réglage adopté, pas de porte V102.**

La vraie question résiduelle est de savoir pourquoi la commande
`AITile.LevelTiles` échoue **réellement** sur sept sites que le test
simulé admettait. Avant de choisir un filtre ou un ordre B-first, il faut
une preuve à l'échelle de la tuile : coût/précondition dans le monde réel,
taille de l'emprise, source du refus, éventuelle transformation partielle,
et caractérisation des 29 projets `defer_level` pourtant bâtis. Une
alternative B-first qui construit réellement B avant A déplacerait les
dépenses, les orphelins et la compétition : elle exigerait un prototype
transactionnel isolé et son propre A/B, pas une déduction de ces logs.
**Aucun commit/push.**

## Autopsie géométrique r3 — protocole fixé avant mesure

La catégorie `real_b_stage=level` de r2 regroupe deux sorties différentes
de `OpexAirLevelFootprint` : une commande `AITile.LevelTiles` refusée et
une commande terminée mais suivie de `OpexAirFootprintIsFlat=false`. Le
code de résultat `263` peut être **synthétique**, produit par la seconde
sortie (`air_sites.nut`) ; ne pas attribuer les cinq `263` au moteur.
La source API 15.3 `script_error.hpp` identifie les codes : **2**
`ERR_PRECONDITION_FAILED`, **258** `ERR_LOCAL_AUTHORITY_REFUSES` (y compris
limites liées au bruit), **263** `ERR_FLAT_LAND_REQUIRED`.

Sous le **setting déjà existant** `air_bfail_precheck_shadow=1` et
`probe_air_finance_margin=1`, le code local r3 ajoute au même événement
`AIR_FINANCE_TRY` des champs `b_level_*` : phase exacte, retour et première
erreur de `LevelTiles`, retry éventuel, caisse juste avant/après, emprise et
coordonnées, option `construction.build_on_slopes`, grille compacte des
hauteurs min/max et pentes avant/après la commande sur **(w+1)×(h+1)**
tuiles, et compteurs d'occupation. Le relevé `after` précède la pose B.
Le défaut des quatre difficultés demeure **OFF=0**. Aucun champ n'influence
la sélection, la constructibilité, le rollback ou Save/Load.

Protocole diagnostic pré-enregistré, sur la branche `master` HEAD
`cb23a172fa6f7b79e50d0392e526a061c130259b`, arbre local dirty gelé
au lancement par `run_c66_reference.py`, image `openttd-lab:latest`, hôte
local ≤10 CPU/8 Go/10 workers : d'abord smoke ON/OFF **seed5678×1 an**
afin de valider compilation, intégrité de la grille, identité d'issue et
exposition des deux BFAIL ; puis, si sain et moteur libre, collecte mono-bras
**seeds 42/100/999/1234/5678/2026 ×3 ans** avec les mêmes réglages et un
bundle/manifest propres, pour confronter les sept échecs historiques aux
29 `defer_level` ayant construit B. Réglages AIR communs :
`air_site_cost_quote=1,air_site_quote_keep_legacy_margin=1,probe_air_finance_margin=1,air_bfail_dispose_orphan=0`.
Analyse exclusivement observationnelle ; aucune règle statistique V102 ni
seuil économique, aucune adoption automatique et aucun commit/push.

### Verdict mesuré r3 : le stade `level` n'est pas un refus natif de `LevelTiles`

Le second smoke apparié **`air_bfail_geometry_smoke_5678x1_20261009_r2`**
utilise le bundle `d8a0b19683654aae93a3015fad4e697c585c02e4c6e54e31f5bc23e7f8597519`
et le manifest `475428c0901a77d102e4fcc87208fea6ae86e019153844a4651e3e576d0402eb`.
**2/2 parties saines**, résultat économique ON/OFF strictement identique
à un an (delta `profit_year` 0, delta valeur 0). Le décodeur
`sweeps/analyse_air_bfail_geometry.py` retrouve **10/10** événements
atteignant B, **zéro warning**, dont deux BFAIL de mécanismes distincts.
Le smoke r1 antérieur avait déjà le même signal, mais sa photographie du
bord x=255 lisait les hauteurs de tuiles invalides ; le correctif de sonde
est inclus dans le bundle r2 et les invalides y sont explicitement `X`.

La collecte mono-bras **`air_bfail_geometry_6x3_20261009_r3`** utilise ce
**même bundle** (`d8a0b196…f8597519`), manifeste propre
`7e204db267c1873febe7cf68f77ace269c6cdd443e1228204c618488a73d5520`,
source HEAD `cb23a172` dirty, image OpenTTD 15.3
`sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
Graines **42, 100, 999, 1234, 5678, 2026**, années 1970–72 : **6/6
parties saines**. Le décodeur géométrique retrouve **60/60** constructions
ayant atteint B, **zéro warning** : 52 B construits, 8 BFAIL. Le décodeur
de préflight complet retrouve **83/83** tentatives newpair, dont 23 AFAIL,
52 B construits, 8 BFAIL (**27** succès `defer_level`, 25 `accept`).
Ces observations ne constituent pas
un A/B comportemental.

| Seed / date r3 | Ancre B | Erreur B | Stade exact de B | Tuiles aéroport discordantes après | Tuiles modifiées au nivellement |
|---|---:|---:|---|---:|---:|
| 999 / 1971-07-08 | 5346 | 263 | `postcheck_nonflat`, commande OK | 2 | 27 |
| 1234 / 1971-01-12 | 60508 | 263 | `postcheck_nonflat`, commande OK | 2 | 36 |
| 5678 / 1970-01-15 | 19895 | 263 | `postcheck_nonflat`, commande OK | 2 | 20 |
| 5678 / 1970-12-02 | 44793 | 2 | `invalid_end`, commande non appelée | 0 | 0 |
| 5678 / 1972-07-17 | 44793 | 2 | `invalid_end`, commande non appelée | 0 | 0 |
| 2026 / 1970-10-05 | 5604 | 263 | `postcheck_nonflat`, commande OK | 2 | 14 |
| 2026 / 1971-08-10 | 18980 | 258 | `success` du nivellement, pose refusée | 0 | 48 |
| 2026 / 1972-04-30 | 51233 | 263 | `postcheck_nonflat`, commande OK | 34 | 14 |

**Cinq `263` sont fabriqués par le garde de planéité final d'OpexAI**
(`OpexAirLevelFootprint`), après `LevelTiles=true` et des mutations
physiques du terrain. Dans quatre cas, les deux dernières discordances
sont des tuiles de pente contiguës sur la première ligne ou colonne de
l'emprise : `(0,4)/(0,5)`, `(0,3)/(0,4)`, ou `(3,0)/(4,0)`.
Sur 2026/1972-04-30, l'ancre conserve un maximum de hauteur **4**
mais passe d'une pente **6 à 4**, tandis que 34 autres tuiles de l'emprise
sont plates au niveau **3** : les 34 discordances après commande sont donc
relatives à la hauteur de référence, pas 34 obstacles nouvellement créés.
L'API du moteur
permet un `LevelTiles=true` si une partie seulement a été traitée. Les
logs confirment le résultat partiel, mais **pas** la raison interne de
chaque coin résiduel (limite terraform, voisinage, obstacle ou autre).

**Deux `2` sont créés localement avant toute commande** : ancre B=44793,
coordonnées `(249,174)`, aéroport `6×6`, `end=(255,180)` invalide sur
une carte 256×256, sept tuiles invalides sur le rectangle inclusif
de nivellement ; les 36 tuiles aéroport contrôlées étaient pourtant
planes (`mismatch=0`, pente=0). Le test préflight B acceptait les deux.
Le helper vérifie `end` avant de tester l'emprise déjà plate. Corriger
l'ordre de ces deux gardes est **une hypothèse de correction isolée** ;
aucune pose réelle réussie n'a été démontrée à ce site. L'autre `258`
est bien un refus **`BuildAirport`** après nivellement sain : l'enum
`ERR_LOCAL_AUTHORITY_REFUSES` couvre note municipale et plafond de bruit,
qui ne sont pas distingués dans les logs r3.

**Limite de comparabilité majeure** : sept des huit BFAIL conservent
exactement date et ancre entre r2 et r3, mais **seed1234** diverge :
r2 BFAIL le **1971-05-19**, ancre **59444** ; r3 BFAIL le **1971-01-12**,
ancre **60508**. Le profit annuel final Opex de seed1234 change de
**+69 689 £** et sa valeur de **+238 769 £** ; les cinq autres graines
gardent leurs profits/valeurs terminaux. La sonde est donc **intrusive
pour au moins une trajectoire**. Les données r3 expliquent directement
sept sites historiques et un nouveau site, mais **ne caractérisent pas
géométriquement l'ancien site 59444**. Les coûts A historiques exposés
en r3 sont **167 872 £**, contre **168 532 £** en r2 ; ce ne sont ni des
remboursements ni des gains potentiels établis.

Fichiers de preuve :
`results/air_bfail_geometry_6x3_20261009_r3.json`, son manifeste,
`results/air_bfail_geometry_6x3_20261009_r3_engine/`,
`results/air_bfail_geometry_6x3_20261009_r3_analysis.json`, et
`results/air_bfail_geometry_6x3_20261009_r3_precheck_analysis.json`.
Analyseur HOST et sept fixtures :
`sweeps/analyse_air_bfail_geometry.py`,
`sweeps/test_analyse_air_bfail_geometry.py`.

**Décision : diagnostic causal au niveau du helper acquis pour 7/8 sites
historiques. Ne pas modifier le rectangle `+(w,h)` sans preuve : il couvre
les coins extrêmes nécessaires au nivellement. Ne pas assimiler
`LevelTiles=true` à une terrasse complète ; ne pas rejeter `defer_level`
(27 bons chantiers dans r3). Piste sûre à évaluer séparément : traiter
l'emprise déjà plate avant de rejeter le coin de terrassement invalide.
Aucun correctif décisionnel adopté, aucun filtre nouveau, aucune porte
V102, aucun commit/push.**
