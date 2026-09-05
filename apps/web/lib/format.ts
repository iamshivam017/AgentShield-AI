export function formatMoney(paise: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(paise / 100);
}

export function formatTime(value: string): string {
  return new Intl.DateTimeFormat("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "short",
  }).format(new Date(value));
}

export function decisionTone(decision: string): "safe" | "warn" | "danger" {
  if (decision === "ALLOW") return "safe";
  if (decision === "VERIFY") return "warn";
  return "danger";
}
