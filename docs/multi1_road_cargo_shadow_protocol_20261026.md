# MULTI-1 — protocole préalable SHADOW du deuxième cargo ROUTE (26 octobre 2026)

**Pré-enregistrement du diagnostic uniquement — aucun levier économique ON.**
Base documentaire : `842e15b8`, avant instrumentation. Ce protocole
observe un marché supplémentaire que le générateur courant pourrait ignorer
sur la carte 256² ; il ne change ni l'algorithme de sélection, ni les
constructions, ni la difficulté, ni les trois critères historiques de
MULTI-1. Les portes A 40×5 et B 20×10 restent interdites tant qu'un
levier ON distinct et physiquement exposable n'a pas reçu son propre
pré-enregistrement.

## Hypothèse et conditions de déclenchement

Le générateur ROAD standard reçoit **un seul** `freightCargo` depuis
RAIL (`projects_generation.nut:75-85`, `projects.nut:303-307`).
La reconstruction PO-01c utilise également ce cargo
(`po01c_regen.nut:52-55,89-101`). Le défaut
`v276_cand_slices=3` est résolu à **0** sur 256² :
V276, qui énumère déjà tous les cargos ROAD sur de plus grandes cartes,
doit être **exclu** de cette sonde.

Déclencher uniquement en multimodal AIR+RAIL+ROUTE, **1971–1973**, avec
`ROAD_BUILD_ENABLED`, `V276_CAND_SLICES == 0`, lorsqu'aucun candidat
ROAD ordinaire du lot n'est **finançable** au moment du relevé.
Une seule observation par mois civil au plus ; viser le cargo actif
qui suit `freightCargo` dans `OpexFreightCargoOrder`, à condition
qu'un moteur ROUTE existe. Aucun inventaire global non borné, aucune
publication d'un nouveau candidat.

## Tranche d'observation et plafond

- Échantillon déterministe mensuel : **au plus deux producteurs** du
  deuxième cargo, **quatre accepteurs industriels et quatre villes**
  par producteur, soit au plus **16 couples** soumis aux filtres et au
  calcul économique par observation ; l'index de départ tourne avec le
  mois civil pour éviter de sonder toujours les mêmes entreprises.
- Distinguer production positive, véhicule compatible, destinataire
  acceptant, origine/destination déjà desservies, distance admissible,
  paire abandonnée, bénéfice prédit positif, coût avec marge
  `OpexProjectFinanceCapital`, trésorerie mobilisable et doublons
  `(mode,cargo,src,dst)`.
- Parmi les candidats économiquement et financièrement admissibles,
  examiner **au plus trois plans physiques** (`OpexRoadPlanFor`,
  véritable devis géométrique en `AITestMode` ; aucun
  `OpexBuildRoadRoute`). Journaliser `SITEA`, `SITEB`,
  `TRACEX`, `DEPOTX` ou `OK`, et le profit recalculé lorsque la
  distance de route réelle est disponible. Vérifier que l'appel de plan
  n'altère ni l'état du constructeur, ni les sélections courantes.
- Limiter le diagnostic à une tranche reprise d'environ **40 000
  opcodes** et ne pas initier un nouvel examen physique après
  **200 000 opcodes** sur une observation. Ces chiffres sont des
  **plafonds de travail souples** : un unique appel à
  `OpexRoadPlanForActive` n'est pas préemptible et peut les dépasser.
  Pour revendiquer une borne dure, il faudrait ajouter des points de
  reprise au planificateur ; en leur absence, publier le dépassement et
  censurer le reliquat sans conclure qu'il n'existe aucune route.

La sonde est **OFF par défaut (0)** aux quatre difficultés. Son mode
actif est strictement SHADOW (1), avec sorties dédiées. Elle n'ajoute
rien à `all`, `candidateGroups`, `generated.projects`,
`s.outputs`, `_projects` ni aux tâches de construction. L'état de
coroutine est transitoire : au Load, annuler et repartir d'une
photographie fraîche ; dédoublonner dans le rapport les répétitions
du même mois/monde/cargo/couple après chargement. Les logs doivent
exposer `trigger`, `cargo`, compte de couples uniques examinés,
`economic`, `financeable`, `physically_planable`, causes de
refus, `plan_ops`, `total_ops`, `censored` et profit annuel
**prédit**, jamais le faire passer pour un profit réellement encaissé.

## Vérifications et statut de la décision

Contrats : OFF identité des décisions et des chemins principaux sous
`probes=0/2/256`, ON sans mutation de projet, borne d'échantillon,
unicité, filtres de cash et de desserte, passage des ticks, interruption
sur budget, Save/Load au milieu d'une tranche. Suite complète
`python -X utf8 -m unittest discover -s sweeps -p "test_*.py"`,
`git diff --check`, smoke 1×1, puis **diagnostic 5 graines ×
5 ans** (42, 100, 7, 999, 2026), sources figées et journaux moteur
(`probes=258`) vérifiés, un seul Docker et au plus 10 workers.

On n'autorisera le **pré-enregistrement d'un quatrième levier ON**
que si le rapport identifie des plans distincts physiquement réussis
et financeables sur plusieurs mondes, avec un **potentiel marginal
quantifié** suffisamment important pour rendre plausible le seuil
de porte A **+4 %** déjà fixé. L'absence de résultats sur un
échantillon **censuré** n'est pas un `NO-GO` économique général.
Une réussite en `AITestMode` n'est pas une ligne effectivement bâtie :
le levier ON devra encore prouver une construction associée après
exposition 5×5, puis passer A et éventuellement B.

À la publication de ce texte, **aucun code de la sonde ni aucune
campagne supplémentaire** n'ont été exécutés. MULTI-1 reste ouvert,
les trois `NO-GO_NON_EXPOSE` sont définitifs et les défauts inchangés.
