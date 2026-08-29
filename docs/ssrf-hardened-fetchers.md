# SSRF-hardened httpx fetchers

> **Scope: every fleet tool that fetches attacker-influenced URLs over httpx.**
> Any tool that takes a URL from a user, a chat message, a webhook payload, or
> any other untrusted source and fetches, probes, or renders it (today:
> `robotsix_chat`'s `public_fetch` and `http_probe`; the pattern applies to any
> future fetch/probe/render tool). This applies *in addition to* the
> [HTTP client persistence](http-client-persistence.md) standard and the
> [security posture](security-posture.md).

A tool that fetches an attacker-supplied URL is a Server-Side Request Forgery
(SSRF) sink: without a guard, an attacker points it at `169.254.169.254`
(cloud metadata), `127.0.0.1`, or an internal service and reads a response the
attacker could never reach directly. The common defence — resolve the hostname
with `socket.getaddrinfo`, check the IP is public, then hand the hostname to
httpx — is **not sufficient**. It leaves a time-of-check-to-time-of-use
(TOCTOU) gap: httpx re-resolves the hostname independently when it opens the
connection, so an attacker-controlled DNS server with a sub-second TTL can
return a public IP for the pre-flight check and `169.254.169.254` /
`127.0.0.1` for the actual connection. This is classic DNS-rebinding, and
OWASP's SSRF Prevention Cheat Sheet calls it out explicitly: *"a DNS
resolution will be made when the business code will be executed"*.

## The rule

**SSRF-hardened httpx fetchers MUST enforce the allow/deny decision at the
*connection* layer, not (only) in a pre-flight check, so the address that is
validated is provably the address that is connected to.** A pre-flight
`getaddrinfo` check is defence-in-depth at best; it is never the sole control.

### 1. Validate and pin the resolved IP at the connection layer

Subclass `httpcore.AsyncConnectionPool` and override `_resolve_host` to reject
private, loopback, link-local, multicast, unspecified, and IPv4-mapped
addresses, returning only the validated entries. httpcore caches the resolved
entry keyed by `(host, port, ssl)`, so httpx connects to exactly the validated
IP — while the `Host` header and TLS SNI keep the original hostname, so
certificate verification stays intact. Install the guarded pool via
`httpx.AsyncHTTPTransport(pool=...)`.

```python
import ipaddress

import httpcore
import httpx


def _is_blocked(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_unspecified
        or addr.is_reserved
        or (isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None)
    )


class SSRFGuardPool(httpcore.AsyncConnectionPool):
    async def _resolve_host(self, origin: httpcore.Origin) -> list[dict]:
        entries = await super()._resolve_host(origin)
        allowed = [e for e in entries if not _is_blocked(e["addr"][0])]
        if not allowed:
            raise httpx.ConnectError("blocked by SSRF guard: no public address")
        return allowed


_transport = httpx.AsyncHTTPTransport(pool=SSRFGuardPool())
_client = httpx.AsyncClient(transport=_transport, timeout=httpx.Timeout(10.0))
```

Because the validated entry is what httpcore caches and connects to, there is
no window between the check and the connection for DNS to change under the
tool's feet. Pinning the IP — not re-resolving the hostname — is what closes
the TOCTOU gap.

```python
# ❌  Pre-flight check only — TOCTOU / DNS-rebinding gap
import socket

import httpx


def fetch(url: str) -> httpx.Response:
    host = httpx.URL(url).host
    ip = socket.getaddrinfo(host, None)[0][4][0]  # checked here...
    if _is_blocked(ip):
        raise ValueError("blocked")
    return httpx.get(url)  # ...but httpx re-resolves here — different answer
```

### 2. Re-validate every redirect hop

An auto-followed redirect to an internal endpoint bypasses a check that only
looks at the original URL. Every fetcher MUST either:

- rely on the guarded pool, so that **every** connection — including each
  redirect hop — flows through `_resolve_host` and is re-validated for free; or
- set `follow_redirects=False` and re-run the connection-layer check on each
  hop explicitly before following it.

Never combine `follow_redirects=True` with an unguarded transport and a
pre-flight-only check: the redirect target is fetched without ever being
validated.

## Why this is a fleet standard

The shared helper `robotsix_chat/common/http_fetch.py` already consolidates
SSRF logic for two tools, and any new outbound-fetch tool in any fleet repo
faces the same TOCTOU and redirect surface. Codifying "validate at the
connection layer, pin the resolved IP, re-validate redirects" as a single
standard prevents each tool from re-implementing a subtly-unsafe pre-flight
check.

## Failure modes this prevents

- **DNS rebinding (TOCTOU).** An attacker DNS server returns a public IP for
  the pre-flight `getaddrinfo` and a private IP (`169.254.169.254`,
  `127.0.0.1`) for the connection httpx opens a moment later. Connection-layer
  validation pins the address that was checked, so the two can never diverge.
- **Redirect-based SSRF.** A public URL 302-redirects to an internal endpoint.
  A check that only inspects the original URL follows the redirect blindly; a
  guarded pool re-validates the redirect target's address before connecting.
- **Cloud metadata exfiltration.** `169.254.169.254` (link-local) and other
  internal ranges are rejected at the moment of connection, so instance
  credentials and metadata cannot be read through the fetcher.
- **IPv4-mapped IPv6 bypass.** An address like `::ffff:127.0.0.1` sneaks a
  loopback target past an IPv4-only string check; unwrapping the mapped
  address and re-checking it closes that hole.

## Reference

- OWASP — [Server-Side Request Forgery Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html).
