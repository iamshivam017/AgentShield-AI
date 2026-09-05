# Deterministic demo runbook

## Preparation

1. Copy `.env.example` to `.env`; keep Razorpay credentials blank for deterministic demo mode or add test credentials.
2. Run `docker compose up --build` or start the API and web app with `make api` and `make web`.
3. Open <http://localhost:3000> and sign in with the seeded analyst account.
4. Confirm the header says `TEST MODE`.

## Exact clicks

1. Select **Run** beside **Trusted purchase**. Open the resulting drawer; show `ALLOW`, confidence, evidence, and the three baseline audit events.
2. Close the drawer. Select **Run** beside **Delegation edge**. Explain why ₹4,500 crosses the ₹3,000 verification threshold even if ML risk is not a hard block.
3. Select **Approve intent**, then **Create Razorpay test order**. Point to the audited `payment.order_created` event. When keys are blank the returned ID begins `order_demo_` and is visibly a demo stand-in—not a claimed network success.
4. Close the drawer. Select **Run** beside **Mandate violation**. Show the blocked category/mandate evidence and the absence of an execution action.
5. Open **Policies**. Change a numeric threshold and select **Commit policy change**; run the edge scenario again to demonstrate deterministic authority.
6. Open **Evidence** and explain the temporal split, compared models, and cost assumptions.

## Failure path

Set invalid Razorpay test credentials and execute an approved intent. The UI displays **Safe failure**, the API returns 503 without claiming a charge, and the audit timeline records `payment.create_failed`. Restore or clear credentials afterward.

## Reset

For a clean SQLite demo, stop services and remove the ignored `services/api/agentshield.db`; startup recreates and seeds the schema. For Docker Compose, remove only the project volume if a full reset is desired.
