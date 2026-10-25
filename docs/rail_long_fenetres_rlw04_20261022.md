# RAIL-LONG-FENETRES — RLW-04 (22/10/2026)

## Etat

**Correctif shadow recontrole dans OpenTTD sur 256² et 1024² : 0 depassement
mesure sur les deux cartes, passe 256² COMPLETE (9/9 le 30/07/1972),
mais passe 1024² NON complete (3/10 apres six ans).** Les premiers
essais ci-dessous documentent l'ancien code (depassements et resets). Les
recontroles du 22/10 en fin de rapport les remplacent pour l'admission sous
budget, sans prouver le cout absolu de journalisation ni la couverture de la
grande carte. Le dernier recontrole priorise et son budget complet sont detailles
en fin de rapport. RLW-04 reste ouverte/non qualifiee sur 1024².
Aucun changement de defaut,
candidat promu, construction ni porte economique. RLW-03 reste OFF.

Worktree : `.worktrees/rlw04` **a l'interieur** du depot, HEAD initial
`41031a7f24f8a60e8b671c954baeabe14088a145` en detached HEAD. Les
modifications non commitees `rail_long_*` et leurs sites d'integration ont
ete copiees depuis le depot principal a la creation. La reference adverse
`ai/AAAHogEx-115` etait bien presente dans le depot principal mais ignoree
par Git : ses **17 fichiers** ont ete copies dans le worktree avec empreintes
SHA-256 identiques. Le volume Docker pointe bien `/work` sur ce worktree,
incluant OpexAI et AAAHogEx. Les fichiers `air_*` et le depot principal n'ont
pas ete modifies ici.

## Livraison technique et garde OFF

`ai/OpexAI/rail_long_window_enumerator.nut` ajoute un parcours des paires
RAIL voyageurs et fret par cargo dans la **seule bande 224..288 Manhattan**.
Le curseur porte famille, cargo, source et destination ; un tour distribue le
travail entre les cargos pour ne pas laisser une source dense monopoliser la
recherche. Seul un echantillon de **32 paires par famille** est conserve dans
`_rlw04State.pool` hors `_projects`, hors `candidateGroups`, hors
`_ranked` et hors V276. Les paires 201..223 ne sont **pas** admises dans le
stock : elles sont seulement comptees en `outside201_223` pour preparer une
ablation separee, preservee pour RLW-05.

La source de configuration `RLW04_SHADOW <- false` dans `globals_post.nut`
reste OFF. Elle est independante de `RLW03_SHADOW <- false` ; aucun nouveau
`AddSetting` OpenTTD n'est introduit. Les deux boucles (`main.nut` et
`probes.nut`) appellent la tranche uniquement si RLW04 est explicitement
active. Le passage s'arrete pendant les deux premieres annees et est place
apres les continuations de catalogue et de recherche rail. Aucun appel de
`OpexMakeCandidate`, `OpexV276Publish`, `OpexBuildCandidates`, A*,
transaction ou depot n'existe dans cet enumerateur.

Budget annonce : au plus 24 comparaisons par invocation, cible **1 800
opcodes de calcul par tranche**, garde d'entree a **5 500 opcodes restants**,
sortie au changement de tick et compteurs `overrun`, `max_ops`, `totalOps`.
Le tri ne concerne que les IDs des cargos, jamais les paires : aucun
`AIList.Sort` ni accumulation des paires en `AIList`. Si la liste des puits
depasse 128, le parcours regarde au plus **128 destinations par source**,
avec un pas deterministe et un decalage selon la source. Cet echantillonnage
peut manquer une liaison attractive : **le stock n'est pas un vrai TOP**, ni
une preuve d'opportunite. Les frais atomiques d'initialisation et de log sont
hors compteur de tranche ; le respect du plafond absolu ne peut etre affirme
sans mesure OpenTTD sur 256² et 1024².

Les logs `RLW04_ENUM` (phase, volume, distance, stock, opcodes, ticks, budget,
depassement) et `RLW04_UNIT` (famille, cargo, sources, puits, pas, couverture)
se decodent par `sweeps/analyze_rlw04.py` :

```powershell
python -X utf8 sweeps/analyze_rlw04.py results/nom_campagne_engine --format markdown
python -X utf8 sweeps/analyze_rlw04.py results/nom_controle_engine --expect-off
```

## Audit des chemins d'origine

| Chemin | Risque identifie | Garde RLW-04 |
|---|---|---|
| `OpexRailPaxPairInBand` | `railMax` borne le RAIL pax, et la bande `PAX_BAND_AIR_RAIL` peut eliminer les longues paires | Controle de distance local **224..288**, sans modifier `catalog.bounds.railMax` ni les seuils AIR |
| `OpexMakeCandidate` | `ratio_floor`, sites, statut de ligne et rentabilite peuvent rejeter une paire avant A* | Aucun appel en RLW-04 ; les paires observees **ne valent pas** des projets admissibles |
| V269 / V217 | Borne fret tardive 250/400 liee a l'annee, au cargo et a la regeneration | Aucun changement de V269, aucune promesse d'admission ou de construction |
| V276 | `V276_EVAL_CAP=500`, `TOP_K=20`, liste de paires et `AIList.Sort` global avant evaluation | Etat, budget et pool separes, sans publication ni classement du portefeuille |
| Fenetre 201..223 | Lignes observees 205/209/220/222 absentes de 224..288 | Occurrences comptees separement, jamais melees a la bande active |

## Validation effective

Dans `.worktrees/rlw04`, les cinq suites ciblees ci-dessous passent :

```powershell
$env:PYTHONPATH=(Get-Location).Path
uvx --from 'pytest==8.4.2' pytest -q sweeps/test_analyze_rlw04.py sweeps/test_rail_long_window_probe.py sweeps/test_rail_long_window_policy.py sweeps/test_rail_long_early1.py sweeps/test_v269_rail_late_relax.py
```

**32 tests verts**, dont une regression nouvelle du depouillement apres
`stale_restart`. `git diff --check` passe. Les fixtures synthetiques restent
utiles pour les gardes : 256² contient 10 paires 224..288 et 11 paires
201..223 ; 1024², 240 et 51. Il ne s'agit pas de mesures moteur.

### OpenTTD reel, 22 octobre 2026

Hote Docker Desktop `desktop-linux`, image `openttd-lab:latest`
`sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
Lanceur hote `sweeps/run_c66_reference.py`, montage du worktree sur `/work`,
cache `openttd-lab-home`, limite **2 CPU, 4 Go RAM, 2 workers** pour partager
les ressources avec AIR-ROI-RENFORT-1. Graine 42, un seul repeat, debut 1970,
3 ans pour atteindre le declenchement 1972, `--probes 6` dans les deux bras,
`--decision-rule signs20 --min-useful-primary-delta 0`, valeur garde 5 %.

Les deux bras `OpexAI[v269_rail_long_max=0]` et `OpexAI[v269_rail_long_max=200]`
ont tous deux la valeur effective **0** (normalisation sous 250). Cette
comparaison controle l'identite **intra-bundle** ; elle ne compare pas ON contre
OFF dans une meme paire : `RLW04_SHADOW` est un flag source, et les experiences
ON/OFF ont necessairement des bundles differents. Les sondes `probes=6`
journalisent les decisions et ajoutent elles-memes des opcodes ; toute
comparaison economique ON/OFF inter-bundles reste descriptive.

| Bundle / campagne | Carte | RLW04 | Parties | Traces RLW04 / bras | Tranches / bras | Depassements / bras | Pic opcodes / bras | Reinitialisations / bras | Passe complete |
|---|---:|---|---:|---:|---:|---:|---:|---:|---|
| `rlw04_off_smoke256_20261022` | 256², 1 an | OFF | 2/2 saines | 0 | — | — | — | — | sans objet |
| `rlw04_off_engine256_20261022` | 256², 3 ans | OFF | 2/2 saines | 0 | — | — | — | — | sans objet |
| `rlw04_on_engine256_20261022` | 256², 3 ans | ON | 2/2 saines | oui | **321** | **321** | **2 026** | 1 | non |
| `rlw04_on_engine1024_20261022` | 1024², 3 ans | ON | 2/2 saines | oui | **29** | **29** | **2 011** | 18 | non |
| `rlw04_off_engine1024_20261022` | 1024², 3 ans | OFF | 2/2 saines | 0 | — | — | — | — | sans objet |

Empreintes de bundles : OFF `be1502c11118a9609aa9c931a47dc7328426ca8cc44777cb7c01d5fb7e1fcc08`,
ON `6bb68341266df88405d30d93d23194c8ae8f913bb3a6e5bcaef48c7a4ab18598`.
Les deux bras de chaque campagne ont la meme trajectoire economique finale,
`delta profit_year=0`, `ratio company_value=1`, verdict harnais
`diagnostic_only` attendu pour une seule graine. Aucun resultat economique
d'adoption n'est invoque.

**Sur 256²**, cumul des cycles RLW04 : 1 343 paires examinees, 202 dans
224..288 et 123 dans 201..223 ; 8 unites source/cargo closes, sans fin de
passe generale. Le stock atteint 32 paires pax et 32 fret. **Sur 1024²**,
les 18 evenements `stale_restart` reinitialisent le curseur apres des
rafraichissements du catalogue : au moins 272 paires testees, 11 dans
224..288, 1 dans 201..223 et **0 unite close**. La couverture 1024² n'est
pas demontree.

`sweeps/analyze_rlw04.py` a ete corrige pour sommer par **cycle** les champs
cumulatifs (`slices`, `scanned`, `overrun`...), en prenant le maximum des pics
plutot que le dernier `stale_restart` a zero. Un cycle inacheve sans checkpoint
final demeure sous-observe. Pour regenerer ces preuves :

```powershell
python -X utf8 sweeps/analyze_rlw04.py results/rlw04_on_engine256_20261022_engine --format markdown
python -X utf8 sweeps/analyze_rlw04.py results/rlw04_on_engine1024_20261022_engine --format markdown
python -X utf8 sweeps/analyze_rlw04.py results/rlw04_off_engine256_20261022_engine --expect-off
python -X utf8 sweeps/analyze_rlw04.py results/rlw04_off_engine1024_20261022_engine --expect-off
```

### Verdict initial avant correctifs (historique)

Le plafond `RLW04_OPS_BUDGET=1800` est franchi sur **toutes les tranches
journalisees des deux tailles**. `max_ops` exclut les couts atomiques
d'initialisation et de journalisation : le cout complet ne peut etre plus
faible. La verification en tete de boucle de `OpexOpsMeasureEnd(mark) < 1800`
ne reserve pas le cout de l'iteration suivante ni celui de sortie. Les resets
frequents sur 1024² empechent egalement de prouver que chaque famille et
cargo peut etre parcouru a terme.

**Conclusion : RLW-04 shadow expose, mais garde budget et progres non
qualifies ; aucun candidat comportemental n'en decoule.** Pour poursuivre,
borner la tranche en tenant compte du cout de l'iteration complete, puis
traiter les refreshs de catalogue et refaire ces controles moteur. Les portes
A 40×3 / B 20×10 n'ont pas lieu d'etre lancees sur cet enumerateur. Les
flags `RLW03_SHADOW` et `RLW04_SHADOW` sont laisses **false** et aucun defaut
de politique n'est change.

## Correction locale du 22/10 — validation moteur en attente

La correction dans `ai/OpexAI/rail_long_window_enumerator.nut` effectue
l'admission **avant** chaque pas : le cout anticipe est
`max(650, 2 * maxWorkOps + 160)`, auquel s'ajoute une reserve de
sortie de 300 opcodes sous le budget de 1 800. Le reliquat du tick
reste controle. Le cout des pas (`max_work_ops`), de la sortie
(`max_tail_ops`), de l'initialisation (`init_ops`) et des logs de fin
d'unite (`max_log_ops`) est mesure par etape. Aucun journal n'est
ecrit au milieu de la boucle de comparaisons.

Un **snapshot des collections initiales** reste fixe durant la passe :
la progression source/destination et la cle `cargo + sourceKey` (ID API)
survivent aux republications. Les sources disparues sont ignorees
individuellement avec les gardes `AITown.IsValidTown` et
`AIIndustry.IsValidIndustry`; chaque refresh incremente `refreshes`
sans effacer les curseurs ni les comptes. Les nouveaux elements ajoutes
au catalogue apres ce snapshot attendent une passe ulterieure :
RLW-04 ne fournit pas encore de suivi continu des nouveaux entrants.
La trace `RLW04_ENUM` est emise tous les 16 pas de tranche et a `done`,
avec `refreshes` et `pending`. Le decodeur distingue les anciens
`stale_restart` et les refreshs sans remise a zero, et signale les
reculs observables par checkpoint.

L'admission reste **une estimation prudente**, corrigee par les couts
observes. Sans moteur, elle n'est pas une preuve de plafond absolu :
initialisation et journalisation sont mesurees distinctement de
`max_ops`. L'invalidation du stock shadow lors de changements
physiques et la fin effective d'une grande passe doivent aussi etre
verifiees avant exploitation dans RLW-05.

Commande de verification depuis `.worktrees/rlw04` :

```powershell
$env:PYTHONPATH=(Get-Location).Path
uvx --from 'pytest==8.4.2' pytest -q sweeps/test_analyze_rlw04.py sweeps/test_rail_long_window_probe.py sweeps/test_rail_long_window_policy.py sweeps/test_rail_long_early1.py sweeps/test_v269_rail_late_relax.py
```

**38 tests verts**, `git diff --check` OK. Les anciennes traces
redecodées confirment 256² : 321/321 depassements (pic 2 026) ;
1024² : 29/29 (pic 2 011), 18 resets. Ce sont des mesures de
l'ancienne implementation.

Tentative `rlw04_recheck_on256_20261022` : lanceur hote
`run_c66_reference.py`, `desktop-linux`, image
`sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`,
2 CPU, 4 Go, 2 workers, seed 42 × 3 ans, 256², `probes=6`.
Le processus a atteint `docker run`, mais **aucun conteneur dans
`docker ps`, ni bundle ni log moteur** : la CLI du seul lancement
RLW-04 a ete arretee (retour -1) apres constat du blocage. Aucun
nouveau resultat moteur ON/OFF 256² ou 1024² n'est disponible.
Le drapeau `RLW04_SHADOW <- false` a ete restaure dans le worktree.

**Verdict : correction locale et tests statiques termines, qualification
moteur toujours bloquee.** Reprendre par un controle Docker unique,
puis ON/OFF 256² et 1024², verifier `max_ops`, `overrun`, les
pics d'etape, `refreshes`, `pending`, `RLW04_UNIT` et `done`.
En l'absence d'une variante candidate constructible, aucune porte
economique A/B n'est ouverte.

## Recontroles moteur apres redemarrage de Docker Desktop (22/10)

Hote `desktop-linux`, image `openttd-lab:latest` de SHA
`sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
Quatre campagnes du lanceur hote `sweeps/run_c66_reference.py`, dans **ce seul
worktree** : graine 42, depart 1970, horizon 3 ans, 1 repetition,
`--map-size 8` (256²) ou `10` (1024²), `--probes 6`, `--decision-rule signs20`,
`--min-useful-primary-delta 0`, 2 CPU, 4 Go, 2 workers. Une campagne RLW-04
a la fois, avec la campagne AIR deja active (conteneur distinct de 5 CPU).
Les deux bras de chaque campagne utilisent `v269_rail_long_max=0/200`,
normalises tous deux a 0 : ce sont des controles d'identite *dans le meme
bundle*, pas des portes economiques. `RLW04_SHADOW` est un flag SOURCE :
les bundles ON/OFF ne different que par sa ligne dans `globals_post.nut`
(`git diff --no-index` sur leurs repertoires `ai/OpexAI`). Le flag du worktree
a ete restaure a `false` a la fin de chaque execution ON.

| Campagne `rlw04_recheck_fix_*_20261022` | Carte | Source | Duels | Tranches / bras | Overrun / bras | Pic `max_ops` | `max_work_ops` | Init | Log unite | Refresh / resets / reculs | Unites closes / total | Paires / 224..288 / 201..223 |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|
| `on256` | 256² | ON | 2/2 | 368 | **0** | **1 234** | 236 | 1 104 | 174 | 1 / 0 / 0 | **7/9** | 742 / 114 / 76 |
| `on1024` | 1024² | ON | 2/2 | 48 | **0** | **1 230** | 234 | 1 262 | 0 | 18 / 0 / 0 | **0/10** | 145 / 9 / 3 |
| `off256` | 256² | OFF | 2/2 | 0 | s.o. | s.o. | s.o. | s.o. | s.o. | s.o. | s.o. | 0 evenement RLW04 |
| `off1024` | 1024² | OFF | 2/2 | 0 | s.o. | s.o. | s.o. | s.o. | s.o. | s.o. | s.o. | 0 evenement RLW04 |

Les valeurs de la ligne ON sont **identiques dans les deux bras du meme
bundle**. `max_tail_ops=22` sur les deux cartes. Sur 256², les sept
`RLW04_UNIT` clos sont des cargos fret (LVST, GRAI, WOOD, STEL, OIL_,
COAL et IORE) ; deux unites sont encore en cours. Sur 1024²,
les **18 refresh** de catalogue conservent les cumuls : aucun
`stale_restart`, aucun recul observe sur les checkpoints et **aucun**
`RLW04_UNIT` clos. Les 48 tranches n'ont pas permis de couvrir les dix
unites. Cela montre une progression sans reset observe, **pas** une preuve
de parcours exhaustif de chaque source ou cargo ni une fin de passe.

La borne mesuree du **calcul par tranche** est sous le budget de 1 800,
sans `overrun` sur 368 + 48 tranches par bras. L'initialisation a un pic
mesure separement (1 104 / 1 262) ; les logs d'unite (174 / 0) et les
messages `RLW04_ENUM` sont hors `max_ops`. Le cout complet d'un appel,
notamment celui des `RLW04_ENUM`, **n'est donc pas certifie sous 1 800**.
Les compteurs sont cumulatifs entre checkpoints toutes les 16 tranches ;
les totaux des tranches non journalisees en fin de partie peuvent etre
sous-estimes. Le code garde les sources par ID et ne remet pas son etat a
zero aux refresh, mais les positions de chaque curseur individuel ne sont
pas toutes journalisees pendant une passe inachevee.

OFF : `sweeps/analyze_rlw04.py --expect-off` reussit sur les quatre logs
de reference et variante OFF ; `RLW04_SHADOW=false` empeche l'appel
`_rlw04Step` dans `main.nut` et `probes.nut`. Pour chacun des quatre
controles, `profit_year` Opex variante moins reference = **0** et ratio de
valeur = **1**, avec statut `complete/complete` des deux duels. Ce constat
etablit l'absence d'effet economique visible OFF sur cette graine et
l'absence de travail RLW04 ; il ne demontre pas une egalite des **opcodes
de garde par tick** ni l'identite bit-a-bit de tous les indicateurs (par
exemple `median_station_rating` differe de 2 sur l'OFF 256²). Les probes
`6` ne collectent pas `probe_loop_ops` (groupe 8), et ajouter un profilage
changerait lui-meme les opcodes et potentiellement la trajectoire.

Traces reproductibles : `results/rlw04_recheck_fix_{on256,on1024,off256,off1024}_20261022.json`,
leurs `.manifest.json`, `_bundle` et `_engine`. Pour regenerer les releves :

```powershell
python -X utf8 sweeps/analyze_rlw04.py results/rlw04_recheck_fix_on256_20261022_engine --format markdown
python -X utf8 sweeps/analyze_rlw04.py results/rlw04_recheck_fix_on1024_20261022_engine --format markdown
python -X utf8 sweeps/analyze_rlw04.py results/rlw04_recheck_fix_off256_20261022_engine --expect-off
python -X utf8 sweeps/analyze_rlw04.py results/rlw04_recheck_fix_off1024_20261022_engine --expect-off
```

Bundles ON `0a1b7d2d984af3d10b287c0da57420cfc5ad3e5512b537fd83140d0d2f2df23f`,
OFF `5ce115a5d2b61fef27e05741bfed798c01d22c4f3d595102304613cb42e3f490`.
Les **38 tests** cibles sont verts apres recontrole.

**Verdict courant : correction du budget de tranche confirmee sur les deux
tailles, rafraichissements sans regression observee, mais couverture et cout
absolu non qualifies.** Le plafond actuel laisse une avance effective trop
faible sur 1024² a trois ans (145 paires et 0/10 unites terminees) pour
valider le parcours integral. Avant RLW-05, mesurer et corriger la cadence
d'avancement par source/cargo et le cout des logs `RLW04_ENUM`, puis
demonstrer la fin des passes dans un protocole borne et predefini.
Il n'existe encore aucun candidat RAIL long evalue, finance et
constructible : **pas de portes A/B**. Flags RLW03/RLW04 OFF ; aucun
commit, push ni intervention dans l'arbre principal.

## Mesure de cadence, ordonnanceur priorise et recontroles finaux (22/10)

### Cause mesuree et changement local

Sur le premier recontrole corrigé **1024², seed 42, 1970-1972**, les
48 tranches et 145 paires du journal couvrent janvier-decembre 1972 :
**4 tranches/mois, 3,02 paires/tranche, 0/10 unite close**. Les couts de
comparaison atteignaient seulement 234 opcodes par pas, 1 230 opcodes au
pic de la tranche ; les 18 rafraichissements n'annulaient plus les curseurs.
La garde initiale de **5 500 opcodes disponibles** avant le travail de
1 800 etait le frein principal a l'admission en fin de boucle IA, avec
une tranche unique par appel. Les paires examinees par tranche sont peu
nombreuses a cause de l'admission prudente du pas suivant :
`max(650, 2*maxWorkOps + 160)` plus 300 opcodes de sortie.

Le correctif reste dans **`ai/OpexAI/rail_long_window_enumerator.nut`** :

- chaque appel peut executer jusqu'a **5 tranches independantes**, avec
  une nouvelle mesure et le **meme budget fixe de 1 800** pour chacune ;
  la reserve d'entree devient 2 150, avec garde du tick et admission du
  prochain pas plus sortie avant tout travail ;
- trois passages environ sur quatre favorisent, quand un candidat est
  disponible, l'unite source/cargo de plus faible travail restant estime
  (`(sourceCount-a) * min(destCount,128)`) ; les autres passages utilisent
  le curseur tournant, pour continuer les grands cargos ;
- le snapshot source/puits demeure conserve aux rafraichissements ;
  `refreshes`, `total_refresh_ops`, `max_refresh_ops` exposent leur cout ;
- journaux d'unite au plus **un par tranche**, journal ENUM tous les
  seize pas et en fin, dont le cout entre maintenant dans `max_full_ops`
  et `overrun`. Les totaux `total_full_ops`, `total_work_ops`,
  `total_unit_log_ops`, `total_enum_log_ops`, `init_ops` separent le temps
  des comparaisons, de la journalisation et de l'initialisation ;
- un **curseur source/cargo different est echantillonne a chaque log ENUM**
  (index, famille, cargo, source courante, nombre de sources, visites et
  fin d'unite). Ces echantillons sont repris dans `cursor_samples` du
  decodeur ; une fin de passe attend toujours les dix unites.

Le cout de selection de la priorite et celui des mesures restent inclus
dans le budget. Ce correctif n'implemente **ni tri spatial des paires,
ni nouvelle fenetre, ni publication V276, ni evaluation ROI ni construction**.
Les quelques unites terminees par priorite ne prouvent pas que le vivier
est un TOP ni que toutes les nouvelles sources du catalogue seront revues.

### Recontroles du dernier code : ON et OFF

Lanceur hote `sweeps/run_c66_reference.py`, Docker Desktop `desktop-linux`,
image `openttd-lab:latest` SHA
`sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`,
2 CPU / 4 Go / **2 workers maximum**, une seule campagne a la fois,
graine 42, depart 1970, 1 repetition, `--probes 6`, carte 256² ou 1024².
Chaque campagne comprend deux duels (reference V269=0, variante V269=200,
toutes deux normalisees a 0) et est `complete/complete`.
Les campagnes ON et OFF emploient des bundles figes distincts car le
drapeau **source** `RLW04_SHADOW` doit etre modifie pour les executer ;
le drapeau du worktree final a ete restaure a **false**.

| Campagne `rlw04_priority4_*_20261022` | Carte | Horizon | Tranches ON / bras | Paires ON / bras | Unites closes ON / total | Pic complet ON / bras | Depassements ON | Refresh | Etat |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `on256` | 256² | 3 ans | **651** | **1 624** | **9/9**, `done` le **30/07/1972** | 1 622 | **0** | 1 | passe close |
| `on1024` | 1024² | 3 ans | **272** | **763** | **1/10** | 1 479 | **0** | 20 | passe ouverte |
| `on1024_6y` (reference) | 1024² | 6 ans | **3 568** | **10 414** | **3/10** | 1 550 | **0** | 74 | passe ouverte |
| `on1024_6y` (variante) | 1024² | 6 ans | **5 056** | **14 905** | **3/10** | 1 559 | **0** | 77 | passe ouverte |
| `off256` | 256² | 3 ans | 0 | 0 | s.o. | s.o. | s.o. | s.o. | deux duels sains, **0 trace** |
| `off1024` | 1024² | 3 ans | 0 | 0 | s.o. | s.o. | s.o. | s.o. | deux duels sains, **0 trace** |

Sur 256², la passe finit **sept mois apres janvier 1972** et toutes les
neuf unites sont journalisees, contre 7/9 lors du premier recontrole.
Sur 1024² a trois ans, le debit passe de **48 tranches et 145 paires**
a **272 tranches et 763 paires** (x5,67 tranches ; x5,26 paires),
avec une unite `VALU` close en fevrier 1972. A six ans, le meme code
termine aussi `OIL_` en septembre 1973 et `IORE` en octobre 1975.
Cela represente **3/10 unites closes apres quatre annees actives
(1972-1975)**. Aucun `stale_restart` ou recul cumulatif detecte.
Les 7 autres unites sont encore ouvertes ; ce constat **ne satisfait pas
l'objectif de completude dans un temps raisonnable** sur 1024².

Les derniers echantillons individuels du bras **variante a six ans**
montrent la concentration du travail et permettent de distinguer une
avance reelle d'un simple compteur de paires : `PASS` **source 2/731**
et 361 destinations visitees, fret cargo API 1 **3/141** (301 visites),
cargo 4 **4/146** (443), cargo 5 **2/175** (316), cargo 6 **3/146**
(339), cargo 7 **11/86** (814), cargo 9 **5/82** (471).
`OIL_`, `IORE` et `VALU` sont clos. **Zero recul individuel** constate
sur les points de controle disponibles. Les echantillons tournants
ne prouvent pas l'etat de tous les curseurs a chaque instant ; ils
ne remplacent ni un scan spatial borne ni un controle de completude.

L'ecart entre 3 568 et 5 056 tranches des deux bras a six ans confirme
que le **debit depend de la trajectoire du moteur**. Ce ne sont ni deux
repetitions independantes ni une preuve de performance moyenne. Ne pas
extrapoler 10/10 a partir de ces debits : les sources restantes ont des
tailles differentes et leurs courbes ne sont pas lineaires.

### Attribution des couts, sources de frein et neutralite

Le decodeur actualise `sweeps/analyze_rlw04.py` expose pour chaque fichier
les appels, `low_reserve`, tranches bonus, paires/tranche, mois, pics
complets et totaux de cout et des curseurs individuels. Pour le **bras
reference de la campagne ON 1024² 3 ans** : **135 appels observes**,
**50 refus de reserve** (37 %), **188 tranches bonus**, **22,67
tranches/mois**, **2,81 paires/tranche**, 763 paires.

| Cout mesure, ON 1024² 3 ans reference | OpCodes | Part des opcodes additionnes (`tranches + init + refresh`) |
|---|---:|---:|
| Calcul des pas `total_work_ops` | 145 316 | **48,01 %** |
| Logs `ENUM + UNIT` | 4 594 | **1,52 %** |
| Initialisation unique | 1 347 | **0,45 %** |
| Rafraichissements (20 fois) | 600 | **0,20 %** |
| Reste dans les tranches (admission, rotation, mesures et boucles) | 150 824 | **49,83 %** |
| **Ensemble** | **302 681** | **100 %** |

Les mesures d'etape sont instrumentees et ont leur propre cout ; la
repartition est valable pour cette version de sonde et **ne mesure pas
le temps CPU absolu de tout l'agent**. Le pic de log ENUM est **280**,
le pic de refresh **30**, le pic d'initialisation **1 347** : le cout
des journaux et du rafraichissement est secondaire. Les appels refusés,
la coordination du parcours et le nombre de sources/puits a couvrir
expliquent la lenteur restante. Les pics complets de tranche incluent
les logs : 1 622 sur 256² et au plus 1 559 sur 1024² a six ans,
**toujours sous 1 800** ; l'initialisation est un evenement separe.

OFF : `analyze_rlw04.py --expect-off` reussit sur les deux fichiers des
campagnes `off256` et `off1024` ; `_rlw04Step()` n'est pas appele.
Les duels OFF **ne sont pas bit-a-bit identiques** : OFF 256² montre
`profit_year` variante - reference **+1 468 £/an** et ratio des valeurs
**0,987009**, tandis que OFF 1024² donne delta **0** et ratio **1**.
Les deux duels ON 3 ans sont identiques sur le profit terminal entre
leurs propres bras, mais ON 1024² 6 ans produit des trajectoires
differentes (`profit_year` delta **-1 259 344 £/an**, ratio de valeur
**1,02123**). Ces chiffres de **graine unique** ne constituent pas une
qualification economique du comportement de l'IA ni une preuve
d'equivalence ON/OFF. Aucun reglage de politique par defaut n'a change.

Reproduction depuis ce worktree :

```powershell
$env:PYTHONPATH=(Get-Location).Path
uvx --from 'pytest==8.4.2' pytest -q sweeps/test_analyze_rlw04.py sweeps/test_rail_long_window_probe.py sweeps/test_rail_long_window_policy.py sweeps/test_rail_long_early1.py sweeps/test_v269_rail_late_relax.py
python -X utf8 sweeps/analyze_rlw04.py results/rlw04_priority4_on256_20261022_engine --require-complete
python -X utf8 sweeps/analyze_rlw04.py results/rlw04_priority4_on1024_20261022_engine --format markdown
python -X utf8 sweeps/analyze_rlw04.py results/rlw04_priority4_on1024_6y_20261022_engine --format markdown
python -X utf8 sweeps/analyze_rlw04.py results/rlw04_priority4_off256_20261022_engine --expect-off
python -X utf8 sweeps/analyze_rlw04.py results/rlw04_priority4_off1024_20261022_engine --expect-off
```

**41 tests cibles verts** (dont detection du recul par source) et
`git diff --check` OK. Les JSON de bilan,
manifestes, bundles et logs sont conserves sous `results/rlw04_priority4_*_20261022`.
Le code s'execute avec `RLW04_SHADOW=false` en etat courant ; aucun
`air_*` ni fichier du depot principal touche, aucun commit/push et aucun
processus tiers termine. **Verdict :** budget et passe 256² qualifies ;
**1024² 3/10 a 6 ans, non qualifie pour RLW-05**. Continuer uniquement
par une optimisation isolee du parcours geometrie/source sur carte large,
avec preuve de couverture et de cout, avant tout candidat a financer ou
une porte A/B economique.

### Reprise de la session interrompue (22/10, verification finale)

Une nouvelle inspection du worktree et des sorties `rlw04_cadence2_*`,
`rlw04_priority3_*` et `rlw04_priority4_*` confirme que les campagnes
`priority4` terminent l'experimentation de cadence disponible : aucun
conteneur OpenTTD actif et aucun duel manquant a reprendre. Les cinq appels
au decodeur ci-dessus ont ete reexecutes avec succes, dont `--require-complete`
sur ON 256² et `--expect-off` sur les deux tailles OFF. Les **deux logs par
campagne** sont presents. La campagne ON 1024² de six ans s'arrete normalement
au terme du jeu, mais son **enumeration reste inachevee** : 3/10 unites,
3 568 / 5 056 tranches, zero depassement, 10 414 / 14 905 paires examinees.
Il s'agit d'un echec de l'objectif de couverture, pas d'un banc a relancer
pour cause de processus interrompu.

Les cinq analyses additionnelles des campagnes intermediaires montrent
egalement **deux logs shadow par campagne, zero overrun et aucune passe
integralement close** : `cadence2` 256² 3 ans **8/9** unites (896 tranches,
1 550 paires), 1024² 3 ans **1/10** (160, 479), 1024² 6 ans **1/10**
(896, 2 667) ; `priority3` 1024² 3 ans **1/10** (160, 447), 1024²
6 ans **2/10** (896, 2 582). Ces essais sont historiques : il n'y a
pas de reliquat d'execution susceptible de remplacer la campagne `priority4`.

Le delai de cloture integral en 1024² **n'est pas mesure**. En particulier,
les sept unites encore ouvertes le **31/12/1975** signifient **plus de
48 mois de recherche depuis janvier 1972**, sans date de terminaison
defendable. Le curseur PASS a seulement atteint la source 2/731 dans le
dernier echantillon ; la priorite des petites unites et l'heterogeneite
des nombres de destinations interdisent d'extrapoler ce point a une date
de fin. Poursuivre avec le meme algorithme et les memes graines sans
changement de parcours geometrie/source ne leverait pas ce blocage.

Verification Python sur l'hote :

```powershell
$env:PYTHONPATH=(Get-Location).Path
uvx --from 'pytest==8.4.2' pytest -q sweeps/test_analyze_rlw04.py sweeps/test_rail_long_window_probe.py sweeps/test_rail_long_window_policy.py sweeps/test_rail_long_early1.py sweeps/test_v269_rail_late_relax.py --tb=short
```

**41 passed**. L'invocation non restreinte `uvx --from 'pytest==8.4.2'
pytest -q --tb=short` reste en erreur **pendant la collecte**, sans test
RLW-04 en echec : `evidence/review/air_catalogue_correctifs_20261011/
test_ac_catalogue_fixes.py` calcule une racine de projet incorrecte ;
`sweeps/archive/diag_c49_vehicles_test.py`, `sweeps/archive/test_c46_shadow.py`
et `sweeps/smoke_test.py` exigent `openttdlab`, absent du seul environnement
`uvx --from pytest`. Ces tests hors perimetre sont conserves, aucune
configuration de collecte n'a ete changee pour les masquer.

La neutralite OFF demontree est **fonctionnelle** (zero evenement RLW04),
pas une equivalence economique bit-a-bit : dans le duel OFF 256², le delta
terminal est encore +1 468 £/an et le ratio de valeur 0,987009. Le flag
`RLW04_SHADOW` dans `globals_post.nut` reste **false**. Le verdict RLW-04
reste **ouvert / blocage de couverture 1024²**, sans proposition RLW-05,
sans variante de politique et sans porte A/B.

## Parcours spatial incremental — dernier recontrole (22/10)

**Verdict : la grille respecte le budget, mais la passe 1024² ne finit pas
dans les 12 mois de jeu actifs demandes.** A fin 1972, seulement **1/10
unites** est terminee. Le temps d'une passe complete sur cette carte demeure
inconnu ; l'essai reste un prototype shadow desarme et non qualifie.

### Implementation et instrumentation

L'ancien echantillon regulier de 128 indices de destinations est remplace par
un index spatial **par unite cargo** en cellules de **128 tuiles**. Le snapshot
reste fixe aux refreshs. Chaque tranche construit l'index progressivement par
lots de **4 puits**, puis parcourt les cellules de coordonnees proches de la
source. Pour chaque puits, la distance Manhattan 224..288 est testee a partir
des coordonnees du cache **avant** la resolution du puits et les validations
API. Les couples voyageurs imposent `destinationIndex > sourceIndex`.
Le quota de 128 destinations s'applique maintenant aux puits **dans l'anneau**
par source ; cela change la couverture des paires par rapport a l'ancien
quota de 128 avant filtrage spatial. Le compteur 201..223 vaut desormais
zero par construction, sans conclusion sur l'absence de ces liaisons.

Un pas lit jusqu'a deux destinations spatiales, puis une seule si un pic
historique de travail atteint 850 opcodes. La garde estime le pas suivant
par `min(maxWorkOps,850)+140`, avec plancher 650 et reserve de sortie 300 ;
le plafond reste **1 800 opcodes par tranche**, maximum 5 tranches par appel.
`RLW04_ENUM` ajoute les etapes et opcodes d'index (`index_steps`, `indexed`,
`index_ops`) et de scan (`scan_steps`, `scan_ops`), les cellules vides
`cell_skips`, elagages `geo_skips` et sources achevees `sources_advanced`.
`sweeps/analyze_rlw04.py` consolide ces mesures.

Les essais precedents de cette grille ont expose une **starvation d'admission** :
`grid1_on256`, 96 tranches, pic du pas 627 et seulement 7/9 unites ; puis
`grid2_on1024`, 160 tranches, pic du pas 997 et 1/10 unite. Le multiplicateur
de garde sur le plus grand pas interdisait ensuite toute nouvelle tranche.
La garde adaptee du dernier bundle `grid3` corrige cette starvation observee,
sans atteindre l'objectif 1024².

### Recontroles ON et OFF du bundle final

Docker Desktop `desktop-linux`, image `openttd-lab:latest` de SHA
`sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
Lanceur hote `sweeps/run_c66_reference.py`, exclusivement dans
`.worktrees/rlw04`, seed 42, 1970-1972 (3 ans), 1 repetition, `probes=6`,
**9 CPU / 8 Go / 9 workers**, une campagne a la fois. Chacune comprend deux
duels sains entre `v269_rail_long_max=0` et `=200`, tous deux effectifs a 0.
La comparaison ON/OFF utilise des bundles differents par la seule ligne
`RLW04_SHADOW` du code source : comparaison recursive des fichiers `ai/OpexAI`
des bundles `grid3_on256` et `grid3_off256` : **une seule difference,
`globals_post.nut` (true contre false)**. Empreintes ON
`3496ec383f6ef44f693f5ab5d190a08a79e6877aae08c36a89817de70ffa70c5`,
OFF `547af3437f4582f028817f02d1fce8f065c8f6ea6450f20da1e32ab1615da281`.
Le flag du worktree est restaure a **false**.

| Campagne `rlw04_grid3_*_20261022` | Carte | Statut des duels | Passe ON | Tranches par bras | Overrun | Pic complet / 1800 | Paires 224..288 | Sources avancees | Index / scan, ops |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|
| `on256` | 256² | complete/complete | **9/9 en juillet 1972**, 7 mois actifs | 599 | **0** | **1725** | 253 | 86 | 9 583 / 250 989 |
| `on1024` | 1024² | complete/complete | **1/10 a fin 1972**, non complete | 288 | **0** | **1772** | 24 | 63 | 65 446 / 89 086 |
| `off256` | 256² | complete/complete | s.o., **0 trace RLW04** | 0 | s.o. | s.o. | 0 | 0 | s.o. |
| `off1024` | 1024² | complete/complete | s.o., **0 trace RLW04** | 0 | s.o. | s.o. | 0 | 0 | s.o. |

Sur **1024²**, le dernier checkpoint totalise 776 puits indexes en 197 pas
d'index, 253 pas de scan, 1 157 cellules vides sautees et 179 eliminations
geometriques. Les 20 refreshs ne causent aucun recul visible. Le travail
mesure atteint 154 532 opcodes pour 276 823 opcodes de tranches (55,82 %),
dont 65 446 pour l'index et 89 086 pour le scan. L'initialisation hors
tranche atteint 1 813 opcodes. Ces nombres sont des minima observes :
les tranches apres le dernier checkpoint de seize peuvent ne pas apparaitre.
Les 63 sources avancees ne sont pas des candidats constructibles.

Les deltas de `profit_year` entre bras du meme bundle ON sont **0** sur les
deux cartes. OFF 256² : **-1 468 GBP/an**, ratio de valeur **1,013162** ;
OFF 1024² : delta **0**, ratio **1**. Une seule graine et l'effet de
trajectoire du moteur interdisent une revendication de neutralite economique
bit-a-bit entre ces parties ; la garde OFF est confirmee fonctionnellement.

Reproduction depuis le worktree :

```powershell
python -X utf8 sweeps/analyze_rlw04.py results/rlw04_grid3_on256_20261022_engine --require-complete
python -X utf8 sweeps/analyze_rlw04.py results/rlw04_grid3_on1024_20261022_engine --format markdown
python -X utf8 sweeps/analyze_rlw04.py results/rlw04_grid3_off256_20261022_engine --expect-off
python -X utf8 sweeps/analyze_rlw04.py results/rlw04_grid3_off1024_20261022_engine --expect-off
$env:PYTHONPATH=(Get-Location).Path
uvx --from 'pytest==8.4.2' pytest -q sweeps/test_analyze_rlw04.py sweeps/test_rail_long_window_probe.py sweeps/test_rail_long_window_policy.py sweeps/test_rail_long_early1.py sweeps/test_v269_rail_late_relax.py
```

La construction d'un index par cargo et les nombreux pas de scan par source
restent trop couteux : 1024² ne couvre qu'une faible partie des sources en
un an. Un prolongement avec **index mutualise entre cargos** et parcours
direct des cellules annulaire serait un autre mecanisme, a qualifier dans
une experience distincte. Sauter arbitrairement les sources pour annoncer
une « passe complete » serait trompeur. Aucun candidat RAIL long eligible
et constructible n'est demontre, aucune porte A/B n'est ouverte. RLW-04 reste
**[ ]**, avec flag OFF, sans changement de defaut, commit, push ou AIR.
**43 tests cibles passes**, `git diff --check` reussi et aucun conteneur
Docker actif a la cloture. Les anciens tests de stride historique restent
des fixtures de comparaison, pas une preuve du nouveau quota spatial.
