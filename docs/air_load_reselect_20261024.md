# AIR-LOAD : audit de la resélection — 24 octobre 2026

## Décision

**Refus motivé du correctif `air_load_reselect` : le blocage allégué n'est pas
établi et le refus flotte ne termine pas le balayage.** Le portefeuille passe
déjà au projet suivant. L'absence de purge immédiate des anciens renforts est
réelle, mais elle ne démontre pas une file arrêtée derrière leur premier refus.
En décembre 1972, les 17 sélections observées du bras testé sélectionnent
**tous** leurs candidats ; une nouvelle sélection du même vivier n'y révèle
aucun projet supplémentaire.

Aucun Squirrel, réglage, score ou état persistant modifié ; `air_load_min_pct`
reste à **0**. Aucun `AIR_LOAD_RESELECT` ajouté : la condition utilisateur de
mise en œuvre du levier n'est pas satisfaite. Cela ne qualifie ni la garde
seule ni un autre levier économique.

## Entrées et méthode

- Branche locale `air-load-reselect`, point de départ propre
  `07f7785b` (garde AIR-LOAD-1 sur `origin/master`).
- Campagne existante **`airload_cash_5x3_20261024`**, cinq graines
  **42, 100, 7, 999, 2026**, une répétition, 1970–1972 : deux duels distincts
  par graine contre la même AAAHogEx. Bras `reference` contre `airload50log`,
  réglages explicites `air_load_min_pct=0` contre **50**, `probes=258` des
  deux côtés. Ce diagnostic ne mesure pas le seuil 30.
- Le chemin annoncé dans le dépôt principal n'existe pas. Les originaux
  ont été retrouvés à l'emplacement déclaré dans
  `/home/deploy/agy_runs/vivier/analyse.py:31` :
  `/home/deploy/.claude/jobs/e230de46/tmp/wt_airload/results/`.
  Lecture seule de ce dossier et du rapport agy ; sorties dans ce worktree.
- Manifeste : SHA-256
  `1b25ee9e5a95622b254c4ae42b39f5d46f69bd787e4aee7d6e039a8ff52437cb`.
  Bundle **121 fichiers**, empreinte complète revérifiée par
  `campaign_freeze.fingerprint_tree` :
  `705bc1f8a41314234e229d3994c04b01199d68ec0f72fab93caa682056af98fa`.
  SHA déclaré `9b3bd86d32e0b3b014505d90ff396d6488e7f0a5`, état dirty
  déclaré : seuls cinq journaux de validation non suivis. L'empreinte du
  bundle, plutôt que ce seul SHA, identifie les entrées exécutées.
- Dix duels `game_ok=true`, `game_status=complete`, cinq paires complètes,
  `comparison_complete=true`, `metric_coverage_complete=true` ;
  **`adoption_sample_complete=false`**. Dernier checkpoint requis :
  1972-12-01 ; les journaux continuent en décembre. Pas de nouveau banc.

[Analyse reproductible](../sweeps/analyse_air_load_reselect.py) : décodeur
`analyse_rail_freight_dlog.decode_line`, noms de fichiers
`parse_air_finance_margin.parse_log_filename`, filtre propriétaire 0,
contrôles du manifeste, du bundle et de la santé enregistrée. Les
[résultats détaillés](../evidence/review/air_load_reselect_20261024/diagnostic.json)
conservent hashes des dix logs, comptes annuels, blocs de rejets observables,
clichés et événements de décembre avec numéros de lignes. Ce fichier est une
preuve dérivée, pas un remplacement des originaux ni une nouvelle campagne.

Reproduction, sortie neuve dans le worktree :

```bash
PYTHONDONTWRITEBYTECODE=1 python3 sweeps/analyse_air_load_reselect.py \
  /home/deploy/.claude/jobs/e230de46/tmp/wt_airload/results \
  --out results/air_load_reselect_20261024/reproduction.json
```

## Diagnostic statique

| Étape | Code courant | Conclusion |
|---|---|---|
| Injection | `ai/OpexAI/scheduler_tasks.nut:945` | `airCount > 0` conditionne bien l'injection ; plan vide : pas de purge à ce site. |
| Purge | `ai/OpexAI/projects_update.nut:15` | `OpexInjectFleetProjects` retire les anciennes entrées fleet puis appelle la resélection (`:41`). |
| Garde à l'achat | `ai/OpexAI/task_projects.nut:239` | Retourne **`outcome="rejected"`**, sans marquer d'abandon de paire. |
| Appelant | `ai/OpexAI/task_projects.nut:1285` et `:1328` | Seul `pending` prend la sortie anticipée ; `rejected` atteint **`continue`**, qui avance le rang. |
| Mise à jour finale | `ai/OpexAI/task_projects.nut:1546` | Sans achat ni abandon, pas de mise à jour incrémentale : constat exact du rapport, mais le reste de `best` a déjà été parcouru. |
| Financement | `ai/OpexAI/projects_selection.nut:720` | Les projets sont testés **individuellement** contre le budget ; la somme des capitaux sélectionnés n'est pas une réservation cumulée. |
| Comptage | `ai/OpexAI/projects_selection.nut:1057` et `:1110` | `remaining=max(0,budget-somme(capital sélectionné))` ; `next_capital` vise un candidat dépassant le budget, pas nécessairement le rang suivant. |

Les corps `_tryBuildFleetProject`, `_tryBuildProjects` et `_dispatchAirFleet`
du bundle et du code courant sont identiques à l'octet (hors signature et
accolades, extraction du helper de contrat existant). SHA-256 respectifs :
`928f019af400bc5bcda4ae732d5ac2e407943e573353b8aae88daf26a21d3d8a`,
`7cb8b962e6822f4c872206f21a0957449e8078815d85cd52d634e5f311f373c2`,
`a4cfd26cc7e75cab0f7ce3264994857fb61b0383b6bfc10b3233f5bbefdfc267`.

**Zéro sortie prématurée par le retour `rejected` de la garde dans ce flot
de contrôle.** Un classement devenu ancien peut différer d'une sélection sur
une caisse rafraîchie, et la limite TOP64 peut cacher des alternatives : cela
reste une autre hypothèse, non démontrée par ces journaux. Les deux bras ont
deux clichés TOP64 en 1972, aucun en décembre dans le bras testé (maximum 25).

## Ce que disent réellement les rejets

| Observation sur 1970–1972 | Référence | Garde 50 |
|---|---:|---:|
| `AIR_FLEET reason=low_load_factor` | 0 | **1 717** |
| `FLEET_PROJECT action=refuse reason=low_load_factor` | **0** | **0** |
| `PROJECT_DISCARD mode=fleet reason=low_load_factor` | **0** | **0** |
| `PROJECT_DISCARD mode=fleet reason=fleet_grow_failed` | **58** | **73** |
| Blocs contigus de rejets contenant au moins un fleet | 37 | **39** |
| Dont rejet fleet au rang 0 | 31 | **33** |
| Dont un rejet de rang supérieur après un rejet fleet | 15 | **21** |

Les 39 blocs du bras testé se ventilent par graine : 42 **12**, 100 **5**,
7 **6**, 999 **7**, 2026 **9**. Ils attestent au moins 39 passes avec un échec
flotte journalisé et sans achat final ; **ils ne recensent pas toutes les
passes**. Les 21 blocs avec plusieurs rangs fleet réfutent directement
l'idée d'un arrêt au premier fleet refusé, même pour `fleet_grow_failed`.

Le rapport agy §2.3 attribue **38** refus d'exécution à `low_load_factor` et
compte 37 `fleet_grow_failed` en référence : ces chiffres ne sont pas
retrouvés dans les originaux. La branche `fleet_grow_failed`
(`task_projects.nut:300`) suit l'appel à `OpexAirAddPlane` et signifie qu'aucun
ajout/remplacement n'a réussi. La garde aurait retourné plus tôt avec la
raison distincte `low_load_factor`. Le sous-motif de l'échec d'ajout n'est
pas conservé ici ; impossible d'en déduire achat API, moteur, hangar ou caisse.

**Censure explicite :** `AIR_FLEET` est dédupliqué par ligne/mois
(`task_air.nut:447`), donc 1 717 n'est ni un nombre de passes ni un nombre
exhaustif de tentatives. `PROJECT_DISCARD` final est plafonné à trois entrées,
sur la première passe journalisée du mois et seulement sans achat
(`task_projects.nut:1165`, `:1522`). `TASK` est émis paresseusement au premier
événement de la tâche (`probes.nut:42`). **Zéro événement d'exécution sous
garde observé ne prouve pas zéro appel non journalisé.** Un nombre exhaustif
de passes « finissant sur un refus de garde » n'est pas récupérable dans ces
logs ; le code exclut en revanche la sortie anticipée supposée.

## Où reste le budget

Chaque cliché VIVIER est partitionné sans convertir un inconnu en zéro.
Les montants ci-dessous additionnent les `remaining` : unité **£-clichés**.
Les mêmes livres peuvent réapparaître à plusieurs dates ; ces sommes ne sont
ni des flux dépensés, ni une mesure causale des livres libérées par la garde.
La moyenne est pondérée par les événements de sélection, pas par le temps
ni également par graine. `selection_pool_capital` n'est pas du capital engagé.

| Catégorie du reliquat | Référence 1972 : clichés / £-clichés | Garde 50, 1972 : clichés / £-clichés | Référence décembre | Garde 50, décembre |
|---|---:|---:|---:|---:|
| Vivier vide (`considered=0`) | 5 / 463 139 | 17 / 2 563 804 | 0 / 0 | **4 / 911 650** |
| Candidat trop cher (`next_capital>budget`) | 167 / 4 022 082 | 40 / 984 279 | 24 / 638 588 | **0 / 0** |
| Tous sélectionnés, aucun candidat supplémentaire | 19 / 1 450 005 | 107 / 7 858 984 | 0 / 0 | **4 / 561 929** |
| Autre cas de sélection non résolu | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| Reliquat nul (somme du pool ≥ budget) | 407 / 0 | 219 / 0 | 27 / 0 | 9 / 0 |
| **Total** | **598 / 5 935 226** | **383 / 11 407 067** | **51 / 638 588** | **17 / 1 473 579** |

Moyenne du reliquat en décembre : **12 521,33 → 86 681,12 £**, retrouvée.
Sous garde : **61,87 %** des £-clichés positifs avec vivier vide,
**38,13 %** sans candidat supplémentaire. **Le montant attribuable à une file
bloquée par la garde n'est pas mesurable** ; les logs ne permettent pas une
ventilation générale du budget en causes d'exécution, en plus de cette
partition des sélections. Ils montrent aussi des recherches rail en cours,
des refus de site et de trésorerie effective malgré des devis finançables.

Les huit clichés à reliquat positif du bras testé, tous avec `rejected=0`
et `next_capital=-1` :

| Graine / date | Candidats sélectionnés | Reliquat £ | Log `airload50log_seedN_r0.log`, ligne |
|---|---:|---:|---:|
| 100 / 26 décembre | 0 | 155 971 | 22383 |
| 7 / 10 décembre | 1 rail | 149 808 | 24658 |
| 7 / 20 décembre | 0 | 316 721 | 24768 |
| 2026 / 7 décembre | 3 rail | 55 770 | 23966 |
| 2026 / 12 décembre | 1 rail | 147 672 | 24034 |
| 2026 / 14 décembre | 0 | 188 238 | 24080 |
| 2026 / 22 décembre | 2 air | 208 679 | 24325 |
| 2026 / 23 décembre | 0 | 250 720 | 24333 |

Ce ne sont pas huit files dominées par un fleet : aucun fleet n'appartient
à ces huit viviers. La caisse ne peut donc pas revenir à un projet déjà
classé absent. Ce comptage des modes est vérifié dans `VIVIER_MIX` : celui-ci
porte le vivier brut, qui peut différer de `considered` après filtrage ; ils
coïncident sur les 17 clichés de décembre du bras testé.
Les neuf clichés à reliquat nul ne prouvent pas une caisse
entièrement investie : par exemple graine 999 le 19 décembre, budget
**115 291 £** et somme du pool **1 186 424 £** ; les 24 projets sont seulement
finançables individuellement au devis.

## Consommateur de caisse proposé

**La voie exposée est la construction de nouvelles lignes fret RAIL
constructibles, avec alimentation du vivier lorsqu'il s'épuise.** Ce diagnostic
ne prouve pas qu'une variante particulière de cette alimentation sera rentable.
Il n'autorise aucune relance des variantes déjà échouées.

Le fait nouveau à isoler est la **transition pool disponible → pool épuisé
dans le même mois**, pas le mode 2 de V217 :

- Graine **7** : V217 refuse de recharger le 2 décembre (`reason=pool`,
  capital disponible **457 159 £**, ligne 24506). Deux `RAIL_BUILD` consomment
  réellement **87 139 £** le 9 puis **74 359 £** le 19 (lignes 24645, 24765).
  Vivier vide le 20, capital disponible **316 721 £**.
- Graine **100** : même skip le 1er (`121 324 £`, ligne 22041), puis
  derniers projets route rejetés `TRACEX` et vivier vide le 26 avec
  **155 971 £** (ligne 22383).
- Graine **2026** : recharge `LVST` de **3 candidats** le 7 (ligne 23969),
  dont un `SITEAB` le 8 ; un rail construit le 11 pour **48 473 £**
  (ligne 24028), puis vivier vide le 14 avec **188 238 £**. La resélection
  du 22 rend deux AIR disponibles et un `AIR_BUILD` suit immédiatement
  (ligne 24329), puis vivier vide le 23 avec **250 720 £**.

`orchestrator.nut:817-818` pose le verrou mensuel avant le test du pool
et `:859` recharge un seul cargo. Un essai futur isolé pourrait **réarmer la
rotation fret existante après épuisement avéré**, avec borne de travail par
mois, sans toucher aux scores ni aux modes disponibles. Le nouveau fait est
daté et mesuré ci-dessus ; ce n'est ni V217 mode 2, ni une nouvelle ouverture
globale V269/V305b, ni la conservation des curseurs AIR. Il faudrait d'abord
prouver des candidats effectivement constructibles et du capital réellement
absorbé ; aucun nombre de lignes ou gain n'est déduit de la seule taille du pool.

Pour un consommateur plus substantiel, le chantier **RAIL-LONG-FENETRES**
déjà ouvert dans `taches.md` (RLW-03…09, traces prévalidées puis arbitrage
calibré) vise précisément cette alimentation. Le présent audit ne valide
pas ses prérequis et n'en réalise aucune étape. V161 est déjà actif ; changer
encore la valeur des renforts ne crée pas de candidat dans un vivier vide.
Aucune interdiction de mode par date n'est proposée.

## Contrats et limites de validation

[Neuf nouveaux tests](../sweeps/test_analyse_air_load_reselect.py) passent :
partition exacte des £-clichés, pool individuellement finançable, sentinelles
et données manquantes, refus d'achat distinct du refus de garde, censure des
passes, séparation des blocs le même jour, propriétaire, intégrité des
sources figées, comptage fleet par `VIVIER_MIX.total` et contrat du `continue` existant.

Suite demandée depuis `sweeps`, stdout/stderr conservés avant le `tail -3` :

| État | Tests | Échecs | Erreurs | Ignorés | Échecs attendus |
|---|---:|---:|---:|---:|---:|
| Avant modification | 2 385 | **13** | **38** | 7 | 2 |
| Après | 2 394 | **13** | **38** | 7 | 2 |

**Les intitulés des 13 échecs et 38 erreurs sont strictement identiques.**
[Inventaire et hashes des deux sorties](../evidence/review/air_load_reselect_20261024/validation.json).
Échecs préexistants : garde AIR (hash `task_air.nut` ancien), PO01C (7
assertions), capture voie rail (2), compatibilité R9, station precheck,
lanceur V166. Erreurs : 7 imports `sweeps` depuis ce cwd, `openttdlab`
absent, 3 imports `pytest` absents, 12 erreurs V166 (AAAHogEx non présent
dans ce worktree), 15 erreurs V184 (chemins relatifs `sweeps/ai/OpexAI/...`
depuis le cwd demandé). Aucun échec masqué ou contrat ancien réécrit.

Commandes avec `PYTHONDONTWRITEBYTECODE=1` et `TMPDIR` sous
`results/air_load_reselect_20261024/tmp` ; logs complets locaux
`tests_before.log` et `tests_final.log` dans le même dossier parent.
**Aucun hash de contrat rebasé**, aucun nouvel `Valuate`, aucun changement
des inventaires de réglages. `po01c_generators.nut` n'a pas été régénéré.
Le chemin OFF et Save/Load restent les fichiers livrés en entrée, sans
nouveau marqueur transitoire ni état comportemental. Aucun round-trip moteur,
compilation Squirrel, Docker ou partie exécuté. `git diff --check` passe.

Les 5×3 avec sonde et le seuil 50 ne démontrent aucun effet au seuil 30 sur
20×10. L'attribution exhaustive de chaque livre réelle et des passes muettes
exigerait une instrumentation supplémentaire ; elle n'est pas inventée ici.
