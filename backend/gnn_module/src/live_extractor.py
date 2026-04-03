import json
import os
import re
import logging
from slither.slither import Slither

logging.getLogger("Slither").setLevel(logging.CRITICAL)


# ---------------------------------------------------------------------------
# Helpers : génération de stubs pour les imports manquants
# ---------------------------------------------------------------------------

def _infer_param_type(expr: str) -> str:
    """Infère le type Solidity d'une expression d'argument (best-effort)."""
    expr = expr.strip()
    low = expr.lower()
    if (
        low.startswith("address(")
        or "address" in low
        or low in {"msg.sender", "tx.origin", "this", "_receiver", "receiver"}
    ):
        return "address"
    if low in {"true", "false"}:
        return "bool"
    if low.startswith("bytes"):
        return "bytes memory"
    return "uint256"


def _analyser_usages(source: str, nom_contrat: str) -> dict:
    """
    Détecte les méthodes appelées sur les variables du type `nom_contrat`
    dans le source Solidity et infère leurs signatures.

    Retourne { nom_methode → {"arg_exprs": [...], "payable": bool, "has_return": bool} }
    """
    # Variables de ce type : LenderPool public pool  →  ["pool"]
    vars_pattern = (
        rf"\b{re.escape(nom_contrat)}\b"
        rf"\s+(?:public\s+|private\s+|internal\s+|immutable\s+)*(\w+)\b"
    )
    vars_du_type = set(re.findall(vars_pattern, source))

    methodes: dict = {}

    for var in vars_du_type:
        # Passe 0 : enregistrer TOUS les noms de méthodes appelés, même imbriqués.
        # (le regex [^)]* ne capture pas les appels imbriqués comme pool.FEE()
        #  à l'intérieur de pool.withdraw(... + pool.FEE()) )
        all_names = re.findall(
            rf"\b{re.escape(var)}\.\s*(\w+)\s*\(",
            source,
        )
        for fn in all_names:
            methodes.setdefault(fn, {"arg_exprs": [], "payable": False, "has_return": False})

        # Appels payable : pool.deposit{value: msg.value}(args)
        payable_calls = re.findall(
            rf"\b{re.escape(var)}\.\s*(\w+)\s*\{{[^}}]*\}}\s*\(([^)]*)\)",
            source,
        )
        for fn, args_str in payable_calls:
            args = (
                [a.strip() for a in args_str.split(",") if a.strip()]
                if args_str.strip()
                else []
            )
            entry = methodes.setdefault(
                fn, {"arg_exprs": args, "payable": True, "has_return": False}
            )
            entry["payable"] = True

        # Appels normaux : pool.flashLoan(address(this), amount)
        # Note : [^)]* s'arrête au premier ')' → les appels imbriqués (step 0)
        # sont déjà enregistrés ; ici on enrichit les args quand c'est possible.
        normal_calls = re.findall(
            rf"\b{re.escape(var)}\.\s*(\w+)\s*\(([^)]*)\)",
            source,
        )
        for fn, args_str in normal_calls:
            args = (
                [a.strip() for a in args_str.split(",") if a.strip()]
                if args_str.strip()
                else []
            )
            entry = methodes.setdefault(
                fn, {"arg_exprs": args, "payable": False, "has_return": False}
            )
            # Conserver l'appel avec le plus d'arguments pour les surcharges
            if len(args) > len(entry.get("arg_exprs", [])):
                entry["arg_exprs"] = args

        # Détecte si la valeur de retour est utilisée dans une expression
        # (couvre aussi les appels imbriqués comme `+ pool.FEE()`)
        return_uses = re.findall(
            rf"(?:=|\+|-|\*|\/|\()\s*{re.escape(var)}\.\s*(\w+)\s*\(",
            source,
        )
        for fn in return_uses:
            # Ajouter si non encore détecté (cas des appels imbriqués)
            entry = methodes.setdefault(
                fn, {"arg_exprs": [], "payable": False, "has_return": True}
            )
            entry["has_return"] = True

    return methodes


def _generer_stub(nom_contrat: str, methodes: dict) -> str:
    """Génère le code source d'un contrat Solidity stub."""
    lines = [
        "// SPDX-License-Identifier: MIT",
        "pragma solidity ^0.8.0;",
        "",
        f"contract {nom_contrat} {{",
    ]
    for fn, info in methodes.items():
        arg_exprs = info.get("arg_exprs", [])
        params = ", ".join(
            f"{_infer_param_type(expr)} _p{i}"
            for i, expr in enumerate(arg_exprs)
        )
        modifiers = "external"
        if info.get("payable"):
            modifiers += " payable"
        ret = " returns (uint256)" if info.get("has_return") else ""
        lines.append(f"    function {fn}({params}) {modifiers}{ret} {{ }}")

    lines.append("    receive() external payable {}")
    lines.append("}")
    return "\n".join(lines)


def _symboles_importes_pour_chemin(source: str, chemin_cible: str) -> list[str]:
    """Extrait les noms dans import { A, B } from \"...chemin...\" si présent."""
    syms: list[str] = []
    for line in source.splitlines():
        if chemin_cible not in line or ".sol" not in line:
            continue
        m = re.search(
            r"import\s+\{([^}]+)\}\s+from\s+[\"']([^\"']+)[\"']",
            line,
        )
        if not m:
            continue
        if m.group(2).rstrip(";").strip() != chemin_cible:
            continue
        for part in m.group(1).split(","):
            part = part.strip()
            if not part:
                continue
            # "IERC20 as T" -> IERC20
            syms.append(part.split()[0])
    return syms


def _generer_stub_interfaces(chemin_import: str, symboles: list[str], source: str) -> str:
    """
    Stub minimal pour un fichier .sol manquant.
    Si symboles (import {A,B}), génère des interfaces vides (compile avec plus de cas).
    Sinon stub « contrat + méthodes » déduit des usages (types externes).
    """
    base = os.path.splitext(os.path.basename(chemin_import))[0]
    if symboles:
        lines = [
            "// SPDX-License-Identifier: MIT",
            "pragma solidity ^0.8.0;",
            "",
        ]
        for s in symboles:
            lines.append(f"interface {s} {{}}")
        return "\n".join(lines)
    methodes = _analyser_usages(source, base)
    return _generer_stub(base, methodes)


def _creer_stubs_imports(chemin_fichier: str) -> list:
    """
    Lit le fichier .sol, identifie les imports .sol manquants (relatifs ou sous-chemins),
    crée des stubs minimaux à l'emplacement attendu par solc.
    Retourne la liste des fichiers stubs créés.
    """
    dir_fichier = os.path.dirname(chemin_fichier)
    try:
        with open(chemin_fichier, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception:
        return []

    # Tous les chemins se terminant par .sol entre guillemets (hors chemins absolus disque)
    imports_tous = re.findall(
        r'import\s+[^;]*["\']([^"\']+\.sol)["\']',
        source,
    )

    stubs_crees = []
    for chemin_import in set(imports_tous):
        if not chemin_import or chemin_import.startswith("/"):
            continue
        chemin_abs = os.path.normpath(os.path.join(dir_fichier, chemin_import))
        if os.path.exists(chemin_abs):
            continue

        symboles = _symboles_importes_pour_chemin(source, chemin_import)
        stub_code = _generer_stub_interfaces(chemin_import, symboles, source)

        try:
            os.makedirs(os.path.dirname(chemin_abs), exist_ok=True)
            with open(chemin_abs, "w", encoding="utf-8") as f:
                f.write(stub_code)
            stubs_crees.append(chemin_abs)
            print(f"    [i] Stub généré : {chemin_import}")
        except Exception as e:
            print(f"    [!] Impossible de créer le stub {chemin_abs} : {e}")

    return stubs_crees


def _graphe_fallback_depuis_source(chemin_fichier: str, chemin_sortie: str) -> bool:
    """
    Si Slither échoue (solc, imports complexes, .vy, etc.), construit un graphe
    ligne à ligne pour permettre au GNN + vectoriseur de tourner quand même.
    Moins précis qu'un CFG Slither, mais évite l'échec total en mode « IA seule ».
    """
    try:
        with open(chemin_fichier, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"    [!] Fallback : lecture fichier impossible : {e}")
        return False

    nom_fichier = os.path.basename(chemin_fichier)
    contract_name = "Contract"
    for line in lines:
        m = re.search(r"\b(?:contract|interface)\s+(\w+)", line)
        if m:
            contract_name = m.group(1)
            break

    noeuds = []
    aretes = []
    max_nodes = 320
    idx = 0
    for line_num, line in enumerate(lines, start=1):
        if idx >= max_nodes:
            break
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
            continue
        if stripped in {"*/", "{", "}"}:
            continue

        noeuds.append({
            "noeud_id": f"fallback_{idx}",
            "type": "NodeType.EXPRESSION",
            "contenu": stripped[:260],
            "lignes": [line_num],
            "label_vulnerable": 0,
        })
        if idx > 0:
            aretes.append([idx - 1, idx])
        idx += 1

    if not noeuds:
        noeuds.append({
            "noeud_id": "fallback_0",
            "type": "NodeType.EXPRESSION",
            "contenu": "// (fichier vide ou non lisible)",
            "lignes": [1],
            "label_vulnerable": 0,
        })

    donnees_ast = {
        nom_fichier: {
            "nom_contrat": contract_name,
            "graphe_noeuds": noeuds,
            "aretes": aretes,
        }
    }
    try:
        with open(chemin_sortie, "w", encoding="utf-8") as f:
            json.dump(donnees_ast, f, indent=4)
    except OSError as e:
        print(f"    [!] Fallback : écriture JSON impossible : {e}")
        return False

    print(f"    [i] Graphe de secours généré ({len(noeuds)} nœuds) — Slither indisponible ou incomplet.")
    return True


# ---------------------------------------------------------------------------
# Extraction principale
# ---------------------------------------------------------------------------

def _extraire_avec_slither(chemin_fichier: str, chemin_sortie: str) -> bool:
    """
    Logique principale d'extraction Slither (factorisée pour permettre les retries).
    """
    slither = Slither(chemin_fichier)
    donnees_ast = {}

    if not slither.contracts:
        print(f"    [!] Erreur : Slither n'a trouvé aucun contrat dans {chemin_fichier}")
        return False

    # Sélectionner le contrat défini dans le fichier cible (pas dans un stub/import)
    nom_cible = os.path.basename(chemin_fichier)
    contrat = None
    for c in reversed(slither.contracts):
        try:
            sm = c.source_mapping
            fn = sm.get("filename", "") if isinstance(sm, dict) else str(getattr(sm, "filename", ""))
            if os.path.basename(fn) == nom_cible:
                contrat = c
                break
        except Exception:
            pass
    if contrat is None:
        contrat = slither.contracts[-1]

    noeuds_graphe = []
    aretes = []
    mapping_noeuds = {}
    compteur_index = 0

    # 1. CONSTRUCTION DES NOEUDS
    for fonction in contrat.functions_and_modifiers:
        for noeud in fonction.nodes:
            mapping_noeuds[noeud] = compteur_index

            lignes_propres = []
            if hasattr(noeud, "source_mapping") and noeud.source_mapping:
                if isinstance(noeud.source_mapping, dict):
                    lignes_brutes = noeud.source_mapping.get("lines", [])
                else:
                    lignes_brutes = getattr(noeud.source_mapping, "lines", [])
                lignes_propres = [int(l) for l in lignes_brutes if str(l).isdigit()]

            noeuds_graphe.append({
                "noeud_id": f"{fonction.name}_{noeud.node_id}",
                "type": str(noeud.type),
                "contenu": str(noeud.expression) if noeud.expression else "",
                "lignes": lignes_propres,
                "label_vulnerable": 0,
            })
            compteur_index += 1

    # 2. CONSTRUCTION DES ARETES
    for fonction in contrat.functions_and_modifiers:
        for noeud in fonction.nodes:
            if noeud in mapping_noeuds:
                index_source = mapping_noeuds[noeud]
                for fils in noeud.sons:
                    if fils in mapping_noeuds:
                        index_cible = mapping_noeuds[fils]
                        aretes.append([index_source, index_cible])

    nom_fichier = os.path.basename(chemin_fichier)
    donnees_ast[nom_fichier] = {
        "nom_contrat": contrat.name,
        "graphe_noeuds": noeuds_graphe,
        "aretes": aretes,
    }

    with open(chemin_sortie, "w", encoding="utf-8") as f:
        json.dump(donnees_ast, f, indent=4)

    return True


def extraire_contrat_local(chemin_fichier: str, chemin_sortie: str) -> bool:
    """
    Extrait l'AST/CFG d'un contrat Solidity.

    Stratégie :
      1. Slither direct (retour False ou exception → poursuite).
      2. Stubs pour imports .sol manquants, puis nouveau Slither.
      3. Si toujours impossible : graphe de secours ligne à ligne (GNN exploitable,
         ex. mode « IA seule » ou imports OpenZeppelin non installés).
    """
    erreur_originale = ""

    # --- Tentative 1 : Slither direct ---
    try:
        if _extraire_avec_slither(chemin_fichier, chemin_sortie):
            return True
        erreur_originale = "Slither : aucun graphe valide"
    except Exception as e:
        erreur_originale = str(e)
        print(f"    [!] Slither (essai 1) : {erreur_originale[:200]}")

    # --- Tentative 2 : stubs puis Slither ---
    stubs_crees = []
    try:
        stubs_crees = _creer_stubs_imports(chemin_fichier)
        try:
            if _extraire_avec_slither(chemin_fichier, chemin_sortie):
                return True
        except Exception as e2:
            print(f"    [!] Slither (essai 2 avec stubs) : {str(e2)[:200]}")
        if not stubs_crees:
            print("    [!] Aucun stub .sol généré (imports absolus ou déjà présents).")
    finally:
        for stub in stubs_crees:
            try:
                os.unlink(stub)
            except OSError:
                pass

    # --- Tentative 3 : graphe heuristique (pas de Slither) ---
    if _graphe_fallback_depuis_source(chemin_fichier, chemin_sortie):
        return True

    print(f"    [!] Echec extraction : {erreur_originale[:200]}")
    return False


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        extraire_contrat_local(sys.argv[1], sys.argv[2])
