# FRONT-PAX-2 — jalon de mesure passive des paires AIR

**Statut au 25 octobre 2026 : sonde locale validée par un smoke 1×1 et une exposition 5×5 ; aucun changement de seuil proposé.**
Base : `master` HEAD `83e436cc`, worktree isolé `.worktrees/nuit75-front-pax2`.

## Résultat de l'exposition 5×5 (après smoke)

Le smoke `nuit75_frontpax2_smoke_1x1_20261025` a produit trois lignes FP2 cohérentes. Le banc diagnostic `nuit75_frontpax2_diag_5x5_20261025`, 5 graines × 5 ans sur 256², a été décodé hors ligne avec le script `sweeps/analyse_front_pax2.py`. **28 `AIR_PLAN_INPUT`, 23 scans finalisés (69 lignes `FRONT_PAX2`) et 5 censurés** : les scans censurés sont écartés des volumes, jamais interprétés comme zéro. La validation `--strict` passe, sans doublons, sans partition incohérente et sans orphan de sortie.

| Bras | 20–63 | 64–77 | 78–199 | Total sous `airMin=200` |
| --- | ---: | ---: | ---: | ---: |
| Deux sites proposés (`newpair`) | 329 | 158 | 1 783 | **2 270** |
| Hub existant + site (`hubsite`) | 1 058 | 522 | 4 930 | **6 510** |
| Deux hubs existants (`hubhub`) | 167 | 77 | 786 | **1 030** |
| **Total** | **1 554** | **757** | **7 499** | **9 810** |

Sur ces 23 scans, la bande effective était **`PAX_BAND_ALL` (0)** et la borne `airMin=200` : `below_min = blocked_min = below_within = 9 810` ; aucun de ces couples examinés ne dépassait `airMax`, `AIR_MAX_DISTANCE` ou le `plane.maxOrderDistance` du combo. Les trois bras cumulent aussi **1 435 évaluations de couples à 200+** ayant passé le filtre de bande, **81 trop courtes** dans `newpair` (entre 20 et 31) et **4 strictement sous 20** ; 0 `other_band`. En comptant toutes les paires d'au moins 20, **11 326** évaluations ont été enregistrées, dont 9 810 sous le seuil 200 et hors minDist. Aucune observation ne mesure leur économie C121, leur constructibilité réelle ni leur admission C77.

Par année du catalogue associée au scan, le volume sous 200 est 1970 : **7 630**, 1971 : **751**, 1972 : **1 140**, 1973 : **143**, 1974 : **146**. En revanche, les années **réelles d'émission des lignes** donnent respectivement 1970 : **771**, 1971 : **5 219**, 1972 : **2 846**, 1973 : **685**, 1974 : **289**. La différence atteste que certains scans se terminent longtemps après leur initialisation : ne pas utiliser `bounds.year` comme date de fin effective.

Commande validée sur Windows PowerShell 5.1 (glob volontairement entre guillemets, développé par le script) :

```powershell
python -X utf8 sweeps/analyse_front_pax2.py 'results/nuit75_frontpax2_diag_5x5_20261025_engine/*.log' --strict --out-json results/nuit75_frontpax2_diag_5x5_20261025_frontpax2.json --out-md results/nuit75_frontpax2_diag_5x5_20261025_frontpax2.md
```

Les sorties JSON/MD incluent la couverture **par graine et année de début**, les agrégats par bras, année de catalogue, bande et année réelle d'émission, avec contrôles de partition. Ce sont des évaluations répétées de couples selon moteur/combo/cycle ; il n'est pas démontré qu'il s'agit de **9 810 opportunités indépendantes**.

## Question causale et réutilisation de C78

`OpexAirPairInBand` (`candidates.nut:472-484`) rejette `manhattan < catalog.bounds.airMin` seulement pour `PAX_BAND_ALL`. La phase `PAX_BAND_AIR_ONLY` rejette `manhattan <= railMax` ; la phase `PAX_BAND_AIR_RAIL` n'admet que `[railAirOverlapMin, railMax]`. Les trois appelants sont dans `air_planning.nut` (newpair, hubsite, hubhub). Le minDist préalable est **30/32** pour newpair et **20** pour les bras hub, et `airMax`, `AIR_MAX_DISTANCE` et `plane.maxOrderDistance` constituent d'autres filtres distincts.

Le C78 existant (`C78_AIRPAIR`) émet déjà `arm`, `dist` et `outcome=pax_band` par paire examinée, mais **uniquement sous `C69_BOTTLENECK_PROBE` pour la première génération journalisée de l'année** (`C78_GEN_LOG_YEAR`). Ses lignes ne séparent pas `PAX_BAND_*` dans le refus, et ne vérifient pas les plafonds de distance en aval de ce refus. Il suffit pour une inspection détaillée de cette génération, sans justifier de second journal par paire ; il ne fournit pas directement les agrégats bornés de toute la génération terminée. Le nouveau compteur exploite les trois sites d'appel existants et les mêmes distances déjà calculées, sans autre balayage.

## Périmètre exact de la nouvelle sonde

Activée **seulement si `DECISION_LOG`** (réglage `probes`, existant). Aucune activation de politique, aucune modification de `OpexAirPairInBand`, aucun nouveau réglage. Sous la sonde, `OpexFrontPax2Observe` incrémente un nombre fixe de compteurs par bras (`newpair`, `hubsite`, `hubhub`) et par intervalle Manhattan : **20–63**, **64–77**, **78–199**, **200+**. Les distances strictement inférieures à 20 ont un compteur distinct `under20`.

Pour chaque bras, la ligne `FRONT_PAX2` finale contient :

| Champ | Signification |
|---|---|
| `seen` | Paires arrivées au calcul Manhattan et de distance, après filtres préalables (cible, disponibilité du site, connexion existante, etc.). Pas toutes les combinaisons théoriques de villes. |
| `short` | Paires à au moins 20 mais sous le minimum propre au bras : 30/32 en `newpair`, 20 pour les hubs. |
| `below_min` | **Observation contrefactuelle** : paires non courtes sous `airMin`, quelle que soit la phase `pax_band`. |
| `blocked_min` | Rejets **réels** imputables à `airMin`, exclusivement sous `PAX_BAND_ALL`. Sous les phases split, ils sont comptés dans `other_band`. |
| `below_airmax`, `below_plane`, `below_config` | Sous-ensembles de `below_min` dépassant, respectivement, `bounds.airMax`, `plane.maxOrderDistance`, `AIR_MAX_DISTANCE` ; les sous-ensembles peuvent se chevaucher. |
| `below_within` | Sous-ensemble de `below_min` restant sous ces trois plafonds **de distance**. Aucun site, capital, autorité locale, véhicule réel choisi par C121, ROI ou construction n'est garanti. |
| `other_band` | Rejet de la phase `AIR_ONLY` / `AIR_RAIL`. |
| `airmax` | Rejet du plafond `bounds.airMax` quand le filtre de phase est passé. |
| `band_pass` | La bande est passée, mais les gardes distance de configuration/moteur, abandon, C121, économie et C77 restent à franchir. |

Les quatre champs **`short + blocked_min + other_band + airmax + band_pass`** partitionnent `seen` tranche par tranche. `below_min` et ses sous-champs sont des coupes **transversales** qui ne s'ajoutent pas à cette partition. Un même couple peut être revisité sous différentes combinaisons avion/aéroport ou générations : le volume correspond aux **évaluations de couples** observées, pas à des paires de villes uniques ni à des projets constructibles.

La distinction des ressources existantes : `newpair` part de **deux sites proposés par le scan AIR** (pas encore deux aéroports posés) ; `hubsite` part d'un **hub existant et d'un site proposé** ; `hubhub` part de **deux hubs existants**. La sonde ne relance jamais `OpexAirFindSite`, `OpexAirSiteStillBuildable`, `Valuate`, A\* ni une géométrie. `plane.maxOrderDistance` correspond au combo examiné, pas nécessairement au moteur finalement sélectionné par C121.

## Reprises, fin de cycle, défaut et limites

- L'histogramme est créé sous `DECISION_LOG` avec le `bounds.year` du catalogue. En mode C78 reprenable, une unique table `resumeState.frontPax2` est partagée par référence entre les appels successifs ; les checkpoints des trois boucles sont antérieurs à la visite de la paire suivante. Les passages de combo ne réinitialisent pas l'histogramme.
- **Trois lignes seulement** par `OpexAirPlansFinalize`, une par bras, avec `scan` de `AIR_PLAN_INPUT` / `AIR_PLAN_PERF`, année et `pax_band`. En absence de combos, trois lignes de zéros lors de l'arrêt précoce. Les abandons/cycles interrompus n'émettent aucun bilan partiel. `resumeState.done=true` empêche un second bilan sur une reprise déjà terminée.
- Les phases `AIR_ONLY` / `AIR_RAIL` sont réellement utilisées par `projects.nut:148-151` et `scheduler_tasks.nut:40-41` ; `PAX_BAND_ALL` par les reconstructions standard. **V276** découpe les unités de candidats RAIL/ROAD (`candidates_v276.nut`), ce qui n'est pas une preuve d'absence des autres bandes dans AIR.
- `V278_AIR_LAZY_SITES` vaut `2` par défaut, donc reste **désactivé sur la carte 256²** de la mission ; lorsqu'il est forcé, `OpexV278LazyPairs` délègue chaque paire effectivement admissible de son heap à `OpexAirPlansNewPairs` via `OpexV278CopyContext`. La mesure couvre les paires réellement transmises, pas les entrées du heap éliminées avant ce passage.
- L'état est de **télémétrie éphémère**. `Save()` n'enregistre que les échéances des tâches, pas `airState` ni `frontPax2` ; `Load()` redémarre les reconstructions en cours. Une sauvegarde au milieu d'un scan perd son histogramme incomplet, sans changer la politique. Aucune prétention de comparaison à travers Save/Load à ce stade.
- **Coût OFF** : une initialisation de champ `ctx.fp2=null`, un test `DECISION_LOG` par appel et des gardes `if (ctx.fp2 != null)` aux points de visite ; aucune allocation d'histogramme, aucun calcul de borne/distance supplémentaire, aucun journal, ni changement de filtre. Le coût résiduel de branchement en opcodes **n'a pas été mesuré**. **Coût ON** : accès à compteurs et vérification de plafonds par couple, susceptibles de changer les moments de suspension et la trajectoire ; à mesurer avant interprétation causale.
- La sonde ne sait ni estimer le profit/ROI d'une paire rejetée, ni prouver qu'elle aurait passé la validation du site, ni dire que C77 l'aurait classée ou financée. Il faudra un shadow économique borné et un contrôle de construction pour décider d'un éventuel seuil 63/78.

## Vérification et suite requise

Tests ciblés sans Docker : `python -X utf8 -m unittest discover -s sweeps -p 'test_front_pax2_passive.py' -v`, fixture figée `sweeps/fixtures/front_pax2_cases.json`, contrat de reprises `test_ac03_air_new_pairs_resume.py`, `git diff --check`. La fixture distingue `below_min` de `blocked_min` pour les trois bandes, le minimum newpair 32, le maximum avion et les distances de vol.

Le smoke FP2 1×1 du prime est passé et le banc diagnostic 5×5 a terminé. **Reste à mesurer l'effet du coût ON sur les opcodes et les suspensions**, puis à dédupliquer les répétitions d'un même couple si l'on veut parler de villes distinctes. Un shadow économique borné et des essais de construction restent nécessaires avant toute porte A/B ou abaissement de `airMin`.
