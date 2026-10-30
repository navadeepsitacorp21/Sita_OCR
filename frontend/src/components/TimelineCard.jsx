import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Calendar, Clock, FolderHeart, CheckCircle2, AlertTriangle, HelpCircle, Trash2, ArrowRight } from "lucide-react";
import { formatReportDate, formatDateTime } from "../utils/dateUtils";

export default function TimelineCard({ report, onDelete, isDeleting }) {
  const [confirmDelete, setConfirmDelete] = useState(false);

  const getOverallBadge = (status) => {
    const s = String(status || "").toLowerCase();
    switch (s) {
      case "all clear":
      case "healthy":
      case "within range":
        return {
          label: "Within Range",
          className: "bg-emerald-50 text-emerald-700 border-emerald-200/80",
          icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />,
        };
      case "needs attention":
      case "attention needed":
      case "outside range":
        return {
          label: "Outside Range",
          className: "bg-rose-50 text-rose-700 border-rose-200/80",
          icon: <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />,
        };
      case "review required":
      case "needs review":
        return {
          label: "Needs Review",
          className: "bg-indigo-50 text-indigo-700 border-indigo-200/80",
          icon: <HelpCircle className="w-3.5 h-3.5 text-indigo-600" />,
        };
      default:
        return {
          label: status || "Report Saved",
          className: "bg-slate-100 text-slate-700 border-slate-200",
          icon: null,
        };
    }
  };

  const getReportTypeDisplay = (type) => {
    switch (type) {
      case "CBC":
        return { name: "Complete Blood Count", code: "CBC" };
      case "LIVER_FUNCTION_TEST":
      case "LFT":
        return { name: "Liver Function Test", code: "LFT" };
      case "KIDNEY_FUNCTION_TEST":
      case "KFT":
        return { name: "Kidney Function Test", code: "KFT" };
      case "LIPID_PROFILE":
      case "LIPID":
        return { name: "Lipid Profile", code: "LIPID PROFILE" };
      default:
        return { name: type || "Laboratory Report", code: type || "LAB" };
    }
  };

  const reportId = report.id || report.report_id;
  const reportDateFormatted = formatReportDate(report.report_date);
  const analyzedDateFormatted = formatDateTime(report.analyzed_at || report.report_json?.analyzed_at);
  const savedDateFormatted = formatDateTime(report.saved_at || report.saved_to_vault_at);

  const typeInfo = getReportTypeDisplay(report.report_type);
  const badge = getOverallBadge(report.overall_status);
  const totalBiomarkers = report.biomarkers_found || report.total_parameters || 0;
  const abnormalCount = report.abnormal_count || 0;

  return (
    <div className="bg-white border border-slate-200/90 rounded-2xl p-5 sm:p-6 shadow-xs hover:border-blue-300 hover:shadow-xs transition-all">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-2.5 flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-bold text-slate-900 text-base sm:text-lg tracking-tight">
              {typeInfo.name}
            </span>
            <span className="px-2 py-0.5 rounded-md bg-blue-50 text-blue-700 font-mono text-xs font-bold border border-blue-200">
              {typeInfo.code}
            </span>
            <span
              className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${badge.className}`}
            >
              {badge.icon}
              <span>{badge.label}</span>
            </span>
          </div>

          {/* 1. Clinical Report Date (Visually Prominent) */}
          <div className="flex items-center gap-1.5 font-medium text-slate-800 text-xs">
            <Calendar className="w-3.5 h-3.5 text-blue-600 shrink-0" />
            <span>Report Date:</span>
            {reportDateFormatted ? (
              <span className="font-bold text-slate-900 bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200">
                {reportDateFormatted}
              </span>
            ) : (
              <span className="text-slate-400 italic">Report date unavailable</span>
            )}
          </div>

          {/* 2. System Timestamps (Secondary line: Analyzed & Saved) */}
          <div className="flex items-center gap-x-3 gap-y-1 text-xs text-slate-500 flex-wrap">
            {analyzedDateFormatted && (
              <span className="flex items-center gap-1 text-slate-500">
                <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                <span>Analyzed:</span>
                <span className="font-medium text-slate-700">{analyzedDateFormatted}</span>
              </span>
            )}

            {savedDateFormatted && (
              <>
                {analyzedDateFormatted && <span>•</span>}
                <span className="flex items-center gap-1 text-slate-500">
                  <FolderHeart className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                  <span>Saved:</span>
                  <span className="font-medium text-slate-700">{savedDateFormatted}</span>
                </span>
              </>
            )}

            {report.filename && (
              <>
                <span>•</span>
                <span className="text-[11px] text-slate-400 font-mono truncate max-w-[160px]" title={report.filename}>
                  {report.filename}
                </span>
              </>
            )}
          </div>

          {/* Biomarker counts */}
          <div className="pt-0.5 flex items-center gap-3 text-xs">
            <span className="font-semibold text-slate-900">
              {totalBiomarkers} {totalBiomarkers === 1 ? "parameter" : "parameters"}
            </span>
            <span className="text-slate-300">•</span>
            {abnormalCount > 0 ? (
              <span className="text-rose-600 font-bold">
                {abnormalCount} outside range
              </span>
            ) : (
              <span className="text-emerald-600 font-bold">
                All within range
              </span>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2 self-end sm:self-center shrink-0 pt-2 sm:pt-0">
          <Link
            to={`/report/${reportId}`}
            className="px-4 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-all shadow-2xs flex items-center gap-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <span>View Report</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>

          {confirmDelete ? (
            <div className="flex items-center gap-1.5 animate-in fade-in">
              <button
                type="button"
                onClick={() => onDelete(reportId)}
                disabled={isDeleting}
                className="px-2.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-lg transition-colors"
              >
                Confirm
              </button>
              <button
                type="button"
                onClick={() => setConfirmDelete(false)}
                className="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium rounded-lg transition-colors"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setConfirmDelete(true)}
              disabled={isDeleting}
              className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
              title="Delete report from vault"
              aria-label="Delete report"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
