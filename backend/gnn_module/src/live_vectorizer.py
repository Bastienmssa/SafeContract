import os
import json
import torch
from transformers import AutoTokenizer, AutoModel
from src.config import DIM_EXPERTE, DIM_CODEBERT

def extraire_regles_expertes(noeud):
    """Calcule le vecteur expert V5 (18 dimensions)."""
    vecteur = [0.0] * DIM_EXPERTE 
    contenu = noeud.get("contenu", "").lower()
    type_noeud = noeud.get("type", "").lower()
    texte_complet = contenu + " " + type_noeud
    
    # --- REGLES V4 ---
    if any(x in texte_complet for x in ["call.value", "send(", "transfer("]): vecteur[0] = 1.0
    if "msg.sender" in texte_complet: vecteur[1] = 1.0
    if any(x in texte_complet for x in ["require", "assert", "revert"]): vecteur[2] = 1.0
    if "selfdestruct" in texte_complet: vecteur[3] = 1.0
    if "delegatecall" in texte_complet: vecteur[4] = 1.0
    if "block.timestamp" in texte_complet or "now" in texte_complet: vecteur[9] = 1.0
    if any(x in texte_complet for x in ["+", "-", "*", "/"]): vecteur[11] = 1.0
    if "for(" in texte_complet or "while(" in texte_complet: vecteur[12] = 1.0
    
    # --- NOUVELLES REGLES V5 ---
    if "ecrecover" in texte_complet or "verify(" in texte_complet: 
        vecteur[16] = 1.0
    if any(x in texte_complet for x in ["nonce", "usedsignatures", "executed"]): 
        vecteur[17] = 1.0
        
    return vecteur

def vectoriser_graphes(chemin_json, chemin_pt):
    """Convertit le JSON temporaire en tenseur V5."""
    # SECURITE : Si on passe un dossier au lieu d'un fichier, on cree le nom de fichier
    if os.path.isdir(chemin_pt):
        chemin_pt = os.path.join(chemin_pt, "temp_audit_v5.pt")

    with open(chemin_json, 'r', encoding='utf-8') as f:
        donnees = json.load(f)
    
    nom_contrat = list(donnees.keys())[0]
    noeuds = donnees[nom_contrat].get("graphe_noeuds", [])
    
    appareil = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained("microsoft/codebert-base")
    model_bert = AutoModel.from_pretrained("microsoft/codebert-base").to(appareil)
    
    vecteurs_fusionnes = []
    for noeud in noeuds:
        texte = f"{noeud.get('type', '')} {noeud.get('contenu', '')}"
        inputs = tokenizer(texte, return_tensors="pt", truncation=True, max_length=128).to(appareil)
        with torch.no_grad():
            outputs = model_bert(**inputs)
        v_bert = outputs.last_hidden_state.mean(dim=1).squeeze(0).cpu()
        
        v_expert = torch.tensor(extraire_regles_expertes(noeud), dtype=torch.float32)
        v_final = torch.cat((v_bert, v_expert), dim=0)
        vecteurs_fusionnes.append(v_final)
    
    aretes = donnees[nom_contrat].get("aretes", [])
    edge_index = torch.tensor(aretes, dtype=torch.long).t().contiguous() if aretes else torch.empty((2, 0), dtype=torch.long)
    
    torch.save({
        'x': torch.stack(vecteurs_fusionnes),
        'edge_index': edge_index
    }, chemin_pt)