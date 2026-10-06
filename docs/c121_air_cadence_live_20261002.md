# C121 AIR — cadence live 1→2 et arbitrage portefeuille

## Objectif

Rendre C121 AIR viable par la cadence, sans réouvrir immédiatement la fonction
économique AIR. L'objectif stratégique reste le rattrapage d'AAAHogEx : le
`profit_year` Opex est un moyen, la `company_value` n'est pas le critère principal.

Chaîne étudiée : détection live → publication renfort → portefeuille → financement
→ exécution → observation → réévaluation. Les expériences ci-dessous ne modifient
pas `2→3+`, la cible C121, K_dec ni K_pass sauf instrumentation passive explicite.

## Seuils d'âge : piste close

Les seuils 60/90/120/150/180/240 jours ont été explorés. Le 150 jours 20×10
reste qualifié sur 19 paires valides : Δ `profit_year` +2,1 k£/an, médiane
−5,8 k£, 9/10, et Δ gap Opex−AAA +3,4 k£/an. L'effet physique est réel
(plus de véhicules/slots/villes), mais l'effet économique est nul. Le repair
seed4096 reproduit l'échec référence avec un bundle différent : ne pas recomposer
artificiellement un 20/20. Ne plus chercher un « nombre de jours magique ».

## Live evidence `balanced90`

Le shadow réutilise les fenêtres C117 déjà calculées, sans second scan avion.
`balanced90` exige une fenêtre d'environ 90 jours, au moins 50 jours observés,
2 voyages, profit récent positif et charge≥40 % ou attente normalisée≥50 % ;
l'âge sert seulement d'anti-bruit. Le shadow 5×3 est sain : 841 événements,
135 lignes, 64 lignes retenues par `balanced90`, coût ajouté ~600–650 opcodes
par publication.

Le premier causal live `r1` est invalide pour l'intention : le signal live y
remplaçait la garde C121 et pouvait retarder un 1→2 baseline. Le correctif actuel
fait du live un **early override seulement** : si le signal live est faux, la
garde historique (`age>=2`, `lastProfit>0`) reprend la main.

### Corrected live 5×6 `r2`

`results/c121_first_live_growth_5x6_20261001_r2.json`, 5/5 paires saines :

- Δ `profit_year` : **−19,5 k£/an** moyen, 2/3 ;
- Δ gap Opex−AAA : **−10,2 k£/an** moyen ;
- `company_value` : +134 k£ moyen, secondaire ;
- véhicules primaires : +6,8 ; slots/villes Opex : −1,0.

Trajectoire moyenne du Δ gap : +4 k (1970), +31 k (1971), +284 k (1972),
+59 k (1973), −275 k (1974), −10 k (1975). Le signal live apporte donc un
gain précoce clair puis s'érode.

## Fenêtre phase4

`results/c121_first_live_growth_phase4_5x6_20261001_r1.json` : live 1→2 limité
aux quatre premières années de jeu, comparé au C121 base.

- Δ `profit_year` : **−112,3 k£/an**, 0/5 ;
- Δ gap Opex−AAA : **+265,6 k£/an**, **5/5** ;
- Δ `company_value` : +24 k£ moyen ;
- slots Opex : −2,0.

Selon l'objectif utilisateur, ce résultat n'est pas rejeté sur le seul profit Opex.
Il est actuellement le meilleur signal de rattrapage AAA de cette famille, malgré
une expansion territoriale Opex plus faible et une forte variance par graine.

## Priorité AIR après renfort live

### Garde large : rejet mécanique

La première formulation décalait un renfort live si la **première** nouvelle
ligne AIR située plus bas dans le classement était finançable maintenant mais ne
le serait plus après achat du renfort. Causal 5×6 :

- Δ `profit_year` −57,9 k£/an ;
- Δ gap −489,4 k£/an ;
- Δ slots +0,2 seulement ; Δ lignes AIR −0,2.

Le diagnostic montre 96 états `displaced=1` dans le bras priorité, mais seulement
12 où l'AIR était réellement le projet immédiatement suivant. Distance médiane
fleet→AIR : 6 rangs ; 51/96 dépassaient 5 rangs. Le garde reportait donc souvent
une flotte sans réserver le capital ni garantir que l'AIR serait atteint.

En plus, le premier causal n'était pas propre du point de vue cadence : seed5678
divergeait sans aucun `displaced=1`, seed42 avant sa première exposition. La simple
évaluation supplémentaire du toggle pouvait changer les opcodes avant action.

### Garde immédiate opcode-paritaire

Le code courant calcule maintenant la condition complète dans les deux bras quand
le shadow est actif. La divergence ne commence qu'au vrai `continue` causal :

1. `displaced=1` ;
2. `nextRank == rank + 1` ;
3. `builtCount == 0`.

Contrôle de parité seed5678 ×3 ans, sans opportunité immédiate : résultats
strictement identiques entre OFF/ON (`profit_year`, valeur, score, véhicules,
gares). 18 tests ciblés C121 cadence sont verts après ajout du shadow K_pass.

`results/c121_first_live_air_priority_immediate_5x6_20261001_r2.json`, 5/5 :

- Δ `profit_year` **+29,3 k£/an**, 4/5 ;
- Δ gap **+28,4 k£/an**, 4/5 ;
- Δ `company_value` +62,0 k£ ;
- Δ slots/villes Opex +0,2 ;
- Δ lignes AIR finales −1,4, avions AIR −0,8.

Signal modeste mais propre : la garde immédiate évite la régression du garde large,
sans démontrer une vraie accélération territoriale.

### Phase4 + garde immédiate

`results/c121_first_live_phase4_air_priority_immediate_5x6_20261001_r1.json`,
phase4 identique dans les deux bras, seule différence effective `air_priority` 0→1 :

- Δ `profit_year` vs phase4 : **−19,8 k£/an** ;
- Δ gap vs phase4 : **−7,4 k£/an** ;
- Δ slots +0,4 ; Δ lignes AIR −3,4.

Pas de synergie démontrée. Conserver phase4 et priorité immédiate comme hypothèses
distinctes ; ne pas les empiler pour un 20×10.

## K_pass : où s'arrête réellement la passe ?

Les expériences de priorité montrent qu'économiser du cash ne garantit pas que le
projet AIR suivant soit exécuté. Le diagnostic suivant a donc porté sur K_pass /
fin de passe, d'abord sans décision modifiée.

Nouveau setting OFF : `c121_kpass_shadow`. À chaque `break` C75/K_pass il logue :

- raison (`k_pass`/`cash`), `next_mode`, rang, finance, K_pass et capital disponible ;
- pour un fleet, identifiant de ligne ;
- jusqu'à cinq projets suivants sous forme `rang=mode:finance:finançable`.

### Shadow K_pass 2×3 : défaut structurel confirmé

`results/c121_kpass_shadow_2x3_20261002_r1.json`, seeds 42/100, 3 ans,
4/4 parties complètes. Bundle
`4183399a8c83ae6d2381496ceba616d8145d29ae6fa22b19f1694f3f0bf2abe9`,
manifeste
`86b86e4c523fc494722b033294cb1c95370aad040f48d1e8b324fceb9b652d75`.

Le delta économique du shadow n'est **pas interprété** : la journalisation ajoute
des opcodes. L'exposition structurelle est en revanche nette :

- 59 arrêts de passe observés : 28 `k_pass`, 31 `cash` ;
- parmi les 28 `k_pass` : 8 blockers `fleet`, 4 `air`, 14 `rail`, 2 `road` ;
- sur les 8 blockers `fleet`, **6/8 (75 %) ont un projet AIR finançable dans les
  cinq rangs suivants** ;
- seed42 : 3/5 blockers fleet avec AIR finançable ; seed100 : 3/3.

Le mécanisme est donc réel : un renfort `fleet` peut arrêter toute la passe sur
K_pass alors que la trésorerie permettrait d'exécuter une nouvelle ligne AIR plus
bas dans le portefeuille.

### Correctif causal minimal `c121_kpass_air_continue`

Nouveau toggle expérimental OFF par défaut : lorsqu'un projet `fleet` ferait
`break` pour raison `k_pass`, chercher uniquement dans les cinq rangs suivants un
projet AIR encore live et déjà finançable. S'il existe, **ne pas acheter de force
le fleet** : sauter seulement ce blocker (`continue`) et laisser la logique C75
normale poursuivre le scan. Le look-ahead est calculé avant le toggle afin que la
divergence OFF/ON commence au vrai `continue` causal.

Tests ciblés après ajout : **21/21 verts** dans Docker. C115, cible C121, logique
`2→3+`, moteur et économie AIR restent inchangés.

Implémentation locale : settings/globals dans `info.nut`, `globals_pre.nut` et
`settings.nut`; `task_projects.nut` contient le shadow
`OpexC121KPassShadow()` et le helper causal borné
`OpexC121KPassFundableAirAhead()`. Les contrats correspondants sont dans
`sweeps/test_c121_air_economics.py`.

#### Causal 2×3

`results/c121_kpass_air_continue_2x3_20261002_r1.json`, 4/4 parties complètes,
bundle `766248c89c877cf1c2ecc868a4cedee94388e653952c5ca4392e8704b6a1bd79`,
manifeste `5980b95db80667e39837cf8d6d8303dda33fc8b6d54d1ea1a52181febd9741c7`.

- seed42 : aucune action causale, OFF/ON strictement identiques ;
- seed100 : deux `continue` successifs franchissent deux blockers fleet devant
  le même AIR (`fleet_cap=39 964`, `air_cap=40 964`, `K_pass=14 144`,
  `available=57 734`) ;
- seed100 : Opex `profit_year` +14,3 k£/an, +2 véhicules ; AAA +63,0 k£/an ;
  le gap Opex−AAA se dégrade donc d'environ −48,6 k£/an ;
- moyenne 2 graines : Δ Opex `profit_year` +7,2 k£/an.

Ce screening montre que le correctif agit au bon endroit et conserve la parité
quand il n'agit pas. Malgré le signal de gap défavorable, l'utilisateur demande
explicitement un 5×6 car ce comportement est considéré comme un défaut de C121 à
corriger indépendamment de son statut comme levier de rattrapage.

#### Causal 5×6 demandé par l'utilisateur

Deux tentatives de lancement ont échoué avant production d'un artefact final à
cause de Docker Desktop (`DockerDesktopLinuxEngine ... containers/create: EOF`).
Le daemon répondant de nouveau, le même protocole a été relancé sans changement.
La troisième tentative est complète :

`results/c121_kpass_air_continue_5x6_20261002_r1.json`, 10/10 parties, seeds
42/100/999/1234/5678, 6 ans, 10 workers / 10 CPU. Bundle final
`fcd45ded504ee7ffd7810b69d857fcddce725fd922254bea23db17a5c171d6a9`,
manifeste `5eb1476070f119d7b5e48d1b774b5cc96f717cf9876a03ef26dbecc81452f1ae`.

- Δ Opex `profit_year` : **+42,2 k£/an** moyen, médiane **+18,2 k£**,
  3/2, p signes=1 ; ratio des moyennes **+4,51 %** ;
- IC95 normal du delta : [−83,4 ; +167,9] k£/an ; IC95 Student-t
  [−135,7 ; +220,2] k£/an ;
- `company_value`, ratio des moyennes : **−1,74 %** ;
- Δ gap Opex−AAA : **−156,5 k£/an** moyen, médiane **−247,9 k£**,
  1/4, p signes=0,375 ;
- gap moyen référence : −3,575 M£/an ; variante : −3,732 M£/an ;
- exposition causale : **50 `continue`** au total — seed42=7, seed100=26,
  seed999=9, seed1234=5, seed5678=3 ;
- deltas Opex / gap par graine : seed42 −61,2 / −625,0 k£ ; seed100
  +104,5 / −247,9 k£ ; seed999 +18,2 / **+841,4 k£** ; seed1234
  −105,3 / −179,1 k£ ; seed5678 +255,0 / −572,0 k£ ;
- structure finale moyenne : slots Opex **+0,4**, villes Opex **+0,4**,
  véhicules primaires **−5,4**, avions AIR **−5,8**.

Interprétation : le défaut K_pass est confirmé et le correctif augmente Opex en
nominal sur ce petit échantillon, mais il ne constitue pas à lui seul un levier de
rattrapage AAA : quatre graines sur cinq dégradent le gap final. **Ne pas confondre
correction de logique et validation stratégique.** La correction reste une piste
d'intégration C121 voulue par l'utilisateur ; aucun changement de défaut n'est
effectué ici et aucun 20×10 n'est lancé.

## Piste suivante déjà auditée : C69 / K_dec à froid

`OpexC121ProjectHasRealization(project)` considère actuellement un projet `fleet`
C121 comme « réalisé » dès que la ligne porte `c121MarginalProfit` et
`c121MarginalRevenue`. Or ces champs existent dès le cold-start post-build ; le
test ne regarde pas `c121MarginalSamples`.

Conséquence dans `projects_selection.nut` :

```text
fleetExemptDecision = C69_FLEET_EXEMPT && mode=fleet
                      && !OpexC121ProjectHasRealization(project)
```

Un fleet C121 `samples=0` perd donc déjà l'exemption historique et peut recevoir
`K_dec` comme dénominateur de score avant toute observation réelle. Ce mécanisme
peut retarder un premier renfort indépendamment de `balanced90`.

Le builder confirme explicitement que `samples<=0` est le **cold-start** : les
marges viennent encore de la prédiction initiale, éventuellement recalibrée par
le facteur de réalisation appris. Pourtant `OpexC121ProjectHasRealization()` ne
regarde pas `c121MarginalSamples` et considère déjà la marge comme réalisée.

Ne pas corriger causalement ce point dans le même lot K_pass. Prochaine sonde :
shadow K_dec comparant score courant et score contre-factuel « exemption fleet
tant que samples=0 », avec séparation cold/warm, inversions de rang et changement
éventuel de tête de portefeuille.

## Décisions / non-décisions

- C121 et les nouveaux settings cadence restent OFF par défaut, sauf décisions
  indépendantes déjà documentées ailleurs.
- Aucun 20×10 cadence supplémentaire à ce stade.
- Ne pas retuner `balanced90` ni un âge fixe sans nouvelle preuve.
- Ne pas modifier simultanément `2→3+`, K_dec, K_pass et live evidence.
- Le `fleet` qui coupe la passe K_pass devant un AIR finançable est désormais
  considéré comme un **défaut de logique C121 à corriger** ; le 5×6 montre toutefois
  que sa correction n'est pas, à elle seule, une stratégie de rattrapage AAA.
- Prochaine investigation cadence : cold-start K_dec en shadow, sans causal tant
  que l'exposition/rang n'est pas mesurée.
- C115 reste le témoin historique/opérationnel temporaire.
- Aucun commit/push réalisé dans ce lot.
