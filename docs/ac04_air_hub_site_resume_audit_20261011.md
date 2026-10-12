# AC-04 — hubs → sites AIR : reprise, identité, coût (11/10/2026)

**Verdict : audit technique réalisé ; curseur conforme sur état figé ; deux
anomalies de découverte exposées par des fixtures, sans correction ni adoption
économique.** L'absence de compteur de **paires effectivement parcourues**
aligné sur `AIR_LIGHT` interdit un coût en opcodes **par paire réelle**.
La consommation de la *phase* est mesurée ci-dessous, sans extrapolation.

**Qualification ultérieure AC04-A (11/10, staging non intégré) : REJET
pour hausse globale d'opcodes exécutés.** Le défaut de la station saturée
reclassée orpheline est établi et `ac04_hub_route_fix=1` a été testé
isolément en source gelée. Sur 40 graines, quatre ans, le profit terminal
s'améliore de **+113 600 £/an**, IC95 [+55 294 ; +175 042], mais le travail
VM 1970–1971 augmente de **+213 974 opcodes (+0,170 %)**, IC95 bootstrap
**[+72 713 ; +370 559]** sur les mêmes 40 paires. Sur 1970–1972 :
+497 231 (+0,258 %), IC95 [−340 494 ; +1 464 993] ; la fenêtre plus
longue ne gomme pas la régression démontrée auparavant. Contrat utilisateur :
un gain n'est pas exigé ; une régression établie suffit pour rejeter.
Garder le défaut, l'essai et les preuves. [Validation détaillée](air_catalogue_validation_finale_20261011.md).

**Qualification ultérieure AC04-B (staging) : ACCEPTÉE en isolé, sous
réserve de l'interaction.** Le doublon physique d'ancre est éliminé sans
fusionner deux sites C83 distincts d'une ville. B20×10 (20 graines,
40 parties saines) : profit ON−OFF **+66 123 £/an**, IC95
[−5 857 ; +136 783], valeur +2,11 %. Diagnostic `LOOP_OPS` 10×4,
avec la première année de divergence 1972 effectivement clôturée :
**−146 722 opcodes VM** (−0,076 %), IC95 [−409 370 ; +54 178],
1 hausse, 3 baisses et 6 identités. Absence de dégradation mesurée,
mais pas preuve d'équivalence stricte. Aucune fusion en `master` avant
le test du cumul.

## 1. Frontières et invariants contrôlés

- `ai/OpexAI/air_planning.nut:1208–1401` : `DiscoverHubs` recherche des sites
  additionnels seulement sous `AIR_HUB_NEW_SITE_POOL=12`, puis des stations
  à partir des lignes AIR et des aéroports dits orphelins. Les hubs de lignes
  sont identifiés par `AIStation.GetStationID(ancre)` et dédupliqués avec
  `seenStations`, jamais par le seul nom de ville. Le comptage des routes
  utilise `hubIndex.routes` s'il existe, sinon les lignes AIR ; la borne est
  `OpexAirAirportMaxRoutes(type)` (`air_trip.nut:174–181`).
- `air_planning.nut:1420–1442`, `:1608–1613` : pour C121 incrémental,
  `(hubSiteI,hubSiteJ)` reprend le produit cartésien `hubs × sites` ; le test
  de budget avant une nouvelle paire n'agit qu'après **une progression**.
  Sur yield, les deux indices désignent **la première paire non traitée** ;
  ils deviennent `(len(hubs),0)` une fois la phase terminée. Les rejets V133,
  snapshot et filtres interviennent *après* `progressed=true`.
- `air_planning.nut:2423–2462` : le `hubPhase=1` marque le bras terminé.
  Le snapshot AIR03/10 mémorise l'ordre des hubs et sites sous même combo et
  signature. En cas de changement de signature, les curseurs sont remis au
  début intentionnellement (`:1144–1169`) : **la même paire peut être revisitée
  à travers deux topologies**. Ce n'est pas un doublon *dans un parcours figé*.
  Le skip des paires déjà publiées dépend du type d'aéroport et de la paire
  de villes, pas du choix de moteur (`:1104–1139`).
- `air_planning.nut:1065–1096` : à la reprise, le compte de routes des hubs
  non orphelins est rafraîchi ; les extrémités restaurées sont revalidées sur
  demande. Le chemin sauvegarde/chargement réinitialise le curseur C78,
  comme audité en AC-01/AC-06 ; aucun état nouveau ici.
- `air_planning.nut:1450–1605` : la paire hub→site traverse les exclusions
  existantes (snapshot, ville ciblée, préfiltre, paire liée C83, distance,
  bande, abandon), puis calcul de demande, choix économique et admission.
  Les seuils et priorités existants sont laissés intacts.

## 2. Fixture de reprise et anomalies découvertes

**`sweeps/test_ac04_air_hub_site_resume.py`** : six tests, dont une matrice
de **5 625 comparaisons** parcours monolithique/tranché. Dimensions : cinq
tailles de hubs (0/1/2/4/7), cinq tailles de sites (0/1/2/5/9), cinq
positions de cible, trois modèles de coût (constant, variable, dernière
paire coûteuse), trois sélecteurs d'admission et cinq budgets de tranche.
Les mêmes indices sont visités et admis **dans le même ordre** ; aucun indice
`(hub,site)` n'est oublié ou dupliqué à topologie fixe. Cas dédié : arrêt
immédiatement après la dernière destination de la ligne, puis après le
dernier hub, et une dernière paire plus chère que le budget.

**Deux anomalies structurelles distinctes du curseur** sont reproductibles
par stubs déterministes, avec le chemin correspondant vérifié statiquement :

1. **Station saturée présentée comme orpheline.** La première boucle saute
   `routeCount >= maxRoutes` (`air_planning.nut:1328–1329`) *avant*
   `seenStations.rawset` (`:1339`). La seconde boucle `AIStationList`
   (`:1345–1363`) peut donc récupérer **cette même station active** comme
   « orpheline » avec `routes=0`. Le snapshot conserve ce statut et n'actualise
   pas ses routes (`:1069–1072`) ; la validation snapshot teste ensuite la
   capacité sur ce zéro (`:1084`). **Conséquence démontrée :** admission à la
   *génération* d'un hub faussement non saturé et calculs inutiles possibles.
   **Garde ultérieure :** `OpexAirBatchPlanStillLive` applique
   `OpexAirBatchHubHasCapacity` aux deux extrémités réutilisées
   (`task_air.nut:551–603`), avant la construction de portefeuille
   (`:615–618`). Ne pas prétendre qu'une route excédentaire a été construite
   sur cette seule preuve. L'exposition en partie n'est pas mesurée.
2. **Sites supplémentaires en double.** Tant que `sites.len() < 12`, la
   découverte refait `OpexAirFindSite` sur les villes du début
   (`air_planning.nut:1223–1280`), puis `sites.append(extraSite)` **sans test
   d'identité**. Une ville dont le site figure déjà dans `ctx.sites` peut donc
   être ajoutée une deuxième fois (la recherche et son cache peuvent
   retrouver la même ancre). La fixture donne un doublon concret de
   `(ville,ancre)` avec `sites=[(A,41)]` et scan additionnel `[A,B]`.
   **Conséquence démontrée :** dans cette configuration, le produit cartésien
   `hubs × sites` contient des indices distincts représentant une même paire
   physique ; la répétition de calcul/opcodes est plausible. La fréquence
   réelle, les admissions finales et l'effet économique ne sont pas établis.

Ces deux anomalies ne sont **ni** une perte d'indice `hubSiteI/J` **ni** une
autorisation à réduire arbitrairement le vivier. Les supprimer pourrait
modifier les décisions et leur ordre ; aucune correction OFF/ON n'est activée.

## 3. Mesures d'opcodes et provenance

### Profil historique (non contemporain de V141)

`docs/opcode_profile_c121_20261002.md:48–51` : `AIR_LIGHT hub_site`
**13,5 millions d'opcodes/6 ans/graine en moyenne** (cinq graines), soit
**24,5 % des 55,2 M** de planification AIR sur ce profil historique. Cet
agrégat couvre **toute la phase** (tests, reprises et calculs effectifs),
**pas un nombre connu de paires**.

### Diagnostic AC-04 actuel, mono-graine (pas une porte A/B)

- Source : `master` à `bfdb2b9`, aucun `.nut` modifié, `docker info`
  OpenTTD-lab disponible, image `sha256:f4b2b9b3…` ; une seule campagne active.
- Commande : `docker run --rm --cpus=3 --memory=2g --memory-swap=2g
  -e OPPROF_ONLY_LIGHT=1 -v openttd-lab-home:/home/lab -v "${PWD}:/work"
  -w /work openttd-lab python3 -m sweeps.diag_opcode_profile
  --arms reference --seeds 42 --years 3 --workers 1
  --out results/ac04_hubsite_cost_42_3y_20261011.json`.
- Bras C121 catalogue/économie à 1 avec `probe_loop_ops=1` et
  `catalog_cost_probe=1`, même protocole que `diag_opcode_profile.py` ;
  duel contexte AAAHogEx. **1/1 partie saine**, `complete=true`,
  `sources_unchanged=true`. `source_frozen=false` : hashes contrôlés avant et
  après, pas de bundle isolé ni justification de causalité économique.
- Artefacts conservés : `results/ac04_hubsite_cost_42_3y_20261011.json`,
  `results/ac04_hubsite_cost_42_3y_20261011.artifacts/reference_42.log`
  et `results/ac04_hubsite_cost_42_3y_20261011_phase_summary.json`.
  Analyseur reproductible : `sweeps/analyse_ac04_hubsite_cost.py`.
  **Archive versionnable** : `evidence/review/ac04_hubsite_20261011/`
  (rapport, plan avec empreintes du code, synthèse, log complet compressé
  `reference_42.log.gz` et `manifest.json`). Le manifeste vérifie SHA256
  de chaque copie, SHA256 du log brut et restitution gzip bit à bit.

| Année | Invocations `hub_site` | Opcodes de phase | Ticks de phase |
|---|---:|---:|---:|
| 1970 | 40 | 403 955 | 42 |
| 1971 | 588 | 4 336 781 | 606 |
| 1972 | 238 | 25 020 | 3 |
| **Total 3 ans** | **866** | **4 765 756** | **651** |

Ce sont des **invocations de phase**, pas des couples hub-site distincts.
La graine 42 est une seule réalisation et le coût dépend de ses constructions,
des tranches et de l'instrumentation. Les **0 lignes `CATALOG_COST` finales**
dans ces logs indiquent que le dénominateur `air_hub_site_pairs` n'a **pas été
publié** par ce journal pendant l'horizon ; cela **ne signifie pas zéro
paire examinée**. Les 1 455 lignes `CATALOG_COST_SLICE` ne portent pas ce
dénominateur. Le coût en opcodes par paire est donc **NON IDENTIFIABLE**
avec ces données et l'analyseur produit explicitement `null`.

Ne pas inventer le quotient `4 765 756 / 866` comme coût par paire : c'est au
mieux un **coût moyen par invocation de phase**, incluant les appels vides.
Pour mesurer le coût unitaire dans une future variante, il faudrait un
compteur **synchronisé par tranche et par paire réellement parcourue** (avec
répartition des rejets, snapshot et calculs). Une sonde qui comptabilise
seulement les paires arrivant à l'économique sous-estimerait le coût total.

## 4. Décision et suites

- **CURSEUR validé seulement sur entrées figées :** conserver `hubSiteI/J`,
  `hubPhase`, le snapshot adopté et le rebalayage sur changement de signature.
- **Anomalies de découverte identifiées**, non corrigées : isoler chacune
  dans une intervention différente **uniquement après une mesure d'exposition
  sur une partie réelle** et un protocole pré-enregistré. Si correction,
  vérifier parité des candidats, coûts opcodes ciblés, Save/Load si nécessaire,
  puis neutralité économique V102 aux portes exigées. Rien ne passe au défaut
  en vertu des seules fixtures AC-04.
- **Pas de nouvelle campagne économique :** le diagnostic AC-04 est une
  observation de coût, pas un A/B ; aucune adoption, commit ni push.
  Ne pas rouvrir le préfiltre C80 défavorable, V140b, V142 ou V143.
- **Statut :** audit AC-04 livré, **qualifications et gain unitaire ouverts**.
  La prochaine analyse indépendante AC-05 reste hub→hub.
