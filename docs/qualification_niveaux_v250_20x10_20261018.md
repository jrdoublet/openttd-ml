# OpexAI ? difficult?s N0/N1 et V250 mode 4, 20 graines ? 10 ans (18/10/2026)

## P?rim?tre et reproductibilit?

- **Code test?** : `master` au commit `0d3b2b60cf5092aae45fde64693db65c0003acf8` (ant?rieur aux huit commits de documentation ajout?s ensuite sur `origin/master`). M?me bundle source sur les trois campagnes : `57e08a4d5b693ce6de90e53e8dbd40bc6c2cd426d964817e30983ed707de1e6c`.
- **M?thode** : parties multimodales OpexAI contre AAAHogEx, 20 graines appari?es ? 10 ans (1970?1979), 1 r?p?tition, 20 parties par politique soit 40 jeux complets par campagne ; `--cpus 10 --memory 8g --max-workers 10 --network host` ; m?trique primaire `profit_year`, `--decision-rule non_erosion --min-useful-primary-delta-pct 0 --value-guard-max-loss-pct 5`.
- Les trois campagnes sont termin?es : **20/20 paires, 40/40 jeux et z?ro ?chec moteur** chacune. Les statuts `stagnation_suspect` sont signal?s distinctement des ?checs moteur.
- Les noms `diff_n1_vs_n2_10x10_pc_20261018` et `diff_n0_vs_n2_20x10_pc_20261018` sont historiques : le premier porte ? 10x10 ? dans son nom mais le JSON et le protocole montrent **20 graines ? 10 ans**.

## ?cart de chaque variante ? sa r?f?rence N2

| Variante | ? profit annuel moyen | ? profit relatif | Victoires / d?faites | IC95 bootstrap (profit, ?/an) | ? valeur compagnie | D?cision automatique |
|---|---:|---:|---:|---:|---:|---|
| N1 (`opex_difficulty=1`) | ?183 805,65 ?/an | ?4,87 % | 7 / 13 | [?375 920 ; +9 988] | ?4,17 % | `pass` au seul crit?re de non-?rosion, **pas de gain d?montr?** |
| N0 (`opex_difficulty=0`) | ?364 767,65 ?/an | ?9,63 % | 2 / 18 | [?501 176 ; ?237 400] | ?5,27 % | `fail_primary_and_value_guard` |
| V250 mode 4 (`opex_difficulty=3,v250_rights=4`) | **+1 035 005,85 ?/an** | **+27,35 %** | **20 / 0** | **[+774 383 ; +1 304 992]** | **?52,00 %** | `fail_value_guard` |

Les comparaisons portent sur les mondes appari?s **au sein de chaque campagne**. Le `pass` de N1 signifie seulement que l'IC bootstrap n'exclut pas z?ro ? la hausse et que la garde de valeur ? ?5 % est tenue ; il ne signifie pas que N1 est meilleur que N2.

### Taille du r?seau et sant?

- **N1** : 151,3 v?hicules en moyenne, contre 161,0 pour N2 ; 7/20 parties ? earning_without_expansion ? dans chaque bras.
- **N0** : 143,6 v?hicules contre 162,8 pour N2 ; 12/20 parties N0 ? earning_without_expansion ?, contre 4/20 pour N2.
- **V250 mode 4** : 159,4 v?hicules contre 157,7 pour N2 ; 4/20 parties `stagnation_suspect` (`declining_without_expansion`) sur les graines **42, 73, 100 et 12345**. Les jeux et la mesure ? dix ans sont malgr? tout termin?s.

## V250 mode 4 : duel sp?cifique contre AAAHogEx

Donn?es prises sur les deux bras oppos?s ? **leur AAAHogEx respectif**, dans la campagne `v250_mode4_vs_master_n2_20x10_pc_20261018`, et non sur un AAAHogEx m?lang? entre les bras.

| Profit annuel moyen apr?s dix ans | R?f?rence N2 | Variante V250 mode 4 |
|---|---:|---:|
| OpexAI | 3 783 665,10 ? | **4 818 670,95 ?** |
| AAAHogEx oppos? | 7 845 156,50 ? | **3 893 974,45 ?** |
| OpexAI / AAAHogEx (rapport des moyennes) | **48,23 %** | **123,75 %** |
| Graines o? OpexAI d?passe AAAHogEx sur `profit_year` | 0/20 | **12/20** |

Sur ses mondes avec V250, AAAHogEx perd **50,36 %** de profit annuel moyen relativement ? son bras de r?f?rence. OpexAI gagne **27,35 %** de profit annuel moyen propre. L'effet offensif contre AAAHogEx est donc particuli?rement fort, m?me si la valeur de compagnie d'OpexAI se d?t?riore.

| Autre m?trique OpexAI | N2 | V250 mode 4 | ?cart |
|---|---:|---:|---:|
| Tr?sorerie moyenne finale | 15 272 324 ? | 3 831 410 ? | ?11 440 914 ? |
| Valeur de compagnie moyenne | 19 976 268 ? | 9 587 778 ? | ?10 388 490 ? (?52,00 %) |
| Profit annuel moyen | 3 783 665 ? | 4 818 671 ? | +1 035 006 ? (+27,35 %) |

V250 mode 4 ach?te des droits de transport exclusifs dans les villes cibl?es et peut les renouveler. La forte baisse de tr?sorerie est **compatible** avec ces sorties de caisse, mais les agr?gats ne suffisent pas ? certifier la d?pense exacte en droits ou le rendement marginal de chaque achat. L'id?e de limiter la d?pense est **une piste, non un changement impl?ment? ni une qualification**. Le comparatif V250 n?cessite le niveau personnalis? N3 car le niveau N2 coupe explicitement ce comportement.

**Verdicts op?rationnels :** garder N2 comme d?faut ; ne pas adopter N0 ni N1 sur ces donn?es ; ne pas adopter V250 mode 4 tel quel (garde de valeur d?pass?e), malgr? son avantage de profit de +23,75 % sur AAAHogEx. Aucune configuration n'a ?t? modifi?e lors de la publication des r?sultats.

## Artefacts versionn?s

Pour chaque pr?fixe ci-dessous, `results/` contient :

- `<pr?fixe>.json` : r?sum? et agr?gats complets du banc (dont les 20 paires et d?cisions) ;
- `<pr?fixe>.manifest.json` : param?tres, empreintes et provenance ;
- `<pr?fixe>.jsonl.gz` : t?l?m?trie mensuelle brute au format JSONL compress? gzip. **Les fichiers `.jsonl` non compress?s restent dans le workspace d'origine, non ajout?s au d?p?t Git**, pour ?viter ~216 Mo de blobs suppl?mentaires.

Pr?fixes :

1. `diff_n1_vs_n2_10x10_pc_20261018`
2. `diff_n0_vs_n2_20x10_pc_20261018`
3. `v250_mode4_vs_master_n2_20x10_pc_20261018`

Les gzip ont ?t? d?compress?s et v?rifi?s par SHA256 contre les JSONL bruts originaux :

| Pr?fixe | SHA256 du JSONL d?compress? |
|---|---|
| `diff_n1_vs_n2_10x10_pc_20261018` | `f73472d27d2bb4d0fa78047b3c3e619fec6eb85caac2350cd44ef472754c2e4a` |
| `diff_n0_vs_n2_20x10_pc_20261018` | `3307ebe9c45ed76347fc5dd7940e8fce71949f39766cdab4cb97fbc88b3499fc` |
| `v250_mode4_vs_master_n2_20x10_pc_20261018` | `e3ba0e67d53e43f64d5f8bc403c58391ab5050f4b0f895d8396735995689c9ca` |
