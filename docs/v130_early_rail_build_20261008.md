# V130 — poser le rail de préparation dès qu'il est prêt

**Statut au 08/10/2026 : demande enregistrée, NON IMPLÉMENTÉE, NON TESTÉE.**
Ce document complète la [liste de tâches](taches.md) : il ne décrit **ni un
correctif livré**, ni un résultat V130. Aucun réglage `v130_*`, commit
identifié comme V130, ni campagne `v130*` n'a été retrouvé dans les branches,
le code et les résultats du dépôt à cette date. Il ne faut pas confondre cette
piste avec **V128** (stock de tracés, bancs défavorables) ou **V131**
(diagnostic de l'obsolescence et réparations locales).

## Demande utilisateur et motivation

Le 08/10, l'objectif noté sous **V130** était de **construire une ligne rail
dès qu'un tracé préparé est prêt**, y compris **pendant l'année 1** du régime
C121 « AIR d'abord », au lieu de le retenir jusqu'à la fin de cette phase.
Hypothèse à vérifier : éviter qu'un tracé devenu obsolète au moment de la pose
soit bloqué par un aéroport, une gare ou d'autres constructions.

La priorité AIR de la première année a été qualifiée séparément. V130 propose
une modification d'**arbitrage du capital et du calendrier des constructions** :
elle peut réussir à poser plus de rail tout en empêchant d'ouvrir des aéroports
rentables en 1970. Le nombre de lignes rail posées, à lui seul, ne constitue
donc pas un critère de succès.

## Comportement du code effectivement présent

- `ai/OpexAI/info.nut:687–706` :
  `c121_catalog_air_first_year=1` et
  `c121_air_first_year_rail_prep=1` sont **les défauts actuels** ;
  `ai/OpexAI/settings.nut:361–374` lie la préparation rail au régime
  C121 AIR de première année. Le commentaire d'en-tête de
  `rail_prep_c121.nut:3` disant « défaut 0 » est **historique / périmé** :
  ne pas s'y fier pour conclure que la préparation est éteinte.
- `ai/OpexAI/rail_prep_c121.nut:106–116,174–208` : la préparation rail
  démarre quand aucun projet AIR vivant n'est finançable, qu'une recherche
  rail n'est pas déjà en cours et que le régime année 1 est actif ;
  elle cède la main quand un projet AIR redevient finançable.
  `:12,260–300` borne le stock préparé à **trois** recherches de route.
- `ai/OpexAI/task_rail.nut:180–199` : une route marquée
  `c121PrepStock`, même dotée d'un `railPlan` prêt, est rejetée pendant
  la première année avec la raison **`rail_prep_held`**. Elle redevient
  candidate à la pose une fois l'amorçage terminé.
- `ai/OpexAI/task_rail.nut:2007–2077` : une recherche terminée dépose
  le plan au stock `railReadyStock`; **déposer n'est pas construire**.
  `rail_prep_c121.nut:119–140` décrit le retour à un A* normal après
  invalidation d'un tracé stocké.

**Conclusion statique :** la fonctionnalité de *préparation* rail C121 existe
et est active par défaut. **La fonctionnalité V130 de *pose anticipée* n'existe
pas** : la garde `rail_prep_held` est encore présente.

## Indices historiques pertinents (pas des bancs V130)

- [V128](taches.md) : des tracés stockés environ un an puis utilisés
  tardivement ont montré des échecs de pose. Son banc A 40×3 à profondeur 4
  a échoué au gain primaire (**−40,7 k£/an**) ; le diagnostic 40×4
  n'a pas démontré de rattrapage (**−37,8 k£/an**). V128 ne teste
  **pas** la pose pendant la première année.
- [V131](taches.md) : la sonde `v131_probe_4x3_20261008` a attribué
  plusieurs tracés anciens inutilisables à des emprises d'aéroport,
  notamment des blocs de 10–15 tuiles ; les tracés récents rencontrent
  d'autres obstacles ponctuels. Cela rend l'hypothèse V130 **plausible**,
  sans montrer qu'une pose anticipée aurait été rentable.
- Les remarques « fin janvier 1970 » et « environ un an plus tard »
  décrivent des cas observés dans ces diagnostics ; elles ne sont pas
  une date de dépôt ni un délai garantis pour toutes les cartes.

## Ce qui reste à décider et mesurer avant implémentation

1. **Exposition sans nouvelle décision** : mesurer par graine et date
   `readyDate`, âge du plan, nombre de refus `rail_prep_held`, trésorerie,
   projet AIR finançable, état de chantier et premier obstacle du tracé.
   Distinguer occurrences répétées et **projets uniques**. Vérifier que
   des plans valides sont réellement prêts *avant* la fin de l'année 1.
2. **Critère de déclenchement minimal** : proposer une voie explicite pour
   construire une route rail préparée avant 1971, sans déverrouiller tout
   le portefeuille rail ni modifier les autres branches C80/V128. Vérifier
   revalidation du site/plan, budget, réserve de caisse, priorité AIR,
   rollback, cooldown et Save/Load. La règle exacte de priorité capital
   AIR vs rail est à fixer **avant** tout banc, pas après les résultats.
3. **Mesure de substitution** : pour les deux bras du **même code gelé**,
   comptabiliser les lignes rail supplémentaires réellement posées,
   leurs dépenses et profits, les aéroports ouverts en 1970 (nombre et
   dates), les projets AIR différés et le `profit_year` terminal Opex.
   Mesurer également si les erreurs `track_blocked` / `station_blocked`
   disparaissent effectivement plutôt que simplement se déplacer.
4. **Qualification comportementale** : contrats Squirrel + smoke
   apparié exposant au moins une pose anticipée, puis protocole V102
   **porte A 40 graines × 3 ans**, `gain_short` avec seuil **+4 %**,
   Wilcoxon p < 0,05, IC95 bootstrap borne basse > 0 et garde de
   valeur **−5 %**. **Porte B 20×10** (`non_erosion`) seulement si A
   est franchie. Un changement de défaut exige les deux portes.
   Ne pas interpréter les bancs V128/V131 comme une qualification V130.

**Décision actuelle :** aucune activation, aucun changement de défaut,
aucune campagne V130 lancée. V130 reste **à étudier** et doit être isolé
des variantes de réparation de tracés et de profondeur de stock.
