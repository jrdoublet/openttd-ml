# P2 — Calibration initiale et exposition du classement (13 octobre 2026)

Stage de travail **`results/scores_p2_stage_20261013`**, base exacte
`c2a5be3` (`codex/scores-p0-diagnostics-20261013`), sans politique de score
modifiée. Les quatre difficultés gardent leurs défauts courants. Aucun banc
Docker ni commit/push effectué dans ce stage.

## Ce que les archives établissent réellement

`docs/estime_realise_par_ligne_20261012.md` documente, sur des anciennes
campagnes comportant de la télémétrie, 44 AIR newpair (médiane réalisé/brut
0,446), 102 hubsite (0,512), 117 hubhub (0,423), 17 rail fret (1,850).
Ces échantillons sont des **lignes**, non des graines indépendantes. Les lignes
RAIL voyageurs n'ont aucun facteur spécifique qualifié ; les 17 fret sont trop
peu et peuvent différer par cargo, géométrie, millésime et flotte. Ce corpus
combine des arbres/bundles différents de `c2a5be3`, et les premières années
réelles ne sont pas toujours appariées à la même profondeur AIR du score.
La métrique de nouvelle ligne ne mesure pas la cannibalisation AIR prévue par
C121. `line.predicted` ne garantit pas que le projet ait été construit à la
profondeur effectivement classée ; les renforts changent la composition.
**Les ratios agrégés ne sont pas des coefficients `score_cold_prior`.**

Les nouvelles parties démarrent en 1970 ; `OpexC70C82AccumulateLine` exige
`year - line.year >= 2`. Une observation C70 mature n'est donc pas disponible
pour décider en 1970–1971, même si C121, V161 et R2 peuvent avoir une
**provenance économique propre**. `OpexC70Profit` et `OpexC82Profit` exemptent
les profits observés R2, la réalisation AIR C121 déjà non neutre et certains
renforts C121/V161. Tout prior éventuel doit garder ces exemptions et la
priorité C77, ainsi que le bonus AIR_EARLY_SLOT. Une multiplication uniforme
de l'aérien ne change pas l'ordre interne newpair/hubsite/hubhub.

Le `PORTFOLIO_RANK` disponible ne publie que cinq projets **après** le TopK,
omet la classe C77 et les coefficients/provenances. `B6_PORTFOLIO` décrit
une sélection agrégée, sans rejouer les alternatives de la même priorité.
Il est impossible d'affirmer aujourd'hui une inversion observée à priorité
égale ou un gain de profit à cinq ans. Le rapport d'estimation/réalisé du 12/10
évoque des inversions rail devant AIR mais les présente comme illustrations,
pas comme élections historiques effectivement inversées.

## Instrumentation minimale livrée

`score_cold_prior_shadow` (0 par défaut aux quatre difficultés) est une
**sonde pure** : lors des appels *réels* à `OpexProjectSelectAffordable`
en 1970–1971, elle émet `SCORE_COLD_P2_CAND` pour **chaque projet passé au
budget et au plancher**, juste après le score courant et avant la troncation
TopK. Elle inclut le rang d'arrivée dans la passe, mode/kind/arm/cargo/src/dst,
classe C77/V88, profit brut et calibré, provenance observée/C121/V161, capital
de financement, capital de décision, dénominateur `max(K_dec,K_decision)`,
besoin cash, score avec bonus AIR_EARLY_SLOT, revenu et date de la passe.
Une `SCORE_COLD_P2_HEAD` journalise le projet réellement retourné, le budget,
le plancher, la taille retenue et les cas de repli après plancher. Les passes
de sélection réitérées ne deviennent pas des achats, et l'instrumentation
ne change aucune décision. Un éventuel regroupement AIR par paire (`dedupe=1`)
est déclaré explicitement ; l'analyseur refuse alors de déduire des inversions.

`sweeps/analyse_score_cold_p2.py` lit ces logs par partie et passe, vérifie
qu'il ne manque aucune candidature et que son classement actuel reproduit
**exactement** la tête observée. Avec un JSON explicite de facteurs fournis
séparément, il rejoue seulement un changement de scores compatible C77,
sans modifier le jeu, et compte les inversions de tête à priorité égale.
Les projets déjà observés / réalisés sont exemptés. Une incohérence du
classement initial (identité du projet, moteur AIR, ligne FLEET, tier C77/V88
ou score) fait refuser la passe. L'analyse sépare les changements du même
service OD des **nouveaux services à priorité égale** ; un changement de
matériel sur la même paire n'est pas une extension territoriale, et le
classement d'un renfort flotte devant un rail existant est signalé comme
non recevable. Le rapport indique explicitement `build_confirmed=false` et
`calibrated_factors_verified=false` : un rejeu de scores ne prouve ni la
construction ultérieure ni un gain de `profit_year`.

La mesure annuelle préexistante `LINE_REVENUE` (`task_report.nut`, sous
`decision_log=1`) contient `line`, `year`, `age`, `mode`, `kind`, estimé et
réalisé, `vehs`. L'événement `C121_BUILD` contient déjà la famille et
profondeur AIR, `RAIL_BUILD` la composition des rames ; exploiter ces événements
sur **les mêmes logs et les mêmes sauvegardes** avant d'ajouter une sonde
annuelle supplémentaire. Ils sont indispensables à l'appariement avec les
choix/achats, et leur suffisance doit être auditée sur des parties finies.

## Campagne de développement proposée au pilote

Réserver les graines de développement `314159,271828,161803,123457,987653`
**en dehors** des quarante graines canoniques de `sweeps/bench_v2.py:46-61`.
Exécuter une seule campagne diagnostique figée d'au moins 5 ans avec
`OpexAI[score_cold_prior_shadow=1,decision_log=1]`, sans les mélanger aux
graines de validation. Conserver moteur, manifest/bundle, JSON/JSONL,
`--line-telemetry` et rapports annuels complets, puis parser, par graine et
ligne, `SCORE_COLD_P2_*`, `PROJECT_CHOSEN`, `C121_BUILD`, `RAIL_BUILD`,
`LINE_REVENUE`. Vérifier la profondeur réellement financée et les années
complètes à composition et modèle homogènes, suivi des ventes/crashes.

Prévoir un contrôle **OFF/ON sonde seule** à graine/bundle identiques et
véritables empreintes économiques, car logger plusieurs centaines de candidats
peut déplacer la cadence VM. Les facteurs devraient être estimés hors jeu,
sur les graines de développement, avec nombre de graines et incertitude par
famille ; une observation de projet est corrélée aux autres lignes de sa
partie. Aucune calibration pax/fret ou cargo à faible support. Réserver les
quarante graines A et vingt graines B de V102 pour l'évaluation économique
finale, sans les consulter pour choisir les coefficients.

Une fois les facteurs réellement décidés, implémenter `score_cold_prior=0`
en comportement OFF par défaut, vérifier R2/C121/V161 et le cache `lastScore`,
puis smoke et évaluation économique selon le protocole pré-enregistré par le
pilote : **horizon 5 ans, échantillon 40 graines**, sans sélectionner l'horizon
après résultats. Les exigences V102 d'une adoption par défaut et ses autres
portes restent distinctes de cette preuve demandée à cinq ans. La mesure
primaire restera le `profit_year` terminal Opex variant−référence et la garde
`company_value` ; l'amélioration d'un score n'est pas le verdict.

## Retour P2 après dépouillement des traces P3 5×5

**Verdict : P2 non implémentable comme variante de score économique sur les
données actuellement accessibles.** Une implémentation des facteurs
newpair/hubsite/hubhub/fret/pax aujourd'hui supposerait ce qu'elle doit
démontrer : des profits réalisés appariés et des inversions d'achats utiles
en 1970–1971. Aucune campagne économique 40×5 P2 n'est justifiée avant la
preuve. La sonde P2 ci-dessus reste l'instrument de vérification, à activer
seulement dans une campagne de développement distincte quand Docker est libre.

Vérification complémentaire **réelle, mais sur le levier P3 distinct** : cinq
logs `reference_seed{42,1,314,12345,8675309}_r0.log` sous
`results/scores_p3_stage_20261013/results/scores_p3_shadow_diag5x5_20261013_engine/`
contiennent les événements P3 suivants :

| Année | Passes de sélection | Projets éligibles | Scores P3 affectés | Inversions de tête P3 |
|---|---:|---:|---:|---:|
| 1970 | 1 036 | 4 204 | 4 181 | **0** |
| 1971 | 1 127 | 4 325 | 3 245 | **1** |
| 1972 | 227 | 22 551 | 3 323 | **9** |

Les 2 163 passes des deux premières années ne sont pas 2 163 expériences
indépendantes : seules cinq graines de carte ont été exécutées. Ce comptage
confirme le constat P3 du pilote, **il ne mesure aucune inversion P2**.
Les logs de ce corpus publient des `P3_CANDIDATE` seulement en cas de score
ou rang affecté, mais aucun `SCORE_COLD_P2_CAND`, `PORTFOLIO_RANK` ni
`LINE_REVENUE`. Il manque donc la contrepartie finançable de même tier et
l'année civile pleine appariée au même projet et à la même profondeur achetée.
On ne peut pas reconstruire le portefeuille P2 avec ces seules lignes.

Dans ces cinq logs, les 15 relevés `C121_REALIZATION phase=annual` de **1970**
et les 15 de **1971** ont chacun `lines=0`, `factor=1.0`, pour les familles
newpair/hubsite/hubhub. Les premières réalisations éligibles de ces journaux
apparaissent en **1972** (10 lignes cumulées sur les 15 relevés de familles).
Le calibrage C70, lui, n'admet les lignes qu'après `age>=2`. Il est donc
impossible de prétendre apprendre dans la partie des facteurs initialement
disponibles pour les décisions 1970–1971.

Pour poursuivre seulement si une campagne de développement complète devient
disponible : `SCORE_COLD_P2_CAND` et `_HEAD` avec `decision_log=1`, logs
`C121_BUILD`/`LINE_REVENUE`, identification du N AIR réellement acheté,
réalisé annualisé sur exercices complets, contrôle des flottes et des
externalités entre lignes. Étudier la validité hors graines/bundle et les
intervalles de calibration **avant** un rejeu des achats. Compter seulement
les inversions effectivement recevables à priorité C77/V88 identique et
financement identique, puis vérifier l'exécution et l'effet au profit terminal.
À défaut de ces éléments, garder le `score_cold_prior` comportemental absent.
