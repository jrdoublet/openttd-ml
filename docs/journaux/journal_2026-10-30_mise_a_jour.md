# 30 octobre 2026 — clôture des tâches et nettoyage du registre documentaire

Ce journal retrace **l'opération de classement documentaire**, sans présenter les
modifications comme un nouvel A/B économique ou un changement de comportement IA.
Le travail s'appuie sur le `origin/master` publié au commit `2429d175` ; le
`master` local de développement contient des modifications d'autres agents et
n'a pas été modifié.

## Réconciliation effectuée

L'ancien `docs/taches.md` comptait **2 874 lignes**, **39 cases non cochées** et
de nombreuses centaines d'analyses, actions anciennes, hypothèses réfutées et
notes de versions précédentes. Il est conservé en entier, avec ses contenus et
ses limites, dans le [journal de transfert](journal_2026-10-30_transfert_taches.md).
Le SHA-256 des octets de la version source est
`55dc840715dc5cfc1abb0a23ed623ac26614550c544fcf05712e03f1b23dfa7c`.
Les chemins Markdown relatifs ont été adaptés au dossier `journaux/`, sans
changer les chiffres et verdicts des études. Le registre actuel ne recopie plus
les historiques de 2026-09 ou les anciennes portes déjà conclues.

### Réconciliation des 39 anciennes cases non cochées

Les numéros suivants sont les **lignes du registre d'origine**, conservées dans
le transfert. Un libellé « clôturé » signifie que l'**étape précise** a été
effectuée ou refusée, et ne donne aucune validation aux hypothèses voisines.

| Lignes de l'ancien registre | Sujet | Sort dans le nouveau registre |
|---|---|---|
| 12 | ESTIM-31 combinatoire AIR+RAIL | **Coché** : top3, vrais 20×10, défaut élu et `origin/master` publiés |
| 14 | Dispatch C121 / moteur | **Coché** : scan ESTIM vérifié, OFF historique préservé |
| 16 | V161 renfort AIR | **Coché** : livré dans le bundle élu ; V252 et autres ROI restent distincts |
| 17, 26 | Couverture AIR et EB-1 | **Ouvert** : nouvelle lecture au défaut ESTIM31 |
| 27 | EB-2 repli de gare neuve | **Coché** : expérience A négative, aucun défaut activé |
| 37 | EB-3 vivier RAIL 1970 | **Ouvert** : réexaminer avec le préchargement EB14=3 |
| 38 | EB-4 trésorerie précoce | **Ouvert** : dépenses/renoncements exacts |
| 39 | EB-5 chaîne GOOD | **Ouvert** : opportunités réellement admissibles |
| 40 | EB-6 / P4 SITEAB | **Ouvert reformulé**, sans retester P4 inerte ni EB-2 rejeté |
| 42 | EB-7 ventilations opcodes et cash | **Première étape cochée** ; comptabilité transactionnelle détaillée toujours ouverte |
| 47 | EB-8 P5 dédoublonnage | **Coché** : script analytique corrigé |
| 49 | EB-9 sonde d'aéroports | **Coché** : AIR seul adopté ; qualification multimodale résiduelle distincte |
| 52 | EB-11 recherche de sites RAIL | **Coché** : hypothèse réfutée à la sonde |
| 54 | EB-12 bilan | **Coché** : suivi redistribué aux tâches actives |
| 55 | EB-10 express / sentinelle 65535 | **Ouvert** : défaut de production à vérifier puis corriger |
| 58 | EB-13 profit passagers | **Ouvert** : calibration et validation indépendante |
| 311 | MULTI-1 | **Suspendu**, pas d'exécution automatique |
| 601, 607 | AIR-ROI remplacement et nouvelle ligne | **Ouverts** séparément du renfort V161 achevé |
| 661 | ESTIM-1 | **Partie implémentation cochée** ; qualité de prévision hors échantillon ouverte |
| 671, 700, 1432 | FLOTTE-EQUILIBRE, V286, V253 | **Ouverts regroupés** : flotte physique et moteur hétérogène |
| 684, 694 | AIList-2, IDLE-1 | **Ouverts** : gain opcode réel et CPU total à prouver |
| 698 | LATE-GAME-1 | **Ouvert** : dépenses tardives rentables à démontrer |
| 907 | V291 difficulté 4 | **Réserve conditionnelle**, distincte du mode compétitif normal |
| 938 | DIST-BORNES-1 | **Ouvert** sans rejouer les essais non exposés |
| 949 | PO-02 | **Ouvert** ; PO-01c reste déjà livré |
| 1105, 1107, 1162 | V242 feeders, V233 chaîne, V226 araignée | **Réserve de nouveaux mécanismes**, les anciens rejets ne sont pas effacés |
| 1285, 1287, 1293 | V249a, b et c | **Ouverts regroupés** : ROI supplémentaire et capital marginal |
| 1405, 1482 | V261 courtoisie / fair-play | **Ouvert** pour les comportements optionnels, audit antérieur livré |
| 1500 | Désactiver les sondes hors banc | **Ouvert** ; le nouveau défaut a explicitement `probes=2` |

Il y avait **39 lignes non cochées au départ** ; ce tableau couvre toutes ces
lignes, y compris les tâches partiellement achevées qui ont été séparées en
**étape cochée + reliquat distinct**, plutôt que d'afficher une fausse
clôture totale. Les centaines d'autres tâches historiquement cochées sont
conservées dans le transfert mais n'encombrent plus la file active.

### ESTIM-31 — campagne achevée et nouveau défaut installé

Le [rapport final](../estim31_phase_combinatoire_20261030.md), le
[classement certifié](../estim31_top3_20x10_20261030.json), la
[preuve d'installation](../estim31_default_promotion_20261030.json) et le
[rapport de validation](../estim31_default_validation_20261030.md)
tranchent les mentions « 40×5 en cours », « élection future » et
« aucun défaut modifié » qui étaient encore vraies pendant l'expérimentation
du 29–30 octobre, mais **fausses pour le code publié ensuite**.

| Campagne réelle 20 graines × 10 ans, 40/40 parties saines | Moyenne OpexAI `profit_year` 1979 | Moyenne AAAHogEx de son propre duel | Ratio des deux moyennes |
|---|---:|---:|---:|
| **V161 AIR2,00 / RAIL0,75 — élu** | **4 255 528,00 £** | **6 393 740,05 £** | **66,557726256 %** |
| V161 AIR2,50 / RAIL0,75 | 4 225 862,90 £ | 6 410 403,65 £ | 65,921947052 % |
| V161 × choix moteur C121 N1/N2 | 4 290 978,40 £ | 6 582 408,65 £ | 65,188575006 % |

Le top 3 figé à 5 ans était dans l'ordre inverse partiel : 106,062928693 %,
105,171758309 % et 103,798667198 %. Aucun veto de valeur d'entreprise,
Wilcoxon, IC95 ou seuil `gain_short` n'a été utilisé pour choisir le meilleur
duel décennal. Les performances des parties tardives ne sont pas extrapolées
des premières cinq années.

La source réellement exécutée du gagnant a été installée, SHA contrôlé et
publiée sur `origin/master` à `7160c6f5`, puis documentaire à `2429d175`,
sans push forcé. Les valeurs publiques **effectives du code au 30/10** sont
`estim_unifie=31`, `eb14_progressive=3`, `probes=2` dans
[`ai/OpexAI/info.nut`](../../ai/OpexAI/info.nut) ; les anciens réglages `0`
restent des options **explicites**. FullScan C121 sous ESTIM ne réemploie pas
une borne économique incorrecte ; les fonctions historiques restent
disponibles OFF. Le bilan PLYR distingue constructions nettes, achats nets,
recettes et stocks physiques, sans inventer les achats bruts.

**Limite non close :** découverte historique globale 3 175 tests avec 84
échecs et 16 erreurs sur le nouveau défaut (ancien socle déjà non vert :
3 124 tests, 2 échecs et 12 erreurs). Les tests spécifiques et suites CI
53+38+4, ainsi que les deux Save/Load seed999 (par défaut et explicite),
réussissent. Ne pas conclure que la grande suite est verte ; une tâche
**QUALITÉ-TESTS-ESTIM31** explicite demeure.

### Clôtures EB et études réutilisables

- **EB-2 :** échec porte A 40×3 du repli de gare neuve (`−19,1 k£/an`),
  `eb2_new_station_fallback=0` dans le nouveau défaut. La cause `SITEAB` et
  le coût physique d'une alternative restent une **nouvelle hypothèse**, pas
  la poursuite automatique du prototype rejeté.
- **EB-7 :** une première ventilation opcodes par sous-tâche et dépenses
  globales a été livrée sur trois graines et cinq ans ; les achats bruts,
  paiements individuels et réconciliations par projet n'ont **pas** encore
  été couverts. Ce reliquat est nommé **EB-7 phase 2**.
- **EB-8 :** lecteur GOOD dédoublonné (614 couples fictifs → 56
  exploitables), sans correction du bug de production d'acceptation GOOD/MAIL
  et de l'industrie invalide `65535` ; ces derniers relèvent d'**EB-10**.
- **EB-9 :** `air_site_ranked` a franchi ses portes AIR seul et été fusionné
  à `fef644a8`, sans preuve de neutralité ou gain **propre en multimodal**.
  Ce contrôle demeure distinct au nouvel état ESTIM31.
- **EB-11 :** approche « sites RAIL classés comme AIR » non qualifiée ;
  `SITEAB` provenait de la jointure V178, pas du score de terrain.
- **EB-12 :** bilan des EB du 27–28/10 déjà rédigé ; ses suites sont
  reclassées sans ouvrir une tâche « faire un autre bilan ».
- **P1–P6, RAIL-CAPEX, FRONT-PAX, AIR-FLOTTE, AIR-MONOPOLY et lots associés :**
  conservent les rejets, non-expositions, dérogations et rapports originels.
  Aucun `NO-GO` historique n'est réinterprété comme une adoption grâce à
  ESTIM31. Voir le [transfert](journal_2026-10-30_transfert_taches.md) et les
  liens aux rapports spécialisés depuis le registre courant.

## Audits des autres pages — périmètre et corrections

Le code réel `ai/OpexAI/info.nut` a été comparé aux fiches ESTIM du 27/10,
au rapport C121 du 29/10 et à la documentation de production du 30/10.
Les fiches **datées** sont préservées comme relevés historiques (notamment les
bras de référence `estim_unifie=0`), mais une bannière indique qu'un ancien
« défaut 0 » ne décrit plus le `master` publié. Le
[sommaire documentaire](../README.md), l'[index des journaux](README.md), le
[README racine](../../README.md) et la reprise ancienne ont été ajustés.
Le code et les journaux plus récents priment sur une ancienne phrase de plan.

Une vérification élargie des liens historiques a aussi repéré des **références
anciennes non résolues dans ce worktree isolé**, notamment des artefacts
`results/estim1_*` des essais du 27/10 et l'ancien module
`ai/OpexAI/task_town.nut`. Ces cibles précédaient la réorganisation ; elles
peuvent être propres à un worktree ou à des résultats non suivis. **Aucun lien
vers un résultat n'a été « réparé » en lui inventant un chemin**. Les pointeurs
vers des lignes du vieux `taches.md` ont en revanche été redirigés vers le
journal exact, et les chemins locaux `file:///home/deploy/...` remplacés
lorsque les fichiers source existent effectivement dans le dépôt. Un audit
exhaustif des artefacts de toutes les campagnes demeure distinct de la
présente clôture documentaire.

## Restants identifiés sans réouverture abusive

La nouvelle [liste active](../taches.md) conserve les problèmes d'AIR après
1972, le vivier RAIL 1970 sous le *nouveau* EB14, les devis `SITEAB`, le fret
GOOD, la sous-estimation RAIL voyageurs, les comptes réels, les bornes V269
tardives, les renouvellements V252, le suivi d'actions municipales et les
tests historiques. Les idées V208–V211, NewGRF, multimodal MULTI-1 suspendu et
maritime restent en **réserve**, sans lancer de banc sur la seule base d'une
phrase « à faire » datée.

## 30/10 — Analyse complémentaire des trois 20×10 et ordre des priorités

Sur les trois qualifications complètes du top3, la première année où
**OpexAI repasse sous 100 % AAAHogEx** est **1975**. Le gagnant tombe de
**103,24 % en 1974 à 66,56 % en 1979**, au moment où le parc de trains
d'AAAHogEx passe de 26,3 à 56,3, contre seulement 24,5 à 29,6 chez
OpexAI. En 1979, le gagnant détient 84,25 avions, 14,74 M£ de caisse
et aucun emprunt restant. Comptes PLYR **1979 cumulés au 1er décembre** :
retard de recettes ferroviaires 1,168 M£ et aériennes 0,857 M£, sans
prétendre que ces deux différences sont des profits marginaux.

Une [analyse dédiée et reproductible](../estim31_priorites_20x10_20261030.md)
et [ses 5 nouveaux tests de cohérence](../../sweeps/test_estim31_20x10_priority_analysis.py)
documentent la lecture précise, le statut non causal de la comparaison
avec le C63 du 26/10 et l'absence de banc supplémentaire. Trois
priorités économiques deviennent explicites dans
[la liste active](../taches.md) : **P0 POST-1974-ENTONNOIR** des
nouveaux projets rentables, **P1 RAIL-RENDEMENT-TARDIF** (capacité,
fréquence, note et V284) puis **P1 AIR-PRODUCTIVITÉ** (rentabilité par
avion/ligne V161/V252). Les tests historiques du nouveau défaut
restent un P0 **technique**, suivi en parallèle. Aucun code métier,
réglage par défaut ou verdict des variantes rejetées n'est modifié.
