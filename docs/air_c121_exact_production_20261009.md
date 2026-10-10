# P0 AIR C121 — fraîcheur exacte de la demande PASS/MAIL (9 octobre 2026)

## Problème isolé

Le calibrage global AIR par revenus observés et le remplacement du
temps de paiement forfaitaire par la durée du vol ont échoué
à leur porte économique A ; **aucun défaut adopté**.

Cette piste concerne l'**ancienneté des entrées physiques**.
Dans catalog.nut::OpexC121CatalogTownProductionBatch, C121 lit
déjà AITown.GetLastMonthProduction pour PASS et MAIL. Pourtant
sa table C121_CATALOG_TOWN_PROD ne déclenche la révision du cache
que si l'écart atteint **simultanément 10 unités et 20 %**.
Une différence de 8 unités ou de 15 % peut donc être retenue.
Dans air_catalog_c121.nut::OpexC121CatalogChoice, une cotation
cohérente avec les révisions anciennes peut survivre **365 jours**,
en transportant demande, moteur, service et économie périmés.

Le risque d'obsolescence est démontrable statiquement ; son exposition
et son coût économique ne sont **pas encore mesurés**. Les seuils
population (20 habitants / 5 %), la géométrie, les projets déjà
constitués et le rythme de balayage des villes sont hors portée.

## Deux réglages indépendants et tous deux OFF

- c121_exact_prod_shadow=1 : au cours du batch de production déjà
  payé, mesurer les villes avec production différente de la dernière
  photographie ayant invalidé le cache, mais encore sous le seuil
  historique. Log C121_PROD_EXACT_SHADOW : ignored_towns,
  ignored_pax_units, ignored_mail_units, first_town.
  **Aucune révision ni décision modifiée** ; attention, les logs et
  opcodes supplémentaires peuvent toutefois modifier le calendrier.
- c121_exact_prod_invalidation=1 : à la lecture déjà effectuée,
  invalider si pax != old.pax ou mail != old.mail. Aucune règle 10/20,
  aucun multiplicateur appris, aucune modification du batch de
  huit villes. La recomputation du choix suit le chemin historique.
  Quand OFF, la décision d'invalidation conserve son ancien critère.

Ce mécanisme n'assure pas une fraîcheur absolue entre deux lectures
de la production : il supprime **uniquement la tolérance arbitraire
au moment d'une observation existante**.

## Tests, blocage et protocole d'expérimentation

Tests de contrat sweeps/test_c121_exact_production.py :
**4/4 verts sur l'hôte**, quatre difficultés OFF, lecture
passive, exemples de variations unitaires et liaison entre
révision et entrée de cache.

**Blocage Docker dans cette session** : les tentatives docker run
avec puis sans volumes n'ont créé aucun conteneur visible et n'ont
renvoyé aucune sortie ; elles ont été interrompues. Aucun smoke
Squirrel ni résultat d'exposition ne peut être affirmé.

Une fois Docker utilisable : contrats moteur, puis smoke apparié
sur une graine avec sonde identique dans les deux bras, et
diagnostic si la première année est trop pauvre. Vérifier des
révisions effectivement ignorées, leurs coûts opcodes, puis les
devis et décisions AIR exposés à ces révisions. Seule une
variante suffisamment exposée et saine justifie une porte
V102 A40×3 (gain +4 %, Wilcoxon p<0,05, IC95 bootstrap basse >0,
garde valeur ≥−5 %), puis B20×10 uniquement si A passe.
Une seule campagne Docker à la fois, maximum 10 CPU/workers.

## Reprise Docker, exposition moteur et porte A — verdict définitif

Docker Desktop a finalement été rétabli : le daemon était bloqué
dans l'état stopping avec la distribution WSL arrêtée ; une tentative
de restart bornée a échoué. Après constat d'absence de tout
conteneur et de WSL actif, fermeture ciblée des processus Docker
Desktop bloqués, puis docker desktop start --timeout 90 : statut
running ; conteneur openttd-lab minimal sain. Aucune image ni volume
supprimé. Les **10/10 tests ciblés ont ensuite passé sous Docker**.

Smoke apparié seed42 × 3 ans, avec la même sonde passive dans les
deux bras et uniquement l'invalidation exacte comme variante :
air_c121_exact_prod_smoke_1x3_20261009_r1, bundle
54f5f9f1d83d169ee89617dc1843604d92c17d4ae90a46d05ee1a6b244ad49ac.
Deux parties complètes/saines, variante−référence +111 297 £/an,
valeur +4,288661 %. **Diagnostic seulement, une graine**.
Les journaux montrent 113 événements de devis périmés
effectivement servis par le cache de la référence, tous hubsite ;
0 événement de cette nature sous invalidation exacte.

Porte A V102 pré-enregistrée : **air_c121_exact_prod_gateA_40x3_20261009_r1**,
40 graines × 3 ans, 80/80 parties complètes et saines, une
campagne Docker à la fois. Même bundle
54f5f9f1d83d169ee89617dc1843604d92c17d4ae90a46d05ee1a6b244ad49ac,
manifest 79755a48f208a90392619b43c97372c69e047aa568533f366a5049640f90fa4d,
image openttd-lab sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659.
La référence utilise c121_exact_prod_shadow=1 et
c121_exact_prod_invalidation=0 ; la variante garde la même sonde
mais active l'invalidation à 1. Aucune correction de délai de
paiement ni autre réglage expérimental activés pour cet essai.

Profit annuel terminal variante−référence **+22 890,4 £/an en
moyenne**, médiane **+6 260,5 £/an**, **21/19/0** victoires/défaites/égalités,
Wilcoxon bilatéral **p=0,4762078**, IC95 bootstrap de la
moyenne **[−19 610,2 ; +67 635,375] £/an**, seuil utile
pré-enregistré **+77 883,764 £/an** (4 % de la référence).
Valeur de compagnie ratio des moyennes **+0,701464 %** :
garde −5 % tenue, mais **fail_primary** (gain non démontré).

Diagnostic des 80 journaux via
sweeps/analyse_c121_exact_prod_cache.py :
**1 527 événements de hits périmés en référence dans 28/40
graines**, contre **0 en variante** ; ventilation référence
**1 486 hubsite, 24 newpair, 17 hubhub** ; âges :
**791 jour 0, 505 de 1 à 29 jours, 231 à partir de 30 jours**.
Les mentions de villes produisant un changement ignoré
dans les batches sont **128 848 référence contre 34 673 variante**.
Ces nombres sont des mentions répétées, pas des villes uniques,
et les hits sont dédupliqués par clé/signature, pas un comptage
de toutes les consultations. Ils prouvent l'**exposition de
devis périmés**, mais non leur écart recoté au même état.
Rapport : results/air_c121_exact_prod_gateA_40x3_20261009_r1_exposure.json.
L'écart économique entre bras inclut l'évolution dynamique
des décisions et du calendrier d'exécution.

**Décision : REJET économique de l'invalidation exacte ; conserver
c121_exact_prod_invalidation=0 et c121_exact_prod_shadow=0 par défaut.
Ne pas lancer la porte B20×10.** L'obsolescence de production est
un défaut de fidélité du modèle bien exposé, mais retirer à lui
seul le seuil 10/20 n'améliore pas le portefeuille de façon
statistiquement établie à trois ans. Si cette piste est rouverte,
la suite rigoureuse est une recotation fresh/cached d'un même
projet/instant, puis une preuve sur score/financement/constructibilité,
sans seuil compensatoire appris sur les mêmes graines.
