# V166 — audit des rames fret, 13 octobre 2026

Audit demandé après le diagnostic rail contre rail 20×3, puis clôturé sur demande
« Finis ». **Aucune partie nouvelle, aucun changement de comportement ou de défaut.**
Les travaux de scores parallèles restent préservés. HEAD au début de l'audit :
`7ecbabe` ; les **72 fichiers OpexAI correspondent octet par octet** au manifeste
du banc `v166_rail_vs_rail_20x3_20261013_r1` (source `d00ba50`, bundle `4ac6f43d`).

## Conclusion

Le dimensionnement initial est un calcul explicite fondé sur la production et le
temps de trajet ; il ne cherche pas l'optimum économique parmi plusieurs longueurs
de rame. Après construction, les rames charbon observées gardent leur capacité,
même lorsque la ligne reçoit un second train. **Cela identifie un mécanisme à
mesurer, pas une erreur économique démontrée ni une autorisation d'activer
`rail_expand`.** Les marchés desservis diffèrent aussi de ceux d'AAAHogEx.

## Chaîne de calcul vérifiée

| Étape | Comportement courant | Source |
|---|---|---|
| Offre fret | Production du dernier mois de l'industrie source, transmise à l'économie | `candidates.nut:1740` |
| Rame initiale | `ceil(0,50 × production / (capacité wagon × trajets chargés/mois))`, puis correction avec la vitesse de cette rame | `economy.nut:219` |
| Trajets fret | `30 / durée aller-retour` ; cette durée modélisée ne contient pas un terme explicite d'arrêt pour charger | `economy.nut:80` |
| Offre et fréquence | Rating dynamique ; temps de chargement estimé utilisé dans le headway effectif de la note | `economy.nut:302` |
| Nombre de trains | Comparaison de 1 et 2 trains, ROI sous le faisceau économique actif ; pas une recherche sur tous les nombres de wagons | `economy.nut:302` |
| Quai | Taille souhaitée dérivée de la rame avec deux wagons de marge ; recalcul après quai effectivement trouvé | `catalog.nut:49`, `builder_rail.nut:1867` |
| Tracé | Recalcul avec longueur A* réelle après recherche | `builder_rail.nut:1926` |
| Construction | Contrôle de longueur nominale puis longueur réelle du matériel ; plein chargement fret à la source | `builder_rail.nut:1593` |
| Croissance | Ajout de wagons derrière `rail_expand=0` ; second train/voie par chemin distinct | `task_rail.nut:729`, `info.nut:1615` |

Le facteur 50 % vient d'une calibration historique passagers citée dans le code.
Cette origine n'est **pas une preuve actuelle** de pertinence pour le fret. Le modèle
de vitesse/accélération C41 est bien présent et conservé. L'absence de terme de
chargement dans le cycle n'établit pas seule un biais : une file de marchandises
peut écourter l'attente, tandis que la note et la concurrence changent l'offre.
Il faut mesurer le cycle et le stock pour trancher, sans remplacer ce modèle par
une simple vitesse maximale ni rétablir une ancienne ancre rejetée.

## Mesures sur les traces existantes

Jointure stricte `graine + LineID` des constructions et événements
`STATION_FIRST_VEHICLE`, puis **les deux StationID exacts** dans la télémétrie.
Le label cargo est celui de l'API journalisée. Aucune attribution à la gare voisine.

- **445/517 observations annuelles de services Opex appariées** ; 72 non appariées
  restent inconnues. Les véhicules sans ordres résolus ne sont pas reconstruits.
- **162 observations charbon appariées** : capacité moyenne par train / nombre
  de wagons journalisé à la construction = **30 unités dans les 162 cas**.
  La capacité observée est cohérente avec les wagons effectivement livrés. Cette
  jointure ne dit pas si un quai avait réduit une proposition antérieure au log.
- **52 lignes charbon** appariées aux deux bornes 1970 et 1972 : **52/52 gardent
  la même capacité moyenne par train**, **21/52 augmentent leur nombre de trains**.
  Cohorte de services survivants, pas ensemble de toutes les occasions d'investir.
- **44 rapports charbon matures** (âge ≥2, nombre de trains égal au nombre livré)
  donnent un ratio revenu réalisé/prédit médian **0,857**, moyen **0,827**,
  intervalle observé **0 à 1,428**. Le revenu réel est celui reconstruit par
  `_reportLines` (profit passé + coût courant), pas une mesure directe des paiements.
  Même nombre de trains ne garantit pas une flotte inchangée durant l'exercice.
  Ce contrôle ne démontre ni saturation ni profit marginal d'un wagon supplémentaire.

Le [banc initial](v166_rail_vs_rail_20x3_20261013.md) reste la source de la comparaison
avec AAA : charbon 69,5 contre 247,7 unités/train sur 19 graines lisibles, distances
Manhattan médianes des gares 72 contre 98,5. **Les marchés ne sont pas appariés** :
ce contraste ne permet pas d'attribuer le profit à la seule longueur des rames.

## Ce que les données ne permettent pas de conclure

Le banc n'a pas conservé les sauvegardes (`retained_savegames=null`), ni extrait
les panneaux existants `PK/PT/OT/PL/PD` : production d'entrée, cycle prévu,
longueur de quai souhaitée/réelle et contraintes physiques ne peuvent pas être
reconstitués exactement. Aucun événement `LINE_PROFIT` n'est présent.
`max_waiting_cargo` est le **maximum depuis le dernier calcul de note**, pas le
stock instantané ; les premiers passages en gare ne sont pas des cycles mesurés.
Remplissage, temps d'attente, production accessible actuelle, part captée et
rendement du wagon alternatif restent donc **non mesurés**.

**Audit clos ; correctif non justifié à ce stade.** L'étape utile suivante serait
une collecte ciblée sur ces mêmes grandeurs, en réutilisant les panneaux et le
harnais, puis un contrefactuel sur une ligne réellement contrainte. Elle n'est
pas lancée. Aucun nouveau coefficient 50 %, seuil, longueur, `rail_expand`,
worker V149 ou remplacement de C41 n'est proposé à l'adoption.

## Reproduction et validation

- [Analyse détaillée](../results/v166_rail_consist_audit_20261013.json).
- Script passif : `python -B -X utf8 results/audit_v166_rail_consists_20261013.py` ;
  réutilise `analyse_rail_freight_dlog.decode_line` ; assertions de sources figées,
  identités de constructions, unicité de jointure, labels et cargaisons exécutées.
- [Archives et SHA-256](../evidence/review/v166_rail_consist_audit_20261013/index.json)
  du script et du résultat ; preuves brutes dans le paquet V166 initial inchangé.
- Vérification documentaire et `git diff --check`. Aucun nouveau test moteur,
  smoke, A/B, commit ou push pour cet audit.
