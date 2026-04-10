const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function fleetFetch(path: string): Promise<Response> {
  return fetch(`${API_BASE}${path}`, {
    credentials: "include",
  });
}

export interface FleetAsset {
  asset_id: string;
  vehicle_type: string | null;
  last_seen: string | null;
  session_count: number;
  open_sessions: number;
  last_symptom: string | null;
  last_top_cause: string | null;
  last_safety_alerts: Array<{ severity: string; message: string }>;
}

export interface AssetSession {
  session_id: string;
  symptom_category: string | null;
  vehicle_type: string | null;
  status: string;
  top_cause: string | null;
  created_at: string | null;
  turn_count: number;
}

export interface AssetHistory {
  asset_id: string;
  sessions: AssetSession[];
}

export interface FleetFault {
  cause: string;
  count: number;
}

export interface FleetSummaryData {
  total_assets: number;
  active_issues: number;
  top_faults: FleetFault[];
}

export async function getFleetAssets(): Promise<FleetAsset[]> {
  const res = await fleetFetch("/api/fleet/assets");
  if (!res.ok) throw new Error(`Fleet assets fetch failed (${res.status})`);
  return res.json();
}

export async function getAssetHistory(assetId: string, limit = 20): Promise<AssetHistory> {
  const res = await fleetFetch(`/api/fleet/asset/${encodeURIComponent(assetId)}/history?limit=${limit}`);
  if (!res.ok) throw new Error(`Asset history fetch failed (${res.status})`);
  return res.json();
}

export async function getFleetSummary(): Promise<FleetSummaryData> {
  const res = await fleetFetch("/api/fleet/summary");
  if (!res.ok) throw new Error(`Fleet summary fetch failed (${res.status})`);
  return res.json();
}

export interface AssetRisk {
  asset_id: string;
  risk_score: number;
  risk_level: "low" | "medium" | "high" | "critical";
  contributing_factors: string[];
  recommended_action: string;
  component_scores: {
    unresolved: number;
    repeat: number;
    contradiction: number;
    safety: number;
    anomaly: number;
    telematics: number;
    service: number;
  };
}

export async function getFleetPriorities(days = 30): Promise<AssetRisk[]> {
  const res = await fleetFetch(`/api/fleet/priorities?days=${days}`);
  if (!res.ok) throw new Error(`Fleet priorities fetch failed (${res.status})`);
  return res.json();
}
