# T5 — Revue des plans de gare et de quai (4 novembre 2026)

## Résumé

1. **Le quai est court par construction économique, pas par le terrain.** Le modèle dimensionne
   **une** rame pour porter 50 % de la production (`STATION_RATING_PCT = 50`), en trajets par
   mois, puis traduit cette rame en quai : `(wagons + 2 + 2) / 2`. Deux à cinq wagons donnent
   donc 3 ou 4 tuiles. Le terrain ne fait que **raccourcir** (boucle descendante), jamais
   allonger (T5-01).
2. **Les jointures propagent la longueur courte** : un quai joint (sibling, destination
   partagée, V264) reprend `joinPlatform.length`, quel que soit le besoin du nouveau candidat
   (T5-04).
3. **Q3, défaut certain sous `rail_open=1`** (bras de référence) : un refus de jointure sans repli
   finançable rend `SITEA`/`SITEB`, ce qui bannit la paire 365 × n jours. Le cache RAIL-OPEN
   annonce pourtant « un refus n'est pas un abandon » (45 jours). Le pack compte **708**
   `skip_fallback` (T5-03).
4. **Q2, aucun plan ne regarde l'arrière du quai.** Le préférer coûte 0 £. Mesure livrée sous
   `decision_log` : `RAIL_BUILD ... back_a= back_b=`, avec le critère exact de RAIL-LOOP (T5-02).
5. **Q4, la note de gare (134 contre 196 dans le pack) relève du service, pas du placement.** Le
   site n'est qu'un filtre « capte > 0 » parmi les 12 plus proches, et la note OpenTTD dépend des
   jours sans enlèvement, de la vitesse et de l'âge du dernier véhicule et du stock en attente.
   Une rame unique et courte par ligne la plafonne (T5-05).

## Périmètre et provenance

- **Référence** : `ccr-6d627d08-tlnphk` au commit **`8268b653`**. Les numéros de ligne
  désignent ce commit.
- **Livraison** : branche `cloud/revue-rail-T5-20261104`, indépendante de T2 à T4.
- **Lecture** :
  - `builder_rail.nut:1-2027` : en entier pour `OpexStationPlans`, `OpexJoinPlatformPlans`,
    V264, `OpexRailTryPlatformLength`, RAIL-OPEN et `OpexRailPlatformPlans` ; en survol pour
    V307 (défaut 0, relève de T9) ;
  - `catalog.nut:20-60` ;
  - `economy.nut:193-420` ;
  - `rail_loop.nut:50-72`, `:230-240` ;
  - `task_rail.nut:260-500`, `:1416-1520`, `:1796-1803` ;
  - `lines.nut:236-292`.
- **Pack** : `docs/cloud_pack_20261104` (`per_seed.csv`, `logs_*.csv`). Médiane de la note de gare
  sur 1 509 parties : Opex **134**, AAA **196**.

## Constats, triés par gain attendu

Classes : **(a)** certain dans le code ; **(b)** probable ; **(c)** à vérifier en moteur.

| ID | Classe / gravité | Emplacement (`8268b653`) | Défaut | Correction | Gain attendu |
|---|---|---|---|---|---|
| T5-01 | (a) mécanisme, (b) effet ; perte de profit | `economy.nut:24`, `:266-276`, `:297-299`, `:399-401` ; `catalog.nut:38`, `:44-47`, `:56-60` ; `builder_rail.nut:1969-1977` | `wagons = ceil(0,5 × production / (capacité × trajets/mois))` : une rame unique, calibrée sur une note de 50 %. Quai = `(wagons + 2 marge + 2) / 2` tuiles, plafonné par `station_spread` puis `max_train_length`. Une ligne courte et fréquente donne 2 à 5 wagons, soit un quai de 3 ou 4. La recherche de site **descend** de `wanted` à 2 et ne propose jamais plus long. RAIL-LONG v1 à v3 (opt-in) contournent ce calcul au cas par cas | Sous opt-in : quai minimal **indépendant** de la rame initiale (par exemple 6 en fret si le site existe), la rame restant dimensionnée par l'économie. Le surcoût est de 2 × (6 − n) tuiles de gare par ligne ; le quai ensuite allongeable sert RAIL-LOOP/RAIL-FILL | Élevé si confirmé : c'est l'écart structurel avec AAA (7 tuiles). À mesurer en 40×5 rail seul, à cause de l'échec de RAIL-LONG (`docs/rail_long_20261103.md`) |
| T5-03 | (a) ; perte de profit, sous `rail_open=1` | `builder_rail.nut:1570-1576` (contrat), `:1886-1898` ; `task_rail.nut:1796-1803` ; `lines.nut:251-262` | Jointure RAIL-OPEN refusée et repli « nouvelle gare » non finançable (`OpexRailOpenNewStationFunded`) : retour `OpexRailSiteReason`, donc `SITEA`/`SITEB`, donc `_markPairAbandoned` sur la clé `freight\|cargo\|src\|dst`. La clé ne contient pas la jointure : **toute** variante de la paire est bannie 365 jours, puis 730. Le cache de 45 jours et le « repli si la caisse le permet » ne servent jamais | Opt-in, ou correctif dans la branche RAIL-OPEN : poser `candidate.railOpenJoinRefused` à `skip_fallback` et exclure ce cas du bannissement `SITE*`. Délai de 45 jours seulement. Non codé : le candidat reviendrait à chaque passe pendant le délai, ce qui demande un banc | 708 bannissements évitables dans le pack (contre 693 replis financés). Gain direct sur le levier sibling du bras de référence |
| T5-04 | (a) ; perte de profit | `builder_rail.nut:1787`, `:1806-1812`, `:1849-1854` ; `candidates.nut:1395`, `:1502` ; `lines.nut:456` | Un quai joint prend `jointLength = joinPlatform.length`. Avec `rail_sibling=1`, l'essentiel de la croissance passe par des jointures : la longueur courte de la première ligne se recopie sur toute la gare | Proposer aussi le quai joint à `max(jointLength, wanted)` si `OpexJoinPlatformPlans` le trouve, avec repli sur `jointLength` | Couplé à T5-01 |
| T5-02 | (a) ; robustesse, enjeu RAIL-LOOP | `builder_rail.nut:1117-1127` ; `rail_loop.nut:50-66`, `:236-237` | `OpexStationPlans` exige quai et `lead` libres et plats, jamais l'arrière (`anchor − step` ou `anchor + step × length`). RAIL-LOOP rejette ensuite `back_lead_A/B` (30 rejets au smoke 4×6, `docs/rail_loop_bancs_20261104.md`). Préférer un site à arrière libre ne coûte rien. **Le réserver** est impossible : une ville ou un tiers peut l'occuper | **Mesure livrée** (`back_a`/`back_b` dans `RAIL_BUILD`). Puis, sous RAIL-LOOP et en opt-in : trier les plans à arrière libre en premier, sans exclure les autres (l'A\* multi-source choisit déjà parmi 12) | Lever une partie des 30 `back_lead` ; à lire d'abord dans la mesure (arrière libre à la pose puis perdu, ou jamais libre) |
| T5-05 | (b) ; perte de profit, hors placement | `builder_rail.nut:1103-1133`, `:134-146` | Q4 : le site est le premier des 12 plans d'une spirale autour du centre, filtré par « capte > 0 » (fret) ou ≥ 8 (acceptation), sans tri par production (`V207_RAIL_PAX_SITE_RANK_PCT = 0`, et rien pour le fret). La note de gare OpenTTD ne dépend pourtant pas du site, mais du service (jours depuis le dernier enlèvement, vitesse et âge du dernier véhicule, stock en attente). L'écart 134 / 196 vient de la rame unique et courte (T5-01), pas du placement | Ne pas chercher le gain dans le placement. Il passe par plus de rames ou des rames qui attendent le plein (RAIL-LOOP/RAIL-FILL) et par des quais plus longs. Le tri V207 par production reste utile pour les gisements partiellement captés (opt-in existant) | Indirect |
| T5-06 | (a) ; style | `builder_rail.nut:1210-1260`, `:1352-1381` | `OpexJoinPlatformPlans` et `OpexV264TrySpreadAnchor` comptent `nCargo` sans tester la production (commentaire explicite) : les panneaux `PS` d'un échec de jointure surestiment « cargo » | Documentaire | Nul |

### T5-01 — Qui plafonne la longueur ?

| Étape | Source | Effet |
|---|---|---|
| Rame cible | `economy.nut:266-276` : `offered = mensuel × 50 %` ; `wagons = ceil(offered / (capacité × trajets))`, borné par `maxWagons` | Une rame porte la moitié de la production pour une seule rame par ligne |
| Quai souhaité | `catalog.nut:44-60` : `(wagons + 2 + 2) / 2`, plafonné par `station_spread` (12 par défaut) | 2 wagons → 3 tuiles ; 4 → 4 ; 6 → 5 |
| `max_train_length` | `economy.nut:239-241` (`maxWagons`) | Plafond haut, rarement atteint |
| Terrain | `builder_rail.nut:1969-1977` : `for (length = wanted; length >= floor; length--)` | Ne fait que raccourcir |
| Jointure | `builder_rail.nut:1787` | Recopie la longueur existante |
| Caisse | Aucune dans le choix de longueur (seulement RAIL-LONG v2/v3) | — |

AAA vise une rame longue qui attend le plein à quai. Opex vise une rame courte qui repart vite.
L'écart 3-4 contre 7 vient de là. Le terrain n'en est pas la cause.

### T5-03 — Le refus de jointure RAIL-OPEN devient un bannissement

```squirrel
// builder_rail.nut:1570-1573
/* RAIL-OPEN : ... Un refus n'est pas un abandon de la paire : pendant 45 jours, eviter de
 * recommencer la meme recherche de site et essayer directement le repli si la caisse le permet. */
// builder_rail.nut:1886-1898
if (EB2_NEW_STATION_FALLBACK == 0 && !railOpenFallback) {
  ... OpexDecide("RAIL_OPEN_SITE", "phase=skip_fallback reason=cash_or_profit" ...);
  return { plansA = null, ..., reason = OpexRailSiteReason(joinHasA, joinHasB), ... };
}
// task_rail.nut:1796-1803 : SITEA/SITEB/SITEAB -> this._markPairAbandoned(OpexAbandonedPairKey(candidate));
```

La paire bannie est filtrée avant `OpexRailPlatformPlans` (`task_rail.nut:368`). Le délai de
45 jours n'est donc jamais consulté pendant la première année. Le cas « la caisse le permet » ne
se produit qu'à l'échec initial. Le défaut ne concerne pas le défaut du jeu (`rail_open=0`), mais
le bras de référence de tous les bancs rail (`rail_open=1`).

## Réponses aux questions du prompt

**1. Pourquoi le quai reste-t-il court ?** Parce que l'économie le dérive d'une rame unique
calibrée sur 50 % de la production (T5-01). La jointure le recopie (T5-04). Le terrain ne fait
que raccourcir. La caisse n'intervient pas, hors RAIL-LONG v2/v3.

**2. Réserver une case libre à l'arrière ?**

- Préférer est possible à coût nul : un critère de tri des plans (T5-02).
- Réserver au sens strict ne l'est pas : rien n'empêche une ville ou un tiers d'occuper la case.
  Dans notre propre code, ni le dépôt (posé sur la voie, indices 1-2 côté sortie) ni le
  doublement (quais parallèles latéraux) ne visent l'arrière.
- La mesure `back_a`/`back_b` dira s'il faut trier (arrière jamais libre) ou si le problème naît
  après la pose.

**3. Jointure qui échoue en silence ou quai inutilisable ?**

- **Échec qui coûte cher** : T5-03.
- **Pas de quai inutilisable trouvé** :
  - `BuildRailStation` avec un `StationID` explicite échoue franchement plutôt que de créer une
    gare voisine ;
  - les plans joints exigent quai et lead libres et plats, et un test `AITestMode` de la
    jointure ;
  - la fenêtre V264 respecte `station_spread`, ce que confirme la vérification des bornes de
    `OpexV264SpreadWindow` ;
  - les deux sorties sont dédiées, sans aiguillage.
- La perte silencieuse est ailleurs : la longueur recopiée (T5-04).

**4. Captation et note 151 contre 212 (pack : 134 contre 196).** Le placement ne vise que « capte
quelque chose » (T5-05). Mais la note OpenTTD est une note de **service** : elle monte quand un
véhicule charge en permanence et quand l'enlèvement est récent. Une rame courte unique la
plafonne. Le levier est T5-01 avec RAIL-LOOP/RAIL-FILL, pas le site.

## Changement livré (branche `cloud/revue-rail-T5-20261104`)

- **Mesure** : `task_rail.nut`, dans le bloc `if (DECISION_LOG)` de `_recordRailAttempt`, ligne
  `RAIL_BUILD` d'une réussite. Champs `len_a`, `len_b`, `back_a`, `back_b`, avec
  `OpexRailLoopBackPlan`, c'est-à-dire le critère exact de `back_lead`. **Aucun effet au défaut.**
- **Projection OFF** : `sweeps/revue_rail_t5_off.py` en tête de chaîne (avant RAIL-KEEP). Elle
  restaure les octets de `8268b653`, est idempotente et refuse un hunk partiel. Les tests de
  projection de RAIL-LOOP, RAIL-FILL et RAIL-KEEP retirent d'abord cette couche ; le contrat P2
  (`+ p2Trace`) est conservé.
- **Tests** : `sweeps/test_revue_rail_T5_20261104.py`, 13 tests (placement sous `DECISION_LOG`,
  gardes `platformA`/`platformB`, critère RAIL-LOOP, contrats documentant T5-01 à T5-03,
  projection).
- **Suite complète** : avant 3 407 tests ; après 3 419 tests, **mêmes 4 échecs et 12 erreurs**
  préexistants (`test_b6_portfolio_causality`, deux `test_rail_long_v3_multi`,
  `test_v166_aaahogex_settings`).
- **Squirrel relu deux fois** :
  - commentaire placé entre deux opérandes `+` (accepté par le lexer) ;
  - `OpexRailLoopBackPlan` est défini dans `rail_loop.nut`, chargé après `task_rail.nut` mais
    résolu à l'exécution ;
  - pas de closure, de `const` ni de mot réservé.

## Plan de banc pour le PC

```powershell
$ref = 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1]'
$log = 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1,decision_log=1]'
$aaa = @('--aaahogex-setting','disable_veh_roadveh=1','--aaahogex-setting','disable_veh_tram=1',
         '--aaahogex-setting','disable_veh_ship=1','--aaahogex-setting','disable_veh_aircraft=1')

# 0. T5-03 sur des journaux EXISTANTS : skip_fallback suivi d'un ABANDON_PAIR de la même paire
Get-ChildItem .wt_rail_loop_20261104\results\rail_loop_non_erosion_rail_20x10_20261104_engine\*.log |
  ForEach-Object { $s = (Select-String $_ 'RAIL_OPEN_SITE phase=skip_fallback').Count
                   $n = (Select-String $_ 'RAIL_OPEN_SITE phase=new_station').Count
                   "$($_.Name) skip_fallback=$s new_station=$n" }

# 1. Compilation 1x1
docker run --rm --cpus=10 --memory=8g --memory-swap=8g -v openttd-lab-home:/home/lab -v "${PWD}:/work" -w /work openttd-lab `
  python3 sweeps/bench_v2.py --arms "OpexAI[decision_log=1]" --seeds 42 --years 1 --max-workers 1 `
  --out results/revue_t5_smoke_1x1_20261104.json

# 2. Smoke 4x6 rail seul, decision_log=1 (la mesure n'agit pas sur le jeu)
python -X utf8 sweeps/run_c66_reference.py --campaign revue_t5_smoke_4x6_20261104 `
  --policy-id reference --variant-policy-id revue_t5_log --reference $ref --variant $log `
  --decision-rule gain_short --min-useful-primary-delta-pct 4 --required-seeds 4 --required-years 6 `
  --years 6 --seeds 17 512 314 8191 --probes 6 --script-debug --line-telemetry `
  --mount-root 'C:\Users\jr\vscode\openttd-ml\openttd-ml' --cpus 10 --memory 8g --max-workers 10 `
  --value-guard-max-loss-pct 100 --out results/revue_t5_smoke_4x6_20261104.json @aaa
Get-ChildItem results\revue_t5_smoke_4x6_20261104_engine\*revue_t5_log*.log | ForEach-Object {
  $b = Select-String $_ 'RAIL_BUILD line=.* len_a=(\d+) len_b=(\d+) back_a=(\d) back_b=(\d)'
  $free = @($b | Where-Object { $_.Matches[0].Groups[3].Value -eq '1' -and $_.Matches[0].Groups[4].Value -eq '1' }).Count
  $lens = ($b | ForEach-Object { $_.Matches[0].Groups[1].Value } | Group-Object | ForEach-Object { "$($_.Name):$($_.Count)" }) -join ','
  "$($_.Name) builds=$($b.Count) both_back_free=$free len_a=[$lens]" }
```

**Critères de lecture.**

| Critère | Lecture |
|---|---|
| Santé | 8/8, 0 erreur NoAI, année de fin 1976 |
| `len_a` | Confirme la distribution 3-4 de T5-01 ; un 5 ou plus doit venir d'une rame de 6 wagons ou plus |
| `both_back_free` à la pose | Proche de 100 % : les `back_lead` naissent après la pose (ville, tiers), trier ne sert à rien. Faible : coder le tri opt-in T5-02, puis smoke 4×10 et porte B 20×10 (RAIL-LOOP ne paie qu'à 10 ans) |
| Étape 0, `skip_fallback` | Au-delà de 2 par graine en 20×10 : coder T5-03 (branche RAIL-OPEN, donc bras de référence), puis porte A 40×3 et porte B 20×10 |
| T5-01, quai minimal | Seulement après lecture de `docs/rail_long_20261103.md` (RAIL-LONG v1 à v3 non retenus) : définir une variante qui ne paie que le quai, puis porte A 40×5 rail seul |
