import React, { useEffect, useState } from "react";
import { getHealthVaultReports, deleteHealthVaultReportById } from "../services/api";
import TimelineCard from "../components/TimelineCard";
import { FolderHeart, RefreshCw, CheckCircle2, AlertCircle, FileText } from "lucide-react";
import { Link } from "react-router-dom";

export default function VaultPage() {
  const [reports, setReports] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [activeFilter, setActiveFilter] = useState("ALL");

  const fetchReports = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getHealthVaultReports();
      setReports(data.reports || []);
    } catch (err) {
      console.error("Vault fetch error:", err);
      setError("Unable to retrieve your Health Vault reports. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const handleDelete = async (reportId) => {
    setDeletingId(reportId);
    try {
      await deleteHealthVaultReportById(reportId);
      setToastMessage("Report removed from Health Vault.");
      setTimeout(() => setToastMessage(null), 3000);
      await fetchReports();
    } catch (err) {
      console.error("Delete error:", err);
      alert("Failed to delete the report. Please try again.");
    } finally {
      setDeletingId(null);
    }
  };

  const filteredReports = reports.filter((r) => {
    if (activeFilter === "ALL") return true;
    const type = (r.report_type || "").toUpperCase();
    if (activeFilter === "CBC") return type === "CBC";
    if (activeFilter === "LFT") return type === "LFT" || type === "LIVER_FUNCTION_TEST";
    if (activeFilter === "KFT") return type === "KFT" || type === "KIDNEY_FUNCTION_TEST";
    if (activeFilter === "LIPID") return type === "LIPID" || type === "LIPID_PROFILE";
    return true;
  });

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Title & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Health Vault
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Persisted history of processed laboratory reports and longitudinal records.
          </p>
        </div>
        <button
          onClick={fetchReports}
          disabled={isLoading}
          className="self-start sm:self-auto px-3.5 py-2 text-xs font-semibold bg-white border border-slate-200/90 rounded-xl hover:bg-slate-50 text-slate-700 transition-colors shadow-2xs flex items-center gap-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-blue-600" : ""}`} />
          <span>{isLoading ? "Refreshing..." : "Refresh"}</span>
        </button>
      </div>

      {/* Filter Tabs (All Reports, CBC, LFT, KFT) */}
      <div className="flex items-center gap-1.5 border-b border-slate-200/80 pb-3 overflow-x-auto">
        {[
          { id: "ALL", label: "All Reports" },
          { id: "CBC", label: "CBC" },
          { id: "LFT", label: "LFT" },
          { id: "KFT", label: "KFT" },
          { id: "LIPID", label: "Lipid Profile" },
        ].map((tab) => {
          const count =
            tab.id === "ALL"
              ? reports.length
              : reports.filter((r) => {
                  const t = (r.report_type || "").toUpperCase();
                  if (tab.id === "CBC") return t === "CBC";
                  if (tab.id === "LFT") return t === "LFT" || t === "LIVER_FUNCTION_TEST";
                  if (tab.id === "KFT") return t === "KFT" || t === "KIDNEY_FUNCTION_TEST";
                  if (tab.id === "LIPID") return t === "LIPID" || t === "LIPID_PROFILE";
                  return false;
                }).length;

          const isSelected = activeFilter === tab.id;

          return (
            <button
              key={tab.id}
              onClick={() => setActiveFilter(tab.id)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all flex items-center gap-1.5 ${
                isSelected
                  ? "bg-slate-900 text-white shadow-2xs"
                  : "bg-white text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-slate-200/70"
              }`}
            >
              <span>{tab.label}</span>
              <span
                className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                  isSelected ? "bg-slate-800 text-slate-200" : "bg-slate-100 text-slate-500"
                }`}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Toast feedback */}
      {toastMessage && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-xl flex items-center gap-2 animate-in fade-in">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-xl flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="space-y-4">
          {[1, 2].map((i) => (
            <div
              key={i}
              className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-xs animate-pulse space-y-3"
            >
              <div className="h-5 bg-slate-100 rounded-md w-1/3" />
              <div className="h-3 bg-slate-100 rounded-md w-1/2" />
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && filteredReports.length === 0 && (
        <div className="bg-white border border-slate-200/90 rounded-2xl p-10 text-center space-y-3 shadow-xs">
          <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto">
            <FolderHeart className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-bold text-slate-900">No reports stored in this view</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              Analyze a medical report and click "Save to Health Vault" to track your parameters over time.
            </p>
          </div>
          <div className="pt-2">
            <Link
              to="/"
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl transition-all shadow-xs"
            >
              <span>Analyze New Report</span>
            </Link>
          </div>
        </div>
      )}

      {/* Report Cards Feed */}
      {!isLoading && filteredReports.length > 0 && (
        <div className="space-y-3.5">
          {filteredReports.map((report) => (
            <TimelineCard
              key={report.id}
              report={report}
              onDelete={handleDelete}
              isDeleting={deletingId === report.id}
            />
          ))}
        </div>
      )}
    </div>
  );
}
