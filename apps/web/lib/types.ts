export type Decision = "ALLOW" | "VERIFY" | "BLOCK";

export interface Summary {
  total: number;
  allowed: number;
  verify: number;
  blocked: number;
  amount_screened_paise: number;
  amount_blocked_paise: number;
  avg_risk_score: number;
  decisions_by_hour: Array<Record<string, unknown>>;
}

export interface Transaction {
  transaction_id: string;
  merchant_name: string;
  amount_paise: number;
  decision: Decision;
  status: string;
  risk_score: number;
  created_at: string;
}

export interface RiskSignal {
  code: string;
  label: string;
  contribution: number;
  evidence: string;
}

export interface TransactionDetail extends Transaction {
  correlation_id: string;
  model_probability: number;
  confidence: number;
  signals: RiskSignal[];
  policy_violations: string[];
  explanation: string;
  explanation_source: string;
  model_version: string;
}

export interface Policy {
  agent_id: string;
  display_name: string;
  max_transaction_paise: number;
  daily_limit_paise: number;
  verification_threshold_paise: number;
  blocked_categories: string[];
  allowed_regions: string[];
  is_active: boolean;
}

export interface AuditEvent {
  id: string;
  actor: string;
  action: string;
  status: string;
  reason: string;
  created_at: string;
}
