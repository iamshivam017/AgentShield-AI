# Threat model

## Protected assets

- User funds and payment mandates
- Beneficiary and transaction metadata
- Verification challenges and access tokens
- Decision integrity and audit history
- Razorpay credentials and webhook authenticity

## Primary threats and mitigations

| Threat | Mitigation |
|---|---|
| Prompt-injected agent requests a payment | Payload is data only; deterministic policy is authoritative |
| Amount/velocity mandate abuse | Hard per-payment, daily, and velocity limits |
| New beneficiary fraud | Trust history feature plus mandatory verification above threshold |
| Replay or duplicate execution | Required idempotency key and persisted uniqueness constraint |
| Forged payment status | Razorpay webhook signature verification |
| Model evasion or drift | Policy floor, feature bounds, benchmark monitoring, model version audit |
| LLM hallucinated approval | LLM output has no decision or execution capability |
| Credential leakage | Environment-only secrets, redacted logs, secret scanning in CI |
| Audit tampering | Append-only events and stable correlation identifiers |

## Explicit non-goals

AgentShield is a buildathon defense prototype. It does not claim regulatory certification, replace a payment processor's fraud controls, or authorize real-money operation without an independent security review.
