# MULTI-1 — pré-enregistrement du deuxième levier AIR/RAIL, 26 octobre 2026

**Statut : pré-enregistré avant tout code, smoke ou résultat ON.** Dépôt
`/openttd-ml`, branche `master`, base `a1924f17`, arbre propre après
`git pull --ff-only`. Le premier levier ROUTE est `NO-GO_NON_EXPOSE` et ses
seuils restent inchangés. Les références comparées sont celles de
[`multi1_analyse_20261026.md`](multi1_analyse_20261026.md) : AIR seul 109,09 %,
RAIL seul 77,44 %, MULTI 92,67 % du profit AAA à cinq ans et ≈56 % à dix ans
dans la référence historique. La lecture H5 de MULTI comptabilise environ
30,4 M opcodes de tentatives rail et 5,24 M de plans AIR, mais la couverture
CPU est incomplète. H2 (opportunité perdue en recherche rail) reste à tester ;
ce contraste ne mesure pas une économie d'opcodes isolée.

## Intervention et limites figées

Paramètre `multi1_air_over_rail` **0 OFF (défaut aux quatre niveaux)**,
**1 shadow** (log de conflit, ordre inchangé), **2 ON** (une promotion AIR
bornée). Utilisation uniquement en **multimodal AIR+RAIL+ROAD actif**, années
civiles **1971, 1972 ou 1973**, au moment de la dernière sélection
`OpexProjectSelectAffordable(realSelection=true)` et après P2/MULTI1 ROUTE.
La tête doit être un projet `rail` finançable à profit positif, de classe
défensive C77 **0**, sans `railPlan` prêt dans son payload ; les têtes déjà
AIR/ROUTE/FLEET/WATER ou les candidats rail déjà préparés sont intouchables.
Chercher le **premier AIR financé parmi les rangs 1 à 7** du TOP-K, avec
`fundScore >= 80 %` du score de la tête RAIL et `profitAnnual >= 70 %` de
son profit, strictement positif, et
`OpexProjectFinanceCapital(air) <= capitalBudget`. Le projet AIR doit avoir
un payload avec `siteA.town.tile` et `siteB.town.tile`, pour rattacher sans
ambiguïté l'exposition à une construction ; la fonction ne crée ni projet
ni devis, ne lit aucun adversaire et ne modifie aucune métrique économique.
La tête et le candidat doivent être de même tier C77 (tier 0). La variante
2 déplace exactement cet AIR en rang 0 ; 1 ne change rien. Aucune donnée
persistante supplémentaire : liste et classement reconstruits après Load.
Le chemin `0` n'appelle jamais le pilote, ne journalise rien et conserve les
décisions, API et opcodes de sélection historiques.

`MULTI1_AIR_OVER_RAIL` (`AILog.Info`, capturé par `--script-debug`) ne doit
être émis que sur un conflit admissible : année, shadow/promote, rang avant,
identité AIR `(src,dst)`, score/profit/finance AIR et RAIL. Il prouve le
reclassement, pas la construction. L'effet attendu est de sélectionner plus
tôt une ligne AIR rentable avant le coût de démarrage d'une recherche RAIL ;
il peut également cannibaliser un fret profitable. Il ne faut pas attribuer
des opcodes de rail économisés sans trace de recherche correspondante.

## Contrats et épreuves pré-enregistrés

- Contrats hôtes : déclaration, bornes, quatre défauts 0, lecture unique,
  intégrité de l'inventaire historique, OFF court-circuité, shadow inerte,
  limites annuelles/top-K, mêmes rangs C77, budget et marges, aucune lecture
  concurrente. Suite complète : `python -X utf8 -m unittest discover -s
  sweeps -p "test_*.py"` et `git diff --check` après chaque étape.
- Smoke apparié **42 × 1970**, 1 an OFF=0/ON=2, 1970/256²,
  `probes=2`, source figée et même AAAHogEx : santé et compilation seules.
  Save/Load réel **42**, `--years-a 2 --years-b 1` et
  `--arm "OpexAI[multi1_air_over_rail=2]"`, vérifier `LOAD_RECONCILE`,
  absence de crash et redémarrage sans ordre persistant artificiel.
- Exposition appariée **5 graines 42,100,7,999,2026 × 5 ans**, 1970–1974,
  256², OFF=0/ON=2, deux duels distincts contre le même AAA,
  `--probes 258 --script-debug` des deux côtés (panneaux + decision log),
  un même bundle figé ; la sonde est symétrique, ses trajectoires ne sont
  pas supposées identiques à un banc économique en `probes=2`.
  Conditions **cumulatives** pour continuer : **≥3/5 graines** avec au
  moins une promotion `MULTI1_AIR_OVER_RAIL action=promote` enregistrée ET
  **≥2/5** avec construction `AIR_BUILD` du même couple `src,dst` sur le
  même monde, dans les **90 jours** suivant la promotion, via le journal
  `AIR_BUILD` du même bras ON. Sans chaîne
  de construction attribuable, `NO-GO_NON_EXPOSE`, **ni A ni B**.
- Porte A **40 graines canoniques × 5 ans** (1970–1974), mêmes références
  et politique sauf opt-in, `probes=2` des deux côtés, `gain_short`
  sur `profit_year` Opex ON−OFF fin
  1974. Préconditions 40/40 paires complètes, santé, quatre trimestres et
  dénominateurs de valeur positifs ; gain moyen **≥4 %** de la moyenne OFF,
  Wilcoxon exact bilatéral **p<0,05**, borne basse **IC95 bootstrap >0**
  (20 000 répétitions, graine 0), valeur moyenne ON/OFF **≥0,95**. Tout
  échec arrête le levier, sans ajustement post hoc.
- Porte B seulement après A `pass` : **20 graines canoniques × 10 ans**,
  `non_erosion`, borne haute IC95 bootstrap **≥0** et ratio de valeurs
  **≥0,95**, santé 20/20, une répétition, 1970/256². Rapporter en plus
  les ratios Opex/AAA des moyennes et médianes appariées, cible stratégique
  distincte **≥75 %**. Une B pass appelle une **décision utilisateur** ;
  jamais de défaut 2 ni adoption automatique.

Budget : Docker unique, profil Windows local `--cpus 10 --memory 8g
--max-workers 10`, image `openttd-lab:latest`, gel du bundle/source par
`sweeps/run_c66_reference.py`, noms de campagne neufs. Ne pas modifier
P1/VPS, P6 ou LATE-GAME-1. Le pilote ROUTE rejeté n'est pas retesté.
