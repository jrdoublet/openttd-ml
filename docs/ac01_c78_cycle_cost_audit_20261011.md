# AC-01 — coût du cycle C78 et rôle des reprises hub (11 octobre 2026)

**Décision : audit terminé, aucun correctif à proposer sur le cycle de vie.**
Les traces historiques permettent de hiérarchiser les coûts et V142/V143
montrent qu'une réduction du travail apparent peut détériorer le portefeuille.
Elles **ne permettent pas** d'isoler le coût ni la rentabilité de *chaque*
réinitialisation du snapshot hub sous le défaut courant V141. Ce manque de
granularité est explicite : ne pas lui substituer une estimation inventée.
AC-01 ne justifie donc ni une sonde permanente, ni une nouvelle campagne A/B.

## 1. Sources et comparabilité

| Source | Portée vérifiable | Limite |
|---|---|---|
| `docs/opcode_profile_c121_20261002.md`, §2, `sweeps/analyse_opcode_profile.py` | Profil **antérieur à V141**, cinq graines × six ans, moyennes par graine ; `AIR_LIGHT` par phase et budget annuel | Ne représente pas la charge actuelle au défaut V141 ; les fichiers bruts `opprofile_c121_5x6_20261002.artifacts` n'étaient pas présents dans cet arbre de travail lors de l'audit |
| `docs/taches.md`, V141 ; `docs/journaux/journal_2026-10-11.md`, V141 | Mesure spécifique de republication : ~150 `catalog.rebuild` par an, la plupart partiels ; V141 adopté au 20×10 | Ne mesure ni le coût d'un snapshot invalidé ni ses nouveaux projets rentables |
| Journal du 11/10, V142 | Spans et porte A **40×3** pour la coalescence, `fail_primary` | Les postes économisés se déplacent vers d'autres tâches ; décisions différentes |
| Journal du 11/10, V143 | Smoke puis porte A **40×3** pour les curseurs, et smoke refresh seul | Les 29 vs 18 avions hub-hub sont une corrélation de portefeuille, **pas** un rendement par invalidation |
| `scheduler_tasks.nut:15–230`, `air_planning.nut:995–1205`, `:2325–2543`, `probes.nut:866–885` | Chemin exact des phases, reprise, publication et compteurs conditionnels | Source statique, pas une mesure supplémentaire du comportement réel |

L'archive présente localement les rapports et les scripts d'analyse, mais
pas les journaux bruts V141–V143 nécessaires à une ventilation rétrospective
par génération/événement. Aucun accès à un nouveau banc n'a été nécessaire
ni engagé : le chantier C121 utilise déjà le budget Docker.

## 2. Résultats chiffrés déjà acquis

### Profil AIR ancien : ordre de grandeur, **pas coût actuel**

Le profil du 2 octobre attribue **55,2 millions d'opcodes AIR sur six ans
en moyenne par graine**, soit **9,2 M/an** sur ce profil ; le budget IA
complet représentait **405,9 M sur six ans**, soit **13,6 %** pour cette
planification AIR. Les postes ne doivent pas être additionnés aux coûts de
`catalog`/`projects` sans vérifier le chevauchement des périmètres.

| Phase AIR | M opcodes / 6 ans / graine | Part des 55,2 M |
|---|---:|---:|
| `new_pairs` | 15,6 | 28,3 % |
| `hub_site` | 13,5 | 24,5 % |
| `hub_discover` | 11,9 | 21,6 % |
| `hub_hub` | 10,5 | 19,0 % |
| `sites` | 2,5 | 4,5 % |
| `prepare` | 0,7 | 1,3 % |
| Résidu de ventilation/arrondis | ~0,5 | ~0,9 % |

Les trois phases hub représentent **35,9 M/55,2 M = 65,0 %**. Cela borne
la taille du poste à examiner : même historiquement, **35,9 M n'est pas le
coût des reprises**, car ces phases incluent les premières évaluations utiles.
Leurs chiffres ne permettent ni le nombre de redémarrages ni les opcodes
évitables sous V141.

### Mesures actuelles documentées de publication et de cycle

- **V141, adopté** : environ **150 reconstructions/publications par an**, très
  souvent après **un seul plan AIR neuf**, avec **72–92 plans antérieurs**
  reconvertis à tort ; **0 projet invalidé sur ~37 000 contrôles de publication**
  (à ne pas confondre avec les invalidations du snapshot hub).
  V141 évite cette reconversion : `pub.filter` **−25 à −31 %**, soit environ
  **1,3 M opcodes/an/partie** sur la mesure instrumentée. Son 20×10 passe les
  critères de neutralité économique, sans être une mesure de redémarrage hub.
- **V142, non retenu** : coalescer les publications baisse `task.catalog`
  d'environ **50 %** et `catalog.rebuild` de **22 à 29 %**, mais `loop.orch`
  monte de **25 %** ; **467** divergences de `candidateGroups`, **36** de
  capital, **1** de `best`. Porte A 40×3 : **+44,0 k£/an**, 24/16,
  p=0,17, IC95 **[−23,6 ; +111,8] k£**, seuil utile 77,3 k£ :
  `fail_primary`. Économies locales ≠ neutralité globale.
- **V143, non retenu** : le curseur hub corrigé parcourt **1017/1184** paires
  au lieu de **112/1134**, sans finir le scan en cinq ans ; porte A 40×3
  **−63,9 k£/an**, 12/28, Wilcoxon p=0,013, IC95 bootstrap
  **[−127,4 ; +6,3] k£**, valeur **−2,7 %** : `fail_primary`.
  Référence : **29 avions hub-hub**, contre **18** avec le mécanisme de
  reprise V143. L'observation soutient le rôle de **réévaluation du haut du
  vivier** ; elle ne prouve pas que chacun des 11 avions manquants provient
  d'une invalidation déterminée ni que leur profit isolé vaut 63,9 k£.
- **Refresh annuel V143 seul** : smoke 2×5 **−252 k£/an**, 0/2,
  valeur −13 %. Résultat d'alerte, non une porte A statistique ; le smoke
  était sur une version légèrement différente de la porte A scan.

## 3. Cause exacte dans le code : deux échelles de reprise

1. **Génération C78** (`scheduler_tasks.nut:15–69`) : crée une table
   `c78AirRebuild` portant `phase=primary`, `cursor`, `plans`, `airOps`,
   `partialPending`. Tant qu'elle existe, `_dispatchCatalog` appelle sa
   continuation **avant** la garde de fraîcheur et le refresh matériel
   (`:247–265`). Une tranche bornée passe dans `OpexAirPlans` (`:181–209`).
2. **Publications intermédiaires** (`:89–150`) : lorsqu'une tranche produit
   de nouveaux plans, `partialPending` déclenche une publication au passage
   *suivant* et rend la main sans faire de nouvelle tranche. Elle garde le
   même `cursor` C78 ; elle ne marque pas le scan terminé.
3. **Snapshot hub** (`air_planning.nut:997–1010`, `:1141–1205`) : une signature
   compacte `nombre de lignes AIR vivantes : nombre d'aéroports` est comparée
   au snapshot mémorisé. Même combo/signature ⇒ `reuse` ; même combo avec
   signature différente ⇒ `invalidate`, remise à zéro des indices
   `hubSiteI/J`, `hubHubI/J` et mémorisation des paires hub déjà retenues.
   **C'est un redémarrage local des bras hub au sein de la génération C78,
   non une recréation systématique de `c78AirRebuild`.** Une signature identique
   ne garantit pas une topologie identique : les effectifs peuvent coïncider ;
   aucune correction comportementale n'est proposée sans preuve d'exposition.
4. **Fin normale** (`air_planning.nut:2253–2261`, `scheduler_tasks.nut:210–230`,
   `:154–179`) : `cursor.done` après `OpexAirPlansFinalize` ; éventuellement
   `fallback` sous bootstrap AIR vide ; sinon `phase=apply`, reconstruction
   finale, accusé C76 et suppression du curseur. Les 0 `apply` rapportés dans
   les campagnes V141/V143 ne prouvent donc pas un blocage de cette branche
   en dehors des fenêtres observées.

## 4. Ce qu'on peut et ne peut pas attribuer

Les compteurs `AIR0310_HUB_SNAPSHOT` (`discover`, `reuse`, `invalidate`) ne
sont imprimés que sous `PROBE_SPAN_TRACE` ou `C56_TASK_TRACE`. `AIR_LIGHT`
émet une entrée et une sortie par invocation avec `gen`, `slice`, opcodes
par phase ; `CATALOG_COST_SLICE` expose opcodes de tranche, plans évalués,
publiés et en attente (`probes.nut:866–885`). Les identifiants `AIR_LIGHT`
sont transitoires à la VM : le lecteur doit les contextualiser par
session/compagnie et Save/Load avant d'agréger.

**Manque exact :** aucun compteur existant ne joint **chaque** invalidation
hub à ses opcodes *additionnels*, aux plans hub nouvellement retenus,
aux projets sélectionnés puis construits et au profit finalement réalisé.
Les totaux de phase ne sont donc pas un « surcoût V141 » ; les 29/18
avions ne sont pas un rendement attribuable par reset. Il serait erroné
d'extrapoler le profil du 2 octobre au défaut du 11 octobre.

Si un lot ultérieur **AC-04/AC-05** établit d'abord une optimisation exacte
qui préserve le rebalayage, le plus petit diagnostic complémentaire serait
une **agrégation sous sonde OFF**, sur le même bundle : signature avant/après,
compteurs d'invalidation et de paires revisitées, opcodes des phases, paires
réadmises, identités des plans retenus. La liaison avec les constructions
effectives demande une analyse *a posteriori* par clé de paire ; elle n'est
pas couverte ici et un traçage ne saurait justifier seul l'adoption.

## 5. Verdict AC-01

**CLÔTURER AC-01 comme audit sans modification de production.**

- Conserver V141 adopté, le comportement de remise à zéro des hubs et les
  publications intermédiaires nécessaires à la concurrence du portefeuille.
- Ne pas ressusciter V142 (`publish_coalesce`), V143 (`scan_completion`,
  `annual_refresh`) ni reprendre leurs campagnes ; leurs verdicts suffisent
  à rejeter **ces mécanismes**, pas toute optimisation future du hub.
- Ne pas installer une sonde ou lancer Docker pour le seul désir de voir
  un scan atteindre `apply` : l'utilité économique est l'objectif, et AC-01
  ne présente pas de correctif local admissible.
- Garder la mesure **par invalidation** comme *inconnue*, pas comme gain
  potentiel validé. Réexaminer uniquement si AC-04 ou AC-05 identifie un
  coût structurel économisable **sans perdre de candidats ni d'ordre**.

**Validation de cette livraison :** lecture seule du code, revue du profil
historique et des verdicts existants, chiffres et limites explicités.
Aucune modification `.nut`, aucun réglage ni valeur par défaut changés,
aucun test Docker, aucune nouvelle campagne, aucun commit/push demandé.
