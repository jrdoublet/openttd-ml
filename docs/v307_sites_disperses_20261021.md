# V307 1.8 — Sites de gare dispersés par octant

21 octobre 2026. Changement expérimental **désactivé par défaut** ; aucune porte A ni adoption.

## Hypothèse et périmètre

L'autopsie `docs/v307_extremites_20261021.md` (§ décisions) montre que la spirale
`OpexStationPlans` privilégie les douze premiers plans valides, généralement proches
et rassemblés. Un terrain plat dans un autre octant ne prouve pas qu'un quai y
capte assez de cargo ou qu'un tracé ferroviaire y est possible.

Le réglage `v307_sites` reste **0** aux quatre niveaux. À 0, la recherche de plans
reste la spirale historique ; sous `decision_log` uniquement, un relevé de coût
`V307S_PLANS` est ajouté. À 1 :

- fret : ensemble natif `AITileList_IndustryProducing` ou
  `AITileList_IndustryAccepting`, filtré par évaluateurs natifs de pente et de
  constructibilité, puis classé selon la distance au centre ; au maximum douze
  positions de départ examinées par octant, trois quais retenus par octant,
  douze plans au total, servis en tours des huit octants ;
- villes : anneaux de spirale prolongés avec trois plans retenus au maximum par
  octant ; le budget de travail de la variante est borné à 73 000 opcodes mesurés ;
- dans les deux cas, mêmes filtres locaux de longueur, quai, entrée, cargo,
  empiètement rival, validation réelle par `AITestMode(BuildRailStation)`, et
  exigence de quai parallèle lorsque demandée ;
- journal de contrôle `V307S_PLANS` : type, côté, centre, nombre d'octants,
  plans et opcodes (horloge reposant sur `AIController.GetOpsTillSuspend`).

Le tri natif n'est pas une preuve d'un coût inférieur à la spirale et n'élargit
pas l'emprise au carré complet. Le résultat économique ne peut pas être déduit
du seul nombre d'octants.

## Validation du code

`sweeps/test_v307_sites.py` vérifie le défaut 0 à quatre niveaux, la lecture
unique, la distribution octants/quota, l'usage du sous-ensemble natif et les
cas de logs sans sonde. L'inventaire exhaustif des `.Valuate` est mis à jour
dans `sweeps/fixtures/v262_valuate_inventory.json` (test V262).

La suite complète `python -m pytest sweeps -q` n'est pas disponible dans les
interpréteurs Python du PC ou de l'image Docker de simulation : module `pytest`
absent. Le contrôle `unittest` ciblé et la vérification `git diff --check`
ont été exécutés séparément. Ce manque n'est pas un succès implicite de pytest.

## Exposition et critères pré-enregistrés

- Smoke `v307s_smoke_1x1_20261021` : 1 graine (42) × 1 an, deux bras
  `OpexAI[decision_log=1]` et `OpexAI[decision_log=1,v307_sites=1]`.
  Bundle `30bac441d8ecb44d6814db79e7b8f71e1596bd8ea4ab136e66edaffe4e95929e` ;
  **2/2 parties terminées, zéro erreur script**, verdict `diagnostic_only`.
  Le premier exercice ne comporte aucune tentative RAIL : les seuls appels aux
  sites portent sur des préparations. La sonde observe, respectivement référence
  puis variante : côté A 4→6 octants, médiane d'opcodes 8 134→13 514 ; côté B
  4→6 octants, 5 497→11 169. C'est **au-dessus de ×1,5** sur le petit smoke,
  non concluant sur les tentatives de construction.
- Exposition prescrite : `v307s_expo_3x10_20261021`, mêmes bras et options,
  graines 42, 7, 100, dix ans, 3 workers, `--script-debug` et télémetrie
  par ligne (`--line-telemetry`) pour éviter d'assimiler le profit prédit au
  profit effectivement constaté. Elle seule permettra de comparer les motifs
  `ABND`, `SITEB`, `SITEA`, `SITEAB`, les constructions et la distribution du
  coût par appel.

Critère du prompt avant toute porte A : réduction d'au moins **30 %** du total
`ABND + SITEB` **et** coût par appel au plus **×1,5** de la spirale historique.
Ces critères ne sont pas remplacés par le profit brut d'un banc exploratoire.

## Résultats du banc 3×10

Campagne complète `results/v307s_expo_3x10_20261021.json`, manifeste
`8569caf6c1066067a46c455861e74ddd669ba97ba5c007f324d9a071ee8efdb4`,
**3/3 paires complètes, six journaux, zéro erreur script** ; même bundle
`30bac441d8ecb44d6814db79e7b8f71e1596bd8ea4ab136e66edaffe4e95929e`
que le smoke. Le banc exploratoire est `diagnostic_only`, et non une porte A.

| Mesure | Référence 0 | V307S=1 |
|---|---:|---:|
| `RAIL_ATTEMPT` | 126 | 189 |
| `ABND` | 6 | 2 |
| `SITEA` | 5 | 29 |
| `SITEB` | 3 | 27 |
| `SITEAB` | 27 | 62 |
| **`ABND + SITEB`** | **9** | **29** |
| `RAIL_BUILD` | 78 | 69 |
| Octants médians côté A | 4 | 1 |
| Octants médians côté B | 3 | 0 |
| Ops médianes côté A | 12 390 | 9 083 |
| Ops p90 côté A | 2 246 642 | 17 335 |
| Ops médianes côté B | 14 187 | 2 472 |
| Ops p90 côté B | 2 593 663 | 13 287 |

Les faibles opcodes de la variante sont **trompeurs** : des appels échouent vite
avec `plans=0`, d'où les médianes d'octants de 0 ou 1. Il ne s'agit pas d'une
accélération à service identique. Les très grands p90 de la référence indiquent
des franchissements de ticks dans l'horloge, non un coût de calcul plat par appel.
La population des appels diffère aussi entre bras ; ces statistiques ne sont pas
des paires iso-état.

**Économie exploratoire :** Δ profit_year variante − référence moyen
`+47 100,67 £/an`, médiane `−73 429 £/an`, 1V/2D ; IC95 bootstrap
`[−77 480 ; +292 211] £/an`, valeur ratio des moyennes `+1,2335 %`.
La télémétrie annuelle au dernier point (1979, somme des trois parties) observe
le profit `profit_this_year_gbp` des services ferroviaires à environ
`7,927 M£` en référence et `6,593 M£` en variante. Ces services ne sont pas
un proxy interchangeable avec les seuls nouveaux `RAIL_BUILD`, et ce total
n'est ni le profit consolidé de la compagnie ni un profit prédit.

**Décision : refus de la qualification technique.** L'objectif `ABND + SITEB`
−30 % est inversé (9 → 29, +222 %), et le nombre de nouvelles constructions
recule de 78 à 69. La variante supprime des sites sur certains gisements
industriels : les listes natives filtrées à plat/constructible et limitées aux
premiers candidats peuvent produire zéro quai là où la spirale en proposait.
Le critère `ops ≤ ×1,5` ne peut pas rattraper cet échec : en particulier,
les faibles mesures d'opcodes viennent des retours sans plan. **Aucune porte A,
aucun changement de défaut ; `v307_sites=0`.** Pour reprendre cette piste, il
faudrait garantir un repli de faisabilité (ou élargir les listes natives tout en
préservant le rayon de captage) puis soumettre un nouveau bundle à une
qualification indépendante.

## Valeur 2 : repli spirale (22/10)

### Étape 0 — autopsie des six journaux du 3×10 précédent

Commande : `python -X utf8 sweeps/diag_v307_sites.py --logs
results/v307s_expo_3x10_20261021_engine --autopsy`. Les trois graines
42/7/100 sont conservées ; la table détaillée par année, côté et fret/pax est
reproductible avec `--autopsy`. Tous les appels vides relevés sont du fret.

| Recherche `plans=0` | Spirale v=0 | Native v=1 |
|---|---:|---:|
| Fret, côté A | 16 | 212 |
| Fret, côté B | 25 | 145 |
| **Total** | **41** | **357** |

Sur le côté B natif, `plans=0` atteint 32/39 (82,1 %) en 1973,
21/25 (84 %) en 1974 et 26/30 (86,7 %) en 1975 ; côté A natif,
60/60 (100 %) en 1978 et 34/36 (94,4 %) en 1979. La population des appels
diffère entre les bras : ce n'est pas une comparaison iso-état.

**Diagnostic causal limité :** les anciens événements V307S_PLANS n'enregistrent
ni l'effectif de la liste industrielle brute, ni les survivants de pente,
constructibilité, rayon et quota, ni les rejets longueur + entrée, cargo,
`AITestMode`, quai parallèle. Il est donc impossible d'attribuer **avec preuve**
les 357 absences de plans à une étape particulière. Le code suggère que le
préfiltrage `AITileList_Industry*` + 12 premières positions de chaque octant
élimine des bases décalées pourtant capables de porter un quai de plusieurs
tuiles. L'hypothèse de l'emprise de l'industrie est plausible, **non vérifiée**.
Une instrumentation conditionnée à `decision_log` comptabilise désormais
`native`, `flat`, `buildable`, `bucketed`, `tested`, `clear`, `cargo_ok`,
`station`, `accepted` dans V307S_PLANS. Le décodage `--autopsy` distingue
explicitement les anciens journaux « étape inconnue ». Aucun de ces compteurs
n'est actif au défaut sans journal.

### Étape 1 — variante v307_sites=2

- Valeurs 0 et 1 : logique préexistante conservée, défaut **0** aux quatre
  difficultés. La valeur 2 commence par l'appel exact au code de la spirale
  historique (y compris le classement V207 quand actif), puis recherche les
  sites natifs admissibles dans les seuls octants initialement absents.
- Les ancres natives déjà utilisées sont écartées ; tant qu'il reste de la place,
  les nouveaux octants sont ajoutés. Au plafond de 12, un quai d'un octant
  surreprésenté peut être remplacé sans réduire le nombre de plans et sans
  supprimer le dernier quai de cet octant. Aucun remplacement n'est imposé
  si les propositions natives n'apportent pas d'octant supplémentaire.
- La ligne `V307S_PLANS` de la variante porte `v=2`, `spiral=<n>`,
  `native_added=<n>` et les opcodes de l'appel complet. La recherche native
  interne est muette et ne crée pas de seconde ligne d'appel.

**Contrats pré-enregistrés avant exposition :** smoke 1×1 (42, un an), puis
3×10 (42/7/100, trois paires, horizon dix ans), `decision_log=1` des deux
côtés et aucun réglage comportemental différent sauf `v307_sites=2`.
Critères structurels cumulatifs : (1) `ABND+SITEB` ≤ 70 % de la référence,
(2) `SITEA` ≤ référence + 2, (3) `RAIL_BUILD` ≥ référence, (4) médiane des octants B
≥ référence + 1, (5) médiane d'opcodes par appel ≤ 1,5 × référence.
Le delta `profit_year` du 3×10 est descriptif et **ne décide pas** du passage
à une porte A. Aucun défaut ne change après le résultat.

### Étape 2 — exposition 3×10 complète et verdict

Smoke `results/v307s2_smoke_1x1_20261022.json` : deux duels terminés (graine
42 × 1 an), **zéro erreur Squirrel**. Les six appels `V307S_PLANS v=2`
observés gardent exactement les 12 plans de la spirale en effectif ; entre
2 et 4 propositions natives remplacent des plans dans des octants déjà servis.

Exposition `results/v307s2_expo_3x10_20261022.json`, six journaux dans
`results/v307s2_expo_3x10_20261022_engine` : **3/3 paires complètes**, six
parties saines, **zéro erreur de script**, comparabilité et couverture des
métriques confirmées par `policy_comparison` du JSON final. Le smoke et
l'exposition partagent le bundle figé
`4d16f702141b566a36913bfe3465b603beb3798b893d410ef0b07358e836e95b` ;
manifeste de l'exposition
`ec9a73a974f78b2494b9b67f9eeca8bba1a8774c3f542ff2aaa442e90c8d2f9f`.
Mêmes graines 42/7/100, horizon dix ans, mode apparié, `decision_log=1`,
`--line-telemetry`, 3 workers et plafonds 10 CPU / 8 Go sur PC.

| Critère pré-enregistré | Référence | V307S=2 | Condition | Verdict |
|---|---:|---:|---|---|
| 1. `ABND + SITEB` | 12 | 4 | Variante ≤ 8,4 | **Passe** |
| 2. `SITEA` | 6 | 0 | Variante ≤ 8 | **Passe** |
| 3. `RAIL_BUILD` | 78 | 80 | Variante ≥ 78 | **Passe** |
| 4. Octants médians côté B | 3 | 6 | Variante ≥ 4 | **Passe** |
| 5. Ops médianes par appel, tous côtés | 11 268 | 24 251 | Variante ≤ 16 902 | **Échoue : ×2,15** |

Compléments : médiane d'opcodes côté A, 11 225,5 → 24 106,5 (×2,15) ;
côté B, 11 582 → 25 437,5 (×2,20). Les appels `V307S_PLANS` sont 214
en référence et 188 en variante, avec `plans=0` respectivement 23 et 12.
Sur 188 appels v=2, **aucun** ne retourne moins de plans que sa spirale
(`plans >= spiral`), et la somme des `native_added` vaut 310. Les
distributions d'appels sont dépendantes des trajectoires et non iso-état ;
les opcodes enregistrés peuvent aussi englober des ticks. La mesure est
néanmoins celle pré-enregistrée pour décider de la qualification technique.

**Économie exploratoire, non qualifiante :** delta `profit_year`
`−259 768 £/an` (moyenne), `−411 154 £/an` (médiane), 1V/2D/0E,
IC95 bootstrap de la moyenne `[−868 211 ; +500 061] £/an`
(20 000 tirages, graine bootstrap 0), Wilcoxon p=0,75. Ratio des moyennes
de valeur de compagnie `0,957211` (−4,279 %). Ce panel de trois graines
n'autorise aucune conclusion sur un gain ou une perte à généraliser.

**Décision : qualification technique REFUSÉE (4/5).** Le repli spirale
élimine la majorité des `SITEA`/`SITEB` et améliore les constructions,
mais la recherche combinée coûte **2,15 fois** les opcodes médians de la
référence, au-dessus du plafond ×1,5. **Ne pas lancer de porte A 40×3,
ne pas modifier le défaut `v307_sites=0`.** Un prochain essai devrait
éviter le double parcours intégral des sites sans perdre la garantie de
faisabilité de la spirale ; ce serait un autre bundle et un autre test.

### Contrats et traçabilité de publication

Les **50 tests ciblés** V307S, V207 et V261 passent. Suite complète
`python -X utf8 -m unittest discover -s sweeps -p 'test_*.py'` :
**2 397 tests**, deux échecs, deux tests ignorés et deux échecs attendus.
Les deux échecs restants sont les plafonds de `AddSetting` codés en dur
dans `test_v246_fixed_policies.py` et `test_v284_rail_growth.py` (94
attendu, **98 déjà dans le HEAD avant les modifications V307S=2**).
Les deux autres échecs apparus pendant le développement (signature V207,
clé d'audit `cargo=0`) sont corrigés ; tous les tests concernés passent.
`git diff --check` est sain.

Commit de code et de résultats de la file A : **`8f4ac6c1`** (après rebase
sur `master`, contenu initial `59be7d4c`). Les bancs ont été gelés avant
ce commit avec un arbre Git sale : le **bundle** précité est l'autorité
de reproductibilité, et contient des modifications simultanées de la
file B, dont les interrupteurs restent par défaut à zéro. Le commit
sélectif de la file A n'embarque aucune modification de V307R.

## Valeur 3 : prolongation ciblée de la spirale (22/10, Claude VPS)

### Pourquoi la valeur 2 coûte ×2,15

Lecture du code de `OpexV307HybridStationPlans` (`dec590bd`) : après la spirale,
la recherche native de la valeur 1 est relancée **entière** (huit octants, trois
quais par octant, douze plans), alors que l'hybride n'en garde **qu'un quai par
octant absent**. Deux gaspillages, démontrables sans partie :

1. **Spirale épuisée** (moins de 12 plans dans le rayon 30) : toutes les tuiles du
   carré ont déjà été testées, avec les quatre mêmes orientations et les mêmes
   filtres que `OpexV307SiteTry`, sur un état de carte inchangé (`AITestMode`).
   Les sites natifs (captage de l'industrie, à moins de 30 tuiles) sont un
   sous-ensemble de ces tuiles : le complément **ne peut rien trouver**, mais la
   valeur 2 le paie quand même.
2. **Spirale arrêtée à sa limite** à l'anneau *s* : les anneaux < *s* sont
   entièrement testés et ont échoué dans les octants absents. Seuls les anneaux
   ≥ *s* peuvent apporter un quai, et un seul par octant absent est utile.

### Variante `v307_sites=3`

- la spirale historique d'abord (même copie que la valeur 2), qui rend aussi son
  anneau d'arrêt ;
- spirale épuisée : aucun complément ;
- sinon, prolongation de la spirale à partir de l'anneau *s*, **dans les seuls
  octants absents, un quai chacun** ; un bord d'anneau qui ne touche aucun octant
  absent n'est pas parcouru ; fret borné par le captage natif de l'industrie
  (`AIMap.DistanceMax` maximal + longueur de quai − 1), ville par le rayon ;
- complément plafonné à **60 % des opcodes de la spirale du même appel**
  (`V307S3_BUDGET_PCT`), vérifié avant chaque tuile, avec une réserve égale à
  l'essai le plus cher déjà vu dans l'appel (estimation, pas une borne stricte :
  le premier essai, ou un essai plus cher que les précédents, peut déborder) ;
  coût de spirale nul ou négatif : aucun complément ; au plafond de 12 plans,
  même remplacement que la valeur 2 (octant le plus fourni, jamais son dernier
  quai) ;
- trois économies **exactes** (mêmes plans) : chaque bord d'anneau est coupé
  d'avance en trois segments d'octant, seuls les segments voulus **et leurs deux
  voisins** sont parcourus (l'octant qui compte est celui de l'**ancre** du quai,
  comme dans le décompte ; une orientation négative recule l'ancre de longueur − 1
  tuiles et peut changer d'octant : revue Codex du 22/10, corrigée avant le smoke
  `v307s3e`) ; toutes les orientations admises d'une tuile sont essayées, la
  première dont l'ancre tombe dans un octant encore ouvert est gardée ;
  une tuile de base non constructible ou en pente est écartée avant les quatre
  orientations (elle est tuile de quai dans les quatre), dans la prolongation
  **et dans la copie de spirale de la valeur 3** ; la portée du captage est mise
  en cache par tuile d'industrie et côté (`V307S3_REACH`, non sauvegardé),
  recalculée si le type d'industrie ou le rayon de captage diffère ;
- `V307S_PLANS ... v=3 spiral= native_added= spiral_ops= extra_ops= stop_ring=
  max_ring= wanted=` sous `decision_log` ; valeurs 0, 1 et 2 inchangées
  (la copie de spirale prend un argument optionnel `scan`, nul pour 2).
- Limites connues : la prolongation n'alimente pas les compteurs `stats` de
  l'autopsie (ses compteurs propres sont dans la ligne `V307S_PLANS`) ; avec le classement V207 (`v207_rail_pax_site_rank_pct > 0`,
  défaut 0), les plans écartés par le classement dans les anneaux < *s* ne sont
  pas repris.

Contrats : `sweeps/test_v307_sites.py` vérifie que les bords couvrent chaque
tuile d'anneau une fois avec les octants déclarés, et, sur 400 grilles
aléatoires, que repartir de *s* retrouve exactement les mêmes octants, au même
anneau, qu'un parcours complet, et rien quand la spirale est épuisée.

### Calibrage sur smokes 1×1 (graine 42, un an, avant l'exposition)

Quatre smokes successifs, 0 erreur Squirrel chacun, six appels `V307S_PLANS`
par bras, mêmes centres et mêmes dates dans les deux bras (comparaison appariée
appel par appel). Le coût logué de la référence inclut son propre comptage
d'octants sous `decision_log`.

| Smoke | Version | Ratio apparié ops v3 / ops réf. (min–max) | Quais ajoutés / 6 appels | Octants (somme) réf. → v3 |
|---|---|---:|---:|---:|
| `v307s3_smoke_1x1` | budget 40 %, sans pré-test | 1,30–1,36 | 2 | 23 → 25 |
| `v307s3b_smoke_1x1` | + pré-test prolongation, réserve | 1,26–1,33 | 3 | 23 → 26 |
| `v307s3c_smoke_1x1` | + pré-test spirale, segments | 0,98–1,19 | 1 | 23 → 24 |
| `v307s3d_smoke_1x1` | budget **60 %** | 1,20–1,34 | **6** | 23 → **29** |

Compteurs du dernier : 4 à 8 tuiles balayées, 1 à 5 essais par appel, toujours
arrêté par le budget ; un essai sur tuile constructible coûte ~700 à 1 500
opcodes, le premier calcul de portée de captage ~1 500. La spirale du smoke
s'arrête aux anneaux 1-2 : ses 12 plans viennent de trois tuiles de base au plus.
**60 % est retenu avant l'exposition** ; le texte du pré-enregistrement ci-dessous
est mis à jour en conséquence.

### Pré-enregistrement (avant tout banc)

Dépôt `openttd-ml`, branche locale `v307s3` sur `dec590bd` (non poussée), arbre
modifié consigné dans le manifeste. Bras : `OpexAI[decision_log=1]` contre
`OpexAI[decision_log=1,v307_sites=3]`, mêmes autres réglages. Hôte VPS
(`--cpus 3 --memory 2g --max-workers 3 --network host`).

1. Smoke 1×1 (graine 42, un an) : 2/2 parties, zéro erreur Squirrel.
2. Exposition **3×5** (graines 42, 7, 100 ; cinq ans car le VPS ne fait pas
   de 10 ans de jour), `--script-debug --line-telemetry`. Mêmes cinq critères
   que la valeur 2, sommes sur les trois graines :
   (1) `ABND+SITEB` ≤ 0,7 × référence ; (2) `SITEA` ≤ référence + 2 ;
   (3) `RAIL_BUILD` ≥ référence ; (4) octants médians côté B ≥ référence + 1 ;
   (5) opcodes médians par appel ≤ 1,5 × référence. Descriptif seulement :
   médiane iso-état `extra_ops / spiral_ops` dans la variante, profit 3×5.
3. Si les cinq tiennent : porte A V102 40×3 `gain_short` (Wilcoxon p < 0,05,
   borne basse IC95 bootstrap > 0, delta ≥ 4 %, garde de valeur 5 %), sur le VPS
   puisque la branche n'est pas publiée ; sinon arrêt, défaut 0, cause en une
   phrase. Porte B 20×10 seulement avec l'accord de l'utilisateur. Aucun
   changement de défaut.

### Exposition 3×5 (22/10, VPS) : arrêt, défaut 0

`v307s3_expo_3x5_20261022`, code `dec590bd` + arbre modifié (correctifs de la
revue Codex inclus : octant d'ancre, garde budgétaire par tuile, cache vérifié),
6/6 parties complètes, 0 erreur Squirrel. Smoke préalable `v307s3e_smoke_1x1` :
2/2, ratio apparié des opcodes par appel 1,12–1,40, octants 23 → 26.

| Critère (sommes 3 graines) | Référence | Valeur 3 | Seuil | Verdict |
|---|---:|---:|---|---|
| (1) `ABND+SITEB` | 3 | 6 | ≤ 2,1 | échec |
| (2) `SITEA` | 0 | 0 | ≤ 2 | tenu |
| (3) `RAIL_BUILD` | 68 | 66 | ≥ 68 | échec |
| (4) octants médians côté B | 4 | 4 | ≥ 5 | échec |
| (5) opcodes médians par appel A / B | 8 134 / 8 992 | 9 351 / 12 145 | ≤ ×1,5 | tenu (×1,15 / ×1,35) |

Descriptif : 180 appels v=3, 41 spirales épuisées (aucun complément), 139
compléments, 63 quais ajoutés ; médiane iso-état ops/spirale 1,57 (p90 1,71,
max 1,84 : le premier essai déborde la réserve de 60 %). `SITEAB` 17 → 10.
Profit 5 ans −54,5 k£/an (médiane −65,5 k, 1 V / 2 D, IC95 bootstrap
[−281 ; +183] k£), valeur +1,6 %.

**Cause :** sur ces graines le défaut visé est déjà rare dans la référence
(3 `ABND+SITEB` en 93 tentatives), et les quais ajoutés, un par octant absent
sur l'anneau suivant, ne déplacent pas la médiane d'octants ni la construction.
Pas de porte A ; `v307_sites=3` reste à 0, branche locale non publiée.
