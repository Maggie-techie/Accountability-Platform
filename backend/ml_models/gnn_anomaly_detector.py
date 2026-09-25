"""
GNN-Based Anomaly Detection Model for Public Funds Accountability
Implements a Graph Variational Autoencoder (GVAE) for detecting anomalous
expenditure patterns, financial inconsistencies, and suspicious governance relationships.
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as torch_nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv, VGAE, InnerProductDecoder
from torch_geometric.data import Data
from torch_geometric.utils import train_test_split_edges
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score
import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VariationalGCNEncoder(torch_nn.Module):
    """
    Variational Graph Convolutional Network Encoder for VGAE
    """
    def __init__(self, in_channels: int, out_channels: int):
        super(VariationalGCNEncoder, self).__init__()
        self.conv1 = GCNConv(in_channels, 2 * out_channels)
        self.conv_mu = GCNConv(2 * out_channels, out_channels)
        self.conv_logstd = GCNConv(2 * out_channels, out_channels)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # First GCN layer
        x = F.relu(self.conv1(x, edge_index))
        x = F.dropout(x, training=self.training)

        # Return mean and log standard deviation
        return self.conv_mu(x, edge_index), self.conv_logstd(x, edge_index)

class GVAEAnomalyDetector:
    """
    Graph Variational AutoEncoder for anomaly detection in public funds data
    """

    def __init__(self,
                 input_dim: int = 16,
                 hidden_dim: int = 32,
                 embedding_dim: int = 16,
                 learning_rate: float = 0.01,
                 epochs: int = 200):
        """
        Initialize the GNN anomaly detector

        Args:
            input_dim: Number of input features per node
            hidden_dim: Dimension of hidden layers
            embedding_dim: Dimension of node embeddings
            learning_rate: Learning rate for optimizer
            epochs: Number of training epochs
        """
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.embedding_dim = embedding_dim
        self.learning_rate = learning_rate
        self.epochs = epochs

        # Initialize model components
        self.encoder = VariationalGCNEncoder(input_dim, embedding_dim)
        self.decoder = InnerProductDecoder()
        self.model = VGAE(self.encoder, self.decoder)

        # Initialize optimizer
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)

        # Initialize scalers for feature normalization
        self.feature_scaler = StandardScaler()

        # Track training history
        self.train_losses = []
        self.is_trained = False

        # Node and edge mappings for interpretation
        self.node_mapping = {}  # Maps node_id -> (constituency, year, type)
        self.reverse_mapping = {}  # Maps (constituency, year, type) -> node_id

    def extract_features_from_db(self, db_connection) -> Tuple[np.ndarray, List[Dict]]:
        """
        Extract features from MongoDB collections for graph construction

        Returns:
            features: Normalized feature matrix (n_nodes x input_dim)
            node_info: List of dictionaries containing node metadata
        """
        logger.info("Extracting features from database...")

        # Get database connection
        db = db_connection

        # Define constituencies in Nyeri County (hardcoded for now, could be fetched)
        constituencies = [
            {"name": "Tetu", "slug": "tetu"},
            {"name": "Kieni", "slug": "kieni"},
            {"name": "Mathira", "slug": "mathira"},
            {"name": "Othaya", "slug": "othaya"},
            {"name": "Mukurwe-ini", "slug": "mukurweini"},
            {"name": "Nyeri Town", "slug": "nyeri_town"}
        ]

        # Define fiscal years available in data
        fiscal_years = ["2022/23", "2023/24", "2024/25"]  # Could be fetched dynamically

        # Define major departments (could be fetched from department_absorption)
        departments = ["Health", "Water", "Roads", "Agriculture", "Education"]

        node_features = []
        node_info = []
        node_id = 0

        # Process Constituency-Year nodes
        for constituency in constituencies:
            for year in fiscal_years:
                # Extract financial features
                allocations = list(db.allocations.find({
                    "constituency_slug": constituency["slug"],
                    "fy_key": year.replace("/", "_")  # Convert to FY2022_23 format
                }))

                total_allocation = sum(alloc.get("amount_kshm", 0) for alloc in allocations)
                avg_allocation = total_allocation / len(allocations) if allocations else 0

                # Extract audit features
                audit_findings = list(db.audit_findings.find({
                    "constituency": constituency["name"],
                    "fy_reviewed": year
                }))

                num_findings = len(audit_findings)
                misappropriation_count = sum(1 for f in audit_findings
                                           if f.get("finding_type") == "misappropriation")
                total_flagged = sum(f.get("amount_at_risk", 0)
                                  for f in audit_findings if f.get("amount_at_risk"))

                # Calculate additional features
                allocation_growth = 0  # Would need previous year data
                audit_severity_score = 0  # Would need severity weighting

                # Construct feature vector for constituency-year node
                features = [
                    # Financial features (normalized)
                    total_allocation / 1000.0,  # Scale to billions
                    avg_allocation / 100.0,     # Scale to hundreds of millions
                    len(allocations),           # Number of allocation records

                    # Audit features
                    num_findings / 10.0,        # Normalize by expected max
                    misappropriation_count / 5.0, # Normalize
                    total_flagged / 100.0,      # Scale flagged amounts

                    # Temporal features (would be enhanced with historical data)
                    hash(year) % 100 / 100.0,   # Pseudo-temporal feature
                    len(fiscal_years) - fiscal_years.index(year) - 1,  # Years from most recent

                    # Categorical features (one-hot encoded or embedded)
                    1.0 if constituency["slug"] in ["tetu", "kieni"] else 0.0,  # Region feature
                    1.0 if "urban" in constituency["slug"].lower() else 0.0,   # Urban/rural

                    # Additional engineered features
                    total_allocation / (num_findings + 1),  # Allocation per finding
                    np.log1p(total_allocation),            # Log-transformed allocation
                    num_findings / (len(allocations) + 1),  # Findings per allocation
                ]

                # Ensure we have exactly input_dim features
                if len(features) < self.input_dim:
                    features.extend([0.0] * (self.input_dim - len(features)))
                elif len(features) > self.input_dim:
                    features = features[:self.input_dim]

                node_features.append(features)
                node_info.append({
                    "node_id": node_id,
                    "type": "constituency_year",
                    "constituency": constituency["name"],
                    "constituency_slug": constituency["slug"],
                    "fiscal_year": year,
                    "total_allocation": total_allocation,
                    "num_audit_findings": num_findings,
                    "misappropriation_count": misappropriation_count
                })

                # Update mappings
                self.node_mapping[node_id] = ("constituency_year", constituency["name"], year)
                self.reverse_mapping[("constituency_year", constituency["name"], year)] = node_id
                node_id += 1

        # Process Governor-Year nodes
        governor_profile = db.county_leaders.find_one()
        if governor_profile:
            for year in fiscal_years:
                # Extract financial data for the year
                finances = list(db.county_finances.find({
                    "financial_year": year
                }))

                total_revenue = sum(fin.get("amount_kshb", 0) for fin in finances)
                num_revenue_sources = len(finances)

                # Extract audit data
                gov_audit_findings = list(db.county_audit.find({
                    "financial_year": year
                }))

                num_gov_findings = len(gov_audit_findings)
                gov_misappropriation = sum(f.get("amount_flagged_kshm", 0)
                                         for f in gov_audit_findings
                                         if f.get("finding_type") == "misappropriation")

                # Extract department performance
                dept_absorption = list(db.department_absorption.find({
                    "financial_year": year
                }))

                avg_absorption = np.mean([d.get("absorption_rate", 0)
                                        for d in dept_absorption]) if dept_absorption else 0
                num_departments = len(dept_absorption)

                # Construct feature vector for governor-year node
                features = [
                    # Financial features
                    total_revenue / 10.0,           # Scale to billions
                    num_revenue_sources / 5.0,      # Normalize
                    total_revenue / (num_revenue_sources + 1),  # Revenue per source

                    # Audit features
                    num_gov_findings / 10.0,        # Normalize
                    gov_misappropriation / 100.0,   # Scale
                    gov_misappropriation / (num_gov_findings + 1),  # Misappropriation per finding

                    # Performance features
                    avg_absorption,                 # Already percentage
                    num_departments / 10.0,         # Normalize
                    avg_absorption * num_departments,  # Combined performance

                    # Temporal features
                    hash(year) % 100 / 100.0,       # Pseudo-temporal
                    len(fiscal_years) - fiscal_years.index(year) - 1,

                    # Categorical features
                    1.0,  # Governor node indicator
                    0.0,  # Placeholder

                    # Additional features
                    total_revenue / (num_gov_findings + 1),  # Revenue per audit finding
                    np.log1p(total_revenue),                # Log-transformed revenue
                ]

                # Ensure correct dimension
                if len(features) < self.input_dim:
                    features.extend([0.0] * (self.input_dim - len(features)))
                elif len(features) > self.input_dim:
                    features = features[:self.input_dim]

                node_features.append(features)
                node_info.append({
                    "node_id": node_id,
                    "type": "governor_year",
                    "governor_name": governor_profile.get("name", ""),
                    "fiscal_year": year,
                    "total_revenue": total_revenue,
                    "num_audit_findings": num_gov_findings,
                    "misappropriation_amount": gov_misappropriation
                })

                self.node_mapping[node_id] = ("governor_year", governor_profile.get("name", ""), year)
                self.reverse_mapping[("governor_year", governor_profile.get("name", ""), year)] = node_id
                node_id += 1

        # Convert to numpy array and normalize
        features_array = np.array(node_features, dtype=np.float32)
        normalized_features = self.feature_scaler.fit_transform(features_array)

        logger.info(f"Extracted features for {len(node_info)} nodes")
        return normalized_features, node_info

    def construct_graph(self, features: np.ndarray, node_info: List[Dict]) -> Data:
        """
        Construct a PyTorch Geometric graph from node features and information

        Args:
            features: Normalized feature matrix (n_nodes x input_dim)
            node_info: List of node metadata dictionaries

        Returns:
            PyTorch Geometric Data object
        """
        logger.info("Constructing graph...")

        n_nodes = len(node_info)

        # Convert features to tensor
        x = torch.tensor(features, dtype=torch.float)

        # Initialize edge list
        edge_list = []

        # Create temporal edges: same constituency/department across consecutive years
        for i, node_info_i in enumerate(node_info):
            for j, node_info_j in enumerate(node_info):
                if i >= j:  # Avoid duplicate edges and self-loops
                    continue

                # Temporal edges: same entity, consecutive years
                if (node_info_i["type"] == node_info_j["type"] and
                    self._are_consecutive_years(node_info_i, node_info_j)):
                    edge_list.extend([[i, j], [j, i]])  # Undirected graph

                # Similarity edges: similar entities in same year
                elif (node_info_i["fiscal_year"] == node_info_j["fiscal_year"] and
                      node_info_i["type"] == node_info_j["type"] and
                      self._are_similar_entities(node_info_i, node_info_j)):
                    edge_list.extend([[i, j], [j, i]])

                # Governance edges: governor to constituencies in same year
                elif ((node_info_i["type"] == "governor_year" and
                       node_info_j["type"] == "constituency_year") or
                      (node_info_i["type"] == "constituency_year" and
                       node_info_j["type"] == "governor_year")):
                    if self._is_same_year(node_info_i, node_info_j):
                        edge_list.extend([[i, j], [j, i]])

        # Convert edge list to tensor
        if edge_list:
            edge_index = torch.tensor(edge_list, dtype=torch.long).t().contiguous()
        else:
            # Create a minimal graph if no edges found
            edge_index = torch.tensor([[0, 1], [1, 0]], dtype=torch.long).t().contiguous()

        # Create PyTorch Geometric Data object
        data = Data(x=x, edge_index=edge_index)

        logger.info(f"Constructed graph with {n_nodes} nodes and {edge_index.shape[1]} edges")
        return data

    def _are_consecutive_years(self, node_info_i: Dict, node_info_j: Dict) -> bool:
        """Check if two nodes represent consecutive years"""
        try:
            year_i = self._parse_fiscal_year(node_info_i["fiscal_year"])
            year_j = self._parse_fiscal_year(node_info_j["fiscal_year"])
            return abs(year_i - year_j) == 1
        except:
            return False

    def _parse_fiscal_year(self, year_str: str) -> int:
        """Convert fiscal year string to integer for comparison"""
        # Extract start year from FY2022/23 format
        if "/" in year_str:
            return int(year_str.split("/")[0][2:])  # Extract 2022 from FY2022/23
        elif "_" in year_str:
            return int(year_str.split("_")[0][2:])  # Extract 2022 from FY2022_23
        else:
            return int(year_str[-2:])  # Fallback

    def _are_similar_entities(self, node_info_i: Dict, node_info_j: Dict) -> bool:
        """Check if two nodes represent similar entities (for peer comparison)"""
        # For constituencies: same region type or similar characteristics
        if node_info_i["type"] == "constituency_year" and node_info_j["type"] == "constituency_year":
            # Simple similarity: same urban/rural classification
            urban_i = "urban" in node_info_i.get("constituency_slug", "").lower()
            urban_j = "urban" in node_info_j.get("constituency_slug", "").lower()
            return urban_i == urban_j

        # For governor years: always similar (only one governor)
        if node_info_i["type"] == "governor_year" and node_info_j["type"] == "governor_year":
            return True

        return False

    def _is_same_year(self, node_info_i: Dict, node_info_j: Dict) -> bool:
        """Check if two nodes are from the same fiscal year"""
        return node_info_i.get("fiscal_year") == node_info_j.get("fiscal_year")

    def train(self, db_connection) -> Dict[str, Any]:
        """
        Train the GNN anomaly detection model

        Args:
            db_connection: MongoDB database connection

        Returns:
            Training results dictionary
        """
        logger.info("Starting GNN model training...")

        # Extract features and construct graph
        features, node_info = self.extract_features_from_db(db_connection)
        data = self.construct_graph(features, node_info)

        # Move to appropriate device
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = self.model.to(device)
        data = data.to(device)

        # Set model to training mode
        self.model.train()

        # Split edges for training/testing (we'll use link prediction as auxiliary task)
        data = train_test_split_edges(data)

        # Training loop
        self.train_losses = []
        for epoch in range(self.epochs):
            self.optimizer.zero_grad()

            # Get latent node embeddings
            z = self.model.encode(data.x, data.train_pos_edge_index)

            # Compute loss
            loss = self.model.recon_loss(z, data.pos_train_edge_index)

            # Add KL divergence loss for VGAE
            loss = loss + (1 / data.num_nodes) * self.model.kl_loss()

            loss.backward()
            self.optimizer.step()

            self.train_losses.append(loss.item())

            if epoch % 20 == 0:
                logger.info(f'Epoch: {epoch:03d}, Loss: {loss:.4f}')

        self.is_trained = True
        logger.info("Training completed!")

        # Return training results
        return {
            "status": "success",
            "epochs": self.epochs,
            "final_loss": self.train_losses[-1] if self.train_losses else 0,
            "num_nodes": data.num_nodes,
            "num_edges": data.edge_index.shape[1] if hasattr(data, 'edge_index') else 0,
            "training_losses": self.train_losses[-10:]  # Last 10 losses
        }

    def detect_anomalies(self, db_connection) -> Dict[str, Any]:
        """
        Detect anomalies in the public funds data using the trained GNN model

        Args:
            db_connection: MongoDB database connection

        Returns:
            Anomaly detection results including anomaly scores and explanations
        """
        if not self.is_trained:
            # Try to train if not already trained
            logger.info("Model not trained, initiating training...")
            train_result = self.train(db_connection)
            if train_result["status"] != "success":
                return train_result

        logger.info("Detecting anomalies...")

        # Extract features and construct graph (same as training)
        features, node_info = self.extract_features_from_db(db_connection)
        data = self.construct_graph(features, node_info)

        # Move to device
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = self.model.to(device)
        data = data.to(device)

        # Set model to evaluation mode
        self.model.eval()

        with torch.no_grad():
            # Get node embeddings
            z = self.model.encode(data.x, data.edge_index)

            # Compute reconstruction error for each node
            # For VGAE, we can use the likelihood of the observed adjacency matrix
            adj_pred = self.model.decoder(z)

            # Convert to numpy for easier handling
            z_np = z.cpu().numpy()
            adj_pred_np = adj_pred.cpu().numpy()

            # Calculate node-level anomaly scores
            # Approach 1: Reconstruction error of node features
            # Approach 2: Embedding-based isolation (using distance to neighbors)
            # Approach 3: Graph structure anomaly (unexpected connections)

            # For simplicity, we'll use a combination of:
            # 1. Node feature reconstruction error
            # 2. Social anomaly score (how well connected a node is to similar nodes)

            # Feature reconstruction error (would need decoder for features, not just edges)
            # Instead, we'll use embedding-based approaches

            # Method 1: Distance to k-nearest neighbors in embedding space
            from sklearn.metrics import pairwise_distances
            embedding_distances = pairwise_distances(z_np)
            knn_distance = np.mean(np.sort(embedding_distances, axis=1)[:, 1:6], axis=1)  # Avg distance to 5-NN

            # Method 2: Isolation Forest on embeddings
            from sklearn.ensemble import IsolationForest
            iso_forest = IsolationForest(contamination=0.1, random_state=42)
            anomaly_scores_iso = iso_forest.fit_predict(z_np)
            anomaly_scores_iso = (-anomaly_scores_iso + 1) / 2  # Convert to 0-1 scale (1 = anomaly)

            # Method 3: Reconstruction-based (using edge prediction error)
            # For each node, compute how well its connections are predicted
            node_anomaly_scores = np.zeros(data.num_nodes)
            for i in range(data.num_nodes):
                # Get actual neighbors
                if data.edge_index.shape[1] > 0:
                    mask = (data.edge_index[0] == i) | (data.edge_index[1] == i)
                    if np.any(mask):
                        actual_neighbors = set()
                        edge_indices = data.edge_index[:, mask]
                        for k in range(edge_indices.shape[1]):
                            src, dst = edge_indices[0, k].item(), edge_indices[1, k].item()
                            actual_neighbors.add(dst if src == i else src)

                        # Get predicted connections
                        if i < adj_pred_np.shape[0]:
                            pred_connections = adj_pred_np[i]
                            # Score based on difference between actual and predicted connectivity
                            actual_connectivity = np.zeros(len(pred_connections))
                            for neighbor in actual_neighbors:
                                if neighbor < len(actual_connectivity):
                                    actual_connectivity[neighbor] = 1

                            recon_error = np.mean((actual_connectivity - pred_connections) ** 2)
                            node_anomaly_scores[i] = recon_error

            # Combine anomaly scores (ensemble approach)
            # Normalize each score to 0-1 range
            def normalize_score(score_array):
                if np.max(score_array) == np.min(score_array):
                    return np.zeros_like(score_array)
                return (score_array - np.min(score_array)) / (np.max(score_array) - np.min(score_array))

            knn_score = normalize_score(knn_distance)
            iso_score = normalize_score(anomaly_scores_iso)
            recon_score = normalize_score(node_anomaly_scores)

            # Weighted ensemble (can be tuned)
            final_anomaly_scores = (
                0.4 * knn_score +
                0.3 * iso_score +
                0.3 * recon_score
            )

            # Identify top anomalies
            n_anomalies = max(1, int(len(final_anomaly_scores) * 0.1))  # Top 10% as anomalies
            anomaly_indices = np.argsort(final_anomaly_scores)[-n_anomalies:][::-1]  # Descending order

            # Prepare results
            anomalies = []
            for idx in anomaly_indices:
                if idx < len(node_info):
                    info = node_info[idx]
                    anomaly_record = {
                        "node_id": int(idx),
                        "anomaly_score": float(final_anomaly_scores[idx]),
                        "anomaly_rank": int(np.where(anomaly_indices == idx)[0][0] + 1),
                        "node_type": info.get("type", "unknown"),
                        "explanation": self._generate_anomaly_explanation(info, final_anomaly_scores[idx], z_np[idx]),
                        "features": {
                            "financial": {
                                "total_allocation": info.get("total_allocation", 0),
                                "total_revenue": info.get("total_revenue", 0),
                            },
                            "audit": {
                                "num_findings": info.get("num_audit_findings", 0),
                                "misappropriation_count": info.get("misappropriation_count", 0),
                                "misappropriation_amount": info.get("misappropriation_amount", 0),
                            }
                        },
                        "metadata": info
                    }
                    anomalies.append(anomaly_record)

            # Overall statistics
            results = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "total_nodes_analyzed": len(node_info),
                "num_anomalies_detected": len(anomalies),
                "anomaly_rate": len(anomalies) / len(node_info) if len(node_info) > 0 else 0,
                "anomalies": anomalies,
                "model_info": {
                    "input_dim": self.input_dim,
                    "hidden_dim": self.hidden_dim,
                    "embedding_dim": self.embedding_dim,
                    "epochs_trained": self.epochs,
                    "final_training_loss": self.train_losses[-1] if self.train_losses else 0
                },
                "summary_statistics": {
                    "mean_anomaly_score": float(np.mean(final_anomaly_scores)),
                    "std_anomaly_score": float(np.std(final_anomaly_scores)),
                    "max_anomaly_score": float(np.max(final_anomaly_scores)),
                    "min_anomaly_score": float(np.min(final_anomaly_scores))
                }
            }

            logger.info(f"Anomaly detection completed. Found {len(anomalies)} anomalies out of {len(node_info)} nodes.")
            return results

    def _generate_anomaly_explanation(self, node_info: Dict, anomaly_score: float,
                                    embedding: np.ndarray) -> str:
        """
        Generate human-readable explanation for why a node was flagged as anomalous
        """
        explanations = []

        node_type = node_info.get("type", "unknown")

        if node_type == "constituency_year":
            constituency = node_info.get("constituency", "Unknown")
            year = node_info.get("fiscal_year", "Unknown")

            # Check financial anomalies
            total_alloc = node_info.get("total_allocation", 0)
            if total_alloc > 500_000_000:  # Over 500M KSH
                explanations.append(f"Unusually high total allocation: {total_alloc:,.0f} KSH")

            # Check audit anomalies
            num_findings = node_info.get("num_audit_findings", 0)
            misap_count = node_info.get("misappropriation_count", 0)
            if num_findings > 5:
                explanations.append(f"High number of audit findings: {num_findings}")
            if misap_count > 2:
                explanations.append(f"Multiple misappropriation findings: {misap_count}")

            misap_amount = node_info.get("misappropriation_amount", 0)
            if misap_amount > 50_000_000:  # Over 50M KSH
                explanations.append(f"Large amount flagged in misappropriations: {misap_amount:,.0f} KSH")

            # Check for unusual patterns
            if num_findings > 0 and total_alloc < 100_000_000:  # Low allocation but many findings
                explanations.append("Disproportionate audit findings relative to allocation size")

        elif node_type == "governor_year":
            governor = node_info.get("governor_name", "Unknown")
            year = node_info.get("fiscal_year", "Unknown")

            total_rev = node_info.get("total_revenue", 0)
            if total_rev > 10_000_000_000:  # Over 10B KSH
                explanations.append(f"Unusually high total revenue: {total_rev:,.0f} KSH")

            num_findings = node_info.get("num_audit_findings", 0)
            if num_findings > 10:
                explanations.append(f"High number of county-wide audit findings: {num_findings}")

            misap_amount = node_info.get("misappropriation_amount", 0)
            if misap_amount > 100_000_000:  # Over 100M KSH
                explanations.append(f"Large county-wide misappropriation amount: {misap_amount:,.0f} KSH")

        # Default explanation if no specific triggers
        if not explanations:
            explanations.append(f"Anomalous embedding pattern detected (score: {anomaly_score:.3f})")

        return "; ".join(explanations)

    def save_model(self, filepath: str):
        """Save the trained model to disk"""
        if self.is_trained:
            torch.save({
                'model_state_dict': self.model.state_dict(),
                'optimizer_state_dict': self.optimizer.state_dict(),
                'input_dim': self.input_dim,
                'hidden_dim': self.hidden_dim,
                'embedding_dim': self.embedding_dim,
                'feature_scaler': self.feature_scaler,
                'node_mapping': self.node_mapping,
                'train_losses': self.train_losses
            }, filepath)
            logger.info(f"Model saved to {filepath}")
        else:
            logger.warning("Cannot save model: model not trained yet")

    def load_model(self, filepath: str):
        """Load a trained model from disk"""
        if os.path.exists(filepath):
            checkpoint = torch.load(filepath)
            self.input_dim = checkpoint['input_dim']
            self.hidden_dim = checkpoint['hidden_dim']
            self.embedding_dim = checkpoint['embedding_dim']

            # Reinitialize model
            self.encoder = VariationalGCNEncoder(self.input_dim, self.embedding_dim)
            self.decoder = InnerProductDecoder()
            self.model = VGAE(self.encoder, self.decoder)

            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            self.feature_scaler = checkpoint['feature_scaler']
            self.node_mapping = checkpoint['node_mapping']
            self.train_losses = checkpoint['train_losses']
            self.is_trained = True

            logger.info(f"Model loaded from {filepath}")
        else:
            logger.error(f"Model file not found: {filepath}")

# Global model instance for reuse
gnn_detector = None

def get_gnn_detector() -> GVAEAnomalyDetector:
    """Get or create the global GNN detector instance"""
    global gnn_detector
    if gnn_detector is None:
        gnn_detector = GVAEAnomalyDetector()
    return gnn_detector