# RVA-08 — estimateur local et calibration hors échantillon

La seconde passe complète le modèle à blanc de `rva_08_emprises_20261019.md`.
Aucun banc neuf. NewGRF réel reporté à RVA-17 par décision utilisateur.

`sweeps/rva_demand.py:17` applique le partage 15.3 : production × (meilleure
note brute + 1)/256, parts des compagnies proportionnelles à leur meilleure
note, puis parts de leurs gares proportionnelles à toutes leurs notes.
Source locale OpenTTD 15.3 : `station_cmd.cpp:4599–4679`, fractionnement
`:4408–4410`. Ce n'est pas un partage uniforme entre les deux meilleures gares.
Les notes NoAI sont des pourcentages arrondis (`script_station.cpp:149–154`) ;
leur conversion en note brute est une estimation. Une note adverse inconnue
exige des scénarios explicites. Éligibilité, droits exclusifs et service sélectif
restent des préconditions, pas des gares automatiquement admises.

`sweeps/rva_demand.py:54` répartit la production mensuelle de chaque ville/cargo
sur son inventaire COMPLET de producteurs pondérés par le compte API.
L'hypothèse initiale est une production identique par producteur. Ce n'est
pas une formule moteur : maisons hétérogènes/NewGRF peuvent la contredire.
L'emprise est l'union réelle des tuiles et les producteurs communs sont
alloués une fois. Voyageurs/courrier et chaque ville ont leur inventaire.
Aucun coefficient 22 %, 40 %, 150/85 ni soustraction de supplied : le partage
par notes a déjà réduit le cargo. Capacité/stock interviennent ensuite dans
le débit et l'effet sur les services, pas dans la production.

## Diagnostic mesuré et limites

Avant exécution : séparation déterministe par graines entières triées,
indices pairs apprentissage, impairs contrôle ; même graine dans les quatre
cellules toujours du même côté. Dix graines de chaque côté, 80 journaux
V216 sondés archivés, lecteur `analyze_v216.parse_log` étendu au gzip.
Commande : `python3 sweeps/calibrate_rva.py <S1_engine> <S2_engine> --out <neuf>`.
S1/S2 sont `v216_sonde_aaacomplet_20x3_20261016` et
`v216_sonde_aaarail_20x3_20261016`, sous l'archive `wt-v216-probe/results`.

Calibration : médiane des notes voyageurs de gares rail sans aéroport,
**62 % sur 3 357 relevés des seules graines d'apprentissage**. Pas une nouvelle
constante déployée ; le futur évaluateur conserve la note physique du candidat.
Sur les clichés anciens, projection agrégée avec une gare propre et un rival
de même note sur les tuiles adverses seules, étiquetée comme scénario.

| Contrôle hors échantillon | Référence | Projection calibrée |
|---|---:|---:|
| Lignes voyageurs 1971, ≥180 j | 19 | 19 |
| Erreur absolue moyenne de recette annualisée | 9 271 £/an | 6 870 £/an |
| Biais prévu − réalisé | +6 304 £/an | +6 445 £/an |
| WAPE | 140,85 % | 104,38 % |

Apprentissage (15 lignes) : MAE 8 335 → 8 168 £/an. Résultat médiocre,
aucune sélection de meilleur coefficient après contrôle, aucune qualification
économique. Recette réalisée annualisée et ramenée aux trains initiaux via le
lecteur V216 actuel ; cycles/lignes ne sont pas des graines indépendantes.

**Erreur locale en unités/mois non identifiable dans ces anciens logs** : ils
n'ont ni inventaire complet des producteurs ni livraisons locales. L'erreur
mesurée ci-dessus est celle de la projection de recettes, pas une validation
du volume par tuile. L'implémentation exacte sur inventaire explicite est
couverte par contrats ; les mesures d'emprise live restent requises à RVA-17.
Cette limite n'empêche plus la définition du modèle et les travaux aval.

Preuve : `evidence/review/rva_20261019/calibration.json.gz`, index/hashes et
80 SHA de sources incorporés. Tests `test_rva_estimator.py` : partage par
compagnie, gares jointes, emprises disjointes/partielles, inconnus et zéro.
Aucun achat, score ou réglage modifié dans cette tâche.
