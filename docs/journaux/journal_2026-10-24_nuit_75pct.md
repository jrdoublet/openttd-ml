# Nuit du 24 au 25 octobre 2026 — objectif 75 % AAAHogEx

### 25/10 — Résultat final du 20×10 multicargo (après adoption)

**Campagne saine et complète :**
`nuit75_multicargo_default_20x10_seedsfix_20261025`, source Git
`f3c1b1b1a3930ca0a1b0e02d0f5b6d5e628c506b`, SHA256 du bundle
`0bde1bde0de7a437c4365432d5c45be6d2becae0318b84dbb57e17376dae1c7d`,
manifeste SHA conforme, 1970–1979, 256², multimodal, 20 graines
identiques à la baseline 20×10 (dont **373684**, substitution à 73),
40/40 duels et 80/80 bilans de compagnies complets, 20/20 paires,
zéro partie invalide, zéro `failed_runs`, zéro erreur script dans les
bilans structurés. Les 40 fichiers de logs moteur sont présents et vides :
ils ne fournissent aucune preuve textuelle indépendante d'absence d'erreur.
Un seul Docker utilisé avec 10 CPU, 8 GiB et **9 workers max**.
Même code/bundle et `probes=2` pour les deux bras ; seul réglage effectif
différent : `n75_multi_cargo=0` ancien défaut contre `=2` nouveau défaut.
Le commit de base avant cette adoption est `02a48e95` ; l'option OFF
sur le nouveau code fige le comportement témoin pour un A/B isolé.

| Indicateur à fin 1979 | OFF (`0`) | ON (`2`) |
|---|---:|---:|
| Profit annuel moyen OpexAI | 4 139 142,55 £ | 4 215 559,65 £ |
| Profit annuel moyen AAAHogEx | 7 018 046,05 £ | 7 207 457,70 £ |
| Ratio Opex/AAA des profits moyens | **58,9786 %** | **58,4889 %** |
| Médiane des 20 ratios Opex/AAA par graine | **59,7217 %** | **61,1192 %** |

**Verdict officiel du harnais `non_erosion` : `pass`**, 20 paires :
Δ moyen privé Opex ON−OFF **+76 417,10 £/an**, soit **+1,85 %** de
4 139 142,55 £/an témoin ; médiane des différences **+43 630,50 £/an**,
**11V/9D/0E**, Wilcoxon exact bilatéral **p=0,62151337**,
IC95 bootstrap 20 000 rééchantillonnages graine 0
**[−158 453,90 ; +318 370,15] £/an**. Valeur Opex ON/OFF
(ratio des moyennes) **1,056398**, soit **+5,63979 %**, au-dessus de
la garde de perte maximale −5 %. La borne haute de l'IC95 est positive :
le critère `non_erosion` passe, sans prouver une hausse statistiquement
significative. Le ratio de profits moyens Opex/AAA **baisse de 0,4897
point** malgré le gain privé Opex, car le profit AAA varie lui aussi dans
chaque bras ; la médiane des ratios monte **de 1,3974 point**.
**La cible externe 75 % à dix ans n'est atteinte sur aucun des deux
agrégats.** Ce test est une vérification postérieure à la décision
utilisateur, pas la B conditionnelle de l'A40×5 antérieure `fail_primary`.

Contrôle reproductible : `python -X utf8
sweeps/analyse_nuit75_multicargo_default_20x10.py
results/nuit75_multicargo_default_20x10_seedsfix_20261025.json
--output results/nuit75_multicargo_default_20x10_seedsfix_20261025_analysis.json`.
Rapports à publier : `.json` de synthèse, `.manifest.json`,
`_analysis.json` ; exclusion des JSONL exhaustifs (~80 Mo) et `_engine/`.
Le premier essai interrompu pour corriger 73→373684, documenté dans
la section chronologique ci-dessous, n'a aucun verdict économique.

### 25/10, après clôture — adoption explicite de MULTICARGO et vérification 20×10

L'utilisateur a demandé : « Accept multicargo as a new default and run a 20x10
on it », puis « Update the documentation. Commit and push this multicargo
change and all this night's results ». Il autorise ainsi l'adoption ON malgré
`fail_primary` A40×5 : Δ moyen +91 191,925 £/an, médiane +93 397,
24V/16D, p=0,13868, IC95 [−16 568,375 ; +197 955,75] £/an,
seuil +112 369,415, valeur +2,646 %. Le réglage `n75_multi_cargo`
devient **2** aux quatre difficultés ; OFF=0 reste le comparateur exact,
SHADOW=1 reste disponible. Les tests et le code sont intégrés de manière
ciblée depuis `.worktrees/nuit75-early-multicargo-v1` ; le rapport technique
est publié dans `docs/nuit75_multi_cargo_20261025.md`.

Le 20×10 de vérification est **une demande indépendante après adoption** et
ne change aucun verdict A, ni la condition historique des B. Protocole fixé :
20 graines de référence, 1970–1979, carte 256², multimodal, 9 workers max,
un seul conteneur Docker, même code/bundle ON et OFF, `profit_year` privé
à l'année terminale, Wilcoxon exact bilatéral, bootstrap IC95 de moyenne
20 000 rééchantillonnages graine 0, ratio des moyennes de `company_value`
et garde −5 %, ratios Opex/AAAHogEx moyen et médian par bras. La baseline
historique 20×10 (56,5519 % / 58,9112 %) et les audits des six A sont
conservés sans requalification. Les gros JSONL de moteurs et répertoires
`*_engine/` restent dans les worktrees ; seules les synthèses sont publiées.

**Correction avant résultat :** le premier lancement portant l'identifiant
`nuit75_multicargo_default_20x10_20261025` utilisait par erreur la graine
73 des cohortes courtes. Il a été interrompu sans rapport économique final,
avec arrêt contrôlé de son unique conteneur. La baseline 20×10 de référence
emploie à cette position **373684**, substitution documentée pour le long
horizon. Le lancement définitif est
`nuit75_multicargo_default_20x10_seedsfix_20261025`, 20 graines
identiques à la baseline historique, source commit `f3c1b1b1`, bundle
`0bde1bde0de7a437c4365432d5c45be6d2becae0318b84dbb57e17376dae1c7d`,
OFF `n75_multi_cargo=0` contre ON `n75_multi_cargo=2`, `probes=2`
symétriques ; aucun verdict n'est imputé au lancement interrompu.

### 25/10, 09:10 — CLÔTURE de la file A40×5 multimodale (six verdicts officiels)

Orchestrateur `sweeps/run_nuit75_newformat_queue_20261025.py` terminé
**code 0**, événement `queue_complete` dans
`results/nuit75_newformat_queue_20261025.jsonl` ; aucun Docker ni
processus de file restant. Les **six A** ont chacune 40/40 paires,
80 duels, 160 bilans de compagnie, et **un audit indépendant VALIDE**
(`python -X utf8 sweeps/audit_nuit75_queue_20261025.py --require-all` :
sortie 0), avec SHA manifeste correspondant au fichier, source OFF/ON
commune, interventions isolées et sondes symétriques, aucun `failed_runs`,
aucune erreur script dans les bilans structurés. Les `.log` moteur des
six campagnes sont tous **présents mais vides** ; ne pas en déduire une
inspection textuelle des exceptions. Critères figés : horizon 1974,
256², `gain_short`, +4 % de profit moyen, Wilcoxon exact bilatéral
p<0,05, borne basse IC95 >0, perte de valeur ≤5 %.

| Porte A / intervention ON | Δ Opex `profit_year` £/an | Seuil +4 % £/an | p Wilcoxon | Valeur entreprise | Verdict |
|---|---:|---:|---:|---:|---|
| N75-CAP `n75_freight_capacity=1` | −9 137,625 | 114 705,404 | 0,928548 | −0,177 % | `fail_primary` |
| GOOD `good_source_rail_join=1` | −40 727,5 | 113 747,221 | 0,091824 | −2,176 % | `fail_primary` |
| AIR-GROW corrigé `air_grow_marginal=2` | −23 434,75 | 111 791,566 | 0,509914 | −0,347 % | `fail_primary` |
| C75-REFUND `n75_c75_refund=2` | −11 117,975 | 111 924,424 | 0,957845 | −0,536 % | `fail_primary` |
| AIR TRUE QUOTE `n75_air_true_quote=2` | +6 856,725 | 112 475,315 | 0,397424 | +0,252 % | `fail_primary` |
| N75 multi-cargo `n75_multi_cargo=2` | **+91 191,925** | **112 369,415** | **0,138680** | **+2,646 %** | `fail_primary` |

**Bilan : zéro A `pass`, donc zéro B20×10 déclenchée.** Le meilleur
gain moyen multi-cargo ne franchit ni +4 % ni Wilcoxon/IC95 ; ses
24 victoires/16 défaites, IC95 [−16 568,375 ; +197 955,75] £/an,
ne le qualifient pas. Ratios descriptifs **fin 1974** de ce dernier
A par bras (40 paires saines propres à chaque bras) : OFF
Opex 2 809 235,375 £/an, AAA 3 055 470,5 £/an, ratio des moyennes
**91,9412 %**, médiane des ratios appariés **96,5730 %** ; ON
Opex 2 900 427,3 £/an, AAA 2 998 522,45 £/an, ratio des moyennes
**96,7286 %**, médiane **99,6565 %**. Les ratios à cinq ans des six A
sont consignés séparément dans les audits JSONL et le journal ;
**aucun nouveau ratio 1979 n'est produit**, et la cible ≥75 %
Opex/AAAHogEx 20×10 demeure NON démontrée.

GSP GOOD origin-spread reste **prototype opt-in, OFF par défaut**
dans `.worktrees/nuit75-good-origin-spread-v1`, sans simulation,
avec **175 tests hôtes regroupés PASS** et `git diff --check` PASS.
Ce code n'a altéré aucun des six bundles comparés. Aucune adoption,
aucun défaut/`AGENTS.md` changé, aucun commit, push ou merge.

### 25/10 — contrôle d'intégrité renforcé pendant la file A40×5

Au terme de N75-CAP, GOOD, AIR-GROW corrigé et C75-REFUND,
**4/4 campagnes A validées techniquement** par l'auditeur hors Docker :
chacune a **40/40 paires, 80/80 duels et 160/160 bilans de compagnies**,
aucun `failed_runs`, aucune erreur Squirrel dans les bilans structurés,
aucune partie ou année terminale invalide. Manifestes SHA256 recomputés
et conformes, bundles cohérents, paramètres OFF/ON isolés, `probes=2`
symétrique, année 1970, carte 256², décision `gain_short`, seuil +4 %
et garde valeur −5 % vérifiés sans modifier les six bundles de simulation.
**Les 80 fichiers `.log` moteur par campagne sont présents mais vides** :
l'absence d'erreur de script est fondée sur les bilans du harnais, pas sur
une inspection de messages textuels absents. Tests du vérificateur
**11/11 PASS** (doublons, provenance, année, manifeste, règle,
sondes, fichier moteur manquant et exception Squirrel textuelle).
Verdicts officiels des quatre A : **`fail_primary`**, aucune porte B.
TRUE QUOTE puis multi-cargo restent dans l'orchestrateur unique ;
aucun second Docker, défaut, commit ou push.

### AIR-GROW corrigé — porte A 40×5 terminée, intégrité vérifiée

`nuit75_airgrowfix_porteA_40x5_20261025`, bundle source
`20aed72968d8ab7a5afdabad3ce9aeea15f6c7f42b482ac5f509717dea88e389` :
**80/80 duels, 160/160 lignes de compagnie, 40/40 paires complètes,
0 erreur script, 0 partie invalide, 0 erreur de provenance** d'après
`sweeps/verify_nuit75_gate_integrity_20261025.py`. Verdict officiel
**`fail_primary`**, Δ Opex `profit_year` moyen
**−23 434,75 £/an**, médiane −71 454, 19V/21D,
Wilcoxon bilatéral p=0,5099141, IC95 bootstrap
[−100 394,5 ; +54 630,7] £/an, seuil +4 % requis
**+111 791,566 £/an**, valeur entreprise −0,34663 %
(garde −5 % respectée). **Pas de porte B.**

Ratios Opex/AAAHogEx descriptifs **fin 1974** par bras
(40 couples Opex/AAA sains, AAA positive, chacun dans le monde
de sa politique) : OFF Opex moyen 2 794 789,15 £/an,
AAA 3 082 243,575 £/an, ratio des profits moyens **90,6739 %**,
médiane des ratios appariés **92,5360 %**. ON Opex
2 771 354,40 £/an, AAA 3 120 637,75 £/an,
ratio des profits moyens **88,8073 %**, médiane appariée
**90,4192 %**. Les ratios à cinq ans ne sont pas la cible 1979.
L'orchestrateur a enchaîné N75-C75-REFUND 40×5
`nuit75_c75refund_porteA_40x5_20261025`, un seul Docker,
9 workers maximum.

### GOOD A40×5 : contrôle indépendant après verdict

Campagne `nuit75_goodsource_porteA_40x5_newformat_20261025`,
bundle `4da09e927f64bc110ee2da6752131226a2ab9fdd792e0670f2b80bcc1790b808` :
**80/80 duels, 160/160 lignes compagnies, 40/40 paires
complètes, zéro erreur script ni partie invalide**, confirmé par
`sweeps/verify_nuit75_gate_integrity_20261025.py`.
**`fail_primary`** : Δ Opex moyen **−40 727,5 £/an**,
13V/27D, Wilcoxon exact p=0,091824, IC95 bootstrap
[−101 369,375 ; +21 796,25] £/an, seuil +4 %
**+113 747,221 £/an**, valeur −2,17609 % (garde respectée).
**Pas de B GOOD**. Distinct de l'ancien A40×10 GOOD
(`fail_primary` p=0,0548, horizon fin1979).

**Ratios descriptifs fin 1974 de cette nouvelle A40×5**
(ne pas confondre avec la cible 1979) : OFF : Opex
2 843 680,525 £/an, AAA 3 087 227,10 £/an,
ratio des moyennes **92,1112 %**, médiane des 40 ratios
appariés **95,8158 %**. ON : Opex 2 802 953,025 £/an,
AAA 3 125 139,675 £/an, ratio des moyennes **89,6905 %**,
médiane **91,4316 %**. Chaque bras a 40 dénominateurs AAA
valides propres à ses duels. AIR-GROW corrigé 40×5
`nuit75_airgrowfix_porteA_40x5_20261025` lancé ensuite,
nouveau conteneur unique, 9 workers, sans chevauchement.

### Audit indépendant de la nouvelle file et préparation du levier suivant

**N75-CAP A40×5 : intégrité confirmée indépendamment** avec
`sweeps/verify_nuit75_gate_integrity_20261025.py` : 40 graines
uniques, 80 duels, 160 lignes de compagnies, 40/40 paires, source
bundle commun `7814fbdc…`, **0 erreur script, 0 erreur de partie,
0 exécution incomplète**. Vérification fonctionnelle de ce contrôleur :
6/6 tests unitaires verts. Verdict économique inchangé
`fail_primary` ; aucune B.

**Ratios descriptifs fin 1974, N75-CAP A40×5, pas le ratio objectif
fin 1979 :** OFF, Opex moyen 2 867 635,10 £/an et AAA moyen
3 080 053,875 £/an, ratio des profits moyens **93,1034 %**,
médiane des ratios appariés **95,2716 %** (40/40).
ON, Opex moyen 2 858 497,475 £/an et AAA moyen
3 005 389,725 £/an, ratio **95,1124 %**, médiane **97,4096 %**
(40/40). Les AAA sont propres à chaque bras ; une amélioration du
ratio par baisse d'AAA ne démontre pas un gain privé Opex.

**Nouvelle variante code/tests préparée sans Docker :**
`.worktrees/nuit75-good-origin-spread-v1` sur base `83e436cc`,
copie autonome du code GOOD déjà gelé (worktree de campagne
intouché), `good_source_rail_join` prolonge son domaine à
`0=OFF / 1=GOOD historique / 2=GOOD avec récupération de quai
A hors parallèle`, quatre défauts 0. Le moteur V264 existant
cherche un quai joint dans les limites réelles de spread
**uniquement** lorsque le quai parallèle GOOD est non productif
ou introuvable ; aucune gare indépendante autorisée, gare source
et production revalidées, aucun contournement A*/C77/C80.
**199/199 contrats ciblés verts**, `git diff --check` OK,
SHA historiques GOOD conservées en soustrayant seulement les
fragments exacts de ce nouveau mode (pas de rebaseline).
**Aucun smoke ni bench**, effet économique inconnu :
voir `.worktrees/nuit75-good-origin-spread-v1/docs/nuit75_good_origin_spread_20261025.md`.
Cette préparation n'affecte pas la file déjà lancée.

### 25/10 — CONSIGNE LA PLUS RÉCENTE : file complète des portes A, format modifié

L'utilisateur remplace **le format** d'A40×10 tardive par : « Il faudra
relancer des 40x5 multi ou des 40x3 rail seul sur tous les sujet de cette
nuit. » Cette instruction couvre **toutes** les variantes comportementales
suivantes, y compris celles fermées par un diagnostic court. L'autorisation
de B20×10 `non_erosion` **si et seulement si A a formellement `pass`**
reste acquise ; aucun défaut, `AGENTS.md`, commit, push ni merge modifié.

**Choix explicite pré-résultat : A40×5 multimodal pour les six lignes**,
1970–1974 sur carte 256², 40 graines canoniques identiques en OFF/ON,
1 répétition, `probes=2` symétrique, Opex contre AAAHogEx-115 par
bras, car le jeu complet (AIR/V252 et arbitrages de caisse) est la
cible des 75 % ; le profil « rail seul » 40×3 est autorisé mais non
retenu pour ces comparaisons. Tous les A : `gain_short`,
`--min-useful-primary-delta-pct 4 --primary-metric profit_year`,
`--value-guard-max-loss-pct 5 --required-seeds 40 --required-years 5
--years 5 --repeats 1 --max-workers 9 --cpus 10 --memory 8g
--map-size 8`. PASS impose Wilcoxon exact bilatéral p<0,05,
borne basse IC95 bootstrap >0, moyenne du delta ≥4 % de la
moyenne de référence, valeur entreprise ≥95 % du témoin, 40/40
paires saines. Les règles sont fixées **avant** le résultat et
restent celles du moteur V102. B le cas échéant : 20 graines
canoniques × 10 ans `non_erosion`, même bundle OFF/ON,
seuil 4 % enregistré mais non porte B ; rapporter ratio à dix
ans (moyenne Opex / moyenne AAA) et médiane des 20 ratios
Opex/AAA appariés **par bras**.

**File ordonnée (un seul Docker, 9 workers au plus) :**

| Rang | Variante / worktree sous `.worktrees/` | OFF → ON | Campagne A40×5 multimodale | État au pré-enregistrement |
|---:|---|---|---|---|
| 1 | N75-CAP / `nuit75-freight-capacity-variant` | `n75_freight_capacity=0→1` | `nuit75_freightcap_porteA_40x5_20261025` | **Déjà lancée**, Docker `flamboyant_antonelli`, 9 workers, conforme : terminer sans interruption |
| 2 | GOOD / `nuit75-good-source-variant` | `good_source_rail_join=0→1` | `nuit75_goodsource_porteA_40x5_newformat_20261025` | En attente ; ancien A40×10 `fail_primary` conservé sans l'utiliser comme A40×5 |
| 3 | AIR-GROW corrigé / `nuit75-air-grow-corrected` | `air_grow_marginal=0→2` | `nuit75_airgrowfix_porteA_40x5_20261025` | En attente, correctif motorisation conservé |
| 4 | N75-C75-REFUND / `nuit75-early-c75-refund` | `n75_c75_refund=0→2` | `nuit75_c75refund_porteA_40x5_20261025` | En attente, effet possible limité à 1971–1972 mais horizon demandé maintenu |
| 5 | N75 AIR quote +1,4 % / `nuit75-early-value-v1` | `n75_air_true_quote=0→2` | `nuit75_truequote_porteA_40x5_20261025` | En attente, gain 10×3 initial non qualifiant |
| 6 | N75 multi-cargo / `nuit75-early-multicargo-v1` | `n75_multi_cargo=0→2` | `nuit75_multicargo_porteA_40x5_20261025` | En attente, diagnostic 5×3 précédent ne qualifie pas |

Chaque lancement doit vérifier `docker ps` vide ; **ne pas interrompre
le conteneur existant**, puisque son A40×5 N75-CAP satisfait la
nouvelle consigne. Pour chaque A `pass`, enchaîner B20×10
`non_erosion` sur le même worktree et le même code figé,
avant l'A suivante, puis inscrire santé/statistiques/ratio.
Conserver tous les rapports et manifests historiques, noms de
campagnes distincts pour éviter toute écriture sur un résultat ancien.

### 25/10 — Approbation explicite de l'utilisateur : A40×10 pour effets post-1973

**Précision utilisateur ultérieure, applicable à la présente séquence :**
« Pour les améliorations rail tu peux faire des 40x5 rail seul ou 40x5 multimodal ».
Les deux profils A40×5 sont désormais **autorisés en alternative** à l'A40×10
pour GOOD, N75-CAP et les autres politiques rail ; ils gardent strictement
`gain_short` +4 % du profit annuel moyen de référence à fin horizon,
Wilcoxon exact bilatéral p<0,05, borne inférieure IC95 bootstrap >0
et valeur au moins 95 % de la référence. La B `non_erosion` 20×10
est inchangée, conditionnelle à A `pass`. Choix **avant résultats** :
GOOD conserve A40×10 **multimodal déjà lancée** sur bundle
`4da09e92...` : des constructions GOOD en 1977/1979 ont été
observées sur un diagnostic antérieur, donc l'horizon dix ans garde
une justification causale, et il serait contre-productif d'arrêter/
relancer Docker à mi-parcours. Pour N75-CAP, choisir **A40×5
multimodal** (1970–1974, fin 1974), car N75 peut sélectionner des
secondes rames dès 1972 et cinq ans permettent de vérifier une
réponse physique durable ; le profil rail seul ne représenterait
pas les contraintes AIR/V252 et capital du jeu complet cible 75 %.
Nom `nuit75_freightcap_porteA_40x5_20261025` ;
`--required-seeds 40 --required-years 5 --years 5`.
Ne pas mélanger le verdict à horizon cinq ans avec celui de GOOD
à horizon dix ans et ne pas lancer plusieurs campagnes simultanément.

**Résultat GOOD A40×10 multimodal terminé le 25/10**, campagne
`nuit75_goodsource_porteA_40x10_20261025`, 40/40 paires,
80/80 duels sains, bundle IA **identique** à l'ancienne A40×3
`4da09e927f64bc110ee2da6752131226a2ab9fdd792e0670f2b80bcc1790b808`.
`good_source_rail_join=0` vs `=1`, `probes=2`,
1970–1979/256²/9 workers. `profit_year` ON−OFF
**+127 819,45 £/an**, médiane +156 160,5,
**28V/12D**, Wilcoxon exact bilatéral **p=0,0548103**
(ne satisfait pas p<0,05), IC95 bootstrap
**[+18 683,25 ; +239 499,375] £/an** (borne positive),
seuil +4 % du témoin **+170 929,10 £/an**
(moyenne témoin Opex 4 273 227,50 £/an).
Valeur entreprise ON/OFF **+0,74543 %**, garde −5 % respectée.
**Verdict officiel `fail_primary` : A échoue par le seuil
de gain ET par p, aucune porte B GOOD** malgré IC positif.

**Ratios de profits en décembre 1979, 40 paires valides par bras,
aucun dénominateur AAA nul/non positif :**

| GOOD arm | Opex moyen £/an | AAA moyen £/an | Ratio des profits moyens Opex/AAA | Médiane des 40 ratios appariés |
|---|---:|---:|---:|---:|
| OFF=0 | 4 273 227,50 | 7 565 478,05 | **56,4832 %** | **55,3267 %** |
| ON=1 | 4 401 046,95 | 7 445 675,88 | **59,1088 %** | **60,0331 %** |

Les dénominateurs AAA proviennent de **chaque duel propre au bras**,
pas de la seule référence : les écarts AAA ne sont pas attribués au
profit privé Opex. Le seuil externe 75 % n'est atteint par **aucun bras**
sur ces 40 graines. Résultats dans le worktree GOOD :
`results/nuit75_goodsource_porteA_40x10_20261025.{json,jsonl,manifest.json}`,
`results/nuit75_goodsource_porteA_40x10_20261025_ratios.json`.
Pas d'adoption, aucun défaut/commit/push changé.

L'utilisateur a écrit **« J'approuve »** et autorise **expressément** une
porte A de **40 graines × 10 ans (1970–1979), carte 256×256, 1 répétition**
pour les variantes dont l'effet attendu se manifeste après 1973, en commençant
par `good_source_rail_join` puis `n75_freight_capacity`. C'est une
**dérogation explicite d'horizon** à la porte A 40×3 précédente : la règle
`gain_short` reste appliquée sur les profits annuels **fin 1979**, avec
**seuil relatif de +4 %** du profit Opex de référence, Wilcoxon exact
bilatéral `p<0,05`, **borne inférieure IC95 bootstrap >0** et garde
de valeur de compagnie (baisse au plus **5 %**). La porte B demeure
`non_erosion` 20×10, désormais **approuvée explicitement uniquement
si la porte A complète de la variante concernée passe**. Aucune B après
A `fail_primary`, échec de significativité, santé insuffisante ou garde.

Références et variantes depuis le **même bundle gelé** par worktree :
`OpexAI[good_source_rail_join=0]` vs `=1`, puis
`OpexAI[n75_freight_capacity=0]` vs `=1`. Les autres réglages
restent aux défauts courants ; GOOD et N75-CAP ne sont pas combinés.
Harnais C66.4 : `--decision-rule gain_short --min-useful-primary-delta-pct 4
--primary-metric profit_year --value-guard-max-loss-pct 5
--required-seeds 40 --required-years 10 --years 10 --repeats 1
--max-workers 9 --cpus 10 --memory 8g --map-size 8`, graines
canoniques 40 de `sweeps/qualification.py`, `probes=2` symétrique.
Campagnes pré-enregistrées `nuit75_goodsource_porteA_40x10_20261025`
et `nuit75_freightcap_porteA_40x10_20261025` ; jamais deux Docker
simultanément. Mesurer pour **chaque bras** le ratio
Opex/AAAHogEx **des profits moyens** et la **médiane des ratios
appariés** à fin 1979, avec leurs dénominateurs et effectifs.
Ne pas modifier `AGENTS.md`, les défauts ou les données antérieures ;
aucun commit/push/merge. N75 multi-cargo précédent clos après
diagnostic causal NO-GO, aucun nouveau banc N75-MC.

### 25/10, reprise N75-MC : recharge rail supplémentaire après V217

Worktree propre créé sur `83e436cc` : `.worktrees/nuit75-early-multicargo-v1`.
Variante opt-in `n75_multi_cargo` (0 OFF aux quatre difficultés, 1 SHADOW, 2 ON)
sans modification du défaut ni des fonctions historiques V217. Le V217 courant
est déjà à 1 : N75 ne peut essayer qu'un cargo additionnel en 1972 lorsque
le portefeuille demeure nominalement non finançable. Sur 256², V276 auto
est 0 ; le générateur historique essaye déjà des cargos fallback en cas
d'absence totale de candidats. Hypothèse d'un gain +4 % 1972 **très faible
et non démontrée**.

Audits READ ONLY indépendants : AIR_GROW corrigé 5×3 −99,33 k£/an, valeur
−8,39 %, redondance de prix avec N75 AIR quote +32,18 k£/an (+1,403 %),
donc **NO-GO cumul**. Fenêtre AIR 1971 : 59 RAIL suivis d'un AIR
déjà construit sous 30 jours dans 32/40 mondes ; plafond 1972 AIR
non construites derrière RAIL ~70,7 k£/monde théorique, sous seuil.
Archives V217 **non identiques au master** en 1972 : 474 événements
mensuels (240 skip cash, 142 skip pool, 92 recharges) ; seuls 75 mois
commencent avec zéro candidat physiquement non bloqué, pas preuve de
devis ou construction supplémentaires. Référence 1972 Opex
2 104 034 £/an, **+84 161 £/an nécessaires pour +4 %**.

Code et tests dans le worktree ; **170/170 tests Python ciblés PASS**,
`git diff --check` PASS, SHA PO01C et 58 réglages historiques
vérifiés après neutralisation des **seuls** fragments N75. Revue
indépendante de syntaxe/SaveLoad/C77/V276 : GO uniquement smoke
technique. Smoke `nuit75_mc_smoke_1x1_20261025` bundle
`542e1c346d44ae042a5d67713dc8c68be5c34dd1a71a46955e804265a5b5f359` :
2/2 duels 1970 complets, ON−OFF +15 316 £/an **sans exposition N75**
avant 1972, donc aucun effet attribuable. Après ce smoke, correction
de la recherche : génération sur brouillon, publication du nouveau
vivier seulement si projet admissible, sinon état live conservé.
Smoke **r2 final** `nuit75_mc_smoke_r2_1x1_20261025`, bundle
`ae6b948c9b14e394055e6a4befded72346697fdda5c7737a462f262200450fe2`,
**2/2 sains**, identique +15 316 £ en 1970 sans activation N75.
Exposition `nuit75_mc_expo_5x3_20261025` **10/10 sains**
sur même bundle, ON−OFF `profit_year` 1972 +126 548,8 £/an
en moyenne, 3V/2D, p=0,3125, IC95 bootstrap [−43 954 ;
+297 051,6], valeur +0,47035 %, seuil +86 663 £ sur cohorte :
**diagnostic_only, pas A**. Graine100 N75 **jamais activé**
mais +301 814 £/an de différence ; les quatre autres graines
moyennent +82 732,5 £/an (+3,40 %), insuffisant.
Logs 1972 : sept `N75_MC refill`, cinq budget-éligibles,
deux non appliqués ; 1 654 407 opcodes mesurés pour les recharges,
hors latences indirectes. Différences larges RAIL 51 ON-only /
30 OFF-only, AIR 29 ON-only /20 OFF-only, non causales compte
tenu des divergences avant exposition. Fenêtres de 45 jours suivant
les cinq recharges admissibles : 10 builds ferroviaires du cargo ciblé,
6 builds de mêmes sources côté référence dans l'année ; **+69 664 £**
de profit ANNUEL **prédit** total cinq mondes, soit +13 932,8
£/an par graine (~0,64 %), non profit réalisé et non attribuable
rigoureusement à N75. **Verdict NO-GO A40×3 et B faute de
gisement causal ≥4 %** ; prototype conservé sans adoption.
Voir `.worktrees/nuit75-early-multicargo-v1/docs/nuit75_multi_cargo_20261025.md`.
Aucun commit/push/merge, Docker simultané interdit, fichiers locaux
préexistants conservés.

Mission utilisateur : atteindre au moins 75 % des profits de AAAHogEx en moyenne ou en médiane sur 20×10 ou 40×10, en duel 1970, carte 256², sans modifier les défauts avant qualification et sans commit/push/merge. Ne jamais assimiler le ratio concurrentiel à une qualification V102.

## État initial et résultats déjà disponibles

- Dépôt PC `/openttd-ml`, `master` HEAD `83e436cc3db35ff18efb685ace4f97eb569f77b1`, `git status` sans modification suivie, seul `?? .worktrees/` préexistant. Contexte Docker `desktop-linux`, image locale `openttd-lab:latest` `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`, OpenTTD 15.3, AAAHogEx-115 présent. Aucun conteneur démarré au constat initial.
- `air_grow_marginal=2` contre 0, porte A `gain_short` 40×3 GitHub [run 40131984205](https://github.com/jrdoublet/openttd-ml/actions/runs/40131984205), source `25f40f8e`, 40/40 paires : **`fail_primary`**, delta `profit_year` +4 160,4 £/an, médiane +55 735,5, 24V/16D, Wilcoxon p=0,50137, IC95 bootstrap [−93 232,05 ; +92 684,475], seuil +87 413,321, garde valeur −1,945 % tenue. Aucun lancement B pour ce candidat.
- `v217_refill_unlock=2` contre 0, porte A GitHub [run 40131786349](https://github.com/jrdoublet/openttd-ml/actions/runs/40131786349), source `374fd605` : tentative 1 **erreur technique avant simulation** (`httpcore.ReadTimeout`, téléchargement de bibliothèque BaNaNaS dans `freeze_bananas_libraries`). **Tentative 2 terminée `fail_primary` 40/40** : delta moyen Opex **+57 501,475 £/an**, médiane +12 415,5, **21 V / 19 D**, Wilcoxon p=0,2424468, IC95 bootstrap **[−25 606,125 ; +139 387,375]**, seuil 4 % **+86 127,421**, ratio de valeurs 0,960235 (−3,97653 %, garde 5 % tenue). Aucune porte B pour ce réglage isolé, défaut 0.
- AIR-PELOTON-1 : diagnostic 5×5 `peloton_diag_5x5_20261024`, 10 497 départs et charge médiane 9–12 %, surcapacité dominante avec effet d'écart entre départs. Sonde uniquement ; pas de politique adoptée.
- RAIL-CAL-1 : `rail_cal=1` clos (A 40×3 `fail_primary` +15,4 k£/an ; diagnostic 40×10 `fail_primary` +70,5 k£/an) ; ne pas relancer sous le même modèle.

### Ratios externes recalculés sur les fichiers PC déjà terminés

Pour chaque bras, ratio moyen = `100 × somme(profit_year Opex) / somme(profit_year AAA)` à horizon dix ans. Ratio médian = **médiane des ratios par graine** `100 × profit_year Opex / profit_year AAA`, et non le rapport des médianes. Tous les profits AAA sont strictement positifs ; chaque bras mentionné ci-dessous possède ses vingt paires complètes et sa propre trajectoire AAA. Les écarts entre campagnes peuvent donc venir de l'échantillon, de la base ou de la trajectoire du duel ; **ces ratios ne qualifient aucun réglage**.

| Source 1970/256² | Bras | Opex moyen (£/an) | AAA moyen (£/an) | Ratio moyennes | Médiane ratios appariés | Verdict interne |
|---|---|---:|---:|---:|---:|---|
| `results/v217m2_porteB_20x10_20261024.json` | `v217_rail_refill=1` | 4 138 468 | 7 318 183 | **56,5505 %** | **59,8280 %** | témoin |
| idem | `v217_rail_refill=2` | 4 094 917 | 7 265 869 | **56,3583 %** | **60,5453 %** | B `pass` ; Δ Opex −43 551 £/an |
| `../wt_airload30/results/airload30_porteB_20x10_20261024_final.json` | `air_load_min_pct=0` | 4 153 724 | 7 047 098 | **58,9423 %** | **61,5788 %** | témoin |
| idem | `air_load_min_pct=30` | 4 075 315 | 7 380 512 | **55,2172 %** | **54,4352 %** | B `pass` ; Δ Opex −78 410 £/an |

En 40×10 sur graines différentes, ancien paquet adopté `docs/taches.md` ~59,7 % de ratio de moyennes (GitHub 39576096262, base précédente). Aucun de ces résultats n'atteint 75 %. Parmi les expériences opcodes distinctes du 23/10 (`opcode_ailist_L5_air_refit_20x10_20261023`), la variante atteint 63,6219 % de ratio des moyennes et 71,4737 % de médiane des ratios mais les bases et interventions diffèrent ; elle ne prouve pas le ratio du master actuel ni une progression causale jusqu'au seuil.

Le diagnostic AIR-PELOTON indique une concurrence de temps de chargement : AAAHogEx pose `OF_FULL_LOAD_ANY` aux deux gares de ses lignes bidirectionnelles (`ai/AAAHogEx-115/route.nut:1871,2163`, `air.nut:201`), OpexAI `OF_NONE` dans `air_construction.nut`/`air_fleet.nut`. Hypothèse à tester isolément derrière `air_peloton_full_load=0` par défaut : charger complètement aux deux extrémités. Effet adverse possible : immobilisation de flotte sur les lignes à faible demande, autre terme que le coût de surcapacité ; aucun bénéfice présumé. Un worktree expérimental distinct `/openttd-ml/.worktrees/nuit75-air-full-load` est préparé pour code/tests, sans banc tant que la référence PC est active.

Revue critique `air_grow_marginal` : lorsque le renfort choisit un moteur différent, le modèle utilise la capacité/rotation du nouveau moteur pour les N anciens appareils (`ai/OpexAI/air_fleet.nut`). Cette modernisation fictive contamine l'estimation de gain du N+1e avion. Correctif et tests en préparation dans worktree isolé `/openttd-ml/.worktrees/nuit75-air-grow-corrected`, défaut conservé à 0, **sans annuler l'échec de porte A de la version SHA25f40f8e**.

## Mesure de référence pré-enregistrée : `nuit75_master83e_baseline20x10_20261024`

Référence seule contre AAAHogEx-115, aucun bras variante et **aucun test d'adoption**, objectif de mesure externe. `OpexAI` aux défauts présents dans `master` HEAD `83e436cc`; départ 1970, carte 2^8 = 256², année terminale 1979, 20 graines canoniques de `sweeps/qualification.py` (73 remplacée par 373684) : 42, 100, 7, 999, 2026, 1, 17, 373684, 314, 512, 1024, 1337, 4096, 8191, 12345, 54321, 65537, 123456, 424242, 8675309. Une répétition. Profil PC 10 CPU, 8 GiB, 9 workers (plafond utilisateur), volume de cache standard, `probes=2` symétrique selon harnais. Produits : `results/nuit75_master83e_baseline20x10_20261024.{json,jsonl,manifest.json}` et bundles figés.

Mesures prévues : santé, 20/20 duels, profit annuel terminal de chaque compagnie ; ratio des **moyennes** Opex/AAA et **médiane des ratios appariés** Opex/AAA (en décrivant les dénominateurs et les éventuelles exclusions), plus profits moyens et médians individuels. Comparer aux ratios historiques à 10 ans (~59,7–60,4 % sur 40 graines, code antérieur) sans déclarer une amélioration causale entre versions ni échantillons.

Commande pré-enregistrée (sur le PC local, hors Docker) :

```powershell
python -X utf8 sweeps/run_c66_reference.py --campaign nuit75_master83e_baseline20x10_20261024 --reference "OpexAI" --policy-id reference --years 10 --start-year 1970 --map-size 8 --repeats 1 --seeds 42 100 7 999 2026 1 17 373684 314 512 1024 1337 4096 8191 12345 54321 65537 123456 424242 8675309 --cpus 10 --memory 8g --max-workers 9
```

## Suivi

**25/10 00h18 — baseline référence terminée : 20/20 duels, 40/40 parties complètes, sans erreur de script ni horizon manquant.** `results/nuit75_master83e_baseline20x10_20261024.{json,jsonl,manifest.json}` ; code `83e436cc3db35ff18efb685ace4f97eb569f77b1`, bundle figé `ba2012554b094377887f559421345f567c0648937dbff4a7972357be460eb615`, manifeste SHA256 `f6cb49ef20f2a3703cd2bcb928c9b5b784b31e2a8800d472bf4ecb4fcb026a12`, image `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`, 9 workers PC, 1970-1979, carte 256². État Git marqué `dirty=1` parce que le journal et `docs/taches.md` sont modifiés non committés avant campagne, sans modification du code AI dans ce master.

- **Profit OpexAI moyen** : **4 122 708,10 £/an** ; médian : 4 121 686,50 £/an.
- **Profit AAAHogEx moyen** : **7 290 134,25 £/an** ; médian : 7 240 559 £/an.
- **Ratio des moyennes** : **56,5519 %** ; **médiane des 20 ratios appariés** : **58,9112 %** ; les vingt ratios ont un dénominateur positif.
- Écart moyen Opex−AAA = **−3 167 426,15 £/an**, 0/20 profits Opex supérieurs. À profit AAA figé, le seuil 75 % demanderait Opex moyen ≥ **5 467 600,69 £/an**, soit **+1 344 892,59 £/an** sur ce jeu de graines.
- **Échelle des réseaux** : Opex 149,1 véhicules et 83 gares en moyenne, AAAHogEx 280,5 véhicules et 177,5 gares. L'écart de volume des actifs est descriptif, pas une démonstration que toute nouvelle gare est rentable.
- **Ventilation mode sur les 20 graines** (moyennes issues de `summary[].primary_vehicles_by_mode`) : OpexAI **114,0 avions, 4,6 routiers, 30,4 trains, 0,2 navire** ; AAA **52,4 avions, 166,3 routiers, 60,9 trains, 0,8 navire**. Installations (des catégories se recoupent) : Opex **33,2 aéroports, 30,7 stations bus, 2,8 stations camions, 44,4 gares rail** ; AAA **37,4 / 102,8 / 64,4 / 46,8**. OpexAI a déjà plus de deux fois le nombre d'avions d'AAA : hypothèse « il manque des avions » trop sommaire.
- **Attention à la piste routière naïve :** `docs/taches.md` §V242 et `docs/v242_rabattement_diag_20261018.md` documentent 95–97 % de bus AAA joints à une gare AIR/RAIL, profit direct ≈−8 à +3 k£/an ; le test V139 de feeders Opex a **échoué porte A 40×5 −154,3 k£/an, 6V/34D**, avions 91,9→79,1. Construire 160 bus sans mesurer le gain du service parent pourrait empirer les profits. Investiguer les transferts rentables seulement avec sièges vacants réels mesurés et capital oisif, comme V242/V266 non résolus ; un diagnostic shadow reste préalable.
- Objectif nocturne **non atteint** sur ce master. Ne pas comparer causalement les 56,55 % avec 59,7 % de la campagne historique différente.

### Chronologie 1970–1979 sur les 20 mêmes duels

Ratio de la moyenne des profits annuels `profit_year` au checkpoint du 1er décembre de chaque année ; les vingt Opex et vingt AAA présents chaque année :

| Année terminale | Profit Opex moyen (£/an) | Profit AAA moyen (£/an) | Ratio |
|---|---:|---:|---:|
| 1970 | 351 307 | 315 663 | 111,29 % |
| 1971 | 1 411 184 | 1 476 261 | 95,59 % |
| 1972 | 2 104 034 | 2 049 717 | **102,65 %** |
| 1973 | 2 406 725 | 2 545 797 | 94,54 % |
| 1974 | 2 699 696 | 3 087 412 | 87,44 % |
| 1975 | 2 995 362 | 4 021 534 | 74,48 % |
| 1976 | 3 275 085 | 4 895 759 | 66,90 % |
| 1977 | 3 594 101 | 5 904 910 | 60,87 % |
| 1978 | 3 836 538 | 6 465 082 | 59,34 % |
| 1979 | 4 122 708 | 7 290 134 | **56,55 %** |

La divergence est **postérieure à 1972** : Opex part dans la même gamme, puis la croissance des bénéfices AAA est bien supérieure. La chronologie renforce la priorité sur nouveaux projets rentables en 1973–1979 ; elle ne démontre pas si le verrou est le classement, le foncier, la liquidité, la priorité AIR/flotte ou les candidatures.

### AIR-GROW : exposition réelle avant porte A corrigée

Smoke `nuit75_airgrowfix_smoke_1x3_20261025`, source SHA25f40f8e + correctif non committé, bundle `067bb64152ecd66f1f454dd0da2a2ee96c7c6073d244c6ad0d2c977a4aedb816`, référence `air_grow_marginal=0` et variante `=2` sur graine42, 1970–1972, 2/2 sains, aucun script error. Delta Opex **+249 517 £/an** et valeur **−1,116 %**, mais **`diagnostic_only` (1/40 paires)**. Les logs de la variante montrent 159 `phase=rank, decision=accept` et 13 `phase=purchase, decision=accept`; **aucun** de ces événements n'a un `K_N1` passagers qui s'écarte de `K_N × (N+1)/N` de plus de 0,5 passager/an. La correction ancien/nouveau moteur n'est pas démontrée sur cette graine ; ne pas lui attribuer +249 k£.

Instrumentation additionnelle **diagnostique et désactivée au défaut** dans worktree `.worktrees/nuit75-air-grow-corrected` : `old_engine`, `buy_engine`, `rot_old`, `rot_buy`, valeurs déjà calculées, sans nouvel appel API ; 16/16 tests ciblés. Un **diagnostic 5×3** `nuit75_airgrowfix_exposure_5x3_20261025` (graines canoniques 42/100/7/999/2026, deux bras identiques sauf `air_grow_marginal`) est lancé après libération du Docker afin de chercher `old_engine != buy_engine`, en distinguant décisions rank et achats réels. Ce diagnostic ne remplace pas A 40×3. N'engager une A corrigée que si le mécanisme changé est exposé dans les 3 premières années ou avec une raison technique contraire prouvée ; sinon conserver A précédente `fail_primary` et diriger le nouveau test vers l'horizon où le changement opère.

Prochaine étape : smoke du calcul AIR-GROW corrigé, en cours sur la graine 42 durant 3 ans, source bundle `067bb64152ecd66f1f454dd0da2a2ee96c7c6073d244c6ad0d2c977a4aedb816`, campagne `nuit75_airgrowfix_smoke_1x3_20261025`. L'exposition moteur nouveau/ancien doit être vérifiée avant de lancer une porte A complète. Prototype AIR-PELOTON full load placé en attente de revue : l'option équivalente `air_full_load=1` C81 avait déjà fait **−54 % de profit en solo 3×6** (`docs/journaux/20_nuit_2026-09-22.md:24-64`) ; une variante deux avions + chargement complet s'était également effondrée en duel 5×3 (`docs/catalogue_decoupe_phase2_20260929.md:244-256`). Ne pas réexécuter de porte A full load isolée sans hypothèse nouvelle qui réfute ces observations.

## 25/10 — FRONT-PAX-1 complet, AIR-GROW corrigé exposé

**FRONT-PAX-1 :** worktree `.worktrees/nuit75-front-pax1`, base `83e436cc`, `candidates.nut` instrumenté sous `DECISION_LOG` seulement, sans changement des seuils. Smoke r3 `nuit75_frontpax1_smoke_1x1_20261025_r3` complet sans erreur. Campagne diagnostique `nuit75_frontpax1_diag_5x5_20261025`, code bundle figé `fd93c32d9f1fb91cb1d5e4fc40c4d4820668504d19bef171dfc335d390832024`, manifest `3b73d7c42bbfafe9fbd4f688c54d149b3ce413a71afd6d7a73c2efde611057fc`, image `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`, OpenTTD 15.3, 1970–1974, 256², graines 42/100/7/999/2026. **5/5 duels et 10/10 compagnies complets, aucun `failed_runs`, zéro script error.**

Le nouveau lecteur `sweeps/analyse_front_pax_bounds.py` : 45 marqueurs valides, **40 recalculs uniques**, 5 répétitions exactes de jour/payload, 0 erreur de parsing, 0 graine non identifiée. 21 des 25 années-graines ont au moins un recalcul (les quatre autres ne sont **pas** des parties écourtées). Sur **40/40** : `road_reason=delta_nonpositive` et `road_raw=-1` ; `rail_raw=439`, `rail_source=200`, `rail_max=200`, `rail_clamp=rail_max`, `rail_model=crossing` ; ni `road_max` ni taille de carte n'a plafonné le RAIL. Les champs `rail_tau100=29`, `air_tau100=23`, `rail_dwell100=864`, `air_fixed100=2619` décrivent le modèle historique, **pas** une correction C100/C121. Rapport détaillé avec tableaux `.worktrees/nuit75-front-pax1/docs/front_pax1_bounds_diag_20261025.md` et résultats du lecteur sous `results/*_bounds_analysis.{json,md}`. Le lecteur passe 10 tests unitaires; l'absence de preuve de neutralité d'opcodes OFF/ON reste explicite.

À cinq ans, profits annuels moyens OpexAI **2 948 112 £** / AAAHogEx **2 907 548 £**, ratio des moyennes **101,40 %** ; médiane des cinq ratios par graine **91,99 %**. Aucune comparaison Opex instrumenté vs non instrumenté n'existe. Ces cinq graines n'invalident **pas** le ratio du master 20×10 de **56,5519 % / 58,9112 %**, ni le manque **+1,345 M£/an à dix ans**. FRONT-PAX-2 devra compter les **candidats AIR effectivement exclus** à 20–199 tuiles et leurs perspectives économiques ; `rail_raw=439` n'en est pas une preuve.

**AIR-GROW corrigé :** diagnostic `nuit75_airgrowfix_exposure_5x3_20261025`, bundle `20aed72968d8ab7a5afdabad3ce9aeea15f6c7f42b482ac5f509717dea88e389`, manifest `2cbeeb135ac24622d38af4ce66daff9e1da504bd05a462b5ab6cbad323dcdadd`, 5/5 paires et 10/10 parties saines. `AIR_GROW_MARGINAL` expose **39 acceptations d'achat** avec `old_engine != buy_engine` sur 54 à moteurs valides (7/4/14/6/8 par graine), dont 37 rapprochées d'un `V252_ENGINE action=reinforce` même ligne/moteur à 0–1 jour. Les 39 ont `rot_old=c117` / `rot_buy=c121` et `K_N1` non proportionnel à `K_N`, montrant l'activation réelle du correctif. Résultat économique ON−OFF **−99 333,6 £/an**, médiane −77 261, **1 V / 4 D**, Wilcoxon p=0,3125, IC95 [−258 224 ; +68 255] £, valeur **−8,3866 %**, garde −5 % non tenue. **Simple diagnostic 5×3, non porte A.** L'ancienne A 40×3 non corrigée reste `fail_primary`; une nouvelle A corrigée est suspendue sans preuve causale favorable nouvelle, défaut 0 conservé. Rapport `.worktrees/nuit75-air-grow-corrected/docs/air_grow_marginal_capacity_fix_20261025.md`.

**Priorité suivante :** audit indépendant de nuit : IDLE-1/PCAL-02 (V309 : 7 409 tours stables non finançables/231 M opcodes, **0 après 1974** sur trois graines ; mesurer réservation réelle et cache consommé), AIR-MONOPOLY-1 (hypothèse défensive non validée, analyse hors ligne seulement), FRONT-PAX-2 (shadow de paires avec vrais filtres/sites/capital). V294g déjà négatif 40×10, V233 GOODS et V266 sans traction suffisante, C81/full-load déjà négatif. **Aucun levier actuellement démontré de +1,345 M£/an**, aucune adoption, aucun commit/push/merge. Expérimentation FRONT-PAX-2 préparée dans un worktree neuf pour prolonger la mission.

### AIR-MONOPOLY-1 — audit indépendant en lecture seule

À partir de la référence 20×10 `results/nuit75_master83e_baseline20x10_20261024.{json,jsonl}` (20/20 duels sains), les villes ayant deux aéroports AAAHogEx et zéro Opex sont **5,10 en moyenne par graine au checkpoint décembre 1979** (plage 1–10), contre **24,55 villes partagées** avec un aéroport de chaque camp. Les monopoles AAA (2/0) passent de **0,70 en 1970** à **3,65 en 1972**, **4,15 en 1973**, puis **5,10 en 1979** : le nombre de nouveaux monopoles AAA ne suffit pas, seul, à expliquer le décrochage continu des profits Opex/AAA après 1973. Les villes Opex avec aéroport sont 33,05 en 1979, celles AAA 32,3 ; les aéroports moyens Opex/AAA 33,25/37,40. Ce sont des instantanés de présence, pas des profits par marché.

La règle envisagée `~300 k£/ville × 5,1 = 1,53 M£/an` est **une multiplication hypothétique, pas un gisement validé**. Dans l'historique C78 (`docs/22_c78_lignes_vs_aaa.md`), 50 monopoles AAA sur cinq graines cumulaient une attribution de profit AIR d'environ 3,2 M£ au millésime considéré, soit ~64 k£/monopole descriptif et non un profit marginal autonome (liaisons avec deux villes, doubles attributions possibles). Fenêtre médiane premier→second aéroport AAA **211 jours** ; sur 51 propositions Opex avant le second créneau AAA, seules **11** finançables, **7** entrant au portefeuille et **zéro construites**. Le dispositif C83-6 a déjà produit, historiquement, **+165 329 £/an Opex et −314 729 £/an AAA** (+480 058 £/an relatif), effet **déjà adopté et donc non additionnable** au master présent. V95 recensait 60 opportunités de créneaux concurrents, mais profit marginal médian du site nouveau **~3,9 k£**, 0/60 qualifiées (`docs/35_v95_air_post1973.md`). L'analyse causale early-slot 20×10 antérieure (`docs/07_air_early_slot_causal_analysis.md`) aboutissait à environ **−291,1 k£/an AAA AIR** et **+134,9 k£/an Opex**, très loin d'un transfert intégral des profits des villes.

La baseline ne contient pas de `line_telemetry` (valeur nulle) et `station_supply_telemetry=false` : **impossible d'attribuer exactement une valeur privée par ville exclusive avec ces seuls fichiers**. Le rapport V299 comporte de plus un résidu comptable important interdisant d'assigner tout le déficit au seul AIR. Prochaine mesure peu coûteuse : exploitation des séries `jsonl` déjà disponibles (sans opcodes en jeu) et, si les archives contiennent les sauvegardes nécessaires, rapprochement des TownID, des sites et des profits des lignes matures ; sinon une sonde bornée sur événements de disponibilité concurrentielle, réutilisant les caches C83, avant de mesurer son surcoût. **Ne pas activer le multiplicateur défensif ×2** et ne pas déclarer l'objectif +1,345 M£/an atteignable par cette seule piste.

### FRONT-PAX-2 — histogrammes réels de paires AIR, smoke et diagnostic 5×5

Worktree **isolé** `.worktrees/nuit75-front-pax2` depuis master `83e436cc`. La sonde purement passive de `ai/OpexAI/air_planning.nut` produit 3 agrégats `FRONT_PAX2` par cycle AIR **terminé**, selon les bras `newpair`, `hubsite`, `hubhub` et les tranches Manhattan 20–63, 64–77, 78–199, 200+. Elle mesure les paires filtrées sous le vrai `airMin` (`blocked_min` sous `PAX_BAND_ALL`) séparément des paires **hypothétiquement sous `airMin`** (`below_min` dans toutes les phases). Les plafonds de distance AIR/moteur/config sont vérifiés par les **valeurs déjà disponibles** ; aucun site, ROI, financement ou construction additionnel n'est testé. Les compteurs survivent aux slices par `resumeState.frontPax2` (pas de persistance Save/Load), restent OFF sous `DECISION_LOG=0`. Tests de contrat initiaux **46/46** : 6 FP2, 6 AC03, 8 V168, 26 V276, `git diff --check` sain ; le test d'empreinte textuelle V278 a demandé une exclusion précisément bornée aux lignes de sonde, à vérifier indépendamment.

Smoke moteur `nuit75_frontpax2_smoke_1x1_20261025`, graine 42/1970 : **1/1 duel complet et sain**, bundle `0893465c9f771a36638addefe95307a21c52660ff0cf863c3dd2496eb97c20fd`, manifest `30055057c9610061b825726110419dbc80185b932409cc8515693578a17ce16f` ; trois lignes `FRONT_PAX2` de scan 2 le 2 mars, 34 évaluations `newpair` et 4 `hubsite` sous seuil 200 et sous limites de distance. **Pas** 38 lignes indépendantes ni un gain.

Diagnostic `nuit75_frontpax2_diag_5x5_20261025`, mêmes cinq graines 42/100/7/999/2026, 1970–1974, carte 256², bundle **identique au smoke** `0893465c9f771a36638addefe95307a21c52660ff0cf863c3dd2496eb97c20fd`, manifest `bdfc58d3d6c553a7322a4e3c3741adf145365f964e84b71b02fdc536ec523811` : **5/5 parties complètes, zéro `failed_runs`**, toutes compagnies `game_ok`. Ratio de profits en 1974 : OpexAI moyenne **3 047 912 £/an**, AAA **2 797 505 £/an**, ratio des moyennes **108,9511 %**, médiane des ratios par graine **116,1663 %**. **Une seule référence instrumentée, pas d'effet causal de sonde, pas de porte A/B et pas de qualification à dix ans** : les trajectoires diffèrent également de FRONT-PAX-1 et l'identité des opcodes n'a pas été établie.

Premier dépouillement direct des 5 logs : **28 `AIR_PLAN_INPUT`** mais seulement **23 cycles avec 3 lignes FP2/3 bras**, soit **69 lignes** ; cinq cycles initialement démarrés n'ont pas de bilan complet observable, et ne sont pas transformés en comptes nuls. Sur cycles complets, **9 810 évaluations sous `airMin=200`** (`newpair` **2 270**, `hubsite` **6 510**, `hubhub` **1 030**) ; **9 810/9 810** ne dépassent pas les trois plafonds de distance analysés. Par tranches de distance Manhattan : **1 554 (20–63)**, **757 (64–77)**, **7 499 (78–199)**. Par année des bornes **au démarrage du cycle** : 1970 **7 630**, 1971 **751**, 1972 **1 140**, 1973 **143**, 1974 **146** (cycles complets classés 15, 2, 4, 1, 1 dans cet ordre). Le lecteur final `sweeps/analyse_front_pax2.py` vérifie **--strict exit0** et distingue l'année d'émission effective : **1970 771**, **1971 5 219**, **1972 2 846**, **1973 685**, **1974 289** ; une partie des cycles lancés plus tôt finit nettement plus tard. Ces deux calendriers ne doivent pas être confondus. La comparaison économique ne repose jamais sur des cycles incomplets assimilés à zéro. Exports dans le worktree : `results/nuit75_frontpax2_diag_5x5_20261025_analysis.{json,md}`. Il peut y avoir des répétitions de couples entre combos, scanners et années ; aucune métrique de paire unique, de ROI, de site constructible ni de `K_dec` en sortie. Un plafond théorique de revenu annuel complémentaire n'est donc **pas calculable** sur ces seuls agrégats.

**Contrôle technique supplémentaire :** smoke 1×1 master original `nuit75_frontpax2_control_master_smoke_1x1_20261025`, `probes=258` également, graine42/1970, bundle master `ba2012554b094377887f559421345f567c0648937dbff4a7972357be460eb615`, 1/1 sain. Le profit Opex master **465 853 £/an** vs FP2 instrumenté **468 349**, AAA master **364 556** vs FP2 **340 778** et Opex possède 18 gares sur master contre 17 FP2. Les trajectoires sont **différentes**, malgré l'absence de variation volontaire de score/filtre : la surcharge en opcodes/logs et les ticks peuvent amplifier des bifurcations. **Il n'y a pas de preuve de neutralité bit-à-bit** ; les profits 5×5 FP2 ne peuvent pas être interprétés comme un gain relatif au master. Suite : vérifier les occasions effectivement **constructibles et économiquement admises** et le taux de cycles censurés avant toute proposition de correction 200.
**Contrôle technique supplémentaire :** smoke 1×1 master original `nuit75_frontpax2_control_master_smoke_1x1_20261025`, `probes=258` également, graine42/1970, bundle master `ba2012554b094377887f559421345f567c0648937dbff4a7972357be460eb615`, 1/1 sain. Le profit Opex master **465 853 £/an** vs FP2 instrumenté **468 349**, AAA master **364 556** vs FP2 **340 778** et Opex possède 18 gares sur master contre 17 FP2. Dans `AIR_PLAN_PERF scan=2`, master **617 414 opcodes**, **63 probes**, **180 ticks**, terminé le 1er mars ; FP2 **666 909 opcodes**, **71 probes**, **188 ticks**, terminé le 2 mars. L'écart est **+49 495 opcodes (+8,02 %), +8 probes, +8 ticks**, **mais ne mesure pas le coût propre de FP2** car les ensembles de projets/candidats et la trajectoire ont déjà divergé. Les trajectoires sont **différentes**, malgré l'absence de variation volontaire de score/filtre : la surcharge en opcodes/logs et les ticks peuvent amplifier des bifurcations. **Il n'y a pas de preuve de neutralité bit-à-bit** ; les profits 5×5 FP2 ne peuvent pas être interprétés comme un gain relatif au master. Suite : vérifier les occasions effectivement **constructibles et économiquement admises** et le taux de cycles censurés avant toute proposition de correction 200.

### FRONT-PAX-3 — audit de faisabilité des candidats sous 200 (sans code supplémentaire)

**Blocage confirmé au niveau de l'observation :** dans `air_planning.nut`, `OpexAirPairInBand` se produit **avant** `OpexC121CatalogChoice` dans les trois bras (newpair ~714 puis ~756 ; hubsite ~1310 puis ~1345 ; hubhub ~1484 puis ~1516, version worktree FP2). Donc pour les **9 810 évaluations filtrées** de FP2 il **n'existe pas de prévision C121 publiée** ; `AIR_PLAN_SETS` et le C78 annuel n'exposent pas à eux seuls les ancres, la demande ou un ROI utilisable. `OpexC121ChooseRoutePlane` relance calcul de demande/couverture et des moteurs, écrit des caches/états mutables ; `OpexAirSiteStillBuildable` utilise `AITestMode` et une validation de terrain qui peut coûter cher. **Interdit d'appeler ces fonctions en boucle dans le chemin live sous prétexte de shadow neutre**.

Un coût historique descriptif de **1 409 appels C121 pour 23 scans**, avec **20 132 opcodes/appel** moyens, suggère qu'une évaluation naïve des 9 810 visites représente environ **197,5 M opcodes** *à coût constant hypothétique* ; évaluer un seul dossier par bras et par scan représenterait ~**69 × 20 132 = 1,389 M opcodes** (~3,29 % des 42,178 M enregistrés sur le sous-ensemble comparable), **non une mesure de coût réel du nouveau shadow**. Premier filtre envisageable, à prédéfinir hors moteur : clés canoniques couple de villes/site/type/époque, une priorité déterministe et **au plus un candidat par bras et par cycle achevé**, puis analyse de constructibilité et d'économie **dans un replay isolé** plutôt que sur le moteur compétitif. Vérifier le caractère réellement majorant d'un upper de revenu C121, les coûts minimaux avion+deux aéroports, la flotte et les conflits d'emprise ; ensuite la somme de projets doit contraindre le nombre de lignes, le capital et les autres investissements évincés. Les seules valeurs de FP2 ne bornent **aucun gain £/an crédible**, en particulier pour 1975–1979 non mesurés.

Les fourches « même sauvegarde » demandent un contrôle AA/AA de reprise : `Save()` ne sérialise pas l'intégralité de la pile de projets et des décisions, et un fork peut lui-même diverger. Audit FRONT-PAX-3 terminé **en lecture seule**, aucun changement de borne 200, aucun replay ni porte V102 déclenché.

### IDLE-1 / PCAL-02 — correction du diagnostic V309 réserves, effet économique inconnu

Audit isolé `.worktrees/nuit75-idle1` (base `83e436cc`) : `OpexV309IdleFundingBand` distingue, avec le **devis nominal historique potentiellement périmé**, caisse insuffisante, réserve certainement bloquante (marge 0–5 k£), réserve incertaine (5–25 k£) et budget suffisant (≥25 k£). Le sélecteur utilise déjà `OpexAvailableCapital=max(0,caisse−OpexCashReserve)` avec réserve variable de 5 à 25 k£ ; l'ancien V309 n'utilisait que `cash<cost` et sous-décrivait donc la retenue de trésorerie. **Sonde OFF par défaut**, aucune décision changée, aucune API NoAI appelée de plus par le classifieur. Tests **10/10 V309** et voisins **73/73** d'après l'audit ; `diag_v309_idle.py --selftest` et `git diff --check` réussis.

Historique 3 graines × 10 ans V309 (1970–1979), 27 111 boucles : **7 409** états `stable_unfunded` (27,33 %), **231 461 376 opcodes déjà exécutés** dans ces boucles, **165 610 002 opcodes au Sleep** ; **zéro stable_unfunded après 1974** sur les mois observés. 2 263 boucles sans devis, 7 587 avec devis non financé à la sélection, 752 jours constatés `cash<devis` hors réserve. Ni les 231 M d'opcodes ni les 165,6 M au Sleep ne représentent un potentiel d'exécution rentable déjà prouvé : ces sommes **ne sont pas additives**. L'ancienne sonde ON 3×10 avait perdu **−204 448 £/an**, avec valeur **−7,017 %**, preuve de sensibilité au coût de traçage, non effet causal d'un précalcul. V308 mesure environ **988 opcodes par bloc short6**, pas le proxy historique de 430.

Smoke moteur nouveau `nuit75_idle1_reserve_smoke_1x1_20261025` (graine42/1970, carte 256², 1/1 duel complet, zéro script error), `OpexAI[probes=67109122]`, bundle `ecfb285a532438b82b3869ab95a8880a4a7243d1649b93e6103a889406bb8a20`, manifest `fe9c1c8f9a11ed3d744d4d9c2951f0d7e8c105db29fa8a104c6ae5de5402b82c`. Onze flushs mensuels couvrent **1 044 boucles** : 40 devis inconnus, 671 caisse insuffisante, 60 réserve certainement bloquante, 127 incertaine, 146 suffisant. Parmi **839 boucles stable_unfunded** (35 429 468 opcodes), seules **12** sont dans la classe nominale suffisante, pour **590 712 opcodes**, soit **1,67 % des opcodes du proxy stable**. Cela peut signaler un devis vieux de plusieurs jours ; **aucun site AIR pré-calculable ou projet exécutable n'est prouvé**. Les recherches `air.sites` disposent déjà de `AIR_SITE_CACHE`, avec invalidation/revalidation et un coût partiel d'environ 2,01 M opcodes en 1970 graine42/256², sans mesure du surcoût évitable. Prochaine observation PCAL-02 : joindre site calculé, cache réutilisé, devis et projet retenu, date de construction, puis résultat mature, sans nouveau balayage par tick. Détails `.worktrees/nuit75-idle1/docs/idle1_tours_attente_20261024.md`. **Aucun changement de défaut, aucune porte A/B, aucun commit/push/merge.**

### IDLE-1 / V309 — réserve réelle et tours d'attente

L'audit du code a identifié une divergence du diagnostic : `probes.nut` comparait historiquement **trésorerie bancaire** au devis instantané `OpexProjectFinanceCapital`, tandis que le véritable sélecteur `OpexAvailableCapital` exclut une **réserve opérationnelle bornée de 5 000 à 25 000 £**. Le devis `stats.nextProjectCapital` peut être une alternative rejetée et périmée ; il ne prouve ni l'identité ni la constructibilité d'un prochain projet. Les anciens diagnostics V309 donnaient **27 111 boucles**, dont **7 409 attentes stables** (27,33 %), **231 461 376 opcodes** sur ces attentes, **0 après 1974** dans l'échantillon ; l'instrumentation active 3×10 avait une dérive économique **−204 448 £/an**, valeur **−7,017 %**. Les 231 M opcodes **ne sont pas du capital de CPU libre** tant qu'on ne sait pas ce qu'un calcul anticipé permettrait de construire.

Worktree isolé `.worktrees/nuit75-idle1` depuis master `83e436cc`, sans défaut changé. Une sonde **strictement V309** (`probes & 67108864`, réglage par défaut 0) classe le devis connu en quatre bornes fondées sur la caisse et les réserves minimale/maximale : `cash_short`, `reserve_short`, `reserve_uncertain`, `sufficient`, et dénombre `stable_sufficient` sur les attentes sans portefeuille. Aucun appel `OpexCashReserve` ni scan supplémentaire de véhicules par tour, politique non modifiée. Tests ciblés V309 **10/10** et `git diff --check` verts ; le lecteur `sweeps/diag_v309_idle.py` accepte les anciens logs sans inventer leurs nouveaux champs.

Smoke moteur `nuit75_idle1_reserve_smoke_1x1_20261025` sur graine42, année1970, `probes=67109122` (V309+DECISION_LOG+signs) : **1/1 duel complet, 0 erreur script**, bundle `ecfb285a532438b82b3869ab95a8880a4a7243d1649b93e6103a889406bb8a20`, manifest `fe9c1c8f9a11ed3d744d4d9c2951f0d7e8c105db29fa8a104c6ae5de5402b82c`. Onze lignes mensuelles `V309_IDLE` réelles, sorties du lecteur : **1 044 boucles** en 1970, dont **40 sans devis connu**, **671 `cash_short`**, **60 `reserve_short`**, **127 `reserve_uncertain`**, **146 `sufficient`**. Sur **839 `stable_unfunded_loops` / 35 429 468 ops**, **12 `stable_sufficient_loops` / 590 712 ops** seulement (~1,43 % des attentes stables, ~1,67 % des opcodes de cette classe), et les devis peuvent être périmés. Le monstre apparent de tours « récupérables » est donc essentiellement de **l'attente sans financement démontré**, pas une file de bons projets immédiatement constructibles.

**Décision provisoire :** ne pas adopter de précalcul PCAL-02 généralisé ni attribuer 231 M opcodes à un gain post-1972 ; la réserve budgétaire est mieux diagnostiquée, mais aucun avantage de profit qualifié. Poursuivre, si données supplémentaires, la recherche de pré-calcul **consommé** sur 1973–1979 avec réserve/conditions financières et sites vérifiés ; éviter 40×3/20×10 coûteux sans hypothèse causale nouvelle. Aucun commit/push/merge.

### 25/10 — audits GOODS et RAIL-ROI : hypothèse neuve, non qualifiée

Les deux audits indépendants en lecture seule sont achevés, sans fichier changé ni Docker. V299 référence 3 graines × 10 ans, photographie des véhicules survivants en 1979 et profit de l'année 1978 : fret GOOD Opex **60,4 k£/an** contre AAA **802,3 k£/an** (écart descriptif **741,8 k£**) ; fret >160 hors GOOD **671,0 k£**, segment distinct mais sans preuve que les écarts sont récupérables. En comparaison, sur le master `83e436cc` et les **20 graines de la baseline actuelle**, l'écart à combler à profit AAA constant reste **+1 344 892,59 £/an**. Même un comblement hypothétique complet du seul GOOD de V299 serait de l'ordre de 55 % de ce besoin, et le ratio résultant resterait inférieur à 75 % ; les sources/graines et les horloges comptables diffèrent et rendent ce calcul purement indicatif.

**Blocage statique inédit à observer :** dans `OpexFreightCandidates`, `OpexOriginService` repère une gare RAIL proche **sans vérifier son cargo**. Le trajet industrie→ville est rejeté par `ss != null || st != null` dès qu'une extrémité est déjà desservie, avant le contrôle de production `monthly>0`, l'économie, la recherche de quai et A\*. Une usine recevant des intrants peut donc ne pas émettre de candidat GOOD normal ; une ville desservie pour un autre fret peut également être écartée. Le chemin industrie→industrie bénéficie de V179 côté destination, pas le chemin vers la ville. Cette condition ne prouve ni l'acceptation réelle des GOOD au quai ni le profit marginal d'une deuxième ligne ; les tentatives V233 modes 2/3/4/5 ont déjà des verdicts défavorables. Observation prévue : compteur **passif et OFF par défaut** des rejets de paires déjà évaluées, en distinguant GOOD, production positive, source/destination servie, cargo identique ou distinct et bande de distance, sans nouveau scan, A\*, site ni mutation des décisions ; bien dédupliquer les publications PO01C et distinguer **occurrences de génération** de routes indépendantes.

**RAIL-ROI :** en 6×3 V294c adapt400, les opérations A\* diminuent (pour distances <100 : 2,79→0,37 M ; ≥200 : 4,65→1,52 M) mais les lignes passent de 93 à 143 et le capital de 6,05 à 10,38 M£ ; valeur à trois ans **−231,9 k£**. Les 40 SOLO/40 DUEL 10 ans n'étayent pas un seuil de coupe fondé sur le ROI brut des lignes d'âge ≥2 : le quartile le moins rentable en prédiction reste en moyenne positif en réalisé ; l'ancien « ROI faible sur-prédit » incluait des années incomplètes. La nouvelle idée d'arbitrage avant ou après A\* n'est justifiée que lorsqu'une **alternative exécutable, finançable et meilleure** est identifiée ; jamais sacrifier AIR/V252 sur la foi d'un autre ROI de papier. Aucun changement de défaut, aucun V102 ni commit/push/merge.

**Contrôle gratuit sur les anciens logs instrumentés FP2** `nuit75_frontpax2_diag_5x10_20261025_engine`, cinq graines 42/100/7/999/2026 : la somme annuelle des occurrences de rejet `VIVIER_REJECT reason=origin_served`, **tous cargos, toutes générations confondus**, vaut respectivement **9 790 / 13 101 / 16 945 / 16 982 / 16 210 / 15 741 / 11 337** pour 1973–1979 ; appels `VIVIER_GEN mode=rail` **171 / 218 / 267 / 270 / 265 / 248 / 186**. La trace de sélection de projets ferroviaires fret `cargo=GOOD` n'apparaît que **1 / 1 / 1 / 2 / 0 / 3 / 0 fois** ces mêmes années, sans garantie de construction. La hausse des occurrences `origin_served` rend la ventilation utile, **mais aucune occurrence ne constitue une ligne distincte ni n'est attribuable à GOOD**. Comptage obtenu par lecture seule et regex d'événement daté ; ces cinq parties ont été instrumentées, leur trajectoire peut différer du master. Aucun ratio de gain causal n'en est tiré.

### FRONT-PAX-2 prolongé — les observations post-1974 changent la lecture des scans

Le banc `nuit75_frontpax2_diag_5x10_20261025` s'est achevé 5/5 graines et 10/10 compagnies saines, 1970–1979, avec **Opex 4 390 194 £/an** et AAA **6 788 729 £/an** soit ratio descriptif des moyennes ~**64,67 %**. Ce n'est pas un duel variante contre master ; les sondes `DECISION_LOG` peuvent modifier la trajectoire et aucun effet économique causal n'est inféré. Le lecteur strict a été exécuté **sans produire de nouveau fichier** par l'auditeur : `python -X utf8 sweeps/analyse_front_pax2.py 'results/nuit75_frontpax2_diag_5x10_20261025_engine/*.log' --strict`, sortie zéro anomalie.

Sur **35** scans commencés, **30** complets, **5** censurés (contre 28/23/5 à cinq ans). Parmi les seuls cycles complets : **13 370** évaluations sous 200 tuiles (2 082 sur 20–63 ; 1 048 sur 64–77 ; 10 240 sur 78–199), par bras **2 872 `newpair`**, **8 561 `hubsite`**, **1 937 `hubhub`** ; 1 875 évaluations 200+ autorisées dans les bandes du modèle. L'écart sur le diagnostic 5×5 de **+3 560** ne représente pas 3 560 *nouvelles* occasions postérieures : **2 660** sont émises le 8 septembre 1976 à la fin d'un scan graine7 ouvert **en 1970** et censuré par la coupure à cinq ans. Les scans **effectivement commencés de 1975 à 1979** totalisent **900** évaluations sous 200, avec 1/1, 3/2 (une censurée), 1/1, 1/1, 1/1 scans commencés/complets par année, soit **tous les scans complets tardifs sur une seule graine (100)**. Répartition tardive : `newpair` 41, `hubsite` 344, `hubhub` 515 ; les 129 évaluations par an 1977–1979 peuvent être répétées, donc pas de croissance démontrée. Aucun site, C121, ROI, trésorerie ni ligne construite n'est confirmé. **Décision : ne pas relâcher `airMin=200` ni engager une porte AIR ; priorité fret/choix de capital.**

### FREIGHT-ATTRITION — nouvelle sonde passive et smoke

**25/10 — audit long RAIL non-GOOD en lecture seule terminé :** mêmes cinq logs `nuit75_freight_source_diag_5x10_20261025_engine`, aucune nouvelle partie. `PROJECT_CHOSEN`→`RAIL_ATTEMPT` 62/62 tentatives >160 non-GOOD appariées, **53 paires tentées distinctes, 34 construits, 28 échecs** (SITEAB20, ABND2, TRKFAIL4, STNFAIL1, NOPA1). **161–200 : 33/52 réussites ; >200 : 1/10, neuf refus SITEAB**. Après1975, 21 tentatives pour 14 paires, seulement cinq réussites ; les **9 paires non construites** portent au premier échec **386 287 £/an de profit prévu cumulé sur cinq mondes** (77,3 k£/monde/an fictif si tout réussissait), capital prédit £613 589 sur cinq mondes. Il manque le ROI réalisé, le temps de maturation et le coût AIR/V252 évincé. Total tentative 71,917 M opcodes, échecs23,963 M, ABND10,440 M ; 25/62 `search_ops` sentinelles −1 et non zéros. Les défaillances `SITEAB` interviennent avant A\* et sont donc de faible coût CPU, particulièrement >200. L'écart V299 **671 k£/an** couvre aussi toutes les routes fret hors GOOD **jamais choisies**, non mesurables dans `VIVIER_REJECT` agrégé et sur d'autres graines/horloges ; ne pas leur imputer les neuf échecs. **NO-GO comportemental** sur ce seul audit et ne pas relancer V294c adapt400. Pour diagnostiquer physiquement les refus sans API supplémentaire, enregistrer OFF les compteurs `statsA/statsB` déjà en scope de `OpexRailPlatformPlans` pour SITEAB >160 et par longueur, mais ce seul instrument ne créera pas un gisement de +1,345 M£/an. Travail exclusivement lecture seule par l'auditeur, aucun Docker ni commit/push.

**Test de dimension seulement, sans mélange causal des échantillons :** les deux poches V299 descriptives GOOD +741,8 k£/an et fret long hors GOOD +671,0 k£/an font **1 412,8 k£/an**, à comparer au manque **1 344,9 k£/an** sur la baseline master 20×10. Leur récupération intégrale imaginaire ne laisserait que **67,9 k£/an** d'écart favorable, **avant** construction, cannibalisation AIR/V252, demande, transporteur et réactions d'AAA. Parce que les trois graines V299/profits véhicules 1978 et les vingt graines master/profits compagnie 1979 ne sont pas directement comparables, **ce calcul n'est ni une borne de gain, ni une projection 75 %**. Il renforce l'exigence d'une rentabilité nette démontrée et d'autres opportunités complémentaires.

**Reproductibilité supplémentaire :** exports des deux décodages stricts, créés dans les résultats ignorés Git du worktree `.worktrees/nuit75-freight-attrition/results/` : `nuit75_freight_attr_diag_5x10_20261025_analysis_strict.json` (2 757 invocations) et `nuit75_freight_source_diag_5x10_20261025_analysis_strict.json` (2 248 invocations avec détail de déduplication). Aucun fichier étranger écrasé ; les manifests propres aux campagnes restent séparés.

**Observation de capacité GOOD déjà construite, strictement hors jeu :** sur les mêmes cinq logs 5×10 de la seconde sonde, `LINE_REVENUE` de début 1979 donne **9 lignes fret GOOD d'âge ≥2** (quatre graines), **4/9** avec `wait_a >= cap`, **3/9** avec `wait_a >= 3×cap`, **1/9** avec `wait_a >= 5×cap` ; somme des `real_prof` propres 624,815 k£/an, sans valeur causale ni réconciliation compagnie. Sur leurs historiques, `V284` compte **3 `pick kind=wagon` / 3 `done kind=wagon`, 9 `skip traction`, 12 `skip geometry`, aucun second train posé par V284**. Les refus se répètent entre années : ligne35 seed100 en 1979 ~1 247 de file pour `cap=325`, profit ~71,6 k£/an, dernière boucle refusée `geometry`; ligne54 seed100 418 pour 25, profit ~18,5 k£/an, `platform=1`, boucle refusée ; ligne54 seed2026 371 pour 100 mais profit **−2,9 k£/an**. La majorité des lignes n'a pas d'attente ≥ une rame, et certaines sont déficitaires ; un stock à un instant ne prouve pas un débit marginal durable. **NO-GO** pour abaisser les gardes de sécurité V284 ; observation ultérieure seulement sur les quelques lignes GOOD rentables réellement surchargées, avec boucle/traction réalisables et coût d'opportunité AIR/V252. Ne pas confondre avec l'écart V299 de véhicules survivants.

**Complément V299 / échelle fret GOOD (aucun nouveau banc) :** sur les véhicules survivants de 1979 / profits 1978 du bras référence V299 (trois autres graines), AAAHogEx a **4,7 lignes GOOD, 20,0 trains, 802,3 k£/an** contre **1,3 ligne, 1,3 train, 60,4 k£/an** pour Opex. Quotients agrégés **40,1 k£/train/an AAA, 46,5 k£/train/an Opex** ; environ **4,26 vs 1 train par ligne**. Hypothèse nouvelle **d'échelle** plutôt que preuve d'un rendement intrinsèque moindre du train Opex, mais le profit marginal d'une deuxième rame n'est **PAS** ce quotient, et V284 a historiquement zéro pose de second train et de nombreux refus `traction`, souvent peu d'attente aux gares. Ne pas confondre capacité/production théorique et flux réellement transportable, ou additionner ce diagnostic au manque +1,345 M£/an. Prochaine mesure à coût minimal hors live : pour les 33 usines GOOD déjà alimentées sur cinq mondes, relier chargement réel, durée de production, quai, trains/jour et opportunité AIR/V252 avant de concevoir la greffe A ou un renforcement de flotte, sans relancer V233.

**Clôture observation SOURCE 5×10 (complète, sans politique nouvelle) :** campagne `nuit75_freight_source_diag_5x10_20261025`, 5/5 duels et 10/10 compagnies sains 1970–1979 sur 256², bundle `fa1b4489d9525befe5ee53f1c1af1c6eadba3fcad60b607803f81cb169e0e62c`, manifest `20a30de913e52a7f2a8ccc3a16c74b74a8852408872b41cf7c44c6a1ae5547dc`. Moyennes Opex **4 400 353 £/an**, AAA **7 183 206 £/an**, soit **61,26 %** : trajectoires instrumentées, **AUCUN** gain causal sur le 5×10 précédent ou master20×10, et aucune porte V102. Décodeur strict fini : **2 248** invocations, GOOD visité **277** (non visité 1 971), GOOD positive **56 661** occurrences, `origin_served` **55 335**, candidats **992**, autres refus **334** ; **257** invocations avec source, **1 092** lignes source répétées, plafonnement 8 sources jamais atteint, **0 troncature**. **Deux lots** de lignes `FREIGHT_ATTRITION_SOURCE` traversaient un changement de jour (`OpexDecide`), corrigés au décodeur par ordre contigu et fenêtre temporelle bornée, horloge comptable du résumé ; **77/77 tests**, tous cinq vrais logs acceptés, zéro incohérence.

En **1979**, la dédup `(graine, année, industrieID, tuile industrie)` donne **33 usines GOOD distinctes échantillonnées** (graines 42/100/7/999/2026 : **5/6/9/7/6**) : **6,6 par partie**, production mensuelle maximale sur l'année médiane **125 unités**, 16 avec max ≥128, seulement **6 avec max ≥256** (max observé global 570). Sur les dix ans, **36 usines-mondes distinctes**, contre des dizaines de milliers de paires rejetées au fil des générations. Ces 33 usines 1979 correspondent toutes par **tuile exacte** à une destination d'un `RAIL_BUILD` NON-GOOD en amont : Opex alimente effectivement des usines dont la sortie GOOD est bloquée par un service rail existant. Un matching de tuile et une production mensuelle ne garantissent **ni station source A joignable, quai et déchargement GOOD, ville d'accueil, chantier A\*, ROI réel, ni coût d'opportunité AIR/V252**. Les villes retenues par source ne sont que les extrêmes min/max de distance ; le filtre PO01C ne visite pas GOOD à chaque invocation. À titre de test dimensionnel, le manque master **+1 344 893 £/an / 6,6 = ~204 k£/an net par usine**, si cette seule poche devait atteindre 75 % à AAA constant : pas d'estimation économique et probablement exigeant face aux faibles greffes V233 précédentes. **Décision : sonde validée et goulot prouvé, pas de politique activée ni porte A/B.** Nouvelle hypothèse future uniquement sur producteurs GOOD réellement volumineux, joindre strictement **A déjà gare intrants** (non V233 modes rejoués), préserver AIR/V252, et démontrer profit net incrémental sur vrais couples dédupliqués avant V102. Voir rapport worktree `docs/freight_attrition_diag_20261025.md`. **Aucun commit, push ni merge.**

**Deuxième lecture gratuite des mêmes cinq logs à dix ans — fret long non-GOOD au stade chantier :** 196 événements `RAIL_ATTEMPT kind=freight` sur 1970–1979, 189 rapprochés d'un `PROJECT_CHOSEN` pour identifier le cargo (matching même graine et tuiles O/D ; les 7 autres restent inconnus). Dans la période **1975–1979**, **42 tentatives** fret non-GOOD enregistrées sur **27 couples O/D distincts par graine**, **7 `ok=1`**, **35 échecs** : **20 `SITEAB`**, **11 `ABND`**, **2 `SITEA`**, **2 `SITEB`**. **17/42** tentatives ont une distance >200, dont 9 `ABND` et seulement 2 réussites ; un plafond de génération 200 ne signifie pas absence de recherche >200 (V269 peut relâcher le fret tardivement). Les 20 `SITEAB` ne portent que sur **13** couples distincts, et les 11 `ABND` sur **8** ; les causes se répètent, le calcul du profit prédit `pred_profit` et les opcodes `ops` par événement ne sont pas des valeurs privées additionnables. Aucun cargo GOOD n'a été rapproché des 42 tentatives tardives, ce qui rend le blocage GOOD **en amont** cohérent mais non causal. Ces événements ne couvrent pas les projets jamais choisis, ni les bénéfices des lignes construites ou l'opportunité AIR/V252 ; aucune politique de site, de distance ou d'A\* n'est justifiée à ce stade.

**Bilan final 5×10, après le smoke décrit ci-dessous :** `nuit75_freight_attr_diag_5x10_20261025`, bundle identique au smoke, manifeste `f9eac7387d9aa73347d429da9ad11236e3fe4687f70823f98bc80372095f753e`, 5/5 duels et 10/10 compagnies saines 1970–1979, 256². OpexAI **4 318 476 £/an** vs AAAHogEx **7 794 482 £/an**, ratio descriptif **55,40 %**, sans variante causale. Le décodeur a lu **2 757** invocations terminées (2 525 legacy, 232 PO01C), 320 avec GOOD visité, **0 tronquée**. Toutes années : 65 615 occurrences GOOD de production positive, **64 551** rejetées `origin_served`, 805 candidats avant TOP_K et 259 autres refus. En **1975–1979** : 54 184 occurrences positives, **53 496 refus origin_served (98,73 %)**, dont 47 810 « autre/mixte cargo » du rail représentatif (**89,37 % des rejets**), 540 candidats, 148 autres refus. En **1979**, GOOD visité sur **48/448** invocations (400 non visitées, une non-visite n'est pas un zéro) ; sur 10 620 évaluations positives, **10 470** rejetées : **9 186 source seule, 30 destination seule, 1 254 les deux**, distances **1 579 ≤78, 3 448 entre 79–160, 5 443 >160** (y compris fraction >200 hors `railMax=200`). Lignes représentatives mêmes/autres/mixtes/inconnues : **1 087 / 9 076 / 307 / 0**. Graines 42/7, 1975–79 : 8 833/15 915 occurrences positives, toutes rejetées « autre cargo », zéro candidat GOOD admis ; cela peut n'être que **quelques paires réexaminées**. **Blocage réel de génération**, sans preuve de profit privé récupérable ou station réutilisable. Prochaine observation la moins chère : **échantillon déterministe dédupliqué d'IDs source/destination et de production**, distance ≤200, station A et cargo initial, sans scan/A\*/site/devis supplémentaire ; mesurer quai/acceptation/ROI et coûts AIR/V252 avant une éventuelle nouvelle politique opt-in. Voir le [rapport complet](../../.worktrees/nuit75-freight-attrition/docs/freight_attrition_diag_20261025.md). Aucun défaut changé, aucune porte A/B, commit/push/merge.

Implémentation isolée dans `.worktrees/nuit75-freight-attrition` à HEAD `83e436cc`, non committée : `ai/OpexAI/candidates.nut`, la copie PO01C générée de `ai/OpexAI/po01c_generators.nut` par `sweeps/po01c_generate.py`, `sweeps/diag_freight_attrition.py`, tests et fixture. `FREIGHT_ATTRITION schema=1` sous le seul `DECISION_LOG` (désactivé en jeu normal) et seulement sur carte 256² sans V276 ni régénération ciblée, une émission à la fin d'une invocation de générateur. Les 36 classes GOOD de production positive croisent distance ≤78, 79–160, >160, côté desservi (source/destination/les deux) et cargo de la ligne rail représentative (même/autre/mixte/inconnu). Compteurs distincts pour `good_zero`, `good_kept` avant Top-K et `good_other` ; volume limité à 16 384 évaluations GOOD par invocation, `truncated=1` signale toute perte ; `visited_good=0` distingue expressément cargo non parcouru lors de l'arrêt PO01C au premier cargo productif. **Aucun nouveau scan, site, A\*, calcul économique, API par paire, changement de politique ou de défaut.** L'API cargo est appelée seulement une fois par cargo effectivement visité, quand le diagnostic est ON. Tests ciblés **71/71** selon l'agent, et 8 sonde / 27 PO01C / 26 V276 réexécutés par le prime ; décodeur fixture strict et `git diff --check` OK. La neutralité chronologique et le coût en VM de la sonde restent non démontrés.

Smoke réel `nuit75_freight_attr_smoke_1x1_20261025`, référence unique `OpexAI[probes=258]`, graine42 1970, carte256², bundle `eae876964a787bc544274e22df283195a10ada28838297aba6b87fb452ace1ec`, manifeste `b55f3111bd9c168dde73902592e7b190dfbe2dbaf4ebb1c793da7b54ee2fa560` : 1/1 duel complet, sans erreur Squirrel, Opex **472 780 £/an**, AAA **363 725 £/an** ; ce sont les deux compagnies d'une référence instrumentée, non un delta causé par le code. Décodeur strict sur les logs : **3 invocations terminées**, GOOD visité dans les 3, 0 tronquée, **1 856 évaluations GOOD à production mensuelle nulle**, **0 GOOD à production positive et donc 0 `origin_served` pertinent** sur cette unique année de démarrage. La sonde fonctionne techniquement, mais le smoke ne peut pas répondre au blocage post-1973. Une référence passive 5 graines × 10 ans `nuit75_freight_attr_diag_5x10_20261025` est lancée, sans variante comportementale ni porte A/B, pour vérifier l'exposition tardive avant toute proposition. **Aucun commit/push/merge.**


## 25/10/2026 — variantes comportementales GOOD source et N75-CAP

Reprise du master 83e436cc, deux nouveaux worktrees séparés, code opt-in désactivé dans les quatre difficultés, aucun défaut modifié ni commit/push/merge ; charges Docker séquentielles uniques. Référence qualifiée 20 graines x10 ans : Opex 4 122 708,10 £/an, AAA 7 290 134,25 £/an, ratio des moyennes 56,5519 %, médiane des ratios appariés 58,9112 %, objectif 75 % non atteint.

GOOD (`good_source_rail_join`) : 108/108 tests ciblés verts, smoke 1x1 sain. Exposition diagnostique seed100 1x10 : 6 lignes GOOD effectives sur source A réellement jointe, 28 tentatives dont 22 échecs (16 SITEAB), delta Opex +838 426 £/an sur un monde seulement. Porte A 40x3 `nuit75_goodsource_porteA_40x3_20261025` 80/80 parties, delta moyen +4 262,075 £/an, V/D/E 12/13/15, p=0,9789, IC95 [-11 334,4 ; +22 239,825] £/an, seuil +89 549,093 £/an, valeur +0,4634 % : FAIL_PRIMARY. Pas de B.

N75-CAP (`n75_freight_capacity`) : tests ciblés verts, smoke 1x1 sain. Diagnostic seed100 1x10 : aucun `N75CAP screen/pick/done`, delta Opex -190 538 £/an (un monde), aucun gain attribuable à une seconde rame N75. Porte A 40x3 `nuit75_freightcap_porteA_40x3_20261025` 80/80 parties, delta +6 794,725 £/an, V/D/E 21/16/3, p=0,5016, IC95 [-8 269,775 ; +23 215,575] £/an, seuil +90 301,657 £/an, valeur -1,3688 % : FAIL_PRIMARY. Pas de B.

Les deux politiques restent OFF, worktrees et résultats ignorés préservés. Rapport de détail et hashes : `docs/nuit75_variantes_comportementales_20261025.md`.
## 25/10/2026 — proposition de qualification des leviers tardifs, SANS changement de règle

**Constat et distinction d'horizons.** La référence master 20×10 passe d'un ratio des profits moyens Opex/AAA de **102,65 % en 1972 à 56,55 % en 1979**. Une porte A V102 `gain_short` 40 graines × 3 ans mesure exclusivement 1970–1972 ; elle ne permet donc pas de prouver le gain d'une politique intrinsèquement inactive avant 1973. Les options GOOD source A et N75-CAP restent **rejetées selon leurs portes A40×3 réelles**, qui ne sont ni annulées ni réécrites.

**Option conforme au §4 d'`AGENTS.md`, à décider séparément AVANT tout nouveau lancement tardif :** pour une **nouvelle** variante dont l'inertie à 3 ans est démontrée par traces datées, pré-enregistrer explicitement une **porte A personnalisée `gain_short` 40 graines × 10 ans**, 1 répétition, même arbre et seuls réglages opt-in 0/1 différents, 1970 sur 256², métrique primaire delta `profit_year` Opex ON−OFF en décembre1979, Wilcoxon exact bilatéral p<0,05, borne basse de l'IC95 bootstrap >0, gain moyen >=4 % du profit de référence, garde de valeur `company_value` >=−5 %. Avec `run_c66_reference.py`, fixer `--decision-rule gain_short --required-seeds 40 --required-years 10 --years 10 --min-useful-primary-delta-pct 4 --primary-metric profit_year --value-guard-max-loss-pct 5` et les 40 graines canoniques. Le §4 prévoit expressément ce profil `custom` **si l'exposition prouve l'inertie à trois ans** ; ce n'est pas une nouvelle règle que nous appliquons de notre propre chef, ni un raccourci après un A40×3 échoué.

La **porte B reste distincte et obligatoire** après A40×10 complète et `pass` : **20 graines × 10 ans**, `non_erosion`, borne haute de l'IC95 bootstrap du delta >=0, garde de valeur −5 %, profit privé Opex primaire. Il faut l'accord explicite de l'utilisateur pour tout banc B individuel tel que le précise le §4.1, même si une qualification générique A/B est envisagée. La métrique « atteindre 75 % du profit AAA » est un **objectif externe supplémentaire** mesuré en ratio de profits moyens et médiane de ratios appariés sur une campagne complète 20×10 ou 40×10, pas un substitut aux portes. Même cohorte, graines, cartographie, adversaire figé et provenance bundle/manifeste par campagne ; un seul Docker, <=9 workers, 10 CPU et 8 GiB au PC ; Save/Load, tests, smoke et mesure d'exposition préalables. Les `fail_primary` des deux essais N75 déjà clos demeurent les verdicts historiques et ne sont pas « requalifiés » par une nouvelle horloge.

**État de décision : simple proposition documentaire, NON autorisée comme protocole de lancement dans cette séquence, non exécutée.** Aucun changement d'`AGENTS.md`, des règles V102, des défauts ou du protocole des variantes précoces. Attendre une décision utilisateur explicite sur chaque variante tardive et son horizon A40×10. En attendant, poursuivre seulement des mécanismes observables et efficaces dès 1970–1972 avec le parcours courant A40×3 → B20×10.

## 25/10/2026 — étude et pré-enregistrement d'un levier précoce de déploiement C75

**Audit rétrospectif, pas une preuve de causalité.** Sur les 20 graines × 10 ans de la baseline master `83e436cc`, fin décembre 1970/1971/1972, OpexAI possède en moyenne respectivement 62 393 / 118 395 / 218 884 £ en caisse contre 36 655 / 77 927 / 253 452 £ chez AAAHogEx, et un emprunt moyen 300 000 / 300 000 / 179 500 £ contre 289 500 / 90 500 / 29 000 £. Le déficit tardif n'est donc pas corrigible par un simple réemprunt 1970–71. L'audit C75 par lecture JSONL compte en 1971 : 147 arrêts `k_pass`, 35 bypass consommés ; en 1972 : 333 arrêts `k_pass`, 184 bypass consommés. Ce sont des **événements de passes**, non des projets uniques, et ils ne prouvent ni sites valides, ni avance effective de construction, ni profit supplémentaire.

**Variante candidate pré-enregistrée AVANT diagnostic et résultats :** arbre/worktree isolé `.worktrees/nuit75-early-c75-second` sur `83e436cc`, comportemental et opt-in `n75_second_newline_bypass` (défaut 0 sur easy/medium/hard/custom). Mode 1 destiné exclusivement à observer les projets réellement finançables et vivants derrière un arrêt C75 ; mode 2 destiné à autoriser **au plus un second bypass K_pass par passe** en 1971–1972, après le premier bypass C75 existant, uniquement sur nouvelle ligne (jamais flotte/maintenance), en conservant la caisse après réserve, la validité des sites, C77, le plancher C80 et les transactions A* rail. Ne pas dégrader le comportement OFF, ne pas convertir les demandes `fleet` en nouvelles lignes. Quantifier sous trace les clés distinctes de projets, les tentatives, les chantiers physiques réellement construits et les semaines d'avance avant de présumer un bénéfice. Risque : accélérer des dépenses peu rentables ou déplacer de meilleurs projets AIR/V252 ; la baseline ne prouve pas d'opportunité marginale d'au moins +4 % en 1972.

**Parcours conditionnel fixé avant les résultats :** contrats Squirrel/Python et Save/Load, revue indépendante, smoke causal 1×1 graine42 (1970) pour compilation/santé, diagnostic de couverture 1971–1972 si le smoke n'expose pas le nouveau chemin, puis seulement si exposition de constructions distinctes et plausiblement rentables, porte A `gain_short` 40×3, 1 répétition, 1970/256², référence `OpexAI[n75_second_newline_bypass=0]`, variante `OpexAI[n75_second_newline_bypass=2]`, `--min-useful-primary-delta-pct 4 --primary-metric profit_year --value-guard-max-loss-pct 5 --required-seeds 40 --required-years 3 --years 3`, graines canoniques, seuil Wilcoxon bilatéral p0<0,05 et gain moyen >=4 %, garde valeur −5 %. Porte B `non_erosion` 20×10 uniquement si A complète `pass` et accord explicite pour ce banc précis conformément à `AGENTS.md` §4.1 ; aucune requalification post hoc. Au PC un seul Docker à la fois, 10 CPU, 8 GiB, 9 workers maximum. Aucune campagne 40×3 ni B de cette nouvelle variante lancée au moment de cette écriture, aucun défaut existant ni règle modifié, aucun commit/push/merge.

**Résultat effectif de N75 second bypass : NON-EXPOSITION, fermeture avant porte A.** Worktree `.worktrees/nuit75-early-c75-second` créé sur SHA `83e436cc`, défaut 0 toutes difficultés, modes 0 OFF / 1 shadow / 2 ON ; 193 contrats ciblés OK (`PYTHONPATH=sweeps`), `git diff --check` OK, revue critique indépendante GO pour smoke au défaut V131=0 (V131=1 demanderait garde de réparation rail supplémentaire). Smoke `nuit75_early_c75_smoke_1x1_20261025` 1970 graine42, 2/2 jeux sains, delta ON−OFF 0, bundle `e076291ec739b9bcddb1ad6f07bf5b32d60e0f4ac89b35444f92de66a731170b`, manifeste `762cc029003673d1e005154a98f39c7553fe296562030642ba2f0e2d61bcb2e6` ; aucune exposition attendue en 1970. Diagnostic apparié 2×3 `nuit75_early_c75_expo_2x3_20261025` (graines 42,100), 4/4 saines, **14** clés annuelles distinctes, **1** tentative ROAD additionnelle physiquement rejetée, **0** `phase=built`, delta moyen **−38 814 £/an**, valeur **−4,598 %** ; manifeste `95b5b3732ce03d3f7759c63a4321f7fc08844ec5efa746ef3fff4ff5084a7cd6`. Complément indépendant 5×3 `nuit75_early_c75_expo_more5x3_20261025` (7,999,2026,1,17), 10/10 saines, **51** clés annuelles distinctes, **0** tentative additionnelle, **0** construction, delta moyen +94 192 £/an, valeur +1,292 %, manifeste `3bf729bde9f76705220adbf5cbaa75eb508b5b0ed9c739f1c362426f796fbb7d`. Les deux diagnostics même bundle, 1970–1972, 256², 9 workers, 10 CPU, 8 GiB, `--probes 2 --script-debug` ; l'analyseur `sweeps/analyse_n75_early_c75.py` déduplique fichier+année+clé et classe les événements. Les `N5` inscrits dans le jeu ne sont pas dans les logs moteur, d'où compteurs de signes nuls dans l'analyseur ; les phases `N75_EARLY_C75` sont bien présentes dans les logs. **Sur sept graines : 65 clés distinctes par jeu/année, 1 tentative supplémentaire sans chantier et 0/7 graine avec chantier supplémentaire**. L'écart des profits 2×3/5×3 ne prouve donc aucun mécanisme N75 ; l'instrumentation peut elle-même déplacer l'ordonnancement. **Pas de A40×3 : prérequis d'exposition non rempli ; pas de B.** Conserver réglage OFF, code et données expérimentaux sans commit/push/merge. Ne jamais relire `C75_BYPASS phase=consumed` comme preuve de construction.

**Nouvelle hypothèse précoce distincte, étude N75-C75-REFUND avant résultat :** Le bypass historique est marqué `c75BypassConsumed=true` dans `task_projects.nut` **avant** le filtre obligatoire `OpexC80ProjectBelowMarginalFloor`; si ce filtre veto le candidat, aucune construction ne tire parti du bypass, mais l'unique jeton C75 reste perdu pour les candidats suivants de la même passe. Tester dans un nouveau worktree sur `83e436cc`, réglage isolé `n75_c75_refund` 0 OFF / 1 shadow / 2 ON (toutes difficultés OFF), strictement 1971–1972 et uniquement si **premier bypass C75 a été marqué sur ce candidat et rejet C80 immédiatement après**, jamais si chantier lancé, ni rail pending, ni échec physique, ni flotte. ON rend à la passe son jeton C75 sans contourner C80, sans créer une deuxième exception après succès ; la passe continuera historiquement à examiner ses autres candidats. SHADOW observe uniquement ces décisions et candidats, les clés uniques, budgets/rangs/profits, nouveaux projets réellement bâtis en ON. Ce n'est **pas** un relâchement du plancher C80, de la réserve, de C77 ou de l'A*. Pré-enregistrement : contrats + revue, smoke 1×1 1970 puis exposition 1971–1972, porte A standard 40×3 `gain_short`, seuil +4 % et Wilcoxon exact p0<0,05 / valeur −5 % seulement si de vraies constructions sont avancées ; B `non_erosion` 20×10 seulement après A `pass` et autorisation utilisateur spécifique §4.1. Ne pas qualifier sur 5×3. Même 1970/256², un Docker, 10 CPU/8 GiB, ≤9 workers, même bundle OFF/ON, aucun défaut/commit/push/merge modifié. Les 40 logs de `rail_cal4_40x10_multimodal_pc_20261021_engine` montrent en 1971/1972 82/487 consommations C75, mais **pas** combien furent rejetées précisément par C80, ni le bénéfice du remboursement ; ces compteurs ne suffisent donc pas à lancer directement A.

**Verdict N75-C75-REFUND : restitution exposée, mais aucun chantier attribuable en 10×3 ; abandon avant A.** Worktree non committé `.worktrees/nuit75-early-c75-refund` sur `83e436cc`, bundle SHA256 `244de36cc2fa95c2f418f73571c95461b3537ac5006b9941b8317da1096c0f17`, defaults inchangés 0/1/2 ; **170 tests ciblés** consolidés PASS (l'auteur a aussi 173 PASS), revue indépendante READ ONLY GO pour le smoke, `git diff --check` PASS. Tests historiques de limite de réglages ne sont pas assouplis : 58 réglages précédents prouvés séparément du nouvel opt-in ; empreintes PO01C inchangées une fois retirés les octets exacts de l'option N75. Smoke `nuit75_c75refund_smoke_1x1_20261025`, manifest `6b850c673cab41666cf1b0db66d7826680afe03bc4d8255e81a9908a4f279ecc`, 2/2 jeux complets graine42/1970, ON−OFF 0. Diagnostic apparié `nuit75_c75refund_expo_5x3_20261025` graines 42,100,7,999,2026 (manifest `f0fed6f59120a498737cb5968e0aaf0236894b888ab0a3bdcff9a0a46cb54a5e`) : 10/10 jeux complets, **8 `phase=refund`** sur graines 42/999, **5 `postrefund=rejected`**, **0 `postrefund=attempt`, 0 `postrefund=built`**, delta Opex ON−OFF **+562 £/an**, V/D/E 1/0/4, p=1, valeur −0,413 % ; seuil A indicatif +92 325 £/an. Complément `nuit75_c75refund_expo_more5x3_20261025`, graines 1,17,73,314,512 (manifest `4410a5a469df6cb40a4ad32c2682828fa67b8ffd8a595b27891f700b5ab9044d`) : 10/10 jeux complets, **5 `phase=refund`** sur 4 graines, **4 `postrefund=rejected`**, **0 `postrefund=attempt`, 0 `postrefund=built`**, delta +14 094,4 £/an, V/D/E 2/0/3, p=0,5, valeur −1,102 %, seuil A indicatif +90 493 £/an. Les 2 diagnostics utilisent même bundle, 1970–1972, 256², 9 workers/10 CPU/8 GiB, `--probes 2 --script-debug`; les journaux moteur sont sans erreur `[E]` et la déduplication ne confond pas reprises de candidats et projets uniques. **Bilan 10 graines et 20 parties saines : 13 restitutions observées, 9 seconds candidats rejetés C80, zéro tentative d'exécuteur et zéro construction physiquement prouvée après remboursement ; aucune porte A40×3 ni B20×10.** L'écart de profit n'est pas imputable à des lignes construites par REFUND, et l'effet de l'instrumentation sur l'ordre d'exécution est une réserve. Aucun défaut/adoption/commit/push/merge. Cette séquence complète le test des deux hypothèses précoces C75 isolées, non exposées au sens économique ; **objectif 75 % à dix ans toujours NON démontré**. Le protocole tardif A40×10 proposé plus haut demeure **documentation seulement**, à décider explicitement ; ne pas modifier AGENTS.md ni requalifier GOOD/N75-CAP.

## 25/10/2026 — N75 AIR TRUE QUOTE après C75-REFUND : code, 215 tests, revue, smoke et 10×3 d'exposition ; clos sans porte A

**Audit précoce sans nouveau moteur** : le remboursement reporté en 1972 libérerait au maximum 120 500 £/graine de capital sur les 20 graines master, sans projet supplémentaire prouvé (NO-GO) ; les 40 traces de référence montraient en 1972 86 couples AIR finançables rang>0 derrière RAIL rang0 malgré profit AIR ≥1,5× celui de RAIL, mais un plafond très optimiste de +65,7 k£/an pour les trois meilleurs écarts par monde, sous la porte A ~90 k£ (NO-GO). L'anomalie nouvelle et distincte retenue : `task_air.nut` cote parfois le renfort AIR 1→2 au moteur ancien alors que V252 en achète un autre. Dans cinq logs instrumentés existants, 53 achats 1→2 avaient réellement changé de moteur, prix catalogue 32 812–153 808 £ contre 38 964 £ ancien, sans preuve de profit incrémental.

**Variante isolée opt-in** dans `.worktrees/nuit75-early-value-v1`, base `83e436cc` : `n75_air_true_quote` 0 OFF/1 shadow/2 ON, easy/medium/hard/custom=0. Fenêtre 1970–1972, 1→2 sous cible C121 uniquement. Devis moteur V252 mis en cache par ligne/moteur/mois, budget et score corrigés mais prévisions de profit C121/V161 inchangées (donc PAS vrai ROI du nouveau moteur). Revalidation moteur/prix à l'exécution, refus stale, sûreté du clone de repli plus cher limitée au seul achat N75, marge `OpexCashReserve()+1000` maintenue. Aucun déblocage AIR_GROW/V217, C75/C80/C77/PO01C, priorité, défaut historique, état SaveLoad ou protocole V102 modifiés. Cache/projet transitoires, SaveLoad vérifié statiquement mais pas par recharge moteur réelle ; coût d'opcodes non isolé. Revue critique indépendante READ ONLY : GO smoke après correction P1 (prix périmé/repli), **215 contrats ciblés PASS**, `git diff --check` PASS, aucune erreur évidente de syntaxe Squirrel (moteur vérifie réellement).

**Smoke `nuit75_truequote_smoke_1x1_20261025`** graine42/1970 : 2/2 parties complètes, moteur sain, ON−OFF −7 £/an, `diagnostic_only`, manifeste `558ac9791cadd13b60b715513deabdd7191bf0e8e51dad981b7dc689600768c1`. **Exposition** `nuit75_truequote_expo_5x3_20261025` (42/100/7/999/2026), 10/10 jeux complets, 51 renforts N75 effectivement construits, +10 avions nets, delta profit annuel +44 530,8 £/an, 4V/1D, p=0,625, seuil +91 913 £ ; manifeste `758a72cfd544cf0599b22f22e340221f9250f91f8814c4e2e34ea6f957cfcb09`. Complément `nuit75_truequote_expo_more5x3_20261025` (1/17/73/314/512), 10/10 jeux complets, 44 achats N75, +3 avions nets, delta +19 837,6 £/an, 2V/3D, p=1 ; manifeste `d9c400f5e26285f28a4b2c1cc41cd3bddf130b6c9564aad00d297b5646d4e677`. Même bundle SOURCE gelé `4bd4c8e3f9a6023a513980874a624f345071fa26b710913927536a3ed484ee12`, 1970–1972/256²/OpenTTD15.3, `--probes 258 --script-debug`, 9 workers, 10 CPU/8 GiB, un seul Docker.

**Bilan combiné descriptif 10 graines, 20/20 parties saines** : 95 `N75_QUOTE phase=built` (ne sont **pas** 95 achats supplémentaires), 0 divergence prix moteur catalogue construit vs devis N75, 0 `stale` ; +13 avions nets, −3 nouvelles lignes AIR nettes, 0 nouvelles lignes RAIL nettes mais reconfigurations par graine. `phase=plan` est répétée 8 985 fois et ne représente pas des projets uniques. ON−OFF `profit_year` moyen **+32 184,2 £/an (+1,403 %)**, médiane différences +66 007 £/an, 6V/4D, Wilcoxon exact bilatéral **p=0,4921875**, IC95 bootstrap indicatif [−99 146 ; +149 534] £/an, seuil 4 % **+91 757 £/an**, valeur de compagnie +4,41 %. Le prix du moteur reste un tarif catalogue, pas une preuve du débit bancaire réel, et le changement d'ordonnancement/opcodes est un confondant. Analyse reproductible `sweeps/analyse_n75_truequote.py`, résultats `/results/nuit75_truequote_*`, tableaux `_mechanism.json`, rollup `_10x3_20261025_rollup.json`, et rapport détaillé `.worktrees/nuit75-early-value-v1/docs/nuit75_air_true_quote_20261025.md`.

**Verdict : mécanisme PHYSIQUEMENT exposé mais effet trop limité et non significatif pour satisfaire le prérequis de plausibilité +4 % : PAS de porte A40×3, PAS de B20×10.** Ne pas interpréter le +1,4 % descriptif 10×3 comme qualification V102 ni résultat 75 % à dix ans. Conserver tous les artefacts pour audit, opt-in OFF au défaut des quatre difficultés, aucun commit/push/merge. Ne pas relancer cette variante à l'identique. L'objectif de ≥75 % en 20×10 reste NON atteint/démontré.

**25/10 — N75-CAP, A40×5 multimodal `nuit75_freightcap_porteA_40x5_20261025` :** verdict **`fail_primary`**, 40 paires, Δ `profit_year` moyen **-9,137.62 £/an**, médiane +26,449.50, V/D/E=21/18/1, Wilcoxon p=0.9285482017548929, IC95 bootstrap [-80,415.73; +61,403.30], garde valeur -0.177 %, bundle `7814fbdcfcc9a93a8dffc2b0a5b4e996ae238d134d69945f0f3dc69913c2ddcc`. Seuil indicatif 4 % = 114705.40400000001 £/an. B20×10 déclenchée seulement si A passe ; un résultat A40×5 n'autorise pas à déclarer un ratio de profit à dix ans.

**25/10 — GOOD, A40×5 multimodal `nuit75_goodsource_porteA_40x5_newformat_20261025` :** verdict **`fail_primary`**, 40 paires, Δ `profit_year` moyen **-40,727.50 £/an**, médiane -47,177.50, V/D/E=13/27/0, Wilcoxon p=0.0918240616483672, IC95 bootstrap [-101,369.38; +21,796.25], garde valeur -2.176 %, bundle `4da09e927f64bc110ee2da6752131226a2ab9fdd792e0670f2b80bcc1790b808`. Seuil indicatif 4 % = 113747.221 £/an. B20×10 déclenchée seulement si A passe ; un résultat A40×5 n'autorise pas à déclarer un ratio de profit à dix ans.

**25/10 — AIR-GROW corrigé, A40×5 multimodal `nuit75_airgrowfix_porteA_40x5_20261025` :** verdict **`fail_primary`**, 40 paires, Δ `profit_year` moyen **-23,434.75 £/an**, médiane -71,454.00, V/D/E=19/21/0, Wilcoxon p=0.5099141109240009, IC95 bootstrap [-100,394.50; +54,630.70], garde valeur -0.347 %, bundle `20aed72968d8ab7a5afdabad3ce9aeea15f6c7f42b482ac5f509717dea88e389`. Seuil indicatif 4 % = 111791.56599999999 £/an. B20×10 déclenchée seulement si A passe ; un résultat A40×5 n'autorise pas à déclarer un ratio de profit à dix ans.

**Audit indépendant A — `nuit75_freightcap_porteA_40x5_20261025` : VALIDE**, 80 duels, 160 compagnies, 40/40 paires, 0 erreur script, 0 partie invalide et 0 bilan invalide. SHA source `7814fbdcfcc9a93a8dffc2b0a5b4e996ae238d134d69945f0f3dc69913c2ddcc` ; verdict économique `fail_primary`. reference (fin 1974) : 40 paires avec AAA positif, Opex moyen 2,867,635.10 £/an, AAA moyen 3,080,053.88 £/an, ratio des moyennes **93.1034 %**, médiane des ratios appariés **95.2716 %**. n75freightcap (fin 1974) : 40 paires avec AAA positif, Opex moyen 2,858,497.48 £/an, AAA moyen 3,005,389.73 £/an, ratio des moyennes **95.1124 %**, médiane des ratios appariés **97.4096 %**.  Les ratios à 5 ans ne remplacent pas les mesures à 10 ans ; B uniquement si l'A officielle passe.

**Audit indépendant A — `nuit75_goodsource_porteA_40x5_newformat_20261025` : VALIDE**, 80 duels, 160 compagnies, 40/40 paires, 0 erreur script, 0 partie invalide et 0 bilan invalide. SHA source `4da09e927f64bc110ee2da6752131226a2ab9fdd792e0670f2b80bcc1790b808` ; verdict économique `fail_primary`. reference (fin 1974) : 40 paires avec AAA positif, Opex moyen 2,843,680.52 £/an, AAA moyen 3,087,227.10 £/an, ratio des moyennes **92.1112 %**, médiane des ratios appariés **95.8158 %**. goodsourcerailjoin (fin 1974) : 40 paires avec AAA positif, Opex moyen 2,802,953.02 £/an, AAA moyen 3,125,139.67 £/an, ratio des moyennes **89.6905 %**, médiane des ratios appariés **91.4316 %**.  Les ratios à 5 ans ne remplacent pas les mesures à 10 ans ; B uniquement si l'A officielle passe.

**Audit indépendant A — `nuit75_airgrowfix_porteA_40x5_20261025` : VALIDE**, 80 duels, 160 compagnies, 40/40 paires, 0 erreur script, 0 partie invalide et 0 bilan invalide. SHA source `20aed72968d8ab7a5afdabad3ce9aeea15f6c7f42b482ac5f509717dea88e389` ; verdict économique `fail_primary`. reference (fin 1974) : 40 paires avec AAA positif, Opex moyen 2,794,789.15 £/an, AAA moyen 3,082,243.58 £/an, ratio des moyennes **90.6739 %**, médiane des ratios appariés **92.5360 %**. airgrowmarginal (fin 1974) : 40 paires avec AAA positif, Opex moyen 2,771,354.40 £/an, AAA moyen 3,120,637.75 £/an, ratio des moyennes **88.8073 %**, médiane des ratios appariés **90.4192 %**.  Les ratios à 5 ans ne remplacent pas les mesures à 10 ans ; B uniquement si l'A officielle passe.

**25/10 — N75-C75-REFUND, A40×5 multimodal `nuit75_c75refund_porteA_40x5_20261025` :** verdict **`fail_primary`**, 40 paires, Δ `profit_year` moyen **-11,117.98 £/an**, médiane +0.00, V/D/E=13/12/15, Wilcoxon p=0.9578450322151184, IC95 bootstrap [-59,567.00; +33,388.90], garde valeur -0.536 %, bundle `244de36cc2fa95c2f418f73571c95461b3537ac5006b9941b8317da1096c0f17`. Seuil indicatif 4 % = 111924.424 £/an. B20×10 déclenchée seulement si A passe ; un résultat A40×5 n'autorise pas à déclarer un ratio de profit à dix ans.

**Audit indépendant A — `nuit75_c75refund_porteA_40x5_20261025` : VALIDE**, 80 duels, 160 compagnies, 40/40 paires, 0 erreur script, 0 partie invalide et 0 bilan invalide. SHA source `244de36cc2fa95c2f418f73571c95461b3537ac5006b9941b8317da1096c0f17` ; verdict économique `fail_primary`. reference (fin 1974) : 40 paires avec AAA positif, Opex moyen 2,798,110.60 £/an, AAA moyen 3,077,682.20 £/an, ratio des moyennes **90.9162 %**, médiane des ratios appariés **95.0761 %**. n75c75refund (fin 1974) : 40 paires avec AAA positif, Opex moyen 2,786,992.62 £/an, AAA moyen 3,046,133.80 £/an, ratio des moyennes **91.4928 %**, médiane des ratios appariés **93.3894 %**.  Les ratios à 5 ans ne remplacent pas les mesures à 10 ans ; B uniquement si l'A officielle passe.

**25/10 — N75 AIR quote, A40×5 multimodal `nuit75_truequote_porteA_40x5_20261025` :** verdict **`fail_primary`**, 40 paires, Δ `profit_year` moyen **+6,856.73 £/an**, médiane +78,255.50, V/D/E=26/14/0, Wilcoxon p=0.3974238318751304, IC95 bootstrap [-96,318.10; +102,589.88], garde valeur +0.252 %, bundle `4bd4c8e3f9a6023a513980874a624f345071fa26b710913927536a3ed484ee12`. Seuil indicatif 4 % = 112475.315 £/an. B20×10 déclenchée seulement si A passe ; un résultat A40×5 n'autorise pas à déclarer un ratio de profit à dix ans.

**Audit indépendant A — `nuit75_truequote_porteA_40x5_20261025` : VALIDE**, 80 duels, 160 compagnies, 40/40 paires, 0 erreur script, 0 partie invalide et 0 bilan invalide. Manifest SHA conforme, 80 fichiers moteur dont 0 non vides, 0 message fatal dans les logs. SHA source `4bd4c8e3f9a6023a513980874a624f345071fa26b710913927536a3ed484ee12` ; verdict économique `fail_primary`. Les fichiers moteur sont vides : absence d'erreur script établie par les bilans structurés, non par une trace textuelle. reference (fin 1974) : 40 paires avec AAA positif, Opex moyen 2,811,882.88 £/an, AAA moyen 3,034,751.83 £/an, ratio des moyennes **92.6561 %**, médiane des ratios appariés **92.0498 %**. n75airtruequote (fin 1974) : 40 paires avec AAA positif, Opex moyen 2,818,739.60 £/an, AAA moyen 3,047,167.58 £/an, ratio des moyennes **92.5036 %**, médiane des ratios appariés **89.1133 %**.  Les ratios à 5 ans ne remplacent pas les mesures à 10 ans ; B uniquement si l'A officielle passe.

**25/10 — N75 multi-cargo, A40×5 multimodal `nuit75_multicargo_porteA_40x5_20261025` :** verdict **`fail_primary`**, 40 paires, Δ `profit_year` moyen **+91,191.93 £/an**, médiane +93,397.00, V/D/E=24/16/0, Wilcoxon p=0.13868038851069286, IC95 bootstrap [-16,568.38; +197,955.75], garde valeur +2.646 %, bundle `ae6b948c9b14e394055e6a4befded72346697fdda5c7737a462f262200450fe2`. Seuil indicatif 4 % = 112369.41500000001 £/an. B20×10 déclenchée seulement si A passe ; un résultat A40×5 n'autorise pas à déclarer un ratio de profit à dix ans.

**25/10 — File nouvelle formule terminée :** les six portes A40×5 ont reçu un verdict ; les B20×10 ont été effectuées seulement pour les portes A officiellement `pass`. Aucun défaut/commit/push/merge.

**Audit indépendant A — `nuit75_multicargo_porteA_40x5_20261025` : VALIDE**, 80 duels, 160 compagnies, 40/40 paires, 0 erreur script, 0 partie invalide et 0 bilan invalide. Manifest SHA conforme, 80 fichiers moteur dont 0 non vides, 0 message fatal dans les logs. SHA source `ae6b948c9b14e394055e6a4befded72346697fdda5c7737a462f262200450fe2` ; verdict économique `fail_primary`. Les fichiers moteur sont vides : absence d'erreur script établie par les bilans structurés, non par une trace textuelle. reference (fin 1974) : 40 paires avec AAA positif, Opex moyen 2,809,235.38 £/an, AAA moyen 3,055,470.50 £/an, ratio des moyennes **91.9412 %**, médiane des ratios appariés **96.5730 %**. n75multicargo (fin 1974) : 40 paires avec AAA positif, Opex moyen 2,900,427.30 £/an, AAA moyen 2,998,522.45 £/an, ratio des moyennes **96.7286 %**, médiane des ratios appariés **99.6565 %**.  Les ratios à 5 ans ne remplacent pas les mesures à 10 ans ; B uniquement si l'A officielle passe.
