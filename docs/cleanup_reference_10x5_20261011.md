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
rtk proxy python -X utf8 sweeps/run_c66_reference.py --campaign cleanup_reference_10x5_20261011_1227 --container-name cleanup-reference-10x5-20261011-1227 --policy-id cleanup_reference --reference OpexAI --primary-metric profit_year --decision-rule signs20 --years 5 --seeds 42 100 7 999 2026 1 17 73 314 512 --repeats 1 --cpus 10 --memory 8g --max-workers 10 --out results/cleanup_reference_10x5_20261011_1227.json
```

## État au pré-enregistrement

Non lancé. Contrôles de nettoyage déjà effectués : 18 contrats voisins V126 et smoke ; 102 contrats plafond C121, smoke et fixture VM/Save-Load partagée ; 91 contrats stock C121 et smoke. Dernier `git diff --check` propre. Aucun push demandé. Résultats à analyser uniquement après complétude, horizon, couverture annuelle et santé vérifiés.
