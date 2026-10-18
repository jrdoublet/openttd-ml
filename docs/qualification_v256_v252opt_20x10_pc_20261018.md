# V256 : désactivation du rafraîchissement moteur AIR — qualification 20 × 10, 18 octobre 2026

## Protocole et provenance

- Branche `v252opt`, commit testé `4e9380bd0e00bd63387dd556334ef1ef03bd6dfb`, worktree propre pendant le banc (`dirty=false`).
- Campagne `v256_v252opt_20x10_pc_20261018` ; empreinte du bundle `f8ecee771e82d5f6a61fa0869fc45134e70b33867293cd9e8fb07e2ea5fa03bd`.
- Référence : `OpexAI[opex_difficulty=2]` ; variante : `OpexAI[opex_difficulty=2,v252_air_engine_refresh=0]`.
- Identifiant interne : `v256_v252off` ; différences effectives : `{"v252_air_engine_refresh": {"candidate": 0, "reference": 2}}`.
- Appariement C66.4 : 20 graines, 10 ans de jeu (1970–1979), 1 répétition, OpexAI opposé à AAAHogEx dans chaque bras. **40/40 jeux, 20/20 paires complètes, 0 échec.**
- Ressources : Docker `openttd-lab:latest` (empreinte `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`), 10 CPU, 8 Go, 10 workers ; campagnes lancées successivement, sans concurrence Docker.
- Graines : 42, 100, 7, 999, 2026, 1, 17, 73, 314, 512, 1024, 1337, 4096, 8191, 12345, 54321, 65537, 123456, 424242, 8675309.
- Règle `non_erosion`, métrique `profit_year`, gain utile minimal 0 %, garde de valeur (`company_value`) tolérant au maximum −5 %.

## Résultats comparatifs (variante moins référence)

| Indicateur | Résultat |
|---|---:|
| `profit_year` annuel moyen de la référence | 3,815,834.15 £/an |
| Δ profit annuel moyen | -353,984.15 £/an |
| Δ profit annuel médian | -368,248.50 £/an |
| Évolution relative du profit (rapport des moyennes) | -9.2767 % |
| Victoires / défaites / égalités sur le profit | 4 / 16 / 0 |
| IC95 bootstrap de Δ profit | [-545,838.90 ; -174,367.75] £/an |
| Test de Wilcoxon apparié sur le profit | p = 0.001209 |
| Δ valeur d'entreprise moyenne | -1,063,726.25 £ |
| Évolution relative de la valeur (rapport des moyennes) | -5.2981 % |
| Victoires / défaites sur la valeur | 8 / 12 |
| Critère primaire de non-érosion | Échec |
| Garde de valeur de −5 % | Échec |
| **Verdict automatique** | **`fail_primary_and_value_guard`** |

**Rejet** : perte de profit statistiquement établie (IC95 entièrement négatif) et garde de valeur franchissant le seuil de −5 %.

Dans ce protocole, le test `non_erosion` n'exige pas un gain strictement positif : il rejette la métrique primaire lorsque la borne supérieure de son IC95 bootstrap est négative. La garde de valeur est un critère séparé, fondé sur le rapport des moyennes.

**Précision :** La commande demandée annonçait `--variant-policy-id v256` et une variante sans niveau explicite. Le banc existant a utilisé `v256_v252off` et a fixé `opex_difficulty=2` dans les deux bras. Cela ne change pas la comparaison économique : la seule intervention effective est `v252_air_engine_refresh` passant de 2 à 0.

## Artefacts versionnés sur la branche

Dans `results/` :

- `v256_v252opt_20x10_pc_20261018.json` : résultats des 40 jeux, agrégats et 20 paires complètes.
- `v256_v252opt_20x10_pc_20261018.manifest.json` : provenance et configuration effective du moteur.
- `v256_v252opt_20x10_pc_20261018.jsonl.gz` : télémétrie brute compressée gzip (décompression vérifiée contre le fichier JSONL original). SHA-256 du contenu **décompressé** : `24888121b626de24a437a767a533d69ed214448b854f12dd38dcde7a1221d9e1`.

L'original `.jsonl` non compressé reste hors Git pour éviter un fichier de plus de 70 Mo. Aucun paramètre par défaut d'OpexAI n'a été changé ; l'adoption de la variante n'est pas justifiée.
