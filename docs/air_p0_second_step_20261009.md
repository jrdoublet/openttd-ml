# P0 AIR — défaut de profondeur du devis 2→3, protocole et verdict

## Défaut identifié avant toute variante

`OpexC121MeasureBuiltEconomics` (`air_catalog_c121.nut`) calcule au chantier un seul marginal
`P(N0+1)-P(N0)` et le stocke dans `line.c121MarginalProfit/Revenue`, échantillons `0`.
`OpexProjectFromFleet` (`projects_builders.nut`) réutilise ce champ à chaque
renfort en dessous de `targetAirPlanes` jusqu'à la première réalisation annuelle.
`OpexC121RefreshVisibleFleet` réactualiserait le marginal mais le réglage
`c121_air_visible_competition=0` le désarme par défaut.

Sur les trois graines instrumentées 42/512/65537, 17 achats **2→3** avec
`marginal_samples=0` et un achat 1→2 antérieur connu présentent strictement
le **même cache de marginal** au second achat ; exemple graine 42 ligne 3 :
`c121MarginalProfit=101984` lors de 1→2 et lors de 2→3. Le `pred_profit`
peut avoir été recalibré via C121 par bras, mais sa profondeur économique
reste erronée. Ce constat est du **code et des logs réels**, sans estimation
contrefactuelle de son coût économique.

## Correctif candidat OFF et invariants

Le réglage `air_p0_second_step_marginal=0` (quatre difficultés) n'introduit
**aucun seuil numérique**. Activé, il capture dans **le scan C121 de cible
déjà exécuté** les profits `P(N0+1)` et `P(N0+2)` pour le même modèle,
les mêmes ports, le même moteur et la même demande; il mémorise les scalaires
`c121SecondStepHave/Profit/Revenue` sur la ligne. Lorsqu'un nouvel achat est
proposé sans échantillon réel, **uniquement au palier N0+1→N0+2**, il emploie
le vrai écart `P(N0+2)-P(N0+1)` au lieu de `P(N0+1)-P(N0)`.

`samples>0` laisse l'observation réelle prioritaire. Le devis live C121 visible
(`c121_air_visible_competition=1`) reste prioritaire : il désactive la
substitution froide. Un ancien save sans nouveaux champs conserve le témoin.
Les remplacements, refleet de crash et nouvelles lignes ne sont pas transformés
en renforts par ce patch. Une éventuelle erreur de profondeur **3→4 et suivantes**
n'est pas réparée dans cette expérience isolée; ne pas généraliser le résultat.

**Contrôle de parité supplémentaire** : quand `air_p0_margin_probe=1`
est activé dans les deux bras de diagnostic, les deux construisent les
*mêmes* captures P(N0+1), P(N0+2), les mêmes champs persistants et évaluent
la même condition d'éligibilité (`secondStepAvailable`) ; le bool de décision
ne diverge qu'au moment d'employer cette marge pour scorer le renfort. Au
défaut normal (les **deux** flags OFF), aucune capture additionnelle n'est
effectuée. La branche diagnostic rajoute des opcodes identiques dans les
deux bras mais ne doit pas être assimilée au profil de production non sondé.

## Pré-enregistrement du diagnostic moteur (avant exécution)

1. **Contrat/smoke** : tests ciblés `sweeps/test_air_p0_second_step_marginal.py`,
   harnais selftest, smoke 42×1 avec ON/OFF, mêmes sources/AAA.
2. **Diagnostic causal apparié** si smoke sain : graines **42,512,65537**,
   5 années 1970–1974, `--script-debug`, télémétrie mensuelle de lignes,
   `air_p0_margin_probe=1` dans les **deux** bras pour observer rangs et achats,
   seul `air_p0_second_step_marginal` diffère. 6 parties complètes, un bundle
   figé commun. `--cpus 10 --memory 8g --max-workers 6`, une campagne à la fois.
3. Mesures pré-spécifiées : `profit_year` OpexAI en décembre 1973 et 1974,
   `company_value` (garde −5 %), véhicules et lignes AIR, achats froids
   2→3 réellement sélectionnés, devis/score, autres constructions et
   opcodes aux étapes du modèle si mesurables. Les visites répétées du TOPK
   ne sont pas des achats indépendants.

**Décision** : un diagnostic 3×5 n'est jamais une porte V102; si signal
économique robuste et confirmé mécaniquement, V102 A40×3 (`gain_short`,
seuil +4 % et IC95/Wilcoxon, garde valeur −5 %), puis B20×10
(`non_erosion`) **uniquement** si A passe. Aucun défaut/adoption/commit/push
sans ces deux portes. Le surcoût cible est seulement deux tuples capturés
dans le scan déjà payé, non une nouvelle évaluation lourde; **le coût en
opcodes reste à mesurer**. Les différences ON/OFF peuvent également refléter
des décalages de cadence par opcodes; vérifier la première divergence avant
d'attribuer un gain/perte au seul nouveau score.

## Premier diagnostic 3×5 — non retenu pour attribution stricte

`air_p0_second_step_3x5_20261009_r1`: 6/6 parties saines,
bundle `70560f52919b5ff3fc173494bd53cba76628cdb0dd2589ddf84936a61d3d1880`,
variante − référence `profit_year` moyen **−18 258 £/an**, V/D/E=1/2/0,
IC95 traversant zéro, ratio de `company_value` −3,25 % ; 35 achats 2→3
en variante contre 31 en référence. Les premières divergences de journaux
apparaissent au 2→3 sur seeds42 et 65537, mais la graine512 présente une
petite divergence `cost_cash` avant le premier 2→3 différent : le surcoût
de capture n'était pas symétrique à la construction dans r1.

**Second diagnostic pré-enregistré avant lancement** : exactement les
mêmes 3 graines et 5 ans, mêmes réglages P0 de journalisation sur les
deux bras, mais **capture/éligibilité partagées sur les deux bras** et seul
le choix `secondStepAvailable && air_p0_second_step_marginal` diverge.
Objectif : vérifier d'abord l'identité des décisions antérieures au 2→3,
puis mesurer le profit final et les constructions réellement modifiées.
Ne pas agréger r1 et r2 comme six graines indépendantes ni lancer V102
si la petite étude est négative/inconcluante.

## Verdict contrôlé r2 — **REJET économique provisoire, OFF conservé**

Campagne `air_p0_second_step_parity_3x5_20261009_r2` : **6/6 parties complètes et saines**, un seul bundle figé `91227a3eba8bf035915392d05f8eef9ed1e269a6907c734a6ab07b16d5b55b13`. Le diagnostic `air_p0_margin_probe=1` est commun aux deux bras : chaque ligne capture les *mêmes* devis P(N0+1) et P(N0+2) dans le scan déjà existant. Seul le rang établi au 2→3 à froid utilise le second devis dans le bras variante. Le smoke de parité graine42×1 était parfaitement identique (2/2 sains).

| Graine | Δ `profit_year` variante−référence fin 1972 | fin 1973 | fin 1974 | Δ `company_value` fin 1974 | Δ avions AIR fin 1974 | Δ lignes AIR fin 1974 |
|---|---:|---:|---:|---:|---:|---:|
| 42 | −171 935 £ | −141 116 £ | **−82 885 £** | −745 068 £ | −18 | −3 |
| 512 | 0 £ | −48 041 £ | **−70 073 £** | −185 136 £ | −6 | −5 |
| 65537 | +28 919 £ | −28 765 £ | **−52 316 £** | +6 721 £ | +9 | +3 |
| **Moyenne** | — | — | **−68 425 £/an** | — | — | — |

**Trois défaites sur trois**, IC95 bootstrap indicatif [−85 796 ; −51 054] £/an (3 graines, intervalle non qualifiant), ratio de la **valeur moyenne** variante/référence **−5,55 %**, au-delà de la garde V102 −5 %. `AIR_P0_BUY` compte 113 renforcements variante et 116 référence sur les trois graines, dont respectivement **33 et 32** achats 2→3 : corriger la profondeur ne signifie pas « acheter systématiquement moins d'avions ».

**Contrôle de causalité de la décision, non de l'avion isolé** (événements prélevés dans les logs des deux bras avant toute divergence) :

- Graine42 : **55** événements `AIR_P0_BUY/ROUTE` initiaux identiques ; le 21/01/1972 la référence sélectionne le 2→3 de la ligne4 (devis final 62 364 £/an) alors que la variante sélectionne celui de la ligne0 (50 666 £/an). Les marchés se séparent ensuite.
- Graine512 : **14** événements identiques ; le 26/03/1972 **même achat 2→3, ligne1**, mais `pred_profit` vaut **92 725 £/an en référence contre 55 825 £/an en variante**, autres champs d'achat identiques. Preuve directe de substitution de marge à profondeur corrigée avant toute trajectoire différente.
- Graine65537 : **25** événements initiaux identiques ; la référence construit le 2→3 de ligne1 le 05/05/1972 (`pred_profit` 87 836 £/an), la variante ouvre plutôt une nouvelle ligne AIR le 06/05/1972. Les décisions aval divergent.

La première divergence est donc précisément dans la règle de **classement économique du renfort**, avec capture et coût de calcul symétrisés. **La correction est valide comme correction de profondeur du devis, mais ne gagne pas économiquement** ; les retombées dépendent de l'ordre des lignes achetées, des réseaux et des cascades. Les snapshots montrent en fin 1974 des profits AIR YTD inférieurs en variante de **−209 / −11 / −28 k£** pour les trois graines, sans attribution possible à un seul avion.

**Verdict d'adoption : NON**. Laisser `air_p0_second_step_marginal=0` aux quatre difficultés, ne pas engager V102 A40×3 ni B20×10 pour ce candidat, ne fixer aucun nouveau seuil de flotte. Les tests de contrats (4/4 Docker), smoke 1×1 et harnais sont sains ; coût opcodes total par partie et roundtrip Save/Load ciblé restent non qualifiés pour une éventuelle reprise. La prochaine hypothèse doit porter sur l'**arbitrage réseau et la fraîcheur du modèle de demande**, non sur l'obligation de prendre toujours la marge P3−P2 seule.

Reproduction de la comparaison par graine/année et des premières divergences : `python -X utf8 sweeps/analyse_air_p0_second_step_20261009.py`, qui produit `results/air_p0_second_step_parity_3x5_20261009_r2_analysis.json` depuis les logs et snapshots du *même* bundle.
