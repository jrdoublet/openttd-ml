# P4 — variante d'essai C70 sur cohortes candidates, 13 octobre 2026

## Référence et mécanisme

Worktree indépendant `results/scores_p4_behavior_stage_20261013` issu de
`codex/scores-p0-diagnostics-20261013@c2a5be3`, avec la même sonde P4 que
`results/scores_p4_stage_20261013`, source de base identique.
La variation comportementale unique est `score_c70_stable_cohort=0→1`,
défaut 0 aux quatre difficultés. Le flag de journalisation
`score_c70_cohort_probe=0` reste identique aux deux bras économiques.

Sous ON, la cohorte candidate de `OpexC70P4ObserveLine` est intégrée aux
cumuls du mode C70 ; elle exige âge>=2, ID de flotte identiques aux relevés,
véhicules assez anciens et aucun événement de mutation connu sur l'exercice.
Le flag ON active aussi `SCORE_C70_COHORT_PROBE=LOG||STABLE` et donc
des hooks d'observation/mutation et leur coût VM même quand le facteur
ne peut pas encore être alimenté. La **seule modification directe de score**
est le facteur C70, mais l'effet économique du CODE ON comprend ces
surcoûts et éventuels déplacements d'ordonnancement.
La pseudo-ligne C70 de poids 1 subsiste, tout comme le facteur précédent
quand aucun nouvel exercice admissible ne change le cumul. Le mode OFF,
le financement, le plancher de profit, les scores des renforts observés R2,
les réalisations AIR C121, V161 et C82 (défaut OFF) restent inchangés.
Le facteur est reconstruit après Load à partir des mêmes cumuls de ligne.

**Limite de recevabilité critique** : « candidate stable » ne garantit pas
que la flotte n'a subi aucune mutation intra-annuelle cachée. Un véhicule
acheté puis vendu avant le bilan peut biaiser la réalisation sans laisser de
différence dans les IDs survivants. Un résultat favorable au banc reste donc
exploratoire tant que le registre de transactions de tous les modes n'a pas
été prouvé exhaustif. Pas d'adoption sur seule hausse du score ou d'un facteur.

## Protocole gelé avant moteur

Contrats et tests de Save/Load ciblés, smoke C66 graine 314159×3 ans
avec `score_c70_cohort_probe=1` des deux côtés pour vérifier la compilation,
les facteurs et l'exposition ; puis benchmark économique strict sur
**40 graines canoniques × 5 ans**, deux duels séparés par graine, une seule
répétition, Opex référence versus Opex variante face au même AAAHogEx figé.
`--decision-rule gain_short --min-useful-primary-delta-pct 4
--required-seeds 40 --required-years 5 --primary-metric profit_year
--value-guard-max-loss-pct 5 --cpus 10 --memory 8g --max-workers 10`,
pas de `--script-debug` ni de probe P4 aux deux bras économiques.

Verdict 5 ans : comparaison terminale `profit_year` Opex ON−OFF,
40/40 paires saines et couverture 4 trimestres, moyenne relative >=4 %,
Wilcoxon exact bilatéral p<0,05 et borne basse bootstrap95 >0 ;
garde `company_value` ratio des moyennes >=0,95. Graine bootstrap 0,
20 000 rééchantillonnages. Le coût opcode fait partie des différences
intrinsèques de la variante ; compteurs détaillés à sonde dédiée si exposée.

Un résultat `fail_primary` stoppe le candidat. Même une éventuelle porte
cinq ans `pass` ne qualifie **ni** Save/Load sans roundtrip **ni** le défaut :
la porte V102 séparée 40×3 puis B20×10 et le contrôle d'exhaustivité des
mutations restent requis. P1/V165 clos. Aucun commit sur master/push.

## Résultat final : porte A40×5 rejetée

Campagne `scores_p4_stable_gateA40x5_20261013`, même bundle
`a6fd1a93c3230c3000462646368c476aa764b7ebc58529efe68e98f6ec3c5531`
dans les deux bras, image Docker
`sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
Sonde de logs P4 désactivée des deux côtés ; 40 graines canoniques, 80/80
parties saines, `comparison_complete`, `adoption_sample_complete` et
`metric_coverage_complete` tous vrais. Sorties :
`results/scores_p4_stable_gateA40x5_20261013.json`, `.manifest.json`, `.jsonl`.

- `profit_year` terminal ON−OFF : **moyenne −43 730,3 £/an**
  (**−2,0633 %** de la moyenne de référence), médiane **−24 164,5 £/an**,
  **18 victoires / 21 défaites / 1 égalité** ; Wilcoxon bilatéral exact
  `p=0,2585682743`, bootstrap 20 000 graine 0
  **IC95 [−100 828,35 ; +7 772,25] £/an** ; seuil utile positif
  **+84 776,777 £/an**. Verdict du harnais **`fail_primary`**.
- `company_value` terminal : écart moyen **−97 540,4 £** ; ratio des
  moyennes **0,986385**, soit **−1,361491 %** ; garde de valeur tenue,
  mais aucun gain primaire démontré.
- Contexte duel figé : référence OpexAI **2,119 M£/an** contre
  AAAHogEx **3,200 M£/an**, écart moyen **−1,080 M£/an** ;
  sous le bras variante, écart OpexAI−AAAHogEx moyen
  **−1,132 M£/an**. Ce n'est pas la métrique primaire de politique.
- Effet par année, moyenne des 40 deltas `profit_year` ON−OFF :
  1970 **−2 084,85**, 1971 **−4 279,675**, 1972 **−14 033,1**,
  1973 **−35 633,6**, 1974 **−43 730,3 £/an**.
  En 1970 et 1971, **39/40 graines sont à delta zéro** ; la seule
  divergence précoce est la graine **1** (première différence de trésorerie
  mensuelle dès **février 1970** ; profit annuel 1970 **−83 394**,
  1971 **−171 187**), bien avant une cohorte mature C70 pouvant être
  exploitée, ce qui interdit de l'attribuer directement au seul facteur C70.
  À partir de 1972, les trajectoires divergent davantage.
- Physique terminale : variante **−1,125 véhicule primaire** et
  **−1,075 gare** en moyenne, **−0,525 avion primaire** et
  **+0,1 aéroport**. Ce sont des conséquences observées, pas des inversions
  de classement démontrées.
- Panneaux d'opcodes **observés seulement**, reconstruction des SIGNS
  `IG|`, `OB|A`, `RB|`, `OA|`, `OM|W` : en décembre 1974,
  **84 116 029** observés par graine référence vs **84 881 183** ON,
  soit **+765 154 en moyenne** (+0,91 %), médiane des deltas
  **−145 691**. Le champ `observed_opcode_complete_cpu=false` pour cette
  télémétrie : **ne pas lire ces valeurs comme des opcodes VM totaux**.
- Panneaux `project_builds_sign_by_year` **survivants** au relevé terminal :
  variation de comptes ON−OFF moyenne **−1,975 en 1973** puis
  **+1,25 en 1974**. Sur les 28 graines ayant moins de panneaux de
  constructions 1973 sous ON, le delta de profit terminal moyen est
  **−57 207 £/an** ; 10 graines en ont davantage (−26 260 £/an) et
  deux sont à égalité (+57 586 £/an). Cela suggère un éventuel déplacement
  de constructions de 1973 vers 1974, **mais** un panneau survivant ne
  garantit ni exhaustivité des chantiers ni attribution causale à une
  inversion du score : nécessité d'une sonde de décisions.

La porte A stoppe P4 : ni V102, ni B20×10, ni combinaison économique
justifiée par cette variante. L'audit statique complémentaire rappelle
qu'un `candidate=1` est nécessaire mais non suffisant pour établir une
flotte stable pendant l'exercice. La projection Save mensuelle de >64 lignes
peut être obsolète après le rapport annuel et les flottants sauvegardés sont
arrondis, ce qui empêche de qualifier la continuité de facteur P4 après
Save/Load. Les mutations transitoires de flotte restent non exhaustives.
Ces défauts auraient interdit l'adoption **même si** la porte avait été
favorable. La variante reste isolée, défaut OFF, non intégrée.
