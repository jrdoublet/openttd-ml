# V233b — diagnostic et suite du 18 octobre 2026

Travail dans `/home/deploy/projects/wt-v233b`, branche `v233b`, départ propre
`b7d6d34`, contenant E0–E3. Code et contrats : **`d2c2b31`**
(`V233b : corriger les greffes et tracer leur conversion`). Aucun push ni merge.
Cette intervention ne qualifie aucun gain économique. Les défauts V233 restent 0/0.
Les deux verdicts historiques `fail_primary` sont conservés.

## 1. Diagnostic sans partie

Sources : les vingt fichiers `reference_seed*_r0.log` et
`v233expo_seed*_r0.log` de `results/v233_expo_10x6_20261018_engine/`.
L'analyseur reproductible est `sweeps/analyze_v233_exposure.py` ; résultat local
`results/v233b_diagnostic_20261018.json`, avec SHA256 des fichiers lus et numéros
de lignes des échecs/exemples. Les observations décrivent la production globale,
pas la contribution causale d'OpexAI. Les références de code ci-dessous sont au
commit `d2c2b31` ; les chemins et numéros des logs désignent les fichiers fournis.

Reproduction, sortie à nom neuf, sans moteur :

```bash
python3 sweeps/analyze_v233_exposure.py \
  results/v233_expo_10x6_20261018_engine \
  --out results/v233b_diagnostic_relecture.json
```

### 1a. E1 : conversion locale réelle, supplément net non démontré

Le décompte exact est **223 continuations**, sur les dix graines. Les 738
constructions de rang > 0 en variante contre 730 en référence sont confirmées,
mais ce compteur inclut **toutes** les passes, avec ou sans continuation. Il ne
mesure donc pas la conversion de l'événement `continue`.

En découpant chaque journal après `continue`, jusqu'à la prochaine tâche OPEX
`TASK` ou prochaine continuation, **80 segments sur 223 contiennent une pose**,
143 aucune. Les 80 segments contiennent **88 constructions** : 51 `fleet`,
32 AIR, 3 route et 2 rail. Cela ne prouve pas 88 constructions supplémentaires
face à la référence : un renfort simplement avancé dans le temps peut ensuite
manquer dans une passe ultérieure. La porte A E1 reste négative/non qualifiée.

Exemple direct : `v233expo_seed42_r0.log:4166`, continuation rail rang 0,
`built=0` ; `:4167` renfort de flotte, `:4169` `V233_BUILD mode=fleet rank=1`.
La continuation n'est donc pas globalement « vue, jamais convertie ».

Le devenir du projet suivant est déterminé par les gardes ordinaires :

- **A* occupé** : `task_projects.nut:1474` écarte les autres projets rail sans
  plan prêt **avant** K_pass. Pas de deuxième recherche, pas de compteur de pose.
  Cet écartement était silencieux dans les journaux fournis.
- **Caisse / K_pass** : `task_projects.nut:1529` et la suite conservent le budget,
  le seuil après une vraie pose et son unique bypass. `pending` n'incrémente
  toujours pas `builtCount` ; si une pose a précédé le pending, ces gardes peuvent
  terminer la passe. Un candidat absent de `best` pour financement n'est pas
  ressuscité par E1. Aucun fonds n'est réservé au rail.
- **Dédoublonnage** : `task_projects.nut:1608` évite une seconde tentative de la
  même recherche rail/fleet dans la passe ; `c75BuiltKeys` évite aussi de refaire
  une construction. Aucun compteur historique ne permet d'attribuer les 143
  segments vides à ce motif.
- **Fin de liste** : exemple `v233expo_seed100_r0.log:11831`, sélection de trois
  projets ; `:11834–11835`, les deux premiers rail échouent à la séparation ;
  `:11837`, continuation rang 2 ; `:11838`, tâche suivante. Il n'y a aucun projet
  derrière. Sur les 143 segments vides, 28 ont un rang final compatible avec la
  taille de la dernière sélection `VIVIER` journalisée ; 115 ont des suivants
  sélectionnés. Ce rapprochement de snapshots n'est pas un audit exhaustif des
  motifs de sortie de passe.
- **Suivants non constructibles** : dans les segments prolongés, les événements
  `PROJECT_DISCARD` donnent 43 `plan_failed`, 19 `batch_plan_dead`, 8
  `siteB_unbuildable`, 5 `siteA_unbuildable`, 4 `build_failed`, 3
  `dst_origin_served`, 2 `src_origin_served`, 1 `abandoned_pair`. Ce sont des
  événements, potentiellement plusieurs par segment, avec journalisation
  mensuelle partielle ; pas une partition des 143 échecs de conversion.

Conclusion limitée : E1 libère bien l'examen d'autres modes, mais ne crée ni
caisse, ni candidat constructible, ni deuxième créneau A*. Les logs existants
ne permettent pas de quantifier honnêtement chaque motif silencieux. Je ne
modifie donc pas sa politique pour fabriquer davantage de poses ; j'ajoute les
liens de passe et les compteurs manquants.

### 1b. Les treize `build_failed` sont surtout des recherches de sites échouées

**9 `SITEAB`, 3 `SITEB`, 1 `NOPA`**. Douze échecs ont `iters=0` ; `NOPA` a
9 itérations. Les treize `RAIL_BUILD_FAIL` donnent **`error=0`**. Aucun de ces
treize événements ne fournit une erreur native AIError expliquant le site.
Ne pas leur attribuer un `TRKFAIL` voisin d'une autre paire.

| Graine | Ligne `V233_DROP` | Ligne `RAIL_ATTEMPT` | Usine | Motif |
|---|---:|---:|---:|---|
| 100 | 12375 | 12372 | 4 | SITEAB |
| 100 | 24501 | 24498 | 43 | SITEAB |
| 17 | 18422 | 18419 | 18 | NOPA |
| 1 | 5905 | 5902 | 39 | SITEAB |
| 1 | 21842 | 21839 | 39 | SITEAB |
| 1 | 21991 | 21988 | 37 | SITEAB |
| 314 | 18602 | 18599 | 20 | SITEAB |
| 512 | 4867 | 4864 | 33 | SITEB |
| 512 | 8154 | 8151 | 24 | SITEAB |
| 512 | 11197 | 11194 | 33 | SITEB |
| 512 | 16133 | 16130 | 24 | SITEAB |
| 512 | 19241 | 19238 | 37 | SITEB |
| 73 | 22756 | 22753 | 32 | SITEAB |

Chaque ligne est dans `v233expo_seed<GRAINE>_r0.log`. Des rejets sont également
publiés par `PROJECT_DISCARD`, notamment graine 512 `:8155` (`SITEAB`), `:16134`
(`SITEAB`), `:19242` (`SITEB`) et graine 73 `:22758` (`SITEAB`). Leur absence
ailleurs vient du contrat de journalisation partielle, pas d'une réussite cachée.

Le builder impose la **longueur du quai d'intrants** à la greffe
(`builder_rail.nut:501`), tente une jointure parallèle à 1–4 tuiles
(`:385`), puis cherche B seulement si A existe. Le refus strict à `:555`
utilise `OpexRailSiteReason` (`:461`). Ainsi **`SITEAB` ne prouve pas deux sites
impossibles indépendamment** : B n'a pas été inspecté si A a échoué. On sait
que neuf greffes n'ont pas obtenu de quai A captant les biens, et trois ont
obtenu A mais pas B à cette longueur. Les logs ne séparent pas terrain non
plat, tuiles occupées, couverture productrice et échec de commande de jointure.
`NOPA` est une impossibilité de chemin avec les sites retenus, pas un manque de
caisse ni une erreur AIError renseignée.

Autre défaut visible : `v233expo_seed1_r0.log:21841` abandonne
`freight|5|39|65535` alors que le générateur cherche `freight|5|39|t43`.
`OpexAbandonedPairKey` ne reconnaissait que les IDs négatifs comme invalides.
La sentinelle réellement observée empêche ici le cooldown de la paire urbaine
d'être reconnu ; le même mauvais débouché peut donc être proposé à nouveau.
La correction est limitée aux candidats marqués V233.

### 1c. `month_coverage` et seuil de production : deux filtres distincts

Les **320** `V233_DROP reason=month_coverage` sont produits quand un travail
d'observation encore inachevé est remplacé après **changement de mois OU de
révision du monde** (`goods_v233.nut:151`). Ce compteur ne signifie ni 320
usines sous 64 unités, ni 320 mois manquants indépendants. Il peut également
signaler un redémarrage après une construction AIR au cours du même mois.

Le seuil est dans `OpexV233Quantity` (`goods_v233.nut:73`) : trois lectures
calendaires consécutives, distinctes, puis `min(q0,q1,q2) >= 64`. Un zéro est
conservé ; une observation manquante réinitialise la série. `count=3` ne veut
pas dire trois mois productifs.

Sur les logs : **1 861 observations**, dont **1 262 strictement positives** ;
**1 249 fenêtres** de trois mois consécutifs observés, **305** passent le minimum
mensuel, **682** passeraient une moyenne entière de 64. Les **377 fenêtres
supplémentaires** sont des fenêtres corrélées, pas 377 nouvelles usines ni
377 possibilités constructibles. Le volume est industriel global ; la présence
de nos trains ne prouve pas que nous avons causé chaque production.

Exemple sans même un mois à zéro : graine 7, usine 2/gare 41, lectures
`v233expo_seed7_r0.log:4667`, `:5052`, `:5449` = **60, 60, 120** ; moyenne 80,
minimum 60, rejet historique. Puis `:5052`, `:5449`, `:5925` = **60, 120, 110** ;
moyenne 96, minimum 60, encore rejet. Ce seuil élimine donc bien des usines à
production régulièrement positive, compatible avec des arrivages espacés.
Les données ne prouvent pas à elles seules le calendrier ni l'auteur des
livraisons d'intrants. Graine 42 : aucune fenêtre stricte, six fenêtres moyennes
potentielles ; ce n'est pas une garantie de greffe.

## 2. Correctifs livrés et périmètre

Tout le code ci-dessous est dans `d2c2b31`.

- `info.nut`, `settings.nut`, `globals_pre.nut` : `v233_goods_graft` devient un
  **entier 0–2**, même réglage public, défaut 0 aux quatre difficultés. 1 garde
  le minimum mensuel ; **2** active le lot expérimental ci-dessous. La greffe
  est toujours refusée si `v233_pending_continue=0`. Aucun réglage ajouté,
  plafond de 76 inchangé.
- `goods_v233.nut::OpexV233Quantity` : mode 2 = moyenne entière sur les mêmes
  trois vrais mois, seuil toujours 64. Aucun remplacement d'un mois manquant
  par zéro et aucune production inventée. La revalidation accepte un mois
  courant à zéro seulement dans ce mode, avec fenêtre complète exigée par
  `_v233CandidateLive`. Les observations restent au format sauvegardé v1.
- `_v233GoodsStep` : en mode 2, termine une indexation/observation bornée malgré
  une révision intermédiaire ; chaque support est revalidé. La publication
  reste interdite sur révision périmée. Les échantillons obtenus sont conservés
  pour la reconstruction suivante. Le changement de mois reste une frontière
  stricte, sans rattrapage fictif. Enrichissement de `month_coverage` par cause,
  phase et curseurs ; `V233_OBS` expose les trois valeurs et le volume retenu.
- `_v233CandidateLive` : en mode 2, une hausse de moyenne ne jette plus une
  offre déjà chiffrée à volume inférieur. Une baisse sous son propre volume
  l'invalide toujours. Aucun relèvement de score, de profit ou de volume.
- `OpexV233PlatformPlans`, appelé par `builder_rail.nut::OpexRailPlatformPlans`
  **uniquement en mode 2 pour une greffe** : cherche de la longueur économique
  aval jusqu'au plancher physique commun, plafonnée par le quai support et
  le catalogue. Jointure StationID stricte, couverture de l'usine, test moteur
  et acceptation B conservés. Pas de réemploi de voie ni de gare libre de repli.
  L'économie et le capital sont recalculés par le chemin ordinaire après le
  choix du quai. Cela offre des solutions plus courtes sans garantir de sauver
  les douze sites historiques.
- `_v233GraftStep` : en mode 2, vérifie le couple de quais avant de retenir la
  meilleure des trois villes. Une ville économiquement séduisante mais sans
  sites ne masque plus les autres. Un seul candidat économique et un seul
  appel de recherche de sites par invocation ; coût VM non mesuré, chaque
  recherche pouvant effectuer plusieurs tests natifs. `state=site_rejected`
  donne motif et compteurs A/B. Aucun assouplissement des filtres communs.
- `lines.nut::OpexAbandonedPairKey` : clé usine/cargo/**ville** explicite pour
  une greffe active, conforme au générateur. Pas de changement des autres
  paires ni des anciennes sauvegardes ; les anciennes clés génériques ne sont
  pas transformées en bannissement de toutes les villes.
- `task_rail.nut::_tryBuildRailProject` : une fin de recherche synchrone réussie
  passe elle aussi par stockage, devis et réarbitrage, comme la fin segmentée.
  Corrige le risque de `V233_REPRICE` sur une entrée de stock absente. Cette
  correction de contrat s'applique aux greffes des modes 1 et 2.

Les deux derniers correctifs de contrat s'appliquent aux chemins V233 existants.
Les choix nouveaux d'exposition sont groupés en **mode 2**, comparables au mode 1
dans le même arbre. Le résultat éventuel du lot ne sera pas attribué à la seule
moyenne. Ni score, ni réserve, ni priorité rail, ni modèle C70/C69 modifié.
Les chemins et réglages interdits par la mission sont inchangés. Le défaut 0
garde la même logique métier ; aucune identité bit à bit des trajectoires n'est
affirmée sans exécution, car même des gardes ajoutées consomment des opcodes.

## 3. Mesure de conversion ajoutée

Tous les nouveaux événements sont sous `DECISION_LOG` ; la sonde de livraison
est en plus sous le drapeau greffe. Aucun panneau ni réglage public nouveau.

- `task_projects.nut::_tryBuildProjects` : identifiant `pass` dans `continue`,
  `V233_CONVERSION state=result` pour les cinq exécuteurs après la première
  continuation ; clé, rang, mode, résultat et motif disponible. `state=pass_end`
  donne poses après continuation, suivants examinés, rails sautés pour créneau
  occupé, doublons, motif d'arrêt et capital disponible. Il reste possible de
  distinguer « aucun suivant » et « suivants refusés ». La politique E1 reste
  identique. Le motif d'exécuteur reste `rejected` si aucun discard précis
  n'a été produit : ne pas le renommer arbitrairement en manque de caisse.
- `task_rail.nut` : `V233_GRAFT state=attempt`, puis `pose_attempt` si le plan
  existe et est valide, sinon `search_failed` ; résultat avec motif réel et
  code erreur, puis `V233_BUILD factory=... line=...` au succès. Une tentative
  d'entrée d'exécuteur n'est pas comptée comme pose ni comme dépense réelle.
- `goods_v233.nut::_v233DeliveryStep`, appelé depuis `scheduler.nut` : une ligne
  inspectée par invocation, charges des seuls véhicules de la ligne. Baisse
  de chargement du bon cargo, véhicule à l'arrêt dans la gare B réellement
  acceptante, ordre non transfert : `V233_DELIVERY
  state=first_observed_since_load`, identités usine/cargo/gare/ligne/véhicule.
  Aucun revenu utilisé comme preuve. Il s'agit de la **première livraison
  observée depuis le chargement**, pas nécessairement de la première réelle.
  Une décharge entre deux inspections peut être manquée ; l'absence d'événement
  reste inconnue. Sonde transitoire, remise à zéro dans `Load`, jamais dans
  `Save` ; aucune nouvelle dépendance comportementale persistée.

La chaîne mesurable est donc candidature → entrée d'exécuteur → recherche/stock
→ tentative de pose → ligne enregistrée → déchargement observé. Les codes
AIError des anciens tests de sites ne sont pas récupérables rétroactivement.
Les compteurs de commandes donnent désormais une localisation plus précise
des refus de sites ; le code natif précis reste absent si le helper ne le
remonte pas.

## 4. E4 différé

**Non implémenté.** E3 n'a pas passé A et ne construisait que huit greffes dans
dix parties. La conception §5.1 exige une greffe qualifiée commune aux bras
avant l'option ; §6.5 recommande OFF tant que le devis aval n'est pas bornable.
Ajouter un bonus maintenant brouillerait le diagnostic de conversion et
avancerait des intrants sans preuve que leur aval est exploitable. Aucun mode
d'option factice, score forcé ou drapeau public supplémentaire n'est ajouté.

## 5. Tests réellement exécutés

Commande demandée :

```bash
PYTHONPATH=sweeps python3 -m unittest discover -s sweeps -p "test_*.py"
```

**1 914 tests, OK, 3 ignorés**, 20,591 s. Journal complet :
`results/v233b_unittest_delivered.log`. Aucun test échoué. Les trois skips
sont conservés ; ils ne valent pas validation moteur. Les essais intermédiaires
ont permis d'adapter deux assertions textuelles E1 aux compteurs ajoutés.

Nouveaux contrats et fixtures dans `sweeps/test_v233b_exposure.py` : limites des
segments de continuation, attribution des échecs par paire, conservation du
code erreur, zéros/mois manquants/doublons, mode entier OFF, recherche physique
stricte, ordre de choix des villes, fin synchrone passant par le stock, clé
d'abandon urbaine, gardes de télémétrie et absence de persistance de la sonde.
`sweeps/test_v233_pending.py` est adapté, sans relâcher ses invariants de
bypass, dates et recherche unique. Le test `test_v246_fixed_policies.py` fait
partie de la suite complète ; son plafond reste inchangé.

`git diff --check` propre. Relecture du diff, dépendances, déclarations de
méthodes et défauts effectuée. Aucun Docker, OpenTTD, smoke ni roundtrip moteur
lancé, conformément à la demande. **Compilation Squirrel, coût VM, Save/Load
réel et gain d'exposition après correction restent non mesurés.**

## 6. Plan proposé, à lancer par l'utilisateur uniquement

Lot évalué : E1 + E3 mode 2, pas E4. Figer le code `d2c2b31` (ou la pointe
documentaire qui le contient), adversaire, bibliothèques et configuration dans
un nouveau bundle avec le harnais courant. Pas de réemploi des verdicts du
18/10. Vérifier contexte Docker, volume et ressources au lancement ; sur VPS
3 CPU, 2 Go RAM/swap, 3 workers, une seule campagne. Pas de lancement effectué.

1. **Diagnostic d'exposition 10×6 apparié**, graines identiques :
   `42 100 999 7 73 314 512 1 17 2026`. Référence
   `OpexAI[decision_log=1,v233_pending_continue=0,v233_goods_graft=0]`, variante
   `OpexAI[decision_log=1,v233_pending_continue=1,v233_goods_graft=2]`,
   `--script-debug`. Comparer les entonnoirs avec les dix graines entières,
   pas un sous-ensemble favorable : couverture, motifs des sites, A*→stock,
   plans expirés, caisse, continuation→poses, greffes→déchargements, délais,
   évolution AIR et temps/opcodes des tâches. Suivre aussi les champs annuels
   ordinaires sans en tirer de verdict économique sur dix graines. Objectif
   descriptif pré-enregistré : dépasser les huit poses historiques et observer
   des déchargements attribués sur plusieurs graines ; aucun seuil de profit
   utilisé comme filtre. Si la conversion reste faible, diagnostiquer avant
   A et laisser E4 OFF. La nouvelle sonde peut manquer une décharge : auditer
   les sauvegardes des lignes sans témoin avant de conclure « zéro livraison ».
2. **Porte A 40×6 `gain_short`**, sous le même lot et les mêmes défauts communs,
   sans `decision_log` ni autre sonde détaillée dans les deux bras. Référence
   `OpexAI[v233_pending_continue=0,v233_goods_graft=0]`, variante
   `OpexAI[v233_pending_continue=1,v233_goods_graft=2]` ; graines canoniques
   complètes, une répétition. Primaire `profit_year` Opex variante − référence,
   Wilcoxon bilatéral exact p < 0,05, borne basse IC95 bootstrap > 0,
   moyenne ≥ 4 % du profit de référence, garde de valeur 5 %. Quarante paires
   saines, horizon terminal et quatre trimestres complets, couverture et verdict
   `pass` requis. Une seule campagne pré-enregistrée, aucun choix d'horizon après
   résultat ni relance pour obtenir un résultat favorable. A seul n'autorise
   aucune adoption ; B 20×10 resterait nécessaire si A passe.

Options communes du lanceur : `--primary-metric profit_year --repeats 1
--decision-rule gain_short --min-useful-primary-delta-pct 4
--value-guard-max-loss-pct 5 --required-seeds 40 --required-years 6 --years 6`.
Noms neufs proposés : `v233b_expo_10x6_20261018` et
`v233b_porteA_40x6_20261018` (vérifier leur disponibilité). Ajouter
`--variant-policy-id v233b_e13_mode2` et le profil matériel vérifié.
Le diagnostic à dix graines est attendu hors échantillon d'adoption
(`diagnostic_only`) ; ne pas le présenter comme une porte A incomplète gagnée.

FIN
