# Parameter cleanup evidence —12/10

Archives compactes et vérifiables des trois comparaisons demandées : C121 initial-project40×5, C122 regime-priority40×3, C122 threat-retry40×5. JSON finaux, manifestes, pré-enregistrements, synthèses/exposition et deltas par graine sont conservés, ainsi que leurs préalables disponibles et les deux smokes de retrait. Dix logs moteur du retry (ON/OFF des cinq graines exposées) permettent de relire les six relances et leurs suites locales.

`index.json` conserve chemins d'origine, tailles et SHA-256 des octets bruts et des gzip. Vérification sans Docker ni dossier de résultats :

```text
python -X utf8 evidence/review/parameter_cleanup_20261012/verify.py
```

Les sources figées complètes, caches, savegames et JSONL restent dans `results/`, hors Git. Cette archive ne suffit donc pas à rejouer les campagnes et ne prétend pas archiver tous les logs. Aucun verdict n'est requalifié : les trois comparaisons sont `fail_primary`; le retry a une sonde de menace commune=1, pas un témoin sondeOFF. Les smokes valident la santé/compilation, pas la rentabilité du nettoyage ni la neutralité d'opcodes.

[Passation et décisions](../../../docs/passation_nettoyage_parametres_20261012.md), [C12140×5](../../../docs/c121_initial_project_40x5_20261012.md), [C12240×3](../../../docs/c122_regime_priority_40x3_20261012.md), [retry40×5](../../../docs/c122_threat_retry_40x5_20261012.md), [audit des relances](../../../docs/c122_retry_reparation_audit_20261012.md).
