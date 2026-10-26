# MULTI-1 — premier levier ROUTE : NO-GO non exposé (26 octobre 2026)

**Pré-enregistrement immuable** : [`multi1_road_priority_prereg_20261026.md`](multi1_road_priority_prereg_20261026.md), publié dans `218362bc` **avant** code `9d1412bd`. Paramètre `multi1_road_priority=0` aux quatre niveaux, `1` shadow, `2` promotion bornée de ROUTE finançable derrière la tête économique non défensive, en 1971–1973. Aucun défaut changé.

**Code et tests** : commit `9d1412bd`, `git diff --check` propre ; **2 922** tests Python réussis (5 ignorés et 2 échecs attendus). Inventaire des **58 réglages historiques inchangé** et les assertions actuelles comptent **70** réglages déclarés dont cet opt-in. Aucun état de Save/Load nouveau. Le `0` garde la condition de sélection totalement inactive.

**Smoke 1×1** : `results/multi1_road_smoke_1x1_20261026.{json,jsonl,manifest.json}`, graine 42 × 1970, référence `0` / variante `2`, `probes=2`, même SHA bundle `a2c56583…`, **2/2 duels terminés**, pas d'erreur moteur ou de Squirrel. Effet nul, attendu car le levier ne s'active pas en 1970 : **smoke sain**, verdict statistique `fail_primary` à 1 graine sans portée économique.

**Save/Load** : `results/multi1_road_saveload_20261026.json`, graine 42 en solo, variante `2`, phase A 1970–1971 : **25 sauvegardes**, rechargement du **1er juillet 1971**, phase B 12 sauvegardes, preuve positive `LOAD_RECONCILE`, aucun marqueur d'erreur `CallLoad`/Squirrel, sortie `status=OK`. Le harnais solo ajoute une **compagnie fantôme inerte** après chargement, phénomène déjà décrit dans le rapport de sauvegarde ; ce test atteste la reprise technique, **pas** une égalité économique same-world. Les copies des sauvegardes sont archivées localement sous `results/multi1_road_saveload_20261026_work` (leur chemin original `/work/.scratch_saveload_multi1_20261026` figure dans le JSON).

**Exposition 5×5** : `results/multi1_road_exposure_5x5_20261026.{json,jsonl,manifest.json}` et `results/multi1_road_exposure_5x5_20261026_engine/`, graines préfixées **42,100,7,999,2026** × 1970–1974, `probes=2` / `--script-debug`, référence `0` vs ON `2`, 10 workers, un seul Docker, SHA source gelé identique `a2c56583…`. **5/5 paires complètes**, 0 `failed_runs`, 0 erreur script, bons états physiques. **Zéro événement `MULTI1_ROAD_PRIORITY` dans les cinq journaux ON**, donc **0/5 promotions** constatées, loin du **≥3/5** pré-enregistré ; aucune construction ROUTE ne peut être attribuée au mécanisme, critère **≥2/5** également non satisfait. Le TOP-K ou les seuils économiques n'ont jamais donné de cas éligible. L'écart de quelques véhicules ROUTE entre parties ON/OFF provient nécessairement d'autres variations de trajectoire (décalages d'opcodes/ticks) puisqu'aucune promotion n'a eu lieu.

Les bénéfices à fin 1974, sur ce petit échantillon, sont :

| Politique | Opex £/an moyen | AAA £/an moyen | Opex/AAA |
|---|---:|---:|---:|
| OFF, référence | 3 074 076 | 3 076 475 | **99,92 %** |
| ON, levier ROUTE | 2 845 881 | 3 221 490 | **88,34 %** |

Contraste apparié Opex ON−OFF : **−228 195,2 £/an** (2 victoires, 3 défaites), Wilcoxon bilatéral **p=0,3125**, IC95 bootstrap **[−469 036,8 ; +12 646,4] £/an**, ratio de valeurs **95,7155 %** (garde de −5 % tenue de justesse). **Ce banc est un test d'exposition, pas la porte A 40×5** ; ce gain négatif n'établit aucun effet causal de la promotion puisqu'elle ne s'est jamais produite. Le manifeste a enregistré `git_dirty=1` uniquement à cause des sauvegardes temporaires non suivies créées juste avant le banc ; elles ont ensuite été archivées sous `results/`, sans modifier le code ni le bundle. Cette provenance est explicitée, sans masquer l'indicateur historique du manifeste.

**Verdict ferme pré-enregistré : `NO-GO_NON_EXPOSE`, première variante refusée.** Ne jamais modifier ses seuils après coup, ne pas lancer A40×5 ni B20×10 pour `multi1_road_priority`, conserver défaut `0`. H3 reste un constat de flotte AAA, mais le portefeuille ROUTE propre ne franchit pas simultanément les critères de `fundScore`, profit et rang TOP-K. Un second levier doit cibler une cause **en amont** de la sélection ou l'usage coûteux de l'A* rail, après une nouvelle fiche de pré-enregistrement, sans requalifier le présent verdict.
