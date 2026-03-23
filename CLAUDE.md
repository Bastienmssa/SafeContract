# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SafeContract is a web3/smart contract analysis platform with three layers:
- **Frontend**: Next.js 14 (App Router) marketing/product site
- **API Gateway**: Zuplo (TypeScript, OpenAPI-spec-first) — routes requests to backend or Ethereum RPC
- **Backend**: Python FastAPI — API d'analyse de contrats via Mythril
- **Core**: Rust library (stub, not yet implemented)

## Commands

### Frontend (Next.js)
```bash
cd frontend && npm install   # install dependencies
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

### Backend (FastAPI + Mythril)
```bash
cd backend
pip install fastapi uvicorn mythril   # mythril doit être installé séparément (pip install mythril)
uvicorn app.main:app --reload         # dev server (port 8000 par défaut)
```

L'outil CLI Mythril (`myth`) doit être disponible dans le PATH — il est invoqué directement via `subprocess` dans `app/services/mythril_service.py`.

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
       → Zuplo API Gateway (port 9000) → Python backend OR Ethereum RPC node
Caddy reverse proxy handles external HTTPS traffic (infra/Caddyfile)
```

### Zuplo API Gateway
Routes are defined declaratively in `config/routes.oas.json` (OpenAPI 3.1.0). Handler modules live in `modules/`. Current routes:
- `/todos/*` — example CRUD (to be replaced)
- `/rpc` — proxies to Ethereum node at `http://159.65.192.47.nip.io:8545`
- `/*` — catch-all proxy to `http://159.65.192.47.nip.io:3000`

To add a route, edit `config/routes.oas.json`; to add custom handler logic, add a TypeScript module in `modules/` and reference it via `x-zuplo-route`.

### Backend — Analyse Mythril
Le backend expose un seul endpoint pour l'instant :

- `POST /scan` (`app/api/scan.py`) — reçoit un `contract_path` (chemin vers un fichier `.sol`), appelle `analyze_contract()` du service Mythril, et retourne le rapport JSON.

`app/services/mythril_service.py` exécute `myth analyze <contract_path> -o json` en subprocess et parse le JSON retourné. Si Mythril échoue (returncode != 0), une exception est levée avec le stderr.

**À noter** : le `requirements.txt` est actuellement vide — les dépendances (`fastapi`, `uvicorn`, `mythril`) doivent être ajoutées.

### Frontend Components
The frontend is a landing page assembled from composable sections in `frontend/components/`. Each section is an independent React component. The page composition is in `frontend/app/page.tsx`. Custom Tailwind colors (primary green `#2cbe88`, dark `#152d5b`) are defined in `frontend/tailwind.config.ts`.

### TypeScript Configuration
Two separate tsconfig scopes:
- Root `tsconfig.json` — targets Zuplo modules (`modules/**`, `.zuplo/**`, `tests/**`)
- `frontend/tsconfig.json` — targets Next.js app; uses `@/*` path alias for the frontend root

These are independent — do not mix root and frontend imports.
