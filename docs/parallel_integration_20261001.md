# Intégration des quatre audits — 1er octobre 2026

## Décision avant nouvel essai

Demande : exécuter le lot 5 après livraison des lots 1–4. Intégration centrale,
pas de nouvelle délégation ni édition concurrente. Aucun défaut changé, C115=1
conservé, options cadence OFF, aucun commit/push. Copie sans `.git`, Git absent :
impossible de certifier par historique l'exclusivité des écritures des agents.
Les 122 sources `.nut` OpexAI/AAAHogEx/bibliothèques correspondent toutefois aux
empreintes du diagnostic cadence précédent, sans ajout ni suppression.

### Réception et réconciliation

| Lot | Conclusion retenue | Limite / décision |
|---|---|---|
| [Sélection](parallel_selection_audit.md) | R2 présent ; convention d'amortissement différente entre renfort legacy et nouvelle liaison | Pas de biais à l'élection mesuré. Retrait de l'amortissement ajouté = candidat isolé futur, pas correction activée ici. |
| [Latence](parallel_latency_audit.md) | Rebuilds synchrones observés à 24–29 jours | La domination du rail pax n'est pas démontrée. Profiler avant tout découpage. |
| [Bypass](parallel_bypass_audit.md) | R3 présent ; continuation après candidats caducs observée en moteur | Pas d'ancien ordre témoin, causalité non établie. Ni quota accru ni remboursement du bypass après échec réel. |
| [Flotte](parallel_fleet_audit.md) | R1 présent ; renforts observés | Aucun avant/après annuel complet exploitable ; quantité demandée avant R1 absente. Aucun plafond ni priorité nouvelle. |

Les lots sélection/flotte se complètent : moyenne observée, profit marginal et
amortissement sont trois questions différentes. R2 ne corrige pas les deux
dernières. La poursuite R3 ne prouve pas un aéroport supplémentaire (hubs
réutilisables). L'observation de rebuilds longs ne désigne pas leur sous-bloc.

Validation d'intégration avant moteur : **95/95 tests des quatre lecteurs**,
**28/28 contrats R1/R2/R3 et analyse par ligne**, **11/11 tests du diagnostic et
de son raccord**. Suite complète : **997 tests, 995 réussis, 1 erreur Git absent,
1 skip**. Les messages de qualification dans cette suite sont des fixtures,
pas des campagnes lancées. Empreintes vérifiées : 55 entrées sélection,
27 entrées latence, cinq modules de l'analyse sélection ; aucune dérive.

## Protocole pré-enregistré : exposition et perturbation seulement

Intervention minimale retenue : utiliser **les sondes déjà disponibles**, sans
ajout Squirrel. Le lanceur `sweeps/diag_parallel_integration.py` réutilise
`diag_cadence_duel.main`, collecteur officiel, santé et contrôles de couverture.
Le petit raccord accepte des bras sans modifier les bras cadence historiques.

- Deux duels distincts contre AAAHogEx-115, graine **42**, **un an**, début 1970,
  fin exigée **1971-02-01**. Deux workers, plafond conteneur 3 CPU, 2 Go sans swap,
  cache `openttd-lab-home`. Aucun autre conteneur de partie en parallèle.
- Référence : `OpexAI`, tous les défauts courants.
- Profil : `OpexAI[decision_log=1,probe_portfolio=1,probe_scheduler=1,probe_candidates_rail=1,catalog_cost_probe=1,probe_events=1]`.
- Script debug **4 dans les deux bras**. `probe_events` active notamment C56 ;
  ses autres sondes rendent le profil plus coûteux. Les six seules différences
  effectives sont vérifiées par test ; aucun réglage de décision n'est changé.
- Image : `sha256:69d7e57aad5d3036f16655e8af23f36aa9fbb7c82c61ea325192c56b50e48e47`.
- Sortie neuve : `results/diag_parallel_integration_20261001_r1.json`, logs,
  checkpoints et `plan.json` dans le dossier `.artifacts` associé.
- Sources stabilisées pendant le run et contrôlées par empreintes avant/après.
  **Pas de SHA Git ni bundle immuable exécuté** ; ce diagnostic n'est pas une
  qualification et ne remplace pas le gel requis d'un futur A/B économique.

### Critères fixés avant résultat

1. Santé : deux parties complètes, dates/année/compteurs physiques valides,
   aucun fatal, sources inchangées. Sinon résultat non validé.
2. Exposition : au moins une fenêtre C56 rail/AIR appariée et un profil rail pax
   non nul. Publier les trous/ambiguïtés ; le compteur d'émissions n'est pas le
   nombre de générations (un profil peut être republié après resélection).
3. Mesures : durées calendaires et ticks des fenêtres C56, opcodes conventionnels
   par phase et ventilation C41 à l'intérieur du rail. Ne pas sommer parents et
   sous-étapes ni convertir le champ AIR `days=ticks/74` en jours calendaires.
4. Perturbation : profit Opex, valeur, dates de construction et compteurs du profil
   contre le témoin de la même campagne. Une seule graine de duel bruité ne sépare
   pas le coût direct des sondes des divergences de trajectoire ; aucun seuil de
   neutralité ou verdict de gain n'est attribué à cette comparaison.
5. Arrêt après ce smoke/profil : **aucun 5×6 ou 20×10 automatique**, aucun nouveau
   découpage ni changement du classement décidé uniquement sur cet échantillon.
   Pour une future politique : exposition dédiée, profit Opex +50 k£/an et garde
   valeur −5 %, protocole officiel ; règle distincte si optimisation d'opcodes
   déclarée et coût net effectivement mesuré avant comparaison.

Les probes sont volontairement différentes pour mesurer leur perturbation,
pas pour comparer deux politiques. Toute future comparaison comportementale
devra utiliser une instrumentation identique entre bras.

## Résultats et suites

### r1 : santé acquise, exposition C41 incomplète

Deux parties saines, sources inchangées, exit=0 et pas d'OOM. Collecteur/lecteurs
exercés réellement. 1 101 marqueurs C56 dans le profil, sept fenêtres complètes
par grande phase : AIR médiane 23 j (max 25), rail 5 j (max 5), assemblage 5 j
(max 9). Parents/sous-étapes non additionnés. Un `TASK_ENTER projects` reste
ouvert en fin de log : conservé comme censuré, pas comme durée complète.

**Perturbation observée :** profil −242 016 £ de profit Opex en 1970 et −50,41 %
de valeur contre témoin. L'écart ne chiffre pas le coût direct de la sonde :
duel bruité, calculs instrumentés et trajectoires compétitives différents.
Première construction AIR du profil 19/02/1970 ; date inconnue dans le log témoin
non instrumenté, donc aucun délai gagné/perdu apparié inventé.

**Défaut du protocole d'exposition r1 identifié :** `probe_candidates_rail`
active les compteurs C41, mais `OpexC39Log` retourne si
`C39_INVALIDATION_PROBE` est faux. Il faut aussi `probe_catalogue=1` ; aucun
profil C41 émis dans r1. Ce n'est pas une absence de calcul rail. Le critère
d'exposition pré-enregistré n'est donc pas rempli, sans effacer ce résultat.

### Amendement technique r2, fixé avant relance

Seule correction : ajout de `probe_catalogue=1` au bras profil, test de contrat
de cette dépendance ajouté. Sept différences de sondes contre référence,
aucun changement Squirrel. Même graine/horizon/ressources/critères et image ;
nouvelle sortie `results/diag_parallel_integration_20261001_r2.json`.
Cette relance corrige une collecte manquante, ne recherche pas un résultat
économique favorable. Ni pooling r1/r2 ni substitution des résultats r1.
Après r2, arrêt du protocole même si la ventilation reste insuffisante.

### r2 : résultats finaux et décision

`results/diag_parallel_integration_20261001_r2.json` : **2/2 parties saines**,
`complete=true`, `sources_unchanged=true`, dates finales 1971-02-01. Conteneur
`opex-parallel-integration-r2`, sortie 0, sans OOM, environ neuf secondes.
Les horodatages moteur sont UTC (30 septembre au soir), le suivi est daté du
1er octobre local. r1 est conservé séparément.

**Exposition atteinte :** 1 099 marqueurs C56, cinq profils rail pax dont quatre
non nuls (184 à 187 paires examinées), cinq bilans `CATALOG_COST`. Le premier
profil pax nul correspond à la génération initiale fret, pas à une sonde cassée.
Les profils restent des émissions, pas des générations indépendantes garanties.

| Fenêtre C56 du profil | n | Médiane jours | p95 jours | Maximum jours |
|---|---:|---:|---:|---:|
| Grande phase AIR | 7 | 23 | 25 | 25 |
| Grande phase rail | 7 | 5 | 5,7 | 6 |
| Assemblage, sélection comprise | 7 | 5 | 9,1 | 10 |
| Tâche catalogue complète | 5 | 36 | 42,6 | 43 |

Un `TASK_ENTER air_fleet`, daté du 25/01/1971, reste sans EXIT dans le log :
intervalle non clos conservé comme tel, non ajouté aux durées complètes. Cela ne
prouve ni un blocage infini ni la cause exacte de la clôture manquante. Santé du
jeu et complétude de chaque fenêtre de télémétrie sont des contrôles distincts.

Sur les **cinq bilans catalogue** : 29 167 535 opcodes conventionnels au total ;
AIR 18 592 367 (**63,74 %**), rail 3 829 528 (**13,13 %**), sélection 4 599 099
(**15,77 %**), refresh 4,66 %, assemblage hors sélection 1,27 %. Ratio des sommes
sur ces seuls bilans, pas part du CPU ni couverture de tout le temps de partie.
Les fenêtres C56 et bilans catalogue n'ont pas exactement le même périmètre ;
ne pas sommer leurs comptes ou extrapoler ce profil au défaut non instrumenté.

**Perturbation r2 :** profit Opex 1970 = 323 000 £ contre 543 910 £, soit
**−220 910 £** ; valeur 292 396 £ contre 545 521 £ (**−46,40 %**). Au checkpoint
final : 8 aéroports / 6 avions principaux Opex contre 10 / 10 dans le témoin.
AAA : profit 809 317 £ contre 610 754 £. Ce sont les effets observés du profil
complet et de sa trajectoire, **pas un coût causal pur des sondes**. Le faible
profit du profil n'est ni un rejet de C115 ni un test des corrections R1/R2/R3.

Les trois lecteurs à sortie persistée ont été exécutés sur r1 et r2 :

- `results/parallel_latency_audit/integration_20261001_r{1,2}/` ;
- `results/parallel_selection_audit/integration_20261001_r{1,2}.json` ;
- `results/parallel_bypass_audit/integration_20261001_r{1,2}.json`.

Le lecteur flotte a été exercé via `analyse_payload` sur chacun des logs, dans
une enveloppe portant le bras et la graine issus du manifeste : aucun événement
`fleet_built` dans ce court profil, aucune paire avant/après, quantité inconnue
et non zéro imputé. Sortie consultée en mémoire seulement. Les lots sélection
et bypass restent non qualifiants ; aucun biais comparable à l'élection ni
avancement causal déduit de cette campagne d'exposition.

Empreintes du lot bypass vérifiées : dix artefacts et un manifeste concordent.
La source flotte concorde avec le SHA publié. Les quatre lots originaux sont
inchangés ; les résultats d'intégration sont des fichiers distincts.

Tests finaux : **998 exécutés, 996 réussis, 1 erreur Git absent, 1 skip** ;
12/12 tests ciblés du raccord/collecteur. Aucune erreur nouvelle fonctionnelle.
Le test Git échoue toujours sur `git show 6895781:ai/OpexAI/builder_rail.nut` ;
ni masqué ni désactivé. Aucun test source ne remplace une qualification moteur.

### Ordre de suite retenu

1. **Mesure légère AIR / sélection** avant découpage : ce profil ne justifie pas
   de commencer par le rail pax. Réduire l'instrumentation englobante, conserver
   des identifiants et durées locaux puis vérifier sa perturbation. Aucun
   changement de C115 ni réactivation de C121 pour obtenir cette mesure.
2. **Convention d'amortissement du renfort legacy**, lot séparé : figer une
   estimation à l'élection et mesurer les inversions de classement avant variante.
   Ne pas confondre cohérence comptable et preuve de rendement marginal.
3. **Validation ciblée R1/R3** : états budget 4→1 et bypass au rejet directement
   observables, scénarios moteur et Save/Load dédiés. Les traces naturelles ne
   remplacent pas ces fixtures ; elles restent à réaliser, sans recoder les fixes.

**Intégration des lecteurs et contrôle moteur terminés ; validation économique
non acquise.** Aucun fichier Squirrel édité, aucune adoption, aucun nouveau
5×6/20×10, aucun commit ou publication. Arrêt des parties après r2 conformément
au protocole ; le prochain changement comportemental reste isolé et pré-enregistré.