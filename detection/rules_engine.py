import re
import time
from collections import defaultdict, deque
from typing import Dict, Any, Optional, Tuple, List

# Signatures for known cyber attack vectors
SQLI_REGEX = re.compile(
    r"(\b(UNION(\s+ALL)?\s+SELECT|SELECT\s+.*\s+FROM|INSERT\s+INTO|DROP\s+TABLE|UPDATE\s+.*\s+SET|DELETE\s+FROM)\b)|"
    r"('.*--)|(\bOR\s+\d+=\d+)|('.*\bOR\b.*')|(\bSLEEP\(\d+\))|(\bBENCHMARK\()",
    re.IGNORECASE
)

XSS_REGEX = re.compile(
    r"(<script.*?>.*?</script>)|(javascript:)|(onerror\s*=)|(onload\s*=)|(<iframe.*?>)|(<svg.*?onload)|(<img.*?src=.*?onerror)",
    re.IGNORECASE
)

PATH_TRAVERSAL_REGEX = re.compile(
    r"(\.\./|\.\.\\|%2e%2e%2f|%2e%2e/|%252e%252e%252f|/etc/passwd|/windows/win\.ini|boot\.ini)",
    re.IGNORECASE
)

RECON_FILES_REGEX = re.compile(
    r"(/\.env|/\.git/|/wp-config\.php|/phpmyadmin|/actuator/|/\.aws/|/id_rsa|/web\.config|/server-status)",
    re.IGNORECASE
)

class RulesEngine:
    """Deterministic Rule-Based Detection Engine with Signature Matching & Stateful Rate Limiting."""

    def __init__(self):
        # Sliding windows for stateful detections: IP -> deque of timestamps
        self.failed_logins: Dict[str, deque] = defaultdict(deque)
        self.request_windows: Dict[str, deque] = defaultdict(deque)

        # Threshold configurations
        self.BRUTE_FORCE_LIMIT = 5       # Max failed logins
        self.BRUTE_FORCE_WINDOW = 60     # in 60 seconds
        self.DOS_RATE_LIMIT = 25         # Max requests
        self.DOS_RATE_WINDOW = 10        # in 10 seconds

    def analyze(self, log_event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyzes a single log event against known signatures and behavioral thresholds.
        Returns threat details dict if malicious, or None if benign.
        """
        endpoint = log_event.get("endpoint", "")
        ip = log_event.get("client_ip", "127.0.0.1")
        method = log_event.get("method", "GET")
        status_code = int(log_event.get("status_code", 200))
        now = time.time()

        # 1. Check SQL Injection (SQLi)
        if SQLI_REGEX.search(endpoint):
            return {
                "threat_type": "SQL_INJECTION",
                "severity": "CRITICAL",
                "threat_source": "RULE_ENGINE",
                "details": f"SQL Injection signature detected in request URL: '{endpoint}'",
                "recommendation": "Block client IP, use prepared statements & input sanitization."
            }

        # 2. Check Cross-Site Scripting (XSS)
        if XSS_REGEX.search(endpoint):
            return {
                "threat_type": "XSS_ATTACK",
                "severity": "HIGH",
                "threat_source": "RULE_ENGINE",
                "details": f"XSS payload pattern detected in request: '{endpoint}'",
                "recommendation": "Enforce Content Security Policy (CSP) and sanitize query strings."
            }

        # 3. Check Directory / Path Traversal
        if PATH_TRAVERSAL_REGEX.search(endpoint):
            return {
                "threat_type": "PATH_TRAVERSAL",
                "severity": "HIGH",
                "threat_source": "RULE_ENGINE",
                "details": f"Path traversal attempt to access sensitive system files: '{endpoint}'",
                "recommendation": "Restrict URI decoding, validate absolute path boundaries."
            }

        # 4. Check Reconnaissance & Secret Probing
        if RECON_FILES_REGEX.search(endpoint):
            return {
                "threat_type": "RECONNAISSANCE",
                "severity": "MEDIUM",
                "threat_source": "RULE_ENGINE",
                "details": f"Attempted probe of sensitive/admin configuration path: '{endpoint}'",
                "recommendation": "Configure web server to return 403 Forbidden and block enumeration crawlers."
            }

        # 5. Stateful: Brute Force Login Detection
        if "/login" in endpoint.lower() and status_code in (401, 403):
            window = self.failed_logins[ip]
            window.append(now)
            # Prune old timestamps
            while window and window[0] < now - self.BRUTE_FORCE_WINDOW:
                window.popleft()

            if len(window) >= self.BRUTE_FORCE_LIMIT:
                return {
                    "threat_type": "BRUTE_FORCE",
                    "severity": "CRITICAL",
                    "threat_source": "RULE_ENGINE",
                    "details": f"Brute force detected from IP {ip}: {len(window)} failed authentication attempts in {self.BRUTE_FORCE_WINDOW}s.",
                    "recommendation": "Temporarily lock account, challenge IP with CAPTCHA, and enforce rate limits."
                }

        # 6. Stateful: DoS / High Rate Burst Detection
        ip_reqs = self.request_windows[ip]
        ip_reqs.append(now)
        while ip_reqs and ip_reqs[0] < now - self.DOS_RATE_WINDOW:
            ip_reqs.popleft()

        if len(ip_reqs) >= self.DOS_RATE_LIMIT:
            return {
                "threat_type": "DOS_BURST",
                "severity": "CRITICAL",
                "threat_source": "RULE_ENGINE",
                "details": f"Denial of Service flood: IP {ip} sent {len(ip_reqs)} requests in {self.DOS_RATE_WINDOW}s.",
                "recommendation": "Deploy automatic IP null-routing or Cloudflare/Nginx rate-limit filtering."
            }

        return None
