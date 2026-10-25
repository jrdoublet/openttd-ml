# V216 — sécurisation de l'analyse hors banc, 16 octobre 2026

Demande utilisateur : avancer sans banc ni redémarrage Docker.
Lot de complexité 3/5, dans le worktree `est-v216-final` sur `506f29e8`.
Modifications limitées à l'analyse Python et ses tests ; aucun fichier IA,
défaut, campagne ou artefact historique modifié. Aucun lancement moteur.

## Calcul disponible

`sweeps/analyze_v216.py::rail_pax_fixed_cost_shadow` conserve les coûts
implicites `revenueAnnual - profitAnnual`, le facteur de calibration
`fund_profit / profitAnnual` et le dénominateur du score. Le facteur fantôme
moyen des deux extrémités s'applique au **revenu**, puis les coûts sont déduits.

Exemple synthétique : revenu 100, profit brut 20, coûts 80, facteur 50 %.
Le profit corrigé est **−30**, et non +10. Avec une calibration 0,5,
le profit calibré est −15 ; le projet ne reste pas dans le classement.
Un facteur 100 % conserve les valeurs initiales ; les coûts restent présents
si le revenu tombe à zéro. Les rames avec cargo secondaire sont indéterminées.

`fixed_cost_rank_sensitivity` traite uniquement une liste de projets déjà
classés, dont tous les rangs ont été enregistrés. Les projets simplement
finançables ne sont pas promus : leurs autres conditions d'admission sont
inconnues. Champs manquants/non finis, doublons, liste tronquée, ordre initial
non reproduit et égalité au premier rang sont signalés comme indéterminés,
pas comme « aucun changement ». Les entrées ne sont pas modifiées.

La sortie principale présente désormais cette **sensibilité du rang à coûts
fixes** et ses compteurs observés/calculables/indéterminés. La fonction historique
`replay_selections_6` reste disponible pour reproduire les anciens calculs ;
les rapports déjà versionnés ne sont pas réécrits.

## Contrôle du test D

`invariance_test_d` ne peut plus retourner PASS si le nombre de cellules fourni
diffère de quatre, si une cellule est inexploitable ou si un facteur fantôme
d'extrémité manque. Le verdict est alors INCOMPLETE. Le calcul numérique
intermédiaire reste identifiable par `numeric_verdict` ; il ne remplace pas
le verdict tenant compte de la couverture.

La correspondance effective des quatre ensembles à A/B/C/D reste à vérifier
dans les manifestes : compter quatre étiquettes ne prouve pas le plan factoriel.
Comparer le revenu propre d'une ligne au gain net de compagnie reste également
une limite de définition de la métrique. Un PASS numérique n'est pas une
qualification économique. Le FAIL historique du rapport VPS reste inchangé.

## Validation et portée

`python -X utf8 -m unittest discover -s sweeps -p "test_v216*.py"` :
**32 tests réussis**, dont les cas revenu/coûts/calibration, inconnus, rame mixte,
suppression sans remplacement, absence de promotion d'un candidat non classé,
classement tronqué, ordre initial, égalités et rendu du rapport CLI.
`git diff --check` réussi. Aucun test moteur requis pour cette modification
du lecteur ; aucune compilation Squirrel ni performance économique revendiquée.

Ce calcul impose un choc de revenu à matériel constant. Il ne reproduit pas
V216a, qui modifie la demande avant dimensionnement : saturation de capacité,
nombre de véhicules, coûts, note et tarif peuvent alors évoluer. Le seuil
d'opcodes, V88 et les tentatives de construction ne sont pas rejoués ; le
champ `purchase_replay_complete` reste faux.

Prochain usage utile : exécuter cette version sur les journaux V216 originaux
lorsqu'ils sont disponibles et rapporter d'abord la couverture calculable.
Ne pas extrapoler les fixtures à des graines réelles, ni lancer un banc pour
remplacer des journaux manquants. Aucun commit/push effectué pour ce lot.
