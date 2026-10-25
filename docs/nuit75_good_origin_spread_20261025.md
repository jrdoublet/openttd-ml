# N75-GSP — deuxième fenêtre physique pour une origine GOOD déjà raccordée

## Statut au 25 octobre 2026

**Prototype code et contrats uniquement — aucun Docker, smoke, exposition
ni porte A/B.** Worktree indépendant
`.worktrees/nuit75-good-origin-spread-v1`, point de départ
`83e436cc` et copie des **sources expérimentales GOOD** du worktree
`.worktrees/nuit75-good-source-variant` (le source original reste
strictement inchangé). Pas de commit, push, merge ni changement
de défaut. Ne pas substituer ce code aux bundles déjà gelés des six
portes A nocturnes en cours.

## Signal motivant, sans causalité revendiquée

GOOD `good_source_rail_join=1` produisait un gain de
**+127 819,45 £/an sur 40×10**, 28V/12D, p=0,05481
et IC95 positif [+18 683 ; +239 499] £, mais échouait
le prérequis de +4 % (seuil +170 929) : **fail_primary**.
Diagnostic GOOD seed100 10 ans : 28 tentatives et seulement
6 lignes physiquement construites, 16 échecs `SITEAB`.
Cela suggère un potentiel de constructibilité, **mais SITEAB
peut signifier deux extrémités impossibles** : aucun gain ≥4%
n'est prouvé et la proportion réparable n'est pas connue.
**Mise à jour après préparation :** le nouveau GOOD A40×5 multimodal
est terminé, **40/40 sain mais `fail_primary`**, delta de profit Opex
**−40 727,5 £/an**, Wilcoxon p=0,091824, IC95
[−101 369 ; +21 796], valeur −2,176 %. Il ne valide donc pas
le prédécesseur sur l'horizon 1974 ; la motivation du fallback
GSP reste seulement le goulot physique `SITEAB` observé à dix ans.
**Aucune extrapolation d'un gain ≥4 % ni porte A/B de GSP n'est justifiée
sans exposition physique et coût de la branche V264 mesurés.**

## Mécanisme incrémental exact, sans nouvelle option

Le paramètre expérimental GOOD existant devient `0/1/2` :

- **0 OFF** : comportement de master, défaut easy/medium/hard/custom
  toujours 0 ; aucune branche GOOD activée.
- **1** : GOOD classique, gare origine réutilisée uniquement par
  `OpexJoinPlatformPlans` (quai parallèle producteur GOOD) ;
  **comportement précédent identique**.
- **2** : identique à 1, mais uniquement si **aucun quai
  parallèle physiquement joint ne produit GOOD**, essaie le
  moteur existant `OpexV264SpreadJoinPlans` pour un quai joint
  dans la limite configurée de `station.station_spread`,
  avec respect de `station.distant_join_stations`, StationID réel,
  test `AIRail.BuildRailStation` sous `AITestMode`, production
  `OpexRailPlatformCargoValue(... wantProduction=true)>0`
  pour **chaque** quai proposé, et contrôles d'exécution GOOD
  initiaux inchangés (`OpexGoodSourceStationLive`,
  `OpexGoodSourcePlanSafe`, fonds, A*, C77/C80).

La recherche ne crée **jamais** de gare A indépendante. En cas
d'échec des deux types de jonction, le constructeur historique
rend SITEA/SITEAB et ne déroge à aucune restriction financière.
L'appel V264 est entièrement ignoré pour le paramètre 0 ou 1.
À 2, sa fréquence est limitée aux candidats GOOD explicitement
choisis pour chantier qui n'ont **aucun quai producteur parallèle** ;
le coût d'opcodes de cette branche reste à mesurer. Trace facultative
`N75_GOOD_SPREAD phase=siteA scanned=... productive=...`
quand `DECISION_LOG` est activé.

## Vérifications hors moteur

Tests spécifiques `sweeps/test_n75_good_origin_spread.py` :
garde 0/1/2 et quatre défauts OFF, lecture unique de l'option,
appel fallback borné, production GOOD positive, restrictions
du moteur V264 et comparaison des octets EXACTS aux SHA du
prédécesseur GOOD pour `info.nut`, `settings.nut`,
`builder_rail.nut`. `sweeps/n75_good_spread_legacy.py`
soustrait **uniquement la différence exacte de GSP** pour protéger
ces SHA dans les contrats PO01C, sans rebaseline.
`test_v264_convergent_freight` isole la branche historique B
pour ne pas confondre sa recherche avec le nouvel appel côté A.
Suites GOOD/PO01C/V276/V264/V178/V190 : **100/100 PASS**,
`git diff --check` PASS.
Contrôle supplémentaire au suivi de file : **175/175 tests hôtes PASS**
sur 15 modules exécutés ensemble (GOOD, GSP, V264, V178, V190,
C77, C80, V252, PO01C, V276, V284 et contrats de réglages),
sans Docker, `git diff --check` OK ; cet effectif unique remplace
les comptes partiellement recoupés des essais précédents.

Tests complémentaires Save/Load, C77/C80, finance et script
Squirrel en jeu nécessaires avant toute exposition.
**Aucune adoption ni lancement de benchmark n'est demandé
tant que la file nocturne en cours n'est pas achevée**.
