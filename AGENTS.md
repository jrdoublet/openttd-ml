# AGENTS.md — OpenTTD-ML / OpexAI

Guide applicable à tout le dépôt. Consignes documentaires réconciliées le **2026-09-30** ;
validation mise à jour le **2026-10-03** selon V102/V110 et le harnais livré.
Ces mises à jour ne constituent pas une nouvelle qualification économique.
Ce fichier fixe les invariants et méthodes ; [docs/taches.md](docs/taches.md) est la
**seule liste autoritaire du travail restant**. Les anciennes revues ne sont pas une file active.

## 1. Commencer par le contexte courant

1. Lire les instructions applicables et inspecter `git status --short` et `git diff` avant
   modification. Préserver les changements et fichiers non suivis de l'utilisateur.
2. Lire l'« État courant » de `docs/taches.md`, puis chercher les symboles et réglages concernés
   dans le code. Avant de rouvrir une piste, consulter aussi
   [le journal du 13 septembre](docs/journaux/journal_2026-09-13.md) et
   [l'archive des tâches](docs/archives/taches_archive_2026-09-09.md), ainsi que les journaux quotidiens
   récents liés depuis `docs/taches.md`. Les comptes rendus retirés de la liste le 22 septembre
   sont conservés dans `docs/journaux/journal_2026-09-22_transfert_historique.md`.
3. Distinguer décision utilisateur, implémentation, hypothèse et mesure. Une ancienne mention
   « à faire » ou un commentaire ne prouve pas l'état actuel.
4. Définir une intervention isolée et sa validation avant de modifier le comportement.
   Ne pas réactiver implicitement une politique abandonnée ou désarmée.

**Objectif :** améliorer les résultats économiques d'OpexAI face à AAAHogEx sur carte partagée.
ROI, profit/opcode et scores internes sont des heuristiques ; leur hausse ne prouve pas un gain
économique. Vérifier l'effet sur OpexAI elle-même, pas seulement la baisse de l'adversaire.

**Repère historique :** au début du 21 septembre, `docs/taches.md` retenait `b68fafb` (C68 adopté,
`air_route_plane_selection=1`, feeders supprimés). La frontière AIR capital→profit, le best
equipment et leur cycle de vie sont abandonnés. C66 est qualifié/clos. Ce repère évite une
réouverture accidentelle ; il n'autorise aucun reset ou changement de branche. Toujours relire
l'état courant plutôt que considérer ce paragraphe comme un backlog permanent. Le défaut courant
du 22 septembre inclut aussi C69 bis/C70/C75 ; les intégrations sont dans les journaux quotidiens.

## 2. Repères et architecture

Les noms `.nut` ci-dessous sont relatifs à `ai/OpexAI/`.

| Besoin | Source à consulter |
|---|---|
| Priorités et décisions | `docs/taches.md` |
| Carte des modules | `docs/architecture_courante.md` ; anciens schémas dans `docs/architecture_opexai.md` |
| Protocole et pièges Squirrel | `docs/methode.md` |
| Entrée et ordre de chargement | `main.nut`, `globals_pre.nut`, `globals_post.nut` |
| Réglages déclarés et chargés | `info.nut`, `settings.nut` |
| Modèles et portefeuille | `catalog.nut`, `economy.nut`, `candidates.nut`, `projects.nut`, `tension.nut` |
| Exécution | `builder_*.nut`, `task_*.nut`, `scheduler.nut`, `scheduler_tasks.nut` |
| Événements et état | `events.nut`, `event_handlers.nut`, `persist.nut`, `lines.nut` |
| Instrumentation | `probes.nut`, `ledgers.nut`, `budget.nut` |
| Banc solo / diagnostic | `sweeps/bench_v2.py` |
| Duel figé / comparaison causale | `sweeps/run_c66_reference.py`, `sweeps/bench_1v1_5y_20seeds.py` |
| Compteurs / santé / gel | `sweeps/physical_counters.py`, `sweeps/game_health.py`, `sweeps/campaign_freeze.py` |
| Preuves versionnées | `evidence/review/README.md`, `evidence/review/index.json` |

La cible OpexAI est **OpenTTD 15.3 / API NoAI 15 / OpenGFX 7.1** ; OpenTTDLab est fixé à
**0.0.75** dans `requirements.txt`. Les passages Phase 0 du README (13.4, trAIns, calibration)
sont désormais condensés dans [la synthèse Phase 0](docs/archives/phase0_trainline_synthese.md) ;
ils sont historiques et ne définissent pas le runtime d'OpexAI.

### Invariants Squirrel

- Conserver le découpage : `main.nut` assemble ; placer les méthodes dans leur module métier.
  Charger les définitions `function OpexAI::...` après la déclaration de classe. Respecter les
  dépendances de `globals_pre.nut` et `globals_post.nut` avant de déplacer un symbole.
- Pour un réglage, vérifier ensemble `AddSetting`, bornes, défaut, chargement dans `settings.nut`
  et sites d'utilisation. Ne pas changer silencieusement un défaut pour un essai.
- Pour un état qui influence les décisions, vérifier `Save`, `Load` et la réconciliation après
  chargement. Distinguer état comportemental, cache reconstructible et télémétrie transitoire.
- Préserver les contrats des tâches reprenables, l'invalidation des caches et le nettoyage après
  échec partiel de construction. Un déplacement de code peut changer le coût en opcodes.
- Ne pas supposer qu'une fonction imbriquée capture les variables `local` englobantes : consulter
  le piège de portée documenté dans `docs/methode.md` et les usages existants.
- Résoudre cargos et types de rail via l'API (`AICargo`, `AIRailTypeList`), sans IDs codés en dur.
- `AISign.BuildSign` est limité à **31 caractères** ; préserver les formats lus par les décodeurs.
  Réutiliser les logs/sondes existants et vérifier leur activation effective.
- Les opcodes sont une ressource de jeu à allouer. Ne pas ajouter de `Sleep()` « par politesse »
  envers un joueur humain absent du banc. Vérifier le rôle des suspensions fonctionnelles
  existantes avant de les modifier ; ne pas prétendre qu'aucune suspension n'existe.

## 3. Outils, édition et environnement

- Si `rtk` est installé, suivre sa configuration locale et utiliser `rtk proxy <commande>`
  lorsque son filtrage n'est pas adapté. Sinon, utiliser les outils natifs disponibles ; aucun
  chemin personnel tel que `C:/Users/jr/.codex/RTK.md` n'est un prérequis du dépôt.
  Les exemples ci-dessous sont sans wrapper ; adapter l'exécutable Python à l'environnement choisi.
  Si Git ou le runtime manque, signaler les contrôles non exécutés, sans installation implicite.
- Utiliser les outils d'édition disponibles (en priorité `apply_patch`), sans
  dépendre d'anciens outils `run_command`, `write_to_file` ou `ArtifactMetadata`.
- Conserver l'UTF-8. Sous Windows, `python -X utf8` évite les erreurs de console sur les accents ;
  préciser `-Encoding utf8` pour lire avec PowerShell. Ne pas mélanger quoting Bash et PowerShell.
- Garder les modifications ciblées. Aucun reset, nettoyage, commit ou publication implicite.
  Ne pas écraser une campagne ni modifier un bundle figé pour le faire correspondre au code courant.
- `sweeps/archive/` contient des références historiques : vérifier leurs dépendances et protocole
  avant toute réutilisation, plutôt que les traiter comme des harnais courants.

### Protection obligatoire du VPS et cache Docker

Toute exécution Docker de tests/parties utilise **`--cpus=3 --memory=2g --memory-swap=2g`** et
**`-v openttd-lab-home:/home/lab`**, en plus du montage du dépôt et de `-w /work`.
Le VPS a 4 cœurs et environ 3,7 Go de RAM ; ces limites protègent l'hôte et interdisent le swap.
Plusieurs conteneurs plafonnés séparément peuvent saturer ensemble le VPS : ne pas y lancer
plusieurs campagnes simultanées. Garder `--max-workers 3` au maximum sur ce profil.
Un ancien résultat local à 6 CPU n'autorise pas à dépasser ces limites.

Avant un lancement, vérifier le contexte Docker actif, l'image `openttd-lab`, le cache et le
chemin réellement monté. Un daemon distant ne monte pas automatiquement le dossier Windows local.
Si le runtime manque, rapporter la validation non exécutée ; ne pas substituer un autre protocole.
Ne pas appeler `openttd` directement : utiliser les harnais Python existants.

Smoke **1 graine × 1 an**, depuis la racine, syntaxe PowerShell :

```powershell
docker run --rm --cpus=3 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab -v "${PWD}:/work" -w /work openttd-lab python3 sweeps/bench_v2.py --arms "OpexAI" --seeds 42 --years 1 --max-workers 3 --out results/smoke_identifiant_unique.json
```

Sous Bash, remplacer uniquement le montage du dépôt par `-v "$PWD":/work`. Choisir un nom de
sortie neuf ; pour une variante, remplacer le bras par son réglage réel déclaré.

Pour un duel reproductible, préférer le lanceur hôte qui enregistre Git, l'image exacte et les
limites Docker, puis exécute les copies figées :

```powershell
python -X utf8 sweeps/run_c66_reference.py --campaign diag_identifiant_unique --years 6 --seeds 42 100 999 1234 5678 --max-workers 3 --min-useful-primary-delta 50000
```

Cette commande mesure une référence ; le lanceur exige un seuil même pour ce diagnostic.
Pour un A/B, ajouter les bras et critères pré-enregistrés du §4.1. Consulter `--help`.
Le nom `bench_1v1_5y_20seeds.py` n'impose ni durée ni nombre de graines : les passer
selon la porte choisie. Le défaut CLI reste `signs20` ; V102 exige une règle explicite.

## 4. Validation proportionnée, puis adoption

| Changement | Validation requise |
|---|---|
| Documentation uniquement | Relire le diff, vérifier chemins/symboles/options cités, `git diff --check` si Git est disponible ; aucune partie nécessaire |
| Harnais ou décodeur | Tests ciblés et fixtures ; smoke réel si l'intégration moteur ou le schéma collecté change |
| Squirrel | Tests de contrat pertinents et smoke 1×1 pour compilation/exécution |
| Comportement IA | Exposition du mécanisme, puis protocole V102 : porte A **40 graines × 3 ans**, porte B **20 graines × 10 ans** pour les survivants |
| Adoption par défaut | Les **deux portes V102** complètes et saines avant changement du défaut ; règle opcodes distincte ci-dessous |
| Persistance | En plus, validation adaptée de Save/Load, notamment `sweeps/save_load_roundtrip.py` |

**Optimisations d'opcodes (décision utilisateur du 2026-09-24).** Un changement dont le but est
d'économiser des opcodes est **adopté par défaut s'il est neutre** : gain d'opcodes mesuré sur le
poste visé (sonde existante, même protocole des deux côtés), puis 20×10 apparié complet et sain
qui ne montre **pas de perte** — IC95 Student du delta `profit_year` non entièrement négatif, pas de
défaite significative au test des signes (p ≥ 0,05 ou majorité de victoires) et garde de valeur
−5 % tenue. Cette règle spécifique est conservée ; la porte A de gain V102 et les
anciens seuils de gain (+50 k£/an, 15/20) ne s'appliquent pas : les opcodes
libérés sont une ressource réservée à d'autres chantiers (C67…). Un changement qui modifie aussi
les décisions reste soumis à cette même absence de perte ; « même tracé / mêmes décisions »
dispense seulement de chercher la cause d'une dérive de trajectoire.

Les tests Python ne compilent pas Squirrel. Un smoke ne valide pas la rentabilité ; le banc CI
20×3 ne remplace pas les deux portes V102. Le **5×6 n'est plus une porte obligatoire**
de qualification comportementale ; un diagnostic ciblé reste possible pour comprendre
un mécanisme, sans constituer une preuve d'adoption. Ne pas lancer un banc coûteux pour une simple édition
documentaire. Les scripts exposant `--selftest` peuvent être testés sur l'hôte.

Exemples de tests ciblés sans partie (sélectionner ceux du changement) :

```powershell
python -X utf8 -m unittest discover -s sweeps -p test_physical_counters.py
python -X utf8 -m unittest discover -s sweeps -p test_game_health.py
python -X utf8 -m unittest discover -s sweeps -p test_campaign_freeze.py
python -X utf8 sweeps/bench_1v1_5y_20seeds.py --selftest
```

Pour C66.4, chaque graine donne **deux parties distinctes** : référence contre AAAHogEx, puis
variante contre la même AAAHogEx figée, avec mêmes carte/configuration, horizon et places.
Deux bras solo de `bench_v2.py` ne remplacent pas ce duel.

**Protocole comportemental V102 (décision utilisateur du 03/10, application V110).**
La métrique primaire est le delta `profit_year` **Opex variante − Opex référence**
à l'année terminale, pas le profit cumulé ni le ratio Opex/AAAHogEx.

| Porte | Protocole et critères de passage |
|---|---|
| A — gain (`gain_short`) | **40 graines × 3 ans**, une répétition, 80 parties ; Wilcoxon exact bilatéral **p < 0,05**, borne basse de l'**IC95 bootstrap de la moyenne > 0**, delta moyen **≥ 4 %** du profit moyen de référence de l'année terminale ; garde de valeur **−5 %** |
| B — non-érosion (`non_erosion`) | Après A, **20 graines × 10 ans**, une répétition, 40 parties ; borne haute de l'**IC95 bootstrap ≥ 0**, garde de valeur **−5 %** ; aucun gain positif minimal ni quota de victoires exigé |

La garde utilise le **ratio des moyennes de `company_value`**, avec tous les
dénominateurs de référence strictement positifs. Sous B, une borne haute < 0
signale une perte ; un intervalle traversant zéro passe ce critère. Ce passage
ne prouve ni équivalence ni gain à dix ans. Un intervalle absent reste non validé.
Le bootstrap livré utilise 20 000 rééchantillonnages et la graine 0 ; conserver
ses paramètres avec les résultats. Le test des signes et V/D/E restent descriptifs
pour V102, sans exigence de 15/20. `signs20` et `mean40` restent disponibles pour
reproduire les protocoles historiques, pas comme consigne courante implicite.

Pré-enregistrer règle, seuil, graines, horizon, exposition et budget **avant** mesure.
Un autre horizon `gain_short` (par exemple six ans) doit être décidé avant lancement ;
aucune porte six ans automatique ni sélection du meilleur horizon après résultats.
Conserver les verdicts historiques : une réanalyse est identifiée séparément et ne
remplace pas la mesure initiale. V110 documente une nouvelle porte A et une porte B
réanalysée ; cela n'autorise pas à requalifier automatiquement d'anciens rejets.
Un sous-ensemble favorable ou un réglage hors défaut commun aux deux bras ne prouve
pas un gain au défaut. Ne pas contourner les audits de réglages pour obtenir un verdict.

### 4.1 Pilotage automatique des bancs par les agents LLM

**Décision utilisateur du 30/09, protocole actualisé le 03/10.** Pour une demande
de modification ou de qualification d'un paramètre par défaut, préparer, déclencher
et suivre les bancs nécessaires sans nouvelle demande de lancement lorsque les
prérequis sont réunis. Aucune campagne pour une simple revue ou édition documentaire.
Les interdictions de `docs/taches.md` (réglage protégé, pas de 20×10, piste abandonnée)
restent applicables.

**Avant tout lancement :**

1. Lire les décisions courantes ; définir l'intervention isolée, l'ancien défaut,
   la valeur candidate et une preuve d'exposition réelle du mécanisme. Conserver
   l'ancien défaut dans `info.nut`/`settings.nut` pendant la qualification. Les bras
   `OpexAI[reglage=ancienne_valeur]` et `OpexAI[reglage=valeur_candidate]` partagent
   le **même arbre de code**, avec les autres réglages aux défauts courants.
   Vérifier déclaration, bornes, chargement, usages, persistance et différences
   effectives. Sans chemin témoin, ou avec d'autres changements non qualifiés
   dans les deux bras, ne pas attribuer au candidat la qualification du cumul.
2. Pré-enregistrer dans le journal du chantier : dépôt, branche, SHA et état local,
   bras, catégorie comportement/opcodes, exposition, graines, horizons, règles,
   seuils et budget. Pour le comportement : `profit_year`, porte A `gain_short`
   **40×3**, seuil relatif **4 %**, puis porte B `non_erosion` **20×10**, garde
   de valeur **5 %** aux deux portes. Toute variante de protocole se décide avant
   les résultats. Les snapshots répétés d'une partie ne sont pas des graines.
3. Vérifier runtime, image exacte, cache, montage et ressources du §3, campagnes
   existantes et budget : aucun doublon du même code/protocole, une seule campagne
   à la fois sur le VPS, aucune relance jusqu'à obtenir un résultat favorable.
   Figer le code réellement exécuté avec le harnais courant avant chaque campagne.
4. Si le moteur local manque, vérifier l'accès et les capacités réelles de GitHub
   Actions : dépôt, branche publiée contenant le candidat et les harnais, SHA,
   workflow, authentification, quota. **L'autorisation de banc n'autorise aucun
   commit, push, merge ou publication implicite.** Si le candidat n'est pas publié,
   demander la publication ou l'autorisation correspondante. Si runtime, accès,
   budget ou workflow compatible manque : **bloqué/non validé**, obstacle précis,
   paramètres prêts et défaut inchangé.

**Parcours courant V102 : contrats → smoke → porte A → porte B.**

Après les tests ciblés, exécuter un smoke causal **1 graine × 1 an** (deux duels).
Il valide compilation/exécution et santé, sans conclusion économique ; la première
année peut n'avoir que trois trimestres clos. Après smoke sain et exposition
établie, lancer A ; après A complet, sain et `pass`, lancer B. Un diagnostic
ciblé peut aider à établir l'exposition ; **ne plus imposer le filtre 5×6 / +50 k£**
du protocole précédent. Toute porte échouée ou preuve absente arrête la séquence.

Utiliser `sweeps/run_c66_reference.py` avec les options communes suivantes,
remplacées par les valeurs du plan : `--campaign <identifiant_neuf>`,
`--reference "OpexAI[reglage=ancien]"`, `--variant "OpexAI[reglage=candidat]"`,
`--variant-policy-id <chantier>`, `--primary-metric profit_year`,
`--value-guard-max-loss-pct 5`, `--repeats 1`, `--cpus 3 --memory 2g --max-workers 3`.
Le lanceur ajoute le plafond swap égal à la RAM et le volume de cache.

| Étape | Options supplémentaires explicites |
|---|---|
| Smoke | `--decision-rule gain_short --min-useful-primary-delta-pct 4 --required-seeds 40 --required-years 3 --years 1 --seeds 42` ; hors échantillon d'adoption, juger la santé et la couverture attendue à un an |
| A | `--decision-rule gain_short --min-useful-primary-delta-pct 4 --required-seeds 40 --required-years 3 --years 3` ; omettre `--seeds` pour les 40 graines canoniques |
| B | `--decision-rule non_erosion --min-useful-primary-delta-pct 4 --years 10` ; omettre `--seeds` pour les 20 graines canoniques |

Le lanceur exige **exactement un** seuil absolu `--min-useful-primary-delta`
**ou** relatif `--min-useful-primary-delta-pct` sous V102. Sous B, ce seuil est
enregistré mais **n'est pas une porte**. `--required-seeds`/`--required-years`
ne concernent que `gain_short` ; ils ne remplacent pas `--years`, qui fixe la
durée réellement simulée. Le défaut CLI `signs20` est conservé pour compatibilité :
toujours nommer la règle. Télémétrie OFF sauf besoin pré-enregistré et identique
dans les deux bras ; distinguer exposition instrumentée et résultat sans sonde.

**Limite GitHub vérifiée le 03/10 :** `bench.yml` / `github_bench.py` imposent
encore `signs20` et au plus 20 graines ; `qualify.yml` /
`github_qualification.py` / `qualification.py` enchaînent encore
smoke→5×6→20×10 avec +50 k£ et 15/20. **Ils n'implémentent pas V102.**
Ne pas présenter un job vert ou un plan JSON de schéma 1 comme qualification A/B
V102, ni substituer l'ancien protocole quand V102 est demandé. Le lanceur hôte
ci-dessus est le parcours disponible ; la migration des workflows est suivie
dans `docs/taches.md`. Contrats et limites historiques :
[guide GitHub](docs/bancs_github.md), [plans](qualifications/README.md).

**Optimisations d'opcodes :** appliquer la règle dédiée du §4, déclarée avant
mesure : gain d'opcodes mesuré sur le poste visé à entrées/protocoles comparables,
puis absence de perte selon les critères conservés. Aucun gain économique positif
ni porte A imposés. Un `fail_primary` sous `signs20` ne tranche pas la neutralité ;
`min_delta=0` ne transforme pas cette règle en test de neutralité. Garder le verdict
brut et documenter séparément chaque critère. Ne pas remplacer cette règle par le
seul `pass non_erosion`, ni reclasser un essai perdant en « opcodes » après coup.
Le validateur GitHub historique ajoute une comparaison H5 par échantillon seulement
pour les composants couverts ; son absence de preuve arrête sa séquence.

**Suivi et décision :**

- Suivre la campagne exacte et, sur GitHub, son ID, URL, tentative et SHA ; récupérer
  les artefacts dans un dossier neuf, contrôler requête, manifeste/bundle et JSON
  final. Ne pas lire arbitrairement « le dernier run ». Si la session s'arrête,
  consigner l'identifiant et l'étape suivante, jamais un verdict à venir.
- Pour chaque porte V102 : santé et horizon complets, **40/40 paires pour A,
  20/20 pour B**, `comparison_complete=true`, `adoption_sample_complete=true`,
  `metric_coverage_complete=true`, couverture annuelle de quatre trimestres valides
  et `policy_comparison.verdict=pass` sous la **règle attendue**. Contrôler les
  critères réels du §4, l'exposition et la comparabilité des deux portes.
  Le `pass` d'une seule porte n'autorise pas l'adoption.
- `fail_primary`, `fail_value_guard` ou `fail_primary_and_value_guard` sous le
  protocole pré-enregistré : ne pas adopter. Erreur technique, timeout, collecte
  incomplète, `incomplete`, `diagnostic_only` hors smoke ou preuve ambiguë :
  **non validé**, pas rejet économique. Diagnostiquer avant relance ; une correction
  du code ou des bras impose une nouvelle campagne, sans réutiliser l'ancien verdict.
- Le ratio Opex/AAAHogEx, un duel trois ans non apparié, un solo ou la seule baisse
  d'AAAHogEx ne sont pas des critères d'adoption. Un A/B 40×3 satisfaisant A reste
  une preuve de gain à cet horizon, soumise à B pour l'adoption.
- Si les deux portes sont qualifiées et que la demande porte sur l'adoption,
  appliquer uniquement le défaut testé aux quatre difficultés, vérifier chargement
  et persistance, exécuter tests ciblés et smoke du défaut livré. Si la demande
  porte seulement sur l'évaluation, rapporter « qualifié » sans changer le défaut.
  Aucun autre changement comportemental ne bénéficie du verdict ; aucun push/merge
  automatique.
- Journaliser décision, SHA/arbre figé, bras, paramètres, campagne ou URL/run/attempt,
  chemins d'artefacts, couverture, santé, deltas par graine, moyenne/médiane,
  Wilcoxon p, IC95 **bootstrap**, V/D/E, garde de valeur et verdict brut de chaque
  porte. Pour les opcodes, ajouter les mesures et critères spécifiques. Mettre à
  jour `docs/taches.md` et conserver les preuves selon §6. Une dérogation explicite
  reste tracée, sans fabriquer de `pass` statistique.

## 5. Mesure fiable : réutiliser le harnais

Tout nouveau diagnostic doit partir d'un script courant et réutiliser ses extracteurs,
configuration, bibliothèques, nettoyage et contrôles. Ne pas improviser un appel incomplet à
`openttdlab.run_experiments` ni dupliquer son instrumentation par monkey-patch non contrôlé.

### Contrat du processeur

`result_processor=keep` attend un itérable de lignes. Pour une ligne, retourner un **tuple** :

```python
def keep(row):
    record = ...  # extraction fondée sur les helpers actuels du harnais
    return (record,)  # la virgule est obligatoire
```

Retourner directement le dictionnaire ferait itérer ses clés et corromprait les résultats.
Ce fragment illustre uniquement le contrat ; ce n'est pas un lanceur autonome.

### Économie et compteurs OpenTTD 15.3

- Utiliser `PLYR[owner]` (clé entière ou chaîne) et `old_economy`, index 0 = trimestre clos le
  plus récent. `cur_economy` ne remplace pas la valeur du dernier trimestre clos.
- Réutiliser `quarter_profit` et `year_profit` de `bench_v2.py` : les dépenses peuvent être
  négatives. `year_profit` somme **jusqu'à quatre** trimestres disponibles ; une année initiale
  incomplète doit rester identifiable. `money` seul n'est pas une mesure de succès.
- Préserver `None`/inconnu : ne pas convertir une métrique absente en zéro. Distinguer absence,
  échec de décodage, zéro réellement observé et mode non qualifié.
- **Ne pas utiliser `len(VEHS)` comme nombre de véhicules.** Wagons, remorques, ombres et rotors
  produisent des enregistrements supplémentaires. Réutiliser `decode_vehicles(..., target_owner=...)`
  de `physical_counters.py` et ses indicateurs de validité/qualification.
- Utiliser `decode_stations(..., target_owner=...)` pour les gares ; distinguer gares physiques
  et installations d'une gare multimodale. Ne pas mélanger compagnies ni additionner les
  capacités de cargos différents sous un même intitulé.
- Réutiliser `station_ratings(chunks, owner=...)` de `bench_v2.py` : structures imbriquées,
  propriétaire et activité du cargo comptent. Filtrer seulement `rating > 0` biaise la mesure.
- Lire les métadonnées du harnais choisi (`bench_run`, `bench_arm`, graine, politique, répétition,
  compagnie, date) ; ne pas supposer que tous les scripts ont le même schéma.
- Dédupliquer les trimestres par leur date réelle, jamais par `len(old_economy)` : la fenêtre
  historique plafonne. Les sauvegardes mensuelles ne sont pas des observations indépendantes.

### Santé et reproductibilité

Réutiliser `game_health.py` pour distinguer moteur, erreurs NoAI attribuées, données manquantes,
doublons, horizon tronqué, activité suspecte et faillite. Une faillite est une issue économique
à conserver ; une erreur de collecte rend le protocole incomplet. Ne pas attribuer un log fatal
partagé à OpexAI sans identifiant. Un processus terminé avec code 0 ne suffit pas à valider le banc.

Pour une preuve comparative, figer les entrées avec `campaign_freeze.py` **avant** les parties :
code réellement exécuté (y compris modifications locales), adversaire, bibliothèques, configuration,
défauts/réglages explicites, runtime, graines et places. Un SHA Git seul ne suffit pas.
Conserver JSON, JSONL, manifeste, bundle et journaux uniques ; rapporter parties attendues/obtenues,
statuts de santé et horizon atteint. Une campagne interrompue n'est pas un résultat d'adoption.

## 6. Provenance des preuves

**Décision utilisateur du 2026-09-11 : les résultats antérieurs au 2026-09-09 ne font plus foi.**
Ne jamais les citer comme preuve de performance actuelle, même s'ils existent encore dans
`results/`, une archive, un commentaire ou un document. Les archives expliquent les décisions ;
si un chiffre ancien compte, le remesurer sur une référence identifiée.

La date seule ne qualifie pas non plus un résultat récent : vérifier bundle, protocole, métriques,
santé et pertinence pour le code étudié. Éviter les chiffres sans source et les conclusions causales
fondées sur deux campagnes non appariées.

`results/` est principalement ignoré par Git. Pour une preuve destinée à une revue versionnée,
consulter `evidence/review/README.md` et `sweeps/package_review_evidence.py` ; préserver hashes et
index. Ne pas forcer l'ajout de caches, sauvegardes ou logs volumineux. Citer le fichier de preuve,
sa campagne et ses limites ; distinguer résultat testé et hypothèse.

## 7. Bibliothèques tierces vendorisées

Vérifier les **`import` et `require` transitifs**, pas uniquement `main.nut` : l'ancienne
adaptation MinchinWeb dans `lib_water.nut` (avec `queue.fibonacci_heap` v3) a été retirée le
21 septembre (`7c194d2`), après désactivation des chemins Lakes. Le chemin eau courant utilise
`builder_water.nut::OpexWaterFindConnection`, un BFS borné. C67.3 à C67.6 sont livrés
(`terrain_map.nut`, `water_graph.nut`, `task_terrain.nut`), mais sans consommateur métier
exposé aux décisions économiques ; ne pas confondre implémentation, activation et adoption.
`main.nut` importe `pathfinder.rail` v1. La présence de
SuperLib/MinchinWeb/Queue sur disque ne prouve pas un import intégral ni l'absence de réutilisation.

- La décision de commencer par une bibliothèque pour l'eau avait donné cette adaptation.
  Lire le builder courant et le journal du 21 septembre avant toute nouvelle proposition.
  C67 porte désormais sur la carte par blocs et sa connectivité ; ne pas restaurer Lakes
  ni planifier à nouveau son retrait.
- Avant copie/import, vérifier dépendances, versions NoAI et licences des fichiers utilisés.
  Préserver avis de copyright et obligations applicables ; ne pas résumer GPL/LGPL à la seule
  conservation d'un en-tête. Lire les `license.txt` et en-têtes locaux : SuperLib GPLv2 ;
  MinchinWeb permissif, RoadPathFinder LGPLv2.1.
- AAAHogEx et AdmiralAI restent des références adverses locales non versionnées conformément à
  `.gitignore`. Ne pas copier leur code dans OpexAI au prétexte qu'il est disponible sur disque.
- **Rail : rechercher C41 dans `docs/taches.md` et son archive avant de toucher au temps de trajet.**
  `OpexRailEffectiveSpeed` modélise vitesse de croisière et accélération avec cache. Une formule
  SuperLib à vitesse maximale ne constitue pas un remplacement acceptable de ce modèle.
- **Air :** le chemin legacy d'`OpexAirTripModel` initialise `airportDelayDays = 3.0`, mais les
  chemins physiques/replay peuvent le remplacer. Lire C115/C121 et leurs gates avant toute
  conclusion sur le modèle effectivement utilisé. La table SuperLib est elle-même estimée :
  mesurer les délais réels par type avant remplacement.
- **Route :** `OpexRoadLineEconomics` applique déjà `ROAD_SPEED_EFFICIENCY_PCT` ; son audit ne
  justifie pas de le remplacer par un modèle plus rudimentaire à vitesse maximale.
- **Note municipale :** le bug enum de `OpexBoostTownRating` est corrigé. Le filtre proactif existe
  désormais (`OpexTownRatingAllowStation`, C60), a été sondé et reste désarmé selon l'état courant.
  Ne pas le présenter comme absent, ni confondre note faible et refus réel de construction.

## 8. Revues externes et fin de tâche

`docs/00_conseils.md` est une synthèse générique, pas une revue du code courant. Avant d'en tirer
une tâche : chercher l'implémentation, lire les décisions/mesures pertinentes, établir une exposition
réelle, puis proposer une intervention mesurable. Les arrêts routiers traversants ont déjà été
écartés ; ne pas les reproposer sans nouvelle justification. Les droits exclusifs municipaux restent
hors de la politique retenue. Une ancienne liste de « gaps » ne prouve pas qu'ils sont encore ouverts.

Avant de terminer : inspecter le diff, lancer les vérifications adaptées, s'assurer que seuls les
fichiers voulus ont changé. Rapporter ce qui a changé, ce qui a été effectivement validé et ce qui
reste non mesuré. Mettre à jour `docs/taches.md`/le journal pertinent lorsqu'une décision ou un
statut de chantier change, sans recopier tout l'historique dans ce fichier.
