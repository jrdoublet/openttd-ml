# V275 — porte A en rail seul (PC, 19 octobre 2026)

**Verdict brut : `pass` sur 40/40 paires**, 80/80 parties saines à trois ans. Il s'agit de la comparaison du **paquet rail voyageurs V207 + V275**, et non d'un effet isolé du seul réglage V275. La qualification en partie complète et la porte B à dix ans restent distinctes.

## Protocole et provenance

- Campagne : `v275_railseul_porteA_40x3_pc_20261019`, du 19/10/2026, terminée à 17 h 44 (heure locale). Smoke `v275_railseul_porteA_40x3_pc_20261019_smoke` : 2/2 duels complets (graine 42, un an).
- Arbre exécuté : branche `v275`, commit **`6b65fbbd9e67a7ec9f7fc22b6a314852c4be0791`**, `dirty=0`. Image `openttd-lab:latest` : `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`; OpenTTD 15.3, OpenGFX 7.1.
- Bundle source SHA-256 : `ebf9cc3589ae4a53d0c43b9192fbf8b589860cec2a2f5e7f7c774095d1026a23` ; manifeste SHA-256 : `37021b087baa95b027259288c03173439ff4a57a6e8f9ed2a2963657812a29af`.
- Référence : `OpexAI[v275_rail_pax_mm=0,mode_air=0,mode_road=0,mode_water=0]` ; variante : `OpexAI[v207_rail_pax_share_pct=40,v207_rail_mail=1,v207_rail_pax_joined_stops=2,v275_rail_pax_mm=7,mode_air=0,mode_road=0,mode_water=0]`.
- AAAHogEx-115 : avions, véhicules routiers, trams et bateaux désactivés dans les **deux** bras. Même carte/graine par paire ; deux duels contre le même adversaire figé. 40 graines de `sweeps/run_v275_pc.sh` (73 remplacée par 373684), un seul tirage par graine, horizon trois ans.
- `gain_short`, primaire `profit_year` de l'année terminale (variante moins référence), Wilcoxon exact bilatéral, bootstrap 20 000 tirages/graine 0, seuil de gain +4 % du profit moyen de référence, garde de valeur d'entreprise −5 %. Ressources : 10 CPU, 8 Go RAM, 10 workers.

## Mesures

| Mesure | Résultat |
| --- | ---: |
| Paires / parties complètes | **40/40 ; 80/80** |
| Opex référence, profit annuel | **329 799,63 £/an** |
| Opex variante, profit annuel | **965 166,40 £/an** |
| Delta moyen / médian | **+635 366,78 / +671 577 £/an** |
| Gains / pertes / ex æquo | **40 / 0 / 0** |
| Wilcoxon p exact | **1,8189894 × 10⁻¹²** |
| IC95 bootstrap de la moyenne | **[+585 195 ; +684 446,68] £/an** |
| Seuil minimal +4 % | **13 191,99 £/an** |
| Ratio des valeurs d'entreprise moyennes | **2,777328**, soit **+177,73 %** |
| Contrôles du protocole | `comparison_complete=true`, `adoption_sample_complete=true`, `metric_coverage_complete=true`, `value_guard_pass=true` |
| Verdict du harnais | **`pass`** |

Dans le duel de référence, le profit annuel moyen d'AAAHogEx vaut **1 317 091,95 £/an**, contre **1 277 957,68 £/an** dans le duel de la variante ; l'Opex variante atteint ainsi **75,5 %** de cet AAAHogEx, avec un écart moyen de **−312 791,28 £/an**. L'évolution face à AAA mêle progression d'Opex et changement de trajectoire d'AAAHogEx ; le critère d'adoption reste le delta propre à Opex.

## Artefacts et suite

- Sources locales originales (ignorées par Git) : `results/v275_railseul_porteA_40x3_pc_20261019.json` et `results/v275_railseul_porteA_40x3_pc_20261019.manifest.json` ; archives gzip vérifiables et SHA-256 consignés dans `evidence/review/index.json`.
- Le commit `d2794a5c` est postérieur au banc : il ajoute le bit 8 et fait passer le script à `v275_rail_pax_mm=15`. Ce bit n'agit que si `MODE_AIR` est actif ; **le rail seul de ce banc utilisait réellement la valeur 7**. Ne pas attribuer le résultat à un banc effectué avec 15 ou à une qualification multimodale.
- Porte B 20 graines × 10 ans (`non_erosion`) requise pour la tenue à long terme du paquet rail seul. Aucun changement de défaut n'est autorisé par cette seule porte A.
