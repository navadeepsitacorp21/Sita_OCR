import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getHealthVaultReportById } from "../services/api";
import BiomarkerTable from "../components/BiomarkerTable";
import PatternCards from "../components/PatternCards";
import UnderstandingYourResults from "../components/UnderstandingYourResults";
import DoctorDiscussion from "../components/DoctorDiscussion";
import BiomarkerDetailModal from "../components/BiomarkerDetailModal";
import {
  ArrowLeft,
  AlertCircle,
  Calendar,
  Clock,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  Building2,
  FileText,
} from "lucide-react";
import { formatReportDate, formatAnalyzedDate, formatDateTime } from "../utils/dateUtils";

export default function ReportPage() {
  const { report_id } = useParams();
  const [reportDetail, setReportDetail] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedBiomarker, setSelectedBiomarker] = useState(null);

  useEffect(() => {
    let isMounted = true;
    if (!report_id) return;

    const fetchReport = async () => {
      try {
        const data = await getHealthVaultReportById(report_id);
        if (isMounted) {
          setReportDetail(data);
        }
      } catch (err) {
        if (isMounted) {
          console.error("Fetch report detail error:", err);
          setError("We couldn't retrieve the report details. Please try again.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    fetchReport();
    return () => {
      isMounted = false;
    };
  }, [report_id]);

  if (isLoading) {
    return (
      <div className="py-20 text-center text-slate-500 text-xs space-y-3">
        <div className="w-9 h-9 rounded-full border-2 border-blue-200 border-t-blue-600 animate-spin mx-auto" />
        <p className="font-semibold text-slate-700">Loading archived report...</p>
      </div>
    );
  }

  if (error || !reportDetail) {
    return (
      <div className="space-y-4 max-w-5xl mx-auto">
        <Link
          to="/vault"
          className="text-xs text-blue-600 hover:underline inline-flex items-center gap-1 font-semibold"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Health Vault
        </Link>
        <div className="bg-rose-50 border border-rose-200 text-rose-800 p-6 rounded-2xl text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error || "Report could not be retrieved from Health Vault."}</span>
        </div>
      </div>
    );
  }

  const storedReport = reportDetail.report || {};

  const parsedReport = storedReport.parsed_report || {};
  const biomarkers = parsedReport.biomarkers || [];
  const patterns = parsedReport.patterns || storedReport.patterns || [];
  const statusSummary = parsedReport.status_summary || {};

  const reportMeta = storedReport.report || storedReport.metadata?.report || parsedReport.report || parsedReport.metadata?.report || {};
  const rawReportDate = storedReport.report_date || reportDetail.report_date || reportMeta.report_date || reportMeta.collection_date || reportMeta.reported_date || reportMeta.received_date || reportMeta.ordered_date;
  const formattedReportDate = formatReportDate(rawReportDate);

  const analyzedAt = storedReport.analyzed_at || reportDetail.analyzed_at || parsedReport.analyzed_at || null;
  const savedToVaultAt =
    reportDetail.saved_at ||
    reportDetail.saved_to_vault_at ||
    storedReport.saved_at ||
    storedReport.saved_to_vault_at ||
    null;

  const abnormalTotal = (statusSummary.high || 0) + (statusSummary.low || 0);
  const isAllNormal = abnormalTotal === 0;

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

  const rawReportType = storedReport.report_type || storedReport.classification?.report_type;
  const typeInfo = getReportTypeDisplay(rawReportType);
  const reportTitle = typeInfo.name;
  const reportCode = typeInfo.code;

  const labName =
    storedReport.metadata?.hospital?.name ||
    parsedReport.metadata?.hospital?.name ||
    storedReport.hospital_name ||
    storedReport.laboratory_name ||
    null;

  const explanation =
    storedReport.explanation ||
    parsedReport.explanation ||
    storedReport.analysis?.explanation ||
    null;

  const reportInterpretation =
    storedReport.report_interpretation ||
    reportDetail.report_interpretation ||
    storedReport.metadata?.report_interpretation ||
    parsedReport.report_interpretation ||
    parsedReport.metadata?.report_interpretation ||
    null;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header & Back link */}
      <div className="space-y-4">
        <Link
          to="/vault"
          className="text-xs text-blue-600 hover:text-blue-700 inline-flex items-center gap-1 font-bold transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Health Vault
        </Link>

        {/* SECTION 2: EXECUTIVE HEADER CARD */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-6 sm:p-7 shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
            <div className="space-y-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-blue-600 block">
                Medical Report Analysis
              </span>

              {/* Visual Focus: Report Type */}
              <div className="flex items-center gap-2.5 flex-wrap">
                <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
                  {reportTitle}
                </h1>
                <span className="px-2.5 py-0.5 rounded-lg bg-blue-50 text-blue-700 font-mono text-xs font-bold border border-blue-200">
                  {reportCode}
                </span>
              </div>

              {/* Laboratory Name if available */}
              {labName && (
                <div className="flex items-center gap-1.5 text-xs text-slate-600 font-medium">
                  <Building2 className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <span>{labName}</span>
                </div>
              )}

              {/* Date Metadata */}
              <div className="flex items-center gap-x-4 gap-y-1.5 text-xs text-slate-600 flex-wrap pt-0.5">
                <div className="inline-flex items-center gap-1.5 font-medium">
                  <Calendar className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                  <span>Report Date:</span>
                  {formattedReportDate ? (
                    <span className="font-bold text-slate-900 bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200">
                      {formattedReportDate}
                    </span>
                  ) : (
                    <span className="text-slate-400 italic">Report date unavailable</span>
                  )}
                </div>

                {analyzedAt && (
                  <>
                    <span className="text-slate-300 hidden sm:inline">•</span>
                    <div className="inline-flex items-center gap-1.5 text-slate-500">
                      <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      <span>Analyzed:</span>
                      <span className="font-medium text-slate-800">
                        {formatDateTime(analyzedAt)}
                      </span>
                    </div>
                  </>
                )}

                <span className="text-slate-300 hidden sm:inline">•</span>

                {savedToVaultAt ? (
                  <div className="inline-flex items-center gap-1.5 text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-md border border-emerald-200/80 font-medium">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                    <span>Saved:</span>
                    <span className="font-semibold text-emerald-900">
                      {formatDateTime(savedToVaultAt)} ✓
                    </span>
                  </div>
                ) : (
                  <div className="inline-flex items-center gap-1.5 text-slate-500 font-medium">
                    <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span>Saved:</span>
                    <span className="text-slate-400 italic">Not saved yet</span>
                  </div>
                )}
              </div>
            </div>

            <div className="shrink-0 self-start sm:self-center">
              {savedToVaultAt && (
                <span className="px-3.5 py-2 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-2xs">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Saved to Health Vault ✓</span>
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 1. RESULT SUMMARY */}
      <section aria-label="Result Summary" className="bg-white border border-slate-200/90 rounded-2xl p-5 sm:p-6 shadow-xs">
        <div className="grid grid-cols-3 gap-3">
          <div className="p-3.5 bg-slate-50/70 rounded-xl border border-slate-200/60 text-center">
            <span className="text-xl sm:text-2xl font-bold font-mono text-slate-900 block">
              {parsedReport.biomarkers_found || biomarkers.length}
            </span>
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              Parameters
            </span>
          </div>

          <div className="p-3.5 bg-emerald-50/40 rounded-xl border border-emerald-100 text-center">
            <span className="text-xl sm:text-2xl font-bold font-mono text-emerald-700 block">
              {statusSummary.normal ?? 0}
            </span>
            <span className="text-[11px] font-semibold text-emerald-700 uppercase tracking-wider">
              Within Range
            </span>
          </div>

          <div className="p-3.5 bg-rose-50/40 rounded-xl border border-rose-100 text-center">
            <span className="text-xl sm:text-2xl font-bold font-mono text-rose-700 block">
              {abnormalTotal}
            </span>
            <span className="text-[11px] font-semibold text-rose-700 uppercase tracking-wider">
              Outside Range
            </span>
          </div>
        </div>
      </section>

      {/* 3. UNDERSTANDING YOUR RESULTS (Humanoid Clinical Summary) */}
      <UnderstandingYourResults
        explanation={explanation}
        biomarkers={biomarkers}
        patterns={patterns}
      />

      {/* 4. ALL PARAMETERS (Complete reference table) */}
      <BiomarkerTable
        biomarkers={biomarkers}
        onSelectBiomarker={(bm) => setSelectedBiomarker(bm)}
      />

      {/* 5. OBSERVED PATTERNS */}
      {patterns.length > 0 && <PatternCards patterns={patterns} />}

      {/* 6. LABORATORY REPORT NOTE (Reported verbatim by testing lab) */}
      {reportInterpretation?.text && (
        <div className="bg-amber-50/80 border border-amber-200 rounded-2xl p-4 sm:p-5 shadow-xs space-y-2">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-amber-700 shrink-0" />
              <h3 className="text-xs font-bold text-amber-950 uppercase tracking-wider">
                Laboratory Report Note
              </h3>
            </div>
            <span className="text-[10px] font-semibold text-amber-800 bg-amber-100 px-2.5 py-0.5 rounded-full border border-amber-200">
              Reported by the laboratory
            </span>
          </div>
          <p className="text-sm text-amber-950 font-semibold leading-relaxed">
            "{reportInterpretation.text}"
          </p>
          <p className="text-[11px] text-amber-800/80 leading-normal">
            This is a clinical observation printed directly on the physical laboratory report. It is preserved for your physician's evaluation and is not an automated algorithmic diagnosis.
          </p>
        </div>
      )}

      {/* 7. THINGS TO DISCUSS WITH YOUR DOCTOR */}
      {explanation?.doctor_discussion && explanation.doctor_discussion.length > 0 && (
        <DoctorDiscussion discussionPoints={explanation.doctor_discussion} />
      )}

      {/* Medical Safety & Compliance Footer */}
      <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-500 leading-relaxed flex items-start gap-2.5">
        <ShieldCheck className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
        <div>
          Persisted laboratory data for personal health tracking. Reference intervals are sourced directly from the original laboratory report. Consult your physician for medical diagnosis.
        </div>
      </div>

      {/* SECTION 11: BIOMARKER DETAIL MODAL */}
      {selectedBiomarker && (
        <BiomarkerDetailModal
          biomarker={selectedBiomarker}
          onClose={() => setSelectedBiomarker(null)}
        />
      )}
    </div>
  );
}
