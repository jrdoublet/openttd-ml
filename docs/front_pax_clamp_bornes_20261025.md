# FRONT-PAX-1 — preuve rétrospective du clamp RAIL→AIR

25 octobre 2026. **Analyse hors moteur seulement** : aucun filtre, classement,
paramètre ou code Squirrel n'a été modifié. Cet audit porte sur le calcul des
bornes voyageurs PASS, **pas** sur le fret RAIL.

## Source et protocole

80 jeux historiques de calibration `1970–1979`, 40 SOLO + 40 DUEL :

`results/calibration_pc_20261021/results/calib_{solo,duel}_40x10_pc_20261021_engine/`

Reproduction (chemins réels explicités) :

```powershell
python -X utf8 sweeps/diag_front_pax_clamp_bounds.py `
  --logs results/calibration_pc_20261021/results/calib_solo_40x10_pc_20261021_engine `
  --logs results/calibration_pc_20261021/results/calib_duel_40x10_pc_20261021_engine `
  --out results/front_pax_clamp_certain_20261025.json
python -X utf8 -m unittest discover -s sweeps -p test_diag_front_pax_clamp_bounds.py
```

Le code `ai/OpexAI/candidates.nut:315–327` calcule le croisement avant clamp :

`d = tFixe / (4096/(74·1,6·vRail) − 4096/(74·1,6·vAir))`

La sortie `EPOCH_BOUNDS` journalise `vAir.tointeger()` et
`tFixe.tointeger()` ; nous ne les traitons **pas** comme exacts, mais
respectivement comme `[vAir, vAir+1)` et `[tFixe, tFixe+1)` pour des valeurs
positives. La vitesse `vRail` textualisée est admise à ±0,01, plus large que
sa précision affichée. La durée par tuile utilise 74 ticks/jour, valeur fixe
vérifiée dans `OpexTicksPerDay`. Le résultat entier est calculé avant les
bornes `roadMax…railMax`.

La borne basse la plus favorable au rail-air court emploie la plus lente
vitesse RAIL plausible, la plus rapide AIR plausible et le plus petit temps
fixe. Ainsi, **si son entier est strictement supérieur à `railMax`**, le
résultat original était nécessairement supérieur à la limite et le code a dû
rabattre la frontière à `railMax`. Les autres configurations restent
`unknown` ; ne jamais imputer un motif sans intervalle entièrement conclusif.

## Observations certifiables

| Mesure | Résultat |
|---|---:|
| Jeux distincts parcourus | **80** (SOLO + DUEL) |
| Événements EPOCH_BOUNDS distincts dans ces journaux | **1 524** |
| Émissions `EPOCH_BOUNDS` brutes, copies `.log`/`.gz` dédoublonnées | **2 109** |
| Réémissions même partie, jour et payload | **585** |
| Événements dont le clamp haut RAIL→AIR est prouvé | **1 524 / 1 524** |
| Contradictions de clamp avec `railAir` final | **0** |
| Première observation-type : vitesse RAIL / avion efficace journalisés | **115,88227 / 144** |
| Première observation-type : temps fixe tronqué | **26 jours** |
| Première observation-type : croisement brut sous incertitude | **[433,52 ; 463,39] tuiles** |
| Valeur finale observée | **`railAir=railMax=200`** |

**26/10 — rectification du dénominateur :** les **2 109** sont bien les
émissions brutes `EPOCH_BOUNDS` de ces **mêmes 80 journaux**, tandis que
**1 524** sont les états distincts `(partie, jour, contenu)` conservés par
le rapport historique. **585** émissions supplémentaires répètent un état
identique plus tôt dans la journée, même après des événements intermédiaires ;
elles peuvent correspondre à des recalculs effectifs distincts. La ventilation
brute par motif et par année, ainsi que celle des réémissions, est dans
[`front_pax_emissions_solo_duel_20261026.json`](../results/front_pax_emissions_solo_duel_20261026.json).
Le classement du clamp reste **1 524/1 524 états distincts** prouvés et
**2 109/2 109 émissions** classées hautes, sans contradiction. Ne pas
interpréter ces fréquences comme le nombre de projets, de décisions utiles
ou de changements de frontières, ni étendre la conclusion à d'autres cartes.

## Ce qui demeure inconnu (case FRONT-PAX-1 maintenue ouverte)

La sortie `roadMax=roadMin=7` peut correspondre à une absence de moteur,
un `deltaM` nul/négatif, un dénominateur ou numérateur non positif, ou une
distance brute calculée inférieure au minimum. Ces quatre motifs ne peuvent
pas être départagés par `EPOCH_BOUNDS` : il faudrait une sonde passive **une
fois par rafraîchissement de bornes**, sans changer aucun filtre, publiant
les termes intermédiaires et leur coût opcode. Les champs loggés ne disent
pas non plus quels projets PASS non sélectionnés seraient devenus faisables
avec une autre frontière. Aucun verdict économique ou adoption n'en découle.

Le contrôle hôte a **11 tests** dont émissions identiques séparées par
un autre événement, états différents le même jour, copie texte/gzip conforme
ou contradictoire, preuve du clamp, classification incertaine et contrat
source des troncatures.
