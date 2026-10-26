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
V224, V290, V241, FRONT-PAX-1, V303, V308, PCAL-03, AIR-FLOTTE-1, RAIL-CAPEX-1, AIR-MONOPOLY-1, V250, PO-01 (suite PO-01c non qualifiée), programme historique de croissance RAIL (sous-lots clos) et V281 (portage obsolète), puis **PCAL-01 (V289 rejeté)** et **V294k (suivi fusionné dans V294)**, soit **dix-huit cases**.
Le reste comporte **23 cases** après les décisions utilisateur de
réouverture **V286** et de création **ESTIM-1** le 26/10 après-midi :
21 dossiers actionnables, deux
avec dépendance bloquante. Les estimations restent des **ordres de
grandeur relatifs**, pas une promesse de calendrier. Pour tout code
comportemental, OFF par défaut, tests/smoke/exposition et portes
pré-enregistrées restent obligatoires.

## C2 — études ciblées et sondes, effort modéré

| Ordre | Case | Effort / dépendance principale | Besoin de banc | Risque |
|---:|---|---|---|---|
| 1 | OPCODE-AILIST-2 | Moyen ; L1/L2 retirés, coût de création et cache | Mesure 1024² années 8–10 | Moyen |
| 2 | Désactiver les sondes non essentielles | Moyen ; `probes=0` déjà par défaut, C75_YEAR_LEDGER résiduel | Mesure opcodes puis neutralité B si optimisé | Moyen à élevé |
| 3 | AIR-ROI-LIGNE-1 | Moyen à élevé ; coûts réels, flotte modifiée et témoin | Hors ligne puis expérience même-save | Moyen à élevé |
| 4 | AIR-ROI-RENOUVELLEMENT-1 | Moyen à élevé ; V252, revente et contrefactuel | Hors ligne puis expérience même-save | Moyen à élevé |
| 5 | DIST-BORNES-1 | Moyen à élevé ; double écran V276/V269 sur 201–250 | Exposition 1024², puis porte si choix | Élevé |
| 6 | V249a | Moyen à élevé ; demande supplémentaire captable par gare/cargo | Shadow puis expérience | Moyen à élevé |
| 7 | V286 | Moyen ; mesures de stock par gare/cargo, remplissage effectif et production ; instrumentation passive d'abord | Observation moteur, sans porte comportementale à ce stade | Moyen |

## C3 — prototypes et validations dépendantes

| Ordre | Case | Effort / dépendance principale | Besoin de banc | Risque |
|---:|---|---|---|---|
| 8 | Mode fair_play explicite | Moyen à élevé ; audit existant, choix des comportements | Contrats niveaux et smoke, banc si comportement | Moyen à élevé |

## C4 — chantiers lourds dépendants de constructions ou de séquences

| Ordre | Case | Effort / dépendance principale | Besoin de banc | Risque |
|---:|---|---|---|---|
| 9 | V294 | Élevé ; A*, paramètres physiques et itérations, y compris futur périmètre tunnel/eau de V294k | Porte RAIL, puis B | Élevé |
| 10 | IDLE-1 | Élevé ; fusion V308/V309, réserve, carte invalidable et consommateur concret ; suite V303 par cartographie | 3×10 puis A/B si exposé | Élevé |
| 11 | PO-02 | Élevé ; PO-01c livré, publication/expiration de viviers | Exposition, A/B | Élevé |
| 12 | ESTIM-1 | Élevé ; coûts et profits marginaux, garde financière et témoins ; reprises RAIL-CAPEX, FRONT-PAX, AIR-MONOPOLY | Validation hors échantillon, même-save, puis A/B selon le correctif | Élevé |
| 13 | V240 | Élevé ; croissance urbaine retirée, devis géométrique nouveau | Démontrer activité puis A/B | Élevé |
| 14 | V242 | Élevé ; feeders et transport multimodal | Chaînes physiques, A/B | Élevé |
| 15 | V249b | Élevé ; marges réelles V249a et achats marginaux | A/B finance | Très élevé |
| 16 | V249c | Élevé ; surplus durable après V249b et choix intermodaux | A/B finance | Très élevé |
| 17 | V253 | Très élevé ; choix global d'avions, V252 et cycles de renouvellement | A/B AIR | Très élevé |
| 18 | V233 | Très élevé ; marchandises transformées, sources/débouchés et rivalité | Exposition causale, A/B | Très élevé |
| 19 | V226 | Très élevé ; réseau ferroviaire en araignée | Architecture, Save/Load, A/B | Très élevé |
| 20 | V251 | Très élevé ; construction d'industries et contrat économique de l'API | Exposition puis A/B | Très élevé |
| 21 | V291 | Très élevé ; terrassement/canaux uniquement au niveau permissif | Garde de sécurité, exposition, A/B | Très élevé |

## Bloquées : annoter et passer sans nouvelle expérience

| Case | Blocage concret | Reprise possible |
|---|---|---|
| V306 | Les journaux mesurent le revenu et le profit des lignes construites, mais pas le contrefactuel au choix ; les ratios de profit positifs excluent aussi les pertes réalisées | Formuler une hypothèse de classement marginal avec témoin même monde et portes A/B avant une table de décision |
| V261 | Audit/forum et tests déjà livrés, liste publique hébergée sur un tiers | Publication par le gestionnaire de tipsyfox.net/ottd/ |

Les dossiers d'un niveau ne sont pas interchangeables : une mesure
hors moteur n'autorise jamais à écrire une politique ON. Une tâche
sans données suffisantes reçoit un verdict documenté (« non exposée »,
« bloquée » ou « non qualifiée ») puis cède la priorité au dossier
suivant. Ne pas relancer les campagnes historiques exclues ni créer
de scripts de diagnostic pour simplement remplir une case.
