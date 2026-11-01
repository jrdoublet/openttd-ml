# Sessions Claude cloud — chantier route seule à 3 ans

Branche de travail : `road1y-s17`. Chaque session cloud crée **sa propre branche**
`cloud/<sujet>` depuis `road1y-s17`, commite et pousse dessus. Jamais de
modification de `master`, jamais de changement de valeur par défaut.

## Objectif

Profit annuel OpexAI ≥ AAAHogEx à 3 ans, **route seule**, sur au moins une graine.
Seul critère : `profit_year` au cliché 1972-12-01 (pas la valeur de compagnie).

État au 29/10 (porte A 40×3, défaut actuel) : Opex 216 k£/an contre AAA 941 k£
(23 %), 80 véhicules contre 247 ; meilleure graine 34 %. Sur la graine 613553 :
Opex 301 k£ contre 816 k£ ; AAA tire **~297 k£/an du courrier** (76 fourgons),
Opex 0 ; à nombre de bus PAX égal (75), AAA 6 440 £/bus contre 2 921 £.

## Déjà essayé (ne pas refaire)

- `road1y_fleet_unlock` (renfort selon l'attente, réserves de caisse abaissées) :
  −20 % ; bus marginaux ~+361 £/an ; la caisse ne dépasse plus le seuil
  d'ouverture de ligne (6 lignes de moins). Bug : plafond = somme des arrêts A+B
  au lieu du min. Voir `diag_fleet_unlock_agy.md`.
- `road1y_long_band` (liaisons jusqu'à 192 tuiles) : porte A 40×3 `fail_primary`
  (−2,0 k£/an, 19/21, p=0,84).
- `road100_mail_intertown` (ROAD100-27, générateur MAIL ville↔ville séparé) :
  NO-GO, lignes à 273 £/an (voir `docs/taches.md`, ROAD100-27).
- Diagnostic général 3 ans : `diag_3ans_agy.md` (attention : agy surévalue
  parfois ; vérifier ses chiffres dans les données).

## Données fournies (`docs/cloud/data/`, lire avec `zcat`)

| Fichier | Contenu |
|---|---|
| `road1y_3ans_defaut_3graines.jsonl.gz` | défaut, graines 613553/781335/100, 3 ans, clichés mensuels, `line_telemetry` Opex ET AAA (`policy_id` = `reference` / `AAAHogEx`, `run`=[ia, graine, rép]) |
| `road1y_3ans_fleet_unlock15_3graines.jsonl.gz` | même chose avec `road1y_fleet_unlock=15` |
| `road1y_3ans_s613553_decision_log.log.gz` | journal moteur Opex, `probes=258` (DECISION_LOG), graine 613553 |
| `road1y_long2_gateA_40x3_summary.json.gz` | synthèse porte A 40×3 (40 graines, défaut et variante) |
| `AAAHogEx-115_source.tar.gz` | source de l'adversaire (GPLv3, `license.txt` inclus) |

Dans `line_telemetry.lines[*]` : `ordered_station_tiles` (distance = Manhattan
sur carte 256), `vehicle_ids`, `vehicle_financials[*].profit_last_year_gbp`,
cargo dans `service_key` (`cargo=0` PAX, `cargo=2` MAIL).

## Contraintes de code (OpexAI, Squirrel 2/3 d'OpenTTD 15.3)

- Pas de `yield` (ni appel qui suspend) dans un `try`.
- Les closures ne capturent pas les locales ; mots réservés `clone`, `base`, `par`.
- Toute nouveauté derrière un réglage `info.nut` à **0 par défaut**, lu dans
  `settings.nut`, constante dans `globals_pre.nut` ; à 0, comportement
  **strictement identique** (même trajectoire).
- `AIIndustry.GetIndustryID` renvoie 65535 si invalide, pas −1.
- Les tests de projection `sweeps/fixtures/road100_*_hunks.json` reconstruisent
  le parent : ne modifier que les blocs « after » ou ajouter un hunk.
- Tests à faire passer :
  `python3 -B -m unittest discover -s sweeps -p 'test_road100*'` et
  `python3 -B -m unittest discover -s sweeps -p 'test_road1y*'`.
  Ajouter un test de contrat `sweeps/test_road1y_<sujet>.py`.

## Ce qu'on ne peut probablement pas faire en cloud

Pas de Docker/OpenTTDLab : **pas de partie**. Donner en fin de rapport la
commande de mesure à lancer sur le VPS (3 ans, 3 graines, puis porte A) :

```
python3 sweeps/run_c66_reference.py --campaign <nom> --network host \
  --reference "OpexAI[mode_air=0,mode_rail=0,mode_road=1,mode_water=0,estim_unifie=31,<réglage>=<v>]" \
  --aaahogex-setting disable_veh_train=1 --aaahogex-setting disable_veh_tram=1 \
  --aaahogex-setting disable_veh_ship=1 --aaahogex-setting disable_veh_aircraft=1 \
  --years 3 --repeats 1 --cpus 3 --memory 2g --max-workers 3 --line-telemetry \
  --line-telemetry-monthly --script-debug --probes 2 --seeds 613553 781335 100
```

Si Docker est disponible malgré tout, une partie de 1 an sur une graine suffit
comme smoke ; ne lancer aucune porte A/B.

## Livrable de chaque session

Rapport en français `docs/cloud/rapport_<sujet>.md` : constats chiffrés avec
fichier:ligne, diff résumé, tests passés, commandes de mesure, risques.
Commits sur `cloud/<sujet>`, push de cette branche seulement.
