# C83 — supprimer la régénération réactive de créneau

## Plan pré-enregistré — 2 octobre 2026

Demande utilisateur : travailler la suppression de la réaction qui abandonne
une passe de construction lorsque AAAHogEx prend un emplacement d'aéroport,
avec un recalcul ciblé annoncé de 25 à 60 jours. Cette durée est une observation
rapportée, **pas une mesure revalidée ici**.

Lecture du code : `_c83WatchAirSlotTransitions()` observe les six grandes villes
via `AITown.GetAllowedNoise()`, sous le signal moteur de deux slots par ville.
Un état 1 (Opex absent, un slot restant), nouveau et sans projet AIR financé,
enfile `c83_slot_race` dans C77. `_tryBuildProjects()` retourne alors avant la
construction. Ce signal indique une occupation de slot dans une ville ; il ne
désigne ni AAAHogEx individuellement ni un site précis devenu caduc.

**Intervention comportementale isolée :** `c83_slot_reaction=0` conserve
l'observation, la mise à jour de l'état et les sondes existantes, mais supprime
cet enqueue. La passe poursuit donc sa sélection habituelle. Le contrôle
`=1` garde l'ancien chemin. Même garde dans le watcher `c83_fixes`, lequel
reste OFF au défaut. Priorité défensive des projets disponibles, second slot
proactif, préflight R3, financement, C115=1 et C121=0 restent inchangés.
`c83_preempt_open` et le retry expérimental C122 sont distincts et restent OFF.

Le défaut livré reste **1** (quatre difficultés, fallback global true) pendant
la qualification. Aucun nouvel état décisionnel ni champ de Save/Load.

### Identité et protocole

- Dépôt : `C:\Users\jr\vscode\openttd-ml\openttd-ml` ; branche `c121-catalog` ;
  HEAD initial `3ffd615`, arbre dirty conservé et figé par le harnais.
- Les changements préexistants `air_fleet_cooldown_prefilter=1` et leur journal
  sont préservés. L'essai compare le même arbre aux défauts courants et n'accorde
  aucune qualification aux autres modifications intégrées antérieurement.
- Référence : `OpexAI[c83_slot_reaction=1]` contre AAAHogEx figée.
- Variante : `OpexAI[c83_slot_reaction=0]` contre la même AAAHogEx, autre partie
  avec même carte, configuration, horizon et places.
- Catégorie **behavior**, fixée avant mesure ; primaire `profit_year`, effet
  utile **+50 000 £/an**, garde `company_value` **−5 %**, règle `signs20`.
- Smoke : graine 42, un an, deux parties. Diagnostic : 42/100/999/1234/5678,
  six ans, dix parties. Adoption conditionnelle : 20 graines canoniques,
  dix ans, quarante parties ; aucune relance identique ni seuil révisé.
- Docker local `desktop-linux`, image `openttd-lab:latest`
  `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`,
  OpenTTDLab 0.0.75 ; 3 CPU, 2 Go sans swap, cache `openttd-lab-home`,
  montage racine `/work`, deux workers. Aucune campagne active au préflight.
- `--script-debug` commun aux deux bras ; `line_telemetry=false` et sondes
  portefeuille OFF. Trace rare `C83_REACTION` à l'intention d'enqueue ou à sa
  suppression, sans scan ni sonde de portefeuille supplémentaire.
- Exposition : `summary[].c83_reaction.suppressed >= 1` pour chacune des cinq
  graines variantes ; `enqueued=0` dans ces variantes et contrôle de `enabled=0`.
  Lire aussi les enqueues de référence. Absence ou log malformé reste inconnu,
  jamais zéro. Ces événements ne mesurent ni le temps de recalcul ni une perte
  d'aéroport. Le lecteur lit une fois le log final cumulatif de chaque partie.

Passage au diagnostic seulement après contrats et smoke sains. Passage au
20×10 seulement après 5/5 paires complètes, saines, exposées, quatre trimestres
valides, delta moyen ≥+50 000 £/an et garde tenue. Sinon arrêt et ancien défaut
conservé. Une adoption ultérieure exige le verdict complet du §4 d'AGENTS.md.

Commandes hôte : `sweeps/run_c66_reference.py`, bras et seuils ci-dessus,
`--max-workers 2 --cpus 3 --memory 2g --script-debug`. Campagnes neuves :
`c83_reaction_off_smoke_20261002_r1`, puis
`c83_reaction_off_diag_20261002_r1`. Bundle, manifeste, JSON/JSONL et logs
restent propres à chaque campagne sous `results/`.

### Validation et décision

120 tests ciblés réussis (C83/P4/C78, gel du harnais, santé), selftest C66 OK.
Smoke : **2/2 duels sains et complets**, sauvegarde finale 1971-01-01,
aucune exposition C83 (champ inconnu/absent dans les deux bras). Résultats
identiques : profit initial 336 825 £, valeur 348 919 £, 16 véhicules et
12 gares. Cette absence d'événement ne prouve pas la neutralité économique.

SHA réellement capturé : `b2334d7156f12519b1f27a0078bc267f7d40dce8`, dirty.
Un commit documentaire concurrent a ajouté un suivi K_dec pendant la préparation ;
aucune source IA modifiée par ce commit. Identités smoke : bundle
`1b0fdb96d9df667f981db66cc66234c4c245d611db5ee24fab0af98e5e54c8e4`,
manifeste `5d960e20d72abbf1a6441f1107c4c8dd38735c405dac9bf8d56ea6aed55fea36`.
Empreinte du bundle revérifiée dans le conteneur. Diagnostic 5×6 autorisé
par la porte technique ; défaut 1 conservé.

### Diagnostic 5×6 — décision : arrêt, suppression non retenue

**10/10 retours moteur sains**, 5/5 paires complètes, horizons jusqu'au
1975-12-01, `comparison_complete=true`, `metric_coverage_complete=true`,
quatre trimestres valides par primaire final. JSONL **1440/1440** observations
attendues, aucun manque, doublon ni observation inattendue. Le smoke contient
48 observations mensuelles plus quatre retours au 1971-01-01, conservés.

Les deux étapes ont exactement le même bundle et les mêmes empreintes OpexAI,
AAAHogEx, bibliothèques et harnais. Manifeste diagnostic :
`7f94cdbbc1d8867f4bdeab16a2f7b797fee706b7f6ad4f320c2ef38ed29a692a`.
SHA `b2334d7`, arbre dirty, runtime et limites inchangés. Les quatre sources
modifiées pour C83 correspondent toujours à la copie testée à la clôture.

| Graine | Profit référence £/an | Profit sans réaction £/an | Delta £/an | Enqueues référence | Réactions supprimées |
|---|---:|---:|---:|---:|---:|
| 42 | 1 766 125 | 1 766 125 | 0 | aucun événement observé | aucun événement observé |
| 100 | 685 912 | 606 388 | −79 524 | 4 | 5 |
| 999 | 1 843 738 | 1 729 092 | −114 646 | 4 | 2 |
| 1234 | 1 380 397 | 1 579 892 | +199 495 | 1 | 1 |
| 5678 | 2 230 224 | 1 740 193 | −490 031 | 2 | 2 |

Profit moyen Opex : **1 581 279 → 1 484 338 £/an**, delta **−96 941 £/an**,
médiane **−79 524 £/an**, **1 victoire / 3 défaites / 1 égalité**, p bilatéral
**0,625** (quatre deltas non nuls). IC95 **Student [−408 849 ; +214 966] £/an** ;
le harnais publie aussi l'IC normal [−317 125 ; +123 242]. Incertitude large :
ce diagnostic ne démontre pas une perte générale significative.

Valeur moyenne **6 210 762 → 5 643 890 £**, ratio des moyennes **−9,1273 %** :
**garde −5 % échouée**. Nombre d'aéroports Opex : delta moyen −1,4,
réparti 0/−7/+1/+1/−2 par graine ; ce compteur ne mesure pas le temps de recalcul.

Exposition technique : **11 enqueues** au contrôle, **10 suppressions** dans
la variante, avec zéro enqueue C83 variante. Mécanisme exposé sur **4/5 graines** ;
42 reste sans événement et son exposition est inconnue. Les comptes différents
reflètent les trajectoires différentes des bras. La durée de 25–60 jours
rapportée initialement n'a pas été remesurée.

Verdict brut **`diagnostic_only`**, `adoption_sample_complete=false`. Trois
portes de passage échouent : exposition sur toutes les graines, gain moyen
≥+50 k£/an, garde de valeur. **Aucun 20×10, aucune adoption et aucune relance
identique.** Le réglage `c83_slot_reaction` reste **1** aux quatre difficultés ;
`=0` reste disponible comme ablation expérimentale. La priorité défensive et
les vérifications physiques n'ont pas été modifiées par ce lot.

Preuves : [résumé durable](../evidence/review/c83_slot_reaction_20261002/summary.json),
[index et empreintes](../evidence/review/c83_slot_reaction_20261002/index.json).
Cinq JSON archivés en gzip déterministe avec `package_review_evidence` ; hashes
bruts/gzip, manifests, bundles, JSONL et logs vérifiés. Les logs et bundles
complets restent locaux, leurs empreintes sont versionnables dans le résumé.
L'index global historique n'a pas été modifié.

Fichiers locaux : `results/c83_reaction_off_smoke_20261002_r1.json`,
`results/c83_reaction_off_smoke_20261002_r1.manifest.json`,
`results/c83_reaction_off_diag_20261002_r1.json`,
`results/c83_reaction_off_diag_20261002_r1.manifest.json`,
`results/c83_slot_reaction_20261002_summary.json` ; JSONL, logs et bundles
homonymes préservés.

Des travaux concurrents ont modifié `air_construction.nut`,
`projects_selection.nut` et `scheduler_tasks.nut` pendant le diagnostic.
Ils sont préservés et absents des copies testées ; ce résultat ne les qualifie
pas. Aucun commit ni push effectué dans ce lot.
