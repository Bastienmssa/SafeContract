# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SafeContract is a web3/smart contract analysis platform with four layers:
- **Frontend**: Next.js 14 (App Router) — site marketing + dashboard d'analyse
- **API Gateway**: Zuplo (TypeScript, OpenAPI-spec-first) — routes requests to backend or Ethereum RPC
- **Backend**: Python FastAPI — API d'analyse de contrats via Mythril + persistance MongoDB
- **Core**: Rust library (stub, not yet implemented)

## Commands

### Frontend (Next.js)
```bash
cd frontend && npm install       # install dependencies
npm --prefix frontend run dev    # dev server on port 3000
npm --prefix frontend run build  # production build
npm --prefix frontend run lint   # lint
```

### Zuplo API Gateway (root)
```bash
npm install          # install Zuplo dependencies
npm run dev          # Zuplo dev server on localhost:9000
npm test             # run Zuplo tests
npm run docs         # generate API docs
```

### Backend (FastAPI + Mythril + MongoDB)
```bash
cd backend
pip install fastapi uvicorn mythril motor python-dotenv
uvicorn app.main:app --reload    # dev server (port 8000 par défaut)
```

L'outil CLI Mythril (`myth`) doit être disponible dans le PATH — invoqué via `subprocess` dans `app/services/mythril_service.py`.

MongoDB doit tourner sur `localhost:27017` (configurable via `MONGODB_URL` dans `backend/.env`).

### Production / PM2
```bash
./deploy.sh                                   # full deploy (install + build + PM2)
pm2 start ecosystem.config.cjs --env production
pm2 logs safe-contract-front
```

## Architecture

### Request Flow
```
Browser → Next.js frontend (port 3000)
       → Next.js API routes (/api/*) → Python backend (port 8000)
       → Zuplo API Gateway (port 9000) → Python backend OR Ethereum RPC node
Caddy reverse proxy handles external HTTPS traffic (infra/Caddyfile)
```

### Zuplo API Gateway
Routes defined in `config/routes.oas.json` (OpenAPI 3.1.0). Current routes:
- `POST /scan` — proxies to FastAPI backend at `http://127.0.0.1:8000`
- `GET /analyses` — proxies to FastAPI backend at `http://127.0.0.1:8000`
- `GET /analyses/:id` — proxies to FastAPI backend at `http://127.0.0.1:8000`
- `POST /rpc` — proxies to Ethereum node at `http://159.65.192.47.nip.io:8545`
- `/*` — catch-all proxy to Next.js at `http://159.65.192.47.nip.io:3000`

### Backend — Endpoints
- `POST /scan` (`app/api/scan.py`) — reçoit un fichier `.sol`, lance Mythril, calcule le score, **sauvegarde en MongoDB**, retourne `{ status, id, report }`.
- `GET /analyses` (`app/api/analyses.py`) — liste toutes les analyses (triées par date desc). Retourne `[]` si MongoDB indisponible.
- `GET /analyses/{id}` (`app/api/analyses.py`) — récupère une analyse par son ObjectId MongoDB.

`app/services/mythril_service.py` exécute `myth analyze <path> -o json` en subprocess.

### Backend — MongoDB
- Connexion dans `app/database/mongodb.py` via `motor` (driver async)
- Variable d'environnement : `MONGODB_URL` (défaut : `mongodb://localhost:27017`)
- Base de données : `safecontract`, collection : `analyses`
- Le scan fonctionne même si MongoDB est indisponible (résultat retourné, erreur loggée)
- Config dans `backend/.env` (ne pas committer les credentials)

Structure d'un document `analyses` :
```json
{
  "_id": "ObjectId",
  "filename": "MonContrat.sol",
  "code": "// Solidity source...",
  "score": 72,
  "issues": [{ "line": 14, "severity": "critical", "title": "...", "desc": "...", "swcId": "SWC-107" }],
  "raw_report": {},
  "analyzed_at": "ISODate",
  "status": "completed"
}
```

### Frontend — Pages
- `/` — Landing page (Navbar + sections composables + Footer)
- `/about` — Présentation du projet, stack, équipe (Bastien, Géraud, Pierre-Henri)
- `/connexion` — Login (hardcodé : admin/admin, stocke `sc_auth` dans localStorage)
- `/dashboard` — Dashboard protégé : Vue d'ensemble, Nouvelle analyse, Code & Diagnostic, Historique
- `/free-analyse` — Analyse publique sans compte

### Frontend — API Routes (Next.js proxy)
- `POST /api/scan` → `BACKEND_URL/scan`
- `GET /api/analyses` → `BACKEND_URL/analyses`
- `GET /api/analyses/[id]` → `BACKEND_URL/analyses/{id}`

`BACKEND_URL` défaut : `http://localhost:8000`. Toutes les routes lisent la réponse en texte avant de parser le JSON pour éviter les crashes sur réponses vides ou HTML.

### Frontend — Composants clés
- `components/Navbar.tsx` — Navbar card-nav flottante centrée (sticky, frosted glass, `usePathname` pour l'état actif). Liens : À propos, Se connecter, Essai gratuit.
- `app/dashboard/page.tsx` — Dashboard complet (818+ lignes). Contient : `AnalyseScan`, `HealthGauge`, `SecurityTimeline`, `CodeDiagnostic`, `ContractCard`.
- `app/dashboard/data.ts` — Types TypeScript (`Contract`, `Issue`, `Severity`). Plus de données mock — les données viennent de MongoDB via `/api/analyses`.

### Frontend — Sélecteur d'outils (dashboard)
Dans l'onglet "Nouvelle analyse", l'utilisateur choisit les outils via des **checkboxes** :
- **Mythril** : toujours coché, non décochable (badge "Requis")
- **Intelligence Artificielle** : optionnelle, cochable seulement si aucun autre outil optionnel n'est actif (badge "Bientôt" tant que `available: false`)
- Règle : cocher un futur outil décoche automatiquement l'IA (badge "Incompatible")
- Pour activer l'IA quand le modèle sera prêt : passer `available: true` dans `TOOLS` dans `page.tsx` et brancher la logique dans `handleSubmit` selon `selectedTools.has("ai")`

### Frontend — Styles
- Police principale : **Satoshi** (Fontshare CDN, importée dans `globals.css`)
- Fallback : Inter (next/font/google)
- Couleurs : primary green `#2cbe88`, dark `#152d5b` (définis dans `tailwind.config.ts`)
- Dégradé logo/texte : `linear-gradient(135deg, #2cbe88 0%, #152d5b 100%)`

### TypeScript Configuration
Two separate tsconfig scopes:
- Root `tsconfig.json` — targets Zuplo modules (`modules/**`, `.zuplo/**`, `tests/**`)
- `frontend/tsconfig.json` — targets Next.js app; uses `@/*` path alias for the frontend root

These are independent — do not mix root and frontend imports.
