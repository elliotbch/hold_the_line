# 🏃‍♂️ Hold The Line: Guidance System for the Visually Impaired

Ce projet vise à développer un système portatif permettant d’aider les personnes malvoyantes à se déplacer en toute sécurité le long d’un parcours balisé. En utilisant un Raspberry Pi, une caméra et un casque audio, le système capte en temps réel l’image d’une ligne sur le sol, calcule l’angle entre cette ligne et la direction de l’utilisateur, et fournit un retour audio stéréophonique pour guider l’utilisateur. 🎧📷

---

## 📋 Table des matières

1. [Introduction](#introduction)
2. [Approches Exploitées](#approches-exploitées)
   - [Active Outline Model](#active-outline-model)
   - [Middle Edge Model](#middle-edge-model)
   - [Radon Transform Model](#radon-transform-model)
   - [Quantization & Middle-Sampled Linear Regression Model](#quantization--middle-sampled-linear-regression-model)
3. [Ensemble & Multi-threading](#ensemble--multi-threading)
4. [Expériences & Résultats](#expériences--résultats)
5. [Conclusion & Perspectives](#conclusion--perspectives)
6. [Mode d'emploi](#mode-demploi)
7. [Instructions pour Développeurs](#instructions-pour-développeurs)
8. [Contributeurs](#contributeurs)
9. [Références](#références)

---

## 📖 Introduction

Ce projet de semestre a pour objectif de permettre aux personnes malvoyantes de se déplacer en toute autonomie grâce à un système de guidage basé sur la détection d’une ligne. En capturant en temps réel des images et en analysant leur contenu, le système calcule l’angle entre la ligne et la direction de l’utilisateur, puis fournit un retour audio permettant d’ajuster le trajet. L’approche fait appel à des techniques variées de traitement d’image et de gestion multi-threadée sur un Raspberry Pi. 😊

---

## 🔍 Approches Exploitées

Plusieurs méthodes de détection ont été explorées pour identifier la trajectoire à suivre :

### 💡 Active Outline Model

- **Principe :** Utilise la méthode des *contours actifs* (snakes) pour segmenter l’image.
- **Fonctionnement :** Le contour évolue pour minimiser une fonction d’énergie qui combine la fidélité aux bords et la régularité du contour.
- **Limites :** Calcul complexe et difficultés à obtenir une performance en temps réel.

### ✨ Middle Edge Model

- **Principe :** Applique une détection d’arêtes via un filtre Laplacien du Gaussien (LoG).
- **Fonctionnement :**  
  1. Compression et amélioration de l’image (affinage et lissage).  
  2. Détection des bords donnant deux lignes limites de la trajectoire.  
  3. Calcul du point médian pour chaque ligne de pixels.
- **Retour Audio :** Le volume stéréophonique est ajusté en fonction de la distance entre l’utilisateur et la trajectoire.
- **Complexité :** Environ O(n log(n)) grâce à l’utilisation des algorithmes de transformation de Fourier rapides.

### 🔄 Radon Transform Model

- **Principe :** Utilise la transformation de Radon pour identifier l’orientation dominante des arêtes.
- **Fonctionnement :**  
  - Compression, filtrage par le détecteur Canny, et application de la transformation de Radon pour estimer l’angle de la ligne par rapport à la verticale.
- **Limites :** Complexité élevée (O(n²)) et temps de calcul plus long.

### 🎨 Quantization & Middle-Sampled Linear Regression Model

- **Principe :** Combine la quantification de couleurs par l’algorithme k-means++ et une régression linéaire sur les segments échantillonnés.
- **Fonctionnement :**  
  1. Quantification de l’image pour conserver les informations de couleur sans passer au niveau de gris.  
  2. Extraction des milieux de segments de couleur similaires et application d’une régression linéaire pour estimer l’angle.
- **Avantage :** Complexité linéaire (O(n)) après quantification, offrant des résultats rapides et précis.
- **Retour Audio :** L’angle estimé est transformé en signal audio, modulant les volumes gauche et droit.

---

## 🔧 Ensemble & Multi-threading

Pour permettre un traitement en temps réel sur le Raspberry Pi, nous avons mis en place un système multi-threadé :

- **Thread A :**  
  - Responsabilité : Quantification des couleurs et détection initiale de la ligne.  
  - Tâche relativement lente mais essentielle pour établir la référence de couleur. 🧵

- **Thread B :**  
  - Responsabilité : Détection fine de la ligne et génération du signal audio de guidage en temps réel.  
  - Fonctionne en parallèle avec Thread A pour assurer une réponse rapide. ⚡

Cette architecture permet d’offrir un guidage continu et fluide à l’utilisateur, même si la mise à jour de la référence de couleur se fait moins fréquemment.

---

## 📊 Expériences & Résultats

- **Environnement de Test :**  
  - Tests réalisés dans le Marconi amphi-théâtre et sur le terrain.
  
- **Performances :**  
  - Sur 20 essais, le système a détecté correctement la ligne à chaque fois.
  - Le retour audio stéréophonique guide efficacement l’utilisateur vers la trajectoire souhaitée.
  
- **Observations :**  
  - Quelques ajustements de calibration étaient nécessaires pour optimiser la détection des couleurs et réduire le bruit environnant.
  - L’approche multi-thread permet une transition fluide des signaux, améliorant l’expérience utilisateur.

---

## 🎓 Conclusion & Perspectives

**Conclusion :**  
Le système "Hold The Line" démontre avec succès qu’une solution basée sur le Raspberry Pi, couplée à un traitement d’image en temps réel et à un retour audio stéréophonique, peut grandement faciliter la mobilité des personnes malvoyantes. 🌟

**Perspectives :**  
- Optimiser la vitesse de traitement pour réduire davantage la latence.
- Intégrer et améliorer les approches multiples pour une détection plus robuste.
- Envisager une implémentation en Python pour rendre le système plus accessible et économique.
- Améliorer la résistance au bruit et la précision de la détection sur différentes surfaces.

---

## 📖 Mode d'emploi

### 🚀 Pour les Utilisateurs

1. **Utilisation :**  
   - Allumez le système en appuyant sur le bouton dédié (le lancement s’effectue automatiquement sur le Raspberry Pi).  
   - Placez le casque et suivez les instructions audio stéréophonique pour rester centré sur la ligne.
   
2. **Mise à jour du Firmware :**  
   - Connectez le Raspberry Pi à l’alimentation via le câble USB-C.  
   - Téléchargez la version la plus récente du firmware depuis notre GitLab : [GitLab Project](https://gitlab.eurecom.fr/the-win-team-a3/project-s5).  
   - Ouvrez un terminal et connectez-vous via SFTP :  
     ```
     sftp pi@holdtheline.local
     ```
   - Supprimez l’ancien fichier et transférez le nouveau :  
     ```
     rm projects5.elf
     put /chemin/vers/projects5.elf /home/pi
     ```
   - Déconnectez le câble d’alimentation et redémarrez en maintenant le bouton enfoncé.

---

## 👨‍💻 Instructions pour Développeurs

### Pré-requis logiciels :
- **MATLAB et Simulink** avec les packages de support pour Raspberry Pi.
- **Audio Toolbox** et **DSP System Toolbox**.

### Connexions matérielles :
- Connectez le Raspberry Pi à la caméra, aux écouteurs et à la batterie.
- Utilisez un câble Ethernet pour le déploiement initial depuis votre ordinateur.

### Déploiement :
1. Configurez la connexion avec le Raspberry Pi via Simulink.
2. Sélectionnez le bon matériel dans les paramètres et lancez la compilation.
3. Une fois le déploiement terminé, débranchez le Raspberry Pi et testez le système en conditions réelles.

Le code complet est accessible sur notre GitLab : [GitLab Repository](https://gitlab.eurecom.fr/the-win-team-a3/project-s5)

---

## 👥 Contributeurs

**Team A - Group 3**  
- **Elliot Bouchy**  
- **Gaëtan Plisson**  
- **Maxime Belpois**  
- **Lina Chiadmi**  
- **Meriem Driss**  

Sous la supervision de **Raphaël Troncy** à EURECOM, Sophia Antipolis.

---

## 📚 Références

1. Dugelay, J.-L. – *Image Processing*, 2022.  
2. Todisco, M. – *Sound Processing*, 2022.  
3. Galdi, C. – *Computer Programming*, 2022.  
4. Magnac, M.-A. – *Digital Responsibility*, 2023.  
5. Pacalet, R. – *Project S5*, 2022.

---

