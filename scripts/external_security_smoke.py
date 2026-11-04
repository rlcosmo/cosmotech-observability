"""Bounded, credential-free checks intended for a GitHub-hosted runner."""

from __future__ import annotations

import concurrent.futures
import json
import socket
import urllib.error
import urllib.request
from pathlib import Path

DOMAIN = "cosmotechsolutions.com.br"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def response(url: str, *, headers: dict[str, str] | None = None) -> tuple[int, str]:
    """Verify TLS normally and return redirects without following them."""
    opener = urllib.request.build_opener(NoRedirect)
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with opener.open(request, timeout=20) as result:
            return result.status, result.headers.get("Location", "")
    except urllib.error.HTTPError as error:
        return error.code, error.headers.get("Location", "")


def closed_port(port: int) -> dict[str, object]:
    """Check the ALB hostname only; do not scan arbitrary networks."""
    try:
        with socket.create_connection((f"glpi.{DOMAIN}", port), timeout=3):
            return {"check": f"public-port-{port}", "passed": False}
    except (TimeoutError, ConnectionRefusedError, OSError):
        return {"check": f"public-port-{port}", "passed": True}


def main() -> None:
    results: list[dict[str, object]] = []
    for host in [f"glpi.{DOMAIN}", f"kestra.{DOMAIN}"]:
        code, location = response(f"http://{host}/")
        results.append({
            "check": f"{host}-https-redirect",
            "passed": code in [301, 302, 307, 308] and location.startswith(f"https://{host}"),
            "status": code,
        })
    checks = [
        (f"https://glpi.{DOMAIN}/", 200),
        (f"https://glpi.{DOMAIN}/api.php/v2/Assistance/Ticket", 401),
        (f"https://kestra.{DOMAIN}/api/v1/instance", 401),
        (f"https://grafana.{DOMAIN}/login", 200),
        (f"https://argocd.{DOMAIN}/", 200),
        (f"https://argocd.{DOMAIN}/api/v1/applications", 401),
        (f"https://grafana.{DOMAIN}/api/search", 401),
        (f"https://prometheus-aws-eks-istio-lab-dev.{DOMAIN}/", 403),
        (f"https://alertmanager.{DOMAIN}/", 403),
        (f"https://tempo.{DOMAIN}/", 403),
    ]
    for url, expected in checks:
        code, _ = response(url)
        results.append({"check": url, "passed": code == expected, "status": code})
    code, _ = response(f"https://glpi.{DOMAIN}/", headers={"Host": "unrouted.invalid"})
    results.append({"check": "waf-unknown-host", "passed": code == 403, "status": code})
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        results.extend(pool.map(closed_port, [8080, 8081, 8088, 3306, 5432, 6443, 6379, 30080]))
    Path("external-security-evidence.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))
    if not all(result["passed"] for result in results):
        raise SystemExit("External security checks failed; inspect evidence.")


if __name__ == "__main__":
    main()
