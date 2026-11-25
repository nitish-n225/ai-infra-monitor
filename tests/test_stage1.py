"""
Automated Unit Tests for Stage 1: Enterprise Autonomous AI Infrastructure Monitoring System.
"""
import sys
import os
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.parser import InfrastructureLogParser
from src.telemetry import TelemetryAnalyzer
from src.sample_data import load_sample_log, get_available_sample_files

def test_bracketed_log_parsing():
    line = "2026-10-25 10:00:01.102 [INFO] [ingress-gateway] Ingress healthy. 248 active connections."
    parsed = InfrastructureLogParser.parse_line(line, line_no=1)
    assert parsed is not None
    assert parsed["level"] == "INFO"
    assert parsed["service"] == "ingress-gateway"
    assert "Ingress healthy" in parsed["message"]
    print("[PASS] Bracketed log format parsed successfully.")

def test_standard_log_parsing():
    line = "2026-10-25 10:02:30.104 ERROR [cache-redis-01] OOM command not allowed when used memory > 'maxmemory'."
    parsed = InfrastructureLogParser.parse_line(line, line_no=2)
    assert parsed is not None
    assert parsed["level"] == "ERROR"
    assert parsed["service"] == "cache-redis-01"
    assert "OOM command" in parsed["message"]
    print("[PASS] Standard log format parsed successfully.")

def test_json_log_parsing():
    line = '{"time": "2026-10-25T10:00:00Z", "level": "WARN", "service": "k8s-node-1", "msg": "Memory pressure"}'
    parsed = InfrastructureLogParser.parse_line(line, line_no=3)
    assert parsed is not None
    assert parsed["level"] == "WARN"
    assert parsed["service"] == "k8s-node-1"
    assert parsed["message"] == "Memory pressure"
    print("[PASS] JSON log format parsed successfully.")

def test_telemetry_computation():
    sample_text = (
        "2026-10-25 10:00:01 [INFO] [svc-a] Health OK\n"
        "2026-10-25 10:00:02 [WARN] [svc-b] High CPU\n"
        "2026-10-25 10:00:03 [ERROR] [svc-a] Connection timeout\n"
        "2026-10-25 10:00:04 [CRITICAL] [svc-c] Database crashed\n"
    )
    df = InfrastructureLogParser.parse_text(sample_text)
    assert len(df) == 4

    telemetry = TelemetryAnalyzer.compute_summary(df)
    assert telemetry["total_logs"] == 4
    assert telemetry["info_count"] == 1
    assert telemetry["warn_count"] == 1
    assert telemetry["error_count"] == 1
    assert telemetry["critical_count"] == 1
    assert telemetry["unique_services_count"] == 3
    assert telemetry["error_rate_pct"] == 50.0  # 2 errors out of 4 = 50%
    print("[PASS] Telemetry summary computed with accurate metrics.")

def test_sample_files_exist_and_parse():
    sample_files = get_available_sample_files()
    assert len(sample_files) >= 2
    assert "production_incident.log" in sample_files
    assert "normal_operations.log" in sample_files

    content = load_sample_log("production_incident.log")
    assert content is not None
    df = InfrastructureLogParser.parse_text(content)
    assert len(df) > 10
    telemetry = TelemetryAnalyzer.compute_summary(df)
    assert telemetry["critical_count"] > 0
    print(f"[PASS] Sample production incident parsed: {len(df)} logs, {telemetry['critical_count']} critical/fatal incidents.")

if __name__ == "__main__":
    print("=" * 60)
    print("Running Stage 1 Test Suite for Enterprise AI Infrastructure Monitor")
    print("=" * 60)
    test_bracketed_log_parsing()
    test_standard_log_parsing()
    test_json_log_parsing()
    test_telemetry_computation()
    test_sample_files_exist_and_parse()
    print("=" * 60)
    print("[SUCCESS] All Stage 1 tests passed successfully!")
    print("=" * 60)
