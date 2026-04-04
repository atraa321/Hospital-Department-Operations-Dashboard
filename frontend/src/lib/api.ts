import axios from 'axios';

function extractApiErrorMessage(error: unknown): string | null {
  if (!axios.isAxiosError(error)) {
    return null;
  }

  const data = error.response?.data;
  if (typeof data === 'string' && data.trim()) {
    return data.trim();
  }
  if (data && typeof data === 'object') {
    const detail = (data as { detail?: unknown }).detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail.trim();
    }
    const message = (data as { message?: unknown }).message;
    if (typeof message === 'string' && message.trim()) {
      return message.trim();
    }
  }
  return null;
}

export type ImportType =
  | 'CASE_INFO'
  | 'CASE_HOME_FILTERED'
  | 'COST_SUMMARY'
  | 'COST_DETAIL'
  | 'DIP_DICT'
  | 'ICD10_DICT'
  | 'ICD9_DICT';

export interface ImportBatch {
  batch_id: string;
  import_type: string;
  source_filename: string;
  status: string;
  row_count: number;
  column_count: number;
  error_message: string | null;
  requested_by: string | null;
  started_at: string | null;
  finished_at: string | null;
  cancel_requested_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ImportIssue {
  id: number;
  row_no: number;
  field_name: string | null;
  error_code: string;
  severity: string;
  message: string;
  created_at: string;
}

export interface ImportIssueList {
  total: number;
  page: number;
  page_size: number;
  items: ImportIssue[];
}

export interface ImportDataClearResult {
  message: string;
  deleted_case_info: number;
  deleted_cost_detail: number;
  deleted_orphan_fee_action: number;
  deleted_import_batch: number;
  deleted_import_issue: number;
  deleted_upload_files: number;
}

export interface ImportDataRestoreResult extends ImportDataClearResult {
  restored_case_info: number;
  restored_cost_detail: number;
  restored_orphan_fee_action: number;
  restored_import_batch: number;
  restored_import_issue: number;
}

export interface CurrentUser {
  user_id: string;
  role: string;
  dept_name: string | null;
  display_name: string | null;
  auth_source: string;
}

export interface OperationsOverviewSummary {
  total_cases: number;
  avg_cost: number;
  avg_los: number;
  turnover_index: number;
  department_count: number;
  average_score: number;
  risk_department_count: number;
}

export interface OperationsMonthlyTrendItem {
  period: string;
  case_count: number;
  avg_cost: number;
  avg_los: number;
  turnover_index: number;
  issue_count: number;
}

export interface DepartmentRankingItem {
  dept_name: string;
  case_count: number;
  avg_cost: number;
  avg_los: number;
  turnover_index: number;
  issue_count: number;
  efficiency_score: number;
  revenue_score: number;
  quality_score: number;
  total_score: number;
  summary_issue: string;
}

export interface OperationsHighlightItem {
  label: string;
  dept_name: string;
  detail: string;
}

export interface OperationsOverviewResponse {
  summary: OperationsOverviewSummary;
  monthly_trend: OperationsMonthlyTrendItem[];
  rankings: DepartmentRankingItem[];
  highlights: OperationsHighlightItem[];
  suggestions: string[];
}

export interface DepartmentScoreBreakdown {
  efficiency_score: number;
  revenue_score: number;
  quality_score: number;
  total_score: number;
}

export interface DepartmentDetailSummary {
  dept_name: string;
  case_count: number;
  avg_cost: number;
  avg_los: number;
  turnover_index: number;
  issue_count: number;
  score: DepartmentScoreBreakdown;
}

export interface DepartmentScoreDriver {
  title: string;
  detail: string;
  tone: string;
}

export interface DepartmentCostStructureItem {
  name: string;
  value: number;
  ratio: number;
}

export interface DepartmentDoctorCompareItem {
  doctor_name: string;
  case_count: number;
  avg_total_cost: number;
  avg_los: number;
  avg_drug_ratio: number;
  avg_material_ratio: number;
  issue_count: number;
}

export interface DepartmentAnomalyCategory {
  rule_code: string;
  rule_name: string | null;
  hit_count: number;
  red_count: number;
  orange_count: number;
  yellow_count: number;
}

export interface DepartmentDetailTopItem {
  item_code: string | null;
  item_name: string;
  total_amount: number;
  case_count: number;
  ratio: number;
}

export interface DepartmentOperationDetailResponse {
  summary: DepartmentDetailSummary;
  monthly_trend: OperationsMonthlyTrendItem[];
  cost_structure: DepartmentCostStructureItem[];
  doctor_compare: DepartmentDoctorCompareItem[];
  anomaly_categories: DepartmentAnomalyCategory[];
  detail_top_items: DepartmentDetailTopItem[];
  score_drivers: DepartmentScoreDriver[];
  suggestions: string[];
}

export interface QualityIssueCount {
  error_code: string;
  severity: string;
  count: number;
}

export interface QualityOverview {
  case_total: number;
  cost_detail_total: number;
  batch_total: number;
  batch_failed: number;
  pk_complete_rate: number;
  required_complete_rate: number;
  icd_valid_rate: number;
  orphan_fee_record_rate: number;
  import_failure_rate: number;
  warning_issue_total: number;
  error_issue_total: number;
  issues: QualityIssueCount[];
  generated_at: string;
}

export interface OrphanFeePatient {
  patient_id: string;
  detail_count: number;
  total_amount: number;
  latest_import_batch: string | null;
  status: string;
  note: string | null;
  operator: string | null;
  updated_at: string | null;
}

export interface OrphanFeePatientList {
  total: number;
  page: number;
  page_size: number;
  items: OrphanFeePatient[];
}

export interface CostStructureItem {
  name: string;
  value: number;
}

export interface TrendPoint {
  period: string;
  avg_cost: number;
  avg_drug_ratio: number;
}

export interface ClinicalTopItem {
  diagnosis_code: string;
  diagnosis_name: string | null;
  case_count: number;
}

export interface MonthlyMetric {
  period: string;
  case_count: number;
  avg_cost: number;
  avg_drug_ratio: number;
}

export interface RuleMonthlyMetric {
  period: string;
  hit_count: number;
  red_count: number;
}

export interface MonthlyReport {
  disease_metrics: MonthlyMetric[];
  rule_metrics: RuleMonthlyMetric[];
}

export interface ExecutiveBrief {
  total_cases: number;
  avg_cost: number;
  avg_los: number;
  rule_hit_total: number;
  open_workorders: number;
  close_rate: number;
}

interface ImportListResponse {
  items: ImportBatch[];
}

interface ImportStartResponse {
  message: string;
  batch: ImportBatch;
}

const configuredApiBaseUrl = `${import.meta.env.VITE_API_BASE_URL ?? ''}`.trim();
const devAuthHeaders = import.meta.env.DEV
  ? {
      'X-User-Id': import.meta.env.VITE_DEV_AUTH_USER_ID ?? 'dev_user',
      'X-Role': import.meta.env.VITE_DEV_AUTH_ROLE ?? 'ADMIN',
      'X-Dept-Name': import.meta.env.VITE_DEV_AUTH_DEPT ?? '',
    }
  : undefined;

const api = axios.create({
  baseURL: configuredApiBaseUrl || '/api/v1',
  timeout: 20_000,
  headers: devAuthHeaders,
});

api.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    const message = extractApiErrorMessage(error);
    if (message) {
      return Promise.reject(new Error(message));
    }
    return Promise.reject(error);
  },
);

// Large data imports may run for a long time; keep request alive until server returns.
const IMPORT_REQUEST_TIMEOUT_MS = 60_000;

export async function fetchHealth() {
  const response = await api.get<{ status: string }>('/health');
  return response.data;
}

export async function fetchCurrentUser() {
  const response = await api.get<CurrentUser>('/auth/me');
  return response.data;
}

export async function fetchOperationsOverview(params?: {
  dateFrom?: string;
  dateTo?: string;
  limit?: number;
}) {
  const response = await api.get<OperationsOverviewResponse>('/operations/overview', {
    params: {
      date_from: params?.dateFrom || undefined,
      date_to: params?.dateTo || undefined,
      limit: params?.limit ?? 12,
    },
  });
  return response.data;
}

export async function fetchDepartmentRankings(params?: {
  dateFrom?: string;
  dateTo?: string;
  limit?: number;
}) {
  const response = await api.get<DepartmentRankingItem[]>('/operations/rankings', {
    params: {
      date_from: params?.dateFrom || undefined,
      date_to: params?.dateTo || undefined,
      limit: params?.limit ?? 50,
    },
  });
  return response.data;
}

export async function fetchDepartmentOperationDetail(params: {
  deptName: string;
  dateFrom?: string;
  dateTo?: string;
}) {
  const response = await api.get<DepartmentOperationDetailResponse>(
    `/operations/departments/${encodeURIComponent(params.deptName)}`,
    {
      params: {
        date_from: params.dateFrom || undefined,
        date_to: params.dateTo || undefined,
      },
    },
  );
  return response.data;
}

export async function fetchQualityOverview() {
  const response = await api.get<QualityOverview>('/quality/overview');
  return response.data;
}

export async function fetchOrphanFeePatients(page = 1, pageSize = 50) {
  const response = await api.get<OrphanFeePatientList>('/quality/orphan-patients', {
    params: { page, page_size: pageSize },
  });
  return response.data;
}

export async function updateOrphanFeePatientAction(payload: {
  patientId: string;
  status: 'MARKED' | 'REJECTED' | 'SUPPLEMENTED' | 'PENDING';
  note?: string;
}) {
  const response = await api.post(`/quality/orphan-patients/${payload.patientId}/action`, {
    status: payload.status,
    note: payload.note || undefined,
  });
  return response.data;
}

export async function fetchCostStructure(params?: {
  deptName?: string;
  dateFrom?: string;
  dateTo?: string;
}) {
  const response = await api.get<{ items: CostStructureItem[] }>('/analytics/cost-structure', {
    params: {
      dept_name: params?.deptName || undefined,
      date_from: params?.dateFrom || undefined,
      date_to: params?.dateTo || undefined,
    },
  });
  return response.data;
}

export async function fetchCostTrend(params?: {
  deptName?: string;
  dateFrom?: string;
  dateTo?: string;
}) {
  const response = await api.get<{ items: TrendPoint[] }>('/analytics/cost-trend', {
    params: {
      dept_name: params?.deptName || undefined,
      date_from: params?.dateFrom || undefined,
      date_to: params?.dateTo || undefined,
    },
  });
  return response.data;
}

export async function fetchClinicalTop(params?: {
  limit?: number;
  deptName?: string;
  dateFrom?: string;
  dateTo?: string;
}) {
  const response = await api.get<{ items: ClinicalTopItem[] }>('/analytics/clinical-top', {
    params: {
      limit: params?.limit ?? 10,
      dept_name: params?.deptName || undefined,
      date_from: params?.dateFrom || undefined,
      date_to: params?.dateTo || undefined,
    },
  });
  return response.data;
}

export async function fetchMonthlyReport() {
  const response = await api.get<MonthlyReport>('/reports/monthly');
  return response.data;
}

export async function fetchExecutiveReport() {
  const response = await api.get<ExecutiveBrief>('/reports/executive');
  return response.data;
}

export async function downloadCaseReportCsv() {
  const response = await api.get('/reports/cases.csv', { responseType: 'blob' });
  const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  link.href = url;
  link.download = `cases_${Date.now()}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

export async function fetchImportBatches(limit = 20) {
  const response = await api.get<ImportListResponse>('/imports', {
    params: { limit },
  });
  return response.data.items;
}

export async function cancelImportBatch(batchId: string) {
  const response = await api.post<ImportStartResponse>(`/imports/${batchId}/cancel`);
  return response.data;
}

export async function fetchImportIssues(payload: {
  batchId: string;
  page?: number;
  pageSize?: number;
  severity?: string;
  errorCode?: string;
}) {
  const response = await api.get<ImportIssueList>(`/imports/${payload.batchId}/issues`, {
    params: {
      page: payload.page ?? 1,
      page_size: payload.pageSize ?? 20,
      severity: payload.severity || undefined,
      error_code: payload.errorCode || undefined,
    },
  });
  return response.data;
}

export async function downloadImportIssues(payload: {
  batchId: string;
  format: 'csv' | 'xlsx';
  severity?: string;
  errorCode?: string;
}) {
  const response = await api.get(`/imports/${payload.batchId}/issues.${payload.format}`, {
    params: {
      severity: payload.severity || undefined,
      error_code: payload.errorCode || undefined,
    },
    responseType: 'blob',
  });

  const blob = new Blob([response.data], {
    type:
      payload.format === 'csv'
        ? 'text/csv;charset=utf-8'
        : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  link.href = url;
  link.download = `issues_${payload.batchId}.${payload.format}`;
  link.click();
  URL.revokeObjectURL(url);
}

export async function createImportBatch(payload: { importType: ImportType; file: File }) {
  const formData = new FormData();
  formData.append('file', payload.file);
  const response = await api.post<ImportStartResponse>('/imports/start', formData, {
    params: { import_type: payload.importType },
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: IMPORT_REQUEST_TIMEOUT_MS,
  });
  return response.data;
}

export async function createCaseHomeImportBatch(payload: { sourceFile: File }) {
  const formData = new FormData();
  formData.append('source_file', payload.sourceFile);
  const response = await api.post<ImportStartResponse>('/imports/case-home/start', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: IMPORT_REQUEST_TIMEOUT_MS,
  });
  return response.data;
}

export async function createCaseHomeFilteredImportBatch(payload: { sourceFile: File; filterFile?: File }) {
  return createCaseHomeImportBatch({ sourceFile: payload.sourceFile });
}

export async function downloadCaseCostBackup() {
  const response = await api.get('/imports/backup/case-cost.xlsx', {
    responseType: 'blob',
    timeout: 10 * 60 * 1000,
  });
  const blob = new Blob([response.data], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  link.href = url;
  link.download = `case_cost_backup_${Date.now()}.xlsx`;
  link.click();
  URL.revokeObjectURL(url);
}

export async function clearCaseCostImportData(confirmText: string) {
  const response = await api.post<ImportDataClearResult>('/imports/clear/case-cost', {
    confirm_text: confirmText,
  });
  return response.data;
}

export async function restoreCaseCostImportData(payload: { file: File; confirmText: string }) {
  const formData = new FormData();
  formData.append('file', payload.file);
  formData.append('confirm_text', payload.confirmText);
  const response = await api.post<ImportDataRestoreResult>('/imports/restore/case-cost', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 10 * 60 * 1000,
  });
  return response.data;
}
