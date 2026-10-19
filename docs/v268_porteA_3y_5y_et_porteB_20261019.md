# V268 : 3 ans, 5 ans et porte B exploratoire — 19 octobre 2026

Provenance : branche `v268`, source du banc `ebbe92e9`, bundle commun `663097c5a4575a9a87a495fa0e8c759f7a7e4eb68466a1869195fe38127be3eb`. Même code et mêmes 40 graines (73 remplacée par 373684), en partie complète : `OpexAI[v268_c70_early=0]` contre `OpexAI[v268_c70_early=2]` avec AAAHogEx dans chaque duel. Campagnes 40/40 paires, 80/80 parties complètes et saines, 0 échec.

| Mesure de variante moins référence | 40×3 (1972) | 40×5 (1974) |
|---|---:|---:|
| Profit/an moyen | +45 608,55 £ | +59 344,975 £ |
| Delta médian | +41 672 £ | +65 766,5 £ |
| Victoires / défaites | 22 / 18 | 25 / 15 |
| Wilcoxon exact | p=0,25914 | p=0,149902 |
| IC95 bootstrap | [−26 802,775 ; +118 086,85] £ | [−34 530,175 ; +150 481,5] £ |
| Gain relatif / seuil 4 % | +2,17 % / +83 958 £ | +2,3501 % / +101 009 £ |
| Valeur compagnie, ratio des moyennes | +3,65945 % | +2,473201 % |
| Verdict | `fail_primary` | `fail_primary` |

Sur cinq ans : OpexAI référence 2 525 229,85 £/an, variante 2 584 574,825 £/an ; AAAHogEx du bras variante 3 121 749,525 £/an. Ni gain utile démontré, ni qualification. Valeur protégée. Le mode 2 reste OFF. Le banc 5 ans réutilise le même panel après l'échec à 3 ans, donc l'extension est exploratoire.

L'hypothèse d'une activation quasi nulle sur 3 ans n'est pas vérifiable dans les logs de ces bancs : `decision_log=1` n'était pas actif. L'usage des profits précoces par C70 exige notamment une ligne de moins de deux ans, une estimation/prédiction valide et au moins 180 jours d'observation d'un véhicule. Absence de trace ne signifie pas absence d'activation.

## Porte B commandée par dérogation

Malgré les échecs A, demande expresse de réaliser B dès que Docker est libre : 20×10, `non_erosion`, garde de valeur −5 %, 10 CPU / 8 Go / 10 workers, un seul conteneur. Les 20 graines canoniques sont les 20 premières de A (pas un holdout indépendant), 73 remplacée par 373684. Campagne `v268m2_porteB_20x10_pc_20261019`. Les deux bras ajoutent `decision_log=1` pour compter `V268_C70` et `V268_EST` et investiguer l'exposition : ce paramètre peut ajouter un coût d'opcodes par rapport à A. Script `sweeps/run_v268_porteB_pc.sh`. Les résultats B devront être considérés exploratoires, sans adoption automatique.

Archives publiées : JSON terminaux et manifests A40×3 (+smoke) et extension 40×5. Journaux moteur et JSONL volumineux conservés localement uniquement.