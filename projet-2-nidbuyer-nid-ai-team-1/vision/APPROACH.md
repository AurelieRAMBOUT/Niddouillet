## R&D vision 
# Etat d’avancement
Par manque de temps, nous n’avons malheureusement pas pu implémenter ni tester la partie vision du projet.
Néanmoins, nous avons commencé par une phase de recherche pour comprendre. les CNN et les LLM multimodaux. Nous nous sommes donc renseignés sur les deux principales pistes proposées : les CNN et les LLM multimodaux.

**Nous avons compris** que les CNN sont des modèles spécialisés dans l’analyse d’images (détection de motifs, classification). Leur fonctionnement est inspiré du système visuel des mammifères, en particulier des travaux sur le cortex visuel des chats, où les neurones réagissent à des motifs simples (lignes, orientations) avant de reconstruire des formes plus complexes.
Et les LLM multimodaux permettent d’aller plus loin en combinant image et texte pour produire une interprétation globale, par exemple estimer l’état d’un bien, détecter des travaux ou générer une analyse cohérente.
Si nous avions eu plus de temps, nous aurions  :
•	entraîner un modèle CNN sur des photos labellisées (par état du bien),
•	utiliser un LLM multimodal (type GPT-4o ou Claude) pour analyser directement les images sans phase de labellisation, comme suggéré dans le projet.

Nous prévoyons de poursuivre cette partie dans les prochains jours, même si cela sera hors délai de rendu, car le sujet nous intéresse réellement. 
Les avancées récentes en IA, notamment autour des modèles combinant perception et raisonnement, montrent que ces approches vont jouer un rôle majeur dans des applications concrètes comme celle de NidDouillet. 
Les travaux récents du domaine, ont été très médiatisés, grâce à certaines initiatives portées par des chercheurs comme Yann LeCun (startup ami), et confirment cette évolution vers des systèmes capables de mieux comprendre leur environnement.

# R&D Vision — Choix d'approche et résultats

## Approche retenue

**CNN / LLM multimodal / Autre** *(barrer les mentions inutiles)*

Modèle : _______________

Justification du choix :
- Pourquoi cette approche plutôt que l'alternative ?
- Contraintes prises en compte (données disponibles, coût, temps) :

---

## Dataset

| | Valeur |
|--|--|
| Nombre de photos labellisées | |
| Source des photos | |
| Répartition par classe | excellent: X / bon: X / correct: X / à rénover: X |

*(Si LLM : indiquer "aucun label nécessaire" et le nombre de photos testées)*

---

## Résultats

### Métriques sur jeu de test

| Classe | Précision | Rappel | F1 |
|--------|-----------|--------|----|
| excellent | | | |
| bon | | | |
| correct | | | |
| a_renover | | | |

**Accuracy globale :** ____%

### Exemples de prédictions

| Photo | Vérité terrain | Prédiction | Correct ? |
|-------|---------------|------------|-----------|
| photo_001.jpg | a_renover | a_renover | ✓ |
| photo_002.jpg | bon | correct | ✗ |

---

## Coût

*(Si LLM uniquement)*

| Modèle testé | Coût / photo | Coût total tests | Qualité estimée |
|-------------|-------------|-----------------|----------------|
| | | | |

---

## Limites et biais

- Ce que le modèle rate systématiquement :
- Conditions où il se trompe :
- Ce qu'on ferait différemment avec plus de temps :

---

## Intégration dans le scoring

La fonction `vision.model.evaluer_etat_bien()` est appelée dans `backend/scoring.py`
via le paramètre `vision_result`. Impact sur le score d'opportunité :

- Profil investisseur : travaux = opportunité → malus = 0
- Profil RP famille : travaux = frein → malus = 0.3
