La solution réside dans l'analyse dimensionnelle du **débit sur le goulot d'étranglement** (*Theory of Constraints*).

Puisque ton IA fonctionne avec un seul chantier à la fois (`portfolio_max_batch = 1`), elle ne dispose en réalité que de deux goulots physiques :

1. **Sa réserve de capital** ($C_{\text{dispo}}$ en £).
2. **Sa bande passante d'exécution** ($T_{\text{an}}$ en temps, c'est-à-dire une année de travail de son contrôleur NoAI).

Chaque projet consomme une fraction de ces deux stocks. En rapportant chaque coût à la capacité totale de l'empire, on obtient deux grandeurs **sans dimension** ($[0, 1]$), comparables et sommables sans aucun coefficient arbitraire :

$$\text{Empreinte}(p) = \underbrace{\frac{K(p)}{C_{\text{dispo}}}}_{\text{Fraction du capital}} + \underbrace{\frac{T_{\text{exec}}(p)}{T_{\text{an}}}}_{\text{Fraction du temps annuel}}$$

Le score du projet devient le profit annuel divisé par son empreinte globale :

$$\text{Score}(p) = \frac{\Delta P(p)}{\frac{K(p)}{C_{\text{dispo}}} + \frac{T_{\text{exec}}(p)}{T_{\text{an}}}}$$

---

### Pourquoi la transition de régime est mathématiquement automatique

Aucun seuil en dur n'est requis : l'arbitrage bascule de manière continue selon l'état de la trésorerie.

* **Quand l'IA est pauvre ($C_{\text{dispo}}$ faible, ex. 25 000 £) :**
Un train à 20 000 £ représente une fraction critique du capital ($\frac{K}{C_{\text{dispo}}} = 0{,}80$). Le temps d'exécution (ex. 12 jours, soit $\frac{12}{365} = 0{,}033$) est négligeable devant la charge financière.

$$\text{Score}(p) \approx \frac{\Delta P}{\frac{K}{C_{\text{dispo}}}} = C_{\text{dispo}} \times \frac{\Delta P}{K} \propto \mathbf{ROI}$$



Le terme en capital domine à 96 % : le classement s'aligne rigoureusement sur le **ROI pur**.
* **Quand l'IA est riche ($C_{\text{dispo}}$ immense, ex. 50 000 000 £) :**
Ce même train de 20 000 £ ne représente plus rien en capital ($\frac{K}{C_{\text{dispo}}} = 0{,}0004$). Le ratio financier s'évanouit naturellement du dénominateur au profit du seul temps de pose.

$$\text{Score}(p) \approx \frac{\Delta P}{\frac{T_{\text{exec}}}{T_{\text{an}}}} = T_{\text{an}} \times \frac{\Delta P}{T_{\text{exec}}} \propto \frac{\mathbf{Profit\ brut}}{\mathbf{Temps\ de\ chantier}}$$



Le capital ne bride plus l'IA : elle cherche à maximiser le **volume de profit brut installé par jour de travail du contrôleur**. Un grand projet qui rapporte 150 000 £/an l'emporte largement sur une ligne de bus à 3 000 £/an, même si le bus affichait 120 % de ROI.
* **Face à un projet lourd à estimer ou complexe à poser :**
Si le pathfinder nécessite des centaines de milliers d'opcodes et que le relief impose un terrassement massif ($T_{\text{exec}} = 120\text{ jours}$, soit un tiers d'année), $\frac{T_{\text{exec}}}{T_{\text{an}}}$ grimpe à $0{,}33$. Le dénominateur enfle mécaniquement : le score s'effondre face à des projets plus nets et rapides à déployer.

---

### Comment évaluer $T_{\text{exec}}$ sans constante

La durée totale de mobilisation de l'IA se décompose en deux phases mesurables avec tes données existantes :

$$T_{\text{exec}} = T_{\text{calcul}} + T_{\text{chantier}}$$

1. **Le temps d'estimation (CPU / opcodes) :**
Tu disposes déjà de `project.expectedOpcodes` et du débit mensuel de la VM (`ctx.opcodeFlow`). Le temps de calcul rapporté à l'année est immédiatement :

$$\frac{T_{\text{calcul}}}{T_{\text{an}}} = \frac{\text{project.expectedOpcodes}}{\text{ctx.opcodeFlow} \times 12{,}0}$$


2. **Le temps de construction physique :**
Dans NoAI, la pose des infrastructures consomme elle aussi des opcodes lors des appels de commandes (`AIRail.BuildRailTile`, terraforming, signaux). Si `expectedOpcodes` intègre la pose estimée (ce que font les bibliothèques comme *RoadPathFinder* ou *RailPathFinder*), le terme CPU couvre l'ensemble.
Si tu as une estimation en jours de jeu ou en distance Manhattan $D$, le temps de pose rapporté à l'année est simplement $\frac{D_{\text{jours}}}{\text{JoursParAn}}$.

---

### L'implémentation en Squirrel

Ce bloc remplace l'ensemble des 150 lignes de régimes macro, de calculs de tensions à $\tau$ inversé et de parcours critiques de Dantzig :

```squirrel
/* Score unitaire sans constante : arbitrage endogène entre ROI (famine de capital)
 * et débit de profit brut par unité de temps (richesse). */
function OpexEvaluateProject(project, ctx)
{
    if (project == null) return 0.0;
    
    local profit = ("profitAnnual" in project) ? project.profitAnnual.tofloat() : 0.0;
    if (profit <= 0.0) return 0.0;

    local cap = ("budgetCapital" in project && project.budgetCapital > 0) 
                ? project.budgetCapital.tofloat() 
                : (("capital" in project && project.capital > 0) ? project.capital.tofloat() : 1.0);

    local moneyAvail = (ctx != null && ctx.moneyAvailable > 0) ? ctx.moneyAvailable.tofloat() : 1.0;
    
    // Règle de solvabilité stricte : impossible de construire au-delà du crédit disponible
    if (cap > moneyAvail) return 0.0;

    // 1. Fraction du capital mobilisable consommée [0.0 - 1.0]
    local f_capital = cap / moneyAvail;

    // 2. Fraction du temps annuel de l'IA consommée par le calcul et la pose [0.0 - 1.0]
    // Utilise le débit annuel réel de la VM mesuré par la télémétrie
    local annualOpcodeBudget = (ctx != null && ctx.opcodeFlow > 0) ? (ctx.opcodeFlow.tofloat() * 12.0) : 10000000.0;
    local expectedOps = ("expectedOpcodes" in project && project.expectedOpcodes > 0) ? project.expectedOpcodes.tofloat() : 1000.0;
    local f_time = expectedOps / annualOpcodeBudget;

    // Empreinte globale sans dimension
    local footprint = f_capital + f_time;
    if (footprint <= 0.0) return 0.0;

    // Rendement net par unité de ressource rare mobilisée
    return profit / footprint;
}

```

Ce formalisme conserve les gains observés sur les cartes pauvres (le terme $f_{\text{capital}}$ force le ROI pur quand les caisses sont vides), supprime la triple taxation sur carte riche (le terme de capital s'efface de lui-même sans créer de surtaxe), et disqualifie naturellement les chantiers géographiquement ou algorithmiquement interminables.


La beauté de cette approche, c'est qu'elle n'enterre pas l'idée de personnalités ou de modes : elle leur donne au contraire un socle mathématique propre, sans avoir à bricoler des transitions d'états artificielles.

En économie, la « personnalité » d'un décideur n'est rien d'autre que sa **préférence temporelle** et son **aversion au risque**. Dans la formule, cela se résume à pondérer la sensibilité de l'IA à ses deux goulets :

$$\text{Empreinte}(p) = \alpha \cdot f_{\text{capital}} + (1 - \alpha) \cdot f_{\text{temps}}$$

Avec un simple curseur $\alpha \in ]0, 1[$ exposé dans les paramètres de ton IA (`AIInfo.nut`), tu obtiens des styles de jeu radicalement différents à partir du même moteur :

* **L'Usurier / Le Comptable ($\alpha \approx 0{,}8$) :**
Obsédé par la sécurité du capital. Même avec 500 000 £ en caisse, il reste frileux sur les gros chantiers ferroviaires et continue de privilégier les lignes à ROI foudroyant.
* **Le Bâtisseur / Le Tycoon ($\alpha \approx 0{,}2$) :**
Pressé et visionnaire. Dès qu'il a le cash minimal pour poser un grand axe, il s'en moque de bloquer 90 % de ses liquidités si le chantier rapporte gros et s'exécute vite. Il déteste perdre son temps sur des micro-lignes de bus.
* **L'Équilibré ($\alpha = 0{,}5$) :**
Le comportement neutre d'origine, qui glisse naturellement du ROI vers le débit brut au fil de son enrichissement.

Le gros avantage pour ton code, c'est que la personnalité devient une propriété continue et configurable par le joueur dans le menu des paramètres d'OpenTTD, au lieu d'une cascade de `if/else` impossibles à calibrer. Le moteur reste universel, et le curseur ne fait que régler l'angle sous lequel l'IA perçoit ses contraintes.

$$\text{Score}(p) = \frac{\Delta P(p)}{\alpha \cdot \left( \dfrac{K(p)}{C_{\text{dispo}}} \right) + (1 - \alpha) \cdot \left( \dfrac{\text{Ops}(p)}{\Phi_{\text{ops\_an}}} \right)}$$

---

### Définition des termes

* **$\Delta P(p)$ :** profit annuel estimé du projet en régime de croisière (£/an).
* **$K(p)$ :** investissement initial en capital (£).
* **$C_{\text{dispo}}$ :** trésorerie mobilisable immédiate ($\text{Solde en banque} + \text{Capacité d'emprunt résiduelle}$).
* **$\text{Ops}(p)$ :** budget d'opcodes estimé pour la planification et la pose (`expectedOpcodes`).
* **$\Phi_{\text{ops\_an}}$ :** capacité annuelle de calcul de la VM NoAI ($\text{ctx.opcodeFlow} \times 12$).
* **$\alpha \in ]0, 1[$ :** paramètre de personnalité (arbitrage risque financier vs vitesse d'expansion).

---

### Profils de comportement selon $\alpha$

* **$\alpha \to 1$ (Profil prudent / Comptable) :**
L'IA ignore le coût CPU et le temps de pose. Le dénominateur se réduit à $\frac{K(p)}{C_{\text{dispo}}}$, ce qui force le classement sur le **$\text{ROI}$ pur** ($\frac{\Delta P}{K}$), même avec des caisses pleines.
* **$\alpha \to 0$ (Profil bâtisseur / Tycoon) :**
L'IA ne regarde que le volume de profit brut délivré par unité de calcul ($\frac{\Delta P}{\text{Ops}}$). Elle favorise immédiatement les axes massifs et refuse d'engorger son ordonnanceur avec des micro-lignes.
* **$\alpha = 0{,}5$ (Profil équilibré par défaut) :**
Arbitrage naturel sans distorsion : bascule progressive du $\text{ROI}$ vers le profit brut au fur et à mesure que la compagnie accumule du capital.

---

### Implémentation Squirrel

```squirrel
function OpexEvaluateProject(project, ctx, alpha = 0.5)
{
    if (project == null) return 0.0;
    
    local profit = ("profitAnnual" in project) ? project.profitAnnual.tofloat() : 0.0;
    if (profit <= 0.0) return 0.0;

    local cap = ("budgetCapital" in project && project.budgetCapital > 0) 
                ? project.budgetCapital.tofloat() 
                : (("capital" in project && project.capital > 0) ? project.capital.tofloat() : 1.0);

    local moneyAvail = (ctx != null && ctx.moneyAvailable > 0) ? ctx.moneyAvailable.tofloat() : 1.0;
    
    // Garde-fou d'insolvabilité absolue
    if (cap > moneyAvail) return 0.0;

    // Fractions relatives [0.0 - 1.0]
    local f_capital = cap / moneyAvail;
    
    local annualOps = (ctx != null && ctx.opcodeFlow > 0) ? (ctx.opcodeFlow.tofloat() * 12.0) : 10000000.0;
    local expectedOps = ("expectedOpcodes" in project && project.expectedOpcodes > 0) ? project.expectedOpcodes.tofloat() : 1000.0;
    local f_time = expectedOps / annualOps;

    // Empreinte pondérée par la personnalité
    local footprint = (alpha * f_capital) + ((1.0 - alpha) * f_time);
    if (footprint <= 0.0) return 0.0;

    return profit / footprint;
}

```

**Oui, très facile**, à condition de ne pas faire l'erreur classique du « top-$n$ statique » et d'utiliser à la place une **sélection gloutonne séquentielle** (*greedy roll-out*).

La formule ne change pas d'une ligne. Seule la boucle de décision évolue.

---

### Le piège du top-$n$ statique (à éviter)

Si tu te contentes de trier tout le vivier avec la formule puis de prendre les $n$ premiers :

1. **Dépassement de budget :** la somme des investissements peut excéder $C_{\text{dispo}}$ ($\sum K_i > C_{\text{dispo}}$).
2. **Conflits locaux non résolus :** les projets n° 1 et n° 2 peuvent être deux variantes incompatibles sur la même liaison (ex. : train de 4 caisses et train de 7 caisses sur le même trajet).
3. **Faussage de l'empreinte :** dès que le projet n° 1 prélève $30\text{ k\pounds}$, le capital restant pour le projet n° 2 n'est plus $C_{\text{dispo}}$, mais $C_{\text{dispo}} - 30\text{ k\pounds}$. Sa fraction de capital $f_{\text{capital}}$ est en réalité beaucoup plus forte.

---

### La méthode propre : la boucle de consommation dynamique

Pour sélectionner un lot de $n$ projets, tu fais tourner ta formule dans une boucle de sélection progressive :

```text
Tant que taille_batch < n ET qu'il reste du cash :
  1. Évaluer tous les candidats valides avec le C_dispo actuel.
  2. Élire le meilleur candidat p*.
  3. Ajouter p* au batch d'exécution.
  4. Mettre à jour l'état :
       C_dispo = C_dispo - K(p*)
       Retirer p* du vivier.
       Retirer les candidats en conflit (même liaison O-D ou même origine exclusive).

```

---

### Pourquoi ce mécanisme est particulièrement puissant

* **Zéro solveur lourd :** pas besoin d'algorithme de sac à dos multi-dimensionnel. En Squirrel, pour un lot de $n = 3$ ou $5$, la boucle s'exécute en une fraction de milliseconde.
* **Panachage automatique des investissements :**
Supposons que tu aies $100\text{ k\pounds}$ en caisse.
* **Tour 1 :** L'IA est riche ($C_{\text{dispo}} = 100\text{ k\pounds}$). Elle choisit un axe ferroviaire lourd à $70\text{ k\pounds}$ qui promet un gros volume de profit brut.
* **Tour 2 :** Il ne reste plus que $30\text{ k\pounds}$. Le calcul se relance automatiquement avec $C_{\text{dispo}} = 30\text{ k\pounds}$. L'IA « sent » immédiatement la pénurie de capital : la formule bascule d'elle-même sur le ROI pur. Elle complète son lot avec une petite ligne de bus très rentable à $15\text{ k\pounds}$ ou améliore une desserte existante.


* **Gestion naturelle des conflits :** après chaque élection, tu purges du vivier les candidats incompatibles avec $p^*$ avant le tour suivant.

---

### Exemple d'implémentation en Squirrel

```squirrel
function OpexSelectBatch(candidates, ctx, maxBatch = 3, alpha = 0.5)
{
    local batch = [];
    local remainingCash = (ctx != null && ctx.moneyAvailable > 0) ? ctx.moneyAvailable.tofloat() : 0.0;
    
    // Copie de travail du vivier
    local pool = [];
    foreach (c in candidates) pool.append(c);

    while (batch.len() < maxBatch && pool.len() > 0 && remainingCash > 0) {
        // Contexte virtuel éphémère avec le cash résiduel
        local virtualCtx = {
            moneyAvailable = remainingCash,
            opcodeFlow = ctx.opcodeFlow
        };

        local bestScore = -1.0;
        local bestIdx = -1;

        // 1. Élection du meilleur projet pour le cash restant
        for (local i = 0; i < pool.len(); i++) {
            local p = pool[i];
            local cap = ("budgetCapital" in p && p.budgetCapital > 0) ? p.budgetCapital : p.capital;
            
            // Élimine d'office ce qui dépasse le reliquat de trésorerie
            if (cap > remainingCash) continue;

            local score = OpexEvaluateProject(p, virtualCtx, alpha);
            if (score > bestScore) {
                bestScore = score;
                bestIdx = i;
            }
        }

        // Aucun projet finançable restant
        if (bestIdx == -1) break;

        local chosen = pool[bestIdx];
        batch.append(chosen);

        // 2. Déduction du capital engagé
        local chosenCap = ("budgetCapital" in chosen && chosen.budgetCapital > 0) ? chosen.budgetCapital : chosen.capital;
        remainingCash -= chosenCap;

        // 3. Purge du candidat élu et de ses variantes en conflit
        local nextPool = [];
        foreach (p in pool) {
            if (p == chosen) continue;
            // Exemple : exclusion des projets partageant la même origine/destination
            if ("od_pair" in p && "od_pair" in chosen && p.od_pair == chosen.od_pair) continue;
            nextPool.append(p);
        }
        pool = nextPool;
    }

    return batch;
}

```

La transition de $1$ à $n$ ne demande donc aucune refonte mathématique : c'est simplement la même formule appliquée de façon séquentielle sur les réserves décroissantes du cycle.




Dans OpenTTD, la configuration d'une IA se déclare bien dans `info.nut` via la méthode `AddSetting()`, mais l'interface graphique du jeu a des contraintes très strictes :

* **Sliders (curseurs de défilement) : Non.** Le moteur graphique d'OpenTTD ne propose aucun composant slider pour les scripts d'IA.
* **Champ numérique libre (saisie clavier libre) : Non.** OpenTTD refuse les champs de texte ouverts pour les scripts. Ce sont obligatoirement des compteurs d'entiers bornés manipulés via des flèches latérales `<` et `>`.
* **Choix multiples (liste déroulante / sélection textuelle) : Oui.** C'est la méthode reine : on définit un entier et on lui associe un dictionnaire de libellés avec `AddLabels()`.
* **Float natif (nombres à virgule) : Non.** L'API NoAI ne prend en charge que des entiers signés (`integer`).

Pour intégrer un paramètre comme $\alpha \in [0, 1]$, tu as deux options propres.

---

### Option 1 : Le pourcentage numérique borné (0 à 100)

Tu définis une plage d'entiers avec un pas (`step_size`), puis tu divises par `100.0` à la lecture dans ton code.

Dans `info.nut` :

```squirrel
function AIInfo::GetSettings()
{
    AddSetting({
        name = "personality_alpha",
        description = "Aversion au risque (0 = Tycoon brut, 100 = Comptable ROI)",
        min_value = 0,
        max_value = 100,
        step_size = 5,
        easy_value = 50,
        medium_value = 50,
        hard_value = 50,
        custom_value = 50,
        flags = AICONFIG_INGAME // Modifiable en pleine partie
    });
}

```

Dans ton script (`main.nut` ou ton évaluateur) :

```squirrel
local alphaSetting = AIController.GetSetting("personality_alpha");
local alpha = alphaSetting / 100.0; // Donne un float propre entre 0.0 et 1.0

```

---

### Option 2 : Le choix multiple via `AddLabels`

Si tu veux un affichage textuel élégant dans le menu OpenTTD plutôt que des chiffres, associe des libellés à des valeurs entières :

Dans `info.nut` :

```squirrel
function AIInfo::GetSettings()
{
    AddSetting({
        name = "personality_profile",
        description = "Doctrine d'investissement de l'IA",
        min_value = 0,
        max_value = 2,
        easy_value = 1,
        medium_value = 1,
        hard_value = 1,
        custom_value = 1,
        flags = AICONFIG_INGAME
    });

    AddLabels("personality_profile", {
        [0] = "Bâtisseur (Volume brut & Vitesse)",
        [1] = "Équilibré (Standard)",
        [2] = "Comptable (Sécurité du capital & ROI)"
    });
}

```

Dans ton script :

```squirrel
local profile = AIController.GetSetting("personality_profile");
local alpha = 0.5;

if (profile == 0) alpha = 0.2;
else if (profile == 2) alpha = 0.8;

```

---

### Récapitulatif des champs de `AddSetting()`

| Propriété | Type | Rôle |
| --- | --- | --- |
| `name` | `string` | Clé d'interrogation pour `AIController.GetSetting()` |
| `description` | `string` | Texte affiché dans le menu de configuration |
| `min_value` / `max_value` | `int` | Bornes strictes du paramètre |
| `step_size` | `int` | Incrément à chaque clic sur les flèches (défaut : 1) |
| `easy_value`, etc. | `int` | Valeurs par défaut selon le niveau de difficulté choisi |
| `flags` | `bitmask` | `AICONFIG_INGAME` pour autoriser le changement sans redémarrer la partie |





L'API de configuration `info.nut` d'OpenTTD est volontairement rudimentaire : pour des raisons de sécurité (sandbox Squirrel) et de compatibilité multijoueur, le moteur interdit les champs de saisie texte libre, les fenêtres personnalisées et tout accès au système de fichiers (pas de `fopen` ou de sockets réseau).

Si le menu de configuration officiel te semble trop étroit, voici les options alternatives réellement exploitables dans le jeu :

---

### 1. Le hack des panneaux sur la carte (`AISign`) : une console interactive

C'est la méthode de prédilection des développeurs d'IA avancées pour tester des réglages sans redémarrer la partie.

* **Le principe :** En jeu, le joueur plante un panneau n'importe où sur la carte avec une commande textuelle (ex. `!alpha 75` ou `!mode builder`).
* **Dans l'IA :** Le script scrute régulièrement `AISignList()`, lit le texte via `AISign.GetName(sign_id)`, applique le paramètre, puis détruit le panneau (`AISign.RemoveSign(sign_id)`) pour accuser réception.

```squirrel
function CheckPlayerCommands()
{
    local signs = AISignList();
    for (local s = signs.Begin(); !signs.IsEnd(); s = signs.Next()) {
        local text = AISign.GetName(s);
        if (text.len() > 7 && text.slice(0, 7) == "!alpha ") {
            local val = text.slice(7).tointeger();
            if (val >= 0 && val <= 100) {
                this.alpha = val / 100.0;
                AILog.Info("Nouvel alpha applique via panneau : " + this.alpha);
            }
            AISign.RemoveSign(s); // Efface le panneau une fois lu
        }
    }
}

```

* **Avantages :** Saisie totalement libre en pleine partie, pas besoin d'ouvrir de menu, idéal pour débugger ou envoyer des ordres précis en direct.

---

### 2. Le drapeau booléen natif (`AICONFIG_BOOLEAN`)

Dans `info.nut`, tu n'es pas obligé de faire un compteur `< 0 / 1 >`. Tu peux forcer l'affichage d'un vrai bouton bascule binaire (*Oui / Non*) avec le drapeau `AICONFIG_BOOLEAN` :

```squirrel
AddSetting({
    name = "debug_mode",
    description = "Mode verbeux dans la console de script",
    easy_value = 0,
    medium_value = 0,
    hard_value = 0,
    custom_value = 0,
    flags = AICONFIG_BOOLEAN | AICONFIG_INGAME
});

```

---

### 3. La configuration par fichier dédié (`config.nut`)

Puisque le moteur ne peut pas lire de fichier externe à l'exécution, l'approche habituelle pour le développement consiste à isoler tous les profils dans un fichier Squirrel séparé chargé au démarrage :

```squirrel
// Dans config.nut
CONFIG_PROFILES <- {
    "tycoon" = { alpha = 0.15, max_batch = 5, reserve_ratio = 0.05 },
    "safe"   = { alpha = 0.85, max_batch = 1, reserve_ratio = 0.25 },
    "fast"   = { alpha = 0.40, max_batch = 2, reserve_ratio = 0.10 }
};

CONFIG_ACTIVE_PROFILE <- "tycoon";

```

Dans `info.nut`, tu n'exposes qu'un seul choix multiple (`AddLabels`) qui bascule entre les clés `"tycoon"`, `"safe"` et `"fast"`. L'utilisateur choisit un profil d'un clic, et ton code récupère un ensemble complet de réglages cohérents sans multiplier les paramètres individuels.

---

### 4. L'autorégulation endogène (la supprimer des réglages)

La solution la plus élégante reste de ne pas demander au joueur de choisir $\alpha$. Ton IA peut déduire sa propre personnalité à partir des conditions de la partie :

* **Taille de la carte :** Sur une carte de $256 \times 256$, le foncier et la distance sont courts, $\alpha$ grimpe (prudence, réseau dense). Sur une carte de $2048 \times 2048$, l'IA abaisse $\alpha$ pour privilégier les longs corridors rapides.
* **Densité des concurrents :** Tu comptes les compagnies adverses via `AICompanyList()`. S'il y a 8 concurrents actifs, la vitesse de préemption prime $\rightarrow \alpha$ bas. Si l'IA est seule au monde, elle maximise le ROI $\rightarrow \alpha$ haut.
* **Coût d'emprunt :** Si l'inflation ou les taux d'intérêt sont élevés, la pénalité sur le capital s'alourdit d'elle-même.