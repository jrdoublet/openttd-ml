# Ordre de clôture des tâches encore ouvertes — 26 octobre 2026

Classement **par effort restant**, puis dépendances, preuve existante,
besoin de moteur/porte et risque pour les contrats de l'IA. Il ne
requalifie aucun résultat historique. Source autoritaire pour les cases :
[taches.md](taches.md). Un chantier bloqué est annoté puis sauté ;
aucune décision de défaut ou adoption n'est implicite. P1 est repris
sur le VPS, P6 abandonné et P3 est poursuivi uniquement via AIR-LOAD-1 :
ces trois parcours sont exclus des lots à lancer.

Au début du reclassement, **39 cases ouvertes** (dont quatre sous-cases
indentées). Les lots successifs du 26/10 ont déjà clos V304, V309,
V224, V290, V241, FRONT-PAX-1, V303, V308, PCAL-03, AIR-FLOTTE-1, RAIL-CAPEX-1, AIR-MONOPOLY-1, V250, PO-01 (suite PO-01c non qualifiée), programme historique de croissance RAIL (sous-lots clos) et V281 (portage obsolète), puis **PCAL-01 (V289 rejeté)**, **V294k (suivi fusionné dans V294)** et **V306 (table multiplicative non qualifiable, NO-GO)**, soit **dix-neuf cases**.
Le reste comportait **22 cases** après les décisions utilisateur de
réouverture **V286** et de création **ESTIM-1** le 26/10 après-midi.
**Deux clôtures documentaires de plus le 26/10, V240 et V294, abaissent
le total à 20 cases ouvertes** : 19 dossiers à instruire et un nécessitant
une publication externe (V261). V240 clôt sa tentative de croissance
urbaine sans hypothèse ciblée étayée ; V294 clôt ses essais A* non
qualifiés, tout en conservant leurs livraisons et rejets historiques.
La première sonde V286 a été instrumentée et validée au smoke moteur ;
sa tâche reste ouverte pour les livraisons et le coût observateur.
**La nouvelle tâche LATE-GAME-1 porte ensuite le total à 21 cases ouvertes** :
20 dossiers à instruire et V261 en attente d'une publication tierce.
LATE-GAME-1 est bloquée jusqu'à la parité de profit OpexAI/AAAHogEx
sur les 48 combinaisons date × mode × carte à cinq ans. V240 reste close ;
V251 et IDLE-1 sont liés à cette reprise tardive.
**Lot documentaire suivant : V251 est close comme suivi fusionné dans
LATE-GAME-1**, soit **20 cases ouvertes** (19 dossiers et V261 tiers).
L'inventaire V251 acquis reste consultable ; aucune industrie ne peut être
achetée au titre du late game avant réussite des 48 cellules.
Les estimations restent des **ordres de
grandeur relatifs**, pas une promesse de calendrier. Pour tout code
comportemental, OFF par défaut, tests/smoke/exposition et portes
pré-enregistrées restent obligatoires.

## C2 — études ciblées et sondes, effort modéré

| Ordre | Case | Effort / dépendance principale | Besoin de banc | Risque |
|---:|---|---|---|---|
| 1 | OPCODE-AILIST-2 | Moyen ; étude tardive L1/L2 explicitement demandée « pour plus tard » | **Bloquée sur N et opcodes L1/L2 en années 8–10 sur 1024²** ; les variantes de sonde avaient été retirées après les rejets initiaux | Moyen |
| 2 | Désactiver les sondes non essentielles | Moyen ; C75 annuel opt-in défaut 0 prêt, **bypass C75 et émetteurs de logs C121 encore à classifier** | Micro-opcodes puis B20×10 du seul C75 annuel ; poursuivre l'inventaire avant toute clôture globale | Moyen à élevé |
| 3 | V286 | Moyen ; stocks, charges et quantité sortie d'industrie relevés, sans livraisons attribuées à la ligne | Microcoût 42×3 de 22 000 ops ; **événement physique par ligne/cargo**, cas mixtes et effet observateur manquants | Moyen |
| 4 | AIR-ROI-LIGNE-1 | Moyen à élevé ; rétrospective 40 DUEL déjà close `not_identifiable`, coût net et témoin absents | Épisode pré-décision et coût d'infrastructure attribuable, puis AA/AA même-save | Moyen à élevé |
| 5 | AIR-ROI-RENOUVELLEMENT-1 | Moyen à élevé ; rétrospective 40 DUEL déjà close `not_identifiable`, revente et témoin absents | Coût net V252 daté et fourche achat/sans achat après AA/AA même-save | Moyen à élevé |
| 6 | DIST-BORNES-1 | Moyen à élevé ; **correctif expérimental opt-in OFF par défaut** des deux filtres fret 201–250 et du contexte V269 différé, sans clôture des bornes route/rail/AIR | Smoke 42×1 sain ; exposition tardive réelle 1024² absente, puis porte V102 si les choix changent | Élevé |
| 7 | V249a | Moyen à élevé ; V249s mode 2 évalue déjà gare/cargo mais captage concurrentiel non démontré | Observation au choix, témoin des gains captable et garde des doublons avant qualification | Moyen à élevé |

**Lot du 26/10 après `bca3c701` :** V286 instrumenté sur cinq graines
et trois ans (294 instantanés gare/cargo, 314 véhicules), mais la livraison
exacte par ligne et l'effet observateur restent inconnus : V286 conserve
son rang et sa case ouverte. Les deux sous-études de ROI AIR **fondées
uniquement sur les 40 journaux DUEL existants** sont closes en
`NO-GO méthodologique / not_identifiable` ; les demandes de ROI marginal
AIR-ROI-LIGNE-1 et AIR-ROI-RENOUVELLEMENT-1 demeurent ouvertes et
nécessitent des contrefactuels même-save plus coût net.
**Aucune nouvelle case racine fermée ; 20 cases ouvertes.**

**Sous-lot V286 complémentaire :** `src_transported_last_month_all` et
`V286_SAMPLE` désormais produits par la sonde préexistante en opt-in,
avec 35 passes et 22 000 opcodes sur la graine 42×3 et Save/Load sain.
Cette dépense de mesure n'est pas un gain d'opcodes. L'option reste
à 0 par défaut ; la sous-étape source/coût est instruite, mais la
case V286 ne peut être fermée sans livraison réelle par ligne,
cas mixtes et qualification de l'effet observateur.

**Sous-lot DIST-BORNES-1 du 26/10 :** grille fret, filtre `ALL` et
contexte de régénération tardive V269 réparés sous
`dist_bornes_v276_freight=1` (**défaut 0**). Contrats et smoke moteur
42×1 sains après correction de l'emplacement Squirrel du contexte.
L'exposition 1024² après activation de V269 manque toujours, ainsi
que la comparaison causale des choix, les portes et le traitement des
frontières route/AIR : tâche globale ouverte, **20 cases ouvertes**.

## C3 — prototypes et validations dépendantes

| Ordre | Case | Effort / dépendance principale | Besoin de banc | Risque |
|---:|---|---|---|---|
| 8 | Mode fair_play explicite | Moyen à élevé ; audit existant, choix des comportements | Contrats niveaux et smoke, banc si comportement | Moyen à élevé |

**Blocages vérifiés au HEAD `1b37fead` (26/10, sans nouvelle expérimentation) :**
`OPCODE-AILIST-2` a rejeté L1 sur **16 appels** et L2 sur **un appel** en
début de partie, sans tableau N/opcodes des années 8–10 sur 1024²
(`opcode_ailist_lots_20261023.md:11-29,89-91`). Les archives 1024²
disponibles n'ont pas été qualifiées comme mesure des variantes L1/L2 :
ne pas fermer cette demande ni extrapoler un seuil de rentabilité. Pour
`DIST-BORNES-1`, `candidates_v276.nut:139-145,278-280` applique deux
barrières voyageurs même au fret ; `candidates.nut:757-770` autorise
conditionnellement 201–250 tuiles et `orchestrator.nut:860-875` remet
`V269_RELAXED` à faux après la requête, alors que V276 peut reprendre
plus tard. L'effet physique et le nombre de paires perdues demeurent inconnus.
Le classement privilégie donc le passage au dossier suivant plutôt qu'un
verdict économique fabriqué.

La tâche globale « sondes non essentielles » ne sera **pas** close par
le seul B20×10 C75 : `C75_KPASS_BYPASS_LEDGER` est encore initialisé
(`settings.nut:358-360`) et alimenté même hors diagnostic dans
`task_projects.nut:1042,1235-1245` puis `probes.nut:2229-2300` ; distinguer
ces comptes de la décision `K_pass`. Les émissions `C121_FLEET_MARGINAL`
(`task_report.nut:61-64`) et `[FLEET_PROJECT]` (`task_projects.nut:344`)
méritent la même vérification de pure télémétrie. Aucun de ces postes
n'a une économie mesurée ni une qualification 20×10, et aucun réglage
par défaut n'a changé. L'audit du `fair_play` est livré
(`fair_play_audit_20261018.md`) ; le **choix utilisateur des comportements**
et le réglage distinct restent absents. Le profil de difficulté existant
ne vaut pas autorisation implicite de ce nouveau mode.

**26/10, complément C75 bis :** le registre bypass a désormais un
**second essai opt-in à défaut 0**, `c75_bypass_ledger_skip=1`. Sous
`probes=0`, il supprime la tenue du registre, les lignes de journal et les
panneaux associés, en laissant l'admission K_pass et le bypass local inchangés ;
`probes=2` conserve les traces (smoke 42×2 sain, résultat identique sur
les deux bras). Exposition 42×3 : 41 événements de référence contre zéro
dans la variante, 2/2 parties saines, mais delta de profit −72 712 £ sur
une seule graine, `diagnostic_only`. La microéconomie d'opcodes et le
contrôle 20×10 de non-érosion manquent avant une éventuelle adoption ;
les logs C121 et `[FLEET_PROJECT]` restent à classer. **Toujours 20 cases
ouvertes, sans fermeture globale prouvée.**

## C4 — chantiers lourds dépendants de constructions ou de séquences

| Ordre | Case | Effort / dépendance principale | Besoin de banc | Risque |
|---:|---|---|---|---|
| 9 | IDLE-1 | Élevé ; fusion V308/V309, réserve, carte invalidable et consommateur concret ; suite V303 par cartographie | 3×10 puis A/B si exposé | Élevé |
| 10 | PO-02 | Élevé ; PO-01c livré, publication/expiration de viviers | Exposition, A/B | Élevé |
| 11 | ESTIM-1 | Élevé ; coûts et profits marginaux, garde financière et témoins ; reprises RAIL-CAPEX, FRONT-PAX, AIR-MONOPOLY | Validation hors échantillon, même-save, puis A/B selon le correctif | Élevé |
| 12 | V242 | Élevé ; feeders et transport multimodal | Chaînes physiques, A/B | Élevé |
| 13 | V249b | Élevé ; marges réelles V249a et achats marginaux | A/B finance | Très élevé |
| 14 | V249c | Élevé ; surplus durable après V249b et choix intermodaux | A/B finance | Très élevé |
| 15 | V253 | Très élevé ; choix global d'avions, V252 et cycles de renouvellement | A/B AIR | Très élevé |
| 16 | V233 | Très élevé ; marchandises transformées, sources/débouchés et rivalité | Exposition causale, A/B | Très élevé |
| 17 | V226 | Très élevé ; réseau ferroviaire en araignée | Architecture, Save/Load, A/B | Très élevé |
| 18 | V291 | Très élevé ; terrassement/canaux uniquement au niveau permissif | Garde de sécurité, exposition, A/B | Très élevé |
| 19 | LATE-GAME-1 (inclut V251) | Très élevé ; V240 clos, volet industries V251 et IDLE-1 ; aucun code avant parité ≥100 % sur 1930/1950/1970/1990 × RAIL/AIR/ROAD/multimodal × 256²/512²/1024² | Matrice 48 cellules, cinq ans chacune, puis protocole du nouveau mécanisme | Très élevé |

## Bloquées : annoter et passer sans nouvelle expérience

| Case | Blocage concret | Reprise possible |
|---|---|---|
| V261 | Audit/forum et tests déjà livrés, liste publique hébergée sur un tiers | Publication par le gestionnaire de tipsyfox.net/ottd/ |

**V306 :** l'ancien blocage est clos avec verdict `NO-GO` sur la table
multiplicative proposée ; toute nouvelle hypothèse de profit marginal
et de classement va dans **ESTIM-1**. Les résultats descriptifs V306,
ainsi que les archives sources, sont conservés.

Les dossiers d'un niveau ne sont pas interchangeables : une mesure
hors moteur n'autorise jamais à écrire une politique ON. Une tâche
sans données suffisantes reçoit un verdict documenté (« non exposée »,
« bloquée » ou « non qualifiée ») puis cède la priorité au dossier
suivant. Ne pas relancer les campagnes historiques exclues ni créer
de scripts de diagnostic pour simplement remplir une case.
