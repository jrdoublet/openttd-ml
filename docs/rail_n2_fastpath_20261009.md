# P0 RAIL — coût d'exposition N=2 et fast-path conservateur (09/10/2026)

## Problème, preuve et hypothèse

Le candidat N=2 à dominance intermodale (`rail_n2_opportunity_gate=1`) a échoué
au V102 40 graines × 3 ans r2 : −60 078 GBP/an et valeur −2,81 %, `fail_primary`.
Les 80 logs engine r2 sont vides (`decision_log=0`), donc impossible d'attribuer
les écarts à telle admission B au moment du jeu. En revanche, les snapshots
appariés montrent les premières divergences économiques/physiques dès 1970 :
25 graines divergent en 1970, 11 supplémentaires en 1971 et 3 en 1972 selon
la combinaison valeur/cash/flotte. **39/39** premières divergences ne présentent
pas d'écart de nombre de trains. Cela n'exclut pas des recherches A* ; cela
exclut une explication par de nouveaux trains physiquement présents à la
première divergence. Rapport reproductible :
`results/rail_n2_gate_first_divergence_40x3_20261009.json` et
`sweeps/analyse_rail_n2_first_divergence_20261009.py`.

Sur un **autre** diagnostic 3 graines × 5 ans sous logs, 8 secondaires B
démarrent mais aucune construction B n'est confirmée. Quatre recherches B
`OK` sont ensuite abandonnées après revalidation de la carte courante :
`quote_STNFAIL` deux fois, `quote_TRKFAIL` une fois, `too_close` une fois,
14 601 409 opcodes A* attribués aux quatre. Le devis est indispensable :
`OK` signifie chemin trouvé, pas infrastructure réalisable. Ne jamais retirer
le devis protecteur ni confondre ce diagnostic avec une preuve de causalité
sur les pertes du 40×3.

Hypothèse isolée : les appels N=2 à vide (rotation/parking/promotion même
sans secondaire) et les scans de garde alors que le premier projet est déjà
non-RAIL perturbent les opcodes/ticks et le calendrier AIR sans bénéfice.

## Changement expérimental, réglages OFF inchangés

- `scheduler.nut` : conserver la branche historique
  `if (RAIL_COOPERATIVE_N2)`, mais n'appeler rotation/parking que si
  `_railN2Secondary != null` ; le cas N=1 n'évalue aucune nouvelle expression.
- `task_projects.nut`, `task_rail.nut` : dans la même branche historique N2,
  sauter la promotion quand B absent. Ordre de construction A→B, rotations
  V89 et revalidation de B inchangés lorsqu'il existe.
- `_railN2Competitive` : si le projet de rang 0 est un non-RAIL connu
  (`air/fleet/road/water`), à profit strictement positif et capital payable,
  refuser immédiatement N=2. Preuve d'équivalence : `firstOtherRank=0`, or
  `beatsOther` requiert `firstOtherRank > primaryRank, candidateRank` avec les
  deux rangs >=0 ; la branche `railOnlyFull` est alors nécessairement fausse.
  Aucun candidat admissible dans l'ancien algorithme n'est ainsi rejeté.
  Aucune date, ratio ou coût arbitraire introduit.

**Important** : la garde reste volontairement limitée au TOP_K du portefeuille.
La branche historique `railOnlyFull` n'est pas une preuve d'absence d'AIR
hors TOP_K. Aucun changement de définition de dominance n'est inclus dans
cette expérience de coût, pour conserver une seule variable à la fois.

## Validations intermédiaires

Contrats hôte N2/B5/C121 35/35 et C80 18/18 : **53/53**.
Smoke Docker sur 1 an seed42 : référence/variante identiques (valeur
447 254 GBP, profit 528 157 GBP, 18 véhicules, 24 gares). Un an sans
secondaire observé n'est pas un test du bénéfice N2.

Premier diagnostic 5×3 avec garde sans branche N=1 strictement conservée
(`rail_n2_gate_fastpath_diag_5x3_20261009_r1`) : référence N=1 a elle-même
divergé des anciennes réalisations sur deux graines. **Échantillon invalidé
pour attribuer un effet au seul fast-path** ; corrigé par imbrication de la
condition `_railN2Secondary` *dans* le `if (RAIL_COOPERATIVE_N2)` d'origine.

Deux nouveaux diagnostics avec source figée identique, bundle SHA256
`6b0fa9269123349aab806f5a7fb00615f9af1842ac83de967bd54930ce3ec1c9` :

- `rail_n2_gate_fastpath_parity_2x3_20261009_r2`, graines 42/100 :
  référence strictement identique au r2, variante inchangée sur ces graines.
- `rail_n2_gate_fastpath_parity_3x3_20261009_r3`, graines 7/999/2026 :
  référence strictement identique au r2, variante modifiée sur graines 7
  (−63 869 GBP/an par rapport à ancienne gate), 2026 (+258 902 GBP/an),
  graine999 identique.

Sur les **5 graines regroupées** : nouveau N2−N1 en fin 1972 :
`[+13 121, −9 651, −185 838, +15 700, +223 153]` GBP/an pour
graines `[42,100,7,999,2026]`, moyenne **+11 297 GBP/an**, 3/2.
Ancienne garde sur ces mêmes graines : **−27 710 GBP/an** moyenne.
Ce sont des diagnostics de mécanisme et non la porte V102 : 5 paires n'ont
aucune puissance décisionnelle pour un gain de +4 %.

Comparaisons reproductibles :
`results/rail_n2_gate_fastpath_comparison_2x3_20261009.json` et
`results/rail_n2_gate_fastpath_comparison_3x3_20261009.json`, avec
`sweeps/analyse_rail_n2_fastpath_comparison_20261009.py`.

## Porte A

Campagne préenregistrée `rail_n2_gate_fastpath_gain_short_40x3_20261009_r4` :
40 graines canoniques × 3 ans, deux politiques OpexAI sur cartes identiques
contre AAAHogEx, profit_year, +4 % et Wilcoxon/IC95, garde valeur −5 %.
`decision_log=0`, shadow OFF, Docker 10 CPU/10 workers, 8 GiB.
**Aucun défaut activé, aucune porte B si A échoue.**

### Verdict final r4 : non adoption, correctif comportemental retire

Source du run figee : bundle SHA256
`6b0fa9269123349aab806f5a7fb00615f9af1842ac83de967bd54930ce3ec1c9` ;
manifest SHA256
`cc7649f42698fdd78e9d52f58d0019281c0524b78b85d4e6849ea4b999ba458f`.
Resultats : `results/rail_n2_gate_fastpath_gain_short_40x3_20261009_r4.json` ;
comparaison inter-bundles :
`results/rail_n2_gate_fastpath_comparison_40x3_20261009.json`.

- 80/80 parties saines, 40/40 paires completes, OpenTTD 15.3.
- Delta N2 fast-path − N1 en 1972 : **−29 757,725 GBP/an** en moyenne,
  médiane **−656 GBP/an**, victoires/défaites/égalités **17/21/2** ;
  Wilcoxon bilatéral **p=0,372752**, IC95 bootstrap
  **[−76 060,325 ; +14 069,45] GBP/an**.
- Ratio des valeurs de compagnie : **−1,547688 %**. Seuil V102 +4 %
  du profit moyen de reference = **79 678,905 GBP/an**, non atteint.
  Verdict officiel **`fail_primary`** ; porte B 20×10 NON executee.
- Ancienne N2 gate r2 : −60 078,425 GBP/an ; nouveau r4 : −29 757,725.
  Amelioration apparente de +30 320,700 GBP/an entre politiques dans leurs
  bancs respectifs, **mais ce n'est pas une estimation propre du seul fast-path**.
  Les sources IA figées differaient seulement dans
  `scheduler.nut`, `task_projects.nut`, `task_rail.nut`, mais les resultats
  N1 de r2 et r4 divergent sur **3/40 graines** (232037, 442018, 746035) :
  **37/40 références** identiques, pas 40/40. Les deltas de variantes
  peuvent donc contenir un effet de cadence/compiler non attribuable.
- First divergence nouveau r4 : 16 graines des 40 des 1970, 17 des 1971,
  5 en 1972 ; **38/38** premieres divergences observees sans difference
  de flotte RAIL. Rapport :
  `results/rail_n2_gate_fastpath_first_divergence_40x3_20261009.json`.

**Décision** : porte A echouee, pas d'adoption ; les edits comportementaux
de ce fast-path ont ete **annules par patches cibles**. Comparaison
`git diff --no-index` entre le bundle historique r2 et `ai/OpexAI` apres
retrait : **zero diff dans l'ensemble des sources IA OpexAI**.
Les fichiers de diagnostic, preuves et cette documentation sont conserves.
34/34 tests structurels N2/B5/C121 et 18/18 C80 verts apres retrait.
Les settings `rail_cooperative_n2` et `rail_n2_opportunity_gate` restent OFF.
**Aucun commit/push de code comportemental**, aucune modification des travaux
AIR/ROAD externes. La publication documentaire de l'essai est independante de
l'adoption du prototype N=2.

**Preuve versionnable** :
[`evidence/review/rail_n2_fastpath_40x3_20261009.json`](../evidence/review/rail_n2_fastpath_40x3_20261009.json)
contient les écarts par graine et les agrégats pour les deux portes A r2/r4.
Les fichiers moteur et checkpoints bruts restent locaux sous `results/`
(bundles figés et manifestes identifiés ci-dessus), car ils ne sont pas
inclus dans cette publication documentaire. Les scripts de comparaison exigent
ces JSONL bruts pour refaire intégralement les calculs.

Suite P0 : le ROI du second A* doit tenir compte de la fiabilite de la
construction et de son prix en opcodes/ticks, sur des projets concurrents
au meme instant. Une garde de rang ne suffit pas : les 4 B termines jetes
dans le diagnostic 3×5 ont deja couté 14,6 M opcodes sans chantier livre.
Ne pas lancer une nouvelle variante à seuil arbitraire ; investiguer un
contrefactuel pre-chantier et un modele de probabilité de pose observee.
