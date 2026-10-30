# 30 octobre 2026 — décision utilisateur : arrêter les scans AIR stériles, réactiver les réparations RAIL

## Périmètre de cette révision

Mise à jour **documentaire du registre actif** sur décision explicite de
l'utilisateur, après la clôture `POST-1974-ENTONNOIR` :

1. **Supprimer `AIR-PRODUCTIVITÉ` des priorités et des tâches ouvertes**, ainsi
   que les sous-items dédiés `AIR-ROI-LIGNE-1` et
   `AIR-ROI-RENOUVELLEMENT-1` qui avaient été laissés autonomes. Les données
   historiques de rendement et les mesures C63 restent dans leurs rapports,
   mais **aucun chantier de productivité AIR** n'est maintenu de manière implicite.
2. **Restreindre `AIR-COVERAGE / EB-1` à une optimisation de calcul** :
   arrêter les passes répétées de découverte de nouvelles villes quand toutes
   les villes disponibles ont été examinées/épuisées ; **ne lancer à nouveau
   cette recherche que sur un événement de fondation de ville**.
3. **Réactiver explicitement les réparations RAIL lors des échecs** :
   V131 (tracé vieilli), EB-2/EB-6/P4 (gare et jonction), recherche
   `ABND/NOPA` et pose `TRKFAIL/STNFAIL/LOOPFAIL`, avec V233L en chantier
   de constructibilité à part entière. La relance des *questions* est
   autorisée, **pas l'adoption automatique** des variantes historiquement
   perdantes.

Cette réorganisation **n'implémente aucun comportement** : code IA,
paramètres par défaut et verdicts d'essais restent inchangés.

## Point d'ancrage réel de la recherche AIR par événement

- `ai/OpexAI/events.nut` traite déjà `AIEvent.ET_TOWN_FOUNDED` et appelle
  `_onTownFounded`.
- `ai/OpexAI/event_handlers.nut::_onTownFounded` marque actuellement le
  catalogue `towns` et les modes `rail/road/air/water` comme modifiés puis
  appelle `_catalog._refreshTowns()`.
- `ai/OpexAI/air_planning.nut` parcours les villes triées et effectue
  des recherches de sites ; il ne suffit pas d'ignorer les sorties
  `C78_SLOT` pour économiser ces opcodes.
- En 1978 sur **une seule graine instrumentée**, 92/92 passes
  `C78_SLOT phase=projects_pass` avaient `air_candidates=0`, alors que
  les passes voyaient entre **5,808 et 7,958 M£** de capital disponible.
  Cela motive le STOP, mais **zéro candidat AIR dans une passe ne prouve
  pas à lui seul que toutes les villes sont épuisées** : moteurs,
  sites et candidats pré-calculés sont différents.

Contrat de la prochaine implémentation : lister une fois les villes au
premier lancement, définir l'invariant d'épuisement du vivier en fonction
des **gardes de disponibilité existantes**, puis **ne plus déclencher de
nouveau scan de villes par cycle/TTL/caisse ou croissance d'une ville
existante**. À la réception d'un ou plusieurs `ET_TOWN_FOUNDED`, intégrer
les nouvelles villes sans refaire les villes épuisées, et persister la
veille/les identifiants déjà traités à travers Save/Load. Les **projets
déjà évalués**, la flotte et l'exploitation des aéroports actuels sont
hors de ce STOP. Un simple `air_candidates=0` ne permet **pas** de mettre
en veille définitivement si le vivier de villes n'a pas été classé.

Le choix utilisateur est volontairement strict : **un gain potentiel de
couverture dû seulement au changement d'une ville existante n'est plus
un déclencheur de recherche**. Documenter cette contrepartie et mesurer
les opcodes, l'équivalence des choix hors saturation et les effets
économiques avant toute promotion. Nouveau levier opt-in défaut 0 pour
préserver le bundle élu.

## Quatre familles de réparations RAIL réouvertes

| Famille | Déclencheur et intervention à requalifier | Historique qui n'est pas effacé |
|---|---|---|
| `RAIL-REPAIR-V131` | `track_blocked`/`station_blocked` après stockage ; revalidation par tuile, détour local, décalage de quai | V131c répare dans des smokes mais **40×5 `fail_primary`, −31,55 k£/an**, défaut 0 ; voir [archive V131](journal_2026-10-30_transfert_taches.md) |
| `RAIL-REPAIR-SITE` (`EB-2/EB-6/P4`) | `SITEA/B/AB`, `STNFAIL` ; repli gare neuve, quai différent ou jonction alternative **réellement testée** | EB-2 40×3 **−19,1 k£/an** ; P4 inerte/NO-GO ; V307 sites élargis non retenus ; voir [audit EB-2](../eb2_maturation_20261028.md) |
| `RAIL-REPAIR-ASTAR` | `ABND/NOPA` primaire ; alternative bornée de gares/couloirs/sens et mémoire des échecs | V307 sens inverse et V303 reprenable non retenus ; plafond seul et libération de créneau réfutés ; voir [V307](../v307_puits_multiquais_20261021.md) |
| `RAIL-REPAIR-POSE` | `TRKFAIL`/`TRACK_FAIL`, `STNFAIL`, `LOOPFAIL` pendant la pose ; détour/connexion locale et rollback transactionnel | V233L TRACK8–10 et V131 ont des outils de réparation ; aucune qualification économique de ces outils sur **ESTIM31** ; voir [V233L](../v233_long_good_20261025.md) |

Le diagnostic [POST-1974](../post1974_entonnoir_20261030.md) relie
**5 tentatives RAIL échouées et 1 inachevée** à des OD dirigées distinctes
sur la graine 42. Les motifs `NOPLAN2` et `ABND` montrent des problèmes
concrets ; ils **ne prouvent pas** qu'un parcours alternatif est viable.
Les réparations doivent transformer une OD en **liaison réellement
construite**, avec coût, recette et rentabilité mesurés, plutôt que
seulement réduire un compteur d'échecs. Les hypothèses nouvelles
seront évaluées sous les défauts actuels, avec tests OFF/ON, Save/Load,
un Docker à la fois, exposition, puis validation appariée avant adoption.

## Statut au 30 octobre

**Livré :** décision et tâches réconciliées dans `docs/taches.md`.
**À faire :** implémentation AIR sur événement et études/réparations RAIL
dans leurs chantiers respectifs. **Aucun prototype adopté par ce document.**
