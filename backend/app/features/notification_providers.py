from __future__ import annotations

from app.schemas import DeliveryResult

# - destination comes from backend DISCORD_WEBHOOK_URL; it is not student-editable.
# - Require HTTPS, exact host discord.com and /api/webhooks/<id>/<token>; reject credentials,
#   query/fragment and nonstandard ports. Resolve DNS and reject private/loopback/link-local IPs.
# - POST JSON {"content": message} with Content-Type application/json, timeout 10s and redirects
#   disabled. Read only a bounded response. Keep URLs, tokens and raw provider responses private.
# - A 2xx response returns DeliveryResult(accepted=True,error_code=None). Invalid configuration,
#   rejected HTTP responses or network failures return accepted=False and a safe error code.
# - Send once. delivery_id identifies the stored delivery; duplicate prevention is in the database,
#   not a promise that the external provider deduplicates requests.
def send_discord(destination: str, message: str, delivery_id: str) -> DeliveryResult:
    raise NotImplementedError
