# Tâches — réduire l'écart avec AAAHogEx

Revue du **2026-09-13**. Ce fichier contient les décisions actuelles et le prochain travail
utile. Les travaux terminés et leurs dossiers, y compris C65 (`19609f8`), sont transférés
dans [le journal du 13 septembre](journal_2026-09-13.md). Les développements antérieurs y sont
conservés intégralement pour la traçabilité ; seul ce fichier prescrit le travail restant.

Avant de rouvrir une piste, rechercher son nom et ses réglages dans ce journal **et** dans
[l'archive du 9 septembre](taches_archive_2026-09-09.md). L'archive sert à retrouver les
implémentations et les raisons des décisions ; **aucun résultat antérieur au 09/09 ne prouve
la performance actuelle**. Les journaux quotidiens conservent le détail des expériences.

## Où nous en sommes

**Le retard économique est établi ; sa cause dominante ne l'est pas encore.** Le duel partagé
20 graines × 5 ans du 13 septembre donne les résultats suivants, recalculés depuis les
20 paires de [la référence](../results/bench_1v1_5y_20seeds_reference.json) :

| Dernier checkpoint : 1974-12-01 | OpexAI, moyenne | AAAHogEx, moyenne | Écart des moyennes Opex/AAAHogEx | Victoires Opex |
|---|---:|---:|---:|---:|
| Valeur de compagnie | 2,189 M£ | 7,698 M£ | −71,56 % | 0/20 |
| Profit annuel | 676 k£ | 4 000 k£ | −83,09 % | 0/20 |
| Score de performance | 483 | 807 | −40,09 % | 0/20 |
| Moyenne des notes médianes de gare | 167,6 | 186,8 | −10,28 % | 0/20 |
| Gares possédées | 64,5 | 177,6 | −63,68 % | — |
| Caisse | 364 k£ | 1 650 k£ | — | — |
| Emprunt restant | 223,5 k£ | 0 £ | — | — |

Ces pourcentages sont des **rapports de moyennes**, pas la moyenne des pourcentages par graine.
Le harnais annonce zéro échec et les 40 lignes finales atteignent bien décembre 1974.
Il ne renseigne toutefois pas `expected_last_year` et ne transmet pas la sortie du moteur au
contrôle d'échec d'AAAHogEx : sa validation automatique reste à compléter (P0).

**Retrait du diagnostic « 93 % de rendement par véhicule, donc presque uniquement du volume ».**
Le harnais [du duel](../sweeps/bench_1v1_5y_20seeds.py), dans `extract_company_record`, compte
les entrées `VEHS` par propriétaire sans filtrer les composants. Les 102,4 contre 564,35 sont
ces entrées ; C54 a déjà identifié le piège wagons/ombres/rotors. Les décodeurs
`vehicle_breakdown` et `physical_telemetry`, malgré le nom `primary_vehicles_by_mode` de ce dernier,
ne filtrent eux aussi que type et propriétaire. Leur comptage demande la même qualification.
Même avec de vrais véhicules, une moyenne mélangeant bus, avions et trains ne prouverait pas
une équivalence de rendement. **Ne pas dériver de productivité ni de cible de flotte de ces comptes.**

L'emprunt nul d'AAAHogEx **à l'arrivée** ne veut pas dire qu'elle n'a jamais emprunté.
La dette élevée et la caisse positive d'OpexAI ne suffisent pas non plus à désigner le capital
ou le contrôleur comme goulot : il faut observer les occasions réellement disponibles et leur
financement au moment du refus. Les relevés économiques restent utiles malgré le problème de flotte.

La [chronologie C50](../results/diag_1v1_chronology_6y_5seeds.json) situe une rupture à examiner
dès **1971** : sur cinq graines, les créations nettes de gares passent de 148 contre 72 en 1970
à 57 contre 241 en 1971. Ce sont des sommes sur cinq parties, et des variations nettes de stock,
pas un comptage des chantiers. Le volet véhicules reste soumis à la réserve ci-dessus.

## Pourquoi le travail donne une impression de surplace

1. **La mesure du progrès a glissé vers le volume et les opcodes.** C51 augmente le nombre de
   gares sans gain économique démontré ; C50b augmente la flotte routière et dégrade la valeur.
   Une optimisation locale ou un réseau plus gros n'est pas encore un rattrapage.
2. **Les essais sont surtout arbitrés en solo.** Une victoire contre notre propre référence
   sur une carte séparée ne démontre pas une meilleure résistance à AAAHogEx sur carte partagée.
   Nous n'avons pas ici une série homogène de duels entre versions permettant de mesurer une
   vitesse de rattrapage. Le duel récent établit le retard, pas l'absence de tout progrès passé.
3. **Les mêmes hypothèses réapparaissent après leur réfutation.** Exemples : supprimer les
   plafonds après C50b ; proposer P1.1 comme inédit en C63 ; expliquer le rail improductif avec
   le comptage invalidé de C54 ; conserver le « facteur 15 inexpliqué » après sa correction C39.6.
4. **Les statuts confondaient livré, adopté et rentable.** C56 a corrigé un gel réel ; C65 facilite
   le développement. Ce sont des acquis. C60 n'a qu'un smoke de son filtre ; C53 non-stop est
   adopté mais son gain économique n'est pas établi statistiquement par le banc cité.

**Objectif de la prochaine séquence : augmenter le profit et la valeur en duel, en expliquant
le mécanisme qui permet de réinvestir.** Le nombre de véhicules, les gares et les opcodes restent
les instruments de diagnostic. Ils ne remplacent pas cet objectif.

## Ordre de travail

| Rang | Chantier | Question qui doit être tranchée | Livrable / condition de passage |
|---|---|---|---|
| **P0** | **C66 : duel fiable et référence reproductible** | Quelle est la trajectoire économique actuelle face à AAAHogEx, avec une flotte correctement comptée ? | Harnais qualifié, référence figée ; réutiliser les données valides avant de relancer |
| **P1** | **C63 + C58 : investissement et réinvestissement** | Où se perd la croissance à partir de 1971 : coût, revenu capté, occasions absentes ou décisions lentes ? | Un diagnostic commun 5×6, attribution par mode/âge de ligne, puis **un seul** correctif causal |
| **P2** | C61 + C59 : exploitation des infrastructures rentables | Quelles lignes profitables disposent de demande non servie et d'une capacité réellement disponible ? | Cibler le mode exposé par P1 ; un levier isolé, sans rejouer la suppression brute des plafonds |
| **P2 conditionnelle** | C39/C41 : coût des décisions utiles | Reste-t-il des projets valides et finançables que le contrôleur traite trop tard ? | Montrer un délai et une occasion perdue sur l'arbre courant avant de modifier la cadence ou les caches |
| **P3** | C52/C60, eau/C57, autres | Quel effet matériel subsiste hors des priorités ci-dessus ? | Remontée seulement sur exposition mesurée ou défaut bloquant reproductible |

La première action est P0, puis le diagnostic commun C63/C58. **Ne pas lancer simultanément
une nouvelle famille de plafonds, un nouveau score et un orchestrateur général.** Les rangs P2
restent des suites conditionnelles ; rien ne prouve encore que l'un d'eux est le meilleur levier.

<a id="c66"></a>
## P0 — C66 : fiabiliser le duel et rendre le rattrapage mesurable

**Statut : à faire.** Fiche ouverte le 2026-09-13 à la demande de l'utilisateur ; elle reprend
le volet « référence fiable » de C64. C64 conserve uniquement la piste adaptative, différée.
**But :** pouvoir dire si une modification d'OpexAI améliore son résultat économique **contre
AAAHogEx**, avec des mesures correctes, des parties complètes et une comparaison reproductible.
Cette fiche porte sur le harnais et ses preuves ; elle ne change aucune stratégie de jeu.

### C66.1 — Corriger et qualifier les compteurs physiques

**Défaut localisé :** `extract_company_record` dans
[`bench_1v1_5y_20seeds.py`](../sweeps/bench_1v1_5y_20seeds.py) compte les entrées `VEHS`
possédées. `vehicle_breakdown` dans `diag_1v1_monthly.py` et `physical_telemetry` dans
`bench_c50b_physical.py` ne filtrent pas davantage les composants internes. Le champ `type`
distingue les modes, pas nécessairement la tête d'un véhicule de ses composants.

- [x] Définir **un décodeur partagé**, avec un schéma de sortie versionné (`sweeps/physical_counters.py`,
  schéma 1.1.0). Garde le compte brut sous `vehicle_pool_entries`, ajoute les unités pilotables
  par mode (`primary_vehicles_by_mode`) et le bilan des anomalies (`unclassified_entries`).
  `n_vehicles` conserve sa valeur brute dans les enregistrements de sortie pour assurer la
  rétro-compatibilité sans dérive silencieuse. Respect strict du principe **fail-closed** :
  si un chunk est manquant (`None`) ou de type inattendu, `chunk_valid` passe à `False`,
  `chunk_error` documente la cause, et les compteurs — y compris les secondaires
  (`fleet_status`, `components_breakdown`, `station_ids`) — sont passés à `None`.
  Une anomalie interne (pointeur de convoi mort, cycle, composant non-dict, gare
  non résolue) invalide aussi `chunk_valid` : le comptage partiel n'est plus
  `physical_ok`. `schema_version`, `qualified_modes`, `vehs_chunk_valid`,
  `stnn_chunk_valid`, `physical_ok` et les causes d'erreur sont conservés dans les
  métadonnées de `bench_1v1_5y_20seeds.py`, `diag_1v1_monthly.py` et
  `bench_c50b_physical.py`. `summarise()` propage `physical_ok` et bascule
  `run_ok=False` avec `failure_reason` explicite dès qu'un chunk physique est corrompu.
  L'agrégation mensuelle reçoit `args.seeds` et les mois calendaires attendus : une
  graine qui n'a produit aucune ligne reste `FAIL v/e`, pas un `1/1` silencieux.
- [x] Qualifier les discriminants de tête/composant sur les chunks **réellement produits par
  OpenTTD 15.3**. Confrontation formelle et exacte à un inventaire API NoAI indépendant
  (`AIVehicleList`, `AIVehicle.IsPrimaryVehicle(v)`, `AIStationList`, `AIStation.HasStationType`)
  capturé au **même instant exact** de jeu (autosave `1970-12-01`, graine 42) dans
  `sweeps/fixtures/c66_control_fixture_15_3.json` via `sweeps/generate_c66_control_fixture.py`
  (injection garantissant un réveil le 1er du mois sans décalage temporel).
  Égalité ensembliste exacte :
  `primary_vehicle_ids` API == `primary_vehicles_detail` décodés (21 unités : IDs 7, 9, 10, 11, 12, 15, 16, 17, 18, 19, 20, 21, 22, 24, 25, 26, 27, 28, 29, 30, 32).
  `primary_vehicles_by_mode` API == chunks décodés (`rail: 1, road: 17, air: 3, water: 0`).
  Composants exclus sans résidu : 2 wagons ferroviaires, 3 ombres d'aéronefs, 7 effets, zéro non classé.
  Le mode bateau est explicitement étiqueté `qualified: False` (non exercé).
- [x] Compter un train comme une unité pilotable tout en additionnant correctement la capacité
  de ses wagons. Suivi déterministe de la chaîne de convoi via le pointeur 1-based `next` du
  format saveload (`val - 1 = index`). Capacités strictement ségrégées **par cargo**
  (`capacities_by_cargo`), sans somme hétérogène passagers/tonnes.
  Détection et signalement explicite des corruptions de chaîne : rupture de pointeur
  (`corrupted_consist_pointer_missing_target`), cycle (`consist_cycle_detected`) ou absence de bloc
  commun (`missing_consist_component_common`) alimentent `unclassified_entries` et marquent `consist_valid: False`.
  Observables physiques `vehstatus` strictement conformes à `src/vehicle_base.h` d'OpenTTD 15.3 :
  `is_hidden` (`0x01`), `is_stopped` (`0x02`), `is_broken` (`0x40`), `is_crashed` (`0x80`).
  `running` est strictement défini en excluant stopped, hidden, broken et crashed.
  `fleet_status` expose les observables réels `{stopped, not_stopped, running, hidden, broken, crashed}`.
- [x] Vérifier aussi les propriétaires des gares, les gares multimodales et les représentations
  dictionnaire/liste des chunks. Propriétaire extrait strictement de `base.owner` sans repli
  silencieux (anomalies isolées dans `unresolved_stations`). Une gare multimodale compte pour 1
  dans `total_stations`, avec détail dans `n_multimodal_stations`, `multimodal_station_ids`,
  `stations_by_facility` et `stations_detail`. Confrontation exacte API : 24 gares API == 24 gares
  décryptées (IDs 0 à 23), 4 gares multimodales bus+air (0, 1, 14, 21) comptées 1 fois dans le total,
  installations identiques (`rail: 2, truck: 6, bus: 16, airport: 4, dock: 0`).
  Intégré et validé dans `bench_1v1_5y_20seeds.py`, `diag_1v1_monthly.py` et `bench_c50b_physical.py`
  avec protection contre les valeurs `None` et suites `--selftest` autonomes.

**Preuve technique :**
- Suite de tests unitaires et empiriques `sweeps/test_physical_counters.py` validée à 100 % (7/7 tests OK)
  sur l'hôte et dans Docker avec les limites canoniques (`--cpus=3 --memory=2g --memory-swap=2g`).
- Fixture de contrôle C66 (`sweeps/fixtures/c66_control_fixture_15_3.json`, générée par
  `sweeps/generate_c66_control_fixture.py`) intégrant à la fois les chunks bruts et l'inventaire API
  NoAI indépendant au **même instant exact** (`1970-12-01`), avec assertions automatisées d'égalité ensembliste stricte.
- Selftests unitaires autonomes validés sur `bench_1v1_5y_20seeds.py --selftest`, `bench_c50b_physical.py --selftest`
  et `diag_1v1_monthly.py --selftest`.

### C66.2 — Séparer santé du moteur, santé des compagnies et activité de l'IA

**Défauts localisés :** le duel appelle `summarise(rows)` sans `expected_last_year` ; `keep`
transmet toute la sortie du moteur à OpexAI et une chaîne vide à AAAHogEx. Le détecteur commun
cherche des marqueurs fatals sans attribution de compagnie. Une erreur d'AAAHogEx pourrait donc
être imputée à OpexAI, tandis que la ligne AAAHogEx serait déclarée saine.

- [x] Journal moteur **une seule fois par partie** : `keep` écrit
  `{out}_engine/seed{S}_r{R}.log` et pose le même `engine_log_path` sur les deux
  compagnies ; plus de stdout recopié dans le JSON. Parseur
  [`sweeps/game_health.py`](../sweeps/game_health.py) : `[script:N] [company]`
  confronté au manifeste des places (script 0 → OpexAI / compagnie 0, script 1 →
  AAAHogEx / compagnie 1). Script inconnu, company id contradictoire ou marqueur
  sans identifiant → `unattributed`, jamais joueur 0 par défaut.
- [x] `summarise(..., expected_last_year=starting_year+years-1)` dans le duel, plus
  le dernier checkpoint exigé `YYYY-12-01` (`expected_last_checkpoint`). Un
  1974-01-01 pour un 5 ans 1970 n'est plus une année complète. Contrôle des deux
  compagnies, des doublons `(arm, date)` et des absents.
- [x] Statuts distincts : `engine_error`, `missing_data`, `duplicate_checkpoint`,
  `noai_error`, `horizon_truncated`, `bankrupt`, `stagnation_suspect`, `complete`.
  `include_in_economic_stats` / `run_ok` reste vrai pour faillite, fin complète et
  suspicion de gel ; faux pour les erreurs de collecte. `game_ok` est faux dès
  qu'une compagnie de la partie est en erreur de collecte, même si l'autre est saine.
- [x] Activité : deltas de flotte, de gares et de valeur. Signal `active` /
  `earning_without_expansion` / `no_signal`. Pas de construction + valeur qui
  bouge ≠ gel. `no_signal` sur un horizon complet → `stagnation_suspect`, **pas**
  une exclusion des moyennes.

**Preuve :** [`sweeps/test_game_health.py`](../sweeps/test_game_health.py) (20/20
sur l'hôte) avec les journaux
[`sweeps/fixtures/c66_health/`](../sweeps/fixtures/c66_health/) — erreur OpexAI
seule, erreur AAAHogEx seule (Opex reste `complete`), log ambigu non attribué,
compagnie absente, janvier de dernière année tronqué, décembre complet, faillite
conservée dans les stats, earning sans expansion, suspicion sans exclusion,
doublon, fatal moteur. Selftest Docker de
`bench_1v1_5y_20seeds.py` : `keep` partage le chemin de log et n'impute pas une
erreur HogEx à Opex. Aucune IA de production n'a été crashée.

**Corrections (revue, 2026-09-14) :** trois P1 et un P2 rouvraient des faux
positifs de santé.

1. `annotate_summary` ne réhabilite plus un `run_ok=False` de `summarise`
   (`physical_decode_failure` reste `missing_data`, `game_ok` faux).
2. `enable_engine_failure_capture` (timeout 1800 s par défaut, avant le cleanup)
   attrape `CalledProcessError` / `TimeoutExpired` dans le worker et rend des
   lignes `engine_error` au lieu d'abandonner `run_experiments`. Un crash qui
   sort 0 avec un marqueur fatal reste lu dans le journal.
3. Une compagnie présente plus tôt puis absente au dernier checkpoint est
   `missing_data`, sauf faillite déjà établie.
4. `earning_without_expansion` exige une variation de valeur dans les 3 derniers
   pas ; un revenu de février suivi de dix mois figés est `no_signal`.
5. Le wrapper de capture copie la signature de `_run_experiment` (`__wrapped__` +
   `__signature__`) ; `enable_savegame_cleanup` retrouve `run_dir`/`i`/
   `final_screenshot_directory`. Testé en composition (hôte + selftest Docker).
6. `games[]` est reconstruit via `reconcile_assessment` après `annotate_summary` :
   un fail-closed physique n'y reste plus `game_ok=true/complete`.

### C66.3 — Figer une référence réellement reproductible

- ⬜ Créer un manifeste contenant : SHA Git, état modifié, empreinte et copie isolée des sources
  effectivement exécutées, version/empreinte d'AAAHogEx et des bibliothèques, versions
  OpenTTD/OpenGFX/OpenTTDLab et image Docker, configuration effective, réglages IA explicites
  **et défauts**, année initiale, durée, graines, répétitions et places des compagnies.
- ⬜ Figer les sources **avant** de lancer les parties ; les modifications de l'arbre de travail
  pendant le banc ne doivent pas contaminer les graines suivantes. C65 illustre pourquoi un
  SHA sans le contenu modifié ne suffit pas à décrire le programme exécuté.
- ⬜ Identifier séparément la politique testée, la compagnie et la partie : par exemple
  `(campaign, policy, seed, repeat, company_slot)`. Les noms « OpexAI » et « AAAHogEx » ne sont
  pas les deux variantes de stratégie. Refuser les paires dont les configurations diffèrent
  sur autre chose que l'intervention annoncée.
- ⬜ Conserver résultats compacts, checkpoints, manifeste, logs uniques et fixtures de décodage.
  Sorties sous un nom de campagne nouveau ; ne pas écraser la référence 20×5 ni ses JSONL.
  Les empreintes servent à relier une mesure à son code, pas à affirmer l'équivalence de deux codes.

**Preuve attendue :** deux relances courtes de la même référence isolée produisent les mêmes
métriques aux mêmes checkpoints. Si elles divergent, documenter et traiter la source de variation
avant d'attribuer une petite différence à une stratégie ; ne pas sélectionner la meilleure relance.

### C66.4 — Comparer deux politiques, chacune contre le même adversaire

Étendre le harnais existant avec la validation des réglages de `bench_v2.py`, sans écrire un
nouveau lanceur ad hoc. Pour chaque graine, exécuter **deux parties distinctes** :

| Partie | Compagnie OpexAI | Adversaire | Conditions |
|---|---|---|---|
| Témoin | Référence figée | AAAHogEx figée | Même graine, configuration, durée et place |
| Variante | Même référence + intervention isolée | Même AAAHogEx | Seule l'intervention annoncée diffère |

L'évolution ultérieure d'AAAHogEx peut différer entre les parties parce qu'OpexAI agit autrement :
c'est une conséquence du duel, pas un défaut d'appariement. Ne pas comparer deux OpexAI jouant
ensemble, ni la variante seule à une référence jouant contre AAAHogEx. Garder les places fixes
pour le premier protocole ; une inversion des places serait un bloc de robustesse distinct.

- ⬜ Fixer avant le banc la métrique primaire — **proposition : profit annuel final d'OpexAI** —,
  l'effet minimal utile et le garde-fou sur la valeur. Conserver les trajectoires annuelles,
  notamment 1970–1972, pour distinguer gain précoce et destruction de croissance à long terme.
- ⬜ Rapporter deux comparaisons différentes : `Opex_variante − Opex_témoin` sur chaque graine,
  puis l'écart `Opex − AAAHogEx` dans chacune des deux parties et son évolution. Une réduction
  du retard obtenue seulement en dégradant les deux compagnies n'est pas un gain économique
  d'OpexAI. Rapporter aussi les victoires directes contre AAAHogEx.
- ⬜ Publier deltas par graine, moyenne et médiane **des deltas**, intervalle d'incertitude,
  V/D/égalités et test des signes excluant les égalités. Les ratios demandent un dénominateur
  positif et doivent distinguer rapport de moyennes et moyenne des rapports.
- ⬜ Garder toutes les graines prévues et tous les statuts. Les erreurs de collecte doivent
  être résolues ou rendre la comparaison incomplète ; ne pas recalculer discrètement le verdict
  sur les seules réussites. Les analyses par mode, richesse ou déclenchement restent secondaires.

### C66.5 — Validation progressive et critères de clôture

1. ⬜ **Hors jeu :** fixtures des compteurs, erreurs par compagnie, horizon, appariement et calculs
   statistiques ; vérifier aussi qu'un réglage inconnu est rejeté et qu'une erreur interrompt
   proprement le rapport de validation sans effacer les résultats.
2. ⬜ **Smoke 1 graine × 1 an :** le duel démarre, les deux compagnies et leurs métriques sont
   présentes. Les scénarios physiques manquants sont qualifiés séparément ; un smoke sans train
   ne valide pas le compteur des trains. Conserver le tuple de dictionnaires retourné par `keep`.
3. ⬜ **Contrôle de répétabilité court**, puis **diagnostic 5 graines × 6 ans** sur référence figée.
   Ce diagnostic peut être partagé avec C63/C58 pour éviter une campagne supplémentaire ;
   distinguer sa télémétrie instrumentée du résultat économique sans sonde lourde.
4. ⬜ **Banc officiel 20 graines × 10 ans** quand une variante causale est prête : 40 parties
   partagées au total, chacune avec deux compagnies, soit 20 paires de politiques. Il valide
   l'intervention ; un nouveau 20×10 sans variante n'est pas requis pour clore le harnais.

**C66 est close lorsque** le décodeur a sa preuve indépendante, les contrôles négatifs détectent
et attribuent les échecs, la référence est figée et répétable, le diagnostic 5×6 est complet,
et le rapport distingue progrès d'OpexAI et évolution du duel. Tout gel suspect non expliqué ou
mode non qualifié doit être indiqué comme limite, jamais transformé en validation générale.
Le livrable est un harnais réutilisable et une référence qualifiée pour P1, pas une nouvelle IA.
Respecter les limites Docker et l'unique campagne consommatrice à la fois, comme en fin de fichier.

<a id="c64"></a>
## C64 — Politique adaptative : en attente d'un mécanisme établi

Le duel 20×5 et le banc `< 50 industries` sont terminés, consignés dans
[le journal du jour](journal_2026-09-13.md). Leur qualification et le futur comparateur relèvent
désormais de **C66**. Le défaut adaptatif reste à 0 : 9 V / 2 D / 9 égalités, p=0,06543,
sur des graines déjà utilisées pour découvrir le seuil, sans validation indépendante.

Pas de nouvelle recherche de seuil sur les mêmes 40 graines. Une reprise demande un mécanisme
identifié par C63/C58, une règle pré-enregistrée et des graines nouvelles. La mesure primaire
porte sur toutes les graines prévues ; les seules graines déclenchées restent une analyse
secondaire, particulièrement si le déclenchement dépend de l'état produit par la politique.

<a id="c63"></a>
<a id="c58"></a>
## P1 — C63 + C58 : comprendre le rendement de l'investissement

**Hypothèse ouverte :** l'expansion rentable ne s'auto-entretient pas assez vite face à la
concurrence. Le coût de construction n'est qu'une explication possible ; une recette trop
optimiste, un mauvais captage ou une occasion non traitée peuvent produire le même symptôme.

**Correction de C63.** Le devis anticipé rail existe :
[`OpexPrequoteRailCandidates`](../ai/OpexAI/projects.nut), `rail_prequote` et
`rail_prequote_keep_plan`, tous deux à défaut 0 dans `info.nut` et lus dans `settings.nut`.
P1.1/P1.3 ont été implémentés et rejetés avant le 09/09 ; leur histoire est dans l'archive,
**leurs anciens chiffres ne sont pas une preuve actuelle**. Ne pas réécrire ce mécanisme ni
réactiver son coût à chaque rebuild en le présentant comme une nouveauté. Les facteurs rail
170 % / route 121 % sont toujours dans le code ; leur justesse actuelle reste à mesurer.

**Un seul diagnostic commun, 5 graines × 6 ans, sur carte partagée**, en examinant d'abord
1970–1972 puis la suite. Réutiliser les sondes coût `RC|`, `AC|`, les événements de construction,
les sauvegardes et les prédictions enregistrées sur les lignes. Vérifier leur couverture
avant de supposer qu'elles suffisent : les succès seuls ne donnent pas les dépenses d'échec.
Ne pas activer aveuglément `decision_log` partout.

**Inventaire du 2026-09-13** (`sweeps/diag_c63_c58.py --selftest`) : les sources existantes
**ne ferment pas** le tableau joint. `OpexSign` écrase la tuile (1,1) ; un chunk `SIGN` ne
garde que le dernier nom, donc `RC|` (succès route, coût réel seulement), `AC|`/`RP|`/`DC|`
(sondes coût défaut 0, panneaux et non AILog) et `OY|`/`OZ|` ne reconstituent pas une série.
C50 a `pred_profit` pas `pred_revenue`, et `project_built.cost` est le modèle. C49 compte des
passes, pas des jours. `LINE_REVENUE` est derrière `decision_log`. L'eau n'a pas d'`actualCost`
(`predicted = 0`). `len(VEHS)` n'est pas une flotte. Quatre trous nommés : dépense prévue vs
réelle y compris échecs ; recette prédite vs réelle avec témoins profitables ; jours
d'occasion via `OpexAvailableCapital` ; une sorte de reliquat par passe. Sonde
`c63_invest_probe` (défaut 0) ajoutée pour ces trous ; agrégation hors-jeu dans
`sweeps/diag_c63_c58.py`.

**Smoke 2×3 ON/OFF** (`results/c63_c58_probe_onoff_3y_2seeds.json`) : **pas bit-identique**.
Graine 42 : +0,60 % de valeur ; graine 100 : **−37,6 %**. 0 échec script. Les conclusions
économiques se lisent sur le bras OFF ; le tableau C63 du diagnostic 5×6 est de la
télémétrie du bras ON, pas une preuve de performance du défaut.

**Diagnostic 5×6 partagé, reliquat corrigé** (`results/diag_c63_c58_6y_5seeds.json`) :
5/5 jusqu'à 1975-12-01, 0 échec script. `c63_invest_probe=1` contre AAAHogEx. Années C63 :
1970–1974 (flush de janvier ; 1975 absent, arrêt au 1er décembre). `len(VEHS)` non utilisé.
Le classifieur ne mappe plus une raison vide vers `waiting_compute` ; les
`passDiscards` (dont `build_failed` / `insufficient_cash`) sont enregistrés sous le gate
C63, pas seulement `decision_log`/`c49`. Une passe A* en vol avec un échec air/route
compte l'échec, pas l'attente. Les totaux leftover+lancé 342–375 j et l'année 1969
sur 5/5 graines viennent d'un flush au 28 décembre qui mélangeait les années : retiré.
Le ledger se ferme au 1er janvier suivant (`OpexC63EnsureYear`) ; la dernière année
d'une partie qui s'arrête en décembre n'est publiée que si le calendrier passe le
1er janvier. Capital immobilisé jusqu'au premier revenu : non mesuré. Eau : 0 ligne.

Jours de reliquat 1970–1972 : absent / invalid / unaffordable / wait / lancé.
Graine 42 = seule graine du smoke 2×3 dont la valeur n'a pas chuté.

| Graine | 1970 | 1971 | 1972 | 1970 | 1971 |
|---:|---|---|---|---|---|
| 42 | 158 / 45 / 0 / 5 / 143 | 70 / 74 / 0 / 67 / 158 | 208 / 30 / 0 / 47 / 76 | portefeuille vide | **mixte** (inv 35 %, abs 33 %, wait 32 %) ; 6 échecs air, `invalid_n=4` |
| 100 | 210 / 71 / 0 / 16 / 55 | 207 / 61 / 0 / 10 / 87 | 207 / 56 / 0 / 0 / 99 | portefeuille vide | portefeuille vide (sonde −38 % à 3 ans) |
| 999 | 86 / 46 / 0 / 17 / 203 | 110 / 50 / 29 / 42 / 133 | 175 / 43 / 0 / 36 / 108 | portefeuille vide | mixte |
| 1234 | 136 / 50 / 18 / 29 / 109 | 155 / 60 / 0 / 30 / 130 | 60 / 97 / 0 / 0 / 190 | portefeuille vide | portefeuille vide |
| 5678 | 202 / 67 / 0 / 0 / 83 | 172 / 23 / 0 / 28 / 140 | 27 / 28 / 0 / 26 / 261 | portefeuille vide | portefeuille vide |

`unaffordable` reste rare (18 j en 1970 sur 1234, 29 j en 1971 sur 999). `demand` = 0.
Recettes, témoins profitables du même mode/âge : air et route en 1970 âge 1, médiane
réel/prévu **≥ 0,91** (air 1,41 / 1,34 ; route 1,10 / 0,91). Rail âge 1 en 1971 :
médiane 0,13 / 0,31, **n=7**. Les lignes positives air/route ne sont pas le trou de 1971.

**Décision.** Ce n'est **pas le capital**. Ce n'est **pas le modèle de revenu** air/route.
Ce n'est pas « caisse ≥ 300 k£ ⇒ CPU ». Ce n'est **pas** « 1971 = attente de calcul » :
sur la graine 42 le reliquat 1971 se partage entre site/échec (`invalid`), portefeuille
vide et A*. En 1970, 5/5 graines ont un reliquat **portefeuille vide**. En 1971 la
pluralité reste le portefeuille vide, sans majorité sur 42 et 999. **Donnée manquante**
pour un levier : *pourquoi* `best` est vide les jours d'absent (vivier, seuil, déjà
construit), mesuré **sans** sonde qui déplace la trajectoire. **Pas de correctif, pas
de C61/C59, pas de C39/C41, pas de devis rail synchrone.** `c63_invest_probe` reste à 0.

**Ventilation de `best == vide` (sonde d'absence C63/P1, 2026-09-14)** :
Une sonde sous gate `c63_invest_probe` ventile les jours d'absence. Deux campagnes 5×6,
à ne pas confondre :

1. **12:03** (`results/diag_c63_c58_6y_5seeds.json`), avant le split unaffordable et
   `empty_probe` : 2654 j `absent` = 2654 j `selection_empty`. Ce JSON **ne contient pas**
   `min_cap`, `avail_cap` ni le nombre d'alternatives. Les bornes « 70–164 » / « 63 k£ vs
   36–48 k£ » citées un temps n'y figurent pas ; elles ne font plus foi.
2. **12:46** (`results/diag_c63_absent_6y_5seeds.json`), après split et sonde échantillonnée :
   1939 j `unaffordable` + 911 j `absent` (toujours `selection_empty`). 135 `empty_probe`
   agrégées : alternatives 81–372 (médiane 233), `min_cap` 15 971–70 806 (médiane 62 653),
   `avail_cap` 3 693–166 935 (médiane 43 661), 103/135 avec `min_cap > avail_cap`, cause
   journalisée `all_unaffordable`. `stage_empty` / `cache_exhausted` / `abandon_filtered`
   restent à 0 j : cette campagne n'exerce pas ces branches. `probe_displaced` reste
   `null` (pas de ON/OFF apparié de la sonde échantillonnée).

**Ne pas générer davantage de candidats par réflexe.** Si le vivier est hors budget,
élargir le scan consomme surtout des opcodes. Le levier à trancher est : candidats moins
chers, réévaluation du cache, ou repêchage des abandonnés — avec les champs déjà
journalisés (`considered`, `min_cap`, `avail_cap`, compteurs d'étape, cache, abandons).

**Comparaison mensuelle 1v1 partagée (2026-09-14).** Le diagnostic C63 ne conservait
aucune métrique du joueur 1 : `n_stations` était le total de la carte, les sauvegardes
étaient nettoyées, `n_ok` comptait une construction réussie plutôt que le tunnel
candidats → acceptés → financés → tentés → construits. Harnais :
[`sweeps/diag_1v1_monthly.py --shared`](../sweeps/diag_1v1_monthly.py), sonde
`monthly_funnel=1` (un AILog par passe projects, défaut 0). Chunks VEHS/STNN/PLYR des
deux compagnies ; waypoints STNN sans `normal` exclus sans invalider le mois ; notes
filtrées `status & 1` (plus la valeur par défaut 175) ; attente = paquets `goods.cargo`.

[`results/diag_1v1_shared_monthly_6y_5seeds.json`](../results/diag_1v1_shared_monthly_6y_5seeds.json)
: 5/5 jusqu'au 1975-12-01, 720 lignes, 0 mois physique `FAIL`. Valeurs OpexAI proches
du C63 absent (moyenne 2,578 M£, médiane 2,923 M£, 1,639–3,215) : la sonde mensuelle
ne rejoue pas le −38 % du smoke C63 ON/OFF. **Pas un banc officiel.**

| Graine | Valeur O vs A | Véhicules | Gares | Air O/A | Route O/A | Rail O/A | Note méd. | HogEx mène dès |
|---:|---|---|---|---|---|---|---|---|
| 42 | 2,92 vs 10,47 M£ (28 %) | 85 vs 254 | 76 vs 177 | 36 / 47 | 48 / 170 | 1 / 37 | 166 / 190 | 1970-11 |
| 100 | 2,03 vs 6,98 M£ (29 %) | 63 vs 197 | 50 vs 168 | 34 / 42 | 27 / 116 | 2 / 38 | 166 / 184 | 1971-05 |
| 999 | 3,21 vs 13,12 M£ (24 %) | 109 vs 353 | 97 vs 234 | 36 / 65 | 69 / 240 | 4 / 48 | 170 / 196 | 1970-08 |
| 1234 | 1,64 vs 8,81 M£ (19 %) | 64 vs 293 | 60 vs 197 | 23 / 58 | 35 / 194 | 6 / 41 | 170 / 180 | 1971-02 |
| 5678 | 3,08 vs 15,80 M£ (20 %) | 81 vs 339 | 67 vs 221 | 36 / 72 | 40 / 225 | 5 / 42 | 170 / 196 | 1970-11 |

AAAHogEx gagne **d'abord par le volume et par l'air précoce**, pas par une rentabilité
unitaire d'un autre ordre. En décembre 1970 elle a déjà plus d'avions (13 vs 4) et une
valeur supérieure, souvent avec *moins* de véhicules. Le dépassement en nombre d'unités
n'arrive qu'en 1971. Ensuite la route HogEx explose (2 → 189 véhicules moyens en 1970–1975)
pendant qu'Opex reste à ~44 bus/camions et ~4 trains. Revenu trimestriel par véhicule
×1,3–1,8 ; notes de gare meilleures ; attente par gare *plus faible* chez HogEx
(les quais Opex sont plus chargés, 2,3–3,3 k vs 1,2–1,9 k). Eau : 0 / 1 navire.

Tunnel OpexAI (somme des passes, pas des projets uniques) : 244 705 considérés →
11 084 acceptés (4,5 %) → 3 170 tentés → 2 862 passés caisse → **213 construits**
(6,7 % des tentatives, 1,9 % des acceptés). AAAHogEx : 3 312 succès de construction
journalisés / 104 échecs (97 %). Rejets Opex : `build_failed` 1211, `search_in_progress`
994, `insufficient_cash` 308, `abandoned_pair` 214, `plan_failed` 181. 1970–1972 :
caisse / A* / `plan_failed`. 1973–1975 : `build_failed` (1136) et A* (808), le taux
ok/tentative tombe de 15 % à 4 %. Ce n'est plus « pas de candidat » : le portefeuille
accepte, la carte refuse.

Pas de correctif. Le levier n'est pas « plus de candidats » ; c'est convertir les
acceptés en constructions, surtout air précoce et tenues de chantier (`build_failed`).

**Désambiguïsation structurelle (2026-09-14) :** l'amalgame `best=absent` / `selection_empty`
classait tout `best.len()==0` en `absent`. Corrections en place :

1. **`OpexC63NotePass`** : si `budgetConsidered > 0 && minCapital > available`, `unaffordable`
   et non `absent`.
2. **`OpexProjectsStampSelectionStats`** : `minCapital`, comptes rail/route/air/eau, cache,
   abandons et `emptyCause` sur les trois producteurs, y compris `OpexReselectProjects`.
3. **`OpexC63ClassifyAbsent`** : un compteur manquant n'est plus traité comme 0 (plus de
   `stage_empty` systématique). Repli sur `projects.rail` / `road` / `airPlans` / `waterPlans`.
4. **Sonde `OpexC63RecordEmptyProbe`** : via `_c63RecordPassAndProbe`, à la transition
   non-vide→vide (`lastKind` absent/unaffordable) ou 1×/mois. Journalise stage, cargo,
   comptes d'étape, `min_cap`, `avail_cap`, cache et abandons.
5. **`phase=opp_absent`** écrit les 9 causes, y compris `stage_empty`, `cache_exhausted`,
   `abandon_filtered`. Le parseur les lit. `absent_d` ≠ somme des causes devient un piège
   `absent_causes_do_not_sum` / `absent_causes_unlogged`.

Sortie attendue : **un tableau par mode, année et cohorte de lignes**, contenant :

- coût prévu, coût engagé, dépenses d'échec/rollback et capital immobilisé jusqu'au premier
  revenu ; couverture et montants non attribués explicités ;
- revenu/profit attendu contre profit observé à périmètre comparable, âge depuis la mise en
  service, rotations/remplissage lorsque mesurables ; distinguer résultat d'exploitation
  d'une ligne et résultat de compagnie, qui n'ont pas les mêmes charges ;
- nouvelles lignes et renforts, demande effectivement captée, partage de gares/bassins et
  présence concurrente ; un stock à quai est un symptôme, pas une preuve de revenu récupérable ;
- trésorerie **mobilisable selon `OpexAvailableCapital`** : caisse + emprunt effectivement
  accessible − réserve, face au besoin réel du projet ;
- sur les occasions où une décision peut être prise : candidat absent, invalide/site refusé,
  non finançable, demande/capacité insuffisante, en attente de calcul ou effectivement lancé.
  Rapporter séparément occurrences et **jours de jeu** ; aucune double attribution silencieuse.

**Deux corrections de méthode indispensables :**

- « Caisse ≥ 300 k£ et rien construit » ne prouve pas un manque de débit. Il faut un projet
  rentable, réalisable et finançable qui attend. Réciproquement, un surcoût modèle de 30 % ne
  prouve pas qu'une baisse du coût résoudrait le problème. Le bilan peut rester mixte ou inconclusif.
- C58 ne doit pas observer seulement `ET_VEHICLE_UNPROFITABLE` : cela sélectionne les perdants
  et rate les lignes positives qui rapportent bien moins que prévu. Comparer aussi des lignes
  profitables du même mode et du même âge. Pas de ferraillage automatique dans cet audit.

Les deltas de solde bancaire peuvent inclure revenus, entretien ou emprunts pendant un chantier :
ne pas les appeler coûts purs sans réconciliation. Deux smokes identiques sondes ON/OFF sont
un contrôle préliminaire, **pas une preuve de neutralité sur six ans**. Privilégier l'extraction
hors jeu ; si une instrumentation est nécessaire, mesurer sa perturbation et séparer son
résultat du banc économique final, exécuté sans instrumentation lourde.

**Décision à la sortie, avant tout autre diagnostic :**

| Fait observé sur des lignes/occasions identifiées | Suite autorisée par le diagnostic |
|---|---|
| Dépenses d'infrastructure/échecs immobilisant matériellement le capital | Un correctif de placement, réutilisation ou estimation sur le mode concerné ; pas de devis rail synchrone généralisé |
| Lignes positives mais recettes très inférieures au modèle | Corriger une hypothèse de demande, captage ou rotation ; C58/C59 |
| Demande non servie sur une infrastructure rentable ayant de la capacité | C61 ciblée, avec dépense et congestion observées |
| Projets valides finançables retardés pendant un coût de calcul identifié | C39/C41 ciblée |
| Pas de cause dominante ou données insuffisantes | Publier les limites et nommer la seule donnée manquante ; ne pas déclarer arbitrairement « capital » ou « CPU » |

**Fin de P1 (2026-09-13) :** hypothèse « capital » close. Hypothèse « modèle de revenu
air/route » close sur les témoins 1970–1971. L'attente A* n'est pas le reliquat 1971
(graine 42 mixte après correction du classifieur). La seule donnée manquante est
**pourquoi le portefeuille est vide** les jours `absent`, sans sonde qui déplace. Pas
de second levier.

<a id="c61"></a>
<a id="c59"></a>
## P2 — C61/C59 : mieux exploiter les lignes, si P1 le justifie

**Acquis causal C50b**, [banc consolidé](../results/bench_c50b_levers_10y_40seeds.json) :
supprimer la réserve de demande aérienne détruit de la valeur sur 20/20 graines ; relever le
plafond routier perd 27 paires sur 40 en valeur ; supprimer le cap de cadence aérien est
inconclusif à 21/40. Ajouter des véhicules n'est donc pas en soi le chantier prioritaire.

- **Air :** mesurer rotations, attente, demande et occupation aux deux aéroports avant de
  remplacer le partage égal de cadence entre lignes. `airportDelayDays = 3` et la table par
  type sont des modèles à qualifier, pas des capacités mesurées. Le modèle mutualisé proposé
  dans le dossier C61 reste un candidat, pas une spécification validée.
- **Route :** séparer fret, feeders et passagers interurbains. **`road_pax_build=0` au défaut** :
  une réforme visant les bus interurbains ne résoudra pas le duel courant. Le fret en chargement
  complet demande une mesure d'attente distincte du dwell passagers ; ne pas diviser par son
  `dwellDays=0`. La cible est du trafic rentable supplémentaire, pas le passage de 2 à 8 véhicules.
- **Rail :** la relaxation du seuil de backlog a déjà été inerte. C50b rapporte 39 `NOSPOT`
  pour 28 `OK` et 2 `TRACKFAIL` sur les références d'extension : inspecter les échecs de géométrie
  **si** les lignes concernées sont profitables et demandent réellement un second train.
  Cela ne justifie pas encore un chantier global de jonctions et gares partagées.
- **Ordres C59 :** corréler chargement, attente et profit avant une politique contextuelle.
  Retirer la prémisse « longue distance ⇒ full load mathématiquement supérieur » : attente,
  demande, prix du transport et congestion doivent entrer dans la comparaison. Une photographie
  de `cargo_count` ne mesure pas à elle seule le remplissage au départ ni une rotation.

<a id="c39"></a>
<a id="c41"></a>
<a id="c44"></a>
## P2 conditionnelle — C39/C41/C44 : traiter une occasion perdue, pas une lenteur abstraite

Les profils C39/C48 du 10 septembre montrent une augmentation du coût de génération avec
la maturité du réseau. Ils ne prouvent pas à eux seuls le gain d'une optimisation aujourd'hui.
Le [banc C48 final](../results/bench_c48_indexed_regeneration_10y_20seeds.json) donne
**10 victoires / 10 défaites en valeur**, +0,53 % en moyenne : gain économique non démontré,
`c48_indexed_regeneration=0` conservé. C46 reste également à 0 malgré un coût fret réduit en 1024².

Reste utile : critère de fraîcheur par couche, invalidation et recomputations évitables,
**sur le chemin où P1 aura montré des occasions finançables retardées**. Les modules actuels
sont `scheduler_tasks.nut`, `task_projects.nut`, `projects.nut` et `catalog.nut` ; les anciens
numéros de ligne de `main.nut` sont périmés après C65.

Ne pas relancer `portfolio_max_batch`/`portfolio_dynamic_batch`, un prix d'opcode ajouté au
score, ni un orchestrateur général sur la seule foi d'anciens profils. La fiche C39.5 est
close sur son levier testé ; « construit au premier tour » ne signifie cependant pas qu'un
intervalle entre tours est gratuit. Mesurer en jours, à âge de partie comparable, et vérifier
ce qui devient effectivement constructible. **Le titre catégorique de C44 (« ni capital ni
opcodes : le tour ») est retiré**, tout comme le « facteur 15 inexpliqué » déjà corrigé par C39.6.

## Autres tâches ouvertes, hors séquence prioritaire

Les travaux clos C45/C46/C47/C48/C49/C50/C51/C53/C54/C55/C56/C62/C65 et les étapes déjà
livrées des autres fiches sont consignés dans [le journal du jour](journal_2026-09-13.md).
Ne pas les remettre dans la file active sans fait nouveau.

| Fiche | Travail restant | Condition de reprise |
|---|---|---|
| C52 | Revalider les corrections crash/non rentable postérieures au banc ; exploiter la sonde de première arrivée si nécessaire | Défaut de service observé ; pas un objectif de nombre d'événements branchés |
| C60 | Exposition actuelle route/rail puis diagnostic 5×6 du filtre, encore à 0 après son smoke | Refus municipaux matériellement coûteux ; ne pas inférer cette exposition des seuls refus air, qui incluent le bruit |
| C57 | Calibrer les 50 000 opcodes de Lakes | Distribution des recherches eau et coût des paires perdues ; conserver la protection contre le gel |
| C43 / E3 | Constantes non tranchées : réserve, `loop_budget`, `pax_near`, seuils de mise au rebut | Constante impliquée par le diagnostic ; pas de balayage général |
| C45, reliquat | Décider de la persistance des compteurs de subventions | Besoin au rechargement ; secondaire pour des parties neuves |
| C42 bis | Filtrage/rendement des subventions | Exposition rentable démontrée ; les subventions brutes restent à 0 |
| C55, reliquat | Partage de demande et sur-service des bassins | Flux concurrents observés par P1 ; ne pas rouvrir le filtre d'origine |

## Eau, bibliothèques et robustesse — conservés, différés

Le code utilise déjà la transcription MinchinWeb dans `lib_water.nut`, avec budget en opcodes.
Ne pas proposer de recommencer son intégration. La bibliothèque n'apporte pas à elle seule des
lignes rentables ; le catalogue de sites intégré aux rebuilds a été testé sans justifier son adoption.
L'ancien essai Lakes du 09/09 précède le correctif de gel C56 : il ne tranche pas à lui seul
le défaut combiné actuel. Aucune modification de défaut eau n'est décidée par cette revue.

Le dossier eau conserve : découverte de sites séparée du portefeuille, distance navigable au
lieu du minorant Manhattan, revalidation des fronts réels sans réintroduire le faux négatif du
BFS borné, rotations fractionnaires et qualification mémoire sur grandes cartes. **Réexaminer
ces points dans le code au moment de la reprise**. Leur poids dans le retard courant n'est pas
mesuré ; un gel reproductible reprendrait immédiatement la priorité. C57 conserve le calibrage
du budget, pas un retour au budget en itérations. La consigne existante d'accord explicite avant
un nouveau diagnostic de découverte maritime est conservée ; aucun n'est lancé ici.

Les autres sujets restent disponibles : catchment réel des gares, placement/bruit d'aéroport,
jonctions/agrandissement de gare, `station_join`, coût A*, réglages de partie avec mode désactivé,
RAM Squirrel et automatisation GitHub. Ils remontent sur un besoin démontré, pas parce qu'une
bibliothèque propose une fonction. Le temps de trajet rail reste hors périmètre de SuperLib
(cf. C41 et `AGENTS.md`). `origin_sitable` et `complex_cargo` conservent leurs défauts ; ne pas
présenter leur conservation comme un nouveau gain mesuré.

## Règles pour la prochaine expérience

- **Une hypothèse, une intervention, une décision attendue.** Écrire le coût d'essai et le critère
  d'arrêt avant de coder. Ne pas prolonger un résultat nul en explorant des seuils jusqu'à gagner.
- Smoke 1×1, diagnostic physique **5×6**, puis **20×10 apparié avant adoption**. Pour revendiquer
  un rattrapage, le banc doit comparer les deux politiques OpexAI **face au même AAAHogEx**.
  Le 20×5 actuel est une référence descriptive, pas une exception à la règle d'adoption.
- Pré-enregistrer la métrique économique primaire, l'effet minimal utile et les garde-fous
  sur l'autre métrique économique, les échecs et le service. Publier les deltas par graine,
  moyenne et médiane appariées, incertitude et V/D/égalités. Exclure les égalités du test des
  signes ; un résultat non significatif n'est ni une preuve d'équivalence ni une adoption.
- Garder les graines d'échec dans les résultats avec leur statut. Distinguer validation d'un
  correctif fonctionnel, maintien d'un défaut et démonstration d'un gain économique.
- Exploiter les résultats déjà présents avant de lancer une campagne. Après verdict, remplacer
  la fiche active par sa décision et archiver le détail : ne pas empiler les conclusions opposées.
- Docker : toujours `--cpus=3 --memory=2g --memory-swap=2g`, cache
  `-v openttd-lab-home:/home/lab`, source montée dans `/work`. Une seule campagne consommatrice
  à la fois sur le VPS ; ces limites par conteneur ne bornent pas leur consommation cumulée.

**Portée de cette revue :** lecture du code courant et des archives, recomptage hors ligne des
JSON récents, réorganisation documentaire. Aucun changement de comportement IA, aucun défaut
modifié, aucun nouveau banc lancé. L'[architecture après C65](architecture_opexai.md) donne les
nouveaux emplacements des fonctions.
