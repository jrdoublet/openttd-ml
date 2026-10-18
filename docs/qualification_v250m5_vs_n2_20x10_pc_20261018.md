# V250 mode 5 contre niveau N2 — qualification 20 × 10, 18 octobre 2026

## Protocole et provenance

- Branche `v250m5`, commit testé `dae8e9ea2e27d73545f55f95b7039c7de31d41fe`, worktree propre pendant le banc (`dirty=false`).
- Campagne `v250m5_vs_n2_20x10_pc_20261018` ; empreinte du bundle `c5d2b908fc6122e2a5bfc881e555a9a2368bc4c0cb619b0c4e5cd65ee4bb0638`.
- Référence : `OpexAI[opex_difficulty=2]` ; variante : `OpexAI[opex_difficulty=3,v250_rights=5]`.
- Identifiant interne : `v250m5` ; différences effectives : `{"opex_difficulty": {"candidate": 3, "reference": 2}, "v250_rights": {"candidate": 5, "reference": 0}}`.
- Appariement C66.4 : 20 graines, 10 ans de jeu (1970–1979), 1 répétition, OpexAI opposé à AAAHogEx dans chaque bras. **40/40 jeux, 20/20 paires complètes, 0 échec.**
- Ressources : Docker `openttd-lab:latest` (empreinte `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`), 10 CPU, 8 Go, 10 workers ; campagnes lancées successivement, sans concurrence Docker.
- Graines : 42, 100, 7, 999, 2026, 1, 17, 73, 314, 512, 1024, 1337, 4096, 8191, 12345, 54321, 65537, 123456, 424242, 8675309.
- Règle `non_erosion`, métrique `profit_year`, gain utile minimal 0 %, garde de valeur (`company_value`) tolérant au maximum −5 %.

## Résultats comparatifs (variante moins référence)

| Indicateur | Résultat |
|---|---:|
| `profit_year` annuel moyen de la référence | 3,765,589.05 £/an |
| Δ profit annuel moyen | -30,802.70 £/an |
| Δ profit annuel médian | +89,023.50 £/an |
| Évolution relative du profit (rapport des moyennes) | -0.8180 % |
| Victoires / défaites / égalités sur le profit | 13 / 7 / 0 |
| IC95 bootstrap de Δ profit | [-213,626.10 ; +136,829.45] £/an |
| Test de Wilcoxon apparié sur le profit | p = 0.869488 |
| Δ valeur d'entreprise moyenne | -6,207,553.35 £ |
| Évolution relative de la valeur (rapport des moyennes) | -30.9069 % |
| Victoires / défaites sur la valeur | 0 / 20 |
| Critère primaire de non-érosion | Réussi |
| Garde de valeur de −5 % | Échec |
| **Verdict automatique** | **`fail_value_guard`** |

**Rejet** : le critère statistique de non-érosion du profit est satisfait, mais la valeur recule de plus de 30 % (20 défaites sur 20 graines).

Dans ce protocole, le test `non_erosion` n'exige pas un gain strictement positif : il rejette la métrique primaire lorsque la borne supérieure de son IC95 bootstrap est négative. La garde de valeur est un critère séparé, fondé sur le rapport des moyennes.

**Précision :** La variante change conjointement le niveau de difficulté (N2 → N3) et `v250_rights` (0 → 5). Ce banc ne permet pas de séparer les effets de ces deux réglages.

## Artefacts versionnés sur la branche

Dans `results/` :

- `v250m5_vs_n2_20x10_pc_20261018.json` : résultats des 40 jeux, agrégats et 20 paires complètes.
- `v250m5_vs_n2_20x10_pc_20261018.manifest.json` : provenance et configuration effective du moteur.
- `v250m5_vs_n2_20x10_pc_20261018.jsonl.gz` : télémétrie brute compressée gzip (décompression vérifiée contre le fichier JSONL original). SHA-256 du contenu **décompressé** : `fefc66aca8298eab536329965e1fcb500d0e5945e4f60c60266ab118266c5f9e`.

L'original `.jsonl` non compressé reste hors Git pour éviter un fichier de plus de 70 Mo. Aucun paramètre par défaut d'OpexAI n'a été changé ; l'adoption de la variante n'est pas justifiée.
