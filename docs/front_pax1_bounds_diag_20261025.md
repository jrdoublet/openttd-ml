# FRONT-PAX-1 — diagnostic passif des bornes, 25 octobre 2026

## Objet et pré-enregistrement

Objectif général de la mission : OpexAI ≥75 % du profit annuel d'AAAHogEx, moyenne ou médiane, duel 1970/256² 20×10 ou 40×10. Sur le master 83e436cc, la référence PC 20×10 vaut 56,5519 % en ratio des moyennes et 58,9112 % en médiane des ratios par graine. Il manque environ 1,345 M£/an à OpexAI à adversaire figé.

Worktree `/openttd-ml/.worktrees/nuit75-front-pax1`, HEAD `83e436cc3db35ff18efb685ace4f97eb569f77b1`, copie AAAHogEx-115 depuis le dépôt principal. Aucune modification du comportement ou des défauts. `candidates.nut` instrumenté sous `DECISION_LOG` (`probes=258`) : un événement `FRONT_PAX_BOUNDS` par `OpexRefreshEpochBounds` avec raison du fallback route, numérateur/dénominateur, distance brute RAIL/AIR, motifs de clamp, moteurs, airportType, vitesse divisée, temps par tuile et dwell RAIL. Les valeurs sont les paramètres du modèle **existant** ; le délai mécanique RAIL n'est pas ajouté à la politique de frontière. Zéro appel API ajouté si DECISION_LOG est désactivé ; quelques tests et affectations scalaires subsistent hors sonde, donc l'identité stricte en opcodes n'est pas revendiquée.

Smoke préalable 1 graine × 1 an `nuit75_frontpax1_smoke_1x1_20261025_r2` : duel complet 42, 0 erreur Squirrel, OpenTTD 15.3, bundle `a73a008240509583ff7d58b24e2f3f90e865cd72c11aa6dae24fa5a11198707f`, image `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`. Extrait 1970-01-02 : `road_reason=delta_nonpositive`, `rail_raw=439`, `rail_clamp=rail_max`, `rail_max=200`, `rail_tau100=29`, `air_tau100=23`, `rail_dwell100=864`, `air_fixed100=2619` : cause du plafond observée une seule fois, pas preuve de gain.

### Diagnostic pré-enregistré 5 graines × 5 ans

Campagne `nuit75_frontpax1_diag_5x5_20261025`. Un duel de référence par graine, code du worktree avec `OpexAI[probes=258]` contre AAAHogEx-115. Graines 42/100/7/999/2026, une répétition, départ 1970, carte `2^8=256²`, 5 ans, horizon 1974, 5/5 parties attendues, 9 workers, 10 CPU, 8 GiB, cache de référence, `--script-debug`. **Diagnostic seulement** : aucun bras ON/OFF, aucune porte A/B, aucun verdict d'adoption ; l'empreinte du bundle et du manifest sera relevée.

Mesures avant lecture : nombre d'événements par année/graine, histogramme des `road_reason`, `rail_clamp` et `rail_model`, dénominateur et numérateur, bornes brutes et finales, absence de script errors et dépassement d'opcodes. Le lecteur `sweeps/analyse_front_pax_bounds.py` résume les journaux, y compris couverture nulle et champs manquants. Ne pas extrapoler le nombre de nouveaux candidats AIR à partir de ces bornes ; FRONT-PAX-2 exigera une exposition des paires effectivement filtrées et de leur constructibilité, puis des fourches causales avant toute variante de politique.

Commande PowerShell :

```powershell
python -X utf8 sweeps/run_c66_reference.py --campaign nuit75_frontpax1_diag_5x5_20261025 --reference "OpexAI[probes=258]" --policy-id reference --years 5 --seeds 42 100 7 999 2026 --repeats 1 --start-year 1970 --map-size 8 --script-debug --cpus 10 --memory 8g --max-workers 9
```

## Résultats

Campagne `nuit75_frontpax1_diag_5x5_20261025` **terminée et saine : 5/5 duels, 10/10 compagnies `complete` et `game_ok`, `failed_runs=[]`, aucune erreur Squirrel, checkpoint final 1974-12-01**. Bundle `fd93c32d9f1fb91cb1d5e4fc40c4d4820668504d19bef171dfc335d390832024` ; manifest SHA256 `3b73d7c42bbfafe9fbd4f688c54d149b3ce413a71afd6d7a73c2efde611057fc` ; OpenTTD 15.3, OpenGFX 7.1, Docker `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.

| Mesure dans les logs `FRONT_PAX_BOUNDS` | Résultat |
|---|---:|
| Marqueurs valides / recalculs uniques / doublons exacts | **45 / 40 / 5** |
| Erreurs de parsing / fichiers sans graine | **0 / 0** |
| Années-graines avec marqueur / années-graines de jeu | **21 / 25** |
| `road_reason=delta_nonpositive`, `road_raw=-1` | **40/40** |
| `rail_model=crossing`, `rail_bound=v294` | **40/40** |
| `rail_raw=439`, `rail_source=200`, `rail_max=200` | **40/40** |
| Clamp exactement `rail_max` | **40/40** |
| `rail_road_floor=1` / `rail_map_cap=1` | **0 / 0** |

Par graine 7/42/100/999/2026, respectivement 4/6/21/4/5 recalculs uniques. Les années sans trace de rafraîchissement (1971 pour 7/999/2026 et 1974 pour 999) ne sont **pas des horizons manquants** : l'état des dix compagnies est validé indépendamment dans le JSON de campagne. Les événements répétés à l'identique un même jour sont dédupliqués pour les statistiques ; les 40 événements ne constituent pas 40 essais indépendants. Détail par graine/année et distribution des champs : `results/nuit75_frontpax1_diag_5x5_20261025_bounds_strict_validated.{json,md}`, **`--strict` exit 0**, 10/10 tests du lecteur. Les premières sorties `*_bounds_analysis.{json,md}` sont préservées.

Sur les quarante événements : `rail_tau100=29`, `air_tau100=23`, `rail_dwell100=864`, `air_fixed100=2619`, `air_div=4`. Le `road_M` varie de 80 à 159 mais la formule ROAD retourne avant un seuil brut (différentiel de revenu calculé nul). La frontière RAIL/AIR brute historique à **439 tuiles** est rabattue à **200 par le seul plafond V294** observé. Le dwell RAIL n'a pas été injecté dans les décisions ; la valeur 439 ne représente ni un seuil optimal ni une opportunité économique.

Au terme de 1974 : profit annuel moyen **OpexAI 2 948 112 £**, **AAAHogEx 2 907 548 £**, ratio des moyennes **101,40 %**, médiane des ratios par graine **91,99 %**. Aucun bras comportemental, aucune porte A/B, aucune preuve de progression vers les 75 % à dix ans (baseline master 20×10 : 56,5519 % et 58,9112 %). Profil partiel : **239 435 971 opcodes OpexAI observés sur 1 152 échantillons**, dont `rail_attempt` 167 318 286 (69,88 %), `air_planning` 29 860 174 (12,47 %), `road_planning` 25 725 060 (10,74 %). `observed_opcode_complete_cpu=false` sur les cinq jeux : le coût d'opcodes additionnel de la sonde et sa neutralité de trajectoire OFF/ON **ne sont pas mesurés**.

**Suite : FRONT-PAX-2 shadow** doit dénombrer les couples PASS/AIR réellement considérés puis rejetés sur 20–199 tuiles, séparés par `newpair`, `hubsite`, `hubhub`, les filtres suivants, l'existence d'un site, le devis/ROI et la constructibilité. Ne pas changer le seuil 200 ni extrapoler un gain à partir d'un recalcul de borne. Aucun défaut, commit, push ou merge changé.
