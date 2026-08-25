**Question.** Peut-on prédire le profit d'une ligne ferroviaire à partir de ses caractéristiques
de construction, sans simuler la partie ?

**Unité d'observation.** Une ligne construite (couple villes × cargo × matériel × nombre de rames).

**Métrique.** MAE sur le profit annuel moyen.

**Baseline.** Profit médian du jeu d'entraînement.

**Protocole de split.** Par graine, jamais par ligne : deux lignes d'une même partie partagent
le monde, la conjoncture et la concurrence.

**Critère de réussite.** Battre la baseline de 20 % en MAE, sur des graines jamais vues.
