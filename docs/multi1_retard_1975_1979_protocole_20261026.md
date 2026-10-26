# MULTI-1 — diagnostic tardif du capital et des occasions de construire, 26 octobre 2026

**Pré-enregistrement d'une observation, pas d'un levier ON ni d'une porte économique.**
Source avant expérience : `master` `08adcba6`, arbre suivi propre, synchronisé avec
`origin/master` le 26/10. L'instrumenteur de portefeuille C63/C50/C69 existe déjà ;
aucun paramètre économique n'est modifié. Cette étude conserve les trois
`NO-GO_NON_EXPOSE` et le `NO-GO_PREQUALIFICATION_PHYSIQUE` de la route.

## Question et raison de la nouvelle mesure

Dans l'archive 20×10 `nuit75_master83e_baseline20x10_20261024` (code historique
`83e436cc`), OpexAI passe de **87,44 % du profit annuel AAAHogEx en 1974**
à **74,48 % en 1975** puis **56,55 % en 1979**, malgré **14,90 M£ de caisse**
à fin 1979. Le rail Opex plafonne autour de 30 trains ; AAA atteint environ
61 trains, mais ses véhicules routiers sont largement des feeders dont le
profit autonome est faible. Ces **stocks** ne mesurent ni dépenses de chantier,
ni projets réellement constructibles, ni profit net marginal.

Question testable : après 1974, le portefeuille échoue-t-il principalement
par **absence de candidats**, **impossibilité physique / invalidité**, **coût
opcodes et attente du calcul**, **filtre de demande**, **financement**, ou
**surestimation du bénéfice des lignes existantes** ? Une même observation
peut laisser plusieurs causes en concurrence ; ne pas baptiser un classement
causal sans projet témoin finançable et physiquement exécutable.

## Acquisition fixée avant mesure

- **Carte** 256², année de départ 1970, modes par défaut, AAAHogEx-115
  identique dans les deux bras. Graines `42, 100, 7, 999, 2026`, une
  répétition, **11 années simulées, 1970–1980** : indispensable pour
  récupérer la vidange C63 de **1979** émise au début de 1980 ; exclure 1980
  de la comparaison économique demandée. Périmètre descriptif **1975–1979**,
  sans sélection après résultats.
- Référence `OpexAI[probes=2]`, diagnostic
  `OpexAI[probes=131074]` (bits **131072 + 2**). Le bit 131072 active le
  groupe portefeuille **C63/C50/C69** ; le bit 2 conserve les panneaux.
  Le paramètre ancien `probe_portfolio` mentionné dans
  `sweeps/diag_c63_c58.py` **n'est plus déclaré dans `info.nut`** :
  utiliser le masque actuel sans supposer que cet ancien script lance la
  campagne. `--script-debug` permet de conserver le journal OPEX.
- Lancement hôte `sweeps/run_c66_reference.py` avec noms de campagne
  neufs `multi1_late_c63_smoke_20261026` (graine 42, deux ans, compile et
  flush 1970) puis `multi1_late_c63_5x11_20261026`.
  `--decision-rule signs20` uniquement pour satisfaire le schéma du
  harnais ; **aucun verdict de gain/adoption ne sera inféré**. Capturer les
  manifests, SHA source, empreinte de l'image et les logs moteur du bras
  diagnostique. `--cpus 10 --memory 8g --max-workers 10`, **un seul Docker**.
- La sonde ajoute des journaux et du travail sous un chemin opt-in, peut
  déplacer la trajectoire ; les ratios Opex/AAA du bras sonde et les deltas
  entre les bras seront signalés comme **diagnostic uniquement, non causal**.
  La cohorte actuelle n'est pas identique à la référence historique
  `83e436cc`. Ne pas mélanger ses chiffres avec le témoin 20×10.

## Sorties et garde qualité pré-enregistrées

Pour chaque graine et **chaque année 1975–1979**, vérifier les vidanges
`C63_INVEST phase=spend` par mode (somme `actual_ok`, `n_ok` séparés de
`planned_ok`), `phase=opp` avec jours `absent / invalid / unaffordable /
demand / waiting_compute / launched`, `phase=opp_absent` et
`phase=empty_probe`. Relever en parallèle `C50_CHRONO` pour la caisse
et les refus de financement ; ne pas additionner les sorties redondantes
C50 et C63. Les `phase=line` C63 comparent `pred_p`, `real_p`,
`pred_r`, `real_r` et âge, en isolant les lignes **matures ≥2 ans** et
les pertes. Les dépenses de véhicules (`fleet`) sont un poste distinct
du CAPEX d'infrastructure et les constructions ratées restent séparées.
Les jours d'opportunité couvrent un **état exclusif par passe** et ne
prouvent pas qu'un projet rejeté était physiquement constructible.

Avant interprétation, exiger cinq paires complètes, une campagne saine,
zéro erreur Squirrel, les lignes C63 annuelles 1975–1979 présentes
pour chacune des cinq graines ; refuser tout agrégat qui confond mois,
années et graines. Vérifier l'état du dépôt, l'intégrité des deux bras
et la complétude des journaux. Si l'instrumentation déplace la politique
ou si des années manquent, documenter les censures et limiter les conclusions
aux observations réellement disponibles.

**Décision après données :** rechercher un nombre significatif de couples
uniques rentables, finançables **et constructibles** ainsi qu'une marge
annuelle plausible face au déficit stratégique avant tout nouveau ON.
Une future politique tardive fera l'objet d'un **nouveau** pré-enregistrement
de son horizon/exposition **avant** son code et ses mesures : ne pas allonger
après coup A 40×5 des trois leviers précoces. Pas de porte A/B, pas
d'adoption, pas de modification de P1, P6 ou LATE-GAME-1 dans cette étape.
