"use client";

import { useState } from "react";
import { submitFeedback } from "@/lib/api";
import type { DiagnosticResult, OBDResult } from "@/types";

const SEVERITY_STYLES: Record<string, { label: string; color: string }> = {
  low: { label: "Low — monitor", color: "bg-green-100 text-green-800" },
  moderate: { label: "Moderate — address soon", color: "bg-yellow-100 text-yellow-800" },
  high: { label: "High — address promptly", color: "bg-orange-100 text-orange-800" },
  critical: { label: "Critical — stop driving", color: "bg-red-100 text-red-800" },
};

const DIY_LABELS: Record<string, { label: string; color: string }> = {
  easy: { label: "Easy DIY", color: "bg-green-100 text-green-800" },
  moderate: { label: "Moderate DIY", color: "bg-yellow-100 text-yellow-800" },
  hard: { label: "Difficult DIY", color: "bg-orange-100 text-orange-800" },
  seek_mechanic: { label: "See a Mechanic", color: "bg-red-100 text-red-800" },
};

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 70 ? "bg-green-500" : pct >= 45 ? "bg-amber-400" : "bg-red-400";
  return (
    <div className="flex items-center gap-2 mt-1">
      <div className="flex-1 bg-slate-100 rounded-full h-1.5">
        <div
          className={`h-1.5 rounded-full ${color} transition-all`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-slate-400 w-8 text-right tabular-nums">{pct}%</span>
    </div>
  );
}

export function DiagnosticResultCard({
  result,
  sessionId,
}: {
  result: DiagnosticResult;
  sessionId?: string;
}) {
  const [feedbackRating, setFeedbackRating] = useState<number | null>(null);
  const [feedbackSent, setFeedbackSent] = useState(false);

  const diy = result.diy_difficulty ? DIY_LABELS[result.diy_difficulty] : null;
  const overallConf = Math.round(result.confidence_level * 100);

  function handleCopy() {
    const top = result.ranked_causes[0];
    const diyLabel = result.diy_difficulty
      ? (DIY_LABELS[result.diy_difficulty]?.label ?? result.diy_difficulty)
      : null;
    const lines: string[] = [
      "=== Fix Diagnostic Summary ===",
      "",
      `Top Cause: ${top?.cause ?? "Unknown"} (${Math.round((top?.confidence ?? 0) * 100)}% confidence)`,
      ...(top?.reasoning ? [`Reasoning: ${top.reasoning}`] : []),
      "",
      "Likely Causes:",
      ...result.ranked_causes.map(
        (c, i) => `  ${i + 1}. ${c.cause} — ${Math.round(c.confidence * 100)}%`
      ),
    ];
    if (result.next_checks.length > 0) {
      lines.push("", "Next Checks:");
      result.next_checks.forEach((c) => lines.push(`  - ${c}`));
    }
    if (diyLabel) {
      lines.push("", `DIY Level: ${diyLabel}`);
    }
    if (result.escalation_guidance) {
      lines.push("", `When to See a Mechanic: ${result.escalation_guidance}`);
    }
    navigator.clipboard.writeText(lines.join("\n"));
  }

  async function handleStarClick(star: number) {
    setFeedbackRating(star);
    if (sessionId) {
      try {
        await submitFeedback(sessionId, star);
      } catch {
        // best-effort — don't surface feedback errors to the user
      }
    }
    setFeedbackSent(true);
  }

  return (
    <div className="mt-3 rounded-2xl border border-gray-100 bg-white shadow-card-md overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 bg-gradient-to-r from-slate-800 to-slate-900 flex items-center justify-between">
        <span className="text-sm font-semibold text-white">Diagnostic Result</span>
        <span className="text-xs text-slate-400 tabular-nums">{overallConf}% confidence</span>
      </div>

      <div className="divide-y divide-gray-100">
        {/* Ranked Causes */}
        <div className="px-4 py-4">
          <h3 className="text-xs font-semibold text-cyan-700 uppercase tracking-wide mb-3">
            Likely Causes
          </h3>
          <div className="space-y-3.5">
            {result.ranked_causes.map((cause, i) => (
              <div key={i}>
                <div className="flex items-start justify-between gap-2">
                  <span className="text-sm font-medium text-slate-900">
                    {i + 1}. {cause.cause}
                  </span>
                </div>
                <ConfidenceBar value={cause.confidence} />
                <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">{cause.reasoning}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Next Checks */}
        {result.next_checks.length > 0 && (
          <div className="px-4 py-4">
            <h3 className="text-xs font-semibold text-cyan-700 uppercase tracking-wide mb-2.5">
              Next Checks
            </h3>
            <ol className="space-y-1.5">
              {result.next_checks.map((check, i) => (
                <li key={i} className="flex gap-2.5 text-sm text-slate-700">
                  <span className="text-slate-300 font-mono text-xs mt-0.5 min-w-4 tabular-nums">
                    {i + 1}.
                  </span>
                  {check}
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* Post-diagnosis follow-up checks */}
        {result.post_diagnosis && result.post_diagnosis.length > 0 && (
          <div className="px-4 py-4 bg-cyan-50/60">
            <h3 className="text-xs font-semibold text-cyan-700 uppercase tracking-wide mb-2.5">
              After Confirming, Also Check
            </h3>
            <ul className="space-y-1.5">
              {result.post_diagnosis.map((item, i) => (
                <li key={i} className="flex gap-2 text-sm text-cyan-900">
                  <span className="text-cyan-400 mt-0.5">•</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* DIY Difficulty + Parts */}
        <div className="px-4 py-4 flex flex-wrap gap-4">
          {diy && (
            <div>
              <h3 className="text-xs font-semibold text-cyan-700 uppercase tracking-wide mb-1.5">
                DIY Level
              </h3>
              <span className={`inline-block px-2.5 py-1 rounded-full text-xs font-medium ${diy.color}`}>
                {diy.label}
              </span>
            </div>
          )}

          {result.suggested_parts.length > 0 && (
            <div className="flex-1">
              <h3 className="text-xs font-semibold text-cyan-700 uppercase tracking-wide mb-1.5">
                Possible Parts
              </h3>
              <ul className="space-y-0.5">
                {result.suggested_parts.map((part, i) => (
                  <li key={i} className="text-sm text-slate-700">
                    <span className="font-medium">{part.name}</span>
                    {part.notes && (
                      <span className="text-slate-400"> — {part.notes}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Escalation Guidance */}
        {result.escalation_guidance && (
          <div className="px-4 py-4 bg-amber-50/70">
            <h3 className="text-xs font-semibold text-amber-700 uppercase tracking-wide mb-1.5">
              When to See a Mechanic
            </h3>
            <p className="text-sm text-amber-900 leading-relaxed">{result.escalation_guidance}</p>
          </div>
        )}

        {/* Footer: copy + feedback */}
        <div className="px-4 py-3 flex items-center justify-between gap-4">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-700 transition-colors cursor-pointer"
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
            </svg>
            Copy summary
          </button>

          {sessionId && !feedbackSent && (
            <div className="flex items-center gap-1">
              <span className="text-xs text-slate-400 mr-1">Helpful?</span>
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  onClick={() => handleStarClick(star)}
                  className={`text-base leading-none transition-colors cursor-pointer ${
                    feedbackRating !== null && star <= feedbackRating
                      ? "text-amber-400"
                      : "text-slate-200 hover:text-amber-300"
                  }`}
                  aria-label={`Rate ${star} star${star !== 1 ? "s" : ""}`}
                >
                  ★
                </button>
              ))}
            </div>
          )}
          {feedbackSent && (
            <span className="text-xs text-slate-400">Thanks for the feedback.</span>
          )}
        </div>
      </div>
    </div>
  );
}

export function OBDResultCard({ result }: { result: OBDResult }) {
  const severity = SEVERITY_STYLES[result.severity] ?? { label: result.severity, color: "bg-gray-100 text-gray-800" };
  const diy = DIY_LABELS[result.diy_difficulty] ?? null;

  return (
    <div className="mt-3 rounded-2xl border border-gray-100 bg-white shadow-card-md overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 bg-gradient-to-r from-slate-800 to-slate-900 flex items-center justify-between">
        <span className="text-sm font-semibold text-white font-mono">{result.code}</span>
        <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${severity.color}`}>
          {severity.label}
        </span>
      </div>

      <div className="divide-y divide-gray-100">
        {/* Description */}
        <div className="px-4 py-4">
          <p className="text-sm text-slate-800 leading-relaxed">{result.description}</p>
        </div>

        {/* Likely Causes */}
        {result.likely_causes.length > 0 && (
          <div className="px-4 py-4">
            <h3 className="text-xs font-semibold text-cyan-700 uppercase tracking-wide mb-2.5">
              Likely Causes
            </h3>
            <ul className="space-y-1.5">
              {result.likely_causes.map((cause, i) => (
                <li key={i} className="flex gap-2.5 text-sm text-slate-700">
                  <span className="text-slate-300 font-mono text-xs mt-0.5 min-w-4 tabular-nums">{i + 1}.</span>
                  {cause}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Next Steps */}
        {result.next_steps.length > 0 && (
          <div className="px-4 py-4">
            <h3 className="text-xs font-semibold text-cyan-700 uppercase tracking-wide mb-2.5">
              Next Steps
            </h3>
            <ol className="space-y-1.5">
              {result.next_steps.map((step, i) => (
                <li key={i} className="flex gap-2.5 text-sm text-slate-700">
                  <span className="text-slate-300 font-mono text-xs mt-0.5 min-w-4 tabular-nums">{i + 1}.</span>
                  {step}
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* DIY Level */}
        {diy && (
          <div className="px-4 py-4">
            <h3 className="text-xs font-semibold text-cyan-700 uppercase tracking-wide mb-1.5">
              DIY Level
            </h3>
            <span className={`inline-block px-2.5 py-1 rounded-full text-xs font-medium ${diy.color}`}>
              {diy.label}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
