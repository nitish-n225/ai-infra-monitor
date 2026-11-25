import os
import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from typing import Dict, Any, Tuple, Optional

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "isolation_forest.pkl")

class MLAnomalyDetector:
    """
    Unsupervised Anomaly Detection using Isolation Forest.
    Detects behavioral outliers, data exfiltration, abnormal payload lengths,
    and unknown (zero-day) traffic patterns without requiring labeled attack datasets.
    """

    def __init__(self, contamination: float = 0.05):
        self.contamination = contamination
        self.model: Optional[IsolationForest] = None
        self._load_or_train_model()

    @staticmethod
    def extract_features(log_event: Dict[str, Any]) -> list:
        """
        Extracts numerical feature vector for the ML model:
        [endpoint_length, param_count, response_size, status_code, method_code]
        """
        endpoint = log_event.get("endpoint", "/")
        endpoint_len = len(endpoint)
        
        # Count parameter and special encoding indicators (?, &, =, %, /)
        special_chars = sum(endpoint.count(c) for c in ["?", "&", "=", "%", ";", "$"])
        
        status_code = int(log_event.get("status_code", 200))
        size = int(log_event.get("response_size", 0))

        # Encode HTTP method
        method = log_event.get("method", "GET").upper()
        method_map = {"GET": 1, "POST": 2, "PUT": 3, "DELETE": 4, "OPTIONS": 5, "HEAD": 6}
        method_code = method_map.get(method, 0)

        return [endpoint_len, special_chars, size, status_code, method_code]

    def _train_baseline(self):
        """Generates baseline normal web traffic patterns and trains the Isolation Forest."""
        os.makedirs(MODEL_DIR, exist_ok=True)
        np.random.seed(42)
        
        # Baseline normal web browsing patterns:
        # endpoint_len ~ 15-40, special_chars ~ 0-3, size ~ 500-15000, status ~ 200 (mostly) or 304, method ~ GET/POST
        n_samples = 1500
        normal_endpoint_len = np.random.normal(25, 8, n_samples).clip(5, 70)
        normal_special_chars = np.random.poisson(1.2, n_samples).clip(0, 5)
        normal_sizes = np.random.normal(3500, 1500, n_samples).clip(200, 25000)
        normal_status = np.random.choice([200, 301, 302, 304, 404], size=n_samples, p=[0.88, 0.04, 0.04, 0.02, 0.02])
        normal_method = np.random.choice([1, 2], size=n_samples, p=[0.85, 0.15])

        X_train = np.column_stack([
            normal_endpoint_len,
            normal_special_chars,
            normal_sizes,
            normal_status,
            normal_method
        ])

        self.model = IsolationForest(
            n_estimators=100,
            contamination=self.contamination,
            random_state=42
        )
        self.model.fit(X_train)
        joblib.dump(self.model, MODEL_PATH)

    def _load_or_train_model(self):
        if os.path.exists(MODEL_PATH):
            try:
                self.model = joblib.load(MODEL_PATH)
                return
            except Exception:
                pass
        self._train_baseline()

    def analyze(self, log_event: Dict[str, Any]) -> Tuple[bool, float, Optional[Dict[str, Any]]]:
        """
        Analyzes a log event.
        Returns:
            is_anomaly (bool)
            anomaly_score (float, between 0.0 and 1.0, higher = more anomalous)
            threat_info (dict or None)
        """
        if self.model is None:
            self._load_or_train_model()

        features = np.array([self.extract_features(log_event)])
        
        # IsolationForest decision_function returns negative values for anomalies, positive for normal
        decision_val = self.model.decision_function(features)[0]
        # Normalize to 0.0 - 1.0 score (0 = perfectly normal, 1 = extreme outlier)
        anomaly_score = round(float(1.0 / (1.0 + np.exp(decision_val * 4))), 3)
        
        prediction = self.model.predict(features)[0] # -1 for anomaly, 1 for normal
        is_anomaly = bool(prediction == -1)

        if is_anomaly:
            threat_info = {
                "threat_type": "AI_ANOMALY_DETECTED",
                "severity": "HIGH" if anomaly_score > 0.75 else "MEDIUM",
                "threat_source": "ML_ISOLATION_FOREST",
                "details": f"Machine Learning detected statistical behavioral anomaly (Outlier Score: {anomaly_score * 100:.1f}%) on endpoint '{log_event.get('endpoint')}'.",
                "recommendation": "Investigate unusual request parameters, response size, and client payload entropy."
            }
            return True, anomaly_score, threat_info

        return False, anomaly_score, None
