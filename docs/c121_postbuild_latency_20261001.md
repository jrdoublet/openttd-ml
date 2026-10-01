# C121 — diagnostic post-chantier (lot 2, 01/10/2026)

> **Rectification du 01/10 : témoins contaminés.** Les dix journaux désignés
> sans sonde contiennent `POSTBUILD`. Le filtre ON/OFF est **invalide**, non pas
> passé. Les copies préparées/hachées ne prouvaient pas leur chargement distinct.
> Les chiffres ci-dessous restent descriptifs de trajectoires instrumentées ;
> le −41,33 % n'est pas une comparaison sans sonde. La santé et la récupération
> des checkpoints restent établies, pas la conformité du protocole comparatif.
> Voir [rectification et autre piste](c121_investments_20261001.md).

## Plan avant exécution

Demande « prochaine étape » après le correctif cache. Diagnostic uniquement,
aucune source de production modifiée. C115 protégé ; économie C121 et catalogue
incrémental activés uniquement dans les bras explicitement nommés C121.
Pas de variante AIR première année, stock-growth, territoire, C122 ou cadence.

Hypothèse : la régénération synchrone post-chantier (notamment `staged_full`)
retarde le prochain investissement. Chercher l'exposition, pas supprimer une
branche sur la seule foi de son coût. Une liste sélectionnée n'est pas une
preuve de disponibilité physique ni de financement continu.

### Inventaire des mesures

- `PROJECTS_COST` fournit les coûts build/flotte/régénération et le chemin,
  mais pas l'identité de passe, ses dates, les retours anticipés ni le prochain
  investissement. `AIR_PLAN_PERF.days` reste un quotient ticks/74.
- C39/C50/C56 et les sondes larges apportent des traces mais leur perturbation
  a déjà été observée ; ne pas les réarmer ensemble.
- Les smokes du lot cache n'ont ni ces frontières ni un témoin de perturbation.
  Ils ne permettent pas de mesurer la latence post-chantier demandée.

Ajout **dans une copie seulement** : identités passe/événement, marques jour
NoAI/tick et `OpexOpsMeasureBegin/End` autour de flotte et régénération existantes,
issues réelles des exécuteurs, motifs de fin et compteur de caducité déjà testée.
État O(1) de dispatch (invalidé, taille de liste, phase rail) ; pas de scan du
portefeuille, de carte, second choix ou nouveau test de liveness.
Financement publié seulement si la garde métier l'a déjà calculé.

### Campagnes bornées / portes

1. Contrats lecteur/staging puis smoke **42×1 an**, C115 tracé et C121 tracé,
   chacun contre AAAHogEx-115. Santé complète, sources/copies inchangées,
   au moins une régénération post-chantier close et une issue réelle par bras.
2. Si exposé/sain : **5 graines ×3 ans ×4 bras**, graines
   42/100/999/1234/5678, fin 1973-02-01. Bras C115, C115 tracé, C121, C121 tracé.
   Deux paires ON/OFF servent à constater la perturbation séparément par modèle.
   Pas de neutralité revendiquée, pas d'adoption, pas de 5×6/20×10 automatique.
   Budget : 2 smokes +20 duels courts, maximum trois workers, un conteneur
   3 CPU/2 Go sans swap, volume `openttd-lab-home`, runtime et image du lot 1.

Primaire diagnostique : jours/ticks et opcodes conventionnels de régénération
par chemin et année. Délais construction→régénération terminée→prochain dispatch,
prochaine tentative et prochaine construction, en distinguant renforts et
nouvelles lignes. Agrégats par graine, pas un pooling de centaines de passes
comme observations indépendantes. Une fin ouverte est censurée, jamais zéro.
Les intervalles entre événements incluent le travail non instrumenté ; ils ne
sont ni un coût CPU ni une attente financière continue.

Filtre de confiance exploratoire de la sonde, séparément C115/C121 : profit
moyen ON/OFF ≥95 %, valeur ≥95 %, ≥3/5 deltas de profit non négatifs. Échec :
mesures valables uniquement sur trajectoire instrumentée, aucune estimation
du gain récupérable ni optimisation automatique. Même passage ≠ neutralité.

Sources exécutées copiées et hachées avant les parties (adversaire compris).
Manifestes, réglages effectifs, logs/checkpoints et résultats dans un nouveau
dossier `results/c121_postbuild_latency/`. Git absent : pas de SHA inventé.

## Résultat et récupération indépendante

- `smoke_20261001_r1/report.json` : deux smokes sains, exposition et intégrité OK.
- `exposure_20261001_r1/` : les vingt jeux ont atteint le dernier checkpoint,
  mais le processus a reçu `KeyboardInterrupt` pendant l'assemblage final
  (`savegame_rows_async_result.get()`). **Pas de `report.json` original, pas
  de succès de processus revendiqué, aucune partie rejouée.**
- Relecture par `sweeps/analyse_c121_postbuild.py`, reçu neuf
  `exposure_20261001_r1/recovery_report_r1.json` : **20/20 parties saines**,
  38 dates mensuelles uniques chacune, du 1970-01-01 au 1973-02-01 ; profits
  annuels et compteurs physiques complets selon les helpers existants.
  Les dix traces sont exposées/intègres : uniquement des attentes du prochain
  événement censurées à la fin, aucune phase ou passe ouverte.
- Sources du manifeste initial, copies exécutées et fixture inchangées.
  Les deux fichiers ajoutés après campagne (lecteur hors moteur et ses tests)
  sont explicitement listés ; SHA256 des 40 logs/JSONL, plan et lecteur conservés.
  Les chemins `/work` sont adaptés en mémoire seulement pour la lecture Windows.
- **101 contrats Python ciblés réussis** après récupération (97 précédemment,
  plus quatre tests du lecteur). Pas de nouvelle suite complète revendiquée.
  Aucune modification de production dans ce lot ; C115 protégé et défauts OFF.

### Perturbation : ancien calcul retiré (témoins contaminés)

Dernière année complète 1972 ; valeur au checkpoint final. Deltas ON−OFF :

| Modèle | Δ profit moyen / médian | Δ profit moyen % | Δ valeur % | Graines non négatives |
|---|---:|---:|---:|---:|
| C115 | 0 / 0 £ | 0 | 0 | 5/5 |
| C121 | +472 / 0 £ | +0,063 | +0,908 | 5/5 |

Par graine 42/100/999/1234/5678 : C115 = 0/0/0/0/0 £ ;
C121 = 0/0/+2 360/0/0 £. Les trajectoires ne sont donc pas strictement
identiques pour C121. Ces calculs ont été initialement interprétés à tort comme
un filtre passé : tous les bras étaient instrumentés. **Aucun verdict de
perturbation valide.** Le reçu original est conservé ; la rectification indépendante
`identity_investments_correction_r1.json` retire cette interprétation.

## Ce qui bloque réellement dans le périmètre observé

### 1. Les régénérations récurrentes ne sont pas le handicap comparatif principal

Sommes des durées calendaires des **phases de régénération closes**, par jeu ;
les colonnes annuelles affectent chaque phase à son année de début. La phase
`fleet` est exclue. Ce ne sont ni l'ensemble du travail catalogue en arrière-plan,
ni des jours automatiquement récupérables.

| Graine | C115 : 1970 / 1971 / 1972 (j) | C121 : 1970 / 1971 / 1972 (j) | Total C115 / C121 (j) |
|---|---:|---:|---:|
| 42 | 101 / 112 / 65 | 61 / 7 / 12 | 278 / 80 |
| 100 | 88 / 116 / 109 | 43 / 6 / 13 | 313 / 62 |
| 999 | 146 / 114 / 60 | 107 / 13 / 20 | 320 / 140 |
| 1234 | 127 / 129 / 61 | 75 / 6 / 10 | 317 / 91 |
| 5678 | 126 / 100 / 72 | 119 / 17 / 6 | 298 / 142 |

Chemin `incremental` : médianes par graine **10–18 jours pour C115** contre
**1–1,5 jour pour C121**. Attention : ce nom décrit la branche de mise à jour du
portefeuille, pas nécessairement le catalogue AIR C121. Aucun chemin `full`
hors bootstrap observé. `fleet` coûte 2–27 jours cumulés C115, 0–1 C121.
Les distributions jours/ticks/opcodes, avec n/médiane/p95/max, sont conservées
par graine, année et chemin dans `metrics.phases_by_year` du reçu.

### 2. Une reconstruction de démarrage longue est exposée sur les cinq cartes

Première fenêtre C121 `staged_full`, étape 0 :

| Graine | Début | Jours réels | Ticks | Proxy opcodes | Fin→prochaine construction (j) |
|---|---|---:|---:|---:|---:|
| 42 | 1970-01-21 | 39 | 731 | 7 305 914 | 46 |
| 100 | 1970-01-10 | 29 | 538 | 5 370 197 | 17 |
| 999 | 1970-01-13 | 71 | 1 311 | 13 106 748 | 18 |
| 1234 | 1970-01-13 | 50 | 917 | 9 161 324 | 23 |
| 5678 | 1970-01-13 | 79 | 1 457 | 14 564 910 | 105 |

Quatre fenêtres `staged_full` par jeu C121, toutes en 1970, cumul **39–113 j**.
La première représente 29–79 j (médiane inter-graines 50 j).
La graine42 est une reconstruction **après abandon/rejets**, sans construction
dans cette passe : `built=0`, 27 issues rail rejetées. Ne pas la présenter comme
une latence après achat. Les quatre autres premières fenêtres ont une construction
antérieure dans la même passe. Aucun attribut de rentabilité marginale n'est mesuré.

Relecture de `task_projects.nut` : sous `STAGED_BOOTSTRAP`, `_tryBuildProjects`
appelle encore `_rebuildProjects(fleetPlan)` synchroniquement. Le recyclage d'un
lot AIR existant dans `_rebuildProjects` est conditionné au mécanisme C78 et à
son seuil de villes ; ce constat ne démontre pas à lui seul quel sous-bloc
consomme les 29–79 jours dans C121. **Cible localisée, gain causal non établi.**

### 3. L'intervalle après régénération reste distinct de son coût

Médianes par graine, dans l'ordre 42/100/999/1234/5678, en jours :

| Intervalle clos | C115 | C121 |
|---|---|---|
| Fin régénération→dispatch | 35,5 / 6 / 32 / 21 / 38 | 9 / 8 / 10 / 10 / 11 |
| Fin régénération→tentative | 38 / 15 / 34 / 27 / 38 | 10 / 9 / 12 / 12 / 12 |
| Fin régénération→construction | 39,5 / 19 / 35 / 37 / 38 | 23,5 / 20 / 22 / 24 / 30 |
| Entre issues nouvelles lignes | 1 / 30 / 1 / 8 / 1 | 22 / 30 / 24,5 / 26 / 30 |
| Entre issues renforts `fleet` | 46,5 / 52 / 43 / 60,5 / 54 | 13,5 / 20 / 27 / 48,5 / 0 |

Les faibles intervalles C115 entre nouvelles lignes reflètent aussi les lots de
constructions ; ne pas en déduire une cadence régulière. Les renforts observés ici
ne couvrent que les exécuteurs instrumentés, pas chaque achat hors portefeuille.
Les fenêtres fin→prochain événement peuvent se recouvrir : ne pas les additionner.
Attentes finales censurées : 6 C115 et 8 C121 ; aucune n'est remplacée par zéro.

Aucun dispatch avec `invalidated=1` dans les dix traces. Arrêts observés par la
garde instrumentée : C115 **23 K_pass /50 cash**, C121 **62 K_pass /54 cash**.
Parmi K_pass, financement connu/suffisant **16 C115 /48 C121**, les autres
inconnus (renforts). Cela ne couvre pas tous les refus de financement : le hook
`stop` vise une garde précise. Même financement suffisant au point observé ne
prouve ni liveness continue ni attente financière inutile jusqu'au prochain achat.

## Contrôle économique descriptif, témoins eux aussi instrumentés

Il compare ici, sur des trajectoires instrumentées, **le paquet économie+catalogue C121** à C115 après le correctif
cache, pas le cache seul ni la seule cadence. Profit Opex de l'année1972 :

| Graine | C115 (£/an) | C121 (£/an) | Δ C121−C115 |
|---|---:|---:|---:|
| 42 | 1 397 442 | 737 425 | −660 017 |
| 100 | 524 041 | 507 796 | −16 245 |
| 999 | 1 837 469 | 1 048 369 | −789 100 |
| 1234 | 1 152 567 | 592 598 | −559 969 |
| 5678 | 1 476 073 | 861 697 | −614 376 |

Moyennes **1 277 518 contre749 577 £/an**, delta moyen **−527 941 £/an
(−41,33 %)**, médian **−614 376 £/an**, cinq deltas négatifs. Valeur **−36,11 %**.
AAAHogEx moyen : 2 311 474 £ face à C115, 2 721 319 £ face à C121 ; moyenne des
ratios Opex/AAA **55,52 % contre27,99 %**. Le ratio s'améliore sur100 seulement
par baisse de l'adversaire, malgré la perte Opex : ce n'est pas une réussite.
Au dernier checkpoint, avions primaires moyens **56 contre21,6**, aéroports
**21,8 contre13,4** (décodeurs physiques, pas `len(VEHS)`).

## Conclusion / prochaine intervention proposée

**Diagnostic clos ; C121 non adoptable à ce stade.** Le poids des régénérations
récurrentes mesurées ne suffit pas à expliquer son retard : il est déjà moindre
que chez C115. Ne pas augmenter globalement les budgets ni modifier K_pass/R4,
le classement ou la flotte pour « corriger » cette seule métrique.

Proposition historique, non implémentée et écartée de la priorité après la demande
« essaie autre chose » : isoler le retour synchrone du **bootstrap
C121 à l'étape0**, puis traiter sa continuation sans modifier simultanément
l'économie. Vérifier réemploi/invalidation du lot publié, curseur actif, progression
des étapes et Save/Load ; ne pas simplement supprimer `_rebuildProjects` ou
réutiliser des candidats caducs. Exiger exposition et baisse du coût ciblé,
puis investissement effectivement avancé et comparaison économique isolée.
Ce poste ne garantit pas de combler les −41 % : le lien choix initial→croissance
de ligne→profit réalisé reste à établir séparément. Aucun nouveau banc déclenché,
aucun 20×10 autorisé par ce résultat.

Suite courante : analyse descriptive des investissements, pas optimisation du
bootstrap. La correction du lanceur charge chaque bras séparément et vérifie
la présence/absence de sonde dans **tous** les bras. Contrats Python validés,
validation moteur de cette correction non exécutée ; aucune nouvelle campagne.