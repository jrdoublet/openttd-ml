# Étape 17 — Harnais — duel 1v1 et contrôle de santé

- **SHA revu** : `421f14d`
- **Modèle / effort prévus** : Opus 5 / xhigh
- **Périmètre** : `sweeps/bench_1v1_5y_20seeds.py`, `game_health.py`, `smoke_test.py` — 2 238 l.
- **Plan** : `docs/revue_code_2026-09-15_plan.md`

**Enjeu annoncé**

Comptage `VEHS` non qualifié (composants non filtrés) ; 4 faux positifs de santé rouverts le
09-14 ; `expected_last_year` non renseigné. Toute conclusion économique du projet passe par là.

**Rappel de méthode** — diagnostic seulement, rien n'est corrigé au passage. Vérifier à la main,
pas par grep seul. Vérifier le défaut d'un réglage avant de le qualifier de code mort. Ancrer
chaque constat sur `fichier:ligne`. Ne lire que `ai/OpexAI/CLAUDE.md` et les fichiers du
périmètre : pas `docs/taches.md` en entier, pas les journaux, pas `results/`.

**État de l'énoncé du plan à la relecture** — trois des cinq points annoncés sont fermés dans le
code actuel (voir « Vérifié, n'est PAS un bug ») : `expected_last_year` **est** renseigné, la
sortie du moteur **est** transmise au contrôle d'échec, et 3 des 4 faux positifs de santé sont
traités. Le comptage `VEHS` est bien le défaut décrit, mais pas là où le plan le situe : le
filtrage existe (`physical_counters.decode_vehicles`) et est appelé — c'est la **clé retenue**
dans le dossier de sortie qui est la mauvaise. Deux défauts non annoncés, plus graves que
plusieurs des points listés, sont apparus à la lecture (17.2, 17.3).

**Chiffres de référence utilisés ci-dessous** — obtenus en exécutant `decode_vehicles` sur la
fixture de contrôle officielle `sweeps/fixtures/c66_control_fixture_15_3.json` (celle-là même
qu'utilise le selftest), pas sur un raisonnement : 33 entrées `VEHS` au total, dont 7 véhicules
d'effet (type 4) ; propriétaire 0 → **26 entrées de pool, 21 véhicules pilotables**, l'écart étant
2 wagons de rail et 3 ombres/rotors d'avion.

---

## Constats

### 17.1 — `n_vehicles` publie les entrées de pool, pas les véhicules        [gravité : P1]
`sweeps/bench_1v1_5y_20seeds.py:264` — `"n_vehicles": veh_dec["vehicle_pool_entries"]` retient le
compteur **brut** du pool pour le propriétaire (têtes + wagons + ombres + rotors + parties
articulées), alors que le décodeur rend au même endroit `primary_vehicles_count`, filtré
(`physical_counters.py:234-257`). La ligne 265 recopie la même valeur sous son vrai nom
`vehicle_pool_entries` : les deux clés sont donc numériquement identiques, l'une correctement
nommée, l'autre pas · la docstring du module (`:7`) annonce « les métriques standard (…)
`n_vehicles` » comme une métrique de banc, et le tableau imprimé l'intitule « Véhicules »
(`:1040`) · sur la fixture de contrôle, `n_vehicles` vaut **26 pour 21 véhicules réels (+23,8 %)**,
et le selftest **fige** cet écart en l'attendant explicitement (`:1137` `assert rec0["n_vehicles"]
== 26` face à `:1138` `assert rec0["primary_vehicles"] == 21`). La surestimation n'est pas un
décalage constant : elle vaut 0 % pour une flotte routière pure (17 véhicules routiers, 0
composant dans la fixture), +100 % pour un avion (1 ombre par appareil), +200 % pour un
hélicoptère, et +N par convoi ferroviaire de N wagons. Elle est donc **fonction de la composition
de flotte**, c'est-à-dire de l'arm : la valeur affichée par `:1057` et la moyenne par arm de
`:1082-1089` comparent deux dénominateurs incomparables. Tout rapport « profit par véhicule »,
« valeur par véhicule » ou « rendement par véhicule » dérivé de ce champ — dont le « 93 % de
rendement par véhicule, donc presque uniquement du volume » et le « 564 véhicules contre 102 »
cité par `ai/OpexAI/CLAUDE.md:17-20` — est biaisé dans le sens qui gonfle le plus l'arm à longs
convois ferroviaires et à aéronefs, donc mécaniquement en faveur d'OpexAI si AAAHogEx roule plus
au train. Le champ est ensuite propagé tel quel par `bench_v2.py:483` dans `summary[]`, donc dans
le JSON de campagne que lisent tous les diagnostics en aval.

### 17.2 — Le verdict C66.4 se décide à la moyenne ; le test des signes est calculé puis ignoré        [gravité : P1]
`sweeps/bench_1v1_5y_20seeds.py:708-715` — `primary_pass` vaut `primary_stats["mean"] >=
min_useful_primary_delta` et `guard_pass` un seuil sur un ratio de moyennes ; le verdict
`pass`/`fail_*` (`:716-725`) n'utilise rien d'autre · le bloc `decision_rule` publié dans le
rapport (`:733-739`) annonce `"primary_rule": "mean(variant-reference) >=
min_useful_primary_delta"`, et `delta_statistics` calcule pourtant `wins`, `losses`, `ties`,
`sign_test_n_excluding_ties` et `sign_test_p` (`:445-447`, `:467-468`), correctement, ex æquo
exclus · conséquence : la règle d'adoption du projet — « banc officiel 20 graines × 10 ans
apparié, lu au **test des signes d'abord** (≥ 15/20, p < 0,05), moyennes ensuite »
(`ai/OpexAI/CLAUDE.md:97-100`) — n'est appliquée **nulle part dans le code qui rend le verdict**.
Une seule graine à fort delta peut porter la moyenne au-dessus du seuil pendant que le bilan est
10 victoires / 10 défaites ; le rapport imprimera alors `verdict=pass` avec `p_signes=1.0` sur la
même ligne (`:1110-1113`). C'est le protocole « fail-closed » C66.4 qui décide de l'adoption d'une
variante : il est plus permissif que la méthode écrite.

### 17.3 — Aucune garde de complétude du lot sur le chemin C66.3 (le banc de référence)        [gravité : P1]
`sweeps/bench_1v1_5y_20seeds.py:893-958` — `by_game` est construit **uniquement à partir des
lignes revenues** de `run_experiments`, puis `summary`, `games` et `failed` en dérivent ; rien ne
compare `len(by_game)` à `len(exps)` (le plan de parties validé en `:870`), ni `len(summary)` à
`2 × len(exps)` · le rapport annonce pourtant `"seeds": args.seeds` et `"repeats"` (`:994-995`) et
`enforce_validation_outcome` (`:753-758`) prétend terminer en erreur sur tout banc invalide · une
partie qui ne rend aucune ligne (worker qui ne remonte rien, résultat vide après une exception non
couverte par `capture_engine_failure`) disparaît **silencieusement** : `arm_statistics` et
`paired_comparisons` moyennent sur 19 graines au lieu de 20, `failed_runs` reste vide, le code de
sortie est 0, et le JSON ne contient aucun champ qui contredise l'en-tête « 20 graines ». La garde
existe pourtant, mais seulement pour le chemin à deux politiques (`:700-705`,
`comparison_complete = len(complete_pairs) == planned`) : le banc de référence 20×5 — celui qui a
produit le 0/20 cité par `CLAUDE.md:15-17` — est justement le seul à en être dépourvu.

### 17.4 — Le compteur corrigé est écrit puis jamais lu        [gravité : P2]
`sweeps/bench_1v1_5y_20seeds.py:266-267` — `primary_vehicles` et `primary_vehicles_by_mode` sont
enregistrés par compagnie et par checkpoint, et repris dans `summary[]` par `bench_v2.py:500-501`
· c'est la contrepartie annoncée de 17.1, la donnée qui permettrait de corriger toute lecture
économique · hors selftest (`:1138`, `:1147`, `:1168-1172`, `:1208-1209`), **aucune** occurrence
n'existe dans le fichier : pas d'impression, pas de moyenne, pas de comparaison appariée. Ils ne
sont pas dans `SUCCESS_METRICS` (`bench_v2.py:68-74`), donc ni `arm_statistics` ni
`paired_comparisons` ni `build_policy_comparison` (`:596`, `:676`) ne les touchent. Seul
`game_health.activity_from_series` les consulte (`game_health.py:369-370`), et uniquement pour un
signal booléen d'activité. Le seul agrégat de flotte publié par le banc est donc celui de 17.1.

### 17.5 — La garde de valeur C66.4 se calcule sur un sous-ensemble non déclaré au verdict        [gravité : P2]
`sweeps/bench_1v1_5y_20seeds.py:472-498` et `:707` — `ratio_statistics` écarte, à raison, toute
paire dont le dénominateur (`company_value` de référence) est nul ou négatif, et compte les
exclusions dans `excluded_nonpositive_or_missing_denominator` · le champ est publié mais
**n'entre dans aucune décision** : `guard_ratio` est lu tel quel en `:707` et
`comparison_complete` (`:705`) ne contrôle que la présence et la santé des paires, pas la
validité du dénominateur · conséquence : si 19 des 20 graines terminent avec une valeur de
compagnie de référence ≤ 0 (faillite, ce que le module traite explicitement comme une issue
économique valide, `game_health.py:59`), la garde `value_guard_pass` est tranchée sur **une seule
graine** et le verdict affiche `pass` avec `comparison_complete=True`. Même mécanisme que 17.2 :
le protocole se déclare fail-closed sur la complétude des parties, pas sur celle des statistiques
qu'il en tire.

### 17.6 — `stagnation_suspect` est inatteignable dès qu'une compagnie a un véhicule ou un emprunt        [gravité : P2]
`sweeps/game_health.py:486-492` — le statut `stagnation_suspect` exige
`activity["signal"] == "no_signal"` · `activity_from_series` (`:390-395`) ne rend `no_signal` que
si, en plus de l'absence de tout changement de flotte et de réseau, **`company_value` n'a pas
bougé** sur les 3 derniers pas (`ACTIVITY_RECENT_STEPS = 3`, `:60`) ; sinon elle rend
`earning_without_expansion`, qui laisse le statut à `complete` · or `company_value` intègre la
trésorerie, l'emprunt et la dépréciation : une compagnie qui possède un seul véhicule en service,
ou simplement un emprunt qui court, voit sa valeur changer à chaque checkpoint mensuel. Le signal
`no_signal` n'est donc atteignable que par une compagnie strictement vide. Conséquence directe :
une partie C56 (« l'IA cesse toute activité après 1970 sans erreur NoAI »,
`ai/OpexAI/CLAUDE.md:142-143`) est classée `complete`, `run_ok=True`, `game_ok=True`, et **entre
dans les moyennes du banc** comme une partie saine. Le nom `earning_without_expansion` est de
surcroît trompeur : `value_changes` (`:381-383`) compte toute variation, y compris une valeur qui
**s'effondre** — une compagnie en train de mourir est déclarée « active économiquement ». C'est le
quatrième faux positif rouvert le 09-14 ; il est toujours ouvert.

### 17.7 — Un adversaire chargé mais inerte est réputé sain        [gravité : P2]
`sweeps/game_health.py:453-493` — `classify_company` couvre l'absence de compagnie, le doublon de
checkpoint, l'erreur NoAI attribuée, l'horizon tronqué et la faillite, mais n'impose **aucun
plancher d'activité** : aucune condition sur `primary_vehicles > 0`, `n_stations > 0` ou
`company_value > 1` · le module annonce « distingue moteur/timeout, données manquantes, NoAI
attribué, faillite, fin complète et suspicion de stagnation » (`:11-12`) et le harnais de smoke
test, lui, connaît ce plancher (`smoke_test.py:48-59`) · conséquence, pour le point 5 de la revue :
un AAAHogEx qui **plante** est bien détecté (journal moteur attribué, cf. « Vérifié »), et un
AAAHogEx qui **ne crée pas de compagnie** l'est aussi (`:461-465`) ; mais un AAAHogEx qui se
charge, crée sa compagnie et ne joue pas — le mode d'échec le plus proche de C56, et le seul
silencieux — produit un duel `game_ok=True` où OpexAI « gagne » contre un adversaire à l'arrêt.
Combiné à 17.6, aucun garde-fou du fichier ne rattrape ce cas. Le banc étant l'arbitre externe de
toute décision du projet (`ai/OpexAI/CLAUDE.md:8-13`), c'est la garantie d'arbitrage elle-même qui
manque de son côté adverse.

### 17.8 — Rien ne contrôle le nombre ni la continuité des checkpoints mensuels        [gravité : P2]
`sweeps/game_health.py:313-335` — `inspect_checkpoints` ne vérifie que deux choses : les doublons
`(compagnie, date)` et les compagnies absentes du lot · la docstring du module annonce « contrôle
compagnies attendues, doublons de checkpoints et horizon réel (janvier de la dernière année ne
prouve pas l'année) » (`:9-11`), et `expected_last_checkpoint` (`:68-76`) verrouille effectivement
la **dernière** date · rien ne vérifie qu'il y a bien ~60 checkpoints mensuels entre la première et
la dernière : une partie dont 48 sauvegardes sur 60 manquent, mais qui atteint 1974-12-01, passe
`complete`. `bench_v2.summarise` calcule pourtant `n_savegames` (`bench_v2.py:485`) — jamais
comparé à quoi que ce soit. Deux conséquences : la trajectoire annuelle de `_annual_final_records`
(`bench_1v1_5y_20seeds.py:501-518`) peut reposer sur un seul point par année sans le signaler, et
la fenêtre de récence d'activité (`ACTIVITY_RECENT_STEPS = 3`, comptée **en checkpoints** et non en
mois, `game_health.py:385-389`) devient silencieusement une fenêtre de plusieurs années.

### 17.9 — `assess_game` est fail-ouvert quand aucun journal moteur n'est fourni        [gravité : P2]
`sweeps/game_health.py:524-534` — si `engine_log_path` est `None`, `engine_log` reste `None`,
`parse_script_errors` s'exécute sur `""` et la garde `missing_engine_log` de `:533` est
inopérante puisqu'elle exige `engine_log_path` vrai · le module promet d'attribuer les erreurs
NoAI et de ne jamais les imputer au joueur 0 par défaut (`:3-8`) · conséquence : une partie sans
journal ne rend **aucune** erreur, ni attribuée ni non attribuée, et ressort `game_ok=True`. Le
chemin d'appel qui y mène est réel : `bench_1v1_5y_20seeds.py:291-294` ne calcule un chemin que si
`ENGINE_LOG_DIR is not None`, et cette globale vaut `None` au chargement du module (`:62`) ; en
`:912`, `log_path` est le premier `engine_log_path` non nul trouvé dans les lignes, sinon `None`.
`main()` la renseigne toujours (`:856`, depuis `campaign_freeze.FrozenCampaign.engine_log_dir`),
donc l'exposition est aujourd'hui latente ; elle devient active pour tout appelant de `keep()` ou
`assess_game()` hors `main` (le selftest doit d'ailleurs la poser à la main, `:1193`).

### 17.10 — Le plancher « au moins 1 véhicule » du smoke test est satisfait par la fumée        [gravité : P2]
`sweeps/smoke_test.py:55-56` — `if (record.get("n_vehicles") or 0) < 1` · la docstring annonce
« au moins 1 vehicule (n_vehicles >= 1) » comme plancher de plausibilité (`:8`) · mais ce
`n_vehicles`-là ne vient pas de `extract_company_record` : `smoke_test` importe `keep` de
`bench_v2` (`:29`, passé en `result_processor` en `:79`), et `bench_v2.keep:361` pose
`"n_vehicles": len(chunks.get("VEHS", {}))` — la **taille entière du chunk**, tous propriétaires
confondus, véhicules d'effet et catastrophes compris. Sur la fixture de contrôle, cela vaut 33
pour 21 véhicules réels (+57 %), dont 7 entrées de type 4 (effets : fumées d'usine, étincelles)
qui n'appartiennent à personne et existent sur la carte sans aucune compagnie. Le plancher est
donc franchi même si l'IA n'a construit **aucun** véhicule — exactement le cas que la porte de PR
prétend interdire. Le plancher `n_stations >= 1` (`:53-54`) souffre du même défaut d'origine mais
`len(STNN)` reste borné par les gares réellement construites, donc lui reste indicatif.

### 17.11 — Le smoke test ne vérifie jamais l'horizon        [gravité : P2]
`sweeps/smoke_test.py:87` — `summary = summarise(rows)` est appelé **sans**
`expected_last_year` · `bench_v2.summarise:450-457` ne produit `incomplete_run: last autosave year
… < expected …` que si ce paramètre est fourni, et le banc 1v1 le fournit bien
(`bench_1v1_5y_20seeds.py:891`, `:919`) · conséquence : une partie de smoke test arrêtée au bout de
3 mois — IA figée, moteur qui rend la main tôt — sort `run_ok=True` dès lors que les trois
planchers de `verify_plausibility` sont franchis, ce qui est le cas avec une seule gare et une
valeur de compagnie de départ. La porte de PR laisse passer un gel précoce, qui est justement le
mode d'échec C56. C'est la seule occurrence restante du point « `expected_last_year` n'est pas
renseigné » de l'énoncé.

### 17.12 — Le smoke test n'a ni timeout ni capture de crash moteur        [gravité : P2]
`sweeps/smoke_test.py:69` — seul `enable_savegame_cleanup()` est posé ;
`enable_engine_failure_capture` n'est ni importé ni appelé · la docstring vend « Porte de PR
rapide (~2-5 min) » (`:3`) et « Aucun crash / erreur fatale NoAI » (`:6`) · or c'est
`game_health.enable_engine_failure_capture` (`game_health.py:196-204`) qui pose l'unique
`timeout` du dépôt sur `subprocess.check_output` (`DEFAULT_ENGINE_TIMEOUT_SEC = 1800`) : sans lui,
un OpenTTD qui se bloque fait **pendre la CI indéfiniment**, sans rapport ni message. Et un crash
moteur remonte en `CalledProcessError` non rattrapée, donc en trace Python : `write_json_atomically`
(`:115`) n'est jamais atteint, aucun `results/smoke_ci.json` n'est écrit, et la distinction entre
« crash moteur » et « bug du harnais » est perdue pour qui lit le log de CI.

### 17.13 — Le smoke test embarque le stdout moteur complet dans son rapport        [gravité : P3]
`sweeps/smoke_test.py:107-115` — `payload["summary"] = summary` est sérialisé tel quel ·
`bench_v2.summarise:486` conserve `"openttd_output": final["openttd_output"]`, soit l'intégralité
du stdout d'OpenTTD pour chaque partie · le banc 1v1 prend explicitement soin de le retirer avant
écriture (`bench_1v1_5y_20seeds.py:956-957`, et `annotate_summary` le supprime aussi,
`game_health.py:637`), pas le smoke test · conséquence : `results/smoke_ci.json` grossit du volume
de trois journaux moteur complets à chaque exécution de la porte de PR, avec `debug_signs = 1` par
défaut (`ai/OpexAI/CLAUDE.md:130-131`).

### 17.14 — Code mort dans le banc, dont le contrôle de stabilité d'identité de campagne        [gravité : P3]
`sweeps/bench_1v1_5y_20seeds.py:127-149` — `vehicle_owner` et `station_owner` ne sont appelés nulle
part (leur rôle est tenu par `physical_counters.decode_vehicles` / `decode_stations`, appelés en
`:238-239`) · `:399-424` — `attach_campaign_identity` non plus · la docstring de cette dernière
annonce « Propage l'identite C66.3 que bench_v2.summarise ne connait pas » et, surtout, lève
`ValueError` sur une identité de campagne **instable** entre deux lignes d'une même partie
(`:414-416`) et sur une identité absente (`:421-422`) · `main()` refait l'affectation à la main en
`:922-930` mais sans ces deux contrôles : la seule vérification d'identité qui subsiste est
l'unicité du `policy_id` par partie (`:908-911`). Le décalage entre les deux implémentations est
exactement le genre d'écart qui rend un code mort dangereux : on croit le contrôle posé.

### 17.15 — Une compagnie disparue mais en faillite entre dans les moyennes avec `company_value = 0`        [gravité : P3]
`sweeps/bench_1v1_5y_20seeds.py:235-247` — quand `PLYR` ne contient plus le propriétaire,
`last_closed` vaut `{}` et `company_value` est forcé à `0` par le défaut de `.get`, tandis que
`profit_year` vaut `None` (`year_profit([])`, `bench_v2.py:304-310`) · `game_health.py:436-446`
qualifie ce cas de `bankrupt` dès qu'un checkpoint antérieur porte `months_of_bankruptcy > 0`, et
la faillite est une issue économique conservée dans les moyennes par choix explicite
(`game_health.py:13`, `:59`) · conséquence : pour la même partie, la moyenne de `company_value`
intègre un 0 alors que celle de `profit_year` écarte la ligne (les `None` sont filtrés par
`bench_v2.dispersion`). Les deux métriques du même tableau sont calculées sur des effectifs
différents sans que le rapport l'indique.

### 17.16 — Le timeout moteur s'applique à tous les `check_output` d'OpenTTDLab        [gravité : P3]
`sweeps/game_health.py:196-204` — le patch remplace `openttdlab.subprocess.check_output`, c'est-à-
dire l'attribut du **module `subprocess` lui-même**, et pose `timeout` par défaut sur tout appel ·
la docstring annonce « Intercepte un crash/timeout d'OpenTTD dans le worker » (`:187`) · or
OpenTTDLab utilise aussi `check_output` hors partie (récupération du binaire OpenTTD 15.3 et
d'OpenGFX 7.1) : un téléchargement lent dépassant 1 800 s est tué et remonté par
`capture_engine_failure` (`:131-152`) comme `engine_failure = {"kind": "timeout"}`, donc requalifié
en `engine_error` d'une partie (`:110-111`). Un incident réseau devient un échec de santé de banc.

### 17.17 — Le journal moteur est réécrit intégralement à chaque checkpoint mensuel        [gravité : P3]
`sweeps/bench_1v1_5y_20seeds.py:291-294` — `keep()` est appelé une fois par sauvegarde (cadence
mensuelle) et appelle `write_engine_log` à chaque fois · la docstring de la fonction annonce
« Écrit le stdout du moteur une seule fois par partie » (`game_health.py:210`) — c'est vrai du
*chemin* (un fichier par partie, le point dur de C66.2, cf. « Vérifié »), pas du *nombre
d'écritures* · conséquence : ~60 réécritures complètes du stdout par partie et par exécution, soit
1 200 pour un banc de 20 graines, chacune avec `mkdir(parents=True)` (`game_health.py:212`).

### 17.18 — Le smoke test ne fait pas ce que la convention du projet prescrit        [gravité : P3]
`sweeps/smoke_test.py:32-33` — `DEFAULT_SEEDS = (42, 100, 7)` et `DEFAULT_YEARS = 2`, cohérents
avec la docstring « 3 graines x 2 ans » (`:3`) · `ai/OpexAI/CLAUDE.md:101-103` prescrit
« smoke test (2 graines × 3 ans) **avant** commit » · conséquence : la durée par graine est plus
courte d'un tiers que la convention écrite, or c'est la deuxième année qui fait apparaître le cycle
de rapport annuel et le ferraillage. Un des deux documents doit être corrigé ; à lire à l'étape 20
plutôt qu'ici, la question étant de savoir laquelle des deux valeurs a été mesurée.

## Vérifié, n'est PAS un bug

- **Faux positif #1 — `annotate_summary` ne réhabilite plus un `run_ok=False`.**
  `game_health.py:614` : `run_ok = preexisting_ok and bool(health_ok)`, conjonction stricte ; le
  motif d'échec préexistant est conservé et concaténé au motif de santé (`:616-618`), et
  `include_in_economic_stats` (`:635`) exige en plus un statut économique. `game_ok` est recalculé
  en aval sur les lignes annotées et non repris de l'évaluation (`:640-649`), et
  `reconcile_assessment` réaligne l'évaluation de partie sur ce fail-closed (`:656-676`). Le
  selftest couvre le cas mixte (`bench_1v1_5y_20seeds.py:1181-1186`). **Fermé.**
- **Faux positif #2 — crash et timeout moteur ne sont plus perdus.** Chaîne complète et vérifiée :
  `wrap_engine_failure_capture` (`game_health.py:162-183`) rattrape `CalledProcessError` et
  `TimeoutExpired` dans le worker, `capture_engine_failure` (`:131-152`) fabrique une ligne
  `keep()` portant `engine_failure` et la sortie partielle, `keep` la recopie sur les deux
  compagnies (`bench_1v1_5y_20seeds.py:317-318`), `engine_failure_from_records` (`:103-116`) la
  relit et `assess_game` la fait primer sur le marqueur de journal (`:530-532`). L'ordre imposé
  (capture **avant** nettoyage) est respecté en `:859-860`, et la préservation de signature
  nécessaire au nettoyage (`_preserve_signature`, `:155-159`) est testée
  (`bench_1v1_5y_20seeds.py:1276-1279`). Le couplage à l'API privée `openttdlab._run_experiment`
  est assumé et borné par le gel de version (`requirements.txt` : `OpenTTDLab==0.0.75`). **Fermé.**
- **Faux positif #3 — compagnie disparue au dernier checkpoint.** `classify_company:433` lit
  `company_present` du dernier checkpoint, `:461-465` la classe `missing_data` si elle a disparu
  sans faillite préalable, et `:439-446` remonte la série pour ne pas confondre disparition et
  faillite. `extract_company_record` alimente bien ce drapeau (`bench_1v1_5y_20seeds.py:233`), et
  le selftest le vérifie (`:1238-1239`). Couvre au passage le mode d'échec silencieux « l'IA ne se
  charge pas, aucune compagnie n'est créée » documenté dans `bench_v2.arm_notes`. **Fermé.**
- **`expected_last_year` est renseigné.** `bench_1v1_5y_20seeds.py:891` puis `:919`
  (`summarise(recs, expected_last_year=last_year)`), et publié dans le rapport (`:1011`). Il est
  même doublé par un contrôle **plus strict** que celui de `bench_v2` : `expected_last_checkpoint`
  (`game_health.py:68-76`) exige le 1er décembre de la dernière année, la docstring expliquant
  précisément pourquoi l'année seule accepterait à tort un 1974-01-01. Le point de l'énoncé ne
  vaut plus que pour `smoke_test` (17.11). **Fermé pour le banc 1v1.**
- **La sortie du moteur est transmise au contrôle d'échec, et l'attribution est correcte.**
  `keep` écrit le stdout dans un journal unique par partie (`:291-294`), `assess_game` le relit
  (`game_health.py:524-528`), `parse_script_errors` (`:246-303`) n'attribue une erreur que si
  `[script:N] [C]` concorde avec `DUEL_SLOT_MAP` (`:37-40`) et laisse `unattributed` — jamais
  joueur 0 — dans tous les autres cas, y compris quand l'identifiant de compagnie contredit la
  place. Une erreur non attribuée met **les deux** compagnies en échec (`:475-477`) et interdit
  `game_ok` (`:569-576`). Le format attendu est bien celui des journaux réels : la fixture
  `sweeps/fixtures/c66_health/opex_error.log` est un extrait authentique
  (`[script:0] [0] [S] Your script made an error…` + CALLSTACK). Le selftest exerce le cas
  AAAHogEx de bout en bout et vérifie que l'erreur n'est pas imputée à OpexAI
  (`bench_1v1_5y_20seeds.py:1188-1236`). `openttd_output` forcé à `None` dans les enregistrements
  de duel (`:277`) n'est donc pas une perte mais le remplacement voulu (une copie du journal par
  compagnie et par mois était le défaut d'origine de C66.2) — sous réserve de 17.9. **Fermé pour
  le crash ; reste 17.7 pour l'adversaire inerte.**
- **Le test des signes exclut les ex æquo.** `delta_statistics:445-447` sépare `wins`, `losses`,
  `ties` et n'alimente `exact_sign_test_p` (`:431-438`, binomial exact bilatéral) qu'avec les deux
  premiers, `sign_test_n_excluding_ties` étant publié à part. Conforme à
  `ai/OpexAI/CLAUDE.md:99-100` (« deux bras identiques signifient “le drapeau n'a pas joué”, pas
  une victoire »). Le défaut n'est pas dans le calcul mais dans son non-usage (17.2).
- **Rapport de moyennes et moyenne des rapports sont distingués.** `ratio_statistics:472-498`
  publie les deux et exige un dénominateur strictement positif. C'est la bonne pratique ; le
  défaut est ailleurs (17.5).
- **L'appariement C66.4 est réellement contrôlé.** `validate_paired_experiments:362-396` vérifie
  l'unicité de la paire, l'égalité stricte de tous les invariants (graine, durée, configuration,
  identifiant de campagne, empreinte du bundle), l'unicité du `game_id`, et — contrôle rare et
  juste — que l'adversaire est **le même objet descripteur gelé** (`:395-396`), pas seulement un
  descripteur équivalent. Testé (`:1399-1416`).
- **Le bras de référence sans réglages explicites n'est pas le constat G0.** `:339-341` construit
  la référence avec `explicit_settings = ()`, mais les deux politiques jouent sur le **même arbre
  `ai/OpexAI` gelé et empreint** (`prepare_frozen_campaign`, `:833-853`), et
  `validate_policy_settings` refuse toute différence de réglage non annoncée en
  `intervention_settings` (testé `:1286-1301`, y compris le refus). L'héritage des défauts est
  donc identique et tracé des deux côtés.
- **Le fail-closed du décodage physique est strict par choix.** Une seule entrée `VEHS` non
  classée rend `chunk_valid=False` (`physical_counters.py:391-394`), ce qui met `n_vehicles` à
  `None` (`bench_1v1_5y_20seeds.py:260-264`), déclenche `physical_decode_failure`
  (`bench_v2.py:459-468`), donc `run_ok=False`, donc `SystemExit` du banc entier
  (`:753-758`). C'est brutal mais c'est la propriété voulue : aucun mois partiellement décodé
  n'entre dans une moyenne. Le selftest le vérifie (`:1141-1159`).
- **Le rapport est écrit avant l'échec de validation.** `write_json_atomically` en `:1034`,
  `enforce_validation_outcome` en `:1123` : un banc invalide laisse quand même son JSON pour
  diagnostic (C66.5, testé `:1418-1430`).
- **`airport_slot_metrics` compte bien une ressource rare, pas des gares.** `:152-198` filtre sur
  le bit `facilities & 8` et agrège par `TownID`, pas par gare ; une gare routière n'y entre pas
  (testé `:1244-1264`).
- **`days = 365 * years` ne casse pas l'horizon.** Le décalage cumulé des années bissextiles
  (2 jours sur 5 ans) déplace la fin de partie au 30 décembre, ce qui laisse intact le checkpoint
  du 1er décembre exigé par `expected_last_checkpoint`.

## Hors périmètre, à relire ailleurs

- **`vehicle_breakdown` et `physical_telemetry` ne sont pas dans le périmètre de l'étape 17** et
  ne portent **pas** le défaut que leur prête l'énoncé du plan. Les versions vivantes délèguent à
  `physical_counters.decode_vehicles` et n'exposent que des têtes de convoi :
  `sweeps/diag_1v1_shared_monthly.py:97-140` (→ **étape 19**) et
  `sweeps/bench_c50b_physical.py:28-73` (aucune étape). Les copies antérieures
  (`bench_1v1_5y_5seeds.py:40`, `bench_1v1_3y_10seeds.py:40`, `bench_feeders_y1.py:22`,
  `bench_fullload_feeders_y1.py:26`) filtrent sur `unitnumber`, ce qui écarte déjà wagons, ombres
  et rotors : ce sont des archives d'expérience, hors plan, à laisser tomber. **Le seul endroit où
  le compte non filtré sort vraiment est la clé `n_vehicles`** (17.1, et son origine
  `bench_v2.keep`).
- **`bench_v2.py:361`** — `"n_vehicles": len(chunks.get("VEHS", {}))` : le compte le plus faux du
  dépôt (pool entier, tous propriétaires, effets et catastrophes compris), racine de 17.10 et
  utilisé par tous les bancs mono-arm. → **étape 18**.
- **`bench_v2.py:433-510`** — `summarise` est le point de passage de 17.1, 17.4, 17.11 et 17.13
  (conservation d'`openttd_output`, propagation de `n_vehicles`, absence de contrôle sur
  `n_savegames`). → **étape 18**.
- **`profit_year` au dernier checkpoint** — `bench_v2.py:304-310` somme les 4 derniers trimestres
  **clos** ; au checkpoint du 1er décembre de la dernière année, cela couvre Q4 de l'année n−1 à
  Q3 de l'année n, pas l'année civile finale. La métrique primaire du duel
  (`bench_1v1_5y_20seeds.py:65`) hérite de ce décalage d'un trimestre. → **étape 18**.
- **`sweeps/physical_counters.py` (546 l.) et `sweeps/campaign_freeze.py` (545 l.) ne sont
  couverts par AUCUNE étape du plan**, alors que tout le périmètre 17 en dépend : le filtrage
  têtes/composants de 17.1 et 17.4, la validité fail-closed de chaque mois, le gel de campagne,
  l'unicité de `engine_log_dir` (17.9) et `validate_policy_settings` y vivent. Ils sont pourtant
  déclarés fichiers de harnais de la campagne
  (`bench_1v1_5y_20seeds.py:89-100`, `CAMPAIGN_HARNESS_FILES`). Deux points appelleraient une
  relecture dédiée : les règles de qualification têtes/composants de
  `physical_counters.py:226-257` (jamais vérifiées contre `src/vehicle_base.h` d'OpenTTD 15.3 par
  cette revue) et `QUALIFIED_MODES["water"] = False` (`:50`), qui déclare le mode eau non qualifié
  sans que le banc n'en tire aucune conséquence. → **à trancher à l'étape 20**.
- **`sweeps/test_game_health.py` (428 l.) et `sweeps/test_physical_counters.py` (448 l.)** ne sont
  couverts par aucune étape non plus ; ce sont les seuls tests unitaires du harnais. → **étape 20**.
