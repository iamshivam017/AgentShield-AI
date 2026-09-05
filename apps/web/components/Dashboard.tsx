"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { decisionTone, formatMoney, formatTime } from "@/lib/format";
import type { AuditEvent, Policy, Summary, Transaction, TransactionDetail } from "@/lib/types";
import { Logo } from "./Logo";

type View = "overview" | "queue" | "policies" | "evidence";
type Scenario = "trusted" | "verify" | "blocked" | "failure";

const emptySummary: Summary = { total: 0, allowed: 0, verify: 0, blocked: 0, amount_screened_paise: 0, amount_blocked_paise: 0, avg_risk_score: 0, decisions_by_hour: [] };

const scenarios: Record<Scenario, { name: string; note: string; payload: Record<string, unknown> }> = {
  trusted: { name: "Trusted purchase", note: "Known context · within mandate", payload: { merchant_id: "merchant-paperpine", merchant_name: "Paper & Pine", merchant_category: "retail", amount_paise: 125000, device_id: "device-known", ip_region: "IN-KA", purpose: "Restock office supplies" } },
  verify: { name: "Delegation edge", note: "₹4,500 · above verification floor", payload: { merchant_id: "merchant-nomad", merchant_name: "Nomad Electronics", merchant_category: "electronics", amount_paise: 450000, device_id: "device-new-07", ip_region: "IN-KA", purpose: "Purchase noise-cancelling headphones" } },
  blocked: { name: "Mandate violation", note: "Restricted category · hard block", payload: { merchant_id: "merchant-restricted", merchant_name: "QuickChip Exchange", merchant_category: "cash_equivalent", amount_paise: 890000, device_id: "device-new-91", ip_region: "IN-DL", purpose: "Purchase digital stored value" } },
  failure: { name: "Provider failure", note: "Safe degraded execution path", payload: { merchant_id: "merchant-paperpine", merchant_name: "Paper & Pine", merchant_category: "retail", amount_paise: 90000, device_id: "device-known", ip_region: "IN-KA", purpose: "Demonstrate external dependency handling" } },
};

function DecisionChip({ value }: { value: string }) {
  return <span className={`decision-chip ${decisionTone(value)}`}><i />{value}</span>;
}

function RiskBar({ score }: { score: number }) {
  return <div className="risk-bar" aria-label={`Risk score ${score} out of 100`}><span style={{ width: `${score}%` }} data-tone={score >= 85 ? "danger" : score >= 55 ? "warn" : "safe"} /></div>;
}

function Metric({ label, value, detail }: { label: string; value: string | number; detail: string }) {
  return <article className="metric"><p>{label}</p><strong>{value}</strong><span>{detail}</span></article>;
}

export function Dashboard({ token, onLogout }: { token: string; onLogout: () => void }) {
  const [view, setView] = useState<View>("overview");
  const [summary, setSummary] = useState<Summary>(emptySummary);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [selected, setSelected] = useState<TransactionDetail | null>(null);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [filter, setFilter] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    try {
      const [nextSummary, nextTransactions, nextPolicy] = await Promise.all([api.summary(token), api.transactions(token, filter || undefined), api.policy(token)]);
      setSummary(nextSummary); setTransactions(nextTransactions); setPolicy(nextPolicy); setError("");
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Unable to load risk data";
      setError(message);
      if (message.toLowerCase().includes("token") || message.toLowerCase().includes("authentication")) onLogout();
    }
  }, [filter, onLogout, token]);

  useEffect(() => { queueMicrotask(() => void load()); }, [load]);

  const rates = useMemo(() => ({
    intervention: summary.total ? Math.round(((summary.verify + summary.blocked) / summary.total) * 100) : 0,
    allow: summary.total ? Math.round((summary.allowed / summary.total) * 100) : 0,
  }), [summary]);

  async function runScenario(scenario: Scenario) {
    setBusy(true); setError(""); setNotice("");
    try {
      const item = scenarios[scenario];
      const suffix = `${scenario}-${crypto.randomUUID()}`;
      const result = await api.evaluate(token, { ...item.payload, idempotency_key: suffix, agent_id: "agent-shopping-01", currency: "INR", initiated_at: new Date().toISOString() });
      setSelected(result);
      setAudit(await api.audit(token, result.transaction_id));
      setNotice(`${item.name} evaluated: ${result.decision}`);
      await load();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Scenario failed safely"); }
    finally { setBusy(false); }
  }

  async function inspect(id: string) {
    setBusy(true);
    try { const [detail, events] = await Promise.all([api.transaction(token, id), api.audit(token, id)]); setSelected(detail); setAudit(events); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to inspect transaction"); }
    finally { setBusy(false); }
  }

  async function resolve(action: "APPROVE" | "BLOCK") {
    if (!selected) return;
    setBusy(true);
    try { const updated = await api.verify(token, selected.transaction_id, action); setSelected(updated); setAudit(await api.audit(token, updated.transaction_id)); setNotice(`Verification resolved: ${action}`); await load(); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to resolve verification"); }
    finally { setBusy(false); }
  }

  async function execute() {
    if (!selected) return;
    setBusy(true);
    try { const result = await api.execute(token, selected.transaction_id); setNotice(`Razorpay test order ${result.order_id} created`); setSelected(await api.transaction(token, selected.transaction_id)); setAudit(await api.audit(token, selected.transaction_id)); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Payment provider failed safely"); }
    finally { setBusy(false); }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Logo />
        <nav aria-label="Primary navigation">
          {(["overview", "queue", "policies", "evidence"] as View[]).map((item, index) => <button key={item} className={view === item ? "active" : ""} onClick={() => setView(item)}><span>0{index + 1}</span>{item}</button>)}
        </nav>
        <div className="system-state"><i /><div><strong>Decision engine online</strong><span>Deterministic fallback ready</span></div></div>
        <button className="logout" onClick={onLogout}>Sign out <span>↗</span></button>
      </aside>

      <main className="workspace">
        <header className="topbar"><div><p className="eyebrow">PAYMENT RISK COMMAND CENTER</p><h1>{view === "overview" ? "Today’s control surface" : view === "queue" ? "Decision queue" : view === "policies" ? "Delegated authority" : "Model evidence"}</h1></div><div className="topbar-meta"><span>TEST MODE</span><time>{new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short", year: "numeric" }).format(new Date())}</time></div></header>

        {error && <div className="banner error" role="alert"><strong>Safe failure</strong><span>{error}</span><button onClick={() => { setError(""); void load(); }}>Retry</button></div>}
        {notice && <div className="banner success" role="status"><strong>Recorded</strong><span>{notice}</span><button onClick={() => setNotice("")} aria-label="Dismiss notification">×</button></div>}

        {view === "overview" && <>
          <section className="metric-grid" aria-label="Risk metrics">
            <Metric label="PAYMENTS SCREENED" value={summary.total} detail={formatMoney(summary.amount_screened_paise)} />
            <Metric label="INTERVENTION RATE" value={`${rates.intervention}%`} detail={`${summary.verify} verify · ${summary.blocked} blocked`} />
            <Metric label="RISK PREVENTED" value={formatMoney(summary.amount_blocked_paise)} detail="Policy-blocked exposure" />
            <Metric label="MEAN RISK SCORE" value={`${summary.avg_risk_score}`} detail={`${rates.allow}% cleared automatically`} />
          </section>
          <section className="overview-grid">
            <article className="scenario-panel"><div className="section-heading"><div><p className="section-index">LIVE DECISION LAB</p><h2>Run a bounded scenario</h2></div><span>Actual API + policy + ML</span></div><div className="scenario-list">{(Object.keys(scenarios) as Scenario[]).map((key, index) => <button key={key} disabled={busy} onClick={() => void runScenario(key)}><span className="scenario-number">0{index + 1}</span><span><strong>{scenarios[key].name}</strong><small>{scenarios[key].note}</small></span><b>Run ↗</b></button>)}</div></article>
            <article className="decision-distribution"><div className="section-heading"><div><p className="section-index">POLICY OUTCOMES</p><h2>Decision distribution</h2></div></div><div className="distribution"><div className="donut" style={{ background: `conic-gradient(var(--safe) 0 ${rates.allow}%, var(--warn) ${rates.allow}% ${rates.allow + (summary.total ? Math.round(summary.verify / summary.total * 100) : 0)}%, var(--danger) 0)` }}><span><strong>{summary.total}</strong>evaluated</span></div><ul><li><i className="safe-bg"/><span>Allowed</span><strong>{summary.allowed}</strong></li><li><i className="warn-bg"/><span>Verify</span><strong>{summary.verify}</strong></li><li><i className="danger-bg"/><span>Blocked</span><strong>{summary.blocked}</strong></li></ul></div><p className="method-note">Outcomes are calculated from persisted decisions—not presentation fixtures.</p></article>
          </section>
          <TransactionTable items={transactions.slice(0, 6)} onInspect={inspect} />
        </>}

        {view === "queue" && <section><div className="filter-row" role="group" aria-label="Filter decisions">{["", "ALLOW", "VERIFY", "BLOCK"].map(item => <button key={item || "ALL"} className={filter === item ? "active" : ""} onClick={() => setFilter(item)}>{item || "ALL"}<span>{item ? transactions.filter(tx => tx.decision === item).length : summary.total}</span></button>)}</div><TransactionTable items={transactions} onInspect={inspect} /></section>}

        {view === "policies" && policy && <PolicyPanel policy={policy} token={token} onSaved={(next) => { setPolicy(next); setNotice("Delegated payment policy updated"); }} />}

        {view === "evidence" && <EvidencePanel />}
      </main>

      {selected && <Investigation item={selected} audit={audit} busy={busy} onClose={() => setSelected(null)} onResolve={resolve} onExecute={execute} />}
    </div>
  );
}

function TransactionTable({ items, onInspect }: { items: Transaction[]; onInspect: (id: string) => void }) {
  return <section className="table-panel"><div className="section-heading"><div><p className="section-index">LIVE LEDGER</p><h2>Recent payment intents</h2></div><span>{items.length} visible records</span></div>{items.length === 0 ? <div className="empty-state"><strong>No decisions yet</strong><p>Run a scenario to send a real intent through the risk pipeline.</p></div> : <div className="table-scroll"><table><thead><tr><th>Merchant</th><th>Amount</th><th>Risk</th><th>Decision</th><th>Status</th><th>Time</th><th><span className="sr-only">Action</span></th></tr></thead><tbody>{items.map(item => <tr key={item.transaction_id}><td><strong>{item.merchant_name}</strong><small>{item.transaction_id.slice(0, 8)}</small></td><td>{formatMoney(item.amount_paise)}</td><td><span className="risk-score">{item.risk_score}</span><RiskBar score={item.risk_score} /></td><td><DecisionChip value={item.decision} /></td><td className="status-text">{item.status.replaceAll("_", " ")}</td><td>{formatTime(item.created_at)}</td><td><button className="inspect" onClick={() => void onInspect(item.transaction_id)}>Inspect ↗</button></td></tr>)}</tbody></table></div>}</section>;
}

function Investigation({ item, audit, busy, onClose, onResolve, onExecute }: { item: TransactionDetail; audit: AuditEvent[]; busy: boolean; onClose: () => void; onResolve: (action: "APPROVE" | "BLOCK") => void; onExecute: () => void }) {
  return <div className="drawer-backdrop" role="presentation" onMouseDown={(event) => { if (event.currentTarget === event.target) onClose(); }}><aside className="drawer" role="dialog" aria-modal="true" aria-labelledby="investigation-title"><header><div><p className="section-index">INVESTIGATION · {item.transaction_id.slice(0, 8)}</p><h2 id="investigation-title">{item.merchant_name}</h2></div><button onClick={onClose} aria-label="Close investigation">×</button></header><div className="decision-hero"><div><span>RISK SCORE</span><strong>{item.risk_score}<small>/100</small></strong><RiskBar score={item.risk_score} /></div><DecisionChip value={item.decision} /></div><section className="explanation"><p className="section-index">DECISION RATIONALE</p><p>{item.explanation}</p><footer><span>{Math.round(item.confidence * 100)}% model confidence</span><span>{item.explanation_source.replaceAll("_", " ")}</span></footer></section><section><p className="section-index">EVIDENCE</p><div className="signal-list">{item.signals.map(signal => <div key={signal.code}><b className={signal.contribution < 0 ? "negative" : ""}>{signal.contribution > 0 ? "+" : ""}{signal.contribution}</b><span><strong>{signal.label}</strong><small>{signal.evidence}</small></span></div>)}</div></section>{item.policy_violations.length > 0 && <section><p className="section-index">BINDING POLICY</p><div className="policy-tags">{item.policy_violations.map(item => <span key={item}>{item.replaceAll("_", " ")}</span>)}</div></section>}<section><p className="section-index">AUDIT TIMELINE</p><ol className="timeline">{audit.map(event => <li key={event.id}><time>{new Date(event.created_at).toLocaleTimeString("en-IN")}</time><div><strong>{event.action.replaceAll(".", " / ")}</strong><span>{event.reason}</span></div></li>)}</ol></section><footer className="drawer-actions">{item.status === "AWAITING_VERIFICATION" && <><button className="secondary-button danger-outline" disabled={busy} onClick={() => onResolve("BLOCK")}>Block payment</button><button className="primary-button" disabled={busy} onClick={() => onResolve("APPROVE")}>Approve intent</button></>}{item.status === "APPROVED" && <button className="primary-button full" disabled={busy} onClick={onExecute}>Create Razorpay test order ↗</button>}<p>Model {item.model_version}</p></footer></aside></div>;
}

function PolicyPanel({ policy, token, onSaved }: { policy: Policy; token: string; onSaved: (policy: Policy) => void }) {
  const [draft, setDraft] = useState(policy); const [saving, setSaving] = useState(false); const [error, setError] = useState("");
  async function save() { setSaving(true); setError(""); try { const { agent_id: _, display_name: __, ...payload } = draft; void _; void __; onSaved(await api.updatePolicy(token, payload)); } catch (caught) { setError(caught instanceof Error ? caught.message : "Policy update failed"); } finally { setSaving(false); } }
  return <section className="policy-layout"><article className="policy-editor"><div className="section-heading"><div><p className="section-index">ACTIVE MANDATE</p><h2>{policy.display_name}</h2></div><span className="live-indicator"><i />Active</span></div><p className="lead">These deterministic limits remain authoritative even when the model reports low risk.</p><div className="form-grid"><label>Maximum single payment<span>Paise, stored as an integer</span><input type="number" value={draft.max_transaction_paise} onChange={event => setDraft({ ...draft, max_transaction_paise: Number(event.target.value) })} /></label><label>Daily delegated limit<span>Across approved intents</span><input type="number" value={draft.daily_limit_paise} onChange={event => setDraft({ ...draft, daily_limit_paise: Number(event.target.value) })} /></label><label>Verification threshold<span>Human approval required above</span><input type="number" value={draft.verification_threshold_paise} onChange={event => setDraft({ ...draft, verification_threshold_paise: Number(event.target.value) })} /></label></div><div className="read-only-groups"><div><span>Blocked merchant categories</span>{draft.blocked_categories.map(value => <b key={value}>{value.replaceAll("_", " ")}</b>)}</div><div><span>Delegated regions</span>{draft.allowed_regions.map(value => <b key={value}>{value}</b>)}</div></div>{error && <p className="form-error">{error}</p>}<button className="primary-button" disabled={saving} onClick={() => void save()}>{saving ? "Saving…" : "Commit policy change"}</button></article><aside className="policy-principles"><p className="section-index">ENFORCEMENT ORDER</p><ol><li><span>01</span><div><strong>Authenticate actor</strong><p>Reject unknown agents and operators.</p></div></li><li><span>02</span><div><strong>Score behavior</strong><p>Estimate anomaly probability from context.</p></div></li><li><span>03</span><div><strong>Apply mandate</strong><p>Hard rules override the model.</p></div></li><li><span>04</span><div><strong>Gate execution</strong><p>Only allowed or verified intents reach Razorpay.</p></div></li></ol></aside></section>;
}

function EvidencePanel() {
  return <section className="evidence-layout"><article className="evidence-intro"><p className="section-index">HELD-OUT EVALUATION</p><h2>Evidence over accuracy theatre.</h2><p>AgentShield uses a reproducible 10,000-record synthetic dataset with a temporal 70/15/15 split. The final 1,500-record test window remained untouched until model and threshold analysis.</p><div className="evidence-stats"><div><strong>94.78%</strong><span>Precision</span></div><div><strong>85.83%</strong><span>Recall</span></div><div><strong>90.08%</strong><span>F1 score</span></div></div></article><article className="evidence-method"><p className="section-index">COST-AWARE OPERATING POINT</p><ul><li><span>PR-AUC</span><b>90.18% on held-out future window</b></li><li><span>False-positive rate</span><b>0.44% · 6 legitimate intents</b></li><li><span>False-positive cost</span><b>₹900 · ₹150 analyst friction / review</b></li><li><span>False-negative exposure</span><b>₹48,741.55 · 10% illustrative severity</b></li></ul><p className="method-note">All figures are generated by <code>make benchmark</code>. Synthetic inputs and cost assumptions are explicitly labeled; no Razorpay customer data is claimed.</p></article><article className="evidence-guardrail"><p className="section-index">ANTI-WRAPPER TEST</p><h3>The LLM is never the authority.</h3><div className="guardrail-flow"><span>ML predicts</span><i>→</i><span>Policy decides</span><i>→</i><span>Human verifies</span><i>→</i><span>Razorpay executes</span></div><p>If an explanation provider times out, the decision still completes using deterministic evidence. Financial execution cannot be reached through explanation output.</p></article></section>;
}
