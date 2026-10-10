# AIR — préparation du retrait de C115 (10 octobre 2026)

**État : inventaire statique et plan de retrait ; code C115 conservé.**
Référence lue : `master` à `95a6ad2`, avec des modifications locales
concurrentes non commitées. Cette préparation ne valide ni la neutralité
économique ni une économie d'opcodes. Elle complète le
[plan de nettoyage AIR P0](air_p0_legacy_cleanup_plan_20261010.md), qui concerne
principalement l'ancienne calibration des recettes et le prototype LOO.

## Ce qui est réellement inutilisé au défaut

`c121_air_economics=1` et `c121_catalog_incremental=1` sont les défauts
actuels des quatre difficultés (`info.nut`, vers 745 et 777). Les trois
générateurs de nouveaux plans (`air_planning.nut`, vers 908, 1555, 1844)
appellent alors `OpexC121CatalogChoice` ou `OpexC121ChooseRoutePlane`.
Ils **n'appellent pas** `OpexAirChooseRoutePlane`, qui héberge le replay C115.
Le cache C121 appelle directement `OpexC121ChooseRoutePlane`
(`air_catalog_c121.nut`, vers 425). Au défaut, les nouveaux devis AIR n'utilisent
donc plus la décision économique C115.

En revanche, le réglage **`c115_air_c100_capital_replay=1` reste déclaré et
chargé** (`info.nut:643-648`, `settings.nut:354`). Il redevient actif quand
`c121_air_economics=0` : le chemin legacy des trois générateurs passe par
`OpexAirChooseRoutePlaneFull`, dont la branche C115 est vers 1871–1883.
Le toggle C121 est lui-même toujours sélectionnable à 0. Il serait donc
incorrect de qualifier l'ensemble du code C115 d'inaccessible.

Deux appels supplémentaires à `OpexAirChooseRoutePlane` existent dans la
sonde V95 et un dans sa recherche diagnostique (`air_planning.nut`, vers
2034, 2195, 2205). Ils ne construisent pas les trois bras AIR C121 mais
doivent être traités avec la sonde, pas effacés par une substitution textuelle.

## Inventaire de retrait ciblé

| Élément | Situation actuelle | Action possible lors du retrait |
| --- | --- | --- |
| `info.nut::c115_air_c100_capital_replay`, `settings.nut::C115_AIR_C100_CAPITAL_REPLAY`, `globals_pre.nut` | Réglage historique à 1 | Retirer ensemble déclaration, chargement et global **après décision de fin de compatibilité C121=0/C115** ; ne jamais recycler le nom du réglage. |
| `air_engine_choice.nut::OpexC115ChooseRoutePlane` (vers 1417–1460) | Algorithme C68/replay C100 conditionné par `OpexC69CachedKDec` ; appelé depuis une unique branche de `OpexAirChooseRoutePlaneFull` | Supprimer méthode et branche de dispatch (vers 1871–1883) une fois le profil legacy retiré. |
| `air_engine_choice.nut::OpexAirChooseRoutePlane` (vers 446–452) | C115 désactive le mémo C80 historique | Enlever seulement le terme C115, préserver les autres causes d'invalidation du mémo. |
| `air_engine_choice.nut::OpexAirChooseRoutePlaneFull` (vers 1795) | C115 inhibe la comparaison C104 | Retirer la garde C115, mais conserver le chemin et les contrôles propres à C104. |
| `settings.nut::C69_TRACK_BUILDS` (vers 525–526) | C115 est une cause d'activation parmi C69, C72, C97, C116 | Retirer uniquement le terme C115. Le défaut `c69_decision_bottleneck=1` continue d'activer l'historique de constructions. |
| `selection_diagnostics.nut::OpexAmortProbeBegin` (vers 24–29) | Son support diagnostique exige explicitement C115 et C121 désactivé | Décider si la sonde du profil C115 est archivée ou redéfinie ; retirer la condition sans autre décision change son périmètre. |
| `air_engine_choice.nut::OpexC116LegacyDecisionRunner` et `OpexC116LogProjectProbe` (vers 1331, 1360) | Leur seul appel métier relevé est actuellement **dans C115** | Candidats secondaires à retirer **si** la sonde C116 est elle aussi abandonnée ; vérifier de nouveau tous les appels lors du patch. |

**À conserver :** `OpexC104BestAirEngine`, employé par C104/C105/C111 et
d'autres expériences ; `OpexC69ComputeKDec` et `OpexC69CachedKDec`, employés
notamment par `air_economics_c121.nut` (vers 198, 686, 1244) et le portefeuille ;
`C69_BUILD_DATES` et sa persistance `c69BuildDates` ; les chemins C68 et
`OpexAirChooseRoutePlane` eux-mêmes tant que leurs autres utilisateurs vivent ;
les états, sondes, fonctionnalités de C118/C120 et la logique C121.

## Points où une suppression naïve changerait le comportement

1. Le défaut C69 est à 1 : `C69_TRACK_BUILDS` reste actif même sans C115.
   Mais sous la combinaison utilisateur `c69_decision_bottleneck=0` et
   `c115_air_c100_capital_replay=1`, le suivi des constructions était encore
   activé par C115. Le retirer peut changer le **K_dec de C121**, même si
   C115 n'effectuait pas son choix moteur. Vérifier ce cas explicitement.
2. La sauvegarde contient `c69BuildDates` (`persist.nut`, vers 812, 869,
   944–946), repris après `OpexLoadSettings`. Ce champ est partagé et doit
   être conservé ; il n'existe pas de champ `C115` propre dans `persist.nut`.
   L'ancien réglage explicite `c115_air_c100_capital_replay` dans les fichiers
   de configuration/bras de bench peut néanmoins cesser d'être accepté.
3. Les sondes C104, C116, V95 et `fleet_amort_shadow_probe` utilisent la
   politique C115 comme témoin ou condition de support. Plusieurs anciens
   lanceurs `sweeps/run_c115_*`, `run_c116_*`, `run_c121_air_economics_*`
   et les tests `test_c115_air_c100_capital_replay.py`,
   `test_c116_air_incremental_probe.py`, `test_c104_air_c100_compare_probe.py`
   référencent toujours ce réglage. Les scripts historiques peuvent rester
   archivés pour la provenance ; ils ne seront plus exécutables sur le nouveau
   code si leurs paramètres disparaissent.
4. La disparition d'un bloc Squirrel dans un module chargé peut affecter
   l'ordre/coût de compilation ; elle ne garantit aucun gain d'opcodes au
   runtime. Au défaut C121, C115 est normalement contourné à la génération :
   la réduction d'opcodes attendue sur ce chemin est proche de zéro, **à mesurer**.

## Déroulé recommandé

**Étape 0 — choix de compatibilité.** Acter explicitement la fin du support
du profil `c121_air_economics=0` avec C115 actif, et le sort des sondes qui
l'utilisent. Si le retour arrière C121=0 reste une option supportée, limiter
le travail à la documentation : le corps C115 est encore du code utilisé.

**Étape 1 — patch minimal isolé.** Dans un arbre de travail sans autres
expériences, supprimer seulement le toggle C115, sa méthode/son dispatch
et ses quatre gardes ou usages annexes, plus les seuls helpers devenus
orphelins après nouvel inventaire. Conserver C69 et C104 partagés. Adapter
les tests contractuels concernés et les lancements encore courants sans
écraser les fixtures/archives historiques. Aucun changement simultané du
facteur direct P0, des lissages 75/25 et 50/50, ni des prototypes RAIL.

**Étape 2 — vérification technique.** Comparer avant/après sous les défauts
réellement livrés (incluant `c121_air_economics=1`, C69=1) : tests de contrat,
compilation smoke Docker 1 graine × 1 an, premiers projets/avions et sondes
actives. Contrôler `rg` des anciennes références runtime ; exécuter aussi
`sweeps/save_load_roundtrip.py` sur une sauvegarde de l'ancien format,
avec les dates C69 conservées. Examiner séparément une matrice
`C121=1 × C69=0/1 × C115=0/1` **avant retrait**, puis le défaut **après**.
Une différence hors profils officiellement abandonnés empêche de qualifier
le retrait de purement structurel.

**Étape 3 — décision économique et opcodes.** Si toutes les décisions au
défaut et le Save/Load sont inchangés, documenter une parité par graine et
une mesure totale d'opcodes homogène ; appliquer les
[critères futurs](experimental_acceptance_policy_20261010.md) si une vraie
évolution du comportement reste. Ne pas baptiser une différence
non significative « équivalence ». Mettre à jour `docs/taches.md` et le
journal avec le résultat réel puis seulement proposer commit/push isolés.

**Livraison de cette préparation :** aucun retrait C115 ni changement de
réglage effectué, aucun Docker, aucune campagne A/B ; seul le plan est prêt.
