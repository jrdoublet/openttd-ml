# P0 AIR C121 — verdict invalidation exacte et devis recalculés (9 octobre 2026)

## Porte A40×3 terminée : rejet de l'invalidation exacte

Campagne `air_c121_exact_prod_gateA_40x3_20261009_r1`,
fichier `results/air_c121_exact_prod_gateA_40x3_20261009_r1.json`.
Bundle SHA-256 :
`54f5f9f1d83d169ee89617dc1843604d92c17d4ae90a46d05ee1a6b244ad49ac`.
Les deux bras ont la sonde `c121_exact_prod_shadow=1` ; seul le réglage
`c121_exact_prod_invalidation` diffère (OFF référence, ON variante).

- 40/40 paires complètes, 0 partie en échec.
- `profit_year` variante moins référence : moyenne **+22 890,4 £/an**,
  médiane **+6 260,5 £/an**, 21 victoires, 19 défaites.
- Wilcoxon bilatéral **p=0,476207802976** ; IC95 bootstrap du gain moyen
  **[−19 610,2 ; +67 635,375] £/an**.
- Gain utile requis de 4 % du profit référence : **77 883,764 £/an**.
- Valeur d'entreprise : ratio des moyennes **+0,701464 %** ; garde −5 % passée.
- Verdict harness **`fail_primary`**. **Ne pas adopter, pas de porte B20×10.**

Analyse passive des 80 journaux moteur (outil
`sweeps/analyse_c121_exact_prod_cache.py`) :

- **1 527** événements `C121_PROD_CACHE_STALE` dans les références, sur
  **28/40 graines**, contre **0** dans les variantes ;
- répartis en **791** âgés de 0 jour, **505** de 1 à 29 jours et
  **231** de 30 jours ou plus ;
- **1 486** événements hubsite, **24** newpair et **17** hubhub ;
- **163 521** *mentions par batch* de variations sous les seuils historiques.
  Ce dernier chiffre ne représente ni des villes uniques ni des projets.

Découpage observationnel par graine : 28 graines exposées affichent un
delta profit moyen d'environ **+44 521 £/an** (17 victoires/11 défaites) ;
12 graines sans hit stale journalisé affichent environ **−27 582 £/an**
(4 victoires/8 défaites). Ce contraste n'établit **aucune relation causale** :
petits échantillons sélectionnés après observation, trajectoires des deux
politiques déjà différentes, dépenses CPU et rafraîchissements non isolés.

Attention : `C121_PROD_CACHE_STALE` signifie que la production lue diffère
de la **base historique d'invalidation** ; le devis peut avoir été calculé
depuis sous d'autres événements. Compter ces hits comme autant de devis
financièrement faux surinterpréterait les données.

## Sonde supplémentaire : ancien devis vs recalcul naturel

Réglage autonome `c121_quote_refresh_delta_shadow=0` OFF aux quatre
difficultés, actif uniquement en même temps que
`c121_exact_prod_invalidation=1`. Ne modifie aucune décision : quand
`OpexC121CatalogChoice` traite déjà un miss pour révision de ville, conserver
un pointeur local vers l'ancien devis et journaliser une fois le choix suivant
évalué, **sans déclencher un second scan moteur**.

Événement `C121_QUOTE_REFRESH_DELTA` : clé et âge du devis, bras AIR,
production allouée PASS/MAIL aux deux sites avant/après, profit, recette,
capital, moteur et validité avant/après. Champ `only_town` : les autres
révisions visibles dans la clé du parent sont inchangées ; il ne prouve pas
l'absence de variation démographique ou de données cachées.

Validation : 3 tests ciblés en Python hôte et Docker, tous OK ;
`test_analyse_c121_quote_refresh_delta.py` 2/2 hôte OK.
Les tests C121 précédents restent verts.

Smoke `air_c121_quote_delta_smoke_1x3_20261009_r1` : graine 42,
3 ans, source bundle
`78475056d100632eb46eb2cb7a8a43dd62676ee59860633b9cba6a759938d8fc`,
manifest `47ac8e04180f58a41ed9262ed2cea5753e9b4c0cea2ebe1dfd7db2894bf96f03`.
Même politique d'invalidation exacte ON dans les deux bras ; seul le
nouveau log change (OFF/ON). **2/2 parties complètes**, mêmes résultats
économiques : delta `profit_year=0`, valeur entreprise `0 %`. Ce smoke
ne qualifie pas l'invalidation exacte.

Un seul événement naturel `C121_QUOTE_REFRESH_DELTA` dans la variante :

- arm `hubhub`, deux stations réutilisées, ancien devis âgé de **318 jours** ;
- prévision PASS/Mail des extrémités **16/52 et 7/21** auparavant contre
  **7/30 et 4/17** maintenant ;
- recette annuelle prévue **67 116 → 42 864 £** ;
- profit annuel prévu **59 768 → 35 516 £**, soit **−24 252 £/an** ;
- capital inchangé **38 964 £**, moteur identique (`223`) ;
- `only_town=0` : **révisions additionnelles concomitantes** ; attribution
  à la seule variation de production PASS/MAIL impossible.

Ce cas démontre qu'un recalcul peut changer matériellement une cotation,
**pas** que sa cause unique est un seuil de production ni qu'un chantier
aurait été financé/construit autrement.

## Suite

Conserver `c121_exact_prod_invalidation=0`, ainsi que le nouveau
`c121_quote_refresh_delta_shadow=0`. Pas de recherche opportuniste de seuil
et **pas de porte B**. Avant toute nouvelle variante, isoler un événement
où seule la donnée de demande change, conserver toutes les autres entrées
C121 du même projet, puis vérifier l'ordre et la finançabilité au niveau
du portefeuille. Une sonde naturelle de miss est volontairement moins
invasive qu'un recalcul complet sur chaque hit.
