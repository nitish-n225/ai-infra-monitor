"""
Sample Data Loader Module.
Provides instant access to realistic sample logs for evaluation and testing.
"""
from pathlib import Path
from typing import Optional
from config import SAMPLE_LOGS_DIR

def load_sample_log(filename: str = "production_incident.log") -> Optional[str]:
    """Loads text content of a sample log file."""
    file_path = SAMPLE_LOGS_DIR / filename
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return None

def get_available_sample_files() -> list:
    """Lists available sample log files in sample_logs/."""
    if not SAMPLE_LOGS_DIR.exists():
        return []
    return [f.name for f in SAMPLE_LOGS_DIR.glob("*.log")]
