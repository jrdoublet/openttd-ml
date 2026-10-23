# AIR-ROI-RENFORT-1 — étape 2b ITT : campagne longitudinale 20×6 achevée (22/10/2026)

> **ARCHIVE HISTORIQUE — WIP LOCAL NON INTÉGRÉ (22/10/2026).** Résultats de simulations sur le `master` local HEAD `41031a7f` avec des modifications Squirrel non commitées. Les **40 parties** de cette campagne 20×6 sont documentées comme complètes, mais le seuil préenregistré de graines avec les deux affectations observables à 24 mois n'est pas atteint : l'effet marginal causal et la qualification économique demeurent **non établis**. L'option ITT de report est **expérimentale, non intégrée et non adoptée** par la branche d'archive. Les JSON, journaux, manifestes et données sous `results/` sont **locaux au WIP et non archivés ici** ; la présence éventuelle d'analyseurs Python versionnés ne constitue pas l'adoption du mécanisme.

## Statut final : 40 parties complètes, expérience ITT non concluante

**Reprise Docker terminée avec succès.** La campagne
`airr1_itt_month_20x6_20261022_a` a produit **40/40 parties saines et 20/20
paires complètes** avec les 20 graines du protocole §7. Le contraste compagnie
p50 − p0 à six ans est de **−38 927 £/an**, IC95
**[−205 760,5 ; +124 648,9] £/an** (bootstrap de graines). L'ITT d'exploitation
à 24 mois sur les séries valides vaut **+24 793 £/an**, IC95
**[+6 737 ; +45 681] £/an**, mais seulement **9 graines** disposent des deux
affectations évaluables, contre **10 exigées** : verdict scientifique
**`inconclusive`**. Aucun ROI physique net par appareil n'est identifié.

La campagne précédente `air_roi_renfort1_itt_exposure20x6_20261022` (237
assignations sur seulement quatre graines) reste partielle ; ses données ne sont
pas mêlées à la reprise. Voir l'[étape 2b initiale](air_roi_renfort1_etape2b_itt_20261022.md).

### Incident Docker antérieur, conservé comme historique

Le 22/10 à 14:21 (Europe/Paris), un smoke de trois ans a été lancé avec le harnais
`sweeps/run_c66_reference.py` sur le dépôt Windows `/openttd-ml` :

- HEAD `41031a7f24f8a60e8b671c954baeabe14088a145`, arbre **dirty** (code AIR-ROI
  en cours, RLW-04 et modifications partagées conservés) ; image Docker
  `openttd-lab:latest` `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659` ;
  contexte `desktop-linux` ; `--cpus 5 --max-workers 4 --memory 8g`.
- Bras `OpexAI[air_roi_renfort1_itt=1]` (p0 instrumenté) et
  `OpexAI[air_roi_renfort1_itt=2]` (p50, report 732 jours), graine 42, trois ans,
  une répétition, avec `--script-debug --line-telemetry --line-telemetry-monthly`.
- Le processus hôte est arrivé à `docker run` mais aucune partie ni sortie moteur n'a
  commencé. `docker ps` montrait zéro conteneur actif. Une seconde commande
  **minimale** `docker run --rm ... openttd-lab:latest python3 -c 'print(123)'`
  est restée bloquée de la même manière ; `docker version`, `docker info` et
  `docker image inspect` répondaient normalement. Aucun JSONL, log moteur ou
  bilan du nouveau smoke n'a été créé.
- Les trois commandes clientes Docker bloquées appartenant à cette session ont été
  arrêtées précisément, sans toucher aux conteneurs ou processus RLW-04. L'origine
  exacte du blocage Docker reste indéterminée. Cet incident est **clos par la
  reprise ci-dessus** ; il n'apporte aucune observation expérimentale.

## Mesure ajoutée (passive sous `air_roi_renfort1_itt > 0`)

`ai/OpexAI/air_flotte1_shadow.nut` initialise au moment de chaque assignation un
suivi identifié par `episode_id`, `lineId` et les `VehicleID` de la ligne. Le passage
de l'ordonnanceur (`scheduler.nut`) prend un relevé à chacune des **24 dates anniversaires
mensuelles** et émet `AIRR1_ITT_MONTH` dans le log moteur :

| Champ | Sens et provenance |
|---|---|
| `month_offset`, `date_due`, `date_actual`, `days`, `complete` | Mois 1..24, échéance, date réelle, intervalle et indicateur de continuité ; contrôle des retards et véhicules disparus |
| `vehicle_net_profit_gbp` | Variation du profit cumulé NoAI des avions de **cette ligne**, avec passage d'année géré par `GetProfitLastYear` ; comprend les charges d'exploitation des avions |
| `running_cost_est_gbp` | `GetRunningCost` annuel des avions présents, proratisé par les jours : **approximation**, pas dépense comptable exacte |
| `revenue_est_gbp` | Profit des avions + frais de roulage estimés : **reconstitution**, pas revenu brut officiel |
| `aircraft` | Nombre de `VehicleID` AIR actifs reconnus à la date du relevé |
| `maintenance_gbp`, `residual_value_gbp` | `na` : ventilation maintenance séparée et valeur résiduelle ligne non fiablement disponibles dans cette sonde |
| `scope` | `vehicle_operating_no_infrastructure`, jamais bénéfice complet incluant les aéroports et leur capital |

L'inventaire `line.vehicles` doit être présent pour éviter d'attribuer les appareils
d'une gare partagée à la mauvaise ligne. Une vente, un crash, un changement
d'identification ou un échantillonnage tardif invalide le suivi plutôt que de créer
un rendement artificiel. L'état de suivi est sauvegardé via la table ITT existante ;
la prochaine assignation de la même ligne attend la fin de la fenêtre. Sous mode 0,
la garde précède toute collecte et aucun état ITT n'est sérialisé.

L'auditeur `sweeps/audit_air_roi_renfort1_itt.py` consomme désormais ces événements
et produit séparément `itt_line_vehicle_operating_profit_last_12m`, les coûts de roulage
et revenus estimés sur les mois 13..24, ainsi que les cohortes de flotte initiale,
saturation cible et architecture. Il exige 24 mois uniques avec `complete=1`,
vérifie l'identité ligne/graine et l'identité `profit + running ≈ revenue`.
Son endpoint `itt_line_net_profit_last_12m` exige toujours un **net complet de ligne**
documenté ; la nouvelle sonde ne le fabrique pas, puisqu'elle n'attribue pas les
coûts d'infrastructure, dépréciation, entretien non ventilé et remplacements.

## Contrôles et smoke après redémarrage

Le 22/10 : **97 tests passés** avec `uvx --from 'pytest==8.4.2' pytest`,
`PYTHONPATH=.` (contrats ITT, auditeur ITT et historique, inventaires des réglages,
V161, C121 et autres suites AIR liées). Deux nouvelles fixtures vérifient le format
réel `AIRR1_ITT_MONTH`, l'ITT d'exploitation par graine et le rejet des séries
incomplètes. Ces tests précèdent la reprise. `git diff --check` a réussi ;
aucun commit/push.

Le nouveau smoke `airr1_itt_month_smoke42_3y_20261022_a` (graine 42,
référence `air_roi_renfort1_itt=1`, variante `=2`, trois ans) s'est terminé
**2/2 sans erreur moteur/Squirrel**, code 0, sur le bundle
`c3c1100fbb057590f287ddf6e6f0e2b3c63f2d11cea09d390a4cdc1d659ede22`.
Dans p50 : **21 assignations (7 treatment, 14 deferred)**,
**6 ajouts réussis déclarés**, et des `AIRR1_ITT_MONTH` mensuels réels
(`month_offset`, coût de roulage, profit d'exploitation et recette reconstruite).
Trois épisodes précoces ont 24 observations, mais `complete=0` après un
relevé tardif en janvier 1972 : les endpoints sont légitimement `null`.
Le smoke prouve le fonctionnement des événements et des commandes de renfort,
pas une série de 24 mois nécessairement exploitable.

## Campagne figée : protocole, qualité, reproductibilité

- **Exécution :** `sweeps/run_c66_reference.py`, deux duels
  `OpexAI[air_roi_renfort1_itt=1]` et `OpexAI[air_roi_renfort1_itt=2]`
  contre AAAHogEx par graine, **6 ans, une répétition, 20 graines** du §7,
  `--script-debug --line-telemetry --line-telemetry-monthly`.
  Docker Desktop `desktop-linux`, **5 CPU, 4 workers maximum, 8 Gio RAM**
  et cache `openttd-lab-home`. Aucune interruption de RLW-04.
- **Révisions :** HEAD `41031a7f24f8a60e8b671c954baeabe14088a145`,
  arbre `dirty` préservé ; image
  `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
  Bundle **`c3c1100fbb057590f287ddf6e6f0e2b3c63f2d11cea09d390a4cdc1d659ede22`**,
  manifeste **`42fa9b31d4b8ffc48258fa4fe48ef13db6a5e6cd9d6fb36675c39c53e8749a00`**.
- **Santé :** 40/40 `game_ok` et `game_status=complete`,
  20/20 paires, `comparison_complete=true`,
  `metric_coverage_complete=true`, sortie hôte 0,
  `policy_comparison.verdict=diagnostic_only` (20×6 n'est pas une porte V102).
- **Sorties :** `results/airr1_itt_month_20x6_20261022_a.json`,
  `.jsonl` (~446 Mo), `_engine/airr1_itt_p50_seed*_r0.log`,
  `.manifest.json` et
  `results/airr1_itt_month_20x6_20261022_a_itt_report.json`.
  Ce dernier est reproduit par :

```powershell
python -X utf8 sweeps/report_air_roi_renfort1_itt_20261022.py airr1_itt_month_20x6_20261022_a
```

L'auditeur fait **20 000 bootstrap de grappes par graine**, générateur
`random.Random(0)`, IC95 percentile. Les unités sont des assignations
intra-partie ; les **20 graines** sont les unités indépendantes. Les 1 291
assignations ne constituent jamais 1 291 répétitions indépendantes.

## Estimands préenregistrés et résultat final

| Mesure | Observations (treatment / deferred) ; graines avec les deux affectations | Estimation | IC95 bootstrap par graine |
|---|---:|---:|---|
| ITT **net complet de ligne**, mois 13–24 | 0 / 0 ; 0 | `null` | `null` |
| ITT **profit d'exploitation de tous les avions de la ligne**, mois 13–24, £/an | **13 / 30 ; 9** | **+24 793,40** | **[+6 736,89 ; +45 680,73]** |
| ITT **recettes reconstituées** des avions, £/an | 13 / 30 ; 9 | +30 355,55 | [+10 753,82 ; +52 709,91] |
| ITT **coût de roulage estimé**, £/an (surcoût treatment) | 13 / 30 ; 9 | +5 562,15 | [+3 370,26 ; +7 313,37] |
| Ratio ITT exploitation / premier étage **sur les seuls 43 épisodes observés**, £/an par ajout déclaré | 13 / 30 ; 9 | **+32 231,42** | **[+7 975,11 ; +61 179,45]** |
| Premier étage : avions `added=1` par assignation treatment − deferred | **703 / 588 ; 20** | **+0,894737** | **[+0,864000 ; +0,921898]** |
| Proxy VEHS, profit flotte (mois civils complets, distinct de la sonde ITT) | 388 / 374 ; 20 | +9 264,80 £/an | [+3 587,37 ; +15 284,11] |
| Compagnie p50 − p0, `profit_year` à six ans | **20 paires / 20 graines** | **−38 927 £/an** | **[−205 760,50 ; +124 648,85]** |
| Compagnie p50 − p0, valeur | 20 paires / 20 graines | **−2,623 %** (ratio des moyennes) | Voir rapport C66, garde de −5 % respectée |
| Projets d'investissement individuellement évincés et ROI physique net par appareil | non identifiables | `null` | `null` |

Le **premier étage** est bien exposé : **1 291 assignations p50**,
**703 treatment / 588 deferred**, 629 succès `added=1` déclarés par le
constructeur sous treatment (74 `added=0`), aucun ajout immédiat sous
deferred. Le coût comptable transactionnel moyen des 703 treatment, échecs
inclus, est **43 494,74 £** (médiane 32 812 £ ; 0 pour deferred). Ce coût
est celui de la transaction, éventuellement multi-unités ; aucun `VehicleID`
individuel du nouvel avion n'est certifié dans les issues constructeur.
L'estimand est l'effet d'une **assignation** de renfort sur le profit de tous
les avions de la ligne, pas le rendement de l'avion ajouté lui-même.

Le ratio descriptif de **32 231,42 £/an par ajout** utilise le premier
étage du **sous-échantillon de 43 observations complètes**
(10 ajouts parmi 13 treatment), pas le premier étage des 1 291
assignations. Il est conditionné par un suivi qui dépend de la trajectoire
post-assignation ; ses bornes bootstrap ne corrigent ni ce biais de
sélection, ni l'interdépendance réseau, ni l'absence de coûts d'infrastructure.
**Ne pas l'employer comme ROI marginal physique ni comme coefficient V161.**

**Seuil d'information préenregistré :** au moins 30 épisodes complets
**et 10 graines** avec les deux affectations. **43 épisodes satisfont le
premier critère ; seulement 9 graines satisfont le second. Verdict :
`inconclusive`**, même si l'IC95 du profit d'exploitation observé reste
positif. La comparaison compagnie est complète, mais son IC95 recoupe zéro.

## Suivi, censure et validité des séries

- **780/1 291 épisodes** possèdent les 24 décalages mensuels ; **511**
  ont moins de 24 mois ou aucune observation. Parmi les 780 complets en
  nombre, **737** sont invalidés par `complete=0` ou net manquant ;
  **43 seulement** sont exploitables pour le profit des avions.
- **913 épisodes** ont leur première rupture liée à un relevé tardif de
  plus de 7 jours, **159** une première rupture d'autre origine ou
  indéterminée (vente/crash, inventaire d'avions, continuité).
  Dès qu'une rupture est rencontrée, le suivi reste invalide : pas de
  compensation artificielle par la lecture ultérieure.
- La fin de la sixième année censure les affectations tardives ;
  refus `added=0`, renforts naturels ultérieurs, ventes/crashs et
  `REPLACE` ne sont pas retirés du registre d'assignation.
  L'attrition **diffère fortement entre bras** (13/703 treatment complets,
  30/588 deferred), de sorte que le contraste conditionnel observé peut
  être biaisé. Cette attrition limite bien plus la causalité que la largeur
  nominale de l'IC95.
- Les **0 endpoints nets complets** reflètent l'absence documentée de
  ventilation infrastructure, dépréciation et remplacements. Les
  `running_cost_est_gbp` et `revenue_est_gbp` sont des reconstructions,
  pas une facture complète.

## Cohortes prétraitement et comparaison V161 / modèle

| Cohorte | Assignations p50 | Épisodes 24 mois valides (treatment / deferred) | ITT d'exploitation £/an et IC95, descriptif |
|---|---:|---:|---|
| Flotte initiale **1** | 1 173 | 13 / 29 | +29 864 [+13 024 ; +50 412], 9 graines avec deux affectations |
| Flotte initiale **2** | 107 | 0 / 1 | `null` |
| Flotte initiale **3–4** | 11 | 0 / 0 | `null` |
| Flotte initiale **≥5** | 0 | 0 / 0 | `null` |
| Sous cible `vehCount < targetAirPlanes` | 1 291 | 13 / 30 | +24 793 [+6 737 ; +45 681] |
| Saturée `vehCount >= targetAirPlanes` | 0 | 0 / 0 | `null` |
| C121 `newpair` | 184 | 3 / 8 | +52 216 [−11 485 ; +115 383], 1 graine avec deux affectations |
| C121 `hubsite` | 766 | 8 / 15 | +21 074 [−1 843 ; +51 185], 5 graines |
| C121 `hubhub` | 341 | 2 / 7 | +561 [−22 538 ; +20 234], 2 graines |
| V161 source `prior` | 1 205 | 13 / 29 | 42 observations ; effet par source faiblement identifiable |
| V161 source `model` | 86 | 0 / 1 | `null` |

Les valeurs sont descriptives et **aucune cellule ne franchit
indépendamment la règle préenregistrée de 10 graines**. Les classes
`unknown` de flotte et `other` C121 sont vides ; en revanche
la cohorte distincte `v161_cohort` est `unknown` pour les 1 291
assignations (nombre d'échantillons marginaux absent du log).
Ici « saturation » est seulement la cible de taille de flotte atteinte ;
l'occupation physique des aéroports n'a pas été mesurée.

Au moment du choix, le champ `v161_model` porte une estimation de profit annuel
par avion : médiane **24 855 £/an** en provenance `prior` (1 205
assignations) contre **2 629 £/an** en provenance `model` (86
assignations). Le `roi` brut enregistré a respectivement pour médianes
**19** et **64,5** (unités du score de sélection). Les médianes des
devis sont **38 964 £** dans les deux groupes. Sur les 43 épisodes valides,
**42 sont `prior`** (13 treatment, 29 deferred) et **un seul est
`model`**, affecté deferred : la comparaison hors-échantillon du ROI
V161 avec un **profit marginal net physique** est `non identifiable`.
Les profits mesurés portent sur toute la ligne et le score ne doit pas
être divisé naïvement par le coût comptable.

## Politique p50 versus p0 et éviction potentielle

À six ans, le contraste p50 − p0 `profit_year` de −38 927 £/an
présente **11 V / 9 D / 0 E**, médiane **+95 102,5 £/an**,
Wilcoxon bilatéral `p=0,6742` et IC95 de moyenne recoupant zéro.
La valeur compagnie en ratio des moyennes est **0,973770**
(−2,623 %) ; elle respecte la garde descriptive −5 %. Ces écarts
incluent tous les changements de dépenses, disponibilité de caisse,
concurrence et portefeuille ; ils ne sont pas un effet local d'avion.

Les snapshots physiques appariés à six ans, p50 − p0, montrent :

| Stock final OpexAI | Δ moyen sur 20 graines | IC95 par bootstrap de graines |
|---|---:|---:|
| Avions | −14,55 | [−19,35 ; −9,45] |
| Véhicules ferroviaires | −0,35 | [−1,95 ; +1,15] |
| Gares ferroviaires | −0,50 | [−2,45 ; +1,40] |
| Aéroports | +1,75 | [+0,55 ; +2,95] |
| Véhicules routiers | +0,20 | [−1,00 ; +1,40] |

Il y a bien une différence de composition du réseau. **Aucun projet rail
ou autre projet précis n'est identifié comme évincé** par une chaîne
de décisions de financement et de construction appariées. Le signe
de la caisse, le classement C77 ou la différence du nombre de gares
ne prouvent pas une éviction causalement attribuable à un renfort
AIR. `displaced_investments_verified=null` reste la conclusion correcte.

## Limites, décision et suites éventuelles

Le contraste intra-partie repose sur la randomisation d'assignations
**après les gardes d'éligibilité** ; les lignes éligibles dépendent de
la concurrence et des choix antérieurs. Les lignes d'une même partie
s'influencent par trésorerie et réseau ; l'IC bootstrap rééchantillonne
donc les **graines**, jamais les ticks ni les avions. La longue
attrition et son déséquilibre treatment/deferred empêchent d'interpréter
les 43 épisodes complets comme une population représentative.
Les coûts de remplacement, l'infrastructure, la valeur résiduelle et
les investissements compensatoires ne sont pas alloués à l'avion
intervenu. La jointure VEHS par stations reste un **proxy** et n'est
pas la preuve comptable du profit de ligne.

**Décision : `inconclusive`** pour l'ITT marginal à 24 mois,
**`diagnostic_only`** pour la compagnie 20×6. Le défaut
`air_roi_renfort1_itt=0` reste en place, sans changement de score,
de prior, de V161, de priorité ni adoption de politique ; aucune porte
A/B V102 n'est déclenchée. Toute reprise prospective nécessiterait
un nouveau protocole d'observation capable de couvrir les échéances
mensuelles malgré les gels de l'ordonnanceur, puis une qualification
comportementale distincte. Aucune campagne fermée n'est relancée
et aucun commit/push n'a été effectué.
