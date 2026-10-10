# Critères d'acceptation — simplifications économiques et opcodes

Décision de l'utilisateur du 10 octobre 2026 : utiliser ces critères pour
**les futures expérimentations** remplaçant des « nombres magiques » par un
calcul causal, sans ajouter de complexité inutile au modèle de décision.

## Contrat prédéfini avant chaque banc

1. **Économie : non-infériorité**. Mesure primaire : `profit_year` en fin
   d'horizon, différences **ON−OFF appariées par graine**. La borne
   inférieure unilatérale à **95 %** du changement relatif de profit
   doit dépasser **−1 %** de la référence. Un gain est accepté : le but
   n'est **pas** l'égalité parfaite. Vérifier séparément une garde de
   `company_value` de **−1 %** avec le même principe de confiance.
2. **Opcodes : pas de surcoût significatif**. Sur **des états et nombres
   d'appels identiques**, comparer les opcodes de la formule ou du chemin
   modifié. La borne supérieure unilatérale à **95 %** du surcoût relatif
   doit être **inférieure à +1 %**. Conserver un contrôle séparé de la
   charge réelle et de la couverture des postes du CPU. Les compteurs
   partiels de jeu (SIGN) ne suffisent pas à conclure sur le CPU total.
3. **Protocole apparié**. Même source figée, mêmes paramètres, mêmes
   graines et adversaires dans les deux bras, à une seule variable près.
   Priorité à un **40×10 sur graines inédites**, avec une deuxième série
   si l'intervalle reste trop large. Fixer avant lancement la population,
   la durée, le critère, le seuil, la méthode d'IC et les gardes.
4. **Interprétation**. Un p-value > 0,05 n'est pas une preuve de neutralité ;
   faire un **test de non-infériorité** avec intervalle et marge fixée
   avant d'observer les résultats. Toute combinaison a posteriori de
   plusieurs panels est qualifiée d'**exploratoire**. Distinguer
   explicitement « objectif non démontré » et « régression prouvée ».
5. **Simplicité**. Ne pas ajouter dans l'IA de seuils, compteurs persistés,
   écarts types ou mécanismes de validation sophistiqués uniquement pour
   satisfaire un test. Les seuils d'acceptation appartiennent au **harnais
   et à la documentation**, pas à l'algorithme embarqué.

Ces marges **−1 % économique / −1 % valeur / +1 % opcodes** sont des seuils
d'ingénierie proposés et **retenus pour les prochains essais** ; ce ne
sont ni des résultats issus des données ni des exigences de la simulation.
Les témoins de sécurité (Save/Load, comportement à froid, fallback et
absence de double correction) restent éliminatoires indépendamment des
mesures financières et des opcodes.
