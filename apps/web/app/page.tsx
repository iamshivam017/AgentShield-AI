"use client";

import { useEffect, useState } from "react";
import { Dashboard } from "@/components/Dashboard";
import { Login } from "@/components/Login";

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    queueMicrotask(() => {
      setToken(sessionStorage.getItem("agentshield_token"));
      setReady(true);
    });
  }, []);

  if (!ready) return <div className="page-loader" aria-label="Loading AgentShield"><span /></div>;
  if (!token) return <Login onAuthenticated={setToken} />;
  return <Dashboard token={token} onLogout={() => { sessionStorage.removeItem("agentshield_token"); setToken(null); }} />;
}
