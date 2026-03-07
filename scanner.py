#!/usr/bin/env python3
"""
=============================================================================
  Facebook-Clone Security Scanner & OSINT Tool
  For Educational / Authorized Penetration Testing ONLY
  Target: Isolated clone environments with written permission
=============================================================================
"""

import requests
import argparse
import json
import re
import time
import sys
import urllib.parse
from bs4 import BeautifulSoup
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────

# Default request headers to mimic a real browser
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# OWASP Top-10 based XSS payloads (safe test strings)
XSS_PAYLOADS = [
    "<script>alert('XSS')</script>",
    '"><script>alert(1)</script>',
    "';alert('XSS');//",
    "<img src=x onerror=alert('XSS')>",
    "<svg onload=alert(1)>",
    "javascript:alert(1)",
    "<body onload=alert(1)>",
]

# Basic SQL Injection test payloads
SQLI_PAYLOADS = [
    "'",
    '"',
    "' OR '1'='1",
    '" OR "1"="1',
    "' OR 1=1--",
    "1' ORDER BY 1--",
    "1 UNION SELECT NULL--",
    "'; DROP TABLE users--",
]

# Common sensitive paths to enumerate
SENSITIVE_PATHS = [
    "/admin",
    "/admin/login",
    "/wp-admin",
    "/dashboard",
    "/api",
    "/api/v1",
    "/api/users",
    "/api/users/me",
    "/graphql",
    "/.env",
    "/config.php",
    "/config.json",
    "/robots.txt",
    "/sitemap.xml",
    "/.git/HEAD",
    "/.git/config",
    "/backup",
    "/backup.zip",
    "/db.sql",
    "/phpinfo.php",
    "/server-status",
    "/actuator",
    "/actuator/health",
    "/actuator/env",
    "/swagger-ui.html",
    "/api-docs",
    "/v1/users",
    "/v2/users",
    "/profile",
    "/settings",
    "/login",
    "/register",
    "/logout",
    "/reset-password",
    "/forgot-password",
    "/search",
    "/users",
    "/friends",
    "/messages",
    "/notifications",
]

# Security headers that should be present
REQUIRED_SECURITY_HEADERS = {
    "Strict-Transport-Security": "Enforces HTTPS (HSTS)",
    "Content-Security-Policy": "Prevents XSS and data injection",
    "X-Frame-Options": "Prevents Clickjacking",
    "X-Content-Type-Options": "Prevents MIME sniffing",
    "Referrer-Policy": "Controls referrer information",
    "Permissions-Policy": "Controls browser features",
    "X-XSS-Protection": "Legacy XSS filter (Chrome removed, still tested)",
}

# Cookie attributes to check
COOKIE_CHECKS = ["HttpOnly", "Secure", "SameSite"]


# ─────────────────────────────────────────────
#  SESSION MANAGER
# ─────────────────────────────────────────────

class SessionManager:
    """Manages the HTTP session with optional authentication."""

    def __init__(self, target_url: str, timeout: int = 10):
        self.target_url = target_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def authenticate(self, login_path: str, username: str, password: str,
                     user_field: str = "email", pass_field: str = "password") -> bool:
        """
        Attempts to log in to the target using form-based authentication.
        Returns True on apparent success.
        """
        login_url = self.target_url + login_path
        print(f"[*] Attempting authentication at: {login_url}")

        # First GET to retrieve CSRF token if any
        try:
            resp = self.session.get(login_url, timeout=self.timeout)
            soup = BeautifulSoup(resp.text, "html.parser")
            csrf_token = None

            # Look for common CSRF token field names
            for name in ["csrf_token", "_token", "authenticity_token",
                         "csrf", "__RequestVerificationToken"]:
                tag = soup.find("input", {"name": name})
                if tag:
                    csrf_token = tag.get("value", "")
                    print(f"[+] CSRF token found: {csrf_token[:20]}...")
                    break

            # Build POST payload
            payload = {user_field: username, pass_field: password}
            if csrf_token:
                payload["csrf_token"] = csrf_token
                payload["_token"] = csrf_token

            post_resp = self.session.post(
                login_url, data=payload,
                timeout=self.timeout, allow_redirects=True
            )

            # Heuristic: if we get a 200 and no "invalid" keyword → success
            body_lower = post_resp.text.lower()
            if post_resp.status_code in (200, 302) and not any(
                kw in body_lower for kw in ["invalid", "incorrect", "failed", "error"]
            ):
                print("[+] Authentication appears successful.")
                return True
            else:
                print("[-] Authentication may have failed (check credentials).")
                return False

        except requests.RequestException as e:
            print(f"[!] Authentication error: {e}")
            return False

    def get(self, path: str, **kwargs):
        """Wrapper for session GET."""
        url = self.target_url + path if path.startswith("/") else path
        return self.session.get(url, timeout=self.timeout, **kwargs)

    def post(self, path: str, **kwargs):
        """Wrapper for session POST."""
        url = self.target_url + path if path.startswith("/") else path
        return self.session.post(url, timeout=self.timeout, **kwargs)


# ─────────────────────────────────────────────
#  OSINT MODULE
# ─────────────────────────────────────────────

class OSINTCollector:
    """Collects publicly accessible information from a user's profile page."""

    def __init__(self, session: SessionManager):
        self.session = session

    def collect_profile(self, profile_path: str) -> dict:
        """
        Scrapes all visible metadata from the target profile page.
        Returns a dictionary of collected data.
        """
        print(f"\n[OSINT] Collecting profile data from: {profile_path}")
        data = {
            "profile_url": self.session.target_url + profile_path,
            "collected_at": datetime.utcnow().isoformat() + "Z",
            "basic_info": {},
            "contact_info": {},
            "social_links": [],
            "images": [],
            "meta_tags": {},
            "open_graph": {},
            "raw_emails": [],
            "raw_phones": [],
            "scripts_found": [],
            "external_links": [],
        }

        try:
            resp = self.session.get(profile_path)
            soup = BeautifulSoup(resp.text, "html.parser")

            # ── Meta tags ──────────────────────────────────
            for meta in soup.find_all("meta"):
                name = meta.get("name") or meta.get("property") or ""
                content = meta.get("content", "")
                if name and content:
                    if name.startswith("og:"):
                        data["open_graph"][name] = content
                    else:
                        data["meta_tags"][name] = content

            # ── Title & description ────────────────────────
            title = soup.find("title")
            data["basic_info"]["page_title"] = title.text.strip() if title else "N/A"

            # ── All text containing name-like patterns ─────
            headings = soup.find_all(["h1", "h2", "h3"])
            data["basic_info"]["headings"] = [h.text.strip() for h in headings if h.text.strip()]

            # ── Email addresses via regex ──────────────────
            emails = re.findall(
                r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
                resp.text
            )
            data["raw_emails"] = list(set(emails))

            # ── Phone numbers via regex ────────────────────
            phones = re.findall(
                r"(\+?\d[\d\s\-().]{7,}\d)",
                resp.text
            )
            data["raw_phones"] = list(set(p.strip() for p in phones))

            # ── Images (src of all img tags) ───────────────
            for img in soup.find_all("img"):
                src = img.get("src", "")
                alt = img.get("alt", "")
                if src:
                    data["images"].append({"src": src, "alt": alt})

            # ── External links ─────────────────────────────
            base_domain = urllib.parse.urlparse(self.session.target_url).netloc
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("http") and base_domain not in href:
                    data["external_links"].append(href)
            data["external_links"] = list(set(data["external_links"]))

            # ── Inline scripts (may reveal API keys, tokens) ──
            for script in soup.find_all("script"):
                src = script.get("src")
                if src:
                    data["scripts_found"].append(src)
                else:
                    # Look for suspicious patterns in inline JS
                    text = script.string or ""
                    for pattern in ["api_key", "apiKey", "token", "secret", "password",
                                    "accessToken", "graphql", "endpoint"]:
                        if pattern in text:
                            data["scripts_found"].append(
                                f"[INLINE] Contains '{pattern}' — review manually"
                            )
                            break

            # ── Social / profile links ─────────────────────
            social_keywords = ["facebook", "twitter", "instagram", "linkedin",
                                "github", "youtube", "tiktok", "snapchat"]
            for a in soup.find_all("a", href=True):
                href = a["href"].lower()
                if any(kw in href for kw in social_keywords):
                    data["social_links"].append(a["href"])

            print(f"[+] OSINT collection complete. Found {len(data['raw_emails'])} emails, "
                  f"{len(data['images'])} images, {len(data['external_links'])} external links.")

        except requests.RequestException as e:
            data["error"] = str(e)
            print(f"[!] OSINT error: {e}")

        return data


# ─────────────────────────────────────────────
#  VULNERABILITY SCANNER
# ─────────────────────────────────────────────

class VulnerabilityScanner:
    """
    Performs OWASP Top-10 based vulnerability checks on the target.
    All tests are safe and non-destructive.
    """

    def __init__(self, session: SessionManager):
        self.session = session
        self.findings = []

    def _add_finding(self, severity: str, category: str, title: str,
                     description: str, evidence: str = "", remediation: str = ""):
        """Adds a vulnerability finding to the results list."""
        self.findings.append({
            "severity": severity,         # CRITICAL / HIGH / MEDIUM / LOW / INFO
            "category": category,         # OWASP category
            "title": title,
            "description": description,
            "evidence": evidence,
            "remediation": remediation,
            "found_at": datetime.utcnow().isoformat() + "Z",
        })
        icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡",
                "LOW": "🔵", "INFO": "⚪"}.get(severity, "❓")
        print(f"  {icon} [{severity}] {title}")

    # ── 1. Security Headers ────────────────────────────────────────────────
    def check_security_headers(self, path: str = "/") -> None:
        print("\n[SCAN] Checking security headers...")
        try:
            resp = self.session.get(path)
            headers = resp.headers

            for header, description in REQUIRED_SECURITY_HEADERS.items():
                if header not in headers:
                    self._add_finding(
                        severity="MEDIUM",
                        category="A05: Security Misconfiguration",
                        title=f"Missing HTTP Header: {header}",
                        description=f"The response is missing the '{header}' header. {description}.",
                        evidence=f"Header not present in response from {path}",
                        remediation=f"Add '{header}' to all HTTP responses via server/framework configuration."
                    )
                else:
                    self._add_finding(
                        severity="INFO",
                        category="A05: Security Misconfiguration",
                        title=f"Header Present: {header}",
                        description=f"Value: {headers[header]}",
                        evidence=f"{header}: {headers[header]}"
                    )

            # Check for server version disclosure
            server = headers.get("Server", "")
            if server and any(char.isdigit() for char in server):
                self._add_finding(
                    severity="LOW",
                    category="A05: Security Misconfiguration",
                    title="Server Version Disclosure",
                    description="The Server header reveals version information that can help attackers target known vulnerabilities.",
                    evidence=f"Server: {server}",
                    remediation="Configure the server to hide version information."
                )

            # X-Powered-By check
            powered = headers.get("X-Powered-By", "")
            if powered:
                self._add_finding(
                    severity="LOW",
                    category="A05: Security Misconfiguration",
                    title="Technology Disclosure via X-Powered-By",
                    description="X-Powered-By header reveals backend technology stack.",
                    evidence=f"X-Powered-By: {powered}",
                    remediation="Remove or obscure the X-Powered-By header."
                )

        except requests.RequestException as e:
            print(f"  [!] Headers check error: {e}")

    # ── 2. Cookie Security ─────────────────────────────────────────────────
    def check_cookie_security(self, path: str = "/login") -> None:
        print("\n[SCAN] Checking cookie security attributes...")
        try:
            resp = self.session.get(path, allow_redirects=True)
            cookies = resp.cookies

            if not cookies:
                # Try root path
                resp = self.session.get("/")
                cookies = resp.cookies

            for cookie in cookies:
                issues = []
                if not cookie.has_nonstandard_attr("HttpOnly") and not cookie._rest.get("HttpOnly"):
                    issues.append("Missing HttpOnly flag")
                if not cookie.secure:
                    issues.append("Missing Secure flag")
                samesite = cookie._rest.get("SameSite", "")
                if not samesite:
                    issues.append("Missing SameSite attribute")

                if issues:
                    self._add_finding(
                        severity="HIGH" if "HttpOnly" in str(issues) else "MEDIUM",
                        category="A02: Cryptographic Failures",
                        title=f"Insecure Cookie: {cookie.name}",
                        description=f"Cookie '{cookie.name}' has security issues: {', '.join(issues)}",
                        evidence=f"Cookie: {cookie.name} | Issues: {', '.join(issues)}",
                        remediation="Set HttpOnly, Secure, and SameSite=Strict on all session cookies."
                    )
                else:
                    self._add_finding(
                        severity="INFO",
                        category="A02: Cryptographic Failures",
                        title=f"Cookie Secure: {cookie.name}",
                        description="Cookie has proper security attributes.",
                        evidence=f"Cookie '{cookie.name}' passed all security checks."
                    )

        except requests.RequestException as e:
            print(f"  [!] Cookie check error: {e}")

    # ── 3. Path Enumeration ────────────────────────────────────────────────
    def check_path_enumeration(self) -> None:
        print(f"\n[SCAN] Enumerating {len(SENSITIVE_PATHS)} sensitive paths...")

        def probe(path):
            try:
                resp = self.session.get(path, allow_redirects=False)
                return path, resp.status_code, len(resp.content)
            except Exception:
                return path, None, 0

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(probe, p): p for p in SENSITIVE_PATHS}
            for future in as_completed(futures):
                path, status, size = future.result()
                if status in (200, 301, 302, 403):
                    severity = "HIGH" if status == 200 else "MEDIUM" if status in (301, 302) else "LOW"
                    self._add_finding(
                        severity=severity,
                        category="A05: Security Misconfiguration",
                        title=f"Sensitive Path Accessible: {path}",
                        description=f"Path returned HTTP {status} (size: {size} bytes).",
                        evidence=f"GET {path} → {status}",
                        remediation="Restrict access to sensitive paths. Return 404 instead of 403 for hidden pages."
                    )

    # ── 4. XSS Testing ────────────────────────────────────────────────────
    def check_xss(self, search_path: str = "/search", param: str = "q") -> None:
        print(f"\n[SCAN] Testing XSS on {search_path} (param: {param})...")
        for payload in XSS_PAYLOADS:
            try:
                encoded = urllib.parse.urlencode({param: payload})
                resp = self.session.get(f"{search_path}?{encoded}")
                # Check if payload is reflected without encoding
                if payload in resp.text:
                    self._add_finding(
                        severity="HIGH",
                        category="A03: Injection",
                        title=f"Reflected XSS Vulnerability — {search_path}",
                        description=(
                            f"The parameter '{param}' reflects unsanitized input in the response. "
                            "An attacker can inject malicious scripts."
                        ),
                        evidence=f"Payload: {payload[:60]} | Reflected: YES",
                        remediation=(
                            "Encode all user-controlled output using context-aware escaping. "
                            "Implement a strict Content-Security-Policy."
                        )
                    )
                    break  # One confirmed XSS is enough per endpoint
                time.sleep(0.1)
            except requests.RequestException:
                pass

    # ── 5. SQL Injection Testing ───────────────────────────────────────────
    def check_sqli(self, login_path: str = "/login",
                   user_field: str = "email", pass_field: str = "password") -> None:
        print(f"\n[SCAN] Testing SQL Injection on {login_path}...")
        error_signatures = [
            "sql syntax", "mysql_fetch", "ora-", "postgresql",
            "sqlite", "syntax error", "unclosed quotation",
            "you have an error in your sql", "warning: mysql",
            "division by zero", "pg_query", "odbc_exec",
        ]

        for payload in SQLI_PAYLOADS:
            try:
                data = {user_field: payload, pass_field: "test123"}
                resp = self.session.post(login_path, data=data)
                body_lower = resp.text.lower()

                if any(sig in body_lower for sig in error_signatures):
                    self._add_finding(
                        severity="CRITICAL",
                        category="A03: Injection",
                        title=f"SQL Injection Vulnerability — {login_path}",
                        description=(
                            f"The field '{user_field}' appears vulnerable to SQL injection. "
                            "Database error messages were returned in the response."
                        ),
                        evidence=f"Payload: {payload} | DB error detected in response.",
                        remediation=(
                            "Use parameterized queries / prepared statements. "
                            "Never interpolate user input directly into SQL queries. "
                            "Disable detailed database error messages in production."
                        )
                    )
                    break
                time.sleep(0.1)
            except requests.RequestException:
                pass

    # ── 6. CSRF Check ─────────────────────────────────────────────────────
    def check_csrf(self, form_paths: list = None) -> None:
        print("\n[SCAN] Checking CSRF protection on forms...")
        if not form_paths:
            form_paths = ["/login", "/register", "/profile/update",
                          "/settings", "/password/change"]

        csrf_tokens = ["csrf_token", "_token", "authenticity_token",
                       "csrf", "__RequestVerificationToken", "csrfmiddlewaretoken"]

        for path in form_paths:
            try:
                resp = self.session.get(path)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                forms = soup.find_all("form")

                for form in forms:
                    has_csrf = False
                    for token_name in csrf_tokens:
                        if form.find("input", {"name": token_name}):
                            has_csrf = True
                            break
                    if not has_csrf:
                        action = form.get("action", path)
                        self._add_finding(
                            severity="HIGH",
                            category="A01: Broken Access Control",
                            title=f"Missing CSRF Token — {path}",
                            description=(
                                f"Form at '{path}' (action: {action}) does not contain a CSRF token. "
                                "An attacker can forge cross-site requests on behalf of authenticated users."
                            ),
                            evidence=f"Form HTML: {str(form)[:200]}...",
                            remediation=(
                                "Implement CSRF tokens on all state-changing forms. "
                                "Use SameSite=Strict cookie attribute as an additional layer."
                            )
                        )
            except requests.RequestException:
                pass

    # ── 7. Open Redirect ──────────────────────────────────────────────────
    def check_open_redirect(self) -> None:
        print("\n[SCAN] Testing for open redirects...")
        test_url = "https://evil.example.com"
        redirect_params = ["redirect", "url", "next", "return", "returnUrl",
                           "redirect_to", "goto", "target", "dest", "destination"]
        redirect_paths = ["/login", "/logout", "/auth"]

        for path in redirect_paths:
            for param in redirect_params:
                try:
                    full_url = f"{path}?{param}={urllib.parse.quote(test_url)}"
                    resp = self.session.get(full_url, allow_redirects=False)
                    location = resp.headers.get("Location", "")
                    if "evil.example.com" in location:
                        self._add_finding(
                            severity="HIGH",
                            category="A01: Broken Access Control",
                            title=f"Open Redirect — {path}?{param}=",
                            description=(
                                f"The parameter '{param}' at '{path}' redirects to arbitrary URLs. "
                                "Attackers can use this for phishing by crafting trusted-looking URLs."
                            ),
                            evidence=f"Location header: {location}",
                            remediation=(
                                "Validate redirect URLs against an allowlist of trusted domains. "
                                "Never redirect based on unvalidated user input."
                            )
                        )
                except requests.RequestException:
                    pass

    # ── 8. Sensitive Data Exposure ─────────────────────────────────────────
    def check_sensitive_data_exposure(self) -> None:
        print("\n[SCAN] Checking for sensitive data exposure...")
        # Check if .env or config files are accessible (already partly done in path enum)
        # Check API responses for over-exposed data
        api_paths = ["/api/users/me", "/api/profile", "/api/v1/user",
                     "/api/v2/me", "/graphql"]

        graphql_introspection_query = json.dumps({
            "query": "{ __schema { types { name fields { name } } } }"
        })

        for path in api_paths:
            try:
                # Try GraphQL introspection
                if "graphql" in path:
                    resp = self.session.post(
                        path,
                        data=graphql_introspection_query,
                        headers={"Content-Type": "application/json"}
                    )
                    if resp.status_code == 200 and "__schema" in resp.text:
                        self._add_finding(
                            severity="HIGH",
                            category="A02: Cryptographic Failures",
                            title="GraphQL Introspection Enabled",
                            description=(
                                "GraphQL introspection is enabled in production. "
                                "Attackers can enumerate the entire API schema."
                            ),
                            evidence=f"Introspection query succeeded at {path}",
                            remediation="Disable GraphQL introspection in production environments."
                        )
                else:
                    resp = self.session.get(path)
                    if resp.status_code == 200:
                        # Check for sensitive fields in JSON response
                        try:
                            body = resp.json()
                            body_str = json.dumps(body).lower()
                            for field in ["password", "hash", "token", "secret",
                                          "private_key", "ssn", "credit_card"]:
                                if field in body_str:
                                    self._add_finding(
                                        severity="CRITICAL",
                                        category="A02: Cryptographic Failures",
                                        title=f"Sensitive Field in API Response — {path}",
                                        description=(
                                            f"The API at '{path}' returns sensitive field: '{field}'. "
                                            "This data should never be included in API responses."
                                        ),
                                        evidence=f"Field '{field}' found in JSON response.",
                                        remediation=(
                                            "Apply field-level filtering. Use response DTOs "
                                            "that explicitly define safe-to-expose fields."
                                        )
                                    )
                        except ValueError:
                            pass
            except requests.RequestException:
                pass

    # ── 9. Authentication Brute-Force Protection ───────────────────────────
    def check_brute_force_protection(self, login_path: str = "/login") -> None:
        print("\n[SCAN] Testing brute-force protection (5 rapid attempts)...")
        attempt_count = 5
        blocked = False

        for i in range(attempt_count):
            try:
                resp = self.session.post(
                    login_path,
                    data={"email": "test@test.com", "password": f"wrongpass{i}"}
                )
                # Check for rate limiting indicators
                if resp.status_code in (429, 403):
                    blocked = True
                    self._add_finding(
                        severity="INFO",
                        category="A07: Identification & Authentication Failures",
                        title="Brute-Force Protection Detected",
                        description=f"Server returned HTTP {resp.status_code} after {i+1} failed attempts.",
                        evidence=f"HTTP {resp.status_code} on attempt #{i+1}"
                    )
                    break
                if "captcha" in resp.text.lower() or "too many" in resp.text.lower():
                    blocked = True
                    self._add_finding(
                        severity="INFO",
                        category="A07: Identification & Authentication Failures",
                        title="CAPTCHA / Rate Limiting Detected",
                        description="Server uses CAPTCHA or rate-limiting after repeated failed logins.",
                        evidence="'captcha' or 'too many' keyword found in response body."
                    )
                    break
                time.sleep(0.2)
            except requests.RequestException:
                pass

        if not blocked:
            self._add_finding(
                severity="HIGH",
                category="A07: Identification & Authentication Failures",
                title="No Brute-Force Protection on Login",
                description=(
                    f"Performed {attempt_count} rapid failed login attempts without triggering "
                    "any rate limiting, lockout, or CAPTCHA. Account enumeration and brute-force are possible."
                ),
                evidence=f"{attempt_count} consecutive failed logins accepted without throttling.",
                remediation=(
                    "Implement account lockout after N failed attempts. "
                    "Add exponential back-off delays. Deploy CAPTCHA on login forms. "
                    "Log and alert on suspicious login patterns."
                )
            )

    # ── 10. Run All Checks ─────────────────────────────────────────────────
    def run_all(self, profile_path: str = "/", login_path: str = "/login",
                search_path: str = "/search") -> list:
        print("\n" + "="*60)
        print("  STARTING FULL VULNERABILITY SCAN")
        print("="*60)
        self.check_security_headers(profile_path)
        self.check_cookie_security(login_path)
        self.check_path_enumeration()
        self.check_xss(search_path)
        self.check_sqli(login_path)
        self.check_csrf()
        self.check_open_redirect()
        self.check_sensitive_data_exposure()
        self.check_brute_force_protection(login_path)
        print("\n[✔] Scan complete.")
        return self.findings


# ─────────────────────────────────────────────
#  MAIN ENTRY POINT
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Facebook-Clone Security Scanner (Authorized Penetration Testing Only)"
    )
    parser.add_argument("--target", required=True, help="Target base URL (e.g., https://clone.local)")
    parser.add_argument("--profile", default="/profile/1", help="Profile path to scan for OSINT")
    parser.add_argument("--login-path", default="/login", help="Login endpoint path")
    parser.add_argument("--search-path", default="/search", help="Search endpoint path")
    parser.add_argument("--username", default="", help="Username/email for authenticated scan")
    parser.add_argument("--password", default="", help="Password for authenticated scan")
    parser.add_argument("--output", default="scan_results.json", help="Output JSON file path")
    parser.add_argument("--timeout", type=int, default=10, help="Request timeout in seconds")
    args = parser.parse_args()

    print("="*60)
    print("  Facebook-Clone Security Scanner")
    print("  FOR AUTHORIZED PENETRATION TESTING ONLY")
    print(f"  Target : {args.target}")
    print(f"  Time   : {datetime.utcnow().isoformat()}Z")
    print("="*60)

    # Initialize session
    session = SessionManager(args.target, timeout=args.timeout)

    # Authenticate if credentials provided
    authenticated = False
    if args.username and args.password:
        authenticated = session.authenticate(
            args.login_path, args.username, args.password
        )

    # Run OSINT
    osint = OSINTCollector(session)
    osint_data = osint.collect_profile(args.profile)

    # Run vulnerability scan
    scanner = VulnerabilityScanner(session)
    findings = scanner.run_all(
        profile_path=args.profile,
        login_path=args.login_path,
        search_path=args.search_path
    )

    # Compile full report
    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    for f in findings:
        severity_counts[f["severity"]] = severity_counts.get(f["severity"], 0) + 1

    report = {
        "report_metadata": {
            "target": args.target,
            "profile_path": args.profile,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "authenticated": authenticated,
            "total_findings": len(findings),
            "severity_summary": severity_counts,
        },
        "osint_data": osint_data,
        "vulnerability_findings": findings,
    }

    # Save to JSON
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n[✔] Report saved to: {args.output}")
    print(f"  CRITICAL: {severity_counts['CRITICAL']} | HIGH: {severity_counts['HIGH']} | "
          f"MEDIUM: {severity_counts['MEDIUM']} | LOW: {severity_counts['LOW']} | "
          f"INFO: {severity_counts['INFO']}")


if __name__ == "__main__":
    main()
