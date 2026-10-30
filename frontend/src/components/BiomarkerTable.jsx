import React, { useState, useMemo } from "react";
import {
  CheckCircle2,
  ArrowUpRight,
  ArrowDownRight,
  HelpCircle,
  TrendingUp,
  TrendingDown,
  Minus,
  Search,
  Info,
} from "lucide-react";

export default function BiomarkerTable({ biomarkers = [], onSelectBiomarker, trends = {} }) {
  const [filterMode, setFilterMode] = useState("all"); // 'all', 'abnormal', 'normal'
  const [searchQuery, setSearchQuery] = useState("");

  const safeBiomarkers = useMemo(() => biomarkers || [], [biomarkers]);

  const getStatusConfig = (status) => {
    const s = String(status || "").toLowerCase();
    switch (s) {
      case "normal":
      case "within range":
        return {
          label: "Within Range",
          isAbnormal: false,
          badgeClass: "bg-emerald-50 text-emerald-700 border-emerald-200/80",
          rowClass: "bg-white hover:bg-slate-50/80",
          icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />,
        };
      case "high":
      case "above range":
        return {
          label: "Above Range",
          isAbnormal: true,
          badgeClass: "bg-rose-50 text-rose-700 border-rose-200/80",
          rowClass: "bg-rose-50/20 hover:bg-rose-50/40 border-l-2 border-l-rose-500",
          icon: <ArrowUpRight className="w-3.5 h-3.5 text-rose-600 shrink-0" />,
        };
      case "low":
      case "below range":
        return {
          label: "Below Range",
          isAbnormal: true,
          badgeClass: "bg-rose-50 text-rose-700 border-rose-200/80",
          rowClass: "bg-rose-50/20 hover:bg-rose-50/40 border-l-2 border-l-rose-500",
          icon: <ArrowDownRight className="w-3.5 h-3.5 text-rose-600 shrink-0" />,
        };
      case "needs review":
        return {
          label: "Needs Review",
          isAbnormal: true,
          badgeClass: "bg-indigo-50 text-indigo-700 border-indigo-200/80",
          rowClass: "bg-indigo-50/20 hover:bg-indigo-50/40 border-l-2 border-l-indigo-500",
          icon: <HelpCircle className="w-3.5 h-3.5 text-indigo-600 shrink-0" />,
        };
      default:
        return {
          label: status || "Unknown",
          isAbnormal: false,
          badgeClass: "bg-slate-100 text-slate-700 border-slate-200",
          rowClass: "bg-white hover:bg-slate-50/80",
          icon: null,
        };
    }
  };

  const counts = useMemo(() => {
    let normal = 0;
    let abnormal = 0;
    safeBiomarkers.forEach((bm) => {
      const cfg = getStatusConfig(bm.status);
      if (cfg.isAbnormal) abnormal++;
      else normal++;
    });
    return { all: safeBiomarkers.length, normal, abnormal };
  }, [safeBiomarkers]);

  const filteredBiomarkers = useMemo(() => {
    return safeBiomarkers.filter((bm) => {
      const cfg = getStatusConfig(bm.status);
      if (filterMode === "abnormal" && !cfg.isAbnormal) return false;
      if (filterMode === "normal" && cfg.isAbnormal) return false;

      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const name = (bm.name || "").toLowerCase();
        const key = (bm.key || "").toLowerCase();
        return name.includes(query) || key.includes(query);
      }
      return true;
    });
  }, [safeBiomarkers, filterMode, searchQuery]);

  if (!safeBiomarkers || safeBiomarkers.length === 0) {
    return (
      <div className="bg-white border border-slate-200/90 rounded-2xl p-8 text-center text-slate-500 text-sm shadow-xs">
        No laboratory parameters detected in this report.
      </div>
    );
  }

  // Format clean, readable reference display
  const formatReferenceDisplay = (bm) => {
    const rawRef = bm?.reference_range ? String(bm.reference_range).trim() : "";
    if (!rawRef || rawRef === "—" || rawRef.toLowerCase() === "n/a" || rawRef.toLowerCase() === "none") {
      return "—";
    }

    const unit = bm?.unit ? String(bm.unit).trim() : "";

    // Replace standard hyphens with readable en-dash '–' with clean spacing
    let formattedRef = rawRef;
    if (/^\d+(?:\.\d+)?\s*[-–]\s*\d+(?:\.\d+)?(?:\s*\(.*?\))?$/.test(rawRef)) {
      formattedRef = rawRef.replace(/\s*[-–]\s*/, " – ");
    }

    // Append unit if not already contained inside rawRef
    if (unit && !formattedRef.toLowerCase().includes(unit.toLowerCase())) {
      // If there is a trailing gender tag e.g. " > 40 (Male) " or " 3.5 – 5.0 (Adult) "
      const genderMatch = formattedRef.match(/^(.*?)\s*(\([A-Za-z\s]+\))$/);
      if (genderMatch) {
        return `${genderMatch[1].trim()} ${unit} ${genderMatch[2].trim()}`;
      }
      return `${formattedRef} ${unit}`;
    }

    return formattedRef;
  };

  const renderTrendBadge = (tr) => {
    if (!tr) {
      return (
        <span className="text-slate-400 text-xs inline-flex items-center justify-center gap-1">
          <Minus className="w-3.5 h-3.5 text-slate-300" />
          <span className="text-[11px] text-slate-400">Baseline</span>
        </span>
      );
    }

    const isUp = tr.direction === "increased";
    const isDown = tr.direction === "decreased";

    return (
      <span
        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-xs font-semibold ${
          isUp
            ? "bg-rose-50 text-rose-700 border border-rose-200"
            : isDown
            ? "bg-purple-50 text-purple-700 border border-purple-200"
            : "bg-slate-50 text-slate-600 border border-slate-200"
        }`}
        title={tr.summary}
      >
        {isUp ? <TrendingUp className="w-3 h-3" /> : isDown ? <TrendingDown className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
        <span>{tr.arrow} {Math.abs(tr.percentage_change)}%</span>
      </span>
    );
  };

  return (
    <div className="bg-white border border-slate-200/90 rounded-2xl overflow-hidden shadow-xs">
      {/* Table Header with Quick Filters & Search */}
      <div className="px-5 sm:px-6 py-4.5 border-b border-slate-200/80 bg-slate-50/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <span>Laboratory Parameters</span>
            <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-200 text-slate-700">
              {biomarkers.length}
            </span>
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Click any parameter to view clinical significance, reference intervals, and interpretation.
          </p>
        </div>

        {/* Filter Pills & Search */}
        <div className="flex items-center gap-2.5 flex-wrap">
          {/* Compact Filter Pills */}
          <div className="flex items-center bg-slate-100/90 p-1 rounded-xl border border-slate-200/60 text-xs">
            <button
              type="button"
              onClick={() => setFilterMode("all")}
              className={`px-3 py-1 rounded-lg font-semibold transition-all ${
                filterMode === "all"
                  ? "bg-white text-slate-900 shadow-2xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              All {counts.all}
            </button>
            <button
              type="button"
              onClick={() => setFilterMode("normal")}
              className={`px-3 py-1 rounded-lg font-semibold transition-all ${
                filterMode === "normal"
                  ? "bg-white text-emerald-700 shadow-2xs"
                  : "text-slate-600 hover:text-emerald-600"
              }`}
            >
              Within Range {counts.normal}
            </button>
            {counts.abnormal > 0 && (
              <button
                type="button"
                onClick={() => setFilterMode("abnormal")}
                className={`px-3 py-1 rounded-lg font-semibold transition-all flex items-center gap-1 ${
                  filterMode === "abnormal"
                    ? "bg-white text-rose-700 shadow-2xs"
                    : "text-slate-600 hover:text-rose-600"
                }`}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
                Outside Range {counts.abnormal}
              </button>
            )}
          </div>

          {/* Quick Search Input */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search parameters..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-3 py-1.5 text-xs bg-white border border-slate-200 rounded-xl placeholder:text-slate-400 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 w-32 sm:w-44 transition-all"
            />
          </div>
        </div>
      </div>

      {/* Desktop / Tablet Table */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full text-left text-sm" role="table">
          <thead className="bg-slate-50 text-[11px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200/80">
            <tr>
              <th scope="col" className="px-6 py-3.5">Parameter</th>
              <th scope="col" className="px-5 py-3.5 text-right">Result</th>
              <th scope="col" className="px-6 py-3.5">Reference Range</th>
              <th scope="col" className="px-6 py-3.5 text-center">Trend</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {filteredBiomarkers.length === 0 ? (
              <tr>
                <td colSpan="4" className="px-6 py-8 text-center text-xs text-slate-400">
                  No parameters match your search or filter.
                </td>
              </tr>
            ) : (
              filteredBiomarkers.map((bm, index) => {
                const k = (bm.key || "").toLowerCase();
                const tr = trends[k];
                const statusCfg = getStatusConfig(bm.status);

                return (
                  <tr
                    key={bm.key || index}
                    onClick={() => onSelectBiomarker && onSelectBiomarker(bm)}
                    tabIndex={0}
                    role="button"
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        if (onSelectBiomarker) onSelectBiomarker(bm);
                      }
                    }}
                    className={`focus:bg-blue-50/40 focus:outline-none cursor-pointer transition-colors group ${statusCfg.rowClass}`}
                  >
                    {/* 1. Parameter Name with subtle, non-noisy lab reference indicator */}
                    <td className="px-6 py-4 font-semibold text-slate-900 group-hover:text-blue-600 transition-colors">
                      <div className="flex items-center gap-1.5">
                        <span className="text-sm font-semibold">{bm.name || bm.key}</span>
                        {bm.reference_source === "report" && (
                          <span
                            className="text-slate-400 hover:text-slate-600 text-xs cursor-help inline-flex items-center"
                            title="Verified directly from laboratory report reference range"
                            aria-label="Laboratory reference"
                          >
                            <Info className="w-3 h-3 text-slate-400" />
                          </span>
                        )}
                      </div>
                    </td>

                    {/* 2. Numerical Result */}
                    <td className="px-5 py-4 text-right font-bold text-slate-900 font-mono text-base">
                      {bm.value !== null && bm.value !== undefined ? bm.value : "—"}{" "}
                      <span className="font-sans font-normal text-slate-500 text-xs ml-0.5">
                        {bm.unit}
                      </span>
                    </td>

                    {/* 3. Reference Range */}
                    <td className="px-6 py-4 text-slate-700 font-mono text-xs">
                      {formatReferenceDisplay(bm)}
                    </td>

                    {/* 4. Trend Badge */}
                    <td className="px-6 py-4 text-center">
                      {renderTrendBadge(tr)}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Mobile Card Layout */}
      <div className="md:hidden divide-y divide-slate-100">
        {filteredBiomarkers.length === 0 ? (
          <div className="p-6 text-center text-xs text-slate-400">
            No parameters match your search or filter.
          </div>
        ) : (
          filteredBiomarkers.map((bm, index) => {
            const statusCfg = getStatusConfig(bm.status);
            const k = (bm.key || "").toLowerCase();
            const tr = trends[k];

            return (
              <div
                key={bm.key || index}
                onClick={() => onSelectBiomarker && onSelectBiomarker(bm)}
                role="button"
                tabIndex={0}
                className={`p-4.5 transition-colors cursor-pointer space-y-2.5 ${statusCfg.rowClass}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h4 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                      <span>{bm.name || bm.key}</span>
                      {bm.reference_source === "report" && (
                        <span title="Laboratory reference" className="text-slate-400 text-xs">
                          <Info className="w-3 h-3 text-slate-400 inline" />
                        </span>
                      )}
                    </h4>
                  </div>
                  {tr && (
                    <div>
                      {renderTrendBadge(tr)}
                    </div>
                  )}
                </div>

                <div className="flex items-baseline justify-between pt-1">
                  <div>
                    <span className="text-[11px] text-slate-500 block">Result</span>
                    <span className="text-lg font-bold font-mono text-slate-900">
                      {bm.value} <span className="font-sans font-normal text-xs text-slate-500">{bm.unit}</span>
                    </span>
                  </div>

                  <div className="text-right">
                    <span className="text-[11px] text-slate-500 block">Reference Range</span>
                    <span className="text-xs font-mono text-slate-700">
                      {formatReferenceDisplay(bm)}
                    </span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
