# IDLE-1 / PCAL-02 — audit nocturne du 25 octobre 2026

**Périmètre :** audit des mesures existantes et correction passive de télémétrie V309 dans le worktree indépendant `.worktrees/nuit75-idle1`, base `83e436cc`, sur la carte 256². L'analyse initiale des archives n'a requis aucune partie supplémentaire ; **un smoke moteur 1×1 a ensuite été exécuté par le prime**, détaillé ci-dessous. Il ne constitue ni une porte V102 ni une démonstration de progression vers 75 % d'AAAHogEx.

## Observations reproduites, et ce qu'elles prouvent

Source : `results/v309_bench_clean_20261021/results/v309_idle_expo_3x10_20261021_engine`, décodeur `sweeps/diag_v309_idle.py`. Campagne du 21/10, **3 graines (42, 7, 100) × 10 ans**, bras V309 instrumenté, 345 mois observés sur 360, donc aucune extrapolation des quinze mois absents.

| Années | Tours | Proxy `stable_unfunded` | Opcodes déjà exécutés par proxy | Reliquat au `Sleep` |
|---|---:|---:|---:|---:|
| 1970 | 3 810 | 3 145 | 118 040 174 | 22 861 865 |
| 1971 | 4 426 | 1 812 | 45 645 625 | 28 005 270 |
| 1972 | 2 989 | 1 598 | 43 336 035 | 17 384 880 |
| 1973 | 1 792 | 674 | 14 691 283 | 10 963 234 |
| 1974 | 2 044 | 180 | 9 748 259 | 11 838 928 |
| 1975–1979 | 12 050 | 0 | 0 | 74 555 825 |
| **Total** | **27 111** | **7 409 (27,33 %)** | **231 461 376** | **165 610 002** |

Le critère historique *strict* a classé **un seul tour** comme inutile (491 732 opcodes) : `best` est un portefeuille **déjà financé** (`OpexProjectSelectAffordable`). Quand il est vide, V309 lit `stats.nextProjectCapital`, prix du prochain devis rejeté au moment de l'élection, puis `stats.minCapital` en repli. Il ne possède ni l'identité de ce projet ni la preuve que son site est encore valide. Dans les anciens journaux, **7 587 tours** utilisent ce devis hors sélection, **2 263 tours** ont un coût inconnu, et **752 jours observés** présentent `caisse brute < devis` sans compter la réserve. Les **231,46 M** sont des opcodes consommés pendant un portefeuille stable : ce ne sont **pas** des opcodes prouvés récupérables, et il ne faut pas les additionner à `Sleep` comme deux gisements disponibles.

Le `Sleep(1)` laisse théoriquement **165,61 M opcodes / 30 années-parties**, soit **5,52 M par année-partie**. Le vieux dénominateur **430 opcodes/bloc** est une estimation V307 optimiste : V308 a mesuré **988 opcodes/bloc `short6`** en moyenne, **1 154–1 161 `full6`**, avant gestion des invalidations, cache et ordonnanceur. `165 610 002 / 988 ≈ 167 622` lectures théoriques `short6`, mais le budget est fragmenté entre tours et s'applique à trois cartes comportant seulement **3 × 1 024 blocs distincts** à 256². Ce ratio n'est ni une cartographie réellement achevée ni un gain net de travail.

Le banc V309 ON−OFF a donné **−204 448 £/an** de profit terminal moyen (0 victoire, 3 défaites), **−7,017 %** de valeur moyenne relative, avec IC95 bootstrap **[−413 788 ; −3 522] £/an**. Il s'agit de trois trajectoires sensibles aux opcodes de la sonde, **pas d'une estimation causale d'une nouvelle politique**. La sonde V309 demeure désactivée par défaut.

## Erreur de financement corrigée sous sonde OFF

Le sélecteur compare `OpexProjectFinanceCapital(project)` à `OpexAvailableCapital()`, soit `max(0, cash − OpexCashReserve())`, avec une réserve réelle bornée **[5 000 ; 25 000] £** par les frais courants des véhicules. Avant correction, V309 comparait `cash < cost`, ignorait donc la réserve et comptait des attentes nulles trop tôt. La nouvelle fonction `OpexV309IdleFundingBand` ne relit **aucune API NoAI** : elle compare la marge `caisse − devis publié` à ces bornes, ce qui préserve le coût OFF, tout en signalant l'incertitude du devis :

| Condition sur la marge bancaire | Classe passive | Interprétation si le devis est encore valide |
|---|---|---|
| Marge négative | `cash_short` | Manque de caisse certain |
| Marge de 0 à moins de 5 000 £ | `reserve_short` | Réserve certainement bloquante |
| Marge de 5 000 à moins de 25 000 £ | `reserve_uncertain` | Réserve réelle inconnue : on ne conclut pas |
| Marge d'au moins 25 000 £ | `sufficient` | Budget nominal couvert même avec réserve maximale |
| Devis absent / invalide | `unknown` | Aucune cause financière déductible |

Les sommes mensuelles exposent chaque classe (`*_loops`) et `stable_sufficient_loops` / `stable_sufficient_ops`, sous-ensemble de `stable_unfunded` où la marge couvre déjà le devis nominal. L'ancien `stable_unfunded` est **conservé, sans nouvel étiquetage comme travail inutile**. En phase de stabilité, `stable_sufficient` peut signaler un devis ancien plutôt qu'une opportunité ignorée. Les `wait_days` sont désormais **une borne inférieure** fondée sur la réserve minimale, codée `wait_basis=reserve_minimum_bound` ; l'attente est **inconnue (`-1`)** dans la bande de réserve incertaine. Le trimestre comptable et l'avenir du portefeuille n'étant pas observés, aucune erreur de prévision P50/P90 défendable n'est calculable pour l'instant.

Le décodeur expose les nouvelles classes par année sans transformer les anciennes lignes (où ces compteurs n'existent pas) en faux zéros. Le canal reste le bit V309 **67108864** du réglage `probes`, OFF au défaut. Les deux boucles existantes appellent la même fonction uniquement si le bit est présent ; le nouvel helper et les nouveaux champs ne s'exécutent donc jamais OFF. `V309_IDLE_STATE` reste transitoire, hors Save/Load, réinitialisé dans `Start` au redémarrage d'une partie ; aucun format de sauvegarde ni état de politique ne change.

## Consommateur AIR et limite PCAL-02

Il existe bien un **consommateur opérationnel de recherche de site AIR**, contrairement aux anciennes cartes C67 sans consommateur : `OpexAirFindSite` est appelé pendant `air_planning.nut` et utilise `AIR_SITE_CACHE` (ville/type), avec revalidation de l'emprise dans un `AITestMode` ; `OpexAirSiteStillBuildable` contrôle ensuite le projet avant la pose dans `task_air.nut` et `air_construction.nut`. Le mode de course C83 peut contourner le cache de ville/type ; V278 décale le choix des sites sur 1024² et est désactivé automatiquement au défaut sur 256². Réévaluer les sites pré-calculés en parallèle sans clé d'invalidation ni attribution au constructeur pourrait créer un second inventaire ou ralentir les projets immédiatement finançables.

Le profil PCAL-03 historique pour **1970, graine 42, 256²** porte `air.sites` à **2,01 M opcodes/an** (`air.plans` 13,95 M/an en span englobant), contre **9,65 M** pour `air.sites` sur une seule graine à **1024²**. Les spans parents et enfants **se chevauchent** ; leurs durées ne s'additionnent pas. Aucun essai n'isole le **coût récupérable** d'un futur cache PCAL-02 à 256², le taux de réemploi effectif, les sites consommés, l'avance de date de pose, ni le profit des lignes matures. Pour juger PCAL-02, la prochaine observation ciblée doit corréler `site calculé → cache hit → revalidation → plan choisi → BuildAirport → ligne mature` avec **clé ville/type/site, époque et raison d'invalidation**, et mesurer en parallèle la durée de recherche et les opcodes de l'appel réellement consommateur. La trace doit rester OFF hors diagnostic et suffisamment bornée pour ne pas déplacer l'ordonnancement.

La cible nocturne exige environ **+1 344 893 £/an** pour atteindre 75 % de profit d'AAAHogEx à la baseline indiquée. Aucun chiffre observé ici ne constitue un **plafond économique positif démontré** : même économiser 100 % du `Sleep` ou des appels `air.sites` ne garantit aucune ligne supplémentaire, encore moins +1,345 M£/an. Le plafond de gain économique identifiable à ce stade est **inconnu**, son plancher mesuré est **nul**. Une porte 20×10 ou 40×10 complète reste nécessaire après preuve de site effectivement consommé et déplacement de date de construction.

## Validation locale et smoke moteur proposé au prime

Changements non committés limités à `ai/OpexAI/probes.nut`, `sweeps/diag_v309_idle.py`, `sweeps/test_v309_idle.py` et **ce rapport**, sur worktree détaché. Tests nouveaux écrits avant correction : **2 rouges**, puis **10/10 V309 verts** ; contrats voisins V308/V307/V167/V147/V279/Save-Load **73 tests exécutés : 72 réussis, 1 ignoré** (archive moteur V308 absente) ; `diag_v309_idle.py --selftest` OK ; décodage des journaux V309 2021 compatible ; `git diff --check` OK. Ces tests contractuels ne mesurent pas les opcodes ON et ne constituent pas un smoke de Save/Load moteur. Le smoke moteur indépendant lancé ensuite par le prime est détaillé ci-dessous.

Le répertoire `ai/AAAHogEx-115` était absent du worktree neuf ; il a été **copié depuis le dépôt principal** (17 fichiers, 1 221 778 octets, ignorés par Git), pour permettre le smoke par le prime. **Smoke moteur exécuté par le prime** après gel du code, campagne `nuit75_idle1_reserve_smoke_1x1_20261025` (graine 42, 1970, carte 256², `--script-debug`, `OpexAI[probes=67109122]`, une partie complète, aucune erreur de script). Les artefacts figés sont `results/nuit75_idle1_reserve_smoke_1x1_20261025.json`, le manifeste et `results/nuit75_idle1_reserve_smoke_1x1_20261025_engine/reference_seed42_r0.log`. Bundle SHA256 `ecfb285a532438b82b3869ab95a8880a4a7243d1649b93e6103a889406bb8a20` ; manifeste SHA256 `fe9c1c8f9a11ed3d744d4d9c2951f0d7e8c105db29fa8a104c6ae5de5402b82c`.

Le décodeur des **11 flushs mensuels effectifs** donne, de janvier à novembre 1970 :

| Compteur | Total smoke |
|---|---:|
| Tours observés | **1 044** |
| Tours strictement inutiles | **0** |
| Devis absent / inconnu | 40 |
| Caisse strictement insuffisante | **671** |
| Réserve certainement bloquante | **60** |
| Bande de réserve incertaine | **127** |
| Budget nominal suffisant | **146** |
| Tours avec sélection vide, devis stable et révisions inchangées | **839** |
| Dont budget nominal suffisant malgré cet état | **12** |
| Opcodes exécutés durant ces 839 tours stables | **35 429 468** |
| Dont opcodes des 12 tours stables nominalement financés | **590 712** |
| Opcodes abandonnés au `Sleep` | **6 260 284** |
| Jours observés avec déficit de budget certain | **181** |

Les quatre classes financières partitionnent exactement les **1 004 tours** pour lesquels un devis existe ; les 40 restants restent inconnus. Les 12 tours avec budget nominal suffisant mais sélection vide stable ne représentent que **1,67 %** des opcodes du proxy stable ; ils signalent une **discordance potentielle entre un devis historique et le capital du jour**, sans certifier l'existence d'un candidat exécutable ni d'un emplacement AIR. Le reste des 839 tours stables reste principalement dans la **période de caisse faible**, sans preuve qu'une boucle complète aurait pu être sautée. Sept mois terminent avec une prévision `wait_days` absente : le profit trimestriel a pu rester inconnu, non positif ou la réserve incertaine. Aucune fenêtre de profit de ligne AIR accélérée n'est mesurée.

Pour une comparaison ON/OFF ultérieure, la commande **proposée uniquement**, depuis ce worktree, serait :

```powershell
python -X utf8 sweeps/run_c66_reference.py --campaign nuit75_idle1_smoke_1x1_20261025 --reference "OpexAI[probes=258]" --variant "OpexAI[probes=67109122]" --variant-policy-id nuit75_idle1 --decision-rule gain_short --primary-metric profit_year --min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 5 --map-size 8 --years 1 --seeds 42 --repeats 1 --script-debug --cpus 10 --memory 8g --max-workers 1 --network host
```

`258 = 2` (panneaux) `+ 256` (journal), `67109122 = 258 + 67108864` (V309). Les deux bras incluraient les mêmes autres probes, avec **le seul bit V309** supplémentaire sur le variant. Le smoke à bras unique a déjà validé les 11 nouveaux journaux et la compilation ; il n'établit **aucune neutralité opcodes/économique ON vs OFF**, ni gain de 75 %. **Aucun Docker lancé par ce worker** ; aucun banc/porte supplémentaire recommandé avant une jonction consommateur AIR prouvée.
