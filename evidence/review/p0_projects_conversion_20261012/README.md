# P0 — Conversion économique OpexAI, preuves gelées du 12/10/2026

Voir [`docs/p0_conversion_projects_1973_20261012.md`](../../../docs/p0_conversion_projects_1973_20261012.md). **Aucune adoption**, P0 encore ouvert : sondes intrusives et absence de preuve transactionnelle de ligne alternative réalisable.

## Provenance et statut

- Témoin **sans sondes**, cinq graines 42/100/999/1234/5678, années 1970–1973, bundle `edd8b31f8d50d2f4d29ae90a87ddb360a59542ade9ee089ddbadf4d2ec093792`, sorties complètes sous `results/diag_opcodes_1970_1973_default_5seeds_20261012.{json,jsonl}` (ignorées Git).
- Profil décisionnel historique **distinct**, cinq graines, bundle `efa38f1ae72d035237e046bc6ea0a23f72ce36ccfa184c5b945059ea5f3da05d` et traces dans `results/diag_opcodes_1970_1973_detail_worker_5x5_20261012_engine/`. Les `P2_PASS`, `P5_RAIL_PASS`, `P5_BUILD_LINE` sont indicatifs, sondes intrusives et fenêtres non exclusives.
- **Nouvelle campagne** `p0_projects_conversion_diag3x5_20261012_r2`, 3 graines 42/100/999, 5 ans, une carte 1v1 OpexAI vs AAAHogEx par graine. Image `openttd-lab:latest` digest `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`, bundle figé `04af9610318c9214da9664b17d9c6326ba17e332c8f3a4bc8d3cec1342e0a59f`, 3/3 jeux et duels sains, 10 CPU / 8 Go / 3 workers, sans overlap. Active `probe_scheduler=1,probe_select_reject=1,catalog_cost_probe=1,probe_loop_ops=1` et `--line-telemetry` annuel, `--script-debug` pour les journaux.
- Tentative **r1 invalide**, faute `C122_AIR_REGIME_PRIORITY` absente dans l'assemblage provisoire de slots du stage ; zéro partie saine. Pour r2 uniquement, trois fichiers de réglages **du stage** ont été restaurés depuis `f6139d8` pour préserver les champs `C122` OFF requis par les sources. `smoke42_r2` 1 an a compilé/passé sain. Aucune modification des travaux utilisateurs dans le principal, pas de commit/push.

## Inventaire des preuves

| Fichier | Contenu et limites |
|---|---|
| `diagnostic_3x5.json` + `.manifest.json` | Résultat C66 apparié et **services actifs** des deux IA reconstruits hors NoAI depuis les sauvegardes décembre. Les services actifs ne sont PAS des constructions brutes. |
| `live_trace_3x5.json` | Registres `SELECT_REJECT`, P2 et services par graine/année, explicite visites répétées et non pertes construites. |
| `historical_funnel_5seeds.json` | Cinq graines, même année rapprochée sur sources **séparées** (profil vs témoin). Quatre trimestres valides exigés pour le premier déficit annuel. |
| `stage_current_overlays.patch` | Diff expérimental local `air_planning`, `probes`, `projects_builders` par rapport à HEAD f6139d8 ; n'est PAS un candidat économique, seulement alignement de certains nettoyages C121 et sonde. |

Les logs bruts et JSONL du r2, ainsi que le bundle de 109+ fichiers et moteur, résident sous `results/p0_projects_causal_stage_20261012/results/`, ignorés Git et préservés. Scripts : `sweeps/analyse_p0_conversion_funnel_20261012.py`, `sweeps/analyse_p0_live_trace_20261012.py`; tests : `sweeps/test_analyse_p0_conversion_funnel_20261012.py` (6 verts), `sweeps/test_analyse_p0_live_trace_20261012.py` (3 verts). Éviter la confusion avec le TopK déjà traité et les pilotes C122 concurrentiels.

## Résultat / garde-fous

**À la clôture 1973 du nouveau 3×5 instrumenté :** Opex AIR actifs **56/46/42**, AAA AIR **13/13/19** ; Opex RAIL **5/6/4**, AAA RAIL **13/7/19** ; Opex ROAD **2/0/1**, AAA ROAD **79/67/101** (seeds42/100/999). Opex domine encore en AIR actif mais le différentiel AAA multimodal est substantiel. `road_pax_build=0` est le défaut historique volontaire et l'activation a été rejetée économiquement ; ne pas redécouvrir comme « bug manquant ».

**Verdict : DIAGNOSTIC SEULEMENT** ; aucun mécanisme d'optimisation économique n'a encore franchi la preuve d'exposition/causalité puis A40×3. Revalidations AIR, sélection capitale et scheduler dépendent d'états dynamiques, un skip global dangereux. Microdoublon `OpexCandidateIsAbandoned` identifié comme correction de calcul potentiellement strictement équivalente, mais sans lien prouvé à la stagnation et sans preuve de gain. V144/AC04-A, score rail simple, `air_fleet_dirty_sched`, TopK sont déjà arbitrés, ne pas relancer.

La comparaison AAA des budgets opcode totaux n'est pas possible par addition de ses `PerformanceCounter` partiels : le déficit économique est mesuré physiquement, mais pas attribué à une supposée surcharge CPU AAA. Les fins de tick demeurent un plafond arithmétique, **0 opcode réellement affecté à un worker par cette étude**.
