import React, { useEffect } from "react";
import {
  X,
  CheckCircle2,
  ArrowUpRight,
  ArrowDownRight,
  HelpCircle,
  TrendingUp,
  TrendingDown,
  Minus,
  ShieldCheck,
  Stethoscope,
  Clock,
} from "lucide-react";
import { formatReportDate } from "../utils/dateUtils";

export default function BiomarkerDetailModal({ biomarker, trend, onClose }) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!biomarker) return null;

  const interp = biomarker.interpretation || {};
  const statusLower = String(biomarker.status || "Unknown").toLowerCase();

  const getStatusBadge = (status) => {
    switch (status) {
      case "normal":
      case "within range":
        return {
          label: "Within Range",
          className: "bg-emerald-50 text-emerald-700 border-emerald-200/80",
          icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />,
        };
      case "high":
      case "above range":
        return {
          label: "Above Range",
          className: "bg-rose-50 text-rose-700 border-rose-200/80",
          icon: <ArrowUpRight className="w-3.5 h-3.5 text-rose-600" />,
        };
      case "low":
      case "below range":
        return {
          label: "Below Range",
          className: "bg-rose-50 text-rose-700 border-rose-200/80",
          icon: <ArrowDownRight className="w-3.5 h-3.5 text-rose-600" />,
        };
      case "needs review":
        return {
          label: "Needs Review",
          className: "bg-indigo-50 text-indigo-700 border-indigo-200/80",
          icon: <HelpCircle className="w-3.5 h-3.5 text-indigo-600" />,
        };
      default:
        return {
          label: biomarker.status || "Unknown",
          className: "bg-slate-100 text-slate-700 border-slate-200",
          icon: null,
        };
    }
  };

  const statusConfig = getStatusBadge(statusLower);

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="biomarker-modal-title"
    >
      <div className="fixed inset-0" onClick={onClose} aria-hidden="true" />

      <div className="relative bg-white rounded-2xl max-w-lg w-full shadow-2xl border border-slate-200 overflow-hidden z-10 animate-in fade-in zoom-in-95 duration-150">
        {/* Modal Header */}
        <div className="px-6 py-5 border-b border-slate-100 flex justify-between items-start bg-slate-50/60">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-blue-600 block">
              Parameter Details
            </span>
            <h3 id="biomarker-modal-title" className="text-xl font-bold text-slate-900 tracking-tight mt-0.5">
              {biomarker.name || biomarker.key}
            </h3>
            {biomarker.key && biomarker.name && biomarker.key.toLowerCase() !== biomarker.name.toLowerCase() && (
              <p className="text-xs text-slate-400 font-mono mt-0.5">
                {biomarker.key}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 bg-slate-100 hover:bg-slate-200/80 p-1.5 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
            title="Close modal (Esc)"
            aria-label="Close modal"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 space-y-5 max-h-[75vh] overflow-y-auto text-sm">
          {/* Result & Reference Card */}
          <div className="p-4.5 bg-slate-50/70 rounded-xl border border-slate-200/80 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                  Observed Result
                </span>
                <div className="text-2xl font-bold font-mono text-slate-900 mt-0.5">
                  {biomarker.value}{" "}
                  <span className="font-sans font-normal text-slate-500 text-sm">
                    {biomarker.unit}
                  </span>
                </div>
              </div>
              <span
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${statusConfig.className}`}
              >
                {statusConfig.icon}
                <span>{statusConfig.label}</span>
              </span>
            </div>

            <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between text-xs text-slate-600">
              <span className="font-medium text-slate-500">Reference Range:</span>
              <span className="font-mono font-semibold text-slate-800">
                {biomarker.reference_range || "—"} {biomarker.unit}
              </span>
            </div>

            {biomarker.reference_source === "report" && (
              <div className="text-[11px] text-slate-500 flex items-center gap-1 pt-0.5">
                <CheckCircle2 className="w-3 h-3 text-emerald-600 shrink-0" />
                <span>Extracted directly from laboratory report reference intervals</span>
              </div>
            )}
          </div>

          {/* Educational Insights */}
          <div className="space-y-4">
            {/* What is this? */}
            {interp.what_it_measures && (
              <div className="space-y-1.5">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  What is this?
                </h4>
                <p className="text-xs sm:text-sm text-slate-700 leading-relaxed bg-white border border-slate-200/70 p-3.5 rounded-xl">
                  {interp.what_it_measures}
                </p>
              </div>
            )}

            {/* What this result may mean */}
            {(interp.significance || biomarker.status_reason) && (
              <div className="space-y-1.5">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  What this result may mean
                </h4>
                <p className="text-xs sm:text-sm text-slate-700 leading-relaxed bg-white border border-slate-200/70 p-3.5 rounded-xl">
                  {interp.significance || biomarker.status_reason}
                </p>
              </div>
            )}

            {/* Previous Results (Only if trend data exists!) */}
            {trend && (
              <div className="space-y-1.5">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-blue-600" />
                  <span>Previous Results</span>
                </h4>
                <div className="bg-slate-50/80 border border-slate-200/80 rounded-xl p-3.5 space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-slate-500 block">Previous</span>
                      <span className="font-mono font-bold text-slate-800">
                        {trend.previous_value} {trend.unit}
                      </span>
                      {trend.previous_report_date && (
                        <span className="text-[10px] text-slate-400 block">
                          ({formatReportDate(trend.previous_report_date)})
                        </span>
                      )}
                    </div>
                    <div className="text-right">
                      <span className="text-slate-500 block">Current</span>
                      <span className="font-mono font-bold text-slate-900">
                        {trend.current_value} {trend.unit}
                      </span>
                    </div>
                  </div>
                  <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between">
                    <span className="text-slate-600">{trend.summary}</span>
                    <span className="font-bold text-blue-700">
                      {trend.arrow} {Math.abs(trend.percentage_change)}%
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Things to discuss with your doctor */}
            {interp.recommendation && (
              <div className="space-y-1.5">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                  <Stethoscope className="w-3.5 h-3.5 text-blue-600" />
                  <span>Things to discuss with your doctor</span>
                </h4>
                <div className="bg-blue-50/40 border border-blue-100/80 rounded-xl p-3.5 text-xs text-slate-800 leading-relaxed">
                  {interp.recommendation}
                </div>
              </div>
            )}
          </div>

          {/* Educational Disclaimer */}
          <div className="pt-2 text-[11px] text-slate-400 flex items-start gap-1.5 border-t border-slate-100">
            <ShieldCheck className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
            <span>
              Educational information only. Not a medical diagnosis. Consult your healthcare provider for clinical interpretation.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
