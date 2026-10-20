# V285 — exposition, ablation des quais et wagons, 20 octobre 2026

## Audit du précédent 40×3 (mode 7 contre 0)

Le manifeste `results/v285_railseul_porteA_40x3_pc_20261020.manifest.json` prouve
`decision_log=0`, `probes=2`, `script_debug=true`. Les 40 logs du bras variante
ne contiennent donc aucun `V285 action=wagon` : cela **n'est pas** zéro ajout.
Les relevés agrégés montrent en 1972 +590 places voyageurs et +18,08 entrées
au pool véhicule par graine, avec à peu près le même nombre de locomotives ;
ce sont des proxys de composition, pas des wagons attribuables à V285.
Le verdict économique publié du mode 7 demeure `fail_primary` (+3,40 k£/an,
18/22, valeur −2,25 %) et n'est pas modifié par cette analyse.

## Instrumentation nouvelle (sans modifier les choix V285)

Sous `DECISION_LOG`, les événements suivants sont distincts :

- `V285_GATE` : un motif de blocage **une fois par motif/ligne/mois**, ou
  `eligible` ; les occurrences ne sont pas des tentatives de construction.
- `V285 action=wagon` : lancement d'une transaction, **pas** la preuve d'ajout.
- `V285_RESULT action=moved` : le wagon a été physiquement attaché par
  `MoveWagon` ; coût de la transaction ; `completed` prouve ensuite la reprise.
  Les échecs de dispatch, dépôt, achat, longueur et déplacement ont leur cause.

`sweeps/analyze_v285_exposure.py` produit un CSV et JSON par graine et par
ligne, avec séparation entre tentatives, wagons déplacés, succès définitifs,
échecs et transactions non résolues à l'échéance. **Important :** activer
`decision_log` ajoute beaucoup d'opcodes et change les trajectoires (sur la
graine 42, référence 40×3 sans journal : 847 795 £/an, diagnostic avec journal :
578 644 £/an). Les économies à long terme doivent donc être mesurées avec
`decision_log=0`, sur deux bras symétriques, distinctement des sondes.

## Exposition prouvée — mode 6 sans quai long (5 graines × 3 ans)

Campagne : `v285m6_exposure_5x3_pc_20261020`, `probes=6`, variante `6`
(bits 2+4), référence `0`. 10/10 parties terminées.

| Graine | Tentatives | Wagons déplacés | Transactions terminées | Lignes distinctes | Coût wagons |
|---:|---:|---:|---:|---:|---:|
| 7 | 13 | 12 | 12 | 8 | 17 501 £ |
| 42 | 17 | 17 | 17 | 7 | 24 825 £ |
| 100 | 20 | 20 | 20 | 8 | 29 086 £ |
| 999 | 17 | 16 | 16 | 9 | 16 800 £ |
| 2026 | 17 | 17 | 17 | 8 | 24 800 £ |
| **Total** | **84** | **82** | **82** | — | **113 012 £** |

Deux tentatives sont encore sans issue terminale observée au bout des trois
ans. Aucun échec physique n'a été enregistré. Goulots mensuels observés (par
motif, et **non** nombre de lignes uniques) : profit 484, délai 154, quai 132,
second train 64, attente 17.

Les tentatives répétées d'une même ligne respectent toutes l'intervalle de
90 jours : **0 violation** ; le minimum observé est de 90 jours. Plusieurs
lignes reçoivent deux ou trois wagons en trois ans (jusqu'à trois). Cela
rend importante la fraîcheur du backlog `lastWaitingA/B`, rafraîchi au
rapport annuel : le code peut réutiliser plusieurs fois une observation
ancienne. Il s'agit d'une hypothèse de surdimensionnement, **pas** d'une
preuve causale par ligne.

Indication économique sur ces cinq graines avec journal activé : mode 6
+133 153 £/an, médiane +120 440, 4/1, IC95 bootstrap [+33 924 ; +250 073]
£/an, Wilcoxon p=0,125, valeur +12,78 % : **diagnostic non qualifiant**.

## Ablation bit 1 : quais longs seuls (5 graines × 3 ans)

Campagne `v285m1_exposure_5x3_pc_20261020`, référence et graines identiques,
`probes=6`, variante `1`. **Aucune** transaction wagon (attendu : bit 2 absent).
Δ profit −21 214 £/an, médiane −67 985, 2/3, p=0,8125, valeur +3,14 %.
Pas de gain du quai long isolé démontré à 3 ans. Ce n'est pas une preuve de
compensation exacte bit 1 / bits 2+4 : le plan est un ablation exploratoire.

## Horizon 10 ans — sans journal global

Campagne de suivi `v285m6_railseul_20x10_pc_20261020` : mode 6 vs 0, 20 graines,
10 ans, protocole C66.4 `non_erosion`, `decision_log=0`, `probes=2`, 10 CPU,
10 workers, 8 Go RAM, rail seul des deux côtés, télémétrie de lignes.
`sweeps/analyze_v285_years.py` compare profit, valeur, capacité voyageurs,
trafic livré et courrier livré aux années 3, 5, 7 et 10. Le 20×10 mesure le
mode 6, **pas** un nouveau mode 7 (dont la porte A a échoué).

### Résultat complet

Les **20/20 paires** (40/40 parties) sont complètes ; aucune défaillance
bloquante. À dix ans, **Δ profit annuel −119 868,4 £**, médiane −106 000,5,
**4/16/0**, Wilcoxon **p=0,003654**, IC95 bootstrap
**[−199 607,45 ; −40 461,15] £/an**. Valeur d'entreprise, ratio des
moyennes : **−4,71429 %**. Verdict officiel **`fail_primary`** ; garde de
valeur −5 % respectée, mais le critère de profit échoue nettement.

| Fin de l'année | Δ profit annuel V285m6 − ref. | Gagnants/perdants | Δ capacité passagers | Δ voyageurs livrés au dernier trimestre |
|---|---:|---:|---:|---:|
| 1972 (3 ans) | +46 740 £ | 15/5 | +500 | +814 |
| 1974 (5 ans) | −35 516 £ | 10/10 | +902 | +164 |
| 1976 (7 ans) | −110 229 £ | 7/13 | +1 142 | +337 |
| 1979 (10 ans) | **−119 868 £** | **4/16** | **+1 250** | **+378** |

En 1979 la capacité passagers moyenne est de 2 982 dans le bras 6 contre
1 732 en référence (+72 %), mais seulement 4 633 voyageurs livrés au dernier
trimestre contre 4 255 (+9 %) ; le courrier livré est inférieur de **536**
unités par trimestre. Le gain de capacité ne se transforme donc pas en gain
économique durable. Les métriques sont agrégées par compagnie, sans
attribution à une ligne V285 particulière. Rapport annuel calculé dans
`results/v285m6_railseul_20x10_pc_20261020.yearly.json`.

**Décision :** rejeter la configuration `6` comme candidate d'adoption,
conserver le défaut `0`, ne pas lancer d'autre banc V285 sans hypothèse
mécanique nouvelle (mesure de la demande fraîche avant chaque expansion,
rendement marginal d'un wagon, impact sur courrier et sur autres investissements).

## Archivage Git et vérification

- Les quatre campagnes `v285m6_instrument_smoke_1x3_pc_20261020`,
  `v285m6_exposure_5x3_pc_20261020`, `v285m1_exposure_5x3_pc_20261020`
  et `v285m6_railseul_20x10_pc_20261020` conservent chacune le `.manifest.json`,
  le rapport C66.4 `.json` (le 20×10 en `.json.gz`), les relevés `.jsonl.gz`
  et **tous** leurs journaux moteur en `.engine.tar.gz` (archive contenant
  `<campagne>_engine/*.log`). Compression sans modification des données ;
  originaux non compressés encore disponibles localement sous `results/`.
- Les synthèses `.v285_exposure.{json,csv}` et `.yearly.json` sont versionnées
  à côté des rapports de campagne, pour audit reproductible sans moteur.
- Tests ciblés V285 : **11/11 réussis**. Suite générale : 2 151 tests lancés,
  **1 échec + 1 erreur** dans les tests historiques `test_b9_air_catchment`
  (contrats de réglages B9 obsolètes), hors V285 ; aucune correction B9
  incluse dans ce lot.
- Aucun paramètre de jeu par défaut n'a été modifié et aucun banc n'a été
  relancé pour cet archivage.
