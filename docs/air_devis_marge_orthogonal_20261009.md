# AIR — séparer le devis et la marge (protocole pré-enregistré avant banc)

Le diagnostic V126 6×3 précédent a modifié **simultanément** le capital
devisé et la marge 12/30k£ ramenée à 2k£. Le nouveau réglage de diagnostic
`air_site_quote_keep_legacy_margin` (0 sur les quatre difficultés, OFF par
défaut) préserve entièrement la logique du devis tout en retenant la
marge historique lors du financement. Il n'a aucun effet si le devis est OFF.

## Protocole pré-enregistré

Arbre courant `master`, HEAD `cb23a17`, travail local dirty préservé ;
bundle et manifeste seront figés pour les deux bras de chaque campagne.
Profil Docker Desktop local : 10 CPU, 8 GiB, 10 workers maximum,
`openttd-lab`, une seule campagne à la fois. Contrôler les conteneurs avant
chaque lancement. Instrumentation identique aux deux bras :
`probe_air_finance_margin=1`, `--script-debug`. Aucun nouveau seuil numérique
de marge ; tous les autres réglages aux défauts courants.

Graines **42, 100, 999, 1234, 5678, 2026**, 3 ans, répétition 1,
OpexAI comparé à AAAHogEx dans le harnais apparié. 12 duels/campagne.
Le smoke préalable 1×1 graine 42 est **un contrôle de compilation**, pas
une sélection de graine favorable. Les campagnes sont deux diagnostics 6×3
pré-déclarés, sans élimination de graine ni modification a posteriori :

1. `air_quote_margin_legacy_6x3_20261009_r1` : **devis commun ON**.
   Référence `OpexAI[air_site_cost_quote=1,probe_air_finance_margin=1]`,
   variante `OpexAI[air_site_cost_quote=1,probe_air_finance_margin=1,air_site_quote_keep_legacy_margin=1]`.
   C'est **l'effet de restaurer la marge historique** à devis identique.
2. `air_quote_capital_only_6x3_20261009_r1` : **marge historique commune**.
   Référence `OpexAI[air_site_cost_quote=0,probe_air_finance_margin=1,air_site_quote_keep_legacy_margin=1]`,
   variante `OpexAI[air_site_cost_quote=1,probe_air_finance_margin=1,air_site_quote_keep_legacy_margin=1]`.
   Le réglage legacy_margin=1 est sans effet quand quote=0. C'est **l'effet
   du devis seul sur capital, prévision, choix et financement**.

Métrique primaire : profit terminal `profit_year` OpexAI variante−référence.
Règle demandée au harnais `gain_short` (4 %), garde company_value −5 %,
`required-seeds=40`, `required-years=3` : 6 graines => verdict
`diagnostic_only` et **jamais** une porte A/B V102. Observer les dépenses
`AIR_FINANCE_TRY`, succès/échecs N=0/1/2 sites, brèches de réserve et
premier revenu, résidus succès et coût opcode sur scans réellement
comparables. La somme de dépenses d'échec à construction n'est pas une
perte finale si ticket de rollback reporté/airport A conservé. Si une
campagne ne démarre pas (Docker occupé ou autre), la déclarer non exécutée.

La version du code doit rester identique entre les deux campagnes autant
que possible. Si une autre modification concurrente intervient, elle doit
être indiquée et le SHA de bundle de chaque campagne comparé ; **ne pas
additionner causalement des campagnes fondées sur des sources différentes**.

## Résultats

**Smoke 1×1** : `air_quote_margin_legacy_smoke_1x1_20261009_r1`, 2/2
parties complètes/saines, même bundle que les diagnostics ; sur seed42
première année, restaurer la marge produit −9 875 £/an, valeur −3,98 %.
Ce n'est pas une preuve économique.

**Deux campagnes complètes** sur le même bundle
`f745b31c7c7304f424470b92bee3e221596098e801c993e77a8dcb4cfb2e8de2` :

| Comparaison isolée (variante−référence) | Graine 42 | 100 | 999 | 1234 | 5678 | 2026 |
|---|---:|---:|---:|---:|---:|---:|
| Devis seul : quote ON + marge ancienne, moins quote OFF + marge ancienne | +72 267 | +48 041 | −426 489 | −141 305 | +388 654 | −928 394 |
| Marge seule : quote ON + marge ancienne, moins quote ON + marge résiduelle | +113 822 | +31 453 | −567 462 | −183 174 | −95 709 | −237 408 |

**Devis seul** : campagne `air_quote_capital_only_6x3_20261009_r1`,
12/12 duels complets ; profit Opex année terminale delta moyen
**−164 538 £/an**, médiane −46 632 £/an, V/D/E=3/3/0,
Wilcoxon p=0,5625, IC95 bootstrap moyenne [−519 265 ; +143 297] £/an,
ratio des moyennes de valeur compagnie **−8,88 %** ;
verdict du harnais **`diagnostic_only`**.

**Marge seule** : campagne `air_quote_margin_legacy_6x3_20261009_r1`,
12/12 duels complets ; profit Opex année terminale delta moyen
**−156 413 £/an**, médiane −139 442 £/an, V/D/E=2/4/0,
Wilcoxon p=0,21875, IC95 bootstrap moyenne [−343 897 ; +2 794] £/an,
ratio des moyennes de valeur compagnie **−11,37 %** ;
verdict du harnais **`diagnostic_only`**. Une baisse de marge accroît bien
le nombre de projets accessibles, mais sa sûreté n'est pas démontrée par
le nombre de constructions. Sur le devis ON, garder l'ancienne marge
construit 196 lignes AIR et enregistre 98 échecs (416 288 £ d'actual
comptabilisés) contre 210 lignes/70 échecs (370 199 £), 139 contre 84
refus de financement documentés. Trajectoires distinctes : ces écarts
ne donnent pas un effet *par projet*.

**Répétabilité :** le bras commun devis ON + marge ancienne donne
**exactement** les mêmes profits Opex et valeurs de compagnie pour chacune
des six graines entre les deux campagnes, bit à bit. Les deux bundles
et paramètres complets correspondent. Cette identité permet la
**décomposition triangulaire descriptive**, sans ajouter une nouvelle
expérience : devis+réduction de marge versus référence historique
`(devis seul) − (retour à marge ancienne)` = **−8 125 £/an** en moyenne,
V/D/E=4/2/0, ratio des moyennes de valeur **+2,81 %**. Ce n'est **pas**
une septième graine, une validation de marge ni un résultat V102 ;
la campagne 6×3 antérieure utilisait un **bundle différent** et son delta
de −70 729 £/an ne doit pas être fusionné avec ce triangle.

**Conclusion causale limitée** :

1. Le surcoût de capital que V126 ajoute au devis peut changer fortement
   la sélection et le profit, mais n'a **pas** apporté de gain robuste :
   résultat moyen négatif et IC95 traversant zéro. La perte du devis seul
   est portée en partie par la graine 2026 (−928 394 £/an), sans preuve
   d'un mécanisme unique.
2. Restaurer l'ancienne marge **en présence du devis** est également
   défavorable en moyenne ; toutefois le protocole n'a que six graines,
   et la baisse de marge expérimentale laisse des dépassements de coûts
   sur les succès et des échecs. Elle ne peut être adoptée en l'état.
3. Aucun réglage par défaut ne change. Il faut isoler les **pertes finales**
   après rollback/actifs conservés, et tracer la fraîcheur du devis au
   dernier garde de cash avant de chercher une nouvelle politique de
   financement. Aucune porte V102 A/B ; aucun commit ni push.

## Prolongement R19 — suivi des récupérations nettes (pré-enregistré)

Les 6×3 précédents contiennent uniquement les `actualCost` au retour de la
construction. Le constructeur peut créer un ticket R19 et sortir alors que
la vente des avions ou la démolition des aéroports s'effectue dans un scrap
ultérieur. Le constructeur laisse aussi l'aéroport A en place sur `BFAIL`
si la maintenance d'infrastructure est désactivée, ce qui est un actif
potentiellement réutilisable, pas une perte nette immédiate.

Instrumentation sous **`probe_air_finance_margin=1` uniquement** :
`AIR_RECOVERY_CREATE`, `AIR_RECOVERY_STEP` (delta signé via `AIAccounting`
propre à la passe différée), `AIR_RECOVERY_COMPLETE`. L'ID de ticket est
reporté dans `AIR_FINANCE_TRY recovery_id`; la ventilation
`orphan_kept=1` sépare explicitement les BFAIL avec actif A conservé.
Chaque état incomplet est **censuré**, aucune dépense comptabilisée d'un
ticket encore ouvert n'est appelée « perte finale ». Les ventes et
démolitions **immédiates** figurent déjà dans `actualCost` et ne sont pas
additionnées une seconde fois. Format ticket V1 conservé, champs facultatifs
`v126TraceId/v126RecoveryNet` recopiés par Save/Load ; aucune décision R19
ou marge de financement modifiée sous les réglages par défaut.

Protocole préenregistré avant exécution : smoke moteur mono-bras 1×1 seed42
pour compilation et événements du décodeur, puis si sain diagnostic mono-bras
6 graines (42,100,999,1234,5678,2026) × 3 ans,
`OpexAI[air_site_cost_quote=1,probe_air_finance_margin=1]`,
`--script-debug`, Docker local 10 CPU/8 GiB/10 workers max, une campagne à
la fois. Répétition 1. Sorties neuves
`air_rollback_net_smoke_seed42_20261009` et
`air_rollback_net_6x3_20261009_r1`, parser
`sweeps/analyse_air_recovery_net.py`. Objectif : comptabiliser par
tentative l'instantané, le coût signé différé et les actifs retenus ;
reporter les cas définitivement liquidés / sans ticket / en attente.
Pas un duel causal et surtout pas une porte V102. Aucun défaut modifié.

Limite pré-annoncée : un identifiant séquentiel fondé sur date+séquence
pourrait entrer en collision lors d'une sauvegarde et reprise dans le
**même jour de jeu** ; le décodeur rejette les doublons. Le coût des actifs
conservés reste sans valorisation finale tant que leur réemploi/vente
n'est pas suivi. Les sauvegardes R19 ordinaires et la reprise du suivi de
ticket sont à vérifier séparément si des tickets différés sont observés.

**Résultat diagnostic naturel** : 6/6 parties complètes/saines, bundle
`3adb03f255509368d2dcee90f4034b50d07d28df0ed8efb525e41b545a7aa29a`,
`results/air_rollback_net_6x3_20261009_r1.json` et rapport
`results/air_rollback_net_6x3_20261009_r1_analysis.json`. Les 70 événements
de `failed` du bras devis ON/surcoût sont **16 AFAIL**, **54 BFAIL** ;
aucun `ORDFAIL/START`, aucun `AIR_RECOVERY_CREATE` : **zéro ticket de
liquidation différée observé** sur ces six graines. Dépenses comptabilisées
au retour total 370 199 £, dont **61 échecs sans ticket pour 166 879 £**
(16 AFAIL = 58 380 £, 45 BFAIL sur site A réutilisé = 108 499 £) et
**9 BFAIL avec nouvel aéroport A conservé pour 203 320 £**. Ce capital
est immobilisé dans des installations pouvant être réutilisées : aucune
valeur de liquidation ou rentabilité finale n'est connue. On ne doit ni
compter les 370 199 £ comme perte définitive ni conclure que les 203 320 £
seront tous récupérés. L'absence de ticket naturel interdit de valider le
mesureur différé sur ce prélèvement, malgré sa compilation sur 1×1.

**Neutralité du nouveau logging sous sonde non démontrée** : comparée au
bras devis ON/marge résiduelle de la campagne factorielle (bundle antérieur),
la nouvelle campagne de télémétrie a les mêmes profits terminaux sur **5/6**
graines mais diffère sur la graine 5678 (2 433 239 → 2 450 506 £/an).
Ces journaux ne sont donc pas une nouvelle comparaison économique causale.
Les changements de l'instrumentation demeurent en revanche **inactifs au
défaut** `probe_air_finance_margin=0` ; toute qualification de politique
devra mesurer/contrôler séparément l'impact de la sonde.

**Contrôle dirigé pré-enregistré avant exécution** : un seul duel OpexAI vs
AAAHogEx, seed42, 2 ans, réglages
`OpexAI[air_site_cost_quote=1,probe_air_finance_margin=1,r19_fault_inject=1]`.
`r19_fault_inject=1` existe déjà et provoque volontairement l'échec du
**premier démarrage de ligne AIR**, afin d'exercer le chemin
`AIR_RECOVERY_CREATE → STEP/COMPLETE` ; il est 0 par défaut et ne sera pas
adopté. Docker local 10 CPU / 8 GiB, `--script-debug`, un seul lancement,
campagne `air_rollback_net_fault1_seed42_2y_20261009_r1`. Aucun résultat
de profit tiré de cette partie sabotée ne doit être réutilisé comme preuve
économique ; contrôle comptable et Squirrel seulement.

**Contrôle dirigé terminé et moteur sain** : 1/1 partie OpexAI/AAAHogEx
complète (2 ans), bundle identique au 6×3 R19
`3adb03f255509368d2dcee90f4034b50d07d28df0ed8efb525e41b545a7aa29a` ;
`results/air_rollback_net_fault1_seed42_2y_20261009_r1.json`, logs
`_engine/` et rapport `_analysis.json`. Le premier démarrage forcé
`START` (1970-01-16) a créé le ticket **`719543_1`** pour deux avions,
deux aéroports et 118 505 £ dépensées au retour initial.
Le nettoyage différé au jour jeu `719575` a vendu/retiré les biens :
`AIR_RECOVERY_STEP delta=−75 136 £`, 0 avion/0 aéroport restant,
`AIR_RECOVERY_COMPLETE`, donc **coût net final observé du chantier saboté
= 118 505 − 75 136 = 43 369 £**. Les quatre autres échecs du même
run étaient sans ticket ; coût comptabilisé au retour 21 337 £ ;
ensemble **64 706 £** de coût net comptabilisé à horizon pour cinq échecs.
Le diagnostic forcé démontre concrètement que considérer toute la dépense
`actual` comme **perte définitive** aurait surestimé de 75 136 £ ce
chantier précis ; il valide l'association ID, la vente signée et la clôture
de ticket. Il **ne prouve pas** la fréquence du mécanisme sans injection :
sur les 6 graines naturelles, aucun ticket différé n'a été observé.
Les actifs BFAIL conservés restent non évalués et aucune mesure de
réemploi ultérieur n'est fournie. Aucune qualification V102 ni adoption.
