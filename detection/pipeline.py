from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from ingestion.log_parser import LogParser
from detection.rules_engine import RulesEngine
from detection.ml_detector import MLAnomalyDetector
from storage.database import insert_log, insert_alert

class SecurityPipeline:
    """Unified detection pipeline combining Rule-Based signatures and Machine Learning."""

    def __init__(self):
        self.rules_engine = RulesEngine()
        self.ml_detector = MLAnomalyDetector()

    def process(self, log_input: Any) -> Dict[str, Any]:
        """
        Accepts either a raw string log or a structured dictionary.
        Returns the processed event with threat classification and database record IDs.
        """
        if isinstance(log_input, str):
            event = LogParser.parse_line(log_input)
            if not event:
                return {"error": "Failed to parse log line"}
        elif isinstance(log_input, dict):
            event = log_input
        else:
            return {"error": "Invalid log format"}

        # Step 1: Check Deterministic Rule-Based Engine
        threat = self.rules_engine.analyze(event)
        anomaly_score = 0.0

        # Step 2: If Rule engine didn't catch anything, run ML Anomaly Detector
        if not threat:
            is_anomaly, score, ml_threat = self.ml_detector.analyze(event)
            anomaly_score = score
            if is_anomaly and ml_threat:
                threat = ml_threat
        else:
            # Still compute anomaly score for stats
            _, anomaly_score, _ = self.ml_detector.analyze(event)

        # Step 3: Populate Threat Metadata
        if threat:
            event["is_threat"] = 1
            event["threat_type"] = threat["threat_type"]
            event["threat_source"] = threat["threat_source"]
            event["severity"] = threat["severity"]
            event["anomaly_score"] = anomaly_score

            # Create Alert Record
            alert_id = insert_alert({
                "timestamp": event.get("timestamp", datetime.utcnow().isoformat()),
                "client_ip": event.get("client_ip", "127.0.0.1"),
                "threat_type": threat["threat_type"],
                "severity": threat["severity"],
                "threat_source": threat["threat_source"],
                "details": threat["details"],
                "recommendation": threat["recommendation"],
                "status": "ACTIVE"
            })
            event["alert_id"] = alert_id
            event["threat_details"] = threat
        else:
            event["is_threat"] = 0
            event["threat_type"] = "NORMAL"
            event["threat_source"] = "NONE"
            event["severity"] = "NONE"
            event["anomaly_score"] = anomaly_score
            event["threat_details"] = None

        # Step 4: Persist log entry
        log_id = insert_log(event)
        event["id"] = log_id

        return event
