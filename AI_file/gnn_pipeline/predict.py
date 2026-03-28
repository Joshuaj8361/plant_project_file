import os
import json
import torch
import pandas as pd
import torch.nn.functional as F

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPELINE_DIR = os.path.join(BASE_DIR, 'gnn_pipeline')

# Load files once in memory
MAPPINGS_PATH = os.path.join(PIPELINE_DIR, 'mappings.json')
REV_PLANT_MAPPING_PATH = os.path.join(PIPELINE_DIR, 'rev_plant_mapping.json')
EMBEDDINGS_PATH = os.path.join(PIPELINE_DIR, 'embeddings.pt')
DISEASE_MAPPING_PATH = os.path.join(BASE_DIR, 'Dataset', 'disease_mapping.csv')
PLANTS_PATH = os.path.join(BASE_DIR, 'Dataset', 'plants.csv')

# These will be initialized exactly once when module loads
mappings = None
rev_plant_mapping = None
embeddings = None
disease_df = None
plants_df = None

def init_gnn():
    global mappings, rev_plant_mapping, embeddings, disease_df, plants_df
    try:
        with open(MAPPINGS_PATH, 'r') as f:
            mappings = json.load(f)
        with open(REV_PLANT_MAPPING_PATH, 'r') as f:
            rev_plant_mapping = json.load(f)
            
        embeddings = torch.load(EMBEDDINGS_PATH, weights_only=False)
        disease_df = pd.read_csv(DISEASE_MAPPING_PATH)
        plants_df = pd.read_csv(PLANTS_PATH)
        
        # Ensure we have the embeddings in memory
        if 'plant' not in embeddings:
            raise Exception("Plant embeddings not found in saved embeddings!")
            
    except Exception as e:
        print(f"Error initializing GNN prediction module: {e}")

def predict_plants_for_disease(disease_name, top_k=5):
    """
    Given a disease name, finds matching known plants in the dataset,
    gets their learned GNN embeddings, computes an average disease embedding,
    and finds the top K most similar *novel* recommended plants.
    """
    if embeddings is None:
        init_gnn()
        
    if embeddings is None:
        return []

    # 1. Find known matching plant IDs for the disease
    disease_search = disease_name.strip().lower()
    matched_rows = disease_df[disease_df['Disease'].str.lower() == disease_search]
    
    if matched_rows.empty:
        return []
        
    known_plant_ids = matched_rows['Plant_ID'].unique().tolist()
    
    # 2. Extract their GNN embeddings based on index mappings
    known_node_indices = []
    for pid in known_plant_ids:
        # plant mapping keys might be strings
        if str(pid) in mappings['plant']:
            known_node_indices.append(mappings['plant'][str(pid)])
            
    if not known_node_indices:
        return []
        
    # Get all plant embeddings
    plant_embs = embeddings['plant']
    
    # Get average embedding of known plants to conceptually represent the "disease vector profile"
    known_embs = plant_embs[known_node_indices]
    disease_vector = known_embs.mean(dim=0).unsqueeze(0)
    
    # 3. Compute cosine similarity against ALL plants
    # Normalize vectors to compute cosine sim via dot product
    plant_embs_norm = F.normalize(plant_embs, p=2, dim=1)
    disease_vector_norm = F.normalize(disease_vector, p=2, dim=1)
    
    similarities = torch.mm(disease_vector_norm, plant_embs_norm.t()).squeeze(0)
    
    # We want to exclude the known plants from suggestions so they are truly "novel" inferences
    # (Or we can include them but label them. Let's exclude for pure novelty).
    # We set their similarity extremely low
    similarities[known_node_indices] = -1.0
    
    # 4. Get the Top K most similar
    top_indices = similarities.argsort(descending=True)[:top_k].tolist()
    
    # 5. Map back to human-readable response
    results = []
    for idx in top_indices:
        str_idx = str(idx)
        if str_idx in rev_plant_mapping:
            plant_id = rev_plant_mapping[str_idx]
            sim_score = similarities[idx].item()
            
            # Fetch plant properties
            plant_info = plants_df[plants_df['Plant_ID'] == plant_id]
            if not plant_info.empty:
                row = plant_info.iloc[0]
                results.append({
                    "Plant_ID": plant_id,
                    "Common_Name_of_Plant": row.get('Common_Name_of_Plant', 'Unknown'),
                    "GNN_Similarity_Score": round(sim_score * 100, 2)  # as percentage
                })
                
    return results

# Initialize when imported
init_gnn()
