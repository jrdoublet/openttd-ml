# T8 — Revue des rames : moteur, wagons, longueur, clonage (4 novembre 2026)

## Résumé

1. **INVEST-STALL, 0 complément sur 37 : point d'abandon exact trouvé et corrigé.**
   - Où : `task_v284.nut:614`, revalidation au dépôt.
   - La garde « composition homogène » exige `AIEngine.GetCapacity(<locomotive>) == 0`. Or
     l'API rend **−1** pour une locomotive sans cargo, ce que la sous-sonde moteur du 04/11 a
     mesuré dans 10 cas sur 10, avec marge positive et wagons identiques.
   - Correction F1 : `<= 0`, le prédicat déjà utilisé par la sélection
     (`invest_stall_fleet.nut:351`, `:433`), V284 (`:150`), V257 et RAIL-LONG v3.
   - Opt-in (`invest_stall=0`) : **aucun changement de défaut**.
2. **Choix de locomotive (Q1)** : le catalogue maximise la vitesse de croisière **sur le plat**,
   à poids chargé, puis départage par l'accélération à mi-vitesse. La pente n'entre ni dans le
   choix courant ni dans le coût A\* (T4-02). Une rame qui atteint juste sa vitesse maximale sur
   le plat peut ramper en côte (b).
3. **RAIL-LONG v3 (Q2) : l'idée n'a pas été testée.**
   - L'exposition est restée médiane à **3 wagons et 90 unités** (cibles : 8 et 200).
   - Aucune multi-locomotive n'a été assemblée.
   - 5 modernisations sur 5 ont été annulées.
   - Le sélecteur de traction prend la motrice **la moins chère** qui tient 35 km/h en pente
     maximale, ce qui donne des rames longues lentes (T8-02).
4. **Renouvellement (Q4)** : autorenouvellement de la compagnie actif (6 mois avant la fin de
   vie, sans seuil de caisse). V257 change de modèle sur critère économique. Les wagons sont
   achetés par cargo, sans refit à faire. Pas de rames vieilles laissées par défaut. V257 peut en
   revanche **raccourcir** une rame longue (déjà documenté dans RAIL-LONG).
5. **Écart avec AAA** (10 à 13 wagons et 2 à 3 motrices, contre 2 à 4 wagons et 1 motrice) : il
   vient du dimensionnement (T5-01) et de l'absence de motorisation multiple au défaut, pas d'un
   plafond logiciel. Des rames à 13 wagons existent déjà (RAIL-LONG v2, `fleet_done` 12→13).

## Périmètre et provenance

- **Référence** : `8268b653`.
- **Livraison** : branche `cloud/revue-rail-T8-20261104`.
- **Lecture ciblée** :
  - `catalog.nut:20-130` et `:320-392` ;
  - `economy.nut:193-320` ;
  - `rail_long_v3*.nut` (sélecteur, constructeur) ;
  - `task_v284.nut:540-640` ;
  - `invest_stall_fleet.nut` (gardes de capacité) ;
  - `task_v257.nut:340-400` ;
  - `main.nut:770-776` ;
  - `rail_templates.nut` et `double_grow_fleet.nut` en survol (clonage : mêmes gardes `> 0`).
- **Documents** : `docs/invest_stall_obstacles_20261104.md`,
  `docs/invest_stall_diagnostic_p0_20261104.md`, `docs/rail_long_20261103.md`.

## Constats, triés par gain attendu

Classes : **(a)** certain dans le code ; **(b)** probable ; **(c)** à vérifier en moteur.

| ID | Classe / gravité | Emplacement (`8268b653`) | Défaut | Correction | Gain attendu |
|---|---|---|---|---|---|
| T8-03 | **(a) mesuré** ; bloquant pour INVEST-STALL | `task_v284.nut:614` | `homogeneous = GetCapacity(GetEngineType(oldVehicle)) == 0` est toujours faux pour une locomotive (−1). Chaque complément choisi fait `pick` → `approach` → `depot` → `invest_stall_recheck` → `rolled_back`, avec 13 à 68 jours de détour. Sous-sonde : 10/10 refus sur cette seule clause, `wagon_mismatches=0`, marge positive | **F1 codé** : `<= 0` (même prédicat que tous les autres sites). Les wagons restent comparés un à un | Débloque INVEST-STALL (opt-in). Avant toute adoption, smoke puis portes A/B ; le gain économique reste à prouver |
| T8-02 | (b) ; perte de profit sous RAIL-LONG v3 | `rail_long_v3_multi.nut:96-120` | Seuil plancher de 35 km/h en pente, puis **coût minimal** (achat + 5 ans d'entretien), la vitesse ne servant qu'à départager. Le moteur le plus lent et le moins cher qui « passe » est retenu ; le revenu, qui dépend du temps de trajet, n'est pas comparé | Choisir par profit (revenu au temps de trajet de chaque configuration, moins le coût), comme le catalogue | Conditionne toute reprise de v3 |
| T8-01 | (b) ; perte de profit | `catalog.nut:324-386` (et la boucle livrée équivalente) ; `economy.nut:248` | Choix de motrice : plus forte vitesse de croisière **sur le plat**, à pleine charge. Aucune réserve de traction pour la pente (`train_slope_steepness`, 3 % par défaut). Une rame lourde, et a fortiori une rame allongée par RAIL-FILL ou RAIL-LOOP, peut perdre beaucoup de vitesse en côte | Opt-in : départager les motrices sur la vitesse soutenable à la pente maximale (formule déjà écrite dans `OpexRailLongV3MultiGradeSpeed`), au moins dès 6 wagons | À mesurer (vitesse moyenne chargée contre nombre de tuiles en pente, avec la mesure T4/T5) |
| T8-04 | (a) ; interaction | `task_v257.nut:81-103`, `:206-253` | V257 élit le maximum `revenu − entretien` d'**une** motrice sur toutes les longueurs. Il peut raccourcir une rame longue posée par RAIL-LONG ou RAIL-FILL (documenté dans `rail_long_20261103.md` §903) | Exclure de V257 les rames marquées longues (v3 le fait déjà pour ses multi-têtes) | Préserve l'effet des allongements |
| T8-05 | (a) ; style | `invest_stall_fleet.nut:95` | La télémétrie `loco_capacity` lit la même valeur −1 : utile pour le diagnostic, sans effet | — | — |

### T8-03 — Preuve et correctif

```squirrel
// 8268b653, task_v284.nut:614
local homogeneous = AIEngine.GetCapacity(AIVehicle.GetEngineType(oldVehicle)) == 0;
// branche T8
local homogeneous = AIEngine.GetCapacity(AIVehicle.GetEngineType(oldVehicle)) <= 0;
```

Mesure moteur (`docs/invest_stall_diagnostic_p0_20261104.md`) :

| Graines 17 et 65537, 1×6 chacune | Valeur |
|---|---|
| Refus `invest_stall_recheck` | 10 |
| … avec `loco_capacity=-1`, `wagon_mismatches=0` | **10** |
| … avec `margin_detail=positive` | 10 |
| `done` | 0 |

Partout ailleurs, le code teste `> 0` pour exclure les automotrices
(`invest_stall_fleet.nut:351`, `:433`, `task_v284.nut:150`, `task_v257.nut:368`,
`rail_long_v3_upgrade.nut:163`, `v233_long_good.nut:3063`). Le test
`test_every_loco_capacity_guard_now_uses_the_same_predicate` interdit désormais `== 0` / `!= 0`
sur cette expression.

**Seconde cause d'échec, hors correctif** : `approach_timeout` (6 sur 37). La rame doit passer
**vide** à 8 tuiles du dépôt (`task_v284.nut:515-529`). La piste P1 de
`invest_stall_obstacles_20261104.md` §2 s'applique.

## Réponses aux questions

1. **Traction.** Le modèle physique est fidèle sur le plat (force = min(effort, puissance/v),
   résistances d'OpenTTD, poids plein). La pente est absente du choix courant et du coût A\*. Des
   rames sous-motorisées en côte sont donc possibles, et probables pour les rames longues (T8-01).
   Seul RAIL-LONG v3 calcule une vitesse en pente.
2. **RAIL-LONG v3.** Une exposition insuffisante plus des défauts de conception :
   - le sélecteur vise le coût et non le profit (T8-02) ;
   - V257 raccourcit les rames (T8-04) ;
   - les quais restent courts, faute d'un quai minimal (T5-01) ;
   - 5 modernisations sur 5 ont échoué (`build_a`, `build_b_or_commit`, `send_to_depot`).

   Il n'y a pas eu de « devis rejeté » massif, mais 59 rejets de traction, surtout pour la caisse
   (`rail_long_v3_multi.nut:102-106`, marge de 50 k£).
3. **INVEST-STALL, 0 sur 37.** `task_v284.nut:614` (T8-03), sortie `invest_stall_recheck` à
   `:629`. Second motif : `approach_timeout`.
4. **Renouvellement et refit.**
   - `SetAutoRenewStatus(true)`, `-6` mois, `money=0` (`main.nut:774-776`) : renouvellement à
     l'identique.
   - V257 change de modèle si le gain sur la vie restante couvre le coût.
   - Pas de refit : chaque wagon est acheté pour son cargo (`wagonByCargo`), plus un second cargo
     V163.
   - Aucune rame vieille ni wagon de mauvais type n'est attendu au défaut.

## Changement livré

- **F1** dans `task_v284.nut`, chemin INVEST-STALL seulement : `invest_stall=0` par défaut, donc
  aucun changement de défaut.
- **Projection OFF** : `sweeps/revue_rail_t8_off.py` en tête de chaîne. Les tests RAIL-LOOP,
  RAIL-FILL et RAIL-KEEP retirent d'abord cette couche ; les empreintes INVEST-STALL restent
  vérifiées par la chaîne.
- **Tests** : `sweeps/test_revue_rail_T8_20261104.py`, 11 tests.
- **Suite complète** : 3 418 tests, **mêmes 4 échecs et 12 erreurs préexistants**.

## Plan de banc pour le PC

```powershell
$ref = 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1]'
$is  = 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1,invest_stall=1]'
$aaa = @('--aaahogex-setting','disable_veh_roadveh=1','--aaahogex-setting','disable_veh_tram=1',
         '--aaahogex-setting','disable_veh_ship=1','--aaahogex-setting','disable_veh_aircraft=1')
docker run --rm --cpus=10 --memory=8g --memory-swap=8g -v openttd-lab-home:/home/lab -v "${PWD}:/work" -w /work openttd-lab `
  python3 sweeps/bench_v2.py --arms "OpexAI[invest_stall=1,decision_log=1]" --seeds 42 --years 1 --max-workers 1 `
  --out results/revue_t8_smoke_1x1_20261104.json
# Smoke 4x6 rail seul : INVEST-STALL ON (branche T8) contre référence
python -X utf8 sweeps/run_c66_reference.py --campaign revue_t8_smoke_4x6_20261104 `
  --policy-id reference --variant-policy-id revue_t8_is --reference $ref --variant $is `
  --decision-rule gain_short --min-useful-primary-delta-pct 4 --required-seeds 4 --required-years 6 `
  --years 6 --seeds 17 512 314 8191 --probes 6 --script-debug --line-telemetry `
  --mount-root 'C:\Users\jr\vscode\openttd-ml\openttd-ml' --cpus 10 --memory 8g --max-workers 10 `
  --value-guard-max-loss-pct 100 --out results/revue_t8_smoke_4x6_20261104.json @aaa
Get-ChildItem results\revue_t8_smoke_4x6_20261104_engine\*revue_t8_is*.log | ForEach-Object {
  $p = (Select-String $_ 'INVEST_STALL event=pick .*route=fleet').Count
  $d = (Select-String $_ 'INVEST_STALL event=done .*route=fleet').Count
  $r = (Select-String $_ 'reason=invest_stall_recheck').Count
  $t = (Select-String $_ 'reason=approach_timeout').Count
  "$($_.Name) pick=$p done=$d recheck=$r approach_timeout=$t" }
```

| Critère | Attendu |
|---|---|
| Santé | 8/8, 0 erreur NoAI |
| `done route=fleet` | > 0 (contre 0 avant F1) ; `recheck` en forte baisse |
| Compositions | Wagons ajoutés visibles dans `line-telemetry` (capacité par rame en hausse) |
| Économie | Smoke seulement. INVEST-STALL reste opt-in : porte A 40×3, puis porte B 20×10 avant toute adoption |
