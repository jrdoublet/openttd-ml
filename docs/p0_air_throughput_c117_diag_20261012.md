# P0 AIR — débit réel C117 et dilution du rendement 1973 (12/10/2026)

**Verdict : mécanisme de dilution de charge fortement compatible avec les observations, causalité du renfort et correction économique NON DÉMONTRÉES.** Le chantier P0 reste ouvert. Ne pas réactiver la concurrence visible C121 (`fail_primary`), le `air_fleet_dirty_sched` rejeté, ni fabriquer de nouvelle limite de flotte.

## Deux expériences distinctes, pas un appariement événementiel

1. Sur la **référence OFF** B20×10 (bundle `6f4657…`), 19/19 graines présentent un contraste négatif du delta YTD des vieux avions entre OD dont la flotte augmente et OD stables : 310 OD agrandies/434 survivants, −11 762 £/ancien contre +751 £ pour 416 OD stables/599 survivants. Parmi les 310, **195 améliorent la note PASS aux DEUX aéroports** ; **152 de ces 195** voient pourtant baisser les profits des vieux avions. Les renforts sont endogènes : les routes qui vont passer de 1→2 avions rapportaient déjà **37 191 £/ancien** en 1972 contre **14 694 £** pour celles qui resteront à 1. Les snapshots sont du **1er décembre** et ne donnent aucune date d'achat ni débit annuel. Voir [autopsie initiale](p0_conversion_projects_1973_20261012.md).
2. Pour examiner charge et cadence, un **nouveau stage indépendant** `results/p0_air_throughput_diag_stage_20261012` a été créé à `f6139d8`, avec les **trois overlays causaux C121 octet-identiques** à `p0_projects_causal_stage_20261012` et les 17 fichiers AAAHogEx-115 figés. Aucune édition d'un ancien stage, ni de `master` côté Squirrel. Flag préexistant `c117_air_throughput_probe=0` aux quatre difficultés, C121 station flux OFF, aucun changement de politique. Smoke OFF/ON 42×1 **2/2 sain**, 51 lignes C117 ON et zéro OFF ; puis diagnostic C66 `p0_air_c117_diag3x5_20261012` graines42/100/999 ×5 ans **6/6 jeux sains**, 0 `failed_runs`, bundle `04af9610318c9214da9664b17d9c6326ba17e332c8f3a4bc8d3cec1342e0a59f`, 6 workers/10 CPU/8g et `--script-debug --line-telemetry`. Les six logs et les sauvegardes traitées sont conservés dans le stage ; Docker libre après terminaison.

## Reconstitution des mêmes `lineId` dans le seul bras ON

Le décodeur [C117](../sweeps/analyse_p0_c117_throughput_20261012.py) suit le même `lineId` de 1972 à 1973, classe **augmentation/constance/diminution** par le nombre de véhicules à la dernière fenêtre observée de chaque année et somme les fenêtres d'âge de ligne par année de clôture. Il archive **5 028 fenêtres** (42 : 2 094 ; 100 : 1 550 ; 999 : 1 384), 111 lignes comparables (47 à flotte accrue, 64 stables), et **5 tests hôte verts**. Toutes les moyennes suivantes sont *par ligne*, non pondérées ; profits annualisés par jour-avion effectivement observé, pas comptes des compagnies.

| Graine | Lignes à flotte accrue / stables | Variation moyenne du profit par avion-année exposé — accrue | Stable | Δ du facteur de charge — accrue / stable | Δ cadence en jours — accrue / stable | Δ rating moyen — accrue / stable |
|---|---:|---:|---:|---:|---:|---:|
| 42 | 18 / 31 | **−9 603 £** | −6 124 £ | −0,026 / −0,019 | −9,5 / +2,6 | +3,7 / +0,3 |
| 100 | 15 / 16 | **−12 322 £** | +1 378 £ | −0,047 / +0,009 | −28,0 / −4,1 | +6,9 / −1,0 |
| 999 | 14 / 17 | **−32 934 £** | −1 286 £ | −0,091 / −0,026 | −29,9 / −8,7 | +7,5 / −0,1 |

Sur les **47 lignes agrandies**, 44 voient la durée de desserte estimée entre passages diminuer, 42 une amélioration du rating moyen, **38 une baisse du facteur de charge reconstruit**, et **36 une baisse du profit normalisé par avion**. **34/47** cumulent *profit par avion en baisse + facteur de charge en baisse + rating en hausse*. En moyenne interlignes, profit par avion-année exposé −17 420 £ sur agrandies contre −2 964 £ sur stables ; charge −0,052 contre −0,013 ; période entre vols −21,5 jours contre −1,9 ; rating +5,8 points contre −0,1. Cela correspond à une flotte plus fréquente mais moins remplie par appareil, **sans prouver que le renfort l'a causé**.

## Qualité de la mesure et perturbation

- C117 relève le chargement maximal **observé pendant chaque vol** à partir des ordres/états toutes les deux journées ; les passagers réels peuvent échapper au suivi. Les contrôles `invalid_order_samples` valent **2 688** sur agrandies et **2 543** sur stables, pour respectivement 7 827 et 9 605 *échantillons de ligne*. Attention : les invalides sont comptés **dans la boucle véhicules**, les échantillons au niveau ligne ; leur division **n'est pas un pourcentage de vols perdus**. `unobserved_transitions` vaut 9 et 8 sur les mêmes groupes. Ces asymétries peuvent biaiser les facteurs de charge et interdisent de traiter les valeurs comme débit réel exhaustif.
- La période C117 est un **bucket d'âge de ligne d'environ 30 jours**, non une clôture au 31 décembre. Les fenêtres peuvent traverser le changement d'année ; `profit` est une différence de profits YTD véhicule observée, non `profit_year`, et `run_est` est estimatif. L'analyseur conserve jours et fenêtres observés, sans extrapoler 365 jours de données absentes. Les lignes sorties du registre entre dates sont exclues de la comparaison par identifiant.
- La sonde ON modifie les trajectoires. Delta 1973 de profit comptable ON−OFF : graine42 **−62 543 £**, 100 **+19 989 £**, 999 **+46 591 £**. Ce n'est ni un signal d'adoption ni l'effet d'un renfort. **Aucun appariement événementiel avec OFF ou avec la référence N19** malgré le mécanisme compatible ; 3 graines ne constituent pas une porte V102.

## Contrôle complémentaire — date d'achat encadrée et fenêtres réellement avant/après

L'audit de la transaction dans `task_projects.nut:206–326` révèle un journal **préexistant** et inconditionnel `[FLEET_PROJECT] line=… added=… replaced=…` après achat, qui n'avait **pas** été exploité. Plutôt que créer une autre sonde, le décodeur hôte [des achats](../sweeps/analyse_p0_air_c117_purchase_events_20261012.py) encadre chaque émission par les dates de jeu immédiatement avant et après dans le **même log moteur partagé Opex/AAA**. Il ne confond pas les horodatages muraux 2026 avec 1970–1974. Sur les **134 acquisitions enregistrées** (42 :54, 100 :40, 999 :40), **98** sont bornées à 0–2 jours de largeur, et toutes à **12 jours maximum**. Aucune date précise n'est inventée quand les bornes diffèrent.

Pour l'analyse locale, on ne retient que les achats +1 sans remplacement avec une fenêtre C117 achevée **avant la borne inférieure** de l'achat et une autre fenêtre commencée **après la borne supérieure** ; les fenêtres doivent appartenir au même `lineId` **et au même `build_date`**, être distantes de 90 jours au plus des bornes, offrir des sièges observés, et aucun autre renfort de cette ligne ne doit les séparer. **131 achats** satisfont ces critères toutes années confondues, **47 en 1973** (42 :17, 100 :15, 999 :15).

| 1973, seul bras C117 ON | Graine42, 17 achats | Graine100, 15 achats | Graine999, 15 achats | Ensemble, 47 achats |
|---|---:|---:|---:|---:|
| Remplissage estimé **en baisse immédiatement après** | 3 | 10 | 8 | **21/47** |
| Passagers transportés estimés par 30 jours en hausse | 13 | 11 | 8 | **32/47** |
| Sièges offerts par 30 jours en hausse | 13 | 15 | 12 | **40/47** |
| Profit observé normalisé par jour-avion en baisse | 10 | 10 | 9 | **29/47** |
| Delta moyen de facteur de charge | +0,049 | −0,018 | −0,023 | hétérogène |

**Ce contrôle empêche de transformer l'association annuelle en causalité directe :** la dilution observée sur l'année **ne se manifeste pas systématiquement immédiatement après le renfort**. Sur la graine42, les fenêtres proches des achats suggèrent même un **remplissage initial amélioré**, tandis que l'évolution annuelle des flottes agrandies est défavorable. Le signal peut être différé, dépendre de l'évolution de la demande et de la concurrence, de l'âge de la liaison, ou être partiellement lié aux limites de mesure des vols. Le pré/post n'est pas un contrefactuel : saison, sélection endogène, nouveaux compétiteurs, occupation des hubs et variations de dates demeurent incontrôlés.

Le fichier [détaillé des 134 achats et 47 pré/post en 1973](../evidence/review/p0_projects_conversion_20261012/p0_air_c117_purchase_events_diag3x5_20261012.json) contient les bornes, fenêtres, niveaux avant/après et SHA256 des trois logs. Décodeur **3 tests hôte verts** ; contrôle `build_date` empêchant d'associer un éventuel `lineId` recyclé ajouté au décodeur C117 (**6 tests**). **Aucun nouveau Docker, aucun flag comportemental.**

## Prochain test réellement causal

Avant tout flag comportemental, compléter les **dates désormais bornées** d'achat par la cible C121, ses hypothèses de revenu marginal, le profit réalisé avant/après, l'état réel de la demande et de la concurrence, le capital alors disponible et la position du projet suivant. Il faut surtout un **contrefactuel de décision** qui conserve l'OD, le budget et la demande initiale avec vs sans renfort, sans imposer une priorité ou limite fictive : le comportement d'autres services et l'ordonnanceur peuvent changer. Une telle intervention serait ensuite isolée par flag OFF, tests, Save/Load et portes A40×3 puis B20×10 si A survit ; opcodes globaux et `profit_year` 1973 resteraient les métriques décisionnelles. Aucune expérience économique n'est pré-enregistrée aujourd'hui.

**Fichiers vérifiables :** [données détaillées avec hashes des logs, du manifeste et du JSON C66](../evidence/review/p0_projects_conversion_20261012/p0_air_c117_diag3x5_20261012.json), `sweeps/test_analyse_p0_c117_throughput_20261012.py` (6 tests verts), `sweeps/test_analyse_p0_air_c117_purchase_events_20261012.py` (3 tests verts), logs/sauvegardes dans le stage gelé. Aucune adoption, aucun commit/push.
