"use client";

import { useState } from "react";
import type { HeavyEquipmentContext } from "@/types";

interface Props {
  value: HeavyEquipmentContext;
  onChange: (ctx: HeavyEquipmentContext) => void;
}

const ENVIRONMENTS = [
  { value: "dusty", label: "Dusty — quarry, demolition, earthmoving" },
  { value: "muddy", label: "Muddy — wet earthmoving, construction" },
  { value: "marine", label: "Marine — near water, saltwater air" },
  { value: "urban", label: "Normal / urban" },
] as const;

export function HeavyEquipmentForm({ value, onChange }: Props) {
  const set = <K extends keyof HeavyEquipmentContext>(k: K, v: HeavyEquipmentContext[K]) =>
    onChange({ ...value, [k]: v });

  return (
    <div className="rounded-2xl border border-amber-200/80 bg-amber-50/60 p-4 space-y-4 text-sm w-full">
      <p className="font-semibold text-amber-800 text-xs uppercase tracking-wide">
        Heavy Equipment Context <span className="font-normal text-amber-600">(optional — improves accuracy)</span>
      </p>

      {/* Single-column stacked layout for mobile; 2-column on sm+ */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-slate-600 mb-1.5">Machine hours</label>
          <input
            type="number"
            inputMode="numeric"
            min={0}
            placeholder="e.g. 4500"
            value={value.hours_of_operation ?? ""}
            onChange={(e) => set("hours_of_operation", e.target.value ? Number(e.target.value) : undefined)}
            className="w-full rounded-xl border border-amber-200 bg-white/70 px-3 py-2.5 text-base sm:text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent min-h-[44px] transition"
          />
        </div>
        <div>
          <label className="block text-xs text-slate-600 mb-1.5">Hours since last service</label>
          <input
            type="number"
            inputMode="numeric"
            min={0}
            placeholder="e.g. 210"
            value={value.last_service_hours ?? ""}
            onChange={(e) => set("last_service_hours", e.target.value ? Number(e.target.value) : undefined)}
            className="w-full rounded-xl border border-amber-200 bg-white/70 px-3 py-2.5 text-base sm:text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent min-h-[44px] transition"
          />
        </div>
      </div>

      <div>
        <label className="block text-xs text-slate-600 mb-1.5">Working environment</label>
        <select
          value={value.environment ?? ""}
          onChange={(e) => set("environment", e.target.value as HeavyEquipmentContext["environment"] || undefined)}
          className="w-full rounded-xl border border-amber-200 bg-white/70 px-3 py-2.5 text-base sm:text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent min-h-[44px] transition"
        >
          <option value="">Not sure</option>
          {ENVIRONMENTS.map((env) => (
            <option key={env.value} value={env.value}>{env.label}</option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-slate-600 mb-1.5">Days since last used</label>
          <input
            type="number"
            inputMode="numeric"
            min={0}
            placeholder="e.g. 45"
            value={value.storage_duration ?? ""}
            onChange={(e) => set("storage_duration", e.target.value ? Number(e.target.value) : undefined)}
            className="w-full rounded-xl border border-amber-200 bg-white/70 px-3 py-2.5 text-base sm:text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent min-h-[44px] transition"
          />
        </div>
        <div>
          <label className="block text-xs text-slate-600 mb-1.5">Recent work type</label>
          <input
            type="text"
            placeholder="e.g. trenching"
            value={value.recent_work_type ?? ""}
            onChange={(e) => set("recent_work_type", e.target.value || undefined)}
            className="w-full rounded-xl border border-amber-200 bg-white/70 px-3 py-2.5 text-base sm:text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent min-h-[44px] transition"
          />
        </div>
      </div>
    </div>
  );
}
