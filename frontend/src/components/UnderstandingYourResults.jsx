import React from "react";
import { Stethoscope, ShieldCheck, HeartHandshake } from "lucide-react";

export default function UnderstandingYourResults({ explanation, biomarkers = [], patterns = [] }) {
  if (!explanation) return null;

  const {
    overall_explanation,
    disclaimer,
    key_findings = [],
  } = explanation;

  if (!overall_explanation && key_findings.length === 0) return null;

  // Filter abnormal biomarkers dynamically
  const abnormalItems = (biomarkers || []).filter((bm) => {
    const s = String(bm.status || "").toLowerCase();
    return s === "high" || s === "low" || s === "above range" || s === "below range" || s === "needs review";
  });

  const highItems = abnormalItems.filter((b) => {
    const s = String(b.status || "").toLowerCase();
    return s.includes("high") || s.includes("above");
  });

  const lowItems = abnormalItems.filter((b) => {
    const s = String(b.status || "").toLowerCase();
    return s.includes("low") || s.includes("below");
  });

  // Concise, reference-range focused summary wording
  let displaySummary = overall_explanation;
  if (
    overall_explanation &&
    overall_explanation.includes("Several values in your") &&
    overall_explanation.includes("outside the expected laboratory ranges")
  ) {
    displaySummary = overall_explanation
      .replace("expected laboratory ranges", "laboratory reference ranges")
      .replace(
        "and are worth reviewing in the context of your overall health, symptoms, and clinical history.",
        "and may be worth discussing with a healthcare professional in the context of your overall health and clinical history."
      );
  }

  return (
    <section
      aria-label="Clinical Understanding & Summary"
      className="bg-white border border-slate-200/90 rounded-2xl p-6 sm:p-7 shadow-xs space-y-5"
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-100 pb-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center border border-blue-100 shrink-0">
            <HeartHandshake className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 tracking-tight flex items-center gap-2">
              Understanding Your Results
            </h2>
            <p className="text-xs text-slate-500">
              A thoughtful, plain-language walkthrough of your test results and what they indicate.
            </p>
          </div>
        </div>
      </div>

      {/* Main Narrative */}
      <div className="p-4 sm:p-5 bg-gradient-to-br from-blue-50/50 via-slate-50/60 to-indigo-50/30 border border-blue-100/80 rounded-2xl space-y-3">
        <p className="text-sm sm:text-[15px] font-medium text-slate-800 leading-relaxed">
          {displaySummary}
        </p>

        {/* Dynamic data-driven abnormal findings */}
        {abnormalItems.length > 0 && (
          <div className="pt-2 text-xs sm:text-sm text-slate-600 space-y-2 border-t border-blue-100/60">
            {highItems.length > 0 && (
              <p className="leading-relaxed">
                <span className="font-semibold text-rose-700">Above the laboratory reference range:</span>{" "}
                <span className="text-slate-800 font-medium">
                  {highItems.map((b) => b.name || b.biomarker || b.key).join(", ")}.
                </span>
              </p>
            )}
            {lowItems.length > 0 && (
              <p className="leading-relaxed">
                <span className="font-semibold text-rose-700">Below the laboratory reference range:</span>{" "}
                <span className="text-slate-800 font-medium">
                  {lowItems.map((b) => b.name || b.biomarker || b.key).join(", ")}.
                </span>
              </p>
            )}
          </div>
        )}
      </div>

      {/* Safe deterministic medical context statement */}
      <div className="p-3.5 bg-slate-50/80 rounded-xl border border-slate-200/70 text-xs text-slate-600 leading-relaxed flex items-start gap-2.5">
        <Stethoscope className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
        <div>
          These results should be interpreted together with your overall health, symptoms, medical history, and the laboratory's reference ranges.
        </div>
      </div>

      {disclaimer && (
        <div className="text-[11px] text-slate-400 flex items-center gap-1.5 pt-1">
          <ShieldCheck className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <span>{disclaimer}</span>
        </div>
      )}
    </section>
  );
}

