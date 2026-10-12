# AC04-A — relance causale sans réhabiliter une variante rejetée

**Statut final ultérieur :** AC04-A v3 a été adoptée avec
`ac04_hub_usage_gate=1` par défaut, rollback 0, après
une porte A40×4 de gain et une porte B20×10 de non-érosion
avec amélioration globale des opcodes. Voir
[le verdict AC04-A v3](ac04a_v3_adoption_20261012.md).
Les étapes ci-dessous conservent la chronologie de la
préparation expérimentale (v3 initialement à 0).

Date : **12 octobre 2026**. Pistes proposées pour débloquer l'anomalie
« aéroport saturé réintroduit comme orphelin ».
Ce document consigne une **analyse de code et de preuves existantes** :
aucun patch AC04-A, A/B Docker, nouveau défaut ou nouvelle décision
d'adoption n'en découle.

## Expérimentation v3 isolée, ouverte le 12/10

Une **nouvelle** variante `ac04_hub_usage_gate=1` a été codée
au point d'usage des hubs, avec `0` par défaut. Elle ne change
ni `DiscoverHubs`, ni la taille des listes/snapshots, ni les
indices de reprise ; elle rectifie uniquement les hubs conservés
avec `routes=0` avant les bras `HubToSite` et `HubToHub`.
Le comptage reprend la capacité exacte du batch builder, avec
`hubIndex.routes` par défaut, ou le helper existant sans C80.
L'ancienne variante v1/v2 n'est pas réactivée.

**Contrôle déjà obtenu :** 15 tests hôtes ciblés verts et smoke
Squirrel Docker sur graine 42 × 1 an ON sain, sans assertion
d'amélioration économique. Ce statut ne change pas le rejet antérieur.

**Porte A terminée (12/10, source gelée) :** campagne
`ac04v3_usage_A40x4_20261012_r1`, 40/40 paires et 80/80 parties
saines, verdict `gain_short=pass`. Profit annuel terminal
ON−OFF moyen **+90 736,9 £/an** (27V/13D), Wilcoxon
`p=0,00758`, IC95 bootstrap **[+29 527,8 ; +150 402,1]**,
seuil préenregistré **+76 172,7 £/an**, valeur +4,165 %.
Attention : malgré le réglage commun `probe_loop_ops=1`, cette
campagne avait été lancée **sans** `--script-debug` ; ses
80 fichiers engine log sont vides. Un parseur retournant
un delta nul sur ces journaux **ne prouve strictement rien**
sur les opcodes. La preuve économique reste valide ;
prévoir une campagne VM distincte avec `--script-debug`.

**Porte B préenregistrée avant lancement :** conserver
le même code, les réglages `ac04_hub_usage_gate=0/1`
et `probe_loop_ops=1`, les autres défauts du master,
un horizon de **10 ans**, critère `non_erosion`
et garde valeur −5 %, 20 graines indépendantes du A.
Graines tirées par `random.Random(20261012).randrange(2**31)`,
les doublons ou membres des 40 graines A étant ignorés :
`1746464918 33934613 216632973 6110703 185273592
294736331 955972638 1691483264 215716649 733559510
987534985 1000703872 320742773 1356252196 1878794266
492256521 548748579 357268034 1472475944 1186980962`.
Utiliser **`--script-debug`** pour conserver les compteurs
`LOOP_OPS` de chaque année clôturée : différence moyenne
exécutée, signes, IC95 et décomposition par poste,
sans assimiler les économies d'AIR aux opcodes globaux.

**Protocole v3 préenregistré avant duel :** un A/B gelé
sur **40 graines × 4 ans**, pour capturer le profit terminal 1973
où les anciennes preuves AC04-A mesuraient déjà l'exposition,
plutôt que de choisir l'horizon après les résultats de v3.
Seuil économique `gain_short` V102 (Wilcoxon p<0,05,
IC95 bootstrap moyen bas >0, gain moyen ≥4 % du profit
de référence, garde de valeur −5 %), avec
`--required-years 4`. Deux bras `ac04_hub_usage_gate=0/1`
et `probe_loop_ops=1` commun, toutes autres options aux
défauts de master et même bundle figé. Fenêtres opcode
1970–1971 et 1970–1972 séparées, et horizon économique
1973. La dérogation utilisateur du 12/10 autorise désormais
**une faible augmentation globale d'opcodes en échange d'un
gain économique** : comme *borne de travail proposée*
(et non décision chiffrée de l'utilisateur), examiner un
ratio moyen exécuté ≤+1 % en 1970–1972, sans masquer un
surcoût systématique précoce. La seule moyenne ne suffit
pas à attribuer le mécanisme, d'où la fixture VM et
l'autopsie obligatoires. Si A démontre un gain, une
porte B **20×10** `non_erosion` avec de nouvelles graines
doit confirmer l'absence d'érosion à long terme ;
aucune adoption en défaut 1 avant cette vérification.

## Faits établis

- Dans `OpexAirPlansDiscoverHubs` (`air_planning.nut`, vers
  1300–1377), la première passe omet `seenStations.rawset`
  quand `routeCount >= maxRoutes`. La seconde passe
  `AIStationList(STATION_AIRPORT)` réintroduit cette même gare avec
  `routes=0`. Le défaut existe dans le HEAD actif.
- `OpexAir0310RefreshHubRoutes` saute les hubs marqués
  `orphan` (`air_planning.nut`, vers 1065–1073). La validation
  `OpexAir0310RestoredHubUsable` teste alors la capacité via
  `hub.routes` (`vers 1076–1086`). La voie
  `OpexAir0310SkipRestoredPair` ne vérifie la capacité que si
  `ctx.air0310HubRestored` est vrai ; elle ne protège **pas**
  l'évaluation initiale après découverte.
- `OpexAirBatchPlanStillLive` appelle la garde physique
  `OpexAirBatchHubHasCapacity` avant chantier
  (`task_air.nut`, vers 551–618). Celle-ci compte *toutes*
  les lignes AIR conservées, y compris `deadStreak >= 2`.
  Aucune construction supplémentaire sur hub saturé n'est
  démontrée ; en revanche, un faux hub libre peut générer,
  valoriser et classer des paires, éventuellement devant des
  projets valides et des projets **RAIL**.
- L'index C80 `hubIndex.routes` (`air_planning.nut`, vers
  314–329) compte lui aussi toutes les lignes AIR, sans filtre
  `deadStreak`, alors que la **première boucle de découverte**
  ignore les lignes à `deadStreak >= 2`. La simple présence
  dans cet index ne signifie donc pas « découvert par une
  ligne active ». `AIStationList` est déjà une AIList native.

## Lecture des cinq pistes

1. **Coût intrinsèque vs trajectoire — prioritaire comme attribution.**
   Dans l'A40×3 existante, 24/40 graines ont le même nombre de
   `rail_attempt` et leur delta moyen sur ce poste est
   **−2 724 opcodes** ; les 16 autres portent **+6,676 M**
   en moyenne sur ce poste (contribution globale +2,669 M).
   AC04-A v2 conserve **+307 376 opcodes** en 1970–1971,
   IC95 [+92 855 ; +609 554], malgré l'élimination du
   recomptage. Ces faits **suggèrent** une causalité
   comportementale, mais ne mesurent pas le coût par appel.
   Réaliser d'abord une fixture **dans la VM Squirrel réelle**
   sur jeux d'entrées identiques : cas zéro ligne, hub libre,
   saturé, orphelin vrai, lignes mortes, C80 OFF/ON, snapshot
   restauré/non restauré ; répétitions avec alternance de l'ordre
   A/B et soustraction de l'enveloppe de mesure. Ne pas
   confondre cette mesure VM à état fixe avec Python ou H5.

2. **Corriger à la lecture / validation snapshot — candidat à
   étudier, pas solution isolée suffisante.** Ajouter un accès
   O(1) à `hubIndex.routes[station]` lorsqu'un
   `hub.routes==0` est restauré paraît peu coûteux
   avec C80=1, mais **ne touche pas à la première génération**
   où le faux orphelin est créé. Un correctif complet doit
   également couvrir l'usage non restauré au classement
   hub→site/hub→hub, sans reboucler sur les lignes et sans
   invalider les indices `hubSiteI/J`, `hubHubI/J`.
   La politique C80=0 nécessite un repli exact, à évaluer
   séparément. Ne pas confondre la validation du snapshot
   avec la validation de constructibilité en fin de batch.

3. **Orphelin défini par `hubIndex.routes` — ambiguïté
   sémantique à lever avant code.** `station in
   hubIndex.routes` indique une extrémité de ligne AIR
   enregistrée, **pas** forcément une ligne vivante au sens
   de la découverte. Un hub avec seulement des lignes
   `deadStreak >= 2` est absent de la première boucle, mais
   présent dans l'index et dans le compteur de capacité
   de construction. Séparer dans les fixtures
   `historicalRoutes`, `liveDiscoveryRoutes` et
   `batchCapacityRoutes`. Un seul `rawin` est insuffisant
   pour les assimiler.

4. **Exposition passive — première étape de preuve matérielle.**
   Pour chaque scan et combo, distinguer :
   `falseOrphanStations` uniques, reprises depuis snapshot,
   `hubsite/hubhub` paires visitées, paires filtrées avant
   devis, devis économiques effectivement payés, projets
   admis, présence en TopN/Top64 et projets sélectionnés.
   Relier par graine, StationID/OD, type de combo, année et
   rang à `batch_plan_dead` ou à l'éviction d'un
   candidat valide (AIR/RAIL). Le nombre brut de faux hubs
   **ne suffit pas** à conclure à l'absence de matérialité.
   Une sonde est une perturbation possible en Squirrel :
   OFF totalement inerte, puis A/A avec instrumentation
   symétrique et budget de log borné.

5. **Intégration future dans CD-00/CD-03 — utile pour les
   invariants, non pour contourner le rejet.** Formaliser
   dans CD-00 les états `saturé`, `libre`,
   `orphelin`, `non admissible` et leurs dimensions
   de capacité (routes historiques / vivantes) ; CD-03
   pourrait porter cet état sans recompter à chaque reprise.
   Toutefois, aucun changement AC04-A ne peut être
   « caché » dans une refactorisation CD : test et verdict
   **propres à AC04-A** restent nécessaires.

## Ordre de travail et portes de décision

**AC04-P0 — lecture seule :** exploiter tous les fichiers de
résultats existants pour décomposer, à graines identiques, la
variation de `rail_attempt`, de la sélection et des fenêtres
VM ; distinguer `nombre d'appels × coût par appel` de
`nouveau travail déclenché`. La valeur citée de bruit
« ±290 k£ par graine » demande sa référence de campagne :
elle ne vaut pas borne de neutralité tant que protocole,
définition et distribution ne sont pas retrouvés.

**AC04-P1 — fixture VM à état identique :** comparer
historique OFF, v1, v2 et un éventuel accès direct ciblé
sur les mêmes listes de lignes/stations. Instrumenter la
génération, le refresh snapshot et la revalidation,
avec coût par appel et variance, plutôt que les seuls
opcodes globaux d'une partie.

**AC04-P2 — exposition avant comportement :** sonde passive
et contre-factuel hors ligne sur le vivier, en distinguant
pair évaluée, projet admis, rang et sélection. Si
inexposition démontrée, clore la priorité pratique sans
prétendre que le bug n'existe pas. Si exposition
matérielle, isoler le premier impact.

**AC04-P3 — une seule variante causale :** seulement après
P1/P2, retenir soit un correctif au point d'usage couvrant
première découverte et restauration, soit l'invariant CD-03
dans un lot isolé. Ne pas relancer v1/v2 inchangées.
Exiger tests des lignes mortes, C80 OFF/ON, tous types
d'aéroports, V93/C83, curseurs, V141, Save/Load et classement.

**AC04-P4 — portes moteur :** smoke Squirrel puis A/B
apparié avec profit, valeur et `LOOP_OPS` globaux,
fenêtres 1970–1971 et 1970–1972 **distinctes**, mêmes
options et mêmes graines. Une fixture intrinsèque
neutre **ne supprime pas** une régression globale
mesurée : les critères économiques et opcode
restent indépendants sauf nouvelle dérogation
explicite. En particulier, l'ancien A40×3 AC04-A
n'avait pas établi le gain V102 (+6 354 £/an, IC95
traversant zéro), malgré un bénéfice à quatre ans
sur un autre horizon. Reclasser automatiquement
AC04-A sous V102 ne prouverait donc pas son adoption.

**Décision actuelle :** AC04-A non adopté, ses résultats
v1/v2 et bundles sont conservés. Prochaine action
pertinente : **P0 puis P1**, suivis de P2 si le coût
intrinsèque ne suffit pas à trancher ; aucun nouveau
banc global coûteux avant hypothèse prouvable.

Sources : [audit AC04](ac04_air_hub_site_resume_audit_20261011.md),
[qualification A/B](air_catalogue_validation_finale_20261011.md),
[autopsie opcode](ac_opcode_optimisation_20261011.md),
[reliquat CD](air_catalogue_reliquat_decoupage_20261012.md).
