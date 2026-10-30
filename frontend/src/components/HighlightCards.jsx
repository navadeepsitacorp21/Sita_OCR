import React from "react";

export default function HighlightCards({ highlights }) {
  if (!highlights || highlights.length === 0) {
    return null;
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm space-y-3">
      <h3 className="text-base font-semibold text-gray-900 border-b pb-2">
        Health Highlights ({highlights.length})
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {highlights.map((item, idx) => {
          const isHigh = item.status === "High";
          const isLow = item.status === "Low";
          const badgeClass = isHigh
            ? "bg-red-50 border-red-200 text-red-900"
            : isLow
            ? "bg-amber-50 border-amber-200 text-amber-900"
            : "bg-gray-50 border-gray-200 text-gray-900";

          return (
            <div
              key={idx}
              className={`p-3 rounded-lg border flex items-start gap-3 ${badgeClass}`}
            >
              <span className="text-xl leading-none">
                {isHigh ? "🔴" : isLow ? "🟡" : "⚪"}
              </span>
              <div className="flex-1 text-sm space-y-1">
                <div className="flex justify-between items-center">
                  <span className="font-semibold">{item.name || item.key}</span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded font-bold ${
                      isHigh
                        ? "bg-red-200 text-red-800"
                        : "bg-amber-200 text-amber-800"
                    }`}
                  >
                    {item.status}
                  </span>
                </div>
                <p className="text-xs text-gray-700">{item.title || item.status_reason}</p>
                <div className="text-xs text-gray-600 font-mono">
                  Observed: <span className="font-bold">{item.value} {item.unit}</span> (Ref: {item.reference_range || "N/A"})
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
