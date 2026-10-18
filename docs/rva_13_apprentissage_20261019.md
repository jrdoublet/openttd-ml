# RVA-13 — apprentissage observable, sans fuite temporelle

`sweeps/rva_learning.py:14` conserve seulement des intervalles de séjour
observé et leur instant de fin. Prévision = médiane des séjours comparables
terminés **avant** le début de la rotation prévue. Démarrage sans observation :
physique initiale intacte. Matériel, composition, capacité, gares, session et
ligne changés : contexte différent, donc démarrage froid. Aucune correction du
revenu ou de la demande, ni C70/V212/V216a supplémentaire. Le séjour observé
inclut attente/chargement/perturbations : il n'identifie pas leur cause mécanique.

`analyze_rva_cycle.py:68` ajoute début/fin d'observation et signature de matériel.
`validate_rva_learning.py:25` fixe avant calcul une première moitié chronologique
pour apprendre, puis une seconde moitié pour contrôler. Les rotations traversant
la frontière sont exclues. Aucun apprentissage sur les résultats du contrôle,
ni mélange de graines. Le modèle est une médiane empirique sans coefficient
multiplicatif de recalage, et publie les bornes des observations échantillonnées.

Douze logs des campagnes `rva_cycle_railseul_3x3_20261018` et
`rva_cycle_expo_3x3_20261018` relus, hashés ; 31 rotations avec résidus,
7 rotations entièrement dans la fenêtre de contrôle avec contexte appris.
MAE de durée médiane **9,640 → 16,028 jours**, biais **−7,711 → −1,222 jours**,
WAPE **11,86 → 19,72 %**. L'apprentissage dégrade l'erreur absolue ici : il
**n'est pas activé en jeu**. Très petit échantillon corrélé, intervalles de
visite larges et couverture multimodale insuffisante. Aucun gain économique.
Les anciens logs ne signalent pas un changement de distribution en cours de
partie ; leur contexte de distribution reste incomplet, jamais imputé vanilla.

Preuve `evidence/review/rva_20261019/learning.json.gz` avec les 12 SHA,
coupures, prévisions et intervalles par rotation. Les coûts qui y figurent
sont ceux de l'ancienne sonde cycle : rail seul 2,329 M / 1,768 M / 0,738 M
opcodes partiellement mesurés, pas ceux du nouvel évaluateur RVA-12.
Contrats : `test_rva_learning.py:5`, dates futures ignorées, froid et matériel
nouveau, séparation des distributions et absence de correction monétaire.
MESURE REQUISE pour observations du passif neuf ; cela ne bloque pas le rejeu.
