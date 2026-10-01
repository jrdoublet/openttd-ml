# R1/R3 — préparation de validation moteur, 1er octobre 2026

> **Suite intégrée le 01/10 :** constante corrigée en entier **0/1** (NoAI refuse
> `const … = false`), smoke naturel et Save/Load technique exécutés et sains.
> `r3_dead`/`r3_cash` exposés ; huit fixtures dirigées toujours non validées.
> [Bilan central](three_lots_integration_20261001.md). La suite de ce document
> conserve l'état de livraison initial antérieur à ces exécutions.

## Statut et périmètre

**Instrumentation et lecteur préparés ; aucun scénario moteur exécuté par ce
lot.** Le lanceur d'exposition naturelle est prêt pour l'intégrateur après gel.
Les huit cas dirigés ont leurs préconditions et critères ci-dessous ; leurs
états de jeu déterministes et le checkpoint Save/Load exact restent à raccorder.
Ne pas présenter cette préparation comme huit fixtures moteur exécutables et
validées. Aucun succès, refus physique ni résultat économique n'est fabriqué.

Écritures du lot :

- `ai/OpexAI/projects_selection.nut` : sonde après le retour du fit existant,
  filiation sur **copie** du projet admis, observation du classement final ;
- `ai/OpexAI/task_projects.nut` : inventaire de ligne, retours réels du helper
  d'achat, refus/examen/consommation/arrêt/résultat AIR immédiatement publiés ;
- `sweeps/diag_r1_r3_mechanisms.py`, `sweeps/test_r1_r3_mechanisms.py` ;
- ce rapport et les sorties neuves sous `results/r1_r3_mechanisms/`.

R1 et R3 ne sont pas recodés. C115 protégé ; cadence, C84/C85/C121/C122 non
activés. Aucun changement de batch, quota, priorité flotte, réglage, harnais
commun, dépendance, tâche ni journal commun. Aucun commit/push/nettoyage/
installation. Git/rtk absents de la recherche PATH : pas de diff Git attesté.
Les modifications préexistantes, notamment l'extraction R14 du sélecteur, sont
conservées. Les tests Python **ne compilent pas Squirrel**.

Contexte lu : `AGENTS.md`, `CLAUDE.md`, `ai/OpexAI/CLAUDE.md`, instructions
Copilot, état courant de `taches.md`, [intégration](parallel_integration_20261001.md),
[audit bypass](parallel_bypass_audit.md), [audit flotte](parallel_fleet_audit.md),
contrats `test_r1_partial_fleet.py` et `test_r3_air_bypass.py`.

## Gate et traces

`const R1_R3_TEST_ONLY = false;` est **déclarée dans le fichier autorisé**
`projects_selection.nut`. Les deux compteurs de télémétrie y sont aussi déclarés.
`projects.nut` requiert ce module ; `main.nut` charge `projects.nut` avant
`task_projects.nut`. Aucun symbole global non déclaré ni nouveau membre de
classe nécessitant une édition de `main.nut`.

Le lanceur copie OpexAI dans **son propre dossier de résultat neuf**, puis ne
remplace que cette constante par `true` dans la copie. Aucune modification de
`main.nut`, `globals_pre.nut`, `info.nut` ou `settings.nut`, même dans la copie.
Pas de nouvelle option publique, pas de réemploi ambigu de `selftest` ou R19.
Chaque ligne émise commence par `R1R3 test_only=1`, sous enveloppe NoAI, avec
date API et tick. `decision_log=1` fournit les motifs de refus du constructeur
via les collecteurs déjà présents ; debug script=4 est nécessaire.

### R1

1. `fit` : `id`, ligne, O/D, quantité originale, quantité admise ou `unknown`,
   admission, base/have, liquidation, budget transmis **après réserve**, prix du
   projet, réserve observée, tampon **unique de 1 000 £**, caisse.
2. `rank` : même ID, rang final du sélecteur, score calculé, financement/budget.
   Rang −1 = absent de la liste finale, jamais un rang favorable. Le rang de
   l'exécuteur est aussi publié : une promotion ultérieure doit rester visible.
3. `execute` / `result` : passe, cycle, rang, motif, quantités `added` et
   `replaced` séparées, cache `vehCount`, IDs et nombre de véhicules principaux
   valides **attachés à cette ligne**, via `AIVehicle`.
4. `api_result` : retour réel d'`OpexAirAddPlane`, après l'unique appel existant,
   indice unitaire, raison, `added`. Ce n'est pas un deuxième achat ni un second
   appel physique pour le log. Les raisons `REPLACE` ne sont pas des renforts.

Le prix exposé est `entry.planePrice`. Le helper relit le prix réel du moteur
avant l'achat ; la sonde n'en invente pas le résultat. Si ce prix change entre
sélection/exécution, le cas de frontière exacte n'est pas qualifié sans la
mesure du garde réel décrite dans les raccordements. `prix × added` n'est pas
une dépense comptable ; aucune comptabilité imbriquée ajoutée.

Les ID `fN` suivent la copie admise dans ce flux. Une nouvelle sélection crée
une nouvelle révision/ID ; cela n'est pas automatiquement la même demande.
Compagnie + fichier/phase + ID font la clé. Les compteurs sont **transitoires**,
sans prétention de persistance ; aucune jointure automatique entre phases.

### R3

- `examine` avant la garde existante ; `reject batch_plan_dead` immédiatement
  avant son `continue`, **sans rappeler** `OpexAirBatchPlanStillLive` ;
- `consume` immédiatement après l'unique affectation du bypass ;
- `stop cash/k_pass` immédiatement au vrai `break` financier ;
- `attempt` = entrée de l'exécuteur, pas preuve d'appel constructeur ;
- `result` = retour réel de l'exécuteur avec raison, détail/erreur déjà capturés
  dans `attempt.discards`, nombre de lignes avant/après ; aucun nouvel `AIError`
  après coup ni retest physique.

Chaque événement comporte passe/cycle/rang, clé du projet, O/D, ancres,
financement/disponible/seuil, état bypass avant/après et constructions antérieures.
Les valeurs financières déjà calculées sont réutilisées aux barrières ; la
sonde lit les valeurs courantes au rejet précoce et à l'entrée/résultat.
Ces lectures ajoutent des opcodes **dans le profil test-only**. Leur neutralité
temporelle n'est pas mesurée ; même les gardes OFF peuvent décaler la trajectoire.
Un opcode conventionnel n'est jamais du temps CPU.

**Détail préservé du code courant :** sous K_pass, le bloc `projCap > availCap`
pose `c75StopReason="cash"` mais ne fait pas lui-même `break`. La trace y est
`cash_note`, **pas** `stop`. Le scénario d'arrêt financier ci-dessous exige
`finance >= K_pass`. Aucune modification de cette politique.

## Harnais et provenance

Interface module `sweeps.diag_r1_r3_mechanisms` :

| Action | Entrées | Effet |
|---|---|---|
| `prepare` | `--out` dossier neuf | Écrit `plan.json`, aucune importation moteur ni partie. |
| `analyse` | `--input` logs explicites ou JSON Save/Load, `--out` neuf | Écrit `analysis.json`, hashes/lignes/portées conservés. |
| `smoke` | `--out` neuf, **`--centralized --sources-stable` obligatoires** | Après intégration uniquement : un duel d'exposition, un worker, 42, 1970→1971-02-01, IA test-only. |

Tous les dossiers doivent être sous `results/r1_r3_mechanisms/` ; dossiers déjà
présents (même vides), fichiers déjà présents et sortie hors périmètre refusés.
Pas de réutilisation du dossier créé par `prepare` pour `smoke` : choisir un autre
identifiant et garder le plan pré-enregistré. Pas de commande conteneur intégrée.

Réutilisation effective du lanceur moteur :

- `bench_v2.make_cfg`, résolution des réglages et adversaire AAAHogEx-115 ;
- `diag_cadence_duel.collect`, qui appelle `extract_company_record` et les
  compteurs physiques officiels, sauvegarde log/checkpoints, retourne un tuple ;
- instrumentation script=4 et capture d'échecs moteur existantes ;
- `game_health.assess_game` sur les checkpoints, log et horizon ;
- versions OpenTTD/OpenGFX de `bench_v2`, bibliothèques Queue/Pathfinder existantes.

Bras limité à `decision_log=1`, contrôles C115=1 et options protégées OFF avant
le moteur. La copie activée est hachée ; empreintes des sources locales et de
la copie avant/après, configuration et réglages effectifs dans les artefacts.
Le lanceur n'annonce pas de SHA Git ni de bundle runtime/downloads immuable.
L'intégrateur doit conserver aussi l'ID d'image, versions/cache des bibliothèques
réellement utilisés et son gel commun. Pas d'installation automatique par ce lot.

La présence de métriques économiques dans les checkpoints du collecteur partagé
est de la collecte brute, **pas** une évaluation économique : `economic_verdict`
reste `not_evaluated`. Pas de bras « ancien bug » et pas d'A/B économique.

Le lecteur conserve `None`/`unknown`, ne déduit pas la compagnie du script,
rejette les identités contradictoires, signale duplications et logs mal formés,
isole les phases Save/Load. Les marqueurs de santé sont lus via
`game_health.parse_script_errors` ; leur absence ne certifie pas l'horizon.

`trace_status=pass` signifie seulement que les **conditions de trace observées**
sont remplies ; même sur un log moteur, `engine_validated=false` tant que les
préconditions de fixture, inventaires physiques et raccordements ne sont pas
attestés. `r1_reload` reste volontairement `non_expose` sans contrat transversal
de sauvegarde : un `LOAD_RECONCILE` ne suffit pas.

## Protocole moteur pré-enregistré — critères par scénario

Sources stabilisées, C115 inchangé, réglages au défaut hors sonde de décision,
graine **42**, année initiale **1970**, horizon initial **un an** pour le smoke.
Les essais dirigés reprennent chacun un état identifié par SHA-256 ; le passage
R1 nécessite une ligne AIR réellement en service, même si cet état doit venir
d'un horizon antérieur plus long. Ne pas prolonger implicitement une partie
jusqu'à un résultat favorable : enregistrer un amendement avant nouveau run.
Les valeurs numériques suivantes sont relatives au **prix API observé P**, pas
au prix fictif 30 000 £ des tests Python.

| Cas | Préparation du monde réel et appels | Réussite moteur exigée | Échec / non-exposé |
|---|---|---|---|
| R1 exact | Demande vivante issue du producteur flotte, `want=4`, base à jour ; trésorerie réelle telle que disponible net réserve = P+1 000 ; passer par le sélecteur commun puis l'exécuteur normal. | Même filiation 4→1, rang final admis, retour d'achat réel +1, un nouvel ID principal avec ordres valides, aucun remplacement/avion orphelin, inventaire final = initial+1. | Fit seul = incomplet ; fit admis sans achat = échec complet (motif conservé) ; prix/réserve/caisse changés avant achat = frontière non-exposée, ne pas les figer artificiellement. |
| R1 dessous | Copie du même état, disponible = P+999, gardes inventaire/profit identiques. | Retour nul du fit, absent du classement, aucune commande flotte associée et inventaire physique inchangé. | Autre garde en échec ou état exact absent = non-exposé ; achat malgré seuil = échec. |
| R1 inventaire | Après sélection réelle, une commande API réussie modifie la flotte et réconcilie le cache de ligne ; conserver le snapshot original. | Exécuteur refuse `fleet_stale` avant tout `OpexAirAddPlane`, inventaire d'après mutation inchangé. | Modifier seulement `vehCount` ou `baseVehicles` ne prouve rien ; mutation impossible = non-exposé ; achat du snapshot = échec. |
| R1 deuxième passe | Après le succès R1 exact, soumettre le **même snapshot** à la passe suivante, sans réécrire sa base ; distinguer un nouveau besoin régénéré. | `fleet_stale` ou exclusion par clé construite lorsque pertinente ; zéro seconde commande/achat, mêmes IDs. | Absence de seconde soumission = non-exposé ; nouveau besoin ≠ double achat du premier ; commande dupliquée = échec. |
| R1 Save/Load | Sauvegarder après sélection et avant exécution, puis après achat avant seconde soumission ; chaque checkpoint exact haché. | `LOAD_RECONCILE`, ligne/IDs/cartographie snapshot attestés ; revalidation contre monde rechargé, achat au plus une fois, inventaire physique cohérent. | Save mensuelle hors fenêtre = non-exposé ; retour logiciel OK sans frontière couverte = incomplet ; état/achat dupliqué = échec. |
| R3 caduc | Trois projets du vrai catalogue, classement normal A–B, A–C (`reuseA=false`, pas de second-slot), D–E indépendant, initialement vivants ; A–B réussit réellement. | Revalidation invalide A–C naturellement ; A–C et D–E vérifient K_pass≤finance≤disponible ; A–C 0→0, D–E 0→1 puis succès réel, identité et nouvelle ligne physique cohérentes. | Caduc forcé par booléen = invalide ; rang/admissibilité/financement manquants = non-exposé ; consommation par A–C ou D–E non tenté malgré préconditions = échec. |
| R3 trop cher | A–B réel ; candidat initialement vivant/finançable, restant vivant mais finance≥K_pass et finance>disponible après chantier. | `stop cash`, état bypass inchangé, pas d'appel constructeur de ce candidat ni tentative suivante dans la passe. | finance<K_pass ne teste pas cet arrêt ; autre garde = non-exposé ; poursuite au-delà du vrai arrêt = échec. |
| R3 refus réel | Candidat finançable consomme le bypass ; provoquer dans le monde un refus du constructeur **après** les contrôles physiques ; suivant vivant, K_pass≤finance≤disponible. | Retour API/AIError réels puis `build_failed`, rollback/récupération vérifié, pas de ligne fantôme ; bypass reste 1, suivant arrêté par `k_pass`, sans deuxième achat. | Refus du prétest de site, R19 synthétique, finance devenue insuffisante = non-exposé ; bypass remboursé ou ligne fantôme = échec. |

Chaque scénario publie son état **réussite / échec / non-exposé / non-validé
technique**. Précondition absente n'est ni zéro achat attesté ni réussite.
Crash, santé manquante, sources modifiées ou log tronqué = non-validé technique.
La preuve de non-duplication/ligne fantôme exige la correspondance **compagnie,
lineId, gares, véhicules principaux et ordres**, pas seulement les totaux.
Le lecteur n'érige pas `len(VEHS)` en compteur ; ne pas réutiliser les anciens
totaux bruts de `save_load_roundtrip.parse_sav_file` pour ce contrôle.

## Raccordements exacts pour l'intégrateur — non effectués

### 1. Fixture du monde et points de contrôle

Le lanceur livré observe les véritables parcours naturels, **sans contrôler la
caisse ou forcer l'ordre des projets**. Pour les cas exacts, préparer un état
via scénario/contrôleur de test moteur, archiver les commandes et leurs retours.
Ne pas remplacer `capitalBudget`, `OpexAvailableCapital`, les retours de
constructeur ni les booléens de liveness par des valeurs prescrites.

Points à raccorder dans la copie test-only stabilisée :

- R1 : entrée de `OpexProjectSelectAffordable`, autour de son unique
  `OpexProjectFitFleetToBudget` (déjà tracé), puis **avant** l'appel
  `_tryBuildFleetProject` dans `_tryBuildProjects`. Suspendre uniquement le
  coordinateur de fixture à ce point pour mutation réelle/sauvegarde, pas le
  sélecteur ou la politique de production. Relever le classement après toute
  promotion. Aucun ajout de quota ou priorité pour rendre le cas atteignable.
- Prix exact : dans `air_fleet.nut::OpexAirAddPlane`, après les calculs existants
  `price`, `need`, `money` et avant `if (money < need)`, journaliser sous la même
  gate ces **variables existantes**, moteur et ligne, sans refaire le garde ni
  calculer une dépense par différence de cash. Ce fichier est hors lot : aucune
  référence à une future fonction manquante n'a été laissée dans le code livré.
- R3 initial : figer les références de trois vrais plans dans le catalogue avant
  la passe et attester leur liveness initiale. Utiliser les contrôles métier dans
  la **préparation** de fixture, pas les rappeler pour chaque log. Ne pas
  promouvoir D–E artificiellement ni désactiver les filtres existants.
- R3 refus : `air_construction.nut::OpexBuildAirRoute` et son premier véritable
  appel `AIAirport.BuildAirport` sont hors lot. Le coordinateur moteur externe
  doit intercaler un obstacle/prise de slot réel après les prétests, avec preuve
  de commande réussie ; lire le retour et `AIError` capturés immédiatement par le
  constructeur courant. Un obstacle posé trop tôt donne `site*_unbuildable` et
  **ne couvre pas** ce cas. `r19_fault_inject` reste 0 : son bloc force erreur −1
  et `START` après achat, donc ce n'est pas un refus API acceptable ici.

### 2. Save/Load exact et séquentiel

`save_load_roundtrip.py` est lu et réutilisable pour `make_patched_check_output`,
`run_phase_a` / `run_phase_b`, capture des saves, retrait de `start_ai` au reload
et preuve `LOAD_RECONCILE`. Son `main()` choisit par `mid_fraction` une date
mensuelle et partage `.scratch_saveload`, dont il remplace les sous-répertoires.
**Ne jamais le lancer simultanément**, ni laisser ce remplacement effacer une
preuve : sauvegarder ses artefacts dans un dossier neuf après chaque essai.
Le présent lot ne l'appelle pas et n'a rien nettoyé.

L'intégrateur doit ajouter un choix **exact par hash/date/phase de mécanisme**
dans son raccord, pas faire passer `mid_fraction` pour ce contrôle. Appeler les
fonctions de phase avec dossiers/checkpoints neufs plutôt que le `main()`
historique. Enchaîner A puis B, un worker, et conserver les deux stdout isolés,
les `.sav` réellement chargés et leurs hashes. Réutiliser `assess_game` et les
décodeurs physiques par propriétaire pour les deux phases ; conserver la
compagnie humaine supplémentaire éventuelle au reload comme métadonnée.

Pour la frontière sélection/exécution, le portefeuille n'est pas une pile
Squirrel automatiquement restaurée. Dans `persist.nut` (hors lot), prévoir sous
gate seulement une enveloppe de fixture versionnée contenant : scénario,
étape, request_id, lineId, baseVehicles, want original/ajusté, IDs avant, clés
des candidats et hash de checkpoint. Après `LOAD_RECONCILE`, retrouver la ligne
par ID et comparer l'inventaire réel ; ne pas persister des références d'objets
NoAI ni réinjecter un besoin caduc comme neuf. Publier explicitement le mapping
pré-save→post-load. L'absence de ce raccord interdit de joindre `f1` en phase A
au `f1` recréé en phase B. Si le choix retenu est une reconstruction sans
snapshot persistant, la tester et l'étiqueter séparément ; ne pas prétendre
avoir repris la même décision suspendue.

## Ordonnancement central

1. Finir toutes les éditions ; relire le diff/empreintes de chaque lot et figer
   sources/configuration/runtime. Aucun agent ne lance une partie entre-temps.
2. Smoke défaut 1×1 via harnais existant pour compilation et `require`, puis
   smoke test-only livré, **un worker**. La seconde partie vérifie les branches
   instrumentées ; elle ne remplace pas les huit états dirigés.
3. Exécuter les fixtures ciblées séparément, dans des sorties uniques ; publier
   aussi les non-expositions. Arrêter sur santé invalide ou dérive de sources.
4. Save/Load **séquentiel**, A puis B, sans autre usage du répertoire historique.
5. Réconcilier logs/API/saves/ordres et rendre le verdict de mécanisme, sans
   profit attribué. Aucun témoin ancien-bug requis, aucun 5×6/20×10 automatique.

Plafond central absolu **12 CPU / 12 workers** pour tous les lots cumulés ; le
lanceur livré en utilise un. Les flags de confirmation ne sont pas un gestionnaire
global de ressources : cette allocation appartient à l'intégrateur. Sur VPS,
conserver en plus le profil obligatoire 3 CPU / 2 Go / sans swap et cache commun,
sans campagnes concurrentes. Aucun conteneur démarré par ce lot.

## Tests et preuves hors moteur

Fixtures Python séparées des scénarios moteur : `fleet_fixture`,
`STALE_THEN_VALID`, `TOO_EXPENSIVE`, `REAL_REFUSAL`. Ce dernier nom décrit un
**format de trace simulé pour le lecteur**, pas une exécution API attestée.
Les sorties de test portent `synthetic_fixture` / `synthetic_reader_fixtures` ;
elles ne deviennent jamais `engine_validated=true`.

Validation exécutée dans le venv existant **Python 3.14.4**, avec `-B -X utf8`,
sans installation : **94/94 tests réussis**, aucun skip :

| Module | Tests |
|---|---:|
| `sweeps.test_r1_r3_mechanisms` | 33 |
| `sweeps.test_r1_partial_fleet` | 8 |
| `sweeps.test_r3_air_bypass` | 6 |
| `sweeps.test_parallel_fleet_audit` | 26 |
| `sweeps.test_parallel_bypass_audit` | 21 |

La découverte de tests de l'éditeur n'a rien trouvé ; exécution explicite de
ces cinq modules par `unittest`. Le contre-test de changement de `lineId` a
révélé une jointure trop permissive, corrigée et revérifiée. Une erreur
d'indentation introduite à l'application d'un patch a aussi été corrigée avant
le passage final. Les diagnostics éditeur seuls ne remplaçaient pas ce contrôle.

Artefacts réellement produits, **hors moteur** :

- `results/r1_r3_mechanisms/pre_registered_20261001_r1/plan.json` : huit critères,
  séquence, limites, empreintes locales, `engine_executed=false` ;
- `results/r1_r3_mechanisms/historical_coverage_20261001_r1/analysis.json` : lecture
  CLI des logs `profile_42.log` et `reference_42.log` de l'intégration r2 ;
- `results/r1_r3_mechanisms/reader_fixtures_*/` : fixtures JSON, provenance
  **synthétique**, tests d'exclusivité et copie test-only, conservés sans nettoyage.
  Ces copies ne sont **pas** des bundles moteur exécutés ;
- `results/r1_r3_mechanisms/validation_20261001_r1.json` : reçu des tests ciblés
  et contrôles statiques finaux.

Les deux logs historiques contiennent **zéro nouvelle trace R1R3** : les huit
cas restent `non_expose` pour ce lecteur. Cela ne signifie ni zéro renfort ni
zéro caducité dans ces parties anciennes ; leurs autres canaux restent couverts
par les audits antérieurs. Empreintes des entrées dans `analysis.json` : profil
`da2f743324d2db7e3849be7ca44ea0a9d518123d2c3135dc248bd5716ad232f0`, référence
`0e237d86cfd14cd20f08301c3230f78b68e1e858fd1229f9f6f1b103b737d2b2`.

**Conclusion :** sondes OFF et harnais d'exposition préparés, lecteur testé,
protocole des huit scénarios pré-enregistré. Les états moteur dirigés et la
persistance au checkpoint exact ne sont pas encore raccordés ; critères et
points d'intégration sont explicités, pas déclarés réussis. **Aucune partie ni
aucun conteneur lancé, aucune compilation Squirrel ou preuve économique acquise.**