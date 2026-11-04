# Mission cloud n°4 : fret routier — pourquoi AAAHogEx gagne ~45 k£/an en camions et nous presque rien (route seule, 3 ans)

Dépôt `jrdoublet/openttd-ml`, branche de départ `cloud/road1y-pack3-0411`. Réponds en français. Lis d'abord `AGENTS.md` §4/§4.1, `ai/OpexAI/CLAUDE.md`, `docs/cloud/road1y_0411/PROMPT.md` (contexte, règles du dépôt, données, sources AAA à décompresser, commande de smoke), puis `BILAN_MISSIONS.md`, `agy_freight_rapport.md`, `agy_freight2_rapport.md` et `agy_paxgap_rapport.md` (§ fret).

## Constat
- Écart total route seule à 3 ans : Opex 527 k£/an contre AAA 716 k£/an. Le fret routier en pèse ~45 k (24 %) : AAA ~3 lignes de charbon/bois par graine, ~45 camions, ~1 à 2,5 k£ par camion ; Opex ~0,12 ligne de fret par graine.
- AAA (3 graines, `agy_freight_rapport.md` §1) : la 1re ligne de charbon s'ouvre mi-1971 sur une mine de 130-210 t/mois à 70-80 tuiles, monte à 23-25 camions et fait 51-57 k£ en 1972 (2,0-2,5 k£/camion). Puis 4 lignes de plus en 1972, dont certaines à 177-207 tuiles. AAA prend aussi des mines très tôt (Cafingbridge au 15/01/1970 sur la graine 100, selon `agy_freight2_rapport.md`).
- Notre estimateur (`economy.nut` ~760-810, `OpexRoadLineEconomics`) : flux offert borné par `STATION_RATING_PCT = 50 %` (68 t/mois pour 136 t/mois produites), donc ≤ 17 camions et ~7,9 k£/an pour Cafingbridge. AAA en tire ~51 k£ avec 25 camions. **Cet écart d'estimation (×6) n'a jamais été expliqué.**

## Déjà essayé — ne pas refaire (branche `origin/road1y-freight`, base ANCIENNE d'avant `load_orders`/`spread_stops`)
- `28b62b3a` `road1y_freight` = plafond de camions relevé (12 ou 20) : résultats identiques, +5,9 k.
- `af087da9` = en plus ×2 sur profit/ROI du fret avant la sélection (contourne la troncature `PROJECT_TOP_K = 64` remplie de bus) : porte A 40×3 +5,4 k£/an, 17/23, p=0,91 ⇒ neutre. Du fret est construit, mais il ne paie pas plus que les bus évincés.
- Ni un simple bonus de score, ni un plafond de camions : la question est **pourquoi nos lignes de fret, une fois construites, rapportent bien moins que celles d'AAA**, et ce qui manque pour qu'elles rapportent autant.

## À faire
### Phase 1 — mesure (≤ 2 h)
1. Lire comment AAA construit, dimensionne et exploite une ligne de fret routier (`route.nut`, `road.nut`, `station.nut`, `estimator.nut`, `main.nut` : choix de l'industrie et de la destination, estimation de production, nombre de camions, chargement complet, gare et nombre de quais, dépôts, alimentation de plusieurs sources). Cite fichier:ligne.
2. Rebaser `af087da9` (fichiers `economy.nut`, `candidates.nut`, réglage `road1y_freight`) sur `cloud/road1y-pack3-0411` dans une branche de travail, et lancer un smoke GitHub de mesure à 3 graines (`probes=258` aux deux bras, `line_telemetry=true`, variante `road1y_freight=12`) pour obtenir des lignes de fret Opex réellement construites. Pour chacune et pour chaque ligne fret d'AAA : industrie, production mensuelle, % transporté, note de gare, distance, camions, chargement complet ou non, quais, temps de ramassage, profit 1972, date d'ouverture.
3. Expliquer chiffre à chiffre l'écart de profit par ligne entre nos lignes de fret et celles d'AAA (production captée, note de gare, nombre de camions, distance, vitesse/modèle, files au quai). Et l'écart d'estimation (×6) : quel terme de `OpexRoadLineEconomics` est faux.
4. Écrire `docs/cloud/road1y_0411/RAPPORT_CLOUD4.md` : cause principale chiffrée, effet attendu d'un levier en k£/an (seuil utile de la porte A ≈ +21 k£/an).

### Phase 2 — coder le levier (un seul, cohérent, éventuellement plusieurs règles ensemble)
- Réglage `road1y_<nom>` (défaut 0), règles du dépôt de `PROMPT.md` (info.nut 4 valeurs à 0, globale `globals_pre.nut`, lecture + forçage à 0 hors route seule dans LES DEUX chargeurs de `settings.nut`, pas de closure capturant une locale, `clone`/`base` réservés, `OpexDecide` sous `DECISION_LOG`, `sweeps/test_road1y_<nom>.py`, `test_road1y_multimodal_gate.py`, fixtures `road100_*.json`, `test_v251_inventory.py` ; depuis la racine `test_road1y*`, `test_road100*`, `test_v251*` verts).
- Le levier peut inclure `road1y_freight`/`af087da9` rebasé s'il est nécessaire à la construction, mais la mesure et le levier doivent porter sur le rendement d'une ligne de fret, pas seulement sur son admission.
- Branche `cloud/road1y-<nom>` depuis `cloud/road1y-pack3-0411`, push de cette branche seulement. Jamais master, aucun défaut changé.

### Phase 3 — smoke GitHub
Commande de `PROMPT.md` avec `probes=258` aux deux bras et la variante du levier. Suivi par `gh run view` toutes les 10 min. Si `gh workflow run` répond 403 ou que le jeton manque, arrête-toi après le push et dis-le (je lancerai le smoke sur le VPS). Vérifie : parties complètes, 0 erreur, lignes de fret construites, camions et profit par ligne de fret contre AAA, profit_year par graine. Pas de conclusion économique sur 3 graines, pas de porte A/B.

## Livrables
`RAPPORT_CLOUD4.md`, branche `cloud/road1y-<nom>` poussée, et en fin de session : branche, commit, réglage et valeur à banquer, lien du run.
