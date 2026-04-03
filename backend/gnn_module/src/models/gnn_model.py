import torch
import torch.nn.functional as F
from torch_geometric.nn import GATConv, LayerNorm
from src.config import DIM_TOTALE, HEADS


class SmartContractGNN(torch.nn.Module):
    """
    GNN pour la detection de vulnerabilites dans les smart contracts.

    Architecture :
      - norm_entree : LayerNorm sur les features d'entree (786D)
      - gat1        : GATConv(786 -> 128, heads=4, concat=True) => 512D
      - norm1       : LayerNorm(512)
      - gat2        : GATConv(512 -> 128, heads=1, concat=False) => 128D
      - norm2       : LayerNorm(128)
      - memoire_origine : connexion residuelle Linear(786 -> 128)
      - classifieur : Linear(128 -> 2)
    """

    def __init__(self, in_channels=DIM_TOTALE, hidden_channels=128, out_channels=2, heads=HEADS):
        super(SmartContractGNN, self).__init__()

        self.norm_entree = LayerNorm(in_channels)

        # Couche 1 : analyse large du voisinage (4 tetes d'attention, concat=True)
        self.gat1 = GATConv(in_channels, hidden_channels, heads=heads, concat=True)
        self.norm1 = LayerNorm(hidden_channels * heads)

        # Couche 2 : agregation fine (1 tete, concat=False)
        self.gat2 = GATConv(hidden_channels * heads, hidden_channels, heads=1, concat=False)
        self.norm2 = LayerNorm(hidden_channels)

        # Connexion residuelle : preserve l'identite du noeud d'origine
        self.memoire_origine = torch.nn.Linear(in_channels, hidden_channels)

        # Classifieur final
        self.classifieur = torch.nn.Linear(hidden_channels, out_channels)

    def forward(self, x, edge_index):
        identite_brute = self.memoire_origine(x)

        x = self.norm_entree(x)
        x = F.elu(self.gat1(x, edge_index))
        x = self.norm1(x)
        x = F.dropout(x, p=0.2, training=self.training)

        x = self.gat2(x, edge_index)
        x_graphe = self.norm2(x)

        x_final = F.elu(x_graphe + identite_brute)
        x_final = F.dropout(x_final, p=0.2, training=self.training)

        return self.classifieur(x_final)
