# Buildathon requirement traceability

Official source reviewed 2026-09-05: [Razorpay AI Buildathon](https://razorpay.com/buildathon/).

## Track decision

Track 02 remains the strongest fit. AgentShield prevents one explicit loss class—unauthorized or anomalous AI-initiated payments—using a working detector, verifier, safe responder, and held-out evaluation. Track 01 is adjacent but would judge revenue growth or complete AI-buyer commerce; Track 02 directly rewards the system's strongest assets: payment-risk modeling, delegation policy, explainability, and measurable classification quality.

## Matrix

| Requirement | Implemented feature | Status | Gap / fix | Test or evidence |
|---|---|---|---|---|
| Pick a track | Track 02 — AI Risk Manager | PASS | None | README, PRD |
| One class of merchant loss | Unauthorized/anomalous agent payments | PASS | None | PRD scope, scenario suite |
| Working detector | Calibrated logistic-regression behavioral scorer | PASS | Synthetic domain only | `test_benchmark.py`, benchmark JSON |
| Working verifier | `VERIFY` state with analyst approve/block transition | PASS | Production identity provider deferred | API integration and E2E tests |
| Auto-responder | Hard blocks and safe allow/execute gate | PASS | Live money intentionally excluded | Policy and API tests |
| Precision on held-out test | Temporal 15% untouched test partition | PASS | Final value generated at release gate | `make benchmark` |
| Recall on held-out test | Same evaluation harness | PASS | Final value generated at release gate | `docs/EVALUATION.md` |
| Honest false-positive cost | ₹150 review-friction assumption reported | PASS | Assumption needs merchant calibration | Threshold table and JSON |
| Strictly defense-only | No offensive data, tools, or evasion features | PASS | None | Threat model and code review |
| Public repository | Public GitHub repository | PASS | Final branch must be pushed | GitHub remote verification |
| Five-minute pitch | Timed pitch script | PASS | Record video manually | `docs/PITCH_SCRIPT.md` |
| Architecture | System and workflow diagrams | PASS | None | `docs/ARCHITECTURE.md` |
| Show real work | Code, commits, tests, evaluation, audit | PASS | CI must pass after push | Git history and Actions |
| Razorpay relevance | Test Orders API after risk approval; verified webhooks | PASS WITH MANUAL LIVE TEST | Test credentials absent | adapter contract/webhook tests |
| Explainable bounded money actions | Evidence, mandate, human gate, audit timeline | PASS | None | Dashboard and workflow tests |
| Graceful failure | Deterministic explanation fallback; failed-safe provider path | PASS | External outage live demo optional | negative tests/demo script |
