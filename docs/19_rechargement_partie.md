# Rechargement de partie : ce que deviennent les leviers adoptés le 2026-09-21

**Point préparé le 2026-09-21 à la demande de l'utilisateur.** Diagnostic seulement, aucun code
modifié. Porte sur le défaut adopté ce jour (C69, C69 bis, C70, C75) et sur C80.

## 1. Pourquoi ça n'a pas été vu

Les bancs ne rechargent jamais une partie : chaque partie démarre en 1970 et tourne d'une traite.
Une vraie partie, elle, est rechargée (`Load()` n'est appelé qu'au chargement ; l'autosauvegarde
appelle seulement `Save()`). Tout état qui n'est pas dans la sauvegarde repart de zéro au
chargement, et l'IA continue sans le savoir.

Un banc de rechargement existe et est validé (B5) : `sweeps/save_load_roundtrip.py` joue une
partie, garde ses sauvegardes, en recharge une et continue. Il a servi à la mesure du §3.

## 2. Ce qui est sauvegardé, et ce qui ne l'est pas

| état | sauvegardé ? | effet au chargement |
|---|---|---|
| lignes (`_lines`) avec `trains0`, `planeId`, `c70Real`, `c70Pred` | oui ; les flottants sont arrondis en entiers par la projection existante (`persist.nut:~447`) | aucun plantage ; les cumuls C70 par ligne survivent |
| vivier (`_projects`) | non, par conception | régénéré au premier passage (comportement historique) |
| recherche rail en cours (`_railSearch`) | non, par conception (pathfinder vivant) | abandonnée puis reconstruite (B5 validé) |
| **dates de chantier C69 (`C69_BUILD_DATES`)** | **non** | **K_dec faux pendant des mois (§3)** |
| **dates de passe C75 (`C75_PASS_DATES`)** | **non** | **K_pass faux pendant des mois (§3)** |
| **facteurs C70 (`C70_MODE_FACTOR`)** | **non** | reviennent à 1 jusqu'au prochain rapport annuel (au plus un an) ; recalculés ensuite correctement à partir des cumuls par ligne |
| C80 : file réactive, travailleur actif | oui (sous `c80_double_register`) | recherche rail abandonnée ; travailleur `town_growth` annulé puis recréé (sa référence à l'IA n'est pas sauvegardée) |
| registres des sondes (C69, C73, C76) | non | sans effet sur le jeu |

## 3. Mesure : graine 42, sauvegarde du 1er janvier 1973 rechargée

`save_load_roundtrip.py --seed 42 --years-a 4 --years-b 2 --mid-fraction 0.75
--arm "OpexAI[probe_portfolio=1]"`, `results/reload_c69c75_seed42.json` (non versionné : 3,7 Mo de
journal ; `LOAD_RECONCILE` présent, `Load()` bien appelé).

| passe | K_dec (C69) | τ (C69) | K_pass (C75) | τ_pass (C75) |
|---|---:|---:|---:|---:|
| avant la sauvegarde (décembre 1972) | 143 k£ | 28 j | 266 k£ | 52 j |
| 1re passe après chargement (février 1973) | **0** | 0 | **0** | 0 |
| 2e passe (avril 1973) | **2 081 k£** | **365 j** | **1 040 k£** | **182 j** |
| 3e passe (juillet 1973) | 1 040 k£ | 182 j | 699 k£ | 122 j |

**Mécanisme.** Au chargement, les listes de dates sont vides. τ = D / N, avec D = 365 jours (la
partie a plus d'un an) mais N qui ne compte que les chantiers ou passes **d'après** le chargement :
- 1re passe : N = 0, donc K = 0 : classement au ROI pur et un seul chantier ;
- puis N = 1 ou 2 : τ vaut 365 ou 182 jours, **13 et 3,5 fois** la valeur d'avant. K_dec atteint
  2 M£ : **tout projet devient « riche »**, le classement passe au profit pur, et C75 enchaîne les
  chantiers tant que la caisse le permet ;
- l'écart se résorbe à mesure que N se reconstitue, soit **pendant environ un an**.

## 4. Second défaut, indépendant du rechargement : l'année 1970 est écrite en dur

`probes.nut` compte les trimestres depuis 1970 (`OpexComputeOperatingCashFlow`, ~ligne 944) et
mesure les jours « depuis le début » à partir du 1er janvier 1970 (`OpexC69ComputeKDec`,
`OpexC75RecordPassDate`, `OpexC75ComputeKPass`, ~lignes 990, 1034, 1057). Les bancs démarrent
toujours en 1970, donc rien ne l'a révélé. Dans une partie qui démarre une autre année :

- **avant 1970** (par exemple 1950) : le nombre de trimestres est négatif, **F = 0**, donc K_dec =
  K_pass = 0 : C69 et C75 sont **inertes jusqu'en 1970** ;
- **après 1970** (par exemple 2000) : D vaut 365 dès le premier jour, donc τ est gonflé toute la
  première année et la neutralité du démarrage disparaît (C69 classe au profit, C75 enchaîne les
  chantiers dès les premiers mois) ; F est moyenné sur des trimestres où la compagnie n'existait
  pas.

L'année de départ est pourtant connue et sauvegardée : `this._startYear` (`main.nut:536-538`,
`persist.nut:379`, `:484`).

## 5. Correctifs proposés (non codés)

1. **Sauvegarder `C69_BUILD_DATES` et `C75_PASS_DATES`** : des tableaux d'entiers (dates), d'au
   plus un an, quelques dizaines d'entrées. K_dec et K_pass sont alors continus au chargement.
2. **Recalculer `C70_MODE_FACTOR` au chargement** à partir des cumuls par ligne déjà sauvegardés,
   au lieu d'attendre le rapport annuel.
3. **Remplacer 1970 par la date de départ réelle** (`_startYear`, déjà sauvegardé) dans les trois
   calculs, via une globale posée dans `Start()`.
4. **Validation** : rejouer le banc du §3 et vérifier que K_dec et K_pass après chargement restent
   dans l'ordre de grandeur d'avant ; smoke au défaut. Pour le point 3, une partie démarrant en
   1950 et une en 2000 doivent retrouver un démarrage à K = 0.

Rien de ceci ne change les bancs (départ en 1970, jamais de rechargement) : pas de nouveau 20×10
nécessaire pour ces correctifs, seulement les vérifications ci-dessus.
