# AGENTS.md — OpenTTD-ML / OpexAI

Guide applicable à tout le dépôt. État vérifié le **2026-09-21** ; repères documentaires et eau
actualisés le **2026-09-22**.
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
| Carte des modules | `docs/architecture_opexai.md` ; schéma daté à confronter au code |
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
sont historiques et ne définissent pas le runtime d'OpexAI.

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

- Dans cet environnement, lire `C:/Users/jr/.codex/RTK.md` et préfixer les commandes shell par
  `rtk`. Utiliser `rtk proxy <commande>` si le filtrage n'est pas adapté ; préférer `rg` pour
  rechercher. Ne pas transposer ce chemin Windows dans un conteneur Linux.
- Utiliser les outils d'édition disponibles (`apply_patch` ou écriture native du shell), sans
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
rtk proxy docker run --rm --cpus=3 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab -v "${PWD}:/work" -w /work openttd-lab python3 sweeps/bench_v2.py --arms "OpexAI" --seeds 42 --years 1 --max-workers 3 --out results/smoke_identifiant_unique.json
```

Sous Bash, remplacer uniquement le montage du dépôt par `-v "$PWD":/work`. Choisir un nom de
sortie neuf ; pour une variante, remplacer le bras par son réglage réel déclaré.

Pour un duel reproductible, préférer le lanceur hôte qui enregistre Git, l'image exacte et les
limites Docker, puis exécute les copies figées :

```powershell
rtk proxy python -X utf8 sweeps/run_c66_reference.py --campaign diag_identifiant_unique --years 6 --seeds 42 100 999 1234 5678 --max-workers 3
```

Cette commande mesure une référence. Pour un A/B, ajouter `--reference`, `--variant`,
`--variant-policy-id`, `--primary-metric`, `--min-useful-primary-delta` et
`--value-guard-max-loss-pct` avec les valeurs décidées avant le banc. Consulter `--help`.
Le nom `bench_1v1_5y_20seeds.py` n'impose pas la durée : passer **`--years 10`** pour l'adoption.

## 4. Validation proportionnée, puis adoption

| Changement | Validation requise |
|---|---|
| Documentation uniquement | Relire le diff, vérifier chemins/symboles/options cités, `rtk git diff --check` ; aucune partie nécessaire |
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
rtk proxy python -X utf8 -m unittest discover -s sweeps -p test_physical_counters.py
rtk proxy python -X utf8 -m unittest discover -s sweeps -p test_game_health.py
rtk proxy python -X utf8 -m unittest discover -s sweeps -p test_campaign_freeze.py
rtk proxy python -X utf8 sweeps/bench_1v1_5y_20seeds.py --selftest
```

Pour C66.4, chaque graine donne **deux parties distinctes** : référence contre AAAHogEx, puis
variante contre la même AAAHogEx figée, avec mêmes carte/configuration, horizon et places.
Deux bras solo de `bench_v2.py` ne remplacent pas ce duel.

Fixer métrique primaire, effet minimal utile et garde-fou de valeur **avant** les résultats.
Utiliser le verdict calculé par le harnais et lire sa règle effective : actuellement 20 paires,
au moins 15 victoires, test exact des signes bilatéral p < 0,05, effet moyen minimal et garde-fou
sur la valeur. Publier couverture, deltas par graine, moyenne/médiane des deltas et incertitude.
Un sous-ensemble favorable ou un réglage hors défaut commun aux deux bras ne prouve pas un gain
au défaut. Ne pas contourner les audits de réglages pour obtenir un verdict.

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
`builder_water.nut::OpexWaterFindConnection`, un BFS borné ; C67 n'est pas encore implémenté.
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
- **Air :** `OpexAirTripModel` utilise encore `airportDelayDays = 3.0`. La table SuperLib est
  elle-même estimée : mesurer les délais réels par type avant remplacement. Voir C61 AIR.
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
