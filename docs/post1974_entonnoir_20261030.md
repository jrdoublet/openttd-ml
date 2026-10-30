# POST-1974-ENTONNOIR — audit du défaut ESTIM31/V161 (30 octobre 2026)

## Pré-enregistrement et discipline

Objectif : reconstituer, sans modifier une décision de jeu, les pertes de
nouveaux projets en 1974–1979, distinctes des renforts de flotte. Le défaut
élu et les trois 20×10 qualifiés restent inchangés. La cohorte historique C63
du 26/10 n'est pas transposée au nouveau code.

1. Lire les trois archives `estim31ten_*20x10_20261030.jsonl` depuis leur
   **snapshot final** pour les panneaux annuels cumulatifs. Contrôler les
   20 graines et l'empreinte source de chaque politique, les deux compagnies,
   les dix checkpoints. Ne pas sommer les mêmes signes répétés d'année en
   année ; ne pas confondre `OR|`/`OB|`, nombre de projets bâtis et nombre de
   lignes neuves ; ne pas déduire un achat brut des PLYR nets.
2. Un seul diagnostic **1 graine × 10 ans**, graine **42** fixée avant toute
   lecture de traces ; code exact `origin/master` `10b5197d`, carte 256²,
   1970–1979, moteur OpenTTD 15.3, AAAHogEx-115. Deux bras : défaut publié
   `estim_unifie=31,eb14_progressive=3,probes=2` et même comportement avec
   `probes=131330` (C63 131072 + décisions 256 + panneaux 2), `--script-debug`.
   Aucun paramètre économique ni code Squirrel changé. Un Docker, 10 CPU,
   ≤8 Gio, 1 worker. **Mesure descriptive uniquement** : les sondes peuvent
   décaler les décisions et les résultats. Un 1×10 n'est ni Gate A/B ni
   preuve représentative des 20 graines. Le ledger C63 de 1979 peut ne
   s'imprimer qu'en 1980 : absence de la vidange ≠ zéro.
3. Parser et dédupliquer par graine/année et identité disponible (mode,
   source, destination, cargaison, variante de projet) ; isoler AIR neuf,
   RAIL neuf, flotte/V161 et V284. Distinguer génération, rang, refus,
   recherche de site, attente de calcul, A*, financement et succès physique.
   Les `OTHER` de panneaux doivent rester inconnus sans trace directe.
   Chiffrer les montants **réellement payés** seulement si l'événement ou
   l'observation les démontre ; ne pas assimiler un devis à une dépense.
4. **Critère de sortie économique strict :** aucun nouveau comportement ON
   sans **exemple traçable d'un projet simultanément rentable, finançable et
   physiquement constructible mais écarté**, suivi du motif de rejet exact.
   À défaut, clore uniquement la phase de mesure et maintenir la preuve
   d'exposition ouverte dans `docs/taches.md`.

## 1. Inventaire et contrôle de la cohorte

Le lecteur reproductible [`sweeps/post1974_archives.py`](../sweeps/post1974_archives.py)
produit [`post1974_archives_20261030.json`](post1974_archives_20261030.json)
à partir des **trois** archives figées `results/estim31_v161_{safe,coeff,motorcap}20261030/*/results/estim31ten_*20x10*.jsonl`.
Il vérifie dans chaque duel : 20 graines attendues, dix couples de checkpoints
au 1er décembre, 20 × 2 compagnies, unicité, cohérence SHA de la source
exécutée et concordance exacte des profits 1979 avec le classement qualifié.
**60 paires × 10 ans contrôlées** (les bras témoins et les variantes ne sont
pas mélangés) ; échec immédiat si source ou checkpoint divergent.

Les panneaux `OB|`/`OR|` contiennent des **signes conservés dans les
sauvegardes**, pas le journal intégral des tentatives. Leur clé
`(année, id de ligne cible, position de panneau)` n'est pas un identifiant
stable d'une tentative, leur nom est limité à 31 caractères et ne contient
ni couple OD complet ni fret/voyageurs. Même lorsque 1 311 `OR` et 1 311 `OB`
sont présents pour le gagnant, seulement **925 clés** sont appariables
univoquement ; **101 clés sont ambiguës**. N'en déduire ni un nombre de
projets uniques ni une exposition économique exhaustive. Le code de motif
`X` devient `OTHER` : la nature réelle de l'échec est inconnue.

## 2. Comptage annuel — configuration élue, 20 graines

Les valeurs ci-dessous sont **des occurrences observées dans les signes**,
pas des OD uniques. Les ratios sont calculés à chaque année comme
`100 × moyenne des profits Opex / moyenne des profits AAA` dans le même duel.
`C75` concerne exclusivement le contournement du plafond de capital en
**passe déjà productive**, pas tous les projets. Son bilan annuel est parfois
absent des signes (notamment **20/20 en 1979**) : `n.o.` signifie
**non observé et non zéro**. Pour 1978, 19/20 graines disposent du ledger
C75 ; les agrégats C75 sont donc volontairement censurés.

| Année | Chantiers `PB` | Tentatives RAIL `OR` | `OK` RAIL | `OTHER` RAIL | `ABND` RAIL | `SITEAB` RAIL | C75 éligibles / consommés | Caisse moyenne Opex | Profit / AAA |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1974 | 246 | 105 | 10 | 65 | 15 | 6 | 62 / 42 | 1,04 M£ | 103,24 % |
| 1975 | 108 | 149 | 17 | 89 | 16 | 15 | 58 / 39 | 2,13 M£ | 88,88 % |
| 1976 | 83 | 110 | 7 | 55 | 9 | 23 | 24 / 16 | 4,14 M£ | 80,80 % |
| 1977 | 37 | 110 | 9 | 61 | 10 | 14 | 10 / 8 | 7,26 M£ | 73,62 % |
| 1978 | 38 | 86 | 11 | 45 | 10 | 9 | n.o. (19/20) | 10,78 M£ | 70,47 % |
| 1979 | 20 | 72 | 4 | 35 | 11 | 9 | n.o. (0/20) | 14,74 M£ | 66,56 % |

RAIL 1979 : les **72 signes** se ventilent exactement en `OTHER` 35,
`ABND` 11, `SITEAB` 9, `SITEA` 1, `NOPA` 5, `TRKFAIL` 5,
`NOTRAIN` 2, `OK` 4. Le sens de `ABND` est un abandon signalé par
la tentative, **pas** la preuve d'un épuisement d'un budget A* particulier.
Les signes ne permettent pas de distinguer directement le retard du calcul
et le projet jamais présenté au constructeur.

Les stocks observés **entre checkpoints** étayent le ralentissement mais
ne le localisent pas à une étape du pipeline. De 1978 à 1979, sur
les 20 graines, variation nette : **+9 trains Opex / +93 trains AAA**,
**+2 aéroports Opex / +5 AAA**. Un train supplémentaire peut être un renfort
V284, une rame de ligne neuve ou un remplacement : **ce n'est pas un compte
de nouvelles lignes**. De même, une ligne AIR peut réutiliser deux hubs sans
aucun aéroport neuf, et `PB` compte également les chantiers flotte.

## 3. Contrôle croisé des deux autres 20×10

| Campagne | `PB` 1974 → 1979 | Signes RAIL 1974 → 1979 | `OTHER` RAIL 1979 | `OK` RAIL 1979 | `SITEAB` 1979 | C75 complet 1979 |
|---|---:|---:|---:|---:|---:|---|
| **V161 AIR2,00/RAIL0,75 — élu** | 246 → 20 | 105 → 72 | 35 | 4 | 9 | Non (0/20) |
| V161 AIR2,50/RAIL0,75 | 250 → 25 | 96 → 72 | 39 | 5 | 9 | Non (0/20) |
| V161 × C121 N1/N2 | 196 → 18 | 146 → 96 | 61 | 2 | 8 | Non (0/20) |

Le même profil d'attrition des chantiers et de tentatives RAIL infructueuses
se retrouve dans **trois environnements de décision distincts**. Il ne
constitue ni une comparaison causale de leurs changements, ni une preuve
qu'il faut augmenter artificiellement l'offre de candidats : les témoins
AAAHogEx de leurs duels diffèrent.

## 4. Source exacte : ce qu'on sait et ce qu'on ne sait pas

| Étape de l'entonnoir | Lieu du code existant | Observation 20×10 | Couverture |
|---|---|---|---|
| Génération AIR/RAIL, admissibilité, OD, fret/pax | `projects_generation.nut`, `candidates_v276.nut`, `projects_selection.nut` | Aucune liste exhaustive de couples rejetés | **Inconnue** |
| Classification et sélection du projet, arbitrage flotte | `projects_selection.nut`, `task_projects.nut` | `PB` compte les réalisations, `C75` une seule garde partielle | **Partielle** |
| Filtre classement / score marginal et disponibilité | `task_projects.nut`, `probes.nut` | Scores de projets individuels non journalisés sous `probes=2` | **Inconnue** |
| Recherche de sites et A* RAIL | `task_rail.nut`, `lines.nut` | `OR` : `SITEA/B/AB`, `ABND`, `NOPA`, `OTHER`, `OK` | **Signes retenus seulement** |
| Construction AIR neuve | `task_air.nut` | Stocks aéroports et projets globaux, aucun `AIR_BUILD` détaillé | **Inconnue** |
| Renfort AIR V161 et RAIL V284 | `task_projects.nut`, `task_v284.nut` | Variations de véhicules sans distinction fiable d'origine | **Inconnue** |
| Coûts réellement déboursés | `task_air.nut`, `task_rail.nut`, C63 opt-in | PLYR 1979 : constructions **nettes toutes modes** Opex 60,7 k£ vs AAA 213,0 k£, véhicules **neufs moins ventes** 167,3 k£ vs 719,5 k£ ; **aucun montant brut individualisé** | **Inconnue par mode/OD** |

La comptabilité PLYR est annuelle jusqu'au 1er décembre et nette : on
**ne peut pas** attribuer les 60,7 k£ aux aéroports, gares ou pistes,
ni les 167,3 k£ aux avions/trains achetés. Des projets proposés avec un
`quote` élevé ne prouvent pas que le chantier a été payé. L'instrumentation
`C63_INVEST` existante sépare `planned_ok`, `actual_ok`, `planned_fail`,
`actual_fail` et les modes, mais elle est **absente de ces 20×10**.

À la lecture du code, `OpexEstimDTraceActive` dans `probes.nut` ne trace
les comparaisons détaillées des offres **qu'en 1973–1975**. Les traces
`ESTIM_PASS`/`ESTIM_DECISION` ne sauraient donc expliquer 1976–1979 sans
nouvelle instrumentation explicitement bornée. Le code `OpexC75KPassBypass...`
ne comptabilise que les projets neufs **après** un premier chantier réussi
dans la même passe. Les absences de compte C75 ne sont donc jamais
une mesure d'absence de nouveaux projets.

## 5. Acquisition complémentaire et statut de preuve

La graine **42** a été pré-enregistrée pour l'unique 1×10 de sondes passives
(`probes=131330`), distinct du défaut public `probes=2`. **Premier lancement
refusé par le harnais** (garde d'argument manquante), deuxième interrompu
avant le jeu (répertoire `AAAHogEx-115` absent du worktree isolé), troisième
refusé avant le jeu par prévention d'écrasement de la préparation partielle.
Ces trois refus historiques sont des **échecs de préparation avant simulation**,
et non des résultats économiques. Le dossier incomplet
`results/post1974_entonnoir_seed42_1x10_20261030_bundle` ne doit pas être
interprété comme une campagne. Un Docker étranger était alors actif.
**Nouvelle tentative terminée avec succès** : voir §6, qui prévaut sur
l'ancien constat d'absence de logs ci-dessus.

**Verdict actualisé au §6 :** un entonnoir de recherche physique V233L et
une sous-réalisation des prévisions AIR sont documentés sur **une graine**.
La preuve d'un projet rentable, finançable, **physiquement constructible**
et injustement écarté reste absente. Aucune modification ON.

**Reproduction et contrôles :**

```powershell
python -m unittest sweeps.test_post1974_archives -v
python sweeps/post1974_archives.py
git diff --check
```

Ne pas utiliser la source historique `multi1_retard_1975_1979_resultats_20261026.md`
comme si elle avait les mêmes paramètres que le défaut élu.

## 6. Relance du 1×10 sur graine 42 — deux bras achevés

La relance, demandée expressément, est **réussie** sous le nom
`post1974_entonnoir_seed42_retry_1x10_20261030` ; la première préparation
interrompue n'a pas été réutilisée. Provenance :

- Source exécutée **`3998d9b1`**, campagne figée SHA-256
  `3590ff3bd7e0a2e3b9990ac2d1e1239a05065e423d0f12b7a15ee39163193abc`,
  même bundle pour les deux bras ; manifeste dans `results/`.
- Carte partagée 256², graine **42**, années **1970–1979**, AAAHogEx-115,
  `estim_unifie=31`, `eb14_progressive=3` ; témoin `probes=2`, observation
  `probes=131330` (C63/C50/C78 + décisions + panneaux), `--script-debug`.
  Un seul Docker, **1 worker**, CPU ≤10, mémoire ≤8 Gio.
- **2/2 parties complètes**, deux sociétés saines, checkpoint attendu
  `1979-12-01`, **zéro erreur Squirrel** repérée dans le log diagnostique.
  Sans sonde : profit annuel Opex **3 620 331 £** ; avec sonde :
  **3 507 554 £**, soit **−112 777 £**. Ce décalage rappelle que
  l'instrumentation **n'est pas neutre sur la trajectoire** : aucune
  conclusion économique par comparaison de ces deux bras. AAAHogEx fait
  **5 992 017 £/an** dans le duel témoin de la graine ; ce **n'est pas**
  le ratio décennal 20×10.

Les traces existantes ont été exploitées par
[`sweeps/post1974_probe.py`](../sweeps/post1974_probe.py) ;
leur [résumé dédupliqué et C63 par année](post1974_entonnoir_seed42_1x10_20261030.json)
permet de contrôler les comptages. Dans cette **unique graine instrumentée** :

| Année | Sélections RAIL / AIR journalisées | Tentatives RAIL (résultats) | Constructions AIR journalisées | Jours C63 `invalid` / `waiting_compute` / `unaffordable` | Dépenses C63 réussies (échecs précisés) |
|---|---|---|---:|---|---|
| 1974 | 1 / 0 | 0 | 0 | 305 / 15 / 20 | flotte 194 820 £ |
| 1975 | 0 / 0 | 1 `ABND` | 0 | 230 / 115 / 0 | flotte 188 668 £ ; AIR échec 960 £ |
| 1976 | 1 / 1 | 1 `ABND` | 1 | 215 / 128 / 0 | AIR 38 964 £ |
| 1977 | 3 / 1 | 3 `OK` | 1 | 134 / 195 / 0 | RAIL 411 212 £ ; AIR 38 964 £ |
| 1978 | 3 / 0 | 1 `NOPA`, 1 `NOPLAN2` | 0 | 186 / 124 / 0 | aucun chantier réussi recensé |
| 1979 | 1 / 1 | 1 `NOPLAN2` | 1 | **censuré** | **C63 non vidangé** |

Les 1978 **54 jours `absent`** s'ajoutent à 186 jours `invalid`
et 124 jours `waiting_compute` (364 jours classés au total) ;
`launched=0`. **Un état C63 exclusif par passe n'identifie pas un
nombre de projets uniques.** Le nombre de rejets `too_close_no_join`
se répète pour les **mêmes OD**, par exemple 13 événements RAIL en 1978 ;
ne pas les compter comme 13 projets distincts. Les compteurs `V284`
de 1979 sont `pick=7`, `done=4`, `fail=2`, `skip=1`, événements
du déclencheur de renfort **et non sept nouvelles lignes**.

### Deux projets fret longs particulièrement révélateurs

1. **GOOD 50791→7810** : offre sélectionnée le **5 novembre 1978**
   (profit prédit **69 478 £/an**, devis d'offre **98 426 £**).
   Son constructeur n'achève la tentative que le **26 octobre 1979** ;
   résultat `NOPLAN2`, `ok=0`, `quote=-1`, `actual=-1`
   (montant réellement payé **non mesuré**, et non zéro certifié).
   À la tentative, profit réestimé **79 663 £/an**. La cause dans
   `builder_rail.nut:4575–4579` est **l'échec du plan obligatoire
   de seconde voie pour V233L**, et non une simple pénurie de caisse ;
   `lines.nut:10–31` regroupe ce motif non codé dans `OTHER` sur
   les panneaux `OR`. La durée entre sélection et fin de tentative
   est d'environ **355 jours** — observation descriptive, pas mesure
   isolée d'opcodes A*.
2. **GOOD 50791→12090** : sélectionné le **10 novembre 1979**
   (profit prédit **67 822 £/an**, devis **98 650 £**) avec
   **plus de 11 M£ de capital disponible** relevé par `C78_SLOT`
   dans la fin d'année. La recherche V233L de seconde voie continue
   en décembre, après des obstacles précis : `BRIDGE_NATIVE`
   `error=260`, `area_not_clear=1`, présence d'un **tunnel RAIL
   concurrent** au débouché, puis `REJECT_SPLICE` et nouveau
   `search BEGIN` le **21 décembre**. **Aucun succès ni échec
   définitif n'est observé avant la fin du banc.**

Ces cas valident **une exposition de candidats économiquement positifs
et finançables dont la réalisation est bloquée/retardée** ; ils ne
valident **pas** l'existence d'un tracé physique rentable **constructible**
que la politique aurait arbitrairement éliminé. Essayer le
monovoie, élargir les options de doublement ou desserrer les filtres V233L
exigerait un **nouveau levier opt-in** et une validation indépendante,
pas un changement automatique du défaut.

### Cohortes AIR matures : seconde alerte distincte

Dans le ledger **1978** (vidangé le 29 janvier 1979), pour les lignes
âgées d'au moins deux ans, **38 lignes AIR** totalisent
`pred_p=8 507 573 £` contre `real_p=2 527 205 £`
(**29,7 %** du profit prédit) ; les **25 lignes RAIL** totalisent
`pred_p=445 733 £`, `real_p=602 789 £`. Ce sont les *sommes de
prévisions enregistrées à la construction* et des *profits de lignes
observés lors du rapport annuel*, dans le bras **sondé**, pas des
profits incrémentaux contrefactuels. Elles orientent la tâche
**AIR-PRODUCTIVITÉ**, sans justifier une correction immédiate de
`estim_unifie`.

### Frontières de preuve et décision

La dernière ligne `C63_INVEST phase=opp` est la vidange de
**1978** ; celle de **1979** est attendue en **1980** et le banc
s'arrête fin 1979. Les **projets non sélectionnés** n'ont pas de
liste OD complète après 1975 : `OpexEstimDTraceActive` est borné
aux années **1973–1975**. Le détail des lignes V233L confirme un
**blocage de seconde voie** sur cette graine mais n'établit pas
le mécanisme dominant sur les 20 graines. **Critère de clôture de
POST-1974-ENTONNOIR non satisfait** : aucun projet économiquement bon
et **physiquement réalisable** n'a été démontré injustement rejeté.

**Décision : maintenir le défaut élu inchangé.** Conserver la tâche
ouverte sur la validation physique V233L (deuxième voie obligatoire,
recherche longue, collisions concurrentes), la comparaison avec
un éventuel projet monovoie constructible et la reproduction sur
plusieurs graines **avant** tout levier. Ne pas relancer la même
campagne sous couvert de la relance déjà réussie.
