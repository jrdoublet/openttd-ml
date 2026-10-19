# Réanalyse RVA : ce que coûte l'arrivée d'AAAHogEx dans une de nos villes (19/10/2026)

Expérience naturelle, hors moteur et sans nouvelle partie, sur des données déjà
collectées. Elle répond à l'objection qui avait servi à clore RVA : « le partage
avec les gares voisines n'est pas estimable ». Il l'est, sur les parties.
L'utilisateur avait raison : nos données contiennent déjà ces baisses.

Script : `sweeps/rva_aaa_arrival_air.py` (lecture seule de `line_telemetry`).

## Mécanisme du jeu

`MoveGoodsToStation` (`station_cmd.cpp`, 15.3) répartit la production d'une maison
entre les compagnies qui la couvrent. La part de chaque compagnie est
proportionnelle à sa meilleure note (`rating + 1`). Une maison n'est donc partagée
que si elle est dans **les deux** zones de captage. Avec des notes comparables
(médiane prédite pour nous : 0,45), un recouvrement complet nous coûterait environ
la moitié des voyageurs de ces maisons.

## Plan d'analyse

- **Unité :** une ligne AIR d'OpexAI, identifiée par ses deux StationID, au cliché
  du 1er décembre.
- **Ligne traitée en t :** aucun aéroport AAA dans ses deux villes au cliché t−1,
  au moins un au cliché t.
- **Témoins :** lignes sans aéroport AAA dans leurs villes de t−1 à t+1.
- **Résultat :** profit par avion, `d2 = ppv(t+1) − ppv(t−1)` (exposition
  complète) et `d1` (année d'arrivée, exposition partielle).
- **Modèle :** MCO `d ~ 1 + ppv(t−1) + traité + effets année`.
  - Le contrôle du niveau de départ est indispensable : sans lui, le retour vers la
    moyenne domine. Une différence brute par partie-année donnait −1,2 k£, IC
    [−5,0 k ; +2,5 k].
  - IC95 par bootstrap des parties (grappes).
- **Placebo :** une arrivée fictive en t, alors que l'arrivée réelle a lieu en t+2.
  La période t−1 → t+1 n'est donc pas encore exposée.

## Résultats

| Données | Effet `d2` (£/avion/an) | IC95 | Placebo `d2` | Δ avions |
|---|---:|---:|---:|---:|
| **Aérien seul des deux côtés**, `airseul_20x10` + `v252m2_airseul_20x10` (60 parties, 20 graines), 96 lignes traitées | **−1 694** | **[−3 026 ; −436]** | **+4** [−1 466 ; +1 714] | −0,01 |
| Multimodal, six expositions 3×10 (30 parties, 3 graines), arrivée d'un aéroport AAA, 275 lignes traitées | −3 216 | [−4 057 ; −2 293] | **−2 393** [−3 523 ; −1 084] | +0,02 |
| Multimodal, première station AAA de tout mode, 225 lignes traitées | −1 170 | [−2 470 ; +151] | −357 [−1 525 ; +890] | −0,02 |

- **Estimation propre : aérien seul.** L'arrivée d'un aéroport AAA dans une ville
  de la ligne coûte **≈ −1,7 k£ par avion et par an**, soit **≈ −10 %** du profit
  par avion (base 16,6 k£). Le placebo est nul.
- **La flotte ne réagit pas** : aucun avion retiré ni ajouté.
- **L'année de l'arrivée, l'effet est encore nul** (`d1` +82 £, IC [−1,6 k ;
  +1,7 k]), puisqu'elle mélange les mois avant et après l'arrivée.
- **Multimodal par aéroport :** l'effet est contaminé par une tendance préalable,
  et les trois graines de ces parties ne sont pas indépendantes.
  - AAA arrive dans des villes où nos lignes déclinaient déjà : placebo −2,4 k£.
  - Seules 65 des 498 arrivées d'aéroports AAA suivaient une présence d'AAA dans un
    autre mode : ce n'est donc pas un effet des bus.
  - Effet corrigé du placebo : ≈ −0,8 k£, imprécis.
- **Multimodal, tout mode :** placebo propre et effet compatible (−1,2 k£), mais non
  significatif.

## Dose-effet : non identifiée

- J'ai approché les zones de captage par des rectangles : aéroports d'après
  `table/airport_defaults.h`, autres stations ±3 autour de leur tuile connue.
- 98 à 99 % des lignes traitées ont un recouvrement : AAA et nous visons le centre
  des mêmes villes. Le recouvrement moyen vaut 25 à 31 % de notre zone.
- La perte prédite (recouvrement × (1 − part de note)) a une médiane de 10 à 15 %,
  du même ordre que l'effet moyen mesuré.
- La pente dose-effet change de signe d'un jeu de données à l'autre et ses IC sont
  larges. Le modèle de notes × rectangles donne le bon ordre de grandeur, pas un
  prédicteur par cas : il manque la répartition des maisons.

## Enjeu

- **93 à 96 % de nos avions** (aérien seul) et **77 à 82 %** (multimodal) volent sur
  des lignes qui touchent une ville où AAA a un aéroport.
- À −1,7 k£ par avion, le coût total de la concurrence vaut ≈ **130 à 200 k£/an par
  partie** (1973 → 1979), soit environ 10 % de notre profit aérien.
- Il ne se récupère pas en évitant AAA : il est présent presque partout et dans les
  plus grandes villes. C'est du même ordre qu'un levier qualifié, mais ce n'est pas
  un gisement accessible.

## Conséquences pour RVA

1. **Le motif de clôture est corrigé.** Le partage est estimable et vaut environ
   −10 %, pas une inconnue totale.
2. **La garde de recouvrement de RVA-16** (`rva_policy.nut:44-50`, abstention dès
   qu'une gare existe dans l'emprise) traite une perte d'environ 10 % comme une
   inconnue rédhibitoire. Un abattement de 10 à 15 % du gain local estimé serait la
   version défendable.
   - Il ne ferait passer sous zéro que les lignes rail voyageurs déjà marginales.
   - RVA-16 n'a vu que 17 décisions voyageurs en rail seul 3×3.
   - La transposition de l'aérien au rail (captage 4) est une hypothèse non mesurée.
3. **Recommandation :** ne pas rouvrir RVA-17 sur cette base, car l'enjeu de décision
   est trop faible. Réutiliser l'estimation (−10 % de profit par véhicule quand un
   concurrent couvre la zone) comme abattement dans tout score de site qui en a
   besoin, et garder ce script comme outil de mesure.

## Limites

- Clichés annuels seulement : la date exacte d'arrivée est inconnue.
- Le profit au cliché couvre environ onze mois, avec les véhicules présents.
- Notes AAA lues dans la sauvegarde : l'IA ne voit pas celles d'un concurrent.
  Elle peut en revanche détecter ses stations par `AITile.GetOwner`.
- Rectangles de captage approximatifs. Identifiants de ville de la sauvegarde
  (+1), comparés entre eux seulement.
