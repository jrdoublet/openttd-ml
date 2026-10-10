# P0 AIR — exposition réelle des hits C121 aux productions périmées (2026-10-09)

## Hypothèse, état et portée

Le prototype antérieur `c121_exact_prod_shadow=1` observe les villes dont
les productions PASS/MAIL ont changé mais n'atteignent pas les seuils historiques
`10 unités ET 20 %`. Ce compteur **ne suffit pas** : une ville modifiée ne
prouve pas qu'un projet AIR a effectivement utilisé son devis périmé.

Extension passive sous **le même toggle OFF par défaut** :

1. Lors de `OpexC121CatalogTownProductionBatch`, conserver en mémoire volatile
   la dernière production observée par les appels NoAI **déjà présents**.
   Ne pas avancer `C121_CATALOG_TOWN_PROD` ni `TOWN_REV` à ce titre.
2. Sur un *hit* dans `OpexC121CatalogChoice`, comparer la dernière observation
   de chacune des deux villes à la photographie encore utilisée par les
   révisions historiques. Émettre `C121_PROD_CACHE_STALE` si au moins un écart
   PASS/MAIL est non nul : âge et clé du cache, bras AIR, deux villes, quatre deltas,
   `last_score`, profit/capital/recette figurant dans le **devis mémorisé**.
3. Dédupliquer par clé de devis et signature des quatre deltas. Effacer la
   signature lorsque le devis est recalculé ou redevient sans décalage.

Aucune lecture NoAI supplémentaire, aucun rescannage des sites et moteurs,
aucune modification de la sélection, du devis ou des gardes de financement.
Les tables de télémétrie sont volatiles, non sauvegardées, et réinitialisées
avec les caches du catalogue lors de `OpexLoadSettings`. Les logs et opcodes
additionnels peuvent **néanmoins** faire bifurquer le calendrier moteur :
un smoke de neutralité stricte ou un delta de profit ON/OFF sonde n'est **pas**
une preuve causale de rendement économique.

## Ce que cette sonde ne prouve pas

- Un hit avec delta production ne prouve **ni** un écart numérique du devis
  recoté sur le même état, **ni** un reclassement AIR/RAIL, **ni** un financement
  ou une construction différents. `quoted_*` est le **devis ancien**, pas le
  contrefactuel recalculé. Une variation peut avoir un effet nul sur les
  volumes effectivement alloués si les capacités saturent.
- Seules les villes déjà revisitées par le batch de 8 villes peuvent être
  comparées. La latence entre deux lectures et le seuil de population restent.
- La déduplication permet de lire des *expositions distinctes* mais **ne compte
  pas tous les hits**. Une variation des données d'autres composants peut
  invalider un devis entre deux signatures identiques.

## Validation et porte de décision

Contrats statiques `sweeps/test_c121_exact_production.py` et
`sweeps/test_c121_exact_prod_cache_hit.py`. Au démarrage de ce travail,
`docker ps` était vide et `docker version`/`docker info` répondaient, mais
`docker run` restait bloqué **avant la création de tout conteneur**, même
avec `--pull never`, sans volumes, sur `python3 --version`. Deux clients
Docker CLI créés pour ces essais ont été arrêtés individuellement, sans
toucher au moteur ni aux tâches des autres agents.

**Statut : nouvelle sonde statique non qualifiée en Docker.** Ne pas lancer
une porte A40×3 ou adopter l'invalidation stricte avant des logs d'exposition
et, si significatifs, une confrontation *fresh vs cached* identique sur les
mêmes projets/états, comprenant impact score, cash, constructibilité et opcodes.

## Analyseur reproductible et diagnostic environnemental

Le script sweeps/analyse_c121_exact_prod_cache.py accepte
--logs log1.log log2.log --out rapport.json. Il sépare les fichiers de
parties, additionne les **mentions de villes par batch** dont une
variation est ignorée et mesure séparément les **événements de devis
périmés réellement servis**. Répartition par bras AIR et âge du devis,
quinze exemples par partie, avertissement sur logs incomplets, champs
numériques invalides et signatures dupliquées. Les montants quoted_*
restent des **devis anciens** : aucune conversion en bénéfice manqué,
profit recalculé ou occasion AIR perdue.

Tests hôte : test_analyse_c121_exact_prod_cache.py **3/3 PASS**,
test_c121_exact_prod_cache_hit.py **3/3 PASS**,
test_c121_exact_production.py **4/4 PASS**, soit **10/10 PASS**.
La vérification diff --check ne relève aucune erreur.

Recherche Docker complémentaire : docker desktop status signale
**stopping** ; wsl --list --verbose indique docker-desktop **Stopped**.
La CLI retourne encore les informations de l'image et du daemon
(29.8.2), mais une création minimale de conteneur ne se matérialise
pas dans docker ps -a. docker desktop start rapporte déjà démarré ;
docker desktop restart --timeout 45 s'achève par Failed to stop Docker
Desktop, avec backend et interfaces toujours actifs.
Il s'agit d'un **blocage du cycle de vie Desktop/WSL**, indépendant du
code NoAI. Aucun effacement, reset Docker ou arrêt forcé des processus
des autres projets n'a été effectué.

## Qualification réalisée après reprise de Docker

La section précédente décrit le blocage **au moment du premier
audit**, et non l'état final de la machine. Docker Desktop a été
rétabli par fermeture des processus Desktop déjà bloqués, après
contrôle d'absence de conteneurs et WSL arrêtée, puis relancement
standard. Les trois groupes de tests — **10/10** — ont passé sous
Docker, suivis d'un smoke 1×3 et de la porte V102 A40×3 sains.
Voir le [verdict économique et les manifests](air_c121_exact_production_20261009.md).

La sonde a détecté **1 527 utilisations dédupliquées de devis
périmés sur 28 des 40 graines témoins** ; la variante les supprime,
mais le gain de profit moyen (+22 890,4 £/an) est non significatif
(p=0,476, IC95 [−19 610 ; +67 635] £/an), verdict
**fail_primary**. Donc **sonde et variante OFF**, aucune porte B.
