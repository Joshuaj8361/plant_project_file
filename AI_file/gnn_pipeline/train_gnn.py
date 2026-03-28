import os
import torch
import torch.nn.functional as F
from torch_geometric.data import HeteroData
from torch_geometric.nn import SAGEConv, to_hetero

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAPH_PATH = os.path.join(BASE_DIR, 'gnn_pipeline', 'graph.pt')

class GNN(torch.nn.Module):
    def __init__(self, hidden_channels):
        super().__init__()
        self.conv1 = SAGEConv((-1, -1), hidden_channels)
        self.conv2 = SAGEConv((-1, -1), hidden_channels)

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index).relu()
        x = self.conv2(x, edge_index)
        return x

class LinkPredictor(torch.nn.Module):
    def forward(self, x_i, x_j):
        return (x_i * x_j).sum(dim=-1)

class HeteroLinkPredictionModel(torch.nn.Module):
    def __init__(self, hidden_channels, metadata):
        super().__init__()
        # Use simple GNN applied to hetero graph
        self.gnn = to_hetero(GNN(hidden_channels), metadata, aggr='sum')
        self.predictor = LinkPredictor()

    def forward(self, x_dict, edge_index_dict, edge_label_index):
        # 1. Get node embeddings
        x_dict = self.gnn(x_dict, edge_index_dict)
        
        # 2. Extract embeddings for the predicted edge nodes (phytochemical -> protein)
        src_node_type, rel_type, dst_node_type = ('phytochemical', 'targets', 'protein')
        x_src = x_dict[src_node_type][edge_label_index[0]]
        x_dst = x_dict[dst_node_type][edge_label_index[1]]

        # 3. Predict probability (logits first, output is sum of dot products)
        return self.predictor(x_src, x_dst)

def train_gnn():
    print("Loading graph...")
    data = torch.load(GRAPH_PATH, weights_only=False)
    
    # Simple training loop for Link Prediction (phytochemical -> targets -> protein)
    # Note: For production, we would use proper edge splitting train/val/test and negative sampling.
    # Here we show a basic demonstration training loop.
    
    pos_edge_index = data['phytochemical', 'targets', 'protein'].edge_index
    num_pos_edges = pos_edge_index.size(1)
    
    # Generate negative edges randomly
    num_phytos = data['phytochemical'].x.size(0)
    num_proteins = data['protein'].x.size(0)
    neg_edge_index = torch.randint(0, num_phytos, (1, num_pos_edges), dtype=torch.long)
    neg_edge_index = torch.cat([neg_edge_index, torch.randint(0, num_proteins, (1, num_pos_edges), dtype=torch.long)], dim=0)

    # Combine pos and neg edges
    edge_label_index = torch.cat([pos_edge_index, neg_edge_index], dim=1)
    edge_label = torch.cat([torch.ones(num_pos_edges), torch.zeros(num_pos_edges)], dim=0)

    model = HeteroLinkPredictionModel(hidden_channels=32, metadata=data.metadata())
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    criterion = torch.nn.BCEWithLogitsLoss()

    print("Training started...")
    for epoch in range(1, 101):
        optimizer.zero_grad()
        out = model(data.x_dict, data.edge_index_dict, edge_label_index)
        loss = criterion(out, edge_label)
        loss.backward()
        optimizer.step()
        
        if epoch % 10 == 0:
            print(f'Epoch: {epoch:03d}, Loss: {loss:.4f}')
            
    # Save the trained model
    torch.save(model.state_dict(), os.path.join(BASE_DIR, 'gnn_pipeline', 'model.pth'))
    # Pre-compute final node embeddings and save to file for fast prediction
    model.eval()
    with torch.no_grad():
        final_embeddings = model.gnn(data.x_dict, data.edge_index_dict)
        torch.save(final_embeddings, os.path.join(BASE_DIR, 'gnn_pipeline', 'embeddings.pt'))
        
    print("Training finished! Model and embeddings saved.")

if __name__ == '__main__':
    train_gnn()
