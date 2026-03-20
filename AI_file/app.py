import os
from flask import Flask, jsonify, render_template
import pandas as pd

app = Flask(__name__)

# Base directory for the Flask app (AI_file)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Data directory is one level up in my_code folder
DATA_DIR = os.path.join(BASE_DIR, '..', 'my_code')

# Load Datasets globally to act as an in-memory database
try:
    plants_df = pd.read_csv(os.path.join(DATA_DIR, 'plants.csv'))
    proteins_df = pd.read_csv(os.path.join(DATA_DIR, 'proteins.csv'))
    phytochemicals_df = pd.read_csv(os.path.join(DATA_DIR, 'phytochemicals.csv'))
    interactions_df = pd.read_csv(os.path.join(DATA_DIR, 'interactions.csv'))
    print("✅ All datasets loaded successfully!")
except Exception as e:
    print(f"❌ Error loading datasets: {e}")
    plants_df, proteins_df, phytochemicals_df, interactions_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

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
    from flask import request
    disease = request.args.get('disease', '').strip().lower()
    
    # Since the curated dataset specifically focuses on Type-2 Diabetes targets:
    if 'diabetes' in disease or 'diabetic' in disease:
        return jsonify(plants_df.fillna('').to_dict(orient='records'))
    else:
        return jsonify([])

if __name__ == '__main__':
    # Run the Flask app
    app.run(debug=True, port=5000)
