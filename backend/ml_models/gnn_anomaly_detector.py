"""
GNN-Based Anomaly Detection Model for Public Funds Accountability

Graph Variational Autoencoder (GVAE) that embeds constituency-year and
governor-year nodes, then flags nodes whose embeddings / connectivity look
unusual compared with their peers.
"""

import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Tuple

import numpy as np
import torch
import torch.nn as torch_nn
import torch.nn.functional as F
from sklearn.ensemble import IsolationForest
from sklearn.metrics import pairwise_distances
from sklearn.preprocessing import StandardScaler
from torch_geometric.data import Data
from torch_geometric.nn import GCNConv, InnerProductDecoder, VGAE
from torch_geometric.transforms import RandomLinkSplit

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved", "gnn_anomaly_model.pt")

# Fallbacks used only if the database has nothing to derive these from
DEFAULT_CONSTITUENCIES = [
    {"name": "Tetu", "slug": "tetu"},
    {"name": "Kieni", "slug": "kieni"},
    {"name": "Mathira", "slug": "mathira"},
    {"name": "Othaya", "slug": "othaya"},
    {"name": "Mukurweini", "slug": "mukurweini"},
    {"name": "Nyeri Town", "slug": "nyeri_town"},
]
DEFAULT_START_YEARS = [2022, 2023, 2024]
URBAN_SLUGS = {"nyeri_town"}
NORTHERN_SLUGS = {"tetu", "kieni"}

# Matches "FY2022_23", "FY2022/23", "2022/23", "2022-23" ...
FY_RE = re.compile(r"(20\d{2})\s*[/_\-]\s*(\d{2})")
# Fields that may carry a financial year, depending on the collection
FY_KEYS = ("fy_key", "fy_display", "financial_year", "fy_reviewed", "fy", "year")
AMOUNT_RE = re.compile(r"([\d,]*\.?\d+)\s*([kKmMbB])?")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def fy_start_years(value) -> set:
    """
    Start years covered by a financial-year string. A range such as
    "FY2022/23 - FY2024/25" covers 2022, 2023 and 2024. "Legacy" covers none.
    """
    if value is None:
        return set()
    starts = [int(m.group(1)) for m in FY_RE.finditer(str(value))]
    if not starts:
        return set()
    return set(range(min(starts), max(starts) + 1))


def doc_in_year(doc: Dict, start_year: int) -> bool:
    return any(start_year in fy_start_years(doc.get(key)) for key in FY_KEYS)


def fy_label(start_year: int) -> str:
    return f"{start_year}/{str(start_year + 1)[-2:]}"


def to_float(value) -> float:
    """
    Parse numbers or strings like "Ksh 2.1M" safely. Suffixes are converted to
    millions (k -> 0.001, m -> 1, b -> 1000); bare numbers are returned as-is.
    """
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    m = AMOUNT_RE.search(str(value))
    if not m:
        return 0.0
    number = float(m.group(1).replace(",", ""))
    multiplier = {"k": 0.001, "m": 1.0, "b": 1000.0}.get((m.group(2) or "").lower(), 1.0)
    return number * multiplier


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
class VariationalGCNEncoder(torch_nn.Module):
    def __init__(self, in_channels: int, hidden_channels: int, out_channels: int):
        super().__init__()
        self.conv1 = GCNConv(in_channels, hidden_channels)
        self.conv_mu = GCNConv(hidden_channels, out_channels)
        self.conv_logstd = GCNConv(hidden_channels, out_channels)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        x = F.relu(self.conv1(x, edge_index))
        x = F.dropout(x, training=self.training)
        return self.conv_mu(x, edge_index), self.conv_logstd(x, edge_index)


class GVAEAnomalyDetector:
    def __init__(
        self,
        input_dim: int = 16,
        hidden_dim: int = 32,
        embedding_dim: int = 16,
        learning_rate: float = 0.01,
        epochs: int = 200,
    ):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.embedding_dim = embedding_dim
        self.learning_rate = learning_rate
        self.epochs = epochs

        self.feature_scaler = StandardScaler()
        self.train_losses: List[float] = []
        self.is_trained = False

        # Metadata exposed through the status endpoint
        self.trained_at = None
        self.num_nodes = 0
        self.num_edges = 0
        self.val_auc = None
        self.training_history: List[Dict[str, Any]] = []

        # node_id -> (type, entity, fiscal_year) and the reverse
        self.node_mapping: Dict[int, Tuple[str, str, str]] = {}
        self.reverse_mapping: Dict[Tuple[str, str, str], int] = {}

        self._build_model()

    def _build_model(self):
        """(Re)create the network with fresh weights and a fresh optimizer."""
        self.encoder = VariationalGCNEncoder(self.input_dim, self.hidden_dim, self.embedding_dim)
        self.decoder = InnerProductDecoder()
        self.model = VGAE(self.encoder, self.decoder)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)

    # ------------------------------------------------------------------
    # Feature extraction
    # ------------------------------------------------------------------
    @staticmethod
    def _load_constituencies(db) -> List[Dict[str, str]]:
        try:
            docs = list(db.constituencies.find({}, {"_id": 0, "name": 1, "slug": 1}))
            docs = [d for d in docs if d.get("slug")]
            if docs:
                return [{"name": d.get("name") or d["slug"], "slug": d["slug"]} for d in docs]
        except Exception as e:
            logger.warning(f"Could not load constituencies, using defaults: {e}")
        return DEFAULT_CONSTITUENCIES

    @staticmethod
    def _load_fiscal_years(db) -> List[int]:
        years = set()
        try:
            for key in db.allocations.distinct("fy_key"):
                starts = fy_start_years(key)
                if starts:
                    years.add(min(starts))
        except Exception as e:
            logger.warning(f"Could not load fiscal years, using defaults: {e}")
        return sorted(years) or DEFAULT_START_YEARS

    def extract_features_from_db(self, db, fit_scaler: bool = True) -> Tuple[np.ndarray, List[Dict]]:
        """
        Build one feature vector per node.

        fit_scaler=True refits the StandardScaler (training). At detection time
        pass False so the same scaling learned during training is reused.
        """
        logger.info("Extracting features from database...")

        self.node_mapping, self.reverse_mapping = {}, {}

        constituencies = self._load_constituencies(db)
        start_years = self._load_fiscal_years(db)
        n_years = len(start_years)

        # Load each collection once and filter in Python (datasets are small)
        allocations = list(db.allocations.find({}, {"_id": 0}))
        mp_findings = list(db.audit_findings.find({}, {"_id": 0}))
        gov_profile = db.county_leaders.find_one()
        gov_finances = list(db.county_finances.find({}, {"_id": 0}))
        gov_findings = list(db.county_audit_findings.find({}, {"_id": 0}))
        dept_rows = list(db.department_absorption.find({}, {"_id": 0}))

        node_features: List[List[float]] = []
        node_info: List[Dict[str, Any]] = []

        def register(info: Dict[str, Any]):
            node_id = len(node_info)
            info["node_id"] = node_id
            node_info.append(info)
            key = (info["type"], info["entity"], info["fiscal_year"])
            self.node_mapping[node_id] = key
            self.reverse_mapping[key] = node_id

        def pad(features: List[float]) -> List[float]:
            if len(features) < self.input_dim:
                return features + [0.0] * (self.input_dim - len(features))
            return features[: self.input_dim]

        # ---- Constituency-year nodes ----
        for c in constituencies:
            slug = c["slug"]
            c_findings_all = [f for f in mp_findings if f.get("constituency_slug") == slug]
            all_misap = sum(1 for f in c_findings_all if f.get("finding_type") == "misappropriation")

            for idx, year in enumerate(start_years):
                c_allocs = [a for a in allocations if a.get("constituency_slug") == slug and doc_in_year(a, year)]
                total_allocation = sum(to_float(a.get("amount_kshm")) for a in c_allocs)  # KShM
                avg_allocation = total_allocation / len(c_allocs) if c_allocs else 0.0

                y_findings = [f for f in c_findings_all if doc_in_year(f, year)]
                num_findings = len(y_findings)
                misap_count = sum(1 for f in y_findings if f.get("finding_type") == "misappropriation")
                total_flagged = sum(to_float(f.get("amount_at_risk")) for f in y_findings)  # KShM

                is_urban = 1.0 if slug in URBAN_SLUGS else 0.0
                year_frac = idx / max(1, n_years - 1)

                features = [
                    total_allocation / 1000.0,
                    avg_allocation / 100.0,
                    float(len(c_allocs)),
                    num_findings / 10.0,
                    misap_count / 5.0,
                    total_flagged / 100.0,
                    year_frac,
                    float(n_years - idx - 1),  # years before the most recent
                    1.0 if slug in NORTHERN_SLUGS else 0.0,
                    is_urban,
                    total_allocation / (num_findings + 1),
                    float(np.log1p(total_allocation)),
                    num_findings / (len(c_allocs) + 1),
                    # Constituency-level totals: many findings carry no year
                    len(c_findings_all) / 10.0,
                    all_misap / 5.0,
                    0.0,  # governor flag
                ]
                node_features.append(pad(features))
                register({
                    "type": "constituency_year",
                    "entity": slug,
                    "constituency": c["name"],
                    "constituency_slug": slug,
                    "fiscal_year": fy_label(year),
                    "fy_start": year,
                    "is_urban": bool(is_urban),
                    "total_allocation_kshm": total_allocation,
                    "num_audit_findings": num_findings,
                    "misappropriation_count": misap_count,
                    "amount_flagged_kshm": total_flagged,
                })

        # ---- Governor-year nodes ----
        if gov_profile:
            gov_name = gov_profile.get("name") or gov_profile.get("governor") or "Governor"
            for idx, year in enumerate(start_years):
                finances = [f for f in gov_finances if doc_in_year(f, year)]
                total_revenue = sum(to_float(f.get("amount_kshb")) for f in finances)  # KShB
                num_sources = len(finances)

                y_findings = [f for f in gov_findings if doc_in_year(f, year)]
                num_gov_findings = len(y_findings)
                amount_flagged = sum(to_float(f.get("amount_flagged_kshm")) for f in y_findings)  # KShM

                depts = [d for d in dept_rows if doc_in_year(d, year)]
                rates = [to_float(d.get("absorption_rate")) for d in depts]
                avg_absorption = float(np.mean(rates)) if rates else 0.0
                num_departments = len(depts)

                year_frac = idx / max(1, n_years - 1)

                features = [
                    total_revenue / 10.0,
                    num_sources / 5.0,
                    total_revenue / (num_sources + 1),
                    num_gov_findings / 10.0,
                    amount_flagged / 100.0,
                    amount_flagged / (num_gov_findings + 1),
                    avg_absorption,
                    num_departments / 10.0,
                    avg_absorption * num_departments,
                    year_frac,
                    float(n_years - idx - 1),
                    0.0,  # region flag (n/a)
                    0.0,  # urban flag (n/a)
                    total_revenue / (num_gov_findings + 1),
                    float(np.log1p(total_revenue)),
                    1.0,  # governor flag
                ]
                node_features.append(pad(features))
                register({
                    "type": "governor_year",
                    "entity": "governor",
                    "governor_name": gov_name,
                    "fiscal_year": fy_label(year),
                    "fy_start": year,
                    "is_urban": False,
                    "total_revenue_kshb": total_revenue,
                    "num_audit_findings": num_gov_findings,
                    "amount_flagged_kshm": amount_flagged,
                })

        if not node_features:
            return np.zeros((0, self.input_dim), dtype=np.float32), []

        arr = np.array(node_features, dtype=np.float32)
        if fit_scaler or not hasattr(self.feature_scaler, "mean_"):
            normalized = self.feature_scaler.fit_transform(arr)
        else:
            normalized = self.feature_scaler.transform(arr)
        normalized = np.nan_to_num(normalized).astype(np.float32)

        logger.info(f"Extracted features for {len(node_info)} nodes")
        return normalized, node_info

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------
    def construct_graph(self, features: np.ndarray, node_info: List[Dict]) -> Data:
        logger.info("Constructing graph...")
        n_nodes = len(node_info)
        x = torch.tensor(features, dtype=torch.float)

        edges = set()
        for i in range(n_nodes):
            a = node_info[i]
            for j in range(i + 1, n_nodes):
                b = node_info[j]
                connect = False

                if a["type"] == b["type"]:
                    if a["entity"] == b["entity"] and abs(a["fy_start"] - b["fy_start"]) == 1:
                        # Temporal: the SAME entity in consecutive years
                        connect = True
                    elif (
                        a["type"] == "constituency_year"
                        and a["fy_start"] == b["fy_start"]
                        and a["is_urban"] == b["is_urban"]
                    ):
                        # Peers: comparable constituencies in the same year
                        connect = True
                elif a["fy_start"] == b["fy_start"]:
                    # Governance: governor <-> constituencies in the same year
                    connect = True

                if connect:
                    edges.add((i, j))
                    edges.add((j, i))

        if edges:
            edge_index = torch.tensor(sorted(edges), dtype=torch.long).t().contiguous()
        else:
            edge_index = torch.tensor([[0, 1], [1, 0]], dtype=torch.long)

        data = Data(x=x, edge_index=edge_index)
        logger.info(f"Constructed graph with {n_nodes} nodes and {edge_index.shape[1]} edges")
        return data

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------
    def train(self, db_connection) -> Dict[str, Any]:
        logger.info("Starting GNN model training...")

        features, node_info = self.extract_features_from_db(db_connection, fit_scaler=True)
        if len(node_info) < 3:
            return {"status": "error", "message": "Not enough data to build a graph (need at least 3 nodes)."}

        data = self.construct_graph(features, node_info)
        num_nodes = int(data.num_nodes)
        num_edges = int(data.edge_index.size(1))  # read BEFORE any edge splitting

        torch.manual_seed(42)
        np.random.seed(42)
        self._build_model()  # retraining starts from fresh weights

        # Hold out a slice of edges for a link-prediction sanity check.
        # (train_test_split_edges is deprecated and removes edge_index; use RandomLinkSplit.)
        val_data = None
        if num_edges // 2 >= 20:
            split = RandomLinkSplit(
                num_val=0.1,
                num_test=0.1,
                is_undirected=True,
                add_negative_train_samples=False,
                split_labels=True,
            )
            train_data, val_data, _ = split(data)
            message_edges = train_data.edge_index          # edges used for message passing
            train_pos_edges = train_data.pos_edge_label_index  # positives for the reconstruction loss
        else:
            message_edges = data.edge_index
            train_pos_edges = data.edge_index

        x = data.x
        self.model.train()
        self.train_losses = []
        for epoch in range(self.epochs):
            self.optimizer.zero_grad()
            z = self.model.encode(x, message_edges)
            loss = self.model.recon_loss(z, train_pos_edges)
            loss = loss + (1.0 / num_nodes) * self.model.kl_loss()
            loss.backward()
            self.optimizer.step()
            self.train_losses.append(float(loss.item()))

            if epoch % 20 == 0:
                logger.info(f"Epoch: {epoch:03d}, Loss: {loss.item():.4f}")

        val_auc = None
        if val_data is not None:
            try:
                self.model.eval()
                with torch.no_grad():
                    z = self.model.encode(x, message_edges)
                    auc, _ap = self.model.test(z, val_data.pos_edge_label_index, val_data.neg_edge_label_index)
                val_auc = float(auc)
            except Exception as e:
                logger.warning(f"Could not compute validation AUC: {e}")

        self.is_trained = True
        self.trained_at = datetime.now().isoformat(timespec="seconds")
        self.num_nodes = num_nodes
        self.num_edges = num_edges
        self.val_auc = val_auc
        self.training_history.append({
            "date": self.trained_at,
            "nodes": num_nodes,
            "edges": num_edges,
            "val_auc": val_auc,
            "final_loss": self.train_losses[-1],
            "status": "Completed",
        })
        self.training_history = self.training_history[-10:]

        try:
            self.save_model()
        except Exception as e:  # saving must never fail the training request
            logger.warning(f"Could not save model: {e}")

        logger.info("Training completed!")
        return {
            "status": "success",
            "epochs": self.epochs,
            "final_loss": self.train_losses[-1],
            "num_nodes": num_nodes,
            "num_edges": num_edges,
            "val_auc": val_auc,
            "trained_at": self.trained_at,
            "training_losses": self.train_losses[-10:],
        }

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------
    def detect_anomalies(self, db_connection) -> Dict[str, Any]:
        if not self.is_trained:
            logger.info("Model not trained, initiating training...")
            train_result = self.train(db_connection)
            if train_result["status"] != "success":
                return train_result

        logger.info("Detecting anomalies...")

        # Reuse the scaler fitted during training
        features, node_info = self.extract_features_from_db(db_connection, fit_scaler=False)
        n = len(node_info)
        if n < 3:
            return {"status": "error", "message": "Not enough data to run detection."}
        data = self.construct_graph(features, node_info)

        self.model.eval()
        with torch.no_grad():
            z = self.model.encode(data.x, data.edge_index)
            adj_pred = self.model.decoder.forward_all(z, sigmoid=True)  # dense n x n probabilities

        z_np = z.cpu().numpy()
        adj_np = adj_pred.cpu().numpy()

        # 1) Connectivity reconstruction error per node
        actual = np.zeros((n, n), dtype=np.float32)
        ei = data.edge_index.cpu().numpy()
        actual[ei[0], ei[1]] = 1.0
        recon_error = np.mean((actual - adj_np) ** 2, axis=1)

        # 2) Mean distance to the k nearest neighbours in embedding space
        k = min(5, n - 1)
        distances = pairwise_distances(z_np)
        knn_distance = np.mean(np.sort(distances, axis=1)[:, 1 : k + 1], axis=1)

        # 3) Isolation Forest (continuous score; higher = more anomalous)
        iso = IsolationForest(contamination=0.1, random_state=42).fit(z_np)
        iso_score = -iso.score_samples(z_np)

        def normalize(arr: np.ndarray) -> np.ndarray:
            span = np.max(arr) - np.min(arr)
            return np.zeros_like(arr) if span == 0 else (arr - np.min(arr)) / span

        final_scores = 0.4 * normalize(knn_distance) + 0.3 * normalize(iso_score) + 0.3 * normalize(recon_error)

        n_anomalies = max(1, int(n * 0.1))
        top = np.argsort(final_scores)[-n_anomalies:][::-1]

        anomalies = []
        for rank, idx in enumerate(top, start=1):
            info = node_info[int(idx)]
            anomalies.append({
                "node_id": int(idx),
                "anomaly_score": float(final_scores[idx]),
                "anomaly_rank": rank,
                "node_type": info.get("type", "unknown"),
                "explanation": self._generate_anomaly_explanation(info, float(final_scores[idx])),
                "features": {
                    "financial": {
                        "total_allocation_kshm": info.get("total_allocation_kshm", 0),
                        "total_revenue_kshb": info.get("total_revenue_kshb", 0),
                    },
                    "audit": {
                        "num_findings": info.get("num_audit_findings", 0),
                        "misappropriation_count": info.get("misappropriation_count", 0),
                        "amount_flagged_kshm": info.get("amount_flagged_kshm", 0),
                    },
                },
                "metadata": info,
            })

        logger.info(f"Anomaly detection completed. Found {len(anomalies)} anomalies out of {n} nodes.")
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "total_nodes_analyzed": n,
            "num_anomalies_detected": len(anomalies),
            "anomaly_rate": len(anomalies) / n,
            "anomalies": anomalies,
            "model_info": {
                "input_dim": self.input_dim,
                "hidden_dim": self.hidden_dim,
                "embedding_dim": self.embedding_dim,
                "epochs_trained": self.epochs,
                "final_training_loss": self.train_losses[-1] if self.train_losses else 0,
            },
            "summary_statistics": {
                "mean_anomaly_score": float(np.mean(final_scores)),
                "std_anomaly_score": float(np.std(final_scores)),
                "max_anomaly_score": float(np.max(final_scores)),
                "min_anomaly_score": float(np.min(final_scores)),
            },
        }

    def _generate_anomaly_explanation(self, info: Dict, anomaly_score: float) -> str:
        """Human-readable reasons. Amounts are stored in KShM (constituency/flags) and KShB (revenue)."""
        reasons = []
        node_type = info.get("type", "unknown")

        if node_type == "constituency_year":
            label = f"{info.get('constituency', 'Unknown')} {info.get('fiscal_year', '')}".strip()
            total_alloc = info.get("total_allocation_kshm", 0)
            findings = info.get("num_audit_findings", 0)
            misap = info.get("misappropriation_count", 0)
            flagged = info.get("amount_flagged_kshm", 0)

            if total_alloc > 500:
                reasons.append(f"Unusually high allocation: KSh {total_alloc:,.1f}M")
            if findings > 5:
                reasons.append(f"High number of audit findings: {findings}")
            if misap > 2:
                reasons.append(f"Multiple misappropriation findings: {misap}")
            if flagged > 50:
                reasons.append(f"Large amount at risk: KSh {flagged:,.1f}M")
            if findings > 0 and total_alloc < 100:
                reasons.append("Disproportionate audit findings relative to allocation size")
            prefix = label

        elif node_type == "governor_year":
            prefix = f"County {info.get('fiscal_year', '')}".strip()
            revenue = info.get("total_revenue_kshb", 0)
            findings = info.get("num_audit_findings", 0)
            flagged = info.get("amount_flagged_kshm", 0)

            if revenue > 10:
                reasons.append(f"Unusually high total revenue: KSh {revenue:,.1f}B")
            if findings > 10:
                reasons.append(f"High number of county audit findings: {findings}")
            if flagged > 100:
                reasons.append(f"Large amount flagged: KSh {flagged:,.1f}M")
        else:
            prefix = "Node"

        if not reasons:
            reasons.append(f"Unusual embedding pattern relative to peers (score {anomaly_score:.3f})")
        return f"{prefix}: " + "; ".join(reasons)

    # ------------------------------------------------------------------
    # Persistence (so a Flask restart doesn't wipe the trained model)
    # ------------------------------------------------------------------
    def save_model(self, filepath: str = MODEL_PATH) -> bool:
        if not self.is_trained:
            logger.warning("Cannot save model: model not trained yet")
            return False

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        scaler = self.feature_scaler
        torch.save(
            {
                "model_state_dict": self.model.state_dict(),
                "input_dim": self.input_dim,
                "hidden_dim": self.hidden_dim,
                "embedding_dim": self.embedding_dim,
                "epochs": self.epochs,
                "scaler_mean": scaler.mean_.tolist(),
                "scaler_scale": scaler.scale_.tolist(),
                "scaler_var": scaler.var_.tolist(),
                "node_mapping": {int(k): list(v) for k, v in self.node_mapping.items()},
                "train_losses": self.train_losses,
                "trained_at": self.trained_at,
                "num_nodes": self.num_nodes,
                "num_edges": self.num_edges,
                "val_auc": self.val_auc,
                "training_history": self.training_history,
            },
            filepath,
        )
        logger.info(f"Model saved to {filepath}")
        return True

    def load_model(self, filepath: str = MODEL_PATH) -> bool:
        if not os.path.exists(filepath):
            return False

        try:
            ckpt = torch.load(filepath, map_location="cpu", weights_only=True)
        except TypeError:  # older torch without weights_only
            ckpt = torch.load(filepath, map_location="cpu")

        self.input_dim = ckpt["input_dim"]
        self.hidden_dim = ckpt["hidden_dim"]
        self.embedding_dim = ckpt["embedding_dim"]
        self.epochs = ckpt.get("epochs", self.epochs)
        self._build_model()
        self.model.load_state_dict(ckpt["model_state_dict"])

        scaler = StandardScaler()
        scaler.mean_ = np.array(ckpt["scaler_mean"])
        scaler.scale_ = np.array(ckpt["scaler_scale"])
        scaler.var_ = np.array(ckpt["scaler_var"])
        scaler.n_features_in_ = len(scaler.mean_)
        scaler.n_samples_seen_ = 1
        self.feature_scaler = scaler

        self.node_mapping = {int(k): tuple(v) for k, v in ckpt.get("node_mapping", {}).items()}
        self.reverse_mapping = {v: k for k, v in self.node_mapping.items()}
        self.train_losses = ckpt.get("train_losses", [])
        self.trained_at = ckpt.get("trained_at")
        self.num_nodes = ckpt.get("num_nodes", 0)
        self.num_edges = ckpt.get("num_edges", 0)
        self.val_auc = ckpt.get("val_auc")
        self.training_history = ckpt.get("training_history", [])
        self.is_trained = True

        logger.info(f"Model loaded from {filepath}")
        return True


# Global instance reused across requests
gnn_detector = None


def get_gnn_detector() -> GVAEAnomalyDetector:
    global gnn_detector
    if gnn_detector is None:
        gnn_detector = GVAEAnomalyDetector()
        try:
            gnn_detector.load_model()
        except Exception as e:
            logger.warning(f"Could not load saved model: {e}")
    return gnn_detector