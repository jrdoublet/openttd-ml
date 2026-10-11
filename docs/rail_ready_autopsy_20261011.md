# Autopsie hors ligne — réadmission RAIL 40×5, 11 octobre 2026

Édition versionnée : les constats de préservation ci-dessous se rapportent à l'analyse, avant la présente publication documentaire autorisée. [Sous-index et limites de couverture](../evidence/review/rail_ready_autopsy_20261011/README.md) ; les références de code renvoient aux extraits numérotés du **bundle historique**, pas au code courant. La [mesure de sonde indépendante](rail_ready_measure_20261011.md) est documentée séparément.


**Décision : conserver le rejet de la variante. L'autopsie ne justifie ni un nouveau score ni une réactivation de la réadmission. Elle établit des divergences AIR précoces, dont certaines précèdent la période où la décision de réadmission peut s'appliquer. L'effet de la politique et celui de son coût d'exécution ne sont pas séparés par cette expérience.**

Le constat principal est plus précis que « le rail prend le capital de l'avion » : sur 8191, la trajectoire diverge pendant l'année réservée à l'AIR ; sur 746035, davantage d'avions et de lignes ferroviaires accompagnent une perte de profit. Le nombre de constructions, le rang interne et le cash ne suffisent pas à expliquer ces résultats.

**1. Périmètre et provenance**

Lecture de la campagne `rail_ready_readmission_diag_40x5_20261010_r1`, archivée dans `results/rail_ready_readmission_A2`. OFF et ON opposent chacun OpexAI au même AAAHogEx gelé, sur les mêmes 40 graines et cinq années 1970–1974. Le manifeste ne déclare qu'une différence effective entre les bras : `rail_ready_readmission=0/1`.

Le hash du bundle a été recalculé avec `fingerprint_tree` du harnais **gelé** : `250223deaebfb849cde5717888fd2b16942de22798c1385158d4a5ad51757ff8`, 107 fichiers. Analyse des 80 journaux moteur et des 4 800 checkpoints mensuels OpexAI ; examen détaillé des trois graines les plus perdantes, choisies avant cette extraction : 746035, 424242, 8191. La sélection de ces cas ne permet pas d'estimer un effet moyen causal.

Le résultat brut demeure `fail_primary` : 40/40 paires complètes, couverture primaire complète, moyenne +29 385,625 £/an, médiane +51 873,5, IC95 bootstrap [−33 434,45 ; +88 655,10], Wilcoxon p=0,053049, gain relatif +1,522 %, inférieur au seuil pré-enregistré de 4 %. La valeur moyenne gagne 1,159 % et tient sa garde. Ni les 28 victoires contre 10 défaites et 2 égalités, ni cette garde ne font passer la porte de gain. L'ancien A2 40×3 rejeté reste également rejeté ; aucune requalification ici.

Les réglages du bundle diffèrent du code courant : notamment `air_c121_physical_payment_days=0` dans les deux bras historiques. Aucune fusion avec la mesure ultérieure de `rail_ready_measure_20261011_r1`, faite sur un autre arbre. Les chiffres ci-dessous caractérisent cette expérience historique.

**2. Les premières divergences observables**

Les événements `C121_BUILD` n'ont pas de date de jeu propre. Leurs dates sont encadrées par les événements **de la compagnie 0**, `OPEX yyyy-m-d` ou `C121_GE date=...`, immédiatement antérieurs et suivants. Les horodatages de l'ordinateur sont exclus. Une borne n'est pas une date exacte de décision ou d'entrée en revenu.

| Graine | Premier checkpoint cash différent | Premier checkpoint physique AIR différent | Première prévision/identité de construction AIR différente |
|---|---|---|---|
| 8191 | 01/07/1970 : 50 371 → 50 390 £ | 01/10/1970 : 10 → 11 avions ; 8 → 10 aéroports | 5e construction : même OD et avion, prévision différente en juillet–août 1970 ; 7e construction : OD différente en septembre–novembre 1970 |
| 424242 | 01/03/1971 : 57 657 → 52 285 £ | 01/04/1971 : 19 → 18 avions ; 24 → 22 aéroports | 12e construction : OD différente entre mars et avril 1971 |
| 746035 | 01/10/1971 : 64 861 → 64 860 £ | 01/12/1971 : 36 → 35 aéroports ; avions différents en janvier 1972 | 32e construction : OD différente entre septembre et octobre 1971 |

Flèches : OFF → ON. Un écart de 1 £ est un signal de divergence, pas un effet économiquement substantiel. Le premier profit annuel différent est observé le 01/08/1970 sur 8191 (+19 £, seulement des trimestres partiels), le 01/05/1971 sur 424242 (−2 413 £, quatre trimestres), le 01/11/1971 sur 746035 (−1 £, quatre trimestres). Sur 8191, le premier checkpoint différent avec quatre trimestres valides est le 01/02/1971 (+12 585 £). Les divergences initiales ne sont donc pas toutes des pertes.

Avant même ces constructions, le premier texte OpexAI différent dans les journaux est une clôture de portefeuille incrémental :

- **8191, ligne 1488 des deux logs**, encadrée par le 24 mai et le 20 juin 1970 : `candidates=78/79`, `od=78/79`, `selected=0/0`, `remaining=31555/31485`.
- **424242, ligne 2242**, entre le 26 janvier et le 13 février 1971 : même nombre de candidats et projets, `remaining=79934/79890`.
- **746035, ligne 3838**, entre le 21 septembre et le 4/5 octobre 1971 : mêmes candidats et projets, `remaining=13799/14020`.

Attention : `remaining` représente le **capital non affecté**, calculé par `capitalBudget - selectedCap`, et non le reliquat opcode. Source gelée : [projects_update.nut:237](../evidence/review/rail_ready_autopsy_20261011/source_excerpts.json) et journal à la ligne 257. Ces traces montrent un état différent, sans identifier à elles seules l'instruction responsable.

Les premières constructions différentes apportent trois précisions :

- **8191** : ligne 1528 des deux logs, 5e événement, OD 29–41, moteur 223, un avion, capital 38 964 £ identiques. `decision_profit` passe de 138 332 à 135 704 £/an et `decision_kdec` de 29 236 à 29 390 £. Bornes OFF : 07/07–07/08/1970 ; ON : 08/07–04/08. Il s'agit de prévisions, pas de profits réalisés. La première OD différente arrive au 7e événement : OFF 17–0, ON 33–43. OFF construit également 33–43 au 8e événement, entre le 17 novembre et le 7 décembre ; 17–0 n'apparaît dans aucun `C121_BUILD` ON de cette campagne.
- **424242** : OFF ligne 2444, 12e événement, 36–41 ; ON ligne 2481, 13–9. Même moteur 223, un avion, capital 71 364 £. Prévisions respectives 116 012 et 52 652 £/an. OFF est encadré par le 13 mars–12 avril 1971, ON par le 20 mars–10 avril. L'OD 36–41 finit par être construite ON, au 41e événement, entre le 27 octobre et le 8 novembre **1972**. L'OD 13–9 n'apparaît dans aucun événement OFF. La différence combine changement de marché et retard, pas seulement suppression définitive.
- **746035** : OFF ligne 3870, 32e événement, 24–13 ; ON ligne 3853, 24–8. Moteur 223, un avion, capital 38 964 £ ; prévisions 66 200 et 48 128 £/an. Bornes OFF 04/10–11/10/1971, ON 21/09–05/10. ON construit aussi 24–13 au **33e** événement, entre le 5 et le 10 octobre. Le premier désaccord d'ordre ne prouve donc pas que ce marché a été sacrifié. 24–8 n'apparaît pas dans les événements OFF.

Après la rupture du préfixe commun, le même ordinal n'identifie plus le même projet. Les comparaisons de marchés utilisent les villes, jamais les IDs locaux de lignes ou gares.

**3. Ce qui est établi avant 1971**

Sur l'ensemble des 40 paires, six ont une première divergence des champs AIR économiques étudiés dont **les deux bornes supérieures sont en 1970** : 999, 73, 8191, 123456, 232037, 59527. Quatre ont déjà un nombre d'avions et d'aéroports différent à un checkpoint de 1970 : 999, 73, 8191, 59527. Sept ont un checkpoint de cash différent en 1970, les six précédentes plus 723002. Aucun checkpoint ne présente de divergence OR ferroviaire en 1970. Ce sont des fréquences descriptives ; aucun tri par performance ni test causal supplémentaire.

Dans le bundle testé, `c121_catalog_air_first_year=1` et `c121_air_first_year_rail_prep=1`. L'année initiale est recalculée avant construction du portefeuille : [task_projects.nut:2548](../evidence/review/rail_ready_autopsy_20261011/source_excerpts.json) et [scheduler_tasks.nut:234](../evidence/review/rail_ready_autopsy_20261011/source_excerpts.json). Le portefeuille exclut alors fret, PAX ferroviaire, route et eau : [projects.nut:176](../evidence/review/rail_ready_autopsy_20261011/source_excerpts.json).

Les recherches préparatoires démarrent via le stock et portent `isC121RailPrep=true` : [rail_prep_c121.nut:262](../evidence/review/rail_ready_autopsy_20261011/source_excerpts.json). Au début de passe, leur fin va au stock : lignes 146–157. Le contrôle de réadmission exclut explicitement ces états : [task_projects.nut:1562](../evidence/review/rail_ready_autopsy_20261011/source_excerpts.json). C80 worker/gate et V88 goods chain sont tous désactivés dans les deux bras.

En revanche, ON appelle `_railReadyReadmissionShouldDefer` à **chaque passe projects**, même quand les gardes retournent faux ; OFF court-circuite cet appel : [task_projects.nut:1817](../evidence/review/rail_ready_autopsy_20261011/source_excerpts.json). La recherche exhaustive du symbole ne trouve aucun autre consommateur comportemental dans le bundle.

**Interprétation :** sous ces chemins et réglages, les divergences de 1970 ne s'expliquent pas par un RAIL primaire prêt volontairement déféré. Un coût d'exécution supplémentaire peut décaler une tranche, un événement, le rafraîchissement du catalogue ou le profit constaté. Cette chaîne est compatible avec les observations, mais ni son coût VM ni le tick déclencheur ne sont mesurés. L'absence de sauvegardes et de traces de visites interdit de vérifier chaque état intermédiaire. Il ne faut pas transformer cette lecture statique en preuve expérimentale que quelques opcodes expliquent les pertes finales.

L'A/B garde sa valeur pour l'effet total du réglage livré. Ce réglage inclut son contrôle et sa cadence : l'expérience ne les isole pas de la décision économique souhaitée. Ce n'est pas un motif pour annuler le rejet ou sélectionner les graines qui conviennent.

**4. Où se matérialisent les pertes finales**

Snapshots du 1er décembre 1974. Les profits modaux ci-dessous sont la somme de `profit_this_year_gbp` des véhicules affectés aux lignes ; ce n'est pas le `profit_year` de la compagnie, ni une année complète depuis la mise en service de chaque ligne. Les coûts d'infrastructure et autres postes empêchent une décomposition comptable exacte du profit compagnie par cette télémétrie.

| Graine | Δ profit annuel compagnie | Δ profit des avions | Avions OFF/ON | Lignes AIR OFF/ON | Lignes RAIL OFF/ON | Δ profit des trains |
|---|---:|---:|---:|---:|---:|---:|
| 746035 | −525 183 £ | −447 633 £ | 124 / 128 | 57 / 57 | 4 / 6 | −18 357 £ |
| 424242 | −481 430 £ | −474 277 £ | 109 / 96 | 55 / 51 | 7 / 5 | −65 145 £ |
| 8191 | −372 964 £ | −310 831 £ | 101 / 72 | 53 / 42 | 2 / 2 | −12 650 £ |

La perte AIR est le principal déficit modal observé dans les trois cas. Elle ne se résume pas partout à un manque de flotte : 746035 termine avec quatre avions supplémentaires et autant de lignes AIR. Ses deux lignes RAIL supplémentaires ne rapportent pas davantage dans cette capture. Aucun de ces constats n'établit quelle décision initiale a causé les performances ultérieures.

Décomposition AIR par ensemble des marchés, en livres arrondies :

| Graine | Marchés communs / OFF seulement / ON seulement | Δ profit des marchés communs | Profit des marchés OFF seulement | Profit des marchés ON seulement |
|---|---:|---:|---:|---:|
| 746035 | 43 / 14 / 14 | −327 714 | 381 768 | 261 849 |
| 424242 | 24 / 31 / 27 | −343 222 | 868 366 | 737 311 |
| 8191 | 18 / 35 / 24 | +37 279 | 784 280 | 436 170 |

L'identité vérifiée est : delta AIR = delta commun − profit OFF seulement + profit ON seulement. Les marchés « OFF seulement » ne sont pas tous des opportunités accessibles à ON au même instant ; leur profit mature n'est pas la valeur marginale d'une décision passée. Sur 8191, les marchés communs gagnent légèrement tandis que le remplacement de marchés explique le déficit descriptif. Sur les deux autres graines, les marchés communs perdent aussi. Congestion, fréquentation, renforcement, rating et concurrence demeurent des explications possibles, pas une causalité départagée.

**5. Rail : résultats disponibles et limites de la réadmission testée**

Les premières tentatives ferroviaires conservées de 1971 ont les mêmes OR dans les deux bras :

- 746035 : budgets 8 000, recherches 161 et 30 itérations, résultats OK ; première présence en février puis mars.
- 424242 : budgets 7 000 / 7 000 / 10 000, recherches 53 / 955 / 99, résultats OK ; première présence en février.
- 8191 : budgets 7 000 / 7 000, recherches 5 571 / 49, résultats OK ; première présence en février.

Les OR ne divergent dans les checkpoints qu'en juillet 1974 sur 8191, janvier 1973 sur 424242 et novembre 1973 sur 746035. Ils ne contiennent pas toutes les visites de réadmission ; leur identité n'établit pas une cadence identique. Leurs dates mensuelles sont des dates de **première observation**, pas des dates exactes d'A* ou de construction. Les panneaux ne conservent qu'une partie des événements historiques ; les nombres d'itérations ne sont jamais assimilés à des opcodes.

Les OB divergent plus tôt sur certaines tentatives : par exemple 587 077 → 596 893 sur la troisième tentative 424242, et 651 725 → 651 707 sur la seconde 8191. Ce sont des compteurs de chantier : le résultat commence avec les opcodes du plan, puis ajoute stations, voie et trains ([builder_rail.nut:2162](../evidence/review/rail_ready_autopsy_20261011/source_excerpts.json), lignes 2301, 2379, 2463). Ils ne mesurent ni le coût du helper ni la charge globale, et la mesure traversant des ticks peut inclure l'attente. Aucun verdict opcode global n'en découle.

La lecture du helper testé révèle trois limites techniques, sans prouver leur exposition dans ces trois parties :

1. `phase == build` n'implique pas `railPlan.ok`. Une recherche échouée passe aussi à cette phase : [task_rail.nut:1633](../evidence/review/rail_ready_autopsy_20261011/source_excerpts.json). Son nettoyage peut donc être déféré, alors que le consommateur reconnaît les plans invalides avant le contrôle de cash, lignes 1671–1677.
2. Le helper inspecte la tête du portefeuille, son profit positif et son financement, puis le rang du RAIL. Il ne prouve pas que la tête sera constructible et ne refait pas une comparaison économique fraîche entre deux projets prêts. Les rangs portent sur `best`, pas sur tout le vivier ni sur TOP20 RAIL local.
3. La protection contre les reports mémorise la dernière tête, pas un nombre total de reports par recherche. Une succession de têtes différentes peut donc prolonger l'attente ; C77 peut partager un report. Sans traces, impossible d'en mesurer la fréquence ou le dommage ici.

`decision_log=0`, `rail_ready_admission_shadow=0` et `probe_span_trace=0` dans cette campagne. Les six journaux prioritaires ne contiennent aucun événement `RAIL_READY_READMISSION` ou `RAIL_READY_ADMISSION`. Il est donc impossible de désigner « le RAIL déféré qui a provoqué le premier changement AIR », de prouver que la tête concurrente a réellement été construite, ou de quantifier un blocage par plan invalide. La sonde ultérieure a montré des consommations RAIL hors arbitrage normal, mais ses visites et ses coûts ne peuvent pas être transférés à ce bundle.

**6. Verdict et suivi de la mesure prioritaire**

| Composant | Verdict | Motif |
|---|---|---|
| Score financier C69/C70 | Conserver | Cette autopsie ne démontre pas un défaut du score commun. |
| Réadmission ON historique | Maintenir rejet | Porte de gain échouée ; effets temporels et décisions non séparés ; limites techniques non qualifiées. |
| Précalcul C121 | Conserver son statut courant | Faisabilité existante, mais aucun gain économique supplémentaire attribuable ici. |
| Assimilation `build` à un tracé prêt valide | Rejeter dans tout futur diagnostic | Le code gelé place aussi les plans échoués dans cette phase. |
| Attribution des pertes à « trop de rail » | Rejeter | 8191 diverge avant la décision étudiée ; résultats modaux et quantités ne soutiennent pas cette explication universelle. |
| Hypothèse d'un effet du contrôle même inéligible | Premier maillon mesuré, transmission non démontrée | Surcoût local ON−OFF de 15/25/40 ops par appel ; fréquence et suspension non récupérables dans les archives. Aucun effet AIR attribué. |

La proposition initiale ci-dessous a été réalisée : [microbench VM des retours faux](rail_ready_guard_vm_20261011.md), puis [audit hors ligne de fréquence/suspension](rail_ready_guard_exposure_20261011.md). Le coût local est établi, mais les archives ne permettent pas de démontrer sa transmission à la cadence ou au profit. Cette piste est close comme explication non démontrée sur ces archives ; aucun correctif de production ou nouveau banc actif n'en découle. Le protocole initial est conservé ci-dessous pour provenance.

Hypothèse falsifiable : l'enveloppe ON consomme davantage d'opcodes que le court-circuit OFF alors qu'aucune décision de report n'est possible ; ce coût devient assez fréquent pour pouvoir déplacer une tranche de scheduler. Mesurer séparément état absent, recherche en cours et préparation C121 terminée, avec exactement les gardes du bundle et des fixtures figées. Les trois cas doivent retourner faux et ne modifier aucun état. Même budget d'entrée, même tick, même nombre d'appels dans chaque paire ; soustraire une enveloppe vide commune, publier aussi les valeurs brutes et rejeter les échantillons traversant un tick. L'adaptation partirait du harnais microbench existant, sans installation ou nouveau lanceur moteur improvisé.

Critère de cette seule mesure : un surcoût stable mesuré soutient le premier maillon de l'hypothèse ; un coût nul ou non résolu l'affaiblit. Elle **ne prouve pas** une perte AIR, une famine CPU ou un gain à supprimer le contrôle. Le nombre de visites et la marge scheduler historiques sont absents : toute estimation de déplacement de tranche doit garder ces variables inconnues. Aucun seuil arbitraire de score, quota worker ou adoption économique ne peut en sortir. Une future expérience active nécessiterait d'abord ces données d'exposition et une sonde dont la neutralité économique et opcode serait évaluée avec marges fixées avant lancement. Elle n'est ni préparée ni lancée dans ce mandat.

**7. Fichiers livrés et vérification**

- [analysis.json](../evidence/review/rail_ready_autopsy_20261011/autopsy/analysis.json.gz) : verdict brut, réglages, premiers écarts sur les 40 graines et données détaillées des trois cas.
- [monthly.csv](../evidence/review/rail_ready_autopsy_20261011/autopsy/monthly.csv.gz) : 180 checkpoints appariés, couverture annuelle conservée.
- [air_builds.csv](../evidence/review/rail_ready_autopsy_20261011/autopsy/air_builds.csv.gz) et [first_log_differences.json](../evidence/review/rail_ready_autopsy_20261011/autopsy/first_log_differences.json.gz) : événements, lignes exactes, bornes de dates et réapparition des premières OD dans l'autre bras.
- [annual_modes.csv](../evidence/review/rail_ready_autopsy_20261011/autopsy/annual_modes.csv.gz), [rail_retained_signs.csv](../evidence/review/rail_ready_autopsy_20261011/autopsy/rail_retained_signs.csv.gz) et [all_seeds_first_month.csv](../evidence/review/rail_ready_autopsy_20261011/autopsy/all_seeds_first_month.csv.gz).
- [analyse.py](../evidence/review/rail_ready_autopsy_20261011/autopsy/analyse.py.gz), `complete.py`, `test_analysis.py` : extraction reproductible, complément, cinq vérifications Python réussies. L'extraction refuse un dossier déjà analysé ; choisir un dossier neuf pour la reproduire. Les premières exécutions de préparation ont révélé un arrondi flottant dans l'identité de décomposition ; correction de la tolérance numérique à 10⁻⁶ £, sans modification des données ou de l'économie.

Contrôle final : 1 742 fichiers suivis ou non ignorés, statut Git et HEAD identiques ; 83 fichiers historiques bruts inchangés ; 107 fichiers du bundle inchangés. Aucun moteur, Docker, changement de production, défaut, branche, commit ou push. Seuls ces artefacts neufs dans un dossier `results/` ignoré ont été créés. Les preuves de préservation sont dans `inputs_before.json`, `production_before.json` et `final_verification.json`.
