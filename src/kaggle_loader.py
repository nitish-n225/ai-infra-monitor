"""
Kaggle Dataset Catalog & Archive Loader for Infrastructure Log & Telemetry CSVs.
Supports direct CSV uploads from kaggle.com as well as Kaggle API dataset downloads.
"""
import io
import os
import re
import zipfile
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests

KAGGLE_DATASETS: List[Dict[str, str]] = [
    {
        "title": "Windows Event Log Dataset",
        "slug": "initialv/windows-event-log",
        "url": "https://www.kaggle.com/datasets/initialv/windows-event-log",
        "focus": "Windows Event Viewer logs (TimeCreated, Level, Source, EventID, Message)",
    },
    {
        "title": "Log Data for Anomaly Detection",
        "slug": "quek01/log-data-for-anomaly-detection",
        "url": "https://www.kaggle.com/datasets/quek01/log-data-for-anomaly-detection",
        "focus": "Sequence-based server & infrastructure log anomaly benchmark",
    },
    {
        "title": "Server Logs - Suspicious (CIDDS)",
        "slug": "kartikjaspal/server-logs-suspicious",
        "url": "https://www.kaggle.com/datasets/kartikjaspal/server-logs-suspicious",
        "focus": "Suspicious server traffic flows, anomalies & attack indicators",
    },
    {
        "title": "System Monitoring & Security Dataset",
        "slug": "subashm/system-monitoring-and-security-dataset",
        "url": "https://www.kaggle.com/datasets/subashm/system-monitoring-and-security-dataset",
        "focus": "CPU/Memory resource metrics paired with security intrusion labels",
    },
]


def parse_kaggle_slug(url_or_slug: str) -> Optional[str]:
    """
    Extracts canonical '<owner>/<dataset>' slug from a Kaggle dataset URL or slug string.
    Returns None if invalid.
    """
    raw = (url_or_slug or "").strip()
    if not raw:
        return None
    if raw.startswith(("http://", "https://")):
        parsed = urlparse(raw)
        if "kaggle.com" not in (parsed.netloc or "").lower():
            return None
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 3 and parts[0].lower() == "datasets":
            return f"{parts[1]}/{parts[2]}"
        return None
    cleaned = raw.strip("/")
    if re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+", cleaned):
        return cleaned
    return None


def _pick_kaggle_credentials(username: str = "", api_key: str = "") -> Tuple[str, str]:
    user = (username or os.environ.get("KAGGLE_USERNAME", "")).strip()
    key = (api_key or os.environ.get("KAGGLE_KEY", "")).strip()
    if user and key:
        return user, key
    try:
        import streamlit as st
        user = user or str(st.secrets.get("KAGGLE_USERNAME", "")).strip()
        key = key or str(st.secrets.get("KAGGLE_KEY", "")).strip()
    except Exception:
        pass
    return user, key


def extract_best_log_from_zip(raw_zip: bytes, max_rows: int = 2000) -> Tuple[str, str]:
    """
    Extracts the primary .csv, .log, .txt, or .json dataset file from a Kaggle ZIP archive
    and caps line count to max_rows (+ header) to keep dashboard & vector indexing fast.
    Returns (filename, content_text).
    """
    allowed_exts = (".csv", ".log", ".txt", ".json")
    with zipfile.ZipFile(io.BytesIO(raw_zip), "r") as zf:
        candidates = [
            info
            for info in zf.infolist()
            if not info.is_dir() and info.filename.lower().endswith(allowed_exts)
        ]
        if not candidates:
            raise ValueError("No .csv, .log, .txt, or .json file found inside Kaggle archive.")
        # Prefer CSV/LOG over small README/metadata txt files by picking largest matching file
        candidates.sort(key=lambda info: info.file_size, reverse=True)
        chosen = candidates[0]
        raw_bytes = zf.read(chosen.filename)

    text = raw_bytes.decode("utf-8", errors="replace")
    lines = text.splitlines()
    cap = max(50, int(max_rows))
    if len(lines) > cap + 1:
        text = "\n".join(lines[: cap + 1])
    basename = os.path.basename(chosen.filename)
    return basename, text


def download_kaggle_dataset(
    url_or_slug: str,
    username: str = "",
    api_key: str = "",
    max_rows: int = 2000,
    timeout: float = 35.0,
) -> Tuple[str, str]:
    """
    Downloads a dataset archive from Kaggle's official dataset download API and extracts
    the primary log/CSV file ready for InfrastructureLogParser.
    """
    slug = parse_kaggle_slug(url_or_slug)
    if not slug:
        raise ValueError("Enter a valid Kaggle dataset slug (owner/dataset) or https://www.kaggle.com/datasets/owner/dataset URL.")

    user, key = _pick_kaggle_credentials(username, api_key)
    api_url = f"https://www.kaggle.com/api/v1/datasets/download/{slug}"
    auth = (user, key) if (user and key) else None

    resp = requests.get(api_url, auth=auth, timeout=timeout, allow_redirects=True)
    if resp.status_code in (401, 403):
        raise PermissionError(
            "Kaggle requires your API credentials (KAGGLE_USERNAME & KAGGLE_KEY from kaggle.com -> Settings -> API) "
            "for direct downloads, or download the CSV from Kaggle and drop it into the uploader above."
        )
    resp.raise_for_status()

    content_type = (resp.headers.get("Content-Type") or "").lower()
    if resp.content[:2] == b"PK" or "zip" in content_type:
        return extract_best_log_from_zip(resp.content, max_rows=max_rows)

    text = resp.content.decode("utf-8", errors="replace")
    if text.lstrip().startswith("<!DOCTYPE html") or "<html" in text[:300].lower():
        raise PermissionError(
            "Kaggle returned a sign-in page instead of the dataset archive. Add your Kaggle Username & API Key or upload the downloaded CSV directly."
        )
    lines = text.splitlines()
    cap = max(50, int(max_rows))
    if len(lines) > cap + 1:
        text = "\n".join(lines[: cap + 1])
    return f"{slug.replace('/', '_')}.csv", text
