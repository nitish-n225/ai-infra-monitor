# Model Training & Evaluation Report — Enterprise Autonomous AI Infrastructure Monitoring System

**Generated (UTC):** `2026-11-27T06:32:19Z`  
**Trained Model Bundle:** [models/hdfs_log_anomaly_model.joblib](models/hdfs_log_anomaly_model.joblib) (`282.2 KB`)  
**Metrics Artifact:** [models/hdfs_evaluation_metrics.json](models/hdfs_evaluation_metrics.json)  
**Reproducible Script:** [train_kaggle_model.py](train_kaggle_model.py)

---

## 1. Existing AI Pipeline Inspection (Before Integration)

Before adding Kaggle dataset training, every existing AI/detection module was audited:

| Component | Module | Paradigm | Prior Training / Data Status |
| :--- | :--- | :--- | :--- |
| Security & Rate Rules | `detection/rules_engine.py` (`RulesEngine`) | **Rule-Based** | Regex signatures (`SQLI_REGEX`, `XSS_REGEX`, `PATH_TRAVERSAL_REGEX`, `RECON_FILES_REGEX`) & sliding-window thresholds |
| Root Cause Analysis | `src/rca_engine.py`, `backend/ai_pipeline.py` | **Rule-Based** | Regex `INCIDENT_PATTERNS` + `WINDOWS_RCA_PATTERNS` + heuristic confidence |
| Infrastructure Health | `src/health_score.py` | **Rule-Based** | Deterministic severity/service deduction rules |
| Predictive Risk & Trends | `src/predictive_failure.py`, `backend/ai_pipeline.py` | **Rule / Heuristic** | Weighted 4-factor risk rubric + `np.polyfit` telemetry linear slopes |
| Semantic Embeddings | `src/embedding_engine.py`, `src/vector_store.py` | **Pretrained / Hashing** | Pretrained `all-MiniLM-L6-v2` (384-dim) or Blake2b fallback + FAISS `IndexFlatIP(384)` |
| AI Assistant | `src/assistant_engine.py` | **Deterministic / API** | Grounded offline evidence templates or optional OpenAI-compatible LLM |
| Legacy ML Detector | `detection/ml_detector.py` (`MLAnomalyDetector`) | **Trained (Synthetic)** | `IsolationForest` trained on `1,500` synthetic random HTTP records; **no real dataset, no train/val/test split, no evaluation metrics, not integrated into main log/live pipeline** |

---

## 2. Kaggle Dataset Selection & Characteristics

- **Dataset Name:** HDFS_v1 LogHub Dataset Archive  
- **Source Link:** https://www.kaggle.com/datasets/tamaniwilliams/hdfs-v1-loghub-dataset-archive  
- **License:** **Apache 2.0**  
- **Files Used (in `KAGGLE/`):**
  - `anomaly_label.csv` (`17.77 MB`) — Ground-truth block session labels (`BlockId`, `Label`: `Normal` / `Anomaly`)
  - `Event_occurrence_matrix.csv` (`50.64 MB`) — Structured event frequency vectors (`BlockId`, `Label`, `Type`, `E1`..`E29`)
  - `Event_traces.csv` (`119.60 MB`) — Ordered template sequences, inter-event timings, and total trace latency (`BlockId`, `Label`, `Type`, `Features`, `TimeInterval`, `Latency`)
  - `HDFS.log_templates.csv` (`1.56 KB`) — Canonical template text definitions for `E1`..`E29`

### Dataset Scale & Class Distribution
- **Total Block Traces:** `575,061` (all `BlockId` values unique; `0` missing feature cells)
- **Normal (`Success`) Traces:** `558,223` (`97.072%`)
- **Anomaly (`Fail`) Traces:** `16,838` (`2.928%` positive rate — imbalanced binary classification)
- **Unique Ordered Event Sequences (`Features`):** `18,373`
- **Log Event Templates:** `29` (`E1`–`E29`)

---

## 3. Preprocessing & Data Leakage Prevention

### Identified Leakage Risks & Mitigations
1. **Post-hoc / Target Column Leakage:** Both `Event_occurrence_matrix.csv` and `Event_traces.csv` contain `BlockId`, `Label`, and `Type` (where `Type` is a failure-type code populated only for anomalous rows). All three (`BlockId`, `Label`, `Type`) are **strictly dropped** prior to feature construction.
2. **Sequence Repetition Leakage:** Although all `575,061` `BlockId` identifiers are unique, only `18,373` unique ordered `Features` sequences exist across all traces. A naive random `train_test_split` would place identical log execution sequences in both training and test sets.
3. **Mitigation — Sequence-Disjoint Stratified Group Split (`70 / 15 / 15`):**
   - Implemented `stratified_group_split()` in [train_kaggle_model.py](train_kaggle_model.py), packing each of the `18,373` unique `Features` sequence groups strictly into a single split (`train`, `val`, or `test`) while balancing both total rows and anomaly ratio (`~2.93%`).
   - Verified post-split overlap: **`train ∩ val = 0`**, **`train ∩ test = 0`**, **`val ∩ test = 0`** unique sequences.
4. **Strict Fit/Transform Separation:**
   - `StandardScaler` and `TfidfVectorizer` were fit **only on `Train`**.
   - Decision thresholds (maximizing F1 on Precision-Recall curve) were tuned **only on `Validation`**.
   - The held-out **`Test` split (`86,244` blocks across `2,754` unseen sequences)** was used strictly once for final evaluation.

| Split | Block Traces | Share | Anomalies | Anomaly Rate | Unique Sequences | Shared Sequences w/ Other Splits |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| **Train** | `402,573` | `70.01%` | `11,786` | `2.928%` | `12,866` | `0` |
| **Validation** | `86,244` | `15.00%` | `2,526` | `2.929%` | `2,753` | `0` |
| **Test (Held-Out)** | `86,244` | `15.00%` | `2,526` | `2.929%` | `2,754` | `0` |

### Feature Engineering
- **Event Session Feature Set (`70` features, deployed in `session_model`):**
  - `29` raw template counts (`E1`..`E29`) + `29` normalized event ratios (`E_k / total_events`)
  - `5` structural session statistics: `total_events`, `unique_event_types`, `event_diversity_ratio`, `max_event_count`, `max_event_dominance`
  - `7` failure/domain group aggregates derived from `HDFS.log_templates.csv` wording: `exception_event_count` (`E4,E7,E10,E12,E14`), `failure_interrupt_count` (`E8,E13,E17,E20,E28,E29`), `replication_delete_count`, `error_signal_total`, `error_signal_ratio`, `has_exception_flag`, `has_failure_flag` (`29 + 29 + 5 + 7 = 70` leak-free columns; legacy descriptive text in `hdfs_evaluation_metrics.json` notes `67 features` prior to adding the 3 domain signal indicators).
- **Event + Timing Feature Set (`+7` timing features = `77` columns total from `Event_traces.csv`):** adds `latency`, `log1p_latency`, `latency_per_event`, `ti_mean`, `log1p_ti_max`, `ti_std`, `ti_nonzero_ratio` (evaluated for ablation).
- **Reconstructed Log-Text Representation (deployed in `text_model`):** reconstructs template log wording per trace using `HDFS.log_templates.csv` (stripping `[*]`), encoded via `TfidfVectorizer(ngram_range=(1, 2), max_features=3000, sublinear_tf=True)`.

---

## 4. Models & Training Configuration

All models were trained with deterministic seeds (`random_state=42`):
1. **`hist_gb_event_features` (Primary Deployed Session Classifier):** `HistGradientBoostingClassifier(max_iter=150, learning_rate=0.08, max_leaf_nodes=31, min_samples_leaf=30, l2_regularization=1.0)` with positive class weight `min(neg/pos, 20.0)` and validation-tuned probability threshold (`0.8059`).
2. **`hist_gb_event_plus_timing`:** Same HGB configuration trained with `Latency` & `TimeInterval` features (`threshold = 0.9750`).
3. **`random_forest_event_features`:** `RandomForestClassifier(n_estimators=120, max_depth=16, min_samples_leaf=5, class_weight="balanced_subsample")` (`threshold = 0.7905`).
4. **`logistic_regression_event_features`:** `StandardScaler` + `LogisticRegression(max_iter=400, class_weight="balanced", C=1.0)` (`threshold = 0.9204`).
5. **`tfidf_logreg_log_text` (Deployed Live Log-Text Classifier):** `TfidfVectorizer(ngram_range=(1, 2), max_features=3000, sublinear_tf=True)` + `LogisticRegression(max_iter=400, class_weight="balanced", C=1.5)` fit on up to `120,000` stratified Train traces (`threshold = 0.9761`).
6. **`unsupervised_isolation_forest` (Unsupervised Reference):** `IsolationForest(n_estimators=100, contamination=0.03)` fit strictly on `100,000` Normal-only Train traces (`threshold = -0.0565` on `-decision_function`).

---

## 5. Held-Out Test Evaluation & Baseline Comparison

Evaluated strictly once on the **`86,244`** held-out Test block traces (`83,718` Normal, `2,526` Anomaly) from **`2,754` completely unseen event sequences**:

### Summary Table (Held-Out Test Set, `n = 86,244`)

| Model / Detection Pipeline | Accuracy | Precision | Recall | F1-Score | ROC-AUC | PR-AUC | Confusion Matrix `[[TN, FP], [FN, TP]]` |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| **`hist_gb_event_features` (Deployed Session ML)** | **0.999965** | **0.998814** | **1.000000** | **0.999407** | **1.000000** | **0.999989** | `[[83715, 3], [0, 2526]]` |
| `hist_gb_event_plus_timing` | `0.999861` | `0.998810` | `0.996437` | `0.997622` | `1.000000` | `0.999984` | `[[83715, 3], [9, 2517]]` |
| `random_forest_event_features` | `0.999838` | `0.997623` | `0.996833` | `0.997228` | `0.999997` | `0.999896` | `[[83712, 6], [8, 2518]]` |
| `logistic_regression_event_features` | `0.999710` | `0.991742` | `0.998416` | `0.995068` | `0.999977` | `0.999165` | `[[83697, 21], [4, 2522]]` |
| **`tfidf_logreg_log_text` (Deployed Text ML)** | **`0.996939`** | **`0.966969`** | **`0.927158`** | **`0.946645`** | **`0.999610`** | **`0.987745`** | `[[83638, 80], [184, 2342]]` |
| `unsupervised_isolation_forest` | `0.895285` | `0.198368` | `0.846793` | `0.321437` | `0.936025` | `0.221622` | `[[75074, 8644], [387, 2139]]` |
| `template_keyword_rule_baseline` (Error Regex) | `0.780553` | `0.100234` | `0.813935` | `0.178488` | — | — | `[[65262, 18456], [470, 2056]]` |
| `existing_rca_regex_rules` (`src/rca_engine.py`) | `0.970711` | `0.000000` | `0.000000` | `0.000000` | — | — | `[[83718, 0], [2526, 0]]` |

### Unique-Sequence Deduplicated Held-Out Test Check (`n = 2,754` Unseen Sequences)
To prevent high-frequency normal sequences from masking errors on rare execution paths, we also evaluated `1` representative block trace per unique unseen test sequence (`2,137` Normal, `617` Anomaly):
- **`hist_gb_event_features`:** `Accuracy = 0.998911`, `Precision = 0.995161`, `Recall = 1.000000`, `F1 = 0.997575`, `CM = [[2134, 3], [0, 617]]`
- **`hist_gb_event_plus_timing`:** `Accuracy = 0.996006`, `Precision = 0.995098`, `Recall = 0.987034`, `F1 = 0.991050`, `CM = [[2134, 3], [8, 609]]`
- **`random_forest_event_features`:** `Accuracy = 0.994916`, `Precision = 0.990244`, `Recall = 0.987034`, `F1 = 0.988636`, `CM = [[2131, 6], [8, 609]]`

### Key Takeaways vs. Existing Detection Pipeline
1. **Existing `INCIDENT_PATTERNS` Regexes (`src/rca_engine.py`):** Designed for web/DB/Windows events (`OOMKilled`, `PostgreSQL`, `x509`, `502`), so they matched `0` of `29` HDFS block storage templates (`TP = 0`, `F1 = 0.0000`).
2. **Naive Infrastructure Keyword Regex (`exception|failed|error|interrupted|timed out|unexpected`):** Caught `81.39%` (`2,056 / 2,526`) of failing HDFS traces, but generated **`18,456` false positives** (`Precision = 10.02%`) because transient exceptions/interruptions also occur in completed Normal block workflows, and missed `470` structural anomalies (`F1 = 0.1785`).
3. **Unsupervised `IsolationForest`:** Without labeled failure supervision, statistical outlier detection flagged rare valid block sequences alongside real anomalies (`8,644` FPs, `Precision = 19.84%`, `F1 = 0.3214`).
4. **Trained Supervised Models (`HGB` & `TF-IDF + LogReg`):** Learned multi-template co-occurrence and recovery combinations (`Exception` without subsequent `Received/addStoredBlock` completion vs. fatal replication failures), cutting false positives by **>99.5%** compared to keyword rules (`80` FP for TF-IDF text, `3` FP for HGB session model) while achieving `F1 = 0.9466` (text) and `F1 = 0.9994` (session).
*(Note: The legacy `detection/ml_detector.py` `MLAnomalyDetector` accepts only 5 HTTP request features `[endpoint_len, special_chars, size, status_code, method_code]` and cannot score HDFS system logs natively.)*

---

## 6. System Integration (Preserving All Live Functionality)

The evaluated artifacts are integrated via [src/ml_log_anomaly.py](src/ml_log_anomaly.py) without disturbing the Windows agent, FAISS semantic search, RCA rule engine, or dashboard:
- **Runtime Scorer:** `LogAnomalyScorer.score_parsed_logs(df)` scores parsed logs & live event streams using the saved `tfidf_logreg_log_text` pipeline + template regex matchers (`E1`..`E29`), while `LogAnomalyScorer.score_hdfs_matrix(df)` scores Kaggle HDFS `Event_occurrence_matrix` CSV batches using the saved `hist_gb_event_features` model.
- **Backend Live AI Integration:** [backend/ai_pipeline.py](backend/ai_pipeline.py) (`evaluate_device_ai_state`) attaches `ml_anomaly` to live device evaluations non-destructively inside a safe `try/except` wrapper.
- **API & Client:** [backend/server.py](backend/server.py) exposes `GET /api/v1/ai/ml-model`, and [src/realtime_client.py](src/realtime_client.py) exposes `get_ml_model_info()`.
- **Dashboard UI:** [app.py](app.py) and [src/ui/views.py](src/ui/views.py) display active-dataset ML anomaly flags and an expandable Kaggle `HDFS_v1` evaluation benchmark table inside **Overview** and **Incidents & RCA** while preserving all existing views.

---

## 7. Limitations

1. **Domain Specificity (HDFS vs. Windows/Cloud Events):** All training labels originate from Hadoop Distributed File System (`HDFS_v1`) block operations (`NameSystem`, `PacketResponder`, `Receiving block`). While the deployed `tfidf_logreg_log_text` model generalizes failure vocabulary (`exception`, `failed`, `timed out`, `interrupted`) onto live Windows/service logs, OS-specific Windows failures (e.g., DCOM errors, NTFS disk faults, Registry/auth events) should primarily rely on the live Windows RCA engine and FAISS index unless retrained on labeled Windows event logs.
2. **Count-Signature Collisions:** Across `18,373` unique ordered sequences, `Event_occurrence_matrix.csv` collapses unordered event counts into `589` distinct count signatures (`9` count patterns exhibit mixed `Normal`/`Anomaly` labels across traces depending on event ordering or latency).
3. **Class Imbalance & Offline Batch Assumption:** Only `2.928%` of HDFS blocks are anomalous; scoring individual raw log lines (`tfidf_logreg_log_text` at inference) differs structurally from whole-block trace scoring used during offline evaluation.

---

## 8. Instructions to Retrain the Model

1. Place the extracted Kaggle `HDFS_v1` CSV files (`anomaly_label.csv`, `Event_occurrence_matrix.csv`, `Event_traces.csv`, `HDFS.log_templates.csv`) in `KAGGLE/`.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the reproducible training & evaluation script:
   ```bash
   python train_kaggle_model.py --data-dir KAGGLE
   ```
4. Verify trained artifacts & pipeline integration:
   ```bash
   python tests/test_kaggle_ml_pipeline.py
   ```

