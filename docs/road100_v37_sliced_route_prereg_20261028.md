# ROAD100-37 — recherche ROUTE découpée et reprenable (préenregistrement)

**ARRÊT SUR DEMANDE UTILISATEUR LE 28/10/2026 : ne pas implémenter,
intégrer, tester ou lancer ce projet.** Le prototype Squirrel et ses
contrats de tests éventuels restent non chargés et non validés.
Voir [le bilan d'arrêt](road100_bilan_arret_20261028.md).

**Statut 28/10/2026 : hypothèse architecturale ; aucune parité démontrée.**
Point de départ figé : V36 `road100_v36_rail_local_repair_arith_roadonly_seed42_1x1_20261028`, bundle
`cf675df6682af97d0d663550e42c8c28c5668703b59dd16e2879c5b9c2b21bc7` :
14 expansions, 36 états, 18 209 opcodes, `REPAIR_OPCAP`, aucun LONG, H1
Opex ON 19 106 contre AAA ON 93 008 £/an, soit ROAD100 **0/5**.

## Hypothèse vérifiable et architecture

Le générateur `OpexRoad100SiteFirstGenerator` rend déjà la main entre marchés,
mais `OpexRoad100LongConstructPlan` est atomique (jusqu'à 180 000 opcodes
par paire), à la différence de `_startRailSearch/_continueRailSearch` côté
RAIL. Les micro-variantes géométriques V36 ne règlent donc pas la recherche
interrompable. V37 doit conserver une recherche **dans un objet éphémère de
travail**, la faire progresser par petites tranches depuis le générateur
PO01C, puis publier un projet **uniquement après** vérification physique,
devis, flotte, créneaux et caisse. Ne pas remplacer un `PENDING` par un succès.

La transition proposée est : `SELECT_PAIR` → `SCAN_SITES` → `RANK_SITES` →
`SEARCH_CHUNK` → `VERIFY` → `ADMIT` → `READY`, avec états terminaux
`NO_PATH`, `OPCAP`, `STALE`, `UNBUILDABLE`, `NOT_PROFITABLE`. Le modèle doit
accepter plusieurs couples de vrais quais testés, des façades déjà reliées
dans les deux sens, et des buts alternatifs. Une route manquante n'est jamais
certifiée par la géométrie ni par `AIRoad.IsRoadTile` seul. Les coûts A* de
route existante requièrent `AreRoadTilesConnected` dans les deux sens ;
turns, emprise, pente, tiers et routes neuves nécessitent un préflight réel.

## Budget et validité

- **Opérations de recherche par reprise :** cible 20 000–30 000 opcodes,
  garde souple PO01C de 40 000 par passage ; les appels NoAI non
  interrompables sont comptabilisés et journalisés.
- **Budget cumulé :** 180 000 opcodes maximum par couple, 400 000 sur la
  génération LONG de l'année ; jamais réallouer 180 000 à chaque reprise.
  Garder au moins 50 000 pour la vérification, l'admission et les devis.
- **Mémoire :** bornes explicites sur ouvert/fermé, parents, caches et nombre
  de sites. Une tranche terminée pour cause `OPCAP` ne publie rien.
- **Identité :** clé `année + villes normalisées + cargo + sites + fronts +
  type de route + révisions catalogue/lignes`. Toute modification invalidate
  les preuves temporaires ; les AITest sont refaits après interruption.
- **Save/Load :** les coroutines et graphes ne sont pas sérialisables. Le
  `Load` actuel annule `_po01cJob`, puis relance la régénération après les
  réglages. Rejouer *toute* la génération ROAD du snapshot courant, sans
  publier de liste partielle ni restaurer un curseur de pair seul. Ne
  sérialiser ni AITest, ni chemin spéculatif, ni coût de devis obsolète.
- **OFF :** `road100_pax_graph_bridge=0` conserve les octets comportementaux
  historiques. Tout nouveau réglage éventuel est **0 aux quatre difficultés**,
  strictement ROAD-only. Ne toucher ni AIR/RAIL/WATER ni la fixture V262.

## Portes de validation et falsification

1. Tests de contrats : OFF exact, appels natifs et caps, distinction entre
   `PENDING` et `VERIFIED`, publication unique, invalidation et Save/Load.
2. Smoke **1×1 seed42 H1**, Opex ROAD-only, AAA sans train/tram/ship/aircraft,
   OFF/ON sur **un bundle commun**. Relever par paire les sites, expansions,
   états, reprises/ticks, opcodes de chaque tranche et total, arêtes déjà
   connectées, arêtes hypothétiques, premier échec moteur, devis et cash.
3. Exposition minimale avant 5×5 ou 40×5 : **au moins une nouvelle ligne
   LONG entièrement construite**, deux `StationID`, dépôt, bus avec ordres,
   PASS réellement livrés et résultat financier en jeu. Un chemin A*, une
   trace FAST, un devis ou un `AITest` isolé **ne comptent pas**.
4. Critère métier non négociable : `profit_year` annuel réel Opex ≥ AAA à
   chacun des H1, H2, H3, H4 et H5, sans érosion. Tout H1 seed42 reste
   diagnostic, sans preuve statistique. En absence d'exposition réelle :
   **NO-GO**, documenter et ne pas lancer les grandes campagnes.

Les contrats de construction existants (`OpexRoad100LongVerifyTrace`, devis
avec route manquante, préflight des deux arrêts et dépôt, droits, cash,
rollback et achat des véhicules) sont impératifs et restent l'autorité.
Les preuves V36 et les worktrees/conteneurs des autres sessions sont intacts.
