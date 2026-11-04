# Mission cloud : rendement des lignes bus d'AAAHogEx en route seule (3 ans)

Tu travailles sur le dépôt `jrdoublet/openttd-ml`, branche de départ `cloud/road1y-pack-0411` (= master 558f5bd8 + ce dossier). Réponds en français. Commence par lire `AGENTS.md` (§4 et §4.1), `ai/OpexAI/CLAUDE.md`, puis tout ce dossier `docs/cloud/road1y_0411/`.

## Objectif du projet
OpexAI (IA OpenTTD en Squirrel, `ai/OpexAI/`) doit atteindre 100 % du `profit_year` d'AAAHogEx à 3 ans, en duel **route seule** (bus, fourgons postaux, camions ; avion/rail/bateau coupés des deux côtés). Aujourd'hui, avec les défauts de master : Opex ≈ 527 k£/an, AAA ≈ 716 k£/an (40 graines, an 3), soit −188 k£.

## Ce qu'on sait déjà (lis les rapports, ne refais pas ces analyses)
- `agy_paxgap_rapport.md` : écart = bus voyageurs −94 k (50 %), courrier −51 k (27 %), camions fret −45 k (24 %). Sur les 48 paires de villes communes, profit par ligne IDENTIQUE (39,4 k vs 39,7 k). L'écart bus est sur les paires que nous ne partageons pas : AAA 30,2 k£/ligne avec 5,1 bus, nous 25,1 k£/ligne avec 7,3 bus ; paires AAA plus longues de ~10 tuiles (médiane 107 vs 98), villes de même taille. 54 % des bus AAA font > 6 k£/an, 20 % des nôtres.
- `agy_cash72_rapport.md` : la caisse oisive de 1972 n'est pas un blocage ; le rythme d'ouverture n'est pas en cause (Opex a de l'avance en 1970-71).
- `agy_mailgap_rapport.md` + `LEVIERS_TESTES.md` : courrier CLOS ; et la liste de TOUS les leviers déjà testés et rejetés ou adoptés. **Ne repropose aucun levier de cette liste** (fleet, weak, gap, mail2, next/next3, astar, bridge, far, rich_fleet, mail_min, dest_full, load_orders, spread_stops, spread_mail, mail_pick, mail_net, site_relocate, pax_bilat, freight ×2 et plafond camions…).
- Données : `n_spread2_gateA.jsonl.gz` (40 graines × 3 ans, télémétrie par ligne ; sépare les bras par `policy_id` : `spread2` = config actuelle de master, `reference` = sans spread_stops ; clé `run` = [ai, graine, 0]), `n_spread2_3y.jsonl.gz` + `engine_seed*.log.gz` (3 graines, journaux de décision complets des deux IA).
- Sources d'AAAHogEx (GPL, non suivies dans git) : `tar xzf docs/cloud/road1y_0411/AAAHogEx-115.tar.gz -C ai/` puis `ai/AAAHogEx-115/` (`route.nut`, `road.nut`, `station.nut`, `estimator.nut` surtout). **Ne committe jamais `ai/AAAHogEx-115/`.**

## Travail demandé
### Phase 1 — comprendre pourquoi les paires d'AAA rapportent plus (lecture de code + données, 1-2 h max)
1. Comment AAA choisit et classe ses paires bus (estimateur, distance, production, dénominateur profit/coût ou profit/temps), et comment il dimensionne la flotte d'une ligne (ajout, retrait, vente des bus en trop). Cite fichier:ligne.
2. Comparer avec OpexAI : génération des paires bus-quartier (`ai/OpexAI/bus_districts*.nut`, `candidates.nut`, `projects.nut`), score, renfort (`OpexRoad1yRefleetSaved` dans `bus_districts_overrides.nut`).
3. Confronter aux données : pour nos lignes et celles d'AAA, profit/ligne et bus/ligne en fonction de la distance et de la population ; d'où viennent nos 7,3 bus/ligne (renforts sans demande ? jamais de retrait ?).
4. Écris `docs/cloud/road1y_0411/RAPPORT_CLOUD.md` : la cause principale chiffrée et 1 à 2 leviers NOUVEAUX, chacun avec effet attendu chiffré (k£/an à 3 ans ; le seuil utile de la porte A est ≈ +21 k£/an).

### Phase 2 — coder le meilleur levier (un seul)
Règles du dépôt, toutes obligatoires :
- Nouveau réglage `road1y_<nom>` : `AddSetting` dans `info.nut` (4 `*_value` égaux à 0, défaut 0), globale MAJUSCULE dans `globals_pre.nut`, lecture + bornage + **forçage à 0 hors route seule dans LES DEUX chargeurs** de `settings.nut` (`OpexLoadSettings` et `OpexLoadBusDistrictSettings`, copier le motif de `ROAD1Y_SPREAD_STOPS`). À 0, le code exécuté doit être strictement l'ancien.
- Squirrel : pas de closure qui capture une locale ; `clone`, `base` réservés ; `const` = littéral seulement. Si `DECISION_LOG`, un `OpexDecide(...)` pour la mesure.
- Tests : nouveau `sweeps/test_road1y_<nom>.py` (contrats statiques, modèle `sweeps/test_road1y_spread_stops.py`) ; ajoute le réglage dans `sweeps/test_road1y_multimodal_gate.py` comme les autres ; mets à jour les blocs `after` de `sweeps/fixtures/road100_*_hunks.json` si un bloc touché y figure, et le plafond de `sweeps/test_v251_inventory.py`. Depuis la RACINE : `python3 -m unittest discover -s sweeps -p 'test_road1y*.py'`, `python3 -m unittest discover -s sweeps -p 'test_road100*.py'`, `python3 -m unittest discover -s sweeps -p 'test_v251*.py'` → tout vert.
- Commit sur une nouvelle branche `cloud/road1y-<nom>` créée depuis `cloud/road1y-pack-0411`, puis push de CETTE branche. **Jamais de push ni de fusion sur master, aucun changement de défaut.**

### Phase 3 — smoke sur GitHub Actions (si `gh` est disponible et authentifié ; sinon arrête-toi après le push et dis-le)
```
gh workflow run bench.yml --ref cloud/road1y-<nom> \
  -f mode=paired -f profile=custom -f years=3 -f seeds="613553 781335 100" \
  -f reference="OpexAI[mode_air=0,mode_rail=0,mode_road=1,mode_water=0]" \
  -f variant="OpexAI[mode_air=0,mode_rail=0,mode_road=1,mode_water=0,road1y_<nom>=<N>]" \
  -f aaahogex_settings=road_only -f line_telemetry=true
```
Suis avec `gh run view <id>` toutes les 10 min (pas `gh run watch`, quota API), télécharge l'artefact, et vérifie : parties complètes, 0 `noai_error`, mécanisme exercé (compteurs `OpexDecide`), profit_year par graine des deux bras et d'AAA. Un smoke 3 graines ne prédit pas une porte (duel non déterministe, ±18 %) : ne conclus rien d'économique, signale seulement si le mécanisme marche. Ne lance PAS de porte A/B (gain_short / non_erosion) : je les lance moi-même sur le VPS.

## Livrables
1. `docs/cloud/road1y_0411/RAPPORT_CLOUD.md` (phase 1 + résultat du smoke), commité sur la branche du levier.
2. Branche `cloud/road1y-<nom>` poussée, tests verts.
3. En fin de session : nom de la branche, hash du commit, réglage et valeur à banquer, lien du run Actions.
