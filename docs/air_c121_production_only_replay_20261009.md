# P0 AIR C121 — replay physique PASS/MAIL à état constant (09/10/2026)

## Décision antérieure et question

L'invalidation stricte des révisions de production PASS/MAIL a échoué à
la porte A40×3 : profit_year moyen +22 890,4 £/an, Wilcoxon p=0,4762,
IC95 bootstrap [−19 610,2 ; +67 635,375], seuil utile +77 883,764 £/an,
valeur +0,701464 %. Elle reste OFF ; aucune porte B.

La sonde précédente c121_quote_refresh_delta_shadow comparait le devis
historique et son successeur sur un miss town réel. Cela ne permettait pas
d'isoler la production : les ratings, stations, réserves, couvertures,
géométrie, durée, tarifs, démographie et flotte pouvaient avoir changé.

## Expérience contrôlée construite, OFF par défaut

c121_production_only_replay_shadow=1 (défaut **0** dans les quatre profils)
opère **uniquement** lorsqu'un choix de catalogue C121 est déjà recalculé
à cause d'une révision de ville (reason == town). Aucune nouvelle
invalidation ni modification de la sélection, du portefeuille ou du cash.

Au terme du recalcul normal :

1. Retenir le devis C121 précédent et le nouveau c121Demand. Si les
   quatre volumes de production brute PASS/MAIL sont identiques, ne rien faire.
2. Réévaluer **l'avion choisi et son nombre d'appareils courant fixe** à
   partir du plan normal. Vérifier la parité exacte du profit, des recettes
   et du capital avec le devis courant effectivement publié. En cas de
   différence (notamment le passage d'un mode moteur fusionné), produire
   status=control_mismatch et **ne pas conclure**.
3. Cloner superficiellement le plan, sa table de demande et ses invariants
   c121EngineStatic. Remplacer seulement les quatre volumes sources par
   oldEntry.demand (pax/mail Produced A/B). Les reprojecter sur les
   **tuiles productrices couvertes et le nombre de routes du plan actuel** :
   raw = oldProduction × min(unionTiles,townTiles) / townTiles lorsque
   townTiles>0, avec troncature entière, puis allocated=raw/routeDiv.
   Formules déjà présentes dans OpexAirB9TownUnionMonthly.
4. Réévaluer les quatre existing{Pax,Mail}Before{A,B} à partir des valeurs
   de station, compétition, cadence et runway **actuelles**. Les champs du
   plan réel demeurent immuables.
5. Réévaluer seulement le **même moteur au même N**, en conservant la carte,
   la géométrie, les ratings de gare observés, les règles physiques,
   le prix et les capacités. Les ratings **projetés** de la future ligne
   restent endogènes et sont recalculés lorsque les productions changent.
   Journaliser C121_PRODUCTION_ONLY_REPLAY status=compared avec le revenu,
   profit, capital, cargo transporté, cannibalisation, score C121 et viabilité
   prévus sur les deux volumes.

Il ne s'agit **pas** d'une recherche générale du moteur optimal en replay :
aucun scan moteur supplémentaire n'est exécuté. La date du jeu est
contrôlée avant et après ces calculs, pour écarter un saut de calendrier
pendant le calcul. L'instrumentation peut néanmoins ajouter des opcodes
et influencer le temps d'exécution ; elle n'a pas à être activée en production.

Cette paire de devis a une interprétation causale **locale** : dans
la fonction économique C121, à géométrie, état des stations, compétition,
moteur et N *fixes*, quel effet produirait le remplacement du seul volume
source PASS/MAIL ? Il s'agit de l'effet sur **un candidat** dans **un état**
et non de l'impact net sur profit_year, le classement AIR/RAIL ou la
constructibilité d'une ligne différente.

## Méthode de qualification

Tests de contrat :

- sweeps/test_c121_production_only_replay.py : OFF, insertion sur miss
  naturel, clones, source de production, division entière, reconstitution
  de la cannibalisation, témoin de parité, absence de scans/revisions forcés.
- sweeps/test_analyse_c121_production_only_replay.py : parsing des logs,
  parité, sous-comptes, absence d'extrapolation au profit réalisé.

Analyseur : python sweeps/analyse_c121_production_only_replay.py
--logs logs... --out rapport.json

À la date de développement, un **autre conteneur Docker**
elated_curie était déjà engagé dans
air_c121_exact_prod_40x5_20261009_r1 à 10 workers.
Pour éviter le chevauchement, les tests Docker et le smoke de cette
nouvelle sonde sont différés jusqu'à Docker libre. Les tests hôte sont
passés (4/4 contrats + 2/2 analyseur). Ne pas lancer A40×3 sur cette
sonde passive : elle ne modifie pas la politique.

## Règle de décision

Le signal recherché est une différence **non nulle et validée par le
témoin de parité**, idéalement proche d'un seuil réel
(profitAnnual>0 ou capital disponible), sans coefficient empirique.

Les cas control_mismatch, les dates incohérentes ou les entrées manquantes
ne comptent jamais comme une preuve du mécanisme. Une exposition de
plusieurs cotations n'établit pas automatiquement que leur classement
ou leur décision d'achat ont changé.

**Statut : diagnostic expérimental OFF, pas de correctif adopté ni B.**
