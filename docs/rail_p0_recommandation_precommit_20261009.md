# P0 RAIL — Proposition suivante : réadmission au financement avant chantier

Statut au 09/10/2026 : **proposition technique, aucun changement de comportement ni qualification économique**. L'objectif reste de faire concourir lignes neuves, renforts et autres investissements sous le même classement ; il n'est pas de chercher un nouveau seuil 500/200, un coefficient de rotation ou une valeur de cap A*.

## Ce que les résultats établissent

Les trois expériences isolées du rapport [rail_magic_filter_p0_20261009.md](rail_magic_filter_p0_20261009.md) échouent en porte A V102 : lot combiné −31 949 £/an, admission seule +8 256 £/an (non significatif, sous seuil), A* sans borne de ratio −864 £/an (37/40 profits inchangés). Le tri TOP20 RAIL ne sert pas au portefeuille normal : `projects.nut` y soumet `rail.candidates` en entier. L'idée d'ouvrir le vivier ou de donner simplement davantage d'itérations n'a donc pas montré de gain.

L'autopsie des checkpoints des bancs 40×3 indique un **effet indirect précoce** : dans le lot combiné, les 40 premières divergences de caisse surviennent d'avril à juillet 1970, avant tout train ; en admission seule, les premières divergences de profit touchent 35/40 graines dès mai–août 1970, et 39/40 graines divergent ensuite en flotte AIR. Sous A* seul, 1970–1971 sont identiques et seulement trois graines changent le `profit_year` terminal en 1972. **Ces différences de cadence et d'achat AIR ne permettent pas d'attribuer le `profit_year` aux nouveaux rails**, d'autant que les 80 fichiers engine de chaque porte A sont vides (logs désactivés). Les mesures sont néanmoins de vrais duels appariés de politique sur un bundle figé.

Une mesure 5×6 sur un **autre bundle**, observationnelle et intrusive, situe une perte plus concrète en 1972–1975 : `_railSearch` est unique, et toute nouvelle primaire est refusée avec `search_in_progress` pendant une recherche primaire/upgrade en cours (`task_rail.nut:202–263`). La recherche de doublement COAL seed999 du 16/07/1972 au 05/03/1975 a occupé le créneau **962 jours** pour `ABND` à 10 000 itérations ; une primaire GOOD démarrée plus tard a abouti en **125 itérations / un jour**. Ces trajectoires ne démontrent pas que la primaire aurait été constructible ou rentable à la date antérieure. Le prototype N=2 conditionnel déjà rejeté (−60 078 £/an porte A) a dépensé 14,6 M opcodes sur quatre recherches B ensuite jetées : **ne pas le reprendre comme première solution**.

Une cohorte diagnostique supplémentaire de recherches primaires exposées contient **34 START : 24 `OK`, 6 `ABND`, 4 censures**. Parmi les 24 `OK` : **13 constructions**, **10 refus de pose**, **1 attente de caisse**. Ce sont des **fréquences descriptives de projets déjà choisis**, et non des probabilités transportables aux candidats jamais recherchés. De même, 518 visites de fret concurrent bloqué correspondent à 64 OD uniques, dont seulement trois paires sont associées ultérieurement à une construction dans leur partie ; l'absence de construction ultérieure ne démontre pas l'impossibilité de la paire.

## Défaut structurel plus précis

La sélection intermodale est faite en `projects_selection.nut:1144–1470` : capital finançable, profit C70, `fundScore` utilisant C69 `max(financeCapital, K_dec)`, tier C77, rangs territoriaux C118/C120 et bonus AIR early. Cependant, quand un A* primaire finit plusieurs mois plus tard, `task_projects.nut:1707–1719` appelle **`_consumeResumableRailAtPassStart` avant la boucle sur le meilleur portefeuille courant**. Ce chemin appelle directement `_consumeRailSearch` (`:1409–1422`), qui vérifie notamment la caisse et la pose, mais pas une nouvelle admission économique du projet face aux AIR/RAIL/fleet maintenant mieux placés. C77 ne reporte l'A* prêt qu'**une passe** via `c77DefensiveDeferred` (`:1676–1701`). Une opportunité classée à la date de lancement A* peut donc débiter le capital à une date où le classement a changé.

Autre écart documenté : `_expandRailLines` (`task_rail.nut:733–925`) peut engager un second train ou lancer un upgrade en fonction du seul `lastProfit>0`, d'un instantané de backlog et de la caisse. Ces dépenses sont **hors du TOP64 intermodal**, et un A* upgrade peut bloquer le même créneau plusieurs saisons. `trackCost+trainCost` y est un devis de financement, **pas** un devis de profit marginal de l'investissement supplémentaire. Une ligne existante rentable ne garantit pas un doublement rentable.

## Intervention recommandée, en deux portes causales

### A. Réadmission des projets RAIL *prêts* avant dépense (priorité 1)

1. En phase A* terminée, identifier le projet avec **`OpexProjectAttemptKey` complet**, sa génération et son devis. Lire/recalculer au besoin le **même** portefeuille courant que le sélecteur normal, en respectant les règles C69/C70/C77/C118/C120. Ne pas comparer seulement un `ratio` ou le score brut des deux projets.
2. Si le projet RAIL prêt est effectivement le premier **investissement encore admissible et payable**, lancer sa revalidation de site, capital et véhicules, puis poser. S'il a été évincé par un projet AIR/fleet/route/eau admissible devant lui, **laisser ce projet concurrent tenter la construction en premier** ; si l'alternative échoue, passer au rang suivant dans la même logique de portefeuille.
3. Une préparation ne doit plus monopoliser indéfiniment `_railSearch` après avoir perdu l'admission. Garer le tracé **comme état préparé, non financé**, avec OD/cargo, date/epoch du devis et vérification de géométrie ; libérer le créneau pour un autre A*. Au retour d'admission, valider la carte, la caisse et la capacité ; si le tracé a expiré, replanifier selon le chemin normal. Ne jamais présumer qu'un `OK` A* garantit une pose : `STNFAIL`/`TRKFAIL` surviennent après la recherche.
4. Pour le Load, les pathfinders sont actuellement non sérialisables : conserver explicitement le contrat de reconstruction/invalidation des préparations, sans prétendre restaurer une recherche A* suspendue. Garder `N=1`, `V89`, les plafonds A* et les modèles de recettes inchangés.

La propriété vérifiable est **zéro dépense de chantier RAIL dont l'identité est absente d'une décision intermodale fraîche**, et **zéro saut injustifié d'un projet finançable mieux classé**. Cette correction vise la cohérence de sélection et non un gain économique affirmé d'avance.

### B. Devis marginal des seconds trains et upgrades (priorité 2)

Publier les renforts comme projets explicites au même portefeuille, avec `lineId`, version des installations, `profitAnnual` **incrémental** (`recettes réellement supplémentaires - charges supplémentaires - amortissement des nouveaux actifs`) et `financeCapital` (`voie/quais/dépôt + train + réserve, cohérent avec les autres projets`). Les observations de `task_report.nut` incluent `lastRevenue` et `lastWaitingA/B`; elles ne suffisent pas encore à inférer de façon fiable le trafic supplémentaire servi par un second train. Un devis inconnu doit rester **inconnu**, sans assimilation de `lastProfit` de la ligne existante au profit marginal du renfort. Mesurer le cargo réellement transporté, son rythme d'arrivée et les coûts avant d'admettre un upgrade au classement.

Le **temps de monopolisation A*** est une ressource supplémentaire à comptabiliser, en **jours de créneau** (et opcodes VM en métrique distincte), à partir des débuts/fins RID observés par type et de l'état courant. Pour comparer deux opérations, estimer le profit marginal retardé `profitAnnual / 365 × jours` uniquement pour une alternative réellement exposée. Les probabilités de réussir A* puis de construire doivent être calibrées sur des cohortes comparables ; les données actuelles sont trop rares pour fixer un seuil de réussite ou un prix £/opcode. Ne pas convertir les 10 000 itérations en une limite arbitraire de jours.

## Mesure la moins intrusive avant le prototype

Ajouter **sous une sonde existante OFF** un événement unique `RAIL_READY_ADMISSION` à la frontière `task_projects.nut:1707` : date, identité OD/cargo, RID, âge et itérations de l'A* prêt, `rank` courant (ou absent), `fundScore` existant, capital et caisse disponibles, `head_mode`/`head_rank`/`head_score`, tiers C77 et raison de la comparaison. Lire des champs **déjà calculés**, sans nouveau scan carte, recalcul de revenus ni A* ; distinguer *rang qui devance RAIL* d'un concurrent qui a effectivement construit, et enregistrer les cas censurés. Instrumenter de même l'initiation des upgrades avec `lineId`, backlog, revenu de la ligne, devis voie+train, head courant et résultat RID→pose. Dédupliquer par RID/projet/année, jamais par compte de visites de sélection.

Critère préalable à toute politique : trouver au moins quelques cas **réels** où un chantier RAIL prêt aurait payé avant un projet supérieur, ou où un upgrade monopolise le slot pendant une primaire financée qui n'est pas une revisite, puis établir coûts et constructibilité avec des états clonés pré-engagement. Une comparaison d'un score papier à AIR n'est pas une telle preuve.

Une fois la correction isolée sous réglage OFF par défaut : tests Squirrel/Save-Load et smoke 1×1 ; porte A **40 graines ×3 ans** V102 `gain_short` (Wilcoxon p<0,05 ; IC95 bootstrap bas>0 ; gain >=4 % du témoin et garde valeur −5 %) ; porte B **20 graines ×10 ans** `non_erosion` **uniquement** si A passe. La première porte sous-expose potentiellement le 1973–1975 : si ce mécanisme est principalement tardif, définir **un horizon diagnostique distinct à l'avance**, jamais après avoir vu le résultat.

## Décision

**Ne pas introduire de nouvelle politique ni modifier le défaut sur la seule étude statique.** La première livraison utile est la preuve transactionnelle de réadmission à la pose. Si elle expose effectivement un contournement coûteux, c'est le plus petit correctif à qualifier. La migration des upgrades au portefeuille commun est ensuite un chantier indépendant, avec modèle de gain marginal à établir. Aucun changement de revenus AIR, de demande RAIL ni de prix de construction ne découle de cette proposition.

## Exécution engagée — sonde OFF par défaut

La sonde `rail_ready_admission_shadow` est déclarée dans
`globals_pre.nut`, `info.nut` et `settings.nut`, avec **0 dans les
quatre difficultés**. Aucun comportement du portefeuille, aucune pose,
aucune admission économique n'est modifié par cette sonde.

- `task_projects.nut::_railReadyAdmissionShadow` lit uniquement le TOP64
  courant, le capital disponible et l'état primaire A* `phase=build`.
  `RAIL_READY_ADMISSION phase=before` expose `startTick` de la recherche,
  son âge et ses itérations, OD/cargo, rang/score/capital de l'ancien candidat,
  premier candidat maintenant rentable/payable, tier C77 et report. Le même
  `startTick` apparaît dans `phase=after` après la tentative de pose, avec
  `built=0/1`. Une visite reportée par C77 peut précéder une visite
  réellement consommée : **ne jamais les additionner comme des chantiers**.
- `task_rail.nut` émet `RAIL_READY_UPGRADE phase=start` seulement lorsqu'un
  devis et des quais de doublement ont permis de démarrer A*. Il relève
  `lineId`, backlog, revenu/profit historique, coût estimé voie+train,
  trésorerie et tête du portefeuille. `phase=end` donne issue de la pose,
  durée/itérations, refus ou coût déclaré ; **pas** un gain marginal du second train.
- `sweeps/analyse_rail_ready_admission.py` agrège par
  (`policy`, `seed`, `repeat`, `searchTick`) et sépare visites,
  recherches uniques, constructions, projets absents du TOP64,
  première alternative finançable, reports C77 et upgrades. La mesure
  `higher_rank_eligible` est explicitement *une priorité théorique*
  qui **ne prouve ni la pose possible ni le bénéfice d'une autre ligne**.
- `sweeps/test_rail_ready_admission_shadow.py` (3 tests) et
  `sweeps/test_analyse_rail_ready_admission.py` (2 tests) vérifient
  defaults, séparation comportementale et déduplication. Les cinq tests hôte
  sont verts.

Smoke apparié `rail_ready_shadow_smoke_42x1_20261009_r1` **INVALIDE** :
`OpexLoadSettings` levait une erreur NoAI dans les deux bras sur deux
globales ROAD expérimentales lues mais absentes :
`ROAD_FINANCE_UNBIAS_P0`, `ROAD_FINANCE_GATE_SHADOW_P0`.
Elles ont été déclarées **false** dans `globals_pre.nut`, sans changer la
politique ROAD au défaut. Smoke neuf
`rail_ready_shadow_smoke_42x1_20261009_r2` : 2/2 parties saines,
delta `profit_year` OFF/ON = **0**, valeur identique, verdict
`diagnostic_only`, bundle
`085f63c749b8ecc7f7943becf513c78c53450e3f624633eceb00e1a6f28b06e3`.
Ce smoke année 1970 ne prouve pas que les branches `phase=build` et
`upgrade` ont été exécutées en moteur.

La campagne 5 graines ×6 ans `rail_ready_shadow_obs_5x6_20261009_r1`
avait été **interrompue dès le lancement** à la découverte d'un
autre conteneur déjà actif sur le Docker partagé. Ne pas la déclarer
complète ou utiliser son bundle à la place d'une exécution. Les prochains
résultats demandent **un nouveau nom de campagne**, un Docker libre et un
bundle figé après l'ajout du log `UPGRADE phase=end`.

**Statut de validation** : instrument diagnostique et tests hôte livrés,
aucun résultat long permettant une décision économique, aucun correctif
comportemental ni nouveau défaut adopté ; aucun commit/push.
