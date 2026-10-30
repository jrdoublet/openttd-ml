# RAIL-REPAIR-SITE et RAIL-REPAIR-V131 — prototypes isoles, 30 octobre 2026

**Base :** `729eafb8`, ESTIM31/EB14=3, gagnant AIR2,00/RAIL0,75.
**Etat :** code et tests hotes ; **aucune preuve de conversion physique ni de gain economique**.
Deux parametres publics independants, desactives aux quatre difficultes :
`rail_repair_join_site=1` et `rail_repair_v131_focus=1`.
Les defaults `v131_rail_repair=0`, `eb2_new_station_fallback=0`,
`v307_sites=0` restent inchanges ; l'ancien mecanisme V131c reste disponible.

## Site — le refus de quai parallele a une destination partagee

`OpexRailPlatformPlans` teste d'abord la jonction parallele historique. Si
**aucun** quai ne passe et si `candidate.shared_dest=1`, le mode SITE cherche
dans **deux anneaux** autour de la gare rail existante des quais orientables
différemment. Il recycle les controles physiques `OpexV264SpreadVisit` :
tuile plane et constructible, acces ferroviaire plat et `AIRail.BuildRailStation`
avec **le StationID original**, en `AITestMode`. Le plan garde l'origine,
la destination, le cargo et la longueur de quai contractuelle ; les sites
producteurs sont verifies a leur tour avant le lancement A*.

La nouvelle voie est distincte d'EB-2 : aucun remplacement par une gare
independante, aucune exception au garde `strictOriginReuseJoin`.
Elle est aussi plus bornée que le scanner integral V264 et ne change pas
V307S/R. `RAIL_SITE_REPAIR end=A|B src dst cargo options` note les cas physiques
testes ; `RAIL_ATTEMPT` et `RAIL_BUILD` portent `site_repair=1` seulement
si une solution de jonction de repli et l'autre extremite ont ete retenues.
Pour mesurer les OD recuperees, dedoublonner par `(seed,src,dst,cargo,kind)`
et exiger **`RAIL_BUILD` effectif**, devis reel, suivi du profit de la ligne.

**Limites connues :** ce repli ne sauve pas une source sans terrain de gare,
une destination sans aucun quai autorise par le moteur ni les `STNFAIL`
survenant plus tard pendant une construction reelle. Il ne renforce pas les
longueurs de quai ou la configuration de flotte. Les essais de jonction
en `AITestMode` constituent un prefiltre, pas la preuve qu'un chemin A*
et la pose finale seront possibles.

## Trace prepare — une seule obstruction locale

`rail_repair_v131_focus=1` active l'etat de recherche reprenable de V131
pour un plan stocke devenu `station_blocked`/`track_blocked`. Le profil rejette
plus de **4 tuiles** bloquees, plusieurs groupes d'obstacles et les detours
necessitant une recherche complete de gare a gare. Si le quai seul a disparu,
il n'accepte qu'une seule extremite endommagee, decalee de **4 tuiles** au
maximum et raccordee sur les quatre premieres/dernieres tuiles du trajet
stocke. Le cout A* est plafonne a **900 iterations** ; l'ancien V131c plafonnait
3 runs, 35 tuiles et 2 500 iterations. L'implementation exploite
`OpexV131PlanAnchorRun`, `OpexV131ApplySplice` et revalide les stations en
`AITestMode` puis chaque voie par `OpexTestRailTrack` avant commit.

La pose ulterieure passe toujours dans `OpexExecuteRailPlan`, qui fait le
devis reel, la garde de caisse et de slots, puis `OpexRollback` en cas
d'echec avant l'achat de trains. Le projet est refuse si l'option locale
est introuvable ; l'ancienne recherche large n'est pas lancee en secours.
Le journal `V131_REPAIR` indique `start`, `ok`, `fail` ou `fallback` avec
OD, nombre de segments et de tuiles, iterations et opcodes. Le profil
ajoute `cargo` et `focus=1` ; les evenements `RAIL_ATTEMPT` et `RAIL_BUILD`
portent aussi `v131_repair=1` pour identifier un chantier finalement pose.

Le pathfinder et le stock `railReadyStock` sont deja transitoires dans
`persist.nut` : `railSearchPending` declenche leur abandon sur `Load`,
l'invalidation du portefeuille et la reconstitution des plans. Aucun etat
persistant supplementaire n'est introduit, et aucun projet en cours n'est
converti en depense fantome. **Un roundtrip moteur reste indispensable** pour
observer ce comportement sur vraie partie.

## Hypothese et criteres enregistres avant toute mesure moteur

L'hypothese SITE est qu'une fraction des refus `SITEAB` a quai parallele
impossible dispose d'un quai **joint mais tourne**, dans les deux premiers
anneaux, sans avoir a reconstruire un reseau. L'hypothese V131-FOCUS est
qu'un incident ponctuel de carte vaut une petite reprise et evite la
surconsommation d'opcodes du V131c negatif. Les tests doivent prouver une
**construction et un profit reel supplementaires**, pas seulement une baisse
du compteur SITE ou un succes d'A*.

1. Smoke moteur OFF, SITE seul, FOCUS seul puis les deux, 1 graine × 1 an,
   sans erreur Squirrel, avec finances et ownership corrects. Roundtrip
   Save/Load avec recherche V131 pendante, annulation et reprise.
2. Exposition 5 graines × 5 ans, memes cartes/AAAHogEx, deux jeux apparies
   par option ; compter `RAIL_SITE_REPAIR`, `V131_REPAIR`, `RAIL_ATTEMPT`,
   `RAIL_BUILD` et benefice reel par OD unique. Si aucune construction
   additionnelle rentable, arreter **NO_GO_NON_EXPOSE**. Controle budget,
   opcodes, gares, vehicules, depot et absence de debrits physiques.
3. Seulement si expose et sain : porte A **40×5 multimodal** sur
   `profit_year` apparie, puis porte B **20×10** pour les variantes qui
   franchissent A. Conserver les seuils de porte en vigueur et preregistrer
   ensemble avant le lancement, sans selection post-hoc ; aucun changement
   de defaut avant validation. Les essais V131c 40×5 (`-31 550 £/an`)
   et EB-2 40×3 (`-19 100 £/an`) conservent leur `fail_primary` historique.

## Validation realisee sans Docker

Tests hotes : `test_rail_repair_site_v131_focus.py` (5/5),
`test_v131_rail_repair.py` (16/16), `test_v264_convergent_freight.py`
(10/10), `test_eb2_new_station_fallback.py` (5/5) et
`test_rail_geometry_guard.py` (12/12). `git diff --check` sain.
`test_v251_inventory.py` reste a **1 echec sur 7**, dans
`historical_info -> estim_off` (`ESTIM-1 info.nut hunk 0`), reproduit
egalement sur **`git show HEAD:ai/OpexAI/info.nut`** : deja casse sur la
base 729eafb8, voir `QUALITÉ-TESTS-ESTIM31`. Le seuil de comptage du test
est monte de 60 a 62 uniquement pour les deux controles publics.

**Non realises par ce worker (interdiction Docker) :** compilation Squirrel,
smoke moteur, verification physiquement causale, Save/Load reel, campagne
5×5, portes A et B. Les deux items restent donc **ouverts**.
