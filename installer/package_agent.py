"""
Builds a portable zip distribution (dist/windows-monitoring-agent.zip)
for installing the Windows Monitoring Agent on other laptops and PCs.
"""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "dist"
OUT_ZIP = DIST_DIR / "windows-monitoring-agent.zip"

INCLUDE_DIRS = ["agent", "installer"]
EXCLUDE_PATTERNS = {"__pycache__", ".pyc", "agent_config.json", "agent_state.json", "agent_state.db", "agent.log", "agent_service.log"}


def build_package() -> Path:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for folder in INCLUDE_DIRS:
            base = ROOT / folder
            if not base.exists():
                continue
            for file_path in base.rglob("*"):
                if not file_path.is_file():
                    continue
                if any(part in EXCLUDE_PATTERNS or file_path.name.endswith(".pyc") for part in file_path.parts):
                    continue
                if file_path.name == "package_agent.py":
                    continue
                rel = file_path.relative_to(ROOT)
                zf.write(file_path, arcname=str(rel))
    return OUT_ZIP


if __name__ == "__main__":
    zip_path = build_package()
    print(f"Created portable agent bundle: {zip_path}")

