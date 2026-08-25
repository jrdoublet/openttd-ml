# openttd-ml

Peut-on prédire le profit d'une ligne ferroviaire à partir de ses caractéristiques de
construction, sans simuler la partie ? Voir `docs/methode.md` pour le protocole complet.

## Décisions figées (Phase 0)

| Élément | Valeur | Raison |
|---|---|---|
| OpenTTD | `13.4` | Voir note ci-dessous |
| OpenGFX | `7.1` | Version appariée à 13.4 dans les exemples de référence |
| Python | 3.12 | Testé par le projet (3.8.2 minimum) |
| IA de calibration | trAIns, `unique_id='54524149'` | IA de référence utilisée dans les exemples |
| Durée de partie | `days = 365 * 4 + 1` | 4 ans de jeu, valeur de l'exemple officiel |

**Note sur la version.** La documentation d'OpenTTDLab se contredit : la section *Compatibility*
annonce le support des branches 12, 13 et 15+, tandis que l'avertissement sur `run_experiments`
indique que 13.4 est la dernière version connue pour fonctionner. La branche 14.x n'est supportée
dans aucun des deux cas. → On pin 13.4, on note la contradiction ici, on ne teste 15.x que si le
besoin s'en fait sentir.

## Version exacte d'OpenTTDLab

```
OpenTTDLab==0.0.75
```

## MD5 de trAIns

```
c4c069dc797674e545411b59867ad0c2
```
(`ai/54524149`, trAIns 2.1, GPL v2 — obtenu via `download_from_bananas('ai/54524149')`,
utilisé comme `bananas_ai("54524149", "trAIns", md5="c4c069dc797674e545411b59867ad0c2")`
dans `sweeps/phase0_timing.py` et `sweeps/phase0_plot.py`.)

## Installation — VPS (Docker)

```bash
docker build -t openttd-lab .

docker run --rm -it \
  --name openttd-lab \
  --cpus=3 \
  --memory=2g --memory-swap=2g \
  -v openttd-lab-home:/home/lab \
  -v "$PWD":/work \
  -w /work \
  openttd-lab bash
```

- `--cpus=3` — laisse un cœur pour Traefik, Netdata et le reste de la stack.
- `--memory-swap=2g` égal à `--memory` — désactive le swap : le conteneur se fait tuer proprement
  au lieu d'entraîner l'hôte dans une saturation.
- Volume nommé sur `/home/lab` — cache persistant pour OpenTTD/OpenGFX/IA téléchargés par
  OpenTTDLab, pour éviter de tout retélécharger à chaque `docker run`.

**Alerte Netdata : pas encore faite.** Netdata n'est pas déployé sur ce VPS actuellement — à poser
avant la première vraie campagne de nuit (voir la stack Docker existante du VPS pour l'intégrer
proprement, ex. via `socket-proxy` comme les autres outils d'observabilité de ce serveur).

## Calibration (Phase 0)

```bash
MACHINE=vps python sweeps/phase0_timing.py   # coût unitaire, point d'inflexion du parallélisme
python sweeps/phase0_plot.py                 # graphique money x date sur 10 graines
```

### Résultats — VPS (4 CPU hôte, conteneur `--cpus=3`)

| workers | wallclock (s) | s/partie | rows |
|---|---|---|---|
| 1 | 12.9 | 12.9 | 47 |
| 2 | 12.8 | 6.4 | 94 |
| 3 | 13.0 | 4.3 | 141 |
| 4 | 17.0 | 4.3 | 188 |

**Point d'inflexion : `max_workers=3`.** Au-delà (4 workers dans un conteneur `--cpus=3`), le
wallclock augmente sans que `s_per_game` ne s'améliore — cohérent avec la limite CPU du conteneur
et la recommandation de garder un cœur pour le reste de la stack. `max_workers=3` retenu pour la
production sur ce VPS.

**Granularité temporelle.** 47 lignes par partie de 4 ans = un savegame par mois (OpenTTD est
configuré en `autosave=monthly, keep_all_autosave=true` pour les versions 12–13.x). La granularité
disponible est donc mensuelle, pas annuelle.

**Débit de production (VPS, s_per_game_optimal = 4.3s à 3 workers) :**

```
parties_par_jour_vps = 24 * 3600 / 4.3 ≈ 20 090 parties/jour
```

### Laptop / sharding — non applicable

La section 2 de la spec ignore l'installation portable pour cette phase. Sans second point de
mesure, `docs/phase0_laptop.json`, le calcul de `ratio_sharding` et le test de déterminisme
inter-machines (section 5) ne s'appliquent pas — VPS seul pour l'instant. À reprendre si une
seconde machine est ajoutée au projet.

Le graphique produit (`docs/phase0_money_vs_date.html`, données brutes dans
`docs/phase0_money_vs_date.csv`) trace `money` par mois sur 10 graines (300–309), IA trAIns,
4 ans de jeu, `max_workers=3`.

## Checklist de sortie de phase 0

- [x] Dépôt git initialisé, versions figées dans `requirements.txt`
- [x] Conteneur VPS avec limites CPU/mémoire, volume de cache persistant
- [ ] Alerte Netdata — **pas encore faite**, Netdata non déployé sur ce VPS
- [ ] WSL2 plafonné sur le portable — non applicable (portable ignoré en phase 0)
- [x] `docs/phase0_vps.json` produit — `docs/phase0_laptop.json` non applicable
- [x] `max_workers` optimal déterminé sur le VPS (3) — non applicable sur portable
- [ ] Déterminisme inter-machines — non applicable, une seule machine pour l'instant
- [x] MD5 de trAIns noté et épinglé (`c4c069dc797674e545411b59867ad0c2`)
- [x] `docs/methode.md` rédigé
- [x] Un graphique money × date sur 10 graines, commité — premier résultat
