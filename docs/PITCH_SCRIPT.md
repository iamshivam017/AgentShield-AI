# Five-minute pitch

## 0:00–0:30 — Problem

“AI agents can now initiate payments, but a technically valid payment can still violate the user’s intent. Existing fraud signals do not understand which agent acted, what authority it was delegated, or whether this purchase fits that mandate.”

## 0:30–1:00 — Why current controls miss it

“A transaction-only scorer sees ₹4,500 at a legitimate electronics merchant. AgentShield sees a new device, a first-time beneficiary, unusual behavior, and a ₹3,000 human-verification boundary. Agent context changes the correct intervention.”

## 1:00–1:30 — Solution

“AgentShield is a defense-first trust layer between an agent’s intent and Razorpay execution. ML predicts behavioral risk. Deterministic policy remains the authority. Ambiguous actions pause for a human. Every transition is explainable and auditable.”

## 1:30–3:15 — Live demo

1. Run **Trusted purchase**; open `ALLOW` evidence.
2. Run **Delegation edge**; inspect risk, policy, confidence, and audit events.
3. Approve the paused intent and create the Razorpay test order.
4. Run **Mandate violation**; show the hard block and inability to execute.

## 3:15–4:00 — Architecture, AI, and Razorpay

“The pipeline is feature engine → calibrated model → mandate policy → optional explanation. The LLM cannot decide or execute. If it is unavailable, deterministic evidence remains. Razorpay Orders is downstream of risk approval, and webhooks are verified over the raw body and deduplicated.”

## 4:00–4:35 — Measured results

Open the Model Evidence screen and repository evaluation report. State the exact generated precision, recall, F1, PR-AUC, false-positive cost, and assumptions from `docs/benchmark-results.json`. Emphasize the temporal held-out split and synthetic-data limitation.

## 4:35–5:00 — Close

“AgentShield is not an LLM deciding whether money should move. It is the bounded, measurable control layer that lets agentic commerce scale without giving an AI unrestricted authority over a user’s funds.”
