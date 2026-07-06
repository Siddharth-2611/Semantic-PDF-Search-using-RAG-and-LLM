"""
Turns raw request metadata (User-Agent header, client IP) into the
human-readable "device + location" pair shown in login notification
emails.

Geolocation uses ip-api.com's free endpoint — no API key required, which
keeps local setup dependency-free. It correctly fails soft on private/
loopback IPs (localhost during local dev), returning a clear placeholder
instead of a confusing error.
"""
import logging

import httpx
from user_agents import parse as parse_user_agent

logger = logging.getLogger(__name__)

_PRIVATE_IP_PREFIXES = ("127.", "10.", "192.168.", "::1", "localhost")


def get_device_name(user_agent_string: str | None) -> str:
    if not user_agent_string:
        return "Unknown device"
    ua = parse_user_agent(user_agent_string)
    browser = ua.browser.family or "Unknown browser"
    os_name = ua.os.family or "Unknown OS"
    os_version = ua.os.version_string
    os_label = f"{os_name} {os_version}".strip() if os_version else os_name
    return f"{browser} on {os_label}"


def _is_private(ip_address: str) -> bool:
    return any(ip_address.startswith(p) for p in _PRIVATE_IP_PREFIXES)


def get_location(ip_address: str) -> str:
    if not ip_address or _is_private(ip_address):
        return "Local network (unavailable)"

    try:
        resp = httpx.get(f"http://ip-api.com/json/{ip_address}", timeout=3.0)
        data = resp.json()
        if data.get("status") == "success":
            city = data.get("city", "")
            country = data.get("country", "")
            return ", ".join(part for part in [city, country] if part) or "Unknown location"
        return "Unknown location"
    except Exception:
        logger.exception("Geolocation lookup failed for %s", ip_address)
        return "Location unavailable"


def get_client_ip(request) -> str:
    """
    Prefers X-Forwarded-For (set by reverse proxies) over the raw socket
    address, since in production the socket address is often the proxy's
    own IP rather than the real client's.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
