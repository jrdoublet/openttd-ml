# C121 : rendre la cible de flotte contraignante — 07/10

Mise a jour apres commit utilisateur `36fa8c7` : C121 corrige est maintenant
adopte (economie/catalogue1/1). Le garde dernier marginal de ce commit etait
deja present localement dans les deux bras de nos A40x3 et 40x6 ; verification
du snapshot dans `frozen_root`. Ces comparaisons mesurent uniquement le
plafond additionnel, pas le garde marginal et pas C121 corrige contre C115.
La qualification `c121_last_marginal_guard_A/B_20261007` compare au contraire
C1150/0 au profil C121 corrige1/1 : A40x3 pass et B20x10 pass confirmes dans
les JSON/manifeste. Les anciens etats de defaut0/0 de cette fiche sont
historiques ; `c121_air_target_limit` reste0. Aucun resultat ancien ne change.

## Extension 40 x 6 ans demandee par l'utilisateur

Apres le resultat 40x3, demande explicite : « Fais un 40x6 ».
Nouvelle comparaison pre-enregistree avant lancement, sans remplacer le verdict
historique a trois ans : `c121_target_limit_40x6_20261007`, 40 graines canoniques,
6 ans, une repetition, 80 duels distincts (480 annees-parties). Meme arbre fige
et memes bras cible0->1 que A r2 ; bundle attendu
`cc25b98a1e841b451df376add995e137334ed051ba34c4e93a942855983c0989`.
Metrique primaire : `profit_year` Opex variante moins reference a six ans.
Regle `gain_short`, `required-seeds=40`, `required-years=6`, seuil relatif 4 %,
Wilcoxon bilateral p<0,05, borne basse IC95 bootstrap moyenne >0, garde de
valeur 5 %. Bootstrap 20 000, graine 0. Autres defauts du snapshot communs,
sondes decision OFF ; exposition et smoke r2 precedents sur le meme code.
Cette extension est autorisee apres lecture du resultat a trois ans ; elle
reste un nouvel horizon choisi ensuite, sans effacer A40x3 ni garantir un gain.
Contexte `desktop-linux`, image/cache verifies identiques, aucun conteneur actif
avant lancement, profil local 10 CPU/8g RAM+swap/10 workers, montage `/work`.
Sortie neuve `results/c121_target_limit/A40x6/bench.json`, etat
`results/c121_target_limit/state_40x6.json`, lanceur `run_40x6.py`.
Defaut candidat 0, aucun commit/push. Perimetre autorise ici : 40x6 seulement ;
aucune porte B automatique ni adoption sur le seul resultat de cette extension.

### Resultat 40x6 et decision

Campagne terminee : **40/40 paires, 80/80 duels sains et complets**,
`comparison_complete=true`, `adoption_sample_complete=true`,
`metric_coverage_complete=true`, horizon et quatre trimestres valides par
profit terminal couverts. Regle verifiee `gain_short`, required-years=6,
required-pairs=40 ; meme ensemble de graines et bundle que A r2.
Verdict brut **fail_primary** :

- profit reference moyen terminal : 1 763 464,825 £/an ; candidat :
  1 762 818,525 £/an ; seuil utile 4 % = 70 538,593 £/an ;
- delta moyen **-646,3 £/an (-0,036649 %)**, mediane **-65 230,5 £/an** ;
- V/D/E **16/24/0**, Wilcoxon exact bilateral **p=0,9100459609** ;
- IC95 bootstrap moyenne **[-55 455,25 ; +57 013,975] £/an**,
  20 000 reechantillonnages, graine 0 ;
- valeur, ratio des moyennes : **-1,394152 %**, 40 denominateurs positifs,
  garde de perte maximale 5 % tenue.

Le seuil, la significativite et la borne basse positive echouent. Le delta
moyen presque nul ne demontre ni equivalence ni neutralite. Aucun gain
retarde n'est demontre a six ans ; aucune perte significative n'est non plus
etablie. **Candidat toujours OFF, B non lancee, aucun commit/push.**
Le resultat historique a trois ans reste conserve avec son protocole initial.

Trajectoire annuelle descriptive du nouveau 40x6 (40 paires a chaque annee,
annee 1 avec seulement les trimestres disponibles, hors critere terminal) :

| Annee simulee | Delta moyen profit annuel (£/an) | Delta relatif |
|---:|---:|---:|
| 1 | +1 430,800 | +0,388 % |
| 2 | -20 426,800 | -1,524 % |
| 3 | -21 309,400 | -1,182 % |
| 4 | -33 523,575 | -1,984 % |
| 5 | -27 633,175 | -1,665 % |
| 6 | -646,300 | -0,037 % |

Ces points ne sont pas des observations independantes ni des horizons
alternatifs d'adoption. Les deltas par graine et valeurs des deux bras sont
conserves dans `results/c121_target_limit/receipt_40x6.json` ; resultat moteur
`results/c121_target_limit/A40x6/bench.json`, JSONL, journaux et bundle adjacents.
SHA256 JSON :
`01ca5bb45f6c10fc568d6c3d326ce7aa737f4a7421ce122e968112f81c7f0120`.
SHA256 manifeste, recalcule conforme :
`3c678f960a91fed6eb68447110c089f6601b4e1fa19f155592d5fef9dd93b3fc`.
Bundle : `cc25b98a1e841b451df376add995e137334ed051ba34c4e93a942855983c0989`.
Etat final `state_40x6.json` : finished, complete=true, verdict=fail_primary.
Conteneur exact termine normalement (exit 0) et supprime par `--rm`.

### Diagnostic hors ligne : ce que le plafond corrige peu

Suite a l'observation utilisateur (avions peu rentables, aeroportuaire AAA plus
etendu et trajets plus longs), extraction du JSONL terminal et des 80 logs du
meme 40x6, sans nouvelle partie ni modification de politique. Les 160 lignes
compagnie terminales sont presentes au 01/12/1975 ; compteurs AIR qualifies.

| Moyenne terminale | C121 reference | C121 plafond | AAA face reference | AAA face plafond |
|---|---:|---:|---:|---:|
| Avions principaux | 85,650 | 83,875 | 46,000 | 48,225 |
| Aeroports physiques | 23,975 | 23,725 | 39,200 | 39,900 |
| Capacite passagers simultanee | 19 208,5 | 18 819,0 | 5 900,75 | 6 046,75 |
| Avions / aeroport (ratio des totaux) | 3,572 | 3,535 | 1,173 | 1,209 |
| Places passagers / avion (ratio des totaux) | 224,3 | 224,4 | 128,3 | 125,4 |

Le plafond reduit la flotte totale Opex de seulement **1,775 avion (-2,07 %)**,
et sa capacite passagers de **389,5 places (-2,03 %)**. 22 graines ont moins
d'avions, 2 autant, 16 plus (trajectoires du reseau modifiees). Il ne conduit
pas a davantage d'aeroports en moyenne. Opex conserve environ 3 fois plus
d'avions par aeroport et 3,3 fois la capacite passagers d'AAA. La densite ne
mesure ni congestion ni taux de remplissage ; les totaux AIR incluent le
courrier, dont l'offre AAA est differente. Le profit compagnie ne se divise
pas par ce nombre d'avions pour calculer un profit AIR.

Logs cumules de construction : Opex reference, 1 388 C121_BUILD, distance
tarifaire Manhattan moyenne **209,9**, mediane **205,5** ; AAA en face,
787 constructions AirRoute reussies, distance Manhattan moyenne **249,8**,
mediane **246**. Moyenne AAA superieure sur **40/40 graines**.
Avec plafond : Opex 209,1/205 (1 362 builds), AAA 247,7/242 (802 builds),
AAA plus long sur 39/40 graines. Comparaison descriptive de constructions
cumulatives, pas des lignes survivantes, et melange PASS/MAIL AAA : Opex
mesure station->station, AAA place->place (`route.nut`, log Succeeded).
La geometrie n'est pas strictement identique ; aucune causalite de longueur
sur le profit n'est attribuee a cette comparaison.

Renforts Opex : **584/1 065 observations de marge negatives (54,8 %)** en
reference et **541/1 004 (53,9 %)** avec plafond. Respectivement 85 et 63
observations ont une moyenne historique positive mais un dernier palier
negatif. Le garde sur le dernier marginal est deja present dans les deux
bras. `obs_profit` est la variation du profit TOTAL de ligne entre avant
et apres renfort, moins amortissement, puis normalisee par avions ajoutes :
croissance de demande, concurrence et reseau peuvent varier entre-temps.
Ce n'est ni le profit propre d'un avion ni une estimation causale de son effet.
L'observation attend `year+2` ; le plafond physique ne reduit pas ce delai et
ne revend pas les avions devenus peu rentables.

Conclusion diagnostique : l'absence de gain du plafond ne refute pas le
probleme de flotte. Il modifie peu la densification et laisse inchanges les
estimations economiques, les choix d'appareils/distances et le retrait de
capacite. Suite utile : mesurer par ligne et avion mature le profit, la
capacite, le renfort, le partage d'aeroport et la distance, puis separer
maintien d'un avion negatif et prochain achat a marge negative avant une
intervention isolee. Aucun nouveau reglage ni campagne adopte ici.

Preuves locales reproductibles : `results/c121_target_limit/diagnose_fleet_40x6.py`,
`fleet_diagnostic_40x6.json`, `diagnose_marginal_40x6.py`,
`marginal_diagnostic_40x6.json` (hashes des 80 logs),
`diagnose_distances_40x6.py`, `distance_diagnostic_40x6.json`.
SHA256 JSONL : `4c4ff251343cef5f5c8fadab7a1b9206b39d8fdd4392eaa89fd91ca6f8d84bce`.


Demande utilisateur : poursuivre l'analyse de `targetAirPlanes` et corriger le
comportement. Intervention distincte du garde sur le dernier renfort marginal,
deja present dans l'arbre local et commun aux deux bras.

## Diagnostic et intervention isolee

`OpexC121AirFleetScanCap` borne une recherche economique, pas l'absorption d'un
aeroport. Le N de profit absolu maximal calcule apres construction n'est pas
borne par `OpexAirCadenceCap`, garde appliquee seulement aux achats. Une cible
au-dessus du cap physique peut donc rester indefiniment inatteignable.
Deuxieme incoherence : une fois la cible atteinte, `c121BelowTarget=false`
reactive le scoring historique au profit moyen/avion et la croissance sur stock,
en quittant les gardes marginales C121. La cible n'etait pas un plafond.

Lecture hors ligne de la B originale `c121_vs_c115_current_B_20261007` :
1 387 evenements de construction proprietaire 0, cible moyenne **8,1002**, mediane
**7**, maximum **27** ; N de decision moyen **1,1240**, construit **1,1168**.
Sur 1 387/1 387 evenements, cible > decision et cible > construit. Ce sont des
constructions cumulees, pas les lignes survivantes ni un optimum observe.
Le cap physique n'etait pas collecte ; aucune reconstruction presumee ici.
Script/source/hashes : `results/c121_target_limit/offline/analyse_existing_b.py`,
`original_b_targets.json` ; manifeste source SHA256
`41d92545d8d770bdfd7a57ec2db9fab0578a05842cd04a7932cca484ef10af7f`.

Candidat `c121_air_target_limit=1`, defaut **0** pendant qualification :

- ouverture : `targetAirPlanes=min(cible economique,cap physique)` ;
- renfort : plafond effectif=min(cible memorisee,cap physique courant partage
  entre lignes) ; refus si deja atteint, aucune croissance historique au-dela ;
- projet/cache : refus des lots depassant la cible memorisee ;
- dernier site d'achat : revalidation de la flotte AIR vivante et de la cadence
  partagee avant toute commande ;
- aucune vente implicite ; remplacement V92 et refleet de crash distincts.

Scan economique, moteur, achat initial N=1/N=2, demande et classement inchanges.
`c121TargetPlanes` conserve le N theorique comme diagnostic. Pas de nouveau
champ durable ; anciennes saves revalidees au premier usage, cible absente/non
positive interdite sous candidat. Reglage relu par `OpexLoadSettings`.
La cible peut devenir conservatrice apres evolution du reseau : sa revalorisation
economique reste une piste distincte. Pas de retour aux anciens depth/split
rejetes : aucun remplacement de max-profit par P/C ni changement du classement.

## Pre-enregistrement et portes

Depot Windows local, `master`, HEAD observe
`c968157085ccbbe60f7da4fba98c40b1b70db67c`, arbre sale conserve. Le lanceur
fige l'arbre/SHA effectivement presents a chaque campagne. Tous les autres
changements locaux (dernier marginal, adaptatif tous regimes) sont communs.
Comparaison isolee du plafond, sans qualification du cumul C121/C115 :

```
reference = OpexAI[c121_air_economics=1,c121_catalog_incremental=1,c121_air_target_limit=0]
variante  = OpexAI[c121_air_economics=1,c121_catalog_incremental=1,c121_air_target_limit=1]
```

Autres defauts courants, C115=1 conserve ; aucun commit/push.
Image verifiee `openttd-lab:latest`, SHA256
`f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`,
contexte `desktop-linux`, cache `openttd-lab-home`, montage racine `/work`.
Profil 10 CPU, RAM/swap 8g, 10 workers, reseau host pour le gel des dependances.
Une campagne economique de ce chantier a la fois ; attendre la B existante
avant A/B, sans interruption. Exception technique pre-enregistree avant moteur :
PC 12 processeurs logiques/32 Go, campagnes actives ~10+1 coeurs et <1 Go RAM
observee ; VM/Save-Load seul peut occuper le coeur restant, 1 CPU/1g RAM et swap,
1 worker, copie dediee. Cette exception ne constitue pas une mesure economique.
Le smoke causal technique utilise egalement 1 CPU/1g/1 worker pendant la B
existante (diagnostic tiers termine), meme profil dans ses deux duels.
Parcours : contrats -> assertions VM/Save-Load -> smoke causal
42 x 1 an -> A40x3 -> B20x10 seulement apres A pass. Budget : 120 duels
economiques, 2 duels smoke, 2 phases solo techniques.

A `gain_short`, `profit_year`, seuil relatif 4 %, Wilcoxon bilateral p<0,05,
IC95 bootstrap borne basse >0 ; B `non_erosion`, borne haute >=0 ; garde valeur
-5 % aux deux portes. Bootstrap 20 000, seed 0, une repetition, graines
canoniques du harnais. Arret si sante/couverture/exposition absente ou porte
echouee, sans relance favorable. Candidat OFF avant qualification complete.

Exposition : smoke avec `decision_log=1` dans les deux bras ; rechercher
`C121_TARGET_LIMIT phase=build` model>limit et refus resize/buy a la limite.
VM : contrat du dernier achat sur une vraie ligne, projets caches, anciennes
cibles hautes, aucun achat/vente ; ce n'est pas une qualification du modele
physique. A/B sans cette sonde. JSON/JSONL, manifestes/bundles distincts dans
`results/`. Save/Load ordinaire, pas une interruption a une frontiere d'achat.

## Validation en cours

149 contrats verts : 73 C121, 5 cible, 8 flotte R1, 10 recovery R19,
6 calibration R2, 6 C84, 33 mecanismes R1/R3 et 8 revue R7/R10. Le contrat
C84 est adapte au troisieme argument (reseau partage). VM/Save-Load
`results/c121_target_limit/vm_save_load_r1/report.json` : **pass**, 17 assertions
avant et 17 apres reload, 13 sauvegardes mensuelles dans chacune des deux phases,
reconciliation effective, absence d'erreurs NoAI, copie source inchangee.
Matrice synthetique et refus reel d'achat/projet a la cible sur une vraie ligne.
Smoke causal `c121_target_limit_smoke_20261007_r1` lance ensuite, meme arbre,
sonde `decision_log=1` dans les deux bras, 1 CPU/1g/1 worker.

Smoke r1 termine sain : 1/1 paire, deux duels complete, comparaison/couverture
complete, `diagnostic_only` (echantillon d'adoption incomplet attendu). Exposition
naturelle : cible 7->6 sur line=7. Delta partiel a un an -21 310 £/an, valeur
+3,67 %, sans conclusion economique. Bundle
`4d25d4a962c547f1ea7c9b60526eae8eb1a50b1b5067f4030516e3322d239f24`.

Relecture avant A : retirer le scan physique redondant avant les gardes d'age.
Le garde precoce devient scalaire ; le calcul de cadence partagee existant
reste execute une seule fois pour un renfort eligible. La revalidation finale
d'achat reste physique. Aucun changement de formule/seuil ni selection d'un
resultat favorable. Nouvelle VM et nouveau smoke r2 sur cette finition avant A ;
r1 reste la preuve de son arbre anterieur.

Version finale r2 : VM/Save-Load **pass** avec 17 assertions dans chaque phase,
13 sauvegardes mensuelles/phase, reconciliation et absence d'erreurs. Smoke
`results/c121_target_limit/smoke_r2/bench.json` complet et sain : 1/1 paire,
`comparison_complete=true`, `metric_coverage_complete=true`,
`adoption_sample_complete=false` attendu, `diagnostic_only`. 14 constructions
tracees, dont line=5 cible **9->8**. Delta partiel -2 370 £/an, valeur -0,449 %,
sans conclusion economique. Bundle
`cc25b98a1e841b451df376add995e137334ed051ba34c4e93a942855983c0989`,
manifeste `7bc30eb2130abd7f09cc1389b538f1260ffc855eb217f392b17dbbdc9f23a277`
audite par recalcul SHA256.

Sources finales copiees dans `results/c121_target_limit/frozen_root` ; empreintes
dans `frozen_source_hashes.json`. Le lanceur courant et les memes fichiers AI/
harnais sont utilises depuis cette copie aux deux portes, montee via
`--mount-root` du depot. La provenance Git reste celle du depot parent, tandis
que les manifests identifient les sources effectivement executees de la copie.
Sequence unique `results/c121_target_limit/qualify_frozen.py`, sans relance,
en attente de ressources pour `c121_target_limit_A_20261007_r1` ; etat suivi
dans `pipeline_state.json`. A sous `gain_short`, B uniquement apres `pass`.

Preparation A r1 arretee **avant toute partie** : copie du harnais incomplete,
`Dockerfile` absent. Dossier partiel `results/c121_target_limit/A` conserve ;
aucun verdict economique. Copie completee avec `Dockerfile` et
`requirements-ml.txt` du bundle smoke r2, sans modification AI. Sequence unique
reprise sous `qualify_frozen_r2.py`, nouveaux identifiants A/B `_20261007_r2`,
etat `pipeline_state_r2.json`. Budget economique reste 120 duels puisque r1
n'a execute aucun duel ; total technique r1+r2 : 4 duels smoke et 4 phases solo.

A r2 effectivement lancee : 40 graines, 80 duels, 3 ans, 10 CPU/8g/10 workers,
sondes OFF. Bundle **identique au smoke r2**
`cc25b98a1e841b451df376add995e137334ed051ba34c4e93a942855983c0989` ;
manifeste `79d7beadcd3779b198162e3b79ceb18e5fc1123ced0daa959f7f3335a70f9e36`.
Sortie `results/c121_target_limit/A_r2/bench.json`, verdict en attente.

## Resultat et decision

A r2 terminee : **40/40 paires, 80/80 duels sains**, horizon et couverture
annuelle complets. `comparison_complete=true`, `adoption_sample_complete=true`,
`metric_coverage_complete=true`, regle **gain_short** attendue.

- Delta `profit_year` moyen **-21 192,025 £/an (-1,18 %)** ; reference moyenne
  **1 802 546,15 £/an**, seuil utile 4 % = **72 101,846 £/an**.
- Mediane **+14 260 £/an**, V/D/E **21/19/0**, Wilcoxon bilateral
  **p=0,8575823362** ; IC95 bootstrap **[-95 307,7 ; +53 257,8] £/an**.
- Garde de valeur : ratio des moyennes **-1,614341 %**, 40 denominateurs
  strictement positifs, garde -5 % tenue.
- Verdict brut **fail_primary** : gain utile non demontre. L'IC traverse zero :
  ni perte significative ni neutralite/equivalence demontree.

**B non lancee. Correctif conserve a defaut 0**, C121 economie/catalogue=0/0
et C115 protege inchanges. Aucun commit/push. La cible physique et le dernier
garde sont fonctionnellement valides, mais leur activation n'est pas qualifiee
economiquement. Ne pas transformer cet echec de A en validation de neutralite.
La correction ne resout pas la surestimation eventuelle de demande/profit du
modele ; une cible reevaluee depuis les observations reste une piste distincte.

Preuves : `results/c121_target_limit/A_r2/bench.json`, JSONL, manifeste, bundle
et logs voisins. JSON SHA256
`e75c2dbd292188cf67ca2751cf72bf7a1115ed75408dc19dac36ec15436482ad`.
Receipt audite `results/c121_target_limit/final_receipt.json` et script
`final_summary.py`. Aucun fichier Squirrel de production ne differe de la copie
testee ; defaults economie/catalogue/cible=0/0/0 verifies apres mesure.

### Deltas par graine, annee terminale 1972

| Graine | Reference £/an | Candidat £/an | Delta £/an |
|---:|---:|---:|---:|
| 42 | 2007075 | 1905209 | -101866 |
| 100 | 1199719 | 1141298 | -58421 |
| 7 | 2542515 | 2707592 | +165077 |
| 999 | 1209687 | 1310876 | +101189 |
| 2026 | 1774500 | 1790916 | +16416 |
| 1 | 2532689 | 2354382 | -178307 |
| 17 | 1101410 | 934884 | -166526 |
| 73 | 2534366 | 2661669 | +127303 |
| 314 | 1879794 | 2107860 | +228066 |
| 512 | 556939 | 489054 | -67885 |
| 1024 | 1203933 | 1138009 | -65924 |
| 1337 | 1848126 | 1557330 | -290796 |
| 4096 | 2842545 | 2369970 | -472575 |
| 8191 | 2447051 | 2443600 | -3451 |
| 12345 | 1057278 | 1076524 | +19246 |
| 54321 | 1877024 | 2007586 | +130562 |
| 65537 | 1407634 | 1101225 | -306409 |
| 123456 | 1830114 | 1842218 | +12104 |
| 424242 | 2039541 | 1934997 | -104544 |
| 8675309 | 1769561 | 1789528 | +19967 |
| 423960 | 3116252 | 2916667 | -199585 |
| 613553 | 2186639 | 1570536 | -616103 |
| 515222 | 2380997 | 2556237 | +175240 |
| 781335 | 1372003 | 1525613 | +153610 |
| 375172 | 1988762 | 1927158 | -61604 |
| 999533 | 2322837 | 2526054 | +203217 |
| 442018 | 1392023 | 1547570 | +155547 |
| 746035 | 2368188 | 2455304 | +87116 |
| 455216 | 799805 | 775015 | -24790 |
| 230185 | 1517179 | 1131074 | -386105 |
| 706990 | 1463877 | 962565 | -501312 |
| 983759 | 942918 | 736096 | -206822 |
| 802204 | 2153301 | 2633075 | +479774 |
| 232037 | 1157370 | 1533178 | +375808 |
| 723002 | 1981891 | 2095648 | +113757 |
| 313707 | 1914899 | 2073625 | +158726 |
| 701256 | 2041596 | 2132942 | +91346 |
| 292001 | 2016816 | 2352638 | +335822 |
| 841478 | 2098130 | 1776895 | -321235 |
| 59527 | 1224862 | 1361548 | +136686 |
