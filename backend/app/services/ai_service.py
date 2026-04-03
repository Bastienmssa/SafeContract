"""
backend/app/services/ai_service.py

Pont vers gnn_module/ai_service.py.
Ce fichier ne contient pas de logique — tout est dans gnn_module/.

Pour modifier le comportement du modèle : éditer gnn_module/ai_service.py
ou gnn_module/src/predict.py.
Ne jamais modifier gnn_module/src/models/gnn_model.py ni les poids .pth.

Configuration :
    GNN_MODULE_PATH (variable d'environnement) : chemin absolu vers gnn_module/.
    Par défaut : <backend>/gnn_module/ (résolu relativement à ce fichier).
"""
import os
import sys
import logging
import importlib.util

logger = logging.getLogger(__name__)

# ── Localisation de gnn_module/ ──────────────────────────────────────────────
_GNN_MODULE_PATH = os.environ.get(
    "GNN_MODULE_PATH",
    os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "gnn_module")
    ),
)

# ── Chargement de gnn_module/ai_service.py sous un alias pour éviter les ─────
# ── conflits de nom avec le présent fichier ───────────────────────────────────
try:
    _chemin_module = os.path.join(_GNN_MODULE_PATH, "ai_service.py")
    _spec = importlib.util.spec_from_file_location("gnn_ai_service", _chemin_module)
    _mod  = importlib.util.module_from_spec(_spec)

    # gnn_module/ doit être dans sys.path pour que ses imports internes fonctionnent
    if _GNN_MODULE_PATH not in sys.path:
        sys.path.insert(0, _GNN_MODULE_PATH)

    _spec.loader.exec_module(_mod)

    is_available     = _mod.is_available
    get_version      = _mod.get_version
    analyze_contract = _mod.analyze_contract

    logger.info("[GNN] Module chargé depuis %s", _chemin_module)

except Exception as _e:
    logger.warning("[GNN] Impossible de charger gnn_module/ai_service.py : %s", _e)

    def is_available() -> bool:
        return False

    def get_version() -> str:  # type: ignore[misc]
        return "GNN non disponible"

    def analyze_contract(contract_path: str, issues: list) -> dict:  # type: ignore[misc]
        return {
            "verdict":     "safe",
            "score":       0,
            "explanation": f"Module GNN non disponible : {_e}",
            "ai_issues":   [],
        }
