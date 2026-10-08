# UR-15a / UR-16b — validation technique du 8 octobre 2026

Archives compactes du smoke et de la fixture NoAI finale r4 ; le fichier
`index.json` conserve chemins sources, tailles et SHA-256 bruts/compressés.
Décompression vérifiée à la création. Les sauvegardes volumineuses restent locales.

- Smoke seed42 ×1 an : complet/sain, compilation et exécution du code local.
- Fixture sur copie : sept scénarios rail à API synthétiques restaurées,
  champs identiques au corps pré-factorisation de `856c82c` ; 240 cas de
  calendrier issus des cinq lecteurs de production, décembre sauvegardé/rechargé.
- Deux phases : 13 sauvegardes chacune, 370 puis 371 assertions, santé et
  réconciliation vertes ; empreintes de la copie contrôlées. Garde des sources
  de production avant/après exécution réussie dans le lanceur final.
- r1/r2 : erreurs du hook de fixture, conservées dans `results/` ; r3 : première
  exécution saine ; r4 : confirmation du lanceur final avec garde de sources.

Ces fixtures ne prouvent ni gain économique ni gain d'opcodes. Les diagnostics
rail sont comparés sous API synthétiques ; les chaînes de log et l'ordre de
rollback sont aussi figés par les contrats statiques. Pas d'erreur physique
naturelle prétendue. Le test Save/Load vérifie l'estampille réelle, sans valider
un démarrage naturel du jeu en décembre ni toutes les politiques C121.
