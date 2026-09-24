# V92 — choix d'un service aérien

État au 2026-09-24 : **implémenté, défaut 0**. Réglage `v92_air_service_choice`.
La fiche est le numéro 31 : 29 est le pathfinder V90, 30 est V91.

## Règle

Pour chaque route, chaque moteur compatible est chiffré pour n = 1…plafond (le même 3/4/6 que le dimensionnement historique). On retient le n au meilleur profit annuel. Le `maxCapital` reçu par `OpexAirChooseRoutePlane` est transmis à `OpexAirEconomics`. La génération du portefeuille appelle déjà `OpexAirPlans` avec 0 : le filtre de caisse du portefeuille reste alors le seul plafond. Le chemin qui passe une caisse positive le conserve.

Deux projets sortent, pour les mêmes villes :

1. ce service ;
2. le meilleur profit à **un** appareil dont le prix ne dépasse pas le gros jet le moins cher encore en lice (sur un petit aéroport, le moins cher de la liste).

Si les deux sont le même moteur et le même nombre, un seul projet est émis. La construction de l'un retire l'autre (`v92PairKey`, et une ligne déjà ouverte entre ces villes). `V92_CLOSED_PAIRS` n'est pas sauvegardé. Après rechargement, les lignes vivantes ferment encore la paire par `originA`/`originB`. Une paire dont la ligne a été mise au rebut se rouvre au chargement, et reste fermée tant que la partie continue.

Le courrier connu est la soute lue sur un avion **de cette compagnie** (`AIVehicleList` ne voit pas les autres), ramenée à la proportion de remplissage de la cabine. C'est une hypothèse : les villes produisent moins de courrier que de passagers, et une soute réelle souvent supérieure à 15 % de la capacité passagers peut surestimer le revenu. Sans mesure, le forfait de 15 % reste. L'amortissement de l'appareil est `prix / AIEngine.GetMaxAge` au lieu de `prix / 20`.

Tant que V92 est actif, ce choix ne passe ni par le mémo C80, ni par C82, ni par le dimensionnement C84, ni par la frontière C85.

Au renforcement, « un appareil de plus du moteur actuel » est comparé au meilleur autre service. S'il gagne, la flotte est envoyée au hangar puis remplacée. Les identifiants déjà envoyés sont mémorisés sur la ligne (`v92SentToHangar`) : `SendVehicleToDepot` n'est pas rappelé. Chaque passe de flotte reprend une ligne qui a `v92PendingEngine`, même si elle n'est plus candidate à la croissance. Le rebut d'une ligne et la retraite d'un avion non rentable ne renvoient pas ces avions et ne les retirent pas de la flotte pendant l'échange. La caisse et `AIEngine.IsBuildable` sont revérifiés au moment de l'échange, avant toute vente. Si l'achat du nouveau moteur échoue, l'ancien est racheté. Si ce rachat échoue aussi, la ligne ne conserve pas les identifiants vendus. Un remplacement n'est pas rejoué avant deux ans. Le nombre acheté ne dépasse pas `OpexAirCadenceCap`.

La comparaison ignore l'arrêt de la ligne pendant l'échange et la perte à la revente. « Garder le moteur actuel » est chiffré à n+1 avions, pas à son meilleur nombre. Ce sont des points à mesurer, pas des garde-fous déjà chiffrés.

Chaque paire chiffre chaque moteur plusieurs fois et peut produire deux projets. Le surcoût d'opcodes est à lire avec `AIR_PLAN_PERF` avant tout 5×6.

Aucun nom d'avion, aucun EngineID, aucun seuil de places.

## Hors de ce réglage

À 0, les décisions d'avion restent celles d'avant : un appareil, forfait courrier 15 %, amortissement sur 20 ans, clonage du même moteur. Le catalogue appelle quand même `GetMaxAge` et pose `mailCapacity`, et le revenu passe par `OpexAirFarePerPax`. Les décisions sont les mêmes. La trajectoire peut dériver, parce que la consommation d'opcodes n'est pas identique.

Smoke 1×1, graine 42, `v92_air_service_choice=1` : partie jusqu'au 1971-01-01, `run_ok`, compteurs physiques valides (`results/smoke_v92_air_service_20260924.json`). Pas de diagnostic 5×6.
