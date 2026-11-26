"""
Configuration settings for Enterprise Autonomous AI Infrastructure Monitoring System.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SAMPLE_LOGS_DIR = BASE_DIR / "sample_logs"

PROJECT_TITLE = "Enterprise Autonomous AI Infrastructure Monitoring System"
PROJECT_SUBTITLE = "Real-Time Multi-Device Windows AIOps Platform"
VERSION = "5.1.0-3D"

# Research Paper Architecture Alignment (IEEE Paper: Enterprise Autonomous AI Infrastructure Monitoring System)
RESEARCH_MODULES = [
    "Log Upload Module",
    "Log Processing Module",
    "Semantic Embedding Module (SentenceTransformer all-MiniLM-L6-v2)",
    "FAISS Intelligence Engine (Vector Similarity Search)",
    "Critical Event Detection Module",
    "Root Cause Analysis Engine (RCA)",
    "Predictive Failure Detection Module",
    "Autonomous Self-Healing Engine",
    "Infrastructure Health Scoring Module",
    "Conversational AI Assistant",
    "Streamlit Monitoring Dashboard"
]

STAGES = {
    "Stage 1": {
        "title": "Log Upload, Processing & Monitoring Dashboard",
        "paper_steps": "Steps 1 & 2 (Log Ingestion, Preprocessing & Streamlit Dashboard)",
        "status": "COMPLETED",
        "description": "Log Upload Module, Log Processing Module, multi-format parsing, telemetry extraction, and Streamlit infrastructure dashboard."
    },
    "Stage 2": {
        "title": "Critical Event Detection, RCA, Health Scoring & Self-Healing",
        "paper_steps": "Steps 5, 6, 7, 8 & 9 (Operational Failures, RCA, Health Index & Self-Healing)",
        "status": "COMPLETED",
        "description": "Rule & pattern detection for errors/timeouts/crashes, RCA across 6 failure domains (DB, CPU, Memory, Storage, Auth, Network), Predictive Failure probability, Health Index %, and autonomous self-healing recommendations."
    },
    "Stage 3": {
        "title": "Semantic Log Vectorization & FAISS Indexing",
        "paper_steps": "Steps 3 & 4 (SentenceTransformer all-MiniLM-L6-v2 & FAISS Vector Engine)",
        "status": "COMPLETED",
        "description": "High-dimensional vector embeddings with SentenceTransformer ('all-MiniLM-L6-v2') and FAISS index for sub-second semantic retrieval over infrastructure logs."
    },
    "Stage 4": {
        "title": "Conversational AI Infrastructure Assistant",
        "paper_steps": "Step 10 (Interactive Natural Language Infrastructure Copilot)",
        "status": "COMPLETED",
        "description": "Embedded natural language AI assistant enabling engineers to query infrastructure health, failure root causes, and execute safe recovery actions."
    },
    "Stage 5": {
        "title": "Real-Time Multi-Device Windows Monitoring & Central Backend",
        "paper_steps": "Live Production Windows Agents, FastAPI + SQLite, WebSocket/SSE Streaming",
        "status": "COMPLETED",
        "description": "Continuous Windows Event Viewer, psutil telemetry, incremental app log tailing, authenticated multi-computer enrollment, persistent FAISS similarity search, and auto-updating Streamlit Command Center."
    }
}

# Stage 3 Vector Embedding Configuration
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384
DEFAULT_TOP_K = 5

# Stage 4 Conversational Assistant Configuration
DEFAULT_LLM_PROVIDER = "Deterministic Evidence-Based Engine (Offline)"
MAX_CHAT_HISTORY = 50

# Standardized Log Severity Mapping
SEVERITY_LEVELS = ["CRITICAL", "FATAL", "ERROR", "WARN", "WARNING", "INFO", "DEBUG"]
SEVERITY_COLORS = {
    "CRITICAL": "#ef4444",
    "FATAL": "#dc2626",
    "ERROR": "#f97316",
    "WARN": "#f59e0b",
    "WARNING": "#f59e0b",
    "INFO": "#3b82f6",
    "DEBUG": "#64748b"
}
