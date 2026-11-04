# Capacité par rame et réinvestissement — revue cloud du 4 novembre 2026 (Prompt 2)

Sujet : « capacité-rame ». Pourquoi les rames d'OpexAI restent-elles courtes et sa caisse
dort-elle, alors qu'AAAHogEx transporte 240 unités par rame contre 90 ?

Session cloud **sans Docker ni OpenTTD** : rien n'a été joué en moteur. Les chiffres viennent de
`docs/cloud_pack_20261104/` et des rapports du 3-4 novembre. Les références `fichier:ligne`
portent sur `ai/OpexAI/` au commit `47395b4`. **Aucun défaut n'est modifié** : le nouveau réglage
`rail_fill` vaut 0, et sa projection OFF redonne octet pour octet les huit fichiers câblés.

La source AAAHogEx‑115 n'est ni versionnée ni téléchargeable depuis cette session (voir
`docs/cloud_double-voie_20261104.md`). Ses lignes `trainroute.nut:970-1008` et `2957-2988` sont
connues par les lectures documentées dans `docs/v190_eco_20261103.md` §6.

## 0. Résumé

1. **Les rames longues ne sont presque jamais exposées.** Dans toutes les campagnes, la médiane
   des rames fret en service reste à **3 wagons** :
   - RAIL-LONG v2 4×10, 1970-1979, avec la variante ;
   - RAIL-LONG v3 4×6, en décembre 1975.

   RAIL-LONG v3 construit bien des lignes longues neuves : 278 sur 40 graines × 5 ans. Mais le
   parc posé en 1970-72 reste court :
   - **11 modernisations** seulement sur 40 graines (porte A 40×5) ;
   - **1 multi-traction assemblée** sur 1 209 choix, dont 447 refus de caisse.

   L'idée n'est donc pas réfutée : elle n'a pas été testée sur le parc (c).
2. **Le dimensionnement est auto-confirmant (b).** La demande utilisée pour choisir la taille
   d'une rame est le fret **déjà livré**, donc plafonné par la rame actuelle :
   - V257 : `task_v257.nut:316`, `:490` et `:99` ;
   - la note retenue est celle observée ou une constante de calibration (`economy.nut:265-274`).

   Une rame courte justifie donc une rame courte. À revenu égal, V257 départage **par le prix**
   (`task_v257.nut:246`) et choisit la rame la plus courte. Ce comportement est observé : dans
   RAIL-LONG v1, les deux rames longues ont été raccourcies à 1 et 2 wagons.
3. **La croissance de rame existe déjà (V284, actif par défaut) mais elle est verrouillée** :
   - pas avant trois ans de partie, et **1 M£ de caisse** exigé (`task_v284.nut:122`) ;
   - un choix par mois pour toute la compagnie (`:127`) ;
   - **un seul wagon** par transaction (`:185`).

   À 5 ans, la caisse vaut 1,2 à 2,0 M£ : V284 démarre à peine.
4. **INVEST-STALL n'a jamais acheté un wagon, à cause d'un bug (b).** La revalidation exige
   `AIEngine.GetCapacity(locomotive) == 0` (`task_v284.nut:605`), alors que l'API renvoie
   **−1** pour une locomotive sans cargaison. Les 10 refus mesurés en sont tous la conséquence,
   avec une marge positive. Le commentaire de V257 (`task_v257.nut:227-228`) documente déjà ce
   piège.
5. **Correction codée : RAIL-FILL** (`rail_fill=1`, défaut 0). C'est un mode de V284 qui
   **remplit les quais existants**, puisqu'un quai de 4 cases porte 7 wagons :
   - porte de caisse à 250 k£ ;
   - taille visée calculée sur la **production réelle** de l'industrie, à 75 % de note, pour
     1,5 cycle ;
   - traction sans perte de vitesse ;
   - la rame remplie n'est plus revue par V257.

   La transaction V284 déjà éprouvée en moteur est réutilisée telle quelle.

## 1. Diagnostic par expérience

Catégories : (a) idée réfutée ; (b) implémentation défaillante ; (c) mesure non concluante.

### 1.1 RAIL-CONSIST 200 % (`rail_consist_pct=200`)

**Verdict : (b) mauvais moment d'investissement, et (c) pour l'idée.**

**Mécanisme.** Le réglage double l'offre de calibration avant le calcul du nombre de wagons des
**lignes neuves** (`economy.nut:272-274`). La taille reste bornée par le quai : 3 à 4 cases,
soit 5 à 7 wagons.

**Résultats.**
- 40×5 rail seul : **−61 k£/an**, 17V/23D, p = 0,13.
- Smoke 2×2 : −81 k£.

**Trace d'éviction de capital.** Le smoke 2×2 compte **64 `cash_at_build` pour 72 constructions**
(0,89 par construction). Les smokes de référence en comptent environ 0,6 :
- `rds_failclosed_smoke_4x6` : 204 pour 351 ;
- RAIL-LONG v3 r3 : 208 pour 348.

Doubler le matériel des lignes neuves en 1970-72, quand la caisse est la contrainte, retarde le
réseau. L'expérience ne dit rien d'une rame plus longue **payée par une caisse oisive**.

### 1.2 RAIL-LONG v1 (`rail_long=1`)

**Verdict : (c) exposition quasi nulle, et (b) annulation par V257.**

- Smoke 4×6 : **2 constructions longues** en tout (`RAIL_LONG event=build` = 2), −50 puis
  −37 k£/an.
- **V257 a raccourci les deux rames longues** (`docs/rail_long_20261103.md`) :
  - graine 17, ligne 23 → **1 wagon** le 06/06/1974 ;
  - graine 841478, ligne 27 → **2 wagons** le 27/08/1974.

### 1.3 RAIL-LONG v2 (`rail_long=2`, seul ou avec `invest_stall=1`)

**Verdict : (c) exposition insuffisante, et (b) gardes trop restrictives.**

**Exposition cumulée**, tous événements ON :

| Campagne | Lignes neuves longues | Extensions A/B | Rames agrandies (`fleet_done`) |
|---|---:|---:|---:|
| Rail 20×10 | 8 | 16 | 47 |
| Rail 40×5 | 5 | 32 | 33 |

Cela fait environ **1 à 2 événements par graine** pour ~40 lignes. Résultat physique du smoke
4×10 : **3 wagons médians dans les deux bras**, chaque année.

**Gardes en cause.**
- Une seule rame par ligne et des gares non partagées (`task_rail_long_v2.nut:115-169`).
- Croissance d'**un** wagon par décision, vitesse ≥ 85 %, caisse ≥ prix + 100 k£
  (`task_rail_long_v2_fleet.nut:20-145`).

**Résultats économiques** : smoke seul −31 k ; combo +174 k (4/4) ; 20×10 +18 k ; multimodal
−120 k. Tous neutres.

### 1.4 RAIL-LONG v3 (`rail_long=3`)

**Verdict : (b) pour les modernisations et la multi-traction, (c) pour l'économie.**

| Mesure (porte A 40×5) | Valeur |
|---|---:|
| Lignes longues neuves (`build`) | 278 |
| Replis `SITE_ROI_OR_CASH` | 365 |
| Modernisations choisies / abouties (`upgrade_pick` / `upgrade_done`) | 55 / **11** |
| Échecs `send_to_depot` (corrigés ensuite par R6) | 29 |
| Multi-traction assemblée / choix | **1 / 1 209** |
| Refus de caisse sur ces choix | 447 |

**Audit physique du smoke r3 (déc. 1975)** : 27 rames d'au moins 8 wagons contre 1, mais la
médiane reste **3 wagons et 90 unités**. Le profit médian par rame passe de 16,4 k£ à 20,8 k£.

**Portes post-R6.**

| Porte | Δ profit_year | Verdict |
|---|---:|---|
| A rail | −7 k£ | `fail_primary` |
| A multimodal | −64 k£ | `fail_primary` |
| B rail | **+47 k£** | `non_erosion` |
| B multimodal | **+100 k£** | `non_erosion` |

En B multimodal, le profit croît avec le temps : de +5 k en 1972 à +94-176 k en 1976-77.

**Lecture.** Le gain n'arrive qu'à 10 ans, et seulement sur les lignes neuves d'après 1972, qui
sont rares puisque le vivier s'épuise. La correction R6 (modernisation transactionnelle et
Save/Load) est techniquement validée sur 3 reprises sur 3, mais elle ne touche presque pas le
parc existant.

### 1.5 INVEST-STALL v1-v3 (`invest_stall=1`)

**Verdict : (b) bug bloquant, et (c) pour les portes mesurées.**

**Achats de wagons.**
- 37 renforcements choisis, **0 terminé** dans le 2×8.
- Les deux smokes 1×6 du 04/11 ventilent **10/10 refus** sur la seule clause `homogeneous`.
  La valeur est **`loco_capacity=-1`**, avec `wagon_mismatches=0` et une marge positive
  (`docs/invest_stall_diagnostic_p0_20261104.md`).
- La garde `== 0` (`task_v284.nut:605`) est contraire à l'API : `ScriptEngine::GetCapacity`
  vaut −1 sans cargaison. Les autres gardes du dépôt utilisent déjà `> 0` (`:148`, `:93`).

**Quais.** `unsafe_or_busy` vient d'une gare partagée dans 20 cas sur 20 ; une recherche rail
simultanée s'y ajoute dans 10 cas.

**Économie.** Les portes v2-r2 ont été mesurées avec quasiment **aucun** achat de wagon
INVEST-STALL :

| Porte | Δ profit_year | V/D | Verdict |
|---|---:|---:|---|
| 40×5 | +5,5 k£ | 20/20 | `fail_primary` |
| 20×10 | +36 k£ | 14/6 | `pass` |

Elles mesurent les gares neuves d'origine (2 `build_ok` au 40×5) et le bruit, pas l'idée « grossir
les rames saturées ».

## 2. Réponses aux questions du prompt

**Les rames longues sont-elles construites ?** Sur les lignes neuves de RAIL-LONG v2 et v3, oui.
Sur le parc, non : la médiane reste à 3 wagons dans tous les bras mesurés. La composition est
ensuite **défaite par V257**, qui tourne par défaut (`orchestrator.nut:1020`), sauf pour les
multi-tractions v3.

**La marge et la traction sont-elles mal calculées ?** Oui, sur trois points.

1. **Demande censurée.**
   - V257 calcule `monthly = (livré annuel + attente) / (12 × rames)`
     (`task_v257.nut:316`, `:490`), puis `carried = min(capacité × trajets, capté)` (`:99`).
   - Une rame plus grande ne « voit » donc jamais le fret supplémentaire qu'elle attirerait.
   - En OpenTTD, la note de gare dépend fortement des **jours depuis le dernier chargement**.
     Une rame en chargement complet présente en permanence la maintient haute : AAA est à 212/255
     de note source (83 %), Opex à 151/255 (59 %) (`docs/point_9h_20261103.md`).
   - À revenu égal, la plus courte gagne au prix (`task_v257.nut:246`).
2. **Note constante au dimensionnement initial.** `calibrationOffered = monthlyUnits ×
   STATION_RATING_PCT` (`economy.nut:267`), pour une rame par ligne. La rame est donc taillée
   pour transporter exactement le flux calibré, sans tenir compte de la note qu'elle ferait
   monter. Le modèle de cadence `OpexStationRatingForHeadway` n'est branché que sous
   `estim_unifie & 8`, défaut 0.
3. **Marge INVEST-STALL très conservatrice.** Elle soustrait le remplacement complet et son
   amortissement (`invest_stall_fleet.nut:18-55`) : 3 045 `nonpositive_margin_or_traction` dans
   le smoke 4×10. Les wagons vanilla n'ont **pas de coût de fonctionnement**
   (`task_v257.nut:96-98`) ; un wagon de plus coûte donc seulement son prix.

Unités : la note est déjà en pourcentage dans `OpexInvestStallSourceGap` ; pas d'erreur d'année
repérée.

**Le pipeline d'achat V284 est-il trop fragile ?** La transaction elle-même est saine : approche
non bloquante, construction, copie des ordres, adoption idempotente après Load. Elle est validée
en moteur par RAIL-LONG v3 R3/R6. Ce sont **sa politique** et **un bug INVEST-STALL** qui
bloquent :
- 1 M£ et 3 ans ;
- un choix par mois pour toute la compagnie ;
- +1 wagon ;
- `== 0` sur la locomotive.

**Composition AAA** (lectures documentées). Rames de 10 à 13 wagons, souvent 2 à 3 locomotives,
quais de 7 cases, 4 à 12 rames par bonne ligne. Exemple : service `rail|22,34` de la graine 512,
passé de 2 à 9 rames en 14 mois. Ce n'est pas une rame dimensionnée pour un flux observé, mais
une offre surdimensionnée qui fait monter la note puis le trafic.

## 3. Corrections proposées, classées par gain attendu / risque

| Rang | Correction | Gain attendu | Risque | État |
|---:|---|---|---|---|
| 1 | **RAIL-FILL** : V284 remplit les quais existants dès 250 k£ de caisse, à une taille calculée sur la production réelle et une note de 75 %, avec un saut direct ; rame protégée de V257 | Élevé : touche **tout le parc** posé en 1970-72 ; capacité médiane possible de 3 à 7 wagons sans aucune construction ; financé par la caisse qui dort après 1973 | Faible à moyen : réutilise la transaction V284 éprouvée ; effets de bord au §5 | **Codé**, `rail_fill=1`, défaut 0 |
| 2 | **INVEST-STALL, garde de locomotive** : `== 0` → `<= 0` à `task_v284.nut:605` | Moyen : débloque 100 % des achats mesurés | Très faible (deux caractères) | Non codé : cela changerait le sens d'un opt-in déjà mesuré. Patch exact donné ici ; à re-mesurer par le smoke 2×8 du 04/11 sous un nom neuf |
| 3 | **Demande non censurée dans V257** : fret capté = production × note prévue, la note intégrant la présence d'une rame en chargement ; à revenu égal, départager par la capacité plutôt que le prix | Moyen, sur tout le parc et dans la durée | Moyen : V257 est actif par défaut, donc nouvel opt-in obligatoire | Non codé. RAIL-FILL contourne le problème en protégeant ses lignes |

Suite naturelle : quand une rame atteint la longueur maximale du quai, ajouter des **rames** par
RAIL-LOOP (Prompt 1). Depuis le commit `a8cfb1e`, `rail_loop=1` est le défaut, par décision
utilisateur (`docs/rail_loop_bancs_20261104.md`). L'évitement V284 (V202k : −27 k£) et l'allongement des quais
(gardes v2/v3) sont moins prometteurs. La multi-traction ne devient nécessaire qu'au-delà de 7
wagons, c'est-à-dire sur des quais de plus de 4 cases.

## 4. Code livré (réglage `rail_fill`, défaut 0)

### Fichiers

| Fichier | Rôle |
|---|---|
| `ai/OpexAI/rail_fill.nut` | Module neuf : `OpexRailFillGateClosed`, `OpexRailFillAddAllowed`, `OpexRailFillProduction`, `OpexRailFillTarget`, `OpexRailFillPlan` ; journal `RFILL` |
| `task_v284.nut` | Cinq points d'accroche, tous derrière `RAIL_FILL` |
| `task_v257.nut` | Une ligne : `_v257Review` ignore une ligne `railFill` |
| `info.nut`, `globals_pre.nut`, `settings.nut`, `main.nut` | Réglage, globale, lecture unique, `require` |
| `sweeps/rail_fill_off.py` | Projection OFF stricte, retirée en tête de chaîne avant RAIL-LOOP |
| `sweeps/test_rail_fill_20261104.py` | 13 contrats |
| Six tests d'inventaire | Plafond d'`AddSetting` passé de 94 à 95, avec justification |

### Points d'accroche dans `task_v284.nut`

1. **Porte de sélection.** Sous `RAIL_FILL` : deux ans et 250 k£. Sinon, la garde historique
   **ligne intacte**, sous forme de `else if`.
2. **Seconde rame avec évitement** : toujours conditionnée à 1 M£. Une ligne dont la conversion
   RAIL-LOOP est en cours (`railLoop == 1`) est ignorée : RAIL-LOOP est désormais actif par
   défaut.
3. **Taille** : après l'équipement +1 historique, `OpexRailFillPlan` remplace le +1 par la plus
   grande taille qui respecte ces quatre conditions :
   - au plus la cible, calculée ainsi : `production × 75 % × 1,5 cycle / capacité wagon`, bornée
     par `OpexRailNominalMaxWagons(quai)` ;
   - tenue par une locomotive sans perte de vitesse (`OpexV284Equipment`, règle V284 inchangée) ;
   - payable avec la réserve de 50 k£ de la revalidation ;
   - à défaut, retour au +1 historique.

   Inactif sous `estim_unifie & 4` et pour V233L.
4. **Marquage** : la transaction porte `railFill`, et la ligne reçoit `railFill=true` **après**
   adoption de la nouvelle rame.
5. **Revalidation au dépôt inchangée** : borne de quai, attente ≥ 1 wagon, caisse ≥ prix + 50 k£,
   traction compatible.

### Validations faites dans cette session

- Suite complète, après rebase sur `a8cfb1e` (RAIL-LOOP par défaut) : **3 400 tests**, **mêmes
  17 échecs/erreurs qu'avant intervention**, aucun nouveau. Un contrat V233L qui lisait la garde V284 a été préservé en gardant la ligne
  historique intacte.
- `test_rail_fill_20261104.py` 13/13 et `test_rail_loop_20261104.py` 20/20. Ils vérifient :
  - la projection OFF égale aux SHA du commit `47395b4` ;
  - le refus d'un hunk modifié ;
  - l'ordre des gardes ;
  - que la production vient d'`AIIndustry` et non de l'attente ;
  - l'existence et l'arité de chaque fonction `Opex*` appelée.
- `git diff --check` propre.
- **Non fait : compilation Squirrel**, faute de compilateur. Le smoke 1×1 du §6 est la première
  exécution réelle.

## 5. Risques et effets de bord à surveiller

1. **Avancement de l'état V284.** `_v284State` est créé dès que la porte passe. Or
   `task_rail.nut:650` désactive alors les cas 1 et 2 historiques (second train, double voie
   indépendante) pour **toutes les lignes fret**. Sous RAIL-FILL, cela arrive vers 250 k£ au lieu
   d'1 M£. Le Prompt 3 corrige ce verrou par RAIL-KEEP (`rail_expand_keep=1`,
   `docs/cloud_portefeuille_20261104.md`) : la combinaison `rail_fill=1,rail_expand_keep=1` est la
   variante recommandée. C'est un effet de traitement à mesurer :
   - `RAIL_EXPAND action=double_track|second_train` ;
   - trains par ligne, OFF contre ON.
2. **Vieillissement de la cargaison.** Une rame en chargement complet très longue garde le fret à
   bord. La cible de 1,5 cycle borne l'attente à environ un aller-retour. À vérifier sur le bétail
   et les marchandises : profit par rame des lignes remplies.
3. **Traction.** La règle « aucune perte de vitesse » peut bloquer les gros sauts avec les
   locomotives des années 1970. Repli : +1. Compter `RFILL action=fallback_plus_one`.
4. **Concurrence avec les projets** en 1972-73 si la caisse dépasse 250 k£ alors que le vivier
   n'est pas épuisé. À regarder : `RAIL_BUILD` et `cash_at_build`, ON contre OFF.
5. **Renouvellement.** V257 ne revoit plus les lignes remplies. Les locomotives de 1970 ne sont
   pas obsolètes en 10 ans, mais une partie plus longue demanderait un renouvellement qui
   conserve la taille (correction 3).

## 6. Plan de bancs pour le PC (PowerShell, depuis la racine)

Le code est sur la branche `ccr-6d627d08-tlnphk`. L'intégrer à `master` relève de ta décision.
**Le défaut reste `rail_fill=0`.** La référence ci-dessous n'écrit pas `rail_loop` : elle
inclut donc RAIL-LOOP, actif par défaut depuis `a8cfb1e`, et RAIL-FILL est mesuré **en plus** de
ce nouveau défaut. Pour isoler RAIL-FILL de RAIL-LOOP, ajouter `rail_loop=0` aux deux bras.

```powershell
$ref = 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1]'
$on  = 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1,rail_fill=1]'
$aaa = @('--aaahogex-setting','disable_veh_roadveh=1','--aaahogex-setting','disable_veh_tram=1',
         '--aaahogex-setting','disable_veh_ship=1','--aaahogex-setting','disable_veh_aircraft=1')
$common = @('--mount-root','C:\Users\jr\vscode\openttd-ml\openttd-ml',
            '--cpus','10','--memory','8g','--max-workers','10',
            '--start-year','1970','--map-size','8','--repeats','1','--primary-metric','profit_year')

# 0. Contrats
python -X utf8 -m unittest discover -s sweeps -p 'test_rail_fill_20261104.py'

# 1. Compilation et exécution 1x1 (solo)
docker run --rm --cpus=10 --memory=8g --memory-swap=8g -v openttd-lab-home:/home/lab -v "${PWD}:/work" -w /work openttd-lab `
  python3 sweeps/bench_v2.py --arms "OpexAI[rail_fill=1]" --seeds 42 --years 1 --max-workers 1 `
  --out results/rail_fill_smoke_1x1_20261104.json

# 2. Smoke physique 4x6 rail seul
python -X utf8 sweeps/run_c66_reference.py --campaign rail_fill_smoke_4x6_20261104 `
  --policy-id reference --variant-policy-id rail_fill --reference $ref --variant $on `
  --decision-rule gain_short --min-useful-primary-delta-pct 4 --required-seeds 4 --required-years 6 `
  --years 6 --seeds 17 512 314 8191 --probes 6 --script-debug --line-telemetry --line-telemetry-monthly `
  --retain-savegames results/rail_fill_smoke_4x6_20261104_saves `
  --value-guard-max-loss-pct 100 --out results/rail_fill_smoke_4x6_20261104.json @common @aaa

# Audit physique (outil existant)
python -X utf8 sweeps/analyse_rail_long_v3_exposure.py results/rail_fill_smoke_4x6_20261104.json `
  --saves results/rail_fill_smoke_4x6_20261104_saves --date 1975-12-01 --min-wagons 6 --min-capacity 150
```

### Critères d'exposition du smoke 4×6, tous exigés avant les portes

| # | Critère | Où le lire |
|---:|---|---|
| F1 | ≥ 2 `V284 action=done kind=wagon` par graine avec `new_wagons − old_wagons ≥ 2` | Journaux ON |
| F2 | Médiane des wagons par rame fret ON au 01/12/1975 **≥ 5**, contre 3 en OFF ; capacité médiane ≥ 150 | Script d'audit ci-dessus |
| F3 | **Aucune** ligne `railFill` raccourcie après coup : wagons et capacité ne baissent jamais d'une sauvegarde mensuelle à la suivante | Sauvegardes |
| F4 | Note source des lignes remplies : +5 points ou plus, six mois après le remplissage | `line_telemetry`, `endpoint_cargo_stats` |
| F5 | Santé : `game_ok` 8/8, 0 erreur NoAI, 0 rame `Lost` créée par une transaction RAIL-FILL | Manifeste, journaux, sauvegardes |
| F6 | Effet de bord §5.1 mesuré | `RAIL_EXPAND` et trains par ligne, OFF contre ON |

**Si F1 échoue**, lire les journaux :
- `V284 action=skip reason=traction|geometry` ;
- `RFILL action=fallback_plus_one` ;
- `V284 ... cancel` avec le motif `depot_recheck`.

### Portes économiques, si F1 à F5 tiennent

```powershell
# Porte A — 40 graines canoniques x 5 ans (le prompt dit 40x5 ; V102/CLAUDE.md : 40x3 pour une adoption)
python -X utf8 sweeps/run_c66_reference.py --campaign rail_fill_gain_short_40x5_20261104 `
  --policy-id reference --variant-policy-id rail_fill --reference $ref --variant $on `
  --decision-rule gain_short --min-useful-primary-delta-pct 4 --required-seeds 40 `
  --required-years 5 --years 5 --probes 6 --script-debug --line-telemetry `
  --value-guard-max-loss-pct 5 --out results/rail_fill_gain_short_40x5_20261104.json @common @aaa

# Porte B — 20 graines canoniques x 10 ans (si A passe)
python -X utf8 sweeps/run_c66_reference.py --campaign rail_fill_non_erosion_20x10_20261104 `
  --policy-id reference --variant-policy-id rail_fill --reference $ref --variant $on `
  --decision-rule non_erosion --min-useful-primary-delta-pct 4 --required-seeds 20 `
  --required-years 10 --years 10 --probes 6 --script-debug --line-telemetry `
  --value-guard-max-loss-pct 5 --out results/rail_fill_non_erosion_20x10_20261104.json @common @aaa
```

Ensuite seulement :
- variante sans RAIL-LOOP (`rail_loop=0` dans les deux bras), pour isoler l'effet propre ;
- correction 2 (INVEST-STALL), en smoke 2×8 sous un nom neuf ;
- multimodal 20×10.

Lire le verdict économique propre à Opex (Δ `profit_year`, V/D, p, IC95, garde de valeur), et pas
seulement le ratio Opex/AAA.
