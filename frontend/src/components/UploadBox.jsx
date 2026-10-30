import React, { useState, useRef } from "react";
import { UploadCloud, FileText, CheckCircle2, X } from "lucide-react";

export default function UploadBox({ isLoading, selectedFile, setSelectedFile }) {
  const [dragActive, setDragActive] = useState(false);
  const [localError, setLocalError] = useState(null);
  const inputRef = useRef(null);

  const formatFileSize = (bytes) => {
    if (!bytes && bytes !== 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  const validateAndSetFile = (file) => {
    setLocalError(null);
    if (!file) return;

    const allowedExtensions = [".pdf", ".jpg", ".jpeg", ".png", ".webp"];
    const ext = "." + (file.name.split(".").pop() || "").toLowerCase();
    if (!allowedExtensions.includes(ext)) {
      setLocalError("Please upload a supported report format: PDF, PNG, JPG, or WEBP.");
      return;
    }

    if (file.size > 20 * 1024 * 1024) {
      setLocalError("File size exceeds the 20 MB limit.");
      return;
    }

    setSelectedFile(file);
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (isLoading) return;
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (isLoading) return;
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleRemove = (e) => {
    e.stopPropagation();
    setSelectedFile(null);
    setLocalError(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  const getFileExtension = (name) => {
    return (name?.split(".").pop() || "FILE").toUpperCase();
  };

  return (
    <div className="space-y-2">
      <input
        ref={inputRef}
        type="file"
        id="report-file-input"
        accept=".pdf,.png,.jpg,.jpeg,.webp"
        onChange={handleChange}
        disabled={isLoading}
        className="hidden"
        aria-label="Upload medical report"
      />

      {!selectedFile ? (
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => !isLoading && inputRef.current?.click()}
          role="region"
          aria-label="Medical report file upload"
          className={`relative border-2 border-dashed rounded-2xl p-8 sm:p-10 text-center transition-all bg-white cursor-pointer group ${
            dragActive
              ? "border-blue-500 bg-blue-50/40 ring-4 ring-blue-500/10"
              : "border-slate-300 hover:border-blue-400 hover:bg-slate-50/70"
          } ${isLoading ? "opacity-60 cursor-not-allowed" : ""}`}
        >
          <div className="flex flex-col items-center justify-center space-y-3 max-w-sm mx-auto">
            <div className="w-13 h-13 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center group-hover:scale-105 group-hover:bg-blue-100 transition-all shadow-xs">
              <UploadCloud className="w-6 h-6" />
            </div>

            <div className="space-y-1">
              <p className="text-sm font-semibold text-slate-800">
                <span className="text-blue-600 hover:underline">Click to upload</span> or drag and drop
              </p>
              <p className="text-xs text-slate-500">
                Supports Complete Blood Count (CBC), Liver (LFT), Kidney (KFT), and Lipid Profile panels
              </p>
            </div>

            <span className="inline-flex items-center text-[11px] font-medium text-slate-400 bg-slate-100 px-2.5 py-1 rounded-full">
              PDF, PNG, JPG, or WEBP up to 20 MB
            </span>
          </div>
        </div>
      ) : (
        <div className="bg-white border border-slate-200/90 rounded-2xl p-4.5 sm:p-5 shadow-xs flex items-center justify-between gap-4 transition-all">
          <div className="flex items-center gap-3.5 min-w-0">
            <div className="w-11 h-11 rounded-xl bg-blue-50 border border-blue-100 text-blue-600 flex items-center justify-center shrink-0">
              <FileText className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <p className="text-sm font-bold text-slate-900 truncate" title={selectedFile.name}>
                  {selectedFile.name}
                </p>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200 shrink-0">
                  {getFileExtension(selectedFile.name)}
                </span>
              </div>
              <div className="flex items-center gap-2 text-xs text-slate-500 mt-0.5">
                <span>{formatFileSize(selectedFile.size)}</span>
                <span>•</span>
                <span className="text-emerald-600 font-medium inline-flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Ready for analysis
                </span>
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={handleRemove}
            disabled={isLoading}
            className="text-slate-400 hover:text-slate-600 hover:bg-slate-100 p-2 rounded-xl transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 shrink-0"
            title="Remove file"
            aria-label="Remove file"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {localError && (
        <p className="text-xs text-rose-600 font-medium pl-1 flex items-center gap-1">
          <span>•</span> {localError}
        </p>
      )}
    </div>
  );
}
