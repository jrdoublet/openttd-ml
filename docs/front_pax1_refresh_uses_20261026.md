# FRONT-PAX-1 — portée des bornes et points réels de rafraîchissement

26 octobre 2026. Audit **statique**, sur `e928c20d`, complément ciblé à
[`DIST-BORNES-1`](dist_bornes_inventaire_20261025.md), à la
[preuve rétrospective du clamp](front_pax_clamp_bornes_20261025.md) et au
[journal du diagnostic instrumenté du 25/10](journaux/journal_2026-10-24_nuit_75pct.md).
Aucune modification des filtres, aucun banc ni changement de réglage.

## Producteur et rafraîchissements

`OpexRefreshEpochBounds` (`ai/OpexAI/candidates.nut:400-487`) stocke les
bornes de l'époque dans `catalog.bounds`. Les appels ne sont **pas limités à un
événement par année**, ni nécessairement à un rafraîchissement complet du
catalogue :

| Chemin | Site | Condition/effet |
|---|---|---|
| Rafraîchissement du catalogue | `catalog.nut:1078-1082` | Recalcul dans le budget `cat_bounds` |
| Moteur nouvellement disponible | `event_handlers.nut:440-445` | Pose `_recomputeEpochBounds=true` et recalcule **immédiatement** si le catalogue existe |
| Rafraîchissement partiel | `orchestrator.nut:936-941` | Recalcule si le drapeau est encore posé, puis l'efface |
| Reconstruction des projets | `orchestrator.nut:1308-1311` | Même garde sur le drapeau |
| Tâche d'ordonnancement | `scheduler_tasks.nut:424-427` | Même garde sur le drapeau |
| Accès à des bornes absentes | `candidates.nut:489-505` | `OpexCatalogBounds` tente un recalcul si `catalog` existe mais que `bounds` est nul ; sinon retourne des valeurs de secours non journalisées |

Par conséquent, le handler d'arrivée de moteur et un chemin ultérieur peuvent
recalculer les bornes si le drapeau reste armé. `EPOCH_BOUNDS` est émis **à chaque
appel qui atteint la fin du recalcul sous `DECISION_LOG`** (`candidates.nut:479-486`),
et non une fois par époque, par paire ni par projet. Dédupliquer les mêmes
`(partie, jour, payload)` aide à caractériser des *états* observés, mais peut
masquer des *exécutions* distinctes du calcul et leur coût. Une sonde de coût
doit donc entourer chaque appel, et une synthèse doit séparer émissions brutes,
rafraîchissements et valeurs finales distinctes.

## Consommateurs : ne pas confondre seuil économique et garde effective

| Famille | Garde de distance effectivement traversée | Particularité |
|---|---|---|
| ROUTE | `OpexRoadDistanceAllowed`, `candidates.nut:508-520`, dans les générateurs route et V276 | Manhattan de `roadMin` à **`roadGenMax`** (repli `roadMax`), même si `roadMax=roadMin` ; C42 fait aussi `roadMin…roadGenMax` (`:2180-2183`) |
| RAIL PASS | `OpexRailPaxPairInBand`, `:537-546`, avant `OpexMakeCandidate` ; `OpexMakeCandidate` impose en plus `railMin…railMax` (`:679-689`) | `AIR_RAIL` = `[railAirOverlapMin,railMax]`, `RAIL_ONLY` = `[railMin,railAirOverlapMin)`, autres = `[railMin,railMax]` |
| AIR PASS | `OpexAirPairInBand`, `:523-535`, appelé par les générateurs AIR | `AIR_ONLY` exige Manhattan **strictement supérieur** à `railMax`, `AIR_RAIL` est inclusif `[railAirOverlapMin,railMax]`, `ALL` commence à `airMin`; `airMax`, si positif, borne **la distance de vol**, distincte du Manhattan |
| RAIL fret | `OpexMakeCandidate`, `:679-693`, sans plancher `railMin` PASS | Peut admettre la relaxation V269 au-delà de `railMax`, **mais** V276 préfiltre la grille fret à `railMax` (`candidates_v276.nut:139-144`) et réutilise la garde PASS `OpexRailPaxPairInBand(..., ALL)` sur tout mode `rail` (`:278-280`). Ce double écran est déjà documenté dans `DIST-BORNES-1`. |

`projects.nut:148-151` dérive les bandes PASS du stage (`AIR_ONLY`,
`AIR_RAIL`, `RAIL_ONLY`), tandis que les autres chemins de génération peuvent
appeler la bande `ALL`. `PAX_BAND_ROUTE_ONLY` est affecté aux unités V276 de
route, pas à une partition supplémentaire de RAIL PASS. Les constantes de bande
ne sont donc ni des bornes numériques ni une preuve de projet constructible.

## Deux sources d'observation, deux portées

- **80 jeux 1970–1979 SOLO/DUEL :** 2 109 émissions `EPOCH_BOUNDS`, 1 524
  états distincts, 585 réémissions identiques ; clamp haut RAIL→AIR démontré
  dans cette archive, mais les *motifs* de `roadMax=7` ne sont pas récupérables
  des champs historiquement consignés.
- **Diagnostic instrumenté distinct, 5 graines × 5 ans :** le worktree
  expérimental `.worktrees/nuit75-front-pax1` du 25/10 a déjà ajouté un
  marqueur `FRONT_PAX_BOUNDS` sous `DECISION_LOG` et obtenu **40 recalculs
  uniques** (45 marqueurs, cinq doublons), dont **40/40**
  `road_reason=delta_nonpositive`, `road_raw=-1`, ainsi que `rail_raw=439`
  rabattu à `rail_max=200` par V294. Voir
  [`journal de nuit`, lignes de diagnostic](journaux/journal_2026-10-24_nuit_75pct.md).
  C'est une preuve **pour cet échantillon instrumenté**, pas l'imputation
  rétroactive de la cause aux 80 jeux ni un comptage de paires voyageurs.

Le prototype n'a pas été adopté sur `master`. Sa neutralité d'opcodes **OFF
versus ON** n'a pas été mesurée, son profil CPU est incomplet et sa trajectoire
n'a pas de témoin non instrumenté. Ne pas refaire ce prototype ou la campagne
5×5 comme s'ils n'existaient pas ; pour une étude nouvelle, identifier d'abord
la couverture manquante, comparer les opcodes de mêmes mondes et tracer les
projets PASS réellement exclus, leur site, leur financement et leur suite.
FRONT-PAX-2 a par ailleurs été clos sur un **NO-GO d'exposition tardive** ; son
résultat ne qualifie aucun déplacement de frontière. **FRONT-PAX-1 reste
ouvert** pour la couverture des motifs au périmètre visé et la neutralité de la
sonde ; aucun gain de profit ou changement de défaut n'est établi ici.
