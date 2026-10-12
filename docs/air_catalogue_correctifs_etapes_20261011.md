# Catalogue AIR — correctifs AC-04/05/06 découpés, staging et portes (11/10/2026)

**ÉTAT FINAL POSTÉRIEUR À CE PLAN :** les huit audits AC01–AC08 sont clos.
Après les qualifications appariées isolées, le **cumul AC04-B + AC05**
a passé son économie 20 graines × 10 ans (profit +59 835 £/an,
IC95 [−75 536 ; +192 620]) et son contrôle opcode global VM 10×4
(−230 118 opcodes, IC95 [−897 523 ; +276 929]). Les deux changements
ont été **intégrés sans commit dans `master`**, réglages par défaut 1 et
retour possible à 0 ; 124 tests passent et le smoke Docker 42×1 est sain.
Les correctifs **AC04-A et AC06 v1 sont rejetés pour opcode** ; les
alternatives optimisées AC04-A v2 et AC06 v2/v3, réalisées à la demande
sur index, redondances et filtres Squirrel/AIList, ont aussi été rejetées
après tests VM. Le défaut late-ack et la saturation orpheline demeurent
connus, sans code non qualifié livré. Détails, limites et provenance :
[validation finale](air_catalogue_validation_finale_20261011.md) et
[autopsie/optimisations](ac_opcode_optimisation_20261011.md).
**Tout le plan qui suit est conservé comme pré-enregistrement historique
avant essais ; ses statuts « aucun banc » et ses anciens seuils de gain ne
sont plus l'état présent ni les critères de décision. Aucun commit/push.**

## RECTIFICATIF utilisateur — critère unique « aucune régression »

**Dernière décision explicite de l'utilisateur : aucun AC ne vise un gain
économique ou en opcodes. Seule une dégradation établie en économie ou en
opcodes entraîne le rejet.** Un gain éventuel est admis, sans être une
condition d'adoption. Cette règle remplace toutes les demandes de *gain
positif* présentes plus bas dans ce plan ancien (notamment V102
`gain_short`, delta moyen ≥4 %, poste opcode devant baisser), et vaut
**pour AC04-A, AC04-B, AC05, AC06 et l'instrumentation AC07/AC08**.

- **Économie :** comparaison appariée ON−OFF ; rejet si perte prouvée au
  `profit_year` (IC95 bootstrap entièrement négatif / règle
  `non_erosion`) ou garde de valeur du protocole rompue. Des graines
  divergentes, un intervalle traversant zéro et un `fail_primary` sous
  l'ancienne porte de gain ne sont **pas** des preuves de régression.
- **Opcodes :** rejet sur hausse établie de consommation à instrumentation
  **comparable** et pertinente. Les compteurs H5 du banc n'enregistrent
  qu'une **partie** des opcodes et leurs échantillons peuvent différer
  quand les décisions changent ; ne pas conclure au CPU total sans
  couverture ni décomposition. Une économie d'opcodes n'est **pas**
  recherchée ni obligatoire, y compris pour AC05.
- **Suite :** les anciens 40×3 sont conservés comme diagnostics ; porte
  `non_erosion` 20×10 (sans gain minimum) pour les candidats encore
  ouverts ; Save/Load pour AC06 ; interprétation prudente du coût opcode.
  **Aucun correctif par défaut sur une seule preuve économique incomplète.**

Les paragraphes d'étapes historiques restés formulés en « gain » plus bas
ne constituent plus le contrat d'acceptation : appliquer exclusivement
le présent rectificatif, de priorité ultérieure.

## Statut exact, sans assimilation « codé » à « adopté »

**Quatre variantes correctives sont implémentées dans un worktree Git isolé,
toutes à défaut 0.** Elles ont passé **73 tests ciblés Python/statiques**,
mais **aucun smoke OpenTTD, Save/Load moteur ou A/B économique/opcode de la
variante n'a encore été lancé**. Elles ne sont donc ni adoptées ni intégrées
à `master`. La campagne concurrente
`first-observation-100x3-20261011-r1` a terminé pendant la préparation.
Une tentative de smoke 1×1 sur cinq bras (référence et chacun des quatre
toggles ON isolément) a ensuite été **bloquée par l'environnement
avant exécution** : aucun conteneur ni résultat de ce smoke n'a été créé.
Ce blocage n'est ni un échec moteur ni un passage de porte.

| Ressource | Valeur |
|---|---|
| Worktree | `results/ac_fixes_worktree_20261011/` (exclu de `git status` du parent par `.gitignore`) |
| Branche | `air-catalogue-fixes-staging` |
| Base figée | commit `436e1b5` (master au démarrage de cette préparation) |
| Fichiers de production touchés **dans le worktree seulement** | `ai/OpexAI/air_planning.nut`, `globals_pre.nut`, `settings.nut`, `info.nut`, `scheduler_tasks.nut`, `orchestrator.nut` |
| Tests | `sweeps/test_ac_catalogue_fixes.py` (7 tests) ; `sweeps/test_air0310_2_hub_snapshot.py` : contrat statique adapté aux deux nouveaux gardes |
| Défauts de tous les nouveaux réglages | **0 / OFF** : référence V141, AIR0310 et C76 inchangée |
| Publication | **aucun commit, push, cherry-pick ou changement de défaut** |

Une **archive vérifiable de récupération** (patch Git, fixture non suivie,
SHA256) est conservée dans
[`evidence/review/air_catalogue_correctifs_20261011/`](../evidence/review/air_catalogue_correctifs_20261011/README.md).

Ne pas fusionner tous les changements en un unique A/B : le même patch de
staging possède quatre leviers de comportement **indépendants**, dont un
correctif de comptabilité C76 et un pré-calcul inerte sous C121. Pour chaque
qualification, **l'ensemble des autres nouveaux réglages reste explicitement
à 0** dans les deux bras ; conserver tous les défauts historiques communs.

## Ordre de travail et frontière de chaque essai

### Étape 0 — validation préliminaire, déjà réalisée

Audit statique AC-01 à AC-08, comparaison du `HEAD`, historique des rejets
V142/V143, des contraintes V141 et du contrat C76. Sauvegarde des artefacts
et maintien du `master` intact. Création du staging séparé ; contrats source
et modèles de transitions. **73 tests ciblés verts, diff --check vert.**
La campagne C121 concurrente est terminée, mais la tentative de smoke
Docker a été bloquée avant lancement ; la validation Squirrel reste
nécessaire. Pour la reprendre, utiliser le banc
`sweeps/bench_v2.py` du worktree isolé avec les cinq bras
`OpexAI`, `OpexAI[ac04_hub_route_fix=1]`,
`OpexAI[ac04_extra_site_dedup=1]`,
`OpexAI[ac05_skip_unused_hub_income=1]` et
`OpexAI[ac06_c76_snapshot_ack=1]`, graine 42, un an,
trois workers maximum pour ce smoke. Cela ne constitue pas une
mesure de neutralité économique ni une exposition réelle.

### Étape 1 — AC04-A, faux hub « orphelin » saturé

- Réglage `ac04_hub_route_fix` (défaut 0) ; un seul comportement : dans le
  parcours des aéroports non encore reconnus comme hubs, lire
  `OpexAir0310CountStationRoutes(ctx, st)` (index O(1) si disponible, sinon
  balayage existant des lignes), **refuser `routes >= maxRoutes`**, conserver
  le compte réel des stations actives admises et rafraîchir ce compte à
  la reprise du snapshot. Un vrai orphelin à zéro ligne reste inchangé.
  Sous le correctif, la reprise recalcule aussi les routes d'un ancien
  orphelin si des lignes apparaissent **pendant** le scan.
- Invariants : plafond d'aéroport, identité `stationId`, ordre des hubs
  non saturés, réutilisation des vrais orphelins, cohérence snapshot
  `air0310HubOrphan` et garde builder. Déterminisme OFF sans changement.
- **Mesure d'exposition** préalable : compter les stations saturées qui
  rentraient comme orphelines, le nombre de paires AIR évaluées depuis
  ces stations, celles admises/refusées en aval et leur coût opcode.
  Sans exposition réelle, verdict sans adoption.
- Si la correction affecte la sélection : smoke Docker 1×1, vérification
  décisions/opcodes, puis portes comportementales V102 : A **40×3
  `gain_short`** et, seulement si elle passe, B **20×10
  `non_erosion`** ; garde valeur −5 %. Aucun critère réduit improvisé.

### Étape 2 — AC04-B, même site ajouté plusieurs fois

- Réglage `ac04_extra_site_dedup` (défaut 0), sans activer AC04-A.
  Après `OpexAirFindSite` dans le supplément hub, ignorer seulement
  une **ancre physique déjà présente** dans `sites`. Une nouvelle ancre
  **dans la même ville** reste valide, notamment second slot C83.
- Invariants : `hubProbes`/budget conservés, exclusion V93/C83 conservée,
  liste par ordre de découverte (pas de tri), limitation à 12 **sites
  distincts** ; si le doublon libère une place, des villes suivantes
  peuvent désormais entrer, donc **sélection potentiellement changée**.
- Mesure : doublons exacts `(town,anchor)` par combo/site, coût des
  recherches qui les produisent, couples physiques hub→site en trop et
  nombre de sites supplémentaires découverts. Smoke et V102 A/B séparés
  comme à l'étape 1 si exposition/décisions modifiées.

### Étape 3 — AC06, révisions C76 acquittées après refresh

- Réglage `ac06_c76_snapshot_ack` (défaut 0), tous les AC04 à 0.
  `OpexC78StartCatalogAirRebuild` capture les révisions C76 au début
  (après le refresh). Lors du `phase=apply`, le helper
  `OpexAC06AcknowledgeSnapshot` n'acquitte **pas plus** que ce snapshot,
  respecte les révisions déjà consommées par C77/modes ciblés,
  et met à jour `_c76ModeConsumedRevision`. La voie synchrone C76,
  les émissions intermédiaires V141 et le scheduler restent inchangés.
- Scénarios d'exécution obligatoires : événement entre refresh et première
  tranche, en cours de tranche, avant `apply`, publication intermédiaire,
  multiples couches/modes, C77 concurrent, passage de mois, absence
  d'événement, rechargement **Save/Load au milieu du scan**.
  Un événement tardif doit rester `_c76AnyLayerChanged=true` puis être
  couvert par une génération ultérieure : surveiller redémarrage en boucle
  et double publication. Une étude VM du `_c76ModeConsumed` réel est requise.
- Mesurer le **nombre de scans supplémentaires** et les opcodes totaux,
  pas seulement l'absence de late-ack. La correction a une conséquence
  économique possible et nécessite ses propres portes V102 A/B.

### Étape 4 — AC05, pré-calcul V86 inutile sous C121

- Réglage `ac05_skip_unused_hub_income` (défaut 0), tous les autres AC à 0.
  N'exécuter le pré-calcul de `hubAvgIncome` que si sa valeur peut être lue
  par la branche d'ajustement V86 :
  `AIR_HUBHUB_MARGINAL && !C121_AIR_ECONOMICS`. Le **choix de route et
  l'économie C121 ne changent pas intentionnellement** ; sous C121 OFF,
  le comportement V86 reste strictement identique.
- Vérifier par tests VM que les projets, leurs clés, ordre, scores, décisions,
  et la sélection finale sont identiques OFF/ON à état gelé.
  Mesurer **les opcodes du pré-calcul** et les opcodes globaux, avec et
  sans beaucoup de hubs et de reprises, pas seulement une différence
  agrégée `hub_hub`.
- Règle spécifique d'optimisation opcodes du dépôt : après smoke,
  **20×10 apparié sain**, gain opcode du poste et absence de défaite
  significative sur le profit, intervalle non entièrement négatif et
  garde valeur −5 %. Aucune exigence de gain V102 de 4 % pour un
  changement opcode seulement, tant qu'une réelle neutralité décisionnelle
  est montrée ; sinon passer en V102 comportemental.

### Étape 5 — instrumentation AC07/AC08 (pas un correctif d'anomalie)

Les audits ont conclu à **dénominateurs manquants**, pas à des bugs.
Sur une campagne diagnostique indépendante, mesurer au **même tick** :
`pub.filter`, `pub.partition`, `pub.insert`, `pub.recount`,
`pub.select`, nombre de projets existants/neufs, et
`catalog.refresh.air` via les sondes **existantes**
`PROBE_SPAN_TRACE`/`CATALOG_COST_ACTIVE`. Ventiler les appels C77
et les refreshs complets ; ne pas extrapoler un coût par paire depuis
les invocations de phase. Si coûts faibles, **clore sans optimisation**.
Ne pas rouvrir V142, V143 ni la frontière C85 rejetée/non adoptée.

### Étape 6 — intégration uniquement après les verdicts isolés

Si plusieurs correctifs passent **chacun** leurs portes, vérifier ensuite
leur interaction (AC04-A/B dans le même vivier, AC06 vs V141/Save-Load,
AC05 vs C121). Garder une copie OFF/ON de chaque changement et
pré-enregistrer le protocole du cumul avant de l'essayer ; **ne pas
attribuer la validation isolée au cumul**. Nettoyage des toggles
expérimentaux, conservation des preuves, puis commit/push seulement
sur demande ou autorisation explicite.

## Critères transversaux, statut de remise

1. **Sécurité d'exécution :** une seule campagne Docker à la fois.
   PC local jusqu'à **10 CPU/10 workers, 8 Go** selon `AGENTS.md` ;
   VPS 3 CPU/3 workers, 2 Go. Bundle figé et hashé, résultats nommés
   de façon unique, aucun écrasement.
2. **Référence contrôlée :** flags AC=0/0/0/0. Une seule variante AC=1
   par essai ; même version, graines, adversaire AAAHogEx et paramètres
   historisés dans les deux bras. La neutralité opcodes exige des
   traces à charge comparable, y compris coûts du scheduler et des
   régénérations induites.
3. **Portes économiques :** comportement = V102 A 40×3 (Wilcoxon exact
   p<0,05, IC95 bootstrap borne basse positive, delta moyen ≥4 %
   du profit de référence, valeur ≥−5 %), puis B 20×10
   non-érosion/valeur selon `AGENTS.md §4`. Optimisation pure opcode =
   mesure du poste + règle opcodes 20×10 explicitée à §4. Un smoke
   ou une fixture synthétique ne vaut pas preuve de passage.
4. **Arrêt documenté :** aucune exposition → ne pas multiplier les
   campagnes ; perte économique, coût global opcode en hausse ou
   cas Save/Load non sûr → conserver le défaut 0, archiver la preuve,
   rejeter/retravailler **la seule étape fautive**.

**Livraison présente :** code correctif prêt à tester dans le worktree
isolé, flags OFF, tests statiques verts ; **pas** de mise en production.
La procédure de qualification est pré-enregistrée ici, mais aucune
campagne ou automatisation future n'est programmée par ce document.
