import React from "react";
import { Stethoscope } from "lucide-react";

export default function DoctorDiscussion({ discussionPoints = [] }) {
  if (!discussionPoints || discussionPoints.length === 0) return null;

  // Filter out any save-to-vault / storage suggestions and duplicate lab notes
  const cleanedPoints = discussionPoints.filter((point) => {
    if (!point || typeof point !== "string") return false;
    const lower = point.toLowerCase();
    if (lower.includes("health vault") || lower.includes("keep this report") || lower.includes("save this report")) {
      return false;
    }
    return true;
  });

  // Limit to maximum 2-3 concise, non-repetitive discussion points
  const displayPoints = cleanedPoints.slice(0, 3);

  if (displayPoints.length === 0) return null;

  return (
    <section
      aria-label="Things to Discuss With Your Doctor"
      className="bg-white border border-slate-200/90 rounded-2xl p-6 sm:p-7 shadow-xs space-y-4"
    >
      <div className="flex items-center gap-3 border-b border-slate-100 pb-3.5">
        <div className="w-8 h-8 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center border border-blue-100/80 shrink-0">
          <Stethoscope className="w-4 h-4" />
        </div>
        <div>
          <h3 className="text-base font-bold text-slate-900 tracking-tight">
            Things to Discuss With Your Doctor
          </h3>
          <p className="text-xs text-slate-500">
            Concise discussion prompts to consider during your physician consultation.
          </p>
        </div>
      </div>

      <div className="space-y-2.5">
        {displayPoints.map((point, idx) => (
          <div
            key={idx}
            className="p-3.5 bg-slate-50/70 border border-slate-200/70 rounded-xl text-xs sm:text-sm text-slate-700 leading-relaxed flex items-start gap-3"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-blue-600 shrink-0 mt-2" />
            <span className="font-medium text-slate-800">{point}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

