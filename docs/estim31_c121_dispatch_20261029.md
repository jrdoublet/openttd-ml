# ESTIM-31 — sélection des moteurs AIR, version expérimentale isolée

> **Statut actuel (30/10) :** diagnostic et branche expérimentale datés
> du 29/10. Le correctif FullScan C121 a ensuite été intégré dans le
> bundle **réellement élu** à dix ans et poussé comme défaut
> `estim_unifie=31` sur `origin/master` (`2429d175`). La présente fiche
> reste utile pour la cause d'élagage, mais ses conclusions intermédiaires
> « non adopté » ne prévalent pas sur la [qualification finale](estim31_phase_combinatoire_20261030.md)
> et le [contrat C121](estim31_default_c121_verified_20261030.json).

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

**Rapprochement financier 1974 :** le résultat annuel moyen Opex passe de
2 856 233 à 2 627 711 £, la variation de caisse entre décembre 1973 et
décembre 1974 de **+1 562 187** à **+692 603 £**. Aucune variation de dette
dans cet exercice. Le résidu `profit_year + variation_dette − variation_caisse`
se déplace de **1 294 046** à **1 935 108 £ par compagnie**, soit
**+641 062 £ d'emplois nets hors résultat non attribués**. Ce résidu ne
constitue pas un total de dépenses de flotte, de statues, ni d'aéroports ;
il contient aussi les flux de vente/crédit, les remboursements et les postes
non instrumentés. Sur un autre bundle ESTIM31+EB2+load25, la sonde C63
avait observé 773 statues contre 227, mais **ces résultats ne prouvent pas
une cause de nos 641 k£**.

**Stocks de moteurs (40 cartes, décembre 1974) :** Opex moteur 223
**850→879**, 228 **428→360**, 217 **625→814**, 218 **516→224** ; parc
AIR total **2 661→2 347**. Les stocks cumulés ne distinguent pas acquisitions,
ventes, remplacements, ni appareils en transfert. Les journaux moteur du
40×5 (`probes=2`) sont vides ; seules les traces Save/Load seed999
`probes=258` apportent une liste de chantiers partielle, sous un protocole
SOLO non comparable aux duels 40×5.

**Couverture physique aéroportuaire :** Opex 33,675→32,425 aéroports
et **33,000→31,975 villes portant au moins un aéroport Opex** par carte ;
AAAHogEx dans son duel passe de 34,125→35,275 aéroports et de
29,750→30,500 villes avec aéroport AAA. Les villes où AAA possède au moins
deux aéroports et Opex aucun montent de **4,375→4,775 par carte** ; les
villes possédant exactement un aéroport de chaque concurrent diminuent de
22,325→21,550. Ces champs sont calculés par appartenance des stations
`STNN` à une ville, **pas par voyageurs effectivement transportés, bus de
rabattement, catchment, revenu, ou foncier encore constructible**. Les mêmes
champs apparaissent dans la ligne de chaque compagnie du duel : ne pas les
additionner deux fois.

**Save/Load et achats effectifs (cas seed999 isolé) :** les comptes bruts
`n_vehicles=22` et 89 imprimés par le harnais sont les tailles de chunk VEHS,
**pas 22 et 89 avions**. Le décodage physique donne 4 avions (228) au
01/07/1970, puis 31 avions (25×223, 6×228) et 3 trains au 01/07/1971
après rechargement. Les 21 `AIR_BUILD` phase B décrivent 24 avions
initiaux 223 et deux `FLEET_PROJECT grow added=1` décrivent 2 renforts ;
un avion 223 du stock final n'est **pas expliqué exhaustivement** par ces
événements. Un échec `PROJECT_DISCARD ... PLANE error=257 ERR_NOT_ENOUGH_CASH`
et un `AIR_ROLLBACK_DONE immediate=1` sont observés, mais pas les montants nets
perdus/récupérés. Le C121_GE évite réellement le scan sur 19/21 ouvertures
post-reprise (`causal_engine_evals=0`), alors que les autres évaluent 12
moteurs. Le changement de 228 en phase A vers 223 en phase B après recharge
n'est **pas une comparaison causale de moteur** : la reprise crée une
trajectoire différente et une compagnie fantôme du harnais.

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
