---
title: Hold The Line
emoji: 🦯
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# Hold The Line : démo en ligne

Choisissez une image d'exemple ou importez la photo d'une ligne au sol : la démo détecte la ligne avec un portage Python des détecteurs MATLAB du projet, la trace sur l'image, donne son angle par rapport à la direction de marche et joue le son de guidage stéréo dans le navigateur (Web Audio API, volumes gauche/droite issus de `findsound.m`, signal carré de 100 Hz comme dans le modèle Simulink). Un mode webcam envoie une image par seconde au serveur.

Trois détecteurs sont disponibles, chacun porté depuis un fichier MATLAB du dépôt :

| Méthode | Source MATLAB | Python |
|---|---|---|
| Quantification + régression linéaire sur les milieux échantillonnés (déployée sur le Raspberry Pi) | `matlab/simulink_blocks/rgbtoimg.m`, `findcolor.m`, `findsound.m` | `holdtheline/quantization.py` |
| Milieu des bords | `matlab/approaches/draw_line__1_.m` | `holdtheline/middle_edge.py` |
| Transformée de Radon | `matlab/approaches/find_line_radon.m` | `holdtheline/radon_method.py` |

L'erreur d'angle de chaque méthode sur 60 images synthétiques d'angle connu se trouve dans `eval_metrics.json` (écrit par `python scripts/evaluate.py` à la racine du dépôt) et est affichée sur la page. Trois des six exemples sont des images synthétiques générées par `holdtheline/synthetic.py` ; la page le précise.

## Lancer en local

Depuis la racine du dépôt :

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r demo/requirements.txt
uvicorn demo.app:app --port 7860       # ouvrir http://localhost:7860
pip install pytest httpx && pytest demo/tests
```

La webcam exige `localhost` ou HTTPS (règle des navigateurs pour `getUserMedia`).

## Docker (même image que le Space Hugging Face)

```bash
./demo/sync_core.sh                    # copie holdtheline/ dans demo/_core/
docker build -t hold-the-line-demo demo
docker run --rm -p 7860:7860 hold-the-line-demo
```

## API

| Méthode | Chemin | Description |
|---|---|---|
| GET | `/` | Page de démo |
| GET | `/health` | État et méthodes disponibles |
| GET | `/api/examples` | Images d'exemple (`/static/examples/`) avec leur source et leur angle de référence |
| GET | `/api/metrics` | `eval_metrics.json` |
| POST | `/api/detect` | multipart : `file`, `method` (`middle_edge`, `quantization`, `radon`), `color` (`r,g,b`) et `threshold` facultatifs pour réutiliser la couleur de la ligne (quantification) |
| POST | `/api/detect_example` | formulaire : `name` (fichier d'exemple), `method` |

Réponse : `found`, `angle_deg` (positif = la ligne part vers la droite), `left`, `right` (volumes de somme 1), `time_ms`, `image` annotée (data URL JPEG) et détails propres à la méthode. Les fichiers importés sont limités à 8 Mo ; au plus deux détections tournent en même temps.
