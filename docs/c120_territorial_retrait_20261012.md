# Retrait du classement territorial AIR C120 — 12 octobre 2026

Décision utilisateur : « Supprime et nettoie ». Analyse préalable en lecture seule,
puis retrait de `c120_air_territorial_ranking`, ancien défaut 0 aux quatre difficultés.
C120 était gelé jusqu'à correction du modèle AIR ; r4 mélangeait encore les modes,
et r8 était préparé sans lancement. Aucun verdict économique de l'implémentation
courante n'est ajouté ni déduit du retrait.

## Périmètre

Réglage, globale et chargement retirés ; préparation `c120NewTowns`, permutation
AIR seulement, exception dans la promotion défensive, snapshots, compteurs de
filtrage et traces exclusives retirés. Les gardes des diagnostics communs perdent
seulement leur terme C120. Le financement et les admissions économiques restent.

Après C118 puis C120, le setter `OpexC118SetProjectField`, les helpers de couverture
des endpoints/projets et le cache `AIR_TERRITORIAL_COVERAGE_*` n'avaient plus de
consommateur : retirés avec leurs remises à zéro. Les helpers de couverture des
gares réelles, `OpexC118EngineFitsPlan`, les caches C121 et la sonde indépendante
`c118_air_coverage_probe=0`/`C8V|` sont conservés. `persist.nut`, l'économie C121,
le catalogue C121 et la génération des plans AIR sont identiques octet pour octet.

Deux lanceurs C120 et leur contrat exclusif sont retirés après sauvegarde et
vérification SHA-256. Le contrat partagé du cycle du cache de gare est conservé
dans le test de couverture C118. Analyseurs et décodeurs historiques C120 restent
pour les preuves passées ; aucun lanceur historique n'est exécuté.

## Validation pré-enregistrée

Checkout isolé `results/c118_c119_merge_stage_20261012`, branche
`codex/c118-c119-merge-20261012`, base `a8a33fb` avec modifications de ce seul retrait.
Les diagnostics P0 du checkout principal sont exclus. V157/V158/V160 restent à 1.
269 contrats ciblés verts ; audit des 27 sauvegardes et composants partagés réussi.
Une assertion V122 était périmée face aux maps externes V156 : échec reproduit sur
le corps avant retrait, puis attente alignée sur le repli local si les maps sont null.
Les deux filtres sont comparés avant/après sans leurs seuls compteurs C120.

Deux contrôles techniques, graine 42, un an, un duel Opex/AAAHogEx chacun :

- `cleanup_c120_defaults_smoke_20261012_r1` : défauts courants, sonde OFF.
- `cleanup_c120_coverage_smoke_20261012_r1` : même code, seul
  `c118_air_coverage_probe=1` ; vérifier compilation/exécution et émission de couverture.

Profil local : Docker `desktop-linux`, image
`sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`,
cache `openttd-lab-home`, 10 CPU/8 Go RAM/swap 8 Go/10 workers. Montage commun
du dépôt racine avec répertoire d'exécution dans le checkout isolé. Sources figées
par `run_c66_reference.py`, noms uniques, Docker libre vérifié avant lancement.
Santé et couverture attendues à un an, pas gain ni équivalence économique.

## Résultats et état livré

269 contrats verts, audit des composants partagés et spécifications des autres
réglages inchangées, `git diff --check` sans erreur. Préparation hôte de la fixture
R3 failure réussie avec les nouvelles gardes : toutes ses ancres appliquées,
sans partie supplémentaire.

Les deux smokes sont sains et complets, 1/1 duel chacun, Opex et AAAHogEx actifs,
horizons complets, aucune erreur non attribuée. L'année initiale possède trois
trimestres valides, couverture partielle attendue. Sonde OFF : zéro événement de
couverture ; sonde ON : 11 événements distincts décodés et émission
`C118_COVERAGE` vérifiée. Aucun événement C120. Même bundle source :
`be3ab6b84a4e34c4415e3d7b800085949db1a89e73cf5e8127a1a1297d03ce73`.
Manifestes défauts/sonde respectivement :
`5fd9f094afbefb67971f899e84ed25a83b8f8849f9860c6500cab6a97e422d5f` et
`e9b1ab6508e213cdbc557182e26ad054f67e90b40b276b4d5de144f940335b89`.
Manifestes audités : C120 absent, V157/V158/V160, C121 et les adoptions explicites
à 1 ; seule la sonde de couverture diffère. Les trajectoires peuvent changer avec
la sonde : ces smokes ne mesurent pas l'effet économique du nettoyage.

[Preuves archivées](../evidence/review/c120_cleanup_20261012/README.md) : 39 artefacts,
SHA-256 brut/gzip vérifiés ; sauvegardes récupérables avant suppression.
[Audit des composants](../results/cleanup_c120_audit_20261012.json),
[contrats](../results/cleanup_c120_contracts_20261012.json),
[audit des deux smokes](../results/cleanup_c120_smoke_audit_20261012.json).

Retrait local sur la branche isolée déjà publiée avant cette demande ; pas de
nouveau commit ni push. Checkout principal et diagnostics parallèles préservés.

Le 13/10, l'utilisateur demande ensuite « Commit pousse » : publication ciblée de
ce retrait, de ses contrats, documentation et preuves sur
`codex/c118-c119-merge-20261012`. Les validations ci-dessus portent sur ce code ;
aucune fusion distante dans master ni ajout des diagnostics P0 demandé.
