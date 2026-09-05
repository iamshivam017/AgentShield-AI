# Product requirements document

## Problem

AI commerce agents can initiate payments that are technically valid yet violate the user's delegated intent. Traditional transaction fraud scoring lacks agent identity, mandate utilization, purpose, and human delegation context. A merchant or payment platform needs a control plane between agent intent and payment execution.

## Users

- **Primary:** risk analyst or operations lead responsible for agent-initiated payment safety.
- **Secondary:** merchant developer integrating a commerce agent with Razorpay test-mode APIs.
- **Affected end user:** the person delegating a bounded purchasing mandate.

## Product

AgentShield accepts structured payment intents, adds behavioral context, produces an ML anomaly probability, enforces an agent-specific payment mandate, and returns `ALLOW`, `VERIFY`, or `BLOCK`. Approved intents can create a Razorpay test order. Every decision and state transition is auditable.

## AI advantage

Rules are strong at known boundaries but brittle for combinations such as a moderately elevated amount, new device, unfamiliar merchant, unusual hour, and short-window velocity. The ML layer estimates joint behavioral risk across these signals. Deterministic policy remains authoritative for hard financial boundaries, while the optional language model only renders constrained explanations from trusted evidence.

## Razorpay advantage

Razorpay is the execution boundary, not decorative checkout. The adapter creates an Order only after AgentShield's risk state permits it; signed webhooks update the audit trail; test credentials determine test mode; integer subunits preserve money safety. This demonstrates a trust layer suitable for Razorpay's emerging agentic payments surface.

## Outcome and metrics

**North-star metric:** anomalous-payment value prevented without unacceptable legitimate-payment friction.

Supporting metrics: held-out precision, recall, F1, PR-AUC, false-positive rate, estimated review cost, false-negative exposure, verification rate, block rate, and decision latency.

## Journeys

### Primary journey

Agent submits intent → features computed → ML score produced → mandate applied → decision recorded → allow executes, verify pauses for analyst, or block terminates.

### Demo journey

Run trusted, delegation-edge, and hard-violation scenarios; inspect the evidence and audit timeline; approve the verification case; create a Razorpay test order; show held-out metrics and a safe provider-failure path.

### Failure journey

If the explanation provider fails, the deterministic explanation is returned. If Razorpay times out, the state becomes `PAYMENT_FAILED`, no success is claimed, and an audit event is recorded. Duplicate intents and webhooks are idempotently ignored.

## Differentiation

AgentShield models agent authority in addition to transaction anomaly. It exposes evidence and policy provenance, provides a real human verification transition, generates measurable cost-aware performance, and prevents AI text from obtaining payment authority.

## Non-goals

No real customer data, card storage, KYC, offensive fraud capability, real-money autonomy, foundation-model training, production certification, or attempt to replace Razorpay's own fraud controls.
