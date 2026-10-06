# Aérien : ce qui sépare OpexAI d'AAAHogEx (2026-09-29)

**Statut : analyse passive, aucune partie lancée, aucun code modifié.** Objectif (décision
utilisateur du 2026-09-29) : **rattraper AAAHogEx** ; la valeur d'entreprise n'est pas un
objectif et le profit d'OpexAI n'est qu'un moyen.

Sources :

- télémétrie par ligne de deux duels 5×6 contre AAAHogEx déjà enregistrés sur le VPS :
  `results/lineprofit_default_5x6_20260926.json` et `results/lineprofit_costprobe_5x6_20260927.json`
  (champ `line_telemetry`, instantanés de décembre, graines 42/100/999/1234/5678) ;
- lecture du code local `ai/AAAHogEx-115/` (analyse agy, citations vérifiées à la main) ;
- sonde passive C116 sur la trajectoire C115, `results/diag_c116_probe_vps_3x4_20260929.json`.

⚠️ **Limites.** Les deux duels sont **antérieurs à C115 par défaut** (27 septembre) : ils décrivent
bien AAAHogEx et la valeur réelle de chaque moteur, pas la trajectoire OpexAI actuelle. Les
comparaisons sont transversales (lignes et aéroports déjà construits), donc non causales : les
grandes villes reçoivent plus de lignes. Le taux de remplissage réel n'est pas mesuré directement ;
passagers en attente et note de gare n'en sont que des indices.

## 1. Mesures (lignes aériennes existant depuis au moins un an)

Duel du 26 septembre, 5 graines × 6 ans ; moteur identifié par la capacité passagers par avion.

| | OpexAI | AAAHogEx |
|---|---|---|
| Profit par ligne (médiane) | 15,9 k£ | **108,5 k£** |
| Profit par avion (médiane) | 14,8 k£ | **49,2 k£** |
| Avions par ligne (moyenne) | 1,2 | **2,4** |
| Note de gare passagers, minimum des deux bouts (médiane) | 160 | 108 |
| Passagers en attente, maximum des deux bouts (médiane) | 9 | **78** |
| Lignes par aéroport (1975) | **7,8** (jusqu'à 12) | **1,0** |
| Aéroports / villes desservies (1975, moyenne par graine) | 24 / 23 | **41 / 34** |

- Le profit par ligne d'OpexAI **s'effondre** avec l'expansion (64 k£ en 1971 → 13 k£ en 1975) ;
  celui d'AAAHogEx reste stable (~100 k£).
- Chez AAAHogEx, le profit **par avion croît** avec le nombre d'avions de la ligne (29 k£ à 1 avion,
  49 k£ à 2, 56 k£ à 3, 70 k£ à 5). Chez OpexAI il reste plat (~12–14 k£), y compris aéroport par
  aéroport quel que soit le nombre de lignes du hub.
- Chez OpexAI, le **223** (220 places, 39 k£) rapporte **25 k£/avion** contre **12 k£** pour le
  **217** (90 places, 33 k£), alors que le 217 équipe 540 lignes-années sur 962.
- AAAHogEx exploite aussi des **avions courrier seul** (105 lignes-années ; ~92 k£/ligne médian).
- Le duel du 27 septembre donne la même structure (7,6 lignes/aéroport contre 1,0).

## 2. Mécanismes d'AAAHogEx (code vérifié)

1. **Chargement complet aux deux bouts** : `isDestFullLoadOrder = true` (`air.nut:201`),
   `isSrcFullLoadOrder = true` (`route.nut:1871`), `OF_FULL_LOAD_ANY` (`route.nut:2137`).
2. **Estimation à capacité pleine, attente comprise** : revenu par rotation = capacité × tarif dans
   les deux sens + **soute courrier réelle du moteur** (`estimator.nut:287-306`) ; le temps pour
   remplir l'avion (`waitingInStationTime`, `estimator.nut:273-281`) est ajouté au cycle
   (`estimator.nut:56`). La capacité agit donc linéairement tant que la production suit.
3. **Point à point strict** : un aéroport ne se partage pas entre deux lignes passagers aller-retour
   (`air.nut:742-745`) ; pas de correspondance aérienne. Il ouvre donc de nouvelles villes.
4. **Deux avions dès l'ouverture**, le second au hangar opposé (`route.nut:2232-2237`, `2995`), puis
   ajout selon les passagers en attente et la note (`route.nut:2906-2915`).
5. **Choix du moteur et des projets par une seule valeur**, dont le dénominateur change avec la
   ressource rare : capital (ROI, coût d'opportunité du premier voyage inclus), temps de chantier,
   ou véhicule (`estimator.nut:80-92`).
6. Concurrence (corrigé le 2026-10-02, relu dans `place.nut:1934-1950`) : **pas** de division par
   le nombre de concurrents. Sans route AAA sur ce cargo, la production estimée vaut
   `70 × production / (% transporté le mois dernier + 70)`, en supposant un seul autre
   transporteur. Sinon, elle est divisée par le nombre de routes source d'AAA elle-même (+1 si la
   route n'est pas encore à elle). `otherCompanies` (`!A || A ? 0 : 1`) vaut toujours 0 : ce
   n'est pas un comptage de gares adverses.

## 3. Écarts du modèle OpexAI qui en découlent

- **Capacité** : le modèle OpexAI transporte `min(demande × note(intervalle), capacité)`, la note ne
  dépendant que de l'intervalle entre passages ; sur la sonde C116, la capacité ne limite que dans
  **4 à 12 %** des décisions. Le 217 gagne donc presque toujours contre le 223. C'est le défaut que
  le replay C115 compense par accident (trajets allongés → capacité limitante), et que C106/C123
  (descentes 223→217) ont confirmé.
- **Note de gare** : le modèle prédit ~13–23 % (sonde C116), alors que les notes réelles d'OpexAI
  sont ~160/255 ≈ 63 % et celles d'AAAHogEx ~108/255 ≈ 42 % avec stock en attente. Écart d'échelle
  à vérifier (la définition de `monthlyPax` peut le compenser en partie).
- **Courrier** : forfait de 15 % du tarif passager, indépendant de la soute réelle.
- **Structure** : hubs (7–12 lignes sur un aéroport) à un avion par ligne, au lieu d'ouvrir des villes.
- **Chargement complet** : C81 (`air_full_load`) coûtait −37 à −54 % **en solo**. Hypothèse non
  testée : avec 7 à 12 lignes se partageant les passagers d'un même aéroport, attendre le plein ne
  peut pas fonctionner ; le chargement complet suppose la structure point à point.

## 4. Pistes (non mesurées causalement)

1. Ne plus chercher une règle de choix qui remplace C115 : **corriger le modèle de revenu**
   (capacité pleine + temps d'attente de remplissage + soute courrier réelle), ce qui supprime la
   raison d'être du timing faux.
2. Tester ensemble, et non séparément, **point à point + chargement complet + 2 avions initiaux +
   ajout sur stock**, contre le défaut, sur la métrique de rattrapage.
3. Mesurer au passage l'effet de C115 lui-même sur l'écart avec AAAHogEx (jamais fait).
