# ROAD100-2 — bus intra-urbains ROAD seul, preregistration (27/10/2026)

## Motif distinct de ROAD100-1

ROAD100-1 (bus ville↔ville) a expose 363 opportunites positives et construit
cinq bus sur la graine 42, mais son diagnostic 5×1 `road100_solo_pax_expo_5x1_20261027`
donne **−410 £/an**, 3V/2D, IC95 recouvrant largement zero. Ce n'est ni un
gain qualifie ni un chemin credible vers la parite de 134 k£/an a un an.
Les cinq lignes de cette graine avaient 14 a 50 cases entre villes, un seul
bus chacune et 2,8 a 4,7 k£/an de profit prevu a la construction.

Le concurrent utilise egalement des **TownBus** dans une meme ville, entre
deux stations distinctes, avec arrêts rapproches, alors qu'OpexAI n'a aucun
generateur pour ces lignes. Ceci fournit une hypothese neuve : un trajet
local permet plus de courses payantes et moins de temps mort/route construite,
et sert une population deja concentree. Nous n'importons aucun code tiers.

## Intervention

`road100_town_bus=0` aux quatre difficultes, `1` = candidats PAX locaux
uniquement si `MODE_ROAD` est le seul mode effectif. Une paire maximum par
ville : deux ancres distinctes a cinq cases du centre sur un axe, si elles
restent dans la meme ville. La production cible est bornee par la production
mensuelle de voyageurs de la ville et environ vingt maisons de captage
cumulees sur les deux arrêts, maximum 86 % de la ville. Le candidat parcourt
le pipeline existant `OpexMakeRoadCandidate` → score → site/trace → economie
recalculee → financement → construction. La garde `OpexTownBusPaxServed`
empeche de desservir deux fois les memes passagers. Aucun levier de cadence,
de profit minimum ni de classe de financement ne change simultanement.

`ROAD100_TOWN_GEN` donne le nombre de villes retenues et de candidats
economiquement positifs. `ROAD_BUILD cargo=PASS` et les traces de causes
`SITEA`, `SITEB`, `SPACING` fournissent l'exposition reelle.

## Mesure predefinie

Smoke causal 1 graine × 1 an (42), puis diagnostic 5 graines × 1 an
(42,100,7,999,2026) si construction et sante etablies, comparaison OFF/ON
sur le **meme code fige** avec `road100_solo_pax=0`, `estim_unifie=31`,
ROAD seul Opex et AAA tous les autres modes desactives. Objectif prioritaire :
100 % du **profit annuel de l'AAA a un an**, ratio des moyennes et quatre
trimestres reconstitues, avec hausse de profit Opex elle-meme. Si resultat
convaincant sur diagnostic, 40×5 descriptif pour quantifier les cinq annees ;
autrement `NO-GO` ou nouvelle conception. `ROAD100-1` n'est pas requalifie par
un essai `ROAD100-2`.

Si on envisage un nouveau défaut, appliquer ensuite V102 A40×3 +4 %, p<0,05,
IC95 bas >0, garde de valeur −5 %, et B20×10 sur autorisation specifique
avec non-erosion et garde de valeur. La parite face a AAA est un objectif
descriptif supplementaire, pas un substitut a ces portes. Aucun changement de
défaut ni commit/push implicite.
