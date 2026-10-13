# P3 — séparation du tampon AIR dans le score, 13 octobre 2026

## Objet et intervention

Base `c2a5be39043e64c754d9f659057dab3221e3e935`, worktree dédié
`results/scores_p3_stage_20261013`. Variante ON/OFF au seul flag
`score_air_buffer_separate`, défaut 0 aux quatre difficultés ;
`score_air_buffer_shadow=0` pour toute porte économique. `score_air_buffer_shadow=1`
réserve le contrefactuel de classement aux campagnes diagnostiques.

La sélection garde strictement le même `OpexProjectFinanceCapital`, la même
admission au budget, les priorités C77, le bénéfice, K_dec, les devis et les
constructeurs. Le dénominateur P3 retire uniquement `OpexAirRequiredMargin`
du devis *décisionnel* AIR, sans descendre sous `decisionConstructionCapital` ;
les immobilisations restent dans le score. Autres modes inchangés. Le cache
`lastScore` utilisé par la régénération du catalogue AIR conserve le score
historique, pour isoler les décisions du portefeuille.

## Pré-enregistrement de la qualification cinq ans

- Contrats statiques/fonctionnels P3 ; smoke 42×1 avec sonde P3 ON/OFF,
  même arbre et adversaire ; diagnostic 5 graines `[42,1,314,12345,8675309]`
  sur cinq ans pour établir l'exposition (non qualifiant).
- Porte économique **40 graines canoniques × 5 ans**, sans sélection opportuniste
  de graines ; un seul répétition ; 80 duels, 10 CPU/8g/10 workers sur PC.
  `--decision-rule gain_short --required-seeds 40 --required-years 5`,
  `--min-useful-primary-delta-pct 4`, valeur au moins 95 % du témoin,
  Wilcoxon exact bilatéral p<0,05 et borne basse bootstrap95 strictement positive.
- Métrique primaire : différence Opex ON−OFF du `profit_year` à la clôture
  de la cinquième année ; valeur d'entreprise terminale secondaire, V/D/E,
  médiane, IC95 bootstrap (20 000 rééchantillonnages graine 0) et santé 40/40.
  En complément les comptes de portefeuilles et opcodes peuvent être sondés
  séparément ; une sonde intrusive ne peut être fusionnée à la gate économique.
- Si la porte échoue, P3 est écarté de l'adoption. Un succès sur cinq ans serait
  une preuve de gain à cet horizon mais ne remplace pas, à lui seul, la
  qualification complète V102 40×3 puis 20×10 pour changer un défaut.
  Les combinaisons seront gelées en nouveau bundle et évaluées indépendamment,
  seulement si le mécanisme d'interaction est exposé.

P1/V165 demeure clos. Aucun changement par défaut, commit sur master ou push.

## Diagnostics initiaux distincts

`scores_p3_shadow_smoke42_1y_20261013` : préparation incomplète (adversaire
ignoré par Git et absent du stage), aucune simulation. `r2` : erreur Squirrel
dans la nouvelle sonde quand le premier vivier était vide (`rows` absent),
2/2 parties invalides ; corrigé avant `r3`. `r3` : deux parties saines,
206 sélections sans inversion de tête dans le témoin à un an.

`scores_p3_shadow_diag5x5_20261013` : diagnostics sur même bundle figé
`0b0daf301c80c7a4f86d821aebcd469db7d6180b494ecbde0b4321cd04341c18`,
10/10 jeux sains ; la sonde modifie le coût VM. La correction de `lastScore`
est intervenue **après** ce diagnostic ; il constitue une preuve d'exposition,
pas une gate de la variante finale. Voir
`results/scores_p3_shadow_diag5x5_20261013_analysis.json`.

La porte finale utilise un **nouveau bundle** après cette correction :
`scores_p3_gateA40x5_20261013`, avec la sonde désactivée dans les deux bras.

## Porte cinq ans complète — P3 non retenue

La campagne pré-enregistrée `scores_p3_gateA40x5_20261013` est terminée :
80/80 parties saines, 40/40 paires, `comparison_complete=true`,
`adoption_sample_complete=true`, `metric_coverage_complete=true`, quatre
trimestres terminaux couverts. Bundle figé
`f0711fb57620e9218a67e301d2a64064bc4c357de5c67d7364f327601415930a`,
image Docker `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
Référence `score_air_buffer_separate=0`, variante=1, sonde=0 des deux côtés,
40 graines canoniques, années 1970–1974, bootstrap 20 000 graine 0.

Métrique primaire `profit_year` terminal (Opex variante−référence) :
**moyenne −58 915,725 £/an**, **médiane −76 425 £/an**, **15V/25D/0E**,
Wilcoxon bilatéral exact **p=0,1386804**, bootstrap IC95
**[−128 221,6 ; +10 102,875] £/an**. Gain utile requis
**+86 163,094 £/an** (4 % de la référence). Valeur `company_value` ratio
des moyennes **0,990051**, soit **−0,994875 %**, garde −5 % tenue.
Verdict brut du harnais : **`fail_primary`**. L'IC recouvre zéro : ce n'est
pas une perte statistiquement démontrée, mais **aucun gain démontré**.

La sonde des mêmes portefeuilles révèle une faible exposition à l'inversion
de tête malgré des milliers de scores modifiés, essentiellement après 1971.
Un éventuel achat différent modifie les trajectoires futures et les compteurs
de catalogue ; un changement de rang n'est pas un gain économique. Aucune
campagne B20×10 ni combinaison P3 déclenchée, aucun changement de défaut,
aucun portage production. Résultat à conserver comme rejet de cette variante
isolée, sans le recycler pour choisir un coefficient ou une graine.

Le relevé terminal SIGNS `h5.observed-v1` donne en moyenne **82 376 176,5**
opcodes publiés par graine pour la référence et **83 411 526,72** sous P3,
soit **+1 035 350,22** en moyenne. Il est **incomplet** :
`observed_opcode_complete_cpu=false` et ne mesure pas les opcodes totaux
du VM. Malgré la baisse de profit, la variante a +1,30 panneaux de
constructions survivants, +1,25 véhicule primaire et +1,43 gare au terminal ;
un surcroît de volume ne démontre pas une meilleure allocation.

La suite d'ensemble du stage a exécuté 2 098 tests : quatre échecs/two erreurs
initialement. Deux erreurs requéraient les résultats AC04 externes, absents
du worktree (chemin `results/ac_fixes_worktree_20261011/...`), et deux
assertions historiquement figées ont été actualisées puis validées (B6 7 tests,
V126 31 tests). Il reste deux échecs non attribués de la suite globale ; la
branche commune de départ avait 2 093 tests verts et la variante P3 a passé
ses propres contrats. Comme P3 est rejetée économiquement, cette suite
globale ne vaut pas qualification pour son adoption.
