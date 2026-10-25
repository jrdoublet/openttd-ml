# AIR-MONOPOLY-1 — valeur défensive d'un aéroport, preuves rétrospectives

**25 octobre 2026 — synthèse documentaire sur les bancs existants ; aucun code IA ni banc supplémentaire.**

L'hypothèse proposée est une note de projet compétitive : au profit privé futur
d'un aéroport s'ajouterait le profit que l'entrée retire à AAAHogEx. Le raccourci
« doubler le profit du nouvel aéroport » suppose implicitement que chaque livre
gagnée par OpexAI enlève exactement une livre à AAAHogEx au même horizon.
Cette hypothèse n'est pas établie.

## Ce que les campagnes existantes mesurent

- [Air early-slot, 20×10](07_air_early_slot_causal_analysis.md#2-décision-économique-déjà-prise) :
  le classement précoce de projets **déjà rentables** fait passer le profit annuel
  moyen OpexAI de 1 330 712 à 1 485 068 £ (+154 356 £/an, +11,6 %).
  La politique sélectionne des projets économiques et ne crée pas d'aéroports
  vides pour défendre un créneau.
- [Étude des marchés early-slot, §8](07_air_early_slot_causal_analysis.md) :
  en 1979, les marchés propres au témoin d'AAAHogEx représentent environ
  2,00 M£/an, mais ceux propres à la variante environ 1,80 M£/an.
  Les marchés perdus sont donc largement **remplacés** et les trajectoires de
  compagnies divergent ; le retrait de profit au rival n'est pas la simple
  valeur du marché initialement pris. Ce rapprochement de marchés est descriptif.
- [C83-6, 20×10](22_c78_lignes_vs_aaa.md#qualification-causale-20-10-du-défaut-final-à-6-villes) : le profit annuel d'OpexAI
  augmente en moyenne de **165 329 £/an** et celui d'AAAHogEx diminue de
  **314 729 £/an**, d'où un écart compétitif amélioré de **480 058 £/an**.
  Les villes avec deux aéroports AAA et aucun Opex passent de **215 à 178**
  à fin 1979. L'écart concurrentiel agrégé vaut ici ~2,90 fois le gain privé
  agrégé (480 058 / 165 329) ; ce **n'est pas** un coefficient par projet.

## Ce qui manque pour une note défensive exploitable

Les comparaisons portent sur des **politiques entières** et des trajectoires de
portefeuille, pas des créations d'aéroport isolées. Elles ne séparent ni le
profit incrémental d'une ligne de son coût réel et de ses renforts, ni l'effet
sur les alternatives que le rival construit ensuite. On ne peut déduire ni
un partage 300/150 k£ pour une ville, ni un coefficient universel ×2.

Avant de classer une création AIR sur cette base, apparier les créneaux et
villes **au même monde et au même instant**, identifier le rival et son
occupation effective, les alternatives financées et bâties, puis contrôler
par fourche même sauvegarde (AA/AA avant intervention) le différentiel
`profit_year(OpexAI) − profit_year(AAAHogEx)` et les coûts d'opportunité
sur un horizon mature. Distinguer les nouvelles villes des hubs et des renforts,
et conserver la garde de rentabilité privée. **Aucun ×2 proposé à l'adoption.**
