# T7 — Revue exécution du plan et mise en service (4 novembre 2026)

## Résumé

1. **Incohérence certaine entre le devis et le constructeur (T7-01).**
   - L'économie choisit entre 1 et `MAX_RAIL_TRAINS = 2` rames par ROI, et chiffre alors une
     **voie unique** avec deux rames.
   - Sur voie unique, `OpexExecuteRailPlan` ne pose **qu'une** rame (`want = 1`). La seconde
     voie prévue par `OpexTryDoubleTrack` sort avant l'A\*, puisque les gares n'existent pas
     encore.
   - Un candidat « 2 rames » est donc classé avec un profit qu'il ne réalise pas.
2. **Mesure livrée** sous `decision_log` : `RAIL_ATTEMPT ... pred_trains= built_trains=`.
   La ligne garde déjà `predTrains`, mais aucun journal rail ne l'exposait.
3. **Ordres.**
   - Source : `OF_FULL_LOAD_ANY | OF_NON_STOP_INTERMEDIATE`.
   - Destination fret : `OF_NONE | non-stop`, soit déchargement de ce qui est accepté, puis
     retour à vide ; pour les passagers, plein aux deux bouts.
   - Aucun délai sur le plein : une source qui faiblit retient sa rame indéfiniment.
4. **Environ 1,2 rame par ligne** : une rame par voie unique sans signaux (T6-03). La seconde ne
   vient que du Cas 2 (seconde voie), de RAIL-LOOP, ou de V190 (désactivé au défaut).
5. **Pas de ligne sans rame ni de rame sans ordres** : achat, ordres puis démarrage, avec un
   rollback atomique. Une seule fenêtre résiduelle (c), l'échec de `StartStopVehicle` en cours de
   liste. L'objet `line` est cohérent pour RAIL-LOOP et la persistance (`stationA`/`B` sont des
   **cases**).

## Périmètre et provenance

- **Référence** : `8268b653`.
- **Livraison** : branche `cloud/revue-rail-T7-20261104`.
- **Lecture** :
  - `builder_rail.nut:4748-5972` : préparation, plan, exécution, `OpexBuildLine` ;
  - `builder_rail.nut:4478-4640` (`OpexBuildTrains`, ordres) et `:3104-3132` ;
  - `economy.nut:36-42`, `:214-226`, `:428-520` ;
  - `task_rail.nut:1463-1660` (enregistrement de la ligne) ;
  - `task_report.nut:440-460` ;
  - `persist.nut:895-950`.

## Constats, triés par gain attendu

Classes : **(a)** certain dans le code ; **(b)** probable ; **(c)** à vérifier en moteur.

| ID | Classe / gravité | Emplacement (`8268b653`) | Défaut | Correction | Gain attendu |
|---|---|---|---|---|---|
| T7-01 | (a) code, (c) fréquence ; perte de profit (classement faussé) | `economy.nut:39-42`, `:430-436`, `:399-413` ; `builder_rail.nut:4920-4935`, `:3108-3110`, `:5570`, `:5610-5612` | Le commentaire de `MAX_RAIL_TRAINS` dit : « le classement ne doit pas attribuer du revenu à une flotte qu'il ne construit pas ». Mais au défaut (V190, V198 et V233L inactifs), le capital d'infrastructure est celui d'**une** voie (`:401`), avec jusqu'à 2 rames. `candidate.trains > 1` déclenche `OpexTryDoubleTrack`, qui rend `ok=false` sans gares posées, donc une rame posée. Les candidats à 2 rames gagnent au classement un revenu de seconde rame jamais construite (ou seulement plus tard, par le Cas 2, s'il a le slot) | Opt-in : sur voie unique, `maxTrains = 1` hors V190/V233L/V198, **ou** chiffrer la seconde voie quand `trains == 2`. Mesurer d'abord (`pred_trains` contre `built_trains`) | Moyen à élevé si la fréquence est forte : un choix de portefeuille fondé sur une flotte fictive |
| T7-02 | (b) ; perte de profit | `builder_rail.nut:4517-4519` | `OF_FULL_LOAD_ANY` sans délai : une source qui baisse (déclin, fermeture partielle, secondaire mal alimentée) garde sa rame à quai. Le profit retombe jusqu'au déclassement de la ligne | Mesurer les jours à quai (`line-telemetry`) avant tout changement. Option opt-in : ordre conditionnel ou retrait du plein après N jours sans chargement | Faible à moyen, selon la fréquence |
| T7-03 | (c) ; robustesse | `builder_rail.nut:4618-4633`, `:5634-5650`, puis `:5663-5664` | Si `StartStopVehicle` échoue pour la rame k, les rames 0..k-1 déjà parties sont « re-stoppées » hors du dépôt. `OpexRollback` ne vend que `IsStoppedInDepot` et la démolition sous un train échoue : il reste des rames orphelines et des bouts de voie | Vendre après `SendVehicleToDepot`, ou ne lancer que la dernière rame après le succès de toutes. Échec rarissime (une rame par ligne au défaut) | Très faible |
| T7-04 | (a) ; style | `builder_rail.nut:4519` | Fret à destination `OF_NONE` : la rame **charge** si la gare B a du même cargo en attente (gare B partagée avec une source du même cargo). Elle le ramène à A, où il n'est pas accepté, et réduit le plein suivant. Cas rare : figé (`C53_ORDER_NOLOAD=false`) | `OF_NO_LOAD` en option si une gare de destination est aussi source du même cargo | Négligeable |

### T7-01 — Le chemin exact

1. Devis (`economy.nut:430-436`) :
   - `startTrains = 1` ;
   - `maxTrains = MAX_RAIL_TRAINS = 2` ;
   - meilleur ROI, puis meilleur profit ;
   - infrastructure à voie unique (`:401`), les variantes à deux voies étant réservées à
     `longModel` et V190.
2. Plan (`builder_rail.nut:4920`) : `candidate.trains > 1` → `OpexTryDoubleTrack(..., null, ...)`.
   Ses premières lignes (`:3108-3110`) rendent `acc` si les gares ne sont pas encore valides, ce
   qui est toujours le cas pour une ligne neuve. Le commentaire `:4923-4926` le reconnaît.
3. Exécution (`:5570`, `:5610`) : `want = 1` ; `OpexBuildTrains(..., 1, ...)`.
4. Enregistrement (`task_rail.nut:1642`) : `predTrains = candidate.trains`, `trains = result.trains`.
   L'écart est stocké mais n'était journalisé nulle part pour le rail.

## Réponses aux questions

1. **Ordres.**
   - A : plein (n'importe quel cargo), non-stop.
   - B, fret : aucun drapeau, donc déchargement de l'accepté et départ à vide (sauf T7-04).
   - B, passagers : plein.
   - Pas d'ordre de dépôt : l'entretien est automatique.
   - Attente indéfinie possible sur une source faible (T7-02).
2. **Nombre de rames.**
   - Une seule à la construction sur voie unique (T7-01).
   - Une seconde seulement par une seconde voie dédiée (Cas 2, slot unique et seuils, T2/T3),
     ou par RAIL-LOOP.
   - `OpexRailVehicleSlotAvailable` n'est que le plafond moteur `max_trains` (500), sans effet.
   - Le facteur réel est l'absence de signaux et de croisement sur voie unique (T6-03).
3. **Ligne sans rame ou rame sans ordres.**
   - Non : les rames sont construites arrêtées, reçoivent leurs deux ordres
     (`GetOrderCount == 2`), puis démarrent ensemble.
   - Tout échec avant le démarrage vend les rames, puis le rollback défait gares, voie et dépôt.
   - Exception (c) : T7-03.
4. **Cohérence de l'objet `line`.**
   - Il porte `platformA`/`B` (avec `station_exit` et `lead`), `depot`, `vehicles`, `trains`,
     `trains0`, `predTrains`, `stationA`/`B` (cases), et `depot2`/`platformA2`/`B2` si le Cas 2
     a lieu.
   - RAIL-LOOP lit `platformA`/`B`, `depot`, `vehicles`, `trains == 1` et `doubleTrack`.
   - Le rechargement revalide `stationA`/`B` comme cases (`persist.nut:940-948`).
   - Aucune incohérence trouvée, hors `trains` contre `predTrains` (T7-01).

## Changement livré

- **Mesure** : `task_rail.nut`, ligne `RAIL_ATTEMPT` (bloc `DECISION_LOG`), champs `pred_trains`
  et `built_trains`. Aucun effet au défaut.
- **Projection OFF** : `sweeps/revue_rail_t7_off.py` en tête de chaîne. Les tests RAIL-LOOP,
  RAIL-FILL et RAIL-KEEP retirent d'abord cette couche.
- **Tests** : `sweeps/test_revue_rail_T7_20261104.py`, 9 tests.
- **Suite complète** : 3 416 tests, **mêmes 4 échecs et 12 erreurs préexistants**.

## Plan de banc pour le PC

```powershell
$ref = 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1]'
$log = 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1,decision_log=1]'
$aaa = @('--aaahogex-setting','disable_veh_roadveh=1','--aaahogex-setting','disable_veh_tram=1',
         '--aaahogex-setting','disable_veh_ship=1','--aaahogex-setting','disable_veh_aircraft=1')
docker run --rm --cpus=10 --memory=8g --memory-swap=8g -v openttd-lab-home:/home/lab -v "${PWD}:/work" -w /work openttd-lab `
  python3 sweeps/bench_v2.py --arms "OpexAI[decision_log=1]" --seeds 42 --years 1 --max-workers 1 `
  --out results/revue_t7_smoke_1x1_20261104.json
python -X utf8 sweeps/run_c66_reference.py --campaign revue_t7_smoke_4x6_20261104 `
  --policy-id reference --variant-policy-id revue_t7_log --reference $ref --variant $log `
  --decision-rule gain_short --min-useful-primary-delta-pct 4 --required-seeds 4 --required-years 6 `
  --years 6 --seeds 17 512 314 8191 --probes 6 --script-debug --line-telemetry `
  --mount-root 'C:\Users\jr\vscode\openttd-ml\openttd-ml' --cpus 10 --memory 8g --max-workers 10 `
  --value-guard-max-loss-pct 100 --out results/revue_t7_smoke_4x6_20261104.json @aaa
Get-ChildItem results\revue_t7_smoke_4x6_20261104_engine\*revue_t7_log*.log | ForEach-Object {
  $a = Select-String $_ 'RAIL_ATTEMPT .* pred_trains=(\d+) built_trains=(\d+) .* ok=1'
  $gap = @($a | Where-Object { $_.Matches[0].Groups[1].Value -gt $_.Matches[0].Groups[2].Value }).Count
  "$($_.Name) built=$($a.Count) pred_gt_built=$gap" }
```

| Critère | Lecture |
|---|---|
| Santé | 8/8, 0 erreur NoAI |
| `pred_gt_built / built` | Au-delà de 20 % : coder l'opt-in T7-01 (`maxTrains = 1` sur voie unique, ou devis à deux voies), puis porte A 40×3 et porte B 20×10. Sous 5 % : sans objet |
| T7-02 | `--line-telemetry` : jours à quai par rame ; à croiser avec la production mensuelle de la source |
