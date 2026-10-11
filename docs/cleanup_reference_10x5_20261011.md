# Référence après nettoyage — OpexAI contre AAAHogEx, 10×5

Demande utilisateur du 11/10 : committer les nettoyages puis exécuter un banc contre AAAHogEx, 10 graines × 5 ans, 10 CPU et 10 workers. Pré-enregistrement avant lancement, vers 12h27 Europe/Paris.

## Code et protocole

Les trois retraits demandés sont inclus : `v126_air_served_town_reuse`, `c121_air_target_limit`, `c121_fleet_stock_growth`, avec contrats/diagnostics adaptés. Sources initialement basées sur `dd19329` ; commit de nettoyage à réaliser avant le lancement. Le lanceur enregistrera son SHA et l'état Git, puis figera sources, harnais, bibliothèques, adversaire et configuration dans un bundle neuf.

- Campagne : `cleanup_reference_10x5_20261011_1227`.
- Politique : `cleanup_reference`, bras `OpexAI` aux défauts livrés, sans variante ni sonde ajoutée.
- Adversaire : AAAHogEx du dossier courant `ai/AAAHogEx-115`, figé et haché par le harnais.
- Carte partagée, Opex joueur 0 et AAA joueur 1 ; configuration standard du harnais.
- Graines, dix premières de `SEEDS` : 42, 100, 7, 999, 2026, 1, 17, 73, 314, 512.
- Horizon : cinq ans à partir de 1970, une répétition ; 10 parties et 50 années de jeu, 20 résumés compagnie attendus.
- Mesure : profit annuel terminal `profit_year`, valeur compagnie, parc physique et santé ; résultat contre l'adversaire, sans attribution causale au nettoyage.
- Catégorie : référence diagnostique C66.3. Aucune porte V102 A/B ni décision d'adoption ; `signs20` nommé pour compatibilité du CLI, sans variante à qualifier.
- Docker Desktop local `desktop-linux`, image `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`, cache `openttd-lab-home`, montage de ce dépôt à `/work`.
- Ressources : 10 CPU, 8 Go RAM, plafond swap égal à8 Go, 10 workers. Aucune autre campagne active au contrôle préalable.

Commande prévue depuis la racine :

```powershell
rtk proxy python -X utf8 sweeps/run_c66_reference.py --campaign cleanup_reference_10x5_20261011_1227 --container-name cleanup-reference-10x5-20261011-1227 --policy-id cleanup_reference --primary-metric profit_year --decision-rule signs20 --years 5 --seeds 42 100 7 999 2026 1 17 73 314 512 --repeats 1 --cpus 10 --memory 8g --max-workers 10 --out results/cleanup_reference_10x5_20261011_1227.json
```

## État au pré-enregistrement

Non lancé. Contrôles de nettoyage déjà effectués : 18 contrats voisins V126 et smoke ; 102 contrats plafond C121, smoke et fixture VM/Save-Load partagée ; 91 contrats stock C121 et smoke. Dernier `git diff --check` propre. Aucun push demandé. Résultats à analyser uniquement après complétude, horizon, couverture annuelle et santé vérifiés.

## Résultat vérifié

Commit de nettoyage **`5b05be9b9ed6a4d5942ae846904fdbaae94decc9`**, arbre propre au lancement (`dirty=false`). Le premier appel a été refusé par le CLI avant gel/partie : `--reference OpexAI` est invalide, car cette option exige `OpexAI[cle=valeur]`. Appel corrigé en omettant l'option : le bras simple OpexAI reste aux mêmes défauts pré-enregistrés. Aucun jeu ni mesure du premier appel, aucun changement de code et aucun rerun économique.

**10/10 duels complets et sains**, 20/20 résumés compagnies, aucun échec ni erreur NoAI. Toutes les graines prévues sont présentes, dernier checkpoint `1974-12-01`, quatre trimestres valides pour chacun des 20 profits annuels terminaux. Ressources confirmées par le manifeste et Docker : 10 CPU, 10 workers, 8 Go RAM et swap plafonné à8 Go.

| Moyenne terminale | OpexAI | AAAHogEx | Écart Opex − AAA |
|---|---:|---:|---:|
| Profit annuel | 1 875 416,70 £ | 3 441 327,50 £ | −1 565 910,80 £ (−45,50 %) |
| Valeur compagnie | 6 570 172,30 £ | 6 201 304,00 £ | +368 868,30 £ (+5,95 %) |
| Véhicules primaires | 94,0 | 215,4 | −121,4 |
| Gares physiques | 48,1 | 153,6 | −105,5 |
| Score historique | 649,2 | 789,3 | −140,1 |

Profit : **0V/10D/0E**, Wilcoxon exact bilatéral p=0,001953125 ; médiane du delta −1 435 878 £/an. Valeur : **8V/2D/0E**, Wilcoxon p=0,322265625, signes p=0,109375. Les pourcentages sont calculés sur les moyennes, sans confondre ratio moyen et moyenne des ratios. L'avantage moyen de valeur n'est pas statistiquement établi ; le déficit de profit contre l'adversaire est net sur cet échantillon.

| Graine | Profit annuel Opex | Profit annuel AAA | Valeur Opex | Valeur AAA |
|---|---:|---:|---:|---:|
| 42 | 2 103 754 | 3 040 277 | 7 695 482 | 5 555 483 |
| 100 | 1 169 528 | 2 215 057 | 4 006 559 | 3 854 389 |
| 7 | 2 360 891 | 4 220 326 | 9 021 942 | 8 376 257 |
| 999 | 1 750 961 | 4 679 429 | 5 410 148 | 7 851 908 |
| 2026 | 1 958 946 | 3 170 370 | 6 582 350 | 5 827 442 |
| 1 | 2 295 721 | 3 585 047 | 8 799 583 | 6 457 269 |
| 17 | 1 535 864 | 2 842 430 | 5 547 788 | 5 500 165 |
| 73 | 2 263 379 | 3 900 851 | 7 665 559 | 7 448 034 |
| 314 | 2 213 841 | 3 779 031 | 7 700 020 | 6 321 194 |
| 512 | 1 101 282 | 2 980 457 | 3 272 292 | 4 820 899 |

Montants par graine en £. Résultat de référence C66.3, `policy_comparison=null` : il décrit le niveau courant face à AAAHogEx, **sans mesurer l'effet causal des trois nettoyages**, sans référence avant retrait, ni qualification V102 A/B.

## Provenance conservée localement

- [JSON final](../results/cleanup_reference_10x5_20261011_1227.json), SHA-256 `d6d59a7629c54d0cfe96e64b691dbb6bea58be7b4d3e7b3c95ec14d46a773546`.
- [Manifeste](../results/cleanup_reference_10x5_20261011_1227.manifest.json), SHA-256 `89ae6ab70936aea365830244f9e0de989074b8dcf52aa17da2251a0d7d9e6a41`, empreinte vérifiée contre le JSON final.
- Bundle figé `results/cleanup_reference_10x5_20261011_1227_bundle`, 108 fichiers, SHA-256 `cf065a29e3a660107adaf09e20c78c0f97e4aec49e7b96b746ed1bf2efedb2de`.
- Checkpoints JSONL et logs moteur dans les chemins de la campagne ; aucune sauvegarde demandée. Gros artefacts laissés dans `results/`, sans ajout forcé à Git.

Aucun défaut modifié après mesure, aucune publication distante.
