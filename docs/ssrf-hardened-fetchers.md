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

httpcore has no resolver hook on the connection pool: each connection calls
its **network backend's** `connect_tcp(host, port, ...)`, and the backend
resolves the hostname itself. That backend is therefore the one place where
the guard can see — and fix — the address actually connected to. A
fleet fetcher MUST:

1. **Subclass `httpcore.AsyncNetworkBackend`** (wrapping
   `httpcore.AnyIOBackend`). Its `connect_tcp` resolves the host with
   `getaddrinfo`, drops every address `_is_blocked` rejects, raises
   `httpcore.ConnectError` when none is left, and otherwise calls the wrapped
   backend's `connect_tcp` with the **validated IP literal** — never the
   hostname, so nothing re-resolves it. TLS SNI, certificate verification, and
   the `Host` header still use the original hostname: httpcore passes
   `server_hostname` to `start_tls` from the request origin, not from the
   socket address.
2. **Install the backend in an `httpcore.AsyncConnectionPool(network_backend=...,
   ssl_context=...)`** and route the httpx client through it. httpx's
   `AsyncHTTPTransport` accepts neither a `pool=` nor a `network_backend=`
   argument, so either write a small `httpx.AsyncBaseTransport` adapter or
   replace the transport's private `_pool` attribute as below — and pin httpx
   to the range the private attribute was verified against
   (`httpx>=0.28,<0.29`, `httpcore>=1.0,<2`).
3. **Disable proxies** — `trust_env=False` on the client and transport, no
   `proxy=`. Through a proxy, httpx connects to the *proxy* and the proxy
   resolves the attacker-chosen host itself, so the backend guard only ever
   validates the proxy's address.

`_is_blocked` rejects private, loopback, link-local, multicast, unspecified,
reserved and CGNAT (`100.64.0.0/10`) addresses, and unwraps IPv4 addresses
embedded in IPv6 — IPv4-mapped (`::ffff:a.b.c.d`), IPv4-compatible
(`::a.b.c.d`) and NAT64 (`64:ff9b::/96`) — before re-checking them.

```python
import ipaddress
import socket
import ssl
import typing

import anyio
import httpcore
import httpx

_EXTRA_BLOCKED = (ipaddress.ip_network("100.64.0.0/10"),)  # CGNAT, RFC 6598
_IPV4_EMBEDDING = (
    ipaddress.ip_network("64:ff9b::/96"),  # NAT64 well-known prefix, RFC 6052
    ipaddress.ip_network("::/96"),  # deprecated IPv4-compatible, RFC 4291
)


def _is_blocked(ip: str) -> bool:
    addr = ipaddress.ip_address(ip.split("%", 1)[0])  # drop any IPv6 zone id
    if isinstance(addr, ipaddress.IPv6Address):
        if addr.ipv4_mapped is not None:  # ::ffff:a.b.c.d
            return _is_blocked(str(addr.ipv4_mapped))
        if int(addr) > 1 and any(addr in net for net in _IPV4_EMBEDDING):
            return _is_blocked(str(ipaddress.IPv4Address(int(addr) & 0xFFFFFFFF)))
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_unspecified
        or addr.is_reserved
        or any(addr in net for net in _EXTRA_BLOCKED)
    )


async def _resolve(host: str, port: int) -> list[str]:
    infos = await anyio.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return [info[4][0] for info in infos]


class SSRFGuardBackend(httpcore.AsyncNetworkBackend):
    """Resolve, validate, then connect to the validated IP literal."""

    def __init__(self) -> None:
        self._inner = httpcore.AnyIOBackend()

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: typing.Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        allowed = [ip for ip in await _resolve(host, port) if not _is_blocked(ip)]
        if not allowed:
            raise httpcore.ConnectError(f"blocked by SSRF guard: {host!r}")
        # Connect to the address that was validated — never re-resolve `host`.
        return await self._inner.connect_tcp(
            allowed[0], port, timeout, local_address, socket_options
        )

    async def connect_unix_socket(self, *args, **kwargs):
        raise httpcore.ConnectError("blocked by SSRF guard: unix sockets")

    async def sleep(self, seconds: float) -> None:
        await self._inner.sleep(seconds)


class SSRFGuardTransport(httpx.AsyncHTTPTransport):
    # httpx>=0.28,<0.29: no pool=/network_backend= argument, so the guarded
    # pool replaces the private `_pool` attribute. Re-verify on every bump.
    def __init__(self, ssl_context: ssl.SSLContext | None = None) -> None:
        super().__init__(trust_env=False)
        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=ssl_context or httpx.create_ssl_context(),
            network_backend=SSRFGuardBackend(),
        )


_client = httpx.AsyncClient(
    transport=SSRFGuardTransport(),
    trust_env=False,  # no env proxy: a proxy would resolve the host itself
    timeout=httpx.Timeout(10.0),
)
```

httpcore maps the backend's `httpcore.ConnectError` to `httpx.ConnectError`,
so callers see an ordinary connection failure. Because the backend connects to
the exact address it just validated, there is no window between the check and
the connection for DNS to change under the tool's feet. Pinning the IP — not
re-resolving the hostname — is what closes the TOCTOU gap.

**Prove the guard runs.** A guard that is wired wrong (an override nothing
calls) fails open and looks identical to a working one until it is exploited.
Every fetcher MUST ship a test that a fetch to `http://127.0.0.1:<port>/` and
to a hostname resolving to `169.254.169.254` both raise:

```python
import httpx
import pytest

import fetcher  # the module defining _client and _resolve above


@pytest.mark.anyio
async def test_guard_blocks_loopback_literal():
    with pytest.raises(httpx.ConnectError, match="SSRF guard"):
        await fetcher._client.get("http://127.0.0.1:8080/")


@pytest.mark.anyio
async def test_guard_blocks_hostname_resolving_to_metadata(monkeypatch):
    async def resolve_to_metadata(host: str, port: int) -> list[str]:
        return ["169.254.169.254"]

    monkeypatch.setattr(fetcher, "_resolve", resolve_to_metadata)
    with pytest.raises(httpx.ConnectError, match="SSRF guard"):
        await fetcher._client.get("http://rebind.example/latest/meta-data/")
```

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

- rely on the guarded network backend, so that **every** connection —
  including each redirect hop — flows through its `connect_tcp` and is
  re-validated for free; or
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
  guarded network backend re-validates the redirect target's address before
  connecting.
- **Cloud metadata exfiltration.** `169.254.169.254` (link-local) and other
  internal ranges are rejected at the moment of connection, so instance
  credentials and metadata cannot be read through the fetcher.
- **IPv4-in-IPv6 bypass.** An address like `::ffff:127.0.0.1`,
  `::127.0.0.1` or `64:ff9b::a9fe:a9fe` (NAT64 for `169.254.169.254`) sneaks
  an internal target past an IPv4-only check; unwrapping the embedded IPv4
  address and re-checking it closes that hole.
- **Proxy bypass.** With an environment proxy, httpx connects to the proxy and
  the proxy resolves the attacker's host, so the backend only ever validates
  the proxy. `trust_env=False` keeps the connection — and the check — local.
- **A guard that never runs.** An override of a method httpcore does not call
  (such as a nonexistent `AsyncConnectionPool._resolve_host`) lets every
  request through while looking compliant in review. The mandatory
  loopback/metadata tests fail as soon as the guard is not on the connection
  path.

## How this is enforced

Enforcement is by code review and the periodic standards-audit agent; there is
no standalone machine check, because "the address validated is the address
connected to" is a property of the transport wiring, not a grep-able string.
An auditor (human or agent) applies these criteria to every tool that fetches
an attacker-influenced URL:

- **Connection-layer validation.** The fetcher's `httpx` client is wired to a
  guarded **network backend** — an `httpcore.AsyncNetworkBackend` subclass
  (e.g. `SSRFGuardBackend`) whose `connect_tcp` rejects private, loopback,
  link-local, multicast, unspecified, reserved, CGNAT and IPv4-embedded
  addresses and connects to the validated IP literal — installed through
  `httpcore.AsyncConnectionPool(network_backend=...)`, or an equivalent
  connection-layer control. A tool that only performs a pre-flight
  `getaddrinfo`/`socket` check before an unguarded transport fails this
  criterion, and so does any override of a method httpcore never calls (e.g.
  `AsyncConnectionPool._resolve_host`, which does not exist).
- **No proxy.** The client and transport set `trust_env=False` and pass no
  `proxy=`; a proxied fetcher fails this criterion.
- **Guard test.** The repo has a test asserting that a fetch to
  `http://127.0.0.1:<port>/` and to a hostname resolving to `169.254.169.254`
  both raise. Without it, a no-op guard cannot be told apart from a working
  one, and the fetcher fails this criterion.
- **Redirect re-validation.** Redirect hops are re-validated: either the
  guarded backend handles every hop (so `connect_tcp` runs on each redirect
  target), or the tool sets `follow_redirects=False` and re-runs the
  connection-layer check on each hop explicitly. A tool that combines
  `follow_redirects=True` with an unguarded transport fails this criterion.

New outbound-fetch tools MUST route through the shared
`robotsix_chat/common/http_fetch.py` helper (or reproduce its guarded network
backend);
reviewers reject a fetcher that opens its own unguarded client.

## Reference

- OWASP Top 10 — [A01:2025 Broken Access Control](https://owasp.org/Top10/2025/A01_2025-Broken_Access_Control/)
  (SSRF was merged into A01 in 2025; it was A10:2021).
- OWASP — [Server-Side Request Forgery Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html).
