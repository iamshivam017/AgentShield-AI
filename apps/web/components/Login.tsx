"use client";

import { FormEvent, useState } from "react";
import { login } from "@/lib/api";
import { Logo } from "./Logo";

export function Login({ onAuthenticated }: { onAuthenticated: (token: string) => void }) {
  const [email, setEmail] = useState("demo-admin@agentshield.dev");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const result = await login(email, password);
      sessionStorage.setItem("agentshield_token", result.access_token);
      onAuthenticated(result.access_token);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to sign in");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-story" aria-labelledby="login-title">
        <Logo />
        <div>
          <p className="eyebrow">Razorpay Buildathon · Track 02</p>
          <h1 id="login-title">Autonomy needs a boundary.</h1>
          <p className="story-copy">AgentShield detects when an AI-initiated payment breaks behavioral norms or delegated authority—before money moves.</p>
        </div>
        <div className="trust-chain" aria-label="Decision architecture">
          <span>Behavior</span><i /> <span>Model</span><i /> <span>Policy</span><i /> <strong>Decision</strong>
        </div>
      </section>
      <section className="login-panel" aria-label="Sign in">
        <form onSubmit={submit}>
          <p className="section-index">01 / SECURE ACCESS</p>
          <h2>Risk command center</h2>
          <p className="muted">Use the seeded administrator account to run the complete deterministic demo.</p>
          <label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="username" required /></label>
          <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required /></label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="primary-button" disabled={loading}>{loading ? "Authenticating…" : "Enter command center"}<span aria-hidden="true">↗</span></button>
          <p className="fine-print">Set your local demo password through the environment. Production requires managed identity.</p>
        </form>
      </section>
    </main>
  );
}
