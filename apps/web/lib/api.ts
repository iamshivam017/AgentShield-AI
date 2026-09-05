import type { AuditEvent, Policy, Summary, Transaction, TransactionDetail } from "./types";

const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

async function request<T>(path: string, token?: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({ detail: "Request failed" }))) as { detail?: string };
    throw new ApiError(body.detail ?? "Request failed", response.status);
  }
  return (await response.json()) as T;
}

export async function login(email: string, password: string) {
  return request<{ access_token: string; role: string }>("/auth/login", undefined, {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export const api = {
  summary: (token: string) => request<Summary>("/metrics/summary", token),
  transactions: (token: string, decision?: string) => request<Transaction[]>(`/transactions${decision ? `?decision=${decision}` : ""}`, token),
  transaction: (token: string, id: string) => request<TransactionDetail>(`/transactions/${id}`, token),
  audit: (token: string, id: string) => request<AuditEvent[]>(`/audit/${id}`, token),
  policy: (token: string) => request<Policy>("/policies/agent-shopping-01", token),
  updatePolicy: (token: string, policy: Omit<Policy, "agent_id" | "display_name">) => request<Policy>("/policies/agent-shopping-01", token, { method: "PUT", body: JSON.stringify(policy) }),
  evaluate: (token: string, payload: Record<string, unknown>) => request<TransactionDetail>("/risk/evaluate", token, { method: "POST", headers: { "Idempotency-Key": String(payload.idempotency_key) }, body: JSON.stringify(payload) }),
  verify: (token: string, id: string, action: "APPROVE" | "BLOCK") => request<TransactionDetail>(`/transactions/${id}/verify`, token, { method: "POST", body: JSON.stringify({ action, reason: action === "APPROVE" ? "User confirmed the intended purchase" : "Risk analyst rejected the payment" }) }),
  execute: (token: string, id: string) => request<{ order_id: string; status: string }>(`/transactions/${id}/execute`, token, { method: "POST" }),
};
