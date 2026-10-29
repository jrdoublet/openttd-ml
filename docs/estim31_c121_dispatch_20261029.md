# ESTIM-31 — sélection des moteurs AIR, version expérimentale isolée

## Défaut et correction

`OpexC121InitialEngineUpperScore` n'est pas une borne supérieure prouvée du
score effectivement maximisé : le rendement AIR calibré `k_R.air`, la flotte
d'ouverture et les règles de charge peuvent rendre la comparaison fausse.
Sur une route réelle de la graine 42, le candidat 223 avait un score 2 983,30,
supérieur au 228 (2 767,38), mais son ancienne « borne » n'était que 2 433,01.
Un `break` classé par cette valeur pouvait donc ignorer le moteur gagnant.

L'intégration de cette branche conserve **sans modification** les fonctions
historiques `OpexC121ScanRoutePlaneEngines` et `OpexC121ChooseRoutePlane`.
Deux copies expérimentales suffixées `FullScan` évaluent tous les moteurs
admissibles, sans `break` par `upperScore`. Le dispatch n'est activé qu'une fois
à la lecture du réglage `estim_unifie` si son bit 1 est à 1. L'OFF n'exécute
aucune condition supplémentaire dans la boucle de sélection historique.
Le réglage public et les constantes économiques par défaut sont inchangés.

Cette preuve est **structurelle et locale au scan** : aucun coefficient AIR
ne peut déclencher un élagage supprimé. Le raccourci `C121_GE` demeure actif :
après huit choix identiques, il peut éviter les scans intermédiaires puis
réévaluer périodiquement tous les 32 choix. L'argmax sur *chaque* route n'est
donc pas garanti lorsque ce raccourci est actif ; le désactiver a dégradé le
ratio relatif sur le premier 5×5 et augmenté les opcodes de 40 %.

## Reproductibilité et validation effectuée

- Source figée du diagnostic :
  `results/eb3_estim31_air15_rail10_w15_root_20261029`.
- Générateur prototype : `results/estim31_engine_dispatch_prepare_20261029.py`.
- Comparateur : `results/estim31_engine_dispatch_compare_20261029.py`.
- `probes=2` : parité **350/350** mesures OFF sur les cinq graines
  42, 100, 7, 999, 2026, cinq dates (1970–1974), deux compagnies et sept
  métriques dont les opcodes partiellement observés.
- Save/Load réel, graine 999, `estim_unifie=31`, `eb14_progressive=3`,
  `probes=258` : `status=OK`, 13 sauvegardes par phase,
  `LOAD_RECONCILE` après chargement du 01/07/1970. Une compagnie fantôme
  non IA apparaît à la reprise dans le harnais ; les statistiques OpexAI
  restent utilisables, mais une parité parfaite après Save/Load n'est
  **pas** démontrée.
- Tests `sweeps/test_estim31_c121_dispatch.py` : 4 OK ; suite C121 : 102 OK.

Sur la première expérimentation appariée **5×5** (non concluante
statistiquement), le scan corrigé produit fin 1974 **2 471 266 £/an**
de `profit_year` moyen OpexAI contre **2 970 163 £/an** pour AAAHogEx,
soit **83,203 %**, contre **61,323 %** dans le bundle d'élagage historique.
Le gain de profit OpexAI est **+508 786 £/an** (5/5 graines). Ces chiffres
portent sur ESTIM31/EB14=3 avec AIR initial 1,50, RAIL 1,00 et poids 15,
pas sur toutes les configurations ni sur la branche historique sans EB14.

### Qualification 40×5, décembre 1974

Campagne `estim31_engine_dispatch_air15_40x5_20261029`, **40/40 duels sains**,
8 workers, carte 256², `probes=2`, année 1970–1974. Les résultats ci-dessous
proviennent du JSONL filtré sur `duel_policy_id` : le tableau imprimé en
console appartient uniquement à la référence OFF. Calcul et bootstrap 20 000
tirages reproductibles dans `results/estim31_dispatch_40x5_analyse_20261029.py`.

| Politique | Profit OpexAI | Profit AAAHogEx | Ratio des moyennes |
|---|---:|---:|---:|
| OFF historique | 2 856 233 £/an | 3 001 621 £/an | **95,1563 %** |
| `estim_unifie=31`, `eb14_progressive=3` avec dispatch, AIR 1,50 / RAIL 1,00 / poids 15 | 2 627 711 £/an | 2 891 442 £/an | **90,8789 %** |

La variante **ne dépasse pas OFF** : −4,2774 points de ratio de profit,
IC bootstrap 95 % apparié [−10,797 ; +2,051] points ; Opex perd en propre
**228 522 £/an**, 13 graines gagnantes / 27 perdantes. L’ancien verdict
`fail_primary` est une sortie du banc, **pas** un veto du nouveau protocole
utilisateur : seul le pourcentage relatif Opex/AAA détermine le classement.

Les 40 cartes montrent 58,675 avions OpexAI en moyenne contre 66,525 en OFF,
32,425 aéroports contre 33,675 et 31,975 villes avec au moins un aéroport
OpexAI contre 33,0. Le rail progresse de 23,9 à 25,7 trains ; le cash recule
de 2,395 M£ à 1,242 M£. Comptage des moteurs dans les 40 flottes :
223 **850→879**, 228 **428→360**, mais les flottes incluent les acquisitions
et renouvellements ; ce n'est pas une mesure isolée du premier achat.
Les opcodes partiellement observés Opex passent de 54,048 M à 47,209 M ;
le champ `observed_opcode_complete_cpu=false` interdit d'en déduire une
consommation CPU absolue. Les dépenses exactes et les rollbacks ne sont pas
entièrement observables dans ce banc non intrusif ; ne pas assimiler les
devis ou `air_vehicle_book_value` à des mouvements nets de trésorerie.

### Non-régression de la branche d'intégration

La suite générale `python -X utf8 -m unittest discover -s sweeps -p
'test_*.py' -q` a ensuite passé **3 128 tests**, 6 ignorés et 2 échecs
attendus. Les projections historiques `sweeps/estim_unifie_off_lots.py`
et `sweeps/air_site_ranked_legacy.py` enlèvent explicitement le seul append
C121, sans rebâtir les fixtures aveuglément ; l'encodage LF a été figé
sur le source C121 pour préserver les empreintes historiques. Le test B6
reconnaît le nouveau cas V161 de renfort marginal déjà présent en HEAD.
La dépendance locale `ai/AAAHogEx-115/info.nut`, absente du worktree mais
présente dans le dépôt principal, a été copiée **sans être versionnée** pour
les tests d'intégration.

La recherche combinatoire AIR/RAIL n'est pas terminée. Les tests ne justifient pas de changer
le défaut `estim_unifie=0`, et **le seul critère économique de classement est
le ratio de `profit_year` OpexAI/AAAHogEx-115 fin 1974** ; valeur de société,
trésorerie, constructions et opcodes sont explicatifs, pas éliminatoires.

## Limites d'intégration

Les deux copies des fonctions représentent **328 lignes additionnelles**.
La duplication est volontaire afin de préserver exactement le chemin OFF,
mais exige une synchronisation des corrections futures entre les deux
implémentations, idéalement par génération contrôlée ou tests de structure.
Cette branche isole son code du dépôt `master` partagé, où d'autres agents
modifient simultanément `air_economics_c121.nut`, `settings.nut` et
`docs/taches.md`. Aucun changement concurrent n'est inclus ici.
