export type VehicleType = "car" | "truck" | "motorcycle" | "boat" | "generator" | "atv" | "pwc" | "rv" | "heavy_equipment" | "other";

export type SessionMode = "consumer" | "operator" | "mechanic";

export interface HeavyEquipmentContext {
  hours_of_operation?: number;
  last_service_hours?: number;
  environment?: "dusty" | "muddy" | "marine" | "urban";
  storage_duration?: number;
  recent_work_type?: string;
}

export interface Vehicle {
  year?: number;
  make?: string;
  model?: string;
  engine?: string;
  vehicle_type?: VehicleType;
}

export interface OBDResult {
  code: string;
  description: string;
  severity: "low" | "moderate" | "high" | "critical";
  likely_causes: string[];
  next_steps: string[];
  diy_difficulty: "easy" | "moderate" | "hard" | "seek_mechanic";
}

export interface RankedCause {
  cause: string;
  confidence: number;
  reasoning: string;
}

export interface SuggestedPart {
  name: string;
  notes: string;
}

export interface DiagnosticResult {
  ranked_causes: RankedCause[];
  next_checks: string[];
  diy_difficulty: "easy" | "moderate" | "hard" | "seek_mechanic" | null;
  suggested_parts: SuggestedPart[];
  escalation_guidance: string | null;
  confidence_level: number;
  post_diagnosis: string[];
}

export interface MessageResponse {
  session_id: string;
  message: string;
  msg_type: "question" | "result" | "error";
  turn: number;
  result: DiagnosticResult | null;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  msg_type?: "question" | "result" | "chat" | "image" | "error";
  result?: DiagnosticResult;
  obd_result?: OBDResult;
}

export interface SessionSummary {
  session_id: string;
  created_at: string;
  status: "active" | "awaiting_followup" | "complete" | "abandoned";
  symptom_category: string | null;
  vehicle_year: number | null;
  vehicle_make: string | null;
  vehicle_model: string | null;
  vehicle_type: VehicleType;
  excerpt: string;
  top_cause: string | null;
}

export interface FeedbackRequest {
  rating: number; // 1–5
  comment?: string;
}

export interface FeedbackResponse {
  session_id: string;
  rating: number;
}

// ── Admin analytics types ─────────────────────────────────────────────────────

// Phase 14 — Learning
export interface HypothesisMetric {
  hypothesis_id: string;
  total_cases: number;
  resolution_rate: number;
  reversal_rate: number;
  avg_rating: number | null;
  correct: number;
  reversed: number;
}

export interface WeightAdjustment {
  hypothesis_id: string;
  base_weight: number;
  suggested_multiplier: number;
  confidence: number;
  reason: string;
  metrics: HypothesisMetric;
  current_approved_multiplier: number | null;
  is_approved: boolean;
  sample_session_ids: string[];
}

export interface LearningInsight {
  type: "critical" | "warning" | "opportunity";
  title: string;
  description: string;
  affected: string[];
  suggested_action: string;
  priority: number;
}

// Phase 14 — Fleet
export interface FleetSummary {
  total_sessions: number;
  resolved_count: number;
  unresolved_count: number;
  safety_triggered_count: number;
  avg_contradictions: number;
  avg_rating: number | null;
  by_mode: Record<string, number>;
  by_environment: Record<string, number>;
  by_tree: { tree: string; count: number }[];
}

export interface FleetPattern {
  pattern_type: string;
  tree_key?: string;
  environment?: string;
  hours_band?: string;
  hypothesis_key?: string;
  session_count: number;
  unresolved_rate?: number;
  safety_trigger_rate?: number;
  avg_contradictions?: number;
  description: string;
  sample_session_ids: string[];
}

// Phase 14 — Mode Analytics
export interface ModeMetrics {
  mode: string;
  session_count: number;
  resolution_rate: number;
  contradiction_rate: number;
  safety_trigger_rate: number;
  avg_rating: number | null;
  reroute_rate: number;
  early_exit_rate: number;
  anomaly_frequency: number;
}

export interface ModeComparison {
  metric: string;
  by_mode: Record<string, number | null>;
  best_mode: string | null;
  worst_mode: string | null;
  spread: number;
}

// Phase 14 — Telematics
export interface TelemetryReading {
  telemetry_id: string;
  asset_id: string;
  received_at: string;
  telemetry_ts: string | null;
  raw: {
    engine_temp_c?: number;
    voltage_v?: number;
    pressure_psi?: number;
    fuel_level_pct?: number;
    fault_codes?: string[];
  };
  signal_names: string[];
  safety_count: number;
  linked_session_id: string | null;
}

export interface AdminStats {
  total_sessions: number;
  total_users: number;
  rated_sessions: number;
  avg_rating: number | null;
  sessions_this_week: number;
  completed_sessions: number;
}

export interface DailyCount {
  day: string;
  count: number;
}

export interface TopDiagnosis {
  symptom_category: string;
  vehicle_type: string;
  session_count: number;
  avg_rating: number | null;
  rated_count: number;
}

export interface FeedbackEntry {
  session_id: string;
  rating: number;
  comment: string | null;
  created_at: string;
  symptom_category: string | null;
  vehicle_type: string | null;
  vehicle_year: number | null;
  vehicle_make: string | null;
  vehicle_model: string | null;
}

export interface CoverageCell {
  has_tree: boolean;
  session_count: number;
}

export interface CoverageRow {
  symptom: string;
  vehicles: Record<string, CoverageCell>;
}

export interface SessionState {
  session_id: string;
  status: string;
  turn_count: number;
  symptom_category: string | null;
  vehicle: Vehicle;
  messages: { role: string; content: string; type: string }[];
  result: DiagnosticResult | null;
}
