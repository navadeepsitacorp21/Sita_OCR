import React, { useState } from "react";
import { Link } from "react-router-dom";
import { analyzeMedicalReport, saveReportToHealthVault } from "../services/api";
import UploadBox from "../components/UploadBox";
import BiomarkerTable from "../components/BiomarkerTable";
import PatternCards from "../components/PatternCards";
import UnderstandingYourResults from "../components/UnderstandingYourResults";
import TrendsSection from "../components/TrendsSection";
import DoctorDiscussion from "../components/DoctorDiscussion";
import BiomarkerDetailModal from "../components/BiomarkerDetailModal";
import {
  AlertTriangle,
  CheckCircle2,
  ShieldCheck,
  FolderHeart,
  Calendar,
  Clock,
  ArrowRight,
  FileText,
  Loader2,
  Building2,
} from "lucide-react";
import { formatReportDate, formatAnalyzedDate, formatDateTime } from "../utils/dateUtils";

export default function UploadPage() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [patientGender, setPatientGender] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorState, setErrorState] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [selectedBiomarker, setSelectedBiomarker] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(null);
  const [saveError, setSaveError] = useState(null);

  const mapErrorToUserFriendly = (err) => {
    if (!err) return null;
    const status = err.response?.status;
    const detail = err.response?.data?.detail;

    if (status === 409) {
      const existingId = typeof detail === "object" ? detail.existing_report_id : null;
      const savedAt = typeof detail === "object" ? (detail.saved_at || detail.saved_to_vault_at) : null;
      return {
        code: 409,
        title: "Report Already Saved",
        message: "This report is already stored in your Health Vault.",
        existingReportId: existingId,
        savedToVaultAt: savedAt,
      };
    }
    if (status === 413) {
      return {
        code: 413,
        title: "File Too Large",
        message: "The uploaded file exceeds the 20 MB size limit.",
      };
    }
    if (status === 400) {
      return {
        code: 400,
        title: "Invalid File",
        message:
          typeof detail === "string"
            ? detail
            : "Please upload a valid PDF, PNG, JPG, or WEBP medical report.",
      };
    }
    if (status === 422) {
      return {
        code: 422,
        title: "Unsupported Panel",
        message: "Supported document types are Complete Blood Count (CBC), Liver Function (LFT), Kidney Function (KFT), and Lipid Profile.",
      };
    }
    if (status === 504) {
      return {
        code: 504,
        title: "Analysis Timeout",
        message: "The OCR extraction took longer than expected to process. Please try uploading a clearer, higher-contrast, or cropped image of the report.",
      };
    }

    return {
      code: status || 500,
      title: "Analysis Failed",
      message: typeof detail === "string" ? detail : "We encountered an issue analyzing your report. Please verify clarity and try again.",
    };
  };

  const handleAnalyze = async () => {
    if (!selectedFile || isLoading) return;

    setIsLoading(true);
    setErrorState(null);
    setAnalysisResult(null);
    setSaveSuccess(null);
    setSaveError(null);

    try {
      const data = await analyzeMedicalReport(selectedFile, patientGender || null);
      if (data.status === "unsupported_report_type" || data.is_supported === false) {
        setErrorState({
          code: 422,
          title: "Unsupported Panel",
          message: "Supported document types are Complete Blood Count (CBC), Liver Function (LFT), Kidney Function (KFT), and Lipid Profile.",
        });
      } else if (data.status === "unreadable_report") {
        setErrorState({
          code: 400,
          title: "Unreadable Document",
          message: "Could not detect readable laboratory text. Please upload a clear photo or digital PDF.",
        });
      } else {
        setAnalysisResult(data);
      }
    } catch (err) {
      console.error("Analysis request error:", err);
      setErrorState(mapErrorToUserFriendly(err));
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveToVault = async () => {
    if (!analysisResult || isSaving) return;
    setIsSaving(true);
    setSaveError(null);

    try {
      const res = await saveReportToHealthVault({
        requestId: analysisResult.request_id,
        filename: analysisResult.filename,
        reportType: analysisResult.report_type,
        patientGender: analysisResult.patient_gender || patientGender || null,
        rawParsedReport: analysisResult.raw_parsed_report,
        fileHash: analysisResult.file_hash,
        analyzedAt: analysisResult.analyzed_at,
      });
      setSaveSuccess(res);
    } catch (err) {
      console.error("Save to vault error:", err);
      setSaveError(mapErrorToUserFriendly(err));
    } finally {
      setIsSaving(false);
    }
  };

  const summary = analysisResult?.summary || {};
  const biomarkers = analysisResult?.biomarkers || [];
  const patterns = analysisResult?.patterns || [];
  const trends = analysisResult?.trends || {};
  const explanation = analysisResult?.explanation || null;

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
        return { name: type || "Medical Laboratory Report", code: type || "LAB" };
    }
  };

  const reportTypeInfo = analysisResult ? getReportTypeDisplay(analysisResult.report_type) : null;
  const abnormalTotal = summary.abnormal_total || 0;
  const isAllNormal = abnormalTotal === 0;

  // Extract lab or hospital name if available from metadata
  const labName =
    analysisResult?.metadata?.hospital?.name ||
    analysisResult?.hospital_name ||
    analysisResult?.laboratory_name ||
    analysisResult?.report?.hospital?.name ||
    null;

  const reportInterpretation =
    analysisResult?.report_interpretation ||
    analysisResult?.metadata?.report_interpretation ||
    analysisResult?.raw_parsed_report?.report_interpretation ||
    null;

  const savedAt =
    saveSuccess?.saved_at ||
    saveSuccess?.saved_to_vault_at ||
    saveError?.savedToVaultAt ||
    analysisResult?.saved_at ||
    analysisResult?.saved_to_vault_at ||
    null;
  const savedToVaultAt = savedAt;

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* 1. Page Title & Intro */}
      <div className="space-y-1.5">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Medical Report Analysis
        </h1>
        <p className="text-slate-500 text-sm leading-relaxed max-w-2xl">
          Upload your CBC, LFT, KFT, or Lipid Profile report for instant deterministic analysis, reference range verification, and clear educational insights.
        </p>
      </div>

      {/* 2. Upload Box & Setup Card */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 sm:p-7 shadow-xs space-y-5">
        <UploadBox
          selectedFile={selectedFile}
          setSelectedFile={setSelectedFile}
          isLoading={isLoading}
        />

        {/* Patient Reference Context */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 border-t border-slate-100">
          <div>
            <span className="text-xs font-bold text-slate-800 block">
              Patient Sex for Reference Range
            </span>
            <span className="text-[11px] text-slate-400">
              Auto-detected from report if available. Specify only if your report omits it.
            </span>
          </div>

          <div className="flex items-center gap-1.5" role="radiogroup" aria-label="Patient sex for reference ranges">
            {[
              { id: "male", label: "Male" },
              { id: "female", label: "Female" },
              { id: "", label: "Auto / Unspecified" },
            ].map((opt) => {
              const isSelected = patientGender === opt.id;
              return (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => setPatientGender(opt.id)}
                  disabled={isLoading}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    isSelected
                      ? "bg-slate-900 text-white shadow-2xs"
                      : "bg-slate-100 hover:bg-slate-200 text-slate-700"
                  }`}
                  role="radio"
                  aria-checked={isSelected}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Primary Action Button */}
        <button
          type="button"
          onClick={handleAnalyze}
          disabled={!selectedFile || isLoading}
          className="w-full py-3.5 text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed rounded-xl transition-all shadow-sm shadow-blue-600/20 flex items-center justify-center gap-2 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Analyzing report with clinical rule engine...</span>
            </>
          ) : (
            <>
              <span>Analyze Report</span>
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>
      </div>

      {/* Loading Progress State */}
      {isLoading && (
        <div className="bg-white border border-slate-200/90 rounded-2xl p-8 sm:p-10 shadow-xs space-y-6 text-center animate-in fade-in duration-200">
          <div className="w-14 h-14 rounded-2xl bg-blue-50 border border-blue-100 text-blue-600 flex items-center justify-center mx-auto animate-pulse">
            <FileText className="w-7 h-7" />
          </div>
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-slate-900 tracking-tight">
              Processing Laboratory Document
            </h3>
            <p className="text-xs text-slate-500">
              Extracting parameters, matching report reference intervals, and applying deterministic rules.
            </p>
          </div>

          <div className="max-w-xs mx-auto grid grid-cols-3 gap-2 pt-2 text-xs text-slate-600">
            <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-200/60 font-medium">
              OCR Engine
            </div>
            <div className="p-2.5 bg-blue-50 text-blue-700 rounded-xl border border-blue-200 font-bold animate-pulse">
              Parsing
            </div>
            <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-200/60 text-slate-400">
              Insights
            </div>
          </div>
        </div>
      )}

      {/* Error State */}
      {errorState && !isLoading && (
        <div className="bg-rose-50 border border-rose-200 text-rose-900 p-5 rounded-2xl shadow-xs space-y-2 animate-in fade-in">
          <div className="flex items-start gap-2.5">
            <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div className="space-y-0.5 flex-1">
              <h4 className="text-sm font-bold text-rose-950">{errorState.title}</h4>
              <p className="text-xs text-rose-800 leading-relaxed">{errorState.message}</p>
            </div>
          </div>
          {errorState.code === 409 && errorState.existingReportId && (
            <div className="pt-2 border-t border-rose-200/60 flex justify-end">
              <Link
                to={`/report/${errorState.existingReportId}`}
                className="px-3 py-1.5 text-xs font-bold text-rose-900 bg-white border border-rose-300 rounded-lg hover:bg-rose-100 transition-colors inline-flex items-center gap-1.5"
              >
                <span>View Existing Report</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          )}
        </div>
      )}

      {/* Analysis Results View */}
      {analysisResult && !isLoading && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {/* SECTION 2: REPORT HEADER */}
          <div className="bg-white border border-slate-200/90 rounded-2xl p-6 sm:p-7 shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
              <div className="space-y-2">
                <span className="text-[11px] font-bold uppercase tracking-wider text-blue-600 block">
                  Medical Report Analysis
                </span>

                {/* Report Type as Visual Focus */}
                <div className="flex items-center gap-2.5 flex-wrap">
                  <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
                    {reportTypeInfo.name}
                  </h2>
                  <span className="px-2.5 py-0.5 rounded-lg bg-blue-50 text-blue-700 font-mono text-xs font-bold border border-blue-200">
                    {reportTypeInfo.code}
                  </span>
                </div>

                {/* Laboratory name if available */}
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
                    {analysisResult.report_date ? (
                      <span className="font-bold text-slate-900 bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200">
                        {formatReportDate(analysisResult.report_date)}
                      </span>
                    ) : (
                      <span className="text-slate-400 italic">Report date unavailable</span>
                    )}
                  </div>

                  <span className="text-slate-300 hidden sm:inline">•</span>

                  <div className="inline-flex items-center gap-1.5 text-slate-500 font-medium">
                    <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span>Analyzed:</span>
                    <span className="text-slate-800">
                      {formatDateTime(analysisResult.analyzed_at) || "Unavailable"}
                    </span>
                  </div>

                  <span className="text-slate-300 hidden sm:inline">•</span>

                  {savedAt ? (
                    <div className="inline-flex items-center gap-1.5 text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-md border border-emerald-200/80 font-medium">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                      <span>Saved:</span>
                      <span className="font-semibold text-emerald-900">
                        {formatDateTime(savedAt)} ✓
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

              {/* Action: Save to Health Vault */}
              <div className="shrink-0 self-start sm:self-center">
                {savedAt ? (
                  <div className="flex items-center gap-2">
                    <span className="px-3.5 py-2 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-2xs">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      <span>Saved to Health Vault ✓</span>
                    </span>
                    <Link
                      to="/vault"
                      className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition-colors"
                    >
                      View Vault
                    </Link>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={handleSaveToVault}
                    disabled={isSaving}
                    className="px-4 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-xl text-xs font-bold transition-all shadow-xs flex items-center gap-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {isSaving ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Saving...</span>
                      </>
                    ) : (
                      <>
                        <FolderHeart className="w-3.5 h-3.5" />
                        <span>Save to Health Vault</span>
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>

            {/* Save duplicate error notice */}
            {saveError && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 flex items-center justify-between gap-3">
                <span>{saveError.message}</span>
                {saveError.existingReportId && (
                  <Link
                    to={`/report/${saveError.existingReportId}`}
                    className="px-2.5 py-1 font-bold text-amber-900 bg-white border border-amber-300 rounded-md hover:bg-amber-100 shrink-0"
                  >
                    View Report
                  </Link>
                )}
              </div>
            )}
          </div>

          {/* 1. RESULT SUMMARY */}
          <section aria-label="Result Summary" className="bg-white border border-slate-200/90 rounded-2xl p-5 sm:p-6 shadow-xs">
            <div className="grid grid-cols-3 gap-3">
              <div className="p-3.5 bg-slate-50/70 rounded-xl border border-slate-200/60 text-center">
                <span className="text-xl sm:text-2xl font-bold font-mono text-slate-900 block">
                  {summary.total_parameters || biomarkers.length}
                </span>
                <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                  Parameters
                </span>
              </div>

              <div className="p-3.5 bg-emerald-50/40 rounded-xl border border-emerald-100 text-center">
                <span className="text-xl sm:text-2xl font-bold font-mono text-emerald-700 block">
                  {summary.normal || 0}
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
            trends={trends}
            onSelectBiomarker={(bm) => setSelectedBiomarker(bm)}
          />

          {/* 5. OBSERVED PATTERNS (Only when meaningful patterns exist) */}
          {patterns.length > 0 && <PatternCards patterns={patterns} />}

          {/* 6. LABORATORY REPORT NOTE (Original lab comments verbatim) */}
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

          {/* 7. THINGS TO DISCUSS WITH YOUR DOCTOR (Short grouped discussion points) */}
          {explanation?.doctor_discussion && explanation.doctor_discussion.length > 0 && (
            <DoctorDiscussion discussionPoints={explanation.doctor_discussion} />
          )}

          {/* SECTION 15: BOTTOM HEALTH VAULT CTA */}
          <div className="bg-white border border-slate-200/90 rounded-2xl p-5 sm:p-6 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                Keep this report for future comparison
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Save this report to Health Vault to automatically track trends and parameter changes over time.
              </p>
            </div>
            <div className="shrink-0">
              {savedToVaultAt ? (
                <div className="flex flex-col sm:items-end gap-1">
                  <span className="px-4 py-2 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-xl text-xs font-bold inline-flex items-center gap-1.5 shadow-2xs">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    <span>✓ Saved to Health Vault</span>
                  </span>
                  <span className="text-[11px] text-slate-500 font-medium">
                    Saved on {formatDateTime(savedToVaultAt)}
                  </span>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={handleSaveToVault}
                  disabled={isSaving}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-xl text-xs font-bold transition-all shadow-xs flex items-center gap-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {isSaving ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Saving...</span>
                    </>
                  ) : (
                    <>
                      <FolderHeart className="w-3.5 h-3.5" />
                      <span>Save to Health Vault</span>
                    </>
                  )}
                </button>
              )}
            </div>
          </div>

          {/* Medical Safety & Compliance Footer */}
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-500 leading-relaxed flex items-start gap-2.5">
            <ShieldCheck className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
            <div>
              Automated deterministic analysis is designed for clinical reference and educational interpretation only. Always consult a qualified physician or healthcare provider regarding abnormal parameters or symptom correlation.
            </div>
          </div>
        </div>
      )}

      {/* SECTION 11: BIOMARKER DETAIL MODAL */}
      {selectedBiomarker && (
        <BiomarkerDetailModal
          biomarker={selectedBiomarker}
          trend={trends[(selectedBiomarker.key || "").toLowerCase()]}
          onClose={() => setSelectedBiomarker(null)}
        />
      )}
    </div>
  );
}
