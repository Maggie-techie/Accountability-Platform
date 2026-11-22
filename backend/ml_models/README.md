# GNN-Based Anomaly Detection for Public Funds Accountability

This module implements a **Graph Variational Autoencoder (GVAE)** to detect anomalous patterns in public funds expenditure, financial inconsistencies, and suspicious governance relationships in Nyeri County.

---

## 🎯 What Problem Does This Solve?

**In plain language:** The system looks at how money flows through Nyeri County's government (county government + 6 constituencies) over multiple years and flags anything that looks unusual — like a constituency receiving way more money than peers, or audit findings that don't match the spending patterns.

**Why use a graph model?** Government entities aren't isolated — they're connected by oversight relationships, shared fiscal years, and peer comparisons. A graph model captures these connections naturally, so anomalies that only appear *in context* (e.g., "this constituency has 5x more audit findings than similar ones in the same year") are detected automatically.

---

## 🧠 How It Works (Conceptual Overview)

### 1. Building the "Knowledge Graph"

The system builds a network (graph) where:
- **Nodes** = "Entity + Year" pairs (e.g., "Kieni Constituency FY2023/24", "County Governor FY2022/23")
- **Edges** = Relationships between them:
  - **Temporal**: Same entity across consecutive years (Kieni 2022 → Kieni 2023)
  - **Peer**: Similar entities in the same year (all 6 constituencies in FY2023/24)
  - **Governance**: Governor ↔ Constituencies in the same year (oversight relationship)

### 2. What Data Feeds Each Node

| Entity Type | Financial Features | Audit Features | Context Features |
|-------------|-------------------|----------------|------------------|
| **Constituency-Year** | Total NG-CDF allocation, average per project, number of projects | Findings count, misappropriation count, amount flagged | Urban/rural, year position, log-scaled totals |
| **Governor-Year** | Total county revenue, number of revenue sources | County audit findings, amount flagged | Department absorption rates, number of departments |

All numbers are normalized (scaled) so a "KSh 5B" and "5 findings" can be compared fairly.

### 3. The Model: Graph Variational Autoencoder (GVAE)

Think of it as a **compressor-decompressor that learns normal patterns**:

| Component | Role |
|-----------|------|
| **Encoder (2-layer GCN)** | Compresses each node's features + its neighbors' features into a compact "embedding" (16 numbers that summarize the node's context) |
| **Variational Layer** | Adds slight randomness so the model learns a *distribution* of normal patterns, not just one rigid template |
| **Decoder (Inner Product)** | Tries to reconstruct the graph connections from embeddings — "Do these two nodes belong connected?" |
| **Training Objective** | Minimize: (reconstruction error) + (how far embeddings drift from a standard normal distribution) |

**After training:** Normal nodes have embeddings that cluster together; anomalies end up in sparse regions of the embedding space.

### 4. Anomaly Detection: Three Independent Signals

The system doesn't rely on just one method — it ensembles three complementary detectors:

| Detector | What It Catches | Weight |
|----------|-----------------|--------|
| **k-NN Distance in Embedding Space** | Nodes far from their peers in the learned representation | 40% |
| **Isolation Forest** | Nodes that are easy to "isolate" in a random forest (statistical outliers) | 30% |
| **Edge Reconstruction Error** | Nodes whose connections the decoder fails to predict (unexpected relationships) | 30% |

**Final anomaly score** = weighted average of normalized scores from all three. Top 10% of nodes are flagged.

### 5. Human-Readable Explanations

Every flagged anomaly gets a plain-English reason, e.g.:
> *"Kieni FY2023/24: Unusually high allocation: KSh 842.5M; Multiple misappropriation findings: 3"*

---

## 📊 Data Sources Used

| Collection | Purpose |
|------------|---------|
| `constituencies` | Names & slugs of the 6 constituencies |
| `allocations` | NG-CDF project allocations per constituency per year |
| `audit_findings` | MP-level audit findings (misappropriation, correct appropriation) |
| `county_leaders` | Governor profile |
| `county_finances` | County revenue by source per year (equitable share, OSR, grants) |
| `county_audit_findings` | County-level audit findings |
| `department_absorption` | Department budget absorption rates per year |

---

## 🚀 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/anomalies/gnn/train` | Train the model from scratch on current database |
| `GET` | `/api/anomalies/gnn/detect` | Run anomaly detection (auto-trains if needed) |
| `GET` | `/api/anomalies/gnn/status` | Check if model is trained, see training metrics |

### Example Usage

```bash
# Train (takes 30-60 seconds on CPU)
curl -X POST http://localhost:5000/api/anomalies/gnn/train

# Detect anomalies
curl http://localhost:5000/api/anomalies/gnn/detect

# Check status
curl http://localhost:5000/api/anomalies/gnn/status
```

---

## 📈 Interpreting Results

### Output Fields (per anomaly)

| Field | Meaning |
|-------|---------|
| `anomaly_score` | 0–1 combined score (higher = more anomalous) |
| `anomaly_rank` | 1 = most anomalous |
| `node_type` | `"constituency_year"` or `"governor_year"` |
| `explanation` | Plain-English reason for flagging |
| `features.financial` | Key money amounts (allocations/revenue) |
| `features.audit` | Findings counts & flagged amounts |
| `metadata` | Full context (entity name, fiscal year, etc.) |

### Summary Statistics

The response also includes:
- `mean_anomaly_score` / `std_anomaly_score` — distribution of all nodes
- `anomaly_rate` — fraction of nodes flagged (target ~10%)
- `model_info` — architecture hyperparameters for reproducibility

---

## ⚙️ Configuration (in `gnn_anomaly_detector.py`)

```python
GVAEAnomalyDetector(
    input_dim=16,        # Feature vector size (auto-padded)
    hidden_dim=32,       # GCN hidden layer size
    embedding_dim=16,    # Latent embedding size
    learning_rate=0.01,  # Adam optimizer LR
    epochs=200,          # Training iterations
)
```

**Key tunables:**
- `epochs`: More = better convergence, slower training
- `embedding_dim`: Higher = more capacity, needs more data
- `contamination=0.1` in IsolationForest: Expected anomaly fraction

---

## 💾 Model Persistence

- Trained model auto-saves to `ml_models/saved/gnn_anomaly_model.pt`
- Includes: weights, scaler statistics, node mappings, training history
- Loads automatically on server restart via `get_gnn_detector()`

---

## ⚠️ Limitations & Caveats

| Limitation | Mitigation |
|------------|------------|
| **Small graph** (only 6 constituencies × ~3 years = ~18 constituency nodes + ~3 governor nodes) | Results are indicative, not definitive. Treat as "leads for investigation" |
| **No vendor/project-level data** | Add project/vendor nodes for finer granularity |
| **Static graph per fiscal year** | Temporal edges only link consecutive years |
| **Features are aggregated** | Drill-down requires raw transaction data |
| **Unsupervised** — no labeled anomalies to validate against | Combine with domain-expert rules (Benford's law, budget variance thresholds) |

---

## 🔬 For Production Use, Consider

1. **More data granularity**: Project-level, vendor-level, monthly cashflows
2. **Hyperparameter tuning**: Grid search on `hidden_dim`, `epochs`, `learning_rate`
3. **Cross-validation**: Temporal splits (train on 2022–23, test on 2024)
4. **Ensemble with rule-based detectors**: Benford's law on leading digits, budget variance > 2σ, duplicate vendor payments
5. **Explainability**: SHAP values on the Isolation Forest, attention weights on GCN
6. **Monitoring**: Track `val_auc` over time; retrain when it drops > 5%

---

## 📚 Technical References

- **GVAE**: Kipf & Welling, *Variational Graph Auto-Encoders* (NIPS 2016)
- **GCN**: Kipf & Welling, *Semi-Supervised Classification with Graph Convolutional Networks* (ICLR 2017)
- **Isolation Forest**: Liu et al., *Isolation Forest* (ICDM 2008)
- **PyTorch Geometric**: Fey & Lenssen, *Fast Graph Representation Learning* (2019)

---

## 🛠️ Dependencies

```txt
torch
torch-geometric
scikit-learn
numpy
pymongo  # for database access
```

Install with: `pip install torch torch-geometric scikit-learn numpy pymongo`

> **Note**: `torch-geometric` requires matching PyTorch version. See [PyG install guide](https://pytorch-geometric.readthedocs.io/en/latest/install/installation.html).