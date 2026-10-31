# Réparations conditionnelles : se sont-elles déclenchées pendant cinq ans ?

**Oui.** Reproduction instrumentée des **40 graines × 5 ans RAIL seul**
le 30 octobre 2026, pour répondre à la question d'exposition après la porte
économique [40×5 déjà close NO-GO](rail_repair_idle_railonly_gateA_40x5_20261030.md).

## Interprétation correcte des deux bancs

Le banc économique initial, référence contre variante, utilisait
`probes=2` : **aucune trace de déclenchement n'y était disponible**.
Ses 80 parties étaient saines, mais ses différences de profit ne prouvaient
pas que les réparations avaient effectivement fonctionné.

Ce nouveau **replay diagnostique distinct** a simulé **40 parties de la
variante seule**, graines `SEEDS_40`, 1970–1974, carte 256², RAIL uniquement,
OpenTTD 15.3, avec les quatre réglages `rail_repair_join_site=1`,
`rail_repair_v131_focus=1`, `rail_repair_astar_pair=1`,
`rail_repair_pose_order=1`, et `probes=258` / `-d script=4`.
Le repli construit V233L n'est pas inclus.

La journalisation ajoute des opcodes et peut changer la chronologie des
parties. **Ne pas reprendre ses profits comme une preuve économique**, ni
substituer ces runs à la porte initiale. Les bibliothèques NoAI sont les
archives figées et vérifiées SHA de la campagne précédente ; aucun changement
de code de l'IA. Exécuté sous Docker avec **8 workers maximum**.

## Résultats physiques observés

| Événement | Nombre | Couverture |
|---|---:|---|
| Partie saine et complète, 60 sauvegardes mensuelles | **40** | 40/40 |
| `RAIL_REPAIR_IDLE phase=enabled` | **30** | **26 graines** |
| `RAIL_REPAIR_IDLE phase=reset` après construction | 1 636 | 40 graines |
| Réparation de quai `RAIL_SITE_REPAIR` | **6 tentatives** | 6 graines |
| Site alternatif physiquement proposé (`options>0`) | 5 | 5 graines |
| **Construction effective `RAIL_BUILD site_repair=1`** | **5** | **5 graines** |
| Seconde recherche `RAIL_ASTAR_REPAIR` | 3 lancées, 3 terminées | 3 graines |
| Résultat de ces secondes recherches | **3 `ABND`** | aucun secours A* démontré |
| `RAIL_POSE_REPAIR` | 0 événement | aucun secours POSE observé |
| `V131_REPAIR` | 0 événement | aucun secours V131 observé |

L'activation `phase=enabled` atteste que l'IA a **évalué la garde comme
vraie** après six mois sans nouvelle liaison. Dans les 14 autres graines,
l'absence de cette trace ne prouve pas qu'aucun intervalle de six mois ne
s'est jamais écoulé : l'évaluation est paresseuse, sur un chemin pertinent.

### Les cinq secours construits

| Graine | Date `RAIL_BUILD` | OD `src→dst` | Cargo | Profit annuel **prédit**, £/an |
|---|---|---|---|---:|
| 100 | 1974-08-18 | 46958→29140 | COAL | +36 330 |
| 512 | 1974-12-16 | 31408→39017 | IORE | +6 704 |
| 12345 | 1974-11-13 | 46126→50747 | GRAI | +4 738 |
| 54321 | 1974-10-17 | 12108→23443 | GRAI | +5 458 |
| 65537 | 1974-02-18 | 42142→29270 | GRAI | +20 064 |

Pour chaque ligne, le journal contient une recherche `RAIL_SITE_REPAIR`
sur la **même OD** antérieure à la construction, puis un vrai `RAIL_BUILD`
avec **`site_repair=1`** ; ce n'est pas une simple simulation AITestMode.
La sixième tentative (graine **746035**) a produit `options=0` et aucune
construction correspondante.

Les trois recherches A* supplémentaires (graines **1024**, **442018** et
**706990**) ont chacune consommé leur plafond de 900 itérations et se sont
terminées sur `result=ABND`, sans succès de cette réparation.

**Limite économique :** les cinq constructions ont eu lieu en 1974, dont
quatre à partir d'août. Leurs profits sont des **prévisions de construction**,
pas des profits réalisés à maturité. Cela explique en partie pourquoi le
`profit_year` de 1974 n'est pas une bonne mesure du profit ultérieur de
ces lignes : ce constat ne modifie toutefois **pas** le verdict NO-GO
préenregistré (+0,113 %, `p=0,824`, IC95 recouvrant 0).

## Traçabilité et reproduction

- Source brute locale ignorée par Git :
  `results/rail_repair_idle_exposure_40x5_20261030.json` ;
  SHA-256 **`fb31eb8b4a0fbc9ef901c6e57a9b26ae6dbf81fd31bc9dd07cbcbba549a74292`**.
- Événements archivés par graine et par action dans
  [le JSON de preuve](rail_repair_idle_exposure_40x5_20261030_events.json),
  sans les milliers de journaux moteur non pertinents.
- Lanceur gelé : `sweeps/run_rail_repair_idle_exposure_40x5_20261030.py`
  (exécuter sous Docker/Linux), filtre les messages de diagnostic mais
  conserve les marqueurs d'erreur ; analyseur :
  `sweeps/analyse_rail_repair_idle_exposure_40x5_20261030.py`.

**Conséquence :** le dispositif de réparation fonctionne **physiquement**
sur au moins cinq OD de ce replay. La priorité suivante est la mesure du
profit *réalisé* des lignes sauvées et l'analyse des alternatives échouées,
pas l'activation globale de quatre réparateurs encore non qualifiés.
