# Étape 19 — Harnais — enregistreur mensuel partagé

- **SHA revu** : `421f14d`
- **Modèle / effort prévus** : Sonnet 5 / high
- **Périmètre** : `sweeps/diag_1v1_shared_monthly.py` — 1 238 l.
- **Plan** : `docs/revue_code_2026-09-15_plan.md`

**Enjeu annoncé**

Écrit le 09-13 (C66.2), jamais relu. Coût de la sonde au défaut, effet sur la trajectoire
mesurée, qualification des compteurs.

**Rappel de méthode** — diagnostic seulement, rien n'est corrigé au passage. Vérifier à la main,
pas par grep seul. Vérifier le défaut d'un réglage avant de le qualifier de code mort. Ancrer
chaque constat sur `fichier:ligne`. Ne lire que `ai/OpexAI/CLAUDE.md` et les fichiers du
périmètre : pas `docs/taches.md` en entier, pas les journaux, pas `results/`.

---

## Constats

### 19.1 — La sonde `monthly_funnel` est armée par construction dès `--shared`, sans réglage pour la désactiver        [gravité : P1]
`sweeps/diag_1v1_shared_monthly.py:609-610` — `shared = args.shared or args.funnel or args.air_town_limit_memory or args.town_station_detail or args.air_early_slot` puis `funnel = bool(args.funnel or shared)`. Dès que `shared` est vrai pour n'importe quelle raison (y compris `--town-station-detail` ou `--air-early-slot` seuls), `funnel` devient vrai aussi : il n'existe **aucun chemin de code** où `shared=True` et `funnel=False`. `build_arms` (ligne 542) arme alors `("monthly_funnel", 1)` sur l'instance OpexAI. Le docstring (ligne 16 : « Instrumentation OpexAI (derrière `monthly_funnel=0` par défaut) ») laisse croire que la sonde reste optionnelle ; en pratique, le mode `--shared` — l'usage documenté principal de ce script (docstring ligne 3) — la force systématiquement côté OpexAI, jamais côté AAAHogEx (qui n'a pas d'équivalent, ligne 14). Conséquence : ce harnais ne peut produire aucune paire de trajectoires « funnel ON » / « funnel OFF » en mode partagé pour isoler l'effet de la sonde sur la trajectoire mesurée (l'enjeu annoncé) — la comparaison OpexAI/AAAHogEx est structurellement asymétrique en coût d'instrumentation, sans qu'aucun réglage du script ne permette de le vérifier depuis ce fichier.

### 19.2 — Le mélange stock/flux relevé à l'étape 13 est propagé tel quel, sans correction ni avertissement        [gravité : P1]
`sweeps/diag_1v1_shared_monthly.py:360-366` — `parse_opex_funnel` fait `slot["considered"] += considered` (stock de portefeuille) au même titre que `for name in ("accepted","funded","attempted","built"): slot[name] += int(...)` à chaque ligne `MONTHLY_FUNNEL` (une ligne par passe du mois) : aucune distinction stock/flux, une simple somme. `monthly_aggregates` (lignes 822-825) resomme ensuite ces mêmes clés brutes à travers les graines avec `sum(...)` générique, y compris `considered`/`accepted` aux côtés de `attempted`/`built`. Le rendu (`render_monthly_report`, lignes 942-956) affiche ces valeurs sous l'en-tête unique « cand/acc/fin/tent/ok », laissant croire qu'elles sont sur la même échelle. Rien dans ce fichier ne normalise `considered`/`accepted` par le nombre de passes (`passes`, calculé ligne 360 et disponible) avant affichage ou agrégation : le lecteur hérite intégralement le biais identifié à l'étape 13 (taille du vivier × nombre de passes) et le diffuse dans le JSON de sortie (`funnel_by_seed`, `monthly[...]["funnel"]`) comme dans le tableau imprimé.

### 19.3 — `MONTHLY_FUNNEL_DETAIL` : absence d'émetteur ⇒ `None` silencieux, indiscernable d'un mois réellement sans activité        [gravité : P2]
`sweeps/diag_1v1_shared_monthly.py:391-481` — `parse_opex_funnel_detailed` ne matche que les lignes `MONTHLY_FUNNEL_DETAIL` (ligne 399) ; comme aucun `.nut` n'émet cette clé (constat hérité de l'étape 13, non rouvert ici), `by_month_mode` reste vide et la fonction retourne `{}` pour toute graine. `attach_logs` (lignes 520 et 528) affecte alors `record["funnel_detailed"] = None` pour chaque enregistrement OpexAI, sans test d'absence ni log. `monthly_aggregates` (ligne 831) filtre ces `None` (`if record.get("funnel_detailed")`), obtient une liste vide, et laisse `cell["funnel_detailed"]` à sa valeur d'initialisation `None` (ligne 750) — exactement le même résultat qu'un mois où le tunnel détaillé existerait mais n'aurait rapporté aucune activité. Aucun compteur ni avertissement ne permet de distinguer « émetteur absent » de « aucune activité ce mois ». Le selftest (lignes 1150-1177) construit à la main des lignes `MONTHLY_FUNNEL_DETAIL` synthétiques et valide le parseur sur ce texte fabriqué : il passe sans jamais exercer un run réel, masquant que ce chemin est mort en production.

### 19.4 — `qualified_modes` est capturé puis jamais lu : les compteurs eau (et leurs agrégats dérivés) sont mélangés aux modes qualifiés sans distinction        [gravité : P1]
`sweeps/diag_1v1_shared_monthly.py:108,140` — `vehicle_breakdown` recopie `dec["qualified_modes"]` dans son retour, mais ce champ n'est utilisé **nulle part ailleurs** dans le fichier (seules occurrences du terme dans tout le script). `physical_counters.py:46-51` déclare pourtant explicitement `QUALIFIED_MODES = {"rail": True, "road": True, "air": True, "water": False}` (commentaire : « Non exercé sur le banc de contrôle (0 navires construits) »), confirmant l'enjeu annoncé. Or `monthly_aggregates` (lignes 755-758) calcule `mode_totals` par `statistics.mean(...)` pour **tous** les `VEHICLE_MODES` sans condition, y compris `water` ; ce total est réinjecté tel quel dans le tableau imprimé (`mix`, ligne 911) et dans le JSON (`cell["by_mode"]`). Le même défaut de gating touche les agrégats qui ne sont même pas ventilés par mode : `n_units` (ligne 144, `dec["primary_vehicles_count"]`), `rolling_capital`/`capital` (lignes 127-146, somme sur tous les véhicules), `profit_total`/`profit_per_vehicle` (lignes 129-151) incluent les véhicules eau sans isolement possible, puisque la boucle (lignes 129-136) itère `dec["primary_vehicles_detail"]` sans filtrer sur la qualification. Conséquence : `rolling_capital`, `profit_per_vehicle` et `n_units`, repris dans `render_final_comparison` (lignes 995-1024) comme chiffres de synthèse OpexAI/AAAHogEx, intègrent silencieusement une donnée que le projet lui-même documente comme non qualifiée.

### 19.5 — Aucune métrique opcodes ni coût de sonde dans le schéma de sortie        [gravité : P2]
`sweeps/diag_1v1_shared_monthly.py:294-316` — `extract_company` construit le dictionnaire de champs par ligne (money, current_loan, company_value, income, expenses, profit, profit_year, delivered_cargo, vehicles, stations, funnel, hogex_builds, funnel_detailed) : aucun champ opcodes/CPU/coût de sonde n'existe dans ce schéma (recherche du terme « opcode » sur tout le fichier : aucune occurrence). Comme pour `bench_v2.py` (étape 18), ce harnais ne peut donc mesurer directement le coût de la sonde qu'il arme lui-même (19.1) — seul un effet indirect sur `company_value`/`vehicles`/`profit_year` serait visible, jamais la cause opcodes elle-même.

## Vérifié, n'est PAS un bug

- **Absence de test des signes / p-value dans ce script** — contrairement à `bench_v2.py` (relevé étape 18), ce script ne calcule aucun test statistique inter-graines (`render_final_comparison`, lignes 980-1027, affiche des valeurs et ratios par graine, sans agrégat de victoires ni p-value). Ce n'est pas une lacune propre à ce fichier : `ai/OpexAI/CLAUDE.md` (lignes 97-100) documente un cycle de validation à paliers — « sonde passive → diagnostic 5 graines × 6 ans → banc officiel 20 graines × 10 ans apparié, lu au test des signes d'abord ». `DIAG_SEEDS` (ligne 78, 5 graines) place explicitement ce script au palier « diagnostic », dont le rôle n'est pas de trancher statistiquement — cette responsabilité revient au banc officiel. Ne pas requalifier ce point en régression de ce fichier.
- **`physical_row_ok` et le fail-closed sur graines/mois manquants** (`monthly_aggregates`, lignes 693-731, testé par le selftest lignes 1082-1109) fonctionnent comme documenté : un mois incomplet ou une graine totalement absente ne produit jamais de moyenne partielle silencieuse — c'est le comportement voulu, vérifié à la main sur les trois scénarios du selftest (ligne manquante, chunk corrompu, graine absente).
- **`decode_vehicles`/`decode_stations` invalides** (`vehicle_breakdown` lignes 104-122, `station_detail` lignes 163-177) renvoient des dictionnaires à champs `None` de façon cohérente, sans lever d'exception ni de repli silencieux vers une valeur par défaut trompeuse.

## Hors périmètre, à relire ailleurs

- Le coût opcode réel de l'émission `MONTHLY_FUNNEL` / `MONTHLY_FUNNEL_DETAIL` (probablement `task_projects.nut`) est hors périmètre ici (fichier `.nut`, déjà signalé C66.2 par le plan) : ce fichier ne peut que constater que la sonde est forcée par le script (19.1), pas en chiffrer le coût.
- `physical_counters.py` (`QUALIFIED_MODES`, `decode_vehicles`, `FACILITY_BITS`) est un fichier distinct hors périmètre strict de l'étape 19 ; seule l'exploitation qu'en fait `diag_1v1_shared_monthly.py` (19.4) relève de cette étape.
- L'absence d'émetteur `.nut` pour `MONTHLY_FUNNEL_DETAIL` elle-même (côté écriture) a déjà été constatée à l'étape 13 ; 19.3 ne fait que vérifier la conséquence côté lecteur, sans rouvrir la question de l'émetteur.

## Passe de correction ? H5/G0bis, 2026-09-16

Le constat 19.5 est corrig?. Chaque checkpoint OpexAI lit les panneaux de co?t d?j?
pr?sents et `attach_opcode_deltas()` transforme les compteurs cumulatifs en co?t
mensuel par graine. Les cellules mensuelles publient `observed_opcodes`,
`observed_mopcodes`, le d?tail par composante et un ?tat explicite ; aucune valeur
n'est fabriqu?e pour AAAHogEx.

Validation r?elle : `results/review_h5_monthly_observed_ops_final.json`, 1v1 partag?
seed 42, 1 an. Les 13/13 checkpoints OpexAI ont
`observed_opcode_state=available` ; pour chaque mois,
`observed_opcodes_month == somme(observed_opcode_components_month)`. Exemples :
f?vrier 93 528 opcodes observ?s (82 000 s?lection + 11 528 planification air) ;
mars 875 858 (27 000 s?lection + 79 608 planification route + 769 250 build route).
Le co?t reste volontairement partiel : il ne devient pas un compteur CPU total.

## Passe B2 — 2026-09-16

Les constats 19.1 et 19.2 sont corrigés dans le code courant : `--no-funnel` autorise
`shared=True` avec `monthly_funnel=0`, et le schéma distingue désormais explicitement les
stocks moyens par passe (`considered`, `accepted`) des flux mensuels
(`funded`, `attempted`, `built`) via `metric_kinds`.

19.3 reste une **limite de couverture explicite**, pas une valeur silencieuse : aucun
`MONTHLY_FUNNEL_DETAIL` n'est émis côté IA, et le lecteur publie
`funnel_detailed_state=missing_emitter` lorsque la sonde est demandée. Il n'est donc plus
possible de confondre « aucune activité » avec « métrique non émise ». Aucun chiffre détaillé par
mode n'est inventé pour fermer artificiellement B2.
