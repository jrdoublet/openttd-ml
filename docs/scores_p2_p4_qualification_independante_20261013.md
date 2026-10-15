# OpexAI — qualification économique P2/P4, vérification indépendante du 13 octobre 2026

## Décision

**Aucun gain robuste de `profit_year` terminal à cinq ans ne peut être intégré.**
Le dernier candidat sérieux, la **garde d'uplift AIR** de P4 véhicule-année,
présentait une hausse encourageante en développement, mais sa campagne
indépendante **40 graines × 5 ans est négative**. Ce résultat nouveau résout
la contradiction avec les rapports précédents déclarant qu'aucune variante
P4 ne justifiait la porte 40×5 : la porte **avait bien été ouverte puis
exécutée**, et son résultat n'avait pas été reporté dans le document initial.
Il ne faut ni ignorer l'échec ni répéter la campagne pour chercher cinq
graines favorables. Aucun défaut OpexAI n'est changé par cette étude.

## I. Garde AIR : provenance vérifiée, épreuve positive puis négative

Le stage **isolé** `results/scores_p4_guard_stage_20261013` vient de
`c2a5be3`. Son option `score_c70_vyear_air_uplift_guard` est `0` sur les
quatre difficultés. Avec P4 véhicule-année activé, elle prend le facteur
historique C70 AIR lorsque le facteur véhicule-année **le dépasse** ; elle
conserve les baisses du facteur véhicule-année. Aucun coefficient ajusté
aux résultats, aucune nouvelle condition de cash/C77/R2/C121/V161, aucun
changement de sidecar Save/Load.

Les deux campagnes ci-dessous comparent **P4-vyear + garde AIR** à
**C70 historique**. Sources brutes : fichiers `.json`, `.jsonl`,
`.manifest.json` et `_engine/` de chaque campagne dans
`results/scores_p4_guard_stage_20261013/results/`.

| Campagne | Bundle | N paires saines | Δ moyen `profit_year` | V/D/E | IC95 bootstrap | Wilcoxon bilatéral | Δ valeur (%) |
|---|---|---:|---:|---|---|---:|---:|
| Développement `scores_p4_guard_vs_history_dev5x5_20261013` | `10eb475c…` | 5/5 | **+68 191,8 £/an** | 5/0/0 | [+23 476,8 ; +122 707,8] | 0,0625 | +1,2475 % |
| Qualification `scores_p4_guard_gateA40x5_20261013` | **même `10eb475c…`** | **40/40** | **−52 352,375 £/an** | **14/25/1** | **[−96 109,525 ; −15 266,975]** | **0,008947** | **−1,603974 %** |

Le premier 5×5 avait déjà échoué au seuil préétabli de **+4 %** : gain
attendu au moins **+74 245,9 £/an** ; un test bilatéral sur cinq écarts
non nuls ne peut atteindre `p<0,05`. Ses cinq victoires et son IC positif
motivaient néanmoins **une validation indépendante**, pas une adoption.
Cette validation sur quarante graines **disjointes des cinq premières**
exigeait +84 627,198 £/an, IC95 basse positive, Wilcoxon `p<0,05` et
perte de `company_value` inférieure à 5 %. Le gain moyen est au contraire
**négatif**, et l'IC95 bootstrap entièrement négatif. `verdict=fail_primary`.
Le rapport physique terminal ajoute **−114 586,35 £** de valeur
d'entreprise moyenne, et les différences sommées sur les 40 paires
indiquent **−123 véhicules, −37 gares et −110 signes de construction**.
Le total des `observed_opcodes_total` a une différence de −144 604 269,
mais **ce sont des opcodes de signatures observées**, pas la totalité
de la consommation VM. Les chantiers instrumentés ne remplacent pas une
jointure fiable avec les retours constructeurs.

Le **5×5 direct garde vs véhicule-année sans garde**, encore sur le même
bundle, n'était pas qualifiant : +37 094,6 £/an, 3V/2D, IC95
[−53 542 ; +127 731], `fail_primary`. On ne peut additionner ou soustraire
les résultats de ces campagnes séparées comme si leurs trajectoires étaient
déterministes.

### Contrôle indépendant des résultats

Nouvel analyseur sans moteur :
`results/scores_p4_guard_stage_20261013/sweeps/verify_p4_guard_gate_20261013.py`.
Reçu JSON : `results/scores_p4_guard_stage_20261013/results/scores_p4_guard_gate_independent_receipt_20261013.json`.
Il **recalcule les 45 deltas terminaux depuis les relevés mensuels JSONL**
indépendamment des agrégats `policy_comparison`, contrôle **60 relevés
par graine et par politique** et **90 jeux/duels** au total :
**10 pour le 5×5 et 80 pour le 40×5**. Chaque jeu comporte OpexAI et
AAAHogEx sur carte partagée. Tous les jeux sont complets,
sans erreur moteur non attribuée. Il vérifie les SHA256 exacts des manifestes,
la même empreinte de bundle
`10eb475ccfdb87f4964a8560c37d7137c3cbbac0521314dcc53691fdcaafa999`,
les mêmes paramètres communs et les seules différences autorisées de
politique (`score_c70_vyear_cohort` et garde AIR). Aucune graine du 5×5
n'appartient au 40×5. **Deux tests hôte dédiés** contrôlent ce reçu.

La première divergence mensuelle d'argent, sur le 40×5, intervient en
1970 pour la graine **1**, en 1972 pour cinq graines, en 1973 pour 29 et
en 1974 pour cinq. La graine 1 diverge **février 1970**, avant la
première possibilité de correction du facteur annuel P4 en 1972 : ce
cas ne peut être attribué aux nouveaux facteurs C70. Les A/A antérieurs
avaient eux aussi bifurqué avant janvier 1972 sur la graine 314159.
En excluant seulement pour diagnostic la graine 1 (−643 274 £/an),
le delta moyen des **39 autres** reste **−37 200,54 £/an** (14V/24D/1E) :
la régression globale n'est pas uniquement ce cas extrême. Ce retrait
post-hoc **ne constitue pas une nouvelle porte ni un nouveau verdict**.

## II. Chaîne C70 → C77 → choix → construction → profit : état de preuve

La sonde `results/scores_p4_vyear_flip_stage_20261013` rejoue **au même
instant et sur le même vivier finançable et même priorité C77/V88** les
facteurs C70 historique et véhicule-année. Son bundle `a21a67dd…` est
**distinct** de celui des campagnes économiques précédentes. Elle a
identifié **40 flips de tête à priorité identique, 0 discordance de rejeu**,
dont **21 RAIL→AIR et 14 AIR→RAIL**. Les **33 marques ATTEMPT** sont
émises avant certains vetos opérationnels, donc **ne prouvent pas toutes
un appel constructeur**. Les rapprochements par OD/temps associent
**17 épisodes de choix à une construction** sur 17 lignes distinctes,
sans ID causal commun à toutes les étapes. Huit lignes atteignent l'âge
deux ans : profit de ligne observé **286 645 £** contre **515 191 £**
prévus, toutes huit sous la prévision ; ces huit survivantes ne mesurent
ni les alternatives non construites ni le profit **net réseau**.

Une hausse du facteur n'entraîne pas forcément un flip : le tri examine
d'abord les **priorités** puis les scores, parfois amortis par `K_dec` et
exemptés par C121/R2/V161 ; un facteur de mode commun conserve l'ordre
intra-mode, et le cash élimine les projets non finançables **avant** le
classement. Un flip admissible peut ensuite rencontrer un veto,
un pathfinding RAIL différé, ou n'avoir aucun effet économique marginal
positif du fait des hubs et trafics voisins. Cette chaîne est donc
**causale jusqu'au choix C77 au même état**, partiellement corrélée aux
chantiers, mais **pas attribuée** au profit terminal de compagnie.

L'A/A de référence de la graine 314159 sur le même bundle avait déjà
montré une première divergence d'ordonnancement AAAHogEx en août 1971,
avant toute nouvelle application C70 ; on ne peut pas attribuer la
différence économique anticipée au score. La campagne same-world
elle-même active une instrumentation plus coûteuse et ne remplace pas
les essais propres. Les nouveaux résultats 40×5 valident un **effet
économique agrégé négatif associé à la politique** dans cette épreuve,
pas un profit marginal exact imputable à chacun des flips.

## III. Autres hypothèses P4 déjà testées, sans nouvelle campagne

| Politique | Épreuve existante | Δ `profit_year` terminal | Constat |
|---|---|---:|---|
| P4 stable cohort | 40×5 | −43 730 £/an | Rejet acquis |
| P4 véhicule-année non gardé | 5×5 propre / matched-shadow | +19 040 / −19 231 £/an | IC recouvrant zéro ; instrumentation/cadence confondantes |
| P4 nouveaux AIR, C70 historique (`fresh_air`) | 5×5 initial | +85 523 £/an | 4V/1D, IC [−115 159 ; +244 816] ; bifurcations monétaires dès 1970 **avant** le facteur, hot path de score différent |
| `fresh_equal` : même hot path de score dans les deux bras | 5×5 strict | **−24 050,2 £/an** | 3V/2D, IC [−131 972 ; +83 872], `fail_primary` ; aucune preuve de gain |
| P4 inclusion des entrants par jours-véhicules (`partial`) | 5×5 matched-shadow | +475,6 £/an | 2V/2D/1E, IC [−81 415 ; +71 533], `fail_primary` |
| P4 garde uplift AIR | 5×5 puis 40×5 | **−52 352,375 £/an** en indépendant | Rejet économique avec 40 paires |

**Pourquoi ces corrections ont été testables :** 74/311 observations
AIR acceptées par le calcul véhicule-année initial sont sur des flottes
augmentées ; le profit des entrants est exclu, pas leurs externalités.
Le stage `partial` a tenté une normalisation par durée de présence réelle,
sans multiplier arbitrairement les entrants. Le stage `fresh_air` répondait
à une autre exposition : sur 76 nouvelles lignes AIR survivantes de cinq
graines, erreur absolue pondérée **0,194** pour C70 historique et
**0,249** pour véhicule-année, mais ce sont des profits de ligne et pas
des rendements marginaux de portefeuille. Le correctif `fresh_equal`
contrôle les opcodes du calcul de score et annule son prétendu signal
positif. Le stage `guard` a essayé de borner les relèvements AIR sans
coefficient inventé ; sa qualification a finalement échoué.

Les profits des avions vendus/crashés avant le relevé, les modifications
intra-annuelles aller-retour, les lignes supprimées et les effets réseau
des hubs sont **manquants et non identifiés** ; imputer leur profit ou
pondérer les seuls survivants exigerait des hypothèses non démontrées.
Un Save→Load réel de la version 2 véhicule-année avait déjà été validé
à **80 lignes**. La garde AIR ne change ni le format ni le sidecar ; pas
de motif de rejouer ce roundtrip ou les **2 127 tests** historiques.
Le stage garde dispose en outre d'une suite globale antérieure de
**2 132 tests** verts, conservée en archives.

## IV. P2 : cohorte, censure et exposition

Le bundle P2 initial `e9f750…` contient 281 constructions AIR, dont
102 au plus tard en 1971, toutes suivies d'un `LINE_REVENUE` à âge deux.
Les **57 lignes-années initiales** se dédupliquent à **43 lignes
indépendantes strictement appariées** (6 newpair / 28 hubsite / 9 hubhub).
La censure est très différentielle : seuls **6/38 newpair**, **28/54
hubsite** et **9/10 hubhub** sont admissibles strictement. Sur 59 exclusions,
19 n'ont pas de HEAD P2 explicitement associé et 40 sont connues pour
des mutations de flotte. Parmi les 19, **12** ont une candidate proche
mais pas de preuve qu'elle était le HEAD de la décision : le panel
descriptif peut être porté à **55**, pas le panel causal des choix.
IC95 bootstrap par grappes newpair/hubsite des panels 43 et 55 :
**[0,5815 ; 1,4690]** et **[0,5815 ; 1,6355]**. Sur les 102 lignes,
un proxy non causal donne un ratio **0,9866**, IC95 **[0,7294 ; 1,3276]**.
Le sens apparent dépend du critère de sélection et du dénominateur.
Les **trois inversions admissibles P2 LOSO** sur 202 sélections n'ont
aucune construction de l'alternative dans le témoin. Ni prior froid P2,
ni interaction P2/P4 ne peuvent être estimés sans coefficient ou effet
de réseau inventé ; les bundles P2 et P4 diffèrent et il n'existe pas
de vrai 2×2 comportemental apparié sur le même bundle.

## V. Fin de cycle expérimental et limites

Les **candidats comportementaux nouveaux déjà implémentés** (garde AIR,
`fresh_air`/`fresh_equal`, `partial`) ont été testés et échoué à leur
porte économique. La garde a été qualifiée sur 40 graines indépendantes :
**aucune relance supplémentaire n'est justifiée**. Les hypothèses encore
conceptuellement possibles (cohorte de nouvelles lignes, pertes des
sortants, profit marginal des hubs, contrefactuel RAIL différé) exigent
des observations nouvelles *avant* de définir une variante sans
coefficient arbitraire ; les archives présentes ne permettent pas de
conclure à leur rentabilité. **Échec des politiques testées ≠ preuve
d'impossibilité de toute amélioration future.**

Le checkout principal `7ecbabe` inclut V166 et le retrait C116,
postérieurs aux bases expérimentales `c2a5be3`/`068e342` ; les preuves
de stage ne sont pas des preuves sur un binaire V166 porté. En l'absence
de gagnant, **aucun portage, aucun changement des flags OFF, aucun commit,
push, merge ou modification de `master` / `origin/master`**.
Le programme P0 de progression économique AIR/RAIL demeure distinct.
