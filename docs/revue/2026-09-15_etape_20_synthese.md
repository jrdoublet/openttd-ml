# Étape 20 — Synthèse et priorisation des correctifs

- **SHA revu** : `c74a123` (à corriger si la session revoit un autre commit)
- **Modèle / effort prévus** : Opus 5 / high
- **Périmètre** : Les 19 fichiers de constats de `docs/revue/`
- **Plan** : `docs/revue_code_2026-09-15_plan.md`

**Enjeu annoncé**

Regrouper par mécanisme, trancher gravité et ordre, produire
`docs/revue_code_2026-09-15_correctifs.md`, et solder les groupes G0–G12 du 09-06.

**Rappel de méthode** — diagnostic seulement, rien n'est corrigé au passage. Vérifier à la main,
pas par grep seul. Vérifier le défaut d'un réglage avant de le qualifier de code mort. Ancrer
chaque constat sur `fichier:ligne`. Ne lire que `ai/OpexAI/CLAUDE.md` et les fichiers du
périmètre : pas `docs/taches.md` en entier, pas les journaux, pas `results/`.

---

## Constats

Le livrable de cette étape n'est pas un fichier de constats supplémentaire : c'est le regroupement
**par mécanisme** de tous les constats des 19 étapes précédentes, produit dans
`docs/revue_code_2026-09-15_correctifs.md` (5 tiers, groupes H1-H5/B1-B9/M1-M7, statut des groupes
G0-G12 du 09-06, ordre d'exécution recommandé, greffes opportunistes vers `docs/taches.md`) —
conformément à la sortie attendue décrite dans le tableau « Clôture » de
`docs/revue_code_2026-09-15_plan.md`, qui diffère du squelette générique ci-dessous.

Un trou de couverture a été identifié au passage (fichiers de harnais de campagne jamais lus par
aucune étape) et a donné lieu à l'ouverture de l'étape 21, tenue le 2026-09-16 :
`docs/revue/2026-09-15_etape_21_harnais_campagne.md`.

## Vérifié, n'est PAS un bug

Voir `docs/revue_code_2026-09-15_correctifs.md`, section « Tier « ne pas toucher maintenant » » et
le tableau de statut des groupes G0-G12.

## Hors périmètre, à relire ailleurs

Voir `docs/revue_code_2026-09-15_correctifs.md`, section « Deux questions que les étapes ont
explicitement renvoyées à celle-ci » (durée du smoke test ; fichiers de harnais non couverts →
étape 21).

## Avancement des correctifs — 2026-09-16

**H5 est clos côté instrumentation et décision `loop_budget`.** Le banc officiel et
le diagnostic mensuel publient désormais un coût d'opcodes **observé et borné par
son périmètre**, jamais présenté comme CPU total. Les sources sont les panneaux
existants `IG|`, `OB|A`, `RB|`, `OA|`, `OM|W` ; les formats anciens restent lisibles.
Le ratio `final_profit_year_per_observed_mopcode` n'est interprétable qu'à horizon et
instrumentation identiques.

Le 5×6 `loop_budget=0` vs `1` (`review_h5_loop_budget_5x6.json`) donne cinq égalités
exactes sur toutes les métriques économiques/physiques et toutes les composantes
observées : aucun 20×10 ni changement de défaut. Le sous-comptage des sondes
pont/tunnel dans `state.iterations` reste une limite du modèle de budget rail ; il
n'est pas « corrigé » en changeant le pathfinder, puisque `OB|A` fournit le coût
réel mesuré nécessaire à H5.

**B1 est avancé sans adoption implicite.** 08.1 rend le verdict initial de
`BuildAirport` décisif pour 771 et les erreurs structurelles ; smoke 2×3 et diagnostic 5×6
passent. `air_town_limit_memory` reste à 0 et aucun faux fallback distant-join/nettoyage n'est
ajouté. `early_slot` reste adopté.

**B2 est clos côté vérité de mesure.** 02.1 attribue les durées à l'état précédent ; le rail
reprenable remonte aussi ses refus `cash`/échecs ; stocks et flux mensuels sont distingués ;
`--no-funnel` existe ; l'absence de détail par mode est marquée `missing_emitter`.
Le 5×6 final `review_b2_c63_real_5x6_v2.json` est fail-closed et rend
`invariants.ok=true`. La nouvelle mesure invalide l'ancienne conclusion « le capital est
exclu » : `unaffordable` représente 1 495 jours sur les 25 années-graines closes. Aucun défaut
comportemental n'est adopté sur ce diagnostic.

**B4 est clos sur son P1 et son préalable d'éligibilité feeder bus.** Construction, refleet et
extension partagent maintenant les mêmes indicateurs d'ordre stricts ; le feeder bus dédié conserve
son `kind`, contrairement au feeder courrier volontairement exclu du filtre pax. Le 5×6 ORDL-aware
`review_b4_bus_extensions_5x6_ordl.json` exerce 13 vraies `feeder_extension` et 12 listes d'ordres
étendues finales : zéro chaîne invalide, ville/intermédiaires `NO_UNLOAD`, hub
`TRANSFER|NO_LOAD`. Le smoke 2×3 post-`.nut` et le contrat statique 6/6 passent. Aucun changement de
défaut ni adoption de politique n'est tiré de ce 5×6 diagnostique ; les voisins 09.2/09.7 restent
séparés.

**B3 est clos comme expérimentation non adoptée.** La cible brute `vehiclesForVolume`, la capacité
simultanée de quai `roadBerthCapacity` et le plafond de flotte `roadVehicleCap` sont séparés et
propagés jusqu'au ranking, au chantier/refleet, aux feeders et au rapport. Le switch
`road_time_scaled_cap` reste à 0 ; sous 1 il ne modifie que le pax et reste borné par
`MAX_ROAD_VEHICLES`, tandis que le fret conserve l'ancien cap. Smoke 2×3 final
`review_b3_time_scaled_cap_smoke_2x3_v3.json` : PASSED. Le 5×6 probant
`review_b3_time_scaled_cap_paired_5x6_v2.json` a 10/10 runs sains et valide tous les invariants de
séparation, mais n'exerce jamais le cap temporel pax : `road_pax_build=0`, aucun pax classé/choisi,
`town_growth` à cible brute <=1. La variante donne en outre -52,1 k£ de valeur moyenne et
-29,1 k£/an de profit (2 V / 3 D). Aucun 20×10 n'est lancé ; instrumentation et correctif restent
derrière switch pour un contexte futur réellement exposé.

**B8 est clos côté invariants de cycle de vie.** `_resizeAirFleets` ignore désormais toute ligne
AIR `scrapping` avant crash-refleet/croissance, et `_tryBuildFleetProject` revalide le même état à
la frontière transactionnelle afin qu'un projet de cache stale ne puisse acheter un avion. Chaque
nouveau cycle de rebut réécrit son `scrapStartYear`; un recovery feeder efface le timer tout en
conservant le fallback de compatibilité old-save. Le test ciblé passe 7/7, le smoke 2×3 sur la
politique `early_slot` adoptée passe, et le diagnostic 5×6 est sain 5/5. Ce dernier ne rencontre
aucun cycle de rebut en six ans : il ne fournit donc aucune attribution économique et ne remplace
pas les contrats de sûreté. Aucun défaut comportemental n'est ajouté et `early_slot` reste adopté.

**M1 est clos côté vérité de mesure.** C50 publie la valeur trimestrielle réelle ; VIVIER distingue
rejets et candidats conservés ; le capital du pool est explicitement nommé tout en conservant les
aliases IB/JSON ; `knapsackExact=false` reste un slot legacy honnête. Tests M1 8/8,
selftest C50 OK et smoke 2×3 2/2.

**B6 est clos sans nouvelle politique adoptée.** Le 5×6 apparié a 10/10 runs sains. Le budget
snapshot est réellement périmé (630/639, 50 passages avec `affordability_flips`), le tri
ratio diffère du meilleur profit abordable dans 146/501 cas, le `turnoverBonus` est
réellement exposé en pré-classement et le recyclage économique atteint 43 jours. Ces faits
séparent mesure, classement et politique : `portfolio_floor_pct` reste 0,
`PORTFOLIO_MAX_BATCH` reste 1 et `early_slot` reste adopté. Aucun nouveau 20×10
n'est lancé ; le plancher statique 50 % déjà évalué après le 09/09 est défavorable.

## Réconciliation G0 — 2026-09-16

Le factoriel causal `review_g0_abandon_factorial_4arm_5x6.json` a vérifié que le filtre de
génération et le cooldown sont réellement exposés ; le bras `0/0` avait un signal 5×6 suffisant
pour justifier une autorité formelle, sans changer le défaut.

L'autorité C66.4 `results/review_g0_c66_4_20x10.json` a tourné sur 20 graines appariées,
10 ans, avec `profit_year` primaire, seuil utile +50 000 £/an et garde
`company_value >= -5 %`. Les 20/20 paires sont complètes. Pour `0/0` contre `1/365` :
delta moyen `profit_year = +11 264,85 £/an`, 11 V / 9 D, `p=0,823803` ; la valeur est à
+2,759 % en ratio des moyennes. Verdict officiel : `fail_primary`
(`sign_pass=false`, `primary_mean_pass=false`, `value_guard_pass=true`).
**G0 est clos sans adoption : les défauts restent `abandon_gen_filter=1` et
`abandon_cooldown_days=365`.**

Bundle : `845c5b283d86c05fb3360445596e1967edde1d2cbfcd82fb19f08e7864b1dcb2`.
Manifest : `78c4ac1fe74189a119f954902b8a24242c44158bd812bc5d9a5792d4d7bb1047`.
Aucun `.nut` n'ayant changé pour G0, aucun nouveau smoke n'était requis.

## Matrice globale réconciliée — 2026-09-16

| Groupe / item | Statut actuel | Preuve / validation | Limite / suite |
|---|---|---|---|
| H1 | fait | règle d'adoption/sign-test utilisée par C66.4 | ne pas rouvrir sans régression |
| H2 technique | fait | réglages effectifs gelés, audit comparaison, contrat 230 settings | G0 associé désormais rendu |
| H3 | fait | compteurs physiques + fixtures/API | ne pas rouvrir sans régression |
| H4 | fait | santé/horizon fail-closed + cas valeur décroissante | ne pas rouvrir sans régression |
| H5 | fait | coût d'opcodes observé branché | périmètre partiel, pas CPU total |
| G0 | fait — non adopté | C66.4 20×10, 20/20 paires, `fail_primary` | conserver `1/365` |
| B1 | fait | 771 + smoke/5×6 | ne pas rouvrir |
| B2 | fait | C63/funnel truth + smoke/5×6 | ne pas rouvrir |
| B3 | fait — expérimental non adopté | 5×6 apparié | default inchangé |
| B4 | fait | contrat feeder orders + smoke | ne pas rouvrir |
| B5 | fait | 11/11 état/persistance + round-trips | expansion active non capturée au checkpoint |
| M1 | fait | 8/8 + selftest C50 + smoke 2×3 | comportement préservé |
| B6 | fait — 06.5 et 06.11 mesurés, non adoptés | 06.5 : passif 10/10, 41/630 choix changés ; variante 5×6 −135,5 k£/an. 06.11 : 5×6 10/10, 136/348 tops recyclés, 6/114 décisions fret changeraient après repricing | garder `portfolio_fresh_budget=0` et `portfolio_cache` ; refresh général 06.11 rejeté/non adopté ; 06.12 dormant |
| **B9 / G4 résiduel** | **fait** | 17/17 + smoke 2×3 + 5×6 final 10/10 ; marginal joint exact 59/59 | aucun default AIR adopté |
| B7 / G11 | fait — 10.1/10.2/10.3 techniques + 10.5 mesuré | budget Lakes interruptible, distance inconnue fail-closed, connectivité fail-before-spend ; RAM/opcodes Lakes mesurés jusqu'à 2048² | scan freeze 2026/1337 inconclusif ; 10.5 clos comme mesure, aucun default changé |
| C57 | **abandonné** | le calibrage 50 000 opcodes ne sera pas poursuivi | architecture Lakes destinée à être retirée ; supersédé par C67 |
| **C67** | **ouvert — architecture/mesure** | analyse de carte par blocs 5×5 ou 10×10, typage eau/terrain/relief | mesurer granularité, RAM/opcodes et précision avant branchement ; remplacera ensuite Lakes |
| B8 | fait | 7/7 contrats rebut + smoke | 5×6 non exposé : ne pas surinterpréter |
| M4 | fait — diagnostic + 16.2 corrigé + 16.4 mesuré | post-fix `max_trains=0` : 10/10, 0 projet rail, 0 failed spend ; Lakes ~128 B/tuile, ~14 opcodes/tuile jusqu'à 2048² | 16.1 non reproduit ; 16.4/10.5 clos comme mesure externe |
| M3 / G12 → C68 | fait — diagnostic puis politique adoptée | M3 5×6 10/10 ; C68 smoke 4/4, 5×6 10/10, autorité 20×10 20/20 | `air_route_plane_selection=1` adopté ; NewGRF non mesuré |
| M7 / 11.1 | fait | contrat 15/15/15 + 13/13 + selftest C65 + smoke 2×3 4/4 | fallback inconnu seulement ; tâches connues inchangées |
| M7 / 11.2 | fait dans le workspace courant | retours booléens explicites de `_tryTownGrowth` | comportement déjà présent, non rouvert |
| M2 | dormant ou non exposé | options concernées non actives | traiter avant réactivation |
| M5 / G2 résiduel | dormant ou non exposé | `c39_engine_refresh=0` | pas de lot autonome |
| M6 | dormant | pas d'exposition courante | pas de correctif autonome |
| M7 / 11.3 | dormant ou non exposé | branche inactive | surveiller seulement |
| M7 / 11.6–11.7 | fait via B5 | 11/11 persistance + round-trips B5 | expansion active non capturée dynamiquement au checkpoint |
| M7 / 11.8 | fait / caduc | `_lastAirFleetMonth` absent | aucune action |
| G3 résiduel | fait | blocking/resumable → même recalcul post-A*, `candidate.kind` couvre fret | pas de banc supplémentaire requis |
| 07.2 rail iterations | limite diagnostique, non P1 | sondes structure absentes de `state.iterations`, mais incluses dans `OB|A.result.opcodes` | corriger le compteur changerait les budgets/pathfinder |
| Étape 21 / 21.1 | non-bug actif / P3 inerte | garde `unitnumber==0` rend le mauvais littéral rotor sans effet | correction cosmétique/test hélico seulement |
| Étape 21 / 21.2 | largement fait | `test_campaign_freeze.py` + contrat 230 + guards policy/fingerprint | `prepare_frozen_campaign`/freeze libraries sans test unitaire isolé |
| Étape 21 / 21.3 | fait | tests valeur décroissante + uptick final | H4 fail-closed conservé |

### Suivi C68 — graines régressives à expliquer

L'adoption C68 reste valide selon la règle pré-enregistrée, mais elle ne doit pas masquer
l'hétérogénéité inter-cartes. Au checkpoint final 1979, `profit_year` régresse sur cinq graines :
`7`, `42`, `1337`, `12345`, `424242`. Une analyse ultérieure doit relier ces trajectoires aux
propriétés de carte et à la séquence de décisions : distances et géométrie des villes, choix/type
d'aéroport, alternatives d'appareil compatibles, ordre des investissements, routes écartées par le
`maxOrderDistance` de l'appareil catalogue et demande calculée avant C68. Le cas `7` est prioritaire
car profit, score et valeur sont durablement plus faibles ; `42`, `1337`, `12345` et `424242`
montrent plutôt une dégradation tardive du profit malgré une valeur finale encore supérieure.

La table brute annuelle complète (checkpoint de décembre, 1970–1979) est conservée dans
`results/review_c68_air_route_plane_20x10_v2_annual_metrics.csv`, avec baseline, C68 et delta pour
`profit_year`, `performance_history` et `company_value` sur les 20 graines.

### Clôture B7 / G11

10.1 et 10.3 sont désormais fermés comme défauts techniques P1. `lib_water.nut` vérifie le budget
opcodes jusque dans les parcours internes de Lakes et évite de committer une grosse mutation de
graphe avant la fin des scans bornés. `builder_water.nut` valide les fronts réels et la
connectivité bornée avant le premier quai sur le chemin Lakes ; le comportement legacy conserve
sa vérification post-construction. Le contrat B7 ciblé, la suite commune **61/61**, les selftests,
`py_compile` et `git diff --check` passent. Le smoke final
`results/review_final_residuals_smoke_2x3.json` est complet et sain.

Le diagnostic ciblé `results/review_b7_water_c56_targeted_2x10.json` sur 2026/1337 ne produit pas
de trace C56 datée et est donc **inconclusif** (`frozen_count=null`, `measurable_count=0`). Le
diagnostic a été rendu fail-closed pour que cette absence de mesure ne soit jamais convertie en
« 0 gel ». Aucun default eau n'est changé ; 10.2 a ensuite été corrigé fail-closed. 10.5 a été
clos séparément par mesure externe RAM/opcodes le 2026-09-17.

### Preuves de revue versionnables

`results/` reste un espace de travail ignoré. Les JSON effectivement cités par la revue sont
recopiés byte-for-byte sous forme gzip déterministe dans `evidence/review/`. L'index
`evidence/review/index.json` enregistre, pour chaque preuve, le chemin source, la taille et le
SHA256 du JSON brut ainsi que ceux du gzip. `sweeps/test_review_evidence.py` décompresse chaque
archive, revérifie le hash brut et la recompression déterministe : les conclusions de la revue ne
dépendent donc plus de fichiers locaux gitignorés impossibles à rattacher à une version.

### Clôture B9 / G4 résiduel

La sonde `air_catchment_probe` reste default-off et sépare le modèle pré-électoral, la
production réelle de l'aéroport, l'union station complète, le marginal joint, le coût réservé et
le coût réellement payé. Le 5×6 pré-correctif
`results/review_b9_air_catchment_5x6.json` a exposé **148 builds / 296 endpoints** et montré que
la somme brute des arrêts joints double-comptait le catchment aéroport sur **50/63** endpoints
neufs.

Le workspace courant ferme 08.6/08.8/08.9/08.10 sans nouveau default : réserve pré-électorale
inexacte retirée, littéraux 22 % centralisés dans `TOWN_CATCHMENT_SHARE_PCT`, marginal joint
recalculé sur l'union réelle, mélange proxy-population / production physique supprimé sous le
default. Le smoke final `results/review_b9_air_catchment_smoke_2x3_v4.json` passe 2/2 et le
5×6 `results/review_b9_air_catchment_reconciled_5x6.json` passe **10/10**, zéro invariant
cassé, `model_error_pax=0` sur **59/59** endpoints neufs.

La variante de demande production-based n'est pas réintroduite : l'autorité historique
`results/bench_air_demand_plan_10y.json` l'a déjà rejetée (**−51,5 % `profit_year`**,
5/20, `p_signes=0,041`). Le signal de placement AAAHogEx (distance moyenne 6,06 vs
7,47 tuiles ; centre couvert 37,85 % vs 20,0 %) reste descriptif faute de production catchment
exacte côté AAA. `air_demand_plan=0`, `air_catchment_probe=0` et `early_slot=1` sont
inchangés.

### Clôture M3 / G12

`equipment_roi_probe` est default-off ; avec C68 et le nouveau `air_residual_feeder` expérimental
default-off, le contrat courant porte **232 settings**. La sonde conserve
des alternatives uniquement pour le diagnostic, compare avant admission et après route/site, et
sépare capacité native, proxy de refit et capacité réellement observée.

Le smoke `results/review_m3_equipment_roi_smoke_2x3_v5.json` passe **4/4**. Le 5×6
`results/review_m3_equipment_roi_5x6.json` passe **10/10**, horizon complet :
rail 55 106 comparaisons sans multi-choix ; route 736 comparaisons, 18 multi-choix sans regret ;
air 79 807 comparaisons toutes multi-choix, 75 742 différences face au meilleur profit,
77 884 face au meilleur ROI et **2 371 flips d'admission**. Le regret de profit moyen air vaut
7 776,81 £/an.

Le set vanilla n'expose aucun proxy refit et toutes les capacités réellement relues après refit
coïncident avec le catalogue. Il n'y a donc pas de P1 de mesure à corriger. Le risque NewGRF reste
une limite explicitement non mesurée. Le signal air est un P2 de politique : l'appareil 228 est
pré-élu partout alors que le meilleur profit dépend de la route.

**Suite C68 du 17/09 : adoptée.** `air_route_plane_selection` réutilise les alternatives M3 et
`OpexAirEconomics` pour choisir l'appareil par route, sans changer volontairement les sites/type
d'aéroport/demande déjà déterminés par le chemin historique. Smoke post-implémentation
`review_c68_air_route_plane_smoke_2x3_v3.json` : **4/4 sain**. Diagnostic
`review_c68_air_route_plane_5x6.json` : **10/10**, 4/5 deltas `profit_year` positifs,
**+235 565 £/an** moyen. Autorité `review_c68_air_route_plane_20x10_v2.json` : **20/20 paires**,
15 V / 5 D, `p_signes=0,041389`, **+128 201 £/an** moyen, garde valeur **+34,206 %**, verdict
**`pass`**. Le défaut livré passe donc à `air_route_plane_selection=1`. Le smoke post-adoption
`review_c68_adopted_default_smoke_2x3.json` passe **2/2** et confirme dans son manifeste que C68=1
provient du défaut (`defaults=effective=1`) et non d'un override explicite.

### Clôture M4

Le 5×6 `results/review_m4_conformity_5x6.json` exerce séparément
`vehicle.max_trains=0` et `pf.forbid_90_deg=1`, chacun sur cinq graines × six ans : **10/10 runs
sains par scénario**.

Avec `max_trains=0`, Opex termine avec zéro train **et zéro station facility rail** mais choisit
30 projets rail et atteint 15 échecs `NOTRAIN`. C63 mesure 176 313 £ de dépenses rail échouées ;
huit années-graines où `NOTRAIN` est la seule cause cumulent **120 018 £**, preuve directe du
chantier payé avant l'échec matériel. Le parser physique ne compte pas séparément voie/dépôt :
leur absence persistante reste non mesurée. C'est un P2 d'admission/politique, pas un P1 : aucun
patch sous la règle de cette passe.

Le contrôle `results/review_m4_conformity_control_5x6.json` passe aussi 10/10. À titre
descriptif seulement, `max_trains=0` vaut en moyenne 720 197 £/an de `profit_year` contre
747 876,2 £/an au contrôle (−3,70 %) et 2 182 885,2 £ de `company_value` contre
2 226 222,2 £ (−1,95 %). Ce 5×6 n'est pas une autorité d'adoption.

`pf.forbid_90_deg=1` ne provoque ni crash ni blocage d'horizon ; 34 projets rail sont choisis et
du rail est construit dans les cinq graines (1/4/2/2/2 véhicules finaux). Cela ferme le
crash/gel observable sur ce périmètre, pas les internals de la bibliothèque externe. 16.4 a ensuite
été mesuré hors de ces runs avec le micro-banc constructeur Lakes : 256²/512²/1024² donnent une
pente stable proche de 128 B/tuile et 14 opcodes/tuile ; le 2048² long 3× termine 3/3 avec un delta
RSS médian de 524 788 KiB et 58 726 159 opcodes nets. L'ancien 2048² incomplet était limité par
l'horizon, pas par un OOM ou un plafond `AIList` démontré. Autorités :
`results/review_water_memory_10_5_16_4_v3.json` et `results/review_water_memory_2048_long_3x.json`.
M4/16.4 et 10.5 sont donc clos comme mesure, sans comportement/default nouveau ni 20×10.

**Décision post-clôture du 2026-09-17 : abandon de Lakes.** Le résultat mémoire ne déclenche pas un
patch local supplémentaire : il conduit à ne plus investir dans cette architecture. C57 est fermé
sans calibration. Le successeur C67 repart d'une représentation propre à OpexAI, en découpant la
carte en blocs 5×5 ou 10×10 à typer (eau, côte/mixte, plat, vallonné, montagne) à partir de mesures
agrégées de terrain. Cette représentation doit devenir un socle commun pour l'analyse de carte et
le futur remplacement de la connectivité Lakes. La taille de bloc et les seuils de typage restent
des hypothèses à mesurer, pas de nouveaux defaults.

Le rôle attendu de C67 dépasse l'eau : le corridor de blocs doit fournir un **pré-devis commun**
aux projets pour estimer coût de construction, ROI, opcodes, durée/ticks, difficulté et risque de
faisabilité avant l'A* exact. Il pourra aussi guider le choix du mode, le placement/extensibilité des
infrastructures et un pré-pathfinding hiérarchique. Le type de bloc reste une vue dérivée d'un
vecteur de mesures ; l'architecture distingue une couche physique stable d'une couche dynamique
afin de permettre des invalidations locales.

C67 est explicitement **lazy/opportuniste** : pas de scan complet bloquant au démarrage. Les blocs
sont calculés à la demande lorsqu'un projet traverse une zone inconnue, puis mis en cache. Le
remplissage hors demande ne doit se faire que par petites tranches interruptibles lorsque le
scheduler a du budget d'opcodes inutilisé (notamment pendant des périodes sans projet finançable),
et doit céder immédiatement la priorité à une tâche métier. Une carte partiellement connue est un
état normal ; les consommateurs doivent distinguer « bloc non encore calculé » d'une valeur réelle.

### Clôture M7 / 11.1

La désynchronisation future d'un nom de tâche n'est plus silencieuse. Le fallback de
`scheduler.nut` journalise maintenant `Unknown scheduler task name: <nom>` **avant** de conserver
le comportement historique `enabled=false` puis `return false`. La file de `main.nut`, la
cascade de `scheduler.nut` et les 15 handlers de `scheduler_tasks.nut` sont verrouillés par
`sweeps/test_scheduler_task_contract.py` et le selftest C65.

Validation finale du lot : **13/13** tests ciblés+freeze, selftest C65 **14/15**, `py_compile`
et `git diff --check` OK. Le smoke obligatoire
`results/review_m7_scheduler_smoke_2x3.json` passe **4/4**, horizon complet, sans erreur NoAI et
sans occurrence du fallback inconnu sur les tâches normales. Aucun 5×6/20×10 n'est justifié.

11.2 est déjà corrigé dans le workspace courant par les retours booléens explicites de
`_tryTownGrowth`. 11.3 reste dormant/non exposé : il exige simultanément
`town_growth_skip_noop=1` et un ledger C41/C39 actif. 11.6/11.7 restent clos via B5 et 11.8 est
caduc.

### Reprise du principal résidu actif après M7 : B6 / 06.5

Le 5×6 B6 déjà valide n'a pas été rejoué. Le code courant conserve le mécanisme mesuré :
`OpexBuildProjects` photographie le capital avant les balayages air/eau puis sélectionne avec ce
snapshot. Sur 639 événements, 630 diffèrent du capital vivant et 50 événements contiennent
1 203 bascules d'abordabilité.

La relecture des derniers sites de chantier borne cependant la gravité : air, route, eau et flotte
refont un test de cash vivant ; le rail précontrôle le cash et son builder peut encore répondre
`CASH`. 06.5 est donc un **P2 de classement/admission**, pas une dépense P1 hors budget. La reprise
du 17/09 a ensuite mesuré le sélecteur live exact (41/630 choix changés) puis testé le levier existant
`portfolio_fresh_budget=1` en 5×6 : signal économique négatif, candidat non promu en 20×10 et défaut
conservé à 0.

06.11 est également clos comme **diagnostic P3 sans refresh adopté**. Le Docker 5×6
`results/review_b6_0611_join_resolved_5x6.json` est sain 10/10 : 136/348 tops incrémentaux sont
recyclés ; sur 127 tops fret sondés, 117 sont repricés exactement et 6/114 cas décidables changeraient
d'élection (4 inversions de rang, 2 non-générés). Le refresh concurrent reste rejeté car il perdait
des familles de projets. 06.12 reste dormant avec `rail_prequote=0`.

### Réconciliation complémentaire

- **G3** : la dernière réserve est fermée. Tous les chemins rail A* convergent vers
  `OpexCompleteRailRouteAfterSearch`, qui recalcule `routeDistance` puis
  `OpexLineEconomics(... candidate.kind ...)`; le fret est donc couvert.
- **21.2** : le cœur de `campaign_freeze.py` n'est plus sans test ; le contrat à 230 réglages,
  fusion/rejet des settings, garde de politique, fingerprint et état Git sont couverts. Reste
  seulement l'absence de test unitaire isolé de la copie complète de campagne/bibliothèques.
- **21.3** : fermé par les tests actuels de valeur décroissante sans expansion et d'uptick final.

### Réconciliation 07.2 — itérations rail vs coût observé

Le mécanisme historique subsiste : `OpexLocalStructureChoices` sonde ponts/tunnel sans incrémenter
`state.iterations`. La conséquence actuelle n'est toutefois plus celle décrite par l'ancien
constat : aucun consommateur métier ne relit `result.iterations`/`line.iterations` pour classer le
portefeuille ou calculer le capital. Le compteur vit dans `OR|`, les traces et le champ de ligne.

Le canal H5 qui porte le **coût réellement observé** est `OB|A.result.opcodes`. Les deux
orchestrations de recherche entourent l'appel de recherche d'un `budget.begin/end` ; les sondes de
structure sont donc comprises dans cette mesure. 07.2 reste une limite du proxy d'itérations,
pas un P1 de vérité H5. L'incrémenter modifierait aussi les bornes `iterationBudget/timeSafe` et
donc le comportement du pathfinder : aucun patch `.nut` n'est justifié dans cette passe.
