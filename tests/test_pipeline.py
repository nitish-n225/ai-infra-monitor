import sys
import os

# Add root directory to python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from detection.pipeline import SecurityPipeline
from ingestion.log_generator import LogGenerator
from storage.database import init_db, get_stats

def run_tests():
    print("Testing Security Pipeline & Database...")
    init_db()
    pipeline = SecurityPipeline()

    # Test 1: Normal Log
    normal_log = LogGenerator.generate_normal_log()
    res_normal = pipeline.process(normal_log)
    print(f"Test 1 (Normal): is_threat={res_normal['is_threat']}, type={res_normal['threat_type']}")
    assert res_normal["is_threat"] == 0

    # Test 2: SQL Injection Attack
    sqli_log = LogGenerator.generate_sqli_attack()
    res_sqli = pipeline.process(sqli_log)
    print(f"Test 2 (SQLi): is_threat={res_sqli['is_threat']}, type={res_sqli['threat_type']}")
    assert res_sqli["is_threat"] == 1
    assert res_sqli["threat_type"] == "SQL_INJECTION"

    # Test 3: XSS Attack
    xss_log = LogGenerator.generate_xss_attack()
    res_xss = pipeline.process(xss_log)
    print(f"Test 3 (XSS): is_threat={res_xss['is_threat']}, type={res_xss['threat_type']}")
    assert res_xss["is_threat"] == 1
    assert res_xss["threat_type"] == "XSS_ATTACK"

    # Test 4: Path Traversal Attack
    traversal_log = LogGenerator.generate_path_traversal()
    res_trav = pipeline.process(traversal_log)
    print(f"Test 4 (Path Traversal): is_threat={res_trav['is_threat']}, type={res_trav['threat_type']}")
    assert res_trav["is_threat"] == 1
    assert res_trav["threat_type"] == "PATH_TRAVERSAL"

    # Test 5: Brute Force Attack
    bf_logs = LogGenerator.generate_brute_force_batch(count=6)
    detected_bf = False
    for log in bf_logs:
        res = pipeline.process(log)
        if res.get("threat_type") == "BRUTE_FORCE":
            detected_bf = True
            break
    print(f"Test 5 (Brute Force): detected={detected_bf}")
    assert detected_bf is True

    # Test 6: Database Stats
    stats = get_stats()
    print("Database Stats Summary:")
    print(f"  Total Logs: {stats['total_logs']}")
    print(f"  Threat Logs: {stats['threat_logs']}")
    print(f"  Active Alerts: {stats['active_alerts']}")
    print(f"  Threat Distribution: {stats['threat_distribution']}")

    print("\n[SUCCESS] All 6 pipeline unit tests passed seamlessly!")

if __name__ == "__main__":
    run_tests()
