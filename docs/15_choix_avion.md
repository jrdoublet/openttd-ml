# C72 — Choisir l'avion d'une route au profit, au ROI, ou par le score C69

**Ouvert le 2026-09-21 à la demande de l'utilisateur** : « on choisissait toujours les gros avions,
ce qui asséchait la trésorerie ». Aucune trace écrite de cet épisode n'a été trouvée dans le dépôt ;
cette fiche le mesure directement.

## 1. Ce que fait le code

`OpexAirChooseRoutePlane` (`builder_air.nut:988`, C68 adopté) évalue tous les avions compatibles
avec l'aéroport, à route et demande fixées, et retient celui qui a le **plus grand `profitAnnual`**.
Le portefeuille, lui, classe ensuite les routes par **P/C**. Une route n'entre donc au vivier
qu'avec **une seule variante**, celle du profit maximal, qui n'est pas forcément la plus rentable
par livre investie.

## 2. Sonde passive (étape 1)

Sous `probe_portfolio` (implémentée par agy, relue) : pour chaque appel avec au moins deux avions,
les gagnants au profit (choix actuel), au ROI (P/C) et au score C69 (P×1000/max(C, K_dec), K_dec en
cache journalier). Une ligne par désaccord, un compteur annuel, et le type d'avion (`planeId`)
publié dans `line_calib`. Aucune décision changée.

5 graines × 6 ans, solo, 0 échec : `results/diag_c72_plane_choice_6y_5seeds.json` ; analyse
`sweeps/analyse_c72_plane_choice.py` (le brut, 25 Mo, n'est pas versionné).

### 2.1 E1 — exposition (appels à `OpexAirChooseRoutePlane`, 5 graines)

| année | appels | ROI ≠ profit | C69 ≠ profit |
|---|---:|---:|---:|
| 1970 | 903 | 62 % | 63 % |
| 1971 | 23 862 | 67 % | 67 % |
| 1972 | 22 747 | 63 % | 48 % |
| 1973 | 21 105 | 54 % | 15 % |
| 1974 | 18 707 | 49 % | 1 % |
| 1975 | 17 550 | 46 % | 0 % |

Le score C69 fait exactement ce que l'utilisateur décrit : il choisit au ROI tant que l'entreprise
est pauvre, puis rejoint le choix au profit (1 % de désaccord en 1974, 0 % en 1975).

### 2.2 E2 — ce que coûte l'avion au profit maximal (66 310 désaccords)

- L'avion au profit coûte **2,9 fois** la variante au ROI (médiane du capital de la route), pour
  **1,34 fois** son profit : son ROI est environ **deux fois plus bas**.
- En 1970, la variante au profit dépasse le **capital disponible dans 82 % des désaccords** ; 23 %
  en 1971 ; jamais ensuite.
- Couple dominant : **Yate Haugan** au profit contre **FFP Dart** au ROI (28 844 cas), puis Yate
  Haugan contre Bakewell Luckett LB-10 (10 867).
- **Aucune ligne n'a été construite en Yate Haugan** (lignes bâties : LB-10 49, FFP Dart 33,
  Darwin 200 15, Darwin 300 11, YAC 1-11 7, Guru Galaxy 3).

**Lecture.** L'assèchement n'a pas lieu : le portefeuille refuse ce qu'il ne peut pas financer, et
classe mal une variante à ROI divisé par deux. Le coût est ailleurs : **une route dont le meilleur
avion au profit est cher n'entre au vivier que sous cette variante**, trop chère ou peu rentable.
Sa version bon marché, plus rentable, n'est jamais proposée. C'est une hypothèse sur l'effet ;
l'exposition, elle, est mesurée.

### 2.3 E3 — le modèle se trompe-t-il selon l'avion ?

Réalisé/prédit (profit par convoi, amortissement retiré, âge ≥ 2, flotte inchangée) :

| avion | lignes | réalisé / prédit |
|---|---:|---:|
| FFP Dart (217) | 9 | **2,13** |
| Bakewell Luckett LB-10 (223) | 29 | **1,90** |
| Yate Aerospace YAC 1-11 (225) | 2 | 1,31 |
| Darwin 300 (228) | 6 | 1,22 |
| Darwin 200 (227) | 5 | 1,14 |
| Guru Galaxy (232) | 1 | 1,13 |

⚠️ Petits effectifs, sauf pour le LB-10. Mais le sens est net : **le modèle sous-estime surtout les
petits avions bon marché**, environ deux fois, contre 1,1 à 1,3 pour les gros. Un choix au profit
prédit favorise donc à tort les gros avions. Le facteur C70 est le même pour tous les avions et ne
corrige pas ce biais.

## 3. Étape 2 proposée — le levier (critères écrits avant le code)

Réglage `c72_plane_choice` (défaut 0 = C68, profit maximal). Valeurs : 1 = ROI, 2 = score C69.
Seul `OpexAirChooseRoutePlane` change ; K_dec vient du cache journalier.

Diagnostic 5 graines × 6 ans, **solo** (déterministe), trois bras : 0, 1, 2. Un bras passe au 20×10
en duel si, face au bras 0 :

1. il gagne au moins **4 graines sur 5** en `profit_year` ;
2. sa `company_value` moyenne ne baisse pas de plus de 5 % ;
3. il construit réellement d'autres avions (les lignes bâties par type diffèrent du bras 0).

Si les deux bras passent, on garde **2 (C69)**, qui a le moins de désaccords avec C68 et ne dépend
d'aucune constante. Si aucun ne passe, la fiche se ferme sur cette étape.

## 4. Résultat de l'étape 2 (2026-09-21)

Réglage `c72_plane_choice` (0 = profit, défaut ; 1 = ROI ; 2 = score C69), implémenté par agy et
relu. `sweeps/diag_c72_plane_choice_solo_5x6.py`, solo, 5 graines × 6 ans, 0 échec :
`results/diag_c72_plane_choice_solo_5x6.json`.

| paire | profit annuel | valeur | véhicules |
|---|---|---|---|
| **ROI (1) − profit (0)** | **+292 k£, 4 V / 1 D** | **+1,26 M£, 5 V / 0 D** | −3,8 |
| **C69 (2) − profit (0)** | **+145 k£, 4 V / 1 D** | +0,75 M£, 4 V / 1 D | −3,6 |
| C69 (2) − ROI (1) | −147 k£, 2 V / 3 D | −0,51 M£, 1 V / 4 D | +0,2 |

Avions réellement construits (5 graines) : sous le ROI apparaissent les moteurs 220 (18) et 226
(24), absents au profit ; le Darwin 300 (228) passe de 18 à 6. Sous C69, les changements sont plus
faibles : moteur 221 de 8 à 18, 220 et 226 marginaux.

**Critères du §3** : les deux bras passent (4/5 en profit, valeur en hausse, autres avions
construits). **La règle écrite d'avance retient le bras 2 (C69).** ⚠️ Mais le bras 1 (ROI) fait
mieux que le bras 2 sur ce 5×6 : +147 k£ de profit (3/5) et +0,51 M£ de valeur (4/5). La règle
avait choisi C69 parce qu'il s'écarte moins de C68 et ne dépend d'aucune constante, pas pour sa
performance. Choisir entre les deux relève de l'utilisateur.

Le bras 0 de ce diagnostic ne reproduit pas le défaut des diagnostics précédents (graine 100 :
1,245 M£ contre 1,493 M£) : le code de la sonde et du levier décale les opcodes (§13.4 de la
fiche 11). Les trois bras exécutent le même code, donc la comparaison reste appariée.

Commandes du 20×10 : `13_banc_c69_20x10_pc.md` §6.
