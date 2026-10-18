# V249 — effet des statues, audit du 18 octobre 2026

V249 est conservé sur décision utilisateur. Cet audit ne transforme pas l'échec
de porte A en qualification. Le nouveau mode 3 reste expérimental, défaut 0.
**Le gain annuel causal par statue et la fraction remboursée ne sont pas
identifiables dans les données livrées.** Il manque tout profit de ligne après
achat ; aucun coefficient empirique n'a été inventé pour combler ce manque.

## Entrées et reproduction

Travail sur `v249c`, base `7e593c874725a8bfd4b276c711714de5d67ae038`, arbre initial propre.
Lecture seule des campagnes suivantes, JSON, JSONL et tous les logs moteur :

- `/home/deploy/projects/openttd-ml/results/v249_porteA_40x3_20261018` : 40 paires,
  bras `reference` et `v249`, bundle `b96564b36a3695cf475a8fc24a035534948aa747f45e90310e5ba358d3ef7579`.
- `/home/deploy/projects/wt-v249/results/v249c_smoke_3x3_20261018` : 3 paires,
  bras `reference` et `v249c_mode2`.

Les hashes des 86 logs, des JSON/JSONL et des sources examinées sont conservés dans
[l'inventaire](v249_effet_statue_20261018_inputs.json). Il s'agit d'un inventaire
de provenance, pas d'une copie des preuves brutes ignorées par Git.

Le chemin source annoncé `/home/deploy/.claude/jobs/e230de46/tmp/ottd15/src/station_cmd.cpp`
n'existe pas. `ls` confirme les fichiers sous
`/home/deploy/.claude/jobs/e230de46/tmp/ottd15/src/src/`.
Les numéros ci-dessous sont ceux de ces fichiers ; références officielles :
[station_cmd.cpp 15.3](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/station_cmd.cpp),
[town_cmd.cpp 15.3](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/town_cmd.cpp),
[company_cmd.cpp 15.3](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/company_cmd.cpp).

Commandes d'analyse uniquement, sorties neuves obligatoires :

```bash
python3 sweeps/v249_effect.py /home/deploy/projects/openttd-ml/results/v249_porteA_40x3_20261018 --out /tmp/v249d_A_analyse_neuve.json --statues-csv /tmp/v249d_A_statues_neuves.csv
python3 sweeps/v249_effect.py results/v249c_smoke_3x3_20261018 --out /tmp/v249d_mode2_analyse_neuve.json
```

Les sorties finales produites dans cette session sont
`results/v249d_porteA_final_20261018.json` et `results/v249d_mode2_final_20261018.json`.
Les fichiers sources n'ont pas été modifiés. Le script réutilise le parseur de
champs du lecteur courant `analyse_line_profit_by_mode.py` ; il n'appelle aucun moteur.

## 1. Ce que chaque statue permet de mesurer

Le [tableau des 126 statues](v249_effet_statue_20261018_statues.csv) donne graine,
ville, date, coût, exposition au checkpoint, lignes AIR nominales et profits
annuels disponibles avant l'achat, mêmes villes du bras référence et ensemble
des lignes AIR ne touchant aucune ville à statue dans la variante. Les cellules
inconnues restent `unknown`, jamais zéro. Chaque statue renvoie à sa ligne de log.

Couverture : **124/126** statues ont au moins une ligne AIR avec profit préalable,
**123/126** ont une telle observation dans la même ville du bras référence.
Les liens AIR proviennent d'`AIR_BUILD src_town/dst_town`, sans joindre les IDs de
lignes entre bras. Cette jointure est **nominale et partielle** : elle ne garantit
pas la ville administrative de la gare, qui détermine le bonus. Les tuiles rail,
route et eau ne suffisent pas à retrouver cette ville sans les sauvegardes.
Le tableau ne prétend donc pas donner le total exact de toutes les lignes desservies.

Les logs variante contiennent 341 `LINE_REVENUE` au début de 1971 et 1 335 au
début de 1972 (la passe peut déborder sur février). `task_report.nut:258` utilise `GetProfitLastYear` : ces rapports
mesurent respectivement 1970 et 1971. Les 126 statues sont toutes posées entre
le **13 février et le 27 décembre 1972**. Il y a **zéro rapport de profit de ligne
après achat**, même en cherchant toutes les lignes sans exiger une ville correspondante.
`line_telemetry=null`, `retained_savegames=null`, aucune série de cargo livré
par ligne. Le bénéfice après achat, le différentiel avant/après corrigé des
témoins, le délai de profit et la fraction remboursée sur la vie restante sont
donc **inconnus pour 126/126 statues**. Les contrôles avant achat n'y changent rien.

| Mois 1972 | Fév. | Mars | Avr. | Mai | Juin | Juil. | Août | Sept. | Oct. | Nov. | Déc. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Statues | 1 | 5 | 5 | 8 | 11 | 10 | 19 | 14 | 16 | 19 | 18 |

Les **126 coûts journalisés sont 140 625 £**, pas 187 500 £ : 17 718 750 £ sur
les logs complets. Le coût dépend de `_price[PR_TOWN_ACTION]` et du facteur de
l'action (`town_cmd.cpp:3391`, `3735`) ; 187 500 £ est un autre contexte de prix,
pas le coût réellement payé ici. Le code continue de mesurer le coût par l'API.

Le checkpoint économique terminal est **1972-12-01**, avant les 18 achats de
décembre. Seulement **108 statues**, sur **24 graines**, sont déjà payées à cette
date : **15 187 500 £**, soit **379 687,50 £ par paire** sur 40. Exposition moyenne
117,29 jours, médiane 113 jours. Compter les 126 statues pour expliquer la valeur
au checkpoint surévaluerait le décaissement.

### Pourquoi le résultat total baisse

Porte A conservée : `fail_primary_and_value_guard`, profit annuel moyen
**−32 223,65 £/an**, médiane −26 772 £, 19/21/0, Wilcoxon p=0,37538,
IC95 bootstrap [−104 810,40 ; +39 634,05] £/an ; valeur **−351 178,83 £**, soit
−9,099491 %. Aucun gain économique démontré.

**Le coût immédiat n'entre pas directement dans ce `profit_year`.**
`town_cmd.cpp:3735` débite `EXPENSES_OTHER` ; `company_cmd.cpp:289` débite bien la
caisse, mais `297–303` ne transfère aux dépenses de l'économie trimestrielle que
les running costs, propriétés et intérêts. `EXPENSES_OTHER` en est exclu.
`bench_v2.py:327` calcule le profit sur cette économie, pas sur les dépenses de
trésorerie totales. Réintégrer le coût des statues dans le profit annuel serait faux.

Le décaissement explique en revanche l'ordre de grandeur de la baisse de valeur :
**−351 178,83 + 379 687,50 = +28 508,68 £ par paire**. Cette addition est une
décomposition comptable descriptive, pas le résultat d'un monde sans achats :
elle ne retire ni les changements de projets, de matériel et de service, ni leur
effet sur le cash. La statue n'est pas un actif de transport valorisé ;
`economy.cpp:150–158` ajoute caisse et actifs à la valeur, dette déduite.

Les graines avec statue au checkpoint ont un delta de profit moyen de
−14 733,46 £/an (n=24), celles sans statue −58 458,94 £/an (n=16).
Ce regroupement est sélectionné par la richesse, **sans interprétation causale**.
Il prouve surtout que la dérive des trajectoires ne se limite pas aux achats.
La flotte finale varie de −0,675 véhicule primaire par paire, IC95 bootstrap
[−3,7 ; +2,1] : aucun signal clair d'éviction de flotte. Les 9 refus `cash_stop`
et 16 `cost` n'identifient pas les investissements contrefactuels sacrifiés.
Le mauvais choix de ville, la capacité saturée et l'éviction de projets sont des
hypothèses ; aucune ventilation chiffrée de ces causes n'est identifiable ici.
L'horizon est court pour le retour de caisse, mais n'explique pas à lui seul un
delta de profit opérationnel négatif.

## 2. Hausse de note : +26 de cible, pas +50 causaux

`station_cmd.cpp:4048–4063` combine vitesse, délai de ramassage et attente ;
`4066` ajoute exactement **26** si la compagnie possède une statue dans la ville
de la gare ; `4068–4071` ajoute les termes d'âge du dernier véhicule.
`4077` limite ensuite chaque évolution à **−2..+2**, avec saturation sur un octet.
La statue ne modifie pas directement la note municipale :
`town_cmd.cpp:3535–3541` construit l'objet et pose le bit de statue, sans bonus
de conseil municipal ni modification immédiate de la note de gare.

À service constant et à l'équilibre, prédiction directe :
`delta = min(cible_sans_statue + 26, 255) - cible_sans_statue`.
La note courante n'est qu'un proxy de la cible sans statue ; `min(note+26,255)`
est une approximation stationnaire. Il faut au moins 13 mises à jour pour
absorber 26 points depuis un état équilibré, pas un bond instantané. Le source
ne justifie **aucune constante +40, +48 ou +53** en remplacement de +26.

Smoke, graine 7, valeurs réellement journalisées :

| Ville | Achat et note initiale | Relevés après achat |
|---|---|---|
| 38 | 26/02/1972, 171 | mars 163, avril 181, mai 189, juin 191, juillet 209, octobre 219, décembre 206 |
| 22 | 06/05/1972, **166** | juin 156, juillet 168, août 181, septembre 189, octobre 199, novembre 209, décembre 181 |

156 est déjà une observation **après** achat en ville 22. Ville 38 atteint +18
environ trois mois après achat, puis au plus +48 ; ville 22 atteint au plus +43
par rapport à l'achat et retombe à +15 en décembre. Attente et ramassage passent
des seuils discrets qui peuvent chacun changer de plusieurs dizaines de points.
La composition des gares suivies et l'arrondi de l'API peuvent aussi varier.
Sans leurs témoins contemporains, cette hausse brute n'isole pas l'effet statue.
Elle ne démontre ni amplification garantie, ni délai de gain de profit.

Le captage lui-même dépend de `rating+1` dans le cas isolé
(`station_cmd.cpp:4630–4632`), et des meilleures notes par compagnie et des sommes
de notes en concurrence (`4635–4660`). Le ratio des notes n'est donc pas un
modèle universel du supplément de cargo, encore moins du profit livré.

## 3. Coût des refus d'emprunt

Mode 2 : **94 refus `loan`**, 8 refus `cost`, 4 achats, aucun gain de ligne après
achat disponible. 72 refus loan surviennent en 1970–1971 ; en 1972 : 11 sur la
graine 100, 10 sur 42, 1 sur 7. Ce sont des passages mensuels, pas 94 villes ni
94 occasions indépendantes rentables.

Dans les snapshots précédant les refus, **une seule** observation a une caisse
nette de dette supérieure au coût observé d'une statue : graine 42, refus du
1/11/1972, caisse **507 748 £**, dette **150 000 £**, soit **357 748 £ nets**.
La caisse après provision de dette et statue serait 217 123 £, avant réserve et
projet. La valeur de ces deux derniers à l'instant exact du refus n'est pas
journalisée : même ce cas n'est pas une preuve d'éligibilité complète.
Sur la porte A, la même borne descriptive concerne 46/1 232 refus.
Les snapshots et les appels d'IA ne sont pas synchrones à l'intérieur du jour.

Le nombre de statues refusées qui auraient été rentables et le profit perdu
sont **inconnus**, pas nuls. Le mode 2 retourne avant d'évaluer les villes en cas
de dette ; impossible de reconstruire un portefeuille contrefactuel à partir
du seul `loan=`. Ses quatre gains prédits sont 42 412, 31 015, 17 521 et
25 584 £/an, paybacks théoriques 3,3/4,5/8,0/5,4 ans au coût de 140 625 £.
Ce ne sont pas des remboursements mesurés.

Une condition sans montant fixe plus pertinente que `loan == 0` est :
`cash - loan - coût >= réserve + max(capital_financé des projets listés)` et
aucune passe arrêtée pour caisse depuis le dernier mois. Elle laisse la dette
entièrement provisionnée, n'emprunte rien et n'autorise pas de dépenser le cash
réservé aux projets connus. Elle reste limitée au portefeuille actuellement listé.
Les données ne prouvent pas qu'elle ouvrira beaucoup plus d'achats.

## 4. Mode 3 livré et limites du recalage

`info.nut:655` étend le réglage existant à 3 ; quatre défauts à 0, aucun nouvel
`AddSetting`. `settings.nut:125` conserve l'unique lecture. Dans `task_v249.nut` :

- `20` : vie restante mesurée sur les véhicules des lignes contribuant au gain ;
  conversion en années reprise du mode 2, pas d'horizon fixe ajouté.
- `42` : revenu annuel implicite observé = profit véhicules + running costs,
  méthode de `task_report.nut:240–260`. Le running cost courant approxime l'année
  écoulée ; une flotte récente ne fournit pas une année complète.
- `271` : bonus de cible +26, plafond 255, facteur relatif du mode 3
  `delta/(note+1)`, d'après le cas isolé du source. Le gain estimé multiplie ce
  facteur par le revenu observé, avec la demi-part historique quand les deux
  extrémités chargent. Cette demi-part est une hypothèse de symétrie, pas une mesure.
  Les coûts fixes déjà payés ne doivent pas être réduits proportionnellement au cargo.
- `313` : richesse nette de dette, coût API et remboursement testés
  **pour chaque ville avant classement**. Le meilleur score non remboursable
  ne masque plus un candidat éligible. Recontrôle de caisse avant commande.
- `V249_LINE` : jointure explicite ville/gare/ligne/cargo, note, profit de l'année
  précédente, profit cumulé de l'année courante, revenu, part et gain modèle.
  `V249_CANDIDATE` : coût, dette, caisse, réserve/projet, vie restante et verdicts
  séparés `rich`/`pays`, avec `calibration=unavailable`. Sous `decision_log` seulement.
  Les lignes déjà dans une ville à statue continuent d'être journalisées.

Le modèle suppose du cargo livrable supplémentaire à flotte constante. Il ne
mesure ni capacité libre, ni parts concurrentes par tuile, ni élasticité causale.
**La demande de calibration sur un gain de profit réellement mesuré reste
non satisfaite faute d'observation après traitement.** Le mode 3 fournit un
candidat explicite et instrumenté, pas un réglage économiquement recalé ou adopté.
Aucun nombre de calibration n'a été ajouté. Modes 1/2 conservés ; familles
protégées et Save/Load intouchés. Cadence et suivi transitoires gardent leur
limite historique après rechargement, statues retrouvées par le bit du monde.

### Exposition proposée, non exécutée

Après vérification du runtime et des ressources, diagnostic apparié 3 graines ×
5 ans, horizon choisi pour obtenir au moins des années complètes après les
achats de 1972. Ce n'est ni une porte A ni une porte B. Sur profil VPS :

```bash
python3 sweeps/run_c66_reference.py --campaign v249d_exposition_3x5_neuve --reference 'OpexAI[v249_statue=0,decision_log=1]' --variant 'OpexAI[v249_statue=3,decision_log=1]' --variant-policy-id v249d_mode3 --primary-metric profit_year --decision-rule gain_short --min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 5 --required-seeds 40 --required-years 3 --years 5 --seeds 42 7 100 --repeats 1 --cpus 3 --memory 2g --max-workers 3 --line-telemetry --line-telemetry-monthly --station-supply-telemetry --retain-savegames results/v249d_exposition_3x5_neuve_saves --script-debug
```

Vérifier la jointure ville administrative (références sauvegardées = ID+1),
dédupliquer les trimestres par date réelle et les lignes par bras/graine/identité
physique, conserver les zéros et les disparitions. Comparer les mêmes lignes
avant/après, les villes sans statue et les mêmes villes du bras référence, avec
erreurs regroupées par graine. Ne pas additionner deux fois une ligne touchée
à ses deux extrémités. Le cargo en attente ou chargé à un instant n'est pas du
cargo transporté annuel. Après mesure, pré-enregistrer le recalage puis ses
portes économiques ; ne pas réutiliser ce diagnostic comme qualification.

## Validation

**1 927 tests Python verts (3 ignorés)**, commande
`PYTHONPATH=sweeps python3 -m unittest discover -s sweeps -p "test_*.py"`.
CSV versionné reproduit octet pour octet par la CLI finale : 126 statues uniques,
aucun profit après achat reconstruit. Hashes des 90 entrées de campagne revérifiés.
Contrôles `undecl`, `delim`, `orphans2` : niveau de base conservé
(`AICONFIG_BOOLEAN`, `CONFIG_BOOLEAN`, puis `OpexAirV95CompetitorSecondSlotOpen`,
`OpexRoadTryJoinStop`, `OpexV131KeepStructures`). `git diff --check` vert.
Aucun banc, Docker, moteur OpenTTD ou push ; compilation et exécution Squirrel
non validées, conformément à la restriction utilisateur.
