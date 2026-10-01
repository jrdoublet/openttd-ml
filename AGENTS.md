# AGENTS.md — OpenTTD-ML / OpexAI

Guide applicable à tout le dépôt. Consignes documentaires réconciliées le **2026-09-30**
par lecture du code ; cette date ne constitue pas une nouvelle qualification économique.
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
python -X utf8 sweeps/run_c66_reference.py --campaign diag_identifiant_unique --years 6 --seeds 42 100 999 1234 5678 --max-workers 3
```

Cette commande mesure une référence. Pour un A/B, ajouter `--reference`, `--variant`,
`--variant-policy-id`, `--primary-metric`, `--min-useful-primary-delta` et
`--value-guard-max-loss-pct` avec les valeurs décidées avant le banc. Consulter `--help`.
Le nom `bench_1v1_5y_20seeds.py` n'impose pas la durée : passer **`--years 10`** pour l'adoption.

## 4. Validation proportionnée, puis adoption

| Changement | Validation requise |
|---|---|
| Documentation uniquement | Relire le diff, vérifier chemins/symboles/options cités, `git diff --check` si Git est disponible ; aucune partie nécessaire |
| Harnais ou décodeur | Tests ciblés et fixtures ; smoke réel si l'intégration moteur ou le schéma collecté change |
| Squirrel | Tests de contrat pertinents et smoke 1×1 pour compilation/exécution |
| Comportement IA | Puis diagnostic apparié **5 graines × 6 ans** pour exposition, sens de l'effet et grandeurs physiques |
| Adoption par défaut | Banc officiel apparié **20 graines × 10 ans**, complet et sain, avant changement du défaut |
| Persistance | En plus, validation adaptée de Save/Load, notamment `sweeps/save_load_roundtrip.py` |

**Optimisations d'opcodes (décision utilisateur du 2026-09-24).** Un changement dont le but est
d'économiser des opcodes est **adopté par défaut s'il est neutre** : gain d'opcodes mesuré sur le
poste visé (sonde existante, même protocole des deux côtés), puis 20×10 apparié complet et sain
qui ne montre **pas de perte** — IC95 du delta `profit_year` non entièrement négatif, pas de
défaite significative au test des signes (p ≥ 0,05 ou majorité de victoires) et garde de valeur
−5 % tenue. Le seuil d'effet utile positif (+50 k£/an, 15/20) ne s'applique pas : les opcodes
libérés sont une ressource réservée à d'autres chantiers (C67…). Un changement qui modifie aussi
les décisions reste soumis à cette même absence de perte ; « même tracé / mêmes décisions »
dispense seulement de chercher la cause d'une dérive de trajectoire.

Les tests Python ne compilent pas Squirrel. Un smoke ne valide pas la rentabilité ; le banc CI
20×3 ne remplace pas le 20×10 d'adoption. Ne pas lancer un banc coûteux pour une simple édition
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

Fixer métrique primaire, effet minimal utile et garde-fou de valeur **avant** les résultats.
Utiliser le verdict calculé par le harnais et lire sa règle effective : `signs20` par défaut, 20 paires,
au moins 15 victoires, test exact des signes bilatéral p < 0,05, effet moyen minimal et garde-fou
sur la valeur. Publier couverture, deltas par graine, moyenne/médiane des deltas et incertitude.
`mean40` est une option distincte, à décider avant la campagne ; les décisions utilisateur
dérogatoires restent tracées dans `docs/journaux/synthese_decisions_2026-09-30.md` et ne transforment pas un `fail_primary`
en qualification statistique. Un sous-ensemble favorable ou un réglage hors défaut commun aux deux bras ne prouve pas un gain
au défaut. Ne pas contourner les audits de réglages pour obtenir un verdict.

### 4.1 Pilotage automatique des bancs par les agents LLM

**Décision utilisateur du 2026-09-30.** Pour une demande de modification ou de
qualification d'un paramètre par défaut, l'agent doit préparer, déclencher et suivre
les bancs nécessaires **sans attendre une nouvelle demande de lancement**, lorsque
les prérequis ci-dessous sont réunis. Ne pas se limiter à donner une commande ou à
dire « à tester ». Cette consigne ne déclenche aucune campagne pour une simple revue
ou édition documentaire, ne rouvre pas les pistes abandonnées et ne lève pas une
interdiction particulière de `docs/taches.md` (réglage protégé, pas de 20×10, etc.).

**Avant tout lancement :**

1. Lire les décisions courantes ; définir une intervention isolée, l'ancien défaut,
   la valeur candidate et le critère d'exposition du mécanisme. Conserver l'ancien
   défaut dans `info.nut`/`settings.nut` pendant la qualification. Utiliser les bras
   explicites `OpexAI[reglage=ancienne_valeur]` et `OpexAI[reglage=valeur_candidate]` ;
   vérifier déclaration, bornes, chargement et différences effectives. Les autres
   réglages restent aux défauts courants, pas à un socle commun optimisé hors défaut.
  Le workflow compare deux réglages du **même arbre de code**, pas deux commits.
  Sans chemin témoin représentant l'ancien comportement, ou si d'autres changements
  non qualifiés affectent les deux bras, ne pas présenter ce banc comme qualification
  de ces changements : isoler l'intervention ou signaler que le protocole est inadapté.
2. Fixer avant mesure la métrique `profit_year`, l'effet utile **50 000 £/an** et la
   garde de valeur **5 %**, sauf protocole spécifique déjà décidé. Enregistrer le plan
   dans le journal du chantier : dépôt, branche, SHA, bras, profils, seuils, exposition,
   catégorie comportement/opcodes. Aucun changement de seuil après lecture des résultats.
3. Préférer GitHub Actions quand le moteur local manque. Vérifier dépôt distant,
   branche publiée contenant exactement le candidat et les harnais, workflow disponible
   et authentification autorisant le déclenchement/lecture des runs. Utiliser `gh` ou
   un outil/API GitHub authentifié ; ne jamais afficher de jeton. **Cette autorisation
   de banc n'autorise pas un commit, push, merge ou une publication implicite.** Si le
   candidat n'est pas publié, demander sa publication ou l'autorisation correspondante.
4. Vérifier les runs existants et le budget/quota Actions : pas de doublon du même
   SHA/protocole, pas de campagnes parallèles du même chantier, pas de relances jusqu'à
   obtenir un résultat favorable. Pas de dépense au-delà d'un budget utilisateur fixé.
   Si accès, publication, runtime ou quota manquent : statut **bloqué/non validé**,
   obstacle précis et paramètres prêts à lancer ; garder le défaut inchangé.

**Séquence GitHub obligatoire pour une qualification ordinaire :** préférer
`.github/workflows/qualify.yml` (`Qualification de défaut OpenTTD`), avec un plan
pré-enregistré `qualifications/<chantier>.json`. Ce workflow exécute les contrats
choisis et enchaîne les trois portes sans nouvelle session d'agent. Contrat exact,
exposition, budget et limites : [qualifications/README.md](qualifications/README.md).
L'agent reste responsable des interdictions de chantier, de l'isolation, du choix
des sondes/contrats et de l'absence de doublon. Aucun défaut n'est changé par le job.

Le parcours manuel reste disponible avec `.github/workflows/bench.yml`
(`Bancs OpenTTD`), entrées suivantes. Les valeurs des bras sont celles du plan,
jamais des exemples recopiés sans lecture du code.

| Étape | `mode` | `profile` | Autres entrées |
|---|---|---|---|
| Smoke causal, 1 graine × 1 an (2 parties) | `paired` | `smoke` | `reference` ancien défaut, `variant` candidat |
| Diagnostic causal, 5 graines × 6 ans (10 parties) | `paired` | `diagnostic` | mêmes bras et seuils |
| Qualification, 20 graines × 10 ans (40 parties) | `paired` | `adoption` | mêmes bras et seuils |

Pour les trois étapes : `years` et `seeds` vides (profils canoniques),
`min_delta=50000`, `value_guard=5`, `line_telemetry=false` sauf besoin défini avant
mesure et identique dans les deux bras. `signs20`, une répétition, deux workers et
les limites Docker sont fixés par le workflow. Exécuter aussi les tests de contrat
pertinents avant les parties ; le workflow de banc ne teste que son orchestration.

- Après smoke sain et tests réussis, lancer le diagnostic. Après diagnostic complet
  et sain, vérifier l'exposition, le delta **Opex variante − Opex référence** et la
  garde de valeur. Pour l'enchaînement automatique ordinaire, exiger effet moyen
  au moins égal à l'effet utile fixé et garde tenue. C'est un filtre de passage,
  **pas une preuve statistique à cinq graines**. Sinon arrêter : mécanisme non exposé,
  candidat non retenu à ce stade ou résultat indécis, sans lancer le coûteux 20×10.
- Une erreur technique, un timeout ou une collecte incomplète donne **non validé**,
  pas un rejet économique. Diagnostiquer avant toute relance ; une correction du code
  ou des bras impose une nouvelle campagne et interdit de réutiliser l'ancien verdict.
- Pour une optimisation d'opcodes déclarée **avant** les mesures, appliquer la règle
  de neutralité du §4 au lieu du seuil de gain économique positif, y compris pour
  interpréter le diagnostic ; mesurer effectivement les opcodes sur le poste visé.
  `bench.yml` n'encode pas cette règle : son `fail_primary` ne la tranche pas et
  `min_delta=0` ne transforme pas `signs20` en test de neutralité. Conserver le verdict
  brut et documenter séparément tous les critères de neutralité ; si la mesure manque,
  aucune adoption automatique. `qualify.yml` ajoute ce contrôle séparé pour les
  composants H5 mesurés et comparables selon le contrat pré-enregistré ; toute
  preuve absente ou comparaison non couverte arrête la séquence `NON_VALIDÉ`.
  Ne pas reclasser un essai perdant en « opcodes » après coup.

**Suivi et décision :**

- Déclencher sur le dépôt/la branche explicitement identifiés, récupérer l'ID et
  l'URL du run exact et vérifier son SHA. Suivre ce run, télécharger ses artefacts dans
  un dossier neuf, contrôler `request.json`, manifeste/bundle et `bench.json`.
  Ne pas lire arbitrairement « le dernier run ». Si la session s'arrête avant la fin,
  consigner le run et l'étape suivante ; ne jamais annoncer un verdict à venir.
- Pour l'adoption ordinaire, exiger absence d'échecs de santé, horizon et métriques
  complets, **20/20 paires**, `comparison_complete=true`, `adoption_sample_complete=true`,
  `metric_coverage_complete=true`, couverture annuelle de quatre trimestres valides,
  et `policy_comparison.verdict=pass`. Contrôler les critères réels : au moins 15
  victoires, p bilatéral <0,05, delta moyen ≥50 000 £/an, ratio des moyennes de valeur
  ≥−5 %. Un job vert ne remplace pas ces contrôles.
- `fail_primary`, `fail_value_guard` ou `fail_primary_and_value_guard` : **ne pas
  adopter**, conserver l'ancien défaut. `incomplete`, `diagnostic_only`, preuve absente,
  ambiguë ou issue d'un autre code : **non validé**, même conséquence sur le défaut.
  Le ratio Opex/AAAHogEx, un duel 3 ans, un solo ou la seule baisse d'AAAHogEx ne sont
  jamais des critères d'adoption d'un réglage.
- Si qualifié et que la demande porte sur l'adoption, appliquer uniquement le défaut
  testé, vérifier les quatre valeurs de difficulté, le chargement et la persistance,
  exécuter tests ciblés et smoke du défaut livré. Aucun autre changement comportemental
  ne bénéficie de ce verdict. Si la demande portait seulement sur l'évaluation,
  rapporter « qualifié » sans changer le défaut. Aucun merge/push automatique.
- Journaliser l'acceptation/refus/blocage avec SHA, bras, paramètres, URL/run/attempt,
  chemins d'artefacts, couverture, santé, deltas moyen/médian, IC95, victoires/p,
  garde de valeur et verdict brut. Mettre à jour le statut dans `docs/taches.md` et
  conserver les preuves selon §6. Une dérogation utilisateur explicite reste une
  dérogation tracée, jamais un `pass` statistique fabriqué.

Parcours de déclenchement et limites : [docs/bancs_github.md](docs/bancs_github.md).
Une consigne LLM n'est pas un service de déclenchement autonome : un agent ou
l'utilisateur doit lancer le run. Ensuite `qualify.yml` enchaîne les portes seul,
contrairement à `bench.yml`. Aucun workflow ne modifie les défauts, commits ou merges.

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
