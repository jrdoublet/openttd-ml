# C67.2 — fixture de contrat

Cette IA de diagnostic charge le **même** `terrain_map.nut` que le service OpexAI.
État au 30 septembre : C67.3–.6 livrés, sans consommateur métier adopté ;
voir [contrat](../../../docs/c67_cartographie_contrat.md) et [tâches](../../../docs/taches.md).
`diag_c67_terrain.py` copie ses sources et `budget.nut` dans un dossier de campagne
unique, enregistre leurs SHA256 puis réutilise configuration, runtime et nettoyage
de `bench_v2.py`. Le diagnostic ne modifie pas les `require` de `main.nut` ;
le service terrain y est déjà chargé dans le code courant.

La fixture exécute les cas synthétiques dans la VM Squirrel du moteur : agrégats d'un
bloc de bord, inconnus, reprise, LRU, priorité, file pleine et invalidation en cours.
Elle appelle ensuite les API réelles sur un bloc intérieur en 5×5 et en 10×10.
Le panneau final `C67|PASS` n'est produit qu'après toutes les assertions.
Le sommeil final appartient à l'IA de test inactive, pas au service de cartographie.

Depuis la racine du worktree, après vérification du contexte Docker, de l'image,
du cache et du montage local réellement visible par le daemon :

```powershell
python -X utf8 -m unittest discover -s sweeps -p test_c67_terrain.py -v
docker run --rm --cpus=3 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab -v "${PWD}:/work" -w /work openttd-lab python3 sweeps/diag_c67_terrain.py --out results/c67_terrain_smoke_identifiant_unique.json
```

Le smoke est fixe : graine 42, un an, un worker, aucune bibliothèque tierce requise.
Une sortie existante est refusée. Le contrôle exige douze mois distincts de 1970,
l'horizon de décembre, le marqueur au dernier checkpoint et aucune erreur moteur/NoAI.
L'absence d'activité économique est normale pour cette fixture et n'est pas qualifiée
comme un gel. JSON, JSONL et copie des sources sont conservés sous le préfixe choisi.

Les tests Python vérifient le gel des sources et la collecte ; **ils ne compilent ni
n'exécutent le Squirrel**. Le smoke ne remplace pas les mesures mémoire/opcodes de C67.3,
ni Save/Load et l'ordonnancement de C67.4. Aucun gain économique n'est recherché ici.
