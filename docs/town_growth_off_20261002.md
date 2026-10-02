# Town growth OFF — A/B PC du 2 octobre 2026

Au défaut C115, OFF satisfait la règle d'absence de perte pré-enregistrée : −21,8 k£/an, IC95 Student [−131,9 ; +88,2] k£/an, 10/10/0, p=1, valeur +2,05 %. Le verdict brut reste `fail_primary` : aucun gain positif démontré, aucun défaut changé. La future version ciblée doit battre OFF. Sous C121 (secondaire), Δprofit +131,8 k£/an, 13/7/0, p=0,263176, verdict brut `fail_primary`. Voir sa lecture séparée ci-dessous.

## Plan pré-enregistré avant mesure (13 h 45, Europe/Paris)

Demande utilisateur : mesurer si la tâche town growth actuelle paie ses opcodes.
Le profil [C121 du 2 octobre, §3](opcode_profile_c121_20261002.md) motive l'essai
(15 % des opcodes, 95 % en planification infructueuse) ; ce profil instrumenté
est une mesure de coût sous C121, pas une preuve causale du bénéfice économique.
La version ciblée aux monopoles aéroportuaires Opex 2-0 relève du chantier C83.1
mené ailleurs ; aucune implémentation ici. Aucun défaut ni merge autorisé.

- Dépôt : `jrdoublet/openttd-ml`, branche `c121-catalog` ; base propre après
  `git pull --ff-only` : `c9905d84d99a1b715546d94897fb4609eb461820`, contenant `652dac9`.
- Les deux bras utilisent exactement les mêmes sources figées. Le SHA du décodeur
  et les hashes des bundles seront consignés avec les résultats.
- PC Docker `desktop-linux`, image `openttd-lab:latest`, ID vérifié
  `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
  Import `openttdlab` 0.0.75 réussi ; dépôt Windows monté dans `/work` et
  `ai/AAAHogEx-115/main.nut` présents. Adversaire ignoré par Git.
- Limites utilisateur : 10 CPU, 2 Go, `--memory-swap=2g` (sans swap),
  10 workers maximum, cache `openttd-lab-home`. Une campagne à la fois.
- Défaut conservé : `town_growth=1`, quatre difficultés à 1 ; chargement
  `settings.nut::TOWN_GROWTH_ENABLED`. La garde de `_dispatchTownGrowth`
  coupe cette tâche, sans supprimer les bus interurbains.
- Métrique primaire : `profit_year`, delta **Opex OFF − Opex ON**.
  `signs20`, une répétition, effet minimal 0 £/an, garde de valeur 5 %.
  La garde est rapportée et utilisée pour la lecture de neutralité ; selon
  l'objectif utilisateur du 29/09, la valeur seule ne rejette pas la piste.

Séquence autorisée, sans nouvelle demande de lancement :

| Étape | Campagne prévue | Bras | Couverture attendue |
|---|---|---|---|
| Smoke défaut | `tg_default_smoke_1x1_20261002_r1` | `OpexAI` solo | 1 partie × 1 an, graine 42 |
| Diagnostic défaut C115 | `tg_off_default_5x6_20261002_r1` | `OpexAI[town_growth=1]` / `OpexAI[town_growth=0]` | 10 duels, 5 paires × 6 ans |
| A/B défaut C115 | `tg_off_default_20x10_20261002_r1` | mêmes bras | 40 duels, 20 paires × 10 ans |
| A/B secondaire C121 | `tg_off_c121_20x10_20261002_r1` | `OpexAI[c121_air_economics=1,c121_catalog_incremental=1,town_growth=1]` / mêmes options avec `town_growth=0` | 40 duels, 20 paires × 10 ans |

Graines diagnostic : 42,100,999,1234,5678. Graines 20×10 :
42,100,7,999,2026,1,17,73,314,512,1024,1337,4096,8191,12345,54321,65537,123456,424242,8675309.
Sous C121, l'essai qualifie l'effet de TG dans ce socle secondaire, pas l'économie
C121 contre C115. L'autorisation utilisateur de cet A/B ne rouvre pas les autres
20×10 C121 interdits dans `taches.md`.

Porte diagnostic : santé et couverture complètes, exposition TG >0 au total
dans la référence et =0 dans OFF, panneaux invalides absents. Sauf exposition
nulle ou santé défaillante, enchaîner le 20×10 quel que soit le delta 5×6.

Lecture fixée avant les résultats :

- IC95 Student du delta non entièrement négatif, pas de défaites significatives
  au test exact des signes bilatéral, garde −5 % tenue : absence de perte selon
  la règle opcodes demandée ; town growth actuel ne paie pas ses opcodes selon
  cette règle, futur ciblage à comparer à OFF. Ce n'est pas une preuve d'équivalence.
- IC95 entièrement négatif ou majorité de défaites significative : town growth
  paie ; futur ciblage à comparer à ON.
- ≥15 victoires/20 et p<0,05 : candidat au défaut OFF, décision utilisateur.
  Le verdict brut `signs20` reste séparé de cette lecture. Aucun défaut changé ici.
- Garde échouée sans perte significative : neutralité non validée par la règle,
  résultat à rapporter sans rejet fondé uniquement sur la valeur.

## Mesure et validation du harnais

Décodeur `town_growth_sign_metrics` ajouté au harnais courant C66. Un panneau
`TG|aa|ville|avant|après` valide compte une construction, indépendamment du nombre
de stations créées. Propriétaire Opex (0) filtré si `owner` est présent ; ancien
schéma sans propriétaire accepté. Les panneaux malformés sont comptés à part.
`SIGN` absent reste inconnu ; chunk vide = zéro observé. Année à deux chiffres
résolue avec l'année du checkpoint, y compris changement de siècle.

Les snapshots JSONL portent total cumulatif et ventilation annuelle ; les résumés
gardent le dernier snapshot sans sommer des panneaux persistants. Le rapport de
politique expose les comptes ON/OFF et les deltas, par partie et par année.
Limite : panneaux conservés et horizon des checkpoints du harnais (dernier
checkpoint mensuel au 1er décembre), pas journal exhaustif d'événements API ;
un échec non signalé de `AISign.BuildSign` pourrait sous-compter. Aucune sonde
Squirrel supplémentaire, aucun changement de comportement.

Validation hôte avant mesure : 7 tests TG avec fixture, `--selftest` du harnais,
62 tests `campaign_freeze`, `profit_coverage`, `physical_counters`, `game_health`,
et `git diff --check` réussis. Après correction du type date : 8 tests TG et
selftest réussis. Le smoke effectivement exécuté est décrit ci-dessous.


## Smoke et incident technique

Smoke défaut terminé sur `496639f` : 1/1 partie, `run_ok=true`, compteurs
physiques valides, 13 checkpoints jusqu'au 01/01/1971. La première année de
profit conserve sa couverture partielle (3 trimestres) ; smoke technique seulement.

Première tentative diagnostic `tg_off_default_5x6_20261002_r1`, même SHA :
échec de collecte avant résultat, `TypeError: 'datetime.date' object is not
subscriptable`. OpenTTDLab fournit un objet date ; conversion en chaîne corrigée
dans le décodeur, contre-test du type réel ajouté. Ancien bundle conservé,
aucun verdict économique ni réemploi des résultats. Nouvelle campagne
`tg_off_default_5x6_20261002_r2` après validation (8 tests TG + selftest).
Les bras, seuils, graines et règle restent ceux du plan initial.


## Résultats vérifiés

Tous les deltas sont OFF − ON. Profit et gap en k£/an ;
IC95 Student-t appariés. Le profit primaire est le dernier profit annuel
collecté, pas le profit cumulé des dix années.

| Profil | Duels / paires | Δprofit moyen / médian | IC95 | V/D/E ; p | Δgap moyen | Valeur | Verdict brut |
|---|---|---:|---|---|---:|---:|---|
| C115 diagnostic 5×6 | 10/10 ; 5/5 | 96.6 / 114.7 | [-112.6; 305.7] | 3/2/0 ; 1.000000 | 405.6 | 13.0 % | `diagnostic_only` |
| C115 20×10 | 40/40 ; 20/20 | -21.8 / -5.8 | [-131.9; 88.2] | 10/10/0 ; 1.000000 | 38.1 | 2.0 % | `fail_primary` |
| C121 secondaire 20×10 | 40/40 ; 20/20 | 131.8 / 134.4 | [19.9; 243.7] | 13/7/0 ; 0.263176 | 244.6 | 9.5 % | `fail_primary` |

Moyennes du profit annuel final, pour distinguer l'effet sur Opex de celui sur l'adversaire :

| Profil | Opex ON | Opex OFF | AAA face à ON | AAA face à OFF |
|---|---:|---:|---:|---:|
| C115 diagnostic 5×6 | 1 469.3 | 1 565.8 | 4 620.3 | 4 311.2 |
| C115 20×10 | 2 115.7 | 2 093.9 | 9 149.2 | 9 089.3 |
| C121 secondaire 20×10 | 1 353.7 | 1 485.4 | 9 162.9 | 9 050.0 |

### Santé, couverture et exposition

- **C115 diagnostic 5×6** : 10/10 duels sains, 20/20 résumés compagnie, 1440/1440 lignes JSONL attendues. `comparison_complete=true`, `metric_coverage_complete=true`, `adoption_sample_complete=false`. Quatre trimestres valides au primaire pour les deux bras : True. TG ON/OFF : 53/0, zéro panneau TG invalide ; ON construit en moyenne 1.77 ligne par partie et par an.
- **C115 20×10** : 40/40 duels sains, 80/80 résumés compagnie, 9600/9600 lignes JSONL attendues. `comparison_complete=true`, `metric_coverage_complete=true`, `adoption_sample_complete=true`. Quatre trimestres valides au primaire pour les deux bras : True. TG ON/OFF : 246/0, zéro panneau TG invalide ; ON construit en moyenne 1.23 ligne par partie et par an.
- **C121 secondaire 20×10** : 40/40 duels sains, 80/80 résumés compagnie, 9598/9600 lignes JSONL attendues. `comparison_complete=true`, `metric_coverage_complete=true`, `adoption_sample_complete=true`. Quatre trimestres valides au primaire pour les deux bras : True. TG ON/OFF : 237/0, zéro panneau TG invalide ; ON construit en moyenne 1.19 ligne par partie et par an.
  Archive JSONL incomplète : reference / AAAHogEx / graine 8675309 / 1972-02-01; tg_off / AAAHogEx / graine 8675309 / 1972-12-01. Les résumés issus des retours moteur portent 9600/9600 observations (120 par compagnie), y compris les checkpoints finaux. Le rapport brut contient aussi la trajectoire annuelle concernée. Les deux lignes intermédiaires AAA absentes ne sont ni reconstruites ni ajoutées. Cause d'écriture concurrente sur le montage Windows soupçonnée, pas établie. Santé moteur et couverture du primaire final restent complètes selon le harnais ; la complétude du journal JSONL est une limite distincte.

`game_health` : aucune erreur moteur/NoAI, horizon tronqué, donnée manquante
ou erreur non attribuée dans les retours moteur analysés. Le journal persisté
C121 a les deux absences intermédiaires décrites ci-dessus. Compagnies actives,
horizon final au 1er décembre 1975/1979 ; la première année du profit
garde sa couverture partielle. Les métriques finales ont quatre trimestres.

### C115 diagnostic 5×6

**Deltas par graine** — k£/an pour profit/gap, % de valeur
par paire ; constructions TG ON/OFF = total des panneaux durables.

| Graine | Δprofit | Δgap | Δvaleur % | TG ON/OFF |
|---:|---:|---:|---:|---:|
| 42 | 114.7 | -446.7 | 6.2 | 11/0 |
| 100 | 321.9 | 39.8 | 56.8 | 4/0 |
| 999 | -92.4 | 1 226.9 | -1.6 | 12/0 |
| 1234 | -43.0 | -16.0 | 15.4 | 13/0 |
| 5678 | 181.6 | 1 224.2 | 20.4 | 13/0 |

Gap : médiane 39.8 k£/an, IC95 [-552.7; 1 363.9] k£/an, V/D/E=3/2/0, p=1.000000.

**Trajectoire annuelle et TG** — moyenne des deltas de fin d'année ;
TG = total des constructions sur toutes les graines puis moyenne par partie.

| Année | Δprofit k£/an | Δgap k£/an | TG ON/OFF total | TG ON par partie |
|---:|---:|---:|---:|---:|
| 1970 | 33.8 | 0.0 | 15/0 | 3.00 |
| 1971 | 116.5 | 39.7 | 12/0 | 2.40 |
| 1972 | 174.5 | -51.2 | 10/0 | 2.00 |
| 1973 | 213.7 | 28.5 | 6/0 | 1.20 |
| 1974 | 80.6 | 150.6 | 8/0 | 1.60 |
| 1975 | 96.6 | 405.6 | 2/0 | 0.40 |

**Créneaux et véhicules finaux** — moyenne par partie, comptes physiques.

| Métrique | ON | OFF | ΔOFF−ON |
|---|---:|---:|---:|
| Slots Opex | 25.2 | 26.4 | 1.2 |
| Slots AAA | 42.2 | 40.4 | -1.8 |
| Villes AAA≥2 / Opex0 | 7.8 | 6.4 | -1.4 |
| Villes Opex≥2 / AAA0 | 1.6 | 1.2 | -0.4 |
| Villes 1-1 | 20.4 | 22.2 | 1.8 |
| Véhicules Opex primaires (tous modes) | 125.4 | 137.4 | 12.0 |
| Véhicules Opex air | 106.4 | 130.2 | 23.8 |
| Véhicules Opex road | 17.6 | 4.8 | -12.8 |
| Véhicules Opex rail | 1.4 | 2.4 | 1.0 |
| Véhicules Opex water | 0.0 | 0.0 | 0.0 |

Véhicules issus de `decode_vehicles(target_owner=0)`, avec `physical_ok=true` ;
rail/route/air qualifiés. Le mode eau n'est pas qualifié : ses comptes restent descriptifs.
Les comptes 2-0 sont ceux du décodeur existant : ≥2 aéroports contre 0.

### C115 20×10

**Deltas par graine** — k£/an pour profit/gap, % de valeur
par paire ; constructions TG ON/OFF = total des panneaux durables.

| Graine | Δprofit | Δgap | Δvaleur % | TG ON/OFF |
|---:|---:|---:|---:|---:|
| 42 | 269.6 | -509.2 | 11.8 | 14/0 |
| 100 | 45.8 | -584.0 | 19.8 | 7/0 |
| 7 | 72.9 | 2 169.7 | 5.8 | 13/0 |
| 999 | -325.3 | 40.0 | -3.8 | 19/0 |
| 2026 | -75.6 | 773.0 | 12.5 | 11/0 |
| 1 | 257.3 | 1 207.8 | 14.7 | 9/0 |
| 17 | 97.6 | -664.8 | 11.8 | 8/0 |
| 73 | 323.1 | 1 219.9 | -1.9 | 13/0 |
| 314 | 134.3 | -643.5 | -0.6 | 21/0 |
| 512 | -57.4 | -150.5 | -2.7 | 6/0 |
| 1024 | 295.2 | 1 054.9 | 18.0 | 15/0 |
| 1337 | 72.8 | 1 100.8 | 25.4 | 9/0 |
| 4096 | -265.6 | -2 605.8 | 3.3 | 16/0 |
| 8191 | -89.0 | -178.5 | -14.6 | 11/0 |
| 12345 | 140.2 | 33.3 | 9.7 | 16/0 |
| 54321 | -433.7 | 1 131.6 | -8.1 | 12/0 |
| 65537 | -107.8 | -875.2 | -20.8 | 7/0 |
| 123456 | -220.6 | 907.3 | 2.5 | 13/0 |
| 424242 | -103.5 | -2 166.3 | -2.0 | 15/0 |
| 8675309 | -466.1 | -498.0 | -12.6 | 11/0 |

Gap : médiane -58.6 k£/an, IC95 [-516.3; 592.5] k£/an, V/D/E=10/10/0, p=1.000000.

**Trajectoire annuelle et TG** — moyenne des deltas de fin d'année ;
TG = total des constructions sur toutes les graines puis moyenne par partie.

| Année | Δprofit k£/an | Δgap k£/an | TG ON/OFF total | TG ON par partie |
|---:|---:|---:|---:|---:|
| 1970 | 4.3 | -5.7 | 37/0 | 1.85 |
| 1971 | 85.1 | -25.0 | 38/0 | 1.90 |
| 1972 | 78.8 | 28.0 | 34/0 | 1.70 |
| 1973 | 98.1 | 64.8 | 29/0 | 1.45 |
| 1974 | 60.1 | 90.6 | 26/0 | 1.30 |
| 1975 | 41.5 | 96.7 | 21/0 | 1.05 |
| 1976 | 53.6 | 170.0 | 17/0 | 0.85 |
| 1977 | 30.3 | 247.2 | 16/0 | 0.80 |
| 1978 | 22.2 | 242.8 | 16/0 | 0.80 |
| 1979 | -21.8 | 38.1 | 12/0 | 0.60 |

**Créneaux et véhicules finaux** — moyenne par partie, comptes physiques.

| Métrique | ON | OFF | ΔOFF−ON |
|---|---:|---:|---:|
| Slots Opex | 27.6 | 27.1 | -0.6 |
| Slots AAA | 42.4 | 42.3 | -0.1 |
| Villes AAA≥2 / Opex0 | 7.1 | 6.8 | -0.2 |
| Villes Opex≥2 / AAA0 | 1.0 | 0.8 | -0.2 |
| Villes 1-1 | 23.6 | 23.0 | -0.6 |
| Véhicules Opex primaires (tous modes) | 162.8 | 165.6 | 2.8 |
| Véhicules Opex air | 140.8 | 156.8 | 16.0 |
| Véhicules Opex road | 19.5 | 5.8 | -13.8 |
| Véhicules Opex rail | 2.2 | 2.8 | 0.6 |
| Véhicules Opex water | 0.2 | 0.2 | 0.0 |

Véhicules issus de `decode_vehicles(target_owner=0)`, avec `physical_ok=true` ;
rail/route/air qualifiés. Le mode eau n'est pas qualifié : ses comptes restent descriptifs.
Les comptes 2-0 sont ceux du décodeur existant : ≥2 aéroports contre 0.

### C121 secondaire 20×10

**Deltas par graine** — k£/an pour profit/gap, % de valeur
par paire ; constructions TG ON/OFF = total des panneaux durables.

| Graine | Δprofit | Δgap | Δvaleur % | TG ON/OFF |
|---:|---:|---:|---:|---:|
| 42 | -80.6 | 1 193.7 | -5.3 | 16/0 |
| 100 | 184.8 | 1 459.1 | 34.2 | 9/0 |
| 7 | 223.1 | -2 709.8 | 17.4 | 14/0 |
| 999 | 84.1 | 1 369.1 | 3.2 | 12/0 |
| 2026 | -165.7 | -137.7 | -17.0 | 20/0 |
| 1 | 16.9 | -341.5 | -7.2 | 13/0 |
| 17 | -57.1 | 310.6 | 1.0 | 7/0 |
| 73 | 488.2 | 704.1 | 27.6 | 10/0 |
| 314 | 373.4 | 416.2 | 37.4 | 9/0 |
| 512 | 205.9 | -339.8 | 39.1 | 10/0 |
| 1024 | -49.9 | -1 199.0 | -16.5 | 13/0 |
| 1337 | -118.2 | 29.1 | 2.8 | 15/0 |
| 4096 | 33.5 | 791.8 | -3.1 | 9/0 |
| 8191 | -174.0 | 3 227.1 | -1.7 | 14/0 |
| 12345 | 331.0 | 2 031.2 | 27.2 | 9/0 |
| 54321 | 280.9 | -2 266.5 | 3.2 | 11/0 |
| 65537 | 671.1 | 576.9 | 125.4 | 7/0 |
| 123456 | 285.1 | 360.5 | 24.2 | 15/0 |
| 424242 | -184.8 | 91.1 | -9.9 | 14/0 |
| 8675309 | 287.6 | -673.3 | 19.0 | 10/0 |

Gap : médiane 335.6 k£/an, IC95 [-392.9; 882.2] k£/an, V/D/E=13/7/0, p=0.263176.

**Trajectoire annuelle et TG** — moyenne des deltas de fin d'année ;
TG = total des constructions sur toutes les graines puis moyenne par partie.

| Année | Δprofit k£/an | Δgap k£/an | TG ON/OFF total | TG ON par partie |
|---:|---:|---:|---:|---:|
| 1970 | 16.6 | 12.3 | 43/0 | 2.15 |
| 1971 | 77.9 | 106.5 | 45/0 | 2.25 |
| 1972 | 112.7 | 163.5 | 27/0 | 1.35 |
| 1973 | 76.7 | 148.8 | 21/0 | 1.05 |
| 1974 | 51.9 | 104.6 | 15/0 | 0.75 |
| 1975 | 89.0 | 178.0 | 31/0 | 1.55 |
| 1976 | 71.6 | 143.6 | 13/0 | 0.65 |
| 1977 | 120.9 | 379.3 | 19/0 | 0.95 |
| 1978 | 146.0 | 367.3 | 15/0 | 0.75 |
| 1979 | 131.8 | 244.6 | 8/0 | 0.40 |

**Créneaux et véhicules finaux** — moyenne par partie, comptes physiques.

| Métrique | ON | OFF | ΔOFF−ON |
|---|---:|---:|---:|
| Slots Opex | 20.8 | 22.3 | 1.6 |
| Slots AAA | 48.4 | 47.1 | -1.2 |
| Villes AAA≥2 / Opex0 | 12.6 | 10.6 | -2.0 |
| Villes Opex≥2 / AAA0 | 0.6 | 0.6 | 0.0 |
| Villes 1-1 | 17.2 | 19.1 | 1.9 |
| Véhicules Opex primaires (tous modes) | 177.2 | 177.3 | 0.2 |
| Véhicules Opex air | 143.1 | 154.7 | 11.6 |
| Véhicules Opex road | 24.5 | 10.6 | -13.9 |
| Véhicules Opex rail | 9.5 | 11.9 | 2.4 |
| Véhicules Opex water | 0.1 | 0.1 | 0.0 |

Véhicules issus de `decode_vehicles(target_owner=0)`, avec `physical_ok=true` ;
rail/route/air qualifiés. Le mode eau n'est pas qualifié : ses comptes restent descriptifs.
Les comptes 2-0 sont ceux du décodeur existant : ≥2 aéroports contre 0.

### Lecture pré-enregistrée et suite

- **C115 20×10** : absence de perte selon la règle opcodes pré-enregistrée ; town growth actuel ne paie pas ses opcodes selon cette règle. Future version ciblée à comparer à OFF. Cette lecture n'est pas une preuve d'équivalence ; le gain signs20 reste un critère séparé. Gain primaire signs20 : False ; garde valeur : True.
- **C121 secondaire 20×10** : absence de perte selon la règle opcodes pré-enregistrée ; town growth actuel ne paie pas ses opcodes selon cette règle. Future version ciblée à comparer à OFF. Cette lecture n'est pas une preuve d'équivalence ; le gain signs20 reste un critère séparé. Gain primaire signs20 : False ; garde valeur : True.

Aucun défaut modifié. Le comparateur de la future version ciblée découle de
cette lecture pour chaque socle ; C121 reste un résultat secondaire et ne
qualifie pas son économie face à C115. Les opcodes TG économisés n'ont pas
été remesurés ON/OFF ici : le coût motivant l'essai vient du profil C121
instrumenté antérieur. Aucune adoption opcode automatique n'est revendiquée.

## Provenance des campagnes retenues

Sources figées au SHA `1f07b4e3ed3d655bcd457b4c2a1ebedf4ed123d7`, arbre propre au lancement. Bundle commun vérifié : `c8d11b37ef893831711d713315793eee35de85a545dd031c90c37da3046b2552`. Les différences effectives des réglages sont exclusivement `town_growth` dans chaque A/B. Les sondes d'opcodes supplémentaires sont OFF dans les deux bras.

| Campagne | Résultat brut | Manifeste SHA-256 |
|---|---|---|
| `tg_off_default_5x6_20261002_r2` | `results/tg_off_default_5x6_20261002_r2.json` | `3875d0bdeba32066d47cfdd81513fc5c10a83bf087f70a7a6ee39db48c91238c` |
| `tg_off_default_20x10_20261002_r1` | `results/tg_off_default_20x10_20261002_r1.json` | `8d7844ee122d86ea94e71c98bb890c5246fea444db8fdda49141f5d09bf44ac5` |
| `tg_off_c121_20x10_20261002_r1` | `results/tg_off_c121_20x10_20261002_r1.json` | `150ca251286d8ca32d2821e588085fbdb88e4964a723cf96d2e144ce965e9e28` |

JSONL, logs et bundles locaux portent les mêmes identifiants uniques. Les hashes des résultats, JSONL, logs, sources et manifests sont dans l'audit versionné.

## Preuves

Conserver JSON/JSONL, logs, manifestes et bundles dans des dossiers de campagne
neufs. Résumé versionné avec `sweeps/package_review_evidence.py` dans un paquet
borné TG : l'audit global préexistant trouve 371 citations sans source, 269 non
archivées et zéro conflit ; il ne doit pas être remplacé ni déclaré complet.

Paquet TG : [résumé versionné](../evidence/review/town_growth_off_20261002/summary.json) et [index des archives vérifiées](../evidence/review/town_growth_off_20261002/index.json). Produit par le packager courant sur une racine temporaire limitée aux entrées TG, puis archives déplacées et chemins d'index ajustés. Hashes bruts/gzip revérifiés après déplacement ; index global historique inchangé. Le résumé détaillé et les audits complets sont aussi archivés en gzip. Les données ignorées restent sur le PC.
