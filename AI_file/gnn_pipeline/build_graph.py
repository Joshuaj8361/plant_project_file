import os
import pandas as pd
import torch
from torch_geometric.data import HeteroData
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'Dataset')

def load_data():
    plants_df = pd.read_csv(os.path.join(DATA_DIR, 'plants.csv'))
    proteins_df = pd.read_csv(os.path.join(DATA_DIR, 'proteins.csv'))
    phytochemicals_df = pd.read_csv(os.path.join(DATA_DIR, 'phytochemicals.csv'))
    interactions_df = pd.read_csv(os.path.join(DATA_DIR, 'interactions.csv')).dropna()
    
    return plants_df, proteins_df, phytochemicals_df, interactions_df

def build_graph():
    plants_df, proteins_df, phytochemicals_df, interactions_df = load_data()
    
    # Create unique mappings for nodes
    plant_ids = plants_df['Plant_ID'].dropna().unique()
    phyto_ids = phytochemicals_df['PubChem_CID'].dropna().unique()
    protein_ids = proteins_df['UniProt_ID'].dropna().unique()
    
    plant_mapping = {str(id): i for i, id in enumerate(plant_ids)}
    phyto_mapping = {str(int(id)): i for i, id in enumerate(phyto_ids)}
    protein_mapping = {str(id): i for i, id in enumerate(protein_ids)}
    
    # Save mappings to JSON for inference later
    mappings = {
        'plant': plant_mapping,
        'phytochemical': phyto_mapping,
        'protein': protein_mapping
    }
    with open(os.path.join(BASE_DIR, 'gnn_pipeline', 'mappings.json'), 'w') as f:
        json.dump(mappings, f)
        
    # Reverse mappings
    rev_plant_mapping = {v: k for k, v in plant_mapping.items()}
    with open(os.path.join(BASE_DIR, 'gnn_pipeline', 'rev_plant_mapping.json'), 'w') as f:
        json.dump(rev_plant_mapping, f)
        
    # Initialize HeteroData
    data = HeteroData()
    
    # Add dummy node features (required by many PyG layers, we'll use 16-dim ones)
    data['plant'].x = torch.ones(len(plant_mapping), 16)
    data['phytochemical'].x = torch.ones(len(phyto_mapping), 16)
    data['protein'].x = torch.ones(len(protein_mapping), 16)
    
    # Plant -> Contains -> Phytochemical edges
    # Phytochemicals DF has Plant_Source and PubChem_CID
    p2p_src = []
    p2p_dst = []
    for _, row in phytochemicals_df.dropna(subset=['Plant_Source', 'PubChem_CID']).iterrows():
        plant = str(row['Plant_Source'])
        phyto = str(int(row['PubChem_CID']))
        if plant in plant_mapping and phyto in phyto_mapping:
            p2p_src.append(plant_mapping[plant])
            p2p_dst.append(phyto_mapping[phyto])
            
    data['plant', 'contains', 'phytochemical'].edge_index = torch.tensor([p2p_src, p2p_dst], dtype=torch.long)
    
    # Phytochemical -> Targets -> Protein edges
    c2p_src = []
    c2p_dst = []
    for _, row in interactions_df.dropna(subset=['PubChem_CID', 'UniProt_ID']).iterrows():
        try:
            phyto = str(int(row['PubChem_CID']))
        except:
            continue
        protein = str(row['UniProt_ID'])
        
        if phyto in phyto_mapping and protein in protein_mapping:
            c2p_src.append(phyto_mapping[phyto])
            c2p_dst.append(protein_mapping[protein])
            
    data['phytochemical', 'targets', 'protein'].edge_index = torch.tensor([c2p_src, c2p_dst], dtype=torch.long)
    
    # To use standard GNNs, we often make edges bidirectional
    data['phytochemical', 'rev_contains', 'plant'].edge_index = torch.tensor([p2p_dst, p2p_src], dtype=torch.long)
    data['protein', 'rev_targets', 'phytochemical'].edge_index = torch.tensor([c2p_dst, c2p_src], dtype=torch.long)
    
    # Save Graph
    torch.save(data, os.path.join(BASE_DIR, 'gnn_pipeline', 'graph.pt'))
    print("Graph built and saved successfully!")
    print(data)

if __name__ == '__main__':
    build_graph()
