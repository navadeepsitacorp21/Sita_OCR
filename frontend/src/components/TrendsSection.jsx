import React from "react";
import { TrendingUp, TrendingDown, Minus, Clock, Calendar } from "lucide-react";
import { formatReportDate } from "../utils/dateUtils";

export default function TrendsSection({ trends = {} }) {
  const trendList = Object.values(trends || {});
  const hasTrends = trendList.length > 0;

  if (!hasTrends) {
    return (
      <section aria-label="Longitudinal Trends" className="bg-white border border-slate-200/90 rounded-2xl p-5 sm:p-6 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
          <div className="space-y-0.5">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-blue-600" />
              <span>Trend</span>
            </h3>
            <p className="text-xs text-slate-500">
              No previous report available yet. Save future reports to Health Vault to track changes over time.
            </p>
          </div>
          <span className="text-[11px] font-semibold text-slate-400 bg-slate-50 border border-slate-200 px-2.5 py-1 rounded-lg self-start sm:self-auto">
            Baseline Report
          </span>
        </div>
      </section>
    );
  }

  return (
    <section aria-label="Longitudinal Trends" className="bg-white border border-slate-200/90 rounded-2xl p-6 sm:p-7 shadow-xs space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 border-b border-slate-100 pb-3.5">
        <div>
          <h3 className="text-base font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-blue-600" />
            <span>Longitudinal Trends</span>
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Comparison against previous laboratory records in your Health Vault.
          </p>
        </div>
        <span className="text-[11px] font-semibold text-blue-700 bg-blue-50 px-2.5 py-1 rounded-md border border-blue-200 self-start sm:self-auto">
          {trendList.length} Tracked {trendList.length === 1 ? "Parameter" : "Parameters"}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
        {trendList.map((tr, idx) => {
          const isUp = tr.direction === "increased";
          const isDown = tr.direction === "decreased";

          return (
            <div
              key={tr.key || idx}
              className="p-4 bg-slate-50/70 border border-slate-200/80 rounded-xl space-y-2.5 text-xs"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-900 text-sm">{tr.name}</span>
                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md font-semibold text-[11px] ${
                    isUp
                      ? "bg-rose-50 text-rose-700 border border-rose-200"
                      : isDown
                      ? "bg-purple-50 text-purple-700 border border-purple-200"
                      : "bg-slate-100 text-slate-600 border border-slate-200"
                  }`}
                >
                  {isUp ? <TrendingUp className="w-3 h-3" /> : isDown ? <TrendingDown className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
                  <span>{tr.arrow} {Math.abs(tr.percentage_change)}%</span>
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 pt-1 border-t border-slate-200/60">
                <div>
                  <span className="text-slate-400 block text-[10px]">Previous</span>
                  <span className="font-mono font-semibold text-slate-700">
                    {tr.previous_value} {tr.unit}
                  </span>
                  {tr.previous_report_date && (
                    <span className="text-[10px] text-slate-400 block truncate">
                      {formatReportDate(tr.previous_report_date)}
                    </span>
                  )}
                </div>

                <div className="text-right">
                  <span className="text-slate-400 block text-[10px]">Current</span>
                  <span className="font-mono font-bold text-slate-900">
                    {tr.current_value} {tr.unit}
                  </span>
                </div>
              </div>

              {tr.summary && (
                <p className="text-[11px] text-slate-600 leading-snug pt-1 border-t border-slate-200/60">
                  {tr.summary}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
