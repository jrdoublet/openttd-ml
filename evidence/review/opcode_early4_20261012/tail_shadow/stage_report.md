# P0 tail shadow — stage isolé, 12 octobre 2026

## Provenance et portée

- Worktree détaché : `results/p0_opcode_tail_stage_20261012`, HEAD initial
  `f6139d89f299bcd3d2d24bc32bf22fef6df21d8f`.
- Juste après sa création, **seul** le `ai/OpexAI/probes.nut` courant du
  worktree principal a été copié vers ce stage. Vérification immédiate :
  `git diff --stat` montrait **uniquement** `probes.nut`, 33 lignes touchées
  (`+31/-2`). Ce sont la parité Save à partir de 64 lignes, le prélèvement
  C121 station-flux, et les compteurs `sleep_left` / `sleep_ctx` /
  `sleep_cap3k` déjà présents dans la source principale non commitée.
  Les changements de ce chantier sont superposés à cette copie, sans
  recopier aucun autre fichier modifié du worktree principal.
- Changements du stage uniquement : `globals_pre.nut`, `info.nut`,
  `settings.nut`, `probes.nut`, nouveau test `sweeps/test_probe_tail_shadow.py`.
  Aucun changement du scheduler, worker, registre, portefeuille, Save/Load,
  ou harnais C121.

## Contrat

`probe_tail_shadow=0` par défaut aux quatre difficultés ; activable
**seulement** en conjonction avec `probe_loop_ops=1`. Le profil ordinaire
du `main.nut` n'est pas remplacé, et la seule sonde nouvelle est placée
**à la fin de `_mainLoopProfiled`, après C67 et avant `AIController.Sleep(1)`**.

`OpexTailShadowSample` lit le tick et le reliquat (`GetTick` et
`GetOpsTillSuspend`), puis les états : `activeWorker.kind`,
`railSearch.phase/isC121RailPrep`, le flag de hold de prep,
`reactiveQueue.len()` (O(1)), et les indicateurs de C67. Il ne démarre ni
worker, ni pathfinder, ni commande NoAI. Un hold inattendu sans
`isC121RailPrep` est signalé comme `orphan_hold`.

À `left < 4000`, le compteur `low` est incrémenté sans examiner les états.
Au-dessus, le plafond de calcul conditionnel est `left - 3000` et le
plafond résiduel est recalculé après la garde. Toute traversée d'un tick
annule le plafond résiduel ; les traversées sont comptées.
La classification `UNKNOWN` est obligatoire dès qu'un worker, une recherche
rail, une intention réactive ou un crochet C67 existe : l'aptitude réelle
à progresser peut demander API, suspension, réélection, validation de
capital, activité externe ou nettoyage. `NONE` désigne l'absence de ces
indicateurs ; ce n'est pas une prédiction de non-travail futur.

Les observations sont gardées en table transitoire et publiées **une fois
par année close**, `TAIL_SHADOW kind=total` puis une ligne agrégée par
combinaison d'états effectivement rencontrée (`kind=bucket`, jamais par
tick). `LOOP_OPS post=tail_shadow` mesure également l'appel entier du
shadow. Le champ `TAIL_SHADOW.guard_ops` mesure l'intervalle interne entre
le premier et le dernier relevé d'opcodes : il est une **borne basse** du
surcoût total, car la fin de comptabilité est postérieure à ce relevé.
Les budgets `before_cap` et `after_cap` ne sont **pas** du travail effectué.

## Risques et limites de la validation

1. La sonde consomme elle-même des opcodes de tick. Même sans commande de
   jeu, elle peut déplacer la frontière d'une suspension. Comparer la
   trajectoire sondée à une trajectoire non sondée n'est pas une preuve de
   neutralité ; `crosses` et `LOOP_OPS tail_shadow.tk` servent à quantifier
   cette perturbation. Le premier bucket d'une année alloue une table.
2. `GetOpsTillSuspend` compte des fenêtres de suspension NoAI ; le plafond
   suppose une microtranche de travail pure et bornée, hypothèse non
   vérifiée pour les workers existants. Le budget ne garantit aucune
   commande, progression ou profit. Aucune instrumentation de `step`
   ou lecture profonde de readiness n'est incluse.
3. Une boucle finissant sous 4000 fait un simple comptage `low`; les
   détails de worker, son coût spécifique et la traversée éventuelle
   dans cette branche ne sont pas observés. La table annuelle elle-même
   peut changer les frontières de tick au changement d'année.
4. Les indicateurs C67 sont **des flags**, pas la vérité sur sa queue de
   blocs ou les appels réels. La file réactive ne révèle que sa longueur
   O(1), sans inspecter chaque intention.
5. Tests source statiques et comparaisons de formules seulement : ils
   ne compilent pas Squirrel et ne prouvent aucune innocuité runtime.
   Aucun outil de compilation Squirrel n'a été trouvé via `Get-Command`
   sur cet hôte. Aucun Docker, smoke moteur, A/B, commit ou push.

Avant exploitation : compiler sous runtime NoAI 15.3 dans une campagne
**séparée**, avec `probe_loop_ops=1,probe_tail_shadow=1` sur code figé,
comparer `TAIL_SHADOW`, `LOOP_OPS tail_shadow` et logs santé. C'est une
sonde de plafond théorique, et **pas** une justification pour déplacer
des tâches vers le reliquat ni pour réactiver `air_fleet_dirty_sched`.

## Vérification complémentaire du prime (12/10)

Premier smoke moteur isolé (hors A/B) `bench_v2.py` 1 graine 42 × 1 an,
`probe_loop_ops=1,probe_tail_shadow=1` : **partie terminée `OK`**, score
180, valeur 415 468 £, 19 véhicules et 25 gares. Le moteur compile et
exécute donc la sonde. Un an de jeu n'atteint pas la clôture de 1970 dans
les logs `TAIL_SHADOW` ; prévoir au moins **deux ans simulés** pour lire
le bilan 1970. Ce smoke ne mesure ni coût comparatif ni innocuité.

Campagne diagnostique préenregistrée **sans portée d'adoption** :
`p0_tail_shadow_ab42_2y_20261012`, 42 × 2 ans, deux duels C66.3 sur
le même code figé, AAAHogEx-115 local copié dans le répertoire ignoré
`ai/AAAHogEx-115` du stage pour les besoins du harnais uniquement.
Référence `OpexAI[probe_loop_ops=1,probe_tail_shadow=0]`, variante
`OpexAI[probe_loop_ops=1,probe_tail_shadow=1]` ; mêmes autres défauts,
avec `--script-debug`, `--cpus 10 --memory 8g --max-workers 2`, une
seule campagne. Lire santé et logs `TAIL_SHADOW` 1970, contrôler le coût
intrinsèque `LOOP_OPS post=tail_shadow`, franchissements et éventuelle
divergence des décisions. La règle C66 `gain_short` 4 % / garde 5 %
reste purement administrative pour cette **taille non qualifiante** ;
aucun verdict de porte A/B n'en sera tiré.

Exécution : **2/2 duels complets et sains** pour la graine 42 sur deux ans.
Bundle `de399dfde5d82e673acf484bd92922942ae9a48f6f14cb8cb6a1a0e047c47d50` ;
verdict C66 `diagnostic_only`. Profit annuel variante − référence
**+109 404 £** et valeur +6,566 % (une graine, fluctuation de trajectoire,
ni gain attribuable à la sonde ni neutralité prouvée).
La clôture `TAIL_SHADOW y=1970` de la variante révèle 729 boucles,
dont 290 avec reliquat inférieur à 4 000 et 439 au-dessus. Plafond
arithmétique avant la garde **1 876 723 opcodes**, après **1 808 200**,
dont **zéro opcode effectivement récupéré**. 83 observations au-dessus
du seuil sont classées `UNKNOWN`, aucune `READY` ; 356 sans état actif
dans les buckets au-dessus du seuil, plus 1 avec intention réactive.
Le noyau mesuré de la garde coûte 60 927 opcodes en cumulé, tandis que
le registre entier `LOOP_OPS post=tail_shadow` impute **103 735** opcodes
et **quatre ticks franchis**. La mesure `TAIL_SHADOW crosses=0` interne
à la garde ne couvre pas l'intégralité de la fermeture du hook, comme
prévu : les quatre ticks sont donc un vrai avertissement de perturbation.

Pour vérifier la robustesse et les exercices 1970–1973, second diagnostic
**préenregistré** : `p0_tail_shadow_ab5_5y_20261012`, mêmes deux bras et
réglages que ci-dessus, graines **42, 100, 999, 1234, 5678**, horizon
**cinq ans** (pour clôturer l'exercice 1973), `--script-debug`, dix
workers et dix CPU locaux, 8 Go. Son seul but est de mesurer le coût
du hook, les distributions par graine/année et la fréquence de
divergence économique induite par la télémétrie. Même si les résultats
sont favorables, cette sonde n'est **pas une optimisation** et ne peut
être adoptée comme micro-worker. Les anciennes expériences d'ordonnancement
et de politique AIR restent fermées.

**Campagne 5×5 terminée et saine (10/10 duels, 5/5 paires).**
Même bundle `de399dfde5d82e673acf484bd92922942ae9a48f6f14cb8cb6a1a0e047c47d50` ;
manifeste `61ce7229dfc89c786a511aea85a3932eb2e29e2e4c32b117e47316dfc8bd5a10`.
Verdict brut `diagnostic_only`. Le delta profit terminal à cinq ans
est +112 166 £/an (4 victoires, 1 défaite), IC95 bootstrap
**[−7 695 ; +207 781] £/an**, valeur +9,14 %. La télémétrie a modifié
des trajectoires ; ce résultat descriptif ne prouve ni neutralité ni
amélioration. Les contrôles annuels ont été relus indépendamment avec
`sweeps/analyse_tail_shadow_early4.py` (worktree principal) ;
preuve `evidence/review/opcode_early4_20261012/tail_shadow_ab5_5y.json`.

| Exercice | Coût total du hook (opcodes/graine) | Ticks franchis/graine | Cap après garde (M/graine) | Dont état `UNKNOWN` (M) |
|---|---:|---:|---:|---:|
| 1970 | 134 037 | 5,0 | 2,294 | 0,978 |
| 1971 | 115 896 | 2,2 | 2,198 | 0,179 |
| 1972 | 99 002 | 3,8 | 1,747 | 0,574 |
| 1973 | 56 894 | 1,0 | 0,995 | 0,569 |
| **Total quatre exercices** | **405 829** | **12,0** | **7,233** | **2,300** |

Les plafonds du tableau sont **une caractéristique des trajectoires
sondées**, non une nouvelle correction des **6,093/1,768 M** du profil
historique, qui suit d'autres trajectoires. L'état `UNKNOWN` signale
uniquement un worker, une recherche, une intention ou C67 présent,
sans prouver que la micro-tranche est exécutable. **0 opcode worker
récupéré** dans tous les cas. Les 7,233 M restant après garde incluent
**4,933 M sans worker ou autre intention active** à ces instants.

Le coût mesuré d'environ 0,406 M sur quatre ans est réel au niveau des
fenêtres `LOOP_OPS` ; **12 ticks ont été franchis en moyenne par la sonde**
alors que le compteur `crosses` interne à la garde les sous-estime.
Une stratégie de récupération future doit démontrer un rendement net
supérieur à son propre coût, un tick inchangé, aucune famine des tâches
prioritaires et un A/B complet ; cet essai ne valide pas une telle
stratégie.
