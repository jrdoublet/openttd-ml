# T6 — Revue construction, dépôt, rollback, signaux (4 novembre 2026)

## Résumé

1. **Bug certain, corrigé (F1, sans condition)** : `OpexRollback` rasait **chaque case du tracé
   prévu** (`DemolishTile(tiles[i])`), y compris :
   - les cases jamais posées après un échec (arbres, champs, terrain d'autrui) ;
   - **la route d'un passage à niveau** : `DemolishTile` enlève rail **et** route.

   Il ne défait plus que notre propre rail.
2. **Dépôt.** Il est posé à la première case de voie (indices 1-2, contre la gorge de la gare),
   sans exiger une case droite. RAIL-LOOP exige ensuite un front de dépôt droit : c'est son
   premier motif de rejet, `depot_front_curve`, 46 fois au smoke 4×6. Correctif proposé en
   opt-in : préférer une case d'ancrage droite (T6-02).
3. **Signaux.** Au défaut, une ligne primaire à voie unique **n'en a aucun**. Des PBS ne sont
   posés que par le doublement Cas 2 (2 à 8 cases de chaque gare et des deux côtés de
   l'aiguillage du dépôt) et par RAIL-LOOP (`PBS_ONEWAY`). Sur une voie unique sans signaux, une
   deuxième rame ne peut circuler sans risque de collision : c'est le plafond « environ une rame
   par voie ».
4. **Coûts.** Les sondages en mode test pendant la pose sont protégés au défaut (bouclier
   `AIAccounting` pour le dépôt et le diagnostic de convoi ; V199 et V190 sont désactivés).
   `OpexAccountSignal` est un **compteur**, pas un coût. L'écart réel/estimé reste celui mesuré
   par RAIL-CAPEX-1 (×1,16 à ×1,60 par quartile de distance), malgré `RAIL_TERRAIN_FACTOR = 170`.
5. **Orphelins.** Après F1, un échec ne laisse sur la carte que les cases que nous avons
   **nettoyées** (arbres) sans y poser de rail. L'IA n'a **aucun compteur** d'orphelins rail :
   ceux des bancs viennent du décodage des sauvegardes.

## Périmètre et provenance

- **Référence** : `8268b653` (`ccr-6d627d08-tlnphk`).
- **Livraison** : branche `cloud/revue-rail-T6-20261104`.
- **Lecture** :
  - `builder_rail.nut:3095-4748`, en entier pour `OpexBuildTrack`, `OpexTestRailTrack`,
    `OpexBuildDepot`, `OpexRollback`, `OpexV301Trim` et les signaux ;
  - ciblée pour V190 et V199, désactivés au défaut (inventaire en T9) ;
  - `rail_loop.nut:135-150`, et les appelants de `OpexRollback` (27 sites).

## Constats, triés par gain attendu

Classes : **(a)** certain dans le code ; **(b)** probable ; **(c)** à vérifier en moteur.

| ID | Classe / gravité | Emplacement (`8268b653`) | Défaut | Correction | Gain attendu |
|---|---|---|---|---|---|
| T6-02 | (a) mécanisme, (b) effet ; perte de profit | `builder_rail.nut:4346-4352` ; `rail_loop.nut:143-147` | `OpexBuildDepot` prend la première case `index ≥ 1` adjacente à ses deux voisines, sans tester l'alignement. Un front de dépôt sur une courbe rend la ligne inadmissible à RAIL-LOOP (`depot_front_curve`, 46 rejets au smoke 4×6, premier motif) | Opt-in : premier passage limité aux ancres droites (`anchor − stationSide == lineSide − anchor`) dans les 8 premières cases, puis repli historique. Ne casse pas `OpexRailLoopDepotFlow`, qui cherche le dépôt sur toute la voie depuis le 04/11 | Levée d'une partie des 46 rejets. RAIL-LOOP vaut environ +29 k£/an par rame ajoutée |
| T6-01 | (a) ; **robustesse et rapports avec les villes** | `builder_rail.nut:4441-4445` (27 appelants) | Après un `TRKFAIL`, `DEPFAIL`, `TRAINFAIL`, etc., le rollback démolit toute case du tracé. Les cases où la pose a échoué ne sont pas à nous : arbres (coût et note de ville), champs, **route de ville d'un passage à niveau**. Un passage à niveau posé avec succès perd aussi sa route au rollback | **F1 codé** : passage à niveau → `RemoveRailTrack`. Autres cases : démolir seulement si rail **à nous** (`HasTransportType(RAIL)` et `IsMine(GetOwner)`). Gares et dépôt inchangés | Plus de routes de ville coupées ni d'arbres rasés pour rien. Note locale préservée (déjà citée par le commentaire historique : −15/mois pour une ruine) |
| T6-03 | (a) ; constat de conception | `builder_rail.nut:4717-4745` ; `:6670` | Aucun signal sur une voie unique primaire. `OpexPlaceJoinSignals` n'a qu'un appelant (upgrade). Une seconde rame sur la même voie n'est donc jamais sûre ; seuls le Cas 2 (seconde voie indépendante) et RAIL-LOOP (sens unique) ajoutent des rames | Aucune sur la voie unique : des PBS sans évitement bloquent les rames en face-à-face. Le levier reste RAIL-LOOP | — |
| T6-04 | (b) ; perte de profit | `economy.nut:401` ; `globals_pre.nut:604` (`RAIL_DEPOT_COST=false`) | Le devis ignore le dépôt (~450 £) et, pour les longues lignes, sous-estime la voie (RAIL-CAPEX-1 : ×1,16 à ×1,60) | Hors périmètre de la pose : voir RAIL-CAPEX-1, à n'appliquer qu'avec la correction de profit par distance (`taches.md`, 21/10) | Faible ici |
| T6-05 | (a) ; style | `builder_rail.nut:4670-4675` | `OpexAccountSignal` ne compte que `ok/fail`, sans coût. Le coût V199 `n × 100` (`:4286`) est forfaitaire | Documentaire | Nul |

### T6-01 — Preuve

```squirrel
// 8268b653, builder_rail.nut:4441-4445
if (tiles == null) return;
for (local i = 1; i < tiles.len() - 1; i++) {
  AITile.DemolishTile(tiles[i]);
}
```

`OpexBuildTrack` **continue** après une case en échec (`failed++`). Le tracé rendu au rollback
contient donc à la fois nos cases posées et les cases refusées. `DemolishTile` est la commande
« raser » d'OpenTTD : sur une case de route (passage à niveau ou case refusée), elle détruit la
route ; sur des arbres, elle les abat et facture.

**Correctif F1** (branche T6, `:4441-4455`) :
- `AIRail.IsLevelCrossingTile(t)` → `AIRail.RemoveRailTrack(t, AIRail.GetRailTracks(t))` ;
- sinon `continue`, sauf si `HasTransportType(t, RAIL)` et `AICompany.IsMine(AITile.GetOwner(t))` ;
- ponts et tunnels : leurs têtes portent `TRANSPORT_RAIL` et nous appartiennent, donc ils sont
  démolis comme avant.

Le comportement au défaut change **uniquement** pour les cases qui ne sont pas notre rail : c'est
le bug. **À vérifier en moteur (c)** : `GetOwner` d'un pont en tête et le retrait du rail d'un
passage à niveau (smoke ci-dessous).

## Réponses aux questions

1. **Rollback.**

   | Objet | Avant F1 | Après F1 |
   |---|---|---|
   | Rames | Vendues si arrêtées au dépôt (elles ne démarrent qu'une fois tous les ordres posés) | Inchangé |
   | Dépôt | Rasé | Inchangé |
   | Gares | Retirées case par case (`RemoveRailStationTileRectangle`), quais joints compris | Inchangé |
   | Rails, ponts, tunnels et leurs signaux | Rasés | Inchangé |
   | Cases non posées et routes | **Rasées** | Laissées |

   La dépense déjà faite n'est jamais récupérée : la démolition coûte, elle ne rembourse pas.
   Il n'y a pas de compteur d'orphelins dans l'IA.
2. **Dépôt aux indices 1-2.**
   - Avec une rame, ce n'est pas un goulot. Avec RAIL-LOOP, le flux du dépôt est géré par la
     boucle (depuis a8cfb1e).
   - Le vrai coût est l'inéligibilité `depot_front_curve` (T6-02).
   - Placement « après le premier canton » : pas avant RAIL-LOOP. Une ancre droite proche
     préserve le contrat `OpexRailLoopDepotFlow` et le PBS de garde.
3. **Signaux.** Aucun sur la voie unique au défaut. PBS deux sens (repli normal deux sens) posés
   par l'upgrade, 2 à 8 cases depuis chaque gare et de part et d'autre de l'aiguillage du dépôt.
   `PBS_ONEWAY` posés par RAIL-LOOP, avec un espacement de `max(quai + 2, minimum)`.
   - Sur la voie unique, des signaux sans évitement ne permettraient pas de croisement. Ils
     seraient au mieux inutiles, au pire bloquants en face-à-face.
4. **Coûts.**
   - Les sondages en mode test sont protégés au défaut (dépôt `:4374`, convoi `:4539`).
   - V199 (`:3792`) et V190 (`:3266`, `:3585`) ne le sont pas, mais sont désactivés au défaut.
   - La sous-estimation réelle est celle de RAIL-CAPEX-1.

## Changement livré

- **F1** dans `OpexRollback`, sans condition.
- **Projection OFF** : `sweeps/revue_rail_t6_off.py`, en tête de chaîne.
- **Tests** : `sweeps/test_revue_rail_T6_20261104.py`, 11 tests.
- **Suite complète** : 3 418 tests, **mêmes 4 échecs et 12 erreurs préexistants** qu'avant
  (3 407 tests).

## Plan de banc pour le PC

```powershell
$ref = 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1]'
$aaa = @('--aaahogex-setting','disable_veh_roadveh=1','--aaahogex-setting','disable_veh_tram=1',
         '--aaahogex-setting','disable_veh_ship=1','--aaahogex-setting','disable_veh_aircraft=1')
# 1. Compilation 1x1
docker run --rm --cpus=10 --memory=8g --memory-swap=8g -v openttd-lab-home:/home/lab -v "${PWD}:/work" -w /work openttd-lab `
  python3 sweeps/bench_v2.py --arms "OpexAI[decision_log=1]" --seeds 42 --years 1 --max-workers 1 `
  --out results/revue_t6_smoke_1x1_20261104.json
# 2. Smoke 4x6 rail seul : branche T6 contre 8268b653 (worktree séparé), même commande
python -X utf8 sweeps/run_c66_reference.py --campaign revue_t6_smoke_4x6_20261104 `
  --policy-id reference --variant-policy-id revue_t6 --reference $ref --variant $ref `
  --decision-rule gain_short --min-useful-primary-delta-pct 4 --required-seeds 4 --required-years 6 `
  --years 6 --seeds 17 512 314 8191 --probes 6 --script-debug --line-telemetry `
  --mount-root 'C:\Users\jr\vscode\openttd-ml\openttd-ml' --cpus 10 --memory 8g --max-workers 10 `
  --value-guard-max-loss-pct 100 --out results/revue_t6_smoke_4x6_20261104.json @aaa
```

| Critère | Attendu |
|---|---|
| Santé | 8/8, 0 erreur NoAI |
| `RAIL_TRACK_FAIL`, `DEPFAIL` suivis d'une sauvegarde | Branche T6 : aucune route de ville coupée sur le tracé (décodeur de sauvegarde, cases de route manquantes contre la base) |
| Note des villes traversées | ≥ base |
| T6-02 (opt-in à coder) | Compter `RLOOP ... reason=depot_front_curve` avant et après ; porte B 20×10 rail, car RAIL-LOOP ne paie qu'à 10 ans |
