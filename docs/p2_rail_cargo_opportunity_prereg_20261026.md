# P2 — rail cargo opportunity rank : pré-enregistrement

**26 octobre 2026, avant toute exposition de P2.** Base `82027ac1`, branche
isolée `p2_rail_cargo_opportunity_20261026`. L'objectif stratégique reste
**75 % des profits annuels d'AAAHogEx** sur les 20 mêmes mondes à dix ans ;
ce chiffre n'est ni une statistique acquise ni un substitut aux portes A/B.

## Hypothèse comportementale et périmètre

Le candidat P2 teste si l'ordre financier du portefeuille pénalise parfois
une ligne RAIL **fret construisible immédiatement** face à une ligne PASS/MAIL
ou AIR concurrente pourtant de rendement annuel et de score marginal proches.
Il ne fabrique **aucun nouveau cargo ni nouveau projet**. Le refresh N75
`n75_multi_cargo=2` demeure inchangé : le vivier peut n'avoir qu'un cargo fret
à la fois. Ne jamais assimiler deux lignes PASS/MAIL à un conflit fret/fret.
La tâche de renouvellement V252 opère hors sélection de projets : conserver
ses réserves, sa cadence et son ordre, et ne pas déclarer la comparaison
« V252 contre fret » sans un devis V252 simultané et réellement disponible.

Réglage `rail_cargo_opportunity_rank` **0 OFF** par défaut aux **quatre
difficultés**, `1 SHADOW` passif, `2 ON` borné. Les modes OFF/SHADOW ne changent
aucun classement, `fundScore`, dépense, site, sélection C77, cache ou plan.
L'instrumentation SHADOW se contente de lire le petit classement déjà produit
par `OpexProjectSelectAffordable` / `OpexReselectProjects` ; aucun A*, aucune
recherche de site, aucun nouveau cargo, nouvelle voie ou appel C121.

ON examine uniquement le **top-K déjà financé**, jamais des candidats éliminés
du vivier. Un projet RAIL fret est qualifié seulement si son plan physique
`payload.railPlan` est présent et `ok`, le cargo n'est ni voyageurs ni courrier,
`profitAnnual > 0`, le devis est positif, non abandonné et inférieur au
`capitalBudget` **après réserves**. Le concurrent doit lui aussi être financé,
de profit annuel positif, et être un projet RAIL PASS/MAIL préparé ou un AIR
disposant de son devis économique actuel ; jamais une flotte, ROAD ou un
renouvellement V252. Les deux appartiennent à la **même classe défensive
C77** et ne présentent pas d'ambiguïté de provenance. Si preuve manquante,
mode ON revient au classement historique sans substitution.

L'ajustement ON, fixé avant banc, est **au plus +8 %** sur le **score de rang**
du meilleur RAIL fret admissible, sans modifier profit, CAPEX, `fundScore`
comptable, C121, `K_dec` ou la classe défensive C77. Il s'active seulement
si, à score historique, ce fret se place immédiatement sous un rival,
son `fundScore` atteint **au moins 93 %** de celui du rival et son
`profitAnnual` atteint **au moins 80 %** de celui du rival. À chaque
sélection, **une substitution maximum** et classement stable des ex æquo.
Cette borne constitue une hypothèse et peut être insuffisante ; ne pas la
recalibrer à partir des cinq graines de qualification.

Pour préserver la cadence, ne conserver aucun cooldown ou classement persistant
au Load. Mesurer coût de diagnostic et re-classement en `OpexOpsMeasureBegin/End`
et refuser ON si le supplément de la sélection est supérieur à **50 000
opcodes**. Les états locaux sont transitoires ; Save/Load court et complet
doivent reconstituer une sélection sans doublon. L'instrumentation relie
événement `P2_OPPORTUNITY`, rangs/scoring/cargos/devis/tiers, projet
`PROJECT_CHOSEN`, tentative et `RAIL_BUILD` par une clé de projet stable
(mode, cargo, extrémités, devis), sans confondre réévaluations de top-K et
constructions différentes.

## Conditions de validation avant bancs

1. Tests de neutralité OFF (ordre / score / C77 / V252 / N75), pureté shadow,
   corps PO01C et contrats de SHA historiques, droits de deuxième gare, fret
   au plan non prêt, devis nul/obsolète, budget, égalités et C78. Suite hôte
   complète sans nouvel échec, `git diff --check`, smoke moteur OFF vs ON 1×1,
   Save/Load moteur court et complet. Les quatre profils restent au défaut 0.
2. Exposition appariée sur graines **42, 100, 7, 999, 2026**, années
   **1970–1974**, même image et mêmes réglages Opex/AAAHogEx, OFF et SHADOW,
   puis pilote ON seulement si le SHADOW montre un conflit réel. Journaliser
   le nombre de sélections, candidatures RAIL fret avec `railPlan.ok`,
   concurrents finançables même tier, score/marge/CAPEX, propositions de
   substitution uniques par graine, coût en opcodes, acceptation finale et
   trajet effectivement bâti. Conflit sur des jours répétés = **un seul
   événement causal**, pas une nouvelle route.
3. **GO** vers la porte A uniquement si **≥3 des cinq graines** exposent
   chacune un conflit entre projets effectivement finançables, si un pilote
   ON 5×5 observe **≥3 chantiers RAIL réellement substitués** au total, avec
   correspondance décision→tentative→construction, et si le plafond d'opcodes,
   les gardes V252/C77 et le chemin OFF sont respectés. Sinon **NO-GO**, aucun
   A/B, laisser défaut 0, pas de retouche post-hoc à 8 % / 93 % / 80 %.
4. Après GO seulement : **A multimodale 40 graines × 5 ans** `gain_short`
   pré-enregistrée, delta moyen `profit_year` ON−OFF **≥4 %** du témoin,
   Wilcoxon bilatéral **p<0,05**, borne basse IC95 bootstrap **>0**, ratio des
   moyennes `company_value` variante/référence **≥0,95**, 40/40 paires
   complètes et saines. **B 20 graines × 10 ans** en `non_erosion` seulement
   si A passe ; suivi des profits Opex/AAAHogEx (rapport des moyennes et
   médiane des ratios appariés) avec les mêmes vingt graines. Même si A/B
   passent, garder le réglage à 0 jusqu'à décision explicite d'adoption.

Les verdicts historiques P1/RAIL-ROI/V294c/V297 et P3/P6/FRONT-PAX-2
restent inchangés. Un défaut d'exposition est un résultat, pas une raison
de multiplier les bancs ou de créer des candidats artificiels.
