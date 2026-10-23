# Garde de remplissage AIR — 23 octobre 2026

Demande explicite : garde de renfort opt-in, sur `air-load-guard`, depuis
`origin/master` **1df4bdb7a3256f46a78b98e9060b5a5bff42969a**. Reprise du diff
non commité de la passe interrompue. `air_load_min_pct` : entier 0..100,
pas d'interface 5, défaut **0 aux quatre difficultés**. Aucun changement de
calibration V161/C121 ni du module `air_flotte1_shadow.nut`.

## Mesure retenue

Réutiliser les observations C117 déjà faites tous les deux jours de jeu dans
les boucles normale et profilée. Pour chaque avion, C117 mémorise la charge
maximale du cargo de la ligne et sa capacité lorsqu'il est `VS_RUNNING`,
entre deux changements d'ordre 0/1. Une transition termine un trajet :
enregistrer **une seule paire charge/capacité**, et non chaque photo en vol.
Le premier trajet partiel après création/rechargement est ignoré ; un ordre
invalide (par exemple détour de dépôt) invalide le trajet pour cette garde.
Un trajet sans observation en mouvement ou sans capacité positive ne compte pas.

C'est une estimation de charge au départ par trajet observé, pas un événement
de départ exact fourni par l'API. La charge reste stable pendant le vol ; le
maximum en mouvement évite de retenir le déchargement à l'arrivée. La fréquence
existante peut manquer un trajet très court ; il n'est alors pas inventé.
Les vols longs ne reçoivent pas davantage de poids parce qu'ils sont observés
plus souvent. Le courrier n'est pas ajouté aux passagers. Le ratio de revenu
annuel serait moins fiable : prix, distances, âge du cargo et frais ne donnent
pas directement les unités chargées par trajet.

La ligne conserve un anneau de **12 trajets** et leurs sommes entières.
`load_pct = floor(100 × somme(charge) / somme(capacité))` : pondération par
capacité, y compris en flotte mixte. Pas de refus avant **6 trajets**, ni si
la dernière observation date de plus de **180 jours**. Après cette expiration,
le prochain trajet réinitialise la fenêtre. Une valeur exactement au seuil
est acceptée. Les 180 jours sont un délai d'inactivité, pas une purge par âge
de chaque entrée de l'anneau.

## Intégration et persistance

- `_resizeAirFleets` : garde commune aux modes direct et `plan != null`, avant
  les évaluations C121, après la reconstitution de crash.
- `_tryBuildFleetProject` : nouvelle vérification avant la trésorerie et
  l'achat, car un projet peut survivre à son observation initiale.
- Refus `F`, raison `low_load_factor`, journal `AIR_FLEET ... load_pct=` et
  rejet C73 `low_load_factor`. Sous `DECISION_LOG`, chaque trajet enregistré
  émet `AIR_LOAD line=... samples=... load_pct=...`.
- V252 et `OpexAirRefleetCrashedPlane` inchangés ; `needsRefleet` est exempté.
- `airLoad` ne contient que tables/tableaux/entiers. La projection générique
  `OpexSaveProjectLine` le conserve ; la réconciliation garde la table ligne.
  C117 reconstruit son état véhicule transitoire au Load et ignore son premier
  trajet partiel. Une ancienne sauvegarde sans `airLoad` attend six trajets.

## Coût et défaut désactivé

Aucun nouvel appel `AIVehicle`, aucune nouvelle boucle véhicule, aucun
`Valuate`, aucune modification des appels des boucles principales. Ajout O(1)
par trajet terminé et O(1) par vérification de renfort ; stockage O(12) par ligne.
Estimation de lecture de code, **non mesurée** : ordre de quelques centaines
d'opcodes par enregistrement et quelques dizaines par garde active, hors logs.
Au défaut 0, seuls les tests de court-circuit et la lecture initiale du réglage
s'ajoutent : aucune nouvelle fenêtre, aucun journal AIR_LOAD, aucun refus F.

Les contrats comparent à l'octet les anciens corps après retrait des seuls
crochets opt-in. Cela verrouille les décisions du chemin OFF dans le code ;
cela ne prouve pas une identité du bytecode ou de la trajectoire moteur : les
tests conditionnels ajoutent quelques opcodes même à 0.

## Validation

Contrats `test_air_load_guard.py` : dix tests (réglage, OFF, deux chemins,
minimum et péremption, crash/V252, anneau pondéré, trajets partiels/invalides,
appels API, logs, persistance structurelle). Tests statiques, pas une VM Squirrel.

Inventaires de réglages actualisés de 58 à **59** : contrats des retraits du
23/10, V246, V251, V259, V276 et V284. Hashes de contrats PO01C explicitement
recalculés pour **probes.nut, settings.nut, info.nut** uniquement. Aucun nouvel
`Valuate` : inventaires V261/V262 inchangés.

La suite `python3 -m unittest discover -s sweeps -p 'test_*.py'` sur
`origin/master` dans ce worktree, avec restauration du travail local après
exécution, collecte **2388 tests**, 4 erreurs d'import préexistantes, 7 ignorés,
2 échecs attendus. Modules concernés : `test_airr1_offline_postprocess_20261023`
(`openttdlab` absent), `test_analyze_air_load_shadow`, `test_audit_air_roi_renfort1`,
`test_audit_air_roi_renfort1_itt` (`pytest` absent). Aucun masquage ni installation.
Log local : `.air_load_validation/baseline_verified.log`.

Suite finale : **2398 tests**, **aucun échec d'assertion**, les mêmes 4 erreurs
d'import, 7 ignorés et 2 échecs attendus ; dix nouveaux contrats passent.
Log local : `.air_load_validation/final.log`. `git diff --check` passe.

**Aucune partie, aucun Docker, aucun smoke ni round-trip moteur Save/Load**,
conformément à l'interdiction utilisateur. Compilation Squirrel, distribution
réelle, coût mesuré et effet économique restent non validés. Le défaut reste 0.
