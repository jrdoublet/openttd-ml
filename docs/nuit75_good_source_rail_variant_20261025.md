# Nuit 75 % — GOOD depuis usine alimentée par notre rail (variante opt-in)

Date : 25 octobre 2026. Worktree exclusif : `.worktrees/nuit75-good-source-variant`, base `83e436cc3db35ff18efb685ace4f97eb569f77b1`. Aucun Docker, commit, push ou changement de défaut effectué par ce travailleur.

## Décision de conception

Réglage unique `good_source_rail_join` (0/1), **0 aux quatre difficultés** `easy`, `medium`, `hard`, `custom`. Le chemin standard est inchangé lorsque le réglage vaut 0 : une origine fret déjà desservie est rejetée selon le contrat historique. À 1, cette politique est indépendante des modes V233 rejetés et de la croissance V284.

La candidate est **uniquement industrie productrice de GOOD → ville acceptant GOOD, encore non desservie par notre rail**. La destination industrie n'est pas déverrouillée ; les chemins V179/V264 industrie→industrie restent intacts. Une usine source est éligible si `OpexOriginService` identifie sans ambiguïté la **gare B de notre ligne rail existante** terminant à **la même industrie** (`dstIndustry`), que cette ligne apporte un cargo **différent de GOOD et accepté par l'industrie**, qu'elle n'est pas en ferraillage et conserve au moins un véhicule vivant, avec StationID train valide, tuile de gare de notre propriété et plan de quai B persistant. Une gare voisine, un service route et un simple transport GOOD existant ne suffisent pas.

Le candidat porte `goodSourceJoin=1`, `goodSourceLineId`, `goodSourceStationTile`, `joinStationId`, `joinPlatform`, `joinEnd="A"`, `dstTown` et `originServed=true`. Aucun `joinLineId` n'est posé : `_tooClose` conserve ses interdictions physiques en B et aux autres gares en A. La dérogation pour A vise **seulement les extrémités ayant le StationID que la nouvelle gare doit rejoindre**, y compris si plusieurs lignes partagent cet identifiant. La condition de trésorerie, le score économique et le filtre d'opcodes historiques restent actifs.

## Garantie de jonction et de captage

`OpexMakeCandidate` accepte `sourceJoin=true` uniquement pour ignorer le prédicat de **site A neuf**. La preuve physique ne repose jamais sur ce raccourci : `OpexRailPlatformPlans` impose le nouveau quai A généré par `OpexJoinPlatformPlans` qui valide `AIRail.BuildRailStation(..., joinStationId)` en `AITestMode`, et filtre **chaque quai A** avec `OpexRailPlatformCargoValue(..., cargo=GOOD, wantProduction=true)>0`. Le quai doit donc être constructible, joindre la gare et capter une production GOOD positive dans sa propre empreinte. B conserve la recherche standard d'une nouvelle gare de destination acceptante.

Le `strictOriginReuseJoin` oblige le constructeur à rendre SITEA/SITEB/SITEAB si la jonction A échoue ; **aucun fallback sur une gare A indépendante**. `OpexGoodSourcePlanSafe` vérifie avant le devis et juste avant la première dépense que la gare d'origine est encore celle requise (`joinStationId`), que la compagnie la possède et que le quai prévu capte GOOD ; les deux constructeurs réellement empruntés (mono et V190) recontrôlent après `BuildRailStation` que la nouvelle ancre possède le **même StationID** et appartient à la compagnie, sinon déclenchent l'annulation. Le mode V198 qui remplace les deux sites par des quais indépendants est écarté pour cette variante. La protection reste contrôlée même si l'A* est repris après plusieurs tours et si le devis reconstruit une interface exacte.

La ligne d'approvisionnement est recontrôlée dans le précontrôle rail, avant consommation d'une recherche A* et lors de la revalidation C80 des plans stockés. C80 accepte explicitement la paire `industrie→ville` uniquement sous le marqueur GOOD, avec `AITown.IsValidTown(dstTown)` ; les autres candidats fret continuent à exiger les deux IndustryID historiques. Une ligne fournisseur détruite ou ferraillée entre proposition et construction invalide le projet. Les traces sous `decision_log` sont `GOOD_SOURCE_KEEP`, `GOOD_SOURCE_REJECT` et `GOOD_SOURCE_RESULT`, ce dernier indiquant supplier, StationID attendu/réel, résultat, raison, profit prédit et coût réel.

## Opérations et persistance

Le réglage OFF ne lance aucun inventaire de quais, de cargo ou de véhicule dans le nouveau helper : il s'arrête sur `!GOOD_SOURCE_RAIL_JOIN`. Lorsque ON, la résolution du service est déjà mémorisée par source/industrie dans la génération ; le fournisseur GOOD est vérifié **une fois par usine et cargo**, puis réutilisé pour les destinations villes. La vérification des quais est limitée aux candidats GOOD choisis pour construction. Le builder conserve les plafonds A* et les gardes financiers existants ; il ne lance aucune recherche supplémentaire après échec A.

Les métadonnées du fournisseur sont transitoires dans les candidats. PO01C est **régénéré mécaniquement** avec `python -X utf8 sweeps/po01c_generate.py` ; les coroutines suspendues ne sont pas sauvées et sont reconstruites à la reprise comme avant. Les lignes rail persistent `dstIndustry`, `lineId`, `vehicles`, `stationB`, `platformB` selon le contrat Save/Load existant. Les contrôles C80 et source vivante rejettent les associations devenues obsolètes après rechargement. Aucun nouveau format de sauvegarde nécessaire.

## Vérifications hors Docker

Toutes les suites ci-dessous ont réussi :

| Suite | Réussites |
|---|---:|
| `test_good_source_rail_join` (incluant cas géométriques Python à production nulle/positive) | 7/7 |
| `test_po01c_regen_split` (équivalence générateur) | 27/27 |
| `test_v276_candidate_slices` | 26/26 |
| `test_v264_convergent_freight` (géométrie dynamique du joint/spread) | 10/10 |
| `test_v178_rail_shared_dest` | 8/8 |
| `test_v251_inventory`, `test_v246_fixed_policies`, `test_v259_bridge_renew`, `test_v284_rail_growth`, `test_parameter_retirements_20261023` | 7+6+14+12+4 |
| `test_b5_rail_persistence`, `test_c69_reload_contract`, `test_c121_air_first_year_rail_prep` | 11+4+4 |
| `test_c80_rail_stock_worker`, `test_c80_rail_stock_gate`, `test_v190_rail_double_build` | 18+8+18 |
| `test_rail_geometry_guard`, `test_rail_cached_proximity_gate`, `test_inventory_squirrel_loops` | 12+4+3 |

`git diff --check` : succès. Les anciens tests de plafond de configuration passent de **58 à 59**, sans retrait ni modification des 58 options existantes. Quatre SHA de sources historiquement épinglées (candidates, settings, info, builder_rail) ont été rebaselinés **uniquement pour les fichiers modifiés** ; les autres empreintes historiques restent figées. Le contrôle hors jeu ne démontre **pas** l'absence de dérive de trajectoire liée aux opcodes supplémentaires, qui requiert le smoke et les portes appariées du prime.

## Exposition, risques, suite

À mesurer en jeu : nombre `GOOD_SOURCE_KEEP` par graine, pourcentage classé dans les projets, `GOOD_SOURCE_RESULT` (`SITEA/SITEB/SITEAB`, `NOPA`, `STNFAIL`, succès), comparaison `actual==join` pour chaque succès, heures/opcodes de génération des candidatures GOOD, nombre de lignes construites et rentabilité. Le principal verrou possible est une usine alimentée par une gare B dont **aucun quai parallèle constructible ne capte GOOD**, notamment si la production est juste à la limite de couverture ou si la gare existante occupe les seules tuiles utiles ; dans ce cas la politique **refuse** de créer une gare neuve. Aucune exposition réelle ni amélioration économique ne sont affirmées ici.

Préconisation au prime : smoke mechanism OFF/ON sur carte 256², vérifier log `GOOD_SOURCE_KEEP` → `PROJECT_CHOSEN` → `GOOD_SOURCE_RESULT` avec StationID A réel conforme. Si exposition et construction validées, porte A 40×3 puis B 20×10 selon le protocole nocturne et la règle de profit Opex/AAAHogEx. Aucun résultat de banc n'est contenu dans ce rapport.


## Résultats moteur du prime — 25/10/2026

Après freeze du code : smoke graine42 1x1 sain, delta ON-OFF 0, bundle SHA256 4da09e927f64bc110ee2da6752131226a2ab9fdd792e0670f2b80bcc1790b808. Diagnostic 1x10 seed100 : 6/28 tentatives GOOD_SOURCE_RESULT réussies avec `actual=join`, delta économique +838 426 £/an mais un seul monde. Porte A `nuit75_goodsource_porteA_40x3_20261025` 40/40 paires saines, delta Opex +4 262,075 £/an, p=0,9789153, IC95 [-11 334,4 ; +22 239,825] £/an, seuil 4 % +89 549,093 £/an, company_value +0,4634 %, V/D/E 12/13/15 : verdict `fail_primary`. Manifeste A 9021c1f90b718facfa426c5000602342d03e5e5fb8e580ebe67d4d03cadc4549. Aucune porte B, défaut OFF et aucun commit.

## Réévaluation tardive explicitement approuvée — A40×10 multimodal

Le 25/10, l'utilisateur a approuvé A40×10 pour les politiques
exposées après 1973, puis a également ouvert l'alternative A40×5
rail seul ou multimodal. **GOOD conserve le profil 40×10 multimodal
car déjà lancé et observé en 1977/1979**. Code inchangé : 84/84 fichiers
IA identiques en SHA256 au bundle historique
`4da09e927f64bc110ee2da6752131226a2ab9fdd792e0670f2b80bcc1790b808`.
Campagne `nuit75_goodsource_porteA_40x10_20261025`, 40/40 paires
saines, 1970–1979, 256², `probes=2` symétriques, 9 workers max.

**Résultat : `fail_primary`** : Δ Opex `profit_year` moyen
**+127 819,45 £/an**, médiane +156 160,5 £/an, **28V/12D**,
Wilcoxon exact bilatéral **p=0,0548103** (échec),
IC95 bootstrap **[+18 683,25 ; +239 499,375]** (borne positive),
seuil relatif +4 % **+170 929,10 £/an** (échec),
garde valeur **+0,74543 %** (passe). Aucun déclenchement de B20×10.

| Profil fin 1979 | Opex moyen £/an | AAA moyen £/an | Ratio profits moyens | Médiane ratios appariés |
|---|---:|---:|---:|---:|
| OFF=0 | 4 273 227,50 | 7 565 478,05 | **56,4832 %** | **55,3267 %** |
| ON=1 | 4 401 046,95 | 7 445 675,88 | **59,1088 %** | **60,0331 %** |

Chaque profil possède 40 dénominateurs AAA positifs appariés à
ses **propres** mondes. Calcul explicite par
`sweeps/analyse_nuit75_gate_ratios.py` ; artefacts
`results/nuit75_goodsource_porteA_40x10_20261025.json`,
`results/nuit75_goodsource_porteA_40x10_20261025_ratios.json`.
75 % non atteint, aucun défaut adopté, pas de commit/push.
