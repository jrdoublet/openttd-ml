# V303 — sonde RAIL inverse découpée : exposition confirmée, NO-GO économique

26 octobre 2026 — prototype expérimental **non adopté**. Base `7996efc0`,
branche isolée `v303_reverse_probe_sliced_20261026`, réglage
`v303_reverse_probe_sliced` : 0 OFF par défaut (quatre profils), 1 SHADOW
passif, 2 ON. Hypothèse et critères figés dans
[`v303_reverse_probe_sliced_prereg_20261026.md`](v303_reverse_probe_sliced_prereg_20261026.md).
Seule la version **découpable** a été étudiée ; l'option V303 à deux A*
alternés n'a pas été étudiée et n'est pas recommandée sans nouveau pré-enregistrement.

## Ce qui fonctionne et ce qui n'est pas prouvé

Le même pathfinder inverse reprend la recherche en tranches d'au plus
50 itérations, total **300** au maximum, et est libéré avant de créer
l'aller en cas d'échec. L'objet A* reste transitoire, jamais sauvegardé.
`FindPath` retient sa frontière et `LastConsumed()` rapporte la
consommation du dernier appel. L'instrumentation distingue opcodes/ticks
de sonde, comptabilise ces opcodes dans le plan et garde **un seul**
`V294F_PROBE` final par tentative, non par tranche. Le scheduler et
les ledgers C80 acceptent la phase `reverse`.

- Suite hôte : **2 911 tests, OK** (6 skipped, 2 expected failures),
  dont **9 nouveaux contrats V303** ; empreintes des sources
  historiques vérifiées après retrait exact des fragments expérimentaux.
  `git diff --check` : OK.
- Smoke moteur `v303_sliced_smoke_1x1_20261026_r2` : **2/2** parties
  1 an complètes ; même profit annuel **483 881 £/an** et valeur
  **457 955 £** entre OFF/ON. Aucun effet V303 inférable de ce smoke.
- Save/Load avec ON : `v303_sliced_save_load_seed42_20261026.json`,
  graine 42, phase A **3 ans / 36 sauvegardes**, reprise à partir du
  **1er juillet 1971**, phase B **1 an / 12 sauvegardes**, marqueur
  `LOAD_RECONCILE` positif, aucun échec script. Le marqueur
  `rail_search_dropped=0` signifie toutefois que cette sauvegarde
  n'a **pas** capturé une recherche inverse en cours ; le reset
  transitoire est contrôlé par contrats hôtes, pas par ce scénario moteur.
  Le harnais a fait apparaître **une compagnie humaine fantôme** après
  chargement : ce test ne prouve pas une neutralité économique de
  deux parties à monde identique.

## Diagnostic apparié pré-enregistré, 5 graines × 5 ans

Campagne `v303_sliced_exposure_5x5_20261026_r1`, graines
**42, 100, 7, 999, 2026**, même arbre expérimental et même bundle
`9e4025926836c26e131e970508d4f388da7d765d310aa39bdf13d1c95be7d7b8`,
opposant AAAHogEx-115 dans chaque partie, `probes=6` identiques
pour OFF/ON, `--script-debug`, dix workers, dix parties **complètes**.
Image `openttd-lab:latest`, SHA Docker
`f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
Le manifeste indique **dirty=1** pour le prototype, non une révision
Git figée et propre : aucune prétention d'adoption.

| Graine | Sondes inverses ON terminées | Tranches ON | Sondes multi-tranches | RAIL_BUILD OFF | RAIL_BUILD ON |
|---|---:|---:|---:|---:|---:|
| 42 | 20 | 104 | 20 | 22 | 20 |
| 100 | 24 | 110 | 22 | 19 | 20 |
| 7 | 24 | 124 | 24 | 25 | 26 |
| 999 | 29 | 161 | 29 | 26 | 29 |
| 2026 | 28 | 152 | 28 | 25 | 23 |
| **Total** | **125** | **651** | **123** | **117** | **118** |

Le maximum observé est **six tranches et 300 itérations**, aucun
`V303_REVERSE` terminal `ERROR` observé. Les **125 événements finaux**
correspondent aux 125 `V294F_PROBE` du bras ON ; le bras OFF a eu
respectivement 24, 20, 23, 28, 28 tentatives par graine. Les mondes
divergent après les premiers choix : ne pas comparer ces dénominateurs
comme des paires de sondes nécessairement identiques.

Une chaîne physique est démontrée sur la graine 42, couple
`COAL 45472→51600` : `PROJECT_CHOSEN` le 23 janvier 1971,
`V303_REVERSE` CONT après 50 itérations, puis OK après **99**
itérations / **2 tranches**, `RAIL_ATTEMPT ok=1`,
`RAIL_BUILD line=16` le **28 janvier**. En OFF, la **même ligne**
était construite dès le **26 janvier**. Cela prouve la reprise et une
différence d'ordonnancement, mais **pas** un profit marginal supérieur.

La variante compte **56 couples construits en ON mais absents en OFF**,
face à **55 couples construits en OFF mais absents en ON**. La plupart
des différences sont donc des **substitutions de lignes physiques**,
non des additions nettes. Les différences de compte par graine sont
**−2 / +1 / +1 / +3 / −2**, soit seulement **+1 ligne nette**
sur les cinq graines. Les profits prédits des 56 lignes ON exclusives
ne sont **pas** des profits attribuables : ils ne retranchent pas le
coût/opportunité des 55 lignes OFF exclusives et ne démontrent pas la
causalité d'un créneau libéré.

| Mesure terminale appariée ON − OFF | Valeur |
|---|---:|
| Différence moyenne de profit annuel | **+168 878,4 £/an** |
| Victoires / défaites | **4 / 1** |
| Test de Wilcoxon bilatéral | **p = 0,1875** |
| IC95 bootstrap | **[−29 962,2 ; +357 221,6] £/an** |
| Garde de valeur (ratio des moyennes) | **0,998404** (−0,1596 %) |
| Résultat du lanceur | `diagnostic_only` |

Cette distribution n'est ni une preuve d'amélioration causale ni un
échec économique significatif. Elle ne satisfait surtout **pas**
l'exigence pré-enregistrée de deux mondes avec *construction
additionnelle directement attribuable au temps libéré* et somme de
marges nettes prouvées ≥4 % des profits de référence : les lignes
exclusives se remplacent massivement et leur valeur incrémentale
n'est pas identifiable par ce protocole seul.

## Décision

**NO-GO exposition pour la sous-hypothèse V303 découpable**.
Ne pas exécuter la porte A 40×5 ni B 20×10, ne pas adopter
`v303_reverse_probe_sliced=2`, ne pas modifier les quatre défauts,
ne pas merger le code expérimental sur `master`. Conserver le
prototype et ses tests sur sa seule branche de recherche pour
reproductibilité ; publier seulement cette décision documentaire
sur `master`. Une future hypothèse exige un nouveau mécanisme et une
preuve de valeur physique attribuable, pas la répétition de ce même 5×5.
