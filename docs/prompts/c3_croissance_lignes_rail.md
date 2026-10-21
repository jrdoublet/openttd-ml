# C3 — Pourquoi nos lignes rail ne grandissent pas : découpage (22/10, préparé, rien de lancé)

## Le constat à expliquer

- **Cohorte des lignes fret présentes en 1975 et en 1979** (`v299_diag_3x10`, moyennes par partie) :
  - nous : 19 → 19 trains, profit 244 → 546 k£ ;
  - AAAHogEx : 20 → 24-30 trains, profit 675 → 1 398 k£.
- **V284 au défaut 3** (10 ans, 3 graines, 2 bras) :
  - 35/53 ajouts de wagons ;
  - **0 second train terminé** ;
  - 72/87 refus `traction` ;
  - en 1979, 56/58 et 64/69 lignes ont moins d'une rame en attente au quai.
- **Ce qui n'a pas payé** :
  - évitements V202k : 35 posés, −27 k£/an au 20×10 rail seul ;
  - double voie V200d : 2 posées en 20 parties ;
  - tandems V271 : note de la source +30 à +60 points, profit de la ligne inchangé ;
  - V284 : porte A −41 k£/an, porte B neutre.
- **Ce qui le relie** : notre note de source est de 162/255, contre 214 chez AAA. Le délai de ramassage vaut q75 = 7 périodes chez nous et 1 chez AAA.

**Ce que C3 doit trancher.** L'attente au quai est-elle faible parce qu'il n'y a pas d'offre, ou parce que notre unique rame laisse la note basse ? Dans le deuxième cas, la production captée elle-même est réduite. Et si l'offre manque, pourquoi les trains ajoutés jusqu'ici n'ont-ils rien rapporté, alors que ceux d'AAA rapportent ? On ne code aucun levier avant d'avoir la réponse (règle « ne pas reproposer un 2ᵉ train sur voie unique sans diagnostic »).

## Tâches

| N° | Tâche | Priorité | Complexité /5 | Dépend de | Qui | Docker |
|---|---|---|---|---|---|---|
| C3.1 | Où vont les trains ajoutés par AAA | P1 | 2 | — | Claude VPS | non |
| C3.2 | Règle d'AAA pour ajouter un train, dans son source | P1 | 2 | — | Claude VPS | non |
| C3.3 | Débit d'une ligne : offre, note, capacité, aller-retour | P1 | 3 | C3.1 (inventaire des champs) | Claude VPS | non |
| C3.4 | Pourquoi les trains ajoutés par V202k et V271 n'ont rien rapporté | P2 | 2 | C3.3 (même modèle) | Claude VPS | non |
| C3.5 | Les 72/87 refus `traction` de V284 | P2 | 2 | — | Claude VPS | non |
| C3.6 | Compter les exclusions silencieuses de V284 | P2 | 2 | — | prompt PC | smoke 1×1 |
| C3.7 | Synthèse et choix du levier (ou abandon) | P1 | 1 | C3.1 à C3.5 | Claude | non |
| C3.8 | Coder le levier choisi | selon C3.7 | 3-5 | C3.7, accord utilisateur | prompt PC ; codex pour la sous-étape voie/signaux | smoke |
| C3.9 | Exposition puis porte A | selon C3.7 | 1 | C3.8 | PC (10 ans) | 3×10, puis 40×10 |

Ordre : C3.1, C3.2 et C3.5 d'abord, en parallèle. Puis C3.3, puis C3.4. C3.6 peut partir sur le PC dès maintenant. C3.7 clôt le diagnostic.

### C3.1 — Où vont les trains ajoutés par AAA (P1, 2/5)

- **Données** : `wt-v299/results/v299_diag_3x10_20261021*` (télémétrie de ligne des deux compagnies, clichés de décembre). En contrôle : `wt-v294g/results/v270_expo_3x10_20261019*`.
- **Mesure** : pour chaque ligne fret survivante 1975 → 1979, d'AAA puis de nous :
  - cargo, distance ;
  - trains en début et en fin de cohorte ;
  - places par train ;
  - profit de l'année Y−1 (cliché de décembre, voir `profit_last_year_cliche_decembre`) ;
  - voie unique ou double, si la sauvegarde le permet.
- **Livrable** : quelles lignes AAA gagnent des trains (cargo, GOOD ou non, distance), et le profit marginal par train ajouté. Le compte se fait en lignes et en trains, pas en moyennes de ratio.
- **Piège** : le profit du cliché du 1/12 est celui de l'année précédente. Ne pas mélanger la cohorte et le flux de lignes neuves.

### C3.2 — La règle d'AAA, dans son source (P1, 2/5)

- **Source** : `ai/AAAHogEx-115/`. Vérifier chaque chemin et chaque ligne cité (`verifier_citations_source_externe`).
- **À trouver** :
  - le déclencheur d'ajout d'un train : attente, note, production ou temps depuis le ramassage ;
  - la disposition des voies : double voie d'emblée, évitements ou signaux ;
  - le chargement complet (`full load`) ;
  - le plafond de trains par ligne ;
  - la vente ou le renvoi des trains en trop.
- **Livrable** : la règle, traduite en appels de l'API NoAI que nous avons déjà, et ce qui nous manque physiquement (souvent la voie).

### C3.3 — Débit d'une ligne (P1, 3/5)

- **Modèle** : formule de note de `docs/mecanique_jeu.md` (vérifiée dans le source 15.3) et part transportée ≈ note.
  - Offre annuelle = production × part transportée.
  - Capacité annuelle = places × 365 / aller-retour.
  - Plafond de la voie unique : une rame par aller-retour sans évitement.
- **Classement des lignes** :
  - (a) bornées par l'offre à note égale ;
  - (b) bornées par la capacité ;
  - (c) bornées par la note, quand un ramassage plus fréquent ferait monter l'offre ;
  - (d) bornées par la voie.
- **Livrable** : pour chaque ligne survivante, sa classe et le gain plafond en £/an d'un 2ᵉ train :
  - sur voie unique ;
  - avec un évitement ;
  - en double voie.
- **Préalable** : inventaire des champs présents (production de la source, note, `time_since_pickup`, aller-retour). Ce qui manque est noté « inconnu », sans être deviné, et part dans C3.6.

### C3.4 — Pourquoi V202k et V271 n'ont rien rapporté (P2, 2/5)

- **Données** :
  - V202 sur le VPS : `results/v202_railseul_10x3_20261015_engine`, `v202g_railseul_10x3_20261015_engine` ;
  - V271 : `results/worktrees_archives_20261020/wt-v271/results/v271_expo_3x10_20261019*`.
  - Les 20×10 V202k et V200d sont sur le PC.
- **Mesure** : profit de chaque ligne avant et après l'ajout, par classe C3.3.
- **Hypothèse à confronter** : les trains ont été ajoutés sur des lignes (a) ou (d), pas (b) ou (c).
- **Livrable** : la cause, ligne par ligne, et la condition qui aurait dû filtrer l'ajout.

### C3.5 — Les refus `traction` (P2, 2/5)

- **Code** : `OpexV284Equipment` (`task_v284.nut:28`) exige :
  - une vitesse effective ≥ celle de la composition actuelle ;
  - une vitesse maximale de locomotive ≥ celle de la locomotive actuelle.
- **Mesure, par refus des journaux V299** :
  - moteur actuel et meilleur moteur achetable ;
  - vitesse perdue si l'on accepte une locomotive plus lente ;
  - débit `places × vitesse` avant et après.
- **Livrable** : nombre de refus où une rame plus longue mais plus lente transporterait plus par an. La garde n'est relâchée que si ce compte est significatif et que la classe C3.3 de la ligne est (b).

### C3.6 — Compteurs des exclusions de V284 (P2, 2/5, prompt PC)

- **Fichier** : `ai/OpexAI/task_v284.nut` seul, sous `decision_log`, coût nul au défaut.
- **Contenu** : une ligne `V284_SCAN` par mois, avec le nombre de lignes rail fret écartées par motif :
  - nombre de rames ≠ 1 ;
  - double voie ;
  - profit ≤ 0 ;
  - quota de 90 jours ;
  - dépôt invalide ;
  - attente < 1 wagon ;
  - quai plein et attente < 1 rame ;
  - pas de créneau véhicule ;
  - caisse < 1 M£.
- **Champs à ajouter à la même ligne** si C3.3 les trouve absents : production de la source, note et `time_since_pickup`.
- **Validation** : tests de contrat, puis smoke 1×1. Pas d'exposition avant C3.7.

### C3.7 — Synthèse et choix (P1, 1/5)

Choisir un seul levier, avec son gain plafond chiffré, ou conclure qu'il n'y en a pas :

- (i) déclencheur fondé sur le flux et la note au lieu de l'attente instantanée, sur les lignes (b) et (c) seulement ;
- (ii) 2ᵉ train avec évitement, sur les lignes (d) longues seulement ;
- (iii) locomotive plus lente acceptée sur les lignes (b) ;
- (iv) aucun : l'écart vient des lignes GOOD et longues que nous n'avons pas, renvoi vers V233.

Le livrable est une section de `docs/v299_ecart_10ans_20261021.md` et une entrée dans `docs/taches.md`. Le levier est soumis à l'utilisateur avant C3.8.

### C3.8 et C3.9 — Code, exposition, porte

- **Code** : sous un nouveau bit de `v284_rail_growth`, ou un réglage neuf à défaut 0. La sous-étape « évitement + signaux sur une voie existante, avec retour arrière » va à codex, seule et bornée. Le reste va dans un prompt PC.
- **Bancs** :
  - smoke 1×1 ;
  - exposition 3×10 sur le PC, avec des critères fixés dans C3.7 : seconds trains terminés, trains de cohorte, note de source, cargo transporté par ligne ;
  - porte A 40×10 `gain_short`, car le mécanisme joue tard. Elle tourne sur le PC, ou la nuit sur accord.
