# P0 Capital — B0 ROAD, devis par composants (sonde passive)

## Motivation et périmètre

La suppression isolée du biais de financement ROAD 121 % a échoué au
V102 A40×3 (`docs/road_finance_unbias_p0_20261009.md`) : le retrait
du facteur ne démontre pas une amélioration. La piste B **ne réutilise
pas** cet échec pour changer un nouveau pourcentage : elle examine les
commandes physiques qui expliquent le devis, sans toucher à la décision.

Le modèle ROAD dans `economy.nut` calcule historiquement
`distance * coût_road + 2 arrêts + dépôt + N * prix_moteur`. Le plan final
de `builder_road.nut` contient pourtant des arêtes déjà connectées qui
ne seront pas reconstruites, les raccords spécifiques des arrêts et du
dépôt, et le choix cul-de-sac ou drive-through. Le modèle mis à jour
après siting demeure une distance multipliée par un tarif, et peut à la
fois surestimer la voirie existante et ignorer raccords/terrassements.

## Système observé B0

Réglage `road_quote_components_shadow_p0`, **0 à toutes difficultés**.
En ON, après `OpexRoadPlanFor` et révision de l'économie mais avant la
transaction, `OpexRoadQuotePlanComponents` compte sur la carte réelle :

* les arêtes du `plan.trace` non déjà connectées ;
* les deux raccords d'arrêt non connectés pour les seuls cul-de-sac
  (aucun en drive-through) ;
* le raccord de dépôt éventuellement non connecté ;
* deux arrêts au tarif BUS/TRUCK, un dépôt, et `N × prix du moteur`.

Chaque groupe donne un **proxy tarifaire**, pas un devis transactionnel
exact. `AIRoad.GetBuildCost(BT_ROAD)` est un prix-type : chaque commande
réelle peut coûter davantage ou moins selon les bits de route, le terrain,
les défrichements, le refit et le moteur. De plus, les raccords peuvent
être construits même lorsqu'ils paraissent connectés sur la carte avant
transaction. Il n'y a **pas** de simulation séquentielle `AITestMode` :
ce mode n'applique pas les mutations intermédiaires de la construction.

Dans `OpexBuildRoadRoute`, la même comptabilité `AIAccounting` historique
est lue aux quatre frontières de phase, après trace, arrêts, dépôt et
véhicules. Les différences consécutives attribuent le **débit effectif**
par phase sur les seuls succès. Les échecs et les réalisations avec flotte
incomplète sont recensés mais **exclus** de la mesure d'erreur comparable.
Une transaction abandonnée peut avoir des remboursements et actifs
conservés et ne constitue pas nécessairement une perte définitive.

Les logs `ROAD_COMPONENTS_P0` comportent date, OD, cargo, type de
chantier, plan driveThrough, arêtes/raccords, devis génération, devis
post-siting, devis composants, quatre devis et dépenses par poste,
nombre de véhicules voulus/construits, et comparabilité. Utiliser
`--script-debug` pour capturer les `AILog.Info`. L'extracteur
`sweeps/analyse_road_components_p0.py` calcule les agrégats et erreurs
absolues du modèle historique et du proxy seulement sur succès avec flotte
conforme, par type de service et de plan.

**Aucun effet décisionnel** : B0 n'affecte ni `candidate.capital`, ni
`budgetCapital`, `fundScore`, `capitalIsActual`, ni le facteur ROAD 121 %,
`ROAD_CAPITAL_MARGIN=1000 £`, `OpexCashReserve`, AIR C121, RAIL ou
scheduler. L'activation coûte néanmoins quelques opcodes, ce qui peut
changer le déroulé du scheduler ; tester son effet ON/OFF avant de
comparer des trajectoires.

## Portes et conditions de poursuite

1. Tests de contrat du réglage OFF, de la reconstruction par postes et du
   parseur ; smoke moteur apparié avec `road_quote_components_shadow_p0`
   seul différentiel. L'extraction doit retrouver les quatre dépenses
   dont la somme égale `actualCost` sur les succès comparables.
2. Diagnostiquer plusieurs réalisations valides : comparer l'erreur
   absolue des devis avant/après plan, et du proxy de composants ;
   examiner les résiduels par phase, la voirie existante, les raccords et
   la flotte réellement achetée. Une baisse moyenne du devis ne suffit
   pas à établir une amélioration.
3. **Pas encore de variante active.** Seulement si l'erreur baisse et
   qu'une fenêtre réelle de décisions de financement apparaît, créer
   une intervention B1 séparée (par exemple uniquement garde post-plan)
   qui conserve le financement historique à 121 % avant le choix du
   plan, sa marge et la réserve. Attention : une garde post-plan
   n'admettra pas un projet déjà rejeté au classement préalable.
4. V102 A40×3 de B1 uniquement après smoke et exposition réelle, puis
   B20×10 uniquement si la porte A passe. Aucun pourcentage opportuniste.

La variante C d'apprentissage des résiduels n'est pas implémentée ;
elle nécessite d'abord d'identifier des résiduels comparables et stables,
sans faire entrer les échecs non liquidés dans le modèle de succès.

## Qualification en moteur du 10 octobre 2026 — verdict B0

**Contrats techniques.** Le slot Squirrel
`ROAD_QUOTE_COMPONENTS_SHADOW_P0 <- false` existe dans `globals_pre.nut`
avant l'assignation par `OpexLoadSettings`. L'extracteur est exécutable
directement (`python sweeps/analyse_road_components_p0.py`) et n'agrège
comme comparables que les succès à flotte complète dont la somme des
quatre dépenses de phases égale `actualCost`. Le devis en composants ne
modifie aucune donnée lue par le classement, la garde de cash ou le
constructeur. Pas de simulation AITestMode insérée dans AIAccounting.

**Smoke** `p0_road_components_B0_smoke_20261010_r1` : une graine (42),
3 ans, 2/2 parties saines, `profit_year` et valeur strictement identiques
entre OFF et ON ; 1 chantier comparable côté sonde :
modèle post-plan 10 953 £, estimation composants 11 166 £,
coût réel 13 923 £. Décomposition coût réel : tracé 3 425 £,
arrêts 1 048 £, dépôt 592 £, véhicules 8 858 £.
Bundle `a3397f6e998d88e8fedb5b07c582c72d31b58a211baa05d3d28f07e56faa4c6c`.

**Diagnostic élargi** `p0_road_components_B0_diag10x5_20261010_r1` :
10 graines canoniques choisies avant exécution × 5 ans, 10/10 paires
et 20/20 parties saines, 10 CPU/10 workers, `--script-debug`, bundle
identique au smoke de base. Différence effective unique dans le
manifeste : `road_quote_components_shadow_p0=0/1`.
Sonde ON : 12 tentatives ROAD enregistrées, 9 succès avec flotte complète
et phases réconciliées, 3 échecs non utilisés comme pertes finales ;
8 des 10 graines comportent au moins une tentative instrumentée.

| Poste sur les 9 succès | Devis proxy | Dépense réelle | Résiduel réel − proxy |
|---|---:|---:|---:|
| Tracé | 19 596 £ | 84 196 £ | **+64 600 £** |
| Arrêts et raccords | 3 836 £ | 9 168 £ | +5 332 £ |
| Dépôt et raccord | 4 014 £ | 5 103 £ | +1 089 £ |
| Véhicules | 79 562 £ | 79 562 £ | 0 £ |
| **Total** | **107 008 £** | **178 029 £** | **+71 021 £** |

Le modèle historique post-plan totalisait 106 511 £ : son erreur absolue
moyenne est **7 946,44 £/chantier**, contre **7 891,22 £** pour le proxy,
une réduction de seulement **55,22 £/chantier**. Chacun des neuf chantiers
comparables coûte davantage que son estimation par composants. Le ratio
réel/proxy agrégé est **1,664**. Le désaccord se concentre sur la pose
du tracé, car `GetBuildCost(BT_ROAD) × arêtes manquantes` ne capture ni
les frais du terrain et de libération, ni le prix véritable des ajouts
de bits de route. Le nombre de 9 reste un échantillon modeste ; le constat
porte sur la précision de CE proxy, non sur une réserve à adopter.

La variante ON s'écarte économiquement de la référence sur 4/10 graines
malgré une sonde sans changement de décision direct : `profit_year`
variant−référence −3 719,6 £/an, médiane 0,
V/D/E=2/2/6, IC95 bootstrap [−61 056 ; +54 336] £/an,
Wilcoxon p=0,875 ; ratio des valeurs −0,186 %. C'est une **campagne
diagnostique**, pas une porte d'adoption. Le coût en opcodes peut déplacer
la cadence même si la logique économique reste identique. Le protocole
n'avait pas activé `probe_loop_ops` ni `probe_scheduler` : ne pas prétendre
mesurer le coût GLOBAL en opcodes ni attribuer les écarts économiques
au seul calcul.

**Mesure directe d'opcodes.** Un second smoke de vérification
`p0_road_components_B0_ops_smoke_20261010_r1` sur la graine 42,
3 ans, 2/2 parties saines, bundle
`c3a8045fdb12336d7992bb9ba9017a327c56a5eb2bf9fb78d8864a1e4f7ba263`
mesure `OpexOpsMeasureBegin/End` autour du helper, et donne **329 opcodes
pour l'appel effectivement instrumenté**. Cela n'inclut ni les relevés
`AIAccounting.GetCosts` supplémentaires, ni la création de la trace
`AILog.Info` ; impossible d'extrapoler à un coût annuel global sur un
seul appel. Le bénéfice économique ON−OFF sur cette graine était
−30 755 £/an, preuve d'un possible déphasage, pas d'une perte robuste.

**Verdict B0 : sonde valide pour localiser l'erreur, proxy NON ADMIS
comme devis actif.** Aucune variante B1 de financement n'est implémentée,
aucune porte A40×3 de B1, aucun apprentissage de coefficient, aucun
changement de réserves, de 121 % ROAD, d'AIR C121, de RAIL ou du
scheduler. Garder la sonde **OFF**. Si une future intervention est
nécessaire, viser une estimation réellement sensible au terrain des
commandes `BuildRoad` avec validation sur les coûts par phase et sans
simuler une suite de mutations inexistantes en AITestMode.
