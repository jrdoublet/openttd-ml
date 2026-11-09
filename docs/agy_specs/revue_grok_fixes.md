# Revue des correctifs grok-fixes (PO-02, MULTI-1, EB-4)

Travail local sur `grok-fixes`. Aucun défaut de réglage n'est modifié.
Au défaut 0, les nouvelles branches sont fausses : le corps décisionnel
historique n'est pas exécuté. Load est l'exception demandée : il précède
`OpexLoadSettings`, donc il ne peut pas dépendre de la globale encore à 0.

## PO-02 — slot `fleet` et save complet

Défaut : `PO02_LAST_PUBLISH_DATE` n'avait pas de clé `fleet`, alors que
`OpexPO01CStart` parcourt `rail`, `road`, `water`, `fleet`, `air`. À
`po02_independent_expiry=1`, l'affectation `PO02_LAST_PUBLISH_DATE[mode] = now`
sans `<-` lève « the index 'fleet' does not exist » et tue l'IA.

Correctif :

- Initialiseur à cinq slots, `fleet = 0`. Le TTL de fleet reste la branche
  existante `(mode == "water") ? 90 : 30`, donc 30 jours. La spec ne nommait
  pas fleet ; on n'invente pas un TTL.
- Save complet (`save_full_state=1`, défaut) écrit `saveObj.po02LastPublishDate`
  sous le même `if (PO02_INDEPENDENT_EXPIRY)` que le short save, même clé.
- Load copie les cinq entiers dès que la clé est une table, sans lire
  `PO02_INDEPENDENT_EXPIRY`. Une sauvegarde à quatre modes reçoit `fleet = 0`
  et ne réinjecte pas la table brute. Clé absente : la table reste à zéro
  (le premier passage PO-02 estampille `now` sans forcer une régénération).

Risques :

- Au défaut 0, le save complet évalue un `if` faux de plus, et chaque Load
  évalue `("po02LastPublishDate" in data)`. Aucune clé n'est écrite, aucune
  date n'est restaurée si la sauvegarde n'en a pas.
- Les pins SHA de `globals_pre.nut` (ROAD100-B2, RAIL-OPEN, RAIL-SIBLING,
  RAIL-DEPOT-SIGNAL) acceptent le nouvel initialiseur. La ligne est hors des
  hunks ROAD100. L'empreinte gelée précédente reste dans les listes pour
  `origin/master`.
- EB-7 et AIR-COVERAGE restent écrits seulement sur le short save. Hors sujet.

## MULTI-1 — prédicat câblé, persistance, viviers étroits

Défaut : `OpexMulti1TriggerActive` n'était appelée nulle part. Le short save
écrivait `multi1LastBuildDate` seulement, et Load exigeait `MULTI1_RELANCE`,
encore à 0 avant `OpexLoadSettings`. Le `else` estampillait la date courante
dans Load, donc jamais.

Correctif, tout le comportement derrière `MULTI1_RELANCE` (défaut 0) :

- Sélection : si le levier est ≥ 2 et le prédicat vrai, `OpexMulti1CapSecondary`
  retire les projets `multi1Secondary` (projet ou `payload`) qui dépassent
  25 % de la caisse ou laissent moins de 1 000 000. Un `ai` null n'est pas
  un portefeuille vide. Le portefeuille lu est `MULTI1_ACTIVE_PORTFOLIO`,
  posé dans `OpexBuildProjects` (`priorProjects`), `OpexReselectProjects` et
  la re-sélection incrémentale, puis effacé avant le retour.
- Route : `OpexMulti1AppendRoadFeeders` après `OpexBuildRoadCandidates`,
  niveau ≥ 2 seulement. Villes 600..2000, Manhattan 20..50 vers un hub
  air/rail/route déjà en ligne, passagers seulement, au plus 4 candidats.
  Niveau 1 appelle le prédicat (log) et n'ajoute rien.
- Air : `OpexAirPlansStepNewPairs` élargit temporairement `bounds.airMin`
  vers 60 et `bounds.airMax` vers 150 pour `AT_COMMUTER` et `AT_LARGE`
  (city). `minDist` (30 ou 32) n'est pas relevé. Un `airMax` déjà supérieur
  à 150 n'est pas rabattu. Les bornes sont restaurées après l'appel.
- Save complet : `saveObj.multi1LastBuildDate` sous `if (MULTI1_RELANCE)`.
  Load restaure l'entier si la clé existe, sans lire le réglage. La grâce
  `GetCurrentDate` est dans `_reconcileAfterLoad`, après les réglages,
  seulement si la date est encore ≤ 0. Une partie neuve n'y passe pas.

Choix étroit, spec ambiguë sur le rail et l'eau : `MULTI1_LAST_BUILD_DATE`
n'est pas mis à jour par le rail ni l'eau. La spec §3.2-3.4 ne les nomme pas ;
les estampilles air et route existantes sont inchangées. Le courrier feeder
n'est pas émis : le seul producteur routier de courrier est le fret ROAD100.
Le plafond 25 % ne marque pas les plans air admis seulement parce que la
bande a été élargie. Pendant PO01C le global de portefeuille peut rester
null : seule la clause des 180 jours peut alors ouvrir le prédicat.
Le second chargeur de `settings.nut` n'est pas ajouté : un seul lecteur
existe déjà, et un second changerait le SHA de `settings.nut` sans effet
utile au défaut 0.

Risques :

- Au défaut 0, quelques `if (MULTI1_RELANCE != 0)` faux s'ajoutent sur la
  construction, la re-sélection, le pas air et le save complet. Les corps
  ne s'exécutent pas. Load évalue `("multi1LastBuildDate" in data)`.
- `GetClosestTown` ne tourne que dans le feeder, levier ≥ 2 et prédicat vrai.
- Les pins SHA de `globals_pre.nut` incluent `MULTI1_ACTIVE_PORTFOLIO`.
  La ligne est hors des hunks ROAD100 et du bloc retiré par le test V233.

## EB-4

(à compléter)
