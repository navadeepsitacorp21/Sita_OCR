import React from "react";
import { BrowserRouter, Routes, Route, NavLink, Link } from "react-router-dom";
import UploadPage from "./pages/UploadPage";
import VaultPage from "./pages/VaultPage";
import ReportPage from "./pages/ReportPage";
import { Activity, ShieldCheck, FolderHeart, Sparkles, AlertTriangle, RefreshCw } from "lucide-react";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  handleReload = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 max-w-xl mx-auto my-12 bg-white rounded-2xl border border-rose-200 shadow-sm text-center">
          <div className="w-12 h-12 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center mx-auto mb-4">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-bold text-slate-900 mb-2">Display Rendering Error</h2>
          <p className="text-sm text-slate-600 mb-4">
            An unexpected error occurred while rendering this view.
          </p>
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-left font-mono text-xs text-rose-700 overflow-x-auto mb-6">
            {this.state.error?.message || "Unknown error"}
          </div>
          <button
            onClick={this.handleReload}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold transition shadow-xs"
          >
            <RefreshCw className="w-4 h-4" />
            Reload Page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-[#f8fafc] text-slate-900 flex flex-col font-sans selection:bg-blue-100 selection:text-blue-900">
        {/* Modern Navigation Bar */}
        <header className="bg-white/85 backdrop-blur-md border-b border-slate-200/80 sticky top-0 z-30 transition-all">
          <div className="max-w-5xl mx-auto px-4 sm:px-6">
            <div className="flex justify-between h-16 items-center">
              {/* Brand Logo & Title */}
              <Link
                to="/"
                className="flex items-center gap-3 group focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 rounded-xl p-1 transition-transform"
              >
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-700 text-white flex items-center justify-center shadow-sm shadow-blue-500/25 group-hover:scale-[1.02] transition-transform">
                  <Activity className="w-5 h-5 text-white" />
                </div>
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold text-slate-900 text-base sm:text-lg tracking-tight leading-tight">
                      Medical Report Analysis
                    </span>
                    <span className="hidden sm:inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200/60">
                      SITA Clinical
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-500 font-medium hidden sm:block">
                    Deterministic Lab Intelligence & Insights
                  </span>
                </div>
              </Link>

              {/* Navigation Links */}
              <nav className="flex items-center gap-1.5" aria-label="Main Navigation">
                <NavLink
                  to="/"
                  end
                  className={({ isActive }) =>
                    `px-3.5 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all flex items-center gap-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 ${
                      isActive
                        ? "bg-blue-600 text-white shadow-xs shadow-blue-600/30 font-medium"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-100/80"
                    }`
                  }
                >
                  <Activity className="w-4 h-4" />
                  <span>Analyze Report</span>
                </NavLink>
                <NavLink
                  to="/vault"
                  className={({ isActive }) =>
                    `px-3.5 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all flex items-center gap-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 ${
                      isActive
                        ? "bg-blue-600 text-white shadow-xs shadow-blue-600/30 font-medium"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-100/80"
                    }`
                  }
                >
                  <FolderHeart className="w-4 h-4" />
                  <span>Health Vault</span>
                </NavLink>
              </nav>
            </div>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-1 max-w-5xl w-full mx-auto px-4 sm:px-6 py-8 md:py-10">
          <ErrorBoundary>
            <Routes>
              <Route path="/" element={<UploadPage />} />
              <Route path="/vault" element={<VaultPage />} />
              <Route path="/report/:report_id" element={<ReportPage />} />
            </Routes>
          </ErrorBoundary>
        </main>

        {/* Footer */}
        <footer className="border-t border-slate-200/80 bg-white py-6 text-xs text-slate-500">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-slate-600 font-medium">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>100% Deterministic Rule Engine • Zero Generative AI</span>
            </div>
            <div className="text-slate-400">
              For informational and educational laboratory reference only. Not a medical diagnosis.
            </div>
          </div>
        </footer>
      </div>
    </BrowserRouter>
  );
}
