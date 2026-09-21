# Dart/Flutter network resilience

> **Scope: every Dart/Flutter service that makes HTTP requests** (mobile apps,
> desktop apps, backend clients). These are the network-resilience practices for
> Dart HTTP clients; the language-agnostic rules live in the
> [repo baseline](repo-baseline.md).

Transient network failures — a socket blip on a mobile connection, a momentary
5xx from an overloaded backend, a slow response that never arrives — are the
normal operating conditions of a networked client, not exceptional ones. A Dart
service that throws on the first error, with no timeout and no retry, turns every
such blip into a user-visible failure. This page codifies the fleet convention
for making Dart/Flutter HTTP calls resilient.

## Retry transient failures with exponential backoff

- **HTTP calls MUST retry transient failures with exponential backoff.** The
  fleet default is **3 retries** with delays growing from **~100 ms to ~1000 ms**
  (jittered). Retry only the errors that a retry can plausibly fix:
    - Socket/connection errors (`SocketException`, connection reset/refused).
    - `5xx` server errors.
    - Timeout errors (the request exceeded its deadline).
- **Never retry errors a retry cannot fix.** Do **not** retry `4xx` client
  errors (with the optional exception of `408 Request Timeout`), and never retry
  `401`/`403` authentication or authorization failures — retrying an unauthorized
  request just repeats the rejection and can trip rate limits or lockouts.
- Use the [`retry`](https://pub.dev/packages/retry) package (`0.3.x`) for the
  exponential-backoff wrapper, or hand-roll a small retry utility when adding a
  dependency is constrained. Either way, wrap `http.Client.get`/`post`/`delete`
  in a single retry helper rather than scattering ad-hoc `try`/`catch` retry
  loops across call sites.

## Configure explicit timeouts

- **Every HTTP client MUST set explicit timeouts** — never rely on the platform
  default (which is often unbounded). The fleet defaults are:
    - Connection timeout: **10–15 s**.
    - Read timeout: **30 s**.
- Apply per-request overrides where a specific call has a different deadline
  (e.g. a long-running upload). A request without a timeout is not a resilient
  request: it can hang indefinitely, and a hung request cannot be retried
  because the retry helper never regains control.

## Classify error types in the exception hierarchy

- **Distinguish transient (retryable) errors from fatal ones** in the service's
  exception hierarchy. The retry helper decides whether to retry by inspecting
  the error type, so the classification must be explicit rather than inferred
  from string matching on messages.
- **Let callers tell network failures apart from auth/validation failures.** A
  UI layer needs to show "you're offline, retrying…" for a transient error but
  "your session expired, please sign in" for a `401`. Collapsing both into one
  opaque exception type makes correct user-facing behavior impossible.

## Canonical source

Identified in [robotsix-mill](https://github.com/damien-robotsix/robotsix-mill)
at `lib/services/api_service.dart` (the `sendMessage` stream) and
`lib/services/update_service.dart` (`checkForUpdate`), where network calls throw
immediately on error with no timeout and no retry.

## Failure modes prevented

- **Transient blips become hard failures.** Without retry + backoff, a single
  dropped packet on a mobile network fails the whole request even though an
  immediate retry would have succeeded — the user sees an error for a condition
  that self-heals in milliseconds.
- **Requests hang forever.** Without explicit timeouts, a stalled connection
  leaves the request pending indefinitely; the UI spins with no error and no
  recovery, and the stuck request can never be retried.
- **Retry storms against unauthorized/invalid requests.** Retrying `4xx`/`401`/
  `403` responses repeats a request that will never succeed, wasting battery and
  bandwidth and risking rate-limit lockout.
- **Callers cannot react correctly.** When transient and fatal errors share one
  undistinguished type, the UI cannot decide whether to auto-retry silently or
  prompt the user to re-authenticate, so it does the wrong thing for one of them.
