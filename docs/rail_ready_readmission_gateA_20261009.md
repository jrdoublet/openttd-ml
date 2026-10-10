# P0 RAIL — Porte A, réadmission du tracé prêt (09/10/2026)

## Hypothèse et intervention unique

Un A* RAIL primaire préparé peut être posé en début de passe, avant le
portefeuille C69/C70/C77/C118/C120 actualisé
(`task_projects.nut::_consumeResumableRailAtPassStart`). Au cours de la
recherche, une occasion financièrement et économiquement mieux classée
peut apparaître. Au défaut, seul l'AIR défensif C77 obtient déjà un
report d'une passe.

**Variante isolée** : `rail_ready_readmission=1` (défaut `0` sur
toutes difficultés). Lorsqu'une primaire A* non-C121 est prête :

1. Consulter uniquement `_projects.best[0]` (rang global existant, y
   compris priorités intermodales) et sa possibilité de financement sous
   le capital actuel ; calculer également le rang du projet RAIL prêt
   dans le vivier courant.
2. Si la tête est différente, positive, finançable et mieux classée que
   le RAIL préparé, reporter la consommation du tracé **une fois par
   identité de projet concurrent** ; laisser la boucle historique tenter
   les investissements dans son ordre ordinaire.
3. Si ce concurrent reste en tête à la passe suivante, autoriser la
   pose RAIL historique pour éviter l'affamement par un chantier
   non constructible. Partager le report existant C77 (pas de
   deuxième report injustifié pour la même AIR).
4. Rien ne change au nombre de recherches A* (N=1), au budget, aux
   décisions de préparation C121, à la réservation de caisse, ni à
   l'exécution finale de `_consumeRailSearch`. L'état
   `readyReadmissionHeadKey` est transitoire et réside uniquement
   dans l'état de recherche, non restauré au Load.

Ce n'est **pas encore** une réadmission stricte de toute opération
capitalisée. Un rail absent du TOP64 peut encore être construit à la
passe suivante après avoir laissé sa chance au concurrent. Une priorité
du catalogue n'établit pas une constructibilité réelle. Il s'agit d'une
intervention minimale et réversible à qualifier avant la migration
générale vers le portefeuille unique.

## Protocole pré-enregistré

- Référence : `OpexAI[rail_ready_readmission=0]`.
- Variante : `OpexAI[rail_ready_readmission=1]`.
- Tous autres réglages inchangés, notamment
  `rail_ready_admission_shadow=0`,
  `rail_economic_preselect=0`, `rail_magic_admission_only=0`,
  `rail_cooperative_n2=0`.
- Même bundle figé pour les deux bras, même jeu partagé AAAHogEx,
  40 graines canoniques, un repeat, 3 années de simulation,
  80 parties au total. Harnais V102, `gain_short`,
  profit annuel Opex variante − référence (dernier exercice).
- Passage A seulement si 40/40 duels complets et sains, Wilcoxon exact
  bilatéral p<0,05, borne basse de l'IC95 bootstrap de la moyenne >0,
  delta moyen >=4% du profit témoin et ratio des valeurs de
  compagnie >=0,95. Une porte A refusée signifie pas de B.
- B (20 graines x 10 ans, `non_erosion`) uniquement si A passe,
  en conservant un paquet de code strictement identifié.
- Le 1970–72 de la porte A peut sous-exposer les recherches A*
  tardives 1973–75 ; ne pas modifier a posteriori le protocole pour
  récupérer un résultat. Une série diagnostique tardive est indépendante
  de la qualification V102.

## État avant lancement

Contrats hôte : `test_rail_ready_readmission.py` 3/3,
`test_rail_ready_admission_shadow.py` 3/3,
`test_rail_origin_reuse.py` 56/56 ; `git diff --check` vert
(avertissement CRLF lié au journal du 08/10 sans erreur).

**Note historique du 09/10, avant les campagnes :** lancement encore en
attente de Docker. Ne pas interpréter la sonde shadow comme une
campagne de cette variante. Le résultat définitif de A2 figure ci-dessous.

## Autopsie de la première porte A (80/80 parties invalides)

- **Smoke** `rail_ready_readmission_smoke_42x3_20261009_r1` :
  2/2 parties saines, bundle
  `93c2ea1b1b6a0c3540f7dd20e542c045df7091395bed34935f9848ae7a47463e`.
- **Porte A** `rail_ready_readmission_gateA_40x3_20261009_r1` :
  80/80 parties `noai_error`, 0/40 paires valides,
  verdict harnais `incomplete`, bundle
  `0e57dcdb43330cb63c8c254d6e6c7fedd809c8043af6018ba36605ce525cc19f`.
  Les 80 fichiers `_engine/*.log` contiennent exactement le même message :
  `the index 'ROAD_QUOTE_COMPONENTS_SHADOW_P0' does not exist`.
  Callstack : `OpexLoadSettings` dans `settings.nut:93` →
  `Start` dans `main.nut:658`. Les deux bras échouent **au démarrage** ;
  aucune décision de la variante RAIL n'a eu lieu.
- **Cause précise, vérifiée dans les deux bundles gelés** : la nouvelle
  lecture `ROAD_QUOTE_COMPONENTS_SHADOW_P0 = AIController.GetSetting(...)`
  apparaît dans `settings.nut` du bundle A mais **pas** dans celui du
  smoke. Dans le bundle A, `globals_pre.nut:55–58` ne déclare que les
  deux flags ROAD précédents. Squirrel exige l'existence du slot global
  pour l'affectation `=` ; `AddSetting` dans `info.nut` n'y supplée pas.
  Le fichier source a été modifié entre les deux gels par un chantier
  ROAD concurrent, donc le smoke sain ne validait **pas** le code gelé
  pour la porte A.
- **Correction isolée** : ajout uniquement de
  `ROAD_QUOTE_COMPONENTS_SHADOW_P0 <- false;` dans
  `globals_pre.nut`, avant `OpexLoadSettings`. Le nouveau test
  `sweeps/test_road_components_shadow_p0.py` exige désormais cette
  déclaration ; 3/3 verts, `test_rail_ready_readmission.py` 3/3,
  `test_road_finance_unbias_p0.py` 5/5, `git diff --check` code 0.
- **Qualification** : la porte A r1 est définitivement **invalide**,
  ni `fail_primary` ni `pass`. Une éventuelle porte A r2 doit utiliser
  un **nouveau bundle figé et unique** pour son smoke et son A/B,
  avec vérification de l'identité source entre les deux ; aucun résultat
  r1 ne peut être recyclé. Les tentatives de relance moteur après la
  correction n'ont pas abouti à la création d'un résultat, donc aucun
  nouveau smoke sain ni verdict économique ne sont affirmés.

## Qualification A2 : porte A terminée, variante rejetée

Le 09/10 au soir, reprise avec un **worktree détaché isolé** :
`.scratch_rail_ready_readmission_A2`. Le dossier contient une copie
figée des arbres `ai/`, `ai_libraries/`, `sweeps/` et le correctif
global ROAD OFF. Il a permis de séparer les deux campagnes des éditions
concurrentes de la racine. Aucune édition du code métier ni remise à
zéro des autres travaux pendant la mesure.

| Contrôle | Smoke A2 | Porte A A2 |
| --- | --- | --- |
| Campagne | `rail_ready_readmission_smoke_A2_42x3_20261009` | `rail_ready_readmission_gateA_A2_40x3_20261009` |
| Graine / années / repeat | 42 / 3 / 1 | 40 canoniques / 3 / 1 |
| Parties saines | **2/2** | **80/80** |
| Paires valides | 1 (diagnostic seul) | **40/40** |
| Empreinte bundle SHA256 | `250223deaebfb849cde5717888fd2b16942de22798c1385158d4a5ad51757ff8` | **identique** |
| Verdict harnais | `diagnostic_only` | **`fail_primary`** |

Référence `OpexAI[rail_ready_readmission=0]` versus variante
`OpexAI[rail_ready_readmission=1]`, tous autres réglages identiques ;
V102 `gain_short`, 40 graines indépendantes, 1970–1972, 10 CPU /
10 workers maximum, une seule campagne Docker simultanément.
Manifests, résultats complets et journaux initialement produits dans le
worktree temporaire A2 sont archivés localement sous
`results/rail_ready_readmission_A2/` ; le manifest 40×5 et le classement
des graines sont également dans `docs/archives/`.

**Métrique primaire, profit annuel 1972, variante − référence :**

- Moyenne **−5 048,98 £/an** (−0,256 % en ratio des profits moyens) ;
  médiane **0 £/an**, 17 victoires / 14 défaites / 9 égalités.
- IC95 bootstrap 20 000 rééchantillonnages
  **[−52 010,15 ; +42 191,08] £/an**, Wilcoxon exact
  bilatéral **p = 0,992295**, test des signes p = 0,7201.
- Profit annuel témoin moyen en 1972 : **1 975 293,15 £/an** ;
  gain exigé `+4 %` = **+79 011,73 £/an**. Les conditions
  Wilcoxon, IC95 > 0 et gain minimal ne sont pas réunies.
- Valeur de compagnie moyenne variante − référence :
  **−8 728,95 £**, ratio des moyennes **0,997515**
  (−0,249 %) ; la garde de perte maximale 5 % est **respectée**,
  mais elle ne compense pas l'échec primaire.

**Trajectoire du profit annuel, moyenne des 40 deltas par graine :**

| Année | Variante − référence (£/an) | V/D/E |
| --- | ---: | --- |
| 1970 | −626,90 | 3/3/34 |
| 1971 | +456,23 | 10/13/17 |
| 1972 | −5 048,98 | 17/14/9 |

Une différence finale n'apparaît pas sur 9/40 graines.
Exemples de fortes pertes en 1972 : seed999 −344 963,
seed424242 −310 572, seed8191 −272 379 ; gains extrêmes :
seed723002 +353 186, seed123456 +268 949.
Ces exemples décrivent la dispersion, pas des mécanismes prouvés.
Il ne faut pas prétendre connaître la constructibilité des concurrents
ou une cause unique de divergence sans traces décisionnelles
supplémentaires ; le résultat économique A2 suffit néanmoins à refuser
cette variante, sans chercher un seuil optimisé a posteriori.

**Verdict : `rail_ready_readmission` rejeté en porte A ; flag OFF sur
toutes les difficultés ; aucune porte B, aucune adoption.**
Le modèle de double voie / second train reste un sujet distinct. Aucune
modification des paramètres physiques/financiers n'est justifiée par ce
banc. Aucun commit/push effectué pour ce correctif.
