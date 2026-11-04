# Diagnostic & Implémentation ROAD1Y_FREIGHT (Fret routier OpexAI)

## 1. Mesures comparatives 1970-1972 (Graines 100, 613553, 781335)

### Côté AAAHogEx (Charbon routier)
- **Graine 100** :
  - 1971-06-03 : Cafingbridge (dist 73, prod 130 t/m), 16 camions prévus. Fin 1972 : 25 camions, +51 032 £ (2 041 £/camion).
  - 1972-08 à 11 : 4 nouvelles lignes ouvertes (Wonnton dist 193, Sinfingfield dist 207, Chondwood dist 93, Flindston dist 177).
  - Total AAA charbon fin 1972 : 4 lignes actives, 37 camions, 50 431 £ de profit.
- **Graine 613553** :
  - 1971-09-27 : Kenfingbourne (dist 76, prod 210 t/m). Fin 1972 : 23 camions, +57 059 £ (2 481 £/camion).
  - 1972-07 à 09 : 4 lignes ouvertes (Tenfingpool dist 81, Flindingham dist 112, Pufingway dist 79, Harwood dist 109).
  - Total AAA charbon fin 1972 : 5 lignes, 56 camions, 67 020 £ de profit.
- **Graine 781335** :
  - 1972-07 : Slentburg (dist 69, prod 130 t/m, 11 camions, +5 626 £) et Tendinghead (dist 66, prod 130 t/m, 10 camions, +4 646 £).
  - Total AAA charbon fin 1972 : 2 lignes, 21 camions, 10 272 £ de profit.
- **Moyenne 3 graines AAA charbon en 1972** : ~42,6 k£/an avec des parcs de 10 à 25 camions par ligne.

### Côté OpexAI (Candidats et éviction dans le portefeuille)
- Génération : Opex énumère bien les mines de charbon (`OpexRoadFreightCandidates` dans `candidates.nut:2886`).
  Exemple graine 100 : Cafingbridge -> Honnville Power Station (dist 73, prod 130 t/m, 84 t/m offertes).
- Goulot d'étranglement : `OpexRoadLineEconomics` plafonne les véhicules fret à `OpexRoadPhysicalVehicleCap(1, 1) = 2`.
  À 2 camions Balogh (capacité 20 t), la capacité de transport n'est que de ~20 t/mois sur 84 t/mois offertes.
- Évaluation : profit estimé plafonné à ~1 800 £/an (au lieu de 38 000 - 51 000 £/an).
  Score portefeuille (`fundScore`) = ~50 pour le charbon, contre 250 - 350 pour les lignes PAX (8-16 bus).
- Éviction mois par mois : relégué au-delà du 50e rang dans le portefeuille, le fret n'est jamais financé.
  En 1970-1972, Opex n'a ouvert aucune ligne de charbon sur les 3 graines (profit charbon = 0 £).

## 2. Cause racine et impact financier
- **Fichier et ligne** : `ai/OpexAI/economy.nut:778-792` (`OpexRoadLineEconomics`).
  La dérogation de flotte (`fleetCapOverride` ou `ROAD1Y_PAX_ECONOMY`) n'était appliquée qu'à `kind == "pax"`.
  Le fret restait bridé au plafond physique minimal de 2 camions.
- **Manque à gagner identifié** : ~43 k£/an en moyenne en 1972 (~51 k£ sur graine 100, ~67 k£ sur graine 613553).

## 3. Implémentation du correctif (`road1y_freight`)
- Nouveau réglage entier `road1y_freight` (borne 0..30, défaut 0) déclaré dans `globals_pre.nut` et `info.nut`.
- Lu et borné (0..30), puis forcé à 0 hors route seule (`!road1yRoadOnly`) dans `OpexLoadSettings` et `OpexLoadBusDistrictSettings` de `settings.nut`.
- Dans `ai/OpexAI/economy.nut` (`OpexRoadLineEconomics`) :
  Si `ROAD1Y_FREIGHT > 0 && kind == "freight"`, le plafond de flotte est porté jusqu'à `ROAD1Y_FREIGHT`.
  À 0 (défaut), le comportement historique (plafond à 2 camions) reste strictement préservé.
- Fixtures `road100_bus_districts_hunks.json` mises à jour (blocs `after` seulement, une occurrence exacte).
- Tests de contrat ajoutés (`sweeps/test_road1y_freight.py`), multimodal gate et inventaire mis à jour.
- Validation : `python3 -m unittest test_road1y*.py test_road100*.py` : 275 tests OK, 2 ImportErrors préexistantes acceptées.
