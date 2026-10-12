# V151d — revue du code : scan AIR, sélection, flotte (12/10)

Revue statique guidée par les spans V151c (`v151c_spans_3x5_20261012`, graines 42/100/999) et
les compteurs `AIR_PLAN_PERF`. Les chiffres sont par graine et par an. Chaque levier passe par la
règle des optimisations d'opcodes (gain d'opcodes + 20×10 neutre) ; un levier **strictement
équivalent** se vérifie d'abord par décisions identiques sur un A/A instrumenté.

## Classement

| # | Levier | Coût mesuré | Gain attendu | Équivalence |
|---|---|---|---|---|
| 1 | **Flotte AIR : tester les gardes C121 « O » avant `OpexC121RefreshVisibleFleet`** (`task_air.nut:1176`) | `fleet.resize` 5,8 M (1973), 16,6 M (1974), 155 k/appel et croissant | ~70–90 % du poste | Décisions identiques, sauf l'âge du cache de cible (rafraîchi au moment où la ligne redevient éligible) |
| 2 | **Sélection : insertion par dichotomie sur clés mises en cache** (`OpexProjectInsertDefensive`) | `pub.select.score.insert` 6,6–10 M (1973), ~2,2 k/insertion | ~80 % de l'insertion, 5–9 M/an de 1972 à 1974 | **Stricte** quand C118 et le shadow C122 sont éteints (défaut) |
| 3 | **Revalidation incrémentale indexée** (`OpexCandidateStillValid` dans `select.incremental`) | 440 k exclusifs/appel en 1973 (7,5 M/an, graine 42) | ~70 % | Stricte si les index reproduisent les prédicats |
| 4 | Publication AIR 1970–71 : une resélection complète par publication (~270/an, 90 k chacune) | ~24 M/an en 1970–71 | à mesurer | **Non** : change le moment de la sélection, banc obligatoire |
| 5 | Régénération réactive ciblée AIR (V151a) | ~2 régénérations complètes/partie (01/1972, 01/1973), ~7 M chacune | ~3 M/an | Non stricte |
| 6 | Scan AIR : la demande coûte ~22 k par échec de cache (géométrie), le reste est négligeable | 4,5 M de demande sur 5 ans (graine 42) ; 1 424 succès / 200 échecs | faible | — |

## Détails

**1. Flotte.** Sous C121 (défaut), une ligne ne passe la garde `T` que si `have < targetAirPlanes`,
donc `c121BelowTarget` est vrai et les gardes « O » s'appliquent : âge < 2 ans, `lastProfit <= 0`,
croissance il y a moins de 2 ans. Aucune ne dépend de la valeur de la cible. Or le
rafraîchissement, qui rejoue la demande, la concurrence, le moteur et l'économie et construit
`others` en O(lignes), est payé avant ces gardes, toutes les 30 jours par ligne, à chaque appel
de `fleet.resize` (~106 par an en 1974).

Correctif : si la ligne a déjà une `targetAirPlanes` et qu'elle sera refusée par une garde
« O » quelle que soit la cible, on la refuse avant le rafraîchissement. Le chemin first-live
(`have == 1`, jamais agrandie) est exclu, car il peut contourner ces gardes. Les champs posés
par le rafraîchissement (`targetAirPlanes`, `c121Marginal*`) ne sont lus qu'en aval d'une ligne
acceptée.

**2. Sélection.** `OpexProjectInsertDefensive` remonte la liste depuis la fin et recalcule pour
chaque prédécesseur `OpexProjectDefensiveAirPriority`, `OpexProjectSelectionScore` et le
`c118Active`, qui est invariant pendant la boucle. Hors C118 et C122, le comparateur est un ordre
lexicographique cohérent : rang défensif décroissant, score décroissant, puis revenu.

Avec ce comparateur, les prédécesseurs qui gardent la priorité forment un préfixe. La position
d'insertion se trouve donc par dichotomie, avec le même départage. Les clés restent stables
pendant un appel : les rafraîchissements de créneaux ne lisent que l'état partagé
(`servedTowns`, `servedCount`).

**3. Revalidation incrémentale.** Pour chaque candidat du vivier, la revalidation parcourt :
- toutes les lignes, pour le doublon exact ;
- deux `OpexOriginServed` pour le rail, en O(lignes) chacun ;
- quatre à cinq parcours pour la route ;
- deux `OpexAirBatchSiteStillBuildable` non mis en cache pour l'air. Les mêmes sites sont
  revalidés aussitôt après par `OpexFilterAirAlternativesStillValid`, qui, lui, a un cache par
  site.

Correctif : construire une fois par appel l'ensemble des paires bâties, l'index losange
d'`OpexOriginServed`, dont le motif existe déjà dans `OpexRoadFreightServedIndex`, avec et sans
route, et le cache de validité des sites air.

**Vu et écarté.** La mesure `GetTick`/`GetOpsTillSuspend` de la demande (~10 appels natifs par
paire) et la table `c121Demand` de 44 champs coûtent environ 150 opcodes sur 11 k par paire :
c'est négligeable, on n'y touche pas. Les panneaux `OpexSign` font partie du canal de mesure
(`debug_signs=1` par défaut) : ce n'est pas un levier.

## Hors opcodes : V153

L'autopsie V152 a mis au jour un faux `TRKFAIL`. Le contrôle final
`AIRail.AreTilesConnected(tiles[last-2], tiles[last-1], exitB)` est faux par construction
lorsque le dernier segment est un pont ou un tunnel : la tête de pont n'est pas une tuile rail
et les tuiles ne sont pas adjacentes. La ligne est alors démolie alors qu'elle est continue.
Les 6 `cause=connect failed=0` des journaux sont tous dans ce cas, avec un saut aligné sur le
quai. Correctif confié à agy derrière `rail_end_jump_connect`, défaut 0.
