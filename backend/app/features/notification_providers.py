from __future__ import annotations

import ipaddress
import json
import re
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import build_opener, HTTPRedirectHandler, Request

from app.schemas import DeliveryResult


def valid_destination(destination: str) -> bool:
    try:
        url = urlsplit(destination)
        return (url.scheme == 'https' and url.hostname == 'discord.com' and url.port in (None, 443)
                and not url.username and not url.password and not url.query and not url.fragment
                and bool(re.fullmatch(r'/api/webhooks/\d+/[A-Za-z0-9_-]+', url.path)))
    except ValueError:
        return False


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def send_discord(destination: str, message: str, delivery_id: str) -> DeliveryResult:
    if not valid_destination(destination):
        return DeliveryResult(accepted=False, error_code='CHANNEL_UNAVAILABLE')
    try:
        addresses = socket.getaddrinfo('discord.com', 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(r[4][0]).is_global for r in addresses):
            return DeliveryResult(accepted=False, error_code='UNSAFE_DESTINATION')
        req = Request(destination, data=json.dumps({'content': message[:2000], 'allowed_mentions': {'parse': []}}).encode(),
                      headers={'Content-Type': 'application/json', 'User-Agent': 'OurSJSU/0.1'}, method='POST')
        with build_opener(NoRedirect()).open(req, timeout=10) as res:
            res.read(4096)
            return DeliveryResult(accepted=200 <= res.status < 300, error_code=None if 200 <= res.status < 300 else 'PROVIDER_REJECTED')
    except HTTPError:
        return DeliveryResult(accepted=False, error_code='PROVIDER_REJECTED')
    except (URLError, OSError, ValueError):
        return DeliveryResult(accepted=False, error_code='PROVIDER_UNREACHABLE')
