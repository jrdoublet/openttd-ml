# Revue documentaire — clôture des corrections locales du 30 septembre 2026

Cette note récapitule les corrections documentaires et les limites de validation.
Elle ne constitue ni un nouveau backlog ni une qualification économique.
Le travail restant est exclusivement suivi dans [taches.md](taches.md).

## Corrections présentes dans l'arbre

| Constat | Correction / référence |
|---|---|
| Consignes périmées | [AGENTS.md](../AGENTS.md) et [CLAUDE.md](../ai/OpexAI/CLAUDE.md) distinguent C67 livré/non exposé, BFS courant/Lakes retiré, biais financier rail 100/facteur terrain 170, optimisations adoptées/workers expérimentaux. |
| Protocoles contradictoires | AGENTS.md est la référence des validations ; smoke 1×1, règles d'adoption et exceptions explicites. RTK et un chemin personnel ne sont plus obligatoires. |
| Anciennes architectures présentées comme actuelles | README et guides signalent leurs sections historiques ; repères courants sur `fundScore`, profit calibré, `policy_road` et persistance. Le walkthrough racine renvoie à une seule copie historique. |
| Défauts et états contradictoires | Tâches réconciliées pour V90/V91/V94 ; état du catalogue découpé présenté par phase ; collisions d'identifiants qualifiées par leurs alias. |
| C116/C117 corrompus | Originaux conservés dans `docs/archives/` comme non autoritaires. C117 décrit la méthode relue dans le code, sans reconstruire les tableaux perdus ; C116 conserve les incertitudes chiffrées. |
| Bilans divergents | C116.4 réduit à une synthèse avec réserves ; B9 renvoie à sa fiche canonique, sans prétendre avoir réanalysé les résultats. |
| Gabarit V88 incomplet | [Fiche V88](27_v88_chaines_biens.md) : arguments complets et cinq graines explicites ; suspension maintenue, aucune campagne lancée. |
| Banc CI sans adversaire approvisionné | Le workflow courant `ci.yml` ne lance plus cet ancien banc ; les bancs manuels ont leur procédure dans [bancs_github.md](bancs_github.md). Leur mise en place appartient au lot GitHub distinct. |
| Cache Docker masquant les paquets | Dépendances déplacées dans `/opt/venv`, hors du volume `/home/lab`, site utilisateur désactivé ; cibles `simulation` et `ml` préservées. |
| Couverture des preuves trop étroite | `package_review_evidence.py` audite toutes les citations JSON explicites du périmètre documenté, sans filtre de préfixe. Mode par défaut en lecture seule, écriture explicite et refus des entrées manquantes/conflits. |

## Contrôles effectivement réalisés

- Lecture croisée de la documentation et des symboles/réglages concernés.
- Contrôle PowerShell en lecture seule des **57 archives** de l'index historique :
  SHA-256 gzip et SHA-256/taille décompressés conformes, **0 anomalie**.
- Inventaire au moment du contrôle : **143 documents**, **618 citations JSON
  uniques**, dont **406 sans fichier local ni entrée de l'index**. Ces chiffres
  portent aussi sur les archives historiques, pas seulement les preuves récentes.
  Ils ne signifient pas 406 campagnes à relancer ou résultats définitivement perdus.
- Diagnostics éditeur sans erreur sur les derniers fichiers corrigés.

Le contrôle PowerShell des archives n'est **pas** une exécution du nouveau script
Python. Onze fixtures synthétiques ont été ajoutées aux deux contrôles d'intégrité
existants ; `benchmark-regressions.yml` les sélectionne désormais. Elles couvrent
citations récentes, absence de sources, conservation des archives, conflits, chemins,
collisions de noms et gzip déterministe. Les tests ne confondent pas intégrité de
l'index historique et couverture exhaustive de la documentation actuelle.

## Limites et reliquat

- Configuration Python : `No base python found` ; exécution via l'éditeur :
  `No tests found`. **Aucun test Python exécuté** dans ce lot.
- Git et Docker indisponibles : pas de diff Git, construction d'image, smoke
  moteur, commit, push ou exécution GitHub revendiqués.
- L'index et les bundles historiques n'ont pas été régénérés ni modifiés.
  Récupérer les preuves originales et sources textuelles saines pour lever les
  réserves C116/C117/C122 ; ne pas fabriquer des résultats ou réécrire un bundle.
- Valider les tests sur GitHub et le runtime de l'image reconstruite avec le
  volume existant avant d'utiliser cette image pour une preuve comparative.
  Voir le [contrat d'archivage](../evidence/review/README.md) pour l'audit séparé.

**Aucun changement du comportement Squirrel ni des défauts IA dans ce lot.**
Les autres corrections de code du 30 septembre sont décrites séparément dans
le [journal quotidien](journaux/journal_2026-09-30.md).