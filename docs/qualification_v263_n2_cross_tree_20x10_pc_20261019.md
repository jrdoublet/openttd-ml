# V263 — deux duels N2 de 20 graines × 10 ans, bilan PC (19 octobre 2026)

## Statut et verdict

**Exécutions terminées et saines ; comparaison économique descriptive seulement, NON QUALIFIÉE.**
Les deux campagnes C66.3 ont produit chacune **20/20 duels complets** (1970–1979),
sans `failed_runs` ni erreur script attribuée. La tentative de comparaison
`sweeps/compare_cd_cross_tree_c66.py --economic-only` échoue sur
`AssertionError: Unexpected changed AI setting` : les deux arbres **n'ont pas les
mêmes réglages effectifs**. Ne pas présenter le delta comme une preuve causale de
neutralité, ni comme une qualification V263 permettant une adoption.

Le delta descriptif du `profit_year` d'OpexAI **V263 − master** est
**+48 883,05 £/an (+1,34 %)** sur les 20 graines, 11 victoires et 9 défaites,
IC95 bootstrap de la moyenne **[−104 996,25 ; +205 504,55] £/an**. Cet intervalle
traverse zéro. AAAHogEx évolue lui aussi sensiblement entre les deux campagnes.

## Exécution, sources et reproductibilité

| Élément | Référence master | Variante V263 |
|---|---|---|
| Arbre Git exécuté, propre | `1b76124233869bc2050389f3b000ac7e63ffd509` | `8dbf8c136a706a30cd5cb8406232851ce0a1f59c` |
| Campagne | `v263_master_n2_20x10_pc_20261019` | `v263_branch_n2_20x10_pc_20261019` |
| Bundle figé SHA-256 | `ac5014463008879993550da1297e87aabe903fab03118b866f9bd449696fa772` | `dd58376a222b1c0378414548fce9f01c7b323632ab2049f7308326f44f687d70` |
| Manifeste SHA-256 | `73aefb33f6881914e44a9d6a0ba48e374c8f91a3dffa3285087540b8fd94d292` | `326e831c510b12429d39a7ee12403dc154570ec0399c80358c5fc5b550b0a961` |
| JSON résultat SHA-256 | `fbf6f119bd1c7e446fbbfac2a3e43c84b992c0a10af7d88ed293e845d8b10d31` | `2f13416d4b38e8a2bb08b9d40267b814b7797632eb3fda0a943c7fa53d98df33` |
| Santé | 20/20 `game_ok`, 0 échec | 20/20 `game_ok`, 0 échec |

- Protocole : **un duel OpexAI N2 (`opex_difficulty=2`) contre AAAHogEx-115
  par graine et par arbre**, en carte partagée ; une répétition, 10 ans à partir de
  1970. Ce sont **deux séries C66.3 indépendantes**, et non une expérience C66.4
  à deux bras ni un replay contrefactuel de la même partie.
- Graines dans **l'ordre effectivement exécuté** : 1024, 42, 100, 7, 999,
  2026, 1, 17, 373684, 314, 512, 1337, 4096, 8191, 12345, 54321,
  65537, 123456, 424242, 8675309. La graine historique 73 est remplacée par
  373684 dans le lanceur en raison d'un plantage déterministe connu d'AAAHogEx.
- **`1024` désigne ici une graine, pas une dimension de carte.** La configuration
  réellement exécutée porte `map_size=8`, soit **256 × 256 cases** ; aucune
  campagne 1024 × 1024 n'a été effectuée par ce lanceur.
- Smokes `v263_master_n2_20x10_pc_20261019_smoke` et
  `v263_branch_n2_20x10_pc_20261019_smoke` : une graine **1024** × un an,
  1/1 duel sain dans chaque arbre. Pour cette exécution, l'ordre des graines
  et la graine des smokes avaient été réordonnés temporairement dans le script ;
  le fichier `sweeps/run_v263_pc.sh` a ensuite été **restauré à l'identique**.
  Les manifestes et les JSON font foi sur les graines réellement exécutées.
- PC local : Docker `openttd-lab:latest`, OpenTTD **15.3**, OpenGFX **7.1**,
  OpenTTDLab **0.0.75**, **10 CPU / 8 Go / 10 workers**, `--network host` ;
  une campagne à la fois (master, puis V263). Même SHA-256 d'AAAHogEx :
  `eaec19151d118daad80eddab437180402764e1c919f48904cc22cbf71cb80bc7`.
  Sources OpexAI différentes, comme prévu : master
  `df6fc917861462288cc0cd60e4766e1591b5924298b4c258f0ba13685475b0c1`,
  V263 `76f8ebd7c582af600e01adbcf89d799e69e0e4abcc076dc7b81bc8a0d484b6ad`.

## Résultats à dix ans

Moyennes sur les 20 graines, **année terminale** (les chiffres par campagne
sont des mesures, pas des paires causales contrôlées).

| Mesure | Master OpexAI | Master AAAHogEx | V263 OpexAI | V263 AAAHogEx |
|---|---:|---:|---:|---:|
| `profit_year` (£/an) | 3 636 971,70 | 7 467 996,05 | 3 685 854,75 | 7 837 313,30 |
| `company_value` (£) | 19 089 027,90 | 28 082 329,95 | 19 114 183,10 | 28 197 728,00 |
| Véhicules primaires | 168,45 | 278,15 | 155,85 | 290,80 |
| Gares | 79,85 | 175,00 | 76,95 | 183,50 |
| OpexAI / AAAHogEx en profit (rapport des moyennes) | **48,70 %** | — | **47,03 %** | — |

| Écart descriptif V263 OpexAI − master OpexAI | Valeur |
|---|---:|
| `profit_year`, moyenne | **+48 883,05 £/an**, soit **+1,34 %** du master |
| `profit_year`, médiane | +69 812,50 £/an |
| Profit, victoires / défaites / égalités | 11 / 9 / 0 |
| Profit, IC95 bootstrap moyenne | **[−104 996,25 ; +205 504,55] £/an** |
| `company_value`, moyenne | +25 155,20 £ (**+0,13 %**) |
| Valeur, IC95 bootstrap moyenne | [−492 234,80 ; +556 582,40] £ |
| Véhicules primaires, moyenne | −12,60 (−7,48 %) |
| Gares, moyenne | −2,90 (−3,63 %) |

IC95 reproduit par rééchantillonnage apparié **10 000 fois**, générateur Python
`random.Random(20261012)`, selon la fonction `ci()` du comparateur ; les
comparaisons restent **exploratoires**. En parallèle, le profit annuel moyen
d'AAAHogEx change de **+369 317,25 £/an** entre ses deux séries indépendantes ;
le ratio OpexAI / AAAHogEx recule d'environ **1,67 point** malgré la petite
hausse de profit absolu d'OpexAI.

### Deltas OpexAI `profit_year` par graine (V263 − master, £/an)

| Graine | Delta | Graine | Delta |
|---:|---:|---:|---:|
| 1 | −384 816 | 7 | +172 096 |
| 17 | −301 656 | 42 | +454 888 |
| 100 | +363 255 | 314 | −273 411 |
| 512 | −256 465 | 999 | −29 473 |
| 1024 | −259 341 | 1337 | +49 018 |
| 2026 | +184 845 | 4096 | +812 959 |
| 8191 | −38 876 | 12345 | +90 607 |
| 54321 | +150 752 | 65537 | +334 113 |
| 123456 | −57 375 | 373684 | −786 291 |
| 424242 | +489 652 | 8675309 | +263 180 |

## Pourquoi le comparateur refuse la qualification

Les garanties sur les mêmes graines, horizon, version moteur, configuration
de carte et source AAAHogEx sont vérifiées. Le comparateur s'arrête **avant**
de retourner un JSON valide au test d'identité des réglages effectifs :

```text
AssertionError: Unexpected changed AI setting
```

Le manifeste master contient **79** réglages effectifs, celui de V263 **75**.
Quatre clés sont présentes **seulement** dans master :

| Réglage supprimé du manifeste V263 | Master |
|---|---:|
| `v252_air_engine_refresh` | 2 |
| `v257_rail_refresh` | 1 |
| `v259_bridge_renew` | 0 |
| `v264_convergent_freight` | 1 |

Deux clés communes portent des valeurs **effectivement différentes** :

| Réglage | Master | V263 |
|---|---:|---:|
| `v178_rail_shared_dest` | 1 | 0 |
| `v179_rail_gen_dest_served` | 1 | 0 |

Ces différences ne sont pas une simple divergence de noms : **les deux options
ferroviaires communes changent de valeur**. La disparition des autres clés ne
prouve pas à elle seule que leurs chemins métiers sont identiques. Le contrôle
de conformité du comparateur doit donc **rester bloquant** : ne pas supprimer
l'assertion ni modifier rétrospectivement un manifeste ou un bundle figé.
Une comparaison causalement interprétable exigerait un protocole pré-enregistré
et la parité des réglages actifs ou des comportements figés ; aucune relance
n'est engagée dans cette documentation.

## Artefacts et portée

- Master (worktree `../v263-master-tree`) :
  `results/v263_master_n2_20x10_pc_20261019.json`, son `.manifest.json`,
  `.jsonl`, les bundles et journaux moteur de même préfixe.
- V263 (checkout principal) :
  `results/v263_branch_n2_20x10_pc_20261019.json`, son `.manifest.json`,
  `.jsonl`, les bundles et journaux moteur de même préfixe.
- La tentative `results/v263_cross_tree_20x10_pc_20261019.json` **n'a pas
  produit de fichier qualifié** : l'assertion sur les réglages a arrêté l'outil.
- Les gros artefacts restent localement sous `results/` (ignoré par Git) ; les
  empreintes ci-dessus permettent de vérifier les copies d'origine. Cette
  documentation ne constitue **pas** un archivage Git des JSON bruts.

**Décision de ce rapport :** état du banc clôturé, **qualification V263 non établie**.
Aucun nouveau banc, aucune modification de comportement OpexAI et aucune
adoption implicite.
