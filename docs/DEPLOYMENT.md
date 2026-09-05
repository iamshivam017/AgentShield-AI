# Deployment runbook

## Required configuration

Use a managed secret store for `JWT_SECRET`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`, and any optional LLM key. Keep `RAZORPAY_TEST_MODE=true` for the buildathon. Configure `DATABASE_URL` for PostgreSQL and set exact HTTPS dashboard origins in `CORS_ORIGINS`.

## Release order

1. Build pinned web and API container images.
2. Run `alembic upgrade head` as a one-off release task.
3. Start the API and verify `/health/live` and `/health/ready`.
4. Start the web service with `NEXT_PUBLIC_API_URL` set at build time.
5. Terminate TLS at the platform ingress.
6. Configure the Razorpay test webhook URL as `https://<api-host>/api/v1/webhooks/razorpay` and use the same secret in the platform secret store.
7. Send one Razorpay test event, verify the audit entry, and confirm a replay returns `duplicate_ignored`.

## Rollback

Deploy the previous application image. Database downgrades are not automatic; review migration compatibility before a rollback. The initial migration is additive and can remain in place.

## Health and observability

- Liveness: `/health/live`
- Readiness: `/health/ready`
- Prometheus: `/metrics`
- Logs: structured JSON to stdout
- Correlation: `X-Request-ID` response header plus transaction correlation ID

## Manual buildathon deployment actions

The repository is deployable with Docker Compose, but this environment has no connected hosting account, domain, database, or Razorpay credentials. See the final audit for the minimal external steps.

For a non-local API URL, pass it while building the web image:

```bash
NEXT_PUBLIC_API_URL=https://api.example.com/api/v1 docker compose build web
```
