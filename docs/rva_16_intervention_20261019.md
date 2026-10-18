# RVA-16 — une intervention expérimentale, défaut OFF

`rva_policy=0/1` est l'unique réglage ajouté. Déclaration dans `info.nut:16`,
quatre difficultés à **0**, bornes 0/1 ; lecture unique dans `settings.nut:59`,
globale `RVA_POLICY` initialisée à zéro. Le plafond 80 réglages est respecté.
Aucune famille protégée n'a été modifiée ; V207/V212/V216 sont seulement lus.

## Intervention isolée

`ai/OpexAI/rva_policy.nut:20` estime la demande locale d'un projet rail voyageurs
**autonome**, mono-cargo, manuel, à horloge calendaire et couverture modifiée.
Union réelle des deux quais, rayons API, producteurs des tuiles réellement
couvertes, exclusion des maisons détruites par les quais. Production par maison
= dernier mois ville / nombre de maisons ; poids de producteurs API, contribution
par ville plafonnée à sa production totale. Ce prior suppose des maisons
comparables, il n'est pas une loi moteur ni une garantie NewGRF. Le modèle
complet sur inventaire pondéré est disponible hors ligne en RVA-08 ; les vieux
logs n'en permettent pas la validation locale directe.

Sans recouvrement avec nos gares, le scénario sans rival donne une demande
optimiste pour la ligne ; note future du modèle, capture (note brute+1)/256,
capacité par composition existante, tarif API et revenu annualisé selon le
contrat courant `economy.nut:387–400`. Les coûts annuels après devis sont
soustraits, pas le capital engagé. **Gain estimé ≤0 ⇒ veto avant dépense**.
Pas de recalage appris, de second facteur V216a, de multiplication de profit
par une part de marché ou de remplacement de C41.

Recouvrement propre, jointure de gare, courrier mixte, arrêts joints, V212
revenu hors 100, CargoDist, horloge non couverte, producteur non résidentiel,
API invalide ou budget de calcul insuffisant ⇒ décision de référence.
L'effet réseau manquant n'est jamais remplacé par zéro. Aucun test du nombre
de modes autorisés ou de l'année ne décide de l'activation.

Ce premier consommateur est volontairement plus étroit que l'évaluateur : les
projections réseau et l'apprentissage ayant échoué leurs diagnostics, il ne
les active pas ensemble. Il ne prétend pas encore résoudre la cannibalisation
multimodale. L'expérience est prête pour exposition, **pas adoptée/qualifiée**.

## Preuve statique des achats et inertie

`builder_rail.nut:3427` place la garde paresseuse après devis/rafraîchissement
des sites et avant démolition, construction de gare, voie, dépôt et trains.
À 0, aucun appel au modèle/API/énumération RVA n'est exécuté. Projection exacte
du corps `OpexExecuteRailPlan` en retirant cette seule garde : SHA de tokens
identique à `master` importé **b229674**, `8c61cd26…2325e` des deux côtés.
Preuve complète `evidence/review/rva_20261019/default_inert.json`.
Le contrat historique UR-15a conserve son SHA initial, en retirant exactement
la garde RVA comme il retire déjà celle de V233 ; il vérifie tous les autres
ordres de construction, échecs et rollback.

Témoin `sweeps/fixtures/rva_purchase_witness.json` (synthétique, pas une partie) :
candidat de référence finançable (50 k£ / budget 100 k£), 154 unités/mois,
profit annuel positif **88 419 £**. Sur le site à cinq producteurs après
terrassement, prior local 10 unités brutes/mois → **3 transportées**,
recette 1 800 £/an, coûts 3 981 £/an, gain **−2 181 £/an**.
Avec les précontrôles existants satisfaits, référence = un projet acheté ;
`rva_policy=1` = retour avant toute commande d'achat. Il s'agit d'une preuve
statique de contrôle de flux, pas d'un comptage observé d'achats changés.
`test_rva_policy.py` vérifie le calcul avec le partage indépendant RVA-08,
l'emplacement avant dépense et les deux consommateurs immédiat/reprenable.

Les rejets économiques sont interceptés avant `_recordRailAttempt` : aucune
mémoire d'échec de géométrie/abandon n'est empoisonnée, aucune dépense partielle
à nettoyer. Le chemin reprenable libère sa recherche ; le plan immédiat reste
réutilisable. Aucun nouvel état comportemental à persister.
L'ajout de code peut déplacer les opcodes : l'inertie prouvée porte sur les
choix/logique au défaut, pas sur une identité bit à bit de deux parties.

## Validation

Suite complète depuis la racine : **2 089 tests OK**, 3 ignorés et 8 échecs
attendus ; 68 contrats RVA inclus. `git diff --check` vert, cinq preuves
compactes vérifiées par leurs SHA. Les contrats Python ne compilent pas Squirrel.
Aucun moteur, Docker, banc, push ni modification de `docs/taches.md`.
Compilation Squirrel, Save/Load moteur, coût du nouveau passif, exposition
réelle et nombre d'achats changés : **MESURE REQUISE**, commandes VPS exactes
au rapport. RVA-17/18 restent hors mission. Aucun seuil économique franchi
ou résultat de jeu futur n'est annoncé.
