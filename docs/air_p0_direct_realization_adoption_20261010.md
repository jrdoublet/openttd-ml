# AIR P0 — Adoption volontaire de la réalisation directe (10 octobre 2026)

## Décision

À l'issue de la campagne indépendante **40 graines × 10 ans**, l'utilisateur
**valide explicitement** la variante `air_p0_direct_realization=1` et demande
de la rendre **active par défaut**, de commiter et de pousser. Cette décision
prend le pas sur les conclusions provisoires « ne pas adopter » formulées à
la fin des rapports des campagnes 40×5 et 40×10. Elle ne transforme pas un
résultat statistiquement non significatif en preuve d'équivalence.

Les protocoles, les graines et résultats bruts sont décrits dans :

- `docs/air_p0_direct_realization_20261010.md` (premier 40×5) ;
- `docs/air_p0_direct_realization_holdout_20261010.md` (second 40×5) ;
- `docs/air_p0_direct_realization_holdout_40x10_20261010.md` (40×10, r2).

Le 40×10 (80/80 parties, 40/40 paires, 40 graines inédites) donne **+74 488,8
£/an** de profit terminal ON−OFF, **22 gains et 18 pertes**, IC95 bootstrap
**[−21 695,825 ; +173 259,4] £/an**, Wilcoxon p=0,149902, valeur de
compagnie **+0,625302 %**. La règle historique de gain minimum +4 % renvoie
`fail_primary`. Les opcodes partiels SIGN sont à **−4,988 %**, mais ni leur
couverture CPU ni la charge des deux trajectoires ne sont identiques.

## Modification adoptée

- Réglage `air_p0_direct_realization` à **1 sur toutes les difficultés** ;
  `0` conserve la branche historique comme option de retour arrière.
- Nouveaux devis **AIR hubsite/hubhub** uniquement : moyenne arithmétique
  directe des ratios matures `c121RealizationPm` déjà observés pour le bras,
  sans pseudo-ligne, seuil de deux lignes ou lissage `0.75 + 0.25 * learned`.
- Facteur **1,0 à froid**, puis activation à la première observation non
  neutre ; hors hubs et pour la flotte, le modèle historique est conservé.
- Garde C70/C82 contre une **double correction** lorsque le projet porte
  déjà un facteur C121 non neutre ; C70 reste actif à froid.
- Cache purement transitoire, dérivé des lignes au rapport annuel et
  reconstruit au `Load`, sans nouvelle clé persistée ni scan supplémentaire.
- Pas de remise en question des autres constantes historiques (MAIL15,
  104 %, pondération 50/50 d'autres chemins, calibration C70 générale).

Cette adoption est un **choix de projet éclairé par le benchmark**, et non
une validation d'équivalence stricte. L'anomalie de divergence précoce sur
la graine `796219007` en 1970 est documentée dans le rapport 40×10.

## Règles pour les futurs tests de simplification

Document de référence : `docs/experimental_acceptance_policy_20261010.md`.
Ces seuils expérimentaux s'appliquent **aux futurs changements**, sans
invalidation rétroactive du choix d'adoption explicite présent.
