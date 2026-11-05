# INVEST-STALL — qualification de la transaction de quais (4 novembre 2026)

## Périmètre et état

Essai de la révision INVEST-STALL qui privilégie l'ajout d'un wagon, puis
l'extension transactionnelle des quais vers **7, puis 6 tuiles**, sous
contrôles économiques. Branche `exp/rail-sibling-20261102`, worktree
`/openttd-ml/.wt_sibling_20261102`, HEAD `99f29d9c858f390de6193978a4f12d3fbdb48127`
avec modifications locales préexistantes. Paramètre `invest_stall=0` par
défaut, jamais changé ici ; aucune publication.

Tests vérifiés le 4 novembre : **50/50 contrats INVEST-STALL** et **12/12
contrats V284** verts ; projection OFF `sweeps/invest_stall_platform_off.py`
sans écart et `git diff --check` sans erreur. Ces tests contrôlent du code
source, pas la réussite physique d'une extension. Image Docker
`sha256:0480a863e164856797412ff4a0782621464a52087abbb9c056dd3587d46cac31` ;
bundle de simulation des trois duels
`5bc450a5fc5ef289f3ea1a13468e3170c51aa40f94f679184b56b61f44efc261`.

Les duels comparent sur la même carte
`OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1]`
à ce même bras avec `invest_stall=1`, face à AAAHogEx désactivé sur
ROAD/TRAM/SHIP/AIR. `--probes 6`, `--script-debug`, carte 256²,
année de départ 1970, 9 workers, 9 CPU et 8 GiB RAM.
La garde de valeur était explicitement ignorée (`100`) pour ces diagnostics,
conformément au protocole expérimental historique : **aucun verdict ne vaut
qualification d'adoption V102**.

## Simulation et économie

| Campagne et horizon | Couverture et santé | ON − OFF, `profit_year` | IC95 bootstrap | Autres indicateurs |
| --- | --- | ---: | --- | --- |
| `invest_stall_platform_smoke_1x1_20261104_b` (graine 42, 1970) | 1/1 paire, 2/2 parties `complete` | −16 676 £/an | [−16 676 ; −16 676] £/an | `diagnostic_only` ; mécanisme tardif non exposé |
| `invest_stall_platform_exposure_4x6_20261104_a` (17, 512, 841478, 65537 ; 1970–1975) | 4/4 paires, 8/8 parties ; Opex seed 17 `stagnation_suspect`, autres Opex `complete` | **+42 580,75 £/an** | [−65 870,75 ; +149 950,50] £/an | 3 V / 1 D, Wilcoxon p=0,625 ; valeur +13,03 % ; `diagnostic_only` |
| `invest_stall_platform_exposure_2x8_20261104_a` (17, 65537 ; 1970–1977) | 2/2 paires, 4/4 parties `complete` | **−103 120 £/an** | [−168 897 ; −37 343] £/an | 0 V / 2 D, Wilcoxon p=0,5 ; valeur +19,11 % ; `diagnostic_only` |

Sources : `results/<nom_de_campagne>.json`, `.manifest.json`, `_engine/`,
`_bundle/` et `_saves/`. Les expériences 2×8 prolongent deux **mêmes graines**
déjà incluses au 4×6 ; leurs observations ne sont pas des répétitions
indépendantes. Avec deux ou quatre graines, ni le signe du delta ni les IC95
ne permettent un verdict de gain ou d'érosion généralisable. Aucun passage
40×5/20×10 de cette **révision de quai** n'a été engagé.

La tentative initiale `invest_stall_platform_smoke_1x1_20261104_a` a été
rejetée avant simulation : l'option `decision_log=1` n'est pas un réglage
NoAI déclaré. Les relances `b`, 4×6 et 2×8 utilisent `--probes 6`, qui
active le journal de décision. Ne pas interpréter ce pré-échec comme un
échec du moteur ni comme un duel supplémentaire.

## Exposition physique et sûreté

Dans les logs `INVEST_STALL` de la variante du **4×6**, on trouve **34
`origin_candidate`**, **2 `station_built`** et **2 `build_ok`** pour la
création de nouvelles lignes (graines 512 et 65537). Ce sont des événements
de construction physiques, pas des preuves d'un effet économique positif.

Sur le chemin **d'extension de quais**, **12 événements `kind=platform`**,
tous `event=skip reason=unsafe_or_busy` (5 sur la graine 17, 7 sur 65537).
**Aucun** `kind=platform` avec `screen eligible`, `pick`, `done`, `fail`,
`rolled_back` ou `orphan_safe`. Après extension à huit ans sur les deux
graines concernées, **24 refus `unsafe_or_busy`** (10 sur 17, 14 sur 65537),
aucune transaction de quai démarrée. Ces 24 refus incluent les observations
des six premières années : ne pas les additionner aux 12.

La condition `unsafe_or_busy` agrège les réservations des autres tâches,
la validation topologique et la cohérence des deux plans de quai.
Les logs actuels ne permettent pas d'attribuer les 24 refus à une clause
unique. Il faut ventiler cette garde avant d'envisager une intervention ;
**ne pas assouplir les garde-fous de sécurité** en l'absence de cause
physique établie. Aucun `Squirrel` fatal, `Your script made an error`,
`The script died unexpectedly` ou message d'échec Save/Load repéré dans
les journaux moteur de ces campagnes.

## Reprise Save/Load

`results/invest_stall_platform_roundtrip_seed512_20261104.json` est le
rapport de `sweeps/save_load_roundtrip.py` en solo, avec `invest_stall=1`
et `probes=6`. Première phase : six ans, **72 sauvegardes**. La sauvegarde
du **1er février 1975** a été rechargée, puis la partie a poursuivi un an,
produisant **13 sauvegardes**. Rapport `status=OK` ; preuve positive
`LOAD_RECONCILE` présente ; aucun marqueur moteur d'échec Save/Load.
Le harnais signale une compagnie fantôme au rechargement, phénomène déjà
documenté dans ce script ; les compteurs bruts `VEHS` de son résumé ne
sont pas des comptes de trains qualifiés.

**Limite majeure :** cette reprise ne prouve pas que la sauvegarde
contenait `_railLongV2Pending` avec `investStall=true`. Aucune transaction
physique d'extension n'ayant été observée dans les duels, le **Save/Load
pendant une pose**, le rollback de tuiles réellement bâties et l'absence
d'orphelins après un échec n'ont **pas** de validation dynamique.

## Décision et suite ciblée

**NO-GO d'adoption de cette révision** : extension de quais **non exposée**,
aucune preuve économique robuste, sûreté transactionnelle partiellement
couverte par les contrats seulement. `invest_stall=0` reste le défaut.
Suite justifiée : détailler sans changement comportemental les motifs de
`unsafe_or_busy` (transaction concurrente, état de ligne, partage de gare,
géométrie, longueur), puis produire un cas reproductible où `kind=platform`
atteint la phase de devis et de pose. Sur cette preuve, tester Save/Load
en phases `intent_a`, `intent_b`, `commit` et `rollback` et comparer les
tuiles réellement présentes avant/après. Une nouvelle version comportementale
exige son propre bundle et ses portes appariées avant adoption.
