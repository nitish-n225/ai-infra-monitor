"""
Reproducible Training, Leak-Free Splitting & Held-Out Test Evaluation Pipeline
for Kaggle HDFS_v1 LogHub Infrastructure Anomaly Detection.

Usage:
    python train_kaggle_model.py --data-dir KAGGLE
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, IsolationForest, RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from src.ml_log_anomaly import (
    DEFAULT_METRICS_PATH,
    DEFAULT_MODEL_PATH,
    EVENT_IDS,
    build_event_feature_matrix,
    build_reconstructed_log_texts,
    load_template_map,
)
from src.rca_engine import INCIDENT_PATTERNS, RootCauseAnalysisEngine


def stratified_group_split(
    groups: np.ndarray,
    y: np.ndarray,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
) -> np.ndarray:
    """
    Assigns every distinct sequence group strictly to one of {'train', 'val', 'test'}
    using greedy dual-balance packing on (positive count, total count).
    Guarantees ZERO overlap of unique sequences or BlockIds across splits.
    """
    assert abs((train_ratio + val_ratio + test_ratio) - 1.0) < 1e-6
    df_meta = pd.DataFrame({"seq": groups, "y": y})
    grp = df_meta.groupby("seq", sort=True).agg(n=("y", "size"), pos=("y", "sum")).reset_index()
    grp = grp.sort_values(["pos", "n", "seq"], ascending=[False, False, True]).reset_index(drop=True)

    targets = {"train": train_ratio, "val": val_ratio, "test": test_ratio}
    total_n = max(int(len(y)), 1)
    total_pos = max(int(y.sum()), 1)
    cur_n = {"train": 0, "val": 0, "test": 0}
    cur_pos = {"train": 0, "val": 0, "test": 0}
    seq_to_split: Dict[str, str] = {}

    for row in grp.itertuples(index=False):
        best_split = min(
            ("train", "val", "test"),
            key=lambda s: (
                0.60 * ((cur_pos[s] + 0.5 * row.pos) / (targets[s] * total_pos))
                + 0.40 * ((cur_n[s] + 0.5 * row.n) / (targets[s] * total_n))
            ),
        )
        seq_to_split[row.seq] = best_split
        cur_n[best_split] += int(row.n)
        cur_pos[best_split] += int(row.pos)

    return pd.Series(groups).map(seq_to_split).to_numpy()


def find_optimal_f1_threshold(
    y_true: np.ndarray,
    y_score: np.ndarray,
    clip_range: Tuple[float, float] | None = (0.05, 0.99),
) -> float:
    """Tunes decision threshold strictly on the Validation split."""
    precisions, recalls, thresholds = precision_recall_curve(y_true, y_score)
    if len(thresholds) == 0:
        return 0.5
    p = precisions[:-1]
    r = recalls[:-1]
    denom = p + r
    f1s = np.divide(2.0 * p * r, denom, out=np.zeros_like(denom, dtype=np.float64), where=denom > 0)
    best_idx = int(np.argmax(f1s))
    th = float(thresholds[best_idx])
    if clip_range is not None:
        th = float(np.clip(th, clip_range[0], clip_range[1]))
    return th


def compute_binary_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray | None = None) -> Dict[str, Any]:
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = [int(v) for v in cm.ravel()]
    res: Dict[str, Any] = {
        "samples": int(len(y_true)),
        "positives": int(y_true.sum()),
        "negatives": int((1 - y_true).sum()),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 6),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 6),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 6),
        "f1_score": round(float(f1_score(y_true, y_pred, zero_division=0)), 6),
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp, "matrix": [[tn, fp], [fn, tp]]},
    }
    if y_prob is not None and len(np.unique(y_true)) == 2:
        res["roc_auc"] = round(float(roc_auc_score(y_true, y_prob)), 6)
        res["pr_auc"] = round(float(average_precision_score(y_true, y_prob)), 6)
    return res


def evaluate_rule_baselines_on_test(
    test_occ_df: pd.DataFrame,
    y_test: np.ndarray,
    template_map: Dict[str, str],
) -> Dict[str, Dict[str, Any]]:
    """
    Evaluates our existing rule-based detection pipeline (RootCauseAnalysisEngine)
    plus an explicit template keyword rule baseline on the exact held-out Test log traces.
    """
    # Map each of the 29 template strings through existing RootCauseAnalysisEngine pattern catalog
    rca_flagged_eids = set()
    kw_regex = re.compile(r"\b(exception|failed|error|interrupted|timed out|unexpected)\b", re.I)
    kw_flagged_eids = set()
    for eid in EVENT_IDS:
        msg = template_map[eid]
        # Evaluate pattern match directly using INCIDENT_PATTERNS regex strings
        for cfg in INCIDENT_PATTERNS.values():
            if any(re.search(pat, msg, re.I) for pat in cfg.get("patterns", [])):
                rca_flagged_eids.add(eid)
        if kw_regex.search(msg):
            kw_flagged_eids.add(eid)

    counts = test_occ_df[EVENT_IDS].to_numpy(dtype=np.int32)
    eid_idx = {e: i for i, e in enumerate(EVENT_IDS)}

    rca_cols = [eid_idx[e] for e in rca_flagged_eids]
    pred_existing_rca = (counts[:, rca_cols].sum(axis=1) > 0).astype(int) if rca_cols else np.zeros_like(y_test)

    kw_cols = [eid_idx[e] for e in kw_flagged_eids]
    pred_keyword_rule = (counts[:, kw_cols].sum(axis=1) > 0).astype(int) if kw_cols else np.zeros_like(y_test)

    m_rca = compute_binary_metrics(y_test, pred_existing_rca)
    m_rca["matched_event_ids"] = sorted(rca_flagged_eids)

    m_kw = compute_binary_metrics(y_test, pred_keyword_rule)
    m_kw["matched_event_ids"] = sorted(kw_flagged_eids)

    return {
        "existing_rca_regex_rules": m_rca,
        "template_keyword_rule_baseline": m_kw,
    }


def main():
    parser = argparse.ArgumentParser(description="Train & evaluate HDFS_v1 Kaggle anomaly detection model.")
    parser.add_argument("--data-dir", type=Path, default=ROOT_DIR / "KAGGLE")
    parser.add_argument("--model-out", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--metrics-out", type=Path, default=DEFAULT_METRICS_PATH)
    args = parser.parse_args()

    t_start = time.time()
    data_dir = args.data_dir
    print(f"[1/6] Loading Kaggle HDFS_v1 dataset from: {data_dir}")

    templates_map = load_template_map(data_dir / "HDFS.log_templates.csv")
    labels_df = pd.read_csv(data_dir / "anomaly_label.csv")
    occ_df = pd.read_csv(data_dir / "Event_occurrence_matrix.csv")
    traces_df = pd.read_csv(data_dir / "Event_traces.csv", usecols=["BlockId", "Label", "Features", "TimeInterval", "Latency"])

    assert (occ_df["BlockId"].values == labels_df["BlockId"].values).all(), "BlockId order mismatch"
    assert (traces_df["BlockId"].values == labels_df["BlockId"].values).all(), "Trace BlockId mismatch"
    y = (labels_df["Label"].values == "Anomaly").astype(np.int32)

    print(f"    Loaded {len(y):,} block traces | Normal: {(y == 0).sum():,} | Anomaly: {y.sum():,} ({y.mean()*100:.2f}%)")

    # 2. Strict leak-free grouped split on canonical ordered sequence `Features`
    print("[2/6] Building leak-free stratified group split on ordered sequence `Features`...")
    splits = stratified_group_split(traces_df["Features"].values, y, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15)
    m_tr = splits == "train"
    m_va = splits == "val"
    m_te = splits == "test"

    # Explicit leakage verification assertions
    s_tr = set(traces_df.loc[m_tr, "Features"].unique())
    s_va = set(traces_df.loc[m_va, "Features"].unique())
    s_te = set(traces_df.loc[m_te, "Features"].unique())
    assert len(s_tr & s_va) == 0 and len(s_tr & s_te) == 0 and len(s_va & s_te) == 0, "Sequence leakage detected!"

    split_summary = {}
    for name, mask, seqs in [("train", m_tr, s_tr), ("val", m_va, s_va), ("test", m_te, s_te)]:
        split_summary[name] = {
            "rows": int(mask.sum()),
            "pct_rows": round(float(mask.mean()) * 100.0, 2),
            "anomalies": int(y[mask].sum()),
            "anomaly_rate_pct": round(float(y[mask].mean()) * 100.0, 3),
            "unique_sequences": int(len(seqs)),
        }
        print(f"    {name:5s}: {split_summary[name]['rows']:>7,} rows ({split_summary[name]['pct_rows']:5.2f}%) | "
              f"anom={split_summary[name]['anomalies']:>5,} ({split_summary[name]['anomaly_rate_pct']:.2f}%) | "
              f"uniq_seqs={split_summary[name]['unique_sequences']:,}")

    # 3. Feature engineering (both Event-Only and Event+Timing views)
    print("[3/6] Engineering leak-free features (zero BlockId/Type/Label features)...")
    X_ev, feat_names_ev = build_event_feature_matrix(occ_df, include_timing=False)
    X_full, feat_names_full = build_event_feature_matrix(occ_df, traces_df=traces_df, include_timing=True)

    # Deduplicated sequence-group mask on held-out Test set (1 representative row per unseen sequence)
    te_idx = np.where(m_te)[0]
    te_df_tmp = pd.DataFrame({"row_idx": te_idx, "seq": traces_df["Features"].values[m_te]})
    te_uniq_row_idx = te_df_tmp.drop_duplicates(subset=["seq"], keep="first")["row_idx"].to_numpy()
    y_te_uniq = y[te_uniq_row_idx]

    # Sample weights for imbalance (applied only on Train!)
    pos_cnt = max(int(y[m_tr].sum()), 1)
    neg_cnt = max(int((1 - y[m_tr]).sum()), 1)
    pos_weight = min(neg_cnt / pos_cnt, 20.0)
    sw_train = np.where(y[m_tr] == 1, pos_weight, 1.0).astype(np.float32)

    results: Dict[str, Any] = {}
    trained_candidates: Dict[str, Tuple[Any, float, np.ndarray]] = {}

    # Candidate 1: HistGradientBoostingClassifier (Event-Only features -> works on matrix CSVs without timing)
    print("[4/6] Training & tuning candidate models strictly on Train/Validation...")
    hgb_ev = HistGradientBoostingClassifier(
        max_iter=150,
        learning_rate=0.08,
        max_leaf_nodes=31,
        min_samples_leaf=30,
        l2_regularization=1.0,
        random_state=42,
    )
    hgb_ev.fit(X_ev[m_tr], y[m_tr], sample_weight=sw_train)
    val_p = hgb_ev.predict_proba(X_ev[m_va])[:, 1]
    th = find_optimal_f1_threshold(y[m_va], val_p)
    te_p = hgb_ev.predict_proba(X_ev[m_te])[:, 1]
    results["hist_gb_event_features"] = {
        "feature_set": "E1..E29 counts + ratios + template signals (67 features)",
        "tuned_threshold": round(th, 4),
        "val_metrics": compute_binary_metrics(y[m_va], (val_p >= th).astype(int), val_p),
        "test_metrics": compute_binary_metrics(y[m_te], (te_p >= th).astype(int), te_p),
        "test_unique_sequence_metrics": compute_binary_metrics(
            y_te_uniq, (hgb_ev.predict_proba(X_ev[te_uniq_row_idx])[:, 1] >= th).astype(int),
            hgb_ev.predict_proba(X_ev[te_uniq_row_idx])[:, 1],
        ),
    }
    trained_candidates["hist_gb_event_features"] = (hgb_ev, th, te_p)

    # Candidate 2: HistGradientBoostingClassifier (Event + Trace Timing features)
    hgb_full = HistGradientBoostingClassifier(
        max_iter=150,
        learning_rate=0.08,
        max_leaf_nodes=31,
        min_samples_leaf=30,
        l2_regularization=1.0,
        random_state=42,
    )
    hgb_full.fit(X_full[m_tr], y[m_tr], sample_weight=sw_train)
    val_p_full = hgb_full.predict_proba(X_full[m_va])[:, 1]
    th_full = find_optimal_f1_threshold(y[m_va], val_p_full)
    te_p_full = hgb_full.predict_proba(X_full[m_te])[:, 1]
    results["hist_gb_event_plus_timing"] = {
        "feature_set": "E1..E29 counts/ratios/signals + Latency & TimeInterval stats (74 features)",
        "tuned_threshold": round(th_full, 4),
        "val_metrics": compute_binary_metrics(y[m_va], (val_p_full >= th_full).astype(int), val_p_full),
        "test_metrics": compute_binary_metrics(y[m_te], (te_p_full >= th_full).astype(int), te_p_full),
        "test_unique_sequence_metrics": compute_binary_metrics(
            y_te_uniq, (hgb_full.predict_proba(X_full[te_uniq_row_idx])[:, 1] >= th_full).astype(int),
            hgb_full.predict_proba(X_full[te_uniq_row_idx])[:, 1],
        ),
    }

    # Candidate 3: RandomForestClassifier (Event features)
    rf_ev = RandomForestClassifier(
        n_estimators=120,
        max_depth=16,
        min_samples_leaf=5,
        class_weight="balanced_subsample",
        n_jobs=-1,
        random_state=42,
    )
    rf_ev.fit(X_ev[m_tr], y[m_tr])
    val_p_rf = rf_ev.predict_proba(X_ev[m_va])[:, 1]
    th_rf = find_optimal_f1_threshold(y[m_va], val_p_rf)
    te_p_rf = rf_ev.predict_proba(X_ev[m_te])[:, 1]
    results["random_forest_event_features"] = {
        "feature_set": "E1..E29 counts + ratios + template signals (67 features)",
        "tuned_threshold": round(th_rf, 4),
        "val_metrics": compute_binary_metrics(y[m_va], (val_p_rf >= th_rf).astype(int), val_p_rf),
        "test_metrics": compute_binary_metrics(y[m_te], (te_p_rf >= th_rf).astype(int), te_p_rf),
        "test_unique_sequence_metrics": compute_binary_metrics(
            y_te_uniq, (rf_ev.predict_proba(X_ev[te_uniq_row_idx])[:, 1] >= th_rf).astype(int),
            rf_ev.predict_proba(X_ev[te_uniq_row_idx])[:, 1],
        ),
    }

    # Candidate 4: Logistic Regression (Scaled Event features)
    lr_ev = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=400, class_weight="balanced", C=1.0, random_state=42)),
    ])
    lr_ev.fit(X_ev[m_tr], y[m_tr])
    val_p_lr = lr_ev.predict_proba(X_ev[m_va])[:, 1]
    th_lr = find_optimal_f1_threshold(y[m_va], val_p_lr)
    te_p_lr = lr_ev.predict_proba(X_ev[m_te])[:, 1]
    results["logistic_regression_event_features"] = {
        "feature_set": "StandardScaled E1..E29 + structural ratios (67 features)",
        "tuned_threshold": round(th_lr, 4),
        "val_metrics": compute_binary_metrics(y[m_va], (val_p_lr >= th_lr).astype(int), val_p_lr),
        "test_metrics": compute_binary_metrics(y[m_te], (te_p_lr >= th_lr).astype(int), te_p_lr),
    }

    # Candidate 5: Deployable Live Log-Text Model (TF-IDF on Template Log Text + LogisticRegression)
    # Fit vectorizer strictly on Train reconstructed log documents (deduplicated slightly or full train subset <=120k for speed)
    print("    Training deployable Log-Text TF-IDF Classifier...")
    all_texts = build_reconstructed_log_texts(occ_df, template_map=templates_map)
    tr_idx = np.where(m_tr)[0]
    rng = np.random.default_rng(42)
    # Stratified subsample up to 120k rows from Train for crisp TF-IDF training (<10s)
    if len(tr_idx) > 120000:
        pos_tr = tr_idx[y[tr_idx] == 1]
        neg_tr = tr_idx[y[tr_idx] == 0]
        neg_keep = rng.choice(neg_tr, size=max(120000 - len(pos_tr), 10000), replace=False)
        tr_text_idx = np.concatenate([pos_tr, neg_keep])
    else:
        tr_text_idx = tr_idx

    text_pipe = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=3000, sublinear_tf=True)),
        ("clf", LogisticRegression(max_iter=400, class_weight="balanced", C=1.5, random_state=42)),
    ])
    text_pipe.fit([all_texts[i] for i in tr_text_idx], y[tr_text_idx])
    va_texts = [all_texts[i] for i in np.where(m_va)[0]]
    te_texts = [all_texts[i] for i in te_idx]
    val_p_txt = text_pipe.predict_proba(va_texts)[:, 1]
    th_txt = find_optimal_f1_threshold(y[m_va], val_p_txt)
    te_p_txt = text_pipe.predict_proba(te_texts)[:, 1]
    results["tfidf_logreg_log_text"] = {
        "feature_set": "TF-IDF (1-2 gram) over HDFS.log_templates log message text",
        "tuned_threshold": round(th_txt, 4),
        "val_metrics": compute_binary_metrics(y[m_va], (val_p_txt >= th_txt).astype(int), val_p_txt),
        "test_metrics": compute_binary_metrics(y[m_te], (te_p_txt >= th_txt).astype(int), te_p_txt),
    }

    # Candidate 6: Unsupervised IsolationForest baseline (fit strictly on Normal-only rows of Train)
    normal_tr_idx = tr_idx[y[tr_idx] == 0]
    if_sample = rng.choice(normal_tr_idx, size=min(len(normal_tr_idx), 100000), replace=False)
    iso = IsolationForest(n_estimators=100, contamination=0.03, random_state=42, n_jobs=-1)
    iso.fit(X_ev[if_sample])
    # Higher -decision_function = more anomalous (signed score, so do not clip to probability [0, 1])
    val_if_score = -iso.decision_function(X_ev[m_va])
    th_if = find_optimal_f1_threshold(y[m_va], val_if_score, clip_range=None)
    te_if_score = -iso.decision_function(X_ev[m_te])
    results["unsupervised_isolation_forest"] = {
        "feature_set": "E1..E29 counts + ratios (trained on Normal-only Train split)",
        "tuned_threshold_neg_score": round(float(th_if), 4),
        "val_metrics": compute_binary_metrics(y[m_va], (val_if_score >= th_if).astype(int), val_if_score),
        "test_metrics": compute_binary_metrics(y[m_te], (te_if_score >= th_if).astype(int), te_if_score),
    }

    # 5. Evaluate existing rule-based detection baselines on exact same held-out Test split
    print("[5/6] Evaluating existing rule-based baselines on held-out Test set...")
    rule_baselines = evaluate_rule_baselines_on_test(occ_df.loc[m_te], y[m_te], templates_map)
    for b_name, b_metrics in rule_baselines.items():
        results[b_name] = {
            "feature_set": "Rule-based regex pattern matching on reconstructed HDFS template messages",
            "test_metrics": b_metrics,
        }

    # Select best deployable event-session model strictly by Validation F1-score (event-only so it works on all CSVs/live)
    session_candidates = [
        ("hist_gb_event_features", hgb_ev, th),
        ("random_forest_event_features", rf_ev, th_rf),
        ("logistic_regression_event_features", lr_ev, th_lr),
    ]
    best_name, best_session_model, best_session_th = max(
        session_candidates,
        key=lambda item: results[item[0]]["val_metrics"]["f1_score"],
    )

    # Save trained bundle & metrics JSON
    print("[6/6] Saving trained model bundle and evaluation metrics...")
    args.model_out.parent.mkdir(parents=True, exist_ok=True)
    bundle = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": "HDFS_v1 LogHub Dataset Archive (tamaniwilliams/hdfs-v1-loghub-dataset-archive)",
        "license": "Apache 2.0",
        "primary_model_name": f"{best_name} + tfidf_logreg_log_text",
        "session_model_name": best_name,
        "session_model": best_session_model,
        "session_threshold": float(best_session_th),
        "session_feature_names": feat_names_ev,
        "text_model": text_pipe,
        "text_threshold": float(th_txt),
        "unsupervised_iforest": iso,
        "template_map": templates_map,
    }
    joblib.dump(bundle, args.model_out, compress=3)

    report_payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(time.time() - t_start, 2),
        "dataset": {
            "name": "HDFS_v1 LogHub Dataset Archive",
            "kaggle_url": "https://www.kaggle.com/datasets/tamaniwilliams/hdfs-v1-loghub-dataset-archive",
            "license": "Apache 2.0",
            "total_blocks": int(len(y)),
            "normal_blocks": int((y == 0).sum()),
            "anomaly_blocks": int(y.sum()),
            "anomaly_rate_pct": round(float(y.mean()) * 100.0, 3),
            "unique_sequences": int(traces_df["Features"].nunique()),
            "templates_count": len(templates_map),
        },
        "leakage_prevention": {
            "split_method": "Stratified greedy group packing by canonical ordered sequence `Features`",
            "dropped_columns": ["BlockId", "Label", "Type"],
            "train_val_seq_overlap": 0,
            "train_test_seq_overlap": 0,
            "val_test_seq_overlap": 0,
        },
        "splits": split_summary,
        "selected_deployed_session_model": best_name,
        "selected_deployed_text_model": "tfidf_logreg_log_text",
        "models": results,
    }
    args.metrics_out.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")

    print("\n=== HELD-OUT TEST EVALUATION SUMMARY ===")
    for name, info in results.items():
        tm = info["test_metrics"]
        cm = tm["confusion_matrix"]
        print(
            f"{name:34s} | Acc={tm['accuracy']:.4f} | Prec={tm['precision']:.4f} | "
            f"Rec={tm['recall']:.4f} | F1={tm['f1_score']:.4f} | CM=[[TN={cm['tn']}, FP={cm['fp']}], [FN={cm['fn']}, TP={cm['tp']}]]"
        )
    print(f"\nSaved model bundle: {args.model_out} ({args.model_out.stat().st_size / 1024:.1f} KB)")
    print(f"Saved metrics JSON: {args.metrics_out}")
    print(f"Completed in {time.time() - t_start:.2f}s.")


if __name__ == "__main__":
    main()

