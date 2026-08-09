export type Finding = {
  id: number;
  resource_id: string;
  resource_arn: string;
  resource_type: string;
  resource_name: string;
  region: string;
  flag_type: string;
  detection_confidence: number;
  metric_summary: Record<string, unknown>;
  resource_metadata: Record<string, unknown>;
  explanation: string;
  severity: string;
  proposed_action: string;
  proposed_params: Record<string, unknown>;
  agent_confidence: number;
  estimated_monthly_savings_usd: number;
  blast_radius: string;
  status: string;
  created_at: string;
};

const BASE = "";

export async function fetchFindings(): Promise<Finding[]> {
  const res = await fetch(`${BASE}/api/findings`);
  if (!res.ok) throw new Error(`Failed to load findings (${res.status})`);
  return res.json();
}

export async function triggerScan(): Promise<{ created: number; findings: Finding[] }> {
  const res = await fetch(`${BASE}/api/scan`, { method: "POST" });
  if (!res.ok) throw new Error(`Scan failed (${res.status})`);
  return res.json();
}
