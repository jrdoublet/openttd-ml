# P0 RAIL — reproductibilité et autopsie de la première divergence (10 octobre 2026)

## Mandat, périmètre et verdict maintenu

Suite au rejet au 40×5 de `rail_magic_simple_opcode=1`, établir si les
divergences OFF/ON proviennent d'un moteur non reproductible ou d'une bifurcation
après les générations RAIL. **Aucune troisième formule**, aucun changement du
score historique ou des défauts, aucune adoption, aucun commit/push. Le verdict
préexistant reste **REJET** : Δprofit moyen −88 103,8 £/an à cinq ans,
IC95 bootstrap [−172 423 ; −6 074], valeur compagnie −4,685 %, même si
les postes partiels OP/OS sont moins coûteux dans les trajectoires ON.

Toutes les campagnes ci-dessous partagent **exactement le bundle source**
`226368a5c6b141daac700569a4165cc2e0205a0394a1156de884ea3c88296e0c`
du 40×5 et la même image Docker `openttd-lab:latest`, digest
`sha256:f4b2b9b3b7399cbfecacfe03b8dda49bff2921de36a61fed4e9441e5d44659`.
Les graines 73, 781335, 802204 et 701256 sont **choisies à dessein** comme
cas informatifs, et ne constituent pas un nouvel échantillon statistique.

## 1. Témoin OFF/OFF réellement identique

Le harnais C66.4 interdit deux bras dont les réglages sont identiques
(`bench_1v1_5y_20seeds.py`). Aucun faux flag n'a été introduit.
Un C66.3 mono-politique, `--repeats 2`, fournit deux exécutions réellement
identiques, sur 4 graines × 2 ans = 8 parties OpexAI/AAAHogEx saines :

`rail_opcode_identity_off_repeats_4x2_20261010_r1`

- Réglages : `rail_magic_simple_opcode=0,rail_magic_simple_roi=0`.
- CPU 10, workers 8, RAM 8 Go, moteur Docker ; `--script-debug` **absent**.
- Manifeste : `ee15683fe560e4aee41d71e6a408349d9ef19e2ad20925c697da8c9c72b43288`.
- Aux checkpoints mensuels, **0 divergence sur les 4 graines** pour les 14
  séries non nulles : trésorerie, valeur, profit annuel, véhicules AIR/RAIL/ROAD,
  installations airport/rail, nombres de builds conservés, OP/OS et budget utilisé.
- Les checkpoints r0 du témoin et les checkpoints OFF correspondants du
  **40×5 initial** sont également identiques jusqu'au 1er décembre 1971 sur
  ces quatre graines et ces mêmes 14 séries. Le témoin reproduit donc le
  **vrai bras historique**, pas seulement une paire égale à elle-même.

Artefacts : `results/rail_opcode_identity_off_repeats_4x2_20261010_r1.{json,jsonl,manifest.json}`,
`results/rail_opcode_identity_off_repeats_4x2_20261010_r1_first_divergence.json`,
`results/rail_opcode_identity_vs_A40_off_4x2_20261010_r1.json`.

## 2. Relecture exhaustive des checkpoints du 40×5 initial

L'analyse hôte de `rail_magic_simple_opcode_A40x5_20261010_r1.jsonl` détecte :

| Première différence ON−OFF observée | Paires concernées |
|---|---:|
| Trésorerie à un moment quelconque sur 5 ans | 39/40 |
| Trésorerie dès avril–juillet 1970 | 36/40 |
| Avions à un moment quelconque sur 5 ans | 39/40 |
| Véhicules RAIL à un moment quelconque sur 5 ans | 38/40 |
| Panneaux cumulés `cand_pax`, `cand_freight`, `cand_rank` différents au relevé de février 1971 | 40/40 |

**Attention :** le relevé OP/OS de février 1971 est un panneau annuel
`OpexSign`; il **ne date pas** la première génération RAIL de février 1971.
Les différences d'argent ou d'avions ne sont pas des mesures de ticks ou
d'opcodes. `observed_opcodes_total` demeure une somme **partielle** ; il n'est
pas le coût VM total et dépend aussi du nombre de projets réalisés.

Artefact : `results/rail_magic_simple_opcode_A40x5_20261010_r1_first_divergence.json`.

## 3. Capture moteur seule : contrôle de non-perturbation observée

Campagne `rail_opcode_capture_only_A4x2_20261010_r1`, 4 graines × 2 ans,
8/8 parties saines, `rail_magic_simple_opcode=0` contre `=1` ; ROI pur `=0`
des deux côtés. Seule option de capture supplémentaire : `--script-debug`
(OpenTTD `-d script=4`). Le réglage interne IA `decision_log` reste **0**.
Campagne **diagnostique seulement**, jamais une porte d'adoption 40×5.

- Manifeste : `ed666165ac928c6d66bf4ad5abfded254f5b3b08e65f216d6b2f93a85d9eca42`.
- **OFF et ON reproduisent chacun exactement** les 14 séries mensuelles du
  40×5 initial sur les 4 graines, jusqu'au 1er décembre 1971 : aucune différence
  observée malgré la capture des AILog. Ce constat ne démontre pas une absence
  de surcoût *global* des journaux ni leur innocuité pour toutes les graines.
- Les journaux moteur désormais non vides permettent de comparer les événements
  préexistants, sans activer les sondes RAIL/scheduler intrusives.

Premières différences **parmi les messages OPEX effectivement émis** :

| Graine | Événement conservé OFF vs ON | Premier argent ON−OFF aux checkpoints |
|---|---|---|
| 73 | `C83_REACTION` même ville 40, 6 mars vs 7 mars 1970 | avril : −2 £ |
| 781335 | `C83_REACTION` même ville 29, 21 février vs 20 février | mai : −137 £ |
| 701256 | `C83_REACTION` même ville 23, 27 février vs 25 février | avril : −62 906 £ |
| 802204 | première différence conservée `C121_HUB_DELAY` de septembre/octobre ; pas de témoin de la première bifurcation | juin : −3 £ |

Les messages OPEX ne représentent **pas** toutes les décisions et ne fournissent
pas les ticks. Ainsi, les changements `C83_REACTION` sont les **premières
différences loguées**, non nécessairement la première instruction différente
ni la cause du décalage. La graine 802204 prouve précisément cette limite :
la trésorerie est différente avant le premier événement divergent conservé.

Artefacts : `results/rail_opcode_capture_only_A4x2_20261010_r1.{json,jsonl,manifest.json}`,
`results/rail_opcode_capture_only_A4x2_20261010_r1_engine/*.log`,
`results/rail_opcode_capture_only_A4x2_20261010_r1_event_first.json`,
`results/rail_opcode_capture_vs_A40_{off,on}_4x2_20261010_r1.json`.

## 4. Essai de `decision_log=1` : **perturbateur confirmé**

Campagne `rail_opcode_trace_A4x2_20261010_r1`, 8/8 parties saines,
**`decision_log=1` dans les deux bras**, plus `--script-debug`.
Manifeste `0ebfff0f82bf294faa3ee323f880f811c2cabad6dd100f0c29cdeed6eecadc39`.

Dans cette simulation *instrumentée*, les premiers `VIVIER_GEN` peuvent être
identiques, puis des tâches `TASK` / événements AIR décalent en janvier, et
les choix de projets AIR se séparent plus tard. Ceci rend plausible le
mécanisme `score local → coût/ordre du TOP20 → cadence scheduler → AIR`.

**Mais `decision_log=1` change l'économie** : même le bras OFF diffère du OFF
historique dès le checkpoint de **février 1970 pour les quatre graines** en
trésorerie, et les états physiques divergeront ensuite. Ce diagnostic ne
mesure donc **pas** le premier événement de la campagne économique originale.
Les différences de `TASK` relevées ici ne sont pas la preuve du mécanisme
historique. Ce banc n'est pas une validation d'adoption et ne doit pas être
agrégé avec le 40×5.

Artefacts : `results/rail_opcode_trace_A4x2_20261010_r1_event_first.json`,
`results/rail_opcode_trace_overhead_off_4x2_20261010_r1.json`.

## 5. Interprétation causale et décision

- Le changement de réglage est **causalement associé aux trajectoires** dans
  un moteur reproductible : le témoin OFF/OFF est strictement identique et les
  deux bras d'une même campagne partagent le même code/image.
- `candidates.nut` fait toujours `OpexRailEconomicTopK(all, TOP_K)` ; les
  comparaisons/inserts dans `OpexTopK` dépendent de `candidate.ratio` ; la
  bande `OpexBands` aussi. C'est un mécanisme de **coût/cadence plausible**.
- `projects.nut` donne néanmoins à la sélection financière **tous** les
  `rail.candidates`, et non le TOP20 `best` ; le changement n'est pas censé
  remplacer directement le score intermodal du portefeuille.
- Les résultats ne prouvent **pas encore** que le premier tick divergent est
  causé par l'insertion TOP20, ni quel coût VM exact il entraîne. Ce maillon
  demanderait un relevé à bas coût des ticks / opclock à la première génération
  RAIL et avant le prochain dispatch `projects`, avec contre-épreuve de
  non-perturbation ; les probes existantes `probe_events` et
  `probe_rail_search` activent d'autres journaux et sont intrusives.

**Verdict :** les deux ablations `simple_opcode` et `simple_roi` restent OFF ;
aucune porte B20×10, aucun changement du score, ni commit/push. On conserve le
nouvel analyseur hôte `sweeps/analyse_rail_opcode_first_divergence.py` et
`sweeps/analyse_rail_opcode_trace.py` pour ne pas confondre une première
différence de checkpoint, une première ligne de journal et un premier tick.
Tests hôte dédiés : 3/3 et 1/1 verts.
