import os
from flask import Flask, jsonify, render_template, request
import pandas as pd

app = Flask(__name__)

# Base directory for the Flask app (AI_file)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Changed the# Data directory is one level up in my_code folder
DATA_DIR = os.path.join(BASE_DIR, 'Dataset')

# Load Datasets globally to act as an in-memory database
try:
    plants_df = pd.read_csv(os.path.join(DATA_DIR, 'plants.csv'))
    proteins_df = pd.read_csv(os.path.join(DATA_DIR, 'proteins.csv'))
    phytochemicals_df = pd.read_csv(os.path.join(DATA_DIR, 'phytochemicals.csv'))
    interactions_df = pd.read_csv(os.path.join(DATA_DIR, 'interactions.csv'))
    
    # Load Disease Mapping Dataset
    MAPPING_DIR = os.path.join(BASE_DIR, 'Dataset')
    disease_mapping_df = pd.read_csv(os.path.join(MAPPING_DIR, 'disease_mapping.csv'))
    
    print("✅ All datasets loaded successfully!")
except Exception as e:
    print(f"❌ Error loading datasets: {e}")
    plants_df, proteins_df, phytochemicals_df, interactions_df, disease_mapping_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

@app.route('/')
def index():
    """Serves the main frontend page."""
    return render_template('index.html')

@app.route('/api/plants', methods=['GET'])
def get_plants():
    # fillna('') is necessary to ensure JSON compatibility for missing values
    return jsonify(plants_df.fillna('').to_dict(orient='records'))

@app.route('/api/proteins', methods=['GET'])
def get_proteins():
    return jsonify(proteins_df.fillna('').to_dict(orient='records'))

@app.route('/api/phytochemicals', methods=['GET'])
def get_phytochemicals():
    return jsonify(phytochemicals_df.fillna('').to_dict(orient='records'))

@app.route('/api/interactions', methods=['GET'])
def get_interactions():
    return jsonify(interactions_df.fillna('').to_dict(orient='records'))

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Returns basic counts of our datasets for the dashboard."""
    return jsonify({
        "total_plants": len(plants_df),
        "total_proteins": len(proteins_df),
        "total_phytochemicals": len(phytochemicals_df),
        "total_interactions": len(interactions_df)
    })

@app.route('/api/disease-search', methods=['GET'])
def search_disease():
    disease = request.args.get('disease', '').strip().lower()
    
    if not disease_mapping_df.empty:
        # Find matching plant IDs for this disease (case-insensitive)
        disease_mapping_df['Disease'] = disease_mapping_df['Disease'].str.lower()
        matched_ids = disease_mapping_df[disease_mapping_df['Disease'] == disease]['Plant_ID'].tolist()
        
        if matched_ids and not plants_df.empty and not phytochemicals_df.empty:
            # Filter plants to only those that treat this disease
            matched_plants = plants_df[plants_df['Plant_ID'].isin(matched_ids)]
            # Calculate efficiency: count phytochemicals per plant
            efficiency = phytochemicals_df.groupby('Plant_Source').size().reset_index(name='Efficiency_Score')
            # Merge with matched plants
            ranked_plants = pd.merge(matched_plants, efficiency, left_on='Plant_ID', right_on='Plant_Source', how='left')
            # Fill NaN for plants with 0 phytochemicals
            ranked_plants['Efficiency_Score'] = ranked_plants['Efficiency_Score'].fillna(0)
            # Sort by efficiency descending and take top 5
            top_5_plants = ranked_plants.sort_values(by='Efficiency_Score', ascending=False).head(5)
            # Remove the extra Plant_Source column
            if 'Plant_Source' in top_5_plants.columns:
                top_5_plants = top_5_plants.drop(columns=['Plant_Source'])
            
            return jsonify(top_5_plants.fillna('').to_dict(orient='records'))

    return jsonify([])

from gnn_pipeline.predict import predict_plants_for_disease

@app.route('/api/gnn-predict', methods=['GET'])
def gnn_predict():
    disease = request.args.get('disease', '').strip()
    if not disease:
        return jsonify([])
        
    try:
        results = predict_plants_for_disease(disease, top_k=5)
        return jsonify(results)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    

if __name__ == '__main__':
    # Support local runs and platform-provided ports such as Render's PORT env var.
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '').lower() in {'1', 'true', 'yes'}
    app.run(host='0.0.0.0', port=port, debug=debug)
