import React from "react";

export default function SummaryCard({ reportData }) {
  if (!reportData) return null;

  const { filename, page_count, ocr_summary, classification, parsed_report, health_summary } = reportData;

  const getOverallStatusBadge = (status) => {
    switch (status) {
      case "All Clear":
        return "bg-green-100 text-green-800 border-green-200";
      case "Needs Attention":
        return "bg-red-100 text-red-800 border-red-200";
      case "Review Required":
        return "bg-yellow-100 text-yellow-800 border-yellow-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  const confidencePercent = Math.round((ocr_summary?.average_confidence || 0) * 100);
  const statusSummary = parsed_report?.status_summary || {};

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Report Info Card */}
      <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm space-y-3">
        <h3 className="text-base font-semibold text-gray-900 border-b pb-2">Report Info</h3>
        <div className="grid grid-cols-2 gap-y-2 text-sm">
          <span className="text-gray-500">Filename:</span>
          <span className="font-medium text-gray-900 truncate" title={filename}>
            {filename || "N/A"}
          </span>

          <span className="text-gray-500">Report Type:</span>
          <span className="font-semibold text-blue-700">
            {classification?.report_type || parsed_report?.report_type || "UNKNOWN"}
          </span>

          <span className="text-gray-500">OCR Confidence:</span>
          <span className="font-medium text-gray-900">{confidencePercent}%</span>

          <span className="text-gray-500">Parser Version:</span>
          <span className="font-medium text-gray-900">
            {parsed_report?.parser_version || "1.0.0"}
          </span>

          <span className="text-gray-500">Page Count:</span>
          <span className="font-medium text-gray-900">{page_count || 1}</span>
        </div>
      </div>

      {/* Health Summary Card */}
      <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm space-y-3">
        <div className="flex justify-between items-center border-b pb-2">
          <h3 className="text-base font-semibold text-gray-900">Health Summary</h3>
          {health_summary?.overall_status && (
            <span
              className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${getOverallStatusBadge(
                health_summary.overall_status
              )}`}
            >
              {health_summary.overall_status}
            </span>
          )}
        </div>

        <div className="grid grid-cols-3 gap-2 text-center pt-1">
          <div className="bg-gray-50 border border-gray-100 rounded p-2">
            <div className="text-xs text-gray-500">Total Biomarkers</div>
            <div className="text-lg font-bold text-gray-800">
              {parsed_report?.biomarkers_found || 0}
            </div>
          </div>
          <div className="bg-green-50 border border-green-100 rounded p-2">
            <div className="text-xs text-green-700 font-medium">Normal</div>
            <div className="text-lg font-bold text-green-800">
              {statusSummary.normal ?? 0}
            </div>
          </div>
          <div className="bg-red-50 border border-red-100 rounded p-2">
            <div className="text-xs text-red-700 font-medium">High</div>
            <div className="text-lg font-bold text-red-800">
              {statusSummary.high ?? 0}
            </div>
          </div>
          <div className="bg-orange-50 border border-orange-100 rounded p-2">
            <div className="text-xs text-orange-700 font-medium">Low</div>
            <div className="text-lg font-bold text-orange-800">
              {statusSummary.low ?? 0}
            </div>
          </div>
          <div className="bg-gray-50 border border-gray-100 rounded p-2 col-span-2">
            <div className="text-xs text-gray-500 font-medium">Unknown / Missing</div>
            <div className="text-lg font-bold text-gray-700">
              {statusSummary.unknown ?? 0}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
