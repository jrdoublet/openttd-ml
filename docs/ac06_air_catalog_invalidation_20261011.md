# AC-06 — événements, durée de vie C78 et Save/Load (11/10/2026)

**Verdict : audit de cycle de vie terminé, pas de correctif adopté.**
L'invalidation ou le changement de mois pendant un scan C78 **ne détruit pas
son curseur** ; la publication partielle n'est pas une fin de génération ;
Save/Load abandonne intentionnellement le scan non sérialisable et provoque
une régénération complète. En revanche, un **risque causal distinct
d'acquittement prématuré C76** est établi au niveau des transitions de code :
des révisions survenues *après* la photographie du catalogue peuvent être
acquittées à la fin du scan, alors qu'elles n'ont pas été prises en compte.
Ce dernier risque n'est **pas** une perte économique mesurée en jeu et ne
justifie pas un changement de défaut sans qualification.

## Qualification postérieure : correctif AC06 rejeté pour opcode

La correction isolée `ac06_c76_snapshot_ack=1` capture les révisions
au début du scan et évite l'acquittement des événements arrivés après.
Les quatre tests de transitions et le Save/Load moteur OFF/ON sur la
graine 512 (2+1 ans, marqueur `LOAD_RECONCILE`, aucune erreur moteur)
passent. **Limite :** le rechargement ne démontre pas un événement C76
survenu précisément entre le refresh et l'apply.

La non-régression économique B20×10 reste indécidable :
−78 982 £/an, IC95 [−192 524 ; +25 994] ; le 40×4 de confirmation
donne −11 283 £/an, IC95 [−39 173 ; +9 427]. Aucune perte économique
statistiquement démontrée. Mais les opcodes globaux instrumentés montrent
un coût **systématique** : 38/40 parties augmentent sur 1970–1971,
médiane **+451 opcodes**, signe exact p=1,49×10⁻⁹ ; 25 paires affichent
exactement +451. Sur 1970–1972, 34/40 augmentent, médiane +451,
p=8,36×10⁻⁶, bien que les fortes divergences de quelques graines
rendent la moyenne −95 314 et son IC95 compatible avec zéro.

**Verdict : REJET** selon le critère utilisateur d'absence de toute
dégradation démontrée (aucun gain ni seuil d'acceptation requis). Conserver
le risque logique identifié, le correctif expérimental OFF et ses
preuves dans le worktree ; **ne pas intégrer dans master**.
Voir [l'étude de validation](air_catalogue_validation_finale_20261011.md).

## 1. Chemins réels et priorité

Sources : `ai/OpexAI/scheduler_tasks.nut:15–457`,
`main.nut:772–794`, `scheduler.nut:263–322`,
`orchestrator.nut:1069–1178`, `events.nut:40–60`,
`persist.nut:730–925,1127–1129`.

| Événement/état | Scan C78 actif | Sans scan C78 actif |
|---|---|---|
| Nouveau mois | **Poursuite du même `s.cursor`** ; l'horodatage `s.ym` reste celui du démarrage | Test `_lastCatalogMonth == ym`, puis branche C76 ou régénération/sélection selon les gardes |
| Franchissement de capital | Pas de reselect par la garde de fraîcheur tant que le scan existe ; les publications et les projets courants peuvent employer la trésorerie vivante | `stale` déterminé par franchissement du prochain capital connu sous AIR_EFFICIENCY_RESELECT, sinon par gain minimal ET doublement ; reselect isolée uniquement pour le réglage qui l'autorise |
| Construction / nouvelle ligne | `_c76BumpLayer("lines")` peut incrémenter les révisions ; **pas de destruction du curseur actif** ; revalidation des plans à l'exécution | C76 détecte `_c76AnyLayerChanged`, choix entre mode, full et autres chemins |
| Fondation de ville / industrie ouverte ou fermée / moteur disponible | C76 incrémente respectivement `towns`, `industries` ou `engines.<mode>` ; le scan en cours poursuit son ancien catalogue | Ces couches déterminent le besoin de régénération selon dépendances et cadence |
| `_portfolioInvalidated=true` pendant scan | Si un lot a déjà été publié, `_dispatchCatalog` efface ce booléen au prochain passage ; une publication partielle l'efface aussi | Invalidation empêche la garde « frais » et demande regeneration/refresh |
| Tranche inachevée avec nouveaux plans | `partialPending=true` ; **le passage suivant publie**, ne consomme pas une tranche supplémentaire et conserve phase/cursor | — |
| Fin de la phase primaire AIR_ONLY sans plans | **Fallback interne** : `phase=fallback`, band AIR_RAIL, nouveau cursor ; ce n'est pas une nouvelle tâche C78 | — |
| Fin du dernier scan | `phase=apply`, puis publication finale/rebuild, acquittement C76 si full, mise à jour `_lastCatalogMonth=s.ym`, suppression de `task.c78AirRebuild` | La prochaine tâche peut repartir, notamment si `ym` courant diffère |
| Save/Load pendant scan | **Curseur abandonné volontairement** : `Save()` n'enregistre ni `c78AirRebuild` ni les plans avec flottants | `Load()` restaure dates/révisions ; `_reconcileAfterLoad()` impose `_c76ForceReloadRegen=true` si C76, puis reconstruction de catalogue |

Le gestionnaire `_dispatchCatalog` donne priorité absolue au curseur actif
(`:248–265`) **avant** la garde `stale`, cadence mensuelle, révisions C76,
capital et chargement (`:267–323`). Il est donc erroné de conclure qu'un
événement ou un mois nouveau « relance le scan » : la tâche reste la même
tant que le curseur est présent.

Le moteur ne réexécute pas indéfiniment dans un seul tick : `OpexC121CatalogCanContinue`
exige absence de worker, de railSearch et de railExpansion, même tick
et budget disponible strictement supérieur à 2 000 opcodes
(`scheduler_tasks.nut:7–13`, `main.nut:772–794`). La file conserve
son alternance entre les tâches. Sans portefeuille initial,
`OpexC78RequeueInitialCatalogSlice` remet temporairement `catalog` en tête
pour ne pas bloquer les autres travaux de construction.

**Save/Load n'est pas une reprise de curseur identique** et ne doit pas être
présenté comme tel. Dans les formats court et complet, les dates et la
comptabilité C76 sont sauvegardées ; aucune instance de `task.c78AirRebuild`
ni son tableau de plans n'est enregistrée. Après chargement, le constructeur
repart sans portefeuille publié ; la réconciliation C76 force la
reconstruction. Ce comportement est documenté dès
`docs/22_c78_lignes_vs_aaa.md:267–270`.

## 2. Défaut logique possible : acquitter des révisions arrivées trop tard

Ce cas est plus précis qu'un redémarrage inutile :

1. `_dispatchCatalog` appelle `_catalog.refresh` puis crée
   `task.c78AirRebuild` (jusqu'à `:399–404`). Les révisions C76 actuelles
   **ne sont pas photographiées dans ce curseur**.
2. Le calcul est suspendu. Avant sa fin, un événement appelle
   `_c76BumpLayer`, par exemple `town_founded` ⇒ `towns++`
   (`events.nut:40–51`) ou un chantier appelle `lines++`. Le catalogue
   photographié à l'étape 1 peut ne pas contenir cet événement.
3. Le scan continue sans nouvelle `_catalog.refresh` ; en particulier
   `task.c78AirRebuild` n'est pas recréé. Les publications peuvent effacer
   `_portfolioInvalidated`.
4. À `phase=apply`, **`owner._c76AcknowledgeAllLayers()`**
   (`scheduler_tasks.nut:171–175`) recopie **toutes les révisions
   *actuelles*** dans les révisions acquittées
   (`orchestrator.nut:1149–1176`), y compris les événements survenus en 2.
   La phase fixe aussi `_c76LastRegenQuarter` à la valeur de départ et
   désarme `_c76ForceReloadRegen`.
5. Si aucun autre mécanisme n'a traité l'événement, `_c76AnyLayerChanged()`
   rend faux jusqu'à une révision suivante ou à la cadence périodique.
   Pendant le même mois, la garde de fraîcheur peut empêcher une nouvelle
   régénération.

**Conclusion établie statiquement :** l'acquittement est fait au dernier état,
pas à l'état couvert par le catalogue. La fixture AC-06 reproduit
`revision > ack` après événement, puis `revision == ack` après apply, sans
refresh dans cet intervalle. **Ce n'est pas une preuve qu'une occasion rentable
a été perdue sur une carte réelle** : C77 peut effectuer une génération
réactive, un autre événement peut survenir, ou la cadence suivante peut
rattraper l'état.

Une correction envisageable devrait conserver la photographie des révisions
au lancement, puis acquitter uniquement celles réellement couvertes et
différer une nouvelle régénération si des révisions ultérieures existent.
Mais cela change le nombre et la temporalité des scans et potentiellement la
sélection économique. **Aucun correctif de production ni toggle créé en AC-06** :
il faut d'abord mesurer l'exposition en partie (révisions de départ/fin par
couche, couverture C77, date de rafraîchissement, sélection divergente),
puis tester une hypothèse unique OFF/ON au protocole économique et opcode.
Ne pas relancer V143 `annual_refresh`, déjà réfuté : ce n'est pas le même
mécanisme.

## 3. Tests AC-06 et limites

Fixture : `sweeps/test_ac06_catalog_lifecycle.py`, **8 tests**.
Elle associe des vérifications textuelles sur les fonctions réelles à un modèle
de transitions déterministe. Scénarios :

- scan actif + changement de mois + événement + publication partielle ;
- transitions `primary → fallback → apply` ;
- publication intermédiaire et finale, conservation du même curseur ;
- événements successifs pendant plusieurs tranches ;
- acquittement tardif C76 (reproduction négative, par construction) ;
- Save/Load qui jette le curseur transitoire, préserve C76 et force regen ;
- garde de reprise dans le même tick, worker et moteur rail actifs.

`python -X utf8 -m unittest -q sweeps.test_ac06_catalog_lifecycle
sweeps.test_r4_catalog_continuation
sweeps.test_c78_air_candidate_hygiene
sweeps.test_air0310_1_incremental_publish
sweeps.test_air0310_2_hub_snapshot`
⇒ **37/37 tests verts** ; `git diff --check` vert.

**Limites :** le modèle Python ne lance pas le Squirrel NoAI, ne reproduit pas
les réactions C77 concurrentes et ne mesure ni la fréquence des événements
pendant la génération, ni l'impact sur les finances ni les opcodes. Les tests
du code réel vérifient les affectations et leur ordre, sans prétendre un
smoke Save/Load du moteur. Le banc C121 100×3 concurrent n'a pas été
perturbé par une campagne AC-06.

**Décision : clôturer l'audit AC-06, ouvrir séparément la qualification
causale « C76 late-ack pendant C78 » ; laisser intacts les réglages, les
curseurs, le refresh annuel V143 rejeté et toutes les publications V141.**
Pas de commit/push.
