# AIR — BFAIL, liquidité et contrefactuel conserver/démolir A (09/10/2026)

## Point de décision et deux hypothèses distinctes

Lorsque B échoue après la construction d'un nouvel aéroport A, le chantier a
déjà dépensé `cost_a` et souvent des frais `cost_b`. Si la maintenance des
infrastructures vaut zéro, la politique actuelle garde A sans service. Il est
redécouvert par les générations de hubs, et une liaison ultérieure ne repaie
pas sa construction. Le coût passé n'est ni une recette de liquidation ni un
capital remboursé. La maintenance de ce hub inutilisé est nulle dans les
parties étudiées. Le coût de destruction est mesuré dans le diagnostic ci-dessous.

Deux contrefactuels économiquement différents :

1. **Décision après BFAIL** : conservation de A ou envoi de ce seul A neuf
   vers `OpexAirRollback` (R19), et observation du réseau ultérieur. Les dépenses
   initiales identiques restent engagées dans les deux bras, les frais de
   démolition éventuels et les réemplois futurs peuvent différer.
2. **Décision avant chantier** : empêcher une dépense inutile de A si B ne peut
   pas être construit. Un preflight peut échouer à simuler terrassement et
   autorité municipale ; cette hypothèse exige sa propre preuve et une
   variante différente. Ne pas additionner `cost_a` comme si une démolition
   après BFAIL le reversait en caisse.

## Pression financière observable sans refaire de parties

Analyseur : `sweeps/analyse_air_orphan_opportunity.py`, tests synthétiques
`sweeps/test_analyse_air_orphan_opportunity.py`. Il réapparie chaque
`AIR_ORPHAN_RETAIN` à son `AIR_FINANCE_TRY outcome=failed reason=BFAIL`
du même log, même coût et date, puis à la première sélection de portefeuille
observée dans les sept jours. Si une construction réussie intervient avant
la sélection, la comparaison est censurée. `AIR_FINANCE_SELECT.budget` est un
budget de sélection, pas le solde bancaire ; `blk_finance` porte uniquement
sur le meilleur projet bloqué **par la marge**, sans identité de projet ni
preuve de constructibilité. Le test `deficit <= cost_a` est une sensibilité
arithmétique statique à **l'évitement hypothétique de la dépense de A** ;
le budget réel aurait évolué autrement. Un classement plusieurs jours plus
tard n'est jamais traité comme un état invariant au moment de l'échec.

Archives analysées, sans simulation nouvelle :

| Source | Orphelins | Après BFAIL, première sélection ≤ 7 jours avant autre chantier | Même jour | Cas de déficit couvert dans la sélection même jour | Croisements arithmétiques ultérieurs (5–7 jours) |
|---|---:|---:|---:|---:|---:|
| `air_orphan_profit_6x3_20261009_r2` | 8 | 5 | 1 | **0** | 3 |
| `air_orphan_profit_maturity_3x5_20261009_r1` (cohorte sélectionnée) | 7 | 4 | 1 | **0** | 2 |

Sur la première source, un cas voit un autre projet construit avant le
nouveau classement et deux n'ont pas de classement dans la fenêtre : aucune
valeur zéro n'est fabriquée. Quatre des cinq sélections appariées ont un
projet AIR bloqué par la marge ; **trois** ont un déficit numériquement
inférieur au coût historique de A, mais à J+5, J+6 ou J+7. Les campagnes
partagent des graines et ne constituent pas quinze événements indépendants.

Sorties : `results/air_orphan_opportunity_6x3_20261009_r1.json`,
`results/air_orphan_opportunity_maturity_3x5_20261009_r1.json`.
Ce calcul ne prouve aucune opportunité perdue, ne couvre pas les projets
bloqués par le capital (dont le montant individuel manque), et ne garantit
ni le même portefeuille, ni la même date de sélection après un autre chantier.

## Expérience de démolition : protocole pré-enregistré

**Nature :** expérience économique comportementale *diagnostique*, aucun
réglage à adopter sur ce petit échantillon. HEAD de départ `cb23a17` sur
`master`, arbre partagé dirty ; le gel du lanceur fera foi de la source
réellement exécutée. Même code pour les bras, réglages communs
`air_site_cost_quote=1`, `air_site_quote_keep_legacy_margin=1`,
`probe_air_finance_margin=1`, et uniquement
`air_bfail_dispose_orphan=0` (référence, conservation historique) contre
`=1` (variante expérimentale). Ce nouveau réglage est **0 sur les quatre
difficultés**. La variante cible `airportB == null && !reuseA && !reuseB`
avec maintenance des infrastructures inactive et appelle exactement le
rollback R19 déjà utilisé lorsque la maintenance est active ; aucun hub
préexistant ne va dans le ticket.

**Ordre du diagnostic fixé avant mesure :** contrats Squirrel, smoke causal
`seed=5678` sur un an (BFAIL connu dès janvier), puis, sous réserve d'un
smoke sain et de l'exposition effective, `3 graines × 5 ans` appariées sur
`1234,5678,2026` déjà exposées et prolongées. Ne pas présenter ces trois
graines sélectionnées comme une porte V102 ni tirer une conclusion d'adoption.
Une seule campagne moteur à la fois ; profil local 10 CPU, 8 Go, 10 workers,
gel source/manifeste contrôlé, nouveaux identifiants de campagnes.

**Mesures à relever** : même première trajectoire jusqu'à la première
liquidation ; succès et durée des tickets R19 et coût signé net (ne pas
déduire des tickets ouverts un coût final) ; survie et réemploi physique des
aéroports, constructions AIR, slots, nombre d'avions, dates d'investissement,
`profit_year` et `company_value` OpexAI par graine à décembre 1974,
comparaison avec AAAHogEx uniquement comme contexte. Rejeter le duel comme
preuve causale si le premier écart précède le mécanisme visé ou si les bras
ne proviennent pas du même gel.

L'analyse observationnelle antérieure reste valide : cinq premiers réemplois
de huit A sur 6×3, puis sept réemplois de sept A sur les trois graines 3×5,
dont six groupes financiers appariés (+421 313 £ seulement sur 148 périodes
complètes). Ces profits historiques ne sont pas transférables à la variante.

## État de qualification

La qualification comportementale d'une politique par défaut exige les
portes V102 A40×3 puis B20×10 sur les graines canoniques, les mêmes critères
et l'exposition suffisante. Ce diagnostic ciblé ne vaut ni adoption ni
choix de seuil. Aucun commit ou push sans demande explicite.

## Résultats moteur du contrefactuel pré-enregistré

**Smoke** `air_bfail_dispose_smoke_5678x1_20261009_r1` : **2/2 parties
complètes**, exit 0. Les **370 premières lignes des logs** des deux bras
sont identiques après normalisation de l'horodatage de collecte. Leur
première divergence correspond au BFAIL du 15/01/1970 : conservation de A
avec `actual=28396` contre `AIR_RECOVERY_CREATE` suivi de rollback
immédiatement terminé et `actual=29188`. Détruire A coûte **792 £ en plus**
sur cet événement, sans récupérer les frais de construction de A. À un an,
le delta variante−référence vaut **−49 049 £/an** de `profit_year` et
**−0,713 %** de valeur Opex : smoke technique, pas preuve économique.

**Diagnostic** `air_bfail_dispose_diag_3x5_20261009_r1` : **6/6 parties
complètes et saines**, code 0, 3 graines exposées (1234/5678/2026),
5 ans, source des deux bras identique. Bundle SHA256
`04b40393c8bdb22448a9aa3dcf82a2af93584fcd7b4ac765b5680f06abc69a2e` ;
manifest SHA256
`51305fc3aa08dbf7f25297a824d7922441e94fab94018e92959e2c35d1f64067` ;
OpenTTD 15.3, image `openttd-lab:latest` SHA256
`f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
Le SHA du bundle est aussi celui du smoke. Git de départ
`cb23a172fa6f7b79e50d0392e526a061c130259b`, arbre dirty préservé.
La règle `gain_short` et ses seuils V102 ont été inscrits au manifeste
uniquement comme contrat du harnais ; l'étude **3×5 ne prétend pas passer
le seuil de 40 graines ×3 ans** : verdict brut `diagnostic_only`.

La première divergence de log dans chaque graine est précisément le
remplacement de `AIR_ORPHAN_RETAIN` (référence) par `AIR_RECOVERY_CREATE`
(variante) : les préfixes égaux font **2 744 lignes pour 1234**, **370 pour
5678**, **1 905 pour 2026**. Le rollback R19 se termine aussitôt dans les
trois cas, `AIR_RECOVERY_COMPLETE deferred_net=0 immediate=1`.

| Seed | Premier BFAIL | Station/ancre | Dépense conservée | Dépense avec liquidation | Delta frais R19 |
|---|---|---|---:|---:|---:|
| 1234 | 1971-05-19 | 34 / 8166 | 19 136 £ | 19 928 £ | +792 £ |
| 5678 | 1970-01-15 | 2 / 38488 | 28 396 £ | 29 188 £ | +792 £ |
| 2026 | 1970-10-05 | 17 / 36881 | 18 940 £ | 19 732 £ | +792 £ |

Les trois A coûtent historiquement **60 643 £**, déjà dépensés dans les deux
bras ; la politique de démolition y ajoute **2 376 £**, sans restitution des
60 643 £. Le coût immédiat de R19 est déjà inclus dans `AIR_FINANCE_TRY.actual`,
et apparaît dans le résidu `c_planes=792`, sans achat d'avion. Les événements
de chantier ultérieurs divergent avec les trajectoires et ne constituent
pas automatiquement des paires de BFAIL comparables.

**Delta terminal 1974** : Opex variante démolition moins Opex référence
conservation sur la même graine et la même source figée.

| Seed | Delta `profit_year` | Delta `company_value` | Delta slots AIR Opex |
|---|---:|---:|---:|
| 1234 | **+293 683 £/an** | −36 463 £ | +3 |
| 5678 | **−380 374 £/an** | −360 233 £ | −1 |
| 2026 | **+134 140 £/an** | +459 155 £ | +1 |

Moyenne **+15 816 £/an**, médiane **+134 140**, 2 victoires / 1 défaite,
IC95 bootstrap **[−380 374 ; +293 683] £/an**, Wilcoxon exact bilatéral
**p=1**, ratio des moyennes de valeur **+0,3924 %**. Les trois paires sont
complètes et les métriques couvertes. Les graines sont délibérément
sélectionnées pour l'exposition, et la forte hétérogénéité ne soutient
aucune adoption. Les profits incluent l'ensemble des décisions ultérieures
sur la carte, y compris les effets de concurrence ; ils ne donnent pas une
valeur indépendante à chaque A.

Artefacts principaux : `results/air_bfail_dispose_smoke_5678x1_20261009_r1.json`,
`results/air_bfail_dispose_diag_3x5_20261009_r1.json`,
`results/air_bfail_dispose_diag_3x5_20261009_r1.manifest.json`,
`results/air_bfail_dispose_diag_3x5_20261009_r1_engine/`,
`results/air_bfail_dispose_diag_3x5_20261009_r1_savegames/`,
`results/air_bfail_dispose_diag_3x5_20261009_r1_recovery.json`.

**Verdict causal borné :** la démolition d'A a bien été exercée et coûte
792 £ lors des trois premiers échecs ciblés ; son effet économique global
reste mixte et incertain. Garder le réglage expérimental
`air_bfail_dispose_orphan=0` aux quatre difficultés, sans déclencher de
porte V102. Le contrefactuel différent **éviter la construction de A
avant le risque BFAIL** mérite d'être étudié au point du préflight,
avec preuve de faisabilité réelle de B et projet de remplacement finançable.
