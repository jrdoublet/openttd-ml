# N75 AIR TRUE QUOTE — variante précoce isolée (25/10/2026)

## Hypothèse pré-enregistrée avant essai moteur

Objectif général : ratio de profits OpexAI/AAAHogEx >= 75 % en partie complète
1970–1979, 256×256, 20×10 ou 40×10. Base master `83e436cc` : 56,5519 %
en ratio de moyennes, médiane des ratios appariés 58,9112 % (20×10).

L'estimation du prix du projet AIR « flotte +1 » utilise le moteur de l'avion
existant (`task_air.nut`), alors que `OpexAirAddPlane` peut en choisir un autre
par V252. Sur cinq journaux de référence instrumentés 1970–1972, 53 renforts
1→2 ont réellement choisi un nouveau moteur, avec prix catalogue variant de
32 812 à 153 808 £ contre un devis ancien observé de 38 964 £.
Ce comptage descriptif n'est **pas** un profit causal récupérable.

La seule décision modifiée par le réglage expérimental `n75_air_true_quote`
est le **coût finançable et le classement** du projet de renfort déjà éligible
en 1970–1972 lorsque la ligne compte exactement un avion, est sous sa cible
C121, et V252 choisit un moteur de prix différent. Le modèle de profit C121,
le calibrage V161, la demande, la cadence, les gardes physiques, le K_pass C75,
le plancher C80, la priorité C77 et les réserves restent ceux du master.
Il ne s'agit ni d'AIR_GROW ni de V217. Ne pas présenter le ROI modifié comme
rendement économique réel du nouveau modèle : la capacité/maintenance de
l'ancien avion restent dans le modèle de marge, et l'ancienne A AIR_GROW est
`fail_primary`.

Réglage opt-in `0 OFF` (défaut easy/medium/hard/custom), `1 SHADOW` (compare
ancien/nouveau devis sans modifier achat/rang), `2 ON` (utilise nouveau prix
au portefeuille). La cotation V252 est mise en cache **au maximum une fois par
mois, ligne et moteur existant** et le cache est transitoire (purge à changement
de mois et au chargement des réglages). Avant l'achat ON, revalider le moteur
et le prix cible ; si V252 retombe sur l'ancien modèle, revalider ses coûts
contre la caisse et la réserve. Le moteur/prix catalogue effectivement acquis
est loggé sous `N75_QUOTE phase=built` ; une trace `phase=plan` ou `execute`
n'est pas une preuve de construction.

## Étapes bloquantes et critères de décision

1. Contrats Python et gardes historiques (dont SaveLoad/PO01C), `git diff --check`,
   puis **revue indépendante** de la sécurité financière, performance et Squirrel.
2. **Smoke OpenTTD** 1 graine 42 ×1 an, OFF=0 contre ON=2 du même arbre et bundle,
   partie complète avec AAAHogEx, scripts sains ; il atteste compilation et
   absence de crash, mais 1970 peut ne présenter aucun renfort 1→2.
3. **Exposition** diagnostique appariée 5 graines `42 100 7 999 2026` ×3 ans,
   même code OFF/ON, `--probes 258 --script-debug`, en observant les couples
   ligne/mois dédoublonnés et les événements `N75_QUOTE phase=plan`, `execute`,
   `stale`, `built`, `FLEET_PROJECT action=grow`, `V252_ENGINE action=reinforce`
   et les nouveaux projets AIR/RAIL éventuellement évincés. Une inversion du
   seul devis sans achat supplémentaire/changement physique ne suffit pas.
   Vérifier la réserve réelle, les prix du moteur bâti, les dépenses alternatives
   et le coût d'opcodes/temps de la cotation ; le SHADOW n'est pas présumé neutre.
4. **Porte A `gain_short` uniquement si le diagnostic prouve une construction
   ou un investissement avancé réellement attribuable et une ampleur plausible
   >= 4 % en 1972** : 40 graines canoniques ×3 ans, 1 répétition, mêmes sources
   gelées OFF/ON, `profit_year`, delta moyen >=4 % du profit de référence,
   Wilcoxon exact bilatéral p<0,05 et IC95 bootstrap favorable, garde valeur
   maximum −5 %. Aucun résultat 5×3 ne requalifie une A.
5. Porte B `non_erosion` 20×10 seulement si A `pass` **et accord explicite de
   l'utilisateur pour ce banc spécifique**, conformément à AGENTS.md §4.1.

Un seul Docker, `docker ps` avant chaque lancement, 9 workers max, 10 CPU,
8 GiB, carte 256², année 1970, OpenTTD 15.3. Aucun défaut historique changé,
aucun commit, push, merge, suppression ou nouveau protocole V102.

## Vérifications disponibles avant moteur

`PYTHONPATH=sweeps python -X utf8 -m unittest -q sweeps.test_n75_air_true_quote
sweeps.test_v259_bridge_renew sweeps.test_v246_fixed_policies
sweeps.test_v251_inventory sweeps.test_po01c_regen_split
sweeps.test_v276_candidate_slices sweeps.test_v178_rail_shared_dest
sweeps.test_v284_rail_growth sweeps.test_b5_rail_persistence`

Au 25/10 : **116 tests PASS**, empreintes historiques PO01C vérifiées en
soustrayant seulement les octets explicites du nouvel opt-in (jamais rebases),
inventaire de 58 anciens réglages conservé séparément de l'option N75.

## Résultats effectifs et clôture sans porte A

Après une dernière correction de scope du garde de repli (paramètre interne
`n75PriceGuard` faux au défaut et vrai **seulement** pour le projet N75 1→2),
**215 contrats ciblés PASS** (dont V252, C121, C77, C80, PO01C/SaveLoad) et
`git diff --check` PASS. Revue indépendante READ ONLY : GO pour smoke technique,
aucune qualification économique acquise.

**Smoke 1×1** `nuit75_truequote_smoke_1x1_20261025` : graine42/1970,
2/2 parties complètes, aucune erreur Squirrel ; ON−OFF **−7 £/an** ;
manifeste `558ac9791cadd13b60b715513deabdd7191bf0e8e51dad981b7dc689600768c1`.

**Exposition 5×3** `nuit75_truequote_expo_5x3_20261025` (42,100,7,999,2026),
10/10 parties complètes : **51 renforts N75 bâtis**, 0 divergence prix catalogue
du moteur réellement bâti vs prix du projet, 0 quote devenue stale, +10 avions
OFF→ON, +2 lignes AIR mais −10 RAIL, profit/an **+44 530,8 £**, 4V/1D,
Wilcoxon p=0,625 ; garde valeur +3,28 %, seuil A descriptif +91 912,6 £.
Manifeste `758a72cfd544cf0599b22f22e340221f9250f91f8814c4e2e34ea6f957cfcb09`.

**Complément indépendant 5×3** `nuit75_truequote_expo_more5x3_20261025`
(1,17,73,314,512), 10/10 parties complètes : **44 renforts N75 bâtis**,
0 mismatch prix/moteur, 0 stale, +3 avions nets, −5 lignes AIR et +10 RAIL,
profit/an **+19 837,6 £**, 2V/3D, Wilcoxon p=1, garde valeur +5,60 %,
seuil indicatif +91 602 £.
Manifeste `d9c400f5e26285f28a4b2c1cc41cd3bddf130b6c9564aad00d297b5646d4e677`.

Les **deux diagnostics ont le même bundle de code**
`4bd4c8e3f9a6023a513980874a624f345071fa26b710913927536a3ed484ee12`,
OpenTTD 15.3, OpenGFX 7.1, carte 256², 1970–1972, 9 workers max,
10 CPU, 8 GiB. Décodeur reproductible :
`python -X utf8 sweeps/analyse_n75_truequote.py
results/nuit75_truequote_expo_5x3_20261025_engine` et second dossier
`nuit75_truequote_expo_more5x3_20261025_engine` ; sortie JSON `_mechanism.json`
dans chaque campagne et `nuit75_truequote_expo_10x3_20261025_rollup.json`.

**Total exploratoire 10×3 (non porte A) :** 20/20 parties complètes,
**95 achats de renfort N75 effectivement prouvés** (et NON 95 achats
supplémentaires), **+13 avions nets**, **−3 lignes AIR et 0 ligne RAIL nettes**
entre ON et OFF, malgré fortes substitutions par graine.
En dix graines, 8 985 événements de devis `phase=plan` **répétés**,
aucune divergence entre prix du moteur construit et cotation du projet,
aucune trace `stale` ; ne pas compter les devis comme des commandes ni
le prix catalogue comme dépense transactionnelle mesurée.

Profits terminaux **+32 184,2 £/an ON−OFF** (**+1,4030 %** de la référence),
médiane des différences +66 007 £, **6 victoires / 4 défaites**,
Wilcoxon exact bilatéral **p=0,4921875**, bootstrap exploratoire du delta
moyen IC95 [−99 145,6 ; +149 533,5] £, valeur +4,4101 % ; seuil 4 %
de cette cohorte **+91 757,3 £/an**. Aucune valeur 10×3 n'est une porte
statistique de remplacement : l'IC95 est indicatif et la politique est
bruitée par les choix de réseau et les opcodes supplémentaires.

**Verdict : exposition PHYSIQUE positive, potentiel incrémental >4 %
non étayé.** Avec seulement +13 appareils nets sur dix mondes,
réallocation AIR/RAIL, effet moyen +1,4 %, non-significatif, **NO-GO
porte A40×3** pour cette variante et **aucune B20×10**. Ne pas contourner le
pré-enregistrement en lançant des graines A pour espérer une réussite aléatoire.
Les économies d'opcodes et un vrai Save/Load exécuté sous moteur n'ont pas
été mesurés ; seuls les invariants de persistance ont été testés statiquement.
Le ratio cible 75 % sur dix ans reste non démontré ; conserver le paramètre à
zéro partout, le worktree/les données pour audit, sans commit/push/merge.
