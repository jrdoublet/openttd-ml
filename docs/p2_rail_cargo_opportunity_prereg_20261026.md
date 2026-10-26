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

## Implémentation et validation mécanique (26 octobre 2026)

- Pré-enregistrement committé **avant banc** : `35b5a67b`; code opt-in
  `ddb9afa0`, fusion `eab91e07` sur `origin/master`. Un correctif ultérieur
  `f6455c4b` supprime les journaux des sélections `action=none` sans modifier
  le seuil économique, la condition d'éligibilité ou le défaut du réglage.
- `0` OFF (défaut sur quatre difficultés), `1` SHADOW sans permutation, `2` ON
  avec au plus une permutation adjacente d'un fret préparé. C77, `fundScore`,
  `K_dec`, N75, V252 et les recherches A* ne sont pas modifiés. Le score
  +8 % est un test de rang, jamais une réécriture du rendement économique.
- Suite complète `python -X utf8 -m unittest discover -s sweeps -p 'test_*.py'` :
  **2 895 tests OK** (6 skipped, 2 expected failures), `git diff --check`
  conforme ; huit contrats P2 ajoutés. Le test Python ne compile pas Squirrel.
- Smoke moteur `p2_cargo_smoke_42x1_20261026_r2` : graine 42, un an,
  OFF `0` contre ON `2`, **1/1 paire saine**, zéro `failed_runs`,
  `comparison_complete=true`, `metric_coverage_complete=true`, verdict
  `diagnostic_only`. Écart ON−OFF −48 588 £/an sur **une seule graine** :
  aucune portée économique statistique. Bundle gelé
  `68eb8fda36c3dcefe1a67b6142458bf93ea880ce56027cf474290a2edac80f1a`.
- Save/Load moteur du mode ON, graine 42 :
  `results/p2_cargo_saveload_short_42_20261026.json` et
  `results/p2_cargo_saveload_full_42_20261026.json`. Pour chacun,
  `save_full_state=0` ou `1`, **13 sauvegardes phase A + 13 phase B**,
  rechargement du `000000005.sav` (01/07/1970), `LOAD_RECONCILE` positif,
  aucun échec script. Le harnais engendre une compagnie fantôme connue :
  ces essais prouvent la reprise technique, non l'identité des trajectoires.

## Exposition shadow appariée et verdict (26 octobre 2026)

Campagne `p2_cargo_shadow_5x5_20261026_r1` : **cinq graines**
`42,100,7,999,2026`, années 1970–1974, OFF `0` contre SHADOW `1`,
**10 parties / 5 paires complètes et saines**, aucun `failed_runs` ; les champs
`comparison_complete` et `metric_coverage_complete` valent `true`. Bundle
`68eb8fda36c3dcefe1a67b6142458bf93ea880ce56027cf474290a2edac80f1a` ;
manifeste SHA256 **vérifié** :
`0cfd31a10a451feded29610f6bce892dc08d00a31298bf55d894c0c345a78fb7`.

Comptage direct des cinq journaux moteur **shadow** réellement joués :

| Graine | `P2_OPPORTUNITY action=shadow` (conflit admissible) | `action=none` (sélections répétées) |
|---|---:|---:|
| 42 | 0 | 633 |
| 100 | 0 | 924 |
| 7 | 0 | 644 |
| 999 | 0 | 672 |
| 2026 | 0 | 798 |
| **Total** | **0** | **3 671** |

**Zéro des cinq graines** manifeste un conflit fret/RAIL PASS ou AIR
simultanément préparé, finançable, de même tiers C77, avec marge/rang
respectant 8 %/93 %/80 %. Les 3 671 journaux `none` étaient seulement des
réévaluations, **pas** des projets construits. Les chantiers réellement
substitués démontrés sont donc également **zéro**. La condition pré-enregistrée
exigeait des conflits sur **au moins trois graines**, puis trois chantiers
substitués en pilote ON : la première condition échoue sans ambiguïté.

À titre **strictement descriptif**, shadow−OFF : delta annuel moyen
`profit_year` **+50 355,2 £/an**, médiane **+42 219**, 3V/2D/0E,
Wilcoxon bilatéral **p=0,625**, IC95 bootstrap **[−87 198,6 ; +192 910,2]**,
ratio de valeur **1,018098**. Une fluctuation entre deux bras à instrumentation
différente ne prouve pas d'effet causal de l'arbitrage, qui n'a jamais proposé
de conflit dans ce banc. Ces cinq ans ne remplacent pas la cible 20×10
face à AAAHogEx.

**VERDICT : `NO-GO` d'exposition**. Aucun pilote ON 5×5, aucune porte A 40×5
ou B 20×10, aucun changement de défaut ni adoption. Ne pas réviser après
observation la borne +8 %, les ratios 93 %/80 %, les filtres de constructibilité
ou les exigences de provenance. Le correctif ultérieur des journaux vides
reste un changement d'observabilité, sans nouvelle preuve économique ; les
résultats ci-dessus restent explicitement ceux du bundle gelé `ddb9afa0`.
P1/P4/P5 pourront être étudiées selon leur propre protocole et sans prétendre
que ce premier arbitrage P2 a déplacé une construction.

## Contre-vérification après suppression des journaux vides (26 octobre 2026)

Sur le code **`f6455c4b` propre**, le smoke OFF/ON
`p2_opportunity_smoke_42x1_20261026_r2` est terminé sans erreur moteur sur
la graine 42. L'écart ON−OFF **−15 633 £/an** et la valeur relative
**0,964978** sur cette unique graine restent purement diagnostiques : aucune
promotion P2 ne s'est produite. Le correctif a supprimé les 184 journaux
`action=none` observés au premier smoke. Les Save/Load ON court et complet
ont ensuite confirmé `LOAD_RECONCILE` après rechargement réel, avec 13+13
sauvegardes chacun ; la compagnie fantôme connue du harnais est signalée.

L'exposition indépendante **`p2_opportunity_shadow_5x5_20261026_r2`** fige
les mêmes graines `42,100,7,999,2026`, de 1970 à 1974, sur le code corrigé :
**10/10 parties terminées, 5/5 paires saines**, sans `P2_OPPORTUNITY
action=shadow`, `action=promote`, `action=ops_reject` ni `action=none` sur
les cinq journaux shadow. Le manifeste SHA256 est
`ef9f7044dbebc876fe4643c81abcb4c661314e18d6324b89ad658146ff782127`
et l'image Docker
`sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
Le code a passé **2 895 tests** complets après correction (5 ignorés et
2 échecs attendus) et `git diff --check`.

Delta shadow−OFF strictement descriptif : **+134 075,2 £/an**,
médiane **+196 236 £/an**, 4V/1D, Wilcoxon **p=0,4375**,
IC95 bootstrap **[−127 665,4 ; +340 923,6]**, ratio des moyennes
`company_value` **1,033616**. Aucune proposition n'ayant été observée, ces
différences de trajectoire ne sont **pas un effet du levier**. La nouvelle
campagne n'efface ni le bundle `ddb9afa0` ni ses 3 671 journaux historiques.
**Verdict `NO-GO` confirmé à 0/5 graines exposées** (seuil 3/5) : aucun
pilote ON, aucune porte A/B, aucune adoption, défaut 0 inchangé.
