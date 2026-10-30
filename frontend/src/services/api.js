import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

export const uploadReportFile = async (file) => {
  const formData = new FormData();
  formData.append("file", file);
  const response = await apiClient.post("/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

export const getHealthVaultReports = async () => {
  const response = await apiClient.get("/health-vault/reports");
  return response.data;
};

export const getHealthVaultReportById = async (reportId) => {
  const response = await apiClient.get(`/health-vault/reports/${reportId}`);
  return response.data;
};

export const deleteHealthVaultReportById = async (reportId) => {
  const response = await apiClient.delete(`/health-vault/reports/${reportId}`);
  return response.data;
};

export const analyzeMedicalReport = async (file, patientGender = null) => {
  const formData = new FormData();
  formData.append("file", file);
  if (patientGender) {
    formData.append("patient_gender", patientGender);
  }
  const response = await apiClient.post("/medical-reports/analyze", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

export const saveReportToHealthVault = async ({
  requestId,
  filename,
  reportType,
  patientGender,
  rawParsedReport,
  fileHash,
  analyzedAt,
}) => {
  const response = await apiClient.post("/medical-reports/save-to-health-vault", {
    request_id: requestId,
    filename: filename,
    report_type: reportType,
    patient_gender: patientGender || null,
    raw_parsed_report: rawParsedReport,
    file_hash: fileHash,
    analyzed_at: analyzedAt || null,
  });
  return response.data;
};

export default apiClient;

