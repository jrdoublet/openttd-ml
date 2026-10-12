# AC-02 — recherche et reprise des sites AIR (11 octobre 2026)

**Verdict : AUDIT TERMINÉ, aucun défaut de curseur démontré ; aucun correctif
de production.** La paire `scanIndex` / `rankIndex` assure, dans le code courant,
la progression monotone à chaque suspension puis une consolidation ordonnée.
Une fixture indépendante a vérifié ces invariants sur état simulé figé. **Ce
n'est pas une exécution de Squirrel/NoAI** : on ne conclut pas à la neutralité
opcodes ni à la parité sur une carte qui évolue pendant plusieurs ticks.

## Frontière auditée

- `ai/OpexAI/air_planning.nut:176–440` (`OpexAirPlansPrepare`) : initialisation
  une seule fois de `combos`, `towns`, `townLimit` et classement C83 de référence.
  Le ciblage C83 déplace la ville cible en tête ; sans cible, la priorité C121
  des villes sales est appliquée **à l'initialisation** ; les tranches suivantes
  relisent `resumeState.towns` et ne retrient pas le vivier.
- `air_planning.nut:443–610` (`OpexAirPlansFindSites`) : `scanSites` est conservé
  et le prochain indice vaut **`i + 1`**, mis à jour *avant* le test de budget.
  L'objet `scanProbes` est conservé, y compris `left`, `tested`, `cheapSkip`,
  `stationLimitedTowns` ; une suspension ne recrée donc pas le budget des
  sondes `OpexAirFindSite`.
- `air_planning.nut:612–660` : la revalidation des sites accumulés reprend à
  **`rankIndex + 1`** ; `rankSites` est conservé dans l'ordre du balayage. Le
  résultat `resumeState.sites` n'est fixé qu'à la fin, puis les compteurs
  de scan et de rang sont remis à zéro sans vider la liste finale.
- `air_planning.nut:2393–2410,2489–2517` : tant que `sites=null`, la recherche
  précédente se poursuit ; une fois `sites` finalisée, les suspensions des
  paires réutilisent la liste sans rescanner les villes. Le passage au combo
  suivant vide explicitement `sites`, `scanSites`, `rankSites` et `scanProbes`.
- `air_planning.nut:678–779` : sur reprise des paires, le code revalide les
  sites en cas de modification de carte. Ce garde-fou est **postérieur** à
  AC-02 et ne remplace pas un test de parité du portefeuille.

**Bords métier inspectés :** villes déjà desservies, deuxième créneau C83,
exception V134, population des aéroports grands/petits avec ou sans V93,
quarantaine V133, refus du site, quota de sondes, ville ciblée et classements
C121. Le chemin *expérimental* `c83_local_repair=1` dévie vers
`OpexC83RepairFindSites` (`air_c83_repair.nut`) et possède ses propres
curseurs ; il est **à défaut 0** et n'est pas assimilé au chemin standard
dans la fixture. Ses six contrats existants restent verts.

## Matrice reproductible

**Fichier** : `sweeps/test_ac02_air_site_resume.py`.

Deux sortes de vérifications :

1. **Contrats sur le Squirrel réel** : présence et ordre de l'incrémentation
   *avant* suspension pour les deux curseurs ; conservation du budget et des
   résultats partiels ; conditions C83 ; absence de rescan lorsque `sites`
   est déjà disponible ; réinitialisation au combo suivant. Ces contrôles
   doivent échouer si le chemin est modifié sans mise à jour de preuve.
2. **Modèle de parcours sur état déterministe figé** : huit villes avec
   acceptations/rejets synthétiques, site périmé, ville servie, slot C83,
   quarantaine, limite de station. **96 configurations** combinant grand/petit,
   V93 ON/OFF, priorité sale ON/OFF, quatre budgets de sondes et cible
   C83 absente/présente/inexistante ; pour chacune, **cinq coupures**
   (1/2/3/5/9 unités), soit **480 comparaisons** avec le parcours non découpé.
   Assertions : mêmes IDs/ordre/sites, mêmes sondes, aucune ville ou
   revalidation parcourue deux fois, état transitoire vidé à la fin. Cas
   dédié : suspension **juste après la dernière ville**, puis **juste après
   la dernière revalidation** ; reprise vide sans doubler les visites.

Commandes et résultats du 11 octobre (Python local, sans Docker) :

| Vérification | Résultat |
|---|---:|
| `python -X utf8 -m unittest -v sweeps.test_ac02_air_site_resume` | **4/4 OK**, dont les 480 sous-cas |
| Contrats C78, V93, C83, V134 (`unittest -q`) | **28/28 OK** |
| Contrats C120, V133 (`unittest -q`) | **19/19 OK** |
| `python -X utf8 -m unittest discover -s sweeps -p 'test_c83_local_repair.py' -v` | **6/6 OK** |
| Total | **57/57 tests OK** |

Le test Python modélise **les checkpoints de reprise**, pas les appels
effectifs à `AIAirport.BuildAirport` : ceux-ci dépendent de l'état du terrain,
des gares, du cache, des prix et d'une éventuelle suspension NoAI. Les
différences naturelles lors d'une carte qui change entre deux tranches
ne constituent pas en elles-mêmes un défaut du curseur. Aucun smoke réel
Squirrel n'a été exécuté, car **aucun `.nut` n'a changé** et aucune variante
comportementale n'est soumise à adoption ; ne pas remplacer cette absence
par une affirmation de parité runtime.

## Points résiduels et décision

1. **Pas de doublon/omission établi** : le `scanIndex` et le `rankIndex` sont
   sauvegardés avant chaque retour et la liste de sites est conservée jusqu'à
   la consolidation. Sur les entrées figées simulées, le résultat final est
   identique, y compris avec le budget très faible.
2. **Coût par ville non strictement plafonné** : `OpexAirFindSite` est appelé
   *avant* le contrôle de budget de tranche. Une seule ville peut donc déjà
   consommer plus que le reliquat alloué ; c'est la granularité actuelle du
   mécanisme, pas un défaut de progression. Une optimisation intraville
   demanderait un autre protocole de reprise, un smoke et des portes
   économiques/opcodes : **pas dans AC-02**.
3. **Parité sur carte mouvante non affirmée** : la revalidation est faite
   à l'instant du rang puis au niveau des paires ; la cible de la fixture
   est expressément un même état figé et non la suppression de ce contrôle.

**Clôturer AC-02 sans retoucher production**, conserver la fixture de
non-régression. Ne pas réouvrir les politiques C83/V93/V134, le classement
C120/C121, V142 ou V143. Pas de campagne A/B, pas de modification de
réglage, aucun commit/push ; `git diff --check` validé.
