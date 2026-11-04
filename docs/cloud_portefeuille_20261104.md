# Portefeuille, recherche et arrêt d'investissement — revue cloud du 4 novembre 2026 (Prompt 3)

Sujet : « portefeuille ». Pourquoi OpexAI cesse-t-il d'ouvrir des lignes après 1973 avec des
millions en caisse, alors qu'AAAHogEx continue de croître ?

Session cloud **sans Docker ni OpenTTD** ; aucun résultat des bancs RAIL-FILL n'a été attendu.
Les sources sont le pack `docs/cloud_pack_20261104/`, les rapports du 2 au 4 novembre et
l'historique de `docs/taches.md`. Les références `fichier:ligne` portent sur `ai/OpexAI/` au
commit `80df60e`, qui inclut `rail_loop=1` par défaut et RAIL-FILL opt-in. **Aucun défaut n'est modifié** : le
nouveau réglage `rail_expand_keep` vaut 0, et sa projection OFF redonne octet pour octet les
cinq fichiers câblés.

## 0. Résumé

1. **Le nombre de lignes n'est pas l'écart.** Fin 1975, OpexAI exploite **41 à 48 lignes** rail
   (bras OFF de `docs/v190_eco_20261103.md` §2) ; AAAHogEx en exploite **19 à 32**, avec 32 à 61
   trains (§6 du même rapport). AAA gagne avec **moins de lignes, plus de trains par ligne et des
   rames plus longues**. Ouvrir encore des lignes après 1973 est le levier le plus faible : il a
   été mesuré de nombreuses fois, toujours neutre (§1).
2. **`origin_served` n'est pas trop stricte au sens « nouvelle ligne ».** La relâcher a été
   mesuré nul : `rail_origin_reuse=1` donne **147 lignes posées contre 144**, puis −30,7 k£/an
   (`docs/suppressions_parametres_idees_20261017.md` §9.1). Les exceptions ciblées restent faibles :
   - RAIL-SIBLING : +22 k£/an ;
   - RAIL-OPEN : +21 k£/an à 5 ans, +61 k£/an à 10 ans ;
   - deuxième gare INVEST-STALL : 2 `build_ok` seulement.

   Une industrie sous-transportée doit recevoir **plus de capacité sur sa ligne existante**, pas
   une seconde ligne qui partage la même production.
3. **Le créneau A\* unique n'est pas la contrainte après 1973.**
   - Les refus `search_in_progress` ne sont que des reports : 33, 31 et 32 par an pour 4 graines
     en 1973-75.
   - Plusieurs créneaux (V184) et des workers A\* (V149, 20/10) ont déjà été mesurés inutiles.
   - RAIL-SEARCH-PRIO a **aggravé** les choses (−325 k£/an) en préemptant le mauvais travail :
     64 recherches d'« upgrade » interrompues, 24 trains de moins (200 → 176), soit 1,14 → 1,04
     train par ligne, pour à peine 7 lignes de moins.
4. **Fait nouveau identifié dans le code.** Quand V284 crée son état, il faut déjà 3 ans et 1 M£
   de caisse (`task_v284.nut:122`), ce qui arrive en 1975 en moyenne. À ce moment,
   `task_rail.nut:652` **saute toutes les lignes fret** dans `_expandRailLines`. Cela coupe :
   - le doublement « Cas 2 » (seconde voie indépendante et second train) ;
   - le « Cas 1 » (second train sur une double existante).

   La coupure tombe exactement quand la caisse devient oisive. La remplaçante V284 (+1 wagon par
   mois pour toute la compagnie ; second train seulement au quai plein, avec évitement et 1 M£)
   ne rouvre presque rien. Sous RAIL-FILL, la coupure arrive dès 250 k£.
5. **Correction codée : RAIL-KEEP** (`rail_expand_keep=1`, défaut 0). Une fois V284 actif, seule
   la ligne de **la transaction V284 en cours** est exclue ; les autres lignes fret gardent le
   parcours historique, avec toutes ses gardes. Avant l'activation de V284, rien ne change, donc
   **1970-72 n'est pas touché**.

## 1. Diagnostic par expérience

Catégories : (a) idée réfutée ; (b) implémentation défaillante ; (c) mesure non concluante.

### 1.1 RAIL-SEARCH-PRIO (`rail_search_prio=1`)

**Verdict : (b) mauvaise victime, et (a) pour « le créneau est le goulot ».**

| Mesure | Référence | PRIO |
|---|---:|---:|
| Δ profit_year | — | **−325 k£/an** (0V/4D) |
| Lignes | 176 | 169 (−4 %) |
| Trains | 200 | **176** (−12 %) |
| Trains par ligne | 1,14 | 1,04 |
| Préemptions `preempt:upgrade` | — | 64 |
| Recherches d'upgrade démarrées | — | 85 |

Source : `docs/rail_search_prio_20261103.md`, annexes.

**Lecture.**
- Les ouvertures de lignes sont restées les mêmes : le créneau n'était pas la contrainte des
  projets.
- Ce qui a disparu, ce sont les **seconds trains des doublements Cas 2**, interrompus avant la fin
  puis recommencés de zéro.
- Ordre de grandeur, **par inférence** : 24 trains × environ 13 k£ ≈ 310 k£, cohérent avec
  −325 k£. Les 7 lignes en moins ne sont pas ventilées séparément.

Avec V190, l'écrasement du créneau décrit dans `docs/cloud_double-voie_20261104.md` §1.1
s'ajoute : 141 lignes et −410 k£/an.

### 1.2 Épuisement des origines (`origin_served`, `both_ends_served`)

**Verdict : (a) pour « relâcher `origin_served` donne du volume ».**

**Autopsie de référence** (`docs/invest_stall_20261103.md`, 4 graines) :

| Mesure | 1973 | 1974 | 1975 |
|---|---:|---:|---:|
| Rejets `origin_served` (événements répétés) | 11 169 | 13 420 | 13 115 |
| Projets choisis | 33 | 14 | 9 |
| Lignes construites | 24 | 11 | 3 |
| Refus pour argent insuffisant | 2 | 0 | 0 |

La caisse n'est pas la contrainte.

**Rejets des bras exposés** (`logs_rds_failclosed_smoke_4x6`, bras proche de la référence) :
- **2 338 `too_close_no_join`** pour 351 constructions ;
- **2 198 `RAIL_OPEN_REJECT both_ends_served`**.

Dans le diagnostic du 03/11, les rejets `too_close_no_join` portent sur **162 identités
seulement**, reproposées sans cesse. Les `PROJECT_DISCARD` ne sont publiés que lors d'une passe
qui choisit un projet (`task_rail.nut:449-452`) : les comptes sont **sous-estimés** pour les
passes sans choix.

**Déjà mesuré, à ne pas rouvrir sans fait nouveau :**

| Levier | Résultat | Source |
|---|---|---|
| Filtrer la proximité avant le TOP_K (`rail_cached_proximity_gate=2`) | Porte A 40×5 +42,7 k£/an, 22/18, `fail_primary` | `docs/taches.md` : « ne doit pas être repris » |
| Relâcher l'exclusion de l'origine (`rail_origin_reuse`, retiré le 17/10) | Nul : 147 lignes contre 144 | §9.1 du rapport de suppressions |
| `MIN_SEPARATION` | Écarté le 29/08, puis « no-op mesuré » | `journal_2026-08-29.md`, `journal_2026-09-13.md` |
| Destination partagée (V178/V179) | V178 adopté ; « l'offre de candidats à destination partagée n'est plus le goulot » | `docs/taches.md` |

**Cause de fond.** Chaque gare interdit un disque de 10 cases (`main.nut:72`). Les industries
restantes proches du réseau sont des sources déjà desservies, des destinations prises, ou des
paires plus faibles. Le vivier résiduel après 1973 est maigre **par construction**, et ce qui
reste est moins rentable. C'est cohérent avec RAIL-OPEN : +3 véhicules par graine sur 5 ans.

### 1.3 RAIL-SIBLING (`rail_sibling=1`) et RAIL-OPEN (`rail_open=1`)

**Verdict : (c) mécanisme sain mais petit, et (a) pour « c'est la voie de croissance ».**

**RAIL-SIBLING.**
- 40×5 : +22 k£/an, 22V/18D, p = 0,47.
- **57 paires physiques** à origine partagée sur 32 graines ; les 57 sommes de paire sont
  positives.

**RAIL-OPEN.**
- 40×5 : +21 k£/an, 23V/17D.
- 20×10 rail : +61 k£/an, 13V/7D, p = 0,33, non-érosion.
- Intégré contre nu : rail 40×5 +12,5 k£ (20V/20D), multimodal 20×10 +37,6 k£ (10V/10D).

**La caisse continue de dormir.** Dans le 20×10 rail, elle atteint 6,66 M£ dans les deux bras en
1979. Les véhicules ne passent que de 50,0 à 52,9 (1975), puis de 52,5 à 55,9 (1979).

### 1.4 Graines systématiquement perdantes (314, 8191, 512, 746035, 232037, 100, 1024, 1337)

**Verdict : (a) pour une cause « portefeuille ».**

Le profit d'Opex y est **le même qu'ailleurs** (1,1-1,9 M£, 38-56 véhicules). Ce sont les cartes
où AAA monte à 50-70 véhicules à environ 60 k£ par véhicule (`docs/point_9h_20261103.md`). Opex
perd là où une route peut porter beaucoup de trains, donc sur la **capacité par ligne**, pas sur
le nombre d'origines. Les meilleures graines sont celles où AAA reste petit.

## 2. Réponses aux questions du prompt

**`origin_served` est-elle trop stricte ?** Pas pour ouvrir une **nouvelle ligne** : c'est mesuré
nul. Elle l'est pour la **capacité**. Une industrie qui produit plus que ce qu'on transporte doit
recevoir :
- plus de rames sur sa ligne : RAIL-LOOP, défaut depuis `a8cfb1e` ;
- des rames plus longues : RAIL-FILL ;
- un second train : Cas 2, qui est justement coupé par V284 (§0.4).

Plus de capacité fait monter la note de gare, donc le fret capté. C'est exactement ainsi qu'AAA
grandit (graine 512, service `rail|22,34` : de 2 à 9 rames en 14 mois).

**L'ordonnanceur est-il sous-dimensionné ?** Non après 1973 : peu de reports, ouvertures
inchangées sous PRIO, multi-créneaux et workers déjà mesurés inutiles. Deux règles en découlent :
- **ne jamais préempter un upgrade**, dont le travail est perdu et le second train jamais posé ;
- **ne jamais laisser une recherche secondaire écraser `_railSearch`** (bug V190,
  `task_rail.nut:644` → `:730` → `:1832`).

**Comment AAA choisit-il ses routes** (`main.nut`, `estimator.nut:1767-1811`, lectures
documentées) ?
- Comparaison simple contre double d'une même route.
- Réutilisation d'une source en **ajoutant des trains** (`trainroute.nut:970-1008`) ou une
  destination par extension (`TrainRouteExtendBuilder`).
- Budget ROI lié à la caisse disponible, y compris le crédit non tiré (`main.nut:4203-4252`).

AAA n'ouvre pas plus de routes qu'Opex : il les **remplit**.

## 3. Corrections proposées, classées par gain attendu / risque

| Rang | Correction | Gain attendu | Risque | État |
|---:|---|---|---|---|
| 1 | **RAIL-KEEP** : V284 actif n'exclut plus que sa propre ligne de `_expandRailLines` ; le doublement Cas 1/2 continue ailleurs | Moyen à élevé sur 10 ans, puisque PRIO a montré environ 13 k£ par second train ; nul avant l'activation de V284 | Faible : parcours historique inchangé, une seule garde déplacée | **Codé**, `rail_expand_keep=1`, défaut 0 |
| 2 | **Ne jamais préempter ni écraser une recherche d'upgrade** : garde `_railSearch == null` avant `_startRailUpgradeSearch` (`task_rail.nut:708-730`) sous V190 ; abandonner `rail_search_prio` | Rend V190 et FIX2 mesurables | Très faible | Non codé (V190 et PRIO sont des opt-in non recommandés) ; patch d'une ligne dans `docs/cloud_double-voie_20261104.md` §3 |
| 3 | **Réseau en étoile avec transfert** (hub et rabattements, `OF_TRANSFER`), comme AAA (V226) : réutiliser une gare existante comme tronc, une fois la double voie disponible | Élevé à long terme | Élevé : chantier, pas un réglage | Non codé. RAIL-LOOP étant désormais par défaut, le prérequis « tronc multi-rames » existe |

**Pourquoi pas un nouveau relâchement du vivier.** Le filtre amont de proximité, la réutilisation
d'origine et `MIN_SEPARATION` sont mesurés ou écartés (§1.2). Sans fait nouveau, les rouvrir
contreviendrait à AGENTS.md §1.5.

## 4. Code livré (réglage `rail_expand_keep`, défaut 0)

### Fichiers

| Fichier | Rôle |
|---|---|
| `ai/OpexAI/rail_keep.nut` | `OpexRailExpandKeepSkip(owner, line)` : vrai seulement pour une ligne fret qui est celle de la transaction V284 en cours (`_v284State.pending.lineId`) |
| `task_rail.nut` (`_expandRailLines`) | `if (RAIL_EXPAND_KEEP) { if (skip) continue; } else <garde historique>`. La garde historique reste **octet pour octet** dans la branche `else`, et le contrat V284 qui la retire de son empreinte passe toujours |
| `info.nut`, `globals_pre.nut`, `settings.nut`, `main.nut` | Réglage, globale, lecture unique, `require` |
| `sweeps/rail_keep_off.py` | Projection OFF stricte, couche la plus récente, retirée en tête de chaîne avant RAIL-FILL et RAIL-LOOP |
| `sweeps/test_rail_keep_20261104.py` | 7 contrats |
| Six tests d'inventaire | Plafond d'`AddSetting` passé de 95 à 96 |

**Pourquoi c'est sûr sans autre garde.** V284 ne choisit jamais pendant une recherche d'upgrade
(`task_v284.nut`, garde `_railSearch.kind == "upgrade"`, vérifiée par contrat). Il ne prend que
des lignes simples à une rame, que le Cas 2 transforme justement en double. Le Cas 2 ne démarre
une recherche que si `_railSearch` est libre (`task_rail.nut:644` hors V190). Les deux mécanismes
ne touchent donc pas la même ligne au même moment.

### Validations faites dans cette session

- Suite complète : **3 407 tests**, mêmes 17 échecs/erreurs qu'avant intervention, aucun nouveau.
- Contrats RAIL-KEEP 7/7 ; avec RAIL-FILL et RAIL-LOOP, 40/40. Les projections composées
  redonnent les SHA du commit `47395b4`.
- `git diff --check` propre.
- **Non compilé** : le smoke 1×1 sur le PC est la première exécution réelle.

## 5. Risques à surveiller

1. **Concurrence pour la caisse avec V284.** Une fois V284 actif, la caisse dépasse 1 M£ : risque
   faible.
2. **Concurrence avec RAIL-LOOP**, désormais par défaut. Les deux visent les lignes simples à une
   rame avec de la cargaison en attente :
   - RAIL-LOOP passe en premier ;
   - les lignes `railLoop > 0` sont sautées par la boucle historique.

   À mesurer : boucles certifiées contre doublements Cas 2, dans les deux bras.
3. **Lignes Cas 2 sorties de V284 et de RAIL-FILL.** Elles ont `doubleTrack=1` : le compromis
   « plus de trains contre rames plus longues » est voulu, mais doit être lu par ligne.

## 6. Plan de bancs pour le PC (PowerShell, depuis la racine)

Le code est sur `ccr-6d627d08-tlnphk`. L'activation de V284 arrive vers 1975 au défaut : un 4×6
n'expose que la fin de partie. Le smoke est donc fait sur **10 ans**, et un second smoke combine
RAIL-FILL, qui active V284 dès 250 k£.

```powershell
$ref = 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1]'
$on  = 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1,rail_expand_keep=1]'
$aaa = @('--aaahogex-setting','disable_veh_roadveh=1','--aaahogex-setting','disable_veh_tram=1',
         '--aaahogex-setting','disable_veh_ship=1','--aaahogex-setting','disable_veh_aircraft=1')
$common = @('--mount-root','C:\Users\jr\vscode\openttd-ml\openttd-ml',
            '--cpus','10','--memory','8g','--max-workers','10',
            '--start-year','1970','--map-size','8','--repeats','1','--primary-metric','profit_year')

# 0. Contrats
python -X utf8 -m unittest discover -s sweeps -p 'test_rail_keep_20261104.py'

# 1. Compilation 1x1 (solo)
docker run --rm --cpus=10 --memory=8g --memory-swap=8g -v openttd-lab-home:/home/lab -v "${PWD}:/work" -w /work openttd-lab `
  python3 sweeps/bench_v2.py --arms "OpexAI[rail_expand_keep=1]" --seeds 42 --years 1 --max-workers 1 `
  --out results/rail_keep_smoke_1x1_20261104.json

# 2. Smoke physique 4x10 rail seul (graines du prompt)
python -X utf8 sweeps/run_c66_reference.py --campaign rail_keep_smoke_4x10_20261104 `
  --policy-id reference --variant-policy-id rail_keep --reference $ref --variant $on `
  --decision-rule non_erosion --min-useful-primary-delta-pct 4 --required-seeds 4 --required-years 10 `
  --years 10 --seeds 17 512 314 8191 --probes 6 --script-debug --line-telemetry `
  --retain-savegames results/rail_keep_smoke_4x10_20261104_saves `
  --value-guard-max-loss-pct 100 --out results/rail_keep_smoke_4x10_20261104.json @common @aaa

# 3. Variante combinée, activation de V284 plus tôt
python -X utf8 sweeps/run_c66_reference.py --campaign rail_keep_fill_smoke_4x10_20261104 `
  --policy-id rail_fill --variant-policy-id rail_keep_fill `
  --reference 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1,rail_fill=1]' `
  --variant   'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1,rail_fill=1,rail_expand_keep=1]' `
  --decision-rule non_erosion --min-useful-primary-delta-pct 4 --required-seeds 4 --required-years 10 `
  --years 10 --seeds 17 512 314 8191 --probes 6 --script-debug --line-telemetry `
  --value-guard-max-loss-pct 100 --out results/rail_keep_fill_smoke_4x10_20261104.json @common @aaa
```

### Critères d'exposition, tous exigés avant les portes

| # | Critère | Où le lire |
|---:|---|---|
| K1 | Après le premier `V284 action=pick` de chaque graine (activation), ON compte **≥ 2 `RAIL_EXPAND action=double_track ok=1` ou `second_train`** de plus qu'OFF sur la suite de la partie | Journaux, par année |
| K2 | Trains par ligne fret ON > OFF à partir de l'année suivant l'activation | `line_telemetry` |
| K3 | Avant l'activation, mêmes décisions : `RAIL_BUILD`, `PROJECT_CHOSEN` et `RAIL_EXPAND` par année ON = OFF jusqu'au premier `V284 action=pick`, à la dérive d'opcodes près | Journaux |
| K4 | Aucune transaction V284 annulée parce qu'un doublement a touché sa ligne ; `V284 ... cancel` ON ≤ OFF | Journaux |
| K5 | Santé : 8/8 parties, 0 erreur NoAI | Manifeste, journaux |

### Portes, si K1 à K5 tiennent

```powershell
# Porte A — 40x5 (prompt) ; V102 : 40x3 pour une adoption. Effet tardif : A risque d'être neutre
python -X utf8 sweeps/run_c66_reference.py --campaign rail_keep_gain_short_40x5_20261104 `
  --policy-id reference --variant-policy-id rail_keep --reference $ref --variant $on `
  --decision-rule gain_short --min-useful-primary-delta-pct 4 --required-seeds 40 `
  --required-years 5 --years 5 --probes 6 --script-debug --line-telemetry `
  --value-guard-max-loss-pct 5 --out results/rail_keep_gain_short_40x5_20261104.json @common @aaa

# Porte B — 20x10 non_erosion
python -X utf8 sweeps/run_c66_reference.py --campaign rail_keep_non_erosion_20x10_20261104 `
  --policy-id reference --variant-policy-id rail_keep --reference $ref --variant $on `
  --decision-rule non_erosion --min-useful-primary-delta-pct 4 --required-seeds 20 `
  --required-years 10 --years 10 --probes 6 --script-debug --line-telemetry `
  --value-guard-max-loss-pct 5 --out results/rail_keep_non_erosion_20x10_20261104.json @common @aaa
```

**Lecture attendue.** Le mécanisme n'agit qu'après l'activation de V284 (1975 en moyenne au
défaut), donc la porte A à 5 ans a peu de chances de montrer +4 %. C'est la porte B à 10 ans qui
tranche. Si l'utilisateur veut un parcours d'adoption, combiner avec RAIL-FILL (activation dès
250 k£) est le moyen de rendre la porte A informative. Lire le Δ `profit_year` propre d'Opex, et
pas le ratio contre AAA.
