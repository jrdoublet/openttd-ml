# C83 — réparation locale d'emplacement (02/10/2026)

Demande utilisateur : après l'ablation défavorable de la réaction C83, conserver
la réponse au dernier créneau, éviter la recherche d'emplacements dans les autres
villes et réparer uniquement l'aéroport de la ville menacée.

## Intervention pré-enregistrée

Catégorie **comportement**, pas optimisation qualifiée par neutralité. Le vivier
de partenaires connus peut différer du recalcul : aucun gain économique présumé.
`c83_local_repair=0` reste le défaut aux quatre difficultés ; candidat `=1`.
`c83_slot_reaction=1`, C115=1, C121=0, C83 fixes/P4/préemption ouverte OFF.

Le worker ne passe par le nouveau chemin que pour une intention `c83_slot_race`
ciblée sur une ville. Une photographie transitoire reprend les ancres non-reuse
du portefeuille et les ancres positives du cache, sans modifier leurs tables.
Les données de ville/équipement sont rafraîchies par C77 comme au témoin.

Par combinaison aéroport/avion : revalider les partenaires connus dans le même
vivier urbain ; revalider l'ancre cible, y compris son identité physique de ville
de créneau. Si nécessaire, appeler le chercheur existant seulement pour cette
ville. Revalider le résultat après recherche. Aucun partenaire valide connu
entraîne un repli sur le parcours ciblé ancien pour cette combinaison. Sinon,
la découverte des hubs conserve les hubs existants sans resondage des autres
villes. Les fonctions usuelles évaluent uniquement les paires touchant la cible
et la fusion ciblée conserve les autres projets et modes. Les alternatives ne
sont pas réduites à la seule tête du portefeuille.

La passe reste interrompue pendant le travail réactif comme au témoin : ce lot
réduit son travail, sans changer simultanément l'ordre d'exécution. La recherche
globale normale, C83.1 proactif, le watcher et les autres intentions C77 gardent
leur parcours. Save/Load conserve le contrat de reprise existant : abandon de
la tranche AIR non publiée, redémarrage du mode et reconstruction de la photo.

## Protocole décidé avant les résultats

- Worktree isolé `results/c83_local_worktree_20261002` sous le dépôt partagé Docker,
  HEAD `b2334d7156f12519b1f27a0078bc267f7d40dce8` ; sources C83 et préfiltre de
  cooldown AIR adopté repris du bundle précédent `c83_reaction_off_diag_20261002_r1`.
  Les modifications concurrentes AIR efficiency du checkout principal sont exclues.
- Référence `OpexAI[c83_local_repair=0]`, variante `OpexAI[c83_local_repair=1]`,
  autres réglages aux défauts de cette copie, même AAAHogEx-115 figée.
- Contrats Python, huit cas dirigés en VM NoAI, smoke causal 42 × 1 an,
  puis 5 graines (42,100,999,1234,5678) × 6 ans, une répétition, deux workers.
- Primaire `profit_year`, effet utile +50 000 £/an, garde valeur −5 %, `signs20`.
  Diagnostic : complet/sain, moyenne ≥50 000, garde tenue ; exposition locale
  sur au moins trois des cinq graines pour envisager le 20×10 officiel.
- Trace rare de chaque travail C83 terminé dans les deux bras : branche locale,
  replis, cible conservée/recherchée, partenaires, opcodes et ticks du worker AIR.
  Ces durées excluent le délai d'attente en file et la construction ultérieure.
  Des travaux non appariés ne constituent pas une preuve de gain d'opcodes.
- Docker desktop-linux, image `openttd-lab:latest`
  `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`,
  3 CPU / 2 Go / swap 2 Go, volume `openttd-lab-home`, montage du worktree.
  Aucun commit/push ; aucun défaut changé avant qualification.

## Validation et décision

**Prototype livré OFF ; filtre du diagnostic non franchi.** À ce stade, avant
la demande suivante d'un 20×10, aucun prolongement automatique. Le défaut
`c83_local_repair=0` et la réaction C83 sont conservés. Le 20×10 demandé ensuite
est terminé et non qualifié ; voir l'extension ci-dessous.

105 contrats ciblés réussis (C83, C78, harnais figé, montage, gel, santé), selftest
C66 réussi. Huit cas dirigés dans la VM NoAI : site valide conservé, cible invalide
remplacée, ancre rattachée au mauvais créneau refusée, partenaires absents ou
infirmes déclenchant le repli, reprise sans recherche répétée, résultat de
recherche invalidé avant publication, photographie sans mutation des plans.
Premier essai de fixture non validé : contexte simulé incomplet (`perfOpsSites`
absent dans le curseur de test) ; fixture corrigée, r2 réussi sans changer le
code comportemental. Smokes et diagnostic n'utilisent pas les stubs de fixture.

Save/Load technique réussi : candidat activé et `save_full_state=1`, solo graine
100, phase A 1 an, sauvegarde du 1970-07-01 rechargée, phase B 1 an ; 13 sauvegardes
par phase, `LOAD_RECONCILE` présent, aucun marqueur d'erreur. Ce contrôle n'expose
pas un worker C83 interrompu exactement en cours de réparation ; son redémarrage
repose sur le contrat existant vérifié de sérialisation de `regen_candidates`.
Une compagnie humaine fantôme apparaît au chargement, limite connue du harnais ;
ce test reste technique, aucune conclusion économique en est tirée.

Lors de cette validation, le checkout principal avait un échec de contrat C78
préexistant au lot, lié à la
modification concurrente de `scheduler_tasks.nut` (`refreshReason="event"` au lieu
de `"month"`). Les 18 contrats C78 passent dans le worktree isolé testé ; aucun
correctif de ce chantier concurrent n'a été introduit ici.

### Résultats appariés

Campagnes `c83_local_smoke_20261002_r1` et `c83_local_diag_20261002_r1`.
Bundle commun `6a431e25f13f5e2e742cd7646a9ab02020370a8fdc883f35ec44fba4cde0569c`.
Manifestes smoke `55d38cc136132c91bdf67bd9bd18cbbf3a97761feaa342ac222b468e1b161d1f`
et diagnostic `13a39e4924d8ee3d6bd5d806a6049401cdd8b9885efa0459e0cc9bb0706d2f95`.
Témoin et candidat proviennent du même arbre figé. Le nouveau témoin est remesuré :
ses chiffres ne sont pas interchangeables avec ceux de l'ablation précédente.

Smoke : **2/2 duels sains**, profit identique 336 825 £ (trois trimestres valides,
année initiale partielle), valeur 348 919 £, aucune exposition C83.
Diagnostic : **10/10 duels sains, 5/5 paires**, horizon final 1975-12-01, quatre
trimestres valides par métrique primaire, 1440/1440 observations mensuelles sans
doublon, manque ni extra ; comparaison et couverture complètes. Verdict brut
`diagnostic_only`, échantillon d'adoption incomplet.

| Graine | Profit témoin £/an | Profit variante £/an | Delta £/an | Aéroports témoin → variante |
|---|---:|---:|---:|---|
| 42 | 1 766 125 | 1 766 125 | 0 | 25 → 25 |
| 100 | 695 248 | 830 375 | +135 127 | 24 → 23 |
| 999 | 1 639 043 | 1 855 861 | +216 818 | 23 → 28 |
| 1234 | 1 449 450 | 1 325 184 | −124 266 | 29 → 26 |
| 5678 | 2 008 861 | 1 694 666 | −314 195 | 28 → 25 |

Delta moyen **−17 303,2 £/an**, médiane 0, **2 victoires / 2 défaites / 1 égalité**,
p des signes 1, IC95 Student **[−279 183 ; +244 577] £/an**. Pas de perte démontrée,
mais pas de gain utile établi pour franchir le filtre pré-enregistré +50 k£/an.
Valeur : ratio des moyennes **+1,084392 %**, garde −5 % tenue.

Exposition locale sur **4/5 graines** (100,999,1234,5678) : douze travaux locaux,
sept sites cibles conservés, cinq recherches cibles, zéro repli naturel. Le repli
est exercé par les cas dirigés. Témoin : onze travaux C83 terminés.

Coût observé des travaux du worker : médiane **629 062 → 500 130,5 opcodes**,
durée médiane **1,054 → 0,824 jour**, maximum **1,297 → 1,095 jour**. Les tâches et
leurs entrées diffèrent entre trajectoires : ces observations ne qualifient pas
un gain d'opcodes à entrées appariées. Elles excluent rafraîchissement du catalogue,
fusion finale du portefeuille, attente en file et construction. **Le délai global
25–60 jours n'est donc ni expliqué ni remesuré par ce lot.**

### Preuves conservées

[Résumé durable](../evidence/review/c83_local_repair_20261002/summary.json),
[index et empreintes](../evidence/review/c83_local_repair_20261002/index.json).
JSON, manifestes, fixtures et reload compressés ; JSONL, bundles, sauvegardes et
logs bruts conservés sous `results/c83_local_worktree_20261002/results/`.
Le lanceur accepte `--mount-root` pour utiliser le parent déjà partagé Docker et
sélectionne le worktree réel avec `-w`; le montage par défaut reste inchangé.
Le worktree géré initialement sous `.codex` était non montable ; archivé après
préservation de la copie de test dans le répertoire partagé. Aucun commit/push.

## Extension demandée : estimation opcodes et 20×10

**Décision utilisateur suivante, 02/10 :** estimer les gains opcodes et exécuter
un 20×10. Cette demande autorise explicitement le dépassement du filtre 5×6
non franchi. La catégorie reste comportement et les critères économiques ne
sont pas changés après les résultats du diagnostic. Évaluation uniquement :
le défaut reste OFF pendant le banc et aucun changement automatique n'est demandé.

### Estimation à partir du diagnostic

Calcul sur chaque log cumulatif final une seule fois, avec vérification de son
SHA-256. Onze travaux témoin : 6 595 502 opcodes, soit **599 591 par travail** ;
douze travaux variante : 5 995 533, soit **499 628 par travail**. Ordre de grandeur
**100 000 opcodes économisés par travail C83**, **−16,67 % en moyenne**, **−20,50 %
sur la médiane**. Dépense totale C83 observée : **−599 969 opcodes (−9,10 %)**.
Les nombres et entrées des travaux diffèrent : ce calcul estime un gain local,
sans constituer une mesure causale à entrées identiques ni une neutralité économique.

La somme des traces `AIR_PLAN_PERF` du témoin est **463 780 770 opcodes**
(236 planifications, cinq graines), contre 461 131 930 (235) dans la variante.
La dépense C83 témoin représente seulement **1,42 %** du poste planification AIR.
Les 599 969 opcodes de différence C83 représentent **0,129 %** de ce poste témoin.
Le gain attendu à l'échelle de toute l'IA est donc faible ; son total n'est pas
instrumenté par cette mesure. La différence totale AIR entre trajectoires n'est
pas attribuée à cette seule réparation.

Calcul conservé dans `results/c83_local_opcode_estimate_20261002.json`, données
source et logs vérifiés contre le résumé durable du diagnostic.

### Plan pré-enregistré du 20×10

- Campagne `c83_local_20x10_20261002_r1`, même worktree, même HEAD `b2334d7`,
  même candidat et harnais que le 5×6 ; bundle attendu
  `6a431e25f13f5e2e742cd7646a9ab02020370a8fdc883f35ec44fba4cde0569c`.
- Bras inchangés : `OpexAI[c83_local_repair=0]` / `OpexAI[c83_local_repair=1]`
  contre la même AAAHogEx-115 figée, autres réglages aux défauts de la copie.
- Graines canoniques : 42,100,7,999,2026,1,17,73,314,512,1024,1337,4096,8191,
  12345,54321,65537,123456,424242,8675309 ; dix ans, une répétition, **40 parties**.
- Primaire `profit_year`, effet utile +50 000 £/an, garde valeur −5 %, `signs20`
  (≥15 victoires, p bilatéral <0,05), 20/20 paires, santé/couverture complètes.
- Trois workers, Docker 3 CPU / 2 Go / swap 2 Go, volume `openttd-lab-home`,
  même image figée ; télémétrie de ligne OFF, script debug ON comme au diagnostic.
- Aucun doublon existant. Un autre 20×10 AIR preflight occupe Docker au contrôle
  initial : le lanceur attend sa fin sans arrêter ni modifier ce conteneur.

Lancement effectif après la fin du banc concurrent : campagne
`c83_local_20x10_20261002_r1`, trois workers, 40 parties. Bundle vérifié identique
au diagnostic, manifeste
`e87fcfc284ad70da65335a9066f2e072dfdf01ea7cbe6e1591d5b77e5e3ea610`.
### Résultat du 20×10

**Complet et sain, non qualifié (`fail_primary`) ; défaut OFF conservé.**
Quarante duels sains, **20/20 paires**, comparaison, échantillon d'adoption et
couverture métrique complets. Fin 1979-12-01, quatre trimestres valides par
primaire. **9600/9600 observations mensuelles**, aucun doublon, manque ou extra.
Le manifeste et le bundle exécutés correspondent au plan et leurs empreintes
ont été revérifiées après la campagne. Pas d'erreur technique, aucune relance.

Profit moyen Opex témoin **2 109 304,25 £/an**, variante **2 173 733,45 £/an**.
Delta moyen **+64 429,2 £/an**, médiane **+53 163 £/an** ; **11 victoires,
9 défaites, 0 égalité**, p bilatéral des signes **0,823803**. IC95 Student
**[−67 828,84 ; +196 687,24] £/an** (IC normal publié par le harnais :
[−59 420,79 ; +188 279,19]). Valeur : ratio des moyennes **+5,399673 %**,
garde −5 % tenue. La moyenne dépasse +50 k£/an, mais ni les quinze victoires
ni p<0,05 ne sont atteints : le gain économique reste indécis. Ce résultat
n'établit pas une perte ; il ne qualifie pas non plus une optimisation d'opcodes.

| Graine | Delta profit variante − témoin £/an |
|---|---:|
| 42 | −74 843 |
| 100 | +138 932 |
| 7 | +579 404 |
| 999 | +465 222 |
| 2026 | −143 898 |
| 1 | −217 230 |
| 17 | +436 067 |
| 73 | −273 653 |
| 314 | +406 633 |
| 512 | +35 149 |
| 1024 | −405 905 |
| 1337 | +89 938 |
| 4096 | −124 400 |
| 8191 | −203 425 |
| 12345 | +137 580 |
| 54321 | +416 984 |
| 65537 | +227 726 |
| 123456 | −196 103 |
| 424242 | −76 771 |
| 8675309 | +71 177 |

### Estimation affinée des opcodes

Chaque bras compte **38 travaux C83 terminés sur 17/20 graines**. Variante :
38 parcours locaux, **19 cibles conservées, 19 recherches cibles, zéro repli**.
Le nombre égal de travaux ne rend pas leurs entrées identiques : leurs villes,
partenaires et trajectoires peuvent différer.

| Poste observé | Témoin | Variante |
|---|---:|---:|
| Opérations moyennes par travail C83 | 612 821,34 | 502 151,76 |
| Opérations médianes par travail C83 | 620 875 | 511 724 |
| Total C83 | 23 287 211 | 19 081 767 |
| Durée médiane du worker, jours | 1,041 | 0,831 |
| Total des traces de planification AIR | 2 074 697 938 | 2 114 333 724 |
| Appels de planification AIR | 1087 | 1085 |

L'estimation devient **110 670 opcodes économisés par travail**, **−18,059 %
en moyenne**, **−17,580 % sur la médiane** : ordre de grandeur cohérent avec le
5×6. Différence totale C83 **−4 205 444 opcodes**. Le poste C83 témoin représente
**1,122 %** de la planification AIR ; cette différence en représente **0,203 %**.
Le total AIR observé augmente pourtant de **1,91 %** entre trajectoires : le
gain local ne démontre donc pas une baisse nette de tous les calculs AIR, ni
des opcodes de toute l'IA. Les mesures gardent les exclusions du diagnostic
(catalogue, fusion finale, attente et construction). Le délai global 25–60 jours
n'est toujours pas remesuré.

Les graines 42,1337,12345 n'ont aucun marqueur de réaction C83 ni de réparation
terminée dans leurs deux logs, mais présentent des deltas de profit non nuls.
L'origine de cette divergence de trajectoire n'est pas identifiée par ces
sondes ; chaque delta n'est pas attribuable à une réparation locale observée.
Aucune qualification à entrées appariées ni nouvelle campagne n'est inférée.

### Preuves du 20×10

[Résumé, contrôles et observations](../evidence/review/c83_local_20x10_20261002/summary.json),
[index et empreintes](../evidence/review/c83_local_20x10_20261002/index.json).
Les JSON de campagne et manifeste, l'estimation préalable et son affinage sur
le 20×10 sont compressés et vérifiés. JSONL, bundle et quarante logs moteur restent
dans le worktree ignoré, avec empreintes conservées dans le résumé. Les six
fichiers comportementaux C83 du checkout ont été vérifiés identiques au candidat
testé ; les autres réglages et chantiers ne bénéficient d'aucune qualification.
Aucun défaut modifié, aucun commit/push.

## Publication demandée après le bilan

Demande utilisateur suivante : committer et pousser. Commit C83 `dfa84ba`
(code, contrats, trois paquets de preuves et bilans) ; modifications concurrentes
d'autopsie C121 et de télémétrie mensuelle laissées hors de ce commit.
La branche distante ayant avancé jusqu'à `78f642a`, intégration réalisée dans
le worktree `results/c83_publish_20261002`, sans réécrire les commits distants.
Les conflits réunissent les paramètres/traces C83 avec les spans publiés et
conservent les deux ajouts du journal. Aucun réglage C83 n'est changé.

Validation de cette intégration : **52 contrats ciblés réussis** (C83 29,
montage 3, harnais figé 11, préparation C121 déjà publiée 9), selftest C66 réussi,
diff sans erreur. Smoke technique `c83_publish_smoke_20261002_r2`, graine 42,
un an contre AAAHogEx, bras `OpexAI[c83_local_repair=0]` : **1/1 duel sain**,
deux compagnies actives, horizon complet, dernier checkpoint 1971-01-01.
Trois trimestres valides, année initiale partielle. Premier appel r1 refusé
avant toute partie car `--reference OpexAI` exige un réglage explicite ; r2
corrige uniquement cette syntaxe. Docker 3 CPU/2 Go/swap 2 Go, cache nommé,
un worker, même image ; aucune campagne parallèle.

Bundle technique
`84db5bd9f46f285e504e9b89c20a5b13e13f0db85cbcfb107995432d35733363`,
manifeste `36a273edf488ebf700cfe13aa2a618ee385964544979a108fe0d6dbce883f80b`.
Réglages effectifs vérifiés : réaction C83=1, réparation locale=0,
fixes/préemption ouverte/watcher quotidien=0, C115=1, économie C121=0.
[Preuves du smoke d'intégration](../evidence/review/c83_publication_smoke_20261002/summary.json),
[archives et empreintes](../evidence/review/c83_publication_smoke_20261002/index.json).
Les résultats économiques du 20×10 restent attachés au bundle `6a431e25…` ;
ce smoke ne qualifie pas économiquement le nouvel arbre combiné.
