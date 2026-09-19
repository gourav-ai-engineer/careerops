from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

from app.settings import settings


@dataclass(frozen=True)
class LiveSourceCheck:
    status: str
    requested_url: str
    final_url: str | None
    http_status: int | None
    title: str | None
    reason: str


def _is_public_hostname(host: str) -> bool:
    if not host or host.lower() == "localhost":
        return False
    try:
        ip = ipaddress.ip_address(host)
        return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved)
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError:
        return False
    for item in infos:
        ip = ipaddress.ip_address(item[4][0])
        if not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved):
            return True
    return False


def _host_allowed(host: str, company_domain: str) -> bool:
    host = host.lower().removeprefix("www.")
    domain = company_domain.lower().removeprefix("www.")
    return host == domain or host.endswith("." + domain)


def _page_title(html: str) -> str | None:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.I | re.S)
    return " ".join(match.group(1).split())[:300] if match else None


async def check_official_source(url: str, company_domain: str) -> LiveSourceCheck:
    parts = urlsplit(url)
    if parts.scheme.lower() != "https" or not parts.hostname:
        return LiveSourceCheck("rejected", url, None, None, None, "Only HTTPS URLs are accepted")
    if not _host_allowed(parts.hostname, company_domain):
        return LiveSourceCheck("needs_review", url, None, None, None, "URL host is outside the employer domain")
    if not _is_public_hostname(parts.hostname):
        return LiveSourceCheck("rejected", url, None, None, None, "Target host is not publicly routable")
    headers = {"User-Agent": "CareerOps/1.0 (+official-source-check)"}
    async with httpx.AsyncClient(timeout=settings.http_timeout_seconds, follow_redirects=True, max_redirects=5, headers=headers) as client:
        response = await client.get(url)
    final = str(response.url)
    final_host = urlsplit(final).hostname or ""
    if not _host_allowed(final_host, company_domain):
        return LiveSourceCheck("rejected", url, final, response.status_code, None, "Redirect left the employer domain")
    title = _page_title(response.text)
    if 200 <= response.status_code < 400:
        return LiveSourceCheck("screened", url, final, response.status_code, title, "HTTPS source is reachable and remained on the employer domain")
    return LiveSourceCheck("needs_review", url, final, response.status_code, title, f"Employer-domain source returned HTTP {response.status_code}")
