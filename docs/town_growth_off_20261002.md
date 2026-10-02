# Town growth OFF — A/B PC du 2 octobre 2026

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
| Smoke défaut | `tg_default_smoke_1x1_20261002_r1` | `OpexAI` solo | 1 partie × 1 an, graine42 |
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
et `git diff --check` réussis. Runtime conteneur pré-vérifié ; smoke à exécuter.

## Résultats

En attente. Rapporter couverture/santé, verdict brut, deltas par graine,
moyenne/médiane/IC95, signes recomptés, évolution du gap, slots 2-0/1-1,
véhicules primaires décodés et constructions TG annuelles.

## Preuves

Conserver JSON/JSONL, logs, manifestes et bundles dans des dossiers de campagne
neufs. Résumé versionné avec `sweeps/package_review_evidence.py` dans un paquet
borné TG : l'audit global préexistant trouve 371 citations sans source, 269 non
archivées et zéro conflit ; il ne doit pas être remplacé ni déclaré complet.
