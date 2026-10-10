# AIR P0 — Préparation du nettoyage de l'ancien code (10 octobre 2026)

**Statut : audit et plan uniquement ; aucune suppression ni modification de
comportement dans cette passe.** Point de départ fonctionnel :
`95a6ad2` (`air_p0_direct_realization=1` par défaut), comparé au bundle
figé `061096c0…` et aux trois campagnes économiques documentées.

## Intention, périmètre et contraintes

Réduire la dette des **calibrations AIR historiques/prototypes** après
l'adoption explicite du ratio C121 direct pour les nouveaux devis
`hubsite`/`hubhub`. Le but n'est **pas** une nouvelle calibration :
conserver les chiffres et la séquence de décision de la version validée,
à froid, après observation et après Save/Load. Ne pas mélanger le ménage
avec les autres expériences AIR/RAIL/Capital dans l'arbre partagé déjà
modifié ; pas de restauration globale des fichiers dirty.

Le « 75/25 supprimé » désigne **son emploi dans le chemin nominal après
apprentissage**, pas son absence textuelle : aujourd'hui il subsiste
comme branche de repli (`air_p0_direct_realization=0` ou chemins non
éligibles). Ne pas prétendre avoir physiquement retiré ces coefficients.

## Carte d'usage relevée dans l'arbre courant

| Groupe | Points d'entrée actuels | Sortie / dépendances | Décision de nettoyage |
|---|---|---|---|
| Réglage direct validé | `info.nut` (`air_p0_direct_realization`), `settings.nut`, `globals_pre.nut` | `projects_models.nut::OpexC121RealizationFactor` et `OpexC121ApplyRealizationSums` | **CONSERVER** : défaut à 1 et repli à 0 tant que promis aux utilisateurs |
| Ratio C121 observé mature | `task_report.nut::OpexC121ObserveLineRealization` (`c121RealizationPm`, `c121RealizationYear`) | `OpexC121RealizationSums` et `OpexC121RecomputeRealizationFactors` | **CONSERVER** : source de vérité, éligibilité âge ≥ 2 et flotte N=N0 |
| Ancien lissage projet 75/25, 50/50 | `projects_models.nut::OpexC121RealizationFactor` (~90–95), `C121_AIR_PROJECT_REALIZATION[_ADAPTIVE]` | Repli lorsque le facteur direct est inactif, compatibilité réglage OFF | **NE PAS SUPPRIMER** avant décision sur `=0` et test de parité historique |
| Pseudo-observation et seuil `MIN_LINES=2` | `projects_models.nut::OpexC121ApplyRealizationSums` et `globals_pre.nut` | Calcul de `C121_AIR_REALIZATION_FACTOR` encore lu par flotte (`projects_builders.nut`), correction engine-only, anciens devis | **CONSERVER** tant que ces consommateurs existent ; ce calcul ne corrige plus les devis hub nominaux après activation directe |
| Repli 50/50 du moteur | `projects_models.nut::OpexC121EngineDecisionRealizationFactor` | `air_economics_c121.nut::OpexC121EngineEconomics`, option `c121_air_engine_realization=0` par défaut | **HORS PÉRIMÈTRE** de la validation directe ; retirer uniquement dans un chantier isolé |
| Prototype LOO `air_p0_learned_revenue=0` | `projects_models.nut` (`OpexC121P0AddObservation`, `OpexC121P0CrossValidatedFactor`, tableaux à 4 valeurs), `task_report.nut`, `air_fleet.nut`, `air_catalog_c121.nut`, `air_planning.nut`, `air_economics_c121.nut`, `persist.nut`, `settings.nut`, `info.nut` | Capture des époques de flotte, recettes observées/predites, chemin MAIL alternatif et champs exceptionnels Save | **MEILLEUR CANDIDAT** à suppression, sous réserve d'abandon officiel du réglage expérimental OFF et de contrôle des autres utilisateurs des helpers |
| Régime adaptatif / pression / C122 | `projects_selection.nut`, `globals_pre.nut`, `persist.nut::OpexSaveC121Strategy` et `OpexRestoreC121Strategy` | `c121_air_project_realization_adaptive` **actif par défaut**, stratégie et éventuels modes C122 ; `OpexC121RealizationFactor` y teste aussi ce flag | **NE PAS RETIRER EN BLOC** : usage indépendant du lissage historique |
| Garde anti-double correction | `projects_models.nut::OpexC70Profit`, `OpexC82Profit` | Quand réalisation directe non neutre, ne pas réappliquer C70/C82 ; C70 reste actif à froid | **CONSERVER** et tester aussi le passage froid→mature et Save/Load |
| Tarifs historiques `104 %` / forfait MAIL15 | `globals_pre.nut::AIR_PAX_REVENUE_CALIBRATION_PCT`, `air_economics_c121.nut::OpexAirFarePerPax`, `air_planning.nut` | Certains chemins historiques, pas la recette physique PASS/MAIL nominale C121 | **HORS PÉRIMÈTRE** : leur suppression doit être prouvée séparément |

### Deux obstacles à un « simple effacement »

1. **La porte actuelle du facteur direct dépend encore du flag adaptatif :**
   dans `OpexC121RealizationFactor`, le test
   `(!C121_AIR_PROJECT_REALIZATION && !C121_AIR_PROJECT_REALIZATION_ADAPTIVE)`
   retourne 1,0 **avant** d'examiner le facteur direct. Avec le réglage
   adaptatif nominal à 1, le chemin validé fonctionne ; mettre les deux
   anciens flags à 0 le neutraliserait **malgré** `air_p0_direct_realization=1`.
   Un nettoyage doit déplacer ou découpler ce garde de manière explicite,
   sans modifier le comportement des sauvegardes et réglages existants.
2. **Les données historiques servent toujours ailleurs :**
   `C121_AIR_REALIZATION_FACTOR` est consommé par la flotte
   (`projects_builders.nut`, renfort froid) et la correction du moteur ;
   supprimer sa pseudo-ligne, sa reconstruction ou ses persistences de ligne
   modifierait potentiellement des décisions autres que les devis hub.

## Nettoyage proposé en trois lots indépendants

### A — Supprimer le prototype LOO rejeté (priorité 1)

**But :** retirer uniquement le chemin `air_p0_learned_revenue=1`, désactivé
dans tous les presets et exclusif du chemin direct. Commencer par tracer
les champs persistés `c121P0Epoch*`, `c121P0Observed*` et les helpers
`OpexC121P0*`, notamment la préservation conditionnelle des capacités
dans `persist.nut`. Vérifier que chaque appel à la capture d'époque en
`air_fleet.nut`, `air_catalog_c121.nut` et `task_air.nut` devient réellement
inutile une fois ce réglage supprimé. Dans `task_report.nut`, garder la
branche C121 standard écrivant `c121RealizationPm/Year` : **elle alimente
désormais le comportement par défaut**.

**À ne pas confondre :** `OpexAirP0KnownMailShare` et les capacités AIR
observées peuvent avoir des consommateurs non-LOO. Faire une recherche
d'appels avant toute suppression de helper partagé ; ne pas supprimer
les mesures PASS/MAIL C121 requises par d'autres fonctions.

**Compatibilité :** retirer le réglage `air_p0_learned_revenue` rend
impossible sa sélection dans les sauvegardes ou configurations anciennes.
Qualifier d'abord ce changement de support ; au besoin garder une entrée
de réglage désactivée avec avertissement plutôt que réutiliser son nom.
Ne jamais recycler l'identifiant pour un autre mécanisme.

**Vérifications :** contrat default ON, même sortie froide, même ratio
direct après un rapport mature, tests Save/Load depuis une partie de l'ancien
format et à chaud, audit des chaînes `AIR_P0_LEARNED_REVENUE` disparues,
tests ciblés existants mis à jour (notamment
`sweeps/test_air_p0_learned_revenue.py`) **seulement après** approbation du
retrait du prototype, puis smoke de jeu apparié. Comparer opcodes du chemin
actif en conditions équivalentes. Retirer les champs de Save uniquement
si aucun ancien `Load` ne les lit.

### B — Isoler le chemin validé du lissage historique (priorité 2)

**But :** simplifier la lecture de `OpexC121RealizationFactor(plan)` en
distinguant **1) froid/observé direct** et **2) repli historique**. Éviter
un nouveau helper ou un cache inutile ; placer la sélection directe au
bon niveau, après validation `plan.arm` et en conservant strictement les
cas historiques `newpair`, `AIR_P0_LEARNED_REVENUE=0`, moteurs et flotte.

**Décision préalable incontournable :** le réglage `air_p0_direct_realization=0`
est officiellement conservé comme retour arrière depuis `95a6ad2`.
Il est donc **interdit d'effacer** aujourd'hui le `0.75 + 0.25 * learned`
et les seuils encore nécessaires à son comportement. On peut d'abord
les **isoler** en branche de compatibilité (simple réorganisation),
en gardant les deux valeurs ON/OFF identiques.

**Vérifications :** matrice de tests sur
`direct=0/1 × adaptive=0/1 × project_realization=0/1 × cold/observed` ;
le résultat **nominal ON + adaptive=1** doit être bit/sémantiquement
identique à `95a6ad2`. Confirmer aussi que `direct=0` retrouve les
coefficients historiques à l'identique et qu'il n'y a pas de double
correction C70/C82. Attention à la cadence/opcodes d'un `if` déplacé :
une parité de nombres ne garantit pas une trajectoire de jeu identique.

### C — Évaluer ensuite la suppression *physique* des branches anciennes

**Seulement si** l'utilisateur accepte de retirer le retour arrière
`air_p0_direct_realization=0` et les réglages anciens correspondants,
faire l'inventaire complet de leur compatibilité puis supprimer :
`C121_AIR_PROJECT_REALIZATION`, `C121_AIR_REALIZATION_MIN_LINES`, le
lissage 75/25, la pseudo-ligne et les branches de calcul **uniquement si**
la flotte, l'engine-only, la classification adaptative/C122 et Save/Load
n'en dépendent plus. Le lissage moteur 50/50 et les revenus MAIL/104 %
doivent faire l'objet de chantiers distincts, jamais entraînés par cette
suppression. Sans cette décision, arrêter après le lot B.

## Porte de validation du nettoyage

- **Avant tout edit :** snapshot du diff de chaque fichier dirty, périmètre
  figé des branches, tests et configs `OFF/ON`; aucun commit mélangeant
  des modifications concurrentes. Une campagne Docker à la fois.
- **Contrats ciblés :** `sweeps/test_air_p0_direct_realization_default.py`,
  tests C121 de l'économie, froid et rechargement ; revoir les tests
  legacy LOO/flag adaptatif plutôt que les supprimer silencieusement.
- **Parité forte privilégiée :** si le nettoyage prétend être purement
  structurel, comparer par graine les métriques et premières décisions,
  avec mêmes options et source du moteur. Si une divergence est détectée,
  ne pas annoncer « suppression neutre » : passer à une véritable porte
  économique suivant
  [les règles futures](experimental_acceptance_policy_20261010.md).
- **Coût d'opcodes :** profiler le chemin touché à charge identique ;
  ne pas déduire sa neutralité des sommes SIGN partielles de trajectoires
  divergentes. Les règles futures retiennent une marge supérieure de +1 %.
- **Save/Load :** comparaison à froid, après rapport mature, puis
  sauvegarde/recharge avec ratio conservé et absence de calibration double.
  Ne pas faire de changement de schéma implicite.

## État de livraison de cette préparation

**Pas de code Squirrel modifié, pas de Docker lancé, aucun commit/push.**
Le seul livrable est cette cartographie et l'entrée complémentaire du
journal du jour ; les bundles, résultats A/B et travaux partagés ne sont
pas changés. Le premier lot recommandé est **A (ancien learner LOO)**,
mais son retrait n'est pas inclus dans la présente tâche.
