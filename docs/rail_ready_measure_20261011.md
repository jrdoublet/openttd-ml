# Mesure de la frontière RAIL terminé → décision → dépense

Édition versionnée du rapport livré le 11 octobre ; aucune partie supplémentaire. Les assertions « aucun commit » et « backlog intact » décrivent l'état **à la fin de la mesure**, avant cette publication autorisée. [Preuves sélectionnées et provenance](../evidence/review/rail_ready_autopsy_20261011/README.md) ; [autopsie historique indépendante](rail_ready_autopsy_20261011.md).

**Décision : sonde non qualifiée. Aucun changement de politique justifié par
ce banc.** Dix duels complets et sains ; le mécanisme est exposé, mais la
neutralité économique n'est pas démontrée et les trajectoires AIR diffèrent.
Ces observations éclairent l'admission des projets ; elles ne prouvent ni
le rendement d'une réadmission, ni un gain d'un score intégrant les opcodes.

## Protocole et préservation

Autorisation utilisateur : « Fais cette mesure ». Pré-enregistrement avant
lancement dans [preregistration.md](../evidence/review/rail_ready_autopsy_20261011/measurement/preregistration.md.gz). Une copie isolée
de l'arbre courant dirty, HEAD `220b5fa75e0bf6b9c5d9167e996b025a464276f8`,
contient l'extension de la sonde et la date/tick du `C121_BUILD` déjà émis.
Cette métadonnée est commune aux deux bras ; le contrôle est différentiel
sur cette copie, sans qualification séparée de son effet commun.

- OFF : `OpexAI[rail_ready_admission_shadow=0]` ; ON : `=1`.
- Unique différence effective de réglage confirmée par le manifeste.
  Readmission, simple_opcode, simple_roi, cooperative_n2 : défauts 0 conservés.
- Smoke : 42×1, deux duels sains, profit et valeur identiques, aucune visite
  primaire à cette frontière pendant cette première année.
- Diagnostic : **42, 100, 999, 746035, 424242 × 5 ans**, une répétition,
  dix duels contre la même AAAHogEx figée. Échantillon ciblé, pas représentatif.
- Image exacte : `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
  Profil local 10 CPU / 8 Go / swap 8 Go / 10 workers ; aucun autre conteneur
  actif constaté avant préparation. Aucun arrêt d'un chantier concurrent.
- **Même bundle smoke et diagnostic** :
  `ea8391ed6a86ccc282be1d87d83e3870d960f9116661e33f843e93b529b7fcaf`.
  Manifeste diagnostic :
  `61b43088b7d41241343db1175209fdf1d25811436514d35b0a97a4224da6b2a7`.
- 5/5 paires complètes, 10/10 duels sains, couverture terminale complète.
  Verdict harnais **`diagnostic_only`**, aucune qualification V102.
- 9 contrats ciblés verts : 3 sonde existante, 2 parseur existant, 4 analyse.
  Les tests Python ne compilent pas Squirrel ; les smokes et duels valident
  son exécution. Deux seuls fichiers Squirrel modifiés dans la copie ; patch
  [snapshot_probe.patch](../evidence/review/rail_ready_autopsy_20261011/measurement/snapshot_probe.patch.gz), jamais appliqué à la production.

**Intégrité : 1 458 hashes de fichiers de production inchangés, statut Git
strictement identique avant/après, source de la copie inchangée après gel.**
Aucun commit/push, aucun défaut modifié. Tous les artefacts sont dans ce
répertoire ignoré `results/`, aucun fichier de backlog parallèle retouché.
L'inventaire initial est [production_before.json](../evidence/review/rail_ready_autopsy_20261011/measurement/production_before.json.gz).

## Neutralité : les critères pré-enregistrés ne sont pas satisfaits

Marge exigée : IC95 apparié entièrement dans ±1 % de la moyenne OFF, pour
profit et valeur. Bootstrap partagé du harnais : 20 000 tirages, graine 0.

| Fin 1974, Opex ON−OFF | Delta moyen | IC95 de moyenne | IC95 relatif | Équivalence ±1 % |
|---|---:|---:|---:|---|
| Profit annuel net | −33 879 £/an (−1,763 %) | [−224 708 ; +113 180] £/an | [−11,697 ; +5,891] % | Non démontrée |
| Company value | −41 450 £ (−0,599 %) | [−357 689 ; +229 476] £ | [−5,168 ; +3,316] % | Non démontrée |

Profit : médiane +1 614 £/an, 3V/2D, Wilcoxon exact p=1.0. Cela ne démontre
**ni perte économique statistique ni neutralité**. Le delta favorable sur
trois graines ne qualifie rien. Les marges n'ont pas été élargies après mesure.

| Graine | Delta profit annuel | Delta valeur |
|---|---:|---:|
| 42 | +71 160 £ | +234 472 £ |
| 100 | −30 219 £ | −153 920 £ |
| 999 | +1 614 £ | −8 048 £ |
| 746035 | +176 210 £ | +343 243 £ |
| 424242 | −388 160 £ | −622 999 £ |

En 1970, les checkpoints de décembre sont identiques. En 1971, les compteurs
AIR mensuels divergent sur **3/5 graines**, dans **19 checkpoints graine×mois**.
Fin 1971 : −0,6 aéroport et +1 avion moyens, profit −1 757 £/an moyen ; ce
ne sont pas des acquisitions territoriales et économiques strictement préservées.

Sur les constructions AIR C121 à même paire OD/occurrence, **18 cas associés
à un projet OFF construit en 1970–1971 sont plus tardifs en ON** (jour ou tick).
Les 92 cas OD non appariés sont des différences de catalogue/construction,
pas 92 retards prouvés. Les renforts ne sont pas horodatés par C121_BUILD ;
ils sont seulement couverts par les compteurs physiques mensuels.

Exemple fiable au début de divergence : graine42, même OD 30→5, même moteur223,
un appareil, construction retardée de **4 jours / 82 ticks** en ON.
Graine746035 : même OD30→24, un tick de décalage dès janvier1971, avant toute
visite primaire observée dans cette graine. La différence comprend aussi les
gardes activées, la remise à zéro télémétrique par passe et la sonde upgrade
existante : ne pas attribuer chaque divergence au seul coût d'une visite ready.

## Coût observé, avec ses limites

| Bloc ajouté au canal primaire ON | N | Médiane | Maximum | Total mesuré | Blocs traversant un tick |
|---|---:|---:|---:|---:|---:|
| Lecture portefeuille + logs à la frontière | 17 | 6 860 ops | 15 103 ops | 127 033 ops | 8 |
| Trace du résultat rail | 17 | 51 ops | 51 ops | 867 ops | 0 |
| Trace d'une tentative concurrente réelle | 22 | 418 ops | 418 ops | 9 004 ops | 0 |

Le bloc de lecture n'effectue aucune commande de construction ni attente
intentionnelle. Sa mesure inclut le balayage du TOP64 existant et le capital
disponible, pas un nouveau modèle économique ou physique. **136 904 ops** au
total sur ces blocs mesurés ; les logs COST, gardes, resets et le canal upgrade
ne sont pas inclus. Aucun compteur global comparable d'opcodes VM purs n'est
disponible : le critère de surcoût global ≤1 % reste **non démontré**. Un petit
volume agrégé n'empêche pas une suspension de déplacer une décision territoriale.
La capacité théorique annuelle n'est pas utilisée comme dénominateur de coût
global ni comme preuve de gratuité CPU.

## Ce que les événements établissent réellement

Le parseur historique nomme `unique_ready` **17** identités et 17 visites.
Cette étiquette est trop large : `task_rail.nut` (source de la copie testée : `../../ai/OpexAI/task_rail.nut`)
assigne `phase="build"` après la fin de recherche **même en échec**
(autour des lignes1633–1657), puis `_consumeRailSearch` distingue `planFailed`
(autour de1671–1676). Il faut lire le résultat avant de parler de tracé prêt.

- **14 constructions réussies** à cette frontière.
- **1 manque de cash** (`insufficient_cash`) ; un renfort fleet28 est ensuite
  effectivement construit dans cette passe (graine100, 22 octobre1972).
- **2 ABND**, budget de recherche épuisé, pas deux échecs de pose d'un tracé
  trouvé : graine42, recherche de576jours ; graine746035,306jours.
- **7 candidats absents du TOP64 courant**, dont6 construits et1 refus cash.
  Absence du classement ne veut donc pas dire absence de consommation.
- **6 constructions rail précèdent un concurrent finançable mieux classé** :
  2 AIR, 1 fleet, 3 autres RAIL. Cela expose le contournement du classement
  historique à cette frontière ; aucun gain d'une réadmission n'en découle.
- **0 report C77 observé** dans ces visites. L'invariant défensif est conservé,
  son interaction n'est pas exposée par cet échantillon.
- 22 retours de dispatch concurrents réellement enregistrés : built, pending
  et rejected restent distincts. `pending` signifie recherche engagée, pas
  construction réussie. Les raisons détaillées de certains rejets ne sont
  pas présentes avec les diagnostics de production désactivés : `rejected`
  reste générique, aucun motif physique inventé.
- 5 upgrades initiés :3 OK,2 NOPATH ; recherches infructueuses de211 et380jours.
  Ce canal est séparé des15 primaires compatibles avec un tracé trouvé.

Les deux cas où AIR devance le rail (graine100) sont particulièrement lisibles :

| Date | RAIL rang / profit calibré / financement | AIR rang / profit calibré / financement | Résultat réel |
|---|---|---|---|
| 01/11/1972 | 14 / 2 130 £/an / 39 327 £ | 0 / 17 416 £/an / 40 964 £ | RAIL construit, aucune tentative AIR dans cette passe |
| 13/12/1973 | 2 / 2 315 £/an / 39 887 £ | 0 / 2 874 £/an / 40 964 £ | RAIL construit, aucune tentative AIR dans cette passe |

Le profit AIR est déjà celui du helper de calibration utilisé par fundScore,
sans second facteur de réalisation. Ses décisions de flotte et son financement
sont les champs du projet courant. Le rail et le premier AIR ont un tier0.
Le rail a une économie stockée respectivement **263 et298 jours** avant la
visite, contre2 et1jours pour AIR : fraîcheur différente, pas une revalidation
économique équivalente. Le tracé trouvé ne valide pas une vieille prévision.

**Censure importante :** ces AIR n'ont pas été essayés à cet instant. Rien ne
prouve qu'ils auraient effectivement construit, ni qu'ils auraient accru le
profit de l'empire. Pour le cas fleet de la graine999, le rail puis les deux
renforts sont tous construits dans la même passe : être devancé n'implique pas
être supprimé. Aucune conclusion TOP20→construction, aucun test de politique
de réadmission, aucune réouverture de ses qualifications rejetées.

## Comparaison des formules, hors décisions

`K_dec` n'est pas présent dans `projects.c69KDecData` pendant ces visites ;
`TENSION_TICKS_PER_DAY` reste0. Cela ne signifie pas K_dec=0 ou débit nul.
Sur3 paires où deux profits/fundScores donnent le même dénominateur supérieur
à leurs capitaux, l'analyse **infère conditionnellement** K_dec (arrondi, profit
calibré supposé identique à celui du classement). Ce n'est pas un champ mesuré.
Deux exemples donnent environ57 260 £ et43 695 £.

Les scores S et S* sont seulement des calculs de sensibilité : 200k ops de
transaction rail **estimées**, expectedOpcodes du rival, budgets annuels
paramétriques 1M/10M/67,525M. Ces valeurs n'entrent jamais dans l'IA et ne sont
ni un débit libre mesuré, ni une proposition de paramètre par défaut.

Pour les deux AIR ci-dessus, **aucun des deux scores ne fait gagner RAIL** dans
ces scénarios. Exemple1973, C=72 399 £, K_dec≈43 695 £, budget10M ops/an :

- S : RAIL≈4 054, AIR≈4 991.
- S* : RAIL≈3 712, AIR≈4 684.

Sur une autre paire **RAIL prêt / RAIL brut** (graine100,11décembre1972), le
résultat varie avec le budget : le précalcul peut améliorer l'arbitrage CPU,
sans garantir un gagnant lorsque les opcodes sont peu contraints. Il n'y a
que9 scénarios,3 paires, pas9 observations économiques indépendantes.
Les ABND sont exclus de ce calcul : leur retirer A* au prétexte de
`phase="build"` fabriquerait une fausse compétitivité d'un tracé inexistant.

## Une autre formule possible, sans coefficient inventé

Pour AIR/RAIL/ROAD, la piste conceptuelle la plus propre est la **valeur
réduite d'un projet face au portefeuille réalisable** :

\[
G(p,t)=P_{\mathrm{cal}}(p,t)
       -\lambda_K(t)K_{\mathrm{fin}}(p,t)
       -\lambda_\Omega(t)\widehat\Omega_{\mathrm{restant}}(p,t)
       -\lambda_D(t)D_{\mathrm{restant}}(p,t).
\]

Les lambda ne sont ni des bonus de mode ni des nombres choisis pour que le
rail gagne. Ce sont les prix d'opportunité des contraintes dans une allocation
du portefeuille : maximiser la somme des profits incrémentaux comparables,
sous capital disponible, budget CPU effectivement allouable et capacité des
décisions/constructions séquentielles. D représente uniquement la ressource
de cadence non déjà comptée dans les opcodes : pas de double facturation CPU.
Un lambda vient de la contrainte active, par exemple du problème relaxé ;
il est nul si cette contrainte ne limite pas l'allocation. Choisir à la main
ces lambda ferait revenir les multiplicateurs magiques.

Unités : P en £/an ; lambda_K en1/an ; lambda_Omega en £/an/opcode ; lambda_D
en £/an/unité de cadence. Horizon de valorisation commun décidé avant mesure,
profit au même palier de flotte et calibration unique obligatoires. Une
contrainte de capital est K_fin, pas le coût historique d'A* déjà payé.
Le rôle économique de K_dec doit être représenté par la cadence D ou conservé
dans C69 ; supprimer les deux ferait réapparaître « petits projets d'abord ».
Lorsque les opcodes ne contraignent pas, lambda_Omega=0 : cette expression
reste une valeur marginale avec coût d'opportunité, elle ne devient pas
automatiquement un ratio profit/capital.

**Faisabilité non établie.** Le vrai profit incrémental réseau, les coûts
résiduels VM, le reliquat libre, D et les prix de contraintes ne sont pas
mesurés ici. Les coefficients d'une relaxation peuvent aussi changer les
choix à projets indivisibles ; maximiser G seul n'est pas un solveur exact.
Constructibilité, véhicule disponible, sites/slots et concurrence restent
des conditions d'admission et des contraintes, pas un multiplicateur de
réalisation ajouté à un profit déjà calibré. Cette formule vaut pour tous
les modes dans le même problème d'allocation, mais **n'est ni qualifiée ni
proposée à l'adoption**. Aucune refonte générale n'est nécessaire pour traiter
le contournement d'admission déjà exposé.

## Verdict et suite

1. **Conserver C69/C70 et les invariants AIR en production.** Le portefeuille
   sait déjà classer économiquement ces concurrents ; la frontière primaire
   peut les court-circuiter avant la boucle normale.
2. **Ne pas adopter cette sonde telle quelle.** Équivalence économique non
   démontrée, chronologie AIR perturbée, neutralité opcode globale inconnue.
   Aucun nouveau banc actif, défaut ou correction comportementale lancé.
3. **Ne pas qualifier la réadmission, le précalcul ou une formule par ce
   diagnostic.** Il établit une exposition dans le bras ON, pas une perte de
   profit causalement attribuable à l'ordre des constructions.
4. **Condition nécessaire avant une intervention :** distinguer réussite
   A*/échec dans l'admission, rapprocher devis frais et alternatives réellement
   exécutables ; observer depuis données existantes ou instrumenter plus
   localement sans balayage répété du portefeuille et vérifier à nouveau la
   sonde avant usage causal. Aucune relance automatique ni réouverture d'essais
   rejetés. Le dépôt C121, tout le stock prêt et sa persistance ne sont pas
   exhaustivement mesurés par cette frontière : pas de conclusion à leur place.

## Artefacts reproductibles

- [Analyse complète et vérification d'intégrité](../evidence/review/rail_ready_autopsy_20261011/measurement/analysis.json.gz),
  [événements avec fichier/ligne](../evidence/review/rail_ready_autopsy_20261011/measurement/events.json.gz), [trajectoires annuelles](../evidence/review/rail_ready_autopsy_20261011/measurement/annual.csv.gz).
- [Code d'analyse](../evidence/review/rail_ready_autopsy_20261011/measurement/analyse.py.gz), [tests](../evidence/review/rail_ready_autopsy_20261011/measurement/test_analysis.py.gz),
  [script de copie et instrumentation](../evidence/review/rail_ready_autopsy_20261011/measurement/prepare.py.gz).
- [Résultat brut diagnostic](../evidence/review/rail_ready_autopsy_20261011/measurement/snapshot/results/diagnostic.json.gz),
  [manifeste](../evidence/review/rail_ready_autopsy_20261011/measurement/snapshot/results/diagnostic.manifest.json.gz),
  [checkpoints](../evidence/review/rail_ready_autopsy_20261011/measurement/snapshot/results/diagnostic.jsonl.gz),
  journaux dans `snapshot/results/diagnostic_engine/`.
- Cas AIR1972 : `ready_on_seed100_r0.log:6421–6423` ; AIR1973 : `:8974–8976`.
  Échec A* faussement appelé ready : `ready_on_seed42_r0.log:13076–13087`.
  Les champs log et line des événements évitent d'utiliser les heures murales
  comme dates de jeu.
