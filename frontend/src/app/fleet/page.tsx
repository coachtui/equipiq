"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import {
  getFleetAssets,
  getFleetSummary,
  getAssetHistory,
  getFleetPriorities,
  type FleetAsset,
  type FleetSummaryData,
  type AssetHistory,
  type AssetRisk,
} from "@/lib/fleet";

const SYMPTOM_LABELS: Record<string, string> = {
  no_start: "No Start",
  hydraulic_loss: "Hydraulic Loss",
  electrical_fault: "Electrical Fault",
  track_or_drive_issue: "Track / Drive",
  abnormal_noise: "Abnormal Noise",
  coolant_leak: "Coolant Leak",
  implement_failure: "Implement Failure",
  cab_electrical: "Cab Electrical",
  fuel_contamination: "Fuel Contamination",
  overheating: "Overheating",
  loss_of_power: "Loss of Power",
};

const VEHICLE_LABELS: Record<string, string> = {
  tractor: "Tractor",
  excavator: "Excavator",
  loader: "Loader",
  skid_steer: "Skid Steer",
  heavy_equipment: "Heavy Equipment",
  truck: "Truck",
};

const RISK_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-800 border-red-200",
  high:     "bg-orange-100 text-orange-800 border-orange-200",
  medium:   "bg-yellow-100 text-yellow-800 border-yellow-200",
  low:      "bg-green-100 text-green-800 border-green-200",
};

const RISK_BORDER: Record<string, string> = {
  critical: "border-red-200",
  high:     "border-orange-200",
  medium:   "border-yellow-200",
  low:      "border-gray-100",
};

const RISK_LABELS: Record<string, string> = {
  critical: "Critical",
  high:     "High",
  medium:   "Medium",
  low:      "Low",
};

// ── Sub-components ────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: "bg-yellow-100 text-yellow-800",
    awaiting_followup: "bg-cyan-100 text-cyan-800",
    completed: "bg-green-100 text-green-800",
  };
  const labels: Record<string, string> = {
    active: "Active",
    awaiting_followup: "Awaiting Follow-up",
    completed: "Completed",
  };
  return (
    <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-medium ${colors[status] ?? "bg-gray-100 text-gray-700"}`}>
      {labels[status] ?? status}
    </span>
  );
}

function RiskBadge({ level }: { level: string }) {
  return (
    <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold border ${RISK_COLORS[level] ?? "bg-gray-100 text-gray-700 border-gray-200"}`}>
      {RISK_LABELS[level] ?? level}
    </span>
  );
}

function AssetCard({ asset, onSelect }: { asset: FleetAsset; onSelect: () => void }) {
  const hasSafetyAlert = asset.last_safety_alerts?.length > 0;
  const hasOpenIssue = asset.open_sessions > 0;

  return (
    <button
      onClick={onSelect}
      className="w-full text-left bg-white border border-gray-100 rounded-2xl p-4 hover:border-cyan-300 hover:shadow-card-hover transition-all min-h-[44px] cursor-pointer"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-slate-900 truncate">{asset.asset_id}</span>
            {asset.vehicle_type && (
              <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">
                {VEHICLE_LABELS[asset.vehicle_type] ?? asset.vehicle_type}
              </span>
            )}
            {hasOpenIssue && (
              <span className="text-xs bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full font-medium">
                {asset.open_sessions} open
              </span>
            )}
            {hasSafetyAlert && (
              <span className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded-full font-medium">
                Safety alert
              </span>
            )}
          </div>

          <div className="mt-2 text-sm text-slate-600 space-y-1">
            {asset.last_top_cause && (
              <div>
                <span className="text-slate-400">Last fault: </span>
                <span className="text-slate-700">{asset.last_top_cause}</span>
              </div>
            )}
            {asset.last_symptom && (
              <div>
                <span className="text-slate-400">Last symptom: </span>
                <span>{SYMPTOM_LABELS[asset.last_symptom] ?? asset.last_symptom}</span>
              </div>
            )}
            {asset.last_seen && (
              <div className="text-slate-400 text-xs">
                Last seen: {new Date(asset.last_seen).toLocaleString()}
              </div>
            )}
          </div>
        </div>

        <div className="text-right shrink-0">
          <div className="text-2xl font-bold text-slate-700 tabular-nums">{asset.session_count}</div>
          <div className="text-xs text-slate-400">sessions</div>
        </div>
      </div>
    </button>
  );
}

function AssetRiskCard({
  risk,
  onViewHistory,
}: {
  risk: AssetRisk;
  onViewHistory: (assetId: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={`bg-white border rounded-2xl p-4 ${RISK_BORDER[risk.risk_level] ?? "border-gray-100"}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-slate-900">{risk.asset_id}</span>
            <RiskBadge level={risk.risk_level} />
            <span className="text-xs text-slate-400 font-mono tabular-nums">
              {(risk.risk_score * 100).toFixed(1)}%
            </span>
          </div>

          {/* Recommended action */}
          <p className="mt-2 text-sm text-slate-700 font-medium leading-snug">
            {risk.recommended_action}
          </p>

          {/* Top contributing factor */}
          {risk.contributing_factors.length > 0 && (
            <p className="mt-1 text-xs text-slate-500">
              {risk.contributing_factors[0]}
            </p>
          )}
        </div>

        <div className="shrink-0 flex flex-col gap-1 items-end">
          <button
            onClick={() => onViewHistory(risk.asset_id)}
            className="text-xs text-cyan-600 hover:text-cyan-700 min-h-[44px] flex items-center cursor-pointer transition-colors"
          >
            History
          </button>
        </div>
      </div>

      {/* Expand/collapse factors */}
      {risk.contributing_factors.length > 1 && (
        <button
          onClick={() => setExpanded((v) => !v)}
          className="mt-2 text-xs text-slate-400 hover:text-slate-600 cursor-pointer transition-colors"
        >
          {expanded ? "Hide details" : `+${risk.contributing_factors.length - 1} more factors`}
        </button>
      )}

      {expanded && (
        <div className="mt-2 space-y-1">
          {risk.contributing_factors.slice(1).map((f, i) => (
            <p key={i} className="text-xs text-slate-500">• {f}</p>
          ))}
          {/* Component score breakdown */}
          <div className="mt-2 pt-2 border-t border-gray-100">
            <p className="text-xs text-slate-400 mb-1 font-medium">Score breakdown</p>
            <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
              {Object.entries(risk.component_scores)
                .filter(([, v]) => v > 0)
                .sort(([, a], [, b]) => b - a)
                .map(([key, val]) => (
                  <div key={key} className="flex justify-between text-xs">
                    <span className="text-slate-500 capitalize">{key}</span>
                    <span className="text-slate-700 font-mono tabular-nums">
                      {(val * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function AssetHistoryPanel({ history, onClose }: { history: AssetHistory; onClose: () => void }) {
  return (
    <div className="bg-white border border-gray-100 rounded-2xl p-4 shadow-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-slate-900">{history.asset_id} — Session History</h3>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-slate-600 text-sm min-h-[44px] min-w-[44px] flex items-center justify-center cursor-pointer transition-colors"
        >
          Close
        </button>
      </div>
      {history.sessions.length === 0 ? (
        <p className="text-slate-500 text-sm">No sessions found for this asset.</p>
      ) : (
        <div className="space-y-2">
          {history.sessions.map((s) => (
            <div key={s.session_id} className="border border-gray-100 rounded-xl p-3 text-sm">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-slate-400 text-xs">
                    {s.created_at ? new Date(s.created_at).toLocaleDateString() : "—"}
                  </span>
                  {s.symptom_category && (
                    <span className="font-medium text-slate-800">
                      {SYMPTOM_LABELS[s.symptom_category] ?? s.symptom_category}
                    </span>
                  )}
                </div>
                <StatusBadge status={s.status} />
              </div>
              {s.top_cause && (
                <div className="mt-1 text-slate-600">
                  <span className="text-slate-400">Fault: </span>{s.top_cause}
                </div>
              )}
              <div className="text-slate-400 text-xs mt-0.5 tabular-nums">{s.turn_count} turns</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Filters ───────────────────────────────────────────────────────────────────

type RiskFilter = "all" | "critical" | "high" | "medium" | "low";

function PriorityFilters({
  riskFilter,
  onRiskFilter,
}: {
  riskFilter: RiskFilter;
  onRiskFilter: (v: RiskFilter) => void;
}) {
  const levels: RiskFilter[] = ["all", "critical", "high", "medium", "low"];
  return (
    <div className="flex flex-wrap gap-2">
      {levels.map((level) => (
        <button
          key={level}
          onClick={() => onRiskFilter(level)}
          className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all min-h-[36px] cursor-pointer ${
            riskFilter === level
              ? level === "all"
                ? "bg-slate-900 text-white border-slate-900"
                : `${RISK_COLORS[level]} border-current`
              : "bg-white text-slate-600 border-gray-200 hover:border-gray-300"
          }`}
        >
          {level === "all" ? "All risks" : RISK_LABELS[level]}
        </button>
      ))}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

type ViewMode = "assets" | "priorities";

export default function FleetPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  const [view, setView] = useState<ViewMode>("assets");
  const [assets, setAssets] = useState<FleetAsset[]>([]);
  const [summary, setSummary] = useState<FleetSummaryData | null>(null);
  const [priorities, setPriorities] = useState<AssetRisk[]>([]);
  const [selectedHistory, setSelectedHistory] = useState<AssetHistory | null>(null);
  const [loadingData, setLoadingData] = useState(true);
  const [loadingPriorities, setLoadingPriorities] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [riskFilter, setRiskFilter] = useState<RiskFilter>("all");

  useEffect(() => {
    if (loading) return;
    if (!user || (!user.is_operator && !user.is_admin)) {
      router.replace("/login");
      return;
    }

    Promise.all([getFleetAssets(), getFleetSummary()])
      .then(([a, s]) => {
        setAssets(a);
        setSummary(s);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoadingData(false));
  }, [user, loading, router]);

  const handleViewPriorities = async () => {
    setView("priorities");
    if (priorities.length > 0) return;
    setLoadingPriorities(true);
    try {
      const data = await getFleetPriorities();
      setPriorities(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load priorities");
    } finally {
      setLoadingPriorities(false);
    }
  };

  const handleAssetSelect = async (assetId: string) => {
    try {
      const history = await getAssetHistory(assetId);
      setSelectedHistory(history);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load history");
    }
  };

  const filteredPriorities =
    riskFilter === "all"
      ? priorities
      : priorities.filter((r) => r.risk_level === riskFilter);

  if (loading || loadingData) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-cyan-50/40">
        <p className="text-slate-500 text-sm">Loading fleet data…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-cyan-50/40">
        <p className="text-red-500 text-sm">{error}</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-cyan-50/40">
      <div className="max-w-5xl mx-auto px-4 py-6">

        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Fleet Dashboard</h1>
            <p className="text-slate-500 text-sm mt-1">Asset status and diagnostic history</p>
          </div>
          <button
            onClick={() => router.push("/")}
            className="text-sm text-cyan-600 hover:text-cyan-700 font-medium min-h-[44px] flex items-center transition-colors cursor-pointer"
          >
            New Diagnostic
          </button>
        </div>

        {/* Summary bar */}
        {summary && (
          <div className="grid grid-cols-3 gap-3 mb-6">
            <div className="bg-white border border-gray-100 rounded-2xl p-4 text-center shadow-card">
              <div className="text-3xl font-bold text-slate-900 tabular-nums">{summary.total_assets}</div>
              <div className="text-xs text-slate-500 mt-1">Total Assets</div>
            </div>
            <div className={`bg-white border rounded-2xl p-4 text-center shadow-card ${summary.active_issues > 0 ? "border-amber-200" : "border-gray-100"}`}>
              <div className={`text-3xl font-bold tabular-nums ${summary.active_issues > 0 ? "text-amber-600" : "text-slate-900"}`}>
                {summary.active_issues}
              </div>
              <div className="text-xs text-slate-500 mt-1">Open Issues</div>
            </div>
            <div className="bg-white border border-gray-100 rounded-2xl p-4 shadow-card">
              <div className="text-xs text-slate-500 mb-2 font-medium">Top Faults</div>
              {summary.top_faults.length === 0 ? (
                <div className="text-xs text-slate-400">None recorded</div>
              ) : (
                <div className="space-y-1">
                  {summary.top_faults.slice(0, 3).map((f) => (
                    <div key={f.cause} className="flex justify-between text-xs">
                      <span className="text-slate-700 truncate">{f.cause}</span>
                      <span className="text-slate-400 ml-2 shrink-0 tabular-nums">{f.count}×</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* View toggle */}
        <div className="flex gap-1 mb-5 bg-slate-100 rounded-xl p-1 w-fit">
          <button
            onClick={() => setView("assets")}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all min-h-[36px] cursor-pointer ${
              view === "assets"
                ? "bg-white text-slate-900 shadow-[0_1px_2px_rgba(0,0,0,0.08)]"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            Assets
          </button>
          <button
            onClick={handleViewPriorities}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all min-h-[36px] cursor-pointer ${
              view === "priorities"
                ? "bg-white text-slate-900 shadow-[0_1px_2px_rgba(0,0,0,0.08)]"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            Priorities
          </button>
        </div>

        {/* Assets view */}
        {view === "assets" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-3">
              <h2 className="font-semibold text-slate-500 text-xs uppercase tracking-wider">
                Assets ({assets.length})
              </h2>
              {assets.length === 0 ? (
                <div className="bg-white border border-gray-100 rounded-2xl p-6 text-center text-slate-500 text-sm shadow-card">
                  No assets with telemetry data yet.
                </div>
              ) : (
                assets.map((a) => (
                  <AssetCard
                    key={a.asset_id}
                    asset={a}
                    onSelect={() => handleAssetSelect(a.asset_id)}
                  />
                ))
              )}
            </div>

            <div>
              {selectedHistory ? (
                <AssetHistoryPanel
                  history={selectedHistory}
                  onClose={() => setSelectedHistory(null)}
                />
              ) : (
                <div className="bg-white border border-dashed border-gray-200 rounded-2xl p-6 text-center text-slate-400 text-sm">
                  Select an asset to view its diagnostic history
                </div>
              )}
            </div>
          </div>
        )}

        {/* Priorities view */}
        {view === "priorities" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <h2 className="font-semibold text-slate-500 text-xs uppercase tracking-wider">
                  Risk Ranking
                </h2>
                {filteredPriorities.length > 0 && (
                  <span className="text-xs text-slate-400">
                    {filteredPriorities.length} asset{filteredPriorities.length !== 1 ? "s" : ""}
                  </span>
                )}
              </div>

              <PriorityFilters riskFilter={riskFilter} onRiskFilter={setRiskFilter} />

              {loadingPriorities ? (
                <div className="bg-white border border-gray-100 rounded-2xl p-6 text-center text-slate-500 text-sm shadow-card">
                  Computing risk scores…
                </div>
              ) : filteredPriorities.length === 0 ? (
                <div className="bg-white border border-gray-100 rounded-2xl p-6 text-center text-slate-500 text-sm shadow-card">
                  {priorities.length === 0
                    ? "No assets with telemetry data."
                    : `No assets at ${riskFilter} risk level.`}
                </div>
              ) : (
                filteredPriorities.map((r) => (
                  <AssetRiskCard
                    key={r.asset_id}
                    risk={r}
                    onViewHistory={handleAssetSelect}
                  />
                ))
              )}
            </div>

            <div>
              {selectedHistory ? (
                <AssetHistoryPanel
                  history={selectedHistory}
                  onClose={() => setSelectedHistory(null)}
                />
              ) : (
                <div className="bg-white border border-dashed border-gray-200 rounded-2xl p-6 text-center text-slate-400 text-sm">
                  <p>Select an asset to view its diagnostic history</p>
                  <p className="mt-2 text-xs">
                    Risk scores are computed from sessions and telemetry in the last 30 days.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
