# AIR-GROW — estimateur marginal de renfort, 24 octobre 2026

Demande utilisateur : implémentation opt-in sur `air-grow-marginal`, sans partie,
Docker, publication ni changement de défaut. Référence locale avant intervention :
`eec5db814734b99c03ed005bfc476c7ff20006c7`, arbre propre. Le diagnostic fourni
`/home/deploy/.claude/jobs/e230de46/tmp/renfort/rapport_renfort.md`, §3, motive
la demande commune aux deux tailles de flotte. Les résultats rétrospectifs ne
qualifient pas ce nouvel estimateur. AIR-PELOTON-1 n'a pas d'entrée portant ce nom
dans le `docs/taches.md` de cette référence ; le §4 du diagnostic en décrit la piste.

`air_grow_marginal` : 0..2, pas 1, défaut **0 aux quatre difficultés**.
0 n'appelle aucun helper marginal et conserve les corps historiques hors gardes.
1 calcule et journalise, sans changer prix, taille, profit ou acceptation.
2 ajoute la condition ΔP > 0 aux gardes historiques, remplace le profit de
classement par ΔP et utilise le prix du moteur sélectionné. Le résultat net
n'est pas recalibré une deuxième fois par C70. Les refus historiques C121/V161
restent applicables. Une estimation connue finance un seul avion par passe,
pour ne pas multiplier le même incrément par un lot.

## Formule et unités

Pour chacun de `A_PASS,A_MAIL,B_PASS,B_MAIL`, séparément :

```
W = jours réellement couverts par l'agrégat C117 retenu (courante + 0 à 3 closes)
D = (enlèvements observés sur W + stock courant de la gare) × 365,25 / W
R = 365,25 / durée d'une rotation en jours
K_N = N × capacité du moteur acheté × R
K_N1 = (N+1) × capacité du moteur acheté × R
Δrecette = Σ tarif × (min(D,K_N1) − min(D,K_N))
ΔP = Δrecette − coût annuel moteur − prix moteur × 365,25 / durée de vie en jours
```

D et K : unités de cargo/an ; capacité : unités/avion ; R : rotations/avion/an ;
tarif : £/unité ; recette, charges, amortissement et ΔP : £/an. PASS et MAIL
ne sont jamais additionnés avant multiplication par leurs tarifs respectifs.
Le stock est drainé sur **une fenêtre W**, hypothèse explicite, et non traité
comme une hausse permanente de production ou de note. D est identique pour les
deux tailles. Si D ≤ K_N dans tous les compartiments, Δrecette = 0 et ΔP est
négatif des charges et de l'amortissement.

C117 compte les legs par **destination** : `paxB/mailB` sont les enlèvements de A,
et réciproquement. Pour un moteur inchangé, deux fois la durée moyenne des legs
complets C117, chargement inclus, donne la rotation (au moins deux legs mesurés).
Sinon, repli **de rotation** sur `OpexC121AirTripModel`, avec les deux aéroports
existants et leurs délais appris. Le tarif utilise la distance Manhattan et
`OpexC121PhysicalPaymentDays` ; aucun forfait de recette MAIL n'est ajouté.
Capacités : véhicule modèle vivant pour un clonage, observations exactes C121
du moteur PASS refitté pour un autre modèle. Le moteur sélectionné suit
`OpexAirAddPlane` ; son repli de construction vers l'ancien moteur est revérifié.

## Données inconnues et journal

Pas de nouvel état sauvegardé : lecture des fenêtres C117 transitoires,
réinitialisée dans `OpexLoadSettings`. `_projects` est reconstruit après Load ;
les champs d'entrée/projet ne sont pas ajoutés au format de sauvegarde.
La collecte C117 par cargo/sens est réactivée uniquement à 1/2.

Repli **de décision** = comportement historique intact, avec motif :

- `obs_days` : agrégat disponible absent ou <14 jours ;
- `obs_stale` : dernier échantillon du collecteur > `C117_AIR_SAMPLE_DAYS + 2` jours ;
- `obs_trips` : un des deux sens sans trajet observé ;
- `obs_invalid_order` : `invalidOrderSamples > samples / 4` ;
- `obs_unobserved` : `unobservedTransitions > (tripsA + tripsB) / 4` ;
- `obs_engine_change`, `obs_mixed_engine` : changement/mélange de moteurs dans
  la fenêtre retenue ou la courante ;
- `fleet_changed` : effectif ou moteur vivant différent des observations ;
- `station` : gare invalide, identique aux deux bouts ou liste de lignes absente ;
- `shared_station` : une autre ligne partage une gare. Le stock commun n'est
  pas attribué arbitrairement au renfort ; aucune politique de hub ne change ;
- `cargo`, `engine_capacity`, `rotation`, `cost`, `flow_or_fare` : donnée
  correspondante inconnue/invalide. Un stock observé nul reste un zéro valide.

Le journal `AIR_GROW_MARGINAL` contient tous les champs demandés ; `d/kn/kn1`
sont les quatre composantes dans l'ordre ci-dessus. Un résultat inconnu publie
`dp=unknown`, jamais un faux zéro rentable. `prior` est le profit historique
final par avion après V161 en phase `rank`, ou `unknown` ailleurs. Le champ
additionnel `phase` distingue `pending_v161`, `rank`, `direct`, `execute`,
`purchase`, `clone_fallback` : compter les replis **par phase**, sans sommer
des traces successives d'une même décision comme des décisions indépendantes.
Tous les appels au logger et son émission sont sous `DECISION_LOG`.

## Correction bornée — trois fenêtres closes

Le smoke VPS fourni `marginal_smoke_1x3_20261024b` (42, trois ans,
`air_grow_marginal=2`, `probes=258`) est annoncé sans erreur mais sans activation :
2 306 `obs_trips`, 94 `obs_stale`, 52 `shared_station`, 24 `obs_invalid_order`.
Source fournie : `results/marginal_smoke_1x3_20261024b_engine/marginal2_seed42_r0.log`.
Un aller-retour de 40–60 jours ne tient pas dans un bucket C117 de 30 jours.

Les trois dernières fenêtres closes sont désormais conservées par ligne sous forme
de snapshots scalaires, sans chaînage ni sauvegarde, même si une fenêtre fait moins
de 14 jours. L'estimateur teste la courante, puis ajoute successivement la dernière,
les deux dernières et les trois dernières closes jusqu'à obtenir ≥14 jours et
au moins un trajet par sens. Il s'arrête au premier agrégat suffisant. Les jours,
flux, durées de legs et compteurs de qualité sont sommés ; D utilise ces jours.
Un trou de buckets/dates, un effectif ou moteur différent, une fenêtre mélangée
ou modifiée interrompt l'extension avant cette fenêtre et toutes les antérieures.
Les gardes existantes s'appliquent ensuite à l'agrégat et à la flotte courante.
`win_days` et `wins` indiquent les jours et le nombre de fenêtres retenues,
courante comprise si elle couvre des jours. Le réglage 0 conserve ses empreintes.
Aucune partie ni validation Squirrel par le moteur dans cette intervention.
Validation locale : 12 contrats ciblés OK ; suite complète 2414→2415 tests,
14 échecs et 5 erreurs identiques par nom avant/après, 7 ignorés et 2 échecs
attendus. Sorties locales : `/tmp/marginal_before_tests.log` et
`/tmp/marginal_after_tests.log`. Parmi les erreurs préexistantes :
`test_airr1_offline_postprocess_20261023` requiert `openttdlab` absent ;
`test_analyze_air_load_shadow`, `test_audit_air_roi_renfort1` et
`test_audit_air_roi_renfort1_itt` requièrent `pytest` absent.

## Contrats, empreintes et validation

`sweeps/test_air_grow_marginal.py` : 12 contrats, défauts/bornes/lecture unique,
gardes OFF, log, provenance du profit, replis/persistance et miroir dimensionnel
(demande satisfaite, incrément partiel, sens/cargos indépendants), historique borné
et sélection du plus court agrégat sans rupture de flotte.

Empreintes OFF explicitement recalées sur le HEAD local indiqué plus haut dans
`sweeps/fixtures/air_grow_marginal_off.json` (indentation 2), corps entiers après
retrait des seuls ajouts opt-in :

- `air_fleet.nut::OpexAirAddPlane` ;
- `projects_builders.nut::OpexProjectFromFleet` ;
- `task_air.nut::OpexAI::_resizeAirFleets` ;
- `task_projects.nut::OpexAI::_tryBuildFleetProject` ;
- `probes.nut::OpexC117AirThroughputStep` (expression OFF ramenée à `true`) ;
- `projects_models.nut::OpexC70Profit`.

Les empreintes de fichiers entiers `probes.nut`, `settings.nut`, `info.nut` de
`test_po01c_regen_split` étaient **déjà fausses avant intervention** : elles
ne sont pas remplacées par les nouveaux hashes pour faire disparaître ces
échecs. Les nouveaux contrats OFF vérifient séparément les corps touchés.
Aucun nouvel appel Valuate : inventaires V261/V262 inchangés.

Plafond et compte 58→59 dans `test_v246_fixed_policies`, `test_v251_inventory`,
`test_v259_bridge_renew`, `test_v276_candidate_slices`, `test_v284_rail_growth`,
`test_parameter_retirements_20261023`. Les 43 retraits historiques restent vérifiés.

Suite `python3 -m unittest discover -s sweeps -p 'test_*.py'`, sortie complète
conservée localement avant d'en afficher les trois dernières lignes :

| État | Tests | Échecs | Erreurs | Ignorés | Échecs attendus |
|---|---:|---:|---:|---:|---:|
| Avant | 2403 | 14 | 5 | 7 | 2 |
| Après | 2412 | 14 | 5 | 7 | 2 |

Les ensembles de noms d'échecs/erreurs avant/après sont identiques. Héritage :
PO01C générateurs, huit pins PO01D et dépendances PO01F ; deux contrats capture
rail ; contrat R9 ; précontrôle station. Erreurs : extraction site-validity
(`ValueError`), module AIRR1 (`openttdlab` absent), trois imports d'analyses
AIR (`pytest` absent). Logs hôte : `/tmp/air_marginal_before.log` et
`/tmp/air_marginal_final.log`. `git diff --check` propre.

Aucune compilation Squirrel ni partie : interdiction explicite de cette tâche.
Le code est **non qualifié en moteur et économiquement**, défaut 0 conservé.

## Correction des gardes après smoke VPS (24/10)

Intervention bornée sur `443cf2e3`, branche `air-grow-marginal`, arbre initial propre.
Lecture de `results/marginal_smoke_1x3_20261024_engine/marginal2_seed42_r0.log` :
**2 294** traces, toutes `decision=legacy fallback=observation` :
900 `pending_v161`, 900 `rank`, 247 `execute`, 247 `purchase`.
Le journal ne contient pas les sous-causes ; leur répartition est inconnue.
Les sept motifs ci-dessus remplacent ce motif opaque dans le journal existant :
une trace compte le premier blocage rencontré, à agréger par `fallback` et `phase`.
Ce ne sont pas 2 294 décisions indépendantes.

Justification par le code, sans attribuer de cause mesurée au smoke :

- Le bucket C117 change tous les 30 jours ; exiger 14 jours de fenêtre courante
  rend mécaniquement indisponible environ la moitié de chaque bucket. Au flush,
  les seuls agrégats lus par l'estimateur sont copiés si la couverture atteint
  14 jours. La copie ne contient aucun ancien état et n'est réutilisable que dans
  le bucket immédiatement suivant, tant que la courante reste <14 jours.
- La fraîcheur porte sur le **collecteur courant**, pas sur la date historique
  de clôture. Le seuil passe de 3 à 4 jours (`C117_AIR_SAMPLE_DAYS=2`, marge 2),
  pour tolérer un décalage d'échantillonnage. Un bucket sauté invalide la copie.
- Les deux tolérances de 25 % demandées bornent les observations censurées au
  lieu d'exiger une collecte parfaite : ordre invalide rapporté aux `samples`
  de ligne (compteur par véhicule, donc garde plus stricte à plusieurs avions),
  transition non observée rapportée aux trajets A+B. L'égalité à 25 % passe.
  Leur effet réel et le biais résiduel du flux restent à mesurer.
- `air_fleet.nut::OpexAirAddPlane` ajoute exactement stationA puis stationB et
  impose `GetOrderCount(plane) == 2` ; les clones partagent/copient les ordres.
  Rien dans ce code ne prouve que les positions >1 sont des ordres d'entretien
  légitimes : aucune exemption ajoutée. Les ordres hors liste restent comptés.
- Les gardes moteur/effectif vérifient aussi la fenêtre courante : une copie
  historique ne doit pas masquer une modification récente de flotte.

À 0, aucune copie ni sélection de fenêtre marginale : empreintes OFF inchangées,
avec une empreinte supplémentaire du flush prise sur `443cf2e3`. État uniquement
dans `C117_AIR_LINE_STATE`, vidé au Load, aucun format de sauvegarde modifié.
Validation : **11 contrats OK** ; suite complète **2412→2414 tests**, mêmes
**14 échecs / 5 erreurs**, mêmes noms vérifiés avant/après, 7 ignorés et 2 échecs
attendus. Logs hôte : `/tmp/marginal_fix_before.log`, `/tmp/marginal_fix_after.log`.
`git diff --check` propre. Aucune partie ni Docker autorisé pour cette correction ;
l'activation effective après correction n'est donc pas encore mesurée.

## Coût d'opcodes estimé, non mesuré

OFF : lecture du réglage une fois et tests de garde seulement ; aucun scan,
modèle, chaîne ou journal marginal. Ce n'est pas une preuve de zéro instruction :
les gardes elles-mêmes coûtent quelques instructions, notamment dans C70.
ON : réactivation des champs détaillés du sampler C117 existant ; estimation
en O(véhicules de la ligne + lignes existantes + choix moteur), quatre
compartiments fixes, sans nouveau Valuate/A*. Ordre de grandeur statique :
centaines à quelques milliers d'opcodes par estimation hors coût variable de
sélection moteur ; plusieurs estimations par candidat/achat pour la revalidation.
Le surcoût annuel C117 et ces estimations restent à mesurer avec la sonde existante.
