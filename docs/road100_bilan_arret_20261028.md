# ROAD100 — bilan des tentatives et arrêt demandé le 28 octobre 2026

**Décision utilisateur : arrêter les travaux sur la route ; ne plus relancer ROAD100.**
Ce document résume les essais réalisés, sans transformer une réussite technique
en résultat économique. **Résultat final démontré : 0/5 parités H1–H5.**
Les essais et mécanismes expérimentaux n'ont pas été adoptés par défaut.

## Objectif, protocole, référence

Objectif : duel OpenTTD 15.3, OpexAI contre AAAHogEx-115 sur la même carte,
**strictement ROUTE seule pour les deux IA**. Les trains, tramways, bateaux
et avions sont désactivés chez AAAHogEx ; AIR/RAIL/WATER désactivés chez
OpexAI. La seule victoire admissible est `profit_year` **annuel réel** de
la société OpexAI ≥ celui d'AAAHogEx à **chacun** des cinq horizons annuels,
sans éroder un horizon gagné. Une trace, un score, un préflight, une valeur
d'entreprise, un bénéfice estimé de ligne ou un achat isolé ne vaut pas une
parité. Les petites campagnes exploratoires n'établissent pas de causalité
statistique.

**Baseline 40 graines × 5 ans** :
`results/road100_baseline_40x5_20261027.json`, 40 duels valides, zéro
victoire Opex contre AAA à chacun des cinq horizons.

| Horizon | OpexAI `profit_year` moyen | AAAHogEx-115 moyen | Opex/AAA |
|---|---:|---:|---:|
| H1, 1970 | 8 095 £/an | 134 498 £/an | 6,0 % |
| H2, 1971 | 26 907 £/an | 555 822 £/an | 4,8 % |
| H3, 1972 | 28 913 £/an | 1 108 485 £/an | 2,6 % |
| H4, 1973 | 29 110 £/an | 1 704 870 £/an | 1,7 % |
| H5, 1974 | 29 753 £/an | 2 161 407 £/an | 1,4 % |

**Déficit H5 : ~2,132 M£/an.** Opex termine cette baseline avec
14 véhicules et 14 gares en moyenne, contre ~497 véhicules et 93 gares
chez AAA ; sa caisse moyenne reste proche de 278 k£. La difficulté ne
se réduit donc pas à « manquer d'argent » : peu de projets construits,
de bassins réellement captés et de véhicules productifs.

## Toutes les familles de tentatives ROAD100

Les numéros correspondent aux dossiers et options ROAD100. Un résultat
positif **ON−OFF** est un delta de profit de société **par rapport à Opex
OFF**, pas une victoire sur AAA. Certaines expériences utilisent des bras
combinés et des sous-versions ; les comparer seulement dans leur bundle.

| Famille | Ce qui a été essayé | Preuve / verdict |
|---|---|---|
| **1, bus interurbains PAX** | Réintroduire des lignes de bus entre villes, mode ROUTE seul, demande prudente | 5×1 : **−410 £/an** ; davantage de lignes, sans gain robuste |
| **2/2b, bus intra-ville et voirie** | Deux quartiers, BFS sur rues réellement connectées | 5×1 : **−800 £/an** ; variante voirie **−924 £/an** malgré des plans valides |
| **3, construction par lots** | Jusqu'à quatre chantiers/passe, ROI supplémentaires ≥25 %, réserve 50 k£ | **40×5 : −194 £/an à H5**, p=0,8522, **fail_primary** ; 0/40 contre AAA chaque année |
| **4, flotte BUS accrue** | Autoriser jusqu'à 8 bus si capacité physique | Pilote inchangé, **aucune exposition** au plafond augmenté |
| **5–6, autres leviers initiaux** | Ajustements de sélection, de flotte et d'estimation avant stratégie site-first | Aucun résultat ne qualifie le profit annuel ; voir journal détaillé et préenregistrements ROAD100 |
| **7, site-first** | Choisir stations physiques, captation puis chemin/devis avant classement ; correctifs v1–v4 contre le fallback trompeur | 12 projets admis/8 bâtis en v3, mais préflights très chers ; v4 5×1 **+37 £/an**, valeur **−61 %** ; NO-GO |
| **8, satellites joints** | Agrandir réellement la couverture PAX sous le même StationID | Quai physique et +5 PAX/mois sur seed42, mais **5×5 −5 002 £/an** H5, valeur −6,24 % |
| **9, multi-bassins** | Nouveaux arrêts disjoints de couverture, malgré ville déjà desservie | 5×5 **+994 £/an**, p=1,0, signal non robuste ; 0/5 |
| **10, flotte selon attente réelle** | Acheter des bus sur lignes rentables avec waiting et capacité physique vérifiés | 21 bus supplémentaires réellement achetés sur 5 graines ; 5×5 **+3 499 £/an** H5, p=0,625 ; 0/5 |
| **11, fenêtre tournante** | Diversifier les paires de sites examinées pour éviter les répétitions | 5×5 **−5 432 £/an** H5, aucune parité |
| **12, priorité aux sites proches** | Classement favorisant les distances faisables et un proxy de profit | 5×5 **−23 710 £/an**, 0V/5D, valeur −33,86 % ; NO-GO |
| **13, détour deux coudes** | Routes alternatives bornées quand BFS/L échoue | **Une vraie ligne PAX** de 43 arêtes construite seed42 ; 5×5 **−6 231 £/an**, valeur −8,83 % ; NO-GO |
| **14, tournée / troisième arrêt** | Étendre une ligne vers StationID A1 distinct et circuit quatre ordres | v1–v5 : `OPCAP`, `NO_MARGINAL` ou `ROI`, **aucun A1 construit**, aucune qualification |
| **15, calibrage du profit** | Lire `LINE_REVENUE` réalisé vs estimé, investiguer ESTIM31 et flotte réelle | **Audit seulement** : cohortes non comparables ; aucun multiplicateur de recette adopté |
| **16, longue distance / préqualification** | Sites d80..170, multi-coudes, coûts, vrais quais, dépôts ; v1–v19b | Voir détail ci-dessous : nombreuses traces tentées mais **aucun LONG** physique ; coûts/opcodes/obstacles |
| **20/20d/20e, portefeuille PAX** | Plusieurs stations jointes et couverture marginale sans bonus fictif | Vrais satellites posés, mais V20e 5×5 **−3 091 £/an** H5, ratio Opex/AAA 2,3 % |
| **21, fret diversifié + lot** | Plusieurs marchandises (`COAL`, `IORE`, `WOOD`) et vrais chantiers | 5×5 **+14 976 £/an** H5, p=0,4375, 13 lignes/28 véhicules contre AAA 49/497 ; 0/5 |
| **22, origine par cargo** | Autoriser plusieurs cargos indépendants au même site | 5×1 **+199 £/an**, quatre graines inchangées ; non qualifié |
| **23, ROI du second chantier 15 %** | Réduire le seuil de 25 à 15 %, garder cash et construction | 5×1 **+585 £/an**, valeur **−29,62 %** ; NO-GO |
| **24, deux quais fret** | Vrais quais joints, attendre cargaison et renforcer flotte | **11 doubles quais et 22 camions achetés**, 5×5 **+8 887 £/an** H5, p=0,0625, H2/H3 non-érosion non démontrée ; 0/5 |
| **25, projets PAX obsolètes** | Filtrer au classement les villes déjà servies, puis réélire | 2×3 : v25a **−10 443 £/an** H3 ; v25b **−10 246 £/an** ; moins de refus redondants, pas de gain |
| **26, quai bus limitant** | Ajout physique de quais et passage 2→4 bus sur lignes PAX existantes | Vrais quais et renforts ; 5×5 **+9 121 £/an** H5, p=0,625 ; Opex/AAA **3,7 %**, 0/5 |
| **27a/b, MAIL de ville à ville** | Fourgons MAIL neufs puis BFS uniquement sur route existante connectée d43..80 | Une petite ligne MAIL construite en v27a ; H2 **−10 260 £/an** ; v27b aucune longue ligne et **−6 082 £/an** |
| **28a/b/c, double quai bus 1/1** | Ajouter successivement deux vrais quais, renforcer seulement après validation | v28a change des lignes déjà 2/1 ; correction v28b : **aucune exposition**, H3 −1 180 £/an ; récupération de marqueurs validée sans gain |
| **29, marché PAX shadow d43..80** | Compter producteurs marginaux, vrais fronts BUS, sans construire ni classer | 5×H1 **+3 325 £/an** mais 2×H2 **−4 966 £/an** ; **aucun nouveau projet** : delta dû au calendrier, pas aux routes |
| **30/30a, unités PAX et sites** | Corriger producteurs vs PASS/mois, vrais volumes mensuels de la ville et sites ; multi-quartiers étudié | V30a 5×5 **+5 500 £/an** H5, p=0,625 ; ratio Opex/AAA **3,57 %**, non qualifié |
| **31/31b, flotte initiale PAX** | N'acheter plus de bus que si quais et économie réelle le permettent | V31b seed100 : 3 bus au lieu d'un, mais **−2 186 £/an** H1, **−7 736 £/an** H2, valeur −95,1 % ; NO-GO |
| **32/32b, corridor segmenté** | Petits gaps et ancres routières | `SEGMENT_OPCAP` 47–80k opcodes, **aucun LONG** |
| **33, corridor sparse** | Chaînage creux et gardes physiques | 1×H1 : **−1 694 £/an**, zéro corridor, valeur −33,58 % ; NO-GO |
| **34, volumes locaux LONG** | Mesure dimensionnellement correcte avant tracé | Vrais marchés estimés **258** et **175 PASS/mois** d158/d154 ; sonde seulement, aucun tracé ni livraison |
| **35, Portal-Stitch** | Scanner proche des sites et portail de voirie orienté | Sites physiques mais `BAND_1_EDGE_OCCUPIED`, `BAND_10_GAP_TURN`, aucun LONG ; H1 −31 £/an |
| **36, Graph-Bridge** | Sleeves réellement connectés, couloirs FAST, cache, site-rank AIR/RAIL, détours et réparation A* locale | **20 smokes environ documentés**, dernier 14 expansions/18 209 ops, aucun LONG, H1 **−1 691 £/an**, NO-GO |
| **37, projet interrompu** | Préenregistrement d'un A* ROUTE reprenable par tranches PO01C, idée inspirée du RAIL | **Interrompu sur ordre utilisateur avant intégration, tests et smoke.** Aucun résultat économique ; ne pas le présenter comme une tentative moteur validée |

## Pourquoi les longs tracés n'ont jamais abouti

**ROAD100-16 v1–v19b** a progressivement exploré : scans de sites de
plusieurs couronnes ; classement et dispersion des villes ; BFS sur route
déjà connectée ; A* synchrone (v9b–v12) ; polylignes géométriques puis
`AITestMode` (v13–v14) ; arrêts traversants alternatifs et façades
orientées (v15–v17) ; manchons réutilisant les routes publiques (v18) ;
sorties urbaines à détours bornés (v19b). Les A* synchrones ont coûté
~171–177k opcodes pour 90–116 nœuds sans atteindre l'autre ville ; les
polylignes et manchons ont rencontré des arêtes refusées par OpenTTD.
Une version a échoué en compilation Squirrel car `parent` est réservé ;
sa compilation invalide ne compte pas dans les résultats économiques.

**ROAD100-32 à 36** ont tenté de réduire le coût : ancres segmentées,
liaisons sparse, portails, sleeves connectés, géométrie FAST orthogonale,
micro-doglegs de largeur 1 à 3, priorité aux sorties réellement jointes,
classement des 16 couples de sites avant réduction Top-3, puis A* local
best-first sans et avec sondes natives. Le classement des sites **fonctionne**
(scores 8/4 et nouvelles paires) et produit des traces de 64–77 arêtes.
Mais le vérificateur physique échoue encore à d63 index21 `error260`
et d68 index18 `error1281`. `error260` indique un problème de zone non
libérée ; **`1281` n'est pas le code `ERR_ROAD_CANNOT_BUILD_ON_TOWN_ROAD`
(2307)**. Sa signification exacte demeure non prouvée. Même la recherche
arithmétique locale ne dépasse pas 14 expansions/36 états/18 209 opcodes
dans sa limite de 18k. **Aucune trace GRAPH n'a passé le préflight complet
avec dépôt, devis, vraie construction, bus et PASS livrés.**

Un échec de route spéculative ne démontre pas que **tous** les parcours
sont impossibles : il constate que les méthodes essayées n'ont pas trouvé
de construction admissible **sous les budgets et sites utilisés**.

## Erreurs d'interprétation corrigées

1. `AITile.GetCargoProduction` en NoAI retourne un nombre de
   **producteurs**, et non des PASS/mois. Les plafonds de recettes
   V16/V19b/V20/V29 calculés en assimilant ces deux unités sont invalidés.
   La sonde V34 a trouvé, sur les mêmes types de racines, 258 et 175
   PASS/mois **estimés**, pas livrés : aucune conclusion « demande LONG
   trop faible » ne doit être tirée des anciens 7–35 producteurs.
2. Le `waiting` constaté **après construction** sur une gare AAA ne
   peut pas être introduit dans les prévisions ex ante d'Opex.
3. `LINE_REVENUE` réalisé par véhicule/lignes ne correspond pas exactement
   à la comptabilité `profit_year` de l'entreprise. Flotte et âge
   changent souvent entre prévision et résultat ; un gros ratio sur
   une seule ligne ne permet pas de booster tous les candidats.
4. La réussite d'un `AITest` sur une gare ou un morceau de route ne
   garantit pas la construction simultanée des deux gares, du dépôt
   et de la continuité routière. Une tuile de route existante n'est pas
   nécessairement connectée à sa voisine.
5. Les sondes SHADOW qui ne construisent rien peuvent quand même
   décaler PO01C et l'ordre des décisions. Le delta ON−OFF de société
   n'est **pas** du profit provenant d'un projet inexistant.

## Enseignements et résultat final

AAAHogEx exploite très tôt **des lignes interurbaines bien plus longues**,
une couverture multi-quais et plusieurs dizaines de bus, tandis que
les lignes construites par Opex sont principalement petites, à 1–2
véhicules et captation limitée. L'écart de **volume physique** domine :
le portefeuille ne se remplit pas de projets assez rentables. Les
améliorations isolées de capacité (24, 26), fret (21) et demande (30a)
ont montré de vraies constructions et quelques gains Opex, mais **pas de
parité, pas de gain robuste et cumulatif à H1–H5**. Diminuer les seuils
ROI ou ouvrir plus de TopK n'a pas réparé le goulot de site/tracé/volume.

**Décision finale : ROAD100 arrêté à 0/5.** Pas d'autre expérimentation,
pas de 5×5 ni Gate A40×5, pas de changement de défaut ni de publication
Git sans nouvelle demande explicite. Les bundles/JSON/logs, tests et
worktrees préexistants sont conservés. Le fichier expérimental V37
`ai/OpexAI/road100_resumable_search.nut`, s'il est présent, est
**non intégré, non validé et non utilisé** : il ne prouve rien.

## Où relire les preuves

Le journal longitudinal et les liens vers chaque campagne sont dans
[`road100_etapes_20261027.md`](road100_etapes_20261027.md) ; l'état de
travail et les garde-fous dans [`taches.md`](taches.md). Pour les derniers
essais : [`road100_graph_bridge_prereg_20261028.md`](road100_graph_bridge_prereg_20261028.md),
[`road100_v35_portal_stitch_resultats_20261028.md`](road100_v35_portal_stitch_resultats_20261028.md),
[`road100_calibration_pax_40graines_20261028.md`](road100_calibration_pax_40graines_20261028.md),
[`road100_site_first_resultats_20261028.md`](road100_site_first_resultats_20261028.md).
Les résultats complets des campagnes appariées se trouvent dans `results/`.
