# Tâches — réduire l'écart avec AAAHogEx

État courant actualisé le **2026-09-21**. Ce fichier est la **seule liste autoritaire du
travail restant**. Les sections datées du 13 au 18 septembre sont conservées pour la traçabilité,
mais leur ordre de priorité et leurs mentions « à faire » ne prévalent pas sur l'état courant
ci-dessous.

Avant de rouvrir une piste, rechercher son nom et ses réglages dans
[le journal du 13 septembre](journal_2026-09-13.md) **et** dans
[l'archive du 9 septembre](taches_archive_2026-09-09.md). L'archive sert à retrouver les
implémentations et les raisons des décisions ; **aucun résultat antérieur au 09/09 ne prouve
la performance actuelle**. Les journaux quotidiens conservent le détail des expériences.

## État courant — 2026-09-21

La séquence P0/P1 du 13 septembre est désormais **historique** : C66 est qualifié/clos. Le
chantier AIR post-C68 sur la frontière capital→profit, `AIR_BEST_EQUIPMENT` et le cycle de vie
associé est **abandonné le 2026-09-21** après résultats économiques négatifs répétés. La base de
reprise est `b68fafb` : master + C68 adopté (`air_route_plane_selection=1`) + suppression des
feeders. Les listes de revue restent des documents historiques ; elles ne doivent plus être lues
comme une file active.

| Statut courant | Chantier | Travail restant / règle de reprise |
|---|---|---|
| **PRIORITAIRE — 2026-09-21** | **C80 — orchestrateur à double registre (intentions / exécution)** | Choix utilisateur (option 2 de son plan) : file réactive (événements C76/C77) et file de fond (dérive, scans, maintenance) pour **décider quoi faire** ; registre d'exécution de travailleurs résumables et sérialisables, chacun avec son échéance locale, pour **découper les calculs lourds** (A\* rail, régénération par mode, `town_growth`). Un événement peut s'intercaler entre deux tranches d'un A\*. Contrat à écrire avant code. |
| **PRIORITAIRE — 2026-09-21** | **C77 — déclenchement des candidats opportunistes** | Un événement ou un changement mesuré produit **tout de suite** les candidats de l'entité touchée, insérés au vivier sans régénération complète et constructibles sans attendre le tour suivant (~45 j). Détail : [§ C76-C77](#c76-c77). Dépend de C76. |
| **VALIDÉ — ÉTAPE 2 À FAIRE — 2026-09-21** | **C76 — gestion des événements : consommer les invalidations** | Étape 1 faite (`docs/17_evenements_regeneration.md` §6) : 53-76 % des régénérations sans changement, ~145-180 j de jeu/an/partie de régénération ; C3 échoue (tête du classement instable) mais **C76 validé tel quel par l'utilisateur**. Étape 2 à intégrer à l'orchestrateur C80. |
| **EN COURS — 2026-09-21** | **C75 — plusieurs chantiers par passe en phase riche** | Choix utilisateur : τ = durée réelle entre deux passes `projects`. Continuer à construire dans la liste déjà classée tant que le projet suivant coûte moins que K_dec et reste finançable. `docs/16_bilan_volume.md` §6-§7. |
| **À FAIRE — 2026-09-21** | **C78 — chronologie décision par décision contre AAAHogEx** | 1970-1973 en duel : chaque chantier des deux IA (date, mode, villes, coût, avions) et le revenu de chaque ligne au fil du temps ; journal d'AAAHogEx via `-d script=4`. Question : quand et où l'écart de revenu aérien se creuse. |
| **ANNULÉ — 2026-09-21** | **C79 — feeders de ville vers l'aéroport** | Annulé par l'utilisateur. Aucun réglage feeder ne subsiste : `feeder_enabled`, puis `feeder_unlock`, `feeder_pricing`, `feeder_portfolio` ont été retirés le 2026-09-17 (`b48d8d5`) ; code récupérable dans `b48d8d5~1`. Reste seulement `air_joined_stop_limit` (0 à 2, défaut 2 : arrêts de bus joints à l'aéroport, sans bus). |
| **EN PAUSE — 2026-09-21** | **C69 goulot de décision (+ bis) et C70 calibration** | Non adopté : deux 20×10 duel à 12/20 (`fail_primary`), gain moyen +87,6 et +111 k£/an. Plus d'aéroports, moins de véhicules. Reprise : cause de la flotte manquante (`W` contre cadence), puis C69 bis par-dessus C72 si C72 est adopté. `docs/11_goulot_decision.md` §17-§19. |
| **NON ADOPTÉ — 2026-09-21** | **C72 choix de l'avion par route** | 20×10 duel contre le défaut : ROI −1,9 k£/an, score C69 −4,5 k£/an, 11/9 tous deux (`fail_primary`) ; valeur +6,8 % et +3,2 %, non significative. Le 5×6 solo (+292 et +145 k£) ne s'est pas confirmé. `docs/15_choix_avion.md` §5. |
| **ABANDONNÉ — 2026-09-21** | **AIR post-C68 — frontière capital→profit réseau** | Retour à `b68fafb`. Ne pas reprendre le λ global sans nouvelle formulation et nouvelle preuve indépendante. |
| **CLOS / RETIRÉ** | **Opcodes AIR / sélecteur de projets** | Les caches, heaps, enveloppes et snapshots ajoutés pour la frontière/lifecycle sont abandonnés avec ces politiques. |
| **COMMENCÉ — EN PAUSE** | **C61 AIR : délai/capacité aéroport** | Mesurer rotations, attente, demande et occupation avant de toucher `airportDelayDays` ou la cadence. |
| **COMMENCÉ — AUTRE SESSION** | **C61 Route / town growth** | Recalibrage déjà avancé ; le reliquat sur les stations actives est traité séparément. |
| **FAIT — 2026-09-20** | **21.1 — constante rotor/hélico** | `AIR_ROTOR=6` aligné, commentaire corrigé et test synthétique hélicoptère tête+ombre+rotor ajouté ; 8/8 hôte et Docker. |
| **FAIT — 2026-09-20** | **21.2 — `prepare_frozen_campaign`** | Test unitaire isolé du gel complet ajouté : IA, harnais, bibliothèque BaNaNaS synthétique, empreintes, manifeste et descripteur local ; 11/11 hôte, 11 tests dans Docker dont 1 skip Git CLI attendu. |
| **FAIT — 2026-09-20** | **C45 reliquat — persistance subventions** | L'état comportemental `_activeSubsidies` est déjà persisté par Save/Load au défaut `save_full_state=1`. Les compteurs `_subsidyStats` restent volontairement transitoires : télémétrie uniquement, rapportée seulement sous `EVENT_SUBSIDY_PROBE`, forcé à `false`. |
| **FAIT — 2026-09-20** | **C52 reliquat — crash/non rentable** | Revalidation courante close : handlers sains, 5×6 complet, aucun défaut de service reproduit ; politique laissée à 0. |
| **FAIT — 2026-09-20** | **C60 — filtre municipal** | Sonde corrigée pour appliquer le vrai prédicat de tolérance municipale. 5×6 courant : 145 501 contrôles, dont 1 719 notes VERY_POOR/APPALLING, mais 0 refus réel ; filtre laissé désarmé. |
| **NON DÉMARRÉ** | **C59 — ordres contextuels** | Corréler chargement, attente et profit avant toute politique dynamique. |
| **NON DÉMARRÉ** | **C61 Rail — géométrie NOSPOT/TRACKFAIL** | Examiner les échecs réellement exposés avant un projet général de jonctions. |
| **CONCEPTION SEULEMENT** | **C67 — carte par blocs / remplacement de Lakes** | Implémentation non commencée ; d'abord mesurer 5×5 vs 10×10, RAM/opcodes/précision. |
| **DIFFÉRÉ / CONDITIONNEL** | **C64, C42 bis, C55 reliquat, C43/E3 restant** | Reprendre seulement sur exposition mesurée ; `loop_budget` est déjà clos/non adopté. |
| **DORMANT / NON EXPOSÉ** | **M2, M5/G2, M6, M7/11.3, B6/06.12** | Aucun lot autonome ; traiter seulement avant réactivation. |

<a id="c76-c77"></a>
### C76-C77 — Événements et candidats opportunistes (ouvert le 2026-09-21)

**Constat mesuré** (`docs/16_bilan_volume.md` §6-§7, sondes C73 et C74, 3 graines × 10 ans) :
à partir de 1975, un tour de la file dure **45 à 52 jours de jeu** et ne construit qu'un projet,
soit ~7 à 8 chantiers par an pendant que la caisse monte à 11 M£. `catalog` (31 % du temps) et
`projects` (23 %) régénèrent chacun le vivier ; `town_growth` en prend 28 %.

**État du code, vérifié le 2026-09-21 :**

- `_dispatchCatalog` ne saute son tour que dans le même mois ; avec un tour de 45 jours, il
  rafraîchit **tout** le catalogue (`OpexCatalog::refresh` : cargos, rail, villes, industries, route,
  air, eau) et **régénère tous les candidats** (`_rebuildProjects`) à chaque tour. Le catalogue
  coûte peu ; les ~2,8 M opcodes par passe sont la régénération des candidats.
- Les événements `IndustryOpen/Close`, `TownFounded`, `EngineAvailable`, subventions et véhicules
  sont reçus et routés, mais **`_markDirty` ne fait rien hors sonde** (`C39_INVALIDATION_PROBE`) et
  son état n'est consommé par aucune tâche. Le seul effet réel d'un événement est
  `_portfolioInvalidated`, qui **avance** une régénération complète : les événements ajoutent des
  régénérations, ils n'en évitent aucune.
- Les sous-catalogues et révisions par couche sont **conçus** (`cible.md` §8, registre C41.0 en
  sonde, essais C41.1-C41.3), pas livrés. La régénération indexée C48 (20×10, 10/10) était neutre
  à une époque où le goulot mesuré n'était pas le nombre de chantiers par an.

**C76 — consommer les invalidations.** Contrat à écrire avant code :

1. une révision par sous-catalogue (`cargos`, `towns`, `industries`, `rail`, `road`, `air`,
   `water`) et par mode de candidats ; un rafraîchissement de sous-catalogue par couche au lieu de
   `refresh()` d'un bloc ;
2. `catalog` et `projects` ne régénèrent un mode que si une de ses dépendances a changé ;
3. **filet périodique** obligatoire (`cible.md` §8) : population et production changent sans
   événement ; il met à jour ces grandeurs et réévalue les candidats existants, sans tout
   régénérer ;
4. mesure préalable du gain : sur une partie instrumentée, combien de régénérations mensuelles
   ne correspondent à aucun changement de leurs dépendances, et combien de jours de tour on
   récupère.

**C77 — déclencher les candidats opportunistes.** Quand une occasion apparaît, produire tout de
suite les candidats de l'entité concernée et les rendre constructibles sans attendre le tour :

| déclencheur | candidats ciblés |
|---|---|
| `IndustryOpen` | lignes rail/route/fret depuis et vers cette industrie |
| `TownFounded`, ville qui franchit un seuil de population mesuré | aéroport, bus, rail pax de cette ville |
| `EngineAvailable` (moteur retenu par son sous-catalogue) | réévaluation des lignes et candidats du mode |
| `SubsidyOffer` | le candidat de la subvention, daté de son échéance |
| construction d'AAAHogEx dans une ville à un seul aéroport libre | prise du slot restant (course aux 2 aéroports par ville, erreurs 771, `taches.md` §771) |
| ligne en attente au sol durable (refus `W` levé, stock mesuré) | renfort de flotte de cette ligne |

Critère d'étape 1 (sonde) : nombre d'occasions par an, délai actuel entre l'occasion et sa prise
en compte (aujourd'hui jusqu'à un tour, ~45 j), et part des occasions prises par AAAHogEx pendant
ce délai. Un levier n'est codé que si ce délai coûte des occasions mesurées.

### Clôture AIR post-C68 — frontière, best equipment et cycle de vie (2026-09-21)

La branche expérimentale postérieure à `b68fafb` est archivée sous
`archive/air-frontier-2026-09-21`. La reprise fonctionnelle repart de `b68fafb`, qui contient C68
adopté (`air_route_plane_selection=1`) et la suppression des feeders. Les trois pistes suivantes
sont closes ensemble : `AIR_CAPITAL_FRONTIER`, `AIR_BEST_EQUIPMENT` et le cycle de vie AIR
upgrade/preview/Pareto/persistance qui dépendait de ce moteur multi-équipements.

La frontière capital→profit n'a pas corrigé le sous-investissement. Sur le 5×6
`diag_air_capital_frontier_c66_4_5x6_v3.json`, le profit annuel moyen recule d'environ
**267 k£/an** et le ratio de valeur de compagnie vaut **0,7229** (soit **−27,71 %**). Les variantes
ultérieures qui corrigent les conflits physiques et l'état économique restent négatives : environ
**−204 k£/an** sur l'isolat `isolate_air_capital_frontier_econstate_5x6.json`, puis environ
**−288 k£/an et 0/5 victoire** sur `diag_air_capital_frontier_lifecyclefix_5x6.json`. Le coût en
opcodes augmente fortement en parallèle ; l'optimiser davantage ne change pas le verdict
économique.

`AIR_BEST_EQUIPMENT` et le cycle de vie associé ne fournissent pas non plus de candidat à adopter.
Dans le 5×6 post-lifecycle, la baseline C68 reste devant d'environ **+308 959 £/an de profit annuel**
et **+1,31 M£ de valeur de compagnie** en moyenne. Le candidat utilise pourtant réellement les
nouveaux choix d'équipement (le moteur 218 apparaît sur **66/145 avions**) : l'échec ne vient donc
pas d'un chemin mort ou d'une absence d'exposition.

Leçons conservées pour une éventuelle reprise future :

- un λ global rejoue la famille de formulations déjà réfutée avec C35.4 ; sa cohérence théorique
  ne suffit pas à produire une meilleure politique sur le réseau réel ;
- élargir l'ensemble des avions sous un modèle AIR encore biaisé peut produire un **pire argmax** :
  plus de choix améliore l'optimisation du modèle, pas nécessairement le jeu réel ;
- la baseline a dérivé pendant l'exploration ; toute nouvelle piste doit repartir explicitement de
  `b68fafb`/C68 et annoncer son delta exact avant le premier banc ;
- `air_early_slot` est un mécanisme territorial concurrentiel : son effet doit être jugé en duel,
  pas dans un 5×6 solo où son coût peut apparaître sans bénéfice de verrouillage adverse ;
- les optimisations d'opcodes spécifiques à la frontière/lifecycle (caches, heap de λ, enveloppes,
  snapshots et télémétrie CF) ne sont pas des améliorations autonomes et ne doivent pas être
  rapatriées sur C68.

Le recalage route et le modèle physique de délai d'aéroport restent des chantiers séparés, chacun
derrière son propre drapeau et avec son propre 5×6 avant toute adoption.

**Contrôle du ménage `tension.nut` — non rapatrié.** La suppression de `tension.nut`,
`tension_scoring`, `shadow_pricing` et de leurs chemins morts a été portée puis testée avant commit.
Le smoke demandé **2 graines × 3 ans** réfute l'hypothèse de neutralité : le candidat nettoyé donne
sur la graine 42 `value=2 561 481`, `profit_year=1 454 938`, 50 véhicules et 36 gares, contre
`b68fafb` `value=2 940 277`, `profit_year=1 662 912`, 43 véhicules et 24 gares ; sur la graine 100,
le candidat donne `value=2 048 722`, `profit_year=1 217 187`, contre `b68fafb` `value=1 803 322`,
`profit_year=916 336`. Ce n'est donc pas bit-identique.

Le contrôle causal est net : `f9488de`, qui contient tous les rapatriements sûrs précédents mais
pas le ménage tension, reproduit **exactement `b68fafb` sur les deux graines et les deux métriques**
du même 2×3 (ainsi que véhicules, gares, score et note). La divergence apparaît donc avec le retrait
du travail Squirrel mort lui-même. Même avec les drapeaux à 0, enlever ces opérations modifie le
calendrier d'opcodes/suspensions et finit par changer la simulation. Le ménage tension est par
conséquent **abandonné comme refactor neutre** et n'est pas conservé sur la branche de retour.

## Référence historique — 2026-09-13

**Le retard économique est établi ; sa cause dominante ne l'est pas encore.** Le duel partagé
20 graines × 5 ans du 13 septembre donne les résultats suivants, recalculés depuis les
20 paires de [la référence](../results/bench_1v1_5y_20seeds_reference.json) :

| Dernier checkpoint : 1974-12-01 | OpexAI, moyenne | AAAHogEx, moyenne | Écart des moyennes Opex/AAAHogEx | Victoires Opex |
|---|---:|---:|---:|---:|
| Valeur de compagnie | 2,189 M£ | 7,698 M£ | −71,56 % | 0/20 |
| Profit annuel | 676 k£ | 4 000 k£ | −83,09 % | 0/20 |
| Score de performance | 483 | 807 | −40,09 % | 0/20 |
| Moyenne des notes médianes de gare | 167,6 | 186,8 | −10,28 % | 0/20 |
| Gares possédées | 64,5 | 177,6 | −63,68 % | — |
| Caisse | 364 k£ | 1 650 k£ | — | — |
| Emprunt restant | 223,5 k£ | 0 £ | — | — |

Ces pourcentages sont des **rapports de moyennes**, pas la moyenne des pourcentages par graine.
Le harnais annonce zéro échec et les 40 lignes finales atteignent bien décembre 1974.
Il ne renseigne toutefois pas `expected_last_year` et ne transmet pas la sortie du moteur au
contrôle d'échec d'AAAHogEx : sa validation automatique reste à compléter (P0).

**Retrait du diagnostic « 93 % de rendement par véhicule, donc presque uniquement du volume ».**
Le harnais [du duel](../sweeps/bench_1v1_5y_20seeds.py), dans `extract_company_record`, compte
les entrées `VEHS` par propriétaire sans filtrer les composants. Les 102,4 contre 564,35 sont
ces entrées ; C54 a déjà identifié le piège wagons/ombres/rotors. Les décodeurs
`vehicle_breakdown` et `physical_telemetry`, malgré le nom `primary_vehicles_by_mode` de ce dernier,
ne filtrent eux aussi que type et propriétaire. Leur comptage demande la même qualification.
Même avec de vrais véhicules, une moyenne mélangeant bus, avions et trains ne prouverait pas
une équivalence de rendement. **Ne pas dériver de productivité ni de cible de flotte de ces comptes.**

L'emprunt nul d'AAAHogEx **à l'arrivée** ne veut pas dire qu'elle n'a jamais emprunté.
La dette élevée et la caisse positive d'OpexAI ne suffisent pas non plus à désigner le capital
ou le contrôleur comme goulot : il faut observer les occasions réellement disponibles et leur
financement au moment du refus. Les relevés économiques restent utiles malgré le problème de flotte.

La [chronologie C50](../results/diag_1v1_chronology_6y_5seeds.json) situe une rupture à examiner
dès **1971** : sur cinq graines, les créations nettes de gares passent de 148 contre 72 en 1970
à 57 contre 241 en 1971. Ce sont des sommes sur cinq parties, et des variations nettes de stock,
pas un comptage des chantiers. Le volet véhicules reste soumis à la réserve ci-dessus.

## Pourquoi le travail donne une impression de surplace

1. **La mesure du progrès a glissé vers le volume et les opcodes.** C51 augmente le nombre de
   gares sans gain économique démontré ; C50b augmente la flotte routière et dégrade la valeur.
   Une optimisation locale ou un réseau plus gros n'est pas encore un rattrapage.
2. **Les essais sont surtout arbitrés en solo.** Une victoire contre notre propre référence
   sur une carte séparée ne démontre pas une meilleure résistance à AAAHogEx sur carte partagée.
   Nous n'avons pas ici une série homogène de duels entre versions permettant de mesurer une
   vitesse de rattrapage. Le duel récent établit le retard, pas l'absence de tout progrès passé.
3. **Les mêmes hypothèses réapparaissent après leur réfutation.** Exemples : supprimer les
   plafonds après C50b ; proposer P1.1 comme inédit en C63 ; expliquer le rail improductif avec
   le comptage invalidé de C54 ; conserver le « facteur 15 inexpliqué » après sa correction C39.6.
4. **Les statuts confondaient livré, adopté et rentable.** C56 a corrigé un gel réel ; C65 facilite
   le développement. Ce sont des acquis. C60 n'a qu'un smoke de son filtre ; C53 non-stop est
   adopté mais son gain économique n'est pas établi statistiquement par le banc cité.

**Objectif de la prochaine séquence : augmenter le profit et la valeur en duel, en expliquant
le mécanisme qui permet de réinvestir.** Le nombre de véhicules, les gares et les opcodes restent
les instruments de diagnostic. Ils ne remplacent pas cet objectif.

## Ordre de travail historique — 2026-09-13

> **Supersédé pour la file active par l'état courant du 2026-09-20 ci-dessus.**
> Ce tableau reste la trace de la séquence qui a mené à C66 puis au diagnostic C63/C58.

| Rang | Chantier | Question qui doit être tranchée | Livrable / condition de passage |
|---|---|---|---|
| **P0** | **C66 : duel fiable et référence reproductible** | Quelle est la trajectoire économique actuelle face à AAAHogEx, avec une flotte correctement comptée ? | Harnais qualifié, référence figée ; réutiliser les données valides avant de relancer |
| **P1** | **C63 + C58 : investissement et réinvestissement** | Où se perd la croissance à partir de 1971 : coût, revenu capté, occasions absentes ou décisions lentes ? | Un diagnostic commun 5×6, attribution par mode/âge de ligne, puis **un seul** correctif causal |
| **P2** | C61 + C59 : exploitation des infrastructures rentables | Quelles lignes profitables disposent de demande non servie et d'une capacité réellement disponible ? | Cibler le mode exposé par P1 ; un levier isolé, sans rejouer la suppression brute des plafonds |
| **P2 conditionnelle** | C39/C41 : coût des décisions utiles | Reste-t-il des projets valides et finançables que le contrôleur traite trop tard ? | Montrer un délai et une occasion perdue sur l'arbre courant avant de modifier la cadence ou les caches |
| **P3** | C52/C60, C67 carte/eau, autres | Quel effet matériel subsiste hors des priorités ci-dessus ? | Remontée seulement sur exposition mesurée ou défaut bloquant reproductible |

La première action est P0, puis le diagnostic commun C63/C58. **Ne pas lancer simultanément
une nouvelle famille de plafonds, un nouveau score et un orchestrateur général.** Les rangs P2
restent des suites conditionnelles ; rien ne prouve encore que l'un d'eux est le meilleur levier.

<a id="c66"></a>
## P0 — C66 : fiabiliser le duel et rendre le rattrapage mesurable

**Statut : CLOS — harnais qualifié.** Fiche ouverte le 2026-09-13 à la demande de l'utilisateur ;
les preuves C66.1–C66.5 puis H1/H3/H4/H5 ont qualifié le harnais courant. Le point 4 de C66.5
reste uniquement le jalon d'adoption d'une future variante causale ; il ne rouvre pas C66.
C64 conserve uniquement la piste adaptative, différée.
**But :** pouvoir dire si une modification d'OpexAI améliore son résultat économique **contre
AAAHogEx**, avec des mesures correctes, des parties complètes et une comparaison reproductible.
Cette fiche porte sur le harnais et ses preuves ; elle ne change aucune stratégie de jeu.

### C66.1 — Corriger et qualifier les compteurs physiques

**Défaut localisé :** `extract_company_record` dans
[`bench_1v1_5y_20seeds.py`](../sweeps/bench_1v1_5y_20seeds.py) compte les entrées `VEHS`
possédées. `vehicle_breakdown` dans `diag_1v1_monthly.py` et `physical_telemetry` dans
`bench_c50b_physical.py` ne filtrent pas davantage les composants internes. Le champ `type`
distingue les modes, pas nécessairement la tête d'un véhicule de ses composants.

- [x] Définir **un décodeur partagé**, avec un schéma de sortie versionné (`sweeps/physical_counters.py`,
  schéma 1.1.0). Garde le compte brut sous `vehicle_pool_entries`, ajoute les unités pilotables
  par mode (`primary_vehicles_by_mode`) et le bilan des anomalies (`unclassified_entries`).
  Depuis la clôture H3 du 2026-09-16, `n_vehicles` désigne la flotte primaire pilotable,
  identique à `primary_vehicles`; le compte brut reste disponible sous
  `vehicle_pool_entries`/`total_vehicle_pool_entries`. Respect strict du principe
  **fail-closed** :
  si un chunk est manquant (`None`) ou de type inattendu, `chunk_valid` passe à `False`,
  `chunk_error` documente la cause, et les compteurs — y compris les secondaires
  (`fleet_status`, `components_breakdown`, `station_ids`) — sont passés à `None`.
  Une anomalie interne (pointeur de convoi mort, cycle, composant non-dict, gare
  non résolue) invalide aussi `chunk_valid` : le comptage partiel n'est plus
  `physical_ok`. `schema_version`, `qualified_modes`, `vehs_chunk_valid`,
  `stnn_chunk_valid`, `physical_ok` et les causes d'erreur sont conservés dans les
  métadonnées de `bench_1v1_5y_20seeds.py`, `diag_1v1_monthly.py` et
  `bench_c50b_physical.py`. `summarise()` propage `physical_ok` et bascule
  `run_ok=False` avec `failure_reason` explicite dès qu'un chunk physique est corrompu.
  L'agrégation mensuelle reçoit `args.seeds` et les mois calendaires attendus : une
  graine qui n'a produit aucune ligne reste `FAIL v/e`, pas un `1/1` silencieux.
- [x] Qualifier les discriminants de tête/composant sur les chunks **réellement produits par
  OpenTTD 15.3**. Confrontation formelle et exacte à un inventaire API NoAI indépendant
  (`AIVehicleList`, `AIVehicle.IsPrimaryVehicle(v)`, `AIStationList`, `AIStation.HasStationType`)
  capturé au **même instant exact** de jeu (autosave `1970-12-01`, graine 42) dans
  `sweeps/fixtures/c66_control_fixture_15_3.json` via `sweeps/generate_c66_control_fixture.py`
  (injection garantissant un réveil le 1er du mois sans décalage temporel).
  Égalité ensembliste exacte :
  `primary_vehicle_ids` API == `primary_vehicles_detail` décodés (21 unités : IDs 7, 9, 10, 11, 12, 15, 16, 17, 18, 19, 20, 21, 22, 24, 25, 26, 27, 28, 29, 30, 32).
  `primary_vehicles_by_mode` API == chunks décodés (`rail: 1, road: 17, air: 3, water: 0`).
  Composants exclus sans résidu : 2 wagons ferroviaires, 3 ombres d'aéronefs, 7 effets, zéro non classé.
  Le mode bateau est explicitement étiqueté `qualified: False` (non exercé).
- [x] Compter un train comme une unité pilotable tout en additionnant correctement la capacité
  de ses wagons. Suivi déterministe de la chaîne de convoi via le pointeur 1-based `next` du
  format saveload (`val - 1 = index`). Capacités strictement ségrégées **par cargo**
  (`capacities_by_cargo`), sans somme hétérogène passagers/tonnes.
  Détection et signalement explicite des corruptions de chaîne : rupture de pointeur
  (`corrupted_consist_pointer_missing_target`), cycle (`consist_cycle_detected`) ou absence de bloc
  commun (`missing_consist_component_common`) alimentent `unclassified_entries` et marquent `consist_valid: False`.
  Observables physiques `vehstatus` strictement conformes à `src/vehicle_base.h` d'OpenTTD 15.3 :
  `is_hidden` (`0x01`), `is_stopped` (`0x02`), `is_broken` (`0x40`), `is_crashed` (`0x80`).
  `running` est strictement défini en excluant stopped, hidden, broken et crashed.
  `fleet_status` expose les observables réels `{stopped, not_stopped, running, hidden, broken, crashed}`.
- [x] Vérifier aussi les propriétaires des gares, les gares multimodales et les représentations
  dictionnaire/liste des chunks. Propriétaire extrait strictement de `base.owner` sans repli
  silencieux (anomalies isolées dans `unresolved_stations`). Une gare multimodale compte pour 1
  dans `total_stations`, avec détail dans `n_multimodal_stations`, `multimodal_station_ids`,
  `stations_by_facility` et `stations_detail`. Confrontation exacte API : 24 gares API == 24 gares
  décryptées (IDs 0 à 23), 4 gares multimodales bus+air (0, 1, 14, 21) comptées 1 fois dans le total,
  installations identiques (`rail: 2, truck: 6, bus: 16, airport: 4, dock: 0`).
  Intégré et validé dans `bench_1v1_5y_20seeds.py`, `diag_1v1_monthly.py` et `bench_c50b_physical.py`
  avec protection contre les valeurs `None` et suites `--selftest` autonomes.

**Preuve technique :**
- Suite de tests unitaires et empiriques `sweeps/test_physical_counters.py` validée à 100 % (7/7 tests OK)
  sur l'hôte et dans Docker avec les limites canoniques (`--cpus=3 --memory=2g --memory-swap=2g`).
- Fixture de contrôle C66 (`sweeps/fixtures/c66_control_fixture_15_3.json`, générée par
  `sweeps/generate_c66_control_fixture.py`) intégrant à la fois les chunks bruts et l'inventaire API
  NoAI indépendant au **même instant exact** (`1970-12-01`), avec assertions automatisées d'égalité ensembliste stricte.
- Selftests unitaires autonomes validés sur `bench_1v1_5y_20seeds.py --selftest`, `bench_c50b_physical.py --selftest`
  et `diag_1v1_monthly.py --selftest`.

### C66.2 — Séparer santé du moteur, santé des compagnies et activité de l'IA

**Défauts localisés :** le duel appelle `summarise(rows)` sans `expected_last_year` ; `keep`
transmet toute la sortie du moteur à OpexAI et une chaîne vide à AAAHogEx. Le détecteur commun
cherche des marqueurs fatals sans attribution de compagnie. Une erreur d'AAAHogEx pourrait donc
être imputée à OpexAI, tandis que la ligne AAAHogEx serait déclarée saine.

- [x] Journal moteur **une seule fois par partie** : `keep` écrit
  `{out}_engine/seed{S}_r{R}.log` et pose le même `engine_log_path` sur les deux
  compagnies ; plus de stdout recopié dans le JSON. Parseur
  [`sweeps/game_health.py`](../sweeps/game_health.py) : `[script:N] [company]`
  confronté au manifeste des places (script 0 → OpexAI / compagnie 0, script 1 →
  AAAHogEx / compagnie 1). Script inconnu, company id contradictoire ou marqueur
  sans identifiant → `unattributed`, jamais joueur 0 par défaut.
- [x] `summarise(..., expected_last_year=starting_year+years-1)` dans le duel, plus
  le dernier checkpoint exigé `YYYY-12-01` (`expected_last_checkpoint`). Un
  1974-01-01 pour un 5 ans 1970 n'est plus une année complète. Contrôle des deux
  compagnies, des doublons `(arm, date)` et des absents.
- [x] Statuts distincts : `engine_error`, `missing_data`, `duplicate_checkpoint`,
  `noai_error`, `horizon_truncated`, `bankrupt`, `stagnation_suspect`, `complete`.
  `include_in_economic_stats` / `run_ok` reste vrai pour faillite, fin complète et
  suspicion de gel ; faux pour les erreurs de collecte. `game_ok` est faux dès
  qu'une compagnie de la partie est en erreur de collecte, même si l'autre est saine.
- [x] Activité : deltas de flotte, de gares et de valeur. Signal `active` /
  `earning_without_expansion` / `no_signal`. Pas de construction + valeur qui
  bouge ≠ gel. `no_signal` sur un horizon complet → `stagnation_suspect`, **pas**
  une exclusion des moyennes.

**Preuve :** [`sweeps/test_game_health.py`](../sweeps/test_game_health.py) (20/20
sur l'hôte) avec les journaux
[`sweeps/fixtures/c66_health/`](../sweeps/fixtures/c66_health/) — erreur OpexAI
seule, erreur AAAHogEx seule (Opex reste `complete`), log ambigu non attribué,
compagnie absente, janvier de dernière année tronqué, décembre complet, faillite
conservée dans les stats, earning sans expansion, suspicion sans exclusion,
doublon, fatal moteur. Selftest Docker de
`bench_1v1_5y_20seeds.py` : `keep` partage le chemin de log et n'impute pas une
erreur HogEx à Opex. Aucune IA de production n'a été crashée.

**Corrections (revue, 2026-09-14) :** trois P1 et un P2 rouvraient des faux
positifs de santé.

1. `annotate_summary` ne réhabilite plus un `run_ok=False` de `summarise`
   (`physical_decode_failure` reste `missing_data`, `game_ok` faux).
2. `enable_engine_failure_capture` (timeout 1800 s par défaut, avant le cleanup)
   attrape `CalledProcessError` / `TimeoutExpired` dans le worker et rend des
   lignes `engine_error` au lieu d'abandonner `run_experiments`. Un crash qui
   sort 0 avec un marqueur fatal reste lu dans le journal.
3. Une compagnie présente plus tôt puis absente au dernier checkpoint est
   `missing_data`, sauf faillite déjà établie.
4. `earning_without_expansion` exige une variation de valeur dans les 3 derniers
   pas ; un revenu de février suivi de dix mois figés est `no_signal`.
5. Le wrapper de capture copie la signature de `_run_experiment` (`__wrapped__` +
   `__signature__`) ; `enable_savegame_cleanup` retrouve `run_dir`/`i`/
   `final_screenshot_directory`. Testé en composition (hôte + selftest Docker).
6. `games[]` est reconstruit via `reconcile_assessment` après `annotate_summary` :
   un fail-closed physique n'y reste plus `game_ok=true/complete`.

### C66.3 — Figer une référence réellement reproductible

- ☑ Créer un manifeste contenant : SHA Git, état modifié, empreinte et copie isolée des sources
  effectivement exécutées, version/empreinte d'AAAHogEx et des bibliothèques, versions
  OpenTTD/OpenGFX/OpenTTDLab et image Docker, configuration effective, réglages IA explicites
  **et défauts**, année initiale, durée, graines, répétitions et places des compagnies.
- ☑ Figer les sources **avant** de lancer les parties ; les modifications de l'arbre de travail
  pendant le banc ne doivent pas contaminer les graines suivantes. C65 illustre pourquoi un
  SHA sans le contenu modifié ne suffit pas à décrire le programme exécuté.
- ☑ Identifier séparément la politique testée, la compagnie et la partie : par exemple
  `(campaign, policy, seed, repeat, company_slot)`. Les noms « OpexAI » et « AAAHogEx » ne sont
  pas les deux variantes de stratégie. Refuser les paires dont les configurations diffèrent
  sur autre chose que l'intervention annoncée.
- ☑ Conserver résultats compacts, checkpoints, manifeste, logs uniques et fixtures de décodage.
  Sorties sous un nom de campagne nouveau ; ne pas écraser la référence 20×5 ni ses JSONL.
  Les empreintes servent à relier une mesure à son code, pas à affirmer l'équivalence de deux codes.

**Preuve attendue :** deux relances courtes de la même référence isolée produisent les mêmes
métriques aux mêmes checkpoints. Si elles divergent, documenter et traiter la source de variation
avant d'attribuer une petite différence à une stratégie ; ne pas sélectionner la meilleure relance.

**Preuve réalisée le 2026-09-15.** Le gel est implémenté dans
`sweeps/campaign_freeze.py`, le lancement hôte dans `sweeps/run_c66_reference.py` et le banc
`sweeps/bench_1v1_5y_20seeds.py` exécute les copies gelées d'OpexAI/AAAHogEx et les archives
BaNaNaS gelées. Les campagnes finales de preuve sont `c66_3_repro_a2` et `c66_3_repro_b2`
(`results/*.json`, `*.jsonl`, `*.manifest.json`, bundles et logs dédiés). Les essais `a/b`
antérieurs sont conservés mais sont supersédés par `a2/b2`, qui incluent aussi les limites
Docker dans le manifeste.

- Git : `96e52817e140f67fa5026c34c907ca20f92be130`, arbre modifié explicitement enregistré.
- Bundle source commun : `7e48a62b6fc47e5b60ed412f25c4f2a49c5457d9c2c2a3bf8cf663f54541417f`.
- Manifestes : A2 `3603cf10790fd69071f0fb0614ef7fce21cfd8f59429988c81bcd4ae38dd3397`,
  B2 `7a9abb72d345982a16eee7008cf339fb51f08855f626947ded06330146871120` ; leur SHA diffère
  normalement car les identifiants/chemins de campagne diffèrent, tandis que Git, runtime,
  versions, configuration, politique, adversaire, slots, sources et bibliothèques sont identiques.
- Runtime : OpenTTD 15.3, OpenGFX 7.1, OpenTTDLab 0.0.75, image `openttd-lab`
  `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`,
  test local à 6 CPU / 2 Gio / swap 2 Gio. Le lanceur garde 3 CPU par défaut pour le profil VPS.
- Bibliothèques gelées : Queue.FibonacciHeap v3
  `c3c80ad59a0cf43b67a7d769484ba10f316b7a0b4a83a28efe5ce82e96066c9b`, Pathfinder.Rail v1
  `e3ab05b1811c1a57abb4219480f0fffa885efff6be42691c836ec144ab7f8b13`, Graph.AyStar v4
  `cfc09cdd5877800d57e490832b65cf028db16aef4f1906eb1d625f908ebc49f1` et Queue.BinaryHeap v1
  `a83eb5002b1246330dfc467dbd1076687d227156a697cc140f6d04515cf3bb67`.
- Reproductibilité : 26/26 checkpoints identiques après retrait des seuls `campaign_id`,
  `game_id` et `engine_log_path`; résumés normalisés identiques, comparaisons appariées identiques,
  `run_ok=true` et `game_ok=true` pour les deux compagnies des deux campagnes, aucun `failed_run`,
  checkpoint attendu `1970-12-01` atteint. Aucune relance n'a été sélectionnée sur ses performances.

### C66.4 — Comparer deux politiques, chacune contre le même adversaire

Étendre le harnais existant avec la validation des réglages de `bench_v2.py`, sans écrire un
nouveau lanceur ad hoc. Pour chaque graine, exécuter **deux parties distinctes** :

| Partie | Compagnie OpexAI | Adversaire | Conditions |
|---|---|---|---|
| Témoin | Référence figée | AAAHogEx figée | Même graine, configuration, durée et place |
| Variante | Même référence + intervention isolée | Même AAAHogEx | Seule l'intervention annoncée diffère |

L'évolution ultérieure d'AAAHogEx peut différer entre les parties parce qu'OpexAI agit autrement :
c'est une conséquence du duel, pas un défaut d'appariement. Ne pas comparer deux OpexAI jouant
ensemble, ni la variante seule à une référence jouant contre AAAHogEx. Garder les places fixes
pour le premier protocole ; une inversion des places serait un bloc de robustesse distinct.

- ☑ Fixer avant le banc la métrique primaire — **proposition : profit annuel final d'OpexAI** —,
  l'effet minimal utile et le garde-fou sur la valeur. Conserver les trajectoires annuelles,
  notamment 1970–1972, pour distinguer gain précoce et destruction de croissance à long terme.
- ☑ Rapporter deux comparaisons différentes : `Opex_variante − Opex_témoin` sur chaque graine,
  puis l'écart `Opex − AAAHogEx` dans chacune des deux parties et son évolution. Une réduction
  du retard obtenue seulement en dégradant les deux compagnies n'est pas un gain économique
  d'OpexAI. Rapporter aussi les victoires directes contre AAAHogEx.
- ☑ Publier deltas par graine, moyenne et médiane **des deltas**, intervalle d'incertitude,
  V/D/égalités et test des signes excluant les égalités. Les ratios demandent un dénominateur
  positif et doivent distinguer rapport de moyennes et moyenne des rapports.
- ☑ Garder toutes les graines prévues et tous les statuts. Les erreurs de collecte doivent
  être résolues ou rendre la comparaison incomplète ; ne pas recalculer discrètement le verdict
  sur les seules réussites. Les analyses par mode, richesse ou déclenchement restent secondaires.

**Preuve du harnais réalisée le 2026-09-15.** `bench_1v1_5y_20seeds.py` accepte désormais une
variante au format déjà validé par `bench_v2.py` (`OpexAI[cle=valeur]`) et construit, pour chaque
`(seed, repeat)`, deux parties séparées : référence vs AAAHogEx et variante vs le même AAAHogEx
gelé. Le plan est validé avant `run_experiments` : graine, répétition, durée, configuration,
campagne, bundle, slots et descripteur AAAHogEx doivent être identiques ; seuls le descripteur
OpexAI, `policy_id` et `game_id` peuvent différer. Les logs incluent désormais la politique pour
éviter toute collision.

Le rapport `policy_comparison` conserve chaque paire et ses quatre statuts, les trajectoires
annuelles, `variante - référence`, les deux écarts `OpexAI - AAAHogEx` et leur évolution. Les
agrégats publient moyenne/médiane des deltas, erreur standard et IC normal 95 % lorsque `n > 1`,
V/D/égalités, test binomial exact des signes hors égalités, ainsi que rapport de moyennes et
moyenne des rapports en excluant les dénominateurs non positifs. Si une partie prévue manque,
échoue ou ne fournit pas les métriques de décision pour l'une des quatre lignes, le verdict reste
`incomplete` même si les autres paires sont exploitables à titre diagnostique.

Smoke final : `results/c66_4_smoke_air_presite_v3.json`, graine 42, 1 an, variante
`air_presite=1` contre défaut 0. Bundle
`4d72bcbf53fdca5816bdbc5b8d660ace02b5d26846116b14c82d688cedabb6ec`, manifeste
`409910194b6b84791cb0d33ee782af44b7babb3a6cf53bb1288340fa7528f1b9`, image
`openttd-lab:latest` `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
Les 2/2 parties et 4/4 lignes sont `run_ok=true`, `game_ok=true`, sans `failed_run`, avec deux
`game_id` et deux logs distincts. Le manifeste confirme que la seule différence effective est
`air_presite: 0 -> 1`. Sur ce smoke, le profit annuel OpexAI vaut 185451 (référence) contre
190217 (variante), delta +4766 ; l'écart au profit AAAHogEx passe de -158466 à -108129, soit
+50337, tandis que le profit AAAHogEx change aussi entre les deux parties comme attendu dans un
duel interactif. Le `pass` de ce smoke utilise volontairement `min_useful_primary_delta=0` et
`value_guard_max_loss_pct=100` : il valide le protocole, **pas** l'intérêt économique de
`air_presite=1`. Toute campagne causale officielle devra pré-enregistrer des seuils substantifs.

### C66.5 — Validation progressive et critères de clôture

1. ☑ **Hors jeu :** fixtures des compteurs, erreurs par compagnie, horizon, appariement et calculs
   statistiques ; vérifier aussi qu'un réglage inconnu est rejeté et qu'une erreur interrompt
   proprement le rapport de validation sans effacer les résultats.
2. ☑ **Smoke 1 graine × 1 an :** le duel démarre, les deux compagnies et leurs métriques sont
   présentes. Les scénarios physiques manquants sont qualifiés séparément ; un smoke sans train
   ne valide pas le compteur des trains. Conserver le tuple de dictionnaires retourné par `keep`.
3. ☑ **Contrôle de répétabilité court**, puis **diagnostic 5 graines × 6 ans** sur référence figée.
   Ce diagnostic peut être partagé avec C63/C58 pour éviter une campagne supplémentaire ;
   distinguer sa télémétrie instrumentée du résultat économique sans sonde lourde.
4. ⬜ **Banc officiel 20 graines × 10 ans** quand une variante causale est prête : 40 parties
   partagées au total, chacune avec deux compagnies, soit 20 paires de politiques. Il valide
   l'intervention ; un nouveau 20×10 sans variante n'est pas requis pour clore le harnais.

**Validation C66.5 réalisée le 2026-09-15.** La couche hors-jeu passe intégralement :
`test_physical_counters.py` = 7/7 tests, `test_game_health.py` = 20/20 tests, puis selftest du
harnais. Elle couvre la confrontation indépendante chunks/API NoAI des compteurs, erreurs NoAI
attribuées par compagnie, erreur ambiguë non attribuée, crash/timeout moteur, compagnie absente,
doublon de checkpoint, horizon décembre, faillite économique, appariement C66.4, calculs de
deltas/ratios/test des signes, rejet d'un réglage inconnu et conservation du JSON écrit avant un
`SystemExit` de validation.

Smoke final de référence : `results/c66_5_smoke_reference_v1.json`, graine 42, 1 an. Les deux
compagnies sont `complete`, `run_ok=true`, `game_ok=true`, horizon `1970-12-01`, aucun
`failed_run`. OpexAI possède au dernier état 1 train, 25 véhicules routiers et 4 avions ; la
fixture/qualification physique couvre donc rail/route/air sur OpenTTD 15.3. L'eau reste
explicitement **non qualifiée** (`water=false`) et ne doit pas être présentée comme validée.

Contrôle de répétabilité final : `c66_5_smoke_reference_v1` et
`c66_5_smoke_reference_v2` utilisent le même bundle
`bac767e10fa6008668a5da5064e41d143057fda6683a57e781926d1ccec6c238`. Les 26/26 checkpoints
normalisés sont identiques (0 différence après retrait de `campaign_id`, `game_id` et chemin de
log), de même que les résumés. Manifestes : v1
`86d32c6f561ef05e1b9f3765c111908264dcd1ded612d8765f526a70e22b30f6`, v2
`23d2546310f1a7e1d02e7636fa2be01b7287cdd6ed748a0b5b23e04f1b06d403`.

Diagnostic de référence : `results/c66_5_diag_reference_6y_5seeds.json`, 6 ans, graines
**42, 100, 999, 1234, 5678**, soit le même échantillon que C63/C58. Bundle identique au smoke,
manifeste `efbe10f4eeda177f863118da281e2b15abc3ca16d03f300a7e35f176225add32`. Les 5/5 parties et
10/10 lignes sont `complete`, `run_ok=true`, `game_ok=true`, toutes `active`, horizon attendu
`1975-12-01`, 0 `failed_run`, 0 erreur de script/non attribuée, 0 véhicule non classé et compteurs
physiques valides. Rail/route/air sont qualifiés ; eau reste non qualifiée.

À 6 ans, cette **référence sans sonde lourde** reste très derrière AAAHogEx : moyenne OpexAI
2 532 412 £ de valeur et 737 824 £ de profit annuel contre 12 243 227 £ et 5 354 521 £ pour
AAAHogEx. Les écarts appariés moyens sont -79,32 % sur `company_value`, -86,22 % sur
`profit_year`, -40,42 % sur le score et -16,52 % sur la note médiane de gare ; OpexAI ne gagne
aucune des 5 graines sur ces quatre métriques. Ce diagnostic qualifie la référence et le harnais,
il ne valide aucune nouvelle stratégie.

Le point 4 reste volontairement **en attente** : aucune variante causale avec seuils substantifs
pré-enregistrés n'est prête. Conformément au contrat ci-dessus, un 20×10 supplémentaire de la
référence seule n'apporterait pas de preuve sur une intervention et n'est pas requis pour clore le
harnais C66.

**Revalidation après C66.4 sur le harnais courant (2026-09-15).** Les preuves ci-dessus ont été
rejouées après l'ajout du comparateur à deux politiques afin d'éviter de qualifier un ancien
bundle. La couche hors-jeu reste verte : `test_physical_counters.py` 7/7,
`test_game_health.py` 20/20, selftest C66.1→C66.4 et `git diff --check`.

Deux smokes consécutifs de référence, `results/c66_5_current_smoke_a.json` et
`results/c66_5_current_smoke_b.json`, utilisent le même bundle courant
`87a9a718f9f169400ca475adf95b223ed310dbcd7c20277280622fb7b105e67e`.
Manifestes respectifs :
`63dd63ffd820e7e53309ed1b10119c92db82e4f11179b98baa4c3fcab0dade70` et
`c3563c2b082e837155f5b9fe74348b9fc09717c4e4c724a0b2fdd6cd50a4480d`.
Les 26/26 checkpoints normalisés sont identiques, avec 0 différence après retrait des seuls
`campaign_id`, `game_id` et `engine_log_path`, et les résumés normalisés sont identiques.
Sur le smoke courant OpexAI termine avec 1 train, 22 véhicules routiers et 4 avions ; AAAHogEx
avec 2 trains, 2 routiers et 14 avions. Rail/route/air sont donc réellement exercés ; eau reste
explicitement non qualifiée.

Le diagnostic courant est `results/c66_5_current_diag_6y_5seeds.json`, mêmes graines
42/100/999/1234/5678, 6 ans, **même bundle** que les deux smokes, manifeste
`ebce3fd0c0c0c000c8ed14012f5f18fcd7694a9ab08599d9da3ef169eacd3d6e`.
Les 5/5 parties et 10/10 lignes sont `complete`, `run_ok=true`, `game_ok=true`, horizon
`1975-12-01`, aucun `failed_run`, aucune erreur script/non attribuée, aucun véhicule non classé,
compteurs physiques valides ; qualification rail/route/air vraie, eau fausse.

À 6 ans sur le bundle courant, OpexAI moyenne 2 942 073 £ de valeur, 850 360 £ de profit annuel,
score 543 et note médiane de gare 157,1, contre 11 145 231 £, 4 694 956 £, score 821,2 et
note 185,1 pour AAAHogEx. Les écarts appariés moyens sont respectivement -73,60 %, -81,89 %,
-33,88 % et -15,13 %, avec 0/5 victoire OpexAI sur chacune de ces quatre métriques.
Ces chiffres supersèdent les anciens chiffres C66.5 comme qualification du **harnais courant** ;
ils qualifient la référence mais ne constituent toujours pas un correctif causal.

**Statut C66.5 : harnais qualifié.** Les points 1–3 sont validés sur le code courant. Le point 4
reste un jalon de validation d'une future intervention : il ne doit être exécuté que lorsqu'un
mécanisme C63/C58 aura produit une variante unique et des seuils substantifs pré-enregistrés.
Le lancer aujourd'hui avec `air_presite=1` ou la référence seule transformerait un smoke de
protocole en faux banc causal.

**Revalidation finale H1/H3/H4 — 2026-09-16.** La revue de code a rouvert trois garanties du
harnais et elles sont désormais refermées sur le code courant :

- **H1 / adoption statistique.** Le verdict C66.4 exige une campagne d'adoption de **20 paires**,
  puis le test des signes exact bilatéral en premier (**≥ 15/20 victoires et p < 0,05**), puis
  seulement le seuil sur la moyenne du delta. Une campagne plus courte rend
  `diagnostic_only` et ne peut plus produire un verdict d'adoption. La couverture statistique
  est fail-closed : toutes les paires primaires et tous les dénominateurs positifs de la garde de
  valeur sont requis.
- **H3 / flotte physique.** `n_vehicles == primary_vehicles` dans les sorties de banc ; les
  entrées brutes du pool restent séparées. `primary_vehicles` est une métrique commune des
  agrégats et le smoke teste explicitement la flotte pilotable. Le diagnostic mensuel exclut les
  modes non qualifiés de ses totaux ; l'eau reste `qualified=false`.
- **H4 / fail-closed.** Le duel vérifie la grille mensuelle complète, les jeux planifiés sans
  ligne, l'identité de campagne, l'existence du journal moteur et un plancher d'activité physique.
  Une stagnation ou une valeur qui décroît sans expansion récente ne rentre plus dans les
  statistiques économiques. Le timeout ne s'applique plus aux téléchargements OpenTTDLab : il est
  injecté uniquement pendant `_run_experiment`.

Validation hors jeu rejouée après ces corrections :
`python sweeps/test_physical_counters.py` = **7/7**,
`python sweeps/test_game_health.py` = **25/25**,
`python sweeps/bench_1v1_5y_20seeds.py --selftest` = OK,
`python sweeps/diag_1v1_shared_monthly.py --selftest` = OK,
`python -m py_compile ...` = OK et `git diff --check` = OK.

Smoke PR réel : `results/review_h134_smoke_ci_2x3_v3.json`, graines **42/100**, **3 ans**.
Résultat **PASSED**, 2/2 runs présents, 36 checkpoints contigus par run jusqu'au
`1972-12-01`, chunks physiques valides et `n_vehicles == primary_vehicles` (52 et 39).

Diagnostic C66.4 de cohérence :
`results/review_h134_5x6_air_presite_v2.json`, graines **42/100/7/999/2026**, **6 ans**,
référence contre `air_presite=1`. Le lanceur officiel
`sweeps/run_c66_reference.py` a imposé CPU=3, mémoire/swap **2g/2g**, image
`openttd-lab:latest` vérifiée
`sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
Le manifeste `results/review_h134_5x6_air_presite_v2.manifest.json` ne contient qu'une
différence effective : `air_presite: 0 -> 1`.

Audit du JSON/checkpoint : **10/10 jeux**, **20/20 lignes** `complete/run_ok/game_ok`,
0 `failed_run`, horizon `1975-12-01`, **1 440** lignes de checkpoint =
20 séries × 72 mois exacts, 0 trou mensuel, 0 erreur non attribuée, 0 véhicule non classé,
0 gare non résolue et tous les chunks physiques valides. La flotte primaire observée va de
51 à 391 véhicules ; le pool brut dépasse la flotte primaire de 34 à 550 entrées selon la
composition, ce qui confirme que l'ancien dénominateur H3 était matériellement faux.

Le comparateur de politiques rend **5/5 paires complètes**, V/D/E **2/3/0** sur
`profit_year`, test des signes **p=1,0**, delta moyen **+20 419,8**, garde de valeur
**+3,578 %**, mais verdict **`diagnostic_only`** : c'est la preuve attendue que H1 interdit une
décision d'adoption sur le 5×6, même lorsque la moyenne est positive. Ces chiffres valident le
harnais, **pas** `air_presite=1` ; le 20×10 causal reste requis pour toute adoption réelle.

Limite de traçabilité : le workspace était `git dirty=1` pendant la revue. Le manifeste enregistre
le SHA Git `769fdf9baed4042b830fbf24393c17a65f530a56`, l'état dirty et le bundle exact
`fe883b9eb5d43a6a87961ac7cfa03380670e35599f84253285af28021a7da502`, de sorte que la preuve
reste reproductible sur les sources effectivement exécutées sans prétendre correspondre à HEAD
propre.

**C66 est close :** le décodeur a sa preuve indépendante, les contrôles négatifs détectent
et attribuent les échecs, la référence est figée et répétable, le diagnostic 5×6 est complet,
et le rapport distingue progrès d'OpexAI et évolution du duel. Tout gel suspect non expliqué ou
mode non qualifié doit être indiqué comme limite, jamais transformé en validation générale.
Le livrable est un harnais réutilisable et une référence qualifiée pour P1, pas une nouvelle IA.
Respecter les limites Docker et l'unique campagne consommatrice à la fois, comme en fin de fichier.

**Clôture H5 / G0bis — 2026-09-16.** Le banc officiel publie maintenant un coût
**observé**, explicitement distinct d'un coût CPU total. Le schéma h5.observed-v1
additionne uniquement des blocs déjà mesurés par OpexAI, sans double compte connu :
sélection portefeuille (IG|, coût réel en milliers d'opcodes), tentative rail
(OB|A, plan + construction), route (RB|, plan puis construction), planification
air (OA|) et planification eau des succès (OM|W). Le JSON porte
observed_opcode_complete_cpu=false, le détail par composante, et deux indicateurs
à horizon fixe : final_profit_year_per_observed_mopcode et
company_value_per_observed_mopcode. Ils ne doivent **jamais** être présentés comme
profit/CPU global : le build air/eau non publié, les tâches de catalogue/scheduler et
le budget de tick inutilisé restent hors périmètre.

Validation : sweeps/test_campaign_freeze.py **10/10**, selftests
diag_1v1_shared_monthly.py et bench_1v1_5y_20seeds.py OK, smoke obligatoire
results/review_h5_final_smoke_2x3.json **PASSED**. Le contrôle 2×3
results/review_h5_observed_ops_2x3.json est complet (2/2, zéro échec) et vérifie
observed_opcodes_total == somme(composantes) sur les deux graines. Exemple à 3 ans :
seed 100 = **44 993 008** opcodes observés, dont **38 569 083** rail ; seed 42 =
**8 614 882**, sans tentative rail mesurée. Le diagnostic mensuel
results/review_h5_monthly_observed_ops_final.json reconstitue les deltas depuis les
panneaux cumulatifs ; 13/13 checkpoints OpexAI ont un état available.

loop_budget=1 a été rejoué causalement sur
results/review_h5_loop_budget_5x6.json (5 graines × 6 ans). Les **5/5 paires sont
des égalités exactes** sur valeur, profit annuel, score, flotte primaire, gares,
observed_opcodes_total et chaque composante observée. Aucun 20×10 n'est justifié :
le défaut reste 0. Ce résultat ne prouve pas que le slack de tick vaut zéro ; il
montre au contraire la limite volontaire du schéma, qui mesure le travail exécuté,
pas les opcodes potentiels abandonnés par Sleep(1).

Le constat rail 07.2 est conservé comme limite du **modèle d'itérations** : les sondes
locales pont/tunnel ne sont pas ajoutées à state.iterations. Elles ne sont pas
injectées artificiellement dans ce compteur, car cela modifierait budget et
comportement du pathfinder. Pour mesurer le coût réel d'une tentative rail, le
harnais consomme désormais OB|A.result.opcodes.

**Clôture B5 — état rail multi-tick et reload (2026-09-16).** Réconciliation préalable :
07.1 (libération de `_railSearch` sur CASH), 13.11 (`rawset` des champs double voie manquants)
et 13.12 (reprise bornée à trois essais) étaient déjà corrigés et n'ont pas été rouverts.
Les trois écarts actifs ont été traités :

- `RAIL_EXPAND_APPROACH_TILES = 8`, valeur justifiée par la fenêtre locale existante des signaux
  d'approche rail (`maxDistance=8`) ; `rail_expand` reste à **0** par défaut ;
- `_railExpansion` est persisté sous forme d'un descriptor scalaire et repris idempotemment sur
  `approach/depot/resume`. La frontière de commit
  `idle → build_started → wagon_built → wagon_moved → metadata_done` interdit un second
  `BuildVehicle` après reload ; un wagon identifié est réutilisé, et une rame déjà repartie n'est
  jamais togglée une seconde fois ;
- les objets vivants `_railSearch`/`_dynamicBatch` ne sont pas sérialisés. Save conserve
  seulement leur présence ; au reload ils sont abandonnés et le catalogue/portefeuille est
  reconstruit proprement ;
- les files C41 signal/jonction sont sauvegardées, filtrées aux LineID rail double voie encore
  valides et leurs micro-tâches sont réarmées seulement lorsqu'il reste du travail.

Validation : `sweeps/test_b5_rail_persistence.py` **11/11**, campagne **10/10**, santé
**26/26**, compteurs physiques **7/7**, selftests C63/mensuel/C66.4 OK, compilation et
`git diff --check` OK. Smoke obligatoire
`results/review_b5_smoke_2x3.json` → **PASSED**.

Deux vrais round-trips sont verts :
`results/review_b5_save_load_seed42.json` et
`results/review_b5_save_load_seed42_6y.json`. `LOAD_RECONCILE` prouve positivement la reprise,
aucun marqueur d'échec moteur/script n'est présent, et les deux ont réellement rencontré
`rail_search_dropped=1` avant reconstruction. Le diagnostic conditionnel
`results/review_b5_rail_expand_5x6.json` donne **5/5 runs complets**, zéro
`protocol_failure`; ce n'est pas un banc d'adoption.

Limites explicites : aucun checkpoint réel n'a intercepté une `_railExpansion` active
(`rail_expansion_* = 0`) ; ces frontières exactes sont donc couvertes par le test de contrat,
pas par un save moteur forcé. Aucune sauvegarde historique `stateVersion=1` n'était disponible
localement ; la compatibilité ancienne repose sur les champs optionnels de `Load()`. Dans la
fenêtre extrême où Save tombe après `BuildVehicle` mais avant stockage de son VehicleID,
`build_started` abandonne sans reconstruire : cela peut laisser un wagon libre non identifié,
mais exclut volontairement le risque plus grave de double construction.

<a id="c64"></a>
## C64 — Politique adaptative : en attente d'un mécanisme établi

Le duel 20×5 et le banc `< 50 industries` sont terminés, consignés dans
[le journal du jour](journal_2026-09-13.md). Leur qualification et le futur comparateur relèvent
désormais de **C66**. Le défaut adaptatif reste à 0 : 9 V / 2 D / 9 égalités, p=0,06543,
sur des graines déjà utilisées pour découvrir le seuil, sans validation indépendante.

Pas de nouvelle recherche de seuil sur les mêmes 40 graines. Une reprise demande un mécanisme
identifié par C63/C58, une règle pré-enregistrée et des graines nouvelles. La mesure primaire
porte sur toutes les graines prévues ; les seules graines déclenchées restent une analyse
secondaire, particulièrement si le déclenchement dépend de l'état produit par la politique.

<a id="c63"></a>
<a id="c58"></a>
## P1 — C63 + C58 : comprendre le rendement de l'investissement

**Hypothèse ouverte :** l'expansion rentable ne s'auto-entretient pas assez vite face à la
concurrence. Le coût de construction n'est qu'une explication possible ; une recette trop
optimiste, un mauvais captage ou une occasion non traitée peuvent produire le même symptôme.

**Correction de C63.** Le devis anticipé rail existe :
[`OpexPrequoteRailCandidates`](../ai/OpexAI/projects.nut), `rail_prequote` et
`rail_prequote_keep_plan`, tous deux à défaut 0 dans `info.nut` et lus dans `settings.nut`.
P1.1/P1.3 ont été implémentés et rejetés avant le 09/09 ; leur histoire est dans l'archive,
**leurs anciens chiffres ne sont pas une preuve actuelle**. Ne pas réécrire ce mécanisme ni
réactiver son coût à chaque rebuild en le présentant comme une nouveauté. Les facteurs rail
170 % / route 121 % sont toujours dans le code ; leur justesse actuelle reste à mesurer.

**Un seul diagnostic commun, 5 graines × 6 ans, sur carte partagée**, en examinant d'abord
1970–1972 puis la suite. Réutiliser les sondes coût `RC|`, `AC|`, les événements de construction,
les sauvegardes et les prédictions enregistrées sur les lignes. Vérifier leur couverture
avant de supposer qu'elles suffisent : les succès seuls ne donnent pas les dépenses d'échec.
Ne pas activer aveuglément `decision_log` partout.

**Inventaire du 2026-09-13** (`sweeps/diag_c63_c58.py --selftest`) : les sources existantes
**ne ferment pas** le tableau joint. `OpexSign` écrase la tuile (1,1) ; un chunk `SIGN` ne
garde que le dernier nom, donc `RC|` (succès route, coût réel seulement), `AC|`/`RP|`/`DC|`
(sondes coût défaut 0, panneaux et non AILog) et `OY|`/`OZ|` ne reconstituent pas une série.
C50 a `pred_profit` pas `pred_revenue`, et `project_built.cost` est le modèle. C49 compte des
passes, pas des jours. `LINE_REVENUE` est derrière `decision_log`. L'eau n'a pas d'`actualCost`
(`predicted = 0`). `len(VEHS)` n'est pas une flotte. Quatre trous nommés : dépense prévue vs
réelle y compris échecs ; recette prédite vs réelle avec témoins profitables ; jours
d'occasion via `OpexAvailableCapital` ; une sorte de reliquat par passe. Sonde
`c63_invest_probe` (défaut 0) ajoutée pour ces trous ; agrégation hors-jeu dans
`sweeps/diag_c63_c58.py`.

**Smoke 2×3 ON/OFF** (`results/c63_c58_probe_onoff_3y_2seeds.json`) : **pas bit-identique**.
Graine 42 : +0,60 % de valeur ; graine 100 : **−37,6 %**. 0 échec script. Les conclusions
économiques se lisent sur le bras OFF ; le tableau C63 du diagnostic 5×6 est de la
télémétrie du bras ON, pas une preuve de performance du défaut.

**Diagnostic 5×6 partagé, reliquat corrigé** (`results/diag_c63_c58_6y_5seeds.json`) :
5/5 jusqu'à 1975-12-01, 0 échec script. `c63_invest_probe=1` contre AAAHogEx. Années C63 :
1970–1974 (flush de janvier ; 1975 absent, arrêt au 1er décembre). `len(VEHS)` non utilisé.
Le classifieur ne mappe plus une raison vide vers `waiting_compute` ; les
`passDiscards` (dont `build_failed` / `insufficient_cash`) sont enregistrés sous le gate
C63, pas seulement `decision_log`/`c49`. Une passe A* en vol avec un échec air/route
compte l'échec, pas l'attente. Les totaux leftover+lancé 342–375 j et l'année 1969
sur 5/5 graines viennent d'un flush au 28 décembre qui mélangeait les années : retiré.
Le ledger se ferme au 1er janvier suivant (`OpexC63EnsureYear`) ; la dernière année
d'une partie qui s'arrête en décembre n'est publiée que si le calendrier passe le
1er janvier. Capital immobilisé jusqu'au premier revenu : non mesuré. Eau : 0 ligne.

Jours de reliquat 1970–1972 : absent / invalid / unaffordable / wait / lancé.
Graine 42 = seule graine du smoke 2×3 dont la valeur n'a pas chuté.

| Graine | 1970 | 1971 | 1972 | 1970 | 1971 |
|---:|---|---|---|---|---|
| 42 | 158 / 45 / 0 / 5 / 143 | 70 / 74 / 0 / 67 / 158 | 208 / 30 / 0 / 47 / 76 | portefeuille vide | **mixte** (inv 35 %, abs 33 %, wait 32 %) ; 6 échecs air, `invalid_n=4` |
| 100 | 210 / 71 / 0 / 16 / 55 | 207 / 61 / 0 / 10 / 87 | 207 / 56 / 0 / 0 / 99 | portefeuille vide | portefeuille vide (sonde −38 % à 3 ans) |
| 999 | 86 / 46 / 0 / 17 / 203 | 110 / 50 / 29 / 42 / 133 | 175 / 43 / 0 / 36 / 108 | portefeuille vide | mixte |
| 1234 | 136 / 50 / 18 / 29 / 109 | 155 / 60 / 0 / 30 / 130 | 60 / 97 / 0 / 0 / 190 | portefeuille vide | portefeuille vide |
| 5678 | 202 / 67 / 0 / 0 / 83 | 172 / 23 / 0 / 28 / 140 | 27 / 28 / 0 / 26 / 261 | portefeuille vide | portefeuille vide |

`unaffordable` reste rare (18 j en 1970 sur 1234, 29 j en 1971 sur 999). `demand` = 0.
Recettes, témoins profitables du même mode/âge : air et route en 1970 âge 1, médiane
réel/prévu **≥ 0,91** (air 1,41 / 1,34 ; route 1,10 / 0,91). Rail âge 1 en 1971 :
médiane 0,13 / 0,31, **n=7**. Les lignes positives air/route ne sont pas le trou de 1971.

**Décision historique, supersédée le 2026-09-16.** La conclusion précédente
« ce n'est **pas le capital** » reposait sur le ledger C63 avant correction de 02.1 :
chaque intervalle était crédité à l'état observé **après** l'intervalle. Elle ne doit plus
être utilisée comme conclusion actuelle.

**Clôture B2 / diagnostic C63 corrigé.** `OpexC63NotePass` compte désormais
l'observation courante sans lui attribuer le temps passé depuis la passe précédente ;
ce temps est crédité à `previousKind`/`previousAbsentCause`. Le passage d'année
transporte le dernier état sans fabriquer une observation supplémentaire. Le chemin rail
reprenable enregistre aussi ses outcomes `failed` et `cash` dans `passDiscards`, donc
`insufficient_cash`/`cash_at_build` ne deviennent plus silencieusement `invalid`.

Le diagnostic final `results/review_b2_c63_real_5x6_v2.json` a été exécuté sur
**5 graines × 6 ans**, avec **6 workers / 6 CPU**, mémoire/swap **2g/2g** et cache lab
persistant. Les 5/5 parties atteignent 1975 ; toutes les années C63 closes 1970–1974
sont présentes, 1975 est explicitement `open_partial_year`, `invariants.ok=true`,
aucune année close ne manque et aucun `table_trap` n'est observé.

Sur les 25 années-graines closes, le ledger corrigé totalise :
`unaffordable=1 495 j`, `invalid=1 242 j`, `absent=985 j`,
`waiting_compute=526 j`, `launched=4 819 j`, `demand=0`.
Le capital est donc un **facteur mesuré important, surtout en 1970–1971** ; il n'est plus
exclu par le diagnostic. Ce 5×6 reste instrumenté et n'autorise **aucun changement de
défaut comportemental**. `c63_invest_probe` reste à 0.

**Ventilation de `best == vide` (sonde d'absence C63/P1, 2026-09-14)** :
Une sonde sous gate `c63_invest_probe` ventile les jours d'absence. Deux campagnes 5×6,
à ne pas confondre :

1. **12:03** (`results/diag_c63_c58_6y_5seeds.json`), avant le split unaffordable et
   `empty_probe` : 2654 j `absent` = 2654 j `selection_empty`. Ce JSON **ne contient pas**
   `min_cap`, `avail_cap` ni le nombre d'alternatives. Les bornes « 70–164 » / « 63 k£ vs
   36–48 k£ » citées un temps n'y figurent pas ; elles ne font plus foi.
2. **12:46** (`results/diag_c63_absent_6y_5seeds.json`), après split et sonde échantillonnée :
   1939 j `unaffordable` + 911 j `absent` (toujours `selection_empty`). 135 `empty_probe`
   agrégées : alternatives 81–372 (médiane 233), `min_cap` 15 971–70 806 (médiane 62 653),
   `avail_cap` 3 693–166 935 (médiane 43 661), 103/135 avec `min_cap > avail_cap`, cause
   journalisée `all_unaffordable`. `stage_empty` / `cache_exhausted` / `abandon_filtered`
   restent à 0 j : cette campagne n'exerce pas ces branches. `probe_displaced` reste
   `null` (pas de ON/OFF apparié de la sonde échantillonnée).

**Ne pas générer davantage de candidats par réflexe.** Si le vivier est hors budget,
élargir le scan consomme surtout des opcodes. Le levier à trancher est : candidats moins
chers, réévaluation du cache, ou repêchage des abandonnés — avec les champs déjà
journalisés (`considered`, `min_cap`, `avail_cap`, compteurs d'étape, cache, abandons).

**Comparaison mensuelle 1v1 partagée (2026-09-14).** Le diagnostic C63 ne conservait
aucune métrique du joueur 1 : `n_stations` était le total de la carte, les sauvegardes
étaient nettoyées, `n_ok` comptait une construction réussie plutôt que le tunnel
candidats → acceptés → financés → tentés → construits. Harnais :
[`sweeps/diag_1v1_monthly.py --shared`](../sweeps/diag_1v1_monthly.py), sonde
`monthly_funnel=1` (un AILog par passe projects, défaut 0). Chunks VEHS/STNN/PLYR des
deux compagnies ; waypoints STNN sans `normal` exclus sans invalider le mois ; notes
filtrées `status & 1` (plus la valeur par défaut 175) ; attente = paquets `goods.cargo`.

[`results/diag_1v1_shared_monthly_6y_5seeds.json`](../results/diag_1v1_shared_monthly_6y_5seeds.json)
: 5/5 jusqu'au 1975-12-01, 720 lignes, 0 mois physique `FAIL`. Valeurs OpexAI proches
du C63 absent (moyenne 2,578 M£, médiane 2,923 M£, 1,639–3,215) : la sonde mensuelle
ne rejoue pas le −38 % du smoke C63 ON/OFF. **Pas un banc officiel.**

| Graine | Valeur O vs A | Véhicules | Gares | Air O/A | Route O/A | Rail O/A | Note méd. | HogEx mène dès |
|---:|---|---|---|---|---|---|---|---|
| 42 | 2,92 vs 10,47 M£ (28 %) | 85 vs 254 | 76 vs 177 | 36 / 47 | 48 / 170 | 1 / 37 | 166 / 190 | 1970-11 |
| 100 | 2,03 vs 6,98 M£ (29 %) | 63 vs 197 | 50 vs 168 | 34 / 42 | 27 / 116 | 2 / 38 | 166 / 184 | 1971-05 |
| 999 | 3,21 vs 13,12 M£ (24 %) | 109 vs 353 | 97 vs 234 | 36 / 65 | 69 / 240 | 4 / 48 | 170 / 196 | 1970-08 |
| 1234 | 1,64 vs 8,81 M£ (19 %) | 64 vs 293 | 60 vs 197 | 23 / 58 | 35 / 194 | 6 / 41 | 170 / 180 | 1971-02 |
| 5678 | 3,08 vs 15,80 M£ (20 %) | 81 vs 339 | 67 vs 221 | 36 / 72 | 40 / 225 | 5 / 42 | 170 / 196 | 1970-11 |

AAAHogEx gagne **d'abord par le volume et par l'air précoce**, pas par une rentabilité
unitaire d'un autre ordre. En décembre 1970 elle a déjà plus d'avions (13 vs 4) et une
valeur supérieure, souvent avec *moins* de véhicules. Le dépassement en nombre d'unités
n'arrive qu'en 1971. Ensuite la route HogEx explose (2 → 189 véhicules moyens en 1970–1975)
pendant qu'Opex reste à ~44 bus/camions et ~4 trains. Revenu trimestriel par véhicule
×1,3–1,8 ; notes de gare meilleures ; attente par gare *plus faible* chez HogEx
(les quais Opex sont plus chargés, 2,3–3,3 k vs 1,2–1,9 k). Eau : 0 / 1 navire.

Tunnel OpexAI (somme des passes, pas des projets uniques) : 244 705 considérés →
11 084 acceptés (4,5 %) → 3 170 tentés → 2 862 passés caisse → **213 construits**
(6,7 % des tentatives, 1,9 % des acceptés). AAAHogEx : 3 312 succès de construction
journalisés / 104 échecs (97 %). Rejets Opex : `build_failed` 1211, `search_in_progress`
994, `insufficient_cash` 308, `abandoned_pair` 214, `plan_failed` 181. 1970–1972 :
caisse / A* / `plan_failed`. 1973–1975 : `build_failed` (1136) et A* (808), le taux
ok/tentative tombe de 15 % à 4 %. Ce n'est plus « pas de candidat » : le portefeuille
accepte, la carte refuse.

Pas de correctif. Le levier n'est pas « plus de candidats » ; c'est convertir les
acceptés en constructions, surtout air précoce et tenues de chantier (`build_failed`).

**Candidat causal P1 pré-enregistré le 2026-09-15 — `air_town_limit_memory=1`.** Le diagnostic
détaillé identifie `AIStation.ERR_STATION_TOO_MANY_STATIONS_IN_TOWN` (771) comme cause dominante
des échecs air : 1 396 occurrences sur 1 590 `build_failed` dans le 5×6 instrumenté OFF. Le
mécanisme candidat ne change ni score, ni budget, ni demande : après un vrai 771 il mémorise
temporairement la commune via le cooldown/backoff d'abandon. Le pilote instrumenté réduit 771 de
1 396 à 114 et `build_failed` de 1 590 à 228 ; ce signal choisit le mécanisme, pas le seuil.

Règle figée avant le prochain 5×6 apparié : primaire `profit_year`, delta moyen variante −
référence **>= +45 000 £/an** ; garde-fou `company_value`, rapport des moyennes **>= 98 %**
(perte maximale 2 %). Les 5 graines 42/100/999/1234/5678 doivent toutes être complètes et saines.

**Piste à examiner plus tard autour de l'erreur 771 / `ERR_STATION_TOO_MANY_STATIONS_IN_TOWN`.**
Ne pas supposer que l'un de ces points est la cause tant qu'il n'est pas confirmé dans OpenTTD et
sur nos sauvegardes :

- vérifier, dans chaque ville qui déclenche 771, le **nombre réel de stations**, leur propriétaire,
  leur type et si OpexAI contribue elle-même à saturer la limite locale ;
- mesurer combien de stations OpexAI y sont **orphelines, inutilisées ou issues de chantiers
  partiellement abandonnés**, et tester si leur nettoyage libère effectivement la capacité locale ;
- étudier en priorité un **rattachement / distant join à une station OpexAI existante** plutôt que
  la création d'une nouvelle entité station, si l'API IA permet de reproduire le mécanisme du
  `Ctrl` manuel ; comparer notamment avec les mécanismes `station_join` / `air_joined_stops`
  déjà présents dans OpexAI ;
- distinguer cette limite de nombre de stations du réglage **Max station spread** : ce dernier
  concerne a priori l'étendue spatiale d'une station existante et ne doit pas être modifié comme
  contournement de 771 sans preuve dans le code OpenTTD ;
- seulement après ces mesures, comparer trois politiques : évitement temporaire de la ville
  (`air_town_limit_memory`), rattachement à une station existante, ou nettoyage ciblé des stations
  réellement inutiles. Ne jamais bulldozer une infrastructure active uniquement pour libérer un
  slot.

**Sonde exacte au moment du 771 (2026-09-15).** `task_air.nut` compte désormais les aéroports
OpexAI déjà rattachés à la ville de l'ancre qui échoue, et `task_projects.nut` agrège cette valeur
dans le funnel sous `build_error_air_own_airports_<n>`. La méthode
`AIStationList(AIStation.STATION_AIRPORT).Valuate(AIStation.GetNearestTown)` est valide en jeu :
le diagnostic ne plante pas.

- smoke 3 ans seed 42 : `results/diag_771_error_own_airports_seed42_3y_v2.json`,
  **11 erreurs 771 / 11 avec Opex=0 aéroport dans la ville** ;
- diagnostic 6 ans seed 42 : `results/diag_771_error_own_airports_seed42_6y_v3.json`,
  **291 erreurs 771 / 291 avec Opex=0** ;
- répartition 6 ans : town 15=38, 24=29, 27=35, 30=48, 31=15, 32=10, 34=38,
  36=44, 38=34.

Conclusion sur cette graine : le 771 observé n'est **pas** une auto-saturation par des aéroports
OpexAI. Puisque la partie est un duel et que la limite OpenTTD 15.3 est de deux aéroports par ville
avec `station_noise_level=false`, ces échecs arrivent lorsque les deux slots sont déjà détenus par
AAAHogEx. Nettoyer des stations OpexAI ne traite donc pas ces cas. Le distant join ne permet pas non
plus de créer un troisième aéroport : le contrôle de capacité de la ville intervient avant ce
mécanisme.

Priorités 771 qui en découlent : (1) prendre les slots utiles plus tôt, (2) tester un placement
périphérique dont l'ancre est rattachée à une ville voisine encore disponible tout en rabattant la
ville cible, (3) détecter les constructions AAAHogEx et accélérer la prise du slot restant. Ces
runs sont des **diagnostics instrumentés**, pas des benchmarks économiques d'adoption.

**Revue B1 — faux site 771 corrigé (2026-09-16).** Sous `air_cheap_site=1`,
`BuildAirport` pouvait échouer puis être transformé en succès dès que l'empreinte était
plate/nivelable. Le repli de nivellement n'est désormais admis que pour
`ERR_LOCAL_AUTHORITY_REFUSES` et `ERR_FLAT_LAND_REQUIRED`; 771 et les autres erreurs restent
décisives. Aucun pathfinder ni budget n'a été modifié.

- smoke post-correctif 2×3 : `results/review_b1_probe_fix_smoke_2x3.json` → **PASSED** ;
- diagnostic 5×6 : `results/review_b1_probe_fix_5x6.json` → **5/5 complets** ;
- contre la référence pré-correctif, trois graines sont identiques et deux divergent ; delta
  moyen `company_value = -183 428 £`, `profit_year = -32 569 £/an` : correction de vérité du
  verdict de sonde, **pas** optimisation économique ;
- `air_town_limit_memory` reste à 0. Le 5×6 historique antérieur à 08.1 était défavorable et le
  rerun C66.4 sur la nouvelle base a été bloqué avant toute partie : aucune adoption n'est inférée ;
- distant join/nettoyage OpexAI ne contournent pas le plafond observé ; `early_slot` reste acquis.

**Décision et explication causale — `air_early_slot` adopté (2026-09-15).** La priorité « prendre
les slots utiles plus tôt » a été implémentée et **adoptée** ; ne pas rouvrir la décision au motif
que le nombre final de monopoles AAA converge. Le banc économique officiel
`results/bench_early_slot_20x10_w6.json` (20 seeds × 10 ans, current vs early-slot) donne en 1979
`profit_year` OpexAI ≈ 1,331 M£ → 1,485 M£, soit **+154 k£/an, +11,6 %**.

Le diagnostic causal passif `results/diag_early_slot_lines_20x10_v1.json` (40/40 parties,
20/20 paires) et son analyse `results/diag_early_slot_lines_20x10_v1_analysis.json` montrent pourquoi :

- le nombre total de marchés air AAAHogEx converge presque (1979 : **24,20 current vs 23,75
  early-slot**), mais seulement **12,20** sont encore communs ; environ la moitié du portefeuille a
  changé ;
- les marchés AAA `current-only` passent de 6,0/seed en 1972 à 12,0 en 1979 ; ceux qui touchent au
  moins une ville occupée par OpexAI sous early-slot représentent **62 % de leur profit en 1972**,
  puis **73–76 % en 1976–1979** ;
- certaines routes déplacées valent plusieurs centaines de k£/an observés ; le maximum relevé dans
  le top causal atteint ~951 k£/an ;
- AAAHogEx compense en partie par de nouveaux marchés : son profit air total peut même être supérieur
  sous early-slot en 1975–1976. Le mécanisme n'est donc pas « détruire X £ chez AAA », mais une
  **réallocation précoce des marchés puis une dépendance au chemin** ;
- un seul endpoint stratégique suffit souvent : en 1979, 8,1 marchés current-only/seed touchent une
  ville OpexAI, contre seulement 2,6 dont les deux endpoints sont occupés.

Conclusion : **early-slot prive surtout AAAHogEx de certains marchés précoces très rentables autour
des villes qu'OpexAI sécurise, puis AAA se redéploie ailleurs.** Cela explique qu'un avantage de
profit OpexAI persiste alors que les compteurs finaux d'aéroports/monopoles se rapprochent. Le détail,
la méthode de reconstruction VEHS/ORDL/STNN et les limites (`profit_this_year` des véhicules encore
présents, `group_id` local, pas de revenue/running_cost inventé) sont figés dans
[`07_air_early_slot_causal_analysis.md`](07_air_early_slot_causal_analysis.md).

**Correctif feeders bus — ordres unidirectionnels ville → hub (2026-09-15).**
Bug confirmé dans `builder_road.nut` : les feeders passagers utilisaient `OF_NONE` à la ville et
`OF_TRANSFER` au hub, avec `OF_NO_LOAD` seulement si le switch global fret `c53_order_noload`
était actif. Cela permettait de décharger des passagers au mauvais bout et surtout d'en reprendre
au hub/aéroport au retour. Corrigé dans les deux chemins de création (construction initiale et
refleet) :

- arrêt ville : `OF_NO_UNLOAD` — chargement disponible uniquement, aucun déchargement ;
- arrêt hub/aéroport : `OF_TRANSFER | OF_NO_LOAD` — transfert complet vers la gare commune,
  aucun nouveau chargement, le bus repart vide ;
- `OF_TRANSFER` est conservé plutôt que `OF_UNLOAD` afin que les passagers restent disponibles
  pour la correspondance avion/train au lieu d'être traités comme une destination finale.

Smoke fonctionnel : `results/feeder_orders_exercised_s42_3y.json`, seed 42, 3 ans, feeders
explicitement exercés via `feeder_candidates=1,feeder_hub_check=0`, 2/2 jeux complets,
`failed_runs=[]`. La divergence économique de ce smoke n'est **pas** une preuve d'adoption du mode
feeder ; ce run valide seulement que le chemin modifié construit et tourne sans rejet d'ordre.

> **Décision courante — 2026-09-17 : feeders supprimés.** Les sections feeder ci-dessous sont
> conservées uniquement comme historique expérimental. Après vérification du code OpenTTD et des
> mesures B9, les arrêts `air_joined_stops` appartiennent au même `StationID` que l'aéroport et
> étendent déjà directement son union de catchment. Le second mécanisme de rabattement routier
> concurrençait donc ce captage sans topologie suffisamment cohérente. Le réglage `feeder_enabled`,
> la génération/pricing/exécution/refleet feeder, les ordres de transfert dédiés, leur télémétrie
> et leurs tests actifs ont été retirés du code de production. Les anciens JSON et scripts de
> diagnostic restent des archives de mesure, pas une politique disponible.

**Re-test apparié de `feeder_candidates` sur la base courante (2026-09-17, historique).**
`results/review_feeder_candidates_5x6_20260917.json`, 5 graines × 6 ans, compare uniquement
`feeder_candidates=0` à `1` avec tous les autres défauts courants identiques : **4 défaites / 1
victoire**, delta moyen `profit_year = -105 350 £/an`, `company_value = -14,36 %`, et score de
performance inférieur sur **5/5** graines. L'ancien vivier global reste donc désactivé et ne mérite
pas de 20×10 sur cette base.

La **seed 999 est le contre-exemple à conserver pour étude ultérieure** : `feeder_candidates=1`
y gagne **+186 326 £/an** de `profit_year` et **+527 221 £** de valeur malgré `-19` points de
performance. À analyser par propriétés de carte et trajectoire : position de l'aéroport dans la
ville, production restant hors catchment des pièces jointes, densité/voirie autour des meilleurs
stops, longueur/coût du feeder et moment où il est construit. L'objectif est d'expliquer pourquoi
un vrai feeder est utile sur cette carte sans réactiver le vivier global.

**Feeder résiduel hybride (expérimental, 2026-09-17, retiré).** Nouveau switch `air_residual_feeder=0`
par défaut. Il reprend le modèle observé chez AAAHogEx sans modifier l'ancien
`air_split_feeder_test` : les arrêts joints restent prioritaires ; seuls les hubs **air** peuvent
ensuite produire un feeder dans leur propre ville, et seulement si de la production passagers reste
hors de l'union réelle du `StationID`. Après choix du stop routier, cette production marginale est
recalculée tuile par tuile avant toute dépense ; un stop devenu redondant est rejeté. Le feeder
démarre avec **un seul bus**, avec les ordres stricts ville `NO_UNLOAD` → hub
`TRANSFER|NO_LOAD`; la cible de flotte reste conservée pour le refleet ultérieur. Ce switch doit
être mesuré apparié avant toute adoption.

**Clôture B4 — extensions feeder bus (2026-09-16).** Une régression restante du correctif ci-dessus
a été trouvée puis corrigée dans le workspace courant : `feeder_extension` insérait encore un arrêt
intermédiaire avec `OF_NONE`, et le feeder bus dédié de `task_feeders.nut` ne persistait pas son
`kind`, ce qui le rendait inéligible à cette extension. Les trois producteurs d'ordres bus utilisent
désormais les mêmes helpers : ville/intermédiaire `OF_NO_UNLOAD`, hub
`OF_TRANSFER | OF_NO_LOAD`. Le feeder bus dédié stocke `kind = candidate.kind`; le feeder courrier
reste volontairement sans `kind` pour ne pas entrer dans le filtre pax.

Preuves : `sweeps/test_b4_feeder_orders.py` 6/6 ; `diag_c53_orders.py --selftest` OK ; smoke
obligatoire post-`.nut` `results/review_b4_smoke_2x3.json` PASSED ; diagnostic réel
`results/review_b4_bus_extensions_5x6_ordl.json` sur 5 graines × 6 ans avec feeders isolés :
**13 `feeder_extension`** réellement construites, 3 `bus_pax_extension`, 12 listes d'ordres feeder
étendues distinctes observées en fin de partie, `errors=[]` et `invalid_extended_feeders=0` sur les
cinq graines. ORDL confirme pour chaque chaîne observée `LOAD_IF_POSSIBLE + NO_UNLOAD` sur tous les
arrêts ville/intermédiaires et `NO_LOAD + TRANSFER` au hub. Le dernier ajout après le smoke est
uniquement l'inspection Python ORDL, pas du gameplay. **Aucun défaut/politique n'est adopté sur ce
5×6** ; il s'agit d'une validation ciblée, donc aucun 20×10 n'est requis.

**Correctif feeders courrier — ordres unidirectionnels ville → hub (2026-09-15).**
`task_feeders.nut` applique désormais la même sémantique stricte aux feeders courrier, derrière
le switch causal `feeder_mail_strict_orders` (défaut = 1) :

- arrêt ville : `OF_NO_UNLOAD` — chargement uniquement ;
- arrêt hub/aéroport : `OF_TRANSFER | OF_NO_LOAD` — transfert complet sans nouveau chargement,
  le camion repart vide ;
- `OF_TRANSFER` est conservé : ne pas le remplacer par `OF_UNLOAD`, et ne jamais combiner
  `OF_TRANSFER | OF_UNLOAD`.

Banc causal rapide : `results/bench_feeder_mail_strict_orders_3y_5seeds.json`, 5 seeds
(42, 100, 999, 1234, 5678), 3 ans, 1 repeat, 6 CPU / 6 workers, 10 jeux complets,
`failed_runs=[]`. Les deux bras forcent exactement le même ancien régime feeder
(`feeder_candidates=1, feeder_portfolio=0, feeder_hub_check=0, feeder_mail_duplicate=1`) et ne
diffèrent que par `feeder_mail_strict_orders=0/1`.

Résultat strict − legacy :

| Seed | Δ company value | Δ profit_year | Δ rating médian |
|---:|---:|---:|---:|
| 42 | -253 864 | -259 667 | 0 |
| 100 | -158 500 | -162 630 | -24 |
| 999 | -6 082 | -26 217 | +2 |
| 1234 | -506 897 | -165 992 | +15,5 |
| 5678 | -738 604 | -608 338 | +4 |

Moyenne : **−332 789** de company value et **−244 569/an** de `profit_year`.
Médiane : **−253 864** et **−165 992/an**. Le strict fait **0/5 victoire** sur les deux métriques
économiques. Le rating médian n'explique pas le signal (delta moyen +0,5). Les seeds 42 et 5678
terminent en plus avec respectivement 70 k£ et 300 k£ d'emprunt supplémentaire.

Interprétation : la correction fonctionnelle des ordres est valide et reste le comportement par
défaut, mais dans ce régime **forcé** elle dégrade fortement l'économie à 3 ans. Ce banc expose
volontairement le chemin feeder courrier ; il ne doit pas être extrapolé tel quel au défaut courant
où `feeder_candidates=0`, ni pris comme validation économique générale du portefeuille feeder.

**Désambiguïsation structurelle (2026-09-14) :** l'amalgame `best=absent` / `selection_empty`
classait tout `best.len()==0` en `absent`. Corrections en place :

1. **`OpexC63NotePass`** : si `budgetConsidered > 0 && minCapital > available`, `unaffordable`
   et non `absent`.
2. **`OpexProjectsStampSelectionStats`** : `minCapital`, comptes rail/route/air/eau, cache,
   abandons et `emptyCause` sur les trois producteurs, y compris `OpexReselectProjects`.
3. **`OpexC63ClassifyAbsent`** : un compteur manquant n'est plus traité comme 0 (plus de
   `stage_empty` systématique). Repli sur `projects.rail` / `road` / `airPlans` / `waterPlans`.
4. **Sonde `OpexC63RecordEmptyProbe`** : via `_c63RecordPassAndProbe`, à la transition
   non-vide→vide (`lastKind` absent/unaffordable) ou 1×/mois. Journalise stage, cargo,
   comptes d'étape, `min_cap`, `avail_cap`, cache et abandons.
5. **`phase=opp_absent`** écrit les 9 causes, y compris `stage_empty`, `cache_exhausted`,
   `abandon_filtered`. Le parseur les lit. `absent_d` ≠ somme des causes devient un piège
   `absent_causes_do_not_sum` / `absent_causes_unlogged`.

Sortie attendue : **un tableau par mode, année et cohorte de lignes**, contenant :

- coût prévu, coût engagé, dépenses d'échec/rollback et capital immobilisé jusqu'au premier
  revenu ; couverture et montants non attribués explicités ;
- revenu/profit attendu contre profit observé à périmètre comparable, âge depuis la mise en
  service, rotations/remplissage lorsque mesurables ; distinguer résultat d'exploitation
  d'une ligne et résultat de compagnie, qui n'ont pas les mêmes charges ;
- nouvelles lignes et renforts, demande effectivement captée, partage de gares/bassins et
  présence concurrente ; un stock à quai est un symptôme, pas une preuve de revenu récupérable ;
- trésorerie **mobilisable selon `OpexAvailableCapital`** : caisse + emprunt effectivement
  accessible − réserve, face au besoin réel du projet ;
- sur les occasions où une décision peut être prise : candidat absent, invalide/site refusé,
  non finançable, demande/capacité insuffisante, en attente de calcul ou effectivement lancé.
  Rapporter séparément occurrences et **jours de jeu** ; aucune double attribution silencieuse.

**Deux corrections de méthode indispensables :**

- « Caisse ≥ 300 k£ et rien construit » ne prouve pas un manque de débit. Il faut un projet
  rentable, réalisable et finançable qui attend. Réciproquement, un surcoût modèle de 30 % ne
  prouve pas qu'une baisse du coût résoudrait le problème. Le bilan peut rester mixte ou inconclusif.
- C58 ne doit pas observer seulement `ET_VEHICLE_UNPROFITABLE` : cela sélectionne les perdants
  et rate les lignes positives qui rapportent bien moins que prévu. Comparer aussi des lignes
  profitables du même mode et du même âge. Pas de ferraillage automatique dans cet audit.

Les deltas de solde bancaire peuvent inclure revenus, entretien ou emprunts pendant un chantier :
ne pas les appeler coûts purs sans réconciliation. Deux smokes identiques sondes ON/OFF sont
un contrôle préliminaire, **pas une preuve de neutralité sur six ans**. Privilégier l'extraction
hors jeu ; si une instrumentation est nécessaire, mesurer sa perturbation et séparer son
résultat du banc économique final, exécuté sans instrumentation lourde.

**Décision à la sortie, avant tout autre diagnostic :**

| Fait observé sur des lignes/occasions identifiées | Suite autorisée par le diagnostic |
|---|---|
| Dépenses d'infrastructure/échecs immobilisant matériellement le capital | Un correctif de placement, réutilisation ou estimation sur le mode concerné ; pas de devis rail synchrone généralisé |
| Lignes positives mais recettes très inférieures au modèle | Corriger une hypothèse de demande, captage ou rotation ; C58/C59 |
| Demande non servie sur une infrastructure rentable ayant de la capacité | C61 ciblée, avec dépense et congestion observées |
| Projets valides finançables retardés pendant un coût de calcul identifié | C39/C41 ciblée |
| Pas de cause dominante ou données insuffisantes | Publier les limites et nommer la seule donnée manquante ; ne pas déclarer arbitrairement « capital » ou « CPU » |

**Fin de P1 (2026-09-13) :** hypothèse « capital » close. Hypothèse « modèle de revenu
air/route » close sur les témoins 1970–1971. L'attente A* n'est pas le reliquat 1971
(graine 42 mixte après correction du classifieur). La seule donnée manquante est
**pourquoi le portefeuille est vide** les jours `absent`, sans sonde qui déplace. Pas
de second levier.

<a id="c61"></a>
<a id="c59"></a>
## P2 — C61/C59 : mieux exploiter les lignes, si P1 le justifie

**Acquis causal C50b**, [banc consolidé](../results/bench_c50b_levers_10y_40seeds.json) :
supprimer la réserve de demande aérienne détruit de la valeur sur 20/20 graines ; relever le
plafond routier perd 27 paires sur 40 en valeur ; supprimer le cap de cadence aérien est
inconclusif à 21/40. Ajouter des véhicules n'est donc pas en soi le chantier prioritaire.

- **Air :** mesurer rotations, attente, demande et occupation aux deux aéroports avant de
  remplacer le partage égal de cadence entre lignes. `airportDelayDays = 3` et la table par
  type sont des modèles à qualifier, pas des capacités mesurées. Le modèle mutualisé proposé
  dans le dossier C61 reste un candidat, pas une spécification validée.
- **Route :** séparer fret, feeders et passagers interurbains. **`road_pax_build=0` au défaut** :
  une réforme visant les bus interurbains ne résoudra pas le duel courant. Le fret en chargement
  complet demande une mesure d'attente distincte du dwell passagers ; ne pas diviser par son
  `dwellDays=0`. La cible est du trafic rentable supplémentaire, pas le passage de 2 à 8 véhicules.
  **B3 clos le 2026-09-16 :** `vehiclesForVolume`, `roadBerthCapacity` et `roadVehicleCap` sont
  maintenant séparés et instrumentés. `road_time_scaled_cap` reste **0** ; sous 1 le cap temporel
  ne s'applique qu'au pax et le fret reste à l'ancien cap. Le smoke 2×3 final passe ; le 5×6
  `review_b3_time_scaled_cap_paired_5x6_v2.json` a 10/10 runs sains et tous les invariants physiques
  attendus, mais **aucun projet pax n'est classé/choisi** au défaut (`road_pax_build=0`) et les pax
  `town_growth` ont `raw_vehs <= 1`. La variante est négative (`company_value` -52,1 k£ moyen,
  `profit_year` -29,1 k£/an, 2 V / 3 D) : pas de 20×10, pas d'adoption. Le switch et la télémétrie
  sont conservés pour une politique future réellement exposée.
- **Rail :** la relaxation du seuil de backlog a déjà été inerte. C50b rapporte 39 `NOSPOT`
  pour 28 `OK` et 2 `TRACKFAIL` sur les références d'extension : inspecter les échecs de géométrie
  **si** les lignes concernées sont profitables et demandent réellement un second train.
  Cela ne justifie pas encore un chantier global de jonctions et gares partagées.
- **Ordres C59 :** corréler chargement, attente et profit avant une politique contextuelle.
  Retirer la prémisse « longue distance ⇒ full load mathématiquement supérieur » : attente,
  demande, prix du transport et congestion doivent entrer dans la comparaison. Une photographie
  de `cargo_count` ne mesure pas à elle seule le remplissage au départ ni une rotation.

<a id="c39"></a>
<a id="c41"></a>
<a id="c44"></a>
## P2 conditionnelle — C39/C41/C44 : traiter une occasion perdue, pas une lenteur abstraite

Les profils C39/C48 du 10 septembre montrent une augmentation du coût de génération avec
la maturité du réseau. Ils ne prouvent pas à eux seuls le gain d'une optimisation aujourd'hui.
Le [banc C48 final](../results/bench_c48_indexed_regeneration_10y_20seeds.json) donne
**10 victoires / 10 défaites en valeur**, +0,53 % en moyenne : gain économique non démontré,
`c48_indexed_regeneration=0` conservé. C46 reste également à 0 malgré un coût fret réduit en 1024².

Reste utile : critère de fraîcheur par couche, invalidation et recomputations évitables,
**sur le chemin où P1 aura montré des occasions finançables retardées**. Les modules actuels
sont `scheduler_tasks.nut`, `task_projects.nut`, `projects.nut` et `catalog.nut` ; les anciens
numéros de ligne de `main.nut` sont périmés après C65.

Ne pas relancer `portfolio_max_batch`/`portfolio_dynamic_batch`, un prix d'opcode ajouté au
score, ni un orchestrateur général sur la seule foi d'anciens profils. La fiche C39.5 est
close sur son levier testé ; « construit au premier tour » ne signifie cependant pas qu'un
intervalle entre tours est gratuit. Mesurer en jours, à âge de partie comparable, et vérifier
ce qui devient effectivement constructible. **Le titre catégorique de C44 (« ni capital ni
opcodes : le tour ») est retiré**, tout comme le « facteur 15 inexpliqué » déjà corrigé par C39.6.

## Autres tâches ouvertes, hors séquence prioritaire

Les travaux clos C45/C46/C47/C48/C49/C50/C51/C52/C53/C54/C55/C56/C62/C65 et les étapes déjà
livrées des autres fiches sont consignés dans [le journal du jour](journal_2026-09-13.md).
Ne pas les remettre dans la file active sans fait nouveau.

| Fiche | Travail restant | Condition de reprise |
|---|---|---|
| C52 | **CLOS 2026-09-20** — corrections crash/non rentable revalidées sur le code courant ; aucun défaut de service reproduit | Rouvrir seulement sur défaut de service observable ; la politique reste à 0 |
| C60 | **CLOS 2026-09-20** — aucune exposition réelle sous la configuration canonique permissive ; filtre laissé désarmé | Rouvrir seulement si `difficulty.town_council_tolerance` devient non permissif dans le protocole ou si un refus de gare par note est reproduit |
| C57 | **ABANDONNÉ — ne plus calibrer les 50 000 opcodes de Lakes** | Architecture MinchinWeb.Lakes abandonnée le 2026-09-17 ; ne pas investir dans le réglage d'un composant destiné à être retiré |
| **C67** | **Analyse spatiale de la carte par blocs + remplacement propre de Lakes** | Concevoir/mesurer la grille 5×5 vs 10×10, le typage des blocs et ses usages eau/terrain avant toute migration comportementale |
| C43 / E3 | Constantes non tranchées : réserve, `pax_near`, seuils de mise au rebut. `loop_budget` est clos/non adopté. | Constante impliquée par le diagnostic ; pas de balayage général |
| C45, reliquat | **CLOS 2026-09-20** — état actif déjà persisté ; compteurs de sonde volontairement transitoires | Test de contrat `test_c45_subsidy_persistence.py` ; ne pas sérialiser de télémétrie morte |
| C42 bis | Filtrage/rendement des subventions | Exposition rentable démontrée ; les subventions brutes restent à 0 |
| C55, reliquat | Partage de demande et sur-service des bassins | Flux concurrents observés par P1 ; ne pas rouvrir le filtre d'origine |

**Clôture C52 — 2026-09-20.** Les diagnostics ont d'abord été remis sur les réglages regroupés
actuels : `diag_c52_events.py` compare `probe_events=1` à
`policy_vehicle_events=1,probe_events=1`, et les sondes C52 autonomes passent désormais par
`probe_events=1`. Les trois selftests de sonde passent, ainsi que **12/12 tests lifecycle ciblés**
sur crash, retraite, autoreplace et refleet. Le smoke 1×1 est complet et identique entre les deux
bras. Le diagnostic apparié
[`diag_c52_revalidate_6y_5seeds.json`](../results/diag_c52_revalidate_6y_5seeds.json) est complet
**10/10, 0 erreur** : politique active contre désarmée = valeur moyenne **4 902 664 £ vs
4 824 164 £** (+78 501 £, +1,63 %) et profit annuel **1 328 934 £ vs 1 294 921 £**
(+34 013 £/an, +2,63 %), avec **2 gains / 2 pertes / 1 égalité** sur les deux métriques.
Ce 5×6 reste un diagnostic et ne justifie donc aucun changement de défaut.

Le chemin crash est réellement exposé : le bras actif enregistre **7 `VEHICLE_CRASHED` et
7 `CRASH_REFLEET`**. Le chemin non rentable reçoit **12 `VEHICLE_UNPROFITABLE`** mais aucun
`UNPROFITABLE_RETIRE`/`UNPROFITABLE_SCRAP` sur six ans ; même le contrôle graine 42 avec seuil
forcé à 1 reste sans retraite, cohérent avec la garde de jeunesse `age >= 365`. Aucun défaut de
service n'étant observé, la sonde `ET_STATION_FIRST_VEHICLE` n'a pas été utilisée pour décider.
Le contrôle supplémentaire 10×5 destiné seulement à forcer l'exposition non rentable a finalement
été relancé après rétablissement de Docker :
[`diag_c52_unprofitable_exposure_10y_5seeds.json`](../results/diag_c52_unprofitable_exposure_10y_5seeds.json)
est complet **5/5, 0 erreur** sous `policy_vehicle_events=1,probe_events=1` avec
`unprofitable_streak_threshold=1`. Il enregistre **69 `VEHICLE_UNPROFITABLE`**, dont **6
`UNPROFITABLE_RETIRE` et 2 `UNPROFITABLE_SCRAP`** ; le même banc voit aussi **19
`VEHICLE_CRASHED` et 19 `CRASH_REFLEET`**. Le chemin non rentable n'est donc pas mort : il agit
dès qu'un événement atteint aussi les autres gardes d'éligibilité. Ce seuil forcé à 1 reste une
sonde d'exposition, sans bras de comparaison et sans autorité d'adoption ; la politique et son
default restent inchangés.

**Clôture C60 — 2026-09-20.** La première mesure courante a semblé montrer 2 790 refus rail,
mais elle a révélé un défaut de la sonde : `OpexC60ObserveTownRating()` comparait directement
l'enum de réputation à `VERY_POOR` sans appliquer la garde
`difficulty.town_council_tolerance == 0`, alors que le vrai prédicat
`OpexTownRatingAllowStation()` l'applique. Le bras filtre temporaire était donc strictement
identique au contrôle sur le 5×6 `results/diag_c60_filter_6y_5seeds.json` (5/5 égalités sur
valeur, profit, véhicules, gares et opcodes observés).

La sonde réutilise désormais le prédicat comportemental exact. Le rerun passif
`results/diag_c60_current_exposure_6y_5seeds_v2.json` est sain **5/5** et cumule
**145 501 contrôles** au dernier rapport annuel disponible : route **0**, rail **134 125**,
air **11 376**. Il observe pourtant **1 290 `VERY_POOR` + 429 `APPALLING`**, mais
**0 refus réel** dans les trois modes. La configuration canonique est donc permissive sur ce
point ; C60 n'a aucun levier comportemental à benchmarker davantage. Le filtre reste forcé à
`false` et aucun 20×10 n'est justifié. Rouvrir uniquement si le protocole passe à une tolérance
municipale non permissive ou si un refus par note est reproduit.

**Clôture B8 / G10 — 2026-09-16.** Le sous-comptage de flotte AIR avant rapport reste infirmé et
ne doit pas être rouvert. Le défaut réellement actif était le cycle de vie : une ligne AIR pouvait
encore produire/exécuter un projet de croissance pendant sa liquidation. Deux gardes symétriques
ferment maintenant ce chemin (`_resizeAirFleets` puis `_tryBuildFleetProject`). Le timer de rebut
`scrapStartYear` est recréé à chaque cycle, effacé lors d'un sauvetage feeder et garde son fallback
pour les anciennes sauvegardes. Test ciblé 7/7 ; smoke `air_early_slot=1` 2×3 PASSED ; diagnostic
`review_b8_scrap_lifecycle_5x6.json` sain 5/5 mais **sans exposition runtime du rebut** sur
1970–1975. Ne pas lui attribuer de gain économique et ne pas lancer de 20×10 pour cette correction
de sûreté. `early_slot` reste inchangé.

## Eau, bibliothèques et robustesse — P1 techniques clos, architecture Lakes abandonnée

Le code courant utilise encore la transcription MinchinWeb dans `lib_water.nut`, avec budget en
opcodes. **Décision du 2026-09-17 : ne plus poursuivre cette architecture et supprimer l'import/
transcription Lakes lors du chantier C67.** Il ne faut donc ni recommencer son intégration ni
calibrer davantage ses constantes. Le code n'est pas retiré dans cette étape documentaire : il
reste le chemin courant jusqu'à ce que son remplacement soit implémenté et validé.

La bibliothèque n'apporte pas à elle seule des lignes rentables ; le catalogue de sites intégré aux
rebuilds a été testé sans justifier son adoption.
L'ancien essai Lakes du 09/09 précède le correctif de gel C56 et ne tranche pas à lui seul le
défaut combiné actuel. La revue du 17/09 ferme toutefois deux défauts techniques directement
observables : 10.1 rend le budget d'opcodes interruptible jusque dans les parcours internes de
Lakes ; 10.3 déplace le BFS borné de validation des fronts réels avant toute dépense de quai sur
le chemin Lakes. Aucun réglage ni politique économique n'est changé.

Le dossier eau conserve : découverte de sites séparée du portefeuille et rotations fractionnaires.
**10.5 est clos comme mesure externe** : le micro-banc Lakes donne une pente stable d'environ
128 B/tuile et 14 opcodes/tuile de 256² à 2048² ; à 2048², 3/3 allocations longues terminent avec
524 788 KiB de delta RSS médian et 58 726 159 opcodes nets. **10.2 est clos** : quand Lakes confirme la
connectivité mais que la distance navigable exacte reste inconnue, le candidat est désormais rejeté
avant `OpexWaterEconomics` au lieu de substituer Manhattan. **C57 est abandonné** : la valeur
`WATER_LAKES_OPS = 50 000` ne sera pas calibrée puisque Lakes doit disparaître. Les corrections
10.1/10.2/10.3 restent des preuves historiques utiles sur le chemin courant, pas une raison de le
conserver. Le scan ciblé des anciennes graines 2026/1337 est inconclusif faute de traces
C56 datées (`frozen_count=null`) et ne doit être lu ni comme reproduction ni comme absence de gel.
La consigne existante d'accord explicite avant un nouveau diagnostic de découverte maritime reste
conservée.

### C67 — analyse spatiale de la carte par blocs et remplacement de Lakes

**Décision de conception du 2026-09-17.** Repartir de zéro sur une représentation de carte propre à
OpexAI, commune à l'analyse du terrain et au futur remplacement de la connectivité Lakes. La carte
est découpée en blocs carrés réguliers ; deux granularités candidates sont à mesurer, **5×5** et
**10×10 tuiles**. La taille n'est pas fixée par intuition : le premier livrable de C67 doit comparer
coût mémoire/opcodes, précision et utilité pour les décisions.

Chaque bloc porte un résumé compact calculé depuis ses tuiles, au minimum : part eau/terre,
altitudes min/max/moyenne, amplitude de relief, proportion de terrain plat et indicateur de
pente/irrégularité. À partir de ces mesures, le bloc reçoit un type principal tel que **eau**,
**côte/mixte**, **plat**, **vallonné** ou **montagne**. Les seuils exacts et l'éventuel typage
secondaire sont à calibrer sur cartes réelles ; ils ne doivent pas devenir des constantes métier
avant mesure.

Les blocs forment ensuite un graphe spatial léger de voisinage. Ce niveau grossier doit pouvoir
servir à plusieurs consommateurs sans dupliquer des scans de carte : présélection de corridors,
coût/complexité de terrain, détection de grandes zones d'eau et connectivité grossière. Les tests
fins restent au niveau tuile lorsque la construction l'exige ; C67 n'a pas vocation à remplacer un
pathfinder exact par une classification grossière.

**Principe d'exécution : cartographie lazy et opportuniste.** C67 ne doit jamais lancer une grosse
tâche monolithique de cartographie complète au démarrage. Un bloc est calculé lorsqu'un projet a
besoin de l'étudier ; son résultat est ensuite mis en cache et réutilisé. En dehors de ces demandes,
la couverture de la carte peut progresser en tâche de fond par petits lots uniquement quand le
contrôleur dispose d'un budget d'opcodes réellement libre — par exemple lorsqu'aucun projet utile
n'est constructible faute de trésorerie — sans retarder les tâches métier prioritaires. Le scheduler
doit donc pouvoir interrompre/reprendre ce remplissage, lui imposer un budget strict par tranche et
abandonner immédiatement la cartographie de fond dès qu'un travail plus prioritaire apparaît.

La carte peut ainsi rester **partielle** pendant longtemps : les zones pertinentes pour les projets
réels seront naturellement cartographiées en premier. Aucune décision ne doit supposer que 100 % de
la carte est déjà connue ; une donnée de bloc absente signifie « à calculer si nécessaire », pas
« terrain neutre ». Le remplissage opportuniste est un bonus de temps mort, jamais une condition de
démarrage de l'IA ni un motif pour immobiliser des opcodes qui pourraient servir à une décision ou
une construction immédiatement utile.

Usages visés au-delà du remplacement de Lakes :

- **prévision économique par projet** : utiliser le corridor de blocs pour estimer plus tôt le coût
  réel probable de construction, le délai avant mise en service et donc un ROI plus réaliste que les
  facteurs fixes actuels ;
- **prévision du coût de décision** : estimer avant le pathfinding exact le nombre d'opcodes et le
  temps/ticks nécessaires pour étudier puis construire un projet, afin d'ordonner les candidats par
  valeur attendue mais aussi par coût de calcul ;
- **pré-pathfinding hiérarchique** : chercher d'abord un corridor grossier dans le graphe de blocs,
  puis limiter l'A* exact aux zones plausibles au lieu d'explorer la carte sans information globale ;
- **risque de faisabilité** : dériver un indicateur de difficulté/échec probable à partir du relief,
  de l'eau, des pentes, de la constructibilité et de la fragmentation du corridor ;
- **choix du mode de transport** : comparer rail/route/eau/air à partir de la structure physique du
  corridor avant de lancer des devis lourds pour chaque famille ;
- **implantation et extensibilité** : repérer les zones adaptées aux gares, dépôts, quais et axes
  d'approche, ainsi que la place disponible pour double voie, allongement ou branches futures ;
- **détection de régions naturelles** : agréger les blocs en plaines, massifs, bassins, îles,
  péninsules ou corridors côtiers pour améliorer la génération même des candidats.

Le **type principal** d'un bloc est seulement une vue simplifiée. La représentation doit conserver
un vecteur de caractéristiques réutilisable, par exemple `water_ratio`, `buildable_ratio`,
`height_min/max/mean`, amplitude de relief, densité de pente, bords côtiers et densité
d'infrastructure. Le typage `eau/plat/montagne/...` est dérivé de ces mesures et ne doit pas faire
perdre l'information brute nécessaire aux modèles de coût, ROI ou temps.

La carte est conceptuellement séparée en deux couches : une **couche physique** relativement stable
(eau, altitude, pente, constructibilité) et une **couche dynamique** (villes, industries,
infrastructures Opex/adverses, gares, voies, routes). Les modifications locales de carte doivent
invalider seulement les blocs concernés. La cible architecturale devient donc :
`candidat -> corridor de blocs -> prévision £ / ROI / opcodes / durée / risque -> portefeuille ->
pathfinding exact seulement pour les candidats retenus`.

Contraintes de conception :

- **aucune structure persistante à une entrée par tuile de la carte entière**, contrairement à
  Lakes ; à 2048², une grille 5×5 représente au plus ~168 100 blocs et une grille 10×10 ~42 025,
  contre 4 194 304 tuiles ;
- construction interruptible/mesurable en opcodes et mémoire, compatible avec les grandes cartes ;
- représentation indépendante de MinchinWeb, réutilisable par eau **et** analyse générale du
  terrain ;
- stratégie explicite de rafraîchissement/invalidation des blocs affectés par les modifications de
  carte, plutôt qu'une reconstruction globale aveugle ;
- migration en deux temps : valider la représentation et ses oracles, puis seulement brancher les
  consommateurs et retirer `water_lakes_connectivity`, `water_lakes_ops_budget` et le code Lakes.

Premier protocole attendu : construire les deux grilles sur 256²/512²/1024²/2048², mesurer
RAM/opcodes/temps, comparer 5×5 et 10×10, puis vérifier le typage sur un échantillon de blocs et la
connectivité eau contre un oracle BFS borné/exact. **Aucun default de jeu ou de politique n'est à
changer avant cette qualification.**

Les autres sujets restent disponibles : catchment réel des gares, placement/bruit d'aéroport,
jonctions/agrandissement de gare, `station_join`, coût A*, réglages de partie avec mode désactivé,
RAM Squirrel et automatisation GitHub. Ils remontent sur un besoin démontré, pas parce qu'une
bibliothèque propose une fonction. Le temps de trajet rail reste hors périmètre de SuperLib
(cf. C41 et `AGENTS.md`). `origin_sitable` et `complex_cargo` conservent leurs défauts ; ne pas
présenter leur conservation comme un nouveau gain mesuré.

## Règles pour la prochaine expérience

- **Une hypothèse, une intervention, une décision attendue.** Écrire le coût d'essai et le critère
  d'arrêt avant de coder. Ne pas prolonger un résultat nul en explorant des seuils jusqu'à gagner.
- Smoke 1×1, diagnostic physique **5×6**, puis **20×10 apparié avant adoption**. Pour revendiquer
  un rattrapage, le banc doit comparer les deux politiques OpexAI **face au même AAAHogEx**.
  Le 20×5 actuel est une référence descriptive, pas une exception à la règle d'adoption.
- Pré-enregistrer la métrique économique primaire, l'effet minimal utile et les garde-fous
  sur l'autre métrique économique, les échecs et le service. Publier les deltas par graine,
  moyenne et médiane appariées, incertitude et V/D/égalités. Exclure les égalités du test des
  signes ; un résultat non significatif n'est ni une preuve d'équivalence ni une adoption.
- Garder les graines d'échec dans les résultats avec leur statut. Distinguer validation d'un
  correctif fonctionnel, maintien d'un défaut et démonstration d'un gain économique.
- Exploiter les résultats déjà présents avant de lancer une campagne. Après verdict, remplacer
  la fiche active par sa décision et archiver le détail : ne pas empiler les conclusions opposées.
- Docker : toujours `--cpus=3 --memory=2g --memory-swap=2g`, cache
  `-v openttd-lab-home:/home/lab`, source montée dans `/work`. Une seule campagne consommatrice
  à la fois sur le VPS ; ces limites par conteneur ne bornent pas leur consommation cumulée.

**Portée de cette revue :** lecture du code courant et des archives, recomptage hors ligne des
JSON récents, réorganisation documentaire. Aucun changement de comportement IA, aucun défaut
modifié, aucun nouveau banc lancé. L'[architecture après C65](architecture_opexai.md) donne les
nouveaux emplacements des fonctions.


### Décision 2026-09-15 — `early_slot` adopté économiquement

`early_slot` est désormais considéré comme définitivement adopté sur le plan économique. Il ne constitue plus un chantier de validation ni une priorité de benchmark : les travaux suivants doivent partir de cette stratégie comme base retenue.

Réserve pour une évolution future : OpexAI devra à terme savoir lire la carte au démarrage et décider si `early_slot` est adapté au contexte de la partie. La décision devra probablement s'appuyer au minimum sur la liste des villes, leur population et une mesure de la densité de la carte. Cette adaptation nécessite d'abord des outils de caractérisation de carte ; elle est explicitement hors priorité pour le moment.

Priorité immédiate après cette décision : comparer OpexAI et AAAHogEx ligne par ligne sur les mêmes marchés afin de distinguer l'écart de couverture de marchés de l'écart de productivité à marché comparable.

### Diagnostic 2026-09-15 — OpexAI vs AAAHogEx sur les mêmes marchés

Comparaison terminée sur la télémétrie passive 20×10 déjà disponible, sous la politique
early_slot adoptée. Analyse :
[08_opex_vs_aaahogex_same_markets.md](08_opex_vs_aaahogex_same_markets.md).

Fait principal AIR en 1979 :

- OpexAI dessert **44,65 marchés/seed** contre **23,75** pour AAAHogEx, mais reste à
  **1,02 avion/marché** contre **3,00** ;
- sur 30 observations même paire de villes + mêmes cargos, AAA a **3,50× plus d'avions**,
  **2,47× plus de capacité**, gagne en profit sur **28/30** marchés et produit environ
  **106,5 k£/avion** contre **40,2 k£/avion** pour Opex ;
- l'âge ne suffit pas : sur 9 marchés apparus la même année chez les deux IA, AAA finit encore
  avec **3,56× plus d'avions** ;
- la ROUTE donne le signal inverse sur 108 marchés strictement comparables : Opex gagne 93/108.
  Le rail n'offre que 4 observations même cargo ; aucune priorité générale n'en découle.

**Nouvelle priorité immédiate : comprendre pourquoi _resizeAirFleets laisse presque toutes les
lignes AIR Opex à un avion.** Mesurer les refus existants (W, M, C, Y, L/S, etc.) sur le défaut
actuel early_slot, ligne par ligne, avant de modifier fleet_before_new, le buffer ou un plafond.
Le maintien de fleet_before_new=0 est commenté avec des bancs du 2026-09-02 ; ces résultats
antérieurs au 2026-09-09 ne font plus foi selon la règle du dépôt et ne ferment donc pas ce chantier.

### Diagnostic 2026-09-15 — profondeur AIR : W est un symptôme, pas le levier

Le diagnostic 5×6 early_slot montre que W (pas assez de cargo en attente pour proposer un
renfort) domine très largement les refus de _resizeAirFleets, avec pratiquement aucun refus cash.
Mais deux expériences causales ferment la piste du desserrage direct :

- air_fleet_buffer=-1 : seed 42 × 3 ans, **−167,9 k£/an** et **−19,3 % de company value** ;
- seuil expérimental à 50 % d'une capacité : **−240,2 k£/an** et **−32,3 % de value**.

Le mécanisme protège donc réellement l'allocation du capital. Forcer la profondeur de flotte
consomme le capital qui aurait servi à ouvrir des marchés rentables. Aucun balayage opportuniste de
seuil n'est poursuivi.

### Diagnostic 2026-09-15 — qualité de service AIR / STNN.goods

Extension passive terminée : chaque endpoint/cargo de ligne expose désormais rating,
time_since_pickup et max_waiting_cargo. Analyse complète :
[09_air_service_quality.md](09_air_service_quality.md).

Conclusion :

- l'hypothèse « 1 avion → mauvaise fréquence → mauvais rating → peu de cargo → W » est réfutée ;
- en 1975, Opex a un pickup **plus récent** qu'AAA (4,6 vs 10,1 jours) mais seulement
  **60,5 £ de profit/capacité** contre **322,6 £** ;
- sur 7 marchés strictement identiques en TownID+cargos, AAA a plus de profit/capacité **7/7** et
  plus de max_waiting/capacité **7/7**, alors qu'Opex a le meilleur rating sur **4/7** ;
- à **un seul avion** et dans les mêmes bandes de distance, l'écart persiste fortement.

**Nouvelle priorité immédiate : demande/catchment AIR.** Mesurer passivement le type/taille
d'aéroport, son placement dans la ville et, si disponible sans instrumentation intrusive, la
production passagers/courrier réellement couverte. Le verrou se situe en amont de W :
les stations Opex voient beaucoup moins de cargo passer, même sur les mêmes TownID.

### Expérience 2026-09-15 — renforcement AIR ciblé sur la fréquence

Une première variante comportementale minimale a été testée sans remettre en cause early_slot.
Le mécanisme autorisait, uniquement sur une ligne rentable à **1 avion**, un seul candidat de
renforcement malgré W lorsque le deuxième avion faisait franchir un palier du modèle existant
OpexPickupRatingPoints(headwayDays). Tous les caps physiques et l'arbitrage ROI restaient actifs.

Résultats complets :
[10_air_frequency_variant.md](10_air_frequency_variant.md).

Smoke seed 42 × 3 ans :

- +26,9 k£/an ;
- +2,89 % de company value ;
- sous le seuil utile pré-enregistré de +50 k£/an.

5×6 apparié :

- **−123,7 k£/an** en moyenne ;
- **0/5 victoire** ;
- company value **−7,12 %** ;
- verdict fail_primary_and_value_guard.

Le mécanisme a pourtant bien augmenté la fréquence :

- avions/ligne 1975 : **1,013 → 1,058** ;
- time_since_pickup : **5,84 → 4,51 jours** ;
- rating : **139,2 → 144,3** ;
- achats AIR C50 : **20 → 28** ;
- refus W C50 : **4 806 → 4 566**.

Mais le profit/capacité tombe de **66,3 à 53,1 £**. La piste « fréquence de collecte » est donc
**écartée**. Aucun 20×10 n'est lancé et le comportement expérimental est retiré.

**Priorité confirmée : catchment / placement AIR.** Chercher pourquoi AAA capte beaucoup plus de
passagers/courrier dans les mêmes villes, plutôt que d'augmenter artificiellement la fréquence.
early_slot reste définitivement adopté et ne doit pas être rouvert.

## Revue 2026-09-16 — clôture M1/B6

**M1 clos.** Vérité des canaux rétablie sans changement métier : vraie `company_value`
C50, VIVIER reject/retained séparés, capital du pool explicitement nommé avec compatibilité
IB/JSON, score final et capital de financement exposés honnêtement. Test M1 8/8, selftest C50 OK,
smoke 2×3 2/2.

**B6 clos sans nouveau défaut adopté.** Le 5×6 apparié
`results/review_b6_portfolio_causality_paired_5x6.json` est sain 10/10 et mesure
630/639 snapshots de capital différents du capital vivant, 50 événements
d'`affordability_flips`, 146/501 choix ratio différents du meilleur profit abordable,
592 rangs avec `turnoverBonus` non neutre et 139 choix incrémentaux recyclés, âge max
43 jours. `portfolio_floor_pct` reste 0, `PORTFOLIO_MAX_BATCH` reste 1 et
`early_slot` reste adopté. Le floor50 a déjà un 20×10 post-09/09 défavorable
(−4,94 % valeur, 4 V / 16 D) : pas de relance/adoption. **État final du 17/09 :** 06.5 est clos
non adopté après son 5×6 comportemental négatif ; 06.11 est clos comme diagnostic P3 après la
mesure de repricing détaillée plus bas ; 06.12 reste dormant.

## Revue 2026-09-16 — clôture G0

Le factoriel causal 4 bras × 5 graines × 6 ans
`results/review_g0_abandon_factorial_4arm_5x6.json` a confirmé que
`abandon_gen_filter` et `abandon_cooldown_days` sont réellement exposés. Le bras `0/0`
avait un signal diagnostic positif et a donc été promu vers l'autorité C66.4, sans adoption au
stade 5×6.

Autorité officielle :
`results/review_g0_c66_4_20x10.json`, 20 graines × 10 ans × 2 politiques, 40/40 parties
complètes. Candidat `abandon_gen_filter=0,abandon_cooldown_days=0` contre courant `1/365` :

- primaire `profit_year` : **+11 264,85 £/an** en moyenne ;
- victoires/défaites : **11/9**, `p_signes=0,823803` ;
- seuil utile pré-enregistré : **+50 000 £/an**, non atteint ;
- `company_value` : **+2,759 %** en ratio des moyennes, garde -5 % respectée ;
- verdict C66.4 : **`fail_primary`**.

Décision : **non-adoption de `0/0`**. Les défauts livrés restent
`abandon_gen_filter=1` et `abandon_cooldown_days=365`. `early_slot=1` reste la base adoptée.
Aucun `.nut` n'a été modifié pour cette décision, donc aucun smoke supplémentaire G0 n'était
nécessaire.

Bundle : `845c5b283d86c05fb3360445596e1967edde1d2cbfcd82fb19f08e7864b1dcb2`.
Manifest : `78c4ac1fe74189a119f954902b8a24242c44158bd812bc5d9a5792d4d7bb1047`.

## Revue 2026-09-17 — clôture C68 sélection avion par route

Le résidu AIR de M3/G12 a été converti en switch causal `air_route_plane_selection` : à route,
sites, type d'aéroport et demande déjà choisis identiques, l'IA compare les appareils compatibles
avec `OpexAirEconomics` et retient le meilleur `profitAnnual` (ROI en départage). Le chemin `0`
préserve la sélection catalogue historique.

Validation : smoke `results/review_c68_air_route_plane_smoke_2x3_v3.json` **4/4 sain** ; diagnostic
`results/review_c68_air_route_plane_5x6.json` **10/10 sain**, 4/5 graines positives,
**+235 565 £/an** de `profit_year` moyen. L'autorité C66.4
`results/review_c68_air_route_plane_20x10_v2.json` couvre **20 graines × 10 ans × 2 politiques**,
40/40 parties complètes : **15 V / 5 D**, `p_signes=0,041389`, delta moyen primaire
**+128 201 £/an**, supérieur au seuil +50 000 ; `company_value` **+34,206 %** en ratio des moyennes,
garde -5 % respectée ; verdict **`pass`**.

Décision : **C68 adopté**. `air_route_plane_selection=1` devient le défaut livré. La portée reste
volontairement minimale : les pré-filtres de paire et la demande éventuelle restent calculés avant
le choix C68 avec l'appareil catalogue historique.

Validation post-adoption : `results/review_c68_adopted_default_smoke_2x3.json` est **2/2 sain** ;
son manifeste publie `air_route_plane_selection=1` dans `defaults` et `effective`, sans le réglage
dans `explicit`. Le défaut adopté est donc bien celui réellement exécuté.

**Suivi à conserver malgré l'adoption :** les cinq graines perdantes sur le primaire final sont
`7`, `42`, `1337`, `12345` et `424242`. Elles doivent faire l'objet d'une analyse causale détaillée,
sans urgence mais avant de considérer C68 comme uniformément compris, car la régression peut dépendre
de propriétés de carte (géométrie/distances, distribution des villes, compatibilité des aéroports),
du calendrier d'investissement ou des pré-filtres AIR encore évalués avec l'appareil catalogue.
Le brut annuel baseline/C68/delta pour `profit_year`, `performance_history` et `company_value` est
extrait dans `results/review_c68_air_route_plane_20x10_v2_annual_metrics.csv`. La graine `7` est le
cas prioritaire : elle reste défavorable presque tout l'horizon et termine aussi en baisse de valeur ;
les quatre autres pertes de profit sont surtout tardives et doivent être comparées à la trajectoire
des choix de routes/appareils avant toute correction supplémentaire.

## Revue 2026-09-16 — clôture B9 / G4 résiduel

B9 a été traité **measurement-first** avec `air_catchment_probe=0` par défaut. Le premier
5×6 valide `results/review_b9_air_catchment_5x6.json` est sain **10/10** ; le « 0 événement »
initial venait du parseur, qui ne relisait pas les logs moteur persistés. L'analyse offline a
récupéré **148 builds / 296 endpoints** sans rejouer la campagne.

Constats causaux :

- 08.6 : le coût réel d'un arrêt joint traversant varie environ de **450 à 2 250 £/arrêt** ;
  `BT_BUS_STOP` n'est donc pas une réserve exacte. Les arrêts sont désormais optionnels avant
  chantier, puis coût réel + catchment réel sont réconciliés ;
- 08.8 : les trois `22` ont été remplacés par `TOWN_CATCHMENT_SHARE_PCT`, sans changer la
  politique de demande livrée ;
- 08.9 : le marginal joint est calculé sur l'union réelle de la station moins le catchment
  aéroport. Pré-fix : double comptage positif **50/63** endpoints, +**10,14 pax** en moyenne ;
  post-fix : `model_error_pax=0` sur **59/59** endpoints neufs ;
- 08.10 : sous `air_demand_plan=0`, le proxy population n'est plus additionné à une production
  physique. Le marginal physique n'est ajouté que dans le mode production-based.

Le placement reste un signal descriptif : dans le sous-ensemble STNN comparable du 5×6 final,
AAAHogEx est plus proche du centre (distance rectangle moyenne **6,06**, centre couvert
**37,85 %**) qu'Opex (**7,47**, **20,0 %**). La production catchment exacte d'AAAHogEx n'est
pas disponible : aucune politique de placement n'est adoptée sur ce seul constat.

Validation finale : tests B9+freeze **17/17**, selftest B9 OK, `py_compile` OK,
`git diff --check` OK hors warnings CRLF ; smoke
`results/review_b9_air_catchment_smoke_2x3_v4.json` **2/2** ; 5×6 final
`results/review_b9_air_catchment_reconciled_5x6.json` **10/10**, horizon complet,
148 builds / 296 endpoints, zéro invariant cassé.

**Pas d'adoption AIR.** `air_demand_plan=1` possède déjà une autorité 20×10 défavorable
(`results/bench_air_demand_plan_10y.json` : **−51,5 % `profit_year`**, 5/20,
`p=0,041`). Il reste 0, `air_catchment_probe` reste 0 et `early_slot=1` reste adopté.

**Décision du 2026-09-17 — conserver `air_joined_stops`, retirer les feeders.** La relecture des
logs B9 confirme que les pièces bus jointes augmentent bien l'union de couverture du `StationID`
de l'aéroport : ce ne sont pas des terminaux de correspondance nécessitant un bus. Elles captent
directement le cargo dans leur propre rayon et le rendent disponible à la station aéroportuaire.
Le mécanisme feeder expérimental a donc été supprimé du code courant, avec son réglage et ses
branches mortes. `air_joined_stops` reste inchangé fonctionnellement ; ses anciens résultats de
mesure et les anciens bancs feeder sont conservés pour traçabilité.

## Matrice de revue actuelle

| Groupe | Statut | Preuve principale | Suite / limite |
|---|---|---|---|
| H1 | fait | règle 20 paires + sign-test C66.4 | ne pas rouvrir sans régression |
| H2 technique | fait | freeze/pinning + contrat **230 settings** | G0 rendu séparément |
| H3 | fait | compteurs physiques validés | ne pas rouvrir sans régression |
| H4 | fait | santé/horizon fail-closed | ne pas rouvrir sans régression |
| H5 | fait | coût/opcodes observés branchés | mesure partielle, pas CPU total |
| G0 | fait — non adopté | 20×10 officiel `fail_primary` | garder 1/365 |
| B1 | fait | sonde AIR 771 + smoke/5×6 | clôture conservée |
| B2 | fait | diagnostic C63 corrigé + smoke/5×6 | clôture conservée |
| B3 | fait — expérimental non adopté | `review_b3_time_scaled_cap_paired_5x6_v2.json` | default inchangé |
| B4 | fait | feeder orders 6/6 + smoke | clôture conservée |
| B5 | fait | contrats état/reload + validations | clôture conservée |
| B6 | fait — 06.5 non adopté | passif 10/10 : 41/630 choix changés ; variante 5×6 : −135,5 k£/an, valeur −27,31 %, 1 V / 4 D | garder `portfolio_fresh_budget=0` ; 06.11 P3 mesuré/non adopté, refresh concurrent rejeté ; 06.12 dormant |
| B7/G11 | fait — 10.1/10.2/10.3 techniques + 10.5 mesuré | budget Lakes interruptible + distance inconnue fail-closed + connectivité fail-before-spend ; RAM/opcodes jusqu'à 2048² | scan freeze 2026/1337 inconclusif ; aucun default eau changé |
| B8 | fait | contrats rebut 7/7 + smoke ; 5×6 non exposé | ne pas prétendre preuve dynamique du rebut |
| **B9/G4 résiduel** | **fait** | 17/17 + smoke 2×3 + 5×6 10/10, marginal exact 59/59 | aucun default AIR adopté |
| M1 | fait | 8/8 + selftest + smoke 2×3 | — |
| M2 | dormant ou non exposé | flags concernés à 0 | traiter avant réactivation |
| **M3/G12** | **fait — diagnostic, non adopté** | smoke 2×3 + 5×6 **10/10**, 135 887 événements | AIR P2 exposé ; NewGRF non mesuré ; pas de 20×10 |
| M4 | fait — diagnostic + 16.2 corrigé + 16.4 mesuré | `max_trains=0` post-fix : 10/10 sains, 0 projet rail, 0 build fail, 0 £ failed spend ; Lakes ~128 B/tuile, ~14 opcodes/tuile | 16.1 non reproduit ; 16.4/10.5 clos comme mesure externe |
| C57 | abandonné | calibrage Lakes devenu sans objet | supersédé par C67 ; ne pas lancer le banc 50 000 opcodes |
| **C67** | **ouvert — conception/mesure** | grille 5×5 vs 10×10 + typage eau/relief/plat | qualifier RAM/opcodes/précision puis remplacer Lakes sans modifier les defaults avant preuve |
| M5/G2 résiduel | dormant ou non exposé | `c39_engine_refresh=0` | pas de lot autonome |
| M6 | dormant ou non exposé | pas d'exposition courante | pas de correctif autonome |
| M7/11.1 | fait | contrat 15/15/15 + 13/13 + C65 + smoke 2×3 4/4 | fallback inconnu seulement |
| M7/11.2 | fait dans le workspace courant | `_tryTownGrowth` retourne booléen utile/vide | ne pas rouvrir sans régression |
| M7/11.3 | dormant ou non exposé | branche inactive | surveiller seulement |
| M7/11.6–11.7 | fait via B5 | 11/11 + round-trips save/load | expansion active non capturée au checkpoint |
| M7/11.8 | fait / caduc | symbole obsolète absent | aucune action |
| G3 résiduel | fait | recalcul post-A* commun blocking/resumable, fret compris | aucune suite |
| 07.2 rail iterations | limite diagnostique, non P1 | proxy `state.iterations` incomplet ; `OB|A.result.opcodes` complet sur la recherche | ne pas changer le budget/pathfinder pour « corriger » un proxy |
| 21.1 | **fait** | `AIR_ROTOR=6` + test synthétique hélicoptère ; 8/8 hôte/Docker | aucune suite |
| 21.2 | **fait** | `test_campaign_freeze.py` couvre le gel complet ; 11/11 hôte, 11 tests Docker dont 1 skip Git CLI attendu | aucune suite |
| 21.3 | fait | valeur décroissante sans expansion testée fail-closed | aucune suite |

## Revue 2026-09-16 — clôture M3 / G12

M3 a été repris depuis le workspace courant sans modifier les règles de choix livrées.
`equipment_roi_probe=0` est un canal passif ; le contrat compte désormais **230 réglages**.
Il conserve les alternatives d'équipement seulement sous probe, compare la pré-sélection contre
les économies réelles avant admission et après route/site, et sépare explicitement
`native_choices`, `refit_proxy_choices` et capacité post-refit réellement relue.

Réconciliation :

- locomotive rail : déjà couplée au convoi et départagée physiquement/économiquement ;
- wagon : toujours unique par cargo sur capacité, mais aucun second wagon n'est exposé en vanilla ;
- route : 18 cas multi-choix sur 736 comparaisons, jamais de regret ni de flip ;
- feeder G12 historique : déjà corrigé via le catchment du hub réel ;
- air : appareil unique par type d'aéroport réellement limitant. La préférence de type d'aéroport
  reste une politique séparée et n'a pas été touchée.

Validation : freeze+M3+B9 **23/23**, selftests bench/diag OK, `py_compile` et
`git diff --check` OK. Smoke obligatoire
`results/review_m3_equipment_roi_smoke_2x3_v5.json` : **4/4**.
5×6 `results/review_m3_equipment_roi_5x6.json` : **10/10** et 135 887 événements.
AIR : 79 807 comparaisons multi-choix, 75 742 écarts au meilleur profit, 77 884 au meilleur ROI,
**2 371 flips d'admission** ; regret profit moyen +7 776,81 £/an.

Le catalogue sélectionne toujours l'avion 228 mais le meilleur profit varie réellement par route
(principalement 218, 217, 223). Une sélection économique par route est donc une piste P2 concrète,
pas un « remplacement statique » de moteur. Elle n'est ni implémentée ni adoptée dans ce lot :
aucun défaut P1 de mesure n'est démontré en vanilla, aucun 20×10 n'est lancé.

Le risque NewGRF reste ouvert au sens compatibilité : ce 5×6 OpenGFX n'expose aucun
`refit_proxy_choice` et toutes les capacités post-refit observées ont `capacity_delta=0`.
Il ne faut donc pas présenter ce résultat vanilla comme une validation NewGRF.

Le smoke a aussi permis de corriger le harnais : callback multiprocessing Windows sérialisable,
chemins de logs moteur injectés/créés explicitement, selftest aligné sur le champ additif
`endpoint_cargo_stats.airport`. Le contrôle CLI
`results/review_m3_harness_cli_check_1x1.json` passe.

## Revue 2026-09-16 — clôture M4 conformité NoAI

Nouveau banc ciblé : `sweeps/run_m4_conformity.py`, analyse `sweeps/diag_m4_conformity.py`,
runner hôte borné à 6 CPU / 2g / 2g avec cache persistant.

`results/review_m4_conformity_2x3.json` a servi de preuve courte ; le résultat descriptif final est
`results/review_m4_conformity_5x6.json`, complété par le contrôle
`results/review_m4_conformity_control_5x6.json`.

- **max_trains=0** : 10/10 runs sains ; Opex finalise les cinq graines avec zéro véhicule et zéro
  station facility rail, mais choisit 30 projets rail et enregistre 15 `NOTRAIN`. C63 totalise
  176 313 £ de coût rail échoué ; huit années-graines où NOTRAIN est l'unique échec totalisent
  **120 018 £**. Voie/dépôt ne sont pas comptés séparément. Le contrôle 5×6 est 10/10 ; sur ces
  cinq graines, `profit_year` moyen vaut −3,70 % et `company_value` moyenne −1,95 % face au
  contrôle, résultat descriptif sans autorité d'adoption. 16.2 est confirmé comme défaut P2 de
  gaspillage/admission. Le garde `vehicle.max_trains` est maintenant appliqué avant l'A* puis
  revalidé juste avant la première dépense. Le rerun ciblé
  `results/review_m4_162_fail_before_spend_5x6.json` donne 10/10 runs sains, zéro projet rail lancé,
  zéro `RAIL_BUILD_FAIL`, `actual_fail=0` et `pure_notrain_actual_fail=0` ;
- **pf.forbid_90_deg=1** : 10/10 runs sains, zéro erreur NoAI, 34 projets rail choisis et rail
  construit dans chaque graine (1/4/2/2/2 véhicules). L'hypothèse crash/boucle n'est pas
  reproduite sur ce périmètre ; les internals `Pathfinder.Rail` restent externes au dépôt ;
- 16.3 reste clos ; 16.4/10.5 a ensuite été mesuré par micro-banc constructeur. Les tailles
  256²/512²/1024² suivent ~128 B/tuile et ~14 opcodes/tuile ; le 2048² long 3× termine 3/3 avec
  524 788 KiB de delta RSS médian, 58 726 159 opcodes nets et 5 872 ticks. L'ancien horizon court
  était insuffisant ; aucun OOM/plafond `AIList` n'est démontré.

**Décision : M4 fait — diagnostic + mesure, non adopté.** Aucun `.nut` OpexAI comportemental n'a
changé pour 16.4, donc aucun nouveau smoke n'est requis. M7/11.1, alors identifié comme prochain lot,
est désormais traité ci-dessous.

## Revue 2026-09-16 — clôture M7 / 11.1

Le workspace contenait déjà le patch minimal M7 à reprendre/valider : dans
`ai/OpexAI/scheduler.nut`, un nom de tâche inconnu produit maintenant
`AILog.Error("Unknown scheduler task name: " + task.name)` avant la désactivation historique.
Les 15 tâches connues, leur ordre, leurs `dueCycle` et leurs handlers ne changent pas.

Contrat ajouté/renforcé :

- `sweeps/test_scheduler_task_contract.py` impose l'égalité exacte
  `_taskQueue` / cascade / handlers et l'ordre log → disable → return ;
- `sweeps/c65_pass3.py` extrait désormais la vraie file depuis `main.nut` au selftest.

Validation : tests ciblés + freeze **13/13**, C65 selftest
**14 événements / 15 tâches**, `py_compile` OK, `git diff --check` OK. Le smoke obligatoire
post-`.nut` `results/review_m7_scheduler_smoke_2x3.json` passe **4/4**, horizon complet, zéro
erreur NoAI ; les logs moteur ne contiennent aucune occurrence du fallback inconnu.

11.2 est déjà corrigé dans le workspace courant : `_tryTownGrowth` renvoie `true` uniquement
après une construction et `false` sur les gardes/échecs. 11.3 reste **dormant/non exposé** :
la mauvaise attribution éventuelle exige `town_growth_skip_noop=1` et un ledger concerné actif,
alors que les defaults restent à 0. 11.6/11.7 sont clos par B5 ; 11.8 est caduc.

**Décision : M7/11.1 fait.** Aucun réglage/default/politique n'a été modifié ; aucun 5×6 ni 20×10.

## Revue 2026-09-16 — résidus techniques après M7

Le plus gros résidu actif non gelé et hors eau a été repris de bout en bout : **B6/06.5**. Le
snapshot de capital est encore pris avant la découverte air/eau et utilisé à la sélection, mais le
diagnostic passif actuel mesure maintenant son effet exact :
`results/review_b6_065_live_budget_5x6.json`, 10/10 parties saines, **41/630** élections changées
par le capital vivant ; 39/41 ont un profit local supérieur, médiane +17 322 £/an.

Le candidat comportemental existant `portfolio_fresh_budget=1` a ensuite été testé sans nouveau
code de politique : `results/review_b6_065_fresh_budget_c66_4_5x6.json`, 5/5 paires complètes.
Il perd **−135 528,6 £/an** de `profit_year` en moyenne, V/D/E **1/4/0**, et **−27,307 %** de
`company_value` en ratio des moyennes. Ce 5×6 est `diagnostic_only`, mais son signal négatif suffit
à **ne pas promouvoir** le candidat en 20×10. `portfolio_fresh_budget` reste 0 et 06.5 est clos
comme candidat non adopté. Le smoke final post-instrumentation
`results/review_b6_065_final_smoke_2x3.json` passe **2/2**.

**Étape intermédiaire 06.11, supersédée par la mesure de clôture ci-dessous.** Le premier banc
n'établissait encore que 139/345 choix incrémentaux recyclés, âge moyen 14,36 j, max 43 j. Le refresh
comportemental concurrent avait été audité puis retiré parce qu'il supprimait les subventions et
extensions routières du vivier alors que l'incrémental ne les régénère pas. Le contre-factuel frais
équivalent a depuis été ajouté en mesure passive et clôt 06.11 sans adopter ce refresh. **06.12**
reste dormant.

Deux résidus documentaires ont aussi été soldés :

- G3 : blocking et resumable rail appellent le même recalcul post-A* ; `candidate.kind` fait que
  le fret suit exactement ce chemin ;
- étape 21 : 21.1 possède maintenant le cas synthétique hélicoptère tête+ombre+rotor ;
  21.2 couvre le cœur fail-closed **et** la copie complète campagne/bibliothèques via un faux
  BaNaNaS sans réseau ; 21.3 possède les cas de valeur décroissante. Les trois reliquats sont clos.

**07.2** a aussi été requalifié sur les consommateurs actuels. Les sondes pont/tunnel ne sont
toujours pas ajoutées à `state.iterations`, mais ce proxy n'est plus consommé par le classement
vivant ni par `OpexAvailableCapital`. Le coût H5 du rail vient de `OB|A.result.opcodes`, dont les
`budget.begin/end` englobent les sondes de structure en mode bloquant comme reprenable. Ajouter
ces sondes au compteur d'itérations modifierait simultanément les bornes de recherche ; ce ne
serait pas une correction de mesure neutre. Aucun patch P1.

## Revue 2026-09-17 — preuves et résidus techniques

Les JSON cités par la revue sont archivés sous `evidence/review/` en gzip déterministe avec index
des SHA256 brut/gzip ; `results/` reste un scratch ignoré. Le test d'intégrité vérifie que chaque
référence de revue est couverte et se décompresse exactement vers son JSON source.

Les derniers résidus neutres ont été corrigés sans nouvelle politique : reset de `passDiscards`
rail après flush, `EU|` visible en refleet-only, bit IG renommé `selection_not_exact` côté parseur
et compteur `n_vehicles` du banc 3 ans aligné sur H3. Le smoke final
`results/review_final_residuals_smoke_2x3.json` est sain ; B7/10.1 et 10.3 sont également clos.

**B6/06.11 est désormais mesuré de bout en bout, sans refresh adopté.** Le diagnostic Docker 5×6
`results/review_b6_0611_join_resolved_5x6.json` est sain 10/10. Sur 348 sélections incrémentales,
136 choisissent un top recyclé (âge moyen 15,74 j, max 44). Le rail pax comparable au rebuild frais
montre une erreur absolue moyenne de 608,59 £/an (max 6 969) mais un biais signé faible (+51,54).
Sur 127 tops fret recyclés, 117 sont repricés exactement ; 17 changent de profit et, parmi 114 cas
décidables, **6 changeraient réellement l'élection** (4 inversions de rang, 2 non-générés) contre
108 choix inchangés ; 5 égalités et 8 cas hors oracle restent non tranchés. Le refresh concurrent
qui supprimait subventions/extensions reste rejeté. **Décision : 06.11 clos comme diagnostic P3,
correctif général non adopté ; `portfolio_cache` reste actif, aucun 20×10.** À cette date, les
autres restes étaient architecture/mesure (C67), politique (M3 AIR) ou cosmétique/inert (21.1).
Le reliquat 21.1 a depuis été clos le 2026-09-20.

Le smoke Docker final post-`.nut` `results/review_b6_0611_final_smoke_2x3_v2.json` est sain **2/2**
sur 42/100, avec horizons complets pour OpexAI et AAAHogEx et les réglages de référence conservés.

## Revue 2026-09-17 — relecture du regroupement des sondes (`probe_*`)

Voir [`docs/walkthrough_regroupement_probes.md`](walkthrough_regroupement_probes.md) §5 pour le
détail. Deux problèmes trouvés et corrigés dans le même chantier : 17 scripts `sweeps/*.py`
(dont les trois runners de banc) qui passaient encore les 70 anciens noms de sonde, et une garde
`C41_WATER_PRECHECK` perdue sur les sondes eau (`probe_catalogue=1` sans précontrôle exécutait
réellement `OpexWaterPlans()` au lieu de rester passif). Les deux sont réglés ; reste ouvert :

- **Découplage `c41_water_refresh` / `probe_catalogue`** : `scheduler_tasks.nut:318` fait dépendre
  le refresh fonctionnel du catalogue eau de `C41_REVISION_PROBE`, qui n'est plus accessible seul —
  il faut désormais `probe_catalogue=1`, ce qui allume au passage les 6 autres sondes catalogue.
  Couplage préexistant au regroupement, élargi par lui. Pas un correctif de sûreté ; à traiter
  comme une tâche de conception (séparer le fonctionnel du diagnostic) si `c41_water_refresh` doit
  un jour s'activer indépendamment.

## Revue 2026-09-17 — regroupement des politiques et suppression des pistes abandonnées

Voir [`docs/walkthrough_regroupement_parametres.md`](walkthrough_regroupement_parametres.md) pour le compte rendu détaillé du chantier.

Suite logique du regroupement des sondes :
- **66 pistes formellement abandonnées / rejetées retirées de `info.nut`** et figées à `false`/neutre dans `settings.nut` (pas de régression ni de code cassé).
- **~60 réglages adoptés regroupés en 8 macro-politiques `policy_*`** (`policy_caches`, `policy_feeders`, `policy_rail`, `policy_road`, `policy_air`, `policy_abandon`, `policy_portfolio`, `policy_vehicle_events`).
- **`air_early_slot` basculé à 1 par défaut** dans `info.nut` (alignement sur la décision du 2026-09-15).
- Surface exposée de `info.nut` réduite de **169 à 44 paramètres** (-1870 lignes nettes).
- 119 tests unitaires passés ; équivalence bit-à-bit vérifiée par smoke test Docker.

