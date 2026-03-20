import pandas as pd
import networkx as nx
import torch
from torch_geometric.data import Data
from torch_geometric.nn import GCNConv
from torch_geometric.utils import negative_sampling
import torch.nn.functional as F

# --- Part 0: Re-run Graph Construction (from Step 2) ---
# In a real project, you'd save the graph and load it, but for simplicity,
# we just rebuild it here.
def build_graph():
  print("Building graph from CSVs...")
  plants_df = pd.read_csv('plants.csv')
  chemicals_df = pd.read_csv('phytochemicals.csv')
  proteins_df = pd.read_csv('proteins.csv')
  interactions_df = pd.read_csv('interactions.csv')

  G = nx.Graph()
  # Add nodes with attributes
  for _, row in plants_df.iterrows():
    G.add_node(row['Plant_ID'],type='plant', name=row['Common_Name_of_Plant'])
  for _, row in chemicals_df.iterrows():
    G.add_node(str(row['PubChem_CID']), type='chemical',name=row['Chemical_Name'])
  for _, row in proteins_df.iterrows():
    G.add_node(row['UniProt_ID'],type='protein', name=row['Protein_Name'])

  # Add edges with attributes
  for _, row in chemicals_df.iterrows():
    G.add_edge(str(row['PubChem_CID']), row['Plant_Source'],relation='is_found_in')

  # The interactions_df only contains 'UniProt_ID' and 'Protein_Name',
  # as confirmed by the previous execution. It does not contain 'PubChem_CID',
  # so chemical-protein interaction edges cannot be built from this DataFrame
  # as currently structured. The following loop is commented out to prevent KeyError.
  # If chemical-protein interactions are needed, 'interactions.csv' needs to be updated
  # to include 'PubChem_CID' or a different interaction file must be used.
  # for _, row in interactions_df.iterrows():
  #   if G.has_node(str(row['PubChem_CID'])) and G.has_node(row['UniProt_ID']):
  #     G.add_edge(str(row['PubChem_CID']), row['UniProt_ID'],relation='targets')

  return G
G = build_graph()
print(f"Graph built with {G.number_of_nodes()} nodes and{G.number_of_edges()} edges.")

# --- Part 1: Prepare Data for PyTorch Geometric ---
print("\n--- Preparing data for PyTorch Geometric ---")
# Create a mapping from node ID to an integer index
node_list = list(G.nodes())
node_to_int = {node: i for i, node in enumerate(node_list)}
# Create the edge_index tensor
# This describes all connections in the graph in the format PyG needs
edge_list = []
for u, v in G.edges():
  edge_list.append([node_to_int[u], node_to_int[v]])
  edge_list.append([node_to_int[v], node_to_int[u]]) # Add edges in both directions for an undirected graph
edge_index = torch.tensor(edge_list, dtype=torch.long).t().contiguous()
# Create node features (x) using one-hot encoding
# This gives each node a unique numerical vector
num_nodes = G.number_of_nodes()
x = F.one_hot(torch.arange(0, num_nodes), num_classes=num_nodes).float()
# Create the PyG Data object
data = Data(x=x, edge_index=edge_index)
# Identify the edges for our training task (chemical-protein interactions)
interaction_edges = []
for u, v, attrs in G.edges(data=True):
 if attrs.get('relation') == 'targets':
  interaction_edges.append([node_to_int[u], node_to_int[v]])

# Fix: Handle cases where no interaction edges are found
if len(interaction_edges) > 0:
    train_pos_edge_index = torch.tensor(interaction_edges, dtype=torch.long).t().contiguous()
    num_pos_samples = train_pos_edge_index.size(1)
else:
    # Create an empty tensor of shape (2, 0) if no positive edges
    train_pos_edge_index = torch.empty((2, 0), dtype=torch.long)
    num_pos_samples = 0

# Sample negative edges (pairs that are not connected)
# This is crucial for teaching the model what a "bad" link looks like
num_neg_samples = num_pos_samples # Match the number of positive samples

# Only perform negative sampling if there are positive samples to match
if num_neg_samples > 0:
    train_neg_edge_index = negative_sampling(
        edge_index=data.edge_index,
        num_nodes=data.num_nodes,
        num_neg_samples=num_neg_samples
    )
else:
    # If no positive samples, create an empty tensor for negative samples
    train_neg_edge_index = torch.empty((2, 0), dtype=torch.long)

print(f"Prepared PyG data object. Positive examples:{train_pos_edge_index.size(1)}, Negative examples:{train_neg_edge_index.size(1)}")

# --- Part 2: Define the GNN Model ---
print("\n--- Defining the GNN Model ---")
class GCNLinkPredictor(torch.nn.Module):
 def __init__(self, in_channels, hidden_channels, out_channels):
  super().__init__()
  self.conv1 = GCNConv(in_channels, hidden_channels)
  self.conv2 = GCNConv(hidden_channels, out_channels)
 def encode(self, x, edge_index):
  # Learn node embeddings
  x = self.conv1(x, edge_index).relu()
  return self.conv2(x, edge_index)
 def decode(self, z, edge_label_index):
  # Calculate a score for a given pair of nodes (an edge)
  # We use a simple dot product
  return (z[edge_label_index[0]] * z[edge_label_index[1]]).sum(dim=-1)
# Initialize the model
# in_channels = number of features per node (which is num_nodes because of one-hot)
# hidden_channels = an intermediate size, a hyperparameter to tune
# out_channels = the size of the final embedding vector for each node
model = GCNLinkPredictor(data.num_nodes, 128, 64)
optimizer = torch.optim.Adam(params=model.parameters(), lr=0.01)

# --- Part 3: The Training Loop ---
print("\n--- Starting Model Training ---")
def train():
  model.train()
  optimizer.zero_grad()

  # 1. Get node embeddings from the encoder
  z = model.encode(data.x, data.edge_index)

  # 2. Get scores for positive and negative edges
  pos_logits = model.decode(z, train_pos_edge_index)
  neg_logits = model.decode(z, train_neg_edge_index)

  # 3. Combine them and create labels
  logits = torch.cat([pos_logits, neg_logits])
  labels = torch.cat([torch.ones(pos_logits.size(0)), torch.zeros(neg_logits.size(0))])

  # 4. Calculate the loss (how wrong the model is)
  loss = F.binary_cross_entropy_with_logits(logits, labels)

  # 5. Backpropagate the error and update the model
  loss.backward()
  optimizer.step()

  return loss
for epoch in range(1, 201):
 loss = train()
 if epoch % 10 == 0:
  print(f"Epoch: {epoch:03d}, Loss: {loss:.4f}")
print("--- Training Complete ---")

# --- Part 4: Save the Trained Model ---
print("\n--- Saving the trained model ---")
# We save the trained state of the model, and also the node mapping
# which is essential for decoding the results later.
torch.save(model.state_dict(), 'trained_model.pth')
torch.save(node_to_int, 'node_to_int_mapping.pth')
torch.save(node_list, 'node_list.pth') # Save the node list as well
print("\nModel saved as 'trained_model.pth'.")
print("Node mapping saved as 'node_to_int_mapping.pth'.")
print("Step 3 is complete. You are now ready for the final prediction step!")