# RVA-10 — détection CargoDist et repli explicite

`ai/OpexAI/rva_distribution.nut:4` lit le mode effectif de chaque cargo via
`AICargo.GetDistributionType` et conserve les réglages pax/mail/default via
`AIGameSettings.IsValid/GetValue`. Un override de cargo n'est pas remplacé par
le réglage global. Aucun cargo fixé par identifiant, aucun appel au défaut.

`OpexRvaExistingFlow` conserve origine et via ensemble ; consommation sur place
et production locale ont les conventions de `script_station.hpp:100–169`.
Un stock n'est pas un flux mensuel, un plan n'est pas une livraison réalisée.
`sweeps/rva_distribution.py:5` borne le débit d'un graphe existant par sa
capacité ; nouveau lien/graphe en formation : bornes [0,min(offre,capacité)],
valeur centrale inconnue et retour explicite à la décision de référence.
Manuel, symétrique et asymétrique ont des contrats distincts testés. Cela ne
revendique pas une prévision des destinations d'un nouveau lien CargoDist.

Source locale 15.3 : `script_cargo.cpp:81–84`, `economy.cpp:1217–1247` : paiement
final et crédit de transfert sont distincts. Aucune somme de crédits VEHS en
recette compagnie, aucun feeder réintroduit. `test_rva_distribution.py:6`
couvre les trois modes, graphe neuf, absence et provenance des lectures.
Compilation/exécution des appels NoAI : MESURE REQUISE, sans blocage aval.
