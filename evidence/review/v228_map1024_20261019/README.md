# V228 — duel sur carte 1024 × 1024 (PC, 19/10/2026)

## Protocole et résultat

- Commande : `bash sweeps/run_v228_pc.sh map1024` **uniquement** ; `map1024` est une **taille de carte**, `--map-size 10` = 1024 × 1024 tuiles, et non la graine 1024 (qui fait partie des 20 graines).
- Référence `OpexAI[v264_convergent_freight=1]` contre AAAHogEx-115, carte partagée, départ 1970, 20 graines, 10 ans, 1 répétition, 10 workers, Docker `--cpus 10 --memory 8g --network host`.
- Git au lancement : `5108fffd69bd70d9383fd07c9848e3f2db58d08a`, **dirty=1** (correctif local du checkpoint JSONL et documentation/lanceur) ; les sources effectives sont figées dans le bundle local `results/v228_map1024_20x10_pc_20261019_bundle`, SHA-256 d'arbre `196764d40f2b8ca5588518859669270c154c3b4ea933b6ed1e99590dd7af471f`. Ce bundle inclut AAAHogEx non versionné et reste volontairement hors Git. Manifest archivé ici.
- Smoke 42 × 1 an : complet, OpexAI et AAAHogEx actifs ; fichier JSON archivé.
- 20 × 10 : **20/20 parties exécutées et résumé JSON produit, mais banc invalide** (`Banc invalide : 1 échec(s) de santé`, code de sortie 1). Aucun crash moteur ni `PermissionError` à cette occasion.
- Santé des 20 duels : **17 `complete`, 2 `stagnation_suspect`, 1 `inactive_company`**. Graine 8191 : OpexAI, 0 véhicule, 2 gares, valeur 1 085 130 £ au dernier relevé ; AAAHogEx reste `complete`. Ce statut interdit toute qualification économique du banc ; ne pas convertir les statistiques des 19 parties saines en verdict sur les 20.

## Durée constatée (heure de Paris)

| Étape | Horodatage local | Remarque |
|---|---|---|
| Début du lanceur | 20:48:46 | Création du journal stdout ; approximation du départ |
| Smoke : manifeste | 20:48:51 | Début de la préparation figée |
| Smoke : JSON final | 20:49:17 | Smoke sain |
| 20 × 10 : manifeste | 20:49:20 | Début de la préparation figée |
| 20 × 10 : JSON final | 21:20:31 | 20 parties terminées, santé globale invalide |

**Durée du banc 20 × 10 : environ 31 min 11 s** (entre manifeste et résultat final). **Durée du lancement complet avec smoke : environ 31 min 45 s** (entre création du journal et dernier résultat). Ce sont des durées déduites des fichiers, pas une télémétrie chronométrique exacte du moteur.

## Signal économique descriptif, sans qualification

| Moyenne publiée par le harnais | OpexAI (19 retenues) | AAAHogEx (20) |
|---|---:|---:|
| Profit annuel | 298 371 £ | 55 147 354 £ |
| Valeur d'entreprise | 2 852 728 £ | 288 740 023 £ |
| Véhicules | 1,95 | 757,8 |

Ces moyennes **n'ont pas le même échantillon** du fait de l'inactivité d'OpexAI à la graine 8191 : ne pas les utiliser comme une comparaison appariée qualifiée. Le signal structurel est néanmoins frappant : OpexAI termine avec approximativement deux véhicules dans pratiquement tous les mondes, alors qu'AAAHogEx en exploite plusieurs centaines. La cause de l'incapacité d'expansion d'OpexAI sur grande carte n'a pas été établie ; ne pas attribuer l'écart à un mécanisme spécifique sans diagnostic.

## Preuves versionnées

`index.json` associe chaque fichier `results/` à sa copie compressée `.gz` avec SHA-256 et taille, et les sept fichiers sont vérifiés à la compression/décompression. Cette liste est **indépendante de l'index historique global** `evidence/review/index.json`, qui n'est pas modifié. Les originaux, le bundle figé et les journaux moteur restent dans le worktree local ; ils n'ont pas été supprimés. Le JSONL complet est archivé ici sans l'ajouter brut au dépôt.

Les autres bancs V228 (`ref1970`, `y1950`, `y1990`) relèvent de campagnes distinctes. Le `ref1970` d'origine est incomplet après une erreur d'accès JSONL ; toute nouvelle tentative doit porter un identifiant neuf et préserver ses artefacts.
