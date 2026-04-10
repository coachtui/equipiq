import type {
  AdminStats,
  CoverageRow,
  DailyCount,
  FeedbackEntry,
  FleetPattern,
  FleetSummary,
  HypothesisMetric,
  LearningInsight,
  ModeComparison,
  ModeMetrics,
  TelemetryReading,
  TopDiagnosis,
  WeightAdjustment,
} from "@/types";

async function adminFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(path, { credentials: "include", ...options });
  if (res.status === 403) throw new Error("Admin access required");
  if (!res.ok) throw new Error(`Admin API error: ${res.status}`);
  return res.json();
}

// ── Existing endpoints ────────────────────────────────────────────────────────

export async function getAdminStats(): Promise<AdminStats> {
  return adminFetch("/api/admin/stats");
}

export async function getSessionsOverTime(days = 30): Promise<{ days: number; data: DailyCount[] }> {
  return adminFetch(`/api/admin/sessions_over_time?days=${days}`);
}

export async function getTopDiagnoses(limit = 20): Promise<{ data: TopDiagnosis[] }> {
  return adminFetch(`/api/admin/top_diagnoses?limit=${limit}`);
}

export async function getFeedback(
  limit = 30,
  commentsOnly = false
): Promise<{ data: FeedbackEntry[]; distribution: Record<number, number> }> {
  return adminFetch(`/api/admin/feedback?limit=${limit}&comments_only=${commentsOnly}`);
}

export async function getCoverage(): Promise<{
  symptoms: string[];
  vehicle_types: string[];
  matrix: CoverageRow[];
}> {
  return adminFetch("/api/admin/coverage");
}

// ── Phase 14 — Learning ───────────────────────────────────────────────────────

export async function getLearningMetrics(): Promise<{
  total_hypotheses: number;
  metrics: Record<string, HypothesisMetric>;
}> {
  return adminFetch("/api/admin/learning/metrics");
}

export async function getLearningAdjustments(): Promise<{
  count: number;
  adjustments: WeightAdjustment[];
}> {
  return adminFetch("/api/admin/learning/adjustments");
}

export async function approveLearningAdjustment(
  hypothesisId: string,
  multiplier: number
): Promise<{ hypothesis_id: string; multiplier: number; status: string }> {
  return adminFetch(`/api/admin/learning/adjustments/${encodeURIComponent(hypothesisId)}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ multiplier }),
  });
}

export async function rejectLearningAdjustment(
  hypothesisId: string
): Promise<{ hypothesis_id: string; status: string }> {
  return adminFetch(`/api/admin/learning/adjustments/${encodeURIComponent(hypothesisId)}/reject`, {
    method: "POST",
  });
}

export async function getLearningInsights(
  useLlm = true,
  dataLimit = 200
): Promise<{
  generated_at: string;
  use_llm: boolean;
  insights: LearningInsight[];
  weak_hypotheses: object[];
  tree_gaps: object[];
  anomaly_trends: object[];
}> {
  return adminFetch(`/api/admin/learning/insights?use_llm=${useLlm}&data_limit=${dataLimit}`);
}

// ── Phase 14 — Fleet ──────────────────────────────────────────────────────────

export async function getFleetHeavy(
  sessionMode?: string,
  limit = 100
): Promise<{ summary: FleetSummary; sessions: object[] }> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (sessionMode) params.set("session_mode", sessionMode);
  return adminFetch(`/api/admin/fleet/heavy_equipment?${params}`);
}

export async function getFleetHeavyPatterns(
  useLlm = true,
  limit = 500,
  sessionMode?: string
): Promise<{
  fleet_summary: string;
  hours_failure_patterns: FleetPattern[];
  environment_patterns: FleetPattern[];
  unresolved_clusters: FleetPattern[];
  safety_hotspots: FleetPattern[];
  contradiction_hotspots: FleetPattern[];
  total_sessions_analysed: number;
}> {
  const params = new URLSearchParams({ use_llm: String(useLlm), limit: String(limit) });
  if (sessionMode) params.set("session_mode", sessionMode);
  return adminFetch(`/api/admin/fleet/heavy_equipment/patterns?${params}`);
}

// ── Phase 14 — Modes ──────────────────────────────────────────────────────────

export async function getModeAnalytics(
  vehicleType?: string,
  limit = 1000
): Promise<{
  summaries: Record<string, string>;
  metrics: Record<string, ModeMetrics>;
  breakdown: Record<string, object>;
}> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (vehicleType) params.set("vehicle_type", vehicleType);
  return adminFetch(`/api/admin/analytics/by_mode?${params}`);
}

export async function getModeComparison(
  vehicleType?: string,
  limit = 1000
): Promise<{
  modes_present: string[];
  comparison: ModeComparison[];
}> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (vehicleType) params.set("vehicle_type", vehicleType);
  return adminFetch(`/api/admin/analytics/mode_comparison?${params}`);
}

// ── Phase 14 — Telematics ─────────────────────────────────────────────────────

export async function getRecentTelemetry(
  limit = 50,
  assetId?: string
): Promise<{ count: number; readings: TelemetryReading[] }> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (assetId) params.set("asset_id", assetId);
  return adminFetch(`/api/admin/telematics/recent?${params}`);
}
