# Étape 21 — Harnais de campagne non couvert (physical_counters, campaign_freeze, tests)  (SHA revu : `421369e`)

Étape ouverte par la synthèse (`docs/revue_code_2026-09-15_correctifs.md`, « Deux questions »,
point 2) : `sweeps/physical_counters.py`, `sweeps/campaign_freeze.py`, `sweeps/test_game_health.py`
et `sweeps/test_physical_counters.py` sont déclarés `CAMPAIGN_HARNESS_FILES` mais n'avaient été lus
par aucune des 20 étapes du plan initial — trou de couverture, pas un constat. Recommandation de la
synthèse : `physical_counters.py` en Opus 5 / high (H3 en dépend entièrement, jamais confronté à
`src/vehicle_base.h`), `campaign_freeze.py` et les deux fichiers de test en Sonnet 5 / medium.

## Constats

### 21.1 — Constante de rotor d'aéronef fausse mais rendue inerte par l'OR sur `unitnumber`        [gravité : P3]
`sweeps/physical_counters.py:246-251` — la classification air traite les composants avec
`elif unitnumber == 0 or subtype in (3, 4):`. Confronté à `src/aircraft.h` d'OpenTTD (upstream,
`enum AircraftSubType`) : `AIR_HELICOPTER=0`, `AIR_AIRCRAFT=2`, `AIR_SHADOW=4`, `AIR_ROTOR=6`. La
valeur `3` n'existe dans aucune configuration réelle ; le rotor d'hélicoptère vaut `6`, jamais
testé par le code. Le commentaire de tête (`:229`, « Ombres (4) et rotors (3) ») reprend la même
erreur. Conséquence observée : aucune, car `unitnumber == 0` (toujours vrai pour une ombre ou un
rotor, qui n'ont jamais de numéro d'unité) suffit seul à classer l'entrée en composant — la
branche `subtype in (3, 4)` ne fait jamais la différence en pratique. Les deux fixtures de test
(`c66_control_fixture_15_3.json`, `c53_real_chunks_15_3.json`) ne contiennent que des avions
(`aircraft_shadows_rotors` == nombre d'avions primaires, un ombre par avion, zéro rotor observé) :
le chemin rotor n'a jamais été exercé, ni en fixture ni en test. `ai/OpexAI/catalog.nut` et
`builder_air.nut` ne filtrent pas explicitement les hélicoptères (aucune occurrence de
« helico » dans ces fichiers), donc le catalogue peut en sélectionner un si son ROI l'emporte sur
un type d'aéroport donné.

**Réconciliation 2026-09-20 : fait.** La classification utilise désormais
`subtype in (4, 6)`, le commentaire indique rotor=6 et
`test_helicopter_head_shadow_and_rotor_subtypes` exerce explicitement une tête hélicoptère
(`subtype=0`), son ombre (`4`) et son rotor (`6`). Suite physique : **8/8** sur l'hôte et
**8/8** dans Docker.

### 21.2 — `campaign_freeze.py` (545 l.) : zéro test unitaire, seul module du harnais C66 dans ce cas        [gravité : P2]
Aucun `sweeps/test_campaign_freeze.py` n'existe, et aucun `--selftest` du dépôt n'exerce
`prepare_frozen_campaign`, `validate_policy_settings`, `parse_ai_settings`, `effective_ai_settings`
ou `freeze_bananas_libraries` (vérifié par grep sur `sweeps/test_*.py` et sur les fonctions
`selftest()` de `bench_1v1_5y_20seeds.py` : aucune n'importe `campaign_freeze`). C'est le seul
fichier des quatre couverts par cette étape sans preuve automatisée — `physical_counters.py` a
7/7 tests + confrontation API exacte, `game_health.py` (étape 17) a `test_game_health.py`.
Or `validate_policy_settings` est précisément le garde-fou fail-closed censé fermer G0 côté C66.4
(voir 21.6) : une régression silencieuse ici (ex. une comparaison qui ne détecte plus une
différence non annoncée) rouvrirait G0 sur le seul chemin qui le ferme aujourd'hui, sans qu'aucun
test ne le signale.

**Réconciliation 2026-09-20 : fait.**
`sweeps/test_campaign_freeze.py` existe et couvre le cœur fail-closed demandé par cette fiche :
`parse_ai_settings` sur le vrai `info.nut` (contrat courant de **48 réglages**), `effective_ai_settings`,
`validate_policy_settings` (différence annoncée, différence parasite, intervention sans effet),
`fingerprint_tree` et `git_state`. Un test isolé supplémentaire exerce maintenant
`prepare_frozen_campaign` et le vrai `freeze_bananas_libraries` sans réseau : deux IA minimales,
un fichier de harnais et une bibliothèque BaNaNaS synthétique sont copiés dans le bundle ; le
manifeste, les empreintes et le descripteur local de bibliothèque sont relus et vérifiés.
Suite campagne : **11/11** sur l'hôte ; dans Docker, **11 tests sont découverts, dont 1 skip
attendu** pour le sous-test `git_state` dépendant du binaire Git.

### 21.3 — `test_game_health.py` ne teste jamais le cas exact que 17.6 dénonce        [gravité : P2]
17 tests couvrent `game_health.py` (étape 17, H4/17.6-17.9) mais aucun n'utilise une série de
`company_value` **décroissante** avec `fleet_changes == 0` — c'est-à-dire le signal réel d'un gel
C56 (une compagnie qui n'agit plus mais dont la valeur bouge seule via emprunt/dépréciation).
`test_earning_without_expansion_is_not_freeze` (`:173-184`) n'exerce qu'une valeur **croissante**
(1000→1600 sur 5 mois). `test_no_signal_on_complete_horizon_is_suspicion_not_exclusion`
(`:186-200`) est le seul test qui produit `no_signal`, avec une valeur **parfaitement constante**
sur 12 mois — exactement le cas que 17.6 identifie comme quasi impossible en jeu réel (la valeur
intègre trésorerie et emprunt, elle ne reste jamais identique à zéro décimale près). La suite de
tests ne fait donc pas que manquer le bug 17.6 : elle documente et fige, sans commentaire, la seule
forme d'entrée qui déclenche `no_signal` — celle qui n'arrive jamais en jeu — sans jamais exercer
celle qui arrive (valeur qui s'effonre). Un correctif à 17.6 pourra passer tous les tests existants
sans ajouter de régression sur le cas qu'il est censé corriger, à moins qu'un cas décroissant soit
ajouté en même temps.

**Réconciliation 2026-09-16 : fait.** Le workspace courant contient
`test_declining_value_without_expansion_is_stagnation` et
`test_recent_one_point_uptick_does_not_hide_net_decline`. La valeur décroissante sans expansion
produit `declining_without_expansion`, puis `stagnation_suspect` fail-closed. Le trou de test
21.3 n'existe plus.

## Vérifié, n'est PAS un bug

- **`physical_counters.py` — le discriminant tête/composant est structurellement correct.**
  Confrontation ligne à ligne aux en-têtes C++ d'OpenTTD (dépôt amont, branche `master` — pas de
  tag `15.3` public distinct disponible pour cette confrontation ; les dispositions de bits de ces
  enums sont stables depuis de nombreuses versions, mais un futur écart mériterait une
  revérification humaine si `15.3` diverge un jour) :
  - `GroundVehicleSubtypeFlags` (`vehicle_base.h`) : `GVSF_FRONT=0` (0x01), `ARTICULATED_PART=1`
    (0x02), `WAGON=2` (0x04), `ENGINE=3` (0x08), `FREE_WAGON=4` (0x10), `MULTIHEADED=5` (0x20).
    `(subtype & 0x01) != 0` pour la tête (rail et route, classe commune) et `subtype == 4` pour
    « wagon simple, aucun autre bit » (`:227,237`) correspondent exactement à ces valeurs.
  - `AircraftSubType` (`aircraft.h`) : `HELICOPTER=0`, `AIRCRAFT=2`, `SHADOW=4`, `ROTOR=6`.
    `subtype in (0, 2)` pour une tête pilotable (`:247`) est exact.
  - `VehState` (`vehicle_base.h`) : `Hidden=0` (0x01), `Stopped=1` (0x02), `TrainSlowing=4` (0x10),
    `AircraftBroken=6` (0x40), `Crashed=7` (0x80). Les masques `0x01/0x02/0x40/0x80` de
    `:282-285` sont exacts, y compris la distinction explicite `TrainSlowing` ≠ `Stopped` déjà
    testée par `test_vehstatus_observables_and_bitmasks`.
  - `StationFacility` (`station_type.h`) : `Train=0` (0x01), `TruckStop=1` (0x02), `BusStop=2`
    (0x04), `Airport=3` (0x08), `Dock=4` (0x10) — identique à `FACILITY_BITS`
    (`physical_counters.py:54-60`).
  - Dans les quatre modes, `unitnumber == 0` est le garde-fou universel qui rend les affinements
    de `subtype` redondants pour tout composant réel (seul le véhicule en tête d'un convoi reçoit
    un numéro d'unité non nul dans le jeu) : aucune entrée composant ne peut échapper à la
    classification même quand le sous-critère `subtype` est imprécis (21.1). Aucun risque de sous-
    comptage silencieux — au pire un `unresolved_role` fail-closed si les deux conditions se
    contredisaient, ce qui n'a été observé sur aucune fixture.
  - Marche du convoi (`next_ptr`, pointeur 1-based) : compteurs de composants et agrégats de
    capacité/valeur sont calculés dans deux passes indépendantes (boucle principale pour le
    comptage, parcours de chaîne pour la capacité) — pas de double comptage possible, vérifié à la
    main sur `:187-389`.
  - Reconfirmé indépendamment par `test_physical_counters.py` sur les deux fixtures réelles
    (21/21 et 30/30 IDs pilotables identiques à l'inventaire API NoAI pris au même instant) : la
    clôture C66.1 (`docs/taches.md:121-131`) tient à une relecture fraîche, pas seulement à la
    confiance dans un test qui passe.
- **`campaign_freeze.py::parse_ai_settings`** — revérifié par exécution directe sur
  `ai/OpexAI/info.nut` : 227 réglages extraits, exactement le compte déclaré par le plan de revue.
  Tous les `custom_value` du fichier sont des entiers littéraux purs (`grep` ciblé, zéro
  correspondance symbolique ou flottante) : le repli « chaîne brute si non entier »
  (`:150-151`) n'est actuellement jamais emprunté, pas une fragilité active.
- **`decode_stations` — repli waypoint.** Le cas particulier `:470-476` (un enregistrement
  `waypoint` sans corps `normal` est ignoré plutôt que classé `missing_base`) est correctement
  isolé par `isinstance(stn, dict) and "waypoint" in stn and not stn.get("normal")` : ne peut pas
  avaler silencieusement une vraie gare orpheline, seulement un enregistrement qui porte
  explicitement la clé `waypoint`. Confirmé par `test_c66_fixture_stations` (cas
  `waypoint-only`).

## Hors périmètre, à relire ailleurs

### 21.6 — Le garde-fou C66.4 de `campaign_freeze.py` existe mais n'est câblé que sur le mauvais banc
`validate_policy_settings` / `effective_ai_settings` (`campaign_freeze.py:140-185`) sont
correctement construits pour fermer G0 : ils comparent les réglages effectifs des deux bras et
échouent (`ValueError`) sur toute différence non annoncée. Mais seul
`bench_1v1_5y_20seeds.py` les importe (`grep` sur tout `sweeps/*.py`) — pas `bench_v2.py`, le
« banc officiel » 20×10 que H2 (`docs/revue_code_2026-09-15_correctifs.md:72-145`) diagnostique
comme structurellement incapable de prouver ce qu'il a joué. Ce n'est pas un nouveau constat : ceci
confirme H2 depuis l'autre bout (le correctif existe déjà dans le dépôt, il n'est simplement pas
branché là où H2 dit qu'il manque). Pas de fiche séparée à ouvrir — à traiter comme un rappel
d'implémentation quand H2 sera corrigé : câbler `bench_v2.py` sur `effective_ai_settings` /
`validate_policy_settings` plutôt que de réinventer le garde-fou.
- `test_game_health.py` et `game_health.py` eux-mêmes (hors la lacune 21.3) restent couverts par
  l'étape 17 et par H4 — pas relus en détail ici au-delà du croisement de couverture.

## Modèle et effort de correction (pour `docs/revue_code_2026-09-15_correctifs.md`)

- **21.1** — **réalisé le 2026-09-20** : `subtype in (4, 6)`, commentaire corrigé et test
  synthétique hélicoptère tête + ombre + rotor.
- **21.2** — **réalisé le 2026-09-20** : `test_campaign_freeze.py` couvre le cœur du contrat
  ainsi que `prepare_frozen_campaign` / `freeze_bananas_libraries` avec une bibliothèque
  synthétique hors réseau.
- **21.3** — **réalisé avec H4** : les deux cas décroissants du test courant figent le comportement
  fail-closed.

## Preuves de revue versionnables — 2026-09-17

Les JSON décisifs sous `results/` sont volontairement gitignorés. La revue conserve désormais ces
preuves sous `evidence/review/` sous forme de gzip **déterministes** (`mtime=0`) et exacts au byte
près. `evidence/review/index.json` associe à chaque source le SHA256/taille du JSON brut et le
SHA256/taille de l'archive. `sweeps/package_review_evidence.py` reconstruit le paquet depuis les
références des documents de revue ; `sweeps/test_review_evidence.py` vérifie couverture,
décompression, hash brut et recompression déterministe. `results/` reste donc un scratch local,
mais une conclusion citée par la revue ne dépend plus d'un fichier ignoré non versionnable.
