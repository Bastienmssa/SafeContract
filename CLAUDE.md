# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SafeContract is a web3/smart contract analysis platform with four layers:
- **Frontend**: Next.js 14 (App Router) — site marketing + dashboard d'analyse
- **API Gateway**: Zuplo (TypeScript, OpenAPI-spec-first) — routes requests to backend or Ethereum RPC
- **Backend**: Python FastAPI — analyse multi-outils (Mythril, Slither, Solhint, Echidna, Foundry) + modèle GNN + persistance MongoDB
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
python3 -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn python-multipart motor python-dotenv
pip install mythril slither-analyzer solc-select pyyaml
pip install torch torch-geometric transformers
pip install ollama markdown2 weasyprint
uvicorn app.main:app --reload    # dev server (port 8000 par défaut)
```

**Important :** ne pas faire `pip install -r requirements.txt` en une seule fois — le graph de dépendances est trop complexe (torch + mythril + weasyprint). Installer par groupes comme ci-dessus.

MongoDB doit tourner sur `localhost:27017` (configurable via `MONGODB_URL` dans `backend/.env`).

### Security Tools (outils d'analyse)
```bash
# Solhint (linter Solidity)
npm install -g solhint

# Foundry (Mac)
curl -L https://foundry.paradigm.xyz | bash && foundryup
ln -s ~/.foundry/bin/forge /opt/homebrew/bin/forge   # rendre visible à Python

# Echidna (Mac)
brew install echidna

# solc (compiler Solidity, nécessaire pour Slither)
backend/.venv/bin/solc-select install 0.8.20
backend/.venv/bin/solc-select use 0.8.20
```

### Production / PM2 (serveur Linux — /home/SafeContract)
```bash
# 1. Libs système (weasyprint)
sudo apt install -y libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0

# 2. MongoDB
sudo systemctl start mongod && sudo systemctl enable mongod

# 3. Deploy principal (installe + build + PM2)
chmod +x deploy.sh && ./deploy.sh

# 4. Symlink Slither + solc
ln -s /home/SafeContract/backend/.venv/bin/slither /usr/local/bin/slither
backend/.venv/bin/solc-select install 0.8.20 && backend/.venv/bin/solc-select use 0.8.20

# 5. Echidna (Linux x86_64)
wget https://github.com/crytic/echidna/releases/download/v2.3.2/echidna-2.3.2-x86_64-linux.tar.gz
tar -xzf echidna-2.3.2-x86_64-linux.tar.gz && mv echidna /usr/local/bin/ && chmod +x /usr/local/bin/echidna

# 6. Solhint + Foundry
npm install -g solhint
curl -L https://foundry.paradigm.xyz | bash && foundryup

# 7. (Optionnel) Rapports LLM
curl -fsSL https://ollama.com/install.sh | sh && ollama pull mistral

# Logs / redémarrage
pm2 logs safe-contract-back
pm2 restart safe-contract-back
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
- `POST /scan` (`app/api/scan.py`) — reçoit un fichier `.sol`/`.vy`, lance les outils en parallèle, appelle le GNN, **sauvegarde en MongoDB**, retourne `{ status, id, report }`.
- `GET /analyses` (`app/api/analyses.py`) — liste toutes les analyses (triées par date desc). Retourne `[]` si MongoDB indisponible.
- `GET /analyses/{id}` (`app/api/analyses.py`) — récupère une analyse par son ObjectId MongoDB.

### Backend — Pipeline d'analyse (ordre d'exécution dans `scan.py`)
1. Validation extension (`.sol` ou `.vy`)
2. Écriture dans `/tmp` (fichier temporaire)
3. **Parallèle** : Mythril, Slither (+ Solhint, Echidna, Foundry pour `.sol`) — filtrés selon `tools` reçu
4. `aggregator.py` : `normalize_issue()` → `_deduplicate()` → `compute_score()`
5. **Séquentiel** : modèle GNN si `"ai"` dans `tools` et `is_available()` — marque les issues `CONFIRMED`, ajoute les `POTENTIAL`, recalcule le score avec `compute_score_weighted()`
6. Suppression du fichier temporaire
7. Sauvegarde MongoDB

### Backend — Score de sécurité
Deux variantes dans `aggregator.py` :
- `compute_score(issues)` : pénalités `critical -30, medium -15, low -5`
- `compute_score_weighted(issues)` : idem mais les issues `confirmedByGnn=True` ont un poids ×1.5

### Backend — Module GNN (`backend/gnn_module/`)
Modèle Graph Attention Network (GATConv, PyTorch Geometric) entraîné sur des smart contracts Solidity.

```
gnn_module/
├── ai_service.py          ← logique bridge + verdict/score/explanation
├── gnn_service.py         ← point d'entrée : analyser_contrat(chemin_sol, chemin_rapport)
├── src/
│   ├── config.py          ← DIM_TOTALE=786, HEADS=4, SEUIL_DEFAUT=0.60 — NE PAS MODIFIER
│   ├── live_extractor.py  ← extraction CFG via Slither
│   ├── live_vectorizer.py ← vectorisation CodeBERT (768 dim) + 18 features expertes
│   ├── predict.py         ← fusion GNN + outils, niveaux CONFIRMED/POTENTIAL/FILTERED
│   └── models/
│       └── gnn_model.py   ← architecture GNN — NE PAS MODIFIER (liée aux poids v6)
└── models/
    └── gnn_smart_contracts_v6_retrain.pth   ← poids entraînés — NE PAS MODIFIER
```

**Fichiers modifiables sans risque :** `gnn_module/ai_service.py`, `gnn_module/src/predict.py`
**Fichiers figés :** `gnn_module/src/models/gnn_model.py`, `gnn_module/src/config.py`, le `.pth`

**Variable d'environnement :** `GNN_MODULE_PATH` = chemin absolu vers `gnn_module/`. Par défaut résolu relativement à `app/services/ai_service.py`.

**Activation :** `is_available()` retourne `True` automatiquement si le `.pth` existe et si les dépendances sont installées (torch, torch-geometric, transformers).

**Niveaux de findings GNN :**
- `CONFIRMED` : outil ET GNN d'accord → vulnérabilité certaine
- `POTENTIAL` : GNN seul, confiance > seuil → remontée dans `ai_issues`
- `FILTERED` : outil a trouvé mais GNN détecte une protection dans le CFG (CEI, nonReentrant, contrôle d'accès)

**Vulnérabilités détectées :** SWC-107 (Reentrancy), SWC-115 (tx.origin), SWC-122 (Signature Replay), SWC-116 (Timestamp), SWC-120 (Bad Randomness), SWC-101 (Integer Overflow), SWC-113 (DoS), SWC-106 (Selfdestruct), SWC-112 (Delegatecall), SWC-104 (Unchecked Return), Unprotected ETH Withdrawal

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
  "issues": [{
    "line": 14, "severity": "critical", "title": "...", "description": "...", "swcId": "SWC-107",
    "tool": "mythril", "confirmedByGnn": true, "gnnConfidence": "0.92", "gnnDescription": "..."
  }],
  "summary": { "critical": 1, "medium": 0, "low": 2, "total": 3 },
  "tools_used": ["mythril", "slither", "ai"],
  "tools_errors": {},
  "tools_versions": { "mythril": "0.24.8" },
  "ai_verdict": { "verdict": "vulnerable", "score": 0.87, "explanation": "..." },
  "raw_tool_results": {},
  "analyzed_at": "ISODate",
  "status": "completed"
}
```
**Note :** les issues sont stockées avec le champ `description` (Python). Le frontend mappe `i.desc ?? i.description` pour compatibilité.

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

### Frontend — Sélecteur d'analyse (dashboard)
Dans l'onglet "Nouvelle analyse", l'utilisateur choisit via des **packages** + une checkbox IA :
- **Analyse Statique** (package) : Slither + Solhint — cochable indépendamment
- **Analyse Dynamique** (package) : Mythril + Foundry + Echidna — coché par défaut
- Au moins un package OU l'IA doit rester sélectionné
- **Intelligence Artificielle** (checkbox séparée) : GNN SafeContract — cochable indépendamment des packages
- Si l'IA est seule sélectionnée (sans package), le backend appelle uniquement le GNN

Le backend accepte `"ai"` dans le paramètre `tools` et appelle le GNN si `is_available()` == True.

### Frontend — Types (data.ts)
- `Issue` : `{ line, severity, title, desc, swcId, tool?, confirmedByGnn?, gnnConfidence?, gnnDescription? }`
- `AiVerdict` : `{ verdict: "vulnerable"|"safe", score: number, explanation: string }`
- `Contract` : inclut `toolsUsed?`, `toolsErrors?`, `toolsVersions?`, `aiVerdict?`
- `buildContracts()` mappe les issues DB (`description`) → `Issue.desc` (évite le mismatch de champ)

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
