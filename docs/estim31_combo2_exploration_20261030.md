# ESTIM-31 — deuxième exploration combinatoire AIR × RAIL (30/10/2026)

**Statut : campagne expérimentale nouvelle, qualification économique non achevée.**
Cette étude ne répète ni les trois 40×5/20×10 finalistes ni la promotion
`10b5197d`. La référence historique décennale reste le défaut publié
V161 AIR=2,00 / RAIL=0,75 / poids=15 / pente : **66,557726256 %** en
1979. Le record historique à cinq ans est **106,062928693 %** (autre
configuration ; son classement décennal a déjà été tranché).

## Sources et sécurité

- Point de départ exact : `10b5197dda97c991f783841b63b1ac19c83cc5b8`.
- Travail dans `.worktrees/estim31_combo2_20261030`, branche
  `experiments/estim31-combo2-20261030` ; `master` local sale et archives
  historiques laissés intacts.
- Moteur Docker `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659` ;
  10 CPU, 8 Gio, huit workers au plus, un seul Docker de benchmark.
- Source économique et adversaire local `AAAHogEx-115` copiés dans des
  bundles distincts, sous `results/estim31_combo2_20261030/<candidat>`.
  Le code de l'adversaire partagé n'a pas été modifié. Les manifestes C66
  enregistrent les empreintes des sources et des bibliothèques.
- Les scripts `sweeps/estim31_combo2_prepare_20261030.py` et
  `sweeps/run_estim31_combo2_20261030.ps1` empêchent l'écrasement des
  bundles/campagnes. Les vieux résultats restent inchangés.
- Deux premiers gels de C02 (`sans AAAHogEx`, puis option ESTIM
  explicitement égale au défaut) ont échoué **avant toute partie**.
  Ils sont conservés en traces `r1/r2` et ne sont pas des essais économiques.

## Hypothèses et croisement

Les trois 20×10 existants révèlent un ralentissement des investissements
après 1974 malgré 14,74 M£ de liquidités en 1979. Le parc ferroviaire
Opex stagne à ~29,6 trains contre ~56,3 chez AAA. Les recettes AIR
restent inférieures chez Opex malgré 84,25 avions contre 48, mais le
ratio YTD/stock ne mesure **pas** la marge de chaque avion.

`POST-1974-ENTONNOIR` : nouvelle infrastructure, rang portefeuille,
retards A*, financement et choix de la flotte sont des causes à séparer.
`RAIL-RENDEMENT-TARDIF` : `task_v284.nut` écarte certaines lignes avant
la valorisation marginale ESTIM ; l'assouplissement expérimental ne
remplace pas cette valorisation ni les gardes de géométrie.
`AIR-PRODUCTIVITÉ` : les coefficients appris par mode, V161 même moteur,
V252 et les mutations de V249/charge peuvent interagir avec cette
expansion ferroviaire.

La grille figée contient **dix tuples distincts** C01–C10, parmi lesquels
des combinaisons AIR=1,50–2,50, RAIL=0,50–1,50, poids=5/15,
V284 à un/deux/trois ans, garde de flux V284, minimum de charge AIR
0/25 et V249 0/2. L'objectif est explicitement d'autoriser plusieurs
changements individuellement défavorables à se compenser en combinaison.
Tous les nombres sont des réglages/valeurs déjà existants : **aucune
nouvelle constante seuil économique introduite dans le code de production**.

Les variantes `flow` remplacent deux gardes V284 par un test alternatif
sur `predCarried` existant (uniquement avec `ESTIM & 4`) : aucun train
supplémentaire automatique ; les contrôles d'équipement rentable,
capacité, finances et boucle physique restent présents. Les sources
OFF C121, `settings.nut`, `persist.nut` et les défauts publics ne changent
pas. Hypothèse susceptible d'échouer économiquement ; exposition à mesurer.

## Protocole et classement

Pilotes : **cinq graines communes × cinq ans**, 1970–1974, deux politiques
par graine, `probes=2`, source et Docker figés. Sélection des pilotes
sur **100 × moyenne des profits OpexAI / moyenne des profits AAAHogEx
du propre bras *variant*** au 1er décembre 1974. Le bras `reference`
sert de comparaison interne, et ne doit pas être confondu avec la
variante si le harnais affiche en premier son bilan.

Après contrôle des cinq graines, seules les configurations intéressantes
et techniquement saines seront considérées à 40×5 ; si elles sont
compétitives, la règle utilisateur sélectionne les trois meilleures
nouvelles configurations à 20×10 sans relancer les anciennes. Aucun veto
de valeur de société, p-valeur, IC95, ancien seuil `gain_short`.

## Résultat validé à ce stade

| Essai | Source | Santé | Opex / AAA à cinq ans | Différence en points vs bras `reference` de la même source |
|---|---|---|---:|---:|
| C02 AIR2,00 RAIL1,00 poids15, V284 an1 et flux | `estim31combo2_c02_a200_r100_v1_flow_5x5_20261030_r3` | **10/10 jeux complets** | **86,917484 %** (2 782 456 / 3 201 262 £/an) | **−2,6852** |

Le récapitulatif imprimé par le harnais donne d'abord **89,60 % pour
le bras de référence**, non le score C02. Le score ci-dessus a été
recalculé depuis les enregistrements `duel_policy_id=combo2_c02...`
et les deux compagnies du même bras. Ce pilote n'est **pas** une preuve
d'adoption ou de rejet pour le reste de la grille.

## Tests et limites

Douze contrats ciblés de combinaison, FullScan C121, opt-in et analyse
20×10 ont passé le 30/10 ; `git diff --check` a passé. Le vieux test
`sweeps.test_estim31_c121_dispatch` attend encore le FullScan inline
dans l'ancien fichier et échoue sur la structure modulaire publiée :
il n'a **pas** été déclaré vert. La suite globale historique reste
également non verte, conformément à `QUALITÉ-TESTS-ESTIM31`.

Les archives du nouveau défaut n'exposent pas à `probes=2` les rejets
OD uniques après 1974. L'hypothèse de projet constructible et rentable
écarté est **non encore démontrée** ; une instrumentation dédiée et
un 1×10 loggé ne seront lancés que si indispensables à l'arbitrage.
