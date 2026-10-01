# Audit R3 — conservation du bypass AIR

Date : 2026-09-30. **Lecture et analyse hors ligne uniquement.**

## Verdict

**Continuation observée dans le moteur : oui. Avancement causal dû à R3 : non prouvé.**
Un premier chantier AIR est suivi du rejet de plans caducs puis d'une autre
construction dans la même passe. Le rapprochement avec le bypass est cohérent
avec le correctif actuel, mais partiellement inféré : la sonde bypass ne porte
ni rang ni identifiant de passe. Aucun témoin exécutant l'ancien ordre R3 n'est
disponible dans le corpus analysé. Aucun gain de profit, délai gagné ou nombre
d'aéroports supplémentaires n'est attribué à R3.

Le code R3 n'a pas été recodé. Aucun fichier `ai/`, harnais partagé, dépendance,
réglage VS Code, tâche ou journal commun n'a été édité. C115 reste protégé ;
les expériences cadence restent OFF par défaut. Aucun commit, push, nettoyage,
partie ni conteneur lancé. Les autres bras présents dans les preuves sont des
**expériences antérieures**, pas des activations faites par cet audit.

## 1. Code existant et contrats

Consignes consultées : `AGENTS.md`, `.github/copilot-instructions.md`, `CLAUDE.md`,
`ai/OpexAI/CLAUDE.md`, état courant de `docs/taches.md`, revue R3 et journaux pertinents.
La description initiale R3 de `docs/revue_code_2026-09-30.md:130–166` décrit le
défaut historique ; le tableau R2/R3/R22 en fin de revue décrit sa correction.

- `ai/OpexAI/task_projects.nut:1509–1570` : la garde
  `OpexAirBatchPlanStillLive(project.payload, this._lines)` précède K_pass et
  l'unique affectation `c75BypassConsumed = true`. Elle est indépendante de C121
  et de `builtCount`. Plan caduc : raison `batch_plan_dead`, puis `continue`.
- La barrière conserve `projCap >= K_pass`, financement `projCap <= availCap`,
  quota unique et arrêt `cash`/`k_pass`. Un candidat vivant devenu non finançable
  au-dessus du seuil arrête la passe : **R3 ne promet pas de passer au suivant**.
- `task_air.nut:272–337` : revalidation finale conservée (récupération, ville
  desservie/second slot, capacité hub, doublon O/D), puis contrôles physiques des
  deux sites. Le précontrôle R3 n'est pas un remplacement de ces validations.
- `task_air.nut:516–525` : après succès, publication de `passDiscards`, puis
  `PROJECT_CHOSEN` et `AIR_BUILD`. Les rejets sont donc publiés **en différé**.
- `task_projects.nut:1760–1767` : sans construction, seulement les trois premiers
  rejets peuvent être publiés, avec limitation mensuelle. Les sondes ne couvrent
  pas exhaustivement tous les candidats examinés/rejetés.

Les **six contrats source existants** de `sweeps/test_r3_air_bypass.py` passent.
Ils vérifient ordre, quota, financement, portée C121, raisons/sondes et
revalidation finale. Ils **ne compilent ni n'exécutent Squirrel**.

## 2. Preuve principale sourcée

Source : `results/diag_cadence_exposure_20260930_r1.artifacts/reference_42.log`.
SHA-256 : `522e623c81a3069473b63b97988141696e0ad5b95537267dcd5384cd60391b0c`.
Graine 42, compagnie **0**, `pass=6`, `cycle=5`.

| Lignes du log | Date de jeu / constat |
|---|---|
| 4640, 4646–4648 | 1970-09-21 : tentative rang 0, villes 26–36 ; `AIR_BUILD line=8`, puis `air_outcome outcome=built`. Ticks 4866→4880. |
| 4650–4652 | Bypass éligible non consommé auparavant, puis consommé ; capital **63 063 £**, disponible **96 988 £**, K_pass **11 699 £**, `built_before=1`. Tentative rang 3 au tick 4881, villes 30–34. |
| 4656–4657 | 1970-09-22 : publication de `batch_plan_dead` aux rangs 1 et 2, destinations tuile **40153**, celle de la première construction. |
| 4659–4661 | `AIR_BUILD line=9`, rang 3 confirmé `built`, tick 4894. Construction observée, pas simple admission. |
| 4663–4664 | Arrêt `cash` devant rang 12 ; `built_count=2`. |

Les rangs 1 et 2 se situent entre les rangs construits 0 et 3, sans tentative
d'exécuteur journalisée pour eux. Le code explique leur élimination avant la
consommation du bypass, malgré leur publication après celle-ci. **Leur date de
contrôle et leur état exact de bypass ne sont pas mesurés directement.**
Le motif partagé de destination est compatible avec la caducité provoquée par
la première construction ; le log ne détaille pas quelle sous-garde de liveness
a échoué. Le capital historique des deux candidats caducs n'est pas rapproché
ici : on ne démontre pas qu'ils auraient consommé le bypass dans un témoin.

Manifeste associé : `results/diag_cadence_exposure_20260930_r1.json` :
quatre bras × une graine × un an, quatre `valid=true`, `complete=true`,
`sources_unchanged=true`. Le bras `reference` utilise `decision_log=1` et
`probe_portfolio=1` ; C75 multi-build/bypass actifs, C121 économie/première année
OFF, C115=1. Les quatre empreintes enregistrées (`task_projects.nut`,
`task_air.nut`, `settings.nut`, `info.nut`) correspondent aux sources relues.
Mais **`git_sha=null`, `source_frozen=false`** : pas de bundle exécuté immuable.
La santé du manifeste est conservée, pas recalculée à partir de ces seuls logs.

### Contre-exemple : consommation ≠ réussite

Même répertoire, `watch_daily_42.log:4698–4707`, compagnie 0, passe 5,
1970-10-13 : bypass consommé, tentative rang 1, rejet réel `build_failed`,
`BFAIL`, erreur **771 / ERR_STATION_TOO_MANY_STATIONS_IN_TOWN**. Ensuite
`already_consumed=1` et arrêt `k_pass` devant rang 2, pourtant financièrement
admissible (67 164 £ ≤ 132 310 £). Ce dernier candidat n'est pas prouvé
physiquement constructible. C'est une limite attendue du quota, pas un nouveau
défaut corrigé par ce lot. Pas de remboursement du bypass après échec réel.

## 3. Analyseur et couverture

Livrable : `sweeps/parallel_bypass_audit.py`. Imports passifs réutilisés :
`analyse_v86_cannibalisation.parse_kv_fields/to_int` et
`game_health.SCRIPT_LINE_RE/parse_script_errors`. Aucun import de lanceur ni
monkey-patch OpenTTDLab. L'enveloppe propre aux événements R3 est un adaptateur,
pas une nouvelle implémentation des collecteurs de santé ou des champs k=v.

Entrées CLI : fichiers `.log` explicites ou JSON Save/Load contenant
`phase_a.openttd_output_raw` et `phase_b.openttd_output_raw`, plus `--manifest`
optionnel et `--out` obligatoire. La sortie doit être un **nouveau** fichier
sous `results/parallel_bypass_audit/` ; tout écrasement est refusé.
Les autres schémas sont signalés `no_supported_log_stream`, pas convertis en
journaux vides. Les snapshots/JSONL et les archives gzip ne sont pas couverts
par cette exécution ; il ne s'agit pas d'un recensement exhaustif du dépôt.

Résultat : `results/parallel_bypass_audit/observations_20260930.json`,
**10 artefacts, 16 flux séparés, 66 956 lignes lues**, sans erreur de parsing
signalée. Empreintes SHA-256, tailles, lignes sources, préfixes bruts, dates de
publication, IDs, capital/finance/disponible/K_pass en £, ticks et couvertures
sont conservés. La compagnie vient du préfixe NoAI, jamais d'une supposition 0.
Chaque occurrence de passe, chaque fichier et chaque phase Save/Load est isolé.

Comptages de **traces**, pas de totaux exhaustifs d'événements :

| Log d'exposition (graine 42) | `AIR_BUILD` | Rejets explicites caducs | Bypass AIR consommés | Séquences construction→caduc→construction | Dont bypass suivant rapproché |
|---|---:|---:|---:|---:|---:|
| reference | 8 | 2 | 2 | 1 | 1 |
| hub_prefilter | 9 | 20 | 2 | 2 | 1 |
| watch_daily | 9 | 33 | 4 | 2 | 1 |
| skip_not_due | 8 | 0 trace | 3 | 0 reconstruite | 0 |

`skip_not_due` possède des mentions `r_batch_plan_dead` dans le funnel : zéro
rejet détaillé n'est donc **pas** zéro plan caduc. Le funnel peut lui-même ne
contenir que les rejets restant après vidage au succès : ne pas additionner les
deux canaux comme des observations disjointes garanties.

Autres fichiers analysés : `save_load_c121_exposed_20260930.json`,
`save_load_exp_cadence_20260930_r2.json`, `save_load_r19_inject_20260930.json`,
`save_load_r19_inject_mid_20260930.json`, `save_load_r4_probes_20260930.json`,
`save_load_review_20260930.json` sous `results/`. Dans le Save/Load cadence,
phases A/B : respectivement 22/15 `AIR_BUILD`, 67/30 rejets explicites caducs,
8/7 séquences reconstruites, **aucune avec rapprochement bypass suivant**.
Ce sont d'autres traces de continuation, pas une preuve supplémentaire de R3
avec bypass. Les autres fichiers sont trop partiellement instrumentés pour
reconstruire la séquence. Leurs réglages/provenances ne sont pas assimilés à
ceux du manifeste d'exposition.

### Sémantique des étapes

- **Candidat examiné** : trace d'exécuteur/rejet ou `pass_stop next_rank` à la
  barrière financière (`gate_candidates`). Un `project_candidate` de catalogue
  ne prouve pas un examen dans la boucle de construction.
- **Rejeté** : `PROJECT_DISCARD` / `air_outcome=rejected`, avec raison. Un arrêt
  financier est séparé d'un rejet par le constructeur.
- **Bypass consommé** : événement `C75_BYPASS phase=consumed`. L'attribution au
  candidat suivant exige même compagnie/passe, prochain `air_attempt`, même
  finance et `built_before`. Elle reste étiquetée **inférée**, pas identité directe.
- **Construction tentée** : `air_attempt` prouve l'entrée dans l'exécuteur, pas
  l'appel du constructeur physique. Une réussite `AIR_BUILD` ou un rejet
  `build_failed` prouve ce dernier stade. `siteA_unbuildable` ne le prouve pas.
- **Construction réussie** : tentative/outcome appariés ; les séquences exigent
  en plus `AIR_BUILD` de mêmes tuiles entre ces deux événements. Le nom
  `C78_BUILD` seul ne prouve jamais un succès.

Dates de bypass inconnues : `null`. Compteurs exhaustifs de candidats/bypass
préservés et nombre d'aéroports supplémentaires : `null`. Les hubs réutilisés
interdisent notamment de traduire une ligne AIR en deux nouveaux aéroports.
Pas de concaténation Save/Load, de double comptage des trois marqueurs de succès,
de remplacement de champ absent par zéro ou d'attribution causale automatique.

## 4. Fixtures et validation exécutée

`sweeps/test_parallel_bypass_audit.py` contient trois fixtures nommées,
`STALE_THEN_VALID`, `TOO_EXPENSIVE`, `REAL_FAILURE`, et leurs contre-tests.
Ce sont **des logs synthétiques Python écrits à l'avance**, sans modèle de
construction, sans réimplémentation de R3 et sans simulation de l'API NoAI.

| Cas déterministe | Attendu à diagnostiquer |
|---|---|
| A–B construit ; A–C caduc ; D–E valide | Caduc examiné/rejeté sans tentative observée ; bypass rapproché de D–E ; succès seulement avec ses propres preuves. |
| Candidat devenu trop cher | `finance=160`, `available=140`, K_pass=30 dans la fixture ; arrêt cash, pas de tentative suivante inventée. La hausse du prix elle-même n'est pas mesurée. |
| Échec réel du candidat consommant le bypass | Tentative physique, rejet `build_failed`, pas de succès ; suivant au-dessus de K_pass bloqué même s'il est finançable. |
| Site non constructible dans l'exécuteur | Entrée d'exécuteur distincte d'une tentative physique ; aucun faux succès. |

Validation ciblée exécutée dans le venv Python **3.14.4**, via `unittest`, sans
écriture de bytecode : **21 tests diagnostic + 6 contrats R3 = 27/27 OK**.
Ils couvrent aussi publication différée, absence/viduité, financement manquant,
compagnies distinctes, doublons, répétition de passe, reload, isolation des phases,
préservation de fichiers existants, restriction du répertoire et attribution des
erreurs par le collecteur partagé. Aucun autre test ni partie lancé.
Les diagnostics éditeur des deux fichiers Python n'ont signalé aucune erreur.
Git absent : `git status`/`git diff --check` indisponibles ; les sources R3 sont
contrôlées par empreintes, pas par un faux statut Git propre.

## 5. Prochaine intervention minimale — intégrateur uniquement

L'exposition naturelle existe, mais les **états de bypass au rejet**, le cas
exact A–B/A–C/D–E et le délai causal ne sont pas complètement prouvés. Aucun
raccordement ci-dessous n'a été ajouté aux sources communes.

1. Dans une copie moteur test-only figée, fournir trois projets AIR ordonnés
   et réellement admissibles au départ : A–B, A–C avec nouvel aéroport A,
   puis D–E indépendant. Après succès réel A–B, laisser la revalidation
   existante invalider A–C **naturellement**. Ne pas forcer son résultat booléen.
   Vérifier pour A–C et D–E `K_pass <= finance <= capital disponible`, avec
   les vraies valeurs après A–B. C121 première année OFF, options cadence OFF,
   C115 inchangé, même quota et mêmes règles territoriales.
2. Ajouter seulement dans cette copie une émission immédiate au point de rejet
   R3 (`task_projects`, juste avant `continue`), sous un gate test-only OFF :
   compagnie, session/passe/cycle/tick/date, rang, tuiles O/D, motif, `builtCount`,
   `bypass_before/after`, finance, K_pass et disponible. Émettre aussi l'examen
   avant la garde ; ajouter passe/rang/tuiles au marqueur de consommation existant.
   Garder `air_attempt`, `air_outcome` et `AIR_BUILD`, sans créer un autre compteur
   de succès. Ne pas appeler une seconde fois les tests physiques pour journaliser.
3. Rejouer séparément : (a) caduc ; (b) candidat vivant finançable au catalogue
   puis `finance > available` après A–B ; (c) véritable refus API dans le
   constructeur. Pour (c), utiliser un état de test reproduisant la limite de
   stations par ville observée erreur 771, ou un obstacle posé par le fixture
   moteur entre validation et commande. Capturer le retour réel et `AIError`,
   pas un `outcome=rejected` fabriqué. Vérifier rollback et absence de ligne fantôme.
   Le candidat suivant à `finance >= K_pass` doit rester bloqué après consommation.
4. Si une **preuve d'avancement causal** est demandée, exposer dans le même
   binaire de test un témoin restaurant uniquement l'ordre pré-R3 (revalidation
   finale conservée), instrumentation symétrique, même état initial figé. Comparer
   ID du chantier D–E, tick/date de succès ou censure si jamais construit.
   Pas de témoin constitué par une autre expérience cadence. Aucun batch accru,
   nouveau classement territorial ou changement de défaut n'est nécessaire.

Ces tests moteur seront centralisés après les éditions, dans le plafond global
**12 CPU / 12 workers**, non par agent. Ils ne sont ni lancés ni déclarés réussis
ici. Un succès mécanique n'établira toujours pas un gain économique.