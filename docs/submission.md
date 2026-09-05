# Razorpay Buildathon submission notes

## Track alignment

AgentShield targets Track 02 — AI Risk Manager and focuses on unauthorized or anomalous AI-initiated payments. It detects the loss class, pauses risky actions for verification, blocks mandate violations, and explains each decision.

## Evidence package

- Working web dashboard and API
- Reproducible held-out benchmark with precision, recall, F1, confusion matrix, and false-positive cost
- Architecture and trust-boundary documentation
- Threat model and operational runbook
- Razorpay test-mode adapter and signed webhook handler
- Five-minute demo flow documented in `docs/DEMO_SCRIPT.md`

Final metrics are recorded in `docs/EVALUATION.md`. A public deployment URL and
recorded video remain submission-portal actions because no hosting or recording
account is connected to this workspace.
