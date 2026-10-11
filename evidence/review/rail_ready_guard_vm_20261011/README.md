# P0 RAIL — preuve VM de la garde inéligible

[Rapport de mesure et limites](../../../docs/rail_ready_guard_vm_20261011.md).
Ce sous-paquet conserve l'essai r1 invalide et le lancement r2 valide,
leurs préinscriptions, la fixture détachée, les scripts et les sorties brutes.
L'index local contient les hashes SHA256 et tailles brutes/compressées.
Le grand index `evidence/review/index.json` reste inchangé.

La mesure porte exclusivement sur trois retours anticipés sans mutation :
surcoût ON−OFF de 15/25/40 opcodes par appel. Elle ne qualifie ni une
politique ferroviaire, ni un gain économique, ni un goulot CPU en partie.
Le code de production et les défauts ne changent pas.

Vérification en lecture seule, avec le vérificateur du sous-paquet précédent :

```text
python -B -X utf8 evidence/review/rail_ready_guard_vm_20261011/verify.py
```

Les archives des scripts peuvent être inspectées sans exécution. Les chemins
temporaires de `launch.json` ont disparu après l'essai ; les hashes du binaire
et des archives runtime restent dans les métadonnées. Ne pas relancer un
dossier déjà mesuré ni exécuter le script de préparation historique depuis
les archives pour remplacer une preuve.

Deux scripts intermédiaires locaux ont été retirés après vérification de leur
identité avec les archives. Les journaux, fixtures et préinscriptions restent
conservés ; le vérificateur accepte l'absence de ces doublons locaux.
