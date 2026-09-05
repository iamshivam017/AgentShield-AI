# AgentShield architecture

## System architecture

```mermaid
flowchart TB
  subgraph Client
    A[Risk dashboard]
    B[Commerce agent]
  end
  subgraph Control[AgentShield control plane]
    C[FastAPI + RBAC]
    D[Feature + ML engine]
    E[Policy engine]
    F[Explanation adapter]
    G[Audit service]
  end
  subgraph Data
    H[(PostgreSQL)]
    I[Prometheus metrics]
  end
  J[Razorpay test APIs]
  B --> C
  A --> C
  C --> D --> E
  E --> F
  E --> G
  C --> H
  G --> H
  C --> I
  E -->|approved only| J
  J -->|signed webhook| C
```

## Core user workflow

```mermaid
sequenceDiagram
  participant Agent
  participant Shield as AgentShield
  participant Analyst
  participant Rzp as Razorpay Test
  Agent->>Shield: Payment intent + idempotency key
  Shield->>Shield: Score behavior + enforce mandate
  alt Low risk
    Shield-->>Agent: ALLOW
    Analyst->>Shield: Execute approved intent
  else Ambiguous
    Shield-->>Analyst: VERIFY + evidence
    Analyst->>Shield: Approve or block
  else Hard violation
    Shield-->>Agent: BLOCK + reason
  end
  opt Approved intent
    Shield->>Rzp: Create test Order
    Rzp-->>Shield: Order result
  end
```

## AI decision workflow

```mermaid
flowchart TD
  A[Validated intent] --> B[Historical features]
  B --> C[Calibrated model]
  C --> D[Risk probability]
  D --> E[Mandate checks]
  E --> F{Final decision}
  F -->|Evidence only| G[Structured explanation]
  G --> H[Schema validation]
  H --> I[Audit + response]
  G -. timeout .-> J[Deterministic fallback]
  J --> I
```

## Razorpay event workflow

```mermaid
sequenceDiagram
  participant UI as Operator UI
  participant API as AgentShield API
  participant Rzp as Razorpay Orders API
  participant Hook as Webhook endpoint
  UI->>API: Execute risk-approved intent
  API->>API: Recheck state + idempotency
  API->>Rzp: POST /v1/orders (test credentials)
  Rzp-->>API: order_id or error
  API-->>UI: created or failed-safe
  Rzp->>Hook: payment event + HMAC signature
  Hook->>Hook: Verify raw body and deduplicate event
  Hook->>API: Append audit transition
```

## Failure and recovery

```mermaid
flowchart TD
  A[Dependency call] --> B{Result}
  B -->|LLM timeout| C[Deterministic explanation]
  B -->|Razorpay error| D[PAYMENT_FAILED]
  B -->|Duplicate intent| E[Return original decision]
  B -->|Duplicate webhook| F[Ignore safely]
  C --> G[Audited response]
  D --> G
  E --> G
  F --> G
```

## Deployment

Docker Compose runs a non-root Next.js container, a non-root FastAPI container, and PostgreSQL 16. The API exposes liveness, readiness, and Prometheus endpoints. A production deployment must terminate TLS, set a rotated JWT secret, configure exact CORS origins, run Alembic migrations before application rollout, and provide Razorpay test credentials through a secret store.

## State authority

- Clients never submit risk scores, decisions, payment status, or Razorpay identifiers.
- Payment amounts use integer paise throughout.
- `BLOCK` is terminal for a payment intent.
- `VERIFY` requires an authorized analyst transition.
- Razorpay calls only accept `APPROVED` state and record the returned order ID.
- Webhook state is accepted only after raw-body HMAC verification and event deduplication.
