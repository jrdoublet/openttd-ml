# AC-08 — catalogue matériel AIR : coût, compatibilité et choix (11/10/2026)

**Décision : audit terminé sans refactoring ni optimisation.** Les boucles
de `OpexCatalog::_refreshAir` restent de faible cardinalité (au plus cinq
types d'aéroports, avec un parcours de la liste des moteurs AIR par type).
Les profils disponibles décrivent un coût de catalogue faible et surtout
**peu fréquent** au défaut courant ; aucune mesure actuelle du coût propre
à `_refreshAir` ne prouve un goulot d'étranglement significatif.
**Aucun changement de l'ordre des appareils/aéroports n'est justifié.**

## 1. Le catalogue exact et ses consommateurs

`ai/OpexAI/catalog.nut:634–764` reconstruit à chaque appel :
`airport=null`, `plane=null`, `airCombos=[]`,
`airPlaneChoicesByAirport={}` et `airPlaneFrontierByAirport={}`.
Sans cargo passagers, retour avec des collections vides.
Les moteurs viennent de `AIEngineList(VT_AIR)`, filtrés par
`IsBuildable` puis `CanRefitCargo(paxCargo)`; capacité positive exigée.

L'ordre historique des types est **INTERNATIONAL, METROPOLITAN, LARGE**
(aéroports grands), puis **COMMUTER, SMALL** (aéroports petits).
Un type non disponible n'émet pas de combo.

| Catégorie | Compatibilité / choix du meilleur |
|---|---|
| Grand | Petit ou gros avion admissible. **Priorité absolue au gros** quand il en existe un ; ensuite capacité maximale, puis vitesse maximale. Un score identique conserve le premier moteur rencontré. |
| Petit | **Uniquement `PT_SMALL_PLANE`**, même si un gros avion aurait une meilleure capacité ou vitesse. Capacité maximale, puis vitesse maximale ; premier moteur à égalité. |
| Collections secondaires | `airPlaneChoicesByAirport` conserve dans l'**ordre des moteurs parcourus** toutes les alternatives admissibles quand `EQUIPMENT_ROI_PROBE`, `AIR_ROUTE_PLANE_SELECTION`, C85 ou C121 (actif/shadow) le demande. |
| Frontière C85 | `airPlaneFrontierByAirport` est produite **uniquement si `C85_AIR_EQUIPMENT_FRONTIER`**. Cette frontière expérimentale n'est pas une nouvelle sélection à adopter en AC-08. |
| Aliases legacy | `catalog.airport` et `catalog.plane` sont définis par le **premier combo valide** ; changer cet ordre modifierait les consommateurs anciens. |

Consommateurs identifiés : `air_planning.nut` lit `airCombos`
pour les combinaisons de génération ; `air_engine_choice.nut`,
`air_economics_c121.nut`, `air_catalog_c121.nut`,
`air_fleet.nut` et `air_route_economics.nut` lisent les choix
par type. La frontière C85 est notamment lue dans
`air_engine_choice.nut:1942–1950`. Le catalogue est donc **un
contrat de classement**, et pas uniquement une liste à dédupliquer.

## 2. Fréquence et mesures disponibles

Le chemin complet `OpexCatalog::refresh` appelle
`_refreshAir` (`catalog.nut:1084–1112`). Le chemin ciblé
`_c77RefreshModeCatalog("air")` l'appelle aussi
(`orchestrator.nut:850–863`). Le scheduler C78 empêche le
refresh ordinaire **pendant le scan actif** tant que sa branche
de continuation retourne `false`. Une publication partielle
V141 n'est **pas** un refresh de matériel.

**Traces actuelles visibles, sans lancement de nouvelle partie :**

- `results/ac04_hubsite_cost_42_3y_20261011.artifacts/reference_42.log`
  contient **3 lignes `_refreshAir: combos=1`** au cours du
  diagnostic graine 42, trois ans : un combo grand/petit disponible
  dans cette réalisation. Ce nombre n'est pas une fréquence généralisable.
- Le rapport historique V141 indique **deux refreshs de matériel en
  trois ans** sur son propre échantillon. La trace AC-04 et V141
  sont des campagnes différentes ; ne pas additionner ni présenter
  ces nombres comme une fréquence annuelle stable.
- Le journal `results/catalogue_churn.json` est un ancien profil
  **graine 42, 1970–1989, OpenTTD 15.3** : pour les 20
  observations annuelles, `ops_airports` varie de
  **149 à 161 opcodes** (moyenne **155,2**) et `ops_engines`
  de **1 099 à 1 339** (moyenne **1 216,8**).
  Le `catalog.nut` documente environ **21 500 opcodes pour un
  refresh complet** dans cet ancien protocole. Ces postes du
  vieux harnais ne sont **pas une mesure isolée actuelle de
  `_refreshAir`** ; impossible d'en déduire la facture de sa
  double boucle avec les réglages C121 courants.

Le code courant possède déjà les points d'instrumentation adéquats :
`CATALOG_COST_ACTIVE.engineRefreshOps` sur la mise à jour AIR et ses
empreintes C121 (`catalog.nut:1084–1107`), et
`PROBE_SPAN_TRACE` pour `catalog.refresh.air`. Le diagnostic
AC-04 ne produit pas de fin de cycle `CATALOG_COST` exploitable
et n'a pas cette sonde de spans activée. **Aucun coût unitaire
actuel fiable n'est publié**.

Au vu du **nombre limité de refreshs** et de l'ordre de grandeur
historique comparé aux millions d'opcodes du scan de paires AIR,
il n'existe **aucune preuve suffisante de gain matériel** pour
risquer la modification du choix des avions et des gares. Cela
ne signifie pas qu'un gain d'opcodes a été mesuré à zéro.

## 3. Fixture indépendante et vérifications

`sweeps/test_ac08_air_material_catalog.py` vérifie statiquement les
conditions, les API utilisées et les consommateurs, puis simule des
moteurs stubs sur **4 800 catalogues synthétiques** (deux profils
de conservation des alternatives chacun). L'oracle indépendant
recalcule le meilleur avion sur la priorité
`gros > capacité > vitesse` quand pertinent, avec conservation du
premier en cas d'égalité.

Cas ciblés : absence de passagers, types d'aéroports indisponibles,
capacité non positive, refit impossible, appareils non constructibles,
gros avion faible capacité prioritaire en grand, gros interdit en
petit, stabilité des départages, ordre des cinq types et des
alternatives, activation conditionnelle de C85.

**6/6 tests verts**, plus **8/8 AC-07 verts**, Python local.
Cette fixture ne compile pas Squirrel ni ne mesure le choix moteur
en situation NewGRF, ni les opcodes de la VM. Un changement de
comportement nécessiterait une campagne économique et opcode
appariée ; aucun code de production ni défaut n'est modifié.

**Clôture AC-08 : sans patch.** Le risque le plus élevé serait un
« nettoyage » des règles de priorité qui changerait discrètement
`airCombos` et ses consommateurs. Ne pas rouvrir C85 ou les scores
C121 au titre d'une optimisation du catalogue matériel.
