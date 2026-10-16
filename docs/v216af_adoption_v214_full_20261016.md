# Adoption V216a/V216f et porte A V214 en partie complète — 16 octobre 2026

## Décision d'adoption V216a + V216f

Décision explicite de l'utilisateur du 16/10/2026 après lecture du résultat
`docs/v216af_porteB_20x10_20261016.md` : activer simultanément
`v216a_ghost_demand=1` et `v216f_dwell_pct=100` par défaut aux quatre niveaux
(`easy`, `medium`, `hard`, `custom`). Les anciens défauts étaient 0/0.
La porte A 40×3 de ce paquet était `fail_primary` (+61,7 k£/an), acceptée
**par dérogation utilisateur**, et la porte B à dix ans `non_erosion` est
`pass` : +139 030,9 £/an, médiane +123 435, 13/7/0,
Wilcoxon p=0,1054, IC95 bootstrap [−30 570,85 ; +300 407,55] £/an,
valeur +4,9086 %, 20/20 paires saines. Le gain robuste à dix ans
n'est pas démontré. Cette adoption est une décision explicite, et ne
requalifie pas le verdict brut de la porte A.

Changement limité à `ai/OpexAI/info.nut` : quatre défauts par réglage ; le
chargement dans `settings.nut`, le chemin comportemental et les bornes ne
changent pas. Les contrats statiques V216a/V216f reflètent le nouveau défaut
et gardent les contrôles de l'inertie des mécanismes à 0.

Contrats : `test_v216_probe.py` 15/15, `test_v216f_dwell.py` 3/3 ;
`test_v214_rail_turn_costs.py` 15/15 (V214 demeure à 0/0).
Smoke adopté : `v216af_adopt_default_smoke_1x1_20261016`,
AAAHogEx complet, seed 42, un an, OpexAI et AAAHogEx `complete`,
0 échec. Trois trimestres clos seulement, attendu pour une première année ;
ce smoke vérifie l'exécution, aucune rentabilité.

## Pré-enregistrement de la nouvelle porte A V214

**Demande utilisateur du 16/10, après l'adoption V216a/V216f :** évaluer V214
sur le *nouveau défaut courant*, en **partie complète** contre AAAHogEx-115
complet. V214 concerne **deux réglages inséparables de coût de virage** pour
l'A* ferroviaire. V214 a déjà passé A et B en rail seul sur un ancien paquet,
mais n'a pas été qualifié en partie complète ; une ablation 10×3 V214 seul
sur l'ancienne base était inconclusive (−72,8 k£/an, 3/7, garde valeur OK).
L'exposition mécanique de V214 est avérée dans la porte A rail seul du 15/10 :
les coudes serrés chutent de 2 746 à 72. Le test présent est nécessaire
pour vérifier l'effet sur le portefeuille multimodal avec V216a/V216f activés.

- Code : même arbre Git figé **après** le commit d'adoption de V216a/V216f,
  avec AAAHogEx inchangé et tous les modes ouverts aux deux entreprises ;
  V129 A* actif selon son défaut courant, V207/V212 non activés.
  Base Git retenue : `8bcccf8e` (`origin/master` au pré-enregistrement,
  comprend l'adoption V216a/V216f `9f9ad9e6` et V211 désactivé par défaut).
  Worktree isolé `results/v214_v216af_A_stage_20261016`.
- Référence : `OpexAI[v214_rail_turn_cost=0,v214_rail_tight_turn_cost=0]`.
  Variante : `OpexAI[v214_rail_turn_cost=300,v214_rail_tight_turn_cost=1500]`.
  Les autres réglages sont identiques et à leurs nouveaux défauts courants,
  dont V216a=1, V216f=100. V214 garde les défauts 0/0 pendant le test.
- Smoke causal préalable : `v214_v216af_complet_smoke_1x1_20261016`,
  seed 42, 1 an, 2 politiques. Contrôler compilation, deux duels, santé et
  différences réelles des réglages. Le smoke n'est pas dans la porte A.
- Porte A : `v214_v216af_complet_porteA_40x3_20261016`, graines canoniques
  40 distinctes, 1 répétition, 3 ans, 80 jeux, `profit_year` terminal Opex
  variante − Opex référence, `gain_short` (règle V102) : Wilcoxon exact
  bilatéral **p < 0,05**, borne basse de l'IC95 bootstrap de la moyenne
  **> 0**, delta moyen **≥ 4 %** du profit moyen OpexAI de référence,
  garde de `company_value` (ratio des moyennes) **≥ −5 %** et **40/40**
  paires complètes, saines et couvertes. Bootstrap 20 000 tirages, seed 0.
- Hôte : PC, Docker `openttd-lab:latest`, un seul banc à la fois,
  10 CPU, 8 Gio RAM/swap et 10 workers. Harnais
  `sweeps/run_c66_reference.py`, source figée, AAAHogEx local complet ; pas de
  changement implicite des défauts, pas de sonde supplémentaire.
- Un `fail_primary` ou `fail_value_guard` arrête la qualification : **pas de
  porte B** sans nouvelle décision. Un résultat `incomplete` réclame un
  diagnostic technique. Si A passe, B serait 20×10 `non_erosion`, campagne
  distincte après vérification, et aucun passage V214 par défaut avant la
  qualification complète.

## Résultat de V214 — porte A complète : `fail_primary`

Smoke `v214_v216af_complet_smoke_1x1_20261016` : deux duels complets,
quatre entreprises `complete`, zéro erreur Squirrel, zéro échec ; écart
OpexAI variante − référence −15 423 £/an (une seule graine : diagnostic).

La porte A `v214_v216af_complet_porteA_40x3_20261016` est terminée sur
**le commit `2845ccd` (dirty=0)**, soit le code `8bcccf8e` plus le seul
pré-enregistrement documentaire ci-dessus. Provenance : bundle
`53743c0b7eba408451922f41203acf7d83f809002dfb1658e52f86f4db0f5c1c`,
manifeste
`891873098adc9894fb28c4dbf84830e58f4513d9b9277356f868920f6ba2edca`,
image Docker `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
Référence V214 0/0, variante 300/1500 ; V216a 1 et V216f 100 communs,
V211 désactivé, AAAHogEx complet dans les deux politiques.

| Mesure (année terminale 1972) | Variante − référence |
|---|---:|
| `profit_year` moyen | **+18 699,05 £/an** |
| `profit_year` médian | +23 444 £/an |
| Variation relative du profit moyen Opex | **+0,8415 %** |
| Victoires / défaites / égalités | **23 / 17 / 0** |
| Wilcoxon bilatéral exact | **p = 0,55369956** (requis < 0,05) |
| IC95 bootstrap de la moyenne (20 000, seed 0) | **[−42 882,525 ; +80 952,95] £/an** (requis borne basse > 0) |
| Seuil de gain 4 % | **88 888,242 £/an** (non atteint) |
| Ratio des moyennes de `company_value` | **1,004220 (+0,421953 %)** (garde −5 % passée) |
| Santé / couverture | **40/40 paires**, **80/80 parties**, **160/160 résumés de compagnies** |
| `comparison_complete`, `adoption_sample_complete`, `metric_coverage_complete` | `true`, `true`, `true` |
| `ci_pass`, `primary_pass`, `value_guard_pass` | `false`, `false`, `true` |
| `policy_comparison.verdict` | **`fail_primary`** |

Les 160 résumés sont `complete`/`run_ok`/`game_ok`, horizon atteint,
**4 trimestres valides** pour chacun, zéro erreur Squirrel, zéro `failed_runs`,
zéro exclusion ou paire incomplète. Le gain moyen est très inférieur au seuil
et aucune inférence de gain positif n'est possible car l'IC95 traverse zéro.
La garde de valeur passe. V214 **ne passe pas la porte A** sur ce nouveau
défaut multimodal ; **aucune porte B** et aucun changement de ses défauts
**0/0**. Les défauts V216a=1 / V216f=100 restent en place.

### Profits annuels moyens par politique, tous modes disponibles

| Entreprise | Référence V214 0/0 | Variante V214 300/1500 |
|---|---:|---:|
| OpexAI (`profit_year`) | 2 222 206,05 £/an | 2 240 905,10 £/an |
| AAAHogEx (`profit_year`) | 1 968 909,23 £/an | 1 938 515,35 £/an |
| OpexAI (`company_value`) | 3 968 401,60 £ | 3 985 146,40 £ |

Le `d%` du tableau OpexAI contre AAAHogEx dans la sortie du banc mesure
l'écart **entre concurrents**, pas la comparaison entre politiques OpexAI.
Le delta primaire de V214 est bien **+18 699,05 £/an**.

### Deltas terminaux par graine (OpexAI variante − référence, £/an)

| Graine | Δ | Graine | Δ |
|---:|---:|---:|---:|
| 1 | −219 024 | 232037 | −14 365 |
| 7 | +227 033 | 292001 | +355 025 |
| 17 | −98 719 | 313707 | −93 852 |
| 42 | +57 795 | 375172 | −129 994 |
| 73 | −325 937 | 423960 | +79 984 |
| 100 | +235 272 | 424242 | +92 002 |
| 314 | +36 580 | 442018 | +235 233 |
| 512 | +16 450 | 455216 | +7 613 |
| 999 | −307 100 | 515222 | +228 669 |
| 1024 | +235 711 | 613553 | +447 475 |
| 1337 | +186 691 | 701256 | −39 778 |
| 2026 | +253 239 | 706990 | +90 398 |
| 4096 | +18 570 | 723002 | −17 877 |
| 8191 | +144 158 | 746035 | −244 115 |
| 12345 | +217 279 | 781335 | −123 208 |
| 54321 | −215 202 | 802204 | −399 346 |
| 59527 | +28 318 | 841478 | +47 397 |
| 65537 | +72 114 | 983759 | −283 058 |
| 123456 | −99 824 | 999533 | −221 484 |
| 230185 | −61 621 | 8675309 | +329 460 |

Artefacts locaux (ignorés par Git, dans ce worktree) :
`results/v214_v216af_complet_porteA_40x3_20261016.json`, `.jsonl`,
`.manifest.json`, `.out`, `_bundle/`, `_engine/`. Les données du smoke
portent le préfixe `v214_v216af_complet_smoke_1x1_20261016`.
