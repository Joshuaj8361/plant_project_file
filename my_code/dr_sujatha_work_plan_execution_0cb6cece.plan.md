---
name: Dr Sujatha work plan execution
overview: Summarize the PDF’s 4-step computational drug-discovery workflow and provide an executable, Windows-friendly step-by-step plan with concrete deliverables (CSVs, scripts, trained model, predictions).
todos:
  - id: pdf-summarize
    content: Convert the PDF’s 4 steps into runnable deliverables (CSVs, scripts, model outputs) with Windows-friendly commands and clear exit criteria.
    status: in_progress
  - id: fix-pdf-gaps
    content: Address PDF code gaps that prevent Step 4 from running (graph saving/loading consistency, indentation/line-wrap issues, correct drawing call).
    status: pending
  - id: execution-checklist
    content: Provide a final checklist mapping each step to required inputs, expected outputs, and verification checks.
    status: pending
isProject: false
---

# Summary of what’s in the PDF

The PDF titled “Dr. S. Sujatha - work Plan” describes an end-to-end computational workflow to discover **new anti-diabetic phytochemical → human protein target** hypotheses using a **knowledge graph** and a **Graph Neural Network (GNN)**.

- **Step 1 (Data collection / “shopping list”)**: build 4 clean datasets:
  - `plants.csv` (Plant_ID, Plant_Name)
  - `phytochemicals.csv` (PubChem_CID, Chemical_Name, Plant_Source)
  - `proteins.csv` (UniProt_ID, Protein_Name)
  - `interactions.csv` (PubChem_CID, UniProt_ID) as a known “answer key” from BindingDB
- **Step 2 (Connect the dots)**: write a Python script using `pandas` + `networkx` (optionally `matplotlib`) to construct a graph whose nodes are plants/chemicals/proteins and edges represent `is_found_in` and `targets`.
- **Step 3 (Train the detective)**: use **PyTorch Geometric** to train a simple GCN-based link prediction model using known chemical–protein edges as positives and sampled negatives.
- **Step 4 (Get predictions)**: load the trained model and score **novel** chemical–protein pairs, rank them, and print the top candidates.

The PDF also lists **3 alternatives**: (1) classical ML on chemical fingerprints (RDKit + RandomForest/XGBoost), (2) enrich graph using NLP on papers (BioBERT/SciBERT), (3) graph analytics to rank plants/communities (PageRank/Louvain).

# Important “paper vs runnable code” notes

The PDF includes code blocks, but some lines are **broken by line wrapping/indentation** (common in PDFs). When implementing, ensure:

- Python indentation is correct in loops (`for ...:` blocks) and `if` blocks.
- In Step 4, the PDF references `nx.read_gpickle('graph.gpickle')` but earlier steps don’t explicitly save `graph.gpickle`. You must either:
  - save the graph during Step 2/3 (`nx.write_gpickle(G, 'graph.gpickle')`), or
  - rebuild the graph again in Step 4 exactly as in training.
- In Step 2’s “complete script” section, a line uses `nx.draw(pos, ...)` (missing `G,` argument); the correct call is typically `nx.draw(G, pos, ...)`.

# Execution plan (Windows / PowerShell friendly)

## Inputs you need (from databases)

- IMPPAT: plant → phytochemicals + PubChem CIDs
- PubChem: CIDs (as universal compound IDs)
- UniProt: target proteins + UniProt accessions (human)
- BindingDB: known ligand–target interactions (for training positives)

## Folder layout (recommended)

Create a single project folder containing:

- `plants.csv`
- `phytochemicals.csv`
- `proteins.csv`
- `interactions.csv`
- `build_graph.py`
- `train_model.py`
- `predict.py`
- outputs: `graph.gpickle`, `trained_model.pth`, `node_to_int_mapping.pth`, `node_list.pth`, `predictions.csv` (recommended)

## Step 1 — Build the 4 CSVs (deliverables)

1. **Create `plants.csv`**
  - Start with 5–10 South Indian anti-diabetic plants.
  - Columns: `Plant_ID`, `Plant_Name` (IDs like `P001`).
2. **Create `phytochemicals.csv`**
  - For each plant, query IMPPAT and list phytochemicals.
  - Capture: `PubChem_CID`, `Chemical_Name`, `Plant_Source` (Plant_ID).
3. **Create `proteins.csv`**
  - Pick 2–3 validated T2D targets (PDF suggests **DPP-4** and **Alpha-glucosidase**).
  - From UniProt, store `UniProt_ID`, `Protein_Name` for *Homo sapiens*.
4. **Create `interactions.csv`**
  - From BindingDB, collect known binders for each target.
  - Store `PubChem_CID`, `UniProt_ID`.

**Exit criteria**: All 4 files load cleanly in Excel and have consistent headers; IDs match exactly (no extra spaces).

## Step 2 — Build a knowledge graph (`build_graph.py`)

1. Install basics:
  - `pip install pandas networkx matplotlib`
2. Implement `build_graph.py` to:
  - read the 4 CSVs
  - add nodes with attributes `type` and `name`
  - add edges:
    - chemical → plant with `relation='is_found_in'`
    - chemical → protein with `relation='targets'`
  - print counts (#nodes/#edges)
  - optional: visualize (expect “hairball” if large)
  - **save** graph to `graph.gpickle` for Step 4 consistency
3. Run:
  - `python build_graph.py`

**Exit criteria**: script completes; counts look plausible; `graph.gpickle` exists.

## Step 3 — Train a GNN link predictor (`train_model.py`)

1. Install PyTorch (CPU is fine) using the official selector, then install PyTorch Geometric.
2. Ensure training script:
  - builds or loads the exact same graph structure
  - creates `node_to_int` mapping and consistent `edge_index`
  - defines GCN encoder + dot-product decoder
  - constructs positives from `relation='targets'` edges
  - samples negative edges
  - trains for a fixed number of epochs and prints loss periodically
  - saves:
    - `trained_model.pth`
    - `node_to_int_mapping.pth`
    - `node_list.pth`
3. Run:
  - `python train_model.py`

**Exit criteria**: loss generally decreases; saved `.pth` files exist.

## Step 4 — Predict novel interactions (`predict.py`)

1. Load:
  - `trained_model.pth`, mappings, and **the same** `graph.gpickle` (or rebuild identically).
2. Generate all candidate (chemical, protein) pairs.
3. Filter out already-known edges.
4. Score with the trained model and apply sigmoid to get probabilities.
5. Rank and print top N; also write a `predictions.csv` (recommended) containing:
  - Chemical_Name, PubChem_CID, Source_Plant, Protein_Name, UniProt_ID, Confidence
6. Run:
  - `python predict.py`

**Exit criteria**: you get a ranked list of plausible new hypotheses.

## What to do with results (real-world “execution”)

- Prioritize top-ranked predictions by:
  - literature support (PubMed search)
  - druggability/assay availability for target
  - compound availability and safety
- Validate experimentally (in vitro binding/enzymatic inhibition; then cellular assays).

## Optional extensions (from PDF)

- **Baseline model**: RDKit fingerprints + RandomForest/XGBoost to predict activity.
- **NLP enrichment**: add edges extracted from papers using BioBERT/SciBERT.
- **Network analytics**: PageRank plants, community-detect chemical clusters.

