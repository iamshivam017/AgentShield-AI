export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="logo" aria-label="AgentShield">
      <svg viewBox="0 0 36 40" role="img" aria-hidden="true">
        <path d="M18 1 33 7v11c0 10.4-6.2 17.3-15 21C9.2 35.3 3 28.4 3 18V7L18 1Z" fill="currentColor" />
        <path d="m11 20 4.3 4.3L26 13.6" fill="none" stroke="#10120f" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      {!compact && <span>AGENTSHIELD</span>}
    </div>
  );
}
