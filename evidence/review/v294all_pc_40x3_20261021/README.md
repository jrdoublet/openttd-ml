# V294all + V295 ? trois portes A 40?3 sur PC (21 octobre 2026)

Ces trois campagnes ont d?j? ?t? ex?cut?es ; cette publication n?a lanc? aucun banc suppl?mentaire.

## Protocole

- Git r?ellement ?valu? : `6c86558906330239eb39c496351d31c4ef35dd1d` (correctif V294c `eb9e933a` inclus ; commits ult?rieurs `ebefa851`, `277d7ede` et `3f81583d` non pr?sents pendant les trois runs).
- Bundle identique : `a9208bcce4911f011b0bc45d689cb2f9836ae95c3625771ac247f97c46688620` ; Docker `openttd-lab:latest` sha256 `f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
- Lancement par `sweeps/run_v294all_pc.sh`. 40 graines ? 1 r?p?tition ? 2 politiques ? 3 ans = 80 parties par campagne. Carte 256?256, 10 CPU / 8 Go / 10 workers. AAAHogEx sur carte partag?e avec chacune des politiques.
- R?f?rence OpexAI `v294_rail_continuous=0` ; variante combinaison `v294_rail_bridge_len=20,v294_rail_weight_pct=200,v294_rail_aaa_costs=1,v294_rail_reverse_probe=300,v294_rail_dist_decouple=200,v294_rail_slope_engine=1,v295_astar_fast=1`.
- Complet 1927 : `START_YEAR=1927` (variante A* continu `v294_rail_continuous=1`). Rail seul 1970 : `RAILSEUL=1` (variante A* continu). Rail seul ADAPT400 1970 : `RAILSEUL=1 ADAPT=400` (variante A* segment? `v294_rail_continuous=0,v294_rail_weight_adapt=400`). L?option ADAPT ne teste pas isol?ment le poids puisqu?elle change aussi le mode A*.
- En rail seul, OpexAI d?sactive air/route/eau et AAAHogEx d?sactive avions/routiers/trams/navires. Porte A `gain_short`, profit annuel ? 3 ans, gain utile minimal +4 %, Wilcoxon p<0,05, IC95 bootstrap strictement positive, garde de valeur ?5 %.

## R?sultat ?conomique terminal (moyennes sur 40 graines)

| Campagne | Profit Opex ref. (?/an) | Profit Opex variante (?/an) | Profit AAA contre variante (?/an) | Ratio Opex/AAA variante | ? Opex variante?r?f?rence (?/an) | V/D | ? valeur compagnie | Verdict |
|:--|--:|--:|--:|--:|--:|:--:|--:|:--|
| Complet 1927 | 240 345 | 123 662 | 706 171 | 17.51% | -116 683 | 5/35 | -34.30% | `fail_primary_and_value_guard` |
| Rail seul 1970 | 1 011 340 | 984 740 | 1 198 812 | 82.14% | -26 601 | 19/21 | -3.30% | `fail_primary` |
| Rail seul ADAPT400 1970 | 1 011 341 | 958 369 | 1 221 631 | 78.45% | -52 972 | 15/25 | -18.32% | `fail_primary_and_value_guard` |

Remarque : les duels AAAHogEx face ? la r?f?rence et ? la variante sont distincts ; la baisse du profit adverse ne signifie pas un b?n?fice pour OpexAI.

## Significativit? et r?seau

| Campagne | ? m?dian (?/an) | Wilcoxon p | IC95 bootstrap ? (?/an) | Trains ref.?var. | Gares ref.?var. | Cash ref.?var. (?) |
|:--|--:|--:|:--|:--|:--|:--|
| Complet 1927 | -120 872 | 5.02951e-09 | [-144 365 ; -88 115] | 23.6?10.6 | 39.3?24.5 | 54 037?55 734 |
| Rail seul 1970 | -13 812 | 0.562668 | [-85 332 ; 31 669] | 20.9?22.1 | 34.1?35.9 | 621 287?536 874 |
| Rail seul ADAPT400 1970 | -65 472 | 0.124716 | [-114 927 ; 9 530] | 20.9?27.8 | 34.1?45.7 | 621 202?200 706 |

**Interpr?tation non causale des m?canismes :** en 1927 V294all pose moins de rail, en rail seul 1970 ADAPT400 construit plus mais consomme beaucoup de tr?sorerie sans augmenter le profit. Isoler le m?canisme par des journaux/ablation avant toute adoption. Aucun de ces trois bancs ne passe la porte A.

## Preuves archiv?es

JSON de synth?se, manifestes, s?ries mensuelles JSONL et smokes compress?s en gzip d?terministe. Les bundles et logs moteur restent locaux ; ils ne sont pas inclus dans Git. Les CSV sont extraits des synth?ses terminales.

| Fichier | Octets non compress?s | Octets versionn?s | SHA256 versionn? |
|:--|--:|--:|:--|
| `v294all_complet_1927_porteA_40x3_pc_20261021.json.gz` | 1688921 | 83134 | `1036f6d97a13a4b37bfd324bac027478cda73c19c27e1f6a8be1e273ab9b1684` |
| `v294all_complet_1927_porteA_40x3_pc_20261021.jsonl.gz` | 34058077 | 2108235 | `3713c2c81e7f1391a9d23ed74be190484eedc60eae6053043a87163fa43c05ce` |
| `v294all_complet_1927_porteA_40x3_pc_20261021.manifest.json.gz` | 79532 | 12410 | `e650ade4f5917b5fe6f6cd43567ad8bbd293b6326820266d4b2d96dc1e79f691` |
| `v294all_complet_1927_porteA_40x3_pc_20261021_smoke.json.gz` | 72729 | 6506 | `1ade23bef18b7c700cbbc07fd1820ae9be1b06d532308e6dc42efebbf69053d7` |
| `v294all_complet_1927_porteA_40x3_pc_20261021_smoke.manifest.json.gz` | 48782 | 10925 | `dc4f96a3973872b80801ce572852990c3d4d506cef627f5a1b9ada8d01fc53c3` |
| `v294all_railseul_1970_porteA_40x3_pc_20261021.json.gz` | 1655816 | 79122 | `7e65dd8281084ea07d776fcd93330714d178029c7ac2815fad02df5e0d3285fa` |
| `v294all_railseul_1970_porteA_40x3_pc_20261021.jsonl.gz` | 31544429 | 1918060 | `2b1ea2718870015b0fa4399aea0b3d8ac7062f35bcf5cf47f8b2f7c79feacf80` |
| `v294all_railseul_1970_porteA_40x3_pc_20261021.manifest.json.gz` | 80190 | 12494 | `66c7ad9ed3eab315cf954b83d7fcc9f39595b209626d96eff60d9d5a869beab8` |
| `v294all_railseul_1970_porteA_40x3_pc_20261021_smoke.json.gz` | 70983 | 6482 | `046a508b3fbc3a8204ff92358dedac792d07e614d68b320c64b4d38656215933` |
| `v294all_railseul_1970_porteA_40x3_pc_20261021_smoke.manifest.json.gz` | 49362 | 11011 | `afe21c7e8e2282d30d5d3160549bde2467d9b44f10dc1d9aa3c5a792c38d9be4` |
| `v294all_railseul_adapt400_1970_porteA_40x3_pc_20261021.json.gz` | 1643748 | 78500 | `128e49738aa51196ed4b533404700668cd4d20b7995bc8473bc36c0024894ed8` |
| `v294all_railseul_adapt400_1970_porteA_40x3_pc_20261021.jsonl.gz` | 31876894 | 1926396 | `f6ce64bb9ab9502a2e34da9ed9418760c260e89934a2151da24a21f31776df7c` |
| `v294all_railseul_adapt400_1970_porteA_40x3_pc_20261021.manifest.json.gz` | 81058 | 12526 | `51663f4e7920de46f6c3e2790fb5fba51141772aa7d89e95c740c4e596c21aa8` |
| `v294all_railseul_adapt400_1970_porteA_40x3_pc_20261021_smoke.json.gz` | 71226 | 6445 | `4a81587fdac30c5fbb6a429773ec0050d11d0ed7eb72b2a8b0f77c231e919843` |
| `v294all_railseul_adapt400_1970_porteA_40x3_pc_20261021_smoke.manifest.json.gz` | 49528 | 11027 | `560ef5831f8744647ac29fb9194a528e1a2d84ba8991aa21c745c080ebb1fbda` |
| `per_seed_terminal.csv` | 55868 | 55868 | `38d5e9ba03a2745c2ebedc5aaf4d14c5ae2b803806b80e1df9543a57cba53a2c` |
