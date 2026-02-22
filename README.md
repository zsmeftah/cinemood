# CinéMood

Application de recommandation de films basée sur votre humeur. Repondez a un quiz et laissez l'IA vous suggerer le film parfait.

## Architecture

- **Frontend** : React + TypeScript + Vite + Tailwind CSS
- **Backend** : FastAPI + SQLite + SBERT (embeddings) + Google Gemini (LLM)

## Prerequis

- [Node.js](https://nodejs.org/) v18 ou superieur
- [Python](https://www.python.org/) 3.10 ou superieur
- Cle API [TMDB](https://www.themoviedb.org/settings/api) (pour synchroniser les films)
- Cle API [Google Gemini](https://makersuite.google.com/app/apikey) (pour les recommandations IA)

## Installation

### 1. Cloner le projet

```bash
git clone https://github.com/votre-username/CineMood.git
cd CineMood
```

### 2. Configuration du Backend

```bash
cd backend

# Creer un environnement virtuel
python -m venv .venv

# Activer l'environnement virtuel
# Windows
.venv\Scripts\activate
# macOS
source .venv/bin/activate

# Installer les dependances
pip install -r requirements.txt
```

#### Variables d'environnement

Creer un fichier `.env` dans le dossier `backend/` :

```env
# Cle API TMDB (obligatoire)
TMDB_API_KEY=votre_cle_tmdb  

# Cle API Google Gemini (obligatoire)
GEMINI_API_KEY=votre_cle_gemini

# Mode debug (mettre False en production)
DEBUG=True
```

### 3. Configuration du Frontend

```bash
cd frontend

# Installer les dependances
npm install
```

## Lancement

### Demarrer le Backend (port 8000)

```bash
cd backend

# Activer l'environnement virtuel si pas deja fait
# Windows : .venv\Scripts\activate
# macOS/Linux : source .venv/bin/activate

# Lancer le serveur
python -m uvicorn app.main:app --reload --port 8000
```

### Demarrer le Frontend (port 5173)

Dans un autre terminal :

```bash
cd frontend
npm run dev
```

### Acceder a l'application

Ouvrez votre navigateur sur : **http://localhost:5173**

## Structure du projet

```
CineMood/
├── backend/
│   ├── app/
│   │   ├── api/            # Endpoints API
│   │   ├── models/         # Modeles SQLAlchemy
│   │   ├── services/       # Logique metier
│   │   └── main.py         # Point d'entree FastAPI
│   ├── data/               # Base de donnees SQLite
│   ├── scripts/            # Scripts utilitaires
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── components/     # Composants React
│   │   ├── pages/          # Pages de l'application
│   │   ├── stores/         # Etat global (Zustand)
│   │   └── types/          # Types TypeScript
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

## API Endpoints

| Methode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/health` | Verification de sante |
| GET | `/api/questions/random` | Question aleatoire pour le quiz |
| POST | `/api/recommend` | Obtenir des recommandations |

## Technologies utilisees

### Frontend
- React 19
- TypeScript
- Vite
- Tailwind CSS
- Zustand (state management)
- React Router

### Backend
- FastAPI
- SQLAlchemy + SQLite
- Sentence Transformers (SBERT)
- Google Generative AI (Gemini)
- HTTPX

## Depannage

### Le frontend affiche "Aucune recommandation trouvee"

Verifiez que :
1. Le backend tourne bien sur le port 8000
2. Les cles API dans `.env` sont valides
3. La base de donnees contient des films

### Erreur CORS

Le backend autorise uniquement `http://localhost:5173`. Assurez-vous que le frontend tourne sur ce port.

### Le modele SBERT est lent au demarrage

C'est normal. Le modele est charge en memoire au premier lancement (~2-3 secondes).
