# V303 — Sonde inverse RAIL reprenable, pré-enregistrement (26 octobre 2026)

## Hypothèse et frontière expérimentale

Branche `v303_reverse_probe_sliced_20261026`, worktree
`results/v303_reverse_probe_sliced_stage_20261026`, base `7996efc0`.
Aujourd'hui `OpexV294fReverseProbe` exécute synchroniquement un
`FindPath(300)` **avant** le trajet aller. V303 doit répartir **la même sonde
inverse de 300 itérations** sur des tranches de 50, en réutilisant le
pathfinder existant jusqu'à son terme, puis réutiliser **le même créneau C80**
pour l'aller seulement si l'inverse échoue. Il n'ajoute aucun site, candidat,
mode de transport, force de recherche, budget financier ou moteur de train.

Archive de calibration déjà disponible (`docs/taches.md`, V303) : 1 388
sondes inverses historiques sur 40 parties, 440 chemins trouvés, 870 sondes
ayant atteint les 300 itérations ; les autres événements ne justifient aucun
gain causal. Ce sont des occurrences, non des constructions distinctes.
Ne pas relancer V307n (inverse mode 6), V280, V294c, RLW ni P1 rejetés.

## Modes et conditions d'arrêt

- `v303_reverse_probe_sliced=0` : **OFF exact**. Même appel historique
  `OpexV294fReverseProbe`, mêmes données, logs et sélection ; défaut **0** dans
  easy, medium, hard et custom, sans adoption implicite.
- `=1` : **SHADOW strictement passif** : utiliser exclusivement les journaux
  existants `V294F_PROBE`, sans allouer un second pathfinder, `AITestMode`,
  écrire de cache, varier le budget ni modifier l'état C80, la décision ou le
  séquencement. La collecte de traces est une campagne diagnostic séparée.
- `=2` : **ON borné**. Un pathfinder inverse au plus, initialisé une fois ;
  au plus `min(50, 300 - consumed)` itérations par tranche (six tranches
  maximum), avec `LastConsumed` **par appel**, ajouté à un cumul C80. Interdiction d'initialiser l'aller
  tant que l'inverse vit. Si inverse `OK`, retourner les mêmes tuiles inversées
  et devis physique ; sinon libérer le pathfinder inverse avant de créer
  l'aller via les mêmes plans/poids/budget que OFF. Pas de second A* ou de
  nouvelle validation de sites. `null` de chemin et `false` en continuation
  restent distincts ; une erreur ou un état périmé échoue ouvert vers l'aller,
  sans réutiliser de chemin incomplet.

La sonde conserve un plafond **strict** de 300 itérations pour l'inverse,
`PATH_CHUNK=50`, `RAIL_SEARCH_SLICE=50`, recherche aller inchangée,
`HARD_ITERATION_CAP`, garde des opcodes du budget d'exécution actuel. Les
statistiques distinguent itérations de sonde inverse et itérations de l'aller :
ne jamais créditer deux fois ni annuler une dépense consommée ; comparer les
ticks et opcodes réels sur les mêmes graines. Le code doit prouver qu'un
`FindPath(50)` reprend la frontière précédente et ne crée pas un nouveau
chemin de manière implicite. Faute de contrat fiable, **NO-GO technique avant
code** ou retrait de l'implémentation, sans banc économique.

L'état C80 est strictement transitoire (`this._railSearch`), sans nouveau
champ `Save`. Après `Load`, abandonner l'inverse vivant et reconstruire
normalement le prochain candidat selon l'invalidation historique ; jamais
sauvegarder les objets `pathfinder`. Durée maximale calendaire de sonde
**ajoutée par V303** de 180 jours (ce n'est pas une borne déjà prouvée de
V294f), sinon repli aller sain. La garde existante
`RAIL_SEARCH_SAFETY_TICKS=54020` reste aussi applicable : aucune conversion
de ce délai en opcodes garantis n'est revendiquée. Pas de mutation des autres tâches, du
stock rail, du classement C77/K_dec, des dépenses ou des paramètres V252.

## Preuves exigées avant qualification

Tests hôtes OFF exact, SHADOW passif, six tranches au maximum, cap cumulé,
absence de pathfinder concurrent, équivalence du chemin trouvé à la version
bloquante à monde figé, arrêt sur `null`/`false`, traçabilité et intégration
avec les états `primary`/`rail_stock`/`upgrade`, Save/Load technique.
Puis suite complète, `git diff --check`, smoke moteur OFF/ON **1 graine ×
1 an** et Save/Load court/complet sans erreur script. Le test Python seul ne
prouve pas que Squirrel compile ou qu'un chemin est identique.

Exposition appariée **5 graines × 5 ans** (42,100,7,999,2026), 1970–1974,
diagnostic-only : établir sur **au moins trois mondes** des sondes inverses
effectivement coupées en plusieurs tranches ; rattacher
`V303_REVERSE` → `PROJECT_CHOSEN` → `RAIL_ATTEMPT` → `RAIL_BUILD` avec
`(cargo,src,dst)` et les opcodes/ticks des deux phases. Le taux de succès
physique ne doit pas se dégrader sans cause explicite. Pour rendre le
changement potentiellement rémunérateur, montrer **au moins deux mondes** où
un projet supplémentaires est effectivement **construit** grâce au créneau
libéré ou à une différence d'ordonnancement prouvée, avec somme des marges
nettes des seules lignes attribuables ≥ **4 %** de la somme des profits
terminaux du témoin. Une simple différence de ticks ou de logs ne prouve pas
le gain économique. Sinon **NO-GO exposition** et défaut 0 conservé.

**Catégorie fixée avant résultats : comportement/ordonnancement, pas optimisation
pure d'opcodes (§4).** V303 exécute au maximum les mêmes 300 itérations et
augmente potentiellement le nombre d'appels `FindPath` ; aucune économie
d'opcodes n'est postulée. L'intérêt hypothétique est de redistribuer les
ticks de la sonde pour rendre le scheduler moins bloquant et permettre
d'autres projets physiques. En conséquence, l'adoption ne repose **pas** sur
la règle d'optimisation d'opcodes seule ; la porte A de gain pré-enregistrée
ci-dessous est conservée, sans recalage a posteriori. Mesurer les opcodes
réels reste un diagnostic de coût/neutralité.

Porte **A 40 graines × 5 ans**, multimodale, `gain_short`, 40 paires/80
parties, profit moyen terminal ON−OFF ≥4 % du profit moyen OFF, Wilcoxon
bilatéral p<0,05, IC95 bootstrap (20 000, graine 0) borne basse >0,
ratio des moyennes `company_value` ≥0,95 et 40/40 paires saines.
Porte **B 20 graines × 10 ans**, `non_erosion`, 20 paires/40 parties,
seulement après A réussi, IC95 borne haute ≥0, ratio de valeur ≥0,95,
20/20 saines. Aucun paramètre adopté par défaut sans décision explicite.
