# C88 — Reconnaissance des compagnies humaines et IA (08/10/2026)

**Verdict : clos, non réalisable de manière fiable depuis NoAI 15.3.**
Investigation statique du code actuel ; aucune modification de comportement,
aucun essai moteur. C88 ne concerne pas V88 (`goods_chain`).

## Frontière de l'API

Sources primaires du **tag officiel OpenTTD 15.3** (et non une documentation
`master` potentiellement postérieure) :

- [`src/script/api/script_company.hpp`](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_company.hpp)
  expose à `AICompany` les signatures
  `static ScriptCompany::CompanyID ResolveCompanyID(ScriptCompany::CompanyID company)`,
  `static bool IsMine(ScriptCompany::CompanyID company)`,
  `static std::optional<std::string> GetName(ScriptCompany::CompanyID company)`,
  `static Money GetBankBalance(ScriptCompany::CompanyID company)`,
  ainsi que diverses statistiques trimestrielles. Aucune fonction
  `IsAICompany`, `IsHumanCompany`, `is_ai`, `GetCompanyType` ou équivalente.
  `IsMine` teste **uniquement l'identité de la compagnie de ce script** ;
  `ResolveCompanyID` résout/valide un identifiant, sans qualifier son contrôleur.
- [`src/script/api/script_controller.hpp`](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_controller.hpp)
  expose notamment `static uint GetTick()`, `static int GetOpsTillSuspend()`,
  `static int GetSetting(const std::string &name)`,
  `static uint GetVersion()`, `Save()` et `Load()` : aucune inspection
  du contrôleur des autres compagnies. `GetVersion()` donne la version
  **d'OpenTTD**, pas la nature d'une compagnie.
- Aucune classe `AICompanyList` dans l'[index public NoAI](https://docs.openttd.org/ai-api/classes),
  et pas de `script_companylist.hpp` dans les fichiers API du tag 15.3.
  Une énumération d'identifiants avec `COMPANY_FIRST`/`COMPANY_LAST`
  et `ResolveCompanyID` identifierait au mieux des sociétés existantes,
  jamais leur contrôleur.
- [`src/script/api/script_tile.hpp`](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_tile.hpp) :
  `static ScriptCompany::CompanyID GetOwner(TileIndex tile)` donne un
  propriétaire de tuile, pas son type. La
  [`ScriptStationList`](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_stationlist.hpp)
  liste les stations **dont le script est propriétaire** ; elle ne fournit
  aucun inventaire humain/IA de toutes les compagnies.

La [définition du moteur `src/company_base.h`](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/company_base.h)
contient effectivement `CompanyProperties::is_ai` (booléen) et les fonctions
`Company::IsValidAiID(index)`, `Company::IsValidHumanID(index)`,
`Company::IsHumanID(index)`. Ce sont des membres/fonctions **C++ internes**,
qui ne figurent pas dans l'interface `ScriptCompany` exportée vers Squirrel.
La documentation du champ `is_ai` précise qu'un humain peut également
participer à une compagnie pilotée par NoAI : même côté moteur, ce champ
désigne la présence d'une IA, pas l'exclusivité du contrôle humain.

## Usage réel dans OpexAI

- `ai/OpexAI/air_coverage.nut:503-545` : le modèle C121 de concurrence
  visible trouve des **tuiles d'aéroports** adverses via `AIAirport.IsAirportTile`
  et `AITile.GetOwner`, écarte notre compagnie/les identifiants invalides,
  et déduplique par propriétaire. Il ne teste jamais humain contre IA.
- `ai/OpexAI/air_coverage.nut:547-651` : `AIStationList(STATION_ANY)`
  recense les stations propres pour calculer leur chevauchement ; avec la
  concurrence visible activée, le facteur rival est le **nombre de propriétaires
  d'aéroports visibles**, traité uniformément quelle que soit leur nature.
  Ce modèle est un proxy de couverture, sans visibilité sur le rating réel
  des aéroports étrangers ; C88 ne résout pas cette limite.
- `ai/OpexAI/event_handlers.nut:376-385,629-640` :
  `GetAwardedTo`/`ResolveCompanyID(COMPANY_SELF)` distinguent nos subventions
  de celles des autres ; `IsMine(AITile.GetOwner(...))` contrôle nos gares.
  Aucun de ces chemins ne réclame le type du contrôleur adverse.

**Conclusion d'utilité :** aucune décision courante de construction,
de sélection ou de concurrence recensée ne requiert de séparer les
compagnies humaines des compagnies IA. Une telle séparation aurait en plus
besoin d'une nouvelle politique, hors de C88.

## Moteur, sauvegardes et harnais : information non exportée

`sweeps/save_load_roundtrip.py:144-164` décode des sauvegardes via
`openttdlab.parse_savegame` et lit `chunks["PLYR"]`, notamment
`body.get("is_ai")` sur les autres compagnies. Le banc apparié
`sweeps/bench_1v1_5y_20seeds.py:1033-1047` lit aussi les compagnies
par propriétaire dans `PLYR`. Cette observation Python/Savegame est
**extérieure à la machine virtuelle NoAI** ; elle ne donne aucun
accès supplémentaire à `AICompany`.

`docs/journaux/journal_2026-09-13.md:2716-2744` et
`sweeps/save_load_roundtrip.py:464-482` décrivent une **compagnie fantôme**
apparue lors d'un rechargement headless, marquée `is_ai=0`, avec une
caisse initiale d'environ 100 000 £ sans activité observée. Le cas n'établit
pas un joueur humain ; le journal précise que l'essai avec `-D` ne
supprimait pas la compagnie. Cela invalide aussi l'inférence externe
`is_ai=0` ⇒ « humain actif ».

## Décision

**C88 clos : cas B, API NoAI absente/inaccessible.** Pas de sonde Squirrel
possible sur `is_ai` en 15.3, pas de substitut heuristique (nom, caisse,
véhicules ou performances), aucun nouveau paramètre et aucune suite
d'implémentation. Une éventuelle réouverture exigerait **une nouvelle
fonction publique documentée dans une autre version ciblée** d'OpenTTD.
