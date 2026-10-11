# P0 RAIL — exposition de la garde dans les traces existantes

**Audit terminé : les archives ne permettent pas de mesurer la fréquence de
la garde ni de démontrer qu'elle suspend une passe et retarde l'AIR.** Son
[coût VM local](rail_ready_guard_vm_20261011.md) reste établi ; son coût global
et son effet économique restent inconnus. Au défaut courant
`rail_ready_readmission=0`, l'appel est court-circuité : ce surcoût de la
variante ON ne constitue pas un goulot démontré de la production actuelle.
Pas de correctif, refonte du score ou relance de la politique rejetée.

Demande utilisateur « Continue sans me demander ». Analyse uniquement hors
ligne : aucun moteur, Docker, téléchargement, nouveau banc, commit ou push.
Les chantiers parallèles restent préservés.

## Corpus et couverture

Campagne historique `rail_ready_readmission_diag_40x5_20261010_r1`, bundle A2
SHA256 `250223deaebfb849cde5717888fd2b16942de22798c1385158d4a5ad51757ff8` :
80 journaux complets, 4 800 checkpoints mensuels OpexAI et 80 résumés finaux.
Les hashes des 83 entrées et des 107 fichiers du bundle concordent avec
l'autopsie précédente. Le verdict économique `fail_primary` reste inchangé.
La date de fin est le 1er décembre 1974 ; les registres annuels clos C75
disponibles couvrent 1970–1973, pas l'année 1974 complète.

Les deux bras ont effectivement `probe_span_trace=0`, `probe_scheduler=0`,
`probe_portfolio=0`, `probe_loop_ops=0` et `catalog_cost_probe=0`. Le census
des 80 journaux trouve **zéro ligne** SPAN/SPAN_EVENT/SPAN_AGG,
C39_PASS_CLOCK/C41_SLACK_LEDGER/C41_MONTHLY_BUSY, PROJECTS_COST ou
`phase=c75_year/c75_pass`. Ce sont des absences de télémétrie, **pas des
zéros observés de visites ou de suspensions**. De même, l'absence de ligne
RAIL_READY_READMISSION ne prouve pas l'absence de reports : `decision_log=0`.

Dans les 4 800 checkpoints, les champs de visites, état de garde, tick,
reliquat, `c75PassDates` et coût opcode global sont absents. Dans les 80
résumés, les coûts globaux/selection sont explicitement `null`, non zéro.
`exp_opcode_exact=1` ne fournit pas ce dénominateur : son mode de publication
`exp_opcode_exact_check` est OFF, et ses postes locaux ne sont pas la garde.

## Ce que C75 permet effectivement de compter

`C75_MULTI_BUILD=1` active `C75_TRACK_PASSES` (source gelée `settings.nut`
539–549). Chaque entrée `_tryBuildProjects` enregistre une date et incrémente
le registre de passes (`task_projects.nut` 1695–1701). La publication du total
annuel est toutefois désactivée par `probe_portfolio=0` (`probes.nut`
2233–2239). L'entrée précède aussi un retour possible pour régénération C83
(1711–1724), avant l'appel à la garde (1817–1818) : même un total d'entrées
ne serait pas exactement le nombre d'appels à la garde.

Le registre **C75_BYPASS des motifs d'arrêt après construction** est publié.
Ses compteurs sont alimentés lorsque `builtCount > 0` (`task_projects.nut`
1649–1668 ; les autres sites 2165–2167 et 2345–2347 gardent aussi cette
condition). Ils ne couvrent pas les passes vides, infructueuses ou en attente
d'A*, et ne donnent ni leur date précise ni leur reliquat. Les 320 lignes
annuelles sont complètes, uniques, à cinq motifs non négatifs :

| Année close | Passes productives REF | Passes productives ON | Graines dont le compte diffère |
|---|---:|---:|---:|
| 1970 | 420 | 420 | 2/40 |
| 1971 | 1 132 | 1 132 | 20/40 |
| 1972 | 830 | 774 | 24/40 |
| 1973 | 564 | 553 | 34/40 |

En 1970, les différences se compensent : graine 999, 7→6 ; graine 8191,
12→13. L'égalité de la somme ne prouve donc aucune neutralité de trajectoire.
En particulier, 8191 a une passe productive de plus malgré les prévisions
AIR divergentes dès 1970 et sa perte finale historique. Cela ne permet pas
d'expliquer ses pertes par un simple nombre inférieur de passes productives.
Un compte de sorties ne mesure pas le calendrier, les choix OD/avion, les
passes infructueuses ni la fréquence des trois états du microbench.
Les différences 1972–1973 peuvent être des conséquences des trajectoires
divergentes ; aucune attribution causale à la garde n'est possible.

## Persistance et autres traces

`c75PassDates` est sauvegardé/restauré (`persist.nut` 810–813, 869–870,
947–948). Il conserve les dates d'entrée dans une fenêtre glissante de
365 jours au maximum (`probes.nut` 1977–1996 et 2001–2022), et non des ticks,
états de rail ou reliquats. Le résultat de cette campagne indique
`retained_savegames=null` ; aucun `.sav/.sav.gz/.sav.xz` n'est présent dans
son répertoire déclaré. Les checkpoints n'ont pas extrait ce cache.
La persistance implémentée ne rend donc pas les observations récupérables
dans ce corpus, et même un cache récupéré ne suffirait pas à mesurer les
suspensions causées par la garde.

La [sonde indépendante 5×5](rail_ready_measure_20261011.md), bundle distinct,
ne collecte que la frontière de fin de recherche : 17 visites. Elle ne
fournit pas les appels inéligibles absents/en recherche/préparation, ni leur
reliquat. Ses coûts partiels traversant des ticks ne sont pas un dénominateur
CPU pur. Elle ne conserve pas non plus de sauvegardes. Ne pas réunir ces
deux campagnes en une pseudo-comparaison appariée ou extrapoler 17 visites
au fonctionnement annuel de la garde.

## Décision

La formule `15 N_absent + 25 N_search + 40 N_prep` reste une expression
conditionnelle pour les seuls états mesurés. Les trois nombres de visites
sont inconnus ; aucun total n'est calculé. Ni `K_pass`, ni le nombre de
constructions, ni les timestamps muraux des logs, ni OB ne les remplacent.
Un appel consommant quelques opcodes ne prouve pas que la passe réelle
était proche de la limite VM ou qu'un AIR utile a été retardé.

**Clore cette piste comme explication non démontrée sur les archives
disponibles.** Ne pas optimiser en production un appel déjà court-circuité
au défaut, ni réactiver ON pour vérifier a posteriori les graines perdantes.
Conserver C69/C70 et réadmission OFF. Le défaut courant est vérifié dans
`info.nut` 2048–2051 et l'appel dans `task_projects.nut` 1817–1818.

Pour poursuivre ultérieurement ce mécanisme, il faudrait une mesure
non décisionnelle des visites par état et du reliquat avant le contrôle,
séparément du coût de la sonde, avec neutralité de la sonde qualifiée.
La présente analyse n'établit pas le goulot nécessaire pour justifier un
nouveau banc actif, et n'en lance aucun. Elle ne tranche pas les autres
questions de préparation A*, constructibilité ou admission des rails prêts.

[Tableaux, extraits gelés, hashes et vérification](../evidence/review/rail_ready_guard_exposure_20261011/README.md).
Six tests ciblés du décodeur passent ; analyse et contrôle d'intégrité
hors ligne terminés.
