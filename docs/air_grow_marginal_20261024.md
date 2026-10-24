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
W = jours réellement couverts par la fenêtre C117 courante
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

Pas de nouvel état sauvegardé : lecture de la fenêtre C117 déjà transitoire,
réinitialisée dans `OpexLoadSettings`. `_projects` est reconstruit après Load ;
les champs d'entrée/projet ne sont pas ajoutés au format de sauvegarde.
La collecte C117 par cargo/sens est réactivée uniquement à 1/2.

Repli **de décision** = comportement historique intact, avec motif :

- `observation` : fenêtre absente, <14 jours, dernier échantillon >3 jours,
  sens non observé, ordre/transition invalide ou fenêtre à moteurs mélangés ;
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

## Contrats, empreintes et validation

`sweeps/test_air_grow_marginal.py` : 9 contrats, défauts/bornes/lecture unique,
gardes OFF, log, provenance du profit, replis/persistance et miroir dimensionnel
(demande satisfaite, incrément partiel, sens/cargos indépendants).

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
