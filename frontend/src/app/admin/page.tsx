"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import {
  getAdminStats,
  getCoverage,
  getFeedback,
  getSessionsOverTime,
  getTopDiagnoses,
  getLearningInsights,
  getLearningAdjustments,
  getLearningMetrics,
  approveLearningAdjustment,
  rejectLearningAdjustment,
  getFleetHeavy,
  getFleetHeavyPatterns,
  getModeAnalytics,
  getModeComparison,
  getRecentTelemetry,
} from "@/lib/admin";
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

// ── Helpers ───────────────────────────────────────────────────────────────────

const SYMPTOM_LABELS: Record<string, string> = {
  no_crank: "No Crank",
  crank_no_start: "Crank No Start",
  loss_of_power: "Loss of Power",
  rough_idle: "Rough Idle",
  strange_noise: "Strange Noise",
  visible_leak: "Visible Leak",
  overheating: "Overheating",
  check_engine_light: "Check Engine",
  brakes: "Brakes",
  transmission: "Transmission",
  suspension: "Suspension",
  hvac: "HVAC",
  // Heavy equipment
  no_start: "No Start (HE)",
  hydraulic_loss: "Hydraulic Loss",
  electrical_fault: "Electrical Fault",
  track_or_drive_issue: "Track / Drive",
  abnormal_noise: "Abnormal Noise",
  coolant_leak: "Coolant Leak",
  implement_failure: "Implement Failure",
  cab_electrical: "Cab Electrical",
  fuel_contamination: "Fuel Contamination",
};

const VT_LABELS: Record<string, string> = {
  car: "Car",
  truck: "Truck",
  motorcycle: "Moto",
  boat: "Boat",
  generator: "Gen",
  atv: "ATV",
  pwc: "PWC",
  rv: "RV",
  heavy_equipment: "Heavy Eq.",
};

function pct(n: number | null | undefined, decimals = 0) {
  if (n == null) return "—";
  return `${(n * 100).toFixed(decimals)}%`;
}

type TabKey = "overview" | "diagnoses" | "feedback" | "coverage" | "learning" | "fleet" | "modes" | "telematics";

const TABS: { key: TabKey; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "diagnoses", label: "Top Diagnoses" },
  { key: "feedback", label: "Feedback" },
  { key: "coverage", label: "Tree Coverage" },
  { key: "learning", label: "Learning" },
  { key: "fleet", label: "Fleet" },
  { key: "modes", label: "Modes" },
  { key: "telematics", label: "Telematics" },
];

// ── Shared components ─────────────────────────────────────────────────────────

function StarRating({ rating }: { rating: number | null }) {
  if (!rating) return <span className="text-slate-400 text-sm">—</span>;
  return (
    <span className="text-yellow-400 text-sm">
      {"★".repeat(Math.round(rating))}
      {"☆".repeat(5 - Math.round(rating))}
      <span className="text-slate-500 ml-1">({rating.toFixed(1)})</span>
    </span>
  );
}

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-slate-800 rounded-2xl p-4 flex flex-col gap-1">
      <span className="text-slate-400 text-xs uppercase tracking-wider">{label}</span>
      <span className="text-white text-2xl font-bold tabular-nums">{value}</span>
      {sub && <span className="text-slate-500 text-xs">{sub}</span>}
    </div>
  );
}

function TabLoading() {
  return (
    <div className="flex items-center justify-center py-16 text-slate-500 text-sm">
      Loading…
    </div>
  );
}

function TabEmpty() {
  return (
    <p className="text-slate-500 text-sm text-center py-12">No data yet.</p>
  );
}

// ── Mini bar chart (CSS only) ─────────────────────────────────────────────────

function BarChart({ data }: { data: DailyCount[] }) {
  if (!data.length) return <p className="text-slate-500 text-sm">No data yet.</p>;
  const max = Math.max(...data.map((d) => d.count), 1);
  return (
    <div className="flex items-end gap-0.5 h-24 w-full">
      {data.map((d) => (
        <div
          key={d.day}
          title={`${d.day}: ${d.count}`}
          className="flex-1 bg-cyan-500 rounded-t hover:bg-cyan-400 transition-colors min-w-0"
          style={{ height: `${Math.max(2, (d.count / max) * 100)}%` }}
        />
      ))}
    </div>
  );
}

// ── Coverage grid ─────────────────────────────────────────────────────────────

function CoverageGrid({ matrix, vehicleTypes }: { matrix: CoverageRow[]; vehicleTypes: string[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="text-xs w-full border-collapse">
        <thead>
          <tr>
            <th className="text-left text-slate-400 py-1 pr-3 font-normal">Symptom</th>
            {vehicleTypes.map((vt) => (
              <th key={vt} className="text-slate-400 font-normal px-1 text-center">
                {VT_LABELS[vt] ?? vt}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row) => (
            <tr key={row.symptom} className="border-t border-slate-700/50">
              <td className="text-slate-300 py-1 pr-3 whitespace-nowrap">
                {SYMPTOM_LABELS[row.symptom] ?? row.symptom}
              </td>
              {vehicleTypes.map((vt) => {
                const cell = row.vehicles[vt];
                return (
                  <td key={vt} className="text-center px-1 py-1">
                    <span
                      title={`${cell?.session_count ?? 0} sessions`}
                      className={`inline-block w-5 h-5 rounded text-xs leading-5 text-center ${
                        cell?.has_tree
                          ? "bg-green-700 text-green-200"
                          : "bg-slate-700 text-slate-500"
                      }`}
                    >
                      {cell?.has_tree ? "✓" : "·"}
                    </span>
                    {(cell?.session_count ?? 0) > 0 && (
                      <div className="text-slate-500 text-[10px] leading-none">
                        {cell.session_count}
                      </div>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function AdminPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  // ── Existing tab state ────────────────────────────────────────────────────
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [timeSeries, setTimeSeries] = useState<DailyCount[]>([]);
  const [topDx, setTopDx] = useState<TopDiagnosis[]>([]);
  const [feedback, setFeedback] = useState<FeedbackEntry[]>([]);
  const [distribution, setDistribution] = useState<Record<number, number>>({});
  const [coverage, setCoverage] = useState<{ matrix: CoverageRow[]; vehicleTypes: string[] } | null>(null);
  const [commentsOnly, setCommentsOnly] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [loadedTabs, setLoadedTabs] = useState<Set<string>>(new Set());

  // ── Learning tab state ────────────────────────────────────────────────────
  const [insights, setInsights] = useState<LearningInsight[]>([]);
  const [adjustments, setAdjustments] = useState<WeightAdjustment[]>([]);
  const [metrics, setMetrics] = useState<Record<string, HypothesisMetric>>({});
  const [learningLoading, setLearningLoading] = useState(false);
  const [multiplierInputs, setMultiplierInputs] = useState<Record<string, string>>({});

  // ── Fleet tab state ───────────────────────────────────────────────────────
  const [fleetSummary, setFleetSummary] = useState<FleetSummary | null>(null);
  const [fleetPatterns, setFleetPatterns] = useState<FleetPattern[]>([]);
  const [fleetSummaryText, setFleetSummaryText] = useState("");
  const [fleetLoading, setFleetLoading] = useState(false);

  // ── Modes tab state ───────────────────────────────────────────────────────
  const [modeMetrics, setModeMetrics] = useState<Record<string, ModeMetrics>>({});
  const [modeSummaries, setModeSummaries] = useState<Record<string, string>>({});
  const [modeComparison, setModeComparison] = useState<ModeComparison[]>([]);
  const [modesLoading, setModesLoading] = useState(false);

  // ── Telematics tab state ──────────────────────────────────────────────────
  const [telemetry, setTelemetry] = useState<TelemetryReading[]>([]);
  const [telemetryAsset, setTelemetryAsset] = useState("");
  const [telemetryAssetInput, setTelemetryAssetInput] = useState("");
  const [telemetryLoading, setTelemetryLoading] = useState(false);

  function markLoaded(tab: string) {
    setLoadedTabs((prev) => new Set([...prev, tab]));
  }

  // ── Initial load (existing tabs) ──────────────────────────────────────────
  useEffect(() => {
    if (authLoading) return;
    if (!user) { router.push("/login"); return; }
    if (!user.is_admin) { router.push("/"); return; }

    Promise.all([
      getAdminStats(),
      getSessionsOverTime(30),
      getTopDiagnoses(20),
      getFeedback(30, false),
      getCoverage(),
    ])
      .then(([s, ts, dx, fb, cov]) => {
        setStats(s);
        setTimeSeries(ts.data);
        setTopDx(dx.data);
        setFeedback(fb.data);
        setDistribution(fb.distribution);
        setCoverage({ matrix: cov.matrix, vehicleTypes: cov.vehicle_types });
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [authLoading, user, router]);

  // Reload feedback when commentsOnly changes
  useEffect(() => {
    if (!stats) return;
    getFeedback(30, commentsOnly).then((fb) => {
      setFeedback(fb.data);
      setDistribution(fb.distribution);
    });
  }, [commentsOnly]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Lazy load: Learning tab ───────────────────────────────────────────────
  useEffect(() => {
    if (activeTab !== "learning" || loadedTabs.has("learning")) return;
    setLearningLoading(true);
    Promise.all([getLearningInsights(), getLearningAdjustments(), getLearningMetrics()])
      .then(([ins, adj, met]) => {
        setInsights(ins.insights);
        setAdjustments(adj.adjustments);
        const inputs: Record<string, string> = {};
        adj.adjustments.forEach((a) => {
          inputs[a.hypothesis_id] = String(a.suggested_multiplier);
        });
        setMultiplierInputs(inputs);
        setMetrics(met.metrics);
      })
      .catch(() => {/* silently show empty state */})
      .finally(() => { setLearningLoading(false); markLoaded("learning"); });
  }, [activeTab]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Lazy load: Fleet tab ──────────────────────────────────────────────────
  useEffect(() => {
    if (activeTab !== "fleet" || loadedTabs.has("fleet")) return;
    setFleetLoading(true);
    Promise.all([getFleetHeavy(), getFleetHeavyPatterns()])
      .then(([heavy, patterns]) => {
        setFleetSummary(heavy.summary);
        setFleetSummaryText(patterns.fleet_summary);
        const allPatterns: FleetPattern[] = [
          ...patterns.hours_failure_patterns,
          ...patterns.environment_patterns,
          ...patterns.unresolved_clusters,
          ...patterns.safety_hotspots,
          ...patterns.contradiction_hotspots,
        ];
        setFleetPatterns(allPatterns);
      })
      .catch(() => {})
      .finally(() => { setFleetLoading(false); markLoaded("fleet"); });
  }, [activeTab]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Lazy load: Modes tab ──────────────────────────────────────────────────
  useEffect(() => {
    if (activeTab !== "modes" || loadedTabs.has("modes")) return;
    setModesLoading(true);
    Promise.all([getModeAnalytics(), getModeComparison()])
      .then(([analytics, comparison]) => {
        setModeMetrics(analytics.metrics);
        setModeSummaries(analytics.summaries);
        setModeComparison(comparison.comparison);
      })
      .catch(() => {})
      .finally(() => { setModesLoading(false); markLoaded("modes"); });
  }, [activeTab]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Lazy load: Telematics tab ─────────────────────────────────────────────
  useEffect(() => {
    if (activeTab !== "telematics" || loadedTabs.has("telematics")) return;
    setTelemetryLoading(true);
    getRecentTelemetry(50)
      .then((res) => setTelemetry(res.readings))
      .catch(() => {})
      .finally(() => { setTelemetryLoading(false); markLoaded("telematics"); });
  }, [activeTab]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Learning action handlers ───────────────────────────────────────────────
  async function handleApprove(hypothesisId: string) {
    const multiplier = parseFloat(multiplierInputs[hypothesisId] ?? "1");
    if (isNaN(multiplier) || multiplier <= 0) return;
    await approveLearningAdjustment(hypothesisId, multiplier);
    setAdjustments((prev) =>
      prev.map((a) =>
        a.hypothesis_id === hypothesisId
          ? { ...a, is_approved: true, current_approved_multiplier: multiplier }
          : a
      )
    );
  }

  async function handleReject(hypothesisId: string) {
    await rejectLearningAdjustment(hypothesisId);
    setAdjustments((prev) =>
      prev.map((a) =>
        a.hypothesis_id === hypothesisId ? { ...a, is_approved: false } : a
      )
    );
  }

  function handleTelemetryFilter() {
    setTelemetryLoading(true);
    const assetId = telemetryAssetInput.trim() || undefined;
    setTelemetryAsset(telemetryAssetInput.trim());
    getRecentTelemetry(50, assetId)
      .then((res) => setTelemetry(res.readings))
      .catch(() => {})
      .finally(() => setTelemetryLoading(false));
  }

  // ── Render guards ─────────────────────────────────────────────────────────
  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center text-slate-400 text-sm">
        Loading…
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center text-red-400 text-sm">
        {error}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      {/* Header */}
      <div className="border-b border-slate-700/50 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/")}
            className="text-slate-400 hover:text-white text-sm transition-colors cursor-pointer"
          >
            ← Back
          </button>
          <h1 className="text-white font-semibold">Fix — Admin</h1>
        </div>
        <span className="text-slate-500 text-xs">{user?.email}</span>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-700/50 px-6 flex gap-1 overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap cursor-pointer ${
              activeTab === t.key
                ? "border-cyan-500 text-white"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="px-6 py-6 max-w-6xl mx-auto">
        {/* ── Overview ── */}
        {activeTab === "overview" && stats && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <StatCard label="Total Sessions" value={stats.total_sessions.toLocaleString()} />
              <StatCard label="Total Users" value={stats.total_users.toLocaleString()} />
              <StatCard
                label="Avg Rating"
                value={stats.avg_rating ? `${stats.avg_rating.toFixed(1)} / 5` : "—"}
                sub={`${stats.rated_sessions} rated`}
              />
              <StatCard label="This Week" value={stats.sessions_this_week.toLocaleString()} sub="sessions" />
              <StatCard label="Completed" value={stats.completed_sessions.toLocaleString()} sub="sessions" />
              <StatCard
                label="Completion Rate"
                value={
                  stats.total_sessions > 0
                    ? `${Math.round((stats.completed_sessions / stats.total_sessions) * 100)}%`
                    : "—"
                }
              />
            </div>

            <div className="bg-slate-800 rounded-2xl p-4">
              <h2 className="text-sm font-medium text-slate-300 mb-3">Sessions — Last 30 Days</h2>
              <BarChart data={timeSeries} />
              <div className="flex justify-between text-slate-600 text-[10px] mt-1">
                <span>{timeSeries[0]?.day ?? ""}</span>
                <span>{timeSeries[timeSeries.length - 1]?.day ?? ""}</span>
              </div>
            </div>
          </div>
        )}

        {/* ── Top Diagnoses ── */}
        {activeTab === "diagnoses" && (
          <div className="bg-slate-800 rounded-2xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700/50">
                  <th className="text-left px-4 py-3 text-slate-400 font-normal">Symptom</th>
                  <th className="text-left px-4 py-3 text-slate-400 font-normal">Vehicle</th>
                  <th className="text-right px-4 py-3 text-slate-400 font-normal">Sessions</th>
                  <th className="text-right px-4 py-3 text-slate-400 font-normal">Avg Rating</th>
                  <th className="text-right px-4 py-3 text-slate-400 font-normal">Rated</th>
                </tr>
              </thead>
              <tbody>
                {topDx.map((d, i) => (
                  <tr key={i} className="border-b border-slate-700/50 hover:bg-slate-700/30 transition-colors">
                    <td className="px-4 py-2 text-slate-200">
                      {SYMPTOM_LABELS[d.symptom_category] ?? d.symptom_category}
                    </td>
                    <td className="px-4 py-2 text-slate-400">
                      {VT_LABELS[d.vehicle_type] ?? d.vehicle_type}
                    </td>
                    <td className="px-4 py-2 text-right text-white font-medium tabular-nums">
                      {d.session_count}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <StarRating rating={d.avg_rating} />
                    </td>
                    <td className="px-4 py-2 text-right text-slate-500 tabular-nums">{d.rated_count}</td>
                  </tr>
                ))}
                {topDx.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                      No sessions yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* ── Feedback ── */}
        {activeTab === "feedback" && (
          <div className="space-y-4">
            <div className="bg-slate-800 rounded-2xl p-4">
              <h2 className="text-sm font-medium text-slate-300 mb-3">Rating Distribution</h2>
              <div className="flex gap-4">
                {[5, 4, 3, 2, 1].map((star) => {
                  const count = distribution[star] ?? 0;
                  const total = Object.values(distribution).reduce((a, b) => a + b, 0);
                  const p = total > 0 ? Math.round((count / total) * 100) : 0;
                  return (
                    <div key={star} className="flex-1 text-center">
                      <div className="text-yellow-400 text-sm">{"★".repeat(star)}</div>
                      <div className="text-white font-bold tabular-nums">{count}</div>
                      <div className="text-slate-500 text-xs tabular-nums">{p}%</div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="flex items-center justify-between">
              <h2 className="text-sm font-medium text-slate-300">Recent Feedback</h2>
              <label className="flex items-center gap-2 text-sm text-slate-400 cursor-pointer">
                <input
                  type="checkbox"
                  checked={commentsOnly}
                  onChange={(e) => setCommentsOnly(e.target.checked)}
                  className="rounded accent-cyan-500"
                />
                Comments only
              </label>
            </div>

            <div className="space-y-2">
              {feedback.map((fb) => (
                <div key={fb.session_id} className="bg-slate-800 rounded-2xl p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-yellow-400 text-sm">
                          {"★".repeat(fb.rating)}{"☆".repeat(5 - fb.rating)}
                        </span>
                        <span className="text-slate-500 text-xs">
                          {SYMPTOM_LABELS[fb.symptom_category ?? ""] ?? fb.symptom_category ?? "unknown"}
                        </span>
                        <span className="text-slate-600 text-xs">·</span>
                        <span className="text-slate-500 text-xs">
                          {VT_LABELS[fb.vehicle_type ?? ""] ?? fb.vehicle_type ?? "car"}
                        </span>
                        {fb.vehicle_make && (
                          <>
                            <span className="text-slate-600 text-xs">·</span>
                            <span className="text-slate-500 text-xs">
                              {[fb.vehicle_year, fb.vehicle_make, fb.vehicle_model]
                                .filter(Boolean)
                                .join(" ")}
                            </span>
                          </>
                        )}
                      </div>
                      {fb.comment && (
                        <p className="text-slate-300 text-sm mt-1">{fb.comment}</p>
                      )}
                    </div>
                    <span className="text-slate-600 text-xs whitespace-nowrap flex-shrink-0">
                      {fb.created_at ? new Date(fb.created_at).toLocaleDateString() : ""}
                    </span>
                  </div>
                </div>
              ))}
              {feedback.length === 0 && (
                <p className="text-slate-500 text-sm text-center py-8">No feedback yet.</p>
              )}
            </div>
          </div>
        )}

        {/* ── Tree Coverage ── */}
        {activeTab === "coverage" && coverage && (
          <div className="space-y-4">
            <div className="flex items-center gap-4 text-xs text-slate-400">
              <span className="flex items-center gap-1">
                <span className="inline-block w-4 h-4 rounded bg-green-700 text-center leading-4 text-green-200">✓</span>
                Dedicated tree exists
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block w-4 h-4 rounded bg-slate-700 text-center leading-4 text-slate-500">·</span>
                Falls back to base car tree
              </span>
            </div>
            <div className="bg-slate-800 rounded-2xl p-4">
              <CoverageGrid matrix={coverage.matrix} vehicleTypes={coverage.vehicleTypes} />
            </div>
          </div>
        )}

        {/* ── Learning ── */}
        {activeTab === "learning" && (
          <div className="space-y-6">
            {learningLoading ? (
              <TabLoading />
            ) : (
              <>
                {/* AI Insights */}
                <div>
                  <h2 className="text-sm font-semibold text-slate-300 mb-3">AI Insights</h2>
                  {insights.length === 0 ? (
                    <TabEmpty />
                  ) : (
                    <div className="space-y-3">
                      {insights
                        .slice()
                        .sort((a, b) => a.priority - b.priority)
                        .map((ins, i) => {
                          const borderColor =
                            ins.type === "critical"
                              ? "border-red-500"
                              : ins.type === "warning"
                              ? "border-yellow-500"
                              : "border-cyan-600";
                          const badgeColor =
                            ins.type === "critical"
                              ? "bg-red-900/60 text-red-300"
                              : ins.type === "warning"
                              ? "bg-yellow-900/60 text-yellow-300"
                              : "bg-cyan-900/60 text-cyan-300";
                          return (
                            <div
                              key={i}
                              className={`bg-slate-800 rounded-2xl p-4 border-l-4 ${borderColor}`}
                            >
                              <div className="flex items-center gap-2 mb-1">
                                <span
                                  className={`text-xs px-2 py-0.5 rounded-full font-medium uppercase ${badgeColor}`}
                                >
                                  {ins.type}
                                </span>
                                <span className="text-slate-500 text-xs">Priority {ins.priority}</span>
                              </div>
                              <p className="text-white text-sm font-medium">{ins.title}</p>
                              <p className="text-slate-400 text-sm mt-1">{ins.description}</p>
                              {ins.affected.length > 0 && (
                                <p className="text-slate-500 text-xs mt-2">
                                  Affected: {ins.affected.join(", ")}
                                </p>
                              )}
                              <p className="text-slate-400 text-xs italic mt-1">{ins.suggested_action}</p>
                            </div>
                          );
                        })}
                    </div>
                  )}
                </div>

                {/* Weight Adjustments */}
                <div>
                  <h2 className="text-sm font-semibold text-slate-300 mb-3">Pending Weight Adjustments</h2>
                  {adjustments.length === 0 ? (
                    <TabEmpty />
                  ) : (
                    <div className="bg-slate-800 rounded-2xl overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-slate-700/50 text-slate-400 text-xs">
                            <th className="text-left px-4 py-3 font-normal">Hypothesis</th>
                            <th className="text-right px-4 py-3 font-normal">Base</th>
                            <th className="text-right px-4 py-3 font-normal">Suggested ×</th>
                            <th className="text-right px-4 py-3 font-normal">Confidence</th>
                            <th className="text-left px-4 py-3 font-normal">Reason</th>
                            <th className="text-center px-4 py-3 font-normal">Status</th>
                            <th className="text-center px-4 py-3 font-normal">Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {adjustments.map((adj) => (
                            <tr key={adj.hypothesis_id} className="border-b border-slate-700/50">
                              <td className="px-4 py-3 text-slate-200 font-mono text-xs">
                                {adj.hypothesis_id}
                              </td>
                              <td className="px-4 py-3 text-right text-slate-400 tabular-nums">
                                {adj.base_weight.toFixed(2)}
                              </td>
                              <td className="px-4 py-3 text-right text-slate-300 tabular-nums">
                                ×{adj.suggested_multiplier.toFixed(2)}
                              </td>
                              <td className="px-4 py-3 text-right text-slate-400 tabular-nums">
                                {pct(adj.confidence)}
                              </td>
                              <td className="px-4 py-3 text-slate-400 text-xs max-w-xs">
                                {adj.reason}
                              </td>
                              <td className="px-4 py-3 text-center">
                                {adj.is_approved ? (
                                  <span className="text-xs bg-green-900/60 text-green-300 px-2 py-0.5 rounded-full">
                                    Approved ×{adj.current_approved_multiplier?.toFixed(2)}
                                  </span>
                                ) : (
                                  <span className="text-xs bg-slate-700 text-slate-400 px-2 py-0.5 rounded-full">
                                    Pending
                                  </span>
                                )}
                              </td>
                              <td className="px-4 py-3">
                                <div className="flex items-center gap-2 justify-center">
                                  <input
                                    type="number"
                                    step="0.1"
                                    min="0.1"
                                    value={multiplierInputs[adj.hypothesis_id] ?? ""}
                                    onChange={(e) =>
                                      setMultiplierInputs((prev) => ({
                                        ...prev,
                                        [adj.hypothesis_id]: e.target.value,
                                      }))
                                    }
                                    className="w-16 bg-slate-700 text-white text-xs text-center rounded-lg px-1 py-1 border border-slate-600 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                                  />
                                  <button
                                    onClick={() => handleApprove(adj.hypothesis_id)}
                                    className="text-xs bg-green-700 hover:bg-green-600 text-white px-2 py-1 rounded-lg transition-colors cursor-pointer"
                                  >
                                    Approve
                                  </button>
                                  <button
                                    onClick={() => handleReject(adj.hypothesis_id)}
                                    className="text-xs bg-red-800 hover:bg-red-700 text-white px-2 py-1 rounded-lg transition-colors cursor-pointer"
                                  >
                                    Reject
                                  </button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* Metrics table */}
                <div>
                  <h2 className="text-sm font-semibold text-slate-300 mb-3">Hypothesis Metrics</h2>
                  {Object.keys(metrics).length === 0 ? (
                    <TabEmpty />
                  ) : (
                    <div className="bg-slate-800 rounded-2xl overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-slate-700/50 text-slate-400 text-xs">
                            <th className="text-left px-4 py-3 font-normal">Hypothesis</th>
                            <th className="text-right px-4 py-3 font-normal">Cases</th>
                            <th className="text-right px-4 py-3 font-normal">Resolution</th>
                            <th className="text-right px-4 py-3 font-normal">Reversal</th>
                            <th className="text-right px-4 py-3 font-normal">Avg Rating</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.values(metrics)
                            .sort((a, b) => b.total_cases - a.total_cases)
                            .map((m) => (
                              <tr key={m.hypothesis_id} className="border-b border-slate-700/50">
                                <td className="px-4 py-2 text-slate-200 font-mono text-xs">
                                  {m.hypothesis_id}
                                </td>
                                <td className="px-4 py-2 text-right text-slate-300 tabular-nums">{m.total_cases}</td>
                                <td className="px-4 py-2 text-right text-slate-300 tabular-nums">
                                  {pct(m.resolution_rate)}
                                </td>
                                <td className="px-4 py-2 text-right text-slate-400 tabular-nums">
                                  {pct(m.reversal_rate)}
                                </td>
                                <td className="px-4 py-2 text-right">
                                  <StarRating rating={m.avg_rating} />
                                </td>
                              </tr>
                            ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        )}

        {/* ── Fleet ── */}
        {activeTab === "fleet" && (
          <div className="space-y-6">
            {fleetLoading ? (
              <TabLoading />
            ) : !fleetSummary ? (
              <TabEmpty />
            ) : (
              <>
                {/* Summary cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <StatCard
                    label="HE Sessions"
                    value={fleetSummary.total_sessions.toLocaleString()}
                  />
                  <StatCard
                    label="Resolved"
                    value={pct(
                      fleetSummary.total_sessions > 0
                        ? fleetSummary.resolved_count / fleetSummary.total_sessions
                        : null
                    )}
                    sub={`${fleetSummary.resolved_count} sessions`}
                  />
                  <StatCard
                    label="Safety Triggered"
                    value={fleetSummary.safety_triggered_count.toLocaleString()}
                  />
                  <StatCard
                    label="Avg Rating"
                    value={fleetSummary.avg_rating ? fleetSummary.avg_rating.toFixed(1) : "—"}
                  />
                </div>

                {/* LLM fleet summary */}
                {fleetSummaryText && (
                  <div className="bg-slate-800 rounded-2xl p-4">
                    <h2 className="text-sm font-semibold text-slate-300 mb-2">Fleet Summary (AI)</h2>
                    <p className="text-slate-400 text-sm leading-relaxed">{fleetSummaryText}</p>
                  </div>
                )}

                {/* Breakdowns */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* By environment */}
                  <div className="bg-slate-800 rounded-2xl p-4">
                    <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                      By Environment
                    </h2>
                    {Object.entries(fleetSummary.by_environment).length === 0 ? (
                      <TabEmpty />
                    ) : (
                      <table className="w-full text-sm">
                        <tbody>
                          {Object.entries(fleetSummary.by_environment)
                            .sort(([, a], [, b]) => b - a)
                            .map(([env, count]) => (
                              <tr key={env}>
                                <td className="text-slate-300 py-1 capitalize">{env}</td>
                                <td className="text-right text-white font-medium tabular-nums">{count}</td>
                              </tr>
                            ))}
                        </tbody>
                      </table>
                    )}
                  </div>

                  {/* By mode */}
                  <div className="bg-slate-800 rounded-2xl p-4">
                    <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                      By Mode
                    </h2>
                    {Object.entries(fleetSummary.by_mode).length === 0 ? (
                      <TabEmpty />
                    ) : (
                      <table className="w-full text-sm">
                        <tbody>
                          {Object.entries(fleetSummary.by_mode)
                            .sort(([, a], [, b]) => b - a)
                            .map(([mode, count]) => (
                              <tr key={mode}>
                                <td className="text-slate-300 py-1 capitalize">{mode}</td>
                                <td className="text-right text-white font-medium tabular-nums">{count}</td>
                              </tr>
                            ))}
                        </tbody>
                      </table>
                    )}
                  </div>

                  {/* Top trees */}
                  <div className="bg-slate-800 rounded-2xl p-4">
                    <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                      Top Trees
                    </h2>
                    {fleetSummary.by_tree.length === 0 ? (
                      <TabEmpty />
                    ) : (
                      <table className="w-full text-sm">
                        <tbody>
                          {fleetSummary.by_tree.slice(0, 8).map(({ tree, count }) => (
                            <tr key={tree}>
                              <td className="text-slate-300 py-1 font-mono text-xs">{tree}</td>
                              <td className="text-right text-white font-medium tabular-nums">{count}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                </div>

                {/* Patterns */}
                <div>
                  <h2 className="text-sm font-semibold text-slate-300 mb-3">Detected Patterns</h2>
                  {fleetPatterns.length === 0 ? (
                    <TabEmpty />
                  ) : (
                    <div className="space-y-2">
                      {fleetPatterns.map((p, i) => (
                        <div key={i} className="bg-slate-800 rounded-2xl p-4">
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1 min-w-0">
                              <div className="flex flex-wrap gap-2 mb-1">
                                <span className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full">
                                  {p.pattern_type.replace(/_/g, " ")}
                                </span>
                                {p.tree_key && (
                                  <span className="text-xs bg-slate-700 text-slate-400 px-2 py-0.5 rounded-full font-mono">
                                    {p.tree_key}
                                  </span>
                                )}
                                {p.environment && (
                                  <span className="text-xs bg-slate-700 text-slate-400 px-2 py-0.5 rounded-full capitalize">
                                    {p.environment}
                                  </span>
                                )}
                                {p.hours_band && (
                                  <span className="text-xs bg-slate-700 text-slate-400 px-2 py-0.5 rounded-full">
                                    {p.hours_band}
                                  </span>
                                )}
                              </div>
                              <p className="text-slate-300 text-sm">{p.description}</p>
                            </div>
                            <div className="text-right flex-shrink-0 space-y-1">
                              <div className="text-white font-medium text-sm tabular-nums">{p.session_count} sessions</div>
                              {p.unresolved_rate != null && (
                                <div className="text-slate-400 text-xs tabular-nums">{pct(p.unresolved_rate)} unresolved</div>
                              )}
                              {p.safety_trigger_rate != null && p.safety_trigger_rate > 0 && (
                                <div className="text-red-400 text-xs tabular-nums">{pct(p.safety_trigger_rate)} safety</div>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        )}

        {/* ── Modes ── */}
        {activeTab === "modes" && (
          <div className="space-y-6">
            {modesLoading ? (
              <TabLoading />
            ) : Object.keys(modeMetrics).length === 0 ? (
              <TabEmpty />
            ) : (
              <>
                {/* Mode cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {Object.values(modeMetrics).map((m) => (
                    <div key={m.mode} className="bg-slate-800 rounded-2xl p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <h2 className="text-white font-semibold capitalize">{m.mode}</h2>
                        <span className="text-slate-500 text-sm tabular-nums">{m.session_count} sessions</span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <div className="text-slate-500">Resolution</div>
                          <div className="text-white font-medium tabular-nums">{pct(m.resolution_rate)}</div>
                        </div>
                        <div>
                          <div className="text-slate-500">Avg Rating</div>
                          <div className="text-white font-medium tabular-nums">
                            {m.avg_rating ? m.avg_rating.toFixed(1) : "—"}
                          </div>
                        </div>
                        <div>
                          <div className="text-slate-500">Contradiction</div>
                          <div className="text-white font-medium tabular-nums">{pct(m.contradiction_rate)}</div>
                        </div>
                        <div>
                          <div className="text-slate-500">Safety Triggered</div>
                          <div className="text-white font-medium tabular-nums">{pct(m.safety_trigger_rate)}</div>
                        </div>
                        <div>
                          <div className="text-slate-500">Reroute Rate</div>
                          <div className="text-white font-medium tabular-nums">{pct(m.reroute_rate)}</div>
                        </div>
                        <div>
                          <div className="text-slate-500">Early Exit</div>
                          <div className="text-white font-medium tabular-nums">{pct(m.early_exit_rate)}</div>
                        </div>
                      </div>
                      {modeSummaries[m.mode] && (
                        <p className="text-slate-400 text-xs border-t border-slate-700/50 pt-2 leading-relaxed">
                          {modeSummaries[m.mode]}
                        </p>
                      )}
                    </div>
                  ))}
                </div>

                {/* Comparison table */}
                {modeComparison.length > 0 && (
                  <div>
                    <h2 className="text-sm font-semibold text-slate-300 mb-3">Mode Comparison</h2>
                    <div className="bg-slate-800 rounded-2xl overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-slate-700/50 text-slate-400 text-xs">
                            <th className="text-left px-4 py-3 font-normal">Metric</th>
                            {Object.keys(modeComparison[0]?.by_mode ?? {}).map((mode) => (
                              <th key={mode} className="text-right px-4 py-3 font-normal capitalize">
                                {mode}
                              </th>
                            ))}
                            <th className="text-right px-4 py-3 font-normal">Spread</th>
                          </tr>
                        </thead>
                        <tbody>
                          {modeComparison.map((row) => (
                            <tr key={row.metric} className="border-b border-slate-700/50">
                              <td className="px-4 py-2 text-slate-300">{row.metric.replace(/_/g, " ")}</td>
                              {Object.entries(row.by_mode).map(([mode, val]) => {
                                const isBest = mode === row.best_mode;
                                const isWorst = mode === row.worst_mode;
                                return (
                                  <td
                                    key={mode}
                                    className={`px-4 py-2 text-right font-medium tabular-nums ${
                                      isBest
                                        ? "text-green-400"
                                        : isWorst
                                        ? "text-red-400"
                                        : "text-slate-300"
                                    }`}
                                  >
                                    {val != null ? (val < 1 ? pct(val) : val.toFixed(2)) : "—"}
                                  </td>
                                );
                              })}
                              <td className="px-4 py-2 text-right text-slate-500 text-xs tabular-nums">
                                {row.spread.toFixed(2)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ── Telematics ── */}
        {activeTab === "telematics" && (
          <div className="space-y-4">
            {/* Asset filter */}
            <div className="flex items-center gap-3">
              <input
                type="text"
                placeholder="Filter by asset ID…"
                value={telemetryAssetInput}
                onChange={(e) => setTelemetryAssetInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleTelemetryFilter()}
                className="bg-slate-800 border border-slate-700/50 rounded-xl px-3 py-2 text-sm text-white placeholder-slate-500 flex-1 max-w-xs focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition"
              />
              <button
                onClick={handleTelemetryFilter}
                className="bg-cyan-700 hover:bg-cyan-600 text-white text-sm px-4 py-2 rounded-xl transition-colors cursor-pointer"
              >
                Load
              </button>
              {telemetryAsset && (
                <span className="text-slate-500 text-xs">
                  Filtered: {telemetryAsset}
                </span>
              )}
            </div>

            {telemetryLoading ? (
              <TabLoading />
            ) : telemetry.length === 0 ? (
              <TabEmpty />
            ) : (
              <div className="space-y-2">
                {telemetry.map((r) => (
                  <div key={r.telemetry_id} className="bg-slate-800 rounded-2xl p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0 space-y-2">
                        <div className="flex items-center gap-3 flex-wrap">
                          <span className="text-white font-mono text-sm">{r.asset_id}</span>
                          <span className="text-slate-500 text-xs">
                            {new Date(r.received_at).toLocaleString()}
                          </span>
                          {r.safety_count > 0 && (
                            <span className="bg-red-900/60 text-red-300 text-xs px-2 py-0.5 rounded-full font-medium">
                              {r.safety_count} safety alert{r.safety_count > 1 ? "s" : ""}
                            </span>
                          )}
                          {r.linked_session_id && (
                            <span className="bg-slate-700 text-slate-300 text-xs px-2 py-0.5 rounded-lg font-mono">
                              session: {r.linked_session_id.slice(0, 8)}…
                            </span>
                          )}
                        </div>

                        {/* Signal chips */}
                        <div className="flex flex-wrap gap-2">
                          {r.raw.engine_temp_c != null && (
                            <span className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full">
                              Temp {r.raw.engine_temp_c}°C
                            </span>
                          )}
                          {r.raw.voltage_v != null && (
                            <span className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full">
                              {r.raw.voltage_v}V
                            </span>
                          )}
                          {r.raw.pressure_psi != null && (
                            <span className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full">
                              {r.raw.pressure_psi} PSI
                            </span>
                          )}
                          {r.raw.fuel_level_pct != null && (
                            <span className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full">
                              Fuel {r.raw.fuel_level_pct}%
                            </span>
                          )}
                          {(r.raw.fault_codes ?? []).map((code) => (
                            <span
                              key={code}
                              className="text-xs bg-red-900/60 text-red-300 px-2 py-0.5 rounded-full font-mono"
                            >
                              {code}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
