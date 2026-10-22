# PO-01C — reconstruction réactive reprenable

## Pré-enregistrement — 21 octobre 2026

Worktree `/home/deploy/projects/wt-po01c`, branche `po01c`, origine
`ba7ce23da7f070b9b7b8d91663dbe75c2a1066e3`, initialement propre.
Intervention comportementale expérimentale, défaut `po01c_regen_split=0` aux
quatre difficultés. Aucun changement de défaut, aucune porte A/B, aucun GitHub.

Contrats puis smoke causal 42 × 3 ans, carte 256², référence
`OpexAI[decision_log=1]`, variante
`OpexAI[decision_log=1,po01c_regen_split=1]`. Ensuite exposition 42/7/1234 × 3 ans,
mêmes bras avec `probes=10`. Une répétition, deux duels par graine, AAAHogEx figée.
Critère fixé avant mesure : au moins un lot publié par partie variante,
aucune tranche de reconstruction bloquant plus de cinq jours, aucune erreur
`[0] [S] Your script made an error`. `gain_short`, profit_year, seuil 4 %, garde
de valeur 5 % restent les métadonnées du harnais ; verdict économique attendu
`diagnostic_only`, aucune qualification sur cet échantillon.

VPS : contexte Docker `default`, image
`sha256:a0e0a0727f5003532764eeaeee6b83e9ab96a7470df3c76208c6446d10b88c8c`,
cache `openttd-lab-home`, dépôt monté `/work`, réseau host,
3 CPU / 2 Go RAM et swap plafond 2 Go / 2 workers. Une campagne à la fois.
Budget : 2 parties smoke puis 6 parties exposition et un aller-retour solo
Save/Load. Correction technique : nouveau nom de campagne, ancien résultat conservé.

## Conception en cours de validation

La demande coalescée active un travail privé après l'orchestrateur, sans ajouter
de tâche inactive à son tourniquet. Les producteurs actuels sont copiés
mécaniquement avec checkpoints (script et contrat de synchronisation), pas repris
de l'ancien arbre `po01`. Budget cible 4 000 opcodes avec réserve 2 500 et
arrêt après changement de tick. Les opérations API et helpers internes restent
atomiques : leur dépassement doit être mesuré, ce budget n'est pas une garantie
de préemption au milieu d'un appel.

Le catalogue est privé ; seuls les champs des couches calculées sont publiés,
et une actualisation concurrente reste prioritaire. C78 garde ses champs AIR
pendant son scan. Les demandes AIR sont différées seules ; les autres modes
publient sans attendre C78. Le portefeuille est fusionné depuis sa version
courante et resélectionné au capital courant. L'acquittement par mode utilise
le snapshot initial ; une couche commune attend tous ses consommateurs.

`lines` : `OpexOriginService` lit seulement le rail ;
`OpexRoadFreightServedIndex` lit rail et route ; `OpexWaterTownServed` lit l'eau ;
le filtre V275 voyageurs lit aussi les origines AIR. Les signatures de desserte
conservent ces dépendances croisées. Les changements de véhicules seuls
conservent le travail flotte ; les véhicules AIR restent dans sa signature.
Une baseline absente déclenche conservativement le recalcul.

Un lot n'est jamais sérialisé. Load efface ses curseurs et conserve le filet de
sûreté historique de reconstruction ; les révisions publiées restent dans le
format C76 existant. La sonde `save_pending` permet de prouver l'interruption.

## Corrections techniques avant livraison

Le smoke `po01c_smoke_20261021_a` a publié mais la publication répétait la
resélection pour chaque mode (maximum 5 jours). Le smoke `..._b` réduit ce
coût : trois lots, tranches au maximum 3 jours, aucune erreur. L'exposition
`po01c_exposure_20261021_a` conserve ce code dans son bundle.
La revue suivante a ajouté les attributs des quais V264 à la signature et à
la copie des lignes, protégé la publication AIR contre un démarrage C78
survenu après la dernière tranche, et retiré la dernière double sélection
flotte. Ces corrections imposent un nouveau smoke puis une nouvelle exposition,
sans réutiliser le verdict du premier arbre.

L'exposition `po01c_exposure_20261021_a` révèle aussi un défaut technique :
`probes=10` passe par `_mainLoopProfiled`, contournant le hook initial ajouté à
la seule boucle normale. Aucun lot ne progresse. Le hook est déplacé dans
`_runOrchestratorTick`, commun aux deux boucles, avec garde une fois par tick.
Cette exposition est un échec d'intégration, pas une mesure de performance.

Le commit `1ef81fb` passe le smoke `po01c_smoke_20261021_c` (1 lot,
maximum 2 jours). L'exposition `po01c_exposure_20261021_b` ne passe cependant
pas le critère : 42/7/1234 publient respectivement 1/0/2 lots, maximum
3/3/2 jours, aucune erreur. La graine 7 reste en calcul après 334 jours.
La reprise reçoit trop peu de ticks après les traitements de début de boucle.
Correction technique : passage supplémentaire au début des deux boucles,
sans dépasser une tranche par tick, et signature AIR spécifique au filtre
rail V275 (origines/scrapping, sans nombre d'avions). Nouveau smoke et nouvelle
exposition nécessaires. Les résultats précédents restent non validés ; leurs
deltas économiques ne motivent aucune relance.

La suite complète initiale signalait sept contrats périmés sur le master de
départ (score factorisé dans `OpexRailCalFundScore`, clés de tables cargos),
trois plafonds de réglages périmés (93 déjà présents contre plafond 92),
et trois imports NumPy impossibles. Les assertions suivent maintenant le
helper courant, le plafond passe à 94 (93 existants + PO01C), et les trois
modules NumPy sont explicitement sautés en son absence. Aucune installation.
Les six sites Valuate des copies utilisent les mêmes API natives que leurs
originaux ; inventaire V262 actualisé, contrat V261 conservé.

## Reprise par Claude (21/10, 23 h) : deux corrections, puis mesures

Codex s'est arrêté sur quota après `4360b53` ; son smoke `po01c_smoke_20261021_d`
(42 × 3 ans) était sain (2 lots, tranches ≤ 3 jours, 0 erreur) mais non dépouillé.
Branche fusionnée avec master (`6f0de78`), copies régénérées (identiques), suite :
aucun échec nouveau (17 échecs préexistants, contre 27 sur master).

L'exposition `po01c_exposure_20261021_c` (code fusionné) échoue encore sur la graine 7
(483 tranches en 1972, 0 lot publié). Deux causes :
1. **Interception trop large** : `po01c_regen_split=1` captait toute intention `regen`,
   y compris les regens par mode (`_c80DoModeRegen`). Sur la graine 7 la référence
   n'a aucune reconstruction complète ; la variante lançait un lot 4 modes. Correction
   (`a30056b`) : seul le cas `modes == null` est découpé.
2. **Débit** : le crochet tourne une fois par passe de boucle (≈ 44 ticks mesurés,
   1,3 tranche par jour) ; à 4 000 opcodes par appel, un lot recevait ≈ 26 k opcodes
   par jour, contre ≈ 185 k pour la reconstruction synchrone. Tranche portée à
   `PO01C_SLICE_OPS = 40000` (≈ 4 ticks, moins d'un jour), éventuellement à cheval
   sur plusieurs ticks.

**Exposition `po01c_exposure_20261021_d`** (`a30056b`, 42/7/1234 × 3 ans, `probes=10`,
`decision_log=1` dans les deux bras) et smoke `po01c_smoke_20261021_f` :

| Partie | Référence : reconstruction synchrone | Variante : lots publiés | Durée du lot | Opcodes | Tranche max | Erreurs |
|---|---|---|---:|---:|---:|---:|
| smoke 42 | 18 jours (19/01/1972) | 1 (10/03/1972) | 69 j | 3,80 M | 2 j | 0 |
| 42 | 22 jours (24/01/1972) | 1 (07/03/1972) | 65 j | 3,43 M | 2 j | 0 |
| 7 | aucune | 1 (30/03/1972) | 89 j | 4,64 M | 2 j | 0 |
| 1234 | 45 jours (18/02/1972) | 0 : aucune demande complète | — | — | — | 0 |

Critère pré-enregistré : **0 gel > 5 jours** ✅ (aucune reconstruction synchrone dans
la variante), **0 erreur** ✅, **≥ 1 lot publié par partie variante** ❌ au sens littéral :
la graine 1234 de la variante, dont la trajectoire diverge dès 1971, n'a jamais demandé
de reconstruction complète. Le critère supposait une demande par partie ; il n'est pas
réécrit après coup. Économie (diagnostic, n = 3) : +70,7 k£/an, médiane −0,6 k, 1 V / 2 D.

**Save/Load** (`sweeps/save_load_roundtrip.py --require-po01c-pending`, solo) : graines
42 et 7 sans lot en cours au moment d'une sauvegarde ; graine 100 : sauvegarde du
01/02/1972 prise pendant un lot, rechargée, 0 erreur, `LOAD_RECONCILE` 37/37, partie
poursuivie un an (109 → 213 véhicules). Correction du filtre (`d28202c`) : Save() est
journalisé la veille de la date du fichier.

**Limites** : un lot met 2 à 3 mois à aboutir ; pendant ce temps, le vivier des modes
concernés reste celui d'avant (pas de gel, mais un portefeuille plus ancien). Le
contenu publié est calculé sur les lignes et l'état du début du lot ; la resélection
finale, elle, lit l'état courant. Aucune mesure à 10 ans (2 à 4 reconstructions par
partie selon PO-01) : prochaine exposition 3×10, puis porte A.

## Exposition 3×10 (22/10)

**Protocole pré-enregistré, avant résultat** : campagne
`po01c_expo_3x10_20261022`, graines 42/7/1234, 10 ans, une répétition,
carte 256², duel contre AAAHogEx. Référence
`OpexAI[decision_log=1,probes=10]` et variante
`OpexAI[decision_log=1,po01c_regen_split=1,probes=10]` (injection
`--probes 10` du lanceur), `--script-debug` dans les deux bras et
`gain_short`/`profit_year`/seuil +4 %/garde de valeur −5 % pour
l'enregistrement, **sans valeur de porte** (3 graines diagnostiques seulement).
La campagne a été lancée après A et B, `docker ps` vide, profil PC
`--cpus 10 --memory 8g --max-workers 3 --network host`.

Critères de mécanisme, à contrôler séparément sur chaque graine : (1) **zéro**
`PO01C_SYNC reason=reactive` et **zéro** erreur Squirrel dans la variante ;
(2) au moins un `PO01C_BATCH phase=publish` pour toute partie de variante ayant
demandé une reconstruction complète, les parties sans demande étant **non
exposées**, ni succès ni échec ; (3) `max_slice_days` **≤ 3 jours de jeu** ;
(4) relever pour la référence les dates et durées des reconstructions
synchrones. Le diagnostic `sweeps/po01c_diagnostics.py` doit fournir les six
journaux, leurs empreintes et les tranches ; le JSON terminal du harnais doit
confirmer six parties complètes et saines avant toute comparaison économique.

**Provenance et santé.** `master` `dec590bdca9952b919b2a7a7ffa58b7cf4ffacd1`,
arbre Git marqué `dirty=1` à cause du présent rapport non commité (aucune
modification de l'IA dans la file C). Bundle figé SHA256
`a1b5df6865936b89ed345189d9a100be0265a2eacf004e9de4a7f17a0664e645`,
manifest SHA256 `7a5f0c6ed70e4dc3527c6554bdf333ac01fa95afc3d37d6093e86b1a`,
image `openttd-lab:latest`
`sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
Résultats dans `results/po01c_expo_3x10_20261022.json`, six journaux
`results/po01c_expo_3x10_20261022_engine/` et diagnostic reproductible
`results/po01c_expo_3x10_20261022_diag.json` (commande exacte du prompt C,
`sweeps/po01c_diagnostics.py`). **6/6 jeux complets et sains**, 3/3 paires,
`failed_runs=[]`, `comparison_complete=true`,
`metric_coverage_complete=true`, aucun défaut Squirrel des deux bras.

### Exposition du mécanisme

| Graine | Référence : gels synchrones réactifs, date de fin (durée) | Variante : lots commencés/publiés | Tranches | Max tranche | Tranches > 3 jours |
|---|---|---:|---:|---:|---:|
| 42 | 24/01/1972 (22 j), 21/01/1973 (20 j), 21/12/1979 (19 j) | 34/34 | 813 | 3 j | 0 |
| 7 | 02/02/1972 (32 j), 30/01/1973 (29 j), 29/04/1979 (25 j) | 28/28 | 1 021 | 5 j | 2 |
| 1234 | 08/02/1973 (37 j), 30/09/1974 (29 j), 26/01/1975 (22 j) | 43/43 | 1 497 | 6 j | 5 |

Au total : **9** gels complets synchrones dans la référence
(19 à 37 jours, **235 jours cumulés**, mesure par dates finales et durées
internes du même appel), **0** `PO01C_SYNC reason=reactive` dans la variante.
**105 lots commencés et 105 publiés** sur les trois graines ; ils ne sont
pas tous des reconstructions complètes de quatre modes (certains sont des
réactualisations partielles ou de flotte). Chaque partie variante est donc
exposée ; aucune n'est classée « non exposée ». Le premier grand lot publié
est daté du 07/03/1972 (42, 65 jours de calcul), 31/03/1973
(7, 88 jours) et 13/02/1972 (1234, 43 jours). Le calcul complet
d'un lot reste étalé sur plusieurs dizaines de jours malgré les tranches.

**Dépassements du seuil de 3 jours**, tous en phase `PO01C_SLICE phase=mode`,
sans reconstruction synchrone complète : graine 7, 04/11/1973
(5 j, 1 033 909 opcodes), 18/04/1976 (4 j, 590 028) ;
graine 1234, 03/12/1973 (5 j, 916 487), 03/03/1975
(5 j, 1 021 016), 04/10/1977 (4 j, 601 149),
04/03/1978 (6 j, 1 044 362), 09/01/1979 (4 j, 571 213).
Ces opérations dépassent nettement `PO01C_SLICE_OPS = 40000` car la
limite est vérifiée **entre** reprises du générateur : elle ne préempte
pas l'appel atomique en cours. C'est une cause technique à corriger
au niveau des unités de travail du générateur, pas un argument pour
relever a posteriori le plafond.

| Critère pré-enregistré | Résultat | Verdict |
|---|---|---|
| Variante : 0 reconstruction complète synchrone réactive et 0 erreur Squirrel | 0 et 0 sur 3 parties | **PASS** |
| ≥ 1 lot publié pour chaque partie exposée | 34/34, 28/28, 43/43 | **PASS** |
| Plus longue tranche ≤ 3 jours | 3 / 5 / 6 jours, 7 dépassements | **ÉCHEC** |
| Relever les gels de la référence | 3 / 3 / 3, datés dans le tableau | **Mesuré** |

### Économie, descriptive uniquement

| Graine | Δ `profit_year` variante − référence | Δ valeur |
|---:|---:|---:|
| 42 | −4 940 £/an | +1 760 922 £ |
| 7 | −92 889 £/an | +1 632 418 £ |
| 1234 | −281 752 £/an | −2 083 433 £ |

Moyenne **−126 527 £/an**, médiane **−92 889 £/an**,
**0 V / 3 D / 0 E**, Wilcoxon exact bilatéral `p=0,25`,
IC95 bootstrap de la moyenne **[−281 752 ; −4 940] £/an**
(20 000 rééchantillonnages, graine 0). Ratio des moyennes de
`company_value` **+1,9515 %**. Verdict brut du harnais
`diagnostic_only` (3 graines au lieu des 40 requises et horizon
différent de la porte A) : ne pas confondre échantillon descriptif et
rejet économique qualifié.

**Verdict structurel du lot C : non validé**, malgré la disparition des
neuf gels synchrones et la publication effective dans chaque variante,
car deux graines dépassent le plafond de 3 jours. Le réglage
`po01c_regen_split` reste **désactivé par défaut (0)**. Aucun nouveau
banc, aucune porte A/B, aucun ajustement du seuil sur ces résultats ;
la prochaine correction éventuelle doit réduire les plus grosses
unités atomiques du générateur et refaire une exposition indépendante.
