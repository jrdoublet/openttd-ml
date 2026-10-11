# C121 observation growth :100×3

Demande utilisateur100 graines×3 ans. Référence OpexAI[c121_air_observation_growth=0], variante OpexAI[c121_air_observation_growth=1]. Code courant3bccc8b, aucun changement IA ; autres défauts communs, notamment ouverture un/deux avions. Catégorie comportement : un renfort par rapport annuel positif sous cible, marqueur c121GrowthReportYear.

Smoke causal42×1 puis200 duels, une répétition,100 graines tirées sans remise avec random.Random(20261011100), plage[1,100000000[ :

49256198, 40251535, 83661327, 67252909, 32954122, 61277276, 42289106, 31095326, 99947065, 48078806, 46817788, 84959643, 41065124, 96072607, 95103928, 77555843, 75791398, 4534239, 31766200, 81255172, 77038974, 84707446, 97761736, 9145132, 4293350, 53511174, 63258888, 13866363, 59126129, 95527813, 59206776, 18513410, 45211130, 95035196, 28657101, 15771828, 1206141, 15816523, 95940230, 2858502, 13097225, 22674892, 93203227, 73632834, 82622549, 88273420, 52918548, 27220949, 19282185, 64212962, 85577990, 25855129, 32226662, 63716307, 61492693, 3667773, 78914873, 31142783, 11027787, 85387996, 25989308, 38463564, 40702905, 85871141, 18184773, 71257234, 72696364, 823553, 50828053, 93987135, 55466383, 79432432, 39381698, 46336057, 14232081, 41998381, 12179205, 34425505, 50783799, 12583287, 86457249, 99736907, 86247171, 77435569, 1972841, 52098057, 77972755, 97998084, 78967085, 49383685, 20729563, 30983659, 49003797, 12703369, 77549383, 39603104, 14337478, 16822043, 32727518, 87391028

Primaire profit_year Opex ON−OFF terminal, quatre trimestres valides. gain_short avec required-seeds100 et required-years3 ; Wilcoxon exact bilatéral p<0,05, borne basse IC95 bootstrap moyenne>0 et gain>=4 %. Garde ratio moyen des valeurs>=0,95. Bootstrap20000 graine0. Profil local10 CPU/8g RAM/swap8g/10 workers, volume cache standard. Campagne observation_growth_100x3_20261011_r1. Pas de répétition favorable, B ou adoption implicite. Défaut0 conservé.

## Suivi

Smoke2/2 sain, puis100×3 lancé :200 duels à10 workers. Bundle63e16d30a3d97e1a2cac457eb9e7b7ca5844189375155e10002e76ddd2ca9acc, manifest7bfc0848b095a1c9cf824ea64e3c915bf8fa5244726912e4e3b8117e2d3e5a1c. Résultats en attente dans results/observation_growth_100x3_20261011_r1.json ; conteneur observation-growth-100x3-20261011-r1. Le premier appel smoke a été refusé avant toute partie pour option de garde manquante, corrigée à5 %.

## Résultat final vérifié

200/200 duels sains,100/100 paires complètes ; comparaison, échantillon et couverture complets.200 observations Opex terminales avec quatre trimestres valides. Profit annuel ON−OFF −50 966,43 £/an (−2,83281 %), médiane −68 779,38V/62D ; IC95 bootstrap [−88 785,43 ; −12 278,52], Wilcoxon p=0,006692. Valeur ratio des moyennes0,94858 (−5,142 %), garde−5 % échouée. Verdict brut fail_primary_and_value_guard. Perte statistiquement étayée, défaut0 conservé ; aucune B/adoption/commit/push.

## Retrait du paramètre après rejet utilisateur

Suppression demandée le11/10 après100×3 fail_primary_and_value_guard. Réglage c121_air_observation_growth, globale, chargement, branche de cadence annuelle, refus spécifiques et deux écritures c121GrowthReportYear retirés. Tests exclusifs supprimés, diagnostics et fixture numérique adaptés. Cadence historique et variantes premier renfort préservées, gardes marginales intactes. Save/Load générique inchangé : une ancienne clé c121GrowthReportYear peut rester dans une sauvegarde chargée, sans aucun lecteur ni effet ; aucune migration nécessaire.80 contrats verts, smoke cleanup_observation_growth_smoke_20261011_r1 (42×1) sain, bundle248ec7c6a968cfdff7f657b523e9dfaf78cbdb959d0c61595bf77df07b2178b5. Aucun gain économique du nettoyage revendiqué. Aucun commit/push.
