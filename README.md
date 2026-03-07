# 🍳 ChefBot Ultimate - Assistant Culinaire

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Pygame](https://img.shields.io/badge/Pygame-2.0+-green.svg)
![Status](https://img.shields.io/badge/Status-Stable-brightgreen.svg)

**ChefBot Ultimate** est une application de bureau conçue pour simplifier la gestion de vos recettes. Bien plus qu'un simple livre de cuisine numérique, il intègre un moteur de calcul intelligent pour adapter vos ingrédients en un clic et un système de recherche avancée pour cuisiner avec ce que vous avez sous la main.



---

## ✨ Fonctionnalités Clés

### 🧊 Mode Frigo (Recherche Intelligente)
Ne vous demandez plus quoi cuisiner. Entrez les ingrédients qu'il vous reste, activez le **Mode Frigo**, et ChefBot filtre instantanément les recettes réalisables.
* **Algorithme de normalisation** : Ignore les accents et gère les pluriels pour une recherche sans erreur.
* **Filtre strict** : Affiche uniquement les plats dont vous possédez tous les ingrédients nécessaires.

### ⚖️ Calculateur de Portions Dynamique
Passez de 2 à 10 personnes instantanément. ChefBot détecte les nombres dans les listes d'ingrédients et applique un multiplicateur en temps réel sans déformer le texte.

### 📝 Éditeur de Recettes Intégré
Une interface dédiée (Tkinter) permet d'ajouter vos propres créations :
* Gestion du temps, de la difficulté et des tags.
* Importation d'images locales avec gestion automatique des chemins.
* Syntaxe flexible pour les ingrédients (options "OU" et combinaisons "+").

### 🛒 Favoris & Liste de Courses
* Marquez vos plats préférés avec le système de favoris animé.
* **Exportation en 1 clic** : Génère automatiquement un fichier `liste_courses.txt` basé sur vos favoris.

---

## 🛠️ Stack Technique

* **Interface Graphique** : `Pygame` (Rendu fluide, animations de particules, smooth scrolling).
* **Fenêtres d'édition** : `Tkinter` (Formulaires natifs).
* **Base de données** : `JSON` (Stockage local structuré).
* **Traitement de texte** : `Regex` (Analyse et modification des quantités numériques) et `Unicodedata`.



---

## 🚀 Installation & Utilisation

1.  **Prérequis** : Python 3.8 ou supérieur.
2.  **Installation des dépendances** :
    ```bash
    pip install pygame
    ```
3.  **Lancement** :
    ```bash
    python chefbot.py
    ```

### 📦 Compilation en .exe
Le code est optimisé pour être compilé avec `PyInstaller`. Il gère automatiquement les chemins de ressources (`_MEIPASS`) pour inclure les polices et images de base dans l'exécutable.

---

## ⌨️ Raccourcis & Astuces
* **Recherche** : Saisissez vos ingrédients séparés par des virgules.
* **Navigation** : Utilisez la molette de la souris pour un défilement fluide des instructions.
* **Timer** : Cliquez sur le tag "Temps" d'une recette pour lancer un compte à rebours automatique.

---
*Développé pour rendre la cuisine plus accessible et organisée.*
