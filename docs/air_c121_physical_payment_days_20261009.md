# P0 AIR — âge physique du cargo au paiement C121 (09/10/2026)

## Écart physique isolé

La correction globale de recettes AIR par apprentissage a été **rejetée**
à sa porte A 40×5 : profit terminal −20 488,4 £/an en moyenne,
p=0,695, IC95 [−109 677 ; +73 409]. Ne pas la réactiver.

Dans C121, deux durées différentes coexistent pour la même ligne :

- Le paiement PASS/MAIL prend la durée fournie par
  OpexC119AirIncomeDays, fondée sur
  ((distance + 30) × 664) / (speed × 24 × dayLengthFactor).
  Le terme **+30** n'est relié à aucune géométrie de l'aéroport.
- OpexC121AirTripModel connaît déjà physicalOneWayDays =
  flightDays + maneuverDays, calculé à partir de la distance, vitesse,
  types et dimensions des deux aéroports et vitesse de taxi.

La variante, réglage **air_c121_physical_payment_days=0** aux quatre
difficultés, utilise sous ON **ceil(physicalOneWayDays)** (minimum un
jour, unité entière requise par AICargo.GetCargoIncome). Elle ne
modifie aucun trafic, partage d'aéroport, flotte, amortissement,
nombre d'avions ou coefficient de réalisation. Les cinq chemins
C121 concernés — cotation normale, one-or-two fusionnée, matching
des contextes, borne de moteur, shortcut — sont synchronisés pour
éviter des revenus incompatibles entre moteur et projet.

Limite : il s'agit du temps **physique prédit**, et non des jours
réellement facturés par OpenTTD ; attente avant chargement, route
effective, congestion non observée et transferts ne sont pas captés.
Les délais appris aux hubs ne sont pas ajoutés au prix sous ce
réglage : leur imputabilité au cargo n'a pas été démontrée.

Sources API : https://docs.openttd.org/ai-api/classAICargo
et https://wiki.openttd.org/en/Manual/Production%20delivery.

## Protocole déclaré avant la qualification

Tests ciblés Docker, smoke apparié OFF/ON graine42 × 1 an et preuve
d'exposition dans les journaux C121_BUILD. Puis porte A V102 sur
**40 graines × 3 ans** avec exactement les mêmes snapshots/bundles,
référence OpexAI[air_c121_physical_payment_days=0] et variante
OpexAI[air_c121_physical_payment_days=1]. Primaire profit_year
terminal ; seuil gain +4 %, Wilcoxon bilatéral p<0,05, IC95
bootstrap inférieur >0 et valeur d'entreprise ≥−5 %.
Porte B 20×10 non_erosion **seulement après PASS A**.
Max 10 CPU/10 workers, aucune campagne Docker en parallèle.
Ne pas changer le nombre de jours ou le protocole après les résultats.

## Prévalidation

Contrats sweeps/test_air_c121_physical_payment_days.py :
**5/5 verts sur hôte et sous Docker**, diff --check propre.

Smoke air_c121_payment_days_smoke_1x1_20261009, bundle
e7b31b6a708a5d368dd011cd632ab17077f96435c735ca04f41f87733c9a6ae1,
**2/2 parties complètes**. Les premières lignes C121_BUILD
montrent OFF→ON de income_days : **28→41 jours** pour
physical_one_way_days=40,312653 ; **18→31 jours** pour 30,425644.
Delta profit annuel **+2 £**, valeur **−1,64 %**,
verdict diagnostic_only (une graine, premier exercice partiel).

## Porte A et décision

Porte A r1 : air_c121_payment_days_gateA_40x3_20261009_r1 ;
bundle 302ce7e358a498c447825e4dab9981717fa337532c3b6e40b81c3af69d7a7ab6,
manifest 823670e48072ba65a80b818c3577acf5ebc9972f14cc00a5a6b6d673e674ed51.
**40/40 paires et 80/80 parties saines**, variante−référence :
profit moyen +24 516 £/an, médiane **−10 712 £/an**,
19V/21D, Wilcoxon p=0,7046877,
IC95 [−45 252,625 ; +98 020,875] £/an,
valeur +2,392921 %, **fail_primary**.

**Limite majeure de qualification** : pendant cette porte A, un
second conteneur Docker du chantier ROAD
(p0_road_finance_smoke_20261009_r3) a été actif en parallèle.
Le budget CPU et les reprises coopératives peuvent modifier la
trajectoire d'OpexAI : **r1 ne doit pas fonder une adoption**, même
avec 80 parties saines. Une répétition **sans chevauchement**,
mêmes 40 graines et mêmes critères, est nécessaire pour conclure
sans cette réserve. Ne pas adapter le modèle aux résultats r1.

### Répétition isolée r2 — verdict retenu

Porte A air_c121_payment_days_gateA_40x3_20261009_r2_isolated,
bundle 686fe965c7a5ea4bbfb67ed80d83340cd75bbf0ef1f4826cadc538924ff4dfcf,
manifest a1b2c3c39b449757ca0de348b5a5b33d307ea276072583b899a6986ce170cafc.
Au lancement, aucun autre conteneur Docker n'était présent ; seule
la campagne AIR a été observée pendant cette nouvelle porte.

**40/40 paires saines, 80/80 parties complètes**. Delta variante :
profit terminal moyen **+23 835 £/an**, médiane **−5 849 £/an**,
19V/21D, p de Wilcoxon bilatéral **0,71459744**,
IC95 bootstrap **[−45 455,875 ; +96 706,15] £/an**.
Le seuil prédéfini de gain utile était **+77 523,404 £/an**.
La valeur d'entreprise progresse de **+2,362248 %** (ratio des
moyennes) et satisfait la garde −5 %. Le banc conclut
**fail_primary**. **Pas de porte B 20×10**.

Le bundle r2 diffère de r1 parce que le répertoire partagé a
évolué entre les essais : il ne faut pas interpréter la proximité
des résultats comme une répétition bit-identique de source.
En revanche, chaque porte applique les **mêmes snapshots/sources
et paramètres aux deux bras** à l'intérieur de son bundle,
et toutes deux échouent au critère primaire.

**Décision ferme : REJET du changement de délai de paiement, défaut
air_c121_physical_payment_days=0 conservé**. L'anomalie physique
C119 versus C121 est reproduite ; elle ne suffit pas à prouver un
meilleur arbitrage d'investissements. Les échecs des correctifs
globaux précédents ne motivent pas de rajouter un coefficient.

### Prochaine expérience distincte — sans modifier les seuils à l'aveugle

L'audit physique identifie une cause d'obsolescence à mesurer :
air_catalog_c121.nut réutilise des devis jusqu'à 365 jours, alors
que catalog.nut::OpexC121CatalogTownProductionBatch lit déjà la
production mensuelle PASS/MAIL et n'invalide que si l'écart est
simultanément ≥10 unités et ≥20 %. Les révisions de population
ont elles aussi des seuils 20 habitants et 5 %. Une cotation
en cache peut donc ne plus décrire le trafic **physiquement
observé**. Cette hypothèse reste à prouver : instrumenter une
comparaison *fresh versus cached* sur **le même projet au même
état de carte**, mesurer divergences de prix/rang/caisse et opcodes,
puis seulement isoler un correctif OFF par défaut. Ne pas cumuler
ce test avec le délai de paiement rejeté.
