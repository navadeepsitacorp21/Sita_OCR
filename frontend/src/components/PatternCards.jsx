import React, { useState } from "react";
import { Activity, ChevronDown, ChevronUp, Info, Stethoscope } from "lucide-react";

export default function PatternCards({ patterns = [] }) {
  const [expandedMap, setExpandedMap] = useState({});

  const toggleExpand = (id) => {
    setExpandedMap((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  if (!patterns || patterns.length === 0) {
    return (
      <section aria-label="Observed Patterns" className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-slate-900 tracking-tight">
              Observed Patterns
            </h3>
            <p className="text-xs text-slate-500">
              Educational observation — not a diagnosis
            </p>
          </div>
        </div>
        <div className="p-4 bg-slate-50 rounded-xl border border-slate-200/80 text-xs text-slate-500 text-center">
          No significant pattern identified from the available results.
        </div>
      </section>
    );
  }

  return (
    <section aria-label="Observed Patterns" className="space-y-3.5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
        <div>
          <h3 className="text-base font-bold text-slate-900 tracking-tight">
            Observed Patterns
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Educational observation — not a diagnosis
          </p>
        </div>
        <span className="text-[11px] font-semibold text-indigo-700 bg-indigo-50 px-2.5 py-1 rounded-md border border-indigo-200 self-start sm:self-auto">
          Multi-Marker Observation
        </span>
      </div>

      <div className="grid grid-cols-1 gap-3.5">
        {patterns.map((pat, idx) => {
          const patId = pat.pattern_id || `pat-${idx}`;
          const isExpanded = !!expandedMap[patId];

          return (
            <div
              key={patId}
              className="p-5 sm:p-6 bg-white border border-slate-200/90 rounded-2xl shadow-xs space-y-3.5 transition-all"
            >
              {/* Header */}
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0 border border-indigo-200">
                    <Activity className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="font-bold text-slate-900 text-base tracking-tight leading-snug">
                      {pat.name}
                    </h4>
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-indigo-600">
                      Deterministic Pattern
                    </span>
                  </div>
                </div>

                {/* Progressive disclosure toggle */}
                <button
                  type="button"
                  onClick={() => toggleExpand(patId)}
                  className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1 transition-colors shrink-0 focus:outline-none"
                >
                  <span>{isExpanded ? "Hide details" : "View details"}</span>
                  {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>
              </div>

              {/* Summary Description */}
              <p className="text-sm text-slate-800 font-medium leading-relaxed">
                {pat.summary}
              </p>

              {/* Expanded details */}
              {isExpanded && (
                <div className="space-y-3 pt-2 border-t border-slate-100 animate-in fade-in duration-150">
                  {/* Involved Biomarkers */}
                  {pat.involved_biomarkers && pat.involved_biomarkers.length > 0 && (
                    <div className="space-y-1.5">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">
                        Involved Parameters
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {pat.involved_biomarkers.map((bm, bIdx) => {
                          const isNameString = typeof bm === "string";
                          const bmName = isNameString ? bm : bm.name || bm.key;
                          const bmVal = !isNameString && bm.value ? `${bm.value} ${bm.unit || ""}` : null;
                          const bmDir = !isNameString && bm.status ? (bm.status.toLowerCase().includes("high") ? "↑" : bm.status.toLowerCase().includes("low") ? "↓" : "") : "";

                          return (
                            <span
                              key={bIdx}
                              className="inline-flex items-center gap-1.5 text-xs font-mono font-medium bg-slate-50 text-slate-800 px-2.5 py-1 rounded-lg border border-slate-200"
                            >
                              <span className="font-sans font-bold text-slate-900">{bmName}</span>
                              {bmVal && <span className="text-slate-600">{bmVal}</span>}
                              {bmDir && (
                                <span className={bmDir === "↑" ? "text-rose-600 font-bold" : "text-amber-600 font-bold"}>
                                  {bmDir}
                                </span>
                              )}
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Educational Note */}
                  {pat.educational_note && (
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80 text-xs text-slate-600 leading-relaxed">
                      {pat.educational_note}
                    </div>
                  )}

                  {/* Discussion Point */}
                  {pat.recommendation && (
                    <div className="p-3 bg-blue-50/40 rounded-xl border border-blue-100/80 text-xs text-slate-700 flex items-start gap-2">
                      <Stethoscope className="w-3.5 h-3.5 text-blue-600 shrink-0 mt-0.5" />
                      <div className="leading-relaxed">
                        <span className="font-semibold text-slate-900 mr-1">Discussion Point:</span>
                        <span>{pat.recommendation}</span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
