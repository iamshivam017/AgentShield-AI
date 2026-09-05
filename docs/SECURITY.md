# Security and fintech safety review

Review date: 2026-09-05

## Implemented controls

| Area | Control |
|---|---|
| Secrets | Environment-only configuration; `.env`, keys, models, databases, and logs ignored |
| Authentication | Short-lived issuer/audience-bound HS256 JWT; PBKDF2-HMAC-SHA256 passwords at 600k rounds |
| Authorization | Role gates on read, policy mutation, verification, and execution endpoints |
| Object state | Server loads and revalidates persisted state; client decisions are never trusted |
| Input | Strict Pydantic bounds, currency format, idempotency-key syntax, control-character rejection |
| Payments | Integer paise, explicit test-mode guard, risk gate before order creation |
| Webhooks | HMAC-SHA256 over raw request body, constant-time comparison, persistent deduplication |
| Replay | Unique idempotency keys and webhook event IDs |
| Browser | Strict TypeScript, escaped React rendering, no raw HTML, security headers |
| API abuse | Per-client bounded request window and request-size bounds from schema/server |
| CORS | Explicit origins, methods, and headers; credentials disabled |
| LLM | Untrusted text serialized as data; no tools; strict output; short timeout; safe fallback |
| Logging | Structured logs without credentials or payment payloads; request/correlation identifiers |
| Containers | Non-root runtime users, minimal images, health check |

## Threat review

The detailed STRIDE-oriented risk inventory is in `threat-model.md`. Critical invariants are covered by unit and integration tests: blocked payments cannot execute, authorization is required, verification is state-limited, invalid webhook signatures fail, and duplicates are idempotent.

## Residual risks

- The in-memory rate limiter is suitable for a single demo instance; distributed deployment requires Redis or gateway enforcement.
- Local demo auth is intentionally seeded and must be disabled or replaced with managed identity in production.
- JWT revocation is not implemented; the short TTL limits exposure but a production deployment needs rotation/revocation strategy.
- Real Razorpay test credentials and webhook delivery are not available in the build environment, so the HTTP adapter is contract-tested and requires one manual sandbox verification.
- Synthetic inputs cannot demonstrate real population bias, drift, or fraud prevalence.

## Security release commands

```bash
git grep -nEi '(api[_-]?key|secret|token|password).{0,20}[=:].{8,}' -- ':!*.example' ':!package-lock.json'
npm audit --omit=dev
python -m pip check
```
