# Catalogue AIR — découpage en tâches indépendantes (11 octobre 2026)

**Mise à jour du 12/10 :** l'utilisateur a validé **AC06 v2** après
les refus documentés du 11/10. La nouvelle décision autorise son surcoût
de +32 opcodes par paire 1970–1971 ; AC06 v2 rejoint AC04-B et AC05 dans
le `master` local, avec rollback. Toutes les mentions ci-dessous de
« AC06 non adopté » sont historiques. [Décision et implémentation](ac06_v2_adoption_20261012.md).

## Périmètre et décision

Le mot *catalogue* recouvre deux travaux distincts : le **catalogue matériel**
`OpexCatalog::_refreshAir` (`ai/OpexAI/catalog.nut:634`) qui produit les types
d'aéroports et avions compatibles, et la **génération reprenable de projets AIR**
`OpexAirPlans` (`ai/OpexAI/air_planning.nut:2325`), pilotée par
`OpexC78ContinueCatalogAirRebuild` (`scheduler_tasks.nut:83`). Le second reste
la priorité, avec deux essais désormais clos. **V142** a testé la coalescence
des publications C78 : porte A 40×3 `fail_primary` malgré un gain d'opcodes.
**V143** a testé la conservation des curseurs hub (porte A : −63,9 k£/an,
`fail_primary`) et le refresh annuel non-air pendant le scan (smoke seul :
−252 k£/an). La référence remet le haut du vivier hub-hub en concurrence,
ce qui est économiquement utile. Voir les verdicts [V142/V143 dans le journal](journaux/journal_2026-10-11.md)
et `docs/taches.md` ; aucune reprise de ces variantes.

**Statut final des audits et qualification au 11/10 : huit audits AC-01 à
AC-08 terminés, deux correctifs adoptés dans master local sans commit :
AC04-B (ancre physique dédupliquée) et AC05 (pré-calcul V86 inutile
sous C121).** Ils disposent chacun d'une qualification économique/opcode
isolée et d'une validation du cumul (20×10 économie, 10×4 VM).
AC04-A v1 et AC06 v1 sont rejetés pour surcoûts opcode ; leurs **anomalies
restent ouvertes à une v2 optimisée**, isolée dans un autre worktree
avec tests source verts mais sans verdict VM/économique final.
Les rapports/fixtures AC-01 à AC-08 sont conservés sans nouvel audit.
Les huit lots sont les frontières de code de la production AIR ; V141
(`v141_catalog_incremental=1`) est **déjà adopté** avec sa qualification opcode
20×10 ; les ~25–31 % gagnés sur `pub.filter` ne sont pas à requalifier.
Les variantes de score RAIL rejetées restent closes. Les anciennes variantes
AIR rejetées (notamment cache de production exacte, réadmission, plafonds
de flotte, nouvelles priorités de projets, V142 et V143) ne sont pas réintroduites.

Les huit lots ci-dessous sont **des mandats distincts** : chacun doit pouvoir
conclure `sans action`, `correctif proposé`, `adopter` ou `rejeter` sur **sa
propre preuve**. L'audit de chacun peut se mener en parallèle. Si deux lots
veulent modifier `air_planning.nut` ou `scheduler_tasks.nut`, développer en
branches/worktrees séparés et intégrer/tester un changement à la fois ; ne
jamais attribuer la qualification d'un cumul à une seule brique.

## Frontières fonctionnelles effectivement indépendantes

Le découpage AC-01 à AC-08 est celui des **mandats de développement,
audits, tests et décisions** : chacun possède son périmètre et sa preuve ;
aucun résultat A/B ne peut être transféré à un autre lot. Le code actuel
`OpexAirPlans` est également déjà séparé en fonctions de phases reprenables
(`Prepare`, `FindSites`, `NewPairs`, `DiscoverHubs`, `HubToSite`,
`HubToHub`, `Finalize`) avec curseurs dédiés. La publication V141 est
distincte dans `OpexC78ContinueCatalogAirRebuild` et le catalogue matériel
dans `OpexCatalog::_refreshAir`. Les corrections AC04-B, AC05 et AC06,
si qualifiées, restent des helpers/gardes localisés dans leurs frontières.

**Limite explicite :** ces unités ne sont pas huit entrées indépendantes
de `_taskQueue` : elles sont orchestrées par un même curseur C78 et passent
par un même budget de tranche. Convertir chaque phase en tâche de file
autonome risquerait de modifier cadence, portefeuille et V141/V143 ; il
faudrait une autre qualification économique et opcode. Aucun tel refactoring
gratuit ou changement de scheduler n'est inclus au chantier AC actuel.

## AC-01 — Mesurer les coûts restants du cycle C78

**Statut au 11/10 : AUDIT TERMINÉ, aucun correctif.** Les reprises internes du
snapshot hub ne sont pas des reconstructions complètes du scan ; le profil
historique attribue 35,9 M opcodes sur six ans aux phases hub (65 % du poste
AIR), sans isoler la fraction rejouée. V142 et V143 ont déjà montré que réduire
ces reprises/publications peut être défavorable économiquement. Le coût net
par invalidation reste non identifié ; aucune nouvelle campagne n'est
justifiée dans ce lot. [Rapport de décision AC-01](ac01_c78_cycle_cost_audit_20261011.md).

**Question fermée :** après les mesures V141–V143, quel coût réel reste lié
aux reprises du scan, et quelle part de ce coût produit de nouveaux candidats
rentables ? La non-finalisation et l'utilité du redémarrage ont déjà été étudiées.

- **Propriétaire :** transitions `primary → fallback → apply` et publication
  dans `scheduler_tasks.nut:15–230`, compteurs existants `AIR_LIGHT`,
  `CATALOG_COST_SLICE`, spans `catalog.slice` / `catalog.rebuild`.
- **Travail :** analyser d'abord les traces V141–V143 ; seulement si elles
  ne suffisent pas, proposer une télémétrie *agrégée*, OFF par défaut, avec
  identifiant de génération, cause du départ/arrêt, phase, combo, progression
  du curseur, nombre de plans publiés et opcodes par tranche. Pas de logs
  par paire, pas de changement de décision ni de mécanisme de fin V143.
- **Livrable :** coûts par phase, reprises, publications et candidats retenus,
  avec graines et sources précises ; aucune interprétation « finit plus vite
  donc meilleur » : V143 a montré l'inverse.
- **Validation :** décodeur/fixture si ajouté ; comparaison sonde OFF/ON sur
  mêmes entrées, en signalant toute perturbation d'opcodes. Pas de porte
  économique pour cette observation.

## AC-02 — Recherche des sites et reprise des villes

**Statut : AUDIT TERMINÉ, sans correctif (11/10).** Les checkpoints réels
`scanIndex=i+1` / `rankIndex=rankIndex+1` et le budget de sondes conservé
sont vérifiés statiquement ; le modèle figé passe **480 comparaisons**
tranché/non tranché (grands/petits sites, V93, C83 cible, quota et refus).
Aucune omission/duplication démontrée. Pas de preuve VM sur carte mouvante
et aucune optimisation d'opcodes revendiquée.
[Rapport et fixture AC-02](ac02_air_site_resume_audit_20261011.md).

**Question fermée :** une tranche reprend-elle au bon `scanIndex` /
`rankIndex` et retrouve-t-elle les mêmes sites que le parcours synchrone ?

- **Propriétaire :** `OpexAirPlansPrepare` et `OpexAirPlansFindSites`
  (`air_planning.nut:176–677`), cache de sites et `OpexAirFindSite` en lecture.
- **Travail :** vérifier l'initialisation, le tri des villes, la progression
  des deux curseurs et les invariants en cas de budget épuisé, site refusé,
  petit/grand aéroport ou ville ciblée C83. Comparer ordre, cardinalité et
  identités des sites d'un même état figé entre 1 passe et N reprises.
- **Livrable :** fixture de reprise reproductible et verdict sur les pertes,
  relectures ou doublons de sites ; corriger uniquement un écart démontré.
- **Frontière :** ne toucher ni au calcul de rentabilité, ni aux paires,
  ni aux critères V93bis/C83 déjà décidés, ni à la réinitialisation globale V143.

## AC-03 — Paires neuves, un seul curseur

**Statut : AUDIT TERMINÉ sans correctif (11/10).** Le checkpoint `(nextA,nextB)`
est posé avant les filtres et garantit une paire traitée par tranche active.
La fixture passe **2 520 comparaisons** de parcours complets/découpés sur
des choix synthétiques figés, plus les tests de bornes, cible et rejets.
Aucune omission/duplication démontrée ; aucune parité NoAI/économique
revendiquée. [Audit et fixture AC-03](ac03_air_new_pairs_resume_audit_20261011.md).

**Question fermée :** les indices `(a,b)` visitent-ils chaque paire éligible
exactement une fois malgré les suspensions ?

- **Propriétaire :** `OpexAirPlansNewPairs` (`air_planning.nut:678–996`),
  en particulier `resumeState.a/b`, `pairProgress` et la paire de ville ciblée.
- **Travail :** tester les suspensions avant/après la dernière paire d'une
  ligne et sur la dernière ligne ; relever éventuels rejouages d'une paire
  coûteuse, sauts ou défauts de progression. Contrôler l'égalité des candidats
  générés et de leur ordre sur un état figé, avec les mêmes réglages.
- **Livrable :** nombre de paires attendues/visitées/éligibles et égalité
  du vivier non découpé/découpé ; correctif minimal uniquement si causal.
- **Frontière :** ne pas modifier le scoring, les seuils de distance, le
  budget de tranche global ou la publication du portefeuille.

## AC-04 — Hub vers site, sans changer la stratégie

**Décision postérieure à l'audit initial :** AC04-B est **adopté et intégré**
dans `master` avec déduplication par ancre physique (deux vrais slots C83
distincts restent possibles). AC04-A v1 a été rejeté pour dégradation
opcode démontrée sur 40 graines ; sa tentative d'optimisation v2 par
`seenStations` et `hubIndex.routes` a également échoué sur 1970–1971.
Le paragraphe historique ci-dessous décrit l'état *avant* les bancs,
non la décision finale. Voir [validation](air_catalogue_validation_finale_20261011.md)
et [optimisations](ac_opcode_optimisation_20261011.md).

**Statut : AUDIT TERMINÉ (11/10), curseur validé, deux correctifs potentiels
NON ADOPTÉS.** Le parcours cartésien `hubSiteI/J` a la même séquence et les
mêmes admissions sur **5 625 entrées synthétiques figées**, sans omission ni
doublon d'indices ; les contrats voisins restent verts. La découverte peut
toutefois réintégrer une station saturée parmi les « orphelins » avec `routes=0`
et réajouter un site déjà retenu. Ces défauts d'identité métier sont distincts
des curseurs et leur exposition économique/opcode n'est pas établie. Profil
historique : `hub_site` 13,5 M op/6 ans/graine. Diagnostic mono-graine
42×3 sous Docker sain/source inchangée : **4 765 756 opcodes de phase**
pour **866 invocations**, mais **pas de coût exact par paire** faute de
compteur aligné (0 `CATALOG_COST` final). Aucun A/B économique ni `.nut`
modifié. [Audit, trace et fixture AC-04](ac04_air_hub_site_resume_audit_20261011.md).

**Question fermée :** le parcours `hubSiteI/J` avance-t-il sans perdre de
liaisons, et combien coûte sa reprise ?

- **Propriétaire :** `OpexAirPlansDiscoverHubs`, `OpexAirPlansHubToSite`
  (`air_planning.nut:1208–1616`) et les seuls contrats de `hubPhase` utiles.
- **Travail :** vérifier identité des hubs, route counts, progression des
  indices et garde de site encore utilisable à chaque reprise ; comparer le
  flux de candidats hub→site sur même état, puis isoler son coût opcode.
- **Livrable :** preuve d'exhaustivité/absence de doublon et coût par paire
  hub→site ; hypothèse d'optimisation localisée si coût significatif.
- **Frontière :** ne pas réouvrir le préfiltre C80 défavorable ni la priorité
  hub/paires neuves V140b rejetée ; ne pas réintroduire les reprises V143.

## AC-05 — Hub vers hub, sans mélanger les sites

**Décision postérieure à l'audit initial : AC05 adopté et intégré** dans
`master`, sous C121 uniquement, avec le chemin V86 historique préservé
quand C121 est désactivé. B20×10 isolé et 40×4 de confirmation n'ont pas
montré de perte économique ou de surcoût opcode démontrés ; le cumul
AC04-B+AC05 a ensuite passé son 20×10 économique et son 10×4 opcode.
Le statut « aucun correctif adopté » ci-dessous reste le constat
**historique au moment de l'audit**, non le verdict final.

**Statut : AUDIT TERMINÉ (11/10), aucun correctif adopté.** Les curseurs
`hubHubI/J` parcourent le triangle `i<j` sans omission ni doublon d'indice
sur **2 880 comparaisons figées** ; rejets connectés symétriques et
reprises/deadline validés. Une trace existante graine 42×3 ans donne
**12 500 794 opcodes `hub_hub` sur 398 invocations, dont 397 yields**,
sans dénominateur apparié de paires. **Travail V86 inutile sous C121
identifié statiquement** : `hubAvgIncome` est recalculé à chaque tranche
alors que ses déductions sont conditionnées par `!C121_AIR_ECONOMICS`.
Gain VM marginal et neutralité non qualifiés, aucun `.nut` ni Docker relancé.
[Audit, tests et mesure AC-05](ac05_air_hub_hub_resume_audit_20261011.md).

**Question fermée :** le parcours `hubHubI/J` finit-il et maintient-il une
fois chaque paire non orientée ?

- **Propriétaire :** `OpexAirPlansHubToHub`
  (`air_planning.nut:1617–1935`) et état de reprise hub→hub.
- **Travail :** vérifier initialisation `j=i+1`, dernière paire, reprise
  après suspension, exclusion de paires liées et calcul des marges des hubs.
  Comparer les candidats et opcodes à entrée figée.
- **Livrable :** preuve d'exhaustivité/absence de doublon, ventilée par
  rejets ; ne corriger que le défaut vérifié.
- **Frontière :** ne pas changer les calibrages de revenu, `MAIL15` ou
  le modèle économique C121 ; aucune révision du score AIR ici. V143 a montré
  un bénéfice à réexaminer le début des paires hub-hub lors des changements.

## AC-06 — Invalidation et reprise du scan

**Décision postérieure à l'audit initial : aucun portage AC06.** Le défaut
late-ack est confirmé par modèle ; les scénarios Save/Load moteur OFF/ON
sont sains, sans exposition directe d'un événement tardif dans les logs.
AC06 v1 est rejeté pour surcharge opcode systématique (+451 médian), v2
réduit ce coût à +32 opcodes mais ne le supprime pas, et v3 redevient
défavorable globalement. Le travail d'optimisation demandé (copie profonde,
allocations et filtres Squirrel, tableaux/AIList) a été mené et documenté
sans nouveau correctif adopté. Le statut suivant est l'**audit initial**.

**Statut 11/10 : audit de cycle de vie terminé, risque C76 late-ack ouvert,
sans correctif.** Le scan C78 continue malgré événements ou mois nouveau ;
Save/Load jette volontairement le curseur et force un nouveau catalogue.
La fixture (8 tests, 37 avec voisins) expose qu'un événement survenu après
le refresh initial peut être **acquitté** lors de l'apply sans avoir été pris
en compte par ce scan. Fréquence/conséquence économique/opcodes non établies,
aucun comportement changé. [Rapport et tests AC-06](ac06_air_catalog_invalidation_20261011.md).

**Question fermée :** les événements/reprises font-ils recommencer un scan
inutilement ?

- **Propriétaire :** orchestration `OpexAI::_dispatchCatalog`
  (`scheduler_tasks.nut:233–460`), états C76 et `persist.nut`.
- **Travail :** établir l'effet de `_portfolioInvalidated`, `_lastCatalogMonth`,
  C76, capital et Save/Load sur la durée de vie du curseur ; tester séparément
  chantier, changement de mois et Load. Vérifier qu'une interruption justifiée
  redémarre proprement et qu'aucune complétion ne disparaît silencieusement.
- **Livrable :** tableau des événements démarrant, interrompant ou annulant
  une génération ; preuve Save/Load si un état est modifié ; correctif isolé
  seulement si une invalidation inutile est démontrée.
- **Frontière :** ne pas changer les curseurs AC-02 à AC-05, les conversions
  de projets ni remplacer le protocole C76. Le refresh annuel pendant un
  scan actif testé par V143 est clos et ne doit pas être relancé.

## AC-07 — Publication partielle du vivier AIR

**Statut : audit terminé sans correctif (11/10).** Partition V141 testée
sur **5 760 configurations figées** : conservation des projets non-AIR,
des clés transférées et des alternatives, avec doublon de préfixe
AIR_RAIL **explicitement reproduit** et accepté comme exception.
Coût absolu résiduel `pub.filter` non identifiable dans les traces
actuellement accessibles ; baisse relative historique V141 −25 à −31 %,
V142 rejeté et non retesté. Pas de changement de production.
[Rapport et fixture AC-07](ac07_air_partial_publish_audit_20261011.md).

**Question fermée :** entre deux tranches, le vivier publié conserve-t-il
exactement ses projets valides et leur classement lorsque de nouveaux plans
arrivent ?

- **Propriétaire :** `OpexAir0310PublishIncremental`
  (`projects_update.nut:440–675`) et branche `partialPending` de
  `OpexC78ContinueCatalogAirRebuild` (`scheduler_tasks.nut:89–150`).
- **Travail :** comparer premier lot, lot supplémentaire, transition du
  bootstrap AIR_RAIL et `apply` final sur un même état ; vérifier les clés,
  groupes, doublons, projets perdus, ordre de concours et portée des champs
  rafraîchis par V141. Mesurer le coût *résiduel* de `pub.filter` après V141
  sans refaire sa qualification déjà acquise. V142 a déjà montré que
  regrouper les publications altère les décisions et échoue à la porte A.
- **Livrable :** fixture de conservation du vivier, inventaire précis des
  exceptions justifiées et coût par republication ; ne proposer une nouvelle
  optimisation que si elle est indépendante de V141 et matériellement exposée.
- **Frontière :** ne pas modifier le scheduler d'invalidation AC-06, les
  curseurs de génération, les prix, le score ou le défaut V141. Ne pas relancer
  la coalescence V142.

## AC-08 — Catalogue matériel (chantier distinct, priorité basse)

**Statut : audit terminé, aucune optimisation justifiée (11/10).**
Compatibilité et ordre conservés sur **4 800 catalogues synthétiques** :
priorité gros avion sur grands aéroports, gros interdit sur petits,
alternatives dans l'ordre du moteur, frontière C85 séparée. Diagnostic
actuel 42×3 : **3 émissions `_refreshAir`**, sans coût unitaire
isolé ; ancien profil de catalogue 1970–1989 : **149–161 opcodes
`ops_airports`** et 1 099–1 339 `ops_engines` par relevé
(instruments anciens, pas `_refreshAir` actuel). Gain potentiel non
démontré, ne pas modifier la sélection.
[Rapport et fixture AC-08](ac08_air_material_catalog_audit_20261011.md).

**Question fermée :** la sélection des avions/aéroports dans
`OpexCatalog::_refreshAir` consomme-t-elle assez d'opcodes pour justifier un
refactoring ou une optimisation ?

- **Propriétaire :** `catalog.nut:634–765` et l'appel
  `OpexCatalog::refresh` ; contrôler les consommateurs de
  `airCombos`, `airPlaneChoicesByAirport`, `airPlaneFrontierByAirport`.
- **Travail :** mesurer fréquence et coût du refresh au défaut ; vérifier
  les invariants de compatibilité avions/grands et petits aéroports et
  l'ordre des choix. La mesure V141 n'attribue que **deux refreshs matériel
  en trois ans** : si leur coût est négligeable, clore sans optimisation.
- **Livrable :** bilan coût/fréquence et décision motivée ; si refactoring
  purement structurel, préserver mêmes choix et ordre et chiffrer les opcodes.
- **Frontière :** ne pas modifier les calculateurs C121, les préférences
  de flotte, l'algorithme de projets ou la frontière C85 historiquement non
  adoptée.

## Règles communes d'exécution et d'acceptation

1. Chaque mandat commence **en lecture seule**, avec état Git, code actif,
   consommateurs, journaux et résultats existants. Une observation ancienne
   ou une trace partielle ne suffit pas à déclarer une boucle infinie.
2. **Un seul changement causal par campagne**, ancien comportement conservé
   pendant l'essai ; si une variante est introduite, réglage isolé à défaut
   `0`, même code et tous les autres défauts actuels dans les deux bras.
   Pré-enregistrer métriques, budget, graines, règles et provenance.
3. Pour un correctif technique, fixtures/contrats ciblés puis smoke Docker
   1×1 Squirrel ; Save/Load dès que les curseurs ou états transitoires changent.
   Évaluer les **opcodes**, y compris les coûts induits sur les autres tâches,
   à données comparables ; vérifier le vivier et les décisions avant de
   conclure à une neutralité.
4. Si le but est de **gagner des opcodes**, démontrer le gain sur le poste visé,
   puis satisfaire le 20×10 apparié complet et sain et les critères dédiés
   de non-perte économique du §4 d'`AGENTS.md`. Un changement comportemental
   recherchant un gain économique suit V102, A **40×3** `gain_short` puis
   B **20×10** `non_erosion` si A passe. Une qualification d'un lot ne
   qualifie aucun autre lot.
5. Aucun nouveau test coûteux si les preuves existantes suffisent. Sur ce PC :
   Docker local au maximum **10 CPU / 10 workers**, **une campagne à la fois** ;
   conserver les bundles et résultats uniques. **Ne pas empiéter sur la
   campagne C121 territoire d'abord actuellement en cours de qualification**.
6. Ne pas fusionner mécaniquement une optimisation avec V141 ou avec une
   expérimentation rejetée ; ne pas relancer les deux formules de score RAIL
   rejetées ni V142/V143. Pour chaque lot, mettre à jour sa ligne de suivi et les preuves,
   puis décider séparément de son maintien, adoption ou rejet.

**Ordre pratique :** AC-01 et AC-06 permettent de distinguer une interruption
du scan d'une lenteur réelle ; AC-02 à AC-05 sont des audits indépendants des
quatre unités de génération et peuvent être distribués en parallèle. AC-07
traite seulement la publication ; AC-08 est différé tant qu'aucun coût matériel
important n'est observé.
