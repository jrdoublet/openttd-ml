# P0 AIR C121 — bilan de session et coût en opcodes (10 octobre 2026)

## Objectif, intervention, nombres magiques

Le catalogue AIR lit déjà la production mensuelle PASS/MAIL de chaque ville,
mais le chemin historique invalide son devis uniquement si une variation atteint
SIMULTANÉMENT 10 unités et 20 % sur un cargo. Un devis peut survivre jusqu'à
365 jours si aucune autre révision ne le déclare obsolète.

Deux réglages expérimentaux, indépendants et désactivés par défaut :

- c121_exact_prod_invalidation : lorsque activé, réviser le devis dès qu'une
  production PASS ou MAIL effectivement relue diffère de sa référence ;
- c121_exact_prod_shadow : mesurer les variations ignorées et les hits de devis
  servis malgré une production différente. La sonde est passive pour les
  décisions, mais consomme des opcodes et produit des journaux.

Deux nombres magiques (10 unités et 20 %) sont ainsi CONTOURNÉS dans la
variante ; ils ne sont PAS retirés du code ni du comportement historique.
Le balayage de huit villes, les seuils de population 20 habitants / 5 % et
l'expiration du cache restent inchangés. Aucun coefficient correcteur ajouté.

## Réalisations

1. Implémentation C121 isolée dans catalog.nut, globals_pre.nut, settings.nut
   et info.nut, paramétrée OFF sur les quatre difficultés.
2. Sonde C121_PROD_EXACT_SHADOW (villes dont la production change sous les
   seuils historiques), puis C121_PROD_CACHE_STALE sur les vrais hits de devis,
   avec signature dédupliquée, date, âge, type de projet, écarts et ancien
   devis. Pas de nouvelle lecture NoAI ni de recalcul pour cette sonde.
3. Analyseur sweeps/analyse_c121_exact_prod_cache.py et tests de contrats.
4. Docker Desktop rétabli après blocage en état stopping (WSL arrêté) sans
   purge d'images ni de volumes ; conteneur minimal et tests ensuite exécutés.

Commits expérimentaux isolés sur codex/p0-air-exact-production :
351e3aa (premier prototype), 10c0227 (sonde des hits et analyseur),
272e6a7 (verdict initial A40x3). Le présent bilan complète ces commits.

## Contrats et smoke

- Test de production exacte : 4/4 PASS sous Docker.
- Test de la sonde des hits : 3/3 PASS sous Docker.
- Test de l'analyseur : 3/3 PASS sous Docker.
- Total : 10/10 contrats ciblés verts.
- Smoke seed42 x 3 ans, deux parties saines, +111 297 GBP/an variante moins
  référence, mais ce résultat sur une seule graine est purement diagnostic.
  Exposition : 113 hits périmés de devis en référence, zéro en variante.

## Porte A V102 — 40 graines x 3 ans

Campagne : air_c121_exact_prod_gateA_40x3_20261009_r1.
Bundle SHA-256 : 54f5f9f1d83d169ee89617dc1843604d92c17d4ae90a46d05ee1a6b244ad49ac.
Les deux bras ont c121_exact_prod_shadow=1 ; l'invalidation vaut 0 en
référence et 1 en variante. 40/40 paires complètes et saines.

| Mesure, variante moins référence | Résultat |
|---|---:|
| Profit annuel terminal moyen | +22 890,4 GBP/an |
| Profit médian | +6 260,5 GBP/an |
| Victoires / défaites / égalités | 21 / 19 / 0 |
| Wilcoxon bilatéral | p = 0,4762078 |
| IC95 bootstrap du gain moyen | [-19 610,2 ; +67 635,375] GBP/an |
| Gain utile exigé (4 % référence) | +77 883,764 GBP/an |
| Valeur d'entreprise, ratio des moyennes | +0,701464 % |
| Verdict | fail_primary |

Sonde : 1 527 événements de hits périmés sur 28/40 graines en référence,
contre zéro dans la variante. Pas de porte B.

## Vérification supplémentaire demandée — 40 graines x 5 ans

Campagne : air_c121_exact_prod_40x5_20261009_r1.
Bundle SHA-256 : e7814139d3e349708a768c0d6d90606d38575ceabcb5223cd1214ae57c8efbfc.
Manifest SHA-256 : 642231bf552f212ebd368b9146ea2ef3e518df1781ac47fccbce7fce34d7f163.
Image openttd-lab SHA-256 :
f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659.
Limites : 10 CPU / 10 workers, une seule campagne à la fois.
80/80 parties complètes, aucune erreur moteur.

| Mesure, variante moins référence | Résultat |
|---|---:|
| Profit annuel terminal moyen | -20 745,9 GBP/an |
| Profit médian | -10 249,5 GBP/an |
| Victoires / défaites / égalités | 19 / 21 / 0 |
| Wilcoxon bilatéral | p = 0,4762078 |
| IC95 bootstrap du gain moyen | [-83 473,8 ; +43 590,1] GBP/an |
| Gain utile exigé (4 % référence) | +78 077,371 GBP/an |
| Valeur d'entreprise, ratio des moyennes | -0,452233 % |
| Verdict | fail_primary |

Sonde : 5 439 événements dédupliqués de hits périmés sur 40/40 graines
témoins contre zéro en variante, dont 5 385 hubsite, 30 hubhub et
24 newpair. Mentions répétées dans les batches :
141 866 référence contre 45 728 variante.

Sur ces 40 cartes OpexAI reste sous AAAHogEx en profit annuel terminal
sur les 40 graines (environ 1,952 M GBP/an contre 3,353 M GBP/an).
Cette observation du duel n'est pas le delta entre les deux politiques.

Les bundles 40x3 et 40x5 DIFFERENT : la comparaison OFF/ON est
causale à l'intérieur de chaque bundle, mais l'écart des deux résultats
ne mesure pas causalement deux années additionnelles sur source identique.

## Audit rétrospectif des opcodes, uniquement sur 40x5

Les JSON du banc ont observé les finances, mais les champs globaux
observed_opcodes_total et selection_kopcodes_total sont NULS pour
toutes les parties. Aucun total d'opcodes de l'IA n'est disponible.

Les logs AIR_PLAN_PERF permettent une MESURE PARTIELLE des seuls
scans de planification AIR terminés. Sommes de ces événements
sur les 40 parties de chaque bras :

| Compteur instrumenté | Historique | Invalidation exacte | Delta |
|---|---:|---:|---:|
| Événements AIR_PLAN_PERF terminés | 155 | 154 | -1 |
| AIR total_ops | 1 064 436 206 | 1 051 558 178 | -12 878 028 (-1,21 %) |
| AIR ops_eval | 1 004 093 048 | 988 426 206 | -15 666 842 (-1,56 %) |
| C121 demand_ops | 512 983 029 | 509 887 803 | -3 095 226 (-0,60 %) |
| C121 calls | 51 591 | 51 578 | -13 (-0,03 %) |
| C121 endpoint_misses | 11 484 | 13 608 | +2 124 (+18,50 %) |

Ces mesures ne couvrent NI tous les opcodes de l'IA, NI le coût de
OpexC121CatalogTownProductionBatch, NI la sonde sur ses hits hors
finalisation, NI les coûts indirects de renouvellement du catalogue.
Les scans et les trajectoires changent entre bras ; le -1,21 % des
scans AIR n'est pas un gain d'opcodes attribuable à l'invalidation.
De même, +18,50 % de misses endpoint n'est pas une hausse de 18,50 %
du coût total. Les logs et l'analyseur ne permettent pas de séparer
proprement coût intrinsèque sonde vs recalculs causés par la politique.

Une mesure rigoureuse réclame un compteur global enveloppant les
traitements comparables, des décomptes cache hit/miss et un contrôle
avec sonde ON/OFF à politique fixe, de préférence par snapshots d'état
et mesures en opcodes par décision. Aucun chiffre forfaitaire estimé.

## Décision et preuves

Les deux bancs échouent au seuil de gain utile et à la significativité,
malgré l'exposition réelle du problème de cache :
**garder les deux réglages OFF. Aucune porte B, aucune adoption.**

Une suite défendable compare, sur un même projet et un même état, le
devis frais au devis en cache, puis les rangs intermodaux, la
finançabilité et la constructibilité. Aucun nouveau facteur arbitraire
ou réglage opportuniste n'est justifié par ces résultats.

Résultats locaux non versionnés dans results/ :

- air_c121_exact_prod_gateA_40x3_20261009_r1.json
- air_c121_exact_prod_gateA_40x3_20261009_r1_exposure.json
- air_c121_exact_prod_40x5_20261009_r1.json
- air_c121_exact_prod_40x5_20261009_r1_exposure.json

## Piste conservée : seuils statistiques plutôt que 10 unités ET 20 %

**Statut : proposition à étudier, pas un comportement adopté.** Les résultats
existants sont *compatibles* avec un effet économique faible : les différences
ne sont pas statistiquement significatives sur 40x3 ou 40x5. Ils ne démontrent
pourtant **pas une équivalence économique** (l'IC95 du 40x5 s'étend de
-83 474 à +43 590 GBP/an), et les opcodes **globaux** n'ont pas été mesurés.
Le -1,21 % concerne uniquement les scans AIR terminés. Il serait donc faux
de déclarer dès maintenant « neutre et gratuit en opcodes ».

**Si** une mesure complémentaire démontre la non-régression économique dans
une marge pratique pré-déclarée ET un surcoût opcode nul ou négligeable
sur un périmètre global comparable, le remplacement des seuils fixes devient
une piste intéressante de suppression de nombres magiques, même sans hausse
de profit. Ce serait une décision de simplification/fidélité du modèle,
pas un succès du protocole V102 de gain économique.

### Proposition 1 — bruit de production estimé

Pour chaque ville et cargo PASS/MAIL, accumuler les observations mensuelles
réellement lues, en distinguant **niveau** et **changements** de production.
Estimer la dispersion des changements avec une variance empirique
(algorithme en ligne de Welford), ou une mesure robuste comme la MAD si
les variations sont très asymétriques. Au lieu de « 10 ET 20 % », comparer
la variation par rapport à la dernière base du devis à la variabilité
historique **locale**, avec une incertitude qui tient compte du nombre
d'observations disponibles et de la dérive temporelle. Ne pas mélanger
PASS et MAIL : chaque cargo a sa propre échelle et son propre bruit.

**Attention :** remplacer 20 % par « 1 sigma » ou « 2 sigmas » ne supprimerait
pas vraiment l'arbitraire ; on introduirait seulement un autre coefficient
sans preuve. Une valeur élevée de sigma peut aussi masquer une rupture
économique réelle, et une série courte ou de variance nulle peut rendre
l'estimation inutilisable. Un prototype doit expliciter son risque de
faux-négatif et prévoir un repli sûr vers l'invalidation exacte en l'absence
d'observations suffisantes. Il faut étudier l'autocorrélation et la fréquence
réelle du batch de huit villes : les échantillons ne sont pas forcément des
mois consécutifs ni indépendants.

### Proposition 2 — seuil de pertinence économique, préférable à terme

La question opérationnelle est : **ce changement de production peut-il
modifier la décision d'investissement ?** Un écart statistiquement inhabituel
ne suffit pas si l'avion est déjà saturé ou si le même projet garde son rang.

1. Sur des cotations appariées au **même état de carte**, isoler la variation
   de production en maintenant moteur, infrastructure, stations, concurrence,
   calendrier et trésorerie identiques. Mesurer le delta de recette, de profit
   prévu et, surtout, le changement de rang, d'admission et de financement.
2. Chercher une borne **conservatrice** issue des volumes transportables,
   capacités et tarifs réels, permettant d'affirmer qu'une variation n'aurait
   aucun effet sur les choix. Réutiliser le devis en cache seulement si cette
   absence d'effet est démontrable ; sinon déclencher le recalcul ordinaire.
   Une borne ne doit pas supposer que le choix de moteur ou de nombre d'avions
   est continu : une discontinuité exige le recalcul.
3. Comparer sur les mêmes graines les trois politiques
   (ancienne tolérance 10/20 ; invalidation exacte ; méthode statistique ou
   économique), avec le même instrumentation, un total d'opcodes global et
   le nombre de recotations utiles/inutiles. Ne pas choisir un sigma « gagnant »
   après coup sur les graines de validation.

**Ordre recommandé :** utiliser les écarts-types en *shadow* pour caractériser
la variabilité observée et diagnostiquer les faux seuils ; privilégier ensuite
une invalidation fondée sur une borne de **pertinence économique vérifiable**.
L'absence de gain statistique de l'invalidation exacte ne valide pas d'office
un seuil adaptatif, et aucune de ces propositions ne doit changer les défauts
sans qualification indépendante.
