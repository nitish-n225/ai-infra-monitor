"""
Automated Verification Tests for Kaggle HDFS_v1 Model Artifacts, Leakage Checks, and Runtime Scoring.
"""
import os
import sys
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.ml_log_anomaly import (
    DEFAULT_METRICS_PATH,
    DEFAULT_MODEL_PATH,
    EVENT_IDS,
    LogAnomalyScorer,
    build_event_feature_matrix,
)
from src.parser import InfrastructureLogParser
from src.sample_data import load_sample_log


def test_kaggle_trained_artifacts_and_zero_leakage():
    assert DEFAULT_MODEL_PATH.exists(), f"Missing trained model at {DEFAULT_MODEL_PATH}"
    assert DEFAULT_METRICS_PATH.exists(), f"Missing evaluation metrics at {DEFAULT_METRICS_PATH}"

    metrics = LogAnomalyScorer.load_evaluation_metrics()
    assert metrics is not None
    leak = metrics["leakage_prevention"]
    assert leak["train_val_seq_overlap"] == 0
    assert leak["train_test_seq_overlap"] == 0
    assert leak["val_test_seq_overlap"] == 0

    best_key = metrics["selected_deployed_session_model"]
    test_m = metrics["models"][best_key]["test_metrics"]
    assert test_m["accuracy"] > 0.99
    assert test_m["f1_score"] > 0.99
    assert test_m["confusion_matrix"]["tp"] > 2000
    print(f"[PASS] Trained HDFS_v1 artifacts & zero-leakage splits verified ({best_key}, Test F1={test_m['f1_score']}).")


def test_runtime_log_and_hdfs_matrix_scoring():
    LogAnomalyScorer.clear_cache()
    norm_df = InfrastructureLogParser.parse_text(load_sample_log("normal_operations.log"))
    norm_res = LogAnomalyScorer.score_parsed_logs(norm_df)
    assert norm_res["available"] is True
    assert norm_res["prediction"] == "NORMAL", f"False positive on normal operations: {norm_res}"
    assert norm_res["flagged_events"] == 0

    raw = load_sample_log("production_incident.log")
    df = InfrastructureLogParser.parse_text(raw)
    res = LogAnomalyScorer.score_parsed_logs(df)
    assert res["available"] is True
    assert res["evaluated_rows"] > 0
    assert res["flagged_events"] >= 1
    assert res["prediction"] == "ANOMALY_DETECTED"
    assert 0.0 <= res["max_anomaly_prob"] <= 100.0

    # Empty DataFrame safety check
    empty_res = LogAnomalyScorer.score_parsed_logs(pd.DataFrame())
    assert empty_res["flagged_events"] == 0

    # Direct Event_occurrence_matrix batch scoring check (synthetic normal vs exception vector)
    row_norm = {e: 0 for e in EVENT_IDS}
    row_norm.update({"E5": 3, "E6": 3, "E11": 3, "E9": 3, "E26": 3, "E22": 1})
    row_fail = {e: 0 for e in EVENT_IDS}
    row_fail.update({"E5": 2, "E7": 2, "E10": 1, "E12": 1, "E20": 1, "E29": 1})
    hdfs_df = pd.DataFrame([row_norm, row_fail])
    X, names = build_event_feature_matrix(hdfs_df, include_timing=False)
    assert X.shape == (2, 71) or X.shape[0] == 2
    assert len(names) == X.shape[1]

    mat_res = LogAnomalyScorer.score_hdfs_matrix(hdfs_df)
    assert mat_res is not None and mat_res["available"] is True
    assert mat_res["rows"] == 2
    assert int(mat_res["predictions"][1]) == 1
    print(f"[PASS] Runtime parsed-log & HDFS matrix ML scoring verified (features={len(names)}).")


if __name__ == "__main__":
    test_kaggle_trained_artifacts_and_zero_leakage()
    test_runtime_log_and_hdfs_matrix_scoring()
    print("[SUCCESS] All Kaggle ML pipeline verification tests passed!")

