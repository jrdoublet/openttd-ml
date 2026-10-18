# RVA-15 — état appris minimal et invalidation

`sweeps/rva_learning.py:37` sérialise seulement version, empreinte de contexte,
date de sauvegarde et observations physiques terminées. La médiane exige de
conserver les observations, pas seulement une médiane impossible à mettre à jour
exactement. Aucun candidat, rang, recette de transfert ou effet réseau causal
n'est sauvegardé. JSON est le format du modèle **hors ligne**, pas le format
NoAI (les floats seraient interdits dans une sauvegarde NoAI).

Au chargement : version/empreinte incompatible, date future, observation
invalide/non finie ⇒ modèle froid avec cause. Les observations futures par
rapport à la sauvegarde sont refusées. Matériel, gares, cargos, distribution
et horloge appartiennent au contexte ; une nouvelle clé redémarre sans biais.
Le caller doit inclure profil, monde et version des données dans l'empreinte.

**Aucun apprentissage n'est consommé par le comportement Squirrel livré** : le
contrôle RVA-13 l'a dégradé. Il n'existe donc aucun état appris décisionnel
à ajouter à Save/Load. `persist.nut` et son format restent intacts. Les travaux
passifs/emprises/couvertures sont reconstructibles ;
`ai/OpexAI/rva_evaluator.nut:15` les remet à zéro après chargement des réglages
dans Start, uniquement sous le bit 256. Pas de cache observé avant Save
réutilisé après Load, pas de contexte station/matériel périmé conservé.

`test_rva_persistence.py:9` vérifie le roundtrip JSON, prédiction inchangée,
observations non futures, corruption/version/empreinte et absence de changement
du format de sauvegarde au défaut. Le roundtrip moteur réel est **MESURE
REQUISE** via `save_load_roundtrip.py` ; aucun appel moteur dans cette mission.
