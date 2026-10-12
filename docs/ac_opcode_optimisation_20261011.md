# AIR catalogue — autopsie des surcoûts et pistes d'optimisation (11 octobre 2026)

## Contrat et statut

À la demande explicite de l'utilisateur, **un rejet pour dégradation d'opcodes
ne clôt pas l'anomalie métier** : chercher d'abord si le coût peut être éliminé
sans perte économique ni refactorisation de la stratégie. Les verdicts des
implémentations isolées AC04-A v1 et AC06 v1 sont conservés. Pas de gain exigé
mais une augmentation démontrée suffit à rejeter un nouveau candidat.

Les mesures ci-dessous sont des opcodes VM exécutés dans les postes de boucle
instrumentés, pas une mesure matérielle du CPU. Toujours comparer mêmes
graines, source gelée par paire, fenêtres annuelles clôturées, sondes identiques.

## AC06 — cause redondante très précise

- `scheduler_tasks.nut::OpexC78StartCatalogAirRebuild` prend le snapshot par
  `owner._c76SaveRevisions()` si AC06 est actif et la génération C76 full.
- Or `orchestrator.nut::_c76SaveRevisions` est conçu **pour Save/Load** :
  il alloue `consumedCopy`, parcourt tous les modes et couches, alloue une
  table par mode, recopie `_c76ModeConsumedRevision`, puis assemble les
  compteurs réels et acquittés. Le correctif AC06 n'utilise que les **sept
  compteurs de révisions** `towns/industries/lines/engines.{rail,road,air,water}`.
  Tout le reste est redondant au début d'une génération.
- Dans `OpexAC06AcknowledgeSnapshot`, le second parcours sur neuf modes appelle
  `_c76GetModeDeps(mode)`, recrée ses tableaux, puis pour chaque couche
  `OpexAC06SnapshotLayer(snapshot, layer)` effectue jusqu'à sept comparaisons
  de chaînes. Il faut mesurer s'il est justifié de spécialiser cette phase :
  elle reste nécessaire pour ne pas faire régresser une consommation C77
  concurrente, mais des tables temporaires peuvent être évitées.
- **Candidat AC06 v2** : construire un snapshot léger **de sept entiers**
  sans recopier `consumed` ni `ack` ; conserver les opérations `max(previous,
  snapshot)` en fin de scan. Éventuellement replier sur la fonction historique
  lorsqu'aucune couche n'a progressé après la photographie, si ce repli est
  prouvé identique pour tous les modes. Vérifier événements tardifs multi-couches,
  C77 concurrent, séries monotones, et Save/Load. Ne jamais conserver par
  référence le dictionnaire mutable `_c76Revisions` : ce ne serait **pas**
  un snapshot.
- **Preuve justifiant un essai :** sur 40 graines × 4 ans du candidat v1,
  **38/40** présentent un surcoût en 1970–1971, médiane **+451 opcodes**,
  **25** exactement +451. Cela indique une petite dépense systématique,
  compatible avec la copie des tableaux même en l'absence d'un événement
  tardif. Ce n'est pas à lui seul une attribution causale définitive.

## AC04-A — limiter les recomptages des hubs

- `air_planning.nut::OpexAirPlansPrepare` construit déjà l'index exact
  `hubIndex.routes` et `hubIndex.pairs` lorsque `C80_AIR_HUB_INDEX=1`.
  Cette option **est au défaut 1** depuis l'historique C80.
- `OpexAirPlansDiscoverHubs` a déjà un index `seenStations` pour les stations
  considérées. Les hubs dépassant `maxRoutes` sont sautés dans la première
  boucle **avant** insertion dans cette table, d'où le bug « orphelin ».
  Le correctif v1 crée un second appel au compteur pour chaque station de
  `AIStationList(STATION_AIRPORT)` qui n'a pas été marquée comme vue ;
  `OpexAir0310RefreshHubRoutes` recompte aussi les hubs considérés orphelins.
- **Piste rapide** : mémoriser les stations saturées au moment du premier
  comptage et les éliminer avant le parcours des supposés orphelins ;
  conserver le comptage réel pour celles dont l'existence de lignes est
  connue uniquement du second parcours (dont lignes mortes). Tester les
  transitions pendant les tranches et le snapshot V119, afin de ne pas
  réintroduire les stations devenues saturées ou écarter les vrais orphelins.
- **Piste index** : réutiliser `hubIndex.routes` et éviter les scans `foreach
  (other in lines)` par station lorsque l'index est présent. Si l'option C80
  est explicitement désactivée, construire au plus un index local cohérent
  sur la durée de l'appel et le revalider lors des reprises, plutôt que faire
  une opération O(nombre_de_stations × nombre_de_lignes). Comparer les cas
  où un `deadStreak >= 2` diffère entre la découverte et l'indexation.

## `AIList` vs tables / tableaux Squirrel : frontières à comparer

`AIStationList` **est déjà une AIList native** pour les aéroports. La NoAI API
offre `RemoveItem`, `RemoveList`, `HasItem`, `Valuate`, `KeepValue` et autres
filtres natifs (https://docs.openttd.org/ai-api/classAIList), mais il faut
comparer leur coût VM **sur les véritables tailles de listes**, la conservation
de l'ordre, et éviter la modification de la liste pendant une itération
(`SetValue` est explicitement documenté comme pouvant sauter des éléments).

- Candidat ciblé : filtrer dans une `AIStationList` native les stations vues
  ou saturées (`RemoveItem`), **avant** d'énumérer les seuls orphelins.
  Comparer au `if (st in seenStations) continue` actuel et vérifier la même
  séquence d'identifiants ; ne pas supposer qu'une API native est moins chère.
- Les tableaux `ctx.sites` et `ctx.hubs` contiennent des **tables structurées**
  (tuile, ville, routes, flags C83), dont l'ordre alimente les parcours de
  paires et les snapshots. Ils ne sont **pas substituables sans perte** à un
  `AIList` clé/valeur entier. Pour AC04-B la liste est bornée à 12 sites :
  une table temporaire d'ancres en O(1) est une hypothèse, mais son allocation
  peut coûter plus que comparer jusqu'à douze éléments ; microbench d'abord.
- Vérifier également les allocations `ends=[{...},{...}]` faites pour chaque
  ligne et combo dans la découverte des hubs : deux entrées temporaires par
  ligne sont potentiellement plus coûteuses que deux appels directs, mais
  c'est une optimisation transversale et **pas** une preuve du surcoût de
  AC04-A. Ne pas la mélanger à un correctif isolé.

## Protocole avant une v2 admissible

1. Isoler chaque optimisation sur un code/bundle distinct ; tests Squirrel
   de non-changement d'ordre, routes, C83, revisions C76 et Save/Load.
2. Microbench VM à état identique : `snapshot profond vs 7 entiers`,
   `AIList natif vs table seenStations`, `route index vs rescans`,
   mesures **par appel** et à tailles réalistes. Rejeter toute substitution
   native qui ne gagne pas réellement en opcode.
3. Duel global VM OFF vs variante v2 en Docker séquentiel sur les graines
   ayant exposé le coût ; ne pas effacer la preuve v1 et ne pas masquer une
   augmentation moyenne ou systématique. Puis qualification économique
   appariée suffisante si les décisions peuvent diverger ; pas de portage
   par défaut avant absence de dégradation étayée sur **les deux** critères.

**État initial** : autopsie statique des hotspots réalisée ; aucune des
alternatives v2 ci-dessus n'est encore qualifiée ni intégrée en production.

## Mesures des alternatives (état ultérieur du même jour)

**AC04-A v2** (`results/ac_opcode_opt_worktree_20261011`, bundle
`a1f558e5ec4f22fc297b8495f92f977d179adeddf64d51dcbf968edca4914b01`) :
103 contrats ciblés verts, 10×4 VM 20/20 parties saines. Sur 1970–1972,
delta global −875 972 opcodes, IC95 [−2 621 300 ; +904 325] : la moyenne
change de signe mais la neutralité n'est pas démontrée. **Plus important :
sur 1970–1971**, le delta de **+307 376 opcodes**, IC95 **[+92 855 ;
+609 554]**, 8 hausses, 1 baisse, 1 égalité, **confirme la régression
du correctif AC04-A v1** sur les mêmes dix graines, malgré le marquage
précoce et l'accès direct à l'index. Le surcoût n'est donc pas éliminé par
ces optimisations de boucle ; ne pas adopter AC04-A v2. Le contrôle externe
OFF entre deux bundles n'est pas bit-à-bit identique, aussi ne pas attribuer
causalement le changement de moyenne à la seule économie locale : chaque
verdict se fonde sur son A/B gelé interne.

**AC06 v2** (même bundle v2) : snapshot limité aux sept compteurs C76,
contre la copie Save/Load profonde. 10×4 sain, delta global 1970–1972
+4 970 opcodes, IC95 [−45 543 ; +60 422]. Sur 1970–1971,
**les dix graines ont exactement +32 opcodes**, IC95 [32 ; 32] ; la
surcharge systématique v1 (+451 médian) est presque supprimée mais le
critère sans seuil interdit toujours l'adoption. Une variante **AC06 v3**
conserve le snapshot léger et construit une table de correspondance des
sept couches une seule fois au lieu de refaire les comparaisons de noms
à chaque dépendance des neuf modes. 103 tests verts ; VM à qualifier
séparément avant tout verdict.

**AC06 v3 terminé : REJET** : même source v2 enrichie d'une table
`coveredByLayer` pour éviter les comparaisons répétées de chaînes,
bundle `1f84e9a02f27c78433f62c3366ea6fd2134540a86b9a7c967f9ff8b6daed5b72`.
10×4, 20/20 parties saines ; moyenne globale 1970–1972
**+191 250 opcodes** (+0,0996 %), IC95 bootstrap
**[+32 ; +573 685]**, fenêtre 1970–1971 **+32 opcodes** ; aucun
gain d'innocuité comparé à v2. Les 103 tests restent verts, mais la
régression opcode est démontrée. Il serait inexact de reprendre le
`gain_short fail_primary` historique comme motif de rejet : c'est le
diagnostic VM apparié qui tranche.

**Bilan des pistes réellement étudiées :** `AIStationList` est déjà une
AIList native ; la déduplication via table `seenStations`, l'index C80
et le marquage anticipé ont été testés en AC04-A v2. Les tableaux
structurés de hubs/sites ne peuvent pas être remplacés gratuitement par
des AILists d'entiers. AC06 v2 prouve que la sérialisation profonde était
une redondance coûteuse (+451 → +32 opcodes constants) ; v3 montre que
mutualiser les filtres par noms ne suffit pas et peut accroître le coût.
**État au 11/10 :** ni AC04-A v2 ni AC06 v2/v3 ne passaient la règle
sans tolérance opcode ; aucune de ces alternatives n'était intégrée.
**Décision postérieure du 12/10 :** adoption explicite d'**AC06 v2**
malgré +32 opcodes constants en 1970–1971, avec intégration locale et
rollback ; la v3 et AC04-A restent rejetés. Voir
[le dossier d'adoption](ac06_v2_adoption_20261012.md). Les bundles gelés et
rapports des alternatives restent conservés dans le worktree d'optimisation.
