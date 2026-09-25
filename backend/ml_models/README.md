# GNN-Based Anomaly Detection for Public Funds Accountability

This module implements a Graph Variational Autoencoder (GVAE) for detecting anomalous patterns in public funds expenditure, financial inconsistencies, and suspicious governance relationships.

## Overview

The system constructs a temporal graph where nodes represent (entity, fiscal_year) pairs and edges represent various relationships:
- Temporal edges: same entity across consecutive years
- Similarity edges: similar entities in the same fiscal year
- Governance edges: governor to constituencies (oversight relationship)

## Features Used

### Constituency-Year Nodes:
- Financial: Total allocation, average allocation, number of allocations
- Audit: Number of findings, misappropriation count, total flagged amount
- Temporal: Year-over-year changes, positional encoding
- Categorical: Urban/rural classification, region features

### Governor-Year Nodes:
- Financial: Total revenue, number of revenue sources
- Audit: Audit findings count, misappropriation amounts
- Performance: Department absorption rates, number of departments
- Temporal: Year positioning, pseudo-temporal features

## Model Architecture

The implementation uses a Graph Variational AutoEncoder (GVAE):
- Encoder: 2-layer GCN with variational outputs (mean and log-std)
- Decoder: Inner product decoder for link prediction
- Training: Combines reconstruction loss and KL divergence
- Anomaly Detection: Ensemble approach using:
  1. K-Nearest Neighbor distance in embedding space
  2. Isolation Forest on embeddings
  3. Edge reconstruction error

## API Endpoints

Once integrated, the following endpoints are available:

### POST /api/anomalies/gnn/train
Train the GNN anomaly detection model
- Returns: Training status and metrics

### GET /api/anomalies/gnn/detect
Detect anomalies using the trained model
- Returns: Anomaly scores, explanations, and metadata for anomalous nodes

### GET /api/anomalies/gnn/status
Get the current status of the GNN model
- Returns: Training status, model parameters, and progress

## Usage Example

```bash
# Train the model (may take several minutes)
curl -X POST http://localhost:5000/api/anomalies/gnn/train

# Detect anomalies
curl http://localhost:5000/api/anomalies/gnn/detect

# Check model status
curl http://localhost:5000/api/anomalies/gnn/status
```

## Dependencies

Add the following to your requirements.txt:
- torch
- torch-geometric
- scikit-learn
- numpy

## Notes

1. The model requires sufficient data to be effective. With only 6 constituencies, consider:
   - Aggregating data at a finer granularity (e.g., project level)
   - Including more historical years
   - Adding additional entity types (projects, vendors, etc.)

2. For production use, consider:
   - Hyperparameter tuning
   - Cross-validation
   - More sophisticated anomaly detection techniques
   - Integration with business rules and domain knowledge

3. The current implementation uses a simplified feature set. In practice, you would want to:
   - Include more detailed financial breakdowns
   - Add project-level data
   - Incorporate external data sources (economic indicators, demographic data)
   - Use more sophisticated temporal encoding